"""
Flask application entry point.

Routes:
    GET  /         — Serve the web UI.
    POST /ask      — Receive a JSON prompt, take a screenshot, query the LLM,
                     and return the response as JSON.
    GET  /health   — Simple health-check endpoint.
"""

import logging

import config
from flask import Flask, jsonify, render_template, request
from llm_client import query_llm
from screenshot import take_screenshot

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "provider": config.LLM_PROVIDER})


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True)
    if not data or "prompt" not in data:
        return jsonify({"error": "Request body must be JSON with a 'prompt' field."}), 400

    prompt = data["prompt"].strip()
    if not prompt:
        return jsonify({"error": "Prompt cannot be empty."}), 400

    try:
        _, image_base64 = take_screenshot()
        response_text = query_llm(prompt, image_base64)
        return jsonify({"response": response_text})
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
    print(f"[info] Listening on  http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False)
