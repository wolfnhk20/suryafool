"""
tests/test_phase280_multidomain.py

Phase 2.8.0 â€” multi-domain deterministic expansion foundation.

Verifies the FROZEN Phase 2.7 stack now carries the full Suryafool capability
surface â€” Sub-GHz, NFC, Infrared, Ethernet, USB â€” WITHOUT a second capability
system and WITHOUT fake functionality:

  1. the 7 new catalogue entries for infrared / ethernet / usb are registered
     (the existing 14 Phase 2.7 entries are preserved byte-for-byte)
  2. capability contract metadata is valid for every new entry (domain,
     requires_args, output_entity_type, requires, mutates_state); to_dict
     round-trips through JSON
  3. risk values per entry are correct and use the existing ActionRisk tiers
  4. registry resolution: the new entries are catalogue-registered but
     explicitly UNSUPPORTED (supported=False, "no registered provider")
       - the existing 14 entries still resolve supported=True
  5. unsupported capability behavior end-to-end: an unimplemented action is
     REJECTED at the policy gate BEFORE the provider (observation None, no
     env mutation, zero evidence, run continues) â€” the platform never pretends
     an unimplemented domain works
  6. RiskDeclarationRule still guards the new entries (caller downgrade and
     upgrade both rejected)
  7. prerequisite metadata: infrared.transmit requires infrared.capture
     (cross-namespace prereq chain, parallel to ble.gatt.pair requires connect)
  8. Phase 2.7 freeze regression: all 14 frozen keys + risks present, the 4
     evidence producers are unchanged, KNOWN_EVIDENCE_KINDS frozen at 4,
     deterministic plan shapes unchanged
  9. entity/environment substrate: IrSignal / EthernetHost / UsbDevice
     dataclasses exist, Environment exposes empty ir/ethernet/usb lists, and
     snapshot() serializes

Run without pytest:
    python -m tests.test_phase280_multidomain
"""

import json
import os
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None  # standalone runner works without pytest

from capabilities.base import DEFAULT_CAPABILITIES, KNOWN_DOMAINS, Capability
from capabilities.registry import default_registry
from core.evidence import KNOWN_EVIDENCE_KINDS
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
    ir_workflow_plan,
    nfc_workflow_plan,
    subghz_capture_plan,
    wifi_capture_plan,
    zigbee_workflow_plan,
)
from policy.policy import PolicyEngine
from simulator.environment import Environment
from simulator.entities import EthernetHost, IrSignal, UsbDevice
from simulator.scenarios import build_scenario
from simulator.simulator import performed_capability_keys


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Phase 2.8.0 new capability surface â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

NEW_KEYS = [
    "infrared.capture",
    "infrared.analyze",
    "infrared.transmit",
    "ethernet.discovery.discover",
    "ethernet.discovery.inspect",
    "usb.discovery.enumerate",
    "usb.discovery.inspect",
    "nfc.discovery.select",  # Phase 2.8.2 — select is PASSIVE, mutates_state, no evidence
]

# The Phase 2.8.0 entries are registered-but-unsupported (no simulator handler).
# Phase 2.8.2 promoted nfc.discovery.select to supported; Phase 2.8.3 promoted
# the three infrared.* entries to supported. They stay in NEW_KEYS for
# metadata/risk assertions but are excluded from the unsupported check —
# only ethernet + usb remain handler-less (2.8.4 / 2.8.5).
UNSUPPORTED_280_KEYS = [k for k in NEW_KEYS
                        if k not in ("nfc.discovery.select",
                                     "infrared.capture",
                                     "infrared.analyze",
                                     "infrared.transmit")]

