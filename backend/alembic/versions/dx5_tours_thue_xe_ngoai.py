"""R1 · Hai cột 'thuê xe ngoài' trên bảng tours.

Chủ tịch chốt 16/10/2026: khai Ở CHUYẾN BÁN, không ở danh mục tour.

VÌ SAO Ở `tours` MÀ KHÔNG Ở `products`. Cùng một chương trình "Đà Lạt 3N3D": chuyến tuần này dùng
xe nhà, chuyến tuần sau thuê ngoài vì xe nhà kín lịch. Khai ở danh mục thì một chương trình chỉ có
MỘT câu trả lời, và báo cáo nhìn lại (`services/doi_chieu_xe_ngoai.py`) mất đúng cái nó cần biết:
chuyến NÀO đã thuê ngoài.

VÌ SAO LÝ DO LÀ MÃ CHỌN, KHÔNG PHẢI CHỮ TỰ DO. Báo cáo nhìn lại phải cộng được theo nhóm, và phải
phân biệt khoản đáng tiếc với khoản bình thường: "xe nhà kín lịch" là chuyện thường, "khách chỉ
định nhà xe" cũng vậy; "xe nhà đang bảo dưỡng" trong một tháng mà xe đậu nhiều mới là chỗ phải hỏi.
Chữ tự do thì cùng một lý do được gõ bốn cách và không nhóm được cái nào.

HAI CỘT, KHÔNG MỘT. Một cột `ly_do_thue_ngoai` có chữ đã hàm ý thuê ngoài, nhưng cờ riêng mới trả
lời được trường hợp "có thuê ngoài, chưa ai chọn lý do" — khác hẳn "không thuê ngoài". Gộp lại là
để trống mang hai nghĩa.

`server_default` cho cột cờ: bảng `tours` đang có dữ liệu thật, và cột mới không được để mọi chuyến
cũ thành NULL — NULL ở đây đọc như "chưa biết", còn sự thật là "chưa ai khai", mà mặc định đúng cho
chuyến cũ là KHÔNG thuê ngoài (xe nhà là đường mặc định của đội xe).

Revision ID: dx5t0u7s9e4a
Revises: r3b7c1e4a9d52
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "dx5t0u7s9e4a"
down_revision = "r3b7c1e4a9d52"   # head của main a42e82f, đo bằng `alembic heads` 17/10/2026
branch_labels = None
depends_on = None

# Năm lý do, chốt cùng ngày. Giữ đúng thứ tự này trên màn hình: hai lý do đầu là hai lý do thường
# gặp nhất, lý do cuối là lý do đáng hỏi nhất.
LY_DO = ("xe_nha_kin_lich", "khong_co_loai_xe", "ngoai_vung_xe_nha",
         "khach_chi_dinh", "xe_nha_dang_bao_duong")


def upgrade() -> None:
    op.add_column("tours", sa.Column("thue_xe_ngoai", sa.Boolean(), nullable=False,
                                     server_default=sa.false()))
    # sa.false(), KHÔNG sa.text("0"): máy thật chạy PostgreSQL, và `DEFAULT 0` cho một cột boolean
    # bị Postgres từ chối (integer không tự ép sang boolean) — SQLite của phép thử thì nhận, nên lỗi
    # chỉ lộ ra lúc nâng cấp trên máy thật. Cùng cách viết với các tệp migration khác của kho.
    op.add_column("tours", sa.Column("ly_do_thue_ngoai", sa.String(length=40),
                                     nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("tours", "ly_do_thue_ngoai")
    op.drop_column("tours", "thue_xe_ngoai")
