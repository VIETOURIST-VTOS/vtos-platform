# -*- coding: utf-8 -*-
"""Cửa nạp hai mẫu quyết toán tour chuẩn – nhân viên Điều hành tự tải tệp đã điền lên.

Đọc đúng hai tệp do VTOS phát ra:

    MAU_QT_TOUR_TRONG_NUOC.xlsx   8 sheet
    MAU_QT_TOUR_NUOC_NGOAI.xlsx   9 sheet (thêm CHI THEO KHÁCH)

DÒ CỘT THEO NHÃN, KHÔNG THEO CHỮ CÁI

Hai mẫu khác nhau về số cột: mẫu nước ngoài có bốn cột ngoại tệ mà mẫu trong nước không có, nên cột
"DỰ CHI" của mẫu này là L còn của mẫu kia là H. Viết cứng chữ cái cột là gài sẵn một lần đọc nhầm cả
bảng – và đọc nhầm sang cột bên cạnh thì số vẫn là số, bảng vẫn cân, không ai thấy.

MÁY CỘNG LẠI, KHÔNG ĐỌC Ô TỔNG CỦA TỆP

Bộ đọc này BỎ QUA mọi ô công thức trong tệp và tự cộng lại từ các dòng. Lý do đo được: trên tệp mẫu
thật của Điều hành, ô tổng nhóm "B. TRẺ EM" ghi 3.990.000 trong khi năm dòng của chính nhóm ấy cộng
lại được 4.200.000 – thiếu 210.000 đ, và con số sai ấy đi thẳng vào giá vốn rồi vào lợi nhuận mà mọi
tầng vẫn cân.

Tệp gửi lên có thể đã bị gõ đè lên ô công thức, hoặc mở bằng một phần mềm không tính lại công thức
(lúc ấy ô công thức đọc ra rỗng). Cả hai trường hợp đều dẫn tới cùng một kết luận: TIN DÒNG, KHÔNG
TIN TỔNG.

CHÍN PHÉP KIỂM CHẠY LẠI Ở MÁY CHỦ

Tệp có sẵn chín phép kiểm bằng công thức, nhưng đó là phép kiểm của NGƯỜI LẬP TỜ – nó giúp họ sửa
trước khi gửi. Phép kiểm của HỆ THỐNG phải chạy lại ở đây, vì một tệp gửi lên là một tệp đã ra khỏi
tầm kiểm soát: ô công thức xoá được, sheet ĐỐI CHIẾU xoá được.
"""
from datetime import date, datetime
from io import BytesIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Mã khoản mục lấy từ danh mục dùng chung – không chép lại danh sách ở đây.
from app.services import khoan_muc_chi as KM

SHEET = {"tt": "THÔNG TIN", "khach": "KHÁCH", "thu": "THU", "chi": "CHI",
         "chi_khach": "CHI THEO KHÁCH", "pt": "PHƯƠNG TIỆN", "hdv": "HDV"}


# ---------------------------------------------------------------------------------------------
# Đọc
# ---------------------------------------------------------------------------------------------

