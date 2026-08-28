"""
policy/policy.py

Deterministic policy gate between the orchestrator and the executor.

Every ActionRequest must pass through `PolicyEngine.validate()`. The engine:

  - checks that the capability is registered
  - checks that the action is supported
  - enforces risk-tier rules (e.g. restricted actions need explicit scope)

It returns a PolicyDecision with structured reasons. The engine is *not*
advisory — it is the gate. Code paths in the engine that execute an action
must call validate() first; if the decision is REJECT, the action must
not run.

Easy to extend: add a new Rule subclass and register it on the engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from capabilities.registry import CapabilityRegistry
from core.mission import (
    ActionRequest,
    AuthorizationScope,
    PolicyDecision,
    PolicyDecisionKind,
    RunStatus,
    _RISK_SEVERITY,
)


# ── Rules ──────────────────────────────────────────────────────────────────────

class Rule(ABC):
    """A single validation rule. Returns a list of reasons (empty = pass)."""

    @abstractmethod
    def check(self, request: ActionRequest, ctx: "PolicyContext") -> list[str]:
        ...


@dataclass
class PolicyContext:
    """Context passed to every rule — keeps rules stateless."""
    registry: CapabilityRegistry
    run_status: RunStatus
    # Explicit authorization for the run — separate from Scenario. Selecting
    # a scenario no longer grants any risk tier; the scope must be supplied
    # explicitly (via the CLI --allow-risk flag or programmatically).
    authorization: AuthorizationScope = field(default_factory=AuthorizationScope.default)
    extra: dict[str, Any] | None = None


class CapabilityExistsRule(Rule):
    def check(self, request: ActionRequest, ctx: PolicyContext) -> list[str]:
        if ctx.registry.capability(request.capability, request.action) is None:
            return [f"Unknown capability: {request.capability}.{request.action}"]
        return []


class ProviderSupportsRule(Rule):
    def check(self, request: ActionRequest, ctx: PolicyContext) -> list[str]:
        # Skip if the capability doesn't exist at all — CapabilityExistsRule
        # already produced a clearer reason.
        if ctx.registry.capability(request.capability, request.action) is None:
            return []
        decision = ctx.registry.resolve(request.capability, request.action)
        if not decision.supported:
            return [decision.reason or "No provider supports this capability."]
        return []


class RiskDeclarationRule(Rule):
    """The catalogue's cap.risk is authoritative. Any divergence between
    request.risk and cap.risk — whether downgrade OR upgrade — is rejected.
    ActionRequest.risk is never trusted for authorization decisions; it is
    caller self-disclosure that must match the catalogue, otherwise the
    caller is buggy or lying. A mismatch is rejected informatively rather
    than silently ignored, so callers see the bug at the gate instead of
    debugging an ALLOW/REJECT surprise."""

    def check(self, request: ActionRequest, ctx: PolicyContext) -> list[str]:
        cap = ctx.registry.capability(request.capability, request.action)
        if cap is None:
            return []
        if request.risk == cap.risk:
            return []
        if _RISK_SEVERITY[request.risk] < _RISK_SEVERITY[cap.risk]:
            direction, verb = "downgrade", "claims"
        else:
            direction, verb = "upgrade", "upgrades to"
        return [
            f"Risk {direction} rejected: {request.capability}.{request.action} "
            f"is declared {cap.risk.value.upper()} in the catalogue; request "
            f"{verb} {request.risk.value.upper()}. ActionRequest.risk is not "
            f"trusted for authorization — fix the caller, not the catalogue."
        ]


class RiskTierAuthorizedRule(Rule):
    """An action's AUTHORITATIVE risk tier (cap.risk) must be permitted by the
    run's AuthorizationScope. PASSIVE is always allowed; any tier above
    PASSIVE must be listed explicitly in the scope. Uses cap.risk only —
    never request.risk — so a caller cannot upgrade past the scope by lying.

    Replaces the old RestrictedRequiresScopeRule + SensitiveActiveScopeRule
    pair, both of which branched on request.risk (caller-declared) rather
    than cap.risk (authoritative). Those rules also relied on the engine's
    now-removed scenario->scope coupling for authorization."""

    def check(self, request: ActionRequest, ctx: PolicyContext) -> list[str]:
        cap = ctx.registry.capability(request.capability, request.action)
        if cap is None:
            return []
        if ctx.authorization.allows(cap.risk):
            return []
        granted = sorted(r.value for r in ctx.authorization.allowed_risks)
        granted_str = ",".join(granted) if granted else "(none)"
        return [
            f"Action {request.capability}.{request.action} requires risk tier "
            f"{cap.risk.value.upper()} but the run's AuthorizationScope only "
            f"permits: {granted_str}. Use --allow-risk to grant a higher "
            f"tier explicitly for this run."
        ]


class RunNotFailedRule(Rule):
    def check(self, request: ActionRequest, ctx: PolicyContext) -> list[str]:
        if ctx.run_status == RunStatus.FAILED:
            return ["Run has already failed — further actions are rejected."]
        return []


# ── Engine ─────────────────────────────────────────────────────────────────────

class PolicyEngine:
    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry
        self._rules: list[Rule] = [
            CapabilityExistsRule(),
            ProviderSupportsRule(),
            RiskDeclarationRule(),
            RiskTierAuthorizedRule(),
            RunNotFailedRule(),
        ]

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def validate(self, request: ActionRequest, ctx: PolicyContext) -> PolicyDecision:
        reasons: list[str] = []
        for rule in self._rules:
            reasons.extend(rule.check(request, ctx))
        if reasons:
            return PolicyDecision(kind=PolicyDecisionKind.REJECT, reasons=reasons)
        return PolicyDecision(kind=PolicyDecisionKind.ALLOW)
