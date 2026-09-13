# -*- coding: utf-8 -*-
"""Cửa TẠO CHUYẾN cho kho quyết toán cũ – bộ nạp chạy TRƯỚC cửa nạp quyết toán.

VÌ SAO CÓ CỬA NÀY

Đo 13/9/2026: VTOS có 1.150 chuyến nhưng chỉ 47/436 mã của kho cũ khớp được – bản nạp Vietrip chỉ
mang về từ tháng 6, T1–T5/2026 gần như trống. Cửa nạp quyết toán chặn cứng ở "không có chuyến mang
mã ấy", nên phải tạo chuyến trước.

Tách thành CỬA RIÊNG vì tạo mấy trăm chuyến là ghi lại lịch sử vận hành của công ty, không phải hệ
quả phụ của việc đọc tệp.

  IT1  bảng XEM TRƯỚC phải nói đúng con số mà phần ghi sẽ làm
  IT2  bước xem trước KHÔNG ghi một dòng nào
  IT3  điều hành lấy từ THAM SỐ; không có tài khoản ấy thì DỪNG, không tạo gì
  IT4  ô hình thức để RỖNG – đó là ô quyết định phép tính
  IT5  trạng thái là 'ket_thuc', KHÔNG phải 'khoa'
  IT6  nạp lại không nhân đôi chuyến
  IT7  'bỏ qua dòng lỗi' KHÔNG nới được tệp-không-phải-chuyến và tệp-thiếu-ngày
  IT8  khai đủ trong BO_NAP, và quyền HẸP hơn cửa nạp quyết toán
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_taochuyencua.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_taochuyencua.db", "test_taochuyencua.db-journal"):
    if os.path.exists(f):
        os.remove(f)

from datetime import date                                            # noqa: E402

import pytest                                                        # noqa: E402

from app.core.security import hash_password                          # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.models.core import Tour, User                                # noqa: E402
from app.services import intake_tao_chuyen as TCN                     # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(Tour).delete()
    s.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).delete()
    s.add(User(username=TCN.TAI_KHOAN_MAC_DINH, full_name="Điều hành Vietrip", role="nv_kd",
               password_hash=hash_password("x"), active=False))
    s.commit()
    yield s
    s.close()


def _t(tep, ma="", ngay=None, ten="", khach=0):
    return {"ten_tep": tep, "ma_tour": ma, "ngay_di": ngay, "ngay_ve": None,
            "ten_tour": ten, "ten_doan": "", "so_khach": khach, "ngoai_te": []}


def _lo():
    return [
        _t("QT NHA TRANG 05.01.26.xlsx", "NT001.03050126", date(2026, 1, 5), "NHA TRANG", 30),
        _t("QT ĐÀ LẠT 08.01.26.xlsx", "DL001.03080126", date(2026, 1, 8), "ĐÀ LẠT", 40),
        _t("QUYẾT TOÁN VISA MỸ THÁNG 1.xlsx"),                      # không phải chuyến
        _t("THÁNG 1.2026.xlsx"),                                    # thiếu ngày
    ]


def test_it1_bang_xem_truoc_phai_noi_dung_con_so_ma_phan_ghi_se_lam(db):
    """Lỗi đã gặp thật trong lúc chạy thử lô tháng 1: xem trước báo 81, ghi ra 80 – vì hai tệp dùng
    chung một mã mà chỉ tạo được một chuyến (`tours.code` là cột duy nhất).

    Một bảng xem trước nói dối thì lần sau không ai đọc nó nữa, và cái nút "ghi" thành nút bấm mù.
    """
    ds = _lo() + [_t("QT NHA TRANG 05.01.26 (ban 2).xlsx", "NT001.03050126", date(2026, 1, 5))]
    xem = TCN.kiem_lo(db, ds)
    ghi = TCN.nap_lo(db, ds, boi="thu")
    assert xem["da_nap"] == ghi["da_tao"], (
        f"xem trước hứa tạo {xem['da_nap']} nhưng ghi ra {ghi['da_tao']}")
    assert xem["dem"]["trung_trong_lo"] == 1
    assert db.query(Tour).count() == ghi["da_tao"]


def test_it2_buoc_xem_truoc_khong_ghi_mot_dong_nao(db):
    TCN.kiem_lo(db, _lo())
    db.commit()
    assert db.query(Tour).count() == 0, "bước XEM TRƯỚC đã ghi vào cơ sở dữ liệu"


def test_it3_dieu_hanh_lay_tu_tham_so_va_khong_co_thi_DUNG(db):
    """Ô operator_id quyết định THƯỞNG CHUYẾN thuộc về ai. Không tìm thấy tài khoản đã khai thì phải
    dừng hẳn – lấy bừa một người đang làm việc là gán mấy trăm chuyến vào tên họ."""
    r = TCN.nap_lo(db, _lo(), boi="thu")
    assert r["da_tao"] == 2
    nguoi = db.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).one()
    assert all(t.operator_id == nguoi.id for t in db.query(Tour)), \
        "chuyến tạo ra không mang tài khoản hệ thống"

    db.query(Tour).delete()
    db.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).delete()
    db.commit()
    r2 = TCN.nap_lo(db, _lo(), boi="thu")
    db.commit()
    assert r2["da_tao"] == 0 and db.query(Tour).count() == 0, \
        "không có tài khoản điều hành mà vẫn tạo chuyến"
    assert "KHÔNG tạo gì" in r2["message"]


def test_it4_o_hinh_thuc_de_RONG(db):
    """`hinh_thuc` quyết định phép kiểm nào chạy: tour nước ngoài bắt buộc khai tỷ giá và NGÀY tỷ
    giá cho mọi khoản ngoại tệ, giá trẻ em soát theo tỷ lệ khác. Suy ngầm rồi tính tiền theo cái suy
    ấy là chỗ sinh lỗi lặng – để rỗng thì biểu quyết toán hỏi người khai."""
    TCN.nap_lo(db, _lo(), boi="thu"); db.commit()
    assert db.query(Tour).count() == 2
    assert all(t.hinh_thuc is None for t in db.query(Tour)), \
        "cửa tạo chuyến đang tự đặt hình thức – đó là ô của người khai"


def test_it5_trang_thai_la_ket_thuc_khong_phai_khoa(db):
    """'khoa' nghĩa là CNTT đã đối chiếu độc lập. Chưa ai đối chiếu cả."""
    TCN.nap_lo(db, _lo(), boi="thu"); db.commit()
    assert {t.status for t in db.query(Tour)} == {"ket_thuc"}
    assert all(t.status != "khoa" for t in db.query(Tour))


def test_it6_nap_lai_khong_nhan_doi(db):
    TCN.nap_lo(db, _lo(), boi="thu"); db.commit()
    n1 = db.query(Tour).count()
    r2 = TCN.nap_lo(db, _lo(), boi="thu"); db.commit()
    assert r2["da_tao"] == 0 and db.query(Tour).count() == n1, \
        "nạp lại cùng một lô lại đẻ thêm chuyến"


def test_it7_bo_qua_dong_loi_khong_noi_duoc_hai_thu_nay(db):
    """Tệp không phải một chuyến thì không có cách nào biến thành chuyến; tệp thiếu ngày thì không
    có ngày để điền. Cờ 'bỏ qua dòng lỗi' cố ý không mở hai thứ đó."""
    r = TCN.nap_lo(db, _lo(), boi="thu", bo_qua_dong_loi=True); db.commit()
    assert r["da_tao"] == 2, "cờ bỏ-qua-dòng-lỗi vừa tạo thêm chuyến từ tệp không hợp lệ"
    ma = {t.code for t in db.query(Tour)}
    assert not any("VISA" in m.upper() or "THANG" in m.upper() for m in ma)


def test_it8_khai_du_trong_BO_NAP_va_quyen_HEP_hon_cua_nap_quyet_toan():
    from app.services.intake import BO_NAP, VAI_TRO
    assert "tao_chuyen_kho_cu" in BO_NAP, "bộ nạp không khai thì màn hình /tep không thấy nó"
    bo = BO_NAP["tao_chuyen_kho_cu"]
    assert bo["bang_dich"] == "tours" and bo["lo"] is True
    for k in ("kiem", "nap", "kiem_lo", "nap_lo", "doc_tep", "ten", "mo_ta"):
        assert bo.get(k), f"thiếu khoá {k} – khung ba cửa sẽ báo bộ nạp khai thiếu"

    q = set(VAI_TRO["tao_chuyen_kho_cu"])
    assert "ketoan" not in q, (
        "Kế toán có mặt ở cửa NẠP QUYẾT TOÁN vì họ giữ bản đối chiếu H1 để soát TIỀN. Cửa này không "
        "có con số tiền nào – chuyến nào từng chạy là việc của Điều hành.")
    assert "nv_dh" not in q, "nhân viên Điều hành không tạo một lượt mấy trăm chuyến lịch sử"
    assert "tp_dh" in q and "chutich" in q


def test_it9_ma_vua_bi_nguoi_khac_tao_giua_luc_xem_va_luc_ghi(db):
    """Chốt chặn THỨ HAI, chống cuộc đua giữa bước xem trước và bước ghi.

    Bảng xem trước chụp ảnh danh sách mã tại một thời điểm. Giữa lúc chụp và lúc bấm ghi, người khác
    có thể vừa tạo đúng chuyến ấy. `tours.code` là cột DUY NHẤT, nên ghi vào là nổ — và nổ giữa vòng
    lặp thì CẢ LÔ hỏng, không phải một dòng.

    Phép thử dựng đúng cảnh đó: ảnh chụp nói "chưa có", cơ sở dữ liệu nói "có rồi".
    """
    ds = [_t("QT NHA TRANG 05.01.26.xlsx", "NT001.03050126", date(2026, 1, 5), "NHA TRANG", 30)]
    TCN.nap_lo(db, ds, boi="thu"); db.commit()
    assert db.query(Tour).count() == 1

    # Giả đúng cuộc đua: LẦN ĐỌC ĐẦU (của bảng xem trước) chưa thấy mã, lần đọc sau — ngay trước khi
    # ghi — mới thấy. Vá cả hai lần thì không còn cuộc đua nào để thử.
    that = TCN._ma_da_co
    lan = {"n": 0}

    def _gia(_db):
        lan["n"] += 1
        return set() if lan["n"] == 1 else that(_db)

    try:
        TCN._ma_da_co = _gia
        r = TCN.nap_lo(db, ds, boi="thu"); db.commit()
    finally:
        TCN._ma_da_co = that
    assert lan["n"] >= 2, ("nap_lo chỉ đọc danh sách mã MỘT lần – không có lần đọc lại ngay trước "
                           "khi ghi thì không có chốt chặn thứ hai nào cả")

    assert db.query(Tour).count() == 1, \
        "ghi đè lên mã đã có – lô sẽ nổ vì tours.code là cột duy nhất"
    assert r["da_tao"] == 0 and r["bo_vi_vua_co"], \
        "bỏ qua rồi nhưng không nói ra – người bấm tưởng đã tạo đủ"
