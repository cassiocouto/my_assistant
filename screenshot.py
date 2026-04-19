import io
import base64

import mss
from PIL import Image

from config import SCREENSHOT_REGION

# Maximum height (pixels) of each image chunk sent to the LLM.
# Full-width is preserved; only height is capped per chunk.
CHUNK_HEIGHT = 4000


def _page_has_rendered_content(page) -> bool:
    try:
        metrics = page.evaluate(
            """() => {
                const de = document.documentElement;
                const body = document.body;
                const width = Math.max(
                    de?.scrollWidth || 0,
                    de?.clientWidth || 0,
                    body?.scrollWidth || 0,
                    body?.clientWidth || 0,
                    window.innerWidth || 0
                );
                const height = Math.max(
                    de?.scrollHeight || 0,
                    de?.clientHeight || 0,
                    body?.scrollHeight || 0,
                    body?.clientHeight || 0,
                    window.innerHeight || 0
                );
                return { width, height };
            }"""
        )
    except Exception:
        return False

    return metrics.get("width", 0) > 0 and metrics.get("height", 0) > 0


def _page_is_visible_or_focused(page) -> bool:
    try:
        state = page.evaluate(
            """() => ({
                visibility: document.visibilityState,
                focused: document.hasFocus(),
            })"""
        )
    except Exception:
        return False

    return state.get("visibility") == "visible" or bool(state.get("focused"))


def _preload_lazy_content(page) -> None:
    try:
        page.evaluate(
            """async () => {
                const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
                let lastHeight = 0;
                for (let i = 0; i < 4; i += 1) {
                    const currentHeight = Math.max(
                        document.documentElement?.scrollHeight || 0,
                        document.body?.scrollHeight || 0
                    );
                    window.scrollTo(0, currentHeight);
                    await wait(250);
                    if (currentHeight <= lastHeight) {
                        break;
                    }
                    lastHeight = currentHeight;
                }
                window.scrollTo(0, 0);
                await wait(120);
            }"""
        )
    except Exception:
        # If a site blocks script evaluation, continue with normal capture.
        pass


def _wait_for_page_stability(page) -> None:
    for state in ("domcontentloaded", "load", "networkidle"):
        try:
            page.wait_for_load_state(state, timeout=5000)
        except Exception:
            pass
    page.wait_for_timeout(600)


def _get_cdp_page_metrics(page) -> dict[str, int]:
    session = page.context.new_cdp_session(page)
    layout = session.send("Page.getLayoutMetrics")

    content = layout.get("cssContentSize") or layout.get("contentSize") or {}
    viewport = layout.get("cssLayoutViewport") or layout.get("layoutViewport") or {}
    return {
        "width": int(content.get("width") or viewport.get("clientWidth") or 0),
        "height": int(content.get("height") or viewport.get("clientHeight") or 0),
    }



def _is_capturable_url(url: str) -> bool:
    if not url or url == "about:blank":
        return False

    blocked_prefixes = (
        "chrome://",
        "chrome-extension://",
        "devtools://",
        "edge://",
        "about:",
    )
    if url.startswith(blocked_prefixes):
        return False

    return url.startswith(("http://", "https://", "file://"))


def _pick_best_capture_page(pages):
    candidates = [pg for pg in pages if _is_capturable_url(pg.url)]
    if not candidates:
        candidates = [pg for pg in pages if pg.url not in ("about:blank", "")]
    if not candidates:
        candidates = pages

    for pg in candidates:
        if _page_is_visible_or_focused(pg):
            return pg

    for pg in candidates:
        try:
            pg.bring_to_front()
        except Exception:
            pass

        try:
            pg.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        if _page_has_rendered_content(pg):
            return pg

    page = candidates[0]
    try:
        page.set_viewport_size({"width": 1280, "height": 720})
    except Exception:
        pass
    return page



def stitch_png_chunks(chunks: list[bytes]) -> bytes:
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


def _capture_page_chunks_via_cdp(page, chunk_height: int = CHUNK_HEIGHT) -> list[bytes]:
    _wait_for_page_stability(page)
    _preload_lazy_content(page)

    session = page.context.new_cdp_session(page)
    metrics = _get_cdp_page_metrics(page)
    width = metrics.get("width", 0)
    height = metrics.get("height", 0)

    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid CDP page metrics before chunk capture: {metrics}")

    chunks = []
    for top in range(0, height, chunk_height):
        current_height = min(chunk_height, height - top)
        result = session.send(
            "Page.captureScreenshot",
            {
                "format": "png",
                "fromSurface": True,
                "captureBeyondViewport": True,
                "clip": {
                    "x": 0,
                    "y": top,
                    "width": width,
                    "height": current_height,
                    "scale": 1,
                },
            },
        )
        chunks.append(base64.b64decode(result["data"]))

    return chunks


def take_browser_screenshot_chunks() -> list[bytes]:
    """
    Capture the active Chrome page as multiple vertical PNG chunks.

    Chunks are captured directly through the Chrome DevTools Protocol using
    page-space clips, which is more reliable for very long pages than relying
    on a single full-page screenshot.
    """
    try:
        from playwright.sync_api import sync_playwright  # lazy import
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            try:
                if not browser.contexts:
                    raise RuntimeError(
                        "Chrome is running but no browser context was found. Open a regular tab and try again."
                    )

                context = browser.contexts[0]
                pages = context.pages
                if not pages:
                    raise RuntimeError(
                        "Chrome is running but there are no open tabs to capture. Open a page and try again."
                    )

                capturable_pages = [pg for pg in pages if _is_capturable_url(pg.url)]
                source_pages = capturable_pages if capturable_pages else pages
                preferred = _pick_best_capture_page(source_pages)
                ordered_pages = [preferred, *[pg for pg in source_pages if pg is not preferred]]

                last_error = None
                for page in ordered_pages:
                    try:
                        page.bring_to_front()
                    except Exception:
                        pass

                    try:
                        return _capture_page_chunks_via_cdp(page)
                    except Exception as exc:
                        last_error = exc
                        continue

                if last_error is not None:
                    raise RuntimeError(
                        "Could not capture valid browser chunks from open tabs. "
                        "Open a regular webpage (http/https/file), keep it visible, and try again."
                    ) from last_error
                raise RuntimeError("Could not capture browser chunks.")
            finally:
                browser.close()
    except Exception as exc:
        if "connect" in str(exc).lower() or "refused" in str(exc).lower() or "9222" in str(exc):
            raise RuntimeError(
                "Could not connect to Chrome. Make sure Chrome is running with "
                "--remote-debugging-port=9222."
            ) from exc
        raise RuntimeError(str(exc)) from exc



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



# Browser mode requires:
#   pip install playwright
#   playwright install chromium
# Chrome must be launched with --remote-debugging-port=9222 before using this mode.
def take_browser_screenshot() -> tuple[bytes, str]:
    """
    Capture a full-page screenshot of the active Chrome tab via CDP.

    Attaches to a running Chrome instance at http://localhost:9222.
    No new browser or tab is launched.

    Returns:
        A tuple of (raw PNG bytes, base64-encoded PNG string).

    Raises:
        RuntimeError: If Chrome is not reachable on the expected CDP port.
    """
    chunks = take_browser_screenshot_chunks()
    png_bytes = stitch_png_chunks(chunks)

    img_base64 = base64.b64encode(png_bytes).decode("utf-8")
    return png_bytes, img_base64
