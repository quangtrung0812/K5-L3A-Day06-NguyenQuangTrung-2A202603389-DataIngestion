# Báo cáo cá nhân — Day 6 · Data Ingestion Engineering

- **Họ và tên:** Nguyễn Quang Trung
- **MSSV:** `2A202603389`
- **Lớp:** `L3A`
- **Ngày thực hiện:** `2026-11-13`

---

## Dữ liệu và pipeline

### 1. Chủ đề, nguồn/quyền, số trang và quy tắc tính trang
- **Chủ đề:** Quản trị và Quản lý Rủi ro Công nghệ Doanh nghiệp (*Enterprise Technology Governance & Risk Management Frameworks*).
- **Tài liệu nguồn (2 văn bản tiêu chuẩn chính thức của NIST):**
  1. **`nist-ai-rmf-1.0`** ([starter/data/NIST.AI.100-1.pdf](../../starter/data/NIST.AI.100-1.pdf)): *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, mã xuất bản `NIST AI 100-1`, ban hành tháng `01/2023` (URL gốc: `https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf`, DOI: `https://doi.org/10.6028/NIST.AI.100-1`).
  2. **`nist-csf-2.0`** ([starter/data/NIST.CSWP.29.pdf](../../starter/data/NIST.CSWP.29.pdf)): *The NIST Cybersecurity Framework (CSF) 2.0*, mã xuất bản `NIST CSWP 29`, ban hành ngày `26/02/2024` (URL gốc: `https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf`, DOI: `https://doi.org/10.6028/NIST.CSWP.29`).
- **Giấy phép và quyền sử dụng (`license_or_permission`):** **Public Domain** — Tác phẩm của Chính phủ Hoa Kỳ theo `17 U.S.C. § 105` (*"This publication is available free of charge..."*). Được phép lưu trữ, tái phân phối trong repository và gửi qua API nhúng mà không vi phạm bản quyền; không chứa thông tin cá nhân (PII) hay dữ liệu mật.
- **Số trang và quy tắc tính trang ([data/manifest.json](../../data/manifest.json), [data/manifest.md](../../data/manifest.md)):**
  - **Tổng số trang PDF vật lý:** **80 trang** (`48` trang `NIST.AI.100-1.pdf` + `32` trang `NIST.CSWP.29.pdf`).
  - **Quy tắc tính trang nội dung hợp lệ (`page_counting_rule`):** Chỉ tính các trang PDF vật lý chứa nội dung chuyên môn của khung tiêu chuẩn có độ dài văn bản sau chuẩn hóa Unicode **$\ge 500$ ký tự**. Loại bỏ hoàn toàn và ghi log: trang bìa (cover), trang thông tin xuất bản/tuyên bố miễn trừ trách nhiệm (front-matter/back-matter disclaimer), lời cảm ơn (acknowledgments), mục lục (Table of Contents), danh mục hình/bảng (List of Figures/Tables), và các trang chỉ chứa sơ đồ minh họa ít chữ (`< 500` ký tự).
  - **Số trang bị loại trừ:** **13 trang** (`8` trang của `nist-ai-rmf-1.0`: P.1, 2, 3, 4, 5, 16, 39, 48; và `5` trang của `nist-csf-2.0`: P.1, 2, 3, 4, 32).
  - **Tổng số trang nội dung hợp lệ được tính:** **67 trang** (`40` trang `nist-ai-rmf-1.0` + `27` trang `nist-csf-2.0`, vượt yêu cầu tối thiểu $\ge 30$ trang), với tổng cộng **`161,967` ký tự chuẩn hóa**.

### 2. Chuẩn hóa, lỗi và giới hạn
- **Quy trình đọc và chuẩn hóa ([starter/src/ingestion.py](../../starter/src/ingestion.py)):**
  - Dùng `pypdf` (`v6.21.4`) trích xuất văn bản từng trang vật lý, giữ nguyên số trang gốc (`1-indexed`).
  - Hàm `normalize_text()` thực hiện: (1) chuẩn hóa bảng mã Unicode về dạng dựng sẵn `NFC`; (2) lọc bỏ dòng header lặp lại ở đầu trang của tài liệu NIST; (3) nối lại các từ tiếng Anh bị ngắt dòng bằng dấu gạch ngang (`([A-Za-z])-\s*\n\s*([a-z])` $\rightarrow$ `\1\2`, ví dụ `organi-\nzations` $\rightarrow$ `organizations`); (4) làm sạch khoảng trắng ngang thừa và gom các dòng bị ngắt cứng trong cùng một đoạn văn nhưng **giữ nguyên ranh giới đoạn (`\n\n`), tiêu đề mục (`Part`, `Appendix`, `Table`, `1.2.2...`), và các gạch đầu dòng/mã tiểu mục (`GOVERN 1.1:`, `o GV.SC-05:`)**.
