# -*- coding: utf-8 -*-
"""SOÁT NGOẠI TỆ TRÊN DÒNG GIÁ VỐN — đo trước khi sửa. Chủ tịch quyết 27/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ TỆP NÀY
═══════════════════════════════════════════════════════════════════════════════════════════════
Bảng `tour_cost_lines` có HAI cửa ghi, và tới ngày 27/9/2026 hai cửa ấy hiểu ô "số tiền gốc" theo
hai nghĩa NGƯỢC NHAU:

    settlement.py::_ngoai_te      so_tien_goc = ĐƠN GIÁ một đơn vị
                                  unit_price = goc × tỷ giá (VND)
                                  actual     = unit_price × số lượng × hệ số

    quyet_toan_lop3.py::/{tid}/chi  so_tien_goc = TỔNG cả dòng
                                    unit_price = giữ nguyên đồng GỐC
                                    actual     = goc × tỷ giá  ← số lượng và hệ số BIẾN MẤT

Đo bằng đúng ví dụ mà chú thích trong `models/vietrip.py` tự nêu — land 692,34 GBP × 43 khách,
tỷ giá 36.000:

    cửa Điều hành : 1.071.742.320 đ
    cửa lớp 3     :    24.924.240 đ
    lệch          : 1.046.818.080 đ  TRÊN MỘT DÒNG

Chủ tịch chốt 27/9/2026: **"số tiền gốc" là ĐƠN GIÁ MỘT ĐƠN VỊ** — một ô đơn giá thì luôn là đơn
giá, đồng nào cũng vậy. Cửa lớp 3 là cửa sai.

═══════════════════════════════════════════════════════════════════════════════════════════════
TỆP NÀY CHỈ ĐO, KHÔNG SỬA MỘT DÒNG DỮ LIỆU NÀO
═══════════════════════════════════════════════════════════════════════════════════════════════
Chủ tịch chọn ĐO TRƯỚC, và đó là thứ tự đúng: sửa hai cửa cho khớp rồi mới đo thì không còn tách
được dòng nào đã ghi sai, vì từ lúc ấy cả hai cửa sinh ra cùng một hình.

Ranh giới 09/9/2026 cũng nằm ở đây: mỗi con số cần một CỬA cho người dùng. Nên phần "nắn lại những
dòng đã ghi sai" KHÔNG nằm trong tệp này. Máy không tự sửa một con số tiền mà không ai bấm — nhất
là khi chỗ sai là "người nhập đã hiểu ô ấy theo nghĩa nào", điều mà chỉ người nhập biết.

═══════════════════════════════════════════════════════════════════════════════════════════════
NĂM NHÓM, VÀ NHÓM THỨ NĂM MỚI LÀ NHÓM TRUNG THỰC
═══════════════════════════════════════════════════════════════════════════════════════════════
  · `dung`                 actual khớp quy ước ĐƠN GIÁ. Không phải sửa.
  · `sai_bo_nhan`          actual khớp quy ước TỔNG — số lượng/hệ số đã bị bỏ. Có số lệch đo được.
  · `thieu_o`              khai ngoại tệ mà thiếu số gốc hoặc tỷ giá → không quy đổi được gì.
  · `khong_khop_ca_hai`    không khớp quy ước nào. Phần lớn là dòng bộ nạp kho cũ ghi thẳng vào
                           bảng (`nap_mau_quyet_toan.py`), không đi qua cửa nào.
  · `khong_phan_biet_duoc` số lượng × hệ số = 1, nên hai quy ước cho RA CÙNG MỘT SỐ.

Nhóm cuối cùng phải đứng riêng chứ không gộp vào `dung`. Những dòng ấy hôm nay không sai, nhưng
cũng KHÔNG chứng minh được người nhập hiểu ô kia theo nghĩa nào — và ngày họ sửa số lượng từ 1 lên
43 thì con số đi sai mà không ai chạm vào ô ngoại tệ. Gộp vào `dung` là tự cho mình một bản đo đẹp
hơn sự thật.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour
from app.models.vietrip import TourCostLine
from app.services.settlement import calc_actual

# Sai số cho phép khi so hai con số tiền. Một đồng: hai cửa đều `round(..., 2)` rồi `round()` ở
# `calc_actual`, nên chênh dưới một đồng là chênh làm tròn, không phải chênh quy ước.
DUNG_SAI = 1.0

NHOM = {
    "dung": "Đúng quy ước đơn giá",
    "sai_bo_nhan": "Ghi theo quy ước TỔNG — số lượng/hệ số bị bỏ",
    "thieu_o": "Khai ngoại tệ mà thiếu số gốc hoặc tỷ giá",
    "khong_khop_ca_hai": "Không khớp quy ước nào",
    "khong_phan_biet_duoc": "Số lượng × hệ số = 1 — hai quy ước cho cùng một số",
}


def _gan(a, b) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= DUNG_SAI


def phep_nhan(l: TourCostLine) -> list[tuple[str, float]]:
    """Những phép nhân mà dòng này CÓ THỂ đã dùng, kèm tên. Thử cả hai, không tin một cột.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    VÌ SAO KHÔNG TIN `cost_kind` — lỗi bắt được ngày 27/9/2026, trong chính bộ soát này
    ═══════════════════════════════════════════════════════════════════════════════════════════
    Bản đầu của `xep_loai` gọi `calc_actual(l.cost_kind or "co_dinh", ...)`, tức tin cột
    `cost_kind` nói đúng dòng ấy đã nhân với số lượng hay chưa. Sai, và sai đúng ở nhóm dòng bộ
    soát sinh ra để bắt:

        `quyet_toan_lop3.py::/{tid}/chi` nhân `đơn giá × số lượng × hệ số` NHƯNG KHÔNG ĐẶT
        `cost_kind`, nên mọi dòng nó ghi đều mang giá trị mặc định của cột là `"co_dinh"` —
        tức cột nói "đừng nhân với số khách" trong khi cửa đã nhân rồi.

    Hệ quả: một dòng lớp 3 ghi ĐÚNG quy ước đơn giá sẽ bị xếp vào `khong_khop_ca_hai`, còn một
    dòng ghi SAI có thể lọt. Chú thích trong `test_nt2` tự nói ra rủi ro ấy trước khi nó xảy ra:
    *"một bộ soát báo sai số lệch còn tệ hơn không có bộ soát — người ta sẽ đi sửa dữ liệu thật
    theo con số nó in ra."*

    Nên bộ soát THỬ CẢ HAI phép nhân và nói ra cái nào khớp. Câu hỏi nó trả lời là *"ô số tiền
    gốc được hiểu là đơn giá hay là tổng"* — không phải *"cột cost_kind khai đúng chưa"*. Hai câu
    ấy khác nhau, và trộn chúng là cách bản đầu đã sai.
    """
    qty, coef = float(l.qty or 0), float(l.coef or 1)
    ra = [("theo_cost_kind", calc_actual(l.cost_kind or "co_dinh", 1.0, qty, coef))]
    # Phép nhân của cửa lớp 3: luôn nhân số lượng, bất kể cost_kind.
    if qty > 0 and not _gan(qty * coef, ra[0][1]):
        ra.append(("nhan_ca_so_luong", round(qty * coef, 6)))
    return ra


def xep_loai(l: TourCostLine) -> dict:
    """Xếp một dòng vào một nhóm, kèm số lệch nếu đo được. CHỈ ĐỌC."""
    goc = float(l.so_tien_goc) if l.so_tien_goc is not None else None
    tg = float(l.ty_gia) if l.ty_gia is not None else None
    if not goc or not tg:
        return {"nhom": "thieu_o", "actual_dung": None, "lech": None, "phep_nhan": ""}

    mot_don_vi = round(goc * tg, 2)                       # VND của MỘT đơn vị
    actual = float(l.actual) if l.actual is not None else None
    ung_vien = [(ten, round(mot_don_vi * n, 2), n) for ten, n in phep_nhan(l)]
    theo_tong = mot_don_vi                                # cách cửa lớp 3 đang ghi số gốc

    # Hai quy ước cho cùng một số khi MỌI phép nhân đều bằng 1 — dòng ấy không chứng minh được gì.
    if all(_gan(n, 1) for _, _, n in ung_vien):
        return {"nhom": "khong_phan_biet_duoc", "actual_dung": theo_tong,
                "lech": 0.0 if _gan(actual, theo_tong) else None, "phep_nhan": "x1"}

    khop = next((u for u in ung_vien if _gan(actual, u[1])), None)
    if khop:
        return {"nhom": "dung", "actual_dung": khop[1], "lech": 0.0, "phep_nhan": khop[0]}

    # Không khớp phép nhân nào → so với quy ước TỔNG. `actual_dung` lấy phép nhân LỚN NHẤT, vì
    # đó là phép nhân mà các cột của chính dòng này mô tả; in kèm tên để người sửa kiểm lại được.
    lon = max(ung_vien, key=lambda u: u[2])
    if _gan(actual, theo_tong):
        return {"nhom": "sai_bo_nhan", "actual_dung": lon[1],
                "lech": round(lon[1] - (actual or 0)), "phep_nhan": lon[0]}
    return {"nhom": "khong_khop_ca_hai", "actual_dung": lon[1],
            "lech": round(lon[1] - (actual or 0)) if actual is not None else None,
            "phep_nhan": lon[0]}


def quy_uoc_don_gia(l: TourCostLine) -> str:
    """Ô `unit_price` của dòng này đang mang nghĩa nào — VND hay đồng gốc.

    Đây là con số thứ hai, độc lập với `actual`, và nó phải đo riêng: màn hình in thẳng
    `unit_price` ra cột "Đơn giá" mà không nói là đồng nào (`settlement.line_out`). Một dòng có
    `actual` đúng mà `unit_price` mang đồng gốc vẫn là một dòng đọc sai trên màn hình.
    """
    goc = float(l.so_tien_goc) if l.so_tien_goc is not None else None
    tg = float(l.ty_gia) if l.ty_gia is not None else None
    up = float(l.unit_price) if l.unit_price is not None else None
    if not goc or not tg or up is None:
        return "khong_do_duoc"
    if _gan(up, round(goc * tg, 2)):
        return "vnd"
    if _gan(up, goc):
        return "dong_goc"
    return "khong_khop_ca_hai"


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# NGOẠI TỆ ẨN — DÒNG NÓI MÌNH LÀ NGOẠI TỆ MÀ Ô `tien_te` BỎ TRỐNG
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
# Thêm 27/9/2026, sau lần đo đầu tiên trên dữ liệu thật.
#
# Lần đo ấy trả về 61 dòng — nhưng câu truy vấn của `bang()` chỉ lấy dòng CÓ ô `tien_te`. Kho quyết
# toán cũ T1–T7/2026 nạp lên bằng bộ nạp riêng, và bộ nạp không phải lúc nào cũng điền được ô ấy:
# đồng tiền nằm trong CÂU MÔ TẢ ("Phí LSQ Phí (CAD) – NGUYEN TUYET NHI"), không nằm trong một cột.
#
# Một dòng như thế thì bộ soát KHÔNG THẤY, và 61 là con số thấp hơn sự thật. Một bộ soát báo thiếu
# còn nguy hơn không có bộ soát: người đọc đóng sổ lại và tưởng đã hết.
#
# Phép dò này CỐ Ý thô — chỉ tìm mã đồng tiền đứng như một từ riêng trong mô tả hoặc tên nhà cung
# cấp. Nó KHÔNG xếp loại và KHÔNG kết luận dòng ấy sai; nó chỉ nói "chỗ này cần người nhìn".
_MA_TIEN = ("USD", "EUR", "AUD", "CAD", "GBP", "JPY", "KRW", "CNY", "SGD", "THB", "TWD", "HKD")
_DO_NGOAI_TE = re.compile(r"(?<![A-Za-z])(" + "|".join(_MA_TIEN) + r")(?![A-Za-z])")


# MÃ ĐỒNG TIỀN TRÙNG VỚI CHỮ VIẾT TẮT TIẾNG VIỆT TRONG TÊN NHÀ CUNG CẤP.
#
# "HKD" là đô la Hồng Kông, và cũng là "HỘ KINH DOANH" — cách gọi loại hình đăng ký kinh doanh
# nằm ngay đầu tên hàng trăm nhà cung cấp: "HKD TÀU DU LỊCH TÚ ÂN", "HKD NHỮNG CHÀNG TRAI".
# Đo ngày 27/9/2026 trên dữ liệu thật: 4 trong 28 dòng bộ dò bắt được là hộ kinh doanh Việt Nam,
# không một đồng ngoại tệ nào.
#
# Một bộ soát báo nhầm thì người ta thôi đọc nó — và lần sau nó báo đúng cũng không ai tin. Nên
# với những mã này, CHỈ tính khi mã nằm trong MÔ TẢ khoản chi (nơi người ta viết phép tính ngoại
# tệ: "800CNY X 4000"), KHÔNG tính khi nó chỉ nằm trong tên nhà cung cấp.
#
# Cái giá phải trả: một khoản chi bằng đô la Hồng Kông mà chỉ lộ ra ở tên NCC sẽ bị bỏ sót. Đổi
# lại là bộ soát không kêu oan bốn lần cho mỗi lần kêu đúng. Vietourist chưa có dòng nào khai
# `tien_te = "HKD"` (đo 27/9/2026: chỉ CAD, USD, AUD), nên đánh đổi này nghiêng hẳn một bên.
_DE_NHAM_TRONG_TEN_NCC = {"HKD"}


def dong_tien_trong_chu(l: TourCostLine) -> str:
    """Mã đồng tiền xuất hiện trong MÔ TẢ hay TÊN NCC của dòng, nếu có. Rỗng là không thấy gì.

    Mô tả xét trước: đó là nơi người nhập viết phép tính ngoại tệ bằng tay.
    """
    m = _DO_NGOAI_TE.search((l.description or "").upper())
    if m:
        return m.group(1)
    m = _DO_NGOAI_TE.search((l.supplier_name or "").upper())
    if m and m.group(1) not in _DE_NHAM_TRONG_TEN_NCC:
        return m.group(1)
    return ""


def bang(db: Session, gioi_han: int = 300) -> dict:
    """Sổ soát. Trả CẢ con số tổng lẫn danh sách dòng — một con số không bấm vào được là một tin đồn."""
    # Mã chuyến, TRẠNG THÁI và NGÀY KHỞI HÀNH. Hai thứ sau không phải trang trí:
    #  · trạng thái quyết định có được sửa dòng hay không — chuyến đã đóng số / Kế toán đã xác
    #    nhận thì KHÔNG ai được nắn lặng lẽ, phải đi qua đường Kế toán trả lại.
    #  · ngày khởi hành là NGÀY TỶ GIÁ Chủ tịch chốt 27/9/2026 dùng cho dòng kho cũ (kho cũ không
    #    mang ngày tỷ giá nào cả). Có nó ở đây thì đếm được cần bao nhiêu cặp (đồng tiền × ngày).
    tt_tour, ngay_tour = {}, {}
    ma_tour = {}
    for t in db.execute(select(Tour)).scalars():
        ma_tour[t.id], tt_tour[t.id], ngay_tour[t.id] = t.code, t.status, t.start_date

    dem = {k: 0 for k in NHOM}
    dem_don_gia = {"vnd": 0, "dong_goc": 0, "khong_khop_ca_hai": 0, "khong_do_duoc": 0}
    tong_lech = 0.0
    rows: list[dict] = []
    tong_dong_ngoai_te = 0
    # Số ngoại tệ CHƯA ĐƯỢC QUY ĐỔI, cộng theo từng đồng tiền. Đây là con số duy nhất nói được quy
    # mô của nhóm `thieu_o`: những dòng ấy không có tỷ giá nên `lech` không đo được, và `tong_lech`
    # của chúng bằng 0 — một bảng chỉ có `tong_lech` sẽ đọc y hệt "không mất gì".
    chua_quy_doi: dict[str, float] = {}
    dem_trang_thai: dict[str, int] = {}
    dem_nguon: dict[str, int] = {}
    ngoai_te_an: list[dict] = []
    dem_tt_chuyen: dict[str, int] = {}
    # Cặp (đồng tiền × ngày khởi hành) cần một dòng trong SỔ TỶ GIÁ thì mới quy đổi được. Đếm CẶP
    # chứ không đếm dòng: 61 dòng của 10 chuyến chỉ cần chừng mươi con số, không phải 61 lần gõ.
    can_ty_gia: set[tuple[str, str]] = set()

    q = select(TourCostLine).where(TourCostLine.tien_te.is_not(None),
                                   TourCostLine.tien_te != "",
                                   TourCostLine.tien_te != "VND")
    for l in db.execute(q.order_by(TourCostLine.tour_id, TourCostLine.line_no)).scalars():
        tong_dong_ngoai_te += 1
        tt = (l.tien_te or "").upper()
        dem_trang_thai[l.status or ""] = dem_trang_thai.get(l.status or "", 0) + 1
        dem_nguon[l.source or ""] = dem_nguon.get(l.source or "", 0) + 1
        # Chưa có tỷ giá thì chưa quy đổi được đồng nào — cộng phần đồng GỐC lại để biết quy mô.
        dem_tt_chuyen[tt_tour.get(l.tour_id, "")] = dem_tt_chuyen.get(tt_tour.get(l.tour_id, ""), 0) + 1
        goc_nt = float(l.so_tien_goc or 0)
        if l.ty_gia is None and goc_nt:
            nk = ngay_tour.get(l.tour_id)
            if nk: can_ty_gia.add((tt, nk.isoformat()))
            nhan = float(l.qty or 0) * float(l.coef or 1) if (l.cost_kind or "co_dinh") == "theo_khach" \
                else float(l.coef or 1)
            chua_quy_doi[tt] = round(chua_quy_doi.get(tt, 0.0) + goc_nt * nhan, 2)
        kq = xep_loai(l)
        dem[kq["nhom"]] += 1
        dem_don_gia[quy_uoc_don_gia(l)] += 1
        if kq["lech"]:
            tong_lech += kq["lech"]
        # Chỉ in ra những dòng CẦN NGƯỜI NHÌN. Dòng đúng không vào danh sách — một bảng soát in cả
        # phần đúng là một bảng không ai đọc hết.
        if kq["nhom"] in ("sai_bo_nhan", "khong_khop_ca_hai", "thieu_o") and len(rows) < gioi_han:
            rows.append({
                "tour": ma_tour.get(l.tour_id, ""), "dong": l.line_no,
                "mo_ta": (l.description or "")[:80], "ncc": (l.supplier_name or "")[:60],
                "nhom": kq["nhom"], "nhom_ten": NHOM[kq["nhom"]],
                "tien_te": l.tien_te, "so_tien_goc": float(l.so_tien_goc or 0),
                "ty_gia": float(l.ty_gia) if l.ty_gia is not None else None,
                "ngay_ty_gia": l.ngay_ty_gia,
                "so_luong": l.qty, "he_so": l.coef, "cach_tinh": l.cost_kind,
                "actual": float(l.actual or 0), "actual_dung": kq["actual_dung"],
                "lech": kq["lech"], "don_gia_dang_mang": quy_uoc_don_gia(l),
                "phep_nhan": kq["phep_nhan"],
                "nguon": l.source, "boi": l.updated_by,
                "trang_thai_dong": l.status,
                "trang_thai_chuyen": tt_tour.get(l.tour_id, ""),
                "ngay_khoi_hanh": ngay_tour.get(l.tour_id),
            })

    # ── Quét NGOẠI TỆ ẨN: dòng KHÔNG khai `tien_te` mà mô tả có mã đồng tiền ──────────────────
    qa = select(TourCostLine).where((TourCostLine.tien_te.is_(None)) | (TourCostLine.tien_te == "")
                                    | (TourCostLine.tien_te == "VND"))
    dem_an: dict[str, int] = {}
    for l in db.execute(qa.order_by(TourCostLine.tour_id, TourCostLine.line_no)).scalars():
        tt = dong_tien_trong_chu(l)
        if not tt:
            continue
        dem_an[tt] = dem_an.get(tt, 0) + 1
        if len(ngoai_te_an) < gioi_han:
            ngoai_te_an.append({
                "tour": ma_tour.get(l.tour_id, ""), "dong": l.line_no,
                "mo_ta": (l.description or "")[:80], "ncc": (l.supplier_name or "")[:60],
                "doan_la": tt, "so_tien_goc": float(l.so_tien_goc or 0),
                "don_gia": float(l.unit_price or 0), "actual": float(l.actual or 0),
                "so_luong": l.qty, "he_so": l.coef, "cach_tinh": l.cost_kind,
                "trang_thai": l.status, "nguon": l.source, "boi": l.updated_by,
                "trang_thai_chuyen": tt_tour.get(l.tour_id, ""),
                "ngay_khoi_hanh": ngay_tour.get(l.tour_id),
            })

    return {
        "tong_dong_ngoai_te": tong_dong_ngoai_te,
        # Dòng NÓI mình là ngoại tệ trong câu chữ mà ô `tien_te` bỏ trống. KHÔNG xếp loại, KHÔNG kết
        # luận sai — chỉ nói "chỗ này cần người nhìn", vì bộ soát phía trên không thấy chúng.
        "ngoai_te_an": {"tong": sum(dem_an.values()), "theo_dong_tien": dem_an,
                        "rows": ngoai_te_an, "cham_tran": len(ngoai_te_an) >= gioi_han},
        "chua_quy_doi": chua_quy_doi,
        "theo_trang_thai": dem_trang_thai, "theo_nguon": dem_nguon,
        "theo_trang_thai_chuyen": dem_tt_chuyen,
        # Cần bấy nhiêu con số trong Sổ tỷ giá là quy đổi được cả nhóm thiếu tỷ giá.
        "can_ty_gia": sorted([{"tien_te": a, "ngay": b} for a, b in can_ty_gia],
                             key=lambda x: (x["tien_te"], x["ngay"])),
        "dem": dem, "nhom_ten": NHOM,
        "don_gia_dang_mang": dem_don_gia,
        "tong_lech": round(tong_lech),
        "rows": rows, "cham_tran": len(rows) >= gioi_han,
        # Lời khai đi cùng con số, không để màn hình tự đặt câu. Sổ rỗng và sổ sạch trông giống hệt
        # nhau trên một bảng chỉ có số 0.
        "luu_y": ("Chưa có dòng giá vốn nào khai ngoại tệ — chưa ai nhập, không phải đã sạch."
                  if tong_dong_ngoai_te == 0 else
                  "Cột `lech` là số tiền dòng ấy THIẾU so với quy ước đơn giá Chủ tịch chốt "
                  "27/9/2026. Máy KHÔNG tự nắn: ô 'số tiền gốc' người nhập hiểu theo nghĩa nào "
                  "thì chỉ người nhập biết, nên mỗi dòng phải có người sửa và ký. "
                  "`chua_quy_doi` là số NGOẠI TỆ của những dòng chưa có tỷ giá — `lech` của chúng "
                  "không đo được nên `tong_lech` KHÔNG bao gồm chúng; đừng đọc `tong_lech` = 0 "
                  "thành 'không mất gì'."),
    }
