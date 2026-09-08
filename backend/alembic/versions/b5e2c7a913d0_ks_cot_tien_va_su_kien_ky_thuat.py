"""K1, K2, K6 – sổ rà soát cột tiền và sổ sự kiện kỹ thuật của robot Kiểm soát.

Hai bảng, cả hai đều là dấu vết của robot chứ KHÔNG phải dữ liệu nghiệp vụ:
  - ks_cot_tien       : một dòng cho mỗi cột số thực trong mô hình. Robot đề xuất "là tiền / không phải
                        tiền / chưa rõ", người xác nhận. Có bảng này thì câu "số cột sai kiểu giảm dần
                        qua từng đợt sửa" mới đo được, và cột đã có người quyết thì lần quét sau không
                        hỏi lại.
  - su_kien_ky_thuat  : lỗi 5xx, đường dẫn chậm bất thường, tác vụ nền thất bại, lần khởi động máy chủ.
                        Gom theo mã ổn định và đếm số lần – một endpoint hỏng gọi một nghìn lần phải là
                        một dòng, không phải một nghìn dòng.

Revision ID: b5e2c7a913d0
Revises: c9d8e7f6a5b4
"""
from alembic import op
import sqlalchemy as sa

revision = "b5e2c7a913d0"
down_revision = "c9d8e7f6a5b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    co = set(sa.inspect(op.get_bind()).get_table_names())

    if "ks_cot_tien" not in co:
        op.create_table(
            "ks_cot_tien",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bang", sa.String(80), nullable=False),
            sa.Column("cot", sa.String(80), nullable=False),
            sa.Column("kieu", sa.String(40), nullable=False, server_default=""),
            sa.Column("xep_may", sa.String(12), nullable=False, server_default="chua_ro"),
            sa.Column("ly_do_may", sa.String(200), nullable=False, server_default=""),
            sa.Column("quyet_nguoi", sa.String(12), nullable=False, server_default=""),
            sa.Column("quyet_boi", sa.String(50), nullable=False, server_default=""),
            sa.Column("quyet_luc", sa.DateTime(), nullable=True),
            sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
            sa.Column("cho_rong", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("mac_dinh_0", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("quyet_k2", sa.String(6), nullable=False, server_default=""),
            sa.Column("quyet_k2_boi", sa.String(50), nullable=False, server_default=""),
            sa.Column("quyet_k2_luc", sa.DateTime(), nullable=True),
            sa.Column("lan_dau", sa.DateTime(), nullable=True),
            sa.Column("lan_cuoi", sa.DateTime(), nullable=True),
            sa.Column("con", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.UniqueConstraint("bang", "cot", name="uq_ks_cot_tien_bang_cot"),
        )
        op.create_index("ix_ks_cot_tien_bang", "ks_cot_tien", ["bang"])
        op.create_index("ix_ks_cot_tien_con", "ks_cot_tien", ["con"])

    if "su_kien_ky_thuat" not in co:
        op.create_table(
            "su_kien_ky_thuat",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ma", sa.String(200), nullable=False, unique=True),
            sa.Column("loai", sa.String(16), nullable=False),
            sa.Column("muc", sa.String(6), nullable=False, server_default="vang"),
            sa.Column("duong_dan", sa.String(200), nullable=False, server_default=""),
            sa.Column("phuong_thuc", sa.String(8), nullable=False, server_default=""),
            sa.Column("ma_trang_thai", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mili_giay", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("vai_tro", sa.String(30), nullable=False, server_default=""),
            sa.Column("thong_bao", sa.Text(), nullable=False, server_default=""),
            sa.Column("dau_vet", sa.Text(), nullable=False, server_default=""),
            sa.Column("so_lan", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("lan_dau", sa.DateTime(), nullable=True),
            sa.Column("lan_cuoi", sa.DateTime(), nullable=True),
            sa.Column("da_bao", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("chi_tiet", sa.JSON(), nullable=True),
        )
        op.create_index("ix_su_kien_ky_thuat_ma", "su_kien_ky_thuat", ["ma"], unique=True)
        op.create_index("ix_su_kien_ky_thuat_loai", "su_kien_ky_thuat", ["loai"])
        op.create_index("ix_su_kien_ky_thuat_lan_cuoi", "su_kien_ky_thuat", ["lan_cuoi"])
        op.create_index("ix_su_kien_ky_thuat_lan_dau", "su_kien_ky_thuat", ["lan_dau"])


def downgrade() -> None:
    op.drop_table("su_kien_ky_thuat")
    op.drop_table("ks_cot_tien")
