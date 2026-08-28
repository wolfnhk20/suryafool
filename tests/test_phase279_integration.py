"""
tests/test_phase279_integration.py

Phase 2.7.9 â€” final freeze subphase. Golden-path integration tests that
exercise the COMPLETE deterministic Suryafool stack end-to-end as one
coherent security-assessment platform:

  capability resolution -> authoritative risk -> AuthorizationScope ->
  prerequisites -> simulator execution -> state transition -> observation ->
  evidence creation -> Run/ActionRecord persistence -> run.json / JSONL ->
  HTML report  (TUI feed verified by the suryafool-cli test suite)

Two representative workflows are proved end-to-end (Wi-Fi capture and
BLE GATT), plus negative paths that must leave state AND evidence
consistent, and an explicit CONTRACT AUDIT of every Phase 2.7 interface.

No LLM, no hardware, no new domains/kinds/tiers â€” reuse of the existing
stack only.

Run without pytest:
    python -m tests.test_phase279_integration
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
from core.evidence import EvidenceRecord, KNOWN_EVIDENCE_KINDS
from core.events import AGENT_STATUS, EVIDENCE_CREATED, FINDING_CREATED
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
    ble_gatt_workflow_plan,
    default_exploration_plan,
    ir_workflow_plan,
    nfc_workflow_plan,
    subghz_capture_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import render_run
from simulator.scenarios import build_scenario
from simulator.simulator import performed_capability_keys

# Same-Seed deterministic scenarios use these literal lab targets.
LAB_WIFI_WPA3 = "02:00:00:00:00:01"     # LAB-INTERNAL (WPA3)
LAB_WIFI_WPA2 = "02:00:00:00:00:12"     # HomeNet-2.4G (WPA2, home scenario)
LAB_WIFI_OPEN = "02:00:00:00:00:02"     # non-WPA failure target
LAB_BLE       = "AA:BB:CC:00:00:01"     # Suryafool-BLE-Target
LAB_BLE_CHAR  = "battery"


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _scope(max_tier: ActionRisk) -> AuthorizationScope:
    # Cumulative: allows every tier at or below `max_tier` (PASSIVE always).
    return AuthorizationScope.with_cumulative_tier(max_tier)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.7.9 golden path", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _wifi_discover() -> ActionRequest:
    return ActionRequest(capability="wifi.discovery", action="discover", risk=ActionRisk.PASSIVE)


def _wifi_inspect() -> ActionRequest:
    return ActionRequest(capability="wifi.discovery", action="inspect",
                         args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.PASSIVE)


def _handshake() -> ActionRequest:
    return ActionRequest(capability="wifi.capture", action="handshake",
                         args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SAFE_ACTIVE)


def _pmkid() -> ActionRequest:
    return ActionRequest(capability="wifi.capture", action="pmkid",
                         args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SENSITIVE_ACTIVE)


def _ble_discover() -> ActionRequest:
    return ActionRequest(capability="ble.discovery", action="discover", risk=ActionRisk.PASSIVE)


def _ble_inspect() -> ActionRequest:
    return ActionRequest(capability="ble.discovery", action="inspect",
                         args={"address": LAB_BLE}, risk=ActionRisk.PASSIVE)


def _connect() -> ActionRequest:
    return ActionRequest(capability="ble.discovery", action="connect",
                         args={"address": LAB_BLE}, risk=ActionRisk.SAFE_ACTIVE)


def _pair() -> ActionRequest:
    return ActionRequest(capability="ble.gatt", action="pair",
                         args={"address": LAB_BLE}, risk=ActionRisk.SAFE_ACTIVE)


def _gatt_write() -> ActionRequest:
    return ActionRequest(capability="ble.gatt", action="write",
                         args={"address": LAB_BLE, "characteristic": LAB_BLE_CHAR, "value": "encrypted:0xABCD"},
                         risk=ActionRisk.SENSITIVE_ACTIVE)


def _evidence_kinds(run: Run) -> list[str]:
    return sorted(ev.kind for ev in run.evidence)


def _events_of(run: Run, type_: str) -> list[dict]:
    from engine.logger import run_dir
    lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
    return [json.loads(l) for l in lines if l.strip() and json.loads(l).get("type") == type_]


# â”€â”€ 1. Wi-Fi golden path â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestWifiGoldenPath:
    def test_full_wifi_chain_end_to_end(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            # 1. discover (PASSIVE, no auth needed)
            d = engine.execute(_wifi_discover())
            assert d.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(d.observation.entities) > 0 and d.evidence == []

            # 2. inspect initial (PASSIVE) â€” target not yet captured
            i0 = engine.execute(_wifi_inspect())
            assert i0.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert i0.observation.entities[0].attributes["handshake_captured"] is False

            # 3. handshake (SAFE_ACTIVE) â€” allowed under SENSITIVE scope
            hs = engine.execute(_handshake())
            assert hs.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert hs.observation.entities[0].attributes["captured_frames"] == 4
            assert len(hs.evidence) == 1 and hs.evidence[0].kind == "wifi_eapol_handshake"

            # 4. pmkid (SENSITIVE_ACTIVE) â€” prereq satisfied (same bssid)
            pm = engine.execute(_pmkid())
            assert pm.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert pm.evidence[0].kind == "wifi_pmkid"

            # 5. inspect final â€” reflects real state change
            i1 = engine.execute(_wifi_inspect())
            attrs = i1.observation.entities[0].attributes
            assert attrs["handshake_captured"] is True
            assert attrs["pmkid_captured"] is True
            assert attrs["captured_frames"] == 4
            assert "handshake captured" in i1.observation.summary
            assert "PMKID captured" in i1.observation.summary
            assert i1.observation.summary != i0.observation.summary

            # 6. evidence traceability: kinds, provenance, attachment
            assert _evidence_kinds(run) == ["wifi_eapol_handshake", "wifi_pmkid"]
            for rec in run.actions:
                if rec.evidence:
                    assert rec.evidence[0].source_action_id == rec.request.id
        finally:
            logger.close()

    def test_wifi_evidence_persists_via_run_json_roundtrip(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.execute(_wifi_discover())
            engine.execute(_handshake())
            engine.execute(_pmkid())
        finally:
            logger.close()
        run2 = Run.from_dict(json.loads(json.dumps(run.to_dict(), default=str)))
        assert _evidence_kinds(run2) == ["wifi_eapol_handshake", "wifi_pmkid"]
        hs_acts = [a for a in run2.actions if a.request.capability == "wifi.capture" and a.request.action == "handshake"]
        assert len(hs_acts) == 1 and hs_acts[0].evidence[0].kind == "wifi_eapol_handshake"

    def test_wifi_jsonl_reports_complete_workflow(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.run_plan(wifi_capture_plan())
        finally:
            logger.close()
        assert len(_events_of(run, AGENT_STATUS)) >= 1
        assert len(_events_of(run, FINDING_CREATED)) >= 1
        evs = _events_of(run, EVIDENCE_CREATED)
        assert sorted(e["evidence"]["kind"] for e in evs) == ["wifi_eapol_handshake", "wifi_pmkid"]
        for e in evs:
            assert e["run_id"] == run.id and e["source_action_id"]

    def test_wifi_html_report_correct(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.run_plan(wifi_capture_plan())
        finally:
            logger.close()
        html = render_run(run)
        assert "<h2>EVIDENCE</h2>" in html and "Evidence produced:" in html
        assert "wifi_eapol_handshake" in html and "wifi_pmkid" in html
        assert LAB_WIFI_WPA3 in html


# â”€â”€ 2. BLE golden path â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBleGoldenPath:
    def test_full_ble_chain_end_to_end(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            # discover + inspect initial -> not connected
            d = engine.execute(_ble_discover())
            assert d.policy_decision.kind == PolicyDecisionKind.ALLOW and d.evidence == []
            i0 = engine.execute(_ble_inspect())
            assert "not connected" in i0.observation.summary

            # connect (SAFE_ACTIVE)
            c = engine.execute(_connect())
            assert c.policy_decision.kind == PolicyDecisionKind.ALLOW and c.evidence == []

            # pair (SAFE_ACTIVE) -> evidence
            p = engine.execute(_pair())
            assert p.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(p.evidence) == 1 and p.evidence[0].kind == "ble_pairing"

            # secure write (SENSITIVE_ACTIVE) -> evidence
            w = engine.execute(_gatt_write())
            assert w.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert w.evidence[0].kind == "ble_secure_write"

            # inspect final -> reflects paired + secure write
            i1 = engine.execute(_ble_inspect())
            s = i1.observation.summary
            assert "connected" in s and "paired" in s and "secure characteristic(s) written" in s
            assert i1.observation.summary != i0.observation.summary

            # device state genuinely mutated
            b = next(b for b in env.ble if b.address == LAB_BLE)
            assert b.connected is True and b.paired is True
            assert b.secure_characteristics[LAB_BLE_CHAR] == "encrypted:0xABCD"

            assert _evidence_kinds(run) == ["ble_pairing", "ble_secure_write"]
        finally:
            logger.close()

    def test_ble_jsonl_and_per_action_provenance(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.run_plan(ble_gatt_workflow_plan())
        finally:
            logger.close()
        evs = _events_of(run, EVIDENCE_CREATED)
        assert sorted(e["evidence"]["kind"] for e in evs) == ["ble_pairing", "ble_secure_write"]
        for a in run.actions:
            if a.evidence:
                assert a.evidence[0].source_action_id == a.request.id


# â”€â”€ 3. Wi-Fi + BLE coexist in one run â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestCombinedWorkflow:
    def test_both_plans_one_run_four_evidence_kinds(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.run_plan(wifi_capture_plan())
            engine.run_plan(ble_gatt_workflow_plan())
            assert run.status == RunStatus.COMPLETED
            assert _evidence_kinds(run) == [
                "ble_pairing", "ble_secure_write",
                "wifi_eapol_handshake", "wifi_pmkid",
            ]
            assert len(run.evidence) == 4
        finally:
            logger.close()

    def test_combined_jsonl_evidence_count_and_html(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.run_plan(wifi_capture_plan())
            engine.run_plan(ble_gatt_workflow_plan())
        finally:
            logger.close()
        assert len(_events_of(run, EVIDENCE_CREATED)) == 4
        html = render_run(run)
        for kind in ("ble_pairing", "ble_secure_write", "wifi_eapol_handshake", "wifi_pmkid"):
            assert kind in html
        assert len(run.evidence) == 4  # run.json payload is the same view as the report


# â”€â”€ 4. Authorization boundaries keep state + evidence consistent â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestAuthorizationBoundaries:
    def test_passive_scope_rejects_all_active_and_leaves_env_clean(self):
        engine, run, logger, env = _engine_with_scope()  # default = PASSIVE
        try:
            engine.run_plan(wifi_capture_plan())
            engine.run_plan(ble_gatt_workflow_plan())
            assert run.status == RunStatus.COMPLETED  # rejections are valid runs
            rejected = [a for a in run.actions if a.policy_decision.kind == PolicyDecisionKind.REJECT]
            assert len(rejected) == 5  # handshake, pmkid, connect, pair, write
            # Provider never invoked for any rejected action.
            for a in rejected:
                assert a.observation is None
                assert a.evidence == []
            assert run.evidence == []
            # Env untouched by active actions.
            assert performed_capability_keys(env) == set()
            for w in env.wifi:
                assert not w.handshake_captured and not w.pmkid_captured
            for b in env.ble:
                assert not b.connected and not b.paired
        finally:
            logger.close()

    def test_safe_active_scope_allows_safe_blocks_sensitive(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SAFE_ACTIVE))
        try:
            engine.run_plan(wifi_capture_plan())
            engine.run_plan(ble_gatt_workflow_plan())
            rejected = [a for a in run.actions if a.policy_decision.kind == PolicyDecisionKind.REJECT]
            assert {(a.request.capability, a.request.action) for a in rejected} == {
                ("wifi.capture", "pmkid"), ("ble.gatt", "write"),
            }
            # Only SAFE-tier evidence exists; SENSITIVE-tier evidence absent.
            assert _evidence_kinds(run) == ["ble_pairing", "wifi_eapol_handshake"]
            w = next(w for w in env.wifi if w.bssid == LAB_WIFI_WPA3)
            assert w.handshake_captured is True and w.pmkid_captured is False
            b = next(b for b in env.ble if b.address == LAB_BLE)
            assert b.connected is True and b.paired is True
            assert LAB_BLE_CHAR not in b.secure_characteristics or b.secure_characteristics[LAB_BLE_CHAR] == ""
        finally:
            logger.close()

    def test_all_rejected_actions_emit_no_evidence_event(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.run_plan(ble_gatt_workflow_plan())
        finally:
            logger.close()
        assert len(_events_of(run, EVIDENCE_CREATED)) == 0


# â”€â”€ 5. Prerequisites enforced per target â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPrerequisitesPerTarget:
    def test_pmkid_needs_handshake_on_same_bssid(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.execute(_handshake())
            # Different target -> prereq unmet -> structured failure, no evidence.
            rec = engine.execute(ActionRequest(
                capability="wifi.capture", action="pmkid",
                args={"bssid": LAB_WIFI_OPEN}, risk=ActionRisk.SENSITIVE_ACTIVE))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec.observation.entities == [] and rec.observation.evidence == []
            assert len(run.evidence) == 1  # only the handshake evidence
            w = next(w for w in env.wifi if w.bssid == LAB_WIFI_OPEN)
            assert w.pmkid_captured is False
        finally:
            logger.close()

    def test_gatt_pair_needs_connect_on_same_address(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.execute(_connect())
            other = "C0:11:22:33:44:02"  # lab device that is NOT connected in this run
            rec = engine.execute(ActionRequest(
                capability="ble.gatt", action="pair", args={"address": other},
                risk=ActionRisk.SAFE_ACTIVE))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec.observation.entities == [] and rec.observation.evidence == []
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_gatt_write_needs_pair_on_same_address(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.execute(_connect())  # connected but NOT paired
            rec = engine.execute(_gatt_write())
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert "is not paired" in rec.observation.summary
            assert rec.observation.evidence == [] and len(run.evidence) == 0
            b = next(b for b in env.ble if b.address == LAB_BLE)
            assert b.paired is False and b.secure_characteristics == {}
        finally:
            logger.close()


# â”€â”€ 6. Negative paths leave state + evidence consistent â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNegativePathConsistency:
    def test_wrong_wifi_target_unknown_bssid(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            rec = engine.execute(ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": "DE:AD:BE:EF:00:99"}, risk=ActionRisk.SAFE_ACTIVE))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec.observation.entities == [] and rec.observation.evidence == []
            assert "No Wi-Fi network found" in rec.observation.summary
            assert run.evidence == []
        finally:
            logger.close()

    def test_invalid_arguments_no_state_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            rec = engine.execute(ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": 123}, risk=ActionRisk.SAFE_ACTIVE))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec.observation.evidence == [] and "Invalid or missing" in rec.observation.summary
            # BLE wrong target + malformed write arg
            engine.execute(ActionRequest(
                capability="ble.gatt", action="write",
                args={"address": "ZZ:ZZ:ZZ:00:00:99", "characteristic": "x", "value": "y"},
                risk=ActionRisk.SENSITIVE_ACTIVE))
            assert run.evidence == []
            for w in env.wifi:
                assert not w.handshake_captured
        finally:
            logger.close()

    def test_success_then_failure_keeps_only_success_evidence(self):
        # A successful handshake creates evidence; a subsequent failed pmkid
        # (WEP target) must NOT create false success evidence, and the run's
        # evidence stays exactly the handshake record.
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            engine.execute(_handshake())
            engine.execute(ActionRequest(
                capability="wifi.capture", action="pmkid",
                args={"bssid": "02:00:00:00:00:03"}, risk=ActionRisk.SENSITIVE_ACTIVE))  # WEP
            assert _evidence_kinds(run) == ["wifi_eapol_handshake"]
        finally:
            logger.close()


# â”€â”€ 7. Determinism of the golden paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestGoldenPathDeterminism:
    def _combined_summary(self, seed: int) -> dict:
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE), seed=seed)
        try:
            engine.run_plan(wifi_capture_plan())
            engine.run_plan(ble_gatt_workflow_plan())
            return {
                "kinds": _evidence_kinds(run),
                "evidence": [
                    (ev.kind, ev.summary, json.dumps(ev.metadata, sort_keys=True))
                    for ev in run.evidence
                ],
                "final_inspect": [
                    a.observation.summary for a in run.actions
                    if a.observation and a.request.capability == "wifi.discovery" and a.request.action == "inspect"
                ],
            }
        finally:
            logger.close()

    def test_same_seed_identical_combined_workflow(self):
        a = self._combined_summary(7)
        b = self._combined_summary(7)
        assert a == b
        assert a["kinds"] == ["ble_pairing", "ble_secure_write", "wifi_eapol_handshake", "wifi_pmkid"]


# â”€â”€ 8. Contract audit: every Phase 2.7 interface â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestContractAudit:
    def test_capability_metadata_catalogue_frozen(self):
        # Phase 2.7 froze 14 entries. Phase 2.8.0 APPENDED the multi-domain
        # foundation (infrared / ethernet / usb â€” explicit-unsupported until
        # their dedicated 2.8.x subphases) WITHOUT altering the 14. Phase
        # 2.8.1 APPENDED `subghz.capture.signal` and flipped the existing
        # `subghz.discovery.analyze` `produces_evidence` Falseâ†’True â€”
        # sanctioned by the freeze's "new evidence kinds / domains by
        # extending KNOWN_EVIDENCE_KINDS + catalogue flags + a handler
        # success path" rule. The frozen Phase 2.7 keys/risks/requires below
        # are asserted against the preserved keys, not the absolute count.
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert len(DEFAULT_CAPABILITIES) == 23
        # Evidence producers after 2.8.1+2.8.2+2.8.3 = the 4 Phase 2.7 producers
        # + 2 Phase 2.8.1 producers (subghz.capture.signal + the analyze flag) +
        # 1 Phase 2.8.2 producer (nfc.discovery.read) + 2 Phase 2.8.3 producers
        # (infrared.analyze ir_analysis + infrared.transmit ir_transmit).
        # select/capture are PASSIVE (mutates_state / observational, but not
        # evidence-producing).
        ev = sorted(k for k, c in by_key.items() if c.produces_evidence)
        assert ev == ["ble.gatt.pair", "ble.gatt.write", "infrared.analyze",
                      "infrared.transmit", "nfc.discovery.read",
                      "subghz.capture.signal", "subghz.discovery.analyze",
                      "wifi.capture.handshake", "wifi.capture.pmkid"]
        # The 14 frozen Phase 2.7 keys are all still present.
        frozen = {
            "wifi.discovery.discover", "wifi.discovery.inspect",
            "wifi.capture.handshake", "wifi.capture.pmkid",
            "ble.discovery.discover", "ble.discovery.inspect",
            "ble.discovery.connect", "ble.discovery.write",
            "ble.gatt.pair", "ble.gatt.write",
            "nfc.discovery.scan", "nfc.discovery.read",
            "subghz.discovery.spectrum", "subghz.discovery.analyze",
        }
        assert frozen <= set(by_key) and len(frozen) == 14
        # Risk/prereq contract for the four Phase 2.7 producers.
        assert by_key["wifi.capture.handshake"].risk == ActionRisk.SAFE_ACTIVE
        assert by_key["wifi.capture.pmkid"].risk == ActionRisk.SENSITIVE_ACTIVE
        assert by_key["ble.gatt.pair"].risk == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.gatt.write"].risk == ActionRisk.SENSITIVE_ACTIVE
        assert by_key["wifi.capture.pmkid"].requires == ("wifi.capture.handshake",)
        assert by_key["ble.gatt.pair"].requires == ("ble.discovery.connect",)
        assert by_key["ble.gatt.write"].requires == ("ble.gatt.pair",)
        # Phase 2.8.1 contribution locked in: new capture entry + analyze flag.
        assert by_key["subghz.capture.signal"].risk == ActionRisk.SAFE_ACTIVE
        assert by_key["subghz.capture.signal"].mutates_state is True
        assert by_key["subghz.capture.signal"].produces_evidence is True
        assert by_key["subghz.discovery.analyze"].produces_evidence is True
        # Phase 2.8.2 contribution locked in: new select entry + read evidence flag.
        assert by_key["nfc.discovery.select"].mutates_state is True
        assert by_key["nfc.discovery.read"].produces_evidence is True
        # Phase 2.8.3 contribution locked in: analyze + transmit evidence flags.
        assert by_key["infrared.analyze"].risk == ActionRisk.SAFE_ACTIVE
        assert by_key["infrared.transmit"].risk == ActionRisk.SENSITIVE_ACTIVE
        assert by_key["infrared.analyze"].produces_evidence is True
        assert by_key["infrared.transmit"].produces_evidence is True
        assert by_key["infrared.capture"].produces_evidence is False

    def test_evidence_kind_vocabulary_matches_producers(self):
        assert KNOWN_EVIDENCE_KINDS == frozenset({
            "wifi_eapol_handshake", "wifi_pmkid", "ble_pairing", "ble_secure_write",
            "subghz_capture", "subghz_analysis",
            "nfc_read",             # Phase 2.8.2
            "ir_analysis", "ir_transmit",  # Phase 2.8.3
        })

    def test_evidence_record_contract(self):
        ev = EvidenceRecord(
            source_action_id="r1", source_capability="wifi.capture", source_action="handshake",
            target_entity_id="BSSID", target_entity_type="wifi_network", kind="wifi_eapol_handshake",
            summary="s", metadata={"frame_count": 4},
        )
        d = ev.to_dict()
        for f in ("id", "source_action_id", "source_capability", "source_action",
                  "target_entity_id", "target_entity_type", "kind", "summary",
                  "metadata", "captured_at"):
            assert f in d, f"EvidenceRecord missing field {f}"
        ev2 = EvidenceRecord.from_dict(json.loads(json.dumps(d)))
        assert ev2.kind == ev.kind and ev2.metadata == ev.metadata and ev2.id == ev.id

    def test_observation_evidence_default_empty(self):
        assert Observation().evidence == []

    def test_run_and_actionrecord_evidence_default_empty(self):
        run = Run()
        assert run.evidence == []
        assert run.actions == []  # fresh run has no actions
        # ActionRecord.evidence default
        from core.mission import ActionRecord
        assert ActionRecord(ActionRequest()).evidence == []

    def test_event_constant_sync_python_and_node(self):
        vue = Path(__file__).resolve().parent.parent
        js_events = (vue / "suryafool-cli" / "src" / "backend" / "events.js").read_text(encoding="utf-8")
        assert "EVIDENCE_CREATED: 'evidence.created'" in js_events

    def test_deterministic_plans_frozen_shapes(self):
        assert len(default_exploration_plan()) == 4
        assert len(wifi_capture_plan()) == 5
        assert len(ble_gatt_workflow_plan()) == 6
        assert len(subghz_capture_plan()) == 5      # Phase 2.8.1
        assert len(nfc_workflow_plan()) == 5        # Phase 2.8.2
        assert len(ir_workflow_plan()) == 4         # Phase 2.8.3
        for plan in (wifi_capture_plan(), ble_gatt_workflow_plan(),
                     subghz_capture_plan(), nfc_workflow_plan(), ir_workflow_plan()):
            for req in plan:
                reg = default_registry(environment=build_scenario("lab", seed=42))
                cap = reg.capability(req.capability, req.action)
                assert cap is not None and req.risk == cap.risk  # RiskDeclarationRule contract

    def test_performed_capability_keys_mapping_frozen(self):
        # Passive-only discoveries must not mark performed keys; active ones do.
        engine, run, logger, env = _engine_with_scope(_scope(ActionRisk.SENSITIVE_ACTIVE))
        try:
            assert performed_capability_keys(env) == set()
            engine.execute(_wifi_discover())
            assert performed_capability_keys(env) == set()
            engine.execute(_handshake())
            assert "wifi.capture.handshake" in performed_capability_keys(env)
        finally:
            logger.close()


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p279-"))
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