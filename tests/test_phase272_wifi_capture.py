"""
tests/test_phase272_wifi_capture.py

Phase 2.7.2 regression suite â€” stateful Wi-Fi capture simulator capabilities.

Proves the deterministic core can safely execute the COMPLETE Wi-Fi capture
chain

  discover -> inspect -> capture.handshake -> capture.pmkid -> inspect

with no LLM and no hardware, all gated by the unchanged Phase 2.6
authorization gate. Mirrors the Phase 2.7 BLE active lifecycle pattern but
over the new `wifi.capture` namespace (Risinek's capture-vs-discovery
separation encoded into Suryafool's typed capability model):

  1. wifi.discovery.discover  PASSIVE  (unchanged)  â€” initial discovery
  2. wifi.discovery.inspect   PASSIVE  (unchanged)  â€” read-only, surfaces state
  3. wifi.capture.handshake   SAFE_ACTIVE (new)     â€” mutates WifiNetwork entity
     (handshake_captured=True, captured_frames=4, stamps env.notes)
  4. wifi.capture.pmkid      SENSITIVE_ACTIVE (new)â€” mutates WifiNetwork entity
     (pmkid_captured=True, stamps env.notes; requires wifi.capture.handshake
     on the SAME bssid first â€” else structured failure Observation)
  5. unknown/malformed/invalid target / non-WPA encryption / prereq-not-met
     -> STRUCTURED failure Observations (no exception, no crashed run, env
     unchanged)
  6. unauthorized active actions are REJECTed at the POLICY gate BEFORE the
     provider is invoked -> environment state unchanged
  7. same seed -> identical observations (determinism)
  8. wifi_capture_plan() completes under SENSITIVE_ACTIVE scope
  9. regression: Phase 2 / 2.6 / 2.7 / 2.7.1 still intact

Run without pytest:
    python -m tests.test_phase272_wifi_capture
"""

import json
import os
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None  # standalone runner works without pytest

