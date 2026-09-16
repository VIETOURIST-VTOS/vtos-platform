# -*- coding: utf-8 -*-
"""SỔ TỶ GIÁ – tỷ giá ngoại tệ của TỪNG NGÀY, do người nhập, có chứng từ đi kèm.

Chủ tịch chốt 16/9/2026: *"tỷ giá để nhân viên tự nhập tại từng thời điểm; tạo form để nhân viên tự
nhập tay và tải tệp/ảnh."* Tệp này là cái trục của việc ấy.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO PHẢI CÓ SỔ, KHI TỪNG DÒNG TIỀN ĐÃ CÓ CỘT `ty_gia` RỒI
────────────────────────────────────────────────────────────────────────────────

Quy tắc quy đổi của VTOS đã có và không đổi: người khai `tien_te`, `so_tien_goc`, `ty_gia` và
`ngay_ty_gia` trên từng khoản, rồi MÁY NHÂN (`quyet_toan_lop3.quy_doi`). Người không gõ số VND bên
cạnh số gốc và tỷ giá, vì gõ tay cả ba là mở đường cho ba con số không khớp nhau.

Chỗ hở không nằm ở phép nhân. Nó nằm ở chỗ **mỗi người tự nhớ lấy tỷ giá**:

    Đo trên tệp quyết toán UK: HAI tỷ giá GBP khác nhau trong CÙNG MỘT TỆP – 36.000 ở sheet chiết
    tính và 35.944 ở sheet quyết toán. Riêng trên giá land 692,34 GBP × 43 khách, 56 đồng chênh ấy
    là 1.667.155 đ.

    Đo trên 21 tệp quyết toán visa T1–T6/2026: tỷ giá nằm rải trong ô đầu bảng, mỗi tệp một chỗ –
    CAD 19.000, USD 25.500, AUD 18.500 – và không tệp nào ghi tỷ giá ấy lấy từ đâu, ngày nào.

Sổ này là chỗ để trả lời "tỷ giá AUD ngày 04/04/2026 là bao nhiêu, ai nói thế, và bằng chứng đâu".

────────────────────────────────────────────────────────────────────────────────
SỔ NÀY LÀ BẢN THAM CHIẾU, KHÔNG PHẢI QUAN TOÀ
────────────────────────────────────────────────────────────────────────────────

Nó KHÔNG tự động thay tỷ giá đã khai trên một khoản. Từng khoản vẫn giữ `ty_gia` và `ngay_ty_gia`
của chính nó, vì tỷ giá của một khoản là tỷ giá NGÀY CHI THẬT của khoản ấy – một sự thật đã xảy ra,
không được sửa lùi khi sổ đổi.

Việc của sổ là: điền sẵn vào form cho người nhập, và làm lộ ra khi hai người khai hai con số khác
nhau cho cùng một ngày. Máy không chọn hộ.

────────────────────────────────────────────────────────────────────────────────
BA ĐIỀU ĐƯỢC ÉP TRONG CẤU TRÚC
────────────────────────────────────────────────────────────────────────────────

1. `ty_gia` KHÔNG dùng kiểu `TIEN`. `app/models/kieu_tien.py` nói rõ: TIEN chỉ cho cột tiền, không
   cho tỷ lệ và hệ số. Tỷ giá là một TỶ LỆ – 2 chữ số thập phân của TIEN sẽ cắt mất tỷ giá của
   những đồng tiền yếu (1 KRW ≈ 0,0181 đ; làm tròn 2 số thành 0,02 là sai 10%). Sáu chữ số thập
   phân đủ cho cả hai đầu.

2. MỘT NGUỒN, MỘT NGÀY, MỘT ĐỒNG TIỀN → MỘT DÒNG (chỉ mục duy nhất). Nhưng HAI NGUỒN khác nhau
   trong cùng một ngày thì được phép khác nhau, và phải khác nhau: "Vietcombank bán ra" và "tỷ giá
   trên hợp đồng với đối tác" là hai sự thật khác nhau, gộp làm một là bịa.

3. SỬA THÌ PHẢI NÓI VÌ SAO, và lần sửa cũ không biến mất. `lich_su` giữ lại từng lần: số cũ, số
   mới, ai sửa, lúc nào, lý do. Một con số tỷ giá sửa âm thầm là một khoản chênh lệch không ai
   truy được.

Chứng từ (ảnh chụp bảng tỷ giá ngân hàng, sao kê, hợp đồng) gắn qua kho hồ sơ chung với
`doi_tuong = "ty_gia"` – xem `app/models/attachments.py`. Không dựng kho ảnh riêng: một kho chung
là một bộ quy tắc chung về kích thước, loại tệp, ai xem được, và thu hồi thay vì xoá.
"""
from datetime import date, datetime

