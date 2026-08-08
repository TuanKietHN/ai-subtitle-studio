# Implementation Plan: Desktop Subtitle Studio Release Readiness

**Branch**: `001-desktop-subtitle-studio` | **Updated**: 2026-08-08 | **Spec**: [spec.md](./spec.md) | **Next candidate**: `v0.1.0-rc.5` | **Stable target**: `v0.1.0`

**Input**: Hoàn thiện ứng dụng hiện có, sửa lỗi kích hoạt runtime của RC4, tối ưu installer online/resume/uninstall, hỗ trợ cấu hình GPU NVIDIA 4 GiB như RTX 2050, và phát hành lại bằng RC mới qua GitHub Releases.

## Summary

Hoàn thiện AI Subtitle Studio từ trạng thái source/test chạy được thành sản phẩm Windows có thể cài đặt và phát hành lặp lại. Kế hoạch giữ nguyên Python + PySide6 + WhisperX + Torch CUDA, sửa các blocker của môi trường frozen, chuẩn hóa nơi lưu dữ liệu người dùng, bundle `ffmpeg`, bổ sung logging/chẩn đoán, hoàn thiện PyInstaller `onedir`, tạo Inno Setup online installer, thiết lập Git/GitHub/CI/CD, kiểm thử trên máy Windows sạch và phát hành các asset có checksum.

Do Torch CUDA tạo runtime nhiều gigabyte trong khi mỗi GitHub Release asset phải nhỏ hơn 2 GiB, artifact chính cho người dùng là một online installer nhỏ. Installer tải các archive runtime được chia dưới 1.9 GiB, kiểm SHA-256, giải nén vào thư mục cài đặt theo user, tạo shortcut và hỗ trợ uninstall/upgrade. Whisper model không nằm trong installer; app tải model ở lần sử dụng đầu.

RC4 đã chứng minh build/release asset hoạt động nhưng bộc lộ lỗi cài mới: `CurStepChanged(ssInstall)` chạy trước khi Inno Setup tạo `{app}`, trong khi mã đổi tên staging sang `{app}\runtime` mà chưa gọi `ForceDirectories({app})`. RC5 phải sửa lỗi này, chuyển staging sang cùng volume với thư mục cài, giữ archive đã tải để retry, hiển thị tiến độ thật, hỗ trợ local/cache/resume, và tách rõ cài mới với nâng cấp.

Ứng dụng hiện không khóa tên GPU cụ thể nhưng khóa `cuda + float16`, không đọc VRAM và model nhẹ nhất vẫn khuyến nghị 5 GiB. RC5 bổ sung profile 4 GiB theo cấu hình, model tiếng Anh nhỏ, `int8_float16`, batch nhỏ, giải phóng model giữa ASR/alignment và kiểm thử thật trên RTX 2050 hoặc GPU NVIDIA 4 GiB tương đương. `large-v3` vẫn là default theo constitution; máy 4 GiB được cảnh báo và có hành động một lần để chọn profile tương thích thay vì âm thầm đổi model.

## RC4 Baseline Used for RC5 Planning

- Repository đã được khởi tạo trên `main`, có `origin/main`, workflow CI/security/release và tag `v0.1.0-rc.4`.
- Protected self-hosted Windows runner đã build RC4: installer khoảng 2.8 MiB, hai runtime volumes khoảng 1.8 GiB và 526 MiB, manifest, checksum, SBOM và notices.
- RC4 setup log ngày 2026-08-01 xác nhận cả hai volume tải và verify SHA-256 thành công, giải nén thành công, rồi lỗi ở bước `RenameFile(StagedRuntime, ActiveRuntime)` vì `{app}` chưa tồn tại. Rollback xóa temporary download nên người dùng phải tải lại toàn bộ.
- Installer hiện staging tại `{tmp}\runtime-staging`, tải từng volume tuần tự bằng `DownloadTemporaryFile`, chỉ đổi `StatusLabel`, không có tổng progress bar, persistent cache, `.part` resume, local-file reuse hoặc runtime identity để bỏ qua download khi nâng cấp.
- Inno Setup hiện tạo Add/Remove Programs entry và uninstaller mặc định, nhưng Start Menu chưa có shortcut uninstall. `[UninstallDelete]` chỉ xóa binary runtime; model, log, SQLite, QSettings, Credential Manager và output được giữ lại nhưng chưa có lựa chọn full cleanup.
- App phát hiện NVIDIA qua Torch và `nvidia-smi` nhưng fallback `nvidia-smi` có thể báo khả dụng khi Torch CUDA không khởi tạo được. System Info chưa đọc `memory.total`/compute capability và Settings chưa populate danh sách GPU thực tế.
- `TranscriptionRequest` mặc định `compute_type="float16"`; `model.transcribe()` chưa nhận `batch_size`. ASR model còn sống khi alignment model được load, làm tăng peak VRAM.
- Catalog chỉ có `medium` (5 GiB), `distil-large-v3` (6 GiB), `large-v3-turbo` (8 GiB) và default `large-v3` (10 GiB); chưa có profile được hỗ trợ cho GPU 4 GiB.
- Automated/source/frozen validation và NVIDIA acceptance trên RTX 5060 8 GiB đã có bằng chứng trước RC4; clean install/upgrade/uninstall và NVIDIA 4 GiB vẫn chưa có bằng chứng release gate.

