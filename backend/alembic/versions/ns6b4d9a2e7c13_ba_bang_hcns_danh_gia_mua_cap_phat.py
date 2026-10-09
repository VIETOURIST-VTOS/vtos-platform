"""Ba bảng HCNS trong MỘT migration: 5.6 Đánh giá nhân sự, 5.9.2 Đề nghị mua, 5.9.3 Cấp phát tài sản.

Chủ tịch chốt 08–09/10/2026. Gom ba bảng vào một bản là có chủ ý: ngày 14/9/2026 một migration đã
chặn deploy một lần, và bốn làn đang cùng đẩy lên một nhánh chính — hai đầu migration mở song song
thì alembic có HAI head và container không khởi động được. Ba lần đụng rút còn một.

CẢ BA BẢNG TẠO RA RỖNG. Không chèn một dòng dữ liệu nào: ranh giới 09/9/2026 — phần mềm viết cấu
trúc và phép tính, số liệu do người của các phòng tự nhập hoặc tải lên. Hệ quả là mỗi bảng ở đây
phải có một CỬA NHẬP trên màn hình, và vòng này dựng cả ba cửa ấy.

KHÔNG CÓ CỘT TIỀN TRONG BẢNG ĐÁNH GIÁ, và đó là phần quan trọng nhất của bản này. Chủ tịch chốt
09/10/2026: điểm chỉ để XÉT thưởng, TGĐ/Chủ tịch quyết mức tiền từng người bằng tay. Nên không một
dòng mã nào biến điểm thành tiền — không có công thức nào để lách, và không có chuyện phần mềm trả
thưởng sai mà không ai ký. Ngày nào muốn nối thẳng thì đó là một quyết định MỚI, có chữ ký, chứ
không phải một lần thêm cột cho tiện.

`down_revision` đo lại NGAY TRƯỚC KHI GỘP, không phải lúc viết.

Revision ID: ns6b4d9a2e7c13
Revises: nd7a2e5b9c4f3
"""
import sqlalchemy as sa
from alembic import op

