"""
Interactive helper to determine the screenshot region coordinates.

Run this script once to figure out the correct SCREENSHOT_* values to put in
your .env file.  No changes to the application are needed after running it.

Usage:
    python setup_region.py
"""

import os
import re
import sys

try:
    import mss
    from PIL import Image
except ImportError:
    print("Please install dependencies first:  pip install -r requirements.txt")
    sys.exit(1)


def _open_mss():
    mss_class = getattr(mss, "MSS", None)
    if mss_class is not None:
        return mss_class()
    return mss.mss()


def _monitor_info() -> list[dict]:
    with _open_mss() as sct:
        monitors = list(sct.monitors)
        print("Detected monitors:")
        for i, mon in enumerate(monitors):
            label = "all monitors combined" if i == 0 else f"monitor {i}"
            print(
                f"  [{i}] {label}: "
                f"left={mon['left']}, top={mon['top']}, "
                f"width={mon['width']}, height={mon['height']}"
            )
    print()
    return monitors


def _validate_region_in_bounds(region: dict, all_monitors_bounds: dict) -> None:
    left = int(region["left"])
    top = int(region["top"])
    width = int(region["width"])
    height = int(region["height"])

    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be greater than 0.")

    bound_left = int(all_monitors_bounds["left"])
    bound_top = int(all_monitors_bounds["top"])
    bound_right = bound_left + int(all_monitors_bounds["width"])
    bound_bottom = bound_top + int(all_monitors_bounds["height"])

    region_right = left + width
    region_bottom = top + height
    in_bounds = (
        left >= bound_left
        and top >= bound_top
        and region_right <= bound_right
        and region_bottom <= bound_bottom
    )
    if in_bounds:
        return

    max_width = max(0, bound_right - left)
    max_height = max(0, bound_bottom - top)
    raise ValueError(
        "Selected region is outside the visible monitor bounds. "
        f"Visible bounds are left={bound_left}, top={bound_top}, "
        f"right={bound_right}, bottom={bound_bottom}. "
        f"For the provided left/top, max width={max_width}, max height={max_height}."
    )


def _save_preview(region: dict, all_monitors_bounds: dict) -> None:
    _validate_region_in_bounds(region, all_monitors_bounds)

    tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "region_preview.png")
    with _open_mss() as sct:
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        img.save(path)
    print(f"Preview saved to: {path}")


def _update_dotenv_screenshot_vars(repo_root: str, region: dict) -> str:
    env_path = os.path.join(repo_root, ".env")
    updates = {
        "SCREENSHOT_LEFT": str(int(region["left"])),
        "SCREENSHOT_TOP": str(int(region["top"])),
        "SCREENSHOT_WIDTH": str(int(region["width"])),
        "SCREENSHOT_HEIGHT": str(int(region["height"])),
    }

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        newline = "\r\n" if "\r\n" in content else "\n"
        lines = content.splitlines()
    else:
        newline = "\n"
        lines = []

    found: dict[str, bool] = {key: False for key in updates}
    pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
    updated_lines = []
    for line in lines:
        match = pattern.match(line)
        if not match:
            updated_lines.append(line)
            continue

        key = match.group(1)
        if key in updates:
            updated_lines.append(f"{key}={updates[key]}")
            found[key] = True
            continue

        updated_lines.append(line)

    for key in updates:
        if not found[key]:
            updated_lines.append(f"{key}={updates[key]}")

    with open(env_path, "w", encoding="utf-8") as f:
        if updated_lines:
            f.write(newline.join(updated_lines) + newline)
        else:
            f.write("")

    return env_path


def _read_current_screenshot_vars(repo_root: str) -> dict[str, int | None]:
    env_path = os.path.join(repo_root, ".env")
    keys = ("SCREENSHOT_LEFT", "SCREENSHOT_TOP", "SCREENSHOT_WIDTH", "SCREENSHOT_HEIGHT")
    result: dict[str, int | None] = {k: None for k in keys}
    if not os.path.exists(env_path):
        return result
    pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line)
            if not match:
                continue
            key, val = match.group(1), match.group(2).strip()
            if key in result:
                try:
                    result[key] = int(val)
                except ValueError:
                    pass
    return result


def _prompt_int(prompt: str, current: int | None) -> int:
    if current is not None:
        display = f"{prompt} [{current}]: "
    else:
        display = f"{prompt}: "
    raw = input(display).strip()
    if raw == "" and current is not None:
        return current
    return int(raw)


def main() -> None:
    print("=" * 50)
    print("  my_assistant — Screenshot Region Setup")
    print("=" * 50)
    print()

    monitors = _monitor_info()
    all_monitors_bounds = monitors[0]
    current = _read_current_screenshot_vars(os.path.dirname(__file__))

    print("Enter the screen region you want the assistant to capture.")
    print("Tip: (0, 0) is the top-left corner of your primary monitor.")
    print("     Press Enter to keep the current value.\n")

    try:
        left   = _prompt_int("Left   (x, pixels from left edge)", current["SCREENSHOT_LEFT"])
        top    = _prompt_int("Top    (y, pixels from top edge) ", current["SCREENSHOT_TOP"])
        width  = _prompt_int("Width  (pixels)                  ", current["SCREENSHOT_WIDTH"])
        height = _prompt_int("Height (pixels)                  ", current["SCREENSHOT_HEIGHT"])
    except ValueError:
        print("Invalid input — please enter integer values.")
        sys.exit(1)

    region = {"left": left, "top": top, "width": width, "height": height}

    print()
    save = input("Save a preview screenshot to tmp/region_preview.png? [y/N] ").strip().lower()
    if save == "y":
        try:
            _save_preview(region, all_monitors_bounds)
        except Exception as exc:
            print(f"Could not save preview: {exc}")

    print()
    write_env = input("Write these SCREENSHOT_* values to .env now? [Y/n] ").strip().lower()
    if write_env in {"", "y", "yes"}:
        try:
            env_path = _update_dotenv_screenshot_vars(os.path.dirname(__file__), region)
            print(f"Updated .env at: {env_path}")
        except Exception as exc:
            print(f"Could not update .env automatically: {exc}")

    print()
    print("Use the following values in your .env file:")
    print()
    print(f"SCREENSHOT_LEFT={left}")
    print(f"SCREENSHOT_TOP={top}")
    print(f"SCREENSHOT_WIDTH={width}")
    print(f"SCREENSHOT_HEIGHT={height}")
    print()
    print("Then restart the application.")


if __name__ == "__main__":
    main()
