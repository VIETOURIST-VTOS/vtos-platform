"""Sổ tỷ giá – tỷ giá ngoại tệ từng ngày, do người nhập, có chứng từ đi kèm

Revision ID: tg9c4e1a7b52d8
Revises: kh1b6d4e8a2f37
Create Date: 2026-09-16

MỘT bảng mới, KHÔNG sửa bảng nào đang có – nên bản này lùi lại được sạch.

Chủ tịch chốt 16/9/2026: *"tỷ giá để nhân viên tự nhập tại từng thời điểm; tạo form để nhân viên tự
nhập tay và tải tệp/ảnh."*

VÌ SAO PHẢI LÀ BẢNG, KHÔNG PHẢI MỘT DÒNG THAM SỐ

Tỷ giá không phải một con số của công ty – nó là một con số của MỖI NGÀY, và có khi mỗi ngày có hơn
một con số. Đo được:

    Tệp quyết toán UK: HAI tỷ giá GBP trong CÙNG MỘT TỆP – 36.000 ở sheet chiết tính và 35.944 ở
    sheet quyết toán. Trên giá land 692,34 GBP × 43 khách, 56 đồng chênh ấy là 1.667.155 đ.

    21 tệp quyết toán visa T1–T6/2026: tỷ giá nằm rải trong ô đầu bảng mỗi tệp một chỗ – CAD 19.000,
    USD 25.500, AUD 18.500 – và không tệp nào ghi tỷ giá ấy lấy từ đâu, ngày nào.

`params` là sổ chính sách một dòng một con số. Một bảng tỷ giá theo ngày và theo nguồn không nhét
vào đấy được.

BA ĐIỀU TRONG LƯỢC ĐỒ, VÀ LÝ DO

1. `ty_gia` là Numeric(18, 6), KHÔNG phải kiểu TIEN. `app/models/kieu_tien.py` nói rõ: TIEN chỉ cho
   cột tiền, không cho tỷ lệ. Hai chữ số thập phân của TIEN cắt mất tỷ giá đồng tiền yếu – 1 KRW
   ≈ 0,0181 đ, làm tròn thành 0,02 là sai 10%.

2. Chỉ mục DUY NHẤT trên (tien_te, ngay, nguon) chứ không trên (tien_te, ngay). Hai nguồn khác nhau
   trong cùng một ngày được phép khác nhau và PHẢI khác nhau: "Vietcombank bán ra" và "tỷ giá thực
   tế đã chuyển khoản" là hai sự thật, gộp làm một là bịa ra một sự thật thứ ba.

   Đặt bằng CHỈ MỤC chứ không bằng ràng buộc trên cột: SQLite (máy lập trình) không thêm ràng buộc
   vào bảng đã tạo, chỉ mục thì cả hai môi trường đều tạo được – nên hai bên chạy cùng lược đồ.

3. KHÔNG có cột boolean nào trong bảng này. Nếu về sau thêm, nhớ `sa.false()` chứ KHÔNG phải
   `sa.text("0")`: PostgreSQL từ chối `DEFAULT 0` cho cột BOOLEAN và cả lệnh `alembic upgrade head`
   dừng ở đấy – container không khởi động được. SQLite thì nhận, nên bộ thử ở máy (dùng create_all,
   không chạy migration) không bao giờ thấy. Đã xảy ra thật ngày 14/9/2026.
"""
import sqlalchemy as sa
from alembic import op

revision = "tg9c4e1a7b52d8"
down_revision = "kh1b6d4e8a2f37"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ty_gia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tien_te", sa.String(length=3), nullable=False),
        # NGÀY CỦA TỶ GIÁ, không phải ngày nhập. Tỷ giá dùng cho một khoản là tỷ giá ngày chi thật
        # của khoản ấy – Chủ tịch chốt 11/9/2026.
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("ty_gia", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("nguon", sa.String(length=60), nullable=True, server_default=""),
        sa.Column("loai_gia", sa.String(length=20), nullable=True, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=True, server_default=""),
        # Ai nhập. Tỷ giá là con số NHÂN vào tiền – phải biết người chịu trách nhiệm cho nó.
        sa.Column("nguoi_nhap", sa.String(length=50), nullable=True, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
        # Từng lần sửa, nối thêm chứ không ghi đè: số cũ, số mới, ai sửa, lúc nào, lý do.
        sa.Column("lich_su", sa.Text(), nullable=True, server_default=""),
        sa.Column("so_lan_sua", sa.Integer(), nullable=True, server_default="0"),
    )
    op.create_index("ix_ty_gia_tra_cuu", "ty_gia", ["tien_te", "ngay"])
    op.create_index("ux_ty_gia_mot_nguon_mot_ngay", "ty_gia",
                    ["tien_te", "ngay", "nguon"], unique=True)


def downgrade():
    op.drop_index("ux_ty_gia_mot_nguon_mot_ngay", table_name="ty_gia")
    op.drop_index("ix_ty_gia_tra_cuu", table_name="ty_gia")
    op.drop_table("ty_gia")
