# P1-ORCH-02 — Airflow runtime và controlled failure

## Stage này giải quyết vấn đề gì?

Chứng minh DAG chạy thật khi dữ liệu hợp lệ và phản ứng đúng khi một DQ gate fail có kiểm soát. Đây là khác biệt giữa sơ đồ luồng và hệ thống vận hành: như thử cả nút “start” lẫn phanh khẩn cấp.

## Trước stage này project thiếu gì?

Chưa có run id, task state, duration hay bằng chứng failure propagation từ Airflow runtime. Parse/static check không thay thế những bằng chứng này.

## Agent đã sửa những file nào?

- `dags/insurance_dwh_pipeline.py`: sửa quality-gate task để consume result sets và để SQL `THROW` thành task failure thật.
- `reports/checkpoints/P1-ORCH-01.md`, file này: lưu architecture và runtime evidence.

## Valid run evidence

| Thuộc tính | Giá trị |
|---|---|
| DAG | `insurance_data_platform` |
| Run ID | `44294f58-1808-4cd8-8a22-2c90687bf321` |
| State | `success` |
| Start → end UTC | 2026-09-24 01:01:15 → 01:06:48 |
| Wall duration | khoảng 5 phút 33 giây |
| Task states | đủ 12/12 task `success` |

Track A thực hiện source-version ingest (rerun-safe), market DWH, direct reconciliation và DQ. Track B thực hiện precheck, incremental audit, DQ, batch score và prediction reconciliation. Không có task failed/skipped ở valid run.

## Controlled failure evidence

| Thuộc tính | Giá trị |
|---|---|
| Run ID | `0d2f017a-1f52-46b2-9671-2f1e3d95f488` |
| Conf | `{"controlled_track_a_dq_failure": true}` |
| DAG state | `failed` — expected |
| Start → end UTC | 2026-09-24 01:18:06 → 01:30:49 |
| Wall duration | khoảng 12 phút 43 giây |
| `track_a_data_quality_gate` | `failed` — expected; one configured retry means two failed attempts |
| `track_a_market_consumer_ready` | `upstream_failed` — expected |
| `track_b_risk_consumer_ready` | `success` — expected independent branch |

Các task upstream Track A (ingest, market DWH, reconciliation) đều `success`. Track B precheck, incremental audit, DQ, scoring và prediction reconciliation đều `success`. Procedure thêm `CONTROLLED_INVALID_INPUT` chỉ trong memory/log DQ, rồi `THROW`; raw/staging/fact canonical không bị mutate.

## Data/code đi qua đâu?

DQ Track A là cổng cuối sau reconciliation. Khi conf inject test row, procedure trả hard failure; pyodbc drain result set nên Airflow nhận exception. Consumer Track A không được chạy, trong khi Track B không bị dependency giả nên hoàn thành bình thường.

## Owner cần hiểu khái niệm gì?

- **Happy path:** valid input đi hết pipeline.
- **Controlled failure:** lỗi được chủ động tạo theo cách an toàn để kiểm tra phanh.
- **Upstream failed:** task không chạy vì prerequisite fail; đây là hành vi bảo vệ đúng.

## Owner tự kiểm tra thế nào?

```powershell
docker compose exec -T airflow airflow tasks states-for-dag-run insurance_data_platform 0d2f017a-1f52-46b2-9671-2f1e3d95f488
docker compose exec -T airflow airflow dags list-runs -d insurance_data_platform --output plain --no-backfill
```

## Điều gì có thể nhìn đúng nhưng thực ra sai?

Một run `success` không kiểm tra failure propagation. Ngược lại, DAG run `failed` ở controlled test không phải platform regression nếu exact intended DQ task fail, downstream đúng nhánh bị block và independent branch vẫn success.

## Stage verdict

**PASS.** Valid run hoàn thành; controlled Track-A DQ failure được propagate chính xác, downstream Track A bị chặn và Track B độc lập vẫn thành công.
