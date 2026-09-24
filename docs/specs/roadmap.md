# Roadmap hiện hành — Insurance Data Platform

## Milestone đã hoàn thành có evidence

```text
P1-ARCH-REALIGN-01
  → P1-SUSEP-01..05 (Track A runtime)
  → P1-PERF-01..03 (Track A measured tuning)
  → P1-ORCH-01..02 (Airflow valid + controlled failure)
  → P1-BI-01 (semantic model / manual handoff)
  → P1-E2E-01..02 (safe reproducibility + failure paths)
  → P1-DOC-01..03 (final current docs, diagrams, audit)
```

Track A SUSEP và Track B brvehins1 đều có runtime evidence trong boundary đã nêu. Historical checkpoints giữ nguyên trạng thái cũ; chúng không thay thế roadmap hiện hành.

## Trạng thái theo hạng mục

| Hạng mục | Status | Evidence |
|---|---|---|
| Track A source contract / ingestion / DWH / reconciliation / DQ | PASS | `P1-SUSEP-01` đến `P1-SUSEP-05` |
| Track A performance | PASS | `P1-PERF-01/02`, `reports/performance-report.md` |
| Track B foundation / ML / prediction reconciliation | PASS | preflight, `P1-ML-*` |
| Airflow multi-track runtime | PASS | `P1-ORCH-01/02` |
| Power BI semantic model | PASS | `docs/bi/semantic-model.md` |
| Power BI actual `.pbix`/refresh | BLOCKED_MANUAL | `powerbi/README.md` |
| Safe E2E / failure paths | PASS | `P1-E2E-01/02` |
| Prudential Track C | FUTURE | source not present |

## Việc còn lại sau P1

1. Cài/cho phép Power BI Desktop hoặc approved PBIP toolchain.
2. Tạo real artifact gồm hai subject area disconnected, refresh từ SQL Server và đối chiếu measure với SQL.
3. Lưu artifact và evidence refresh; chỉ sau đó đánh giá lại final verdict.

Không download Prudential, không fake cross-track relationship, không retrain Track B chỉ để tăng metric, và không commit/push như một side effect của roadmap.
