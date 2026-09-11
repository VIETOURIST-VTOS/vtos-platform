# -*- coding: utf-8 -*-
"""DT-1 + DT-3 · Bốn mốc lũy kế, tiền khả dụng, mức dự phòng tối thiểu.

Ba chỗ tệp này canh, và cả ba đều là chỗ sai theo CHIỀU NGUY HIỂM – tức là sai về phía làm người
đọc yên tâm hơn sự thật:

  1. Bốn cột hiểu thành nối tiếp thay vì lũy kế. Khi ấy cột "2 tháng" nhẹ hơn cột "1 tháng", và
     người đọc kết luận ngược hẳn về tình hình tiền.
  2. Tiền khả dụng tính thiếu một thành phần TRỪ. Con số luôn CAO HƠN sự thật, đúng theo chiều
     làm người ta yên tâm chi.
  3. "Chưa có ngưỡng dự phòng" biến thành "ngưỡng bằng 0". Khi ấy dòng THIẾU luôn báo đủ.
"""
from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
from app.models.core import Param
from app.services import dong_tien_ky as KY


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:", poolclass=sa.pool.StaticPool,
                           connect_args={"check_same_thread": False})
    md.create_all(eng)
    with Session(eng) as s:
        yield s


XEM = date(2026, 9, 11)


# =============================================================================================
# 1. Bốn mốc – LŨY KẾ, không phải nối tiếp
# =============================================================================================

def test_bon_moc_dung_ten_va_dung_thu_tu_theo_v11():
    assert KY.MA_MOC == ["7n", "14n", "1t", "2t"]
    assert [m["nhan"] for m in KY.cac_khoang(XEM)] == ["1 tuần", "2 tuần", "1 tháng", "2 tháng"]


def test_moc_sau_CHUA_moc_truoc_chu_khong_noi_tiep():
    """Hiểu nhầm chỗ này thì cột '2 tháng' chỉ còn nghĩa vụ của tháng thứ hai, và nó luôn nhỏ hơn
    cột '1 tháng' – một bảng mà cột xa hơn lại nhẹ hơn."""
    ks = {m["ma"]: (m["tu"], m["den"]) for m in KY.cac_khoang(XEM)}
    assert all(t == XEM for t, _ in ks.values()), "mọi cột phải bắt đầu từ chính ngày xem"
    den = [ks[m][1] for m in KY.MA_MOC]
    assert den == sorted(den) and len(set(den)) == 4, "bốn ngày cuối phải tăng dần và khác nhau"


def test_ca_hai_dau_deu_duoc_tinh_khong_lech_mot_ngay():
    """7 ngày kể từ hôm nay là hôm nay + 6 ngày nữa, không phải + 7."""
    d, c = KY.khoang(XEM, "7n")
    assert (d, c) == (date(2026, 9, 11), date(2026, 9, 17))
    assert (c - d).days + 1 == 7
    assert KY.khoang(XEM, "14n")[1] == date(2026, 9, 24)


def test_mot_thang_la_thang_LICH_chu_khong_phai_30_ngay():
    assert KY.khoang(XEM, "1t")[1] == date(2026, 10, 11)
    assert KY.khoang(XEM, "2t")[1] == date(2026, 11, 11)


def test_ngay_31_cong_mot_thang_bi_kep_ve_cuoi_thang_ngan():
    """Dùng 30 ngày cho gọn thì mọi kỳ trả gốc rơi vào ngày 29–31 sẽ nhảy qua nhảy lại giữa hai cột
    tùy tháng, và không ai truy ra được vì sao."""
    assert KY.khoang(date(2026, 1, 31), "1t")[1] == date(2026, 2, 28)
    assert KY.khoang(date(2028, 1, 31), "1t")[1] == date(2028, 2, 29), "2028 là năm nhuận"
    assert KY.khoang(date(2026, 12, 15), "2t")[1] == date(2027, 2, 15), "phải qua được năm mới"


def test_nghia_vu_den_han_DUNG_HOM_NAY_nam_trong_cot_mot_tuan():
    """Nó là khoản gấp nhất trong bảng – rơi ra ngoài là rơi đúng chỗ nguy nhất."""
    assert KY.xep_moc(XEM, XEM) == "7n"


def test_mot_moc_hop_le_la_thi_bao_loi_chu_khong_tra_bua():
    with pytest.raises(ValueError) as e:
        KY.khoang(XEM, "3t")
    assert "7n" in str(e.value), "câu lỗi phải chỉ ra bốn mốc hợp lệ"


# =============================================================================================
# 2. Quá hạn và thiếu ngày – không được rơi ra ngoài bảng
# =============================================================================================

def test_qua_han_tach_rieng_chu_khong_nhet_vao_cot_mot_tuan():
    """'Phải trả trong tuần này' và 'lẽ ra phải trả từ tháng trước' là hai tình trạng khác nhau;
    gộp lại thì cái thứ hai biến mất."""
    assert KY.xep_moc(date(2026, 8, 1), XEM) == KY.QUA_HAN


