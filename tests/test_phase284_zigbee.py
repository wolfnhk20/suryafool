"""
tests/test_phase284_zigbee.py

Phase 2.8.4 — Zigbee wireless mesh vertical slice.

A brand-new Suryafool domain (zigbee) staked in ONE phase on the frozen
Phase 2.7 stack + Phase 2.8.0 multi-domain foundation. Two entity types
(ZigbeeNetwork PAN + ZigbeeNode with mesh parent-child links), one new
stateful SAFE_ACTIVE capability (`zigbee.discovery.join`, produces
`zigbee_join` evidence) alongside two PASSIVE ones (scan / inspect).
No second capability / evidence / event / reporting system — the join
flows through the existing gate (Registry → cap.risk → AuthorizationScope →
Policy → Provider), mutates ZigbeeNode state, and produces `zigbee_join`
evidence via the Phase 2.7.5 pipeline.

Run:  python -m tests.test_phase284_zigbee      (stdlib-only runner)
Also: python -m pytest tests/test_phase284_zigbee.py -q
"""

import json
import os
import tempfile
import time
from pathlib import Path

try:
    import pytest
except Exception:  # pragma: no cover - pytest optional
    pytest = None

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
    default_exploration_plan,
    ir_workflow_plan,
    nfc_workflow_plan,
    subghz_capture_plan,
    wifi_capture_plan,
    zigbee_workflow_plan,
)
from policy.policy import PolicyEngine
from reports.html_report import render_run
from simulator.entities import ZigbeeNetwork, ZigbeeNode
from simulator.environment import Environment
from simulator.scenarios import build_scenario
from simulator.simulator import execute as sim_execute
from simulator.simulator import performed_capability_keys


