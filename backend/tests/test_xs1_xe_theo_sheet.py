# -*- coding: utf-8 -*-
"""XS-1 · «Xe đang đi» đọc từ sheet quyết toán của Đội xe — Chủ tịch duyệt bản xem thử 25/10/2026.

Bảng mẫu dưới đây chép ĐÚNG KHUÔN của sheet thật (bản tải về 25/10/2026): dòng ghi chú màu trên
cùng, nhãn cột có xuống dòng trong ô, biển số rút gọn ở dòng khối, số gõ lẫn «600.000» / «30000» /
«(200.000)» / «30,39» / «#DIV/0!», dòng chỉ có CTP mà không tên tour, ô Tổng chi cộng nhầm cả doanh
thu, ô Lợi nhuận bằng doanh thu, km đầu không nối km cuối chuyến trước. Số tiền là số giả.
"""
import datetime as dt
import re
from pathlib import Path

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from app.services import xe_theo_sheet as XS

GOC = Path(__file__).resolve().parents[2]
HOM_NAY = dt.date(2026, 10, 25)

DAU = (',,,,Màu vàng: chi phí hoàn cho lái xe,,,,,,\n'
       'XE SỐ,SỐ,Lái xe,Tên tour,Ngày đi,Ngày về,Số ngày,CTP,"Gửi xe +\nphí khác",Dầu,EPASS,D. Thu,'
       'Tổng Chi,Lợi nhuận,Km đầu,Km cuối,Tổng km ,SL lít,"Tiêu Hao\n100km",NOTE\n')
MAU = DAU + (
    'XE 1,01783,Tú\n'
    ',50F01783,TÚ,Dalat,20/10/2026,22/10/2026,3,  600.000 ,  30.000 ,  5.000.000 ,  700.000 ,'
    '  10.000.000 ,  6.330.000 ,  3.670.000 ,  1.000 ,  1.600 ,  600 ,  180 ,  30 ,\n'
    ',,,Tây Ninh ,25/10/2026,25/10/2026,1,  200.000 ,,,,4.500.000,  200.000 ,  4.300.000 ,1600,,,,#DIV/0!\n'
    ',,,,,,1,  200.000 ,,,,,  200.000 ,,,,  -   \n'
    'XE 2,02259,HỒ ,,,,,,,,,,  -   \n'
    ',50F02259,HỒ ,Tây Nguyên,22/10/2026,25/10/2026,4,  800.000 ,,,,  23.000.000 ,  23.800.000 ,'
    '  23.000.000 ,,,0,,#DIV/0!\n'
    'XE 3,49829,TRƯỜNG\n'
    ',49829,TRƯỜNG ,Nha trang ,29/9/2026,1/10/2026,3,  600.000 ,  70.000 ,  7.000.000 ,  1.000.000 ,'
    '  15.000.000 ,  8.670.000 ,  6.330.000 ,  5.000 ,  5.900 ,  900 ,  254 ,"28,1"\n'
    ',,,Phan Thiết ,05/10/2026,07/10/2026,3,  600.000 ,25000,3995240,858986,9000000,  5.479.226 ,'
    '  3.520.774 ,5590,6039,449,128,"28,5"\n'
    'XE 9,99999,KHÔNG CÓ TRONG VTOS\n'
    ',99999,X,Vũng Tàu,24/10/2026,26/10/2026,3,  600.000 ,,,,9000000,  600.000 ,  8.400.000 \n'
)
XE_VTOS = {XS.nam_so_cuoi(p): p for p in ("50F01783", "50F02259", "50H49829", "50H94458")}


def test_so_doc_dung_cach_go_viet():
    assert XS.so("  6.375.630 ") == 6375630
    assert XS.so("30000") == 30000
    assert XS.so("(200.000)") == -200000
    assert XS.so("-78697") == -78697
    assert XS.so('30,39772727') == 30.39772727
    # rỗng / gạch / lỗi công thức là CHƯA BIẾT, không phải 0
    for v in ("", "  -   ", "#DIV/0!", None, "abc"):
        assert XS.so(v) is None, v


def test_ngay_va_bien_so():
    assert XS.ngay("4/10/2026") == XS.ngay("04/10/2026") == dt.date(2026, 10, 4)
    assert XS.ngay("31/9/2026") is None
    assert XS.nam_so_cuoi("50H 94458") == XS.nam_so_cuoi("94458") == "94458"
    assert XS.nam_so_cuoi("04622") == "04622"


