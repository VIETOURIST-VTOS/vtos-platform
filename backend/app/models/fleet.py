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
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, ForeignKey, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

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
    # Hạng ghi trên giấy phép lái xe ("E", "D", "A1, E, FC"). Chỉ dùng cho kind="gplx".
    # Phải lưu kèm `issued_on`: chữ D đảo nghĩa giữa luật cũ và luật mới, và ngày cấp là thứ DUY NHẤT
    # phân biệt được hai hệ – xem app/services/hang_gplx.py.
    hang: Mapped[str] = mapped_column(String(30), default="")
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(120), default="")
    # SM-1 (12/10/2026) — chỉ dùng cho kind="sim": cổng GPS mà chiếc sim này nuôi, khóa của
    # CONG_GPS ở đầu tệp.
    #
    # VÌ SAO MỘT CỘT CHỨ KHÔNG PHẢI MỘT CÂU TRONG Ô GHI CHÚ (Chủ tịch chọn 12/10): sim chết thì
    # cổng ấy TẮT, và câu hỏi ngay sau đó luôn là "cổng nào, mất mấy xe". Chữ tự do trong ô ghi chú
    # thì ba người gõ ba kiểu và không lọc được — đúng chỗ `km_nguon` đã hỏng một lần và phải sửa.
    cong_gps: Mapped[str] = mapped_column(String(20), default="")
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
# Quy tắc chốt ngày 07/9/2026: Vietourist TẠM ỨNG nhiên liệu, cầu đường, công tác phí, bãi xe.
# Sửa chữa: bản chốt buổi sáng 07/9 là chủ xe tự chịu; CHỦ TỊCH CHỐT LẠI CUỐI NGÀY 07/9/2026 – giữ cách đang
# làm, tức Vietourist CHI HỘ sửa chữa rồi cấn trừ vào công nợ chủ xe (khoản 22.291.048đ của 50H-496.23 đã
# được chủ xe đồng ý và xử lý xong). Mặc định này để ở tham số `xe_sua_chua_ben_chiu` chứ không cứng trong
# mã, vì đây là điều khoản hợp đồng – lần sau đổi thì đổi tham số, không phải sửa mã rồi triển khai lại.
# Vì vậy "ai chịu khoản này" là một CỘT trên từng dòng chi
# phí, không phải suy ra từ loại chi phí lúc quyết toán: cùng một loại chi phí có thể do hai bên chịu tùy
# hợp đồng, và suy ra lúc quyết toán là lúc không còn ai nhớ để cãi.
BEN_CHIU = {"vietourist_tam_ung": "Vietourist tạm ứng", "chu_xe": "Chủ xe tự chịu"}

# QT-1 (13/10/2026) — AI BỎ TIỀN RA TẠI CHỖ. Trục KHÁC HẲN `ben_chiu` ở trên.
#
# `ben_chiu` trả lời "Vietourist hay CHỦ XE hợp tác gánh khoản này" — dùng để cấn trừ công nợ chủ
# xe ngoài. Tờ quyết toán chuyến của tài xế hỏi một câu khác: tiền ấy LÚC ẤY ai móc túi ra. Hai câu
# trùng nhau ở phần lớn trường hợp nên rất dễ gộp, và gộp là hỏng: một khoản Vietourist chịu
# (`ben_chiu`) vẫn có thể do TÀI XẾ ứng tiền mặt rồi công ty hoàn lại.
#
# Đo trên hai bộ hồ sơ thật 13/10/2026: dầu trả bằng thẻ NAPAS mang tên "HOLDINGS/VIETOURIST",
# ePass trừ thẳng tài khoản công ty, còn vé gửi xe là giấy thu tiền mặt tài xế tự trả. Đó đúng là
# hai tổng "TỔNG TÀI XẾ CHI" và "TỔNG CÔNG TY CHI" trên Mẫu 2.
#
# KHÔNG suy trục này từ `kind`. Lý lẽ ở ngay chú thích `ben_chiu` phía trên và áp y nguyên: cùng
# một loại chi phí có thể do hai bên trả tùy chuyến, và suy ra lúc quyết toán là lúc không còn ai
# nhớ để cãi. Rỗng nghĩa là CHƯA AI KHAI — không mặc định về bên nào.
TRA_BANG = {"tai_xe_tien_mat": "Tài xế ứng tiền mặt",
            "the_cong_ty": "Thẻ của công ty",
            "tai_khoan_cong_ty": "Trừ tài khoản công ty (ePass, chuyển khoản)"}
# Hai tổng của Mẫu 2 suy từ bảng này, không phải từ hai ô người gõ. Ô cộng ra mà cho gõ là ô có thể
# gõ sai: tờ quyết toán 50F-034.71 ngày 07–11/10/2026 ghi "TỔNG TÀI XẾ CHI 1.360.000" trong khi
# công thức in ngay cạnh nó cho 360.000 — người viết cộng nhầm cả công tác phí, mà công tác phí đã
# nằm ở tổng bên dưới. Tổng cuối vẫn đúng, chỉ ô giữa sai, nên không ai thấy.
TRA_BANG_TAI_XE = ("tai_xe_tien_mat",)

# Tuyến ký của tờ quyết toán chuyến — Mẫu 2, Chủ tịch chọn 13/10/2026. Tài xế ký trên giấy rồi Đội
# xe nhập hộ, nên bước đầu của tuyến điện tử là ĐIỀU HÀNH.
QT_BUOC = ("dieu_hanh", "ke_toan", "tgd")
QT_TRANG_THAI = {"nhap": "Đội xe đang nhập", "cho_dieu_hanh": "Chờ Điều hành ký",
                 "cho_ke_toan": "Chờ Kế toán ký", "cho_tgd": "Chờ Tổng giám đốc ký",
                 "da_duyet": "Đã duyệt đủ chữ ký", "tra_lai": "Trả lại để sửa"}
COST_KINDS = {"dau": "Nhiên liệu", "cong_tac_phi": "Công tác phí tài xế", "giu_xe": "Phí giữ/bãi xe",
              "cau_duong": "Phí cầu đường", "sua_chua": "Sửa chữa, bảo dưỡng", "khac": "Khác"}
# Mặc định dự phòng khi chưa có tham số trong cơ sở dữ liệu. Nguồn thật là `xe_sua_chua_ben_chiu`.
BEN_CHIU_MAC_DINH = {"sua_chua": "vietourist_tam_ung"}
TRIP_STATUS = {"nhap": "Nháp – tài xế đang ghi", "cho_xac_nhan": "Chờ xác nhận",
               "da_xac_nhan": "Đã xác nhận", "huy": "Hủy"}
