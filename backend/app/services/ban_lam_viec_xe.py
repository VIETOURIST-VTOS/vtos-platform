"""Bàn làm việc Giám đốc đội xe — màn `/xe`, một cửa cho cả màn.

Đặt vào: backend/app/services/ban_lam_viec_xe.py
Lập 08/11/2026 theo KS-43 / KS-44, sau khi anh Tuấn duyệt bố cục.

═══════════════════════════════════════════════════════════════════════════
MỘT CỬA, BỐN VÙNG
═══════════════════════════════════════════════════════════════════════════
    ①  hang_doi   — việc cần giám đốc, xếp theo tiền treo và rủi ro dừng xe
    ②  so_ky      — doanh thu, ba tầng chi phí, lợi nhuận, biên
    ③  xe_hom_nay — đang đi / ở bãi / không khớp, kèm tuổi số và nguồn
    ④  dien_bien  — lợi nhuận sáu kỳ gần nhất

Bốn cửa thì bốn lần chờ, và bốn cơ hội để hai vùng trên cùng một màn nói hai
con số khác nhau.

LUẬT QUAN TRỌNG NHẤT: KHÔNG TỰ TÍNH LẠI TIỀN. Vùng ② lấy nguyên `tong` của
`AI.hieu_qua_ky` — đúng hàm màn Hiệu quả và màn Lãi lỗ đang dùng. Viết lại
phép tính ở đây là cách chắc chắn nhất để ba màn lệch nhau sau vài tháng.

Nghiệm thu (KS-44): mở `/xe` kỳ 2026-10 phải ra ĐÚNG 116.658.654 đ và 15,1%,
khớp từng đồng với màn Lãi lỗ đội xe.

═══════════════════════════════════════════════════════════════════════════
BỐN LUẬT CỦA HÀNG ĐỢI
═══════════════════════════════════════════════════════════════════════════
1. MỖI VIỆC MỘT BỘ DÒ. Thêm loại việc = thêm một hàm `@bo_do`. Bộ dò hỏng thì
   mất một dòng, cả hàng đợi vẫn hiện — một màn thiếu một dòng vẫn dùng được,
   một màn trắng thì không.
2. VIỆC CHỜ NGƯỜI KHÁC HIỆN NHƯNG KHÔNG ĐẾM. Gộp vào số «việc của tôi» thì
   giám đốc quen nhìn một con số không bao giờ về 0, rồi thôi không nhìn nữa.
3. CHƯA NHẬP ≠ BẰNG 0. Nhóm chi phí trống là THIẾU SỐ, phải thành một việc.
   Luật này đã cứu tháng 10 khỏi đọc sai 84,5 tr (KS-36) và 77 tr lương (KS-41).
4. MỖI DÒNG PHẢI CÓ MỘT NÚT. Việc không bấm được là tin tức, không phải việc.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fleet import FleetPeriodCost, Maintenance, Trip, NHOM_CHI_PHI_KY
from app.models.hr import Vehicle
from app.services import fleet as FL
from app.services import fleet_ai as AI
from app.services import fleet_settlement as QT
from app.services import xe_theo_sheet as XS

log = logging.getLogger(__name__)

SO_KY_DIEN_BIEN = 6

# Ngưỡng ĐỎ cho tiền treo. Chuyến trung bình ~12 tr nên 50 tr ≈ bốn chuyến chưa
# chốt: đủ lớn để không kêu vặt, đủ nhỏ để không bỏ sót một tháng hỏng.
NGUONG_TIEN_TREO_DO = 50_000_000

# Hai nhóm người giữ sổ quyết, robot không đòi: phân bổ trả trước (số phải ghi
# là phần phân bổ tháng này, không phải cả hoá đơn) và lãi vay (ngoài giá vốn,
# Chủ tịch quyết 11/10/2026). Thiếu hai nhóm này KHÔNG phải là việc của giám đốc.
NHOM_NGUOI_QUYET = ("tra_truoc", "lai_vay")

DO, CAM, VANG, TRANG = "do", "cam", "vang", "trang"
THU_TU_MUC = {DO: 0, CAM: 1, VANG: 2, TRANG: 3}

# ngăn kéo -> quyền cần có để BẤM. Thiếu quyền thì việc vẫn hiện, chỉ mất nút.
QUYEN_NGAN_KEO = {"quyet-toan": "quyet_toan", "chi-phi-ky": "ghi_chi_phi_ky",
                  "bao-duong": "ghi_bao_duong", "de-xuat": "duyet_de_xuat"}

_SO_DANG_KY: list = []


def bo_do(ma: str):
    def deco(fn):
        _SO_DANG_KY.append((ma, fn))
        return fn
    return deco


def _viec(ma, tieu_de, mo_ta, muc, nhan_nut, ngan_keo=None, *,
          cua_toi=True, so_luong=0, tien_treo=0, nguon="") -> dict:
    # Luật 4, chặn ngay ở tầng dữ liệu.
    if ngan_keo is None and cua_toi:
        raise ValueError(f"Việc «{ma}» không có ngăn kéo mà lại là việc của tôi.")
    return {"ma": ma, "tieu_de": tieu_de, "mo_ta": mo_ta, "muc": muc,
            "ai_chan": "toi" if cua_toi else "nguoi_khac", "nhan_nut": nhan_nut,
            "ngan_keo": ngan_keo, "so_luong": so_luong, "tien_treo": tien_treo,
            "nguon": nguon}


def _muc(*, chan_khai_thac=False, tien_treo=0, thieu_so_so_sach=False) -> str:
    if chan_khai_thac or tien_treo > NGUONG_TIEN_TREO_DO:
        return DO
    return CAM if thieu_so_so_sach else VANG


def _tien(n) -> str:
    return f"{round(n or 0):,}".replace(",", ".")


# ═════════════════════════════════════════════════════════════════════════
# CÁC BỘ DÒ — mỗi hàm nhận ctx đã nạp sẵn, trả 0..n việc
# ═════════════════════════════════════════════════════════════════════════
@bo_do("chuyen_chua_quyet_toan")
def _chua_quyet_toan(ctx) -> list:
    t = ctx["hieu_qua"].get("tong") or {}
    n = int(t.get("so_chuyen_chua_quyet_toan") or 0)
    if not n:
        return []
    tien = int(t.get("doanh_thu_chua_quyet_toan") or 0)
    return [_viec("chuyen_chua_quyet_toan", f"{n} chuyến chưa quyết toán",
                  f"Kỳ {ctx['ky']} · doanh thu đang treo {_tien(tien)} đ",
                  _muc(tien_treo=tien), "Quyết toán →", "quyet-toan",
                  so_luong=n, tien_treo=tien, nguon="fleet_ai.hieu_qua_ky")]


@bo_do("chuyen_cho_xac_nhan")
def _cho_xac_nhan(ctx) -> list:
    t = ctx["hieu_qua"].get("tong") or {}
    n = int(t.get("so_chuyen_cho_xac_nhan") or 0)
    if not n:
        return []
    return [_viec("chuyen_cho_xac_nhan", f"{n} chuyến kẹt ở «chờ xác nhận»",
                  "Thường do mở lại chuyến còn cờ đỏ — cửa xác nhận trả 422",
                  CAM, "Gỡ cờ →", "quyet-toan",
                  so_luong=n, nguon="fleet_ai.hieu_qua_ky")]


@bo_do("xe_bi_chan_khai_thac")
def _xe_bi_chan(ctx) -> list:
    d = ctx["xe_dem"]
    if not d["bi_chan"]:
        return []
    return [_viec("xe_bi_chan_khai_thac",
                  f"{d['bi_chan']} / {d['tong']} xe đang bị chặn khai thác",
                  f"Thiếu giấy tờ hoặc chưa qua kiểm tra · {d['san_sang']} xe sẵn sàng",
                  _muc(chan_khai_thac=True), "Xem · Gỡ →", "ho-so-xe",
                  so_luong=d["bi_chan"], nguon="fleet.san_sang")]


@bo_do("xe_chua_co_lich_su_bao_duong")
def _chua_bao_duong(ctx) -> list:
    n = ctx["xe_dem"]["chua_co_bao_duong"]
    if not n:
        return []
    return [_viec("xe_chua_co_lich_su_bao_duong", f"{n} xe chưa có lịch sử bảo dưỡng",
                  "Chưa biết mốc kỳ tới — không suy ra từ chu kỳ chung",
                  VANG, "Ghi phiếu →", "bao-duong",
                  so_luong=n, nguon="bảng Maintenance")]


@bo_do("chi_phi_ky_thieu_nhom")
def _chi_phi_thieu(ctx) -> list:
    """LUẬT 3 — nhóm trống là THIẾU SỐ, không phải 0 đồng."""
    thieu = ctx["nhom_thieu"]
    if not thieu:
        return []
    if not ctx["cpk_rows"]:
        tieu_de = "Chi phí kỳ chưa nhập khoản nào"
        mo_ta = (f"0 đ trên cả {len(NHOM_CHI_PHI_KY)} nhóm · "
                 "báo cáo kỳ này đang đọc cao hơn thực tế")
    else:
        ten = ", ".join(NHOM_CHI_PHI_KY[m][0] for m in thieu[:3])
        them = f" và {len(thieu) - 3} nhóm nữa" if len(thieu) > 3 else ""
        tieu_de = f"{len(thieu)} nhóm chi phí kỳ chưa nhập"
        mo_ta = f"{ten}{them} — chưa nhập, không phải bằng 0"
    return [_viec("chi_phi_ky_thieu_nhom", tieu_de, mo_ta,
                  _muc(thieu_so_so_sach=True), "Nhập →", "chi-phi-ky",
                  so_luong=len(thieu), nguon="bảng FleetPeriodCost")]


@bo_do("thieu_link_csv_tab_moi")
def _thieu_link(ctx) -> list:
    """LUẬT 2 — việc CHỜ NGƯỜI KHÁC: hiện nhưng không đếm.

    Chủ sheet phải công bố CSV tab tháng mới, rồi `gd_doi_xe`/`tp_dh`/`cntt`
    dán vào tham số và Chủ tịch ký. Giám đốc đội xe không tự làm xong được,
    nên nó không được tính vào số «việc của tôi».
    """
    s = ctx["sheet"]
    vtos_dang_chay = ctx.get("vtos_dang_chay") or 0
    sheet_dang_di = s.get("dang_di")
    if not s.get("co_link"):
        mo_ta = "Chưa có link bảng xe — ô «đang đi» không có nguồn"
    elif vtos_dang_chay and not sheet_dang_di:
        # PHÉP SO, KHÔNG PHẢI CỜ. Bản đầu neo vào `ban_cu`, mà cờ ấy false ngay
        # cả khi thiếu link tab tháng mới — bộ dò im lặng đúng lúc cần kêu.
        mo_ta = (f"VTOS biết có {vtos_dang_chay} chuyến đang chạy hôm nay, "
                 f"nhưng bảng xe báo 0 — bảng mới đọc {s.get('so_chuyen') or 0} "
                 "chuyến, thiếu link tab tháng này")
    elif s.get("ban_cu"):
        mo_ta = (f"Mới đọc {s.get('so_chuyen') or 0} chuyến từ tab cũ — "
                 "tab tháng này chưa công bố")
    else:
        return []
    return [_viec("thieu_link_csv_tab_moi", "Thiếu link CSV tab tháng mới",
                  f"{mo_ta} · đang chờ chủ sheet công bố", TRANG,
                  "Chờ người khác", None, cua_toi=False,
                  nguon="xe_theo_sheet.bao_cao")]


# ═════════════════════════════════════════════════════════════════════════
def dung_hang_doi(ctx: dict, quyen: dict | None = None) -> dict:
    viec, hong = [], []
    for ma, fn in _SO_DANG_KY:
        try:
            viec.extend(fn(ctx) or [])
        except Exception as e:  # noqa: BLE001
            log.exception("ban_lam_viec_xe: bộ dò «%s» hỏng: %s", ma, e)
            hong.append(ma)

    # mức -> tiền treo nhiều trước -> số lượng nhiều trước -> mã (ổn định để test so được)
    viec.sort(key=lambda v: (THU_TU_MUC[v["muc"]], -v["tien_treo"], -v["so_luong"], v["ma"]))

    # Quyền ẩn NÚT, không ẩn VIỆC: giám đốc vẫn phải thấy tiền đang treo.
    for v in viec:
        q = QUYEN_NGAN_KEO.get(v["ngan_keo"] or "")
        bam = bool(v["ngan_keo"]) and (quyen is None or q is None or quyen.get(q, False))
        v["bam_duoc"] = bam
        if not bam and v["ngan_keo"]:
            v["nhan_nut"], v["ngan_keo"] = "Không có quyền", None

    cua_toi = [v for v in viec if v["ai_chan"] == "toi"]
    return {"viec": viec, "so_viec_cua_toi": len(cua_toi),
            "so_do": sum(1 for v in cua_toi if v["muc"] == DO),
            "so_cam": sum(1 for v in cua_toi if v["muc"] == CAM),
            "so_vang": sum(1 for v in cua_toi if v["muc"] == VANG),
            "so_cho_nguoi_khac": sum(1 for v in viec if v["ai_chan"] == "nguoi_khac"),
            "tong_tien_treo": sum(v["tien_treo"] for v in cua_toi),
            "bo_do_hong": hong}


def _ky_truoc(ky: str, lui: int) -> str:
    nam, thang = (int(x) for x in ky.split("-"))
    thang -= lui
    while thang <= 0:
        thang += 12
        nam -= 1
    return f"{nam:04d}-{thang:02d}"


def _dem_xe(db: Session) -> dict:
    chan = False
    try:
        from app.services import rules as R
        chan = bool(R.get_param(db, "xe_chan_khi_thieu_giay"))
    except Exception:
        pass
    xes = list(db.execute(select(Vehicle)).scalars())
    muc = {}
    for v in xes:
        m = FL.san_sang(db, v, chan)["muc"]
        muc[m] = muc.get(m, 0) + 1
    co_bd = {m.vehicle_id for m in db.execute(select(Maintenance)).scalars()}
    return {"tong": len(xes), "san_sang": muc.get(FL.OK, 0),
            "chua_du_du_lieu": muc.get(FL.UNKNOWN, 0), "bi_chan": muc.get(FL.BLOCK, 0),
            "chua_co_bao_duong": sum(1 for v in xes if v.id not in co_bd)}


def ban_lam_viec(db: Session, ky: str, quyen: dict | None = None) -> dict:
    """Một cửa cho cả màn `/xe`."""
    QT.ky_range(ky)  # ném nếu kỳ sai dạng — router đổi thành 422

    hq = AI.hieu_qua_ky(db, ky)
    t = hq.get("tong") or {}

    cpk_rows = list(db.execute(
        select(FleetPeriodCost).where(FleetPeriodCost.ky == ky)).scalars())
    da_co = {r.nhom for r in cpk_rows}
    nhom_thieu = [m for m in NHOM_CHI_PHI_KY
                  if m not in da_co and m not in NHOM_NGUOI_QUYET]

    try:
        sheet = XS.bao_cao(db, date.today())
    except Exception as e:  # noqa: BLE001
        log.warning("ban_lam_viec_xe: không đọc được bảng xe: %s", e)
        sheet = {"co_link": False, "loi": str(e)}

    # Chuyến VTOS TỰ BIẾT là đang chạy hôm nay. Đây là vế đối chứng của bảng xe:
    # hai nguồn nói khác nhau thì nói ra, đừng im lặng lấy nguồn nào cũng được.
    hom_nay = date.today()
    try:
        vtos_dang_chay = sum(
            1 for t in db.execute(
                select(Trip).where(Trip.ngay_di <= hom_nay, Trip.ngay_ve >= hom_nay,
                                   Trip.status.not_in(("nhap", "huy")))).scalars())
    except Exception as e:  # noqa: BLE001
        log.warning("ban_lam_viec_xe: không đếm được chuyến đang chạy: %s", e)
        vtos_dang_chay = 0

    ctx = {"ky": ky, "hieu_qua": hq, "cpk_rows": cpk_rows,
           "nhom_thieu": nhom_thieu, "sheet": sheet, "xe_dem": _dem_xe(db),
           "vtos_dang_chay": vtos_dang_chay}

    # ④ Kỳ nào chưa có số thì để None, KHÔNG thay bằng 0.
    diem = []
    for lui in range(SO_KY_DIEN_BIEN - 1, -1, -1):
        k = _ky_truoc(ky, lui)
        try:
            tt = (AI.hieu_qua_ky(db, k) or {}).get("tong") or {}
        except Exception as e:  # noqa: BLE001
            log.warning("ban_lam_viec_xe: không đọc được kỳ %s: %s", k, e)
            tt = {}
        co_so = bool(tt.get("doanh_thu"))
        diem.append({"ky": k, "co_so": co_so,
                     "loi_nhuan": int(tt.get("loi_nhuan") or 0) if co_so else None,
                     "bien": tt.get("bien_loi_nhuan") if co_so else None})
    du_ve = sum(1 for d in diem if d["co_so"]) >= 2

    return {
        "ky": ky,
        "hang_doi": dung_hang_doi(ctx, quyen),
        "so_ky": {
            "ky": ky,
            "doanh_thu": t.get("doanh_thu"),
            "chi_phi_xe": t.get("chi_phi_xe"),
            "chi_phi_cua_doi": t.get("chi_phi_doi"),
            "chi_tiet_chi_phi_doi": t.get("chi_tiet_chi_phi_doi") or {},
            "loi_nhuan": t.get("loi_nhuan"),
            "bien_loi_nhuan": t.get("bien_loi_nhuan"),
            "so_xe_co_chay": len(hq.get("xe") or []),
            "tong_xe": ctx["xe_dem"]["tong"],
            # «chưa nhập» nêu TÊN nhóm, không hiện 0.
            "chua_nhap": [{"ma": m, "ten": NHOM_CHI_PHI_KY[m][0]} for m in nhom_thieu],
            "nguon": "fleet_ai.hieu_qua_ky — cùng hàm với màn Hiệu quả và màn Lãi lỗ",
        },
        "xe_hom_nay": {
            "doc_luc": sheet.get("doc_luc"), "dang_di": sheet.get("dang_di"),
            "o_bai": sheet.get("o_bai"), "khong_khop": sheet.get("khong_khop"),
            "so_chuyen_doc_duoc": sheet.get("so_chuyen"),
            "danh_sach": sheet.get("danh_sach") or [],
            "vtos_dang_chay": vtos_dang_chay,
            "canh_bao": (sheet.get("loi") or
                         (f"VTOS biết có {vtos_dang_chay} chuyến đang chạy hôm nay mà "
                          "bảng xe báo 0 — thiếu link CSV tab tháng này, nên «đang đi» "
                          "CHƯA phải số thật."
                          if (vtos_dang_chay and not sheet.get("dang_di")) else
                          ("Mới đọc được tab cũ — thiếu link CSV tab tháng này, nên "
                           "«đang đi» chưa phải số thật." if sheet.get("ban_cu") else None))),
            "nguon": "xe_theo_sheet.bao_cao",
        },
        "dien_bien": {"diem": diem, "du_ve": du_ve,
                      "vi_sao": None if du_ve else
                      "Cần ít nhất hai kỳ có số thì mới vẽ được đường — một điểm "
                      "đứng một mình không so với kỳ nào."},
        "canh_bao": hq.get("canh_bao") or [],
    }