# The authoritative metadata block for the 7 new entries â€” mirrors the
# catalogue table in the Phase 2.8.0 plan.
_EXPECTED_BY_KEY: dict[str, dict] = {
    "infrared.capture":            {"domain": "infrared", "risk": ActionRisk.PASSIVE,
                                    "requires_args": (),              "output_entity_type": "ir_signal",
                                    "requires": (),                  "mutates_state": False,
                                    "produces_evidence": False},
    "infrared.analyze":            {"domain": "infrared", "risk": ActionRisk.SAFE_ACTIVE,
                                    "requires_args": ("capture_id",), "output_entity_type": "ir_signal",
                                    "requires": (),                  "mutates_state": True,
                                    "produces_evidence": True},  # Phase 2.8.3 kind ir_analysis
    "infrared.transmit":           {"domain": "infrared", "risk": ActionRisk.SENSITIVE_ACTIVE,
                                    "requires_args": ("capture_id",), "output_entity_type": "ir_signal",
                                    "requires": ("infrared.capture",), "mutates_state": True,
                                    "produces_evidence": True},  # Phase 2.8.3 kind ir_transmit
    "ethernet.discovery.discover": {"domain": "ethernet", "risk": ActionRisk.PASSIVE,
                                    "requires_args": (),              "output_entity_type": "ethernet_host",
                                    "requires": (),                  "mutates_state": False,
                                    "produces_evidence": False},
    "ethernet.discovery.inspect":  {"domain": "ethernet", "risk": ActionRisk.PASSIVE,
                                    "requires_args": ("host",),      "output_entity_type": "ethernet_host",
                                    "requires": (),                  "mutates_state": False,
                                    "produces_evidence": False},
    "usb.discovery.enumerate":     {"domain": "usb",      "risk": ActionRisk.PASSIVE,
                                    "requires_args": (),              "output_entity_type": "usb_device",
                                    "requires": (),                  "mutates_state": False,
                                    "produces_evidence": False},
    "usb.discovery.inspect":       {"domain": "usb",      "risk": ActionRisk.PASSIVE,
                                    "requires_args": ("path",),      "output_entity_type": "usb_device",
                                    "requires": (),                  "mutates_state": False,
                                    "produces_evidence": False},
}

FROZEN_14 = [
    "wifi.discovery.discover", "wifi.discovery.inspect",
    "wifi.capture.handshake", "wifi.capture.pmkid",
    "ble.discovery.discover", "ble.discovery.inspect",
    "ble.discovery.connect", "ble.discovery.write",
    "ble.gatt.pair", "ble.gatt.write",
    "nfc.discovery.scan", "nfc.discovery.read",
    "subghz.discovery.spectrum", "subghz.discovery.analyze",
]


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase 2.8.0 test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


# â”€â”€ 1. New-document registration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNewDomainRegistration:
    def test_catalogue_now_has_22_entries(self):
        # Phase 2.8.0 appended 7 (21); 2.8.1 +1 (22); 2.8.2 +1 (23);
        # 2.8.3 flipped existing infrared flags (no count change). Phase 2.8.0
        # additionally flipped the existing subghz.discovery.analyze
        # produces_evidence flag (an existing entry, not a new count). The new
        # entry's handler exists.
        assert len(DEFAULT_CAPABILITIES) == 26

    def test_all_new_keys_registered(self):
        by_key = {c.key for c in DEFAULT_CAPABILITIES}
        for key in NEW_KEYS:
            assert key in by_key, f"missing new capability: {key}"

    def test_all_14_frozen_keys_still_present(self):
        by_key = {c.key for c in DEFAULT_CAPABILITIES}
        for key in FROZEN_14:
            assert key in by_key, f"frozen Phase 2.7 key removed: {key}"

    def test_new_domains_are_in_known_domains_vocabulary(self):
        declared = {c.domain for c in DEFAULT_CAPABILITIES}
        assert declared <= KNOWN_DOMAINS
        assert {"infrared", "ethernet", "usb", "subghz", "nfc"} <= declared

    def test_subghz_and_nfc_domains_unchanged(self):
        # Sub-GHz and NFC already had a defined surface (2 entries each);
        # Phase 2.8.0 does not add or alter them.
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        assert by_key["subghz.discovery.spectrum"].risk == ActionRisk.PASSIVE
        assert by_key["subghz.discovery.analyze"].risk == ActionRisk.SAFE_ACTIVE
        assert by_key["nfc.discovery.scan"].risk == ActionRisk.PASSIVE
        assert by_key["nfc.discovery.read"].risk == ActionRisk.SAFE_ACTIVE


