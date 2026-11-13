# Data Manifest — NIST Enterprise AI & Cybersecurity Risk Governance Corpus

## 1. Tổng quan Corpus & Quy tắc tính trang

- **Chủ đề:** Enterprise Technology Governance & Risk Management Frameworks (NIST AI RMF 1.0 & NIST CSF 2.0)
- **Thời điểm truy cập (`accessed_at`):** `2026-11-13T16:11:00+07:00`
- **Giấy phép & Quyền sử dụng (`license_or_permission`):** **Public Domain** — Tác phẩm của Chính phủ Hoa Kỳ (NIST / U.S. Department of Commerce) theo điều khoản `17 U.S.C. § 105`. Được phép sao chép, lưu trữ trong repository công khai và xử lý qua embedding model/API mà không vi phạm bản quyền. Không chứa dữ liệu cá nhân (PII) hay thông tin mật.
- **Tổng số trang vật lý:** **80 trang** (trên 2 tài liệu PDF)
- **Tổng số trang bị loại trừ (bìa, mục lục, front-matter, trang sơ đồ < 500 ký tự, disclaimer cuối):** **13 trang**
- **Tổng số trang nội dung hợp lệ được tính:** **67 trang** (vượt mức tối thiểu 30 trang của đề bài)
- **Tổng số ký tự nội dung đã chuẩn hóa (trên 67 trang hợp lệ):** **161,967 ký tự**

### Quy tắc tính trang nội dung (`page_counting_rule`)
1. Loại bỏ toàn bộ các trang bìa (cover), trang thông tin xuất bản/miễn trừ trách nhiệm (front-matter/back-matter disclaimer), lời cảm ơn (acknowledgments), mục lục (Table of Contents), danh mục hình/bảng (List of Figures/Tables).
2. Loại bỏ các trang chỉ chứa sơ đồ/hình minh họa hoặc chuyển tiếp có độ dài văn bản sau chuẩn hóa Unicode **< 500 ký tự** (cụ thể: trang 16 và trang 39 của `NIST.AI.100-1.pdf`).
3. Mọi trang bị loại đều được ghi log lý do cụ thể trong `data/manifest.json` và `starter/results/page_diagnostics_log.json`.

## 2. Chi tiết từng tài liệu nguồn

| `source_id` | Tiêu đề | Phiên bản / Năm | Đường dẫn / URL | Trang vật lý | Trang hợp lệ | Trang bị loại | Tổng ký tự chuẩn hóa |
|---|---|---|---|---:|---:|---:|---:|
| `nist-ai-rmf-1.0` | Artificial Intelligence Risk Management Framework (AI RMF 1.0) | `Version 1.0 (2023)` | `starter/data/NIST.AI.100-1.pdf` ([NIST PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)) | 48 | **40** | 8 (P: 1, 2, 3, 4, 5, 16, 39, 48) | 99,510 |
| `nist-csf-2.0` | The NIST Cybersecurity Framework (CSF) 2.0 | `Version 2.0 (2024)` | `starter/data/NIST.CSWP.29.pdf` ([NIST PDF](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf)) | 32 | **27** | 5 (P: 1, 2, 3, 4, 32) | 62,457 |

## 3. Metadata phục vụ Truy vết & Lọc (Filter)

| Trường Metadata | Kiểu dữ liệu | Nguồn giá trị | Giá trị trong Corpus | Mục đích sử dụng |
|---|---|---|---|---|
| `document_id` | `str` | Định danh tài liệu trong Manifest | `nist-ai-rmf-1.0`, `nist-csf-2.0` | Truy vết tài liệu gốc |
| `source` | `str` | Đường dẫn file PDF gốc | `starter/data/NIST.AI.100-1.pdf`, `starter/data/NIST.CSWP.29.pdf` | Truy vết file nguồn |
| `page` | `int` | Số thứ tự trang PDF vật lý (1-indexed) | `5..47` (tùy tài liệu) | Truy vết chính xác vị trí trang |
| `domain` | `str` | Phạm vi tiêu chuẩn của tài liệu NIST | `ai_risk` (AI RMF 1.0), `cybersecurity` (CSF 2.0) | **Trường lọc chính** giúp phân biệt câu hỏi về quản trị rủi ro AI vs. an ninh mạng (đặc biệt khi cả 2 cùng có hàm `GOVERN`, `Supply Chain Risk`, `Profiles`) |
| `year` | `int` | Năm xuất bản ghi trên trang bìa/tiêu đề PDF | `2023`, `2024` | **Trường lọc bổ sung** theo năm ban hành tiêu chuẩn |
| `section` | `str` | Cấu trúc phần/chương thực tế của PDF | `executive_summary`, `part_1_framing_and_audience`, `part_1_trustworthiness_and_effectiveness`, `part_2_core_and_profiles`, `appendices`, `preface`, `overview_and_core_intro`, `profiles_tiers_and_integration`, `appendix_a_csf_core`, `appendices_tiers_and_glossary` | **Trường lọc bổ sung** và hỗ trợ kiểm tra ngữ cảnh theo chương mục |

## 4. Danh sách các trang bị loại trừ (Excluded Pages Log)

| `page_id` | `source` | Trang vật lý | Ký tự chuẩn hóa | Lý do loại trừ |
|---|---|---:|---:|---|
| `nist-ai-rmf-1.0:p01` | `starter/data/NIST.AI.100-1.pdf` | 1 | 76 | `cover_page` |
| `nist-ai-rmf-1.0:p02` | `starter/data/NIST.AI.100-1.pdf` | 2 | 377 | `front_matter_publication_info` |
| `nist-ai-rmf-1.0:p03` | `starter/data/NIST.AI.100-1.pdf` | 3 | 1530 | `front_matter_disclaimer_and_version_schedule` |
| `nist-ai-rmf-1.0:p04` | `starter/data/NIST.AI.100-1.pdf` | 4 | 1268 | `table_of_contents` |
| `nist-ai-rmf-1.0:p05` | `starter/data/NIST.AI.100-1.pdf` | 5 | 1607 | `list_of_figures_and_tables` |
| `nist-ai-rmf-1.0:p16` | `starter/data/NIST.AI.100-1.pdf` | 16 | 385 | `low_text_figure_only (Fig. 3, <500 chars)` |
| `nist-ai-rmf-1.0:p39` | `starter/data/NIST.AI.100-1.pdf` | 39 | 443 | `low_text_transition_page (<500 chars)` |
| `nist-ai-rmf-1.0:p48` | `starter/data/NIST.AI.100-1.pdf` | 48 | 89 | `back_cover_doi_only` |
| `nist-csf-2.0:p01` | `starter/data/NIST.CSWP.29.pdf` | 1 | 195 | `cover_page` |
| `nist-csf-2.0:p02` | `starter/data/NIST.CSWP.29.pdf` | 2 | 2254 | `front_matter_abstract` |
| `nist-csf-2.0:p03` | `starter/data/NIST.CSWP.29.pdf` | 3 | 502 | `front_matter_acknowledgments` |
| `nist-csf-2.0:p04` | `starter/data/NIST.CSWP.29.pdf` | 4 | 1996 | `table_of_contents_and_figures` |
| `nist-csf-2.0:p32` | `starter/data/NIST.CSWP.29.pdf` | 32 | 1224 | `back_matter_disclaimer_and_notes` |
