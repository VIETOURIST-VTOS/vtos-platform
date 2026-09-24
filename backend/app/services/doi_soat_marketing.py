"""Đối soát dữ liệu Marketing — nhóm 2.8. Số của hai bên có khớp nhau không.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO NHÓM NÀY LÀM SAU CÙNG, VÀ VÌ SAO NÓ KHÔNG TỰ TÍNH LẠI GÌ
═══════════════════════════════════════════════════════════════════════════════════════════════
Anh Tuấn duyệt thứ tự 23/9/2026: 2.7 trước, rồi 2.6, cuối cùng 2.8. Lý do 2.8 đứng cuối: nó là
bàn cân, mà bàn cân chỉ có nghĩa khi đã có hai vật để đặt lên.

Nên tệp này KHÔNG có một phép tính doanh thu, tỷ lệ chốt hay chi phí nào của riêng nó. Nó gọi
`dong_gop_marketing.thang()` và `chuyen_doi_lead.*`, rồi đặt kết quả cạnh những con số mà NGƯỜI
DÙNG đã tự khai, và chỉ ra chỗ hai bên nói khác nhau. Một bàn cân tự sinh ra vật để cân là một
bàn cân vô nghĩa.

═══════════════════════════════════════════════════════════════════════════════════════════════
HAI NƠI CÙNG GHI CHI PHÍ MARKETING, VÀ TRƯỚC VÒNG NÀY KHÔNG AI ĐẶT CHÚNG CẠNH NHAU
═══════════════════════════════════════════════════════════════════════════════════════════════
    `lead_channel_stats.cost`   chi phí theo KÊNH, Marketing khai khi nhập số lead hằng tháng
    `mkt_budget_lines.amount`   chi phí theo HẠNG MỤC (và từ TC-77, theo CHIẾN DỊCH)

Hai sổ ghi cùng một khoản tiền theo hai trục khác nhau. Chúng KHÔNG buộc phải bằng nhau — một
bên có thể chỉ ghi phần chi quảng cáo, bên kia ghi cả chi sự kiện và nhân sự thuê ngoài. Nhưng
chênh lệch phải HIỆN RA và phải có người giải thích, chứ không phải mỗi báo cáo lấy một sổ rồi
hai báo cáo ra hai con số.

TỆP NÀY KHÔNG CHỌN BÊN NÀO ĐÚNG. Nó in cả hai, in phần chênh, và dừng ở đó. Chọn hộ một bên là
đúng cái việc mà nhóm 2.8 sinh ra để ngăn.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA CHỖ DỄ NÓI DỐI BẰNG SỐ, ĐÃ CHẶN SẴN
═══════════════════════════════════════════════════════════════════════════════════════════════
MỘT — "KHÔNG CHÊNH" KHÁC "CHƯA AI KHAI". Kỳ mà Marketing chưa khai số lead nào thì phần chênh là
CHƯA XÁC ĐỊNH, không phải 0. Trả 0 ở đây là báo cáo một sự khớp nhau chưa từng được kiểm.

HAI — TRÙNG THEO SỐ ĐIỆN THOẠI KHÁC TRÙNG THEO DẤU VÂN TAY. Đường nạp Marketing đã có phép chống
trùng bằng `dau_van_tay` (xem `intake_marketing.py`). Hai lead cùng số điện thoại là chuyện BÌNH
THƯỜNG — một khách hỏi hai tour khác nhau là hai lead thật. Hai lead cùng DẤU VÂN TAY mới là
trùng thật, và nếu tìm thấy thì nghĩa là phép chống trùng đã rò. Hai con số ấy nằm ở hai dòng
riêng, không gộp.

BA — SỐ ĐÃ CHỐT CÒN ĐỔI SAU KHI KỲ ĐÃ KHÉP, và đó không phải lỗi. Quy tắc `overview-v1` Chủ tịch
ký 14/9/2026 tính cả phần chốt ở các kỳ SAU, nên tỷ lệ của tháng 7 còn tăng vào tháng 9. Mục
2.8.3 tồn tại chính vì điều đó: chụp lại số tại thời điểm chốt, rồi chỉ ra nó đã trôi bao nhiêu —
để người đọc biết con số đang đổi VÌ SAO, thay vì nghi có ai sửa sổ.
"""
from datetime import datetime