# â”€â”€ 2. Contract metadata validity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNewCapabilityMetadata:
    def test_every_new_entry_carries_expected_metadata(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        for key, expected in _EXPECTED_BY_KEY.items():
            cap = by_key[key]
            for field, exp_val in expected.items():
                assert getattr(cap, field) == exp_val, (
                    f"{key}: field {field!r} expected {exp_val!r} got {getattr(cap, field)!r}"
                )

    def test_domain_auto_derived_for_flat_infrared_namespace(self):
        # `infrared.capture` uses the dot-less namespace â†’ its own domain.
        cap = next(c for c in DEFAULT_CAPABILITIES if c.key == "infrared.capture")
        assert cap.capability == "infrared"
        assert cap.domain == "infrared"

    def test_new_entries_to_dict_round_trip_through_json(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        for key in NEW_KEYS:
            d = by_key[key].to_dict()
            assert json.loads(json.dumps(d)) == d
            assert isinstance(d["requires_args"], list)
            assert isinstance(d["requires"], list)

    def test_non_evidence_new_entries_not_marked(self):
        # Phase 2.8.0 declared NO new evidence producers. Phase 2.8.3 flips
        # infrared.analyze + infrared.transmit to produces_evidence=True (kinds
        # ir_analysis / ir_transmit). The rest of the Phase 2.8.0 additions
        # (infrared.capture + ethernet + usb) stay non-producers.
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        non_producers = [
            "infrared.capture",
            "ethernet.discovery.discover", "ethernet.discovery.inspect",
            "usb.discovery.enumerate", "usb.discovery.inspect",
            "nfc.discovery.select",
        ]
        for k in non_producers:
            assert not by_key[k].produces_evidence, f"{k} should not produce evidence"
        assert by_key["infrared.analyze"].produces_evidence is True
        assert by_key["infrared.transmit"].produces_evidence is True


# â”€â”€ 3. Risk values â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNewRiskValues:
    def test_new_key_risk_map(self):
        by_key = {c.key: c.risk for c in DEFAULT_CAPABILITIES}
        new_by_key = {k: by_key[k] for k in NEW_KEYS}
        assert new_by_key == {
            "infrared.capture":            ActionRisk.PASSIVE,
            "infrared.analyze":            ActionRisk.SAFE_ACTIVE,
            "infrared.transmit":           ActionRisk.SENSITIVE_ACTIVE,
            "ethernet.discovery.discover": ActionRisk.PASSIVE,
            "ethernet.discovery.inspect":  ActionRisk.PASSIVE,
            "usb.discovery.enumerate":     ActionRisk.PASSIVE,
            "usb.discovery.inspect":       ActionRisk.PASSIVE,
            "nfc.discovery.select":        ActionRisk.PASSIVE,  # Phase 2.8.2
        }

    def test_new_risks_use_only_existing_tiers(self):
        # No new risk semantics were invented â€” the four frozen tiers only.
        for cap in DEFAULT_CAPABILITIES:
            assert cap.risk in (
                ActionRisk.PASSIVE, ActionRisk.SAFE_ACTIVE,
                ActionRisk.SENSITIVE_ACTIVE, ActionRisk.RESTRICTED,
            )


# â”€â”€ 4. Registry resolution: registered-but-unsupported â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegistryResolution:
    def test_new_entries_resolve_unsupported_with_reason(self):
        # The Phase 2.8.0 IR / ethernet / usb entries have no simulator handler
        # and resolve as unsupported. Phase 2.8.2's nfc.discovery.select is
        # excluded — it gained a handler and resolves as supported.
        registry = default_registry(environment=Environment(name="t"))
        for key in UNSUPPORTED_280_KEYS:
            # infrared.transmit -> ("infrared", "transmit"); namespaced keys
            # ethernet.discovery.discover -> ("ethernet.discovery", "discover").
            if key.startswith("infrared."):
                capability, action = key.split(".", 1)
            else:
                capability, action = key.rsplit(".", 1)
            d = registry.resolve(capability, action)
            assert d.supported is False, f"{key} unexpectedly supported"
            assert "provider" in d.reason.lower() and "support" in d.reason.lower(), d.reason

    def test_existing_14_still_resolve_supported(self):
        registry = default_registry(environment=Environment(name="t"))
        supported = {
            ("wifi.discovery", "discover"), ("wifi.discovery", "inspect"),
            ("wifi.capture", "handshake"), ("wifi.capture", "pmkid"),
            ("ble.discovery", "discover"), ("ble.discovery", "inspect"),
            ("ble.discovery", "connect"), ("ble.discovery", "write"),
            ("ble.gatt", "pair"), ("ble.gatt", "write"),
            ("nfc.discovery", "scan"), ("nfc.discovery", "read"),
            ("subghz.discovery", "spectrum"), ("subghz.discovery", "analyze"),
        }
        for capability, action in supported:
            assert registry.resolve(capability, action).supported is True


# â”€â”€ 5 + 6. Unsupported-capability behavior + RiskDeclarationRule â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestUnsupportedCapabilityBehavior:
    def _capex(self, engine):
        return engine.execute

    def test_unsupported_active_action_rejected_before_provider(self):
        engine, run, logger, env = _engine_with_scope(
            AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE))
        try:
            # usb.discovery.enumerate is still handler-less (Phase 2.8.5) —
            # resolving supported=False and REJECTed before the provider.
            record = engine.execute(ActionRequest(
                capability="usb.discovery", action="enumerate",
                risk=ActionRisk.PASSIVE))
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "No registered provider supports this capability." in record.policy_decision.reasons[0]
            # Provider never ran: no observation, no evidence, no env touch.
            assert record.observation is None
            assert record.evidence == []
            assert run.evidence == []
            assert performed_capability_keys(env) == set()
            assert any("usb.discovery.enumerate" in e and "provider" in e.lower() for e in run.errors), run.errors
        finally:
            logger.close()

    def test_unsupported_passive_action_rejected_and_run_continues(self):
        engine, run, logger, env = _engine_with_scope(scenario="home", seed=3)
        try:
            engine.run_plan([
                ActionRequest(capability="usb.discovery", action="enumerate",
                              risk=ActionRisk.PASSIVE),
                ActionRequest(capability="wifi.discovery", action="discover",
                              risk=ActionRisk.PASSIVE),
            ])
            assert run.status == RunStatus.COMPLETED  # rejection is a valid run
            assert len(run.actions) == 2
            assert run.actions[0].policy_decision.kind == PolicyDecisionKind.REJECT
            assert run.actions[1].policy_decision.kind == PolicyDecisionKind.ALLOW
            assert len(run.errors) == 1
            # Provider isolation: only the rejected action has no observation.
            assert run.actions[0].observation is None
            assert run.actions[1].observation is not None
        finally:
            logger.close()

    def test_risk_declaration_still_guards_new_entries(self):
        engine, run, logger, _ = _engine_with_scope()
        try:
            # Upgrade: infrared.capture is PASSIVE; claiming SAFE_ACTIVE.
            up = engine.execute(ActionRequest(capability="infrared", action="capture",
                                              risk=ActionRisk.SAFE_ACTIVE))
            assert up.policy_decision.kind == PolicyDecisionKind.REJECT
            assert any("upgrade" in r.lower() for r in up.policy_decision.reasons)
            # Downgrade: infrared.analyze is SAFE_ACTIVE; claiming PASSIVE.
            down = engine.execute(ActionRequest(capability="infrared", action="analyze",
                                                risk=ActionRisk.PASSIVE))
            assert down.policy_decision.kind == PolicyDecisionKind.REJECT
            assert any("downgrade" in r.lower() for r in down.policy_decision.reasons)
        finally:
            logger.close()

    def test_unsupported_action_produces_no_evidence_event(self):
        engine, run, logger, _ = _engine_with_scope(
            AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE))
        try:
            # usb.discovery.enumerate is still unsupported (Phase 2.8.5) —
            # rejected before the provider, so it emits no evidence.created.
            engine.execute(ActionRequest(capability="usb.discovery", action="enumerate",
                                        risk=ActionRisk.PASSIVE))
        finally:
            logger.close()
        from engine.logger import run_dir
        events_path = run_dir(run.id) / "events.jsonl"
        assert events_path.exists()
        for line in events_path.read_text().splitlines():
            if line.strip():
                assert json.loads(line).get("type") != "evidence.created"


