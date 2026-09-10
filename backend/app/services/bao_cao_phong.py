"""Báo cáo tự động hiện THẲNG TRÊN MÀN HÌNH VTOS – theo phòng ban và toàn công ty.

Quyết định của Chủ tịch 09/9/2026:

    "Báo cáo lập tự động trên màn hình VTOS. Báo cáo của các phòng ban thì hiện lên cho trưởng phòng
     hoặc giám đốc; còn toàn công ty thì hiện lên cho Chủ tịch và TGĐ. Không cần gửi mail hay Zalo."
    "Nghĩa là không cần VIẾT báo cáo, mà sẽ HIỆN báo cáo lên màn hình VTOS của từng trưởng phòng và
     CT, TGĐ – nên cần phải có luồng logic, phép tính, cấu trúc."

────────────────────────────────────────────────────────────────────────────────
ĐIỀU NÀY ĐỔI HẲN HÌNH DẠNG CỦA BÁO CÁO
────────────────────────────────────────────────────────────────────────────────

Báo cáo cũ (robot R7) là một BÀI VIẾT: markdown, có câu chữ, có nhận xét. Bài viết hợp với việc gửi
đi – người nhận đọc một lần rồi thôi.

Báo cáo hiện trên màn hình thì không phải bài viết, mà là một BẢNG CHỈ TIÊU. Mỗi dòng là một con số
có cấu trúc, và cấu trúc đó phải mang theo bốn thứ, không phải một:

    giá trị · cách tính · lấy từ đâu · nếu xấu thì làm gì

Ba thứ sau quan trọng không kém con số. Một trưởng phòng mở màn hình thấy "12" thì câu hỏi đầu tiên
luôn là "12 này tính thế nào" – không trả lời được thì người ta không dùng con số, và một chỉ tiêu
không ai dùng thì bằng không có. Nên `cong_thuc` và `nguon` đi kèm từng dòng, không nằm trong một
tài liệu riêng mà ba tháng sau không khớp với mã nữa.

    Đây cũng là lý do KHÔNG dựng bảng chỉ tiêu bằng markdown rồi để màn hình tách chữ ra: chữ thì
    không có chỗ để gắn công thức, và mọi thứ gắn thêm vào chữ đều mất khi ai đó sửa câu văn.

GIÁ TRỊ RỖNG LÀ MỘT GIÁ TRỊ. `gia_tri = None` nghĩa là CHƯA CÓ SỐ, và màn hình phải hiện ra là chưa
có – khác hẳn với 0. Trộn hai cái đó là cách một bảng điều khiển bắt đầu nói dối: một phòng chưa nhập
liệu trông y hệt một phòng không có việc gì xảy ra.

────────────────────────────────────────────────────────────────────────────────
AI XEM ĐƯỢC GÌ
────────────────────────────────────────────────────────────────────────────────

Cắt theo NGƯỜI CHỊU TRÁCH NHIỆM về con số, không cắt theo "ai tò mò". Nhân viên trong phòng KHÔNG
mặc định xem báo cáo phòng: mỗi người thấy việc của mình là một chuyện, một bản tổng hợp hiệu quả cả
phòng nằm trong tay mọi người là chuyện khác.

Chủ tịch, TGĐ và Ban Kiểm soát xem tất cả – hai người đầu vì đó là quyết định trên; Ban Kiểm soát vì
kiểm soát mà chỉ được xem bản tóm tắt do bên bị kiểm soát chọn thì không kiểm được gì.
"""
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.services import access as AC

TOAN_CTY = "toan_cty"
TEN_KY = {"ngay": "ngày", "tuan": "tuần", "thang": "tháng"}

