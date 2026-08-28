"""
engine/runner.py

The RunEngine — central coordinator for a Suryafool run.

Flow per action:

  orchestrator submits ActionRequest
        │
        ▼
  CapabilityRegistry.resolve()        → CapabilityDecision
        │
        ▼
  PolicyEngine.validate()             → PolicyDecision (ALLOW | REJECT)
        │                 │
        │ (REJECT)        │ (ALLOW)
        ▼                 ▼
  record rejection     provider.execute() → Observation
        │                 │
        └────────┬────────┘
                 ▼
            ActionRecord appended to Run
                 │
                 ▼
           events emitted (JSONL)
                 │
                 ▼
           run.json updated

The engine never mutates state outside this flow. It is deterministic: the
same input sequence yields the same run record (given the same scenario seed).
"""

from __future__ import annotations

import time
from typing import Any, Optional, Sequence

from capabilities.registry import CapabilityRegistry
from core.mission import (
    ActionRecord,
    ActionRequest,
    ActionRisk,
    Run,
    RunStatus,
)
from core.events import LOG, ERROR, AGENT_STATUS, FINDING_CREATED, SCAN_PROGRESS, EVIDENCE_CREATED
from engine.logger import RunLogger
from policy.policy import PolicyContext, PolicyEngine


# ── Default plan (deterministic exploration sequence) ─────────────────────────

def default_exploration_plan() -> list[ActionRequest]:
    """A simple, deterministic plan: discover across all four protocols.

    Future phases (orchestrator agent) will produce richer plans from the
    objective. For Phase 2 the plan is fixed and reproducible.
    """
    return [
        ActionRequest(capability="wifi.discovery",  action="discover"),
        ActionRequest(capability="ble.discovery",   action="discover"),
        ActionRequest(capability="nfc.discovery",   action="scan"),
        ActionRequest(capability="subghz.discovery",action="spectrum"),
    ]


def active_inspection_plan() -> list[ActionRequest]:
    """Phase 2.7 deterministic plan: a complete active BLE lifecycle over the
    `lab` scenario target AA:BB:CC:00:00:01.

        discover -> inspect (initial) -> connect (SAFE_ACTIVE) ->
        write (SENSITIVE_ACTIVE) -> inspect (reflects changed state)

    Each request.risk MUST equal the catalogue cap.risk (RiskDeclarationRule
    rejects mismatches in both directions), so risks are set explicitly. The
    plan targets the lab scenario's literal BLE addresses, so it is
    seed-independent for those targets. Against a non-lab scenario the active
    actions simply find no matching target and return structured 'unknown
    target' failure Observations (no crash). Under a PASSIVE-only
    AuthorizationScope, connect + write are rejected at the policy gate before
    the provider is invoked — a valid, recorded run that demonstrates the
    authorization boundary deterministically.
    """
    return [
        ActionRequest(capability="ble.discovery", action="discover",
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="ble.discovery", action="inspect",
                      args={"address": "AA:BB:CC:00:00:01"},
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="ble.discovery", action="connect",
                      args={"address": "AA:BB:CC:00:00:01"},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="ble.discovery", action="write",
                      args={"address": "AA:BB:CC:00:00:01",
                            "characteristic": "battery", "value": "75%"},
                      risk=ActionRisk.SENSITIVE_ACTIVE),
        ActionRequest(capability="ble.discovery", action="inspect",
                      args={"address": "AA:BB:CC:00:00:01"},
                      risk=ActionRisk.PASSIVE),
    ]


def wifi_capture_plan() -> list[ActionRequest]:
    """Phase 2.7.2 deterministic plan: a complete Wi-Fi capture lifecycle
    over the lab scenario target 02:00:00:00:00:01 (LAB-INTERNAL, WPA3).

        discover -> inspect (initial) -> capture.handshake (SAFE_ACTIVE) ->
        capture.pmkid (SENSITIVE_ACTIVE) -> inspect (reflects changed state)

    Each request.risk equals the catalogue cap.risk (RiskDeclarationRule
    rejects mismatches in both directions). The plan targets the lab scenario
    literal WPA-encrypted network, so it is seed-independent for that target.
    Against a non-lab scenario the active actions find no matching target and
    return structured 'unknown target' failure Observations (no crash). Under
    a PASSIVE-only AuthorizationScope the captures are rejected at the policy
    gate before the provider is invoked — a valid, recorded run that
    demonstrates the authorization boundary deterministically. Under
    SAFE_ACTIVE-only scope, capture.handshake ALLOWs but capture.pmkid
    REJECTs at the tier gate (cumulative stops there).
    """
    return [
        ActionRequest(capability="wifi.discovery", action="discover",
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="wifi.discovery", action="inspect",
                      args={"bssid": "02:00:00:00:00:01"},
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="wifi.capture", action="handshake",
                      args={"bssid": "02:00:00:00:00:01"},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="wifi.capture", action="pmkid",
                      args={"bssid": "02:00:00:00:00:01"},
                      risk=ActionRisk.SENSITIVE_ACTIVE),
        ActionRequest(capability="wifi.discovery", action="inspect",
                      args={"bssid": "02:00:00:00:00:01"},
                      risk=ActionRisk.PASSIVE),
    ]


