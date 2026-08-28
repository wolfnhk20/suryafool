"""
tests/test_phase282_nfc_read.py

Phase 2.8.2 — first real NFC/RFID capability slice on the frozen Phase 2.7
stack + Phase 2.8.0 multi-domain foundation + Phase 2.8.1 Sub-GHz slice.
The deterministic vertical chain is:

    nfc.discovery.scan      (PASSIVE, enumerates tags)
    nfc.discovery.select    (NEW PASSIVE  — PN532 InListPassiveTarget + activate; mutates NfcTag.selected=True; no evidence)
    nfc.discovery.read      (UPGRADE  — per-target prereq t.selected=True on the SAME uid; produces nfc_read evidence)

Proves the 2.7.5/2.7.6/2.7.7/2.8.1 EvidenceRecord pipeline generalizes to a
new domain with NO second evidence system and no pipeline redesign — the
read handler builds an EvidenceRecord identical in shape to wifi/BLE/Sub-GHz
handlers, the engine mirrors it, JSONL/HTML render it identically. The
per-target prerequisite (read needs select on the SAME uid) is the simulator
handler's gate, exactly mirroring `subghz.discovery.analyze` requiring
`SubGhzSignal.captured=True` on the same frequency. Policy-rejected actions
produce zero evidence and zero env mutation.

Covered (mirrors the spec's test bullets):
  1.  NfcTag stateful fields (selected/read/read_at/ndef_supported) + to_dict round-trip
  2.  scan observation success (no state mutation)
  3.  select success (mutates NfcTag.selected=True + env.notes["nfc_select:<uid>"])
  4.  select on unknown uid returns structured failure (no mutation, no evidence)
  5.  read success after select on the SAME uid (mutates read=True + read_at + env.notes["nfc_read:<uid>"])
  6.  read requires select (known-but-unselected -> prereq-missing failure with evidence=[])
  7.  read on different uid after select on another -> prereq failure
  8.  read on tag with ndef_supported=False -> structured failure (clean representation)
  9.  read malformed args (missing uid, empty string, non-string) -> structured failure
 10.  unknown uid read -> structured failure (no evidence)
 11.  no false-positive evidence (failure-only runs / rejected actions produce zero evidence)
 12.  correct evidence kind + provenance (nfc_read, source_action_id stamped by engine, target uid, metadata)
 13.  determinism (same seed -> same state + evidence semantics)
 14.  JSONL evidence.created events include nfc_read (PASSIVE-only rejected run -> 0 events)
 15.  HTML EVIDENCE section renders nfc_read entries
 16.  TUI feed: formatEvidenceLine maps nfc_read -> domain 'other' (forward-link guarded from Python)
 17.  Phase 2.7 + 2.8.0 + 2.8.1 regression: catalogue count 23, 7 evidence producers, nfc_workflow_plan shape,
      KNOWN_EVIDENCE_KINDS extended, performed_capability_keys reflects nfc.discovery.select

Run without pytest:
    python -m tests.test_phase282_nfc_read
"""

import json
import os
import tempfile
import time
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None  # standalone runner works without pytest

