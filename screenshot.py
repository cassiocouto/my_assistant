import io
import base64
import time

from PIL import Image, ImageChops, ImageStat

from config import (
    BROWSER_PAGE_CLICK_X,
    BROWSER_PAGE_CLICK_Y,
    BROWSER_REGION,
    BROWSER_SCROLL_DELAY_MS,
    BROWSER_SCROLL_INPUT_MODE,
    BROWSER_SCROLL_KEY,
    BROWSER_SCROLL_MOUSE_DELTA,
    BROWSER_SEND_HOME_BEFORE_CAPTURE,
    SCREENSHOT_REGION,
)

UNCHANGED_FRAME_LIMIT = 3


def _get_mss_module():
    try:
        import mss  # lazy import for screenshot operations
    except ImportError as exc:
        raise RuntimeError(
            "Screenshot capture requires mss. Run: pip install mss"
        ) from exc

    return mss


def _open_mss():
    mss = _get_mss_module()
    mss_class = getattr(mss, "MSS", None)
    if mss_class is not None:
        return mss_class()
    return mss.mss()


def _get_pyautogui_module():
    try:
        import pyautogui  # lazy import for browser mode only
    except ImportError as exc:
        raise RuntimeError(
            "Browser mode requires pyautogui. Run: pip install pyautogui"
        ) from exc

    pyautogui.PAUSE = 0.08
    return pyautogui


def _capture_region_png(region: dict[str, int]) -> bytes:
    with _open_mss() as sct:
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


def _focus_browser_page(region: dict[str, int], click_x: int, click_y: int) -> None:
    pyautogui = _get_pyautogui_module()

    screen_x = int(region["left"] + click_x)
    screen_y = int(region["top"] + click_y)
    pyautogui.moveTo(screen_x, screen_y, duration=0.1)
    pyautogui.click()


def _send_browser_scroll_input(mode: str, key: str, mouse_delta: int) -> None:
    pyautogui = _get_pyautogui_module()

    if mode == "mouse":
        pyautogui.scroll(int(mouse_delta))
        return

    normalized_key = key.strip().lower().replace(" ", "")
    if normalized_key in {"pagedown", "page_down"}:
        normalized_key = "pagedown"
    elif normalized_key in {"pageup", "page_up"}:
        normalized_key = "pageup"
    elif normalized_key == " ":
        normalized_key = "space"
    pyautogui.press(normalized_key)


def _images_are_visually_unchanged(previous_png: bytes, current_png: bytes) -> bool:
    prev = Image.open(io.BytesIO(previous_png)).convert("L")
    curr = Image.open(io.BytesIO(current_png)).convert("L")

    if prev.size != curr.size:
        return False

    target_size = (360, 360)
    prev_small = prev.resize(target_size)
    curr_small = curr.resize(target_size)

    diff = ImageChops.difference(prev_small, curr_small)
    if diff.getbbox() is None:
        return True

    mean_delta = ImageStat.Stat(diff).mean[0]
    return mean_delta < 1.5


def _trim_chunk_overlap(chunks: list[bytes], overlap: int, sticky_header_crop: int) -> list[bytes]:
    # Explicitly ignore overlap/sticky settings: stitching is pure concat in capture order.
    _ = overlap
    _ = sticky_header_crop
    return list(chunks)



def stitch_png_chunks(chunks: list[bytes]) -> bytes:
    if not chunks:
        raise RuntimeError("No browser chunks were captured.")

    images = [Image.open(io.BytesIO(chunk)).convert("RGB") for chunk in chunks]
    width = max(image.width for image in images)
    height = sum(image.height for image in images)

    stitched = Image.new("RGB", (width, height), "white")
    top = 0
    for image in images:
        stitched.paste(image, (0, top))
        top += image.height

    buffer = io.BytesIO()
    stitched.save(buffer, format="PNG")
    return buffer.getvalue()


def take_browser_screenshot_chunks() -> list[bytes]:
    """Capture a visible browser region as multiple vertically ordered PNG chunks."""
    region = {
        "top": int(BROWSER_REGION["top"]),
        "left": int(BROWSER_REGION["left"]),
        "width": int(BROWSER_REGION["width"]),
        "height": int(BROWSER_REGION["height"]),
    }

    if region["width"] <= 0 or region["height"] <= 0:
        raise RuntimeError("Browser region width/height must be greater than 0.")

    mode = (BROWSER_SCROLL_INPUT_MODE or "keyboard").strip().lower()
    if mode not in {"keyboard", "mouse"}:
        raise RuntimeError("BROWSER_SCROLL_INPUT_MODE must be 'keyboard' or 'mouse'.")

    delay_seconds = max(0, int(BROWSER_SCROLL_DELAY_MS)) / 1000.0

    try:
        _focus_browser_page(region, BROWSER_PAGE_CLICK_X, BROWSER_PAGE_CLICK_Y)
        time.sleep(0.15)

        if BROWSER_SEND_HOME_BEFORE_CAPTURE:
            _send_browser_scroll_input("keyboard", "home", 0)
            time.sleep(0.2)

        chunks = [_capture_region_png(region)]
        previous_png = chunks[0]
        unchanged_count = 0

        while unchanged_count < UNCHANGED_FRAME_LIMIT:
            _send_browser_scroll_input(mode, BROWSER_SCROLL_KEY, BROWSER_SCROLL_MOUSE_DELTA)
            if delay_seconds > 0:
                time.sleep(delay_seconds)

            current_png = _capture_region_png(region)
            if _images_are_visually_unchanged(previous_png, current_png):
                unchanged_count += 1
                continue

            chunks.append(current_png)
            previous_png = current_png
            unchanged_count = 0

        return chunks
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "Browser scroll capture failed. Keep the target page visible inside the configured browser region "
            "and avoid interacting until capture completes."
        ) from exc



def take_screenshot() -> tuple[bytes, str]:
    """
    Capture a screenshot of the configured region.

    Returns:
        A tuple of (raw PNG bytes, base64-encoded PNG string).
    """
    with _open_mss() as sct:
        raw = sct.grab(SCREENSHOT_REGION)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

    img_base64 = base64.b64encode(png_bytes).decode("utf-8")
    return png_bytes, img_base64



