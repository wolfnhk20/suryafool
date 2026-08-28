# CONTEXT.md — policy/

> **For AI coding assistants:** Phase 2 deterministic policy gate.
> Read [`AGENTS.md`](../AGENTS.md) before making changes.

---

## Purpose

Every action request passes through `PolicyEngine.validate()` before
execution. The gate is deterministic code — an LLM cannot reason past it
(AGENTS.md Core Design Rule #2: Scope Guardian principle).

---

## Files

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Done | Package marker |
| `policy.py` | ✅ Done | `PolicyEngine`, `Rule` (ABC), `PolicyContext`, four default rules |

---

## Default rules

| Rule | Rejects when |
|---|---|
| `CapabilityExistsRule` | capability key not registered in the catalogue |
| `ProviderSupportsRule` | capability exists but no provider supports the action |
| `RiskDeclarationRule` | `request.risk` does not match the AUTHORITATIVE catalogue `cap.risk` (mismatch is rejected in BOTH directions — downgrade AND upgrade); `ActionRequest.risk` is caller self-disclosure, never trusted for authorization |
| `RiskTierAuthorizedRule` | the authoritative `cap.risk` is not in the run's `AuthorizationScope.allowed_risks` (PASSIVE always OK; any tier above PASSIVE requires explicit `--allow-risk` from the CLI or an explicit `AuthorizationScope` programmatically) |
| `RunNotFailedRule` | run already in FAILED state |

> **Phase 2.6:** Scenario selection no longer grants any authorization.
> The old `RestrictedRequiresScopeRule` + `SensitiveActiveScopeRule` were
> removed — both branched on `request.risk` (caller-declared) and relied on
> the now-removed `engine` scenario→scope coupling. They are replaced by
> a single `RiskTierAuthorizedRule` that consults `cap.risk`.

## Extending

Subclass `Rule` and call `engine.add_rule(...)`. Rules are stateless;
context travels via `PolicyContext` (registry, run status, authorization, extra).

## Public API

```python
from policy.policy import PolicyEngine, PolicyContext
from core.mission import ActionRequest, PolicyDecisionKind

decision = engine.validate(request, ctx)
if decision.kind == PolicyDecisionKind.ALLOW:
    ...execute...
```

## Rules

- Rules never execute actions — they only return reason strings.
- No LLM input anywhere in this module.