"""Hiệu quả đội xe — bốn chỉ số của khối 04b trên màn hình Chủ tịch, và đội hình xe theo kỳ.

Vì sao một tệp riêng chứ không viết thêm vào `fleet_lai_lo`: hai chỗ cùng cần luật "xe nào có trong
đội tại kỳ nào" — màn hình lãi lỗ đội xe và khối Chủ tịch. Viết hai lần là dựng chỗ để hai màn hình
nói hai con số công suất khác nhau, và lúc ấy không ai biết màn nào đúng.

═══════════════════════════════════════════════════════════════════════════════════════════════
HAI LUẬT TRONG TỆP NÀY, VÀ VÌ SAO CHÚNG NHƯ THẾ
═══════════════════════════════════════════════════════════════════════════════════════════════

**1 · ĐỘI HÌNH TẠI KỲ — mẫu số của công suất.**

Đo trên hệ thật 13/10/2026, kỳ 2026-01: màn hình in "14/12 xe có chạy trong kỳ". Tử số lớn hơn mẫu
số. Tử là số xe CÓ NGÀY KHAI THÁC trong kỳ ấy; mẫu là `len([v for v in veh if v.active])`, tức số xe
còn hoạt động HÔM NAY. Ba chiếc chạy suốt tháng 1 rồi bán đi vẫn nằm ở tử nhưng đã rơi khỏi mẫu.

Hệ quả: công suất 60,8% là một phép chia cho mẫu nhỏ hơn sự thật — nó sai theo hướng ĐẸP LÊN, nên
không ai nghi. Đó là loại sai tệ nhất.

Ý định trong chú thích cũ của `fleet_lai_lo` ĐÚNG ("mẫu là xe CÓ trong đội, không phải xe có chạy").
Cái sai là lấy TRẠNG THÁI HÔM NAY áp cho quá khứ — đúng cái bẫy `xe_theo_bien()` đã xử đúng từ lâu.

Chữa bằng hai cột ngày (`vehicles.ngay_vao_doi` / `ngay_roi_doi`, bản vá `hq1c6f2a8e4b37`), khai qua
cửa `ho_so_xe`. Và chừng nào Đội xe chưa khai đủ thì **trả về None kèm tên xe còn thiếu**, không trả
một con số. Chủ tịch chọn thế 13/10/2026: "ẩn còn hơn hiện số sai".

Chỗ rất dễ làm sai, viết ra để sau không ai sửa ngược: KHÔNG được lấy "rỗng" làm "chưa từng rời đội"
rồi đếm tất. Rỗng ở `ngay_vao_doi` là CHƯA AI KHAI. Đếm tất thì hai chiếc dữ liệu mẫu (51B-123.45,
51B-678.90) chui vào mẫu số và công suất lại sai — lần này theo hướng XẤU ĐI, cũng vẫn là sai.

**2 · KM CHẠY RỖNG — khoảng hở giữa hai chuyến liền nhau.**

Chủ tịch chọn 13/10/2026. Lấy km đầu của chuyến sau trừ km cuối của chuyến trước, trên cùng một xe,
xếp theo ngày đi. Đó là quãng xe lăn bánh mà không mang doanh thu: đi lấy xe, đi trả xe, về bãi.

Tính được NGAY vì cả 676 chuyến nạp 13/10 đều có km đầu và km cuối.

Khoảng hở ÂM thì **báo ra chứ không cộng, và cũng không lấy trị tuyệt đối**. Âm nghĩa là đồng hồ của
hai dòng ấy mâu thuẫn (sổ ghi ngược, hoặc một chuyến bị bỏ sót ở giữa) — cộng một con số mâu thuẫn
vào tổng là biến một lỗi nhập liệu thành một chỉ số điều hành.

Khoảng hở được tính vào kỳ của CHUYẾN SAU: quãng chạy rỗng xảy ra ngay trước khi chuyến ấy khởi
hành. Nhờ vậy quãng rỗng ngay trước chuyến đầu tiên của kỳ cũng được đếm, thay vì rơi mất.
"""
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.fleet import Trip
from app.models.hr import Vehicle
from app.services import fleet_settlement as QT

# Vòng đời nói rằng chiếc xe ĐÃ RỜI đội. Những chiếc này mà thiếu `ngay_roi_doi` thì hồ sơ chưa đủ:
# không biết nó rời lúc nào thì không biết kỳ nào còn phải tính nó vào mẫu số.
DA_ROI = ("da_ban", "ngung")


