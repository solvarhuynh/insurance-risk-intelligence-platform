# Data dictionary — SUSEP Market DWH

## Đọc bảng này như thế nào?

**Source dtype** là hình dạng quan sát trong CSV. **SQL staging type** là nơi pipeline lưu dữ liệu. **Analytical role** nói cột dùng làm dimension, measure hay lineage; nó không tự tạo một entity chưa có trong source.

| Source field | Ý nghĩa theo evidence | Source dtype | SQL staging type | Null / validation policy | Analytical role |
|---|---|---|---|---|---|
| `company_code` | Mã company của SUSEP | integer-like text | `INT` | Bắt buộc, parse `INT`, không null; 196 giá trị | Natural key của `DimSusepCompany` |
| `company_name` | Tên company nguồn | text | `NVARCHAR(116)` | Bắt buộc; max quan sát 116; phải nhất quán 1 code → 1 name | Thuộc tính company dimension |
| `year_month` | Tháng quan sát, biểu diễn bằng ngày đầu tháng | ISO date text | `DATE` | Bắt buộc; ISO date hợp lệ, day = 1 | Natural key của `DimSusepMonth` |
| `product` | Nhãn/mã product nguồn | text | `NVARCHAR(42)` | Bắt buộc; max quan sát 42; 144 giá trị | Natural key của `DimSusepProduct` |
| `state` | Mã geography 2 ký tự do source cung cấp | text | `NVARCHAR(2)` | Bắt buộc; max quan sát 2; 40 lexical values gồm 103 lowercase variants; DWH map `UPPER(state)` về 27 mã canonical, không tạo region hierarchy | Source field và canonical key của `DimSusepState` |
| `premiums` | Financial measure premium từ source | decimal text | Raw `NVARCHAR(100)` + analytic `DECIMAL(38,18)` | Bắt buộc, finite decimal; âm được giữ, không hard reject | Additive measure có điều kiện; tổng phải đọc cùng period/dimension |
| `claims` | Financial measure claims từ source | decimal text | Raw `NVARCHAR(100)` + analytic `DECIMAL(38,18)` | Bắt buộc, finite decimal; âm được giữ, không hard reject | Additive measure có điều kiện |
| `claim_premium_ratio` | Ratio do source cung cấp | decimal text hoặc `NA` | Raw `NVARCHAR(100)` nullable + analytic `DECIMAL(38,18)` nullable | `NA` → `NULL`; value khác phải finite decimal; âm/extreme được giữ | Non-additive source-provided measure; không tự tái tính/aggregate |

## Các con số cần nhớ

| Field | Null | Đặc điểm/range quan sát |
|---|---:|---|
| `premiums` | 0 | Min `-224022539.61`, max `2598854052.42`, 116.980 dòng âm |
| `claims` | 0 | Min `-4162417826.88`, max `5323648483.83`, 301.382 dòng âm |
| `claim_premium_ratio` | 5.167.094 | 3.171.120 numeric; min `-6590560657819567`, max `19804447419966428`; 238.088 dòng âm |

## Derived measure nào được phép?

`Derived market loss ratio` chỉ là một measure mới có nhãn riêng:

```sql
SUM(Claims) / NULLIF(SUM(Premiums), 0)
```

Nó khác `ClaimPremiumRatio` của source. Hãy nghĩ ratio như “tốc độ trung bình”: không thể cộng tốc độ của từng xe rồi gọi đó là tốc độ của cả đoàn. Với premium/claims âm, báo cáo phải cho biết scope và xử lý denominator zero/negative.

## Những entity nào không có trong dictionary?

Không có `Customer`, `Policy`, `Vehicle`, VIN, exposure hoặc claim event. Việc có company không đồng nghĩa company là policy holder/customer. Vì vậy star schema Track A chỉ có month, company, product, state và fact market observation.
