"""Thin async client for the local Ollama server (Phase 8).

This is the only GenAI integration in the project, and it is deliberately
narrow:

- It talks to the locally running Ollama server (``HBN_OLLAMA_BASE_URL``,
  default ``http://localhost:11434``) and to nothing else. There is no cloud
  AI provider, no API key and no outbound internet call.
- It performs one non-streaming ``POST /api/chat`` per explanation with a low
  temperature and thinking disabled where the runtime supports ``think``.
- It is a *transport only*: no business logic, no prompt construction and no
  safety decisions live here. The explanation service owns those.
- Every failure mode (connection error, timeout, malformed body, empty or
  oversized text) becomes an :class:`OllamaChatError`. The explanation service
  treats all of them the same way: discard, fall back to deterministic text.

The generated text is never logged here.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

#: Low temperature: the explanation layer must be boring and repeatable.
_EXPLANATION_TEMPERATURE = 0.2


class OllamaChatError(Exception):
    """Any failure of the local model call (transport or response shape)."""


class OllamaConnectionError(OllamaChatError):
    """The local Ollama server is unreachable or did not answer in time."""


class OllamaMalformedResponseError(OllamaChatError):
    """The server answered but the body is not a usable chat completion."""


class OllamaEmptyResponseError(OllamaChatError):
    """The model returned an empty completion."""


class OllamaOutputTooLongError(OllamaChatError):
    """The completion exceeds the configured character ceiling."""


class OllamaChatClient:
    """Performs one bounded, non-streaming chat completion against Ollama.

    ``transport`` is injectable so tests can drive the real HTTP layer with
    :class:`httpx.MockTransport` without a running Ollama server.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_output_chars: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_chars = max_output_chars
        self._transport = transport

    @property
    def chat_url(self) -> str:
        """Absolute URL of the chat completion endpoint."""

        return f"{self._base_url}/api/chat"

    def build_chat_payload(
        self,
        *,
        system: str,
        user: str,
    ) -> dict[str, Any]:
        """Non-streaming ``/api/chat`` body with deterministic sampling.

        ``stream: false`` and a small ``num_predict`` bound the output; candid
        conversational behaviour is neither wanted nor possible here.
        """

        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": _EXPLANATION_TEMPERATURE,
                "num_predict": max(64, min(512, self._max_output_chars // 3)),
            },
        }

    async def generate(self, *, system: str, user: str) -> str:
        """One completion, or a strongly-typed failure. Never logs content."""

        payload = self.build_chat_payload(system=system, user=user)
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as http:
                response = await http.post(self.chat_url, json=payload)
        except httpx.TimeoutException as exc:
            logger.warning("ollama chat timed out after %.0fs", self._timeout_seconds)
            raise OllamaConnectionError("ollama_timeout") from exc
        except httpx.HTTPError as exc:
            logger.warning("ollama chat unreachable: %s", type(exc).__name__)
            raise OllamaConnectionError("ollama_unreachable") from exc

        if response.status_code >= 500:
            # Transient server-side trouble behaves like "no model available".
            logger.warning("ollama chat returned status=%d", response.status_code)
            raise OllamaConnectionError("ollama_status_5xx")
        if response.status_code != 200:
            raise OllamaMalformedResponseError("ollama_status_non_200")

        try:
            body = response.json()
        except ValueError as exc:
            raise OllamaMalformedResponseError("ollama_body_not_json") from exc
        if not isinstance(body, dict):
            raise OllamaMalformedResponseError("ollama_body_not_object")
        message = body.get("message")
        if not isinstance(message, dict):
            raise OllamaMalformedResponseError("ollama_no_message")
        content = message.get("content")
        if not isinstance(content, str):
            raise OllamaMalformedResponseError("ollama_content_not_text")

        text = content.strip()
        if not text:
            raise OllamaEmptyResponseError("ollama_empty_content")
        if len(text) > self._max_output_chars:
            # Oversized completions are discarded, never truncated then
            # treated as authoritative: a truncated sentence could misstate
            # an amount.
            logger.info("ollama output exceeded the configured length bound")
            raise OllamaOutputTooLongError("ollama_output_too_long")
        return text