## RC5 Implementation Status

**Checked**: 2026-08-08

- R3A-R3D source, contract tests and release tooling are implemented through
  T163-T174. The automated suite passes 158 tests.
- A local validation build produced the RC5 Setup, two runtime volumes,
  manifest, checksums, SBOM and notices; frozen smoke and local release
  verification passed.
- The local validation manifest intentionally records
  `git_commit=uncommitted`. Those assets are not publishable and MUST be rebuilt
  after the source is committed and tag `v0.1.0-rc.5` points to that commit.
- The current validation GPU is an RTX 5060 with 8,151 MiB VRAM, not a 4 GiB
  acceptance device. Windows Sandbox is unavailable on this builder.
- Google/DeepSeek test credentials are not present in the application keyring.
  The RC5 installer is `NotSigned` as expected for a prerelease validation
  build.
- Therefore R5 clean-Windows, real 4 GiB, real-provider, SmartScreen/signing and
  GitHub Settings/tag/draft-publication gates remain open. Source completion
  MUST NOT be used as evidence that these external gates passed.

## Technical Context

**Language/Version**: Python 3.13.7 là interpreter đã được pin và dùng để tạo release artifact hiện tại. Python 3.11 và 3.13 được dùng trong test matrix nhẹ vì metadata WhisperX hỗ trợ `>=3.10,<3.14`. Không trộn package global với release venv.

**Primary Dependencies**: PySide6, `whisperx==3.8.6`, `torch~=2.8.0`, `torchvision~=0.23.0`, `torchaudio~=2.8.0`, httpx, keyring, PyInstaller 6.x, Inno Setup 6.x, ffmpeg, pytest và pytest-qt.

**Dependency Reproducibility**:

- `pyproject.toml` tiếp tục là source dependency cấp cao.
- Tạo release lock cho Python 3.13.7/Windows x64, pin chính xác package build/runtime và lưu hash khi công cụ hỗ trợ.
- Cài Torch/TorchVision/TorchAudio từ index CUDA 12.8 trước, sau đó cài phần còn lại.
- Release workflow xác nhận `pip check`, version runtime và dependency manifest trước khi build.
- Không build release từ Python/package global của máy phát triển.

**Storage**:

- QSettings: tùy chọn không bí mật.
- Windows Credential Manager/keyring: API key.
- `%LOCALAPPDATA%\AI Subtitle Studio\ai_subtitle_studio.sqlite3`: SQLite và state hiện tại; migration phải giữ tương thích với đường dẫn đã phát hành.
- `%LOCALAPPDATA%\AI Subtitle Studio\models`: model cache mặc định.
- `%LOCALAPPDATA%\AI Subtitle Studio\logs`: rolling logs và crash diagnostics.
- `%USERPROFILE%\Documents\AI Subtitle Studio\Outputs`: output mặc định.
- Environment overrides hiện có được giữ cho test, Docker và hỗ trợ kỹ thuật.

**Packaging**:

- PyInstaller `onedir`, `console=False`, `upx=False`.
- Không bundle Whisper model.
- Bundle `models.json`, icon, version metadata, licenses/notices và `ffmpeg.exe`.
- Custom PyInstaller hooks/runtime hook thu thập WhisperX và dependency import động, package metadata, Qt plugins và native DLL cần thiết.
- Loại test, cache, model weights, import library `.lib`, module Qt không dùng và tài liệu phát triển khỏi runtime.
- Runtime `onedir` được đóng thành archive nhiều volume, mỗi volume mục tiêu tối đa 1.8 GiB và bắt buộc dưới 1.9 GiB.

**Installer**:

- Inno Setup online installer x64, per-user, `PrivilegesRequired=lowest`.
- Cài dưới `%LOCALAPPDATA%\Programs\AI Subtitle Studio`.
- Tạo `{app}` trước mọi rename; staging tại `{app}\runtime.staging` để staging, active và previous luôn cùng volume.
- Nguồn runtime theo thứ tự: file cạnh Setup (`{src}`) -> verified persistent cache -> resumable BITS transfer -> Inno HTTPS fallback; mọi nguồn đều phải qua SHA-256 trước extraction.
- Persistent cache mặc định `%LOCALAPPDATA%\AI Subtitle Studio\installer-cache\<runtime_bundle_id>`; cache hoàn chỉnh được giữ qua retry/nâng cấp, staging luôn bị dọn khi thất bại/hủy/uninstall.
- Dùng `CreateDownloadPage` làm trang tiến độ và cập nhật tổng bytes, MiB/s, ETA, volume hiện tại và tiến độ toàn bundle. BITS dùng foreground priority vì người dùng đang chờ; nếu BITS/range/proxy không dùng được thì fallback tải Inno từ đầu với thông báo rõ ràng.
- Tạo Start Menu shortcut, optional desktop shortcut, Add/Remove Programs entry và uninstaller.
- Stable `AppId` để upgrade tại chỗ; runtime marker chứa `runtime_bundle_id` để bỏ qua download/extraction khi active runtime đúng cùng identity.
- Uninstall mặc định chỉ xóa binary/shortcut/registration. Checkbox dữ liệu riêng mới được xóa model/cache/log/history/settings/API key; output có checkbox và xác nhận nguy hiểm riêng.

