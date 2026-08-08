# AI Subtitle Studio

AI Subtitle Studio là ứng dụng desktop Windows dùng Python + PySide6 để tạo phụ đề tiếng Anh từ video `.mp4` bằng WhisperX, dịch sang tiếng Việt qua Google Cloud Translation API v3 hoặc DeepSeek, chỉnh sửa phụ đề và xuất file `.srt`.

> Phiên bản đang được chuẩn bị từ mã nguồn hiện tại: `v0.1.0-rc.5`. Đây là
> pre-release chưa ký số; chỉ tải executable từ trang GitHub Releases chính
> thức sau khi chủ sở hữu công bố bản phát hành. RC4 có lỗi kích hoạt runtime
> khi cài mới và không nên tiếp tục phân phối.

## Repository và giấy phép

Repository hiện được công khai để người dùng phổ thông có thể tải asset từ
GitHub Release mà không đăng nhập. Dự án hiện **chưa có file `LICENSE`**: mã
nguồn có thể xem được nhưng không được mặc định hiểu là open source hay được tự
do sao chép/phân phối. Chủ sở hữu cần chọn license rõ ràng trước khi mời đóng
góp hoặc quảng bá quyền sử dụng mã nguồn.

Binary chính thức sau này chỉ được tải từ trang GitHub Releases của repository.
Bản stable phải có SHA-256 và chữ ký Authenticode; bản chưa ký chỉ được phát
hành dưới dạng pre-release.

## Yêu cầu chính

- Windows 10/11.
- Python 3.11 khuyến nghị.
- NVIDIA GPU có thể khởi tạo bằng Torch CUDA và driver tương thích CUDA 12.8+
  nếu chạy STT thật bằng WhisperX. GPU khoảng 4 GiB như RTX 2050 dùng profile
  `GPU 4 GiB`, model `small.en`/`small`, `int8_float16` và batch 1; model
  `large-v3` vẫn là mặc định cho GPU mạnh hơn. Profile này đã có kiểm thử tự
  động nhưng vẫn cần acceptance trên RTX 2050/4 GiB thật trước khi được coi là
  đã xác nhận đầy đủ cho mọi máy.
- Bản source cần `ffmpeg` để trích audio; installer chính thức sẽ bundle bản đã
  pin và kiểm checksum.
- Subtitle Edit nếu muốn mở file `.srt` bằng Subtitle Edit.
- API key Google Cloud Translation API v3 hoặc DeepSeek nếu chạy dịch thật.

## Chạy local trên Windows

```powershell
cd C:\Users\Kiet\Documents\Codex\2026-07-08\ai-subtitle-studio

.\scripts\setup-windows.ps1
```

Script này tạo `.venv`, activate môi trường, nâng cấp pip, cài riêng `torch~=2.8.0`, `torchvision~=0.23.0`, `torchaudio~=2.8.0` từ index CUDA 12.8 của PyTorch trước, rồi mới chạy `pip install -e ".[dev]"`.

Không cài trực tiếp `pip install -e .[dev]` cho môi trường GPU mới: pip có thể lấy bản Torch CPU-only/default từ PyPI trước khi CUDA wheel được chọn. Bộ version cũng được ghim vì `whisperx==3.8.6` yêu cầu `torch~=2.8.0`, `torchvision~=0.23.0`, `torchaudio~=2.8.0`; cài bản mới hơn như `2.11.x` có thể gây xung đột dependency dù vẫn có CUDA.

Chạy test:

```powershell
python -m pytest tests/unit tests/contract tests/integration tests/gui
```

Chạy app:

```powershell
ai-subtitle-studio
```

Hoặc chạy trực tiếp từ source tree:

```powershell
$env:PYTHONPATH = "src"
python -m ai_subtitle_studio.app
```

## Chạy bằng Docker

Docker setup hiện phù hợp nhất cho dev/test/headless validation. Chạy GUI PySide6 thật trong Docker trên Windows không phải đường mặc định vì cần display server/X11/VNC và GPU passthrough. Với UI desktop thật, nên chạy local Windows như phần trên.

### Build image

```powershell
docker compose build
```

### Chạy test suite trong container

```powershell
docker compose run --rm test
```

### Kiểm tra app bootstrap trong container

```powershell
docker compose run --rm app
```

