"""Đóng góp doanh thu của Marketing — nhóm 2.7. Tiền bỏ ra thu về được bao nhiêu.

═══════════════════════════════════════════════════════════════════════════════════════════════
DÙNG LẠI ĐÚNG MỘT ỐNG SỐ, KHÔNG DỰNG ỐNG THỨ HAI
═══════════════════════════════════════════════════════════════════════════════════════════════
Tệp này gọi thẳng `doanh_thu_kd.dong_ban()` — cùng hàm mà màn hình Kinh doanh Lẻ và màn hình Chủ
tịch đang đọc. Không có một truy vấn doanh thu nào của riêng Marketing ở đây.

Đó là chủ ý, và nó là lý do vòng này rẻ: nếu Marketing tự đếm doanh thu bằng truy vấn riêng thì
sớm muộn hai bảng ra hai con số, và cuộc họp nào cũng mất nửa giờ để cãi bên nào đúng trước khi
bàn được việc. Một ống số thì chỉ có một con số, và mọi câu hỏi còn lại là câu hỏi về cách CHIA
con số ấy — chia theo người bán là màn hình Kinh doanh, chia theo kênh và chiến dịch là màn hình
này.

═══════════════════════════════════════════════════════════════════════════════════════════════
HAI ĐƯỜNG TRUY NGUỒN, VÀ LUẬT ANH TUẤN CHỌN 23/9/2026
═══════════════════════════════════════════════════════════════════════════════════════════════
Một booking có thể nói nó đến từ đâu bằng hai đường, và hai đường ấy đang cùng tồn tại trong kho:

    ĐƯỜNG LEAD    `leads.campaign_id` là KHOÁ NGOẠI thật tới `campaigns`, do Marketing nhập.
                  Nối với booking qua `leads.booking_id` hoặc `leads.ma_booking`.
    ĐƯỜNG BOOKING `bookings.campaign_code` và `bookings.source` — hai Ô CHỮ TỰ DO, người bán gõ.

Anh Tuấn chốt: **ưu tiên đường lead, đường booking là dự phòng.** Lý do anh nêu, ghi lại nguyên ý:
khoá ngoại thật do Marketing nhập thì đáng tin hơn một ô chữ tự do gõ lúc chốt đơn.

NHƯNG KHÔNG ĐƯỢC GIẤU CHỖ HAI ĐƯỜNG BẤT ĐỒNG. Khi lead nói chiến dịch A còn booking ghi chiến dịch
B, tệp này lấy A theo luật, đồng thời đẩy dòng ấy vào `bat_dong` để có người đi soát. Chọn một
đường rồi im lặng về đường kia là cách biến một mâu thuẫn dữ liệu thành một con số trông rất gọn.

MỘT BOOKING CÓ THỂ BỊ NHIỀU LEAD NHẬN. Khớp theo số điện thoại thì một khách gọi ba lần qua ba
kênh sẽ sinh ba lead cùng trỏ vào một booking. Lấy lead SỚM NHẤT (`received_at`), vì kênh kéo được
khách đến lần đầu mới là kênh tạo ra đơn ấy; và đếm số ca như thế vào `nhieu_lead` để Marketing
biết mức nhiễu của phép khớp.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHI PHÍ — MỘT MẶT PHẲNG LỆCH, PHẢI NÓI RA
═══════════════════════════════════════════════════════════════════════════════════════════════
SỬA NGÀY 24/9/2026 — VÒNG TRƯỚC NỐI NHẦM BẢNG, VÀ MÀN HÌNH ĐÃ IN SỐ SAI.

Anh Tuấn chốt 23/9 là "nối chi vào chiến dịch". Bản TC-77 nối `campaign_id` vào DÒNG NGÂN SÁCH rồi
lấy `amount` của dòng ấy làm "chi thực tế". `amount` là DỰ TOÁN — tiền ĐỊNH tiêu. Tiền ĐÃ tiêu nằm
ở đề nghị chi, và `payment_requests.campaign_id` vốn đã có sẵn từ trước. Hệ quả của bản sai: ô
"Thu / chi" chia doanh thu cho dự toán, nên chiến dịch tiêu ít hơn kế hoạch thì hiệu quả hiện THẤP
hơn sự thật, tiêu vượt thì hiện CAO hơn — và không có dấu hiệu nào trên màn hình để ai nghi ngờ.

Nay hàm trả BA con số tiền cho mỗi chiến dịch, mỗi con số một cái tên riêng và không bao giờ trộn:
`du_toan_gan` (tiền định tiêu, từ dòng ngân sách), `da_chi` (tiền đã tiêu, từ đề nghị chi trạng
thái da_chi), `treo` (tiền sắp tiêu, đề nghị đang chạy duyệt). `thu_tren_chi` chia cho `da_chi`.

BA ĐIỀU KÈM THEO, cả ba đều phải hiện lên màn hình:

MỘT — DÒNG CHI CHƯA GẮN CHIẾN DỊCH. Ô chiến dịch của đề nghị chi rỗng cho mọi dòng đã nhập trước
hôm nay, và cố ý không suy ngược từ tên hạng mục: đoán "hạng mục Facebook tháng 9 chắc là của
chiến dịch CD2609-01" là bịa số liệu, đúng thứ ranh giới 09/9/2026 cấm. Phần ấy nằm riêng ở
`da_chi_chua_gan`, không bị chia đều cho các chiến dịch để cho đẹp bảng.

HAI — CHI VÀ THU KHÔNG CÙNG MỘT MỐC THỜI GIAN. Chi tính theo THÁNG LẬP ĐỀ NGHỊ CHI,
thu tính theo THÁNG TOUR KẾT THÚC. Tiền quảng cáo tháng 7 sinh ra tour khởi hành tháng 9 kết thúc
tháng 10, nên tỷ lệ của một tháng đơn lẻ luôn lệch; đọc theo quý hoặc theo cả vòng đời chiến dịch
mới đúng. Hàm trả về `canh_bao_lech_ky` để màn hình in câu ấy ra, chứ không để người đọc tự vấp.

BA — TIỀN ĐANG TREO KHÔNG PHẢI TIỀN ĐÃ TIÊU, và cũng không phải số không. Một chiến dịch có 300
triệu đang chạy duyệt thì "thu trên chi" hôm nay đẹp hơn tuần sau, nên `treo` phải nằm cạnh
`da_chi` trên cùng một dòng chứ không bị giấu đi. Đề nghị bị TỪ CHỐI không vào sổ nào cả.
"""
from sqlalchemy import select