# Ba cờ dùng thống nhất toàn hệ thống (đặc tả §1): xanh cho duyệt một chạm, vàng phải nhập lý do,
# đỏ chặn duyệt. Ánh xạ sang bốn mức của bộ kiểm tra Đợt 1 ở app/services/fleet.py.
CO = {"xanh": "Xanh – đủ chứng từ, số khớp", "vang": "Vàng – lệch trong ngưỡng hoặc thiếu chứng từ phụ",
      "do": "Đỏ – vi phạm quy tắc cứng, thiếu chứng từ chính, hoặc lệch vượt ngưỡng"}
MAINT_KINDS = {"dinh_ky": "Bảo dưỡng định kỳ", "sua_chua": "Sửa chữa", "vo_xe": "Vỏ xe", "khac": "Khác"}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# NGUỒN CỦA SỐ KM — khai thành bảng, không để chuỗi tự do (07/10/2026)
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# `Trip.km_nguon` xưa nay là `String(40)` tự do với chú thích "anh_dong_ho / nhap_tay / gps". Chuỗi
# tự do thì ba người gõ ba cách — "GPS", "gps", "Vietmap" — và lúc đi hỏi "số này ở đâu ra" thì
# không nhóm lại được.
#
# Chủ tịch cho biết 07/10/2026: đội xe Vietourist đang theo dõi hành trình trên BA cổng khác nhau
# (TTC · TCD · Vietmap), mỗi cổng một tài khoản riêng. Nên "gps" không còn là một câu trả lời đủ:
# khi km đồng hồ lệch km GPS, câu hỏi tiếp theo luôn là LỆCH VỚI CỔNG NÀO — ba cổng có thể cho ba
# con số khác nhau cho cùng một chiếc xe, và chọn tin cổng nào là một quyết định của người, không
# phải của phần mềm.
#
# Giữ "gps" trong bảng làm giá trị CŨ, không bỏ: những dòng đã ghi trước hôm nay mang đúng chữ ấy,
# và xoá nó đi là làm chúng thành giá trị lạ.
KM_NGUON = {
    "anh_dong_ho": "Ảnh đồng hồ công-tơ-mét",
    "nhap_tay": "Người nhập tay",
    "gps": "GPS (chưa rõ cổng nào — cách ghi cũ)",
    "gps_ttc": "GPS – cổng TTC",
    "gps_tcd": "GPS – cổng TCD",
    "gps_vietmap": "GPS – cổng Vietmap",
}

# CỔNG GPS mà một chiếc sim nuôi. SUY TỪ `KM_NGUON` chứ không gõ lại ba chữ ấy lần thứ hai: ngày nào
# đội xe thêm cổng thứ tư, thêm một dòng ở trên là cả hai nơi cùng biết. Gõ lại là dựng chỗ để hai
# bảng lệch nhau — đúng cái bẫy `km_nguon` đã mắc một lần (chuỗi tự do, ba người gõ ba kiểu).
#
# Bỏ "gps" cũ: nó là cách ghi CŨ cho số km đã lỡ ghi, không phải một cổng có thật để gắn sim vào.
CONG_GPS = {k: v for k, v in KM_NGUON.items() if k.startswith("gps_")}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# TÀI KHOẢN ePass — HAI PHÁP NHÂN, HAI VÍ (Chủ tịch cho biết 07/10/2026)
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Đội xe đi đường bằng HAI tài khoản ePass thuộc hai pháp nhân khác nhau. Trước bản này bộ nạp
# "Phí cầu đường" không có ô tài khoản và `_gd_nap` không ghi cột `tai_khoan`, nên giao dịch của cả
# hai ví rơi chung một rổ `source="epass"` — chi phí cầu đường của hai pháp nhân TRỘN VÀO NHAU,
# cùng một kiểu hỏng với doanh thu thuê xe chạy lẫn vào doanh thu tour (xem TX-4 ngày 07/10).
#
# Đây là một BẢNG LUẬT, không phải số liệu: nó trả lời "ví này là của ai", và câu trả lời do người
# cho chứ máy không suy được. Ví thứ ba xuất hiện thì bộ nạp NÓI RA chứ không đoán — xem
# `_epass_kiem`.
VI_EPASS = {
    "V001889627": "Vận tải Vietrip",
    "V003014969": "Vietourist (VTD)",
}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# NGẢ CỦA MỘT GIAO DỊCH NGUỒN NGOÀI — khai 07/10/2026, sau khi đo trên hệ thật
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# ĐO ĐƯỢC chứ không suy đoán. Trên bản đang chạy ngày 07/10/2026, tab "Đối soát nguồn ngoài" của
# /doi-xe hiện: tổng chi phí 1.121.825.494 đ, và CHƯA QUY ĐƯỢC VỀ XE NÀO cũng đúng 1.121.825.494 đ —
# tức 100%, cả 36 dòng. Cùng lúc màn hình Lãi lỗ đội xe kỳ 08/2026 báo LỢI NHUẬN 50,3%, vì ba tầng
# chi phí của nó đọc `fleet_trip_costs`, `fleet_maintenance` và `fleet_period_costs`, KHÔNG đọc bảng
# này. Một tỷ hai nằm ngoài sổ mà không màn hình nào nói ra.
#
# Vì sao không sửa bằng cách "tra lại xe cho 36 dòng": bản khảo sát Vietrip 05/9/2026 ghi bộ trường
# của phiếu đề xuất chi là *tour · nhà cung cấp · hình thức thanh toán · loại tiền · dòng dịch vụ*.
# KHÔNG CÓ Ô XE, và sẽ không có — phiếu ấy gắn vào TOUR. Nên "1,12 tỷ này của xe nào" là câu hỏi sai
# ngay từ đầu; hỏi mãi câu sai thì mỗi tháng lại 29 dòng không trả lời được.
#
# Một giao dịch nguồn ngoài chạy về MỘT trong năm ngả dưới đây, và chỉ hai ngả đầu được cộng vào lãi
# lỗ đội xe. Ngả do NGƯỜI ĐỌC CHỨNG TỪ chọn, không phải máy đoán từ cột `nhom` — `nhom` là chữ tự do
# (xem /giao-dich/phan-loai), nên suy ngả từ nó là dựng một phép tính trên cát.
#
# "" (rỗng) = CHƯA ĐỊNH TUYẾN, và đó là một trạng thái tử tế: nó đếm được, nói ra được, và sửa được.
# Mặc định một ngả nào đó cho đủ form thì tiền chạy vào sổ của người không tiêu nó.
NGA_CHI_PHI = {
    "xe": "Của một chiếc xe cụ thể",
    "doi": "Của cả đội, không quy về chiếc nào",
    "chu_xe": "Của chủ xe / đối tác — vào khối quyết toán chủ xe",
    "tour": "Của TOUR, không phải chi phí đội xe",
    "khong_phai_chi_phi": "Điều chuyển tiền nội bộ — không phải chi phí",
}

