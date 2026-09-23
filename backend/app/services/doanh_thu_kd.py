"""Doanh thu tính chỉ tiêu của khối Kinh doanh — ai bán được bao nhiêu, kỳ nào.

═══════════════════════════════════════════════════════════════════════════════════════════════
LUẬT TÍNH — ANH TUẤN CHỐT 19/9/2026
═══════════════════════════════════════════════════════════════════════════════════════════════
Hai câu hỏi được đặt ra và hai câu trả lời được chọn:

  "Doanh thu tính chỉ tiêu lấy theo cách nào?"  →  LẤY THẲNG GIÁ TRỊ BOOKING của người đó.
  "Kỳ tính theo mốc nào?"                       →  THÁNG CỦA NGÀY TOUR KẾT THÚC.
                                                   (khởi hành 28/9, kết thúc 3/10 → tính vào T10)

Phương án còn lại — chia số quyết toán của chuyến theo tỷ trọng booking — đã được đề xuất và anh
KHÔNG chọn. Ghi lại cả hai vế vì cái giá của lựa chọn này là thật và sẽ có người hỏi:

CON SỐ NÀY KHÔNG KHỚP MÀN HÌNH CHỦ TỊCH, VÀ KHÔNG BAO GIỜ KHỚP.
    Màn hình Chủ tịch đọc  : quyết toán chuyến (`tours.actual_revenue`), kỳ theo NGÀY ĐÓNG SỔ.
    Màn hình Kinh doanh đọc: giá trị booking  (`bookings.amount`),       kỳ theo NGÀY KẾT THÚC.
Đo trên dữ liệu thật ngày 19/9/2026, riêng phần chuyến đã đóng sổ: quyết toán 83,86 tỷ, tổng booking
78,51 tỷ — lệch 5,35 tỷ, và 90,9% số chuyến khớp tuyệt đối nên toàn bộ khoản lệch dồn vào khoảng 78
chuyến. Đó là chuyến mà quyết toán có khoản không nằm trong booking nào, hoặc booking bị thiếu.

Hệ quả bắt buộc, KHÔNG phải tuỳ chọn: hàm `thang()` luôn trả kèm `co_so` (nhãn cơ sở tính) và
`doi_chieu_quyet_toan` (số của cùng kỳ theo cách Chủ tịch đọc). Màn hình phải hiện cả hai. Hai bảng
nói hai số mà không ai ghi vì sao thì ba tháng nữa sẽ có người mang cả hai ra hỏi bên nào sai, và
lúc ấy không còn ai nhớ.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ SAI, ĐÃ CHẶN SẴN
═══════════════════════════════════════════════════════════════════════════════════════════════
MỘT — DỊCH VỤ LẺ BỊ GIẤU MẶC ĐỊNH. Cửa `/api/v1/tours` lọc bỏ `tour_type == "non_package"` khi không
ai bảo khác, nên visa và dịch vụ lẻ biến mất. Lần TC-71 em đã sót đúng chỗ này và báo nhầm số cho
anh Tuấn. Tệp này đọc THẲNG từ mô hình, không qua cửa ấy, nên không thừa hưởng bộ lọc nào.

HAI — BOOKING ĐÃ HUỶ. Đếm 19/9/2026: 8.123 trên 16.414 booking mang cờ `cancelled`. Huỷ thì
`amount` đã được đặt về 0 ở đường nạp Vietrip, nhưng KHÔNG phải mọi đường nạp đều làm thế. Lọc bằng
cờ, không tin vào số tiền.

BA — DÒNG CHƯA GÁN ĐƯỢC NGƯỜI BÁN. Lô kho cũ H1/2026 có 466 phiếu mà tệp gốc không ghi hoặc ghi tên
không khớp ai; chúng mang `counts_for_target = False` ngay từ lúc nạp. Những dòng ấy KHÔNG vào chỉ
tiêu của ai — cộng nhầm cho người khác tệ hơn là để trống — nhưng phải HIỆN RA ở `chua_gan_nguoi_ban`
chứ không lặng lẽ biến mất. Cùng luật với "38 chuyến chưa gán pháp nhân" của TC-71.

BỐN — NGƯỜI BÁN CHƯA CÓ ĐƠN VỊ. Cộng lên cấp team/phòng/chi nhánh thì phải biết người ấy thuộc đâu
VÀO CUỐI KỲ (xem `to_chuc_kd.don_vi_cua`). Ai chưa được Hành chính phân công thì tiền của họ vào
`chua_co_don_vi`, không bị nhét tạm vào một đơn vị nào cho đủ tổng.
"""
from calendar import monthrange
from datetime import date

