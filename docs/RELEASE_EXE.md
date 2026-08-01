# Hướng dẫn đưa dự án lên GitHub và phát hành file Setup EXE

Tài liệu này dành cho người chưa từng phát hành phần mềm. Hãy làm từ trên xuống
dưới, không bỏ qua bước kiểm tra.

Tài liệu **không dùng GitHub CLI (`gh`)**:

- Dùng lệnh `git` để đưa mã nguồn lên GitHub.
- Dùng trình duyệt web để tạo repository và GitHub Release.
- Người dùng cuối chỉ cần tải một file `Setup.exe`.

---

## 1. Hiểu bốn từ quan trọng trước khi bắt đầu

Hãy tưởng tượng dự án là một bộ đồ chơi:

| Từ | Hiểu đơn giản |
|---|---|
| Repository, gọi tắt là repo | Chiếc hộp chứa mã nguồn, tài liệu và lịch sử sửa đổi |
| Commit | Một lần chụp ảnh trạng thái mã nguồn |
| Tag | Nhãn dán vào một commit, ví dụ `v0.1.0-rc.1` |
| Release | Trang tải xuống dành cho người dùng, gắn với một tag |
| Asset | Từng file được đính kèm trong Release |

`git push` chỉ đưa **mã nguồn và tag** lên GitHub. Nó không tự tạo trang Release
và cũng không tự upload file cài đặt.

Vì vậy công việc được chia thành ba phần:

```text
Phần 1: Push mã nguồn lên repository
Phần 2: Push tag đánh dấu phiên bản
Phần 3: Tạo Release và upload các file cài đặt
```

---

## 2. Người dùng cuối sẽ tải file nào?

Người dùng chỉ cần bấm tải file:

```text
AI-Subtitle-Studio-Setup-vX.Y.Z.exe
```

Ví dụ:

```text
AI-Subtitle-Studio-Setup-v0.1.0-rc.2.exe
```

Đây là **online installer**, nghĩa là một trình cài đặt nhỏ có nhiệm vụ:

1. Tự tải runtime đúng phiên bản từ GitHub Release.
2. Kiểm tra SHA-256 để phát hiện file hỏng hoặc bị thay đổi.
3. Dùng bản 7-Zip được nhúng sẵn để giải nén.
4. Cài ứng dụng vào máy.
5. Tạo shortcut.
6. Cho phép gỡ cài đặt sau này.

Người dùng không phải tự cài Python, dependency, FFmpeg, 7-Zip hay Inno Setup.

Tuy nhiên, GitHub Release vẫn phải chứa đầy đủ các file phía sau:

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

Các file `.001`, `.002` giống như một chiếc hộp lớn được chia thành nhiều hộp
nhỏ. Setup sẽ tự tải tất cả rồi ghép lại.

**Không được chỉ upload riêng Setup EXE.** Nếu thiếu một volume, Setup sẽ báo lỗi
và không thể cài ứng dụng.

---

## 3. File nào được push vào repo, file nào không?

### Được push

- Mã nguồn trong `src/`.
- Test trong `tests/`.
- Tài liệu trong `docs/`.
- Script build trong `scripts/`.
- Cấu hình đóng gói trong `packaging/`.
- Workflow trong `.github/workflows/`.
- `README.md`, `CHANGELOG.md`, `LICENSE` và các file cấu hình dự án.

### Không được push

- Thư mục `release/`, `dist/`, `build/`.
- File EXE, DLL, ZIP, 7z hoặc runtime volume.
- Video, audio và subtitle của người dùng.
- Database, log và model cache.
- API key, credential Google, file `.env`.
- Chứng thư ký số như `.pfx`, `.p12`, `.pem`, `.key`.
- Môi trường Python như `.venv/`.

Các file không được push đã được chặn trong `.gitignore`. File cài đặt sẽ được
upload vào **GitHub Release**, không được commit vào lịch sử Git.

---

## 4. Chọn repository public hay private

Đây là lựa chọn quan trọng.

### Chọn Public nếu

- Muốn bất kỳ người dùng nào cũng tải và cài được ứng dụng.
- Setup sẽ tải runtime trực tiếp từ GitHub Release mà không cần đăng nhập.
- Không có mã nguồn bí mật trong repository.

### Chọn Private nếu

- Chỉ thành viên đã được cấp quyền mới được xem và tải.
- Chưa muốn công bố mã nguồn.

