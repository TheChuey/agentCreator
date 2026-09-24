"""
app/core/llm.py
===============

The LLM backend. Everything that talks to Ollama lives here:

    ask_llm               - send structured messages, get the reply message dict
    _resolve_model        - explicit arg > config/models.json > first Ollama model
    _get_context_window   - model context length lookup (capped)
    refresh_models        - scan installed Ollama models -> config/models.json

The Agent does not know about Ollama details; it only calls ask_llm().
"""

import json
import time
from pathlib import Path
from typing import Callable, List

import ollama

MAX_NUM_CTX = 32768
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

# How long a successful Ollama model scan is trusted before we re-list.
_MODEL_SCAN_TTL = 60.0
_model_scan_cache = {"at": -1.0, "ids": []}  # ordered list of installed model ids


# ==========================================================================
# MODEL RESOLUTION AND CONTEXT SIZING
# ==========================================================================

def _config_model_ids() -> list:
    """The model ids in config/models.json (re-scanned by refresh_models() at
    every server startup, so it reflects THIS machine's Ollama)."""
    try:
        data = json.loads((CONFIG_DIR / "models.json").read_text(encoding="utf-8"))
        return [m.get("id") for m in data.get("models", []) if m.get("id")]
    except (OSError, json.JSONDecodeError):
        return []


def _installed_model_ids() -> list:
    """Ordered ids of installed Ollama models, cached briefly.

    A failed scan keeps the previous snapshot (or [] when there was none),
    so "no models visible" and "Ollama unreachable" stay distinguishable.
    """
    global _model_scan_cache
    now = time.monotonic()
    if _model_scan_cache["ids"] and now - _model_scan_cache["at"] < _MODEL_SCAN_TTL:
        return _model_scan_cache["ids"]
    try:
        ids = []
        for m in ollama.list().get("models", []):
            mid = m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
            if mid and mid not in ids:
                ids.append(mid)
        _model_scan_cache = {"at": now, "ids": ids}
    except Exception:
        pass  # keep whatever we had before
    return _model_scan_cache["ids"]


# Per-model capabilities (ollama.show), cached per process. None = unknown
# (older Ollama that does not report capabilities yet).
_cap_cache: dict = {}


def _capabilities(model: str) -> list | None:
    """The reported capabilities for `model` (['completion', 'tools', ...])."""
    if model in _cap_cache:
        return _cap_cache[model]
    try:
        info = ollama.show(model=model).model_dump()
        caps = info.get("capabilities") or []
        _cap_cache[model] = caps
        return caps
    except Exception:
        _cap_cache[model] = None
        return None


def _supports_tools(model: str) -> bool | None:
    """True/False when Ollama reports capabilities, None when unknown."""
    caps = _capabilities(model)
    if caps is None:
        return None
    return "tools" in caps


def _resolve_model(model: str | None, require_tools: bool = False) -> str:
    """Pick which model to use: explicit arg (when suitable) > config > Ollama list.

    An explicitly requested model that is NOT installed on this machine is
    dropped so the app falls back to a detected one instead of erroring with
    a 404 - this keeps settings written on one OS (e.g. Windows) from
    breaking the app on another (e.g. Linux). When no models are visible at
    all, the explicit request is honoured as-is (previous behaviour).

    `require_tools`: when the caller needs tool calling, models that Ollama
    reports as NOT supporting tools are skipped so an agent with tools never
    gets a model that Ollama will reject with 400.
    """
    explicit = None
    if model:
        detected = set(_config_model_ids()) | set(_installed_model_ids())
        if model in detected:
            explicit = model
        elif detected:
            print(
                f"[ask_llm] requested model '{model}' is not installed locally - "
                "falling back to a detected model"
            )
        else:
            print(f"[ask_llm] no installed models visible - using requested '{model}' as-is")
            return model

    # Ordered candidates: explicit > config/models.json > live Ollama scan.
    candidates = []
    if explicit:
        candidates.append(explicit)
    for m in _config_model_ids():
        if m not in candidates:
            candidates.append(m)
    for m in _installed_model_ids():
        if m not in candidates:
            candidates.append(m)

    if require_tools:
        # Prefer models that definitely support tools; keep "unknown" ones as a
        # last resort (older Ollama), push confirmed-no-tools models to the end.
        tooled = [c for c in candidates if _supports_tools(c) is True]
        unknown = [c for c in candidates if _supports_tools(c) is None]
        others = [c for c in candidates if c not in tooled and c not in unknown]
        ordered = tooled + unknown + others
        if explicit and others and explicit in others:
            print(
                f"[ask_llm] requested model '{explicit}' does not support tools - "
                "falling back to one that does"
            )
    else:
        ordered = candidates

    if not ordered:
        raise RuntimeError(
            "No model available. Specify one in the frontend, "
            "add models to config/models.json, or install one in Ollama."
        )

    chosen = ordered[0]
    if chosen is explicit:
        print(f"[ask_llm] explicit model used: {model}")
    elif chosen in _config_model_ids():
        print(f"[ask_llm] model from config/models.json: {chosen}")
    else:
        print(f"[ask_llm] first installed Ollama model: {chosen}")
    return chosen