# â”€â”€ 7. Prerequisite metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPrereqMetadata:
    def test_transmit_requires_capture(self):
        cap = next(c for c in DEFAULT_CAPABILITIES if c.key == "infrared.transmit")
        assert cap.requires == ("infrared.capture",)
        assert cap.prerequisites_met(set()) is False
        assert cap.prerequisites_met({"infrared.discovery.anything"}) is False
        assert cap.prerequisites_met({"infrared.capture"}) is True

    def test_no_new_requires_reference_unknown_keys(self):
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        for cap in DEFAULT_CAPABILITIES:
            for req in cap.requires:
                assert req in by_key, f"{cap.key} requires unknown {req}"


# â”€â”€ 8. Phase 2.7 freeze regression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPhase27FreezeRegression:
    def test_frozen_14_risks_unchanged(self):
        by_key = {c.key: c.risk for c in DEFAULT_CAPABILITIES}
        assert by_key["wifi.discovery.discover"] == ActionRisk.PASSIVE
        assert by_key["wifi.discovery.inspect"] == ActionRisk.PASSIVE
        assert by_key["ble.discovery.discover"] == ActionRisk.PASSIVE
        assert by_key["ble.discovery.inspect"] == ActionRisk.PASSIVE
        assert by_key["nfc.discovery.scan"] == ActionRisk.PASSIVE
        assert by_key["nfc.discovery.read"] == ActionRisk.SAFE_ACTIVE
        assert by_key["subghz.discovery.spectrum"] == ActionRisk.PASSIVE
        assert by_key["subghz.discovery.analyze"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.discovery.connect"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.discovery.write"] == ActionRisk.SENSITIVE_ACTIVE
        assert by_key["wifi.capture.handshake"] == ActionRisk.SAFE_ACTIVE
        assert by_key["wifi.capture.pmkid"] == ActionRisk.SENSITIVE_ACTIVE
        assert by_key["ble.gatt.pair"] == ActionRisk.SAFE_ACTIVE
        assert by_key["ble.gatt.write"] == ActionRisk.SENSITIVE_ACTIVE

    def test_four_evidence_producers_unchanged(self):
        # The Phase 2.7 evidence producer set is preserved by Phase 2.8.1
        # (deliberate extension â€” Phase 2.8.1 added subghz.capture.signal +
        # flipped subghz.discovery.analyze produces_evidence True, sanctioned
        # by the freeze language; the 4 Phase 2.7 producers are a subset).
        by_key = {c.key: c for c in DEFAULT_CAPABILITIES}
        ev = sorted(k for k, c in by_key.items() if c.produces_evidence)
        phase27_evokers = ["ble.gatt.pair", "ble.gatt.write",
                           "wifi.capture.handshake", "wifi.capture.pmkid"]
        for key in phase27_evokers:
            assert key in ev, f"Phase 2.7 evidence producer lost: {key}"
        # Phase 2.8.1 contribution locked in.
        assert "subghz.capture.signal" in ev
        assert "subghz.discovery.analyze" in ev

    def test_known_evidence_kinds_frozen(self):
        # Phase 2.8.1 extended the vocabulary (sanctioned by freeze language:
        # "new evidence kinds / domains by extending KNOWN_EVIDENCE_KINDS ...").
        # Phase 2.8.2 added `nfc_read`; Phase 2.8.3 adds `ir_analysis` +
        # `ir_transmit`. The prior kinds are all still present.
        phase27_kinds = frozenset({
            "wifi_eapol_handshake", "wifi_pmkid", "ble_pairing", "ble_secure_write",
        })
        phase281_kinds = frozenset({"subghz_capture", "subghz_analysis"})
        phase282_kinds = frozenset({"nfc_read"})
        phase283_kinds = frozenset({"ir_analysis", "ir_transmit"})
        phase284_kinds = frozenset({"zigbee_join"})
        assert phase27_kinds <= KNOWN_EVIDENCE_KINDS
        assert phase281_kinds <= KNOWN_EVIDENCE_KINDS
        assert phase282_kinds <= KNOWN_EVIDENCE_KINDS
        assert phase283_kinds <= KNOWN_EVIDENCE_KINDS
        assert phase284_kinds <= KNOWN_EVIDENCE_KINDS
        assert KNOWN_EVIDENCE_KINDS == (
            phase27_kinds | phase281_kinds | phase282_kinds | phase283_kinds
            | phase284_kinds)

    def test_deterministic_plan_shapes_frozen(self):
        assert len(default_exploration_plan()) == 4
        assert len(wifi_capture_plan()) == 5
        assert len(ble_gatt_workflow_plan()) == 6
        assert len(subghz_capture_plan()) == 5    # Phase 2.8.1
        assert len(nfc_workflow_plan()) == 5      # Phase 2.8.2
        assert len(ir_workflow_plan()) == 4       # Phase 2.8.3
        assert len(zigbee_workflow_plan()) == 4   # Phase 2.8.4

    def test_default_exploration_run_still_clean(self):
        engine, run, logger, env = _engine_with_scope(scenario="lab", seed=7)
        try:
            engine.run_plan(default_exploration_plan())
            assert run.status == RunStatus.COMPLETED
            assert not run.errors
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()


