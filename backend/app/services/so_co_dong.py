"""CD-2 · Sổ cổ đông và hồ sơ sở hữu (Chủ tịch duyệt bản xem thử 28/10/2026).

QUY TẮC
  1. Số cổ phần CHỈ lấy từ danh sách người sở hữu VSD do IR – Pháp chế tải lên (Excel / CSV) và Chủ tịch duyệt.
     Không có ô gõ số cổ phần ở đâu. Người tải không tự duyệt.
  2. Lô duyệt mới nhất (theo ngày căn cứ) là danh sách đang dùng; lô cũ giữ để tra.
  3. Nối tài khoản: máy GỢI Ý khi số giấy tờ (CCCD / ĐKKD) khớp ĐÚNG sau khi bỏ dấu cách, chấm, gạch; IR bấm nối.
     Tên giống nhau không tự nối. Gỡ nối phải có lý do, không xoá dòng.
  4. Cổ đông chỉ thấy số của CHÍNH mình kèm ngày căn cứ; không bao giờ thấy số giấy tờ đầy đủ.
  5. Số giấy tờ là dữ liệu cá nhân (NĐ 13/2023): chỉ IR – Pháp chế, Chủ tịch, TGĐ, Ban Kiểm soát xem.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cong_co_dong import (TRANG_THAI_LO_SCD, DongSoCoDong, LoSoCoDong, NoiSoCoDong, YeuCauIr)
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.services import rules as R

VAI_NAP = ("ir_phapche",)
VAI_DUYET = ("chutich",)
VAI_XEM = ("chutich", "tgd", "bks", "robot_ks", "ir_phapche")
TOI_DA_DONG = 20000


class LoiSo(Exception):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


# ====================================================================== đọc tệp
def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "")).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


COT = {
    "ho_ten": ("ho ten", "ho va ten", "ten co dong", "ten nha dau tu", "ten chu so huu", "ten"),
    "giay_to": ("so dksh", "so dang ky so huu", "cccd", "cmnd", "so giay to", "so cmnd", "so cccd", "dkkd", "giay to",
                "ma so doanh nghiep", "so dkkd", "so id"),
    "so_cp": ("so luong ck", "so luong co phan", "so co phan", "so luong cp", "so cp", "so luong", "tong so"),
    "tk_luu_ky": ("tai khoan luu ky", "tk luu ky", "so tai khoan", "so tk", "tai khoan"),
}


def chuan_giay_to(s) -> str:
    return re.sub(r"[^0-9A-Z]", "", str(s or "").upper())[:40]


def _so(v) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else None
    t = re.sub(r"[\s.,]", "", str(v))
    return int(t) if t.isdigit() else None


def _bang(ten: str, data: bytes) -> list[list]:
    if (ten or "").lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        try:
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception:
            raise LoiSo("Không đọc được tệp Excel")
        return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    if (ten or "").lower().endswith(".csv"):
        for enc in ("utf-8-sig", "cp1258", "latin-1"):
            try:
                txt = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        dia = csv.Sniffer().sniff(txt[:4000], delimiters=",;\t") if txt.strip() else csv.excel
        return [r for r in csv.reader(io.StringIO(txt), dia)]
    raise LoiSo("Chỉ nhận tệp Excel (.xlsx) hoặc CSV")


def doc_tep(ten: str, data: bytes) -> dict:
    """Đọc danh sách người sở hữu. Không ghi gì. Trả dòng hợp lệ, lỗi theo số dòng, cột nhận ra."""
    if not data:
        raise LoiSo("Tệp rỗng")
    bang = _bang(ten, data)
    dau, cot = None, {}
    for i, r in enumerate(bang[:30]):
        nhan = [_khong_dau(x) for x in r]
        m = {}
        for k, al in COT.items():
            for j, h in enumerate(nhan):
                if h and any(h == a or h.startswith(a) for a in al) and j not in m.values():
                    m[k] = j
                    break
        if {"ho_ten", "giay_to", "so_cp"} <= m.keys():
            dau, cot = i, m
            break
    if dau is None:
        raise LoiSo("Không thấy dòng tiêu đề có đủ ba cột: Họ tên · Số giấy tờ (ĐKSH / CCCD / ĐKKD) · Số lượng cổ phần")
    dong, loi = [], []
    for i, r in enumerate(bang[dau + 1:], start=dau + 2):
        g = lambda k: (r[cot[k]] if k in cot and cot[k] < len(r) else None)  # noqa: E731
        ten_ = str(g("ho_ten") or "").strip()
        gt, sl = chuan_giay_to(g("giay_to")), _so(g("so_cp"))
        if not ten_ and not gt and sl is None:
            continue
        # Dòng tổng: không có số giấy tờ và có ô bắt đầu bằng «Tổng» / «Total» / «Cộng». KHÔNG xét riêng cột
        # tên — «Công ty X» là cổ đông thật, không phải dòng cộng.
        if not gt and any(re.match(r"(tong|total|cong cong|cong)\b", _khong_dau(x)) for x in r if x not in (None, "")):
            continue
        if not gt:
            loi.append({"dong": i, "loi": "thiếu số giấy tờ"}); continue
        if sl is None or sl <= 0:
            loi.append({"dong": i, "loi": "số cổ phần không hợp lệ"}); continue
        dong.append({"ho_ten": ten_[:200], "giay_to": gt, "so_cp": sl, "tk_luu_ky": str(g("tk_luu_ky") or "").strip()[:40]})
    if len(dong) > TOI_DA_DONG:
        raise LoiSo(f"Tệp có {len(dong)} dòng — vượt {TOI_DA_DONG}")
    ten_cot = {k: str(bang[dau][j]) for k, j in cot.items()}
    return {"dong": dong, "loi": loi, "cot": ten_cot, "so_dong": len(dong), "tong_cp": sum(d["so_cp"] for d in dong),
            "so_nguoi": len({d["giay_to"] for d in dong})}


# ====================================================================== lô
def _co(u: User, vai) -> bool:
    return u.role in vai


def doc_thu(u: User, ten: str, data: bytes) -> dict:
    if not _co(u, VAI_NAP):
        raise LoiSo("Chỉ IR – Pháp chế tải danh sách sở hữu", 403)
    r = doc_tep(ten, data)
    r["dong"] = r["dong"][:20]          # xem thử 20 dòng đầu — đủ để nhận ra cột đúng hay sai
    return r


def gui_duyet(db: Session, u: User, ngay_can_cu: date, ten: str, data: bytes) -> LoSoCoDong:
    if not _co(u, VAI_NAP):
        raise LoiSo("Chỉ IR – Pháp chế tải danh sách sở hữu", 403)
    if ngay_can_cu is None or ngay_can_cu > date.today():
        raise LoiSo("Ngày căn cứ không hợp lệ")
    bam = hashlib.sha256(data or b"").hexdigest()
    if db.execute(select(LoSoCoDong).where(LoSoCoDong.bam_tep == bam, LoSoCoDong.trang_thai != "tu_choi")).scalars().first():
        raise LoiSo("Tệp này đã được tải lên", 409)
    if db.execute(select(LoSoCoDong).where(LoSoCoDong.trang_thai == "cho_duyet")).scalars().first():
        raise LoiSo("Đang có một lô chờ Chủ tịch duyệt — chờ duyệt hoặc từ chối trước", 409)
    r = doc_tep(ten, data)
    if not r["dong"]:
        raise LoiSo("Tệp không có dòng hợp lệ nào")
    so = (db.execute(select(func.max(LoSoCoDong.id))).scalar() or 0) + 1
    lo = LoSoCoDong(ma=f"SCD-{so:03d}", ngay_can_cu=ngay_can_cu, ten_tep=(ten or "")[:200], bam_tep=bam,
                    trang_thai="cho_duyet", so_dong=r["so_dong"], tong_cp=r["tong_cp"], loi=r["loi"][:200],
                    nap_boi=u.username, nap_luc=datetime.now())
    db.add(lo); db.flush()
    db.add_all([DongSoCoDong(lo_id=lo.id, **d) for d in r["dong"]])
    db.flush()
    R.audit(db, u.username, u.role, "so_co_dong_gui_duyet", f"lo_so_co_dong:{lo.ma}",
            after={"ngay_can_cu": str(ngay_can_cu), "so_dong": lo.so_dong, "tong_cp": lo.tong_cp, "bam": bam})
    return lo


def duyet(db: Session, u: User, lo_id: int) -> LoSoCoDong:
    if not _co(u, VAI_DUYET):
        raise LoiSo("Chỉ Chủ tịch duyệt danh sách sở hữu", 403)
    lo = db.get(LoSoCoDong, lo_id)
    if lo is None:
        raise LoiSo("Không có lô này", 404)
    if lo.trang_thai != "cho_duyet":
        raise LoiSo("Lô này đã xử lý", 409)
    if lo.nap_boi == u.username:
        raise LoiSo("Người tải không tự duyệt lô của mình", 403)
    lo.trang_thai, lo.duyet_boi, lo.duyet_luc = "da_duyet", u.username, datetime.now()
    db.flush()
    R.audit(db, u.username, u.role, "so_co_dong_duyet", f"lo_so_co_dong:{lo.ma}", after={"tong_cp": lo.tong_cp})
    return lo


def tu_choi(db: Session, u: User, lo_id: int, ly_do: str) -> LoSoCoDong:
    if not _co(u, VAI_DUYET):
        raise LoiSo("Chỉ Chủ tịch từ chối danh sách sở hữu", 403)
    lo = db.get(LoSoCoDong, lo_id)
    if lo is None:
        raise LoiSo("Không có lô này", 404)
    if lo.trang_thai != "cho_duyet":
        raise LoiSo("Lô này đã xử lý", 409)
    if not (ly_do or "").strip():
        raise LoiSo("Từ chối phải ghi lý do")
    lo.trang_thai, lo.duyet_boi, lo.duyet_luc, lo.ly_do = "tu_choi", u.username, datetime.now(), ly_do.strip()[:2000]
    db.flush()
    R.audit(db, u.username, u.role, "so_co_dong_tu_choi", f"lo_so_co_dong:{lo.ma}", after={"ly_do": lo.ly_do})
    return lo


def lo_hien_hanh(db: Session) -> LoSoCoDong | None:
    return db.execute(select(LoSoCoDong).where(LoSoCoDong.trang_thai == "da_duyet")
                      .order_by(LoSoCoDong.ngay_can_cu.desc(), LoSoCoDong.id.desc())).scalars().first()


def _ra_lo(lo: LoSoCoDong, hien_hanh_id: int | None) -> dict:
    return {"id": lo.id, "ma": lo.ma, "ngay_can_cu": lo.ngay_can_cu, "ten_tep": lo.ten_tep, "trang_thai": lo.trang_thai,
            "trang_thai_ten": TRANG_THAI_LO_SCD.get(lo.trang_thai, lo.trang_thai), "so_dong": lo.so_dong,
            "tong_cp": lo.tong_cp, "so_loi": len(lo.loi or []), "loi": lo.loi or [], "nap_boi": lo.nap_boi,
            "nap_luc": lo.nap_luc, "duyet_boi": lo.duyet_boi, "duyet_luc": lo.duyet_luc, "ly_do": lo.ly_do,
            "dang_dung": lo.id == hien_hanh_id}


def quan_tri(db: Session, u: User) -> dict:
    hh = lo_hien_hanh(db)
    return {"lo": [_ra_lo(l, hh.id if hh else None) for l in db.execute(select(LoSoCoDong).order_by(LoSoCoDong.id.desc())).scalars()],
            "duoc_nap": _co(u, VAI_NAP), "duoc_duyet": _co(u, VAI_DUYET)}


def dong_cua_lo(db: Session, lo_id: int, q: str = "") -> list[dict]:
    rows = db.execute(select(DongSoCoDong).where(DongSoCoDong.lo_id == lo_id).order_by(DongSoCoDong.id)).scalars()
    k = _khong_dau(q)
    gq = chuan_giay_to(q)
    ra = []
    for d in rows:
        if q and k not in _khong_dau(d.ho_ten) and (not gq or gq not in d.giay_to):
            continue
        ra.append({"ho_ten": d.ho_ten, "giay_to": d.giay_to, "so_cp": d.so_cp, "tk_luu_ky": d.tk_luu_ky})
        if len(ra) >= 200:
            break
    return ra


# ====================================================================== nối tài khoản
def _so_huu(db: Session, lo: LoSoCoDong | None, gt: str) -> dict | None:
    if lo is None or not gt:
        return None
    rows = list(db.execute(select(DongSoCoDong).where(DongSoCoDong.lo_id == lo.id, DongSoCoDong.giay_to == gt)).scalars())
    if not rows:
        return None
    return {"ho_ten": rows[0].ho_ten, "so_cp": sum(r.so_cp for r in rows), "tk_luu_ky": [r.tk_luu_ky for r in rows if r.tk_luu_ky]}


def _noi_cua(db: Session, tk_id: int) -> NoiSoCoDong | None:
    return db.execute(select(NoiSoCoDong).where(NoiSoCoDong.tai_khoan_id == tk_id, NoiSoCoDong.go_luc.is_(None))
                      .order_by(NoiSoCoDong.id.desc())).scalars().first()


def _che(s: str, giu: int = 4) -> str:
    s = str(s or "")
    return ("•" * max(0, len(s) - giu) + s[-giu:]) if s else ""


def ds_noi(db: Session) -> dict:
    hh = lo_hien_hanh(db)
    ra = []
    for tk in db.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.loai == "co_dong").order_by(TaiKhoanNgoai.id.desc())).scalars():
        n = _noi_cua(db, tk.id)
        gt_khai = chuan_giay_to(tk.giay_to)
        d = {"tai_khoan_id": tk.id, "ho_ten": tk.ho_ten, "lien_he": tk.dien_thoai or tk.email, "trang_thai": tk.trang_thai,
             "giay_to_khai": gt_khai, "tk_luu_ky_khai": tk.tk_luu_ky}
        if n is not None:
            sh = _so_huu(db, hh, n.giay_to)
            d.update({"da_noi": True, "giay_to_noi": n.giay_to, "noi_boi": n.noi_boi, "noi_luc": n.noi_luc,
                      "so_huu": sh})
        else:
            d.update({"da_noi": False, "goi_y": _so_huu(db, hh, gt_khai)})
        ra.append(d)
    return {"tai_khoan": ra, "lo_hien_hanh": _ra_lo(hh, hh.id) if hh else None}


def noi(db: Session, u: User, tk_id: int, giay_to: str) -> NoiSoCoDong:
    if not _co(u, VAI_NAP):
        raise LoiSo("Chỉ IR – Pháp chế nối tài khoản", 403)
    tk = db.get(TaiKhoanNgoai, tk_id)
    if tk is None or tk.loai != "co_dong":
        raise LoiSo("Không có tài khoản cổ đông này", 404)
    gt = chuan_giay_to(giay_to)
    hh = lo_hien_hanh(db)
    if hh is None:
        raise LoiSo("Chưa có danh sách sở hữu nào được duyệt")
    if _so_huu(db, hh, gt) is None:
        raise LoiSo(f"Số giấy tờ này không có trong danh sách ngày {hh.ngay_can_cu:%d/%m/%Y}")
    cu = _noi_cua(db, tk.id)
    if cu is not None:
        if cu.giay_to == gt:
            raise LoiSo("Tài khoản đã nối với số giấy tờ này", 409)
        cu.go_boi, cu.go_luc, cu.ly_do_go = u.username, datetime.now(), "Nối lại sang số giấy tờ khác"
    n = NoiSoCoDong(tai_khoan_id=tk.id, giay_to=gt, noi_boi=u.username, noi_luc=datetime.now())
    db.add(n); db.flush()
    R.audit(db, u.username, u.role, "so_co_dong_noi", f"tai_khoan_ngoai:{tk.id}", after={"giay_to": _che(gt)})
    return n


def go_noi(db: Session, u: User, tk_id: int, ly_do: str) -> None:
    if not _co(u, VAI_NAP):
        raise LoiSo("Chỉ IR – Pháp chế gỡ nối", 403)
    n = _noi_cua(db, tk_id)
    if n is None:
        raise LoiSo("Tài khoản chưa nối", 404)
    if not (ly_do or "").strip():
        raise LoiSo("Gỡ nối phải ghi lý do")
    n.go_boi, n.go_luc, n.ly_do_go = u.username, datetime.now(), ly_do.strip()[:2000]
    db.flush()
    R.audit(db, u.username, u.role, "so_co_dong_go_noi", f"tai_khoan_ngoai:{tk_id}", after={"ly_do": n.ly_do_go})


# ====================================================================== phía cổ đông
def so_huu_cua(db: Session, tk: TaiKhoanNgoai) -> dict:
    hh = lo_hien_hanh(db)
    n = _noi_cua(db, tk.id)
    if n is None:
        return {"trang_thai": "chua_noi", "ngay_can_cu": hh.ngay_can_cu if hh else None}
    sh = _so_huu(db, hh, n.giay_to)
    if sh is None:
        return {"trang_thai": "khong_co_ten", "ngay_can_cu": hh.ngay_can_cu if hh else None, "noi_luc": n.noi_luc}
    return {"trang_thai": "da_xac_minh", "so_cp": sh["so_cp"], "ngay_can_cu": hh.ngay_can_cu,
            "tk_luu_ky": [_che(t) for t in sh["tk_luu_ky"]], "noi_luc": n.noi_luc, "duyet_luc": hh.duyet_luc}


def gui_xac_minh(db: Session, tk: TaiKhoanNgoai, noi_dung: str, ten_tep: str = "", kieu: str = "",
                 data: bytes | None = None) -> YeuCauIr:
    """Câu hỏi IR chủ đề «Tư cách / hồ sơ cổ đông», kèm giấy tờ (nếu có). Tệp đánh dấu DỮ LIỆU NHẠY CẢM."""
    from app.services import attachments as AT
    from app.services import cong_co_dong as CD
    if data:
        if len(data) > 10 * 1024 * 1024:
            raise LoiSo("Tệp tối đa 10 MB")
        if (ten_tep or "").rsplit(".", 1)[-1].lower() not in ("pdf", "jpg", "jpeg", "png", "webp", "heic"):
            raise LoiSo("Chỉ nhận PDF hoặc ảnh")
    try:
        y = CD.gui_ir(db, tk, "tu_cach", noi_dung)
    except CD.LoiCoDong as ex:
        raise LoiSo(str(ex), ex.status)
    if data:
        try:
            a, _ = AT.dinh_kem(db, "van_ban", f"co-dong-xac-minh-{tk.id}", ten_tep, data, kieu=kieu, loai="chung_tu",
                               mo_ta=f"Giấy tờ xác minh cổ đông · {y.ma}", boi=f"cong:{tk.id}")
        except ValueError as ex:
            raise LoiSo(str(ex))
        a.nhay_cam = True               # dữ liệu cá nhân: kho chung chỉ vai nhạy cảm đọc; IR đọc qua cửa riêng
        y.attachment_id = a.id
        db.flush()
    return y