Mặc định service `app` dùng `QT_QPA_PLATFORM=offscreen`, nên lệnh này dùng để xác nhận app import/bootstrap được trong container, không mở cửa sổ desktop thật.

### Mở shell dev trong container

```powershell
docker compose run --rm shell
```

Bên trong container:

```bash
pytest tests/unit tests/contract tests/integration tests/gui
python -m ai_subtitle_studio.app
```

## GPU/WhisperX trong Docker

Nếu muốn thử STT thật trong Docker, host cần NVIDIA Container Toolkit hoặc Docker Desktop/WSL2 có GPU passthrough. Dự án có sẵn file override `docker-compose.gpu.yml` để yêu cầu GPU cho service `app`/`test`:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm app
```

Kiểm tra test suite với GPU passthrough:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm test
```

Lưu ý:

- Container không bundle model Whisper. Model sẽ được tải vào volume `model-cache` khi workflow thật cần.
- `ffmpeg` đã được cài trong image.
- Image đã cài sẵn Torch/TorchVision/TorchAudio bản CUDA 12.8 đúng version trước bước `pip install -e ".[dev]"`, nên pip không kéo bản CPU-only từ PyPI.
- Host chỉ cần bật NVIDIA Container Toolkit hoặc Docker Desktop WSL2 GPU support và dùng driver NVIDIA tương thích CUDA 12.8+; không cần cài thêm CUDA/PyTorch trong container.
- Image dev/test lớn hơn đáng kể vì dùng chung wheel Torch CUDA cho mọi service, kể cả service `test` không dùng GPU.

## Docker volumes

`docker-compose.yml` khai báo các volume:

- `model-cache`: cache model Whisper/WhisperX.
- `app-data`: SQLite/local app state.
- `outputs`: file `.srt` và output sinh ra trong container.

## Cấu trúc chính

```text
src/ai_subtitle_studio/
├── app.py
├── config/
├── domain/
├── io/
├── persistence/
├── stt/
├── translation/
├── ui/
└── workers/

tests/
├── contract/
├── gui/
├── integration/
└── unit/
```

## Các ràng buộc quan trọng

- STT chỉ dùng WhisperX.
- VAD được cấu hình tường minh bằng `vad_method="pyannote"` trong `WhisperXEngine`, không expose ra UI/config.
- Version WhisperX được pin trong `pyproject.toml`: `whisperx==3.8.6`, checked `2026-07-30`.
- Bộ Torch tương thích WhisperX 3.8.6 được pin: `torch~=2.8.0`, `torchvision~=0.23.0`, `torchaudio~=2.8.0`; môi trường GPU phải cài từ index CUDA 12.8 như script/Dockerfile.
- Model mặc định là `large-v3`; danh sách model đọc từ `resources/models.json`.
- Chỉ một job STT được vào vùng GPU tại một thời điểm.


## Hàng đợi, hủy job và khôi phục sau khi mở lại

- Khi bấm **Hủy** job đang chạy, app gửi cờ dừng cho worker/STT. Job hiện tại chuyển sang `Đã hủy`; các job còn lại trong hàng đợi tiếp tục chạy tuần tự khi worker thoát khỏi checkpoint hiện tại.
- Khi bấm **Xóa** một job đang chạy, app yêu cầu hủy job đó, dừng queue thread sau job hiện tại, chờ thread kết thúc an toàn rồi mới xóa job khỏi UI/SQLite. Sau đó app tự khởi động lại hàng đợi còn lại nếu vẫn còn job chờ xử lý.
- Khi đóng app trong lúc có job đang chạy, app dừng worker an toàn và đánh dấu job dở là `Cần chạy lại` (`retry_required`). Khi mở lại app, job/kết quả đã có vẫn được giữ lại, nhưng job dở không resume giữa chừng và cũng không tự chạy ngay. Người dùng cần bấm **Bắt đầu xử lý** để chạy lại job đó từ đầu.
- Log recovery sẽ ghi rõ job nào được chuyển từ trạng thái active sang `retry_required` sau shutdown.

## Tiến trình video dài

WhisperX/Pyannote có thể chia audio dài thành nhiều VAD chunk nội bộ. App không tự tạo file chunk audio riêng; wrapper theo dõi các lần `vad_model.merge_chunks()` của WhisperX. Nếu timestamp chunk bị reset về đầu chunk mới, progress sẽ được tính theo:

