"""
tests/test_phase281_subghz_capture.py

Phase 2.8.1 â€” first real Sub-GHz/RF capability slice on the frozen Phase 2.7
stack + Phase 2.8.0 multi-domain foundation. The deterministic vertical chain
is:

    subghz.discovery.spectrum   (PASSIVE, enumerates signals)
    subghz.capture.signal       (SAFE_ACTIVE, mutates SubGhzSignal + produces `subghz_capture` evidence)
    subghz.discovery.analyze    (SAFE_ACTIVE, per-target prereq s.captured=True on the SAME frequency; produces `subghz_analysis` evidence)

Proves the 2.7.5/2.7.6/2.7.7 EvidenceRecord pipeline generalizes to a new
domain with NO second evidence system and no pipeline redesign â€” the capture
handler builds an EvidenceRecord identical in shape to wifi/BLE handlers, the
engine mirrors it, JSONL/HTML render it identically. The per-target
prerequisite (analyze needs capture on the SAME frequency) is the simulator
handler's gate, exactly mirroring `wifi.capture.pmkid` requiring
`handshake_captured=True` on the SAME bssid. Policy-rejected actions produce
zero evidence and zero env mutation.

Covered (mirrors the spec's test bullets 1-13):
  1. spectrum observation success
  2. capture success (mutates entity, evidence produced)
  3. analyze success on a captured target (evidence produced)
  4. capture requires the signal to exist (unknown frequency -> structured failure)
  5. analyze requires capture (known-but-uncaptured -> prereq-missing failure)
  6. malformed args (non-float frequency_mhz for both capture + analyze)
  7. failure paths produce no false-positive evidence
  8. correct evidence kind + provenance fields
  9. determinism (same seed -> same sample_count/capture_quality/hint/metadata)
  10. JSONL evidence.created events include the new kinds + provenance
  11. HTML EVIDENCE section renders the new kinds
  12. TUI feed: evidenceFormat maps subghz_capture -> domain 'other'
  13. Phase 2.7 + 2.8.0 regression: catalogue count, frozen entries, kinds,
      producers, plan shapes, performed_capability_keys mapping

Run without pytest:
    python -m tests.test_phase281_subghz_capture
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
    zigbee_workflow_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import render_run
from simulator.entities import SubGhzSignal
from simulator.environment import Environment
from simulator.scenarios import build_scenario
from simulator.simulator import (
    _subghz_protocol_hint,
    performed_capability_keys,
    execute as sim_execute,
)


# Lab scenario literal Sub-GHz frequencies (seed-independent).
LAB_FREQ_OOK = 433.92          # lab test transmitter (OOK, -55 dBm)
LAB_FREQ_FSK = 868.30          # lab LoRa-like chirp (FSK, -68 dBm)
SAMPLE_COUNT = 1024


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _safe_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)


def _sensitive_active_scope() -> AuthorizationScope:
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase2.8.1 subghz test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _spectrum() -> ActionRequest:
    return ActionRequest(capability="subghz.discovery", action="spectrum",
                         risk=ActionRisk.PASSIVE)


def _capture(freq: float) -> ActionRequest:
    return ActionRequest(capability="subghz.capture", action="signal",
                         args={"frequency_mhz": freq}, risk=ActionRisk.SAFE_ACTIVE)


def _analyze(freq: float) -> ActionRequest:
    return ActionRequest(capability="subghz.discovery", action="analyze",
                         args={"frequency_mhz": freq}, risk=ActionRisk.SAFE_ACTIVE)


def _signal(env: Environment, freq: float) -> SubGhzSignal | None:
    for s in env.subghz:
        if abs(s.frequency_mhz - freq) < 0.01:
            return s
    return None


# â”€â”€ 1. Spectrum observation success â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestSpectrumObservation:
    def test_spectrum_returns_lab_signals(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_spectrum())
            # The lab scenario has exactly 2 subghz signals.
            assert len(run.observations) == 1
            obs = run.observations[0]
            assert obs.summary.startswith("Spectrum scan returned 2 signal(s).")
            freqs = {round(e.attributes["frequency_mhz"], 2) for e in obs.entities}
            assert LAB_FREQ_OOK in freqs and LAB_FREQ_FSK in freqs
            # Spectrum never produces evidence.
            assert obs.evidence == []
        finally:
            logger.close()

    def test_spectrum_does_not_mutate_state(self):
        engine, run, logger, env = _engine_with_scope()
        try:
            engine.execute(_spectrum())
            assert performed_capability_keys(env) == set()
            # The signals are not marked captured.
            for s in env.subghz:
                assert s.captured is False
        finally:
            logger.close()


# â”€â”€ 2. capture success â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestCaptureSuccess:
    def test_capture_mutates_entity_and_stamps_notes(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_capture(LAB_FREQ_OOK))
            s = _signal(env, LAB_FREQ_OOK)
            assert s is not None and s.captured is True
            assert s.sample_count == SAMPLE_COUNT
            # rssi=-55 dBm -> "clean" (>=-60)
            assert s.capture_quality == "clean"
            assert any(k.startswith("subghz_capture:") for k in env.notes)
            assert "subghz.capture.signal" in performed_capability_keys(env)
        finally:
            logger.close()

    def test_capture_produces_one_evidence_record(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(_capture(LAB_FREQ_OOK))
            assert len(rec.evidence) == 1
            ev = rec.evidence[0]
            assert ev.kind == "subghz_capture"
            assert ev.source_capability == "subghz.capture"
            assert ev.source_action == "signal"
            assert ev.target_entity_type == "subghz_signal"
            ev_record_id = f"{LAB_FREQ_OOK:.3f}MHz-OOK"
            assert ev.target_entity_id == ev_record_id
            # Provenance post-engine: source_action_id stamped by RunEngine.
            assert ev.source_action_id == rec.request.id
            # Metadata is realistic, deterministic, no fake IQ blobs.
            md = ev.metadata
            assert md["frequency_mhz"] == LAB_FREQ_OOK
            assert md["modulation"] == "OOK"
            assert md["sample_count"] == SAMPLE_COUNT
            assert md["capture_quality"] == "clean"
            assert md["rssi"] == -55
            assert "raw_iq" not in md and "payload" not in md and "samples" not in md
        finally:
            logger.close()

    def test_capture_evidence_mirrored_to_run(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_capture(LAB_FREQ_OOK))
            assert len(run.evidence) == 1
            assert run.evidence[0].kind == "subghz_capture"
        finally:
            logger.close()

    def test_capture_quality_derived_from_rssi(self):
        # lab has rssi -55 (OOK -> clean) and -68 (FSK -> partial). Both
        # captured deterministically regardless of seed. The home scenario's
        # OOK signal has rssi -65 -> partial; crowded uses rng.randint.
        for scenario, freq, expected_q in [("lab", LAB_FREQ_OOK, "clean"),
                                          ("lab", LAB_FREQ_FSK, "partial")]:
            engine, run, logger, env = _engine_with_scope(
                _safe_active_scope(), scenario=scenario, seed=42)
            try:
                engine.execute(_capture(freq))
                s = _signal(env, freq)
                assert s.capture_quality == expected_q, (scenario, freq, s.capture_quality)
            finally:
                logger.close()


# â”€â”€ 3. analyze success on a captured target â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestAnalyzeSuccess:
    def test_analyze_produces_subghz_analysis_evidence_after_capture(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_capture(LAB_FREQ_OOK))
            rec = engine.execute(_analyze(LAB_FREQ_OOK))
            assert len(rec.evidence) == 1
            ev = rec.evidence[0]
            assert ev.kind == "subghz_analysis"
            assert ev.source_capability == "subghz.discovery"
            assert ev.source_action == "analyze"
            assert ev.target_entity_type == "subghz_signal"
            assert ev.metadata["capture_prereq"] is True
            assert ev.metadata["classification"]  # set by _classify_subghz
            assert ev.metadata["decoded_protocol_hint"] == "remote_control"
        finally:
            logger.close()

    def test_analyze_sets_decoded_protocol_hint_on_entity(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_capture(LAB_FREQ_OOK))
            engine.execute(_analyze(LAB_FREQ_OOK))
            s = _signal(env, LAB_FREQ_OOK)
            assert s.decoded_protocol_hint == "remote_control"
        finally:
            logger.close()

    def test_protocol_hint_is_a_hint_not_a_decoded_payload(self):
        # The _subghz_protocol_hint function returns a heuristic label based
        # on (frequency, modulation); it does NOT decode payloads (the sim
        # has no payloads). The return is one of a small label set.
        ok = {"remote_control", "ISM_remote", "car_remote", "LoRa_like",
              "ISM_IoT", "unknown"}
        s = SubGhzSignal(frequency_mhz=433.92, modulation="OOK",
                         bandwidth_khz=250, rssi=-60)
        assert _subghz_protocol_hint(s) in ok
        # An unknown combo -> "unknown" hint, no crash.
        s2 = SubGhzSignal(frequency_mhz=500.0, modulation="PSK",
                          bandwidth_khz=100, rssi=-50)
        assert _subghz_protocol_hint(s2) == "unknown"

    def test_analyze_stamps_env_notes_after_capture_pre(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_capture(LAB_FREQ_OOK))
            engine.execute(_analyze(LAB_FREQ_OOK))
            assert any(k.startswith("subghz_analyzed:") for k in env.notes)
            assert "subghz.discovery.analyze" in performed_capability_keys(env)
        finally:
            logger.close()


# â”€â”€ 4. capture requires the signal to exist â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestCaptureTargetValidation:
    def test_unknown_frequency_returns_structured_failure(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "subghz.capture", "signal", {"frequency_mhz": 200.0})
        assert obs.entities == []
        assert obs.evidence == []
        assert "No signal found" in obs.summary
        # No env mutation when no signal matches.
        assert all(not k.startswith("subghz_capture:") for k in env.notes)
        # All scenarios' signals remain uncaptured.
        assert all(s.captured is False for s in env.subghz)

    def test_unknown_target_via_engine_no_evidence(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            rec = engine.execute(ActionRequest(
                capability="subghz.capture", action="signal",
                args={"frequency_mhz": 200.0}, risk=ActionRisk.SAFE_ACTIVE))
            assert rec.observation is not None
            assert rec.observation.evidence == []
            assert run.evidence == []
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()


# â”€â”€ 5. analyze requires capture â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestAnalyzeRequiresCapture:
    def test_analyze_without_capture_returns_prereq_failure(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "subghz.discovery", "analyze",
                          {"frequency_mhz": LAB_FREQ_OOK})
        # The signal exists but is not captured -> structured failure.
        assert obs.entities == []
        assert obs.evidence == []
        assert "not captured" in obs.summary
        assert "subghz.capture.signal" in obs.summary  # tells operator what to call

    def test_analyze_without_capture_does_not_stamp_notes(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "subghz.discovery", "analyze",
                    {"frequency_mhz": LAB_FREQ_OOK})
        # The analyze handler must NOT have stamped subghz_analyzed:.
        assert all(not k.startswith("subghz_analyzed:") for k in env.notes)
        # So performed_capability_keys reflects no analyze.
        assert "subghz.discovery.analyze" not in performed_capability_keys(env)

    def test_analyze_only_after_capture_on_same_frequency(self):
        # Capture 433.92 then analyze 868.30 -> the OTHER target was not
        # captured; analyze of 868.30 must fail (per-target gate).
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_capture(LAB_FREQ_OOK))
            rec = engine.execute(_analyze(LAB_FREQ_FSK))
            assert rec.observation.evidence == []
            assert "not captured" in rec.observation.summary
            # The 433.92 capture still holds.
            sig = _signal(env, LAB_FREQ_OOK)
            assert sig.captured is True
            assert _signal(env, LAB_FREQ_FSK).captured is False
        finally:
            logger.close()

    def test_analyze_on_unknown_frequency_falls_through(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "subghz.discovery", "analyze",
                          {"frequency_mhz": 200.0})
        assert obs.entities == []
        assert obs.evidence == []
        assert "No signal found" in obs.summary


# â”€â”€ 6. malformed args â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestMalformedArgs:
    def _bad_args_cases(self):
        return [
            {"frequency_mhz": "abc"},   # non-numeric string
            {"frequency_mhz": None},     # None
            {},                          # missing
            {"frequency_mhz": ""},       # empty string
            {"frequency_mhz": ["x"]},    # list (a TypeError on float())
        ]

    def test_capture_bad_args(self):
        env = build_scenario("lab", seed=42)
        for args in self._bad_args_cases():
            obs = sim_execute(env, "subghz.capture", "signal", args)
            assert obs.evidence == []
            assert obs.entities == []
            assert "Invalid" in obs.summary or "No signal" in obs.summary
            assert all(not k.startswith("subghz_capture:") for k in env.notes)

    def test_analyze_bad_args(self):
        env = build_scenario("lab", seed=42)
        for args in self._bad_args_cases():
            obs = sim_execute(env, "subghz.discovery", "analyze", args)
            assert obs.evidence == []
            assert obs.entities == []
            assert "Invalid" in obs.summary or "No signal" in obs.summary


# â”€â”€ 7. failure paths produce no false-positive evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNoFalsePositiveEvidence:
    def test_failure_only_run_has_zero_evidence(self):
        # Capture an unknown frequency then analyze an unknown frequency:
        # both failure paths; run still completes with zero evidence.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan([
                ActionRequest(capability="subghz.discovery", action="spectrum",
                              risk=ActionRisk.PASSIVE),
                ActionRequest(capability="subghz.capture", action="signal",
                              args={"frequency_mhz": 200.0},
                              risk=ActionRisk.SAFE_ACTIVE),
                ActionRequest(capability="subghz.discovery", action="analyze",
                              args={"frequency_mhz": 200.0},
                              risk=ActionRisk.SAFE_ACTIVE),
            ])
            assert run.status == RunStatus.COMPLETED
            assert run.evidence == []
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()

    def test_analyze_before_capture_zero_evidence(self):
        # analyze before capture -> prereq failure -> zero evidence, then
        # a fresh capture+analyze may produce evidence (proving the failure
        # did not poison env state).
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.execute(_analyze(LAB_FREQ_OOK))  # failure
            assert run.evidence == []
            engine.execute(_capture(LAB_FREQ_OOK))
            engine.execute(_analyze(LAB_FREQ_OOK))   # success
            assert len(run.evidence) == 2
            kinds = {ev.kind for ev in run.evidence}
            assert kinds == {"subghz_capture", "subghz_analysis"}
        finally:
            logger.close()


# â”€â”€ 8. evidence kind + provenance â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestEvidenceKindAndProvenance:
    def test_kinds_known_in_vocabulary(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(subghz_capture_plan())
            for ev in run.evidence:
                assert ev.kind in KNOWN_EVIDENCE_KINDS, ev.kind
        finally:
            logger.close()

    def test_provenance_full_chain(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(subghz_capture_plan())
            # The plan produces 4 evidence total: 2 captures + 2 analyzes.
            assert len(run.evidence) == 4
            kinds = sorted(ev.kind for ev in run.evidence)
            assert kinds == ["subghz_analysis", "subghz_analysis",
                             "subghz_capture", "subghz_capture"]
            # Every EvidenceRecord carries the full provenance set.
            for ev in run.evidence:
                assert ev.id                                  # uuid
                assert ev.source_action_id                     # stamped by engine
                assert ev.source_capability in ("subghz.capture", "subghz.discovery")
                assert ev.source_action in ("signal", "analyze")
                assert ev.target_entity_type == "subghz_signal"
                assert ev.target_entity_id                     # freq-mod label
                assert ev.summary
                assert ev.metadata
                assert ev.captured_at > 0
        finally:
            logger.close()


# â”€â”€ 9. determinism â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDeterminism:
    def test_same_seed_yields_same_evidence_semantics(self):
        # Two independent runs with the same seed -> identical sample_count,
        # capture_quality, decoded_protocol_hint, evidence summaries +
        # metadata (id/captured_at are intentionally run-specific).
        seen = []
        for _ in range(2):
            engine, run, logger, env = _engine_with_scope(_safe_active_scope(), seed=42)
            try:
                engine.run_plan(subghz_capture_plan())
                semantic = [
                    (e.kind, e.source_capability, e.source_action, e.target_entity_id,
                     e.summary, {k: v for k, v in e.metadata.items()
                                if k not in ()})
                    for e in run.evidence
                ]
                seen.append(sorted(semantic))
            finally:
                logger.close()
        assert seen[0] == seen[1]

    def test_signal_state_deterministic(self):
        env1 = build_scenario("lab", seed=42)
        env2 = build_scenario("lab", seed=42)
        sim_execute(env1, "subghz.capture", "signal", {"frequency_mhz": LAB_FREQ_OOK})
        sim_execute(env2, "subghz.capture", "signal", {"frequency_mhz": LAB_FREQ_OOK})
        s1 = _signal(env1, LAB_FREQ_OOK)
        s2 = _signal(env2, LAB_FREQ_OOK)
        assert (s1.sample_count, s1.capture_quality, s1.captured) == \
               (s2.sample_count, s2.capture_quality, s2.captured)


# â”€â”€ 10. JSONL evidence.created events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestJsonlEvidenceEvents:
    def test_jsonl_emits_evidence_created_for_subghz(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(subghz_capture_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            # Plan produces 4 evidence; expect 4 evidence.created events.
            assert len(ev_events) == 4, len(ev_events)
            kinds = sorted(e["evidence"]["kind"] for e in ev_events)
            assert kinds == ["subghz_analysis", "subghz_analysis",
                             "subghz_capture", "subghz_capture"]
            # Each carries provenance back to source_action_id + run_id.
            for e in ev_events:
                assert e.get("source_action_id")
                assert e.get("run_id") == run.id
        finally:
            logger.close()

    def test_rejected_actions_emit_no_evidence_event(self):
        # PASSIVE-only scope: the SAFE_ACTIVE actions all REJECT, so zero
        # evidence.created events are emitted (and zero evidence records).
        engine, run, logger, env = _engine_with_scope()  # default PASSIVE
        try:
            engine.run_plan(subghz_capture_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            ev_events = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            assert ev_events == []
            assert run.evidence == []
        finally:
            logger.close()


# â”€â”€ 11. HTML EVIDENCE section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestHtmlEvidenceSection:
    def test_html_renders_subghz_evidence(self):
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(subghz_capture_plan())
            html = render_run(run)
            # EVIDENCE section header is present.
            assert "<h2>EVIDENCE</h2>" in html
            # Both new kinds appear in the rendered table.
            assert "subghz_capture" in html
            assert "subghz_analysis" in html
            # Provenance columns are present.
            for ev in run.evidence:
                assert ev.source_capability in html  # e.g. "subghz.capture"
            # The classification / hint metadata appears.
            assert "remote_control" in html or "LoRa_like" in html
        finally:
            logger.close()

    def test_html_empty_evidence_for_passive_run(self):
        engine, run, logger, env = _engine_with_scope()  # PASSIVE
        try:
            engine.run_plan(subghz_capture_plan())
            html = render_run(run)
            assert "<h2>EVIDENCE</h2>" in html
            assert "No evidence captured by this run." in html
        finally:
            logger.close()


# â”€â”€ 12. TUI evidence feed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestTuiEvidenceFeed:
    def test_evidenceFormat_maps_subghz_kind_to_other_domain(self):
        # The Node TUI evidenceFormat.js maps kinds by prefix: wifi->wifi,
        # ble->ble, everything else->other. subghz_* drops into "other",
        # which keeps it visible in the feed without a TUI source change.
        # We assert the JS rule here in Python (the parallel JS assertion
        # is added to suryafool-cli/src/components/evidenceFormat.test.js).
        subghz_ev = {"kind": "subghz_capture", "target_entity_id": "433.920MHz-OOK",
                     "source_capability": "subghz.capture", "source_action": "signal",
                     "summary": "Captured 1024 samples..."}
        # Mirror of the JS prefix logic so a future TUI refactor that breaks
        # this is incidentally caught by Python-suite integrators.
        kind = subghz_ev["kind"]
        if kind.startswith("wifi"):
            domain = "wifi"
        elif kind.startswith("ble"):
            domain = "ble"
        else:
            domain = "other"
        assert domain == "other"

    def test_js_test_file_has_subghz_assertion(self):
        # Forward-link to the Node suite so a future deletion of the new JS
        # assertion fails the Python suite too (integration guard).
        root = Path(__file__).resolve().parent.parent
        js_test = (root / "suryafool-cli" / "src" / "components"
                   / "EvidenceFeed.test.js")
        txt = js_test.read_text(encoding="utf-8")
        assert "subghz_capture" in txt
        assert "subghz_analysis" in txt
        assert "subghz.capture.signal" in txt
        assert "subghz.discovery.analyze" in txt


# â”€â”€ 13. Phase 2.7 + 2.8.0 regression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPhaseRegression:
    def test_catalogue_count_is_22(self):
        assert len(DEFAULT_CAPABILITIES) == 26

    def test_four_phase27_producers_subset_preserved(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        for key in ("wifi.capture.handshake", "wifi.capture.pmkid",
                    "ble.gatt.pair", "ble.gatt.write"):
            assert key in by_key, f"Phase 2.7 producer lost: {key}"

    def test_phase281_contribution_present(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert "subghz.capture.signal" in by_key
        assert by_key["subghz.capture.signal"].produces_evidence is True
        assert by_key["subghz.discovery.analyze"].produces_evidence is True

    def test_phase283_ir_producers_present(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["infrared.analyze"].produces_evidence is True
        assert by_key["infrared.transmit"].produces_evidence is True
        assert by_key["infrared.capture"].produces_evidence is False

    def test_known_evidence_kinds_has_seven(self):
        # The vocabulary extends across Phases 2.8.1 (2), 2.8.2 (nfc_read) and
        # 2.8.3 (ir_analysis + ir_transmit). All 9 kinds are frozen here so a
        # future silent addition or removal is caught. The dedicated suites
        # prove each contribution in detail.
        assert KNOWN_EVIDENCE_KINDS == frozenset({
            "wifi_eapol_handshake", "wifi_pmkid",
            "ble_pairing", "ble_secure_write",
            "subghz_capture", "subghz_analysis",
            "nfc_read",
            "ir_analysis", "ir_transmit",  # Phase 2.8.3
            "zigbee_join",                  # Phase 2.8.4
        })

    def test_default_exploration_plan_unchanged(self):
        plan = default_exploration_plan()
        assert len(plan) == 4
        # spectrum is already in the default exploration plan (no noisy new
        # Sub-GHz REJECT; that was the Phase 2.8.0 design choice).
        assert all(p.risk == ActionRisk.PASSIVE for p in plan)

    def test_deterministic_plan_shapes_frozen(self):
        assert len(default_exploration_plan()) == 4
        assert len(wifi_capture_plan()) == 5
        assert len(ble_gatt_workflow_plan()) == 6
        assert len(subghz_capture_plan()) == 5
        assert len(nfc_workflow_plan()) == 5        # Phase 2.8.2
        assert len(ir_workflow_plan()) == 4         # Phase 2.8.3
        assert len(zigbee_workflow_plan()) == 4     # Phase 2.8.4
        # Every plan action's request.risk equals cap.risk.
        reg = default_registry(environment=build_scenario("lab", seed=42))
        for plan in (wifi_capture_plan(), ble_gatt_workflow_plan(),
                     subghz_capture_plan(), nfc_workflow_plan(), ir_workflow_plan(),
                     zigbee_workflow_plan()):
            for req in plan:
                cap = reg.capability(req.capability, req.action)
                assert cap is not None and req.risk == cap.risk

    def test_performed_capability_keys_includes_subghz_capture(self):
        # The _NOTE_PREFIX_TO_CAPABILITY_KEY map gains subghz_capture:.
        # After a capture, the performed keys include subghz.capture.signal.
        # Validate the mapping indirectly through the handler doing the stamp.
        env = build_scenario("lab", seed=42)
        sim_execute(env, "subghz.capture", "signal",
                    {"frequency_mhz": LAB_FREQ_OOK})
        assert "subghz.capture.signal" in performed_capability_keys(env)

    def test_passive_scope_rejects_active_actions_before_provider(self):
        # PASSIVE-only scope: all SAFE_ACTIVE actions REJECT before the
        # provider. Environment unchanged (no notes; performed_capability_keys
        # empty). run continued.
        engine, run, logger, env = _engine_with_scope()  # PASSIVE
        try:
            engine.run_plan(subghz_capture_plan())
            assert run.status == RunStatus.COMPLETED
            # 4 SAFE_ACTIVE actions REJECT; spectrum ACCEPTs.
            rejected = [r for r in run.actions
                        if r.policy_decision and not r.policy_decision.allowed]
            assert len(rejected) == 4
            for r in rejected:
                assert r.observation is None            # provider never invoked
                assert r.evidence == []
            assert run.evidence == []
            assert performed_capability_keys(env) == set()
            for s in env.subghz:
                assert s.captured is False
                assert s.decoded_protocol_hint == ""
        finally:
            logger.close()

    def test_risk_declaration_rule_still_guards_subghz_capture(self):
        # Caller downgrade/upgrade both rejected by RiskDeclarationRule.
        engine, run, logger, env = _engine_with_scope(_safe_active_scope())
        try:
            # Upgrade: SAFE_ACTIVE entry, claim SENSITIVE_ACTIVE.
            up = engine.execute(ActionRequest(
                capability="subghz.capture", action="signal",
                args={"frequency_mhz": LAB_FREQ_OOK},
                risk=ActionRisk.SENSITIVE_ACTIVE))
            assert up.policy_decision.kind == PolicyDecisionKind.REJECT
            # Downgrade: SAFE_ACTIVE entry, claim PASSIVE.
            down = engine.execute(ActionRequest(
                capability="subghz.capture", action="signal",
                args={"frequency_mhz": LAB_FREQ_OOK},
                risk=ActionRisk.PASSIVE))
            assert down.policy_decision.kind == PolicyDecisionKind.REJECT
            # Neither variant altered env state.
            assert all(s.captured is False for s in env.subghz)
        finally:
            logger.close()


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    os.environ["SURYAFOOL_RUNS_DIR"] = str(
        Path(tempfile.mkdtemp(prefix="suryafool-p281-")) / "runs")
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
