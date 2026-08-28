"""
core/mission.py

Mission, Action, Decision, and Run data structures.

These are the structured records that flow through the entire Phase 2 system.
Everything important lives here as plain dataclasses so logs/reports can be
regenerated from the run record alone.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

from core.confidence import Confidence
from core.evidence import EvidenceRecord
from core.observation import Observation


# ── Enums ──────────────────────────────────────────────────────────────────────

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"      # policy block before execution


class ActionRisk(str, Enum):
    PASSIVE = "passive"
    SAFE_ACTIVE = "safe_active"
    SENSITIVE_ACTIVE = "sensitive_active"
    RESTRICTED = "restricted"


class PolicyDecisionKind(str, Enum):
    ALLOW = "allow"
    REJECT = "reject"


# ── Risk severity ordering (single source of truth) ───────────────────────────
# Hoisted here from policy/policy.py so AuthorizationScope and the policy rules
# share one ordering. Higher int = more sensitive.

_RISK_SEVERITY: dict[ActionRisk, int] = {
    ActionRisk.PASSIVE:           0,
    ActionRisk.SAFE_ACTIVE:       1,
    ActionRisk.SENSITIVE_ACTIVE:  2,
    ActionRisk.RESTRICTED:        3,
}


# ── Authorization ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuthorizationScope:
    """Explicit authorization for a run — separate from Scenario, Capability,
    Provider, and User objective. Carries the set of risk tiers this run is
    cleared to exercise plus optional human-readable context. PASSIVE is
    always implicitly permitted (AGENTS.md Core Design Rule #4: passive is
    the default). Every non-PASSIVE tier must be listed explicitly.

    The model is intentionally tiny: no authentication, no user management,
    no per-target ACL. It answers one question: 'what risk classes is this
    run cleared to perform?' Secrets never live here.

    Three constructors cover the cases the codebase needs:
      - default()                 -> PASSIVE only (preserves Phase 2 default)
      - with_cumulative_tier(t)   -> all tiers at or below t (CLI --allow-risk)
      - with_tiers(*tiers)        -> explicit disjoint grant + PASSIVE (tests)
    """

    allowed_risks: frozenset[ActionRisk] = field(
        default_factory=lambda: frozenset({ActionRisk.PASSIVE})
    )
    notes: str = ""

    @classmethod
    def default(cls) -> "AuthorizationScope":
        """PASSIVE only — the conservative default. Equivalent to the
        historical Phase 2 'default' scope."""
        return cls()

    @classmethod
    def with_cumulative_tier(cls, max_tier: ActionRisk,
                             notes: str = "") -> "AuthorizationScope":
        """Allowed set = all tiers at or below `max_tier` severity-wise.
        This is what the CLI --allow-risk flag builds: selecting a tier
        implicitly grants every lower tier too."""
        max_sev = _RISK_SEVERITY[max_tier]
        allowed = frozenset(
            r for r, sev in _RISK_SEVERITY.items() if sev <= max_sev
        )
        return cls(allowed_risks=allowed, notes=notes)

    @classmethod
    def with_tiers(cls, *tiers: ActionRisk,
                   notes: str = "") -> "AuthorizationScope":
        """Explicit disjoint grant: only the listed tiers plus PASSIVE.
        Used when callers want a non-cumulative exact-set authorization
        (tests, future Lab Mode). PASSIVE is always included."""
        return cls(
            allowed_risks=frozenset(tiers) | {ActionRisk.PASSIVE},
            notes=notes,
        )

    @property
    def enabled(self) -> bool:
        """True if any tier above PASSIVE is authorized."""
        return any(r != ActionRisk.PASSIVE for r in self.allowed_risks)

    def allows(self, risk: ActionRisk) -> bool:
        return risk in self.allowed_risks

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_risks": sorted(r.value for r in self.allowed_risks),
            "notes": self.notes,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "AuthorizationScope":
        risks = frozenset(
            ActionRisk(r) for r in d.get("allowed_risks", [ActionRisk.PASSIVE.value])
        )
        return AuthorizationScope(allowed_risks=risks, notes=d.get("notes", ""))


# ── Action & Decision ──────────────────────────────────────────────────────────

@dataclass
class ActionRequest:
    """A request from the orchestrator to execute a capability action."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability: str = ""          # e.g. "wifi.discovery"
    action: str = ""              # e.g. "discover"
    args: dict[str, Any] = field(default_factory=dict)
    risk: ActionRisk = ActionRisk.PASSIVE
    requested_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk"] = self.risk.value
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ActionRequest":
        d = dict(d)
        risk = d.pop("risk", None)
        req = ActionRequest(**d)
        if risk is not None:
            req.risk = ActionRisk(risk)
        return req


