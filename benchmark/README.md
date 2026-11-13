# Benchmark Design & Pre-Experiment Specification — Day 06

Tài liệu này mô tả thiết kế bộ câu hỏi benchmark ([benchmark/questions.json](questions.json)), quy trình kiểm chứng bằng chứng (`evidence_quote`) trên văn bản đã chuẩn hóa, phân tích nguy cơ rò rỉ dữ liệu (*data leakage*) và **tiêu chí chọn chiến lược được khóa trước khi chạy thử nghiệm**.

---

## 1. Cấu trúc bộ câu hỏi & Phân chia `dev` / `test`

- **Tổng số câu hỏi:** **20 câu** (viết và xác minh hoàn toàn trước khi chạy bất kỳ cấu hình chunking/retrieval nào).
  - **Tập `dev`:** **15 câu** (`q01` – `q15`) — dùng để kiểm tra pipeline, phân tích lỗi và chọn chiến lược tốt nhất.
  - **Tập `test` (Holdout):** **5 câu** (`q16` – `q20`) — khóa cố định, chỉ dùng để đánh giá sau khi đã chốt chiến lược trên `dev` và thực hiện chấm thủ công 5 câu test (Grounding Quality & Metadata Usefulness).
- **Phân bố theo tài liệu nguồn:**
  - `nist-ai-rmf-1.0` (NIST AI RMF 1.0, 2023): **12 câu** (9 câu `dev`, 3 câu `test`).
  - `nist-csf-2.0` (NIST CSF 2.0, 2024): **8 câu** (6 câu `dev`, 2 câu `test`).
- **Phân bố theo loại câu hỏi (`type`):**
  - **Trực tiếp (`direct`):** **6 câu** (`q01`, `q02`, `q06`, `q08`, `q10`, `q17`) — hỏi trực tiếp khái niệm, cấu trúc Core, tiểu mục.
  - **Diễn đạt lại (`paraphrase`):** **4 câu** (`q03`, `q05`, `q09`, `q18`) — dùng từ vựng/cách đặt vấn đề khác câu chữ gốc để kiểm tra khả năng khớp ngữ nghĩa (semantic similarity).
  - **Điều kiện / Ngoại lệ / Đánh đổi (`conditional_exception`):** **4 câu** (`q04`, `q07`, `q11`, `q16`) — hỏi về điều kiện dừng hệ thống AI nguy hiểm, yêu cầu độc lập của nhóm TEVV, lý do đánh số nhảy cóc trong CSF 2.0, và sự khác biệt giữa tính chống chịu (resilience) với bảo mật (security) khi hệ thống suy giảm chức năng.
  - **Kiểm tra Metadata Filter (`metadata_filter`):** **6 câu** (**4 câu `dev`**: `q12`, `q13`, `q14`, `q15`; **2 câu `test`**: `q19`, `q20` — vượt mức tối thiểu $\ge 3$ câu filter và $\ge 1$ câu filter thuộc `test`).

---

## 2. Thiết kế câu hỏi Metadata Filter & Chống gian lận (Anti-Cheating)

Hai tài liệu trong corpus (`NIST AI RMF 1.0` năm 2023 và `NIST CSF 2.0` năm 2024) đều là khung quản trị rủi ro của NIST và **cùng sử dụng các thuật ngữ cốt lõi giống nhau**: hàm `GOVERN`, `Supply Chain Risk Management`, `Current Profile` vs. `Target Profile`, `Decommissioning / Recovery`, và `Access / Policy controls`.
- Do đó, khi truy vấn không có filter (Chiến lược A và B), các chunk từ hai tài liệu hoặc các chương khác nhau dễ cạnh tranh điểm tương đồng cosine.
- Trong 6 câu `metadata_filter` (`q12`–`q15`, `q19`–`q20`), trường `filter` chỉ sử dụng các metadata nghiệp vụ được giả định cung cấp trước từ ngữ cảnh người dùng:
  - `domain`: `"ai_risk"` hoặc `"cybersecurity"`
  - `year`: `2023` hoặc `2024`
  - `section`: `"part_2_core_and_profiles"` hoặc `"appendix_a_csf_core"`
