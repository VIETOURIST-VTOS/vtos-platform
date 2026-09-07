"""Nền dữ liệu đội xe Vietrip – Đợt 1 theo đặc tả "Quản lý vận hành xe Vietrip" v1.3 (06/9/2026).

Điều quan trọng nhất của đợt này không phải thêm màn hình, mà là sửa một giả định sai trong dữ liệu cũ:
BIỂN SỐ KHÔNG PHẢI DANH TÍNH CỦA XE. Bảng `vehicles` cũ lấy biển số làm khóa duy nhất, nên khi một xe đổi
biển hoặc chuyển từ sở hữu sang hợp tác, người dùng buộc phải tạo bản ghi mới – và lịch sử chuyến, chi phí,
khế ước của chiếc xe đó bị chẻ làm đôi mà không ai hay.

Cách xử lý ở đây:
  - `vehicles.id` (đã có sẵn) vẫn là danh tính suốt vòng đời; thêm `code` là mã xe cố định để người dùng gọi.
  - `vehicles.plate` giữ nguyên nghĩa "biển ĐANG dùng" và vẫn duy nhất – hai xe đang chạy không thể cùng một
    biển. Còn toàn bộ lịch sử biển nằm ở `vehicle_plates`, có ngày hiệu lực, và KHÔNG duy nhất vì một biển
    hoàn toàn có thể được cấp lại cho xe khác sau nhiều năm.
  - Sở hữu, khai thác và hợp đồng là ba việc khác nhau: xe đã bán vẫn có thể được khai thác theo hợp đồng hợp
    tác, và xe thuộc sở hữu công ty chưa chắc đã đủ điều kiện chạy. Vì vậy vòng đời tài sản (`lifecycle`) tách
    khỏi quyền khai thác (`op_right`), không gộp vào một cột "active" như trước.

Giấy tờ và hàng đợi xác minh nằm ở đây thay vì rải trong bảng xe, vì một giấy tờ có hạn là một BẢN GHI có
ngày, có nguồn và có mức độ đã xác minh – không phải một ô ngày trên hồ sơ xe.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Vòng đời tài sản – trả lời "chiếc xe này còn là tài sản/trách nhiệm của ai"
LIFECYCLE = {"dang_khai_thac": "Đang khai thác", "cho_kiem_tra": "Chờ kiểm tra", "da_ban": "Đã bán",
             "ngung": "Ngừng khai thác"}
# Quyền khai thác – trả lời "công ty có được điều chiếc xe này đi không"
OP_RIGHT = {"so_huu": "Xe sở hữu", "hop_tac": "Hợp tác theo hợp đồng", "thue": "Thuê ngoài",
            "khong": "Không có quyền khai thác"}
# Giấy tờ có hạn. Tách theo chủ thể: giấy của XE và giấy của NGƯỜI lái.
VEHICLE_DOCS = {"dang_kiem": "Đăng kiểm", "phu_hieu": "Phù hiệu", "bao_hiem": "Bảo hiểm",
                "dang_ky": "Giấy đăng ký xe"}
DRIVER_DOCS = {"gplx": "Giấy phép lái xe"}
DOC_KINDS = {**VEHICLE_DOCS, **DRIVER_DOCS}
# Mức độ tin cậy của một dữ kiện. "Nguồn ghi" khác "đã đối chiếu giấy gốc" – đặc tả nhấn mạnh điểm này.
VERIFY = {"nguon_ghi": "Theo nguồn, chưa đối chiếu", "da_xac_minh": "Đã đối chiếu giấy gốc",
          "sai_lech": "Có sai lệch cần xử lý"}
VERIFY_STATUS = {"cho_xac_minh": "Chờ xác minh", "dang_xu_ly": "Đang xử lý", "xong": "Đã xử lý",
                 "khong_ap_dung": "Không áp dụng"}


class VehiclePlate(Base):
    """Lịch sử biển số của một xe. `to_date` rỗng nghĩa là biển đang dùng.

    Không đặt ràng buộc duy nhất trên `plate`: cùng một biển có thể xuất hiện ở hai xe tại hai thời kỳ khác
    nhau, và ép duy nhất sẽ chặn đúng lúc người dùng cần ghi lại sự thật đó."""
    __tablename__ = "vehicle_plates"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    plate: Mapped[str] = mapped_column(String(20))
    from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(120), default="")        # nguồn dữ liệu: file, công văn, giấy đăng ký
    verify: Mapped[str] = mapped_column(String(20), default="nguon_ghi")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class VehicleDocument(Base):
    """Giấy tờ có hạn của xe hoặc của tài xế.

    `expires_on` để rỗng KHÔNG có nghĩa là còn hạn – nó có nghĩa là chưa biết, và hệ thống phải nói "chưa đủ
    dữ liệu" chứ không được hiện màu xanh (đặc tả §7)."""
    __tablename__ = "vehicle_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))
    number: Mapped[str] = mapped_column(String(60), default="")
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(120), default="")
    verify: Mapped[str] = mapped_column(String(20), default="nguon_ghi")
    note: Mapped[str] = mapped_column(String(300), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class FleetVerification(Base):
    """Hàng đợi làm sạch dữ liệu (đặc tả §1).

    Mỗi dòng là một điều hệ thống KHÔNG tự quyết được và cần người trả lời: pháp nhân của xe, biển số ghi lệch
    giữa hai nguồn, giấy tờ hết hạn theo dữ liệu nhưng chưa rõ ngoài thực tế. Để trong bảng riêng chứ không
    thành cờ trên hồ sơ xe, vì một việc xác minh có người phụ trách, có ngày và có kết luận."""
    __tablename__ = "fleet_verifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(30), default="vehicle")   # vehicle / driver / contract / loan
    ref: Mapped[str] = mapped_column(String(60), default="")             # mã xe, biển số, mã khế ước…
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    issue: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_minh")
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(50), default="")