revision = "ns6b4d9a2e7c13"
down_revision = "nd7a2e5b9c4f3"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    # ── 5.6 ───────────────────────────────────────────────────────────────────────────────────────
    # Sáu ô điểm đều NULLABLE, và đây không phải sự lỏng lẻo: NULL nghĩa là "chưa có số", khác hẳn 0.
    # Phòng nào VTOS chưa có nguồn số cho A1 thì ô ấy để trống kèm chữ, và điểm tổng tính trung bình
    # CÁC Ô CÓ SỐ. Đặt server_default=3 cho qua chuyện là bịa ra một con số rồi đem nó đi xét thưởng.
    op.create_table(
        "danh_gia_nhan_su",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("ky_loai", sa.String(10), server_default="thang", nullable=False),
        sa.Column("ky", sa.String(10), nullable=False),
        sa.Column("department", sa.String(20), server_default=""),
        sa.Column("a1_diem", sa.Integer(), nullable=True),
        sa.Column("a1_nguon", sa.String(200), server_default=""),
        sa.Column("a2_diem", sa.Integer(), nullable=True),
        sa.Column("a2_nguon", sa.String(200), server_default=""),
        sa.Column("a3_diem", sa.Integer(), nullable=True),
        sa.Column("a3_nguon", sa.String(200), server_default=""),
        sa.Column("b1_diem", sa.Integer(), nullable=True),
        sa.Column("b1_ly_do", sa.Text(), server_default=""),
        sa.Column("b2_diem", sa.Integer(), nullable=True),
        sa.Column("b2_ly_do", sa.Text(), server_default=""),
        sa.Column("b3_diem", sa.Integer(), nullable=True),
        sa.Column("b3_ly_do", sa.Text(), server_default=""),
        sa.Column("diem_tong", sa.Float(), nullable=True),
        sa.Column("xep_hang", sa.String(20), server_default=""),
        sa.Column("nhan_xet", sa.Text(), server_default=""),
        sa.Column("viec_phai_sua", sa.Text(), server_default=""),
        sa.Column("de_xuat", sa.Text(), server_default=""),
        sa.Column("thieu_ky_con", sa.String(200), server_default=""),
        sa.Column("trang_thai", sa.String(20), server_default="nhap", nullable=False),
        sa.Column("nguoi_cham", sa.String(50), server_default=""),
        sa.Column("vai_nguoi_cham", sa.String(20), server_default=""),
        sa.Column("cham_luc", sa.DateTime(), nullable=True),
        sa.Column("gui_luc", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    # Một người một kỳ đúng MỘT bản. Không có ràng buộc này thì hai lần bấm "Lưu" đẻ ra hai bản
    # điểm khác nhau của cùng một người, và bảng tổng hợp của HCNS cộng cả hai.
    op.create_unique_constraint("uq_danh_gia_nguoi_ky", "danh_gia_nhan_su",
                                ["employee_id", "ky_loai", "ky"])
    op.create_index("ix_danh_gia_nhan_su_employee_id", "danh_gia_nhan_su", ["employee_id"])
    op.create_index("ix_danh_gia_nhan_su_ky_loai", "danh_gia_nhan_su", ["ky_loai"])
    op.create_index("ix_danh_gia_nhan_su_ky", "danh_gia_nhan_su", ["ky"])
    op.create_index("ix_danh_gia_nhan_su_department", "danh_gia_nhan_su", ["department"])
    op.create_index("ix_danh_gia_nhan_su_trang_thai", "danh_gia_nhan_su", ["trang_thai"])

    # ── 5.9.2 ─────────────────────────────────────────────────────────────────────────────────────
    # `uoc_tinh` và `so_tien_chi` là HAI cột, không phải một. Số người đề nghị đoán và số Kế toán
    # thật sự chi khác nhau là chuyện thường; gộp một cột thì lần chi đầu tiên xoá mất con số đã
    # được duyệt, và không ai còn đối chiếu được "duyệt bao nhiêu, chi bao nhiêu".
    op.create_table(
        "de_nghi_mua",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(30), nullable=False),
        sa.Column("department", sa.String(20), server_default=""),
        sa.Column("nguoi_de_nghi", sa.String(50), server_default=""),
        sa.Column("noi_dung", sa.String(300), server_default=""),
        sa.Column("so_luong", sa.Float(), server_default="1"),
        sa.Column("don_vi", sa.String(20), server_default="cái"),
        sa.Column("uoc_tinh", TIEN, nullable=True),
        sa.Column("ly_do", sa.Text(), server_default=""),
        sa.Column("muc_do", sa.String(10), server_default="thuong"),
        sa.Column("can_truoc_ngay", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(20), server_default="nhap", nullable=False),
        sa.Column("duyet_boi", sa.String(50), server_default=""),
        sa.Column("duyet_vai", sa.String(20), server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("duyet_ghi_chu", sa.Text(), server_default=""),
        sa.Column("chi_boi", sa.String(50), server_default=""),
        sa.Column("chi_luc", sa.DateTime(), nullable=True),
        sa.Column("so_tien_chi", TIEN, nullable=True),
        sa.Column("chung_tu_ref", sa.String(60), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_de_nghi_mua_ma", "de_nghi_mua", ["ma"], unique=True)
    op.create_index("ix_de_nghi_mua_department", "de_nghi_mua", ["department"])
    op.create_index("ix_de_nghi_mua_trang_thai", "de_nghi_mua", ["trang_thai"])

    # ── 5.9.3 ─────────────────────────────────────────────────────────────────────────────────────
    # `asset_id` NULLABLE có lý do, không phải để dễ: phần lớn thứ HCNS cấp — điện thoại, SIM,
    # chìa khoá, đồng phục, thẻ ra vào — không đủ nguyên giá để thành một thẻ TSCĐ. Bắt mọi món phải
    # có thẻ trước khi cấp thì HCNS sẽ ghi ra giấy, và sổ máy này rỗng trong khi đồ vẫn đi.
    op.create_table(
        "cap_phat_tai_san",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(30), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("fixed_assets.id"), nullable=True),
        sa.Column("ten_tai_san", sa.String(200), server_default=""),
        sa.Column("so_luong", sa.Float(), server_default="1"),
        sa.Column("don_vi", sa.String(20), server_default="cái"),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("department", sa.String(20), server_default=""),
        sa.Column("cap_ngay", sa.Date(), nullable=False),
        sa.Column("muc_dich", sa.String(300), server_default=""),
        sa.Column("tinh_trang_khi_cap", sa.String(100), server_default=""),
        sa.Column("trang_thai", sa.String(20), server_default="dang_giu", nullable=False),
        sa.Column("tra_ngay", sa.Date(), nullable=True),
        sa.Column("tinh_trang_khi_tra", sa.String(200), server_default=""),
        sa.Column("nguoi_lap", sa.String(50), server_default=""),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_cap_phat_tai_san_ma", "cap_phat_tai_san", ["ma"], unique=True)
    op.create_index("ix_cap_phat_tai_san_employee_id", "cap_phat_tai_san", ["employee_id"])
    op.create_index("ix_cap_phat_tai_san_department", "cap_phat_tai_san", ["department"])
    op.create_index("ix_cap_phat_tai_san_cap_ngay", "cap_phat_tai_san", ["cap_ngay"])
    op.create_index("ix_cap_phat_tai_san_trang_thai", "cap_phat_tai_san", ["trang_thai"])


def downgrade() -> None:
    op.drop_table("cap_phat_tai_san")
    op.drop_table("de_nghi_mua")
    op.drop_table("danh_gia_nhan_su")
