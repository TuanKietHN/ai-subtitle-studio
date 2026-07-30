# Hướng dẫn build EXE và tạo GitHub Release thủ công

Tài liệu này không dùng GitHub CLI. Mã nguồn được đẩy bằng `git`; repository và
Release được tạo trên giao diện web GitHub.

## 1. Artifact người dùng cần tải

File người dùng bấm tải là:

```text
AI-Subtitle-Studio-Setup-vX.Y.Z.exe
```

Đây là online installer nhỏ. Khi cài đặt, nó tự tải các volume runtime cùng tag,
kiểm SHA-256 rồi giải nén. Vì vậy một Release phải có đủ:

```text
AI-Subtitle-Studio-Setup-vX.Y.Z.exe
AI-Subtitle-Studio-Runtime-vX.Y.Z.7z.001
AI-Subtitle-Studio-Runtime-vX.Y.Z.7z.002
...các volume tiếp theo nếu có
release-manifest-vX.Y.Z.json
SHA256SUMS-vX.Y.Z.txt
SBOM-vX.Y.Z.json
THIRD-PARTY-NOTICES-vX.Y.Z.txt
```

Không chỉ upload riêng file Setup: installer sẽ thất bại nếu thiếu runtime
volume hoặc URL repository/tag không khớp.

## 2. Chuẩn bị máy build

Máy Windows x64 cần:

- Python đúng version trong `packaging/release-config.json`.
- Các dependency trong `packaging/release-requirements.txt`.
- FFmpeg đúng version được pin và có `ffmpeg.exe` trên `PATH`.
- 7-Zip tại `C:\Program Files\7-Zip`.
- Inno Setup 6/7.
- Tối thiểu 40 GiB trống cho build CUDA.
- Chứng thư Authenticode chỉ khi phát hành stable.

Chạy kiểm tra source trước:

```powershell
python -m pytest tests\unit tests\contract tests\integration tests\gui
python -m pip check
.\scripts\verify-repository.ps1
git status --short
```

## 3. Chọn version và repository chính xác

Ví dụ:

```powershell
$version = "0.1.0-rc.1"
$owner = "<github-username>"
$repository = "ai-subtitle-studio"
```

Version phải khớp trong:

- `pyproject.toml`
- `packaging/release-config.json`
- `packaging/assets/version-info.txt`
- tag `v$version`

`$owner` và `$repository` được nhúng vào URL tải runtime của installer. Phải
chọn đúng trước khi chạy `build-installer.ps1`.

## 4. Build runtime và installer

Từ thư mục gốc dự án:

```powershell
.\scripts\build-release.ps1 -Version $version -Clean
.\scripts\package-runtime.ps1 -Version $version

Copy-Item `
  ".\release-staging\build\SBOM-v$version.json" `
  ".\release\SBOM-v$version.json" `
  -Force

Copy-Item `
  ".\THIRD_PARTY_NOTICES.md" `
  ".\release\THIRD-PARTY-NOTICES-v$version.txt" `
  -Force

.\scripts\build-installer.ps1 `
  -Version $version `
  -Owner $owner `
  -Repository $repository `
  -Channel prerelease

.\scripts\verify-release.ps1 -Version $version
```

Kết quả nằm trong `release\`. Thư mục này được `.gitignore` bỏ qua và không được
commit vào repository.

Với stable release, phải có chứng thư và chạy build installer với
`-Channel stable` cùng `-CertificatePath` hoặc `-Thumbprint`. Không có chữ ký thì
chỉ phát hành pre-release.

## 5. Tạo repository và push bằng Git

Trên `https://github.com/new`:

1. Tạo repository, mặc định để **private**.
2. Không chọn tạo README, `.gitignore` hoặc license vì dự án đã có sẵn.
3. Sao chép HTTPS URL của repository.

Sau đó:

```powershell
git remote add origin https://github.com/<owner>/ai-subtitle-studio.git
git remote -v
git push -u origin main
```

Tạo tag nếu version đó chưa có:

```powershell
git tag -a "v$version" -m "AI Subtitle Studio v$version"
git push origin "v$version"
```

Nếu tag đã có, kiểm tra nó trỏ đúng commit thay vì tạo lại:

```powershell
git show --no-patch "v$version"
```

Không xóa rồi tái sử dụng một tag đã phát hành.

## 6. Tạo Release trên giao diện GitHub

1. Mở repository → **Releases** → **Draft a new release**.
2. Chọn tag `v$version`.
3. Đặt tiêu đề `AI Subtitle Studio v$version`.
4. Chép nội dung version tương ứng từ `CHANGELOG.md`.
5. Với RC/chưa ký số, bật **Set as a pre-release** và không chọn latest.
6. Kéo toàn bộ file trong `release\` vào khu vực upload.
7. Đợi tất cả file upload xong; kiểm tra không volume nào từ 2 GiB trở lên.
8. Chọn **Save draft** để kiểm tra trước, sau đó mới **Publish release**.

Workflow `Windows release bundle` là tùy chọn. Nó không tạo Release và không dùng
GitHub CLI; nó chỉ build, xác minh rồi cung cấp một artifact bundle trong trang
Actions. Có thể tải bundle đó, giải nén và upload các file lên Release bằng web.

## 7. Xác minh lại file đã tải từ GitHub

Tải toàn bộ asset của Release bằng trình duyệt vào một thư mục riêng, ví dụ:

```text
C:\Temp\ai-subtitle-studio-v0.1.0-rc.1
```

Sau đó chạy:

```powershell
.\scripts\verify-release.ps1 `
  -Version $version `
  -ReleaseDirectory "C:\Temp\ai-subtitle-studio-v0.1.0-rc.1"
```

Script xác minh tên file, kích thước, SHA-256, manifest, thứ tự runtime volume
và chữ ký đối với stable release.

## 8. Kiểm thử trước khi cho người dùng tải

Tối thiểu với pre-release:

- Cài trên Windows 10/11 x64 sạch, không có Python.
- Kiểm tra tải bị gián đoạn hoặc volume sai hash bị từ chối.
- Chạy hai video trên NVIDIA GPU và kiểm tra queue/cancel/retry.
- Kiểm tra Google/DeepSeek bằng credential test riêng.
- Kiểm tra uninstall giữ database, model và output.
- Ghi rõ installer chưa ký và cảnh báo SmartScreen nếu chưa có Authenticode.

Chỉ đánh dấu stable/latest khi mọi stable gate trong
`specs/001-desktop-subtitle-studio/plan.md` đã đạt.

## 9. Kiểm tra `.gitignore` trước khi push

```powershell
git status --short
git check-ignore -v `
  release `
  dist `
  build `
  .venv `
  outputs\example.srt `
  sample.mp4 `
  signing-certificate.pfx
```

Không dùng `git add -f` cho build artifact, video, subtitle, database, API key,
model cache hoặc signing material.

