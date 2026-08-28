"""
tests/test_phase2_core.py

Unit tests for the Phase 2 deterministic core:
  - capability registry
  - policy engine
  - simulator determinism
  - run engine end-to-end (no hardware, no LLM)
  - run record round-trip (to_dict / from_dict)
  - HTML report generation
"""

import json
import os
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None  # standalone runner works without pytest

from capabilities.registry import default_registry
from core.mission import (
    ActionRequest,
    ActionRisk,
    Run,
    RunStatus,
    PolicyDecisionKind,
)
from core.observation import Observation
from engine.logger import RunLogger, run_dir
from engine.runner import RunEngine, default_exploration_plan
from policy.policy import PolicyEngine
from reports.html_report import render_run, write_report
from simulator.environment import Environment
from simulator.entities import WifiNetwork
from simulator.scenarios import build_scenario, list_scenarios


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _tmp_runs_dir(tmp_path, monkeypatch):
        """Isolate run artifacts under a temp dir for every test."""
        monkeypatch.setenv("SURYAFOOL_RUNS_DIR", str(tmp_path / "runs"))


def make_engine(scenario: str = "home", seed: int = 42):
    env = build_scenario(scenario, seed=seed)
    registry = default_registry(environment=env)
    policy = PolicyEngine(registry=registry)
    run = Run(objective="test", scenario=scenario, seed=seed)
    logger = RunLogger(run)
    engine = RunEngine(registry=registry, policy=policy, run=run, logger=logger)
    return engine, run, logger, env


# ── Capability registry ───────────────────────────────────────────────────────

class TestRegistry:
    def test_lists_capabilities(self):
        registry = default_registry(environment=Environment("home"))
        keys = [c.key for c in registry.capabilities()]
        assert "wifi.discovery.discover" in keys
        assert "ble.discovery.discover" in keys
        assert "nfc.discovery.scan" in keys
        assert "subghz.discovery.spectrum" in keys

    def test_resolve_finds_simulator(self):
        registry = default_registry(environment=Environment("home"))
        d = registry.resolve("wifi.discovery", "discover")
        assert d.supported is True
        assert d.provider == "simulator"

    def test_resolve_unknown_capability(self):
        registry = default_registry(environment=Environment("home"))
        d = registry.resolve("quantum.teleport", "send")
        assert d.supported is False
        assert d.reason

    def test_resolve_unknown_action(self):
        registry = default_registry(environment=Environment("home"))
        d = registry.resolve("wifi.discovery", "destroy")
        assert d.supported is False


# ── Policy ────────────────────────────────────────────────────────────────────

