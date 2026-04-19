"""
Interactive helper to test the full-page browser screenshot mode.

Connects to a running Chrome instance via CDP, captures a full-page screenshot
of the active tab, and saves it to tmp/browser_preview.png so you can verify
it looks correct before using browser mode in the assistant.

Prerequisites:
    pip install playwright
    playwright install chromium

    Launch Chrome with:
        chrome --remote-debugging-port=9222

Usage:
    python test_browser_screenshot.py
"""

import os
import sys

from screenshot import take_browser_screenshot

CDP_URL = "http://127.0.0.1:9222"
PREVIEW_PATH = os.path.join(os.path.dirname(__file__), "tmp", "browser_preview.png")


def _check_imports() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("playwright is not installed.")
        print("Run:  pip install playwright && playwright install chromium")
        sys.exit(1)


def _capture() -> bytes:
    print(f"Connecting to Chrome at {CDP_URL} …")
    try:
        png_bytes, _ = take_browser_screenshot()
    except RuntimeError as exc:
        print(f"\nCould not capture browser screenshot: {exc}")
        sys.exit(1)

    return png_bytes


def _save_preview(png_bytes: bytes) -> None:
    os.makedirs(os.path.dirname(PREVIEW_PATH), exist_ok=True)
    with open(PREVIEW_PATH, "wb") as f:
        f.write(png_bytes)


def main() -> None:
    print("=" * 55)
    print("  my_assistant — Browser Screenshot Test")
    print("=" * 55)
    print()

    _check_imports()

    png_bytes = _capture()

    size_kb = len(png_bytes) / 1024

    # Try to get pixel dimensions via Pillow (optional)
    dimensions = ""
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes))
        dimensions = f", {img.width}×{img.height} px"
    except Exception:
        pass

    print(f"\nScreenshot captured successfully — {size_kb:.1f} KB{dimensions}")

    save = input(f"\nSave preview to {PREVIEW_PATH}? [Y/n] ").strip().lower()
    if save != "n":
        try:
            _save_preview(png_bytes)
            print(f"Saved: {PREVIEW_PATH}")
        except Exception as exc:
            print(f"Could not save preview: {exc}")
            sys.exit(1)
    else:
        print("Preview not saved.")

    print()
    print("Everything looks good! You can now use browser mode in the assistant:")
    print('  POST /ask  {"prompt": "…", "mode": "browser"}')
    print("Or select 'Full page (Chrome)' in the web UI.")


if __name__ == "__main__":
    main()
