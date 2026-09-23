# Tôi đang xây cái gì vậy?

Bạn đang xây một nền tảng **Motor Insurance Data Warehouse** — kho dữ liệu cho bảo hiểm xe cơ giới tại Brazil. Mục tiêu không phải chỉ là đọc CSV rồi vẽ biểu đồ. Mục tiêu là biến dữ liệu nguồn thành một hệ thống có thể kiểm tra: dữ liệu vào từ đâu, có bị mất dòng không, các con số có hợp lệ không, và về sau có thể phục vụ phân tích, Machine Learning và dashboard.

Nguồn nghiệp vụ hiện hành là năm file `brvehins1[a-e].csv`. Mỗi dòng là một **aggregate risk observation** — một quan sát tổng hợp về đặc điểm lái xe/xe/địa lý, exposure, premium và claim. Nó không chứng minh đó là một khách hàng, hợp đồng hay event claim riêng lẻ. Vì vậy repository không được tự bịa `CustomerId` hoặc `PolicyNumber`.

```text
Raw CSV brvehins1 (RUNTIME_PASS: nguồn bất biến)
        ↓
stg.BrVehIns1 (RUNTIME_PASS: staging + lineage)
        ↓
Dimensions + FactRiskObservation (RUNTIME_PASS: DWH)
        ↓
dq.sp_RunQualityGate (RUNTIME_PASS: DQ gate)
        ├── Analytics / Power BI (FUTURE)
        └── ML risk-association workflow (STALE SCAFFOLD, chưa chạy)
                 ↓
              Airflow orchestration (STALE SCAFFOLD, chưa chạy)
```

**So what?** Nếu bạn chỉ nhớ một điều, hãy nhớ rằng “xây được bảng” chưa đủ. Dự án đã chứng minh raw → staging → fact không mất dòng và có cổng chặn dữ liệu lỗi. ML, Airflow và dashboard chỉ được làm sau nền này.

## Nếu tôi mở repo lần đầu, tôi nên nhìn folder nào trước?

Đừng đọc theo alphabet. Hãy đi theo hành trình của dữ liệu.

1. Mở `README.md` để biết ý định chung, nhưng đối chiếu với `reports/foundation-50pct-report.md`: README hiện còn dòng trạng thái DWH/DQ cũ, còn report và runtime evidence là nguồn đáng tin hơn.
2. Mở `data/raw/` để thấy năm file `brvehins1` canonical. Không sửa, không đưa output vào đây.
3. Mở `reports/data/brvehins1-eda-summary.md`, rồi `docs/architecture/source-data-contract.md`. Report nói dữ liệu thực tế trông thế nào; contract quyết định hệ thống phải xử lý nó ra sao.
4. Mở `migrations/` và `sql/` để xem SQL Server được tạo và nạp như thế nào.
5. Mở `scripts/` để xem validator, EDA streaming và loader Python.
6. Mở `docs/architecture/dwh-design.md` để hiểu fact/dimension hiện hành.
7. Chỉ sau đó mới mở `ml/` và `dags/`: chúng là scaffold cũ, hữu ích để biết việc còn lại chứ chưa phải pipeline thực.
8. Cuối cùng đọc `log/progress-log.md` và `reports/checkpoints/`: đây là timeline và bằng chứng từng gate.

| Nơi | Vai trò hiện tại | Đọc ngay? |
|---|---|---|
| `data/raw/brvehins1/` | Năm CSV canonical, immutable | Có, chỉ xem tên/header/size |
| `reports/data/` | Bằng chứng EDA thực tế | Có |
| `docs/architecture/` | Contract, staging, DWH, dependency boundary | Có |
| `migrations/` | Tạo SQL Server objects theo version V1–V8 | Có sau contract |
| `sql/` | Entry point runtime và scaffold legacy | Có, nhưng phân biệt current/stale |
| `scripts/` | Validator, profiler, loader | Có |
| `ml/`, `dags/` | Chưa refactor theo brvehins1 | Đọc sau |
| `powerbi/` | Placeholder | Đọc rất sau |

## Những file quan trọng đang làm việc gì?

