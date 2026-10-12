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
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.services import access as AC

TOAN_CTY = "toan_cty"
TEN_KY = {"ngay": "ngày", "tuan": "tuần", "thang": "tháng"}

# Phòng ban có báo cáo riêng, và AI XEM ngoài Chủ tịch / TGĐ / Ban Kiểm soát.
# Cố ý viết thẳng từng vai trò chứ không suy từ bảng phòng ban: suy thì một vai trò mới thêm vào phòng
# sẽ tự có quyền xem bản tổng hợp của phòng đó mà không ai cân nhắc – nới quyền không ai quyết định.
PHONG = {
    "dieu_hanh": {"ten": "Điều hành", "xem": ("tp_dh", "ptgd_doan")},
    # HAI PHÒNG, HAI BẢNG – 28/9/2026. Trước hôm nay ở đây chỉ có MỘT dòng tên "Kinh doanh", và
    # bảng của nó đếm cả Lẻ lẫn Đoàn. Hai hậu quả ngược nhau từ cùng một dòng: Giám đốc Kinh doanh
    # mở bảng "phòng mình" ra thì thấy số của phòng Đoàn cộng vào, còn P.TGĐ tour đoàn thì không có
    # bảng nào để mở.
    #
    # `kd_doan` CHỈ có ptgd_doan xem – cùng nguyên tắc đã áp cho Visa ngày 10/9: người chịu trách
    # nhiệm về con số, không phải ai tò mò. Đây là một lần SIẾT với ba vai trò của phòng Lẻ: từ hôm
    # nay họ không còn thấy số của phòng Đoàn lẫn trong bảng mình nữa. Muốn mở lại thì thêm vai trò
    # vào đúng dòng dưới đây – một dòng, và có người quyết.
    "kd_le":     {"ten": "Kinh doanh Lẻ", "xem": ("gd_kd", "tp_kd", "ptgd_mkt")},
    "kd_doan":   {"ten": "Kinh doanh Đoàn", "xem": ("ptgd_doan",)},
    "doi_xe":    {"ten": "Đội xe", "xem": ("gd_doi_xe",)},
    "huong_dan": {"ten": "Hướng dẫn", "xem": ("tp_hd",)},
    "marketing": {"ten": "Marketing", "xem": ("ptgd_mkt",)},
    "ketoan":    {"ten": "Kế toán", "xem": ("ketoan",)},
    "hcns":      {"ten": "Hành chính & Nhân sự", "xem": ("hcns",)},
    # Bộ phận Visa THUỘC Phòng Điều hành (Chủ tịch chốt 10/9/2026), nên nó KHÔNG phải một phòng
    # ngang hàng: `thuoc` nói ra điều đó ngay trong bảng, và hai chỗ đọc bảng này xử theo.
    #
    # Bản 09/9 tạm để chuyên viên visa (nv_visa) xem báo cáo của chính ban mình. Nay bỏ dòng tạm ấy:
    # người chịu trách nhiệm về con số của Visa là Trưởng phòng Điều hành, không phải chuyên viên –
    # đúng nguyên tắc ở đầu tệp, "nhân viên trong phòng KHÔNG mặc định xem báo cáo phòng". Đây là một
    # lần SIẾT quyền, ghi rõ ra đây để lần sau ai đọc cũng thấy vì sao nó siết.
    "visa":      {"ten": "Bộ phận Visa", "xem": ("tp_dh", "ptgd_doan"), "thuoc": "dieu_hanh"},
}

# Bộ phận trực thuộc một phòng: {mã bộ phận: mã phòng mẹ}. Suy từ PHONG để không phải khai hai chỗ.
TRUC_THUOC = {ma: cfg["thuoc"] for ma, cfg in PHONG.items() if cfg.get("thuoc")}
PHONG_GOC = [ma for ma, cfg in PHONG.items() if not cfg.get("thuoc")]
XEM_TAT_CA = AC.FULL_VIEW + AC.READ_ALL          # Chủ tịch, TGĐ, Ban Kiểm soát, robot kiểm soát


# Năng lực cấp lẻ cho MỘT NGƯỜI, mở mọi báo cáo. Xem chú thích ở models/core.CAPABILITIES.
NANG_LUC_MOI_PHONG = "bao_cao_moi_phong"


def pham_vi_duoc_xem(vai_tro: str) -> list[str]:
    """Các phạm vi báo cáo một VAI TRÒ được mở. Rỗng = không xem báo cáo tự động nào.

    Hàm này chỉ xét vai trò. Ngoại lệ cấp cho từng người nằm ở `pham_vi_cho_nguoi` – tách hai hàm
    có chủ ý, để đọc mã còn thấy được "theo chức danh thì được những gì", tách khỏi "ai đang được
    cấp thêm". Gộp lại thì ba tháng nữa không ai trả lời được câu hỏi thứ nhất.
    """
    # Đợt LG1 — hàng rào này KHÔNG đi qua `require_roles`, nên nó phải tự đọc phép suy vai kế
    # thừa. Thiếu đoạn này thì Kế toán trưởng mở được `/bao-cao` mà không có báo cáo nào để xem:
    # bấm vào thấy trống và tưởng hệ thống hỏng. `test_bao_cao_phong` bắt đúng chỗ ấy 10/10.
    #
    # Hợp cả vai con lẫn vai cha, KHÔNG thay thế: một phạm vi cấp RIÊNG cho vai con vẫn còn.
    from app.services.vai_ke_thua import vai_va_cha
    vais = vai_va_cha(vai_tro)
    if any(v in XEM_TAT_CA for v in vais):
        return [TOAN_CTY] + list(PHONG)
    return [p for p, v in PHONG.items() if any(x in v["xem"] for x in vais)]


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


