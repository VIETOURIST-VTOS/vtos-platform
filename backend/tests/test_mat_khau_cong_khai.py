# -*- coding: utf-8 -*-
"""MẬT KHẨU ĐÃ CÔNG KHAI — soát, buộc đổi, và chặn đặt lại thứ yếu.

CHỖ HỎNG THẬT, NGÀY 14/9/2026

Trang đăng nhập của bản chạy trên internet công cộng in thẳng ra màn hình rằng mười hai tài khoản
mẫu — kể cả `chutich`, `tgd`, `ketoan` — dùng chung một mật khẩu, và in luôn mật khẩu ấy ra.

Bộ máy buộc đổi mật khẩu thì đã có sẵn và chạy đúng: cột `must_change_password`, chốt
`check_must_change_password` chặn mọi đường trừ ba đường, màn hình `/doi-mat-khau`. Cái thiếu là
**không ai bật cờ** cho những tài khoản sinh ra lúc gieo dữ liệu mẫu — nên không ai bị buộc đổi, và
mật khẩu công khai cứ thế sống cho tới ngày hệ nhận số thật.

  MK1  soát ra ĐÚNG những tài khoản còn dùng mật khẩu đã công khai
  MK2  soát KHÔNG đổi gì, và không trả về mật khẩu của ai
  MK3  bật cờ mặc định chỉ XEM TRƯỚC
  MK4  bật cờ xong thì cờ lên đúng người, không đụng người đã đổi mật khẩu
  MK5  cờ lên là chặn thật — mọi đường trừ ba đường được phép
  MK6  không đặt lại được chính mật khẩu đã công khai
  MK7  không đặt được mật khẩu quá dễ đoán, quá ngắn, hay toàn một ký tự
  MK8  không đặt được mật khẩu chứa tên đăng nhập / họ tên / mã nhân viên
  MK9  mật khẩu tử tế thì đặt được, và cờ hạ xuống
  MK10 trang đăng nhập KHÔNG in tài khoản hay mật khẩu nào
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_matkhau.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_matkhau.db", "test_matkhau.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import pytest                                                        # noqa: E402

from app.core.security import hash_password, verify_password         # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.models.core import User                                      # noqa: E402
from app.services import mat_khau_yeu as MKY                          # noqa: E402

Base.metadata.create_all(engine)

CONG_KHAI = MKY.DA_CONG_KHAI[0]


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(User).delete()
    # Ba tài khoản còn dùng mật khẩu đã công khai, một đã tự đổi, một đã bị khoá.
    for u, ten, vai in (("chutich", "Chủ tịch HĐQT", "chutich"),
                        ("ketoan", "Kế toán trưởng", "ketoan"),
                        ("kd.hoa", "Nguyễn Thị Hoa", "nv_kd")):
        s.add(User(username=u, full_name=ten, role=vai, staff_code="NS0001",
                   password_hash=hash_password(CONG_KHAI), active=True))
    s.add(User(username="daodoi", full_name="Trần Đã Đổi", role="nv_kd", staff_code="NS0009",
               password_hash=hash_password("Bien!Dong2026"), active=True))
    s.add(User(username="dakhoa", full_name="Lê Đã Khoá", role="nv_kd", staff_code="NS0010",
               password_hash=hash_password(CONG_KHAI), active=False))
    s.commit()
    yield s
    s.close()


# ── Soát ────────────────────────────────────────────────────────────────────────────────────────

def test_mk1_soat_ra_dung_nhung_tai_khoan_con_mat_khau_cong_khai(db):
    kq = MKY.soat(db)
    assert kq["con_mat_khau_cong_khai"] == 3, "đếm sai số tài khoản còn mật khẩu đã công bố"
    ten = {x["username"] for x in kq["danh_sach"]}
    assert ten == {"chutich", "ketoan", "kd.hoa"}
    assert "daodoi" not in ten, "người đã tự đổi mật khẩu bị gọi tên oan"
    assert "dakhoa" not in ten, "tài khoản đã khoá không đăng nhập được, không phải việc phải xử"


def test_mk2_soat_khong_doi_gi_va_khong_lo_mat_khau(db):
    kq = MKY.soat(db)
    assert all(not u.must_change_password for u in db.query(User).all()), "soát mà đã bật cờ"
    phang = str(kq)
    assert CONG_KHAI not in phang, "kết quả soát có chứa mật khẩu – không được lộ ra bất kỳ đâu"
    assert all("password" not in k for k in kq["danh_sach"][0])


# ── Bật cờ ──────────────────────────────────────────────────────────────────────────────────────

def test_mk3_bat_co_mac_dinh_chi_XEM_TRUOC(db):
    kq = MKY.bat_co(db, boi="chutich")
    db.commit()
    assert kq["da_bat"] == 0
    assert all(not u.must_change_password for u in db.query(User).all()), \
        "gọi nhầm một lần là cả công ty bị buộc đổi mật khẩu"


def test_mk4_bat_co_len_dung_nguoi(db):
    MKY.bat_co(db, boi="chutich", xac_nhan=True)
    db.commit()
    co = {u.username: u.must_change_password for u in db.query(User).all()}
    assert co["chutich"] and co["ketoan"] and co["kd.hoa"]
    assert not co["daodoi"], "người đã tự đổi mật khẩu vẫn bị bắt đổi lại"

    # Bật lần hai: không có gì để bật thêm, và không làm phiền ai.
    assert MKY.bat_co(db, boi="chutich", xac_nhan=True)["da_bat"] == 0


def test_mk5_co_len_la_chan_that(db):
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


# ── Luật đặt mật khẩu ───────────────────────────────────────────────────────────────────────────

def test_mk6_khong_dat_lai_duoc_chinh_mat_khau_da_cong_khai(db, monkeypatch):
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


def test_mk7_chan_mat_khau_de_doan(db):
    for xau in ("12345678", "123456789", "87654321", "password", "aaaaaaaa", "abc", "matkhau",
                "vietourist", "        "):
        assert MKY.vi_sao_khong_dat_duoc(xau, username="chutich"), f"nhận mật khẩu yếu: {xau!r}"


def test_mk8_chan_mat_khau_chua_thu_nguoi_khac_biet(db):
    """Tên đăng nhập, họ tên và mã nhân viên đều là thứ người khác biết – mã nhân viên còn nằm công
    khai trên bảng lương."""
    assert MKY.vi_sao_khong_dat_duoc("chutich2026", username="chutich")
    assert MKY.vi_sao_khong_dat_duoc("NguyenThiHoa1", ho_ten="Nguyễn Thị Hoa")
    assert MKY.vi_sao_khong_dat_duoc("xxNS0001xx", ma_nhan_vien="NS0001")


def test_mk9_mat_khau_tu_te_thi_dat_duoc_va_co_ha_xuong(db):
    assert MKY.vi_sao_khong_dat_duoc("Bien!Dong2026", username="chutich",
                                     ho_ten="Chủ tịch HĐQT", ma_nhan_vien="NS0001") == "", \
        "chặn quá tay thì người ta sẽ ghi mật khẩu ra giấy dán màn hình"

    MKY.bat_co(db, boi="chutich", xac_nhan=True)
    db.commit()
    u = db.query(User).filter(User.username == "chutich").one()
    u.password_hash = hash_password("Bien!Dong2026")
    u.must_change_password = False
    db.commit()

    assert not MKY.dang_dung_mat_khau_cong_khai(u.password_hash)
    assert verify_password("Bien!Dong2026", u.password_hash)
    assert MKY.soat(db)["con_mat_khau_cong_khai"] == 2


def test_mk10_trang_dang_nhap_khong_in_tai_khoan_hay_mat_khau():
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
