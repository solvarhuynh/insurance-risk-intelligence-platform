# P1-DATA-02 — Đóng băng source data contract

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Chuyển bằng chứng EDA thành contract chuẩn cho `brvehins1`: mọi cột, mapping SQL, grain, technical identity, null/duplicate/invalid policy, batch semantics và metric dẫn xuất.

## File đã thay đổi

- `docs/architecture/data-dictionary.md`
- `docs/architecture/source-data-contract.md`
- `docs/architecture/architecture-explained.md`
- `docs/guides/how-to-run.md`
- `docs/specs/implementation-guide.md`
- `README.md`
- `reports/checkpoints/P1-DATA-02.md`
- `log/progress-log.md`

## Lệnh đã chạy

```text
python -c <data-contract evidence assertions>
python scripts/validate_repo.py
git diff --check
rg -n -i <current stale-doc and unsupported-metric patterns>
```

## Bằng chứng và quyết định

- Dictionary ghi đủ 23 cột đã quan sát, dtype pandas, mapping SQL, nullable expectation, validation và intended use.
- Grain được freeze là source-delivered aggregate risk observation; không phải customer, policy hay claim event cá thể.
- Không có natural customer/policy identifier. Technical uniqueness là `SourceFile + SourceRowNumber`; `SourceRecordHash` là SHA-256 fingerprint, không dùng làm unique identity vì có 14 duplicate logical rows.
- Nullable descriptor được preserve nguyên trạng. Measure nguồn bắt buộc non-null, finite và non-negative.
- Zero exposure/premium là value hợp lệ, nhưng `ClaimFrequency`/`LossRatio` trả NULL thay vì infinity.
- Source batch cố định gồm năm partition, mỗi partition 393,071 dòng; rerun partition đã thành công phải no-op/return batch cũ, không insert trùng.
- Các cột claim được đánh dấu `TARGET_DERIVED`/`LEAKAGE` cho future ML; không có model hay threshold model được freeze.

## Chính sách DQ đã đóng băng

| Nhóm | Chính sách |
|---|---|
| Schema/file | File thiếu, header lỗi hoặc schema khác là hard failure. |
| Numeric | Parse lỗi, non-finite, NULL ở measure bắt buộc hoặc số âm là hard failure. |
| Geography | `State`/`StateAb` không cùng null hoặc mapping mâu thuẫn là hard failure. |
| Zero denominator | Giữ source row; ratio NULL. |
| Duplicate | 14 logical duplicates là audit warning, không deduplicate. |
| `VehYear` NULL/0 | Giữ nguyên; suspicious/business review. |
| Các field fire/rob bằng 0 | Audit-only source constant của snapshot, không xóa. |

## Tiêu chí PASS

- [x] 23 field được xác minh trong `data-dictionary.md`.
- [x] Mọi field có SQL mapping, source group, null/validation expectation và intended use.
- [x] Grain và technical identity được mô tả tường minh.
- [x] Không có fake business identifier.
- [x] Có null, duplicate, invalid, raw immutability và partition ingestion policy.
- [x] Có công thức metric dẫn xuất và chính sách mẫu số bằng 0.
- [x] Assertion độc lập xác minh đủ 23 field và các policy bắt buộc.
- [x] Static validator: 40 PASS, 0 FAIL, 8 SKIPPED runtime scope; `git diff --check` pass.

## Bước tiếp theo chính xác

`P1-INFRA-01 / P1-INFRA-02` — cấu hình credential qua environment, khởi động SQL Server, xác minh kết nối runtime và bootstrap idempotent `DWH_Insurance` với schema/meta foundation.