### `docs/architecture/source-data-contract.md` dùng để làm gì?

Đây là “bản giao kèo” của dữ liệu: nó nói rõ 23 cột, null nào được phép, duplicate nào được giữ, grain là gì và ratio chia cho zero phải xử lý ra sao. Input là EDA; output là nguyên tắc cho loader, staging, DWH và DQ. Nếu file này sai, các bước sau có thể chạy nhưng đang hiểu sai dữ liệu.

### `scripts/load_brvehins1_to_staging.py` dùng để làm gì?

Nó đọc từng CSV theo kiểu streaming, nghĩa là đọc tuần tự thay vì đưa gần hai triệu dòng vào RAM một lần. Nó thêm `SourceFile`, `SourceRowNumber`, `BatchId`, hash và insert vào `stg.BrVehIns1`. File này được `pyodbc` gọi trên host để kết nối SQL Server. Rerun cùng partition sẽ thấy batch SUCCESS và trả `SKIPPED`, không nạp trùng.

### `migrations/V1__create_dwh_schema.sql` đến `V8__create_data_quality_gate.sql` dùng để làm gì?

**Migration** là thay đổi database có version, giống các chương sửa nhà theo thứ tự: V1 tạo nhà và sổ theo dõi batch; V2 tạo staging; V6 tạo dimensions; V7 tạo fact; V8 tạo DQ gate. `meta.SchemaVersion` ghi nhận version đã áp dụng. Điều này giúp một máy khác biết database đã có cấu trúc nào.

### `dwh.FactRiskObservation` lưu gì và vì sao nó ở trung tâm DWH?

**Fact table** là bảng trung tâm lưu measure, tức các con số cần phân tích. Fact này giữ exposure, premium, sum insured, claim count và claim amount của đúng một source row. Nó nối tới `DimDriverProfile`, `DimVehicle`, `DimGeography` bằng key kỹ thuật. Nếu nhét tất cả mô tả lặp lại vào mọi dòng, bảng vẫn dùng được, nhưng khó kiểm soát lookup và tái sử dụng mô tả khi phân tích.

### `dq.sp_RunQualityGate` dùng để làm gì?

**Data Quality Gate** là cổng kiểm tra: nếu hard rule fail, stored procedure ghi log rồi `THROW` SQL error để bước sau dừng. Nó kiểm tra schema, reconciliation, numeric, State mapping, fact grain, FK và ratio. Controlled test đã chứng minh gate fail mà không làm hỏng raw/staging/fact.

### `scripts/validate_repo.py` có thể và không thể chứng minh gì?

Nó là **static validation** — kiểm tra cấu trúc tĩnh: file bắt buộc, header CSV, schema header, YAML Compose, Python syntax, notebook JSON và SQL comment balance. Nó giống kiểm tra bản thiết kế xe. Nó không thể chứng minh SQL Server đang chạy, fact có dữ liệu hay Airflow đã hoàn thành DAG; những điều đó cần runtime command và checkpoint.

## Các file nói chuyện với nhau như thế nào?

```text
data/raw/brvehins1/*.csv
  → scripts/profile_brvehins1.py / notebooks/01-eda.ipynb
  → reports/data/* và docs/architecture/data-dictionary.md
  → docs/architecture/source-data-contract.md
  → migrations/V2 + scripts/load_brvehins1_to_staging.py
  → stg.BrVehIns1
  → V6 dimensions và V7 FactRiskObservation
  → V8 dq.sp_RunQualityGate
  → future: ML artifact, prediction table, Airflow, Power BI
```

Mỗi mũi tên chuyển một thứ cụ thể. CSV chuyển 23 giá trị source; loader thêm lineage; dimension loader chuyển tuple mô tả distinct thành key; fact giữ measures và key; DQ chuyển các phép kiểm tra thành PASS/FAIL log.

## Một dòng brvehins1 đi qua project như thế nào?

