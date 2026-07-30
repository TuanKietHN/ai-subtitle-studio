# Feature Specification: Desktop Subtitle Studio

**Feature Branch**: `001-desktop-subtitle-studio`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Xây dựng ứng dụng desktop Windows cho người dùng cá nhân có GPU NVIDIA tạo phụ đề tiếng Anh từ video bài giảng, dịch sang tiếng Việt, chỉnh sửa, quản lý model, xử lý hàng đợi tuần tự và mở kết quả bằng Subtitle Edit."

## Clarifications

### Session 2026-07-08

- Q: Ứng dụng nên xử lý thế nào khi không phát hiện GPU NVIDIA/CUDA hợp lệ? → A: STT yêu cầu GPU NVIDIA/CUDA; nếu không có GPU hợp lệ thì job STT lỗi rõ ràng, các phần không cần STT vẫn dùng được.
- Q: SRT nên biểu diễn word-level timestamp như thế nào trong file xuất? → A: Xuất cue theo câu/cụm đọc được; dùng word-level alignment để tinh chỉnh timestamp bắt đầu/kết thúc của cue.
- Q: API key dịch nên được lưu an toàn như thế nào? → A: Lưu API key bằng Windows Credential Manager hoặc kho bí mật hệ điều hành tương đương.
- Q: Khi đóng và mở lại ứng dụng, hàng đợi xử lý nên được khôi phục thế nào? → A: Persist hàng đợi, cấu hình job và kết quả đã có; job đang chạy khi app đóng được đánh dấu cần chạy lại.
- Q: Khi người dùng tạm dừng job chưa chạy hoặc job đang chạy thì ứng dụng phải phản hồi thế nào? → A: Job chưa chạy tạm dừng ngay; job đang chạy hiển thị trạng thái chờ checkpoint an toàn cho đến khi bước hiện tại kết thúc.


## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tạo phụ đề tiếng Anh từ hàng đợi video (Priority: P1)

Người dùng không rành dòng lệnh chọn hoặc kéo-thả một hoặc nhiều file `.mp4`, đưa chúng vào hàng đợi, chọn model mong muốn, rồi để ứng dụng lần lượt tạo phụ đề tiếng Anh bằng WhisperX và lưu file `.srt` tiếng Anh dùng được ngay.

**Why this priority**: Đây là luồng nền tảng của ứng dụng: biến video bài giảng tiếng Anh thành phụ đề tiếng Anh có timestamp chính xác, là đầu vào bắt buộc cho bước dịch và chỉnh sửa ở US3.

**Independent Test**: Dùng hai video `.mp4` hợp lệ, thêm cả hai vào hàng đợi, chạy xử lý và xác minh từng job lần lượt tạo được file `.srt` tiếng Anh, trạng thái hoàn tất và lỗi riêng từng job mà không cần mở dòng lệnh hoặc dùng chức năng dịch.

**Acceptance Scenarios**:

1. **Given** người dùng có hai video `.mp4` hợp lệ và đã chọn thư mục output, **When** người dùng kéo-thả cả hai video vào ứng dụng và bấm bắt đầu, **Then** cả hai video xuất hiện trong hàng đợi và chỉ một job được xử lý tại một thời điểm.
2. **Given** một job đang chạy với model đã có sẵn, **When** trích audio, nhận dạng và alignment hoàn tất, **Then** ứng dụng tạo file `.srt` tiếng Anh với timestamp đã tinh chỉnh từ WhisperX word-level forced alignment.
3. **Given** một job trong hàng đợi bị lỗi khi trích audio, nhận dạng, alignment hoặc ghi file `.srt` tiếng Anh, **When** lỗi xảy ra, **Then** job đó hiển thị lý do lỗi rõ ràng và các job khác trong hàng đợi vẫn có thể tiếp tục xử lý.

---

### User Story 2 - Chọn, tải và quản lý model nhận dạng (Priority: P1)

Người dùng chọn model Whisper từ dropdown với mặc định là `large-v3`. Nếu model chưa có trên máy, ứng dụng tự tải model và hiển thị tiến trình để người dùng biết còn phải chờ bao lâu.

**Why this priority**: Model quyết định chất lượng và tốc độ nhận dạng. Người dùng mục tiêu cần chọn model mà không phải biết cách tải thủ công.