# Hai ngả này, và chỉ hai ngả này, là chi phí của đội xe. Dùng ở fleet_lai_lo.py để đếm phần còn
# nằm ngoài sổ. Đừng thêm "chu_xe" vào đây: khoản của chủ xe đi qua khối quyết toán chủ xe, cộng cả
# hai chỗ là tính hai lần đúng một khoản.
NGA_CUA_DOI_XE = ("xe", "doi")


class Trip(Base):
    """Một chuyến xe – nhật trình. Km đầu/cuối là số ĐO, nên phải đi kèm nguồn và thời điểm.

    `km_dau`/`km_cuoi` để rỗng nghĩa là chưa đo, không phải bằng 0. Dùng 0 làm "chưa có" là cách chắc chắn
    nhất để một ngày nào đó hệ thống báo xe chạy âm mấy trăm nghìn km."""
    __tablename__ = "fleet_trips"
    # DL-3: MỘT lệnh điều xe chỉ được có MỘT chuyến. Hàng rào thứ hai, ở cơ sở dữ liệu — lớp dịch
    # vụ đã soát trước khi tạo, nhưng phép soát ấy ĐỌC RỒI GHI nên hai lần bấm gần nhau cùng lọt.
    # Điều kiện `IS NOT NULL` bắt buộc: 756 chuyến nạp bằng Excel đều để trống cột này.
    __table_args__ = (
        Index("uq_fleet_trips_dispatch_id", "dispatch_id", unique=True,
              postgresql_where=text("dispatch_id IS NOT NULL"),
              sqlite_where=text("dispatch_id IS NOT NULL")),
    )
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
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
    # Nguồn của số km – xem KM_NGUON ở đầu tệp. Số đo mà không kèm nguồn thì không đối chiếu được với
    # số GPS: lấy GPS so với GPS thì luôn khớp, và cái "luôn khớp" đó làm người xem tin là đã kiểm.
    km_nguon: Mapped[str] = mapped_column(String(40), default="")      # khóa của KM_NGUON
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")
    co: Mapped[str] = mapped_column(String(10), default="vang")        # cờ tổng hợp của chuyến
    co_ly_do: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    # Mã phiếu gốc bên hệ thống nguồn (ví dụ phiếu chi phí xe #100 trên VieTrip). Duy nhất, để nạp lại cùng
    # một báo cáo hai lần không sinh ra 92 chuyến thứ hai – và để mỗi dòng còn truy ngược được về phiếu gốc.
    ma_phieu: Mapped[str | None] = mapped_column(String(60), nullable=True, unique=True)
    nguon: Mapped[str] = mapped_column(String(40), default="nhap_tay")
    # ── QT-1 (13/10/2026): bảy ô của Mẫu 2 mà bảng chuyến chưa có chỗ giữ ──────────────────────
    # Tạm ứng / hoàn trả / chi thêm là tiền ĐI QUA TAY tài xế, không phải chi phí của chuyến: cộng
    # chúng vào giá vốn là đếm hai lần. Giữ riêng, và chúng chỉ dùng để tính tài xế còn nợ hay còn
    # được nhận. Phụ thu là khoản khách trả thêm tại chỗ — cũng không phải chi phí.
    tam_ung: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    hoan_tra: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chi_them: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    phu_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    hdv: Mapped[str] = mapped_column(String(80), default="")
    hanh_trinh: Mapped[str] = mapped_column(String(200), default="")
    bc_tinh_trang_xe: Mapped[str] = mapped_column(Text, default="")
    # Tuyến ký bốn bước của Mẫu 2. Ghi AI ký và LÚC NÀO cho từng bước, không chỉ một trạng thái:
    # một trạng thái "đã duyệt" không trả lời được câu "ai duyệt" vào đúng lúc cần hỏi.
    qt_trang_thai: Mapped[str] = mapped_column(String(20), default="nhap", index=True)
    qt_nhap_boi: Mapped[str] = mapped_column(String(50), default="")
    qt_nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    qt_dieu_hanh: Mapped[str] = mapped_column(String(50), default="")
    qt_dieu_hanh_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    qt_ke_toan: Mapped[str] = mapped_column(String(50), default="")
    qt_ke_toan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    qt_tgd: Mapped[str] = mapped_column(String(50), default="")
    qt_tgd_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    qt_tra_lai_ly_do: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_by: Mapped[str] = mapped_column(String(50), default="")
    # ĐÃ QUYẾT TOÁN CHƯA — người nạp nói thẳng, hệ thống không suy đoán.
    #
    # Vì sao cần một cột riêng thay vì suy từ "đã có dòng chi phí nào chưa": một chuyến đang chạy có thể đã
    # biết doanh thu (hợp đồng chốt trước) mà chưa có đồng chi phí nào; cộng nó vào ô tiền thì biên lợi nhuận
    # của tháng đang chạy vọt lên gần 100% rồi tụt dần khi chứng từ về. Nhưng "chưa có dòng chi phí" cũng
    # KHÔNG đồng nghĩa "chưa quyết toán": một chuyến quyết toán xong mà thật sự không tốn đồng nào vẫn phải
    # được tính tiền. Hai việc khác nhau thì phải có hai chỗ ghi khác nhau.
    #
    # Mặc định TRUE: mọi chuyến đã có trong sổ trước bản này đều là chuyến đã quyết toán xong, nên số liệu
    # lịch sử không đổi một đồng nào sau khi nâng cấp. Chỉ cửa nạp báo cáo ngoài mới chủ động đặt FALSE cho
    # chuyến đang chạy.
    quyet_toan: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)


