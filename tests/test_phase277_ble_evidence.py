"""
tests/test_phase277_ble_evidence.py

Phase 2.7.7 regression suite â€” generalize the evidence pipeline to the
BLE GATT workflow: `ble.gatt.pair` (kind `ble_pairing`) and
`ble.gatt.write` (kind `ble_secure_write`).

Proves the 2.7.5/2.7.6 EvidenceRecord pipeline generalizes ACROSS domains
(Wi-Fi capture -> BLE GATT session ops) with no second evidence system and
no pipeline redesign â€” the handlers build EvidenceRecords, the engine
mirrors them, and JSONL/HTML render them identically. The per-target
prerequisites (pair needs connect on the SAME address, secure write needs
pair on the SAME address) remain the simulator's gate, so pairing evidence
only exists after successful pairing and secure-write evidence only exists
after the pairing prerequisite is satisfied. Wi-Fi handshake + PMKID
evidence behavior is unchanged.

Run without pytest:
    python -m tests.test_phase277_ble_evidence
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
from core.events import EVIDENCE_CREATED
from core.mission import (
    ActionRequest,
    ActionRisk,
    AuthorizationScope,
    PolicyDecisionKind,
    Run,
    RunStatus,
)
from engine.logger import RunLogger
from engine.runner import (
    RunEngine,
    ble_gatt_workflow_plan,
    default_exploration_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import render_run
from simulator.scenarios import build_scenario


# Lab scenario literal BLE addresses (seed-independent).
LAB_BLE = "AA:BB:CC:00:00:01"          # Suryafool-BLE-Target, connectable
LAB_BLE_CHAR = "battery"               # advertised service, valid after connect
# Lab scenario literal Wi-Fi bssids (for the mixed BLE+Wi-Fi coexistence test).
LAB_WIFI_WPA3 = "02:00:00:00:00:01"


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _sensitive_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.7.7 ble evidence test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _connect_action() -> ActionRequest:
    return ActionRequest(
        capability="ble.discovery", action="connect",
        args={"address": LAB_BLE}, risk=ActionRisk.SAFE_ACTIVE,
    )


def _pair_action() -> ActionRequest:
    return ActionRequest(
        capability="ble.gatt", action="pair",
        args={"address": LAB_BLE}, risk=ActionRisk.SAFE_ACTIVE,
    )


def _write_action(value="encrypted:0xABCD") -> ActionRequest:
    return ActionRequest(
        capability="ble.gatt", action="write",
        args={"address": LAB_BLE, "characteristic": LAB_BLE_CHAR, "value": value},
        risk=ActionRisk.SENSITIVE_ACTIVE,
    )


def _run_connect_pair_write(engine):
    """Execute the full prerequisite chain through the engine under a
    SENSITIVE_ACTIVE scope. Returns (connect_rec, pair_rec, write_rec)."""
    c = engine.execute(_connect_action())
    p = engine.execute(_pair_action())
    w = engine.execute(_write_action())
    return c, p, w


# â”€â”€ 1/2. Successful pair + success write produce exactly one evidence each â”€â”€â”€â”€

class TestSuccessfulEvidence:
    def test_pair_produces_exactly_one_ble_pairing_record(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            c, p, w = _run_connect_pair_write(engine)
            assert p.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(p.observation.evidence) == 1
            assert len(p.evidence) == 1
            assert p.observation.evidence[0].kind == "ble_pairing"
        finally:
            logger.close()

    def test_write_produces_exactly_one_ble_secure_write_record(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            c, p, w = _run_connect_pair_write(engine)
            assert w.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(w.observation.evidence) == 1
            assert len(w.evidence) == 1
            assert w.observation.evidence[0].kind == "ble_secure_write"
        finally:
            logger.close()

    def test_both_kinds_are_in_known_vocabulary(self):
        from core.evidence import KNOWN_EVIDENCE_KINDS
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _, p, w = _run_connect_pair_write(engine)
            assert {e.kind for e in p.observation.evidence} <= KNOWN_EVIDENCE_KINDS
            assert {e.kind for e in w.observation.evidence} <= KNOWN_EVIDENCE_KINDS
        finally:
            logger.close()


# â”€â”€ 3. Provenance fields are correct â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestProvenance:
    def test_pairing_provenance(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_connect_action())
            pair_req = _pair_action()
            rec = engine.execute(pair_req)
            ev = rec.observation.evidence[0]
            assert ev.source_action_id == pair_req.id
            assert ev.source_capability == "ble.gatt"
            assert ev.source_action == "pair"
            assert ev.target_entity_id == LAB_BLE
            assert ev.target_entity_type == "ble_device"
            assert ev.captured_at > 0
            assert ev.summary
            assert ev.metadata["address"] == LAB_BLE
            assert ev.metadata["secure_service_count"] >= 1
        finally:
            logger.close()

    def test_secure_write_provenance(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
            write_req = _write_action()
            rec = engine.execute(write_req)
            ev = rec.observation.evidence[0]
            assert ev.source_action_id == write_req.id
            assert ev.source_capability == "ble.gatt"
            assert ev.source_action == "write"
            assert ev.target_entity_id == LAB_BLE
            assert ev.target_entity_type == "ble_device"
            assert ev.kind == "ble_secure_write"
            assert ev.metadata["characteristic"] == LAB_BLE_CHAR
            assert ev.metadata["address"] == LAB_BLE
        finally:
            logger.close()

    def test_evidence_distinct_from_finding(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _, p, _ = _run_connect_pair_write(engine)
            ev = p.observation.evidence[0]
            assert "source_action_id" in ev.to_dict()
            assert "source_action_id" not in run.findings[0]
        finally:
            logger.close()


# â”€â”€ 4. Prerequisites are enforced â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPrerequisites:
    def test_pair_without_connect_produces_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(_pair_action())
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec.observation is not None
            assert "is not connected" in rec.observation.summary
            assert rec.observation.entities == []
            assert rec.observation.evidence == []
            assert len(rec.evidence) == 0
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_write_without_pair_produces_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_connect_action())
            rec = engine.execute(_write_action())
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert "is not paired" in rec.observation.summary
            assert rec.observation.evidence == []
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_write_after_pairing_on_same_address_succeeds(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _, p, w = _run_connect_pair_write(engine)
            assert p.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert w.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(w.observation.evidence) == 1
        finally:
            logger.close()


# â”€â”€ 5. Failed or rejected operations create zero evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestFailedRejectedZeroEvidence:
    def test_invalid_address_argument_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(ActionRequest(
                capability="ble.gatt", action="pair",
                args={"address": ""}, risk=ActionRisk.SAFE_ACTIVE,
            ))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert "Invalid or missing" in rec.observation.summary
            assert rec.observation.evidence == []
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_unknown_address_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(ActionRequest(
                capability="ble.gatt", action="pair",
                args={"address": "FF:FF:FF:00:00:99"}, risk=ActionRisk.SAFE_ACTIVE,
            ))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert "No BLE device found" in rec.observation.summary
            assert rec.observation.evidence == []
        finally:
            logger.close()

    def test_missing_write_arg_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
            before = len(run.evidence)
            rec = engine.execute(ActionRequest(
                capability="ble.gatt", action="write",
                args={"address": LAB_BLE, "characteristic": LAB_BLE_CHAR},
                risk=ActionRisk.SENSITIVE_ACTIVE,
            ))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert "Missing 'value'" in rec.observation.summary
            assert rec.observation.evidence == []
            assert len(run.evidence) == before  # no extra evidence
        finally:
            logger.close()

    def test_unknown_characteristic_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
            rec = engine.execute(ActionRequest(
                capability="ble.gatt", action="write",
                args={"address": LAB_BLE, "characteristic": "nope", "value": "x"},
                risk=ActionRisk.SENSITIVE_ACTIVE,
            ))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert "Unknown characteristic" in rec.observation.summary
            assert rec.observation.evidence == []
            assert len(run.evidence) == 2  # pair + write from the chain only
        finally:
            logger.close()

    def test_policy_rejections_produce_no_evidence(self):
        # pair is SAFE_ACTIVE, secure write is SENSITIVE_ACTIVE. Under a
        # PASSIVE-only scope both are REJECTed before the provider runs.
        engine, run, logger, env = _engine_with_scope()
        try:
            rec_pair = engine.execute(_pair_action())
            rec_write = engine.execute(_write_action())
            assert rec_pair.policy_decision.kind == PolicyDecisionKind.REJECT
            assert rec_write.policy_decision.kind == PolicyDecisionKind.REJECT
            assert rec_pair.observation is None
            assert rec_write.observation is None
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_secure_write_rejected_under_safe_active_scope(self):
        # SENSITIVE_ACTIVE write is REJECTed at the tier gate under a
        # SAFE_ACTIVE-only scope â€” no evidence, even though connect + pair
        # were allowed and mutated env.
        engine, run, logger, env = _engine_with_scope(
            AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE))
        try:
            c = engine.execute(_connect_action())
            p = engine.execute(_pair_action())
            w = engine.execute(_write_action())
            assert c.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert p.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert w.policy_decision.kind == PolicyDecisionKind.REJECT
            # run.evidence has ONLY the pairing record â€” the write contributed none.
            assert len(run.evidence) == 1
            assert run.evidence[0].kind == "ble_pairing"
        finally:
            logger.close()


# â”€â”€ 6. BLE pairing + secure-write evidence coexist in one run â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBleCoexistence:
    def test_both_ble_kinds_in_one_run(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _, p, w = _run_connect_pair_write(engine)
            kinds = sorted(ev.kind for ev in run.evidence)
            assert kinds == ["ble_pairing", "ble_secure_write"]
            assert p.evidence[0].id != w.evidence[0].id
            sources = {(ev.source_capability, ev.source_action) for ev in run.evidence}
            assert sources == {("ble.gatt", "pair"), ("ble.gatt", "write")}
        finally:
            logger.close()

    def test_evolved_state_still_visible_on_later_inspect(self):
        # Phase 2.7.3 inspection behavior is preserved: after pair + write the
        # inspect summary surfaces "paired; 1 secure characteristic(s) written".
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
            ins = engine.execute(ActionRequest(
                capability="ble.discovery", action="inspect",
                args={"address": LAB_BLE}, risk=ActionRisk.PASSIVE,
            ))
            assert ins.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert "paired" in ins.observation.summary
            assert "secure characteristic(s) written" in ins.observation.summary
        finally:
            logger.close()


# â”€â”€ 7. BLE evidence + Wi-Fi evidence coexist in one run â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestCrossDomainCoexistence:
    def test_ble_and_wifi_evidence_in_one_run(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
            engine.execute(ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SAFE_ACTIVE,
            ))
            engine.execute(ActionRequest(
                capability="wifi.capture", action="pmkid",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SENSITIVE_ACTIVE,
            ))
            kinds = sorted(ev.kind for ev in run.evidence)
            assert kinds == [
                "ble_pairing", "ble_secure_write",
                "wifi_eapol_handshake", "wifi_pmkid",
            ]
            assert len(run.evidence) == 4
        finally:
            logger.close()

    def test_wifi_evidence_kinds_unchanged_by_2_7_7(self):
        # Regression: the wifi.capture plan still yields exactly the two
        # wifi evidence kinds, both unchanged.
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(wifi_capture_plan())
            kinds = sorted(ev.kind for ev in run.evidence)
            assert kinds == ["wifi_eapol_handshake", "wifi_pmkid"]
        finally:
            logger.close()


# â”€â”€ 8. Evidence survives run.json round-trip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRunJsonRoundTrip:
    def test_ble_evidence_round_trips(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
            assert len(run.evidence) == 2
        finally:
            logger.close()
        d = run.to_dict()
        run2 = Run.from_dict(json.loads(json.dumps(d, default=str)))
        kinds = sorted(ev.kind for ev in run2.evidence)
        assert kinds == ["ble_pairing", "ble_secure_write"]
        pair_acts = [a for a in run2.actions
                     if a.request.capability == "ble.gatt"
                     and a.request.action == "pair"]
        write_acts = [a for a in run2.actions
                      if a.request.capability == "ble.gatt"
                      and a.request.action == "write"]
        assert len(pair_acts[0].evidence) == 1
        assert pair_acts[0].evidence[0].kind == "ble_pairing"
        assert len(write_acts[0].evidence) == 1
        assert write_acts[0].evidence[0].kind == "ble_secure_write"


# â”€â”€ 9. Deterministic repeatability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDeterminism:
    def _ble_evidence_semantics(self, seed: int) -> dict:
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope(), seed=seed)
        try:
            _run_connect_pair_write(engine)
            out = {}
            for ev in run.evidence:
                out[ev.kind] = {
                    "source_capability": ev.source_capability,
                    "source_action": ev.source_action,
                    "target_entity_id": ev.target_entity_id,
                    "target_entity_type": ev.target_entity_type,
                    "summary": ev.summary,
                    "metadata": ev.metadata,
                }
            return out
        finally:
            logger.close()

    def test_same_seed_yields_stable_ble_evidence_semantics(self):
        a = self._ble_evidence_semantics(7)
        b = self._ble_evidence_semantics(7)
        assert a == b
        assert set(a.keys()) == {"ble_pairing", "ble_secure_write"}

    def test_wifi_evidence_semantics_stable_across_seeds(self):
        # Deterministic across seeds too â€” no RNG dependence in evidence.
        a = self._ble_evidence_semantics(3)["ble_pairing"]
        b = self._ble_evidence_semantics(9)["ble_pairing"]
        assert a["metadata"] == b["metadata"]


# â”€â”€ 10. JSONL + HTML show both BLE evidence kinds â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestJsonlAndHtml:
    def test_two_evidence_created_events_for_ble(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
        finally:
            logger.close()
        from engine.logger import run_dir
        lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
        events = [json.loads(l) for l in lines if l.strip()]
        ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
        kinds = sorted(e["evidence"]["kind"] for e in ev_events)
        assert kinds == ["ble_pairing", "ble_secure_write"]
        for e in ev_events:
            assert e["run_id"] == run.id
            assert e["source_action_id"]

    def test_html_report_shows_both_ble_kinds_and_provenance(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_connect_pair_write(engine)
        finally:
            logger.close()
        html = render_run(run)
        assert "<h2>EVIDENCE</h2>" in html
        assert "Evidence produced:" in html
        assert "ble_pairing" in html
        assert "ble_secure_write" in html
        assert "ble.gatt.pair" in html and "ble.gatt.write" in html
        assert LAB_BLE in html                 # target entity id
        assert "characteristic" in html        # metadata column

    def test_html_report_empty_evidence_for_passive_run(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.run_plan(default_exploration_plan())
        finally:
            logger.close()
        html = render_run(run)
        assert "<h2>EVIDENCE</h2>" in html
        assert "No evidence captured by this run." in html


# â”€â”€ 11/12. Regression: prior suites + Node mirror â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegression:
    def test_catalogue_count_at_21(self):
        # Phase 2.8.0 appended the multi-domain foundation (infrared / ethernet
        # / usb) to the Phase 2.7 catalogue of 14 (→23). Phase 2.8.4 appended
        # the three zigbee.discovery.* entries (→26).
        assert len(DEFAULT_CAPABILITIES) == 26

    def test_only_evidence_capabilities_marked(self):
        # Phase 2.8.2 added nfc.discovery.read; Phase 2.8.3 added
        # infrared.analyze/transmit; Phase 2.8.4 added zigbee.discovery.join.
        # The full 10-producer set is preserved
        # across Phase 2.7.7/2.8.1/2.8.2/2.8.3/2.8.4.
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        evidence_caps = [k for k, c in by_key.items() if c.produces_evidence]
        assert sorted(evidence_caps) == [
            "ble.gatt.pair", "ble.gatt.write",
            "infrared.analyze", "infrared.transmit",
            "nfc.discovery.read",
            "subghz.capture.signal", "subghz.discovery.analyze",
            "wifi.capture.handshake", "wifi.capture.pmkid",
            "zigbee.discovery.join",
        ]

    def test_ble_gatt_plan_unchanged(self):
        plan = ble_gatt_workflow_plan()
        assert len(plan) == 6
        risks = [(p.capability, p.action, p.risk) for p in plan]
        assert ("ble.discovery", "connect", ActionRisk.SAFE_ACTIVE) in risks
        assert ("ble.gatt", "pair", ActionRisk.SAFE_ACTIVE) in risks
        assert ("ble.gatt", "write", ActionRisk.SENSITIVE_ACTIVE) in risks

    def test_ble_gatt_plan_full_chain_produces_two_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ble_gatt_workflow_plan())
            assert run.status == RunStatus.COMPLETED
            kinds = sorted(ev.kind for ev in run.evidence)
            assert kinds == ["ble_pairing", "ble_secure_write"]
        finally:
            logger.close()

    def test_node_mirror_has_evidence_constant(self):
        ev_js = Path(__file__).resolve().parent.parent / "suryafool-cli" / "src" / "backend" / "events.js"
        txt = ev_js.read_text(encoding="utf-8")
        assert "EVIDENCE_CREATED: 'evidence.created'" in txt


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p277-"))
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