- **Ghi log trang lỗi/loại trừ:** Toàn bộ 80 trang vật lý (gồm 67 trang `valid` và 13 trang `excluded` kèm lý do chi tiết như `cover_page`, `table_of_contents`, `low_text_figure_only (Fig. 3, <500 chars)`) được xuất tự động tại [starter/results/page_diagnostics_log.json](../../starter/results/page_diagnostics_log.json) và [results/page_diagnostics_log.json](../../results/page_diagnostics_log.json).
- **Giới hạn xử lý văn bản:**
  - `pypdf` trích xuất luồng text tuần tự nên với các bảng nhiều cột (như `Table 1`–`Table 4` trong AI RMF hoặc `Table 2. CSF Tiers`), tiêu đề cột (`Categories Subcategories Continued on next page`) đôi khi bị ghép vào cuối đoạn văn.
  - Một số chữ in nghiêng/tiêu đề trong `NIST.CSWP.29.pdf` có khoảng trắng nhỏ giữa các ký tự trong PDF gốc (ví dụ `Im provement`, `P latform Security`, `Suppl y chain`).

### 3. Embedding model, Vector store, Metric, Lệnh chạy và Chi phí
- **Embedding Model ([starter/src/embeddings.py](../../starter/src/embeddings.py)):**
  - **Provider / Model:** `OpenAI` — `text-embedding-3-small` (API REST `/v1/embeddings`).
  - **Số chiều (`dimensions`):** `1536` chiều (float32, chuẩn hóa độ dài đơn vị).
  - **Cách xử lý query/document:** Nhúng đối xứng (symmetric dense embedding) cùng model `text-embedding-3-small` cho cả document chunks (theo batch 64 chunks) và câu hỏi benchmark; giữ nguyên model và vector câu hỏi cho cả 3 chiến lược A, B, C. Không dùng vector mock/ngẫu nhiên; báo lỗi `RuntimeError` tường minh nếu thiếu `OPENAI_API_KEY` hoặc lỗi kết nối.
- **Vector Store ([starter/src/store.py](../../starter/src/store.py)):**
  - **Hệ quản trị:** `PostgreSQL 16.16 (Debian 16.16-1.pgdg12+1)` + extension `pgvector 0.8.7` chạy qua Docker Compose ([starter/docker-compose.yml](../../starter/docker-compose.yml), cổng `127.0.0.1:55433`, lưu bền vững trên Docker volume `day6_student_starter_pg_data`).
  - **Bảng dữ liệu & Index:** Bảng `document_chunks` có khóa chính `(strategy, chunk_id)`, cột vector `embedding vector(1536)`, và B-tree index trên `(strategy, domain, year, section)` cùng `(strategy, document_id)`.
  - **Metric & Chế độ tìm kiếm:** Khoảng cách **Cosine** (`embedding <=> %s::vector`, điểm tương đồng `score = 1.0 - cosine_distance`), tìm kiếm chính xác (**Exact search** / sequential scan kết hợp lọc trước bằng mệnh đề SQL `WHERE` được tham số hóa an toàn).
  - **Xử lý nạp lại không trùng (Idempotent Upsert) & Tài liệu thay đổi:** Khi nạp lại, `PgVectorStore.upsert()` kiểm tra các `chunk_id` hiện có của `(strategy, document_id)`, xóa các `chunk_id` cũ không còn tồn tại trong bản mới (xử lý trường hợp tài liệu nguồn thay đổi/ngắn đi), sau đó thực thi `INSERT ... ON CONFLICT (strategy, chunk_id) DO UPDATE`. Đã kiểm chứng thực nghiệm trong [starter/results/indexing_telemetry_cp4.json](../../starter/results/indexing_telemetry_cp4.json): nạp lại lần 2 giữ nguyên số bản ghi (`A: 383`, `B: 247`, `C: 247`) và tự động dọn sạch chunk giả lỗi thời (`248` $\rightarrow$ `247`).
- **Chi phí thực tế (theo đơn giá OpenAI `$0.02 / 1,000,000 tokens`):**
  - Nhúng Chiến lược A (`383` chunks): `33,145` tokens $\rightarrow$ **`$0.000663`** (`11.596s`).
  - Nhúng Chiến lược B (`247` chunks): `29,915` tokens $\rightarrow$ **`$0.000598`** (`6.681s`).
  - Chiến lược C (`247` chunks, cùng tập chunk với B): **`$0.000598`** (`6.685s`) nếu tính độc lập (hoặc `$0.000000` khi tái sử dụng vector đã nhúng của B).
  - Nhúng 20 câu hỏi Benchmark: `546` tokens $\rightarrow$ **`$0.000011`** (`1.807s`).
  - **Tổng chi phí API toàn bài lab:** **`$0.001272`** (thực trả) / **`$0.001870`** (nếu tính riêng cả 3 index).