**Independent Test**: Trên máy chưa có model được chọn, chọn model từ dropdown và xác minh ứng dụng hiển thị tiến trình tải, sau đó model sẵn sàng dùng cho job tiếp theo.

**Acceptance Scenarios**:

1. **Given** danh sách model hỗ trợ có `large-v3`, `medium`, `large-v3-turbo` và `distil-large-v3`, **When** người dùng mở dropdown model lần đầu, **Then** `large-v3` được chọn mặc định và các model hỗ trợ khác hiển thị để chọn.
2. **Given** người dùng chọn một model chưa tải, **When** ứng dụng bắt đầu tải model, **Then** tiến trình tải hiển thị phần trăm, tốc độ tải và dung lượng còn lại.
3. **Given** người dùng mở màn hình quản lý model, **When** model đã tải tồn tại trên máy, **Then** ứng dụng hiển thị tên model, dung lượng và hành động xóa model không dùng.

---

### User Story 3 - Dịch, chỉnh sửa và xuất phụ đề cuối cùng (Priority: P1)

Sau khi có phụ đề tiếng Anh, người dùng chọn Google Translate hoặc DeepSeek, nhập API key riêng cho provider, dịch theo lô, xem bảng dòng phụ đề, sửa nội dung trực tiếp và xuất file cuối cùng gồm tiếng Việt hoặc song ngữ.

**Why this priority**: Người dùng cần bản dịch có thể kiểm tra và sửa trước khi dùng cho video bài giảng.

**Independent Test**: Với một phụ đề gốc đã tạo, chọn provider dịch, nhập API key, dịch toàn bộ phụ đề, sửa một dòng trong bảng và xuất file tiếng Việt cùng file song ngữ.

**Acceptance Scenarios**:

1. **Given** phụ đề tiếng Anh có 100 dòng, **When** người dùng dịch sang tiếng Việt, **Then** phụ đề dịch có đúng 100 dòng, giữ nguyên thứ tự và timestamp gốc.
2. **Given** bảng phụ đề đang hiển thị text gốc và text dịch, **When** người dùng sửa nội dung của một dòng dịch, **Then** thay đổi đó được giữ khi xuất file `.srt` cuối cùng.
3. **Given** người dùng bật tùy chọn xuất song ngữ, **When** xuất file, **Then** mỗi cue phụ đề chứa cả câu tiếng Anh và câu tiếng Việt tương ứng.

---

### User Story 4 - Điều khiển hàng đợi và phục hồi lỗi (Priority: P2)

Người dùng theo dõi nhiều video trong hàng đợi, tạm dừng hoặc hủy từng job riêng lẻ, và hiểu rõ lỗi của từng job mà không làm ứng dụng bị crash.

**Why this priority**: Xử lý bài giảng dài tốn thời gian; người dùng cần kiểm soát hàng đợi và xử lý lỗi theo từng video.

**Independent Test**: Thêm ba video vào hàng đợi, tạm dừng một job chờ xử lý, hủy một job khác, gây lỗi có kiểm soát ở một job và xác minh hàng đợi vẫn hoạt động.

**Acceptance Scenarios**:

1. **Given** nhiều job đang chờ, **When** người dùng tạm dừng một job chưa chạy, **Then** job đó không được xử lý cho đến khi người dùng tiếp tục hoặc hủy.
2. **Given** một job đang chờ hoặc đang chạy, **When** người dùng hủy job, **Then** job chuyển sang trạng thái đã hủy và không xuất file không hoàn chỉnh như kết quả cuối cùng.
3. **Given** một job gặp lỗi dịch do thiếu API key hoặc lỗi provider, **When** lỗi được ghi nhận, **Then** người dùng thấy thông báo đủ rõ để sửa cấu hình và thử lại job đó.

---

### User Story 5 - Cấu hình công cụ, thông tin hệ thống và mở Subtitle Edit (Priority: P2)

Người dùng cấu hình GPU, đường dẫn lưu model, đường dẫn Subtitle Edit, đường dẫn ffmpeg và thư mục output mặc định; sau khi tạo phụ đề có thể mở file bằng Subtitle Edit từ trong ứng dụng.

**Why this priority**: Người dùng mục tiêu dùng Windows desktop và cần cấu hình một lần để xử lý nhiều video mà không thao tác thủ công trong file system hoặc dòng lệnh.

**Independent Test**: Cấu hình các đường dẫn, tạo một file phụ đề, bấm "Mở bằng Subtitle Edit" và xác minh ứng dụng mở đúng file hoặc hiển thị lỗi cấu hình rõ ràng.

