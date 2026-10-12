# -*- coding: utf-8 -*-
"""ĐỀ NGHỊ XE — mắt đầu của chuỗi điều xe Chủ tịch đặc tả ngày 11/10/2026.

    Điều hành ĐỀ NGHỊ xe  →  Giám đốc đội xe LẬP LỆNH  →  Tài xế NHẬN

Trước bản này chuỗi chỉ có mắt giữa: `POST /dispatch` cho cả Điều hành lẫn Giám đốc đội xe tự chọn
xe và phát lệnh. Nên hai việc khác nhau đi cùng một cửa — người CẦN xe và người CÓ xe là hai vai, và
gộp lại thì không ai trả lời được câu "ai quyết chiếc xe này đi chuyến này".

HAI ĐIỀU BẢNG NÀY CỐ Ý KHÔNG CÓ:

  1. KHÔNG có cột xe. Đề nghị nói "chuyến này cần xe", không nói "cần chiếc 50F-034.71". Chọn xe là
     việc của Giám đốc đội xe, vì chỉ người ấy biết xe nào đang ở đâu, xe nào sắp tới kỳ bảo dưỡng,
     tài xế nào vừa chạy về. Để Điều hành chỉ xe thì cửa lập lệnh thành cửa gõ lại.

  2. KHÔNG có bước duyệt đề nghị. Chủ tịch quyết 11/10/2026: DỰ TOÁN TOUR ĐÃ DUYỆT LÀ ĐỦ — chi phí
     xe đã nằm trong dự toán ấy, nên thêm một chữ ký nữa là bắt mỗi chuyến chờ thêm một người.
     Giám đốc đội xe lập lệnh là mắt kiểm duy nhất, và lý do từ chối là bắt buộc.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Trạng thái của một đề nghị. Bốn trạng thái, không hơn: mỗi trạng thái phải trả lời được câu "bây
# giờ ai đang giữ việc này".
TRANG_THAI = {
    "cho_lap_lenh": "Chờ Giám đốc đội xe lập lệnh",
    "da_lap_lenh":  "Đã có lệnh điều xe",
    "tu_choi":      "Đội xe từ chối – có lý do",
    "huy":          "Điều hành đã huỷ",
}

# Trạng thái chuyến mà dự toán ĐÃ được duyệt, tính cả các bước về sau.
#
# Không chỉ so với "da_duyet": một chuyến đã kết thúc hoặc đã đóng số thì dự toán của nó cũng đã
# duyệt rồi, và chặn đề nghị xe cho chuyến ấy là chặn sai — vẫn có ca phải lập lệnh bù cho một
# chuyến đang chạy dở hoặc vừa đổi xe giữa hành trình.
DU_TOAN_DA_DUYET = ("da_duyet", "ket_thuc", "da_dong_so", "kt_xac_nhan", "khoa")


class DeNghiXe(Base):
    """Một đề nghị xe cho một chuyến."""
    __tablename__ = "fleet_vehicle_requests"
    __table_args__ = (
        # Một chuyến có thể cần nhiều xe, và có thể đề nghị nhiều lần (đổi ngày, thêm xe). Nên KHÔNG
        # khoá duy nhất theo tour: khoá như vậy là chặn đúng ca tour 50 khách cần hai xe. Chỗ chống
        # trùng nằm ở phép kiểm trong dịch vụ, nó nói ra đề nghị đang chờ chứ không chặn cứng.
        Index("ix_de_nghi_xe_tour_trang_thai", "tour_id", "trang_thai"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    ngay_di: Mapped[date] = mapped_column(Date)
    ngay_ve: Mapped[date] = mapped_column(Date)
    # Số khách và km dự kiến là ĐẦU VÀO của bộ gợi ý điều xe (`fleet_ai.goi_y_dieu_xe`). Để rỗng thì
    # bộ gợi ý không lọc được theo số ghế, nên cửa đòi số khách.
    so_khach: Mapped[int] = mapped_column(Integer, default=0)
    km_du_kien: Mapped[int] = mapped_column(Integer, default=0)
    # Số xe Điều hành cho là cần. KHÔNG phải số xe sẽ điều: Giám đốc đội xe quyết điều mấy chiếc.
    so_xe_can: Mapped[int] = mapped_column(Integer, default=1)
    yeu_cau: Mapped[str] = mapped_column(Text, default="")       # xe giường nằm, xe mới, tài xế biết tuyến…
    trang_thai: Mapped[str] = mapped_column(String(20), default="cho_lap_lenh", index=True)
    ly_do: Mapped[str] = mapped_column(String(300), default="")  # lý do TỪ CHỐI hoặc HUỶ – bắt buộc khi có
    nguoi_de_nghi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    xu_ly_boi: Mapped[str] = mapped_column(String(50), default="")
    xu_ly_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