def ble_gatt_workflow_plan() -> list[ActionRequest]:
    """Phase 2.7.3 deterministic plan: a complete stateful BLE GATT
    lifecycle over the lab scenario target AA:BB:CC:00:00:01
    (Suryafool-BLE-Target).

        discover -> inspect (initial) ->
        ble.discovery.connect (Phase 2.7 SAFE_ACTIVE) ->
        ble.gatt.pair        (NEW SAFE_ACTIVE  — pairing session) ->
        ble.gatt.write       (NEW SENSITIVE_ACTIVE — encrypted write) ->
        inspect (reflects paired + secure-write state)

    The plan layers the new `ble.gatt` namespace on top of the existing
    `ble.discovery` connect (Phase 2.7), exactly parallel to how Phase 2.7.2
    layered `wifi.capture` on top of `wifi.discovery`. Each request.risk
    equals the authoritative catalogue cap.risk (RiskDeclarationRule
    rejects mismatches in both directions). The plan targets the lab scenario
    literal BLE address, so it is seed-independent for that target. Against a
    non-lab scenario the active actions find no matching target and return
    structured 'unknown target' failure Observations (no crash). Under a
    PASSIVE-only AuthorizationScope, connect + pair + write are all rejected
    at the policy gate before the provider is invoked — a valid, recorded
    run. Under SAFE_ACTIVE-only scope, connect ALLOWs and pair ALLOWs but
    ble.gatt.write REJECTs at the tier gate (cumulative stops at the first
    SENSITIVE_ACTIVE step). Under SENSITIVE_ACTIVE scope the full chain
    completes and the final inspect summary shows 'paired; 1 secure
    characteristic(s) written'.
    """
    return [
        ActionRequest(capability="ble.discovery", action="discover",
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="ble.discovery", action="inspect",
                      args={"address": "AA:BB:CC:00:00:01"},
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="ble.discovery", action="connect",
                      args={"address": "AA:BB:CC:00:00:01"},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="ble.gatt", action="pair",
                      args={"address": "AA:BB:CC:00:00:01"},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="ble.gatt", action="write",
                      args={"address": "AA:BB:CC:00:00:01",
                            "characteristic": "battery", "value": "encrypted:0xABCD"},
                      risk=ActionRisk.SENSITIVE_ACTIVE),
        ActionRequest(capability="ble.discovery", action="inspect",
                      args={"address": "AA:BB:CC:00:00:01"},
                      risk=ActionRisk.PASSIVE),
    ]


def subghz_capture_plan() -> list[ActionRequest]:
    """Phase 2.8.1 deterministic plan: a complete stateful Sub-GHz/RF
    capture lifecycle over the lab scenario (subghz=[433.92 OOK (-55 dBm),
    868.30 FSK (-68 dBm)]).

        spectrum (PASSIVE, enumerates the 2 lab signals) ->
        subghz.capture.signal @ 433.92 (SAFE_ACTIVE, mutates SubGhzSignal.captured + sample_count + capture_quality; produces 1 subghz_capture evidence) ->
        subghz.discovery.analyze @ 433.92 (SAFE_ACTIVE, sets decoded_protocol_hint; per-target prereq s.captured=True met; produces 1 subghz_analysis evidence) ->
        subghz.capture.signal @ 868.30 (SAFE_ACTIVE, produces 1 subghz_capture evidence) ->
        subghz.discovery.analyze @ 868.30 (SAFE_ACTIVE, produces 1 subghz_analysis evidence)

    Final result: 5 actions, 4 evidence (2 x subghz_capture + 2 x subghz_analysis).
    Each request.risk equals the authoritative catalogue cap.risk
    (RiskDeclarationRule rejects mismatches in both directions). The plan
    targets the lab scenario's literal Sub-GHz frequencies, so it is
    seed-independent for those targets. Against a non-lab scenario the active
    actions find no matching frequency and return structured 'unknown target'
    failure Observations (no crash). Under a PASSIVE-only AuthorizationScope,
    both SAFE_ACTIVE actions (capture + analyze) are rejected at the policy
    gate before the provider is invoked — 4 errors recorded, run COMPLETED,
    environment unchanged, zero evidence. Under SAFE_ACTIVE scope the full
    chain completes and both signals reach captured=True + decoded_protocol_hint
    set + env.notes['subghz_analyzed:<freq>'] stamped.
    """
    return [
        ActionRequest(capability="subghz.discovery", action="spectrum",
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="subghz.capture", action="signal",
                      args={"frequency_mhz": 433.92},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="subghz.discovery", action="analyze",
                      args={"frequency_mhz": 433.92},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="subghz.capture", action="signal",
                      args={"frequency_mhz": 868.30},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="subghz.discovery", action="analyze",
                      args={"frequency_mhz": 868.30},
                      risk=ActionRisk.SAFE_ACTIVE),
    ]


