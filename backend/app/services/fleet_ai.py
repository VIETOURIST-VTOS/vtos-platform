"""Đợt 4 đội xe: gợi ý điều xe, chấm hiệu quả xe và tài xế, bản tin sáng.

Đặc tả đặt ra một ranh giới rõ và cả tệp này nằm bên trong nó: *"Không để quyết định cho xe xuất bến phụ
thuộc vào kết luận của mô hình ngôn ngữ."* Vì vậy toàn bộ phần lọc, xếp hạng và chấm điểm ở đây là **mã xác
định** – cùng dữ liệu vào thì cùng kết quả ra, và có mã băm dữ liệu đầu vào để chứng minh điều đó. Mô hình
ngôn ngữ chỉ dùng ở chỗ mơ hồ (đọc ảnh, giải thích bằng lời), không dùng để quyết ai đi xe nào.

Bốn chỗ dễ làm sai mà tệp này cố ý làm khác:

  1. NGÀY KHAI THÁC không phải số chuyến. Hai chuyến trong cùng một ngày là MỘT ngày xe, không phải hai –
     cộng thành hai là thổi phồng mức sử dụng đội xe lên gần gấp đôi ở mùa cao điểm.
  2. MẪU SỐ BẰNG 0 KHÔNG RA 0. Xe chưa chạy km nào thì "đồng/km" là *chưa đủ dữ liệu*, không phải 0 đồng/km –
     và 0 đồng/km sẽ đứng đầu bảng xếp hạng tiết kiệm nhiên liệu.
  3. TÀI XẾ TÍNH THEO NGƯỜI THỰC HIỆN TỪNG CHUYẾN, không theo tài xế hiện tại của xe. Gán toàn bộ lịch sử cho
     người đang lái là chấm điểm người này bằng việc của người khác.
  4. XẾP HẠNG PHẢI CÓ PHIÊN BẢN, KỲ VÀ TẬP SO SÁNH. "Hạng 3" không có nghĩa nếu không nói hạng 3 trong bao
     nhiêu xe, kỳ nào, theo bộ quy tắc nào.
"""
import hashlib, json
from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Alert, Tour
from app.models.hr import Vehicle, Employee, DispatchOrder
from app.models.fleet import Trip, TripCost, Maintenance, AiRunLog, Settlement
from app.services import rules as R
from app.services import fleet as FL
from app.services import fleet_settlement as QT

RULE_VERSION = "2026-09-07.1"      # đổi khi công thức chấm đổi, để so sánh giữa các kỳ biết là cùng thước đo
CHUA_DU = "chua_du_du_lieu"


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def ghi_run(db: Session, agent: str, dau_vao, ket_qua: dict, so_ban_ghi: int, so_co: int, boi: str) -> AiRunLog:
    r = AiRunLog(agent=agent, rule_version=RULE_VERSION, dau_vao_hash=_hash(dau_vao),
                 so_ban_ghi=so_ban_ghi, so_co=so_co, chay_boi=boi,
                 ket_qua=json.dumps(ket_qua, ensure_ascii=False, default=str)[:20000])
    db.add(r); db.flush()
    return r


# ====================== A1 – GỢI Ý ĐIỀU XE ======================
def _tieu_hao_dong_km(db: Session, vid: int, tu: date) -> float | None:
    """Định mức nhiên liệu đồng/km của chính chiếc xe, 6 tháng gần nhất. Chưa đủ dữ liệu thì trả None chứ
    không trả 0 – 0 đồng/km sẽ đứng đầu bảng tiết kiệm và được gợi ý đầu tiên."""
    trips = list(db.execute(select(Trip).where(Trip.vehicle_id == vid, Trip.ngay_di >= tu)).scalars())
    km = sum((t.km_cuoi - t.km_dau) for t in trips
             if t.km_dau is not None and t.km_cuoi is not None and t.km_cuoi >= t.km_dau)
    if km <= 0: return None
    ids = [t.id for t in trips]
    if not ids: return None
    tien = db.execute(select(func.coalesce(func.sum(TripCost.amount), 0))
                      .where(TripCost.trip_id.in_(ids), TripCost.kind == "dau")).scalar() or 0
    if tien <= 0: return None
    return float(tien) / km


