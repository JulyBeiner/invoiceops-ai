"""AI provider access: the AI reads and proposes; the engine computes;
the person confirms.

This module is the only place that talks to an AI provider. It uses the
provider's REST API through `requests` (no SDK). Routes always call
`complete()` and `transcribe()` through the module (`ai.complete(...)`), so
tests can replace them with a fake and never touch the network.

Configuration (environment variables, never in the repo):
  AI_PROVIDER     "openai" (default) or "gemini"
  AI_API_KEY      the provider's key; without it the AI features answer 503
  AI_MODEL        optional, overrides the default text/vision model
  AI_AUDIO_MODEL  optional, overrides the default transcription model
"""
import base64
import json
import os

import requests

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_AUDIO_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_AUDIO_MODEL = "whisper-1"

GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "{model}:generateContent")
GEMINI_MODEL = "gemini-2.5-flash"

TIMEOUT = 60  # seconds; images and audio can take a while


class AIError(Exception):
    """The provider could not be reached or returned an unusable answer."""


def provider():
    return (os.getenv("AI_PROVIDER") or "openai").strip().lower()


def is_configured():
    return bool(os.getenv("AI_API_KEY"))


def _model():
    return os.getenv("AI_MODEL") or (
        GEMINI_MODEL if provider() == "gemini" else OPENAI_MODEL)


def _audio_model():
    return os.getenv("AI_AUDIO_MODEL") or OPENAI_AUDIO_MODEL


def _parse_json(text):
    """The models are asked to answer ONLY with JSON; tolerate ``` fences."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise AIError(f"AI did not answer with valid JSON: {error}") from error


def complete(prompt, system=None, images=None, want_json=True):
    """Ask the model. `images` is a list of (bytes, mime_type).

    Returns a dict when want_json is True, else the answer text.
    """
    if not is_configured():
        raise AIError("AI is not configured")
    if provider() == "gemini":
        text = _gemini_complete(prompt, system, images or [], want_json)
    else:
        text = _openai_complete(prompt, system, images or [], want_json)
    return _parse_json(text) if want_json else text


def transcribe(audio_bytes, filename, mime_type):
    """Turn a voice note into text (Spanish)."""
    if not is_configured():
        raise AIError("AI is not configured")
    if provider() == "gemini":
        return _gemini_transcribe(audio_bytes, mime_type)
    return _openai_transcribe(audio_bytes, filename, mime_type)


# --- OpenAI ---------------------------------------------------------------

def _openai_headers():
    return {"Authorization": f"Bearer {os.getenv('AI_API_KEY')}"}


def _openai_complete(prompt, system, images, want_json):
    content = [{"type": "text", "text": prompt}]
    for data, mime_type in images:
        encoded = base64.b64encode(data).decode()
        content.append({"type": "image_url", "image_url": {
            "url": f"data:{mime_type};base64,{encoded}"}})
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})
    body = {"model": _model(), "messages": messages,
            "max_completion_tokens": 4000}
    if want_json:
        body["response_format"] = {"type": "json_object"}
    data = _post_json(OPENAI_CHAT_URL, body, _openai_headers())
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIError("unexpected answer from OpenAI") from error


def _openai_transcribe(audio_bytes, filename, mime_type):
    try:
        response = requests.post(
            OPENAI_AUDIO_URL, headers=_openai_headers(),
            files={"file": (filename, audio_bytes, mime_type)},
            data={"model": _audio_model(), "language": "es"},
            timeout=TIMEOUT)
    except requests.RequestException as error:
        raise AIError(f"could not reach OpenAI: {error}") from error
    if response.status_code >= 400:
        raise AIError(f"OpenAI answered {response.status_code}: "
                      f"{response.text[:300]}")
    return response.json().get("text", "")


# --- Gemini ---------------------------------------------------------------

def _gemini_complete(prompt, system, images, want_json):
    parts = [{"text": prompt}]
    for data, mime_type in images:
        parts.append({"inline_data": {
            "mime_type": mime_type, "data": base64.b64encode(data).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}]}
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    if want_json:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    url = GEMINI_URL.format(model=_model())
    data = _post_json(url, body, {"x-goog-api-key": os.getenv("AI_API_KEY")})
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIError("unexpected answer from Gemini") from error


def _gemini_transcribe(audio_bytes, mime_type):
    return _gemini_complete(
        "Transcribe esta nota de voz en español, palabra por palabra. "
        "Responde solo con el texto transcrito.",
        None, [(audio_bytes, mime_type)], want_json=False).strip()


# --- shared ---------------------------------------------------------------

def _post_json(url, body, headers):
    try:
        response = requests.post(
            url, json=body, headers={**headers,
                                     "Content-Type": "application/json"},
            timeout=TIMEOUT)
    except requests.RequestException as error:
        raise AIError(f"could not reach the AI provider: {error}") from error
    if response.status_code >= 400:
        raise AIError(f"AI provider answered {response.status_code}: "
                      f"{response.text[:300]}")
    return response.json()
