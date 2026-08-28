"""
tests/test_phase27_active_sim.py

Phase 2.7 regression suite â€” stateful ACTIVE simulator capabilities.

Proves the deterministic core can safely execute the COMPLETE active chain
  discover -> inspect -> authorized active interaction -> observe changed state
with no LLM and no hardware, all gated by the existing Phase 2.6 authorization:

  1. ble.discovery.discover  PASSIVE (unchanged)           â€” initial discovery
  2. ble.discovery.inspect   PASSIVE (unchanged)           â€” read-only, surfaces state
  3. ble.discovery.connect   SAFE_ACTIVE  (new)            â€” active inspection;
     mutates the BleDevice entity (connected=True, gatt_services, characteristics)
  4. ble.discovery.write     SENSITIVE_ACTIVE (new)        â€” authorized active interaction;
     mutates device.characteristics[char]=value, OBSERVABLE in a later inspect
  5. unknown/malformed/invalid targets/args -> STRUCTURED failure Observations
     (no exception, no crashed run)
  6. unauthorized active actions are REJECTed at the POLICY gate BEFORE the
     provider is invoked -> environment state unchanged
  7. same seed -> identical observations (determinism)
  8. active_inspection_plan() completes under SENSITIVE_ACTIVE scope
  9. regression: Phase 2 default plan + the original four
     PASSIVE catalogue actions all intact

Run without pytest:
    python -m tests.test_phase27_active_sim
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
)
from policy.policy import PolicyEngine
from simulator.entities import BleDevice
from simulator.scenarios import build_scenario


LAB_TARGET = "AA:BB:CC:00:00:01"          # Suryafool-BLE-Target in scenario_lab
LAB_TARGET_2 = "AA:BB:CC:00:00:02"         # Suryafool-BLE-HeartRate-Sim
HOME_NON_CONNECTABLE = "C0:11:22:33:44:03"  # Unknown BLE (connectable=False) in home


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        """Isolate run artifacts under a temp dir for every test."""
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _engine_with_scope(scope=None, scenario="lab", seed=42):
    """Build a simulator-backed RunEngine authorized with `scope` (default PASSIVE).
    Returns (engine, run, logger, env)."""
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.7 test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _safe_active_scope():
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)


def _sensitive_active_scope():
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _device(env, address):
    for b in env.ble:
        if b.address == address:
            return b
    return None


def _sim_provider(engine):
    """The SimulatorProvider from a sim-backed engine (for direct handler tests)."""
    return engine.registry.providers()[0]


# â”€â”€ Target validation (unknown / malformed / invalid-type) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestTargetValidation:
    """Active/inspection actions validate targets and args structurally â€” no crash."""

    def test_discover_lists_lab_ble_targets(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute("ble.discovery", "discover")
            assert len(obs.entities) == 2
            assert {e.id for e in obs.entities} == {LAB_TARGET, LAB_TARGET_2}
        finally:
            logger.close()

    def test_inspect_known_target_returns_device_initial_state(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute(
                "ble.discovery", "inspect", {"address": LAB_TARGET})
            assert len(obs.entities) == 1
            assert obs.entities[0].id == LAB_TARGET
            assert obs.entities[0].attributes["connected"] is False
            assert obs.entities[0].attributes["characteristics"] == {}
            assert "not connected" in obs.summary
        finally:
            logger.close()

    def test_inspect_unknown_target_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute(
                "ble.discovery", "inspect", {"address": "99:99:99:99:99:99"})
            assert obs.entities == []
            assert "No BLE device found" in obs.summary
        finally:
            logger.close()

    def test_connect_unknown_target_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute(
                "ble.discovery", "connect", {"address": "99:99:99:99:99:99"})
            assert obs.entities == []
            assert "No BLE device found" in obs.summary
            assert all(not b.connected for b in env.ble)
        finally:
            logger.close()

    def test_connect_missing_address_arg_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute("ble.discovery", "connect", {})
            assert obs.entities == []
            assert "address" in obs.summary.lower()
            assert all(not b.connected for b in env.ble)
        finally:
            logger.close()

    def test_connect_non_string_address_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute(
                "ble.discovery", "connect", {"address": 12345})
            assert obs.entities == []
            assert "address" in obs.summary.lower()
            assert all(not b.connected for b in env.ble)
        finally:
            logger.close()

    def test_connect_non_connectable_device_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope(scenario="home")
        try:
            obs = _sim_provider(engine).execute(
                "ble.discovery", "connect", {"address": HOME_NON_CONNECTABLE})
            assert obs.entities == []
            assert "not connectable" in obs.summary
            assert _device(env, HOME_NON_CONNECTABLE).connected is False
        finally:
            logger.close()

    def test_write_unknown_target_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute(
                "ble.discovery", "write",
                {"address": "99:99:99:99:99:99", "characteristic": "battery",
                 "value": "x"})
            assert obs.entities == []
            assert "No BLE device found" in obs.summary
        finally:
            logger.close()

    def test_write_missing_characteristic_arg_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            _sim_provider(engine).execute(
                "ble.discovery", "connect", {"address": LAB_TARGET})
            obs = _sim_provider(engine).execute(
                "ble.discovery", "write", {"address": LAB_TARGET, "value": "x"})
            assert obs.entities == []
            assert "characteristic" in obs.summary.lower()
            # nothing written
            assert all(v == "" for v in _device(env, LAB_TARGET).characteristics.values())
        finally:
            logger.close()

    def test_write_missing_value_arg_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            _sim_provider(engine).execute(
                "ble.discovery", "connect", {"address": LAB_TARGET})
            obs = _sim_provider(engine).execute(
                "ble.discovery", "write",
                {"address": LAB_TARGET, "characteristic": "battery"})
            assert obs.entities == []
            assert "value" in obs.summary.lower()
            assert _device(env, LAB_TARGET).characteristics["battery"] == ""
        finally:
            logger.close()

    def test_write_to_unconnected_target_returns_structured_failure(self):
        """Valid known target, but not connected yet -> 'not connected' failure."""
        engine, run, logger, env = _engine_with_scope()
        try:
            obs = _sim_provider(engine).execute(
                "ble.discovery", "write",
                {"address": LAB_TARGET, "characteristic": "battery", "value": "75%"})
            assert obs.entities == []
            assert "not connected" in obs.summary
            assert _device(env, LAB_TARGET).characteristics == {}
        finally:
            logger.close()

    def test_write_unknown_characteristic_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            _sim_provider(engine).execute(
                "ble.discovery", "connect", {"address": LAB_TARGET})
            obs = _sim_provider(engine).execute(
                "ble.discovery", "write",
                {"address": LAB_TARGET, "characteristic": "no_such_char",
                 "value": "x"})
            assert obs.entities == []
            assert "Unknown characteristic" in obs.summary
        finally:
            logger.close()

    def test_malformed_connect_does_not_crash_run(self):
        """A malformed action (missing address) under an ALLOWING scope must
        produce a structured failure Observation, not flip the run to FAILED."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE, args={}))
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert record.observation is not None
            assert record.observation.entities == []
            assert "address" in record.observation.summary.lower()
            assert run.status != RunStatus.FAILED
            assert all(not b.connected for b in env.ble)
        finally:
            logger.close()