**Acceptance Scenarios**:

1. **Given** máy có nhiều GPU được phát hiện, **When** người dùng mở Settings, **Then** người dùng chọn được GPU muốn dùng cho các job tiếp theo.
2. **Given** đường dẫn Subtitle Edit hợp lệ, **When** người dùng bấm "Mở bằng Subtitle Edit" sau khi xuất phụ đề, **Then** file phụ đề vừa tạo được mở bằng ứng dụng đó.
3. **Given** người dùng mở "Thông tin hệ thống / About", **When** màn hình hiển thị, **Then** người dùng thấy phiên bản WhisperX, faster-whisper, CUDA/GPU, model đang chọn, dung lượng model đã tải và phiên bản ứng dụng.

### Edge Cases

- File được chọn không phải `.mp4`, bị hỏng, không đọc được hoặc không có audio.
- Người dùng kéo-thả cùng một video nhiều lần vào hàng đợi.
- Đường dẫn ffmpeg, Subtitle Edit, thư mục model hoặc thư mục output không tồn tại hoặc không có quyền ghi.
- Không phát hiện được GPU NVIDIA, CUDA hoặc driver phù hợp trên máy; các phần không cần STT vẫn dùng được, nhưng mọi job cần STT phải lỗi rõ ràng trước khi transcribe.
- Máy có nhiều GPU nhưng GPU đã chọn không còn khả dụng khi job bắt đầu.
- Model được chọn chưa tải, tải thất bại, bị gián đoạn, thiếu dung lượng đĩa hoặc file model bị lỗi.
- Người dùng hủy job trong lúc tải model, trích audio, nhận dạng hoặc dịch.
- Người dùng tạm dừng job đang chạy trong lúc tải model, trích audio, nhận dạng hoặc dịch; trạng thái phải cho biết đang chờ checkpoint an toàn.
- Provider dịch thiếu API key, API key sai, hết hạn mức, timeout hoặc trả về số dòng khác số dòng đầu vào.
- Dòng phụ đề quá dài, rỗng sau khi dịch hoặc chứa ký tự xuống dòng cần xuất đúng định dạng SRT.
- File output đã tồn tại trong thư mục đích.
- Subtitle Edit chưa cài, đường dẫn cấu hình sai hoặc file phụ đề chưa được tạo.
- Ứng dụng bị đóng khi còn job đang chờ hoặc đang xử lý.

## Requirements *(mandatory)*

### Constitution Impact *(mandatory for AI Subtitle Studio)*

Feature này chạm đến STT, translation, model selection, System Info, worker processing và GPU scheduling. Các ràng buộc constitution sau là bắt buộc trong phạm vi feature:

- **CI-001**: STT MUST dùng WhisperX và MUST NOT giới thiệu `whisper.cpp` hoặc OpenAI Whisper gốc.
- **CI-002**: Transcription MUST luôn dùng Pyannote VAD qua `vad_method="pyannote"` như một invariant không cấu hình được; người dùng không nhìn thấy, tắt hoặc thay đổi được tùy chọn này.
- **CI-003**: Model mặc định MUST là `large-v3`; danh sách model khả dụng MUST đến từ cấu hình hỗ trợ model, không hard-code trong logic giao diện.
- **CI-004**: System Info MUST hiển thị version thực tế của WhisperX, `faster-whisper`, CUDA/GPU driver, model đang chọn và app version tại runtime.
- **CI-005**: STT engine và Translation provider MUST được tách qua provider contracts để có thể thêm provider mới mà không thay đổi luồng nghiệp vụ cốt lõi.
- **CI-006**: Các tác vụ dài như trích audio, nhận dạng, alignment, tải model và dịch MUST không làm đứng giao diện.
- **CI-007**: GPU STT MUST chỉ xử lý một video tại một thời điểm; hàng đợi video MUST chạy tuần tự cho STT.

### Functional Requirements