class TestPolicy:
    def test_unknown_capability_rejected(self):
        engine, run, logger, _ = make_engine()
        record = engine.execute(ActionRequest(capability="quantum.teleport", action="send"))
        assert record.policy_decision.kind == PolicyDecisionKind.REJECT
        assert "Unknown capability" in record.policy_decision.reasons[0]
        logger.close()

    def test_unknown_action_rejected(self):
        engine, run, logger, _ = make_engine()
        record = engine.execute(ActionRequest(capability="wifi.discovery", action="destroy"))
        assert record.policy_decision.kind == PolicyDecisionKind.REJECT
        logger.close()

    def test_caller_cannot_upgrade_passive_to_restricted(self):
        """A caller declaring risk=RESTRICTED on a catalogue-PASSIVE action
        (wifi.discovery.discover) must be rejected — ActionRequest.risk is
        caller self-disclosure that must match the catalogue. The request is
        rejected at the RiskDeclarationRule gate (upgrade mismatch), not at
        the RiskTierAuthorizedRule gate, because the request never gets that
        far with a mismatched risk."""
        engine, run, logger, _ = make_engine()
        record = engine.execute(
            ActionRequest(capability="wifi.discovery", action="discover",
                          risk=ActionRisk.RESTRICTED)
        )
        assert record.policy_decision.kind == PolicyDecisionKind.REJECT
        assert "RESTRICTED" in record.policy_decision.reasons[0]
        assert "upgrade" in record.policy_decision.reasons[0].lower()
        logger.close()

    def test_active_tier_blocked_without_authorization(self):
        """Selecting scenario='home' (or 'lab') no longer grants any risk tier.
        nfc.discovery.read is SAFE_ACTIVE in the catalogue; with request.risk
        matching the catalogue, it passes RiskDeclarationRule but is rejected
        by RiskTierAuthorizedRule because the default AuthorizationScope is
        PASSIVE-only. This is the core 'Scenario != Authorization' regression."""
        engine, run, logger, _ = make_engine(scenario="home")
        record = engine.execute(
            ActionRequest(capability="nfc.discovery", action="read",
                          risk=ActionRisk.SAFE_ACTIVE)
        )
        assert record.policy_decision.kind == PolicyDecisionKind.REJECT
        assert "SAFE_ACTIVE" in record.policy_decision.reasons[0]
        assert "AuthorizationScope" in record.policy_decision.reasons[0]
        logger.close()

    def test_passive_allowed(self):
        engine, run, logger, _ = make_engine()
        record = engine.execute(ActionRequest(capability="wifi.discovery", action="discover"))
        assert record.policy_decision.kind == PolicyDecisionKind.ALLOW
        logger.close()

    def test_risk_downgrade_rejected(self):
        """Callers cannot claim a lower risk than the catalogue declares.

        nfc.discovery.read is declared SAFE_ACTIVE in the catalogue; a request
        claiming PASSIVE must be rejected even if everything else is valid.
        """
        engine, run, logger, _ = make_engine()
        record = engine.execute(
            ActionRequest(capability="nfc.discovery", action="read",
                          risk=ActionRisk.PASSIVE)
        )
        assert record.policy_decision.kind == PolicyDecisionKind.REJECT
        assert "Risk downgrade" in record.policy_decision.reasons[0]
        logger.close()


# ── Simulator ─────────────────────────────────────────────────────────────────

class TestSimulator:
    def test_scenario_listing(self):
        names = [s["name"] for s in list_scenarios()]
        assert "home" in names and "lab" in names and "crowded" in names

    def test_deterministic_scenarios(self):
        e1 = build_scenario("crowded", seed=7)
        e2 = build_scenario("crowded", seed=7)
        assert len(e1.wifi) == len(e2.wifi) == 12
        assert e1.wifi[0].ssid == e2.wifi[0].ssid
        assert e1.wifi[0].rssi == e2.wifi[0].rssi

    def test_discover_returns_structured_observations(self):
        env = build_scenario("home", seed=42)
        registry = default_registry(environment=env)
        obs = registry.resolve("wifi.discovery", "discover")
        assert obs.supported
        provider = registry.providers()[0]
        result = provider.execute("wifi.discovery", "discover")
        assert isinstance(result, Observation)
        assert len(result.entities) == 4
        assert result.entities[0].type == "wifi_network"
        assert result.entities[0].attributes["ssid"] == "HomeNet-5G"
        # full 6-octet MAC: 02:00:00:00:00:11
        assert result.entities[0].id == "02:00:00:00:00:11"

    def test_nfc_read_marks_env_state(self):
        env = build_scenario("lab", seed=42)
        provider = default_registry(environment=env).providers()[0]
        # Phase 2.8.2: read now requires select-on-same-uid as per-target prereq.
        provider.execute("nfc.discovery", "select", {"uid": "04:DE:AD:BE:EF:01"})
        result = provider.execute("nfc.discovery", "read", {"uid": "04:DE:AD:BE:EF:01"})
        assert len(result.entities) == 1
        assert f"nfc_read:04:DE:AD:BE:EF:01" in env.notes


# ── Run engine ────────────────────────────────────────────────────────────────

