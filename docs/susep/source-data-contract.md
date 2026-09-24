# Hợp đồng dữ liệu nguồn — Track A SUSEP

## Stage này giải quyết vấn đề gì?

Tài liệu này chốt **source data contract** (hợp đồng dữ liệu nguồn) cho Track A — SUSEP Market DWH. Contract là lời hứa có thể kiểm tra được giữa CSV gốc và pipeline: file nào được nhận, mỗi dòng mang nghĩa gì, kiểu dữ liệu nào hợp lệ và điều gì phải bị từ chối.

Nó được xây từ file thật `data/raw/susep.gov.br/insurance_dataset.csv`, không suy ra từ thiết kế cũ hay một dataset bảo hiểm khác.

## Một dòng SUSEP thực sự đại diện cho điều gì?

Một dòng là một **market observation** (quan sát thị trường): số premium, claims và ratio nguồn cung cấp của **một company, một tháng, một product và một state**.

Khóa tự nhiên đã được kiểm chứng là:

```text
company_code + year_month + product + state
```

Trên 8.338.214 dòng, khóa này không có duplicate group và không có excess row. Đây là grain của Track A; nó không phải customer, policy, vehicle, exposure hay claim event.

Hãy hình dung một dòng như một ô trong bảng tổng hợp thị trường: “công ty X, tháng 2020-01, sản phẩm Y, bang SP”. Nó không cho biết một người mua bảo hiểm cụ thể nào.

## File nào là canonical source?

| Thuộc tính | Giá trị đã quan sát |
|---|---|
| Path | `data/raw/susep.gov.br/insurance_dataset.csv` |
| Kích thước | 751.126.569 bytes |
| Số dòng dữ liệu | 8.338.214 |
| Header | 8 cột, đúng thứ tự bên dưới |
| Khoảng thời gian | 2003-01-01 đến 2023-07-01 |
| Duplicate dòng đầy đủ | 0 |
| Candidate-grain duplicate | 0 |

Header bắt buộc, theo đúng thứ tự:

```text
company_code,company_name,year_month,product,state,premiums,claims,claim_premium_ratio
```

Raw CSV là immutable (bất biến). Loader chỉ đọc tuần tự; không sửa, di chuyển hoặc ghi đè file này.

## Quy tắc nhận dữ liệu là gì?

| Nhóm | Hard contract (vi phạm sẽ bị reject) | Data characteristic / warning |
|---|---|---|
| File/schema | File tồn tại, không rỗng, header chính xác | — |
| Định danh | `company_code` là `INT`; company/name, month, product, state phải có | Không suy diễn company thành customer |
| Thời gian | `year_month` là ngày ISO hợp lệ và là ngày đầu tháng | Khoảng ngày hiện có chỉ là evidence, không phải giới hạn vĩnh viễn |
| Financial lexical value | `premiums`, `claims` parse được thành số hữu hạn; không null | Giá trị âm được giữ lại và cần xem xét nghiệp vụ, không tự động reject |
| Ratio nguồn | `NA` được map thành `NULL`; giá trị khác phải parse được thành số hữu hạn | Có số âm/cực trị; không coi là phép chia đáng tin để tái tính hay cộng dồn |
| Grain | Không được có trùng `(company_code, year_month, product, state)` trong accepted staging | Rule này là hard DQ sau load |

`Hard contract` giống như kiểm tra vé hợp lệ trước khi vào rạp: không có vé hoặc sai vé thì không được vào. `Warning` giống biển nhắc nhở: giá trị âm có thể là điều chỉnh kế toán có thật, cần điều tra nhưng không thể tự ý xóa nó.

## State được giữ và dùng thế nào?

Raw/staging giữ nguyên lexical value của `state`: profiling thấy 40 value phân biệt chữ hoa/thường. Trong đó 27 mã bang Brazil viết hoa là canonical và có 103 row variant chữ thường (`Al`, `am`, `ba`, …). Market DWH dùng `UPPER(state)` để map deterministically về 27 `DimSusepState` code; không tạo region hierarchy và không làm mất source lineage vì stage/fact vẫn giữ source row fingerprint. Đây là normalization của cùng một state code, không phải fake cross-source mapping.

## Vì sao raw numeric text và analytic numeric cùng tồn tại?

SUSEP chứa giá trị có tối đa 10 chữ số phần nguyên và tối đa 29 chữ số phần lẻ (ở các dòng khác nhau). SQL Server giới hạn `DECIMAL` ở precision 38, nên không có một `DECIMAL(p,s)` đơn lẻ nào giữ được mọi tổ hợp lexical đó ở độ chính xác đầy đủ.

Vì vậy staging và fact có hai representation:

1. `PremiumsRaw`, `ClaimsRaw`, `ClaimPremiumRatioRaw`: chuỗi nguồn nguyên vẹn, là bằng chứng/audit source of truth.
2. `Premiums`, `Claims`, `ClaimPremiumRatio`: `DECIMAL(38,18)` đã làm tròn half-even có kiểm soát, dùng cho tổng hợp SQL và BI.

Pipeline ghi rõ sai số làm tròn tối đa theo từng giá trị nhỏ hơn hoặc bằng `0.5 × 10^-18`; reconciliation analytic dùng tolerance đã công bố. Không được gọi cột numeric là bản sao lexical hoàn hảo của raw.

## Lineage và idempotency hoạt động ra sao?

Mỗi accepted/rejected record có `BatchId`, `SourceFile`, `SourceFileSha256`, `SourceRowNumber`, `SourceRecordHash` và timestamp. `SourceFile + SourceFileSha256 + SourceRowNumber` là technical identity, không phải business key.

Loader lấy application lock, kiểm tra batch `SUCCESS` cùng fingerprint trước khi nạp và có unique index cho technical identity. Rerun cùng file vì thế trả về `SKIPPED`, không nhân đôi staging. Nếu batch lỗi giữa chừng, staging của batch không thành công được dọn có kiểm soát trong lần retry, dưới cùng lock.

## Bằng chứng nào tạo contract này?

Chương trình streaming [profile_susep.py](../../scripts/profile_susep.py) đã đọc toàn bộ CSV bằng `csv.DictReader`, dùng `Decimal` để profile và SQLite tạm để kiểm tra grain/duplicate. Kết quả máy đọc được nằm tại:

- [susep-profile.json](../../reports/data/susep-profile.json)
- [susep-eda-summary.md](../../reports/data/susep-eda-summary.md)
- [susep-column-profile.csv](../../reports/data/susep-column-profile.csv)

## Điều gì trông có vẻ đúng nhưng thực ra sai?

- `claim_premium_ratio` không được giả định bằng `claims / premiums`: source có `NA`, giá trị âm và extreme value.
- Không cộng ratio giữa các dòng. Khi cần ratio dẫn xuất, chỉ tính `SUM(Claims) / NULLIF(SUM(Premiums), 0)` và phải nêu rõ denominator có thể âm/0.
- Không tạo `CustomerId`, `PolicyId`, VIN hay exposure vì schema không cung cấp.
- Không join row-level Track A với brvehins1 hoặc Prudential. Chúng chỉ cùng platform, không chung identity.
