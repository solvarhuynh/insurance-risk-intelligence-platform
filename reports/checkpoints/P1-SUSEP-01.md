# P1-SUSEP-01 — EDA và Source Data Contract SUSEP

## Stage này giải quyết vấn đề gì?

Biến một CSV 751 MB thành knowledge có thể triển khai an toàn: schema thật, grain thật và semantic boundary thật cho Track A. Không có bước này, DWH rất dễ lấy nhầm grain hoặc “phát minh” customer/policy.

## Trước stage này project thiếu gì?

Repository biết SUSEP là Track A nhưng chưa có full-file evidence cho row count, duplicate, range, null, grain và policy cho ratio/giá trị âm.

## Agent đã sửa những file nào và tại sao?

- `scripts/profile_susep.py`: profiler streaming bounded-memory; raw không bị sửa.
- `reports/data/susep-profile.json`, `susep-column-profile.csv`, `susep-eda-summary.md`: bằng chứng EDA có thể đọc bằng người/máy.
- `docs/susep/source-data-contract.md`: contract nhận dữ liệu, lineage, precision và ranh giới semantic.
- `docs/susep/data-dictionary.md`: nghĩa/tên/kiểu/null/role của toàn bộ 8 cột.

## Data/code đi qua đâu?

```text
Raw SUSEP CSV (read-only)
  → csv.DictReader streaming + Decimal profile
  → SQLite tạm kiểm tra duplicate/grain
  → JSON/CSV/Markdown evidence
  → contract dùng cho staging loader ở stage kế tiếp
```

## Runtime evidence là gì?

Profiler đã chạy hoàn tất lúc `2026-09-23T13:05:04Z`, mất `3466.546` giây. Nó đọc **8.338.214** dòng, **8** cột và không thay đổi raw file.

## Những con số nào quan trọng?

- Grain duy nhất: `company_code + year_month + product + state`.
- Exact duplicate: **0**; candidate-key duplicate group/excess row: **0 / 0**.
- `company_code`/`company_name`: **196**, không có code-to-name conflict.
- `product`: **144**; `state`: **40**; period: `2003-01-01` → `2023-07-01`.
- Premium âm: **116.980**; claims âm: **301.382** — warning/characteristic, không tự động hard failure.
- Ratio có `NA`: **5.167.094** và giá trị cực trị; giữ riêng, không xem là ratio tái tính/an toàn để cộng.

## Owner cần hiểu khái niệm gì?

**Grain** là độ hạt, tức “một dòng nói về một thứ gì”. Ở đây nó giống một ô tổng hợp theo company-tháng-product-state. **Data contract** là quy ước để loader biết dữ liệu hợp lệ; nó giống checklist nhận hàng trước khi nhập kho.

## Owner chưa cần học gì?

Chưa cần tối ưu index hoặc học ML. Hai việc đó chỉ an toàn khi staging và fact đã giữ đúng grain.

## Owner tự kiểm tra thế nào?

```powershell
.\.venv\Scripts\python.exe scripts\profile_susep.py --help
Get-Content reports\data\susep-eda-summary.md
Get-Content docs\susep\source-data-contract.md
```

Không cần chạy lại full profiler trừ khi raw source đổi, vì lần chạy mất khoảng 58 phút.

## Điều gì có thể nhìn đúng nhưng thực ra sai?

- Header đúng không chứng minh grain đúng; grain chỉ được chứng minh sau duplicate test toàn file.
- `claim_premium_ratio` có tên giống phép chia không chứng minh nó bằng `claims / premiums`.
- Một `DECIMAL(38,29)` nhìn “rất chính xác” nhưng chỉ chứa tối đa 9 chữ số phần nguyên; nó không chứa được toàn bộ source này.

## Stage verdict

**PASS** — schema, volume, full-file uniqueness, measures, dimension candidates và semantic uncertainty đã được chứng minh; không có customer/policy giả.
