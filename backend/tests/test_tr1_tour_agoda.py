# -*- coding: utf-8 -*-
"""TR-1 · Tour kiểu Agoda trên kh.vietourist.vn/tours + nối nội dung web + đặt tour online + email invoice
(Chủ tịch duyệt bản xem thử 01/11/2026, nối web 02/11/2026).

  1. Đọc web: chỉ https://(www.)vietourist.com.vn; không theo chuyển hướng ra ngoài; HTML mẫu (VIẾT TAY theo cấu trúc
     trang tour — không phải nội dung thật) → ảnh tuyệt đối, lịch trình từng ngày, bảng giá, bao gồm / không bao gồm,
     quy định. Đọc hỏng thì giữ bản cũ.
  2. Gộp chuyến theo sản phẩm, giá từ, đủ chỗ; tìm theo tab / điểm đến / khoảng ngày / loại.
  3. Lịch trình: chuyến → web → «Ngày N» của sản phẩm → nguyên văn.
  4. Tiền: cọc làm tròn lên 1.000 đ; hạn trả phần còn lại; công tắc chung + sản phẩm (409).
  5. QR khớp số cọc → phiếu thu tự động + email kèm PDF; invoice chỉ chủ đơn tải được.
  6. Ma trận quản lý.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 11, 2, 9, 0)

# HTML mẫu VIẾT TAY theo đúng cấu trúc DOM trang tour thật trên vietourist.com.vn (Điều phối đo 02/11/2026) — chữ là
# chữ mẫu, không chép nội dung thật: .album-gallery (ảnh chính + .thumb-tour /thumbnail/), table.info-product, tab
# #tabs-detail / #tabs-more / #tabs-adv / #tabs-comment, băng chuyền tour liên quan .owl-item .item-product, chấm sao .kksr-*.
TRANG = """<html><head><meta property="og:title" content="Tour Du Lịch Hà Nội - Hà Giang 3 Ngày">
<meta property="og:image" content="/public/frontend/uploads/files/tour/thumbnail/ha-giang.jpg"></head><body>
<h1>Tour Du Lịch Hà Nội - Hà Giang 3 Ngày</h1>
<div class="album-gallery">
 <div class="main-img"><img src="/public/frontend/uploads/files/tour/ha-giang.jpg"></div>
 <div class="thumb-tour"><img src="/public/frontend/uploads/files/tour/thumbnail/ha-giang.jpg">
  <img src="/public/frontend/uploads/files/tour/thumbnail/dong-van.jpg"></div>
</div>
<div class="kk-star-ratings"><img class="kksr-star" src="/public/frontend/images/kksr-star.png"></div>
<table class="info-product">
 <tr><td>Khởi hành : thứ bảy, chủ nhật</td></tr>
 <tr><td>Thời gian</td><td>: 3 Ngày - 2 Đêm</td></tr>
 <tr><td>Phương tiện : Ô tô</td></tr>
 <tr><td>Giá : 3,990,000 VNĐ</td></tr>
 <tr><td>Số chỗ còn nhận : Liên hệ</td></tr>
 <tr><td><a href="/vn/tour/bookingtour/872">Đặt tour</a></td></tr>
</table>
<ul class="nav-tabs"><li><a href="#tabs-detail">Chương trình tour</a></li><li><a href="#tabs-more">Quy định</a></li>
 <li><a href="#tabs-adv">Bảng giá chi tiết</a></li><li><a href="#tabs-comment">Nhận xét</a></li></ul>
