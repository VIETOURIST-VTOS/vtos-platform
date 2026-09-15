# -*- coding: utf-8 -*-
"""TC-33 · Khối 08 Tiến độ báo cáo & kết luận chỉ đạo.

Bản vẽ đặt MỘT khối nhưng hỏi HAI câu khác hẳn nhau:

    (A) phòng nào đã nộp báo cáo của kỳ vừa đóng — trả lời được ngay hôm nay;
    (B) chỉ đạo của Chủ tịch có được làm không — CHƯA có bảng nào giữ.

Phép thử dưới đây canh ba thứ: kỳ nào được đem ra đo, đối chiếu đã nộp / chưa nộp, và việc (B)
không được mượn số của (A) để trông như đã xong.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.bao_cao_luu import BaoCaoLuu
from app.services import tien_do_bao_cao as TD
from app.services.bao_cao_phong import PHONG, PHONG_GOC, TOAN_CTY


@pytest.fixture()
def db():
    """Chỉ dựng ĐÚNG bảng khối này đọc, và không đụng vào `Base.metadata` chung — sửa một thứ dùng
    chung giữa chừng thì phép thử hỏng sẽ hiện ra ở tệp KHÁC."""
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=[BaoCaoLuu.__table__])
    s = sessionmaker(bind=e)()
    try:
        yield s
    finally:
        s.close()


def _luu(db, ky, pham_vi, luc, *, kind="thang", viec_do=0):
    db.add(BaoCaoLuu(kind=kind, ky=ky, pham_vi=pham_vi, pham_vi_ten=pham_vi,
                     tao_luc=luc, so_viec_do=viec_do))


def _theo(r):
    return {d["ma_pham_vi"]: d for d in r["dong"]}


# ───────────────── 1 · ĐO KỲ VỪA ĐÓNG, KHÔNG ĐO KỲ ĐANG CHẠY ─────────────────

@pytest.mark.parametrize("hom_nay,kind,mong", [
    (dt.date(2026, 9, 15), "thang", "2026-08"),
    (dt.date(2026, 1, 3), "thang", "2025-12"),      # bắc qua năm
    (dt.date(2026, 3, 1), "thang", "2026-02"),      # tháng ngắn
    (dt.date(2026, 9, 15), "ngay", "2026-09-14"),
    (dt.date(2026, 9, 14), "tuan", "2026-W37"),
])
def test_ky_vua_dong(hom_nay, kind, mong):
    ky, _, _ = TD._ky_vua_dong(kind, hom_nay)
    assert ky == mong


@pytest.mark.parametrize("kind", ["ngay", "tuan", "thang"])
def test_ky_dem_ra_do_luon_da_dong(kind):
    """Báo cáo tháng 09/2026 KHÔNG thể 'trễ' vào ngày 15/09: kỳ chưa đóng thì chưa tới hạn nộp.

    Lấy kỳ đang chạy ra đo thì MỌI phòng hiện 'chưa nộp' — tám dòng đỏ vô nghĩa, và sau vài lần
    nhìn thấy thì người ta thôi tin cả khối.
    """
    for ngay in (1, 5, 14, 15, 28):
        hom_nay = dt.date(2026, 9, ngay)
        _, dau, cuoi = TD._ky_vua_dong(kind, hom_nay)
        assert cuoi < hom_nay, f"{kind} ngày {hom_nay}: kỳ đem ra đo chưa đóng"
        assert dau <= cuoi


def test_tuan_chay_tu_thu_hai_den_chu_nhat():
    _, dau, cuoi = TD._ky_vua_dong("tuan", dt.date(2026, 9, 14))
    assert dau.weekday() == 0 and cuoi.weekday() == 6
    assert (cuoi - dau).days == 6


def test_ky_la_thi_bao_loi_chu_khong_doan():
    with pytest.raises(ValueError):
        TD.tien_do(None, kind="quy")


def test_man_hinh_biet_dang_do_ky_nao(db):
    """Một bảng tiến độ không nói nó đo kỳ nào là một bảng không kiểm được: người đọc không biết
    'chưa nộp' là chưa nộp của tháng nào."""
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15))
    assert r["ky"] == "2026-08"
    assert "08/2026" in r["ten_ky"]


# ───────────────── 2 · ĐỐI CHIẾU ĐÃ NỘP / CHƯA NỘP ─────────────────

def test_da_nop_va_chua_nop(db):
    _luu(db, "2026-08", TOAN_CTY, dt.datetime(2026, 9, 1, 20, 31), viec_do=4)
    _luu(db, "2026-08", "dieu_hanh", dt.datetime(2026, 9, 1, 21, 5))
    db.commit()
    t = _theo(TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15)))
    assert t[TOAN_CTY]["da_nop"] and "01/09 20:31" in t[TOAN_CTY]["tien_do"]
    assert t["dieu_hanh"]["da_nop"]
    assert not t["ketoan"]["da_nop"]


def test_ban_luu_ky_khac_khong_duoc_tinh_sang(db):
    """Nộp báo cáo tháng 7 không phải là đã nộp báo cáo tháng 8."""
    _luu(db, "2026-07", "ketoan", dt.datetime(2026, 8, 1, 9, 0))
    db.commit()
    t = _theo(TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15)))
    assert not t["ketoan"]["da_nop"]


def test_ban_luu_kieu_ky_khac_khong_duoc_tinh_sang(db):
    """Nộp báo cáo NGÀY không phải là đã nộp báo cáo THÁNG."""
    _luu(db, "2026-08", "ketoan", dt.datetime(2026, 8, 5, 9, 0), kind="ngay")
    db.commit()
    t = _theo(TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15)))
    assert not t["ketoan"]["da_nop"]


def test_chua_nop_thi_so_viec_do_de_rong_khong_phai_0(db):
    """RỖNG KHÁC KHÔNG. 0 việc đỏ nghĩa là đã nộp và sạch; chưa nộp thì chưa đếm được gì."""
    _luu(db, "2026-08", "dieu_hanh", dt.datetime(2026, 9, 1, 21, 5), viec_do=0)
    db.commit()
    t = _theo(TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15)))
    assert t["dieu_hanh"]["so_viec_do"] == 0, "Đã nộp và sạch thì là 0 thật"
    assert t["ketoan"]["so_viec_do"] is None, "Chưa nộp thì phải RỖNG, không phải 0"


def test_dem_dung_da_nop_va_con_thieu(db):
    _luu(db, "2026-08", TOAN_CTY, dt.datetime(2026, 9, 1, 20, 31))
    _luu(db, "2026-08", "dieu_hanh", dt.datetime(2026, 9, 1, 21, 5))
    db.commit()
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15))
    assert r["so_da_nop"] == 2
    assert r["so_da_nop"] + r["so_thieu"] == len(r["dong"])


def test_khong_khai_lai_danh_sach_phong(db):
    """`bao_cao_phong.PHONG` là bản khai chính thức. Khai lại ở đây là tạo bản thứ hai, và hai bản
    khai cùng một thứ thì sớm muộn lệch nhau."""
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15))
    ma = [d["ma_pham_vi"] for d in r["dong"]]
    assert ma == [TOAN_CTY] + list(PHONG_GOC)
    nguon = open(TD.__file__, encoding="utf-8").read()
    assert "from app.services.bao_cao_phong import" in nguon


def test_bo_phan_truc_thuoc_khong_dung_thanh_dong_rieng(db):
    """Bộ phận Visa THUỘC phòng Điều hành (Chủ tịch chốt 10/9/2026), nên ở cấp khối này nó không
    đứng ngang hàng với các phòng."""
    assert PHONG["visa"].get("thuoc") == "dieu_hanh"
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15))
    assert "visa" not in [d["ma_pham_vi"] for d in r["dong"]]


def test_buoc_tiep_khac_nhau_giua_da_nop_va_chua_nop(db):
    """Đã nộp thì bước tiếp là ĐỌC; chưa nộp thì bước tiếp là LẬP. Ghi chung một câu thì cột này
    không nói thêm gì so với cột bên cạnh."""
    _luu(db, "2026-08", TOAN_CTY, dt.datetime(2026, 9, 1, 20, 31))
    db.commit()
    t = _theo(TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15)))
    assert t[TOAN_CTY]["buoc_tiep"] != t["ketoan"]["buoc_tiep"]
    assert t["ketoan"]["cua"], "Bước tiếp phải có CỬA đi tới, không chỉ là một câu chữ"


def test_khong_bia_gio_chot_cho_ky_thang(db):
    """Giờ chốt 20:00 là luật của Điều 12 cho báo cáo NGÀY. Kỳ tháng chưa ai chốt giờ — bịa ra một
    mốc là tạo ra một cái hạn mà không ai từng quyết định."""
    t = _theo(TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15)))
    assert t["ketoan"]["han"] == "31/08/2026"
    assert ":" not in t["ketoan"]["han"]


# ───────────────── 3 · KẾT LUẬN CHỈ ĐẠO: CHƯA CÓ SỔ, VÀ PHẢI NÓI RA ─────────────────

def test_ket_luan_chi_dao_tra_none_khong_tra_danh_sach_rong(db):
    """Danh sách rỗng đọc là 'không có chỉ đạo nào đang theo dõi'. Sự thật là 'chưa có chỗ nào để
    theo dõi'. Hai câu khác hẳn nhau."""
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15))
    assert r["chi_dao"] is None
    assert r["chi_dao"] != []