from app.models.core import Booking
from app.models.crm import Lead
from app.models.marketing import Campaign, MarketingBudget, MarketingBudgetLine
from app.services import doanh_thu_kd as DT

# Đường nào quyết định nguồn của một booking. Thứ tự trong tuple LÀ thứ tự ưu tiên.
DUONG = ("lead", "booking", "khong_ro")

KHONG_RO = "(chưa rõ nguồn)"


def _lead_cua_booking(db, ma_booking_theo_id: dict[int, str]) -> tuple[dict[int, Lead], int]:
    """{booking_id: Lead} và số booking bị NHIỀU lead cùng nhận.

    Nối bằng hai cách vì kho có cả hai: `leads.booking_id` (số) và `leads.ma_booking` (mã chữ).
    `leads.booking_id` KHÔNG phải khoá ngoại — nó là kết quả khớp theo số điện thoại, nên có thể
    trỏ vào một booking không còn tồn tại. Tra qua `ma_booking_theo_id` nên dòng rác tự rơi ra.
    """
    theo_ma = {ma: bid for bid, ma in ma_booking_theo_id.items()}
    gom: dict[int, list[Lead]] = {}
    for l in db.execute(select(Lead)).scalars():
        bid = None
        if l.booking_id and l.booking_id in ma_booking_theo_id:
            bid = l.booking_id
        elif l.ma_booking and l.ma_booking in theo_ma:
            bid = theo_ma[l.ma_booking]
        if bid is not None:
            gom.setdefault(bid, []).append(l)

    ra, nhieu = {}, 0
    for bid, ds in gom.items():
        if len(ds) > 1:
            nhieu += 1
        # Sớm nhất trước — xem khối luật ở đầu tệp. `received_at` có thể rỗng ở dòng nạp cũ, nên
        # dòng rỗng xếp sau cùng chứ không làm hàm ngã.
        ds.sort(key=lambda x: (x.received_at is None, x.received_at))
        ra[bid] = ds[0]
    return ra, nhieu


