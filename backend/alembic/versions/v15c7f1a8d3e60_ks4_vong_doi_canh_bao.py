"""KS-4 – vòng đời cảnh báo: chín cột trả lời 'vì sao 1.703 dòng đỏ không ai xử lý'.

Revises: v14b6e9c2a7d31

VÌ SAO BẢN NÂNG CẤP NÀY TỒN TẠI

Đo trên hệ thống thật 11/9/2026: 1.703 cảnh báo đang mở, 1.310 đỏ; lớn nhất là 851 chuyến quá hạn
quyết toán và 251 quá deadline thu. Một danh sách 1.310 dòng đỏ thì không ai đọc dòng nào — và lý do
nó dài đến thế nằm ở chính cấu trúc bảng:

  · `to_roles` trả lời "ai ĐƯỢC XEM", không trả lời "ai PHẢI LÀM". Một cảnh báo đỏ quá hạn thu tiền
    gửi cho "nv_kd,gd_kd,tp_dh,ketoan" — gửi cho bốn vai trò là gửi cho không ai.
  · `resolved` đúng/sai gộp BA trạng thái vào một ô: chưa ai nhận · đang có người làm · đã xong. Nên
    hai người cùng làm một việc mà không ai biết, và "đóng vì đã xử lý" không phân biệt được với
    "đóng vì là dữ liệu lịch sử".
  · Không có hạn xử lý, nên câu "cảnh báo đang trễ" không đo được và 1.310 dòng đỏ đứng ngang nhau
    dù có dòng mở từ tháng trước.
  · Không có cột ai-đóng và bằng chứng đóng, mà cửa POST /alerts/{id}/resolve lại KHÔNG có chặn nào:
    bất kỳ tài khoản nào đăng nhập cũng đóng được cảnh báo đỏ của phòng khác, và sau khi đóng thì
    không truy lại được ai bấm, dựa vào đâu.

`resolved` GIỮ NGUYÊN, không bỏ: mọi màn hình và robot đang đọc nó. Hai cột đi cùng nhau — trang_thai
là sự thật đầy đủ, resolved là hình chiếu đúng/sai cho mã cũ.

DÒNG CŨ: tất cả nhận trang_thai='moi' nếu chưa xử lý, 'dong' nếu resolved=True. Không đoán ngược
người nhận hay bằng chứng cho 146 dòng đã đóng trước bản này — không có thì để trống, và ô trống
đếm được còn hơn một ô điền bừa.
"""
from alembic import op
import sqlalchemy as sa

revision = "v15c7f1a8d3e60"
down_revision = "v14b6e9c2a7d31"
branch_labels = None
depends_on = None


COT = (
    ("trang_thai", sa.String(20), "moi"),
    ("nguoi_nhan_id", sa.Integer(), None),
    ("nhan_luc", sa.DateTime(), None),
    ("han_xu_ly", sa.DateTime(), None),
    ("dong_luc", sa.DateTime(), None),
    ("dong_boi_id", sa.Integer(), None),
    ("bang_chung", sa.Text(), ""),
    ("nguon", sa.String(20), ""),
    ("gom_khoa", sa.String(100), ""),
)


def _co_cot(ten: str) -> bool:
    bind = op.get_bind()
    return ten in {c["name"] for c in sa.inspect(bind).get_columns("alerts")}


def upgrade() -> None:
    for ten, kieu, mac_dinh in COT:
        if _co_cot(ten):
            continue
        op.add_column("alerts", sa.Column(
            ten, kieu, nullable=True,
            server_default=sa.text("'%s'" % mac_dinh) if mac_dinh is not None else None))

    # Dòng cũ: đã xử lý thì là 'dong', còn lại là 'moi'. Gom khoá dựng từ (kind, ref) đúng như khuôn
    # mà từng robot vẫn tự dò bằng tay — để từ nay việc dò trùng có MỘT chỗ chứ không mười một chỗ.
    op.execute("UPDATE alerts SET trang_thai = CASE WHEN resolved THEN 'dong' ELSE 'moi' END "
               "WHERE trang_thai IS NULL OR trang_thai = ''")
    op.execute("UPDATE alerts SET gom_khoa = kind || ':' || ref WHERE gom_khoa IS NULL OR gom_khoa = ''")
    op.execute("UPDATE alerts SET bang_chung = '' WHERE bang_chung IS NULL")
    op.execute("UPDATE alerts SET nguon = '' WHERE nguon IS NULL")

    # Bốn cột mô hình khai Mapped[str] (không có `| None`) thì cơ sở dữ liệu cũng phải nói KHÔNG RỖNG,
    # sau khi đã điền xong dòng cũ. Mô hình bảo không rỗng mà bảng cho rỗng là chỗ hai bên nói khác
    # nhau, và chỗ ấy chỉ lộ ra lúc có một dòng NULL lọt vào rồi màn hình vỡ ở nơi khác.
    # SQLite không ALTER được ràng buộc này; mặc định ở mô hình vẫn giữ mọi dòng có giá trị.
    if op.get_bind().dialect.name != "sqlite":
        for ten in ("trang_thai", "bang_chung", "nguon", "gom_khoa"):
            op.alter_column("alerts", ten, nullable=False)

    for ten in ("trang_thai", "nguoi_nhan_id", "han_xu_ly", "nguon", "gom_khoa"):
        try:
            op.create_index(f"ix_alerts_{ten}", "alerts", [ten])
        except Exception:
            pass


def downgrade() -> None:
    for ten in ("trang_thai", "nguoi_nhan_id", "han_xu_ly", "nguon", "gom_khoa"):
        try:
            op.drop_index(f"ix_alerts_{ten}", table_name="alerts")
        except Exception:
            pass
    for ten, _kieu, _md in reversed(COT):
        if _co_cot(ten):
            op.drop_column("alerts", ten)