Online installer hiện tại tải asset bằng URL GitHub thông thường và không có màn
hình đăng nhập GitHub. Vì vậy, để phát hành cho người dùng phổ thông, hãy dùng
**repository public**.

Nếu muốn giữ mã nguồn private, cần đặt bộ cài ở một nơi public khác như một
repository phát hành riêng hoặc CDN, sau đó sửa URL tải trong installer. Đây là
một công việc khác và không nằm trong quy trình đơn giản của tài liệu này.

---

## 5. Chuẩn bị máy dùng để build

Đây là các công cụ dành cho **người phát triển**, không phải dành cho người dùng
cuối:

- Windows x64.
- Git.
- Python đúng phiên bản trong `packaging/release-config.json`.
- Dependency trong `packaging/release-requirements.txt`.
- FFmpeg đúng phiên bản được pin.
- 7-Zip tại `C:\Program Files\7-Zip`.
- Inno Setup 7 được khuyến nghị; script vẫn có thể tìm Inno Setup 6.
- Ít nhất 40 GiB dung lượng trống cho bản CUDA.
- Chứng thư Authenticode nếu muốn phát hành bản stable có ký số.

Mở PowerShell tại thư mục gốc của dự án:

```powershell
cd C:\Users\Kiet\Documents\Codex\2026-07-08\ai-subtitle-studio
```

Nếu dấu nhắc PowerShell đang đứng đúng thư mục này thì không cần chạy lại `cd`.

---

## 6. Chọn tên và phiên bản

Trong các ví dụ bên dưới, hãy thay:

- `TEN_GITHUB_CUA_BAN` bằng username GitHub thật.
- `ai-subtitle-studio` bằng tên repository thật nếu bạn chọn tên khác.

Khai báo ba giá trị để các lệnh phía sau dễ đọc:

```powershell
$version = "0.1.0-rc.2"
$owner = "TEN_GITHUB_CUA_BAN"
$repository = "ai-subtitle-studio"
```

Ví dụ, nếu trang GitHub của bạn là `https://github.com/anhkiet`, hãy viết:

```powershell
$owner = "anhkiet"
```

Version phải khớp trong:

- `pyproject.toml`
- `packaging/release-config.json`
- `packaging/assets/version-info.txt`
- Git tag `v$version`

Tên owner và repository được nhúng vào Setup để tạo địa chỉ tải runtime:

```text
https://github.com/OWNER/REPOSITORY/releases/download/TAG/TEN_FILE
```

Vì vậy phải chọn đúng `$owner` và `$repository` **trước khi build Setup**.

---

## 7. Kiểm tra mã nguồn trước khi push

### Bước 7.1: Xem trạng thái Git

```powershell
git status --short --branch
```

Kết quả tốt có dạng:

```text
## main
```

Nếu phía dưới có tên file, các file đó đang được thêm, sửa hoặc chưa commit.
Không phải file thay đổi nào cũng xấu; điều quan trọng là phải biết mình sắp
đưa file nào lên mạng.

### Bước 7.2: Chạy kiểm thử

```powershell
python -m pytest tests\unit tests\contract tests\integration tests\gui
python -m pip check
.\scripts\verify-repository.ps1
```

Chỉ tiếp tục khi:

- Test báo `passed`.
- `pip check` không báo dependency bị hỏng.
- `verify-repository.ps1` báo thành công.

### Bước 7.3: Kiểm tra file bí mật và file lớn

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

Mỗi đường dẫn ở lệnh `git check-ignore` phải hiện ra quy tắc `.gitignore` đang
chặn nó.

Tuyệt đối không dùng `git add -f` cho:

- API key hoặc credential.
- Video, audio và subtitle.
- Database.
- Model AI.
- File cài đặt.
- Chứng thư ký số.

### Bước 7.4: Commit thay đổi cần thiết

Xem lại thay đổi:

```powershell
git diff
```

Sau khi chắc chắn không có bí mật:

```powershell
git add .
git status --short
git commit -m "Prepare project for GitHub release"
```

`git add .` mới chỉ chọn file. Hãy luôn đọc kết quả `git status --short` trước
khi chạy `git commit`.

Kiểm tra lại:

```powershell
git status --short --branch
git log -1 --oneline
```

Trước khi build Release chính thức, trạng thái Git nên sạch.

