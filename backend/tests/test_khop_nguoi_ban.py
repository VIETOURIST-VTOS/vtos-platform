# -*- coding: utf-8 -*-
"""KHỚP TÊN NGƯỜI BÁN của kho quyết toán cũ với tài khoản VTOS.

VÌ SAO PHÉP THỬ NÀY QUAN TRỌNG HƠN VẺ NGOÀI CỦA NÓ

Kết quả khớp chảy thẳng vào `bookings.sales_id`, và từ đó vào bảng doanh số cá nhân, vào hoa hồng,
vào chỉ tiêu. Khớp nhầm một cái tên là chuyển doanh số của người này sang người kia — và không ai
phát hiện, vì tổng công ty vẫn đúng. Sai lặng lẽ ra tiền thưởng là loại sai tệ nhất trong hệ này.

Đo thật trên 604 tệp ngày 13/9/2026: 145 tên, 6 tên ứng với nhiều người (286 dòng), 61 tên ngoài
danh sách nhân sự (1.018 dòng). Bốn luật dưới đây không phải giả định — dữ liệu thật đòi từng luật.

  KN1  đúng cả họ tên thì khớp
  KN2  đuôi tên khớp và CHỈ MỘT người ứng thì khớp — "UYỂN NHI" → Lê Thị Uyển Nhi
  KN2b khớp đuôi theo TỪ, không theo ký tự — "YẾN NHI" KHÔNG phải "Lê Thị Uyển Nhi"
  KN3  hai người cùng ứng mà CHỈ MỘT ở phòng kinh doanh thì khớp người bán hàng
  KN3b hai NGƯỜI BÁN HÀNG cùng ứng thì vẫn KHÔNG khớp, và nêu cả hai ra
  KN4  tài khoản đã tắt vẫn khớp — người nghỉ tháng 6 phải nhận doanh số tháng 1–5
  KN5  người gán tay thì máy KHÔNG khớp đè lên, kể cả khi sau đó máy khớp được
  KN6  đã có người nhìn qua và để trống thì lần nạp sau tôn trọng, không tự khớp lại
  KN7  chuỗi không phải tên người thì không đi tìm tài khoản
  KN8  ghi sổ gộp theo khoá tên: "HỒNG NGHIỆP" và "Hong Nghiep" là MỘT dòng, cộng dồn số dòng
  KN9  ghi sổ lần hai không đè lên lựa chọn của người, chỉ cập nhật số dòng
  KN10 bảng cho màn hình gán tách đúng: đã khớp / còn chờ người gán
  KN11 gán cho tài khoản không tồn tại thì từ chối
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_khopnb.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_khopnb.db", "test_khopnb.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import pytest                                                        # noqa: E402

from app.core.security import hash_password                          # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.models.core import User                                      # noqa: E402
from app.models.kho_cu import KhoCuNguoiBan                           # noqa: E402
from app.services import khop_nguoi_ban as K                          # noqa: E402

Base.metadata.create_all(engine)

# Lấy từ danh sách nhân sự thật tháng 9/2026. Hai "Thùy Trang" và hai "Bảo Trâm" là ca có thật;
# "Lê Thị Uyển Nhi" là ca gõ tắt có thật (197 dòng ghi "UYỂN NHI"); hai "Nhị Ngọc" là ca dựng thêm
# để canh đúng chỗ luật phòng dễ đi quá tay — hai người CÙNG bán hàng thì máy vẫn phải im.
NGUOI = [
    # (tài khoản, họ tên, còn làm, phòng) – phòng lấy đúng như danh sách nhân sự tháng 9/2026
    ("vananh", "Nguyễn Ngọc Vân Anh", True, "kd_le"),
    ("uyennhi", "Lê Thị Uyển Nhi", True, "kd_le"),           # NVKD 1
    ("yennhi", "Trần Thị Yến Nhi", True, "kd_doan"),         # NVKD ĐOÀN OB – cái bẫy KN2b
    ("thuytrang1", "Trần Thị Thùy Trang", True, "hcns"),     # HCNS – KHÔNG bán hàng
    ("thuytrang2", "Quách Thị Thuỳ Trang", True, "kd_le"),   # TL Team KD 4 – người bán
    ("baotram1", "Vũ Lý Bảo Trâm", True, "hcns"),
    ("baotram2", "Nguyễn Phương Bảo Trâm", True, "dieu_hanh"),  # cả hai đều KHÔNG bán hàng
    ("nhingoc1", "Lê Thị Nhị Ngọc", True, "kd_le"),
    ("nhingoc2", "Phạm Thị Nhị Ngọc", True, "kd_doan"),      # hai người BÁN HÀNG cùng tên – KN3b
    ("danghi", "Đoàn Phương Nhi", False, "kd_le"),           # đã nghỉ – tài khoản tắt
]


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(KhoCuNguoiBan).delete()
    s.query(User).delete()
    for u, ten, con, phong in NGUOI:
        s.add(User(username=u, full_name=ten, role="nv_kd", department=phong,
                   password_hash=hash_password("x"), active=con))
    s.commit()
    yield s
    s.close()


def _id(db, username):
    return db.query(User).filter(User.username == username).one().id


# ── Ba luật khớp ────────────────────────────────────────────────────────────────────────────────

def test_kn1_dung_ca_ho_ten_thi_khop(db):
    kq = K.khop_mot(db, "NGUYỄN NGỌC VÂN ANH")
    assert kq["user_id"] == _id(db, "vananh")
    assert kq["cach_khop"] == "dung_ten"


def test_kn2_duoi_ten_duy_nhat_thi_khop(db):
    """197 dòng khách trong kho thật ghi "UYỂN NHI". Bỏ luật này là mất đúng chỗ ấy."""
    kq = K.khop_mot(db, "UYỂN NHI")
    assert kq["user_id"] == _id(db, "uyennhi")
    assert kq["cach_khop"] == "duoi_ten"


def test_kn2b_khop_duoi_theo_TU_khong_theo_ky_tu(db):
    """Cái bẫy đã sập một lần, ngày 13/9/2026.

    Khớp theo ký tự thì "YẾN NHI" (yennhi) là đuôi của "Lê Thị Uyển Nhi" (lethiuyennhi), vì
    "uyennhi" kết thúc bằng "yennhi". Hai người khác hẳn nhau, và nhìn bằng mắt thì không ai ngờ
    máy lẫn được — nên nếu lẫn, nó lẫn vĩnh viễn.
    """
    kq = K.khop_mot(db, "YẾN NHI")
    assert kq["user_id"] == _id(db, "yennhi"), \
        "'YẾN NHI' khớp nhầm sang Lê Thị Uyển Nhi – đang khớp đuôi theo ký tự chứ không theo từ"
    assert K.khop_mot(db, "UYỂN NHI")["user_id"] == _id(db, "uyennhi"), \
        "sửa xong bẫy thì làm hỏng ca gõ tắt thật – 197 dòng khách ghi 'UYỂN NHI'"


def test_kn3_trung_cach_goi_thi_lay_nguoi_PHONG_KINH_DOANH(db):
    """Ca thật: "THÙY TRANG" — 103 dòng — ứng với cả Trần Thị Thùy Trang (HCNS) lẫn Quách Thị Thuỳ
    Trang (TL Team KD 4). Cột SALES ghi người BÁN, nên người bán là chị Team KD 4.

    Chủ tịch chỉ ra ngày 13/9: sáu cái tên ấy không phải trùng NGƯỜI, chỉ trùng CÁCH GỌI. Luật phòng
    gỡ được 5 trong 6.
    """
    kq = K.khop_mot(db, "THÙY TRANG")
    assert kq["user_id"] == _id(db, "thuytrang2"), "chị HCNS được gán doanh số bán tour"
    assert kq["cach_khop"] == "duoi_ten_phong_kd"
    assert len(kq["ung_vien"]) == 2, "vẫn phải nêu cả hai ra để người đọc kiểm lại được"

    # Dấu "ỳ"/"ù" khác nhau giữa hai tên vẫn phải ra cùng một kết quả: khoá khớp bỏ dấu.
    assert K.khop_mot(db, "THUỲ TRANG")["user_id"] == _id(db, "thuytrang2")


def test_kn3b_hai_NGUOI_BAN_HANG_cung_ten_thi_van_khong_khop(db):
    """Luật phòng chỉ gỡ được khi còn ĐÚNG MỘT người bán hàng. Hai người bán hàng cùng cách gọi thì
    máy vẫn phải im — đây là chỗ luật mới dễ đi quá tay nhất."""
    kq = K.khop_mot(db, "NHỊ NGỌC")
    assert kq["user_id"] is None, "hai người BÁN HÀNG cùng tên mà máy vẫn chọn bừa một"
    assert kq["cach_khop"] == "trung_ten"
    assert len(kq["ung_vien"]) == 2

    # Và khi KHÔNG AI trong hai người bán hàng: cũng không được chọn.
    kq2 = K.khop_mot(db, "BẢO TRÂM")
    assert kq2["user_id"] is None and kq2["cach_khop"] == "trung_ten"


def test_kn4_tai_khoan_da_tat_van_khop(db):
    """Người nghỉ tháng 6 vẫn phải nhận doanh số tháng 1–5 của họ. Lọc active ở đây là làm mất đúng
    phần dữ liệu lịch sử mà cả lô này sinh ra để có."""
    kq = K.khop_mot(db, "ĐOÀN PHƯƠNG NHI")
    assert kq["user_id"] == _id(db, "danghi"), "tài khoản đã tắt bị bỏ qua – mất doanh số người nghỉ"


def test_kn7_chuoi_khong_phai_ten_thi_khong_di_tim(db):
    for rac in ("VV", "", "   ", "X" * 80):
        kq = K.khop_mot(db, rac)
        assert kq["user_id"] is None
        assert kq["cach_khop"] == "khong_phai_ten", f"'{rac[:12]}' bị đem đi khớp như một cái tên"


# ── Sổ gán: người thắng máy ─────────────────────────────────────────────────────────────────────

def test_kn5_nguoi_gan_tay_thi_may_khong_khop_de_len(db):
    K.ghi_so(db, {"NHỊ NGỌC": 103})
    K.gan_tay(db, K.chuan("NHỊ NGỌC"), _id(db, "nhingoc2"), boi="tp_dh")
    db.commit()

    assert K.tra_so(db, "NHỊ NGỌC") == _id(db, "nhingoc2")

    # Nạp lại lô: máy chạy lại bộ khớp. Lựa chọn của người phải sống sót.
    K.ghi_so(db, {"NHỊ NGỌC": 103})
    db.commit()
    assert K.tra_so(db, "NHỊ NGỌC") == _id(db, "nhingoc2"), \
        "lần nạp sau đã xoá lựa chọn của người – người gán một lần thì phải gán một lần"
    d = db.query(KhoCuNguoiBan).filter(KhoCuNguoiBan.khoa_ten == K.chuan("NHỊ NGỌC")).one()
    assert d.cach_khop == "nguoi_gan" and d.nguoi_gan == "tp_dh"


def test_kn6_de_trong_co_chu_y_thi_lan_sau_ton_trong(db):
    """Người nhìn qua và cố ý để trống ("đây là đại lý ngoài, không phải nhân viên") — lần nạp sau
    không được tự gán cho ai."""
    K.ghi_so(db, {"NGUYỄN NGỌC VÂN ANH": 10})
    K.gan_tay(db, K.chuan("NGUYỄN NGỌC VÂN ANH"), None, boi="tp_dh")
    db.commit()
    assert K.tra_so(db, "NGUYỄN NGỌC VÂN ANH") is None, \
        "để trống có chủ ý mà máy vẫn tự khớp lại – lựa chọn của người không có giá trị gì"


def test_kn8_ghi_so_gop_theo_khoa_ten(db):
    """Cùng một người viết ba kiểu trong ba tệp. Sổ gán phải phình theo SỐ NGƯỜI, không theo lỗi gõ."""
    r = K.ghi_so(db, {"UYỂN NHI": 100, "Uyen Nhi": 50, "uyển nhi": 47})
    db.commit()
    assert r["tong_ten"] == 1, "ba cách viết một cái tên đẻ ra nhiều hơn một dòng trong sổ gán"
    d = db.query(KhoCuNguoiBan).filter(KhoCuNguoiBan.khoa_ten == K.chuan("UYỂN NHI")).one()
    assert d.so_dong == 197, "số dòng không cộng dồn – bảng gán sắp xếp sai thứ tự ưu tiên"
    assert d.user_id == _id(db, "uyennhi")


def test_kn9_ghi_so_lan_hai_chi_cap_nhat_so_dong(db):
    K.ghi_so(db, {"ĐOÀN PHƯƠNG NHI": 166})
    db.commit()
    K.ghi_so(db, {"ĐOÀN PHƯƠNG NHI": 200})
    db.commit()
    ds = db.query(KhoCuNguoiBan).filter(
        KhoCuNguoiBan.khoa_ten == K.chuan("ĐOÀN PHƯƠNG NHI")).all()
    assert len(ds) == 1, "nạp lại đẻ thêm dòng trùng trong sổ gán"
    assert ds[0].so_dong == 200


def test_kn10_bang_tach_dung_da_khop_va_con_cho(db):
    K.ghi_so(db, {"NGUYỄN NGỌC VÂN ANH": 10, "NHỊ NGỌC": 103, "MAI VIGO": 8})
    db.commit()
    b = K.bang(db)
    assert b["tong_ten"] == 3
    assert b["da_khop"] == 1 and b["dong_da_khop"] == 10
    assert b["can_gan"] == 2 and b["dong_can_gan"] == 111, \
        "số dòng còn chờ gán sai – đây là con số người ta nhìn để biết còn bao nhiêu việc"
    trung = next(r for r in b["dong"] if r["khoa_ten"] == K.chuan("NHỊ NGỌC"))
    assert len(trung["ung_vien"]) == 2

    # Gán xong thì nó rời khỏi cột "còn chờ".
    K.gan_tay(db, K.chuan("NHỊ NGỌC"), _id(db, "nhingoc1"), boi="tp_dh")
    db.commit()
    b2 = K.bang(db)
    assert b2["da_khop"] == 2 and b2["can_gan"] == 1


def test_kn11_gan_cho_tai_khoan_khong_ton_tai_thi_tu_choi(db):
    K.ghi_so(db, {"MAI VIGO": 8})
    db.commit()
    with pytest.raises(ValueError):
        K.gan_tay(db, K.chuan("MAI VIGO"), 999999, boi="tp_dh")
    with pytest.raises(ValueError):
        K.gan_tay(db, "khong-co-khoa-nay", None, boi="tp_dh")