**Low-VRAM GPU execution**:

- GPU inventory đọc `index,name,driver_version,memory.total` bằng `nvidia-smi`, đối chiếu `torch.cuda.is_available()`, `torch.cuda.get_device_properties()` và compute types của CTranslate2.
- `nvidia-smi` chỉ dùng cho diagnostics; STT preflight chỉ pass khi Torch CUDA khởi tạo được trên GPU đã chọn.
- Catalog thêm `small.en` và `small` bằng dữ liệu cấu hình, không đổi default `large-v3`.
- Profile 4 GiB: model đề xuất `small.en` cho video tiếng Anh, `compute_type=int8_float16` khi GPU hỗ trợ, `batch_size=1`, một GPU job duy nhất và không diarization.
- Transcription request mang `compute_type` và `batch_size`; UI hiển thị profile/VRAM và yêu cầu người dùng xác nhận đổi khỏi model không tương thích, không âm thầm đổi kết quả.
- Sau ASR phải xóa reference model, đồng bộ khi cần, `gc.collect()` và chỉ gọi `torch.cuda.empty_cache()` sau khi object sống đã được giải phóng; alignment model cũng được giải phóng sau dùng.
- CUDA OOM được phân loại riêng. Hệ thống cleanup và retry tối đa một lần với batch nhỏ hơn/cùng model; nếu vẫn lỗi thì dừng rõ ràng và đề xuất model/profile nhẹ hơn, không loop vô hạn.

**Uninstall ownership**:

- Installer sở hữu `{app}`, `runtime`, `runtime.previous`, `runtime.staging`, shortcut và uninstall registration.
- User-data mặc định không thuộc installer ownership. Full-clean chạy helper của app trước khi xóa runtime để xóa credential aliases qua keyring và QSettings chính xác.
- Checkbox output luôn mặc định tắt, hiển thị đường dẫn chính xác và yêu cầu xác nhận thứ hai. Với custom output directory, chỉ xóa file do app ghi nhận sở hữu; không xóa source video hoặc toàn bộ thư mục tùy ý.

**CI/CD**:

- Pull request/push CI dùng Windows runner và dependency test nhẹ để chạy nhanh.
- Full release build chạy trên clean, protected Windows x64 self-hosted runner có tối thiểu 40 GiB trống; không chạy mã PR không tin cậy trên runner này.
- Release workflow chỉ chạy từ tag `v*` hoặc `workflow_dispatch` có approval.
- Workflow build, attest, verify và upload một release bundle dưới dạng Actions
  artifact; chủ sở hữu tạo draft Release và upload asset bằng giao diện web.
- Workflow giữ `contents: read`; không cần GitHub CLI hoặc token ghi nội dung
  repository để tạo Release.

**Target Platform**: Windows 10/11 x64, NVIDIA GPU và driver tương thích runtime CUDA được bundle. Windows ARM và CPU-only STT nằm ngoài `v0.1.0`.

**Performance/UX Goals**:

- UI responsive trong toàn bộ pipeline.
- Installer hiển thị tổng dung lượng, bytes đã tải, phần trăm tổng, tốc độ MiB/s, ETA, nguồn local/cache/network và lỗi mạng có thể retry/resume.
- Hủy Setup trong lúc tải không làm mất phần `.part` hợp lệ; lỗi extraction/activation không buộc tải lại volume đã verify.
- Nâng cấp cùng `runtime_bundle_id` không tải lại bundle 2.33 GiB.
- App khởi động lần đầu không yêu cầu terminal hoặc Python cài sẵn.
- App hiển thị thông báo rõ ràng nếu thiếu NVIDIA GPU/driver hoặc thiếu dung lượng cho model.
- RTX 2050/GPU 4 GiB hoàn thành pipeline với low-VRAM profile mà không CUDA OOM trong bộ acceptance đã định nghĩa.
- Startup smoke test của frozen app hoàn tất dưới 30 giây trên máy validation sau khi antivirus cache đã ổn định.

**Security and Privacy**:

- Không commit API key, SQLite, output người dùng, model, log hoặc build artifact.
- Installer/runtime downloads phải có SHA-256; phát hành stable yêu cầu Authenticode cho installer và app executable.
- Nếu chưa có signing certificate, chỉ được publish GitHub pre-release kèm cảnh báo SmartScreen.
- API key không xuất hiện trong log, error, release artifact hoặc test fixture thật.
- Dependency audit và secret scan là release gates.

**Scale/Scope**: Một người dùng local; một GPU STT job; runtime nhiều phần nhưng một installer đầu vào; không có auto-updater trong `v0.1.0`; cập nhật qua installer phiên bản mới.

## Constitution Check

*GATE: Phải pass trước khi thực hiện và kiểm tra lại sau thiết kế.*

- **WhisperX stable pin**: PASS. `whisperx==3.8.6` vẫn là stable mới nhất được kiểm tra trên PyPI ngày 2026-07-30; pre-release bị loại.
- **Mandatory VAD**: PASS. Constitution 1.0.1, spec, contract, code và tests cùng yêu cầu Pyannote VAD bắt buộc qua `vad_method="pyannote"`; không có public VAD field/toggle và không truyền keyword `vad_filter` lỗi thời.
- **Model config**: PASS. `large-v3` vẫn là mặc định; `models.json` được bundle như resource; model weights không bundle.
- **System Info**: PASS. Frozen build phải copy package metadata để `importlib.metadata.version()` trả version runtime thật.
- **Interfaces**: PASS. Các fix packaging/data paths không bypass `STTEngine` hoặc `TranslationProvider`.
- **Worker execution**: PASS. Logging, model download, ffmpeg và installer không đưa công việc nặng lên Qt UI thread.
- **Single GPU STT job**: PASS. Frozen/GPU manual test phải xác nhận GPU lock vẫn serialize STT.

