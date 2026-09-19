# -*- coding: utf-8 -*-
"""ZN-1 · Nối tài khoản VTOS với Zalo, và chốt chặn người của công ty thành khách hàng giả.

Hai việc, và việc thứ hai là cái không ai ngờ.

  1. NỐI. Cảnh báo khủng hoảng phải tới được NGƯỜI, không chỉ tới màn hình. Hàm gửi tin OA cần một
     UID Zalo, mà `users` không có ô nào giữ UID. Cách nối phải ngược chiều với trực giác: người
     TỰ XIN một mã trong VTOS rồi TỰ NHẮN mã ấy vào OA — Zalo nói cho mình biết UID, không ai gõ
     nó, nên không tồn tại đường nào để nối nhầm UID người này vào tài khoản người kia.

  2. CHẶN LEAD GIẢ. Webhook OA đang tạo một Lead cho mỗi UID quan tâm OA hoặc nhắn tin. Đúng với
     khách. Nhưng Chủ tịch, TGĐ và P.TGĐ Marketing vừa bấm "Quan tâm" để nhận cảnh báo — và ba
     người lãnh đạo biến thành ba khách hàng tiềm năng, chảy thẳng vào mẫu số của TỶ LỆ CHỐT LEAD
     mà Sales đang được đo bằng. Không ai phát hiện ra; người ta chỉ thấy "dạo này chốt kém".
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_zn1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_zn1.db", "test_zn1.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import inspect  # noqa: E402
import pathlib  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models.core import User  # noqa: E402
from app.models.crm import Conversation, Lead, Message  # noqa: E402
from app.models.zalo_noi import ZaloMaNoi, ZaloNoiTaiKhoan  # noqa: E402
from app.services import zalo as Z  # noqa: E402
from app.services import zalo_nguoi_dung as ZN  # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture()
def db():
    s = SessionLocal()
    for M in (ZaloMaNoi, ZaloNoiTaiKhoan, Message, Conversation, Lead, User):
        s.query(M).delete()
    s.commit()
    yield s
    for M in (ZaloMaNoi, ZaloNoiTaiKhoan, Message, Conversation, Lead, User):
        s.query(M).delete()
    s.commit()
    s.close()


def nguoi(db, ten="chutich", vai="chutich"):
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x")
    db.add(u)
    db.flush()
    return u


def su_kien(ten, uid, text=""):
    if ten == "follow":
        return {"event_name": "follow", "follower": {"id": uid}}
    return {"event_name": ten, "sender": {"id": uid},
            "message": {"text": text, "msg_id": f"m{uid}{len(text)}"}}


# =============================================================================================
# A. MÃ
# =============================================================================================
def test_A_ma_dung_do_dai_va_khong_co_ky_tu_de_go_nham():
    """Bỏ hẳn I, O, 0, 1: người ta đọc mã trên màn hình rồi gõ sang điện thoại, và bốn ký tự ấy là
    bốn cách phổ biến nhất để một mã đúng bị gõ thành sai."""
    for _ in range(50):
        m = ZN.sinh_ma()
        assert len(m) == ZN.DAI_MA == 8
        assert all(c in ZN.BANG_CHU for c in m)
    for xau in "IO01":
        assert xau not in ZN.BANG_CHU, f"bảng chữ còn ký tự dễ gõ nhầm: {xau}"


def test_A_xin_ma_moi_thi_ma_cu_chua_dung_bi_huy(db):
    """Hai mã cùng sống nghĩa là một mã người ta tưởng đã hết hạn vẫn nối được, và cửa sổ mười phút
    mất hết ý nghĩa."""
    u = nguoi(db)
    cu = ZN.tao_ma(db, u)
    moi = ZN.tao_ma(db, u)
    db.commit()
    assert db.get(ZaloMaNoi, cu.id).da_dung is True
    assert db.get(ZaloMaNoi, moi.id).da_dung is False


def test_A_ma_het_han_thi_khong_noi_duoc(db):
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    sau = datetime.now() + timedelta(minutes=ZN.SONG_PHUT + 1)
    assert ZN.thu_ma(db, "uid1", m.ma, bay_gio=sau)["noi"] is False
    assert ZN.la_nhan_vien(db, "uid1") is False


def test_A_ma_da_dung_thi_khong_dung_lai_duoc(db):
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    assert ZN.thu_ma(db, "uid1", m.ma)["noi"] is True
    db.commit()
    assert ZN.thu_ma(db, "uid2", m.ma)["noi"] is False, "mã dùng một lần đang dùng lại được"


def test_A_khoang_trang_va_chu_thuong_van_nhan(db):
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    tho = m.ma[:4].lower() + "  " + m.ma[4:].lower()
    assert ZN.thu_ma(db, "uid9", tho)["noi"] is True, \
        "bắt gõ đúng từng dấu cách chỉ tạo ra những lần nối hỏng vô cớ"


def test_A_tin_thuong_khong_bi_coi_la_ma(db):
    assert ZN.thu_ma(db, "uid1", "cho em hỏi giá tour Phú Quốc")["noi"] is False
    assert ZN.thu_ma(db, "uid1", "")["noi"] is False


def test_A_dem_so_lan_nhan_sai_nhung_khong_khoa(db):
    """Đếm để NHÌN, không để khoá. Khoá theo số lần sai mở ra một cửa mới: ai biết mình đang bị
    nhắm có thể cố tình nhắn sai để khoá mã của người khác."""
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    ZN.thu_ma(db, "uidX", m.ma)          # nối thành công, mã thành đã dùng
    db.commit()
    for _ in range(3):
        ZN.thu_ma(db, "uidY", m.ma)      # nhắn lại mã đã chết
    db.commit()
    assert db.get(ZaloMaNoi, m.id).lan_sai == 3
    # Và mã vẫn không nối cho ai khác – đếm không làm nó sống lại, cũng không khoá gì thêm.
    assert ZN.uid_cua(db, u.id) == "uidX"


# =============================================================================================
# B. NỐI
# =============================================================================================
def test_B_noi_xong_thi_tra_cuu_duoc_hai_chieu(db):
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    kq = ZN.thu_ma(db, "uid-abc", m.ma)
    db.commit()
    assert kq["noi"] is True and kq["username"] == "chutich"
    assert ZN.uid_cua(db, u.id) == "uid-abc"
    assert ZN.la_nhan_vien(db, "uid-abc") is True
    assert ZN.tai_khoan_cua(db, "uid-abc").id == u.id


def test_B_mot_UID_khong_noi_duoc_vao_hai_tai_khoan(db):
    """Một chiếc điện thoại nhận cảnh báo của hai người là đúng cái tình huống bảng này sinh ra để
    chặn — cảnh báo dành riêng cho Chủ tịch tới một máy mà người khác cũng đang cầm."""
    a = nguoi(db, "chutich", "chutich")
    b = nguoi(db, "ptgd", "ptgd_mkt")
    ma_a = ZN.tao_ma(db, a)
    db.commit()
    ZN.thu_ma(db, "uid-chung", ma_a.ma)
    db.commit()
    ma_b = ZN.tao_ma(db, b)
    db.commit()
    kq = ZN.thu_ma(db, "uid-chung", ma_b.ma)
    assert kq["noi"] is False and kq["ly_do"] == "uid_da_noi_nguoi_khac"
    assert ZN.tai_khoan_cua(db, "uid-chung").id == a.id, "UID đã lặng lẽ chuyển sang người khác"


def test_B_doi_may_thi_cap_nhat_chu_khong_sinh_dong_thu_hai(db):
    u = nguoi(db)
    for uid in ("may-cu", "may-moi"):
        m = ZN.tao_ma(db, u)
        db.commit()
        ZN.thu_ma(db, uid, m.ma)
        db.commit()
    assert db.query(ZaloNoiTaiKhoan).count() == 1
    assert ZN.uid_cua(db, u.id) == "may-moi"


def test_B_go_noi_duoc(db):
    """Gỡ được là một phần của an toàn: một tài khoản không gỡ nối được thì chiếc điện thoại cũ vẫn
    nhận cảnh báo khủng hoảng của công ty mãi mãi."""
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    ZN.thu_ma(db, "uid-cu", m.ma)
    db.commit()
    assert ZN.go_noi(db, u) is True
    db.commit()
    assert ZN.uid_cua(db, u.id) == "" and ZN.la_nhan_vien(db, "uid-cu") is False
    assert ZN.go_noi(db, u) is False


def test_B_man_hinh_khong_nhin_thay_UID_day_du(db):
    """UID là mã định danh của một người trên Zalo. Hiện đủ ra thì nó nằm trong ảnh chụp màn hình,
    trong nhật ký trình duyệt, trong mọi chỗ người ta dán."""
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    ZN.thu_ma(db, "1234567890123456", m.ma)
    db.commit()
    tt = ZN.trang_thai(db, u)
    assert tt["da_noi"] is True and tt["duoi_uid"] == "3456"
    assert "1234567890123456" not in str(tt)


def test_B_uid_theo_vai_tra_ca_nguoi_CHUA_noi(db):
    """Danh sách chỉ gồm người đã nối sẽ báo cáo 2/2 thành công và giấu mất người thứ ba."""
    a = nguoi(db, "chutich", "chutich")
    nguoi(db, "tgd", "tgd")
    m = ZN.tao_ma(db, a)
    db.commit()
    ZN.thu_ma(db, "uid-a", m.ma)
    db.commit()
    ds = ZN.uid_theo_vai(db, ["chutich", "tgd"])
    assert len(ds) == 2, "người chưa nối bị loại khỏi danh sách – báo cáo sẽ đẹp một cách giả"
    assert dict((u.username, uid) for u, uid in ds) == {"chutich": "uid-a", "tgd": ""}


# =============================================================================================
# C. WEBHOOK — CHẶN LEAD GIẢ
# =============================================================================================
def test_C_khach_la_quan_tam_OA_van_thanh_lead(db):
    """Giữ nguyên hành vi cũ cho KHÁCH. Chốt chặn chỉ được chặn người của công ty."""
    Z.on_webhook(db, su_kien("follow", "khach-1"))
    assert db.query(Lead).count() == 1


def test_C_nhan_vien_da_noi_quan_tam_OA_thi_KHONG_thanh_lead(db):
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    ZN.thu_ma(db, "uid-sep", m.ma)
    db.commit()
    Z.on_webhook(db, su_kien("follow", "uid-sep"))
    assert db.query(Lead).count() == 0, \
        "Chủ tịch bấm Quan tâm OA để nhận cảnh báo, và vừa thành một khách hàng tiềm năng"


def test_C_nhan_vien_nhan_tin_thi_khong_vao_so_lead_va_khong_vao_hop_thu(db):
    """Hộp thư khách có đồng hồ SLA của Sales, và Sales không nợ Chủ tịch một câu trả lời trong
    mười lăm phút."""
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    ZN.thu_ma(db, "uid-sep", m.ma)
    db.commit()
    Z.on_webhook(db, su_kien("user_send_text", "uid-sep", "alo em ơi"))
    assert db.query(Lead).count() == 0
    assert db.query(Conversation).count() == 0, "tin của sếp đang bật đồng hồ SLA của Sales"


def test_C_nhan_ma_noi_thi_khong_sinh_lead_va_khong_vao_hop_thu(db):
    """Một mã nối không phải một câu hỏi của khách."""
    u = nguoi(db)
    m = ZN.tao_ma(db, u)
    db.commit()
    kq = Z.on_webhook(db, su_kien("user_send_text", "uid-moi", m.ma))
    assert kq.get("noi_tai_khoan") == "chutich"
    assert db.query(Lead).count() == 0 and db.query(Conversation).count() == 0
    assert ZN.uid_cua(db, u.id) == "uid-moi"


def test_C_khach_nhan_tin_binh_thuong_van_chay_nhu_cu(db):
    Z.on_webhook(db, su_kien("user_send_text", "khach-9", "cho em hỏi tour Đà Lạt"))
    assert db.query(Lead).count() == 1
    assert db.query(Conversation).count() == 1


def test_C_chot_chan_dat_TRUOC_moi_nhanh_khac(db):
    """Phép thử ĐỌC MÃ. Chốt phải nằm trước mọi nhánh tạo lead trong `on_webhook`; đặt sau một
    nhánh nào đó là chừa lại đúng một đường để lead giả lọt qua, và đường ấy không ai thấy.
    """
    src = inspect.getsource(Z.on_webhook)
    i_chot = src.find("la_nhan_vien")
    assert i_chot > 0, "on_webhook không còn chốt chặn người của công ty"
    for moc in ("Lead(", "IB.inbound"):
        j = src.find(moc)
        assert j < 0 or j > i_chot, f"nhánh {moc!r} nằm TRƯỚC chốt chặn – lead giả lọt qua đường này"


# =============================================================================================
# D. CỬA VÀ MÀN HÌNH
# =============================================================================================
def test_D_khong_co_cua_noi_ho_nguoi_khac():
    """Toàn bộ tính an toàn nằm ở chỗ này: UID do Zalo nói ra khi chính người ấy nhắn mã. Một cửa
    'quản trị nối hộ' mở lại đúng cái lỗ ấy — quản trị viên gõ nhầm một UID thì cảnh báo của Chủ
    tịch đi tới máy người khác, và không ai biết.
    """
    src = pathlib.Path(ZN.__file__).resolve().parents[1].joinpath(
        "api", "v1", "crm.py").read_text(encoding="utf-8")
    khoi = src[src.find("NỐI TÀI KHOẢN VTOS VỚI ZALO"):]
    assert khoi, "không tìm thấy khối cửa nối Zalo"
    assert "require_roles" not in khoi, \
        "cửa nối Zalo đang khai theo vai trò – nghĩa là có vai nào đó nối được cho người khác"
    assert khoi.count("current_user") >= 3, "có cửa không khoá vào người đang đăng nhập"


def test_D_man_hinh_co_cho_xin_ma():
    """Mã không có cửa cho người dùng lấy thì cả thiết kế này chỉ chạy được bằng tay CNTT."""
    web = pathlib.Path(ZN.__file__).resolve().parents[3].joinpath(
        "web", "app", "doi-mat-khau", "page.tsx").read_text(encoding="utf-8")
    assert "/zalo/ma-noi" in web, "màn hình chưa có nút xin mã nối Zalo"
    assert "/zalo/trang-thai-noi" in web, "màn hình không đọc trạng thái đã nối hay chưa"
