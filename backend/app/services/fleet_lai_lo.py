"""Lãi lỗ đội xe: ba tầng chi phí, và không tầng nào được lẫn vào tầng nào.

Bảng quyết toán xe tháng 6/2026 dạy đúng một bài học, và cả tệp này là để giữ nó:

    Cộng lãi gộp của 21 chiếc được 938 triệu. Sau bảo hiểm, lương tài xế, bãi xe và 327 triệu lãi vay
    thì đội xe còn 227 triệu. Ai chỉ nhìn tầng đầu tưởng đội xe lãi gấp hơn bốn lần thực tế.

Ba tầng:

  Tầng 1 – CHI PHÍ CHUYẾN: dầu, cầu đường, công tác phí, gửi xe. Ra "lãi gộp chuyến". Đây là con số
          dùng để so tuyến với tuyến và để biết một chuyến có đáng chạy không.
  Tầng 2 – CHI PHÍ CỦA XE trong kỳ: bảo hiểm, đăng kiểm, bảo dưỡng, lương tài xế, wifi, phân bổ chi
          phí trả trước. Quy được về từng chiếc, nên trừ thẳng vào kết quả chiếc đó.
  Tầng 3 – CHI PHÍ CỦA ĐỘI: bãi xe, điện nước, phí quản lý, BHXH, và lãi vay. KHÔNG quy về xe nào.

Vì sao tầng 3 mặc định KHÔNG chia về từng xe: chia 327 triệu lãi vay cho 21 chiếc theo doanh thu, theo
ngày chạy hay chia đều đều ra những con số khác nhau và đều "có lý". Người đọc bảng lại nhớ con số cuối
cùng như kết quả thật của chiếc xe, rồi lấy nó ra quyết định bán xe hay đổi tài xế. Nên mặc định để
riêng một khối – đúng như bảng Excel đang làm – và ai muốn xem thử khi phân bổ thì phải CHỌN tiêu thức,
và bảng ghi rõ đó là số phân bổ.
"""
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.fleet import Trip, TripCost, Maintenance, FleetPeriodCost, NHOM_CHI_PHI_KY
from app.models.hr import Vehicle, Employee
from app.services import fleet_settlement as QT

TIEU_THUC = {"khong": "Không phân bổ (khuyến nghị)",
             "ngay_khai_thac": "Theo ngày khai thác của từng xe",
             "doanh_thu": "Theo doanh thu của từng xe",
             "deu": "Chia đều cho số xe có khai thác"}


def _km(t: Trip) -> int:
    if t.km_dau is None or t.km_cuoi is None or t.km_cuoi < t.km_dau: return 0
    return t.km_cuoi - t.km_dau


def theo_chuyen(db: Session, ky: str) -> list[dict]:
    """Quyết toán theo TOUR: mỗi chuyến một dòng, lãi gộp và suất tiêu hao của chính chuyến đó."""
    d1, d2 = QT.ky_range(ky)
    trips = list(db.execute(select(Trip).where(Trip.ngay_di >= d1, Trip.ngay_di <= d2)
                            .order_by(Trip.ngay_di)).scalars())
    chi: dict[int, list] = {}
    if trips:
        for c in db.execute(select(TripCost).where(TripCost.trip_id.in_([t.id for t in trips]))).scalars():
            chi.setdefault(c.trip_id, []).append(c)
    veh = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    out = []
    for t in trips:
        v = veh.get(t.vehicle_id)
        cs = chi.get(t.id, [])
        km = _km(t)
        tien_dau = sum((c.amount or 0) for c in cs if c.kind == "dau")
        lit = sum(c.lit or 0 for c in cs if c.kind == "dau")
        cp = sum((c.amount or 0) for c in cs)
        did = t.driver_id or (v.driver_id if v else None)
        out.append({
            "trip_id": t.id, "ma_phieu": t.ma_phieu, "xe": v.plate if v else "",
            "tai_xe": emps.get(did, ""), "ten_tour": t.ten_tour,
            "ngay_di": t.ngay_di, "ngay_ve": t.ngay_ve,
            "so_ngay": (t.ngay_ve - t.ngay_di).days + 1,
            "doanh_thu": t.doanh_thu, "chi_phi_chuyen": cp,
            "lai_gop": (t.doanh_thu or 0) - cp,
            "ty_le": (round(((t.doanh_thu or 0) - cp) / (t.doanh_thu or 0), 4) if (t.doanh_thu or 0) else None),
            "km": km or None, "tien_dau": tien_dau, "so_lit": lit or None,
            # Suất tiêu hao và giá dầu trên km chỉ tính khi có đủ dữ liệu – thiếu km hay thiếu lít thì
            # trả về trống, không trả 0. Số 0 ở đây đọc ra là "xe không tốn dầu".
            "km_moi_lit": (round(km / lit, 2) if km and lit else None),
            "dau_moi_km": (round(tien_dau / km) if km and tien_dau else None),
            "chi_tiet": {c.kind: c.amount for c in cs},
        })
    return out


