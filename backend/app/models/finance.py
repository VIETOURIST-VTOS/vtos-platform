"""Ngân quỹ – tài chính: khế ước vay, hợp đồng tài chính/đầu tư (mục 3.9), lịch thu/trả, dự báo dòng tiền 13 tuần."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.kieu_tien import TIEN

CONTRACT_KINDS = {"vay": "Khế ước vay ngân hàng", "lien_ket": "Đầu tư công ty liên kết", "hop_tac_kd": "Hợp tác kinh doanh", "ky_quy": "Ký quỹ",
                  "coc": "Đặt cọc mua tài sản", "cho_vay": "Cho vay", "phai_thu_co_phan": "Phải thu bán cổ phần", "von_phat_hanh": "Sử dụng vốn phát hành"}
KIND_ACCOUNT = {"vay": "341", "lien_ket": "222", "hop_tac_kd": "138", "ky_quy": "244", "coc": "331", "cho_vay": "128", "phai_thu_co_phan": "138", "von_phat_hanh": "411"}


class FinContract(Base):
    """Mỗi khoản một hồ sơ: loại, đối tác, giá trị, lãi suất, tài sản đảm bảo, người phụ trách, nghị quyết phê duyệt (HĐQT)."""
    __tablename__ = "fin_contracts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)             # HD2609-0001
    kind: Mapped[str] = mapped_column(String(20))
    entity: Mapped[str] = mapped_column(String(80), default="Công ty mẹ")    # pháp nhân: Công ty mẹ / Vietrip
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)   # pháp nhân vay – dùng cho hợp nhất, cột entity ở trên giữ nguyên văn hồ sơ
    # Nhóm khoản vay. Sao kê ngân hàng gộp chung vay mua xe, vay bất động sản và vay vốn lưu động;
    # màn hình theo dõi vay xe chỉ được lấy đúng nhóm của mình, nếu không thì 51 khoản vay khác sẽ
    # trôi vào đó và con số "nợ của đội xe" thành một con số không có nghĩa.
    loan_group: Mapped[str] = mapped_column(String(24), default="")   # vay_xe_45cho / vay_xe_khac / von_luu_dong / bds / khac
    partner: Mapped[str] = mapped_column(String(160))                       # ngân hàng / đối tác
    contract_no: Mapped[str] = mapped_column(String(80), default="")
    signed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    principal: Mapped[float | None] = mapped_column(TIEN)              # giá trị gốc / hạn mức, nullable=True
    outstanding: Mapped[float | None] = mapped_column(TIEN)            # dư nợ / số đã giải ngân còn lại, nullable=True
    interest_rate: Mapped[float] = mapped_column(Float, default=0)          # %/năm
    maturity: Mapped[date | None] = mapped_column(Date, nullable=True)
    collateral: Mapped[str] = mapped_column(String(300), default="")
    purpose: Mapped[str] = mapped_column(String(300), default="")
    owner: Mapped[str] = mapped_column(String(80), default="")              # người phụ trách
    approval_ref: Mapped[str] = mapped_column(String(120), default="")      # nghị quyết HĐQT
    related_party: Mapped[bool] = mapped_column(Boolean, default=False)     # bên liên quan (NĐ 132, sổ GDLK)
    status: Mapped[str] = mapped_column(String(20), default="hieu_luc")     # hieu_luc / tat_toan / qua_han
    note: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    schedule: Mapped[list["FinSchedule"]] = relationship(back_populates="contract", cascade="all, delete-orphan", order_by="FinSchedule.due_date")


class FinSchedule(Base):
    """Lịch giải ngân / thu hồi / trả gốc / trả lãi của từng hợp đồng – nguồn cho dự báo dòng tiền 13 tuần."""
    __tablename__ = "fin_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("fin_contracts.id"), index=True)
    # V12 – số KỲ trong lịch trả nợ. Để RỖNG cho dòng không thuộc lịch (giải ngân, thu hồi lẻ).
    # Có kỳ thì đối chiếu được "dư nợ trên sổ khớp lịch trả nợ" theo từng kỳ, không chỉ theo tổng.
    ky: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # V12 – mã đáo hạn: hai chân của một lần đảo nợ mang CÙNG một mã, và bút toán sinh ra mang
    # source_ref "dao_han:<mã>" để cổng đáo hạn (cong_chan.CHAN_DAO_HAN) nhìn thấy cả hai.
    # Thiếu một chân là ngoại lệ – đó chính là điều cổng ấy canh.
    ma_dao_han: Mapped[str] = mapped_column(String(40), default="", index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(20))                           # tra_goc / tra_lai / thu_hoi / giai_ngan / nhan_vay
    amount: Mapped[float] = mapped_column(TIEN)
    status: Mapped[str] = mapped_column(String(20), default="ke_hoach")     # ke_hoach / da_thuc_hien / qua_han
    done_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    bank_ref: Mapped[str] = mapped_column(String(80), default="")
    entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract: Mapped["FinContract"] = relationship(back_populates="schedule")


class CashPlanItem(Base):
    """Khoản thu/chi dự kiến khác ngoài hệ thống (thuế, lương, tiền thuê…) cho dự báo 13 tuần – Kế toán nhập."""
    __tablename__ = "cash_plan_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    direction: Mapped[str] = mapped_column(String(5))                       # in / out
    category: Mapped[str] = mapped_column(String(40))                       # luong / thue / thue_van_phong / khac
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(TIEN)
    recurring_monthly: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(50), default="")
