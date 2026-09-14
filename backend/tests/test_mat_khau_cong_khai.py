# -*- coding: utf-8 -*-
"""MẬT KHẨU ĐÃ CÔNG KHAI — bắt ở cửa đăng nhập, và bật cờ cho tài khoản chưa ai dùng.

CHỖ HỎNG THẬT, NGÀY 14/9/2026

Trang đăng nhập của bản chạy trên internet công cộng in thẳng ra màn hình rằng mười hai tài khoản
mẫu — kể cả `chutich`, `tgd`, `ketoan` — dùng chung một mật khẩu, và in luôn mật khẩu ấy ra.

CHỖ HỎNG THỨ HAI, CÙNG NGÀY, DO BẢN VÁ THỨ NHẤT ĐẺ RA

Bản vá đầu giải bài bằng cách QUÉT: duyệt mọi tài khoản đang hoạt động, mỗi tài khoản gọi
`verify_password` một lần. Bộ thử lúc ấy dựng NĂM tài khoản nên nó xanh trong một giây. Bản thật có
116 tài khoản và màn hình Tài khoản treo hơn hai phút — bcrypt chậm là CỐ Ý (0,274 giây/lần đo trên
máy dựng), và phép quét ấy chạy mỗi lần có người mở màn hình.

Nên bộ thử này có hai thứ bộ thử cũ không có:

  * MK2 đếm số lần băm ở đường TẢI TRANG và đòi bằng KHÔNG — không phải "nhanh", mà là không băm.
  * MK11 dựng ĐÚNG 116 tài khoản như bản thật. Phép thử năm tài khoản không nói gì về 116 tài khoản.

  MK1   tóm tắt ra ĐÚNG những tài khoản chưa từng đăng nhập
  MK2   tải trang KHÔNG băm một lần nào, kể cả với 116 tài khoản
  MK3   tóm tắt không đổi gì, và không trả về mật khẩu của ai
  MK4   bật cờ mặc định chỉ XEM TRƯỚC
  MK5   bật cờ xong thì cờ lên đúng người, không đụng người đã dùng tài khoản
  MK6   cờ lên là chặn thật — mọi đường trừ ba đường được phép
  MK7   ĐĂNG NHẬP bằng mật khẩu đã công bố thì bị bật cờ NGAY, trong chính lần đăng nhập ấy
  MK8   đăng nhập bằng mật khẩu tử tế thì không bị làm phiền
  MK9   không đặt lại được chính mật khẩu đã công khai
  MK10  không đặt được mật khẩu quá dễ đoán, quá ngắn, hay chứa thứ người khác biết
  MK11  116 tài khoản: tải trang vẫn rẻ
  MK12  trang đăng nhập KHÔNG in tài khoản hay mật khẩu nào
"""
import os
import sys
import time
from datetime import datetime

os.environ["DATABASE_URL"] = "sqlite:///./test_matkhau.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_matkhau.db", "test_matkhau.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import bcrypt                                                         # noqa: E402
import pytest                                                         # noqa: E402
from fastapi.testclient import TestClient                             # noqa: E402

import app.models                                                     # noqa: E402,F401
from app.core.security import hash_password, verify_password          # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
from app.models.core import User                                      # noqa: E402
from app.services import mat_khau_yeu as MKY                          # noqa: E402
# PHẢI đứng SAU `import app.models`: `import app.models` gán lại tên `app` về chính gói, nên đặt
# trước thì `app` không còn là ứng dụng FastAPI nữa và TestClient nhận vào một module.
from app.main import app                                              # noqa: E402

Base.metadata.create_all(engine)
client = TestClient(app)

CONG_KHAI = MKY.DA_CONG_KHAI[0]
TU_TE = "Bien!Dong2026"

# Băm MỘT LẦN rồi dùng lại cho các tài khoản độn. `hash_password` cũng là bcrypt và cũng chậm bằng
# đúng chừng ấy: băm 116 lần trong fixture là tự bắt bộ thử trả cái giá mà phép thử này sinh ra để
# canh. Những tài khoản độn không bao giờ bị thử mật khẩu nên dùng chung một chuỗi băm là đủ.
BAM_SAN = hash_password(CONG_KHAI)


def _dat_lai(s):
    s.query(User).delete()
    s.commit()


