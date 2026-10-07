"""Chi kỳ lương: bảng chi_ky_luong, và hai cột tóm tắt trên payroll_runs

Đợt A2 – khúc cuối của chuỗi Chủ tịch chốt 07/10/2026: sau chữ ký và khóa bản chụp thì kế toán CHI,
tải Ủy nhiệm chi lên, máy đối chiếu với bản đã ký, rồi ghi nhận ĐÃ TRẢ (đủ / một phần / lỗi).

HAI CỘT THÊM VÀO `payroll_runs` LÀ BẢN TÓM, KHÔNG PHẢI BẢN GỐC. Bản gốc là các dòng `chi_ky_luong`;
hai cột ấy tồn tại để báo cáo đọc được trạng thái trả tiền mà không phải nối bảng, và chúng chỉ được
ghi trong cùng giao dịch với nơi sinh ra chúng (services/chi_luong.py::ghi_nhan). Cột `tra_trang_thai`
RỖNG nghĩa là chưa chi lần nào – khác hẳn "đã chi 0 đồng", nên không có server_default nào khác rỗng.

Revision ID: cl2b8e4f1a7d3
Revises: lk1a7f3c9e2b4
"""
from alembic import op
import sqlalchemy as sa

revision = "cl2b8e4f1a7d3"
down_revision = "lk1a7f3c9e2b4"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2, asdecimal=False)


def upgrade() -> None:
    op.create_table(
        "chi_ky_luong",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("period", sa.String(7), nullable=False, index=True),
        # Trỏ tới BẢN CHỤP ĐÃ KÝ, không trỏ tới kỳ lương: kỳ còn đổi được, bản chụp thì không.
        sa.Column("ban_khoa_id", sa.Integer, sa.ForeignKey("bang_luong_khoa.id"), nullable=False),
        sa.Column("lan", sa.Integer, server_default="1"),
        sa.Column("unc_attachment_id", sa.Integer, sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("ngan_hang", sa.String(60), server_default=""),
        # Tài khoản TRÍCH TIỀN của công ty. Không phải tài khoản người lao động – phụ lục có số tài
        # khoản người nhận thì máy vẫn bỏ, xem models/doc_chung_tu.py::MO_DOC_CO_CHU_KY.
        sa.Column("tai_khoan_cong_ty", sa.String(40), server_default=""),
        sa.Column("ngay_chuyen", sa.Date, nullable=True),
        sa.Column("so_tham_chieu", sa.String(80), server_default=""),
        # K2: RỖNG nghĩa là máy chưa đọc được, KHÔNG phải số 0. Không có server_default.
        sa.Column("so_tien_unc", TIEN, nullable=True),
        sa.Column("noi_dung_unc", sa.String(300), server_default=""),
        sa.Column("phu_luc_attachment_id", sa.Integer, sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("dong_phu_luc", sa.JSON),
        sa.Column("phu_luc_ai_run_id", sa.Integer, nullable=True),
        sa.Column("phu_luc_ghi_chu", sa.Text, server_default=""),
        sa.Column("ket_luan", sa.String(12), server_default=""),
        sa.Column("ket_qua", sa.JSON),
        sa.Column("doi_chieu_luc", sa.DateTime, nullable=True),
        sa.Column("chi_boi", sa.String(50), server_default=""),
        sa.Column("chi_vai", sa.String(30), server_default=""),
        sa.Column("luc", sa.DateTime),
    )
    op.create_index("ix_chi_ky_luong_ky_lan", "chi_ky_luong", ["period", "lan"], unique=True)
    op.create_index("ix_chi_ky_luong_ban_khoa", "chi_ky_luong", ["ban_khoa_id"])
    op.create_index("ix_chi_ky_luong_ket_luan", "chi_ky_luong", ["ket_luan"])

    op.add_column("payroll_runs", sa.Column("tra_trang_thai", sa.String(16), server_default=""))
    op.add_column("payroll_runs", sa.Column("tra_luc", sa.DateTime, nullable=True))


def downgrade() -> None:
    op.drop_column("payroll_runs", "tra_luc")
    op.drop_column("payroll_runs", "tra_trang_thai")
    op.drop_index("ix_chi_ky_luong_ket_luan", table_name="chi_ky_luong")
    op.drop_index("ix_chi_ky_luong_ban_khoa", table_name="chi_ky_luong")
    op.drop_index("ix_chi_ky_luong_ky_lan", table_name="chi_ky_luong")
    op.drop_table("chi_ky_luong")