from sqlalchemy import select

from app.models.bao_cao_luu import BaoCaoLuu
from app.models.core import Booking
from app.models.crm import Lead, LeadChannelStat
from app.services import chuyen_doi_lead as CD
from app.services import dong_gop_marketing as DG
from app.services import rules as R

# `kind` dùng cho bảng `bao_cao_luu` — bảng SẴN CÓ, dùng chung với báo cáo phòng và xu hướng.
# Dựng một bảng chụp số thứ hai cho riêng Marketing là cách chắc chắn để sau này lịch sử của một
# kỳ nằm ở hai chỗ và không chỗ nào đủ.
KIND = "mkt"
PHAM_VI = "marketing"


def _so_lead(db, ky: str) -> dict:
    """Sổ lead thực của kỳ: đếm DÒNG và đếm SỐ ĐIỆN THOẠI, hai đơn vị không gộp.

    Nhãn phải gọi đúng tên "số điện thoại khác nhau", KHÔNG viết "số khách" — hai người chung một
    số đếm thành một, một người đổi số đếm thành hai. Cùng cách gọi đã chốt 14/9/2026.
    """
    ds = list(db.execute(select(Lead).where(Lead.lead_month == ky)).scalars())
    theo_kenh: dict[str, dict] = {}
    for l in ds:
        k = theo_kenh.setdefault(l.channel or "(không ghi)",
                                 {"kenh": l.channel or "(không ghi)", "so_dong": 0, "sdt": set()})
        k["so_dong"] += 1
        if l.phone:
            k["sdt"].add(l.phone)
    return {k: {"kenh": v["kenh"], "so_dong": v["so_dong"], "so_sdt": len(v["sdt"])}
            for k, v in theo_kenh.items()}