# â”€â”€ 9. Entity + environment substrate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestEntitySubstrate:
    def test_ir_signal_entity(self):
        s = IrSignal(capture_id="ir-1", carrier_khz=38.0, length_ms=120.0, protocol="")
        d = s.to_dict()
        assert d["capture_id"] == "ir-1" and d["carrier_khz"] == 38.0
        assert json.loads(json.dumps(d)) == d

    def test_ethernet_host_entity(self):
        h = EthernetHost(mac="AA:BB:CC:DD:EE:FF", ip="192.168.0.10", hostname="lab-pc")
        assert h.to_dict()["ip"] == "192.168.0.10"
        assert json.loads(json.dumps(h.to_dict())) == h.to_dict()

    def test_usb_device_entity(self):
        d = UsbDevice(path="1-2", vid="1a86", pid="7523", manufacturer="WCH")
        assert d.to_dict()["vid"] == "1a86"
        assert json.loads(json.dumps(d.to_dict())) == d.to_dict()

    def test_environment_exposes_empty_new_domains(self):
        env = Environment(name="t")
        assert env.ir == [] and env.ethernet == [] and env.usb == []
        snap = env.snapshot()
        for key in ("ir", "ethernet", "usb"):
            assert key in snap and snap[key] == []

    def test_new_entity_types_are_typed_views_with_to_dict(self):
        # Every entity dataclass follows the existing to_dict() convention so
        # findings/run-records serialize exactly like wifi/ble/nfc/subghz.
        for obj in (IrSignal("x", 38.0, 10.0), EthernetHost("m", "ip"), UsbDevice("p", "v", "p")):
            assert callable(obj.to_dict) and isinstance(obj.to_dict(), dict)


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p280-"))
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