---

## 8. Tạo repository trên trang web GitHub

1. Đăng nhập GitHub bằng trình duyệt.
2. Mở <https://github.com/new>.
3. Trong **Owner**, chọn đúng tài khoản của bạn.
4. Trong **Repository name**, nhập `ai-subtitle-studio`.
5. Viết mô tả ngắn, ví dụ:

   ```text
   Windows desktop application for creating and translating subtitles.
   ```

6. Chọn **Public** nếu muốn người dùng bình thường cài bằng online installer.
7. Không chọn **Add a README file**.
8. Không chọn thêm `.gitignore`.
9. Không chọn thêm license tại đây vì dự án đã quản lý các file của nó.
10. Bấm **Create repository**.

Lý do không tạo README hoặc `.gitignore` trên GitHub: repository local đã có
lịch sử riêng. Tạo thêm file trên web có thể làm lần push đầu tiên bị từ chối vì
hai bên có lịch sử khác nhau.

Sau khi tạo xong, GitHub sẽ hiện địa chỉ HTTPS giống:

```text
https://github.com/TEN_GITHUB_CUA_BAN/ai-subtitle-studio.git
```

Hãy sao chép địa chỉ đó.

---

## 9. Nối dự án local với GitHub

### Bước 9.1: Kiểm tra remote

```powershell
git remote -v
```

Nếu lệnh không hiện gì, thêm remote:

```powershell
git remote add origin https://github.com/TEN_GITHUB_CUA_BAN/ai-subtitle-studio.git
```

Nếu đã có `origin` nhưng URL sai, sửa lại:

```powershell
git remote set-url origin https://github.com/TEN_GITHUB_CUA_BAN/ai-subtitle-studio.git
```

Kiểm tra lần nữa:

```powershell
git remote -v
```

Phải thấy cả dòng `(fetch)` và `(push)` trỏ tới đúng repository.

### Bước 9.2: Push nhánh main

```powershell
git push -u origin main
```

`-u` giúp Git nhớ rằng nhánh `main` local đi cùng nhánh `main` trên GitHub. Các
lần sau thường chỉ cần:

```powershell
git push
```

### Nếu Git hỏi đăng nhập

Đăng nhập GitHub trên trình duyệt không phải lúc nào cũng đồng nghĩa Git trong
PowerShell đã đăng nhập.

Git for Windows thường mở Git Credential Manager và yêu cầu xác nhận bằng trình
duyệt. Hãy chọn đúng tài khoản GitHub.

Nếu Git hỏi `Password`, không nhập mật khẩu GitHub thông thường. GitHub yêu cầu
Personal Access Token cho thao tác Git qua HTTPS. Không gửi token cho người khác
và không ghi token vào file của dự án.

### Bước 9.3: Kiểm tra trên web

Tải lại trang repository và kiểm tra:

- Thấy các thư mục `src`, `tests`, `docs`, `scripts`.
- Thấy `README.md`.
- Không thấy `release`, `dist`, `.venv`, video hoặc credential.
- Nhánh đang xem là `main`.
- Commit mới nhất giống kết quả `git log -1 --oneline`.

Đến đây mã nguồn đã được đưa lên GitHub, nhưng người dùng vẫn chưa có trang tải
Setup. Phần tiếp theo tạo bộ cài.

---

## 10. Build runtime và Setup EXE

Hãy chắc chắn ba biến vẫn có giá trị đúng:

```powershell
$version
$owner
$repository
```

Nếu PowerShell đã được đóng và mở lại, khai báo lại:

```powershell
$version = "0.1.0-rc.2"
$owner = "TEN_GITHUB_CUA_BAN"
$repository = "ai-subtitle-studio"
```

### Bước 10.1: Build ứng dụng

```powershell
.\scripts\build-release.ps1 -Version $version -Clean
```

Script này:

- Kiểm tra version Python.
- Kiểm tra dependency.
- Chạy test.
- Thu thập Python và dependency bằng PyInstaller.
- Bundle FFmpeg.
- Tạo runtime chạy được mà không cần Python trên máy người dùng.

Nếu FFmpeg không nằm trên `PATH`, chỉ rõ file:

```powershell
.\scripts\build-release.ps1 `
  -Version $version `
  -FfmpegPath "C:\duong-dan-den-ffmpeg\bin\ffmpeg.exe" `
  -Clean
