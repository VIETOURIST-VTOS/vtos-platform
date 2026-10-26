"""DH-1 · Hoa hồng đối tác bán hàng theo D06 (Chủ tịch chốt 26/10/2026, duyệt bản xem thử cùng ngày).

Bốn bảng, bốn trách nhiệm tách nhau:
  · `hinh_thuc_hoa_hong` — đối tác hưởng theo chương trình nào (đại lý D06 / CTV D06 / giá NET), có
    hiệu lực từ đầu một tháng. CHƯA CÓ DÒNG NÀO = CHƯA CHỌN = KHÔNG TÍNH. Không tự áp D06 cho ai.
  · `ky_hoa_hong` — một (đối tác × pháp nhân × tháng × chương trình). Số trên đây là BẢN ĐỌC NHANH dựng
    lại từ sổ; nguồn sự thật là sổ.
  · `so_hoa_hong` — sổ CHỈ GHI THÊM. Mỗi lần tính lại ghi phần CHÊNH (cơ bản / thưởng) so với đã ghi,
    kèm bản chụp nguồn doanh số. Hoàn / hủy sau khi chốt là một dòng âm vào ĐÚNG KỲ GỐC — không xoá,
    không sửa dòng cũ, không trừ vào tháng mới.
  · `chi_hoa_hong` — đề nghị chi lập từ một kỳ. Số đã trả chỉ tăng khi đề nghị chi ở trạng thái đã chi.

Tiền là SỐ NGUYÊN ĐỒNG (BigInteger). Tỷ lệ là basis point. Không float ở đâu trong phép tính.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, BigInteger, Date, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

HINH_THUC = {"dai_ly_d06": "Đại lý — hoa hồng D06", "ctv_d06": "CTV bán hàng — hoa hồng D06", "gia_net": "Giá NET (không hưởng D06)"}


class HinhThucHoaHong(Base):
    __tablename__ = "hinh_thuc_hoa_hong"
    id: Mapped[int] = mapped_column(primary_key=True)
    doi_tac_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), index=True)
    hinh_thuc: Mapped[str] = mapped_column(String(20))
    hieu_luc_tu: Mapped[date] = mapped_column(Date)           # luôn là ngày 1 của một tháng
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class KyHoaHong(Base):
    __tablename__ = "ky_hoa_hong"
    __table_args__ = (UniqueConstraint("doi_tac_id", "company_key", "ky", "chuong_trinh", name="uq_ky_hoa_hong"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    doi_tac_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    company_key: Mapped[int] = mapped_column(Integer, default=0)   # 0 = chưa gán pháp nhân (để khoá duy nhất bắt được)
    ky: Mapped[str] = mapped_column(String(7), index=True)          # YYYY-MM
    chuong_trinh: Mapped[str] = mapped_column(String(20))            # dai_ly_d06 / ctv_d06
    doanh_so: Mapped[int] = mapped_column(BigInteger, default=0)
    co_ban: Mapped[int] = mapped_column(BigInteger, default=0)
    thuong: Mapped[int] = mapped_column(BigInteger, default=0)
    trang_thai: Mapped[str] = mapped_column(String(12), default="mo")   # mo / da_chot
    revision: Mapped[int] = mapped_column(Integer, default=0)
    thu: Mapped[bool] = mapped_column(default=True)                 # tính thử (chương trình chưa có ngày hiệu lực)
    chot_boi: Mapped[str] = mapped_column(String(50), default="")
    chot_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tinh_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SoHoaHong(Base):
    __tablename__ = "so_hoa_hong"
    id: Mapped[int] = mapped_column(primary_key=True)
    ky_id: Mapped[int] = mapped_column(ForeignKey("ky_hoa_hong.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    thanh_phan: Mapped[str] = mapped_column(String(10))             # BASE / BONUS
    so_tien: Mapped[int] = mapped_column(BigInteger)                # có dấu
    doanh_so: Mapped[int] = mapped_column(BigInteger, default=0)    # doanh số của lần tính này
    sau_chot: Mapped[bool] = mapped_column(default=False)           # điều chỉnh ghi khi kỳ đã chốt
    nguon: Mapped[str] = mapped_column(Text, default="")            # JSON bản chụp nguồn doanh số
    ly_do: Mapped[str] = mapped_column(String(300), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ChiHoaHong(Base):
    __tablename__ = "chi_hoa_hong"
    id: Mapped[int] = mapped_column(primary_key=True)
    ky_id: Mapped[int] = mapped_column(ForeignKey("ky_hoa_hong.id"), index=True)
    payment_request_id: Mapped[int] = mapped_column(ForeignKey("payment_requests.id"), unique=True)
    so_tien: Mapped[int] = mapped_column(BigInteger)
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
