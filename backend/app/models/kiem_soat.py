"""Robot Kiểm soát: những gì nó phát hiện, chấm và báo cáo.

Vị trí Kiểm soát do AI giữ (chỉ đạo anh Trần Tuấn 07/9/2026): kiểm tra, thử, giám sát và báo cáo mọi
phòng ban về Chủ tịch. Ba bảng dưới đây là toàn bộ dấu vết nó để lại, và cả ba đều KHÔNG phải dữ liệu
nghiệp vụ – robot không sửa được một con số nào của phòng ban mà nó giám sát.

Vì sao chấm điểm phải có trạng thái hậu kiểm: chấm điểm con người là ô rủi ro cao nhất trong bảng
quyền AI. Điểm do máy đặt ra là ĐỀ XUẤT cho tới khi Chủ tịch xem; một điểm số máy chấm mà đi thẳng
vào hồ sơ nhân sự thì không ai đối chất được với nó.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Mức nghiêm trọng của một phát hiện. Chỉ "do" mới kích hoạt báo cáo gửi Chủ tịch – anh Tuấn chốt
# 07/9/2026: không báo cáo định kỳ, chỉ báo khi có việc nghiêm trọng.
MUC_KS = {"do": "Nghiêm trọng", "vang": "Cần rà soát", "xanh": "Ghi nhận"}

LOAI_PHAT_HIEN = {
    "may_chu_loi": "Màn hình làm máy chủ lỗi",
    "quyen_lech": "Ẩn khỏi menu nhưng API vẫn mở",
    "vai_tro_trong": "Vai trò đăng nhập được nhưng không mở được màn hình nào",
    "mach_migration": "Mạch nâng cấp cơ sở dữ liệu có nhiều hơn một đầu",
    "ngoai_le_ton": "Ngoại lệ nghiêm trọng tồn quá lâu không ai xử lý",
    "so_lieu_bat_thuong": "Số liệu bất thường của một phòng ban",
    "ai_chua_hau_kiem": "Nội dung AI mức 3 chưa ai hậu kiểm",
    "cot_tien_float": "Cột tiền còn khai kiểu số thực nhị phân",
    "thieu_khac_0": "Cột tiền ghi 0 thay cho “chưa có số”",
    "vai_tro_khong_co_nguoi": "Vai trò có quyền nhưng chưa tài khoản nào giữ",
    "nhap_tay_bat_thuong": "Số nhân viên nhập tay có dấu hiệu bất thường",
}


class KsPhatHien(Base):
    """Một việc robot Kiểm soát tìm ra. `ma` ổn định để lần quét sau không đẻ ra bản trùng."""
    __tablename__ = "ks_phat_hien"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    loai: Mapped[str] = mapped_column(String(24), index=True)      # LOAI_PHAT_HIEN
    muc: Mapped[str] = mapped_column(String(6), default="vang")    # MUC_KS
    phong_ban: Mapped[str] = mapped_column(String(60), default="") # phòng phải trả lời; rỗng = toàn hệ thống
    vai_tro: Mapped[str] = mapped_column(String(30), default="")
    doi_tuong: Mapped[str] = mapped_column(String(120), default="")
    tom_tat: Mapped[str] = mapped_column(Text, default="")
    chi_tiet: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lan_dau: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    lan_cuoi: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    so_lan: Mapped[int] = mapped_column(Integer, default=1)
    con: Mapped[bool] = mapped_column(Boolean, default=True, index=True)   # lần quét gần nhất còn thấy
    da_bao_cao: Mapped[bool] = mapped_column(Boolean, default=False)


class KsDiem(Base):
    """Nhận xét và điểm của một phòng ban trong một kỳ – ĐỀ XUẤT cho tới khi Chủ tịch hậu kiểm."""
    __tablename__ = "ks_diem"
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)          # YYYY-MM
    phong_ban: Mapped[str] = mapped_column(String(60), index=True)
    # RỖNG khi chưa đủ cơ sở chấm. Để 0 thì cột này đọc ra là "phòng làm kém" – mà chưa có
    # số liệu và làm kém là hai chuyện khác nhau; số 0 không nói được điều đó.
    diem: Mapped[float | None] = mapped_column(Float, nullable=True)   # 0–100, rỗng = chưa đủ cơ sở
    can_cu: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # từng chỉ tiêu và số thật
    nhan_xet: Mapped[str] = mapped_column(Text, default="")
    du_co_so: Mapped[bool] = mapped_column(Boolean, default=True)   # False = chưa đủ dữ liệu để chấm
    trang_thai: Mapped[str] = mapped_column(String(16), default="cho_hau_kiem", index=True)
    hau_kiem_boi: Mapped[str] = mapped_column(String(50), default="")
    hau_kiem_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hau_kiem_ghi_chu: Mapped[str] = mapped_column(String(400), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class KsBaoCao(Base):
    """Báo cáo gửi Chủ tịch. Chỉ sinh khi có việc NGHIÊM TRỌNG – không có báo cáo định kỳ."""
    __tablename__ = "ks_bao_cao"
    id: Mapped[int] = mapped_column(primary_key=True)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    ly_do: Mapped[str] = mapped_column(String(200), default="")     # điều gì đã kích hoạt báo cáo
    so_do: Mapped[int] = mapped_column(Integer, default=0)
    so_vang: Mapped[int] = mapped_column(Integer, default=0)
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    ma_phat_hien: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    da_xem: Mapped[bool] = mapped_column(Boolean, default=False)
    xem_boi: Mapped[str] = mapped_column(String(50), default="")
    xem_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
