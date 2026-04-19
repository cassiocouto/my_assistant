import os
from dotenv import load_dotenv

load_dotenv()

# LLM Provider: "openai", "claude", or "gemini"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# OpenAI model (default: gpt-5.4-mini which supports vision)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

# Claude model (default: claude-3-5-sonnet which supports vision)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

# Gemini model (default: gemini-1.5-flash which supports vision)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Screenshot region in pixels: top-left corner (left, top) + dimensions (width, height)
SCREENSHOT_REGION = {
    "top": int(os.getenv("SCREENSHOT_TOP", 0)),
    "left": int(os.getenv("SCREENSHOT_LEFT", 0)),
    "width": int(os.getenv("SCREENSHOT_WIDTH", 1920)),
    "height": int(os.getenv("SCREENSHOT_HEIGHT", 1080)),
}

# Browser scroll-capture region in pixels.
BROWSER_REGION = {
    "top": int(os.getenv("BROWSER_REGION_TOP", SCREENSHOT_REGION["top"])),
    "left": int(os.getenv("BROWSER_REGION_LEFT", SCREENSHOT_REGION["left"])),
    "width": int(os.getenv("BROWSER_REGION_WIDTH", SCREENSHOT_REGION["width"])),
    "height": int(os.getenv("BROWSER_REGION_HEIGHT", SCREENSHOT_REGION["height"])),
}

# Click target inside BROWSER_REGION before scrolling starts.
BROWSER_PAGE_CLICK_X = int(os.getenv("BROWSER_PAGE_CLICK_X", 20))
BROWSER_PAGE_CLICK_Y = int(os.getenv("BROWSER_PAGE_CLICK_Y", 20))

# Scroll behavior for browser mode.
BROWSER_SCROLL_INPUT_MODE = os.getenv("BROWSER_SCROLL_INPUT_MODE", "keyboard").strip().lower()
BROWSER_SCROLL_KEY = os.getenv("BROWSER_SCROLL_KEY", "PageDown").strip()
BROWSER_SCROLL_MOUSE_DELTA = -1*int(os.getenv("BROWSER_REGION_HEIGHT", 1200))
BROWSER_SCROLL_DELAY_MS = int(os.getenv("BROWSER_SCROLL_DELAY_MS", 2500))
BROWSER_SCROLL_OVERLAP = int(os.getenv("BROWSER_SCROLL_OVERLAP", 200))
BROWSER_SEND_HOME_BEFORE_CAPTURE = os.getenv("BROWSER_SEND_HOME_BEFORE_CAPTURE", "true").lower() == "true"
BROWSER_STICKY_HEADER_CROP = int(os.getenv("BROWSER_STICKY_HEADER_CROP", 0))

# Flask server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))

# Ngrok (optional) — set USE_NGROK=true and provide your auth token for remote access
USE_NGROK = os.getenv("USE_NGROK", "false").lower() == "true"
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "")