@pytest.fixture()
def db():
    s = SessionLocal()
    _dat_lai(s)
    # Ba tài khoản CHƯA TỪNG ĐĂNG NHẬP (last_login rỗng) — mật khẩu còn nguyên như lúc gieo.
    for u, ten, vai in (("chutich", "Chủ tịch HĐQT", "chutich"),
                        ("ketoan", "Kế toán trưởng", "ketoan"),
                        ("kd.hoa", "Nguyễn Thị Hoa", "nv_kd")):
        s.add(User(username=u, full_name=ten, role=vai, staff_code="NS0001",
                   password_hash=BAM_SAN, active=True))
    # Một người ĐÃ dùng tài khoản: cửa đăng nhập lo người này, không phải cái nút.
    s.add(User(username="dadung", full_name="Trần Đã Dùng", role="nv_kd", staff_code="NS0009",
               password_hash=BAM_SAN, active=True, last_login=datetime(2026, 9, 1, 8, 0)))
    # Một tài khoản đã khoá: không đăng nhập được, không phải việc phải xử.
    s.add(User(username="dakhoa", full_name="Lê Đã Khoá", role="nv_kd", staff_code="NS0010",
               password_hash=BAM_SAN, active=False))
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def dem_bam(monkeypatch):
    """Đếm số lần bcrypt thật sự chạy. Đây là cái cân, không phải cái đồng hồ."""
    that = bcrypt.checkpw
    so = {"n": 0}

    def rinh(pw, h):
        so["n"] += 1
        return that(pw, h)

    monkeypatch.setattr(bcrypt, "checkpw", rinh)
    return so


# ── Tóm tắt (đường TẢI TRANG) ───────────────────────────────────────────────────────────────────

def test_mk1_tom_tat_ra_dung_nhung_tai_khoan_chua_tung_dang_nhap(db):
    kq = MKY.tom_tat(db)
    assert kq["chua_tung_dang_nhap"] == 3, "đếm sai số tài khoản còn nguyên mật khẩu lúc gieo"
    ten = {x["username"] for x in kq["danh_sach"]}
    assert ten == {"chutich", "ketoan", "kd.hoa"}
    assert "dadung" not in ten, "người đã dùng tài khoản do cửa đăng nhập lo, không phải cái nút này"
    assert "dakhoa" not in ten, "tài khoản đã khoá không đăng nhập được, không phải việc phải xử"


def test_mk2_tai_trang_khong_bam_mot_lan_nao(db, dem_bam):
    """Phép thử đắt giá nhất trong tệp này, vì nó là phép thử bộ cũ KHÔNG có.

    Bản 14/9 gọi `verify_password` một lần cho MỖI tài khoản ở đúng đường này. Với năm tài khoản
    trong bộ thử thì không ai thấy gì; với 116 tài khoản thật thì màn hình treo hơn hai phút.

    Phép thử không đo "nhanh" — đo nhanh thì máy dựng bận một hôm là đỏ oan. Nó đếm số lần băm và
    đòi bằng KHÔNG: đó là điều thật sự phải đúng, và nó đúng bất kể máy nhanh hay chậm.
    """
    MKY.tom_tat(db)
    assert dem_bam["n"] == 0, (
        f"đường tải trang băm {dem_bam['n']} lần – bcrypt chậm là cố ý, nhân lên theo số tài khoản "
        "là treo màn hình")


def test_mk3_tom_tat_khong_doi_gi_va_khong_lo_mat_khau(db):
    kq = MKY.tom_tat(db)
    assert all(not u.must_change_password for u in db.query(User).all()), "xem mà đã bật cờ"
    phang = str(kq)
    assert CONG_KHAI not in phang, "kết quả có chứa mật khẩu – không được lộ ra bất kỳ đâu"
    assert BAM_SAN not in phang, "kết quả có chứa bản băm – bản băm cũng là thứ đem đi dò được"
    assert all("password" not in k for k in kq["danh_sach"][0])


# ── Bật cờ ──────────────────────────────────────────────────────────────────────────────────────

def test_mk4_bat_co_mac_dinh_chi_XEM_TRUOC(db):
    kq = MKY.bat_co(db, boi="chutich")
    db.commit()
    assert kq["da_bat"] == 0
    assert all(not u.must_change_password for u in db.query(User).all()), \
        "gọi nhầm một lần là cả công ty bị buộc đổi mật khẩu"


def test_mk5_bat_co_len_dung_nguoi(db):
    MKY.bat_co(db, boi="chutich", xac_nhan=True)
    db.commit()
    co = {u.username: u.must_change_password for u in db.query(User).all()}
    assert co["chutich"] and co["ketoan"] and co["kd.hoa"]
    assert not co["dadung"], "người đã dùng tài khoản bị bắt đổi oan"

    # Bật lần hai: không có gì để bật thêm, và không làm phiền ai.
    assert MKY.bat_co(db, boi="chutich", xac_nhan=True)["da_bat"] == 0