- **Lệnh chạy tái lập (từ thư mục gốc của repo):**
  ```powershell
  # 1. Khởi động PostgreSQL 16 + pgvector và kiểm tra kết nối
  docker compose -p day6_student_starter -f starter/docker-compose.yml up -d --wait
  starter\.venv\Scripts\python.exe starter\scripts\check_setup.py

  # 2. Kiểm chứng Corpus (67 trang hợp lệ), Benchmark (20 câu) và xuất thống kê Chunking (A & B)
  starter\.venv\Scripts\python.exe starter\scripts\verify_corpus.py
  starter\.venv\Scripts\python.exe starter\scripts\verify_benchmark.py
  starter\.venv\Scripts\python.exe starter\scripts\run_chunking_preview.py

  # 3. Nhúng OpenAI embeddings, lưu vào pgvector (A, B, C), kiểm chứng idempotent upsert
  starter\.venv\Scripts\python.exe starter\scripts\run_cp4_indexing.py

  # 4. Chạy đánh giá Benchmark dev/test, xuất trace top-3 và tạo bộ mẫu Audit thủ công
  Set-Location starter; .\.venv\Scripts\python.exe -m src.run; Set-Location ..
  starter\.venv\Scripts\python.exe starter\scripts\generate_cp5_audit_artifacts.py
  ```

### 4. Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn
| Trường Metadata | Bắt buộc / Bổ sung | Kiểu | Nguồn giá trị (từ tài liệu gốc, không tự đoán) | Giá trị trong Corpus | Lý do chọn & Vai trò |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `document_id` | Bắt buộc | `str` | Mã định danh tài liệu trong Manifest | `nist-ai-rmf-1.0`, `nist-csf-2.0` | Truy vết tài liệu nguồn và quản lý xóa/cập nhật chunk theo tài liệu |
| `source` | Bắt buộc | `str` | Đường dẫn file PDF gốc | `starter/data/NIST.AI.100-1.pdf`, `starter/data/NIST.CSWP.29.pdf` | Truy vết trực tiếp tới file PDF vật lý |
| `page` | Bắt buộc | `int` | Số thứ tự trang vật lý PDF (`1-indexed`) | `5 .. 47` | Đối chiếu bằng chứng (`gold_page`) chính xác tới từng trang |
| `domain` | **Lọc bổ sung 1** | `str` | Lĩnh vực tiêu chuẩn của văn bản NIST | `ai_risk`, `cybersecurity` | **Trường lọc quan trọng nhất:** Cả 2 khung NIST đều có hàm `GOVERN`, `Supply Chain Risk`, `Current/Target Profile`. Lọc theo `domain` giúp cô lập đúng khung tiêu chuẩn khi người dùng hỏi trong phạm vi AI hoặc Cybersecurity |
| `year` | **Lọc bổ sung 2** | `int` | Năm xuất bản in trên trang tiêu đề PDF | `2023`, `2024` | Phân biệt phiên bản khung tiêu chuẩn theo mốc thời gian ban hành |
| `section` | **Lọc bổ sung 3** | `str` | Cấu trúc chương/phần thực tế trên trang PDF | 10 giá trị (`executive_summary`, `part_2_core_and_profiles`, `appendix_a_csf_core`, v.v.) | Lọc hẹp phạm vi tìm kiếm vào đúng chương/phụ lục (ví dụ chỉ tìm trong bảng Core Appendix A thay vì phần giới thiệu chung) |
| `version` | Bổ sung | `str` | Số phiên bản in trên bìa tài liệu | `"1.0"`, `"2.0"` | Truy vết phiên bản tài liệu khi nâng cấp |

---

## Cấu hình và benchmark

### 1. Ba cấu hình thử nghiệm A / B / C (So sánh có kiểm soát)
| Chiến lược | Phương pháp Chunking | Tham số Chunk | Số lượng Chunk | Metadata lưu kèm | Truy xuất & Lọc Metadata | Mục tiêu so sánh có kiểm soát |
| :--- | :--- | :--- | ---: | :--- | :--- | :--- |
| **A** | `fixed_size` (Cửa sổ ký tự cố định) | `size = 500`, `overlap = 50` (bước nhảy `450` ký tự) | `383` chunks (TB `463.9` ký tự) | `document_id`, `source`, `page`, `domain`, `year`, `version`, `section` | Top-3 Cosine (`<=>`), **không lọc metadata** (`filters=None`) | Baseline chia cửa sổ cứng |
| **B** | `by_paragraph` (Theo cấu trúc đoạn & tiêu đề) | Gom đoạn `\n\n` đến `max_size = 900`, `overlap = 0`; tách câu nếu đoạn `> 900` | `247` chunks (TB `654.3` ký tự) | Giống hệt A | Top-3 Cosine (`<=>`), **không lọc metadata** (`filters=None`) | **So sánh A–B:** Chỉ thay đổi chiến lược Chunking (giữ nguyên corpus, model, store, không filter) |
| **C** | `by_paragraph` (Giống hệt B) | Giống hệt B (`max_size = 900`, `overlap = 0`, cùng `247` chunks) | `247` chunks (TB `654.3` ký tự) | Giống hệt B | Top-3 Cosine (`<=>`) + **Bật SQL `WHERE` filter** (`domain`, `year`, `section`) khi câu hỏi có filter | **So sánh B–C:** Chỉ thay đổi duy nhất việc bật Metadata Filter (với câu không có filter, C chạy không filter giống B) |

