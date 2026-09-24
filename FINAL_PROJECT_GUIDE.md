# Hướng dẫn cuối dự án — Insurance Data Platform

## Tôi đang xây hệ thống gì?

Đây là một **Insurance Data Platform**: một platform dữ liệu bảo hiểm có nhiều dây chuyền phân tích độc lập. Hãy hình dung một nhà ga có nhiều tuyến tàu. Các tuyến dùng chung nhà ga, bảo vệ và bảng điều khiển, nhưng toa tàu của tuyến này không tự nhiên ghép được với tuyến khác.

- **Track A — SUSEP Market DWH / Performance:** biến CSV thị trường thành market warehouse, kiểm tra chất lượng và tối ưu các truy vấn lớn.
- **Track B — brvehins1 Motor Risk / ML:** biến năm CSV motor-risk thành risk warehouse, chạy DQ, reload model đã xác thực, score một population giới hạn và đối soát prediction.
- **Track C — Prudential:** chỉ là ý định ban đầu. Không có data vật lý nên trạng thái là `ORIGINAL_PLANNED_SOURCE / NOT_PRESENT / FUTURE`.

## Vì sao project có nhiều data track?

Một dataset không tự động là “bản mở rộng” của dataset khác. Mỗi track có **grain** (mức ý nghĩa của một row) riêng.

| Track | Một row nghĩa là gì? | Identity đáng tin |
|---|---|---|
| A — SUSEP | Một quan sát market theo `company_code + year_month + product + state` | Bốn field business này, cùng source lineage kỹ thuật |
| B — brvehins1 | Một aggregate motor-risk observation từ partition nguồn | `SourceFile + SourceRowNumber` |

Grain giống đơn vị trên hóa đơn: một bảng ghi doanh thu theo cửa hàng-tháng không thể tự nối với bảng ghi tổng quan sát rủi ro xe chỉ vì cả hai cùng nói về bảo hiểm.

## Vì sao SUSEP và brvehins1 không join nhau?

Không có key thật được source chứng minh. Repository không có customer ID, policy ID, VIN hay event mapping chung. Nếu tự tạo `CustomerId` hoặc mapping, kết quả có thể nhìn hợp lý nhưng là dữ liệu bịa. Hai track chỉ được tích hợp ở mức platform: cùng SQL Server, cùng cách audit/DQ, cùng Airflow và cùng repo; không ở mức row-level.

## Track A — SUSEP làm gì?

1. Đọc file raw immutable `data/raw/susep.gov.br/insurance_dataset.csv` theo streaming/chunk.
2. Ghi row hợp lệ vào `stg.SusepInsuranceMarket` kèm `BatchId`, file hash, source row number/hash; giữ reject/audit riêng.
3. Tạo bốn dimension month/company/product/state và một market fact.
4. Đối soát source → staging → fact về row và premium/claims.
5. Chạy `dq.sp_RunSusepQualityGate`; warning được giữ riêng với hard failure.
6. Dùng fact lớn để đo `STATISTICS IO/TIME` và thử index có căn cứ.

Kết quả runtime chính: **8.338.214** raw rows = staging accepted rows = fact rows. Premium và claims reconcile xuyên ba lớp.

## Một row SUSEP đi xuyên hệ thống thế nào?

```text
CSV row
  → loader kiểm tra schema/parse và gắn source lineage
  → stg.SusepInsuranceMarket
  → lookup DimSusepMonth, DimSusepCompany, DimSusepProduct, DimSusepState
  → dwh.FactSusepInsuranceMarket
  → reconciliation + DQ
  → query/performance hoặc Market BI subject area
```

Premiums và Claims ở cùng fact vì cùng một market observation. `claim_premium_ratio` nguồn là non-additive: không cộng nó khi roll-up; hãy tính `SUM(Claims) / SUM(Premiums)` với guard denominator trong SQL/DAX.

## Track B — brvehins1 làm gì?

1. Nạp năm partition immutable vào `stg.BrVehIns1` với technical identity.
2. Nạp `DimDriverProfile`, `DimVehicle`, `DimGeography` và `dwh.FactRiskObservation` one-to-one từ staging.
3. Chạy Track-B DQ và incremental audit.
4. Reload `ml/artifacts/claim_risk_model_v001.joblib` bằng declared `.venv` có scikit-learn 1.7.2.
5. Score held-out population 20.000 rows vào `dwh.RiskObservationPrediction`, rồi kiểm tra không duplicate identity.

Một row Track B không phải một policy/customer. Model mô tả **cross-sectional association** với `HasClaim` trên aggregate risk observation; nó không dự đoán claim tương lai cho một người hay policy.

## DWH của hai track khác nhau ra sao?