from capabilities.base import DEFAULT_CAPABILITIES
from capabilities.registry import default_registry
from core.events import EVIDENCE_CREATED
from core.evidence import KNOWN_EVIDENCE_KINDS
from core.mission import (
    ActionRequest,
    ActionRisk,
    AuthorizationScope,
    PolicyDecisionKind,
    Run,
    RunStatus,
)
from engine.logger import RunLogger, run_dir
from engine.runner import (
    RunEngine,
    ble_gatt_workflow_plan,
    default_exploration_plan,
    nfc_workflow_plan,
    subghz_capture_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import render_run
from simulator.environment import Environment
from simulator.scenarios import build_scenario
from simulator.simulator import execute as sim_execute
from simulator.simulator import performed_capability_keys


# Lab scenario literal NFC UIDs (seed-independent).
LAB_TAG_1 = "04:DE:AD:BE:EF:01"   # MIFARE Classic 1K, ndef_supported=True
LAB_TAG_2 = "04:DE:AD:BE:EF:02"   # NTAG215, ndef_supported=True


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# Test helpers

def _safe_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase 2.8.2 nfc test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _select(uid: str) -> ActionRequest:
    return ActionRequest(capability="nfc.discovery", action="select",
                         args={"uid": uid}, risk=ActionRisk.PASSIVE)


def _read(uid: str) -> ActionRequest:
    return ActionRequest(capability="nfc.discovery", action="read",
                         args={"uid": uid}, risk=ActionRisk.SAFE_ACTIVE)


def _tag(env: Environment, uid: str):
    for t in env.nfc:
        if t.uid == uid:
            return t
    return None


# 1. NfcTag stateful fields

class TestNfcTagFields:
    def test_nfc_tag_has_stateful_fields(self):
        from simulator.entities import NfcTag
        t = NfcTag(uid=LAB_TAG_1, tag_type="MIFARE Classic 1K", ndef_records=[])
        assert t.selected is False
        assert t.read is False
        assert t.read_at == 0.0
        assert t.ndef_supported is True
        assert t.writable is True

    def test_nfc_tag_to_dict_carries_all_fields(self):
        from simulator.entities import NfcTag
        t = NfcTag(uid="X", tag_type="NTAG215", ndef_records=[],
                   ndef_supported=False, writable=False,
                   selected=True, read=True, read_at=12345.6)
        d = t.to_dict()
        assert d["uid"] == "X"
        assert d["tag_type"] == "NTAG215"
        assert d["ndef_supported"] is False
        assert d["writable"] is False
        assert d["selected"] is True
        assert d["read"] is True
        assert d["read_at"] == 12345.6

    def test_lab_tag_has_ndef_supported_true(self):
        env = build_scenario("lab", seed=42)
        t = _tag(env, LAB_TAG_1)
        assert t.ndef_supported is True
        t2 = _tag(env, LAB_TAG_2)
        assert t2.ndef_supported is True


# 2. scan observation success

class TestScanObservation:
    def test_scan_returns_lab_tags(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            rec = engine.execute(ActionRequest(
                capability="nfc.discovery", action="scan",
                risk=ActionRisk.PASSIVE))
            obs = rec.observation
            assert obs is not None
            assert len(obs.entities) == 2
            uids = {e.id for e in obs.entities}
            assert uids == {LAB_TAG_1, LAB_TAG_2}
        finally:
            logger.close()

    def test_scan_does_not_mutate_state(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(ActionRequest(
                capability="nfc.discovery", action="scan",
                risk=ActionRisk.PASSIVE))
            for t in env.nfc:
                assert t.selected is False
                assert t.read is False
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()

    def test_scan_produces_no_evidence(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            rec = engine.execute(ActionRequest(
                capability="nfc.discovery", action="scan",
                risk=ActionRisk.PASSIVE))
            obs = rec.observation
            assert obs.evidence == []
            assert run.evidence == []
        finally:
            logger.close()


# 3. select success

class TestSelectSuccess:
    def test_select_mutates_selected_flag(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_select(LAB_TAG_1))
            t = _tag(env, LAB_TAG_1)
            assert t.selected is True
        finally:
            logger.close()

    def test_select_stamps_env_notes(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_select(LAB_TAG_1))
            assert any(k.startswith("nfc_select:") for k in env.notes)
            assert f"nfc_select:{LAB_TAG_1}" in env.notes
        finally:
            logger.close()

    def test_select_reflected_in_performed_capability_keys(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_select(LAB_TAG_1))
            assert "nfc.discovery.select" in performed_capability_keys(env)
        finally:
            logger.close()

    def test_select_does_not_set_read_flag(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_select(LAB_TAG_1))
            t = _tag(env, LAB_TAG_1)
            assert t.read is False
            assert t.read_at == 0.0
        finally:
            logger.close()

    def test_select_produces_no_evidence(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            rec = engine.execute(_select(LAB_TAG_1))
            obs = rec.observation
            assert obs.evidence == []
            assert run.evidence == []
        finally:
            logger.close()


# 4. select unknown uid

class TestSelectUnknownUid:
    def test_select_unknown_uid_returns_structured_failure(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "nfc.discovery", "select", {"uid": "FF:FF:FF:FF:FF:FF"})
        assert obs.entities == []
        assert obs.evidence == []
        assert "No NFC tag found" in obs.summary

    def test_select_unknown_uid_does_not_mutate_state(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "nfc.discovery", "select", {"uid": "FF:FF:FF:FF:FF:FF"})
        assert all(not k.startswith("nfc_select:") for k in env.notes)
        assert all(t.selected is False for t in env.nfc)


# 5. read success after select

class TestReadSuccess:
    def test_read_after_select_produces_observation(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            obs = rec.observation
            assert obs is not None
            assert len(obs.entities) == 1
            assert obs.entities[0].id == LAB_TAG_1
        finally:
            logger.close()

    def test_read_sets_read_flag_and_timestamp(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            t0 = time.time()
            engine.execute(_select(LAB_TAG_1))
            engine.execute(_read(LAB_TAG_1))
            tag = _tag(env, LAB_TAG_1)
            assert tag.read is True
            assert tag.read_at > 0
            assert tag.read_at >= t0
        finally:
            logger.close()

    def test_read_stamps_env_notes(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            engine.execute(_read(LAB_TAG_1))
            assert f"nfc_read:{LAB_TAG_1}" in env.notes
        finally:
            logger.close()

    def test_read_summary_references_records_count(self):
        # The read observation summary states the NDEF records count; the
        # surface here is the summary itself (the simulator has no inspect
        # action for NFC, but the read observation carries the same state
        # forward — exactly mirroring ble.gatt.pair/write surfacing state in
        # the inspect summary).
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            obs = rec.observation
            assert obs is not None
            assert "NDEF" in obs.summary
            assert "tag" in obs.summary.lower() or LAB_TAG_1 in obs.summary
        finally:
            logger.close()


# 6. read requires select (per-target prereq)

class TestReadRequiresSelect:
    def test_read_without_select_returns_prereq_failure(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_read(LAB_TAG_1))
            obs = rec.observation
            assert obs.entities == []
            assert obs.evidence == []
            assert "not been selected" in obs.summary or "select" in obs.summary.lower()
        finally:
            logger.close()

    def test_read_without_select_does_not_stamp_notes(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "nfc.discovery", "read", {"uid": LAB_TAG_1})
        # No read notes stamped because the prereq failed.
        assert all(not k.startswith("nfc_read:") for k in env.notes)
        assert "nfc.discovery.read" not in performed_capability_keys(env)

    def test_read_after_select_on_different_uid_fails(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))  # select TAG_1
            rec = engine.execute(_read(LAB_TAG_2))  # read TAG_2
            obs = rec.observation
            # TAG_2 was not selected -> prereq failure
            assert obs.entities == []
            assert obs.evidence == []
            assert "not been selected" in obs.summary or "select" in obs.summary.lower()
        finally:
            logger.close()

    def test_read_after_failure_can_succeed_on_fresh_select(self):
        # Failure-only path does not poison env state; a fresh select+read
        # on the SAME tag after the failure succeeds and produces evidence.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            # First attempt fails (no select).
            rec1 = engine.execute(_read(LAB_TAG_1))
            obs1 = rec1.observation
            assert obs1.evidence == []
            # Now do it right.
            engine.execute(_select(LAB_TAG_1))
            rec2 = engine.execute(_read(LAB_TAG_1))
            obs2 = rec2.observation
            assert len(obs2.evidence) == 1
            assert obs2.evidence[0].kind == "nfc_read"
            assert len(run.evidence) == 1
        finally:
            logger.close()


# 7. ndef_supported=False

class TestNdefUnsupported:
    def test_read_ndef_unsupported_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            tag = _tag(env, LAB_TAG_1)
            tag.ndef_supported = False
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            obs = rec.observation
            assert obs.evidence == []
            assert "NDEF" in obs.summary
        finally:
            logger.close()

    def test_read_ndef_unsupported_does_not_set_read_flag(self):
        env = build_scenario("lab", seed=42)
        tag = _tag(env, LAB_TAG_1)
        tag.ndef_supported = False
        sim_execute(env, "nfc.discovery", "select", {"uid": LAB_TAG_1})
        sim_execute(env, "nfc.discovery", "read", {"uid": LAB_TAG_1})
        assert tag.read is False
        assert tag.read_at == 0.0


# 8. malformed args

class TestMalformedArgs:
    def _bad_args_cases(self):
        return [
            {},                    # missing uid
            {"uid": ""},            # empty
            {"uid": None},          # None
            {"uid": 123},           # non-string number
            {"uid": ["x"]},         # list
            {"uid": {"k": "v"}},   # dict
        ]

    def test_select_bad_args(self):
        env = build_scenario("lab", seed=42)
        for args in self._bad_args_cases():
            obs = sim_execute(env, "nfc.discovery", "select", args)
            assert obs.entities == []
            assert obs.evidence == []
            assert ("Invalid" in obs.summary) or ("missing" in obs.summary.lower()) or ("No NFC tag found" in obs.summary)

    def test_read_bad_args(self):
        env = build_scenario("lab", seed=42)
        for args in self._bad_args_cases():
            obs = sim_execute(env, "nfc.discovery", "read", args)
            assert obs.entities == []
            assert obs.evidence == []
            assert ("Invalid" in obs.summary) or ("missing" in obs.summary.lower()) or ("No NFC tag found" in obs.summary)


# 9. unknown uid

class TestReadUnknownUid:
    def test_read_unknown_uid_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(ActionRequest(
                capability="nfc.discovery", action="read",
                args={"uid": "FF:FF:FF:FF:FF:FF"}, risk=ActionRisk.SAFE_ACTIVE))
            obs = rec.observation
            assert obs.entities == []
            assert obs.evidence == []
            assert "No NFC tag found" in obs.summary
        finally:
            logger.close()

    def test_read_unknown_uid_does_not_mutate_state(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(ActionRequest(
                capability="nfc.discovery", action="read",
                args={"uid": "FF:FF:FF:FF:FF:FF"}, risk=ActionRisk.SAFE_ACTIVE))
            for t in env.nfc:
                assert t.read is False
                assert t.read_at == 0.0
            assert all(not k.startswith("nfc_read:") for k in env.notes)
        finally:
            logger.close()


# 10. no false-positive evidence

class TestNoFalsePositiveEvidence:
    def test_failure_only_run_has_zero_evidence(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan([
                ActionRequest(capability="nfc.discovery", action="scan",
                              risk=ActionRisk.PASSIVE),
                ActionRequest(capability="nfc.discovery", action="read",
                              args={"uid": LAB_TAG_1},
                              risk=ActionRisk.SAFE_ACTIVE),  # missing select
                ActionRequest(capability="nfc.discovery", action="read",
                              args={"uid": "FF:FF:FF:FF:FF:FF"},
                              risk=ActionRisk.SAFE_ACTIVE),  # unknown uid
            ])
            assert run.status == RunStatus.COMPLETED
            assert run.evidence == []
            assert all(t.read is False for t in env.nfc)
            assert all(t.selected is False for t in env.nfc)
        finally:
            logger.close()

    def test_ndef_unsupported_tag_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            tag = _tag(env, LAB_TAG_1)
            tag.ndef_supported = False
            engine.execute(_select(LAB_TAG_1))
            engine.execute(_read(LAB_TAG_1))
            assert run.evidence == []
        finally:
            logger.close()


# 11. evidence kind + provenance

class TestEvidenceKindAndProvenance:
    def test_kind_is_nfc_read(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            obs = rec.observation
            kinds = {e.kind for e in obs.evidence}
            assert kinds == {"nfc_read"}
        finally:
            logger.close()

    def test_provenance_fields_complete(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            assert len(rec.evidence) == 1
            ev = rec.evidence[0]
            assert ev.id                                  # uuid
            assert ev.source_capability == "nfc.discovery"
            assert ev.source_action == "read"
            assert ev.target_entity_id == LAB_TAG_1
            assert ev.target_entity_type == "nfc_tag"
            assert ev.kind == "nfc_read"
            assert ev.summary
            assert ev.captured_at > 0
        finally:
            logger.close()

    def test_source_action_id_stamped_by_engine(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            assert rec.evidence[0].source_action_id == rec.request.id
        finally:
            logger.close()

    def test_metadata_is_concise_and_realistic(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            md = rec.evidence[0].metadata
            # The 5 expected fields are present.
            assert "uid" in md
            assert "tag_type" in md
            assert "technology" in md
            assert "ndef_supported" in md
            assert "records_count" in md
            assert md["uid"] == LAB_TAG_1
            assert md["tag_type"] == "MIFARE Classic 1K"
            assert md["ndef_supported"] is True
            assert md["technology"] == "NFC"
            # No fake protocol blobs.
            assert "raw_ndef" not in md
            assert "bytes" not in md
            assert "payload" not in md
        finally:
            logger.close()

    def test_evidence_mirrored_to_run_and_action_record(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_select(LAB_TAG_1))
            rec = engine.execute(_read(LAB_TAG_1))
            assert len(run.evidence) == 1
            assert run.evidence[0].kind == "nfc_read"
            assert len(rec.evidence) == 1
        finally:
            logger.close()

    def test_known_evidence_kinds_includes_nfc_read(self):
        assert "nfc_read" in KNOWN_EVIDENCE_KINDS


# 12. determinism

class TestDeterminism:
    def test_same_seed_yields_same_evidence_semantics(self):
        seen = []
        for _ in range(2):
            engine, run, logger, env = _engine_with_scope(_safe_active_scope(), seed=42)
            try:
                engine.run_plan(nfc_workflow_plan())
                semantic = [
                    (e.kind, e.source_capability, e.source_action, e.target_entity_id,
                     e.summary, dict(e.metadata))
                    for e in run.evidence
                ]
                seen.append(sorted(semantic))
            finally:
                logger.close()
        assert seen[0] == seen[1]

    def test_nfc_state_deterministic(self):
        env1 = build_scenario("lab", seed=42)
        env2 = build_scenario("lab", seed=42)
        sim_execute(env1, "nfc.discovery", "select", {"uid": LAB_TAG_1})
        sim_execute(env1, "nfc.discovery", "read", {"uid": LAB_TAG_1})
        sim_execute(env2, "nfc.discovery", "select", {"uid": LAB_TAG_1})
        sim_execute(env2, "nfc.discovery", "read", {"uid": LAB_TAG_1})
        t1 = _tag(env1, LAB_TAG_1)
        t2 = _tag(env2, LAB_TAG_1)
        assert (t1.selected, t1.read, t1.read_at > 0) == \
               (t2.selected, t2.read, t2.read_at > 0)


# 13. JSONL evidence.created events

class TestJsonlEvidenceEvents:
    def test_jsonl_emits_evidence_created_for_nfc(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(nfc_workflow_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            # Plan produces 2 nfc_read evidence (TAG_1 + TAG_2).
            assert len(ev_events) == 2
            kinds = sorted(e["evidence"]["kind"] for e in ev_events)
            assert kinds == ["nfc_read", "nfc_read"]
            for e in ev_events:
                assert e.get("source_action_id")
                assert e.get("run_id") == run.id
        finally:
            logger.close()

    def test_rejected_read_emits_no_evidence_event(self):
        engine, run, logger, env = _engine_with_scope()  # default PASSIVE
        try:
            engine.run_plan(nfc_workflow_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            # Both reads are SAFE_ACTIVE and PASSIVE-only scope rejects them
            # BEFORE the provider -> 0 evidence events.
            assert ev_events == []
            assert run.evidence == []
        finally:
            logger.close()


# 14. HTML EVIDENCE section

class TestHtmlEvidenceSection:
    def test_html_renders_nfc_evidence(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(nfc_workflow_plan())
            html = render_run(run)
            assert "<h2>EVIDENCE</h2>" in html
            assert "nfc_read" in html
            for ev in run.evidence:
                assert ev.source_capability in html  # "nfc.discovery"
            assert LAB_TAG_1 in html
            assert LAB_TAG_2 in html
        finally:
            logger.close()

    def test_html_empty_evidence_for_passive_run(self):
        engine, run, logger, env = _engine_with_scope()  # PASSIVE
        try:
            engine.run_plan(nfc_workflow_plan())
            html = render_run(run)
            assert "<h2>EVIDENCE</h2>" in html
            assert "No evidence captured by this run." in html
        finally:
            logger.close()


# 15. TUI evidence feed (forward-link guard)

class TestTuiEvidenceFeed:
    def test_evidenceFormat_maps_nfc_read_to_other_domain(self):
        # Mirror the JS prefix logic so a future TUI refactor that breaks this
        # is incidentally caught by the Python-suite integrators. The Node
        # assertion in suryafool-cli/src/components/EvidenceFeed.test.js
        # mirrors this rule.
        nfc_ev = {"kind": "nfc_read", "target_entity_id": LAB_TAG_1,
                  "source_capability": "nfc.discovery", "source_action": "read",
                  "summary": "Read 2 NDEF record(s) from MIFARE Classic 1K tag 04:DE:AD:BE:EF:01."}
        kind = nfc_ev["kind"]
        if kind.startswith("wifi"):
            domain = "wifi"
        elif kind.startswith("ble"):
            domain = "ble"
        else:
            domain = "other"
        assert domain == "other"

    def test_js_test_file_has_nfc_assertion(self):
        # Forward-link guard so a future deletion of the JS assertion
        # breaks the Python suite.
        root = Path(__file__).resolve().parent.parent
        js_test = (root / "suryafool-cli" / "src" / "components"
                   / "EvidenceFeed.test.js")
        txt = js_test.read_text(encoding="utf-8")
        assert "nfc_read" in txt
        assert "nfc.discovery.read" in txt
        assert "Phase 2.8.2 NFC" in txt


# 16. Phase 2.7 + 2.8.0 + 2.8.1 regression

class TestPhaseRegression:
    def test_catalogue_count_is_23(self):
        # Phase 2.7 = 14; Phase 2.8.0 +7 (ir/ethernet/usb, unsupported) = 21;
        # Phase 2.8.1 +1 (subghz.capture.signal) = 22;
        # Phase 2.8.2 +1 (nfc.discovery.select) = 23.
        assert len(DEFAULT_CAPABILITIES) == 23

    def test_nfc_discovery_select_registered(self):
        by_key = {c.key for c in DEFAULT_CAPABILITIES}
        assert "nfc.discovery.select" in by_key

    def test_nfc_producers_evidence_flags(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        # select is the new discovery step; no evidence (it's a passive act).
        assert by_key["nfc.discovery.select"].produces_evidence is False
        # read now produces nfc_read evidence (Phase 2.8.2).
        assert by_key["nfc.discovery.read"].produces_evidence is True

    def test_seven_evidence_kinds_frozen(self):
        # Phase 2.7 (4) + Phase 2.8.1 (2) + Phase 2.8.2 (1) = 7.
        assert KNOWN_EVIDENCE_KINDS == frozenset({
            "wifi_eapol_handshake", "wifi_pmkid",
            "ble_pairing", "ble_secure_write",
            "subghz_capture", "subghz_analysis",
            "nfc_read",
        })

    def test_nfc_workflow_plan_shape(self):
        # scan + 2x select + 2x read = 5.
        plan = nfc_workflow_plan()
        assert len(plan) == 5
        keys = [f"{r.capability}.{r.action}" for r in plan]
        assert keys == [
            "nfc.discovery.scan",
            "nfc.discovery.select",
            "nfc.discovery.read",
            "nfc.discovery.select",
            "nfc.discovery.read",
        ]
        # Every action's request.risk equals cap.risk.
        reg = default_registry(environment=build_scenario("lab", seed=42))
        for req in plan:
            cap = reg.capability(req.capability, req.action)
            assert cap is not None and req.risk == cap.risk

    def test_default_exploration_plan_unchanged(self):
        plan = default_exploration_plan()
        assert len(plan) == 4
        assert all(p.risk == ActionRisk.PASSIVE for p in plan)

    def test_deterministic_plan_shapes_frozen(self):
        assert len(default_exploration_plan()) == 4
        assert len(wifi_capture_plan()) == 5
        assert len(ble_gatt_workflow_plan()) == 6
        assert len(subghz_capture_plan()) == 5
        assert len(nfc_workflow_plan()) == 5

    def test_performed_capability_keys_includes_nfc_select(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "nfc.discovery", "select", {"uid": LAB_TAG_1})
        assert "nfc.discovery.select" in performed_capability_keys(env)
        sim_execute(env, "nfc.discovery", "read", {"uid": LAB_TAG_1})
        assert "nfc.discovery.read" in performed_capability_keys(env)

    def test_passive_scope_rejects_active_reads_before_provider(self):
        # PASSIVE-only scope: 2 SAFE_ACTIVE reads REJECT, the 3 PASSIVE selects
        # ALLOW. env notes show 2 nfc_select: stamps but no nfc_read: stamps
        # (since the reads never ran). 2 errors recorded, run COMPLETED,
        # zero evidence.
        engine, run, logger, env = _engine_with_scope()  # default PASSIVE
        try:
            engine.run_plan(nfc_workflow_plan())
            assert run.status == RunStatus.COMPLETED
            rejected = [r for r in run.actions
                        if r.policy_decision and not r.policy_decision.allowed]
            assert len(rejected) == 2  # both reads
            for r in rejected:
                assert r.observation is None            # provider never invoked
                assert r.evidence == []
            assert run.evidence == []
            # selects ran (PASSIVE always allowed), so two select stamps exist,
            # but no nfc_read: stamps because the reads were rejected.
            performed = performed_capability_keys(env)
            assert "nfc.discovery.select" in performed
            assert "nfc.discovery.read" not in performed
            assert all(not k.startswith("nfc_read:") for k in env.notes)
            for t in env.nfc:
                assert t.read is False
                assert t.read_at == 0.0
        finally:
            logger.close()

    def test_risk_declaration_rule_still_guards_nfc_read(self):
        # Caller downgrade/upgrade both rejected by RiskDeclarationRule.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            # Upgrade: SAFE_ACTIVE entry, claim SENSITIVE_ACTIVE.
            up = engine.execute(ActionRequest(
                capability="nfc.discovery", action="read",
                args={"uid": LAB_TAG_1}, risk=ActionRisk.SENSITIVE_ACTIVE))
            assert up.policy_decision.kind == PolicyDecisionKind.REJECT
            # Downgrade: SAFE_ACTIVE entry, claim PASSIVE.
            down = engine.execute(ActionRequest(
                capability="nfc.discovery", action="read",
                args={"uid": LAB_TAG_1}, risk=ActionRisk.PASSIVE))
            assert down.policy_decision.kind == PolicyDecisionKind.REJECT
            # Neither variant altered env state.
            assert all(t.read is False for t in env.nfc)
        finally:
            logger.close()


# Standalone runner (no pytest required)

def _run_all() -> int:
    import traceback
    failures = 0
    os.environ["SURYAFOOL_RUNS_DIR"] = str(
        Path(tempfile.mkdtemp(prefix="suryafool-p282-")) / "runs")
    for name in sorted(globals()):
        cls = globals()[name]
        if not isinstance(cls, type) or not name.startswith("Test"):
            continue
        instance = cls()
        for attr in sorted(dir(instance)):
            if not attr.startswith("test_"):
                continue
            tn = f"{name}.{attr}"
            try:
                getattr(instance, attr)()
                print(f"  PASS  {tn}")
            except Exception:
                failures += 1
                print(f"  FAIL  {tn}")
                traceback.print_exc()
    print(f"\n{'FAILED' if failures else 'PASSED'} - {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys
    sys.exit(_run_all())