### 2. Bộ câu hỏi Benchmark ($\ge 20$ câu) và Quy trình kiểm chứng Evidence
- **Quy mô & Phân chia ([benchmark/questions.json](../../benchmark/questions.json), [benchmark/README.md](../../benchmark/README.md)):**
  - Tổng số **20 câu hỏi** được xây dựng hoàn toàn trước khi chạy thử nghiệm: **15 câu `dev`** (`q01`–`q15`) và **5 câu `test` holdout** (`q16`–`q20`).
  - **Không trùng trang đích giữa `dev` và `test`:** 15 câu `dev` và 5 câu `test` nằm trên các trang đích chính hoàn toàn tách biệt (**`0` page overlap**), giảm thiểu hiện tượng rò rỉ dữ liệu khi chọn cấu hình trên `dev`.
  - **Độ phủ loại câu hỏi:** `direct` (6 câu: `q01, q02, q06, q08, q10, q17`), `paraphrase` (4 câu: `q03, q05, q09, q18`), `conditional_exception` (4 câu: `q04, q07, q11, q16`), và `metadata_filter` (**6 câu**: **4 câu `dev`** `q12`–`q15` và **2 câu `test`** `q19`–`q20`).
  - **Quy tắc Metadata Filter:** Các câu có filter chỉ dùng thông tin phạm vi giả định người dùng cung cấp trước (`domain`, `year`, `section`), tuyệt đối không chứa `gold_source_id`, `gold_page` hay đáp án.
- **Cách kiểm chứng Evidence ([starter/scripts/verify_benchmark.py](../../starter/scripts/verify_benchmark.py)):**
  - Chạy script kiểm tra tự động đối chiếu từng `evidence_quote` (20 quote chính + 8 `alternative_gold` quotes cho các khái niệm xuất hiện ở nhiều trang hợp lệ) với văn bản trang nguồn sau chuẩn hóa Unicode (`normalize_text`). Kết quả xác nhận **100% (28/28 quotes)** tồn tại nguyên vẹn tại trang nguồn đích ([starter/results/benchmark_verification_report.json](../../starter/results/benchmark_verification_report.json)).

### 3. Tiêu chí chọn chiến lược đã chốt trước khi xem Test
Được khóa trước trong [benchmark/questions.json](../../benchmark/questions.json) và [benchmark/README.md](../../benchmark/README.md) theo thứ tự ưu tiên từ cao xuống thấp:
1. **Ưu tiên 1:** `Dev Evidence Hit@3` cao nhất (trên 15 câu `dev`).
2. **Ưu tiên 2 (Phá hòa 1):** `Dev Hit@1` cao nhất (trên 15 câu `dev`).
3. **Ưu tiên 3 (Phá hòa 2):** Điểm **Chunk Coherence** trung bình `/2` (trên 10 vị trí nguồn cố định) và **Tỷ lệ tuân thủ Metadata Filter (`Filter Compliance`)** trên các câu có filter cao hơn.
4. **Ưu tiên 4 (Phá hòa 3):** Hiệu quả tài nguyên (số chunk ít hơn, thời gian ingest nhanh hơn và chi phí API thấp hơn).

---

## Kết quả

### Bảng 1: Độ chính xác truy xuất (Retrieval Accuracy) và Tài nguyên Ingest
*(Ghi chú: Một kết quả được tính là Hit khi đúng tài liệu nguồn, đúng trang đích hợp lệ VÀ chunk chứa trọn vẹn `evidence_quote` đã xác minh).*

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: |
| **A** (`fixed_size`, 500/50, no filter) | `dev` | `5/15 (33.3%)` | `7/15 (46.7%)` | 383 | 11.596s (ingest) + 0.898s (search) | \$0.000663 |
| **A** (`fixed_size`, 500/50, no filter) | `test` | `2/5 (40.0%)` | `3/5 (60.0%)` | 383 | 11.596s (ingest) + 0.299s (search) | \$0.000663 |
| **A** (`fixed_size`, 500/50, no filter) | `all` | `7/20 (35.0%)` | `10/20 (50.0%)` | 383 | 11.596s (ingest) + 1.197s (search) | \$0.000663 |
| **B** (`by_paragraph`, max 900, no filter) | `dev` | **`12/15 (80.0%)`** | **`13/15 (86.7%)`** | 247 | 6.681s (ingest) + 0.812s (search) | \$0.000598 |
| **B** (`by_paragraph`, max 900, no filter) | `test` | `1/5 (20.0%)` | **`4/5 (80.0%)`** | 247 | 6.681s (ingest) + 0.271s (search) | \$0.000598 |
| **B** (`by_paragraph`, max 900, no filter) | `all` | **`13/20 (65.0%)`** | **`17/20 (85.0%)`** | 247 | 6.681s (ingest) + 1.083s (search) | \$0.000598 |
| **C** (`by_paragraph`, max 900 + SQL filter) | `dev` | **`12/15 (80.0%)`** | **`13/15 (86.7%)`** | 247 | 6.685s (ingest) + 0.894s (search) | \$0.000598 |
| **C** (`by_paragraph`, max 900 + SQL filter) | `test` | `1/5 (20.0%)` | **`4/5 (80.0%)`** | 247 | 6.685s (ingest) + 0.298s (search) | \$0.000598 |
| **C** (`by_paragraph`, max 900 + SQL filter) | `all` | **`13/20 (65.0%)`** | **`17/20 (85.0%)`** | 247 | 6.685s (ingest) + 1.192s (search) | \$0.000598 |

