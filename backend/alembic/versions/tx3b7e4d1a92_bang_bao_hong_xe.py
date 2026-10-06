# -*- coding: utf-8 -*-
"""Bảng BÁO HƯ HỎNG XE `fleet_faults` — Chủ tịch chọn 06/10/2026.

VÌ SAO LÀ MỘT BẢNG RIÊNG, KHÔNG PHẢI MỘT ĐỀ NGHỊ CHI

Lúc tài xế phát hiện xe hỏng thì chưa có số tiền và chưa chọn garage — hai thứ cửa lập đề nghị chi
bắt buộc phải có. Nhét báo hỏng vào đề nghị chi là bắt tài xế bịa hai con số, đúng thứ ranh giới
09/9/2026 cấm. Đề nghị sửa chữa (loại chi `sua_chua_xe`, PR #195) do Giám đốc đội xe lập SAU khi có
báo giá, và nối ngược về đây bằng `maintenance_id`.

VÌ SAO KHÔNG DÙNG LẠI `fleet_maintenance`

Bảng ấy ghi việc ĐÃ LÀM: ngày làm, garage, số tiền, km lúc làm. Báo hỏng ghi việc CHƯA LÀM GÌ CẢ.
Gộp hai thứ vào một bảng thì mọi báo cáo chi phí bảo dưỡng phải nhớ lọc bỏ những dòng chưa có tiền —
và cái "phải nhớ" ấy là chỗ mọi con số đội xe bắt đầu sai.

HAI MỨC, KHÔNG PHẢI NĂM

`muc_do` chỉ có `con_chay_duoc` và `phai_dung_xe`. Câu hỏi duy nhất người điều xe cần trả lời ngay là
"chiếc xe này tối nay còn chạy được không". Một thang năm mức nghe chuyên nghiệp hơn nhưng không ai
trả lời nổi lúc đang đứng bên đường, và mức ở giữa thì không ai biết nên điều hay không.

KHÔNG CÓ DỮ LIỆU CŨ ĐỂ CHUYỂN. Bảng mới hoàn toàn; `downgrade` xoá bảng và mất mọi báo hỏng đã ghi.

Revision ID: tx3b7e4d1a92
Revises: tx1f3a9c2e5b
"""
import sqlalchemy as sa
from alembic import op

revision = "tx3b7e4d1a92"
down_revision = "tx1f3a9c2e5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fleet_faults",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False, index=True),
        sa.Column("nguoi_bao_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True, index=True),
        sa.Column("bao_luc", sa.DateTime(), nullable=True),
        sa.Column("hien_tuong", sa.String(300), nullable=False),
        sa.Column("muc_do", sa.String(20), nullable=False, server_default="con_chay_duoc"),
        sa.Column("odo_km", sa.Integer(), nullable=True),
        sa.Column("noi_xay_ra", sa.String(160), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(20), nullable=False, server_default="moi"),
        sa.Column("tiep_nhan_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("tiep_nhan_luc", sa.DateTime(), nullable=True),
        sa.Column("ket_qua", sa.String(300), nullable=False, server_default=""),
        sa.Column("dong_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("dong_luc", sa.DateTime(), nullable=True),
        sa.Column("maintenance_id", sa.Integer(), sa.ForeignKey("fleet_maintenance.id"), nullable=True),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # Mất toàn bộ báo hỏng đã ghi. Không có đường khôi phục — chúng không nằm ở bảng nào khác.
    op.drop_table("fleet_faults")
