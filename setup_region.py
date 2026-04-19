"""
Interactive helper to determine the screenshot region coordinates.

Run this script once to figure out the correct SCREENSHOT_* values to put in
your .env file.  No changes to the application are needed after running it.

Usage:
    python setup_region.py
"""

import sys

try:
    import mss
    from PIL import Image
except ImportError:
    print("Please install dependencies first:  pip install -r requirements.txt")
    sys.exit(1)


def _monitor_info() -> None:
    with mss.mss() as sct:
        print("Detected monitors:")
        for i, mon in enumerate(sct.monitors):
            label = "all monitors combined" if i == 0 else f"monitor {i}"
            print(
                f"  [{i}] {label}: "
                f"left={mon['left']}, top={mon['top']}, "
                f"width={mon['width']}, height={mon['height']}"
            )
    print()


def _save_preview(region: dict) -> None:
    import os
    tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "region_preview.png")
    with mss.mss() as sct:
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        img.save(path)
    print(f"Preview saved to: {path}")


def main() -> None:
    print("=" * 50)
    print("  my_assistant — Screenshot Region Setup")
    print("=" * 50)
    print()

    _monitor_info()

    print("Enter the screen region you want the assistant to capture.")
    print("Tip: (0, 0) is the top-left corner of your primary monitor.\n")

    try:
        left   = int(input("Left   (x, pixels from left edge) : "))
        top    = int(input("Top    (y, pixels from top edge)  : "))
        width  = int(input("Width  (pixels)                   : "))
        height = int(input("Height (pixels)                   : "))
    except ValueError:
        print("Invalid input — please enter integer values.")
        sys.exit(1)

    region = {"left": left, "top": top, "width": width, "height": height}

    print()
    save = input("Save a preview screenshot to tmp/region_preview.png? [y/N] ").strip().lower()
    if save == "y":
        try:
            _save_preview(region)
        except Exception as exc:
            print(f"Could not save preview: {exc}")

    print()
    print("Add the following lines to your .env file:")
    print()
    print(f"SCREENSHOT_LEFT={left}")
    print(f"SCREENSHOT_TOP={top}")
    print(f"SCREENSHOT_WIDTH={width}")
    print(f"SCREENSHOT_HEIGHT={height}")
    print()
    print("Then restart the application.")


if __name__ == "__main__":
    main()
