"""
tests/test_phase276_pmkid_evidence.py

Phase 2.7.6 regression suite â€” generalize the evidence pipeline to
`wifi.capture.pmkid` (second evidence-producing capability, same
wifi.capture domain, EXACT same pipeline as Phase 2.7.5's handshake).

Proves the 2.7.5 EvidenceRecord pipeline was not a one-off: PMKID capture
flows through the identical chain

  wifi.capture.pmkid (success)
  -> structured Observation.evidence (kind="wifi_pmkid")
  -> mirrored to ActionRecord.evidence + Run.evidence by the engine
  -> run.json round-trip + evidence.created JSONL event
  -> HTML EVIDENCE section

while every non-success path (missing/invalid/unknown target, non-WPA
encryption, per-target handshake prereq unmet, policy rejection) still
produces ZERO evidence. Handshake evidence behavior is unchanged and the
two kinds coexist in one run.

Run without pytest:
    python -m tests.test_phase276_pmkid_evidence
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
from core.observation import Observation
from engine.logger import RunLogger
from engine.runner import (
    RunEngine,
    default_exploration_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import render_run
from simulator.scenarios import build_scenario


# Lab scenario literal bssids (seed-independent).
LAB_WIFI_WPA3 = "02:00:00:00:00:01"      # LAB-INTERNAL, WPA3 â€” pmkid target
LAB_WIFI_OPEN = "02:00:00:00:00:02"      # LAB-TARGET-OPEN â€” non-WPA failure path
LAB_WIFI_WEP  = "02:00:00:00:00:03"      # LAB-TARGET-WEP  â€” non-WPA failure path
HOME_WIFI_WPA2 = "02:00:00:00:00:12"     # HomeNet-2.4G, WPA2 â€” alt success path


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _sensitive_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _safe_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.7.6 pmkid evidence test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _pmkid_req(bssid=LAB_WIFI_WPA3) -> ActionRequest:
    return ActionRequest(
        capability="wifi.capture", action="pmkid",
        args={"bssid": bssid}, risk=ActionRisk.SENSITIVE_ACTIVE,
    )


def _run_handshake_then_pmkid(engine, bssid=LAB_WIFI_WPA3):
    """Execute the per-target prerequisite (handshake) then pmkid through the
    engine under a SENSITIVE_ACTIVE scope. Returns (handshake_rec, pmkid_rec)."""
    hs = engine.execute(ActionRequest(
        capability="wifi.capture", action="handshake",
        args={"bssid": bssid}, risk=ActionRisk.SAFE_ACTIVE,
    ))
    pm = engine.execute(_pmkid_req(bssid))
    return hs, pm


# â”€â”€ 1. Successful PMKID capture produces exactly one evidence record â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestSuccessfulPmkidProducesEvidence:
    def test_exactly_one_evidence_record_after_handshake(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            hs, pm = _run_handshake_then_pmkid(engine)
            assert hs.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert pm.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(pm.observation.evidence) == 1
            assert len(pm.evidence) == 1       # action mirror
            assert len(run.evidence) == 2      # handshake + pmkid = 2 total
        finally:
            logger.close()


# â”€â”€ 2. Evidence kind is correct â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestEvidenceKind:
    def test_pmkid_evidence_kind_is_wifi_pmkid(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            hs, pm = _run_handshake_then_pmkid(engine)
            assert pm.observation.evidence[0].kind == "wifi_pmkid"
            kinds = {ev.kind for ev in run.evidence}
            assert kinds == {"wifi_eapol_handshake", "wifi_pmkid"}
        finally:
            logger.close()

    def test_kind_in_known_vocabulary(self):
        from core.evidence import KNOWN_EVIDENCE_KINDS
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _, pm = _run_handshake_then_pmkid(engine)
            assert pm.observation.evidence[0].kind in KNOWN_EVIDENCE_KINDS
        finally:
            logger.close()


# â”€â”€ 3. Provenance is correct â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestProvenance:
    def test_pmkid_provenance_fields(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            req = _pmkid_req()
            hs_req = None
            # capture the pmkid request id explicitly
            hs = engine.execute(ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SAFE_ACTIVE,
            ))
            pm = engine.execute(req)
            ev = pm.observation.evidence[0]
            assert ev.source_action_id == req.id
            assert ev.source_capability == "wifi.capture"
            assert ev.source_action == "pmkid"
            assert ev.target_entity_id == LAB_WIFI_WPA3
            assert ev.target_entity_type == "wifi_network"
            assert ev.captured_at > 0
            assert ev.summary
            assert ev.metadata["pmkid"] is True
            assert ev.metadata["handshake_prereq"] is True
        finally:
            logger.close()

    def test_evidence_distinct_from_finding_and_observation(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _, pm = _run_handshake_then_pmkid(engine)
            ev = pm.observation.evidence[0]
            assert "source_action_id" in ev.to_dict()
            assert "source_action_id" not in run.findings[0]
        finally:
            logger.close()


# â”€â”€ 4. Prerequisite failure produces no evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPrereqFailureNoEvidence:
    def test_pmkid_without_handshake_on_target_produces_no_evidence(self):
        # The per-target prereq (handshake on the SAME bssid) is enforced by
        # the handler â€” pmkid against a never-captured target is a structured
        # failure Observation with evidence=[] and run.evidence stays empty.
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(_pmkid_req())   # no handshake first
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW  # policy allows
            assert rec.observation is not None
            assert rec.observation.entities == []
            assert "No handshake captured" in rec.observation.summary
            assert rec.observation.evidence == []
            assert len(rec.evidence) == 0
            assert len(run.evidence) == 0
            w = next(w for w in env.wifi if w.bssid == LAB_WIFI_WPA3)
            assert w.pmkid_captured is False
        finally:
            logger.close()

    def test_pmkid_after_handshake_on_different_bssid_produces_no_evidence(self):
        # Handshake captured on one WPA network does NOT satisfy the prereq
        # for pmkid on a DIFFERENT bssid -> failure -> zero evidence.
        from simulator.environment import Environment
        from simulator.entities import WifiNetwork
        from simulator.simulator import (
            action_wifi_capture_handshake, action_wifi_capture_pmkid,
        )
        env = Environment(name="t", wifi=[
            WifiNetwork(ssid="A", bssid="02:00:00:00:00:01", channel=1,
                        rssi=-50, encryption="WPA3"),
            WifiNetwork(ssid="B", bssid="02:00:00:00:00:02", channel=1,
                        rssi=-50, encryption="WPA2"),
        ])
        action_wifi_capture_handshake(env, {"bssid": "02:00:00:00:00:01"})
        obs = action_wifi_capture_pmkid(env, {"bssid": "02:00:00:00:00:02"})
        assert obs.entities == []
        assert "No handshake captured" in obs.summary
        assert obs.evidence == []
        # Only the handshake note stamped â€” no pmkid note, env otherwise clean.
        assert len(env.notes) == 1
        assert any(k.startswith("wifi_handshake:") for k in env.notes)
        assert not any(k.startswith("wifi_pmkid:") for k in env.notes)


# â”€â”€ 5. Policy rejection produces no evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPolicyRejectNoEvidence:
    def test_pmkid_rejected_under_safe_active_scope_no_evidence(self):
        # pmkid is SENSITIVE_ACTIVE; SAFE_ACTIVE scope REJECTs at the tier
        # gate. Provider never invoked -> zero evidence.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_pmkid_req())
            assert rec.policy_decision.kind == PolicyDecisionKind.REJECT
            assert rec.observation is None
            assert len(rec.evidence) == 0
            assert len(run.evidence) == 0
            assert all("wifi_pmkid:" not in k for k in env.notes)
        finally:
            logger.close()

    def test_pmkid_rejected_under_passive_scope_no_evidence(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            rec = engine.execute(_pmkid_req())
            assert rec.policy_decision.kind == PolicyDecisionKind.REJECT
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_caller_downgrade_rejected_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            req = ActionRequest(
                capability="wifi.capture", action="pmkid",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SAFE_ACTIVE,
            )
            rec = engine.execute(req)
            assert rec.policy_decision.kind == PolicyDecisionKind.REJECT
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_caller_upgrade_rejected_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            req = ActionRequest(
                capability="wifi.capture", action="pmkid",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.RESTRICTED,
            )
            rec = engine.execute(req)
            assert rec.policy_decision.kind == PolicyDecisionKind.REJECT
            assert len(run.evidence) == 0
        finally:
            logger.close()


# â”€â”€ 6. Failed/invalid capture produces no evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestFailedCaptureNoEvidence:
    def _exec_direct_with_handshake(self, args):
        from simulator.simulator import (
            action_wifi_capture_handshake, action_wifi_capture_pmkid,
        )
        env = build_scenario("lab", seed=42)
        action_wifi_capture_handshake(env, {"bssid": LAB_WIFI_WPA3})
        return action_wifi_capture_pmkid(env, args)

    def test_missing_bssid_no_evidence(self):
        obs = self._exec_direct_with_handshake({})
        assert obs.entities == []
        assert obs.evidence == []

    def test_non_string_bssid_no_evidence(self):
        obs = self._exec_direct_with_handshake({"bssid": 12345})
        assert obs.entities == []
        assert obs.evidence == []

    def test_unknown_bssid_no_evidence(self):
        obs = self._exec_direct_with_handshake({"bssid": "DE:AD:BE:EF:00:99"})
        assert obs.entities == []
        assert obs.evidence == []

    def test_open_network_no_evidence(self):
        # OPEN fails even with a handshake-attempt first? OPEN never accepts a
        # handshake, so simulate open target pmkid directly.
        from simulator.simulator import action_wifi_capture_pmkid
        env = build_scenario("lab", seed=42)
        obs = action_wifi_capture_pmkid(env, {"bssid": LAB_WIFI_OPEN})
        assert obs.entities == []
        assert "no PMKID" in obs.summary
        assert obs.evidence == []

    def test_wep_network_no_evidence(self):
        from simulator.simulator import action_wifi_capture_pmkid
        env = build_scenario("lab", seed=42)
        obs = action_wifi_capture_pmkid(env, {"bssid": LAB_WIFI_WEP})
        assert obs.entities == []
        assert obs.evidence == []

    def test_failed_capture_via_engine_no_run_evidence(self):
        # End-to-end: valid policy, handshake prereq met on target, but the
        # target is OPEN -> handler returns failure Observation with empty
        # evidence. run.evidence has only the handshake item.
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            hs = engine.execute(ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SAFE_ACTIVE,
            ))
            pm = engine.execute(_pmkid_req(bssid=LAB_WIFI_OPEN))
            assert pm.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert pm.observation.evidence == []
            assert len(pm.evidence) == 0
            assert len(run.evidence) == 1  # only handshake evidence
        finally:
            logger.close()


# â”€â”€ 7. Handshake + PMKID evidence coexist in one run â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestCoexistence:
    def test_both_kinds_in_one_run_with_correct_total(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            hs, pm = _run_handshake_then_pmkid(engine)
            assert len(run.evidence) == 2
            assert len(hs.evidence) == 1 and len(pm.evidence) == 1
            by_id = {ev.id: ev for ev in run.evidence}
            hsev = hs.evidence[0]
            pmev = pm.evidence[0]
            # distinct ids, distinct kinds, distinct source actions
            assert hsev.id != pmev.id
            assert hsev.kind == "wifi_eapol_handshake"
            assert pmev.kind == "wifi_pmkid"
            assert {ev.source_action for ev in run.evidence} == {"handshake", "pmkid"}
        finally:
            logger.close()

    def test_run_json_roundtrip_preserves_both(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_handshake_then_pmkid(engine)
            assert len(run.evidence) == 2
        finally:
            logger.close()
        d = run.to_dict()
        s = json.dumps(d, default=str)
        run2 = Run.from_dict(json.loads(s))
        assert len(run2.evidence) == 2
        kinds = sorted(ev.kind for ev in run2.evidence)
        assert kinds == ["wifi_eapol_handshake", "wifi_pmkid"]
        # action-level mirrors round-trip too
        pmkid_acts = [a for a in run2.actions
                      if a.request.capability == "wifi.capture"
                      and a.request.action == "pmkid"]
        assert len(pmkid_acts[0].evidence) == 1
        assert pmkid_acts[0].evidence[0].kind == "wifi_pmkid"


# â”€â”€ 8. Deterministic repeatability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDeterminism:
    def _pmkid_evidence_semantics(self, seed: int) -> dict:
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope(), seed=seed)
        try:
            _run_handshake_then_pmkid(engine)
            pmev = next(ev for ev in run.evidence if ev.kind == "wifi_pmkid")
            return {
                "kind": pmev.kind,
                "source_capability": pmev.source_capability,
                "source_action": pmev.source_action,
                "target_entity_id": pmev.target_entity_id,
                "target_entity_type": pmev.target_entity_type,
                "summary": pmev.summary,
                "metadata": pmev.metadata,
            }
        finally:
            logger.close()

    def test_same_seed_yields_stable_pmkid_evidence_semantics(self):
        a = self._pmkid_evidence_semantics(7)
        b = self._pmkid_evidence_semantics(7)
        assert a == b
        assert a["kind"] == "wifi_pmkid"
        assert a["metadata"]["pmkid"] is True

    def test_handshake_evidence_semantics_unchanged_by_2_7_6(self):
        # Regression: the 2.7.5 handshake evidence is byte-for-byte stable
        # under the same seed (metadata/summary unchanged by the pmkid add).
        def hs_semantics(seed):
            engine, run, logger, env = _engine_with_scope(_sensitive_active_scope(), seed=seed)
            try:
                _run_handshake_then_pmkid(engine)
                hsev = next(ev for ev in run.evidence if ev.kind == "wifi_eapol_handshake")
                return (hsev.summary, hsev.metadata)
            finally:
                logger.close()
        a, b = hs_semantics(11), hs_semantics(11)
        assert a == b


# â”€â”€ 9. JSONL + HTML reporting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestJsonlAndHtml:
    def test_two_evidence_created_events_emitted_to_jsonl(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_handshake_then_pmkid(engine)
        finally:
            logger.close()
        from engine.logger import run_dir
        events_path = run_dir(run.id) / "events.jsonl"
        lines = events_path.read_text().splitlines()
        events = [json.loads(l) for l in lines if l.strip()]
        ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
        assert len(ev_events) == 2
        kinds = sorted(e["evidence"]["kind"] for e in ev_events)
        assert kinds == ["wifi_eapol_handshake", "wifi_pmkid"]
        for e in ev_events:
            assert e["run_id"] == run.id
            assert e["source_action_id"]

    def test_rejected_pmkid_emits_no_evidence_event(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_pmkid_req())  # REJECT at tier gate
        finally:
            logger.close()
        from engine.logger import run_dir
        lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
        ev_events = [e for e in (json.loads(l) for l in lines if l.strip())
                     if e.get("type") == EVIDENCE_CREATED]
        assert len(ev_events) == 0

    def test_html_report_shows_both_kinds_and_provenance(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            _run_handshake_then_pmkid(engine)
        finally:
            logger.close()
        html = render_run(run)
        assert "<h2>EVIDENCE</h2>" in html
        assert "Evidence produced:" in html
        assert "wifi_pmkid" in html
        assert "wifi_eapol_handshake" in html
        assert "wifi.capture.pmkid" in html   # source capability.action
        assert LAB_WIFI_WPA3 in html          # target entity id
        assert "handshake_prereq" in html     # metadata column

    def test_html_report_renders_empty_evidence_for_blank_run(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(default_exploration_plan())  # all PASSIVE
        finally:
            logger.close()
        html = render_run(run)
        assert "<h2>EVIDENCE</h2>" in html
        assert "No evidence captured by this run." in html


# â”€â”€ 10. Regression: catalogue + previous suites stay green â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegression:
    def test_catalogue_count_at_21(self):
        # Phase 2.8.0 appended the multi-domain foundation (infrared / ethernet
        # / usb) to the Phase 2.7 catalogue of 14.
        assert len(DEFAULT_CAPABILITIES) == 23

    def test_both_wifi_capture_caps_produce_evidence(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["wifi.capture.handshake"].produces_evidence is True
        assert by_key["wifi.capture.pmkid"].produces_evidence is True

    def test_only_evidence_capabilities_marked(self):
        # Phase 2.8.1 added subghz_capture/subghz_analysis; Phase 2.8.2 added
        # nfc_read; Phase 2.8.3 added infrared.analyze/transmit (ir_analysis /
        # ir_transmit). The complete 9-producer set is preserved by all phases.
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        evidence_caps = [k for k, c in by_key.items() if c.produces_evidence]
        assert sorted(evidence_caps) == [
            "ble.gatt.pair", "ble.gatt.write",
            "infrared.analyze", "infrared.transmit",
            "nfc.discovery.read",
            "subghz.capture.signal", "subghz.discovery.analyze",
            "wifi.capture.handshake", "wifi.capture.pmkid",
        ]

    def test_wifi_capture_plan_unchanged_5_actions(self):
        plan = wifi_capture_plan()
        assert len(plan) == 5
        assert all(p.risk in (ActionRisk.PASSIVE, ActionRisk.SAFE_ACTIVE,
                              ActionRisk.SENSITIVE_ACTIVE) for p in plan)

    def test_default_exploration_plan_unchanged(self):
        plan = default_exploration_plan()
        assert len(plan) == 4
        assert all(p.risk == ActionRisk.PASSIVE for p in plan)

    def test_pmkid_prereq_still_enforced_stateful(self):
        # Phase 2.7.2 per-target prerequisite invariant: pmkid_captured only
        # becomes True after handshake on the SAME bssid observed via
        # performed_capability_keys.
        from simulator.simulator import performed_capability_keys
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            assert "wifi.capture.pmkid" not in performed_capability_keys(env)
            engine.execute(ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SAFE_ACTIVE,
            ))
            performed = performed_capability_keys(env)
            assert "wifi.capture.handshake" in performed
            engine.execute(_pmkid_req())
            assert "wifi.capture.pmkid" in performed_capability_keys(env)
            w = next(w for w in env.wifi if w.bssid == LAB_WIFI_WPA3)
            assert w.pmkid_captured is True
        finally:
            logger.close()


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p276-"))
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