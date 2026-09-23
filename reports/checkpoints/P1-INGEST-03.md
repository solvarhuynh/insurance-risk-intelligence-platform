# P1-INGEST-03 — Nạp đủ năm partition canonical

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Dùng một ingestion path duy nhất để nạp B–E sau A, lưu batch metadata, đối soát tổng staging và xác nhận rerun không accidental duplicate.

## File đã thay đổi

- `docs/architecture/staging-design.md`
- `reports/checkpoints/P1-INGEST-03.md`
- `log/progress-log.md`

## Lệnh đã chạy

```text
python scripts/load_brvehins1_to_staging.py --source-file brvehins1[b-e].csv --batch-size 5000
python scripts/load_brvehins1_to_staging.py --source-file brvehins1e.csv --batch-size 5000  # rerun
sqlcmd < five-partition reconciliation assertion
```

## Bằng chứng runtime

- Năm batch SUCCESS đều có `ExpectedSourceRows=393071`, `StagingRows=393071`, `RejectedRows=0`.
- Batch B `9F8E1334-161D-4739-925E-4CC9414D0897`: `54,595 ms`.
- Batch C `20F620C5-9C71-41DC-B9C9-02DFE18D4B69`: `48,622 ms`.
- Batch D `9C600196-E15E-43D8-BA7B-B5716FE1C4D9`: `46,868 ms`.
- Batch E `04B72A0F-8426-40B3-A485-EC7B7170DE29`: `48,573 ms`.
- Reconciliation assertion: expected total `1,965,355` = staging total `1,965,355` = distinct `SourceFile + SourceRowNumber` `1,965,355`; successful partitions `5`.
- Rerun E trả `SKIPPED`; batch E vẫn có một `SUCCESS` và audit có `STARTED`, `SUCCESS`, `SKIPPED`. Không có row staging mới.
- Các 14 raw logical duplicate đã biết không bị deduplicate; technical identity theo source ordinal giữ mọi dòng nguồn.

## Tiêu chí PASS

- [x] A–E được nạp qua cùng `scripts/load_brvehins1_to_staging.py`.
- [x] Có năm SUCCESS partition batch và mỗi batch đối soát 393,071 dòng.
- [x] Tổng staging đối soát 1,965,355 dòng.
- [x] Không duplicate `SourceFile + SourceRowNumber`.
- [x] Rerun partition SUCCESS là no-op có audit.
- [x] Raw không bị thay đổi.

## Bước tiếp theo chính xác

Hoàn thành yêu cầu bổ sung dependency management: audit imports, tách host/dev/Airflow dependencies, tạo manifest có version compatibility evidence và cập nhật tài liệu/validator. Sau gate đó mới chuyển sang `P1-DWH-01`.
