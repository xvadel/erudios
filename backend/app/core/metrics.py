from __future__ import annotations

from prometheus_client import Counter, Histogram

# ── LLM Metrics ───────────────────────────────────────────────────────────────
LLM_REQUESTS = Counter(
    "erudios_llm_requests_total",
    "Total number of LLM provider requests made.",
    ["provider", "task_type", "status"]
)

LLM_TOKENS = Counter(
    "erudios_llm_tokens_total",
    "Total tokens consumed by LLM requests.",
    ["provider", "token_type"]  # token_type: input | output | total
)

LLM_LATENCY = Histogram(
    "erudios_llm_request_duration_seconds",
    "Duration of LLM API requests in seconds.",
    ["provider", "task_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

# ── Caching Metrics ──────────────────────────────────────────────────────────
CACHE_OPERATIONS = Counter(
    "erudios_cache_operations_total",
    "Total number of Cache L1 (Redis) operations.",
    ["operation", "result"]  # operation: get | set | delete; result: hit | miss | success | error
)

# ── Qdrant Metrics ────────────────────────────────────────────────────────────
QDRANT_OPERATIONS = Counter(
    "erudios_qdrant_operations_total",
    "Total Qdrant operations executed.",
    ["operation", "status"]  # operation: search | upsert | ensure_collection
)

QDRANT_LATENCY = Histogram(
    "erudios_qdrant_duration_seconds",
    "Duration of vector search operations in seconds.",
    ["operation"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# ── Business / Learning Metrics ──────────────────────────────────────────────
QUIZ_ATTEMPTS = Counter(
    "erudios_quiz_attempts_total",
    "Total number of quiz attempts recorded.",
    ["difficulty"]
)

MASTERY_UPDATES = Counter(
    "erudios_mastery_updates_total",
    "Total number of user mastery updates.",
    ["topic_slug"]
)
