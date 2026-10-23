"""Bộ nạp dữ liệu vào VTOS – một cửa duy nhất cho người nhập tay, cho tệp tải lên, và cho AI.

Vì sao phải có một cửa chung thay vì mỗi phân hệ tự làm một kiểu nhập:

  Dữ liệu vào hệ thống bằng ba đường – người gõ tay, người tải tệp lên, và tác vụ tự động nạp. Nếu ba
  đường đó có ba cách kiểm tra khác nhau thì cái chặt nhất trở nên vô nghĩa: người ta chỉ cần đi đường
  lỏng nhất. Ở đây cả ba đi qua CÙNG một bộ kiểm tra, cùng một khóa chống trùng, cùng một nhật ký.

Bốn quy tắc, và mỗi quy tắc ứng một cách nạp dữ liệu làm hỏng sổ:

  1. KIỂM TRA TRƯỚC, NẠP SAU. Bấm một nút rồi 500 dòng rác nằm trong sổ là chuyện của vài giây; dọn nó
     là chuyện của vài ngày. Hàm kiểm tra KHÔNG ghi gì, và trả về lỗi theo từng dòng.
  2. DÒNG LỖI KHÔNG BỊ IM LẶNG BỎ QUA. Có lỗi thì mặc định KHÔNG nạp gì cả. Muốn nạp phần hợp lệ thì
     người nạp phải nói rõ – bỏ qua dòng lỗi là một quyết định, không phải một mặc định.
  3. NẠP LẠI CÙNG TỆP KHÔNG NHÂN ĐÔI. Mỗi bộ nạp có khóa chống trùng riêng; dòng đã có được ĐẾM RIÊNG
     là "đã có", không phải lỗi, cũng không phải bản ghi mới.
  4. DỮ LIỆU NẠP LÀ DỮ LIỆU CHƯA ĐỐI CHIẾU. Nó vào hệ thống kèm nguồn và nhật ký, không mặc nhiên thành
     số liệu chính thức – ai đọc cũng phải thấy được nó từ đâu ra.
"""
import csv, hashlib, io, json, re
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.intake import IntakeRun

NGUON = {"nguoi_nhap": "Người nhập", "nhap_tay": "Nhập tay từng dòng", "nap_tep": "Tải tệp",
         "doc_anh": "Ảnh – AI đọc, người xác nhận", "ai": "Tác vụ AI", "he_thong": "Hệ thống khác"}


# ====================== ĐỌC TỆP ======================
def doc_theo_bo(loai: str, noi_dung: bytes, ten_tep: str) -> list[dict]:
    """Đọc tệp theo bộ nạp. Bộ nạp khai 'doc_tep' thì dùng bộ đọc riêng (ví dụ workbook nhiều sheet của
    quyết toán tour); không khai thì dùng bộ đọc chuẩn một sheet.

    Vẫn là MỘT cơ chế nạp: bốn bước, một bộ kiểm, một nhật ký. Chỉ khác ở chỗ đọc tệp – ép mọi tệp về
    một sheet phẳng thì tệp quyết toán tour phải sửa tay trước khi nạp, và việc sửa tay đó chính là chỗ
    số bị đổi mà không ai biết."""
    bo = BO_NAP.get(loai) or {}
    if bo.get("doc_tep"):
        return bo["doc_tep"](noi_dung, ten_tep)
    return doc_bang(noi_dung, ten_tep)


