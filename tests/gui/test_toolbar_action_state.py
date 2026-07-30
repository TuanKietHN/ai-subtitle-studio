import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QItemSelectionModel, QThread

from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.domain.entities import VideoJob
from ai_subtitle_studio.domain.job_state import ACTIVE_STATUSES, JobStatus
from ai_subtitle_studio.ui.main_window import MainWindow, MainWindowController
from ai_subtitle_studio.workers.job_runner import JobRunner


BUTTONS = {
    "start": "start_button",
    "pause": "pause_button",
    "resume": "resume_button",
    "cancel": "cancel_button",
    "retry": "retry_button",
    "remove": "remove_button",
}


def _window(qtbot, statuses, running_index=None):
    runner = JobRunner()
    controller = MainWindowController(
        ModelCatalog.load("resources/models.json"),
        job_runner=runner,
    )
    jobs = [VideoJob(f"video-{index}.mp4", status=status) for index, status in enumerate(statuses)]
    controller.queue_service.jobs = jobs
    if running_index is not None:
        runner.current_job_id = jobs[running_index].id
    window = MainWindow(controller)
    qtbot.addWidget(window)
    return window, jobs


def _assert_buttons(window, **expected):
    window._update_action_state()
    actual = {name: getattr(window, attribute).isEnabled() for name, attribute in BUTTONS.items()}
    assert actual == expected


SINGLE_SELECTION_MATRIX = {
    JobStatus.QUEUED: dict(start=True, pause=True, resume=False, cancel=False, retry=False, remove=True),
    JobStatus.PAUSED: dict(start=False, pause=False, resume=True, cancel=False, retry=False, remove=True),
    JobStatus.WAITING_FOR_MODEL: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.DOWNLOADING_MODEL: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.EXTRACTING_AUDIO: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.WAITING_FOR_GPU: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.TRANSCRIBING: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.ALIGNING: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.TRANSLATING: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.READY_FOR_EDIT: dict(start=False, pause=False, resume=False, cancel=False, retry=False, remove=True),
    JobStatus.EXPORTING: dict(start=False, pause=True, resume=False, cancel=True, retry=False, remove=True),
    JobStatus.COMPLETED: dict(start=False, pause=False, resume=False, cancel=False, retry=False, remove=True),
    JobStatus.FAILED: dict(start=False, pause=False, resume=False, cancel=False, retry=True, remove=True),
    JobStatus.CANCELED: dict(start=False, pause=False, resume=False, cancel=False, retry=True, remove=True),
    JobStatus.RETRY_REQUIRED: dict(start=True, pause=False, resume=False, cancel=False, retry=False, remove=True),
}


@pytest.mark.parametrize("status", list(JobStatus))
def test_single_selection_matches_toolbar_matrix(qtbot, status):
    running_index = 0 if status in ACTIVE_STATUSES else None
    window, _jobs = _window(qtbot, [status], running_index=running_index)

    _assert_buttons(window, **SINGLE_SELECTION_MATRIX[status])


def test_paused_current_worker_can_resume_or_cancel(qtbot):
    window, _jobs = _window(qtbot, [JobStatus.PAUSED], running_index=0)

    _assert_buttons(
        window,
        start=False,
        pause=False,
        resume=True,
        cancel=True,
        retry=False,
        remove=True,
    )


def test_no_selection_keeps_only_global_start_available(qtbot):
    window, _jobs = _window(qtbot, [JobStatus.QUEUED])
    window.queue_table.clearSelection()

    _assert_buttons(
        window,
        start=True,
        pause=False,
        resume=False,
        cancel=False,
        retry=False,
        remove=False,
    )


@pytest.mark.parametrize(
    ("statuses", "running_index", "start_enabled"),
    [
        ([JobStatus.QUEUED, JobStatus.FAILED], None, True),
        ([JobStatus.TRANSCRIBING, JobStatus.FAILED], 0, False),
        ([JobStatus.FAILED, JobStatus.CANCELED], None, False),
    ],
)
def test_multiple_selection_disables_all_single_job_commands(
    qtbot,
    statuses,
    running_index,
    start_enabled,
):
    window, _jobs = _window(qtbot, statuses, running_index=running_index)
    selection_model = window.queue_table.selectionModel()
    window.queue_table.clearSelection()
    for row in range(len(statuses)):
        selection_model.select(
            window.queue_table.model().index(row, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )

    thread = None
    if running_index is not None:
        thread = QThread(window)
        window._queue_thread = thread
    try:
        _assert_buttons(
            window,
            start=start_enabled,
            pause=False,
            resume=False,
            cancel=False,
            retry=False,
            remove=True,
        )
    finally:
        window._queue_thread = None
        if thread is not None:
            thread.deleteLater()


def test_pause_tooltip_describes_safe_checkpoint_behavior(qtbot):
    window, _jobs = _window(qtbot, [JobStatus.TRANSCRIBING], running_index=0)

    assert "điểm kiểm tra an toàn" in window.pause_button.toolTip()
    assert "GPU" in window.pause_button.toolTip()