# ====================== ĐỢT 2: NHẬT TRÌNH, BẢO DƯỠNG, DỮ LIỆU NGUỒN NGOÀI ======================
# Quy tắc chốt ngày 07/9/2026: Vietourist TẠM ỨNG nhiên liệu, cầu đường, công tác phí, bãi xe;
# KHÔNG tạm ứng sửa chữa – chủ xe hợp tác tự chịu. Vì vậy "ai chịu khoản này" là một CỘT trên từng dòng chi
# phí, không phải suy ra từ loại chi phí lúc quyết toán: cùng một loại chi phí có thể do hai bên chịu tùy
# hợp đồng, và suy ra lúc quyết toán là lúc không còn ai nhớ để cãi.
BEN_CHIU = {"vietourist_tam_ung": "Vietourist tạm ứng", "chu_xe": "Chủ xe tự chịu"}
COST_KINDS = {"dau": "Nhiên liệu", "cong_tac_phi": "Công tác phí tài xế", "giu_xe": "Phí giữ/bãi xe",
              "cau_duong": "Phí cầu đường", "sua_chua": "Sửa chữa, bảo dưỡng", "khac": "Khác"}
# Loại chi phí nào mặc định bên nào chịu. Sửa chữa mặc định CHỦ XE theo quy tắc đã chốt.
BEN_CHIU_MAC_DINH = {"sua_chua": "chu_xe"}
TRIP_STATUS = {"nhap": "Nháp – tài xế đang ghi", "cho_xac_nhan": "Chờ xác nhận",
               "da_xac_nhan": "Đã xác nhận", "huy": "Hủy"}
# Ba cờ dùng thống nhất toàn hệ thống (đặc tả §1): xanh cho duyệt một chạm, vàng phải nhập lý do,
# đỏ chặn duyệt. Ánh xạ sang bốn mức của bộ kiểm tra Đợt 1 ở app/services/fleet.py.
CO = {"xanh": "Xanh – đủ chứng từ, số khớp", "vang": "Vàng – lệch trong ngưỡng hoặc thiếu chứng từ phụ",
      "do": "Đỏ – vi phạm quy tắc cứng, thiếu chứng từ chính, hoặc lệch vượt ngưỡng"}
MAINT_KINDS = {"dinh_ky": "Bảo dưỡng định kỳ", "sua_chua": "Sửa chữa", "vo_xe": "Vỏ xe", "khac": "Khác"}