Hãy tưởng tượng một dòng bất kỳ trong `brvehins1c.csv`; không cần bịa giá trị cụ thể. Raw row có các cột `VehModel`, `Area`, `PremTotal`, `ClaimNbOther`... Khi vào staging, giá trị source được preserve đúng type và có thêm `SourceFile=brvehins1c.csv`, ordinal `SourceRowNumber`, `BatchId`, hash và load time. Đây là nhãn vận chuyển, không đổi ý nghĩa nghiệp vụ.

Kế tiếp, tuple driver/vehicle/geography được lookup vào dimension. Ví dụ `VehYear + VehModel + VehGroup` dẫn tới một `VehicleKey`. Fact nhận key đó cùng tất cả measure. DQ kiểm tra fact có orphan hay bị lệch count so với staging. Dòng này có thể được dùng để phân tích risk association sau này; chưa được phép gọi nó là claim tương lai của một cá nhân.

## Tôi chưa biết DWH, vậy những khái niệm nào thật sự cần hiểu?

- **Raw Data** — dữ liệu gốc; như hộp hàng vừa nhận. Trong repo là năm CSV, không được sửa.
- **Staging** — khu nhận hàng tạm; như quầy kiểm hàng trước khi xếp kho. `stg.BrVehIns1` giữ bản parse và lineage.
- **Data Warehouse (DWH)** — kho được tổ chức để truy vấn/đối soát; ở đây là `DWH_Insurance` trong SQL Server.
- **Grain** — đơn vị nhỏ nhất mà một row biểu diễn; như hỏi “mỗi ô sổ là một món hàng hay một hóa đơn?”. Grain fact hiện là một aggregate risk observation.
- **Dimension** — danh mục mô tả để cắt lát số liệu; như danh mục xe/địa lý trong kho. `DimVehicle` không phải vehicle master đã xác minh.
- **Surrogate Key** — số ID do kho tự tạo; như số kệ kho. `VehicleKey` liên kết bảng mà không giả mạo VIN.
- **Natural Key** — key có sẵn từ nghiệp vụ; repo không có policy/customer natural key đã chứng minh.
- **Technical Key** — key cho hệ thống, không khẳng định business meaning; `(SourceFile, SourceRowNumber)` là technical identity.
- **Foreign Key** — ràng buộc “số kệ này phải tồn tại”; fact có FK tới ba dimension.
- **Star Schema** — bố cục fact ở giữa, dimension bao quanh; như một phiếu trung tâm nối các danh mục. Đây là mô hình logic hiện tại.
- **ETL / ELT** — Extract/Transform/Load, tức lấy/chuyển/nạp dữ liệu. Loader và SQL procedure chia trách nhiệm này.
- **Idempotency** — chạy lại ra cùng kết quả, như bấm lại nút thanh toán không bị trừ tiền hai lần. Partition/fact rerun đều đã chứng minh.
- **Reconciliation** — đối chiếu count giữa các lớp, như đối chiếu số thùng giao với số thùng nhập kho. 1,965,355 = source = staging = fact.
- **Batch** — một lô xử lý; mỗi CSV partition có batch metadata riêng.
- **Incremental Load** — chỉ xử lý phần mới; file partition SUCCESS được nhận biết và skip. Đây là implemented ở mức file batch.
- **CDC (Change Data Capture)** — cơ chế database ghi nhận insert/update/delete theo log thay đổi. brvehins1 tĩnh không tự có lịch sử CDC; file `sql/02_enable_cdc.sql` hiện là stale scaffold, chưa chứng minh CDC thật.
- **SCD Type 2** — lưu lịch sử phiên bản của một dimension, như giữ địa chỉ cũ/mới của cùng khách hàng. Không áp dụng ở đây vì không có customer identity/effective date; `sql/03_sp_dim_customer_scd2.sql` là stale scaffold.

## Docker, SQL Server và Airflow thực sự đóng vai trò gì?

**Docker** là cách đóng gói phần mềm vào môi trường lặp lại được; như đưa cả máy pha cà phê và công thức vào một hộp thay vì bảo từng máy tự cài. **Container** là hộp đang chạy; **image** là bản thiết kế để tạo hộp. `docker-compose.yml` mô tả SQL Server và Airflow.

