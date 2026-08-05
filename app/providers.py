"""Provider profile registration.

`ProviderProfile.init_kwargs` supplies provider-level defaults. The model name
must come from the model string itself, never from init_kwargs, or
`init_chat_model` raises a duplicate-argument error.
"""

from __future__ import annotations

from deepagents import ProviderProfile, register_provider_profile

from app import config


def register_provider_profiles() -> None:
    """Idempotent: safe to call on every agent build."""
    register_provider_profile("anthropic", ProviderProfile())
    register_provider_profile(
        "ollama",
        ProviderProfile(init_kwargs={"base_url": config.ollama_base_url()}),
    )