def _so(v):
    """Số tiền. Rỗng vào thì RỖNG ra – không suy thành 0 (quy ước K2)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace(" ", "").replace("đ", "")
    try:
        return float(s)
    except ValueError:
        return None


def _chu(v) -> str:
    return "" if v is None else " ".join(str(v).split())


def _ngay(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(_chu(v), f).date()
        except (ValueError, TypeError):
            continue
    return None


def _cot(ws, hang_tieu_de: int) -> dict:
    """{nhãn cột: chỉ số cột}. Đây là chỗ thay cho việc viết cứng chữ cái cột."""
    ra = {}
    for c in range(1, ws.max_column + 1):
        n = _chu(ws.cell(hang_tieu_de, c).value)
        if n:
            ra[n] = c
    return ra


DUNG_LAI = ("CỘNG", "VÍ DỤ", "TỔNG CỘNG")


def _la_dong_dung(ws, r: int, het_cot: int) -> bool:
    """Dòng này có phải VẠCH KẾT THÚC của bảng không – dò CẢ DÒNG, không chỉ một cột.

    Bản đầu chỉ nhìn chữ "CỘNG" ở đúng CỘT BẮT BUỘC. Trên mẫu thật, chữ "CỘNG" nằm ở cột 1 của sheet
    KHÁCH và cột 3 của sheet CHI, trong khi cột bắt buộc là "Họ và tên" (cột 3) và "Nội dung" (cột
    4). Tức là vạch kết thúc không bao giờ được nhận ra, và bộ đọc đi thẳng qua dòng tổng xuống phần
    bên dưới – nơi mẫu để một dòng VÍ DỤ. Đo được: tải mẫu trống lên khi chưa điền gì, hệ thống ghi
    một hành khách tên NGUYEN VAN A với giá bán 1.790.000 đ.

    Không dòng dữ liệu thật nào mang những chữ này, nên dò cả dòng là an toàn.
    """
    for c in range(1, het_cot + 1):
        t = _chu(ws.cell(r, c).value).upper()
        if t and any(t.startswith(k) for k in DUNG_LAI):
            return True
    return False


def _bang(ws, hang_tieu_de: int, cot_bat_buoc: str) -> list[dict]:
    """Mọi dòng có dữ liệu ở cột bắt buộc, đọc theo nhãn. Dừng ở vạch CỘNG / VÍ DỤ."""
    m = _cot(ws, hang_tieu_de)
    if cot_bat_buoc not in m:
        return []
    het_cot = max(m.values())
    ra = []
    for r in range(hang_tieu_de + 1, ws.max_row + 1):
        if _la_dong_dung(ws, r, het_cot):
            break
        v = ws.cell(r, m[cot_bat_buoc]).value
        if v in (None, ""):
            continue
        ra.append({"_hang": r, **{n: ws.cell(r, c).value for n, c in m.items()}})
    return ra


def doc_tep(noi_dung: bytes, ten_tep: str = "") -> dict:
    """Đọc một tệp mẫu đã điền. KHÔNG kiểm, KHÔNG ghi – chỉ đọc."""
    import openpyxl
    wb = openpyxl.load_workbook(BytesIO(noi_dung), data_only=True)
    thieu = [t for t in ("THÔNG TIN", "KHÁCH", "THU", "CHI") if t not in wb.sheetnames]
    if thieu:
        raise ValueError(f"Tệp thiếu sheet {', '.join(thieu)} – đây không phải mẫu quyết toán của "
                         f"VTOS. Tải mẫu trống ở màn hình Nạp dữ liệu rồi điền vào đó.")

    ws = wb["THÔNG TIN"]
    dau = {}
    for r in range(1, ws.max_row + 1):
        nhan = _chu(ws.cell(r, 1).value)
        if nhan:
            dau[nhan] = ws.cell(r, 2).value

    d = {
        "ten_tep": ten_tep,
        "ma_tour": _chu(dau.get("Mã tour")),
        "ten_tour": _chu(dau.get("Tên tour")),
        "hinh_thuc": _chu(dau.get("Hình thức")),
        "so_khach_dau_bang": _so(dau.get("Số khách")),
        "ngay_kh": _ngay(dau.get("Ngày khởi hành")),
        "ngay_kt": _ngay(dau.get("Ngày kết thúc")),
        "dieu_hanh": _chu(dau.get("Điều hành")),
        "sale": _chu(dau.get("Sale phụ trách")),
        "hdv": _chu(dau.get("Hướng dẫn viên / TL")),
        "khach": _bang(wb["KHÁCH"], 2, "Họ và tên"),
        "thu": _bang(wb["THU"], 2, "Nội dung"),
        "chi": _bang(wb["CHI"], 2, "Nội dung"),
        "phuong_tien": _bang(wb["PHƯƠNG TIỆN"], 2, "Loại") if "PHƯƠNG TIỆN" in wb.sheetnames else [],
        "hdv_chi": _bang(wb["HDV"], 3, "Nội dung") if "HDV" in wb.sheetnames else [],
        "chi_khach": (_bang(wb["CHI THEO KHÁCH"], 3, "Loại chi phí")
                      if "CHI THEO KHÁCH" in wb.sheetnames else []),
    }
    # Hình thức suy từ chính bộ sheet khi ô đầu bảng để trống – tệp nào có CHI THEO KHÁCH là mẫu
    # nước ngoài. Suy được thì suy, nhưng vẫn nói ra ở phần kiểm rằng ô ấy trống.
    if d["hinh_thuc"] not in ("trong_nuoc", "nuoc_ngoai"):
        d["hinh_thuc_suy_ra"] = "nuoc_ngoai" if "CHI THEO KHÁCH" in wb.sheetnames else "trong_nuoc"
    return d


def doc_tep_lo(noi_dung: bytes, ten_tep: str = "") -> list[dict]:
    """Khung nạp chung gọi hàm này. Một tệp = một chuyến = một phần tử."""
    d = doc_tep(noi_dung, ten_tep)
    # Tổng thu để phẳng ở gốc cho nhật ký nạp ghi được tổng tiền của tệp – MÁY CỘNG, không đọc ô tổng.
    d["doanh_thu"] = _tong_thu(d) or None
    d["so_khach"] = len(d["khach"])
    return [d]


# ---------------------------------------------------------------------------------------------
# Cộng lại – luôn từ dòng, không bao giờ từ ô tổng của tệp
# ---------------------------------------------------------------------------------------------

def _thanh_tien_thu(x: dict) -> float | None:
    dg, sl = _so(x.get("Đơn giá trước thuế")), _so(x.get("Số lượng"))
    if dg is None or sl is None:
        return None
    truoc = round(dg * sl, 2)
    ts = _so(x.get("Thuế suất"))
    return truoc if ts is None else round(truoc * (1 + ts), 2)


def _thuc_chi(x: dict) -> float | None:
    """Thực chi của một dòng chi. Ngoại tệ thì số gốc × tỷ giá; còn lại lấy ô thực chi hoặc dự chi."""
    te = _chu(x.get("Tiền tệ"))
    if te and te.upper() != "VND":
        goc, tg = _so(x.get("Số tiền gốc")), _so(x.get("Tỷ giá"))
        return None if (goc is None or tg is None) else round(goc * tg, 2)
    tc = _so(x.get("THỰC CHI (VND)"))
    return tc if tc is not None else _so(x.get("DỰ CHI (VND)"))


def _tong_thu(d: dict) -> float:
    return round(sum(v for v in (_thanh_tien_thu(x) for x in d["thu"]) if v is not None), 2)


def _tong_chi(d: dict) -> float:
    chung = sum(v for v in (_thuc_chi(x) for x in d["chi"]) if v is not None)
    khach = sum(v for v in (_so(x.get("Thành tiền (VND)")) for x in d["chi_khach"]) if v is not None)
    return round(chung + khach, 2)


# ---------------------------------------------------------------------------------------------
# Kiểm – chín phép, chạy lại ở máy chủ
# ---------------------------------------------------------------------------------------------

def _tim_tour(db: Session, ma: str):
    from app.models.core import Tour
    if not ma:
        return None
    return db.scalars(select(Tour).where(func.lower(Tour.code) == ma.lower())).first()


def _bang_booking(db: Session, tour_id: int) -> dict:
    """{mã booking: id} của MỘT chuyến – nhận nhiều cách gọi tên cùng một phiếu đặt.

    Trên tám tệp thật, cùng một phiếu đặt được gõ bằng ba kiểu: mã VTOS (BK-2026-0042), số Vietrip
    (115069, chính là cột 'BookingID' của sheet DT), và đôi khi cả số id trần. Bắt người lập tờ phải
    nhớ đúng một kiểu là bắt họ gõ sai; nhận cả ba và tra trong PHẠM VI MỘT CHUYẾN thì không có chỗ
    cho nhầm lẫn – hai chuyến khác nhau có trùng số cũng không sao vì đã lọc theo tour_id.

    Cố ý KHÔNG nhận 'Mã đặt chỗ' (PNR hãng bay, ví dụ KCLWRD) làm khoá: PNR là của chuyến bay, một
    PNR có thể chở khách của nhiều phiếu đặt, và nó nằm ở cột khác trên mẫu.
    """
    from app.models.core import Booking
    ra = {}
    for b in db.scalars(select(Booking).where(Booking.tour_id == tour_id).order_by(Booking.id)):
        for k in (b.code, b.vietrip_id, str(b.id)):
            k = _chu(k)
            if k:
                ra.setdefault(k, b.id)
    return ra


def kiem_mot(db: Session, d: dict) -> dict:
    """Chín phép kiểm. 'nang' = chặn nạp; còn lại là cảnh báo đi kèm.

    NẶNG là những phát hiện làm ĐỔI SỐ VÀO SỔ hoặc làm không xác định được chuyến. Lệch nhỏ về số
    khách thì xếp nhẹ: nó không đổi đồng nào, chỉ đổi giá vốn bình quân đầu khách, nên chặn nạp vì nó
    là làm phiền chứ không phải bảo vệ.
    """
    nang, nhe = [], []
    t = _tim_tour(db, d["ma_tour"])

    if not d["ma_tour"]:
        nang.append("Thiếu mã tour ở sheet THÔNG TIN – không biết tờ này thuộc chuyến nào")
    elif t is None:
        nang.append(f"Không có chuyến mã '{d['ma_tour']}' trong hệ thống. Quyết toán phải gắn vào "
                    f"chuyến đã có – tạo chuyến trước rồi nạp lại.")

    ht = d.get("hinh_thuc") or d.get("hinh_thuc_suy_ra")
    if d.get("hinh_thuc") not in ("trong_nuoc", "nuoc_ngoai"):
        nhe.append(f"Ô 'Hình thức' để trống – suy ra '{ht}' theo bộ sheet của tệp")
    if t is not None and t.hinh_thuc and ht and t.hinh_thuc != ht:
        nang.append(f"Tệp là mẫu '{ht}' nhưng chuyến {t.code} trong hệ thống là '{t.hinh_thuc}' – "
                    f"hai hình thức dùng hai tỷ lệ giá khác nhau, nạp nhầm là sai giá chuẩn")

    if not d["khach"]:
        nang.append("Sheet KHÁCH không có dòng nào – tờ quyết toán phải ghi hết người ngồi trên chuyến")
    sk = d["so_khach_dau_bang"]
    if sk is not None and len(d["khach"]) != int(sk):
        nhe.append(f"Số khách đầu bảng ghi {int(sk)} nhưng đếm được {len(d['khach'])} dòng khách")

    thieu_ns = [x for x in d["khach"] if _ngay(x.get("Ngày sinh")) is None]
    if thieu_ns:
        nhe.append(f"{len(thieu_ns)} khách chưa có ngày sinh – quy tắc giá theo tuổi không kiểm được")

    chua_gia = [x for x in d["khach"]
                if _chu(x.get("Nhóm khách")) == "tra_tien" and _so(x.get("Giá bán")) is None]
    if chua_gia:
        nang.append(f"{len(chua_gia)} khách trả tiền chưa có giá bán – ô trống nghĩa là CHƯA NHẬP, "
                    f"bỏ sót một khách là hụt nguyên một suất doanh thu")

    am_khong_can_cu = [x for x in d["thu"]
                       if (_thanh_tien_thu(x) or 0) < 0 and not _chu(x.get("Chứng từ (bắt buộc nếu ÂM)"))]
    if am_khong_can_cu:
        nang.append(f"{len(am_khong_can_cu)} dòng thu ÂM không ghi chứng từ – không phân biệt được "
                    f"hoàn tiền theo biên bản với gõ nhầm dấu trừ")

    chua_qt = [x for x in d["chi"] if not _chu(x.get("Quy tắc phân bổ"))]
    if chua_qt:
        nhe.append(f"{len(chua_qt)} dòng chi chưa khai quy tắc phân bổ – phần ấy không vào giá vốn "
                   f"của khách nào")

    ma_la = sorted({_chu(x.get("Mã khoản mục")) for x in d["chi"]
                    if _chu(x.get("Mã khoản mục")) and _chu(x.get("Mã khoản mục")) not in KM.KHOAN_MUC})
    if ma_la:
        nang.append(f"Mã khoản mục không có trong danh mục: {', '.join(ma_la[:5])}"
                    + (f" và {len(ma_la) - 5} mã nữa" if len(ma_la) > 5 else ""))

    thieu_tg = [x for x in d["chi"]
                if _chu(x.get("Tiền tệ")) and _chu(x.get("Tiền tệ")).upper() != "VND"
                and (_so(x.get("Tỷ giá")) is None or _ngay(x.get("Ngày tỷ giá")) is None)]
    if thieu_tg:
        nang.append(f"{len(thieu_tg)} khoản ngoại tệ thiếu tỷ giá hoặc NGÀY tỷ giá – không ghi ngày "
                    f"thì không bao giờ phân xử được số nào đúng")

    cho_duyet = [x for x in d["hdv_chi"] if _chu(x.get("Duyệt")) in ("", "cho_duyet")]
    if cho_duyet:
        nhe.append(f"{len(cho_duyet)} khoản HDV chi còn chờ duyệt – im lặng không được tính là đồng ý")

    # ---- Booking: khách nào thuộc phiếu đặt nào ----
    #
    # Bản đầu KHÔNG kiểm chỗ này và bộ nạp gán mọi dòng khách vào booking ĐẦU TIÊN của chuyến. Đo
    # trên tệp Nha Trang thật: 42 khách thuộc 9 booking của 10 sale khác nhau, tất cả bị dồn về một
    # booking. Doanh thu theo sale sai, 'đã đóng / còn lại' theo booking sai, hoa hồng sai – mà tổng
    # của chuyến vẫn đúng nên không ai nhìn ra.
    if t is not None:
        bk = _bang_booking(db, t.id)
        # ĐẾM THEO GIÁ TRỊ, KHÔNG THEO KHOÁ. Mỗi phiếu đặt có tới ba khoá tra (mã VTOS, số Vietrip,
        # số id), nên len(bk) là số CÁCH GỌI TÊN chứ không phải số phiếu. Đếm nhầm thì một chuyến có
        # đúng một phiếu đặt vẫn bị báo "có 2 phiếu đặt" và chặn nạp một tờ hoàn toàn hợp lệ.
        so_bk = len(set(bk.values()))
        if not bk:
            # Trước đây bộ nạp lặng lẽ bỏ qua từng dòng khách ở chỗ này (một câu `continue`), rồi
            # báo "nạp xong". Mất sạch dòng khách mà màn hình vẫn xanh là kiểu hỏng tệ nhất.
            nang.append(
                f"Chuyến {t.code} chưa có phiếu đặt (booking) nào trong hệ thống, trong khi tệp có "
                f"{len(d['khach'])} dòng khách. Dòng khách phải treo vào một phiếu đặt – nạp lúc này "
                f"thì {len(d['khach'])} dòng ấy không có chỗ nào để ghi.")
        else:
            la_kh = sorted({_chu(x.get("Mã booking")) for x in d["khach"]
                            if _chu(x.get("Mã booking")) and _chu(x.get("Mã booking")) not in bk})
            la_th = sorted({_chu(x.get("Mã booking")) for x in d["thu"]
                            if _chu(x.get("Mã booking")) and _chu(x.get("Mã booking")) not in bk})
            la = sorted(set(la_kh) | set(la_th))
            if la:
                nang.append(
                    f"Mã booking không có trong chuyến {t.code}: {', '.join(la[:5])}"
                    + (f" và {len(la) - 5} mã nữa" if len(la) > 5 else "")
                    + f". Chuyến này đang có {so_bk} phiếu đặt.")
            thieu = [x for x in d["khach"] if not _chu(x.get("Mã booking"))]
            if thieu and so_bk > 1:
                nang.append(
                    f"{len(thieu)} dòng khách để trống cột 'Mã booking', mà chuyến {t.code} có "
                    f"{so_bk} phiếu đặt. Máy KHÔNG đoán hộ: đoán sai thì doanh thu chạy sang sale "
                    f"khác và số 'đã đóng' của khách cũng sang theo.")
            elif thieu:
                nhe.append(f"{len(thieu)} dòng khách để trống 'Mã booking' – chuyến chỉ có một phiếu "
                           f"đặt nên máy gắn vào phiếu ấy")

    return {"nang": nang, "nhe": nhe, "tour_id": (t.id if t is not None else None),
            "hinh_thuc": ht,
            "tong_thu": _tong_thu(d), "tong_chi": _tong_chi(d),
            "so_khach": len(d["khach"]), "so_dong_chi": len(d["chi"])}


def kiem_lo(db: Session, rows: list[dict]) -> dict:
    """Xem trước. KHÔNG ghi gì."""
    ra, dong_loi = [], 0
    for d in rows:
        k = kiem_mot(db, d)
        dong_loi += 1 if k["nang"] else 0
        ra.append({"ma_tour": d["ma_tour"], "ten_tour": d["ten_tour"], **k})
    # ĐÚNG HỢP ĐỒNG CỦA KHUNG NẠP: so_dong / da_nap / da_co / dong_loi.
    #
    # intake.nap() ghi nhật ký lô bằng chính ba khoá ấy (IntakeRun(so_dong=kq["so_dong"], …)). Bản
    # đầu trả "tong_dong" cho cùng một thứ, nên đường TẢI TỆP LÊN nổ KeyError ngay trước lúc ghi
    # nhật ký – nghĩa là cửa ấy chưa bao giờ chạy thông, dù phép thử của riêng bộ nạp vẫn xanh vì nó
    # gọi thẳng nap_lo() chứ không đi qua khung.
    #
    # da_co = số tệp bỏ qua vì chuyến ĐÃ CÓ dữ liệu. Ở bộ nạp này luôn bằng 0: nạp lại là THAY chứ
    # không bỏ qua, nên không có tệp nào rơi vào nhóm ấy. Khai ra để khung đọc được, và khai 0 chứ
    # không bỏ trống – ở đây 0 là con số ĐÚNG, không phải "chưa đo được".
    return {
        "so_dong": len(rows), "da_co": 0,
        "tong_dong": len(rows), "dong_loi": dong_loi,
        "dong_tot": len(rows) - dong_loi,
        "chi_tiet": ra,
        "loi": [f"{x['ma_tour']}: {m}" for x in ra for m in x["nang"]],
        "canh_bao": [f"{x['ma_tour']}: {m}" for x in ra for m in x["nhe"]],
    }


# ---------------------------------------------------------------------------------------------
# Nạp
# ---------------------------------------------------------------------------------------------

def _nap_mot(db: Session, d: dict, k: dict, boi: str) -> dict:
    from app.models.core import Booking, Tour
    from app.models.lop3_tour import (BookingKhach, KhachChiPhi, TourDoanhThuDong, TourHdvChi,
                                      TourPhuongTien)
    from app.models.vietrip import TourCostLine
    from app.services import gia_khach as G

    t = db.get(Tour, k["tour_id"])
    if t.hinh_thuc is None:
        t.hinh_thuc = k["hinh_thuc"]

    # NẠP LẠI LÀ THAY, KHÔNG PHẢI CỘNG THÊM. Nạp cùng một tệp hai lần mà cộng dồn thì chuyến có hai
    # lần giá vốn, và bảng vẫn cân nên không ai thấy. Xoá theo tour rồi ghi lại là cách duy nhất giữ
    # được tính chất "nạp bao nhiêu lần cũng ra một kết quả".
    for M in (TourHdvChi, TourPhuongTien, TourDoanhThuDong):
        db.query(M).filter(M.tour_id == t.id).delete(synchronize_session=False)
    db.query(KhachChiPhi).filter(KhachChiPhi.tour_id == t.id).delete(synchronize_session=False)
    db.query(BookingKhach).filter(BookingKhach.tour_id == t.id).delete(synchronize_session=False)
    db.query(TourCostLine).filter(TourCostLine.tour_id == t.id,
                                  TourCostLine.source == "mau_qt").delete(synchronize_session=False)
    db.flush()

    # Bảng tra phiếu đặt của CHÍNH chuyến này. Khi chuyến chỉ có đúng một phiếu đặt thì dòng để
    # trống 'Mã booking' gắn vào phiếu ấy – không có chỗ nào để nhầm. Từ hai phiếu trở lên, dòng
    # trống đã bị kiem_mot() chặn ở bậc NẶNG trước khi tới đây.
    bk = _bang_booking(db, t.id)
    mac_dinh_bk = next(iter(bk.values())) if len(set(bk.values())) == 1 else None

    def _bid(x):
        """Phiếu đặt của một dòng. Không tra ra thì trả None – KHÔNG rơi về phiếu đầu tiên."""
        ma = _chu(x.get("Mã booking"))
        if ma:
            return bk.get(ma)
        return mac_dinh_bk

    # ---- khách ----
    gia_nl = None
    nl = [_so(x.get("Giá bán")) for x in d["khach"]
          if _chu(x.get("Nhóm khách")) == "tra_tien" and _so(x.get("Giá bán"))]
    if nl:
        gia_nl = max(set(nl), key=nl.count)

    theo_stt = {}
    for x in d["khach"]:
        kh = BookingKhach(
            booking_id=_bid(x), tour_id=t.id,
            stt=int(_so(x.get("STT")) or 0) or None, ho_ten=_chu(x.get("Họ và tên"))[:200],
            nhom_khach=_chu(x.get("Nhóm khách")) or None,
            ngay_sinh=_ngay(x.get("Ngày sinh")), gia_ban=_so(x.get("Giá bán")),
            ly_do_khac_chuan=_chu(x.get("Note"))[:200] or None,
            # Hai loại giấy tờ, hai cột. Bản đầu nhét CCCD vào ô hộ chiếu vì chưa có cột riêng.
            so_ho_chieu=_chu(x.get("Số hộ chiếu"))[:30] or None,
            cccd=_chu(x.get("CCCD"))[:20] or None,
            gioi_tinh=_chu(x.get("Giới tính"))[:10] or None,
            # Số điện thoại giữ dạng CHỮ: số 0 đứng đầu biến mất nếu đọc thành số, và một số điện
            # thoại mất số 0 đầu thì gọi không được.
            dien_thoai=_chu(x.get("Điện thoại"))[:20] or None,
            email=_chu(x.get("Email"))[:120] or None,
            ma_dat_cho=_chu(x.get("Mã đặt chỗ"))[:30] or None,
            nguoi_sua=boi, sua_luc=datetime.now())
        # KHÔNG còn câu `continue` im lặng ở đây. Bản đầu bỏ qua dòng khách không tra được phiếu
        # đặt rồi vẫn báo "nạp xong" – nhân viên nạp một tệp 42 khách và nhận về một chuyến rỗng mà
        # không có dòng nào nói vì sao. Nay kiem_mot() đã chặn ở bậc NẶNG từ trước; tới được đây mà
        # vẫn rỗng thì là lỗi lập trình, phải nổ chứ không được nuốt.
        if kh.booking_id is None:
            raise ValueError(
                f"Dòng khách '{kh.ho_ten}' không tra được phiếu đặt trong chuyến {t.code}. "
                f"Lẽ ra bộ kiểm phải chặn trước bước ghi – báo cho CNTT.")
        db.add(kh)
        G.xac_dinh_khach(db, kh, t.start_date, gia_nl, t.hinh_thuc)
        db.flush()
        if kh.stt:
            theo_stt[kh.stt] = kh.id

    # ---- doanh thu ----
    for x in d["thu"]:
        dg, sl = _so(x.get("Đơn giá trước thuế")), _so(x.get("Số lượng"))
        truoc = None if (dg is None or sl is None) else round(dg * sl, 2)
        ts = _so(x.get("Thuế suất"))
        thue = None if (truoc is None or ts is None) else round(truoc * ts, 2)
        db.add(TourDoanhThuDong(
            tour_id=t.id, booking_id=_bid(x),
            khach_id=theo_stt.get(int(_so(x.get("Khách (STT)")) or 0)),
            loai=_chu(x.get("Loại")) or None, noi_dung=_chu(x.get("Nội dung"))[:200] or None,
            doi_tuong=_chu(x.get("Đối tượng")) or None,
            don_gia_truoc_thue=dg, so_luong=sl, thanh_tien_truoc_thue=truoc,
            thue_suat=ts, tien_thue=thue,
            thanh_tien=(None if truoc is None else round(truoc + (thue or 0), 2)),
            chung_tu=_chu(x.get("Chứng từ (bắt buộc nếu ÂM)"))[:120] or None))

    # ---- chi ----
    for i, x in enumerate(d["chi"], start=1):
        ma = _chu(x.get("Mã khoản mục")) or None
        md = KM.mac_dinh(ma)
        thuc = _thuc_chi(x)
        ts = _so(x.get("Thuế suất"))
        db.add(TourCostLine(
            tour_id=t.id, line_no=i, ma_khoan_muc=ma,
            description=(_chu(x.get("Nội dung")) or (md.get("ten") if md else "") or "(không ghi)")[:200],
            ngay=_chu(x.get("Ngày"))[:60] or None,
            nhom=(_chu(x.get("Nhóm")) or md.get("nhom") or "")[:80] or None,
            doi_tuong=(_chu(x.get("Đối tượng")) or md.get("doi_tuong") or "") or None,
            quy_tac_phan_bo=(_chu(x.get("Quy tắc phân bổ")) or md.get("quy_tac_phan_bo") or "") or None,
            supplier_name=_chu(x.get("Đối tác"))[:200],
            supplier_tax_code=_chu(x.get("MST đối tác"))[:20],
            # Đơn giá × Số lượng × Hệ số. Tệp thật ghi "Ăn trưa ngày 1 – ĐỒNG TIẾN – 115.000 × 33
            # suất × 1 ngày"; giữ cả ba thì mới trả lời được câu Chủ tịch hỏi: "dự toán 40 suất
            # Tháp Bà, thực chi 44 suất" – lệch do GIÁ hay do SỐ LƯỢNG. Chỉ giữ ô tổng thì hai
            # nguyên nhân ấy trộn vào nhau và không tách ra được nữa.
            unit_price=_so(x.get("Đơn giá")),
            qty=_so(x.get("Số lượng")) or 0,
            coef=_so(x.get("Hệ số")) or 1,
            # ---- Thanh toán: trả bằng gì, thẻ nào, ngày nào, hạn nào ----
            # Land_UK và HotelList của tệp UK ghi đủ những thứ này ("Bank transfer", "Wise 9078",
            # Paid Date, Deadline). Không có chúng thì Kế toán không đối chiếu được với sao kê thẻ
            # và sao kê ngân hàng, và không ai biết khoản nào sắp quá hạn trả đối tác.
            hinh_thuc_tt=_chu(x.get("Hình thức TT"))[:20] or None,
            tai_khoan_the=_chu(x.get("Thẻ / tài khoản trả"))[:60] or None,
            ngay_thanh_toan=_ngay(x.get("Ngày thanh toán")),
            han_thanh_toan=_ngay(x.get("Hạn thanh toán")),
            loai_chung_tu=_chu(x.get("Loại chứng từ"))[:30] or None,
            budget=_so(x.get("DỰ CHI (VND)")), actual=thuc,
            tien_te=(_chu(x.get("Tiền tệ")) or None), so_tien_goc=_so(x.get("Số tiền gốc")),
            ty_gia=_so(x.get("Tỷ giá")), ngay_ty_gia=_ngay(x.get("Ngày tỷ giá")),
            thue_suat=ts,
            vat_hoa_don=(None if (thuc is None or ts is None) else round(thuc * ts, 2)),
            khong_hoa_don=_so(x.get("Phần KHÔNG hoá đơn")),
            so_hoa_don=_chu(x.get("Số hoá đơn"))[:30] or None,
            source="mau_qt", status="hd", updated_by=boi))

    # ---- chi theo khách (chỉ mẫu nước ngoài) ----
    for x in d["chi_khach"]:
        kid = theo_stt.get(int(_so(x.get("Khách (STT)")) or 0))
        if kid is None:
            continue
        db.add(KhachChiPhi(
            khach_id=kid, tour_id=t.id, loai=_chu(x.get("Loại chi phí")) or None,
            noi_dung=_chu(x.get("Nội dung"))[:200] or None,
            so_tien=_so(x.get("Thành tiền (VND)")), tien_te=_chu(x.get("Tiền tệ")) or None,
            so_tien_goc=_so(x.get("Số tiền gốc")), ty_gia=_so(x.get("Tỷ giá")),
            nha_cung_cap=_chu(x.get("Nhà cung cấp"))[:200] or None,
            mst_ncc=_chu(x.get("MST"))[:20] or None,
            so_hoa_don=_chu(x.get("Số hoá đơn"))[:30] or None))

    # ---- phương tiện ----
    for x in d["phuong_tien"]:
        db.add(TourPhuongTien(
            tour_id=t.id, loai=_chu(x.get("Loại"))[:20] or "khac",
            chang=_chu(x.get("Chặng"))[:120] or None, ngay=_ngay(x.get("Ngày")),
            so_hieu=_chu(x.get("Số hiệu / biển số"))[:40] or None,
            ma_dat_cho=_chu(x.get("Mã đặt chỗ"))[:30] or None,
            nha_cung_cap=_chu(x.get("Nhà cung cấp"))[:200] or None,
            mst_ncc=_chu(x.get("MST"))[:20] or None,
            xe_nha=1 if _chu(x.get("Xe nhà?")).lower() in ("x", "1", "có") else 0,
            so_cho=int(_so(x.get("Số chỗ")) or 0) or None,
            so_khach_su_dung=int(_so(x.get("Số khách dùng")) or 0) or None,
            thanh_tien=_so(x.get("Thành tiền (VND)")),
            ghi_chu=_chu(x.get("Ghi chú"))[:300] or None))

    # ---- HDV chi ----
    for x in d["hdv_chi"]:
        # THỰC CHI CỦA HDV: ô ấy là CÔNG THỨC trên mẫu, nên phải tự tính lại được từ mọi hướng.
        #
        # Tệp gửi lên có thể đã đi qua một phần mềm không tính lại công thức (Google Sheets xuất ra,
        # LibreOffice ở chế độ nhanh, hoặc chính openpyxl) – lúc ấy ô công thức đọc ra RỖNG. Bản đầu
        # chỉ lùi về "số gốc × tỷ giá", nên với tour trong nước (không có ngoại tệ) thì cả khoản HDV
        # mất sạch: không dòng nào báo, chỉ là tiền ứng và phần vượt đều ra rỗng.
        #
        # Đúng nguyên tắc TIN DÒNG, KHÔNG TIN TỔNG: dòng có đơn giá và số lượng thì nhân lại.
        thuc = _so(x.get("Thực chi (VND)"))
        if thuc is None:
            goc, tg = _so(x.get("Số gốc")), _so(x.get("Tỷ giá"))
            if goc is not None and tg is not None:
                thuc = round(goc * tg, 2)
        if thuc is None:
            dg, sl = _so(x.get("Đơn giá")), _so(x.get("Số lượng"))
            if dg is not None and sl is not None:
                thuc = round(dg * sl, 2)
        if thuc is None:
            thuc = _so(x.get("Số gốc"))          # nội tệ ghi thẳng một số tổng, không đơn giá
        ct = _so(x.get("Theo chiết tính"))
        ung = _so(x.get("Tiền ứng"))
        db.add(TourHdvChi(
            tour_id=t.id, noi_dung=_chu(x.get("Nội dung"))[:200] or None,
            don_gia=_so(x.get("Đơn giá")), so_luong=_so(x.get("Số lượng")),
            thanh_tien=thuc, tien_te=_chu(x.get("Tiền tệ")) or None,
            so_tien_goc=_so(x.get("Số gốc")), ty_gia=_so(x.get("Tỷ giá")),
            ngay_ty_gia=_ngay(x.get("Ngày tỷ giá")),
            thanh_tien_chiet_tinh=ct, tien_ung=ung,
            vuot=(None if (thuc is None or ct is None) else round(thuc - ct, 2)),
            # HAI PHÉP SO NGƯỢC CHIỀU NHAU, CẢ HAI ĐỀU XẢY RA THẬT
            #   vuot    = thực chi − chiết tính  -> HDV tiêu quá dự toán, không duyệt thì HDV bù
            #   con_lai = tiền ứng − thực chi    -> âm nghĩa là CÔNG TY còn nợ lại HDV
            # Mẫu đoàn Đà Lạt: ứng 3.300.000, chi 3.696.000 -> công ty nợ HDV 396.000. Bản đầu
            # không có cột Tiền ứng nên chỉ chạy được một chiều, và cái nửa thiếu ấy là nửa mà đi
            # đòi tiền nhầm người.
            con_lai=(None if (thuc is None or ung is None) else round(ung - thuc, 2)),
            loai_chung_tu=_chu(x.get("Chứng từ")) or None,
            thu_ho_khach=1 if _chu(x.get("Thu hộ khách?")).lower() in ("x", "1", "có") else 0,
            trang_thai_duyet=_chu(x.get("Duyệt")) or "cho_duyet",
            ly_do_duyet=_chu(x.get("Lý do duyệt / từ chối"))[:300] or None,
            nguoi_nhap=boi, nhap_luc=datetime.now()))

    db.flush()
    return {"ma_tour": t.code, "tour_id": t.id, "so_khach": len(theo_stt),
            "so_dong_chi": len(d["chi"]), "tong_thu": k["tong_thu"], "tong_chi": k["tong_chi"]}


def nap_lo(db: Session, rows: list[dict], boi: str, ten_tep: str = "",
           bo_qua_dong_loi: bool = False) -> dict:
    kt = kiem_lo(db, rows)
    if kt["dong_loi"] and not bo_qua_dong_loi:
        return {**kt, "da_nap": 0,
                "message": (f"Có {kt['dong_loi']} tệp mang phát hiện NẶNG nên KHÔNG nạp gì cả. "
                            f"Sửa rồi nạp lại, hoặc chọn bỏ qua để nạp kèm phát hiện.")}
    da = []
    for d in rows:
        k = kiem_mot(db, d)
        if k["nang"] and not bo_qua_dong_loi:
            continue
        if k["tour_id"] is None:
            continue        # không tra ra chuyến thì không có chỗ để ghi
        da.append(_nap_mot(db, d, k, boi))
    db.commit()
    return {**kt, "da_nap": len(da), "ket_qua": da,
            "message": f"Đã nạp {len(da)}/{len(rows)} tệp."}
