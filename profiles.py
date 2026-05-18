from deepagents import ProviderProfile, register_provider_profile

register_provider_profile("anthropic", ProviderProfile())

register_provider_profile(
    "ollama",
    ProviderProfile(init_kwargs={"base_url": "http://localhost:11434"}),
)