```text
(thời lượng audio đã xử lý ở các chunk trước + tiến trình chunk hiện tại) / tổng thời lượng audio
```

Với video dài, chi tiết tiến trình trong cột trạng thái có dạng `Nhận dạng đã xử lý / tổng thời lượng` và có thêm ước tính thời gian còn lại khi đã đủ dữ liệu tốc độ xử lý trung bình.

## File tạm, output và dữ liệu an toàn để xóa

Trong một job, app có thể tạo các file sau:

- Audio WAV trích từ video: `<default_output_dir>/_work/<job-id>/<ten-video>.wav`.
- File chunk/trung gian nếu pipeline sau này cần ghi ra đĩa: cùng thư mục `<default_output_dir>/_work/<job-id>/`.
- File `.tmp` khi ghi SRT: nằm cạnh file output trong thời gian rất ngắn rồi được replace bằng file `.srt` cuối cùng.
- Output phụ đề cần giữ: `<default_output_dir>/*.en.srt`, `*.vi.srt`, `*.bilingual.srt`.
- SQLite/job history: `AI_SUBTITLE_DATA_DIR/ai_subtitle_studio.sqlite3`, hoặc
  mặc định `%LOCALAPPDATA%\AI Subtitle Studio\data\ai_subtitle_studio.sqlite3`.
- Model cache: `AI_SUBTITLE_MODEL_CACHE`, hoặc `model_cache_dir` trong Settings,
  hoặc mặc định `%LOCALAPPDATA%\AI Subtitle Studio\models`.
- Log chẩn đoán: `%LOCALAPPDATA%\AI Subtitle Studio\logs`.
- Output mặc định: `%USERPROFILE%\Documents\AI Subtitle Studio\Outputs`.

App tự dọn thư mục work của job sau khi job kết thúc thành công, lỗi, bị hủy hoặc bị dừng để chạy lại. Nếu app bị kill/crash, file trong `_work` có thể còn lại. Có thể dọn thủ công bằng **Cài đặt → Khác → Dọn dẹp file tạm**.

An toàn để xóa khi app không chạy job:

- `<default_output_dir>/_work/` hoặc dùng nút **Dọn dẹp file tạm** trong Settings.

Không nên xóa thủ công khi app đang chạy:

- `model_cache` / thư mục model đã tải, vì có thể làm app phải tải lại model hoặc lỗi khi worker đang dùng model.
- File SQLite `ai_subtitle_studio.sqlite3`, vì đây là hàng đợi, lịch sử job và đường dẫn output đã lưu.
- Thư mục output chứa `.srt` nếu vẫn muốn giữ phụ đề đã xuất.

## Quyền riêng tư

- Video, audio tạm, subtitle, SQLite và model cache nằm trên máy người dùng.
- Chỉ text subtitle được gửi tới provider dịch khi người dùng chủ động dịch.
- API key được lưu qua Windows Credential Manager/keyring và không được lưu
  plaintext trong source, SQLite, QSettings, log hoặc release artifact.
- Không gửi telemetry trong `v0.1.0`.

## Build và phát hành

Kế hoạch, artifact contract và checklist phát hành nằm tại:

- `specs/001-desktop-subtitle-studio/plan.md`
- `specs/001-desktop-subtitle-studio/contracts/release-artifacts.md`
- `specs/001-desktop-subtitle-studio/quickstart.md`
- `docs/RELEASE_EXE.md` — hướng dẫn build EXE, tự push bằng Git và tạo Release
  trên giao diện GitHub, không dùng GitHub CLI.

Luồng mục tiêu là PyInstaller `onedir` + Inno Setup online installer. Runtime
CUDA được chia thành các release asset nhỏ hơn 1.9 GiB; installer tải qua HTTPS,
kiểm SHA-256 rồi mới giải nén. Whisper model không được bundle và sẽ tải ở lần
sử dụng đầu.

## Validation gần nhất

Đã chạy trong môi trường local:

```powershell
python -m compileall src tests
python -m pytest tests/unit tests/contract tests/integration tests/gui
```

Kết quả hiện tại: `133 passed`; `compileall`, `pip check`, kiểm tra repository,
PowerShell syntax, frozen smoke và local release verification đều đạt. Bằng
chứng chi tiết và các cổng external còn mở nằm trong
`specs/001-desktop-subtitle-studio/quickstart.md`.
