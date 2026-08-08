import sqlite3

from ai_subtitle_studio.maintenance.cleanup_user_data import cleanup_user_data


class Credentials:
    def __init__(self):
        self.deleted = []

    def delete_password(self, alias):
        self.deleted.append(alias)


def _database(path, owned_output):
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE video_jobs (english_srt_path TEXT, vietnamese_srt_path TEXT, bilingual_srt_path TEXT)"
    )
    connection.execute(
        "INSERT INTO video_jobs VALUES (?, NULL, NULL)", (str(owned_output),)
    )
    connection.execute(
        "CREATE TABLE provider_status (credential_alias TEXT)"
    )
    connection.execute("INSERT INTO provider_status VALUES ('translation/custom')")
    connection.commit()
    connection.close()


def test_output_cleanup_only_deletes_database_owned_srt(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    owned = tmp_path / "outputs" / "owned.en.srt"
    unrelated = tmp_path / "outputs" / "source.mp4"
    owned.parent.mkdir()
    owned.write_text("subtitle", encoding="utf-8")
    unrelated.write_text("video", encoding="utf-8")
    _database(data_dir / "ai_subtitle_studio.sqlite3", owned)

    report = cleanup_user_data(data_dir=data_dir, cleanup_owned_outputs=True)

    assert not owned.exists()
    assert unrelated.exists()
    assert report.deleted_outputs == [str(owned)]


def test_private_cleanup_removes_data_and_known_credentials(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "models").mkdir(parents=True)
    (data_dir / "models" / "weight.bin").write_bytes(b"model")
    database = data_dir / "ai_subtitle_studio.sqlite3"
    _database(database, tmp_path / "missing.srt")
    credentials = Credentials()

    report = cleanup_user_data(
        data_dir=data_dir,
        cleanup_private_data=True,
        credential_store=credentials,
        clear_settings=lambda: True,
    )

    assert not data_dir.exists()
    assert "translation/custom" in credentials.deleted
    assert "translation/google_cloud_v3" in credentials.deleted
    assert "translation/deepseek_chat" in credentials.deleted
    assert report.failures == []
