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
    "You receive a screenshot of the user's screen together with a question about what is visible. "
    "Analyse the screenshot carefully before answering. "
    "Be concise by default; elaborate only when the user explicitly asks for more detail. "
    "If the answer is not visible or determinable from the screenshot, say so clearly. "
    "You may help with any content visible on screen: code, configuration, documents, "
    "diagrams, UI elements, algorithms, and more."
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


def query_llm_multi_image(prompt: str, images_base64: list[str]) -> str:
    """
    Send *prompt* together with multiple base64-encoded PNG images to the LLM.

    All images are sent in a single API call. The model is instructed to review
    every image (which together form a vertically-split full-page screenshot)
    before producing its answer.

    Falls back to the single-image path when only one image is provided.
    """
    if len(images_base64) == 1:
        return query_llm(prompt, images_base64[0])

    provider = LLM_PROVIDER.lower()
    if provider == "openai":
        return _query_openai_multi(prompt, images_base64)
    if provider == "claude":
        return _query_claude_multi(prompt, images_base64)
    if provider == "gemini":
        return _query_gemini_multi(prompt, images_base64)
    raise ValueError(
        f"Unknown LLM provider '{LLM_PROVIDER}'. "
        "Set LLM_PROVIDER to 'openai', 'claude', or 'gemini'."
    )


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _openai_request_kwargs(prompt: str, image_base64: str) -> dict:
    return {
        "model": OPENAI_MODEL,
        "messages": [
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
    }

def _query_openai(prompt: str, image_base64: str) -> str:
    from openai import OpenAI  # imported lazily so unused providers need not be installed

    client = OpenAI(api_key=OPENAI_API_KEY)
    request_kwargs = _openai_request_kwargs(prompt, image_base64)

    response = client.chat.completions.create(**request_kwargs)
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


# ---------------------------------------------------------------------------
# Multi-image provider implementations
# ---------------------------------------------------------------------------

def _multi_image_preamble(n: int, prompt: str) -> str:
    return (
        f"I am sending you {n} screenshot{'s' if n > 1 else ''} that together form a single "
        f"full-page capture of a webpage (top to bottom, in order). "
        f"Please review all {n} image{'s' if n > 1 else ''} before answering.\n\n"
        f"{prompt}"
    )


def _query_openai_multi(prompt: str, images_base64: list[str]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

    content = [{"type": "text", "text": _multi_image_preamble(len(images_base64), prompt)}]
    for img_b64 in images_base64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    return response.choices[0].message.content


def _query_claude_multi(prompt: str, images_base64: list[str]) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    content = []
    for img_b64 in images_base64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
        })
    content.append({"type": "text", "text": _multi_image_preamble(len(images_base64), prompt)})

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text


def _query_gemini_multi(prompt: str, images_base64: list[str]) -> str:
    import google.generativeai as genai
    from PIL import Image

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    parts = [_multi_image_preamble(len(images_base64), prompt)]
    for img_b64 in images_base64:
        img_bytes = base64.b64decode(img_b64)
        parts.append(Image.open(io.BytesIO(img_bytes)))

    response = model.generate_content(parts)
    return response.text
