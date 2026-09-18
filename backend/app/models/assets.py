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

# ══════════════════════════════════════════════════════════════════════════════════════════════
# SỔ TÀI SẢN THƯƠNG HIỆU — Chủ tịch chốt 18/9/2026: DÙNG CHUNG bảng này, không dựng bảng riêng
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# VÌ SAO DÙNG CHUNG LÀ ĐÚNG, chứ không phải mượn tạm: bảng này đã có sẵn loại `vo_hinh` (TSCĐ vô
# hình, TK 213/2143). Một bộ nhận diện MUA NGOÀI có hoá đơn đúng là TSCĐ vô hình — nó vốn thuộc về
# đây. Dựng một bảng thứ hai cho nó là để hai sổ cùng nói về một tài sản.
#
# CHỖ KHÔNG VỪA, và cách giải:
#
#  1. Nhãn hiệu do NỘI BỘ TỰ TẠO thì kế toán không được ghi nhận là tài sản (VAS 04). Logo team tự
#     vẽ, bộ màu, mẫu ấn phẩm — có thật, Marketing phải quản, nhưng không phải một thẻ TSCĐ có giá
#     trị trên sổ. Chúng vào đây với nguyên giá ĐỂ RỖNG.
#
#     Chủ tịch chốt 18/9: *"chỉ hiện dòng có hoá đơn"*. Bảng này không có cột hoá đơn, nó có nguyên
#     giá — nên luật viết ra là: dòng thương hiệu chỉ vào danh sách và báo cáo TSCĐ của Kế toán KHI
#     NGUYÊN GIÁ ĐÃ ĐƯỢC KHAI. Nguyên giá rỗng = nội bộ tự tạo = chỉ Marketing thấy. Luật ấy nằm ở
#     `services/tai_san_thuong_hieu.hien_o_so_ke_toan`, viết MỘT chỗ và mọi nơi đọc đều gọi nó.
#
#  2. Bảng này không có cột để quản nhận diện: phiên bản, hiệu lực từ–đến, bản nào thay bản nào,
#     đang dán ở đâu, ai duyệt. Tám cột dưới đây là chỗ ấy. Chúng CHỈ có nghĩa khi `th_so` bật;
#     thẻ TSCĐ thường của Kế toán không bao giờ chạm tới chúng.
#
#  3. `kind` KHÔNG dùng để đánh dấu thương hiệu, và đây là chỗ dễ làm sai nhất. `kind` quyết định
#     TK nguyên giá và TK hao mòn — đổi nó là đổi định khoản. Một logo mua ngoài vẫn phải là
#     `vo_hinh` (TK 213) cho đúng sổ; dấu "thuộc sổ thương hiệu" là một cột RIÊNG.
TH_LOAI = {
    "logo": "Logo & dấu hiệu nhận diện", "phong_chu": "Bộ phông chữ", "bo_mau": "Bộ màu",
    "an_pham": "Mẫu ấn phẩm (brochure, standee, name card)", "dong_phuc": "Đồng phục",
    "bien_hieu": "Biển hiệu & bảng quảng cáo", "video": "Video & nhạc hiệu", "khac": "Khác",
}
# `nhap` → chưa đủ hai chữ ký. `dang_dung` → bản đang có hiệu lực. `da_thay` → đã có bản mới thay.
# KHÔNG có trạng thái "đã duyệt" tách khỏi "đang dùng": duyệt xong mà chưa có ngày hiệu lực thì
# chưa ai biết từ hôm nào phải in theo bản mới, và đó đúng là chỗ hay cãi nhau nhất khi đổi logo.
TH_TRANG_THAI = {"nhap": "Nháp – chưa đủ chữ ký", "dang_dung": "Đang dùng", "da_thay": "Đã có bản thay"}


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
    # ---- Sổ tài sản thương hiệu (18/9/2026) – xem ghi chú TH_LOAI ở đầu tệp ----
    # `th_so` là DẤU DUY NHẤT phân biệt hai loại thẻ. Không suy từ `group`, không suy từ tên: suy
    # từ một chuỗi người gõ là sớm muộn có thẻ máy photocopy tên "Logo hội nghị" rơi vào sổ nhận diện.
    th_so: Mapped[bool] = mapped_column(Boolean, default=False)
    th_loai: Mapped[str] = mapped_column(String(20), default="")
    th_phien_ban: Mapped[str] = mapped_column(String(30), default="")
    th_hieu_luc_tu: Mapped[date | None] = mapped_column(Date, nullable=True)
    th_hieu_luc_den: Mapped[date | None] = mapped_column(Date, nullable=True)
    th_trang_thai: Mapped[str] = mapped_column(String(20), default="")
    th_noi_su_dung: Mapped[str] = mapped_column(String(200), default="")
    # HAI CHỮ KÝ, đúng khuôn `vehicle_rates` / `guide_rates` đã có trong kho (Chủ tịch + TGĐ ở đó).
    # Ở đây là Chủ tịch + P.TGĐ Marketing, theo chốt 18/9/2026. Hai ô riêng chứ không một ô
    # "đã duyệt": một ô thì sổ không trả lời được câu "ai đã ký, còn thiếu ai".
    th_ky_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    th_ky_ptgd_mkt: Mapped[bool] = mapped_column(Boolean, default=False)


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
