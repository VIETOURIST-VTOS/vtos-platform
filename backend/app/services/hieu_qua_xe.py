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

from app.models.fleet import Trip, FuelNorm
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


def _hom_nay() -> date:
    """Hôm nay.

    Tách thành một hàm chứ không gọi thẳng `date.today()` ở chỗ dùng, vì hai lẽ: phép thử ghim được
    ngày (mẫu số của công suất phụ thuộc vào hôm nay, nên không ghim được thì phép thử đổi kết quả
    theo lịch), và chỗ gọi đọc ra Ý — "tới hôm nay" — chứ không ra một lời gọi thư viện.
    """
    return date.today()


def ngay_xe_trong_doi(db: Session, d1: date, d2: date) -> int:
    """Tổng số NGÀY-XE của đội trong [d1, d2] — mẫu số của công suất khai thác.

    ĐẾM TỪNG XE MỘT, không lấy `số xe × số ngày kỳ`. Phép nhân phẳng ấy cho một chiếc mua ngày 20
    cùng số ngày với một chiếc chạy suốt tháng, nên mẫu phồng lên và công suất đọc ra THẤP hơn sự
    thật. Chiếc bán giữa tháng cũng vậy, theo chiều ngược lại.

    `ngay_vao_doi` rỗng thì tính cả kỳ: `doi_hinh` đã chặn trước — hồ sơ còn thiếu thì nó trả
    `du_du_lieu=False` và `chi_so` không gọi tới đây. Guard ở đây chỉ để hàm này tự đứng được.
    """
    if d2 < d1:
        return 0                                   # kỳ chưa tới một ngày nào: không có mẫu số
    tong = 0
    for v in db.execute(select(Vehicle)).scalars():
        vao = max(d1, v.ngay_vao_doi) if v.ngay_vao_doi else d1
        roi = min(d2, v.ngay_roi_doi) if v.ngay_roi_doi else d2
        if roi >= vao:
            tong += (roi - vao).days + 1
    return tong


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

    # MỤC 3 (21/10/2026, anh Tuấn chốt) — MẪU SỐ DỪNG Ở HÔM NAY, VÀ ĐẾM TỪNG XE MỘT.
    #
    # Trước vòng này mẫu là `số xe × số ngày của cả kỳ`. Đo trên hệ thật kỳ 2026-10 sáng 21/10:
    # 115 ngày khai thác chia cho 11 xe × 31 ngày = 33,7%. Nhưng 11 ngày cuối tháng CHƯA TỚI — đội
    # xe bị chia cho những ngày chưa ai có cơ hội chạy. Con số ấy sai theo hướng XẤU ĐI, và nó là
    # con số Chủ tịch đọc để kết luận đội xe đang nhàn.
    #
    # Nên mẫu dừng ở `min(hết kỳ, hôm nay)`: kỳ 2026-10 đo trên 1→20/10, ra 115 / (11 × 20) = 52,3%.
    # Kỳ ĐÃ QUA không đổi một chữ — `min` không cắt gì khi cả kỳ nằm sau lưng.
    # Kỳ CHƯA TỚI (T11, T12 trên hình diễn biến) có mẫu bằng 0, nên trả None thay vì 0,0% — một
    # tháng chưa tới mà in "0,0%" đọc ra như một tháng đội xe nằm bãi.
    #
    # Và đếm NGÀY-XE từng chiếc (`ngay_xe_trong_doi`) chứ không nhân phẳng: xem hàm ấy.
    d2_mau = min(d2, _hom_nay())
    mau = ngay_xe_trong_doi(db, d1, d2_mau) if dh["du_du_lieu"] else 0
    cong_suat = round(ngay * 100 / mau, 1) if dh["du_du_lieu"] and mau else None

    # Chi phí / km: GIÁ VỐN vận tải chia cho TẤT CẢ km xe lăn bánh — km chuyến cộng km chạy rỗng.
    # Lãi vay không nằm trong tử số: Chủ tịch quyết 11/10/2026 lãi vay không vào giá vốn, và
    # `tong["gia_von"]` đã tôn trọng điều đó. Mẫu số cộng cả km rỗng vì xe đốt dầu trên quãng rỗng y
    # như trên quãng có khách; bỏ km rỗng ra khỏi mẫu thì chi phí mỗi km đọc ra cao hơn sự thật.
    km_chuyen = sum((x["km"] or 0) for x in bc["xe"])
    km_tong = km_chuyen + rong["km"]
    chi_phi_moi_km = round(tong["gia_von"] / km_tong) if km_tong else None

    # HQ-2c — TIÊU HAO DẦU. Mẫu số là KM CHUYẾN, không cộng km rỗng: số lít đo được là lít đã mua
    # có hoá đơn, gắn vào chuyến; quãng rỗng không có dòng chi phí dầu nào của riêng nó. Cộng km
    # rỗng vào mẫu thì tiêu hao đọc ra THẤP hơn sự thật — sai theo hướng đẹp lên, lại đúng loại sai
    # mà cả tệp này sinh ra để chặn.
    so_lit = sum((x["so_lit"] or 0) for x in bc["xe"])
    tieu_hao = round(so_lit * 100 / km_chuyen, 1) if (so_lit and km_chuyen) else None
    nguong = {n.seats: n.l_100km for n in db.execute(select(FuelNorm)).scalars()}
    xe_ds = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    vuot = []
    for x in bc["xe"]:
        v = xe_ds.get(x.get("vehicle_id"))
        ng = nguong.get(v.seats) if v else None
        th = (round((x["so_lit"] or 0) * 100 / x["km"], 1)
              if (x.get("so_lit") and x.get("km")) else None)
        if ng and th and th > ng:
            vuot.append({"xe": x["xe"], "so_cho": v.seats, "tieu_hao": th, "nguong": ng})
    vuot.sort(key=lambda z: -(z["tieu_hao"] - z["nguong"]))

    return {
        "ngay_xe_hoat_dong": ngay or None,
        "cong_suat_khai_thac": cong_suat,
        # Ngày cuối mà mẫu số đếm tới, CHỈ khi nó sớm hơn hết kỳ — tức kỳ đang chạy dở. Màn hình in
        # nó cạnh nhãn. Không có dòng ấy thì «52,3%» của tháng 10 đọc ra như công suất CẢ THÁNG, và
        # người đọc lại mang một con số nửa tháng đi so với tháng 9 đã trọn.
        "cong_suat_den_ngay": d2_mau.isoformat() if (cong_suat is not None and d2_mau < d2) else None,
        "km_chay_rong": rong["km"] or None,
        "chi_phi_moi_km": chi_phi_moi_km,
        "da_chot": db.get(PeriodLock, ky) is not None,
        # HQ-2b — DOANH THU / LỢI NHUẬN. Chủ tịch quyết 13/10/2026: con số trên dòng chuyến là giá
        # của MỖI XE, nên một đoàn ba xe cộng cả ba là đúng. Đo trước khi hỏi: 59 đoàn dùng nhiều
        # hơn một xe, 40 đoàn trong đó ghi số tiền giống hệt nhau trên từng xe — 573.460.000 đ treo
        # trên đúng câu hỏi ấy. Dáng của 19 đoàn còn lại (3,5tr · 3,5tr · 3,5tr · 2,7tr) là dáng giá
        # từng xe theo loại xe, không phải một con số tổng chép lại nhiều lần.
        "doanh_thu": tong["doanh_thu"] or None,
        "loi_nhuan": tong["loi_nhuan"] if tong["doanh_thu"] else None,
        "ty_le_loi_nhuan": tong["ty_le_loi_nhuan"],
        "tieu_hao_l100": tieu_hao,
        # Ngưỡng chưa khai thì KHÔNG im lặng: in ra đang chờ ai, đúng luật của `cong_suat_thieu`.
        "tieu_hao_nguong_thieu": None if nguong else {
            "bo_phan": "Đội xe", "cua_nhap": "/doi-xe"},
        "tieu_hao_vuot": vuot or None,
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
        "_doanh_thu": tong["doanh_thu"] or 0,
        "_loi_nhuan": tong["loi_nhuan"] if tong["doanh_thu"] else 0,
        "_so_lit": so_lit,
        "_km_chuyen": km_chuyen,
        "_km_rong_lech": rong["so_lech"],
        "_so_xe_trong_doi": dh["so_xe"],
        "_so_ngay_ky": so_ngay_ky,
        # Mẫu số THẬT của công suất kỳ này (ngày-xe, đã dừng ở hôm nay). `_gop` cộng chính con số
        # này chứ không nhân lại `số xe × số ngày kỳ` — nhân lại là dựng chỗ cho quý/năm nói một
        # công suất khác tháng, và lúc ấy không ai biết màn nào đúng.
        "_ngay_xe_mau": mau,
    }