SQL Server container `insurance_sqlserver` đã RUNTIME_PASS: nó chứa `DWH_Insurance`, staging, DWH và DQ. Điều này tốt hơn chỉ dùng pandas/CSV vì SQL Server cho phép FK, transaction, batch metadata và audit chung.

Airflow là **orchestrator** — nhạc trưởng, không phải nhạc công. Nó phải gọi các script/procedure đã hoạt động; không chứa business logic. Container Airflow được khai báo nhưng DAG hiện vẫn là stale Porto/customer scaffold và chưa có runtime evidence. Do đó SQL Server là CURRENT/RUNTIME_PASS; Airflow là FUTURE/STALE SCAFFOLD.

## brvehins1 chứa gì và tại sao nó phù hợp với project?

Dataset có nhóm driver (`Gender`, `DrivAge`), vehicle (`VehYear`, `VehModel`, `VehGroup`), geography (`Area`, `State`, `StateAb`), exposure, premium, sum insured, claim count và claim amount. Nó phù hợp cho analytics như phân tích premium/claim theo vehicle group hoặc geography.

Nếu sau này dự đoán `HasClaim`, các cột `ClaimNb*`, `ClaimAmount*`, `TotalClaimCount`, `HasClaim`, `ClaimFrequency` và `LossRatio` là **data leakage**: giống nhìn đáp án trước khi làm bài. Chúng mô tả outcome cùng snapshot, nên không được dùng làm input. Exposure/premium/sum insured có time semantics không rõ, nên cần review trước khi dùng ML.

## Agent đã làm được gì thật, và cái gì chỉ mới có khung?

| Subsystem | Status | Bằng chứng đơn giản | Còn thiếu |
|---|---|---|---|
| Governance/canonical data | DONE | brvehins1 được contract/validator dùng | Đồng bộ README cũ cần tiếp tục |
| EDA | RUNTIME_PASS | reports/data, 1,965,355 rows | Không cần làm lại |
| Data contract | DONE | source-data-contract.md | Review ML contract ở milestone sau |
| SQL Server/infrastructure | RUNTIME_PASS | Docker + DWH_Insurance | Fresh-machine certification |
| Staging/ingest | RUNTIME_PASS | 5 batch, rerun skip | File-incremental demo thêm nếu scope yêu cầu |
| DWH | RUNTIME_PASS | dimensions + FactRiskObservation | Không có customer/policy fact |
| DQ | RUNTIME_PASS | production PASS + controlled fail | DQ evolution khi source đổi |
| ML | STALE SCAFFOLD | Python syntax-only old stub | Contract, train, artifact, scoring |
| Airflow | STALE SCAFFOLD | DAG parse tĩnh old stub | Refactor + container runtime |
| CDC | STALE SCAFFOLD | SQL cũ comment | Synthetic demo nếu muốn học CDC |
| Performance/Power BI | FUTURE | template/.gitkeep | Chưa bắt đầu |

**STATIC_PASS** giống xe qua kiểm tra bản vẽ; **RUNTIME_PASS** giống xe đã chạy thật trên đường. Đừng dùng static syntax của ML/DAG để kết luận pipeline đã vận hành.

## Tại sao repo vẫn còn những file nhìn có vẻ sai?

Repository từng mang mô hình SUSEP + Porto Seguro Safe Driver: `Dim_Customer`, `PolicyNumber`, fact premium/claims tách rời và scoring customer. Những file như `sql/03_sp_dim_customer_scd2.sql`, `sql/05_sp_fact_premium.sql`, `sql/06_sp_fact_claims.sql`, `sql/08_sp_load_risk_predictions.sql`, `ml/*.py`, `dags/insurance_dwh_pipeline.py` vẫn còn để bảo toàn lịch sử/scaffold nhưng không phải architecture hiện hành.

**Historical artifact** là dấu vết cũ để hiểu lịch sử. **Stale scaffold** là code khung cũ, có thể compile nhưng không được chạy. **Current implementation** là V1–V8, loader, contract và DQ gate có runtime evidence. Khi hai file mâu thuẫn, ưu tiên runtime evidence và frozen contract.

