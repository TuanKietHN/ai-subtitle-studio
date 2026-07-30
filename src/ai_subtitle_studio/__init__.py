"""AI Subtitle Studio package metadata."""

from __future__ import annotations

import importlib.metadata

APP_NAME = "AI Subtitle Studio"
PACKAGE_NAME = "ai-subtitle-studio"
UNKNOWN_VERSION = "0+unknown"
DEFAULT_MODEL_ID = "large-v3"


def get_app_version() -> str:
    """Return the installed distribution version without duplicating it in code."""
    try:
        return importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return UNKNOWN_VERSION


APP_VERSION = get_app_version()
