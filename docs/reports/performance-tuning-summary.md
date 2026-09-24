# Performance Tuning sẽ chứng minh điều gì?

Trạng thái: future; chưa có benchmark được chứng nhận.

Trọng tâm P1-PERF là **Track A — SUSEP Market DWH** sau khi source contract, ingestion, dimensional model và DQ đã runtime-pass. Đây là nơi source có quy mô market lớn phù hợp để đo workload SQL Server thật.

Mỗi experiment phải ghi business question, query text, data scale, execution plan, STATISTICS IO/TIME, index/physical change, before/after result và write/storage trade-off. Không được gọi performance pass chỉ vì index hoặc SQL file tồn tại.

Track B có thể có risk analytics query riêng, nhưng benchmark của nó không thay thế market-performance evidence. Không làm performance tuning trong P1-ARCH-REALIGN-01.