class TripCost(Base):
    """Một dòng chi phí của chuyến. Mỗi dòng phải trả lời được ba câu: loại gì, ai chịu, chứng từ đâu."""
    __tablename__ = "fleet_trip_costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("fleet_trips.id"))
    kind: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ben_chiu: Mapped[str] = mapped_column(String(24), default="vietourist_tam_ung")
    lit: Mapped[float] = mapped_column(Float, default=0)               # chỉ dùng cho nhiên liệu
    chung_tu: Mapped[str] = mapped_column(String(200), default="")     # mã/đường dẫn chứng từ gốc
    nguon: Mapped[str] = mapped_column(String(40), default="nhap_tay")  # nhap_tay / the_dau / epass / ocr
    # QT-1: khóa của TRA_BANG. Rỗng = chưa ai khai, KHÔNG mặc định về bên nào — xem chú thích ở
    # TRA_BANG để biết vì sao không suy từ `kind`.
    tra_bang: Mapped[str] = mapped_column(String(24), default="")
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # id giao dịch nguồn nếu khớp tự động
    # KHÓA NỐI VỚI PHIẾU BẢO DƯỠNG – chống cộng trùng một khoản sửa xe.
    # Cùng một hóa đơn garage trước nay có thể nằm ở HAI chỗ: một dòng chi phí chuyến kind="sua_chua"
    # và một phiếu trong fleet_maintenance. Không có khóa nào nối hai bảng, nên báo cáo cộng cả hai và
    # không ai nhìn ra. Khai `maintenance_id` thì báo cáo biết hai bản ghi ấy là MỘT khoản, và chỉ tính
    # một lần – thay vì đoán bằng cách so ngày và số tiền.
    maintenance_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_maintenance.id"), nullable=True)
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
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ben_chiu: Mapped[str] = mapped_column(String(24), default="chu_xe")
    chung_tu: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


MUC_DO_HONG = {"con_chay_duoc": "Còn chạy được", "phai_dung_xe": "Phải dừng xe"}
TRANG_THAI_HONG = {"moi": "Mới báo", "da_tiep_nhan": "Đội xe đã tiếp nhận", "da_dong": "Đã xử lý xong",
                   "bo_qua": "Không phải hư hỏng"}


class Fault(Base):
    """BÁO HƯ HỎNG — tài xế nói XE NÀO HỎNG GÌ. Cố ý KHÔNG có ô tiền và ô garage.

    Vì sao đây là một bảng riêng chứ không phải một đề nghị chi: lúc tài xế phát hiện xe hỏng thì
    chưa có số tiền và chưa chọn garage, mà cửa lập đề nghị chi bắt buộc có cả hai. Bắt tài xế gõ
    hai con số ấy là bắt họ bịa — đúng thứ ranh giới 09/9/2026 cấm. Đề nghị sửa chữa (loại chi
    `sua_chua_xe`) do Giám đốc đội xe lập SAU khi có báo giá, và nối ngược về đây bằng `maintenance_id`.

    Vì sao `muc_do` chỉ có HAI giá trị: câu hỏi duy nhất người điều xe cần trả lời ngay là "chiếc xe
    này tối nay còn chạy được không". Một thang năm mức nghe chuyên nghiệp hơn nhưng không ai trả lời
    nổi lúc đứng bên đường, và mức giữa thì không ai biết nên điều hay không.
    """
    __tablename__ = "fleet_faults"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    # Người báo. Nullable vì đội xe cũng ghi hộ được khi tài xế gọi điện — nhưng khi tài xế tự báo
    # thì cột này mang đúng tên họ, và đó là thứ sau này trả lời được câu "ai là người báo hỏng".
    nguoi_bao_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    bao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    hien_tuong: Mapped[str] = mapped_column(String(300))
    muc_do: Mapped[str] = mapped_column(String(20), default="con_chay_duoc")
    odo_km: Mapped[int | None] = mapped_column(Integer, nullable=True)   # số km lúc báo, nếu nhớ
    noi_xay_ra: Mapped[str] = mapped_column(String(160), default="")
    trang_thai: Mapped[str] = mapped_column(String(20), default="moi")
    tiep_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    tiep_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ket_qua: Mapped[str] = mapped_column(String(300), default="")        # đội xe ghi khi đóng
    dong_boi: Mapped[str] = mapped_column(String(50), default="")
    dong_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Phiếu bảo dưỡng/sửa chữa sinh ra từ báo hỏng này, nếu có. Rỗng KHÁC với "không tốn tiền":
    # có hỏng xử lý xong mà không phải trả đồng nào (siết lại một con ốc), và cột rỗng nói đúng thế.
    maintenance_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_maintenance.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


NGUON_NGOAI = {"the_dau": "Sao kê thẻ dầu", "epass": "Báo cáo ePass/VETC",
               "de_xuat_vietrip": "Đề xuất chi trên phần mềm Vietrip"}