> **Chỉ số chẩn đoán bổ sung (Diagnostic Page-Only Hit@3):** Chiến lược A đạt `Page Hit@3 = 15/15 (100.0%)` trên `dev` và `5/5 (100.0%)` trên `test` (`20/20` tổng cộng), nhưng chỉ đạt `10/20 (50.0%)` `Evidence Hit@3` vì **10 câu hỏi** (`q01, q03, q04, q05, q08, q10, q11, q13, q16, q19`) bị cửa sổ cứng 500 ký tự cắt đứt ngang câu bằng chứng (`split_evidence_error_count = 10`). Chiến lược B và C giảm lỗi cắt bằng chứng xuống chỉ còn **2 câu** (`q08, q10`).

### Bảng 2: Đánh giá thủ công Coherence, Metadata Usefulness và Grounding Quality
| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `0.80 / 2` (`n = 10`, tổng `8/20` điểm; mức `0`: 2, mức `1`: 8, mức `2`: 0) | `15/15 (100.0%)` (trên 5 câu test $\times$ top-3) | `dev`: `3/4 (75.0%)` · `test`: `2/2 (100.0%)` · `all filtered`: `5/6 (83.3%)` · `unfiltered (14 câu)`: `N/A` | Mức `0`: 0 · Mức `1`: 3 (`q16, q18, q19`) · Mức `2`: 2 (`q17, q20`) $\rightarrow$ TB: **`1.40 / 2`** (`7/10`) |
| **B** | **`1.90 / 2`** (`n = 10`, tổng `19/20` điểm; mức `0`: 0, mức `1`: 1, mức `2`: 9) | `15/15 (100.0%)` (trên 5 câu test $\times$ top-3) | `dev`: `3/4 (75.0%)` · `test`: `2/2 (100.0%)` · `all filtered`: `5/6 (83.3%)` · `unfiltered (14 câu)`: `N/A` | Mức `0`: 1 (`q17`) · Mức `1`: 1 (`q18`) · Mức `2`: 3 (`q16, q19, q20`) $\rightarrow$ TB: **`1.40 / 2`** (`7/10`) |
| **C** | **`1.90 / 2`** (`n = 10`, tổng `19/20` điểm; mức `0`: 0, mức `1`: 1, mức `2`: 9) | `15/15 (100.0%)` (trên 5 câu test $\times$ top-3) | **`dev`: `4/4 (100.0%)` · `test`: `2/2 (100.0%)` · `all filtered`: `6/6 (100.0%)`** · `unfiltered (14 câu)`: `N/A` | Mức `0`: 1 (`q17`) · Mức `1`: 1 (`q18`) · Mức `2`: 3 (`q16, q19, q20`) $\rightarrow$ TB: **`1.40 / 2`** (`7/10`) |

### Đường dẫn trace, nhãn thủ công và cách chọn mẫu
- **Full Top-3 Retrieval Traces (60 traces = 3 chiến lược $\times$ 20 câu):** [starter/results/retrieval_traces_top3.json](../../starter/results/retrieval_traces_top3.json) (bản sao tại [results/retrieval_traces_top3.json](../../results/retrieval_traces_top3.json)).
- **Tổng hợp chỉ số Benchmark (`dev`/`test`/`all`):** [starter/results/benchmark_summary_metrics.json](../../starter/results/benchmark_summary_metrics.json) (bản sao tại [results/benchmark_summary_metrics.json](../../results/benchmark_summary_metrics.json)).
- **Nhãn chấm thủ công Chunk Coherence (`n = 10` vị trí nguồn):** [starter/results/manual_audit_coherence.json](../../starter/results/manual_audit_coherence.json) (bản sao tại [results/manual_audit_coherence.json](../../results/manual_audit_coherence.json)).
  - *Cách chọn mẫu:* Chọn cố định trước khi xem điểm theo **10 `page_id` hợp lệ đầu tiên đã sắp xếp tăng dần** (`nist-ai-rmf-1.0:p06` đến `nist-ai-rmf-1.0:p15`), chấm chunk thứ 2 trên mỗi trang (`fixed:002` đối chiếu với `para:002` — tức vị trí ranh giới cắt chunk đầu tiên bên trong mỗi trang).
- **Nhãn chấm thủ công Metadata Usefulness (`15` bản ghi/chiến lược) & Grounding Quality (`5` câu test/chiến lược):** [starter/results/manual_audit_metadata_and_grounding.json](../../starter/results/manual_audit_metadata_and_grounding.json) (bản sao tại [results/manual_audit_metadata_and_grounding.json](../../results/manual_audit_metadata_and_grounding.json)).
  - *Cách chọn mẫu:* Kiểm tra toàn bộ 5 câu thuộc tập `test` (`q16`–`q20`) và toàn bộ `top-3` chunks trả về của chúng (`5 × 3 = 15` bản ghi mỗi chiến lược).

---

## Phân tích và kết luận

### 1. So sánh A–B và B–C; các ví dụ lỗi cụ thể (có ID câu và nguồn)