def nfc_workflow_plan() -> list[ActionRequest]:
    """Phase 2.8.2 deterministic plan: complete stateful NFC/RFID scan ->
    select -> read lifecycle over the lab scenario tags
    (nfc=[04:DE:AD:BE:EF:01 MIFARE Classic 1K (ndef_supported=True),
    04:DE:AD:BE:EF:02 NTAG215 (ndef_supported=True)]).

        scan (PASSIVE, enumerates the 2 lab tags) ->
        nfc.discovery.select @ 04:DE:AD:BE:EF:01 (PASSIVE, mutates NfcTag.selected=True) ->
        nfc.discovery.read    @ 04:DE:AD:BE:EF:01 (SAFE_ACTIVE, per-target prereq met; produces 1 nfc_read evidence) ->
        nfc.discovery.select @ 04:DE:AD:BE:EF:02 (PASSIVE, mutates NfcTag.selected=True) ->
        nfc.discovery.read    @ 04:DE:AD:BE:EF:02 (SAFE_ACTIVE, produces 1 nfc_read evidence)

    Final result: 5 actions, 2 evidence (2 x nfc_read). The two lab tags
    both have ndef_supported=True; reads only succeed after the per-target
    `t.selected=True` gate is satisfied. Each request.risk equals the
    authoritative catalogue cap.risk (RiskDeclarationRule rejects
    mismatches in both directions). The plan targets the lab scenario's
    literal NFC UIDs, so it is seed-independent for those targets. Against
    a non-lab scenario the active reads find no matching tag and return
    structured 'unknown target' failure Observations (no crash). Under a
    PASSIVE-only AuthorizationScope, both SAFE_ACTIVE reads are rejected at
    the policy gate before the provider is invoked — 2 errors recorded,
    run COMPLETED, environment unchanged, zero evidence. Under SAFE_ACTIVE
    scope the full chain completes and both tags reach selected=True +
    read=True + 2 nfc_read evidence records. NFC write is NOT in this plan
    (deliberately deferred).
    """
    return [
        ActionRequest(capability="nfc.discovery", action="scan",
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="nfc.discovery", action="select",
                      args={"uid": "04:DE:AD:BE:EF:01"},
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="nfc.discovery", action="read",
                      args={"uid": "04:DE:AD:BE:EF:01"},
                      risk=ActionRisk.SAFE_ACTIVE),
        ActionRequest(capability="nfc.discovery", action="select",
                      args={"uid": "04:DE:AD:BE:EF:02"},
                      risk=ActionRisk.PASSIVE),
        ActionRequest(capability="nfc.discovery", action="read",
                      args={"uid": "04:DE:AD:BE:EF:02"},
                      risk=ActionRisk.SAFE_ACTIVE),
    ]


