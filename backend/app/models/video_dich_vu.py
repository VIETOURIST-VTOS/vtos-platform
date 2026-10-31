"""KS-16f · VIDEO KHÁCH SẠN VTD VÀ NHÀ HÀNG (Chủ tịch duyệt bản xem thử 31/10/2026).

  · Mức chuẩn (chỉ nhắc, không chặn): khách sạn 3 video (tổng quan · phòng · trải nghiệm), nhà hàng 2 video
    (không gian · món đặc sản). Tối đa 5 video mỗi cơ sở, mỗi video ≤ 100 MB (MP4 / MOV / WebM).
  · Tải lên là hiện (như ảnh sau KS-16c). Người tải tự xóa; TP Điều hành, Chủ tịch, TGĐ ẩn / xóa mọi video.
  · Bắt buộc ghi nguồn và xác nhận Vietourist được phép dùng video cho khách xem.
  · Tệp đi thẳng vào kho R2 theo từng phần 8 MB (multipart) — máy chủ 512 MB không giữ cả tệp.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

LOAI_VIDEO_KS = {"tong_quan": "Tổng quan (mặt tiền, sảnh, vị trí, tiện ích)", "phong": "Phòng — gắn loại phòng",
                 "trai_nghiem": "Trải nghiệm (hồ bơi, buffet sáng, spa, vui chơi)", "khac": "Khác"}
LOAI_VIDEO_NH = {"khong_gian": "Không gian (phòng riêng, khu khách đoàn)", "mon": "Món đặc sản — gắn món",
                 "thuc_don": "Thực đơn đoàn / tiệc — gắn thực đơn", "khac": "Khác"}
CHUAN_KS = ("tong_quan", "phong", "trai_nghiem")
CHUAN_NH = ("khong_gian", "mon")
GOI_Y_GIAY = {"tong_quan": (45, 90), "phong": (30, 60), "trai_nghiem": (30, 60), "khong_gian": (30, 60),
              "mon": (30, 60), "thuc_don": (30, 60), "khac": (30, 90)}
TRANG_THAI_VIDEO = {"dang_tai": "Đang tải lên", "hien": "Đang hiện", "an": "Ẩn", "xoa": "Đã xóa"}


class VideoDichVu(Base):
    __tablename__ = "video_dich_vu"
    id: Mapped[int] = mapped_column(primary_key=True)
    doi_tuong: Mapped[str] = mapped_column(String(20), index=True)          # khach_san_vtd | nha_hang
    doi_tuong_id: Mapped[int] = mapped_column(Integer, index=True)
    loai: Mapped[str] = mapped_column(String(16), default="khac")
    loai_phong_id: Mapped[int | None] = mapped_column(ForeignKey("loai_phong_vtd.id"), nullable=True)
    mon_id: Mapped[int | None] = mapped_column(ForeignKey("mon_nha_hang.id"), nullable=True)
    thuc_don_id: Mapped[int | None] = mapped_column(ForeignKey("thuc_don_nha_hang.id"), nullable=True)
    tieu_de: Mapped[str] = mapped_column(String(160), default="")
    nguon: Mapped[str] = mapped_column(String(200), default="")
    xac_nhan_quyen: Mapped[bool] = mapped_column(Boolean, default=False)
    ten_tep: Mapped[str] = mapped_column(String(200), default="")
    kieu: Mapped[str] = mapped_column(String(40), default="video/mp4")
    kich_thuoc: Mapped[int] = mapped_column(Integer, default=0)
    thoi_luong: Mapped[int] = mapped_column(Integer, default=0)              # giây, trình duyệt đọc lúc chọn tệp
    khoa_luu: Mapped[str] = mapped_column(String(200), default="")
    ma_tai: Mapped[str] = mapped_column(String(300), default="")             # UploadId multipart
    phan: Mapped[list] = mapped_column(JSON, default=list)                   # [[số phần, etag], …]
    anh_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)   # ảnh đại diện (webp)
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    la_gioi_thieu: Mapped[bool] = mapped_column(Boolean, default=False)
    trang_thai: Mapped[str] = mapped_column(String(10), default="dang_tai", index=True)
    tai_boi: Mapped[str] = mapped_column(String(50), default="")
    tai_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    xong_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    an_boi: Mapped[str] = mapped_column(String(50), default="")