def _ngay_cong(db: Session, driver_id: int, tu: date, den: date) -> int:
    """Số NGÀY công của tài xế trong khoảng – hai chuyến cùng ngày là một ngày."""
    ngay = set()
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.driver_id == driver_id,
                                                    DispatchOrder.status.in_(["cho_xac_nhan", "da_xac_nhan", "hoan_thanh"]),
                                                    DispatchOrder.date_to >= tu, DispatchOrder.date_from <= den)).scalars():
        a, b = max(d.date_from, tu), min(d.date_to, den)
        for i in range((b - a).days + 1): ngay.add(a + timedelta(days=i))
    return len(ngay)


def goi_y_dieu_xe(db: Session, d1: date, d2: date, so_khach: int = 0, km_du_kien: int = 0,
                  top: int = 3) -> dict:
    """Xếp hạng các phương án điều xe HỢP LỆ cho một khoảng ngày.

    Lọc cứng trước, xếp hạng sau – đúng thứ tự đặc tả yêu cầu. Xe bị chặn không xuất hiện trong danh sách gợi
    ý dù điểm có cao đến đâu; nếu để chung một thang điểm thì một chiếc xe hết đăng kiểm vẫn có thể đứng trên
    một chiếc xe hợp lệ chỉ vì tốn ít dầu hơn.

    Không xếp hạng chỉ theo một chỉ số: đặc tả nói rõ "không chỉ dựa vào điểm CSKH hoặc tiền dầu/km". Ở đây
    dùng bốn thành phần, và mỗi phương án đi kèm lý do bằng lời để người chốt lệnh đọc được vì sao."""
    chan = bool(R.get_param(db, "xe_chan_khi_thieu_giay"))
    tu_6t = d1 - timedelta(days=182)
    hop_le, bi_loai = [], []
    for v in db.execute(select(Vehicle).where(Vehicle.active == True)).scalars():
        kt = FL.kiem_tra_dieu_xe(db, v, d1, d2, chan_khi_thieu_giay=chan)
        block = [i for i in kt["items"] if i["level"] == FL.BLOCK]
        if block:
            bi_loai.append({"vehicle_id": v.id, "xe": v.plate, "ma_xe": v.code,
                            "ly_do": [i["msg"] for i in block]})
            continue
        if so_khach and v.seats and v.seats < so_khach:
            bi_loai.append({"vehicle_id": v.id, "xe": v.plate, "ma_xe": v.code,
                            "ly_do": [f"Xe {v.seats} chỗ, không đủ cho {so_khach} khách"]})
            continue
        hop_le.append((v, kt))

    if not hop_le:
        return {"phuong_an": [], "bi_loai": bi_loai, "rule_version": RULE_VERSION,
                "ghi_chu": "Không còn xe nào hợp lệ cho khoảng ngày này – xem lý do loại ở danh sách bên dưới"}

    # Thu thập số liệu thô trước, rồi mới chuẩn hóa: chuẩn hóa cần biết dải giá trị của cả tập.
    thoc = []
    for v, kt in hop_le:
        bd = FL.moc_bao_duong(db, v)
        con_km = (bd["km_ky_toi"] - v.odo_km) if (bd["km_ky_toi"] and v.odo_km) else None
        thoc.append({"v": v, "kt": kt, "con_km": con_km, "dong_km": _tieu_hao_dong_km(db, v.id, tu_6t),
                     "ngay_cong": _ngay_cong(db, v.driver_id, d1 - timedelta(days=30), d2) if v.driver_id else 0})
    dks = [x["dong_km"] for x in thoc if x["dong_km"] is not None]
    dk_min, dk_max = (min(dks), max(dks)) if dks else (0, 0)
    ngs = [x["ngay_cong"] for x in thoc]
    ng_min, ng_max = min(ngs), max(ngs)

    pa = []
    for x in thoc:
        v, kt = x["v"], x["kt"]
        ly_do, diem = [], 0.0
        # 1. Km còn lại tới kỳ bảo dưỡng phải PHỦ HẾT hành trình dự kiến.
        if x["con_km"] is None:
            ly_do.append("chưa biết mốc bảo dưỡng nên không khẳng định đủ km cho hành trình")
        elif km_du_kien and x["con_km"] < km_du_kien:
            ly_do.append(f"chỉ còn {x['con_km']:,} km tới kỳ bảo dưỡng, không phủ hết {km_du_kien:,} km dự kiến")
            diem -= 40
        else:
            diem += 25
            ly_do.append(f"còn {x['con_km']:,} km tới kỳ bảo dưỡng" if x["con_km"] else "trong hạn bảo dưỡng")
        # 2. Định mức nhiên liệu thấp. Chưa đủ dữ liệu thì KHÔNG cộng điểm và nói rõ, không coi như tốt nhất.
        if x["dong_km"] is None:
            ly_do.append("chưa đủ dữ liệu định mức nhiên liệu của xe này")
        elif dk_max > dk_min:
            diem += 25 * (dk_max - x["dong_km"]) / (dk_max - dk_min)
            ly_do.append(f"định mức nhiên liệu {x['dong_km']:,.0f} đ/km")
        else:
            diem += 12.5
            ly_do.append(f"định mức nhiên liệu {x['dong_km']:,.0f} đ/km")
        # 3. Cân bằng ngày công giữa các tài xế – người đang ít việc được ưu tiên.
        if ng_max > ng_min:
            diem += 25 * (ng_max - x["ngay_cong"]) / (ng_max - ng_min)
        else:
            diem += 12.5
        ly_do.append(f"tài xế đã có {x['ngay_cong']} ngày công 30 ngày qua")
        # 4. Hồ sơ sạch: không còn cảnh báo mức cần xem lại.
        n_review = sum(1 for i in kt["items"] if i["level"] in (FL.REVIEW, FL.UNKNOWN))
        diem += max(0.0, 25 - 5 * n_review)
        if n_review: ly_do.append(f"còn {n_review} điểm cần xem lại trên hồ sơ xe")
        pa.append({"vehicle_id": v.id, "ma_xe": v.code, "xe": v.plate, "so_cho": v.seats,
                   "tai_xe_id": v.driver_id, "diem": round(diem, 1), "muc_kiem_tra": kt["muc"],
                   "ly_do": ly_do})
    # Sắp xếp ổn định: điểm giảm dần, rồi theo mã xe – để chạy lại cùng dữ liệu ra cùng thứ tự.
    pa.sort(key=lambda r: (-r["diem"], r["ma_xe"] or "", r["vehicle_id"]))
    # `tat_ca` để nơi gọi biết ĐIỂM của một xe cụ thể, không chỉ biết nó có nằm trong top hay không – phân
    # biệt "hệ thống đánh giá thấp hơn" với "chỉ là xếp sau khi điểm bằng nhau".
    return {"phuong_an": pa[:top], "tat_ca": pa, "con_lai": len(pa) - min(top, len(pa)), "bi_loai": bi_loai,
            "rule_version": RULE_VERSION,
            "ghi_chu": "Lọc cứng trước, xếp hạng sau. Bốn thành phần điểm: km còn lại tới kỳ bảo dưỡng, định "
                       "mức nhiên liệu, cân bằng ngày công tài xế, và hồ sơ xe còn bao nhiêu điểm cần xem lại. "
                       "Thiếu dữ liệu KHÔNG được cộng điểm – xe chưa có số liệu không được xếp trên xe đã có."}