def ky_co_chuyen(db: Session) -> list[str]:
    """Các kỳ tháng THẬT SỰ có chuyến, mới nhất trước.

    Ô chọn kỳ chỉ được liệt kê những kỳ này. Liệt kê đủ 12 tháng cho đẹp thì người đọc bấm vào một
    tháng rỗng, thấy bốn dấu gạch, và lại kết luận "màn hình hỏng" — đúng cái vòng HQ-1c vừa sửa.
    """
    # Gom theo tháng BẰNG PYTHON, không bằng hàm ngày tháng của cơ sở dữ liệu: `strftime` là của
    # SQLite còn `to_char` là của PostgreSQL, và phép thử chạy SQLite trong khi hệ thật chạy
    # PostgreSQL — viết theo một bên thì bên kia hỏng ở chỗ không có phép thử nào nhìn thấy.
    # `func.distinct` làm mất kiểu cột, nên SQLite trả về CHUỖI còn PostgreSQL trả về `date`. Cắt
    # bảy ký tự đầu của dạng ISO đúng cho cả hai, và không phụ thuộc hàm ngày tháng của bên nào.
    ngay = db.execute(select(func.distinct(Trip.ngay_di))).scalars().all()
    return sorted({(d if isinstance(d, str) else d.isoformat())[:7] for d in ngay if d},
                  reverse=True)