def _get_context_window(model: str) -> int | None:
    """Return the model's max context length from Ollama, capped; None if unknown."""
    try:
        info = ollama.show(model=model).model_dump()
        model_info = info.get("modelinfo") or info.get("model_info") or {}
        length = model_info.get("llama.context_length")
        if not length:
            return None
        return min(int(length), MAX_NUM_CTX)
    except Exception as exc:
        print(f"[ask_llm] context lookup failed for {model}: {exc}")
        return None


# ==========================================================================
# THE LLM CALL
# ==========================================================================

def ask_llm(messages: List[dict], model: str | None = None, tools: List[Callable] | None = None) -> dict:
    """Send structured messages to the resolved model via Ollama and return the full message dict."""
    resolved = _resolve_model(model, require_tools=bool(tools))

    # A model Ollama reports as NOT supporting tools must not be asked to
    # (Ollama rejects the request with 400) - drop the tool schemas and let
    # the agent answer without tool use rather than crash the chat.
    if tools and _supports_tools(resolved) is False:
        print(f"[ask_llm] model '{resolved}' does not support tools - continuing without tool use")
        tools = None

    num_ctx = _get_context_window(resolved)

    options = {"num_ctx": num_ctx} if num_ctx else {}
    print(f"[ask_llm] calling ollama.chat with model={resolved} num_ctx={num_ctx} tools={len(tools) if tools else 0}")

    for attempt in (1, 2):
        kwargs = {
            "model": resolved,
            "messages": messages,
            "options": options,
        }
        if tools:
            kwargs["tools"] = tools

        response = ollama.chat(**kwargs)
        message = response["message"]

        content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls") or []

        print(f"[ask_llm] reply received ({len(content)} chars, {len(tool_calls)} tool calls)")

        if content.strip() or tool_calls:
            return message

        print(f"[ask_llm] empty reply on attempt {attempt} - retrying")

    return {"role": "assistant", "content": "(The model returned an empty reply. Please try again.)"}


# ==========================================================================
# MODEL SCAN (startup)
# --------------------------------------------------------------------------
# Lists locally installed Ollama models and writes config/models.json so
# the frontend dropdown has something to show. An empty scan (Ollama down)
# leaves the last known good file untouched.
# ==========================================================================

def scan_models() -> list:
    """Return the deduped list of locally installed Ollama models."""
    models = []
    try:
        for m in ollama.list().get("models", []):
            model_id = m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
            size = m.get("size", 0) if isinstance(m, dict) else getattr(m, "size", 0)
            if model_id:
                models.append({"id": model_id, "name": model_id, "source": "ollama", "size": size})
    except Exception as exc:
        print(f"[llm] ollama scan failed: {exc}")

    seen, unique = set(), []
    for m in models:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique.append(m)
    return unique


def refresh_models() -> list:
    """Scan Ollama and write config/models.json (returns the model list)."""
    models = scan_models()
    models_file = CONFIG_DIR / "models.json"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if models:
        models_file.write_text(
            json.dumps({"models": models}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[llm] wrote {len(models)} models to {models_file}")
    else:
        print(f"[llm] scan found no models - keeping {models_file}")
    return models