# ====================== A9 – HIỆU QUẢ XE VÀ TÀI XẾ ======================
def hieu_qua_ky(db: Session, ky: str) -> dict:
    """Chấm hiệu quả từng xe và từng tài xế trong một kỳ (tháng dương lịch).

    Ba nguyên tắc giữ cho con số có nghĩa:
      - Ngày khai thác đếm theo NGÀY, hai chuyến cùng ngày là một ngày.
      - Mẫu số bằng 0 hoặc thiếu thì trả "chưa đủ dữ liệu", không trả 0.
      - Tài xế tính theo người THỰC HIỆN từng chuyến, không theo tài xế hiện tại của xe."""
    d1, d2 = QT.ky_range(ky)
    trips = list(db.execute(select(Trip).where(Trip.ngay_di >= d1, Trip.ngay_di <= d2)).scalars())
    ids = [t.id for t in trips]
    chi = {}
    if ids:
        for c in db.execute(select(TripCost).where(TripCost.trip_id.in_(ids))).scalars():
            chi.setdefault(c.trip_id, []).append(c)
    veh = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}

    def _rong(d: dict) -> dict:
        return {**d, "doanh_thu": 0.0, "chi_phi": 0.0, "ngay_khai_thac": set(), "km": 0, "lit": 0.0,
                "so_chuyen": 0, "tien_dau": 0.0, "sua_chua": 0.0}

    xe_rows, tx_rows = {}, {}
    for t in trips:
        x = xe_rows.setdefault(t.vehicle_id, _rong({"vehicle_id": t.vehicle_id,
                                                    "xe": veh[t.vehicle_id].plate if t.vehicle_id in veh else "",
                                                    "ma_xe": veh[t.vehicle_id].code if t.vehicle_id in veh else ""}))
        # Tài xế của CHÍNH chuyến đó, không phải tài xế hiện tại của xe.
        did = t.driver_id or (veh[t.vehicle_id].driver_id if t.vehicle_id in veh else None)
        tx = tx_rows.setdefault(did, _rong({"driver_id": did, "tai_xe": emps.get(did, "(chưa gán)")})) if did else None
        km = (t.km_cuoi - t.km_dau) if (t.km_dau is not None and t.km_cuoi is not None and t.km_cuoi >= t.km_dau) else 0
        ngay = {t.ngay_di + timedelta(days=i) for i in range((t.ngay_ve - t.ngay_di).days + 1)}
        for r in (x, tx):
            if r is None: continue
            r["so_chuyen"] += 1; r["doanh_thu"] += t.doanh_thu; r["km"] += km
            r["ngay_khai_thac"] |= ngay
            for c in chi.get(t.id, []):
                r["chi_phi"] += c.amount
                if c.kind == "dau": r["tien_dau"] += c.amount; r["lit"] += c.lit
                if c.kind == "sua_chua": r["sua_chua"] += c.amount
    # Bảo dưỡng ngoài chuyến vẫn là chi phí của xe trong kỳ.
    for m in db.execute(select(Maintenance).where(Maintenance.ngay >= d1, Maintenance.ngay <= d2)).scalars():
        x = xe_rows.setdefault(m.vehicle_id, _rong({"vehicle_id": m.vehicle_id,
                                                    "xe": veh[m.vehicle_id].plate if m.vehicle_id in veh else "",
                                                    "ma_xe": veh[m.vehicle_id].code if m.vehicle_id in veh else ""}))
        x["chi_phi"] += m.so_tien; x["sua_chua"] += m.so_tien

    def _hoan(r: dict) -> dict:
        ngay = len(r.pop("ngay_khai_thac"))
        loi = r["doanh_thu"] - r["chi_phi"]
        out = {**r, "ngay_khai_thac": ngay, "loi_nhuan": round(loi),
               "doanh_thu": round(r["doanh_thu"]), "chi_phi": round(r["chi_phi"]),
               "tien_dau": round(r["tien_dau"]), "sua_chua": round(r["sua_chua"])}
        # Mẫu số 0 hoặc thiếu → "chưa đủ dữ liệu", không phải 0.
        out["loi_nhuan_moi_ngay"] = round(loi / ngay) if ngay else CHUA_DU
        out["dau_dong_tren_km"] = round(r["tien_dau"] / r["km"]) if r["km"] and r["tien_dau"] else CHUA_DU
        out["km_moi_lit"] = round(r["km"] / r["lit"], 2) if r["lit"] and r["km"] else CHUA_DU
        out["sua_chua_tren_km"] = round(r["sua_chua"] / r["km"]) if r["km"] and r["sua_chua"] else CHUA_DU
        out["bien_loi_nhuan"] = round(loi / r["doanh_thu"], 4) if r["doanh_thu"] else CHUA_DU
        return out

    xes = sorted((_hoan(r) for r in xe_rows.values()), key=lambda r: -r["loi_nhuan"])
    txs = sorted((_hoan(r) for r in tx_rows.values()), key=lambda r: -r["loi_nhuan"])
    for i, r in enumerate(xes, 1): r["hang"] = i
    for i, r in enumerate(txs, 1): r["hang"] = i
    return {"ky": ky, "rule_version": RULE_VERSION, "tap_so_sanh_xe": len(xes), "tap_so_sanh_tai_xe": len(txs),
            "xe": xes, "tai_xe": txs,
            "ghi_chu": f"Hạng tính trong tập {len(xes)} xe có phát sinh chuyến trong kỳ {ky}, theo bộ quy tắc "
                       f"{RULE_VERSION}. Hạng của kỳ này không so được với hạng của một tập xe khác hay một bộ "
                       "quy tắc khác. Ngày khai thác đếm theo NGÀY: hai chuyến cùng ngày là một ngày. Ô ghi "
                       "\"chưa đủ dữ liệu\" là chưa tính được, không phải bằng 0.",
            "gioi_han": "Đây là phân tích số liệu vận hành. Không dùng làm căn cứ duy nhất để giữ hay điều "
                        "chuyển nhân sự, và không đưa dữ liệu cá nhân ngoài công việc vào chấm điểm."}