def _bo_phan_truc_thuoc(db: Session, phong: str, tu: date, den: date) -> list[dict]:
    """Gom các bộ phận TRỰC THUỘC một phòng vào chính báo cáo của phòng ấy.

    Chủ tịch chốt 10/9/2026: bộ phận Visa thuộc Phòng Điều hành, nên báo cáo Visa đẩy về Phòng Điều
    hành. Câu ấy có hai nửa, và nửa thứ hai mới là phần khó:

      · nửa dễ  – Trưởng phòng Điều hành MỞ được bảng của Visa (xử ở PHONG["visa"]["xem"]);
      · nửa khó – việc đỏ của Visa phải NỔI LÊN trong bảng của Phòng Điều hành. Không có nửa này thì
        báo cáo phòng vẫn im lặng trong khi bộ phận trực thuộc đang có việc phải xử, và người phụ
        trách chỉ biết nếu tự nhớ mà mở thêm một bảng nữa. Một con số phải đi tìm mới thấy thì coi
        như không có.

    Ở đây ĐỌC LẠI kết quả của bộ phận, không tính lại theo cách khác – cùng lý lẽ với báo cáo toàn
    công ty: tính lại là cách chắc chắn nhất để hai bảng lệch nhau, và lúc lệch thì không ai biết
    bảng nào đúng.
    """
    ds = []
    for ma, me in TRUC_THUOC.items():
        if me != phong:
            continue
        cfg = PHONG[ma]
        try:
            dong = HAM[ma](db, tu, den)
        except Exception as e:      # noqa – một bộ phận hỏng không được làm chết báo cáo của phòng
            ds.append(ct(f"bo_phan_{ma}", f"{cfg['ten']} – KHÔNG lấy được số", None, "",
                         "Chỉ tiêu của bộ phận trực thuộc lỗi khi tính", f"bao_cao_phong.{ma}",
                         muc="vang", chi_tiet=[f"{type(e).__name__}: {str(e)[:200]}"]))
            continue
        viec_do = [x for x in dong if x["muc"] == "do"]
        ds.append(ct(f"bo_phan_{ma}", f"{cfg['ten']} (trực thuộc) – việc phải xử lý",
                     len(viec_do), "việc",
                     "Đếm chỉ tiêu mức ĐỎ trong báo cáo của bộ phận trực thuộc. KHÔNG tính lại "
                     "theo cách khác – đọc lại đúng kết quả bảng của bộ phận",
                     f"báo cáo bộ phận {cfg['ten']}",
                     muc=_muc(len(viec_do) > 0, "do"),
                     viec="Mở bảng của bộ phận và xử từng việc đỏ" if viec_do else "",
                     chi_tiet=[f"{x['ten']}: {x['gia_tri']} {x['don_vi']}" for x in viec_do]))
    return ds


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
    from app.models.core import Booking
    qua_sla = [b for b in db.execute(select(Booking).where(Booking.sla_ok == False)).scalars()   # noqa: E712
               if b.created_at and tu <= b.created_at.date() <= den]
    sla_phut = float(R.get_param(db, "sla_booking_phut"))
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
        # CHUYỂN VỀ ĐÂY từ báo cáo bán hàng — Chủ tịch quyết 25/9/2026.
        #
        # Đồng hồ chạy từ lúc Kinh doanh gửi yêu cầu tới lúc Điều hành bấm tạo booking, và cảnh báo
        # quá hạn đã bắn về `tp_dh, nv_dh` từ đầu. Nhưng cột đếm thì nằm ở bảng điểm SALE, gom theo
        # tên sale — một con số người bán không làm gì để đổi được. Nay nó nằm đúng bảng của người
        # gây ra nó. Dữ liệu không đổi: vẫn là `bookings.sla_ok` đã ghi sẵn từ lúc tạo booking.
        ct("booking_qua_sla", "Booking quá hạn 2 giờ", len(qua_sla), "booking",
           f"Đếm booking tạo trong kỳ mà mất quá {sla_phut:.0f} phút kể từ lúc Kinh doanh gửi yêu cầu",
           "bookings.sla_ok = false (tham số sla_booking_phut, ĐH Điều 2)",
           muc=_muc(len(qua_sla) > 0),
           viec="Nhận yêu cầu thì tạo booking ngay. Chậm một giờ ở đây là một giờ khách chưa có "
                "chỗ chắc chắn, và người bán không làm gì để rút ngắn được",
           chi_tiet=[b.code for b in qua_sla[:20]]),
    ] + _bo_phan_truc_thuoc(db, "dieu_hanh", tu, den)


# ═══════════════════ KINH DOANH: LẺ VÀ ĐOÀN LÀ HAI BẢNG RỜI ═══════════════════
#
# HAI BỘ TỪ VỰNG, KHÔNG PHẢI MỘT — chỗ dễ sai nhất của cả phần này:
#   · mảng của TOUR : "le" / "doan"        – định nghĩa MỘT CHỖ, ở services/segments.py
#   · mã PHÒNG BAN  : "kd_le" / "kd_doan"  – models/hr.DEPARTMENTS, và cột `bao_gia.mang`
# Hai bộ trông na ná nhau nên rất dễ đem mã phòng đi so với mảng tour hoặc ngược lại. Lúc ấy bộ lọc
# KHÔNG báo lỗi: nó lặng lẽ trả về rỗng, và một bảng trống trông y hệt một phòng chưa làm gì.
# `MANG_CUA_PHONG` là chỗ DUY NHẤT dịch giữa hai bộ.
MANG_CUA_PHONG = {"kd_le": "le", "kd_doan": "doan"}


def _tour_khong_thuoc_mang_nao():
    """Điều kiện SQL: tour KHÔNG thuộc mảng nào – dịch vụ lẻ (non_package) và các loại khác.

    Dựng bằng chính hai điều kiện của `segments`, rồi phủ định hợp của chúng. KHÔNG chép tay danh
    sách loại chuyến vào đây: chép thì tới ngày segments đổi luật, ngăn "dùng chung" đứng yên với
    luật cũ, và một phần doanh thu biến mất khỏi cả hai bảng mà không ai thấy.
    """
    from app.services import segments as SEG
    return ~or_(SEG.tour_cond("le"), SEG.tour_cond("doan"))