def trong_doi(v: Vehicle, d1: date, d2: date) -> bool:
    """Chiếc xe này có mặt trong đội ở bất kỳ ngày nào của [d1, d2] không?

    Giao nhau giữa hai khoảng, không phải "có mặt cả kỳ": một chiếc bán giữa tháng vẫn là xe của đội
    trong nửa đầu tháng ấy, và nửa tháng đó có doanh thu, có chi phí, có ngày khai thác.
    """
    if v.ngay_vao_doi is not None and v.ngay_vao_doi > d2:
        return False
    if v.ngay_roi_doi is not None and v.ngay_roi_doi < d1:
        return False
    return True


def doi_hinh(db: Session, d1: date, d2: date) -> dict:
    """Đội hình xe tại kỳ [d1, d2].

    Trả `so_xe=None` khi hồ sơ chưa đủ để trả lời — kèm `thieu` nói RÕ xe nào thiếu trường nào, để
    màn hình chỉ được việc cho Đội xe thay vì chỉ hiện một ô trống.
    """
    xe = list(db.execute(select(Vehicle)).scalars())
    thieu = []
    for v in xe:
        if v.ngay_vao_doi is None:
            thieu.append({"xe": v.plate, "thieu": "ngày vào đội"})
        elif v.lifecycle in DA_ROI and v.ngay_roi_doi is None:
            thieu.append({"xe": v.plate, "thieu": "ngày rời đội (vòng đời ghi đã rời)"})
    if thieu:
        return {"so_xe": None, "du_du_lieu": False, "thieu": thieu,
                "vi_sao": f"{len(thieu)} xe chưa khai ngày vào/rời đội — chưa biết đội hình kỳ này "
                          f"gồm những chiếc nào, nên không chia được",
                "cua_nhap": "/nap-du-lieu?loai=ho_so_xe", "bo_phan": "Đội xe"}
    return {"so_xe": len([v for v in xe if trong_doi(v, d1, d2)]),
            "du_du_lieu": True, "thieu": [], "vi_sao": "", "cua_nhap": "", "bo_phan": ""}


def km_chay_rong(db: Session, d1: date, d2: date) -> dict:
    """Km xe lăn bánh ngoài chuyến, trong kỳ [d1, d2].

    Đọc TOÀN BỘ chuyến của mỗi xe chứ không chỉ chuyến trong kỳ: khoảng hở trước chuyến đầu tiên của
    kỳ chỉ đo được khi còn thấy chuyến cuối cùng của kỳ trước.
    """
    ch: dict[int, list[Trip]] = {}
    for t in db.execute(select(Trip)).scalars():
        if t.vehicle_id is None or t.km_dau is None or t.km_cuoi is None:
            continue
        ch.setdefault(t.vehicle_id, []).append(t)

    km, so_khoang, lech = 0, 0, []
    for vid, ts in ch.items():
        ts.sort(key=lambda t: (t.ngay_di, t.id))
        for truoc, sau in zip(ts, ts[1:]):
            if not (d1 <= sau.ngay_di <= d2):
                continue
            ho = sau.km_dau - truoc.km_cuoi
            if ho < 0:
                lech.append({"ma_phieu": sau.ma_phieu, "truoc": truoc.ma_phieu, "ho": ho})
            else:
                km += ho
                so_khoang += 1
    return {"km": km, "so_khoang": so_khoang, "so_lech": len(lech), "lech": lech[:20]}