def khuyen_nghi_ban_xe(db: Session, vehicle_id: int, gia_chao: float, dinh_gia_noi_bo: float,
                       so_thang: int = 12) -> dict:
    """So sánh giá chào bán với định giá nội bộ và lợi nhuận các kỳ gần nhất.

    Đặc tả: giá chào thấp hơn định giá nội bộ quá ngưỡng thì bắt buộc cờ vàng và nêu rõ SỐ NĂM lợi nhuận
    tương đương – để người quyết thấy mình đang đánh đổi bao nhiêu năm khai thác lấy một khoản tiền ngay."""
    nguong = R.get_param(db, "xe_chenh_gia_ban_vang")
    hom_nay = date.today()
    loi = 0.0; ky_co_du_lieu = 0
    for i in range(so_thang):
        m = hom_nay.month - i; y = hom_nay.year
        while m <= 0: m += 12; y -= 1
        hq = hieu_qua_ky(db, f"{y}-{m:02d}")
        r = next((x for x in hq["xe"] if x["vehicle_id"] == vehicle_id), None)
        if r: loi += r["loi_nhuan"]; ky_co_du_lieu += 1
    out = {"vehicle_id": vehicle_id, "gia_chao": gia_chao, "dinh_gia_noi_bo": dinh_gia_noi_bo,
           "loi_nhuan_gan_nhat": round(loi), "so_ky_co_du_lieu": ky_co_du_lieu, "co": "xanh", "ly_do": []}
    if dinh_gia_noi_bo > 0:
        chenh = (dinh_gia_noi_bo - gia_chao) / dinh_gia_noi_bo
        out["chenh_so_dinh_gia"] = round(chenh, 4)
        if chenh > nguong:
            out["co"] = "vang"
            out["ly_do"].append(f"Giá chào thấp hơn định giá nội bộ {chenh*100:.0f}% (ngưỡng {nguong*100:.0f}%) "
                                "– bắt buộc giải trình")
    else:
        out["co"] = "vang"; out["ly_do"].append("Chưa có định giá nội bộ nên chưa so sánh được giá chào")
    if ky_co_du_lieu == 0:
        out["so_nam_loi_nhuan_tuong_duong"] = CHUA_DU
        out["ly_do"].append("Chưa có kỳ nào có số liệu khai thác – chưa quy ra được số năm lợi nhuận tương đương")
        out["co"] = "vang"
    elif loi > 0:
        binh_quan_nam = loi / ky_co_du_lieu * 12
        out["so_nam_loi_nhuan_tuong_duong"] = round(gia_chao / binh_quan_nam, 1)
        out["ly_do"].append(f"Giá chào tương đương {out['so_nam_loi_nhuan_tuong_duong']} năm lợi nhuận khai "
                            f"thác (bình quân {round(binh_quan_nam):,} đ/năm theo {ky_co_du_lieu} kỳ có số liệu)")
    else:
        out["so_nam_loi_nhuan_tuong_duong"] = CHUA_DU
        out["ly_do"].append(f"Lợi nhuận {ky_co_du_lieu} kỳ gần nhất không dương – không quy ra được số năm")
    return out


