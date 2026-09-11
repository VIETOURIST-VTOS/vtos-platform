"""V7 Đợt 3 – Sự cố tour (bảng riêng) và Hồ sơ kiểm toán

Revision ID: v14b6e9c2a7d31
Revises: y2d8e3f0a5b97

NĂM BẢNG MỚI, KHÔNG BẢNG NÀO GIỮ MỘT CON SỐ TIỀN
------------------------------------------------
  su_co_tour                 : sự cố của một chuyến đang chạy
  su_co_tour_xu_ly           : dòng thời gian xử lý
  ho_so_kiem_toan            : một kỳ kiểm toán / soát xét của một pháp nhân
  ho_so_kiem_toan_muc        : từng mục tài liệu kiểm toán yêu cầu
  ho_so_kiem_toan_dieu_chinh : bút toán điều chỉnh kiểm toán đề nghị

Chi phí phát sinh của sự cố nằm ở payment_requests; số tiền điều chỉnh sau soát xét nằm ở
journal_entries. Hai bảng này chỉ giữ SỐ HIỆU chứng từ. Xem ghi chú đầu hai tệp mô hình.

VÌ SAO `su_co_tour` KHÔNG DÙNG LẠI BẢNG `incidents`
--------------------------------------------------
`incidents` là hồ sơ KỶ LUẬT NỘI BỘ của một nhân viên (mức 1–3, chế tài, khiếu nại 3 ngày), cột bắt
buộc là employee_id. Sự cố tour là chuyện xảy ra với một CHUYẾN, và phần lớn không có ai sai – thời
tiết, chuyến bay dời, lỗi nhà cung cấp. Đây đúng là lập luận đã dùng khi tách `complaints` khỏi
`incidents` ngày 07/9/2026, và hai bảng vẫn nối được với nhau bằng khoá ngoài incident_id.

KHÔNG CÓ BƯỚC CHUYỂN DỮ LIỆU CŨ. Không dòng nào của `incidents` là sự cố tour, nên chuyển sang đây là
chuyển nhầm hồ sơ kỷ luật của người thành sự cố của chuyến.
"""
from alembic import op
import sqlalchemy as sa

