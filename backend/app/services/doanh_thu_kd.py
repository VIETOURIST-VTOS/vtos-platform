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
LUONG = ("le", "doan", "dich_vu_le", "thue_xe")


def luong_cua(t: Tour) -> str:
    """Luồng của một chuyến.

    07/10/2026 — THÊM LUỒNG THỨ TƯ. Dòng cũ viết `SEG.mang_of(t) or "dich_vu_le"`: rỗng ở
    `segments` thì gọi là dịch vụ lẻ. Câu ấy đúng khi chỉ có một loại chuyến đứng ngoài hai mảng.
    Hợp đồng thuê xe cũng đứng ngoài hai mảng, nên với dòng cũ nó sẽ được GỌI LÀ DỊCH VỤ LẺ và
    cộng vào đúng ngăn ấy — một lời nói sai, không phải một phép tính sai, và vì thế khó thấy hơn.

    Nay tra bằng bảng: rỗng ở `segments` thì hỏi loại chuyến. Loại nào chưa ai xếp vẫn rơi về
    "dich_vu_le" như cũ, nhưng `test_tx4` canh để chuyện ấy không xảy ra lặng lẽ.
    """
    return SEG.mang_of(t) or {"thue_xe": "thue_xe"}.get(t.tour_type, "dich_vu_le")


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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BIỂU ĐỒ PHẤN ĐẤU CỦA MỘT NHÂN VIÊN — TC-91, Chủ tịch chốt 28/9/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# "để cho nv thấy được động lực phấn đấu hằng ngày theo biểu đồ doanh thu của mình".
#
# ĐƯỜNG NHỊP LÀ THỨ LÀM CHO NÓ HẰNG NGÀY. Một vạch đích không đổi hành vi hằng ngày: "đã bán 180
# triệu / đích 500 triệu" đọc ngày 5 và ngày 25 giống hệt nhau. Nhịp ngày thứ n = đích × n ÷ số
# ngày trong kỳ, nên mỗi sáng người mở lên biết mình đang TRÊN hay DƯỚI — đó mới là tín hiệu để
# hành động hôm nay.
#
# ĐÍCH KHÁC MỐC TÍNH TIỀN. Đọc `dich_dt_nv_le_*` / `dich_ln_nv_doan`, KHÔNG đọc `moc_chi_tieu_*`.
# Hai bộ chênh nhau 2,5 lần; xem lời khai dài ở `rules.py` cạnh chính hai khóa ấy.
#
# LẺ ĐO DOANH THU, ĐOÀN ĐO LỢI NHUẬN. Tour đoàn giá trị lớn mà biên mỏng: đo doanh thu là dạy
# người bán hạ giá để chạy số.
#
# CƠ SỞ NGÀY LÀ NGÀY TOUR KẾT THÚC, đúng bằng cơ sở tính chỉ tiêu (`ky_cua`). Vẽ theo ngày bán thì
# biểu đồ đẹp hơn nhưng cuối tháng nó không khớp con số chấm chỉ tiêu, và hai số đá nhau trên cùng
# một màn hình thì người xem tin số nào cũng sai.
def ln_doan_cua_ky(db, user_id: int, ky: str) -> float:
    """Lợi nhuận đoàn QUYẾT TOÁN thuộc về một người trong một kỳ.

    Dùng đúng `hr.month_tours` + `rules.settlement_summary` + `rules.ln_doan_cua_booking` mà bảng
    lương đang dùng — cùng nguồn, cùng luật chia. Nếu viết một đường lấy số riêng cho biểu đồ thì
    nhân viên sẽ thấy một con số ở màn hình và một con số khác trên phiếu lương, và không ai nói
    được bên nào đúng.
    """
    from app.services import rules as R
    from app.services.hr import month_tours

    nam, thg = _bien_ky(ky)[0].year, _bien_ky(ky)[0].month
    tot = 0.0
    for t in month_tours(db, nam, thg):
        if not R.is_doan(t):
            continue
        sm = R.settlement_summary(db, t)
        tot += sum(R.ln_doan_cua_booking(sm["profit"], sm["revenue"] or 0, b.amount or 0)
                   for b in t.bookings if b.sales_id == user_id)
    return tot


