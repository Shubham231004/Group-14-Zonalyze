from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Ollama only exists on a developer's own machine, so every AI panel reads
# "unavailable" in the cloud deploy. Setting AI_API_KEY routes the same prompts to
# any OpenAI-compatible hosted API instead; unset = Ollama, exactly as before.
#
# Deliberately provider-agnostic (base URL + key + model) rather than hardcoded to
# one vendor — Gemini, Groq and OpenRouter all speak this protocol and their free
# tiers differ in ways that matter here. This app sends FEW, LARGE prompts (the
# operating-profile call runs 4-7k tokens), so tokens-per-minute is the binding
# limit, not requests-per-day:
#   Gemini     https://generativelanguage.googleapis.com/v1beta/openai  gemini-3.5-flash
#              generous free tier; gemini-2.5-flash* returns 404 "no longer available
#              to new users" as of Nov 2026 -- confirm your live quota in AI Studio,
#              Google stopped publishing fixed numbers on the pricing page
#   Groq       https://api.groq.com/openai/v1                           llama-3.3-70b-versatile
#              6k TPM, 14.4k req/day  <- one profile call can exhaust a minute's budget
#   OpenRouter https://openrouter.ai/api/v1                             <model>:free
#              50 req/day without credits
DEFAULT_AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_AI_MODEL = "gemini-3.5-flash-lite"


@dataclass
class LocalAIResult:
    available: bool
    answer: str
    model: str
    error: Optional[str] = None


def _base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def _hosted_api_key() -> str:
    return os.getenv("AI_API_KEY", "").strip()


def hosted_ai_enabled() -> bool:
    return bool(_hosted_api_key())


def _hosted_base_url() -> str:
    return os.getenv("AI_BASE_URL", DEFAULT_AI_BASE_URL).rstrip("/")


def _hosted_provider_name() -> str:
    """Label for status output only — derived from the configured host."""
    host = _hosted_base_url().split("//")[-1].split("/")[0]
    for known in ("groq", "openrouter", "googleapis", "openai"):
        if known in host:
            return "gemini" if known == "googleapis" else known
    return host