```

### Bước 10.2: Nén runtime thành các volume

```powershell
.\scripts\package-runtime.ps1 -Version $version
```

Script dùng 7-Zip để tạo các file nhỏ hơn giới hạn một asset của GitHub:

```text
AI-Subtitle-Studio-Runtime-vX.Y.Z.7z.001
AI-Subtitle-Studio-Runtime-vX.Y.Z.7z.002
```

### Bước 10.3: Chép SBOM và thông báo bản quyền

```powershell
Copy-Item `
  ".\release-staging\build\SBOM-v$version.json" `
  ".\release\SBOM-v$version.json" `
  -Force

Copy-Item `
  ".\THIRD_PARTY_NOTICES.md" `
  ".\release\THIRD-PARTY-NOTICES-v$version.txt" `
  -Force
```

SBOM là danh sách thành phần phần mềm. Third-party notices ghi nhận giấy phép
của các thư viện như FFmpeg và 7-Zip.

### Bước 10.4: Build online installer

Đối với bản RC chưa ký:

```powershell
.\scripts\build-installer.ps1 `
  -Version $version `
  -Owner $owner `
  -Repository $repository `
  -Channel prerelease
```

Lệnh này dùng Inno Setup để tạo:

```text
release\AI-Subtitle-Studio-Setup-vX.Y.Z.exe
```

Owner, repository, tag và hash của runtime được ghi vào Setup. Không được đổi
tên repository sau khi build mà không build lại Setup.

Đối với bản stable, phải có chứng thư ký số và dùng `-Channel stable` cùng
`-CertificatePath` hoặc `-Thumbprint`. Nếu chưa có chứng thư, hãy phát hành
pre-release.

### Bước 10.5: Kiểm tra toàn bộ asset

```powershell
.\scripts\verify-release.ps1 -Version $version
```

Xem danh sách file:

```powershell
Get-ChildItem .\release -File |
  Where-Object Name -Like "*v$version*" |
  Select-Object Name, Length
