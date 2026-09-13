# -*- coding: utf-8 -*-
"""Đợt 1 của khối quyết toán — Đ-10 dự chi↔thực chi · Đ-7 thu hộ–chi hộ · Đ-11 chứng từ theo dòng.

Ba mục này không thêm bảng nào ngoài bốn cột của Đ-7, nhưng cả ba đều canh những chỗ mà một tờ
quyết toán "trông đúng" vẫn sai:

  Đ-10  Thực chi khác dự toán theo CẢ HAI chiều. Vượt thì chặn; hụt thì cần một dòng chữ, vì
        thương lượng tốt và dịch vụ bị cắt bớt nhìn trên con số giống hệt nhau.
  Đ-7   Tiền của khách đi ngang qua công ty. Lọt vào doanh thu là thổi lãi bằng tiền người khác.
  Đ-11  Một dòng chi gắn được NHIỀU chứng từ – bản quyết toán thật là một BỘ HỒ SƠ.

Số dùng ở đây lấy từ mẫu thật của phòng Điều hành (đoàn Hồ Tràm, tệp UK, visa lẻ T5/2026) — số
tròn vẫn xanh khi phép tính lệch vài phần trăm, số thật thì không.
"""
from datetime import date, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

import app.models.core  # noqa: F401
import app.models.lop3_tour  # noqa: F401
import app.models.vietrip  # noqa: F401
from app.db.session import Base
from app.models.lop3_tour import LOAI_DOANH_THU, TourDoanhThuDong, TourHdvChi
from app.models.vietrip import TourCostLine
from app.services import soat_du_chi as SDC
from app.services import thu_ho_chi_ho as THC
from app.services.rules import clear_param_cache

TOUR = 1


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:", poolclass=sa.pool.StaticPool,
                           connect_args={"check_same_thread": False})
    md.create_all(eng)
    clear_param_cache()
    with Session(eng) as s:
        yield s
    clear_param_cache()


def _dong(db, mo_ta, du, thuc, note="", tour_id=TOUR):
    d = TourCostLine(tour_id=tour_id, description=mo_ta, budget=du, actual=thuc,
                     note=note, status="hd")
    db.add(d); db.commit()
    return d


# =============================================================================================
# Đ-10 · DỰ CHI ↔ THỰC CHI
# =============================================================================================

def test_d10_ba_dong_that_cua_doan_ho_tram(db):
    """Đoàn Hồ Tràm 2N1Đ: ba dòng thực chi THẤP hơn dự toán, −11% · −11% · −52%.

    Ngưỡng hụt 15%: hai dòng đầu đi qua, dòng banner phải có một câu giải thích.
    """
    _dong(db, "Ăn tối Cây Dương Hồ Tràm", 9_250_000, 8_205_000)
    _dong(db, "Vé tham quan Minera Bình Châu", 15_000_000, 13_355_000)
    _dong(db, "Banner + ship", 300_000, 145_000)
    kq = SDC.soat_dong(db, TOUR)
    assert [x["mo_ta"] for x in kq["hut"]] == ["Banner + ship"]
    assert kq["hut"][0]["ty_le"] == pytest.approx(-0.5167, abs=0.001)
    assert not kq["vuot"]


def test_d10_hut_la_CANH_BAO_khong_chan_dong_so(db):
    """Chặn một chuyến vì nó tiết kiệm được tiền là cách nhanh nhất để người ta thôi ghi dự toán."""
    _dong(db, "Banner + ship", 300_000, 145_000)
    kq = SDC.soat_dong(db, TOUR)
    assert kq["so_canh_bao"] == 1
    assert kq["duoc_dong_so"] is True


def test_d10_vuot_thi_CHAN(db):
    _dong(db, "Ăn tối phát sinh", 5_000_000, 9_000_000)
    kq = SDC.soat_dong(db, TOUR)
    assert kq["so_chan"] == 1 and kq["duoc_dong_so"] is False
    assert kq["vuot"][0]["muc"] == "chan"


def test_d10_co_giai_thich_thi_thoi_keu_o_CA_HAI_chieu(db):
    """Yêu cầu là MỘT DÒNG GIẢI THÍCH, không phải một lời buộc tội."""
    _dong(db, "Vượt có lý do", 5_000_000, 9_000_000, note="Khách xin đổi nhà hàng cao cấp hơn")
    _dong(db, "Hụt có lý do", 300_000, 100_000, note="Thương lượng lại với nhà in")
    kq = SDC.soat_dong(db, TOUR)
    assert not kq["vuot"] and not kq["hut"]
    assert kq["duoc_dong_so"] is True