def _kd(db: Session, tu: date, den: date, phong: str) -> list[dict]:
    """Bảng chỉ tiêu của MỘT phòng kinh doanh. `phong` là MÃ PHÒNG: "kd_le" hoặc "kd_doan".

    Trước 28/9/2026 hàm này là `_kd_le` và không lọc mảng ở dòng nào: nó đếm MỌI booking, MỌI báo
    giá, MỌI yêu cầu dịch vụ rồi treo tên "Kinh doanh" lên. Số trên bảng ấy sai với cả hai phòng.
    """
    from app.models.core import Booking, ServiceRequest, Tour
    from app.models.crm import Lead
    from app.models.ban_hang import BaoGia
    from app.services import segments as SEG

    mang = MANG_CUA_PHONG[phong]
    la_doan = mang == "doan"

    def _trong_ky(ds):
        return [x for x in ds if x.created_at and tu <= x.created_at.date() <= den]

    # Booking và yêu cầu dịch vụ lọc QUA TOUR, bằng đúng điều kiện của `segments`. Không viết lại
    # ở đây câu "thế nào là tour đoàn": viết lại là có ngày một tour nằm trên bảng phòng này trong
    # khi hoa hồng của nó tính theo bậc thang phòng kia – lệch tiền chứ không chỉ lệch màn hình.
    bk = _trong_ky(db.execute(select(Booking).join(Tour, Booking.tour_id == Tour.id)
                              .where(SEG.tour_cond(mang))).scalars())
    dt = sum((b.amount or 0) - (b.discount or 0) for b in bk)

    # Dịch vụ lẻ không thuộc mảng nào, và CẢ HAI phòng đều bán được. Nó đứng thành một dòng riêng,
    # giống hệt nhau ở hai bảng, thay vì bị nhét vào một phòng cho tròn tổng.
    chung = _trong_ky(db.execute(select(Booking).join(Tour, Booking.tour_id == Tour.id)
                                 .where(_tour_khong_thuoc_mang_nao())).scalars())
    dt_chung = sum((b.amount or 0) - (b.discount or 0) for b in chung)

    lead = [l for l in db.execute(select(Lead)).scalars() if tu <= l.received_at.date() <= den]

    # Báo giá lọc theo CỘT `mang` của chính nó (người soạn khai lúc tạo), không suy từ tour: một
    # báo giá có thể chưa gắn tour nào – `bao_gia.tour_id` cho phép rỗng.
    bg = db.execute(select(BaoGia).where(BaoGia.mang == phong)).scalars().all()
    gui = [b for b in bg if b.trang_thai == "da_gui"]
    chot = [b for b in bg if b.trang_thai == "khach_chot"]
    duoi = [b for b in bg if b.duoi_bien]
    cho = db.execute(select(func.count()).select_from(ServiceRequest)
                     .join(Tour, ServiceRequest.tour_id == Tour.id)
                     .where(ServiceRequest.booking_id == None,                        # noqa: E711
                            SEG.tour_cond(mang))).scalar()
    # Tỷ lệ chốt: mẫu số bằng 0 thì để RỖNG, không để 0%. "Chưa gửi báo giá nào" và "gửi mà không ai
    # chốt" là hai tình huống ngược nhau, hiện cùng một con số 0% là sai.
    mau = len(gui) + len(chot)
    ty_le = round(len(chot) / mau * 100, 1) if mau else None

    ds = [
        ct("booking", "Booking mới trong kỳ", len(bk), "booking",
           f"Đếm booking có ngày tạo trong kỳ, CHỈ chuyến thuộc mảng {SEG.MANG[mang]}",
           "bookings.created_at · services.segments.tour_cond"),
        ct("doanh_thu", "Doanh thu booking trong kỳ", dt, "đ",
           "Tổng (số tiền − giảm giá) của các booking tạo trong kỳ, chỉ chuyến thuộc mảng này",
           "bookings.amount − bookings.discount · services.segments.tour_cond"),
    ]

    if la_doan:
        # ĐOÀN ĐO LỢI NHUẬN, KHÔNG ĐO DOANH THU (cùng lý lẽ đã ghi ở doanh_thu_kd.py): tour đoàn
        # giá trị lớn mà biên mỏng, lấy doanh thu làm thước là dạy người bán hạ giá để chạy số.
        # Dòng doanh thu ở trên vẫn giữ để đối chiếu, nhưng thước của phòng này là dòng dưới đây.
        from app.services.ket_qua_that import DA_DONG_SO
        from app.services import rules as R
        dong_so = list(db.execute(select(Tour).where(
            Tour.status.in_(DA_DONG_SO), Tour.end_date >= tu, Tour.end_date <= den,
            SEG.tour_cond("doan"))).scalars())
        # RỖNG chứ không 0 khi chưa chuyến nào đóng sổ. `settlement_summary` đọc actual_revenue /
        # actual_cost, và hai ô ấy để trống thì nó trả lợi nhuận 0 – một con số 0 không phân biệt
        # được với "quyết toán xong, hoà vốn". Chặn ngay tại đây, đừng để nó lên màn hình.
        ln = float(sum(R.settlement_summary(db, t)["profit"] for t in dong_so)) if dong_so else None
        ds.append(ct("loi_nhuan_dong_so", "Lợi nhuận chuyến đã đóng sổ", ln, "đ",
                     "Cộng lợi nhuận quyết toán của các chuyến ĐOÀN kết thúc trong kỳ VÀ đã đóng "
                     "sổ. Chưa chuyến nào đóng sổ thì để RỖNG, không để 0 – 'chưa quyết toán' và "
                     "'quyết toán ra 0 đồng' là hai chuyện ngược nhau",
                     "tours.status (ket_qua_that.DA_DONG_SO) + rules.settlement_summary",
                     chi_tiet=[t.code for t in dong_so[:20]]))

    ds += [
        ct("dung_chung_dich_vu_le", "Dịch vụ lẻ – KHÔNG thuộc mảng nào", len(chung), "booking",
           "Booking của chuyến không thuộc mảng Lẻ cũng không thuộc mảng Đoàn (dịch vụ lẻ – "
           "non_package). CẢ HAI phòng đều bán được loại này, nên nó KHÔNG cộng vào hai dòng trên "
           "và hiện y hệt nhau ở hai bảng",
           "bookings · phủ định hợp hai điều kiện của services.segments",
           chi_tiet=[f"Số tiền: {dt_chung:,.0f} đ"] if chung else []),
        ct("lead", "Khách mới (lead) trong kỳ – DÙNG CHUNG", len(lead), "khách",
           "Đếm lead có ngày nhận trong kỳ. KHÔNG chia được theo mảng: bảng leads chưa có cột mảng "
           "và cũng chưa gắn tour, nên con số này GIỐNG NHAU ở hai bảng và không phải chỉ tiêu "
           "riêng của phòng nào. Muốn chia thì phải mở thêm một cửa nhập, không phải thêm một phép "
           "đoán", "leads.received_at"),
        ct("bao_gia_cho", "Báo giá đang chờ khách trả lời", len(gui), "báo giá",
           "Báo giá của mảng này ở trạng thái đã gửi",
           f"bao_gia.trang_thai='da_gui' + mang='{phong}'",
           muc=_muc(len(gui) > 0), viec="Gọi lại khách trước khi báo giá hết hạn hiệu lực"),
        ct("bao_gia_chot", "Báo giá khách đã chốt", len(chot), "báo giá",
           "Báo giá của mảng này ở trạng thái khách chốt",
           f"bao_gia.trang_thai='khach_chot' + mang='{phong}'"),
        ct("ty_le_chot", "Tỷ lệ chốt báo giá", ty_le, "%",
           "Khách chốt ÷ (đang chờ + khách chốt) × 100, tính trong mảng này. Chưa gửi báo giá nào "
           "thì để RỖNG, không để 0% – hai tình huống đó ngược nhau",
           f"bao_gia.trang_thai + mang='{phong}'"),
        ct("duoi_bien", "Báo giá từng gửi dưới ngưỡng biên", len(duoi), "báo giá",
           "Báo giá của mảng này có cờ dưới biên (gửi khi biên thấp hơn ngưỡng, kèm giải trình)",
           f"bao_gia.duoi_bien + mang='{phong}'", muc=_muc(len(duoi) > 0),
           viec="Đọc lại giải trình – mỗi bản dưới biên đều bắt buộc có"),
        ct("yeu_cau_cho", "Yêu cầu chưa tạo booking", cho, "yêu cầu",
           "Đếm yêu cầu dịch vụ chưa gắn booking, chỉ chuyến thuộc mảng này",
           "service_requests.booking_id rỗng · services.segments.tour_cond",
           muc=_muc(cho > 0)),
    ]

    # Hệ thống NÓI RA chỗ nó không chắc, thay vì im lặng chọn một bên. Mảng của một tour suy từ HỢP
    # của hai quy tắc (loại chuyến, và quy ước mã MICE), nên tour nào hai quy tắc bất đồng cũng rơi
    # về bảng phòng ĐOÀN – không tour nào bị đếm hai lần, nhưng cũng có nghĩa một chuyến mà phòng Lẻ
    # tưởng là của mình đang nằm ở bảng phòng Đoàn. Dòng này để cả hai phòng cùng thấy.
    lech = SEG.lech_quy_tac(db)
    ds.append(ct("lech_quy_tac_mang", "Tour hai quy tắc mảng nói khác nhau", lech["tong_lech"], "tour",
                 "Đếm tour mà LOẠI CHUYẾN và QUY ƯỚC MÃ MICE không khớp. Hệ thống lấy hợp hai quy "
                 "tắc nên mọi tour bất đồng đều tính về mảng Đoàn – không bỏ sót, nhưng cũng không "
                 "chắc đúng phòng", "services.segments.lech_quy_tac",
                 muc=_muc(lech["tong_lech"] > 0),
                 viec="Kinh doanh sửa DỮ LIỆU GỐC cho hai quy tắc khớp lại: đặt lại loại chuyến, "
                      "hoặc đặt lại mã tour. Hệ thống không tự đoán hộ",
                 chi_tiet=(lech["ma_MICE_nhung_loai_chuyen_ghi_le"]
                           + lech["loai_chuyen_doan_nhung_ma_khong_MICE"])[:20]))
    return ds