- **FR-001**: Người dùng MUST có thể chọn một hoặc nhiều file `.mp4` bằng file picker.
- **FR-002**: Người dùng MUST có thể kéo-thả một hoặc nhiều file `.mp4` vào giao diện để thêm vào hàng đợi.
- **FR-003**: Hệ thống MUST từ chối hoặc đánh dấu không hợp lệ các file không phải `.mp4` trước khi xử lý.
- **FR-004**: Hệ thống MUST hiển thị hàng đợi gồm từng video, trạng thái job, tiến trình hiện tại và lỗi nếu có.
- **FR-005**: Hệ thống MUST xử lý các video trong hàng đợi theo thứ tự tuần tự, không xử lý song song nhiều job STT.
- **FR-006**: Người dùng MUST có thể tạm dừng, tiếp tục hoặc hủy từng job riêng lẻ trong hàng đợi; job chưa chạy phải tạm dừng ngay, còn job đang chạy phải tạm dừng tại checkpoint an toàn sau bước hiện tại.
- **FR-007**: Job bị hủy MUST không được báo là hoàn tất và MUST không ghi đè kết quả cuối cùng hợp lệ trước đó.
- **FR-008**: Hệ thống MUST trích audio từ video bằng đường dẫn công cụ đã cấu hình và báo lỗi rõ ràng nếu công cụ không khả dụng.
- **FR-009**: Hệ thống MUST dùng WhisperX để nhận dạng giọng nói từ audio đã trích.
- **FR-010**: Hệ thống MUST tạo phụ đề `.srt` gốc tiếng Anh thành các cue theo câu hoặc cụm dễ đọc, với timestamp bắt đầu/kết thúc của cue được tinh chỉnh bằng word-level forced alignment của WhisperX.
- **FR-011**: VAD MUST luôn bật ngầm khi transcribe và MUST không xuất hiện như tùy chọn trong UI, Settings hoặc file cấu hình người dùng.
- **FR-012**: Dropdown model MUST chọn `large-v3` mặc định khi người dùng chưa chọn model khác.
- **FR-013**: Dropdown model MUST hiển thị các model được hỗ trợ, bao gồm tối thiểu `medium`, `large-v3`, `large-v3-turbo` và `distil-large-v3` khi chúng có trong danh sách hỗ trợ.
- **FR-014**: Nếu model được chọn chưa có trên máy, hệ thống MUST tự động tải model trước khi job cần model đó chạy.
- **FR-015**: Khi tải model, hệ thống MUST hiển thị phần trăm, tốc độ tải và dung lượng còn lại.
- **FR-016**: Người dùng MUST có thể xem danh sách model đã tải, dung lượng từng model và trạng thái sẵn sàng dùng.
- **FR-017**: Người dùng MUST có thể xóa model đã tải nếu model đó không đang được dùng bởi job đang chạy.
- **FR-018**: Người dùng MUST có thể tải thêm model từ danh sách model hỗ trợ trong màn hình quản lý model.
- **FR-019**: Người dùng MUST có thể chọn provider dịch là Google Translate hoặc DeepSeek.
- **FR-020**: Người dùng MUST có thể nhập và lưu API key riêng cho từng translation provider bằng Windows Credential Manager hoặc kho bí mật hệ điều hành tương đương.
- **FR-021**: API key MUST được che trong giao diện sau khi nhập, MUST không được lưu plaintext trong file cấu hình cục bộ, và MUST không xuất hiện trong file phụ đề, log hoặc thông báo lỗi thông thường.
- **FR-022**: Hệ thống MUST dịch phụ đề theo batch nhiều dòng một lần để giảm thao tác chờ của người dùng.
- **FR-023**: Bản dịch MUST giữ nguyên số dòng, thứ tự dòng và timestamp của phụ đề gốc.
- **FR-024**: Nếu provider dịch trả về số dòng không khớp hoặc thiếu nội dung, hệ thống MUST báo lỗi cho job và không xuất bản dịch sai lệch như kết quả cuối cùng.
- **FR-025**: Hệ thống MUST xuất file `.srt` tiếng Việt sau khi dịch thành công.
- **FR-026**: Người dùng MUST có tùy chọn xuất thêm file `.srt` song ngữ với mỗi cue chứa cả câu tiếng Anh và câu tiếng Việt tương ứng.
- **FR-027**: Hệ thống MUST hiển thị bảng dòng phụ đề gồm số thứ tự, timestamp, text gốc và text dịch.
- **FR-028**: Người dùng MUST có thể sửa trực tiếp text gốc và text dịch trong bảng trước khi xuất file cuối cùng.
- **FR-029**: Các chỉnh sửa trong bảng MUST được dùng khi xuất lại file `.srt`.
- **FR-030**: Hệ thống MUST cảnh báo khi chỉnh sửa làm dòng phụ đề rỗng hoặc có định dạng không thể xuất hợp lệ.
- **FR-031**: Người dùng MUST có thể chọn thư mục output mặc định trong Settings.
- **FR-032**: Hệ thống MUST lưu output của mỗi video theo tên dễ liên hệ với video nguồn; nếu tên file output đã tồn tại, hệ thống MUST tự động tạo tên duy nhất bằng hậu tố như `(1)`, `(2)` và MUST chỉ ghi đè khi người dùng chủ động chọn ghi đè trong giao diện.
- **FR-033**: Người dùng MUST có thể cấu hình đường dẫn Subtitle Edit executable trong Settings.
- **FR-034**: Sau khi có file phụ đề, người dùng MUST có thể mở file đó bằng Subtitle Edit từ trong ứng dụng.
- **FR-035**: Nếu Subtitle Edit chưa cấu hình đúng, hệ thống MUST hiển thị lỗi cấu hình rõ ràng và không crash.
- **FR-036**: Màn hình "Thông tin hệ thống / About" MUST hiển thị version WhisperX đang dùng, version `faster-whisper`, CUDA/GPU phát hiện được, model đang chọn, dung lượng các model đã tải và phiên bản ứng dụng hiện tại.
- **FR-037**: Settings MUST cho phép chọn GPU khi máy có nhiều GPU được phát hiện.
- **FR-038**: Settings MUST cho phép cấu hình đường dẫn lưu model, đường dẫn ffmpeg, đường dẫn Subtitle Edit và thư mục output mặc định.
- **FR-039**: Hệ thống MUST hiển thị lỗi theo từng job khi lỗi xảy ra ở bước trích audio, nhận dạng hoặc dịch.
- **FR-040**: Lỗi của một job MUST không làm crash ứng dụng và MUST không làm mất trạng thái của các job khác trong hàng đợi.
- **FR-041**: Người dùng MUST có thể thử lại một job lỗi sau khi sửa nguyên nhân cấu hình hoặc provider.
- **FR-042**: Giao diện MUST tiếp tục phản hồi thao tác xem tiến trình, tạm dừng, hủy và mở Settings trong khi job dài đang chạy.
- **FR-043**: Ứng dụng MUST phục vụ người dùng cá nhân trên Windows và không yêu cầu người dùng thao tác dòng lệnh cho luồng chính.
- **FR-044**: Nếu không phát hiện GPU NVIDIA/CUDA hợp lệ, hệ thống MUST giữ các khu vực không cần STT vẫn sử dụng được và MUST đánh dấu job cần STT là lỗi cấu hình rõ ràng trước khi transcribe.
- **FR-045**: Hệ thống MUST không xuất một cue SRT riêng cho từng từ trong luồng mặc định; cue phải đủ dễ đọc để người dùng sửa và dùng trực tiếp trong video bài giảng.
- **FR-046**: Hệ thống MUST khôi phục hàng đợi, cấu hình từng job và các kết quả đã tạo sau khi đóng rồi mở lại ứng dụng.
- **FR-047**: Nếu ứng dụng đóng khi job đang chạy, job đó MUST được khôi phục ở trạng thái cần chạy lại và MUST không được đánh dấu thành công dựa trên kết quả chưa hoàn tất.
- **FR-048**: Hệ thống MUST hiển thị rõ khi yêu cầu tạm dừng job đang chạy đang chờ checkpoint an toàn, thay vì báo rằng job đã tạm dừng ngay lập tức.

