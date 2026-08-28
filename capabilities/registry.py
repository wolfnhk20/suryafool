"""
capabilities/registry.py

Capability registry — the central source of truth for
"What capabilities are available?  What backend provides them?
What actions does each capability support?"

This is what every other component (orchestrator, policy, run engine,
CLI) queries to resolve capability lookups. No hardcoded lists elsewhere.
"""

from __future__ import annotations

from typing import Any, Optional

from capabilities.base import (
    Capability,
    CapabilityProvider,
    DEFAULT_CAPABILITIES,
    SimulatorProvider,
)
from core.mission import CapabilityDecision


class CapabilityRegistry:
    """Registry of capabilities + ordered list of providers."""

    def __init__(self,
                 capabilities: Optional[list[Capability]] = None,
                 providers: Optional[list[CapabilityProvider]] = None):
        self._capabilities: list[Capability] = list(capabilities or DEFAULT_CAPABILITIES)
        self._providers: list[CapabilityProvider] = list(providers or [])
        self._by_key: dict[str, Capability] = {c.key: c for c in self._capabilities}

    # ── Registration ──────────────────────────────────────────────────────────
    def add_capability(self, capability: Capability) -> None:
        self._capabilities.append(capability)
        self._by_key[capability.key] = capability

    def add_provider(self, provider: CapabilityProvider) -> None:
        self._providers.append(provider)

    # ── Queries ───────────────────────────────────────────────────────────────
    def capabilities(self) -> list[Capability]:
        return list(self._capabilities)

    def capability(self, capability: str, action: str) -> Optional[Capability]:
        return self._by_key.get(f"{capability}.{action}")

    def providers(self) -> list[CapabilityProvider]:
        return list(self._providers)

    def provider_names(self) -> list[str]:
        return [p.name for p in self._providers]

    # ── Resolution ────────────────────────────────────────────────────────────
    def resolve(self, capability: str, action: str) -> CapabilityDecision:
        """Find a provider that supports (capability, action)."""
        cap = self.capability(capability, action)
        if cap is None:
            return CapabilityDecision(
                capability=capability, action=action,
                provider="", supported=False,
                reason=f"Unknown capability: {capability}.{action}",
            )
        for provider in self._providers:
            if provider.supports(capability, action):
                return CapabilityDecision(
                    capability=capability, action=action,
                    provider=provider.name, supported=True,
                )
        return CapabilityDecision(
            capability=capability, action=action,
            provider="", supported=False,
            reason="No registered provider supports this capability.",
        )


# ── Default factory ───────────────────────────────────────────────────────────

def default_registry(environment=None) -> CapabilityRegistry:
    """Return a registry pre-loaded with default capabilities and the
    simulator provider.

    Phase 2.7.4 removed the Phase 2.5 Marauder provider from the runtime —
    Suryafool now owns its capability model. A future real-hardware backend
    plugs in by subclassing `CapabilityProvider` (see capabilities/base.py)
    and registering itself via `registry.add_provider(...)`; no factory
    change is required.
    """
    sim = SimulatorProvider(environment) if environment is not None else SimulatorProvider(_null_env())
    return CapabilityRegistry(providers=[sim])


def available_providers() -> list[str]:
    """Names of providers the registry factory knows how to construct."""
    return ["simulator"]


def _null_env():
    from simulator.environment import Environment
    return Environment(name="(empty)")
