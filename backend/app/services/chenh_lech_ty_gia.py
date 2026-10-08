# -*- coding: utf-8 -*-
"""CHÊNH LỆCH TỶ GIÁ – ĐO TRƯỚC, GHI SỔ SAU (Chủ tịch quyết 09/10/2026).

────────────────────────────────────────────────────────────────────────────────
VÌ SAO TK 413 TRỐNG, VÀ VÌ SAO ĐÓ KHÔNG PHẢI LỖI
────────────────────────────────────────────────────────────────────────────────

TK 413 "Chênh lệch tỷ giá hối đoái" có trong danh mục mà KHÔNG một dòng mã nào ghi vào nó. Nhìn
qua thì giống một chỗ bỏ quên. Soát ra thì không phải:

    TK 413 dùng để ĐÁNH GIÁ LẠI số dư ngoại tệ cuối kỳ. Sổ cái của VTOS không có số dư ngoại tệ
    nào — `JournalLine` chỉ có cột nợ/có bằng VND, và mọi khoản ngoại tệ đã quy đổi NGAY LÚC NHẬP
    (`quyet_toan_lop3.don_gia_vnd` = số gốc × tỷ giá). Không có số dư ngoại tệ thì không có gì để
    đánh giá lại.

Nên 413 ở lại danh mục và ở lại TRỐNG, và dòng này là chỗ ghi lý do — để lần sau không ai nhìn ô
trống rồi "sửa cho đủ" bằng một đường ghi bịa ra cho một nghiệp vụ hệ thống không có.

────────────────────────────────────────────────────────────────────────────────
CHỖ HỎNG THẬT NẰM CHỖ KHÁC, VÀ NÓ ĐANG CHẠY
────────────────────────────────────────────────────────────────────────────────

Một khoản trả đối tác nước ngoài cam kết ở tỷ giá A rồi chi ở tỷ giá B: phần chênh (A−B) × số gốc
là LÃI/LỖ CHÊNH LỆCH TỶ GIÁ ĐÃ THỰC HIỆN, theo chuẩn mực phải vào 635 (lỗ) / 515 (lãi). VTOS không
tách nó ra — nó nằm im trong giá vốn chuyến, nên lãi lỗ từng chuyến đang gánh một khoản không phải
của chuyến.

Bằng chứng không phải suy đoán, nó đã được đo và ghi trong `models/ty_gia.py`: tệp quyết toán UK
mang HAI tỷ giá GBP khác nhau trong CÙNG MỘT TỆP — 36.000 ở sheet chiết tính và 35.944 ở sheet
quyết toán; riêng dòng land 692,34 GBP × 43 khách, 56 đồng chênh ấy là 1.667.155 đ.

────────────────────────────────────────────────────────────────────────────────
TỆP NÀY CHỈ ĐẾM. NÓ KHÔNG SỬA MỘT CON SỐ NÀO
────────────────────────────────────────────────────────────────────────────────

Chủ tịch quyết 09/10/2026: "đo trước, ghi sổ sau". Tách chênh lệch ra 635/515 sẽ ĐỔI LÃI LỖ của
những chuyến đã chốt — việc ấy phải quyết với con số thật trong tay, không quyết mò. Nên tệp này
trả lời ba câu và dừng lại ở đó:

  1. Chuyến nào đang dùng HAI tỷ giá khác nhau cho cùng một đồng tiền (ca UK ở trên).
  2. Dòng nào dùng tỷ giá không khớp sổ tỷ giá của đúng ngày ấy.
  3. (Đồng tiền, ngày) nào đang được dùng mà SỔ TỶ GIÁ CHƯA CÓ — tức danh sách nhân viên phải nhập.

Câu 3 là một CỬA NHẬP chứ không phải một lời than: sổ tỷ giá đã có form cho nhân viên tự nhập kèm
chứng từ (Chủ tịch chốt 16/9/2026). Việc của tệp này là nói ra còn thiếu đúng những ngày nào.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lop3_tour import (KhachChiPhi, TourDoanhThuDong, TourHdvChi, TourPhuongTien,
                                  TourTlCongNo, TourVeKhach, TourVeThanhToan)
from app.models.core import Tour
from app.models.ty_gia import TyGia

TK_CHENH_LECH_DANH_GIA_LAI = "413"
TK_LO_TY_GIA = "635"
TK_LAI_TY_GIA = "515"

# Bảng nào mang ngoại tệ. KHAI RA chứ không dò động, và có phép thử bắt khai đủ: thêm một bảng mang
# cặp cột `tien_te` + `ty_gia` mà quên khai ở đây thì chênh lệch của bảng ấy không ai đếm — và vì
# bộ đếm vẫn in ra số, không ai biết nó đang đếm thiếu.
#
# `goc`: cột SỐ TIỀN NGUYÊN TỆ. None nghĩa là bảng ấy KHÔNG khai rõ cột nào là nguyên tệ — xem
# `goc_ro_rang` ở dưới; với những bảng ấy chỉ đếm được số dòng và độ lệch tỷ giá, không ước tính
# được tiền. Đoán bừa một cột là nguyên tệ rồi nhân lên thì ra một con số sai mà trông rất thật.
BANG_NGOAI_TE: dict[str, dict] = {
    "khach_chi_phi": {"model": KhachChiPhi, "ten": "Chi phí theo khách",
                      "goc": "so_tien_goc", "sl": None, "ngay": "ngay_ty_gia"},
    "tour_doanh_thu_dong": {"model": TourDoanhThuDong, "ten": "Doanh thu theo dòng",
                            "goc": "so_tien_goc", "sl": "so_luong", "ngay": "ngay_ty_gia"},
    "tour_phuong_tien": {"model": TourPhuongTien, "ten": "Phương tiện",
                         "goc": "so_tien_goc", "sl": "so_luong", "ngay": "ngay_ty_gia"},
    "tour_hdv_chi": {"model": TourHdvChi, "ten": "Chi của hướng dẫn viên",
                     "goc": "so_tien_goc", "sl": "so_luong", "ngay": "ngay_ty_gia"},
    # Ba bảng dưới có `tien_te` và `ty_gia` nhưng KHÔNG có cột nào tên `so_tien_goc`. Cột tiền của
    # chúng (`thanh_tien`, `so_tien`) không khai nó đang ở đồng nào — và đó tự nó là một chỗ hở
    # đáng ghi: một cột tiền nằm cạnh một cột `tien_te` mà không nói mình thuộc đồng nào thì người
    # đọc sau phải đoán, và nửa số người sẽ đoán khác nửa còn lại.
    "tour_ve_khach": {"model": TourVeKhach, "ten": "Vé theo khách",
                      "goc": None, "sl": None, "ngay": None},
    "tour_ve_thanh_toan": {"model": TourVeThanhToan, "ten": "Thanh toán vé",
                           "goc": None, "sl": None, "ngay": None},
    "tour_tl_cong_no": {"model": TourTlCongNo, "ten": "Công nợ trưởng đoàn",
                        "goc": None, "sl": None, "ngay": "ngay_ty_gia"},
}


def goc_ro_rang(bang: str) -> bool:
    return BANG_NGOAI_TE[bang]["goc"] is not None


def _la_ngoai_te(r, m) -> bool:
    tt = (getattr(r, "tien_te", None) or "").strip().upper()
    return bool(tt) and tt != "VND"


def _dong_ngoai_te(db: Session):
    """Mọi dòng mang ngoại tệ của mọi bảng, kèm tên bảng. Một vòng quét, nhiều phép đếm dùng chung."""
    for bang, m in BANG_NGOAI_TE.items():
        for r in db.execute(select(m["model"])).scalars():
            if not _la_ngoai_te(r, m):
                continue
            yield bang, m, r


def _tien_vnd(m: dict, r) -> float | None:
    """Ước tính tiền VND của một dòng, CHỈ khi bảng khai rõ cột nguyên tệ. Không rõ thì trả None."""
    if m["goc"] is None:
        return None
    goc = getattr(r, m["goc"], None)
    tg = getattr(r, "ty_gia", None)
    if goc in (None, "") or not tg:
        return None
    sl = 1.0
    if m["sl"]:
        v = getattr(r, m["sl"], None)
        sl = float(v) if v not in (None, "") else 1.0
    return float(goc) * float(tg) * sl


# ====================== 1. HAI TỶ GIÁ TRONG MỘT CHUYẾN ======================

def hai_ty_gia_mot_chuyen(db: Session, tour_id: int | None = None) -> list[dict]:
    """Cùng một chuyến, cùng một đồng tiền, HAI tỷ giá khác nhau. Đây là ca UK.

    Phép đo này KHÔNG cần sổ tỷ giá, không cần ai nhập thêm gì — nó chỉ hỏi dữ liệu đã có một câu
    mà không ai từng hỏi. Nên nó chạy được ngay hôm nay, trên bàn thật, không chờ.

    Hai tỷ giá khác nhau trong một chuyến KHÔNG tự nó là sai: một khoản chi tháng 3 và một khoản
    chi tháng 5 thì tỷ giá phải khác. Cái đáng ngờ là hai tỷ giá khác nhau cho CÙNG MỘT NGÀY, hoặc
    lệch quá xa. Nên hàm trả cả hai: danh sách tỷ giá kèm ngày của từng cái, để người đọc phân biệt
    "khác vì khác ngày" với "khác vì hai người nhớ hai số".
    """
    gom: dict[tuple, dict] = {}
    for bang, m, r in _dong_ngoai_te(db):
        if tour_id is not None and getattr(r, "tour_id", None) != tour_id:
            continue
        tg = getattr(r, "ty_gia", None)
        if not tg:
            continue
        tid = getattr(r, "tour_id", None)
        tt = (r.tien_te or "").strip().upper()
        k = (tid, tt)
        o = gom.setdefault(k, {"tour_id": tid, "tien_te": tt, "ty_gia": {}, "so_dong": 0,
                               "tien_uoc_tinh": 0.0, "co_dong_khong_uoc_tinh_duoc": False,
                               "bang": set()})
        o["so_dong"] += 1
        o["bang"].add(m["ten"])
        ngay = getattr(r, m["ngay"], None) if m["ngay"] else None
        d = o["ty_gia"].setdefault(float(tg), {"ty_gia": float(tg), "so_dong": 0, "ngay": set()})
        d["so_dong"] += 1
        if ngay:
            d["ngay"].add(ngay)
        v = _tien_vnd(m, r)
        if v is None:
            o["co_dong_khong_uoc_tinh_duoc"] = True
        else:
            o["tien_uoc_tinh"] += v

    ma_tour = {t.id: t.code for t in db.execute(select(Tour)).scalars()}
    ra = []
    for o in gom.values():
        if len(o["ty_gia"]) < 2:
            continue
        muc = sorted(o["ty_gia"])
        cac = []
        for tg in muc:
            d = o["ty_gia"][tg]
            cac.append({"ty_gia": tg, "so_dong": d["so_dong"],
                        "ngay": sorted(str(x) for x in d["ngay"])})
        # Cùng một NGÀY mà hai tỷ giá khác nhau là chỗ đáng ngờ nhất: không thể giải thích bằng
        # "khác ngày nên khác giá".
        ngay_dung_chung = set()
        for i, a in enumerate(muc):
            for b in muc[i + 1:]:
                ngay_dung_chung |= (o["ty_gia"][a]["ngay"] & o["ty_gia"][b]["ngay"])
        ra.append({
            "tour_id": o["tour_id"], "ma_tour": ma_tour.get(o["tour_id"], ""),
            "tien_te": o["tien_te"], "so_ty_gia": len(muc), "ty_gia": cac,
            "chenh_ty_gia": round(muc[-1] - muc[0], 6),
            "so_dong": o["so_dong"], "bang": sorted(o["bang"]),
            "tien_uoc_tinh": round(o["tien_uoc_tinh"]),
            "uoc_tinh_thieu": o["co_dong_khong_uoc_tinh_duoc"],
            "cung_ngay_khac_gia": sorted(str(x) for x in ngay_dung_chung),
        })
    ra.sort(key=lambda x: (-len(x["cung_ngay_khac_gia"]), -x["chenh_ty_gia"]))
    return ra


# ====================== 2 & 3. ĐỐI CHIẾU VỚI SỔ TỶ GIÁ ======================

def _so_ty_gia(db: Session) -> dict[tuple[str, date], list[float]]:
    ra: dict[tuple[str, date], list[float]] = {}
    for x in db.execute(select(TyGia)).scalars():
        ra.setdefault(((x.tien_te or "").strip().upper(), x.ngay), []).append(float(x.ty_gia))
    return ra


def doi_chieu_so_ty_gia(db: Session, tour_id: int | None = None) -> dict:
    """Dòng nào lệch sổ, (đồng tiền, ngày) nào sổ chưa có, dòng nào không có ngày để mà đối chiếu.

    Chia làm ba rổ chứ không gộp thành một con số "có vấn đề": ba rổ ứng với ba việc khác nhau của
    ba người khác nhau. Gộp lại thì không ai biết phần nào là việc của mình.
    """
    so = _so_ty_gia(db)
    lech, thieu_so, thieu_ngay = [], {}, []
    ma_tour = {t.id: t.code for t in db.execute(select(Tour)).scalars()}
    for bang, m, r in _dong_ngoai_te(db):
        if tour_id is not None and getattr(r, "tour_id", None) != tour_id:
            continue
        tg = getattr(r, "ty_gia", None)
        tt = (r.tien_te or "").strip().upper()
        ngay = getattr(r, m["ngay"], None) if m["ngay"] else None
        chung = {"bang": bang, "ten_bang": m["ten"], "id": r.id,
                 "tour_id": getattr(r, "tour_id", None),
                 "ma_tour": ma_tour.get(getattr(r, "tour_id", None), ""),
                 "tien_te": tt, "ty_gia": float(tg) if tg else None}
        if not tg:
            continue
        if ngay is None:
            # Không có ngày thì KHÔNG đoán là hôm nay, cũng không đoán là ngày chuyến. Một tỷ giá
            # không gắn ngày là một con số không kiểm được, và nói ra điều đó đúng hơn là chấm cho
            # nó một ngày rồi đối chiếu với ngày mình vừa bịa.
            thieu_ngay.append({**chung, "ly_do": ("bảng này không có cột ngày tỷ giá"
                                                  if m["ngay"] is None else "dòng bỏ trống ngày tỷ giá")})
            continue
        co = so.get((tt, ngay))
        if not co:
            k = f"{tt}|{ngay}"
            o = thieu_so.setdefault(k, {"tien_te": tt, "ngay": str(ngay), "so_dong": 0,
                                        "ty_gia_dang_dung": set()})
            o["so_dong"] += 1
            o["ty_gia_dang_dung"].add(float(tg))
            continue
        if not any(abs(float(tg) - x) < 0.000001 for x in co):
            lech.append({**chung, "ngay": str(ngay), "ty_gia_trong_so": sorted(co),
                         "chenh_gan_nhat": round(min(abs(float(tg) - x) for x in co), 6)})
    return {
        "lech_voi_so": lech,
        "so_chua_co": sorted(({**v, "ty_gia_dang_dung": sorted(v["ty_gia_dang_dung"])}
                              for v in thieu_so.values()),
                             key=lambda x: (x["tien_te"], x["ngay"])),
        "thieu_ngay_ty_gia": thieu_ngay,
    }


# ====================== TỔNG HỢP ======================

def tong_hop(db: Session, tour_id: int | None = None) -> dict:
    hai = hai_ty_gia_mot_chuyen(db, tour_id)
    dc = doi_chieu_so_ty_gia(db, tour_id)
    nghi_nhat = [x for x in hai if x["cung_ngay_khac_gia"]]
    return {
        "tour_id": tour_id,
        "hai_ty_gia_mot_chuyen": hai,
        "so_chuyen_hai_ty_gia": len(hai),
        "so_chuyen_cung_ngay_khac_gia": len(nghi_nhat),
        **dc,
        "so_dong_lech_so": len(dc["lech_voi_so"]),
        "so_cap_so_chua_co": len(dc["so_chua_co"]),
        "so_dong_thieu_ngay": len(dc["thieu_ngay_ty_gia"]),
        "bang_duoc_quet": [{"bang": k, "ten": v["ten"], "uoc_tinh_duoc_tien": goc_ro_rang(k)}
                           for k, v in BANG_NGOAI_TE.items()],
        "tai_khoan": {"danh_gia_lai": TK_CHENH_LECH_DANH_GIA_LAI,
                      "lo": TK_LO_TY_GIA, "lai": TK_LAI_TY_GIA},
        "ghi_chu": (
            "ĐÂY LÀ BẢN ĐO, KHÔNG PHẢI BẢN GHI SỔ — Chủ tịch quyết 09/10/2026 'đo trước, ghi sổ sau'. "
            "Chênh lệch tỷ giá đã thực hiện hiện NẰM TRONG giá vốn chuyến; tách nó ra 635 (lỗ) / 515 "
            "(lãi) theo chuẩn mực sẽ ĐỔI lãi lỗ của những chuyến đã chốt, nên cần chữ ký và cần một "
            "cách không sửa lùi kỳ đã khóa. TK 413 vẫn để trống và đó KHÔNG phải chỗ bỏ quên: 413 "
            "dùng để đánh giá lại số dư ngoại tệ cuối kỳ, mà sổ cái VTOS không có số dư ngoại tệ nào "
            "(mọi khoản đã quy đổi VND ngay lúc nhập). "
            "Thiếu tỷ giá trong sổ thì nhân viên nhập ở màn hình Tỷ giá, có form và chỗ tải chứng từ."),
    }
