"""R5 · Bàn làm việc Giám đốc Kinh doanh lẻ — Chủ tịch duyệt bản xem trước 13/11/2026 03:21.

CHỈ ĐỌC, KHÔNG SỞ HỮU CON SỐ NÀO. Mỗi số trên bàn đọc lại từ MỘT hàm đang nuôi một màn có sẵn:

    chuyến đang bán · chỗ trống · sắp khởi hành · chưa có dự toán   ← services.ban_tour_le (/ban-tour-le)
    tài khoản chưa có đơn vị · số đơn vị mảng Lẻ                    ← services.to_chuc_kd (/to-chuc-kd)
    phiếu chăm sóc quá hạn                                           ← services.cskh (/cham-soc)
    khách chờ trả lời                                                ← bảng hội thoại (/inbox, cửa status)
    booking · doanh thu · lead · tour lệch quy tắc mảng              ← services.bao_cao_phong (/fit)
    doanh thu tính chỉ tiêu                                          ← services.doanh_thu_kd (/fit, tab doanh thu)

Không chép lại phép tính nào: chép là dựng bản thứ hai, và bản thứ hai rồi cũng lệch.

`None` KHÁC 0. Ô nào chưa có cơ sở để tính thì trả `None` kèm `ly_do`; màn hình in chữ «chưa đo»
cùng lý do, không in số 0 (ranh giới 09/9/2026 — không điền số tạm).

Hộp thư và chăm sóc là số TOÀN CÔNG TY: hai màn ấy chưa có phép lọc mảng. Chủ tịch đồng ý
13/11/2026 để nguyên và gắn nhãn `pham_vi = "toan_cong_ty"` — không đoán phần của Lẻ.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.crm import Conversation
from app.models.to_chuc_kd import DonViKD
from app.services import ban_tour_le as BTL
from app.services import cskh as CS
from app.services import doanh_thu_kd as DT
from app.services import to_chuc_kd as TC
from app.services import segments as SEG

TOAN_CTY = "toan_cong_ty"


def _o(so, nguon: str, ly_do: str = "", pham_vi: str = "kd_le") -> dict:
    return {"so": so, "nguon": nguon, "ly_do": "" if so is not None else (ly_do or "chưa có cửa đo"),
            "pham_vi": pham_vi}


def _doanh_thu_tinh_chi_tieu(db: Session, ky: str, ids: list[int]):
    """R5-9 (Chủ tịch 13/11/2026: «GĐ tính cả khối KD»): chưa khai đơn vị thì cộng MỌI booking tour lẻ của cả
    khối Kinh doanh (luồng `le`, ngăn `khoi_kd`) thay vì để trống. Đã khai thì cộng theo cây như cũ."""
    try:
        if not ids:
            return DT.thang(db, ky, "le", None).get("tong_tinh_chi_tieu"), ""
        return DT.thang(db, ky, "", ids).get("tong_tinh_chi_tieu"), ""
    except Exception as ex:  # noqa: BLE001 — một ô hỏng không làm sập cả bàn
        return None, f"Không đọc được: {ex}"


def doi_chieu_chu_tich(db: Session, d: date) -> dict:
    """R5-9 · Số Lẻ trên màn Chủ tịch (khối «Doanh thu theo phòng») — đặt cạnh để đối chiếu. Đọc ĐÚNG
    `dashboard.doanh_thu_phong`, không tính lại. Cơ sở: doanh thu chuyến, khác cơ sở chỉ tiêu (giá trị booking)."""
    try:
        from app.services import dashboard as DB
        le = DB.doanh_thu_phong(db, d)["le"]
        return {"thang": le.get("thang"), "chuyen_thang": le.get("chuyen_thang"),
                "co_so": "Doanh thu chuyến — khối «Doanh thu theo phòng» trên màn Chủ tịch / TGĐ"}
    except Exception:  # noqa: BLE001
        return {"thang": None, "chuyen_thang": None, "co_so": ""}


def _doi_ngu_phong(db: Session, d: date) -> dict:
    from app.services import ban_kd_vai as V          # nhập muộn: ban_kd_vai đã nhập module này
    kq = V.doi_ngu_ca_phong(db, 0, d)
    return {"doi_ngu": kq["doi_ngu"], "theo_nhom": kq["theo_nhom"], "nguon_doi_ngu": kq["nguon"]}


def tong_quan(db: Session, hom_nay: date | None = None) -> dict:
    d = hom_nay or date.today()
    ky = f"{d:%Y-%m}"

    btl = BTL.ban_lam_viec(db)
    rows, t = btl["rows"], btl["tong"]
    n = len(rows)

    don_vi = [dv.id for dv in db.execute(select(DonViKD).where(DonViKD.mang == "le")).scalars()
              if dv.dang_hieu_luc(d)]
    chua_pc = len(TC.chua_phan_cong(db, d, "le"))

    cs = CS.chi_so_cham_soc(db)
    cho_tra_loi = int(db.execute(select(func.count()).select_from(Conversation)
                                 .where(Conversation.unanswered == True)).scalar() or 0)  # noqa: E712

    # R5-4: đọc thẳng `segments.lech_quy_tac` — đúng hàm mà dòng ấy của bảng /fit đang đọc — thay cho
    # cả bảng chỉ tiêu phòng (bảng ấy tốn ~4 giây, mà bàn chỉ cần một con số của nó).
    lech = SEG.lech_quy_tac(db)["tong_lech"]

    dt_booking, ly_do_dt = _doanh_thu_tinh_chi_tieu(db, ky, don_vi)
    doi_chieu = doi_chieu_chu_tich(db, d)
    # R5-10 (Chủ tịch 13/11/2026 23:52): ô doanh thu của GĐ = doanh thu chuyến Lẻ tháng — đúng ô màn Chủ tịch / TGĐ.
    # Tổng giá trị booking (cơ sở xếp hạng từng NV) trả riêng để màn hình ghi kèm, không thay chỗ.
    dt = doi_chieu["thang"]
    if dt is None:
        ly_do_dt = "Không đọc được doanh thu theo phòng của màn Chủ tịch."
    co_du_toan = n - t["chua_du_co_so"]
    co_gia = sum(1 for r in rows if (r["gia_ban"] or 0) > 0)
    co_cpcd = sum(1 for r in rows if (r["chi_phi_co_dinh"] or 0) > 0)

    the = {
        "chuyen_dang_ban": _o(t["chuyen"], "/ban-tour-le"),
        "cho_con": _o(t["cho_con"], "/ban-tour-le"),
        "sap_khoi_hanh": _o(t["sap_khoi_hanh"], "/ban-tour-le"),
        "doanh_thu_chi_tieu": {**_o(dt, "dashboard.doanh_thu_phong · Lẻ (như màn Chủ tịch / TGĐ)", ly_do_dt),
                               "tong_booking": dt_booking},   # R5-2: /kinh-doanh-le gộp vào /fit
    }

    # Bảy việc, đúng thứ tự bản vẽ đã duyệt. `toi` = màn đang giữ nghiệp vụ (bàn mở nó trong khung).
    viec = [
        {"ma": "chua_don_vi", "muc": "do", "toi": "/to-chuc-kd",
         "ten": "Tài khoản kinh doanh chưa có đơn vị",
         "mo_ta": "Gốc của các việc khác: chưa khai đơn vị thì doanh thu và chỉ tiêu không có phạm vi. "
                  "Khai danh mục là việc của Hành chính – Nhân sự.",
         **_o(chua_pc, "/to-chuc-kd · chưa phân công")},
        {"ma": "chua_du_toan", "muc": "do", "toi": "/ban-tour-le",
         "ten": "Chuyến đang bán chưa có dự toán riêng",
         "mo_ta": "Các chuyến này ghi lợi nhuận «chưa đủ cơ sở tính».",
         **_o(t["chua_du_co_so"], "/ban-tour-le")},
        {"ma": "cham_soc_qua_han", "muc": "do", "toi": "/cham-soc",
         "ten": "Phiếu chăm sóc quá hạn liên hệ",
         "mo_ta": f"{cs['chua_ghi']} phiếu chưa ghi kết quả.",
         **_o(cs["qua_han"], "/cham-soc · chỉ số", pham_vi=TOAN_CTY)},
        {"ma": "hop_thu_cho", "muc": "cam", "toi": "/inbox",
         "ten": "Khách đang chờ sale trả lời",
         "mo_ta": "Hội thoại khách nhắn chưa ai trả lời.",
         **_o(cho_tra_loi, "/inbox", pham_vi=TOAN_CTY)},
        {"ma": "sap_khoi_hanh", "muc": "cam", "toi": "/ban-tour-le",
         "ten": "Chuyến khởi hành trong 7 ngày",
         "mo_ta": "Hết ngày khởi hành là hết bán. Danh sách ở bảng «Chuyến cần thúc bán».",
         **_o(t["sap_khoi_hanh"], "/ban-tour-le")},
        {"ma": "lech_mang", "muc": "vang", "toi": "/fit",
         "ten": "Tour hai quy tắc mảng nói khác nhau",
         "mo_ta": "Kinh doanh sửa dữ liệu gốc (loại chuyến hoặc mã tour) để hai quy tắc khớp lại.",
         **_o(lech, "/fit")},
        {"ma": "cho_dieu_hanh", "muc": "cho", "toi": "",
         "ten": "Lịch khởi hành do Phòng Điều hành mở",
         "mo_ta": "Bàn này không mở chuyến mới được. Đây là việc chờ, không phải việc tồn của phòng.",
         "so": None, "nguon": "", "ly_do": "", "pham_vi": "kd_le"},
    ]

    from app.services import dem_tour as DEM
    gd = DEM.theo_giai_doan(db, hom_nay=d)
    # R5-10: «Tour đang bán» và «Tour đang đi» đọc ĐÚNG khối «Tour theo giai đoạn» của màn Chủ tịch / TGĐ.
    hoat_dong = {"dang_ban": gd.get("dang_ban"), "cho_con": t["cho_con"], "sap_khoi_hanh": t["sap_khoi_hanh"],
                 "dang_di": gd.get("dang_chay"), "nguon_dang_di": "dem_tour.theo_giai_doan (mọi tour, như trang chủ)"}

    san_sang = [
        {"ten": "Có lịch khởi hành đang bán", "dat": n > 0, "so": f"{n}"},
        {"ten": "Có giá bán trên từng chuyến", "dat": n > 0 and co_gia == n, "so": f"{co_gia} / {n}"},
        {"ten": "Dự toán riêng từng chuyến", "dat": n > 0 and co_du_toan == n, "so": f"{co_du_toan} / {n}"},
        {"ten": "Chi phí cố định từng chuyến", "dat": n > 0 and co_cpcd == n, "so": f"{co_cpcd} / {n}"},
        {"ten": "Đơn vị kinh doanh", "dat": bool(don_vi) and chua_pc == 0,
         "so": f"{len(don_vi)} đơn vị · {chua_pc} người chưa gắn"},
    ]

    return {"ngay": d.isoformat(), "the": the, "viec": viec, "hoat_dong": hoat_dong,
            "san_sang": san_sang, "thuc_ban": thuc_ban(db, rows), "phai_thu": phai_thu_le(db, d),
            "doi_chieu": doi_chieu,
            # R5-11: Đội ngũ + Theo nhóm của cả phòng Lẻ — cùng hàm, cùng cách tính với bàn Trưởng phòng.
            **_doi_ngu_phong(db, d),
            "doanh_thu_pham_vi": "ca_khoi_kd" if not don_vi else "co_cau"}


def thuc_ban(db: Session, rows: list | None = None) -> list[dict]:
    """Chuyến cần thúc bán: khởi hành trong 7 ngày, còn chỗ, trống nhiều đứng đầu. R5-7: dùng chung cho
    bàn GĐ và ba bàn TP / Trưởng nhóm / Chuyên viên — một hàm, cùng số."""
    if rows is None:
        rows = BTL.ban_lam_viec(db)["rows"]
    thuc = sorted([r for r in rows if r["days_left"] <= 7 and r["cho_con"] > 0],
                  key=lambda r: (-r["cho_con"], r["start_date"]))
    return [{"id": r["id"], "code": r["code"], "name": r["name"], "start_date": r["start_date"],
                 "cho_da_ban": r["cho_da_ban"], "cho_mo_ban": r["cho_mo_ban"], "cho_con": r["cho_con"],
                 "gia_ban": r["gia_ban"], "loi_nhuan_tai_so_dang_ban": r["loi_nhuan_tai_so_dang_ban"],
                 "trang_thai_cong": r["trang_thai_cong"],
                 "khach_hoa_von": r.get("khach_hoa_von"), "khach_dat_bien": r.get("khach_dat_bien"),
                 "bien_muc_tieu": r.get("bien_muc_tieu"), "khach_toi_da": r.get("khach_toi_da"),
                 "bien_khi_day": r.get("bien_khi_day")} for r in thuc]


def phai_thu_le(db: Session, hom_nay: date | None = None, sales_ids: list[int] | None = None) -> dict:
    """R5-4 · Phải thu KHÁCH của booking tour LẺ, chia bảy mốc hạn — cùng bảy khoảng với khối Phải thu
    của Chủ tịch (`han_cong_no.khoang`), để hai khối đọc được cạnh nhau.

    Còn nợ = giá trị booking − đã thu (booking chưa huỷ). HẠN = ngày khởi hành của chuyến: khách lẻ trả
    đủ trước ngày đi, và đó là mốc duy nhất mọi booking đều có. Chuyến đã đi mà còn nợ → «Quá hạn».

    R5-7: `sales_ids` cắt về booking của những người ấy (bàn TP / Trưởng nhóm / Chuyên viên). `None` = cả
    phòng (bàn GĐ). Danh sách rỗng khác None: rỗng → không có booking nào."""
    from app.models.core import Booking, Tour
    from app.services import han_cong_no as HCN
    from datetime import timedelta
    d = hom_nay or date.today()
    khoang = HCN.khoang(d)
    nhom = {nhan: 0.0 for nhan, _, _ in khoang}
    so_bk, co = 0, False
    # R5-9 (Chủ tịch 13/11/2026): chuyến đã đi QUÁ 30 NGÀY mà booking còn nợ tách ra «nợ cũ cần đối soát» —
    # phần lớn là booking chưa ghi đã thu, không phải nợ thật. Tổng chính + nợ cũ = tổng cũ.
    moc_cu = d - timedelta(days=30)
    cu, so_cu = 0.0, 0
    q = (select(Booking, Tour).join(Tour, Tour.id == Booking.tour_id)
         .where(Booking.cancelled == False, Tour.tour_type.in_(SEG.LE_TYPES)))  # noqa: E712
    if sales_ids is not None:
        q = q.where(Booking.sales_id.in_(sales_ids))
    for bk, tour in db.execute(q).all():
        if SEG.mang_of(tour) != "le" or tour.start_date is None:
            continue
        # R5-10: cùng công thức ô «Phải thu» màn Chủ tịch (`dashboard._so_du_no_vay_phai_thu`): giá trị − giảm giá − đã thu.
        no = float(bk.amount or 0) - float(bk.discount or 0) - float(bk.paid or 0)
        if no <= 0.5:
            continue
        if tour.start_date < moc_cu:
            cu += no; so_cu += 1
            continue
        co = True; so_bk += 1
        for nhan, tu, den in khoang:
            if tu <= tour.start_date <= den:
                nhom[nhan] += no
                break
    no_cu = {"tong": cu if so_cu else None, "so_booking": so_cu,
             "ghi": "Chuyến đã đi quá 30 ngày mà booking chưa ghi đã thu — Kế toán đối soát"}
    if not co:
        return {"nhom": {nhan: None for nhan in nhom}, "tong": None, "so_booking": 0,
                "ly_do": "Không có booking tour lẻ nào còn nợ (trong 30 ngày qua và sắp tới).", "no_cu": no_cu}
    return {"nhom": nhom, "tong": sum(nhom.values()), "so_booking": so_bk, "ly_do": "", "no_cu": no_cu}


def doanh_thu_le(db: Session, nam: int) -> dict:
    """R5-4 · Doanh thu tour LẺ từng tháng của một năm, cạnh chỉ tiêu tháng.

    Doanh thu = ngăn `le` của `ket_qua_that.thang` — CÙNG tập đã cộng ra doanh thu trên biểu đồ của
    Chủ tịch (TC-98), không phải phép tính thứ hai. Chỉ tiêu = tổng chỉ tiêu đã giao cho các đơn vị
    GỐC của cây Kinh doanh lẻ (luồng «tất cả»). Chưa khai đơn vị / chưa giao → None, không vẽ 0."""
    from app.services import ket_qua_that as KQT
    from app.services import chi_tieu_kd as CT
    goc = [dv.id for dv in db.execute(select(DonViKD).where(DonViKD.mang == "le",
                                                             DonViKD.cha_id.is_(None))).scalars()]
    thang = []
    nay = date.today()
    for m in range(1, 13):
        ky = f"{nam}-{m:02d}"
        if date(nam, m, 1) > nay:
            thang.append({"ky": ky, "doanh_thu": None, "chi_tieu": None})
            continue
        try:
            dt = (KQT.thang(db, ky).get("theo_mang") or {}).get("le", {}).get("doanh_thu")
        except Exception:  # noqa: BLE001 — một tháng hỏng không làm sập cả biểu đồ
            dt = None
        ct = None
        if goc:
            bang = CT.tra_cuu(db, ky)["don_vi"]
            vals = [bang.get(f"{i}|tat_ca") for i in goc]
            vals = [v for v in vals if v is not None]
            ct = sum(vals) if vals else None
        thang.append({"ky": ky, "doanh_thu": dt, "chi_tieu": ct})
    dts = [x["doanh_thu"] for x in thang if x["doanh_thu"] is not None]
    cts = [x["chi_tieu"] for x in thang if x["chi_tieu"] is not None]
    tong = sum(dts) if dts else None
    tong_ct = sum(cts) if cts else None
    return {"nam": nam, "thang": thang, "tong_doanh_thu": tong, "tong_chi_tieu": tong_ct,
            "ty_le_dat": (tong / tong_ct) if (tong is not None and tong_ct) else None,
            "ly_do_chi_tieu": "" if goc else "Chưa khai đơn vị Kinh doanh lẻ nên chưa có chỉ tiêu để đặt cạnh."}
