# -*- coding: utf-8 -*-
"""BẢNG SẴN SÀNG VẬN HÀNH ĐỘI XE — Chủ tịch duyệt bản xem trước 10/11/2026.

Một màn đếm CÒN THIẾU GÌ để đội xe chạy thật trên VTOS, chia năm nhóm (xe · người · tham số · chi phí kỳ ·
việc đang treo). Mỗi dòng máy đếm từ dữ liệu thật và trỏ đúng cửa nhập; không dòng nào tự điền số hộ.

Ba mức: `ok` đã đủ · `warn` thiếu nhưng vẫn chạy được (báo cáo sẽ ghi «Chưa nhập») · `bad` thiếu thì một
bước của luồng hỏng (lệnh bị chặn, tài xế không đăng nhập được, chuyến về mà không ai báo cáo).
Hỏi CHÍNH các hàm luật đang có (`fleet.san_sang`, `tinh_trang_bao_duong`, `cap_duyet`…) — không suy lại.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.hr import DispatchOrder, Employee, Vehicle


def _dong(nhom, ma, ten, so, dat, muc_thieu="warn", mo="", nut="Mở", ghi=""):
    return {"nhom": nhom, "ma": ma, "ten": ten, "so": so, "dat": bool(dat),
            "muc": "ok" if dat else muc_thieu, "mo": mo, "nut": nut, "ghi": ghi}


def bang(db: Session, ky: str | None = None) -> dict:
    from app.api.v1.fleet import _chan_khi_thieu_giay
    from app.models.fleet import FleetPeriodCost, FuelNorm, GiaDauNgay, Trip
    from app.services import fleet as FL
    from app.services import ops as O
    hom = date.today()
    ky = ky or hom.strftime("%Y-%m")
    y, m = map(int, ky.split("-"))
    d1 = date(y, m, 1)
    d2 = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
    ds: list[dict] = []

    # ── XE ──────────────────────────────────────────────────────────────────────────────────────────
    xe = list(db.execute(select(Vehicle).where(Vehicle.active.is_(True))).scalars())
    chan = _chan_khi_thieu_giay(db)
    muc = {v.id: FL.san_sang(db, v, chan)["muc"] for v in xe}
    bi_chan = [v.plate for v in xe if muc[v.id] == "BLOCK"]
    thieu = [v.plate for v in xe if muc[v.id] == "UNKNOWN"]
    chua_km = [v.plate for v in xe if v.odo_km is None]
    chua_bd = [v.plate for v in xe if FL.tinh_trang_bao_duong(db, v).get("ma") == "CHUA_BIET_MOC_BAO_DUONG"]
    chua_tx = [v.plate for v in xe if not v.driver_id]
    ds += [
        _dong("xe", "xe_khai_thac", "Xe đang khai thác", len(xe), len(xe) > 0, "bad", "ho-so-xe", "Mở hồ sơ xe"),
        _dong("xe", "xe_bi_chan", "Xe thiếu giấy tờ / bị chặn điều", len(bi_chan), not bi_chan, "bad", "ho-so-xe",
              "Mở hồ sơ xe", ", ".join(bi_chan[:6])),
        _dong("xe", "xe_thieu_du_lieu", "Xe chưa đủ dữ liệu để kiểm sẵn sàng", len(thieu), not thieu, "warn", "ho-so-xe",
              "Mở hồ sơ xe", ", ".join(thieu[:6])),
        _dong("xe", "xe_chua_km", "Xe chưa có số km đồng hồ xác nhận", len(chua_km), not chua_km, "warn", "ho-so-xe",
              "Mở hồ sơ xe", ", ".join(chua_km[:6])),
        _dong("xe", "xe_chua_bao_duong", "Xe chưa có phiếu bảo dưỡng gần nhất", len(chua_bd), not chua_bd, "warn",
              "bao-duong", "Mở bảo dưỡng", ", ".join(chua_bd[:6])),
        _dong("xe", "xe_chua_tai_xe", "Xe chưa gán tài xế mặc định", len(chua_tx), not chua_tx, "warn", "tai-xe",
              "Mở tài xế", ", ".join(chua_tx[:6])),
    ]

    # ── NGƯỜI ───────────────────────────────────────────────────────────────────────────────────────
    gd = db.execute(select(User).where(User.role == "gd_doi_xe", User.active.is_(True))).scalars().first()
    tai_xe = list(db.execute(select(Employee).where(Employee.position == "tai_xe", Employee.active.is_(True))).scalars())
    nguoi = {u.id: u for u in db.execute(select(User).where(User.id.in_([e.user_id for e in tai_xe if e.user_id]))).scalars()}
    chua_tk = [e.full_name for e in tai_xe
               if not e.user_id or e.user_id not in nguoi or not nguoi[e.user_id].active or nguoi[e.user_id].role != "tai_xe"]
    co_xe = {v.driver_id for v in xe if v.driver_id}
    chua_gan = [e.full_name for e in tai_xe if e.id not in co_xe]
    ds += [
        _dong("nguoi", "co_gd_doi_xe", "Có người giữ vai Giám đốc đội xe", 1 if gd else 0, gd is not None, "bad", "", "",
              gd.full_name if gd else "HCNS cấp vai «Giám đốc điều hành đội xe»"),
        _dong("nguoi", "tai_xe_chua_tai_khoan", "Tài xế chưa có tài khoản đăng nhập", len(chua_tk), not chua_tk, "bad",
              "tai-xe", "Mở tài xế", ", ".join(chua_tk[:6]) + (" — HCNS cấp tài khoản vai Tài xế" if chua_tk else "")),
        _dong("nguoi", "tai_xe_chua_gan_xe", "Tài xế chưa gắn với xe nào", len(chua_gan), not chua_gan, "warn",
              "tai-xe", "Mở tài xế", ", ".join(chua_gan[:6])),
    ]

    # ── THAM SỐ ─────────────────────────────────────────────────────────────────────────────────────
    moc = O.nguong_chu_tich_dang_hieu_luc(db)
    gia = db.execute(select(GiaDauNgay).where(GiaDauNgay.ngay >= d1, GiaDauNgay.ngay <= d2)).scalars().first()
    da_dm = {n.seats for n in db.execute(select(FuelNorm)).scalars() if n.l_100km}
    thieu_dm = sorted({v.seats for v in xe if v.seats} - da_dm)
    from app.models.fleet import Collateral
    the_chap = db.execute(select(Collateral).where(Collateral.den_ngay.is_(None))).scalars().first()
    ds += [
        _dong("tham_so", "moc_duyet_chi", "Mốc Chủ tịch duyệt chi đã chốt", None, moc is not None, "bad", "", "",
              "" if moc is not None else "Chưa chốt mốc — đề nghị chi nằm chờ"),
        _dong("tham_so", "gia_dau_ky", f"Giá dầu kỳ {m:02d}/{y}", None, gia is not None, "warn", "dau", "Mở dầu",
              "" if gia else "Chưa khai ngày nào — tiêu hao không tính được lít"),
        _dong("tham_so", "dinh_muc_dau", "Định mức dầu theo nhóm chỗ", len(thieu_dm), not thieu_dm, "warn", "dau",
              "Mở định mức", ("Thiếu nhóm " + ", ".join(f"{s} chỗ" for s in thieu_dm)) if thieu_dm else ""),
        _dong("tham_so", "khe_uoc_the_chap", "Khế ước vay có xe thế chấp", None, the_chap is not None, "warn",
              "cong-no", "Mở công nợ", "" if the_chap else "Chưa có — lãi vay theo khế ước sẽ ghi «Chưa nhập»"),
    ]

    # ── CHI PHÍ KỲ ──────────────────────────────────────────────────────────────────────────────────
    co = {k.nhom for k in db.execute(select(FleetPeriodCost).where(FleetPeriodCost.ky == ky)).scalars()}
    for ma, ten, nhom in (("cp_luong", "lương tài xế", ("luong_tai_xe",)),
                          ("cp_bai", "bãi xe, điện nước", ("bai_xe", "dien_nuoc")),
                          ("cp_bao_hiem", "bảo hiểm, đăng kiểm", ("bao_hiem", "dang_kiem")),
                          ("cp_lai_vay", "lãi vay", ("lai_vay",))):
        ds.append(_dong("ky", ma, f"Chi phí kỳ: {ten}", None, bool(co & set(nhom)), "warn", "quyet-toan", "Nhập",
                        "" if co & set(nhom) else "Chưa nhập"))

    # ── VIỆC ĐANG TREO ──────────────────────────────────────────────────────────────────────────────
    lenh = list(db.execute(select(DispatchOrder).where(DispatchOrder.status != "huy",
                                                       DispatchOrder.date_from >= hom - timedelta(days=60))).scalars())
    chua_nhan = [x for x in lenh if x.nhan_luc is None and x.date_from >= hom]
    co_phieu = {t.dispatch_id for t in db.execute(select(Trip).where(Trip.status != "huy",
                                                                    Trip.dispatch_id.isnot(None))).scalars()}
    chua_bc = [x for x in lenh if x.date_to < hom and x.id not in co_phieu]
    tra_lai = db.execute(select(Trip).where(Trip.qt_trang_thai == "tra_lai")).scalars().all()
    ds += [
        _dong("treo", "lenh_chua_nhan", "Lệnh tài xế chưa nhận", len(chua_nhan), not chua_nhan, "warn", "lich", "Mở lệnh"),
        _dong("treo", "lenh_ve_chua_bao_cao", "Lệnh đã về mà chưa có báo cáo xe", len(chua_bc), not chua_bc, "bad",
              "bao-cao-xe", "Nhập báo cáo"),
        _dong("treo", "to_tra_lai", "Tờ báo cáo xe bị trả lại", len(tra_lai), not tra_lai, "warn", "bao-cao-xe", "Mở"),
    ]
    dat = sum(1 for x in ds if x["dat"])
    return {"ky": ky, "dong": ds, "dat": dat, "tong": len(ds), "du": dat == len(ds),
            "nhom": {"xe": "Xe", "nguoi": "Người", "tham_so": "Tham số", "ky": f"Kỳ {m:02d}/{y}", "treo": "Việc đang treo"}}
