# My Assistant

A general-purpose visual assistant that runs on your computer and lets you ask questions — from any device on the same network — about whatever is currently on your screen.

**Examples of things you can ask:**

- *"What does this function do?"*
- *"Where is the configuration for X in this UI?"*
- *"What is the best approach to optimize the LeetCode problem shown?"*
- *"Explain the error message on screen."*
- *"Summarise this document."*

The assistant captures a configurable area of your screen (or a full-page screenshot of the active Chrome tab), sends it together with your question to an LLM (OpenAI, Claude, or Gemini), and streams the answer back to your browser.

---

## How It Works

```
Phone / tablet / laptop (browser)
        │
        │  HTTP POST /ask  {"prompt": "…", "mode": "screen" | "browser"}
        ▼
  Flask server  (your computer)
        │
        ├── takes screenshot (screen region OR active Chrome tab)
        ├── sends screenshot + prompt to LLM API
        └── returns text answer to browser
```

Remote access (from outside your local network) is supported via **ngrok**.

---

## Requirements

- Python 3.10+
- A display / screen (the app captures it)
- An API key for at least one LLM provider
- *(Browser mode only)* Google Chrome launched with `--remote-debugging-port=9222`

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/cassiocouto/my_assistant.git
cd my_assistant

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Browser mode only) Install the Playwright browser
playwright install chromium
```

---

## Configuration

### 1. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in the values described below.

### 2. Choose your LLM provider

Set `LLM_PROVIDER` to one of: `openai`, `claude`, `gemini`.

| Provider | Variable | Where to get a key |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| Anthropic Claude | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| Google Gemini | `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |

Only fill in the key for the provider you chose. Example for OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

#### Overriding the model (optional)

The defaults are `gpt-5.4-mini`, `claude-3-5-sonnet-20241022`, and `gemini-1.5-flash` respectively. You can override them:

```env
OPENAI_MODEL=gpt-4o
CLAUDE_MODEL=claude-3-haiku-20240307
GEMINI_MODEL=gemini-1.5-pro
```

For OpenAI, both older vision-capable GPT-4 models and newer GPT-5 models are supported. The app does not force an output-token cap for OpenAI requests, which avoids parameter mismatches across model families.

### 3. Configure the screenshot region

The assistant captures a rectangular region of your screen. You need to tell it which region.

**Run the interactive helper:**

```bash
python setup_region.py
```

The helper shows your monitor dimensions, asks for the region coordinates, and optionally saves a preview image so you can verify it looks right.

Copy the printed values into your `.env` file:

```env
SCREENSHOT_LEFT=0
SCREENSHOT_TOP=0
SCREENSHOT_WIDTH=1920
SCREENSHOT_HEIGHT=1080
```

**Tip:** Set the region to cover only the area you care about (e.g., a specific window or monitor) so the LLM has the most relevant context.

### 4. (Optional) Configure browser screenshot mode

Browser mode captures a **full-page screenshot** of the active Chrome tab instead of a screen region. No region coordinates are needed.

**Prerequisites:**

1. Install Playwright (already in `requirements.txt`) and its browser:
   ```bash
   playwright install chromium
   ```

2. Launch Chrome with the remote debugging port enabled:
   ```bash
   # Windows
   chrome.exe --remote-debugging-port=9222

   # macOS
   open -a "Google Chrome" --args --remote-debugging-port=9222

   # Linux
   google-chrome --remote-debugging-port=9222
   ```

3. Verify the setup with the interactive test helper:
   ```bash
   python test_browser_screenshot.py
   ```
   The helper connects to Chrome, lists open tabs, captures a full-page screenshot, and saves a preview to `tmp/browser_preview.png`.

4. In the web UI, select **Full page (Chrome)** before asking a question — or include `"mode": "browser"` in your `POST /ask` request.

---

## Running the Application

```bash
python app.py
```

You should see output like:

```
[info] LLM provider : openai
[info] Screenshot   : {'top': 0, 'left': 0, 'width': 1920, 'height': 1080}
[info] Listening on  http://0.0.0.0:5000
```

Open **http://localhost:5000** in your browser to use the assistant locally.

---

## Accessing from Another Device on the Same Network

1. Find your computer's local IP address:
   - **macOS / Linux:** `ip route get 1 | awk '{print $7}'` or `hostname -I`
   - **Windows:** `ipconfig` → look for *IPv4 Address*

2. On the other device, open a browser and go to:
   ```
   http://<your-computer-ip>:5000
   ```
   For example: `http://192.168.1.42:5000`

> Make sure your firewall allows inbound connections on port 5000.

---

## Remote Access via ngrok (Optional)

ngrok creates a public HTTPS URL that tunnels to your local server — useful when the client device is outside your local network.

### Steps

1. Sign up for a free account at https://ngrok.com and copy your auth token.

2. Add to your `.env`:

   ```env
   USE_NGROK=true
   NGROK_AUTH_TOKEN=your_token_here
   ```

3. Start the application normally:

   ```bash
   python app.py
   ```

   The terminal will print a line like:

   ```
   [ngrok] Public URL: NgrokTunnel: "https://abc123.ngrok-free.app" -> "http://localhost:5000"
   ```

4. Open that URL on any device — phone, tablet, another laptop — from anywhere.

---

## Project Structure

```
my_assistant/
├── app.py                      # Flask web server (routes and entry point)
├── config.py                   # All configuration loaded from .env
├── screenshot.py               # Screen capture logic (screen region + browser mode)
├── llm_client.py               # LLM provider integrations (OpenAI / Claude / Gemini)
├── setup_region.py             # Interactive helper to find screenshot coordinates
├── test_browser_screenshot.py  # Interactive helper to verify browser screenshot mode
├── requirements.txt            # Python dependencies
├── .env.example                # Template for your .env file
├── templates/
│   └── index.html              # Web UI (mobile-friendly, includes mode selector)
└── tests/
    └── test_app.py             # Unit tests
```

---

## Running the Tests

```bash
python -m pytest tests/ -v
```

Tests mock all external dependencies (LLM APIs, screen capture) and run without a display or real API keys.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `mss` / screenshot errors on Linux | Install a virtual display: `sudo apt install xvfb` then run `Xvfb :99 &` and set `export DISPLAY=:99` |
| `APIConnectionError` | Check your API key and internet connection |
| Port already in use | Change `PORT=5001` in `.env` |
| Black screenshot | Make sure the region is inside your screen bounds (run `python setup_region.py`) |
| ngrok error | Verify `NGROK_AUTH_TOKEN` is correct and `pyngrok` is installed |
| Browser mode: "Could not connect to Chrome" | Launch Chrome with `--remote-debugging-port=9222` (see browser mode setup above) |
| Browser mode: blank/wrong page captured | Navigate to the desired page in Chrome before asking; the assistant picks the first non-blank tab |
| `playwright` not found | Run `pip install playwright` then `playwright install chromium` |