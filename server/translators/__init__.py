from .base import Translator, TranslationError


def create_translator(provider: str, **kwargs) -> Translator:
    """Factory function to create translator by provider name."""
    if provider == "deepl":
        from .deepl import DeepLTranslator
        return DeepLTranslator(**kwargs)
    elif provider == "google":
        from .google import GoogleTranslator
        return GoogleTranslator(**kwargs)
    elif provider == "local":
        from .local import LocalTranslator
        return LocalTranslator(**kwargs)
    elif provider == "none" or provider is None:
        return None
    else:
        raise ValueError(f"Unknown translation provider: {provider}")


__all__ = ["Translator", "TranslationError", "create_translator"]