<div class="tab-content">
 <div id="tabs-detail">
  <p><span><strong>NGÀY 01: HÀ NỘI - HÀ GIANG (ĂN: T/C)</strong></span></p>
  <p>Sáng: xe đón khách khởi hành.</p>
  <p><img src="/public/frontend/uploads/kceditor/images/mau-1.jpg"></p>
  <p>Tối: nghỉ đêm tại Hà Giang.</p>
  <p><span><strong>NGÀY 02: HÀ GIANG - QUẢN BẠ - ĐỒNG VĂN (ĂN: S/T/C)</strong></span></p>
  <p>Tham quan cổng trời Quản Bạ.</p>
  <p><img src="/public/frontend/uploads/kceditor/images/mau-2.jpg"></p>
  <p><strong>NGÀY 03: ĐỒNG VĂN - HÀ NỘI (ĂN: S/T)</strong></p>
  <p>Về Hà Nội, kết thúc chương trình.</p>
 </div>
 <div id="tabs-more">
  <p><strong>GIÁ TOUR BAO GỒM:</strong></p>
  <p>- Xe du lịch đời mới</p><p>- Bảo hiểm du lịch</p>
  <p><strong>GIÁ TOUR KHÔNG BAO GỒM:</strong></p>
  <p>- Chi phí cá nhân</p>
  <p><strong>ĐIỀU KIỆN HỦY TOUR:</strong></p>
  <p>Hủy trước 3 ngày: phí 30%.</p>
 </div>
 <div id="tabs-adv"><table>
  <tr><th>Độ tuổi</th><th>Khách sạn</th><th>Giá tiền</th><th>Phụ thu phòng đơn</th></tr>
  <tr><td>Trẻ em( &lt; 5 tuổi)</td><td></td><td>Đang cập nhật</td><td>Không</td></tr>
  <tr><td>Trẻ em (5-11tuổi)</td><td>2 sao</td><td>2,990,000</td><td>Không</td></tr>
  <tr><td>Người lớn</td><td>2 sao</td><td>3,990,000</td><td>800,000</td></tr>
 </table></div>
 <div id="tabs-comment"><p>Chưa có nhận xét.</p></div>
</div>
<div class="owl-carousel"><div class="owl-item"><div class="item-product"><div class="image">
 <a href="/vn/tour/du-lich-vung-tau/tour-vt-964.html"><img src="/public/frontend/uploads/files/tour/POSTER_VUNG_TAU.jpg"></a></div></div></div></div>
<img src="https://evil.example.com/x.jpg">
</body></html>"""

DS = """<html><body>
<h2 class="title-category">Miền Nam</h2>
<div class="item-product"><div class="image"><a href="/vn/tour/du-lich-vung-tau/tour-vt-964.html">
 <img src="/public/frontend/uploads/files/tour/thumbnail/vt.jpg"></a></div>
 <div class="caption-product"><h3 class="caption-title"><a href="/vn/tour/du-lich-vung-tau/tour-vt-964.html">Tour Du Lịch 1 Ngày: TP.HCM - Vũng Tàu</a></h3></div></div>
<div class="item-product"><div class="image"><img src="/public/frontend/uploads/files/tour/dl.jpg"></div>
 <div class="caption-product"><div class="caption-title"><a href="https://www.vietourist.com.vn/vn/tour/du-lich-da-lat-145/tour-da-lat-985.html">Đà Lạt mộng mơ 3N2Đ</a></div></div></div>
