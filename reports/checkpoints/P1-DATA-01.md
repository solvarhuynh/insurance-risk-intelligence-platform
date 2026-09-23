# P1-DATA-01 — EDA và source profiling thực tế

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Profile toàn bộ năm partition `brvehins1` bằng xử lý streaming, tạo bằng chứng review-friendly và machine-readable, đồng thời đánh giá source grain mà không sửa raw hay suy diễn business identifier.

## File đã thay đổi

- `scripts/profile_brvehins1.py`
- `notebooks/01-eda.ipynb`
- `reports/data/brvehins1-profile.json`
- `reports/data/brvehins1-column-profile.csv`
- `reports/data/brvehins1-eda-summary.md`
- `reports/checkpoints/P1-DATA-01.md`
- `log/progress-log.md`

## Lệnh đã chạy

```text
python -m py_compile scripts/profile_brvehins1.py
python scripts/profile_brvehins1.py --chunk-size 100000
python -c <EDA evidence assertions>
python -m json.tool notebooks/01-eda.ipynb
python scripts/validate_repo.py
git diff --check
```

## Phương pháp và bằng chứng

- Đọc `pandas` theo chunk 100,000 dòng; không giữ nhiều DataFrame toàn bộ trong RAM.
- Retain các vector số duy nhất cần cho quantile chính xác.
- Kiểm tra exact duplicate bằng SQLite tạm ngoài repository, dùng toàn bộ 23 trường logical làm primary-key text; không dùng hash dễ va chạm làm bằng chứng duy nhất.
- Thời gian chạy profile: 330.018 giây.
- Bằng chứng chi tiết: `reports/data/brvehins1-profile.json`, `reports/data/brvehins1-column-profile.csv`, `reports/data/brvehins1-eda-summary.md`.

## Kết quả chính

| Hạng mục | Bằng chứng |
|---|---|
| Tổng số dòng | 1,965,355 |
| Partition | 5 file, mỗi file 393,071 dòng |
| Schema | 23 cột, năm schema bằng nhau |
| Exact duplicate logical rows | 14; 1,965,341 logical rows distinct |
| Null đáng kể | `DrivAge` 284,948 (14.498551%), `VehModel`/`VehGroup` 120,515 (6.131971%), `Gender` 88,189 (4.487179%) |
| Null thấp | `VehYear` 4; `Area`/`State`/`StateAb` 13 mỗi cột |
| Numeric âm | 0 ở toàn bộ cột số nguồn |
| `HasClaim` | 363,076 có claim; 1,602,279 không claim |
| Zero exposure/premium | 51,762 ở mỗi metric |
| Mapping State/StateAb | 1,965,342 pair không null; 0 mâu thuẫn hai chiều |
| Claim/amount consistency | 0 amount dương khi count bằng 0; 0 count dương khi amount bằng 0 |

Các distribution, range và quantile chính xác của exposure, premium, sum insured, năm nhóm claim count/amount, `TotalClaimCount`, `TotalClaimAmount`, `ClaimFrequency` và `LossRatio` nằm trong JSON/CSV/Markdown report. Không cắt hoặc cap outlier.

## Đánh giá grain và identifier

Một dòng là quan sát tổng hợp do nguồn cung cấp, ghép các thuộc tính người lái, xe, địa lý với exposure, premium và claim. Nguồn không có mã định danh khách hàng, hợp đồng hoặc thời gian giao dịch rõ ràng; vì vậy không thể mô tả dòng như một customer hay policy cá thể.

Không tạo natural PolicyID hoặc CustomerID. Chính sách đề xuất cho stage tiếp theo là technical identity `(SourceFile, SourceRowNumber)`; `SourceRecordHash` chỉ là fingerprint nội dung, không thay thế row identity vì đã quan sát 14 dòng logical trùng.

## Phân loại quan sát

| Phân loại | Quan sát |
|---|---|
| VALID | Không có số âm; State/StateAb nhất quán; claim count và amount không mâu thuẫn theo hai kiểm tra chéo. |
| SUSPICIOUS | 14 dòng logic trùng; các phân bố exposure, premium, claim và loss ratio có đuôi dài. Không deduplicate/cap trong EDA. |
| INVALID BY CONTRACT | Chưa kết luận ở stage này vì contract chưa đóng băng. |
| UNKNOWN / BUSINESS REVIEW REQUIRED | 51,762 dòng exposure/premium bằng 0; 8 `VehYear` bằng 0; hai trường fire/rob đều bằng 0 ở toàn bộ nguồn; nullable descriptor cần policy explicit. |

## Giả định và quyết định

- `ClaimFrequency` chỉ tính khi `ExposTotal > 0`; `LossRatio` chỉ tính khi `PremTotal > 0`.
- Các value 0 không tự động là invalid; chúng sẽ được phân loại chính thức ở P1-DATA-02.
- Dòng duplicate nguồn vẫn được ingest nguyên trạng và truy vết bằng technical identity.
- Không sửa nội dung raw, không dùng dữ liệu legacy và không huấn luyện ML.

## Tiêu chí PASS

- [x] Có exact total row count, source columns và schema compatibility.
- [x] Có null profile, duplicate profile, categorical cardinality và numeric range/quantile.
- [x] Có phân bố claim, premium, exposure và candidate target `HasClaim`.
- [x] Có grain assessment trung thực, không tạo fake business identifier.
- [x] `python scripts/validate_repo.py`: 40 PASS, 0 FAIL, 8 SKIPPED runtime scope.
- [x] Notebook JSON và `git diff --check` pass.

## Bước tiếp theo chính xác

`P1-DATA-02` — đóng băng source data contract: từng cột, mapping SQL, technical key, null/duplicate/invalid policy và semantic của metric dẫn xuất.
