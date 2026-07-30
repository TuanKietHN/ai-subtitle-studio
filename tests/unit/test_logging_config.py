import logging

from ai_subtitle_studio.logging_config import configure_logging


def test_rotating_log_redacts_credentials(tmp_path):
    log_path = configure_logging(tmp_path, max_bytes=256, backup_count=2)
    logger = logging.getLogger("redaction-test")
    logger.warning(
        "Authorization: Bearer top-secret api_key=abc123 token=qwerty sk-1234567890"
    )
    for handler in logging.getLogger().handlers:
        handler.flush()

    text = log_path.read_text(encoding="utf-8")
    assert "top-secret" not in text
    assert "abc123" not in text
    assert "qwerty" not in text
    assert "sk-1234567890" not in text
    assert text.count("[REDACTED]") >= 4


def test_reconfiguration_keeps_only_one_managed_file_handler(tmp_path):
    configure_logging(tmp_path)
    configure_logging(tmp_path)
    managed = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_ai_subtitle_studio_handler", False)
    ]
    assert len(managed) == 1