def _kd_le(db: Session, tu: date, den: date) -> list[dict]:
    return _kd(db, tu, den, "kd_le")


def _kd_doan(db: Session, tu: date, den: date) -> list[dict]:
    return _kd(db, tu, den, "kd_doan")


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
    moi = db.execute(select(VehicleDocument)
                     .where(VehicleDocument.expires_on != None,                  # noqa: E711
                            VehicleDocument.expires_on <= han)).scalars().all()
    # SM-1 (12/10/2026) — TÁCH SIM RA DÒNG RIÊNG, Chủ tịch chọn. Hai loại giấy này có HAI HẬU QUẢ
    # khác nhau: xe hết đăng kiểm hay hết bảo hiểm thì KHÔNG CHẠY ĐƯỢC; sim hết hạn thì xe vẫn
    # chạy, chỉ là cổng GPS tắt và km của chuyến mất nguồn để đối chiếu với km đồng hồ. Gộp vào
    # một con số thì người đọc không biết phải làm gì trước — và lời khuyên của dòng cũ ("xe hết
    # đăng kiểm là không chạy được") nói sai hẳn cho một nửa số đếm.
    sap_het = [x for x in moi if x.kind != "sim"]
    sim_het = [x for x in moi if x.kind == "sim"]
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
                "và lệnh điều xe đã lên rồi thì phải đổi xe gấp. Sim xe đếm riêng ở dòng dưới",
           chi_tiet=[f"{x.kind} {x.number} – hết hạn {x.expires_on}" for x in sap_het[:20]]),
        ct("sim_xe", "Sim xe hết hạn trong 30 ngày", len(sim_het), "sim",
           "Đếm sim của xe có ngày hết hạn gói cước trong vòng 30 ngày tới",
           "vehicle_documents.expires_on, kind='sim'", muc=_muc(len(sim_het) > 0),
           viec="Gia hạn gói cước. Sim hết hạn thì XE VẪN CHẠY nhưng cổng GPS tắt – km của chuyến "
                "mất nguồn để đối chiếu với km đồng hồ, và tháng sau không ai dựng lại được",
           chi_tiet=[f"{x.number} · {x.cong_gps or 'chưa rõ cổng'} – hết hạn {x.expires_on}"
                     for x in sim_het[:20]]),
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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CHĂM SÓC SAU TOUR — năm dòng giữ cho phép đo còn nghĩa (27/9/2026)
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Đề xuất tự động hoá CSKH 25/9 có bước 7: "báo cáo tự động hằng tuần gửi BLĐ". Anh Tuấn chốt
# 27/9: KHÔNG làm báo cáo gửi đi, vì báo cáo hằng ngày đã có sẵn ở chính tệp này — đúng quyết định
# của Chủ tịch 09/9 ghi ở đầu tệp: báo cáo HIỆN trên màn hình, không gửi mail hay Zalo.
#
# VÌ SAO NĂM DÒNG NÀY, KHÔNG PHẢI "ĐIỂM TRUNG BÌNH SAU TOUR"
#
# Đề xuất bỏ bộ phận chăm sóc riêng và giao việc gọi lại khách chấm thấp cho CHÍNH NGƯỜI ĐÃ BÁN
# tour ấy. Mục 6 của đề xuất tự nhận ra rủi ro: hai phòng ấy có thể ít báo lên hơn, vì chính họ
# bán và vận hành. Một bảng chỉ có điểm trung bình sẽ KHÔNG bao giờ lộ ra điều đó — điểm trung
# bình đẹp lên khi người không hài lòng thôi trả lời, và đó là hướng nó tự trôi tới.
#
# Nên bốn trong năm dòng dưới đây không đo mức hài lòng. Chúng đo phần CÓ THỂ TRÔI: bao nhiêu
# khách thật sự trả lời, bao nhiêu điểm là do nhân viên gõ hộ, bao nhiêu phiếu chấm thấp còn treo,
# và bao nhiêu chuyến không ai nói gì cả.
def _cskh_dong(db: Session, tu: date, den: date) -> list[dict]:
    from app.models.cskh import CareTicket, Complaint, KN_NHOM
    from app.models.crm import ZaloMessage
    from app.models.core import Tour
    try:
        from app.models.danh_gia import DanhGiaSauTour
    except ImportError:          # vòng đánh giá chưa có trên nhánh này
        return []

    # Lời mời ĐÃ GỬI THẬT. Tin còn nằm trong hàng đợi không phải lời mời — tính nó vào mẫu số là
    # tự hạ tỷ lệ trả lời vì một lỗi cấu hình, và khi ấy con số không nói được điều gì về khách.
    da_gui = db.execute(select(func.count()).select_from(ZaloMessage).where(
        ZaloMessage.purpose == "cham_soc", ZaloMessage.status == "da_gui",
        func.date(ZaloMessage.created_at) >= tu, func.date(ZaloMessage.created_at) <= den)).scalar() or 0
    khach_cham = db.execute(select(func.count(func.distinct(DanhGiaSauTour.care_id))).where(
        DanhGiaSauTour.nguon == "khach",
        func.date(DanhGiaSauTour.tao_luc) >= tu, func.date(DanhGiaSauTour.tao_luc) <= den)).scalar() or 0
    ghi_ho = db.execute(select(func.count(func.distinct(DanhGiaSauTour.care_id))).where(
        DanhGiaSauTour.nguon == "nhan_vien",
        func.date(DanhGiaSauTour.tao_luc) >= tu, func.date(DanhGiaSauTour.tao_luc) <= den)).scalar() or 0
    ty_le = round(khach_cham / da_gui, 3) if da_gui else None

    # Phiếu khách chấm thấp mà chưa đóng. `hai_long = 0` là CHƯA CHẤM, không phải chấm 0 điểm —
    # nên điều kiện là 1..3, không phải <= 3.
    thap_treo = db.execute(select(func.count()).select_from(CareTicket).where(
        CareTicket.hai_long >= 1, CareTicket.hai_long <= 3,
        CareTicket.status != "xong")).scalar() or 0

    # Chuyến kết thúc trong kỳ mà KHÔNG một khách nào chấm. Đây là chỗ mù của điểm trung bình.
    da_ket = [t for (t,) in db.execute(select(Tour.id).where(
        Tour.end_date >= tu, Tour.end_date <= den)).all()]
    co_cham = {x for (x,) in db.execute(select(func.distinct(DanhGiaSauTour.tour_id)).where(
        DanhGiaSauTour.tour_id.in_(da_ket))).all()} if da_ket else set()
    im_lang = len([t for t in da_ket if t not in co_cham])

    ket = db.execute(select(func.count()).select_from(ZaloMessage).where(
        ZaloMessage.status == "cho_cau_hinh")).scalar() or 0

    # ── CẤU HÌNH ZALO CHO LỜI MỜI CHẤM ĐIỂM — TC-96, 29/9/2026 ──────────────────────────────
    #
    # Tới hôm nay trạng thái này chỉ nằm trong BIẾN MÔI TRƯỜNG trên máy chủ. Không màn hình nào
    # cho thấy nó. Hệ quả đo được ngày 29/9: 401 tin nằm chờ mẫu ZNS suốt ba ngày, bảng chỉ báo
    # "kẹt chờ cấu hình" — nhưng không nói CẤU HÌNH NÀO, nên người đọc không biết phải làm gì,
    # và người làm xong cũng không có chỗ nào xác nhận là đã xong.
    #
    # Dòng này đếm SỐ MỤC ĐÍCH ĐÃ CÓ MẪU, không đếm tổng số mẫu: hệ thống cần đúng hai mẫu, mỗi
    # mẫu cho một mục đích, và khai mười mẫu cho cùng một mục đích thì vẫn thiếu.
    #
    # Đọc qua `zalo.configured` — CÙNG hàm mà đường gửi thật đọc. Tự đọc lấy biến môi trường ở
    # đây là dựng chỗ thứ hai trả lời cùng một câu, và ngày hai chỗ lệch nhau thì màn hình báo
    # "đã khai đủ" trong khi robot vẫn không gửi được.
    from app.services import zalo as Z
    try:
        cfg_zalo = Z.configured(db)
    except Exception as e:      # noqa – hỏng chỗ đọc cấu hình không được làm chết cả bảng
        cfg_zalo = {"oa": False, "zns_templates": {}, "loi": f"{type(e).__name__}: {str(e)[:80]}"}
    can_mau = ("cham_soc", "cham_soc_nhac")
    co_mau = [m for m in can_mau if (cfg_zalo.get("zns_templates") or {}).get(m)]
    thieu = [m for m in can_mau if m not in co_mau]
    chi_tiet_zalo = [("Tài khoản OA: đã nối" if cfg_zalo.get("oa") else
                      "Tài khoản OA: CHƯA nối — không đường nào gửi được")]
    chi_tiet_zalo += [f"Mẫu ZNS '{m}': đã khai" for m in co_mau]
    chi_tiet_zalo += [f"Mẫu ZNS '{m}': CHƯA khai" for m in thieu]
    if cfg_zalo.get("loi"):
        chi_tiet_zalo.append("Không đọc được cấu hình: " + cfg_zalo["loi"])

    # NGƯỜI XỬ LÝ TỰ ĐÓNG HỒ SƠ CỦA MÌNH — đo, không chặn (anh Tuấn chốt 27/9/2026).
    #
    # Khiếu nại sinh từ đánh giá ≤3 sao được giao cho SALE ĐÃ BÁN tour ấy. Người đó vừa là người bị
    # khách chấm thấp, vừa gọi lại, vừa gõ "khách đã chấp nhận phương án", vừa bấm đóng — bốn vai
    # trong một người. Không ai cần gian dối để con số sai; chỉ cần bận và muốn cho xong.
    #
    # `services/cskh.dong()` đã cấm điều này cho khiếu nại MỨC 3 ("không cho một người vừa xử lý
    # vừa đóng"). Mức 1–2 thì không cấm, và Chủ tịch chọn giữ nguyên như vậy: độc lập bằng TẦM
    # NHÌN, không bằng hàng rào — mọi số liệu chăm sóc lên thẳng Ban Giám đốc và Chủ tịch. Dòng này
    # là cái làm cho lựa chọn ấy có nghĩa: không cản ai, nhưng đếm được.
    dong_kn = db.execute(select(Complaint).where(
        Complaint.source == "cham_soc", Complaint.status == "da_dong",
        Complaint.closed_at.is_not(None),
        func.date(Complaint.closed_at) >= tu, func.date(Complaint.closed_at) <= den)).scalars().all()
    tu_dong = [c for c in dong_kn
               if c.handler and c.handler in [x for x in (c.closed_by or "").split(",") if x]]

    # ── SỔ KHIẾU NẠI VÀO BÁO CÁO PHÒNG — KN-2, 09/10/2026 ──────────────────────────────────
    #
    # Tới hôm nay bảng của phòng CSKH chỉ nói về CHĂM SÓC SAU BÁN: lời mời chấm điểm, phiếu chấm
    # thấp, chuyến không ai chấm, tin Zalo kẹt. Sổ khiếu nại thì có màn hình riêng và có bảng số
    # riêng trên ấy, nhưng KHÔNG một con số nào của nó đi vào báo cáo phòng — nên người đọc báo
    # cáo (trưởng bộ phận, Ban TGĐ, Chủ tịch) không thấy tháng này khách kêu bao nhiêu lần trừ
    # khi tự mở thêm một màn hình nữa. Một con số phải đi tìm mới thấy thì phần lớn thời gian
    # không ai thấy.
    #
    # DÙNG LẠI ĐÚNG MỘT ĐỊNH NGHĨA 'QUÁ HẠN' của `services/cskh` (vòng KN-1 cùng ngày đã gom hai
    # bản SQL / Python về một chỗ). Viết lại mệnh đề ấy ở đây là dựng cái đầu THỨ BA, và ba đầu
    # thì chắc chắn có hai cái lệch — lúc ấy màn hình Khiếu nại nói 7, báo cáo phòng nói 6, không
    # ai biết bên nào đúng. Phép thử `test_kn2` cấm tệp này tự viết lại mệnh đề.
    from app.services import cskh as CS

    trong_ky = db.execute(select(Complaint).where(
        func.date(Complaint.received_at) >= tu,
        func.date(Complaint.received_at) <= den)).scalars().all()
    muc3 = [c for c in trong_ky if c.level == 3]
    tai_mo = [c for c in trong_ky if (c.reopen_reason or "").strip()]
    # Trễ hạn tính trên những hồ sơ ĐÃ phản hồi. Hồ sơ chưa phản hồi chưa biết sớm hay muộn, và
    # nhét nó vào mẫu số là tự bôi đen một kỳ chỉ vì kỳ ấy còn việc đang chạy.
    da_phan_hoi = [c for c in trong_ky if c.first_response_at and c.han_phan_hoi]
    tre = [c for c in da_phan_hoi if c.first_response_at > c.han_phan_hoi]

    # TỒN ĐỌNG, không cắt theo kỳ — cùng lý do với dòng tin Zalo kẹt ở dưới: một hồ sơ quá hạn
    # từ tháng trước vẫn đang quá hạn hôm nay, và cắt nó ra khỏi kỳ là giấu đúng cái cần thấy.
    kn_qua_han = db.execute(select(Complaint).where(CS.dieu_kien_qua_han())).scalars().all()

    theo_nhom = {}
    for c in trong_ky:
        theo_nhom[c.nhom] = theo_nhom.get(c.nhom, 0) + 1
    xep_nhom = sorted(theo_nhom.items(), key=lambda x: (-x[1], x[0]))

    return [
        ct("cs_ty_le_tra_loi", "Khách trả lời khảo sát sau tour", ty_le, "tỷ lệ",
           "Số phiếu KHÁCH TỰ CHẤM ÷ số lời mời ĐÃ GỬI THẬT trong kỳ. Tin còn nằm trong hàng đợi "
           "không tính vào mẫu số. Rỗng khi chưa gửi lời mời nào",
           "danh_gia_sau_tour.nguon='khach' + zalo_messages.status='da_gui'",
           muc=_muc(ty_le is not None and ty_le < 0.5),
           viec="Dưới 50% thì mốc nghiệm thu 31/10 của đề xuất CSKH chưa đạt – xem lại giờ gửi và "
                "nội dung tin trước khi kết luận về khách"),
        ct("cs_ghi_ho", "Đánh giá do nhân viên ghi hộ", ghi_ho, "phiếu",
           "Đếm phiếu có điểm nhập bởi nhân viên, tách khỏi phần khách tự chấm",
           "danh_gia_sau_tour.nguon='nhan_vien'",
           muc=_muc(ghi_ho > khach_cham, "do"),
           viec="Ghi hộ nhiều hơn khách tự chấm nghĩa là điểm đang do người bị đo nhập vào – "
                "phần ấy không dùng để đánh giá ai được"),
        ct("cs_thap_treo", "Phiếu khách chấm 1–3 sao chưa đóng", thap_treo, "phiếu",
           "Đếm phiếu chăm sóc có điểm 1..3 và chưa ở trạng thái xong. Điểm 0 là CHƯA CHẤM, không "
           "tính", "care_tickets.hai_long 1..3 và status != xong",
           muc=_muc(thap_treo > 0), viec="Gọi khách trong 24 giờ theo đề xuất CSKH 25/9"),
        ct("cs_im_lang", "Chuyến kết thúc không ai chấm điểm", im_lang, "chuyến",
           "Đếm chuyến có ngày kết thúc trong kỳ mà không có dòng đánh giá nào",
           "tours.end_date + danh_gia_sau_tour.tour_id",
           muc=_muc(im_lang > 0),
           viec="Điểm trung bình đẹp vì chỉ người hài lòng trả lời là cách một bảng số nói dối mà "
                "không sai dòng nào – xem các chuyến này trước khi đọc điểm"),
        ct("cs_zalo_cau_hinh", "Mẫu ZNS đã khai cho lời mời chấm điểm", len(co_mau), "trên 2 mẫu",
           "Đếm số MỤC ĐÍCH đã có mã mẫu ZNS (cham_soc, cham_soc_nhac), đọc qua chính hàm cấu "
           "hình mà đường gửi thật dùng. Cần đủ 2; thiếu mẫu nào thì khách của mục đích ấy không "
           "nhận được gì, trừ người đã quan tâm OA",
           "biến môi trường ZALO_ZNS_TEMPLATES trên máy chủ + services.zalo.configured",
           muc=_muc(len(thieu) > 0, "do"),
           viec="Đăng ký mẫu tại zalo.cloud rồi dán mã vào biến ZALO_ZNS_TEMPLATES trên máy chủ. "
                "Zalo duyệt 1–2 ngày làm việc; duyệt xong mà chưa dán mã thì với VTOS không có gì "
                "thay đổi" if thieu else "",
           chi_tiet=chi_tiet_zalo),
        ct("cs_zalo_ket", "Tin Zalo đang kẹt chờ cấu hình", ket, "tin",
           "Đếm toàn bộ tin ở trạng thái chờ cấu hình, không giới hạn theo kỳ vì đây là tồn đọng",
           "zalo_messages.status='cho_cau_hinh'",
           muc=_muc(ket > 0, "do"),
           viec="Khai địa chỉ webhook OA và đăng ký mẫu ZNS; khách không nhận được gì cho tới lúc đó"),
        ct("cs_tu_dong", "Phiếu chấm thấp do chính người xử lý đóng", len(tu_dong), "hồ sơ",
           "Đếm khiếu nại nguồn 'phiếu chăm sóc' đã đóng trong kỳ mà tên người xử lý nằm trong "
           "danh sách người ký đóng. KHÔNG chặn — mức 3 đã cấm sẵn ở cskh.dong(), mức 1–2 cố ý để "
           "mở và đo",
           "complaints.handler nằm trong complaints.closed_by",
           muc=_muc(len(tu_dong) > 0),
           viec="Người bị khách chấm thấp cũng là người bấm đóng hồ sơ ấy – đọc lại vài hồ sơ "
                "trong danh sách trước khi tin vào điểm trung bình của kỳ",
           chi_tiet=[f"{c.code} · {c.customer_name} · người xử lý {c.handler}" for c in tu_dong[:12]]),

        # ── Sổ khiếu nại (KN-2, 09/10/2026) ──
        ct("kn_moi", "Hồ sơ khiếu nại nhận trong kỳ", len(trong_ky), "hồ sơ",
           "Đếm hồ sơ có NGÀY NHẬN nằm trong kỳ. Mốc là lúc VTOS nhận, không phải lúc đóng: hồ "
           "sơ nhận tháng này đóng tháng sau vẫn là tiếng kêu của tháng này",
           "complaints.received_at",
           chi_tiet=[f"{c.code} · mức {c.level} · {c.customer_name}" for c in trong_ky[:12]]),
        ct("kn_qua_han", "Khiếu nại quá hạn chưa phản hồi", len(kn_qua_han), "hồ sơ",
           "Hồ sơ còn mở, chưa có lần phản hồi đầu tiên, và đã qua hạn phản hồi theo mức độ. "
           "KHÔNG giới hạn theo kỳ vì đây là tồn đọng — hồ sơ quá hạn từ tháng trước vẫn đang "
           "quá hạn hôm nay. Dùng chung đúng một mệnh đề với màn hình Khiếu nại",
           "services/cskh.dieu_kien_qua_han()",
           muc=_muc(len(kn_qua_han) > 0, "do"),
           viec="Khách đã chờ quá hạn đã hứa mà chưa ai trả lời — gọi trước, xử lý sau",
           chi_tiet=[f"{c.code} · mức {c.level} · hạn {c.han_phan_hoi:%d/%m %H:%M} · {c.customer_name}"
                     for c in kn_qua_han[:12]]),
        ct("kn_muc3", "Khiếu nại mức 3 nhận trong kỳ", len(muc3), "hồ sơ",
           "Mức 3 là mức nặng nhất, đóng được phải có hai chữ ký và người xử lý không tự đóng",
           "complaints.level=3 trong kỳ",
           muc=_muc(len(muc3) > 0),
           viec="Mỗi hồ sơ mức 3 là một lần khách mất lòng tin — đọc nguyên văn, đừng đọc con số",
           chi_tiet=[f"{c.code} · {c.customer_name} · {c.noi_dung[:70]}" for c in muc3[:12]]),
        ct("kn_tre_phan_hoi", "Phản hồi khách TRỄ hạn", (len(tre) if da_phan_hoi else None), "hồ sơ",
           "Trong số hồ sơ nhận trong kỳ ĐÃ phản hồi, đếm cái có lần phản hồi đầu muộn hơn hạn. "
           "Chưa hồ sơ nào phản hồi thì để RỖNG chứ không ghi 0 — chưa đo được khác với đo ra "
           "không có",
           "complaints.first_response_at > complaints.han_phan_hoi",
           muc=_muc(bool(tre)),
           viec="Hạn phản hồi là lời hứa với khách; trễ đều đặn thì hoặc thiếu người, hoặc hạn "
                "đặt sai — cả hai đều sửa được, nhưng phải chọn một",
           chi_tiet=[f"{c.code} · hẹn {c.han_phan_hoi:%d/%m %H:%M} · trả lời {c.first_response_at:%d/%m %H:%M}"
                     for c in tre[:12]]),
        ct("kn_tai_mo", "Hồ sơ trong kỳ đã từng bị tái mở", len(tai_mo), "hồ sơ",
           "Hồ sơ nhận trong kỳ mà có ghi lý do tái mở. Tái mở nghĩa là lần đóng trước đóng hụt",
           "complaints.reopen_reason khác rỗng",
           muc=_muc(len(tai_mo) > 0),
           viec="Đọc lý do tái mở: đóng hụt vì chưa hỏi khách, hay vì phương án không chạy được",
           chi_tiet=[f"{c.code} · {c.reopen_reason[:80]}" for c in tai_mo[:12]]),
        ct("kn_nhom_dau", "Nhóm vấn đề bị kêu nhiều nhất trong kỳ",
           (xep_nhom[0][1] if xep_nhom else None), "hồ sơ",
           "Gom hồ sơ nhận trong kỳ theo nhóm vấn đề, lấy nhóm đông nhất. Con số là số hồ sơ của "
           "nhóm ấy; tên nhóm và cả bảng xếp nằm ở phần chi tiết — một con số không nói được nhóm "
           "nào thì không dùng được",
           "complaints.nhom trong kỳ",
           viec="Nhóm đứng đầu lặp lại ba kỳ liền là một việc phải sửa ở quy trình, không phải "
                "một chuỗi sự cố rời",
           chi_tiet=[f"{KN_NHOM.get(k, k)}: {n}" for k, n in xep_nhom[:8]]),
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
    ] + _cskh_dong(db, tu, den)


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

    # TC-39 · HAI CHỈ TIÊU "SỐ TẠI MỘT THỜI ĐIỂM", thêm vào để bản lưu có cái mà chụp.
    # ═════════════════════════════════════════════════════════════════════════════════════════
    # Chúng KHÁC HẲN mọi chỉ tiêu khác trong bản báo cáo này: những chỉ tiêu kia đo việc xảy ra
    # TRONG KỲ [tu, den] và hôm nay cộng lại vẫn ra đúng con số ấy. Hai cái này đo trạng thái TẠI
    # LÚC ĐỌC, và `Tour.status` không giữ lịch sử — nên "cuối tháng 8 có bao nhiêu tour đang bán"
    # là câu hỏi mà sang tháng 10 không ai trả lời được nữa, kể cả với toàn bộ cơ sở dữ liệu.
    #
    # Đó chính là lý do chúng phải nằm trong bản lưu: bản lưu là chỗ DUY NHẤT giữ được câu trả
    # lời ấy, và mỗi kỳ không chụp là một câu hỏi vĩnh viễn không có đáp án.
    #
    # Câu "tại thời điểm chụp" viết thẳng vào phần CÔNG THỨC, không để trong chú thích mã: ba
    # tháng nữa người đọc bản lưu chỉ thấy JSON, không thấy tệp này.
    from app.services import dem_tour as DT
    _dem = DT.theo_trang_thai(db)
    ds += [
        ct("tour_dang_ban", "Tour đang bán", DT.dang_ban(db, _dem), "tour",
           "Đếm tour ở trạng thái đã duyệt TẠI THỜI ĐIỂM CHỤP — không phải trong kỳ. Số này "
           "không tính lại được cho kỳ đã qua.", "tours.status"),
        ct("tour_cho_quyet_toan", "Tour chờ quyết toán", DT.cho_quyet_toan(db, _dem), "tour",
           "Đếm tour đã kết thúc hoặc đã đóng sổ mà chưa xác nhận, TẠI THỜI ĐIỂM CHỤP — không "
           "phải trong kỳ. Số này không tính lại được cho kỳ đã qua.", "tours.status"),
    ]

    # Gom việc đỏ của từng phòng. Đây là chỗ báo cáo toàn công ty KHÔNG tự tính lại con số nào: nó
    # đọc lại đúng kết quả của báo cáo phòng. Tính lại theo cách khác là cách chắc chắn để hai bản
    # lệch nhau, và lúc lệch thì không ai biết bản nào đúng.
    # Chỉ duyệt PHÒNG GỐC. Bộ phận trực thuộc (Visa) đã được gom vào bảng của phòng mẹ rồi – đếm
    # thêm ở đây là đếm hai lần đúng một việc, và con số "toàn công ty có mấy việc đỏ" sẽ phồng lên
    # mà không ai giải thích được vì sao.
    for ma in PHONG_GOC:
        cfg = PHONG[ma]
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
    # Chăm sóc sau tour lên CẢ bảng toàn công ty, dùng CHUNG một hàm với bảng Marketing. Chép
    # công thức ra lần thứ hai là mở đường cho hai bảng nói hai con số khác nhau về cùng một
    # việc — và khi ấy người đọc chọn con số hợp ý mình.
    ds += _cskh_dong(db, tu, den)
    return ds