#### a) So sánh A vs. B (Tác động của Chunking: `fixed_size` 500/50 vs. `by_paragraph` max 900)
- **Độ chính xác truy xuất:** Chuyển từ cửa sổ cố định 500 ký tự (A) sang gom theo đoạn văn có giới hạn 900 ký tự (B) giúp tăng mạnh `Dev Hit@1` từ `5/15 (33.3%)` lên **`12/15 (80.0%)`** và `Dev Evidence Hit@3` từ `7/15 (46.7%)` lên **`13/15 (86.7%)`**. Trên tập `test`, `Evidence Hit@3` cũng tăng từ `3/5 (60.0%)` lên **`4/5 (80.0%)`**.
- **Tính mạch lạc (Coherence):** Điểm Coherence trung bình tăng hơn gấp đôi, từ **`0.80 / 2`** (A: 8/10 mẫu bị cắt ngang từ hoặc mất chủ ngữ ở đầu/cuối, 2/10 mẫu ở `p13:fixed:002` và `p15:fixed:002` bị điểm `0` do đứt hoàn toàn mệnh đề điều kiện) lên **`1.90 / 2`** (B: 9/10 mẫu đạt `2/2` giữ trọn vẹn đoạn văn; chỉ có 1 mẫu `p15:para:002` đạt `1/2` do danh sách bullet dài vượt 900 ký tự nên ý bullet thứ 4 bị tách sang chunk thứ hai).
- **Tài nguyên & Chi phí:** Nhờ không phải lặp lại `overlap=50` ký tự và gom các đoạn ngắn hợp lý, Chiến lược B giảm **35.5% số lượng chunk** (`247` so với `383` chunks), giảm **9.7% số token nhúng** (`29,915` so với `33,145` tokens), giảm **42.4% thời gian ingest** (`6.681s` so với `11.596s`) và tiết kiệm chi phí API (`$0.000598` so với `$0.000663`).

#### b) So sánh B vs. C (Tác động của Metadata Filter: Không lọc vs. Lọc theo `domain`, `year`, `section`)
- **Độ tuân thủ phạm vi (Filter Compliance):** Trên tập `dev`, Chiến lược B đạt `3/4 (75.0%)` câu tuân thủ filter do ở câu **`q15`** (yêu cầu tìm nguyên tắc phân quyền `PR.AA-05` trong phụ lục Core `section = "appendix_a_csf_core"`), chunk xếp hạng #3 của B (`nist-csf-2.0:p07:para:003`, `score = 0.5261`) lại lấy từ phần giới thiệu chung (`section = "overview_and_core_intro"`). Khi bật bộ lọc SQL `WHERE` ở **Chiến lược C**, toàn bộ các chunk ngoài phạm vi bị loại bỏ trước khi tính khoảng cách Cosine, đưa chunk đúng phụ lục (`nist-csf-2.0:p20:para:001`) vào top-3 và nâng **Filter Compliance lên tuyệt đối `4/4 (100.0%)` trên `dev` và `2/2 (100.0%)` trên `test` (`6/6 = 100.0%` toàn cục)**.
- **Giá trị và Hạn chế của Metadata:**
  - *Giá trị:* Cặp trường `source` + `page` giúp truy vết ngược 100% (`15/15` bản ghi test) về đúng trang PDF; trong khi `domain` (`ai_risk` vs. `cybersecurity`), `year` (`2023` vs. `2024`) và `section` giúp ngăn chặn nhiễu chéo giữa hai bộ tiêu chuẩn có chung thuật ngữ (`GOVERN`, `Profiles`, `Supply Chain`).
  - *Hạn chế:* Trường `section` được gán ở mức trang vật lý (`page-level`); nếu một trang chứa phần cuối của mục trước và phần đầu của mục sau thì cả trang mang nhãn của mục chính. Ngoài ra, nếu người dùng truyền filter sai (ví dụ lọc nhầm `year = 2023` khi hỏi về `CSF 2.0`), lọc cứng (`hard SQL WHERE filter`) sẽ trả về rỗng hoặc loại mất câu trả lời đúng.

