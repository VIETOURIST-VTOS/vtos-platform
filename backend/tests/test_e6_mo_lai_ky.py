# -*- coding: utf-8 -*-
"""Đợt E6 (13/10/2026) — MỞ LẠI KỲ KẾ TOÁN ĐÃ KHÓA. Kế toán trưởng trình, Chủ tịch ký.

VÌ SAO CÓ TỆP NÀY

Trước đợt này khóa kỳ là MỘT CHIỀU: `accounting.lock_period` ghi một dòng `period_locks` và không
có hàm nào, không có cửa nào gỡ nó ra — kể cả cho Chủ tịch. Khóa nhầm một kỳ là kẹt thật, và cách
duy nhất còn lại là sửa thẳng cơ sở dữ liệu, tức đi vòng qua chính lớp kiểm soát vừa dựng.

Mở lại một kỳ đã khóa là mở đường sửa số đã chốt, nên cái cửa ấy phải ĐẮT. Tệp này canh đúng cái
giá đó — và canh cả chỗ nó KHÔNG được đắt quá:

 1. HAI NGƯỜI. Người trình không tự ký, và Chủ tịch — người ký duy nhất — không tự trình.
 2. LÝ DO BẮT BUỘC tối thiểu 30 ký tự.
 3. KHÔNG MỞ KỲ ĐÃ CHỐT THEO BẢN KIỂM TOÁN, và hỏi theo DẤU VẾT trong sổ chứ không theo một cột cờ.
 4. KÝ RỒI THÌ KỲ MỞ RA THẬT — dòng `period_locks` bị xoá, và dấu vết lần khóa cũ được chép lại
    trước khi xoá, vì sau đó nó không còn chỗ nào khác.
 5. KỲ ĐANG MỞ LẠI PHẢI NHÌN THẤY ĐƯỢC cho tới khi có người khóa lại.
 6. LUẬT CHỮ KÝ ĐỌC TỪ BẢNG, không viết tay trong dịch vụ — một luật, một chỗ.
"""
import os
import sys
import tempfile
from datetime import date, datetime

# MỘT TỆP PHÉP THỬ, MỘT CƠ SỞ DỮ LIỆU RIÊNG — đúng lệ của kho này (`tests/run_all.sh` chạy mỗi tệp
# một tiến trình). Đặt biến TRƯỚC khi nhập mô-đun ứng dụng: máy kết nối dựng đúng một lần lúc nhập.
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e6.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                                  # noqa: E402
from sqlalchemy import select                                   # noqa: E402

from app.db.session import Base, SessionLocal, engine           # noqa: E402
from app.models.accounting import JournalEntry, PeriodLock      # noqa: E402
from app.models.core import User                                # noqa: E402
from app.models.mo_lai_ky import MoLaiKy                        # noqa: E402
from app.services import chu_ky as CK                           # noqa: E402
from app.services import mo_lai_ky as ML                        # noqa: E402

Base.metadata.create_all(engine)

LY_DO = ("Kiểm toán gửi bút toán điều chỉnh dự phòng phải thu ngày 12/10, phải ghi vào kỳ này "
         "theo đúng kỳ phát sinh.")


def db_():
    return SessionLocal()


def _nguoi(db, ten: str, vai: str) -> User:
    u = db.execute(select(User).where(User.username == ten)).scalars().first()
    if not u:
        u = User(username=ten, full_name=ten, role=vai, password_hash="x")
        db.add(u)
        db.commit()
    return u


_dem = [0]


def _ky_moi(db) -> str:
    """Một kỳ chưa ai dùng, ĐANG KHÓA. Mỗi phép thử một kỳ riêng để chúng không đè nhau."""
    _dem[0] += 1
    p = "20%02d-%02d" % (30 + _dem[0] // 12, _dem[0] % 12 + 1)
    db.add(PeriodLock(period=p, locked_by="ketoan", locked_at=datetime(2026, 10, 5, 9, 0),
                      note="Chốt sổ kỳ %s" % p))
    db.commit()
    return p


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. LUẬT CHỮ KÝ — khai MỘT chỗ, và dịch vụ đọc đúng chỗ ấy
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_luat_chu_ky_khai_trong_bang_chung():
    """`mo_lai_ky` phải nằm trong bảng chữ ký chung, không nằm trong tệp dịch vụ của riêng nó.

    Đợt E4a quên khai một việc vào bảng này và Đợt DỌN-1 phải đi dọn. Phép thử này là thứ lẽ ra
    phải có từ lần ấy.
    """
    assert CK.can_ky(ML.LOAI_CHU_KY) == ("chutich",)
    # và dịch vụ KHÔNG viết tay tên vai: nó hỏi bảng
    ma = open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "app", "services", "mo_lai_ky.py"), encoding="utf-8").read()
    assert "_CK.can_ky(LOAI_CHU_KY)" in ma
    assert '"chutich"' not in ma, "tên vai viết tay trong dịch vụ — luật phải đọc từ bảng"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. CỬA TRÌNH — bốn chỗ chặn, và CHỈ bốn
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_ly_do_ngan_thi_chan():
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    with pytest.raises(ML.SaiMoLaiKy) as ex:
        ML.de_nghi(db, kt, p, "Mở lại giúp")
    assert "30" in str(ex.value)
    assert not db.execute(select(MoLaiKy).where(MoLaiKy.period == p)).scalars().all()


