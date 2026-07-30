<!--
Sync Impact Report
Version change: 1.0.0 -> 1.0.1
Modified principles:
- II. Mandatory VAD -> Clarified for WhisperX 3.8.6 `vad_method="pyannote"`
Added sections:
- None
Removed sections:
- None
Templates requiring updates:
- ✅ updated: .specify/templates/constitution-template.md
- ✅ updated: .specify/templates/plan-template.md
- ✅ updated: .specify/templates/spec-template.md
- ✅ updated: .specify/templates/tasks-template.md
- ⚠ pending: .specify/templates/commands/*.md not present in this repository
Runtime guidance docs:
- ✅ updated: README.md
- ✅ updated: specs/001-desktop-subtitle-studio/{spec,plan,research,quickstart,tasks}.md
- ✅ updated: specs/001-desktop-subtitle-studio/contracts/stt-engine-contract.md
Follow-up TODOs:
- None
-->
# AI Subtitle Studio Constitution

Dự án này là ứng dụng desktop Windows tạo và dịch phụ đề tự động bằng AI.
Constitution này là nguồn ràng buộc cao nhất cho mọi spec, plan, task và code.

## Core Principles

### I. WhisperX Stable Engine

STT engine MUST dùng WhisperX. Không được thay thế bằng `whisper.cpp`, OpenAI
Whisper gốc, hoặc engine khác trong code lõi. Tại thời điểm build, dự án MUST
dùng phiên bản stable mới nhất của WhisperX từ PyPI; không được dùng bản
pre-release, rc, beta hoặc dev. Version cụ thể MUST được pin trong
`requirements` hoặc `pyproject.toml`, kèm ghi chú ngày kiểm tra theo định dạng
ISO `YYYY-MM-DD`.

Rationale: WhisperX là nền tảng STT đã chọn cho chất lượng, alignment và khả
năng GPU của ứng dụng. Pin version có ngày kiểm tra giúp build lặp lại được mà
vẫn giữ trách nhiệm cập nhật.

### II. Mandatory VAD

Mọi đường transcribe qua WhisperX MUST dùng Pyannote Voice Activity Detection.
Với WhisperX 3.8.6, wrapper MUST truyền `vad_method="pyannote"` khi gọi
`whisperx.load_model()`. Đây là hằng số cứng trong code xử lý STT. Không được
expose tùy chọn bật/tắt hoặc thay đổi VAD trên giao diện người dùng, file config,
tham số CLI, request model, hoặc bất kỳ API công khai nào của ứng dụng. Nếu một
bản WhisperX stable tương lai thay đổi API VAD, constitution và contract MUST
được amend trước khi phát hành với API tương đương mới.

Rationale: VAD là yêu cầu chất lượng và độ ổn định bắt buộc cho phụ đề tự động;
cho phép tắt VAD tạo ra kết quả không nhất quán và khó hỗ trợ.

### III. Config-Driven Whisper Models

Model Whisper mặc định MUST là `large-v3`. Kiến trúc MUST cho phép người dùng
chọn và tải thêm model khác như `medium`, `large-v3-turbo`,
`distil-large-v3`, hoặc model hợp lệ mới mà không cần sửa code. Danh sách model
MUST được đọc từ file config, ví dụ `models.json`; logic UI và logic STT không
được hard-code danh sách model.

Rationale: Model availability thay đổi theo thời gian. Config-driven model list
giữ UI mở rộng được mà không phát hành lại ứng dụng cho mỗi model mới.

### IV. Runtime System Information

Ứng dụng MUST có màn hình hoặc khu vực "Thông tin hệ thống" hiển thị tối thiểu:
phiên bản WhisperX đang cài đặt thực tế, phiên bản `faster-whisper`, phiên bản
CUDA và driver GPU phát hiện được trên máy, model đang được chọn, và phiên bản
ứng dụng. Version package MUST lấy tại runtime từ package đã cài, ví dụ qua
`importlib.metadata.version()`. Không được hard-code chuỗi version WhisperX hoặc
`faster-whisper` trong code.

Rationale: Người dùng cần thông tin runtime thật để debug lỗi GPU, dependency và
model. Hard-code version làm sai lệch chẩn đoán.

### V. Pluggable STT and Translation Interfaces

Code MUST tách rõ interface cho STT engine và Translation provider bằng abstract
base class hoặc `Protocol`. Code lõi, UI và pipeline xử lý MUST phụ thuộc vào
interface thay vì phụ thuộc trực tiếp vào implementation cụ thể. Thêm STT engine
hoặc translation provider mới MUST không yêu cầu sửa code lõi ngoài điểm đăng ký
hoặc cấu hình provider.

Rationale: STT và dịch là các điểm biến động cao. Interface rõ ràng giảm rủi ro
khi thay provider, test bằng mock, hoặc thêm backend mới.

### VI. Non-Blocking Desktop Processing

UI thread MUST không bị block bởi audio/video dài hoặc API dịch. Mọi tác vụ nặng
như trích audio, transcribe, alignment, và gọi API dịch MUST chạy trong worker,
thread, process, hoặc queue riêng phù hợp với framework desktop đang dùng. UI
MUST nhận tiến độ, lỗi, hủy job và kết quả qua cơ chế message/event an toàn giữa
worker và UI.

Rationale: Ứng dụng desktop phải phản hồi trong suốt quá trình xử lý dài; block
UI thread làm mất khả năng hủy, quan sát tiến độ và phục hồi lỗi.

### VII. Single GPU STT Job

Ứng dụng MUST chỉ xử lý một video tại một thời điểm trên GPU cho tác vụ STT.
Không được chạy song song nhiều job STT trên GPU. Pipeline MUST có khóa, semaphore
hoặc hàng đợi toàn cục để serialize các job STT GPU và tránh tràn VRAM. Các tác
vụ không dùng GPU có thể chạy song song nếu không vi phạm nguyên tắc non-blocking
và không tranh chấp tài nguyên STT.

Rationale: WhisperX và model lớn có nhu cầu VRAM cao. Serialize job STT GPU là
biện pháp bắt buộc để tránh crash, out-of-memory và mất tiến độ xử lý.

## Technical Constraints

- Target platform MUST là desktop Windows.
- Build metadata MUST ghi rõ ngày kiểm tra phiên bản WhisperX stable từ PyPI khi
  pin dependency.
- WhisperX wrapper MUST là điểm duy nhất chọn VAD implementation để bảo đảm
  `vad_method="pyannote"` không bị bypass.
- Model configuration file MUST được validate khi khởi động: có `large-v3` làm
  default hợp lệ và không chứa model trùng id.
- System Info MUST đọc version package tại runtime và MUST hiển thị trạng thái
  không phát hiện được CUDA/GPU bằng thông báo rõ ràng thay vì giá trị giả.

## Development Workflow and Quality Gates

- Mỗi feature spec MUST ghi rõ có chạm đến STT, translation, model selection,
  System Info, worker processing hoặc GPU scheduling hay không.
- Mỗi implementation plan MUST có Constitution Check chứng minh tuân thủ 7 nguyên
  tắc trong tài liệu này trước khi thiết kế chi tiết.
- Tasks cho feature chạm STT MUST bao gồm test hoặc kiểm tra code cho
  `vad_method="pyannote"`, không có public VAD field/toggle, pin WhisperX
  stable, model config và khóa một job GPU.
- Tasks cho feature chạm UI hoặc pipeline dài MUST bao gồm kiểm tra UI không bị
  block khi xử lý audio/video dài.
- Review MUST từ chối thay đổi hard-code version runtime, hard-code model list
  trong UI logic, expose toggle VAD, hoặc chạy song song nhiều job STT GPU.

## Governance

Constitution này supersedes mọi hướng dẫn mâu thuẫn trong spec, plan, tasks,
README, docs và code comments. Mọi amendment MUST được thực hiện bằng thay đổi
riêng trong `.specify/memory/constitution.md`, kèm Sync Impact Report cập nhật
template và tài liệu phụ thuộc.

Versioning policy:
- MAJOR: loại bỏ hoặc định nghĩa lại nguyên tắc bắt buộc theo hướng không tương
  thích với specs/tasks hiện có.
- MINOR: thêm nguyên tắc mới, thêm section mới, hoặc mở rộng materially guidance.
- PATCH: sửa câu chữ, làm rõ, hoặc chỉnh lỗi không đổi nghĩa.

Compliance review:
- `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze` và review code MUST xem
  Constitution Check là gate bắt buộc.
- Bất kỳ vi phạm MUST được sửa trong spec/plan/tasks/code; không được hạ thấp
  hoặc diễn giải lại nguyên tắc trong feature work.
- Nếu một nguyên tắc không còn phù hợp, phải amend constitution trước, sau đó mới
  cập nhật artifacts phụ thuộc.

**Version**: 1.0.1 | **Ratified**: 2026-07-08 | **Last Amended**: 2026-07-30
