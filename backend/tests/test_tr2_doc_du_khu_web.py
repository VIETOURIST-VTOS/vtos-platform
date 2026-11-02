# -*- coding: utf-8 -*-
"""TR-2 · Màn «Tour online → tour trên web» phải thấy ĐỦ tour đang bán (Chủ tịch «làm từ 1 đến 4» 03/11/2026).

Hai trang danh sách chỉ in vài tour mỗi miền rồi để nút «Xem thêm» → /vn/tour/area/?area=N (mỗi khu lại chia trang).
Trước TR-2 bộ đọc chỉ lấy hai trang đầu: thấy 57 trong 105 tour, phần còn lại không ai ghép được.
Mỗi phép thử đo hai chiều.
"""
from tests.test_tr1_tour_agoda import db, _u, _sp  # noqa: F401

G = "https://www.vietourist.com.vn"


def _the(duong, ten):
    return f'<div class="item-product"><div class="caption-title"><a href="{duong}">{ten}</a></div></div>'


DS_TRONG = ("<h2>Miền Nam</h2>" + _the("/vn/tour/du-lich-vung-tau/tour-vt-964.html", "Tour Vũng Tàu 1 Ngày")
            + f'<a class="readmore" href="{G}/vn/tour/area/?area=3">Xem thêm</a>')
DS_NGOAI = ('<a class="readmore" href="/vn/tour/area/?area=7">Xem thêm</a>'
            '<a class="readmore" href="https://evil.example/vn/tour/area/?area=9&x=1">lạ</a>')
KHU = {
    (3, 1): _the("/vn/tour/du-lich-vung-tau/tour-vt-964.html", "Tour Vũng Tàu 1 Ngày") + _the("/vn/tour/du-lich-ben-tre/tour-bt-858.html", "Tour Bến Tre Mỹ Tho"),
    (3, 2): _the("/vn/tour/du-lich-can-gio/tour-cg-242.html", "Tour Cần Giờ"),
    (3, 3): _the("/vn/tour/du-lich-can-gio/tour-cg-242.html", "Tour Cần Giờ"),          # trang lặp → dừng
    (7, 1): _the("/vn/tour/du-lich-nhat-ban/tour-nb-882.html", "Tour Nhật Bản Osaka"),
}


def _fetch(goi):
    def f(url):
        goi.append(url)
        if url.endswith("tour-trong-nuoc"):
            return DS_TRONG.encode()
        if url.endswith("tour-nuoc-ngoai"):
            return DS_NGOAI.encode()
        import re
        m = re.search(r"area=(\d+)&page=(\d+)$", url)
        assert m and url.startswith(G + "/vn/tour/area/"), f"đọc link lạ: {url}"
        return KHU.get((int(m.group(1)), int(m.group(2))), "").encode()
    return f


def test_tr2_1_so_khu_chi_nhan_so(monkeypatch):
    from app.services import tour_online as TR
    assert TR.phan_tich_khu(DS_TRONG + DS_NGOAI) == [3, 7], "khu có tham số lạ (&x=1) không được nhận"
    assert TR.phan_tich_khu("<p>không có nút</p>") == []


def test_tr2_2_doc_du_cac_khu_va_phan_trang(monkeypatch):
    from app.services import tour_online as TR
    goi = []
    monkeypatch.setattr(TR, "FETCH", _fetch(goi))
    web, loi = TR.doc_ds_web()
    urls = {o["url"].rsplit("/", 1)[1] for o in web}
    assert urls == {"tour-vt-964.html", "tour-bt-858.html", "tour-cg-242.html", "tour-nb-882.html"} and loi == []
    assert len(web) == 4, "tour lặp giữa trang danh sách và khu chỉ tính một lần"
    vt = next(o for o in web if o["url"].endswith("964.html"))
    assert vt["muc"] == "Miền Nam", "giữ mục của trang danh sách"
    # dừng khi trang không còn tour mới — không đọc tới trần 40 trang
    assert not any("page=4" in u for u in goi) and not any("area=9" in u for u in goi)


def test_tr2_3_khu_hong_khong_mat_tour_da_doc(monkeypatch):
    from app.services import tour_online as TR
    goi = []
    f = _fetch(goi)

    def hong(url):
        if "area=7" in url:
            raise TimeoutError("web chậm")
        return f(url)
    monkeypatch.setattr(TR, "FETCH", hong)
    web, loi = TR.doc_ds_web()
    assert len(web) == 3 and any("khu 7" in l for l in loi)


def test_tr2_4_ds_web_tra_ca_tour_trong_khu(db, monkeypatch):
    from app.services import tour_online as TR
    _sp(db)
    goi = []
    monkeypatch.setattr(TR, "FETCH", _fetch(goi))
    ra = TR.ds_web(db, _u(db, "dh"))
    assert any(o["url"].endswith("tour-nb-882.html") for o in ra), "tour chỉ có trong khu «Xem thêm» phải hiện để ghép"
    # chiều ngược lại: web không có khu nào → vẫn như cũ (chỉ hai trang danh sách)
    monkeypatch.setattr(TR, "FETCH", lambda url: DS_TRONG.replace("readmore", "khac").replace("area=", "x=").encode())
    assert len(TR.ds_web(db, _u(db, "dh"))) == 1