revision = "v14b6e9c2a7d31"
# Nối sau v11 chứ không phải v13. Sửa ngày 10/9/2026, lý do:
#
# Bản này khai down_revision = "v13a4c7e9b1d52", nhưng tệp mang mã v13a4c7e9b1d52
# (ban_luu_bao_cao_chi_tieu) không còn trong thư mục versions. Hệ quả là mạch migration có HAI đầu
# (v11d8e4b6a2f79 và v14b6e9c2a7d31) và một mắt xích trỏ vào chỗ trống.
#
# Dockerfile chạy `alembic upgrade head` khi container khởi động: nhiều hơn một đầu thì alembic
# dừng với lỗi, container không lên, và API sập – không phải chậm, mà là không chạy.
#
# v11d8e4b6a2f79 là đầu mạch còn lại và không tệp nào khác nối sau nó, nên nối vào đó là mạch liền
# một đầu duy nhất. Nếu bản ban_luu_bao_cao_chi_tieu được dựng lại sau này thì phải xếp nó vào giữa
# và sửa lại dòng dưới đây cho đúng thứ tự – KHÔNG dùng merge revision để gộp hai đầu.
# NỐI LẠI 11/9/2026, lúc gộp làn V7 lên nhánh chính.
#
# Bản này vốn khai down_revision = "v11d8e4b6a2f79" – CÙNG CHA với v13a4c7e9b1d52. Lúc viết thì đúng,
# vì v13 chưa có. Nhưng từ hôm ấy nhánh chính đã đi tiếp v13 → w1a2b3c4d5e6 → … → y2d8e3f0a5b97 cũng
# từ v11, nên gộp y nguyên là mạch có HAI ĐẦU và `alembic upgrade head` dừng ngay với
#
#     ERROR: Multiple head revisions are present
#
# Render lại chết như hôm 10/9, chỉ khác câu báo lỗi – và lại là kiểu hỏng lặng: máy chủ giữ bản cũ
# nên nhìn từ ngoài VTOS vẫn chạy bình thường.
#
# Nối vào đầu chuỗi hiện tại thì mạch thẳng trở lại, đúng MỘT đầu. Bản này chỉ TẠO NĂM BẢNG MỚI và
# thêm hai loại đối tượng đính kèm – không chạm bảng nào của các bản ở giữa – nên đổi cha là hợp lệ.
#
# Đổi cha CHỈ an toàn vì bản này CHƯA TỪNG CHẠY ở đâu: nó chưa bao giờ nằm trên nhánh chính, và lần
# triển khai 10/9 hỏng ngay ở bước alembic nên máy chủ giữ bản cũ. Đổi cha của một bản ĐÃ CHẠY là
# đổi lại thứ tự của việc đã xảy ra – không được làm.
down_revision = "y2d8e3f0a5b97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    co = set(sa.inspect(op.get_bind()).get_table_names())

    if "su_co_tour" not in co:
        op.create_table(
            "su_co_tour",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(20), nullable=False, unique=True),
            sa.Column("tour_id", sa.Integer(), nullable=False),
            sa.Column("booking_id", sa.Integer(), nullable=True),
            sa.Column("nhom", sa.String(20), nullable=False),
            sa.Column("muc", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("xay_ra_luc", sa.DateTime(), nullable=True),
            sa.Column("noi_xay_ra", sa.String(160), nullable=False, server_default=""),
            sa.Column("so_khach_anh_huong", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mo_ta", sa.Text(), nullable=False),
            sa.Column("nguoi_bao", sa.String(120), nullable=False, server_default=""),
            sa.Column("nguoi_bao_id", sa.Integer(), nullable=True),
            sa.Column("supplier_id", sa.Integer(), nullable=True),
            sa.Column("trang_thai", sa.String(12), nullable=False, server_default="moi"),
            sa.Column("han_xu_ly", sa.DateTime(), nullable=True),
            sa.Column("nhan_luc", sa.DateTime(), nullable=True),
            sa.Column("nguoi_xu_ly", sa.String(50), nullable=False, server_default=""),
            sa.Column("huong_xu_ly", sa.Text(), nullable=False, server_default=""),
            sa.Column("ket_qua", sa.Text(), nullable=False, server_default=""),
            sa.Column("nguyen_nhan_nhom", sa.String(20), nullable=False, server_default=""),
            sa.Column("nguyen_nhan", sa.Text(), nullable=False, server_default=""),
            sa.Column("payment_request_id", sa.Integer(), nullable=True),
            sa.Column("complaint_id", sa.Integer(), nullable=True),
            sa.Column("incident_id", sa.Integer(), nullable=True),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("closed_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_su_co_tour_tour_id", "su_co_tour", ["tour_id"])
        op.create_index("ix_su_co_tour_booking_id", "su_co_tour", ["booking_id"])
        op.create_index("ix_su_co_tour_supplier_id", "su_co_tour", ["supplier_id"])
        op.create_index("ix_su_co_tour_company_id", "su_co_tour", ["company_id"])
        op.create_index("ix_su_co_tour_trang_thai", "su_co_tour", ["trang_thai"])
        op.create_index("ix_su_co_tour_tour", "su_co_tour", ["tour_id", "trang_thai"])

    if "su_co_tour_xu_ly" not in co:
        op.create_table(
            "su_co_tour_xu_ly",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("su_co_id", sa.Integer(), nullable=False),
            sa.Column("luc", sa.DateTime(), nullable=True),
            sa.Column("nguoi", sa.String(50), nullable=False, server_default=""),
            sa.Column("noi_dung", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_su_co_tour_xu_ly_su_co_id", "su_co_tour_xu_ly", ["su_co_id"])

    if "ho_so_kiem_toan" not in co:
        op.create_table(
            "ho_so_kiem_toan",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(30), nullable=False, unique=True),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("ky", sa.String(12), nullable=False),
            sa.Column("loai", sa.String(20), nullable=False, server_default="soat_xet"),
            sa.Column("don_vi_kiem_toan", sa.String(160), nullable=False, server_default=""),
            sa.Column("so_hop_dong", sa.String(60), nullable=False, server_default=""),
            sa.Column("nguoi_dau_moi", sa.String(50), nullable=False, server_default=""),
            sa.Column("ngay_bat_dau", sa.Date(), nullable=True),
            sa.Column("han_hoan_thanh", sa.Date(), nullable=True),
            sa.Column("trang_thai", sa.String(16), nullable=False, server_default="chuan_bi"),
            sa.Column("loai_y_kien", sa.String(24), nullable=False, server_default=""),
            sa.Column("so_bao_cao", sa.String(60), nullable=False, server_default=""),
            sa.Column("ngay_bao_cao", sa.Date(), nullable=True),
            sa.Column("van_de_nhan_manh", sa.Text(), nullable=False, server_default=""),
            sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_ho_so_kiem_toan_company_id", "ho_so_kiem_toan", ["company_id"])
        op.create_index("ix_ho_so_kiem_toan_ky", "ho_so_kiem_toan", ["ky"])
        op.create_index("ix_ho_so_kiem_toan_trang_thai", "ho_so_kiem_toan", ["trang_thai"])
        # Một pháp nhân, một kỳ, một loại thì chỉ MỘT hồ sơ. Đặt bằng CHỈ MỤC duy nhất chứ không bằng
        # ràng buộc trên bảng: SQLite (máy lập trình) không thêm được ràng buộc vào bảng đã tạo, chỉ
        # mục thì cả hai môi trường đều tạo được – cùng cách làm với ux_attachments_noi_dung.
        op.create_index("ux_ho_so_kiem_toan_ky", "ho_so_kiem_toan",
                        ["company_id", "ky", "loai"], unique=True)

    if "ho_so_kiem_toan_muc" not in co:
        op.create_table(
            "ho_so_kiem_toan_muc",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ho_so_id", sa.Integer(), nullable=False),
            sa.Column("stt", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ten", sa.String(300), nullable=False),
            sa.Column("nhom_ho_so", sa.String(20), nullable=False, server_default="08_Kiem_toan"),
            sa.Column("phong_ban", sa.String(20), nullable=False, server_default="ketoan"),
            sa.Column("nguoi_phu_trach", sa.String(50), nullable=False, server_default=""),
            sa.Column("han_nop", sa.Date(), nullable=True),
            sa.Column("trang_thai", sa.String(16), nullable=False, server_default="chua_gui"),
            sa.Column("ngay_gui", sa.Date(), nullable=True),
            sa.Column("cau_hoi", sa.Text(), nullable=False, server_default=""),
            sa.Column("tra_loi", sa.Text(), nullable=False, server_default=""),
            sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_ho_so_kiem_toan_muc_ho_so_id", "ho_so_kiem_toan_muc", ["ho_so_id"])
        op.create_index("ix_ho_so_kiem_toan_muc_trang_thai", "ho_so_kiem_toan_muc", ["trang_thai"])
        op.create_index("ix_ho_so_kiem_toan_muc_ho_so", "ho_so_kiem_toan_muc",
                        ["ho_so_id", "trang_thai"])

    if "ho_so_kiem_toan_dieu_chinh" not in co:
        op.create_table(
            "ho_so_kiem_toan_dieu_chinh",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ho_so_id", sa.Integer(), nullable=False),
            sa.Column("noi_dung", sa.Text(), nullable=False),
            sa.Column("journal_entry_id", sa.Integer(), nullable=True),
            sa.Column("trang_thai", sa.String(16), nullable=False, server_default="de_xuat"),
            sa.Column("ly_do", sa.Text(), nullable=False, server_default=""),
            sa.Column("nguoi_quyet", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_ho_so_kiem_toan_dieu_chinh_ho_so_id", "ho_so_kiem_toan_dieu_chinh",
                        ["ho_so_id"])


def downgrade() -> None:
    """Hạ cấp XOÁ cả năm bảng, và những gì trong đó không dựng lại được.

    Nói rõ vì đây không phải thao tác đảo ngược vô hại. Hồ sơ sự cố là lời kể của người ở hiện trường
    lúc chuyện đang xảy ra – không ai viết lại được sau. Danh mục kiểm toán là bằng chứng ta đã cung
    cấp những gì cho kiểm toán viên, và đó chính là thứ họ hỏi lại vào kỳ sau.

    Chứng từ tiền thì KHÔNG mất theo: chi phí sự cố nằm ở payment_requests và bút toán điều chỉnh nằm
    ở journal_entries – hạ cấp bản này chỉ cắt đường nối, không đụng tới sổ.
    """
    for t in ("ho_so_kiem_toan_dieu_chinh", "ho_so_kiem_toan_muc", "ho_so_kiem_toan",
              "su_co_tour_xu_ly", "su_co_tour"):
        op.drop_table(t)
