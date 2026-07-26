# CONTEXT.md — core/

> **For AI coding assistants:** This directory contains shared utilities used by all Suryafool agents.
> Read [`AGENTS.md`](../AGENTS.md) before making changes here.

---

## Purpose

`core/` holds cross-cutting infrastructure that every mission agent depends on.

No wireless logic lives here. No agent-specific state lives here.  
This is the foundation layer — keep it lean and stable.

---

## Files

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Done | Python package marker |
| `llm.py` | ✅ Done | LLM factory + rate limiter + OpenRouter/OpenCode Zen wrapper |

---

## `llm.py` — LLM Factory + Rate Limiter

### Usage

```python
from core.llm import llm_call, get_rate_limiter

# Single call with automatic fallback (OpenRouter → OpenCode Zen)
result = llm_call(prompt="...", max_tokens=2000)
if result.success:
    print(result.content)
    print(f"Served by: {result.provider_used}")
else:
    print(f"LLM unavailable: {result.error}")

# Inspect rate limiter
limiter = get_rate_limiter()
print(limiter.current_usage)   # requests in the current 60s window
```

**Every agent must use `llm_call()` for reasoning calls.** Never instantiate a provider directly.

### Rate Limiter

`SlidingWindowRateLimiter` — thread-safe, sliding window (not fixed bucket).

| Config | Default | Env var |
|---|---|---|
| Max requests | 32 | `SURYAFOOL_RATE_LIMIT` |
| Window | 60 seconds | hardcoded |

All agents share a **single module-level limiter instance** — limits are enforced globally across the whole platform, not per-agent.

**Sliding window vs fixed bucket:**

```
Fixed bucket:    [32 requests at :00] → reset → [32 requests at :01] = 64 in 1 second ❌
Sliding window:  at any moment, only 32 requests in the past 60s = always safe ✅
```

### Provider Selection

| Priority | Provider | Endpoint | Model | Env var |
|---|---|---|---|---|
| Primary | OpenRouter | https://openrouter.ai/api/v1 | nvidia/nemotron-3-ultra-550b-a55b:free | `OPENROUTER_API_KEY` |
| Fallback | OpenCode Zen | https://opencode.ai/zen/v1 | opencode/nemotron-3-ultra-free | `OPENCODE_API_KEY` |

**Fallback behavior:** OpenRouter (10s timeout) → OpenCode Zen (10s timeout) → graceful "LLM unavailable" result.

### Public API

```python
llm_call(prompt: str, max_tokens: int = 2000) -> LLMResult
get_rate_limiter() -> SlidingWindowRateLimiter

# Inspect current usage
limiter = get_rate_limiter()
print(limiter.current_usage)   # requests in the current 60s window
print(repr(limiter))           # SlidingWindowRateLimiter(32 req/60s, current=4)
```

### LLMResult

```python
@dataclass
class LLMResult:
    content: str           # response text
    provider_used: str     # "openrouter" | "opencode_zen" | "none"
    success: bool          # True if got a response
    error: Optional[str]   # error message if failed
```

---

## Rules for This Directory

- Do not add agent-specific logic here — that belongs in `agents/<name>/`.
- Do not add wireless hardware logic here — that belongs in `hal/`.
- `core/` must not import from `agents/`, `hal/`, or `scope_guardian/`.
- All new shared utilities need a corresponding section in this `CONTEXT.md`.