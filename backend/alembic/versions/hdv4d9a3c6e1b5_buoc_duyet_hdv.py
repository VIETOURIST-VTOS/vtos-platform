# -*- coding: utf-8 -*-
"""Phòng HDV Đợt 4 — đề xuất của phòng và bước duyệt có cấp (đặc tả v1.0 §10–§12).

ĐỢT NÀY DỰNG CÁI MÁY, KHÔNG ĐẶT CON SỐ. Loại hồ sơ nào, hạn mức bao nhiêu, ai duyệt — đó là chính
sách phê duyệt và phải có người ký. Bảng `cau_hinh_duyet_hdv` sinh ra RỖNG, cố ý.

THIẾU CẤU HÌNH THÌ CHẶN TRÌNH, KHÔNG CHO BỎ CẤP. Lấy nguyên §10. Nếu thiếu cấu hình mà vẫn cho trình
thì hệ thống phải tự chọn một đường đi — và đường nó chọn sẽ thành tiền lệ: không ai ký mà vẫn thành
luật, và tới lúc phát hiện thì đã có hàng chục hồ sơ đi theo đường ấy. Chặn thì có người đi hỏi, và
câu trả lời được ghi lại thành một dòng cấu hình có chữ ký.

KHÔNG GIẢ ĐỊNH TGĐ VÀ CHỦ TỊCH THAY NHAU. §10 nói rõ: "không giả định hai người thay nhau hoặc hồ sơ
nào cũng cần cả hai". Nên cấp duyệt lưu thành MỘT DANH SÁCH CÓ THỨ TỰ (`cac_cap`), mỗi cấp một vai
trò; muốn hai người cùng ký một cấp thì khai hai cấp. Không có đường tắt nào trong mã.

`den_so_tien` RỖNG = KHÔNG CÓ TRẦN, không phải "chưa biết": một khoảng thiếu trần sẽ để lọt mọi hồ sơ
lớn hơn mức cao nhất đã khai — đúng những hồ sơ cần cấp cao nhất. `so_tien` của đề xuất cũng rỗng
được, vì có đề xuất không mang tiền (xin bổ sung nhân sự); rỗng khác 0 và phép chọn cấu hình phân
biệt hai cái.

CÁC BƯỚC LẬP ĐỦ NGAY LÚC TRÌNH, không sinh dần. Lập sẵn thì người trình thấy cả đường đi trước khi
gửi và ai cũng đọc được hồ sơ còn qua mấy cửa; sinh dần thì mỗi lần chỉ biết cửa kế tiếp, và không ai
trả lời được "bao giờ xong".

Revision ID: hdv4d9a3c6e1b5
Revises: hdv3c7e1b4f8a2
"""
import sqlalchemy as sa
from alembic import op

revision = "hdv4d9a3c6e1b5"
down_revision = "hdv3c7e1b4f8a2"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "cau_hinh_duyet_hdv",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loai", sa.String(20), nullable=False),
        sa.Column("tu_so_tien", TIEN, nullable=True),
        sa.Column("den_so_tien", TIEN, nullable=True),
        sa.Column("cac_cap", sa.String(200), server_default=""),
        sa.Column("hieu_luc_tu", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(12), server_default="cho_ky"),
        sa.Column("ky_boi", sa.String(120), server_default=""),
        sa.Column("ky_luc", sa.DateTime(), nullable=True),
        sa.Column("ghi_chu", sa.String(200), server_default=""),
        sa.Column("lap_boi", sa.String(50), server_default=""),
        sa.Column("lap_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_cau_hinh_duyet_hdv_loai", "cau_hinh_duyet_hdv", ["loai"])
    op.create_index("ix_cau_hinh_duyet_hdv_trang_thai", "cau_hinh_duyet_hdv", ["trang_thai"])

    op.create_table(
        "de_xuat_hdv",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ma", sa.String(30), nullable=False, unique=True),
        sa.Column("loai", sa.String(20), nullable=False),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("guide_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("ky", sa.String(7), server_default=""),
        sa.Column("noi_dung", sa.Text(), server_default=""),
        sa.Column("ly_do", sa.Text(), server_default=""),
        sa.Column("can_cu_tinh", sa.Text(), server_default=""),
        sa.Column("so_tien", TIEN, nullable=True),
        sa.Column("loai_tien", sa.String(3), server_default="VND"),
        sa.Column("han_xu_ly", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(14), server_default="nhap"),
        sa.Column("cap_dang_cho", sa.Integer(), server_default="0"),
        sa.Column("cau_hinh_id", sa.Integer(), sa.ForeignKey("cau_hinh_duyet_hdv.id"), nullable=True),
        sa.Column("nguoi_lap", sa.String(50), server_default=""),
        sa.Column("lap_luc", sa.DateTime(), nullable=True),
        sa.Column("trinh_luc", sa.DateTime(), nullable=True),
        sa.Column("xong_luc", sa.DateTime(), nullable=True),
    )
    for ten in ("ma", "loai", "tour_id", "guide_id", "company_id", "trang_thai"):
        op.create_index(f"ix_de_xuat_hdv_{ten}", "de_xuat_hdv", [ten])

    op.create_table(
        "buoc_duyet_hdv",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("de_xuat_id", sa.Integer(),
                  sa.ForeignKey("de_xuat_hdv.id", ondelete="CASCADE"), nullable=False),
        sa.Column("thu_tu", sa.Integer(), server_default="1"),
        sa.Column("vai_tro", sa.String(60), nullable=False),   # nhiều vai thay thế nhau, ngăn bằng `|`
        sa.Column("trang_thai", sa.String(14), server_default="cho"),
        sa.Column("nguoi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.Column("y_kien", sa.Text(), server_default=""),
    )
    op.create_index("ix_buoc_duyet_hdv_de_xuat_id", "buoc_duyet_hdv", ["de_xuat_id"])
    op.create_index("ix_buoc_duyet_hdv_trang_thai", "buoc_duyet_hdv", ["trang_thai"])
    op.create_index("ix_buoc_duyet_hdv_de_xuat_thu_tu", "buoc_duyet_hdv", ["de_xuat_id", "thu_tu"])


def downgrade() -> None:
    for ten in ("de_xuat_thu_tu", "trang_thai", "de_xuat_id"):
        op.drop_index(f"ix_buoc_duyet_hdv_{ten}", table_name="buoc_duyet_hdv")
    op.drop_table("buoc_duyet_hdv")
    for ten in ("trang_thai", "company_id", "guide_id", "tour_id", "loai", "ma"):
        op.drop_index(f"ix_de_xuat_hdv_{ten}", table_name="de_xuat_hdv")
    op.drop_table("de_xuat_hdv")
    op.drop_index("ix_cau_hinh_duyet_hdv_trang_thai", table_name="cau_hinh_duyet_hdv")
    op.drop_index("ix_cau_hinh_duyet_hdv_loai", table_name="cau_hinh_duyet_hdv")
    op.drop_table("cau_hinh_duyet_hdv")
