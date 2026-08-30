"""
tests/test_phase271_capability_metadata.py

Phase 2.7.1 regression suite â€” capability-contract metadata.

Verifies that the single existing `Capability` dataclass carries the metadata
the platform needs to describe Suryafool's future multi-domain (wifi / ble /
subghz / nfc / infrared / camera / ethernet / usb) hardware/security operation
surface â€” WITHOUT a second capability system â€” AND that the smallest
simulator support surfaces the metadata end to end:

  1.  every catalogue entry declares the contract metadata per the spec table
  2.  domain auto-derivation works for existing + future (infrared/camera/...)
      domains with no actions
  3.  invalid capability definitions (empty capability / empty action) raise
  4.  Capability.prerequisitesMet(observed_keys) flips on `requires`
  5.  performed_capability_keys(env) maps env.notes prefixes -> capability
      keys; passive action (wifi.discovery.discover) leaves no env note entry
      (its observation-only contract is preserved)
  6.  the registry surfaces the new metadata via .capability() from the same
      catalogue Phase 2.6 already consults â€” registry, policy, and provider
      architecture is untouched
  7.  the simulator consumes the contract: ble.discovery.write's prerequisite
      `ble.discovery.connect` is unsatisfied in a fresh lab env, becomes
      satisfied after the active_inspection plan runs connect (env.notes
      gains `ble_connected:<addr>`) â€” proving the catalogue metadata and
      real env state agree on observe->test->observe transitions
  8.  policy still gates BEFORE execution: a REJECTED ble.discovery.connect
      under the PASSIVE-only scope does NOT mutate env state, AND the
      authoritative `cap.mutates_state` flag is `True` on the catalogue
      entry (the new contract + the existing Phase 2.6 gate agree)
  9.  regression: catalogue count (10) and per-key risk mapping preserved;
      the original 5-positional-arg Capability(...) constructor is unchanged

Run without pytest:
    python -m tests.test_phase271_capability_metadata
"""

import json
import os
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None  # standalone runner works without pytest

from capabilities.base import (
    DEFAULT_CAPABILITIES,
    KNOWN_DOMAINS,
    Capability,
)
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
    default_exploration_plan,
)
from policy.policy import PolicyEngine
from simulator.environment import Environment
from simulator.scenarios import build_scenario
from simulator.simulator import performed_capability_keys


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        """Isolate run artifacts under a temp dir for every test."""
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


# â”€â”€ Test helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

LAB_TARGET = "AA:BB:CC:00:00:01"  # Suryafool-BLE-Target in scenario_lab


def _engine_with_scope(scope=None, scenario="lab", seed=42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="phase 2.7.1 test", scenario=scenario, seed=seed,
              authorization=scope or AuthorizationScope.default())
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


def _sensitive_active_scope():
    return AuthorizationScope.with_cumulative_tier(ActionRisk.SENSITIVE_ACTIVE)


def _device(env, address):
    for b in env.ble:
        if b.address == address:
            return b
    return None


