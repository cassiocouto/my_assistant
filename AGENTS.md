# AGENTS.md — Project Context for AI Agents

## What this project is

A general-purpose **visual assistant** that runs as a local Flask server. It captures a configurable region of the host screen (or, in browser mode, a calibrated visible browser region with scroll capture), sends the image together with the user's text prompt to an LLM, and returns the answer to a web UI. The UI is accessible from any device on the same local network.

---

## File map

| File | Purpose |
|---|---|
| `app.py` | Flask entrypoint. Routes: `GET /`, `POST /ask`, `GET /health`. Orchestrates screenshot capture and LLM call. |
| `config.py` | All configuration, read from environment variables via `python-dotenv`. Single source of truth for keys, models, screenshot region, host/port, and ngrok settings. |
| `llm_client.py` | Provider-agnostic LLM interface. `query_llm(prompt, image_base64)` dispatches to `_query_openai`, `_query_claude`, or `_query_gemini`. Providers are imported lazily. |
| `screenshot.py` | Screenshot capture. `take_screenshot()` uses `mss` for a screen-region capture. Browser mode uses calibrated on-screen scroll capture, generating multiple vertically ordered PNG chunks for LLM submission. |
| `setup_region.py` | One-time interactive helper to find the correct `SCREENSHOT_*` `.env` values. |
| `test_browser_screenshot.py` | Interactive helper to calibrate browser mode. Previews configured region + click point, runs a short scroll-capture sequence, and saves raw frames plus stitched preview in `tmp/`. |
| `templates/index.html` | Single-page UI. Dark theme. Renders markdown + KaTeX math in responses. Sends `POST /ask` with `{prompt, mode}`. |
| `requirements.txt` | Core dependencies. LLM provider packages are optional (install only the one in use). |
| `tmp/` | Scratch directory for preview images from `setup_region.py` and browser debug artifacts (full screenshot + chunk PNGs). Ignored by version control. |

---

## Configuration (`.env`)

All settings are read by `config.py`. Copy `.env.example` to `.env` and fill in:

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai`, `claude`, or `gemini` |
| `OPENAI_API_KEY` | — | Required when provider is `openai` |
| `ANTHROPIC_API_KEY` | — | Required when provider is `claude` |
| `GEMINI_API_KEY` | — | Required when provider is `gemini` |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Vision-capable model required |
| `CLAUDE_MODEL` | `claude-3-5-sonnet-20241022` | Vision-capable model required |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Vision-capable model required |
| `SCREENSHOT_TOP/LEFT/WIDTH/HEIGHT` | full screen | Pixel coordinates of capture region |
| `BROWSER_REGION_TOP/LEFT/WIDTH/HEIGHT` | `SCREENSHOT_*` values | Pixel coordinates for browser scroll-capture region |
| `BROWSER_PAGE_CLICK_X/Y` | `20/20` | Click point inside browser region used to focus page |
| `BROWSER_SCROLL_INPUT_MODE` | `keyboard` | `keyboard` or `mouse` |
| `BROWSER_SCROLL_KEY` | `PageDown` | Keyboard key used when input mode is keyboard |
| `BROWSER_SCROLL_MOUSE_DELTA` | `-1200` | Mouse wheel delta used when input mode is mouse |
| `BROWSER_SCROLL_DELAY_MS` | `5000` | Delay between scroll and next capture |
| `BROWSER_SCROLL_OVERLAP` | `200` | Fixed overlap trim from each subsequent frame |
| `BROWSER_SEND_HOME_BEFORE_CAPTURE` | `true` | Send `Home` key before first capture |
| `BROWSER_STICKY_HEADER_CROP` | `0` | Additional top crop on subsequent frames |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5000` | Flask port |
| `USE_NGROK` | `false` | Set `true` for remote access via ngrok |
| `NGROK_AUTH_TOKEN` | — | Required when `USE_NGROK=true` |

---

## Screenshot modes

### Screen region (default)
- Uses `mss` to capture a configurable pixel region of the host display.
- Region is set via `SCREENSHOT_*` env vars; use `setup_region.py` to determine values.
- `POST /ask` body: `{"prompt": "...", "mode": "screen"}` (or omit `mode`).

### Full-page browser (Chrome only)
- Captures a visible browser page from a calibrated on-screen region (`BROWSER_REGION_*`).
- Clicks inside the configured page content point before capture (`BROWSER_PAGE_CLICK_X/Y`).
- Scrolls with keyboard (default) or mouse wheel, waits for lazy content, and keeps capturing until 3 consecutive unchanged frames.
- Applies fixed overlap and optional sticky-header trimming, then returns multiple vertical PNG chunks in order.
- Browser window placement is calibration/setup; no browser chrome/tab-strip/taskbar auto-detection is performed.
- `POST /ask` body: `{"prompt": "...", "mode": "browser"}`.
- Browser mode may briefly control local input; keep the browser visible and avoid user interaction during capture.

---

## `POST /ask` API

**Request**
```json
{
  "prompt": "What does this function do?",
  "mode": "screen"
}
```
`mode` is optional and defaults to `"screen"`. Valid values: `"screen"`, `"browser"`.

**Response (success)**
```json
{ "response": "This function iterates over…" }
```

**Response (error)**
```json
{ "error": "Descriptive error message." }
```

---

## Adding a new LLM provider

1. Add the API key and model name to `config.py` (import from env).
2. Add a `_query_<provider>()` function in `llm_client.py` following the existing pattern (lazy import, returns a plain string).
3. Add a branch in `query_llm()` to dispatch to it.
4. Update the `ValueError` message listing valid provider names.
5. Add the SDK to `requirements.txt` with an appropriate comment.

---

## Running the app

```bash
# activate venv first
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

python app.py
# → http://localhost:5000
```

---

## Running tests

```bash
pytest tests/
```

Tests live in `tests/test_app.py` and use Flask's test client.

---

## Key conventions

- **No global state** beyond config constants — each request is self-contained.
- **Lazy provider imports** — only the SDK for the active provider needs to be installed.
- `llm_client.py` is intentionally provider-agnostic; it only receives `(prompt: str, image_base64: str)` and returns `str`.
- The UI sends mode as a plain JSON field; the server is the only place that acts on it.
- Do not store screenshots on disk during normal operation; they are held in memory and discarded after the LLM response is returned.
- Browser mode still submits multiple PNG chunks through the multi-image LLM path.
