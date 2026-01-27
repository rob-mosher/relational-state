"""
Provider registry for Relational Domain.

The registry manages available providers and implements fallback logic.
Local-first with transparent fallback + metadata about provider usage.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass

from .base import Provider, ProviderCapability, ProviderInvocationResult
from .local import LocalProvider
from .openai import OpenAIProvider


@dataclass
class ProviderPreference:
    """
    Preferences for provider selection.
    
    Supports entity affinity: if an entity like 'codex-gpt-5' authored a memory,
    prefer OpenAI provider for operations on it.
    """
    default_order: List[str]  # e.g., ["local", "openai"]
    entity_affinity: Optional[Dict[str, str]] = None  # e.g., {"claude-sonnet-4.5": "local"}
    
    def __post_init__(self):
        if self.entity_affinity is None:
            self.entity_affinity = {}


class ProviderRegistry:
    """
    Registry of available providers with local-first fallback logic.
    
    Manages provider discovery, selection, and transparent fallback.
    """
    
    def __init__(
        self,
        local_model: str = "all-MiniLM-L6-v2",
        openai_model: str = "text-embedding-3-small",
        openai_api_key: Optional[str] = None
    ):
        # Initialize providers
        self._providers: Dict[str, Provider] = {}
        
        # Always register local provider (sovereignty-first)
        local_provider = LocalProvider(model_name=local_model)
        self._providers["local"] = local_provider
        
        # Register OpenAI provider if available
        if openai_api_key or OpenAIProvider().is_available():
            openai_provider = OpenAIProvider(
                model_name=openai_model,
                api_key=openai_api_key
            )
            self._providers["openai"] = openai_provider
        
        # Default preference: local-first with OpenAI fallback
        self.preferences = ProviderPreference(
            default_order=["local", "openai"],
            entity_affinity={
                # Entity affinity can be configured here or learned over time
                # e.g., "codex-gpt-5" might prefer "openai" if it's a GPT model
            }
        )
    
    def list_providers(self) -> List[Provider]:
        """Return all registered providers."""
        return list(self._providers.values())
    
    def list_available_providers(self) -> List[Provider]:
        """Return only providers that are currently available."""
        return [p for p in self._providers.values() if p.is_available()]
    
    def get_provider(self, name: str) -> Optional[Provider]:
        """Get provider by name (e.g., 'local', 'openai')."""
        return self._providers.get(name)
    
    def select_provider(
        self,
        capability: ProviderCapability,
        entity: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> Optional[Provider]:
        """
        Select a provider based on capability, entity affinity, and preferences.
        
        Selection logic:
        1. If preferred_provider specified and available, use it
        2. If entity has affinity and that provider is available, use it
        3. Fall back to default_order, choosing first available
        
        Args:
            capability: Required capability (e.g., EMBED)
            entity: Entity requesting the operation (for affinity)
            preferred_provider: Explicit provider preference
            
        Returns:
            Selected provider, or None if no provider available
        """
        # Check explicit preference first
        if preferred_provider:
            provider = self.get_provider(preferred_provider)
            if provider and provider.is_available():
                descriptor = provider.get_descriptor()
                if capability in descriptor.capabilities:
                    return provider
        
        # Check entity affinity
        if entity and entity in self.preferences.entity_affinity:
            affinity_provider_name = self.preferences.entity_affinity[entity]
            provider = self.get_provider(affinity_provider_name)
            if provider and provider.is_available():
                descriptor = provider.get_descriptor()
                if capability in descriptor.capabilities:
                    return provider
        
        # Fall back to default order
        for provider_name in self.preferences.default_order:
            provider = self.get_provider(provider_name)
            if provider and provider.is_available():
                descriptor = provider.get_descriptor()
                if capability in descriptor.capabilities:
                    return provider
        
        return None
    
    def invoke_with_fallback(
        self,
        capability: ProviderCapability,
        operation: str,  # "embed_text" or "embed_batch"
        entity: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> ProviderInvocationResult:
        """
        Invoke a provider operation with automatic fallback.
        
        Tries preferred provider first, then falls back through default_order.
        Returns metadata about which provider was used and whether fallback occurred.
        
        Args:
            capability: Required capability
            operation: Method name to invoke on provider
            entity: Entity requesting the operation
            preferred_provider: Explicit provider preference
            **kwargs: Arguments to pass to the provider method
            
        Returns:
            ProviderInvocationResult with success/failure and provider metadata
        """
        primary_provider = self.select_provider(capability, entity, preferred_provider)
        
        if not primary_provider:
            return ProviderInvocationResult(
                success=False,
                provider_used="none",
                result=None,
                error_message=f"No provider available for capability: {capability.value}"
            )
        
        # Try primary provider
        method = getattr(primary_provider, operation)
        result = method(**kwargs)
        
        if result.success:
            return result
        
        # Primary failed, try fallback
        fallback_occurred = False
        for provider_name in self.preferences.default_order:
            if provider_name == preferred_provider:
                continue  # Already tried
            
            provider = self.get_provider(provider_name)
            if not provider or not provider.is_available():
                continue
            
            descriptor = provider.get_descriptor()
            if capability not in descriptor.capabilities:
                continue
            
            # Try fallback provider
            method = getattr(provider, operation)
            fallback_result = method(**kwargs)
            
            if fallback_result.success:
                # Mark that fallback occurred
                fallback_result.fallback_occurred = True
                fallback_result.metadata["fallback_from"] = result.provider_used
                return fallback_result
        
        # All providers failed
        return ProviderInvocationResult(
            success=False,
            provider_used="none",
            result=None,
            error_message=f"All providers failed for capability: {capability.value}. Last error: {result.error_message}"
        )
    
    def set_entity_affinity(self, entity: str, provider_name: str):
        """
        Set provider affinity for an entity.
        
        Example: set_entity_affinity("claude-sonnet-4.5", "local")
                 set_entity_affinity("codex-gpt-5", "openai")
        """
        self.preferences.entity_affinity[entity] = provider_name
    
    def get_statistics(self) -> Dict:
        """Return statistics about registered providers and their availability."""
        stats = {
            "total_providers": len(self._providers),
            "available_providers": len(self.list_available_providers()),
            "providers": {}
        }
        
        for name, provider in self._providers.items():
            descriptor = provider.get_descriptor()
            stats["providers"][name] = {
                "type": descriptor.provider_type.value,
                "available": provider.is_available(),
                "capabilities": [c.value for c in descriptor.capabilities],
                "requires_credentials": descriptor.requires_credentials,
                "embedding_dimensions": descriptor.embedding_dimensions
            }
        
        return stats
