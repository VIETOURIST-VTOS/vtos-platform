"""Đối chiếu và nạp danh sách tài xế – xe.

Nguyên tắc (anh Tuấn chốt 06/9/2026): xe thuộc Công ty TNHH Vận tải Vietrip, tài xế hưởng lương ở công ty
mẹ Vietourist Holdings. Hàm này KHÔNG xóa dữ liệu và KHÔNG đoán: hồ sơ trùng tên, xe lạ và xe thiếu số
chỗ đều được báo ra để người có thẩm quyền quyết định.
"""
import re
import unicodedata
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.core import Company
from app.models.hr import Employee, Vehicle
from app.services import rules as R


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def norm_plate(s: str) -> str:
    """50F022.59, 50F-022.59, 50f 022,59 → 50F02259 (so khớp không phụ thuộc dấu phân cách)."""
    return re.sub(r"[^0-9A-Z]", "", (s or "").upper())


def pretty_plate(s: str) -> str:
    """Viết biển số theo đúng kiểu đang dùng trong hệ thống: 50H934.08 → 50H-934.08."""
    raw = norm_plate(s)
    m = re.fullmatch(r"(\d{2}[A-Z]{1,2})(\d{3})(\d{2})", raw)
    return f"{m.group(1)}-{m.group(2)}.{m.group(3)}" if m else (s or "").strip()


def _dob(v) -> date | None:
    if isinstance(v, datetime): return v.date()
    if isinstance(v, date): return v
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try: return datetime.strptime(str(v).strip(), f).date()
        except (ValueError, TypeError): pass
    return None


def reconcile(db: Session, rows: list[dict]) -> dict:
    """So danh sách với dữ liệu đang có. Chỉ đọc, không ghi."""
    emps = list(db.execute(select(Employee)).scalars())
    veh = list(db.execute(select(Vehicle)).scalars())
    by_name: dict[str, list[Employee]] = {}
    for e in emps: by_name.setdefault(norm_name(e.full_name), []).append(e)
    by_plate = {norm_plate(v.plate): v for v in veh}
    ds_plates, ds_names = set(), set()
    khop, thieu_xe, trung_ho_so, chua_co_ho_so = [], [], [], []
    for r in rows:
        ten, bien = r.get("full_name") or r.get("ten") or "", r.get("plate") or r.get("bien_so") or ""
        n, pl = norm_name(ten), norm_plate(bien)
        ds_names.add(n); ds_plates.add(pl)
        cand = by_name.get(n, [])
        if len(cand) > 1: trung_ho_so.append({"ten": ten, "ma": [c.code for c in cand]})
        if not cand: chua_co_ho_so.append({"ten": ten, "bien_so": bien})
        if pl not in by_plate: thieu_xe.append({"ten": ten, "bien_so": bien})
        if cand and pl in by_plate: khop.append({"ten": ten, "bien_so": by_plate[pl].plate})
    lai_xe_ngoai_ds = [{"ma": e.code, "ten": e.full_name} for e in emps
                       if (e.department == "doi_xe" or e.position == "tai_xe") and norm_name(e.full_name) not in ds_names and e.active]
    xe_ngoai_ds = [{"bien_so": v.plate, "tai_xe": next((e.full_name for e in emps if e.id == v.driver_id), ""), "loai": v.kind}
                   for v in veh if norm_plate(v.plate) not in ds_plates]
    return {"trong_danh_sach": len(rows), "khop": khop, "thieu_xe_trong_he_thong": thieu_xe,
            "chua_co_ho_so_nhan_su": chua_co_ho_so, "ho_so_trung_ten": trung_ho_so,
            "tai_xe_trong_he_thong_ngoai_danh_sach": lai_xe_ngoai_ds, "xe_trong_he_thong_ngoai_danh_sach": xe_ngoai_ds}


def apply(db: Session, rows: list[dict], actor: str, role: str, tao_xe_thieu: bool = False) -> dict:
    """Cập nhật ngày sinh, số điện thoại, bộ phận/chức danh, công ty chủ quản và gán tài xế cho xe.

    Không tạo hồ sơ nhân sự mới và không tạo xe mới trừ khi được yêu cầu rõ (tao_xe_thieu=True) –
    xe tạo tự động để số chỗ = 0 để buộc bổ sung.
    """
    me = db.execute(select(Company).where(Company.code == "VTD")).scalars().first()
    vt = db.execute(select(Company).where(Company.code == "VTRIP-VT")).scalars().first()
    emps = list(db.execute(select(Employee)).scalars())
    by_name: dict[str, list[Employee]] = {}
    for e in emps: by_name.setdefault(norm_name(e.full_name), []).append(e)
    by_plate = {norm_plate(v.plate): v for v in db.execute(select(Vehicle)).scalars()}
    ns, xe_moi, gan_xe, bo_qua = 0, [], 0, []
    for r in rows:
        ten = r.get("full_name") or r.get("ten") or ""
        bien = r.get("plate") or r.get("bien_so") or ""
        ma = (r.get("employee_code") or "").strip()
        cand = [x for x in emps if x.code == ma] if ma else by_name.get(norm_name(ten), [])
        if len(cand) != 1:
            ly_do = "không có hồ sơ" if not cand else f"trùng {len(cand)} hồ sơ – ghi rõ mã nhân sự để chỉ đích danh"
            bo_qua.append({"ten": ten, "ly_do": ly_do})
            continue
        e = cand[0]
        d = _dob(r.get("birth_date") or r.get("ngay_sinh"))
        if d: e.birth_date = d
        if r.get("phone") or r.get("dien_thoai"): e.phone = str(r.get("phone") or r.get("dien_thoai")).strip()[:30]
        e.department, e.position = "doi_xe", "tai_xe"
        if me: e.company_id = me.id            # tài xế hưởng lương ở công ty mẹ
        ns += 1
        v = by_plate.get(norm_plate(bien))
        if v is None and tao_xe_thieu and bien.strip():
            v = Vehicle(plate=pretty_plate(bien), seats=0, kind="noi_bo", company_id=vt.id if vt else None)
            db.add(v); db.flush(); by_plate[norm_plate(bien)] = v
            xe_moi.append(v.plate)
        if v is not None:
            v.driver_id = e.id
            if vt and not v.company_id: v.company_id = vt.id
            gan_xe += 1
    R.audit(db, actor, role, "nap_danh_sach_tai_xe", "doi_xe",
            after={"nhan_su": ns, "gan_xe": gan_xe, "xe_moi": xe_moi, "bo_qua": bo_qua})
    db.commit()
    return {"cap_nhat_nhan_su": ns, "gan_tai_xe_cho_xe": gan_xe, "xe_tao_moi": xe_moi, "bo_qua": bo_qua,
            "message": f"Đã cập nhật {ns} hồ sơ tài xế, gán {gan_xe} xe"
                       + (f", tạo mới {len(xe_moi)} xe (số chỗ = 0, cần bổ sung)" if xe_moi else "")
                       + (f"; bỏ qua {len(bo_qua)} dòng" if bo_qua else "")}
