"""Đồng bộ Vietrip → VTOS: bảng trung gian (staging) giữ nguyên dữ liệu gốc + bảng dòng chi phí quyết toán tour (bổ sung theo cấu trúc Vietrip)."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Numeric, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


class VtRecord(Base):
    """Bản ghi Vietrip thô: entity (tour/booking/receipt/supplier_payment/user/vehicle/proposal/settlement), vietrip_id, raw JSON. Idempotent."""
    __tablename__ = "vt_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(30), index=True)
    vietrip_id: Mapped[str] = mapped_column(String(40), index=True)
    ref: Mapped[str] = mapped_column(String(60), default="", index=True)   # tourcode / bookingID để tra chéo
    on_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)          # đã ánh xạ sang bảng nghiệp vụ VTOS
    apply_note: Mapped[str] = mapped_column(String(200), default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class TourCostLine(Base):
    """Dòng chi phí dự toán / quyết toán của tour (theo mẫu bảng quyết toán Vietrip): mô tả, loại DV, NCC (MST), đơn giá, SL, hệ số, thực chi, đã thanh toán."""
    __tablename__ = "tour_cost_lines"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(200))
    cost_kind: Mapped[str] = mapped_column(String(20), default="co_dinh")   # co_dinh / theo_khach
    service_type: Mapped[str] = mapped_column(String(30), default="")        # GUIDE / HOTEL / LAND / BUS / MEAL / TICKET / VISA / INS…
    supplier_name: Mapped[str] = mapped_column(String(200), default="")
    supplier_tax_code: Mapped[str] = mapped_column(String(20), default="")
    # Hoá đơn đầu vào của nhà cung cấp. Trước 09/9/2026 VTOS chỉ có một ô đúng/sai "có hoá đơn" trên đề
    # nghị chi và một ô ghi chú tự do – tức là biết CÓ hoá đơn nhưng không tra được hoá đơn NÀO. Không
    # tra được thì không đối chiếu được với tờ khai thuế, và cũng không trả lời được câu hỏi đơn giản
    # nhất khi quyết toán: khoản chi này có chứng từ hợp lệ không.
    #
    # Ba ô này là CỬA NHẬP cho người làm, không phải chỗ máy tự suy ra. Để rỗng nghĩa là chưa nhập –
    # theo đúng quy ước K2, không mặc định thành 0 hay chuỗi rỗng giả.
    so_hoa_don: Mapped[str | None] = mapped_column(String(30), nullable=True)      # số hoá đơn GTGT đầu vào
    ngay_hoa_don: Mapped[date | None] = mapped_column(Date, nullable=True)
    vat_hoa_don: Mapped[float | None] = mapped_column(TIEN, nullable=True)         # tiền thuế GTGT được khấu trừ
    # Nối tới hồ sơ nhà cung cấp để lấy địa chỉ/mã số thuế chuẩn. Để rỗng vẫn ghi được dòng chi phí –
    # nhiều dòng nhập từ Vietrip chỉ có tên NCC dạng chữ, ép phải chọn danh mục là chặn cả luồng nhập.
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)
    unit_price: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    qty: Mapped[float] = mapped_column(Float, default=0)
    coef: Mapped[float] = mapped_column(Float, default=1)
    actual: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    paid: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(20), default="vietrip")
    budget: Mapped[float | None] = mapped_column(TIEN)                 # dự toán của dòng (để so lệch, nullable=True)
    # ---- Lớp 3 (11/9/2026): những cột mẫu quyết toán của Điều hành có mà VTOS chưa có ----
    #
    # Chủ tịch chốt: dự toán cũng lập theo DÒNG, cùng hình với chiết tính. Cột budget ở trên đã có
    # sẵn, nên dự toán và thực chi nằm CÙNG MỘT DÒNG – so được từng khoản, không phải so hai bảng.
    # Đó là cách duy nhất trả lời được câu "dự toán 40 suất Tháp Bà, thực chi 44 suất".
    #
    # Mã khoản mục chi phí – danh mục ở app/services/khoan_muc_chi.py. Trước cột này, "description"
    # là ô CHỮ TỰ DO và trên tám tệp thật cùng một khoản có nhiều tên (LAND / LAND MCB / Landtour ADL
    # / Giá land), nên không cộng được theo khoản mục. description VẪN GIỮ để ghi chi tiết riêng của
    # dòng ("Ăn trưa ngày 2 – Marina Beach"); mã khoản mục là cái để cộng.
    ma_khoan_muc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Giữ ngày ở dạng CHỮ đúng như tệp gốc ("10/07", "Ngày 1", "10-12/07"). Ép về kiểu ngày là ép
    # người nhập phải chuẩn hoá ngay tại chỗ, và họ sẽ bỏ trống cho nhanh.
    ngay: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # Nhóm khoản mục của sheet CTT: "A. LAND TOUR", "B. TRẺ EM", "C. CHI PHÍ KHÁC". Chính chỗ cộng
    # nhóm B là nơi tệp Nha Trang bỏ sót 210.000 đ mà mọi tầng phía sau vẫn cân.
    nhom: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # nguoi_lon / tre_em / em_be / chung. KHÁC HẲN cost_kind ở trên: cost_kind nói chi phí này có
    # chia theo đầu khách hay không, doi_tuong nói chia cho AI. Tệp Nha Trang tính ăn trưa người lớn
    # 33 suất và ăn trưa trẻ em 7 suất với đơn giá khác nhau – một cột không nói được.
    doi_tuong: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Quy tắc phân bổ phải KHAI ra, không giấu trong công thức Excel. Xem BANG_PHAN_BO trong
    # app/services/gia_khach.py. Rỗng nghĩa là chưa ai chọn quy tắc – máy không đoán hộ.
    quy_tac_phan_bo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # ---- Ngoại tệ (tour nước ngoài) ----
    # Cột actual/budget luôn là VND. Bốn cột này giữ số tiền GỐC và phép quy đổi, để tra ngược được.
    #
    # Tỷ giá lấy tại NGÀY CHI THẬT – Chủ tịch chốt 11/9/2026. Ghi lại ngày ấy vì tệp UK có HAI tỷ giá
    # GBP khác nhau trong cùng một tệp (36.000 ở sheet chiết tính, 35.944 ở sheet quyết toán); riêng
    # trên giá land 692,34 GBP × 43 khách, 56 đồng chênh ấy là 1.667.155 đ. Không ghi ngày thì không
    # bao giờ phân xử được số nào đúng.
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    # ---- Thuế GTGT đầu vào ----
    # Cột vat_hoa_don (tiền thuế) đã có ở trên nhưng THIẾU thuế suất. Mẫu đoàn Đà Lạt có cả ba mức
    # trên cùng một chuyến: 8% cho nhà hàng và lưu trú, 0% cho banner và ăn nội bộ. Không lưu thuế
    # suất thì không dựng lại được bảng kê thuế GTGT đầu vào từ dữ liệu.
    thue_suat: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Phần tiền của khoản này KHÔNG có hoá đơn. Khác NULL ở so_hoa_don: NULL là chưa ai nhập, cột này
    # là đã xác nhận KHÔNG CÓ. Mẫu Đà Lạt có hẳn một cột như vậy, và đó chính là con số cần thấy –
    # phần giá vốn không khấu trừ được thuế.
    khong_hoa_don: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # ---- Thanh toán (bản nâng cấp y2d8e3f0a5b97, 11/9/2026) ----
    #
    # Cột `paid` ở trên nói ĐÃ TRẢ BAO NHIÊU. Năm cột này nói trả BẰNG ĐƯỜNG NÀO, TỪ ĐÂU, NGÀY NÀO.
    # Tệp UK ghi đủ cả năm ("Bank transfer", "Wise 9078", Paid Date, Deadline, Invoice/Receipt) và
    # Kế toán đang phải mở tệp Excel gốc để đối chiếu với sao kê thẻ – công việc thủ công duy nhất
    # còn sót trong chuỗi. Hạn thanh toán cũng là ràng buộc thật: phòng đặt qua Agoda/Booking quá
    # hạn là mất phòng.
    #
    # Rỗng nghĩa là CHƯA NHẬP (quy ước K2) – không mặc định thành hôm nay, không thành chuỗi rỗng.
    hinh_thuc_tt: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tai_khoan_the: Mapped[str | None] = mapped_column(String(60), nullable=True)
    ngay_thanh_toan: Mapped[date | None] = mapped_column(Date, nullable=True)
    han_thanh_toan: Mapped[date | None] = mapped_column(Date, nullable=True)
    loai_chung_tu: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="hd")           # hd (hiệu lực) / huy
    version: Mapped[int] = mapped_column(Integer, default=1)                # phiên bản quyết toán khi tạo/sửa dòng
    doc_name: Mapped[str] = mapped_column(String(160), default="")          # tên tệp chứng từ
    doc_data: Mapped[str] = mapped_column(Text, default="")                 # data URL (ảnh/PDF ≤ 1,5 MB)
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