def doi_chieu(db, ky: str) -> dict:
    """2.8.2 — đặt ba con số cạnh nhau: lead, doanh thu truy được nguồn, và chi phí.

    Không chọn bên nào đúng. In cả hai sổ, in phần chênh, dừng ở đó.
    """
    thuc = _so_lead(db, ky)
    khai = {s.channel: s for s in db.execute(
        select(LeadChannelStat).where(LeadChannelStat.lead_month == ky)).scalars()}

    kenh = sorted(set(thuc) | set(khai))
    dong = []
    for k in kenh:
        t = thuc.get(k)
        s = khai.get(k)
        so_khai = s.leads if s else None
        so_that = t["so_dong"] if t else 0
        dong.append({
            "kenh": k,
            "so_lead_so_sach": so_that,
            "so_sdt_so_sach": t["so_sdt"] if t else 0,
            "so_lead_khai_bao": so_khai,
            # RỖNG KHÁC KHÔNG — xem chỗ dễ nói dối số MỘT ở đầu tệp.
            "lech_lead": (so_that - so_khai) if so_khai is not None else None,
            "chi_theo_kenh_khai": float(s.cost) if (s and s.cost is not None) else None,
            "khai_luc": s.updated_at.isoformat(timespec="seconds") if s and s.updated_at else "",
            "khai_boi": s.updated_by if s else "",
        })

    # HAI SỔ CHI PHÍ. Gọi lại máy của nhóm 2.7 để lấy sổ chi; không đếm lại.
    #
    # ĐỔI NGÀY 24/9/2026: vế thứ nhất trước đây là `tong_chi`, mà con số ấy hoá ra là DỰ TOÁN chứ
    # không phải tiền đã tiêu (lỗi của TC-77, xem dong_gop_marketing). Nay lấy `da_chi_tong` —
    # tiền ĐÃ tiêu theo đề nghị chi. Phép so mới có nghĩa hơn hẳn: hai sổ cũ là "định tiêu" so với
    # "khai đã tiêu theo kênh", tức so hai thứ khác loại và phần lệch không nói lên điều gì.
    #
    # Dự toán KHÔNG biến mất, nó xuống làm con số thứ ba để đọc kèm: một kỳ mà đã chi thấp hơn hẳn
    # dự toán thì phần lệch với sổ kênh có thể chỉ là tiền chưa tiêu, không phải ai khai sai.
    gop = DG.thang(db, ky)
    chi_da_chi = float(gop["chi_marketing"]["da_chi_tong"])
    chi_du_toan = float(gop["chi_marketing"]["du_toan_tong"])
    chi_theo_kenh = sum(d["chi_theo_kenh_khai"] or 0 for d in dong)
    co_khai_chi = any(d["chi_theo_kenh_khai"] is not None for d in dong)

    return {
        "ky": ky,
        "theo_kenh": dong,
        "tong_lead_so_sach": sum(d["so_lead_so_sach"] for d in dong),
        "tong_lead_khai_bao": (sum(d["so_lead_khai_bao"] or 0 for d in dong)
                               if any(d["so_lead_khai_bao"] is not None for d in dong) else None),
        "hai_so_chi_phi": {
            "theo_de_nghi_chi": chi_da_chi,
            "theo_kenh_khai": chi_theo_kenh if co_khai_chi else None,
            "lech": (chi_da_chi - chi_theo_kenh) if co_khai_chi else None,
            # Con số thứ ba, để đọc kèm chứ KHÔNG đem trừ: nó khác loại với hai số trên.
            "du_toan_ky": chi_du_toan,
            "co_so": "Hai sổ ghi cùng một khoản tiền theo hai trục khác nhau: đề nghị chi ghi theo "
                     "HẠNG MỤC và CHIẾN DỊCH, sổ kênh ghi theo KÊNH. Chúng KHÔNG buộc phải bằng "
                     "nhau — nhưng phần chênh phải có người giải thích, chứ không phải mỗi báo "
                     "cáo lấy một sổ rồi hai báo cáo ra hai con số. Dự toán kỳ in kèm làm nền: "
                     "đã chi thấp hơn hẳn dự toán thì phần lệch có thể chỉ là tiền chưa tiêu.",
        },
        "doanh_thu": {
            "tong": gop["tong_doanh_thu"],
            "truy_duoc_nguon": gop["do_phu"]["truy_duoc_nguon"],
            "chua_ro_nguon": gop["do_phu"]["chua_ro_nguon"],
            "ty_le_truy_duoc": gop["do_phu"]["ty_le"],
        },
        "canh_bao_chua_khai": ("" if any(d["so_lead_khai_bao"] is not None for d in dong) else
                               "Kỳ này Marketing chưa khai số lead kênh nào, nên phần chênh là "
                               "CHƯA XÁC ĐỊNH chứ không phải bằng 0. Khai ở màn hình Khách hàng "
                               "tiềm năng rồi xem lại."),
    }


def trung_va_thieu_nguon(db, ky: str) -> dict:
    """2.8.1 — trùng khách và thiếu nguồn.

    HAI LOẠI TRÙNG, KHÔNG GỘP — xem chỗ dễ nói dối số HAI ở đầu tệp:
      · cùng SỐ ĐIỆN THOẠI  : chuyện bình thường, một khách hỏi hai tour là hai lead thật
      · cùng DẤU VÂN TAY    : trùng thật, và tìm thấy nghĩa là phép chống trùng đã rò
    """
    ds = list(db.execute(select(Lead).where(Lead.lead_month == ky)).scalars())

    theo_sdt: dict[str, list] = {}
    theo_vay: dict[str, list] = {}
    thieu_kenh = []
    for l in ds:
        if l.phone:
            theo_sdt.setdefault(l.phone, []).append(l)
        if l.dau_van_tay:
            theo_vay.setdefault(l.dau_van_tay, []).append(l)
        if not (l.channel or "").strip():
            thieu_kenh.append({"lead_id": l.id, "ma_lead": l.ma_lead or "", "ten": l.name,
                               "phone": l.phone})

    nhieu_sdt = [{"phone": p, "so_lead": len(v),
                  "lead": [{"lead_id": x.id, "ten": x.name, "kenh": x.channel,
                            "trang_thai": x.status} for x in v]}
                 for p, v in theo_sdt.items() if len(v) > 1]
    trung_vay = [{"dau_van_tay": k, "so_lead": len(v),
                  "lead_id": [x.id for x in v]}
                 for k, v in theo_vay.items() if len(v) > 1]

    # Booking chưa truy được nguồn: lấy thẳng từ máy của nhóm 2.7, không đếm lại.
    gop = DG.thang(db, ky)

    return {
        "ky": ky,
        "tong_lead": len(ds),
        "nhieu_lead_cung_sdt": {
            "so_sdt": len(nhieu_sdt),
            "rows": sorted(nhieu_sdt, key=lambda x: -x["so_lead"])[:200],
            "co_so": "Đây KHÔNG phải lỗi: một khách hỏi hai tour khác nhau là hai lead thật. "
                     "Con số này để biết mức nhiễu khi khớp lead với booking theo số điện thoại.",
        },
        "trung_dau_van_tay": {
            "so_nhom": len(trung_vay),
            "rows": trung_vay[:200],
            "co_so": "Đây MỚI là trùng thật. Đường nạp Marketing đã chặn bằng dấu vân tay, nên "
                     "tìm thấy ở đây nghĩa là phép chống trùng đã rò — cần xem lại đường nạp, "
                     "không chỉ xoá dòng.",
        },
        "lead_thieu_kenh": {"so_lead": len(thieu_kenh), "rows": thieu_kenh[:200]},
        "booking_thieu_nguon": {
            "so_booking": gop["do_phu"]["so_booking_chua_ro"],
            "tien": gop["do_phu"]["chua_ro_nguon"],
            "ghi_chu": "Gắn nguồn cho từng booking ở màn hình Đóng góp doanh thu của Marketing.",
        },
    }