Low-VRAM profiles không vi phạm constitution: chúng bổ sung model config-driven và runtime parameters cho phần cứng hạn chế, không đổi default `large-v3`, không expose VAD, không thêm CPU fallback và không chạy song song GPU STT.

**Post-design re-check**: PASS. RC5 installer lifecycle, download/cache records, uninstall selection và GPU profiles giữ nguyên toàn bộ invariant. `vad_method="pyannote"` vẫn chỉ được đặt trong WhisperX wrapper; profile 4 GiB chỉ thay model/compute/batch đã được contract cho phép.

## Release Architecture

```text
Git tag v0.1.0
    |
    v
Protected release workflow
    |
    +--> test + dependency/secret/license checks
    |
    +--> PyInstaller onedir runtime
    |       |
    |       +--> frozen smoke tests
    |       +--> archive volumes < 1.9 GiB
    |
    +--> release-manifest.json + SHA256SUMS.txt
    |
    +--> Inno Setup online installer
            |
            +--> Authenticode sign
            +--> clean-VM install/upgrade/uninstall tests
            |
            v
       Verified Actions artifact bundle
            |
            +--> owner downloads bundle
            +--> owner creates draft Release in GitHub web UI
            +--> browser download + local verification
            +--> manual GPU/API acceptance
            |
            v
       Publish Release
```

## Project Structure

### Documentation

```text
README.md
CHANGELOG.md
SECURITY.md
CONTRIBUTING.md
THIRD_PARTY_NOTICES.md
docs/
├── GITHUB_SETUP.md
└── RELEASE_EXE.md
specs/001-desktop-subtitle-studio/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── release-artifacts.md
│   ├── gpu-execution-profiles.md
│   └── ...existing contracts
└── tasks.md
```

### Source and Packaging

```text
src/ai_subtitle_studio/
├── app.py
├── paths.py                    # frozen/dev resource and user-data paths
├── logging_config.py           # rolling file logs/startup diagnostics
└── ...existing modules

packaging/
├── ai-subtitle-studio.spec
├── hooks/
│   └── hook-whisperx.py
├── runtime_hooks/
├── installer/
│   └── ai-subtitle-studio.iss
├── assets/
│   ├── app.ico
│   └── version-info.txt
└── release-manifest.schema.json

scripts/
├── setup-windows.ps1
├── build-release.ps1
├── smoke-frozen.ps1
├── package-runtime.ps1
├── generate-release-manifest.ps1
└── verify-release.ps1

.github/
├── workflows/
│   ├── ci.yml
│   └── release-windows.yml
├── dependabot.yml
└── release.yml
```

**Structure Decision**: Giữ một desktop package hiện có; chỉ thêm lớp path/logging và toolchain phát hành. Không tạo client/server, service cloud hoặc updater riêng trong `v0.1.0`.

## Implementation Phases and Exit Gates

### Phase G0 — Constitution and STT Contract Reconciliation

1. Dùng workflow constitution để xác nhận invariant theo API stable hiện tại: Pyannote VAD bắt buộc thông qua `vad_method="pyannote"`, không có UI/config/CLI/request field cho phép tắt hoặc đổi VAD.
2. Amend constitution với lý do kỹ thuật và Sync Impact Report; không giảm yêu cầu chất lượng hay khả năng kiểm soát invariant.
3. Đồng bộ `spec.md`, `research.md`, `contracts/stt-engine-contract.md`, `tasks.md`, quickstart và test wording.
4. Xác nhận wrapper là điểm duy nhất chọn `vad_method` và mọi đường transcribe đều đi qua wrapper.
5. Chạy contract tests chứng minh không có VAD field công khai và `load_model` luôn nhận `vad_method="pyannote"`.

**Exit gate G0**:

- Constitution, spec, contract, task và code mô tả cùng một API/invariant.
- Không còn yêu cầu literal không được WhisperX 3.8.6 sử dụng.
- Constitution Check được đánh giá lại thành PASS trước Phase R0.

### Phase R0 — Repository Hygiene and Release Governance

1. Cập nhật `.gitignore` cho `outputs/**`, `.env*`, installer staging, release archives, local signing files và generated manifests.
2. Giữ `.gitkeep` nếu cần thư mục output rỗng; không commit các `.srt` hiện có.
3. Chạy secret scan và rà history trước commit đầu tiên.
4. Repository hiện là **public** tại `TuanKietHN/ai-subtitle-studio` để người dùng tải online installer không cần đăng nhập. Vì chưa có `LICENSE`, tài liệu MUST nói rõ source chỉ đang hiển thị công khai và chưa cấp quyền sử dụng lại; chọn license nguồn vẫn là quyết định riêng của chủ sở hữu.
5. Thêm README release-oriented, CHANGELOG, SECURITY, CONTRIBUTING và notices.
6. Chuẩn hóa version về một source trong `pyproject.toml`; app, PyInstaller, installer, tag và manifest đọc cùng version.
7. Khởi tạo Git bằng `git init -b main`, kiểm tra staged files, tạo initial commit sạch, rồi gắn remote GitHub.