def test_ky_dang_mo_thi_khong_co_gi_de_mo_lai():
    db = db_()
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    with pytest.raises(ML.SaiMoLaiKy) as ex:
        ML.de_nghi(db, kt, "2099-01", LY_DO)
    assert "đang MỞ" in str(ex.value)


def test_mot_ky_khong_co_hai_de_nghi_cho_ky():
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    ML.de_nghi(db, kt, p, LY_DO)
    with pytest.raises(ML.SaiMoLaiKy) as ex:
        ML.de_nghi(db, kt, p, LY_DO)
    assert "đang chờ" in str(ex.value)


def test_ky_da_chot_kiem_toan_thi_khong_mo_bang_cua_nay():
    """Hỏi theo DẤU VẾT trong sổ: bút toán chốt sổ kiểm toán, không phải một cột cờ.

    Cột cờ phải có người bấm, mà người quên bấm thì kỳ đã kiểm toán vẫn mở ra được.
    """
    db = db_()
    p = _ky_moi(db)
    db.add(JournalEntry(code="E6KT-%s" % p, entry_date=date(2026, 6, 30), period=p,
                        description="Điều chỉnh chốt sổ theo BCTC kiểm toán",
                        source_type="kiem_toan", source_ref="kt:20260630",
                        ngay_chung_tu=date(2026, 6, 30), status="da_ghi_so"))
    db.commit()
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    with pytest.raises(ML.SaiMoLaiKy) as ex:
        ML.de_nghi(db, kt, p, LY_DO)
    assert "kiểm toán" in str(ex.value)
    assert "E6KT-%s" % p in str(ex.value), "câu từ chối phải nói ra chứng từ làm bằng chứng"


def test_chung_tu_nhap_khong_tinh_la_da_kiem_toan():
    """Một tờ nháp mang mã kiểm toán KHÔNG phải một kỳ đã kiểm toán. Chặn thừa thì người đi vòng."""
    db = db_()
    p = _ky_moi(db)
    db.add(JournalEntry(code="E6NH-%s" % p, entry_date=date(2026, 6, 30), period=p,
                        description="nháp", source_type="kiem_toan", source_ref="kt:20260630",
                        ngay_chung_tu=date(2026, 6, 30), status="nhap"))
    db.commit()
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    d = ML.de_nghi(db, kt, p, LY_DO)
    assert d.trang_thai == "cho_ky"


def test_chu_tich_khong_tu_trinh():
    """Chủ tịch là người ký DUY NHẤT, nên hồ sơ ông tự trình là hồ sơ KHÔNG AI KÝ ĐƯỢC.

    Cùng một phép chặn với `propose_param` (LG2) và `trinh_dieu_khoan` (E4a).
    """
    db = db_()
    p = _ky_moi(db)
    ct = _nguoi(db, "e6_chutich", "chutich")
    with pytest.raises(ML.SaiMoLaiKy) as ex:
        ML.de_nghi(db, ct, p, LY_DO)
    assert "không tự" in str(ex.value)


def test_cua_trinh_khong_mo_gi_ca():
    """Trình xong, kỳ VẪN KHÓA. Cửa trình lập hồ sơ, nó không mở gì."""
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    d = ML.de_nghi(db, kt, p, LY_DO)
    assert d.trang_thai == "cho_ky"
    assert db.get(PeriodLock, p) is not None, "cửa trình đã mở kỳ — nó không được phép"
    assert [x.period for x in ML.dang_cho_ky(db, p)] == [p]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. CỬA KÝ — hai người, và kỳ mở ra ĐÚNG LÚC NÀY
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_nguoi_khong_phai_nguoi_ky_thi_khong_ky_duoc():
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    d = ML.de_nghi(db, kt, p, LY_DO)
    tgd = _nguoi(db, "e6_tgd", "tgd")
    with pytest.raises(ML.SaiMoLaiKy):
        ML.ky(db, tgd, d)
    assert db.get(PeriodLock, p) is not None


def test_nguoi_trinh_khong_tu_ky():
    """Nếu một ngày nào đó bảng chữ ký cho thêm vai, thì vai ấy vẫn không tự ký hồ sơ của mình."""
    db = db_()
    p = _ky_moi(db)
    ct = _nguoi(db, "e6_chutich", "chutich")
    d = MoLaiKy(period=p, ly_do=LY_DO, trinh_boi=ct.username, trinh_vai=ct.role,
                trinh_luc=datetime.now(), trang_thai="cho_ky")
    db.add(d)
    db.commit()
    with pytest.raises(ML.SaiMoLaiKy) as ex:
        ML.ky(db, ct, d)
    assert "không tự ký" in str(ex.value)
    assert db.get(PeriodLock, p) is not None