from sqlalchemy import select

from app.models.core import Booking, Tour, User
from app.models.doi_tac_ban_hang import DoiTacBanHang
from app.models.to_chuc_kd import DonViKD
from app.services import nguoi_ban_hang as NB
from app.services import segments as SEG
from app.services import to_chuc_kd as TC

# BỐN NGĂN NGƯỜI BÁN — khai một chỗ ở `services/nguoi_ban_hang.py`, đây chỉ dùng lại.
#
# Trước 19/9/2026 tệp này giữ một bản chép danh sách bốn vai Kinh doanh. Anh Tuấn giao mở quyền bán
# cho người ngoài khối (hướng dẫn viên, điều hành), nên "ai được bán" thành dữ liệu chứ không còn là
# một tuple trong mã — và một bản chép ở đây là cầm chắc ngày hai nơi trả lời khác nhau.
NGAN = NB.NGAN

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# BA LUỒNG, KHÔNG PHẢI HAI — anh Tuấn 19/9/2026
# ═══════════════════════════════════════════════════════════════════════════════════════════════
# "doanh thu của màn hình chủ tịch gồm cả PKD Đoàn và PKDL, nên em viết cấu trúc và thuật toán sao
#  cho đi thành 2 luồng chính xác kết nối với màn hình chủ tịch và phòng điều hành"
#
# Anh nói hai luồng. Đọc lại `services/segments.py` — nơi VTOS đã chốt cách phân mảng từ 07/9/2026 —
# thì thực tế là BA, và luồng thứ ba không phải em thêm cho đủ:
#
#     le         tour bán lẻ  (le_noi_dia, le_nuoc_ngoai)
#     doan       tour đoàn    (doan_noi_dia, doan_nuoc_ngoai, hoặc mã bắt đầu bằng MICE)
#     dich_vu_le tour non_package — visa, dịch vụ rời
#
# `segments.mang_of()` trả về chuỗi RỖNG cho non_package, và ghi rõ lý do: "nó là loại hàng riêng,
# có màn hình riêng, và CẢ HAI PHÒNG đều có thể bán". Nhét nó vào Lẻ cho đủ hai luồng là gán doanh
# thu của phòng Đoàn sang phòng Lẻ — đo trên máy thật 19/9/2026 thì riêng lô kho cũ H1 đã có 466
# phiếu toàn DVL-VISA và DVL-OTHER, không phải con số bỏ qua được.
#
# ĐIỀU KIỆN TỒN TẠI CỦA CẢ CẤU TRÚC NÀY: ba luồng RỜI NHAU và cộng lại đúng bằng tổng. Không có
# dòng nào ở hai luồng, không có dòng nào rơi ra ngoài. `test_ba_luong_roi_nhau_va_cong_du` canh
# đúng điều đó — vì nếu nó sai thì màn hình Chủ tịch và hai màn hình phòng sẽ lệch nhau mà không ai
# tìm ra chỗ hụt.
#
# KHÔNG CHÉP LUẬT PHÂN MẢNG SANG ĐÂY. Gọi thẳng `SEG.mang_of()`. Quy tắc ấy là HỢP của hai điều kiện
# (loại chuyến HOẶC mã MICE) và `segments.py` còn có sẵn `lech_quy_tac()` chỉ ra chuyến nào hai quy
# tắc bất đồng. Giữ một bản chép ở đây là cầm chắc ngày hai nơi nói khác nhau.
LUONG = ("le", "doan", "dich_vu_le")


def luong_cua(t: Tour) -> str:
    """Luồng của một chuyến. Rỗng ở `segments` nghĩa là dịch vụ lẻ — ở đây gọi đúng tên nó."""
    return SEG.mang_of(t) or "dich_vu_le"


def _bien_ky(ky: str) -> tuple[date, date]:
    """'2026-09' → (1/9/2026, 30/9/2026). Ném ValueError nếu kỳ không đọc được."""
    try:
        nam, thang = ky.split("-")
        nam, thang = int(nam), int(thang)
        dau = date(nam, thang, 1)
    except (ValueError, AttributeError):
        raise ValueError(f"Kỳ không đọc được: {ky!r}. Dạng đúng là 2026-09.")
    return dau, date(nam, thang, monthrange(nam, thang)[1])


