"""Application logging with rotation and best-effort credential redaction."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
from typing import Any

LOG_FILENAME = "ai-subtitle-studio.log"
_HANDLER_MARKER = "_ai_subtitle_studio_handler"
_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


def redact_text(value: str) -> str:
    redacted = value
    for pattern in _PATTERNS:
        if pattern.pattern.startswith(r"\bsk-"):
            redacted = pattern.sub("[REDACTED]", redacted)
        else:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


class CredentialRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.msg)
        if record.args:
            record.args = _redact(record.args)
        return True


def configure_logging(
    log_dir: str | Path,
    *,
    level: int = logging.INFO,
    max_bytes: int = 2 * 1024 * 1024,
    backup_count: int = 3,
    console: bool = False,
) -> Path:
    """Configure one rotating app file handler and return its absolute path."""
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    log_path = (directory / LOG_FILENAME).resolve()
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redaction = CredentialRedactionFilter()
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redaction)
    setattr(file_handler, _HANDLER_MARKER, True)
    root.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(redaction)
        setattr(console_handler, _HANDLER_MARKER, True)
        root.addHandler(console_handler)
    return log_path
