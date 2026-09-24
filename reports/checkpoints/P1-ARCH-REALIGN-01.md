# P1-ARCH-REALIGN-01 — Căn chỉnh Insurance Data Platform

Trạng thái: `PASS`  
Phạm vi: audit, realign current source-of-truth và static validation. Không triển khai SUSEP DWH, Airflow, performance tuning hoặc Power BI.

## Kết luận kiến trúc là gì?

Repository là **Insurance Data Platform** có nhiều data track độc lập:

~~~text
Track A — SUSEP Market DWH / Performance / Market BI
Track B — brvehins1 Motor Risk Analytics / ML
Track C — Prudential Life Underwriting, planned khi source xuất hiện
~~~

SUSEP và brvehins1 đều là `ACTIVE_CANONICAL` theo track. Hai track không có proven row-level relationship, vì vậy không tạo CustomerId, PolicyId, customer mapping hay fact chung giả.

## Physical data inventory đã xác nhận gì?

| Source | Path / physical evidence | Schema/grain đã biết | Implementation status |
|---|---|---|---|
| SUSEP | `data/raw/susep.gov.br/insurance_dataset.csv`, 751,126,569 bytes, non-empty | Header: company_code, company_name, year_month, product, state, premiums, claims, claim_premium_ratio. Candidate market aggregate; exact grain/row count/semantics chưa profile lại. | Track A source present; DWH chưa implement |
| brvehins1 | 5 CSV ở `data/raw/brvehins1/`, tổng 1,965,355 rows theo runtime evidence Track B | 23-column aggregate motor-risk observation; technical identity SourceFile + SourceRowNumber | Track B staging/DWH/DQ/bounded ML/scoring đã runtime-pass |
| Prudential | Không có file nào mang tên Prudential/Life Assessment trong workspace | Không có physical schema để inspect | ORIGINAL_PLANNED_SOURCE / NOT_PRESENT |

SUSEP có field time vật lý `year_month`; company/product/state là candidate dimensions. Candidate fact là một market observation chứa premium/claim/ratio nguồn cung cấp. Không có evidence cho customer, policy hoặc claim-event grain. P1-SUSEP-01 phải dùng streaming EDA để biến candidate này thành contract hoặc bác bỏ nó.

## Drift đã được phân loại như thế nào?

| Classification | Hits / paths | Kết luận và xử lý |
|---|---|---|
| CURRENT_WRONG_SCOPE | README, REPO_LEARNING_GUIDE, architecture-explained, source contract/dictionary, DWH design, run guide, implementation guide, roadmap, validator trước realignment | Đã gọi brvehins1 là nguồn duy nhất hoặc hạ SUSEP sai scope. Các current docs/validator đã được realign. |
| CURRENT_VALID_TRACK_B | V2–V10, loader, current risk DWH/DQ SQL, ml/, Track-B contracts, checkpoint P1-ML-02..05 | Giữ nguyên implementation và metrics. FactRiskObservation chỉ là fact Track B. |
| CURRENT_VALID_TRACK_A | SUSEP physical CSV; project-scope, source-strategy, overall-architecture sau realignment | Khôi phục source role active canonical, nhưng chỉ claim source/header-level static validation. |
| HISTORICAL_EVIDENCE | foundation-50pct report, ml-complete report, P1-ML checkpoints, P1-REPO-00, P1-WF-04 và old progress-log rows | Giữ nguyên, không sửa runtime numbers hay narrative cũ. Đọc với nhãn evidence theo thời điểm. |
| STALE_SCAFFOLD | sql/03_sp_dim_customer_scd2.sql, sql/04_sp_dim_others.sql, sql/05_sp_fact_premium.sql, sql/06_sp_fact_claims.sql, sql/07_data_quality_checks.sql | Commented model customer/policy/fact cũ không được actual SUSEP CSV chứng minh. Không thực thi/không refactor thành SUSEP DWH trong task này. |
| FUTURE_PLAN | P1-SUSEP-01..05, P1-PERF-*, P1-ORCH-*, P1-BI-*, Track C | Có roadmap/guardrails, chưa được gọi runtime pass. |
| UNKNOWN | Không có | Hit Porto trong log/report là lịch sử; Porto Alegre trong Track-B source là giá trị geography, không chứng minh Porto Seguro source active. |

## Current source-of-truth nào đã được realign?

- README và learning guide nay giới thiệu platform đa track bằng tiếng Việt.
- docs/architecture/project-scope.md ghi mục tiêu, precedence, drift timeline và non-integration rule.
- docs/architecture/source-strategy.md là inventory nguồn/candidate SUSEP design.
- docs/architecture/overall-architecture.md biểu diễn hai active tracks và Track C planned.
- Track-B contract/design docs được gắn scope rõ để không làm suy giảm SUSEP.
- run guide, implementation guide, glossary, performance note và roadmap không còn hướng dẫn architecture một nguồn.
- Validator kiểm tra cả raw SUSEP header/non-empty và 5 brvehins1 schema; không bắt Prudential tồn tại và không gọi Track A runtime-pass.
- Cursor rules yêu cầu chọn track, cấm fake join và yêu cầu cập nhật source strategy khi thay đổi scope.

## Điều gì được bảo toàn?

Không sửa raw CSV. Không thay đổi grain/table/data runtime của brvehins1, ML target/metrics/artifact hay scoring semantics. Không rewrite historical report/checkpoint/log entries. Migration V1 và DAG chỉ được sửa mô tả scope Track B, không đổi hành vi.

## Validation nào đã pass?

- `python scripts/validate_repo.py`: **67 PASSED, 0 FAILED, 9 SKIPPED**.
  Validator hiện kiểm tra non-empty/header của SUSEP Track A và năm partition
  schema-compatible của brvehins1 Track B.
- `python -m py_compile` cho validator, maintained ML modules và DAG: pass.
- `docker compose config -q`: pass.
- `git diff --check`: pass.

Static validator cố ý skip SUSEP profiling/ingestion/DWH/DQ, Airflow,
performance và Power BI. Task này chỉ sửa metadata/documentation/rules và
không rerun expensive ML. DQ validation runtime khởi tạo trong lần kiểm tra
kiến trúc bị dừng trước khi hoàn thành vì vượt thời gian command window; không
dùng attempt đó làm runtime evidence mới. Evidence Track B runtime hiện hữu vẫn
ở checkpoint/report trước realignment.

## Điều gì cố ý chưa làm?

- Không download Prudential.
- Không ingest/profile đầy đủ SUSEP hoặc tạo SUSEP staging/DWH.
- Không chạy/triển khai Airflow.
- Không retrain ML, không performance tune, không Power BI.
- Không commit hoặc push.

## Bước tiếp theo được phép là gì?

P1-SUSEP-01: streaming EDA + source contract trên actual SUSEP CSV. Nó phải xác nhận exact row count, grain/key/duplicate policy, null/range/type, month semantics, premium/claims/ratio semantics trước bất kỳ DDL hay ETL nào.
