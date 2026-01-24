"""
OpenAI provider for external compute.

This provider makes API calls to OpenAI for embeddings.
Use when local compute is insufficient or when entity affinity suggests it.
"""

import os
from typing import Optional, List

from .base import (
    Provider,
    ProviderDescriptor,
    ProviderType,
    ProviderCapability,
    ProviderInvocationResult
)


class OpenAIProvider(Provider):
    """
    OpenAI embedding provider.
    
    External compute: makes API calls to OpenAI.
    Requires API key. Used as fallback or when entity affinity suggests it.
    """
    
    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        dimensions: int = 1536
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.dimensions = dimensions
        self._client = None
    
    def _ensure_client(self):
        """Lazy-load OpenAI client on first use."""
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI provider requires 'openai' package. "
                    "Install with: pip install openai"
                )
    
    def get_descriptor(self) -> ProviderDescriptor:
        """Return metadata about this provider."""
        return ProviderDescriptor(
            name=f"openai/{self.model_name}",
            provider_type=ProviderType.OPENAI,
            version=None,  # OpenAI doesn't version models explicitly
            capabilities=[ProviderCapability.EMBED],
            requires_credentials=True,
            embedding_dimensions=self.dimensions
        )
    
    def is_available(self) -> bool:
        """Check if OpenAI provider is available (has API key)."""
        if not self.api_key:
            return False
        try:
            self._ensure_client()
            return self._client is not None
        except Exception:
            return False
    
    def embed_text(self, text: str, entity: Optional[str] = None) -> ProviderInvocationResult:
        """
        Generate embedding using OpenAI API.
        
        Args:
            text: Text to embed
            entity: Entity requesting the embedding (tracked for affinity)
            
        Returns:
            ProviderInvocationResult with embedding vector
        """
        if not self.is_available():
            return ProviderInvocationResult(
                success=False,
                provider_used=self.get_descriptor().name,
                result=None,
                error_message="OpenAI provider not available (missing API key or client init failed)"
            )
        
        try:
            self._ensure_client()
            
            # Call OpenAI embeddings API
            response = self._client.embeddings.create(
                model=self.model_name,
                input=[text]
            )
            
            embedding = response.data[0].embedding
            
            return ProviderInvocationResult(
                success=True,
                provider_used=self.get_descriptor().name,
                result=embedding,
                metadata={
                    "model": self.model_name,
                    "dimensions": len(embedding),
                    "entity": entity,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            )
        except Exception as e:
            return ProviderInvocationResult(
                success=False,
                provider_used=self.get_descriptor().name,
                result=None,
                error_message=f"OpenAI API error: {str(e)}"
            )
    
    def embed_batch(self, texts: List[str], entity: Optional[str] = None) -> ProviderInvocationResult:
        """
        Generate embeddings for multiple texts using OpenAI batch API.
        
        OpenAI supports batching up to 2048 inputs per request.
        """
        if not self.is_available():
            return ProviderInvocationResult(
                success=False,
                provider_used=self.get_descriptor().name,
                result=None,
                error_message="OpenAI provider not available (missing API key or client init failed)"
            )
        
        try:
            self._ensure_client()
            
            # Call OpenAI embeddings API with batch
            response = self._client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            
            return ProviderInvocationResult(
                success=True,
                provider_used=self.get_descriptor().name,
                result=embeddings,
                metadata={
                    "model": self.model_name,
                    "batch_size": len(texts),
                    "dimensions": len(embeddings[0]) if embeddings else 0,
                    "entity": entity,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            )
        except Exception as e:
            return ProviderInvocationResult(
                success=False,
                provider_used=self.get_descriptor().name,
                result=None,
                error_message=f"OpenAI API error: {str(e)}"
            )
