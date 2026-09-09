"""Bộ nạp quyết toán tour theo điều hành – V3 của lệnh giao việc 08/9/2026.

Tệp thật: mỗi điều hành viên một sheet, thêm sheet khách lẻ do sale tự xử lý, và một sheet Tổng hợp là
số cộng lại (không nạp – số cộng nạp vào là cộng hai lần).

Ba điều tệp nguồn làm mà bộ nạp này CỐ Ý không làm theo:

  1. Tệp ghi 0 vào ô giá vốn chưa có số. Ở đây 0 đọc thành RỖNG. Theo chỉ đạo 08/9, mọi đơn đều có giá
     vốn – "giá vốn 0" không phải bản chất nghiệp vụ mà là ô chưa ai điền. Giữ nguyên 0 là để sổ báo
     lãi 100% trên 2,65 tỷ doanh thu, và bảng vẫn cân nên không ai nhìn ra.

  2. Tệp trộn khách lẻ với tour trong cùng một cách đọc. Ở đây mã KLE xếp riêng: 60 trong 76 dòng thiếu
     giá vốn là khách lẻ – bảo lưu do hủy tour, gia hạn visa, vé. Trộn chung thì hàng đợi lúc nào cũng
     đầy những dòng không ai sửa được, và người ta thôi mở nó.

  3. Tệp không nói ai chịu trách nhiệm. Ở đây điều hành viên lấy theo TÊN SHEET và tra ra người thật;
     tra không ra thì ghi nguyên văn và đánh dấu chưa ánh xạ – tuyệt đối không điền tên người nạp tệp.
"""
import io
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User
from app.models.quyet_toan import TourSettlement, PHAN_LOAI

COT = {"mã tour": "ma_tour", "tên tour": "ten_tour", "ngày kh": "ngay_kh", "ngày kt": "ngay_kt",
       "doanh thu": "doanh_thu", "giá vốn": "gia_von", "trạng thái qt": "trang_thai_qt",
       "sale": "sale", "lợi nhuận": "loi_nhuan", "stt": "stt"}


def _chuan(s) -> str:
    return " ".join(str(s or "").strip().lower().split())


def _ngay(v):
    if v in (None, ""): return None
    if isinstance(v, datetime): return v.date()
    if isinstance(v, date): return v
    s = str(v).strip()[:10]
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try: return datetime.strptime(s, f).date()
        except ValueError: continue
    raise ValueError(f"Ngày không đọc được: {v!r}")


