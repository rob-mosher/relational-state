"""
Provider abstraction layer for Relational Domain.

Providers are sovereign compute capabilities that the domain can negotiate with.
The domain declares what it needs; providers declare what they can do.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List


class ProviderType(Enum):
    """Types of compute providers the domain can work with."""
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ProviderCapability(Enum):
    """Operations that a provider can perform."""
    EMBED = "embed"
    SUMMARIZE = "summarize"
    COMPILE_CONTEXT = "compile_context"
    PROMOTE = "promote"


@dataclass
class ProviderDescriptor:
    """Metadata describing a provider's identity and capabilities."""
    name: str
    provider_type: ProviderType
    version: Optional[str] = None
    capabilities: List[ProviderCapability] = None
    requires_credentials: bool = False
    embedding_dimensions: Optional[int] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class ProviderInvocationResult:
    """Result from invoking a provider, with metadata about what happened."""
    success: bool
    provider_used: str  # e.g., "local/sentence-transformers", "openai/text-embedding-3-small"
    result: Any
    metadata: Dict[str, Any] = None
    fallback_occurred: bool = False
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Provider(ABC):
    """
    Abstract base class for compute providers.
    
    Providers are sovereign services that the domain can negotiate with.
    They declare their capabilities and the domain decides whether to use them.
    """
    
    @abstractmethod
    def get_descriptor(self) -> ProviderDescriptor:
        """Return metadata about this provider's capabilities."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is currently available (credentials, network, etc.)."""
        pass
    
    @abstractmethod
    def embed_text(self, text: str, entity: Optional[str] = None) -> ProviderInvocationResult:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            entity: Entity requesting the embedding (for affinity tracking)
            
        Returns:
            ProviderInvocationResult with embedding vector
        """
        pass
    
    def embed_batch(self, texts: List[str], entity: Optional[str] = None) -> ProviderInvocationResult:
        """
        Generate embeddings for multiple texts (batched for efficiency).
        
        Default implementation calls embed_text for each text.
        Providers can override for true batch processing.
        """
        embeddings = []
        for text in texts:
            result = self.embed_text(text, entity=entity)
            if not result.success:
                return result  # Fail fast on first error
            embeddings.append(result.result)
        
        return ProviderInvocationResult(
            success=True,
            provider_used=self.get_descriptor().name,
            result=embeddings,
            metadata={"batch_size": len(texts)}
        )