def test_doc_bang_khoi_bien_va_dong_khong_tour():
    b = XS.doc_bang(MAU)
    assert b["loi"] is None
    assert [k["khoi"] for k in b["khoi"]] == ["XE 1", "XE 2", "XE 3", "XE 9"]
    assert b["khoi"][0]["bien"] == "50F01783", "giữ bản biển có nhiều chữ số hơn"
    assert len(b["chuyen"]) == 6
    khong_tour = [c for c in b["can_sua"] if c["loai"] == "dong_khong_tour"]
    assert len(khong_tour) == 1 and khong_tour[0]["khoi"] == "XE 1"


def test_tin_dong_khong_tin_tong():
    b = XS.doc_bang(MAU)
    t = next(x for x in b["chuyen"] if x["khoi"] == "XE 2")
    assert t["chi"] == 800000, "Tổng chi phải cộng lại từ CTP + gửi xe + dầu + epass"
    assert t["lai"] == 22200000
    loai = {(c["khoi"], c["loai"]) for c in b["can_sua"]}
    assert ("XE 2", "tong_chi") in loai, "ô Tổng chi cộng nhầm doanh thu phải bị báo"
    assert ("XE 2", "loi_nhuan") in loai, "ô Lợi nhuận bằng doanh thu phải bị báo"
    # chuyến đúng thì không báo
    assert not [c for c in b["can_sua"] if c["khoi"] == "XE 1" and c["loai"] in ("tong_chi", "loi_nhuan")]


def test_km_noi_theo_nguong():
    b = XS.doc_bang(MAU)
    km = [c for c in b["can_sua"] if c["loai"] == "km_noi"]
    assert len(km) == 1 and km[0]["khoi"] == "XE 3", km   # 5.900 → 5.590, lệch 310 km
    assert not [c for c in XS.doc_bang(MAU, nguong_km_noi=400)["can_sua"] if c["loai"] == "km_noi"]


def test_do_cot_theo_nhan_khong_theo_chu_cai():
    """Đội xe chèn thêm một cột ở giữa: mọi số vẫn phải về đúng chỗ."""
    import csv
    import io
    rows = list(csv.reader(io.StringIO(MAU)))
    for r in rows[1:]:
        r.insert(2, "Cột mới" if r is rows[1] else "")
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    a, b = XS.doc_bang(MAU), XS.doc_bang(buf.getvalue())
    assert [(t["tour"], t["chi"], t["lai"]) for t in a["chuyen"]] == \
           [(t["tour"], t["chi"], t["lai"]) for t in b["chuyen"]]


def test_thieu_cot_bat_buoc_thi_noi_ra():
    b = XS.doc_bang(MAU.replace("Ngày về", "Về"))
    assert b["loi"] and "ve" in b["loi"] and b["chuyen"] == []


def test_hom_nay_dem_xe_khong_dem_chuyen():
    b = XS.doc_bang(MAU)
    h = XS.hom_nay(b, HOM_NAY, XE_VTOS)
    # XE 1 (Tây Ninh 25/10), XE 2 (22–25/10) khớp VTOS; XE 9 đang đi nhưng không có trong VTOS
    assert h["dang_di"] == 2 and h["khong_khop"] == 1, h
    tt = {d["khoi"]: d["trang_thai"] for d in h["danh_sach"]}
    assert tt == {"XE 1": "Đi trong ngày", "XE 2": "Về hôm nay", "XE 9": "Đang trên đường"}
    assert [n["khoi"] for n in h["nam_bai"]] == ["XE 3"]
    assert next(d for d in h["danh_sach"] if d["khoi"] == "XE 2")["bien"] == "50F02259"


def test_chong_ngay():
    mau = MAU + ',,,Đà Lạt,24/10/2026,27/10/2026,4,  800.000 ,,,,10000000,  800.000 ,  9.200.000 \n'
    b = XS.doc_bang(mau)
    assert [c["khoi"] for c in b["can_sua"] if c["loai"] == "chong_ngay"] == ["XE 9"]
    assert XS.hom_nay(b, HOM_NAY, XE_VTOS)["khong_khop"] == 1, "hai chuyến chồng ngày vẫn là MỘT xe"


# ── nối CSDL + link ─────────────────────────────────────────────────────────────────────────────

def _db(link=""):
    import app.models.core        # noqa: F401
    import app.models.fleet       # noqa: F401
    from app.models.core import Param
    from app.models.hr import Vehicle
    from app.services import rules as R
    e = create_engine("sqlite://")
    Vehicle.__table__.create(e)
    Param.__table__.create(e)
    db = sessionmaker(bind=e)()
    db.execute(insert(Vehicle.__table__), [
        dict(plate=p, active=True, lifecycle="dang_khai_thac", op_right="so_huu") for p in XE_VTOS.values()]
        + [dict(plate="50H00002", active=True, lifecycle="da_ban", op_right="so_huu")])
    if link:
        db.add(Param(key=XS.KHOA_LINK, value=link, label="x", effective_from=dt.date(2026, 1, 1),
                     status="active"))
    db.commit()
    R.clear_param_cache()
    return db


LINK = "https://docs.google.com/spreadsheets/d/e/2PACX-abc/pub?gid=0&single=true&output=csv"


def test_chua_dan_link():
    assert XS.bao_cao(_db(), HOM_NAY)["co_link"] is False
    assert XS.tom_tat(_db(), HOM_NAY) is None


def test_link_la_khong_tai():
    """Máy chủ không tải một địa chỉ tuỳ ý do người dán vào tham số chữ."""
    goi = []
    r = XS.bao_cao(_db("http://10.0.0.1/noi-bo"), HOM_NAY, tai=lambda u: goi.append(u) or MAU)
    assert r["loi"] and not goi


def test_bao_cao_va_tom_tat():
    XS._DEM.clear()
    r = XS.bao_cao(_db(LINK), HOM_NAY, doc_lai=True, tai=lambda u: MAU)
    assert r["loi"] is None
    assert (r["dieu_duoc"], r["dang_di"], r["o_bai"], r["khong_khop"]) == (4, 2, 2, 1), r
    t = XS.tom_tat(_db(LINK), HOM_NAY)   # lần hai: lấy từ đệm, không tải lại
    assert t["dang_di"] == 2 and t["so_can_sua"] == len(r["can_sua"]) and t["loi"] is None


def test_tai_hong_thi_giu_ban_cu_va_noi_ra():
    XS._DEM.clear()
    XS.doc(LINK, tai=lambda u: MAU)
    def hong(u):
        raise OSError("HTTP 404")
    d = XS.doc(LINK, doc_lai=True, tai=hong)
    assert d["noi_dung"] == MAU and d["ban_cu"] is True and "404" in d["loi_tai"]
    XS._DEM.clear()
    assert XS.doc(LINK, tai=hong)["noi_dung"] is None


# ── nối vào hệ ──────────────────────────────────────────────────────────────────────────────────

def test_lenh_thay_sheet_tren_bang_dieu_hanh():
    src = (GOC / "backend/app/services/dashboard.py").read_text(encoding="utf-8")
    m = re.search(r'sec\["xe_theo_sheet"\] = None\s*\n\s*if not sec\["xe_hom_nay"\]\.get\("co_lenh"\):'
                  r'(.*?)XS\.tom_tat', src, re.S)
    assert m, "bảng điều hành chỉ đọc sheet khi CHƯA có lệnh điều xe nào (Chủ tịch 25/10/2026)"


def test_tham_so_cua_link_va_man_con():
    from app.services import access as AC
    from app.services import rules as R
    assert [p for p in R.DEFAULT_PARAMS if p[0] == XS.KHOA_LINK][0][1] == "", "mặc định trống = chưa nối"
    assert "/doi-xe/xe-hom-nay" in AC.MAN_CON_DOI_XE
    trang = (GOC / "web/app/doi-xe/xe-hom-nay/page.tsx").read_text(encoding="utf-8")
    assert "/fleet/xe-theo-sheet" in trang
    assert not re.search(r'method:\s*"(POST|PUT|DELETE|PATCH)"', trang), "màn này chỉ đọc"
    assert '"/doi-xe/xe-hom-nay"' in (GOC / "web/app/doi-xe/page.tsx").read_text(encoding="utf-8")
