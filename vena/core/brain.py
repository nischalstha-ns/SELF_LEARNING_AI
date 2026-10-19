"""Vena chat brain: provider abstraction, model router, streaming.

Adapted from NEXUS (nexus/providers/{base,mock,openai_compat,factory}.py and
nexus/router/router.py). The provider set is built from VENA_* environment
variables; when no usable provider is configured Vena falls back to the mock
provider so the agent still runs offline instead of crashing.

Env knobs (all optional, safe defaults):
    VENA_PROVIDER          mock | openai | ollama | custom   (default: mock)
    VENA_OFFLINE_ONLY      1 = local providers only           (default: 0)
    VENA_OPENAI_BASE_URL   (default: https://api.openai.com/v1)
    VENA_OPENAI_MODEL      (default: gpt-4o-mini)
    VENA_OPENAI_API_KEY    secret; never logged
    VENA_OLLAMA_BASE_URL   (default: http://127.0.0.1:11434/v1)
    VENA_OLLAMA_MODEL      (default: llama3.1)
    VENA_REQUEST_TIMEOUT_S (default: 60)
    VENA_MAX_RETRIES       (default: 2)
"""
from __future__ import annotations

import abc
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from vena.core.errors import ProviderAuthError, ProviderError, ProviderUnavailable
from vena.core.logging import get_logger, redact
from vena.core.types import Message, ProviderResponse, ToolCall

log = get_logger("core.brain")


# ---------------------------------------------------------------------------
# Provider abstraction
# ---------------------------------------------------------------------------

@dataclass
class HealthStatus:
    reachable: bool
    detail: str = ""
    latency_ms: int = 0


class AIProvider(abc.ABC):
    name: str = "base"
    is_local: bool = False

    @abc.abstractmethod
    def complete(self, messages: list[Message], tools: list[dict] | None = None,
                 timeout_s: float = 60.0, **kwargs) -> ProviderResponse:
        """One chat completion. May raise ProviderError subclasses."""

    def stream_complete(self, messages: list[Message], tools: list[dict] | None = None,
                        timeout_s: float = 60.0, **kwargs):
        """Yield ProviderResponse deltas as they arrive. Providers without
        streaming raise NotImplementedError; callers fall back to complete()."""
        raise NotImplementedError(f"{self.name} does not support streaming")

    @abc.abstractmethod
    def health_check(self, timeout_s: float = 5.0) -> HealthStatus:
        """Lightweight reachability probe. Must never raise."""


# ---------------------------------------------------------------------------
# Mock provider (offline testing / safe default)
# ---------------------------------------------------------------------------

