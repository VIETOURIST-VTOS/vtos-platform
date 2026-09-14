"""V6 – một khách đi trọn đường, và cổng biên chặn được ở bước báo giá.

Nghiệm thu V6 nói đúng một câu: "một khách đi trọn đường: bảng giá → báo giá có phiên bản → hợp đồng
→ booking, và cổng biên chặn được ở bước báo giá."

Phép thử quan trọng nhất ở đây KHÔNG phải phép thử đi trọn đường – đường thông là điều dễ làm xanh.
Quan trọng nhất là phép thử NGƯỢC: cổng biên phải CHẶN thật. Một cổng luôn mở cũng làm phép thử đi
trọn đường xanh, và lúc đó ta có một chuỗi bán hàng đầy đủ mà không ai canh biên.

Và canh cả điều luật đã học bằng giá đắt (Ý kiến thẩm định 06/9 mục B1): THIẾU GIÁ VỐN KHÔNG PHẢI
GIÁ VỐN BẰNG 0. Trước đây giá vốn trống cho biên 100% và cổng luôn báo ĐẠT – cổng chặn số một bị vô
hiệu hóa đúng ở những chuyến ít dữ liệu nhất.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v6.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

client = TestClient(app)
KH = (date.today() + timedelta(days=45)).isoformat()


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str) -> dict:
    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()
        assert u is not None, f"dữ liệu mẫu không có vai trò {vai}"
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _nguong() -> float:
    return client.get("/api/v1/ban-hang/meta", headers=login("chutich")).json()["nguong_bien"]


def _tao_bao_gia(dong, mang="kd_le", who="gd_kd", ten="Khách thử V6"):
    r = client.post("/api/v1/ban-hang/bao-gia", headers=login(who),
                    json={"khach_ten": ten, "mang": mang, "so_khach": 10,
                          "ngay_khoi_hanh": KH, "dong": dong})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _dong(don_gia, gia_von, sl=10):
    return [{"hang_khach": "nguoi_lon", "mo_ta": "Tour thử", "so_luong": sl,
             "don_gia": don_gia, "gia_von_don_vi": gia_von}]


# ====================== 1. CỔNG BIÊN – PHÉP THỬ NGƯỢC ======================
def test_thieu_gia_von_KHONG_phai_gia_von_bang_0():
    """Điều luật B1. Bỏ giá vốn trống thì biên KHÔNG được là 100%, và cổng KHÔNG được ĐẠT."""
    bid = _tao_bao_gia([{"hang_khach": "nguoi_lon", "mo_ta": "chưa có giá vốn",
                         "so_luong": 10, "don_gia": 5_000_000}])
    cong = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd")).json()["cong_bien"]
    assert cong["du_co_so"] is False, cong
    assert cong["dat"] is False, "giá vốn trống mà cổng vẫn ĐẠT – đúng cách cổng bị vô hiệu hóa"
    assert cong["bien"] is None, "không có giá vốn mà vẫn tính ra một con số biên"
    assert cong["dong_thieu_gia_von"], cong


def test_gui_bi_CHAN_khi_chua_du_co_so():
    bid = _tao_bao_gia([{"hang_khach": "nguoi_lon", "so_luong": 10, "don_gia": 5_000_000}])
    r = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"), json={})
    assert r.status_code == 422, f"gửi được báo giá không biết lãi lỗ: {r.status_code}"
    assert r.json()["detail"]["gate"] == "CONG_BIEN_BAO_GIA"
    assert r.json()["detail"]["du_co_so"] is False


def test_gui_bi_CHAN_khi_bien_mong_va_khong_giai_trinh():
    """Phép thử ngược quan trọng nhất: cổng phải chặn thật, không phải chỉ hiện một con số."""
    ng = _nguong()
    von = 5_000_000 * (1 - ng / 2)          # biên đúng bằng một nửa ngưỡng: chắc chắn mỏng
    bid = _tao_bao_gia(_dong(5_000_000, von))
    r = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"), json={})
    assert r.status_code == 422, f"biên mỏng vẫn gửi được: {r.text}"
    ct = r.json()["detail"]
    assert ct["gate"] == "CONG_BIEN_BAO_GIA" and ct["du_co_so"] is True
    assert ct["bien"] < ng
    # Giải trình cụt cũng không qua – "ok" không phải một lời giải trình.
    r2 = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"),
                     json={"giai_trinh": "ok"})
    assert r2.status_code == 422


def test_bien_mong_CO_giai_trinh_thi_gui_duoc_va_ghi_lai_la_duoi_bien():
    ng = _nguong()
    bid = _tao_bao_gia(_dong(5_000_000, 5_000_000 * (1 - ng / 2)))
    r = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"),
                    json={"giai_trinh": "Khách đoàn quen, chấp nhận biên mỏng để giữ mối; "
                                        "bù bằng dịch vụ lẻ bán thêm tại điểm đến."})
    assert r.status_code == 200, r.text
    assert r.json()["duoi_bien"] is True
    d = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd")).json()
    assert d["trang_thai"] == "da_gui" and d["duoi_bien"] is True and d["giai_trinh"]


def test_bien_dat_thi_gui_thang_khong_can_giai_trinh():
    ng = _nguong()
    bid = _tao_bao_gia(_dong(5_000_000, 5_000_000 * (1 - ng - 0.1)))
    r = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"), json={})
    assert r.status_code == 200, r.text
    assert r.json()["duoi_bien"] is False and r.json()["du_co_so"] is True


# ====================== 2. BẢN ĐÃ GỬI LÀ BẢN ĐÓNG BĂNG ======================
def test_sua_bao_gia_sau_khi_gui_KHONG_lam_doi_ban_da_gui():
    """Gửi khách rồi thì con số đó là cam kết. Nếu sửa báo giá làm bản đã gửi đổi theo thì câu hỏi
    'hôm ấy ta hứa bao nhiêu' không trả lời được – mà đó đúng là câu hỏi lúc tranh chấp."""
    ng = _nguong()
    bid = _tao_bao_gia(_dong(5_000_000, 5_000_000 * (1 - ng - 0.1)))
    client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"), json={})
    d = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd")).json()
    tong_cu = d["ban_da_gui"][0]["tong_ban"]

    r = client.put(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd"),
                   json={"khach_ten": d["khach_ten"], "mang": d["mang"], "so_khach": 10,
                         "ngay_khoi_hanh": KH, "phien_ban": d["phien_ban"],
                         "dong": _dong(9_000_000, 1_000_000)})
    assert r.status_code == 200, r.text
    d2 = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd")).json()
    assert d2["ban_da_gui"][0]["tong_ban"] == tong_cu, "sửa báo giá làm đổi bản ĐÃ GỬI"


def test_gui_lan_hai_sinh_ban_moi_chu_khong_de_len_ban_cu():
    ng = _nguong()
    bid = _tao_bao_gia(_dong(5_000_000, 5_000_000 * (1 - ng - 0.1)))
    client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"), json={})
    client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers={**login("gd_kd"),
                                                                "X-Khoa-Ghi": "v6-gui-lan-2"}, json={})
    d = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd")).json()
    assert len(d["ban_da_gui"]) == 2 and {b["lan"] for b in d["ban_da_gui"]} == {1, 2}


def test_bam_gui_hai_lan_lien_KHONG_sinh_hai_ban(_khoa="v6-mot-lan-bam"):
    """V10 gặp V6: một lần bấm nút bị lặp không được thành hai cam kết với khách."""
    ng = _nguong()
    bid = _tao_bao_gia(_dong(5_000_000, 5_000_000 * (1 - ng - 0.1)))
    h = {**login("gd_kd"), "X-Khoa-Ghi": _khoa}
    a = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=h, json={})
    b = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=h, json={})
    assert a.status_code == 200 and b.status_code == 200
    assert b.json().get("lap_lai") is True
    d = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd")).json()
    assert len(d["ban_da_gui"]) == 1, "bấm hai lần thành hai bản gửi khách"


# ====================== 3. HỢP ĐỒNG ======================
def _den_khach_chot():
    ng = _nguong()
    bid = _tao_bao_gia(_dong(5_000_000, 5_000_000 * (1 - ng - 0.1)))
    client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui", headers=login("gd_kd"), json={})
    client.post(f"/api/v1/ban-hang/bao-gia/{bid}/khach-chot", headers=login("gd_kd"))
    return bid


def test_khong_lap_duoc_hop_dong_khi_khach_chua_chot():
    ng = _nguong()
    bid = _tao_bao_gia(_dong(5_000_000, 5_000_000 * (1 - ng - 0.1)))
    r = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/hop-dong", headers=login("gd_kd"), json={})
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "TRANG_THAI"


def test_gia_tri_hop_dong_lay_tu_BAN_DA_GUI_chu_khong_tu_ban_dang_soan():
    """Khách chốt con số hôm ấy. Lấy từ bảng đang soạn thì hợp đồng mang con số hôm nay, và chênh
    lệch chỉ lộ ra lúc đối chiếu doanh thu vài tháng sau."""
    bid = _den_khach_chot()
    d = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=login("gd_kd")).json()
    tong_da_gui = d["ban_da_gui"][0]["tong_ban"]
    r = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/hop-dong", headers=login("gd_kd"),
                    json={"ngay_ky": date.today().isoformat(), "dat_coc": 10_000_000})
    assert r.status_code == 201, r.text
    assert r.json()["gia_tri"] == tong_da_gui


def test_mot_bao_gia_chi_mot_hop_dong():
    bid = _den_khach_chot()
    a = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/hop-dong", headers=login("gd_kd"), json={})
    assert a.status_code == 201, a.text
    b = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/hop-dong", headers=login("gd_kd"), json={})
    assert b.status_code == 422 and b.json()["detail"]["gate"] == "DA_CO_HOP_DONG"


# ====================== 4. TRỌN ĐƯỜNG MỘT KHÁCH ======================
def test_mot_khach_di_TRON_DUONG_bang_gia_bao_gia_hop_dong_booking():
    """Đúng câu nghiệm thu của V6."""
    ng = _nguong()
    bg = client.post("/api/v1/ban-hang/bang-gia", headers=login("gd_kd"),
                     json={"ten": "Bảng giá thử V6", "mang": "kd_le",
                           "hieu_luc_tu": date.today().isoformat(),
                           "dong": [{"hang_khach": "nguoi_lon", "gia_ban": 5_000_000,
                                     "gia_von": 3_000_000}]})
    assert bg.status_code == 201, bg.text
    bang_gia_id = bg.json()["id"]

    r = client.post("/api/v1/ban-hang/bao-gia", headers=login("gd_kd"),
                    json={"khach_ten": "Khách trọn đường", "mang": "kd_le", "so_khach": 10,
                          "ngay_khoi_hanh": KH, "bang_gia_id": bang_gia_id,
                          "dong": _dong(5_000_000, 5_000_000 * (1 - ng - 0.1))})
    bid = r.json()["id"]
    assert client.post(f"/api/v1/ban-hang/bao-gia/{bid}/gui",
                       headers=login("gd_kd"), json={}).status_code == 200
    client.post(f"/api/v1/ban-hang/bao-gia/{bid}/khach-chot", headers=login("gd_kd"))
    hd = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/hop-dong", headers=login("gd_kd"),
                     json={"ngay_ky": date.today().isoformat()}).json()

    from app.db.session import SessionLocal
    from app.models.core import Booking
    with SessionLocal() as db:
        bk = db.execute(select(Booking)).scalars().first()
        assert bk is not None, "dữ liệu mẫu không có booking nào"
        bk_id = bk.id
    n = client.post(f"/api/v1/ban-hang/hop-dong/{hd['id']}/booking/{bk_id}", headers=login("gd_kd"))
    assert n.status_code == 200, n.text

    chuoi = client.get(f"/api/v1/ban-hang/hop-dong/{hd['id']}/chuoi", headers=login("ketoan")).json()
    assert chuoi["day_du"] is True, chuoi
    for k in ("bang_gia", "bao_gia", "ban_da_gui", "hop_dong"):
        assert chuoi[k] is not None, f"đứt ở mắt xích {k}"
    assert chuoi["booking_id"] == bk_id


def test_mot_booking_chi_mot_hop_dong():
    ng = _nguong()
    from app.db.session import SessionLocal
    from app.models.core import Booking
    with SessionLocal() as db:
        bk_id = db.execute(select(Booking)).scalars().first().id
    bid = _den_khach_chot()
    hd = client.post(f"/api/v1/ban-hang/bao-gia/{bid}/hop-dong", headers=login("gd_kd"),
                     json={}).json()
    r = client.post(f"/api/v1/ban-hang/hop-dong/{hd['id']}/booking/{bk_id}", headers=login("gd_kd"))
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "BOOKING_DA_CO_HOP_DONG", r.text


# ====================== 5. MỘT BẢNG CHO CẢ LẺ VÀ ĐOÀN ======================
def test_le_va_doan_dung_CHUNG_mot_bang_loc_theo_mang():
    """Tách đôi thì mọi phép tính biên, mọi báo cáo, mọi cổng chặn phải viết hai lần – và hai bản sẽ
    lệch nhau, thường ở bản ít người nhìn hơn."""
    from app.models.ban_hang import BaoGia
    from app.db.session import Base
    assert "bao_gia_doan" not in Base.metadata.tables, "đã tách đôi bảng báo giá"
    _tao_bao_gia(_dong(5_000_000, 3_000_000), mang="kd_doan", ten="Khách đoàn thử V6")
    le = client.get("/api/v1/ban-hang/bao-gia?mang=kd_le", headers=login("chutich")).json()
    doan = client.get("/api/v1/ban-hang/bao-gia?mang=kd_doan", headers=login("chutich")).json()
    assert doan and all(b["mang"] == "kd_doan" for b in doan)
    assert le and all(b["mang"] == "kd_le" for b in le)


def test_mang_la_la_bi_tu_choi():
    r = client.post("/api/v1/ban-hang/bao-gia", headers=login("gd_kd"),
                    json={"khach_ten": "x", "mang": "kd_gi_do", "dong": []})
    assert r.status_code == 422


# ====================== 6. QUYỀN ======================
def test_sale_soan_bao_gia_duoc_nhung_KHONG_dat_duoc_bang_gia():
    """Bảng giá là CHÍNH SÁCH BÁN. Từng sale đặt được giá niêm yết thì không còn là chính sách."""
    r = client.post("/api/v1/ban-hang/bang-gia", headers=login("nv_kd"),
                    json={"ten": "sale tự đặt giá", "hieu_luc_tu": date.today().isoformat()})
    assert r.status_code == 403, r.text
    assert client.post("/api/v1/ban-hang/bao-gia", headers=login("nv_kd"),
                       json={"khach_ten": "Khách của sale", "dong": []}).status_code == 201


def test_ke_toan_xem_duoc_hop_dong_vi_do_la_can_cu_ghi_doanh_thu():
    assert client.get("/api/v1/ban-hang/hop-dong", headers=login("ketoan")).status_code == 200
    # nhưng không soạn báo giá – đó là việc của kinh doanh
    assert client.post("/api/v1/ban-hang/bao-gia", headers=login("ketoan"),
                       json={"khach_ten": "x", "dong": []}).status_code == 403


# ====================== 7. BẢNG GIÁ CÒN HIỆU LỰC ======================
def test_hieu_luc_den_RONG_nghia_la_CON_hieu_luc():
    """Chỗ dễ viết nhầm thành ngày hôm nay và làm mọi bảng giá tự tắt sau một đêm."""
    from app.db.session import SessionLocal
    from app.services import ban_hang as BH
    from app.models.ban_hang import BangGia
    with SessionLocal() as db:
        b = BangGia(ma="BG-THU-RONG", ten="thử rỗng", product_id=999_999,
                    hieu_luc_tu=date.today() - timedelta(days=400), hieu_luc_den=None)
        db.add(b); db.commit()
        assert BH.bang_gia_hieu_luc(db, 999_999) is not None
        assert BH.bang_gia_hieu_luc(db, 999_999, date.today() + timedelta(days=3650)) is not None


def test_bang_gia_het_han_thi_khong_con_hieu_luc():
    from app.db.session import SessionLocal
    from app.services import ban_hang as BH
    from app.models.ban_hang import BangGia
    with SessionLocal() as db:
        db.add(BangGia(ma="BG-THU-HET", ten="thử hết hạn", product_id=999_998,
                       hieu_luc_tu=date.today() - timedelta(days=40),
                       hieu_luc_den=date.today() - timedelta(days=1)))
        db.commit()
        assert BH.bang_gia_hieu_luc(db, 999_998) is None


# ====================== 8. SỬA BÁO GIÁ KHÔNG ĐƯỢC XÓA KHÓA LIÊN KẾT ======================
def test_sua_bao_gia_khong_xoa_lead_id_va_company_id():
    """Lỗ hổng tìm ra khi dựng màn hình soạn 09/9: PUT gán cả trường người gọi KHÔNG gửi.

    Vòng lặp cũ `setattr(bg, k, getattr(data, k))` chạy trên mọi trường; những trường có mặc định None
    (lead_id, company_id) bị gán None ngay cả khi màn hình chỉ sửa tên khách. Mất lặng lẽ – không lỗi,
    không cảnh báo – và chỉ lộ ra lúc đi tìm báo giá này đến từ nguồn khách nào.

    Phép thử này đứng ở chiều nguy hiểm: sửa MỘT trường rồi đòi mọi trường khác còn nguyên.
    """
    h = login("nv_kd")
    r = client.post("/api/v1/ban-hang/bao-gia", headers=h, json={
        "khach_ten": "Khách giữ khóa", "mang": "kd_le", "lead_id": 1, "company_id": 1,
        "so_khach": 2, "dong": [{"hang_khach": "nguoi_lon", "mo_ta": "tour", "so_luong": 2,
                                 "don_gia": 5_000_000, "gia_von_don_vi": 3_000_000}]})
    assert r.status_code == 201, r.text
    bid = r.json()["id"]

    truoc = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=h).json()
    assert truoc["lead_id"] == 1 and truoc["company_id"] == 1, truoc

    # Màn hình soạn chỉ gửi những gì nó có: tên khách, số khách, dòng. Không gửi lead_id/company_id.
    r = client.put(f"/api/v1/ban-hang/bao-gia/{bid}", headers=h, json={
        "khach_ten": "Khách giữ khóa (đã sửa tên)", "mang": "kd_le", "so_khach": 3,
        "phien_ban": truoc["phien_ban"],
        "dong": [{"hang_khach": "nguoi_lon", "mo_ta": "tour", "so_luong": 3,
                  "don_gia": 5_000_000, "gia_von_don_vi": 3_000_000}]})
    assert r.status_code == 200, r.text

    sau = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=h).json()
    assert sau["khach_ten"] == "Khách giữ khóa (đã sửa tên)"
    assert sau["so_khach"] == 3
    assert sau["lead_id"] == 1, "PUT đã xóa lead_id dù người gọi không gửi trường đó"
    assert sau["company_id"] == 1, "PUT đã xóa company_id dù người gọi không gửi trường đó"


def test_sua_bao_gia_van_xoa_duoc_khoa_khi_NGUOI_GOI_co_y_gui_null():
    """Chiều ngược lại: gửi thẳng null vẫn phải xóa được – nếu không thì gỡ liên kết thành không làm được."""
    h = login("nv_kd")
    bid = client.post("/api/v1/ban-hang/bao-gia", headers=h, json={
        "khach_ten": "Khách gỡ khóa", "mang": "kd_le", "lead_id": 1,
        "dong": [{"hang_khach": "nguoi_lon", "mo_ta": "x", "so_luong": 1, "don_gia": 1_000_000,
                  "gia_von_don_vi": 500_000}]}).json()["id"]
    pb = client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=h).json()["phien_ban"]
    r = client.put(f"/api/v1/ban-hang/bao-gia/{bid}", headers=h, json={
        "khach_ten": "Khách gỡ khóa", "mang": "kd_le", "lead_id": None, "phien_ban": pb, "dong": []})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/v1/ban-hang/bao-gia/{bid}", headers=h).json()["lead_id"] is None


# ====================== 9. NỐI BÁO GIÁ VỚI DỰ TOÁN TOUR ======================
def _tour_co_du_toan(ma: str, dong: list[dict]) -> int:
    """Dựng một tour và mấy dòng dự toán. Trả về id tour."""
    from app.db.session import SessionLocal
    from app.models.core import Tour, User
    from app.models.vietrip import TourCostLine
    with SessionLocal() as db:
        dh = db.execute(select(User).where(User.role == "nv_dh")).scalars().first()
        t = Tour(code=ma, name="Tour thử nối dự toán", tour_type="le_noi_dia",
                 start_date=date.today() + timedelta(days=20),
                 end_date=date.today() + timedelta(days=23),
                 operator_id=(dh.id if dh else 1), price_per_pax=0, planned_pax=10,
                 status="da_duyet")
        db.add(t); db.flush()
        for i, d in enumerate(dong):
            db.add(TourCostLine(tour_id=t.id, line_no=i + 1, description=d.get("mo_ta", f"dòng {i}"),
                                cost_kind=d.get("kieu", "co_dinh"), unit_price=d.get("don_gia", 0),
                                qty=d.get("sl", 1), coef=d.get("he_so", 1),
                                budget=d.get("du_toan", 0), status="hd"))
        db.commit()
        return t.id


def test_tour_chua_co_du_toan_thi_gia_von_la_RONG_khong_phai_0():
    """Điều luật học bằng giá đắt, lần này ở cửa mới: thiếu dự toán KHÔNG PHẢI dự toán bằng 0.

    Nếu cửa này trả 0 thì báo giá gắn một tour chưa ai tính giá vốn sẽ cho biên 100% và cổng biên báo
    ĐẠT – đúng cái mà cổng sinh ra để chặn, bị vô hiệu hóa bằng một tiện ích.
    """
    tid = _tour_co_du_toan("V6-DT-TRONG", [])
    r = client.get(f"/api/v1/ban-hang/tour/{tid}/gia-von?so_khach=10", headers=login("nv_kd"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["co_du_toan"] is False
    assert d["gia_von_moi_khach"] is None, f"phải là RỖNG, đang trả {d['gia_von_moi_khach']!r}"


def test_gia_von_moi_khach_chia_dung_co_dinh_va_theo_khach():
    """Cố định chia cho số khách; theo khách thì KHÔNG nhân số lượng lần nữa (nhân hai lần)."""
    tid = _tour_co_du_toan("V6-DT-CO", [
        {"mo_ta": "Thuê xe 45 chỗ", "kieu": "co_dinh", "du_toan": 10_000_000},
        {"mo_ta": "Ăn trưa", "kieu": "theo_khach", "don_gia": 500_000, "sl": 10, "he_so": 1},
    ])
    d = client.get(f"/api/v1/ban-hang/tour/{tid}/gia-von?so_khach=10",
                   headers=login("nv_kd")).json()
    assert d["co_du_toan"] is True and d["so_dong"] == 2
    assert d["co_dinh"] == 10_000_000
    assert d["theo_khach_moi_khach"] == 500_000, "dòng theo khách bị nhân số lượng lần nữa"
    assert d["gia_von_moi_khach"] == 1_500_000, d


def test_cua_gia_von_tour_KHONG_lo_ten_nha_cung_cap():
    """Người soạn báo giá không nằm trong COST_ROLES. Cửa này trả một con số tổng, không trả cơ cấu.

    Mở cả cơ cấu chi phí tour cho phòng kinh doanh là một quyết định về QUYỀN – việc của robot Phân
    quyền. Phép thử này đứng đây để lần sau ai đó thêm 'cho tiện' thì nó đỏ.
    """
    tid = _tour_co_du_toan("V6-DT-NCC", [
        {"mo_ta": "Khách sạn Mường Thanh", "kieu": "co_dinh", "du_toan": 20_000_000}])
    d = client.get(f"/api/v1/ban-hang/tour/{tid}/gia-von?so_khach=10", headers=login("nv_kd")).json()
    assert "dong" not in d and "rows" not in d, "cửa này không được trả dòng chi tiết"
    assert "Mường Thanh" not in str(d.get("dong_chua_co_so_tien", "")), d
    for khoa in ("supplier_name", "supplier_tax_code", "unit_price"):
        assert khoa not in str(d), f"lộ trường {khoa}"


def test_danh_sach_tour_de_chon_khong_kem_so_tien():
    d = client.get("/api/v1/ban-hang/tour-de-chon", headers=login("nv_kd")).json()
    assert isinstance(d, list)
    if d:
        assert set(d[0].keys()) == {"id", "code", "name", "start_date"}, d[0]