def test_qua_han_van_duoc_cong_vao_MOI_cot():
    """v1.1: khoản quá hạn hiển thị riêng VÀ tính vào nhu cầu thanh toán. Nó là tiền đang phải trả,
    không phải tiền của một cột nào."""
    assert KY.luy_ke(KY.QUA_HAN) == KY.MA_MOC


def test_khoan_khong_co_ngay_den_han_vao_ro_rieng_chu_khong_bi_bo_qua_am_tham():
    assert KY.xep_moc(None, XEM) == KY.CHUA_DU_DU_LIEU
    assert KY.luy_ke(KY.CHUA_DU_DU_LIEU) == [], "không có ngày thì không được cộng vào cột nào"


def test_luy_ke_cong_don_len_cac_cot_xa_hon():
    """Một khoản đến hạn trong 10 ngày nằm trong cột 2 tuần, 1 tháng và 2 tháng – KHÔNG nằm ở cột
    1 tuần."""
    assert KY.luy_ke("14n") == ["14n", "1t", "2t"]
    assert KY.luy_ke("7n") == KY.MA_MOC
    assert KY.luy_ke("2t") == ["2t"]


def test_khoan_xa_hon_hai_thang_chua_vao_bang_nhung_khong_mat():
    assert KY.xep_moc(date(2027, 5, 1), XEM) == ""
    assert KY.luy_ke("") == []


# =============================================================================================
# 3. DT-1 · Tiền khả dụng
# =============================================================================================

DU = {"so_du_ngan_hang": 5_000_000_000, "tien_mat": 120_000_000,
      "thu_ho_khach": 800_000_000, "ky_quy_lu_hanh": 500_000_000,
      "lenh_chi_chua_chuyen": 1_300_000_000}


def test_cong_thuc_dung_nam_thanh_phan_theo_v11():
    r = KY.tien_kha_dung(DU, date(2026, 9, 10))
    assert r["du_du_lieu"] is True
    assert r["so"] == 5_000_000_000 + 120_000_000 - 800_000_000 - 500_000_000 - 1_300_000_000
    assert r["so"] == 2_520_000_000
    assert r["hien"] == "2.520.000.000"


def test_thieu_MOT_thanh_phan_la_KHONG_ra_so():
    """Thành phần dễ thiếu nhất là một số TRỪ. Bỏ nó đi thì tiền khả dụng LUÔN CAO HƠN sự thật,
    đúng theo chiều làm người ta yên tâm chi."""
    g = dict(DU); g["lenh_chi_chua_chuyen"] = None
    r = KY.tien_kha_dung(g, date(2026, 9, 10))
    assert r["du_du_lieu"] is False
    assert r["hien"] == KY.CHUA_XAC_MINH
    assert "so" not in r, "trả 'so': None thì nơi nhận rất dễ viết `so or 0`"
    assert "lệnh chi" in r["cau_thieu"]


def test_cau_thieu_goi_ten_dung_thanh_phan_con_thieu():
    g = dict(DU); g["tien_mat"] = None; g["thu_ho_khach"] = None
    r = KY.tien_kha_dung(g)
    assert set(r["thieu"]) == {"tien_mat", "thu_ho_khach"}
    assert "Tiền mặt" in r["cau_thieu"] and "thu hộ khách" in r["cau_thieu"]


def test_so_khong_KHAC_han_voi_chua_co():
    """Số 0 và 'chưa ai điền' trông giống nhau trên màn hình, và cái giống nhau ấy là cách một bảng
    thiếu dữ liệu biến thành một bảng nói rằng mọi thứ đều ổn."""
    g = dict(DU); g["tien_mat"] = 0
    r = KY.tien_kha_dung(g, date(2026, 9, 10))
    assert r["du_du_lieu"] is True and r["so"] == 2_400_000_000


def test_khong_ghi_moc_doi_soat_thi_phai_canh_bao():
    """Một con số tiền khả dụng không kèm ngày đối soát là một con số không biết mình cũ bao nhiêu."""
    r = KY.tien_kha_dung(DU)
    assert "canh_bao" in r and "mốc đối soát" in r["canh_bao"]
    assert "canh_bao" not in KY.tien_kha_dung(DU, date(2026, 9, 10))


def test_moi_thanh_phan_deu_co_dau_va_ly_do():
    assert [d for _m, d, _t, _l in KY.THANH_PHAN] == [1, 1, -1, -1, -1]
    for ma, _d, ten, ly_do in KY.THANH_PHAN:
        assert len(ly_do) >= 40, f"{ma}: khai mà không nói vì sao"
        assert ten.strip()


# =============================================================================================
# 4. Mức dự phòng tối thiểu – hai chữ ký, theo từng pháp nhân
# =============================================================================================

def _dat_nguong(db, company_id, gia_tri, tgd=True, ct=True, tu=date(2026, 1, 1)):
    db.add(Param(key=KY._khoa_theo_phap_nhan(company_id), value=str(gia_tri),
                 label="Mức dự phòng tối thiểu", effective_from=tu))
    db.flush()
    p = db.execute(sa.select(Param).order_by(Param.id.desc())).scalars().first()
    p.signed_tgd, p.signed_chutich = tgd, ct
    db.flush()
    return p


