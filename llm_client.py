"""
LLM client module supporting OpenAI, Anthropic Claude, and Google Gemini.

Each provider receives the user's text prompt together with a base64-encoded
PNG screenshot so the model can answer questions about what is on screen.
"""

import base64
import io

from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)

# System instruction sent to every LLM.
# The assistant is general-purpose: it analyses whatever is visible on the
# screenshot (code, UI, documents, diagrams, …) and answers concisely.
SYSTEM_PROMPT = (
    "You are a helpful visual assistant. "
    "You receive a screenshot of the user's screen together with a question. "
    "Analyse the screenshot carefully and answer the question as concisely as "
    "possible. If the user explicitly asks for more detail, elaborate. "
    "You can help with anything visible on screen: code, configuration, "
    "documents, diagrams, UI elements, algorithms, and more."
)


def query_llm(prompt: str, image_base64: str) -> str:
    """
    Send *prompt* and *image_base64* (PNG) to the configured LLM provider
    and return the text response.

    Raises:
        ValueError: if LLM_PROVIDER is not one of "openai", "claude", "gemini".
        Exception:  re-raised from the underlying SDK on API errors.
    """
    provider = LLM_PROVIDER.lower()
    if provider == "openai":
        return _query_openai(prompt, image_base64)
    if provider == "claude":
        return _query_claude(prompt, image_base64)
    if provider == "gemini":
        return _query_gemini(prompt, image_base64)
    raise ValueError(
        f"Unknown LLM provider '{LLM_PROVIDER}'. "
        "Set LLM_PROVIDER to 'openai', 'claude', or 'gemini'."
    )


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _query_openai(prompt: str, image_base64: str) -> str:
    from openai import OpenAI  # imported lazily so unused providers need not be installed

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            },
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _query_claude(prompt: str, image_base64: str) -> str:
    import anthropic  # imported lazily

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.content[0].text


def _query_gemini(prompt: str, image_base64: str) -> str:
    import google.generativeai as genai  # imported lazily
    from PIL import Image

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    img_bytes = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(img_bytes))

    response = model.generate_content([f"{SYSTEM_PROMPT}\n\n{prompt}", img])
    return response.text
