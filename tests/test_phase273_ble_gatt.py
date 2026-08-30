"""
tests/test_phase273_ble_gatt.py

Phase 2.7.3 regression suite â€” stateful BLE GATT pairing + encrypted write.

Proves the deterministic core can safely execute the COMPLETE BLE GATT
stateful chain

  discover -> inspect -> connect (Phase 2.7 SAFE_ACTIVE) ->
  ble.gatt.pair (NEW SAFE_ACTIVE)       -> mutates BleDevice entity
    (paired=True, inits secure_characteristics, stamps env.notes)
  ble.gatt.write (NEW SENSITIVE_ACTIVE) -> mutates BleDevice entity
    (secure_characteristics[char]=value, stamps env.notes; requires
    ble.gatt.pair on the SAME address first â€” else structured failure)
  inspect (reflects paired + secure-write state)

with no LLM and no hardware, gated by the unchanged Phase 2.6 authorization
gate. The new `ble.gatt` namespace sits alongside `ble.discovery` exactly
as `wifi.capture` (Phase 2.7.2) sits alongside `wifi.discovery` â€” encoding
the architectural distinction (Risinek-style separation) between discovery
observations and GATT-level state-changing operations inside Suryafool's
own typed capability model:

  1. ble.discovery.discover PASSIVE  (unchanged) â€” initial discovery
  2. ble.discovery.inspect  PASSIVE  (unchanged) â€” read-only, surfaces state
  3. ble.discovery.connect  SAFE_ACTIVE (Phase 2.7) â€” link-layer GATT connect
  4. ble.gatt.pair          SAFE_ACTIVE (NEW) â€” establish pairing/bonding
     session on the connected device; mutates BleDevice.paired + secure
     characteristic table; per-target: requires b.connected=True
  5. ble.gatt.write         SENSITIVE_ACTIVE (NEW) â€” write an encrypted
     characteristic inside the bonded session; mutates BleDevice.
     secure_characteristics[char]=value; per-target: requires b.paired=True
  6. unknown/malformed/invalid target / not-connectable / not-connected /
     not-paired / unknown characteristic / missing args -> STRUCTURED
     failure Observations (no exception, no crashed run, env unchanged)
  7. unauthorized active actions are REJECTed at the POLICY gate BEFORE
     the provider is invoked -> environment state unchanged
  8. same seed -> identical observations (determinism)
  9. ble_gatt_workflow_plan() completes under SENSITIVE_ACTIVE scope
 10. regression: Phase 2 / 2.6 / 2.7 / 2.7.1 / 2.7.2 still intact

Run without pytest:
    python -m tests.test_phase273_ble_gatt
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
    ble_gatt_workflow_plan,
    default_exploration_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from simulator.entities import BleDevice
from simulator.environment import Environment
from simulator.scenarios import build_scenario
from simulator.simulator import performed_capability_keys


# Lab scenario BLE literal addresses (seed-independent for those entries).
LAB_BLE_TARGET = "AA:BB:CC:00:00:01"      # Suryafool-BLE-Target â€” the plan target
LAB_BLE_HEART  = "AA:BB:CC:00:00:02"      # Suryafool-BLE-HeartRate-Sim
HOME_BLE_NON_CONNECTABLE = "C0:11:22:33:44:03"  # home scenario, connectable=False


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        """Isolate run artifacts under a temp dir for every test."""
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _safe_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)


def _sensitive_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    """Build a simulator-backed RunEngine authorized with `scope` (default
    PASSIVE). Returns (engine, run, logger, env)."""
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.7.3 test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _device(env, address):
    for b in env.ble:
        if b.address == address:
            return b
    return None


def _sim_provider(engine):
    return engine.registry.providers()[0]


def _connect_target(provider, address=LAB_BLE_TARGET):
    """Run the legacy Phase 2.7 ble.discovery.connect so later gatt tests
    start from a connected device (the per-target b.connected=True prereq)."""
    return provider.execute("ble.discovery", "connect", {"address": address})


def _pair_target(provider, address=LAB_BLE_TARGET):
    return provider.execute("ble.gatt", "pair", {"address": address})


# â”€â”€ 1. BleDevice new stateful fields â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBleDeviceNewFields:
    def test_new_fields_default_safely(self):
        b = BleDevice(address="AA:BB:CC:00:00:01", name="x", rssi=-50)
        assert b.paired is False
        assert b.secure_characteristics == {}

    def test_to_dict_carries_new_fields(self):
        b = BleDevice(address="AA:BB:CC:00:00:01", name="x", rssi=-50)
        d = b.to_dict()
        # original fields preserved
        for k in ("address", "name", "rssi", "advertised_services",
                  "manufacturer", "connectable", "connected",
                  "gatt_services", "characteristics"):
            assert k in d, f"to_dict missing original field: {k}"
        # new stateful fields surfaced
        for k in ("paired", "secure_characteristics"):
            assert k in d, f"to_dict missing new field: {k}"
        # JSON round-trip clean (the run record + reports rely on this)
        assert json.loads(json.dumps(d)) == d

    def test_positional_constructor_back_compat(self):
        """Original BleDevice positional constructor still builds cleanly â€”
        the Phase 2.7.3 fields have safe defaults and don't disturb callers."""
        b = BleDevice("AA:BB:CC:00:00:01", "Speaker", -55,
                      ["audio"], "Sonos", True)
        assert b.paired is False
        assert b.secure_characteristics == {}