def test_chua_ai_chot_thi_ghi_CHUA_CO_NGUONG_chu_khong_phai_so_khong(db):
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    assert n["co_nguong"] is False and n["hien"] == KY.CHUA_CO_NGUONG
    assert "Chưa ai chốt" in n["cau"]


def test_thieu_mot_chu_ky_thi_CHUA_co_hieu_luc(db):
    """Chủ tịch chốt 11/9: hai chữ ký là Tổng giám đốc + Chủ tịch."""
    _dat_nguong(db, 1, 3_000_000_000, tgd=True, ct=False)
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    assert n["co_nguong"] is False
    assert "hai chữ ký" in n["cau"] and "Chủ tịch" in n["cau"]


def test_du_hai_chu_ky_thi_co_nguong(db):
    _dat_nguong(db, 1, 3_000_000_000)
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    assert n["co_nguong"] is True and n["so"] == 3_000_000_000
    assert n["hieu_luc_tu_hien"] == "01-01-2026"


def test_nguong_theo_TUNG_phap_nhan(db):
    """Một ngưỡng chung cho cả nhóm sai hai chiều cùng lúc: công ty nhỏ bị báo thiếu suốt, công ty
    lớn thì không bao giờ được báo."""
    _dat_nguong(db, 1, 3_000_000_000)
    assert KY.muc_du_phong(db, 1, date(2026, 9, 11))["co_nguong"] is True
    assert KY.muc_du_phong(db, 2, date(2026, 9, 11))["co_nguong"] is False


def test_ban_chua_toi_ngay_hieu_luc_thi_chua_dung(db):
    _dat_nguong(db, 1, 3_000_000_000, tu=date(2026, 12, 1))
    assert KY.muc_du_phong(db, 1, date(2026, 9, 11))["co_nguong"] is False
    assert KY.muc_du_phong(db, 1, date(2026, 12, 5))["co_nguong"] is True


def test_co_hai_ban_thi_lay_ban_hieu_luc_gan_nhat(db):
    _dat_nguong(db, 1, 3_000_000_000, tu=date(2026, 1, 1))
    _dat_nguong(db, 1, 5_000_000_000, tu=date(2026, 7, 1))
    assert KY.muc_du_phong(db, 1, date(2026, 9, 11))["so"] == 5_000_000_000


def test_gia_tri_rong_khong_duoc_coi_la_da_chot(db):
    """Hai mốc vận hành cố ý để trống chờ chữ ký; một tham số trống mà tính là đã chốt thì nó thành
    ngưỡng 0."""
    _dat_nguong(db, 1, "")
    assert KY.muc_du_phong(db, 1, date(2026, 9, 11))["co_nguong"] is False


# =============================================================================================
# 5. Dòng THIẾU SO VỚI MỨC DỰ PHÒNG
# =============================================================================================

def test_khong_co_nguong_thi_dong_THIEU_khong_tinh_duoc(db):
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    t = KY.thieu_so_voi_du_phong(2_000_000_000, n)
    assert t["tinh_duoc"] is False and t["hien"] == KY.CHUA_CO_NGUONG
    assert "so" not in t, "không có ngưỡng mà trả số 0 thì dòng THIẾU luôn báo đủ"


def test_dang_thieu_thi_tra_so_DUONG(db):
    """Một dòng tên 'thiếu' mang số âm là thứ người đọc phải dừng lại nửa giây để dịch."""
    _dat_nguong(db, 1, 3_000_000_000)
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    t = KY.thieu_so_voi_du_phong(2_000_000_000, n)
    assert t["so"] == 1_000_000_000 and t["du"] is False
    assert t["hien"] == "1.000.000.000"


def test_du_hoac_du_thua_thi_tra_khong_va_noi_ro(db):
    _dat_nguong(db, 1, 3_000_000_000)
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    assert KY.thieu_so_voi_du_phong(3_000_000_000, n)["du"] is True
    assert KY.thieu_so_voi_du_phong(9_000_000_000, n)["so"] == 0


def test_chua_co_so_du_cuoi_thi_cung_khong_tinh_duoc(db):
    _dat_nguong(db, 1, 3_000_000_000)
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    t = KY.thieu_so_voi_du_phong(None, n)
    assert t["tinh_duoc"] is False and t["hien"] == KY.CHUA_XAC_MINH


# =============================================================================================
# 6. Hai góc nhìn – không trộn hai cơ sở ngày
# =============================================================================================

def test_hai_tab_co_hai_nhan_so_du_KHAC_nhau():
    """Hai tab cho hai con số khác nhau cho cùng một khoảng – đó là bình thường. Cái không bình
    thường là hai con số ấy cùng mang một cái nhãn, vì khi đó người đọc thôi không tin bảng nữa."""
    a = KY.nhan_so_du(KY.CAM_KET)
    b = KY.nhan_so_du(KY.THUC_HIEN)
    assert a != b
    assert "đúng hạn" in a and "kế hoạch" in b.lower()


def test_co_so_ngay_la_thi_bao_loi():
    with pytest.raises(ValueError):
        KY.nhan_so_du("tuy_y")
