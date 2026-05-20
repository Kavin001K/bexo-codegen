"""
Task-based LLM routing: DeepSeek + Kimi (direct APIs) with optional OpenRouter fallback.

| Task              | Provider  | Default model              |
|-------------------|-----------|----------------------------|
| spec / personality| DeepSeek  | deepseek-chat              |
| HTML generation   | Kimi      | kimi-k2-turbo-preview      |
| HTML fix loop     | DeepSeek  | deepseek-chat              |
| moderation        | DeepSeek  | deepseek-chat              |
"""

from __future__ import annotations

import os
from typing import Literal

import requests

Task = Literal["spec", "generate", "fix", "moderation"]

PROVIDERS = {
    "deepseek": {
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "kimi": {
        "base_url": os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1"),
        "api_key_env": "KIMI_API_KEY",
    },
    "openrouter": {
        "base_url": os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "api_key_env": "OPENROUTER_API_KEY",
    },
}

# task -> (provider, model env var, default model)
TASK_ROUTING: dict[Task, tuple[str, str, str]] = {
    "spec": ("deepseek", "DEEPSEEK_MODEL_SPEC", "deepseek-chat"),
    "generate": ("kimi", "KIMI_MODEL_GENERATE", "kimi-k2-turbo-preview"),
    "fix": ("deepseek", "DEEPSEEK_MODEL_FIX", "deepseek-chat"),
    "moderation": ("deepseek", "DEEPSEEK_MODEL_MODERATION", "deepseek-chat"),
}

# OpenRouter model IDs — default to free tier (see openrouter.ai/collections/free-models)
_OPENROUTER_FREE_DEFAULT = "openrouter/free"
OPENROUTER_MODELS: dict[Task, str] = {
    "spec": os.environ.get("OPENROUTER_MODEL_SPEC", _OPENROUTER_FREE_DEFAULT),
    "generate": os.environ.get("OPENROUTER_MODEL_GENERATE", _OPENROUTER_FREE_DEFAULT),
    "fix": os.environ.get("OPENROUTER_MODEL_FIX", _OPENROUTER_FREE_DEFAULT),
    "moderation": os.environ.get("OPENROUTER_MODEL_MODERATION", _OPENROUTER_FREE_DEFAULT),
}

FALLBACK_CHAIN: dict[Task, list[tuple[str, str]]] = {
    "generate": [
        ("kimi", os.environ.get("KIMI_MODEL_GENERATE", "kimi-k2-turbo-preview")),
        ("deepseek", os.environ.get("DEEPSEEK_MODEL_GENERATE_FALLBACK", "deepseek-chat")),
        ("openrouter", OPENROUTER_MODELS["generate"]),
    ],
    "fix": [
        ("deepseek", os.environ.get("DEEPSEEK_MODEL_FIX", "deepseek-chat")),
        ("openrouter", OPENROUTER_MODELS["fix"]),
    ],
}


class LLMError(Exception):
    pass


def _api_key(provider: str) -> str | None:
    env_name = PROVIDERS[provider]["api_key_env"]
    return os.environ.get(env_name, "").strip() or None


def _use_openrouter_only() -> bool:
    return bool(_api_key("openrouter")) and not _api_key("deepseek") and not _api_key("kimi")


def _openrouter_free_only() -> bool:
    return os.environ.get("OPENROUTER_FREE_ONLY", "").lower() in ("1", "true", "yes")


def _cap_max_tokens(provider: str, model: str, requested: int) -> int:
    if provider != "openrouter":
        return requested
    cap = int(os.environ.get("OPENROUTER_MAX_TOKENS", "4096"))
    if ":free" in model or model == "openrouter/free":
        cap = min(cap, int(os.environ.get("OPENROUTER_FREE_MAX_TOKENS", "4096")))
    return min(requested, cap)


def _chat(
    provider: str,
    model: str,
    messages: list[dict],
    *,
    system: str | None = None,
    max_tokens: int = 8000,
    temperature: float = 0.4,
) -> str:
    if provider == "openrouter":
        key = _api_key("openrouter")
        if not key:
            raise LLMError("OPENROUTER_API_KEY not set")
        base = PROVIDERS["openrouter"]["base_url"].rstrip("/")
    elif provider == "deepseek":
        key = _api_key("deepseek")
        if not key:
            raise LLMError("DEEPSEEK_API_KEY not set")
        base = PROVIDERS["deepseek"]["base_url"].rstrip("/")
    elif provider == "kimi":
        key = _api_key("kimi")
        if not key:
            raise LLMError("KIMI_API_KEY not set")
        base = PROVIDERS["kimi"]["base_url"].rstrip("/")
    else:
        raise LLMError(f"Unknown provider: {provider}")

    payload_messages = []
    if system:
        payload_messages.append({"role": "system", "content": system})
    payload_messages.extend(messages)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = os.environ.get("OPENROUTER_REFERER", "https://mybexo.com")
        headers["X-Title"] = "BEXO Codegen"

    effective_tokens = _cap_max_tokens(provider, model, max_tokens)

    url = f"{base}/chat/completions"
    resp = requests.post(
        url,
        headers=headers,
        json={
            "model": model,
            "messages": payload_messages,
            "max_tokens": effective_tokens,
            "temperature": temperature,
        },
        timeout=180,
    )

    if resp.status_code >= 400:
        raise LLMError(f"{provider}/{model} HTTP {resp.status_code}: {resp.text[:400]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Invalid response from {provider}: {data}") from e


def complete(
    task: Task,
    messages: list[dict],
    *,
    system: str | None = None,
    max_tokens: int = 8000,
) -> str:
    """Run completion for a pipeline task with provider-specific model."""
    if _openrouter_free_only() and _api_key("openrouter"):
        model = OPENROUTER_MODELS[task]
        print(f"[LLM] task={task} provider=openrouter (free-only) model={model}")
        return _chat("openrouter", model, messages, system=system, max_tokens=max_tokens)

    if _use_openrouter_only():
        model = OPENROUTER_MODELS[task]
        print(f"[LLM] task={task} provider=openrouter model={model}")
        return _chat("openrouter", model, messages, system=system, max_tokens=max_tokens)

    if task == "generate" and _api_key("kimi"):
        chain = FALLBACK_CHAIN["generate"]
    elif task == "fix" and _api_key("deepseek"):
        chain = FALLBACK_CHAIN.get("fix", [])
    else:
        provider, model_env, default_model = TASK_ROUTING[task]
        model = os.environ.get(model_env, default_model)
        chain = [(provider, model)]

    if not chain:
        provider, model_env, default_model = TASK_ROUTING[task]
        chain = [(provider, os.environ.get(model_env, default_model))]

    last_err: Exception | None = None
    for provider, model in chain:
        if provider != "openrouter" and not _api_key(provider):
            continue
        if provider == "openrouter" and not _api_key("openrouter"):
            continue
        try:
            print(f"[LLM] task={task} provider={provider} model={model}")
            return _chat(provider, model, messages, system=system, max_tokens=max_tokens)
        except Exception as e:
            last_err = e
            print(f"[LLM] fallback: {provider}/{model} failed: {e}")
            continue

    raise LLMError(f"All models failed for task={task}: {last_err}")