def _chien_dich(db) -> tuple[dict[int, Campaign], dict[str, Campaign]]:
    ds = list(db.execute(select(Campaign)).scalars())
    return {c.id: c for c in ds}, {c.code: c for c in ds if c.code}


def nguon_cua(dong: dict, lead: Lead | None, cd_theo_id: dict, cd_theo_ma: dict) -> dict:
    """Nguồn của một dòng doanh thu: kênh nào, chiến dịch nào, biết được nhờ đường nào.

    Luật ưu tiên nằm ở đây, MỘT CHỖ DUY NHẤT. Mọi phép gom bên dưới đều đọc kết quả của hàm này,
    nên đổi luật là sửa đúng một hàm — chứ không phải đi tìm bốn chỗ cùng đoán nguồn.
    """
    cd_lead = cd_theo_id.get(lead.campaign_id) if (lead and lead.campaign_id) else None
    cd_bk = cd_theo_ma.get(dong.get("ma_chien_dich") or "")

    if cd_lead is not None:
        duong, cd, kenh = "lead", cd_lead, (lead.channel or "")
    elif lead is not None and (lead.channel or "").strip():
        duong, cd, kenh = "lead", None, lead.channel.strip()
    elif cd_bk is not None:
        duong, cd, kenh = "booking", cd_bk, (dong.get("nguon") or "")
    elif (dong.get("nguon") or "").strip():
        duong, cd, kenh = "booking", None, dong["nguon"].strip()
    else:
        duong, cd, kenh = "khong_ro", None, ""

    # Bất đồng: CẢ HAI đường cùng nói ra một chiến dịch, và hai chiến dịch ấy khác nhau. Một bên
    # trống thì không phải bất đồng — đó chỉ là một bên chưa ghi.
    bat_dong = cd_lead is not None and cd_bk is not None and cd_lead.id != cd_bk.id
    return {
        "duong": duong,
        "kenh": kenh or KHONG_RO,
        "chien_dich_id": cd.id if cd else None,
        "chien_dich_ma": cd.code if cd else "",
        "chien_dich_ten": cd.name if cd else "",
        "bat_dong": bat_dong,
        "cd_theo_lead": cd_lead.code if cd_lead else "",
        "cd_theo_booking": cd_bk.code if cd_bk else "",
    }