## Làm sao tôi biết agent không chỉ viết code nhìn có vẻ đúng?

Chạy `python scripts/validate_repo.py` để kiểm tra tĩnh. Chạy `docker compose ps`, SQL count query, `sql/07_run_quality_gate.sql` để kiểm tra runtime. Kiểm tra mạnh hơn là reconciliation source/staging/fact, rerun idempotency và controlled DQ failure. Một UI Airflow xanh hoặc Python compile không thay thế những bằng chứng đó.

## Nếu chỉ có 30 phút, tôi nên đọc repo theo thứ tự nào?

1. `reports/foundation-50pct-report.md` (5 phút).
2. `reports/data/brvehins1-eda-summary.md` và `docs/architecture/source-data-contract.md` (10 phút).
3. `docs/architecture/dwh-design.md` và `docs/architecture/staging-design.md` (8 phút).
4. `migrations/V1__create_dwh_schema.sql`, V7, V8 (5 phút).
5. `docs/guides/how-to-run.md` (2 phút).

Nếu có 2 giờ, thêm `scripts/load_brvehins1_to_staging.py`, `scripts/validate_repo.py`, toàn bộ checkpoint theo thứ tự, rồi đối chiếu ML/DAG stale scaffold với DWH contract.

## Khi project lỗi, tôi nên nhìn từ đâu trước?

```text
Raw file/header tồn tại?
  ↓
Source contract khớp?
  ↓
meta.IngestionBatch SUCCESS và staging count đúng?
  ↓
dimensions/fact count đúng?
  ↓
dq.sp_RunQualityGate PASS?
  ↓
chỉ sau đó mới nhìn ML/Airflow downstream
```

Đừng nhảy vào sửa model khi DQ fail, và đừng chạy ingest lại khi batch đã SUCCESS. `meta.IngestionBatch`, `meta.PipelineAudit` và `dq.QualityCheckLog` là ba nơi SQL cần nhìn đầu tiên.

## Trước khi làm Machine Learning, tôi phải hiểu chắc điều gì?

Bạn cần phân biệt **feature** (thông tin được phép dùng trước outcome), **target** (đáp án model cố gắng ước lượng), training/validation split, leakage, baseline, metric, artifact và batch scoring. Với repo này, framing trung thực nhất hiện có là phân loại/risk association trên aggregate observation, không phải “dự đoán claim tương lai của một khách hàng cụ thể”.

Học ngay: grain, target `HasClaim`, cột claim là leakage, split không được để cùng technical record rơi vào hai tập. Có thể học sau: thuật toán phức tạp, tuning, XGBoost/LightGBM. Model tốt trên leakage chỉ là model nhìn đáp án.

## Trước khi học Airflow, tôi phải hiểu pipeline nào trước?

Airflow là nhạc trưởng, không phải nhạc công. Trước Airflow, bạn phải chạy thủ công và hiểu staging check, fact load, DQ và scoring. Nếu một stored procedure lỗi khi chạy tay, đặt nó vào DAG chỉ làm lỗi được lặp lại tự động. DAG cũ chưa được phép xem là pipeline hiện hành.

## Tôi có thật sự hiểu repo chưa?

### Level 1 — cơ bản

1. Dataset canonical là gì? 2. Legacy dataset là gì? 3. Raw có được sửa không? 4. Một source row có phải customer không?

### Level 2 — luồng dữ liệu

5. Loader thêm metadata nào? 6. Staging table tên gì? 7. Làm sao biết file đã xử lý? 8. Reconciliation nghĩa là gì?

### Level 3 — DWH

9. Fact grain là gì? 10. Vì sao không có Dim_Customer? 11. VehicleKey là business ID hay technical key? 12. Vì sao duplicate nguồn không bị xóa?

### Level 4 — runtime/debugging

13. Validator tĩnh không chứng minh điều gì? 14. DQ gate fail thì điều gì nên xảy ra? 15. Xem batch/audit SQL ở đâu? 16. Rerun fact có được thêm row không?

### Level 5 — reasoning