def _ba_ky_gan_nhat(ky: str) -> list[str]:
    """Kỳ này và hai kỳ liền trước, thứ tự từ xa tới gần — đúng cửa sổ Điều 5 Phòng Đoàn."""
    dau = _bien_ky(ky)[0]
    ra = []
    for k in range(2, -1, -1):
        mm, yy = dau.month - k, dau.year
        while mm <= 0:
            mm += 12
            yy -= 1
        ra.append(f"{yy:04d}-{mm:02d}")
    return ra


def thang_nac(db, mang: str, dich: float | None) -> list[dict]:
    """Các NẤC để nhân viên leo, đọc thẳng từ bảng chính sách — không chép bảng vào đây.

    Chủ tịch 28/9/2026: "chia ra nhiều mức, không nên giới hạn". Thang đã có sẵn và đã ký:

      · Lẻ  – `thang_f_bang`, 20 nấc theo % mốc doanh thu; hoa hồng = hệ số × (doanh thu − MỐC),
              chỉ phần VƯỢT mốc mới được hưởng.
      · Đoàn – `hr.DOAN_F` (Phụ lục A), 11 nấc theo % chỉ tiêu `moc_luong_doan`, quyết định % LƯƠNG
              CƠ BẢN chứ không phải hoa hồng. Hoa hồng đoàn là tuyến tính 10% phần vượt
              `hh_doan_moc` — Điều 7 CỐ Ý bỏ bậc nhảy ("không có bậc nào bị cắt"), nên ở đây nấc
              chỉ để NHÌN, tiền vẫn tính tuyến tính.

    `dich` chỉ dùng để đánh DẤU một nấc là mức công ty kỳ vọng. Nó không cắt thang: trên nó vẫn còn
    nấc, và đó là chủ ý — một vạch đích là một cái trần.
    """
    from app.services import hr as HR
    from app.services import rules as R

    ra = []
    if mang == "doan":
        moc = R.get_param(db, "moc_luong_doan")
        moc_hh = R.get_param(db, "hh_doan_moc")
        ty_le_hh = R.get_param(db, "hh_doan_ty_le")
        for i, (nguong, he_so) in enumerate(sorted(HR.DOAN_F)):
            tien = moc * nguong
            ra.append({"bac": "Đạt" if he_so >= 1 else f"f{i}", "pct_moc": round(nguong * 100),
                       "nguong": round(tien), "he_so": he_so,
                       "y_nghia": "phần trăm lương cơ bản",
                       "hoa_hong_uoc": round(max(0.0, tien - moc_hh) * ty_le_hh),
                       "la_dich": dich is not None and abs(tien - dich) < 1})
    else:
        bang = HR.parse_f_table(R.get_param_text(db, "thang_f_bang"))
        moc = dich_moc_le(db)
        for i, (nguong, he_so) in enumerate(bang):
            tien = moc * nguong
            ra.append({"bac": f"f{i + 1}", "pct_moc": round(nguong * 100),
                       "nguong": round(tien), "he_so": he_so,
                       "y_nghia": "hệ số hoa hồng trên phần vượt mốc",
                       # HOA HỒNG = hệ số × (doanh thu − MỐC), không phải × doanh thu. Chép nhầm
                       # chỗ này là hứa với nhân viên một số tiền không có thật.
                       "hoa_hong_uoc": round(he_so * max(0.0, tien - moc)),
                       "la_dich": dich is not None and abs(tien - dich) < 1})
    return ra


def dich_moc_le(db) -> float:
    """Mốc TÍNH TIỀN của mảng Lẻ, mặc định văn phòng HCM — dùng để quy các nấc ra tiền."""
    from app.services import rules as R
    return R.get_param(db, "moc_chi_tieu_hcm")