# ═══════════════════════════════ 2.8.3 — CHUẨN KỲ VÀ ĐỘ TRÔI ═══════════════════════════════

def _so_cua_ky(db, ky: str) -> dict:
    """Bộ số đại diện của một kỳ. Đây là thứ được chụp lại và đem ra so.

    Chọn ít ô thôi, và chọn đúng những ô người ta sẽ mang đi họp. Chụp cả bảng thì mỗi lần đổi
    một chi tiết vụn vặt cũng báo "đã trôi", và một cảnh báo kêu suốt là một cảnh báo không ai nghe.
    """
    gop = DG.thang(db, ky)
    cd = CD.chuyen_doi_theo_moc(db, ky)
    return {
        "tong_doanh_thu": gop["tong_doanh_thu"],
        "truy_duoc_nguon": gop["do_phu"]["truy_duoc_nguon"],
        # ĐỔI TÊN Ô 24/9/2026 cùng lúc với việc sửa nguồn số. Cố ý ĐỔI TÊN chứ không giữ tên cũ:
        # bản chụp cũ đang giữ DỰ TOÁN dưới tên `chi_marketing`, và nếu tên không đổi thì `do_troi`
        # đem dự toán cũ trừ tiền-đã-chi mới rồi báo một độ trôi không có thật. Tên mới không có
        # trong bản chụp cũ, nên `do_troi` trả RỖNG cho ô ấy — đúng nghĩa "chưa từng chốt số này".
        "chi_marketing_da_chi": gop["chi_marketing"]["da_chi_tong"],
        "tong_lead": cd["tong_lead"],
        "da_chot": cd["da_chot"],
    }


TEN_O = {
    "tong_doanh_thu": "Tổng doanh thu kỳ",
    "truy_duoc_nguon": "Doanh thu truy được nguồn",
    "chi_marketing_da_chi": "Chi Marketing đã chi",
    "tong_lead": "Số lead",
    "da_chot": "Số lead đã chốt",
}