# â”€â”€ 1. Contract fields declared on every catalogue entry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# The authoritative metadata block â€” mirrors the catalogue table in the
# Phase 2.7.1 plan. If a catalogue entry drifts from this, one of these
# assertions fails and tells the engineer exactly which field mismatched.
_EXPECTED_BY_KEY: dict[str, dict] = {
    "wifi.discovery.discover":   {"domain": "wifi",   "risk": ActionRisk.PASSIVE,
                                  "requires_args": (),             "output_entity_type": "wifi_network",
                                  "requires": (),                 "mutates_state": False,
                                  "produces_evidence": False,      "hardware": ""},
    "wifi.discovery.inspect":    {"domain": "wifi",   "risk": ActionRisk.PASSIVE,
                                  "requires_args": ("bssid",),     "output_entity_type": "wifi_network",
                                  "requires": (),                 "mutates_state": False,
                                  "produces_evidence": False,      "hardware": ""},
    "ble.discovery.discover":    {"domain": "ble",    "risk": ActionRisk.PASSIVE,
                                  "requires_args": (),             "output_entity_type": "ble_device",
                                  "requires": (),                 "mutates_state": False,
                                  "produces_evidence": False,      "hardware": ""},
    "ble.discovery.inspect":      {"domain": "ble",    "risk": ActionRisk.PASSIVE,
                                  "requires_args": ("address",),  "output_entity_type": "ble_device",
                                  "requires": (),                 "mutates_state": False,
                                  "produces_evidence": False,      "hardware": ""},
    "nfc.discovery.scan":         {"domain": "nfc",    "risk": ActionRisk.PASSIVE,
                                  "requires_args": (),             "output_entity_type": "nfc_tag",
                                  "requires": (),                 "mutates_state": False,
                                  "produces_evidence": False,      "hardware": ""},
    "nfc.discovery.select":       {"domain": "nfc",    "risk": ActionRisk.PASSIVE,
                                  "requires_args": ("uid",),       "output_entity_type": "nfc_tag",
                                  "requires": (),                 "mutates_state": True,
                                  "produces_evidence": False,      "hardware": ""},
    "nfc.discovery.read":         {"domain": "nfc",    "risk": ActionRisk.SAFE_ACTIVE,
                                  "requires_args": ("uid",),       "output_entity_type": "nfc_tag",
                                  "requires": (),                 "mutates_state": True,
                                  "produces_evidence": True,       "hardware": ""},
    "subghz.discovery.spectrum":  {"domain": "subghz","risk": ActionRisk.PASSIVE,
                                  "requires_args": (),             "output_entity_type": "subghz_signal",
                                  "requires": (),                 "mutates_state": False,
                                  "produces_evidence": False,      "hardware": ""},
    "subghz.discovery.analyze":   {"domain": "subghz","risk": ActionRisk.SAFE_ACTIVE,
                                  "requires_args": ("frequency_mhz",), "output_entity_type": "subghz_signal",
                                  "requires": (),                 "mutates_state": True,
                                  "produces_evidence": True,       "hardware": ""},
    # Phase 2.8.1 Sub-GHz/RF capture slice.
    "subghz.capture.signal":      {"domain": "subghz","risk": ActionRisk.SAFE_ACTIVE,
                                   "requires_args": ("frequency_mhz",), "output_entity_type": "subghz_signal",
                                   "requires": (),                 "mutates_state": True,
                                   "produces_evidence": True,      "hardware": ""},
    "ble.discovery.connect":      {"domain": "ble",    "risk": ActionRisk.SAFE_ACTIVE,
                                  "requires_args": ("address",),  "output_entity_type": "ble_device",
                                  "requires": (),                 "mutates_state": True,
                                  "produces_evidence": False,      "hardware": ""},
    "ble.discovery.write":        {"domain": "ble",    "risk": ActionRisk.SENSITIVE_ACTIVE,
                                   "requires_args": ("address", "characteristic", "value"),
                                   "output_entity_type": "ble_device",
                                   "requires": ("ble.discovery.connect",),
                                   "mutates_state": True,
                                   "produces_evidence": False,      "hardware": ""},
    "wifi.capture.handshake":     {"domain": "wifi",   "risk": ActionRisk.SAFE_ACTIVE,
                                    "requires_args": ("bssid",),     "output_entity_type": "wifi_network",
                                    "requires": (),                 "mutates_state": True,
                                    "produces_evidence": True,      "hardware": ""},
    "wifi.capture.pmkid":         {"domain": "wifi",   "risk": ActionRisk.SENSITIVE_ACTIVE,
                                    "requires_args": ("bssid",),     "output_entity_type": "wifi_network",
                                    "requires": ("wifi.capture.handshake",),
                                    "mutates_state": True,
                                    "produces_evidence": True,      "hardware": ""},
    "ble.gatt.pair":              {"domain": "ble",    "risk": ActionRisk.SAFE_ACTIVE,
                                    "requires_args": ("address",),  "output_entity_type": "ble_device",
                                    "requires": ("ble.discovery.connect",),
                                    "mutates_state": True,
                                    "produces_evidence": True,      "hardware": ""},
    "ble.gatt.write":             {"domain": "ble",    "risk": ActionRisk.SENSITIVE_ACTIVE,
                                    "requires_args": ("address", "characteristic", "value"),
                                    "output_entity_type": "ble_device",
                                    "requires": ("ble.gatt.pair",),
                                    "mutates_state": True,
                                    "produces_evidence": True,      "hardware": ""},
    # â”€â”€ Phase 2.8.0 multi-domain foundation (explicit-unsupported until
    #    their dedicated 2.8.x subphases add simulator handlers) â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "infrared.capture":           {"domain": "infrared", "risk": ActionRisk.PASSIVE,
                                    "requires_args": (),             "output_entity_type": "ir_signal",
                                    "requires": (),                 "mutates_state": False,
                                    "produces_evidence": False,      "hardware": ""},
    "infrared.analyze":           {"domain": "infrared", "risk": ActionRisk.SAFE_ACTIVE,
                                    "requires_args": ("capture_id",), "output_entity_type": "ir_signal",
                                    "requires": (),                 "mutates_state": True,
                                    "produces_evidence": True,      "hardware": ""},
    "infrared.transmit":          {"domain": "infrared", "risk": ActionRisk.SENSITIVE_ACTIVE,
                                    "requires_args": ("capture_id",), "output_entity_type": "ir_signal",
                                    "requires": ("infrared.capture",), "mutates_state": True,
                                    "produces_evidence": True,      "hardware": ""},
    "ethernet.discovery.discover": {"domain": "ethernet", "risk": ActionRisk.PASSIVE,
                                    "requires_args": (),             "output_entity_type": "ethernet_host",
                                    "requires": (),                 "mutates_state": False,
                                    "produces_evidence": False,      "hardware": ""},
    "ethernet.discovery.inspect":  {"domain": "ethernet", "risk": ActionRisk.PASSIVE,
                                    "requires_args": ("host",),     "output_entity_type": "ethernet_host",
                                    "requires": (),                 "mutates_state": False,
                                    "produces_evidence": False,      "hardware": ""},
    "usb.discovery.enumerate":    {"domain": "usb",     "risk": ActionRisk.PASSIVE,
                                    "requires_args": (),             "output_entity_type": "usb_device",
                                    "requires": (),                 "mutates_state": False,
                                    "produces_evidence": False,      "hardware": ""},
    "usb.discovery.inspect":      {"domain": "usb",     "risk": ActionRisk.PASSIVE,
                                    "requires_args": ("path",),     "output_entity_type": "usb_device",
                                    "requires": (),                 "mutates_state": False,
                                    "produces_evidence": False,      "hardware": ""},
    "zigbee.discovery.scan":     {"domain": "zigbee",  "risk": ActionRisk.PASSIVE,
                                    "requires_args": (),             "output_entity_type": "zigbee_network",
                                    "requires": (),                 "mutates_state": False,
                                    "produces_evidence": False,      "hardware": ""},
    "zigbee.discovery.inspect":  {"domain": "zigbee",  "risk": ActionRisk.PASSIVE,
                                    "requires_args": ("pan_id",),   "output_entity_type": "zigbee_node",
                                    "requires": (),                 "mutates_state": False,
                                    "produces_evidence": False,      "hardware": ""},
    "zigbee.discovery.join":     {"domain": "zigbee",  "risk": ActionRisk.SAFE_ACTIVE,
                                    "requires_args": ("pan_id", "ieee_address"),
                                    "output_entity_type": "zigbee_node",
                                    "requires": (),                 "mutates_state": True,
                                    "produces_evidence": True,       "hardware": ""},
}


