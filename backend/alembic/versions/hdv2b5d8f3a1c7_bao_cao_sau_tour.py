# -*- coding: utf-8 -*-
"""Phòng HDV Đợt 2 — bảng báo cáo sau tour, có phiên bản và có vòng kiểm.

TRƯỚC BẢN NÀY BÁO CÁO SAU TOUR LÀ MỘT Ô ĐÁNH DẤU. `guide_assignments.report_submitted` kiểu đúng/sai,
chú thích cạnh nó ghi "báo cáo tour 4 phần" — nội dung đã được nghĩ ra từ lâu mà chưa có chỗ chứa.
Một ô đánh dấu thì ai cũng tick được và tick rồi thì không ai đọc lại được gì, trong khi cột ấy đang
gánh hai quyết định thật: treo chào chuyến mới sau 3 ngày, và treo thù lao.

CỘT CŨ KHÔNG BỊ BỎ — nó thành tấm gương của bảng mới, bật khi báo cáo được XÁC NHẬN và tắt khi bị
trả lại. Hai chỗ đang dùng nó không phải sửa một dòng. Bỏ cột thì hai chỗ ấy im lặng ngừng chạy.

GỬI RỒI THÌ KHOÁ, SỬA LÀ BẢN MỚI (`ban_so`, `thay_cho_id`, `bi_thay`). Báo cáo là căn cứ để quyết
toán và để trả thù lao; sửa đè lên bản đã gửi thì người kiểm đã đọc một bản còn hệ thống giữ một bản
khác, và không ai biết.

`so_khach_thuc_te` NULL được và KHÔNG có mặc định: "chưa đếm" khác "đi 0 khách". Mặc định 0 thì mọi
báo cáo chưa điền đều thành một chuyến không khách, và con số ấy đi thẳng vào đối chiếu với booking.
`han_nop` cũng NULL được: chuyến chưa có ngày kết thúc thì không đoán hạn, vì một hạn bịa ra sẽ sinh
cảnh báo trễ cho người chưa hề trễ.

Revision ID: hdv2b5d8f3a1c7
Revises: hdv1a4c7e2b9f
"""
import sqlalchemy as sa
from alembic import op

revision = "hdv2b5d8f3a1c7"
down_revision = "hdv1a4c7e2b9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bao_cao_sau_tour",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("guide_assignments.id"), nullable=False),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("guide_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("chuong_trinh_thuc_hien", sa.Text(), server_default=""),
        sa.Column("so_khach_thuc_te", sa.Integer(), nullable=True),
        sa.Column("danh_gia_ncc", sa.Text(), server_default=""),
        sa.Column("su_co", sa.Text(), server_default=""),
        sa.Column("khoan_chi_thu_ho", sa.Text(), server_default=""),
        sa.Column("viec_chua_xong", sa.Text(), server_default=""),
        sa.Column("ban_so", sa.Integer(), server_default="1"),
        sa.Column("thay_cho_id", sa.Integer(), sa.ForeignKey("bao_cao_sau_tour.id"), nullable=True),
        sa.Column("bi_thay", sa.Boolean(), server_default="0"),
        sa.Column("trang_thai", sa.String(16), server_default="nhap"),
        sa.Column("han_nop", sa.Date(), nullable=True),
        sa.Column("nguoi_nop", sa.String(50), server_default=""),
        sa.Column("nop_luc", sa.DateTime(), nullable=True),
        sa.Column("nguoi_kiem", sa.String(50), server_default=""),
        sa.Column("kiem_luc", sa.DateTime(), nullable=True),
        sa.Column("y_kien_kiem", sa.Text(), server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    for ten, cot in (("assignment_id", ["assignment_id"]), ("tour_id", ["tour_id"]),
                     ("guide_id", ["guide_id"]), ("company_id", ["company_id"]),
                     ("trang_thai", ["trang_thai"]), ("han_nop", ["han_nop"])):
        op.create_index(f"ix_bao_cao_sau_tour_{ten}", "bao_cao_sau_tour", cot)
    op.create_index("ix_bao_cao_sau_tour_assignment_trang_thai", "bao_cao_sau_tour",
                    ["assignment_id", "trang_thai"])


def downgrade() -> None:
    for ten in ("assignment_trang_thai", "han_nop", "trang_thai", "company_id",
                "guide_id", "tour_id", "assignment_id"):
        op.drop_index(f"ix_bao_cao_sau_tour_{ten}", table_name="bao_cao_sau_tour")
    op.drop_table("bao_cao_sau_tour")