class ExternalTxn(Base):
    """Giao dịch từ nguồn ngoài: thẻ dầu (sao kê ngân hàng), trạm thu phí (ePass/VETC), và đề xuất chi
    trên phần mềm Vietrip.

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
    source: Mapped[str] = mapped_column(String(20))                    # the_dau / epass / de_xuat_vietrip
    ma_gd: Mapped[str] = mapped_column(String(120))                    # mã giao dịch gốc của nhà cung cấp
    tai_khoan: Mapped[str] = mapped_column(String(40), default="")     # số tài khoản/ví (chỉ lưu phần cần)
    the_4so: Mapped[str] = mapped_column(String(8), default="")
    bien_so: Mapped[str] = mapped_column(String(20), default="")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_trips.id"), nullable=True)
    thoi_diem: Mapped[datetime] = mapped_column(DateTime)
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    lit: Mapped[float] = mapped_column(Float, default=0)
    mo_ta: Mapped[str] = mapped_column(String(300), default="")
    trung: Mapped[bool] = mapped_column(Boolean, default=False)        # bản ghi lặp: giữ lại, không tính
    trung_cua_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    khop: Mapped[str] = mapped_column(String(20), default="chua_khop")  # chua_khop / da_khop / khong_khop
    # Ngả của khoản này – khoá của NGA_CHI_PHI, rỗng = CHƯA ĐỊNH TUYẾN. Xem chú thích ở NGA_CHI_PHI.
    nga: Mapped[str] = mapped_column(String(20), default="", server_default="")
    nga_ly_do: Mapped[str] = mapped_column(String(300), default="")     # vì sao chọn ngả ấy
    nga_boi: Mapped[str] = mapped_column(String(50), default="")        # ai định tuyến
    nga_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    co: Mapped[str] = mapped_column(String(10), default="vang")
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    imported_by: Mapped[str] = mapped_column(String(50), default="")
    # Hai cột dưới đây sinh ra từ bộ đề xuất chi tháng 8/2026 của Vietrip: trong cùng một danh sách có cả
    # khoản chi thật lẫn khoản ĐIỀU CHUYỂN TIỀN giữa các tài khoản của chính công ty. Cộng gộp lại rồi gọi
    # là "chi phí đội xe" là sai gần 130 triệu chỉ trong một tháng, mà bảng vẫn trông hợp lý.
    nhom: Mapped[str] = mapped_column(String(60), default="")
    khong_phai_chi_phi: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)


# ====================== ĐỢT 3: CHỦ XE HỢP TÁC, CÔNG NỢ, CẤN TRỪ, THẾ CHẤP, QUYẾT TOÁN ======================
# Ba quy tắc sinh ra từ sự cố thực tế, và cả ba đều nằm ở cách DỰNG BẢNG chứ không ở màn hình:
#
#   1. Phân bổ chi phí chung: chỉ chia cho những xe CÓ TÊN trên chính hóa đơn đó. Vì vậy hóa đơn dùng chung
#      có bảng dòng riêng ghi rõ từng xe, chứ không có ô "số lượng xe" để người nhập gõ tay.
#   2. Cấn trừ trước khi chi: khoản cấn trừ là BẢN GHI có lịch, có trạng thái áp dụng, không phải một con số
#      trừ trong đầu lúc lập phiếu.
#   3. Một khoản chỉ được áp dụng MỘT LẦN, kể cả khi chạy lại tác vụ tự động – nên mỗi lần áp dụng có khóa
#      chống lặp riêng.
SALE_STAGES = {"hop_dong": "Đã ký hợp đồng", "thu_tien": "Đang thu tiền", "ban_giao": "Đã bàn giao",
               "giai_chap": "Đã giải chấp", "sang_ten": "Đã sang tên", "huy": "Hủy"}
PLAN_STATUS = {"nhap_chua_xac_nhan": "Nháp – chưa đủ căn cứ", "hieu_luc": "Đang hiệu lực",
               "tat_toan": "Đã tất toán", "huy": "Hủy"}
SETTLE_STATUS = {"nhap": "Nháp", "dh_xac_nhan": "Điều hành đã xác nhận", "kt_doi_soat": "Kế toán đã đối soát",
                 "da_duyet": "Đã duyệt nội bộ", "da_gui_doi_tac": "Đã gửi đối tác", "dong_ky": "Đã đóng kỳ"}
SETTLE_LINE_KINDS = {"doanh_thu": "Doanh thu đủ điều kiện", "chi_ho": "Khoản công ty chi hộ",
                     "chu_xe_chiu": "Khoản chủ xe tự chịu", "dieu_chinh": "Điều chỉnh được duyệt",
                     "phan_bo": "Phân bổ chi phí chung"}


class PartnerOwner(Base):
    """Chủ xe hợp tác. Pháp nhân đối ứng nằm ở đây chứ không suy từ xe: cấn trừ chỉ được thực hiện trên đúng
    pháp nhân, đúng đối tác, đúng hợp đồng – không tự bù nợ công ty A vào khoản công ty B phải trả."""
    __tablename__ = "fleet_partners"
    id: Mapped[int] = mapped_column(primary_key=True)
    ho_ten: Mapped[str] = mapped_column(String(160))
    tax_code: Mapped[str] = mapped_column(String(20), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)  # pháp nhân đối ứng
    xac_minh: Mapped[str] = mapped_column(String(20), default="nguon_ghi")   # định danh đã đối chiếu chưa
    note: Mapped[str] = mapped_column(String(300), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SaleCase(Base):
    """Hồ sơ bán xe. Năm trục TÁCH RỜI, không gộp vào một cột trạng thái, vì chúng đi không cùng nhịp:
    hợp đồng, thu tiền, bàn giao, giải chấp, sang tên. Xe có thể đã bàn giao mà chưa giải chấp, và đó chính
    là ca mà chặn cứng B7 tồn tại để ngăn."""
    __tablename__ = "fleet_sale_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_partners.id"), nullable=True)
    seller_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    ngay_ky: Mapped[date | None] = mapped_column(Date, nullable=True)
    gia_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # Người mua ngoài (không phải đối tác hợp tác trong fleet_partners) và mốc cam kết trả đủ. Có mốc thì
    # khoản còn phải thu mới theo dõi được như một khoản nợ có hạn, thay vì một dòng ghi chú không ai canh.
    nguoi_mua: Mapped[str] = mapped_column(String(160), default="")
    han_thu_du: Mapped[date | None] = mapped_column(Date, nullable=True)
    stage: Mapped[str] = mapped_column(String(20), default="hop_dong")
    da_ban_giao: Mapped[bool] = mapped_column(Boolean, default=False)
    da_giai_chap: Mapped[bool] = mapped_column(Boolean, default=False)
    van_ban_giai_chap: Mapped[str] = mapped_column(String(200), default="")
    da_sang_ten: Mapped[bool] = mapped_column(Boolean, default=False)
    quyen_khai_thac_tiep: Mapped[bool] = mapped_column(Boolean, default=False)
    nguon: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class Collateral(Base):
    """Bảng nhiều–nhiều xe ↔ khế ước. Đặc tả gọi đây là trái tim của hai chặn cứng B7 và B8, và đúng như vậy:
    không có bảng này thì không trả lời được câu "chiếc xe sắp sang tên có đang nằm trong tài sản bảo đảm nào
    không", và câu đó chỉ hỏi được khi quan hệ là nhiều–nhiều chứ không phải một ô chữ trên hồ sơ vay."""
    __tablename__ = "fleet_collaterals"
    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("fin_contracts.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    tu_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)     # rỗng = còn thế chấp
    van_ban_giai_chap: Mapped[str] = mapped_column(String(200), default="")
    phuong_an_rut_tai_san: Mapped[str] = mapped_column(String(300), default="")
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    nguon: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RepaymentPlan(Base):
    """Lịch thu nợ / cấn trừ theo hợp đồng. Chưa có ngày bắt đầu hoặc kỳ hạn hợp lệ thì giữ trạng thái nháp và
    KHÔNG phát thông báo quá hạn – báo quá hạn cho một lịch chưa ai xác nhận là làm hỏng lòng tin vào cảnh báo."""
    __tablename__ = "fleet_repayment_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("fleet_partners.id"))
    sale_case_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_sale_cases.id"), nullable=True)
    creditor_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    ten: Mapped[str] = mapped_column(String(200), default="")
    principal: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_ky: Mapped[int] = mapped_column(Integer, default=0)
    moi_ky: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    bat_dau: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="nhap_chua_xac_nhan")
    can_tru_tu_dong: Mapped[bool] = mapped_column(Boolean, default=True)
    nguon: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class RepaymentInstallment(Base):
    """Từng kỳ của lịch. Để trong bảng chứ không trong một ô JSON – đặc tả yêu cầu đúng như vậy, vì mỗi kỳ có
    trạng thái áp dụng riêng và phải truy được về chứng từ đã duyệt."""
    __tablename__ = "fleet_repayment_installments"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("fleet_repayment_plans.id"))
    ky: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_due: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    amount_applied: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")