def _rong(v: Vehicle | None, vid: int | None) -> dict:
    return {"vehicle_id": vid, "xe": v.plate if v else "", "ma_xe": v.code if v else "",
            "tai_xe": "", "so_chuyen": 0, "doanh_thu": 0.0, "chi_phi_chuyen": 0.0,
            "km": 0, "so_lit": 0.0, "ngay_khai_thac": set(), "chi_phi_xe": 0.0,
            "chi_tiet_cp_xe": {}}


def bao_cao(db: Session, ky: str, phan_bo: str = "khong") -> dict:
    """Báo cáo lãi lỗ đội xe của một kỳ."""
    if phan_bo not in TIEU_THUC: raise ValueError(f"Tiêu thức phân bổ không hợp lệ: {phan_bo}")
    d1, d2 = QT.ky_range(ky)
    so_ngay_ky = (d2 - d1).days + 1
    veh = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    rows: dict[int, dict] = {}

    # --- Tầng 1: chuyến ---
    for c in theo_chuyen(db, ky):
        t = db.get(Trip, c["trip_id"])
        r = rows.setdefault(t.vehicle_id, _rong(veh.get(t.vehicle_id), t.vehicle_id))
        did = t.driver_id or (veh[t.vehicle_id].driver_id if t.vehicle_id in veh else None)
        if did and not r["tai_xe"]: r["tai_xe"] = emps.get(did, "")
        r["so_chuyen"] += 1
        r["doanh_thu"] += c["doanh_thu"]; r["chi_phi_chuyen"] += c["chi_phi_chuyen"]
        r["km"] += c["km"] or 0; r["so_lit"] += c["so_lit"] or 0
        r["ngay_khai_thac"] |= {t.ngay_di + timedelta(days=i)
                                for i in range((t.ngay_ve - t.ngay_di).days + 1)}

    # --- Tầng 2: chi phí của xe trong kỳ ---
    for m in db.execute(select(Maintenance).where(Maintenance.ngay >= d1, Maintenance.ngay <= d2)).scalars():
        r = rows.setdefault(m.vehicle_id, _rong(veh.get(m.vehicle_id), m.vehicle_id))
        r["chi_phi_xe"] += (m.so_tien or 0)
        r["chi_tiet_cp_xe"]["bao_duong"] = r["chi_tiet_cp_xe"].get("bao_duong", 0) + (m.so_tien or 0)

    cp_doi, chi_tiet_doi = 0.0, {}
    for k in db.execute(select(FleetPeriodCost).where(FleetPeriodCost.ky == ky)).scalars():
        if k.pham_vi == "xe" and k.vehicle_id:
            r = rows.setdefault(k.vehicle_id, _rong(veh.get(k.vehicle_id), k.vehicle_id))
            r["chi_phi_xe"] += (k.so_tien or 0)
            r["chi_tiet_cp_xe"][k.nhom] = r["chi_tiet_cp_xe"].get(k.nhom, 0) + (k.so_tien or 0)
        else:
            cp_doi += (k.so_tien or 0)
            chi_tiet_doi[k.nhom] = chi_tiet_doi.get(k.nhom, 0) + (k.so_tien or 0)

    # --- Kết quả từng xe ---
    ds = []
    for r in rows.values():
        ngay = len(r["ngay_khai_thac"])
        lai_gop = r["doanh_thu"] - r["chi_phi_chuyen"]
        ds.append({**{k: v for k, v in r.items() if k != "ngay_khai_thac"},
                   "ngay_khai_thac": ngay,
                   "cong_suat": round(ngay / so_ngay_ky, 4) if so_ngay_ky else None,
                   "lai_gop_chuyen": lai_gop,
                   "ket_qua_xe": lai_gop - r["chi_phi_xe"],
                   "km_moi_lit": (round(r["km"] / r["so_lit"], 2) if r["km"] and r["so_lit"] else None),
                   "ty_le_lai_gop": (round(lai_gop / r["doanh_thu"], 4) if r["doanh_thu"] else None)})
    ds.sort(key=lambda x: -x["ket_qua_xe"])

    tong_dt = sum(x["doanh_thu"] for x in ds)
    tong_cp_chuyen = sum(x["chi_phi_chuyen"] for x in ds)
    tong_cp_xe = sum(x["chi_phi_xe"] for x in ds)
    tong_ngay = sum(x["ngay_khai_thac"] for x in ds)

    # --- Phân bổ tầng 3, chỉ khi được yêu cầu và có ghi rõ ---
    if phan_bo != "khong" and cp_doi and ds:
        mau = {"ngay_khai_thac": tong_ngay, "doanh_thu": tong_dt,
               "deu": len([x for x in ds if x["ngay_khai_thac"]])}[phan_bo]
        for x in ds:
            tu = (x["ngay_khai_thac"] if phan_bo == "ngay_khai_thac"
                  else x["doanh_thu"] if phan_bo == "doanh_thu"
                  else (1 if x["ngay_khai_thac"] else 0))
            x["phan_bo_chi_phi_doi"] = round(cp_doi * tu / mau) if mau else 0
            x["ket_qua_sau_phan_bo"] = x["ket_qua_xe"] - x["phan_bo_chi_phi_doi"]

    thieu = [NHOM_CHI_PHI_KY[n][0] for n, (_, pv) in
             ((n, NHOM_CHI_PHI_KY[n]) for n in NHOM_CHI_PHI_KY)
             if pv == "doi" and n not in chi_tiet_doi]

    return {
        "ky": ky, "so_ngay_ky": so_ngay_ky, "phan_bo": phan_bo, "tieu_thuc": TIEU_THUC,
        "xe": ds,
        "tong": {
            "doanh_thu": tong_dt,
            "chi_phi_chuyen": tong_cp_chuyen,
            "lai_gop_chuyen": tong_dt - tong_cp_chuyen,
            "chi_phi_xe": tong_cp_xe,
            "ket_qua_sau_chi_phi_xe": tong_dt - tong_cp_chuyen - tong_cp_xe,
            "chi_phi_doi": cp_doi,
            "loi_nhuan": tong_dt - tong_cp_chuyen - tong_cp_xe - cp_doi,
            "ty_le_loi_nhuan": (round((tong_dt - tong_cp_chuyen - tong_cp_xe - cp_doi) / tong_dt, 4)
                                if tong_dt else None),
            "so_xe_khai_thac": len([x for x in ds if x["ngay_khai_thac"]]),
            "ngay_khai_thac": tong_ngay,
            # Công suất tính trên số xe CÓ trong đội, không phải số xe có chạy: mẫu số bằng số xe chạy
            # thì một chiếc nằm bãi cả tháng biến mất khỏi phép tính, và công suất luôn đẹp.
            "so_xe_trong_doi": len([v for v in veh.values() if v.active]),
            "cong_suat": (round(tong_ngay / (len([v for v in veh.values() if v.active]) * so_ngay_ky), 4)
                          if veh and so_ngay_ky else None),
        },
        "chi_tiet_chi_phi_doi": [{"nhom": k, "ten": NHOM_CHI_PHI_KY.get(k, (k,))[0], "so_tien": v}
                                 for k, v in sorted(chi_tiet_doi.items(), key=lambda kv: -kv[1])],
        "nhom_chi_phi_doi_chua_nhap": thieu,
        "ghi_chu": ("Ba tầng chi phí để riêng: chi phí chuyến, chi phí của xe, chi phí của đội. "
                    "Chi phí đội mặc định KHÔNG chia về từng xe – chia theo tiêu thức nào cũng ra một "
                    "con số khác, mà người đọc lại nhớ nó như kết quả thật của chiếc xe."),
    }
