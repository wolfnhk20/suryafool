"""
core/llm.py

LLM factory with OpenRouter (primary) + OpenCode Zen (fallback) for Nemotron 3 Ultra.

Providers:
- Primary: OpenRouter (nvidia/nemotron-3-ultra-550b-a55b:free)
- Fallback: OpenCode Zen (opencode/nemotron-3-ultra-free)

Both are OpenAI-compatible endpoints.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

# Load .env so API keys are available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


# ── Rate Limiter (same as before) ──────────────────────────────────────────────

class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self, max_requests: int = 32, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.max_requests:
                    self._timestamps.append(now)
                    return
                wait = self.window_seconds - (now - self._timestamps[0])
            time.sleep(max(0.0, wait) + 0.05)

    @property
    def current_usage(self) -> int:
        with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
                self._timestamps.popleft()
            return len(self._timestamps)

    def __repr__(self) -> str:
        return f"SlidingWindowRateLimiter({self.max_requests} req/{self.window_seconds}s, current={self.current_usage})"


def _build_default_limiter() -> SlidingWindowRateLimiter:
    max_req = int(os.environ.get("SURYAFOOL_RATE_LIMIT", "32"))
    return SlidingWindowRateLimiter(max_requests=max_req, window_seconds=60.0)


_default_limiter: SlidingWindowRateLimiter = _build_default_limiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _default_limiter


# ── Provider Configuration ─────────────────────────────────────────────────────

@dataclass
class ProviderConfig:
    name: str
    base_url: str
    model: str
    api_key_env: str
    timeout: int


PROVIDERS: dict[str, ProviderConfig] = {
    "openrouter": ProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model="nvidia/nemotron-3-ultra-550b-a55b:free",
        api_key_env="OPENROUTER_API_KEY",
        timeout=10,
    ),
    "opencode_zen": ProviderConfig(
        name="opencode_zen",
        base_url="https://opencode.ai/zen/v1",
        model="opencode/nemotron-3-ultra-free",
        api_key_env="OPENCODE_API_KEY",
        timeout=10,
    ),
}

PRIMARY_PROVIDER = "openrouter"
FALLBACK_PROVIDER = "opencode_zen"


# ── LLM Result Types ───────────────────────────────────────────────────────────

@dataclass
class LLMResult:
    """Result of an LLM call."""
    content: str
    provider_used: str
    success: bool
    error: Optional[str] = None


# ── Rate-limited LLM wrapper ───────────────────────────────────────────────────

class _RateLimitedLLM:
    """Wrapper around a LangChain chat model with rate limiting."""

    def __init__(self, inner, limiter: SlidingWindowRateLimiter, provider_name: str) -> None:
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_limiter", limiter)
        object.__setattr__(self, "_provider_name", provider_name)

    def invoke(self, input, config=None, **kwargs):
        self._limiter.acquire()
        return self._inner.invoke(input, config=config, **kwargs)

    async def ainvoke(self, input, config=None, **kwargs):
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._limiter.acquire)
        return await self._inner.ainvoke(input, config=config, **kwargs)

    def stream(self, input, config=None, **kwargs):
        self._limiter.acquire()
        return self._inner.stream(input, config=config, **kwargs)

    async def astream(self, input, config=None, **kwargs):
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._limiter.acquire)
        async for chunk in self._inner.astream(input, config=config, **kwargs):
            yield chunk

    def batch(self, inputs, config=None, **kwargs):
        for _ in inputs:
            self._limiter.acquire()
        return self._inner.batch(inputs, config=config, **kwargs)

    def bind_tools(self, *args, **kwargs):
        return _RateLimitedLLM(self._inner.bind_tools(*args, **kwargs), self._limiter, self._provider_name)

    def with_structured_output(self, *args, **kwargs):
        return _RateLimitedLLM(
            self._inner.with_structured_output(*args, **kwargs), self._limiter, self._provider_name
        )

    def bind(self, **kwargs):
        return _RateLimitedLLM(self._inner.bind(**kwargs), self._limiter, self._provider_name)

    def __getattr__(self, name: str):
        return getattr(object.__getattribute__(self, "_inner"), name)

    def __repr__(self) -> str:
        inner = object.__getattribute__(self, "_inner")
        limiter = object.__getattribute__(self, "_limiter")
        return f"RateLimited({inner!r}, {limiter!r}, provider={self._provider_name})"


# ── Internal: Build raw provider client ────────────────────────────────────────

def _build_openai_compatible(provider_key: str, timeout: int) -> Optional["BaseChatModel"]:
    """Build an OpenAI-compatible client for the given provider."""
    config = PROVIDERS.get(provider_key)
    if not config:
        return None

    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        return None

    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            api_key=api_key,
            base_url=config.base_url,
            timeout=timeout,
            max_retries=0,  # we handle retries at the wrapper level
        )
    except ImportError:
        return None


# ── Public API ──────────────────────────────────────────────────────────────────

def get_llm(
    provider: Optional[str] = None,
    rate_limiter: Optional[SlidingWindowRateLimiter] = None,
    timeout: Optional[int] = None,
) -> Optional[_RateLimitedLLM]:
    """
    Get a rate-limited LLM for the specified provider.
    
    Args:
        provider: 'openrouter' or 'opencode_zen'. If None, uses PRIMARY_PROVIDER.
        rate_limiter: Optional custom rate limiter.
        timeout: Override timeout in seconds.
    
    Returns:
        Rate-limited LLM wrapper, or None if provider not configured.
    """
    if provider is None:
        provider = PRIMARY_PROVIDER
    
    config = PROVIDERS.get(provider)
    if not config:
        return None
    
    if rate_limiter is None:
        rate_limiter = _default_limiter
    
    if timeout is None:
        timeout = config.timeout
    
    inner = _build_openai_compatible(provider, timeout)
    if inner is None:
        return None
    
    return _RateLimitedLLM(inner, rate_limiter, provider)


def llm_call(prompt: str, max_tokens: int = 2000) -> LLMResult:
    """
    Call LLM with automatic fallback from OpenRouter → OpenCode Zen.
    
    This is the main wrapper for agent reasoning calls.
    
    Args:
        prompt: The prompt to send to the LLM.
        max_tokens: Maximum tokens in response.
    
    Returns:
        LLMResult with content, provider_used, success, and error info.
    """
    from langchain_core.messages import HumanMessage
    
    # Try primary provider
    primary_llm = get_llm(PRIMARY_PROVIDER)
    if primary_llm is not None:
        try:
            response = primary_llm.invoke([HumanMessage(content=prompt)])
            return LLMResult(
                content=str(response.content).strip(),
                provider_used=PRIMARY_PROVIDER,
                success=True,
            )
        except Exception as e:
            err_str = str(e).lower()
            is_transient = any(k in err_str for k in (
                "timeout", "timed out", "connection", "refused", "read timed",
                "502", "503", "504", "rate limit", "429"
            ))
            if not is_transient:
                # Non-transient error (e.g., auth failure) - don't fallback
                return LLMResult(
                    content="",
                    provider_used=PRIMARY_PROVIDER,
                    success=False,
                    error=f"Primary provider error: {e}",
                )
            # Transient error - will try fallback
    
    # Try fallback provider
    fallback_llm = get_llm(FALLBACK_PROVIDER)
    if fallback_llm is not None:
        try:
            response = fallback_llm.invoke([HumanMessage(content=prompt)])
            return LLMResult(
                content=str(response.content).strip(),
                provider_used=FALLBACK_PROVIDER,
                success=True,
            )
        except Exception as e:
            return LLMResult(
                content="",
                provider_used=FALLBACK_PROVIDER,
                success=False,
                error=f"Fallback provider error: {e}",
            )
    
    # Both failed or unavailable
    return LLMResult(
        content="",
        provider_used="none",
        success=False,
        error="Both OpenRouter and OpenCode Zen unavailable or misconfigured",
    )


# ── Module-level shared limiter ────────────────────────────────────────────────

def _build_default_limiter() -> SlidingWindowRateLimiter:
    max_req = int(os.environ.get("SURYAFOOL_RATE_LIMIT", "32"))
    return SlidingWindowRateLimiter(max_requests=max_req, window_seconds=60.0)


_default_limiter: SlidingWindowRateLimiter = _build_default_limiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _default_limiter