def doc_bang(noi_dung: bytes, ten_tep: str) -> list[dict]:
    """Đọc .csv hoặc .xlsx thành danh sách dòng theo TÊN CỘT ở hàng đầu.

    Tên cột được chuẩn hóa (bỏ khoảng trắng thừa, đưa về chữ thường) để "Tên NCC" và "tên ncc " là một."""
    ten = (ten_tep or "").lower()
    if ten.endswith(".xlsx") or ten.endswith(".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(noi_dung), data_only=True, read_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        if not rows: return []
        dau = [_chuan_cot(c) for c in rows[0]]
        out = []
        for r in rows[1:]:
            if all(v is None or str(v).strip() == "" for v in r): continue
            out.append({dau[i]: r[i] for i in range(min(len(dau), len(r))) if dau[i]})
        return out
    text = noi_dung.decode("utf-8-sig", errors="replace") if isinstance(noi_dung, bytes) else str(noi_dung)
    # Tách bằng dấu phẩy hoặc chấm phẩy – bảng xuất từ Excel tiếng Việt hay dùng chấm phẩy.
    mau = text.splitlines()[0] if text.splitlines() else ""
    delim = ";" if mau.count(";") > mau.count(",") else ","
    rd = csv.DictReader(io.StringIO(text), delimiter=delim)
    return [{_chuan_cot(k): v for k, v in row.items() if k} for row in rd]


def _chuan_cot(c) -> str:
    return " ".join(str(c or "").strip().lower().split())


def _so(v) -> float:
    """Đọc số từ ô người dùng gõ: '1.200.000', '1,200,000', '1200000 đ' đều là một triệu hai."""
    if v is None or str(v).strip() == "": return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = "".join(ch for ch in str(v) if ch.isdigit() or ch in ".,-")
    if s.count(",") and s.count("."):
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    else:
        s = s.replace(".", "").replace(",", "")
    try: return float(s or 0)
    except ValueError: return 0.0


def _ngay(v):
    if v in (None, ""): return None
    if isinstance(v, datetime): return v.date()
    if isinstance(v, date): return v
    s = str(v).strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try: return datetime.strptime(s, f).date()
        except ValueError: continue
    raise ValueError(f"Ngày không đọc được: {v!r} (dùng dạng 2026-08-31 hoặc 31/08/2026)")


# ====================== KHAI BÁO CÁC BỘ NẠP ======================
def _c(key, ten, bat_buoc=False, kieu="chu", vi_du="", ghi_chu="", **thuoc_tinh):
    """Khai báo một cột. Khai một lần, dùng cho CẢ BA CỬA (nhập tay, tải tệp, ảnh do AI đọc).

    Thuộc tính thêm (V1, lệnh 08/9): min / max cho số, chon={ma: ten} cho danh sách,
    khoa_ky=True cho cột ngày quyết định kỳ kế toán, khong_tuong_lai=True cho ngày không được ở tương lai."""
    return {"key": key, "ten": ten, "bat_buoc": bat_buoc, "kieu": kieu, "vi_du": vi_du,
            "ghi_chu": ghi_chu, **thuoc_tinh}


def _ncc_kiem(db, r):
    from app.models.suppliers import Supplier, LOAI_NCC
    loi, cb = [], []
    ten = str(r.get("ten") or "").strip()
    if not ten: loi.append("Thiếu tên nhà cung cấp")
    loai = str(r.get("loai") or "khac").strip()
    if loai not in LOAI_NCC: loi.append(f"Loại '{loai}' không hợp lệ ({', '.join(LOAI_NCC)})")
    mst = str(r.get("ma_so_thue") or "").strip()
    if not mst:
        cb.append("Chưa có mã số thuế – chi cho đối tác này khó lấy hóa đơn GTGT")
    elif not re.fullmatch(r"\d{10}(-\d{3})?", mst):
        # CẢNH BÁO, không phải LỖI: vẫn nạp được, nhưng phải nói ra. Mã số thuế Việt Nam là 10 chữ số,
        # hoặc 10-3 cho đơn vị phụ thuộc. Đo trên tệp danh mục thật của công ty: 47 trong 280 dòng
        # không đúng dạng – phần lớn là 11 chữ số hoặc 9 chữ số (dạng cũ). Mã sai dạng thì hoá đơn của
        # đối tác ấy không kê khai khấu trừ được, và chỉ phát hiện ra vào lúc quyết toán thuế.
        cb.append(f"Mã số thuế '{mst}' không đúng dạng 10 chữ số (hoặc 10-3 cho đơn vị phụ thuộc) – "
                  f"kiểm lại trước khi dùng để kê khai")
    if not str(r.get("ten_phap_nhan") or "").strip():
        cb.append("Chưa có tên pháp nhân – hoá đơn mang tên pháp nhân, không mang tên giao dịch")
    trung = None
    if ten:
        trung = db.execute(select(Supplier).where(func.lower(Supplier.ten) == ten.lower())).scalars().first()
    return loi, cb, (trung.code if trung is not None else None)


def _ncc_nap(db, r, boi):
    from app.services import suppliers as SU
    s = SU.tao_ncc(db, {k: (str(v).strip() if v is not None else "") for k, v in r.items()}, boi)
    return f"{s.code} – {s.ten}"


def _don_kiem(db, r):
    from app.models.suppliers import Supplier, ServiceOrder
    from app.models.core import Tour
    loi, cb = [], []
    ten = str(r.get("nha_cung_cap") or "").strip()
    s = db.execute(select(Supplier).where(func.lower(Supplier.ten) == ten.lower())).scalars().first() if ten else None
    if s is None: loi.append(f"Không có nhà cung cấp tên '{ten}' – tạo hồ sơ nhà cung cấp trước")
    ma_tour = str(r.get("ma_tour") or "").strip()
    t = db.execute(select(Tour).where(func.lower(Tour.code) == ma_tour.lower())).scalars().first() if ma_tour else None
    if t is None:
        loi.append(f"Không có tour mã '{ma_tour}'. Đơn đặt dịch vụ bắt buộc gắn tour – chi phí không gắn "
                   "tour thì không quy được vào giá thành")
    if not str(r.get("noi_dung") or "").strip(): loi.append("Thiếu nội dung dịch vụ")
    tt = _so(r.get("thanh_tien")) or _so(r.get("so_luong")) * _so(r.get("don_gia"))
    if tt <= 0: loi.append("Thành tiền phải lớn hơn 0")
    try: _ngay(r.get("ngay_su_dung"))
    except ValueError as ex: loi.append(str(ex))
    return loi, cb, None


def _don_nap(db, r, boi):
    from app.models.suppliers import Supplier
    from app.models.core import Tour
    from app.services import suppliers as SU
    s = db.execute(select(Supplier).where(
        func.lower(Supplier.ten) == str(r["nha_cung_cap"]).strip().lower())).scalars().first()
    t = db.execute(select(Tour).where(
        func.lower(Tour.code) == str(r["ma_tour"]).strip().lower())).scalars().first()
    d = SU.tao_don(db, {"supplier_id": s.id, "tour_id": t.id, "loai": str(r.get("loai") or "").strip(),
                        "noi_dung": str(r.get("noi_dung") or ""), "ngay_su_dung": _ngay(r.get("ngay_su_dung")),
                        "so_luong": _so(r.get("so_luong")) or 1, "don_vi": str(r.get("don_vi") or ""),
                        "don_gia": _so(r.get("don_gia")), "thanh_tien": _so(r.get("thanh_tien")),
                        "note": str(r.get("ghi_chu") or "")}, boi)
    return f"{d.code} – {d.thanh_tien:,.0f} đ"


def _chuyen_kiem(db, r):
    from app.models.fleet import Trip
    from app.services import fleet as FL
    loi, cb = [], []
    ma = str(r.get("ma_phieu") or "").strip()
    if not ma: loi.append("Thiếu mã phiếu gốc – không có mã thì không chống được nạp trùng")
    bien = str(r.get("bien_so") or "").strip()
    v = None
    try:
        d1 = _ngay(r.get("ngay_di")); d2 = _ngay(r.get("ngay_ve"))
        if d1 is None or d2 is None: loi.append("Thiếu ngày đi hoặc ngày về")
        elif d2 < d1: loi.append("Ngày về trước ngày đi")
        if bien and d1: v = FL.xe_theo_bien(db, bien, d1)
    except ValueError as ex:
        loi.append(str(ex))
    if bien and v is None: loi.append(f"Không tra ra xe từ biển số '{bien}'")
    if not bien: loi.append("Thiếu biển số xe")
    kd, kc = r.get("km_dau"), r.get("km_cuoi")
    if kd not in (None, "") and kc not in (None, "") and _so(kc) < _so(kd):
        loi.append("Km cuối nhỏ hơn km đầu")
    if kd in (None, "") or kc in (None, ""):
        cb.append("Chưa có km đầu/km cuối – hệ thống ghi 'chưa đo', không tính là 0")
    da_co = db.execute(select(Trip).where(Trip.ma_phieu == ma)).scalars().first() if ma else None
    return loi, cb, (da_co.ma_phieu if da_co is not None else None)


def _chuyen_nap(db, r, boi):
    from app.services import fleet as FL
    row = {"ma_phieu": str(r["ma_phieu"]).strip(), "bien_so": str(r.get("bien_so") or "").strip(),
           "ten_tour": str(r.get("ten_tour") or ""), "ngay_di": _ngay(r.get("ngay_di")),
           "ngay_ve": _ngay(r.get("ngay_ve")),
           "km_dau": int(_so(r.get("km_dau"))) or None, "km_cuoi": int(_so(r.get("km_cuoi"))) or None,
           # `or None` giữ đúng nghĩa "chưa đo" cho cả ba ô km: ô trống đọc ra 0, và 0 ở đây KHÔNG
           # phải một số đo — nó là chỗ chưa ai điền. Ghi 0 vào `km_gps` thì nhánh `elif t.km_gps:`
           # của cửa kiểm vẫn im, nhưng màn hình lại hiện một con số, tức là nói dối gọn gàng hơn.
           "km_gps": int(_so(r.get("km_gps"))) or None,
           "km_nguon": str(r.get("km_nguon") or "").strip(),
           "doanh_thu": _so(r.get("doanh_thu")),
           "chi_phi": {"dau": _so(r.get("tien_dau")), "lit": _so(r.get("so_lit")),
                       "cau_duong": _so(r.get("cau_duong")), "cong_tac_phi": _so(r.get("cong_tac_phi")),
                       "giu_xe": _so(r.get("giu_xe"))}}
    kq = FL.nhap_chuyen_hang_loat(db, "nap_tep", [row], boi, tao_xe_thieu=False)
    if kq["da_nhap"] != 1:
        raise ValueError("Không nạp được dòng này: " + json.dumps(kq.get("xe_khong_tra_ra"), ensure_ascii=False))
    return row["ma_phieu"]


def cot_tien_cua_bo(loai: str) -> tuple[list[str], list[str]]:
    """(cột CHẮC CHẮN là tiền, cột số CHƯA RÕ) của một bộ nạp.

    Dùng lại đúng bộ xếp loại của K1/K2 (`ks_cot_tien.xep_theo_ten`) thay vì viết bảng tên cột thứ hai.
    Hai bảng khai tay thì sớm muộn cũng lệch, và lúc lệch thì không ai biết bảng nào đúng.

    CHỈ cộng những cột xếp loại "tien". Cột "chưa rõ" (so_lit, km_dau, giu_xe…) KHÔNG cộng vào – cộng
    nhầm số lít vào tổng tiền thì con số đối chiếu vô nghĩa, mà vô nghĩa một cách âm thầm. Danh sách
    "chưa rõ" trả về để K5 nói thẳng phần nào chưa được che, thay vì im lặng che thiếu.
    """
    from app.services.ks_cot_tien import xep_theo_ten
    bo = BO_NAP.get(loai) or {}
    tien, chua_ro = [], []
    for c in bo.get("cot", []):
        if (c.get("kieu") or "") != "so": continue
        khoa = c.get("khoa") or c.get("key") or ""
        if not khoa: continue
        xep, _ = xep_theo_ten(khoa)
        (tien if xep == "tien" else chua_ro if xep == "chua_ro" else []).append(khoa)
    return tien, chua_ro


def _tong_tien_dong(row: dict, cot: list[str]) -> float:
    return round(sum(_so(row.get(k)) for k in cot), 2)


BO_NAP = {
    "nha_cung_cap": {
        "ten": "Nhà cung cấp", "bang_dich": "suppliers", "phong_ban": "dieu_hanh",
        "mo_ta": "Danh mục nhà cung cấp. Số tài khoản nạp lần đầu ở đây; đổi về sau phải qua đề nghị có "
                 "người thứ hai xác nhận.",
        "khoa_chong_trung": "Tên nhà cung cấp",
        "cot": [_c("ten", "Tên nhà cung cấp", True, vi_du="Khách sạn Mường Thanh Đà Lạt",
                   ghi_chu="Tên GIAO DỊCH – tên mà điều hành gọi hằng ngày"),
                _c("ten_phap_nhan", "Tên pháp nhân", vi_du="CTY TNHH PHÁT HOÀNG LONG",
                   ghi_chu="Tên trên HOÁ ĐƠN. Khác tên giao dịch: 'RESORT VĨNH HY' xuất hoá đơn dưới "
                           "tên 'CTY TNHH PHÁT HOÀNG LONG'. Thiếu tên này thì kê khai thuế không khớp."),
                _c("loai", "Loại", vi_du="khach_san", ghi_chu="khach_san / nha_hang / van_chuyen / "
                                                              "ve_tham_quan / hdv / hang_khong / tau_thuyen / khac"),
                _c("ma_so_thue", "Mã số thuế", vi_du="0312345678"),
                _c("nguoi_lien_he", "Người liên hệ"), _c("dien_thoai", "Điện thoại"),
                _c("email", "Email"), _c("dia_chi", "Địa chỉ"),
                _c("so_tai_khoan", "Số tài khoản"), _c("ngan_hang", "Ngân hàng"),
                _c("chu_tai_khoan", "Chủ tài khoản"),
                _c("dieu_khoan_tt", "Điều khoản thanh toán", vi_du="Thanh toán trong 15 ngày sau tour")],
        "kiem": _ncc_kiem, "nap": _ncc_nap,
    },
    "don_dich_vu": {
        "ten": "Đơn đặt dịch vụ", "bang_dich": "service_orders", "phong_ban": "dieu_hanh",
        "mo_ta": "Dịch vụ đã đặt cho từng tour. Bắt buộc có nhà cung cấp (đã tồn tại) và mã tour.",
        "khoa_chong_trung": "Không có – mỗi dòng là một đơn mới, nạp lại sẽ tạo thêm đơn",
        "cot": [_c("nha_cung_cap", "Tên nhà cung cấp", True, ghi_chu="phải trùng tên đã có trong danh mục"),
                _c("ma_tour", "Mã tour", True, vi_du="DL2609-01"),
                _c("noi_dung", "Nội dung dịch vụ", True, vi_du="20 phòng đôi 2 đêm"),
                _c("ngay_su_dung", "Ngày sử dụng", kieu="ngay", vi_du="31/08/2026"),
                _c("so_luong", "Số lượng", kieu="so", vi_du="20"), _c("don_vi", "Đơn vị", vi_du="phòng"),
                _c("don_gia", "Đơn giá", kieu="so", vi_du="800000"),
                _c("thanh_tien", "Thành tiền", kieu="so", ghi_chu="để trống thì lấy số lượng × đơn giá"),
                _c("ghi_chu", "Ghi chú")],
        "kiem": _don_kiem, "nap": _don_nap,
    },
    "chuyen_xe": {
        "ten": "Nhật trình chuyến xe", "bang_dich": "fleet_trips", "phong_ban": "doi_xe",
        "mo_ta": "Phiếu chi phí xe theo từng chuyến. Bốn khoản chi phí do Vietourist tạm ứng.",
        "khoa_chong_trung": "Mã phiếu gốc",
        "cot": [_c("ma_phieu", "Mã phiếu gốc", True, vi_du="VTRIP-CH-100",
                   ghi_chu="mã bên hệ thống nguồn – để nạp lại cùng tệp không nhân đôi"),
                _c("bien_so", "Biển số xe", True, vi_du="50F-017.37",
                   ghi_chu="ghi cách nào cũng được: 50F-017.37, 50F 017.37, 50F01737"),
                _c("ten_tour", "Tour / khách hàng", vi_du="Đà Lạt (lẻ)"),
                _c("ngay_di", "Ngày đi", True, kieu="ngay", vi_du="01/08/2026",
                   khoa_ky=True, khong_tuong_lai=True),
                _c("ngay_ve", "Ngày về", True, kieu="ngay", vi_du="03/08/2026"),
                _c("km_dau", "Km đầu", kieu="so", ghi_chu="để trống nghĩa là CHƯA ĐO, không phải 0"),
                _c("km_cuoi", "Km cuối", kieu="so"),
                # ── KM THEO GPS · 07/10/2026 ──────────────────────────────────────────────────
                # Hai cột này mở cửa cho một con số ĐÃ CÓ NGƯỜI ĐỌC nhưng chưa bao giờ có đường vào.
                #
                # Trước bản này: cột `fleet_trips.km_gps` có; tham số ngưỡng `xe_lech_km_gps` có;
                # và `fleet.kiem_tra_chuyen` ĐỌC nó để bật cờ ĐỎ "km đồng hồ lệch GPS quá ngưỡng".
                # Nhưng rà cả kho thì KHÔNG một bộ nạp nào và KHÔNG một ô nào trên màn hình ghi vào
                # cột ấy — nên nhánh `elif t.km_gps:` chưa bao giờ chạy một lần.
                #
                # Một cờ không thể đỏ còn tệ hơn không có cờ: màn hình đội xe hiện "không lệch"
                # trong khi sự thật là nó chưa từng so. Đây đúng là ranh giới 09/9/2026 — mỗi con số
                # cần một cửa; không cửa thì là việc CÒN THIẾU, không phải số liệu để ai đó nhập hộ.
                _c("km_gps", "Km theo GPS", kieu="so",
                   ghi_chu="lấy từ cổng giám sát hành trình. Để trống nghĩa là KỲ NÀY KHÔNG CÓ SỐ "
                           "GPS — khác hẳn 0, và khác hẳn 'đã so, không lệch'"),
                # Đội xe đang theo dõi trên BA cổng (TTC · TCD · Vietmap), nên ô này phải nói CỔNG
                # NÀO chứ không chỉ "gps": lúc km đồng hồ lệch, câu hỏi tiếp theo luôn là lệch với
                # cổng nào, và ba cổng có thể cho ba con số cho cùng một chiếc xe.
                _c("km_nguon", "Nguồn số km", vi_du="gps_vietmap",
                   ghi_chu="anh_dong_ho / nhap_tay / gps_ttc / gps_tcd / gps_vietmap — xem "
                           "models/fleet.py::KM_NGUON. Ghi sai tên thì cửa nạp báo lại, không nuốt"),
                _c("doanh_thu", "Doanh thu", kieu="so"),
                _c("tien_dau", "Tiền dầu", kieu="so"), _c("so_lit", "Số lít", kieu="so"),
                _c("cau_duong", "Phí cầu đường", kieu="so"),
                _c("cong_tac_phi", "Công tác phí tài xế", kieu="so"),
                _c("giu_xe", "Phí gửi xe", kieu="so")],
        "kiem": _chuyen_kiem, "nap": _chuyen_nap,
    },
}


# Các bộ nạp của phòng ban khai báo ở tệp riêng: thêm loại dữ liệu mới không đụng vào luồng nạp.
from app.services.intake_phong_ban import bo_nap as _bo_nap_phong_ban   # noqa: E402
BO_NAP.update(_bo_nap_phong_ban(_c))
# V4 (08/9/2026) – mười bốn bộ nạp còn thiếu. Tệp thứ hai chứ không viết nối vào tệp trên: hai robot
# đang sửa cùng một kho mã trong cùng một ngày, và một tệp 900 dòng do hai bên cùng sửa là một lần
# gộp hỏng chờ sẵn.
from app.services import intake_phong_ban_2 as _pb2   # noqa: E402
BO_NAP.update(_pb2.bo_nap(_c))
# Tệp thứ ba (10/9/2026) – quyết toán tour chi tiết theo tệp MỘT chuyến, bốn sheet. Bộ nạp riêng chứ
# không mở rộng 'quyet_toan_tour': tệp tháng và tệp một chuyến khác nhau về hình dạng, gộp lại thì bộ
# đọc phải đoán đang cầm loại nào – và đoán sai một lần là nạp tổng tháng vào chỗ của một chuyến.
from app.services import intake_phong_ban_3 as _pb3   # noqa: E402
BO_NAP.update(_pb3.bo_nap(_c))
# Tệp thứ tư (11/9/2026) – KHO QUYẾT TOÁN CŨ, 604 tệp Excel TỰ DO tháng 1–6/2026. Bộ nạp riêng chứ
# không mở rộng 'quyet_toan_tour_chi_tiet': tệp mẫu chuẩn có sheet tên cố định và nhãn cột cố định,
# kho cũ thì đo được 108 bộ sheet khác nhau. Một bộ đọc phải đoán đang cầm loại nào là một bộ đọc sẽ
# đoán sai. Xem đầu app/services/intake_kho_cu.py.
from app.services import intake_kho_cu as _kho   # noqa: E402
BO_NAP.update(_kho.bo_nap(_c))

# CỬA TẠO CHUYẾN – chạy TRƯỚC cửa trên. Đo 13/9/2026: 389/436 mã của kho cũ không có chuyến
# tương ứng trong VTOS, mà cửa nạp quyết toán chặn cứng đúng ở đấy. Tách riêng vì tạo chuyến là
# ghi lại lịch sử vận hành, không phải hệ quả phụ của việc đọc tệp.
from app.services import intake_tao_chuyen as _taoc   # noqa: E402
BO_NAP.update(_taoc.bo_nap(_c))

# CỬA THỨ SÁU (13/9/2026) – BẢN ĐỐI CHIẾU H1. Chạy SAU hai cửa trên. Hai cửa ấy cố ý không ghi tiền
# mức chuyến vì bộ đọc Excel chỉ rút được 90,7% doanh thu và 71,1% giá vốn; bản đối chiếu Kế toán đã
# chốt (624 chuyến, khớp MISA) là chỗ duy nhất có số đúng ở mức ấy.
from app.services import intake_doi_chieu_h1 as _dch1   # noqa: E402
BO_NAP.update(_dch1.bo_nap(_c))

# CỬA THỨ BẢY (16/9/2026) – BẢNG THÁNG DỊCH VỤ LẺ. 49 tệp mà cửa tạo chuyến cố ý để ra ngoài vì
# chúng KHÔNG phải một chuyến: visa lẻ, land lẻ, vé, combo bán theo tháng. Đúng là không phải một
# chuyến – nhưng đo ngày 16/9 trên đúng 49 tệp ấy: 672 dòng khách, thu 10,29 tỷ, chi 8,01 tỷ. Ngần
# ấy tiền đứng ngoài hệ vì thiếu một cái cửa, không vì thiếu số liệu. Bộ nạp riêng: mỗi tệp thành
# MỘT SỔ DỊCH VỤ LẺ CỦA MỘT THÁNG (non_package, mã DVL-…), không thành một chuyến ma.
from app.services import intake_bang_thang as _bth   # noqa: E402
BO_NAP.update(_bth.bo_nap(_c))

# CỬA THỨ TÁM (14/9/2026, đẩy 18/9/2026) – MARKETING. Hai cửa: khách tiềm năng, và số lead + chi
# phí theo kênh. Cửa thứ hai CỐ Ý tách khỏi cửa thứ nhất: số Marketing khai tay và số đếm được từ
# dữ liệu thô là HAI NGUỒN khác nhau, và việc đối chiếu chúng chính là nhóm "Đối soát dữ liệu".
# Gộp hai cửa làm một là xoá mất chính việc ấy.
from app.services import intake_marketing as _mkt   # noqa: E402
BO_NAP.update(_mkt.bo_nap(_c))

# CỬA THỨ CHÍN (18/9/2026) – TÀI SẢN THƯƠNG HIỆU. Ghi vào ĐÚNG bảng `fixed_assets` của Kế toán,
# theo chốt của Chủ tịch cùng ngày: dùng chung, không dựng bảng riêng cho Marketing. Cửa này cố ý
# KHÔNG mở ô nguyên giá – nguyên giá là thứ quyết định thẻ có vào sổ Kế toán hay không, và người
# khai nó phải là Kế toán ở màn hình Tài sản. Xem services/tai_san_thuong_hieu.
from app.services import intake_thuong_hieu as _th   # noqa: E402
BO_NAP.update(_th.bo_nap(_c))

# CỬA THỨ MƯỜI (18/9/2026) – HOẠT ĐỘNG PR. Sổ ghi việc truyền thông ĐÃ XẢY RA và ai chịu trách
# nhiệm. Khác với màn hình Nội dung (`content_items`), chỗ giữ BẢN THẢO trước khi đăng: một bảng
# không trả lời được hai câu hỏi ngược chiều nhau. Cửa này cố ý không mở ba ô – mốc đếm hạn hai
# giờ, người phát ngôn, và trạng thái 'đã phát' – xem services/intake_pr.
from app.services import intake_pr as _pr   # noqa: E402
BO_NAP.update(_pr.bo_nap(_c))

# CUA THU MUOI MOT (23/10/2026) -- SO DU DAU KY. Tam cua: mot cua chot theo tai khoan,
# va bay so phu theo doi tuong. Bo nap rieng chu khong noi vao tep tren: tam cua nay dung
# CHUNG mot nha may dung cot, va viet tay tam lan la tam cho de hai cua noi hai dieu khac
# nhau ve cung mot con so.
from app.services import intake_so_du_dau_ky as _sddk   # noqa: E402
BO_NAP.update(_sddk.bo_nap(_c))


# Ai được nạp loại dữ liệu nào. Phân quyền đặt Ở ĐÂY chứ không đặt ở màn hình: mở được trang nạp dữ liệu
# không có nghĩa là nạp được mọi thứ. Kinh doanh nạp danh sách khách của mình, HCNS nạp hồ sơ nhân sự và
# chấm công, Kế toán nạp sao kê – không ai nạp chéo sang sổ của phòng khác chỉ vì cùng thấy một cái nút.
QUAN_TRI = ("chutich", "tgd", "cntt")
VAI_TRO = {
    "nha_cung_cap":     QUAN_TRI + ("tp_dh", "nv_dh", "ketoan"),
    "don_dich_vu":      QUAN_TRI + ("tp_dh", "nv_dh", "ketoan"),
    "chuyen_xe":        QUAN_TRI + ("gd_doi_xe", "tp_dh", "nv_dh", "ketoan"),
    "nhan_su":          QUAN_TRI + ("hcns",),
    "cham_cong":        QUAN_TRI + ("hcns",),
    "khach_hang":       QUAN_TRI + ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "ptgd_mkt"),
    "booking":          QUAN_TRI + ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "tp_dh", "nv_dh", "ptgd_doan"),
    "sao_ke_ngan_hang": QUAN_TRI + ("ketoan",),
    "huong_dan_vien":   QUAN_TRI + ("tp_hd", "hcns", "tp_dh"),
    "quyet_toan_tour":  QUAN_TRI + ("tp_dh", "nv_dh", "ketoan", "ptgd_doan"),
}
VAI_TRO.update(_pb2.vai_tro(QUAN_TRI))
VAI_TRO.update(_pb3.vai_tro(QUAN_TRI))
VAI_TRO.update(_kho.vai_tro(QUAN_TRI))
VAI_TRO.update(_taoc.vai_tro(QUAN_TRI))
VAI_TRO.update(_dch1.vai_tro(QUAN_TRI))
VAI_TRO.update(_bth.vai_tro(QUAN_TRI))
VAI_TRO.update(_mkt.vai_tro(QUAN_TRI))
VAI_TRO.update(_th.vai_tro(QUAN_TRI))
VAI_TRO.update(_pr.vai_tro(QUAN_TRI))
VAI_TRO.update(_sddk.vai_tro(QUAN_TRI))