```

Chỉ tiếp tục nếu `verify-release.ps1` thành công.

Thư mục `release/` có thể giữ asset của nhiều version. Khi đó, chỉ upload những
file có đúng `v$version` trong tên. Không upload file RC.1 vào Release RC.2.

Thư mục `release/` được `.gitignore` bỏ qua. Đó là điều đúng: các file này sẽ
được upload vào trang Release, không được commit.

---

## 11. Tạo và push tag

Tag phải đánh dấu đúng commit đã dùng để build bộ cài.

Kiểm tra lần cuối:

```powershell
git status --short
git log -1 --oneline
```

Nếu version chưa có tag:

```powershell
git tag -a "v$version" -m "AI Subtitle Studio v$version"
git push origin "v$version"
```

Ví dụ tag thực tế:

```text
v0.1.0-rc.2
```

### Nếu Git báo tag đã tồn tại

Không tạo lại và không vội xóa tag. Xem tag đang trỏ tới đâu:

```powershell
git show --no-patch "v$version"
git rev-parse HEAD
git rev-list -n 1 "v$version"
```

Hai lệnh cuối phải trả về cùng mã commit nếu tag thuộc đúng phiên bản hiện tại.

Nếu tag đã được công bố nhưng trỏ sai, cách an toàn là tăng version, ví dụ từ:

```text
0.1.0-rc.2
```

thành:

```text
0.1.0-rc.3
```

Sau đó commit, build và tạo tag mới. Không tái sử dụng một tag đã phát hành vì
người dùng có thể tải nhầm asset cũ và gặp lỗi hash.

---

## 12. Tạo GitHub Release bằng trình duyệt

1. Mở trang repository trên GitHub.
2. Ở bên phải danh sách file, bấm **Releases**.
3. Bấm **Draft a new release**.
4. Bấm **Choose a tag**.
5. Chọn tag `v0.1.0-rc.2`, hoặc tag đúng với `$version`.
6. Nhập tiêu đề:

   ```text
   AI Subtitle Studio v0.1.0-rc.2
   ```

7. Trong phần mô tả, có thể viết:

   ```markdown
   ## Có gì trong phiên bản này?

   - Bản thử nghiệm đầu tiên dành cho Windows 10/11 x64.
   - Người dùng chỉ cần tải file Setup EXE.
   - Setup sẽ tự tải Python runtime, dependency và FFmpeg.

   ## Cách cài

   1. Tải AI-Subtitle-Studio-Setup-v0.1.0-rc.2.exe.
   2. Mở file vừa tải.
   3. Làm theo hướng dẫn trên màn hình.

   ## Lưu ý

   - Cần Internet trong lúc cài đặt.
   - Đây là pre-release và có thể còn lỗi.
   - Installer chưa ký có thể hiện cảnh báo Windows SmartScreen.
   ```

8. Với version có `rc`, `alpha` hoặc `beta`, chọn **Set as a pre-release**.
9. Không chọn nó là bản latest ổn định.
10. Kéo **toàn bộ file của đúng version hiện tại** vào khu vực upload asset.
    Ví dụ với RC.2, chỉ chọn các file có `v0.1.0-rc.2` trong tên; không kéo các
    file RC.1 đang được giữ lại trong cùng thư mục.
11. Chờ đến khi tất cả thanh upload hoàn thành.
12. Kiểm tra không có file nào từ 2 GiB trở lên.
13. Bấm **Save draft** trước để kiểm tra.

Trong draft phải thấy:

- Setup EXE.
- Tất cả runtime volume, từ `.001` đến volume cuối.
- Manifest.
- SHA256SUMS.
- SBOM.
- Third-party notices.

Khi đã đủ file, bấm **Publish release**.

Lưu ý: online installer chỉ tải được asset sau khi Release đã được publish và
người dùng có quyền đọc repository. Setup sẽ không tải được asset chỉ nằm trong
draft.

---

## 13. Kiểm tra Release sau khi publish

### Kiểm tra đơn giản giống người dùng

1. Mở trang Release bằng cửa sổ trình duyệt ẩn danh.
2. Nếu cửa sổ ẩn danh không xem được Release, repository có thể đang private.
3. Chỉ tải file Setup EXE.
4. Chạy Setup trên máy test hoặc máy ảo Windows sạch.
5. Kiểm tra Setup tự tải runtime.
6. Mở ứng dụng từ shortcut.

Máy test nên không có sẵn:

- Python.
- FFmpeg.
- 7-Zip.
- Inno Setup.

Nếu ứng dụng vẫn chạy, bộ cài đã thực hiện đúng nhiệm vụ.

### Kiểm tra kỹ toàn bộ asset

Tải tất cả asset bằng trình duyệt vào một thư mục riêng, ví dụ:

```text
C:\Temp\ai-subtitle-studio-v0.1.0-rc.2
```

Sau đó chạy:

```powershell
.\scripts\verify-release.ps1 `
  -Version $version `
  -ReleaseDirectory "C:\Temp\ai-subtitle-studio-v0.1.0-rc.2"
