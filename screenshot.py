import io
import base64

import mss
from PIL import Image

from config import SCREENSHOT_REGION


def take_screenshot() -> tuple[bytes, str]:
    """
    Capture a screenshot of the configured region.

    Returns:
        A tuple of (raw PNG bytes, base64-encoded PNG string).
    """
    with mss.mss() as sct:
        raw = sct.grab(SCREENSHOT_REGION)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

    img_base64 = base64.b64encode(png_bytes).decode("utf-8")
    return png_bytes, img_base64