# P4 (08/9/2026) – TÁCH QUYỀN THEO TỪNG CỬA, không phải theo màn hình.
#
# Nhập tay sai một dòng thì sửa một dòng. Tải tệp sai một lần là cả tệp vào bảng cùng lúc – và với
# quyết định "nhập là dùng luôn" của Chủ tịch thì số đó dùng ngay, không ai duyệt lại. Hai việc khác
# hẳn nhau về hậu quả nên phải khác nhau về quyền.
#
# Nhưng KHÔNG siết tất cả. Bản đầu của quy tắc này bỏ nhân viên khỏi mọi cửa tải tệp, và ba phép thử
# sẵn có lập tức đỏ: nhân viên kinh doanh nạp danh sách khách và booking của chính mình là việc thường
# ngày, chặn đi thì họ nhờ người khác nạp hộ – và nhật ký ghi sai tên người chịu trách nhiệm, đúng cái
# mà cả thiết kế này đang cố tránh.
#
# Tiêu chí đúng không phải CẤP BẬC mà là DỮ LIỆU ĐI ĐÂU. Lý do siết là "500 dòng vào sổ cùng lúc và
# dùng ngay", nên nó chỉ áp cho những bộ nạp mà dòng dữ liệu chạm thẳng vào tiền: chi phí nhà cung cấp,
# chi phí chuyến xe, quyết toán, sao kê, chấm công (đầu vào của bảng lương). Danh mục khách hàng, danh
# mục nhà cung cấp, danh sách hướng dẫn viên thì không.
BO_NAP_CHAM_TIEN = ("doi_chieu_h1_2026",
                    "don_dich_vu", "chuyen_xe", "quyet_toan_tour", "sao_ke_ngan_hang", "cham_cong"
                    ) + _pb2.CHAM_TIEN + _pb3.CHAM_TIEN + _kho.CHAM_TIEN + _sddk.CHAM_TIEN