**Exit gate R0**:

- `git status` sạch sau commit.
- Không có output/model/database/API key/build artifact trong index.
- Version thống nhất.
- Repository có tài liệu cài đặt, quyền riêng tư và hỗ trợ tối thiểu.

### Phase R1 — Runtime and Frozen-App Correctness

1. Thêm path resolver phân biệt source resource, frozen resource và user-writable data.
2. Di chuyển default SQLite/model/log/output khỏi bundle root.
3. Truyền `model_cache_dir` và GPU selection vào transcription request/runtime environment đúng contract.
4. Resolve `ffmpeg` theo thứ tự: explicit setting, bundled executable, PATH; hiển thị nguồn đang dùng trong System Info.
5. Thêm rolling file logging, startup exception dialog và đường dẫn “Mở thư mục log”.
6. Copy distribution metadata để System Info đọc đúng app/WhisperX/faster-whisper version trong frozen build.
7. Thêm frozen smoke mode không mở event loop vô hạn: kiểm resource, writable paths, imports, SQLite migration, keyring, Qt plugin, ffmpeg và GPU diagnostics.
8. Thêm tests cho path resolver, model cache propagation, bundled ffmpeg resolution, logging redaction và smoke mode.

**Exit gate R1**:

- Full source tests pass.
- Frozen smoke contract pass.
- App không ghi vào `_MEIPASS`, `_internal` hoặc `Program Files`.
- Model cache setting được dùng thật bởi WhisperX.
- Startup failure tạo log và thông báo có thể hành động.

### Phase R2 — Reproducible PyInstaller Runtime

1. Tạo clean Python 3.13.7 release venv.
2. Pin release dependencies và kiểm `pip check`.
3. Hoàn thiện spec/hook cho import động WhisperX, Pyannote, Faster-Whisper, CTranslate2, Torch, keyring backend, httpx certificates và package metadata.
4. Bundle `models.json`, icon/version metadata, ffmpeg và notices.
5. `upx=False`; chỉ include Qt modules/plugins được dùng.
6. Không include model weights, cache, `.lib` development artifacts, tests hoặc sample outputs.
7. Build bằng script duy nhất có `--clean`, deterministic staging directory và fail-fast.
8. Ghi file inventory, dependency versions, build timestamp UTC, commit SHA và sizes.
9. Chạy frozen smoke test từ `dist`, sau đó chạy trên Windows Sandbox/VM không có Python.

**Exit gate R2**:

- Executable mở UI trên clean Windows VM.
- WhisperX import thành công từ frozen runtime.
- `models.json`, Qt platform plugin, keyring và bundled ffmpeg hoạt động.
- Không có model hoặc dữ liệu cá nhân trong bundle.
- Runtime inventory không có file đơn lẻ vượt giới hạn phát hành.

### Phase R3A — RC4 Activation Regression and Atomic Runtime Swap

1. Khai báo rõ `ActiveRuntime := ExpandConstant('{app}\runtime')` và `PreviousRuntime := ExpandConstant('{app}\runtime.previous')`.
2. Trước extraction/rename, bắt buộc:

   ```pascal
   if not ForceDirectories(ExpandConstant('{app}')) then
     RaiseException('Không thể tạo thư mục cài đặt.');
   ```

3. Đặt `StageRoot := ExpandConstant('{app}\runtime.staging')`; xóa staging cũ an toàn rồi tạo lại. Không stage active payload dưới `{tmp}`.
4. Dùng `PrepareToInstall`/Restart Manager với `RegisterExtraCloseApplicationsResource` hoặc app mutex để phát hiện app cũ đang chạy trước download/swap. Yêu cầu đóng app mềm; nếu không đóng được thì dừng trước khi thay file.
5. Xác định `IsUpgrade := DirExists(ActiveRuntime)` trước mutation. Hiển thị “Đang cài mới” hoặc “Đang nâng cấp từ ...” và dùng thông báo lỗi/rollback đúng trường hợp, không nói “bản cũ được giữ lại” trong fresh install.
6. Atomic swap cùng volume: active -> previous, staging -> active; nếu bước hai lỗi thì rollback previous -> active. Chỉ xóa previous sau executable/smoke check thành công.
7. Dùng `try..finally`/deinitialize cleanup để dọn `runtime.staging` sau success, cancel và handled failure; thêm staging vào `[UninstallDelete]`.
8. Thêm regression test cho `{app}` ban đầu không tồn tại và test upgrade khi app đang chạy.

### Phase R3B — Resumable, Cached and Observable Runtime Delivery

1. Sinh `runtime_bundle_id` deterministic từ ordered volume size/hash và build identity; ghi vào manifest, generated `.iss` include và marker trong active runtime.
2. Resolve từng volume theo thứ tự tin cậy:
   - `{src}\<volume>` nếu người dùng tải sẵn cạnh Setup và SHA-256 đúng;
   - persistent installer cache nếu file hoàn chỉnh/hash đúng;
   - `.part` cache + BITS job cùng bundle identity để resume;
   - HTTPS fallback bằng Inno nếu BITS không khả dụng.
