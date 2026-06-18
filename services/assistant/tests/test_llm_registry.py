"""Tests for the dynamic env -> llm-rotate registry builder (no network)."""

from __future__ import annotations

from bobai_assistant.llm import build_registry


def test_single_key_uses_direct_env_ref():
    reg = build_registry({"OPENROUTER_API_KEY": "or-key"}, "openrouter", "openai/gpt-4o-mini")
    assert reg.configured == ["openrouter"]
    assert len(reg.keys) == 1
    assert reg.keys[0]["secret_ref"] == "env://OPENROUTER_API_KEY"
    assert reg.env_to_set == {}


def test_multiple_keys_become_rotatable_credentials():
    reg = build_registry({"OPENAI_API_KEY": "k1, k2 , k3"}, "openai", "gpt-4o-mini")
    openai_keys = [k for k in reg.keys if k["provider"] == "openai"]
    assert len(openai_keys) == 3
    # Multi-key uses synthetic env refs that configure_llm will set.
    assert len(reg.env_to_set) == 3
    assert all(k["secret_ref"].startswith("env://LLMROTATE_OPENAI_") for k in openai_keys)


def test_custom_openai_compatible_provider_gets_base_url():
    reg = build_registry({"GROQ_API_KEY": "g1"}, "groq", "llama-3.3-70b-versatile")
    assert "groq" in reg.providers
    assert reg.providers["groq"]["base_url"] == "https://api.groq.com/openai/v1"
    assert reg.providers["groq"]["adapter"] == "openai"
    # Built-in providers are NOT redefined.
    reg2 = build_registry({"OPENAI_API_KEY": "k1"}, "openai", "gpt-4o-mini")
    assert reg2.providers == {}


def test_fallback_chain_built_across_providers():
    reg = build_registry(
        {"OPENAI_API_KEY": "k1", "GROQ_API_KEY": "g1"}, "openai", "gpt-4o-mini"
    )
    assert "gpt-4o-mini" in reg.fallback_chains
    fb_providers = {f["provider"] for f in reg.fallback_chains["gpt-4o-mini"]}
    assert fb_providers == {"groq"}  # every configured provider except the default


def test_no_keys_means_empty_registry():
    reg = build_registry({}, "openai", "gpt-4o-mini")
    assert reg.use_keys == []
    assert reg.configured == []