def chot_ky(db, boi, ky: str, ghi_chu: str = "") -> dict:
    """CỬA GHI: chụp lại số của kỳ tại thời điểm này vào bảng `bao_cao_luu`.

    DÙNG LẠI BẢNG SẴN CÓ. `bao_cao_luu` đã phục vụ báo cáo phòng và xu hướng; nó có đúng hình
    dạng cần (kind × kỳ × phạm vi, kèm một khối JSON chỉ tiêu). Dựng bảng chụp số thứ hai cho
    riêng Marketing là cách chắc chắn để sau này lịch sử của một kỳ nằm ở hai chỗ và không chỗ
    nào đủ.

    CHỤP LẠI LÀ GHI ĐÈ BẢN CŨ, có chủ ý: ràng buộc duy nhất của bảng là (kind, ky, pham_vi), nên
    mỗi kỳ giữ đúng MỘT mốc chuẩn. Muốn biết nó từng là gì thì đọc nhật ký nghiệp vụ — mỗi lần
    chốt đều để lại một dòng kèm cả bộ số cũ lẫn bộ số mới.
    """
    so = _so_cua_ky(db, ky)
    cu = db.execute(select(BaoCaoLuu).where(
        BaoCaoLuu.kind == KIND, BaoCaoLuu.ky == ky, BaoCaoLuu.pham_vi == PHAM_VI)).scalars().first()
    truoc = dict(cu.chi_tieu or {}) if cu is not None else None

    if cu is None:
        cu = BaoCaoLuu(kind=KIND, ky=ky, pham_vi=PHAM_VI, pham_vi_ten="Marketing")
        db.add(cu)
    cu.chi_tieu = so
    cu.markdown = (ghi_chu or "").strip()
    cu.tao_boi = boi.username
    cu.tao_luc = datetime.now()

    R.audit(db, boi.username, boi.role, "chot_so_ky_marketing", f"bao_cao_luu:{KIND}:{ky}",
            before=truoc, after={**so, "ghi_chu": (ghi_chu or "").strip()})
    return {"da_ghi": True, "ky": ky, "so": so, "lan_dau": truoc is None,
            "message": f"Đã chốt số kỳ {ky}"}


def do_troi(db, ky: str) -> dict:
    """2.8.3 — số hiện tại đã trôi bao nhiêu so với lúc chốt.

    TRÔI KHÔNG PHẢI LÀ LỖI, và màn hình phải nói ra điều đó. Quy tắc `overview-v1` Chủ tịch ký
    14/9/2026 tính cả phần chốt ở các kỳ SAU, nên lead tháng 7 chốt vào tháng 9 sẽ làm số tháng 7
    tăng lên — đúng ý, không phải ai sửa sổ. Mục này tồn tại để người đọc biết con số đang đổi VÌ
    SAO, chứ không phải để bắt lỗi.
    """
    ban_luu = db.execute(select(BaoCaoLuu).where(
        BaoCaoLuu.kind == KIND, BaoCaoLuu.ky == ky, BaoCaoLuu.pham_vi == PHAM_VI)).scalars().first()
    hien_tai = _so_cua_ky(db, ky)

    if ban_luu is None:
        return {
            "ky": ky, "da_chot": False, "hien_tai": hien_tai, "dong": [],
            "canh_bao": "Kỳ này chưa ai chốt số, nên chưa có mốc để so. Chốt số xong thì lần sau "
                        "mở màn hình này sẽ thấy nó đã trôi bao nhiêu.",
        }

    cu = dict(ban_luu.chi_tieu or {})
    dong = []
    for o, ten in TEN_O.items():
        a = cu.get(o)
        b = hien_tai.get(o)
        dong.append({
            "o": o, "ten": ten, "luc_chot": a, "hien_tai": b,
            # Ô có trong bản chụp cũ nhưng không có trong bộ số hôm nay (hoặc ngược lại) thì để
            # RỖNG, không quy về 0 — quy về 0 là bịa ra một lần trôi chưa từng xảy ra.
            "troi": (b - a) if (isinstance(a, (int, float)) and isinstance(b, (int, float))) else None,
        })
    return {
        "ky": ky, "da_chot": True,
        "chot_luc": ban_luu.tao_luc.isoformat(timespec="seconds") if ban_luu.tao_luc else "",
        "chot_boi": ban_luu.tao_boi or "",
        "ghi_chu": ban_luu.markdown or "",
        "hien_tai": hien_tai,
        "dong": dong,
        "co_troi": any(d["troi"] not in (None, 0) for d in dong),
        "co_so": "Trôi KHÔNG phải là lỗi. Quy tắc overview-v1 (Chủ tịch ký 14/9/2026) tính cả "
                 "phần chốt ở các kỳ SAU, nên số của một kỳ đã khép vẫn còn tăng. Mục này để "
                 "biết nó đổi VÌ SAO, không phải để bắt lỗi.",
    }
