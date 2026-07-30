from uuid import uuid4

import pytest

from ai_subtitle_studio.io.working_files import WorkingFileManager


def test_job_directory_accepts_generated_uuid(tmp_path):
    manager = WorkingFileManager(tmp_path / "_work")
    job_id = str(uuid4())

    assert manager.job_dir(job_id) == tmp_path / "_work" / job_id


@pytest.mark.parametrize("job_id", ("..", "../outside", r"..\outside", "job-1", ""))
def test_job_directory_rejects_non_uuid_and_traversal(job_id, tmp_path):
    manager = WorkingFileManager(tmp_path / "_work")

    with pytest.raises(ValueError, match="UUID"):
        manager.job_dir(job_id)