HAM = {"dieu_hanh": _dieu_hanh, "kd_le": _kd_le, "kd_doan": _kd_doan, "doi_xe": _doi_xe,
       "huong_dan": _huong_dan, "marketing": _marketing, "ketoan": _ketoan, "hcns": _hcns,
       "visa": _visa}


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


# ═══════════════════════════ BẢN LƯU THEO LỊCH ═══════════════════════════
def luu(db: Session, kind: str, moc: date | None = None, boi: str = "lich") -> dict:
    """Chụp lại TẤT CẢ phạm vi của một kỳ vào bảng `bao_cao_luu`.

    Điều quan trọng nhất của hàm này nằm ở chỗ nó KHÔNG tính gì: nó gọi đúng `bao_cao()` mà màn hình
    gọi. Trước 10/9/2026 lịch chạy lưu bản của robot R7 – một bài viết dựng từ phép tính riêng – nên
    số trên màn hình và số trong bản lưu là hai phép tính khác nhau cho cùng một câu hỏi. Hai phép
    tính như thế sớm muộn ra hai con số, và lúc lệch thì không ai biết bản nào đúng.

    Chạy lại cùng một kỳ thì ĐÈ lên bản cũ, nhờ khoá (kind, ky, pham_vi). Đây cũng là cái làm việc
    CHẠY BÙ an toàn: lịch lỡ một hôm, hôm sau chạy bù, và kết quả là một bản đúng chứ không phải hai
    bản chờ người ta chọn.

    Một phạm vi hỏng KHÔNG được làm chết cả mẻ – lưu được phạm vi nào thì lưu, và trả về danh sách
    phạm vi hỏng để người đọc nhật ký biết chỗ nào còn thiếu. Dừng cả mẻ vì một phòng lỗi là mất
    luôn bản lưu của những phòng đang ổn, và bản lưu thì không tính lại được về sau.
    """
    from app.models.bao_cao_luu import BaoCaoLuu
    from sqlalchemy import select as _sel

    xong, hong = [], []
    for pv in [TOAN_CTY] + list(PHONG):
        try:
            b = bao_cao(db, kind, pv, moc)
        except Exception as e:      # noqa
            hong.append(f"{pv}: {type(e).__name__}: {str(e)[:120]}")
            continue
        r = db.execute(_sel(BaoCaoLuu).where(BaoCaoLuu.kind == kind, BaoCaoLuu.ky == b["ky"],
                                             BaoCaoLuu.pham_vi == pv)).scalars().first()
        if r is None:
            r = BaoCaoLuu(kind=kind, ky=b["ky"], pham_vi=pv)
            db.add(r)
        r.pham_vi_ten, r.tu, r.den = b["pham_vi_ten"], b["tu"], b["den"]
        r.chi_tieu, r.markdown = b["chi_tieu"], sang_markdown(b)
        r.so_viec_do, r.so_can_ra_soat = b["so_viec_do"], b["so_can_ra_soat"]
        r.so_chua_co_so = b["so_chua_co_so"]
        r.tao_boi, r.tao_luc = boi, datetime.now()
        xong.append(pv)
    db.commit()
    return {"kind": kind, "ky": khoang(kind, moc)[2], "da_luu": xong, "hong": hong}


def ban_luu(db: Session, kind: str, ky: str, pham_vi: str):
    """Đọc lại một bản lưu. Không có thì trả None – KHÔNG dựng tạm một bản mới.

    Dựng tạm là cách bản lưu mất hết ý nghĩa: người ta hỏi 'cuối tháng trước thế nào' và nhận về số
    của hôm nay mà không hề biết.
    """
    from app.models.bao_cao_luu import BaoCaoLuu
    from sqlalchemy import select as _sel
    return db.execute(_sel(BaoCaoLuu).where(BaoCaoLuu.kind == kind, BaoCaoLuu.ky == ky,
                                            BaoCaoLuu.pham_vi == pham_vi)).scalars().first()