class TestContractFields:
    """Every default catalogue entry exposes the Phase 2.7.1 contract."""

    def test_every_default_capability_carries_the_expected_metadata(self):
        for cap in DEFAULT_CAPABILITIES:
            expected = _EXPECTED_BY_KEY[cap.key]
            for field_name, expected_value in expected.items():
                actual = getattr(cap, field_name)
                assert actual == expected_value, (
                    f"{cap.key}: field {field_name!r} expected "
                    f"{expected_value!r} got {actual!r}"
                )

    def test_known_domains_open_set_includes_future_domains(self):
        # The intended domain vocabulary. Most have NO actions implemented yet;
        # the catalogue is open-set so future subphases can add a domain without
        # touching this constant or the dataclass.
        assert KNOWN_DOMAINS == frozenset({
            "wifi", "ble", "subghz", "nfc", "infrared", "camera", "ethernet", "usb",
            "zigbee",  # Phase 2.8.4
        })
        # All declared domains in the current catalogue must be a subset of
        # KNOWN_DOMAINS â€” guard against inventing a domain outside the
        # vocabulary when adding new entries.
        declared = {cap.domain for cap in DEFAULT_CAPABILITIES}
        assert declared <= KNOWN_DOMAINS

    def test_to_dict_roundtrip_carries_every_new_field(self):
        cap = DEFAULT_CAPABILITIES[0]
        d = cap.to_dict()
        # Original fields preserved.
        for k in ("name", "capability", "action", "risk", "description", "key"):
            assert k in d
        # New Phase 2.7.1 fields surfaced.
        for k in ("domain", "requires_args", "output_entity_type",
                  "requires", "hardware", "produces_evidence", "mutates_state"):
            assert k in d, f"to_dict missing new field: {k}"
        # requires_args/requires are JSON-serializable lists.
        assert isinstance(d["requires_args"], list)
        assert isinstance(d["requires"], list)
        # The full to_dict round-trips JSON for free (test that the report /
        # run record will serialize without surprises).
        assert json.loads(json.dumps(d)) == d

    def test_every_catalogue_entry_has_nonempty_domain(self):
        # __post_init__ guarantees this; sanity-check the catalogue as a whole.
        for cap in DEFAULT_CAPABILITIES:
            assert cap.domain, f"{cap.key}: domain auto-derivation failed"