class Trip(Base):
    """Một chuyến xe – nhật trình. Km đầu/cuối là số ĐO, nên phải đi kèm nguồn và thời điểm.

    `km_dau`/`km_cuoi` để rỗng nghĩa là chưa đo, không phải bằng 0. Dùng 0 làm "chưa có" là cách chắc chắn
    nhất để một ngày nào đó hệ thống báo xe chạy âm mấy trăm nghìn km."""
    __tablename__ = "fleet_trips"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    dispatch_id: Mapped[int | None] = mapped_column(ForeignKey("dispatch_orders.id"), nullable=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    ten_tour: Mapped[str] = mapped_column(String(160), default="")
    ngay_di: Mapped[date] = mapped_column(Date)
    ngay_ve: Mapped[date] = mapped_column(Date)
    km_dau: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_cuoi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_gps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_nguon: Mapped[str] = mapped_column(String(40), default="")      # anh_dong_ho / nhap_tay / gps
    doanh_thu: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")
    co: Mapped[str] = mapped_column(String(10), default="vang")        # cờ tổng hợp của chuyến
    co_ly_do: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_by: Mapped[str] = mapped_column(String(50), default="")


class TripCost(Base):
    """Một dòng chi phí của chuyến. Mỗi dòng phải trả lời được ba câu: loại gì, ai chịu, chứng từ đâu."""
    __tablename__ = "fleet_trip_costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("fleet_trips.id"))
    kind: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Float, default=0)
    ben_chiu: Mapped[str] = mapped_column(String(24), default="vietourist_tam_ung")
    lit: Mapped[float] = mapped_column(Float, default=0)               # chỉ dùng cho nhiên liệu
    chung_tu: Mapped[str] = mapped_column(String(200), default="")     # mã/đường dẫn chứng từ gốc
    nguon: Mapped[str] = mapped_column(String(40), default="nhap_tay")  # nhap_tay / the_dau / epass / ocr
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # id giao dịch nguồn nếu khớp tự động
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class Maintenance(Base):
    """Bảo dưỡng, sửa chữa. `km_luc_lam` là bắt buộc về mặt nghiệp vụ – không có nó thì không phát hiện được
    chi phí ghi sai kỳ, mà đó chính là lỗi đã xảy ra với xe 50H-496.23 tháng 8/2026."""
    __tablename__ = "fleet_maintenance"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    ngay: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(20), default="dinh_ky")
    km_luc_lam: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_ky_toi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    noi_dung: Mapped[str] = mapped_column(String(300), default="")
    garage: Mapped[str] = mapped_column(String(120), default="")
    so_tien: Mapped[float] = mapped_column(Float, default=0)
    ben_chiu: Mapped[str] = mapped_column(String(24), default="chu_xe")
    chung_tu: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class ExternalTxn(Base):
    """Giao dịch từ nguồn ngoài: thẻ dầu (sao kê ngân hàng) và trạm thu phí (ePass/VETC).

    Hai điều bắt buộc, đặc tả nêu đích danh vì cả hai đã gây sai số thật:

      1. `ma_gd` DUY NHẤT theo từng nguồn – tải lại cùng một file sao kê hai lần không được sinh bản ghi thứ
         hai. Báo cáo ePass tháng 8/2026 có 2 bản ghi lặp hoàn toàn (218.920đ và 163.800đ); không lọc là
         tính dư đúng bằng số đó.
      2. Bản ghi trùng vẫn được GIỮ trong bảng thô để đối chiếu, chỉ loại ở tầng tính – nên có cột `trung`
         thay vì xóa đi. Xóa mất là mất luôn khả năng chứng minh mình đã loại đúng cái gì.

    Biển số ánh xạ sang xe qua LỊCH SỬ BIỂN SỐ theo thời điểm giao dịch, không theo biển hiện tại. Xe đổi
    biển giữa kỳ mà tra theo biển hiện tại thì nửa đầu kỳ rơi mất khỏi xe – đúng ca 50F-046.92 đổi thành
    50E-955.31 ngày 13/08/2026."""
    __tablename__ = "fleet_external_txns"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20))                    # the_dau / epass
    ma_gd: Mapped[str] = mapped_column(String(120))                    # mã giao dịch gốc của nhà cung cấp
    tai_khoan: Mapped[str] = mapped_column(String(40), default="")     # số tài khoản/ví (chỉ lưu phần cần)
    the_4so: Mapped[str] = mapped_column(String(8), default="")
    bien_so: Mapped[str] = mapped_column(String(20), default="")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_trips.id"), nullable=True)
    thoi_diem: Mapped[datetime] = mapped_column(DateTime)
    so_tien: Mapped[float] = mapped_column(Float, default=0)
    lit: Mapped[float] = mapped_column(Float, default=0)
    mo_ta: Mapped[str] = mapped_column(String(300), default="")
    trung: Mapped[bool] = mapped_column(Boolean, default=False)        # bản ghi lặp: giữ lại, không tính
    trung_cua_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    khop: Mapped[str] = mapped_column(String(20), default="chua_khop")  # chua_khop / da_khop / khong_khop
    co: Mapped[str] = mapped_column(String(10), default="vang")
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    imported_by: Mapped[str] = mapped_column(String(50), default="")
