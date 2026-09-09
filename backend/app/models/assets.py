"""Tài sản cố định & Công cụ dụng cụ – chi phí trả trước (theo phân hệ MISA "Tài sản cố định" và "Công cụ dụng cụ").

Cấu trúc bám sát MISA: mỗi tài sản/CCDC là một thẻ có nguyên giá, thời gian sử dụng, tài khoản nguyên giá –
hao mòn – chi phí, và các chiều theo dõi (đối tượng, công trình, bộ phận). Mỗi kỳ chạy "Tính khấu hao" /
"Phân bổ chi phí" sinh ra một bảng tính theo kỳ, Kế toán duyệt rồi ghi sổ thành một chứng từ tổng hợp.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

# Loại TSCĐ theo MISA (quyết định TK nguyên giá / hao mòn mặc định)
ASSET_KINDS = {
    "huu_hinh": {"ten": "TSCĐ hữu hình", "tk_nguyen_gia": "211", "tk_hao_mon": "2141"},
    "vo_hinh": {"ten": "TSCĐ vô hình", "tk_nguyen_gia": "213", "tk_hao_mon": "2143"},
    "thue_tc": {"ten": "TSCĐ thuê tài chính", "tk_nguyen_gia": "212", "tk_hao_mon": "2142"},
    "bds_dt": {"ten": "Bất động sản đầu tư", "tk_nguyen_gia": "217", "tk_hao_mon": "2147"},
}
ASSET_STATUS = {"dang_dung": "Đang sử dụng", "ngung_kh": "Ngừng trích khấu hao", "thanh_ly": "Đã thanh lý / nhượng bán"}
# Loại chi phí trả trước / CCDC theo MISA
PREPAID_KINDS = {
    "ccdc": {"ten": "Công cụ dụng cụ", "tk_von": "242"},
    "cp_tra_truoc": {"ten": "Chi phí trả trước", "tk_von": "242"},
}
PREPAID_STATUS = {"dang_pb": "Đang phân bổ", "ngung_pb": "Ngừng phân bổ", "het": "Đã phân bổ hết", "ghi_giam": "Đã ghi giảm"}


class FixedAsset(Base):
    """Thẻ tài sản cố định (MISA: Tài sản cố định ▸ Ghi tăng). Khấu hao đường thẳng theo tháng."""
    __tablename__ = "fixed_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)      # TS0001 / mã TSCĐ trên MISA
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="huu_hinh")           # huu_hinh / vo_hinh / thue_tc / bds_dt
    group: Mapped[str] = mapped_column(String(60), default="")                  # nhóm TSCĐ (nhà cửa, phương tiện vận tải…)
    # Tài khoản hạch toán (mặc định lấy theo ASSET_KINDS, cho phép sửa từng thẻ như MISA)
    asset_account: Mapped[str] = mapped_column(String(10), default="211")       # TK nguyên giá
    depr_account: Mapped[str] = mapped_column(String(10), default="2141")       # TK hao mòn lũy kế
    expense_account: Mapped[str] = mapped_column(String(10), default="6424")    # TK chi phí khấu hao
    # Các chiều theo dõi (giống 4 chiều đối tượng của sổ VTOS)
    partner_code: Mapped[str] = mapped_column(String(60), default="")           # nhà cung cấp
    project_code: Mapped[str] = mapped_column(String(40), default="")           # công trình (tour/dự án)
    department: Mapped[str] = mapped_column(String(20), default="")             # bộ phận sử dụng
    # Nguyên giá & khấu hao
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)     # ngày mua
    start_date: Mapped[date] = mapped_column(Date)                              # ngày bắt đầu tính khấu hao
    cost: Mapped[float | None] = mapped_column(TIEN)                       # nguyên giá, nullable=True
    depr_months: Mapped[int] = mapped_column(Integer, default=0)                # thời gian sử dụng (tháng); 0 = không trích
    salvage: Mapped[float | None] = mapped_column(TIEN)                    # giá trị thu hồi ước tính, nullable=True
    opening_accumulated: Mapped[float | None] = mapped_column(TIEN)        # hao mòn lũy kế khi nạp số dư ban đầu, nullable=True
    opening_period: Mapped[str] = mapped_column(String(7), default="")          # kỳ tương ứng số dư ban đầu (YYYY-MM)
    # Trạng thái
    status: Mapped[str] = mapped_column(String(20), default="dang_dung")
    disposed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    note: Mapped[str] = mapped_column(String(300), default="")
    source: Mapped[str] = mapped_column(String(20), default="vtos")             # vtos / misa
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AssetDepreciation(Base):
    """Một dòng bảng tính khấu hao của một kỳ (MISA: Tính khấu hao TSCĐ). Ghi sổ cả bảng thành 1 chứng từ."""
    __tablename__ = "asset_depreciations"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("fixed_assets.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)                  # 2026-09
    amount: Mapped[float | None] = mapped_column(TIEN)                     # khấu hao trong kỳ, nullable=True
    accumulated: Mapped[float | None] = mapped_column(TIEN)                # lũy kế đến hết kỳ, nullable=True
    remaining: Mapped[float | None] = mapped_column(TIEN)                  # giá trị còn lại cuối kỳ, nullable=True
    entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)        # chứng từ ghi sổ
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PrepaidExpense(Base):
    """Thẻ công cụ dụng cụ / chi phí trả trước (MISA: Công cụ dụng cụ ▸ Ghi tăng). Phân bổ đều theo tháng vào TK 242."""
    __tablename__ = "prepaid_expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)      # CC0001
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="ccdc")              # ccdc / cp_tra_truoc
    asset_account: Mapped[str] = mapped_column(String(10), default="242")       # TK chờ phân bổ
    expense_account: Mapped[str] = mapped_column(String(10), default="6423")    # TK chi phí nhận phân bổ
    partner_code: Mapped[str] = mapped_column(String(60), default="")
    project_code: Mapped[str] = mapped_column(String(40), default="")
    department: Mapped[str] = mapped_column(String(20), default="")
    start_date: Mapped[date] = mapped_column(Date)                              # kỳ bắt đầu phân bổ
    amount: Mapped[float | None] = mapped_column(TIEN)                     # giá trị cần phân bổ, nullable=True
    months: Mapped[int] = mapped_column(Integer, default=1)                     # số kỳ phân bổ
    opening_allocated: Mapped[float | None] = mapped_column(TIEN)          # đã phân bổ trước khi lên VTOS, nullable=True
    opening_period: Mapped[str] = mapped_column(String(7), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="dang_pb")
    note: Mapped[str] = mapped_column(String(300), default="")
    source: Mapped[str] = mapped_column(String(20), default="vtos")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PrepaidAllocation(Base):
    """Một dòng bảng phân bổ chi phí trả trước của một kỳ (MISA: Phân bổ chi phí trả trước)."""
    __tablename__ = "prepaid_allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    prepaid_id: Mapped[int] = mapped_column(ForeignKey("prepaid_expenses.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    allocated: Mapped[float | None] = mapped_column(TIEN)                  # lũy kế đã phân bổ đến hết kỳ, nullable=True
    remaining: Mapped[float | None] = mapped_column(TIEN)                  # còn lại cuối kỳ, nullable=True
    entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