# â”€â”€ 2. Domain auto-derivation (existing + future domains) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDomainAutoDerivation:
    def test_empty_domain_derives_from_namespace(self):
        cap = Capability("IR Capture", "infrared.capture", "snapshot",
                         ActionRisk.SAFE_ACTIVE, "Future infrared domain.")
        assert cap.domain == "infrared"
        # infrared is recognized as a future KNOWN_DOMAIN (no action exists
        # in the catalogue yet â€” this proves the contract is extensible).
        assert "infrared" in KNOWN_DOMAINS

    def test_explicit_domain_wins_over_derivation(self):
        cap = Capability("Custom IoT", "iw.spectrum", "sweep",
                         ActionRisk.PASSIVE, "An off-vocabulary domain test.",
                         domain="iw")
        assert cap.domain == "iw"

    def test_namespace_without_dot_is_its_own_domain(self):
        cap = Capability("Plain Cap", "legacy", "ping", ActionRisk.PASSIVE, "")
        assert cap.domain == "legacy"

    def test_namespace_with_multiple_dots_takes_first_segment(self):
        cap = Capability("Deep Cap", "wifi.capture.probe", "request",
                         ActionRisk.SAFE_ACTIVE, "")
        assert cap.domain == "wifi"


# â”€â”€ 3. Invalid capability definitions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _expect_value_error(build_callable):
    """Assert that `build_callable()` raises ValueError. Used when pytest is
    not installed â€” keeps Phase 2.7.1 tests runnable on the stdlib-only
    standalone runner like the rest of the repo."""
    try:
        build_callable()
    except ValueError:
        return
    except Exception as exc:  # wrong exception type
        raise AssertionError(
            f"expected ValueError, got {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError("expected ValueError, but no exception was raised")


class TestInvalidCapability:
    def test_empty_capability_raises(self):
        _expect_value_error(lambda: Capability(
            name="x", capability="", action="y", risk=ActionRisk.PASSIVE))

    def test_empty_action_raises(self):
        _expect_value_error(lambda: Capability(
            name="x", capability="wifi.discovery", action="",
            risk=ActionRisk.PASSIVE))

    def test_none_capability_raises(self):
        _expect_value_error(lambda: Capability(
            name="x", capability=None, action="y",   # type: ignore[arg-type]
            risk=ActionRisk.PASSIVE))


# â”€â”€ 4. prerequisites_met helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPrerequisitesMet:
    def test_empty_requires_always_satisfied(self):
        cap = Capability("Passive Cap", "wifi.discovery", "discover",
                          ActionRisk.PASSIVE, "")
        assert cap.requires == ()
        assert cap.prerequisites_met(set()) is True
        assert cap.prerequisites_met({"anything.at.all"}) is True

    def test_unmet_requires_returns_false(self):
        cap = Capability("Active Cap", "ble.discovery", "write",
                          ActionRisk.SENSITIVE_ACTIVE, "",
                          requires=("ble.discovery.connect",))
        assert cap.prerequisites_met(set()) is False
        assert cap.prerequisites_met({"ble.discovery.discover"}) is False

    def test_met_requires_returns_true(self):
        cap = Capability("Active Cap", "ble.discovery", "write",
                          ActionRisk.SENSITIVE_ACTIVE, "",
                          requires=("ble.discovery.connect",))
        assert cap.prerequisites_met({"ble.discovery.connect"}) is True
        # superset is also OK.
        assert cap.prerequisites_met(
            {"ble.discovery.connect", "ble.discovery.discover"}
        ) is True

    def test_multi_prereq_all_must_be_met(self):
        cap = Capability("Test", "test.cap", "run", ActionRisk.PASSIVE, "",
                          requires=("a.b", "c.d"))
        assert cap.prerequisites_met({"a.b"}) is False
        assert cap.prerequisites_met({"a.b", "c.d"}) is True
        assert cap.prerequisites_met({"c.d", "a.b", "noisy.detritus"}) is True


# â”€â”€ 5. performed_capability_keys(env) â€” simulator env â†’ capability keys â”€â”€â”€â”€â”€â”€â”€

class TestPerformedCapabilityKeys:
    def test_empty_env_yields_empty_set(self):
        env = Environment(name="empty")
        assert performed_capability_keys(env) == set()

    def test_fresh_build_scenario_has_no_notes(self):
        # No state-changing simulator action has run on a freshly built
        # scenario env, so performed_capability_keys returns the empty set
        # â€” proving the ACTIVE chain starts from a clean slate.
        for name in ("home", "lab", "crowded"):
            assert performed_capability_keys(build_scenario(name, seed=42)) == set()

    def test_ble_connected_note_maps_to_connect_capability(self):
        env = Environment(name="t")
        env.notes["ble_connected:AA:BB:CC:00:00:01"] = 1.0
        assert performed_capability_keys(env) == {"ble.discovery.connect"}

    def test_all_recognized_note_prefixes_map_to_capability_keys(self):
        env = Environment(name="t")
        env.notes["ble_connected:x"] = 0
        env.notes["ble_write:x:bat"] = 0
        env.notes["nfc_select:uid"] = 0
        env.notes["nfc_read:uid"] = 0
        env.notes["subghz_analyzed:433.92"] = 0
        env.notes["wifi_handshake:02:00:00:00:00:01"] = 0
        env.notes["wifi_pmkid:02:00:00:00:00:01"] = 0
        env.notes["ble_paired:x"] = 0
        env.notes["ble_secure_write:x:bat"] = 0
        assert performed_capability_keys(env) == {
            "ble.discovery.connect",
            "ble.discovery.write",
            "nfc.discovery.select",
            "nfc.discovery.read",
            "subghz.discovery.analyze",
            "wifi.capture.handshake",
            "wifi.capture.pmkid",
            "ble.gatt.pair",
            "ble.gatt.write",
        }

    def test_unknown_note_prefix_is_ignored(self):
        env = Environment(name="t")
        env.notes["some_future_action:x"] = 0
        env.notes["unrelated_key"] = 0
        assert performed_capability_keys(env) == set()

    def test_passive_action_leaves_no_performed_key_entry(self):
        """wifi.discovery.discover is observation-only: the simulator's passive
        action handler does NOT stamp env.notes, so the catalogue's
        `mutates_state=False` declaration and the env.recorded-keys view agree.
        Run the default exploration plan (4 PASSIVE actions) and confirm
        performed_capability_keys stays empty afterwards."""
        engine, run, logger, env = _engine_with_scope(scenario="lab", seed=7)
        try:
            engine.run_plan(default_exploration_plan())
            assert run.status == RunStatus.COMPLETED
            # No state-changing simulator action has run, so performed set is
            # empty â€” the observation-only catalogue entries ($(discover, $
            # inspect, $ scan, $ spectrum) leave env.notes untouched.
            assert performed_capability_keys(env) == set()
        finally:
            logger.close()


# â”€â”€ 6. Registry surfaces the new metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegistryConsumesMetadata:
    def test_registry_runtime_lookup_returns_metadata_carrier(self):
        env = build_scenario("lab", seed=42)
        registry = default_registry(environment=env)
        # A state-changing capability â€” the registry returns the SAME object the
        # catalogue declares with its Phase 2.7.1 metadata intact.
        cap_write = registry.capability("ble.discovery", "write")
        assert cap_write is not None
        assert cap_write.mutates_state is True
        assert cap_write.requires == ("ble.discovery.connect",)
        assert cap_write.requires_args == ("address", "characteristic", "value")
        assert cap_write.domain == "ble"
        assert cap_write.output_entity_type == "ble_device"
        assert cap_write.produces_evidence is False
        assert cap_write.hardware == ""

    def test_registry_lookup_passive_capability(self):
        env = build_scenario("home", seed=1)
        registry = default_registry(environment=env)
        cap = registry.capability("wifi.discovery", "discover")
        assert cap is not None
        assert cap.mutates_state is False
        assert cap.requires == ()
        assert cap.requires_args == ()
        assert cap.domain == "wifi"
        assert cap.output_entity_type == "wifi_network"

    def test_registry_capabilities_list_preserves_metadata(self):
        env = build_scenario("home", seed=1)
        registry = default_registry(environment=env)
        for cap in registry.capabilities():
            # __post_init__ has run; domain is non-empty for every catalogue
            # entry.
            assert cap.domain
            # mutates_state is set to the right value for every catalogue
            # entry â€” no entry has the default-mismatch where it's actually
            # state-changing but flagged False.
            expected = _EXPECTED_BY_KEY[cap.key]["mutates_state"]
            assert cap.mutates_state == expected, cap.key


# â”€â”€ 7. Simulator consumes metadata (observe -> test -> observe flips) â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestSimulatorConsumesMetadata:
    """The Catalogue metadata and the live env agree on prerequisite state."""

    def test_write_prereq_unsatisfied_in_fresh_lab_env(self):
        """ble.discovery.write declares requires=('ble.discovery.connect',).
        In a fresh lab env nothing has been performed, so
        `prerequisites_met(performed_capability_keys(env))` is False."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope())
        try:
            cap_write = engine.registry.capability("ble.discovery", "write")
            assert cap_write is not None
            assert cap_write.requires == ("ble.discovery.connect",)
            assert performed_capability_keys(env) == set()
            assert cap_write.prerequisites_met(performed_capability_keys(env)) is False
        finally:
            logger.close()

    def test_write_prereq_satisfied_after_active_inspection_plan(self):
        """After running the active_inspection plan under SENSITIVE_ACTIVE
        scope, env.notes has gained `ble_connected:<addr>` AND
        `ble_write:<addr>:<char>`, so performed_capability_keys returns the
        full active chain AND the `requires` of ble.discovery.write is met.
        This proves the catalogue's metadata and the simulator's env state
        agree on observe -> test -> observe transitions."""
        engine, run, logger, env = _engine_with_scope(_sensitive_active_scope(),
                                                     seed=42)
        try:
            engine.run_plan(active_inspection_plan())
            assert run.status == RunStatus.COMPLETED
            performed = performed_capability_keys(env)
            # Both connect and write keys observed.
            assert "ble.discovery.connect" in performed
            assert "ble.discovery.write" in performed
            cap_write = engine.registry.capability("ble.discovery", "write")
            assert cap_write.prerequisites_met(performed) is True
            # cap_write.policy-set authorizations + authoritative risk unchanged
            # (combine the contract flag with the existing Phase 2.6 gate).
            assert cap_write.mutates_state is True
            assert cap_write.risk == ActionRisk.SENSITIVE_ACTIVE
        finally:
            logger.close()

    def test_passive_action_metadata_consumption_does_not_alter_performed_set(self):
        """A successful PASSIVE action execution does NOT cause
        performed_capability_keys to grow â€” wifi.discovery.discover mutates
        no env state (its mutates_state=False catalogue metadata is the
        contract; the simulator's action handler agrees by not stamping
        env.notes). The active chain's `requires` against
        performed_capability_keys therefore stays invariant across passive
        steps â€” necessary for the future observe->upstream-test loop."""
        engine, run, logger, env = _engine_with_scope(scenario="lab", seed=11)
        try:
            # Snapshot before.
            assert performed_capability_keys(env) == set()
            # Run a passive action.
            record = engine.execute(
                ActionRequest(capability="wifi.discovery", action="discover",
                              risk=ActionRisk.PASSIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert record.observation is not None
            assert len(record.observation.entities) > 0
            # Snapshot after â€” passive action left no env note.
            assert performed_capability_keys(env) == set()
            # All Phase 2.7.1 passive metadata is self-consistent.
            cap = engine.registry.capability("wifi.discovery", "discover")
            assert cap.mutates_state is False
            assert cap.prerequisites_met(performed_capability_keys(env)) is True
        finally:
            logger.close()


# â”€â”€ 8. Policy rejects BEFORE execution â†’ no env mutation, contract flag is True â”€

class TestPolicyRejectDoesNotMutateState:
    """Phase 2.7.1 spec: 'Policy must remain before execution. Rejected actions
    must not mutate simulator state.' Combined with the new contract's
    `mutates_state=True` flag on the rejected capability, this is the strongest
    proof that the catalogue + policy + simulator all agree on the state guard."""

    def test_connect_rejected_under_passive_scope_does_not_mutate_env(self):
        engine, run, logger, env = _engine_with_scope()  # PASSIVE-only default
        try:
            cap = engine.registry.capability("ble.discovery", "connect")
            assert cap is not None
            # Contract assertion: connect is flagged state-changing.
            assert cap.mutates_state is True
            assert cap.risk == ActionRisk.SAFE_ACTIVE
            # Action is rejected because cap.risk isn't in the PASSIVE scope.
            record = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_TARGET})
            )
            assert record.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SAFE_ACTIVE" in record.policy_decision.reasons[0]
            # Provider never ran â†’ env untouched.
            assert performed_capability_keys(env) == set()
            assert all(not b.connected for b in env.ble)
            assert all(f"ble_connected:{b.address}" not in env.notes for b in env.ble)
            # authoritative_risk was still resolved onto the action record so
            # reports can show the catalogue's truth (Phase 2.6 invariant).
            assert record.authoritative_risk == ActionRisk.SAFE_ACTIVE
        finally:
            logger.close()

    def test_write_rejected_under_safe_active_scope_does_not_mutate_env(self):
        """Under a SAFE_ACTIVE-only scope connect ALLOWs (mutates env notes) but
        write REJECTs at the tier gate. The catalogue still marks write as
        stateful (mutates_state=True), and the REJECT leaves env state beyond
        the prior connect untouched â€” `ble_write:` does NOT appear in
        env.notes, performed_capability_keys does NOT gain
        `ble.discovery.write`."""
        engine, run, logger, env = _engine_with_scope(
            AuthorizationScope.with_cumulative_tier(ActionRisk.SAFE_ACTIVE)
        )
        try:
            # Connect first â€” ALLOWED, mutates env.
            rec1 = engine.execute(
                ActionRequest(capability="ble.discovery", action="connect",
                              risk=ActionRisk.SAFE_ACTIVE,
                              args={"address": LAB_TARGET})
            )
            assert rec1.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert performed_capability_keys(env) == {"ble.discovery.connect"}

            # Write attempt â€” REJECTED at tier gate.
            cap_write = engine.registry.capability("ble.discovery", "write")
            assert cap_write.mutates_state is True
            assert cap_write.risk == ActionRisk.SENSITIVE_ACTIVE
            # The new `requires` metadata flag for write is True against the
            # observed env state (connect IS recorded); the contract says
            # write WOULD be state-wise OK. The rejection here is the AUTH
            # gate, not the prereq gate. So we record that the env-state
            # prerequisites are met BUT authorization still blocks execution.
            assert cap_write.prerequisites_met(performed_capability_keys(env)) is True

            snapshot = performed_capability_keys(env)
            rec2 = engine.execute(
                ActionRequest(capability="ble.discovery", action="write",
                              risk=ActionRisk.SENSITIVE_ACTIVE,
                              args={"address": LAB_TARGET, "characteristic": "battery",
                                    "value": "75%"})
            )
            assert rec2.policy_decision.kind == PolicyDecisionKind.REJECT
            assert "SENSITIVE_ACTIVE" in rec2.policy_decision.reasons[0]
            # Provider never ran â†’ env state identical to the snapshot after
            # connect (no `ble_write:` entry added; performed set unchanged).
            assert performed_capability_keys(env) == snapshot
            assert "ble.discovery.write" not in performed_capability_keys(env)
            assert all(
                not k.startswith("ble_write:") for k in env.notes
            ), env.notes
        finally:
            logger.close()


# â”€â”€ 9. Regression â€” catalogue and constructor back-compat â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRegressionContract:
    def test_catalogue_count_unchanged(self):
        assert len(DEFAULT_CAPABILITIES) == 26

    def test_per_key_risk_mapping_unchanged(self):
        """Phase 2.7/2.7.2/2.7.3/2.8.1/2.8.2 catalogue regression — the four
        original PASSIVE actions, the two SAFE_ACTIVE NFC/Sub-GHz actions,
        the Phase 2.7 BLE Connect/Write entry risks, the Phase 2.7.2 Wi-Fi
        capture risks, the Phase 2.7.3 BLE GATT pair/write risks, the
        Phase 2.8.0 multi-domain entries, the Phase 2.8.1 Sub-GHz capture
        risk, and the Phase 2.8.2 NFC select (PASSIVE) are all preserved."""
        by_key = {cap.key: cap.risk for cap in DEFAULT_CAPABILITIES}
        assert by_key == {
            "wifi.discovery.discover":    ActionRisk.PASSIVE,
            "wifi.discovery.inspect":     ActionRisk.PASSIVE,
            "ble.discovery.discover":     ActionRisk.PASSIVE,
            "ble.discovery.inspect":      ActionRisk.PASSIVE,
            "nfc.discovery.scan":         ActionRisk.PASSIVE,
            "nfc.discovery.select":       ActionRisk.PASSIVE,
            "nfc.discovery.read":         ActionRisk.SAFE_ACTIVE,
            "subghz.discovery.spectrum":  ActionRisk.PASSIVE,
            "subghz.discovery.analyze":   ActionRisk.SAFE_ACTIVE,
            "ble.discovery.connect":      ActionRisk.SAFE_ACTIVE,
            "ble.discovery.write":        ActionRisk.SENSITIVE_ACTIVE,
            "wifi.capture.handshake":     ActionRisk.SAFE_ACTIVE,
            "wifi.capture.pmkid":         ActionRisk.SENSITIVE_ACTIVE,
            "ble.gatt.pair":              ActionRisk.SAFE_ACTIVE,
            "ble.gatt.write":             ActionRisk.SENSITIVE_ACTIVE,
            # Phase 2.8.0 multi-domain foundation.
            "infrared.capture":           ActionRisk.PASSIVE,
            "infrared.analyze":           ActionRisk.SAFE_ACTIVE,
            "infrared.transmit":          ActionRisk.SENSITIVE_ACTIVE,
            "ethernet.discovery.discover": ActionRisk.PASSIVE,
            "ethernet.discovery.inspect":  ActionRisk.PASSIVE,
            "usb.discovery.enumerate":     ActionRisk.PASSIVE,
            "usb.discovery.inspect":       ActionRisk.PASSIVE,
            # Phase 2.8.1 Sub-GHz/RF capture slice.
            "subghz.capture.signal":      ActionRisk.SAFE_ACTIVE,
            # Phase 2.8.4 Zigbee mesh slice.
            "zigbee.discovery.scan":      ActionRisk.PASSIVE,
            "zigbee.discovery.inspect":   ActionRisk.PASSIVE,
            "zigbee.discovery.join":      ActionRisk.SAFE_ACTIVE,
        }

    def test_positional_constructor_with_original_five_args_still_works(self):
        """A Capability constructed positionally with only the original five
        args (no Phase 2.7.1 metadata) gets the new fields' safe defaults â€”
        proves backward compatibility for any external caller."""
        cap = Capability("Legacy Cap", "test.cap", "run",
                         ActionRisk.PASSIVE, "test-only capability")
        # No new metadata declared â†’ defaults.
        assert cap.domain == "test"          # auto-derived from "test.cap"
        assert cap.requires_args == ()
        assert cap.output_entity_type == ""
        assert cap.requires == ()
        assert cap.hardware == ""
        assert cap.produces_evidence is False
        assert cap.mutates_state is False
        assert cap.prerequisites_met(set()) is True

    def test_default_capabilities_to_dict_round_trips_through_json(self):
        """Every catalogue entry serializes to JSON cleanly (the run record
        and reports rely on this)."""
        for cap in DEFAULT_CAPABILITIES:
            d = cap.to_dict()
            # round-trip must not raise
            json.loads(json.dumps(d))
            # risk serializes to its string value
            assert isinstance(d["risk"], str)
            # new fields are present and serializable
            for k in ("domain", "requires_args", "output_entity_type",
                      "requires", "hardware", "produces_evidence",
                      "mutates_state"):
                assert k in d, f"{cap.key} missing {k!r}"

    def test_engine_action_record_authoritative_risk_still_set(self):
        """Phase 2.6 invariant preserved: authoritative_risk is resolved on
        the ActionRecord from the SAME catalogue entry Phase 2.7.1 extended.
        Doing the right thing through the new contract."""
        engine, run, logger, env = _engine_with_scope(scenario="home", seed=3)
        try:
            record = engine.execute(
                ActionRequest(capability="wifi.discovery", action="discover",
                              risk=ActionRisk.PASSIVE)
            )
            assert record.policy_decision.kind == PolicyDecisionKind.ALLOW
            assert record.authoritative_risk == ActionRisk.PASSIVE
        finally:
            logger.close()


# â”€â”€ Standalone runner (no pytest required) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _run_all() -> int:
    import traceback
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-p271-"))
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