NHAN_VIEN = ("nv_dh", "nv_kd", "tn_kd", "nv_mkt", "nv_visa", "tai_xe", "hdv", "hanh_chinh")
# Suy ra từ VAI_TRO chứ không khai tay lần thứ hai: hai bảng khai tay thì sớm muộn cũng lệch, và lúc
# lệch thì không ai biết bảng nào đúng.
VAI_TRO_NAP_TEP = {k: (tuple(v for v in vs if v not in NHAN_VIEN) if k in BO_NAP_CHAM_TIEN else vs)
                   for k, vs in VAI_TRO.items()}


def duoc_nap(loai: str, vai_tro: str) -> bool:
    """Cửa 1 – nhập tay từng dòng (và cửa 3 – xác nhận số đọc từ ảnh, vì nó đổ về đúng cửa 1)."""
    return vai_tro in VAI_TRO.get(loai, QUAN_TRI)


def duoc_nap_tep(loai: str, vai_tro: str) -> bool:
    """Cửa 2 – tải tệp hàng loạt. Hẹp hơn cửa 1 đúng một bậc: nhân viên nhập tay được, nạp tệp thì không."""
    return vai_tro in VAI_TRO_NAP_TEP.get(loai, QUAN_TRI)


# P5 (08/9/2026) – CNTT vận hành mô hình đọc ảnh nhưng KHÔNG xác nhận số nó đọc ra.
# Xác nhận là hành vi nhập liệu: người bấm chịu trách nhiệm về con số, y như người gõ tay. Người vận
# hành mô hình mà cũng là người xác nhận kết quả của nó thì không còn ai đứng ngoài để nói mô hình đọc
# sai. Đây là lý do duy nhất, và nó đủ.
KHONG_XAC_NHAN_ANH = ("cntt",)