```

Script kiểm tra:

- Tên và số lượng file.
- Kích thước.
- SHA-256.
- Manifest.
- Thứ tự runtime volume.
- Chữ ký số đối với stable release.

---

## 14. Kiểm thử ứng dụng trước khi chia sẻ rộng rãi

Với pre-release, tối thiểu cần kiểm tra:

- Cài trên Windows 10/11 x64 sạch.
- Cài khi máy không có Python.
- Thử ngắt mạng trong lúc tải rồi chạy lại.
- Xác nhận volume sai hash bị từ chối.
- Chạy ít nhất hai video thật.
- Kiểm tra queue, cancel và retry.
- Kiểm tra GPU NVIDIA trên máy tương thích.
- Kiểm tra Google Translation và DeepSeek bằng credential test riêng.
- Kiểm tra xuất subtitle.
- Gỡ cài đặt rồi cài lại.
- Kiểm tra installer chưa ký có cảnh báo SmartScreen hay không.

Chỉ đánh dấu stable/latest khi mọi stable gate trong
`specs/001-desktop-subtitle-studio/plan.md` đã đạt.

---

## 15. Những lần phát hành sau

Lần đầu tiên phải tạo repository và thêm remote. Những lần sau không làm lại hai
bước đó.

Quy trình cho version mới:

1. Sửa version trong các file cấu hình.
2. Cập nhật `CHANGELOG.md`.
3. Chạy test.
4. Commit mã nguồn.
5. Push nhánh `main`.
6. Build lại runtime và Setup bằng đúng owner/repository.
7. Xác minh thư mục `release/`.
8. Tạo tag mới.
9. Push tag mới.
10. Tạo GitHub Release mới.
11. Upload toàn bộ asset.
12. Publish và kiểm tra trên máy sạch.

Không trộn asset của hai version. Không lấy Setup của `rc.1` ghép với runtime
của `rc.2`.

---

## 16. Lỗi thường gặp và cách xử lý

### `remote origin already exists`

Remote đã được tạo trước đó. Kiểm tra:

```powershell
git remote -v
```

Nếu URL sai:

```powershell
git remote set-url origin https://github.com/TEN_GITHUB_CUA_BAN/ai-subtitle-studio.git
```

### `Repository not found`

Kiểm tra:

- Username và tên repository có đúng không.
- Tài khoản Git đang dùng có quyền với repository không.
- Repository private có yêu cầu đăng nhập lại không.

### Git hỏi password nhưng mật khẩu GitHub không hoạt động

GitHub không dùng mật khẩu tài khoản cho Git qua HTTPS. Dùng Git Credential
Manager hoặc Personal Access Token. Không dán token vào mã nguồn hoặc ảnh chụp
màn hình.

### Push bị từ chối ngay lần đầu

Nguyên nhân thường gặp là đã chọn tạo README trên GitHub. Repository web khi đó
đã có commit riêng. Cách đơn giản nhất khi repository vừa tạo và chưa có dữ liệu
quan trọng là tạo lại một repository trống, không chọn README, `.gitignore` hoặc
license.

Không dùng `git push --force` khi chưa hiểu rõ hậu quả.

### Setup báo lỗi 404 khi tải runtime

Kiểm tra:

- Release đã publish chưa hay vẫn là draft.
- Repository có đang private không.
- Owner và repository lúc build Setup có đúng không.
- Tag có đúng không.
- Tất cả runtime volume đã được upload chưa.
- Tên asset có bị GitHub hoặc người upload đổi không.

Nếu owner hoặc repository sai, build lại Setup. Không thể sửa URL bên trong file
EXE bằng cách đổi tên file.

### Setup báo hash không đúng

Các file có thể đến từ hai lần build khác nhau. Xóa bộ asset local bị trộn, build
lại toàn bộ cùng một version và xác minh trước khi upload.

Không thay một runtime volume mới vào Release cũ mà giữ nguyên manifest.

### GitHub không cho upload file lớn

Mỗi release asset phải nhỏ hơn 2 GiB. `package-runtime.ps1` mặc định chia runtime
thành volume khoảng 1.8 GiB. Nếu vẫn có file quá lớn, kiểm tra lại script và danh
sách file trong `release/`.

### Windows hiện cảnh báo SmartScreen

Installer chưa ký số thường có thể bị cảnh báo. Với RC, ghi rõ đây là bản thử
nghiệm. Trước khi phát hành stable, dùng chứng thư Authenticode và kiểm tra chữ
ký.

---

## 17. Checklist ngắn trước khi bấm Publish

Đọc từng dòng và đánh dấu:

- [ ] Repository đúng owner và đúng tên.
- [ ] Repository public nếu dành cho người dùng phổ thông.
- [ ] Không có API key, credential, video, database hoặc chứng thư trong Git.
- [ ] Test đều pass.
- [ ] `verify-repository.ps1` pass.
- [ ] Nhánh `main` đã push.
- [ ] Tag đúng version và đúng commit.
- [ ] Setup được build bằng đúng owner/repository/tag.
- [ ] `verify-release.ps1` pass.
- [ ] Đã upload Setup EXE.
- [ ] Đã upload đủ tất cả runtime volume.
- [ ] Đã upload manifest, SHA256SUMS, SBOM và notices.
- [ ] Mỗi asset nhỏ hơn 2 GiB.
- [ ] RC đã được đánh dấu pre-release.
- [ ] Đã thử chỉ tải Setup trên máy Windows sạch.

Nếu tất cả ô đều được đánh dấu, Release đã sẵn sàng để chia sẻ.

---

## 18. Tài liệu chính thức để đối chiếu

- Tạo và quản lý GitHub Release:
  <https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository>
- Giải thích GitHub Release:
  <https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases>
- Xác thực GitHub:
  <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github>
- Personal Access Token:
  <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens>
- Inno Setup tải file và kiểm tra SHA-256:
  <https://jrsoftware.org/ishelp/topic_isxfunc_downloadtemporaryfile.htm>