def _chi_thang(db, ky: str) -> dict:
    """HAI CON SỐ TIỀN, GỌI ĐÚNG TÊN TỪNG CÁI.

    LỖI ĐÃ SỬA 24/9/2026 — bản TC-77 của hàm này cộng `mkt_budget_lines.amount` rồi trả về dưới
    tên `tong_chi`, và màn hình in nó dưới nhãn "Chi thực tế". `amount` là DỰ TOÁN. Hệ quả: ô
    "Thu / chi" là doanh thu chia cho tiền ĐỊNH tiêu, nên chiến dịch tiêu ít hơn kế hoạch thì hiệu
    quả hiện thấp hơn sự thật và tiêu vượt thì hiện cao hơn. Xem `marketing.chi_thuc_te`.

    Nay trả về CẢ HAI, và không bao giờ trộn:
        du_toan_*  – dòng ngân sách đã duyệt cho kỳ, tiền ĐỊNH tiêu
        da_chi_*   – đề nghị chi trạng thái `da_chi` của kỳ, tiền ĐÃ tiêu
        treo_*     – đề nghị chi đang chạy duyệt, tiền SẮP tiêu

    KHÔNG chia phần chưa gắn cho các chiến dịch, ở cả hai sổ. Chia đều là bịa: một dòng 200 triệu
    không gắn chiến dịch có thể là của một chiến dịch, có thể là chi chung cả tháng, và không ai ở
    đây biết là cái nào.
    """
    from app.services import marketing as MK

    ngan_sach = list(db.execute(
        select(MarketingBudget).where(MarketingBudget.period == ky)).scalars())
    ids = [b.id for b in ngan_sach]
    dong = []
    if ids:
        dong = list(db.execute(
            select(MarketingBudgetLine).where(MarketingBudgetLine.budget_id.in_(ids))).scalars())

    du_theo_cd: dict[int, float] = {}
    du_chua_gan = 0.0
    for d in dong:
        tien = float(d.amount or 0)
        if getattr(d, "campaign_id", None):
            du_theo_cd[d.campaign_id] = du_theo_cd.get(d.campaign_id, 0.0) + tien
        else:
            du_chua_gan += tien

    tt = MK.chi_thuc_te(db, ky)
    return {
        "du_toan_tong": float(sum(float(d.amount or 0) for d in dong)),
        "du_toan_theo_chien_dich": du_theo_cd,
        "du_toan_chua_gan": du_chua_gan,
        "so_dong_du_toan": len(dong),
        "co_ngan_sach": bool(ngan_sach),
        "da_chi_tong": tt["da_chi_tong"],
        "da_chi_theo_chien_dich": tt["da_chi_theo_chien_dich"],
        "da_chi_chua_gan": tt["da_chi_chua_gan"],
        "treo_tong": tt["treo_tong"],
        "treo_theo_chien_dich": tt["treo_theo_chien_dich"],
        "treo_chua_gan": tt["treo_chua_gan"],
        "so_dong_chi": tt["so_dong"],
    }

