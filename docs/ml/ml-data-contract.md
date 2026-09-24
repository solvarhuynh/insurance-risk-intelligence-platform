# Hợp đồng dữ liệu ML Track B — P1-ML-01

Trạng thái: `DONE` cho bản minh họa cross-sectional ngày 2026-09-23.

## 1. Bài toán trung thực

Model ước lượng mối liên hệ quan sát được với `HasClaim` của một **aggregate
insurance risk observation** — quan sát rủi ro bảo hiểm tổng hợp — dựa trên mô
tả driver, vehicle và geography không phải outcome. Đây là bài toán phân loại
cross-sectional và minh họa batch inference.

Model **không** dự đoán claim tương lai của một customer hoặc policy xác định.
Source không có customer ID, policy ID, transaction time hoặc prediction-time
snapshot đã được chứng minh. Không được diễn giải probability thành xác suất
claim tương lai của một policy cá nhân.

## 2. Input canonical và identity

Input duy nhất **của Track B** là view warehouse hiện hành, tạo bằng cách join
`dwh.FactRiskObservation` với `DimDriverProfile`, `DimVehicle` và
`DimGeography`. SUSEP không được đọc trong extraction này vì thuộc Track A
Market DWH độc lập; điều đó không hạ canonical status của SUSEP.

Technical row identity là `(SourceFile, SourceRowNumber)`. Group key để cô lập
split là `SourceRecordHash`: các record có cùng logical source serialization
phải nằm trong cùng một split. Cách này chặt hơn việc chỉ giữ technical row ở
một split và ngăn logical duplicate rò rỉ giữa train, validation và test.

## 3. Target

```text
HasClaim = 1 khi TotalClaimCount > 0
HasClaim = 0 khi TotalClaimCount = 0
```

`TotalClaimCount` là tổng đã được DQ kiểm tra của năm cột `ClaimNb*`. DQ gate
hiện tại kiểm tra count không âm và tính nhất quán của cặp count/amount. Vì
vậy target được hỗ trợ như outcome của observed snapshot, không phải nhãn của
một event tương lai.

Phân bố live DWH ngày 2026-09-23:

| Class | Rows | Tỷ lệ |
|---|---:|---:|
| `HasClaim = 1` | 363,076 | 18.473813% |
| `HasClaim = 0` | 1,602,279 | 81.526187% |
| Tổng | 1,965,355 | 100% |

Đây là bài toán **class imbalance** — mất cân bằng lớp: model luôn trả “không
claim” có thể trông như đạt 81.5% accuracy nhưng không xếp hạng tốt các dòng
có claim.

## 4. Phân loại field và leakage policy

| Field/group | Phân loại | Quyết định baseline | Lý do |
|---|---|---|---|
| `Gender` | PRE_OUTCOME_FEATURE | Dùng | Mô tả source; giữ missing. `Corporate` vẫn là nhãn source, không tự gọi là giới tính. |
| `DrivAge` | PRE_OUTCOME_FEATURE | Dùng | Nhóm tuổi, xử lý dạng categorical. |
| `VehYear` | PRE_OUTCOME_FEATURE | Dùng | Mô tả xe, xử lý categorical; NULL/0 giữ nguyên. |
| `VehModel` | PRE_OUTCOME_FEATURE | Dùng | Mô tả xe; one-hot hỗ trợ 4,259 giá trị quan sát. |
| `VehGroup` | PRE_OUTCOME_FEATURE | Dùng | Mô tả xe. |
| `Area` | PRE_OUTCOME_FEATURE | Dùng | Mô tả địa lý. |
| `State` | PRE_OUTCOME_FEATURE | Loại khỏi estimator | Trùng mapping một-một với `StateAb`; vẫn giữ để audit. |
| `StateAb` | PRE_OUTCOME_FEATURE | Dùng | Mô tả địa lý gọn. |
| `ExposTotal`, `ExposFireRob` | EXPOSURE_OR_PRICING_REVIEW | Loại | Chưa rõ có sẵn ở prediction time; fire/rob constant zero. |
| `PremTotal`, `PremFireRob` | EXPOSURE_OR_PRICING_REVIEW | Loại | Chưa chứng minh timing so với outcome; fire/rob constant zero. |
| `SumInsAvg` | EXPOSURE_OR_PRICING_REVIEW | Loại | Chưa chứng minh timing/quan hệ với outcome. |
| mọi `ClaimNb*` | TARGET_DERIVED / POST_OUTCOME_LEAKAGE | Loại | Trực tiếp tạo target. |
| mọi `ClaimAmount*` | POST_OUTCOME_LEAKAGE | Loại | Mô tả cùng outcome claim đã quan sát. |
| `TotalClaimCount`, `TotalClaimAmount` | TARGET_DERIVED / POST_OUTCOME_LEAKAGE | Loại | Derived từ outcome. |
| `HasClaim` | TARGET | Chỉ làm target | Không đưa vào preprocessing/estimator. |
| `ClaimFrequency`, `LossRatio` | POST_OUTCOME_LEAKAGE | Loại | Tử số chứa claim outcome. |
| file, row, batch, hash, surrogate key, timestamp | TECHNICAL/AUDIT | Loại | Chỉ dùng lineage, reproducibility và split check. |