class RunEngine:
    def __init__(self,
                 registry: CapabilityRegistry,
                 policy: PolicyEngine,
                 run: Run,
                 logger: RunLogger):
        self.registry = registry
        self.policy = policy
        self.run = run
        self.logger = logger

    # ── Main entry ────────────────────────────────────────────────────────────
    def run_plan(self, plan: Sequence[ActionRequest]) -> Run:
        self.run.status = RunStatus.RUNNING
        self.logger.write_record()
        self.logger.log_event(AGENT_STATUS,
                              agent="orchestrator",
                              status="started",
                              run_id=self.run.id,
                              objective=self.run.objective)

        for request in plan:
            self.execute(request)
            if self.run.status == RunStatus.FAILED:
                break

        self.run.completed_at = time.time()
        if self.run.status == RunStatus.RUNNING:
            self.run.status = RunStatus.COMPLETED
        self.run.final_summary = self._summarize()
        self.logger.write_record()
        self.logger.log_event(AGENT_STATUS,
                              agent="orchestrator",
                              status=self.run.status.value,
                              run_id=self.run.id)
        return self.run

    # ── Single action ─────────────────────────────────────────────────────────
    def execute(self, request: ActionRequest) -> ActionRecord:
        record = ActionRecord(request=request)
        try:
            cap_decision = self.registry.resolve(request.capability, request.action)
            record.capability_decision = cap_decision

            # Authoritative risk from the catalogue — resolved ONCE here, used
            # by the policy layer (via cap.risk lookups) and persisted for
            # reports. Authorization decisions consult cap.risk, not
            # request.risk (the caller self-disclosure).
            cap = self.registry.capability(request.capability, request.action)
            if cap is not None:
                record.authoritative_risk = cap.risk

            ctx = PolicyContext(
                registry=self.registry,
                run_status=self.run.status,
                authorization=self.run.authorization,  # explicit, scenario-independent
            )
            policy_decision = self.policy.validate(request, ctx)
            record.policy_decision = policy_decision

            if not policy_decision.allowed:
                self.run.errors.append(
                    f"Action {request.capability}.{request.action} rejected: "
                    + "; ".join(policy_decision.reasons)
                )
                self.logger.log_event(
                    ERROR,
                    message="policy rejected action",
                    capability=request.capability,
                    action=request.action,
                    reasons=policy_decision.reasons,
                )
            else:
                provider = self._get_provider(cap_decision.provider)
                observation = provider.execute(
                    request.capability, request.action, request.args
                )
                record.observation = observation
                self.run.observations.append(observation)
                self.run.capabilities_used.append(f"{request.capability}.{request.action}")
                if observation.entities:
                    self.run.findings.extend(
                        {"entity_type": e.type, "label": e.label, "id": e.id,
                         "attributes": e.attributes, "confidence": e.confidence.value}
                        for e in observation.entities
                    )
                self.logger.log_event(
                    FINDING_CREATED,
                    finding={
                        "capability": request.capability,
                        "action": request.action,
                        "summary": observation.summary,
                        "entities": [e.to_dict() for e in observation.entities],
                    },
                )
                # Phase 2.7.5 — propagate any durable evidence surfaced by the
                # provider. The simulator is the source of truth for WHAT was
                # captured (frame_count, encryption, etc.); the engine is the
                # source of truth for provenance the simulator could not see
                # (request.id, run.id). Policy-rejected actions never reach
                # here — observation is None, no evidence is created. Failed
                # capture paths return Observations with `evidence=[]`, so
                # the loop below is a no-op for them.
                record.evidence = list(observation.evidence)
                for ev in observation.evidence:
                    if not ev.source_action_id:
                        ev.source_action_id = request.id
                    self.run.evidence.append(ev)
                    self.logger.log_event(
                        EVIDENCE_CREATED,
                        evidence=ev.to_dict(),
                        source_action_id=ev.source_action_id,
                        run_id=self.run.id,
                    )
        except Exception as exc:  # unexpected error — record it, don't crash
            record.error = str(exc)
            self.run.errors.append(
                f"Action {request.capability}.{request.action} crashed: {exc}"
            )
            self.run.status = RunStatus.FAILED
            self.logger.log_event(
                ERROR,
                message="action crashed",
                capability=request.capability,
                action=request.action,
                error=str(exc),
            )

        record.completed_at = time.time()
        self.run.actions.append(record)
        self.logger.write_record()
        return record

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_provider(self, name: str):
        for provider in self.registry.providers():
            if provider.name == name:
                return provider
        raise RuntimeError(f"Provider not found: {name}")

    def _summarize(self) -> str:
        n_actions = len(self.run.actions)
        n_observations = len(self.run.observations)
        n_findings = len(self.run.findings)
        n_evidence = len(self.run.evidence)
        n_errors = len(self.run.errors)
        return (
            f"Completed {n_actions} action(s); "
            f"{n_observations} observation(s); "
            f"{n_findings} finding(s); "
            f"{n_evidence} evidence(s); "
            f"{n_errors} error(s)."
        )
