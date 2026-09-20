"""Generic JSON / text structured logging."""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)
_llm_provider: ContextVar[str | None] = ContextVar("llm_provider", default=None)

_CONFIGURED = False
_LOGGER_NAME = "travel_assistant"


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def bind_context(
    *,
    correlation_id: str | None = None,
    session_id: str | None = None,
    llm_provider: str | None = None,
) -> None:
    if correlation_id is not None:
        _correlation_id.set(correlation_id)
    if session_id is not None:
        _session_id.set(session_id)
    if llm_provider is not None:
        _llm_provider.set(llm_provider)


def clear_context() -> None:
    _correlation_id.set(None)
    _session_id.set(None)
    _llm_provider.set(None)


def _truncate(text: str | None, *, limit: int = 120) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in (
            "event",
            "correlation_id",
            "session_id",
            "llm_provider",
            "agent",
            "intent",
            "latency_ms",
            "status",
            "query_preview",
            "hit_count",
            "chunk_count",
            "entity_count",
            "relation_count",
            "store",
            "error",
        ):
            if hasattr(record, key):
                val = getattr(record, key)
                if val is not None:
                    payload[key] = val
        return json.dumps(payload, ensure_ascii=False)


def _ensure_configured() -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)
    if _CONFIGURED:
        return logger

    level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    fmt_mode = (os.getenv("LOG_FORMAT") or "json").strip().lower()
    handler: logging.Handler = logging.StreamHandler(sys.stderr)
    if fmt_mode == "text":
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(event)s] %(message)s")
        )
    else:
        handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    log_file = os.getenv("LOG_FILE")
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(JsonFormatter())
        logger.addHandler(fh)

    _CONFIGURED = True
    return logger


def get_logger() -> logging.Logger:
    return _ensure_configured()


def log_event(
    event: str,
    message: str = "",
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    logger = _ensure_configured()
    extra = {
        "event": event,
        "correlation_id": fields.pop("correlation_id", None) or _correlation_id.get(),
        "session_id": fields.pop("session_id", None) or _session_id.get(),
        "llm_provider": fields.pop("llm_provider", None) or _llm_provider.get(),
    }
    # Truncate user text at INFO
    if "query_preview" in fields and level <= logging.INFO:
        fields["query_preview"] = _truncate(str(fields["query_preview"]))
    if "user_text" in fields and level <= logging.INFO:
        fields["user_text"] = _truncate(str(fields["user_text"]))
    extra.update(fields)
    # Ensure formatter defaults for text mode
    if not hasattr(logging.LogRecord, "event"):
        pass
    record_kwargs = {k: v for k, v in extra.items()}
    logger.log(level, message or event, extra=record_kwargs)