# Lab scenario literal Zigbee targets (seed-independent).
LAB_PAN = "0x1A2B"                       # ch 15, coordinator 0x0000
LAB_COORD = "00:15:8D:00:00:00:00:01"
LAB_ROUTER = "00:15:8D:00:00:00:00:02"
LAB_LAMP = "00:15:8D:00:00:00:00:03"     # pre-joined end-device (short 0x0002)
LAB_JOINEE = "00:15:8D:00:00:00:00:04"   # UNJOINED end-device — the join target


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
    run = Run(objective="phase 2.8.4 zigbee test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _scan() -> ActionRequest:
    return ActionRequest(capability="zigbee.discovery", action="scan",
                         risk=ActionRisk.PASSIVE)


def _inspect(pan_id: str = LAB_PAN) -> ActionRequest:
    return ActionRequest(capability="zigbee.discovery", action="inspect",
                         args={"pan_id": pan_id},
                         risk=ActionRisk.PASSIVE)


def _join(pan_id: str = LAB_PAN, ieee: str = LAB_JOINEE) -> ActionRequest:
    return ActionRequest(capability="zigbee.discovery", action="join",
                         args={"pan_id": pan_id, "ieee_address": ieee},
                         risk=ActionRisk.SAFE_ACTIVE)


def _node(env: Environment, ieee: str):
    for n in env.zigbee_nodes:
        if n.ieee_address == ieee:
            return n
    return None


def _network(env: Environment, pan_id: str):
    for n in env.zigbee_networks:
        if n.pan_id == pan_id:
            return n
    return None


# 1. Zigbee entity fields

class TestZigbeeEntityFields:
    def test_network_fields_and_defaults(self):
        n = ZigbeeNetwork(pan_id="0x1A2B", extended_pan_id="00:15:8D:00:00:00:1A:2B",
                          channel=15, rssi=-52, prefix="zb-lab-")
        assert n.node_count == 0
        assert n.pan_id == "0x1A2B"
        assert n.channel == 15

    def test_node_fields_and_defaults(self):
        n = ZigbeeNode(ieee_address=LAB_COORD, short_address="0x0000",
                       role="coordinator", network=LAB_PAN, parent_short_address="",
                       lqi=255, joined=True)
        assert n.joined is True
        assert n.parent_short_address == ""
        unjoined = ZigbeeNode(ieee_address=LAB_JOINEE, short_address="",
                              role="end_device", network=LAB_PAN)
        assert unjoined.joined is False
        assert unjoined.short_address == ""
        assert unjoined.lqi == 0

    def test_node_to_dict_carries_mesh_fields(self):
        n = ZigbeeNode(ieee_address=LAB_LAMP, short_address="0x0002",
                       role="end_device", network=LAB_PAN, parent_short_address="0x0001",
                       lqi=210, joined=True)
        d = n.to_dict()
        assert d["ieee_address"] == LAB_LAMP
        assert d["short_address"] == "0x0002"
        assert d["parent_short_address"] == "0x0001"
        assert d["joined"] is True
        assert d["network"] == LAB_PAN

    def test_to_dict_round_trips_through_json(self):
        n = ZigbeeNode(ieee_address=LAB_JOINEE, short_address="0x0003",
                       role="end_device", network=LAB_PAN, parent_short_address="0x0001",
                       lqi=220, joined=True)
        d = json.loads(json.dumps(n.to_dict()))
        assert d["short_address"] == "0x0003"
        assert d["parent_short_address"] == "0x0001"
        assert d["joined"] is True

    def test_lab_scenario_has_zigbee(self):
        env = build_scenario("lab", seed=42)
        assert len(env.zigbee_networks) == 1
        assert len(env.zigbee_nodes) == 4
        snaps = env.snapshot()
        assert "zigbee_networks" in snaps and "zigbee_nodes" in snaps


# 2. Scan (PASSIVE, observational)

class TestScanObservation:
    def test_scan_returns_lab_pan(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "scan", {})
        assert obs.capability == "zigbee.discovery" and obs.action == "scan"
        assert len(obs.entities) == 1
        e = obs.entities[0]
        assert e.type == "zigbee_network" and e.id == LAB_PAN
        assert e.attributes["node_count"] == 3  # coordinator + router + lamp (joined)
        assert obs.evidence == []

    def test_scan_is_observational_no_mutation(self):
        env = build_scenario("lab", seed=42)
        before = performed_capability_keys(env)
        sim_execute(env, "zigbee.discovery", "scan", {})
        assert performed_capability_keys(env) == before
        assert not any("zigbee" in k for k in env.notes) 

    def test_home_scan_has_one_pan(self):
        env = build_scenario("home", seed=7)
        obs = sim_execute(env, "zigbee.discovery", "scan", {})
        assert len(obs.entities) == 1
        assert obs.entities[0].id == "0x2C3D"


# 3. Inspect (PASSIVE — surfaces mesh topology)

class TestInspectObservation:
    def test_inspect_lists_nodes_with_parent_links(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "inspect", {"pan_id": LAB_PAN})
        assert obs.capability == "zigbee.discovery" and obs.action == "inspect"
        assert len(obs.entities) == 4
        attrs = {e.id: e.attributes for e in obs.entities}
        # mesh parent-child routing links are honest state, not decoration
        assert attrs[LAB_COORD]["parent_short_address"] == ""
        assert attrs[LAB_ROUTER]["parent_short_address"] == "0x0000"
        assert attrs[LAB_LAMP]["parent_short_address"] == "0x0001"
        assert attrs[LAB_JOINEE]["joined"] is False
        assert attrs[LAB_JOINEE]["short_address"] == ""
        assert obs.evidence == []

    def test_inspect_unknown_pan_fails(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "inspect", {"pan_id": "0xDEAD"})
        assert obs.entities == []
        assert obs.evidence == []
        assert "No Zigbee PAN" in obs.summary

    def test_inspect_missing_pan_arg_fails(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "inspect", {})
        assert obs.entities == [] and obs.evidence == []


# 4. Join success (SAFE_ACTIVE)

class TestJoinSuccess:
    def test_join_mutates_node_state(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "join",
                          {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        assert obs.evidence != []
        assert obs.entities != []
        node = _node(env, LAB_JOINEE)
        assert node.joined is True
        assert node.short_address == "0x0003"  # next free short (0,1,2 used)
        assert node.parent_short_address == "0x0001"  # joined via the router
        assert node.lqi == 220
        assert f"zigbee_joined:{LAB_JOINEE}" in env.notes

    def test_join_assigned_short_is_deterministic(self):
        shors = set()
        for seed in (1, 7, 42):
            env = build_scenario("lab", seed=seed)
            sim_execute(env, "zigbee.discovery", "join",
                        {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
            shors.add(_node(env, LAB_JOINEE).short_address)
        assert shors == {"0x0003"}

    def test_join_produces_zigbee_join_evidence(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "join",
                          {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        ev = obs.evidence
        assert len(ev) == 1
        e = ev[0]
        assert e.kind == "zigbee_join"
        assert e.source_capability == "zigbee.discovery"
        assert e.source_action == "join"
        assert e.target_entity_id == LAB_JOINEE
        assert e.target_entity_type == "zigbee_node"
        assert e.metadata["ieee_address"] == LAB_JOINEE
        assert e.metadata["network"] == LAB_PAN
        assert e.metadata["assigned_short_address"] == "0x0003"
        assert e.metadata["parent_short_address"] == "0x0001"
        assert e.metadata["role"] == "end_device"
        assert e.metadata["lqi"] == 220
        assert "joined PAN" in e.summary

    def test_join_evidence_round_trips(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "join",
                          {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        d = json.loads(json.dumps(obs.evidence[0].to_dict()))
        assert d["kind"] == "zigbee_join"
        assert d["metadata"]["assigned_short_address"] == "0x0003"

    def test_join_reflected_by_later_inspect(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "zigbee.discovery", "join",
                    {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        obs = sim_execute(env, "zigbee.discovery", "inspect", {"pan_id": LAB_PAN})
        attrs = {e.id: e.attributes for e in obs.entities}
        # the state→observation loop: node now shows joined in the re-read
        assert attrs[LAB_JOINEE]["joined"] is True
        assert attrs[LAB_JOINEE]["short_address"] == "0x0003"

    def test_join_updates_network_node_count(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "zigbee.discovery", "join",
                    {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        obs = sim_execute(env, "zigbee.discovery", "scan", {})
        assert obs.entities[0].attributes["node_count"] == 4


# 5. Join failure paths (zero evidence / zero mutation)

class TestJoinFailure:
    def test_join_unknown_pan_fails(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "join",
                          {"pan_id": "0xDEAD", "ieee_address": LAB_JOINEE})
        assert obs.evidence == []
        assert _node(env, LAB_JOINEE).joined is False
        assert not any("zigbee_joined" in k for k in env.notes)

    def test_join_unknown_node_fails(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "join",
                          {"pan_id": LAB_PAN, "ieee_address": "00:11:22:33:44:55:66:77"})
        assert obs.evidence == []

    def test_join_missing_pan_fails(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "join",
                          {"ieee_address": LAB_JOINEE})
        assert obs.evidence == [] and _node(env, LAB_JOINEE).joined is False

    def test_join_missing_ieee_fails(self):
        env = build_scenario("lab", seed=42)
        obs = sim_execute(env, "zigbee.discovery", "join", {"pan_id": LAB_PAN})
        assert obs.evidence == [] and _node(env, LAB_JOINEE).joined is False

    def test_join_already_joined_fails(self):
        env = build_scenario("lab", seed=42)
        # lamp (0x0002) is already joined — cannot join again
        obs = sim_execute(env, "zigbee.discovery", "join",
                          {"pan_id": LAB_PAN, "ieee_address": LAB_LAMP})
        assert obs.evidence == []
        assert "already joined" in obs.summary
        assert _node(env, LAB_LAMP).short_address == "0x0002"  # unmutated

    def test_join_then_join_again_fails(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "zigbee.discovery", "join",
                    {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        obs2 = sim_execute(env, "zigbee.discovery", "join",
                           {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        assert obs2.evidence == []
        assert "already joined" in obs2.summary

    def test_no_false_positive_evidence(self):
        # failure-only sequence must produce zero evidence
        env = build_scenario("lab", seed=42)
        sim_execute(env, "zigbee.discovery", "join",
                    {"pan_id": "0xDEAD", "ieee_address": LAB_JOINEE})
        sim_execute(env, "zigbee.discovery", "join",
                    {"pan_id": LAB_PAN, "ieee_address": LAB_LAMP})
        assert not any("joined" in k for k in env.notes)


# 6. Policy / authorization boundary

class TestAuthorizationBoundary:
    def _run(self, scope):
        engine, run, _, _ = _engine_with_scope(scope)
        engine.run_plan(zigbee_workflow_plan())
        return run

    def test_passive_only_rejects_join(self):
        run = self._run(AuthorizationScope.default())
        assert run.status == RunStatus.COMPLETED
        rejections = [a for a in run.actions
                      if a.policy_decision and a.policy_decision.kind == PolicyDecisionKind.REJECT]
        assert len(rejections) == 1
        assert rejections[0].request.capability == "zigbee.discovery"
        assert rejections[0].request.action == "join"
        assert run.evidence == []

    def test_passive_only_leaves_env_unchanged(self):
        engine, run, _, env = _engine_with_scope(AuthorizationScope.default())
        engine.run_plan(zigbee_workflow_plan())
        # node remains unjoined (provider never reached)
        assert _node(env, LAB_JOINEE).joined is False
        assert not any("zigbee_joined" in k for k in env.notes)

    def test_safe_active_runs_full_chain(self):
        run = self._run(_safe_active_scope())
        assert run.status == RunStatus.COMPLETED
        assert len(run.evidence) == 1
        assert run.evidence[0].kind == "zigbee_join"

    def test_join_risk_authoritative(self):
        env = build_scenario("lab", seed=42)
        reg = default_registry(environment=env)
        cap = reg.capability("zigbee.discovery", "join")
        assert cap.risk == ActionRisk.SAFE_ACTIVE
        # caller downgrade must be rejected by RiskDeclarationRule
        engine, run, _, _ = _engine_with_scope(_safe_active_scope())
        downgraded = ActionRequest(capability="zigbee.discovery", action="join",
                                   args={"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE},
                                   risk=ActionRisk.PASSIVE)
        engine.run_plan([downgraded])
        assert run.actions[-1].policy_decision.kind == PolicyDecisionKind.REJECT
        assert run.evidence == []

    def test_rejected_run_emits_no_evidence_created(self):
        engine, run, logger, _ = _engine_with_scope(AuthorizationScope.default())
        try:
            engine.run_plan(zigbee_workflow_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            assert all(e.get("type") != EVIDENCE_CREATED for e in events)
        finally:
            logger.close()


# 7. Performed capability keys

class TestPerformedCapabilityKeys:
    def test_join_stamps_key(self):
        env = build_scenario("lab", seed=42)
        assert "zigbee.discovery.join" not in performed_capability_keys(env)
        sim_execute(env, "zigbee.discovery", "join",
                    {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
        assert "zigbee.discovery.join" in performed_capability_keys(env)

    def test_passive_actions_not_performed(self):
        env = build_scenario("lab", seed=42)
        sim_execute(env, "zigbee.discovery", "scan", {})
        sim_execute(env, "zigbee.discovery", "inspect", {"pan_id": LAB_PAN})
        keys = performed_capability_keys(env)
        assert "zigbee.discovery.scan" not in keys
        assert "zigbee.discovery.inspect" not in keys


# 8. Determinism

class TestDeterminism:
    def test_join_semantics_deterministic_across_seeds(self):
        summaries = []
        for seed in (7, 42, 99):
            env = build_scenario("lab", seed=seed)
            obs = sim_execute(env, "zigbee.discovery", "join",
                              {"pan_id": LAB_PAN, "ieee_address": LAB_JOINEE})
            node = _node(env, LAB_JOINEE)
            summaries.append((obs.evidence[0].kind,
                              json.dumps(obs.evidence[0].metadata, sort_keys=True),
                              node.short_address, node.parent_short_address, node.lqi))
        assert len(set(summaries)) == 1

    def test_full_plan_semantics_deterministic(self):
        def run_once(scope):
            engine, run, _, env = _engine_with_scope(
                AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE))
            engine.run_plan(zigbee_workflow_plan())
            return [a.policy_decision.kind for a in run.actions], \
                   [(e.kind, json.dumps(e.metadata, sort_keys=True)) for e in run.evidence], \
                   [n.short_address for n in env.zigbee_nodes]
        assert run_once(42) == run_once(42)

    def test_scan_inspect_deterministic(self):
        def run_once():
            env = build_scenario("lab", seed=5)
            scan = sim_execute(env, "zigbee.discovery", "scan", {})
            insp = sim_execute(env, "zigbee.discovery", "inspect", {"pan_id": LAB_PAN})
            return len(scan.entities), len(insp.entities)
        assert run_once() == run_once()


# 9. JSONL evidence events (full run)

class TestJsonlEvidenceEvents:
    def test_safe_active_emits_one_zigbee_join_event(self):
        engine, run, logger, _ = _engine_with_scope(_safe_active_scope())
        try:
            engine.run_plan(zigbee_workflow_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            evts = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            assert len(evts) == 1
            assert evts[0]["evidence"]["kind"] == "zigbee_join"
            assert evts[0]["evidence"]["source_action_id"]
            assert evts[0]["run_id"] == run.id
        finally:
            logger.close()

    def test_passive_only_emits_zero_events(self):
        engine, run, logger, _ = _engine_with_scope(AuthorizationScope.default())
        try:
            engine.run_plan(zigbee_workflow_plan())
            lines = (run_dir(run.id) / "events.jsonl").read_text().splitlines()
            events = [json.loads(l) for l in lines if l.strip()]
            evts = [e for e in events if e.get("type") == EVIDENCE_CREATED]
            assert evts == []
            assert run.evidence == []
            assert run.status == RunStatus.COMPLETED
        finally:
            logger.close()


# 10. HTML report evidence section

class TestHtmlEvidenceSection:
    def test_report_renders_zigbee_evidence(self):
        engine, run, logger, _ = _engine_with_scope(_safe_active_scope())
        engine.run_plan(zigbee_workflow_plan())
        html = render_run(run)
        assert "zigbee_join" in html
        assert LAB_JOINEE in html
        assert "joined PAN" in html

    def test_passive_report_shows_no_evidence(self):
        engine, run, logger, _ = _engine_with_scope(AuthorizationScope.default())
        engine.run_plan(zigbee_workflow_plan())
        html = render_run(run)
        assert "No evidence captured by this run." in html


# 11. TUI forward-guard (Python ↔ Node sync contract)

class TestTuiEvidenceFeed:
    def test_zigbee_kind_locks_in_evidence_kinds(self):
        # phase 2.8.4 adds exactly one new evidence kind: zigbee_join
        assert "zigbee_join" in KNOWN_EVIDENCE_KINDS


# 12. Phase 2.7 + 2.8 regression + catalogue freeze

class TestPhaseRegression:
    def test_catalogue_count_is_26(self):
        assert len(DEFAULT_CAPABILITIES) == 26

    def test_zigbee_entries_correct_risk_and_metadata(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["zigbee.discovery.scan"].risk == ActionRisk.PASSIVE
        assert by_key["zigbee.discovery.scan"].produces_evidence is False
        assert by_key["zigbee.discovery.scan"].output_entity_type == "zigbee_network"
        assert by_key["zigbee.discovery.inspect"].risk == ActionRisk.PASSIVE
        assert by_key["zigbee.discovery.inspect"].requires_args == ("pan_id",)
        assert by_key["zigbee.discovery.inspect"].output_entity_type == "zigbee_node"
        assert by_key["zigbee.discovery.join"].risk == ActionRisk.SAFE_ACTIVE
        assert by_key["zigbee.discovery.join"].produces_evidence is True
        assert by_key["zigbee.discovery.join"].mutates_state is True
        assert by_key["zigbee.discovery.join"].requires_args == ("pan_id", "ieee_address")

    def test_zigbee_domain_registered(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["zigbee.discovery.scan"].domain == "zigbee"
        assert by_key["zigbee.discovery.inspect"].domain == "zigbee"
        assert by_key["zigbee.discovery.join"].domain == "zigbee"

    def test_all_evidence_producers(self):
        producers = sorted(k for k, c in
                           {c.key: c for c in DEFAULT_CAPABILITIES}.items()
                           if c.produces_evidence)
        assert producers == [
            "ble.gatt.pair", "ble.gatt.write",
            "infrared.analyze", "infrared.transmit",
            "nfc.discovery.read", "subghz.capture.signal", "subghz.discovery.analyze",
            "wifi.capture.handshake", "wifi.capture.pmkid",
            "zigbee.discovery.join",
        ]

    def test_known_evidence_kinds_frozen(self):
        assert KNOWN_EVIDENCE_KINDS == frozenset({
            "wifi_eapol_handshake", "wifi_pmkid",
            "ble_pairing", "ble_secure_write",
            "subghz_capture", "subghz_analysis",
            "nfc_read",
            "ir_analysis", "ir_transmit",
            "zigbee_join",
        })

    def test_zigbee_workflow_plan_shape(self):
        plan = zigbee_workflow_plan()
        assert len(plan) == 4
        assert [(r.capability, r.action) for r in plan] == [
            ("zigbee.discovery", "scan"),
            ("zigbee.discovery", "inspect"),
            ("zigbee.discovery", "join"),
            ("zigbee.discovery", "inspect"),
        ]
        risks = [r.risk for r in plan]
        assert risks == [ActionRisk.PASSIVE, ActionRisk.PASSIVE,
                         ActionRisk.SAFE_ACTIVE, ActionRisk.PASSIVE]

    def test_plan_risks_match_authoritative(self):
        reg = default_registry(environment=build_scenario("lab", seed=42))
        for req in zigbee_workflow_plan():
            cap = reg.capability(req.capability, req.action)
            assert cap is not None and req.risk == cap.risk

    def test_deterministic_plan_shapes_frozen(self):
        assert len(default_exploration_plan()) == 4
        assert len(wifi_capture_plan()) == 5
        assert len(subghz_capture_plan()) == 5
        assert len(nfc_workflow_plan()) == 5
        assert len(ir_workflow_plan()) == 4
        assert len(zigbee_workflow_plan()) == 4
        # ethernet / usb remain REGISTERED BUT UNSUPPORTED (2.8.4 is Zigbee)
        env = build_scenario("lab", seed=42)
        reg = default_registry(environment=env)
        for action in ("discover", "inspect"):
            assert reg.resolve("ethernet", action).supported is False
            assert reg.resolve("usb", action).supported is False

    def test_registry_resolves_zigbee_as_supported(self):
        env = build_scenario("lab", seed=42)
        reg = default_registry(environment=env)
        for action in ("scan", "inspect", "join"):
            decision = reg.resolve("zigbee.discovery", action)
            assert decision.supported is True, f"zigbee.discovery.{action}"

    def test_four_phase27_producers_subset_preserved(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        for key in ("wifi.capture.handshake", "wifi.capture.pmkid",
                    "ble.gatt.pair", "ble.gatt.write"):
            assert key in by_key, f"Phase 2.7 producer lost: {key}"

    def test_phase27_kinds_subset_of_known(self):
        assert {"wifi_eapol_handshake", "wifi_pmkid",
                "ble_pairing", "ble_secure_write"} <= KNOWN_EVIDENCE_KINDS

    def test_cli_run_zigbee_workflow(self):
        # full end-to-end via the engine (mirrors `python -m cli.phase2 run
        # --scenario lab --plan zigbee_workflow --allow-risk safe_active`)
        engine, run, logger, _ = _engine_with_scope(_safe_active_scope())
        engine.run_plan(zigbee_workflow_plan())
        assert run.status == RunStatus.COMPLETED
        assert len(run.evidence) == 1
        d = json.loads(json.dumps(run.to_dict()))
        assert d["evidence"][0]["kind"] == "zigbee_join"


# Standalone runner (no pytest required)

def _run_all() -> int:
    import traceback
    failures = 0
    os.environ["SURYAFOOL_RUNS_DIR"] = str(
        Path(tempfile.mkdtemp(prefix="suryafool-p284-")) / "runs")
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
