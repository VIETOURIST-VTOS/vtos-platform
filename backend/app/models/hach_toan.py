"""Quy tắc hạch toán: bảng quy ước máy đọc được, thay cho tệp Excel và trí nhớ của kế toán.

Nguyên tắc: máy chạy quy tắc, người sửa quy tắc chứ không sửa từng bút toán.
Một quy tắc chỉ có hiệu lực khi đủ hai chữ ký (Chủ tịch + TGĐ), giống bảng tham số chính sách.
Sửa quy tắc không sửa bút toán đã ghi – bút toán cũ giữ nguyên dấu vết quy tắc đã sinh ra nó.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


# Nguồn nghiệp vụ mà quy tắc áp vào
NGUON = {
    "tien_vao": "Tiền vào tài khoản (sao kê ngân hàng)",
    "tien_ra": "Tiền ra tài khoản (sao kê ngân hàng)",
    "mua_vao": "Chi phí mua vào (đề nghị chi / hóa đơn NCC)",
    "quyet_toan": "Quyết toán tour / dịch vụ hoàn thành",
    "luong": "Bảng lương",
    "ket_chuyen": "Kết chuyển cuối kỳ",
}

# Cách lấy mã đối tượng cho dòng bút toán
DOI_TUONG = {
    "": "Không cần đối tượng",
    "khach": "Khách hàng của đơn",
    "ncc": "Nhà cung cấp trên đề nghị chi",
    "nhan_vien": "Nhân viên / HDV nhận tạm ứng",
    "ngan_hang": "Ngân hàng của tài khoản",
}

BEN_THUE = {"": "Không có thuế", "no": "Thuế ghi bên Nợ (GTGT đầu vào 133)", "co": "Thuế ghi bên Có (GTGT đầu ra 3331)"}

# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT R2 15/10/2026 — HÌNH THỨC THANH TOÁN NẰM TRONG KHÓA, KHÔNG PHẢI MỘT NHÁNH `if`
#
# Học trực tiếp từ bảng Tài khoản ngầm định của MISA (166 dòng, đọc 15/10/2026): mã loại chứng từ
# của họ GỘP CẢ NGHIỆP VỤ LẪN HÌNH THỨC THANH TOÁN — `TTKHTG` (thu khách bằng tiền gửi) là một mã
# KHÁC HẲN `TTKHTM` (bằng tiền mặt). Vì thế một nghiệp vụ như "mua hàng trong nước nhập kho"
# chiếm NĂM dòng của bảng, mỗi hình thức một dòng.
#
# CHỖ HỎNG CỦA VTOS TRƯỚC ĐỢT NÀY, đọc được trong `hach_toan.MAC_DINH`: mọi quy tắc tiền vào và
# tiền ra đều gõ cứng `1121` — tiền gửi ngân hàng. KHÔNG CÓ MỘT ĐƯỜNG NÀO ĐI RA 1111. Nghĩa là
# một phiếu thu tiền mặt tại quầy, hay một phiếu chi tiền mặt, nếu chạy qua bộ quy tắc thì ghi
# vào TÀI KHOẢN NGÂN HÀNG. Sổ vẫn cân, tổng tiền vẫn đúng, chỉ có quỹ tiền mặt và số dư ngân hàng
# cùng sai một khoản bằng nhau — và cái sai ấy chỉ lộ ra lúc đối chiếu sao kê, tức là muộn.
#
# SÁU HÌNH THỨC lấy đúng bộ của MISA. `""` nghĩa là quy tắc KHÔNG phụ thuộc hình thức thanh toán
# (lương, kết chuyển, khấu hao…), và nó khớp với mọi bối cảnh — xem luật "cụ thể thắng chung
# chung" ở `services/hach_toan.dang_hieu_luc`.
HINH_THUC_TT = {
    "":                 "Không phụ thuộc hình thức thanh toán",
    "tien_mat":         "Tiền mặt",
    "chuyen_khoan":     "Chuyển khoản",
    "sec_tien_mat":     "Séc tiền mặt",
    "sec_chuyen_khoan": "Séc chuyển khoản",
    "unc":              "Ủy nhiệm chi",
    "chua_tt":          "Chưa thanh toán",
}

# Hình thức nào chạy trên tài khoản NGÂN HÀNG. Séc tiền mặt nằm ở ĐÂY chứ không nằm bên tiền mặt,
# và đó không phải lỗi gõ: séc lĩnh tiền mặt vẫn rút trên tài khoản ngân hàng, nên vế tiền của nó
# là 112x. Đọc đúng như MISA khai. `test_r2_4` canh điều này theo cả hai chiều.
HTTT_QUA_NGAN_HANG = ("chuyen_khoan", "sec_tien_mat", "sec_chuyen_khoan", "unc")
HTTT_QUA_TIEN_MAT = ("tien_mat",)
TK_TIEN_MAT = "111"
TK_TIEN_GUI = "112"



class QuyTacHachToan(Base):
    """Một dòng quy ước: gặp nghiệp vụ thế này thì ghi Nợ tài khoản này – Có tài khoản kia."""
    __tablename__ = "quy_tac_hach_toan"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(40), index=True)          # TOUR_DOANH_THU – không unique vì có nhiều bản theo ngày hiệu lực
    ten: Mapped[str] = mapped_column(String(200))
    nguon: Mapped[str] = mapped_column(String(20), index=True)       # xem NGUON
    dieu_kien: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {"ma_bat_dau": ["KLE"], "chua": ["visa"], "khong_chua": [...], "loai_tour": [...], "muc_chi": [...]}
    tk_no: Mapped[str] = mapped_column(String(10))
    tk_co: Mapped[str] = mapped_column(String(10))
    tk_thue: Mapped[str] = mapped_column(String(10), default="")
    ben_thue: Mapped[str] = mapped_column(String(4), default="")     # no / co
    ty_le_thue: Mapped[float] = mapped_column(Float, default=0)      # 0.08 / 0.10 – 0 là không tách thuế
    doi_tuong: Mapped[str] = mapped_column(String(20), default="")   # xem DOI_TUONG
    can_cong_trinh: Mapped[bool] = mapped_column(Boolean, default=False)   # bắt buộc mã tour
    # ── Đợt R2 15/10/2026 ──────────────────────────────────────────────────────────────────────
    hinh_thuc_tt: Mapped[str] = mapped_column(String(20), default="", index=True)  # xem HINH_THUC_TT
    # Chiều KHOẢN MỤC CHI PHÍ, khai NGAY TRONG DÒNG QUY TẮC chứ không ở một bảng thứ hai.
    # Lý do gộp: VTOS vốn khai chiều bắt buộc rời ở `account_rule_check`, nên có HAI bảng cùng nói
    # về một dòng định khoản — và hai bảng thì sớm muộn lệch nhau mà không ai biết bảng nào đúng.
    # Một dòng ở đây nay nói đủ cả định khoản LẪN chiều phân tích bắt buộc đi kèm.
    can_khoan_muc: Mapped[bool] = mapped_column(Boolean, default=False)
    dien_giai: Mapped[str] = mapped_column(String(200), default="")  # mẫu diễn giải, {ma} {ten} {khach}
    uu_tien: Mapped[int] = mapped_column(Integer, default=100)       # số nhỏ xét trước
    can_cu: Mapped[str] = mapped_column(String(200), default="")     # điều khoản TT99 / quyết định nội bộ
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Hiệu lực và chữ ký – y hệt bảng tham số chính sách
    effective_from: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending / active / rejected / ngung
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    proposed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ThieuGiaVon(Base):
    """Hàng đợi cổng chặn: đơn có doanh thu mà chưa có giá vốn thì không được ghi doanh thu.

    Mọi đơn đều có doanh thu và giá vốn (quyết định 08/9/2026 của Chủ tịch). Thiếu giá vốn là
    thiếu dữ liệu, không phải bản chất khác – nên đơn nằm chờ ở đây cho tới khi Điều hành nhập đủ.
    """
    __tablename__ = "thieu_gia_von"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma_don: Mapped[str] = mapped_column(String(60), unique=True, index=True)   # mã tour / mã dịch vụ lẻ
    ky: Mapped[str] = mapped_column(String(7), default="", index=True)         # 2026-08
    ten: Mapped[str] = mapped_column(String(300), default="")
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ly_do: Mapped[str] = mapped_column(String(200), default="")   # thieu_gia_von / thieu_dien_giai / gia_von_am
    phong_ban: Mapped[str] = mapped_column(String(40), default="dieu_hanh")
    nguoi_phu_trach: Mapped[str] = mapped_column(String(120), default="")
    trang_thai: Mapped[str] = mapped_column(String(20), default="cho")         # cho / da_bo_sung / bo_qua
    giai_trinh: Mapped[str] = mapped_column(Text, default="")
    nguoi_xu_ly: Mapped[str] = mapped_column(String(50), default="")
    xu_ly_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    phat_hien_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
