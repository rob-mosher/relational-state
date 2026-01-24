"""
Provider abstraction layer for Relational Domain.

Providers are sovereign compute capabilities that the domain can negotiate with.
"""

from .base import (
    Provider,
    ProviderDescriptor,
    ProviderType,
    ProviderCapability,
    ProviderInvocationResult
)
from .local import LocalProvider
from .openai import OpenAIProvider
from .registry import ProviderRegistry, ProviderPreference

__all__ = [
    "Provider",
    "ProviderDescriptor",
    "ProviderType",
    "ProviderCapability",
    "ProviderInvocationResult",
    "LocalProvider",
    "OpenAIProvider",
    "ProviderRegistry",
    "ProviderPreference",
]
