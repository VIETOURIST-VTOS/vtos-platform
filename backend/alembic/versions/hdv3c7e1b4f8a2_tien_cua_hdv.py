# -*- coding: utf-8 -*-
"""Phòng HDV Đợt 3 — sổ tạm ứng theo NGƯỜI, và đơn giá theo LOẠI TOUR.

HAI VIỆC, MỘT BẢN:

1. BẢNG `tam_ung_hdv`. Hôm nay tiền ứng cho hướng dẫn viên nằm ở `tour_guide_advances`, gắn vào
   `settlement_id` — tức gắn vào TỜ QUYẾT TOÁN, không gắn vào CON NGƯỜI. Nên câu "hướng dẫn viên này
   còn giữ bao nhiêu tiền công ty" không hỏi được; mà đó là câu phải trả lời TRƯỚC khi đưa tiếp một
   khoản ứng mới. Bảng mới KHÔNG thay bảng cũ: bảng cũ là dòng chi của một chuyến, bảng này là sổ
   của một người, hai cái trả lời hai câu khác nhau.

   Bốn cột tiền đều NULL được và KHÔNG mặc định (luật K2): "chưa nhận tiền" khác "nhận 0 đồng". Một
   khoản mới đề nghị mà `da_nhan` = 0 sẽ lẫn vào những khoản đã chi xong và trả về đúng 0.

   KHÔNG GỘP KHÁC CHỦ TIỀN, KHÁC LOẠI TIỀN — đặc tả v1.0 §06. Vì thế có `chu_tien` và `loai_tien`, và
   phép tính số dư trả về NHIỀU TÚI chứ không một con số. Tiền thu hộ khách là một túi riêng và không
   bao giờ bù trừ sang túi công ty: trộn vào là lấy tiền khách che một khoản công ty nợ.

2. CỘT `guide_rates.loai_tour`. Chủ tịch chốt 06/10/2026: thù lao theo ngày, và TUỲ LOẠI TOUR có phí
   khác nhau. Trước bản này bảng giá chỉ khoá theo tuyến, nên một tuyến chỉ có đúng một đơn giá —
   không nói được rằng dẫn đoàn nước ngoài tuyến ấy trả khác dẫn khách lẻ.

   Cột mặc định RỖNG, và rỗng nghĩa là "áp cho mọi loại tour", KHÔNG phải "chưa biết": mọi bản giá
   đang có đều là bản chung và phải giữ nguyên hiệu lực. Phép tra lấy bản khớp đúng loại trước, không
   có mới rơi về bản chung — làm ngược thì một bản chung mới ký sẽ che mất bản riêng đã có.

   Luật "bản mới hạ bản cũ" cũng phải thêm vế loại tour (xem app/api/v1/hr.py, guide_rate_sign): thiếu
   vế ấy thì một bản giá mới cho đoàn nước ngoài sẽ hạ luôn bản giá khách lẻ cùng tuyến.

KHÔNG DỰNG BẢNG THÙ LAO KỲ GHI TIỀN. Chủ tịch chốt 06/10: quyết toán tour là sổ gốc, bảng kỳ chỉ ĐỌC.
Bảng đối soát thù lao là một cửa tính lại mỗi lần mở, không có cột nào xuống cơ sở dữ liệu — chậm hơn
một bảng lưu sẵn, và đó là cái giá để không bao giờ có hai con số thù lao khác nhau cho cùng một chuyến.

Revision ID: hdv3c7e1b4f8a2
Revises: hdv2b5d8f3a1c7
"""
import sqlalchemy as sa
from alembic import op

revision = "hdv3c7e1b4f8a2"
down_revision = "hdv2b5d8f3a1c7"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "tam_ung_hdv",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("guide_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("guide_assignments.id"), nullable=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("chu_tien", sa.String(16), server_default="vietourist"),
        sa.Column("loai_tien", sa.String(3), server_default="VND"),
        # Bốn cột tiền: nullable, KHÔNG default. Xem chú thích đầu tệp.
        sa.Column("de_nghi", TIEN, nullable=True),
        sa.Column("da_nhan", TIEN, nullable=True),
        sa.Column("chi_ho_duyet", TIEN, nullable=True),
        sa.Column("da_nop_lai", TIEN, nullable=True),
        sa.Column("muc_dich", sa.String(200), server_default=""),
        sa.Column("trang_thai", sa.String(12), server_default="de_nghi"),
        sa.Column("ngay_de_nghi", sa.Date(), nullable=True),
        sa.Column("ngay_nhan", sa.Date(), nullable=True),
        sa.Column("ngay_tat_toan", sa.Date(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("nguoi_lap", sa.String(50), server_default=""),
        sa.Column("lap_luc", sa.DateTime(), nullable=True),
        sa.Column("sua_boi", sa.String(50), server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    for ten, cot in (("guide_id", ["guide_id"]), ("assignment_id", ["assignment_id"]),
                     ("tour_id", ["tour_id"]), ("company_id", ["company_id"]),
                     ("chu_tien", ["chu_tien"]), ("loai_tien", ["loai_tien"]),
                     ("trang_thai", ["trang_thai"])):
        op.create_index(f"ix_tam_ung_hdv_{ten}", "tam_ung_hdv", cot)
    op.create_index("ix_tam_ung_hdv_guide_trang_thai", "tam_ung_hdv", ["guide_id", "trang_thai"])
    op.create_index("ix_tam_ung_hdv_tui", "tam_ung_hdv", ["guide_id", "chu_tien", "loai_tien"])

    with op.batch_alter_table("guide_rates") as b:
        b.add_column(sa.Column("loai_tour", sa.String(20), server_default=""))
    op.create_index("ix_guide_rates_loai_tour", "guide_rates", ["loai_tour"])


def downgrade() -> None:
    op.drop_index("ix_guide_rates_loai_tour", table_name="guide_rates")
    with op.batch_alter_table("guide_rates") as b:
        b.drop_column("loai_tour")
    for ten in ("tui", "guide_trang_thai", "trang_thai", "loai_tien", "chu_tien",
                "company_id", "tour_id", "assignment_id", "guide_id"):
        op.drop_index(f"ix_tam_ung_hdv_{ten}", table_name="tam_ung_hdv")
    op.drop_table("tam_ung_hdv")