class MockProvider(AIProvider):
    """Deterministic mock: pops scripted responses in order, then repeats
    the last one. Never needs a network or an API key."""

    name = "mock"

    def __init__(self, script: list[ProviderResponse] | None = None,
                 is_local: bool = True):
        self.script = list(script or [])
        self.fallback = ProviderResponse(text="mock reply")
        self.is_local = is_local
        self.calls: list[list[Message]] = []

    def complete(self, messages, tools=None, timeout_s=60.0, **kwargs) -> ProviderResponse:
        self.calls.append(list(messages))
        if self.script:
            return self.script.pop(0)
        return self.fallback

    def health_check(self, timeout_s=5.0) -> HealthStatus:
        return HealthStatus(True, "mock always healthy")

    def script_tool_call(self, name: str, arguments: dict, text: str = "") -> None:
        self.script.append(ProviderResponse(
            text=text, tool_calls=[ToolCall(name=name, arguments=arguments)]))


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (OpenAI, gateways, llama.cpp server)
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider(AIProvider):
    """Stdlib-only HTTP. Parses the common `tool_calls` response shape;
    providers without tool support just return text."""

    name = "openai_compatible"

    def __init__(self, base_url: str, model_id: str, api_key: str | None = None,
                 is_local: bool = False):
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self._api_key = api_key  # never logged; see redact()
        self.is_local = is_local

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def _payload(self, messages, tools, stream: bool, kwargs: dict) -> dict:
        payload: dict = {
            "model": self.model_id,
            "messages": [{"role": m.role.value, "content": m.content}
                         for m in messages],
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if stream:
            payload["stream"] = True
        payload.update(kwargs)
        return payload

    def complete(self, messages, tools=None, timeout_s=60.0, **kwargs) -> ProviderResponse:
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(self._payload(messages, tools, False, kwargs)).encode(),
            headers=self._headers(),
            method="POST",
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ProviderAuthError(
                    f"provider rejected credentials (HTTP {e.code})") from e
            raise ProviderError(
                f"provider HTTP {e.code}: {redact(e.read().decode(errors='replace')[:300])}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ProviderUnavailable(f"provider unreachable: {e}") from e
        latency_ms = int((time.monotonic() - start) * 1000)

        try:
            choice = body["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            raise ProviderError(
                f"unexpected provider response shape: {str(body)[:300]}") from e

        return ProviderResponse(
            text=choice.get("content") or "",
            tool_calls=[self._parse_tool_call(tc)
                        for tc in choice.get("tool_calls") or []],
            model=body.get("model", self.model_id),
            usage={k: int(v) for k, v in (body.get("usage") or {}).items()
                   if isinstance(v, int)},
            latency_ms=latency_ms,
        )

    @staticmethod
    def _parse_tool_call(tc: dict) -> ToolCall:
        try:
            args = json.loads(tc["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_raw": tc["function"].get("arguments")}
        return ToolCall(name=tc["function"]["name"], arguments=args,
                        call_id=tc.get("id", ""))

    def stream_complete(self, messages, tools=None, timeout_s=60.0, **kwargs):
        """Yield ProviderResponse deltas as SSE arrives (OpenAI stream format).

        Text deltas stream in .text. Fragmented tool-call argument JSON is
        reassembled across chunks; the final yield carries the complete
        tool_calls list and usage.
        """
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(self._payload(messages, tools, True, kwargs)).encode(),
            headers=self._headers(),
            method="POST",
        )
        start = time.monotonic()
        try:
            resp = urllib.request.urlopen(req, timeout=timeout_s)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ProviderAuthError(
                    f"provider rejected credentials (HTTP {e.code})") from e
            raise ProviderError(f"provider HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ProviderUnavailable(f"provider unreachable: {e}") from e

        def _events():
            buf = ""
            try:
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    buf += chunk.decode(errors="replace")
                    while "\n\n" in buf:
                        raw, buf = buf.split("\n\n", 1)
                        for line in raw.splitlines():
                            line = line.strip()
                            if line.startswith("data:"):
                                yield line[5:].strip()
            finally:
                resp.close()

        full_text: list[str] = []
        tool_calls: list[ToolCall] = []
        usage: dict = {}
        model = self.model_id
        try:
            for data in _events():
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                model = obj.get("model", model)
                usage = obj.get("usage") or usage
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content") or ""
                if piece:
                    full_text.append(piece)
                    yield ProviderResponse(text=piece, model=model)
                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    while len(tool_calls) <= idx:
                        tool_calls.append(ToolCall(name="", arguments={},
                                                   call_id=tc.get("id", "")))
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        tool_calls[idx].name = fn["name"]
                    # Arguments arrive fragmented; accumulate raw text.
                    frag = tool_calls[idx].arguments.get("_frag", "")
                    tool_calls[idx].arguments["_frag"] = frag + (fn.get("arguments") or "")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ProviderUnavailable(f"stream interrupted: {e}") from e

        for tc in tool_calls:  # finalize fragmented argument JSON
            frag = tc.arguments.pop("_frag", "")
            try:
                tc.arguments = json.loads(frag or "{}")
            except json.JSONDecodeError:
                tc.arguments = {"_raw": frag}
        latency_ms = int((time.monotonic() - start) * 1000)
        yield ProviderResponse(text="".join(full_text), tool_calls=tool_calls,
                               model=model,
                               usage={k: int(v) for k, v in usage.items()
                                      if isinstance(v, int)},
                               latency_ms=latency_ms)

    def health_check(self, timeout_s=5.0) -> HealthStatus:
        start = time.monotonic()
        try:
            req = urllib.request.Request(f"{self.base_url}/models",
                                         headers=self._headers())
            with urllib.request.urlopen(req, timeout=timeout_s):
                pass
            return HealthStatus(True, "ok", int((time.monotonic() - start) * 1000))
        except Exception as e:  # never raise from a health check
            return HealthStatus(False, str(e)[:200])


# ---------------------------------------------------------------------------
# Ollama provider (local) — thin wrapper over the OpenAI-compatible shape
# ---------------------------------------------------------------------------

class OllamaProvider(OpenAICompatibleProvider):
    """Local Ollama. Same wire format as OpenAI-compatible; always local so
    OFFLINE_ONLY mode keeps working without any cloud dependency."""

    name = "ollama"

    def __init__(self, model_id: str = "llama3.1",
                 base_url: str | None = None,
                 api_key: str | None = None):
        super().__init__(
            base_url or os.environ.get("VENA_OLLAMA_BASE_URL",
                                       "http://127.0.0.1:11434/v1"),
            model_id,
            api_key,
            is_local=True,
        )


# ---------------------------------------------------------------------------
# Model router: failover + retries + offline-only filtering
# ---------------------------------------------------------------------------

class ModelRouter:
    """Picks a provider per call.

    - offline_only (or require_local): only local providers are candidates.
    - Providers tried in registration order; ProviderUnavailable/ ProviderError
      fail over to the next candidate with bounded retries + backoff.
    - ProviderAuthError fails fast (retrying a bad key is pointless).
    """

    def __init__(self, providers: list[AIProvider], offline_only: bool = False,
                 timeout_s: float = 60.0, max_retries: int = 2):
        if not providers:
            raise ValueError("router needs at least one provider")
        self.providers = providers
        self.offline_only = offline_only
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    def candidates(self, require_local: bool = False) -> list[AIProvider]:
        local_only = self.offline_only or require_local
        return [p for p in self.providers if (p.is_local or not local_only)]

    def complete(self, messages: list[Message], tools: list[dict] | None = None,
                 require_local: bool = False, **kwargs) -> ProviderResponse:
        cands = self.candidates(require_local)
        if not cands:
            raise ProviderUnavailable(
                "no providers available (offline_only with no local provider?)")
        last: Exception | None = None
        for provider in cands:
            for attempt in range(self.max_retries + 1):
                try:
                    return provider.complete(messages, tools=tools,
                                              timeout_s=self.timeout_s, **kwargs)
                except ProviderAuthError:
                    log.error("auth failed for provider '%s' — not retrying",
                              provider.name)
                    raise
                except (ProviderUnavailable, ProviderError) as e:
                    last = e
                    log.warning("provider '%s' attempt %d failed: %s",
                                provider.name, attempt + 1, e)
                    time.sleep(min(0.25 * (2 ** attempt), 2.0))
        raise ProviderUnavailable(f"all providers failed; last error: {last}")


# ---------------------------------------------------------------------------
# Environment-based provider factory (DB-backed config lives elsewhere)
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(f"VENA_{key}", default)


def providers_from_env() -> tuple[list[AIProvider], bool]:
    """Build the provider set from VENA_* env vars.

    Never crashes for a missing key or an unknown provider name: falls back
    to the mock provider so Vena always boots (offline-safe by design).
    Returns (providers, offline_only).
    """
    offline_only = _env("OFFLINE_ONLY", "0") == "1"
    name = _env("PROVIDER", "mock").lower()
    if name == "mock":
        providers = [MockProvider(is_local=True)]
    elif name in ("openai", "custom"):
        providers = [OpenAICompatibleProvider(
            _env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            _env("OPENAI_MODEL", "gpt-4o-mini"),
            _env("OPENAI_API_KEY") or None,
            is_local=False)]
    elif name == "ollama":
        providers = [OllamaProvider(_env("OLLAMA_MODEL", "llama3.1"))]
    else:
        log.warning("unknown VENA_PROVIDER '%s' — falling back to mock", name)
        providers = [MockProvider(is_local=True)]
    # Local-first ordering: local providers serve offline_only requests.
    providers.sort(key=lambda p: (not p.is_local,))
    log.info("providers from env: %s (offline_only=%s)",
             [p.name for p in providers], offline_only)
    return providers, offline_only


def build_router() -> ModelRouter:
    """One-call router construction from the environment."""
    providers, offline_only = providers_from_env()
    timeout_s = float(_env("REQUEST_TIMEOUT_S", "60") or 60)
    max_retries = int(_env("MAX_RETRIES", "2") or 2)
    return ModelRouter(providers, offline_only=offline_only,
                       timeout_s=timeout_s, max_retries=max_retries)