# â”€â”€ 2. action_ble_gatt_pair handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPairHandler:
    """Direct simulator handler calls â€” bypass the engine/policy gate so we
    isolate the handler's own semantics (before policy is added later)."""

    def test_missing_address_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_pair
        obs = action_ble_gatt_pair(env, {})
        assert obs.entities == []
        assert obs.capability == "ble.gatt"
        assert obs.action == "pair"
        assert "missing" in obs.summary.lower() and "pair" in obs.summary.lower()
        assert all(not b.paired for b in env.ble)
        assert all("ble_paired:" not in k for k in env.notes)

    def test_non_string_address_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_pair
        obs = action_ble_gatt_pair(env, {"address": 12345})
        assert obs.entities == []
        assert "invalid" in obs.summary.lower() or "missing" in obs.summary.lower()
        assert all("ble_paired:" not in k for k in env.notes)

    def test_unknown_address_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_pair
        obs = action_ble_gatt_pair(env, {"address": "DE:AD:BE:EF:00:99"})
        assert obs.entities == []
        assert "No BLE device found" in obs.summary
        assert all("ble_paired:" not in k for k in env.notes)

    def test_non_connectable_target_returns_structured_failure(self):
        """Even if you somehow reached a non-connectable device over BLE,
        pairing is impossible (link-layer restrictions apply). Returns a
        structured failure Observation â€” env unchanged."""
        env = build_scenario("home", seed=42)
        from simulator.simulator import action_ble_gatt_pair
        b = _device(env, HOME_BLE_NON_CONNECTABLE)
        assert b is not None and b.connectable is False
        obs = action_ble_gatt_pair(env, {"address": HOME_BLE_NON_CONNECTABLE})
        assert obs.entities == []
        assert "not connectable" in obs.summary.lower()
        assert b.paired is False
        assert all("ble_paired:" not in k for k in env.notes)

    def test_pair_on_unconnected_target_returns_structured_failure(self):
        """Per-target prereq: ble.discovery.connect must have run on THIS
        address first. A fresh lab env (b.connected=False) means pairing
        is refused with a structured Observation â€” no env mutation."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_pair
        b = _device(env, LAB_BLE_TARGET)
        assert b.connected is False
        obs = action_ble_gatt_pair(env, {"address": LAB_BLE_TARGET})
        assert obs.entities == []
        assert "not connected" in obs.summary.lower()
        assert "ble.discovery.connect first" in obs.summary
        assert b.paired is False
        assert all("ble_paired:" not in k for k in env.notes)

    def test_pair_after_connect_succeeds_and_mutates_state(self):
        """The happy path: link-layer connect (Phase 2.7) establishes
        b.connected=True; ble.gatt.pair then mutates b.paired=True and
        inits b.secure_characteristics. The env.notes prefix
        `ble_paired:<addr>` is stamped so performed_capability_keys
        reports the new cap."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_pair
        # Phase 2.7 link connect first â€” directly mutate entity state to
        # the post-connect state the legacy handler produces.
        b = _device(env, LAB_BLE_TARGET)
        b.connected = True
        b.gatt_services = list(b.advertised_services) + ["generic_access"]
        b.characteristics = {svc: "" for svc in b.gatt_services}
        # Now pair
        obs = action_ble_gatt_pair(env, {"address": LAB_BLE_TARGET})
        assert obs.capability == "ble.gatt"
        assert obs.action == "pair"
        assert len(obs.entities) == 1
        ent = obs.entities[0]
        assert ent.id == LAB_BLE_TARGET
        assert ent.attributes["paired"] is True
        assert ent.attributes["secure_characteristics"] == {
            svc: "" for svc in b.gatt_services
        }
        assert b.paired is True
        assert set(b.secure_characteristics.keys()) == set(b.gatt_services)
        assert f"ble_paired:{LAB_BLE_TARGET}" in env.notes

    def test_pair_is_idempotent_for_repeat_calls(self):
        """Repeated pair calls on an already-paired device succeed without
        crashing and refresh env.notes (no error)."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_pair
        b = _device(env, LAB_BLE_TARGET)
        b.connected = True
        b.gatt_services = list(b.advertised_services) + ["generic_access"]
        b.characteristics = {svc: "" for svc in b.gatt_services}
        obs1 = action_ble_gatt_pair(env, {"address": LAB_BLE_TARGET})
        assert obs1.entities
        snapshot = dict(b.secure_characteristics)
        obs2 = action_ble_gatt_pair(env, {"address": LAB_BLE_TARGET})
        assert obs2.entities
        # Pairing again doesn't wipe the secure_characteristics table we
        # already accumulated (handler reinitializes to empty strings â€”
        # mirror of Phase 2.7's connect reinitializing characteristics).
        # The important invariant: the env note stays present.
        assert f"ble_paired:{LAB_BLE_TARGET}" in env.notes


# â”€â”€ 3. action_ble_gatt_write handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestGattWriteHandler:

    def test_missing_address_returns_structured_failure_no_mutation(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write
        obs = action_ble_gatt_write(env, {})
        assert obs.entities == []
        assert "address" in obs.summary.lower() and "aborted" in obs.summary.lower()
        assert all("ble_secure_write:" not in k for k in env.notes)

    def test_missing_characteristic_returns_structured_failure(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write
        obs = action_ble_gatt_write(env, {"address": LAB_BLE_TARGET, "value": "v"})
        assert obs.entities == []
        assert "characteristic" in obs.summary.lower() and "aborted" in obs.summary.lower()

    def test_missing_value_returns_structured_failure(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write
        obs = action_ble_gatt_write(env, {"address": LAB_BLE_TARGET,
                                          "characteristic": "battery"})
        assert obs.entities == []
        assert "value" in obs.summary.lower() and "aborted" in obs.summary.lower()

    def test_non_string_characteristic_returns_structured_failure(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write
        obs = action_ble_gatt_write(env, {"address": LAB_BLE_TARGET,
                                          "characteristic": 12345,
                                          "value": "v"})
        assert obs.entities == []
        assert "characteristic" in obs.summary.lower() and "aborted" in obs.summary.lower()

    def test_unknown_address_returns_structured_failure(self):
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write
        obs = action_ble_gatt_write(env, {"address": "DE:AD:BE:EF:00:99",
                                          "characteristic": "battery",
                                          "value": "v"})
        assert obs.entities == []
        assert "No BLE device found" in obs.summary

    def test_write_to_unpaired_target_returns_structured_failure(self):
        """Per-target prereq: ble.gatt.pair must have run on THIS address
        first. A connected-but-not-paired device refuses ble.gatt.write
        with a structured Observation and no env mutation."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write
        b = _device(env, LAB_BLE_TARGET)
        b.connected = True
        b.paired = False
        obs = action_ble_gatt_write(env, {"address": LAB_BLE_TARGET,
                                          "characteristic": "battery",
                                          "value": "v"})
        assert obs.entities == []
        assert "not paired" in obs.summary.lower()
        assert "ble.gatt.pair first" in obs.summary
        assert all("ble_secure_write:" not in k for k in env.notes)

    def test_write_unknown_characteristic_returns_structured_failure(self):
        """Even when paired, writing to a characteristic the GATT service
        table does not contain is refused with a structured Observation."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write
        b = _device(env, LAB_BLE_TARGET)
        b.connected = True
        b.gatt_services = ["battery", "device_info"]
        b.characteristics = {svc: "" for svc in b.gatt_services}
        b.paired = True
        b.secure_characteristics = {svc: "" for svc in b.gatt_services}
        obs = action_ble_gatt_write(env, {"address": LAB_BLE_TARGET,
                                          "characteristic": "no_such_service",
                                          "value": "v"})
        assert obs.entities == []
        assert "Unknown characteristic" in obs.summary
        assert "no_such_service" in obs.summary
        assert all("ble_secure_write:" not in k for k in env.notes)

    def test_write_after_pair_succeeds_and_mutates_state(self):
        """The happy path: connect (link) -> pair (session) -> secure write.
        b.secure_characteristics[char] is set to str(value); env.notes
        `ble_secure_write:<addr>:<char>` is stamped; performed_capability_keys
        reports the new cap."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write, action_ble_gatt_pair
        b = _device(env, LAB_BLE_TARGET)
        b.connected = True
        b.gatt_services = list(b.advertised_services) + ["generic_access"]
        b.characteristics = {svc: "" for svc in b.gatt_services}
        action_ble_gatt_pair(env, {"address": LAB_BLE_TARGET})
        assert b.paired is True
        obs = action_ble_gatt_write(env, {"address": LAB_BLE_TARGET,
                                          "characteristic": "battery",
                                          "value": "encrypted:0xABCD"})
        assert obs.capability == "ble.gatt"
        assert obs.action == "write"
        assert len(obs.entities) == 1
        ent = obs.entities[0]
        assert ent.attributes["secure_characteristics"]["battery"] == "encrypted:0xABCD"
        assert b.secure_characteristics["battery"] == "encrypted:0xABCD"
        assert f"ble_secure_write:{LAB_BLE_TARGET}:battery" in env.notes

    def test_value_is_stringified_like_phase27_legacy_write(self):
        """Mirror Phase 2.7's ble.discovery.write semantics: any non-None
        value is stored as str(value), so an integer becomes '42'."""
        env = build_scenario("lab", seed=42)
        from simulator.simulator import action_ble_gatt_write, action_ble_gatt_pair
        b = _device(env, LAB_BLE_TARGET)
        b.connected = True
        b.gatt_services = ["battery"]
        b.characteristics = {"battery": ""}
        action_ble_gatt_pair(env, {"address": LAB_BLE_TARGET})
        action_ble_gatt_write(env, {"address": LAB_BLE_TARGET,
                                    "characteristic": "battery", "value": 42})
        assert b.secure_characteristics["battery"] == "42"


