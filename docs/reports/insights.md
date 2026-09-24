# Insight nghiệp vụ được tổ chức theo track thế nào?

Trạng thái: chưa có report insight business đã được phê duyệt.

Track B đã có DWH/DQ runtime evidence, nhưng report này không tự suy ra insight chỉ vì table tồn tại. Nếu tạo risk analytics, phải ghi rõ aggregate-risk grain và không diễn giải thành customer/policy behavior.

Track A sẽ là nơi tạo market analytics sau P1-SUSEP-01 đến P1-SUSEP-05: premium/claims theo company, month, product và state chỉ được báo cáo khi contract xác nhận grain, units và ratio semantics.

Không join SUSEP với brvehins1 để tạo insight. Nếu một báo cáo đặt hai track cạnh nhau, nguồn, metric, time range và non-comparability phải được ghi rõ.