def test_mk6_co_len_la_chan_that(db):
    """Cờ mà không chặn thì nó chỉ là một dòng chữ. Chốt thật nằm ở `deps`."""
    from fastapi import HTTPException

    from app.api.deps import PASSWORD_CHANGE_ALLOWED, check_must_change_password

    MKY.bat_co(db, boi="chutich", xac_nhan=True)
    db.commit()
    u = db.query(User).filter(User.username == "chutich").one()

    for duong in ("/api/v1/tours", "/api/v1/quyet-toan-lop3/kho-cu/nguoi-ban", "/api/v1/access"):
        with pytest.raises(HTTPException) as e:
            check_must_change_password(u, duong)
        assert e.value.status_code == 403 and e.value.detail["gate"] == "DOI_MAT_KHAU"

    # Ba đường phải mở, nếu không người ta không có cách nào tự đổi mật khẩu.
    for duong in PASSWORD_CHANGE_ALLOWED:
        check_must_change_password(u, duong)


# ── Cửa đăng nhập: chỗ máy đang cầm sẵn mật khẩu ────────────────────────────────────────────────

def _nguoi(s, ten: str, mk: str, *, da_dang_nhap: bool):
    s.query(User).filter(User.username == ten).delete()
    s.add(User(username=ten, full_name="Người Thử", role="nv_kd", staff_code="NS0100",
               password_hash=hash_password(mk), active=True,
               last_login=datetime(2026, 9, 1, 8, 0) if da_dang_nhap else None))
    s.commit()


def test_mk7_dang_nhap_bang_mat_khau_da_cong_bo_thi_bi_bat_co_ngay(db, dem_bam):
    """Đây là chỗ bài toán thật sự được giải, và nó không tốn gì.

    Người này ĐÃ TỪNG ĐĂNG NHẬP nên cái nút ở màn hình quản trị không đụng tới họ. Nhưng lúc họ gõ
    mật khẩu, máy cầm sẵn chuỗi ấy trong tay – so một phát là biết chắc.
    """
    _nguoi(db, "quenkhongdoi", CONG_KHAI, da_dang_nhap=True)
    assert MKY.tom_tat(db)["danh_sach"] == [] or "quenkhongdoi" not in {
        x["username"] for x in MKY.tom_tat(db)["danh_sach"]}

    r = client.post("/api/v1/auth/login",
                    data={"username": "quenkhongdoi", "password": CONG_KHAI})
    assert r.status_code == 200, r.text

    # Hỏi đúng đường mà giao diện hỏi: `/auth/me` là chỗ màn hình đọc ra cờ để đẩy người dùng sang
    # trang đổi mật khẩu.
    tok = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200, me.text
    assert me.json()["must_change_password"] is True, \
        "đăng nhập được bằng mật khẩu cả internet đã đọc, mà không bị bắt đổi"

    db.expire_all()
    assert db.query(User).filter(User.username == "quenkhongdoi").one().must_change_password

    # Một lần băm, và đúng một lần: đó là phép xác thực chính nó. Nhận ra mật khẩu đã công bố KHÔNG
    # được tốn thêm lần băm nào – nếu tốn thì mỗi lần đăng nhập của cả công ty đắt lên gấp đôi.
    assert dem_bam["n"] == 1, f"đăng nhập băm {dem_bam['n']} lần, đáng lẽ đúng 1"