from sqlalchemy import DateTime, Date, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Tỷ giá là TỶ LỆ, không phải tiền – xem điểm 1 ở đầu tệp. 18 chữ số, 6 chữ số thập phân.
TY_GIA_KIEU = Numeric(18, 6, asdecimal=False)

# Đồng tiền hệ đang thật sự gặp, đo trên kho quyết toán T1–T6/2026 và bộ quyết toán tour nước ngoài.
# Danh sách này để GỢI Ý trong form, KHÔNG phải để chặn: gặp đồng tiền lạ thì vẫn nhập được, vì
# chặn một đồng tiền có thật là đẩy người dùng sang gõ tay ra ngoài hệ.
DONG_TIEN_HAY_GAP = {
    "USD": "Đô la Mỹ",
    "EUR": "Euro",
    "AUD": "Đô la Úc",
    "CAD": "Đô la Canada",
    "GBP": "Bảng Anh",
    "JPY": "Yên Nhật",
    "KRW": "Won Hàn",
    "CNY": "Nhân dân tệ",
    "SGD": "Đô la Singapore",
    "THB": "Baht Thái",
    "TWD": "Đô la Đài Loan",
    "HKD": "Đô la Hồng Kông",
}

# Loại giá. Rỗng CÓ NGHĨA: người nhập không biết đây là giá mua hay giá bán – và để trống thì còn
# hỏi lại được, còn mặc định vào "bán ra" thì con số sai nằm im trong sổ mãi mãi.
LOAI_GIA = {
    "": "Không ghi rõ",
    "mua_vao": "Mua vào",
    "ban_ra": "Bán ra",
    "chuyen_khoan": "Chuyển khoản",
    "thuc_te": "Thực tế đã chi/đã thu",
}


class TyGia(Base):
    """Một dòng sổ tỷ giá: một đồng tiền, một ngày, một nguồn."""
    __tablename__ = "ty_gia"
    __table_args__ = (
        Index("ix_ty_gia_tra_cuu", "tien_te", "ngay"),
        # Một nguồn nói một lần cho một ngày. Đặt bằng CHỈ MỤC duy nhất chứ không bằng ràng buộc
        # trên cột: SQLite (máy lập trình) không thêm ràng buộc vào bảng đã tạo, chỉ mục thì cả hai
        # môi trường đều tạo được – nên hai bên chạy cùng một lược đồ.
        Index("ux_ty_gia_mot_nguon_mot_ngay", "tien_te", "ngay", "nguon", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tien_te: Mapped[str] = mapped_column(String(3))                  # luôn viết HOA: USD, AUD…
    ngay: Mapped[date] = mapped_column(Date)                         # ngày của tỷ giá, không phải ngày nhập
    ty_gia: Mapped[float] = mapped_column(TY_GIA_KIEU)               # 1 đơn vị ngoại tệ = bao nhiêu VND
    nguon: Mapped[str] = mapped_column(String(60), default="")       # "Vietcombank", "hợp đồng đối tác"…
    loai_gia: Mapped[str] = mapped_column(String(20), default="")    # khoá trong LOAI_GIA
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Ai nhập, lúc nào. Tỷ giá là con số nhân vào tiền – phải biết người chịu trách nhiệm cho nó.
    nguoi_nhap: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Từng lần sửa, nối thêm chứ không ghi đè. Xem điểm 3 ở đầu tệp.
    lich_su: Mapped[str] = mapped_column(Text, default="")
    so_lan_sua: Mapped[int] = mapped_column(Integer, default=0)
