"""CG-1 · Cổng kết nối VTD — TÀI KHOẢN BÊN NGOÀI (khách hàng, đối tác, cổ đông) và MÃ XÁC THỰC.

Chủ tịch duyệt bản xem thử 26/10/2026 (dựng từ đúng bộ giao diện v3.2): trang mở đầu bốn ô thay màn
đăng nhập VTOS; Nội bộ vào bằng tài khoản VTOS như cũ; ba cổng ngoài đăng nhập bằng MÃ MỘT LẦN gửi qua
Zalo hoặc Email, người dùng tự chọn kênh.

TÁCH HẲN khỏi bảng `users`. Một tài khoản bên ngoài không bao giờ là một `User`: không có vai trò VTOS,
không ký được phiên VTOS (khoá ký riêng — xem services/cong_ngoai), nên không có đường nào để nó chạm
vào một màn hình hay một cửa API nội bộ. Gộp vào `users` rồi "chặn bằng vai trò" là đặt cả mặt ngoài
của công ty lên đúng một dòng `if`.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

LOAI_NGOAI = {"khach_hang": "Khách hàng", "doi_tac": "Đối tác", "co_dong": "Cổ đông"}
LOAI_DOI_TAC = {"ncc": "Nhà cung cấp", "dai_ly": "Đại lý", "ctv_ban_hang": "Cộng tác viên bán hàng"}
# hoat_dong: dùng được · cho_duyet: đối tác/cổ đông đã gửi hồ sơ, chờ VTOS duyệt · ho_so: mới xác thực
# liên hệ, chưa gửi hồ sơ · bo_sung: VTOS yêu cầu bổ sung · tu_choi · khoa
TRANG_THAI_NGOAI = {"ho_so": "Chưa gửi hồ sơ", "cho_duyet": "Chờ duyệt", "bo_sung": "Cần bổ sung",
                    "hoat_dong": "Đang hoạt động", "tu_choi": "Từ chối", "khoa": "Đã khoá"}
KENH_MA = {"zalo": "Zalo", "email": "Email"}


class TaiKhoanNgoai(Base):
    __tablename__ = "tai_khoan_ngoai"
    __table_args__ = (Index("ix_tkn_loai_dt", "loai", "dien_thoai"), Index("ix_tkn_loai_email", "loai", "email"))
    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(20))                    # khach_hang / doi_tac / co_dong
    ho_ten: Mapped[str] = mapped_column(String(160), default="")
    dien_thoai: Mapped[str] = mapped_column(String(20), default="")  # đã chuẩn hoá 0xxxxxxxxx
    email: Mapped[str] = mapped_column(String(160), default="")      # chữ thường
    trang_thai: Mapped[str] = mapped_column(String(20), default="ho_so")
    # Hồ sơ đối tác / cổ đông — do chính người ấy khai ở cổng, VTOS đối chiếu rồi duyệt.
    loai_doi_tac: Mapped[str] = mapped_column(String(20), default="")
    ten_don_vi: Mapped[str] = mapped_column(String(200), default="")
    ma_so_thue: Mapped[str] = mapped_column(String(20), default="")
    giay_to: Mapped[str] = mapped_column(String(40), default="")     # CCCD / mã số doanh nghiệp (cổ đông)
    tk_luu_ky: Mapped[str] = mapped_column(String(40), default="")
    ghi_chu_ho_so: Mapped[str] = mapped_column(Text, default="")
    gui_ho_so_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do: Mapped[str] = mapped_column(String(300), default="")      # lý do từ chối / bổ sung / khoá
    dong_y_dieu_khoan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nhan_tin_quang_cao: Mapped[bool] = mapped_column(default=False)   # không bao giờ tự bật
    kenh_ua_thich: Mapped[str] = mapped_column(String(10), default="")
    so_thich: Mapped[str] = mapped_column(String(40), default="")        # KH-1: sở thích khách tự chọn (cá nhân hoá gợi ý)
    # DT-1: tài khoản đối tác NỐI vào đúng một đối tác bán hàng trên VTOS — người duyệt xác nhận, máy
    # chỉ gợi ý (khớp MST trước, rồi SĐT). Rỗng = chưa nối: cổng không hiện số liệu nào.
    doi_tac_id: Mapped[int | None] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), nullable=True, index=True)
    # NCC-1: tài khoản nhà cung cấp NỐI vào đúng một NCC trong danh mục `suppliers` (gợi ý MST → SĐT, TP Điều hành nối).
    ncc_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)
    # Tăng lên là mọi phiên đã cấp mất hiệu lực ngay (đăng xuất mọi nơi, khoá tài khoản).
    phien: Mapped[int] = mapped_column(Integer, default=1)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    dang_nhap_cuoi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MaXacThucNgoai(Base):
    """Một lần gửi mã. Lưu BĂM của mã, không lưu mã; dùng một lần; 5 phút; sai 5 lần là chết."""
    __tablename__ = "ma_xac_thuc_ngoai"
    id: Mapped[int] = mapped_column(primary_key=True)
    khoa: Mapped[str] = mapped_column(String(48), unique=True, index=True)   # mã phiên gửi, trả cho trình duyệt
    loai: Mapped[str] = mapped_column(String(20))
    kenh: Mapped[str] = mapped_column(String(10))
    lien_he: Mapped[str] = mapped_column(String(160), index=True)
    ma_bam: Mapped[str] = mapped_column(String(64))
    het_han: Mapped[datetime] = mapped_column(DateTime)
    so_lan_sai: Mapped[int] = mapped_column(Integer, default=0)
    da_dung: Mapped[bool] = mapped_column(default=False)
    ip: Mapped[str] = mapped_column(String(64), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