# ====================== A0 – BẢN TIN SÁNG ======================
def ban_tin_sang(db: Session, hom_nay: date | None = None) -> dict:
    """Bản tin một màn hình cho lãnh đạo và người phụ trách đội xe. Cảnh báo đỏ luôn đứng đầu."""
    t = hom_nay or date.today()
    chay = []
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.date_from <= t, DispatchOrder.date_to >= t,
                                                     DispatchOrder.status.in_(["cho_xac_nhan", "da_xac_nhan"]))).scalars():
        v = db.get(Vehicle, d.vehicle_id); e = db.get(Employee, d.driver_id)
        tour = db.get(Tour, d.tour_id)
        chay.append({"xe": v.plate if v else "", "ma_xe": v.code if v else "", "tai_xe": e.full_name if e else "",
                     "tour": tour.code if tour else "", "den_ngay": d.date_to,
                     "trang_thai": d.status})
    ban = {x["xe"] for x in chay}
    ranh = []
    for v in db.execute(select(Vehicle).where(Vehicle.active == True)).scalars():
        if v.plate in ban: continue
        s = FL.san_sang(db, v, bool(R.get_param(db, "xe_chan_khi_thieu_giay")))
        ranh.append({"xe": v.plate, "ma_xe": v.code, "muc": s["muc"], "ly_do": s["ly_do"][:1]})

    do = [{"id": a.id, "kind": a.kind, "ref": a.ref, "message": a.message, "ngay": a.created_at}
          for a in db.execute(select(Alert).where(Alert.resolved == False, Alert.level == "red")
                              .order_by(Alert.created_at)).scalars()][:20]
    vang = db.execute(select(func.count()).select_from(Alert)
                      .where(Alert.resolved == False, Alert.level == "warn")).scalar() or 0
    cho_duyet = db.execute(select(func.count()).select_from(Settlement)
                           .where(Settlement.status != "dong_ky")).scalar() or 0
    return {"ngay": t, "rule_version": RULE_VERSION,
            "canh_bao_do": do, "so_canh_bao_vang": vang,
            "xe_chay_hom_nay": chay, "xe_ranh": ranh,
            "ky_quyet_toan_chua_dong": cho_duyet,
            "ghi_chu": "Cảnh báo đỏ đứng đầu. Ô \"xe rảnh\" chỉ là xe không có lệnh hôm nay – xe ở mức chưa "
                       "đủ dữ liệu hoặc bị chặn KHÔNG phải là xe sẵn sàng chạy."}