def test_mk8_dang_nhap_bang_mat_khau_tu_te_thi_khong_bi_lam_phien(db):
    _nguoi(db, "dangoanngoan", TU_TE, da_dang_nhap=True)
    r = client.post("/api/v1/auth/login", data={"username": "dangoanngoan", "password": TU_TE})
    assert r.status_code == 200, r.text
    me = client.get("/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["must_change_password"] is False, \
        "bắt đổi cả người đã đặt mật khẩu tử tế thì lần sau không ai tin cái cờ ấy nữa"


# ── Luật đặt mật khẩu ───────────────────────────────────────────────────────────────────────────

def test_mk9_khong_dat_lai_duoc_chinh_mat_khau_da_cong_khai(monkeypatch):
    """Hai phần, và phần thứ hai mới là phần thật.

    Mật khẩu đang bị công bố hôm nay ngắn hơn mức tối thiểu, nên nó bị chặn bởi luật độ dài dù luật
    "đã công khai" có tồn tại hay không. Phép thử chỉ dừng ở đó thì nó XANH cả khi luật ấy bị gỡ —
    thử phá ngày 14/9 lộ ra đúng chuyện này. Nên phần hai dựng một mật khẩu ĐỦ DÀI mà đã bị công bố,
    và đòi máy vẫn từ chối: một mật khẩu đã công bố thì dài bao nhiêu cũng bằng không.
    """
    assert MKY.vi_sao_khong_dat_duoc(CONG_KHAI, username="chutich"), \
        "đặt lại được đúng mật khẩu vừa bị công bố thì cả việc buộc đổi thành vô nghĩa"

    monkeypatch.setattr(MKY, "DA_CONG_KHAI", ("Vietourist#2026",))
    vi_sao = MKY.vi_sao_khong_dat_duoc("Vietourist#2026", username="chutich")
    assert vi_sao, "mật khẩu đã công bố nhưng đủ dài thì vẫn lọt – luật 'đã công khai' không chạy"
    assert "công khai" in vi_sao, "từ chối mà không nói vì sao thì người ta thử lại đúng chuỗi ấy"
    assert MKY.la_mat_khau_da_cong_khai("Vietourist#2026"), \
        "cửa đăng nhập và luật đặt mật khẩu phải đọc cùng MỘT danh sách"


def test_mk10_chan_mat_khau_de_doan_va_thu_nguoi_khac_biet():
    for xau in ("12345678", "123456789", "87654321", "password", "aaaaaaaa", "abc", "matkhau",
                "vietourist", "        "):
        assert MKY.vi_sao_khong_dat_duoc(xau, username="chutich"), f"nhận mật khẩu yếu: {xau!r}"

    # Tên đăng nhập, họ tên và mã nhân viên đều là thứ người khác biết – mã nhân viên còn nằm công
    # khai trên bảng lương.
    assert MKY.vi_sao_khong_dat_duoc("chutich2026", username="chutich")
    assert MKY.vi_sao_khong_dat_duoc("NguyenThiHoa1", ho_ten="Nguyễn Thị Hoa")
    assert MKY.vi_sao_khong_dat_duoc("xxNS0001xx", ma_nhan_vien="NS0001")

    assert MKY.vi_sao_khong_dat_duoc(TU_TE, username="chutich", ho_ten="Chủ tịch HĐQT",
                                     ma_nhan_vien="NS0001") == "", \
        "chặn quá tay thì người ta sẽ ghi mật khẩu ra giấy dán màn hình"


# ── Số thật, không phải số cho vui ──────────────────────────────────────────────────────────────

def test_mk11_mot_tram_mười_sau_tai_khoan_thi_tai_trang_van_re(dem_bam):
    """116 — đúng bằng số tài khoản đang hoạt động trên bản thật ngày 14/9/2026.

    Bộ thử cũ dựng năm tài khoản, và năm tài khoản không nói gì về 116. Con số ở đây không phải cho
    đẹp: nó là con số đã làm treo màn hình thật.
    """
    s = SessionLocal()
    try:
        _dat_lai(s)
        for i in range(116):
            s.add(User(username=f"nv{i:03d}", full_name=f"Nhân viên {i}", role="nv_kd",
                       staff_code=f"NS{i:04d}", password_hash=BAM_SAN, active=True,
                       last_login=None if i % 2 else datetime(2026, 9, 1, 8, 0)))
        s.commit()

        t = time.time()
        kq = MKY.tom_tat(s)
        giay = time.time() - t

        assert kq["tong_tai_khoan"] == 116
        assert kq["chua_tung_dang_nhap"] == 58
        assert dem_bam["n"] == 0, (
            f"116 tài khoản làm {dem_bam['n']} lần băm. Ở máy chủ thật đó là "
            f"~{dem_bam['n'] * 0.27:.0f} giây mỗi lần có người mở màn hình Tài khoản.")
        # Cái cân ở trên mới là chốt; cái đồng hồ này chỉ để lỗi đọc ra thành người hiểu được.
        assert giay < 2, f"tải trang mất {giay:.1f}s với 116 tài khoản"
    finally:
        _dat_lai(s)
        s.close()


def test_mk12_trang_dang_nhap_khong_in_tai_khoan_hay_mat_khau():
    """Chốt cuối, và là chốt đơn giản nhất: đừng dán mật khẩu lên cửa.

    Phép thử đọc thẳng tệp màn hình. Không có nó thì lần sau ai đó thêm lại "cho tiện lúc demo", và
    không gì kêu lên cả.
    """
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "web", "app", "login", "page.tsx")
    if not os.path.exists(p):
        pytest.skip("không có cây web cạnh cây backend")
    src = open(p, encoding="utf-8").read()
    for xau in (MKY.DA_CONG_KHAI + ("mật khẩu 1", "dùng mật khẩu")):
        assert xau not in src, f"trang đăng nhập đang in ra {xau!r}"
    # Tên tài khoản quản trị cũng không nên bày sẵn.
    for tk in ("chutich,", "chutich)", "tgd,", "ketoan,"):
        assert tk not in src, "trang đăng nhập đang liệt kê tên tài khoản quản trị"


def test_mk13_verify_password_van_chay_dung():
    """Phép thử này canh chính cái cân của MK2/MK7: nếu `verify_password` bị ai đó thay bằng thứ
    không gọi bcrypt nữa thì phép đếm ở trên tự nhiên bằng không và không còn nói gì."""
    h = hash_password(TU_TE)
    assert verify_password(TU_TE, h)
    assert not verify_password("sai", h)
