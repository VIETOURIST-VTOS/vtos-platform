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
Từ 23/9/2026 dòng ngân sách mang thêm `campaign_id` (anh Tuấn chọn), nên chi THỰC TẾ của từng
chiến dịch tính được. Hai điều kèm theo, cả hai đều phải hiện lên màn hình:

MỘT — DÒNG CHI CŨ KHÔNG CÓ CHIẾN DỊCH. Cột mới rỗng cho mọi dòng đã nhập trước hôm nay, và cố ý
không suy ngược từ tên hạng mục: đoán "hạng mục Facebook tháng 9 chắc là của chiến dịch CD2609-01"
là bịa số liệu, đúng thứ ranh giới 09/9/2026 cấm. Phần chi chưa gắn chiến dịch nằm riêng ở
`chi_chua_gan`, không bị chia đều cho các chiến dịch để cho đẹp bảng.

HAI — CHI VÀ THU KHÔNG CÙNG MỘT MỐC THỜI GIAN. Chi tính theo THÁNG NGÂN SÁCH (`mkt_budgets.period`),
thu tính theo THÁNG TOUR KẾT THÚC. Tiền quảng cáo tháng 7 sinh ra tour khởi hành tháng 9 kết thúc
tháng 10, nên tỷ lệ của một tháng đơn lẻ luôn lệch; đọc theo quý hoặc theo cả vòng đời chiến dịch
mới đúng. Hàm trả về `canh_bao_lech_ky` để màn hình in câu ấy ra, chứ không để người đọc tự vấp.
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
    """Chi Marketing của kỳ, tách phần đã gắn chiến dịch và phần chưa gắn.

    KHÔNG chia phần chưa gắn cho các chiến dịch. Chia đều là bịa: một dòng chi 200 triệu không
    gắn chiến dịch có thể là của một chiến dịch, có thể là chi chung cả tháng, và không ai ở đây
    biết là cái nào.
    """
    ngan_sach = list(db.execute(
        select(MarketingBudget).where(MarketingBudget.period == ky)).scalars())
    ids = [b.id for b in ngan_sach]
    dong = []
    if ids:
        dong = list(db.execute(
            select(MarketingBudgetLine).where(MarketingBudgetLine.budget_id.in_(ids))).scalars())

    theo_cd: dict[int, float] = {}
    chua_gan = 0.0
    for d in dong:
        tien = float(d.amount or 0)
        if getattr(d, "campaign_id", None):
            theo_cd[d.campaign_id] = theo_cd.get(d.campaign_id, 0.0) + tien
        else:
            chua_gan += tien
    tong = float(sum(float(d.amount or 0) for d in dong))
    return {
        "tong_chi": tong,
        "theo_chien_dich": theo_cd,
        "chi_chua_gan": chua_gan,
        "so_dong": len(dong),
        "co_ngan_sach": bool(ngan_sach),
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
    for c in theo_cd.values():
        cd = cd_id.get(c["chien_dich_id"])
        c["chi_thuc_te"] = chi["theo_chien_dich"].get(c["chien_dich_id"], 0.0)
        c["chi_ke_hoach"] = float(cd.budget or 0) if cd else 0.0
        # Thu trên mỗi đồng chi. Chi bằng 0 thì để RỖNG chứ không để 0 và cũng không chia cho 0:
        # "chưa gắn đồng chi nào" khác hẳn "chi mà không thu được gì".
        c["thu_tren_chi"] = (c["tien"] / c["chi_thuc_te"]) if c["chi_thuc_te"] else None

    # Chiến dịch CÓ CHI mà KHÔNG có doanh thu nào — không tự hiện ra nếu chỉ duyệt theo booking,
    # mà đó lại đúng là nhóm đáng xem nhất.
    for cd_id_, tien_chi in chi["theo_chien_dich"].items():
        if cd_id_ not in theo_cd:
            cd = cd_id.get(cd_id_)
            theo_cd[cd_id_] = {"chien_dich_id": cd_id_, "ma": cd.code if cd else "",
                               "ten": cd.name if cd else "", "tien": 0.0, "so_booking": 0,
                               "so_khach": 0, "chi_thuc_te": tien_chi,
                               "chi_ke_hoach": float(cd.budget or 0) if cd else 0.0,
                               "thu_tren_chi": 0.0}

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
        "chi_marketing": {k: chi[k] for k in ("tong_chi", "chi_chua_gan", "so_dong", "co_ngan_sach")},
        "bat_dong": {"so_dong": len(bat_dong), "rows": bat_dong[:200]},
        "nhieu_lead_mot_booking": nhieu_lead,
        "canh_bao_lech_ky":
            "Chi tính theo THÁNG NGÂN SÁCH, thu tính theo THÁNG TOUR KẾT THÚC. Tiền quảng cáo "
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