from capabilities.base import DEFAULT_CAPABILITIES
from capabilities.registry import default_registry
from core.mission import (
    ActionRequest,
    ActionRisk,
    AuthorizationScope,
    PolicyDecisionKind,
    Run,
    RunStatus,
)
from core.observation import Observation
from engine.logger import RunLogger
from engine.runner import (
    RunEngine,
    active_inspection_plan,
    default_exploration_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from simulator.entities import WifiNetwork
from simulator.scenarios import build_scenario
from simulator.simulator import performed_capability_keys


# Lab scenario literal bssids (seed-independent for those entries).
LAB_WIFI_WPA3 = "02:00:00:00:00:01"      # LAB-INTERNAL, WPA3 â€” the plan target
LAB_WIFI_OPEN = "02:00:00:00:00:02"      # LAB-TARGET-OPEN â€” non-WPA path
LAB_WIFI_WEP  = "02:00:00:00:00:03"      # LAB-TARGET-WEP â€” non-WPA path
HOME_WIFI_WPA2 = "02:00:00:00:00:12"     # HomeNet-2.4G, WPA2


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        """Isolate run artifacts under a temp dir for every test."""
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _sensitive_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _safe_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    """Build a simulator-backed RunEngine authorized with `scope`
    (default PASSIVE). Returns (engine, run, logger, env)."""
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.7.2 test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _device_by_addr(env, bssid):
    for w in env.wifi:
        if w.bssid == bssid:
            return w
    return None


# â”€â”€ 1. WifiNetwork new stateful fields â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestWifiNetworkNewFields:
    def test_new_fields_default_safely(self):
        w = WifiNetwork(ssid="x", bssid="AA", channel=1, rssi=-50, encryption="WPA2")
        assert w.handshake_captured is False
        assert w.captured_frames == 0
        assert w.pmkid_captured is False

    def test_to_dict_carries_new_fields(self):
        w = WifiNetwork(ssid="x", bssid="AA", channel=1, rssi=-50, encryption="WPA2")
        d = w.to_dict()
        # original fields preserved
        for k in ("ssid", "bssid", "channel", "rssi", "encryption",
                  "signal_strength", "vendor_hint"):
            assert k in d
        # new stateful fields surfaced
        for k in ("handshake_captured", "captured_frames", "pmkid_captured"):
            assert k in d, f"to_dict missing new field: {k}"
        # JSON round-trip clean (the run record + reports rely on this)
        assert json.loads(json.dumps(d)) == d


# â”€â”€ 2. action_wifi_capture_handshake handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestHandshakeHandler:
    """Direct simulator handler calls â€” bypass the engine/policy gate so we
    isolate the handler's own semantics (before policy is added later)."""

    def test_missing_bssid_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_handshake
        obs = action_wifi_capture_handshake(env, {})
        assert obs.entities == []
        assert "missing" in obs.summary.lower() and "handshake" in obs.summary.lower()
        assert all(not w.handshake_captured for w in env.wifi)
        assert all("wifi_handshake:" not in k for k in env.notes)

    def test_non_string_bssid_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_handshake
        obs = action_wifi_capture_handshake(env, {"bssid": 12345})
        assert obs.entities == []
        assert "invalid" in obs.summary.lower() or "missing" in obs.summary.lower()
        assert all("wifi_handshake:" not in k for k in env.notes)

    def test_unknown_bssid_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_handshake
        obs = action_wifi_capture_handshake(env, {"bssid": "DE:AD:BE:EF:00:99"})
        assert obs.entities == []
        assert "No Wi-Fi network found" in obs.summary
        assert all("wifi_handshake:" not in k for k in env.notes)

    def test_open_network_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_handshake
        obs = action_wifi_capture_handshake(env, {"bssid": LAB_WIFI_OPEN})
        assert obs.entities == []
        assert "OPEN" in obs.summary and "no WPA handshake" in obs.summary
        w = _device_by_addr(env, LAB_WIFI_OPEN)
        assert w.handshake_captured is False
        assert all("wifi_handshake:" not in k for k in env.notes)

    def test_wep_network_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_handshake
        obs = action_wifi_capture_handshake(env, {"bssid": LAB_WIFI_WEP})
        assert obs.entities == []
        assert "WEP" in obs.summary and "no WPA handshake" in obs.summary
        w = _device_by_addr(env, LAB_WIFI_WEP)
        assert w.handshake_captured is False

    def test_wpa3_target_successful_capture_mutates_state(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_handshake
        w = _device_by_addr(env, LAB_WIFI_WPA3)
        assert w.handshake_captured is False
        assert w.captured_frames == 0
        obs = action_wifi_capture_handshake(env, {"bssid": LAB_WIFI_WPA3})
        assert obs.capability == "wifi.capture"
        assert obs.action == "handshake"
        assert len(obs.entities) == 1
        ent = obs.entities[0]
        assert ent.id == LAB_WIFI_WPA3
        assert ent.attributes["handshake_captured"] is True
        assert ent.attributes["captured_frames"] == 4
        # entity state changed too
        assert w.handshake_captured is True
        assert w.captured_frames == 4
        assert f"wifi_handshake:{LAB_WIFI_WPA3}" in env.notes

    def test_wpa2_home_target_successful_capture(self):
        env = build_scenario("home", seed=42)
        from simulator.simulator import action_wifi_capture_handshake
        obs = action_wifi_capture_handshake(env, {"bssid": HOME_WIFI_WPA2})
        assert len(obs.entities) == 1
        assert obs.entities[0].attributes["handshake_captured"] is True
        w = _device_by_addr(env, HOME_WIFI_WPA2)
        assert w.handshake_captured is True


# â”€â”€ 3. action_wifi_capture_pmkid handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPmkidHandler:
    def test_missing_bssid_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_pmkid
        obs = action_wifi_capture_pmkid(env, {})
        assert obs.entities == []
        assert "missing" in obs.summary.lower() and "pmkid" in obs.summary.lower()
        assert all("wifi_pmkid:" not in k for k in env.notes)

    def test_unknown_bssid_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_pmkid
        obs = action_wifi_capture_pmkid(env, {"bssid": "DE:AD:BE:EF:00:99"})
        assert obs.entities == []
        assert "No Wi-Fi network found" in obs.summary

    def test_open_network_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_pmkid
        obs = action_wifi_capture_pmkid(env, {"bssid": LAB_WIFI_OPEN})
        assert obs.entities == []
        assert "OPEN" in obs.summary and "no PMKID" in obs.summary

    def test_pmkid_without_preceding_handshake_returns_structured_failure(self):
        """Prereq enforced at the per-bssid level: no wifi_handshake:<bssid>
        note means handshake has not captured this specific target, so pmkid
        aborts with a structured Observation. env unchanged."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_wifi_capture_pmkid
        obs = action_wifi_capture_pmkid(env, {"bssid": LAB_WIFI_WPA3})
        assert obs.entities == []
        assert "No handshake captured" in obs.summary
        assert "wifi.capture.handshake first" in obs.summary
        w = _device_by_addr(env, LAB_WIFI_WPA3)
        assert w.pmkid_captured is False
        assert all("wifi_pmkid:" not in k for k in env.notes)

    def test_pmkid_after_handshake_on_same_target_succeeds_and_mutates(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import (
            action_wifi_capture_handshake, action_wifi_capture_pmkid,
        )
        # Pre-condition: handshake on the LAB target.
        action_wifi_capture_handshake(env, {"bssid": LAB_WIFI_WPA3})
        w = _device_by_addr(env, LAB_WIFI_WPA3)
        assert w.handshake_captured is True
        assert w.pmkid_captured is False
        # Now pmkid
        obs = action_wifi_capture_pmkid(env, {"bssid": LAB_WIFI_WPA3})
        assert obs.capability == "wifi.capture"
        assert obs.action == "pmkid"
        assert len(obs.entities) == 1
        ent = obs.entities[0]
        assert ent.attributes["pmkid_captured"] is True
        assert w.pmkid_captured is True
        assert f"wifi_pmkid:{LAB_WIFI_WPA3}" in env.notes

    def test_pmkid_after_handshake_on_a_different_bsid_fails_per_target(self):
        """The per-target prereq is keyed by bssid: capturing the handshake
        on one WPA network does NOT authorize pmkid against another WPA
        network."""
        from simulator.simulator import (
            action_wifi_capture_handshake, action_wifi_capture_pmkid,
        )
        from simulator.environment import Environment
        env = Environment(name="t", wifi=[
            WifiNetwork(ssid="A", bssid="02:00:00:00:00:01", channel=1,
                        rssi=-50, encryption="WPA3"),
            WifiNetwork(ssid="B", bssid="02:00:00:00:00:02", channel=1,
                        rssi=-50, encryption="WPA2"),
        ])
        # Handshake on the first WPA network.
        action_wifi_capture_handshake(env, {"bssid": "02:00:00:00:00:01"})
        # PMKID attempted on the second network â€” fails per-target.
        obs = action_wifi_capture_pmkid(env, {"bssid": "02:00:00:00:00:02"})
        assert obs.entities == []
        assert "No handshake captured" in obs.summary
        assert all("wifi_pmkid:" not in k for k in env.notes)


# â”€â”€ 4. Handshake authorization gate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestHandshakeAuthorizationGate:
    def test_handshake_rejected_under_passive_scope_env_unchanged(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            cap = engine.registry.capability("wifi.capture", "handshake")
            assert cap is not None
            assert cap.mutates_state is True
            assert cap.risk == ActionRisk.SAFE_ACTIVE
            record = engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SAFE_ACTIVE" in record.policy_decision.reasons[0]
            # Provider never ran -> env untouched.
            assert performed_capability_keys(env) == set()
            assert all(not w.handshake_captured for w in env.wifi)
            assert all("wifi_handshake:" not in k for k in env.notes)
            # Authoritative risk still resolved (Phase 2.6 invariant).
            assert record.authoritative_risk == ActionRisk.SAFE_ACTIVE
        finally:
            logger.close()

    def test_handshake_allows_under_safe_active_scope(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert record.observation is not None
            assert len(record.observation.entities) == 1
            w = _device_by_addr(env, LAB_WIFI_WPA3)
            assert w.handshake_captured is True
        finally:
            logger.close()

    def test_handshake_caller_downgrade_rejected_by_risk_rule(self):
        """request.risk=PASSIVE but cap.risk=SAFE_ACTIVE -> the caller
        self-disclosed a lower tier than the authoritative one. The
        RiskDeclarationRule rejects the mismatch (caller cannot downgrade)."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              risk=ActionRisk.PASSIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert all(not w.handshake_captured for w in env.wifi)
        finally:
            logger.close()

    def test_handshake_caller_upgrade_rejected_by_risk_rule(self):
        """request.risk=SENSITIVE_ACTIVE but cap.risk=SAFE_ACTIVE -> the
        caller self-disclosed a higher tier than the authoritative one. The
        RiskDeclarationRule rejects the mismatch (caller cannot upgrade)."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert all(not w.handshake_captured for w in env.wifi)
        finally:
            logger.close()


# â”€â”€ 5. PMKID authorization gate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPmkidAuthorizationGate:
    def test_pmkid_rejected_under_passive_scope_env_unchanged(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            record = engine.execute(
                ActionRequest(capability="wifi.capture", action="pmkid",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SENSITIVE_ACTIVE" in record.policy_decision.reasons[0]
            assert performed_capability_keys(env) == set()
            assert all("wifi_pmkid:" not in k for k in env.notes)
            assert record.authoritative_risk == ActionRisk.SENSITIVE_ACTIVE
        finally:
            logger.close()

    def test_pmkid_rejected_under_safe_active_scope_at_tier_gate(self):
        """SAFE_ACTIVE scope does NOT include SENSITIVE_ACTIVE, so pmkid is
        REJECTed at the tier gate even though handshake might ALLOW under
        the same scope (cumulative stops at SAFE_ACTIVE)."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            # Handshake ALLOWs...
            rec_hs = engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert rec_hs.policy_decision.kind == PolicyDecisionKind.ALLOW
            # ...but pmkid REJECTs at the tier gate.
            rec_pm = engine.execute(
                ActionRequest(capability="wifi.capture", action="pmkid",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert rec_pm.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SENSITIVE_ACTIVE" in rec_pm.policy_decision.reasons[0]
            # handshake mutated env; pmkid did NOT.
            w = _device_by_addr(env, LAB_WIFI_WPA3)
            assert w.handshake_captured is True
            assert w.pmkid_captured is False
            assert all("wifi_pmkid:" not in k for k in env.notes)
        finally:
            logger.close()

    def test_pmkid_allows_under_sensitive_active_scope_after_handshake(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            # Prereq handshake.
            rec_hs = engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert rec_hs.policy_decision.kind == PolicyDecisionKind.ALLOW
            # PMKID ALLOWs.
            rec_pm = engine.execute(
                ActionRequest(capability="wifi.capture", action="pmkid",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert rec_pm.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(rec_pm.observation.entities) == 1
            w = _device_by_addr(env, LAB_WIFI_WPA3)
            assert w.pmkid_captured is True
            assert f"wifi_pmkid:{LAB_WIFI_WPA3}" in env.notes
        finally:
            logger.close()

    def test_pmkid_caller_downgrade_rejected_by_risk_rule(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="wifi.capture", action="pmkid",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"bssid": LAB_WIFI_WPA3})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert all("wifi_pmkid:" not in k for k in env.notes)
        finally:
            logger.close()


# â”€â”€ 6. wifi_capture_plan end-to-end shape + state reflection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestWifiCapturePlan:
    def test_plan_shape_risks_match_catalogue(self):
        plan = wifi_capture_plan()
        assert len(plan) == 5
        reg = default_registry(environment=build_scenario("lab", seed=42))
        for req in plan:
            cap = reg.capability(req.capability, req.action)
            assert cap is not None
            # Caller self-disclosed risk must equal authoritative cap.risk.
            assert req.risk == cap.risk, f"{req.capability}.{req.action}"
        # Discovers/inspects PASSIVE, handshake SAFE_ACTIVE, pmkid SENSITIVE_ACTIVE
        risks = [(p.capability, p.action, p.risk) for p in plan]
        assert ("wifi.discovery", "discover",  ActionRisk.PASSIVE) in risks
        assert ("wifi.discovery", "inspect",   ActionRisk.PASSIVE) in risks
        assert ("wifi.capture",   "handshake", ActionRisk.SAFE_ACTIVE) in risks
        assert ("wifi.capture",   "pmkid",     ActionRisk.SENSITIVE_ACTIVE) in risks
        # Two inspect actions (initial + final) â€” the observe->test->observe loop.
        assert sum(1 for p in plan
                   if p.capability == "wifi.discovery" and p.action == "inspect") == 2

    def test_plan_completes_under_sensitive_active_scope(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(wifi_capture_plan())
            assert run.status == RunStatus.COMPLETED
            w = _device_by_addr(env, LAB_WIFI_WPA3)
            assert w.handshake_captured is True
            assert w.pmkid_captured is True
            performed = performed_capability_keys(env)
            assert "wifi.capture.handshake" in performed
            assert "wifi.capture.pmkid" in performed
        finally:
            logger.close()

    def test_plan_under_passive_scope_records_rejections_and_completes(self):
        """Under a PASSIVE-only default scope, capture.handshake and
        capture.pmkid are REJECTed at the gate but the run still COMPLETED
        (rejections are valid runs). discover/inspect ALLOW. env unchanged
        for any capture cap. The plan exercises 5 actions total."""
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.run_plan(wifi_capture_plan())
            assert run.status == RunStatus.COMPLETED
            # 2 captures were both rejected (policy gate).
            rejected = [r for r in run.actions
                       if r.policy_decision.kind == PolicyDecisionKind.REJECT]
            assert len(rejected) == 2
            rejected_keys = {(r.request.capability, r.request.action) for r in rejected}
            assert rejected_keys == {("wifi.capture", "handshake"),
                                     ("wifi.capture", "pmkid")}
            w = _device_by_addr(env, LAB_WIFI_WPA3)
            assert w.handshake_captured is False
            assert w.pmkid_captured is False
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()

    def test_plan_writes_events_jsonl_to_disk(self):
        # Relies on the pytest autouse fixture (or _run_all() setup) to
        # point SURYAFOOL_RUNS_DIR at a temp dir; this test just verifies
        # the events.jsonl audit trail is written for a completed run.
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(wifi_capture_plan())
            assert run.status == RunStatus.COMPLETED
        finally:
            logger.close()
        from engine.logger import run_dir
        events_path = run_dir(run.id) / "events.jsonl"
        assert events_path.exists(), f"events.jsonl missing at {events_path}"
        lines = events_path.read_text().splitlines()
        events = [json.loads(line) for line in lines if line.strip()]
        types = {e.get("type") for e in events}
        # Run lifecycle + at least one finding emitted by an executed action.
        assert "agent.status" in types
        assert "finding.created" in types


# â”€â”€ 7. State reflection â€” inspect summary differs before/after capture â”€â”€â”€â”€â”€â”€â”€

class TestInspectReflectsStateChange:
    def test_initial_inspect_summary_differs_from_final_after_capture_chain(self):
        """Run discover -> inspect (initial) -> handshake -> pmkid ->
        inspect (final). The two wifi.discovery.inspect Observations differ:
        the first sees handshake_captured=False; the final sees
        handshake_captured=True, pmkid_captured=True."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            # Initial inspect of the lab target.
            rec_initial = engine.execute(
                ActionRequest(capability="wifi.discovery", action="inspect",
                              args={"bssid": LAB_WIFI_WPA3},
                              risk=ActionRisk.PASSIVE)
            )
            assert rec_initial.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(rec_initial.observation.entities) == 1
            attrs_initial = rec_initial.observation.entities[0].attributes
            assert attrs_initial["handshake_captured"] is False
            assert attrs_initial["pmkid_captured"] is False
            # Run the capture chain.
            engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              args={"bssid": LAB_WIFI_WPA3},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            engine.execute(
                ActionRequest(capability="wifi.capture", action="pmkid",
                              args={"bssid": LAB_WIFI_WPA3},
                              risk=ActionRisk.SENSITIVE_ACTIVE)
            )
            # Final inspect.
            rec_final = engine.execute(
                ActionRequest(capability="wifi.discovery", action="inspect",
                              args={"bssid": LAB_WIFI_WPA3},
                              risk=ActionRisk.PASSIVE)
            )
            assert rec_final.policy_decision.kind == PolicyDecisionKind.ALLOW
            attrs_final = rec_final.observation.entities[0].attributes
            assert attrs_final["handshake_captured"] is True
            assert attrs_final["pmkid_captured"] is True
            assert attrs_final["captured_frames"] == 4
            # The summary strings differ â€” state mutated visibly.
            assert rec_final.observation.summary != rec_initial.observation.summary
        finally:
            logger.close()


# â”€â”€ 8. Determinism â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDeterminism:
    def _capture_obs_for_seed(self, seed: int) -> tuple[Observation, Observation]:
        engine, run, logger, env = _engine_with_scope(
            _sensitive_active_scope(), seed=seed)
        try:
            rec_hs = engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              args={"bssid": LAB_WIFI_WPA3},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            rec_pm = engine.execute(
                ActionRequest(capability="wifi.capture", action="pmkid",
                              args={"bssid": LAB_WIFI_WPA3},
                              risk=ActionRisk.SENSITIVE_ACTIVE)
            )
            return rec_hs.observation, rec_pm.observation
        finally:
            logger.close()

    def test_same_seed_yields_identical_observations(self):
        obs_hs_1, obs_pm_1 = self._capture_obs_for_seed(7)
        obs_hs_2, obs_pm_2 = self._capture_obs_for_seed(7)
        assert obs_hs_1.summary == obs_hs_2.summary
        assert obs_pm_1.summary == obs_pm_2.summary
        # Entity.attributes carry the WifiNetwork state dict (not Entity.to_dict,
        # which nests it under 'attributes'). Compare state columns directly.
        a_hs1 = obs_hs_1.entities[0].attributes
        a_hs2 = obs_hs_2.entities[0].attributes
        assert a_hs1["handshake_captured"] == a_hs2["handshake_captured"]
        assert a_hs1["captured_frames"] == a_hs2["captured_frames"]
        a_pm1 = obs_pm_1.entities[0].attributes
        a_pm2 = obs_pm_2.entities[0].attributes
        assert a_pm1["pmkid_captured"] == a_pm2["pmkid_captured"]


# â”€â”€ 9. Phase 2.7.1 contract metadata consumption via performed set â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestContractMetadataConsumption:
    def test_both_new_caps_marked_mutates_state_in_catalogue(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["wifi.capture.handshake"].mutates_state is True
        assert by_key["wifi.capture.pmkid"].mutates_state is True

    def test_pmkid_prerequisites_met_flips_after_handshake(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            cap_pmkid = engine.registry.capability("wifi.capture", "pmkid")
            assert cap_pmkid.requires == ("wifi.capture.handshake",)
            performed = performed_capability_keys(env)
            assert cap_pmkid.prerequisites_met(performed) is False
            engine.execute(
                ActionRequest(capability="wifi.capture", action="handshake",
                              args={"bssid": LAB_WIFI_WPA3},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            performed = performed_capability_keys(env)
            assert "wifi.capture.handshake" in performed
            assert cap_pmkid.prerequisites_met(performed) is True
        finally:
            logger.close()

    def test_passive_wifi_discover_does_not_alter_performed_set(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            assert performed_capability_keys(env) == set()
            engine.execute(
                ActionRequest(capability="wifi.discovery", action="discover",
                              risk=ActionRisk.PASSIVE)
            )
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()


# â”€â”€ 10. Regression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegression:
    def test_phase2_default_plan_unchanged(self):
        plan = default_exploration_plan()
        assert len(plan) == 4
        assert all(p.risk == ActionRisk.PASSIVE for p in plan)

    def test_catalogue_count_and_risks(self):
        by_key = {c.key: c.risk for c in DEFAULT_CAPABILITIES}
        assert len(DEFAULT_CAPABILITIES) == 26
        # Phase 2.7.2 additions present, with prescribed risks.
        assert by_key["wifi.capture.handshake"] == ActionRisk.SAFE_ACTIVE
        assert by_key["wifi.capture.pmkid"] == ActionRisk.SENSITIVE_ACTIVE
        # Phase 2.7.3 additions present, with prescribed risks (parallel to
        # the wifi.capture namespace).
        assert by_key["ble.gatt.pair"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.gatt.write"] == ActionRisk.SENSITIVE_ACTIVE

    def test_wifi_new_fields_default_safely(self):
        """Sanity: WifiNetwork still constructs with original positional args
        (Phase 2.7.1 back-compat extends to the Phase 2.7.2 additions)."""
        w = WifiNetwork(ssid="x", bssid="AA", channel=1, rssi=-50, encryption="OPEN")
        d = w.to_dict()
        assert d["handshake_captured"] is False
        assert d["captured_frames"] == 0
        assert d["pmkid_captured"] is False


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p272-"))
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
