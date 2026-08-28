"""
tests/test_phase275_evidence.py

Phase 2.7.5 regression suite â€” first evidence-producing capability
(`wifi.capture.handshake`).

Proves the deterministic core can carry a complete evidence vertical slice:

  wifi.capture.handshake
  -> structured Observation
  -> structured EvidenceRecord (attached to the Observation)
  -> mirrored to ActionRecord.evidence AND Run.evidence by the engine
  -> persisted in run.json (to_dict/from_dict round-trip)
  -> emitted as `evidence.created` JSONL event
  -> visible in the HTML report (per-action + top-level EVIDENCE section)

All while preserving the unchanged Phase 2.6 authorization gate:
  - policy-rejected capture -> no evidence
  - failed capture (missing arg / unknown bssid / OPEN / WEP) -> no evidence
  - same seed -> stable evidence semantics (kind/summary/metadata/target)
  - existing Wi-Fi capture workflow (Phase 2.7.2) still works end-to-end

Evidence is structurally distinct from observation / indicator /
vulnerability hypothesis / confirmed finding â€” it carries its own
`kind` field and lives in a separate `Run.evidence` list, mirroring the
existing `Run.findings` list without collapsing them.

Run without pytest:
    python -m tests.test_phase275_evidence
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
LAB_WIFI_WPA3 = "02:00:00:00:00:01"      # LAB-INTERNAL, WPA3 â€” handshake target
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
    run = Run(objective="phase2.7.5 evidence test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _handshake_req(bssid=LAB_WIFI_WPA3) -> ActionRequest:
    return ActionRequest(
        capability="wifi.capture", action="handshake",
        args={"bssid": bssid}, risk=ActionRisk.SAFE_ACTIVE,
    )


# â”€â”€ 1. Successful handshake capture produces evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestSuccessfulCaptureProducesEvidence:
    def test_single_handshake_produces_one_evidence_record(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_handshake_req())
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec.observation is not None
            assert len(rec.observation.evidence) == 1
            ev = rec.observation.evidence[0]
            assert isinstance(ev, EvidenceRecord)
            assert ev.kind == "wifi_eapol_handshake"
        finally:
            logger.close()

    def test_evidence_kind_in_known_vocabulary(self):
        # The open-vocabulary frozenset is not enforced, but the sole
        # Phase 2.7.5 producer emits a kind that is in KNOWN_EVIDENCE_KINDS.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_handshake_req())
            ev = rec.observation.evidence[0]
            assert ev.kind in KNOWN_EVIDENCE_KINDS
        finally:
            logger.close()

    def test_evidence_metadata_no_fake_packet_blob(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_handshake_req())
            md = rec.observation.evidence[0].metadata
            # Metadata is deterministic structured fields only â€” no giant blob.
            assert md["frame_count"] == 4
            assert md["encryption"] in ("WPA2", "WPA3")
            assert md["bssid"] == LAB_WIFI_WPA3
            assert "ssid" in md and "channel" in md
            # Sanity: the whole metadata dict serializes cleanly and is small.
            blob = json.dumps(md)
            assert len(blob) < 500  # realistic metadata, not a fake dump
        finally:
            logger.close()


# â”€â”€ 2. Evidence is attached to the correct action/run â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestEvidenceAttachment:
    def test_evidence_mirrored_to_action_record(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_handshake_req())
            assert len(rec.evidence) == 1
            # The action.evidence is a mirror of observation.evidence, same id.
            assert rec.evidence[0].id == rec.observation.evidence[0].id
        finally:
            logger.close()

    def test_evidence_mirrored_to_run_record(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_handshake_req())
            assert len(run.evidence) == 1
            assert run.evidence[0].kind == "wifi_eapol_handshake"
        finally:
            logger.close()

    def test_evidence_not_attached_to_other_actions_in_same_run(self):
        # A discover action in the same run produces NO evidence â€” only the
        # handshake action does. Proves evidence is per-action, not run-global.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            disc = engine.execute(ActionRequest(
                capability="wifi.discovery", action="discover",
                risk=ActionRisk.PASSIVE,
            ))
            assert disc.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(disc.evidence) == 0
            cap = engine.execute(_handshake_req())
            assert len(cap.evidence) == 1
            assert len(run.evidence) == 1
        finally:
            logger.close()


# â”€â”€ 3. Evidence serializes/deserializes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestEvidenceSerialization:
    def test_evidence_record_to_dict_roundtrip(self):
        ev = EvidenceRecord(
            source_action_id="req-123",
            source_capability="wifi.capture",
            source_action="handshake",
            target_entity_id="02:00:00:00:00:01",
            target_entity_type="wifi_network",
            kind="wifi_eapol_handshake",
            summary="Captured 4 EAPOL frames (WPA3) from LAB-INTERNAL (...).",
            metadata={"frame_count": 4, "encryption": "WPA3"},
        )
        d = ev.to_dict()
        # JSON-serializable
        s = json.dumps(d)
        d2 = json.loads(s)
        ev2 = EvidenceRecord.from_dict(d2)
        assert ev2.id == ev.id
        assert ev2.source_action_id == "req-123"
        assert ev2.kind == "wifi_eapol_handshake"
        assert ev2.metadata == ev.metadata
        assert ev2.summary == ev.summary

    def test_run_json_roundtrip_preserves_evidence(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_handshake_req())
            assert len(run.evidence) == 1
        finally:
            logger.close()
        # Serialize/deserialize the whole Run record.
        d = run.to_dict()
        s = json.dumps(d, default=str)
        d2 = json.loads(s)
        run2 = Run.from_dict(d2)
        assert len(run2.evidence) == 1
        ev = run2.evidence[0]
        assert ev.kind == "wifi_eapol_handshake"
        assert ev.source_capability == "wifi.capture"
        assert ev.source_action == "handshake"
        assert ev.target_entity_id == LAB_WIFI_WPA3
        assert ev.metadata["frame_count"] == 4
        # And the action-level mirror round-trips too.
        assert len(run2.actions[0].evidence) == 1
        assert run2.actions[0].evidence[0].id == ev.id

    def test_old_run_json_without_evidence_field_loads_clean(self):
        # Back-compat: a run.json that predates Phase 2.7.5 has no `evidence`
        # key on Run or ActionRecord. Run.from_dict must default to [].
        import time as _time
        req = ActionRequest(capability="wifi.discovery", action="discover")
        rec_dict = {
            "request": req.to_dict(),
            "capability_decision": None, "policy_decision": None,
            "authoritative_risk": None, "observation": None,
            # NOTE: no "evidence" key â€” that's the back-compat case
            "error": None, "started_at": _time.time(), "completed_at": None,
        }
        run_dict = {
            "id": "run-old", "objective": "", "scenario": "", "backend": "simulator",
            "seed": None, "authorization": AuthorizationScope.default().to_dict(),
            "status": "completed", "started_at": _time.time(), "completed_at": _time.time(),
            "actions": [rec_dict], "observations": [],
            "capabilities_used": [], "errors": [], "findings": [],
            # NOTE: no "evidence" key â€” back-compat
            "final_summary": "",
        }
        run = Run.from_dict(run_dict)
        assert run.evidence == []
        assert run.actions[0].evidence == []


# â”€â”€ 4. Policy rejection produces no evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPolicyRejectProducesNoEvidence:
    def test_passive_scope_rejects_handshake_no_evidence(self):
        engine, run, logger, env = _engine_with_scope()  # default PASSIVE
        try:
            rec = engine.execute(_handshake_req())
            assert rec.policy_decision.kind == PolicyDecisionKind.REJECT
            assert rec.observation is None           # provider never ran
            assert len(rec.evidence) == 0            # default
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_caller_downgrade_rejected_no_evidence(self):
        # cap.risk=SAFE_ACTIVE; caller self-declares PASSIVE -> RiskDeclarationRule
        # rejects. Provider never invoked -> no evidence.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            req = ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.PASSIVE,
            )
            rec = engine.execute(req)
            assert rec.policy_decision.kind == PolicyDecisionKind.REJECT
            assert rec.observation is None
            assert len(run.evidence) == 0
        finally:
            logger.close()

    def test_caller_upgrade_rejected_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            req = ActionRequest(
                capability="wifi.capture", action="handshake",
                args={"bssid": LAB_WIFI_WPA3}, risk=ActionRisk.SENSITIVE_ACTIVE,
            )
            rec = engine.execute(req)
            assert rec.policy_decision.kind == PolicyDecisionKind.REJECT
            assert len(run.evidence) == 0
        finally:
            logger.close()


# â”€â”€ 5. Failed capture produces no false-positive evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestFailedCaptureNoFalsePositive:
    """All simulator failure paths for wifi.capture.handshake MUST return an
    Observation with `evidence=[]` (the default). The success path is the
    ONLY path that builds an EvidenceRecord. Proves the contract: a failed
    capture does not produce misleading successful evidence."""

    def _exec_direct(self, args):
        from simulator.simulator import action_wifi_capture_handshake
        env = build_scenario("lab", seed=42)
        return action_wifi_capture_handshake(env, args), env

    def test_missing_bssid_no_evidence(self):
        obs, env = self._exec_direct({})
        assert obs.entities == []
        assert obs.evidence == []

    def test_non_string_bssid_no_evidence(self):
        obs, env = self._exec_direct({"bssid": 12345})
        assert obs.entities == []
        assert obs.evidence == []

    def test_unknown_bssid_no_evidence(self):
        obs, env = self._exec_direct({"bssid": "DE:AD:BE:EF:00:99"})
        assert obs.entities == []
        assert obs.evidence == []

    def test_open_network_no_evidence(self):
        obs, env = self._exec_direct({"bssid": LAB_WIFI_OPEN})
        assert obs.entities == []
        assert "OPEN" in obs.summary
        assert obs.evidence == []

    def test_wep_network_no_evidence(self):
        obs, env = self._exec_direct({"bssid": LAB_WIFI_WEP})
        assert obs.entities == []
        assert "WEP" in obs.summary
        assert obs.evidence == []

    def test_failed_capture_via_engine_produces_no_run_evidence(self):
        # End-to-end: an OPEN target through the engine. Policy ALLOWs
        # (SAFE_ACTIVE scope), the provider runs, the handler returns a
        # failure Observation with empty evidence. Run.evidence stays empty.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_handshake_req(bssid=LAB_WIFI_OPEN))
            assert rec.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert rec.observation is not None
            assert rec.observation.entities == []
            assert len(rec.evidence) == 0
            assert len(run.evidence) == 0
        finally:
            logger.close()


# â”€â”€ 6. Provenance fields are correct â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestProvenanceFields:
    def test_all_required_provenance_fields_present(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            req = _handshake_req()
            rec = engine.execute(req)
            ev = rec.observation.evidence[0]
            # Per Phase 2.7.5 requirements:
            assert ev.id                                  # evidence ID
            assert ev.source_action_id == req.id          # source action id
            assert ev.source_capability == "wifi.capture"  # source capability
            assert ev.source_action == "handshake"         # source action verb
            assert ev.target_entity_id == LAB_WIFI_WPA3   # target/entity
            assert ev.target_entity_type == "wifi_network"
            assert ev.captured_at > 0                     # timestamp
            assert ev.kind == "wifi_eapol_handshake"      # distinction tag
            assert ev.summary                              # concise summary
            assert ev.metadata["frame_count"] == 4        # evidence metadata
        finally:
            logger.close()

    def test_source_action_id_is_request_id_after_engine(self):
        # The simulator can't see the ActionRequest; the engine stamps it.
        # Prove the engine-side stamp actually fills source_action_id.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            req = _handshake_req()
            # Before execution, the request has an id.
            assert req.id
            rec = engine.execute(req)
            ev = rec.observation.evidence[0]
            # Same id â€” not a fresh uuid the simulator made up.
            assert ev.source_action_id == req.id
            assert ev.source_action_id != ""
            assert ev.source_action_id != ev.id  # evidence id != source action id
        finally:
            logger.close()

    def test_evidence_distinct_from_finding_and_observation(self):
        # Evidence and findings are different lists with different shapes.
        # Findings carry raw entity attributes; evidence carries provenance.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_handshake_req())
            assert len(run.evidence) == 1
            assert len(run.findings) >= 1  # handshake returns 1 wifi_network entity
            ev = run.evidence[0]
            f = run.findings[0]
            # Different field sets â€” evidence has source_action_id, findings don't.
            assert "source_action_id" in ev.to_dict()
            assert "source_action_id" not in f
            # Different lists â€” evidence has `kind`, findings have `confidence`.
            assert "kind" in ev.to_dict()
            assert "confidence" in f
        finally:
            logger.close()


# â”€â”€ 7. Deterministic repeatability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDeterminism:
    def _evidence_summary_for_seed(self, seed: int) -> dict:
        engine, run, logger, env = _engine_with_scope(_safe_active_scope(), seed=seed)
        try:
            engine.execute(_handshake_req())
            assert len(run.evidence) == 1
            ev = run.evidence[0]
            return {
                "kind": ev.kind,
                "source_capability": ev.source_capability,
                "source_action": ev.source_action,
                "target_entity_id": ev.target_entity_id,
                "target_entity_type": ev.target_entity_type,
                "summary": ev.summary,
                "metadata": ev.metadata,
            }
        finally:
            logger.close()

    def test_same_seed_yields_stable_evidence_semantics(self):
        a = self._evidence_summary_for_seed(7)
        b = self._evidence_summary_for_seed(7)
        # Semantic stability â€” kind, source, target, summary, metadata all
        # identical. id and captured_at are intentionally run-specific (they
        # follow the existing Observation.id / Run.id non-determinism pattern).
        assert a == b

    def test_evidence_semantics_change_with_target(self):
        # Same seed, different target -> different summary + target_entity_id.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope(),
                                                       scenario="home", seed=7)
        try:
            engine.execute(_handshake_req(bssid=HOME_WIFI_WPA2))
            ev = run.evidence[0]
            assert ev.target_entity_id == HOME_WIFI_WPA2
            assert "WPA2" in ev.summary or ev.metadata["encryption"] == "WPA2"
        finally:
            logger.close()


# â”€â”€ 8. Existing Wi-Fi capture workflow still works â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestExistingWifiCaptureWorkflowIntact:
    def test_wifi_capture_plan_completes_with_evidence_for_both_capture_actions(self):
        # Phase 2.7.2's full plan: discover -> inspect -> handshake -> pmkid
        # -> inspect. After 2.7.6 BOTH capture actions produce evidence:
        # handshake -> wifi_eapol_handshake, pmkid -> wifi_pmkid. Run.evidence
        # total == 2, one per capture action, distinct kinds.
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(wifi_capture_plan())
            assert run.status == RunStatus.COMPLETED
            assert len(run.evidence) == 2
            kinds = sorted(ev.kind for ev in run.evidence)
            assert kinds == ["wifi_eapol_handshake", "wifi_pmkid"]
            sources = {(ev.source_capability, ev.source_action) for ev in run.evidence}
            assert sources == {("wifi.capture", "handshake"), ("wifi.capture", "pmkid")}
            pmkid_acts = [a for a in run.actions
                          if a.request.capability == "wifi.capture"
                          and a.request.action == "pmkid"]
            handshake_acts = [a for a in run.actions
                              if a.request.capability == "wifi.capture"
                              and a.request.action == "handshake"]
            assert len(pmkid_acts) == 1 and len(handshake_acts) == 1
            assert len(pmkid_acts[0].evidence) == 1
            assert len(handshake_acts[0].evidence) == 1
        finally:
            logger.close()

    def test_wifi_capture_state_fields_still_mutated(self):
        # Phase 2.7.2 invariants must still hold â€” handshake_captured=True,
        # captured_frames=4, pmkid_captured=True after the full plan.
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(wifi_capture_plan())
            w = next(w for w in env.wifi if w.bssid == LAB_WIFI_WPA3)
            assert w.handshake_captured is True
            assert w.captured_frames == 4
            assert w.pmkid_captured is True
        finally:
            logger.close()

    def test_pmkid_success_path_produces_evidence_after_handshake(self):
        # Direct handler call â€” pmkid (after handshake on the SAME bssid)
        # returns an Observation carrying exactly one wifi_pmkid EvidenceRecord.
        from simulator.simulator import (
            action_wifi_capture_handshake, action_wifi_capture_pmkid,
        )
        env = build_scenario("lab", seed=42)
        action_wifi_capture_handshake(env, {"bssid": LAB_WIFI_WPA3})
        obs = action_wifi_capture_pmkid(env, {"bssid": LAB_WIFI_WPA3})
        assert len(obs.entities) == 1  # pmkid success path returns an entity
        assert len(obs.evidence) == 1   # and exactly one evidence record
        assert obs.evidence[0].kind == "wifi_pmkid"


# â”€â”€ 9. JSONL + HTML smoke â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestJsonlAndHtmlSmoke:
    def test_evidence_created_event_emitted_to_events_jsonl(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_handshake_req())
        finally:
            logger.close()
        from engine.logger import run_dir
        events_path = run_dir(run.id) / "events.jsonl"
        assert events_path.exists()
        lines = events_path.read_text().splitlines()
        events = [json.loads(l) for l in lines if l.strip()]
        ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
        assert len(ev_events) == 1
        ev_payload = ev_events[0]
        assert ev_payload["run_id"] == run.id
        assert ev_payload["evidence"]["kind"] == "wifi_eapol_handshake"
        # source_action_id is the request id (the engine stamped it).
        assert ev_payload["source_action_id"]

    def test_rejected_action_emits_no_evidence_event(self):
        engine, run, logger, env = _engine_with_scope()  # PASSIVE-only
        try:
            engine.execute(_handshake_req())
        finally:
            logger.close()
        from engine.logger import run_dir
        events_path = run_dir(run.id) / "events.jsonl"
        lines = events_path.read_text().splitlines()
        events = [json.loads(l) for l in lines if l.strip()]
        ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
        assert len(ev_events) == 0

    def test_html_report_contains_evidence_section_and_provenance(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_handshake_req())
        finally:
            logger.close()
        html = render_run(run)
        # Top-level EVIDENCE section header.
        assert "<h2>EVIDENCE</h2>" in html
        # Per-action evidence.
        assert "Evidence produced:" in html
        assert "wifi_eapol_handshake" in html
        # Provenance chain is visible.
        assert "wifi.capture.handshake" in html  # source_capability.source_action
        assert LAB_WIFI_WPA3 in html              # target_entity_id
        assert "frame_count" in html              # metadata table

    def test_html_report_shows_empty_evidence_section_when_no_evidence(self):
        # A PASSIVE-only run produces an empty evidence section, not a
        # missing one (so report consumers can rely on the section existing).
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.run_plan(default_exploration_plan())  # all PASSIVE
        finally:
            logger.close()
        html = render_run(run)
        assert "<h2>EVIDENCE</h2>" in html
        assert "No evidence captured by this run." in html

    def test_node_smoke_events_jsonl_consumable_incremental(self):
        # The Node TUI smoke parser tolerates an unknown event type by
        # dropping it (look-before-leap in src/backend/events.js isValidEvent
        # whitelists by EventType). Adding EVIDENCE_CREATED to that
        # whitelisting keeps the smoke test green. We assert the type is now
        # registered in the Node mirror so consumers can react to it.
        ev_js = Path(__file__).resolve().parent.parent / "suryafool-cli" / "src" / "backend" / "events.js"
        txt = ev_js.read_text(encoding="utf-8")
        assert "EVIDENCE_CREATED: 'evidence.created'" in txt
        assert "evidenceCreated" in txt


# â”€â”€ 10. Regression: catalogue + existing plan shapes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegression:
    def test_catalogue_count_at_21(self):
        # Phase 2.8.0 appended the multi-domain foundation (infrared / ethernet
        # / usb) to the Phase 2.7 catalogue of 14.
        assert len(DEFAULT_CAPABILITIES) == 23

    def test_handshake_marked_produces_evidence_in_catalogue(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["wifi.capture.handshake"].produces_evidence is True

    def test_pmkid_marked_produces_evidence_in_phase_2_7_6(self):
        # Phase 2.7.6 generalizes the 2.7.5 slice to wifi.capture.pmkid.
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["wifi.capture.pmkid"].produces_evidence is True

    def test_only_evidence_capabilities_marked(self):
        # Phase 2.7.7: wifi.capture pair (2.7.5/2.7.6) + ble.gatt pair/write
        # (2.7.7) are the Phase 2.7 evidence-producing entries. Phase 2.8.1
        # extended the set with subghz.capture.signal + flipped
        # subghz.discovery.analyze produces_evidence True. Phase 2.8.2 added
        # nfc.discovery.read (the nfc.discovery.select step is PASSIVE — a
        # discovery step, not a capture — so it does NOT produce evidence).
        # Phase 2.8.3 added infrared.analyze + infrared.transmit (infrared.
        # capture is PASSIVE observational — no evidence).
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        evidence_caps = [k for k, c in by_key.items() if c.produces_evidence]
        assert sorted(evidence_caps) == [
            "ble.gatt.pair", "ble.gatt.write",
            "infrared.analyze", "infrared.transmit",
            "nfc.discovery.read",
            "subghz.capture.signal", "subghz.discovery.analyze",
            "wifi.capture.handshake", "wifi.capture.pmkid",
        ]

    def test_default_exploration_plan_unchanged(self):
        plan = default_exploration_plan()
        assert len(plan) == 4
        assert all(p.risk == ActionRisk.PASSIVE for p in plan)

    def test_wifi_capture_plan_unchanged_5_actions(self):
        plan = wifi_capture_plan()
        assert len(plan) == 5


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p275-"))
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
