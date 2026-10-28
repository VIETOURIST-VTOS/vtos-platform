"""NCC-1 · Cổng Nhà cung cấp N01–N18 (Chủ tịch duyệt bản xem thử 28/10/2026).

Cổng dựng trên dữ liệu ĐÃ CÓ: danh mục `suppliers`, đơn `service_orders`, đề nghị chi `payment_requests`,
đổi tài khoản hai người `supplier_bank_changes`, danh mục `nha_hang` / `thuc_don_nha_hang`. Bảng mới ở đây
chỉ giữ những gì cổng thêm vào:

  · `phan_hoi_don_ncc`   — mỗi lần NCC xác nhận / từ chối / gửi chứng từ cho một đơn dịch vụ.
  · `gia_ncc`            — giá mua đang áp dụng theo khoảng ngày (CHỈ sinh ra khi Điều hành duyệt đề xuất).
  · `de_xuat_gia_ncc`    — NCC đề xuất giá / thực đơn; Điều hành duyệt hoặc từ chối.
  · `ban_ke_ncc` + dòng  — Kế toán lập bản kê theo kỳ từ đơn; NCC xác nhận hoặc báo chênh lệch từng dòng.
  · `de_nghi_ncc`        — đề nghị của NCC (thanh toán, đối chiếu, chứng từ…). KHÔNG tự thành phiếu chi.
  · `hoc_lieu_doi_tac`   — học liệu / thương hiệu VTOS đưa lên cho NCC, đại lý, CTV.

Tất cả bắt đầu RỖNG.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

HANH_DONG_DON = {"xac_nhan": "Xác nhận đơn", "tu_choi": "Từ chối", "chung_tu": "Bổ sung chứng từ"}
TRANG_THAI_DE_XUAT = {"cho": "Chờ Điều hành duyệt", "duyet": "Đã duyệt · đang áp dụng", "tu_choi": "Từ chối"}
TRANG_THAI_BAN_KE = {"cho_ncc": "Chờ NCC xác nhận", "co_chenh_lech": "NCC báo chênh lệch", "da_xac_nhan": "NCC đã xác nhận · khóa"}
LOAI_DE_NGHI = {"thanh_toan": "Đề nghị thanh toán", "doi_chieu": "Đối chiếu công nợ", "chung_tu": "Bổ sung chứng từ",
                "dieu_chinh": "Điều chỉnh dịch vụ", "hop_tac": "Hợp tác / hỗ trợ"}
BO_PHAN_DE_NGHI = {"thanh_toan": "ketoan", "doi_chieu": "ketoan", "chung_tu": "ketoan", "dieu_chinh": "dieu_hanh", "hop_tac": "dieu_hanh"}
TRANG_THAI_DE_NGHI = {"moi": "Mới gửi", "dang_xu_ly": "Đang xử lý", "xong": "Đã xử lý", "tu_choi": "Từ chối"}
NHOM_HOC_LIEU = {"quy_trinh": "Quy trình phục vụ / bán", "san_pham": "Giới thiệu sản phẩm", "thuong_hieu": "Thương hiệu"}
DANH_CHO = {"ncc": "Nhà cung cấp", "dai_ly": "Đại lý", "ctv_ban_hang": "Cộng tác viên"}
NHA_HANG_TT = {"cho": "Chờ nhà hàng nhận", "nhan": "Nhà hàng đã nhận bàn", "tu_choi": "Nhà hàng từ chối"}


class PhanHoiDonNcc(Base):
    __tablename__ = "phan_hoi_don_ncc"
    id: Mapped[int] = mapped_column(primary_key=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id"), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    hanh_dong: Mapped[str] = mapped_column(String(10))
    ma_xac_nhan: Mapped[str] = mapped_column(String(100), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    xu_ly_boi: Mapped[str] = mapped_column(String(50), default="")      # Điều hành xử lý lời từ chối
    xu_ly_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GiaNcc(Base):
    __tablename__ = "gia_ncc"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    dich_vu: Mapped[str] = mapped_column(String(200))
    don_vi: Mapped[str] = mapped_column(String(30), default="")
    gia: Mapped[float] = mapped_column(TIEN)
    so_luong_mo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tu_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_khong_phuc_vu: Mapped[str] = mapped_column(String(300), default="")
    thay_cho_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    het_hieu_luc: Mapped[bool] = mapped_column(Boolean, default=False)
    de_xuat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DeXuatGiaNcc(Base):
    __tablename__ = "de_xuat_gia_ncc"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    loai: Mapped[str] = mapped_column(String(10), default="gia")        # gia | thuc_don
    gia_ncc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)     # cập nhật dòng giá đang áp dụng
    thuc_don_id: Mapped[int | None] = mapped_column(Integer, nullable=True)    # cập nhật thực đơn nhà hàng
    nha_hang_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dich_vu: Mapped[str] = mapped_column(String(200), default="")
    don_vi: Mapped[str] = mapped_column(String(30), default="")
    gia: Mapped[float] = mapped_column(TIEN)
    gia_tre_em: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong_mo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tu_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_khong_phuc_vu: Mapped[str] = mapped_column(String(300), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    trang_thai: Mapped[str] = mapped_column(String(10), default="cho", index=True)
    xu_ly_boi: Mapped[str] = mapped_column(String(50), default="")
    xu_ly_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do: Mapped[str] = mapped_column(Text, default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BanKeNcc(Base):
    __tablename__ = "ban_ke_ncc"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    ky: Mapped[str] = mapped_column(String(7))                           # YYYY-MM
    trang_thai: Mapped[str] = mapped_column(String(14), default="cho_ncc", index=True)
    tong: Mapped[float] = mapped_column(TIEN, default=0)
    lap_boi: Mapped[str] = mapped_column(String(50), default="")
    lap_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    xac_nhan_tk_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DongBanKeNcc(Base):
    __tablename__ = "dong_ban_ke_ncc"
    id: Mapped[int] = mapped_column(primary_key=True)
    ban_ke_id: Mapped[int] = mapped_column(ForeignKey("ban_ke_ncc.id"), index=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id"), index=True)
    ma_don: Mapped[str] = mapped_column(String(30), default="")
    noi_dung: Mapped[str] = mapped_column(String(300), default="")
    ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    gia_tri: Mapped[float] = mapped_column(TIEN, default=0)
    ncc_gia_tri: Mapped[float | None] = mapped_column(TIEN, nullable=True)   # số NCC báo khi chênh lệch
    ncc_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    tra_loi: Mapped[str] = mapped_column(Text, default="")                    # Kế toán trả lời dòng chênh lệch


class DeNghiNcc(Base):
    __tablename__ = "de_nghi_ncc"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    loai: Mapped[str] = mapped_column(String(12))
    bo_phan: Mapped[str] = mapped_column(String(12), default="ketoan")
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    noi_dung: Mapped[str] = mapped_column(Text)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(12), default="moi", index=True)
    tra_loi: Mapped[str] = mapped_column(Text, default="")
    xu_ly_boi: Mapped[str] = mapped_column(String(50), default="")
    xu_ly_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HocLieuDoiTac(Base):
    __tablename__ = "hoc_lieu_doi_tac"
    id: Mapped[int] = mapped_column(primary_key=True)
    tieu_de: Mapped[str] = mapped_column(String(200))
    nhom: Mapped[str] = mapped_column(String(12), default="quy_trinh")
    danh_cho: Mapped[list | None] = mapped_column(JSON, nullable=True)   # ["ncc", "dai_ly", "ctv_ban_hang"]
    attachment_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))
    hien: Mapped[bool] = mapped_column(Boolean, default=True)
    dang_boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    go_boi: Mapped[str] = mapped_column(String(50), default="")
