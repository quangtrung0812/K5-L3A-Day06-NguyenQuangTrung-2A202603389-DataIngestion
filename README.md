# Day 06 · Data Ingestion Engineering — Bài nộp cá nhân

- **Học viên:** Nguyễn Quang Trung (`2A202603389` · Lớp `L3A`)
- **Chủ đề:** Enterprise Technology Governance & Risk Management Frameworks (`NIST AI RMF 1.0` & `NIST CSF 2.0`)
- **Báo cáo cá nhân hoàn chỉnh:** [report/individual/2A202603389_NguyenQuangTrung.md](report/individual/2A202603389_NguyenQuangTrung.md)
- **Thông tin học viên:** [STUDENT.md](STUDENT.md)

---

## 1. Cấu trúc thư mục & Đường dẫn dữ liệu

```text
.
├── STUDENT.md                                         # Thông tin học viên & repo nộp bài
├── README.md                                          # Hướng dẫn cài đặt, lệnh chạy, đường dẫn dữ liệu
├── data/
│   ├── manifest.json                                  # Manifest dữ liệu máy đọc (nguồn, quyền, số trang, SHA-256)
│   └── manifest.md                                    # Manifest dữ liệu chi tiết
├── benchmark/
│   ├── questions.json                                 # 20 câu hỏi benchmark (15 dev / 5 test, 0 overlap trang chính)
│   └── README.md                                      # Quy trình thiết kế, kiểm chứng quote và bảng phân bổ
├── artifacts/
│   └── experiment_log.csv                             # Nhật ký cấu hình, giả thuyết và kết quả thực nghiệm A/B/C
├── results/                                           # Bản sao kết quả, trace top-3, thống kê và nhãn audit ở root
├── starter/
│   ├── docker-compose.yml                             # PostgreSQL 16 + pgvector 0.8.7 (port 55433)
│   ├── sql/001_init.sql                               # Schema bảng documents, chunks (VECTOR(1536), JSONB, GIN/B-Tree)
│   ├── data/
│   │   ├── NIST.AI.100-1.pdf                          # NIST AI RMF 1.0 (48 trang vật lý / 40 trang hợp lệ)
│   │   └── NIST.CSWP.29.pdf                           # NIST CSF 2.0 (32 trang vật lý / 27 trang hợp lệ)
│   ├── src/
│   │   ├── ingestion.py                               # Trích xuất PDF theo trang, chuẩn hóa text, gắn metadata
│   │   ├── chunking.py                                # Chiến lược fixed_size(500, 50) và by_paragraph(900)
│   │   ├── embeddings.py                              # OpenAI text-embedding-3-small (1536 chiều) + telemetry
│   │   ├── store.py                                   # PgVectorStore: upsert idempotent, dọn chunk thừa, vector search + SQL filter
│   │   ├── evaluation.py                              # Hit@1, Evidence Hit@3, Filter Compliance, Coherence & Grounding helpers
│   │   └── run.py                                     # CLI chạy toàn bộ pipeline thực nghiệm A, B, C
│   ├── scripts/
│   │   ├── check_setup.py                             # Kiểm tra kết nối PostgreSQL + pgvector
│   │   ├── verify_corpus.py                           # Kiểm chứng số trang hợp lệ & xuất page_diagnostics_log.json
│   │   ├── verify_benchmark.py                        # Kiểm chứng 100% evidence_quote nguyên văn và điều kiện dev/test
│   │   ├── run_chunking_preview.py                    # Xuất chunks_strategy_A/B.json và chunking_stats.json (CP3)
│   │   ├── run_cp4_indexing.py                        # Chạy nạp pgvector + kiểm chứng idempotent re-ingestion (CP4)
│   │   └── generate_cp5_audit_artifacts.py            # Xuất nhãn đánh giá thủ công Coherence, Metadata & Grounding (CP5)
│   └── results/                                       # Toàn bộ file JSON log, trace, telemetry do scripts sinh ra
└── report/
    └── individual/
        └── 2A202603389_NguyenQuangTrung.md            # Báo cáo phân tích kỹ thuật 5 khía cạnh theo RUBRIC.md
```

---

## 2. Hướng dẫn cài đặt (Setup)

### 2.1. Khởi chạy PostgreSQL 16 + pgvector 0.8.7
```powershell
cd starter
docker compose up -d
```
Container `day6_student_starter-postgres-1` lắng nghe tại `127.0.0.1:55433` và tự động nạp schema `starter/sql/001_init.sql`.