def test_d10_du_toan_RONG_thi_khong_so_chu_khong_coi_bang_0(db):
    """Coi rỗng là 0 thì mọi dòng đều 'vượt vô hạn', danh sách đầy rác, và người ta thôi đọc."""
    _dong(db, "Chưa khai dự toán", None, 9_000_000)
    kq = SDC.soat_dong(db, TOUR)
    assert not kq["vuot"] and not kq["hut"]
    assert kq["chua_co_du_toan"][0]["vi_sao"] == "chưa khai dự toán"


def test_d10_chua_nhap_thuc_chi_KHONG_phai_hut_100_phan_tram(db):
    """Dòng chưa nhập thực chi là dòng CHƯA XONG, không phải dòng tiết kiệm được toàn bộ tiền."""
    _dong(db, "Chưa nhập thực chi", 9_000_000, None)
    kq = SDC.soat_dong(db, TOUR)
    assert not kq["hut"]
    assert kq["chua_co_du_toan"][0]["vi_sao"] == "chưa nhập thực chi"


def test_d10_hai_nguong_khai_RIENG_khong_lay_tri_tuyet_doi(db):
    """Vượt và hụt là hai chuyện nghiệp vụ khác nhau nên ngưỡng khác nhau."""
    kq = SDC.soat_dong(db, TOUR)
    assert kq["nguong_vuot"] == pytest.approx(0.10)
    assert kq["nguong_hut"] == pytest.approx(0.15)
    assert kq["nguong_vuot"] != kq["nguong_hut"]


# =============================================================================================
# Đ-7 · THU HỘ – CHI HỘ
# =============================================================================================

def test_d7_thu_ho_KHONG_phai_doanh_thu(db):
    """Hàng rào chính: một hàm duy nhất trả lời 'dòng này có vào doanh thu không'."""
    assert THC.la_doanh_thu("hop_dong") is True
    assert THC.la_doanh_thu("tip_cong_ty") is True
    assert THC.la_doanh_thu("thu_ho") is False
    assert "thu_ho" in LOAI_DOANH_THU


def test_d7_so_du_tach_theo_chu_tien(db):
    """Visa lẻ T5/2026 có cột 'Thu hộ chi hộ': 821.500 đ và 1.200.000 đ."""
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", noi_dung="Thu hộ mua vé",
                            thanh_tien=821_500, chu_tien="PHAM TIEN QUAN",
                            han_xu_ly=date(2026, 6, 30)))
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", noi_dung="Thu hộ dịch công chứng",
                            thanh_tien=1_200_000, chu_tien="PHAN NGOC HUNG",
                            han_xu_ly=date(2026, 6, 30)))
    db.commit()
    sd = THC.so_du(db, TOUR, date(2026, 6, 1))
    assert sd["da_thu_ho"] == pytest.approx(2_021_500)
    assert {x["chu_tien"] for x in sd["theo_chu_tien"]} == {"PHAM TIEN QUAN", "PHAN NGOC HUNG"}


def test_d7_chi_dung_viec_thi_so_du_ve_0(db):
    """Tệp UK: TL thu của khách 126 GBP rồi mua đúng vé tham quan cho họ."""
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", noi_dung="TL thu của khách",
                            thanh_tien=4_536_000, chu_tien="Khách đoàn UK",
                            han_xu_ly=date(2026, 6, 30)))
    db.add(TourHdvChi(tour_id=TOUR, noi_dung="Mua hộ vé tham quan", thanh_tien=4_536_000,
                      thu_ho_khach=1, chu_tien="Khách đoàn UK"))
    db.commit()
    sd = THC.so_du(db, TOUR, date(2026, 6, 1))
    assert sd["so_du"] == 0
    assert THC.soat(db, TOUR, date(2026, 6, 1))["so_canh_bao"] == 0


def test_d7_so_du_con_treo_TRONG_HAN_thi_KHONG_keu(db):
    """Thu hôm nay, trả ngày mai — đó là hoạt động bình thường, không phải lỗi.

    Đây là chỗ bản đề xuất đầu ngày 12/9 đã sai (đề nghị CHẶN) và làn Codex bác đúng.
    """
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", thanh_tien=1_000_000,
                            chu_tien="Chị Lan", han_xu_ly=date(2026, 7, 30)))
    db.commit()
    kq = THC.soat(db, TOUR, date(2026, 7, 1))
    assert kq["so_du"] == pytest.approx(1_000_000)
    assert kq["duoc_dong_so"] is True
    assert kq["so_canh_bao"] == 0, "còn trong hạn thì không kêu"


def test_d7_qua_han_thi_CANH_BAO_co_ten_nguoi(db):
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", thanh_tien=1_000_000,
                            chu_tien="Chị Lan", han_xu_ly=date(2026, 7, 1)))
    db.commit()
    kq = THC.soat(db, TOUR, date(2026, 8, 1))
    assert kq["so_canh_bao"] == 1
    assert kq["canh_bao"][0]["chu_tien"] == "Chị Lan"
    assert kq["duoc_dong_so"] is True, "quá hạn là việc phải làm, không phải hàng rào"