# Phòng ban có báo cáo riêng, và AI XEM ngoài Chủ tịch / TGĐ / Ban Kiểm soát.
# Cố ý viết thẳng từng vai trò chứ không suy từ bảng phòng ban: suy thì một vai trò mới thêm vào phòng
# sẽ tự có quyền xem bản tổng hợp của phòng đó mà không ai cân nhắc – nới quyền không ai quyết định.
PHONG = {
    "dieu_hanh": {"ten": "Điều hành", "xem": ("tp_dh", "ptgd_doan")},
    "kd_le":     {"ten": "Kinh doanh", "xem": ("gd_kd", "tp_kd", "ptgd_mkt")},
    "doi_xe":    {"ten": "Đội xe", "xem": ("gd_doi_xe",)},
    "huong_dan": {"ten": "Hướng dẫn", "xem": ("tp_hd",)},
    "marketing": {"ten": "Marketing", "xem": ("ptgd_mkt",)},
    "ketoan":    {"ten": "Kế toán", "xem": ("ketoan",)},
    "hcns":      {"ten": "Hành chính & Nhân sự", "xem": ("hcns",)},
    # Ban Visa chưa có vai trò trưởng bộ phận trong bảng vai trò. Tạm để chuyên viên visa xem báo cáo
    # của chính ban mình, và ghi ra đây rằng đó là chỗ TẠM: khi có vai trò phụ trách Visa thì sửa dòng
    # này, đừng để nó trôi thành tiền lệ "nhân viên xem báo cáo phòng".
    "visa":      {"ten": "Ban Visa", "xem": ("nv_visa",)},
}
XEM_TAT_CA = AC.FULL_VIEW + AC.READ_ALL          # Chủ tịch, TGĐ, Ban Kiểm soát, robot kiểm soát


# Năng lực cấp lẻ cho MỘT NGƯỜI, mở mọi báo cáo. Xem chú thích ở models/core.CAPABILITIES.
NANG_LUC_MOI_PHONG = "bao_cao_moi_phong"


def pham_vi_duoc_xem(vai_tro: str) -> list[str]:
    """Các phạm vi báo cáo một VAI TRÒ được mở. Rỗng = không xem báo cáo tự động nào.

    Hàm này chỉ xét vai trò. Ngoại lệ cấp cho từng người nằm ở `pham_vi_cho_nguoi` – tách hai hàm
    có chủ ý, để đọc mã còn thấy được "theo chức danh thì được những gì", tách khỏi "ai đang được
    cấp thêm". Gộp lại thì ba tháng nữa không ai trả lời được câu hỏi thứ nhất.
    """
    if vai_tro in XEM_TAT_CA:
        return [TOAN_CTY] + list(PHONG)
    return [p for p, v in PHONG.items() if vai_tro in v["xem"]]


def pham_vi_cho_nguoi(db, u) -> list[str]:
    """Phạm vi thật của một NGƯỜI: theo vai trò, cộng ngoại lệ đã cấp cho riêng người đó."""
    from app.services import access as AC
    theo_vai = pham_vi_duoc_xem(u.role)
    if AC.co_quyen(db, u, NANG_LUC_MOI_PHONG):
        # Hợp hai danh sách, giữ thứ tự: toàn công ty trước, rồi tới các phòng.
        return [TOAN_CTY] + list(PHONG)
    return theo_vai


def khoang(kind: str, moc: date | None = None) -> tuple[date, date, str]:
    """Khoảng thời gian và mã kỳ.

    Báo cáo phòng dùng CÙNG khoảng với báo cáo công ty, để hai bản đặt cạnh nhau còn so được. Khác
    khoảng thì mọi con số lệch nhau đều đổ được cho 'khác kỳ', và không ai đối chiếu nữa.
    """
    d = moc or date.today()
    if kind == "ngay":
        return d, d, str(d)
    if kind == "tuan":
        return d - timedelta(days=6), d, f"{d:%G}-W{d.isocalendar()[1]:02d}"
    if kind == "thang":
        return d.replace(day=1), d, f"{d:%Y-%m}"
    raise ValueError("kind: ngay / tuan / thang")


def ct(ma: str, ten: str, gia_tri, don_vi: str, cong_thuc: str, nguon: str,
       muc: str = "", viec: str = "", chi_tiet=None) -> dict:
    """Một CHỈ TIÊU – đơn vị nhỏ nhất của báo cáo trên màn hình.

    gia_tri = None nghĩa là CHƯA CÓ SỐ, không phải 0. Màn hình hiện 'chưa có' và không tô màu cảnh
    báo: một phòng chưa nhập liệu không phải một phòng đang có vấn đề, và tô nhầm màu vào đó là cách
    làm người ta thôi tin bảng.

    muc:  "" bình thường · "vang" cần rà · "do" phải xử lý
    viec: nếu xấu thì làm gì. Một con số đỏ mà không nói làm gì thì chỉ tạo lo lắng, không tạo hành động.
    """
    return {"ma": ma, "ten": ten, "gia_tri": gia_tri, "don_vi": don_vi,
            "cong_thuc": cong_thuc, "nguon": nguon,
            "muc": "" if gia_tri is None else muc,
            "viec": viec, "chi_tiet": chi_tiet}


