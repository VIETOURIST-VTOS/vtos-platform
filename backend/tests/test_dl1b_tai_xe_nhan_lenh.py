# -*- coding: utf-8 -*-
"""DL-1b · Tài xế NHẬN lệnh — mắt thứ ba, mắt cuối của chuỗi Chủ tịch đặc tả 11/10/2026.

    Điều hành ĐỀ NGHỊ xe  →  Giám đốc đội xe LẬP LỆNH  →  tài xế NHẬN

BỐN LUẬT Chủ tịch chốt 12/10/2026, mỗi luật một nhóm phép kiểm dưới đây:

  1. TỪ CHỐI KHÔNG HUỶ LỆNH — lệnh vẫn hiệu lực, chỉ báo Giám đốc đội xe.
  2. HẠN NHẬN = 24 GIỜ TRƯỚC NGÀY ĐI — mốc neo vào CHUYẾN, không vào lúc lập lệnh.
  3. SỬA LỆNH SAU KHI ĐÃ NHẬN → XOÁ DẤU NHẬN, tài xế phải nhận lại.
  4. QUÁ HẠN KHÔNG CHẶN AI — chỉ đếm được và nổi lên bàn làm việc.

VÀ MỘT RANH GIỚI QUYỀN: tài xế KHÔNG được mở cả cụm `/api/v1/dispatch`. Mở cả cụm là cho tài xế
đọc giá thuê nội bộ của mọi lệnh trong công ty. Ba cửa của mắt này đứng trên tiền tố riêng
`/api/v1/nhan-lenh`, và hai cửa ghi còn chặn thêm: tài xế chỉ chạm được lệnh ghi TÊN MÌNH.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_dl1b.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
import inspect
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models.core import Tour, User
from app.models.hr import DispatchOrder, Employee, Vehicle
from app.services import nhan_lenh as NL


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _u(db, vai):
    u = db.execute(select(User).where(User.role == vai)).scalars().first()
    return u or db.execute(select(User).where(User.role == "chutich")).scalars().first()


def _lenh(db, di_sau_ngay=5):
    """Một lệnh điều xe còn hiệu lực, ngày đi cách hôm nay `di_sau_ngay` ngày."""
    t = db.execute(select(Tour).order_by(Tour.id)).scalars().first()
    v = db.execute(select(Vehicle)).scalars().first()
    e = db.execute(select(Employee)).scalars().first()
    d1 = date.today() + timedelta(days=di_sau_ngay)
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=e.id,
                      date_from=d1, date_to=d1 + timedelta(days=1), status="da_xac_nhan")
    db.add(d); db.flush()
    return d


# ───────────────────────────── Luật 2: hạn nhận neo vào CHUYẾN
def test_han_nhan_la_24_gio_TRUOC_NGAY_DI(_startup):
    with SessionLocal() as db:
        d = _lenh(db, di_sau_ngay=5)
        h = NL.han_nhan(d)
        assert h == datetime.combine(d.date_from, datetime.min.time()) - timedelta(hours=24)
        assert h.date() == d.date_from - timedelta(days=1)
        db.rollback()


def test_han_KHONG_neo_vao_luc_lap_lenh(_startup):
    """Lệnh lập sớm một tháng thì hạn vẫn rơi đúng một ngày trước khi đi, còn kịp đổi người."""
    with SessionLocal() as db:
        a = _lenh(db, di_sau_ngay=30)
        b = _lenh(db, di_sau_ngay=2)
        assert NL.han_nhan(a) > NL.han_nhan(b), "hạn phải đi theo NGÀY ĐI, không theo lúc lập"
        assert (NL.han_nhan(a) - datetime.now()).days >= 28
        db.rollback()


def test_mot_cho_duy_nhat_tinh_han(_startup):
    """Phép tính hạn chỉ được nằm ở `han_nhan()`.

    Ngày nào lệnh có thêm GIỜ khởi hành thì sửa đúng một hàm là xong. Gõ rải rác nơi khác thì sửa
    một chỗ, quên chỗ kia, và hai màn hình nói hai cái hạn khác nhau.
    """
    import app.services.nhan_lenh as M
    src = inspect.getsource(M)
    assert src.count("timedelta(hours=HAN_GIO)") == 1
    assert "HAN_GIO = 24" in src


# ───────────────────────────── Luật 1: từ chối KHÔNG huỷ lệnh
def test_tu_choi_thi_LENH_VAN_HIEU_LUC(_startup):
    with SessionLocal() as db:
        d = _lenh(db)
        truoc = d.status
        NL.tu_choi(db, _u(db, "tai_xe"), d.id, "Xe đang nằm xưởng thay lốp")
        assert d.status == truoc, "từ chối KHÔNG được đổi trạng thái lệnh"
        assert d.status != "huy", "tài xế không huỷ được việc của cấp trên"
        assert NL.trang_thai_nhan(d) == NL.TU_CHOI
        db.rollback()


def test_tu_choi_KHONG_ghi_ly_do_thi_bi_chan(_startup):
    with SessionLocal() as db:
        d = _lenh(db)
        with pytest.raises(ValueError) as ex:
            NL.tu_choi(db, _u(db, "tai_xe"), d.id, "   ")
        assert "lý do" in str(ex.value).lower()
        db.rollback()


def test_ly_do_tu_choi_nam_lai_de_doi_chieu_thang_sau(_startup):
    with SessionLocal() as db:
        d = _lenh(db)
        NL.tu_choi(db, _u(db, "tai_xe"), d.id, "Tôi đang chạy chuyến khác ngày đó")
        kq = NL.can_giam_doc_xe_biet(db)
        assert any("chuyến khác" in r["tu_choi_nhan_ly_do"] for r in kq["tu_choi"])
        db.rollback()


# ───────────────────────────── Nhận
def test_nhan_ghi_dung_NGUOI_BAM(_startup):
    with SessionLocal() as db:
        d = _lenh(db)
        u = _u(db, "tai_xe")
        NL.nhan(db, u, d.id)
        assert d.nhan_luc is not None and d.nhan_boi == u.username
        assert NL.trang_thai_nhan(d) == NL.DA_NHAN
        db.rollback()


def test_nhan_roi_thi_XOA_ly_do_tu_choi_cu(_startup):
    """Đổi ý là chuyện bình thường; để lại lý do từ chối cạnh dấu đã nhận là hai câu nói ngược nhau."""
    with SessionLocal() as db:
        d = _lenh(db)
        u = _u(db, "tai_xe")
        NL.tu_choi(db, u, d.id, "Xe hỏng")
        NL.nhan(db, u, d.id)
        assert d.tu_choi_nhan_ly_do == ""
        db.rollback()


def test_khong_ghi_de_gio_nhan_lan_dau(_startup):
    with SessionLocal() as db:
        d = _lenh(db)
        u = _u(db, "tai_xe")
        NL.nhan(db, u, d.id)
        with pytest.raises(ValueError):
            NL.nhan(db, u, d.id)
        db.rollback()


def test_lenh_da_huy_thi_khong_con_cho_ai_nhan(_startup):
    with SessionLocal() as db:
        d = _lenh(db); d.status = "huy"; db.flush()
        with pytest.raises(ValueError):
            NL.nhan(db, _u(db, "tai_xe"), d.id)
        db.rollback()


# ───────────────────────────── Luật 3: sửa lệnh thì xoá dấu nhận
def test_sua_lenh_thi_XOA_DAU_NHAN(_startup):
    with SessionLocal() as db:
        d = _lenh(db)
        NL.nhan(db, _u(db, "tai_xe"), d.id)
        assert NL.xoa_dau_nhan(db, d, "lệnh được chốt lại") is True
        assert d.nhan_luc is None and d.nhan_boi == ""
        assert NL.trang_thai_nhan(d) == NL.CHUA_NHAN
        db.rollback()


def test_xoa_dau_nhan_NOI_RA_khi_that_su_co_dau(_startup):
    """Trả False khi không có gì để xoá, để nơi gọi biết mà nói lại cho người sửa — xoá âm thầm là
    bắt tài xế bấm lại mà không ai báo."""
    with SessionLocal() as db:
        d = _lenh(db)
        assert NL.xoa_dau_nhan(db, d, "thử") is False
        db.rollback()


# ───────────────────────────── Luật 4: quá hạn chỉ ĐẾM, không chặn
def test_qua_han_khi_dong_ho_di_qua_moc(_startup):
    with SessionLocal() as db:
        d = _lenh(db, di_sau_ngay=5)
        assert NL.trang_thai_nhan(d) == NL.CHUA_NHAN
        sau = NL.han_nhan(d) + timedelta(hours=1)
        assert NL.trang_thai_nhan(d, sau) == NL.QUA_HAN
        db.rollback()


def test_qua_han_VAN_NHAN_DUOC(_startup):
    """Quá hạn không chặn ai — lệnh vẫn hiệu lực, tài xế vẫn bấm nhận được."""
    with SessionLocal() as db:
        d = _lenh(db, di_sau_ngay=0)
        assert NL.trang_thai_nhan(d) == NL.QUA_HAN
        NL.nhan(db, _u(db, "tai_xe"), d.id)
        assert NL.trang_thai_nhan(d) == NL.DA_NHAN
        db.rollback()


def test_trang_thai_nhan_KHONG_luu_thanh_cot(_startup):
    """Quá hạn đổi theo đồng hồ, không theo một lần bấm nào. Một cột lưu sẵn sai ngay phút sau."""
    cols = {c.name for c in DispatchOrder.__table__.columns}
    assert "trang_thai_nhan" not in cols and "qua_han" not in cols
    assert {"nhan_luc", "nhan_boi", "tu_choi_nhan_ly_do"} <= cols


def test_KHONG_muon_lai_cot_status(_startup):
    """`status` nghĩa là GIÁM ĐỐC ĐỘI XE đã chốt lệnh. Nhận của tài xế là câu hỏi khác."""
    with SessionLocal() as db:
        d = _lenh(db)
        assert d.status == "da_xac_nhan"
        assert NL.trang_thai_nhan(d) != NL.DA_NHAN, \
            "lệnh GĐ xe đã chốt mà chưa ai bấm nhận thì KHÔNG được tính là tài xế đã nhận"
        db.rollback()


# ───────────────────────────── Bàn làm việc đội xe
def test_ban_doi_xe_co_DU_BA_O(_startup):
    from app.services import ban_lam_viec as BLV
    with SessionLocal() as db:
        b = BLV.ban(db, "doi_xe")
        assert b["co_ban"] is True
        assert [o["khoa"] for o in b["o"]] == ["de_nghi_xe_cho_lap_lenh", "lenh_tai_xe_chua_nhan",
                                               "lenh_da_nhan_trong_tuan"]
        assert all(o["trang_thai"] == BLV.SAN_SANG for o in b["o"]), \
            [o.get("ly_do") for o in b["o"]]


def test_ban_dieu_hanh_KHONG_mat_o_nao(_startup):
    """DL-1b đổi `ban()` sang chạy theo bảng khai. Bàn cũ phải y nguyên năm ô."""
    from app.services import ban_lam_viec as BLV
    with SessionLocal() as db:
        b = BLV.ban(db, "dieu_hanh")
        assert [o["khoa"] for o in b["o"]] == ["yeu_cau_booking", "su_co_qua_han", "de_nghi_chi",
                                               "quyet_toan", "bao_cao_ngay"]


def test_o_MAU_SO_khong_cong_vao_tong_dang_cho(_startup):
    """"Lệnh đã nhận trong tuần" là mẫu số để đọc ô kia, không phải việc phải làm.

    PHÉP KIỂM NÀY ĐÃ TỪNG LÀ TRANG TRÍ, và kiểm ngược vạch ra: bản đầu tính lại tổng bằng CHÍNH
    `BLV.MAU_SO` rồi so với tổng của máy — nên khi `MAU_SO = ()` thì hai vế cùng sai một kiểu và
    vẫn bằng nhau. Một phép kiểm so mã với chính nó thì xanh cả khi mã hỏng. Bản này gõ THẲNG tên
    hai ô việc, nên nó đo cái nó nói là đo.
    """
    from app.services import ban_lam_viec as BLV
    with SessionLocal() as db:
        d = _lenh(db)
        NL.nhan(db, _u(db, "tai_xe"), d.id)
        b = BLV.ban(db, "doi_xe")
        so = {o["khoa"]: o["so_luong"] for o in b["o"]}
        assert so["lenh_da_nhan_trong_tuan"] >= 1, "phải đếm được lệnh vừa nhận"
        viec = so["de_nghi_xe_cho_lap_lenh"] + so["lenh_tai_xe_chua_nhan"]
        assert b["tong_dang_cho"] == viec, (
            f"tổng đang chờ phải là {viec} (hai ô việc), không phải "
            f"{viec + so['lenh_da_nhan_trong_tuan']} (cộng cả mẫu số)")
        assert "lenh_da_nhan_trong_tuan" in BLV.MAU_SO
        db.rollback()


def test_o_de_nghi_xe_dung_duoc_khi_CO_DONG(_startup):
    """Phép kiểm này sinh ra từ một lỗi thật: bản đầu của `_de_nghi_xe_cho_lap_lenh` quên
    `from app.models.core import Tour`, và lượt thử trên kho RỖNG không chạy vào thân vòng lặp nên
    NameError không hiện ra. Một ô chỉ thử với 0 dòng là một ô chưa được thử."""
    from app.models.de_nghi_xe import DeNghiXe
    from app.services import ban_lam_viec as BLV, de_nghi_xe as DN
    with SessionLocal() as db:
        t = db.execute(select(Tour).order_by(Tour.id)).scalars().first()
        t.status = "da_duyet"
        t.start_date = date.today() + timedelta(days=3)
        t.end_date = t.start_date + timedelta(days=1)
        db.flush()
        DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=40)
        o = [x for x in BLV.ban(db, "doi_xe")["o"] if x["khoa"] == "de_nghi_xe_cho_lap_lenh"][0]
        assert o["so_luong"] >= 1 and o["dong"], "ô phải dựng được dòng mẫu, không chỉ đếm"
        assert o["trang_thai"] == BLV.SAN_SANG
        db.rollback()


# ───────────────────────────── Ranh giới quyền
def test_tai_xe_KHONG_duoc_mo_ca_cum_dispatch(_startup):
    """Mở cả `/api/v1/dispatch` là cho tài xế đọc giá thuê nội bộ của mọi lệnh trong công ty."""
    from app.services.access import RESTRICTED_API_PREFIXES
    pv = RESTRICTED_API_PREFIXES["tai_xe"]
    assert "/api/v1/nhan-lenh" in pv
    assert "/api/v1/dispatch" not in pv


def test_hai_man_hinh_co_tien_to_moi(_startup):
    """Nút hiện ra mà bấm vào là 403 — "cửa mở, biển đề đóng" đã ghi ba lần trong sổ."""
    from app.services.access import MAN_HINH_API
    assert "/api/v1/nhan-lenh" in MAN_HINH_API["/xe-hdv"]
    assert "/api/v1/nhan-lenh" in MAN_HINH_API["/lenh-dieu-xe"]