@dataclass
class PolicyDecision:
    """Result of policy validation against an ActionRequest."""
    kind: PolicyDecisionKind
    reasons: list[str] = field(default_factory=list)
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "reasons": self.reasons, "decided_at": self.decided_at}

    @property
    def allowed(self) -> bool:
        return self.kind == PolicyDecisionKind.ALLOW


@dataclass
class CapabilityDecision:
    """Result of capability resolution — which provider handles it."""
    capability: str
    action: str
    provider: str
    supported: bool = True
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionRecord:
    """A fully resolved action — request, decision, outcome."""
    request: ActionRequest
    capability_decision: Optional[CapabilityDecision] = None
    policy_decision: Optional[PolicyDecision] = None
    # Authoritative risk resolved from the capability catalogue at executor
    # time (cap.risk). Authorization decisions consult this, not
    # request.risk. Persisted so reports can show it without a live registry.
    authoritative_risk: Optional[ActionRisk] = None
    observation: Optional[Observation] = None
    # Phase 2.7.5 — durable evidence captured by this action. Mirrored from
    # observation.evidence by the engine so the action carries the
    # provenance even after the Observation is detached. Empty for
    # passive / rejected / failed actions.
    evidence: list[EvidenceRecord] = field(default_factory=list)
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "capability_decision": self.capability_decision.to_dict() if self.capability_decision else None,
            "policy_decision": self.policy_decision.to_dict() if self.policy_decision else None,
            "authoritative_risk": self.authoritative_risk.value if self.authoritative_risk else None,
            "observation": self.observation.to_dict() if self.observation else None,
            "evidence": [e.to_dict() for e in self.evidence],
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ── Run ────────────────────────────────────────────────────────────────────────

@dataclass
class Run:
    """A complete Suryafool run — the canonical record used for logs/reports."""
    id: str = field(default_factory=lambda: f"run-{int(time.time())}-{uuid.uuid4().hex[:8]}")
    objective: str = ""
    scenario: str = ""                                # scenario name (sim) or "" (real)
    backend: str = "simulator"                        # "simulator" | future backends
    seed: Optional[int] = None                        # RNG seed for reproducibility
    authorization: AuthorizationScope = field(default_factory=AuthorizationScope.default)
    status: RunStatus = RunStatus.PENDING
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    actions: list[ActionRecord] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    capabilities_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    # Phase 2.7.5 — aggregate evidence collected by the run. Mirrored from
    # each action's observation.evidence by the engine. Distinct from
    # findings (raw entity observations) and errors (rejected/failed
    # actions). Empty for PASSIVE-only runs and rejected capture plans.
    evidence: list[EvidenceRecord] = field(default_factory=list)
    final_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "scenario": self.scenario,
            "backend": self.backend,
            "seed": self.seed,
            "authorization": self.authorization.to_dict(),
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "actions": [a.to_dict() for a in self.actions],
            "observations": [o.to_dict() for o in self.observations],
            "capabilities_used": self.capabilities_used,
            "errors": self.errors,
            "findings": self.findings,
            "evidence": [e.to_dict() for e in self.evidence],
            "final_summary": self.final_summary,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Run":
        d = dict(d)
        d["status"] = RunStatus(d["status"])
        # authorization: back-compat — old run.json files have no key.
        if "authorization" in d:
            d["authorization"] = AuthorizationScope.from_dict(d["authorization"])
        else:
            d["authorization"] = AuthorizationScope.default()
        d["actions"] = [
            ActionRecord(
                request=ActionRequest.from_dict(a["request"]),
                capability_decision=CapabilityDecision(**a["capability_decision"]) if a.get("capability_decision") else None,
                policy_decision=PolicyDecision(
                    kind=PolicyDecisionKind(a["policy_decision"]["kind"]),
                    reasons=a["policy_decision"].get("reasons", []),
                    decided_at=a["policy_decision"].get("decided_at", 0.0),
                ) if a.get("policy_decision") else None,
                authoritative_risk=ActionRisk(a["authoritative_risk"])
                    if a.get("authoritative_risk") else None,
                observation=Observation.from_dict(a["observation"]) if a.get("observation") else None,
                evidence=[EvidenceRecord.from_dict(e) for e in a.get("evidence", [])],
                error=a.get("error"),
                started_at=a.get("started_at", 0.0),
                completed_at=a.get("completed_at"),
            )
            for a in d.get("actions", [])
        ]
        d["observations"] = [Observation.from_dict(o) for o in d.get("observations", [])]
        d["evidence"] = [EvidenceRecord.from_dict(e) for e in d.get("evidence", [])]
        return Run(**d)

    def duration(self) -> float:
        if self.completed_at is None:
            return time.time() - self.started_at
        return self.completed_at - self.started_at