def _muc(dieu_kien: bool, muc: str = "vang") -> str:
    return muc if dieu_kien else ""


# ═══════════════════════════ CHỈ TIÊU TỪNG PHÒNG ═══════════════════════════
def _dieu_hanh(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.core import Tour, ServiceRequest
    from app.models.hach_toan import ThieuGiaVon
    from app.services import rules as R
    kh = db.execute(select(Tour).where(Tour.start_date >= tu, Tour.start_date <= den)).scalars().all()
    kt = db.execute(select(Tour).where(Tour.end_date >= tu, Tour.end_date <= den)).scalars().all()
    hom_nay = date.today()
    qua_han = [t for t in db.execute(select(Tour).where(Tour.status == "ket_thuc")).scalars()
               if hom_nay > R.settlement_deadline(db, t)]
    thieu = db.execute(select(ThieuGiaVon).where(ThieuGiaVon.trang_thai == "cho",
                                                 ThieuGiaVon.phong_ban == "dieu_hanh")).scalars().all()
    cho_bk = db.execute(select(func.count()).select_from(ServiceRequest)
                        .where(ServiceRequest.booking_id == None)).scalar()          # noqa: E711
    return [
        ct("khoi_hanh", "Chuyến khởi hành trong kỳ", len(kh), "chuyến",
           "Đếm tour có ngày khởi hành nằm trong kỳ", "tours.start_date",
           chi_tiet=[t.code for t in kh[:20]]),
        ct("ket_thuc", "Chuyến kết thúc trong kỳ", len(kt), "chuyến",
           "Đếm tour có ngày kết thúc nằm trong kỳ", "tours.end_date",
           chi_tiet=[t.code for t in kt[:20]]),
        ct("qua_han_quyet_toan", "Tour quá hạn quyết toán", len(qua_han), "tour",
           "Tour đã kết thúc mà hôm nay đã qua hạn quyết toán (hạn lấy từ tham số chính sách, "
           "không viết cứng)", "tours.status='ket_thuc' + tham số hạn quyết toán",
           muc=_muc(len(qua_han) > 0, "do"),
           viec="Quyết toán ngay hoặc nêu lý do – tour chưa quyết toán thì giá vốn chưa vào sổ, "
                "và lãi gộp toàn công ty đang bị thổi lên",
           chi_tiet=[t.code for t in qua_han[:20]]),
        ct("thieu_gia_von", "Đơn bị giữ vì thiếu giá vốn", len(thieu), "đơn",
           "Đơn có doanh thu mà chưa có giá vốn, đang chờ phòng bổ sung",
           "thieu_gia_von (trạng thái 'cho', phòng 'dieu_hanh')",
           muc=_muc(len(thieu) > 0, "do"),
           viec="Bổ sung giá vốn. Thiếu giá vốn KHÔNG phải giá vốn bằng 0 – hệ thống giữ đơn lại "
                "chính vì thế, và ghi đại một con số cho qua còn tệ hơn để trống",
           chi_tiet=[x.ma_don for x in thieu[:20]]),
        ct("yeu_cau_cho", "Yêu cầu dịch vụ chưa tạo booking", cho_bk, "yêu cầu",
           "Đếm yêu cầu dịch vụ chưa gắn booking nào", "service_requests.booking_id rỗng",
           muc=_muc(cho_bk > 0), viec="Tạo booking hoặc đóng yêu cầu kèm lý do"),
    ]


def _kd_le(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.core import Booking, ServiceRequest
    from app.models.crm import Lead
    from app.models.ban_hang import BaoGia
    bk = [b for b in db.execute(select(Booking)).scalars() if tu <= b.created_at.date() <= den]
    dt = sum((b.amount or 0) - (b.discount or 0) for b in bk)
    lead = [l for l in db.execute(select(Lead)).scalars() if tu <= l.received_at.date() <= den]
    bg = db.execute(select(BaoGia)).scalars().all()
    gui = [b for b in bg if b.trang_thai == "da_gui"]
    chot = [b for b in bg if b.trang_thai == "khach_chot"]
    duoi = [b for b in bg if b.duoi_bien]
    cho = db.execute(select(func.count()).select_from(ServiceRequest)
                     .where(ServiceRequest.booking_id == None)).scalar()             # noqa: E711
    # Tỷ lệ chốt: mẫu số bằng 0 thì để RỖNG, không để 0%. "Chưa gửi báo giá nào" và "gửi mà không ai
    # chốt" là hai tình huống ngược nhau, hiện cùng một con số 0% là sai.
    mau = len(gui) + len(chot)
    ty_le = round(len(chot) / mau * 100, 1) if mau else None
    return [
        ct("booking", "Booking mới trong kỳ", len(bk), "booking",
           "Đếm booking có ngày tạo trong kỳ", "bookings.created_at"),
        ct("doanh_thu", "Doanh thu booking trong kỳ", dt, "đ",
           "Tổng (số tiền − giảm giá) của các booking tạo trong kỳ",
           "bookings.amount − bookings.discount"),
        ct("lead", "Khách mới (lead) trong kỳ", len(lead), "khách",
           "Đếm lead có ngày nhận trong kỳ", "leads.received_at"),
        ct("bao_gia_cho", "Báo giá đang chờ khách trả lời", len(gui), "báo giá",
           "Báo giá ở trạng thái đã gửi", "bao_gia.trang_thai='da_gui'",
           muc=_muc(len(gui) > 0), viec="Gọi lại khách trước khi báo giá hết hạn hiệu lực"),
        ct("bao_gia_chot", "Báo giá khách đã chốt", len(chot), "báo giá",
           "Báo giá ở trạng thái khách chốt", "bao_gia.trang_thai='khach_chot'"),
        ct("ty_le_chot", "Tỷ lệ chốt báo giá", ty_le, "%",
           "Khách chốt ÷ (đang chờ + khách chốt) × 100. Chưa gửi báo giá nào thì để RỖNG, "
           "không để 0% – hai tình huống đó ngược nhau", "bao_gia.trang_thai"),
        ct("duoi_bien", "Báo giá từng gửi dưới ngưỡng biên", len(duoi), "báo giá",
           "Báo giá có cờ dưới biên (gửi khi biên thấp hơn ngưỡng, kèm giải trình)",
           "bao_gia.duoi_bien", muc=_muc(len(duoi) > 0),
           viec="Đọc lại giải trình – mỗi bản dưới biên đều bắt buộc có"),
        ct("yeu_cau_cho", "Yêu cầu chưa tạo booking", cho, "yêu cầu",
           "Đếm yêu cầu dịch vụ chưa gắn booking", "service_requests.booking_id rỗng",
           muc=_muc(cho > 0)),
    ]


def _doi_xe(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.fleet import Trip, VehicleDocument
    chuyen = db.execute(select(Trip).where(Trip.ngay_di >= tu, Trip.ngay_di <= den)).scalars().all()
    cho_xn = [c for c in chuyen if c.status == "cho_xac_nhan"]
    dt = sum(c.doanh_thu or 0 for c in chuyen)
    # Km chưa đo để RỖNG. Cộng km của những chuyến đã đo rồi gọi là "tổng km" là sai: người đọc hiểu
    # đó là tổng của mọi chuyến.
    da_do = [c for c in chuyen if c.km_dau is not None and c.km_cuoi is not None]
    km = sum((c.km_cuoi - c.km_dau) for c in da_do) if da_do else None
    han = date.today() + timedelta(days=30)
    sap_het = db.execute(select(VehicleDocument)
                         .where(VehicleDocument.expires_on != None,                  # noqa: E711
                                VehicleDocument.expires_on <= han)).scalars().all()
    return [
        ct("chuyen", "Chuyến xe trong kỳ", len(chuyen), "chuyến",
           "Đếm nhật trình có ngày đi trong kỳ", "fleet_trips.ngay_di"),
        ct("doanh_thu", "Doanh thu chuyến ghi nhận", dt, "đ",
           "Tổng doanh thu của các chuyến trong kỳ", "fleet_trips.doanh_thu"),
        ct("km", f"Km chạy ({len(da_do)}/{len(chuyen)} chuyến đã đo)", km, "km",
           "Tổng (km cuối − km đầu) của những chuyến ĐÃ ĐO. Chuyến chưa đo không tính bằng 0 – "
           "km rỗng nghĩa là chưa đo", "fleet_trips.km_dau, km_cuoi",
           muc=_muc(len(da_do) < len(chuyen)),
           viec="Nhập km cho các chuyến còn thiếu – thiếu km thì không tính được chi phí trên km"),
        ct("cho_xac_nhan", "Chuyến còn chờ xác nhận", len(cho_xn), "chuyến",
           "Nhật trình ở trạng thái chờ xác nhận", "fleet_trips.status='cho_xac_nhan'",
           muc=_muc(len(cho_xn) > 0), viec="Xác nhận hoặc trả lại cho tài xế"),
        ct("giay_to", "Giấy tờ xe / bằng lái hết hạn trong 30 ngày", len(sap_het), "giấy tờ",
           "Đếm giấy tờ có ngày hết hạn trong vòng 30 ngày tới",
           "vehicle_documents.expires_on", muc=_muc(len(sap_het) > 0, "do"),
           viec="Gia hạn trước ngày hết hạn – xe hết đăng kiểm là không chạy được, "
                "và lệnh điều xe đã lên rồi thì phải đổi xe gấp",
           chi_tiet=[f"{x.kind} {x.number} – hết hạn {x.expires_on}" for x in sap_het[:20]]),
    ]


def _huong_dan(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.hr import GuideAssignment
    pc = [g for g in db.execute(select(GuideAssignment)).scalars()
          if tu <= g.assigned_at.date() <= den]
    chua = [g for g in pc if g.confirmed_at is None]
    thu_lao = sum((g.days or 0) * (g.rate_per_day or 0) for g in pc)
    return [
        ct("phan_cong", "Phân công hướng dẫn viên trong kỳ", len(pc), "lượt",
           "Đếm phân công có ngày giao trong kỳ", "guide_assignments.assigned_at"),
        ct("chua_xac_nhan", "Chưa được HDV xác nhận", len(chua), "lượt",
           "Phân công chưa có thời điểm xác nhận", "guide_assignments.confirmed_at rỗng",
           muc=_muc(len(chua) > 0), viec="Gọi lại HDV – quá 24 giờ chưa xác nhận là phải tìm người thay"),
        ct("thu_lao", "Thù lao dự tính theo phân công", thu_lao, "đ",
           "Tổng (số ngày × đơn giá ngày) của các phân công trong kỳ",
           "guide_assignments.days × rate_per_day"),
    ]


def _marketing(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.nap_bo_sung import MktChannelSpend
    from app.models.marketing import Campaign
    from app.models.crm import Lead
    ky = f"{den:%Y-%m}"
    chi = db.execute(select(MktChannelSpend).where(MktChannelSpend.ky == ky)).scalars().all()
    co_so = [x for x in chi if x.so_tien is not None]
    thieu_so = [x for x in chi if x.so_tien is None]
    tong = sum(x.so_tien or 0 for x in co_so) if co_so else None
    lead = [l for l in db.execute(select(Lead)).scalars() if tu <= l.received_at.date() <= den]
    theo_kenh: dict[str, int] = {}
    for l in lead:
        theo_kenh[l.channel or "không rõ"] = theo_kenh.get(l.channel or "không rõ", 0) + 1
    dang_chay = db.execute(select(func.count()).select_from(Campaign)
                           .where(Campaign.status == "dang_chay")).scalar()
    # Chi phí trên mỗi khách: RỖNG khi thiếu chi hoặc thiếu khách. Đây là con số dễ dùng sai nhất
    # trong cả bảng – tính ra một số đẹp từ dữ liệu thiếu rồi mang đi so tháng là hỏng thật.
    cpl = round(tong / len(lead)) if (tong is not None and lead and not thieu_so) else None
    return [
        ct("chi_kenh", f"Chi marketing tháng {ky}", tong, "đ",
           "Tổng số tiền các dòng chi của tháng. Dòng CHƯA CÓ số tiền không cộng bằng 0",
           "mkt_channel_spend.so_tien"),
        ct("thieu_so_tien", "Dòng chi chưa có số tiền", len(thieu_so), "dòng",
           "Đếm dòng chi để trống số tiền", "mkt_channel_spend.so_tien rỗng",
           muc=_muc(len(thieu_so) > 0), viec="Nhập số tiền – thiếu dòng nào thì tổng chi và chi phí "
                                             "trên mỗi khách đều đang thiếu phần đó"),
        ct("lead", "Khách mới trong kỳ", len(lead), "khách",
           "Đếm lead có ngày nhận trong kỳ", "leads.received_at",
           chi_tiet=[f"{k}: {v}" for k, v in sorted(theo_kenh.items(), key=lambda x: -x[1])[:12]]),
        ct("cpl", "Chi phí trên mỗi khách mới", cpl, "đ/khách",
           "Tổng chi tháng ÷ số khách mới trong kỳ. Để RỖNG khi còn dòng chi thiếu số tiền hoặc "
           "chưa có khách nào – một con số đẹp tính từ dữ liệu thiếu là con số sai",
           "mkt_channel_spend + leads"),
        ct("chien_dich", "Chiến dịch đang chạy", dang_chay, "chiến dịch",
           "Đếm chiến dịch ở trạng thái đang chạy", "campaigns.status='dang_chay'"),
    ]


def _ketoan(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.payments import BankTransaction
    from app.models.nap_bo_sung import PurchaseInvoice
    from app.models.accounting import PeriodLock
    gd = [t for t in db.execute(select(BankTransaction)).scalars()
          if tu <= t.transaction_date.date() <= den]
    vao = sum(t.amount or 0 for t in gd if t.transfer_type == "in")
    ra = sum(t.amount or 0 for t in gd if t.transfer_type == "out")
    cho = db.execute(select(func.count()).select_from(BankTransaction)
                     .where(BankTransaction.match_status == "cho_ke_toan")).scalar()
    hd = db.execute(select(func.count()).select_from(PurchaseInvoice)
                    .where(PurchaseInvoice.ngay_hd >= tu, PurchaseInvoice.ngay_hd <= den)).scalar()
    ky = f"{den:%Y-%m}"
    khoa = db.execute(select(PeriodLock).where(PeriodLock.period == ky)).scalars().first()
    return [
        ct("tien_vao", "Tiền vào trong kỳ", vao, "đ",
           "Tổng số tiền giao dịch chiều vào có ngày trong kỳ",
           "bank_transactions.transfer_type='in'"),
        ct("tien_ra", "Tiền ra trong kỳ", ra, "đ",
           "Tổng số tiền giao dịch chiều ra có ngày trong kỳ",
           "bank_transactions.transfer_type='out'"),
        ct("cho_khop", "Giao dịch chờ Kế toán khớp (mọi kỳ)", cho, "giao dịch",
           "Đếm giao dịch ở trạng thái chờ kế toán khớp – KHÔNG giới hạn trong kỳ, vì giao dịch "
           "tồn từ tháng trước mới là giao dịch đáng lo",
           "bank_transactions.match_status='cho_ke_toan'",
           muc=_muc(cho > 0), viec="Khớp về booking hoặc đánh dấu không phải tiền khách – "
                                   "mỗi ngày để lại là một ngày công nợ khách chưa đúng"),
        ct("hoa_don_vao", "Hóa đơn GTGT đầu vào có ngày trong kỳ", hd, "hóa đơn",
           "Đếm hóa đơn mua vào theo ngày hóa đơn", "purchase_invoices.ngay_hd"),
        ct("khoa_so", f"Kỳ {ky}", 1 if khoa else 0, "đã khóa sổ (1) / chưa (0)",
           "Có bản ghi khóa kỳ cho kỳ này hay không", "period_locks.period"),
    ]


def _hcns(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.hr import Employee, PayrollRun
    from app.models.hrm import LaborContract, LeaveRequest
    dang_lam = db.execute(select(func.count()).select_from(Employee)
                          .where(Employee.active == True)).scalar()                  # noqa: E712
    han = date.today() + timedelta(days=30)
    sap_het = db.execute(select(LaborContract)
                         .where(LaborContract.status == "hieu_luc",
                                LaborContract.effective_to != None,                  # noqa: E711
                                LaborContract.effective_to <= han)).scalars().all()
    cho_duyet = db.execute(select(func.count()).select_from(LeaveRequest)
                           .where(LeaveRequest.status == "cho_duyet")).scalar()
    ky = f"{den:%Y-%m}"
    run = db.execute(select(PayrollRun).where(PayrollRun.period == ky)).scalars().first()
    return [
        ct("nhan_su", "Nhân sự đang làm việc", dang_lam, "người",
           "Đếm hồ sơ nhân sự còn hiệu lực", "employees.active"),
        ct("hd_sap_het", "Hợp đồng lao động hết hạn trong 30 ngày", len(sap_het), "hợp đồng",
           "Hợp đồng còn hiệu lực, có ngày hết hạn trong 30 ngày tới. Hợp đồng KHÔNG xác định thời "
           "hạn để trống ngày hết hạn nên không rơi vào đây",
           "labor_contracts.effective_to", muc=_muc(len(sap_het) > 0, "do"),
           viec="Ký phụ lục hoặc gia hạn TRƯỚC ngày hết hạn – để quá hạn là hợp đồng tự chuyển "
                "thành không xác định thời hạn"),
        ct("nghi_cho_duyet", "Đơn nghỉ / tăng ca chờ duyệt", cho_duyet, "đơn",
           "Đếm đơn ở trạng thái chờ duyệt", "leave_requests.status='cho_duyet'",
           muc=_muc(cho_duyet > 0)),
        # Chưa lập bảng lương KHÁC bảng lương bằng 0 – nên giá trị ở đây là RỖNG, không phải 0.
        ct("bang_luong", f"Bảng lương kỳ {ky}",
           None if run is None else 1, "đã có (1) / chưa lập (rỗng)",
           "Có bản ghi bảng lương cho kỳ này hay không. Chưa lập thì để RỖNG, không phải 0",
           "payroll_runs.period",
           chi_tiet=[f"trạng thái: {run.status}"] if run else ["chưa lập bảng lương kỳ này"]),
    ]


def _visa(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.visa import VisaCase
    ho_so = db.execute(select(VisaCase)).scalars().all()
    moi = [c for c in ho_so if c.created_at and tu <= c.created_at.date() <= den]
    dang = [c for c in ho_so if c.lifecycle_status == "ACTIVE"]
    theo_kq: dict[str, int] = {}
    for c in ho_so:
        theo_kq[c.result_status] = theo_kq.get(c.result_status, 0) + 1
    return [
        ct("ho_so_moi", "Hồ sơ visa mới trong kỳ", len(moi), "hồ sơ",
           "Đếm hồ sơ có ngày tạo trong kỳ", "visa_cases.created_at"),
        ct("dang_xu_ly", "Hồ sơ đang xử lý", len(dang), "hồ sơ",
           "Hồ sơ ở vòng đời ACTIVE", "visa_cases.lifecycle_status",
           chi_tiet=[f"{k}: {v}" for k, v in theo_kq.items()]),
    ]


# ═══════════════════════════ TOÀN CÔNG TY ═══════════════════════════
def _toan_cty(db: Session, tu: date, den: date) -> list[dict]:
    """Báo cáo Chủ tịch và TGĐ: bốn con số của công ty, cộng phần TỔNG HỢP TỪ CÁC PHÒNG.

    Phần tổng hợp là điều bản báo cáo cũ không có: nó lấy đúng các chỉ tiêu đã đánh dấu ĐỎ ở từng
    phòng và gom lại. Nhờ vậy hai bản luôn nói cùng một chuyện – Chủ tịch thấy 3 việc đỏ thì mở báo
    cáo phòng ra sẽ thấy đúng 3 việc đó, không phải một con số khác tính theo cách khác.
    """
    from app.services import finance as FIN
    from app.models.core import Alert
    fc = FIN.forecast_13w(db)
    canh_bao = db.execute(select(Alert).where(Alert.resolved == False)).scalars().all()   # noqa: E712
    do = [a for a in canh_bao if a.level == "red"]

    ds = [
        ct("tien", "Tiền hiện có", fc["opening"], "đ",
           "Số dư đầu của dự báo dòng tiền 13 tuần", "dự báo dòng tiền"),
        ct("tuan_canh_bao", "Số tuần cảnh báo trong dự báo 13 tuần", len(fc["alerts"]), "tuần",
           "Đếm tuần mà dự báo dòng tiền báo thiếu", "dự báo dòng tiền 13 tuần",
           muc=_muc(len(fc["alerts"]) > 0, "do"),
           viec="Xem lịch thu – chi 13 tuần và quyết sớm",
           chi_tiet=fc["alerts"][:10]),
        ct("canh_bao", "Cảnh báo nghiệp vụ đang mở", len(canh_bao), "cảnh báo",
           "Đếm cảnh báo chưa đóng", "alerts.resolved = false",
           muc=_muc(len(do) > 0, "do"),
           viec="Giao cho phòng phụ trách xử lý hoặc đóng cảnh báo kèm lý do – cảnh báo đỏ để mở "
                "lâu ngày thì lần sau không ai đọc bảng cảnh báo nữa",
           chi_tiet=[a.message for a in do[:10]]),
    ]

    # Gom việc đỏ của từng phòng. Đây là chỗ báo cáo toàn công ty KHÔNG tự tính lại con số nào: nó
    # đọc lại đúng kết quả của báo cáo phòng. Tính lại theo cách khác là cách chắc chắn để hai bản
    # lệch nhau, và lúc lệch thì không ai biết bản nào đúng.
    for ma, cfg in PHONG.items():
        try:
            dong = HAM[ma](db, tu, den)
        except Exception as e:      # noqa – một phòng hỏng không được làm chết báo cáo công ty
            ds.append(ct(f"phong_{ma}", f"{cfg['ten']} – KHÔNG lấy được số", None, "",
                         "Chỉ tiêu của phòng này lỗi khi tính",
                         f"bao_cao_phong.{ma}", muc="vang",
                         chi_tiet=[f"{type(e).__name__}: {str(e)[:200]}"]))
            continue
        viec_do = [x for x in dong if x["muc"] == "do"]
        ds.append(ct(f"phong_{ma}", f"{cfg['ten']} – việc phải xử lý", len(viec_do), "việc",
                     "Đếm chỉ tiêu mức ĐỎ trong báo cáo của phòng này. KHÔNG tính lại theo cách "
                     "khác – đọc lại đúng kết quả của báo cáo phòng, để hai bản không lệch nhau",
                     f"báo cáo phòng {cfg['ten']}",
                     muc=_muc(len(viec_do) > 0, "do"),
                     chi_tiet=[f"{x['ten']}: {x['gia_tri']} {x['don_vi']}" for x in viec_do]))
    return ds


HAM = {"dieu_hanh": _dieu_hanh, "kd_le": _kd_le, "doi_xe": _doi_xe, "huong_dan": _huong_dan,
       "marketing": _marketing, "ketoan": _ketoan, "hcns": _hcns, "visa": _visa}


def bao_cao(db: Session, kind: str, pham_vi: str, moc: date | None = None) -> dict:
    """Bảng chỉ tiêu của một phạm vi, tính tại chỗ. KHÔNG ghi gì vào cơ sở dữ liệu.

    Tính tại chỗ chứ không đọc bản đã lưu: một trưởng phòng mở màn hình lúc 10 giờ sáng cần số của
    lúc 10 giờ, không cần số của 20:30 hôm qua. Bản lưu theo lịch vẫn có, nhưng để ĐỐI CHIẾU về sau
    – hai việc khác nhau, và gộp lại thì mất một trong hai.
    """
    tu, den, ky = khoang(kind, moc)
    if pham_vi == TOAN_CTY:
        ten, dong = "Toàn công ty", _toan_cty(db, tu, den)
    elif pham_vi in PHONG:
        ten, dong = PHONG[pham_vi]["ten"], HAM[pham_vi](db, tu, den)
    else:
        raise ValueError(f"Không có phạm vi báo cáo '{pham_vi}'")
    return {"kind": kind, "kind_ten": TEN_KY[kind], "pham_vi": pham_vi, "pham_vi_ten": ten,
            "ky": ky, "tu": str(tu), "den": str(den), "chi_tieu": dong,
            "so_viec_do": sum(1 for x in dong if x["muc"] == "do"),
            "so_can_ra_soat": sum(1 for x in dong if x["muc"] == "vang"),
            "so_chua_co_so": sum(1 for x in dong if x["gia_tri"] is None)}


def sang_markdown(b: dict) -> str:
    """Bản chữ để LƯU LẠI đối chiếu về sau. Màn hình dùng chi_tieu, không dùng bản này."""
    d = [f"# Báo cáo {b['kind_ten']} – {b['pham_vi_ten']} · kỳ {b['ky']} ({b['tu']} → {b['den']})", ""]
    for x in b["chi_tieu"]:
        gt = "chưa có số" if x["gia_tri"] is None else f"{x['gia_tri']:,}" if isinstance(
            x["gia_tri"], (int, float)) else str(x["gia_tri"])
        dau = {"do": "🔴 ", "vang": "🟡 "}.get(x["muc"], "")
        d.append(f"- {dau}**{x['ten']}**: {gt} {x['don_vi']}".rstrip())
        d.append(f"  - cách tính: {x['cong_thuc']} (nguồn: {x['nguon']})")
        if x["viec"]:
            d.append(f"  - cần làm: {x['viec']}")
    return "\n".join(d)