def thang(db, ky: str, mang: str = "") -> dict:
    """Đóng góp doanh thu của Marketing trong một kỳ.

    `mang` rỗng = cả ba luồng. Truyền "le" hoặc "doan" để trả lời riêng câu hiệu quả khách lẻ và
    khách đoàn (mục 2.7.2) — cùng cách phân mảng mà `services/segments.py` đã chốt, không có bản
    chép thứ hai ở đây.
    """
    if mang and mang not in DT.LUONG:
        raise ValueError(f"Luồng không hợp lệ: {mang!r}. Chỉ có {', '.join(DT.LUONG)}.")

    nhom = DT.dong_ban(db, ky)
    # MỌI ngăn người bán, không riêng khối Kinh doanh: một booking do đối tác hay do Điều hành
    # bán vẫn có thể đến từ một chiến dịch Marketing. Câu hỏi ở đây là "tiền quảng cáo kéo về
    # được bao nhiêu", không phải "ai được tính chỉ tiêu".
    dong = [d for k in nhom for d in nhom[k] if not mang or d["luong"] == mang]

    ma_theo_id = {d["booking_id"]: d["ma"] for d in dong}
    lead_cua, nhieu_lead = _lead_cua_booking(db, ma_theo_id)
    cd_id, cd_ma = _chien_dich(db)

    theo_kenh: dict[str, dict] = {}
    theo_cd: dict[int, dict] = {}
    theo_duong = {k: {"so_booking": 0, "tien": 0.0} for k in DUONG}
    chua_ro_rows: list[dict] = []
    bat_dong = []
    khong_ro = {"so_booking": 0, "tien": 0.0}

    for d in dong:
        ng = nguon_cua(d, lead_cua.get(d["booking_id"]), cd_id, cd_ma)
        tien = d["tien"]

        theo_duong[ng["duong"]]["so_booking"] += 1
        theo_duong[ng["duong"]]["tien"] += tien

        k = theo_kenh.setdefault(ng["kenh"], {"kenh": ng["kenh"], "tien": 0.0,
                                              "so_booking": 0, "so_khach": 0})
        k["tien"] += tien; k["so_booking"] += 1; k["so_khach"] += d["khach_so"] or 0

        if ng["chien_dich_id"]:
            c = theo_cd.setdefault(ng["chien_dich_id"], {
                "chien_dich_id": ng["chien_dich_id"], "ma": ng["chien_dich_ma"],
                "ten": ng["chien_dich_ten"], "tien": 0.0, "so_booking": 0, "so_khach": 0})
            c["tien"] += tien; c["so_booking"] += 1; c["so_khach"] += d["khach_so"] or 0

        if ng["duong"] == "khong_ro":
            khong_ro["so_booking"] += 1; khong_ro["tien"] += tien
            # LIỆT KÊ RA, không chỉ đếm. Một con số "37 booking chưa rõ nguồn" không ai sửa được;
            # một danh sách 37 dòng có nút gắn nguồn thì sửa được ngay tại chỗ nhìn thấy nó thiếu.
            chua_ro_rows.append({x: d[x] for x in
                                 ("booking_id", "ma", "khach", "tien", "ket_thuc", "tour_ma")})

        if ng["bat_dong"]:
            bat_dong.append({**{x: d[x] for x in ("booking_id", "ma", "khach", "tien", "ket_thuc")},
                             "theo_lead": ng["cd_theo_lead"], "theo_booking": ng["cd_theo_booking"]})

    chi = _chi_thang(db, ky)

    def _so_chi(cd_id_: int, cd) -> dict:
        """Ba con số tiền của một chiến dịch, mỗi con số một cái tên riêng.

        `thu_tren_chi` CHIA CHO TIỀN ĐÃ TIÊU, không chia cho dự toán — đó chính là chỗ bản TC-77
        sai. Chưa chi đồng nào thì để RỖNG chứ không để 0 và cũng không chia cho 0: "chưa tiêu
        đồng nào" khác hẳn "tiêu mà không thu được gì".
        """
        da_chi = chi["da_chi_theo_chien_dich"].get(cd_id_, 0.0)
        return {
            "da_chi": da_chi,
            "treo": chi["treo_theo_chien_dich"].get(cd_id_, 0.0),
            "du_toan_gan": chi["du_toan_theo_chien_dich"].get(cd_id_, 0.0),
            "chi_ke_hoach": float(cd.budget or 0) if cd else 0.0,
            "thu_tren_chi": None,
        }

    for c in theo_cd.values():
        c.update(_so_chi(c["chien_dich_id"], cd_id.get(c["chien_dich_id"])))
        c["thu_tren_chi"] = (c["tien"] / c["da_chi"]) if c["da_chi"] else None

    # Chiến dịch CÓ CHI mà KHÔNG có doanh thu nào — không tự hiện ra nếu chỉ duyệt theo booking,
    # mà đó lại đúng là nhóm đáng xem nhất.
    # Duyệt CẢ HAI sổ: một chiến dịch mới lập ngân sách mà chưa tiêu đồng nào cũng phải hiện ra,
    # và một chiến dịch đã tiêu mà chưa ai lập dự toán thì càng phải hiện ra.
    co_tien = set(chi["da_chi_theo_chien_dich"]) | set(chi["treo_theo_chien_dich"]) \
        | set(chi["du_toan_theo_chien_dich"])
    for cd_id_ in co_tien:
        if cd_id_ not in theo_cd:
            cd = cd_id.get(cd_id_)
            theo_cd[cd_id_] = {"chien_dich_id": cd_id_, "ma": cd.code if cd else "",
                               "ten": cd.name if cd else "", "tien": 0.0, "so_booking": 0,
                               "so_khach": 0, **_so_chi(cd_id_, cd)}

    tong = float(sum(d["tien"] for d in dong))
    return {
        "ky": ky, "mang": mang or "tat_ca",
        "tong_doanh_thu": tong,
        "co_so": "Doanh thu lấy từ cùng một ống số với màn hình Kinh doanh Lẻ "
                 "(giá trị booking chưa huỷ, kỳ theo tháng tour kết thúc). "
                 "Gồm mọi người bán, kể cả đối tác và người ngoài khối Kinh doanh.",
        "theo_duong": theo_duong,
        "do_phu": {
            "truy_duoc_nguon": tong - khong_ro["tien"],
            "chua_ro_nguon": khong_ro["tien"],
            "so_booking_chua_ro": khong_ro["so_booking"],
            "ty_le": (1 - khong_ro["tien"] / tong) if tong else None,
            "rows": sorted(chua_ro_rows, key=lambda x: -x["tien"])[:200],
        },
        "theo_kenh": sorted(theo_kenh.values(), key=lambda x: -x["tien"]),
        "theo_chien_dich": sorted(theo_cd.values(), key=lambda x: -x["tien"]),
        # Bản chi theo từng chiến dịch đã nằm trong `theo_chien_dich` ở trên; ở đây chỉ trả phần
        # tổng và phần CHƯA GẮN CHIẾN DỊCH — đúng con số mà người đọc cần để biết bảng trên còn
        # thiếu bao nhiêu tiền chi.
        "chi_marketing": {k: chi[k] for k in (
            "da_chi_tong", "da_chi_chua_gan", "treo_tong", "treo_chua_gan",
            "du_toan_tong", "du_toan_chua_gan", "so_dong_chi", "so_dong_du_toan",
            "co_ngan_sach")},
        "bat_dong": {"so_dong": len(bat_dong), "rows": bat_dong[:200]},
        "nhieu_lead_mot_booking": nhieu_lead,
        "canh_bao_lech_ky":
            "Chi tính theo THÁNG LẬP ĐỀ NGHỊ CHI, thu tính theo THÁNG TOUR KẾT THÚC. Tiền quảng cáo "
            "tháng này thường sinh ra doanh thu của tháng sau hoặc tháng sau nữa, nên tỷ lệ của "
            "một tháng đơn lẻ luôn lệch — đọc theo quý hoặc theo cả vòng đời chiến dịch mới đúng.",
    }