def doc_tep(noi_dung: bytes, ten_tep: str = "") -> list[dict]:
    """Đọc workbook nhiều sheet thành danh sách dòng. Sheet Tổng hợp bị bỏ – đó là số cộng lại."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(noi_dung), data_only=True, read_only=True)
    out = []
    for ws in wb.worksheets:
        ten_sheet = (ws.title or "").strip()
        if _chuan(ten_sheet).startswith("tổng hợp"): continue
        rows = list(ws.iter_rows(values_only=True))
        hdr = None
        for i, r in enumerate(rows[:8]):
            v = [_chuan(x) for x in r]
            if "mã tour" in v: hdr, cols = i, v; break
        if hdr is None:
            continue
        ix = {COT[c]: j for j, c in enumerate(cols) if c in COT}
        if "ma_tour" not in ix: continue
        la_kle_sheet = "khách lẻ" in _chuan(ten_sheet)
        for r in rows[hdr + 1:]:
            ma = r[ix["ma_tour"]] if ix["ma_tour"] < len(r) else None
            if ma is None or str(ma).strip() == "": continue
            d = {"_sheet": ten_sheet, "_khach_le_sheet": la_kle_sheet}
            for k, j in ix.items():
                if k in ("stt", "loi_nhuan"): continue
                d[k] = r[j] if j < len(r) else None
            out.append(d)
    return out


def _nguoi(db: Session, ten: str):
    """Tra điều hành viên theo tên. Không tra ra thì trả None – KHÔNG lấy người nạp tệp thay thế."""
    t = _chuan(ten)
    if not t: return None
    return db.execute(select(User).where(func.lower(User.full_name) == t)).scalars().first()


def kiem(db: Session, rows: list[dict]) -> dict:
    """Kiểm toàn bộ, không ghi gì. Trả về từng dòng kèm lỗi, cảnh báo và cách xếp loại dự kiến."""
    ket, ma_da_gap = [], {}
    for i, r in enumerate(rows, start=1):
        loi, cb = [], []
        ma = str(r.get("ma_tour") or "").strip()
        if not ma:
            loi.append("Thiếu mã tour")
        elif ma in ma_da_gap:
            loi.append(f"Mã {ma} xuất hiện hai lần trong tệp (dòng {ma_da_gap[ma]}) – "
                       "nạp cả hai là cộng đôi doanh thu")
        else:
            ma_da_gap[ma] = i
        try:
            kh, kt = _ngay(r.get("ngay_kh")), _ngay(r.get("ngay_kt"))
        except ValueError as ex:
            loi.append(str(ex)); kh = kt = None
        if kt is None: loi.append("Thiếu ngày kết thúc – không biết chuyến này thuộc kỳ nào")
        if kh and kt and kt < kh: loi.append("Ngày kết thúc trước ngày khởi hành")

        dt = float(r.get("doanh_thu") or 0)
        gv_tho = r.get("gia_von")
        # Ô 0 trong tệp nguồn đọc thành CHƯA CÓ SỐ, không phải "0 đồng".
        gv = None if gv_tho in (None, "", 0) else float(gv_tho)
        if dt < 0: loi.append("Doanh thu âm")
        if gv is not None and gv < 0: loi.append("Giá vốn âm")

        kle = ma.upper().startswith("KLE") or r.get("_khach_le_sheet")
        loai = "khach_le" if kle else "tour"
        dh = "" if kle else str(r.get("_sheet") or "").strip()
        sale = str(r.get("sale") or "").strip() or (str(r.get("_sheet") or "").strip() if kle else "")
        nguoi = _nguoi(db, dh) if dh else None
        if dh and nguoi is None:
            cb.append(f"Chưa tra ra người thật cho điều hành '{dh}' – ghi nguyên văn, chờ HCNS ánh xạ")

        if dt > 0 and gv is None:
            cb.append("Có doanh thu, chưa có giá vốn – " +
                      ("khách lẻ: chờ phân loại (bảo lưu do hủy tour / chưa nhập giá vốn / không phải "
                       "doanh thu)" if kle else "vào hàng đợi chờ Điều hành nhập giá vốn"))
        elif gv is not None and dt > 0 and (dt - gv) / dt > 0.60:
            cb.append(f"Biên {round((dt - gv) / dt * 100)}% – gần như chắc chắn thiếu dòng chi phí")
        elif gv is not None and gv > dt > 0:
            cb.append("Giá vốn lớn hơn doanh thu – chuyến này lỗ, kiểm lại trước khi chốt")

        da_co = db.execute(select(TourSettlement).where(TourSettlement.ma_tour == ma)).scalars().first() if ma else None
        ket.append({"dong": i, "sheet": r.get("_sheet"), "ma_tour": ma,
                    "ten_tour": str(r.get("ten_tour") or "")[:80], "loai": loai,
                    "dieu_hanh": dh, "sale": sale, "doanh_thu": dt, "gia_von": gv,
                    "ky": f"{kt:%Y-%m}" if kt else "", "loi": loi, "canh_bao": cb,
                    "da_co": ma if da_co is not None else None})
    return {
        "so_dong": len(ket),
        "hop_le": sum(1 for k in ket if not k["loi"] and not k["da_co"]),
        "da_co": sum(1 for k in ket if k["da_co"]),
        "dong_loi": sum(1 for k in ket if k["loi"]),
        "tong_doanh_thu": sum(k["doanh_thu"] for k in ket),
        "thieu_gia_von_tour": sum(1 for k in ket if k["doanh_thu"] > 0 and k["gia_von"] is None
                                  and k["loai"] == "tour"),
        "thieu_gia_von_khach_le": sum(1 for k in ket if k["doanh_thu"] > 0 and k["gia_von"] is None
                                      and k["loai"] == "khach_le"),
        "dong": ket,
        "ghi_chu": ("Ô giá vốn bằng 0 trong tệp được đọc là CHƯA CÓ SỐ, không phải 0 đồng. Sheet Tổng "
                    "hợp bị bỏ qua – đó là số cộng lại của các sheet khác."),
    }


def nap(db: Session, rows: list[dict], boi: str, ten_tep: str = "", bo_qua_dong_loi: bool = False) -> dict:
    kt = kiem(db, rows)
    if kt["dong_loi"] and not bo_qua_dong_loi:
        return {**kt, "da_nap": 0,
                "message": f"Có {kt['dong_loi']} dòng lỗi nên KHÔNG nạp gì cả. Sửa tệp rồi nạp lại, "
                           "hoặc chọn bỏ qua dòng lỗi để nạp phần hợp lệ."}
    da_nap = 0
    for k in kt["dong"]:
        if k["loi"] or k["da_co"]: continue
        r = rows[k["dong"] - 1]
        nguoi = _nguoi(db, k["dieu_hanh"]) if k["dieu_hanh"] else None
        tt = "da_qt" if "đã quyết toán" in _chuan(r.get("trang_thai_qt")) else "du_toan"
        s = TourSettlement(
            ky=k["ky"], ma_tour=k["ma_tour"], ten_tour=str(r.get("ten_tour") or "")[:300],
            loai=k["loai"], dieu_hanh=k["dieu_hanh"][:120], operator_id=nguoi.id if nguoi else None,
            sale=k["sale"][:120], ngay_kh=_ngay(r.get("ngay_kh")), ngay_kt=_ngay(r.get("ngay_kt")),
            doanh_thu=k["doanh_thu"], gia_von=k["gia_von"], trang_thai_qt=tt,
            # Máy KHÔNG tự đoán dòng nào là bảo lưu. Tour thiếu giá vốn vào hàng đợi; khách lẻ thiếu
            # giá vốn để TRỐNG phân loại và chờ người xếp – hai thứ đó không được lẫn vào nhau.
            phan_loai=("cho_gia_von" if (k["doanh_thu"] > 0 and k["gia_von"] is None
                                         and k["loai"] == "tour") else ""),
            ten_tep=ten_tep[:200], boi=boi)
        db.add(s); da_nap += 1
    db.flush()
    return {**kt, "da_nap": da_nap,
            "message": f"Đã nạp {da_nap} dòng. Bỏ qua {kt['da_co']} dòng đã có, "
                       f"{kt['dong_loi']} dòng lỗi."}


def phan_loai(db: Session, sid: int, ma: str, boi: str, ghi_chu: str = "", han_bao_luu=None) -> TourSettlement:
    """Người xếp loại một dòng có doanh thu mà chưa có giá vốn."""
    if ma not in PHAN_LOAI or not ma:
        raise ValueError(f"Phân loại '{ma}' không hợp lệ ({', '.join(k for k in PHAN_LOAI if k)})")
    s = db.get(TourSettlement, sid)
    if s is None: raise ValueError("Không có dòng quyết toán này")
    if ma == "bao_luu_huy_tour" and han_bao_luu is None:
        raise ValueError("Bảo lưu phải có HẠN. Không có hạn thì khoản này nằm lại mãi ở trạng thái chờ, "
                         "và tiền khách đã nộp không bao giờ được kết luận là doanh thu hay phải trả lại.")
    s.phan_loai, s.phan_loai_boi, s.phan_loai_luc = ma, boi, datetime.now()
    s.han_bao_luu = han_bao_luu
    if ghi_chu: s.ghi_chu = (s.ghi_chu + " | " + ghi_chu).strip(" |")[:2000]
    db.flush()
    return s


def tong_hop(db: Session, ky: str = "") -> dict:
    q = select(TourSettlement)
    if ky: q = q.where(TourSettlement.ky == ky)
    ds = list(db.execute(q).scalars())
    def _s(f): return sum((x.doanh_thu or 0) for x in ds if f(x))
    cho = [x for x in ds if x.doanh_thu > 0 and x.gia_von is None]
    return {
        "ky": ky, "so_don": len(ds),
        "doanh_thu": sum((x.doanh_thu or 0) for x in ds),
        "gia_von": sum(x.gia_von or 0 for x in ds),
        "so_don_du_so": len([x for x in ds if x.gia_von is not None]),
        "hang_doi_thieu_gia_von": {
            "so_don": len([x for x in cho if x.loai == "tour"]),
            "doanh_thu": _s(lambda x: x.doanh_thu > 0 and x.gia_von is None and x.loai == "tour")},
        "khach_le_cho_phan_loai": {
            "so_don": len([x for x in cho if x.loai == "khach_le" and not x.phan_loai]),
            "doanh_thu": _s(lambda x: x.doanh_thu > 0 and x.gia_von is None
                            and x.loai == "khach_le" and not x.phan_loai)},
        "chua_anh_xa_dieu_hanh": len([x for x in ds if x.dieu_hanh and x.operator_id is None]),
        "ghi_chu": ("Lợi nhuận chỉ cộng trên những đơn ĐÃ CÓ giá vốn. Đơn chưa có giá vốn không được "
                    "tính lãi bằng doanh thu."),
    }
