"""
Interactive helper to calibrate browser scroll-capture mode.

Previews the configured browser region, validates the page click point, runs
a short capture sequence using the same click/scroll logic as runtime browser
mode, and saves raw screenshots under tmp/.

Usage:
    python test_browser_screenshot.py
"""

import os
import sys
import time
import io
from datetime import datetime

import config
from PIL import Image, ImageDraw
from screenshot import (
    _capture_region_png,
    _focus_browser_page,
    _images_are_visually_unchanged,
    _send_browser_scroll_input,
)

TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp")


def _print_config() -> dict[str, int]:
    region = {
        "top": int(config.BROWSER_REGION["top"]),
        "left": int(config.BROWSER_REGION["left"]),
        "width": int(config.BROWSER_REGION["width"]),
        "height": int(config.BROWSER_REGION["height"]),
    }
    click_x = int(config.BROWSER_PAGE_CLICK_X)
    click_y = int(config.BROWSER_PAGE_CLICK_Y)
    abs_x = region["left"] + click_x
    abs_y = region["top"] + click_y

    print("Browser region:")
    print(f"  top={region['top']} left={region['left']} width={region['width']} height={region['height']}")
    print("Page click point:")
    print(f"  relative=({click_x}, {click_y}) absolute=({abs_x}, {abs_y})")
    print("Scroll config:")
    print(
        f"  mode={config.BROWSER_SCROLL_INPUT_MODE} key={config.BROWSER_SCROLL_KEY} "
        f"mouse_delta={config.BROWSER_SCROLL_MOUSE_DELTA} delay_ms={config.BROWSER_SCROLL_DELAY_MS}"
    )
    print(f"  send_home={config.BROWSER_SEND_HOME_BEFORE_CAPTURE}")
    return region


def _check_imports() -> None:
    try:
        import pyautogui  # noqa: F401
    except ImportError:
        print("pyautogui is not installed.")
        print("Run:  pip install pyautogui")
        sys.exit(1)


def _save_region_preview(region: dict[str, int], stamp: str) -> str:
    png_bytes = _capture_region_png(region)
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)

    x = int(config.BROWSER_PAGE_CLICK_X)
    y = int(config.BROWSER_PAGE_CLICK_Y)
    r = 10
    draw.ellipse((x - r, y - r, x + r, y + r), outline="red", width=3)
    draw.line((x - 16, y, x + 16, y), fill="red", width=2)
    draw.line((x, y - 16, x, y + 16), fill="red", width=2)

    preview_path = os.path.join(TMP_DIR, f"browser_region_preview_{stamp}.png")
    image.save(preview_path, format="PNG")
    return preview_path


UNCHANGED_FRAME_LIMIT = 3


def _run_capture(region: dict[str, int]) -> tuple[list[bytes], int]:
    """Mirror the production loop: scroll until UNCHANGED_FRAME_LIMIT consecutive unchanged frames."""
    mode = (config.BROWSER_SCROLL_INPUT_MODE or "keyboard").strip().lower()
    delay_seconds = max(0, int(config.BROWSER_SCROLL_DELAY_MS)) / 1000.0

    _focus_browser_page(region, config.BROWSER_PAGE_CLICK_X, config.BROWSER_PAGE_CLICK_Y)
    time.sleep(0.15)

    if config.BROWSER_SEND_HOME_BEFORE_CAPTURE:
        _send_browser_scroll_input("keyboard", "home", 0)
        time.sleep(0.2)

    raw_chunks = [_capture_region_png(region)]
    previous = raw_chunks[0]
    unchanged_count = 0
    total_scrolls = 0

    while unchanged_count < UNCHANGED_FRAME_LIMIT:
        _send_browser_scroll_input(mode, config.BROWSER_SCROLL_KEY, config.BROWSER_SCROLL_MOUSE_DELTA)
        total_scrolls += 1
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        current = _capture_region_png(region)
        if _images_are_visually_unchanged(previous, current):
            unchanged_count += 1
            print(f"  scroll {total_scrolls}: unchanged ({unchanged_count}/{UNCHANGED_FRAME_LIMIT})")
            continue
        raw_chunks.append(current)
        previous = current
        unchanged_count = 0
        print(f"  scroll {total_scrolls}: new frame captured (total: {len(raw_chunks)})")

    return raw_chunks, total_scrolls


def _save_outputs(stamp: str, raw_chunks: list[bytes]) -> str:
    for index, chunk in enumerate(raw_chunks, start=1):
        path = os.path.join(TMP_DIR, f"browser_raw_{stamp}_{index:02d}.png")
        with open(path, "wb") as f:
            f.write(chunk)

    return os.path.join(TMP_DIR, f"browser_raw_{stamp}_01.png")


def main() -> None:
    print("=" * 55)
    print("  my_assistant — Browser Scroll-Capture Calibration")
    print("=" * 55)
    print()

    _check_imports()
    os.makedirs(TMP_DIR, exist_ok=True)

    region = _print_config()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if region["width"] <= 0 or region["height"] <= 0:
        print("\nInvalid browser region width/height. Update BROWSER_REGION_* in .env.")
        sys.exit(1)

    input("\nKeep your browser visible in the configured region, then press Enter to preview... ")

    try:
        preview_path = _save_region_preview(region, stamp)
    except Exception as exc:
        print(f"Could not capture region preview: {exc}")
        sys.exit(1)

    print(f"Saved region preview with click marker: {preview_path}")

    run_capture = input("\nRun full scroll-capture sequence now? [Y/n] ").strip().lower()
    if run_capture == "n":
        print("Done. Adjust config and re-run this helper.")
        return

    print(f"\nScrolling until {UNCHANGED_FRAME_LIMIT} consecutive unchanged frames...")
    try:
        raw_chunks, total_scrolls = _run_capture(region)
    except RuntimeError as exc:
        print(f"\nCapture failed: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nUnexpected capture error: {exc}")
        sys.exit(1)

    first_raw_path = _save_outputs(stamp, raw_chunks)
    print(f"\nSaved {len(raw_chunks)} raw frame(s) across {total_scrolls} scroll(s), starting at: {first_raw_path}")
    print(f"Total scrolls performed: {total_scrolls}")
    print()
    print("Tuning tips:")
    print("- Review raw frames in tmp/ to verify smooth top-to-bottom progression.")
    print("- If content loads slowly after scroll, increase BROWSER_SCROLL_DELAY_MS.")
    print("- Keep the browser visible and avoid touching mouse/keyboard during capture.")
    print()
    print("Ready for app browser mode:")
    print('  POST /ask  {"prompt": "...", "mode": "browser"}')
    print("UI mode label: Full page (scroll capture)")


if __name__ == "__main__":
    main()