class TestRunEngine:
    def test_full_plan_completes(self):
        engine, run, logger, _ = make_engine(scenario="lab", seed=3)
        engine.run_plan(default_exploration_plan())
        logger.close()
        assert run.status == RunStatus.COMPLETED
        assert len(run.actions) == 4
        assert len(run.observations) == 4
        assert not run.errors
        assert run.final_summary

    def test_rejected_actions_are_recorded_but_run_continues(self):
        engine, run, logger, _ = make_engine(scenario="home", seed=1)
        engine.run_plan([
            ActionRequest(capability="quantum.teleport", action="send"),
            ActionRequest(capability="wifi.discovery", action="discover"),
        ])
        logger.close()
        assert run.status == RunStatus.COMPLETED
        assert len(run.actions) == 2
        assert len(run.errors) == 1
        assert run.actions[0].policy_decision.kind == PolicyDecisionKind.REJECT

    def test_run_record_roundtrip(self):
        engine, run, logger, _ = make_engine(scenario="lab", seed=3)
        engine.run_plan(default_exploration_plan())
        logger.close()

        d = run.to_dict()
        restored = Run.from_dict(d)
        assert restored.id == run.id
        assert restored.status == run.status
        assert len(restored.actions) == len(run.actions)
        # Risk enum restored, not a str
        assert restored.actions[0].request.risk == run.actions[0].request.risk
        assert isinstance(restored.actions[0].request.risk, ActionRisk)
        assert restored.observations[0].entities[0].confidence is not None

    def test_events_written_to_jsonl(self):
        engine, run, logger, _ = make_engine(scenario="home", seed=2)
        engine.run_plan(default_exploration_plan())
        logger.close()
        d = run_dir(run.id)
        events_path = d / "events.jsonl"
        assert events_path.exists()
        lines = [l for l in events_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) >= 2
        first = json.loads(lines[0])
        assert "type" in first


# ── HTML report ───────────────────────────────────────────────────────────────

class TestReport:
    def test_render_contains_sections(self):
        engine, run, logger, _ = make_engine(scenario="lab", seed=3)
        engine.run_plan(default_exploration_plan())
        logger.close()
        html = render_run(run)
        assert "<title>" in html
        assert "TIMELINE" in html
        assert "FINDINGS" in html
        assert "CAPABILITIES" in html
        assert "badge completed" in html
        assert run.id in html

    def test_write_report_file(self, tmp_path):
        engine, run, logger, _ = make_engine(scenario="home", seed=1)
        engine.run_plan(default_exploration_plan())
        logger.close()
        out = tmp_path / "report.html"
        write_report(run, out)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_report_escapes_user_input(self):
        """XSS regression: adversarial strings in run/entity data must be escaped."""
        run = Run(
            objective='<script>alert("xss")</script>',
            scenario="home",
            seed=1,
            status=RunStatus.COMPLETED,
        )
        from core.observation import Entity
        from core.confidence import Confidence
        run.findings.append({
            "entity_type": "wifi_network",
            "label": '<img src=x onerror=alert(1)>',
            "id": '" onmouseover="alert(2)',
            "attributes": {"ssid": "<svg/onload=alert(3)>"},
            "confidence": "CONFIRMED",
        })
        html = render_run(run)
        assert "<script>" not in html
        assert "<img src=x" not in html
        assert "<svg/onload" not in html
        assert "&lt;script&gt;" in html


# ── Standalone runner (no pytest required) ────────────────────────────────────

class _FakeTmpPath:
    """Minimal stand-in for pytest's tmp_path fixture."""

    def __init__(self, base: Path):
        self._base = base

    def __truediv__(self, name: str) -> Path:
        p = self._base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


def _run_all() -> int:
    """Run every test_* method in every Test* class without pytest.

    Exits 1 on the first failure. pytest can still collect these the
    normal way if it's available.
    """
    import traceback
    import tempfile

    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="suryafool-tests-"))
    os.environ["SURYAFOOL_RUNS_DIR"] = str(tmp / "runs")
    for name, cls in sorted(globals().items()):
        if not name.startswith("Test") or not isinstance(cls, type):
            continue
        for attr in sorted(dir(cls)):
            if not attr.startswith("test_"):
                continue
            test_name = f"{name}.{attr}"
            try:
                fn = getattr(cls(), attr)
                if attr == "test_write_report_file":
                    fn(_FakeTmpPath(tmp))
                else:
                    fn()
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