# â”€â”€ Authorization gate (policy is the authority; provider never decides) â”€â”€â”€â”€â”€

class TestAuthorizationGate:
    def test_connect_rejected_without_authorization(self):
        engine, run, logger, env = _engine_with_scope()  # PASSIVE-only default
        try:
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_TARGET}))
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            reasons = " ".join(record.policy_decision.reasons)
            assert "SAFE_ACTIVE" in reasons
            assert "AuthorizationScope" in reasons
        finally:
            logger.close()

    def test_connect_allowed_with_safe_active_scope(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_TARGET}))
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                record.policy_decision.reasons
            assert record.observation is not None
            assert "Connected to" in record.observation.summary
        finally:
            logger.close()

    def test_write_rejected_under_safe_active_scope(self):
        """Cumulative grant STOPS at SAFE_ACTIVE: write (SENSITIVE_ACTIVE) is
        still rejected there. Proves the tier boundary for the new action."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            # connect first (ALLOW under safe_active)
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_TARGET, "characteristic": "battery",
                                    "value": "75%"}))
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SENSITIVE_ACTIVE" in record.policy_decision.reasons[0]
        finally:
            logger.close()

    def test_write_allowed_with_sensitive_active_scope(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_TARGET, "characteristic": "battery",
                                    "value": "75%"}))
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                record.policy_decision.reasons
            assert record.observation is not None
            assert "Wrote value to characteristic" in record.observation.summary
        finally:
            logger.close()

    def test_caller_cannot_downgrade_write_to_safe_active(self):
        """write is catalogue SENSITIVE_ACTIVE; a request claiming SAFE_ACTIVE
        is rejected by RiskDeclarationRule (downgrade) â€” even if the scope
        would otherwise allow SENSITIVE_ACTIVE."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="write",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_TARGET, "characteristic": "battery",
                                    "value": "75%"}))
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            reasons = " ".join(record.policy_decision.reasons)
            assert "downgrade" in reasons.lower()
            assert "SENSITIVE_ACTIVE" in reasons
        finally:
            logger.close()

    def test_caller_cannot_upgrade_inspect_to_restricted(self):
        """inspect is catalogue PASSIVE; claiming RESTRICTED is rejected
        (upgrade) â€” keeps the new SAFE_ACTIVE/SENSITIVE_ACTIVE caps honest."""
        engine, run, logger, env = _engine_with_scope()
        try:
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="inspect",
                              risk=ActionRisk.RESTRICTED,
                              args={"address": LAB_TARGET}))
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            reasons = " ".join(record.policy_decision.reasons)
            assert "upgrade" in reasons.lower()
        finally:
            logger.close()

    def test_provider_not_reached_when_policy_rejects(self):
        """A REJECTED write must NOT mutate environment state â€” the provider's
        execute() never runs. Connect under safe_active (allowed, mutates
        state + initializes characteristics), then attempt write under the
        SAME safe_active scope (rejected) and assert characteristics unchanged."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            dev = _device(env, LAB_TARGET)
            snapshot = dict(dev.characteristics)
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_TARGET, "characteristic": "battery",
                                    "value": "75%"}))
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert dict(dev.characteristics) == snapshot, \
                "provider mutated state despite a REJECT â€” gate is broken"
            assert "ble_write:" not in ",".join(env.notes.keys())
        finally:
            logger.close()


# â”€â”€ State transitions (env actually maintains state; later obs reflect it) â”€â”€â”€

class TestStateTransitions:
    def test_connect_mutates_environment_state(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            dev = _device(env, LAB_TARGET)
            assert dev.connected is True
            assert "generic_access" in dev.gatt_services
            assert "battery" in dev.gatt_services  # advertised service cached
            assert set(dev.characteristics.keys()) == set(dev.gatt_services)
            assert all(v == "" for v in dev.characteristics.values())
            assert f"ble_connected:{LAB_TARGET}" in env.notes
        finally:
            logger.close()

    def test_write_mutates_environment_state(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            engine.execute(ActionRequest(capability="ble.discovery", action="write",
                                         risk=ActionRisk.SENSITIVE_ACTIVE,
                                         args={"address": LAB_TARGET,
                                               "characteristic": "battery",
                                               "value": "75%"}))
            assert _device(env, LAB_TARGET).characteristics["battery"] == "75%"
            assert f"ble_write:{LAB_TARGET}:battery" in env.notes
        finally:
            logger.close()

    def test_later_inspect_reflects_changed_state(self):
        """inspect AFTER write returns entity attributes that DIFFER from the
        initial inspect â€” proving the state change is observable, not faked."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            provider = _sim_provider(engine)
            before = provider.execute("ble.discovery", "inspect",
                                       {"address": LAB_TARGET})
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            engine.execute(ActionRequest(capability="ble.discovery", action="write",
                                         risk=ActionRisk.SENSITIVE_ACTIVE,
                                         args={"address": LAB_TARGET,
                                               "characteristic": "battery",
                                               "value": "75%"}))
            after = provider.execute("ble.discovery", "inspect",
                                      {"address": LAB_TARGET})
            assert before.entities[0].attributes["connected"] is False
            assert after.entities[0].attributes["connected"] is True
            assert before.entities[0].attributes["characteristics"] == {}
            assert after.entities[0].attributes["characteristics"]["battery"] == "75%"
            # The summaries differ (before/after proof for the report)
            assert before.summary != after.summary
            assert "connected" in after.summary and "1 characteristic(s) written" in after.summary
        finally:
            logger.close()

    def test_state_is_persistent_across_observation_calls(self):
        """Two consecutive inspects (no action between) return the SAME state â€”
        the state lives on the entity, not computed per call."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            provider = _sim_provider(engine)
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            o1 = provider.execute("ble.discovery", "inspect", {"address": LAB_TARGET})
            o2 = provider.execute("ble.discovery", "inspect", {"address": LAB_TARGET})
            assert o1.entities[0].attributes == o2.entities[0].attributes
            assert o1.summary == o2.summary
        finally:
            logger.close()


# â”€â”€ Determinism â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDeterminism:
    def test_same_seed_same_observations(self):
        """Two full engine runs with the same plan+seed+scope yield identical
        observation summaries and entity attributes for the active chain."""
        def run_once():
            engine, run, logger, env = _engine_with_scope(_sensitive_active_scope(),
                                                          seed=42)
            try:
                engine.run_plan(active_inspection_plan())
                return (
                    [a.observation.summary if a.observation else None
                     for a in run.actions],
                    [a.policy_decision.kind.value for a in run.actions],
                    [a.observation.entities[0].attributes
                     if a.observation and a.observation.entities else None
                     for a in run.actions],
                )
            finally:
                logger.close()
        a = run_once()
        b = run_once()
        assert a == b, "active chain is not deterministic across same-seed runs"

    def test_connect_shape_is_deterministic(self):
        """The set of GATT services cached on connect is deterministic for a
        given scenario device (derived from advertised_services, not random)."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope(), seed=7)
        try:
            engine.execute(ActionRequest(capability="ble.discovery", action="connect",
                                         risk=ActionRisk.SAFE_ACTIVE,
                                         args={"address": LAB_TARGET}))
            g = _device(env, LAB_TARGET).gatt_services
            assert g == ["battery", "device_info", "custom_service_uuid", "generic_access"]
        finally:
            logger.close()


