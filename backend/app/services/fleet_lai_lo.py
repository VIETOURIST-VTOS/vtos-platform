"""Lãi lỗ đội xe: ba tầng chi phí, và không tầng nào được lẫn vào tầng nào.

Bảng quyết toán xe tháng 6/2026 dạy đúng một bài học, và cả tệp này là để giữ nó:

    Cộng lãi gộp của 21 chiếc được 938 triệu. Sau bảo hiểm, lương tài xế, bãi xe và 327 triệu lãi vay
    thì đội xe còn 227 triệu. Ai chỉ nhìn tầng đầu tưởng đội xe lãi gấp hơn bốn lần thực tế.

Ba tầng:

  Tầng 1 – CHI PHÍ CHUYẾN: dầu, cầu đường, công tác phí, gửi xe. Ra "lãi gộp chuyến". Đây là con số
          dùng để so tuyến với tuyến và để biết một chuyến có đáng chạy không.
  Tầng 2 – CHI PHÍ CỦA XE trong kỳ: bảo hiểm, đăng kiểm, bảo dưỡng, lương tài xế, wifi, phân bổ chi
          phí trả trước. Quy được về từng chiếc, nên trừ thẳng vào kết quả chiếc đó.
  Tầng 3 – CHI PHÍ CỦA ĐỘI: bãi xe, điện nước, phí quản lý, BHXH. KHÔNG quy về xe nào.

Và một nhóm thứ tư nằm NGOÀI cả ba tầng:

  NGOÀI GIÁ VỐN – lãi vay xe. Chủ tịch quyết 11/10/2026: lãi vay không tính vào giá vốn. Nó là chi phí
          tài chính (TK 635), không phải giá vốn vận tải. Báo cáo cho ra HAI con số tách bạch: "lợi
          nhuận đội xe theo giá vốn vận tải", rồi dưới nó "trừ lãi vay" và "kết quả sau lãi vay".
          Danh sách nhóm nào ngoài giá vốn do `NGOAI_GIA_VON` trong mô hình khai, không rải trong mã.

Vì sao tầng 3 mặc định KHÔNG chia về từng xe: chia chi phí đội cho 21 chiếc theo doanh thu, theo ngày
chạy hay chia đều đều ra những con số khác nhau và đều "có lý". Người đọc bảng lại nhớ con số cuối cùng
như kết quả thật của chiếc xe, rồi lấy nó ra quyết định bán xe hay đổi tài xế. Nên mặc định để riêng
một khối – đúng như bảng Excel đang làm – và ai muốn xem thử khi phân bổ thì phải CHỌN tiêu thức, và
bảng ghi rõ đó là số phân bổ.

Phần ngoài giá vốn thì KHÔNG phân bổ về xe trong bất kỳ tiêu thức nào. Gán lãi vay lên đầu một chiếc xe
là nói rằng chiếc ấy lỗ vì nó chạy kém, trong khi nó lỗ vì công ty vay tiền mua nó – hai việc khác nhau
và chỉ một trong hai là việc của người điều hành đội xe.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.fleet import (Trip, TripCost, Maintenance, FleetPeriodCost, ExternalTxn,
                              NHOM_CHI_PHI_KY, NGOAI_GIA_VON, NGA_CHI_PHI, NGA_CUA_DOI_XE)
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
    # Nháp và đã hủy không phải số liệu – xem chú thích cùng luật ở fleet_ai.hieu_qua_ky.
    trips = list(db.execute(select(Trip).where(Trip.ngay_di >= d1, Trip.ngay_di <= d2,
                                               Trip.status.not_in(("nhap", "huy")))
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
        # BÊN CHỊU: dòng `chu_xe` là khoản chủ xe tự gánh – có thật, nhưng không nằm trong lãi lỗ của
        # Vietourist. Tách ra chứ không bỏ đi, để còn đối chiếu được tổng tiền đã chi cho chuyến.
        cs_vt = [c for c in cs if c.ben_chiu != "chu_xe"]
        tien_dau = sum((c.amount or 0) for c in cs_vt if c.kind == "dau")
        lit = sum(c.lit or 0 for c in cs_vt if c.kind == "dau")
        cp = sum((c.amount or 0) for c in cs_vt)
        cp_chu_xe = sum((c.amount or 0) for c in cs if c.ben_chiu == "chu_xe")
        did = t.driver_id or (v.driver_id if v else None)
        out.append({
            "trip_id": t.id, "ma_phieu": t.ma_phieu, "xe": v.plate if v else "",
            # KS-65 · 09/11/2026 — nói ra chuyến này đã quyết toán chưa. Bảng theo chuyến vẫn in
            # ĐỦ mọi chuyến (người điều hành cần thấy chuyến đang chạy), nhưng dòng nào chưa quyết
            # toán thì phải tự khai, vì lãi gộp của nó là doanh thu TRỪ một tập chi phí chưa nhập
            # xong — một con số đẹp hơn sự thật.
            "quyet_toan": bool(t.quyet_toan),
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
            "chi_phi_chu_xe": 0.0, "chi_tiet_cp_xe": {}}


def ngoai_so(db: Session, d1: date, d2: date) -> dict:
    """Tiền đã nạp vào `fleet_external_txns` mà KHÔNG nằm trong ba tầng chi phí của báo cáo.

    Vì sao phải đếm, và vì sao phải in ra chứ không im: ba tầng đọc `fleet_trip_costs`,
    `fleet_maintenance` và `fleet_period_costs`. Bảng giao dịch nguồn ngoài KHÔNG nằm trong số đó —
    một dòng sao kê thẻ dầu hay một phiếu đề xuất chi Vietrip chỉ vào được sổ khi có người KHỚP nó
    vào chuyến (thành `fleet_trip_costs`) hoặc NẠP nó qua cửa chi phí kỳ.

    Đo trên hệ thật 07/10/2026: 1.121.825.494 đ nằm ở bảng ấy, cả 36 dòng chưa khớp chuyến, trong khi
    báo cáo kỳ 08/2026 in LỢI NHUẬN 50,3%. Hai con số không nói chuyện với nhau, và màn hình không
    nói ra là chúng không nói chuyện. Người đọc không có cách nào biết — đó mới là chỗ hỏng, chứ
    không phải bản thân việc tiền chưa vào sổ.

    Chia theo NGẢ vì chỉ hai ngả là chi phí đội xe (NGA_CUA_DOI_XE). Khoản của TOUR hay của CHỦ XE
    nằm ở bảng này là đúng chỗ và KHÔNG thiếu gì cả — gộp chung vào một con số "còn thiếu" thì mỗi
    tháng báo động một tỷ hai mà chẳng ai làm gì được, rồi quen dần và thôi nhìn."""
    q = select(ExternalTxn).where(
        ExternalTxn.thoi_diem >= datetime.combine(d1, datetime.min.time()),
        ExternalTxn.thoi_diem <= datetime.combine(d2, datetime.max.time()),
        ExternalTxn.trung == False,                       # noqa: E712 — bản lặp không tính
        ExternalTxn.khong_phai_chi_phi == False,          # noqa: E712 — điều chuyển không phải chi phí
        ExternalTxn.khop != "da_khop")                    # đã khớp thì đã thành dòng chi phí chuyến
    rows = list(db.execute(q).scalars())
    theo_nga: dict[str, dict] = {}
    for t in rows:
        k = t.nga or ""
        o = theo_nga.setdefault(k, {"nga": k, "so_khoan": 0, "so_tien": 0.0})
        o["so_khoan"] += 1
        o["so_tien"] += (t.so_tien or 0)
    cua_doi_xe = sum(o["so_tien"] for k, o in theo_nga.items() if k in NGA_CUA_DOI_XE)
    chua_dinh_tuyen = theo_nga.get("", {}).get("so_tien", 0.0)
    return {
        "so_khoan": len(rows),
        "tong": sum((t.so_tien or 0) for t in rows),
        # Phần CHẮC CHẮN là chi phí đội xe mà vẫn chưa vào ba tầng – con số phải trừ thêm.
        "cua_doi_xe": cua_doi_xe,
        # Phần chưa ai đọc chứng từ. Chưa biết nó của ai, nên KHÔNG trừ và cũng không bỏ qua.
        "chua_dinh_tuyen": chua_dinh_tuyen,
        # Cờ `cua_doi_xe` do MÁY CHỦ trả, không để màn hình tự gõ lại danh sách hai ngả: gõ lại là
        # ngày nào đó thêm một ngả mà hai bên hiểu khác nhau, và không ai biết bên nào đúng.
        "theo_nga": [{**o, "cua_doi_xe": o["nga"] in NGA_CUA_DOI_XE,
                      "ten": (NGA_CHI_PHI.get(o["nga"]) or "Chưa định tuyến — chưa ai đọc chứng từ")}
                     for o in sorted(theo_nga.values(), key=lambda x: -x["so_tien"])],
        "ghi_chu": ("Tiền đã nạp vào bảng giao dịch nguồn ngoài nhưng CHƯA nằm trong ba tầng chi phí "
                    "ở trên. Lợi nhuận phía trên chưa trừ phần 'của đội xe' trong bảng này. Phần "
                    "'chưa định tuyến' thì chưa biết của ai – định tuyến ở tab Đối soát nguồn ngoài "
                    "của màn hình Hồ sơ xe."),
    }


def bao_cao(db: Session, ky: str, phan_bo: str = "khong") -> dict:
    """Báo cáo lãi lỗ đội xe của một kỳ."""
    if phan_bo not in TIEU_THUC: raise ValueError(f"Tiêu thức phân bổ không hợp lệ: {phan_bo}")
    d1, d2 = QT.ky_range(ky)
    so_ngay_ky = (d2 - d1).days + 1
    veh = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    from app.services import hieu_qua_xe as HQ
    _dh = HQ.doi_hinh(db, d1, d2)
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    rows: dict[int, dict] = {}

    # --- Tầng 1: chuyến ---
    #
    # KS-65 · 09/11/2026 — CHỈ CỘNG CHUYẾN ĐÃ QUYẾT TOÁN. Đây là chỗ sửa của KS-62.
    #
    # Trước bản này vòng lặp lấy mọi chuyến `status not in ("nhap","huy")`, nên nó cộng DOANH THU
    # của chuyến chưa quyết toán vào kỳ, trong khi chi phí của chính chuyến ấy CHƯA ĐƯỢC NHẬP —
    # chi phí chỉ vào lúc quyết toán. Doanh thu vào trước, chi phí vào sau, và chỉ cộng nửa đầu
    # thì ra một con số đẹp gấp đôi sự thật.
    #
    # Đo thật trên hệ ngày 09/11/2026, kỳ 2026-11: 17 chuyến, 7 đã quyết toán (64.000.000 đ doanh
    # thu, 26 dòng chi phí) và 10 CHƯA (94.000.000 đ doanh thu, KHÔNG MỘT DÒNG chi phí nào). Màn
    # Chủ tịch vì thế in biên lợi nhuận đội xe tháng 11 là 74,4%, trong khi phần đã quyết toán là
    # 36,9%. Sai theo hướng ĐẸP LÊN, nên không ai nghi — và nó nằm trên màn hình dùng để quyết.
    #
    # Nay cùng một luật với `fleet_ai.hieu_qua_ky` (dòng `if not t.quyet_toan: … continue`), và
    # hai màn hình cùng gọi con số của mình là "lợi nhuận đội xe" thì phải đếm cùng một luật.
    # Phần bị để ra ngoài KHÔNG biến mất: nó thành `chua_quyet_toan` ở `tong` và một danh sách
    # gọi tên từng chuyến bên dưới — "chưa nhập" không phải "bằng 0", mà cũng không phải "cộng
    # vào như thể đã xong".
    chua_qt, dt_chua_qt, ds_chua_qt = 0, 0.0, []
    for c in theo_chuyen(db, ky):
        t = db.get(Trip, c["trip_id"])
        if not t.quyet_toan:
            chua_qt += 1
            dt_chua_qt += (c["doanh_thu"] or 0)
            ds_chua_qt.append({"ma_phieu": c["ma_phieu"], "xe": c["xe"], "ten_tour": c["ten_tour"],
                               "ngay_di": c["ngay_di"], "ngay_ve": c["ngay_ve"],
                               "doanh_thu": c["doanh_thu"],
                               "so_dong_chi_phi": len(c["chi_tiet"] or {})})
            continue
        r = rows.setdefault(t.vehicle_id, _rong(veh.get(t.vehicle_id), t.vehicle_id))
        did = t.driver_id or (veh[t.vehicle_id].driver_id if t.vehicle_id in veh else None)
        if did and not r["tai_xe"]: r["tai_xe"] = emps.get(did, "")
        r["so_chuyen"] += 1
        r["doanh_thu"] += (c["doanh_thu"] or 0); r["chi_phi_chuyen"] += c["chi_phi_chuyen"]
        r["km"] += c["km"] or 0; r["so_lit"] += c["so_lit"] or 0
        r["ngay_khai_thac"] |= {t.ngay_di + timedelta(days=i)
                                for i in range((t.ngay_ve - t.ngay_di).days + 1)}

    # --- Tầng 2: chi phí của xe trong kỳ ---
    # Cùng luật với fleet_ai: phiếu đã được một dòng chi phí chuyến nối tới thì đã tính ở tầng 1.
    da_tinh_o_chuyen = {c.maintenance_id for c in db.execute(
        select(TripCost).where(TripCost.maintenance_id.isnot(None))).scalars()}
    for m in db.execute(select(Maintenance).where(Maintenance.ngay >= d1, Maintenance.ngay <= d2)).scalars():
        if m.id in da_tinh_o_chuyen: continue
        r = rows.setdefault(m.vehicle_id, _rong(veh.get(m.vehicle_id), m.vehicle_id))
        # `Maintenance.ben_chiu` mặc định là "chu_xe". Cộng thẳng 100% là tính cho Vietourist khoản của
        # chủ xe – cùng luật với dòng chi phí chuyến ở trên.
        if m.ben_chiu == "chu_xe":
            r["chi_phi_chu_xe"] = r.get("chi_phi_chu_xe", 0) + (m.so_tien or 0)
            continue
        r["chi_phi_xe"] += (m.so_tien or 0)
        r["chi_tiet_cp_xe"]["bao_duong"] = r["chi_tiet_cp_xe"].get("bao_duong", 0) + (m.so_tien or 0)

    cp_doi, chi_tiet_doi = 0.0, {}
    cp_tai_chinh, chi_tiet_tai_chinh = 0.0, {}
    for k in db.execute(select(FleetPeriodCost).where(FleetPeriodCost.ky == ky)).scalars():
        # Nhóm ngoài giá vốn đi lối riêng TRƯỚC khi xét phạm vi. Xét phạm vi trước thì một dòng lãi vay
        # nhập nhầm phạm vi "xe" (cửa nhập cho phép, vì phạm vi là ô người chọn) sẽ chui vào giá vốn
        # của đúng một chiếc xe và không ai thấy. Quy ước của công ty phải thắng ô người gõ.
        if k.nhom in NGOAI_GIA_VON:
            cp_tai_chinh += (k.so_tien or 0)
            chi_tiet_tai_chinh[k.nhom] = chi_tiet_tai_chinh.get(k.nhom, 0) + (k.so_tien or 0)
        elif k.pham_vi == "xe" and k.vehicle_id:
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
        lai_gop = (r["doanh_thu"] or 0) - r["chi_phi_chuyen"]
        ds.append({**{k: v for k, v in r.items() if k != "ngay_khai_thac"},
                   "ngay_khai_thac": ngay,
                   "cong_suat": round(ngay / so_ngay_ky, 4) if so_ngay_ky else None,
                   "lai_gop_chuyen": lai_gop,
                   "ket_qua_xe": lai_gop - r["chi_phi_xe"],
                   "km_moi_lit": (round(r["km"] / r["so_lit"], 2) if r["km"] and r["so_lit"] else None),
                   "ty_le_lai_gop": (round(lai_gop / (r["doanh_thu"] or 0), 4) if (r["doanh_thu"] or 0) else None)})
    ds.sort(key=lambda x: -x["ket_qua_xe"])

    tong_dt = sum((x["doanh_thu"] or 0) for x in ds)
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
             if pv == "doi" and n not in NGOAI_GIA_VON and n not in chi_tiet_doi]
    # Nhóm ngoài giá vốn chưa nhập được đếm RIÊNG. Gộp vào `thieu` thì màn hình hiện "thiếu lãi vay"
    # ngay dưới khối giá vốn, và người đọc lại tưởng giá vốn còn thiếu khoản ấy.
    thieu_tai_chinh = [NHOM_CHI_PHI_KY[n][0] for n in NGOAI_GIA_VON if n not in chi_tiet_tai_chinh]

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
            # GIÁ VỐN vận tải = ba tầng, KHÔNG có lãi vay. Chủ tịch quyết 11/10/2026.
            "gia_von": tong_cp_chuyen + tong_cp_xe + cp_doi,
            "loi_nhuan": tong_dt - tong_cp_chuyen - tong_cp_xe - cp_doi,
            "ty_le_loi_nhuan": (round((tong_dt - tong_cp_chuyen - tong_cp_xe - cp_doi) / tong_dt, 4)
                                if tong_dt else None),
            # Ngoài giá vốn — in thành dòng riêng bên dưới lợi nhuận, không trộn vào trên.
            "chi_phi_tai_chinh": cp_tai_chinh,
            "ket_qua_sau_tai_chinh": tong_dt - tong_cp_chuyen - tong_cp_xe - cp_doi - cp_tai_chinh,
            # KS-65: phần ĐỂ RA NGOÀI lợi nhuận ở trên. Cùng tên trường với `fleet_ai.hieu_qua_ky`
            # để hai màn hình không đặt hai cái tên cho cùng một con số.
            "so_chuyen_chua_quyet_toan": chua_qt,
            "doanh_thu_chua_quyet_toan": round(dt_chua_qt),
            "so_xe_khai_thac": len([x for x in ds if x["ngay_khai_thac"]]),
            "ngay_khai_thac": tong_ngay,
            # Công suất tính trên số xe CÓ trong đội, không phải số xe có chạy: mẫu số bằng số xe chạy
            # thì một chiếc nằm bãi cả tháng biến mất khỏi phép tính, và công suất luôn đẹp.
            # HQ-1 (13/10/2026) — Ý ĐỊNH TRÊN ĐÚNG, PHÉP TÍNH CŨ SAI. Bản cũ lấy mẫu là
            # `len([v for v in veh.values() if v.active])`, tức số xe hoạt động HÔM NAY, trong khi tử
            # đếm theo KỲ. Đo trên hệ thật kỳ 2026-01: màn hình in "14/12 xe có chạy trong kỳ" — tử
            # LỚN HƠN mẫu, vì ba chiếc chạy suốt tháng 1 rồi bán đi vẫn ở tử mà đã rơi khỏi mẫu.
            # Công suất khi ấy sai theo hướng ĐẸP LÊN, nên không ai nghi.
            #
            # Luật "xe nào có trong đội tại kỳ nào" khai MỘT CHỖ ở `hieu_qua_xe.doi_hinh`, vì khối
            # Chủ tịch cũng cần đúng luật ấy — hai nơi tự tính là dựng chỗ cho hai màn hình nói hai
            # con số công suất khác nhau.
            "so_xe_trong_doi": _dh["so_xe"],
            "cong_suat": (round(tong_ngay / (_dh["so_xe"] * so_ngay_ky), 4)
                          if _dh["du_du_lieu"] and _dh["so_xe"] and so_ngay_ky else None),
            # Trống công suất thì phải nói VÌ SAO và AI phải làm gì, nếu không ô ấy nằm đó mãi.
            "cong_suat_thieu": None if _dh["du_du_lieu"] else _dh,
        },
        "chi_tiet_chi_phi_doi": [{"nhom": k, "ten": NHOM_CHI_PHI_KY.get(k, (k,))[0], "so_tien": v}
                                 for k, v in sorted(chi_tiet_doi.items(), key=lambda kv: -kv[1])],
        "chi_tiet_chi_phi_tai_chinh": [{"nhom": k, "ten": NHOM_CHI_PHI_KY.get(k, (k,))[0], "so_tien": v}
                                       for k, v in sorted(chi_tiet_tai_chinh.items(), key=lambda kv: -kv[1])],
        "nhom_ngoai_gia_von": list(NGOAI_GIA_VON),
        "nhom_tai_chinh_chua_nhap": thieu_tai_chinh,
        # Phần nằm NGOÀI ba tầng – xem ngoai_so(). In ra ngay cạnh lợi nhuận, không để ở cuối.
        "ngoai_so": ngoai_so(db, d1, d2),
        "nhom_chi_phi_doi_chua_nhap": thieu,
        # Gọi tên từng chuyến bị để ra ngoài. Một con số "10 chuyến đang treo" mà không nói chuyến
        # nào thì người đọc phải đi dò, và việc đi dò ấy sẽ không ai làm.
        "chuyen_chua_quyet_toan": ds_chua_qt,
        "ghi_chu": ("Lợi nhuận kỳ CHỈ gồm chuyến đã quyết toán. Chuyến chưa quyết toán để riêng ở "
                    "dòng «doanh thu đang treo»: chi phí của chúng chỉ được nhập lúc quyết toán, "
                    "nên cộng doanh thu vào mà chưa có chi phí là làm biên lợi nhuận đẹp hơn sự "
                    "thật. "
                    "Ba tầng chi phí để riêng: chi phí chuyến, chi phí của xe, chi phí của đội. "
                    "Chi phí đội mặc định KHÔNG chia về từng xe – chia theo tiêu thức nào cũng ra một "
                    "con số khác, mà người đọc lại nhớ nó như kết quả thật của chiếc xe. "
                    "Lãi vay KHÔNG nằm trong giá vốn (Chủ tịch quyết 11/10/2026) – nó là chi phí tài "
                    "chính, hiện thành dòng riêng dưới lợi nhuận và không phân bổ về xe nào."),
    }