3. Không bao giờ dùng file chỉ vì trùng tên/kích thước. SHA-256 đúng mới được promote `.part` -> final cache và đưa vào extraction.
4. Dùng `CreateDownloadPage`; callback/state tổng hợp phải hiển thị volume N/T, tổng MiB đã tải/tổng MiB, phần trăm tổng, moving-average MiB/s và ETA. Tiến độ không reset về 0 khi chuyển `.001` sang `.002`.
5. BITS chạy foreground priority cho interactive install, lưu job id để cancel/resume và kiểm HTTP range/proxy. Nếu lỗi không hỗ trợ thì fallback có thông báo; không hạ integrity gate.
6. Cancel/mất mạng giữ `.part` và metadata cùng bundle id. Corrupt, sai hash, sai bundle id hoặc quá hạn retention bị xóa; verified complete cache được giữ để retry extraction/activation.
7. Nếu active marker có cùng `runtime_bundle_id`, skip runtime download/extraction và chỉ chạy phần installer metadata/shortcut cần thiết. Nếu marker thiếu hoặc mismatch, fail-safe bằng full verified install.
8. Kiểm dung lượng riêng cho download cache, staging, active, previous và rollback; không dùng một con số tạm thời gây thiếu disk giữa swap.
9. Thêm contract tests cho local-file reuse, complete-cache reuse, interrupted `.part` resume, BITS fallback, aggregate progress/ETA, wrong hash, activation retry không redownload và same-runtime upgrade skip.

### Phase R3C — Uninstall UX and Selective Data Cleanup

1. Thêm Start Menu shortcut “Gỡ cài đặt AI Subtitle Studio” trỏ tới `{uninstallexe}`.
2. Uninstall mặc định xóa binary, staging/previous, shortcut và registration nhưng giữ database, model, log, settings, credentials, installer cache và output.
3. Tạo checkbox mặc định tắt: **“Xóa model, cache, log, lịch sử và API key”**. Khi chọn, cleanup helper phải xóa model/cache/log/SQLite, QSettings registry và credential aliases qua keyring trước khi runtime bị xóa.
4. Tạo checkbox riêng mặc định tắt: **“Xóa phụ đề/output đã tạo”**. Hiển thị đường dẫn, số file/dung lượng và hộp xác nhận nguy hiểm thứ hai; không gộp với checkbox dữ liệu.
5. Với custom output directory, chỉ xóa file output do ứng dụng ghi nhận; không recursive-delete thư mục tùy ý và không bao giờ xóa video nguồn.
6. Nếu cleanup credential/settings thất bại, uninstaller ghi log và báo phần dữ liệu còn lại; không tuyên bố full cleanup thành công sai sự thật.
7. Test bốn ma trận: default preserve; data cleanup only; output cleanup only; full cleanup. Lặp lại với custom model/output paths và app đang chạy.

**Exit gate R3A-R3C**:

- Fresh install pass khi `{app}` chưa tồn tại; không còn lỗi activation RC4.
- Staging/active/previous luôn cùng volume và rollback giữ được active runtime cũ.
- Người dùng chỉ cần Setup; local/cache/resume hoạt động và mọi nguồn đều được hash verify.
- Retry extraction/activation không tải lại 2.33 GiB đã verify; same-runtime upgrade tải 0 byte runtime.
- Progress tổng, tốc độ và ETA được quan sát trên clean Windows.
- Uninstall mặc định không mất dữ liệu; hai lựa chọn cleanup hoạt động độc lập và output có double confirmation.

### Phase R3D — NVIDIA 4 GiB / RTX 2050 Execution Profile

1. Mở rộng GPU detection với total/free VRAM, compute capability, driver và Torch CUDA readiness. Populate GPU selector bằng inventory thực tế.
2. Loại fallback “`nvidia-smi` chạy được nghĩa là STT dùng được”; `torch.cuda.is_available()` và device initialization mới là preflight gate.
3. Mở rộng `models.json` bằng `small.en` và `small`, giữ đúng một default `large-v3`, thêm metadata VRAM/profile config-driven và validation tests.
4. Thêm `GpuExecutionProfile`/resolver. Profile 4 GiB dùng `small.en`, `int8_float16` nếu CTranslate2 báo hỗ trợ, `batch_size=1`; không diarization và vẫn giữ Pyannote VAD bắt buộc.
5. Truyền `batch_size` thật vào `model.transcribe()`; không chỉ lưu trong settings. Ghi effective model/compute/batch/GPU/VRAM vào log chẩn đoán không bí mật.
6. Kết thúc ASR phải giải phóng model trước khi load alignment; kết thúc alignment cũng giải phóng model/tensor. Đo peak allocated/reserved memory trong acceptance.
7. Chuẩn hóa CUDA OOM thành error code riêng; cleanup và retry tối đa một lần với batch 1/cùng model. Chuyển model chỉ sau xác nhận của người dùng.
8. UI đánh dấu model “phù hợp”, “có thể thiếu VRAM”, “không khuyến nghị”; lần đầu trên 4 GiB hiển thị một-click chọn profile nhẹ nhưng không thay default constitution trong config.
9. Unit/contract tests mock 4 GiB/8 GiB, compute-type support, OOM retry và model cleanup. Manual release gate chạy RTX 2050 4 GiB hoặc GPU NVIDIA 4 GiB tương đương với ít nhất hai MP4.

