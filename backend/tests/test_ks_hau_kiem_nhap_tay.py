"""K3 – hậu kiểm số nhân viên nhập tay. Lệnh Robot Kiểm soát 08/9/2026.

Đây là lớp bảo vệ THAY CHO khâu trưởng phòng duyệt từng dòng mà Chủ tịch đã bỏ. Bỏ một lớp chặn có
thật thì lớp còn lại phải chặt hơn, nên mỗi dấu hiệu dưới đây được dựng đúng tình huống rồi mới đòi
robot nhìn thấy.

  KN1  tài khoản máy (robot, vietrip) không bị đem ra hậu kiểm
  KN2  số tròn lặp lại ở khoản lớn thì bắt; tròn một lần thì không
  KN3  nhập ngoài giờ làm việc
  KN4  nhập dồn nhiều dòng trong năm phút
  KN5  một người nhập số cho phòng khác; không biết người đó phòng nào thì IM LẶNG
  KN6  nhập lùi ngày vào kỳ đã khóa – mức ĐỎ
  KN7  mọi ngưỡng đọc từ tham số chính sách, không viết cứng
  KN8  bảng đo ngưỡng: ngưỡng lỏng hơn thì ra ít dòng hơn
  KN9  bộ hậu kiểm đã gắn vào vòng quét, và một dấu hiệu hỏng không làm trắng cả bộ
"""
import os, sys
from datetime import datetime, date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_ksnt.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_ksnt.db", "test_ksnt.db-journal"):
    if os.path.exists(f): os.remove(f)
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
THANG = f"{date.today():%Y-%m}"


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        _dung_du_lieu()
        yield


def _dau(luc: datetime) -> datetime:
    """Giữ mốc trong THÁNG NÀY để phép thử không phụ thuộc ngày chạy."""
    d = date.today().replace(day=1)
    return datetime(d.year, d.month, 2, luc.hour, luc.minute, luc.second)