def _default_model() -> str:
    if hosted_ai_enabled():
        return os.getenv("AI_MODEL", DEFAULT_AI_MODEL)
    return os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def _generate_with_hosted_ai(
    prompt: str,
    model: str,
    timeout_seconds: int,
    max_tokens: int,
    json_mode: bool,
) -> LocalAIResult:
    """Same contract as the Ollama helpers: never raises, reports failure in the result."""
    if json_mode and "json" not in prompt.lower():
        # Some providers 400 in json_object mode unless the prompt mentions JSON.
        prompt = f"{prompt}\n\nRespond with a single valid JSON object."

    body: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0 if json_mode else float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(
            f"{_hosted_base_url()}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {_hosted_api_key()}"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        choices = response.json().get("choices") or []
        answer = str((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
        if not answer:
            return LocalAIResult(False, "", model, "The hosted AI returned an empty response.")
        return LocalAIResult(True, answer, model, None)
    except Exception as exc:
        detail = str(exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            # The API's own message ("model decommissioned", bad key) beats a bare 400.
            detail = f"{detail}: {exc.response.text[:300]}"
        return LocalAIResult(False, "", model, detail)


def allowed_models() -> set[str]:
    """Model names a client is permitted to request.

    The configured default is always allowed. Additional models can be
    whitelisted via OLLAMA_ALLOWED_MODELS (comma-separated).
    """
    raw = os.getenv("OLLAMA_ALLOWED_MODELS", "").strip()
    models = {name.strip() for name in raw.split(",") if name.strip()}
    models.add(_default_model())
    return models


def resolve_model(requested: Optional[str]) -> str:
    """Return a safe model name.

    A client may only pick a model from the allowlist; any other value (or none)
    falls back to the server default. This prevents callers from forcing the
    server to pull/run arbitrary Ollama models (resource-abuse / injection risk).
    """
    default = _default_model()
    if not requested:
        return default
    requested = requested.strip()
    return requested if requested in allowed_models() else default


def list_local_models(timeout_seconds: int = 3) -> List[str]:
    try:
        response = requests.get(f"{_base_url()}/api/tags", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models", []) or []
        names = []
        for model in models:
            name = model.get("name")
            if name:
                names.append(str(name))
        return names
    except Exception:
        return []


def get_ollama_version(timeout_seconds: int = 3) -> Optional[str]:
    """Return the running Ollama version string, or None if unreachable."""
    try:
        response = requests.get(f"{_base_url()}/api/version", timeout=timeout_seconds)
        response.raise_for_status()
        version = str(response.json().get("version") or "").strip()
        return version or None
    except Exception:
        return None


def _version_tuple(version: str) -> Tuple[int, ...]:
    parts: List[int] = []
    for chunk in re.split(r"[.\-+]", version or ""):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            break
    return tuple(parts)


# Ollama gained structured outputs (`format: <json schema>`) in 0.5.0.
STRUCTURED_OUTPUT_MIN_VERSION = (0, 5)


def supports_structured_outputs(version: Optional[str]) -> bool:
    if not version:
        return False
    parsed = _version_tuple(version)
    return bool(parsed) and parsed >= STRUCTURED_OUTPUT_MIN_VERSION


def schema_mode_enabled() -> bool:
    return os.getenv("OLLAMA_JSON_SCHEMA", "1").strip().lower() not in {"0", "false", "no"}


def _model_is_installed(model: str, models: List[str]) -> bool:
    """True when the configured model is actually pulled.

    Ollama reports fully-tagged names ("qwen2.5:7b-instruct", "llama3.2:3b"), and
    an untagged config value resolves to the ":latest" tag.
    """
    if not model or not models:
        return False
    return model in models or f"{model}:latest" in models


def _get_hosted_ai_status() -> Dict[str, Any]:
    """Same shape as the Ollama status so callers/UI need no changes."""
    model = _default_model()
    try:
        response = requests.get(
            f"{_hosted_base_url()}/models",
            headers={"Authorization": f"Bearer {_hosted_api_key()}"},
            timeout=6,
        )
        response.raise_for_status()
        models = [str(m.get("id")) for m in (response.json().get("data") or []) if m.get("id")]
    except Exception as exc:
        return {
            "status": "unavailable",
            "provider": _hosted_provider_name(),
            "base_url": _hosted_base_url(),
            "default_model": model,
            "available_models": [],
            "message": f"Hosted AI is not reachable or the key was rejected: {exc}",
            "ollama_version": None,
            "model_installed": False,
            "structured_outputs": False,
            "structured_outputs_note": "Unknown — the hosted AI is not reachable.",
            "warnings": ["Check AI_API_KEY / AI_BASE_URL."],
        }

    # Gemini's /models list prefixes every id with "models/" (e.g.
    # "models/gemini-3.5-flash-lite"), but chat/completions takes the bare name —
    # strip it on both sides so the comparison matches what actually works.
    bare_models = {m.rsplit("/", 1)[-1] for m in models}
    model_available = model.rsplit("/", 1)[-1] in bare_models
    return {
        "status": "ready" if model_available else "model_missing",
        "provider": _hosted_provider_name(),
        "base_url": _hosted_base_url(),
        "default_model": model,
        "available_models": models,
        "message": (
            f"Hosted AI is ready ({model})."
            if model_available
            else f"The hosted AI is reachable, but '{model}' is not in its model list. Set AI_MODEL to one of: {', '.join(models[:5])}"
        ),
        "ollama_version": None,
        "model_installed": model_available,
        "structured_outputs": True,
        "structured_outputs_note": "Hosted json_object mode is active — responses are forced to valid JSON.",
        "warnings": [] if model_available else [f"AI_MODEL='{model}' not offered by the API."],
    }


def get_local_ai_status() -> Dict[str, Any]:
    """Health check for the local AI.

    Reports what actually determines response quality: is Ollama reachable, is the
    configured model pulled, and is schema-constrained JSON (structured outputs)
    active. Each failure carries the exact command to fix it.
    """
    if hosted_ai_enabled():
        return _get_hosted_ai_status()

    base_url = _base_url()
    default_model = _default_model()
    models = list_local_models()
    version = get_ollama_version()
    reachable = bool(models) or bool(version)

    schema_enabled = schema_mode_enabled()
    version_supports_schema = supports_structured_outputs(version)
    structured_outputs = bool(schema_enabled and version_supports_schema)
    model_installed = _model_is_installed(default_model, models)

    warnings: List[str] = []
    if reachable and not model_installed:
        warnings.append(
            f"Configured model '{default_model}' is not pulled. Run: ollama pull {default_model}"
        )
    if reachable and not version_supports_schema:
        warnings.append(
            f"Ollama {version or 'version unknown'} does not support schema-constrained JSON "
            "(needs >= 0.5). Operating-profile and business-resolver quality will be lower — upgrade Ollama."
        )
    if reachable and version_supports_schema and not schema_enabled:
        warnings.append(
            "Structured outputs are disabled via OLLAMA_JSON_SCHEMA=0. Remove it for more reliable JSON."
        )

    if structured_outputs:
        structured_outputs_note = "Schema-constrained JSON is active — the model is forced to return valid, typed output."
    elif not reachable:
        structured_outputs_note = "Unknown — Ollama is not reachable."
    elif not version_supports_schema:
        structured_outputs_note = f"Not supported by Ollama {version or 'unknown'} (needs >= 0.5); using plain JSON mode."
    else:
        structured_outputs_note = "Disabled via OLLAMA_JSON_SCHEMA=0; using plain JSON mode."

    if not reachable:
        status = "unavailable"
        message = (
            "Local Ollama AI is not reachable. Install/start Ollama, then run "
            f"`ollama pull {default_model}`."
        )
    elif not model_installed:
        status = "model_missing"
        message = (
            f"Ollama is running, but the configured model '{default_model}' is not installed. "
            f"Run `ollama pull {default_model}` (or set OLLAMA_MODEL to an installed model)."
        )
    else:
        status = "ready"
        message = f"Local Ollama AI is ready ({default_model})."

    return {
        "status": status,
        "provider": "ollama",
        "base_url": base_url,
        "default_model": default_model,
        "available_models": models,
        "message": message,
        "ollama_version": version,
        "model_installed": model_installed,
        "structured_outputs": structured_outputs,
        "structured_outputs_note": structured_outputs_note,
        "warnings": warnings,
    }


# def generate_with_ollama(
#     prompt: str,
#     model: Optional[str] = None,
#     timeout_seconds: int = 90,
# ) -> LocalAIResult:
#     selected_model = model or _default_model()

#     try:
#         response = requests.post(
#             f"{_base_url()}/api/generate",
#             json={
#                 "model": selected_model,
#                 "prompt": prompt,
#                 "stream": False,
#                 "options": {
#                     "temperature": 0.2,
#                     "top_p": 0.85,
#                 },
#             },
#             timeout=timeout_seconds,
#         )
#         response.raise_for_status()
#         payload = response.json()
#         answer = str(payload.get("response", "")).strip()

#         if not answer:
#             return LocalAIResult(
#                 available=False,
#                 answer="",
#                 model=selected_model,
#                 error="Ollama returned an empty response.",
#             )

#         return LocalAIResult(
#             available=True,
#             answer=answer,
#             model=selected_model,
#             error=None,
#         )
#     except Exception as exc:
#         return LocalAIResult(
#             available=False,
#             answer="",
#             model=selected_model,
#             error=str(exc),
#         )


def generate_with_ollama(
    prompt: str,
    model: Optional[str] = None,
    timeout_seconds: int | None = None,
) -> LocalAIResult:
    selected_model = model or _default_model()
    timeout = timeout_seconds or int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

    if hosted_ai_enabled():
        return _generate_with_hosted_ai(
            prompt,
            selected_model,
            timeout,
            int(os.getenv("OLLAMA_NUM_PREDICT", "700")),
            json_mode=False,
        )

    try:
        response = requests.post(
            f"{_base_url()}/api/generate",
            json={
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
                    "top_p": 0.9,
                    # Larger context so the full scenario snapshot isn't truncated,
                    # and more output room for a complete answer.
                    "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "700")),
                    "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
                    "repeat_penalty": 1.1,
                },
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        answer = str(payload.get("response", "")).strip()

        if not answer:
            return LocalAIResult(
                available=False,
                answer="",
                model=selected_model,
                error="Ollama returned an empty response.",
            )

        return LocalAIResult(
            available=True,
            answer=answer,
            model=selected_model,
            error=None,
        )
    except Exception as exc:
        return LocalAIResult(
            available=False,
            answer="",
            model=selected_model,
            error=str(exc),
        )

def generate_json_with_ollama(
    prompt: str,
    model: Optional[str] = None,
    timeout_seconds: int | None = None,
    num_predict: int | None = None,
    json_schema: Optional[Dict[str, Any]] = None,
) -> LocalAIResult:
    """Generate JSON output from Ollama, optionally constrained to a JSON schema.

    When `json_schema` is provided (and OLLAMA_JSON_SCHEMA is not disabled), Ollama
    uses structured outputs (`format: <schema>`, Ollama >= 0.5) to *force* the model
    to emit valid JSON matching the schema. This dramatically improves reliability
    on small local models — it is what fixes the operating profile returning missing
    or $0 ranges. If schema mode is unavailable or disabled, it falls back to the
    plain `format: "json"` mode.
    """
    selected_model = model or _default_model()
    timeout = timeout_seconds or int(os.getenv("OLLAMA_JSON_TIMEOUT_SECONDS", os.getenv("OLLAMA_TIMEOUT_SECONDS", "180")))
    max_tokens = num_predict or int(os.getenv("OLLAMA_JSON_NUM_PREDICT", "2200"))

    if hosted_ai_enabled():
        # json_object mode, not schema-constrained: the schema is already spelled out
        # in these prompts, and a hosted frontier-class model follows it far more reliably than the
        # small local model this schema mode was added to rescue.
        return _generate_with_hosted_ai(prompt, selected_model, timeout, max_tokens, json_mode=True)

    use_schema = (
        json_schema is not None
        and os.getenv("OLLAMA_JSON_SCHEMA", "1").strip().lower() not in {"0", "false", "no"}
    )
    format_value: Any = json_schema if use_schema else "json"

    try:
        response = requests.post(
            f"{_base_url()}/api/generate",
            json={
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "format": format_value,
                "options": {
                    "temperature": 0.0,
                    "top_p": 0.8,
                    "num_predict": max_tokens,
                    "num_ctx": int(os.getenv("OLLAMA_JSON_NUM_CTX", "8192")),
                    "repeat_penalty": 1.05,
                },
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        answer = str(payload.get("response", "")).strip()

        if not answer:
            return LocalAIResult(
                available=False,
                answer="",
                model=selected_model,
                error="Ollama returned an empty JSON response.",
            )

        return LocalAIResult(
            available=True,
            answer=answer,
            model=selected_model,
            error=None,
        )
    except Exception as exc:
        return LocalAIResult(
            available=False,
            answer="",
            model=selected_model,
            error=str(exc),
        )
