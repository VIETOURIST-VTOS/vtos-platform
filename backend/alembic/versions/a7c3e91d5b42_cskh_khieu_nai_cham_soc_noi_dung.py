"""Marketing & CSKH Đợt 3–5: khiếu nại của khách, phiếu chăm sóc sau bán, sổ duyệt nội dung.

Ba bảng, không bảng nào giữ một con số tiền:
  - complaints    : khiếu nại của KHÁCH (tách hẳn khỏi bảng incidents – kỷ luật nội bộ nhân viên).
                    Số tiền hoàn cho khách nằm ở payment_requests nhóm "hoan_tien"; bảng này chỉ giữ
                    SỐ HIỆU chứng từ đó (payment_request_id) và ĐỀ NGHỊ CỦA KHÁCH bằng nguyên văn.
  - care_tickets  : phiếu chăm sóc sau bán, mỗi booking một phiếu, hệ thống tự sinh khi tour kết thúc.
  - content_items : sổ duyệt nội dung. Nội dung có cam kết với khách hoặc có số liệu tài chính cần chữ
                    ký thứ hai – Vietourist là công ty đại chúng nên đây là nghĩa vụ, không phải thủ tục.

Revision ID: a7c3e91d5b42
Revises: e4f5a6b7c8d9
"""
from alembic import op
import sqlalchemy as sa

revision = "a7c3e91d5b42"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    co = set(sa.inspect(op.get_bind()).get_table_names())

    if "complaints" not in co:
        op.create_table(
            "complaints",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(20), nullable=False, unique=True),
            sa.Column("source", sa.String(20), nullable=False),
            sa.Column("customer_name", sa.String(120), nullable=False),
            sa.Column("customer_phone", sa.String(30), nullable=False, server_default=""),
            sa.Column("booking_id", sa.Integer(), nullable=True),
            sa.Column("tour_id", sa.Integer(), nullable=True),
            sa.Column("nhom", sa.String(20), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("noi_dung", sa.Text(), nullable=False),
            sa.Column("de_nghi_khach", sa.Text(), nullable=False, server_default=""),
            sa.Column("received_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("received_at", sa.DateTime(), nullable=True),
            sa.Column("handler", sa.String(50), nullable=False, server_default=""),
            sa.Column("han_phan_hoi", sa.DateTime(), nullable=True),
            sa.Column("first_response_at", sa.DateTime(), nullable=True),
            sa.Column("nguyen_nhan_nhom", sa.String(20), nullable=False, server_default=""),
            sa.Column("nguyen_nhan", sa.Text(), nullable=False, server_default=""),
            sa.Column("huong_xu_ly", sa.JSON(), nullable=True),
            sa.Column("payment_request_id", sa.Integer(), nullable=True),
            sa.Column("khach_chap_nhan", sa.String(6), nullable=False, server_default=""),
            sa.Column("status", sa.String(12), nullable=False, server_default="moi"),
            sa.Column("incident_id", sa.Integer(), nullable=True),
            sa.Column("care_id", sa.Integer(), nullable=True),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("nguon_tao", sa.String(6), nullable=False, server_default="nguoi"),
            sa.Column("ai_ghi_chu", sa.Text(), nullable=False, server_default=""),
            sa.Column("closed_by", sa.String(120), nullable=False, server_default=""),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("reopen_reason", sa.String(300), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_complaints_phone", "complaints", ["customer_phone"])
        op.create_index("ix_complaints_booking", "complaints", ["booking_id"])
        op.create_index("ix_complaints_tour", "complaints", ["tour_id"])
        op.create_index("ix_complaints_company", "complaints", ["company_id"])

    if "care_tickets" not in co:
        op.create_table(
            "care_tickets",
            sa.Column("id", sa.Integer(), primary_key=True),
            # Duy nhất theo booking: đây là thứ khiến hàm sinh phiếu chạy lại được bao nhiêu lần cũng
            # không đẻ ra phiếu trùng.
            sa.Column("booking_id", sa.Integer(), nullable=False, unique=True),
            sa.Column("tour_id", sa.Integer(), nullable=False),
            sa.Column("customer_name", sa.String(120), nullable=False, server_default=""),
            sa.Column("customer_phone", sa.String(30), nullable=False, server_default=""),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("han_lien_he", sa.Date(), nullable=False),
            sa.Column("hinh_thuc", sa.String(12), nullable=False, server_default=""),
            sa.Column("lien_he_duoc", sa.String(8), nullable=False, server_default=""),
            sa.Column("ly_do_khong", sa.String(300), nullable=False, server_default=""),
            sa.Column("hai_long", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("diem_chua_hai_long", sa.JSON(), nullable=True),
            sa.Column("nhu_cau_tiep", sa.String(6), nullable=False, server_default=""),
            sa.Column("lead_id", sa.Integer(), nullable=True),
            sa.Column("complaint_id", sa.Integer(), nullable=True),
            sa.Column("dong_y_dung_danh_gia", sa.String(6), nullable=False, server_default=""),
            sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(20), nullable=False, server_default="moi"),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("contacted_at", sa.DateTime(), nullable=True),
            sa.Column("updated_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_care_tickets_tour", "care_tickets", ["tour_id"])
        op.create_index("ix_care_tickets_owner", "care_tickets", ["owner_id"])
        op.create_index("ix_care_tickets_phone", "care_tickets", ["customer_phone"])
        op.create_index("ix_care_tickets_company", "care_tickets", ["company_id"])

    if "content_items" not in co:
        op.create_table(
            "content_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(20), nullable=False, unique=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("loai", sa.String(12), nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=True),
            sa.Column("kenh", sa.JSON(), nullable=True),
            sa.Column("ngay_du_kien", sa.Date(), nullable=False),
            sa.Column("ban_thao", sa.String(400), nullable=False, server_default=""),
            sa.Column("co_cam_ket", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("co_so_lieu_tc", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("nguoi_soan", sa.String(50), nullable=False, server_default=""),
            sa.Column("nguoi_duyet", sa.String(160), nullable=False, server_default=""),
            sa.Column("status", sa.String(12), nullable=False, server_default="nhap"),
            sa.Column("link_dang", sa.String(400), nullable=False, server_default=""),
            sa.Column("ly_do_go", sa.String(300), nullable=False, server_default=""),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("nguon_tao", sa.String(6), nullable=False, server_default="nguoi"),
            sa.Column("ai_ghi_chu", sa.Text(), nullable=False, server_default=""),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("posted_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_content_items_campaign", "content_items", ["campaign_id"])


def downgrade() -> None:
    op.drop_table("content_items")
    op.drop_table("care_tickets")
    op.drop_table("complaints")
