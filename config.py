import os
from dotenv import load_dotenv

load_dotenv()

# LLM Provider: "openai", "claude", or "gemini"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# OpenAI model (default: gpt-4o which supports vision)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

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

# Flask server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))

# Ngrok (optional) — set USE_NGROK=true and provide your auth token for remote access
USE_NGROK = os.getenv("USE_NGROK", "false").lower() == "true"
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "")