# â”€â”€ 4. ble.gatt.pair authorization gate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPairAuthorizationGate:
    def test_pair_rejected_under_passive_scope_env_unchanged(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            cap = engine.registry.capability("ble.gatt", "pair")
            assert cap is not None
            assert cap.mutates_state is True
            assert cap.risk == ActionRisk.SAFE_ACTIVE
            record = engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SAFE_ACTIVE" in record.policy_decision.reasons[0]
            # Provider never ran -> env untouched.
            assert performed_capability_keys(env) == set()
            assert all(not b.paired for b in env.ble)
            assert all(f"ble_paired:{b.address}" not in env.notes for b in env.ble)
            # Authoritative risk still resolved (Phase 2.6 invariant).
            assert record.authoritative_risk == ActionRisk.SAFE_ACTIVE
        finally:
            logger.close()

    def test_pair_allows_under_safe_active_scope_after_connect(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            # Prereq: legacy ble.discovery.connect (SAFE_ACTIVE â€” same scope).
            rec_c = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert rec_c.policy_decision.kind == PolicyDecisionKind.ALLOW
            # Now pair â€” SAFE_ACTIVE, same tier, so ALLOW.
            rec_p = engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert rec_p.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec_p.observation is not None
            assert len(rec_p.observation.entities) == 1
            b = _device(env, LAB_BLE_TARGET)
            assert b.paired is True
            assert f"ble_paired:{LAB_BLE_TARGET}" in env.notes
        finally:
            logger.close()

    def test_pair_caller_downgrade_rejected_by_risk_rule(self):
        """request.risk=PASSIVE but cap.risk=SAFE_ACTIVE â€” caller
        self-disclosed a lower tier than the authoritative one. The
        RiskDeclarationRule rejects the mismatch."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.PASSIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert all(not b.paired for b in env.ble)
        finally:
            logger.close()

    def test_pair_caller_upgrade_rejected_by_risk_rule(self):
        """request.risk=SENSITIVE_ACTIVE but cap.risk=SAFE_ACTIVE â€” caller
        self-disclosed a higher tier than the authoritative one. The
        RiskDeclarationRule rejects the mismatch."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert all(not b.paired for b in env.ble)
        finally:
            logger.close()


# â”€â”€ 5. ble.gatt.write authorization gate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestGattWriteAuthorizationGate:
    def test_write_rejected_under_passive_scope_env_unchanged(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            record = engine.execute(
                ActionRequest(capability="ble.gatt", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_BLE_TARGET,
                                    "characteristic": "battery", "value": "v"})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SENSITIVE_ACTIVE" in record.policy_decision.reasons[0]
            assert performed_capability_keys(env) == set()
            assert all("ble_secure_write:" not in k for k in env.notes)
            assert record.authoritative_risk == ActionRisk.SENSITIVE_ACTIVE
        finally:
            logger.close()

    def test_write_rejected_under_safe_active_scope_at_tier_gate(self):
        """SAFE_ACTIVE scope does NOT include SENSITIVE_ACTIVE, so the
        secure write REJECTs at the tier gate even though connect+pair
        might ALLOW under the same scope (cumulative stops at SAFE_ACTIVE)."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            # connect ALLOWs...
            rec_c = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert rec_c.policy_decision.kind == PolicyDecisionKind.ALLOW
            # pair ALLOWs...
            rec_p = engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert rec_p.policy_decision.kind == PolicyDecisionKind.ALLOW
            # ...but ble.gatt.write REJECTs at the tier gate.
            rec_w = engine.execute(
                ActionRequest(capability="ble.gatt", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_BLE_TARGET,
                                    "characteristic": "battery", "value": "v"})
            )
            assert rec_w.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SENSITIVE_ACTIVE" in rec_w.policy_decision.reasons[0]
            # connect+pair mutated env; write did NOT.
            b = _device(env, LAB_BLE_TARGET)
            assert b.connected is True
            assert b.paired is True
            assert b.secure_characteristics.get("battery") in (None, "")
            assert all("ble_secure_write:" not in k for k in env.notes)
        finally:
            logger.close()

    def test_write_allows_under_sensitive_active_scope_after_pair(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            # Prereq chain: connect (Phase 2.7 SAFE_ACTIVE) + pair (NEW SAFE_ACTIVE).
            engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            # ble.gatt.write ALLOWs.
            rec = engine.execute(
                ActionRequest(capability="ble.gatt", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_BLE_TARGET,
                                    "characteristic": "battery",
                                    "value": "enc:0xABCD"})
            )
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(rec.observation.entities) == 1
            b = _device(env, LAB_BLE_TARGET)
            assert b.secure_characteristics["battery"] == "enc:0xABCD"
            assert f"ble_secure_write:{LAB_BLE_TARGET}:battery" in env.notes
        finally:
            logger.close()

    def test_write_caller_downgrade_rejected_by_risk_rule(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            record = engine.execute(
                ActionRequest(capability="ble.gatt", action="write",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET,
                                    "characteristic": "battery", "value": "v"})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert all("ble_secure_write:" not in k for k in env.notes)
        finally:
            logger.close()


# â”€â”€ 6. Policy reject does not mutate env (Phase 2.7.1 invariant) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPolicyRejectDoesNotMutateState:
    """Phase 2.7.1 spec: 'Policy must remain before execution. Rejected
    actions must not mutate simulator state.' Combined with the new
    ble.gattPair/Write `mutates_state=True` catalogue flags, this proves the
    catalogue + policy + simulator all agree on the state guard."""

    def test_pair_rejected_under_passive_scope_leaves_env_clean(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            cap = engine.registry.capability("ble.gatt", "pair")
            assert cap.mutates_state is True
            record = engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert performed_capability_keys(env) == set()
            assert all(not b.paired for b in env.ble)
        finally:
            logger.close()

    def test_write_rejected_leaves_secure_characteristics_untouched(self):
        """Under SAFE_ACTIVE scope, connect+pair ALLOW but ble.gatt.write
        REJECTs at the tier gate. The connect+pair mutated env (paired=True,
        secure_characteristics initialized to empty strings) â€” but the
        REJECTED write leaves b.secure_characteristics at its post-pair
        state (all empty strings, no writes recorded). performed_capability_keys
        does NOT gain 'ble.gatt.write'."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_BLE_TARGET})
            )
            snapshot = dict(_device(env, LAB_BLE_TARGET).secure_characteristics)
            performed = performed_capability_keys(env)
            assert "ble.discovery.connect" in performed
            assert "ble.gatt.pair" in performed
            assert "ble.gatt.write" not in performed
            # Now attempt the rejected write.
            record = engine.execute(
                ActionRequest(capability="ble.gatt", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_BLE_TARGET,
                                    "characteristic": "battery", "value": "x"})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            # performed set is unchanged.
            assert performed_capability_keys(env) == performed
            assert "ble.gatt.write" not in performed_capability_keys(env)
            # Entity state for the rejected cap's mutation is unchanged.
            assert _device(env, LAB_BLE_TARGET).secure_characteristics == snapshot
        finally:
            logger.close()


# â”€â”€ 7. ble_gatt_workflow_plan end-to-end shape + state reflection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBleGattWorkflowPlan:

    def test_plan_shape_risks_match_catalogue(self):
        plan = ble_gatt_workflow_plan()
        assert len(plan) == 6
        reg = default_registry(environment=build_scenario("lab", seed=42))
        for req in plan:
            cap = reg.capability(req.capability, req.action)
            assert cap is not None, f"unknown cap {req.capability}.{req.action}"
            assert req.risk == cap.risk, f"{req.capability}.{req.action}"
        risks = [(p.capability, p.action, p.risk) for p in plan]
        # Phase 2.7 + 2.7.3 layers
        assert ("ble.discovery", "discover", ActionRisk.PASSIVE) in risks
        assert ("ble.discovery", "inspect",  ActionRisk.PASSIVE) in risks
        assert ("ble.discovery", "connect",  ActionRisk.SAFE_ACTIVE) in risks
        assert ("ble.gatt",      "pair",     ActionRisk.SAFE_ACTIVE) in risks
        assert ("ble.gatt",      "write",    ActionRisk.SENSITIVE_ACTIVE) in risks
        # Two inspect actions (initial + final) â€” observe -> test -> observe loop.
        assert sum(1 for p in plan
                   if p.capability == "ble.discovery" and p.action == "inspect") == 2

    def test_plan_completes_under_sensitive_active_scope(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ble_gatt_workflow_plan())
            assert run.status == RunStatus.COMPLETED
            b = _device(env, LAB_BLE_TARGET)
            assert b.connected is True
            assert b.paired is True
            assert b.secure_characteristics["battery"] == "encrypted:0xABCD"
            performed = performed_capability_keys(env)
            assert "ble.discovery.connect" in performed
            assert "ble.gatt.pair" in performed
            assert "ble.gatt.write" in performed
        finally:
            logger.close()

    def test_plan_under_passive_scope_records_rejections_and_completes(self):
        """Under a PASSIVE-only default scope, all three active steps (connect,
        pair, write) are REJECTed at the policy gate but the run still
        COMPLETED (rejections are valid runs). discover/inspect ALLOW. env
        unchanged. The plan exercises 6 actions total."""
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.run_plan(ble_gatt_workflow_plan())
            assert run.status == RunStatus.COMPLETED
            # 3 active actions were all rejected at the policy gate.
            rejected = [r for r in run.actions
                       if r.policy_decision.kind == PolicyDecisionKind.REJECT]
            assert len(rejected) == 3
            rejected_keys = {(r.request.capability, r.request.action)
                             for r in rejected}
            assert rejected_keys == {("ble.discovery", "connect"),
                                     ("ble.gatt", "pair"),
                                     ("ble.gatt", "write")}
            b = _device(env, LAB_BLE_TARGET)
            assert b.connected is False
            assert b.paired is False
            assert b.secure_characteristics == {}
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()

    def test_plan_under_safe_active_scope_connect_and_pair_allow_write_rejects(self):
        """The cumulative tier boundary is observed precisely: SAFE_ACTIVE
        scope permits connect + pair (both SAFE_ACTIVE) but stops at the
        SENSITIVE_ACTIVE ble.gatt.write â€” proving the tier gate is binary
        and not 'best-case' across the plan."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(ble_gatt_workflow_plan())
            assert run.status == RunStatus.COMPLETED
            allows = [r for r in run.actions
                      if r.policy_decision.kind == PolicyDecisionKind.ALLOW]
            rejects = [r for r in run.actions
                      if r.policy_decision.kind == PolicyDecisionKind.REJECT]
            # 5 ALLOWs: discover, inspect, connect, pair, inspect (final).
            assert len(allows) == 5
            assert len(rejects) == 1
            assert (rejects[0].request.capability,
                    rejects[0].request.action) == ("ble.gatt", "write")
            # connect + pair mutated; write did NOT.
            b = _device(env, LAB_BLE_TARGET)
            assert b.connected is True
            assert b.paired is True
            assert b.secure_characteristics.get("battery") in (None, "")
            performed = performed_capability_keys(env)
            assert "ble.discovery.connect" in performed
            assert "ble.gatt.pair" in performed
            assert "ble.gatt.write" not in performed
        finally:
            logger.close()

    def test_plan_writes_events_jsonl_to_disk(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ble_gatt_workflow_plan())
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


# â”€â”€ 8. State reflection â€” inspect summary differs before/after GATT chain â”€â”€â”€â”€â”€

class TestInspectReflectsStateChange:
    def test_initial_inspect_summary_differs_from_final_after_gatt_chain(self):
        """Run the full chain: discover -> inspect (initial) -> connect ->
        pair -> ble.gatt.write -> inspect (final). The two ble.discovery.inspect
        Observations differ: the first sees `paired=False` and no secure
        characteristic writes; the final sees `paired=True` and a populated
        `secure_characteristics["battery"]`."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            # Initial inspect of the lab target.
            rec_initial = engine.execute(
                ActionRequest(capability="ble.discovery", action="inspect",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.PASSIVE)
            )
            assert rec_initial.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(rec_initial.observation.entities) == 1
            attrs_initial = rec_initial.observation.entities[0].attributes
            assert attrs_initial["connected"] is False
            assert attrs_initial["paired"] is False
            assert attrs_initial["secure_characteristics"] == {}
            # Run the GATT chain.
            engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            engine.execute(
                ActionRequest(capability="ble.gatt", action="write",
                              args={"address": LAB_BLE_TARGET,
                                    "characteristic": "battery",
                                    "value": "encrypted:0xABCD"},
                              risk=ActionRisk.SENSITIVE_ACTIVE)
            )
            # Final inspect.
            rec_final = engine.execute(
                ActionRequest(capability="ble.discovery", action="inspect",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.PASSIVE)
            )
            assert rec_final.policy_decision.kind == PolicyDecisionKind.ALLOW
            attrs_final = rec_final.observation.entities[0].attributes
            assert attrs_final["connected"] is True
            assert attrs_final["paired"] is True
            assert attrs_final["secure_characteristics"]["battery"] == "encrypted:0xABCD"
            # The summary strings differ â€” state mutated visibly, so the
            # final summary mentions pairing + the secure write.
            assert rec_final.observation.summary != rec_initial.observation.summary
            assert "paired" in rec_final.observation.summary
            assert "1 secure characteristic(s) written" in rec_final.observation.summary
        finally:
            logger.close()


# â”€â”€ 9. Determinism â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDeterminism:
    def _gatt_obs_for_seed(self, seed: int) -> tuple[Observation, Observation]:
        engine, run, logger, env = _engine_with_scope(
            _sensitive_active_scope(), seed=seed)
        try:
            rec_c = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            rec_p = engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            rec_w = engine.execute(
                ActionRequest(capability="ble.gatt", action="write",
                              args={"address": LAB_BLE_TARGET,
                                    "characteristic": "battery",
                                    "value": "encrypted:0xABCD"},
                              risk=ActionRisk.SENSITIVE_ACTIVE)
            )
            return rec_p.observation, rec_w.observation
        finally:
            logger.close()

    def test_same_seed_yields_identical_observations(self):
        obs_p_1, obs_w_1 = self._gatt_obs_for_seed(7)
        obs_p_2, obs_w_2 = self._gatt_obs_for_seed(7)
        assert obs_p_1.summary == obs_p_2.summary
        assert obs_w_1.summary == obs_w_2.summary
        a_p1 = obs_p_1.entities[0].attributes
        a_p2 = obs_p_2.entities[0].attributes
        assert a_p1["paired"] == a_p2["paired"]
        assert a_p1["secure_characteristics"] == a_p2["secure_characteristics"]
        a_w1 = obs_w_1.entities[0].attributes
        a_w2 = obs_w_2.entities[0].attributes
        assert a_w1["secure_characteristics"] == a_w2["secure_characteristics"]

    def test_two_full_runs_with_same_seed_produce_identical_summaries(self):
        def run_once():
            engine, run, logger, env = _engine_with_scope(
                _sensitive_active_scope(), seed=42)
            try:
                engine.run_plan(ble_gatt_workflow_plan())
                return [a.observation.summary if a.observation else None
                        for a in run.actions]
            finally:
                logger.close()
        s1 = run_once()
        s2 = run_once()
        assert s1 == s2


# â”€â”€ 10. Phase 2.7.1 contract metadata consumption via performed set â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestContractMetadataConsumption:
    def test_both_new_caps_marked_mutates_state_in_catalogue(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["ble.gatt.pair"].mutates_state is True
        assert by_key["ble.gatt.write"].mutates_state is True

    def test_pair_prerequisites_met_flips_after_connect(self):
        """ble.gatt.pair declares requires=('ble.discovery.connect',).
        In a fresh lab env, prerequisites_met is False; after
        ble.discovery.connect runs, performed_capability_keys gains
        'ble.discovery.connect' and the prereq is satisfied."""
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            cap_pair = engine.registry.capability("ble.gatt", "pair")
            assert cap_pair.requires == ("ble.discovery.connect",)
            assert cap_pair.prerequisites_met(performed_capability_keys(env)) is False
            engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            performed = performed_capability_keys(env)
            assert "ble.discovery.connect" in performed
            assert cap_pair.prerequisites_met(performed) is True
        finally:
            logger.close()

    def test_gatt_write_prerequisites_met_flips_after_pair(self):
        """ble.gatt.write declares requires=('ble.gatt.pair',). After the
        full connect + pair chain, performed_capability_keys contains
        'ble.gatt.pair' and the write's prereq is satisfied."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            cap_write = engine.registry.capability("ble.gatt", "write")
            assert cap_write.requires == ("ble.gatt.pair",)
            assert cap_write.prerequisites_met(performed_capability_keys(env)) is False
            engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            assert cap_write.prerequisites_met(performed_capability_keys(env)) is False
            engine.execute(
                ActionRequest(capability="ble.gatt", action="pair",
                              args={"address": LAB_BLE_TARGET},
                              risk=ActionRisk.SAFE_ACTIVE)
            )
            performed = performed_capability_keys(env)
            assert "ble.gatt.pair" in performed
            assert cap_write.prerequisites_met(performed) is True
        finally:
            logger.close()


# â”€â”€ 11. Regression: Phase 2 / 2.5 / 2.6 / 2.7 / 2.7.1 / 2.7.2 unaffected â”€â”€â”€â”€â”€â”€

class TestRegression:
    def test_phase2_default_plan_unchanged(self):
        plan = default_exploration_plan()
        assert len(plan) == 4
        assert all(p.risk == ActionRisk.PASSIVE for p in plan)

    def test_active_inspection_plan_unchanged(self):
        """Phase 2.7 active_inspection_plan is intact â€” the workflow added
        in this subphase lives ALONGSIDE it as a separate plan, not as a
        modification."""
        plan = active_inspection_plan()
        assert len(plan) == 5
        # No ble.gatt.* in the Phase 2.7 plan â€” adds are confined to the
        # new ble_gatt_workflow_plan.
        assert all(p.capability != "ble.gatt" for p in plan)

    def test_wifi_capture_plan_unchanged(self):
        """Phase 2.7.2 wifi_capture_plan is intact â€” the workflow added in
        this subphase lives ALONGSIDE it, not as a modification."""
        plan = wifi_capture_plan()
        assert len(plan) == 5
        assert all(p.capability != "ble.gatt" for p in plan)

    def test_catalogue_count_and_risks(self):
        by_key = {c.key: c.risk for c in DEFAULT_CAPABILITIES}
        assert len(DEFAULT_CAPABILITIES) == 26
        # Phase 2.7.3 additions present, with prescribed risks.
        assert by_key["ble.gatt.pair"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.gatt.write"] == ActionRisk.SENSITIVE_ACTIVE
        # Existing entries' risks unchanged.
        assert by_key["ble.discovery.connect"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.discovery.write"] == ActionRisk.SENSITIVE_ACTIVE
        assert by_key["wifi.capture.handshake"] == ActionRisk.SAFE_ACTIVE
        assert by_key["wifi.capture.pmkid"] == ActionRisk.SENSITIVE_ACTIVE

    def test_ble_device_new_fields_default_safely(self):
        """Sanity: BleDevice still constructs with original positional args
        (Phase 2.7.1 back-compat extends to the Phase 2.7.3 additions)."""
        b = BleDevice(address="AA:BB:CC:00:00:01", name="x", rssi=-50)
        d = b.to_dict()
        assert d["paired"] is False
        assert d["secure_characteristics"] == {}

    def test_existing_passive_actions_still_allow_under_default_scope(self):
        """The four original PASSIVE discovery actions + Phase 2.7 BLE
        inspect still ALLOW under the default PASSIVE-only scope."""
        engine, run, logger, env = _engine_with_scope()
        try:
            for cap, action in [("wifi.discovery", "discover"),
                                ("ble.discovery", "discover"),
                                ("nfc.discovery", "scan"),
                                ("subghz.discovery", "spectrum"),
                                ("ble.discovery", "inspect")]:
                record = engine.execute(
                    ActionRequest(capability=cap, action=action,
                                  risk=ActionRisk.PASSIVE,
                                  args={"address": LAB_BLE_TARGET}
                                  if action == "inspect" else {})
                )
                assert record.policy_decision.kind == PolicyDecisionKind.ALLOW, \
                    f"{cap}.{action} should ALLOW; got REJECT"
        finally:
            logger.close()


# â”€â”€ 12. New env-notes prefixes map to the new capability keys â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPerformedCapabilityKeysExtended:
    def test_pair_and_write_note_prefixes_recognized(self):
        env = Environment(name="t")
        env.notes["ble_paired:AA:BB:CC:00:00:01"] = 0
        env.notes["ble_secure_write:AA:BB:CC:00:00:01:battery"] = 0
        performed = performed_capability_keys(env)
        assert "ble.gatt.pair" in performed
        assert "ble.gatt.write" in performed

    def test_full_gatt_chain_produces_full_performed_set(self):
        """Run the ble_gatt_workflow_plan under SENSITIVE_ACTIVE scope and
        confirm performed_capability_keys reports the full active chain â€”
        the Old Phase 2.7 connect/write keys AND the Phase 2.7.3 gatt.pair/
        gatt.write keys."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ble_gatt_workflow_plan())
            performed = performed_capability_keys(env)
            assert performed == {
                "ble.discovery.connect",
                "ble.gatt.pair",
                "ble.gatt.write",
            }
        finally:
            logger.close()


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p273-"))
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
