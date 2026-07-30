from ai_subtitle_studio.domain.entities import SubtitleLine, VideoJob
from ai_subtitle_studio.io.srt_writer import SRTWriter
from ai_subtitle_studio.translation.base import TranslatedItem, TranslationBatchResult
from ai_subtitle_studio.translation.registry import TranslationProviderRegistry
from ai_subtitle_studio.workers.job_runner import JobRunner

class Provider:
    provider_id = "fake"
    def translate_batch(self, request, progress=None, cancel=None):
        return TranslationBatchResult([TranslatedItem(item.sequence_number, f"vi-{item.source_text}") for item in request.items])

def test_translation_preserves_line_order_timestamps_and_exports(tmp_path):
    registry = TranslationProviderRegistry(); registry.register(Provider())
    lines = [SubtitleLine(1, 0, 1000, "Hello"), SubtitleLine(2, 1000, 2000, "World")]
    runner = JobRunner(translation_registry=registry)
    translated = runner.translate_lines(VideoJob("lecture.mp4"), lines, "fake", "alias")
    assert [line.sequence_number for line in translated] == [1, 2]
    assert [line.start_ms for line in translated] == [0, 1000]
    writer = SRTWriter()
    vi = writer.write_vietnamese(translated, tmp_path / "lecture.vi.srt")
    bi = writer.write_bilingual(translated, tmp_path / "lecture.bilingual.srt")
    assert vi.exists() and bi.exists()