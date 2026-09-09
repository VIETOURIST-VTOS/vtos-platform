"""K2 phần bù: 8 cột tiền còn lại được PHÉP rỗng – những cột danh sách K2 đi ngang qua

Revision ID: zf6a7b8c9d0e
Revises: ze5f6a7b8c9d
"""
from alembic import op

revision = "zf6a7b8c9d0e"
down_revision = "ze5f6a7b8c9d"
branch_labels = None
depends_on = None

# Vì sao có bản này, và vì sao đáng ghi lại thay vì lặng lẽ gộp vào bản trước:
#
# K2 làm 83 cột rồi tuyên bố xong. Sổ rà soát cột tiền của Robot Kiểm soát – chạy trên máy chủ thật,
# ngay sau khi triển khai – trả lời: 107 cột là tiền, 94 đã cho rỗng, CÒN 8 CỘT vẫn vừa mặc định 0 vừa
# không cho rỗng. Tám cột ấy nằm ngay cạnh những cột K2 vừa sửa: trong bảng quyết toán đội xe,
# `doi_tac_huong` và `doi_tac_chiu` còn nguyên trong khi `doanh_thu` và `dieu_chinh` sát bên đã đổi.
#
# Lý do bỏ sót: danh sách 83 cột được dựng từ nhóm "đã cho rỗng ở CSDL nhưng mặc định 0 nuốt mất" –
# tức là đã nửa đường. Tám cột này chặt hơn một bậc: khai `Mapped[float]`, NOT NULL thật ở CSDL, chưa
# nửa bước nào. Câu truy vấn dựng danh sách hỏi "cột nào cho rỗng mà vẫn mặc định 0", nên chúng không
# lọt vào lưới. Danh sách sai không phải vì máy đếm nhầm, mà vì CÂU HỎI hẹp hơn vấn đề.
#
# Điều đáng giữ lại: cái tìm ra chỗ sót không phải một lượt rà mã nữa, mà là hỏi HỆ THỐNG ĐANG CHẠY
# xem nó thấy gì. Sổ rà soát đọc thẳng từ mô hình trên máy chủ, nên nó không thừa hưởng giả định nào
# của người viết danh sách.
#
# Bản này chỉ nới ràng buộc, KHÔNG đụng một dòng dữ liệu nào – như bản trước.

COT = (
    ("fleet_repayment_plans", "moi_ky"),
    ("fleet_settlements", "chuyen_ky_sau"),
    ("fleet_settlements", "doi_tac_chiu"),
    ("fleet_settlements", "doi_tac_huong"),
    ("guide_assignments", "rate_per_day"),
    ("guide_rates", "old_rate_per_day"),
    ("guide_rates", "rate_per_day"),
    ("vehicles", "internal_rate_per_day"),
)


def upgrade() -> None:
    for bang, cot in COT:
        op.execute(f'ALTER TABLE {bang} ALTER COLUMN {cot} DROP NOT NULL')


def downgrade() -> None:
    """CHỈ CHẠY ĐƯỢC khi chưa có dòng nào rỗng, và đó là chủ ý.

    Nếu đã có dòng rỗng, lệnh này DỪNG với lỗi của PostgreSQL. Không được phép âm thầm điền 0 để đặt
    lại NOT NULL: làm thế là biến "nhân viên chưa nhập" thành "đơn giá bằng 0" – dựng lại đúng chỗ mù
    mà K2 sinh ra để xoá, và lần này xoá luôn bằng chứng rằng nó từng rỗng.
    """
    for bang, cot in COT:
        op.execute(f'ALTER TABLE {bang} ALTER COLUMN {cot} SET NOT NULL')