def duoc_xac_nhan_anh(loai: str, vai_tro: str) -> bool:
    """Cửa 3 – bấm xác nhận số máy đọc từ ảnh. Phải là người của phòng SỞ HỮU con số."""
    return duoc_nap(loai, vai_tro) and vai_tro not in KHONG_XAC_NHAN_ANH


# Bộ nạp thuộc phòng ban nào – để màn hình xếp theo phòng và để mỗi phòng thấy phần của mình trước.
PHONG_BAN = {"nha_cung_cap": "dieu_hanh", "don_dich_vu": "dieu_hanh", "chuyen_xe": "doi_xe",
             "nhan_su": "hcns", "cham_cong": "hcns", "khach_hang": "kd_le", "booking": "kd_le",
             "sao_ke_ngan_hang": "ketoan", "huong_dan_vien": "huong_dan",
             "quyet_toan_tour": "dieu_hanh",
             "nhien_lieu": "doi_xe", "phi_cau_duong": "doi_xe", "bao_duong": "doi_xe",
             "dang_kiem": "doi_xe", "chi_phi_ky_doi_xe": "doi_xe", "bang_lai_xe": "doi_xe",
             "chi_marketing_kenh": "marketing", "doanh_so_tu_van_vien": "kd_le",
             "thu_lao_hdv": "huong_dan", "hoa_don_dau_vao": "ketoan",
             "bao_hiem_ky": "hcns", "bang_luong": "hcns", "hop_dong_lao_dong": "hcns",
             "tai_san_co_dinh": "ketoan", "cong_cu_dung_cu": "ketoan", "khau_hao_ky": "ketoan"}
