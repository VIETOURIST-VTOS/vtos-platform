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
