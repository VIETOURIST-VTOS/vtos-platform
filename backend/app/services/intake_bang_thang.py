# -*- coding: utf-8 -*-
"""CỬA NẠP BẢNG THÁNG DỊCH VỤ LẺ — 49 tệp T1–T6/2026 mà ba cửa kia cố ý để ra ngoài.

──────────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ CỬA THỨ BẢY NÀY
──────────────────────────────────────────────────────────────────────────────────────────────────

Cửa 'Tạo CHUYẾN từ kho cũ' xếp 49 tệp vào rổ `khong_thay_chuyen` và nói thẳng lý do: chúng KHÔNG
phải một chuyến. Đúng — nhưng "không phải một chuyến" không có nghĩa là "không phải tiền". Đo ngày
16/9/2026 trên đúng 49 tệp ấy: **672 dòng khách · thu 10.294.415.565 · chi 8.011.224.547**.

Ngần ấy tiền đứng ngoài hệ vì thiếu MỘT CÁI CỬA, không vì thiếu số liệu. Mỗi dòng trong 49 tệp là
một khách có tên, có người bán, có giá bán và các khoản phí của chính người ấy — chúng là SỔ ĐĂNG KÝ
TỪNG KHÁCH, không phải bảng gom.

──────────────────────────────────────────────────────────────────────────────────────────────────
MỘT TỆP = MỘT CHUYẾN `non_package`, KHÔNG PHẢI MỘT CHUYẾN ĐI
──────────────────────────────────────────────────────────────────────────────────────────────────

'VISA LẺ THÁNG 3.2026' không phải một chuyến đi, và cửa này không dựng chuyến ma cho nó. Nó là SỔ
DỊCH VỤ LẺ CỦA MỘT THÁNG, và VTOS đã có đúng loại ấy: `tour_type = "non_package"` — cái mà màn hình
/non-package vẫn dùng cho visa, vé, khách sạn, land bán lẻ. Đặt vào đó là gọi đúng tên, không phải
mượn chỗ.

Mã sổ mang tiền tố `DVL-` (dịch vụ lẻ) + loại + tháng/năm + ĐUÔI CỦA TÊN TỆP: `DVL-VISA032026-7A3C`.
Nhìn tiền tố là biết nó đến từ đâu, không lẫn vào mã chuyến thật của Điều hành.

CÁI ĐUÔI KHÔNG PHẢI CHO ĐẸP — nó vá một lỗi đo được. Bản đầu đặt mã theo loại + tháng thôi, và
tháng 3/2026 có nhiều tệp visa khác nhau ('VISA LẺ CHÂU ÂU T3.2026' và 'VISA LẺ T3.2026 ĐH PHẠM THỊ
THÚY VY' là hai sổ của hai người). Chúng rơi vào cùng một mã, tệp sau ghi đè tệp trước, và bảng xem
trước nói 43 sổ / 8,37 tỷ trong khi ghi xuống thật còn 17 sổ / 4,51 tỷ: **mất 3,86 tỷ, mất im lặng**.
Xem `ma_chuyen`.

──────────────────────────────────────────────────────────────────────────────────────────────────
CỘT SALES: DÙNG LẠI SỔ GÁN ĐÃ CÓ, KHÔNG DỰNG SỔ THỨ HAI
──────────────────────────────────────────────────────────────────────────────────────────────────

Chủ tịch chốt 16/9/2026: *"cột SALES ghi tên người. Gán bừa vào tài khoản là đụng vào thưởng của
người thật."*

VTOS đã có nguyên bộ máy cho việc ấy, dựng cho kho cũ ngày 13/9: `kho_cu_nguoi_ban` (sổ gán tên),
`phieu_dat_kho_cu.sinh` (MỖI NGƯỜI BÁN MỘT PHIẾU), `phieu_dat_kho_cu.gan_lai` (gán tên xong thì
khách chuyển sang phiếu đúng người, không phải nạp lại lô). Cửa này NỐI VÀO đó chứ không viết lại:
hai sổ gán cho cùng một việc là hai sổ sẽ lệch nhau.

Hệ quả cụ thể, và đây là chỗ khác với điều đã hứa ngày 16/9: **`sales_id` không để RỖNG được** —
`bookings.sales_id` là cột NOT NULL có khoá ngoại. Cách cửa tạo chuyến giải bài ấy là trỏ vào một
TÀI KHOẢN HỆ THỐNG ĐANG KHOÁ rồi nêu tên ra sổ gán, và đó là cách cửa này làm. Kết quả với người
thật vẫn đúng như đã chốt: dòng chưa gán được mang `counts_for_target = False`, nên **không một nhân
viên nào bị cộng nhầm doanh số vào chỉ tiêu**.

DÙNG CHUNG `source = kho_cu_h1_2026` VỚI CỬA KHO CŨ — CỐ Ý. `gan_lai` lọc phiếu theo đúng cột ấy;
đặt một nguồn riêng là phiếu của cửa này nằm ngoài tầm với của màn hình gán, và cột SALES vĩnh viễn
không ai gán được. 49 tệp này VỐN LÀ một phần của kho quyết toán cũ T1–T6/2026, nên tên nguồn ấy
cũng đúng sự thật. Muốn tách riêng thì nhìn `tours.code` — tiền tố `DVL-` là của cửa này.

──────────────────────────────────────────────────────────────────────────────────────────────────
NGOẠI TỆ: GHI SỐ GỐC, KHÔNG QUY ĐỔI, VÀ NÓI RA
──────────────────────────────────────────────────────────────────────────────────────────────────

Chủ tịch chốt: *"Không tự quy đổi ngoại tệ."* `tour_cost_lines` đã mang sẵn bốn cột cho việc ấy —
`tien_te`, `so_tien_goc`, `ty_gia`, `ngay_ty_gia`. Cửa này ghi hai cột đầu và **để `ty_gia` rỗng,
`actual` rỗng**.

`actual` rỗng nghĩa là dòng chi ấy CHƯA CÓ SỐ VND, nên tổng chi của chuyến đọc THIẾU đúng bằng chừng
ấy. Đó là sự thật, không phải lỗi: chưa ai khai tỷ giá của ngày chi thật thì chưa ai biết nó bằng
bao nhiêu đồng. Điều KHÔNG được phép là để chỗ thiếu ấy im lặng — nên mọi bản trả về của cửa này đều
có `cho_ty_gia` và `tien_cho_ty_gia` đứng riêng một dòng.

Số VND sẵn trong tệp cố ý KHÔNG dùng: không ai biết tỷ giá trong tệp của ngày nào, lấy ở đâu.

──────────────────────────────────────────────────────────────────────────────────────────────────
NẠP LẠI THÌ THAY, KHÔNG NHÂN ĐÔI
──────────────────────────────────────────────────────────────────────────────────────────────────

Nạp lại cùng một tệp xoá sạch phần CỦA NGUỒN NÀY trên chuyến ấy rồi ghi lại. Không đụng vào dòng
người ta sửa tay bằng cửa khác (`source` khác), và không đụng vào chuyến của cửa khác.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.services import khop_nguoi_ban as KN
from app.services import nap_bang_thang as NBT
from app.services import phieu_dat_kho_cu as PD
from app.services.tao_chuyen_kho_cu import NGUON

# Tiền tố mã chuyến của cửa này. Nhìn mã là biết dòng tiền đến từ bảng tháng chứ không từ một chuyến
# đi có thật — phân biệt bằng MÃ, không bằng `source` (xem ghi chú đầu tệp).
TIEN_TO = "DVL-"

# Chuyến dựng ra ở trạng thái nào. Giống cửa tạo chuyến: đây là ghi lại lịch sử đã xảy ra, không
# phải một chuyến đang chờ duyệt.
TRANG_THAI = "da_duyet"

LOAI_TEN = {"VISA": "Visa lẻ", "LAND": "Land lẻ", "VE": "Vé lẻ",
            "COMBO": "Combo lẻ", "KHAC": "Dịch vụ lẻ"}


def _thang_nam(d: dict) -> tuple[int, int] | None:
    """(năm, tháng) của bảng. `None` khi tên tệp không nói đủ — và KHÔNG đoán hộ.

    Đoán sai một lần là cả một tháng tiền nằm nhầm năm tài chính, mà không có gì kêu lên: mọi tổng
    vẫn cân, chỉ là cân ở sai chỗ.
    """
    ky = d.get("ky")
    if not ky or ky[0] is None:
        return None
    return int(ky[0]), int(ky[1])


def ma_chuyen(d: dict) -> str | None:
    """Mã sổ tháng cho MỘT TỆP. `None` khi chưa đủ căn cứ — không có mã thì không dựng sổ.

    ĐUÔI BỐN KÝ TỰ LÀ CỦA TÊN TỆP, VÀ ĐÓ LÀ CHỖ SỬA MỘT LỖI ĐO ĐƯỢC NGÀY 16/9/2026.

    Bản đầu đặt mã theo LOẠI + THÁNG (`DVL-VISA032026`). Chạy thử trên tệp thật thì tháng 3/2026 có
    nhiều tệp visa khác nhau — 'VISA LẺ CHÂU ÂU T3.2026' và 'VISA LẺ T3.2026 ĐH PHẠM THỊ THÚY VY'
    là hai sổ riêng của hai người. Chúng rơi vào cùng một mã và tệp sau GHI ĐÈ tệp trước: bảng xem
    trước nói 43 sổ / 8,37 tỷ, ghi xuống thật còn 17 sổ / 4,51 tỷ. **Mất 3,86 tỷ, mất im lặng** —
    mọi tổng vẫn cân, chỉ là cân trên phần còn lại.

    Đuôi lấy từ `khoa_tep` (tên tệp đã chuẩn hoá) nên nó ỔN ĐỊNH: nạp lại đúng tệp ấy ra đúng mã
    ấy, và nạp lại là THAY chứ không đẻ sổ thứ hai. Mã không phải để người đọc — người đọc TÊN sổ,
    và tên sổ mang tên tệp.
    """
    import hashlib

    from app.services.tao_chuyen_kho_cu import khoa_tep

    tn = _thang_nam(d)
    if tn is None:
        return None
    nam, thang = tn
    k = khoa_tep(d.get("ten_tep") or "")
    if not k:
        return None
    duoi = hashlib.sha1(k.encode("utf-8")).hexdigest()[:4].upper()
    return f"{TIEN_TO}{(d.get('loai_dich_vu') or 'KHAC')[:6]}{thang:02d}{nam:04d}-{duoi}"[:30]


def _ngay_bang(d: dict) -> date | None:
    """Ngày gán cho chuyến = NGÀY CUỐI THÁNG của kỳ. Cố ý không lấy ngày đầu tháng.

    Bảng tháng chốt vào cuối tháng; lấy ngày đầu là đặt toàn bộ doanh thu của tháng vào trước lúc
    nó phát sinh, và mọi báo cáo theo ngày đọc lệch một tháng.
    """
    tn = _thang_nam(d)
    if tn is None:
        return None
    nam, thang = tn
    if thang == 12:
        return date(nam, 12, 31)
    return date(nam, thang + 1, 1) - timedelta(days=1)


def _khach_cho_phieu(d: dict) -> list[dict]:
    """Dòng khách theo đúng hình `phieu_dat_kho_cu` cần: `sale`, `ho_ten`, `tong_thu`.

    Dòng KHÔNG có tên khách vẫn giữ lại nếu nó có tiền — tiền công ty thu thật, bỏ đi là bảng lãi lỗ
    sai đúng kiểu cũ. Chỉ bỏ dòng vừa không tên vừa không tiền: đó là dòng trắng.
    """
    ra = []
    for x in d.get("dong") or []:
        ten = (x.get("ten_khach") or "").strip()
        thu = float(x.get("thu") or 0)
        if not ten and thu <= 0:
            continue
        ra.append({"sale": (x.get("sale") or "").strip(),
                   "ho_ten": ten or "(tệp không ghi tên khách)",
                   "tong_thu": thu,
                   "_hang": x.get("_hang"),
                   "_goc": x})
    return ra


def _xoa_phan_cua_nguon(db, tour_id: int) -> None:
    """Xoá phần CỦA NGUỒN NÀY trên một chuyến, trước khi ghi lại.

    Dòng chi lọc theo `source` nên dòng ai đó thêm tay bằng cửa khác KHÔNG bị cuốn theo. Phiếu đặt
    và dòng khách đi qua `PD.xoa_phieu_cua_lo` – nó xoá dòng khách TRƯỚC rồi mới xoá phiếu, nếu
    không `booking_khach.booking_id` thành khoá mồ côi.
    """
    from app.models.vietrip import TourCostLine

    db.query(TourCostLine).filter(TourCostLine.tour_id == tour_id,
                                  TourCostLine.source == NGUON).delete(synchronize_session=False)
    PD.xoa_phieu_cua_lo(db, tour_id)
    db.flush()


def doc_tep_lo(noi_dung: bytes, ten_tep: str = "") -> list[dict]:
    """Một tệp = một dòng của lô. Dùng ĐÚNG bộ đọc vá 10a, không viết bộ đọc thứ hai."""
    return [NBT.doc_tep(noi_dung, ten_tep)]


def _ma_da_co(db) -> dict[str, int]:
    from app.models.core import Tour
    return {(t.code or "").strip().upper(): t.id
            for t in db.scalars(select(Tour).where(Tour.code.like(TIEN_TO + "%"))).all()}


def _mot_hang(d: dict, da_co: dict[str, int]) -> dict:
    """Một dòng của bảng xem trước: tệp này sẽ làm gì."""
    ma = ma_chuyen(d)
    khach = _khach_cho_phieu(d)
    cho = sum(len(x.get("ngoai_te") or []) for x in d.get("dong") or [])
    tien_cho = round(sum(float(k.get("so_tien_goc") or 0)
                         for x in d.get("dong") or [] for k in (x.get("ngoai_te") or [])), 2)
    h = {"tep": d.get("ten_tep") or "", "ma": ma or "",
         "loai": d.get("loai_dich_vu") or "KHAC",
         "ky": (f"{_thang_nam(d)[1]:02d}/{_thang_nam(d)[0]}" if _thang_nam(d) else ""),
         "so_khach": len(khach), "thu": d.get("tong_thu") or 0.0, "chi": d.get("tong_chi") or 0.0,
         "cho_ty_gia": cho, "tien_cho_ty_gia": tien_cho,
         "cot_khong_nhan_ra": list(d.get("cot_khong_nhan_ra") or []),
         "thieu": list(d.get("thieu") or []),
         "viec": "", "vi_sao": ""}
    if d.get("hang_tieu_de") is None:
        h["viec"], h["vi_sao"] = "bo_qua", "không tìm được hàng tiêu đề – cần người xem lại bố cục tệp"
    elif ma is None:
        h["viec"], h["vi_sao"] = "bo_qua", "tên tệp không nói đủ tháng/năm – bộ đọc không đoán kỳ"
    elif not khach:
        h["viec"], h["vi_sao"] = "bo_qua", "không có dòng khách nào có tên hoặc có tiền"
    elif ma.upper() in da_co:
        h["viec"], h["vi_sao"] = "nap_lai", "đã có sổ tháng này – nạp lại sẽ THAY phần của lô, không nhân đôi"
    else:
        h["viec"] = "tao_moi"
    return h


def kiem_lo(db, rows: list[dict]) -> dict:
    """CỬA SOÁT — KHÔNG ghi một dòng nào."""
    da_co = _ma_da_co(db)
    hang = [_mot_hang(d, da_co) for d in rows]

    # CÙNG MỘT TỆP GỬI HAI LẦN TRONG MỘT LÔ. Mã sổ gắn với TÊN TỆP nên hai tệp khác nhau không còn
    # đụng nhau (xem `ma_chuyen`) — chỉ đúng một tệp gửi trùng mới rơi vào đây, và chỉ lần đầu được
    # lần đầu. Vẫn phải NÓI RA và TRỪ RA khỏi tổng: bảng nói "sẽ nạp 6" rồi ra 4 là bảng nói dối,
    # và lần sau không ai tin nó nữa. Đây chính là chỗ bản đầu sai — nó nói ra mà không trừ ra.
    thay: dict[str, str] = {}
    for h in hang:
        if h["viec"] not in ("tao_moi", "nap_lai") or not h["ma"]:
            continue
        k = h["ma"].upper()
        if k in thay:
            h["trung_trong_lo"] = True
            h["vi_sao"] = (f"cùng một tệp với {thay[k]!r} trong lô này – chỉ lần ĐẦU được ghi, "
                           f"tiền của dòng này KHÔNG cộng thêm")
        else:
            thay[k] = h["tep"]

    # Tệp trùng bị TRỪ khỏi mọi con số tổng, không chỉ bị ghi chú.
    lam = [h for h in hang if h["viec"] in ("tao_moi", "nap_lai") and not h.get("trung_trong_lo")]
    bo = [h for h in hang if h["viec"] == "bo_qua"]
    tr = sum(1 for h in hang if h.get("trung_trong_lo"))
    thu = round(sum(h["thu"] for h in lam), 2)
    chi = round(sum(h["chi"] for h in lam), 2)
    cho = sum(h["cho_ty_gia"] for h in lam)
    tien_cho = round(sum(h["tien_cho_ty_gia"] for h in lam), 2)
    khach = sum(h["so_khach"] for h in lam)

    # Tên người bán của cả lô – để người duyệt thấy TRƯỚC là bao nhiêu cái tên sẽ phải gán.
    dem_ban = PD.dem_nguoi_ban([{"khach": _khach_cho_phieu(d)} for d in rows])
    chua_gan = sum(1 for t in dem_ban if KN.tra_so(db, t) is None)
    khong_ten = sum(1 for d in rows for x in _khach_cho_phieu(d) if not x["sale"])

    la = sorted({c for h in hang for c in h["cot_khong_nhan_ra"]})
    return {
        "so_dong": len(rows),
        "da_nap": len(lam),
        "da_co": sum(1 for h in hang if h["viec"] == "nap_lai"),
        "dong_loi": len(bo),
        "dem": {"tao_moi": sum(1 for h in hang if h["viec"] == "tao_moi"),
                "nap_lai": sum(1 for h in hang if h["viec"] == "nap_lai"),
                "bo_qua": len(bo), "trung_trong_lo": tr,
                "so_khach": khach, "so_nguoi_ban": len(dem_ban),
                "nguoi_ban_chua_gan": chua_gan, "dong_khong_ten_nguoi_ban": khong_ten},
        "tien": {"thu": thu, "chi": chi,
                 "lai": None if cho else round(thu - chi, 2),
                 "so_khoan_cho_ty_gia": cho, "tien_goc_cho_ty_gia": tien_cho},
        "cot_khong_nhan_ra": la,
        "chi_tiet": hang,
        "ghi_chu": (
            f"XEM TRƯỚC – chưa ghi gì. Sẽ nạp {len(lam)} bảng tháng · {khach} dòng khách · "
            f"thu {thu:,.0f} đ · chi {chi:,.0f} đ"
            + (f" · LÃI CHƯA TÍNH ĐƯỢC: {cho} khoản ngoại tệ chờ tỷ giá "
               f"(gốc {tien_cho:,.2f}) – khai tỷ giá ở Sổ tỷ giá (/ty-gia) rồi mới có lãi. "
               if cho else f" · lãi {thu - chi:,.0f} đ. ")
            + (f"{tr} tệp dùng chung sổ với tệp khác trong lô. " if tr else "")
            + (f"{len(bo)} tệp KHÔNG nạp được. " if bo else "")
            + f"{len(dem_ban)} tên người bán, {chua_gan} tên CHƯA gán được tài khoản"
            + (f" và {khong_ten} dòng tệp không ghi tên ai" if khong_ten else "")
            + ". Doanh thu của chúng vẫn vào công ty nhưng KHÔNG vào chỉ tiêu của ai – gán tên ở "
              "màn hình người bán rồi bấm gán lại."
            + (f" Cột có tiền mà bộ đọc không biết THU hay CHI: {', '.join(la)} – KHÔNG cộng vào "
               f"đâu cả, người lập cần đặt lại tên cột." if la else "")),
    }


def _ghi_mot(db, d: dict, tour_id: int, boi: str) -> dict:
    """Ghi một bảng tháng lên một chuyến đã có. Trả về những thứ KHÔNG ghi được."""
    from app.models.lop3_tour import BookingKhach
    from app.models.vietrip import TourCostLine

    _xoa_phan_cua_nguon(db, tour_id)
    bao = {"mat_dong_khach": 0, "so_dong_chi": 0, "so_dong_cho_ty_gia": 0}

    khach = _khach_cho_phieu(d)
    kq = PD.sinh(db, tour_id, khach, boi)
    if kq.get("loi"):
        # KHÔNG ghi một nửa. Chuyến có dòng chi mà không có dòng khách là một khoản lỗ bằng đúng chi
        # phí, và con số ấy cộng thẳng vào lãi gộp toàn công ty.
        return {**bao, "mat_dong_khach": len(khach), "vi_sao_mat": kq["loi"], "ghi_duoc": False}

    theo_ten = kq["theo_ten_nguoi_ban"]
    bao["so_phieu_dat"] = kq["so_phieu"]
    bao["chua_gan_nguoi_ban"] = kq["chua_gan_dong"]
    bao["tien_chua_gan"] = kq["chua_gan_tien"]

    stt = 0
    line = 0
    for x in khach:
        bid = theo_ten.get(x["sale"])
        if bid is None:      # không thể xảy ra – phiếu dựng từ chính tập tên này
            bao["mat_dong_khach"] += 1
            continue
        stt += 1
        db.add(BookingKhach(tour_id=tour_id, booking_id=bid, stt=stt,
                            ho_ten=x["ho_ten"][:200], gia_ban=x["tong_thu"],
                            nguoi_sua=NGUON, sua_luc=datetime.now()))

        g = x["_goc"]
        doi_tac = (g.get("doi_tac") or "")[:200]
        mo_ta_khach = x["ho_ten"][:60]

        # DÒNG CHI VND – mỗi khoản một dòng, giữ nguyên nhãn cột của tệp. Gộp lại thành một số là
        # mất cái mà Điều hành đọc bảng này để tìm: phí nào của ai.
        for k in g.get("khoan_chi") or []:
            so = float(k.get("so_tien") or 0)
            if not so:
                continue
            line += 1
            db.add(TourCostLine(
                tour_id=tour_id, line_no=line,
                description=f"{k.get('khoan') or '(không ghi)'} – {mo_ta_khach}"[:200],
                nhom=(g.get("dich_vu") or d.get("loai_dich_vu") or "")[:80] or None,
                supplier_name=doi_tac, qty=1, coef=1,
                actual=so, budget=None,
                source=NGUON, status="hd", updated_by=(boi or NGUON)[:50]))
            bao["so_dong_chi"] += 1

        # DÒNG CHI NGOẠI TỆ – giữ SỐ GỐC, `ty_gia` và `actual` để RỖNG. Xem ghi chú đầu tệp: rỗng
        # nghĩa là chưa ai biết nó bằng bao nhiêu đồng, không phải bằng không.
        for k in g.get("ngoai_te") or []:
            so = float(k.get("so_tien_goc") or 0)
            if not so:
                continue
            line += 1
            db.add(TourCostLine(
                tour_id=tour_id, line_no=line,
                description=f"{k.get('khoan') or '(không ghi)'} – {mo_ta_khach}"[:200],
                nhom=(g.get("dich_vu") or d.get("loai_dich_vu") or "")[:80] or None,
                supplier_name=doi_tac, qty=1, coef=1,
                tien_te=(k.get("tien_te") or "")[:3] or None, so_tien_goc=so,
                ty_gia=None, ngay_ty_gia=None,
                actual=None, budget=None,
                note="CHỜ TỶ GIÁ – khai ở Sổ tỷ giá (/ty-gia) theo ngày chi thật"[:200],
                source=NGUON, status="hd", updated_by=(boi or NGUON)[:50]))
            bao["so_dong_chi"] += 1
            bao["so_dong_cho_ty_gia"] += 1

    bao["ghi_duoc"] = True
    return bao


def nap_lo(db, rows: list[dict], boi: str, ten_tep: str = "",
           bo_qua_dong_loi: bool = False) -> dict:
    """CỬA GHI.

    `bo_qua_dong_loi` ở đây KHÔNG nới gì cả, và cố ý thế: tệp không tìm được hàng tiêu đề thì không
    có cách nào đọc ra dòng khách, tệp không nói tháng nào thì không có kỳ để gán. Không có lối tắt
    cho hai thứ đó — phải sửa tệp.
    """
    from app.models.core import Tour
    from app.services import rules as R
    from app.services.intake_tao_chuyen import _tai_khoan_dieu_hanh

    kq = kiem_lo(db, rows)
    nguoi, ten_tk = _tai_khoan_dieu_hanh(db)
    if nguoi is None:
        return {**kq, "da_nap": 0,
                "message": (f"KHÔNG nạp gì cả: không tìm thấy tài khoản {ten_tk!r} để đứng tên sổ "
                            f"tháng và các phiếu chưa gán được người bán. Không có chỗ đỗ thì "
                            f"doanh thu sẽ rơi vào một nhân viên thật — nên dừng ở đây.")}

    da_co = _ma_da_co(db)
    xong, hong = [], []
    # Đi theo ĐÚNG bảng xem trước, không tính lại: tính lại là hai bộ luật cho cùng một quyết định,
    # và chúng sẽ lệch nhau đúng vào hôm có một tệp lạ. `chi_tiet` cùng thứ tự với `rows`.
    for d, h in zip(rows, kq["chi_tiet"]):
        if h["viec"] == "bo_qua":
            continue
        if h.get("trung_trong_lo"):
            # Cùng một tệp gửi hai lần: chỉ lần ĐẦU được ghi. Bảng xem trước đã trừ nó ra
            # khỏi tổng, nên ở đây cũng không được đếm — hai chỗ phải nói cùng một con số.
            continue
        ma = h["ma"]
        tour_id = da_co.get(ma.upper())
        if tour_id is None:
            tn = _thang_nam(d)
            ngay = _ngay_bang(d)
            # TÊN mang TÊN TỆP. Mã sổ có đuôi băm cho máy phân biệt, còn người đọc thì đọc ở đây —
            # và cũng là chỗ duy nhất trả lời được "sổ này đến từ tệp nào" mà không phải tra bảng.
            t = Tour(code=ma, tour_type="non_package",
                     name=(f"{LOAI_TEN.get(h['loai'], 'Dịch vụ lẻ')} tháng {tn[1]:02d}/{tn[0]} · "
                           f"{h['tep']}")[:200],
                     start_date=ngay, end_date=ngay,
                     operator_id=nguoi.id,
                     planned_pax=h["so_khach"],
                     status=TRANG_THAI,
                     hinh_thuc=None,      # ô quyết định phép tính – để người khai, xem cửa tạo chuyến
                     confirmed_by=NGUON, approved_by=NGUON)
            db.add(t)
            db.flush()
            tour_id = t.id
            da_co[ma.upper()] = tour_id

        bao = _ghi_mot(db, d, tour_id, boi)
        if not bao.get("ghi_duoc"):
            hong.append({"tep": h["tep"], "ma": ma, "vi_sao": bao.get("vi_sao_mat") or "không ghi được"})
            continue
        xong.append({"tep": h["tep"], "ma": ma, **{k: v for k, v in bao.items() if k != "ghi_duoc"}})

    db.flush()
    R.audit(db, boi, "", "nap_bang_thang_dich_vu_le", f"lo:{ten_tep or len(rows)}",
            after={"so_bang": len(xong), "so_khach": sum(x.get("so_phieu_dat", 0) for x in xong),
                   "thu": kq["tien"]["thu"], "chi": kq["tien"]["chi"],
                   "cho_ty_gia": kq["tien"]["so_khoan_cho_ty_gia"]})

    cho = sum(x.get("so_dong_cho_ty_gia", 0) for x in xong)
    chua = sum(x.get("chua_gan_nguoi_ban", 0) for x in xong)
    tien_chua = round(sum(x.get("tien_chua_gan", 0) for x in xong), 2)
    return {
        **kq,
        "da_nap": len(xong), "hong": hong, "chi_tiet_nap": xong,
        "tai_khoan_do": f"{nguoi.username} (id {nguoi.id})",
        "message": (
            f"Đã nạp {len(xong)} bảng tháng · {sum(x.get('so_phieu_dat', 0) for x in xong)} phiếu "
            f"đặt theo người bán · {sum(x.get('so_dong_chi', 0) for x in xong)} dòng chi. "
            + (f"{cho} dòng chi ĐỂ RỖNG số VND vì chờ tỷ giá – tổng chi đang đọc THIẾU đúng chừng "
               f"ấy, khai tỷ giá ở Sổ tỷ giá (/ty-gia) rồi mới đủ. " if cho else "")
            + (f"{chua} dòng khách ({tien_chua:,.0f} đ) chưa gán được người bán, đang đỗ ở phiếu "
               f"đứng tên {nguoi.username} với counts_for_target = False – doanh thu vẫn là của "
               f"công ty, KHÔNG vào chỉ tiêu của ai. Gán tên ở màn hình người bán rồi bấm gán lại. "
               if chua else "")
            + (f"{len(hong)} bảng KHÔNG ghi được." if hong else "")),
    }


def bo_nap(_c) -> dict:
    """Khai bộ nạp. `_c` là hàm khai cột CỦA KHUNG – nhận từ intake.py, không tự viết lại."""
    return {
        "bang_thang_dich_vu_le": {
            "bang_dich": "bookings",
            # Cửa này còn ghi ba bảng nữa. Khai ở đây không phải cho đẹp: phép kiểm "mọi bảng phải
            # có một cửa" (ks_cua_nhap) đọc SỐNG từ chỗ này.
            "bang_phu": ("tours", "booking_khach", "tour_cost_lines"),
            "phong_ban": "dieu_hanh",
            "lo": True,
            "ten": "Bảng tháng DỊCH VỤ LẺ (visa / land / vé / combo) T1–T6/2026",
            "mo_ta": (
                "49 tệp mà cửa 'Tạo CHUYẾN từ kho cũ' để ra ngoài vì chúng KHÔNG phải một chuyến. "
                "Đúng — nhưng không phải một chuyến thì cũng không có nghĩa là không phải tiền. Đo "
                "ngày 16/9/2026 trên đúng 49 tệp ấy: 672 dòng khách, thu 10.294.415.565 đ, chi "
                "8.011.224.547 đ. Ngần ấy tiền đứng ngoài hệ vì thiếu MỘT CÁI CỬA.\n\n"
                "MỘT TỆP = MỘT SỔ DỊCH VỤ LẺ CỦA MỘT THÁNG, mang mã DVL-<loại><tháng><năm> và loại "
                "'non_package' — đúng loại mà màn hình /non-package vẫn dùng cho visa, vé, land bán "
                "lẻ. Cửa này KHÔNG dựng chuyến ma: 'VISA LẺ THÁNG 3' không phải một chuyến đi, và "
                "nó không được ghi như một chuyến đi.\n\n"
                "CỘT SALES ghi TÊN NGƯỜI, không ghi mã nhân viên. Cửa này dùng lại sổ gán người bán "
                "đã có (màn hình người bán): mỗi người bán một phiếu đặt, tên chưa gán được thì "
                "phiếu đứng tên tài khoản điều hành khoá với counts_for_target = False — doanh thu "
                "vẫn là của công ty, nhưng KHÔNG vào chỉ tiêu của bất kỳ ai. Gán bừa vào tài khoản "
                "là đụng vào thưởng của người thật.\n\n"
                "NGOẠI TỆ KHÔNG ĐƯỢC TỰ QUY ĐỔI. Khoản ngoại tệ ghi số gốc và đồng tiền, để tỷ giá "
                "RỖNG và số VND RỖNG. Tổng chi vì thế đọc THIẾU đúng chừng ấy — đó là sự thật, và "
                "cửa này nói ra ở mọi bản trả về. Người lập vào Sổ tỷ giá (/ty-gia) khai tỷ giá của "
                "NGÀY CHI THẬT kèm chứng từ, rồi máy mới nhân. Số VND sẵn trong tệp chỉ để đối "
                "chiếu: không ai biết tỷ giá ấy của ngày nào, lấy ở đâu.\n\n"
                "TỔNG CỘNG TỪ DÒNG, KHÔNG CHÉP Ô TỔNG CỦA TỆP. Đo được một tệp có ô tổng là "
                "=SUM(H6:H52) trong khi bảng chạy tới hàng 55 — ba khách, 19.970.000 đ nằm ngoài "
                "vùng cộng. Chép ô tổng là chép luôn cái sót. Chỗ lệch được NÓI RA, không bỏ im.\n\n"
                "NẠP LẠI THÌ THAY, không nhân đôi: xoá phần của lô trên sổ tháng ấy rồi ghi lại. "
                "Dòng ai đó thêm tay bằng cửa khác không bị cuốn theo."),
            "khoa_chong_trung": "Mã sổ tháng (DVL-<loại><tháng><năm>) – nạp lại thì THAY phần của lô",
            "cot": [
                _c("ten_khach", "Tên khách", vi_du="NGUYỄN VĂN A",
                   ghi_chu="đọc từ cột TÊN KHÁCH/HỌ TÊN của bảng. Dòng không tên mà CÓ TIỀN vẫn giữ"),
                _c("sale", "Người bán", vi_du="HẢI ĐĂNG",
                   ghi_chu="TÊN NGƯỜI, không phải mã. Chưa gán được tài khoản thì doanh thu KHÔNG "
                           "vào chỉ tiêu của ai – gán ở màn hình người bán"),
                _c("doi_tac", "Đối tác / nhà cung cấp"),
                # CỘT BẮT BUỘC DUY NHẤT, và bắt buộc ở mức MỘT DÒNG chứ không ở mức một ô: dòng
                # không có tiền thu thì không phải một khách, nó là dòng trắng ngăn giữa hai nhóm —
                # và cửa này bỏ đúng những dòng ấy (xem `_khach_cho_phieu`). Ngược lại, dòng CÓ
                # tiền mà tệp quên ghi tên khách thì VẪN GIỮ: bỏ nó là mất doanh thu công ty thu
                # thật, và mất lặng vì mọi tổng vẫn cân trên phần còn lại.
                _c("tong_thu", "Tổng thu", True, kieu="so", vi_du="6790000",
                   ghi_chu="lấy ô 'Tổng thu' khi bảng có; không có thì CỘNG các cột thu. Dòng "
                           "không có tiền thu là dòng trắng, không phải một khách"),
                _c("tong_chi", "Tổng chi", kieu="so",
                   ghi_chu="luôn CỘNG TỪ CÁC CỘT CHI. Ô tổng của tệp chỉ dùng để đối chiếu"),
                _c("ty_gia", "Tỷ giá", kieu="so",
                   ghi_chu="KHÔNG đọc vào. Khoản ngoại tệ giữ số gốc và chờ tỷ giá khai ở /ty-gia"),
            ],
            "kiem": kiem_lo, "nap": nap_lo,
            "kiem_lo": kiem_lo, "nap_lo": nap_lo, "doc_tep": doc_tep_lo,
        },
    }


def vai_tro(QUAN_TRI: tuple) -> dict:
    """Ai bấm được nút nạp.

    Giống cửa nạp kho cũ chứ không giống cửa tạo chuyến: ở đây CÓ tiền, và Kế toán giữ bản đối chiếu
    H1 để soát tiền. Không mở cho nhân viên Kinh doanh – doanh số của chính họ nằm trong lô này.
    """
    return {"bang_thang_dich_vu_le": QUAN_TRI + ("tp_dh", "ketoan")}