# â”€â”€ Plan + end-to-end â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPlan:
    def test_active_inspection_plan_shape(self):
        plan = active_inspection_plan()
        assert len(plan) == 5
        assert [p.action for p in plan] == ["discover", "inspect", "connect",
                                            "write", "inspect"]
        # risks MUST match the catalogue (RiskDeclarationRule rejects mismatches)
        catalogue = {(c.capability, c.action): c.risk
                     for c in DEFAULT_CAPABILITIES}
        for p in plan:
            assert p.risk == catalogue[(p.capability, p.action)], \
                f"plan risk for {p.capability}.{p.action} does not match catalogue"

    def test_full_active_plan_completes_under_sensitive_active_scope(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(active_inspection_plan())
            assert run.status == RunStatus.COMPLETED
            assert len(run.actions) == 5
            assert run.errors == []
            # all 5 actions ALLOWed
            assert all(a.policy_decision.kind == PolicyDecisionKind.ALLOW
                       for a in run.actions)
            dev = _device(env, LAB_TARGET)
            assert dev.connected is True
            assert dev.characteristics["battery"] == "75%"
            # final inspect reflects the change
            final_inspect = run.actions[-1].observation
            assert final_inspect is not None
            assert "connected" in final_inspect.summary
            assert "1 characteristic(s) written" in final_inspect.summary
            assert final_inspect.entities[0].attributes["characteristics"]["battery"] == "75%"
        finally:
            logger.close()

    def test_full_active_plan_records_rejections_under_default_scope(self):
        """Under the PASSIVE-only default scope, connect+write are REJECTED at
        the policy gate; the run still COMPLETED (rejections don't fail it),
        and the environment is unchanged (provider never ran the actives)."""
        engine, run, logger, env = _engine_with_scope()  # PASSIVE-only
        try:
            engine.run_plan(active_inspection_plan())
            assert run.status == RunStatus.COMPLETED  # rejections != failure
            assert len(run.actions) == 5
            kinds = [a.policy_decision.kind for a in run.actions]
            # discover(0), inspect(1), inspect(4) -> ALLOW (passive)
            assert kinds[0] == PolicyDecisionKind.ALLOW
            assert kinds[1] == PolicyDecisionKind.ALLOW
            assert kinds[4] == PolicyDecisionKind.ALLOW
            # connect(2), write(3) -> REJECT
            assert kinds[2] == PolicyDecisionKind.REJECT
            assert kinds[3] == PolicyDecisionKind.REJECT
            assert "SAFE_ACTIVE" in run.actions[2].policy_decision.reasons[0]
            assert "SENSITIVE_ACTIVE" in run.actions[3].policy_decision.reasons[0]
            # provider never ran -> state unchanged
            dev = _device(env, LAB_TARGET)
            assert dev.connected is False
            assert dev.characteristics == {}
            # final inspect reflects the UNCHANGED state
            assert "not connected" in run.actions[-1].observation.summary
        finally:
            logger.close()

    def test_active_plan_events_written_to_jsonl(self):
        from engine.logger import run_dir
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(active_inspection_plan())
        finally:
            logger.close()
        events_path = run_dir(run.id) / "events.jsonl"
        assert events_path.exists()
        lines = [l for l in events_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) >= 2
        first = json.loads(lines[0])
        assert "type" in first


# â”€â”€ Regression: Phase 2 / 2.5 / 2.6 not broken â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegression:
    def test_phase2_default_plan_unchanged(self):
        """The original simulator exploration plan is intact: 4 PASSIVE actions."""
        plan = default_exploration_plan()
        assert len(plan) == 4
        assert all(p.risk == ActionRisk.PASSIVE for p in plan)
        assert {(p.capability, p.action) for p in plan} == {
            ("wifi.discovery", "discover"),
            ("ble.discovery", "discover"),
            ("nfc.discovery", "scan"),
            ("subghz.discovery", "spectrum"),
        }

    def test_catalogue_count_and_risks(self):
        """Guard: the active caps (Phase 2.7 BLE + Phase 2.7.2 Wi-Fi +
        Phase 2.7.3 BLE GATT) were ADDED without altering existing entries'
        risks. Phase 2.8.0 appended the multi-domain foundation (21 total);
        the 14 Phase 2.7 risks below remain unchanged."""
        by_key = {c.key: c.risk for c in DEFAULT_CAPABILITIES}
        assert len(DEFAULT_CAPABILITIES) == 23
        # originals unchanged
        assert by_key["wifi.discovery.discover"] == ActionRisk.PASSIVE
        assert by_key["wifi.discovery.inspect"] == ActionRisk.PASSIVE
        assert by_key["ble.discovery.discover"] == ActionRisk.PASSIVE
        assert by_key["ble.discovery.inspect"] == ActionRisk.PASSIVE
        assert by_key["nfc.discovery.scan"] == ActionRisk.PASSIVE
        assert by_key["nfc.discovery.read"] == ActionRisk.SAFE_ACTIVE
        assert by_key["subghz.discovery.spectrum"] == ActionRisk.PASSIVE
        assert by_key["subghz.discovery.analyze"] == ActionRisk.SAFE_ACTIVE
        # Phase 2.7 BLE active caps
        assert by_key["ble.discovery.connect"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.discovery.write"] == ActionRisk.SENSITIVE_ACTIVE
        # Phase 2.7.2 Wi-Fi capture caps
        assert by_key["wifi.capture.handshake"] == ActionRisk.SAFE_ACTIVE
        assert by_key["wifi.capture.pmkid"] == ActionRisk.SENSITIVE_ACTIVE
        # Phase 2.7.3 BLE GATT caps (parallel to wifi.capture namespace)
        assert by_key["ble.gatt.pair"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.gatt.write"] == ActionRisk.SENSITIVE_ACTIVE

    def test_original_passive_actions_still_allow_under_default_scope(self):
        """The four original PASSIVE discovery actions still ALLOW under the
        default PASSIVE-only scope (Phase 2.6 back-compat)."""
        engine, run, logger, env = _engine_with_scope()
        try:
            for cap, action in [("wifi.discovery", "discover"),
                                ("ble.discovery", "discover"),
                                ("nfc.discovery", "scan"),
                                ("subghz.discovery", "spectrum")]:
                record = engine.execute(
                    ActionRequest(capability=cap, action=action,
                                  risk=ActionRisk.PASSIVE))
                assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                    f"{cap}.{action} should ALLOW under default scope; " \
                    f"got REJECT: {record.policy_decision.reasons}"
        finally:
            logger.close()

    def test_bledevice_new_fields_default_safely(self):
        b = BleDevice(address="AA:BB:CC:00:00:01", name="x", rssi=-50)
        assert b.connected is False
        assert b.gatt_services == []
        assert b.characteristics == {}
        d = b.to_dict()
        assert d["connected"] is False
        assert d["gatt_services"] == []
        assert d["characteristics"] == {}
        # existing fields still present
        assert d["connectable"] is True
        assert d["advertised_services"] == []


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p27-"))
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