def chien_dich_chi_tiet(db, chien_dich_id: int, ky: str) -> dict:
    """Một chiến dịch: từng booking nó kéo về trong kỳ. Mục 2.7.1 — truy vết nguồn đến booking."""
    cd = db.get(Campaign, chien_dich_id)
    if cd is None:
        raise ValueError(f"Không có chiến dịch id {chien_dich_id}.")
    nhom = DT.dong_ban(db, ky)
    dong = [d for k in nhom for d in nhom[k]]
    ma_theo_id = {d["booking_id"]: d["ma"] for d in dong}
    lead_cua, _ = _lead_cua_booking(db, ma_theo_id)
    cd_id, cd_ma = _chien_dich(db)

    rows = []
    for d in dong:
        ng = nguon_cua(d, lead_cua.get(d["booking_id"]), cd_id, cd_ma)
        if ng["chien_dich_id"] == chien_dich_id:
            rows.append({**d, "duong": ng["duong"], "kenh": ng["kenh"],
                         "bat_dong": ng["bat_dong"]})
    return {
        "ky": ky,
        "chien_dich": {"id": cd.id, "ma": cd.code, "ten": cd.name, "mang": cd.mang,
                       "trang_thai": cd.status, "ngan_sach_ke_hoach": float(cd.budget or 0),
                       "tu_ngay": cd.from_date.isoformat() if cd.from_date else "",
                       "den_ngay": cd.to_date.isoformat() if cd.to_date else ""},
        "tien": float(sum(r["tien"] for r in rows)),
        "so_booking": len(rows),
        "so_khach": sum(r["khach_so"] or 0 for r in rows),
        "rows": sorted(rows, key=lambda x: x["ket_thuc"]),
    }