### Key Entities *(include if feature involves data)*

- **Video Job**: Một video trong hàng đợi xử lý; có file nguồn, trạng thái, tiến trình, model chọn, provider dịch, lỗi hiện tại, trạng thái cần chạy lại sau khi gián đoạn và các file output liên quan.
- **Subtitle Line**: Một cue phụ đề theo câu hoặc cụm dễ đọc; có số thứ tự, timestamp bắt đầu/kết thúc được tinh chỉnh từ word-level alignment, text gốc, text dịch và trạng thái chỉnh sửa.
- **Whisper Model**: Một model nhận dạng được hỗ trợ hoặc đã tải; có id, tên hiển thị, trạng thái tải, dung lượng và vị trí lưu.
- **Model Download**: Một lần tải model; có model liên quan, phần trăm, tốc độ, dung lượng còn lại, trạng thái hoàn tất hoặc lỗi.
- **Translation Provider**: Provider dịch người dùng chọn; có tên provider, trạng thái API key trong kho bí mật hệ điều hành và trạng thái khả dụng.
- **App Settings**: Cấu hình chung gồm GPU được chọn, thư mục model, đường dẫn ffmpeg, đường dẫn Subtitle Edit và thư mục output mặc định.
- **System Info Snapshot**: Thông tin runtime hiển thị trong About gồm version dependency, GPU/CUDA, model đang chọn, dung lượng model và app version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% người dùng mục tiêu có thể thêm ít nhất hai video vào hàng đợi và bắt đầu xử lý trong dưới 2 phút mà không dùng dòng lệnh.
- **SC-002**: Với hàng đợi 10 video hợp lệ, hệ thống xử lý tuần tự và không có thời điểm nào nhiều hơn một video đang ở bước STT trên GPU.
- **SC-003**: 100% file `.srt` tiếng Việt xuất thành công trong bộ kiểm thử giữ nguyên số cue, thứ tự cue và timestamp của file tiếng Anh tương ứng.
- **SC-004**: 95% thao tác tải model hiển thị tiến trình phần trăm, tốc độ và dung lượng còn lại trong vòng 5 giây sau khi bắt đầu tải.
- **SC-005**: Trong lúc xử lý một video dài, giao diện phản hồi thao tác tạm dừng hoặc hủy trong vòng 2 giây ở ít nhất 95% lần thử hợp lệ.
- **SC-006**: 95% lỗi có chủ đích ở trích audio, nhận dạng hoặc dịch được hiển thị trên đúng job và không làm mất trạng thái các job khác.
- **SC-007**: 90% người dùng kiểm thử có thể sửa một dòng phụ đề, xuất lại file và mở bằng Subtitle Edit mà không cần hướng dẫn ngoài giao diện.
- **SC-008**: Màn hình System Info hiển thị đầy đủ các trường bắt buộc trong vòng 5 giây sau khi mở trên máy có cấu hình hợp lệ.
- **SC-009**: Trên máy không có GPU NVIDIA/CUDA hợp lệ, 100% job cần STT dừng với lỗi cấu hình rõ ràng trước khi transcribe và ứng dụng vẫn cho phép mở Settings, About, quản lý model và bảng phụ đề.
- **SC-010**: Trong kiểm thử với video bài giảng mẫu, 95% cue tiếng Anh xuất ra là câu hoặc cụm có thể đọc và sửa trực tiếp, không phải cue một từ mặc định.
- **SC-011**: 100% kiểm tra bảo mật cấu hình xác nhận API key không xuất hiện plaintext trong file cấu hình, file phụ đề, log hoặc thông báo lỗi thông thường.
- **SC-012**: Sau khi đóng ứng dụng giữa lúc xử lý và mở lại, 100% hàng đợi, cấu hình job và kết quả đã hoàn tất được khôi phục; job đang chạy trước đó hiển thị là cần chạy lại.
- **SC-013**: 100% yêu cầu tạm dừng job chưa chạy có hiệu lực ngay; 100% yêu cầu tạm dừng job đang chạy hiển thị trạng thái chờ checkpoint an toàn cho đến khi bước hiện tại kết thúc.

## Assumptions

- Phiên bản đầu tiên chỉ nhận đầu vào video `.mp4`; các định dạng khác nằm ngoài phạm vi feature này.
- Ngôn ngữ nói chính trong video là tiếng Anh và ngôn ngữ dịch đích mặc định là tiếng Việt.
- Người dùng tự chịu trách nhiệm có quyền dùng video đầu vào và API key dịch của họ.
- API key được lưu trong kho bí mật của người dùng Windows hiện tại và không được đồng bộ ra dịch vụ bên ngoài của ứng dụng.
- Nếu file output đã tồn tại, ứng dụng mặc định tự động tạo tên duy nhất bằng hậu tố như `(1)`, `(2)` và không ghi đè tự động; ghi đè chỉ xảy ra khi người dùng chủ động chọn ghi đè trong giao diện.
- Nếu ứng dụng đóng khi còn job đang chạy, hàng đợi và cấu hình job được khôi phục; job chưa hoàn tất sẽ ở trạng thái cần chạy lại sau khi mở ứng dụng.
- Subtitle Edit là công cụ tùy chọn; không cấu hình Subtitle Edit không được chặn việc tạo hoặc xuất phụ đề.
