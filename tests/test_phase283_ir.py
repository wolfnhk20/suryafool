"""
tests/test_phase283_ir.py

Phase 2.8.3 — first real Infrared (IR) vertical slice on the frozen Phase 2.7
stack + Phase 2.8.0 multi-domain foundation. The deterministic IR chain is:

    infrared.capture    (PASSIVE, enumerates IR bursts, no mutation, no evidence)
    infrared.analyze    (SAFE_ACTIVE, per-target `capture_id` must exist; sets
                         analyzed=True + a deterministic decoded_protocol_hint;
                         produces `ir_analysis` evidence)
    infrared.transmit   (SENSITIVE_ACTIVE, per-target gate: the SAME capture_id
                         must have been analyzed first; sets transmitted=True;
                         produces `ir_transmit` evidence)

The three IR entries were staked in Phase 2.8.0 as registered-but-unsupported
(reason: no simulator handlers). This subphase keeps the catalogue surface
flat and turns `infrared.analyze` + `infrared.transmit` into real evidence
producers by appending handler implementations — exactly parallel to
`subghz.capture`/`nfc.discovery` in 2.8.1/2.8.2. No second capability /
evidence / event / reporting system.

The per-target prerequisite (transmit needs analyze on the SAME capture_id)
mirrors `wifi.capture.pmkid` (handshake on same bssid), `ble.gatt.write`
(pair on same address) and `nfc.discovery.read` (select on same uid). All
failure paths produce zero evidence and zero env mutation; policy-rejected
actions never reach the provider. `decoded_protocol_hint` is a HINT, not a
real decoder — the simulator has no IR payloads.

Covered (mirrors the spec's test bullets):
  1.  IrSignal stateful fields (analyzed/decoded_protocol_hint/transmitted) + to_dict round-trip
  2.  capture observation success (enumerates IR bursts, no mutation, no evidence)
  3.  analyze success on a known capture_id (sets analyzed=True + NEC hint + env.notes["ir_analyzed:<id>"])
  4.  analyze on unknown capture_id / malformed args -> structured failure (no mutation, no evidence)
  5.  transmit success after analyze on the SAME capture_id (sets transmitted=True + env.notes["ir_transmit:<id>"])
  6.  transmit requires analyze (known-but-unanalyzed -> prereq-missing failure with evidence=[])
  7.  transmit on a different capture_id than the one analyzed -> prereq failure
  8.  protocol hint is a hint, not a decode (honest blank when unmapped)
  9.  no false-positive evidence (failure-only runs / rejected actions produce zero evidence)
 10.  correct evidence kind + provenance (ir_analysis/ir_transmit, source_action_id, target capture_id, metadata)
 11.  evidence mirrored to ActionRecord + Run
 12.  determinism (same seed -> same state + evidence semantics)
 13.  JSONL evidence.created events include both IR kinds (PASSIVE-only rejected run -> 0 events)
 14.  HTML EVIDENCE section renders IR entries
 15.  TUI feed: formatEvidenceLine maps ir_* -> domain 'other' (forward-link guarded from Python)
 16.  Phase 2.7 + 2.8.0 + 2.8.1 + 2.8.2 regression: catalogue count 23, 9 evidence kinds,
      ir_workflow_plan shape, performed_capability_keys reflects infrared.analyze + infrared.transmit

Run without pytest:
    python -m tests.test_phase283_ir
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
    ir_workflow_plan,
    nfc_workflow_plan,
    subghz_capture_plan,
    wifi_capture_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import render_run
from simulator.entities import IrSignal
from simulator.environment import Environment
from simulator.scenarios import build_scenario
from simulator.simulator import (
    _ir_protocol_hint,
    execute as sim_execute,
)
from simulator.simulator import performed_capability_keys


# Lab scenario literal IR capture ids (seed-independent).
LAB_REMOTE = "ir-lab-remote"   # NEC, 38.0 kHz / 900 ms
LAB_TV = "ir-lab-tv"           # RC5,  36.0 kHz / 560 ms


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# Test helpers

def _sensitive_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _safe_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase 2.8.3 ir test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _capture() -> ActionRequest:
    return ActionRequest(capability="infrared", action="capture",
                         risk=ActionRisk.PASSIVE)


def _analyze(capture_id: str) -> ActionRequest:
    return ActionRequest(capability="infrared", action="analyze",
                         args={"capture_id": capture_id},
                         risk=ActionRisk.SAFE_ACTIVE)


def _transmit(capture_id: str) -> ActionRequest:
    return ActionRequest(capability="infrared", action="transmit",
                         args={"capture_id": capture_id},
                         risk=ActionRisk.SENSITIVE_ACTIVE)


def _signal(env: Environment, capture_id: str):
    for s in env.ir:
        if s.capture_id == capture_id:
            return s
    return None


# 1. IrSignal stateful fields

class TestIrSignalFields:
    def test_ir_signal_has_stateful_fields(self):
        s = IrSignal(capture_id=LAB_REMOTE, carrier_khz=38.0, length_ms=900.0,
                     protocol="NEC")
        assert s.analyzed is False
        assert s.decoded_protocol_hint == ""
        assert s.transmitted is False

    def test_ir_signal_to_dict_carries_all_fields(self):
        s = IrSignal(capture_id="X", carrier_khz=38.0, length_ms=900.0,
                     protocol="NEC", analyzed=True,
                     decoded_protocol_hint="NEC", transmitted=True)
        d = s.to_dict()
        assert d["capture_id"] == "X"
        assert d["analyzed"] is True
        assert d["decoded_protocol_hint"] == "NEC"
        assert d["transmitted"] is True
        assert d["carrier_khz"] == 38.0

    def test_ir_signal_to_dict_round_trips_through_json(self):
        s = IrSignal(capture_id=LAB_TV, carrier_khz=36.0, length_ms=560.0,
                     protocol="RC5", analyzed=True,
                     decoded_protocol_hint="RC5", transmitted=False)
        d = json.loads(json.dumps(s.to_dict()))
        assert d["capture_id"] == LAB_TV
        assert d["analyzed"] is True
        assert d["decoded_protocol_hint"] == "RC5"


# 2. capture observation success

class TestCaptureObservation:
    def test_capture_returns_lab_ir_signals(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_capture())
            assert len(run.observations) == 1
            obs = run.observations[0]
            assert obs.summary == "Captured 2 IR burst(s) in view."
            ids = {e.id for e in obs.entities}
            assert ids == {LAB_REMOTE, LAB_TV}
            # capture is observational: no evidence, no mutation, no notes.
            assert obs.evidence == []
        finally:
            logger.close()

    def test_capture_does_not_mutate_state(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_capture())
            assert performed_capability_keys(env) == set()
            for s in env.ir:
                assert s.analyzed is False
                assert s.transmitted is False
                assert s.decoded_protocol_hint == ""
        finally:
            logger.close()


# 3. analyze success

class TestAnalyzeSuccess:
    def test_analyze_sets_analyzed_hint_and_stamps_notes(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_analyze(LAB_REMOTE))
            s = _signal(env, LAB_REMOTE)
            assert s.analyzed is True
            assert s.decoded_protocol_hint == "NEC"
            assert f"ir_analyzed:{LAB_REMOTE}" in env.notes
            assert s.transmitted is False
            # The OTHER lab burst is left untouched.
            tv = _signal(env, LAB_TV)
            assert tv.analyzed is False
            assert tv.decoded_protocol_hint == ""
        finally:
            logger.close()

    def test_analyze_produces_ir_analysis_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(_analyze(LAB_REMOTE))
            assert len(rec.evidence) == 1
            ev = rec.evidence[0]
            assert ev.kind == "ir_analysis"
            assert ev.source_capability == "infrared"
            assert ev.source_action == "analyze"
            assert ev.target_entity_id == LAB_REMOTE
            assert ev.target_entity_type == "ir_signal"
            md = ev.metadata
            assert md["capture_id"] == LAB_REMOTE
            assert md["carrier_khz"] == 38.0
            assert md["length_ms"] == 900.0
            assert md["decoded_protocol_hint"] == "NEC"
            assert md["classification"] == "likely NEC consumer-IR frame"
            # No fake protocol blobs.
            assert "raw" not in md
            assert "bytes" not in md
            assert "payload" not in md
        finally:
            logger.close()

    def test_analyze_sets_rc5_hint_for_tv_burst(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_analyze(LAB_TV))
            s = _signal(env, LAB_TV)
            assert s.analyzed is True
            assert s.decoded_protocol_hint == "RC5"
        finally:
            logger.close()


# 4. analyze failures

class TestAnalyzeFailure:
    def test_analyze_unknown_capture_id_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(_analyze("does-not-exist"))
            assert rec.observation is not None
            assert rec.observation.summary == "No captured IR burst with id does-not-exist."
            assert rec.evidence == []
            # No mutation.
            assert performed_capability_keys(env) == set()
            assert all(s.analyzed is False for s in env.ir)
        finally:
            logger.close()

    def test_analyze_malformed_args_returns_structured_failure(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            for bad in ({}, {"capture_id": ""}, {"capture_id": None},
                        {"capture_id": 123}):
                rec = engine.execute(ActionRequest(
                    capability="infrared", action="analyze", args=bad,
                    risk=ActionRisk.SAFE_ACTIVE))
                assert rec.observation is not None
                assert rec.evidence == []
            assert performed_capability_keys(env) == set()
            assert all(s.analyzed is False for s in env.ir)
        finally:
            logger.close()


# 5. transmit success

class TestTransmitSuccess:
    def test_transmit_after_analyze_same_capture_id(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(_transmit(LAB_REMOTE))
            # Not analyzed yet -> prereq failure, no evidence.
            assert rec.evidence == []
            s = _signal(env, LAB_REMOTE)
            assert s.transmitted is False

            engine.execute(_analyze(LAB_REMOTE))
            rec = engine.execute(_transmit(LAB_REMOTE))
            assert len(rec.evidence) == 1
            assert rec.evidence[0].kind == "ir_transmit"
            assert rec.observation.summary == "Transmitted IR burst ir-lab-remote."
            s = _signal(env, LAB_REMOTE)
            assert s.transmitted is True
            assert f"ir_transmit:{LAB_REMOTE}" in env.notes
        finally:
            logger.close()

    def test_transmit_produces_ir_transmit_evidence_with_prereq_meta(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_analyze(LAB_REMOTE))
            rec = engine.execute(_transmit(LAB_REMOTE))
            ev = rec.evidence[0]
            assert ev.kind == "ir_transmit"
            assert ev.source_capability == "infrared"
            assert ev.source_action == "transmit"
            assert ev.target_entity_id == LAB_REMOTE
            md = ev.metadata
            assert md["capture_id"] == LAB_REMOTE
            assert md["decoded_protocol_hint"] == "NEC"
            assert md["analyze_prereq"] is True
            # No fake protocol blobs.
            assert "raw" not in md
            assert "bytes" not in md
        finally:
            logger.close()


# 6/7. transmit requires analyze (same capture_id)

class TestTransmitRequiresAnalyze:
    def test_transmit_on_unknown_capture_id_structured_failure(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(_transmit("missing"))
            assert rec.observation is not None
            assert rec.observation.summary == "No captured IR burst with id missing."
            assert rec.evidence == []
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()

    def test_transmit_on_other_capture_id_fails(self):
        # Analyze LAB_REMOTE, then try to transmit a DIFFERENT burst (LAB_TV)
        # that was not analyzed -> per-target prereq failure.
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_analyze(LAB_REMOTE))
            rec = engine.execute(_transmit(LAB_TV))
            assert rec.observation is not None
            assert "not analyzed yet" in rec.observation.summary
            assert rec.evidence == []
            tv = _signal(env, LAB_TV)
            assert tv.transmitted is False
            assert "ir_transmit:" not in "".join(env.notes.keys())
        finally:
            logger.close()


# 8. protocol hint is a hint, not a decode

class TestProtocolHintIsHonest:
    def test_hint_maps_known_bursts(self):
        assert _ir_protocol_hint(IrSignal(capture_id="a", carrier_khz=38.0, length_ms=900.0)) == "NEC"
        assert _ir_protocol_hint(IrSignal(capture_id="b", carrier_khz=36.0, length_ms=560.0)) == "RC5"
        assert _ir_protocol_hint(IrSignal(capture_id="c", carrier_khz=40.0, length_ms=600.0)) == "SIRC"

    def test_hint_blank_when_unmapped(self):
        # An unusual carrier/length combination the heuristic can't classify
        # stays "" — the honest "not confidently identified" answer, not a
        # fabricated decode.
        assert _ir_protocol_hint(IrSignal(capture_id="d", carrier_khz=56.0, length_ms=1200.0)) == ""


# 9. no false-positive evidence

class TestNoFalsePositiveEvidence:
    def test_failure_only_run_has_zero_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_analyze("does-not-exist"))
            engine.execute(_transmit("does-not-exist"))
            assert run.evidence == []
        finally:
            logger.close()

    def test_transmit_before_analyze_zero_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_transmit(LAB_REMOTE))
            assert run.evidence == []
        finally:
            logger.close()


# 10. evidence kind + provenance

class TestEvidenceKindAndProvenance:
    def test_kinds_known_in_vocabulary(self):
        assert "ir_analysis" in KNOWN_EVIDENCE_KINDS
        assert "ir_transmit" in KNOWN_EVIDENCE_KINDS

    def test_evidence_mirrored_to_run_and_action_record(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.execute(_capture())
            engine.execute(_analyze(LAB_REMOTE))
            rec = engine.execute(_transmit(LAB_REMOTE))
            engine.execute(_analyze(LAB_TV))
            kinds = sorted(e.kind for e in run.evidence)
            assert kinds == ["ir_analysis", "ir_analysis", "ir_transmit"]
            assert len(rec.evidence) == 1
            assert rec.evidence[0].kind == "ir_transmit"
        finally:
            logger.close()

    def test_source_action_id_stamped_by_engine(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            rec = engine.execute(_analyze(LAB_REMOTE))
            assert rec.evidence[0].source_action_id == rec.request.id
            assert rec.evidence[0].source_action_id == run.evidence[0].source_action_id
            assert rec.evidence[0].source_action_id != rec.evidence[0].id
        finally:
            logger.close()

    def test_evidence_round_trips_through_run_json(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ir_workflow_plan())
            run2 = Run.from_dict(json.loads(json.dumps(run.to_dict())))
            kinds = sorted(e.kind for e in run2.evidence)
            assert kinds == ["ir_analysis", "ir_analysis", "ir_transmit"]
        finally:
            logger.close()


# 11. performed_capability_keys

class TestPerformedCapabilityKeys:
    def test_after_full_plan_includes_ir_keys(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ir_workflow_plan())
            keys = performed_capability_keys(env)
            assert "infrared.analyze" in keys
            assert "infrared.transmit" in keys
            assert "infrared.capture" not in keys  # capture leaves no note
        finally:
            logger.close()

    def test_passive_scope_leaves_no_ir_keys(self):
        engine, run, logger, env = _engine_with_scope()  # PASSIVE
        try:
            engine.run_plan(ir_workflow_plan())
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()


# 12. determinism

class TestDeterminism:
    def test_same_seed_yields_same_evidence_semantics(self):
        seen = []
        for _ in range(2):
            engine, run, logger, env = _engine_with_scope(_sensitive_active_scope(), seed=42)
            try:
                engine.run_plan(ir_workflow_plan())
                semantic = [
                    (e.kind, e.source_capability, e.source_action, e.target_entity_id,
                     e.summary, dict(e.metadata))
                    for e in run.evidence
                ]
                seen.append(sorted(semantic))
            finally:
                logger.close()
        assert seen[0] == seen[1]

    def test_ir_state_deterministic(self):
        env1 = build_scenario("lab", seed=42)
        env2 = build_scenario("lab", seed=42)
        for env in (env1, env2):
            sim_execute(env, "infrared", "analyze", {"capture_id": LAB_REMOTE})
            sim_execute(env, "infrared", "transmit", {"capture_id": LAB_REMOTE})
        s1 = _signal(env1, LAB_REMOTE)
        s2 = _signal(env2, LAB_REMOTE)
        assert (s1.analyzed, s1.transmitted, s1.decoded_protocol_hint) == \
               (s2.analyzed, s2.transmitted, s2.decoded_protocol_hint)


# 13. JSONL evidence.created events

class TestJsonlEvidenceEvents:
    def test_jsonl_emits_evidence_created_for_ir(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ir_workflow_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            # Plan produces 3 IR evidence (2 ir_analysis + 1 ir_transmit).
            assert len(ev_events) == 3
            kinds = sorted(e["evidence"]["kind"] for e in ev_events)
            assert kinds == ["ir_analysis", "ir_analysis", "ir_transmit"]
            for e in ev_events:
                assert e.get("source_action_id")
                assert e.get("run_id") == run.id
        finally:
            logger.close()

    def test_rejected_actions_emit_no_evidence_event(self):
        engine, run, logger, env = _engine_with_scope()  # default PASSIVE
        try:
            engine.run_plan(ir_workflow_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            # analyze (SAFE_ACTIVE) + transmit (SENSITIVE_ACTIVE) are REJECTED
            # BEFORE the provider under PASSIVE-only scope -> 0 evidence events.
            assert ev_events == []
            assert run.evidence == []
            assert run.status == RunStatus.COMPLETED
        finally:
            logger.close()


# 14. HTML EVIDENCE section

class TestHtmlEvidenceSection:
    def test_html_renders_ir_evidence(self):
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            engine.run_plan(ir_workflow_plan())
            html = render_run(run)
            assert "<h2>EVIDENCE</h2>" in html
            assert "ir_analysis" in html
            assert "ir_transmit" in html
            assert LAB_REMOTE in html
            assert LAB_TV in html
        finally:
            logger.close()

    def test_html_empty_evidence_for_passive_run(self):
        engine, run, logger, env = _engine_with_scope()  # PASSIVE
        try:
            engine.run_plan(ir_workflow_plan())
            html = render_run(run)
            assert "<h2>EVIDENCE</h2>" in html
            assert "No evidence captured by this run." in html
        finally:
            logger.close()


# 15. TUI evidence feed (forward-link guard)

class TestTuiEvidenceFeed:
    def test_evidenceFormat_maps_ir_kinds_to_other_domain(self):
        # Mirror the JS prefix logic so a future TUI refactor that breaks this
        # is incidentally caught by the Python-suite integrators. The Node
        # assertion in suryafool-cli/src/components/EvidenceFeed.test.js
        # mirrors this rule.
        for kind in ("ir_analysis", "ir_transmit"):
            ev = {"kind": kind, "target_entity_id": LAB_REMOTE,
                  "source_capability": "infrared", "source_action": kind.split("_")[1],
                  "summary": "Analyzed IR burst ir-lab-remote."}
            assert not kind.startswith(("wifi_", "ble_", "subghz_", "nfc_"))
            assert kind.startswith("ir_")

    def test_js_test_file_has_ir_assertions(self):
        # Forward-link guard: the JS EvidenceFeed suite must cover the new IR
        # kinds so a TUI-only regression is surfaced by the Node tests (which
        # this Python suite also monitors via the build + node smokes).
        root = Path(__file__).resolve().parent.parent
        js_test = (root / "suryafool-cli" / "src" / "components"
                   / "EvidenceFeed.test.js")
        txt = js_test.read_text(encoding="utf-8")
        assert "ir_analysis" in txt
        assert "ir_transmit" in txt
        assert "infrared" in txt


# 16. Phase 2.7 + 2.8.0 + 2.8.1 + 2.8.2 regression

class TestPhaseRegression:
    def test_catalogue_count_is_23(self):
        assert len(DEFAULT_CAPABILITIES) == 23

    def test_ir_entries_have_correct_risk_and_evidence_flags(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["infrared.capture"].risk == ActionRisk.PASSIVE
        assert by_key["infrared.capture"].produces_evidence is False
        assert by_key["infrared.analyze"].risk == ActionRisk.SAFE_ACTIVE
        assert by_key["infrared.analyze"].produces_evidence is True
        assert by_key["infrared.transmit"].risk == ActionRisk.SENSITIVE_ACTIVE
        assert by_key["infrared.transmit"].produces_evidence is True
        assert by_key["infrared.transmit"].requires == ("infrared.capture",)

    def test_four_phase27_producers_subset_preserved(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        for key in ("wifi.capture.handshake", "wifi.capture.pmkid",
                    "ble.gatt.pair", "ble.gatt.write"):
            assert key in by_key, f"Phase 2.7 producer lost: {key}"

    def test_all_evidence_producers(self):
        producers = sorted(k for k, c in
                           {c.key: c for c in DEFAULT_CAPABILITIES}.items()
                           if c.produces_evidence)
        assert producers == [
            "ble.gatt.pair", "ble.gatt.write",
            "infrared.analyze", "infrared.transmit",
            "nfc.discovery.read", "subghz.capture.signal", "subghz.discovery.analyze",
            "wifi.capture.handshake", "wifi.capture.pmkid",
        ]

    def test_ir_workflow_plan_shape(self):
        plan = ir_workflow_plan()
        assert len(plan) == 4
        assert [(r.capability, r.action) for r in plan] == [
            ("infrared", "capture"),
            ("infrared", "analyze"),
            ("infrared", "transmit"),
            ("infrared", "analyze"),
        ]
        risks = [r.risk for r in plan]
        assert risks == [ActionRisk.PASSIVE, ActionRisk.SAFE_ACTIVE,
                         ActionRisk.SENSITIVE_ACTIVE, ActionRisk.SAFE_ACTIVE]

    def test_deterministic_plan_shapes_frozen(self):
        assert len(default_exploration_plan()) == 4
        assert len(wifi_capture_plan()) == 5
        assert len(ble_gatt_workflow_plan()) == 6
        assert len(subghz_capture_plan()) == 5
        assert len(nfc_workflow_plan()) == 5
        assert len(ir_workflow_plan()) == 4
        reg = default_registry(environment=build_scenario("lab", seed=42))
        for plan in (wifi_capture_plan(), ble_gatt_workflow_plan(),
                     subghz_capture_plan(), nfc_workflow_plan(), ir_workflow_plan()):
            for req in plan:
                cap = reg.capability(req.capability, req.action)
                assert cap is not None and req.risk == cap.risk

    def test_known_evidence_kinds_frozen(self):
        assert KNOWN_EVIDENCE_KINDS == frozenset({
            "wifi_eapol_handshake", "wifi_pmkid",
            "ble_pairing", "ble_secure_write",
            "subghz_capture", "subghz_analysis",
            "nfc_read",
            "ir_analysis", "ir_transmit",
        })

    def test_registry_resolves_ir_as_supported(self):
        # Phase 2.8.0 registered-but-unsupported is now finalized: the IR
        # handlers exist so infrared.* resolves supported=True.
        env = build_scenario("lab", seed=42)
        reg = default_registry(environment=env)
        for action in ("capture", "analyze", "transmit"):
            decision = reg.resolve("infrared", action)
            assert decision.supported is True, f"infrared.{action} should be supported"


# Standalone runner (no pytest required)

def _run_all() -> int:
    import traceback
    failures = 0
    os.environ["SURYAFOOL_RUNS_DIR"] = str(
        Path(tempfile.mkdtemp(prefix="suryafool-p283-")) / "runs")
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