def chi_so(db: Session, ky: str) -> dict:
    """Bốn chỉ số của khối 04b cho một kỳ tháng, đúng khuôn `HieuQuaXe` của KhoiV14.tsx.

    Trường nào chưa tính được thì BỎ TRỐNG (None) — màn hình tự hiện "Chưa kết nối". Tuyệt đối không
    điền số ước lượng: một con số trên bảng Chủ tịch là một con số ông ấy dùng để quyết.
    """
    from app.models.accounting import PeriodLock
    from app.services import fleet_lai_lo as LL

    d1, d2 = QT.ky_range(ky)
    so_ngay_ky = (d2 - d1).days + 1
    bc = LL.bao_cao(db, ky)
    tong = bc["tong"]

    ngay = tong["ngay_khai_thac"]
    dh = doi_hinh(db, d1, d2)
    rong = km_chay_rong(db, d1, d2)

    mau = (dh["so_xe"] or 0) * so_ngay_ky
    cong_suat = round(ngay * 100 / mau, 1) if dh["du_du_lieu"] and mau else None

    # Chi phí / km: GIÁ VỐN vận tải chia cho TẤT CẢ km xe lăn bánh — km chuyến cộng km chạy rỗng.
    # Lãi vay không nằm trong tử số: Chủ tịch quyết 11/10/2026 lãi vay không vào giá vốn, và
    # `tong["gia_von"]` đã tôn trọng điều đó. Mẫu số cộng cả km rỗng vì xe đốt dầu trên quãng rỗng y
    # như trên quãng có khách; bỏ km rỗng ra khỏi mẫu thì chi phí mỗi km đọc ra cao hơn sự thật.
    km_chuyen = sum((x["km"] or 0) for x in bc["xe"])
    km_tong = km_chuyen + rong["km"]
    chi_phi_moi_km = round(tong["gia_von"] / km_tong) if km_tong else None

    return {
        "ngay_xe_hoat_dong": ngay or None,
        "cong_suat_khai_thac": cong_suat,
        "km_chay_rong": rong["km"] or None,
        "chi_phi_moi_km": chi_phi_moi_km,
        "da_chot": db.get(PeriodLock, ky) is not None,
        # HQ-1b (13/10/2026) — Ô NÀY NẰM TRONG hợp đồng `HieuQuaXe`, không còn là ghi chú nội bộ.
        #
        # Vòng HQ-1 để nó dưới tên `_cong_suat_thieu` với lý lẽ "màn hình bỏ qua". Đo trên hệ thật
        # ngay sau khi lên: khối Chủ tịch in ba ô có số và MỘT DẤU GẠCH NGANG ở ô công suất, không
        # một chữ nào nói vì sao. Người đọc không có cách nào biết nó đang chờ Đội xe khai 16 chiếc.
        #
        # Tính sẵn một câu trả lời rồi giấu nó sau dấu gạch dưới thì cũng bằng không tính.
        "cong_suat_thieu": None if dh["du_du_lieu"] else {
            "bo_phan": dh["bo_phan"], "cua_nhap": dh["cua_nhap"], "thieu": dh["thieu"]},
        "_gia_von": tong["gia_von"],
        "_km_chuyen": km_chuyen,
        "_km_rong_lech": rong["so_lech"],
        "_so_xe_trong_doi": dh["so_xe"],
        "_so_ngay_ky": so_ngay_ky,
    }