def nhip_cua_nguoi(db, user_id: int, ky: str, mang: str = "le") -> dict:
    """Chuỗi ngày trong kỳ cho biểu đồ phấn đấu của MỘT người: lũy kế, nhịp cần đi, vạch đích."""
    from app.models.hr import Employee
    from app.services import hr as HR
    from app.services import rules as R

    mang = SEG.valid(mang) or "le"
    dau, cuoi = _bien_ky(ky)                       # ném ValueError nếu kỳ không đọc được
    so_ngay = (cuoi - dau).days + 1
    e = db.execute(select(Employee).where(Employee.user_id == user_id)).scalars().first()

    # ── Vạch đích. Chưa khai thì RỖNG, không phải 0: "chưa giao đích" và "giao rồi mà chưa bán
    #    được đồng nào" là hai tình huống ngược nhau, hiện cùng một con số là sai.
    def _dich(khoa: str):
        """Giá trị đích, hoặc None nếu đã TẮT.

        Đặt tham số về 0 trên màn hình Chính sách là cách tắt vạch đích mà không phải sửa mã — và
        0 phải trả về RỖNG chứ không phải số 0, vì "không giao đích" khác hẳn "đích bằng không".
        """
        try:
            v = R.get_param(db, khoa)
        except KeyError:
            return None
        return v if v else None

    if mang == "doan":
        thuoc_do, dich = "loi_nhuan", _dich("dich_ln_nv_doan")
    else:
        hcm, tinh = _dich("dich_dt_nv_le_hcm"), _dich("dich_dt_nv_le_tinh")
        # MỘT luật văn phòng, dùng chung với mốc tính tiền. Viết lại "hcm hay không" lần thứ hai
        # là cầm chắc ngày Bình Dương nằm hai bên hai bảng.
        dich = HR.moc_of(e, hcm, tinh) if (e and hcm and tinh) else hcm
        thuoc_do = "doanh_thu"

    # ── Số của từng ngày, gom theo NGÀY TOUR KẾT THÚC.
    theo_ngay: dict[str, float] = {}
    theo_ngay_du_kien: dict[str, float] = {}
    if mang == "doan":
        from app.services import settlement as ST
        for t in db.execute(select(Tour).where(Tour.end_date >= dau, Tour.end_date <= cuoi,
                                               SEG.tour_cond("doan"))).scalars():
            sm = ST.summary(db, t)
            dt_tour = float(sm.get("revenue") or 0)
            # HAI LỚP, HAI CƠ SỞ KHÁC NHAU — đó là lý do chúng không được cộng vào nhau:
            #   chắc    = doanh thu − THỰC CHI đã ghi dòng quyết toán  (`profit`, chỉ có khi có dòng)
            #   dự kiến = doanh thu − DỰ TOÁN                          (chưa ai chi, chưa ai ký)
            # Chưa có dòng quyết toán nào thì lớp chắc là 0 THẬT, không phải thiếu số liệu: chưa
            # chi đồng nào thì chưa chốt được đồng lợi nhuận nào.
            ln_chac = float(sm.get("profit") or 0) if sm.get("lines") else 0.0
            ln_du_kien = dt_tour - float(sm.get("budget") or 0) if sm.get("has_budget") else ln_chac
            for b in t.bookings:
                if b.cancelled or b.sales_id != user_id:
                    continue
                tien = float(b.amount or 0)
                n = t.end_date.isoformat()
                theo_ngay[n] = theo_ngay.get(n, 0.0) + R.ln_doan_cua_booking(ln_chac, dt_tour, tien)
                theo_ngay_du_kien[n] = theo_ngay_du_kien.get(n, 0.0) + R.ln_doan_cua_booking(
                    ln_du_kien, dt_tour, tien)
    else:
        for d in cua_nguoi(db, user_id, ky)["rows"]:
            if d["luong"] == "doan":
                continue                            # mảng Lẻ không ăn doanh thu tour đoàn
            theo_ngay[d["ket_thuc"]] = theo_ngay.get(d["ket_thuc"], 0.0) + float(d["tien"])

    diem, luy, luy_dk = [], 0.0, 0.0
    for i in range(so_ngay):
        ngay = date(dau.year, dau.month, i + 1).isoformat()
        luy += theo_ngay.get(ngay, 0.0)
        luy_dk += theo_ngay_du_kien.get(ngay, 0.0)
        diem.append({
            "ngay": ngay,
            "luy_ke": round(luy),
            # Hai lớp TÁCH RỜI cho đoàn: lợi nhuận chỉ chắc sau quyết toán, mà quyết toán về sau
            # tour hàng tuần. Gộp vào một đường là tạo một con số đẹp không ai kiểm được.
            "luy_ke_du_kien": round(luy_dk) if mang == "doan" else None,
            "nhip": round(dich * (i + 1) / so_ngay) if dich else None,
        })

    # ── Nấc thang: bậc đang đứng và bậc kế tiếp. Luôn còn nấc phía trước cho tới nấc cuối.
    nac = thang_nac(db, mang, dich)
    # Đoàn chấm theo BÌNH QUÂN BA THÁNG (Điều 5): một đoàn lớn mất hai ba tháng để tiếp cận, khảo
    # sát, báo giá và ký, nhưng lợi nhuận chỉ ghi vào đúng tháng quyết toán. Xếp bậc theo tháng đơn
    # là đúng cái mà Điều 5 cố ý tránh — và sẽ lệch với phiếu lương.
    binh_quan = None
    if mang == "doan":
        cac_ky = _ba_ky_gan_nhat(ky)
        lich_su = [{"ky": k, "loi_nhuan": round(ln_doan_cua_ky(db, user_id, k))} for k in cac_ky]
        binh_quan = {"gia_tri": round(sum(x["loi_nhuan"] for x in lich_su) / len(lich_su)),
                     "so_ky": len(lich_su), "cac_ky": lich_su}
        do_bang = binh_quan["gia_tri"]
    else:
        do_bang = luy

    dang_o, ke_tiep = None, None
    for n in nac:
        if do_bang >= n["nguong"]:
            dang_o = n
        elif ke_tiep is None:
            ke_tiep = dict(n, con_thieu=round(n["nguong"] - do_bang))

    hom_nay = date.today()
    thu_may = so_ngay if hom_nay > cuoi else (hom_nay - dau).days + 1 if hom_nay >= dau else 0
    nhip_hom_nay = round(dich * thu_may / so_ngay) if (dich and thu_may) else None
    return {
        "ky": ky, "user_id": user_id, "mang": mang, "thuoc_do": thuoc_do,
        "dich": dich, "so_ngay": so_ngay, "ngay_thu": thu_may,
        "luy_ke": round(luy),
        "luy_ke_du_kien": round(luy_dk) if mang == "doan" else None,
        "dat_pct": round(luy / dich * 100, 1) if dich else None,
        "nhip_hom_nay": nhip_hom_nay,
        "truoc_sau_nhip": round(luy - nhip_hom_nay) if nhip_hom_nay is not None else None,
        # Thang nấc: KHÔNG có trần. Đích chỉ là một nấc được đánh dấu, phía trên nó vẫn còn nấc.
        "thang": nac, "bac_dang_o": dang_o, "bac_ke_tiep": ke_tiep,
        "do_bang": round(do_bang),
        # Đoàn: con số xếp bậc là bình quân ba tháng, KHÁC lũy kế tháng này. Trả cả hai và nói rõ
        # cái nào dùng để xếp bậc — giấu một cái đi là để lại hai số mà không ai biết bên nào đúng.
        "binh_quan_3_thang": binh_quan,
        "co_so_xep_bac": "binh_quan_3_thang" if mang == "doan" else "luy_ke_thang",
        "diem": diem,
    }