def test_d7_khong_dat_han_thi_CANH_BAO(db):
    """Số dư không có hạn thì nằm đó mãi và không bao giờ thành việc của ai."""
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", thanh_tien=500_000, chu_tien="Anh Hùng"))
    db.commit()
    kq = THC.soat(db, TOUR)
    assert kq["so_canh_bao"] == 1 and "HẠN" in kq["canh_bao"][0]["vi_sao"]


def test_d7_KHONG_BIET_CUA_AI_la_cho_DUY_NHAT_bi_chan(db):
    """Không có chủ thì không trả lại được cho ai."""
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", thanh_tien=821_500))
    db.commit()
    kq = THC.soat(db, TOUR)
    assert kq["duoc_dong_so"] is False and kq["so_chan"] == 1
    assert "CHỦ TIỀN" in kq["chan"][0]["vi_sao"]


def test_d7_chu_tien_RONG_khong_duoc_doc_thanh_cua_cong_ty(db):
    """Đọc rỗng thành 'của công ty' là biến tiền của khách thành doanh thu mà không ai bấm nút nào."""
    db.add(TourDoanhThuDong(tour_id=TOUR, loai="thu_ho", thanh_tien=821_500))
    db.commit()
    sd = THC.so_du(db, TOUR)
    assert sd["so_du"] == pytest.approx(821_500), "vẫn là số dư treo, không biến thành doanh thu"
    assert THC.soat(db, TOUR)["so_chan"] == 1


# =============================================================================================
# Đ-11 · CHỨNG TỪ GẮN VÀO TỪNG DÒNG
# =============================================================================================

def test_d11_danh_muc_dinh_kem_co_khoa_cho_DONG_CHI_PHI():
    """Trước bản này kho hồ sơ gắn được vào CHUYẾN, không gắn được vào DÒNG."""
    from app.models.attachments import DOI_TUONG, DOI_TUONG_DAY_DU
    assert "dong_chi_phi" in DOI_TUONG_DAY_DU
    assert "dong_chi_phi" in DOI_TUONG
    ten, phong, nhom, theo_ma = DOI_TUONG_DAY_DU["dong_chi_phi"]
    assert phong == "dieu_hanh" and nhom == "05_Tour"
    assert theo_ma is True, "id của dòng chi sống cùng chuyến, không thuộc về một tháng"


def test_d11_KHONG_dung_kho_tep_thu_hai():
    """Hai kho tệp thì lần sửa quy tắc lưu trữ đầu tiên sẽ sửa một kho và quên kho kia."""
    from app.api.v1 import quyet_toan_lop3 as R
    duong = {getattr(r, "path", "") for r in R.router.routes}
    assert any(p.endswith("/chung-tu-dong-chi") for p in duong)
    assert not any("tai-chung-tu" in p or "upload" in p for p in duong), \
        "cửa tải phải là /api/v1/tep đã có, không dựng cửa tải riêng ở đây"


def test_d11_ba_duong_moi_deu_co_mat():
    from app.api.v1 import quyet_toan_lop3 as R
    duong = {getattr(r, "path", "") for r in R.router.routes}
    for p in ("/soat-du-chi", "/thu-ho", "/chung-tu-dong-chi"):
        assert any(x.endswith(p) for x in duong), f"thiếu đường {p}"


# =============================================================================================
# Bản nâng cấp — mạch phải MỘT đầu
# =============================================================================================

def test_mach_nang_cap_chi_co_MOT_dau():
    """Đã gãy hai lần trong ngày 11/9, cả hai lần đều vì hai làn nối vào cùng một cha.

    Alembic gặp hai đầu thì `upgrade head` DỪNG — máy chủ không lên được, và phép thử nào không
    chạm cơ sở dữ liệu thật vẫn xanh.
    """
    import pathlib
    import re
    goc = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    rev, cha = set(), set()
    for p in goc.glob("*.py"):
        s = p.read_text(encoding="utf-8", errors="replace")
        r = re.search(r'^revision(?::\s*str)?\s*=\s*["\']([^"\']+)', s, re.M)
        d = re.search(r'^down_revision(?::\s*[^=]+)?\s*=\s*(?:["\']([^"\']+)["\']|None)', s, re.M)
        if r:
            rev.add(r.group(1))
            if d and d.group(1):
                cha.add(d.group(1))
    dau = sorted(rev - cha)
    assert len(dau) == 1, f"MẠCH NÂNG CẤP CÓ {len(dau)} ĐẦU: {dau}. Sửa down_revision của bản vào sau."
    mo_coi = sorted(cha - rev)
    assert not mo_coi, f"down_revision trỏ tới bản không tồn tại: {mo_coi}"