PHONG_BAN.update(_pb3.PHONG_BAN)
PHONG_BAN.update(_sddk.PHONG_BAN)


def danh_sach_bo_nap() -> list[dict]:
    return [{"ma": k, "ten": v["ten"], "mo_ta": v["mo_ta"], "khoa_chong_trung": v["khoa_chong_trung"],
             "phong_ban": v.get("phong_ban") or PHONG_BAN.get(k, ""),
             "bang_dich": v.get("bang_dich", ""),
             "vai_tro": list(VAI_TRO.get(k, QUAN_TRI)),
             "vai_tro_nap_tep": list(VAI_TRO_NAP_TEP.get(k, QUAN_TRI)),
             # Bộ nạp nào có MẪU RIÊNG thì nói ra ở đây, để màn hình dựng nút tải đúng mẫu ấy thay
             # cho nút "tải CSV mẫu" chung. Xem giải thích ở mau_csv() ngay dưới.
             "mau_rieng": list(v.get("mau_rieng", ())),
             "cot": v["cot"]} for k, v in BO_NAP.items()]


def mau_csv(loai: str) -> str:
    """Tệp mẫu: hàng đầu là TÊN CỘT, hàng thứ hai là một dòng ví dụ để người nhập biết định dạng.

    KHÔNG PHẢI BỘ NẠP NÀO CŨNG PHẲNG THÀNH CSV ĐƯỢC

    Bộ nạp 'mau_quyet_toan_tour' nhận một tệp MƯỜI SHEET do chính VTOS phát ra. Khai báo "cot" của nó
    chỉ là bảng mô tả cho màn hình xem, không phải hình dạng thật của tệp. Dựng CSV từ bảng ấy thì ra
    một tệp tám cột phẳng – nhân viên tải về, điền vào, nạp lên, và bị từ chối ở dòng đầu vì tệp
    không có sheet THÔNG TIN. Lỗi nằm ở cái nút họ bấm, không nằm ở việc họ làm.

    Nên chỗ này TỪ CHỐI và chỉ sang mẫu thật, thay vì phát ra một tệp không dùng được.
    """
    bo = BO_NAP[loai]
    if bo.get("mau_rieng"):
        ds = " | ".join(f"{m['ten']}: {m['duong_dan']}" for m in bo["mau_rieng"])
        raise ValueError(
            f"'{bo['ten']}' không dùng CSV mẫu – tệp của bộ nạp này là mẫu Excel nhiều sheet do VTOS "
            f"phát ra. Tải mẫu đúng ở: {ds}")
    tieu_de = [c["ten"] for c in bo["cot"]]
    vi_du = [c["vi_du"] for c in bo["cot"]]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(tieu_de); w.writerow(vi_du)
    return out.getvalue()