**Exit gate R3D**:

- GPU 4 GiB được nhận đúng tên/VRAM và không bị khóa theo GPU nhà phát triển.
- Low-VRAM profile chạy hết ASR + alignment + SRT trên hai video mà không OOM.
- Peak VRAM và effective profile được ghi nhận; UI vẫn responsive và GPU lock vẫn serialize job.
- `large-v3` vẫn là default; VAD vẫn hard-coded `pyannote`; không có CPU fallback ngoài phạm vi.

### Phase R4 — GitHub CI/CD and Repository Controls

1. `ci.yml` chạy format/static checks phù hợp, unit/contract/integration/gui tests trên Windows.
2. Tách test dependency nhẹ để CI không tải Torch CUDA nhiều GB cho mọi PR.
3. Thêm dependency review, secret scan và Dependabot.
4. Bật branch protection: required CI, không force-push `main`, review trước merge khi có cộng tác viên.
5. `release-windows.yml` chỉ nhận protected tag/manual approval; build full trên clean self-hosted runner.
6. Workflow tạo verified release bundle artifact; chủ sở hữu tạo draft Release
   bằng giao diện web và không overwrite immutable asset cùng version.
7. Upload installer, runtime volumes, manifest, checksums, notices, SBOM và provenance/attestation khi khả dụng.
8. Tải toàn bộ asset từ draft Release bằng trình duyệt và verify local trước
   publish.
9. Không cấp write token hoặc signing secret cho pull request jobs.
10. Release verifier bắt buộc kiểm `runtime_bundle_id`, cache marker schema, RC5 asset URL/hash và không cho publish nếu installer contract tests R3A-R3D chưa pass.

**Exit gate R4**:

- PR/push CI xanh.
- Release workflow tái tạo artifact từ tag.
- Asset names/version/checksum khớp contract.
- Self-hosted runner không chạy untrusted code.
- GitHub Release vẫn ở draft cho đến khi R5 pass.

### Phase R5 — Product Acceptance and Public Release

1. Clean Windows 10/11 x64 install test.
2. NVIDIA 8 GiB regression test và NVIDIA 4 GiB/RTX 2050 acceptance với ít nhất hai `.mp4`: profile selection, download model, queue tuần tự, cancel/retry/recovery, English SRT và peak VRAM.
3. Google và DeepSeek test bằng credential test riêng, không đưa key vào log.
4. Vietnamese/bilingual edit/export test.
5. No-GPU behavior test.
6. Subtitle Edit integration test nếu executable được cấu hình.
7. Antivirus/SmartScreen/signature observation; fresh-install missing `{app}`, app-running upgrade, local/cache/BITS resume, activation retry và same-runtime no-download tests.
8. Review release notes: prerequisites, download size, disk size, first-model download, known issues, privacy, uninstall.
9. Publish pre-release nếu chưa ký số hoặc còn known issue không chặn; chỉ đánh dấu stable/latest khi mọi stable gate pass.

**Exit gate R5 / Definition of Done**:

- Gate G0 đã đồng bộ constitution/spec/contract với VAD API stable.
- 86+ automated tests pass và test mới cho release correctness pass.
- Source repo sạch, không có secret/dữ liệu người dùng/binary lớn.
- Installer một-click cài thành công trên clean Windows.
- Installer RC5 không tái hiện activation bug RC4; download/cache/resume/upgrade/uninstall matrix pass.
- GPU NVIDIA 4 GiB hoàn thành low-VRAM acceptance profile mà không CUDA OOM.
- GPU STT, translation, edit, export, persistence và recovery pass manual acceptance.
- Installer/app được ký số cho stable release.
- GitHub Release có installer, runtime parts, SHA256, manifest, SBOM/notices và release notes.
- Latest release URL trong README tải đúng installer.
- Previous release vẫn có thể cài lại để rollback.

## Git and GitHub Publication Sequence

Các bước khởi tạo repository, CI, release tooling và các tag RC1-RC4 đã hoàn
thành trước addendum này. Từ trạng thái hiện tại:

1. Giữ nguyên tag/asset RC1-RC4 để audit; đánh dấu RC4 có known installer
   activation issue và không upload đè asset cũ.
2. Thực hiện R3A-R3D trên branch tính năng, bổ sung test tự động và review diff.
3. Chạy R4 cùng source/frozen/release verifier trên protected Windows runner.
4. Merge commit đã pass CI vào `main`; xác nhận working tree sạch và commit đích
   chính xác trước khi tag.
5. Tạo annotated tag mới `v0.1.0-rc.5` trên commit đã xác nhận; không di chuyển
   hoặc tái sử dụng tag RC4.
6. Workflow tạo verified RC5 bundle; chủ sở hữu tải artifact, tạo draft
   pre-release bằng giao diện GitHub và upload đúng các asset version-scoped.
7. Tải lại asset RC5 bằng trình duyệt, chạy `verify-release.ps1`, rồi hoàn tất
   clean-VM installer matrix và GPU 4 GiB acceptance trong R5.
8. Chỉ publish RC5 pre-release khi mọi RC gate pass. Khi stable gates gồm ký số
   pass, tạo tag `v0.1.0`, publish stable và cập nhật README latest-download.