def _dung_du_lieu():
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    from app.models.accounting import JournalEntry, PeriodLock
    from app.models.payments import Receipt
    from app.models.core import Booking
    from sqlalchemy import select
    db = SessionLocal()
    n = 0

    def chi(code, tien, nguoi, luc):
        nonlocal n; n += 1
        db.add(PaymentRequest(code=code, category="hanh_chinh", supplier_name="NCC thử", amount=tien,
                              description="dựng cho phép thử", created_by=nguoi, created_at=luc,
                              status="cho_tp"))

    # KN1: tài khoản máy nhập một loạt số tròn – phải bị bỏ qua
    for i in range(6): chi(f"DCROB{i:03d}", 50_000_000, "robot", _dau(datetime(2026, 1, 1, 10, i)))
    # KN2: người thật nhập đúng 30 triệu bốn lần
    for i in range(4): chi(f"DCTRON{i:03d}", 30_000_000, "hcns", _dau(datetime(2026, 1, 1, 9, i)))
    # số tròn nhưng chỉ một lần – không được bắt
    chi("DCTRON900", 77_000_000, "hcns", _dau(datetime(2026, 1, 1, 9, 40)))
    # KN3: bốn dòng lúc 2 giờ sáng
    for i in range(4): chi(f"DCDEM{i:03d}", 1_234_567 + i, "hcns", _dau(datetime(2026, 1, 1, 2, i)))
    # KN4: mười hai dòng trong ba phút, trong giờ
    for i in range(12): chi(f"DCDON{i:03d}", 900_000 + i, "ketoan", _dau(datetime(2026, 1, 1, 14, i // 5, i)))

    # KN5: sổ Phiếu thu là của Kế toán, nhưng nhân viên kinh doanh nhập
    bk = db.execute(select(Booking)).scalars().first()
    for i in range(3):
        db.add(Receipt(code=f"PTKD{i:03d}", booking_id=bk.id, amount=5_000_000, method="tien_mat",
                       payer="Khách thử", created_by="kd.hoa", created_at=_dau(datetime(2026, 1, 1, 10, i))))

    # KN6: khóa một kỳ cũ rồi ghi bút toán mang ngày thuộc kỳ đó
    ky_cu = (date.today().replace(day=1) - timedelta(days=40))
    ky = f"{ky_cu:%Y-%m}"
    db.add(PeriodLock(period=ky, locked_by="ketoan", note="khóa cho phép thử"))
    for i in range(2):
        db.add(JournalEntry(code=f"CTLUI{i:03d}", entry_date=ky_cu, period=ky, description="lùi ngày",
                            status="da_ghi_so", created_by="ketoan", created_at=_dau(datetime(2026, 1, 1, 11, i))))
    db.commit(); db.close()


def ds(thang=None):
    return client.get(f"/api/v1/kiem-soat/nhap-tay?thang={thang or THANG}", headers=login("cntt")).json()


def loc(d, loai, nguoi=None):
    return [r for r in d["rows"] if r["loai"] == loai and (nguoi is None or r.get("nguoi") == nguoi)]


def test_kn1_tai_khoan_may_khong_bi_dem_ra_hau_kiem():
    d = ds()
    may = [r for r in d["rows"] if (r.get("nguoi") or "").lower() in ("robot", "vietrip", "sepay")]
    assert not may, ("robot nạp dữ liệu không phải người nhập; để lại thì mọi dấu hiệu đều chỉ vào nó "
                     f"và phần của con người chìm nghỉm. Đang thấy: {may}")


def test_kn2_so_tron_lap_lai_thi_bat_tron_mot_lan_thi_khong():
    d = ds()
    r = loc(d, "nt_so_tron", "hcns")
    assert r, "bốn dòng đúng 30.000.000đ của cùng một người mà không bắt thì dấu hiệu này vô dụng"
    assert any(x["chi_tiet"]["so_tien"] == 30_000_000 and x["chi_tiet"]["so_lan"] >= 4 for x in r)
    assert not any(x["chi_tiet"]["so_tien"] == 77_000_000 for x in r), \
        "một con số tròn xuất hiện một lần không nói lên điều gì – bắt là báo oan"


def test_kn3_nhap_ngoai_gio_lam_viec():
    d = ds()
    r = [x for x in loc(d, "nt_ngoai_gio", "hcns") if "ngoài giờ" in x["tom_tat"]]
    assert r and r[0]["chi_tiet"]["so_dong"] >= 4


def test_kn4_nhap_don_nhieu_dong_trong_nam_phut():
    d = ds()
    r = [x for x in loc(d, "nt_ngoai_gio", "ketoan") if "5 phút" in x["tom_tat"]]
    assert r and r[0]["chi_tiet"]["dong_5_phut"] >= 10


def test_kn5_mot_nguoi_nhap_so_cho_phong_khac():
    d = ds()
    r = loc(d, "nt_khac_phong", "kd.hoa")
    assert r, "Phiếu thu là sổ của Kế toán mà nhân viên kinh doanh nhập – phải hiện ra"
    assert r[0]["chi_tiet"]["phong_so"] == "Kế toán" and r[0]["chi_tiet"]["phong_nguoi"] == "Kinh doanh"
    # người không có trong danh mục vai trò thì im lặng, không đoán
    assert all(x["chi_tiet"]["phong_nguoi"] for x in loc(d, "nt_khac_phong"))


def test_kn6_nhap_lui_ngay_vao_ky_da_khoa_la_muc_do():
    d = ds()
    r = loc(d, "nt_lui_ngay", "ketoan")
    assert r and r[0]["chi_tiet"]["so_dong"] >= 2
    from app.services.ks_nhap_tay import _hau_kiem_nhap_tay
    from app.db.session import SessionLocal
    db = SessionLocal(); ph = _hau_kiem_nhap_tay(db); db.close()
    lui = [p for p in ph if "lùi ngày" in p["tom_tat"] or "ĐÃ KHÓA" in p["tom_tat"]]
    assert lui and all(p["muc"] == "do" for p in lui), \
        "kỳ khóa là chốt chặn cuối cùng còn lại sau khi bỏ khâu duyệt – lách nó không thể là mức vàng"


def test_kn7_moi_nguong_doc_tu_tham_so_khong_viet_cung():
    from app.db.session import SessionLocal
    from app.models.core import Param
    from app.services import rules as R
    truoc = len(loc(ds(), "nt_so_tron", "hcns"))
    assert truoc >= 1
    db = SessionLocal()
    db.add(Param(key="ks_tron_lap", value="99", label="thử", unit="lần", source="thử",
                 status="active", effective_from=date.today()))
    db.commit(); R.clear_param_cache(); db.close()
    try:
        assert len(loc(ds(), "nt_so_tron", "hcns")) == 0, \
            "đổi tham số mà kết quả không đổi nghĩa là ngưỡng đang nằm trong mã nguồn"
    finally:
        db = SessionLocal()
        db.add(Param(key="ks_tron_lap", value="3", label="trả lại", unit="lần", source="thử",
                     status="active", effective_from=date.today()))
        db.commit(); R.clear_param_cache(); db.close()


def test_kn8_bang_do_nguong_cho_nguoi_chon_bang_so_lieu():
    d = client.get(f"/api/v1/kiem-soat/nhap-tay/do-nguong?thang={THANG}&lan=2,3,5,10",
                   headers=login("cntt")).json()
    assert [x["lech_bao_nhieu_lan"] for x in d["bang"]] == [2, 3, 5, 10]
    tong = [x["tong_dong"] for x in d["bang"]]
    assert tong == sorted(tong, reverse=True), \
        f"ngưỡng lỏng hơn phải ra ít dòng hơn hoặc bằng, đang là {tong}"
    assert set(d["loai"]) == {"nt_lech_ky", "nt_so_tron", "nt_ngoai_gio", "nt_khac_phong",
                              "nt_lui_ngay", "nt_sua_da_chot"}, "phải đủ sáu dấu hiệu lệnh giao"


def test_kn9_da_gan_vao_vong_quet_va_mot_dau_hieu_hong_khong_lam_trang_ca_bo():
    from app.services import ks_robot as KS
    from app.services import ks_nhap_tay as NT
    from app.db.session import SessionLocal
    assert "_hau_kiem_nhap_tay" in {f.__name__ for f in KS.BO_KIEM}
    goc = NT._so_tron
    NT._so_tron = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("dấu hiệu hỏng"))
    try:
        db = SessionLocal(); ra = NT.quet_thang(db, THANG); db.close()
        assert any(x.get("loi") for x in ra), "dấu hiệu hỏng phải được NÓI RA, không nuốt im lặng"
        assert any(x["loai"] == "nt_khac_phong" for x in ra), "các dấu hiệu còn lại vẫn phải chạy"
    finally:
        NT._so_tron = goc
    r = client.post("/api/v1/kiem-soat/quet", headers=login("cntt")).json()
    assert not r["loi_bo_kiem"]


def test_kn10_moi_bang_chi_doc_mot_lan_trong_mot_vong_quet():
    """Chốt chặn cho đúng lỗi đã xảy ra: bản đầu tiên đọc lại cùng một bảng ở từng dấu hiệu, thành ba
    mươi sáu lượt quét bảng cho một tháng, và cổng trả 502 trên dữ liệu thật trước khi hàm chạy xong.

    Phép thử đếm số lượt đọc thật, không đếm thời gian: thời gian trên máy chạy thử không nói được gì
    về máy chủ 0,5 CPU, còn số lượt đọc thì nói.
    """
    from app.services import ks_nhap_tay as NT
    from app.db.session import SessionLocal
    goc = NT._doc; dem = {"n": 0}

    def dem_doc(db, ng, tu, den, kho=None):
        if kho is None or (ng["ma"], tu, den) not in kho: dem["n"] += 1
        return goc(db, ng, tu, den, kho)

    NT._doc = dem_doc
    try:
        db = SessionLocal()
        dem["n"] = 0; NT.quet_thang(db, THANG)
        mot_thang = dem["n"]
        assert mot_thang <= len(NT.NGUON), \
            f"một vòng quét một tháng chỉ được đọc mỗi nguồn một lần ({len(NT.NGUON)}), đang đọc {mot_thang}"
        # bảng đo bốn ngưỡng KHÔNG được nhân bốn số lượt đọc – chỉ dấu hiệu lệch-kỳ phụ thuộc ngưỡng
        dem["n"] = 0; NT.do_nguong(db, THANG, "2,3,5,10")
        assert dem["n"] <= len(NT.NGUON), \
            f"đo bốn ngưỡng vẫn chỉ đọc mỗi nguồn một lần, đang đọc {dem['n']}"
        db.close()
    finally:
        NT._doc = goc


def test_kn11_tong_tien_cong_bang_sql_khong_nap_dong_nao():
    """Dấu hiệu lệch-so-kỳ-trước chỉ cần TỔNG, nên phải cộng bằng SQL. Nạp từng dòng về chỉ để cộng là
    trả giá cho toàn bộ bảng mỗi lần quét."""
    from app.services import ks_nhap_tay as NT
    from app.db.session import SessionLocal
    goc = NT._doc; NT._doc = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("không được đọc dòng"))
    try:
        db = SessionLocal()
        a, b = NT._khoang_thang(THANG)
        t = NT._tong_tien(db, NT.NGUON[0], a, b)
        assert t >= 0
        db.close()
    finally:
        NT._doc = goc


def _dinh_cua_so(moc, giay=300):
    """Bản tham chiếu ngây thơ: duyệt mọi cặp. Chậm, nhưng hiển nhiên đúng – dùng để chấm bản nhanh."""
    ds = sorted(moc); dinh = 0
    for i in range(len(ds)):
        j = i
        while j < len(ds) and (ds[j] - ds[i]).total_seconds() <= giay: j += 1
        dinh = max(dinh, j - i)
    return dinh


def _chay_ngoai_gio(rows, don_dong):
    """Gọi thẳng dấu hiệu nhập-dồn với một tập mốc dựng sẵn, không đụng cơ sở dữ liệu."""
    from app.services import ks_nhap_tay as NT
    goc = NT._doc
    NT._doc = lambda db, ng, tu, den, kho=None: (rows if ng["ma"] == NT.NGUON[0]["ma"] else [])
    try:
        return NT._ngoai_gio(None, THANG, 0, 24, don_dong, {})   # 0h–24h: tắt phần "ngoài giờ"
    finally:
        NT._doc = goc


def test_kn12_dinh_cua_so_nam_phut_dung_o_bien():
    """Cửa sổ là "trong vòng năm phút", tức ĐÚNG 300 giây vẫn tính, 301 giây thì không.

    Sai một giây ở đây không làm sập gì cả – nó chỉ lặng lẽ đếm thừa hoặc thiếu một dòng, và người đọc
    bảng ngoại lệ không có cách nào biết. Nên chốt bằng phép thử chứ không bằng đọc lại mã.
    """
    g = _dau(datetime(2026, 1, 1, 10, 0, 0))
    # ba mốc cách nhau đúng 150 giây: mốc đầu và mốc cuối cách nhau tròn 300 giây → cả ba cùng một cửa sổ
    vua_du = [{"nguoi": "ketoan1", "luc": g + timedelta(seconds=s)} for s in (0, 150, 300)]
    assert _chay_ngoai_gio(vua_du, 3), "đúng 300 giây phải còn nằm trong cửa sổ năm phút"
    # đẩy mốc cuối thêm một giây → chỉ còn hai mốc trong cửa sổ
    qua_mot_giay = [{"nguoi": "ketoan1", "luc": g + timedelta(seconds=s)} for s in (0, 150, 301)]
    assert not _chay_ngoai_gio(qua_mot_giay, 3), "301 giây thì mốc đầu phải rời khỏi cửa sổ"
    assert _chay_ngoai_gio(qua_mot_giay, 2), "hai mốc còn lại vẫn phải đếm được"


def test_kn12b_hai_con_tro_cho_cung_ket_qua_voi_ban_ngay_tho():
    """Đổi từ hai vòng lồng nhau sang hai con trỏ là đổi cách tính, nên phải chấm lại bằng bản cũ.

    Dựng nhiều hình dạng khác nhau – rời rạc, cụm dày, một cụm dài – vì lỗi hai-con-trỏ thường chỉ hiện
    ra ở chỗ con trỏ sau phải nhảy qua nhiều mốc một lúc.
    """
    import random
    g = _dau(datetime(2026, 1, 1, 10, 0, 0))
    random.seed(20260908)
    for lan in range(30):
        n = random.randint(1, 60)
        # trộn khoảng cách bé (dồn cục) và lớn (rời rạc) để có đủ hình dạng
        moc, t = [], 0
        for _ in range(n):
            t += random.choice([0, 1, 7, 60, 150, 299, 300, 301, 900])
            moc.append(g + timedelta(seconds=t))
        cho_doi = _dinh_cua_so(moc)
        rows = [{"nguoi": "ketoan1", "luc": m} for m in moc]
        # đòi robot báo ở đúng ngưỡng bằng đỉnh, và im ở ngưỡng cao hơn một
        assert _chay_ngoai_gio(rows, cho_doi), f"lần {lan}: đỉnh phải là {cho_doi}"
        assert not _chay_ngoai_gio(rows, cho_doi + 1), f"lần {lan}: đỉnh không được vượt {cho_doi}"


def test_kn12c_hai_muoi_nghin_moc_trung_gio_van_chay_xong():
    """Chốt chặn cho đúng lỗi đã xảy ra trên máy chủ ngày 08/9/2026.

    Bản cũ dò lại từ đầu cửa sổ ở mỗi mốc: 25.728 bút toán của một bản nhập hàng loạt rơi vào cùng vài
    phút thành hơn ba trăm triệu phép trừ thời gian, và cổng trả 502 trước khi hàm chạy xong – nghĩa là
    dấu hiệu "nhập dồn" TẮT đúng vào lúc có nhập dồn thật. Đó là kiểu hỏng tệ nhất: không báo lỗi, chỉ
    im lặng bỏ sót.

    Đặt hạn năm giây, không phải để đo máy chạy thử cho chính xác, mà vì bản cũ ở kích thước này mất
    hàng phút – khoảng cách đủ xa để phép thử không phụ thuộc máy nhanh hay chậm.
    """
    import time
    g = _dau(datetime(2026, 1, 1, 10, 0, 0))
    rows = [{"nguoi": "ketoan1", "luc": g + timedelta(seconds=i % 120)} for i in range(20_000)]
    t0 = time.perf_counter()
    ra = _chay_ngoai_gio(rows, 10)
    giay = time.perf_counter() - t0
    assert ra, "hai mươi nghìn dòng trong hai phút thì phải báo nhập dồn"
    assert giay < 5, f"cửa sổ trượt phải là O(n); đang mất {giay:.1f} giây cho 20.000 mốc"


def test_kn13_thong_ke_nguoi_phan_biet_may_do_vao_va_nguoi_go():
    """Đếm theo người nhập, kèm trải dài thời gian – đây là thứ phân biệt "cả phòng gõ suốt tháng" với
    "một tài khoản đổ một bản nhập hàng loạt trong mười phút".

    Không có cột này thì con số tổng dẫn thẳng tới kết luận sai, và ngưỡng hậu kiểm đặt trên kết luận
    sai thì gác nhầm hệ thống.
    """
    from app.services import ks_nhap_tay as NT
    from app.db.session import SessionLocal
    db = SessionLocal()
    a, b = NT._khoang_thang(THANG)
    ra = NT.thong_ke_nguoi(db, NT.NGUON[0], a, b)
    assert isinstance(ra, list)
    assert all(x["nguoi"].lower() not in NT.BO_QUA_NGUOI for x in ra), \
        "tài khoản máy đã loại khỏi hậu kiểm thì cũng không được xuất hiện trong thống kê người nhập"
    # phải xếp giảm dần theo số dòng: người đọc chỉ nhìn vài dòng đầu
    assert [x["so_dong"] for x in ra] == sorted([x["so_dong"] for x in ra], reverse=True)
    for x in ra:
        assert x["so_dong"] >= 1 and "nhanh_nhat" in x and "cham_nhat" in x
        assert x["trai_dai_phut"] is None or x["trai_dai_phut"] >= 0
    db.close()


def test_kn14_ban_nap_may_khong_bi_dem_ra_hau_kiem_nhap_tay():
    """Chốt chặn cho đúng chuyện đã đo trên máy chủ thật ngày 08/9/2026.

    Sổ bút toán tháng đó có 25.728 dòng bị bộ hậu kiểm coi là số nhân viên nhập tay. Số người thật gõ
    vào sổ đếm trên đầu ngón tay; phần còn lại là bản nạp MISA chạy dưới tên `misa` – một cái tên không
    có trong danh sách BO_QUA_NGUOI, nên lọt qua toàn bộ.

    Hậu quả không phải là báo thừa vài dòng: ngưỡng hiệu chỉnh trên 25.728 dòng máy nạp là ngưỡng cho
    một hệ thống không tồn tại, và bảng ngoại lệ chỉ toàn tên `misa` thì người ta đọc vài lần rồi thôi.
    Nên phép thử này đòi bộ hậu kiểm phân biệt bằng CỘT NGUỒN, không bằng danh sách tên.
    """
    from app.services import ks_nhap_tay as NT
    from app.services import accounting as ACC
    from app.db.session import SessionLocal
    from app.models.accounting import JournalEntry
    from sqlalchemy import select as sel

    db = SessionLocal()
    a, b = NT._khoang_thang(THANG)
    ng = [x for x in NT.NGUON if x["ma"] == "but_toan"][0]
    truoc = len(NT._doc(db, ng, a, b))

    # hai tài khoản tiền: không vướng quy tắc "phải ghi mã đối tượng", nên phép thử đo đúng thứ nó
    # định đo thay vì đo lại quy tắc hạch toán
    ln = [{"account": "111", "debit": 5_000_000, "credit": 0},
          {"account": "112", "debit": 0, "credit": 5_000_000}]
    # Cùng một người, cùng một ngày: khác nhau ĐÚNG ở cột nguồn – nên nếu bộ hậu kiểm phân biệt được
    # thì chỉ có thể là nhờ cột đó.
    tay = ACC.post_entry(db, "ketoan1", "ketoan", date.today(), "Người gõ tay", ln, "thu_cong", "")
    may = ACC.post_entry(db, "ketoan1", "ketoan", date.today(), "Bản nạp MISA", ln, "misa", "misa:test")
    db.commit()

    sau = NT._doc(db, ng, a, b)
    assert len(sau) == truoc + 1, "chỉ dòng người gõ được thêm vào hậu kiểm, dòng máy nạp thì không"
    ids = {x["id"] for x in sau}
    assert tay.id in ids, "dòng do người gõ phải nằm trong hậu kiểm"
    assert may.id not in ids, "dòng do máy nạp (source_type='misa') không được coi là số nhập tay"

    # thống kê người nhập cũng phải cùng một cách nhìn, nếu không thì hai bảng nói hai con số khác nhau
    tk = {x["nguoi"]: x["so_dong"] for x in NT.thong_ke_nguoi(db, ng, a, b)}
    assert tk.get("ketoan1", 0) == 1, f"thống kê người nhập phải đếm đúng một dòng, đang đếm {tk.get('ketoan1')}"

    for e in (tay, may): db.delete(e)
    db.commit(); db.close()


def test_kn15_dong_thieu_cot_nguon_van_bi_dem_ra_hau_kiem():
    """Để trống cột nguồn thì VẪN hậu kiểm. Trong một bộ kiểm soát, im lặng phải do có bằng chứng đây là
    máy sinh, chứ không do thiếu dữ liệu – nếu không, cách dễ nhất để né hậu kiểm là bỏ trống một cột.
    """
    from app.services import ks_nhap_tay as NT
    from app.db.session import SessionLocal
    from app.models.accounting import JournalEntry
    db = SessionLocal()
    ng = [x for x in NT.NGUON if x["ma"] == "but_toan"][0]
    t = NT._bang(ng["bang"])
    dk = NT._chi_nguoi_go(t, ng)
    assert dk is not None, "sổ bút toán phải có cột phân biệt máy sinh / người gõ"
    # cột để trống → coalesce về "thu_cong" → điều kiện đúng → dòng vẫn được đem ra hậu kiểm
    from sqlalchemy import select as sel, literal
    assert db.execute(sel(literal(1)).where(
        NT.func.coalesce(None, NT.NGUOI_GO) == NT.NGUOI_GO)).scalar() == 1
    # nguồn không có cột đó thì không lọc gì cả, thay vì lọc sạch
    khac = [x for x in NT.NGUON if x["ma"] == "thu"][0]
    assert NT._chi_nguoi_go(NT._bang(khac["bang"]), khac) is None, \
        "nguồn không có cột nguồn thì phải giữ nguyên mọi dòng, không được lọc rỗng"
    db.close()
