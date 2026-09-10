"""Lớp 2 của quyết toán tour: bốn mặt của một chuyến.

Lớp 1 (bảng tour_settlements) đã trả lời "chuyến này lãi bao nhiêu". Bản này dựng lớp 2 – "lãi ấy
đến từ đâu" – theo đúng bố cục tệp quyết toán thật của Điều hành, gồm bốn sheet:

    QT       -> tour_settlement_lines + tour_settlement_costs   (từng khách, chi phí phân bổ đầu khách)
    CTT      -> tour_settlement_cost_lines                      (chiết tính: đối tác, chứng từ, MST)
    HDV CHI  -> tour_guide_advances                             (HDV ứng bao nhiêu, chi bao nhiêu, dư)
    DT       -> tour_settlement_bookings                        (BookingID, thu đủ chưa)

VÌ SAO PHẢI LÀ BỐN BẢNG CHỨ KHÔNG PHẢI MỘT

Đo trên tệp thật "QT TOUR NHA TRANG 10.07.26.xlsx" (42 khách, 71.165.000 đ):

  * Cột chi trong sheet QT chỉ là PHÂN BỔ. Cột LAND có đúng hai giá trị – 1.343.030 cho 33 người lớn
    và 570.000 cho 7 trẻ em. Nó là phép chia của chiết tính, không mang thêm thông tin nào.
  * Sheet CTT mang tên đối tác, số hoá đơn và MST: 16 dòng chi, 13 dòng có số chứng từ, 9 dòng có
    MST. Đó chính là bảng kê thuế GTGT đầu vào. Dựng lớp 2 chỉ từ sheet QT là bỏ mất lớp chứng từ,
    và sau đó không đối chiếu tour với tờ khai thuế được nữa.
  * Sheet HDV CHI bắt được một khoản mà ba sheet kia không thấy: HDV tính vé Tháp Bà cho 44 khách
    (1.320.000 đ) trong khi chiết tính tính cho 40 (1.200.000 đ), tiền ứng 1.620.000, dư 0. Tức đã
    chi thật 1.620.000 mà giá vốn chỉ ghi 1.500.000. 120.000 đ ấy không nằm trong giá vốn, không
    trong công nợ, cũng không trong hoàn ứng – và nó vô hình ở mọi chuyến, không riêng chuyến này.
  * Sheet DT có BookingID, khoá duy nhất nối được bản Excel với hệ đặt chỗ. Dò theo tên khách là
    cách sai: cùng một tệp có cả "NGUYEN HONG DEN" không dấu lẫn tên có dấu đầy đủ.

Tất cả cột tiền dùng Numeric(18,2) theo chuẩn V9, và để NULL được: rỗng nghĩa là CHƯA CÓ SỐ, khác
hẳn 0 đồng. Đó là quy tắc đã cứu 2,65 tỷ khỏi bị báo lãi 100% ở bảng lớp 1.

Revision ID: w1a2b3c4d5e6
Revises: v14b6e9c2a7d31
"""
from alembic import op
import sqlalchemy as sa

revision = "w1a2b3c4d5e6"
down_revision = "v14b6e9c2a7d31"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)

# Cột bổ sung cho lớp 1: những ô nằm TRÊN bảng khách trong tệp Điều hành, trước bản này không có
# chỗ nào để ghi nên bị mất khi nạp.
COT_LOP1 = [
    ("ten_chuong_trinh", sa.String(200)),
    ("so_khach", sa.Integer()),
    ("hdv", sa.String(120)),
    ("bien_so_xe", sa.String(30)),
    ("gia_ban", TIEN),
    ("nhieu_muc_gia", sa.Integer()),
    ("chenh_thu", TIEN),
    ("chenh_chi", TIEN),
]


