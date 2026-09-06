"""Danh mục Tài khoản ngân hàng (MISA: Danh mục ▸ Tài khoản ngân hàng).

MISA theo dõi tiền gửi theo TỪNG TÀI KHOẢN NGÂN HÀNG, mỗi tài khoản là một tiểu khoản của 112, nhờ đó in được
"Sổ tiền gửi ngân hàng" riêng cho từng ngân hàng và đối chiếu với sao kê. Sổ nạp sang VTOS trước đây ghi cột
đối tượng trên TK 112 là người nộp/nhận tiền chứ không phải ngân hàng, nên không tách được.

Mỗi bản ghi ở đây gắn với đúng một tiểu khoản 112 (account_code) do hệ thống tự sinh dưới 1121 (tiền Việt Nam)
hoặc 1122 (ngoại tệ). Tiểu khoản để trống ánh xạ chỉ tiêu BCTC thì báo cáo tự lấy theo tài khoản cha, nên việc
mở tiểu khoản KHÔNG làm thay đổi một đồng nào trên Báo cáo tình hình tài chính.

match_prefixes / match_keywords dùng để nhận diện ngân hàng từ sổ cũ: sổ MISA đánh số chứng từ theo tài khoản
ngân hàng (ví dụ TPB1-01358, TPC1-…), đây là căn cứ đáng tin hơn diễn giải. Dòng nào không quy tắc nào khớp thì
GIỮ NGUYÊN trên tài khoản cha, tuyệt đối không đoán bừa.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

CURRENCIES = {"VND": {"ten": "Đồng Việt Nam", "tk_cha": "1121"}, "USD": {"ten": "Đô la Mỹ", "tk_cha": "1122"},
              "EUR": {"ten": "Euro", "tk_cha": "1122"}, "JPY": {"ten": "Yên Nhật", "tk_cha": "1122"}}


class BankAccount(Base):
    __tablename__ = "bank_accounts_cat"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)      # mã ngắn Kế toán tự đặt: TPB1, VCB1…
    bank_name: Mapped[str] = mapped_column(String(120))                          # TPBank, Vietcombank…
    account_number: Mapped[str] = mapped_column(String(40), default="")
    account_name: Mapped[str] = mapped_column(String(200), default="")           # tên chủ tài khoản trên sao kê
    branch: Mapped[str] = mapped_column(String(120), default="")
    currency: Mapped[str] = mapped_column(String(5), default="VND")
    account_code: Mapped[str] = mapped_column(String(10), default="", index=True)  # tiểu khoản 112 hệ thống sinh ra
    parent_account: Mapped[str] = mapped_column(String(10), default="1121")
    match_prefixes: Mapped[list] = mapped_column(JSON, default=list)             # tiền tố số chứng từ: ["TPB1","TPC1"]
    match_keywords: Mapped[list] = mapped_column(JSON, default=list)             # từ khóa trong diễn giải: ["TPBANK"]
    sepay_account_number: Mapped[str] = mapped_column(String(40), default="")    # để đối chiếu giao dịch SePay
    opening_balance: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