def _theo_key(bo: dict, rows: list[dict]) -> list[dict]:
    """Đổi tên cột tiếng Việt trong tệp thành khóa kỹ thuật.

    Tên cột được chuẩn hóa trước khi tra: "Tên nhà cung cấp", "tên nhà cung cấp " và "TEN" phải về cùng một
    cột. Bắt người nhập gõ đúng từng chữ hoa chữ thường là cách chắc chắn nhất để họ nạp nhầm cột.
    Cột lạ giữ lại (ở dạng đã chuẩn hóa) để báo cho người nạp chứ không im lặng bỏ."""
    anh_xa = {_chuan_cot(c["ten"]): c["key"] for c in bo["cot"]}
    anh_xa.update({_chuan_cot(c["key"]): c["key"] for c in bo["cot"]})
    out = []
    for r in rows:
        d = {}
        for k, v in r.items():
            ck = _chuan_cot(k)
            d[anh_xa.get(ck, ck)] = v
        out.append(d)
    return out


def kiem_tra(db: Session, loai: str, rows: list[dict]) -> dict:
    if loai in BO_NAP and BO_NAP[loai].get("lo"):
        bo = BO_NAP[loai]
        return {**bo["kiem_lo"](db, rows), "loai": loai, "ten": bo["ten"], "cot_khong_dung": [],
                "ghi_chu": "Đây là bước XEM TRƯỚC – chưa ghi gì vào hệ thống."}
    return _kiem_tra_tung_dong(db, loai, rows)


def _kiem_tra_tung_dong(db: Session, loai: str, rows: list[dict]) -> dict:
    """Kiểm tra toàn bộ, KHÔNG ghi gì. Trả về lỗi theo từng dòng kèm số dòng trong tệp."""
    if loai not in BO_NAP: raise ValueError(f"Không có bộ nạp '{loai}'")
    bo = BO_NAP[loai]
    biet = {c["key"] for c in bo["cot"]}
    rows = _theo_key(bo, rows)
    cot_la = sorted({k for r in rows for k in r if k not in biet})
    ket = []
    for i, r in enumerate(rows, start=2):        # hàng 1 là tiêu đề
        loi, cb, trung = [], [], None
        # Lớp kiểm DÙNG CHUNG cho ba cửa (app/services/nhap_lieu.py). Bắt buộc, kiểu, khoảng hợp lệ,
        # danh sách chọn và KỲ KHÓA đều kiểm ở đây; hàm kiem riêng của từng bộ nạp chỉ lo phần nghiệp vụ.
        from app.services.nhap_lieu import kiem_dong
        l0, c0 = kiem_dong(db, bo, r)
        loi += l0; cb += c0
        if not loi:
            try:
                l2, c2, trung = bo["kiem"](db, r)
                loi += l2; cb += c2
            except Exception as ex:                       # lỗi ngoài dự kiến vẫn phải hiện ra đúng dòng
                loi.append(f"Không đọc được dòng: {ex}")
        ket.append({"dong": i, "loi": loi, "canh_bao": cb, "da_co": trung,
                    "tom_tat": " · ".join(str(r.get(c["key"]) or "") for c in bo["cot"][:3] if r.get(c["key"]))})
    return {"loai": loai, "ten": bo["ten"], "so_dong": len(ket),
            "hop_le": sum(1 for k in ket if not k["loi"] and not k["da_co"]),
            "da_co": sum(1 for k in ket if k["da_co"]),
            "dong_loi": sum(1 for k in ket if k["loi"]),
            "cot_khong_dung": cot_la, "dong": ket,
            "ghi_chu": ("Đây là bước XEM TRƯỚC – chưa ghi gì vào hệ thống. Có dòng lỗi thì mặc định không "
                        "nạp gì cả; muốn nạp phần hợp lệ phải chọn rõ 'bỏ qua dòng lỗi'.")}