def upgrade() -> None:
    for ten, kieu in COT_LOP1:
        op.add_column("tour_settlements", sa.Column(ten, kieu, nullable=True))

    op.create_table(
        "tour_settlement_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_id", sa.Integer(),
                  sa.ForeignKey("tour_settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stt", sa.Integer(), nullable=True),
        sa.Column("sales", sa.String(120), nullable=True),
        sa.Column("ten_khach", sa.String(200), nullable=True),
        sa.Column("gia_ban", TIEN, nullable=True),
        sa.Column("thu_khac", TIEN, nullable=True),
        sa.Column("tong_thu", TIEN, nullable=True),
        sa.Column("tong_chi", TIEN, nullable=True),
        sa.Column("loi_nhuan_tep", TIEN, nullable=True),
        sa.Column("co_lech", sa.Text(), nullable=True),
    )
    op.create_index("ix_tsl_settlement", "tour_settlement_lines", ["settlement_id"])

    op.create_table(
        "tour_settlement_costs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("line_id", sa.Integer(),
                  sa.ForeignKey("tour_settlement_lines.id", ondelete="CASCADE"), nullable=False),
        # Rỗng nghĩa là CHƯA AI XẾP MÃ cho nhãn ấy, không phải "khoản khác". Máy không đoán: nhãn
        # "PHÍ TL" trong tệp tour lẻ nghe như phí tham quan nhưng đối chiếu chiết tính ra là HDV
        # cộng ăn nội bộ, còn phí tham quan thật nằm trong khối LAND.
        sa.Column("ma_khoan", sa.String(30), nullable=True),
        sa.Column("nhan", sa.String(120), nullable=True),
        sa.Column("so_tien", TIEN, nullable=True),
    )
    op.create_index("ix_tsc_line", "tour_settlement_costs", ["line_id"])
    op.create_index("ix_tsc_ma", "tour_settlement_costs", ["ma_khoan"])

    op.create_table(
        "tour_settlement_cost_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_id", sa.Integer(),
                  sa.ForeignKey("tour_settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ve", sa.String(10), nullable=True),
        sa.Column("nhom", sa.String(80), nullable=True),
        sa.Column("ngay", sa.String(60), nullable=True),
        sa.Column("noi_dung", sa.String(200), nullable=True),
        sa.Column("doi_tac", sa.String(200), nullable=True),
        sa.Column("don_gia", TIEN, nullable=True),
        sa.Column("so_luong", sa.Float(), nullable=True),
        sa.Column("he_so", sa.Float(), nullable=True),
        sa.Column("thanh_tien", TIEN, nullable=True),
        sa.Column("so_chung_tu", sa.String(60), nullable=True),
        sa.Column("mst_ncc", sa.String(30), nullable=True),
        sa.Column("co_lech", sa.Text(), nullable=True),
    )
    op.create_index("ix_tscl_settlement", "tour_settlement_cost_lines", ["settlement_id"])
    # Index trên MST vì câu hỏi hay hỏi nhất là ngược lại: "nhà cung cấp này đã xuất bao nhiêu hoá
    # đơn cho công ty trong kỳ" – hỏi từ phía tờ khai thuế đi vào, không phải từ phía tour đi ra.
    op.create_index("ix_tscl_mst", "tour_settlement_cost_lines", ["mst_ncc"])

    op.create_table(
        "tour_guide_advances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_id", sa.Integer(),
                  sa.ForeignKey("tour_settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("noi_dung", sa.String(200), nullable=True),
        sa.Column("don_gia", TIEN, nullable=True),
        sa.Column("so_luong", sa.Float(), nullable=True),
        sa.Column("tong_chi", TIEN, nullable=True),
        sa.Column("ghi_chu", sa.String(120), nullable=True),
        sa.Column("tien_ung", TIEN, nullable=True),
        sa.Column("du", TIEN, nullable=True),
        sa.Column("ctp", TIEN, nullable=True),
        sa.Column("la_dong_tong", sa.Integer(), nullable=True, server_default="0"),
    )
    op.create_index("ix_tga_settlement", "tour_guide_advances", ["settlement_id"])

    op.create_table(
        "tour_settlement_bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_id", sa.Integer(),
                  sa.ForeignKey("tour_settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ma_booking_nguon", sa.String(40), nullable=True),
        # NULL nghĩa là chưa tra ra booking thật trong VTOS, không phải không có booking.
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("ten_nguoi_book", sa.String(200), nullable=True),
        sa.Column("dien_thoai", sa.String(30), nullable=True),
        sa.Column("gia_tour", TIEN, nullable=True),
        sa.Column("so_khach", sa.Integer(), nullable=True),
        sa.Column("tong_gia_tour", TIEN, nullable=True),
        sa.Column("phi_visa", TIEN, nullable=True),
        sa.Column("phi_khac", TIEN, nullable=True),
        sa.Column("khuyen_mai", TIEN, nullable=True),
        sa.Column("tong_thu", TIEN, nullable=True),
        sa.Column("da_dong", TIEN, nullable=True),
        sa.Column("nguoi_ban", sa.String(120), nullable=True),
    )
    op.create_index("ix_tsb_settlement", "tour_settlement_bookings", ["settlement_id"])
    op.create_index("ix_tsb_ma_nguon", "tour_settlement_bookings", ["ma_booking_nguon"])


def downgrade() -> None:
    for t in ("tour_settlement_bookings", "tour_guide_advances", "tour_settlement_cost_lines",
              "tour_settlement_costs", "tour_settlement_lines"):
        op.drop_table(t)
    for ten, _ in COT_LOP1:
        op.drop_column("tour_settlements", ten)