#### c) Phân tích chi tiết các ví dụ lỗi điển hình (Failure Cases)
1. **Ví dụ lỗi 1 — Lỗi cắt đứt bằng chứng ở Chiến lược A (`q19`, tập `test`, nguồn `nist-ai-rmf-1.0` trang `28`):**
   - *Câu hỏi:* Hỏi về quy trình kiểm kê (`GOVERN 1.6`) và ngừng vận hành an toàn hệ thống AI (`GOVERN 1.7`).
   - *Hiện tượng:* Chiến lược A truy xuất đúng trang 28 ngay ở hạng #1 (`nist-ai-rmf-1.0:p28:fixed:002`, `score = 0.7209`), nhưng cửa sổ 500 ký tự đã cắt đúng vào giữa chữ `"GOVERN 1.7: Processe"` | `"s and procedures are in place for decommissioning..."`. Kết quả là chunk #1 mất nhãn `GOVERN 1.7`, mất hoàn toàn nội dung `GOVERN 1.6` (nằm ở `fixed:001` không lọt vào top-3), dẫn đến `Evidence Hit@3 = False` và `Grounding = 1/2`.
   - *Khắc phục ở B & C:* Chunk `nist-ai-rmf-1.0:p28:para:001` (`score = 0.6944`, hạng #2) giữ nguyên vẹn toàn bộ khối `GOVERN 1.5`, `GOVERN 1.6` và `GOVERN 1.7`, đạt `Evidence Hit@3 = True` và `Grounding = 2/2`.
2. **Ví dụ lỗi 2 — Lỗi cắt mất điều kiện ở Chiến lược A (`q04`, tập `dev`, nguồn `nist-ai-rmf-1.0` trang `13`):**
   - *Câu hỏi:* Trong điều kiện nào việc phát triển và triển khai hệ thống AI phải dừng lại một cách an toàn?
   - *Hiện tượng:* Ở Chiến lược A, câu bằng chứng bị cắt làm đôi giữa `nist-ai-rmf-1.0:p13:fixed:001` (chứa mệnh đề điều kiện `"In cases where an AI system presents unacceptable negative risk levels... development and deployment should c"`) và `p13:fixed:002` (bắt đầu bằng `"ease in a safe manner until risks can be sufficiently managed."`). Không có chunk đơn lẻ nào chứa đủ cả điều kiện lẫn hành động, gây lỗi `split_evidence_error`. Chiến lược B và C giữ nguyên đoạn văn tại `p13:para:001` (hạng #1, `score = 0.7263`).
3. **Ví dụ lỗi 3 — Đánh đổi làm loãng vector nhúng trên đoạn văn dài ở Chiến lược B & C (`q17`, tập `test`, nguồn `nist-ai-rmf-1.0` trang `30`):**
   - *Câu hỏi:* Kết quả nào cần đạt được sau khi hoàn thành hàm `MAP` trước khi chuyển sang `MEASURE` và `MANAGE`? (Đáp án: đủ tri thức ngữ cảnh để đưa ra quyết định `go/no-go` ban đầu).
   - *Hiện tượng:* Trên trang 30 (`nist-ai-rmf-1.0`), câu quy định về quyết định `go/no-go` nằm ở cuối trang, ngay sau một danh sách gồm 8 gạch đầu dòng. Trong Chiến lược B và C (`max_size = 900`), các gạch đầu dòng và đoạn kết được gom chung, làm vector nhúng của chunk trang 30 bị pha loãng bởi các ý phụ; hệ quả là 3 chunk bàn về thứ tự thực hiện `GOVERN -> MAP -> MEASURE -> MANAGE` ở trang 26 (`p26:para:002`, `score = 0.6585`), trang 33 (`p33:para:001`, `score = 0.6524`) và trang 35 (`p35:para:001`, `score = 0.6479`) chiếm mất 3 vị trí đầu (`Hit@3 = False`, `Grounding = 0/2`). Ngược lại, cửa sổ nhỏ 500 ký tự của Chiến lược A (`p30:fixed:005`, `score = 0.6464`) tách riêng phần cuối trang 30 nên lọt vào hạng #3 (`Hit@3 = True`, `Grounding = 2/2`).
4. **Ví dụ lỗi 4 — Lỗi tách danh sách liệt kê qua ngưỡng `max_size` ở cả A, B, C (`q18`, tập `test`, nguồn `nist-ai-rmf-1.0` trang `44`):**
   - *Câu hỏi:* Phụ lục B nêu những rủi ro đặc thù nào của AI chưa được giải quyết toàn diện bởi các khung phần mềm truyền thống?
   - *Hiện tượng:* Danh sách 5 gạch đầu dòng ở cuối trang 44 nằm sau một đoạn văn dài. Cả `p44:fixed:004` (A) và `p44:para:003` (B, C) đều lấy được câu dẫn và 2–3 gạch đầu dòng đầu tiên (nên đều đạt `Evidence Hit@3 = True` theo quote chính), nhưng phần gạch đầu dòng cuối cùng (về mô hình bên thứ ba, transfer learning và fine-tuning lệch mục đích) bị đẩy sang chunk kế tiếp (`p44:para:004`) nằm ngoài top-3, khiến điểm `Grounding Quality` chấm tay của cả A, B, C ở câu `q18` chỉ đạt **`1/2`** (thiếu điều kiện/ý liệt kê).

### 2. Chiến lược chọn, đánh đổi và điều kiện áp dụng
- **Chiến lược được chọn:** **Chiến lược C (`by_paragraph`, `max_size = 900` + SQL Metadata Filter trên `domain`, `year`, `section`)**.
- **Lý do chọn (theo đúng tiêu chí đã khóa trước khi xem tập `test`):**
  1. Đạt **`Dev Evidence Hit@3` cao nhất (`13/15 = 86.7%`)** và **`Dev Hit@1` cao nhất (`12/15 = 80.0%`)**, vượt xa Chiến lược A (`7/15 = 46.7%` và `5/15 = 33.3%`).
  2. Phá thế hòa với Chiến lược B nhờ đạt **Tỷ lệ tuân thủ Metadata Filter tuyệt đối `4/4 (100.0%)` trên `dev`** (so với `3/4 = 75.0%` của B) và **`2/2 (100.0%)` trên `test`**, đồng thời giữ nguyên điểm **Chunk Coherence cao nhất (`1.90 / 2`)** và chi phí/thời gian ingest tối ưu (`247` chunks, `6.685s`, `$0.000598`).
- **Sự đánh đổi (Trade-offs) & Điều kiện áp dụng:**
  - *Đánh đổi giữa kích thước chunk và độ tập trung ngữ nghĩa:* Chunk theo đoạn (`max_size = 900`) giữ trọn vẹn ngữ cảnh pháp lý/kỹ thuật và tăng mạnh Coherence (`1.90/2` so với `0.80/2`), nhưng với các câu hỏi nhắm vào một câu đơn lẻ nằm lẫn trong đoạn dài nhiều ý (như `q17`), vector của cả đoạn có thể bị loãng nhẹ so với chunk ngắn.
  - *Đánh đổi của Hard Metadata Filter:* Rất hiệu quả khi ứng dụng biết rõ ngữ cảnh (người dùng đang tra cứu sổ tay AI hay Cybersecurity, hoặc chọn bộ lọc trên UI), nhưng nếu người dùng không biết trước phạm vi hoặc gán nhãn sai, cần fallback về chế độ không lọc (như cách Chiến lược C tự động chạy không filter cho 14 câu có `filter = null`).

### 3. Hạn chế của dữ liệu, nhãn, tập test nhỏ và đo thời gian/chi phí
1. **Quy mô tập Test nhỏ (`n = 5` câu):** Mỗi câu hỏi trong tập `test` chiếm tới `20.0%` tổng điểm test. Do đó, việc chênh lệch 1 câu (như câu `q17`) làm dịch chuyển ngay `20%` trên bảng điểm. Kết quả trên tập `test` chỉ mang tính kiểm chứng minh họa cho corpus 2 văn bản NIST này, **không dùng để tuyên bố chiến lược C là tối ưu tổng quát cho mọi loại tài liệu**.
2. **Nguy cơ thiên lệch khi chấm thủ công (Self-Grading Bias):** Người thực hiện chấm thủ công Coherence (`10` vị trí), Metadata (`15` bản ghi) và Grounding (`5` câu test) chính là tác giả xây dựng pipeline. Để giảm thiên lệch, vị trí mẫu Coherence đã được chọn cố định theo quy tắc cơ học (10 `page_id` đầu tiên theo thứ tự từ điển) và mọi điểm số đều đính kèm trích dẫn văn bản thực tế trong file JSON audit.
3. **Sai số đo thời gian và chi phí:** Thời gian nhúng API (`6.68s` – `11.60s`) phụ thuộc vào độ trễ mạng tới máy chủ OpenAI tại thời điểm chạy; thời gian truy vấn PostgreSQL (`~1.1s` cho 20 câu qua kết nối TCP local) trên tập nhỏ 247–383 chunks sử dụng exact scan nên chưa phản ánh chi phí xây dựng chỉ mục HNSW/IVFFlat ở quy mô hàng triệu bản ghi.

### 4. Hướng cải tiến nếu làm lại hoặc mở rộng
1. **Hierarchical / Parent-Child Chunking:** Nhúng vector trên các đoạn nhỏ hoặc từng câu/tiểu mục (`child chunks` ~300–400 ký tự) để đạt độ nhạy cosine cao cho các câu hỏi chi tiết như `q17`, nhưng khi truy xuất thì trả về toàn bộ đoạn văn/mục cha (`parent chunk` ~900–1200 ký tự) để giữ điểm Coherence `1.90+/2` và không bị đứt danh sách bullet như `q18`.
2. **Giữ tiêu đề danh sách (List-Header Preservation):** Khi một danh sách gạch đầu dòng bị tách qua ngưỡng `max_size` (như trang 15 hoặc trang 44), tự động gắn lặp lại câu dẫn đầu danh sách vào chunk tiếp theo để không làm mất ngữ cảnh của các bullet cuối.
3. **Hybrid Retrieval (Dense Embedding + BM25 Keyword Search):** Kết hợp điểm tương đồng ngữ nghĩa của `text-embedding-3-small` với điểm khớp từ khóa chính xác `BM25` (hoặc PostgreSQL `tsvector`) để tăng độ chính xác cho các truy vấn chứa mã định danh kỹ thuật như `GOVERN 1.7`, `MEASURE 1.3`, `PR.AA-05`, `RC.RP-03`.

### 5. Minh bạch sử dụng công cụ AI & Kiểm chứng ([RULES.md](../../RULES.md))
- Trong quá trình làm bài, học viên sử dụng AI Assistant (Antigravity) để hỗ trợ viết mã nguồn khung pipeline Python, script kiểm chứng tự động và định dạng bảng báo cáo.
- Toàn bộ dữ liệu nguồn (`NIST.AI.100-1.pdf`, `NIST.CSWP.29.pdf`), kết quả chạy PostgreSQL + `pgvector`, vector nhúng từ OpenAI API (`text-embedding-3-small`), 60 retrieval traces và các nhãn chấm lỗi đều được chạy thật 100% trên máy local và kiểm chứng chéo với văn bản PDF gốc.