class OffsetApplication(Base):
    """Một lần áp dụng cấn trừ. `idem_key` là khóa chống lặp: chạy lại tác vụ với cùng bối cảnh sẽ không trừ
    lần thứ hai. Không có nó thì mỗi lần dựng lại quyết toán là một lần trừ thêm của đối tác."""
    __tablename__ = "fleet_offset_applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    idem_key: Mapped[str] = mapped_column(String(160), unique=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("fleet_repayment_plans.id"))
    installment_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_repayment_installments.id"), nullable=True)
    settlement_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_settlements.id"), nullable=True)
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chung_tu: Mapped[str] = mapped_column(String(200), default="")
    reversed_of: Mapped[int | None] = mapped_column(Integer, nullable=True)   # bút toán đảo, giữ liên kết gốc
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class Settlement(Base):
    """Kỳ quyết toán chủ xe hợp tác. Kỳ là THÁNG DƯƠNG LỊCH (chốt 07/9/2026), chuyến gán theo ngày khởi hành.

    Đóng kỳ rồi thì khóa: sửa phải tạo bút toán điều chỉnh ở kỳ sau, không sửa ngược vào kỳ đã chốt với đối
    tác. Đó là ranh giới giữa một con số đã thỏa thuận và một con số còn đang tính."""
    __tablename__ = "fleet_settlements"
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7))                        # YYYY-MM
    partner_id: Mapped[int] = mapped_column(ForeignKey("fleet_partners.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="nhap")
    co: Mapped[str] = mapped_column(String(10), default="vang")
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    doi_tac_huong: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    doi_tac_chiu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    dieu_chinh: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    truoc_can_tru: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    can_tru: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    sau_can_tru: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chuyen_ky_sau: Mapped[float | None] = mapped_column(TIEN, nullable=True)    # số âm KHÔNG tạo phiếu chi âm
    ghi_chu: Mapped[Text] = mapped_column(Text, default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class SettlementLine(Base):
    """Từng dòng nguồn của kỳ. Bảng tổng không được là một con số không mở ra được: mỗi dòng phải nói rõ nó
    đến từ xe nào, chuyến nào, ai chịu, và chứng từ ở đâu."""
    __tablename__ = "fleet_settlement_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("fleet_settlements.id"))
    kind: Mapped[str] = mapped_column(String(20))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_trips.id"), nullable=True)
    mo_ta: Mapped[str] = mapped_column(String(300), default="")
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ben_chiu: Mapped[str] = mapped_column(String(24), default="")
    chung_tu: Mapped[str] = mapped_column(String(200), default="")
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")     # dòng điều chỉnh phải có người duyệt


class SharedInvoice(Base):
    """Hóa đơn dùng chung nhiều xe (bãi xe, tiện ích).

    Quy tắc sinh ra từ lỗi phân bổ tiền nước tháng 8/2026: chỉ chia cho những xe CÓ TÊN trên chính hóa đơn đó,
    không chia chéo giữa hai pháp nhân, không suy đoán xe thuộc nhóm nào. Vì vậy danh sách xe là các DÒNG của
    hóa đơn (bảng dưới), không phải một ô "số lượng xe" cho người nhập gõ."""
    __tablename__ = "fleet_shared_invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    so_hoa_don: Mapped[str] = mapped_column(String(60))
    ngay: Mapped[date] = mapped_column(Date)
    nha_cung_cap: Mapped[str] = mapped_column(String(160), default="")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    loai: Mapped[str] = mapped_column(String(20), default="giu_xe")
    tong_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    vat: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tieu_thuc: Mapped[str] = mapped_column(String(40), default="deu")    # deu / km / thoa_thuan
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class SharedInvoiceLine(Base):
    """Một xe có tên trên phụ lục hóa đơn dùng chung."""
    __tablename__ = "fleet_shared_invoice_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("fleet_shared_invoices.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    he_so: Mapped[float] = mapped_column(Float, default=1)


# ====================== ĐỢT 4: GHI VẾT TÁC VỤ TỰ ĐỘNG VÀ XẾP HẠNG ======================
class AiRunLog(Base):
    """Nhật ký mỗi lần một tác vụ tự động chạy.

    Đặc tả yêu cầu: ghi thời điểm, phiên bản quy tắc, số bản ghi xử lý, số cờ sinh ra, và MÃ BĂM của dữ liệu
    đầu vào – để "chạy lại cùng dữ liệu phải ra cùng kết quả" là một câu kiểm chứng được, không phải một lời
    hứa. Không có bảng này thì không kiểm toán được việc phần mềm đã tự làm những gì.
    """
    __tablename__ = "fleet_ai_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent: Mapped[str] = mapped_column(String(20))
    rule_version: Mapped[str] = mapped_column(String(20), default="")
    thoi_diem: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    dau_vao_hash: Mapped[str] = mapped_column(String(64), default="")
    so_ban_ghi: Mapped[int] = mapped_column(Integer, default=0)
    so_co: Mapped[int] = mapped_column(Integer, default=0)
    ket_qua: Mapped[str] = mapped_column(Text, default="")
    loi: Mapped[str] = mapped_column(String(300), default="")
    chay_boi: Mapped[str] = mapped_column(String(50), default="")


# ====================== CÔNG NỢ ĐỘI XE: GHI NHẬN ĐÃ TRẢ / ĐÃ THU ======================
HUONG_TIEN = {"tra_chu_xe": "Trả chủ xe (tiền ra)", "thu_chu_xe": "Thu của chủ xe (tiền vào)",
              "thu_ban_xe": "Thu tiền bán xe (tiền vào)"}


class DebtPayment(Base):
    """Một lần trả tiền hoặc thu tiền trên công nợ đội xe.

    Bảng này tồn tại vì thiếu nó thì sổ công nợ nói được "phải trả bao nhiêu" nhưng KHÔNG nói được "đã trả
    chưa" – và một sổ công nợ không phân biệt được hai điều đó là sổ dẫn tới trả tiền hai lần. Bảng quyết
    toán đóng kỳ chỉ có nghĩa hai bên đã thống nhất con số, không có nghĩa tiền đã đi.

    `idem_key` duy nhất ở cơ sở dữ liệu, cùng lý do như bảng cấn trừ: chạy lại một tác vụ, bấm hai lần một
    nút, hay nhập lại từ sao kê đều không được thành hai lần trả.
    """
    __tablename__ = "fleet_debt_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    idem_key: Mapped[str] = mapped_column(String(120), unique=True)
    huong: Mapped[str] = mapped_column(String(16))                 # tra_chu_xe / thu_chu_xe / thu_ban_xe
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_partners.id"), nullable=True)
    settlement_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_settlements.id"), nullable=True)
    sale_case_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_sale_cases.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    ngay: Mapped[date] = mapped_column(Date)
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chung_tu: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# Nhóm chi phí kỳ. Cột thứ hai là phạm vi MẶC ĐỊNH: "xe" là chi phí quy được về từng chiếc, "doi" là chi
# phí của cả đội mà chia về từng xe chỉ là ước lệ. Phân biệt này là cốt lõi của báo cáo lãi lỗ đội xe.
class PhatTaiXe(Base):
    """DX-3 · Khoản phạt của một tài xế. VÀO LƯƠNG, KHÔNG VÀO GIÁ VỐN XE.

    Chủ tịch chốt 16/10/2026: Giám đốc đội xe ghi, HCNS đối chiếu khi chốt lương.

    VÌ SAO LÀ BẢNG RIÊNG, không phải một dòng `fleet_period_costs`. Khoản phạt là tiền của NGƯỜI
    LÁI, không phải chi phí của CHIẾC XE. Nhét vào chi phí kỳ thì chiếc xe gánh lỗi của người, và
    báo cáo lãi lỗ từng xe sai — đúng hình đã ghi trong chính tệp này khi tách `fleet_faults` khỏi
    `fleet_maintenance`: gộp hai thứ khác bản chất thì mọi báo cáo sau đó phải NHỚ lọc bỏ, và cái
    «phải nhớ» ấy là chỗ mọi con số đội xe bắt đầu sai.

    `ky` là kỳ lương sẽ trừ, dạng YYYY-MM — không suy từ `ngay`: một lỗi ngày 29 có thể được chốt
    vào kỳ sau nếu bảng lương kỳ này đã khoá, và suy hộ là trừ nhầm tháng của một con người.

    `trip_id` và `vehicle_id` ĐỂ RỖNG ĐƯỢC: không phải lỗi nào cũng gắn vào một chuyến (đi muộn,
    không mặc đồng phục). Bắt buộc gắn chuyến là bắt người ghi chọn đại một chuyến.
    """
    __tablename__ = "fleet_driver_penalties"
    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)
    ngay: Mapped[date] = mapped_column(Date)
    so_tien: Mapped[float] = mapped_column(TIEN)
    ly_do: Mapped[str] = mapped_column(String(300))
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_trips.id"), nullable=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    # HCNS ĐỐI CHIẾU, không phải DUYỆT. Chủ tịch chọn 16/10/2026: người quản xe ghi, HCNS nhìn
    # thấy khi chốt lương. Dấu này nói «đã có người thứ hai nhìn», không phải «đã được phê».
    hcns_doi_chieu_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hcns_doi_chieu_boi: Mapped[str] = mapped_column(String(50), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GiaDauNgay(Base):
    """DX-3 · Giá dầu một ngày, để QUY TIỀN RA SỐ LÍT.

    Sao kê thẻ dầu cho TIỀN, không cho lít. Không có giá ngày thì không tính được tiêu hao, và ô
    «Tiêu hao» trên màn hình đội xe đọc ra một con số không ai kiểm được — đúng chỗ đã đọc 7,6
    L/100km hồi 14/10 vì cả 80 dòng đều trống số lít.

    MỘT GIÁ cho một (ngày, loại), canh bằng chỉ mục duy nhất: hai dòng cùng ngày cùng loại thì
    phép quy lít ra hai kết quả khác nhau tuỳ dòng nào đọc trước.
    """
    __tablename__ = "fleet_fuel_prices"
    id: Mapped[int] = mapped_column(primary_key=True)
    ngay: Mapped[date] = mapped_column(Date)
    loai: Mapped[str] = mapped_column(String(20), default="do")      # do / xang
    gia_lit: Mapped[float] = mapped_column(TIEN)
    nguon: Mapped[str] = mapped_column(String(120), default="")      # Petrolimex, hoá đơn, ...
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("uq_fleet_fuel_prices_ngay_loai", "ngay", "loai", unique=True),
    )


LOAI_DAU = {"do": "Dầu DO", "xang": "Xăng"}


NHOM_CHI_PHI_KY = {
    "bao_hiem":    ("Bảo hiểm xe", "xe"),
    "dang_kiem":   ("Đăng kiểm", "xe"),
    "bao_duong":   ("Bảo dưỡng, sửa chữa", "xe"),
    "luong_tai_xe": ("Lương tài xế", "xe"),
    "wifi_xe":     ("Wifi trên xe", "xe"),
    "tra_truoc":   ("Phân bổ chi phí trả trước (vỏ xe, ắc quy, thiết bị)", "xe"),
    "khac_xe":     ("Chi phí khác của xe", "xe"),
    # XS-2 (Chủ tịch 25/10/2026): công tác phí tài xế những ngày KHÔNG có chuyến (trực, chờ tour). Đo sheet
    # quyết toán của Đội xe: 10 dòng CTP 200.000 không tên tour — Chủ tịch xác nhận là chi phí thật —
    # và VTOS chưa có chỗ nào ghi được, nên lợi nhuận đội xe đang cao hơn thực tế đúng ngần ấy.
    "ctp_ngoai_chuyen": ("Công tác phí tài xế ngoài chuyến (trực, chờ tour)", "xe"),
    "bai_xe":      ("Phí bãi xe", "doi"),
    "dien_nuoc":   ("Điện, nước, wifi tại bãi", "doi"),
    "quan_ly":     ("Phí dịch vụ quản lý xe, GSHT, camera", "doi"),
    "lai_vay":     ("Chi phí lãi vay", "doi"),
    "bhxh":        ("Bảo hiểm nhân viên công ty đóng", "doi"),
    "khac_doi":    ("Chi phí phát sinh khác của đội", "doi"),
}

# Nhóm nằm NGOÀI GIÁ VỐN vận tải. Chủ tịch quyết ngày 11/10/2026: "lãi vay không tính vào giá vốn".
#
# Lãi vay xe là chi phí TÀI CHÍNH (TK 635), không phải giá vốn vận tải (627 → 632). Trước quyết định
# này các bảng quyết toán T4–T9/2026 đều cộng lãi vay vào "TỔNG CHI PHÍ" đội xe rồi lấy doanh thu trừ
# đi để ra "lợi nhuận" — nên con số lợi nhuận đội xe đã trình thấp hơn thực tế rất xa: tháng 5/2026
# bảng ghi 123.889.302 trong khi lợi nhuận đội xe theo giá vốn vận tải là 445.504.964, lệch 3,6 lần.
# Ai đọc bảng cũ sẽ kết luận sai rằng đội xe gần như không sinh lời.
#
# Vì sao là một HẰNG SỐ cạnh NHOM_CHI_PHI_KY chứ không phải một ô người nhập tự tích:
#   Một khoản vào hay không vào giá vốn là quy ước kế toán của cả công ty, không phải lựa chọn của
#   người gõ bảng tháng. Để người nhập tự tích thì tháng này tích tháng sau quên, và hai tháng liền
#   nhau không còn so được với nhau. Đặt ở đây thì phép tính giá vốn tự loại ra, không ai phải nhớ.
#
# Thêm một nhóm vào đây là việc có người ký, không phải việc dọn mã: phép kiểm
# test_cx1_lai_vay_ngoai_gia_von.py chốt đúng danh sách này.
NGOAI_GIA_VON = ("lai_vay",)


class FleetPeriodCost(Base):
    """Chi phí của một KỲ mà không gắn vào chuyến nào: bảo hiểm, lương tài xế, phí bãi, lãi vay…

    Vì sao phải có bảng riêng thay vì cộng thẳng vào chi phí chuyến:

      Lãi gộp của một chuyến (doanh thu trừ dầu, cầu đường, công tác phí) và kết quả thật của đội xe là
      hai con số khác nhau, và khoảng cách giữa chúng chính là chỗ đội xe lãi hay lỗ. Tháng 6/2026: cộng
      lãi gộp 21 chiếc được 938 triệu, nhưng sau bảo hiểm, lương, bãi xe và 327 triệu lãi vay thì còn
      227 triệu. Ai chỉ nhìn tầng đầu sẽ tưởng đội xe lãi gấp bốn lần thực tế.

    Hai điều bảng này CỐ Ý giữ tách bạch:

      1. PHẠM VI. Chi phí "xe" quy được về từng chiếc và trừ thẳng vào kết quả chiếc đó. Chi phí "đội"
         thì không: chia lãi vay cho 21 xe theo doanh thu hay theo ngày chạy đều ra những con số khác
         nhau và đều "có lý" – nên mặc định KHÔNG chia, để riêng một khối như bảng Excel đang làm.
      2. KHÔNG TỰ SINH. Mỗi dòng là một khoản có người nhập và có chứng từ. Máy không tự ước lượng lương
         hay lãi vay của kỳ chưa có số – kỳ thiếu dữ liệu phải hiện ra là THIẾU, không phải bằng 0.
    """
    __tablename__ = "fleet_period_costs"
    __table_args__ = (
        # Cùng kỳ, cùng nhóm, cùng xe, cùng diễn giải chỉ ghi một lần: nhập lại bảng tháng lần thứ hai
        # là cách nhanh nhất để chi phí nhân đôi mà mỗi dòng vẫn trông đúng.
        Index("ux_fleet_period_costs", "ky", "nhom", "vehicle_id", "mo_ta", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)                 # YYYY-MM
    pham_vi: Mapped[str] = mapped_column(String(10), default="xe")         # xe / doi
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    nhom: Mapped[str] = mapped_column(String(20))
    mo_ta: Mapped[str] = mapped_column(String(200), default="")
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chung_tu: Mapped[str] = mapped_column(String(200), default="")
    nguon: Mapped[str] = mapped_column(String(20), default="nhap_tay")     # nhap_tay / nap_tep / ai
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# HQ-2c (13/10/2026) — ĐỊNH MỨC TIÊU HAO DẦU, KHAI THEO SỐ CHỖ.
#
# Chủ tịch quyết 13/10/2026: ngưỡng do ĐỘI XE khai, không để máy tự đoán. Lý do của quyết định ấy
# nằm ngay trong phương án bị loại: lấy trung bình 6 tháng của chính chiếc xe làm mốc nghe thì gọn,
# nhưng một chiếc hao nhiều SUỐT sáu tháng thì máy coi đó là bình thường — và chiếc hao nhất đội
# trở thành chiếc không bao giờ bị cảnh báo. Một cái ngưỡng tự sinh từ chính số liệu nó canh thì
# không canh được gì.
#
# VÌ SAO KHOÁ THEO `seats` CHỨ KHÔNG THEO TỪNG XE. Số chỗ là thuộc tính đã có sẵn trong danh mục,
# và nó chính là thứ quyết định mức hao: xe 45 chỗ với xe 16 chỗ khác hẳn nhau. Khai theo từng xe
# thì mỗi lần mua xe mới lại thêm một ô trống nữa, và Đội xe phải khai lại con số họ vừa khai cho
# chiếc y hệt. Khai theo số chỗ thì xe mới cùng loại dùng ngay ngưỡng đã có.
#
# `l_100km` là ngưỡng TRẦN: vượt quá thì báo. Để trống (chưa có dòng) nghĩa là CHƯA AI KHAI —
# màn hình vẫn in con số tiêu hao thật, chỉ không bật cảnh báo, và nói rõ đang chờ ai.
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class FuelNorm(Base):
    """Định mức tiêu hao dầu theo số chỗ — một dòng cho mỗi loại xe."""
    __tablename__ = "fleet_fuel_norms"
    id: Mapped[int] = mapped_column(primary_key=True)
    seats: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    l_100km: Mapped[float] = mapped_column(Float)
    ghi_chu: Mapped[str] = mapped_column(String(200), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