- **Cam kết chống rò rỉ nhãn đích:** Không có bất kỳ câu hỏi nào đưa `gold_source_id`, `gold_page` hay câu trả lời (`expected_answer`) vào `question` hoặc `filter`. Với 14 câu hỏi có `"filter": null`, Chiến lược C sẽ chạy truy xuất **không áp dụng filter** và ghi rõ trong trace.

---

## 3. Phân tích nguy cơ rò rỉ (`dev` vs. `test` Leakage Risk)

1. **Tách biệt hoàn toàn trang nguồn đích (`0` page overlap):**
   - Tập `dev` lấy bằng chứng từ 15 trang: `nist-ai-rmf-1.0` (P.6, 11, 13, 17, 22, 23, 29, 34, 38) và `nist-csf-2.0` (P.8, 12, 14, 20, 23, 25).
   - Tập `test` lấy bằng chứng từ 5 trang hoàn toàn khác: `nist-ai-rmf-1.0` (P.20, 28, 30, 44) và `nist-csf-2.0` (P.28).
   - Giao giữa tập trang đích chính của `dev` và `test` bằng **0 trang**, đảm bảo việc chọn tham số trên `dev` không khớp lặp lại chính đoạn văn bản của `test`.
2. **Nguy cơ rò rỉ còn tồn tại (Residual Leakage Risk):**
   - Cả `dev` và `test` đều thuộc cùng 2 tài liệu PDF của NIST nên có chung phong cách trình bày (cấu trúc tiểu mục `GOVERN X.Y`, `GV.SC-XX`, `RC.RP-XX`, bảng biểu và đoạn văn nghị luận kỹ thuật).
   - Do tập `test` chỉ có 5 câu hỏi (mẫu nhỏ, mỗi câu tương ứng $20\%$), kết quả trên `test` chỉ đóng vai trò kiểm tra minh họa holdout chứ không dùng để khẳng định tính tổng quát cho mọi bộ dữ liệu bên ngoài.

---

## 4. Xác minh Evidence & Đa nguồn hợp lệ (`alternative_gold`)

- Toàn bộ 20 câu hỏi đã được kiểm chứng tự động bằng script [starter/scripts/verify_benchmark.py](../starter/scripts/verify_benchmark.py) (kết quả lưu tại [starter/results/benchmark_verification_report.json](../starter/results/benchmark_verification_report.json)):
  - **20/20 `evidence_quote` chính** và **8/8 `alternative_gold` quotes** đều khớp chính xác (exact substring) trong văn bản đã chuẩn hóa Unicode (`normalize_text`) tại đúng trang `gold_page`.
  - Với các câu hỏi mà khái niệm xuất hiện ở cả phần tổng quan lẫn phần chi tiết/phụ lục (như `q02`, `q07`, `q08`, `q09`, `q10`, `q18`), cả trang chính và các trang thay thế hợp lệ đều được ghi nhận trong `alternative_gold` để không chấm sai khi mô hình truy xuất được nguồn hợp lệ tương đương.

---

## 5. Tiêu chí chọn chiến lược cố định trước khi xem Test (Pre-Registered Selection Rule)

Trước khi chạy pipeline và trước khi xem kết quả trên tập `test`, quy tắc chọn chiến lược tốt nhất giữa **A (Fixed-size chunking, no filter)**, **B (Paragraph/structure-aware chunking, no filter)** và **C (Paragraph/structure-aware chunking + Metadata filter)** được khóa cố định theo thứ tự ưu tiên từ cao xuống thấp như sau:

1. **Tiêu chí 1 (Ưu tiên cao nhất):** **Evidence Hit@3 trên tập `dev` (15 câu)** cao hơn.
2. **Tiêu chí 2 (Phá hòa 1):** **Hit@1 trên tập `dev` (15 câu)** cao hơn.
3. **Tiêu chí 3 (Phá hòa 2):** **Điểm mạch lạc của Chunk (Chunk Coherence trung bình `/2` trên 10 vị trí nguồn cố định)** và **Tỷ lệ tuân thủ Metadata Filter** trên các câu có filter cao hơn.
4. **Tiêu chí 4 (Phá hòa 3):** Hiệu quả tài nguyên (số lượng chunk hợp lý, thời gian ingest/truy xuất nhanh và chi phí thấp).

