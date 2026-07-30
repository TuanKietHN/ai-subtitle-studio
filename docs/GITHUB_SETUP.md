# GitHub Repository Setup Without GitHub CLI

Quy trình này dùng giao diện web GitHub và lệnh `git`, không yêu cầu GitHub CLI.
Hướng dẫn build/upload EXE đầy đủ nằm tại
[`docs/RELEASE_EXE.md`](./RELEASE_EXE.md).

## 1. Tạo repository

Tạo `ai-subtitle-studio` trên `https://github.com/new` dưới dạng private repository.
Không khởi tạo README, license hoặc `.gitignore` vì các file đó đã có trong
source.

Thêm remote và push:

```powershell
git remote add origin https://github.com/<owner>/ai-subtitle-studio.git
git remote -v
git push -u origin main
```

Giữ repository private cho đến khi chủ sở hữu chọn source license, kiểm tra
history và quyết định rõ việc công khai source. Third-party notices đã có nhưng
không tự động thay thế quyết định license của chủ sở hữu.

## 2. Bảo vệ `main`

Trong **Settings → Rules → Rulesets**, tạo branch ruleset cho default branch:

- Yêu cầu pull request trước khi merge khi có cộng tác viên.
- Yêu cầu ít nhất một approval và dismiss stale approvals.
- Yêu cầu conversation resolution.
- Chặn force-push và branch deletion.
- Chọn các check `Source CI` làm required sau khi chúng đã chạy ít nhất một lần.

Trong **Settings → Security**, bật Dependabot alerts, secret scanning và push
protection nếu GitHub plan của repository hỗ trợ.

## 3. Phát hành thủ công

Quy trình khuyến nghị hiện tại:

1. Build và xác minh local theo `docs/RELEASE_EXE.md`.
2. Push `main` bằng Git.
3. Tạo và push annotated tag `vX.Y.Z`.
4. Tạo draft Release trên giao diện web.
5. Upload toàn bộ file trong `release\`.
6. Tải lại toàn bộ asset bằng trình duyệt và chạy
   `verify-release.ps1 -ReleaseDirectory`.
7. Chạy clean-machine/GPU/API acceptance.
8. Publish dưới dạng pre-release nếu chưa ký số hoặc còn stable gate chưa đạt.

## 4. Workflow build bundle tùy chọn

`.github/workflows/release-windows.yml` không tạo GitHub Release. Workflow chỉ
build, attest, xác minh và upload một artifact bundle để chủ sở hữu tải xuống rồi
đưa lên Release bằng giao diện web.

Nếu dùng workflow, đăng ký một Windows x64 self-hosted runner riêng cho
repository với labels:

```text
self-hosted
Windows
X64
ai-subtitle-release
```

Runner không được chạy pull-request code không tin cậy. Cài:

- Python 3.13.7.
- 7-Zip 24.09.
- Inno Setup 6.7.3.
- FFmpeg 8.0.1.
- Windows SDK SignTool nếu build stable.

Tạo environment `windows-release`. Chỉ stable build mới cần các environment
secret:

```text
SIGNING_PFX_BASE64
SIGNING_PFX_PASSWORD
```

Workflow dùng quyền `contents: read`; việc tạo và publish Release luôn là thao
tác thủ công của chủ sở hữu trên web.

## 5. Quy tắc release

- Một tag tương ứng một commit và một bộ asset bất biến.
- Không upload đè asset của tag đã publish; tạo version/tag mới.
- Installer và runtime volume phải cùng owner/repository/tag.
- Stable yêu cầu Authenticode hợp lệ.
- Unsigned installer chỉ được phát hành dưới dạng pre-release.