def theo_ky(db: Session, moc: date) -> dict:
    """Ba kỳ của nút chọn trên khối: tháng / quý / năm, tính đến `moc`.

    Quý và năm cộng từ các kỳ tháng, nhưng KHÔNG cộng những thứ không cộng được:
      · ngày hoạt động, km rỗng, km chuyến, giá vốn  → cộng được, cộng.
      · công suất → tính LẠI trên tổng (tổng ngày / tổng chỗ-ngày), không lấy trung bình của các
        tháng: trung bình của ba tỷ lệ có mẫu khác nhau là một con số không nghĩa gì.
      · chi phí / km → cũng tính lại trên tổng, cùng lý do.

    Kỳ nào trong quý/năm mà đội hình chưa đủ dữ liệu thì cả quý/năm ấy bỏ trống công suất — thiếu
    một tháng là mẫu số của cả quý đã thiếu.
    """
    def _thang(n: int) -> list[str]:
        ks, y, m = [], moc.year, moc.month
        for _ in range(n):
            ks.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        return list(reversed(ks))

    quy_dau = ((moc.month - 1) // 3) * 3 + 1
    nhom = {"thang": [f"{moc.year:04d}-{moc.month:02d}"],
            "quy": [f"{moc.year:04d}-{m:02d}" for m in range(quy_dau, moc.month + 1)],
            "nam": [f"{moc.year:04d}-{m:02d}" for m in range(1, moc.month + 1)]}
    nhan = {"thang": f"Tháng {moc.month:02d}/{moc.year}",
            "quy": f"Quý {(moc.month - 1) // 3 + 1}/{moc.year}"
                   + (f" (đến hết tháng {moc.month:02d})" if moc.month % 3 else ""),
            "nam": f"Năm {moc.year} (T01–T{moc.month:02d})"}

    # HQ-1c (13/10/2026) — KỲ MỚI NHẤT CÒN CÓ CHUYẾN.
    #
    # Vì sao cần: khối mở sẵn ở kỳ THÁNG, mà tháng đang chạy gần như luôn trống — sổ quyết toán xe
    # chỉ chốt sau khi hết tháng, nên suốt gần cả tháng khối in bốn dấu gạch. Đo trên hệ thật
    # 13/10/2026: tháng và quý đều rỗng, chỉ kỳ NĂM có số (2.127 ngày · 56.927 km · 10.064 đ/km) —
    # và không có gì trên màn hình chỉ cho người đọc biết điều đó. Chủ tịch mở ra, thấy trống, kết
    # luận "đội xe chưa lên màn hình". Con số có thật mà vẫn bằng không có.
    ngay_cuoi = db.execute(select(func.max(Trip.ngay_di))).scalar()
    ky_cuoi = f"{ngay_cuoi:%Y-%m}" if ngay_cuoi else None

    out = {}
    for ten, kys in nhom.items():
        ds = [chi_so(db, k) for k in kys]
        ngay = sum((x["ngay_xe_hoat_dong"] or 0) for x in ds)
        rong = sum((x["km_chay_rong"] or 0) for x in ds)
        km = sum(x["_km_chuyen"] for x in ds) + rong
        du = all(x["_so_xe_trong_doi"] is not None for x in ds)
        cho_ngay = sum((x["_so_xe_trong_doi"] or 0) * x["_so_ngay_ky"] for x in ds)
        # Cộng GIÁ VỐN gốc, không nhân ngược từ `chi_phi_moi_km`: con số ấy đã làm tròn về đồng, và
        # nhân ngược một số đã tròn với quãng đường hàng chục nghìn km thì sai số đi theo cấp triệu.
        gia_von = sum(x["_gia_von"] for x in ds)
        # Lý do thiếu của quý/năm LẤY NGUYÊN của một kỳ con, không gộp. Viết ra vì "gộp" nghe cẩn
        # thận hơn và em đã viết phần gộp ấy trước khi đo:
        #
        #   `doi_hinh` liệt kê xe thiếu ngày vào đội theo DANH MỤC XE, không theo kỳ — một chiếc
        #   chưa ai khai thì thiếu ở mọi kỳ như nhau. Nên danh sách của tháng 1 và tháng 2 LUÔN
        #   bằng nhau, và phần gộp không bao giờ gộp được gì.
        #
        # Phép thử canh phần gộp ấy VẪN XANH khi em cố tình phá nó — vì bộ dữ liệu không thể làm
        # hai tháng khác nhau. Đó là phép thử trang trí, và mã nó canh là mã trang trí. Bỏ cả hai,
        # giữ lại một phép thử canh đúng cái bất biến thật: lý do của quý trùng lý do của tháng.
        goc = next((x["cong_suat_thieu"] for x in ds if x["cong_suat_thieu"]), None)
        out[ten] = {
            "nhan": nhan[ten],
            "ngay_xe_hoat_dong": ngay or None,
            "cong_suat_khai_thac": round(ngay * 100 / cho_ngay, 1) if du and cho_ngay else None,
            "km_chay_rong": rong or None,
            "chi_phi_moi_km": round(gia_von / km) if km else None,
            "da_chot": all(x["da_chot"] for x in ds),
            "cong_suat_thieu": None if du else goc,
            # Kỳ rỗng thì nói VÌ SAO rỗng, ngay tại kỳ ấy. "Chưa có số" một mình đọc ra như hỏng;
            # "chưa nạp chuyến nào, số mới nhất là tháng 9" đọc ra là một việc có người làm được.
            "trong_vi_sao": (None if ngay else
                             (f"{nhan[ten]} chưa nạp chuyến nào"
                              + (f" — số mới nhất là tháng {ky_cuoi[5:]}/{ky_cuoi[:4]}"
                                 if ky_cuoi and ky_cuoi not in kys else "") + "."
                              if ky_cuoi else f"{nhan[ten]} chưa nạp chuyến nào.")),
        }

    # Kỳ mở sẵn: kỳ HẸP NHẤT còn có số. Tháng trước, rồi quý, rồi năm — mở ra là thấy số, và là
    # con số gần hiện tại nhất có thể. Không kỳ nào có số thì giữ "thang" như cũ: lúc ấy ba nút đều
    # trống như nhau, và `trong_vi_sao` của kỳ tháng nói đúng việc phải làm.
    out["mac_dinh"] = next((t for t in ("thang", "quy", "nam")
                            if out[t]["ngay_xe_hoat_dong"]), "thang")
    out["ky_moi_nhat_co_chuyen"] = ky_cuoi
    return out