def gan_nguon(db, boi, booking_id: int, kenh: str = "", chien_dich_id: int | None = None,
              ly_do: str = "") -> dict:
    """Gắn nguồn cho một booking chưa truy được nguồn. CỬA NHẬP DUY NHẤT của màn hình 2.7.

    VÌ SAO CỬA NÀY NẰM Ở ĐÂY CHỨ KHÔNG Ở MÀN HÌNH BOOKING. Ranh giới 09/9/2026 đòi mỗi con số có
    một cửa, và phép thử `test_man_hinh_co_cua_nhap` đã chặn đúng lúc em định khai màn hình này là
    "chỉ xem" — danh sách ngoại lệ ấy đã chạm trần 8, và nó có trần để ngăn đúng việc nới thêm một
    dòng thay vì dựng cửa.

    Dựng cửa ở đây hoá ra cũng là chỗ đúng: người biết một booking đến từ kênh nào là người
    Marketing, và họ chỉ phát hiện ra nó thiếu khi nhìn bảng độ phủ của chính màn hình này. Bắt họ
    nhớ mã booking rồi đi sang màn hình Booking gõ lại là cách chắc chắn để không ai sửa.

    BA HÀNG RÀO, mỗi cái chặn một kiểu sai khác nhau:

    MỘT — CHỈ GẮN ĐƯỢC CHO BOOKING ĐANG TRỐNG CẢ HAI Ô. Booking đã có nguồn thì cửa này từ chối,
    kể cả khi nguồn ấy trông sai. Sửa một nguồn ĐÃ GHI là đổi câu trả lời cũ của người khác, việc
    ấy phải đi qua màn hình Booking nơi có nhật ký sửa đầy đủ. Cửa này chỉ ĐIỀN CHỖ TRỐNG.

    HAI — KHÔNG ĐỘNG VÀO BOOKING ĐÃ CÓ LEAD. Lead là đường ưu tiên theo luật anh Tuấn chốt 23/9;
    ghi đè ô trên booking khi đã có lead là tạo ra đúng cái bất đồng mà màn hình này sinh ra để
    phát hiện.

    BA — PHẢI GHI LÝ DO. Gắn nguồn là đổi con số đóng góp của một chiến dịch, tức là đổi cơ sở để
    đánh giá một khoản chi. Cuối quý sẽ có người hỏi vì sao chiến dịch này tự nhiên tăng thêm hai
    tỷ, và lúc ấy phải tra ra được ai gắn và vì sao.
    """
    from app.models.core import Booking as _Booking
    from app.services import rules as R

    b = db.get(_Booking, booking_id)
    if b is None:
        raise ValueError(f"Không có booking id {booking_id}.")
    if not (ly_do or "").strip():
        raise ValueError("Gắn nguồn cho một booking phải ghi lý do — đây là thứ đổi con số đóng "
                         "góp của một chiến dịch.")
    if (b.source or "").strip() or (b.campaign_code or "").strip():
        raise ValueError(
            f"Booking {b.code} đã có nguồn ghi sẵn. Cửa này chỉ điền chỗ TRỐNG; sửa một nguồn đã "
            "ghi phải làm ở màn hình Booking, nơi có nhật ký sửa đầy đủ.")

    lead_cua, _ = _lead_cua_booking(db, {b.id: b.code})
    if lead_cua.get(b.id) is not None:
        raise ValueError(
            f"Booking {b.code} đã khớp với một lead, nên nguồn của nó lấy theo lead — đó là luật "
            "ưu tiên chốt 23/9/2026. Ghi đè ô trên booking ở đây chỉ tạo thêm một chỗ bất đồng.")

    cd = db.get(Campaign, chien_dich_id) if chien_dich_id else None
    if chien_dich_id and cd is None:
        raise ValueError(f"Không có chiến dịch id {chien_dich_id}.")
    if not (kenh or "").strip() and cd is None:
        raise ValueError("Phải chọn kênh hoặc chiến dịch — gắn nguồn rỗng thì không gắn gì cả.")

    truoc = {"source": b.source or "", "campaign_code": b.campaign_code or ""}
    if (kenh or "").strip():
        b.source = kenh.strip()
    if cd is not None:
        b.campaign_code = cd.code
    R.audit(db, boi.username, boi.role, "gan_nguon_marketing", f"booking:{b.code}",
            before=truoc,
            after={"source": b.source or "", "campaign_code": b.campaign_code or "",
                   "ly_do": ly_do.strip()})
    return {"da_ghi": True, "booking_id": b.id, "ma": b.code,
            "message": f"Đã gắn nguồn cho booking {b.code}"}