def _nhom_ky(moc: date, den_thang: int | None = None) -> dict[str, list[str]]:
    """Ba kỳ tính đến `moc`. `den_thang` giới hạn số tháng của quý/năm — dùng cho KỲ TRƯỚC."""
    quy_dau = ((moc.month - 1) // 3) * 3 + 1
    quy = [f"{moc.year:04d}-{m:02d}" for m in range(quy_dau, moc.month + 1)]
    nam = [f"{moc.year:04d}-{m:02d}" for m in range(1, moc.month + 1)]
    if den_thang is not None:
        quy, nam = quy[:den_thang], nam[:den_thang]
    return {"thang": [f"{moc.year:04d}-{moc.month:02d}"], "quy": quy, "nam": nam}


def _ky_truoc(ten: str, moc: date, so_thang: int) -> list[str]:
    """Danh sách kỳ tháng của KỲ LIỀN TRƯỚC, CÙNG SỐ THÁNG với kỳ đang xem.

    Vì sao phải cùng số tháng: quý 4 mới đi được một tháng mà đem so với quý 3 đủ ba tháng thì mọi
    chỉ số cộng được đều tụt xuống một phần ba, và mũi tên đỏ ấy không nói gì về đội xe cả — nó chỉ
    nói quý này mới bắt đầu. So lệch số tháng là cách tạo ra một con số trông như phát hiện.
    """
    if ten == "thang":
        y, m = (moc.year - 1, 12) if moc.month == 1 else (moc.year, moc.month - 1)
        return [f"{y:04d}-{m:02d}"]
    if ten == "quy":
        # Quý luôn bắt đầu ở tháng 1, 4, 7 hoặc 10, nên quý liền trước không bao giờ vắt qua giữa
        # năm — chỉ lùi một năm khi quý này là quý 1.
        dau = ((moc.month - 1) // 3) * 3 + 1 - 3
        y = moc.year
        if dau <= 0:
            y, dau = y - 1, dau + 12
        return [f"{y:04d}-{dau + i:02d}" for i in range(so_thang)]
    return [f"{moc.year - 1:04d}-{m:02d}" for m in range(1, so_thang + 1)]


def _gop(db: Session, kys: list[str], nho: dict | None = None) -> dict:
    """Cộng nhiều kỳ tháng thành một kỳ.

    KHÔNG cộng những thứ không cộng được. Công suất, chi phí/km, tiêu hao, tỷ lệ lợi nhuận đều
    tính LẠI trên tổng — trung bình của mấy tỷ lệ có mẫu khác nhau là một con số không nghĩa gì.
    """
    # `nho` la bo nho tam DUNG CHUNG trong mot lan `theo_ky`. Ba ky long nhau - thang nam trong
    # quy, quy nam trong nam - nen khong co no thi thang dang xem duoc tinh BA lan, va tu vong HQ-2
    # them ba ky truoc nua thanh sau. Moi lan tinh thua la mot luot `fleet_lai_lo.bao_cao` quet lai
    # toan bo chuyen va chi phi cua thang ay.
    if nho is None:
        nho = {}
    ds = []
    for k in kys:
        if k not in nho:
            nho[k] = chi_so(db, k)
        ds.append(nho[k])
    ngay = sum((x["ngay_xe_hoat_dong"] or 0) for x in ds)
    rong = sum((x["km_chay_rong"] or 0) for x in ds)
    km_chuyen = sum(x["_km_chuyen"] for x in ds)
    km = km_chuyen + rong
    du = all(x["_so_xe_trong_doi"] is not None for x in ds)
    cho_ngay = sum(x["_ngay_xe_mau"] for x in ds)
    # Cộng GIÁ VỐN gốc, không nhân ngược từ `chi_phi_moi_km`: con số ấy đã làm tròn về đồng, và
    # nhân ngược một số đã tròn với quãng đường hàng chục nghìn km thì sai số đi theo cấp triệu.
    gia_von = sum(x["_gia_von"] for x in ds)
    dt = sum(x["_doanh_thu"] for x in ds)
    ln = sum(x["_loi_nhuan"] for x in ds)
    lit = sum(x["_so_lit"] for x in ds)
    vuot = [z for x in ds for z in (x["tieu_hao_vuot"] or [])]
    return {
        "ngay_xe_hoat_dong": ngay or None,
        "cong_suat_khai_thac": round(ngay * 100 / cho_ngay, 1) if du and cho_ngay else None,
        # Quý/năm lấy ngày cắt MUỘN NHẤT trong các tháng con: quý 4 gồm T10 (cắt ở 20/10), T11 và
        # T12 (chưa tới, không cắt gì vì không có mẫu). Chuỗi ISO so sánh đúng thứ tự ngày.
        "cong_suat_den_ngay": max((x["cong_suat_den_ngay"] for x in ds
                                   if x["cong_suat_den_ngay"]), default=None),
        "km_chay_rong": rong or None,
        "chi_phi_moi_km": round(gia_von / km) if km else None,
        "doanh_thu": dt or None,
        "loi_nhuan": ln if dt else None,
        "ty_le_loi_nhuan": round(ln / dt, 4) if dt else None,
        "tieu_hao_l100": round(lit * 100 / km_chuyen, 1) if (lit and km_chuyen) else None,
        "tieu_hao_nguong_thieu": next((x["tieu_hao_nguong_thieu"] for x in ds
                                       if x["tieu_hao_nguong_thieu"]), None),
        "tieu_hao_vuot": vuot or None,
        "da_chot": all(x["da_chot"] for x in ds),
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
        "cong_suat_thieu": None if du else next(
            (x["cong_suat_thieu"] for x in ds if x["cong_suat_thieu"]), None),
    }


def _chuoi(db: Session, moc: date, nho: dict | None = None) -> list[dict]:
    """12 tháng của NĂM chứa `moc` — T01 → T12 — cho hình diễn biến.

    VÌ SAO CẢ NĂM chứ không phải 12 tháng gần nhất tính lùi: hình này đọc cùng một câu hỏi với mọi
    báo cáo khác của công ty — "năm nay đội xe đi thế nào". Trục chạy lùi qua ranh giới năm thì
    tháng 1 và tháng 12 của CÙNG một năm nằm hai đầu hình, và không ai cộng nhẩm được một năm trên
    một trục như thế. Anh Tuấn soát trên bản chạy thật 20/10/2026 và chốt: đủ 12 cột T1–T12.

    THÁNG CHƯA TỚI VẪN CÓ CỘT, mang `None`. Bỏ chúng đi thì hình co lại dần theo từng tháng trong
    năm, và một hình đổi bề ngang mỗi lần mở là một hình không so được với lần mở trước. `None`
    khác 0: `BieuDoDuong` cắt đường tại `None`, còn 0 thì nối — vẽ 0 cho tháng 11 là nói rằng
    tháng ấy đội xe chạy mà không thu được đồng nào.

    `nho` dùng chung với `theo_ky`: kỳ NĂM đã tính sẵn các tháng đã qua, nên phần lớn cột lấy lại
    từ bộ nhớ tạm chứ không quét lại sổ chuyến.
    """
    if nho is None:
        nho = {}
    ds = []
    for m in range(1, 13):
        k = f"{moc.year:04d}-{m:02d}"
        o = _gop(db, [k], nho)
        ds.append({
            "ky": k,
            "nhan": f"T{m}/{moc.year % 100:02d}",
            "doanh_thu": o["doanh_thu"],
            "loi_nhuan": o["loi_nhuan"],
            "cong_suat_khai_thac": o["cong_suat_khai_thac"],
        })
    return ds


SO_SANH = ("ngay_xe_hoat_dong", "cong_suat_khai_thac", "km_chay_rong", "chi_phi_moi_km",
           "doanh_thu", "loi_nhuan", "tieu_hao_l100")


def theo_ky(db: Session, moc: date, hom_nay: date | None = None) -> dict:
    """Ba kỳ của ô chọn trên khối: tháng / quý / năm, tính đến `moc`, kèm so sánh với kỳ trước.

    `moc` KHÔNG còn bắt buộc là hôm nay (HQ-2a, 13/10/2026). Trước đây nó luôn là hôm nay, nên suốt
    tháng 10 — tháng chưa nạp chuyến nào — hai nút Tháng và Quý đều rỗng và màn hình chỉ còn mở được
    kỳ Năm. Chín tháng số liệu nằm sẵn trong máy mà không có đường nào mở ra, không xem được tháng 9,
    không so được tháng 9 với tháng 8. `hom_nay` tách riêng vì nó chỉ dùng để biết kỳ đã hết chưa.
    """
    hom_nay = hom_nay or date.today()
    nhom = _nhom_ky(moc)
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

    nho: dict = {}
    out: dict = {}
    for ten, kys in nhom.items():
        o = _gop(db, kys, nho)
        o["nhan"] = nhan[ten]
        # Kỳ rỗng thì nói VÌ SAO rỗng, ngay tại kỳ ấy. "Chưa có số" một mình đọc ra như hỏng;
        # "chưa nạp chuyến nào, số mới nhất là tháng 9" đọc ra là một việc có người làm được.
        o["trong_vi_sao"] = (None if o["ngay_xe_hoat_dong"] else
                             (f"{nhan[ten]} chưa nạp chuyến nào"
                              + (f" — số mới nhất là tháng {ky_cuoi[5:]}/{ky_cuoi[:4]}"
                                 if ky_cuoi and ky_cuoi not in kys else "") + "."
                              if ky_cuoi else f"{nhan[ten]} chưa nạp chuyến nào."))

        # HQ-2a — SO VỚI KỲ TRƯỚC, và chỉ khi kỳ này ĐÃ HẾT.
        #
        # Kỳ đang chạy mới đi được mấy ngày: đem 13 ngày đầu tháng 10 so với trọn tháng 9 thì mọi
        # chỉ số cộng được đều tụt, và mũi tên đỏ ấy nói về tờ lịch chứ không nói về đội xe. Thà
        # không có mũi tên còn hơn một mũi tên đọc ra điều không có thật.
        _, het = QT.ky_range(kys[-1])
        if het >= hom_nay:
            o["so_sanh"] = None
            o["chua_so_sanh_vi"] = f"{nhan[ten]} chưa hết — so với kỳ trước khi chưa đủ ngày là so lệch."
        else:
            kt = _ky_truoc(ten, moc, len(kys))
            t = _gop(db, kt, nho)
            o["so_sanh"] = {
                "nhan": f"so với {len(kt)} tháng liền trước ({kt[0]} → {kt[-1]})"
                        if len(kt) > 1 else f"so với tháng {kt[0][5:]}/{kt[0][:4]}",
                "lech": {k: (None if (o[k] is None or t[k] is None) else round(o[k] - t[k], 2))
                         for k in SO_SANH},
                "truoc": {k: t[k] for k in SO_SANH},
            }
            o["chua_so_sanh_vi"] = None
        out[ten] = o

    # Kỳ mở sẵn: kỳ HẸP NHẤT còn có số. Tháng trước, rồi quý, rồi năm — mở ra là thấy số, và là
    # con số gần hiện tại nhất có thể. Không kỳ nào có số thì giữ "thang" như cũ: lúc ấy ba nút đều
    # trống như nhau, và `trong_vi_sao` của kỳ tháng nói đúng việc phải làm.
    out["mac_dinh"] = next((t for t in ("thang", "quy", "nam")
                            if out[t]["ngay_xe_hoat_dong"]), "thang")
    out["ky_moi_nhat_co_chuyen"] = ky_cuoi
    # HQ-3 (20/10/2026) — chuỗi 12 kỳ cho hình diễn biến. Xem `_chuoi`.
    out["chuoi"] = _chuoi(db, moc, nho)
    out["moc"] = moc.isoformat()
    return out
