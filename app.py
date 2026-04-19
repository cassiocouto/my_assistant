"""
Flask application entry point.

Routes:
    GET  /         — Serve the web UI.
    POST /ask      — Receive a JSON prompt, take a screenshot, query the LLM,
                     and return the response as JSON.
    GET  /health   — Simple health-check endpoint.
"""

import base64
import logging
from datetime import datetime
from pathlib import Path

import config
from flask import Flask, jsonify, render_template, request
from llm_client import query_llm, query_llm_multi_image
from screenshot import take_browser_screenshot_chunks, take_screenshot

app = Flask(__name__)
logger = logging.getLogger(__name__)


def _save_browser_debug_artifacts(chunks: list[bytes]) -> str:
    tmp_dir = Path(__file__).resolve().parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base_name = f"browser_debug_{stamp}"

    for index, chunk in enumerate(chunks, start=1):
        chunk_path = tmp_dir / f"{base_name}_chunk_{index:02d}.png"
        chunk_path.write_bytes(chunk)

    logger.info("[browser-debug] saved %d chunk(s) under prefix: %s", len(chunks), base_name)
    return base_name


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "provider": config.LLM_PROVIDER})


@app.route("/capture-config")
def capture_config():
    return jsonify(
        {
            "screen_region": config.SCREENSHOT_REGION,
            "browser": {
                "region": config.BROWSER_REGION,
                "page_click": {
                    "x": config.BROWSER_PAGE_CLICK_X,
                    "y": config.BROWSER_PAGE_CLICK_Y,
                    "screen_x": config.BROWSER_REGION["left"] + config.BROWSER_PAGE_CLICK_X,
                    "screen_y": config.BROWSER_REGION["top"] + config.BROWSER_PAGE_CLICK_Y,
                },
                "scroll": {
                    "input_mode": config.BROWSER_SCROLL_INPUT_MODE,
                    "key": config.BROWSER_SCROLL_KEY,
                    "mouse_delta": config.BROWSER_SCROLL_MOUSE_DELTA,
                    "delay_ms": config.BROWSER_SCROLL_DELAY_MS,
                    "send_home_before_capture": config.BROWSER_SEND_HOME_BEFORE_CAPTURE,
                    "unchanged_frame_limit": 3,
                },
            },
        }
    )


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True)
    if not data or "prompt" not in data:
        return jsonify({"error": "Request body must be JSON with a 'prompt' field."}), 400

    prompt = data["prompt"].strip()
    if not prompt:
        return jsonify({"error": "Prompt cannot be empty."}), 400

    mode = data.get("mode", "screen")

    try:
        if mode == "browser":
            chunks = take_browser_screenshot_chunks()
            debug_prefix = _save_browser_debug_artifacts(chunks)
            images_b64 = [base64.b64encode(c).decode() for c in chunks]
            logger.info("[browser-debug] prompt (%s): %s", debug_prefix, prompt)
            response_text = query_llm_multi_image(prompt, images_b64)
            logger.info("[browser-debug] response (%s): %s", debug_prefix, response_text)
        else:
            _, image_base64 = take_screenshot()
            response_text = query_llm(prompt, image_base64)
        return jsonify({"response": response_text})
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error processing request")
        return jsonify({"error": "An error occurred while processing your request. Check the server logs for details."}), 500


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if config.USE_NGROK:
        try:
            from pyngrok import ngrok

            if config.NGROK_AUTH_TOKEN:
                ngrok.set_auth_token(config.NGROK_AUTH_TOKEN)
            public_url = ngrok.connect(config.PORT)
            print(f"[ngrok] Public URL: {public_url}")
        except ImportError:
            print("[warning] pyngrok is not installed — ngrok tunnel skipped.")

    print(f"[info] LLM provider : {config.LLM_PROVIDER}")
    print(f"[info] Screenshot   : {config.SCREENSHOT_REGION}")
    print(f"[info] Browser mode : region={config.BROWSER_REGION}, scroll={config.BROWSER_SCROLL_INPUT_MODE}")
    print(f"[info] Listening on  http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False)
