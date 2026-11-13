"""Real OpenAI embedding provider implementation (no mock fallback)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Protocol

MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

# Official OpenAI pricing per 1,000,000 tokens (USD)
MODEL_PRICE_PER_1M_TOKENS_USD: dict[str, float] = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
    "text-embedding-ada-002": 0.10,
}


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """OpenAI Embeddings API adapter with token/cost tracking; never falls back to mock vectors."""

    def __init__(self, model_name: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        resolved_model = (model_name or os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small").strip()
        # If .env previously had a local model name but OPENAI_API_KEY is configured, default to text-embedding-3-small
        if resolved_model not in MODEL_DIMENSIONS:
            resolved_model = "text-embedding-3-small"

        resolved_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not resolved_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Set OPENAI_API_KEY in starter/.env before running embeddings. "
                "Refusing to fall back to mock or random vectors."
            )

        self.provider = "OpenAI"
        self.model_name = resolved_model
        self.dimensions = MODEL_DIMENSIONS[resolved_model]
        self.price_per_1m_usd = MODEL_PRICE_PER_1M_TOKENS_USD[resolved_model]
        self._api_key = resolved_key
        self._endpoint = "https://api.openai.com/v1/embeddings"

        # Telemetry counters
        self.total_prompt_tokens = 0
        self.total_api_calls = 0
        self.total_api_time_sec = 0.0

    @property
    def total_cost_usd(self) -> float:
        return round((self.total_prompt_tokens / 1_000_000.0) * self.price_per_1m_usd, 8)

    def _call_openai_batch(self, inputs: list[str]) -> list[list[float]]:
        if not inputs:
            return []
        cleaned = [t.replace("\x00", " ").strip() or " " for t in inputs]
        payload = json.dumps({"model": self.model_name, "input": cleaned}).encode("utf-8")

        last_err: Exception | None = None
        for attempt in range(1, 4):
            t0 = time.perf_counter()
            req = urllib.request.Request(
                self._endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                elapsed = time.perf_counter() - t0
                self.total_api_time_sec += elapsed
                self.total_api_calls += 1
                usage = body.get("usage", {})
                self.total_prompt_tokens += int(usage.get("prompt_tokens", usage.get("total_tokens", 0)))

                data = sorted(body.get("data", []), key=lambda item: item["index"])
                vectors = [item["embedding"] for item in data]
                if len(vectors) != len(inputs):
                    raise RuntimeError(f"Expected {len(inputs)} embeddings from OpenAI, got {len(vectors)}")
                for v in vectors:
                    if len(v) != self.dimensions:
                        raise RuntimeError(f"Dimension mismatch: expected {self.dimensions}, got {len(v)}")
                return vectors
            except urllib.error.HTTPError as http_err:
                err_Text = http_err.read().decode("utf-8", errors="replace")
                last_err = RuntimeError(f"OpenAI HTTP {http_err.code}: {err_Text}")
                if http_err.code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(1.5 * attempt)
                    continue
                raise last_err from http_err
            except Exception as exc:
                last_err = exc
                if attempt < 3:
                    time.sleep(1.5 * attempt)
                    continue
                raise RuntimeError(f"OpenAI embedding request failed: {exc}") from exc

        raise RuntimeError(f"OpenAI embedding failed after retries: {last_err}")

    def embed_documents(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        if not texts:
            return []
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            all_vectors.extend(self._call_openai_batch(batch))
        return all_vectors

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        if not question or not question.strip():
            raise ValueError("Query question must not be empty.")
        return self._call_openai_batch([question.strip()])[0]