def test_ket_luan_chi_dao_noi_ro_chua_co_va_ai_phai_khai(db):
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15))
    vs = r["chi_dao_vi_sao"]
    assert vs and len(vs) > 60
    assert "Hội đồng quản trị" in vs, "Phải nói AI khai sổ — ô trống không nói ai thì nằm đó mãi."


def test_nua_chi_dao_khong_muon_so_cua_nua_tien_do(db):
    """Trộn hai nửa thì khối trông như đã xong trong khi một nửa còn chưa bắt đầu."""
    _luu(db, "2026-08", TOAN_CTY, dt.datetime(2026, 9, 1, 20, 31))
    db.commit()
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15))
    assert r["dong"], "Nửa (A) có số"
    assert r["chi_dao"] is None, "Nửa (B) vẫn phải rỗng, dù nửa (A) đã có số"


# ───────────────── 4 · SEC-02 ─────────────────

def test_truong_phong_chi_thay_phong_minh(db):
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15), vai_tro="tp_dh")
    assert {d["ma_pham_vi"] for d in r["dong"]} == {"dieu_hanh"}
    assert TOAN_CTY not in [d["ma_pham_vi"] for d in r["dong"]], (
        "Trưởng phòng không được thấy bảng toàn công ty."
    )


@pytest.mark.parametrize("vai", ["chutich", "tgd", "bks", "robot_ks"])
def test_vai_xem_tat_ca_thay_het(db, vai):
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15), vai_tro=vai)
    assert len(r["dong"]) == 1 + len(PHONG_GOC)


def test_vai_khong_phu_trach_bao_cao_nao_thi_rong_va_noi_vi_sao(db):
    """Rỗng mà không nói vì sao thì người dùng đọc là 'không phòng nào phải nộp'."""
    r = TD.tien_do(db, kind="thang", hom_nay=dt.date(2026, 9, 15), vai_tro="nv_kd")
    assert r["dong"] == []
    assert r["vi_sao"].strip()


def test_khong_khai_quyen_rieng_cho_khoi_nay():
    """Nới quyền mà không ai quyết định là cách quyền rộng ra một cách im lặng."""
    nguon = open(TD.__file__, encoding="utf-8").read()
    assert "XEM_TAT_CA" in nguon and 'PHONG[ma].get("xem"' in nguon