17. Vì sao SCD2 không hợp lệ? 18. Cột claim gây leakage thế nào? 19. Vì sao Airflow chưa runtime pass? 20. Khi README mâu thuẫn report runtime, tin gì trước?

## Đáp án tự kiểm tra

1. Năm `brvehins1[a-e].csv`; SUSEP là legacy. 2. Raw bất biến. 3. Không: nó là aggregate observation. 4. Loader thêm batch/file/ordinal/hash/timestamp. 5. `stg.BrVehIns1`. 6. `meta.IngestionBatch` SUCCESS. 7. So count mỗi lớp. 8. Fact grain là một staging source row. 9. Không có customer identifier/effective history. 10. `VehicleKey` là surrogate key. 11. Duplicate cần preserve lineage. 12. Static validator không chứng minh database/DAG runtime. 13. Gate throw error. 14. Xem `meta.IngestionBatch`, `meta.PipelineAudit`, `dq.QualityCheckLog`. 15. Rerun an toàn thêm 0 row. 16. SCD2 cần identity/history thật. 17. Claim là outcome cùng snapshot. 18. DAG cũ là stub. 19. Runtime evidence + contract cao hơn README cũ.

## Nếu tôi quên gần hết, hãy nhớ 10 điều này

1. `brvehins1`, không phải SUSEP/Porto, là canonical.
2. Raw không bị sửa.
3. Một row không phải customer/policy/event claim.
4. `SourceFile + SourceRowNumber` là identity kỹ thuật.
5. Staging tồn tại để parse, audit và reconcile.
6. Fact là một risk observation; dimensions chỉ là descriptor grouping.
7. 1,965,355 là con số đối chiếu quan trọng nhất.
8. Rerun phải idempotent.
9. DQ gate có quyền dừng pipeline.
10. ML/Airflow cũ chưa phải bằng chứng runtime.

## Tôi đang đứng ở đâu trên roadmap?

```text
Governance → Canonical Data → EDA → Contract → Infrastructure → Staging → DWH → DQ
  DONE          DONE          DONE     DONE        DONE          DONE      DONE   DONE
        → Incremental/CDC → ML → Airflow → Performance → Power BI → Fresh E2E → Portfolio
            NEXT/FUTURE    FUTURE   FUTURE       FUTURE         FUTURE       FUTURE      FUTURE
```

Incremental file behavior đã có ở batch idempotency. CDC, ML và Airflow chưa phải runtime implementation hiện hành.

## Từ điển nhanh khi tôi quên thuật ngữ

**Batch:** một lô xử lý CSV. **CDC:** nhật ký thay đổi database, chưa triển khai thật. **DQ:** kiểm tra chất lượng. **Fact:** bảng measure trung tâm. **Dimension:** mô tả dùng để phân tích. **Grain:** ý nghĩa của một row. **Idempotency:** chạy lại không nhân đôi. **Lineage:** dấu vết nguồn gốc dữ liệu. **Migration:** phiên bản thay đổi database. **Orchestrator:** bộ điều phối task như Airflow. **Reconciliation:** đối chiếu count. **Surrogate key:** key do DWH tạo. **Technical identity:** identity dùng vận hành, không là business ID.

## Tôi có thể kiểm chứng tài liệu này ở đâu?

- Canonical raw và header: `data/raw/brvehins1/`, `scripts/validate_repo.py`.
- EDA/count/duplicate: `reports/data/brvehins1-eda-summary.md`.
- Contract/grain: `docs/architecture/source-data-contract.md`, `data-dictionary.md`.
- Staging: `migrations/V2__create_staging_schema.sql`, `scripts/load_brvehins1_to_staging.py`.
- DWH: `docs/architecture/dwh-design.md`, migrations V6/V7.
- DQ: `migrations/V8__create_data_quality_gate.sql`, `sql/07_run_quality_gate.sql`.
- Runtime evidence: `reports/foundation-50pct-report.md`, `reports/checkpoints/`, `log/progress-log.md`.
- Stale ML/Airflow: `ml/`, `dags/insurance_dwh_pipeline.py`, old numbered `sql/` files.
