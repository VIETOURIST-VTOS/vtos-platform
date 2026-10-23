# -*- coding: utf-8 -*-
"""CN-2 · GIỮ LƯƠNG PHÒNG CHƯA DUYỆT CÔNG, và BẢNG LƯƠNG BỔ SUNG (Chủ tịch chốt 21/10/2026).

CN-1 chặn CẢ KỲ khi còn một phòng chưa được duyệt công — luật tạm, an toàn nhưng phạt cả công ty
vì một phòng. Bản này thay bằng luật Chủ tịch chọn:

  · Lúc Chủ tịch/TGĐ KÝ bảng chính, phòng nào chưa được duyệt công thì lương phòng ấy BỊ GIỮ: không
    vào bản khoá, không vào bút toán, không vào lệnh chi. Phần còn lại đi tiếp như thường.
  · Công được duyệt rồi, HCNS bấm «Lập bảng bổ sung»: máy tính lại theo công đã duyệt, CHỈ cho những
    người bị giữ. Bảng bổ sung đi CÙNG CHUỖI như bảng chính (máy kiểm cơ sở → HCNS kiểm → Chủ tịch
    hoặc TGĐ ký), khoá bản riêng, bút toán riêng, chi riêng.
  · Người bị giữ: phiếu lương ghi «đang giữ» — KHÔNG hiện số dự kiến; có chuông, và có tin Zalo OA
    cho từng người đã nối Zalo.

GIỮ THEO PHÒNG, KHÔNG TÁCH NGƯỜI. Đơn vị duyệt công là phòng, nên đơn vị giữ cũng là phòng.

QUYẾT ĐỊNH GIỮ CHỤP ĐÚNG LÚC KÝ, và lưu vào `payroll_runs.giu_lai`. Không tính lại về sau: phòng
được duyệt công sau khi ký thì vẫn là phòng ĐÃ BỊ GIỮ, và đường ra duy nhất là bảng bổ sung. Tính lại
thì một phòng tự «rơi» về bảng chính đã khoá mà không ai ký cho nó.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Alert, User
from app.models.hr import Employee, PayrollRun
from app.models.luong_khoa import BangLuongBoSung

CHUONG_GIU = "luong_dang_giu"
VAI_LAP = ("hcns",)
VAI_KY = ("chutich", "tgd")
DA_KY_BS = "da_ky"
TRANG_THAI_BS = {"nhap": "Máy lập – chờ kiểm cơ sở", "da_kiem_co_so": "Đã kiểm cơ sở – chờ HCNS",
                 "hcns_kiem": "HCNS đã kiểm – chờ Chủ tịch/TGĐ ký", "da_ky": "Đã ký & khoá"}

# Các ô cộng được của một dòng lương — đúng bộ ô `hr.compute_draft` cộng ra `totals`.
_O_CONG = ("luong_cb", "bien_doi", "tncn", "bhxh", "doan_phi", "tru_su_vu", "thu_nhap", "khoan_tru",
           "thuc_nhan")
_O_DANH_SACH = ("thieu_cong", "chua_du_co_so", "thieu_muc_bhxh")


class LoiGiuLuong(ValueError):
    pass


# ------------------------------------------------------------------ tách và cộng
def tong_cua(rows: list[dict], goc: dict | None = None) -> dict:
    """Tổng của một tập dòng, cùng hình với `totals` của `compute_draft`.

    Ô không cộng được (công chuẩn, số chuyến) lấy nguyên từ tổng gốc; ô danh sách mã thì lọc lại
    theo tập dòng — không thì bản khoá bảng chính kê tên người không có trong nó.
    """
    goc = goc or {}
    ma = {r.get("ma") for r in rows}
    t = {k: sum(float(r.get(k) or 0) for r in rows) for k in _O_CONG}
    t["so_nguoi"] = len(rows)
    for k in ("so_chuyen", "cong_chuan"):
        if k in goc:
            t[k] = goc[k]
    for k in _O_DANH_SACH:
        t[k] = [m for m in (goc.get(k) or []) if m in ma]
    return t


def ma_bi_giu(run: PayrollRun) -> set[str]:
    return {m for g in (run.giu_lai or {}).values() for m in (g.get("ma") or [])}


def tach(run: PayrollRun) -> tuple[list[dict], list[dict]]:
    """(dòng bảng chính, dòng bị giữ) theo quyết định giữ ĐÃ CHỤP."""
    giu = ma_bi_giu(run)
    return ([r for r in run.rows or [] if r.get("ma") not in giu],
            [r for r in run.rows or [] if r.get("ma") in giu])


def phan_chinh(run: PayrollRun) -> tuple[list[dict], dict]:
    """Phần bảng chính sẽ khoá. Không giữ ai thì trả NGUYÊN `rows`/`totals` — bản khoá của kỳ không
    giữ lương phải y hệt như trước CN-2, từng chữ, để vân tay đối chiếu không đổi nghĩa."""
    if not run.giu_lai:
        return run.rows or [], run.totals or {}
    chinh, _ = tach(run)
    return chinh, tong_cua(chinh, run.totals or {})


# ------------------------------------------------------------------ lúc ký bảng chính
def chup_khi_ky(db: Session, run: PayrollRun) -> dict:
    """Gọi NGAY TRƯỚC khi khoá bảng chính: chụp phòng nào bị giữ, ghi vào `run.giu_lai`.

    Không phân vai: ai ký cũng chụp như nhau. Trả về `run.giu_lai`.
    """
    from app.services import xac_nhan_cong as XNC
    chua = XNC.phong_chua_duyet(db, run.period, [r.get("ma") for r in run.rows or [] if r.get("ma")])
    luc = datetime.now().isoformat(timespec="seconds")
    giu: dict = {}
    for t in chua:
        ma = sorted(r.get("ma") for r in run.rows or [] if r.get("phong") == t["phong"] and r.get("ma"))
        if ma:
            giu[t["phong"]] = {"ma": ma, "ly_do": t["trang_thai_ten"], "luc": luc, "bo_sung_so": None}
    run.giu_lai = giu
    return giu


def bao_giu(db: Session, run: PayrollRun) -> dict:
    """Chuông (một cái mỗi phòng) và tin Zalo OA (một tin mỗi người đã nối Zalo).

    Chuông gửi tới vai của chính những người bị giữ cộng HCNS: người trong phòng là người cần biết.
    Tin nhắn KHÔNG mang số tiền — Chủ tịch chốt phiếu lương chỉ ghi «đang giữ».
    Trả {"tin_da_xep": n, "chua_noi_zalo": [mã NV]} để màn hình nói thật ai chưa nhận được tin.
    """
    from app.services import cskh as CS
    from app.services import zalo as Z
    from app.services import zalo_nguoi_dung as ZN
    from app.models.hr import DEPARTMENTS
    da_xep, chua_noi = 0, []
    for phong, g in (run.giu_lai or {}).items():
        if g.get("bo_sung_so"):
            continue
        ten_phong = DEPARTMENTS.get(phong, phong)
        emps = list(db.execute(select(Employee).where(Employee.code.in_(g["ma"]))).scalars())
        users = {u.id: u for u in db.execute(select(User).where(
            User.id.in_([e.user_id for e in emps if e.user_id]))).scalars()} if emps else {}
        vai = sorted({u.role for u in users.values()} | {"hcns"})
        CS.giao_viec(db, CHUONG_GIU, f"luong:{run.period}:{phong}",
                     f"Lương kỳ {run.period} của {len(g['ma'])} người phòng {ten_phong} đang được giữ lại: "
                     f"{g['ly_do'].lower()}. Sẽ trả bằng bảng lương bổ sung ngay sau khi công được duyệt.",
                     nguoi_id=None, han_gio=None, roles=",".join(vai), level="warn")
        tin = (f"VTOS: Lương kỳ {run.period} của bạn đang được giữ lại vì công tháng của phòng "
               f"{ten_phong} chưa được TGĐ duyệt. Lương sẽ được trả bằng bảng lương bổ sung ngay sau "
               "khi công được duyệt.")
        for e in emps:
            uid = ZN.uid_cua(db, e.user_id) if e.user_id else ""
            if not uid:
                chua_noi.append(e.code)
                continue
            Z.queue(db, "robot_luong", zalo_uid=uid, text=tin, purpose=CHUONG_GIU)
            da_xep += 1
    return {"tin_da_xep": da_xep, "chua_noi_zalo": sorted(chua_noi)}


def _tat_chuong(db: Session, period: str, phong: str, ly_do: str) -> None:
    for a in db.execute(select(Alert).where(Alert.kind == CHUONG_GIU, Alert.ref == f"luong:{period}:{phong}",
                                            Alert.resolved == False)).scalars():  # noqa: E712
        a.resolved, a.trang_thai, a.bang_chung = True, "dong", f"Tự đóng: {ly_do}"


# ------------------------------------------------------------------ bảng bổ sung
def _run_da_ky(db: Session, period: str) -> PayrollRun:
    from app.services import hr as H
    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    if run is None or run.status not in H.DA_KY:
        raise LoiGiuLuong(f"Bảng chính kỳ {period} chưa ký – chưa có ai bị giữ để lập bảng bổ sung")
    return run


def danh_sach(db: Session, period: str) -> list[BangLuongBoSung]:
    return list(db.execute(select(BangLuongBoSung).where(BangLuongBoSung.period == period)
                           .order_by(BangLuongBoSung.so)).scalars())


def lay(db: Session, period: str, so: int) -> BangLuongBoSung:
    b = db.execute(select(BangLuongBoSung).where(BangLuongBoSung.period == period,
                                                 BangLuongBoSung.so == so)).scalars().first()
    if b is None:
        raise LoiGiuLuong(f"Không có bảng bổ sung số {so} của kỳ {period}")
    return b


def phong_lap_duoc(db: Session, run: PayrollRun) -> list[str]:
    """Phòng đang bị giữ, chưa vào bảng bổ sung nào, và công ĐÃ được duyệt."""
    from app.services import xac_nhan_cong as XNC
    return [p for p, g in (run.giu_lai or {}).items()
            if not g.get("bo_sung_so") and XNC.trang_thai(db, run.period, p)["trang_thai"] == "da_duyet"]


def lap(db: Session, u: User, period: str) -> BangLuongBoSung:
    from app.services import hr as H
    from app.services import rules as R
    if u.role not in VAI_LAP:
        raise PermissionError("Chỉ HCNS lập bảng lương bổ sung")
    run = _run_da_ky(db, period)
    phong = phong_lap_duoc(db, run)
    if not phong:
        raise LoiGiuLuong("Chưa có phòng nào bị giữ mà đã được duyệt công – chưa lập được bảng bổ sung")
    ma = {m for p in phong for m in run.giu_lai[p]["ma"]}
    rows_all, totals_all = H.compute_draft(db, period, run.inputs or {})
    rows = [r for r in rows_all if r.get("ma") in ma]
    cu = db.execute(select(BangLuongBoSung).where(BangLuongBoSung.period == period)
                    .order_by(BangLuongBoSung.so.desc())).scalars().first()
    b = BangLuongBoSung(period=period, so=(cu.so + 1) if cu else 1, phong=sorted(phong), rows=rows,
                        totals=tong_cua(rows, totals_all), status="nhap", lap_boi=u.username,
                        lap_luc=datetime.now())
    db.add(b)
    db.flush()
    gl = dict(run.giu_lai or {})
    for p in phong:
        gl[p] = {**gl[p], "bo_sung_so": b.so}
    run.giu_lai = gl                # gán lại cả từ điển: JSON không tự theo dõi sửa bên trong
    R.audit(db, u.username, u.role, "lap_bang_luong_bo_sung", f"payroll:{period}:bs{b.so}",
            after={"phong": b.phong, "so_nguoi": len(rows), "thuc_nhan": b.totals.get("thuc_nhan")})
    db.commit()
    return b


def kiem_co_so(db: Session, b: BangLuongBoSung) -> list[dict]:
    """Cờ của bảng bổ sung: cùng tinh thần `luong_khoa.kiem_co_so`, cộng hai phép riêng của nó."""
    from app.services import luong_khoa as LK
    from app.services import thu_nhap_su_kien as TN
    from app.services import xac_nhan_cong as XNC
    co: list[dict] = []
    ban_chinh = LK.ban_dang_hieu_luc(db, b.period)
    da_tra = {r.get("ma") for r in ((ban_chinh.noi_dung or {}).get("rows") or [])} if ban_chinh else set()
    for khac in danh_sach(db, b.period):
        if khac.id != b.id and khac.status == DA_KY_BS:
            da_tra |= {r.get("ma") for r in khac.rows or []}
    trung = sorted({r.get("ma") for r in b.rows or []} & da_tra)
    if trung:
        co.append({"ma": "TRA_HAI_LAN", "muc": "chan",
                   "thong_diep": f"{len(trung)} người đã có trong một bảng đã ký của kỳ này",
                   "bang_chung": {"ma_nv": trung}})
    for p in b.phong or []:
        t = XNC.trang_thai(db, b.period, p)
        if t["trang_thai"] != "da_duyet":
            co.append({"ma": "CONG_CHUA_DUYET", "muc": "chan",
                       "thong_diep": f"Phòng {p} – công kỳ {b.period}: {t['trang_thai_ten']}",
                       "bang_chung": {"phong": p, "trang_thai": t["trang_thai"]}})
    for r in b.rows or []:
        if r.get("thuc_nhan") is None:
            co.append({"ma": "THUC_NHAN_RONG", "muc": "chan",
                       "thong_diep": f"{r.get('ma')} – chưa tính được thực nhận; rỗng KHÔNG phải số 0",
                       "bang_chung": {"ma_nv": r.get("ma")}})
    co.extend(TN.kiem_trung(db, b.period, b.rows or []))
    return co


def chay_kiem(db: Session, u: User, b: BangLuongBoSung) -> dict:
    from app.services import luong_khoa as LK
    from app.services import rules as R
    if b.status not in ("nhap", "da_kiem_co_so"):
        raise LoiGiuLuong(f"Bảng bổ sung số {b.so} đã qua bước kiểm (đang ở '{b.status}')")
    co = kiem_co_so(db, b)
    chan = LK.co_chan(co)
    if not chan and b.status == "nhap":
        b.status = "da_kiem_co_so"
        R.audit(db, u.username, u.role, "bang_luong_bo_sung_kiem_co_so", f"payroll:{b.period}:bs{b.so}",
                after={"so_co": len(co)})
        db.commit()
    return {"dat": not chan, "co": co, "trang_thai": b.status}


def tien(db: Session, u: User, b: BangLuongBoSung) -> str:
    """Bước tiếp theo — CÙNG CHUỖI với bảng chính (Chủ tịch chốt 21/10/2026)."""
    from app.services import hr as H
    from app.services import luong_khoa as LK
    from app.services import rules as R
    if b.status == "nhap":
        raise LoiGiuLuong("Bảng bổ sung chưa qua bước kiểm cơ sở")
    if b.status == "da_kiem_co_so" and u.role == "hcns":
        b.status, b.hcns_by, b.hcns_at = "hcns_kiem", u.username, datetime.now()
        msg = f"HCNS đã kiểm bảng bổ sung số {b.so} – chờ Chủ tịch hoặc TGĐ ký"
    elif b.status == "hcns_kiem" and u.role in VAI_KY:
        # Kiểm lại ngay trước chữ ký: từ lúc kiểm cơ sở tới giờ có thể đã có thay đổi.
        chan = LK.co_chan(kiem_co_so(db, b))
        if chan:
            raise LoiGiuLuong("Chưa ký được: " + "; ".join(c["thong_diep"] for c in chan))
        ban = LK.khoa(db, SimpleNamespace(period=b.period, rows=b.rows or [], totals=b.totals or {}), u,
                      bo_sung_so=b.so)
        b.status, b.ky_boi, b.ky_vai, b.ky_luc, b.ban_khoa_id = DA_KY_BS, u.username, u.role, datetime.now(), ban.id
        b.entry_ids = H.post_payroll_entries(db, SimpleNamespace(period=b.period, rows=b.rows or []),
                                             bo_sung_so=b.so)
        for p in b.phong or []:
            _tat_chuong(db, b.period, p, f"đã ký bảng bổ sung số {b.so}")
        msg = (f"{'Chủ tịch' if u.role == 'chutich' else 'TGĐ'} đã ký bảng bổ sung số {b.so} kỳ {b.period} – "
               f"đã khoá bản {ban.ban_so}")
    else:
        raise PermissionError(f"Vai trò {u.role} không thực hiện được bước này ở trạng thái {b.status}")
    R.audit(db, u.username, u.role, f"bang_luong_bo_sung_{b.status}", f"payroll:{b.period}:bs{b.so}",
            after={"thuc_nhan": (b.totals or {}).get("thuc_nhan")})
    db.commit()
    return msg


# ------------------------------------------------------------------ phiếu lương
def tinh_trang_nguoi(db: Session, run: PayrollRun, ma: str) -> dict:
    """Một người trong kỳ: đang giữ / đã trả qua bảng bổ sung số mấy / không bị giữ."""
    from app.models.hr import DEPARTMENTS
    for phong, g in (run.giu_lai or {}).items():
        if ma in (g.get("ma") or []):
            so = g.get("bo_sung_so")
            if so:
                b = lay(db, run.period, so)
                if b.status == DA_KY_BS:
                    return {"dang_giu": False, "bo_sung_so": so,
                            "dong": next((r for r in b.rows or [] if r.get("ma") == ma), None)}
            return {"dang_giu": True, "phong": phong,
                    "thong_bao": (f"Lương kỳ này đang giữ lại: công phòng {DEPARTMENTS.get(phong, phong)} "
                                  "chưa được TGĐ duyệt. Sẽ trả bằng bảng lương bổ sung ngay sau khi công "
                                  "được duyệt.")}
    return {"dang_giu": False}


def ra(b: BangLuongBoSung) -> dict:
    return {"id": b.id, "period": b.period, "so": b.so, "phong": b.phong, "rows": b.rows, "totals": b.totals,
            "status": b.status, "status_ten": TRANG_THAI_BS.get(b.status, b.status), "lap_boi": b.lap_boi,
            "lap_luc": b.lap_luc, "hcns_by": b.hcns_by, "hcns_at": b.hcns_at, "ky_boi": b.ky_boi,
            "ky_vai": b.ky_vai, "ky_luc": b.ky_luc, "ban_khoa_id": b.ban_khoa_id, "entry_ids": b.entry_ids}