### 2.2. Cài đặt môi trường Python & Biến môi trường
```powershell
cd starter
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```
Mở `starter/.env` (đã được bảo vệ bởi `.gitignore`) và cấu hình:
```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55433/rag_lab
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

Kiểm tra kết nối database:
```powershell
.\starter\.venv\Scripts\python.exe starter\scripts\check_setup.py
```

---

## 3. Lệnh chạy tái lập từng bước (Reproducible Commands)

Tất cả các lệnh dưới đây chạy từ thư mục gốc của repository:

```powershell
# 1. Kiểm chứng Corpus PDF (67 trang nội dung hợp lệ / 80 trang vật lý)
.\starter\.venv\Scripts\python.exe starter\scripts\verify_corpus.py

# 2. Kiểm chứng bộ 20 câu hỏi Benchmark (15 dev / 5 test, 100% quote khớp nguyên văn)
.\starter\.venv\Scripts\python.exe starter\scripts\verify_benchmark.py

# 3. Chạy thử nghiệm Chunking (Strategy A: 383 chunks; Strategy B/C: 247 chunks)
.\starter\.venv\Scripts\python.exe starter\scripts\run_chunking_preview.py

# 4. Tạo Embedding (OpenAI text-embedding-3-small) & nạp vào pgvector + kiểm tra Idempotency
.\starter\.venv\Scripts\python.exe starter\scripts\run_cp4_indexing.py

# 5. Chạy đánh giá Benchmark trên cả 3 chiến lược A, B, C (lưu top-3 traces & summary metrics)
.\starter\.venv\Scripts\python.exe -m starter.src.run --skip-ingest

# 6. Sinh báo cáo Audit thủ công (Coherence n=10/chiến lược, Metadata n=15, Grounding n=5)
.\starter\.venv\Scripts\python.exe starter\scripts\generate_cp5_audit_artifacts.py
```
*(Nếu muốn chạy toàn bộ từ nạp dữ liệu đến đánh giá trong 1 lệnh duy nhất: `.\starter\.venv\Scripts\python.exe -m starter.src.run`)*

---

## 4. Tóm tắt 3 chiến lược & Kết quả thực nghiệm chính

| Chỉ số / Thuộc tính | Strategy A (`fixed_size`) | Strategy B (`by_paragraph`) | Strategy C (`by_paragraph` + Metadata Filter) |
|---|---|---|---|
| **Quy tắc chia chunk** | `fixed_size(size=500, overlap=50)` | `by_paragraph(max_size=900)` | `by_paragraph(max_size=900)` |
| **Metadata filter khi truy xuất** | Không (`use_filters=False`) | Không (`use_filters=False`) | Có (`domain`, `year`, `section`) |
| **Số lượng chunk / Ký tự TB** | `383` chunks (`471.3` chars) | `247` chunks (`651.2` chars) | `247` chunks (`651.2` chars) |
| **Chi phí / Thời gian nạp** | `$0.000663` / `11.60s` | `$0.000598` / `6.68s` | `$0.000598` / `6.69s` |
| **Dev Page Hit@1 (`n=15`)** | `5/15` (`33.3%`) | **`12/15` (`80.0%`)** | **`12/15` (`80.0%`)** |
| **Dev Evidence Hit@3 (`n=15`)** | `7/15` (`46.7%`) | **`13/15` (`86.7%`)** | **`13/15` (`86.7%`)** |
| **Test Page Hit@1 (`n=5`)** | `2/5` (`40.0%`) | `1/5` (`20.0%`) | `1/5` (`20.0%`) |
| **Test Evidence Hit@3 (`n=5`)** | `3/5` (`60.0%`) | **`4/5` (`80.0%`)** | **`4/5` (`80.0%`)** |
| **Chunk Coherence (`0–2`, `n=10`)** | `0.80 / 2.00` | **`1.90 / 2.00`** | **`1.90 / 2.00`** |
| **Filter Compliance (`n=6` có filter)** | `5/6` (`83.3%`) | `5/6` (`83.3%`) | **`6/6` (`100.0%`)** |
| **Grounding Score (`0–2`, `n=5`)** | `1.40 / 2.00` | `1.40 / 2.00` | **`1.40 / 2.00`** |

Chi tiết phân tích lỗi (split-evidence, ranking ties, semantic interference) và khuyến nghị kiến trúc được trình bày đầy đủ trong [report/individual/2A202603389_NguyenQuangTrung.md](report/individual/2A202603389_NguyenQuangTrung.md).

---

## 5. Tài liệu tham chiếu của Lab

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |
