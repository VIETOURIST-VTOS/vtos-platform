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
    # XS-2: dòng CTP 200.000 không tên tour là công tác phí THẬT (Chủ tịch 25/10) — thiếu ngày thì báo.
    thieu = [c for c in b["can_sua"] if c["loai"] == "ctp_thieu_ngay"]
    assert len(thieu) == 1 and thieu[0]["khoi"] == "XE 1" and "200.000" in thieu[0]["noi_dung"]


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
    # XS-1b: đúng MỘT cửa ghi — trình link chờ ký. Không cửa nào ghi vào sheet hay vào chuyến.
    assert re.findall(r'api<any>\("([^"]+)",\s*\{\s*method:\s*"(?:POST|PUT|DELETE|PATCH)"', trang) == \
        ["/fleet/xe-theo-sheet/link"]
    assert '"/doi-xe/xe-hom-nay"' in (GOC / "web/app/doi-xe/page.tsx").read_text(encoding="utf-8")


# ── XS-1b · cửa dán link ở màn Đội xe, giữ chữ ký Chủ tịch (25/10/2026) ───────────────────────────

def test_link_mo_sheet_bi_bao_dung_cho_sai():
    """Đo thật 25/10: Chủ tịch dán link /edit — phải được bảo đúng là link mở sheet, và cách lấy link CSV."""
    loi = XS.nhan_xet_link("https://docs.google.com/spreadsheets/d/1jaD/edit?gid=0#gid=0")
    assert loi and "Công bố lên web" in loi and "output=csv" in loi
    assert XS.nhan_xet_link(LINK) is None
    assert XS.nhan_xet_link("https://evil.example/x?output=csv")


def test_doc_thu_khong_dung_dem():
    XS._DEM.clear()
    r = XS.doc_thu(LINK, tai=lambda u: MAU)
    assert r == {"ok": True, "so_xe": 4, "so_chuyen": 6, "so_can_sua": len(XS.doc_bang(MAU)["can_sua"])}
    assert XS._DEM == {}, "link chưa ký không được lọt vào đệm mà robot dùng"
    def hong(u):
        raise OSError("HTTP 404")
    assert XS.doc_thu(LINK, tai=hong)["ok"] is False


class _U:
    def __init__(self, username, role):
        self.username, self.role = username, role


def _db_trinh():
    db = _db()
    from app.models.core import Param
    # dòng gieo của tham số, như seed_params tạo trên hệ thật
    db.add(Param(key=XS.KHOA_LINK, value="", label="Link CSV", unit="link",
                 effective_from=dt.date(2026, 9, 1), status="active"))
    db.commit()
    return db


def test_trinh_link_lap_ban_cho_ky_khong_ghi_thang(monkeypatch):
    from app.api.v1 import fleet as F
    from app.services import rules as R
    monkeypatch.setattr(R, "audit", lambda *a, **k: None)
    monkeypatch.setattr(XS, "_tai", lambda u: MAU)
    monkeypatch.setattr(XS.doc_thu, "__defaults__", (50, lambda u: MAU))
    db = _db_trinh()
    r = F.dan_link_sheet(F.LinkSheetVao(url=LINK), _U("nguyenhonghuan", "gd_doi_xe"), db)
    assert r["da_trinh"] is True
    assert XS.link(db) == "", "chưa ký thì robot vẫn chưa có link"
    ck = XS.cho_ky(db)
    assert ck and ck["boi"] == "nguyenhonghuan" and ck["link"] == LINK


def test_link_doc_khong_duoc_thi_khong_trinh(monkeypatch):
    from app.api.v1 import fleet as F
    db = _db_trinh()
    r = F.dan_link_sheet(F.LinkSheetVao(url="https://docs.google.com/spreadsheets/d/1/edit"),
                         _U("nguyenhonghuan", "gd_doi_xe"), db)
    assert r["da_trinh"] is False and "Công bố lên web" in r["doc_thu"]["loi"]
    assert XS.cho_ky(db) is None


def test_chu_tich_khong_nam_trong_vai_dan_link():
    """Chủ tịch là người ký duy nhất của tham số; người trình không tự ký."""
    from app.api.v1 import fleet as F
    assert "chutich" not in F.GHI_LINK_SHEET and "gd_doi_xe" in F.GHI_LINK_SHEET


def test_o_chu_tich_doc_sheet_khi_chua_co_lenh():
    """XS-1c: ô «Xe đang đi» trên màn Chủ tịch hiện số theo sheet khi chưa có lệnh, và nói ra nguồn."""
    trang = (GOC / "web/app/page.tsx").read_text(encoding="utf-8")
    assert "sheet={sec.xe_theo_sheet}" in trang
    khoi = (GOC / "web/components/KhoiV14.tsx").read_text(encoding="utf-8")
    m = re.search(r"\{xeCoNguon && chuaLapLenh && sheet && !sheet\.loi \? \((.*?)\) : xeCoNguon && chuaLapLenh \?",
                  khoi, re.S)
    assert m, "nhánh sheet phải đứng TRƯỚC nhánh «chờ Đội xe», và chỉ khi chưa có lệnh"
    # XS-3 (bản gọn): nguồn và giờ đọc chuyển vào màn chi tiết; ô giữ con số, số dòng cần sửa và lối vào.
    assert "dòng sửa" in m.group(1) and "/doi-xe/xe-hom-nay" in m.group(1)