<div class="item-product"><div class="caption-product"><div class="caption-title"><a href="https://evil.example.com/vn/tour/a/b.html">Giả mạo</a></div></div></div>
<div class="item-product"><div class="caption-product"><div class="caption-title"><a href="/vn/tour/du-lich-vung-tau/tour-vt-964.html">Tour Du Lịch 1 Ngày: TP.HCM - Vũng Tàu</a></div></div></div>
<h2 class="title-category">Du Lịch Xanh</h2>
<div class="item-product"><div class="caption-product"><div class="caption-title"><a href="/vn/tour/du-lich-xanh/tour-bao-loc-990.html">Tour Bảo Lộc 2N1Đ</a></div></div></div>
<a href="/vn/tour/bookingtour/964">Đặt tour</a>
</body></html>"""


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import cong_khach as K
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai, phong in (("dh", "nv_dh", ""), ("tpdh", "tp_dh", ""), ("sa", "sales_admin", "kd_le"), ("ct", "chutich", ""),
                            ("mkt", "nv_mkt", ""), ("kd", "nv_kd", ""), ("kt", "ketoan", "")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, department=phong, password_hash="x"))
    s.commit()
    monkeypatch.setattr(K, "_hom_nay", lambda: NOW.date())
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _sp(s, ma="DL001", ten="ĐÀ LẠT MỘNG MƠ", loai="le_noi_dia", program="", coc=30, dong=3):
    from app.models.core import Product
    p = Product(code=ma, name=ten, tour_type=loai, departure_point="TP HCM", transport="Xe giường nằm", days=3,
                length_text="3N2Đ", deposit_pct=coc, days_to_close=dong, program=program, status="active")
    s.add(p); s.commit()
    return p


def _tour(s, p, ngay=dt.date(2026, 11, 14), gia=2_590_000, km=None, chd=1_790_000, cho=10, ma=None):
    from app.models.core import Tour
    t = Tour(code=ma or f"{p.code}.{ngay:%d%m%y}", name="Tour package", tour_type=p.tour_type, start_date=ngay,
             end_date=ngay + dt.timedelta(days=2), operator_id=_u(s, "dh").id, status="da_duyet", price_per_pax=gia,
             price_promo=km, price_chd=chd, seats_open=cho, planned_pax=cho, imported=True, product_id=p.id, product_code=p.code)
    s.add(t); s.commit()
    return t


def _tk(s, sdt="0901000111", email="lan@example.com"):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai=sdt, email=email, ho_ten="Nguyễn Thị Lan", trang_thai="hoat_dong")
    s.add(tk); s.commit()
    return tk


def _mo(s, p):
    from app.services import tour_online as TR
    TR.bat_tt_chung(s, _u(s, "ct"), True, NOW)
    TR.bat_tt_sp(s, _u(s, "tpdh"), p.id, True)


def _khach(n):
    return [{"ho_ten": f"Nguyễn Văn {chr(65 + i)}", "ngay_sinh": "1990-01-01", "gioi_tinh": "nam"} for i in range(n)]


def _dat(s, tk, t, cach="coc", nl=2, te=0):
    from app.services import tour_online as TR
    return TR.dat(s, tk, {"tour_id": t.id, "nguoi_lon": nl, "tre_em": te, "cach_tra": cach, "ho_ten": "Nguyễn Thị Lan",
                          "dien_thoai": "0901000111", "email": "lan@example.com", "khach": _khach(nl + te), "dong_y": True}, NOW)


# ── 1 · ĐỌC WEB ──────────────────────────────────────────────────────────────────────────────────────────────────

def test_chi_doc_trang_vietourist():
    from app.services import tour_online as TR
    for xau in ("http://www.vietourist.com.vn/vn/tour/a.html", "https://evil.com/x", "https://vietourist.com.vn.evil.com/x",
                "https://www.vietourist.com.vn:8443/x", "https://user@www.vietourist.com.vn/x", "ftp://www.vietourist.com.vn/x"):
        with pytest.raises(TR.LoiTour):
            TR.kiem_link(xau)
    assert TR.kiem_link("https://vietourist.com.vn/vn/tour/a/b.html")
    assert TR.goc_tra_ve("https://evil.com") == TR.goc_tra_ve("https://vietourist.vn.evil.com") == "https://kh.vietourist.vn/tours"
    assert TR.goc_tra_ve("https://crm.vietourist.vn") == "https://crm.vietourist.vn/kham-pha/tours"


def test_phan_tich_trang_tour_mau():
    from app.services import tour_online as TR
    url = "https://www.vietourist.com.vn/vn/tour/du-lich-ha-giang/tour-du-lich-ha-noi-ha-giang-872.html"
    o = TR.phan_tich(TRANG, url)
    g = "https://www.vietourist.com.vn/public/frontend/uploads/"
    assert o["ten"] == "Tour Du Lịch Hà Nội - Hà Giang 3 Ngày"
    # album: ảnh chính + thumbnail đổi sang đường dẫn đầy đủ, trùng tên tệp giữ một; KHÔNG ảnh tour liên quan / chấm sao / host lạ
    assert o["anh"] == [g + "files/tour/ha-giang.jpg", g + "files/tour/dong-van.jpg",          # TR-1c: + ảnh chèn trong lịch trình
                        g + "kceditor/images/mau-1.jpg", g + "kceditor/images/mau-2.jpg"]
    assert [x["ngay"] for x in o["lich_trinh"]] == [1, 2, 3]
    n1, n2 = o["lich_trinh"][0], o["lich_trinh"][1]
    assert n1["tieu_de"] == "HÀ NỘI - HÀ GIANG (ĂN: T/C)" and n2["tieu_de"].startswith("HÀ GIANG - QUẢN BẠ")
    assert n1["noi_dung"] == "Sáng: xe đón khách khởi hành.\nTối: nghỉ đêm tại Hà Giang."
    assert n1["anh"] == [g + "kceditor/images/mau-1.jpg"] and n2["anh"] == [g + "kceditor/images/mau-2.jpg"]
    assert o["bao_gom"] == ["Xe du lịch đời mới", "Bảo hiểm du lịch"] and o["khong_bao_gom"] == ["Chi phí cá nhân"]
    assert o["quy_dinh"] == "ĐIỀU KIỆN HỦY TOUR:\nHủy trước 3 ngày: phí 30%."
    bg = {b["doi_tuong"]: b for b in o["bang_gia"]}
    assert bg["Người lớn"]["gia"] == 3990000 and bg["Người lớn"]["phu_thu_don"] == 800000 and bg["Người lớn"]["khach_san"] == "2 sao"
    assert bg["Trẻ em (5-11tuổi)"]["gia"] == 2990000 and bg["Trẻ em (5-11tuổi)"]["phu_thu_don"] is None
    assert bg["Trẻ em( < 5 tuổi)"]["gia"] is None and bg["Trẻ em( < 5 tuổi)"]["ghi"] == "Đang cập nhật"
    assert o["khoi_hanh_text"] == "thứ bảy, chủ nhật" and o["thoi_luong"] == "3 Ngày - 2 Đêm"
    assert o["phuong_tien"] == "Ô tô" and o["phuong_tien_ma"] == ["xe"] and o["gia_web"] == 3990000
    assert TR.ma_phuong_tien("Máy bay") == ["may_bay"] and TR.ma_phuong_tien("Tàu") == ["tau_hoa"]
    assert TR.ma_phuong_tien("Du thuyền") == ["du_thuyen"] and TR.ma_phuong_tien("Máy bay, Ô tô") == ["may_bay", "xe"]
    # «NGÀY 1» rồi «NGÀY 3» (thiếu ngày 2) → không đoán
    assert TR.phan_tich(TRANG.replace("NGÀY 02", "NGÀY 05"), url)["lich_trinh"] == []
    ds = TR.phan_tich_ds(DS, "https://www.vietourist.com.vn/vn/tour/tour-trong-nuoc")
    assert [x["url"] for x in ds] == ["https://www.vietourist.com.vn/vn/tour/du-lich-vung-tau/tour-vt-964.html",
                                      "https://www.vietourist.com.vn/vn/tour/du-lich-da-lat-145/tour-da-lat-985.html",
                                      "https://www.vietourist.com.vn/vn/tour/du-lich-xanh/tour-bao-loc-990.html"]
    assert ds[0]["ten"] == "Tour Du Lịch 1 Ngày: TP.HCM - Vũng Tàu" and ds[0]["muc"] == "Miền Nam"
    assert ds[0]["anh"] == g + "files/tour/vt.jpg" and not ds[0]["goi_y_wellness"]
    assert ds[2]["muc"] == "Du Lịch Xanh" and ds[2]["goi_y_wellness"]
    assert TR.phan_tich_ds('<div class="item-product"><div class="caption-title"><a href="/vn/tour/a/b.html">Thiên Cầm biển xanh</a></div></div>',
                           "https://www.vietourist.com.vn/x")[0]["goi_y_wellness"] is False


def test_doc_hong_giu_ban_cu_va_ghep_goi_y(db, monkeypatch):
    from app.services import tour_online as TR
    p = _sp(db)
    _tour(db, p)
    monkeypatch.setattr(TR, "FETCH", lambda url: TRANG.encode())
    with pytest.raises(TR.LoiTour):                                   # NV KD không ghép được
        TR.ghep(db, _u(db, "kd"), p.id, "https://www.vietourist.com.vn/vn/tour/du-lich-da-lat/tour-dl.html")
    TR.ghep(db, _u(db, "tpdh"), p.id, "https://www.vietourist.com.vn/vn/tour/du-lich-da-lat/tour-dl.html")
    assert len(p.noi_dung_web["anh"]) >= 2 and p.noi_dung_web["loi"] == ""

    def _hong(url):
        raise TimeoutError("web chậm")
    monkeypatch.setattr(TR, "FETCH", _hong)
    nd = TR.doc_lai(db, _u(db, "mkt"), p.id)
    assert nd["loi"] and len(nd["anh"]) >= 2                          # giữ ảnh cũ, ghi lỗi
    monkeypatch.setattr(TR, "FETCH", lambda url: DS.encode())
    web = TR.ds_web(db, _u(db, "dh"))
    vt = next(x for x in web if "da-lat" in x["url"])
    assert vt["goi_y"] and vt["goi_y"]["ma"] == "DL001"


# ── 2 · GỘP CHUYẾN, TÌM ──────────────────────────────────────────────────────────────────────────────────────────

def test_gop_theo_san_pham_gia_tu_va_loc(db):
    from app.services import tour_online as TR
    p = _sp(db)
    _tour(db, p, dt.date(2026, 11, 14), gia=2_590_000, km=2_190_000)
    _tour(db, p, dt.date(2026, 11, 21), gia=2_390_000, cho=1)          # rẻ hơn nhưng chỉ còn 1 chỗ
    nn = _sp(db, "JP001", "OSAKA – KYOTO 5N4Đ", "le_nuoc_ngoai")
    _tour(db, nn, dt.date(2026, 12, 1), gia=19_990_000)
    doan = _sp(db, "MICE1", "TEAM BUILDING PHAN THIẾT", "doan_noi_dia", program="Ngày 1: Gala")
    r = TR.tim(db, nguoi_lon=2, hom_nay=NOW.date())
    dl = next(x for x in r["san_pham"] if x["ma"] == "DL001")
    assert dl["ten"] == "ĐÀ LẠT MỘNG MƠ" and dl["so_chuyen"] == 2 and dl["gia_tu"] == 2_190_000 and dl["gia_goc"] == 2_590_000
    assert TR.tim(db, nguoi_lon=1, hom_nay=NOW.date())["san_pham"][0]["gia_tu"] == 2_190_000
    assert {x["ma"] for x in TR.tim(db, tab="nuoc_ngoai", hom_nay=NOW.date())["san_pham"]} == {"JP001"}
    assert {x["ma"] for x in TR.tim(db, loai_="doan", hom_nay=NOW.date())["san_pham"]} == {"MICE1"}
    assert {x["ma"] for x in TR.tim(db, q="da lat", hom_nay=NOW.date())["san_pham"]} == {"DL001"}
    r = TR.tim(db, tu=dt.date(2026, 11, 20), den=dt.date(2026, 11, 30), hom_nay=NOW.date())
    assert {x["ma"] for x in r["san_pham"]} == {"DL001", "MICE1"}
    assert doan.id in {x["id"] for x in r["san_pham"]}


def test_lich_trinh_uu_tien(db):
    from app.models.chuong_trinh import ChuongTrinhNgay
    from app.services import tour_online as TR
    p = _sp(db, program="Giá bao gồm xe\nNgày 1: Sài Gòn – Đà Lạt\nĐi xe\nNgày 2: Đồi chè\nNgày 3: Về")
    t = _tour(db, p)
    assert TR.lich_trinh(db, p, t.id)["nguon"] == "san_pham" and len(TR.lich_trinh(db, p, t.id)["ngay"]) == 3
    p.noi_dung_web = {"lich_trinh": [{"ngay": 1, "tieu_de": "Web", "noi_dung": "x", "anh": []}]}
    assert TR.lich_trinh(db, p, t.id)["nguon"] == "web"
    db.add(ChuongTrinhNgay(tour_id=t.id, ngay_thu=1, tieu_de="Chuyến riêng", bua_sang=True)); db.commit()
    lt = TR.lich_trinh(db, p, t.id)
    assert lt["nguon"] == "chuyen" and lt["ngay"][0]["bua"] == ["sáng"]
    assert TR.tach_ngay("Ngày 1: a\nNgày 3: b") == []                 # mốc không liên tiếp → không đoán
    p2 = _sp(db, "X1", "X", program="Văn bản tự do không mốc")
    assert TR.lich_trinh(db, p2)["nguon"] == "van_ban"


# ── 3 · TIỀN, CÔNG TẮC ───────────────────────────────────────────────────────────────────────────────────────────

def test_coc_han_va_cong_tac(db):
    from app.services import tour_online as TR
    p = _sp(db, coc=30, dong=3)
    t = _tour(db, p, gia=2_590_000, km=2_190_000, chd=1_790_001)
    o = TR.tinh(db, t.id, 2, 1, 0, "coc", NOW)
    assert o["tong"] == 2_190_000 * 2 + 1_790_001 and o["coc"] == 1_852_000 and o["phai_tra"] == 1_852_000   # 1.851.000,3 → làm tròn LÊN
    assert o["han_tra_con_lai"] == "2026-11-11T17:00"
    assert TR.tinh(db, t.id, 2, 0, 0, "coc", dt.datetime(2026, 11, 12, 9))["cach_tra"] == "du"   # quá hạn → trả đủ
    tk = _tk(db)
    with pytest.raises(TR.LoiTour) as e:
        _dat(db, tk, t)
    assert e.value.status == 409
    TR.bat_tt_chung(db, _u(db, "ct"), True, NOW)
    with pytest.raises(TR.LoiTour):                                   # chung bật, sản phẩm chưa → vẫn 409
        _dat(db, tk, t)
    with pytest.raises(TR.LoiTour):                                   # NV ĐH không mở thanh toán sản phẩm
        TR.bat_tt_sp(db, _u(db, "dh"), p.id, True)
    with pytest.raises(TR.LoiTour):                                   # TP ĐH không mở công tắc chung
        TR.bat_tt_chung(db, _u(db, "tpdh"), True)
    TR.bat_tt_sp(db, _u(db, "tpdh"), p.id, True)
    d = _dat(db, tk, t)
    assert int(d.phai_tra) == 1_314_000


def test_dat_giu_cho_qr_coc_email_va_invoice(db, monkeypatch):
    from app.models.core import Booking
    from app.models.payments import BankTransaction, Receipt
    from app.services import payments as P
    from app.services import tour_online as TR
    gui = []
    monkeypatch.setattr(TR, "GUI_EMAIL", lambda to, tieu, noi, kem: gui.append((to, tieu, kem)))
    p = _sp(db)
    t = _tour(db, p, gia=2_000_000, cho=10)
    _mo(db, p)
    tk = _tk(db)
    d = _dat(db, tk, t)
    b = db.get(Booking, d.booking_id)
    assert b.sales_id == _u(db, "sa").id and b.amount == 4_000_000 and b.customer_email == "lan@example.com"
    assert b.giu_cho_den == NOW + dt.timedelta(minutes=15) and d.phai_tra == 1_200_000
    with pytest.raises(TR.LoiTour):                                   # thiếu thông tin khách
        TR.dat(db, tk, {"tour_id": t.id, "nguoi_lon": 2, "khach": _khach(1), "ho_ten": "A B", "dien_thoai": "0901000111",
                        "email": "a@b.vn", "dong_y": True}, NOW)
    txn = BankTransaction(sepay_id="S1", transaction_date=NOW, transfer_type="in", amount=1_200_000,
                          content=f"CK {d.ma} coc", match_status="chua_khop")
    db.add(txn); db.commit()
    P.match_transaction(db, txn); db.commit()
    r = db.execute(select(Receipt).where(Receipt.booking_id == b.id)).scalars().one()
    assert int(r.amount) == 1_200_000 and txn.match_status == "da_khop"
    assert len(gui) == 1 and gui[0][0] == "lan@example.com" and gui[0][2][0][2] == "application/pdf"
    assert gui[0][2][0][1][:5] == b"%PDF-"
    o = TR.don_khach(db, tk, d.ma)
    assert o["da_tra"] == 1_200_000 and o["con_lai"] == 2_800_000 and o["trang_thai"].startswith("Đã đặt cọc")
    assert TR.tai_hoa_don(db, tk, d.ma)[:5] == b"%PDF-"
    khac = _tk(db, "0909999888", "khac@example.com")
    with pytest.raises(TR.LoiTour) as e:                              # khách khác không tải được invoice
        TR.tai_hoa_don(db, khac, d.ma)
    assert e.value.status == 404
    txn2 = BankTransaction(sepay_id="S2", transaction_date=NOW, transfer_type="in", amount=999, content=f"{d.ma}",
                           match_status="chua_khop")
    db.add(txn2); db.commit()
    P.match_transaction(db, txn2); db.commit()
    assert txn2.match_status == "cho_ke_toan" and len(gui) == 1        # lệch số: Kế toán quyết, không email


def test_the_sepay_thanh_cong_sinh_phieu_thu(db, monkeypatch):
    from app.models.payments import Receipt
    from app.services import sepay_pg as SP
    from app.services import tour_online as TR
    monkeypatch.setattr(TR, "GUI_EMAIL", lambda *a: None)
    monkeypatch.setattr(SP, "bat", lambda: True)
    monkeypatch.setattr(SP, "bieu_mau", lambda ma, so, mo, a, b, c: {"action": "x", "fields": [["order_invoice_number", ma]]})
    p = _sp(db)
    t = _tour(db, p, gia=1_000_000)
    _mo(db, p)
    tk = _tk(db)
    d = _dat(db, tk, t, cach="du", nl=1)
    f = TR.the_bat_dau(db, tk, d.ma, "https://kh.vietourist.vn", "du", NOW)
    ma = f["form"]["fields"][0][1]
    assert ma.startswith("TR")
    TR.sepay_ket_qua(db, {"ma_gd": ma, "loai": "ORDER_PAID", "thanh_cong": True, "so_tien": 1_000_000, "ma_kq": "APPROVED", "so_gd": "G1"}, NOW)
    r = db.execute(select(Receipt)).scalars().one()
    assert r.method == "the" and int(r.amount) == 1_000_000 and r.status == "tu_dong"
    assert TR.don_khach(db, tk, d.ma)["trang_thai"] == "Đã thanh toán đủ"


def test_ma_tran_quan_ly(db):
    from app.services import access as AC
    from app.services import tour_online as TR
    assert set(TR.VAI_TT_CHUNG) == {"chutich", "tgd"}
    assert "nv_mkt" in TR.VAI_SUA_CONG and "nv_mkt" not in TR.VAI_GHEP and "ketoan" in TR.VAI_VAT
    assert set(TR.VAI_XEM) <= set(AC.MENU_ROLES["/tour-online"])
    assert AC.MAN_HINH_API["/tour-online"] == ("/api/v1/tour-online",)
    with pytest.raises(TR.LoiTour):
        TR.xuat_vat(db, _u(db, "kd"), 1)
    with pytest.raises(TR.LoiTour):
        TR.sua_cong(db, _u(db, "kd"), 1, {})
    p = _sp(db)
    TR.sua_cong(db, _u(db, "mkt"), p.id, {"wellness": True, "phuong_tien_ds": ["tau_hoa", "xe", "bay"], "noi_bat": ["Đồi chè"]})
    assert p.wellness and p.phuong_tien_ds == ["tau_hoa", "xe"]
    with pytest.raises(TR.LoiTour):
        TR.sua_cong(db, _u(db, "mkt"), p.id, {"noi_bat": list("abcdef")})


def test_invoice_khong_co_phong_viet_van_ra_pdf(db, monkeypatch):
    """Máy chủ thiếu gói phông: invoice vẫn ra PDF, chữ in không dấu (không ô vuông)."""
    from app.models.payments import Receipt  # noqa: F401
    from app.services import tour_online as TR
    monkeypatch.setattr(TR, "PHONG", ("/khong/co.ttf",))
    monkeypatch.setattr(TR, "PHONG_DAM", ("/khong/co.ttf",))
    assert not TR.co_phong_viet() and TR._bo_dau("XÁC NHẬN Đà Lạt") == "XAC NHAN Da Lat"
    p = _sp(db)
    t = _tour(db, p)
    _mo(db, p)
    d = _dat(db, _tk(db), t)
    assert TR.hoa_don_pdf(db, d, NOW)[:5] == b"%PDF-"


def test_tr1c_ky_tu_rong_link_co_dau_va_trang_chi_gioi_thieu():
    """TR-1c (đo trên trang thật 02/11/2026): web chèn U+200B trước «NGÀY 1:»; link có dấu cách / «Đ»; tour Du lịch Xanh
    chỉ có bài giới thiệu (không mốc ngày) → giữ làm «Giới thiệu», ảnh chèn vẫn vào album."""
    from app.services import tour_online as TR
    url = "https://www.vietourist.com.vn/vn/tour/du-lich-nha-trang-135/tour-dao-diep-son-3n2d-989.html"
    o = TR.phan_tich(TRANG.replace("NGÀY 01", "\u200bNGÀY 01").replace("NGÀY 02", "\u200bNGÀY 02"), url)
    assert [x["ngay"] for x in o["lich_trinh"]] == [1, 2, 3] and o["gioi_thieu"] == ""
    assert TR.ma_hoa_link("https://www.vietourist.com.vn/vn/tour/du-lich-tay-nguyen/tour- bao-loc-963.html") == \
        "https://www.vietourist.com.vn/vn/tour/du-lich-tay-nguyen/tour-%20bao-loc-963.html"
    assert TR.ma_hoa_link("https://www.vietourist.com.vn/vn/tour/du-lich-mien-tay/tour-mien-tay-2N1Đ-952.html").endswith("2N1%C4%90-952.html")
    assert TR.ma_hoa_link("https://www.vietourist.com.vn/vn/tour/a/tour-%20b-1.html").endswith("tour-%20b-1.html")   # không mã hóa 2 lần
    xanh = """<html><body><h1>Tour Du Lịch Xanh Mẫu</h1><div class="album-gallery"><img src="/public/frontend/uploads/files/tour/xanh.jpg"></div>
    <div id="tabs-detail"><p>Bạn có đang mơ về một chuyến đi chạm vào thiên nhiên?</p>
    <p><img src="/public/frontend/uploads/kceditor/images/rung-1.jpg"></p><p>Đạp xe xuyên rừng, thiền sáng bên sông.</p></div>
    <div id="tabs-more"></div><div id="tabs-adv"></div></body></html>"""
    o = TR.phan_tich(xanh, "https://www.vietourist.com.vn/vn/tour/du-lich-xanh/x-904.html")
    g = "https://www.vietourist.com.vn/public/frontend/uploads/"
    assert o["lich_trinh"] == [] and o["anh"] == [g + "files/tour/xanh.jpg", g + "kceditor/images/rung-1.jpg"]
    assert o["gioi_thieu"] == "Bạn có đang mơ về một chuyến đi chạm vào thiên nhiên?\nĐạp xe xuyên rừng, thiền sáng bên sông."