def ky_cua(t: Tour) -> str:
    """Kỳ của một chuyến = tháng NGÀY KẾT THÚC.

    KHÔNG có nhánh phòng thủ cho `end_date` rỗng, và đó là chủ ý: cột ấy NOT NULL ở cơ sở dữ liệu,
    nên nhánh ấy là mã chết — mã chết làm người đọc sau tưởng trường hợp đó có thật và viết thêm một
    tầng xử lý nữa quanh nó. Ràng buộc được canh bằng phép thử
    `test_ngay_ket_thuc_khong_duoc_rong`; nếu một ngày ai đó nới cột ấy ra, phép thử gãy và người
    nới phải quyết chuyến không có ngày kết thúc thì rơi vào kỳ nào.
    """
    return f"{t.end_date:%Y-%m}"


def dong_ban(db, ky: str) -> dict:
    """Mọi booking rơi vào kỳ này, đã gắn người bán và đơn vị của người ấy.

    Trả về BỐN NGĂN RỜI NHAU — cộng lại đúng bằng tổng, không dòng nào nằm ở hai ngăn:
        khoi_kd    : nhân viên khối Kinh doanh — ngăn DUY NHẤT vào chỉ tiêu
        ngoai_khoi : người bộ phận khác đã được bật quyền bán (HDV, Điều hành, Visa)
        doi_tac    : đối tác ngoài công ty (J Travel, JTV…)
        chua_ro    : chưa biết ai bán — kho cũ chưa gán được tên
    """
    dau, cuoi = _bien_ky(ky)

    # Chuyến kết thúc trong kỳ. Đọc thẳng mô hình: KHÔNG qua bộ lọc `non_package` của cửa /tours.
    chuyen = {t.id: t for t in db.execute(
        select(Tour).where(Tour.end_date >= dau, Tour.end_date <= cuoi)).scalars()}
    if not chuyen:
        return {k: [] for k in NGAN}

    nguoi = {u.id: u for u in db.execute(select(User)).scalars()}
    # Đơn vị xét tại NGÀY CUỐI KỲ: người chuyển team giữa tháng thì cả tháng ấy tính cho nơi họ
    # đang ở lúc chốt. Một luật, viết một chỗ; đổi thì đổi ở đây.
    don_vi_cache: dict[int, DonViKD | None] = {}

    def don_vi_cua(uid: int):
        """Đơn vị của người bán, xét tại NGÀY CUỐI KỲ.

        Thử cây Lẻ trước rồi cây Đoàn: một người thuộc đúng một cây, và dòng dịch vụ lẻ (không
        thuộc mảng nào) vẫn phải cộng lên đơn vị của người bán ra nó — cả hai phòng đều bán dịch
        vụ lẻ, nên buộc nó vào cây Lẻ là gán doanh thu của phòng Đoàn sang phòng Lẻ.
        """
        if uid not in don_vi_cache:
            dv = TC.don_vi_cua(db, uid, cuoi, "le") or TC.don_vi_cua(db, uid, cuoi, "doan")
            don_vi_cache[uid] = dv
        return don_vi_cache[uid]

    doi_tac = {d.id: d for d in db.execute(select(DoiTacBanHang)).scalars()}
    ra = {k: [] for k in NGAN}
    for b in db.execute(select(Booking).where(Booking.tour_id.in_(list(chuyen)))).scalars():
        if b.cancelled:
            continue
        t = chuyen[b.tour_id]
        u = nguoi.get(b.sales_id)
        dv = don_vi_cua(b.sales_id) if b.sales_id else None
        dong = {
            "booking_id": b.id, "ma": b.code, "khach": b.customer_name,
            "tour_id": t.id, "tour_ma": t.code, "tour_ten": t.name,
            "ket_thuc": t.end_date.isoformat(), "loai_tour": t.tour_type,
            "luong": luong_cua(t),
            "tien": float(b.amount or 0), "khach_so": b.pax,
            "user_id": b.sales_id, "nguoi_ban": u.full_name if u else "",
            "vai": u.role if u else "",
            # TC-77 – ba ô cho phép truy nguồn của Marketing. Để Ở ĐÂY chứ không truy vấn lại
            # bookings ở tệp kia: hai nơi cùng đọc một bảng là hai nơi có thể lọc khác nhau, và
            # ngày chúng lệch thì không ai biết bảng nào đúng.
            "nguon": b.source or "",
            "ma_chien_dich": b.campaign_code or "",
            "dien_thoai": b.customer_phone or "",
            "doi_tac_id": b.doi_tac_id,
            "doi_tac": doi_tac[b.doi_tac_id].ten if b.doi_tac_id in doi_tac else "",
            "don_vi_id": dv.id if dv else None,
            "don_vi": dv.ten if dv else "", "don_vi_ma": dv.ma if dv else "",
        }
        # Thứ tự xét CÓ Ý NGHĨA. Đối tác xét TRƯỚC: một booking do đối tác bán vẫn phải có một tài
        # khoản nhân viên đứng tên ở `sales_id` (cột ấy không cho rỗng), thường là người tiếp nhận.
        # Xét vai trước thì doanh thu đối tác chui vào chỉ tiêu của người tiếp nhận.
        if b.doi_tac_id:
            ra["doi_tac"].append(dong)
        elif not b.counts_for_target:
            # Cờ này do đường nạp kho cũ tắt khi tệp gốc không ghi tên người bán. "Chưa biết ai
            # bán" — khác hẳn "biết là đối tác".
            ra["chua_ro"].append(dong)
        else:
            ra[NB.ngan_cua_nguoi(u)].append(dong)
    return ra


