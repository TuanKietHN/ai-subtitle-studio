# AI Subtitle Studio v0.1.0-rc.5

> **Pre-release để kiểm thử.** Bản RC5 chưa ký số, chưa phải bản stable và có
> thể bị Windows SmartScreen cảnh báo. Không dùng các asset được tạo từ working
> tree có `git_commit=uncommitted`.

## Dành cho người dùng

Tải một file duy nhất:

```text
AI-Subtitle-Studio-Setup-v0.1.0-rc.5.exe
```

Mở Setup và làm theo hướng dẫn. Setup tự tải runtime đúng phiên bản; người dùng
không cần tự cài Python, FFmpeg, 7-Zip hoặc Inno Setup. Whisper model không nằm
trong bộ cài và sẽ được tải khi người dùng chọn model lần đầu.

Repository và release asset phải truy cập được mà không cần đăng nhập GitHub.
Không tải riêng hai file runtime trừ khi muốn đặt chúng cạnh Setup để cài từ
file đã tải sẵn.

## Điểm mới trong RC5

- Sửa lỗi RC4 tải và giải nén xong nhưng không kích hoạt được runtime khi cài
  mới.
- Runtime mới được chuẩn bị cùng ổ đĩa, kiểm tra trước khi kích hoạt và rollback
  về bản cũ nếu nâng cấp thất bại.
- Setup tái sử dụng file cạnh bộ cài hoặc cache đã xác minh, tiếp tục phần tải
  bị gián đoạn qua dịch vụ truyền nền của Windows và chuyển sang HTTPS khi cơ
  chế tiếp tục không khả dụng.
- Trang tải hiển thị tiến độ toàn bundle, dung lượng, tốc độ và thời gian còn
  lại ước tính.
- Nâng cấp cùng runtime identity không tải lại runtime nhiều gigabyte.
- Có shortcut gỡ ứng dụng trong Start Menu.
- Gỡ mặc định giữ model, cache, log, lịch sử, settings, API key và phụ đề.
- Hai lựa chọn xóa dữ liệu riêng và xóa output độc lập, mặc định tắt; output ở
  thư mục tùy chỉnh chỉ xóa file được ứng dụng ghi nhận sở hữu.
- Nhận diện GPU theo GPU id, VRAM, CUDA readiness và kiểu tính toán thực tế,
  không khóa cứng theo tên GPU của máy phát triển.
- Thêm `small.en` và `small`, profile nhẹ cho NVIDIA khoảng 4 GiB, truyền đúng
  compute type/batch size, giải phóng bộ nhớ giữa ASR và alignment, và giới hạn
  CUDA OOM retry tối đa một lần.

## Tương thích

- Windows 10/11 x64.
- STT yêu cầu GPU NVIDIA/CUDA tương thích; các phần không cần STT vẫn mở được
  khi không có GPU hợp lệ.
- `large-v3` vẫn là model mặc định. Profile 4 GiB chỉ được áp dụng sau khi người
  dùng xác nhận.
- Chưa được quảng cáo GPU 4 GiB là “đã xác minh” cho đến khi acceptance pass
  trên RTX 2050 4 GiB hoặc phần cứng NVIDIA 4 GiB tương đương.

## Nâng cấp và gỡ ứng dụng

- Đóng AI Subtitle Studio trước khi nâng cấp hoặc gỡ.
- Có thể chạy RC5 Setup trực tiếp trên bản cũ; không cần gỡ trước.
- Gỡ thông thường chỉ xóa ứng dụng và shortcut.
- Chỉ chọn xóa dữ liệu riêng nếu không cần model, lịch sử, settings và API key.
- Xóa output có hộp xác nhận riêng; hãy sao lưu phụ đề quan trọng trước khi
  chọn.

## Known issues và release gates còn mở

- Installer/app chưa có Authenticode; SmartScreen có thể cảnh báo.
- Cần chạy ma trận fresh install, mất mạng/tải tiếp, upgrade và uninstall trên
  máy Windows sạch.
- Cần acceptance thật trên NVIDIA 4 GiB.
- Cần kiểm thử Google và DeepSeek bằng credential test riêng.
- Cần kiểm thử no-GPU, SmartScreen và chữ ký số trước stable.
- Một số dependency advisory do WhisperX/Torch upstream vẫn chặn stable theo
  policy hiện tại.
- Dependency gián tiếp `lightning==2.6.5` có advisory
  `PYSEC-2026-3624`. Pyannote VAD đi qua loader bị ảnh hưởng, nhưng RC5 chỉ nạp
  checkpoint VAD cố định trong WhisperX đã được pin và hash, không cho chọn
  checkpoint Lightning tùy ý; stable tiếp tục bị chặn cho đến khi pin được bản
  Lightning đã vá.

## Asset bắt buộc của release

```text
AI-Subtitle-Studio-Setup-v0.1.0-rc.5.exe
AI-Subtitle-Studio-Runtime-v0.1.0-rc.5.7z.001
AI-Subtitle-Studio-Runtime-v0.1.0-rc.5.7z.002
release-manifest-v0.1.0-rc.5.json
SHA256SUMS-v0.1.0-rc.5.txt
SBOM-v0.1.0-rc.5.json
THIRD-PARTY-NOTICES-v0.1.0-rc.5.txt
```

Không upload source-only ZIP như một bản thay thế cho Setup. Hai file “Source
code” do GitHub tự tạo không chứa runtime cài sẵn.

## Kiểm tra trước khi bấm Publish release

1. Source đã commit, push và working tree sạch.
2. Tag `v0.1.0-rc.5` trỏ đúng commit cần phát hành.
3. Bundle được build lại sau commit; manifest không chứa `uncommitted`.
4. Tải lại toàn bộ asset từ draft Release bằng trình duyệt.
5. Chạy:

   ```powershell
   .\scripts\verify-release.ps1 `
     -Version 0.1.0-rc.5 `
     -ReleaseDirectory "C:\duong-dan\toi\asset-da-tai"
   ```

6. Ghi bằng chứng các gate thủ công vào `quickstart.md`.
7. Chọn **Set as a pre-release**. Không chọn stable/latest cho RC5.