Track A có star schema theo market dimensions (thời gian, company, product, state). Track B có star schema theo risk descriptors (driver, vehicle, geography). Cùng có fact/dimension không đồng nghĩa chung dimension hoặc chung fact. Xem sơ đồ đầy đủ trong [overall architecture](docs/architecture/overall-architecture.md).

## DQ bảo vệ từng track thế nào?

**Data Quality gate (DQ)** là cổng kiểm tra trước downstream, như trạm soát vé: sai điều kiện cứng thì không qua được.

- Track A kiểm tra schema, batch reconciliation, required fields, month, business grain, company mapping, fact/FK/lineage, dimension uniqueness và direct reconciliation.
- Track B kiểm tra contract/range/identity, staging–fact reconciliation và prediction contract.

**Hard failure** chặn DAG. **Warning** lưu một đặc tính cần review nhưng không tự coi là lỗi: ví dụ premium/claims âm có thể là accounting adjustment; source ratio `NA` trở thành NULL được ghi nhận. Controlled failure của Track A chỉ thêm row kiểm thử trong memory procedure và không sửa raw/staging/fact.

## Incremental và CDC nghĩa là gì ở đây?

**Incremental ingestion** là chỉ nạp source version mới; fingerprint source giúp rerun file cũ thành `SKIPPED` thay vì duplicate. **Synthetic CDC** ở Track B là bài thực hành change-data-capture có kiểm soát để chứng minh pattern kỹ thuật, không phải khẳng định raw CSV là stream thay đổi thật. Đừng dùng chữ CDC để che một full reload.

## ML nằm ở đâu và học gì?

ML chỉ nằm trong Track B sau DQ. Artifact được train trên deterministic bounded population vì local resource có giới hạn. Target là `HasClaim = TotalClaimCount > 0`; các claim amount/count bị loại khỏi feature để tránh **data leakage** — đưa đáp án vào input.

Chỉ số held-out đã lưu: ROC-AUC **0,808815**, PR-AUC **0,513523**. Chúng nói về khả năng xếp hạng association trong contract hiện tại, không nói model nhân quả, công bằng pricing hay probability claim tương lai.

## Airflow điều phối hai track thế nào?

Airflow chạy hai đường ray song song: Track A ingest → DWH → reconciliation → DQ; Track B precheck → incremental audit → DQ → score → prediction reconciliation. Không có task giả tạo join hai track.

Nếu Track A DQ được inject failure, consumer Track A bị `upstream_failed`; Track B vẫn hoàn thành theo policy độc lập. Đây là một failure propagation test, không phải lỗi dữ liệu thật.

## Performance Tuning chứng minh điều gì?

Trên fact SUSEP 8,3 triệu row, Q1 company/month giảm logical reads từ **317.528 xuống 3.364** (−98,94%); Q2 state/product/month giảm từ **317.528 xuống 3.734** (−98,82%). Hai covering index được giữ; source-hash trial không giúp query nên bị drop. Xem [performance report](reports/performance-report.md). Một index lớn cũng làm insert chậm và tốn storage — đó là trade-off thật.

## Power BI hiển thị hai subject area thế nào?

Power BI phải có hai page/model tách biệt:

- **Insurance Market:** fact SUSEP + bốn dimension, premium/claims/derived market ratio.
- **Motor Risk / ML:** FactRiskObservation + risk dimensions + prediction theo existing technical contract.

Không tạo cross-filter/bridge giữa hai subject area. Semantic design và lệnh build tay có trong [semantic model](docs/bi/semantic-model.md) và [Power BI handoff](powerbi/README.md). Chưa có Power BI Desktop/PBIP runtime trong repo, nên `.pbix` thật và refresh là `BLOCKED_MANUAL`.

## Nếu lỗi thì debug từ đâu?

Đi theo data flow, không đoán:

1. **Raw/source lỗi:** kiểm tra file presence/header/hash, không chỉnh raw để “cho qua”.
2. **Ingestion lỗi:** đọc batch audit và reject table; so sánh expected = accepted + rejected.
3. **DWH lỗi:** đối chiếu stage row/fact row, dimension lookup/FK và source lineage.
4. **DQ lỗi:** xem `dq.*QualityCheckLog`, rule name, observed/expected; phân biệt hard failure và warning.
5. **ML lỗi:** dùng `.venv\Scripts\python.exe`, kiểm tra artifact version/metadata, rồi prediction identity.
6. **Airflow lỗi:** xem task state/log; downstream bị block là expected khi upstream hard-fail.
7. **BI mismatch:** so SQL reconciliation trước, rồi measure/relationship trong đúng subject area.

## Tôi nên demo project ra sao?