def test_nam_o_van_hanh_bang_nhau_va_co_nut_xem_chi_tiet():
    """XS-3 (Chủ tịch duyệt bản xem thử 25/10/2026): mỗi ô một dòng phụ ngắn + «Xem chi tiết» ở đáy."""
    khoi = (GOC / "web/components/KhoiV14.tsx").read_text(encoding="utf-8")
    i, j = khoi.index("── TẦNG VẬN HÀNH ──"), khoi.index("── DIỄN BIẾN ──")
    tang = khoi[i:j]
    assert tang.count("style={O_VH}") >= 3 and "style={XEM}" in tang
    # mỗi nhánh hiển thị của ô công suất và ô xe đang đi đều có nút; ba ô vanHanh dùng chung một nút
    assert tang.count(">Xem chi tiết →</Link>") >= 7
    assert 'marginTop: "auto"' in khoi, "nút phải bị đẩy xuống đáy để năm ô thẳng hàng"


# ── XS-2 · công tác phí tài xế ngoài chuyến (Chủ tịch 25/10/2026: «là chi phí công tác phí của tài xế thật») ──

def test_nhan_ra_dong_truc_cho_tour_khong_nham_cho_noi():
    for t in ("Trực", "trực bãi", "Chờ tour", "Chờ", "chờ khách"):
        assert XS.LA_NGOAI_CHUYEN.match(XS._khong_dau(t)), t
    for t in ("Chợ nổi Cái Răng", "Chơn Thành", "Dalat", "Trường Sơn"):
        assert not XS.LA_NGOAI_CHUYEN.match(XS._khong_dau(t)), t


MAU_CTP = DAU + (
    'XE 1,01783,Tú\n'
    ',50F01783,TÚ,Dalat,20/10/2026,22/10/2026,3,  600.000 ,,,,  10.000.000 ,,,,,,,,\n'
    ',,,Trực,25/10/2026,25/10/2026,1,  200.000 ,,,,,  200.000 ,,,,,,,\n'
    ',,,,12/10/2026,,1,  200.000 ,,,,,  200.000 ,,,,,,,\n'
    ',,,,,,1,  200.000 ,,,,,  200.000 ,,,,,,,\n'
)


def test_dong_truc_co_ngay_la_ctp_khong_phai_chuyen():
    b = XS.doc_bang(MAU_CTP)
    assert [t["tour"] for t in b["chuyen"]] == ["Dalat"], "ngày trực không được thành một chuyến"
    assert [(c["ngay"].isoformat(), c["so_tien"]) for c in b["ctp_ngoai"]] == \
        [("2026-10-25", 200000), ("2026-10-12", 200000)]
    assert [c["loai"] for c in b["can_sua"]].count("ctp_thieu_ngay") == 1
    h = XS.hom_nay(b, HOM_NAY, XE_VTOS)
    assert h["dang_di"] == 0, "xe trực ở bãi ngày 25/10 không phải xe đang đi"


def _db_ctp(da_nhap):
    db = _db()
    from app.models.fleet import FleetPeriodCost
    from app.models.hr import Vehicle
    FleetPeriodCost.__table__.create(db.get_bind())
    vid = db.execute(__import__("sqlalchemy").select(Vehicle.id).where(Vehicle.plate == "50F01783")).scalar()
    for i, st in enumerate(da_nhap):
        db.add(FleetPeriodCost(ky="2026-10", pham_vi="xe", vehicle_id=vid, nhom=XS.NHOM_CTP_NGOAI,
                               mo_ta=f"truc {i}", so_tien=st))
    db.commit()
    return db


def test_doi_chieu_ctp_ngoai_bao_phan_thieu():
    b = XS.doc_bang(MAU_CTP)
    ra = XS.doi_chieu_ctp_ngoai(_db_ctp([200000]), b)
    assert len(ra) == 1 and ra[0]["loai"] == "ctp_chua_vao_vtos"
    assert "sheet 400.000" in ra[0]["noi_dung"] and "Nhập 200.000" in ra[0]["noi_dung"]
    assert XS.doi_chieu_ctp_ngoai(_db_ctp([200000, 200000]), b) == [], "nhập đủ thì thôi báo"


def test_nhom_ctp_ngoai_chuyen_la_chi_phi_cua_xe():
    from app.models.fleet import NHOM_CHI_PHI_KY, NGOAI_GIA_VON
    assert NHOM_CHI_PHI_KY[XS.NHOM_CTP_NGOAI][1] == "xe"
    assert XS.NHOM_CTP_NGOAI not in NGOAI_GIA_VON, "công tác phí là giá vốn vận tải, phải trừ vào lợi nhuận"
