"""
tests/test_phase26_authorization.py

Phase 2.6 regression suite — explicit AuthorizationScope + hardened policy.

Core invariant: Scenario != Authorization. Selecting --scenario lab grants
nothing. Risk tiers are authorized by an explicit AuthorizationScope, and
authorization decisions consult the AUTHORITATIVE catalogue risk (cap.risk),
never the caller-declared ActionRequest.risk.

Covers the spec §6.2 acceptance criteria:

  1.  scenario="lab" does NOT automatically authorize SAFE_ACTIVE
  2.  caller cannot DOWNGRADE SAFE_ACTIVE -> PASSIVE
  3.  caller cannot DOWNGRADE RESTRICTED -> PASSIVE
  4.  caller cannot UPGRADE PASSIVE -> RESTRICTED
  5.  SAFE_ACTIVE action ALLOWs with explicit --allow-risk safe_active
  6.  SENSITIVE_ACTIVE action ALLOWs with --allow-risk sensitive_active
  7.  RESTRICTED action ALLOWs with --allow-risk restricted
  8.  SENSITIVE_ACTIVE action is REJECTed under a SAFE_ACTIVE-only scope
  9.  unauthorized actions are rejected BEFORE the provider is invoked
  10. all four catalogue-PASSIVE actions ALLOW under the default scope
  11. AuthorizationScope serializes round-trip (to_dict / from_dict)
  12. Run record round-trips the authorization field
  13. old run.json (no authorization key) parses to the PASSIVE default
  14. with_tiers() is non-cumulative (disjoint grant excludes unlisted tiers)

Run without pytest:
    python -m tests.test_phase26_authorization
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    import pytest
except ImportError:
    pytest = None  # standalone runner works without pytest

from capabilities.base import Capability, CapabilityProvider
from capabilities.registry import default_registry
from core.mission import (
    ActionRecord,
    ActionRequest,
    ActionRisk,
    AuthorizationScope,
    PolicyDecisionKind,
    Run,
    RunStatus,
    _RISK_SEVERITY,
)
from core.observation import Observation
from engine.logger import RunLogger
from engine.runner import RunEngine
from policy.policy import PolicyContext, PolicyEngine
from simulator.scenarios import build_scenario


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        """Isolate run artifacts under a temp dir for every test."""
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# ── Test helpers ──────────────────────────────────────────────────────────────

def _engine_with_scope(scope: AuthorizationScope, scenario: str = "home",
                       seed: int = 42):
    """Build a simulator-backed RunEngine authorized with `scope`.

    The run is explicitly given `scope` regardless of scenario — this is the
    core Phase 2.6 invariant: scenario and authorization are decoupled.
    """
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.6 test", scenario=scenario, seed=seed,
              authorization=scope)
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger


def _default_engine(scenario: str = "home", seed: int = 42):
    """Same as _engine_with_scope but with the PASSIVE-only default scope."""
    return _engine_with_scope(AuthorizationScope.default(), scenario, seed)


class _TrackingProvider(CapabilityProvider):
    """A fake provider that records every execute() call. Used to prove that
    a REJECTED action never reaches the provider (test #9)."""

    name = "tracking"

    def __init__(self):
        self.execute_calls = []

    def supports(self, capability, action):
        return True  # claim everything; policy still rejects what scope denies

    def execute(self, capability, action, args=None):
        self.execute_calls.append((capability, action))
        return Observation(
            capability=capability, action=action,
            entities=[], raw_data={}, summary="tracking provider hit",
        )


def _registry_with_test_capability(risk: ActionRisk,
                                   provider: Optional[CapabilityProvider] = None):
    """Build a registry that has ONE extra test-only capability at `risk`,
    backed by `provider` (defaults to a tracking provider so we can also
    prove provider-not-invoked behavior). The four default capabilities
    remain, but the tracker provider is the one that supports the test cap.
    """
    from simulator.environment import Environment
    env = Environment("test")
    registry = default_registry(environment=env)
    cap = Capability(
        name="Test Capability",
        capability="test.cap", action="run",
        risk=risk, description="Phase 2.6 test-only capability",
    )
    registry.add_capability(cap)
    prov = provider or _TrackingProvider()
    registry.add_provider(prov)
    return registry


# ── Test classes ───────────────────────────────────────────────────────────────

class TestScenarioDoesNotAuthorize:
    """The single most important regression: scenario selection grants nothing."""

    def test_scenario_lab_does_not_authorize_safe_active(self):
        """With scenario='lab' and the default PASSIVE-only scope, an
        nfc.discovery.read (catalogue SAFE_ACTIVE) request is REJECTED.
        Selecting --scenario lab no longer implies lab authorization."""
        engine, run, logger = _default_engine(scenario="lab")
        try:
            record = engine.execute(
                ActionRequest(capability="nfc.discovery", action="read",
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            # The reason must mention the authoritative tier (SAFE_ACTIVE),
            # not the scenario.
            assert "SAFE_ACTIVE" in record.policy_decision.reasons[0]
            assert "AuthorizationScope" in record.policy_decision.reasons[0]
        finally:
            logger.close()


class TestCallerCannotDowngrade:
    """RiskDeclarationRule rejects any request.risk < cap.risk mismatch."""

    def test_caller_cannot_downgrade_safe_active_to_passive(self):
        """nfc.discovery.read is SAFE_ACTIVE in the catalogue. A request
        claiming risk=PASSIVE must be rejected with a downgrade reason."""
        engine, run, logger = _default_engine()
        try:
            record = engine.execute(
                ActionRequest(capability="nfc.discovery", action="read",
                              risk=ActionRisk.PASSIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            reasons = " ".join(record.policy_decision.reasons)
            assert "downgrade" in reasons.lower()
            assert "SAFE_ACTIVE" in reasons
        finally:
            logger.close()

    def test_caller_cannot_downgrade_restricted_to_passive(self):
        """Register a test-only RESTRICTED capability; a request claiming
        risk=PASSIVE is rejected by RiskDeclarationRule."""
        registry = _registry_with_test_capability(ActionRisk.RESTRICTED)
        policy = PolicyEngine(registry=registry)
        run = Run(objective="downgrade restricted test")
        logger = RunLogger(run)
        engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
        try:
            record = engine.execute(
                ActionRequest(capability="test.cap", action="run",
                              risk=ActionRisk.PASSIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            reasons = " ".join(record.policy_decision.reasons)
            assert "downgrade" in reasons.lower()
            assert "RESTRICTED" in reasons
        finally:
            logger.close()


class TestCallerCannotUpgrade:
    """RiskDeclarationRule also rejects request.risk > cap.risk."""

    def test_caller_cannot_upgrade_passive_to_restricted(self):
        """wifi.discovery.discover is catalogue PASSIVE. A request claiming
        risk=RESTRICTED is rejected with an upgrade reason — the caller cannot
        upgrade past their scope by lying, and they cannot lie about the tier
        at all."""
        engine, run, logger = _default_engine()
        try:
            record = engine.execute(
                ActionRequest(capability="wifi.discovery", action="discover",
                              risk=ActionRisk.RESTRICTED)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            reasons = " ".join(record.policy_decision.reasons)
            assert "upgrade" in reasons.lower()
            assert "PASSIVE" in reasons
            assert "RESTRICTED" in reasons
        finally:
            logger.close()


class TestExplicitAuthorizationAllows:
    """A correctly-declared request that matches the catalogue risk is ALLOWed
    when the run's AuthorizationScope includes that tier."""

    def test_safe_active_allowed_with_explicit_authorization(self):
        scope = AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)
        engine, run, logger = _engine_with_scope(scope, scenario="lab")
        try:
            record = engine.execute(
                ActionRequest(capability="nfc.discovery", action="read",
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                f"expected ALLOW, got REJECT: {record.policy_decision.reasons}"
        finally:
            logger.close()

    def test_sensitive_active_allowed_with_higher_authorization(self):
        """A test-only SENSITIVE_ACTIVE capability is ALLOWed when the run
        authorizes up to SENSITIVE_ACTIVE."""
        registry = _registry_with_test_capability(ActionRisk.SENSITIVE_ACTIVE)
        policy = PolicyEngine(registry=registry)
        scope = AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)
        run = Run(objective="sensitive active allow", authorization=scope)
        logger = RunLogger(run)
        engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
        try:
            record = engine.execute(
                ActionRequest(capability="test.cap", action="run",
                              risk=ActionRisk.SENSITIVE_ACTIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                f"expected ALLOW, got REJECT: {record.policy_decision.reasons}"
        finally:
            logger.close()

    def test_restricted_allowed_with_restricted_authorization(self):
        """A test-only RESTRICTED capability is ALLOWed when the run authorizes
        up to RESTRICTED (the maximum tier)."""
        registry = _registry_with_test_capability(ActionRisk.RESTRICTED)
        policy = PolicyEngine(registry=registry)
        scope = AuthorizationScope.with_cumulative_tier(ActionRisk.RESTRICTED)
        run = Run(objective="restricted allow", authorization=scope)
        logger = RunLogger(run)
        engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
        try:
            record = engine.execute(
                ActionRequest(capability="test.cap", action="run",
                              risk=ActionRisk.RESTRICTED)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                f"expected ALLOW, got REJECT: {record.policy_decision.reasons}"
        finally:
            logger.close()


class TestTierBoundaryEnforced:
    """A scope stops at its granted tier; higher tiers are still REJECTed."""

    def test_sensitive_active_rejected_under_safe_active_scope(self):
        """A test-only SENSITIVE_ACTIVE capability is REJECTed when the run is
        only authorized up to SAFE_ACTIVE. Cumulative grant stops at the max."""
        registry = _registry_with_test_capability(ActionRisk.SENSITIVE_ACTIVE)
        policy = PolicyEngine(registry=registry)
        scope = AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)
        run = Run(objective="sensitive rejected under safe", authorization=scope)
        logger = RunLogger(run)
        engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
        try:
            record = engine.execute(
                ActionRequest(capability="test.cap", action="run",
                              risk=ActionRisk.SENSITIVE_ACTIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SENSITIVE_ACTIVE" in record.policy_decision.reasons[0]
        finally:
            logger.close()


class TestProviderNotInvokedOnReject:
    """Unauthorized actions must be rejected BEFORE the provider is invoked."""

    def test_unauthorized_action_rejected_before_provider_invocation(self):
        """A RESTRICTED request against a SAFE_ACTIVE-only scope must NOT
        reach the provider. The tracking provider's execute_calls list stays
        empty — proving the engine gates provider.execute() behind policy."""
        tracker = _TrackingProvider()
        registry = _registry_with_test_capability(ActionRisk.RESTRICTED,
                                                  provider=tracker)
        policy = PolicyEngine(registry=registry)
        # SAFE_ACTIVE scope does NOT include RESTRICTED -> must reject
        scope = AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)
        run = Run(objective="provider not invoked", authorization=scope)
        logger = RunLogger(run)
        engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
        try:
            record = engine.execute(
                ActionRequest(capability="test.cap", action="run",
                              risk=ActionRisk.RESTRICTED)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert tracker.execute_calls == [], \
                f"provider was invoked despite REJECT: {tracker.execute_calls}"
        finally:
            logger.close()


class TestPassiveActionsWorkUnchanged:
    """PASSIVE actions are ALLOWed under the default (no-flag) scope — this
    preserves the Phase 2 + 2.5 back-compat requirement."""

    def test_passive_actions_allowed_under_default_scope(self):
        """All four catalogue-PASSIVE actions ALLOW under AuthorizationScope.default().
        This is the back-compat invariant: existing PASSIVE runs need no flag."""
        engine, run, logger = _default_engine(scenario="lab")
        try:
            passive_actions = [
                ("wifi.discovery",  "discover"),
                ("ble.discovery",   "discover"),
                ("nfc.discovery",   "scan"),
                ("subghz.discovery","spectrum"),
            ]
            for cap, action in passive_actions:
                record = engine.execute(
                    ActionRequest(capability=cap, action=action,
                                  risk=ActionRisk.PASSIVE)
                )
                assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                    f"{cap}.{action} should ALLOW under default scope; " \
                    f"got REJECT: {record.policy_decision.reasons}"
        finally:
            logger.close()


class TestAuthorizationScopeSerialization:
    """AuthorizationScope serializes round-trip; old run.json parses safely."""

    def test_authorization_scope_serialization_roundtrip(self):
        scope = AuthorizationScope.with_cumulative_tier(
            ActionRisk.SENSITIVE_ACTIVE, notes="lab audit 2026-08-16",
        )
        d = scope.to_dict()
        assert d["enabled"] is True
        assert d["notes"] == "lab audit 2026-08-16"
        assert set(d["allowed_risks"]) == {"passive", "safe_active", "sensitive_active"}
        restored = AuthorizationScope.from_dict(d)
        assert restored.allowed_risks == scope.allowed_risks
        assert restored.notes == scope.notes
        assert restored.enabled == scope.enabled

    def test_run_record_roundtrip_preserves_authorization(self):
        scope = AuthorizationScope.with_cumulative_tier(
            ActionRisk.RESTRICTED, notes="restricted lab",
        )
        engine, run, logger = _engine_with_scope(scope, scenario="lab", seed=7)
        try:
            # Run one PASSIVE action so the record isn't empty
            engine.execute(ActionRequest(capability="wifi.discovery",
                                         action="discover",
                                         risk=ActionRisk.PASSIVE))
        finally:
            logger.close()

        d = run.to_dict()
        assert d["authorization"]["enabled"] is True
        assert "restricted" in d["authorization"]["allowed_risks"]
        restored = Run.from_dict(d)
        assert restored.authorization.allowed_risks == scope.allowed_risks
        assert restored.authorization.notes == scope.notes
        # authoritative_risk also round-trips on the action record
        assert restored.actions[0].authoritative_risk == ActionRisk.PASSIVE

    def test_old_run_json_parses_with_default_scope(self):
        """A run.json blob produced before Phase 2.6 (no 'authorization' key,
        no 'authoritative_risk' key per action) parses via Run.from_dict into
        a PASSIVE-only default scope and None authoritative_risk values.
        Backward-compat for old on-disk artifacts."""
        old_blob = {
            "id": "run-legacy-12345",
            "objective": "legacy run",
            "scenario": "lab",
            "backend": "simulator",
            "seed": 42,
            "status": "completed",
            "started_at": 0.0,
            "completed_at": 1.0,
            "actions": [
                {
                    "request": {
                        "id": "req-1",
                        "capability": "wifi.discovery",
                        "action": "discover",
                        "args": {},
                        "risk": "passive",
                        "requested_at": 0.0,
                    },
                    "capability_decision": {
                        "capability": "wifi.discovery",
                        "action": "discover",
                        "provider": "simulator",
                        "supported": True,
                        "reason": "",
                    },
                    "policy_decision": {
                        "kind": "allow", "reasons": [], "decided_at": 0.0,
                    },
                    "observation": None,
                    "error": None,
                    "started_at": 0.0,
                    "completed_at": 0.5,
                }
            ],
            "observations": [],
            "capabilities_used": ["wifi.discovery.discover"],
            "errors": [],
            "findings": [],
            "final_summary": "legacy",
        }
        restored = Run.from_dict(old_blob)
        assert restored.authorization == AuthorizationScope.default()
        assert restored.authorization.enabled is False
        assert restored.actions[0].authoritative_risk is None


class TestDisjointGrantNonCumulative:
    """with_tiers(*tiers) is the explicit non-cumulative constructor — it grants
    exactly the listed tiers plus PASSIVE, no implicit lower tiers."""

    def test_authorization_scope_disjoint_grant_not_cumulative(self):
        """with_tiers(SAFE_ACTIVE, RESTRICTED) allows PASSIVE, SAFE_ACTIVE,
        and RESTRICTED — but NOT SENSITIVE_ACTIVE. Complements the cumulative
        CLI builder (with_cumulative_tier) used by --allow-risk."""
        scope = AuthorizationScope.with_tiers(
            ActionRisk.SAFE_ACTIVE, ActionRisk.RESTRICTED,
            notes="disjoint test",
        )
        assert scope.allows(ActionRisk.PASSIVE) is True
        assert scope.allows(ActionRisk.SAFE_ACTIVE) is True
        assert scope.allows(ActionRisk.RESTRICTED) is True
        # SENSITIVE_ACTIVE is NOT in the listed set and is NOT implicitly granted
        # (with_cumulative_tier(RESTRICTED) would include it; with_tiers does not).
        assert scope.allows(ActionRisk.SENSITIVE_ACTIVE) is False


# ── Standalone runner (no pytest required) ────────────────────────────────────

class _FakeTmpPath:
    def __init__(self, base: Path):
        self._base = base
    def __truediv__(self, name: str) -> Path:
        p = self._base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p26-"))
    os.environ["SURYAFOOL_RUNS_DIR"] = str(tmp / "runs")
    for name, cls in sorted(globals().items()):
        if not name.startswith("Test") or not isinstance(cls, type):
            continue
        for attr in sorted(dir(cls)):
            if not attr.startswith("test_"):
                continue
            test_name = f"{name}.{attr}"
            try:
                getattr(cls(), attr)()
                print(f"  PASS  {test_name}")
            except Exception:
                failures += 1
                print(f"  FAIL  {test_name}")
                traceback.print_exc()
    print(f"\n{'FAILED' if failures else 'PASSED'} - {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.exit(_run_all())
