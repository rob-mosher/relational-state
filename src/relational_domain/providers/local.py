"""
Local provider using sentence-transformers.

This provider runs entirely on the local machine with no external dependencies.
It's the default, sovereignty-preserving option.
"""

from typing import Optional, List
from sentence_transformers import SentenceTransformer

from .base import (
    Provider,
    ProviderDescriptor,
    ProviderType,
    ProviderCapability,
    ProviderInvocationResult
)


class LocalProvider(Provider):
    """
    Local embedding provider using sentence-transformers.
    
    Sovereignty-first: runs entirely on local hardware, no external calls.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimensions = None
    
    def _ensure_model_loaded(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
            # Get embedding dimensions by encoding a test string
            test_embedding = self._model.encode(["test"], convert_to_numpy=True)[0]
            self._dimensions = len(test_embedding)
    
    def get_descriptor(self) -> ProviderDescriptor:
        """Return metadata about this provider."""
        if self._dimensions is None:
            self._ensure_model_loaded()
        
        return ProviderDescriptor(
            name=f"local/{self.model_name}",
            provider_type=ProviderType.LOCAL,
            version=None,  # sentence-transformers doesn't expose model version easily
            capabilities=[ProviderCapability.EMBED],
            requires_credentials=False,
            embedding_dimensions=self._dimensions
        )
    
    def is_available(self) -> bool:
        """Local provider is always available (no credentials needed)."""
        try:
            self._ensure_model_loaded()
            return True
        except Exception:
            return False
    
    def embed_text(self, text: str, entity: Optional[str] = None) -> ProviderInvocationResult:
        """
        Generate embedding using local sentence-transformers model.
        
        Args:
            text: Text to embed
            entity: Entity requesting the embedding (tracked for affinity, not used locally)
            
        Returns:
            ProviderInvocationResult with embedding vector
        """
        try:
            self._ensure_model_loaded()
            
            # Encode single text
            embedding = self._model.encode([text], convert_to_numpy=True)[0]
            
            return ProviderInvocationResult(
                success=True,
                provider_used=self.get_descriptor().name,
                result=embedding.tolist(),
                metadata={
                    "model": self.model_name,
                    "dimensions": len(embedding),
                    "entity": entity
                }
            )
        except Exception as e:
            return ProviderInvocationResult(
                success=False,
                provider_used=self.get_descriptor().name,
                result=None,
                error_message=str(e)
            )
    
    def embed_batch(self, texts: List[str], entity: Optional[str] = None) -> ProviderInvocationResult:
        """
        Generate embeddings for multiple texts using true batch processing.
        
        sentence-transformers is optimized for batch encoding.
        """
        try:
            self._ensure_model_loaded()
            
            # Batch encode
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            
            return ProviderInvocationResult(
                success=True,
                provider_used=self.get_descriptor().name,
                result=[emb.tolist() for emb in embeddings],
                metadata={
                    "model": self.model_name,
                    "batch_size": len(texts),
                    "dimensions": len(embeddings[0]) if len(embeddings) > 0 else 0,
                    "entity": entity
                }
            )
        except Exception as e:
            return ProviderInvocationResult(
                success=False,
                provider_used=self.get_descriptor().name,
                result=None,
                error_message=str(e)
            )
