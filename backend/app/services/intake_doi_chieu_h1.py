# -*- coding: utf-8 -*-
"""CỬA TẢI BẢN ĐỐI CHIẾU H1/2026 – ghi TỔNG THU và TỔNG CHI mức chuyến.

VÌ SAO CỬA NÀY PHẢI CÓ, VÀ VÌ SAO NÓ LÀ CỬA THỨ BA

Hai cửa trước làm được nửa việc: cửa tạo chuyến dựng khung chuyến, cửa kho cũ đổ dòng chi tiết vào.
Nhưng cả hai đều cố ý KHÔNG ghi tiền ở mức chuyến, vì bộ đọc 604 tệp Excel chỉ rút được **90,7%
doanh thu và 71,1% giá vốn** so với bản đối chiếu Kế toán đã chốt. Ghi `actual_cost` bằng một con số
kém 29% là làm mọi chuyến trông lãi hơn thật gần một phần ba — và con số ấy chảy thẳng lên bảng của
Ban điều hành.

Bản đối chiếu H1 (`DOICHIEU_QUYETTOAN_TOUR_MISA_H1_2026`) là chỗ DUY NHẤT có số đúng ở mức chuyến:
**624 chuyến, 97,5 tỷ doanh thu, 80,9 tỷ giá vốn**, người đã soát và đã đối với MISA. Cửa này nạp
đúng bản ấy.

CẦU NỐI LÀ TÊN TỆP, KHÔNG PHẢI MÃ TOUR

Đo ngày 13/9/2026 trên 624 dòng: chỉ **10 dòng** mang mã tour đúng dạng; 507 dòng chỉ ghép được qua
cột "File quyết toán". Mã tour thì nằm BÊN TRONG tệp Excel, nên bản đối chiếu không tự suy ra được.
Vì vậy cửa tạo chuyến ghi lại `kho_cu_tep_chuyen` (tệp nào đẻ ra chuyến nào), và cửa này tra ngược
qua đó. Ghép được 599/624 dòng (95%).

25 dòng không ghép được không phải lỗi: 14 dòng nguồn là "Báo cáo doanh thu team đoàn" — không có
tệp quyết toán nào cả — và 11 dòng còn lại là tệp ngoài kho 604. Cửa này nêu chúng ra chứ không tạo
chuyến ma cho chúng.

BA CHỐT AN TOÀN

  1. CHỈ ghi đè tiền của chuyến DO LÔ TẠO RA. Chuyến đã có sẵn trong VTOS (nhập từ Vietrip, hoặc do
     người gõ tay) mà đã mang `actual_revenue` thì cửa này KHÔNG đụng — nó xếp vào rổ "cần người xác
     nhận" và nói rõ hai con số để người đọc tự quyết. Đè lên số của hệ đang chạy là loại sai không
     lùi lại được.
  2. Trạng thái chuyến đổi sang **"khoa" (Đã khoá)**, KHÔNG phải "kt_xac_nhan". Hai lý do, và lý do
     thứ hai quan trọng hơn: "kt_xac_nhan" nghĩa là *Kế toán đã xác nhận*, mà không kế toán nào bấm
     cả — máy ghi vào đó là làm hệ thống ghi nhận một chữ ký không ai ký. "khoa" nói đúng sự thật:
     chuyến đã xong, số đã chốt, không còn chờ ai. Và nó tắt đúng hai chỗ sai: chuyến thôi hiện ở
     mục "quá hạn quyết toán" trên bảng Chủ tịch, và bắt đầu vào KPI tháng.
  3. KHÔNG sinh bút toán kế toán. Sổ H1/2026 đã khoá và đã ra báo cáo tài chính bán niên; sinh bút
     toán bây giờ là ghi trùng doanh thu cả nửa năm. `accounting.on_settlement_confirmed` chỉ chạy ở
     đường Kế toán xác nhận thủ công, và cửa này cố ý không đi qua đường ấy.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.services.tao_chuyen_kho_cu import NGUON, khoa_tep

# Tên sheet và nhãn cột của bản đối chiếu. Khai rõ chứ không "lấy sheet đầu tiên": tệp có 6 sheet và
# sheet đầu là bảng tóm tắt, đọc nhầm nó thì ra một bảng số trông hợp lý mà sai hẳn tầng.
SHEET = "DOI CHIEU TUNG TOUR"
TRANG_THAI_SAU_NAP = "khoa"

_COT = {
    "ma_tour": ("MÃ TOUR",),
    "thang": ("THÁNG",),
    "nhom": ("NHÓM",),
    "ten_tep": ("FILE QUYẾT TOÁN",),
    "so_khach": ("SỐ KHÁCH",),
    "tong_thu": ("TỔNG THU (QT)", "TỔNG THU"),
    "tong_chi": ("TỔNG CHI (QT)", "TỔNG CHI"),
}


def _hoa(v) -> str:
    import re
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip().upper()


def _so(v):
    if isinstance(v, (int, float)):
        return float(v)
    if v is None:
        return None
    import re
    t = re.sub(r"[^\d,.\-]", "", str(v)).replace(".", "").replace(",", ".")
    try:
        return float(t) if t not in ("", "-", ".") else None
    except ValueError:
        return None


# =============================================================================================
# Đọc – KHÔNG chạm cơ sở dữ liệu
# =============================================================================================

def doc_tep(noi_dung: bytes, ten_tep: str = "") -> list[dict]:
    """Đọc sheet đối chiếu thành danh sách dòng. Không có sheet ấy thì trả rỗng – không đoán sheet khác."""
    import io

    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(noi_dung), data_only=True, read_only=True)
    if SHEET not in wb.sheetnames:
        wb.close()
        return []
    ws = wb[SHEET]
    g = [list(r) for r in ws.iter_rows(max_col=20, values_only=True)]
    wb.close()

    # Hàng tiêu đề = hàng đầu tiên chứa cả "MÃ TOUR" lẫn một trong hai cột tiền.
    h = None
    for i, row in enumerate(g[:20]):
        o = [_hoa(x) for x in row]
        if any(x in _COT["ma_tour"] for x in o) and any(
                x in _COT["tong_thu"] + _COT["tong_chi"] for x in o):
            h = i
            break
    if h is None:
        return []

    o = [_hoa(x) for x in g[h]]
    vi = {}
    for khoa, nhan in _COT.items():
        vi[khoa] = next((j for j, x in enumerate(o) if x in nhan), None)
    if vi["ma_tour"] is None or vi["tong_thu"] is None:
        return []

    def lay(row, khoa):
        j = vi[khoa]
        return row[j] if (j is not None and j < len(row)) else None

    ra = []
    for row in g[h + 1:]:
        ma = str(lay(row, "ma_tour") or "").strip()
        if not ma:
            continue
        tep = str(lay(row, "ten_tep") or "").strip()
        ra.append({
            "ma_tour": ma[:200],
            "ten_tep_qt": tep[:255],
            # Hai khoá ghép, theo đúng thứ tự ưu tiên dùng ở `_tim_chuyen`.
            "khoa_tep": khoa_tep(tep),
            "khoa_ma": khoa_tep(ma),
            "thang": str(lay(row, "thang") or "").strip()[:10],
            "nhom": str(lay(row, "nhom") or "").strip()[:60],
            "so_khach": _so(lay(row, "so_khach")),
            "tong_thu": _so(lay(row, "tong_thu")),
            "tong_chi": _so(lay(row, "tong_chi")),
            "ten_tep": ten_tep,
        })
    return ra


# =============================================================================================
# Soát – KHÔNG ghi gì
# =============================================================================================

def _tim_chuyen(db, d: dict):
    """Tìm chuyến của một dòng đối chiếu. Ba đường, theo thứ tự chắc chắn giảm dần.

    1. SỔ TỆP↔CHUYẾN theo tên tệp quyết toán  – đường chính, 507/624 dòng đi đường này.
    2. SỔ TỆP↔CHUYẾN theo cột 'Mã tour'        – nhiều dòng ghi tên tệp vào ô mã tour.
    3. MÃ CHUYẾN trong VTOS                    – 10 dòng mang mã thật; cũng bắt được chuyến Vietrip.
    """
    from app.models.core import Tour
    from app.models.kho_cu import KhoCuTepChuyen

    for khoa in (d.get("khoa_tep"), d.get("khoa_ma")):
        if not khoa:
            continue
        s = db.scalars(select(KhoCuTepChuyen).where(KhoCuTepChuyen.khoa_tep == khoa)).first()
        if s is not None and s.tour_id:
            t = db.get(Tour, s.tour_id)
            if t is not None:
                return t, ("so_tep" if khoa == d.get("khoa_tep") else "so_ma")
    ma = (d.get("ma_tour") or "").strip()
    if ma:
        t = db.scalars(select(Tour).where(func.upper(Tour.code) == ma.upper())).first()
        if t is not None:
            return t, "ma_chuyen"
    return None, ""


def _la_chuyen_cua_lo(t) -> bool:
    return getattr(t, "confirmed_by", None) == NGUON and getattr(t, "approved_by", None) == NGUON


def _soat_mot(db, d: dict) -> dict:
    t, duong = _tim_chuyen(db, d)
    cu_thu = float(t.actual_revenue) if (t is not None and t.actual_revenue is not None) else None
    cu_chi = float(t.actual_cost) if (t is not None and t.actual_cost is not None) else None

    if t is None:
        ro, vi_sao = "khong_thay_chuyen", ["không tìm được chuyến nào cho dòng này"]
    elif not _la_chuyen_cua_lo(t) and (cu_thu or cu_chi):
        # Chốt an toàn 1. Chuyến của hệ đang chạy, đã có tiền – máy KHÔNG đè.
        ro, vi_sao = "can_xac_nhan", [
            f"chuyến {t.code} không do lô này tạo và đã có doanh thu {cu_thu or 0:,.0f} / "
            f"giá vốn {cu_chi or 0:,.0f}; bản đối chiếu ghi {d['tong_thu'] or 0:,.0f} / "
            f"{d['tong_chi'] or 0:,.0f}"]
    elif d.get("tong_thu") is None:
        ro, vi_sao = "chan", ["dòng không có tổng thu – không có gì để ghi"]
    else:
        ro, vi_sao = "nap_duoc", []

    return {
        "ten_tep": d.get("ma_tour"), "ma_tour": d.get("ma_tour"),
        "ten_tep_qt": d.get("ten_tep_qt"), "thang": d.get("thang"), "nhom": d.get("nhom"),
        "tour_id": (t.id if t is not None else None),
        "ma_chuyen": (t.code if t is not None else ""),
        "duong_ghep": duong, "cua_lo": bool(t is not None and _la_chuyen_cua_lo(t)),
        "ro": ro,
        "tong_thu": d.get("tong_thu"), "tong_chi": d.get("tong_chi"),
        "thu_dang_co": cu_thu, "chi_dang_co": cu_chi,
        "chan": vi_sao if ro == "chan" else [],
        "can_xac_nhan": vi_sao if ro == "can_xac_nhan" else [],
    }


def kiem_lo(db, rows: list[dict]) -> dict:
    """CỬA SOÁT. KHÔNG ghi một dòng nào."""
    chi_tiet = [_soat_mot(db, d) for d in rows]
    dem = {r: sum(1 for x in chi_tiet if x["ro"] == r)
           for r in ("nap_duoc", "can_xac_nhan", "chan", "khong_thay_chuyen")}
    thu = sum(x["tong_thu"] or 0 for x in chi_tiet if x["ro"] == "nap_duoc")
    chi = sum(x["tong_chi"] or 0 for x in chi_tiet if x["ro"] == "nap_duoc")
    return {
        "so_dong": len(chi_tiet),
        "da_nap": dem["nap_duoc"],
        "da_co": dem["can_xac_nhan"],
        "dong_loi": dem["chan"] + dem["khong_thay_chuyen"],
        "dem": dem, "chi_tiet": chi_tiet,
        "tong_thu_se_ghi": round(thu, 2), "tong_chi_se_ghi": round(chi, 2),
        "ghi_chu": (
            f"XEM TRƯỚC – chưa ghi gì. {dem['nap_duoc']} dòng ghép được chuyến và sẽ ghi "
            f"{thu:,.0f} đ doanh thu / {chi:,.0f} đ giá vốn ở mức chuyến. "
            f"{dem['can_xac_nhan']} dòng rơi vào chuyến ĐÃ CÓ số của nguồn khác – máy không đè, "
            f"phải người xác nhận. {dem['khong_thay_chuyen']} dòng không tìm được chuyến "
            "(phần lớn là dòng lấy từ 'Báo cáo doanh thu team đoàn', vốn không có tệp quyết toán). "
            "Cửa này KHÔNG sinh bút toán kế toán – sổ H1/2026 đã khoá và đã ra báo cáo bán niên."),
    }


# =============================================================================================
# Ghi
# =============================================================================================

def nap_lo(db, rows: list[dict], boi: str, ten_tep: str = "",
           bo_qua_dong_loi: bool = False) -> dict:
    """CỬA GHI. Mặc định chỉ ghi dòng SẠCH.

    `bo_qua_dong_loi` ở đây mang nghĩa "ghi ĐÈ cả chuyến đã có số của nguồn khác" – và đó là một
    quyết định của người bấm, không phải của máy. Dòng không tìm được chuyến thì không có cách nào
    ghi được, kể cả khi bấm bỏ qua: không có chuyến thì không có chỗ để ghi vào.
    """
    soat = kiem_lo(db, rows)
    da, bo = [], []
    for x in soat["chi_tiet"]:
        if not (x["ro"] == "nap_duoc" or (x["ro"] == "can_xac_nhan" and bo_qua_dong_loi)):
            bo.append({"ma_tour": x["ma_tour"], "ro": x["ro"],
                       "vi_sao": x["chan"] + x["can_xac_nhan"]})
            continue
        from app.models.core import Tour
        t = db.get(Tour, x["tour_id"])
        if t is None:
            bo.append({"ma_tour": x["ma_tour"], "ro": "khong_thay_chuyen", "vi_sao": []})
            continue
        t.actual_revenue = x["tong_thu"]
        if x["tong_chi"] is not None:
            t.actual_cost = x["tong_chi"]
        # Chốt an toàn 2: chỉ đổi trạng thái của CHUYẾN DO LÔ TẠO RA. Chuyến của hệ đang chạy có
        # luồng trạng thái riêng, và kéo nó sang "khoa" là cắt ngang quy trình của người khác.
        if _la_chuyen_cua_lo(t):
            t.status = TRANG_THAI_SAU_NAP
        da.append({"ma_tour": x["ma_tour"], "ma_chuyen": t.code, "tour_id": t.id,
                   "tong_thu": x["tong_thu"], "tong_chi": x["tong_chi"],
                   "de_len_so_cu": bool(x["thu_dang_co"] or x["chi_dang_co"])})
    db.flush()

    thu = sum(x["tong_thu"] or 0 for x in da)
    chi = sum(x["tong_chi"] or 0 for x in da)
    return {
        "so_dong": len(rows), "da_nap": len(da),
        "da_co": sum(1 for x in bo if x["ro"] == "can_xac_nhan"),
        "dong_loi": sum(1 for x in bo if x["ro"] in ("chan", "khong_thay_chuyen")),
        "nguon": NGUON,
        "tong_thu_da_ghi": round(thu, 2), "tong_chi_da_ghi": round(chi, 2),
        "chi_tiet_da_nap": da, "chi_tiet_bo_qua": bo,
        "khong_sinh_but_toan": (
            "Cửa này KHÔNG sinh bút toán kế toán. Sổ H1/2026 đã khoá và đã ra báo cáo tài chính bán "
            "niên; sinh bút toán bây giờ là ghi trùng doanh thu cả nửa năm."),
        "message": (
            f"Đã ghi doanh thu/giá vốn mức chuyến cho {len(da)} chuyến "
            f"({thu:,.0f} đ / {chi:,.0f} đ). Chuyến do lô tạo ra chuyển sang trạng thái "
            f"'{TRANG_THAI_SAU_NAP}' – thôi nằm ở mục 'quá hạn quyết toán' và bắt đầu vào báo cáo "
            f"tháng. Không sinh bút toán kế toán."),
    }


# =============================================================================================
# Khai vào khung nạp
# =============================================================================================

def bo_nap(_c) -> dict:
    return {
        "doi_chieu_h1_2026": {
            "bang_dich": "tours",
            "phong_ban": "ketoan",
            "lo": True,
            "ten": "Bản đối chiếu H1/2026 – tổng thu, tổng chi từng chuyến",
            "mo_ta": (
                "CHẠY SAU hai cửa 'Tạo chuyến còn thiếu' và 'Kho quyết toán CŨ'. Hai cửa ấy dựng "
                "chuyến và đổ dòng chi tiết, nhưng cố ý KHÔNG ghi tiền mức chuyến: bộ đọc 604 tệp "
                "Excel chỉ rút được 90,7% doanh thu và 71,1% giá vốn so với bản này.\n\n"
                "Bản đối chiếu là chỗ DUY NHẤT có số đúng ở mức chuyến – 624 chuyến, 97,5 tỷ doanh "
                "thu, 80,9 tỷ giá vốn, Kế toán đã soát và đã đối với MISA.\n\n"
                "GHÉP BẰNG TÊN TỆP, không bằng mã tour: trong 624 dòng chỉ 10 dòng mang mã tour "
                "đúng dạng. Cửa tạo chuyến ghi lại tệp nào đẻ ra chuyến nào, cửa này tra ngược qua "
                "đó – ghép được 599/624 dòng.\n\n"
                "KHÔNG ĐÈ số của chuyến không do lô tạo ra. Chuyến nhập từ Vietrip hay do người gõ "
                "tay mà đã có doanh thu thì xếp vào rổ 'cần người xác nhận', nêu cả hai con số ra "
                "để người đọc tự quyết.\n\n"
                "CHUYẾN CỦA LÔ CHUYỂN SANG TRẠNG THÁI 'Đã khoá', không phải 'Kế toán đã xác nhận' – "
                "không kế toán nào bấm cả, và máy ghi vào ô ấy là để hệ thống ghi nhận một chữ ký "
                "không ai ký. 'Đã khoá' nói đúng: chuyến xong, số chốt, không chờ ai. Nó cũng tắt "
                "cờ 'quá hạn quyết toán' và đưa chuyến vào báo cáo tháng.\n\n"
                "KHÔNG SINH BÚT TOÁN KẾ TOÁN: sổ H1/2026 đã khoá và đã ra báo cáo tài chính bán "
                "niên, sinh bút toán bây giờ là ghi trùng doanh thu cả nửa năm."),
            "khoa_chong_trung": "Chuyến (tours.id) – ghi lại cùng bản thì THAY, không cộng dồn",
            "cot": [
                _c("ma_tour", "Mã tour", True, vi_du="NT001.03050126",
                   ghi_chu="cột 'Mã tour' của sheet DOI CHIEU TUNG TOUR; nhiều dòng ghi tên tệp ở đây"),
                _c("ten_tep_qt", "File quyết toán", vi_du="QT NHA TRANG 05.01.26.xlsx",
                   ghi_chu="khoá ghép chính – 507/624 dòng chỉ ghép được qua cột này"),
                _c("tong_thu", "Tổng thu (QT)", True, kieu="tien", vi_du="2490514155"),
                _c("tong_chi", "Tổng chi (QT)", kieu="tien", vi_du="2290966430"),
                _c("so_khach", "Số khách", kieu="so", vi_du="44"),
                _c("thang", "Tháng", vi_du="T1"),
                _c("nhom", "Nhóm", vi_du="Tour lẻ"),
            ],
            "doc_tep": doc_tep,
            "kiem_lo": kiem_lo,
            "nap_lo": nap_lo,
            "kiem": lambda db, d: _soat_mot(db, d),
            "nap": lambda db, d, boi: nap_lo(db, [d], boi),
        }
    }


def vai_tro(quan_tri: tuple) -> dict:
    """Ai được nạp. Bản đối chiếu là tài liệu của Kế toán – họ giữ nó, họ nạp nó.

    Trưởng phòng Điều hành KHÔNG có trong danh sách: cửa này ghi thẳng vào doanh thu và giá vốn của
    624 chuyến đã khép sổ, và nó là con số Kế toán chịu trách nhiệm trước MISA.
    """
    return {"doi_chieu_h1_2026": quan_tri + ("ketoan",)}