## 5. Chiến lược split

Không có event time nên chronological split sẽ tự bịa semantics. Preparation
dùng `StratifiedGroupKFold(n_splits=5, shuffle=True,
random_state=20260923)` trên `HasClaim`, group là `SourceRecordHash`.

- Fold 0 là test giữ lại.
- Fold 1 là validation.
- Fold 2–4 là training.

Cách này xấp xỉ 60%/20%/20%, deterministic, giữ technical record trong một
split và giữ logical duplicate cùng nhau. Dataset stage ghi exact count và
xác nhận không có group đi qua nhiều split.

## 6. Hợp đồng preprocessing

Tất cả input được chọn là categorical. `SimpleImputer(strategy="most_frequent")`
và `OneHotEncoder(handle_unknown="ignore")` chỉ fit trên training rows bên
trong scikit-learn `Pipeline`. Validation/test dùng transformer đã fit từ
training, không học lại từ chính chúng.

## 7. Phiên bản dữ liệu

Extraction cần source contract `docs/architecture/source-data-contract.md`,
migrations V1–V8, production DQ pass và reconciliation hiện tại của
`FactRiskObservation` với 1,965,355 rows. Script model ghi Git revision và
working-tree state vào metadata artifact.

## Cần hiểu gì?

- **Feature** → thông tin đưa cho model; giống manh mối có trước quyết định.
- **Target** → đáp án model cần liên hệ; ở đây là `HasClaim` quan sát được,
  không phải event customer tương lai.
- **Data leakage** → đưa một phần đáp án vào input; `ClaimAmount*` là leakage
  vì chỉ biết nó sau khi outcome đã biết.
- **Train/validation/test** → sách luyện, bài kiểm tra thử và bài thi niêm
  phong. Chọn/fitting trên train; so sánh model bằng validation; test chỉ mở
  ở báo cáo cuối.

## Chưa được suy luận gì

Contract này không chứng minh causality, suitability cho pricing công bằng,
future claim prediction, production threshold hoặc customer-level risk score.

## 8. Chiến lược thực thi có giới hạn tài nguyên — P1-ML-02 đến P1-ML-05

Lần thử trước materialize feature frame của toàn bộ 1,965,355 dòng và process
đạt khoảng 0.92 GB working set trước khi host dừng nó. Đây là giới hạn thực tế
của môi trường local, không phải lý do để đổi target hay đưa leakage vào model.

Vì vậy model hiện dùng population deterministic gồm 18,474 positive và 81,526
negative `SourceRecordHash` groups (100,004 rows sau khi giữ duplicate group
đầy đủ). Source hash được rank ổn định trong từng class tại SQL Server, rồi
`StratifiedGroupKFold` vẫn tạo train/validation/test theo policy ở trên. Không
có hash đi qua ranh giới split.

Scale được kiểm tra tiến dần với 4,000, 24,000 và 60,000 training rows. Sparse
one-hot `float32`, một process SGD logistic-loss hoặc ComplementNB, không
cross-validation/grid search và không dense encoded matrix được dùng. Đây là
minh họa ML có giới hạn tài nguyên; không phải mô hình fit trên toàn bộ DWH.
