# -*- coding: utf-8 -*-
"""Phòng HDV Đợt 1 — bảng yêu cầu HDV, và hai mốc giờ cho phân công.

VÌ SAO BẢNG MỚI: hôm nay chuỗi phòng HDV bắt đầu thẳng từ `guide_assignments`, tức từ lúc ĐÃ chọn
được người. Chuyến chưa xếp được ai thì không nằm ở đâu cả, nên câu "tuần sau bao nhiêu chuyến chưa
có hướng dẫn viên" không hỏi được — cái thiếu không tồn tại trong cơ sở dữ liệu.

VÌ SAO THÊM GIỜ VÀO PHÂN CÔNG: Chủ tịch chốt 06/10/2026 cấm xếp một hướng dẫn viên vào hai chuyến
chồng giờ. Bảng chỉ có `days` là một SỐ NGUYÊN — không có hai đầu mốc thì không có gì để so. Lệnh
điều xe đã có `date_from/date_to` từ lâu, nên tám tuần qua hệ thống chặn được một chiếc xe bị đặt hai
lần mà không chặn được một con người.

RỖNG VẪN LÀ RỖNG — ba cột giờ đều NULL được và KHÔNG có mặc định. Suy giờ từ ngày khởi hành của tour
thì mỗi phân công cũ đều có một khoảng trông như thật, xếp gọn trên màn hình lãnh đạo, và không ai
còn nhớ đó là số đoán. Bản ghi cũ giữ nguyên trống và hiện ở danh sách việc còn thiếu
(`GET /api/v1/guide-requests/thieu`).

KHÔNG DÙNG RÀNG BUỘC LOẠI TRỪ THEO KHOẢNG (exclusion constraint) để chặn trùng, dù Postgres có:
bộ phép thử chạy trên SQLite, nơi không có ràng buộc ấy. Viết một hàng rào chỉ sống ở máy chủ thật
thì phép thử sẽ XANH trong khi thực tế vẫn hỏng — đúng loại lỗi tệ nhất. Hàng rào đặt ở tầng dịch vụ
(`app/services/hdv.py`): khoá hàng trước khi ghi, đếm lại sau khi ghi và trước khi chốt giao dịch.
Cách ấy chạy đúng trên cả hai, và phép thử bắt được nó.

ĐỔI NGƯỢC ĐƯỢC: `downgrade` xoá bảng và bốn cột. Mất dữ liệu yêu cầu và giờ đã gõ — không khôi phục
được từ chỗ nào khác, nên chỉ chạy khi thật sự muốn bỏ Đợt 1.

Revision ID: hdv1a4c7e2b9f
Revises: tx1f3a9c2e5b
"""
import sqlalchemy as sa
from alembic import op

revision = "hdv1a4c7e2b9f"
down_revision = "tx1f3a9c2e5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "yeu_cau_hdv",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("so_hdv", sa.Integer(), server_default="1"),
        sa.Column("bat_dau", sa.DateTime(), nullable=True),
        sa.Column("ket_thuc", sa.DateTime(), nullable=True),
        sa.Column("ngoai_ngu", sa.String(60), server_default=""),
        sa.Column("nang_luc", sa.String(200), server_default=""),
        sa.Column("diem_hen", sa.String(200), server_default=""),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("han_phan_hoi", sa.DateTime(), nullable=True),
        sa.Column("trang_thai", sa.String(16), server_default="moi"),
        sa.Column("ly_do_huy", sa.String(200), server_default=""),
        sa.Column("nguoi_lap", sa.String(50), server_default=""),
        sa.Column("lap_luc", sa.DateTime(), nullable=True),
        sa.Column("sua_boi", sa.String(50), server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_yeu_cau_hdv_tour_id", "yeu_cau_hdv", ["tour_id"])
    op.create_index("ix_yeu_cau_hdv_company_id", "yeu_cau_hdv", ["company_id"])
    op.create_index("ix_yeu_cau_hdv_bat_dau", "yeu_cau_hdv", ["bat_dau"])
    op.create_index("ix_yeu_cau_hdv_trang_thai", "yeu_cau_hdv", ["trang_thai"])
    op.create_index("ix_yeu_cau_hdv_trang_thai_bat_dau", "yeu_cau_hdv", ["trang_thai", "bat_dau"])

    # `phien_ban` có mặc định 1 vì nó là BỘ ĐẾM, không phải một con số nghiệp vụ: một bản ghi cũ chưa
    # ai sửa thì đang ở bản thứ nhất, không phải "chưa biết ở bản nào". Ba cột giờ thì ngược lại —
    # KHÔNG mặc định, vì "chưa ai gõ giờ" phải phân biệt được với một giờ nào đó.
    with op.batch_alter_table("guide_assignments") as b:
        b.add_column(sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"))
        b.add_column(sa.Column("yeu_cau_id", sa.Integer(), sa.ForeignKey("yeu_cau_hdv.id"), nullable=True))
        b.add_column(sa.Column("bat_dau", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("ket_thuc", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("vai_tro", sa.String(10), server_default="chinh"))
        b.add_column(sa.Column("gio_boi", sa.String(50), server_default=""))
        b.add_column(sa.Column("gio_luc", sa.DateTime(), nullable=True))
    op.create_index("ix_guide_assignments_bat_dau", "guide_assignments", ["bat_dau"])
    op.create_index("ix_guide_assignments_yeu_cau_id", "guide_assignments", ["yeu_cau_id"])


def downgrade() -> None:
    op.drop_index("ix_guide_assignments_yeu_cau_id", table_name="guide_assignments")
    op.drop_index("ix_guide_assignments_bat_dau", table_name="guide_assignments")
    with op.batch_alter_table("guide_assignments") as b:
        for c in ("gio_luc", "gio_boi", "vai_tro", "ket_thuc", "bat_dau", "yeu_cau_id", "phien_ban"):
            b.drop_column(c)
    for ix in ("ix_yeu_cau_hdv_trang_thai_bat_dau", "ix_yeu_cau_hdv_trang_thai",
               "ix_yeu_cau_hdv_bat_dau", "ix_yeu_cau_hdv_company_id", "ix_yeu_cau_hdv_tour_id"):
        op.drop_index(ix, table_name="yeu_cau_hdv")
    op.drop_table("yeu_cau_hdv")
