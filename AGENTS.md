# AGENTS.md — Project Context for AI Agents

## What this project is

A general-purpose **visual assistant** that runs as a local Flask server. It captures a configurable region of the host screen (or, in browser mode, a full-page screenshot of the active Chrome tab), sends the image together with the user's text prompt to an LLM, and returns the answer to a web UI. The UI is accessible from any device on the same local network.

---

## File map

| File | Purpose |
|---|---|
| `app.py` | Flask entrypoint. Routes: `GET /`, `POST /ask`, `GET /health`. Orchestrates screenshot capture and LLM call. |
| `config.py` | All configuration, read from environment variables via `python-dotenv`. Single source of truth for keys, models, screenshot region, host/port, and ngrok settings. |
| `llm_client.py` | Provider-agnostic LLM interface. `query_llm(prompt, image_base64)` dispatches to `_query_openai`, `_query_claude`, or `_query_gemini`. Providers are imported lazily. |
| `screenshot.py` | Screenshot capture. `take_screenshot()` uses `mss` for a screen-region capture. Browser mode attaches to a running Chrome via CDP using Playwright, captures a full-page image, and can split that image into vertical chunks for LLM submission. |
| `setup_region.py` | One-time interactive helper to find the correct `SCREENSHOT_*` `.env` values. |
| `test_browser_screenshot.py` | Interactive helper to verify browser screenshot mode. Connects to Chrome via CDP, captures a full-page screenshot, and saves a preview to `tmp/browser_preview.png`. |
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
- Attaches to a **running** Chrome instance via Chrome DevTools Protocol (CDP).
- Chrome **must** be launched with `--remote-debugging-port=9222`. No new browser or tab is opened.
- Uses Playwright (`playwright` package + `playwright install chromium` one-time setup).
- Captures a full-page image of the active tab and may split that image into multiple vertical PNG chunks before sending it to the LLM.
- `POST /ask` body: `{"prompt": "...", "mode": "browser"}`.
- If Chrome is unreachable, the server returns HTTP 400 with an explanatory error message.

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