def nang_muc_canh_bao(db: Session, hom_nay: date | None = None) -> dict:
    """Nâng mức cảnh báo tồn lâu và gắn người chịu trách nhiệm.

    Đặc tả có hai câu tưởng như trái nhau: "cảnh báo lặp lại quá 3 ngày tự động nâng mức" và "không nâng mọi
    cảnh báo chỉ vì đã tồn tại ba ngày". Cách dung hòa: chỉ nâng cảnh báo có NGƯỜI NHẬN cụ thể và thuộc loại
    người ta làm được gì với nó. Nâng tất cả thì sau một tuần cả bảng đỏ rực và không ai đọc nữa – lúc đó
    cảnh báo mất tác dụng đúng vào ngày cần nó nhất."""
    t = hom_nay or date.today()
    han = datetime.combine(t - timedelta(days=3), datetime.min.time())
    nang, bo_qua = [], []
    for a in db.execute(select(Alert).where(Alert.resolved == False, Alert.level == "warn",
                                            Alert.created_at <= han)).scalars():
        if not (a.to_roles or "").strip():
            bo_qua.append({"id": a.id, "kind": a.kind, "ly_do": "chưa gắn người nhận nên nâng mức không giúp gì"})
            continue
        a.level = "red"
        a.message = f"[Tồn quá 3 ngày] {a.message}"
        nang.append({"id": a.id, "kind": a.kind, "ref": a.ref, "nguoi_nhan": a.to_roles})
    return {"da_nang": nang, "bo_qua": bo_qua,
            "ghi_chu": "Chỉ nâng cảnh báo đã có người nhận. Nâng tất cả thì sau một tuần cả bảng đỏ rực và "
                       "không ai đọc nữa."}