def thang(db, ky: str, luong: str = "", pham_vi: list[int] | None = None) -> dict:
    """Tổng hợp một kỳ: theo người, theo đơn vị, theo luồng, kèm nhãn cơ sở và số đối chiếu.

    `luong` rỗng = CẢ BA luồng gộp lại — đây là con số đặt cạnh màn hình Chủ tịch. Truyền "le",
    "doan" hoặc "dich_vu_le" thì chỉ lấy luồng ấy, dùng cho màn hình từng phòng.

    `pham_vi` là danh sách id đơn vị người xem được nhìn (`to_chuc_kd.pham_vi_xem`). `None` nghĩa là
    xem tất cả. DANH SÁCH RỖNG KHÁC `None`: rỗng nghĩa là người này chưa được phân công đơn vị nào,
    nên không thấy dòng nào — đừng viết `if not pham_vi`.
    """
    if luong and luong not in LUONG:
        raise ValueError(f"Luồng không hợp lệ: {luong!r}. Chỉ có {', '.join(LUONG)}.")
    dau, cuoi = _bien_ky(ky)
    nhom = dong_ban(db, ky)

    def trong_pham_vi(d):
        if luong and d["luong"] != luong:
            return False
        if pham_vi is None:
            return True
        return d["don_vi_id"] is not None and d["don_vi_id"] in pham_vi

    tinh = [d for d in nhom["khoi_kd"] if trong_pham_vi(d)]

    theo_nguoi: dict[int, dict] = {}
    for d in tinh:
        o = theo_nguoi.setdefault(d["user_id"], {
            "user_id": d["user_id"], "nguoi_ban": d["nguoi_ban"], "vai": d["vai"],
            "don_vi_id": d["don_vi_id"], "don_vi": d["don_vi"], "don_vi_ma": d["don_vi_ma"],
            "tien": 0.0, "so_booking": 0, "so_khach": 0})
        o["tien"] += d["tien"]; o["so_booking"] += 1; o["so_khach"] += d["khach_so"] or 0

    # Cộng lên cấp: mỗi dòng cộng vào ĐÚNG đơn vị của người bán VÀ mọi đơn vị cha của nó. Cộng vào
    # cha là đúng — tổng phòng phải gồm các team — nhưng vì thế KHÔNG được cộng `theo_don_vi` lại
    # với nhau để ra tổng, sẽ trùng. Tổng đúng là `tong_tinh_chi_tieu` dưới đây.
    theo_don_vi: dict[int, dict] = {}
    for o in theo_nguoi.values():
        if o["don_vi_id"] is None:
            continue
        cur = db.get(DonViKD, o["don_vi_id"])
        while cur is not None:
            g = theo_don_vi.setdefault(cur.id, {
                "don_vi_id": cur.id, "ma": cur.ma, "ten": cur.ten, "cap": cur.cap,
                "tien": 0.0, "so_nguoi": 0})
            g["tien"] += o["tien"]; g["so_nguoi"] += 1
            cur = db.get(DonViKD, cur.cha_id) if cur.cha_id else None

    chua_don_vi = [o for o in theo_nguoi.values() if o["don_vi_id"] is None]

    def cong(ds):
        return float(sum(d["tien"] for d in ds))

    return {
        "ky": ky, "luong": luong or "tat_ca",
        "tu_ngay": dau.isoformat(), "den_ngay": cuoi.isoformat(),

        # BA LUỒNG, rời nhau và cộng đủ — xem khối luật ở đầu tệp. Đây là chỗ màn hình Chủ tịch
        # lấy số tổng, và hai màn hình phòng lấy phần của mình, mà không sợ lệch nhau.
        "theo_luong": {
            k: {"tien": float(sum(d["tien"] for d in tinh if d["luong"] == k)),
                "so_booking": sum(1 for d in tinh if d["luong"] == k)}
            for k in LUONG},

        # NHÃN CƠ SỞ — màn hình BẮT BUỘC hiện, xem khối luật ở đầu tệp.
        "co_so": "Giá trị booking chưa huỷ, kỳ tính theo tháng NGÀY TOUR KẾT THÚC. "
                 "Khác cơ sở của màn hình Chủ tịch (quyết toán chuyến, theo ngày đóng sổ), "
                 "nên hai con số không khớp nhau.",
        "doi_chieu_quyet_toan": _quyet_toan_dong_so(db, dau, cuoi),

        "tong_tinh_chi_tieu": cong(tinh),
        "theo_nguoi": sorted(theo_nguoi.values(), key=lambda x: -x["tien"]),
        "theo_don_vi": sorted(theo_don_vi.values(), key=lambda x: (x["cap"], -x["tien"])),

        # BỐN NGĂN NGƯỜI BÁN — rời nhau, cộng lại bằng toàn bộ doanh thu của kỳ. Chỉ ngăn đầu vào
        # chỉ tiêu; ba ngăn sau hiện ra chứ không giấu, vì mỗi ngăn trả lời một câu khác nhau.
        "theo_ngan": {k: {"so_booking": len(nhom[k]), "tien": cong(nhom[k])} for k in NGAN},
        "tong_moi_ngan": cong([d for k in NGAN for d in nhom[k]]),

        "chua_co_don_vi": {"so_nguoi": len(chua_don_vi), "tien": cong(chua_don_vi),
                           "rows": sorted(chua_don_vi, key=lambda x: -x["tien"])},
        "theo_doi_tac": _gom_doi_tac(nhom["doi_tac"]),
    }