## Versioning, Rollback and Artifact Policy

- Semantic Versioning: `MAJOR.MINOR.PATCH`; RC dùng `-rc.N`.
- Một tag tương ứng đúng một commit và một bộ asset immutable.
- Không rebuild rồi upload đè cùng tên/version.
- Release lỗi được đánh dấu pre-release/deprecated; không xóa ngay nếu cần audit.
- Rollback bằng installer của release trước; data schema migration phải backward-safe hoặc có backup trước migration.
- Installer tạo backup SQLite trước upgrade có migration.
- Model cache và output không thuộc installer ownership.

## Risk Register

| Risk | Impact | Mitigation | Gate |
|---|---|---|---|
| WhisperX stable tương lai đổi API VAD | Contract/code có thể lệch constitution | Bắt buộc amend constitution/contract trước khi nâng version | G0 |
| WhisperX import động bị thiếu trong bundle | STT chỉ lỗi sau khi người dùng chạy | Custom hook + frozen import/STT smoke | R2 |
| Torch CUDA runtime vượt 2 GiB | Không upload được một asset | Multi-volume <1.9 GiB + online installer | R3 |
| GitHub runner thiếu disk/time | Release build thất bại | Protected self-hosted clean runner >=40 GiB | R4 |
| App ghi vào bundle/Program Files | Mất dữ liệu hoặc permission error | QStandardPaths/path resolver + clean VM tests | R1 |
| ffmpeg thiếu hoặc sai license | Audio extraction lỗi/pháp lý | Pinned binary + SHA256 + notices/source link | R2 |
| Unsigned executable bị SmartScreen | Người dùng không tin/cài khó | Authenticode stable gate; unsigned chỉ pre-release | R3/R5 |
| API key lọt log/repo | Security incident | Keyring + redaction tests + secret scan | R0/R1/R4 |
| Model cache setting không có tác dụng | Tải model sai nơi, đầy disk | Propagate into request + integration test | R1 |
| Release asset bị hỏng/đổi | Cài đặt lỗi hoặc supply-chain risk | SHA-256, signature, immutable tag/assets | R3/R4 |
| Public repo chưa có license | Người xem có thể hiểu nhầm source đã là open source hoặc được phép tái sử dụng | README/docs nói rõ chưa có license; không tự gán license và yêu cầu owner decision trước khi quảng bá quyền tái sử dụng | R0 |
| `{app}` chưa tồn tại trước atomic swap | Fresh install luôn lỗi sau khi tải 2.33 GiB | `ForceDirectories({app})` + missing-dir regression test | R3A |
| Staging ở `{tmp}` khác volume | `RenameFile` không atomic hoặc thất bại | Stage tại `{app}\runtime.staging` | R3A |
| Mạng ngắt làm tải lại toàn bundle | Trải nghiệm cài đặt kém, tốn băng thông | Persistent `.part`, BITS resume, local/cache reuse | R3B |
| BITS bị proxy/range policy chặn | Installer không tiến triển | Capability check + Inno HTTPS fallback + actionable error | R3B |
| Full cleanup xóa nhầm output/video | Mất dữ liệu người dùng | Default preserve, separate checkbox, exact path, double confirmation, owned-file list | R3C |
| GPU 4 GiB dùng float16/model lớn | CUDA OOM ở ASR hoặc alignment | small.en + int8_float16 + batch 1 + phase cleanup + real 4 GiB gate | R3D |
| `nvidia-smi` có nhưng Torch CUDA lỗi | False-positive GPU support | Torch device initialization là gate, nvidia-smi chỉ diagnostics | R3D |

## Complexity Tracking

| Decision | Why Required | Simpler Alternative Rejected |
|---|---|---|
| PyInstaller `onedir` | Native ML/Qt runtime lớn, dễ debug và test | `onefile` phải giải nén nhiều GB mỗi lần và khó chẩn đoán |
| Online installer + runtime volumes | GitHub giới hạn mỗi asset dưới 2 GiB nhưng Torch CUDA lớn hơn | Commit binary/Git LFS hoặc yêu cầu người dùng ghép file thủ công |
| Self-hosted release runner | Full CUDA build cần disk lớn và môi trường kiểm soát | Build full trên mọi PR/hosted runner tốn thời gian và dễ hết disk |
| Separate light CI dependencies | Tests phần lớn dùng mocks/contracts | Tải Torch CUDA nhiều GB cho mỗi PR không tạo thêm tín hiệu tương xứng |
| BITS + persistent installer cache | Native Inno downloader không có persistent partial resume | Tải lại 2.33 GiB sau lỗi không đạt yêu cầu UX |
| Config-driven GPU execution profiles | Một cấu hình float16 không phù hợp mọi VRAM | Hard-code riêng RTX 2050 sẽ khóa phần cứng và khó mở rộng |
| Selective uninstall cleanup helper | Credential Manager/QSettings không thể xóa chỉ bằng `[UninstallDelete]` | Giữ tất cả hoặc xóa đệ quy toàn bộ đều không đáp ứng quyền kiểm soát dữ liệu |

Không có vi phạm constitution. Độ phức tạp bổ sung chỉ nằm ở delivery toolchain và được yêu cầu trực tiếp bởi kích thước runtime, giới hạn GitHub và trải nghiệm cài đặt không dùng dòng lệnh.
