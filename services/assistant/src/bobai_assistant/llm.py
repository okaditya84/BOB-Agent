"""Provider-agnostic LLM access via llm-rotate.

The registry is built dynamically from environment variables: any provider whose
key is present is wired up, multiple comma-separated keys per provider become
rotatable credentials, and a cross-provider fallback chain is configured for the
default model. Switching provider/model is purely an env change — no code edits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Provider definitions. Built-in llm-rotate providers (openai/anthropic/google/
# openrouter) need only a key; OpenAI-compatible ones (groq/nvidia) are registered
# as custom providers with their base_url.
PROVIDER_DEFS: dict[str, dict] = {
    "openai":     {"env": "OPENAI_API_KEY",     "adapter": "openai",    "base_url": None,
                   "default_model": "gpt-4o-mini", "custom": False},
    "anthropic":  {"env": "ANTHROPIC_API_KEY",  "adapter": "anthropic", "base_url": None,
                   "default_model": "claude-3-5-haiku-latest", "custom": False},
    "google":     {"env": "GOOGLE_API_KEY",     "adapter": "google",    "base_url": None,
                   "default_model": "gemini-1.5-flash", "custom": False},
    "openrouter": {"env": "OPENROUTER_API_KEY", "adapter": "openai",
                   "base_url": "https://openrouter.ai/api/v1",
                   "default_model": "openai/gpt-4o-mini", "custom": False},
    "groq":       {"env": "GROQ_API_KEY",       "adapter": "openai",
                   "base_url": "https://api.groq.com/openai/v1",
                   "default_model": "llama-3.3-70b-versatile", "custom": True},
    "nvidia":     {"env": "NVIDIA_API_KEY",     "adapter": "openai",
                   "base_url": "https://integrate.api.nvidia.com/v1",
                   "default_model": "meta/llama-3.1-70b-instruct", "custom": True},
}


@dataclass
class Registry:
    providers: dict[str, dict] = field(default_factory=dict)
    keys: list[dict] = field(default_factory=list)
    use_keys: list[str] = field(default_factory=list)
    fallback_chains: dict[str, list[dict]] = field(default_factory=dict)
    configured: list[str] = field(default_factory=list)
    # Synthetic env vars that configure_llm must set (for multi-key rotation).
    env_to_set: dict[str, str] = field(default_factory=dict)


def build_registry(env: dict, default_provider: str, default_model: str) -> Registry:
    """Pure: construct the llm-rotate registry from an env mapping (no side effects)."""
    reg = Registry()
    for name, d in PROVIDER_DEFS.items():
        raw = env.get(d["env"])
        if not raw:
            continue
        reg.configured.append(name)

        if d["custom"]:
            reg.providers[name] = {
                "name": name, "display_name": name.title(), "provider_type": "direct",
                "adapter": d["adapter"], "base_url": d["base_url"],
            }

        secrets = [s.strip() for s in raw.split(",") if s.strip()]
        for i, secret in enumerate(secrets):
            models = [d["default_model"]]
            if name == default_provider and default_model not in models:
                models.append(default_model)
            if len(secrets) == 1:
                secret_ref = f"env://{d['env']}"
            else:
                synth = f"LLMROTATE_{name.upper()}_{i}"
                reg.env_to_set[synth] = secret
                secret_ref = f"env://{synth}"
            key_id = f"{name}-{i}"
            reg.keys.append(
                {"key_id": key_id, "provider": name, "secret_ref": secret_ref, "models": models}
            )
            reg.use_keys.append(key_id)

    fallback = [
        {"provider": p, "model": PROVIDER_DEFS[p]["default_model"]}
        for p in reg.configured
        if p != default_provider
    ]
    if fallback:
        reg.fallback_chains[default_model] = fallback
    return reg


def configure_llm(env: dict | None = None, *, default_provider: str, default_model: str) -> Registry:
    """Configure the llm-rotate singleton from env. Returns the resolved Registry."""
    env = env if env is not None else dict(os.environ)
    reg = build_registry(env, default_provider, default_model)
    if not reg.use_keys:
        return reg  # nothing to configure; callers should surface a clear error

    for synth, secret in reg.env_to_set.items():
        os.environ[synth] = secret

    import llm_rotate as L

    kwargs = dict(
        registry={"providers": reg.providers, "keys": reg.keys},
        use_keys=reg.use_keys,
        fallback_chains=reg.fallback_chains or None,
    )
    try:
        L.configure(**kwargs)
    except L.ConfigurationError:
        # The llm-rotate singleton is already configured (prod configures once at
        # startup; repeated app starts in tests hit this). Keep the live config.
        pass
    return reg


async def chat(messages: list[dict], *, model: str, provider: str | None = None,
               temperature: float = 0.2, max_tokens: int = 1024) -> dict:
    """Call the configured LLM and normalise the response to a plain dict."""
    import llm_rotate as L

    resp = await L.lm.chat(
        model, messages, provider=provider, temperature=temperature, max_tokens=max_tokens
    )
    return {
        "content": resp.content,
        "model": resp.model,
        "provider": resp.provider,
        "finish_reason": resp.finish_reason,
        "usage": resp.usage.model_dump() if resp.usage else None,
    }