1. Mở README và overall architecture để nói rõ multi-track/no fake join.
2. Demo Track A: source contract, batch idempotency, 8.338.214 reconciliation, DQ và performance report.
3. Demo Track B: 1.965.355 staging=fact, bounded ML contract, artifact reload và 20.000 prediction reconciliation.
4. Demo Airflow valid run và controlled failure run; chỉ ra Track B vẫn thành công khi Track A DQ bị inject failure.
5. Mở semantic model/Power BI README và nói rõ phần manual blocker thay vì giả dashboard.

## Tôi nên trình bày trong interview thế nào?

Nói theo bằng chứng và trade-off: “Tôi thiết kế một platform hai track với grain độc lập, nên từ chối fake joins. Tôi xây full-file SUSEP market DWH có source-to-fact reconciliation và tối ưu hai workload từ ~317k xuống ~3–4k logical reads. Tôi giữ Track B risk/ML riêng, với model bounded-resource để không giả vờ train full dataset. Tôi kiểm tra Airflow cả happy path lẫn failure propagation, và minh bạch Power BI cần manual GUI artifact.”

## 30 câu tự kiểm tra và đáp án

1. **Platform này có một canonical dataset duy nhất không?** Không; A và B đều `ACTIVE_CANONICAL` trong track riêng.
2. **Một row SUSEP nghĩa là gì?** Company-tháng-product-state market observation.
3. **Một row brvehins1 có phải customer/policy không?** Không; đó là aggregate risk observation.
4. **Vì sao không join A với B?** Không có proven shared business key.
5. **Raw file có được sửa để test không?** Không; raw immutable/read-only.
6. **Track A staging table tên gì?** `stg.SusepInsuranceMarket`.
7. **Track A fact table tên gì?** `dwh.FactSusepInsuranceMarket`.
8. **Track B fact table tên gì?** `dwh.FactRiskObservation`.
9. **Technical identity Track B là gì?** `SourceFile + SourceRowNumber`.
10. **Track A có bao nhiêu raw/fact row đã reconcile?** 8.338.214.
11. **Track B staging/fact smoke count là bao nhiêu?** 1.965.355 mỗi lớp.
12. **SUSEP ratio nguồn có được SUM không?** Không; nó non-additive.
13. **Derived market ratio tính thế nào?** `SUM(Claims) / SUM(Premiums)` có guard mẫu số.
14. **Hard failure khác warning thế nào?** Hard failure chặn downstream; warning được log để review.
15. **Premium âm có luôn là invalid không?** Không; current contract ghi nó là source characteristic warning.
16. **Idempotency của SUSEP ingestion là gì?** Rerun source fingerprint đã SUCCESS trả `SKIPPED`, không thêm row.
17. **ML có retrain trong Airflow routine không?** Không.
18. **Artifact Track B cần environment nào để reload?** Declared `.venv` với scikit-learn 1.7.2.
19. **ML target là gì?** `HasClaim`, derived từ `TotalClaimCount > 0`.
20. **Vì sao claim amount không làm ML feature?** Vì post-outcome leakage.
21. **Population scoring Track B hiện tại bao nhiêu row?** 20.000 held-out rows.
22. **Prediction reconciliation kiểm tra gì?** Count và duplicate technical identity theo population/model contract.
23. **Airflow valid run chứng minh gì?** Task thật đã chạy, không chỉ DAG parse.
24. **Controlled Airflow failure chứng minh gì?** SQL DQ error được propagate và chỉ đúng downstream bị block.
25. **Q1 performance cải thiện reads ra sao?** 317.528 → 3.364, giảm 98,94%.
26. **Tại sao source-hash index bị drop?** Không giúp workload và thêm storage/write cost.
27. **Power BI có relationship giữa A/B không?** Không.
28. **Tại sao chưa có `.pbix`?** Không có Power BI Desktop/PBIP automation được hỗ trợ; không được fake file.
29. **Prudential đang ở trạng thái nào?** `ORIGINAL_PLANNED_SOURCE / NOT_PRESENT / FUTURE`.
30. **Khi một report nói PASS, cần hỏi gì?** PASS của static check hay runtime check, input nào, count/metric nào và evidence nằm ở đâu?

## Đọc tiếp theo thứ tự nào?

1. `README.md` và `docs/architecture/overall-architecture.md`.
2. `docs/susep/source-data-contract.md`, `docs/susep/dwh-design.md`, checkpoints `P1-SUSEP-*`.
3. `docs/architecture/source-data-contract.md`, `docs/ml/ml-data-contract.md`, checkpoints `P1-ML-*`.
4. `reports/performance-report.md`, `P1-PERF-*`, `P1-ORCH-*`.
5. `docs/bi/semantic-model.md` và `powerbi/README.md` cho phần manual handoff.
