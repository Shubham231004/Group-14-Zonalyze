from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


@dataclass
class LocalAIResult:
    available: bool
    answer: str
    model: str
    error: Optional[str] = None


def _base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def _default_model() -> str:
    return os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


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


def get_local_ai_status() -> Dict[str, Any]:
    """Health check for the local AI.

    Reports what actually determines response quality: is Ollama reachable, is the
    configured model pulled, and is schema-constrained JSON (structured outputs)
    active. Each failure carries the exact command to fix it.
    """
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
