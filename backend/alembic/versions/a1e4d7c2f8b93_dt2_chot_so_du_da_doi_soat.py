"""DT-2 – chốt số dư đã đối soát.

Revises: b5f9h4c7e2a31

CỬA NHẬP SỐ 1 CỦA BẢNG DÒNG TIỀN

DT-1 đòi hàm tiền khả dụng "trả kèm mốc đối soát đến ngày…". Rà kho mã ngày 11/9/2026 thì không
có chỗ nào giữ câu ấy: `bank_accounts_cat.opening_balance` là số dư ĐẦU KỲ lúc khai tài khoản,
còn `bank_transactions` là luồng SePay đẩy về – cộng dồn được, nhưng "máy cộng ra" khác "người
đã đối soát". Quỹ tiền mặt thì chỉ có `method='tien_mat'` trên từng phiếu, tức phương thức của
một giao dịch, không phải số dư quỹ đã đếm.

Bảng giữ LỜI KHAI CỦA KẾ TOÁN. Cột `so_may_cong` và `lech` giữ số máy để đối chiếu và kêu khi
lệch – nhưng số đem đi quyết định chi tiền là số người ký.

KHOÁ DUY NHẤT có `trang_thai` trong thành phần là cố ý: chốt lại cùng một ngày thì bản cũ chuyển
sang 'da_thay_the' và rời khỏi ô khoá, bản mới vào được, và sổ giữ CẢ HAI. Không có `trang_thai`
trong khoá thì mỗi lần sửa lại phải xoá bản cũ – tức là xoá đúng thứ kiểm toán cần đọc.

CHA LÀ `b5f9h4c7e2a31` (VPM-17), VÀ ĐÃ ĐỔI HAI LẦN TRONG MỘT NGÀY.

Bản đầu trỏ `v16d8e2b9f4a71` – cùng cha với VPM-11 (`a4e8g3b6d1f29`) – nên mạch có HAI ĐẦU. Sửa lúc
15h thành nối sau VPM-11. Đến 16h, VPM-17 (`b5f9h4c7e2a31`) cũng nối sau VPM-11 mà không biết, nên
lại HAI ĐẦU. Alembic gặp hai đầu thì `upgrade head` DỪNG – máy chủ không lên được.

Lần này nối sau VPM-17, vì VPM-17 đã ghi mã và đã đẩy lên GitHub còn bản này thì chưa: bản vào sau
sửa một dòng, chứ không bắt làn khác mở lại nhánh đã đẩy. Nếu thứ tự gộp đổi thì đổi lại đúng dòng
`down_revision` dưới đây, và CHỈ dòng ấy.

BẢN ĐẦU CÒN TẠO BẢNG `nghia_vu_tien` cho DT-5/DT-6; đã bỏ, vì lằn VPM-11 đã dựng đúng khái niệm
ấy ở `nghia_vu_thanh_toan` và hoàn chỉnh hơn. Bảng ấy CHƯA TỪNG chạy trên máy chủ nào, nên không
có bước gỡ và không có dữ liệu nào phải chuyển.

KHÔNG có dữ liệu nào để chuyển: `chot_so_du` là bảng mới hoàn toàn.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1e4d7c2f8b93"
down_revision = "b5f9h4c7e2a31"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)

CHI_MUC_CHOT = ("company_id", "nguon", "tai_khoan_id", "den_ngay", "trang_thai")


def _co_bang(ten: str) -> bool:
    return ten in sa.inspect(op.get_bind()).get_table_names()


def _chi_muc(bang: str, cot: tuple[str, ...]) -> None:
    for c in cot:
        try:
            op.create_index(f"ix_{bang}_{c}", bang, [c])
        except Exception:
            pass


def upgrade() -> None:
    if not _co_bang("chot_so_du"):
        op.create_table(
            "chot_so_du",
            sa.Column("id", sa.Integer(), primary_key=True),
            # Pháp nhân RỖNG là CHƯA XÁC ĐỊNH – không mặc định về công ty mẹ, và dòng rỗng không
            # cộng vào tiền khả dụng của ai. Cùng quy ước với payment_requests.company_id.
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
            sa.Column("nguon", sa.String(20), nullable=False),
            sa.Column("tai_khoan_id", sa.Integer(),
                      sa.ForeignKey("bank_accounts_cat.id"), nullable=True),
            sa.Column("den_ngay", sa.Date(), nullable=False),
            # Số người ký: KHÔNG rỗng. Chốt mà không có số thì không phải một lần chốt.
            sa.Column("so_du", TIEN, nullable=False),
            # Số máy cộng và chênh lệch: RỖNG khi máy không cộng được (quỹ tiền mặt, hoặc tài khoản
            # chưa nối SePay). Rỗng ≠ 0 – 0 là "đã đối chiếu và khớp".
            sa.Column("so_may_cong", TIEN, nullable=True),
            sa.Column("lech", TIEN, nullable=True),
            sa.Column("ly_do_lech", sa.String(300), nullable=False, server_default=""),
            sa.Column("trang_thai", sa.String(20), nullable=False, server_default="hieu_luc"),
            sa.Column("thay_the_id", sa.Integer(), sa.ForeignKey("chot_so_du.id"), nullable=True),
            sa.Column("boi", sa.String(50), nullable=False),
            sa.Column("luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
            sa.UniqueConstraint("company_id", "nguon", "tai_khoan_id", "den_ngay", "trang_thai",
                                name="uq_chot_so_du_mot_ngay_mot_ban"),
        )
        _chi_muc("chot_so_du", CHI_MUC_CHOT)


def downgrade() -> None:
    if not _co_bang("chot_so_du"):
        return
    for c in CHI_MUC_CHOT:
        try:
            op.drop_index(f"ix_chot_so_du_{c}", table_name="chot_so_du")
        except Exception:
            pass
    op.drop_table("chot_so_du")