def _gom_doi_tac(ds: list[dict]) -> list[dict]:
    """Doanh thu từng đối tác. Đây là câu hỏi "công ty bán qua đối tác bao nhiêu" — câu mà trước
    vòng này không trả lời được, vì đối tác nằm chung ngăn với "chưa biết ai bán"."""
    g: dict[int, dict] = {}
    for d in ds:
        o = g.setdefault(d["doi_tac_id"], {"doi_tac_id": d["doi_tac_id"], "ten": d["doi_tac"],
                                           "tien": 0.0, "so_booking": 0})
        o["tien"] += d["tien"]; o["so_booking"] += 1
    return sorted(g.values(), key=lambda x: -x["tien"])


def _quyet_toan_dong_so(db, dau: date, cuoi: date) -> dict:
    """Số của cùng kỳ theo cách màn hình Chủ tịch đọc — để đặt cạnh mà đối chiếu.

    Cố ý gọi lại `ket_qua_that.DA_DONG_SO` thay vì chép danh sách trạng thái: hai màn hình phải đổi
    cùng lúc, và cách chắc chắn nhất để chúng lệch nhau là mỗi bên giữ một bản chép.
    """
    from app.services.ket_qua_that import DA_DONG_SO
    from datetime import datetime, time
    t_dau, t_cuoi = datetime.combine(dau, time.min), datetime.combine(cuoi, time.max)
    ds = list(db.execute(select(Tour).where(Tour.status.in_(DA_DONG_SO),
                                            Tour.closed_at >= t_dau,
                                            Tour.closed_at <= t_cuoi)).scalars())
    return {"co_so": "Quyết toán chuyến đã đóng sổ, theo ngày đóng sổ",
            "so_chuyen": len(ds),
            "tien": float(sum(float(t.actual_revenue or 0) for t in ds))}


def cua_nguoi(db, user_id: int, ky: str, luong: str = "") -> dict:
    """Màn hình của một nhân viên: từng booking của chính họ trong kỳ, mọi luồng."""
    if luong and luong not in LUONG:
        raise ValueError(f"Luồng không hợp lệ: {luong!r}. Chỉ có {', '.join(LUONG)}.")
    nhom = dong_ban(db, ky)
    cua_toi = [d for d in nhom["khoi_kd"]
               if d["user_id"] == user_id and (not luong or d["luong"] == luong)]
    return {"ky": ky, "user_id": user_id, "luong": luong or "tat_ca",
            "theo_luong": {k: float(sum(d["tien"] for d in cua_toi if d["luong"] == k))
                           for k in LUONG},
            "tien": float(sum(d["tien"] for d in cua_toi)),
            "so_booking": len(cua_toi),
            "so_khach": sum(d["khach_so"] or 0 for d in cua_toi),
            "rows": sorted(cua_toi, key=lambda x: x["ket_thuc"])}