def nhap_mot_dong(db: Session, loai: str, row: dict, boi: str, cua: str = "nhap_tay",
                  tac_nhan: str = "") -> dict:
    """CỬA 1 – nhập tay một bản ghi. Đi qua ĐÚNG bộ kiểm của cửa tải tệp, không có đường tắt.

    Cũng là chỗ cửa 3 (ảnh do AI đọc) đổ về sau khi người bấm xác nhận: số từ ảnh không có đường riêng
    vào bảng, nó chỉ điền sẵn vào biểu này. Ai bấm xác nhận là người chịu trách nhiệm về con số, y như
    người gõ tay – nên nhật ký ghi cửa nào, và nếu là ảnh thì ghi cả tên tác vụ đã đọc."""
    kq = nap(db, loai, [row], boi, bo_qua_dong_loi=False, ten_tep="", nguon=cua, tac_nhan=tac_nhan)
    if kq["da_nap"] == 0:
        d = kq["dong"][0] if kq.get("dong") else {}
        return {"da_ghi": False, "loi": d.get("loi", []), "canh_bao": d.get("canh_bao", []),
                "da_co": d.get("da_co"),
                "message": (f"Đã có trong hệ thống ({d.get('da_co')}) – không ghi thêm bản thứ hai."
                            if d.get("da_co") else "Chưa ghi được: " + " · ".join(d.get("loi", [])))}
    return {"da_ghi": True, "ket_qua": kq.get("ket_qua", [{}])[0].get("ket_qua", ""),
            "canh_bao": kq["dong"][0].get("canh_bao", []), "run_id": kq.get("run_id"),
            "message": "Đã ghi vào hệ thống."}


def nap(db: Session, loai: str, rows: list[dict], boi: str, bo_qua_dong_loi: bool = False,
        ten_tep: str = "", nguon: str = "nguoi_nhap", tac_nhan: str = "") -> dict:
    """Nạp thật. Luôn kiểm tra lại trước khi ghi – không tin vào kết quả xem trước gửi kèm."""
    if loai in BO_NAP and BO_NAP[loai].get("lo"):
        bo = BO_NAP[loai]
        kq = bo["nap_lo"](db, rows, boi, ten_tep, bo_qua_dong_loi)
        noi_dung = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
        # Bộ nạp theo lô tự lo phần ghi nên KHÔNG trả về kết quả từng dòng. Ghi tổng tiền của TỆP –
        # cái biết chắc – và để TRỐNG ba ô còn lại thay vì điền 0. Trống nghĩa là "không đo được"; 0
        # nghĩa là "đo được và bằng không", và K5 phải phân biệt hai thứ đó, nếu không nó báo thiếu
        # tiền ở mọi lô chạy qua đường này.
        _ct, _cr = cot_tien_cua_bo(loai)
        run = IntakeRun(loai=loai, ten_tep=ten_tep[:200],
                        nguon=nguon if nguon in NGUON else "nap_tep", tac_nhan=(tac_nhan or boi)[:80],
                        so_dong=kq["so_dong"], da_nap=kq["da_nap"], bo_qua_da_co=kq["da_co"],
                        dong_loi=kq["dong_loi"], bo_qua_dong_loi=bo_qua_dong_loi,
                        tong_tien_tep=round(sum(_tong_tien_dong(r, _ct) for r in rows), 2),
                        cot_tien=_ct,
                        dau_vao_hash=hashlib.sha256(noi_dung.encode("utf-8")).hexdigest(),
                        ket_qua=json.dumps({"da_nap": kq["da_nap"]}, ensure_ascii=False), boi=boi)
        db.add(run); db.flush()
        return {**kq, "loai": loai, "ten": bo["ten"], "run_id": run.id}
    kt = kiem_tra(db, loai, rows)
    if kt["dong_loi"] and not bo_qua_dong_loi:
        return {**kt, "da_nap": 0,
                "message": f"Có {kt['dong_loi']} dòng lỗi nên KHÔNG nạp gì cả. Sửa tệp rồi nạp lại, "
                           "hoặc chọn 'bỏ qua dòng lỗi' để nạp phần hợp lệ."}
    bo = BO_NAP[loai]
    theo_key = _theo_key(bo, rows)
    da_nap, ket = 0, []
    for k in kt["dong"]:
        if k["loi"] or k["da_co"]: continue
        r = theo_key[k["dong"] - 2]
        try:
            ket.append({"dong": k["dong"], "ket_qua": bo["nap"](db, r, boi)})
            da_nap += 1
        except Exception as ex:
            k["loi"].append(f"Ghi không thành công: {ex}")
    noi_dung = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
    # K5 – bốn con số TIỀN soi gương bốn con số DÒNG. Phân bổ SAU vòng ghi, vì dòng ghi hỏng chỉ được
    # đánh dấu lỗi ở trong vòng đó; phân bổ trước thì tiền của nó nằm nhầm ô "đã nạp".
    ct, _chua_ro = cot_tien_cua_bo(loai)
    t_nap = t_bo = t_loi = 0.0
    for k in kt["dong"]:
        r = theo_key[k["dong"] - 2] if 0 <= k["dong"] - 2 < len(theo_key) else {}
        v = _tong_tien_dong(r, ct)
        if k["loi"]: t_loi += v
        elif k["da_co"]: t_bo += v
        else: t_nap += v
    run = IntakeRun(loai=loai, ten_tep=ten_tep[:200], nguon=nguon if nguon in NGUON else "nguoi_nhap",
                    tac_nhan=(tac_nhan or boi)[:80], so_dong=kt["so_dong"], da_nap=da_nap,
                    bo_qua_da_co=kt["da_co"], dong_loi=sum(1 for x in kt["dong"] if x["loi"]),
                    bo_qua_dong_loi=bo_qua_dong_loi,
                    tong_tien_tep=round(sum(_tong_tien_dong(r, ct) for r in theo_key), 2),
                    tong_tien_da_nap=round(t_nap, 2), tong_tien_bo_qua=round(t_bo, 2),
                    tong_tien_loi=round(t_loi, 2), cot_tien=ct,
                    dau_vao_hash=hashlib.sha256(noi_dung.encode("utf-8")).hexdigest(),
                    ket_qua=json.dumps(ket[:200], ensure_ascii=False), boi=boi)
    db.add(run); db.flush()
    return {**kt, "da_nap": da_nap, "run_id": run.id, "ket_qua": ket[:200],
            "message": (f"Đã nạp {da_nap} dòng. Bỏ qua {kt['da_co']} dòng đã có, "
                        f"{sum(1 for x in kt['dong'] if x['loi'])} dòng lỗi.")}