def test_ky_thi_ky_mo_ra_that_va_dau_vet_khoa_cu_duoc_chep_lai():
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    ct = _nguoi(db, "e6_chutich", "chutich")
    d = ML.de_nghi(db, kt, p, LY_DO)
    ML.ky(db, ct, d)

    assert db.get(PeriodLock, p) is None, "ký rồi mà kỳ vẫn khóa — chữ ký ấy không làm gì cả"
    assert d.trang_thai == "da_ky"
    assert (d.ky_boi, d.ky_vai) == (ct.username, "chutich")
    # DẤU VẾT LẦN KHÓA CŨ: dòng `period_locks` đã bị xoá, nên nếu không chép lại thì nó mất hẳn.
    assert d.khoa_cu_boi == "ketoan"
    assert d.khoa_cu_luc == datetime(2026, 10, 5, 9, 0)
    assert d.khoa_cu_ghi_chu == "Chốt sổ kỳ %s" % p


def test_khong_ky_hai_lan():
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    ct = _nguoi(db, "e6_chutich", "chutich")
    d = ML.de_nghi(db, kt, p, LY_DO)
    ML.ky(db, ct, d)
    with pytest.raises(ML.SaiMoLaiKy):
        ML.ky(db, ct, d)


def test_tu_choi_phai_co_ly_do():
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    ct = _nguoi(db, "e6_chutich", "chutich")
    d = ML.de_nghi(db, kt, p, LY_DO)
    with pytest.raises(ML.SaiMoLaiKy):
        ML.tu_choi(db, ct, d, "   ")
    ML.tu_choi(db, ct, d, "Số kỳ này đã nằm trong BCTC quý 3 đã phát hành — đi bút toán điều chỉnh.")
    assert d.trang_thai == "tu_choi"
    assert db.get(PeriodLock, p) is not None, "từ chối mà kỳ mở ra thì ngược hẳn"
    # từ chối rồi thì trình lại được — đúng việc câu từ chối sinh ra để làm
    d2 = ML.de_nghi(db, kt, p, LY_DO + " Bổ sung: đã có ý kiến Kiểm toán bằng văn bản.")
    assert d2.id != d.id


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. KỲ ĐANG MỞ LẠI PHẢI NHÌN THẤY ĐƯỢC — cho tới khi có người khóa lại
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_ky_dang_mo_lai_hien_tren_ban_lam_viec_cho_toi_khi_khoa_lai():
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    ct = _nguoi(db, "e6_chutich", "chutich")
    d = ML.de_nghi(db, kt, p, LY_DO)
    ML.ky(db, ct, d)
    assert p in [x.period for x in ML.dang_mo_lai(db)]

    # cửa khóa kỳ gọi hàm này sau khi khóa xong — đó là chỗ vòng được đóng
    ML.danh_dau_da_khoa_lai(db, p, "ketoan")
    db.commit()
    assert d.trang_thai == "da_khoa_lai"
    assert d.khoa_lai_boi == "ketoan"
    assert p not in [x.period for x in ML.dang_mo_lai(db)]


def test_bang_nay_khong_bao_gio_xoa_dong():
    """Một kỳ mở lại hai lần là HAI dòng. Đè mất dòng thứ nhất là mất dấu vết lần thứ nhất."""
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    ct = _nguoi(db, "e6_chutich", "chutich")
    for lan in (1, 2):
        d = ML.de_nghi(db, kt, p, LY_DO + " Lần %d." % lan)
        ML.ky(db, ct, d)
        db.add(PeriodLock(period=p, locked_by="ketoan", note="khóa lại lần %d" % lan))
        ML.danh_dau_da_khoa_lai(db, p, "ketoan")
        db.commit()
    ds = db.execute(select(MoLaiKy).where(MoLaiKy.period == p).order_by(MoLaiKy.id)).scalars().all()
    assert len(ds) == 2
    assert [x.trang_thai for x in ds] == ["da_khoa_lai", "da_khoa_lai"]
    assert "Lần 1." in ds[0].ly_do and "Lần 2." in ds[1].ly_do


def test_dong_cho_man_hinh_gui_ten_vai_doc_duoc():
    """Màn hình không phải tự dịch mã vai — dịch hai chỗ là hai chỗ để lệch nhau."""
    db = db_()
    p = _ky_moi(db)
    kt = _nguoi(db, "e6_ktt", "ketoan_truong")
    d = ML.de_nghi(db, kt, p, LY_DO)
    r = ML.dong(d)
    assert r["period"] == p
    assert r["trinh_vai"] == "Kế toán trưởng"
    assert r["ly_do"] == LY_DO
