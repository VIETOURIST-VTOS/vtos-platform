# -*- coding: utf-8 -*-
"""DT-1 + DT-3 · Bốn mốc, tiền được phép sử dụng, mức dự phòng — bản sửa 13/9/2026.

Tệp này canh những chỗ sai theo CHIỀU NGUY HIỂM, tức là sai về phía làm người đọc kết luận nhầm:

  1. TRỪ LỆNH CHI HAI LẦN — lỗi thật của bản 11/9. Số dư cuối THẤP HƠN sự thật, dẫn tới đi vay
     một khoản không cần vay. Bộ phép thử ở mục 3 dựng đúng tình huống ấy bằng số.
  2. Trừ một khoản hạn chế CHƯA TỪNG ĐƯỢC CỘNG (ký quỹ ở tài khoản ngoài tập chốt số dư).
  3. Tính "ngày đầu tiên thiếu tiền" ở bốn mốc lũy kế — hụt giữa khoảng biến mất.
  4. Xử THU và CHI đối xứng nhau — phải thu quá hạn không mặc định thu được ngay.
  5. Cộng cả số gốc của một nghĩa vụ đã trả một phần.
"""
from datetime import date, datetime

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
# 1. Bốn mốc — LŨY KẾ, không phải nối tiếp
# =============================================================================================

def test_bon_moc_dung_ten_va_dung_thu_tu():
    assert KY.MA_MOC == ["7n", "14n", "1t", "2t"]
    assert [m["nhan"] for m in KY.cac_khoang(XEM)] == ["1 tuần", "2 tuần", "1 tháng", "2 tháng"]


def test_moc_sau_CHUA_moc_truoc_chu_khong_noi_tiep():
    ks = {m["ma"]: (m["tu"], m["den"]) for m in KY.cac_khoang(XEM)}
    assert all(t == XEM for t, _ in ks.values()), "mọi cột phải bắt đầu từ chính ngày xem"
    den = [ks[m][1] for m in KY.MA_MOC]
    assert den == sorted(den) and len(set(den)) == 4


def test_ca_hai_dau_deu_duoc_tinh_khong_lech_mot_ngay():
    d, c = KY.khoang(XEM, "7n")
    assert (d, c) == (date(2026, 9, 11), date(2026, 9, 17))
    assert (c - d).days + 1 == 7
    assert KY.khoang(XEM, "14n")[1] == date(2026, 9, 24)


def test_mot_thang_la_thang_LICH_chu_khong_phai_30_ngay():
    assert KY.khoang(XEM, "1t")[1] == date(2026, 10, 11)
    assert KY.khoang(XEM, "2t")[1] == date(2026, 11, 11)
    assert KY.khoang(date(2026, 1, 31), "1t")[1] == date(2026, 2, 28)
    assert KY.khoang(date(2028, 1, 31), "1t")[1] == date(2028, 2, 29), "2028 nhuận"
    assert KY.khoang(date(2026, 12, 15), "2t")[1] == date(2027, 2, 15), "phải qua được năm mới"


def test_nghia_vu_den_han_DUNG_HOM_NAY_nam_trong_cot_mot_tuan():
    assert KY.xep_moc(XEM, XEM) == "7n"


def test_moc_la_thi_bao_loi_chu_khong_tra_bua():
    with pytest.raises(ValueError) as e:
        KY.khoang(XEM, "3t")
    assert "7n" in str(e.value)


# =============================================================================================
# 2. Quá hạn và thiếu ngày — THU và CHI KHÔNG đối xứng
# =============================================================================================

def test_qua_han_tach_rieng_chu_khong_nhet_vao_cot_mot_tuan():
    assert KY.xep_moc(date(2026, 8, 1), XEM) == KY.QUA_HAN


def test_CHI_qua_han_cong_vao_MOI_cot():
    """v1.1: khoản quá hạn hiển thị riêng VÀ tính vào nhu cầu thanh toán."""
    assert KY.luy_ke(KY.QUA_HAN, KY.CHI) == KY.MA_MOC


def test_THU_qua_han_KHONG_cong_vao_cot_nao():
    """Chỗ bản 11/9 sai: xử thu và chi đối xứng nhau. Tiền RA mình quyết, tiền VÀO thì không —
    mặc định một khoản phải thu quá hạn sẽ thu được ngay là làm bảng đẹp hơn sự thật."""
    assert KY.luy_ke(KY.QUA_HAN, KY.THU) == []
    assert KY.luy_ke(KY.QUA_HAN, KY.CHI) != KY.luy_ke(KY.QUA_HAN, KY.THU)


def test_khoan_khong_co_ngay_vao_ro_rieng_chu_khong_bi_bo_qua_am_tham():
    assert KY.xep_moc(None, XEM) == KY.CHUA_DU_DU_LIEU
    assert KY.luy_ke(KY.CHUA_DU_DU_LIEU) == []


def test_ro_thieu_ngay_phai_hien_TONG_GIA_TRI():
    """Một rổ không có số đọc như một rổ rỗng."""
    r = KY.ro_chua_du_du_lieu([{"con_phai_tra": 30_000_000}, {"con_phai_tra": 12_500_000}])
    assert r["so_dong"] == 2 and r["tong"] == 42_500_000
    assert "42.500.000" in r["cau"]
    assert KY.ro_chua_du_du_lieu([])["tong"] == 0


def test_luy_ke_cong_don_len_cac_cot_xa_hon():
    assert KY.luy_ke("14n") == ["14n", "1t", "2t"]
    assert KY.luy_ke("7n") == KY.MA_MOC
    assert KY.luy_ke("2t") == ["2t"]


def test_khoan_xa_hon_hai_thang_chua_vao_bang_nhung_khong_mat():
    assert KY.xep_moc(date(2027, 5, 1), XEM) == ""
    assert KY.luy_ke("") == []


# =============================================================================================
# 3. LỖI TRỪ HAI LẦN — phép thử quan trọng nhất tệp này
# =============================================================================================

CO_BAN = {"so_du_ngan_hang": 100_000_000, "tien_mat": 0,
          "thu_ho_khach": 0, "ky_quy_lu_hanh": 0}
TRONG = {"thu_ho_khach": True, "ky_quy_lu_hanh": True}


def test_so_dau_ky_KHONG_tru_lenh_chi():
    """Ví dụ của người phản biện, bằng đúng số: 100 − 20 rồi dự báo trừ 20 nữa = 60, THẤP HƠN
    sự thật 20 triệu. Số đầu kỳ phải là 100, không phải 80."""
    a = KY.tien_duoc_phep_su_dung(CO_BAN, TRONG, date(2026, 9, 10),
                                  datetime(2026, 9, 10, 17, 0), ["VCB-001"])
    assert a["so"] == 100_000_000, "số đầu kỳ đã bị trừ lệnh chi – lỗi trừ hai lần quay lại"
    chuoi = KY.chuoi_so_du_theo_ngay(a["so"], {date(2026, 9, 15): -20_000_000}, XEM, 10)
    assert chuoi[-1]["so_du"] == 80_000_000, "sau khi chi 20 phải còn 80, không phải 60"


def test_B_tru_lenh_chi_nhung_KHONG_duoc_dung_lam_dau_ky():
    a = KY.tien_duoc_phep_su_dung(CO_BAN, TRONG, date(2026, 9, 10),
                                  datetime(2026, 9, 10, 17, 0), ["VCB-001"])
    b = KY.tien_con_bo_tri_moi(a, 20_000_000)
    assert b["so"] == 80_000_000 and b["da_tru_lenh_chi"] == 20_000_000
    assert b["dung_lam_dau_ky"] is False, "cờ này là hàng rào cuối chặn lỗi trừ hai lần"
    assert "không dùng làm số đầu kỳ" in b["cau"].lower()


def test_hai_chi_tieu_co_TEN_KHAC_NHAU_de_khong_ai_lay_nham():
    a = KY.tien_duoc_phep_su_dung(CO_BAN, TRONG)
    b = KY.tien_con_bo_tri_moi(a, 20_000_000)
    assert a["nhan"] != b["nhan"]
    assert a["chi_tieu"] == "tien_duoc_phep_su_dung"
    assert b["chi_tieu"] == "tien_con_bo_tri_moi"


# =============================================================================================
# 4. Khoản hạn chế chỉ trừ khi THỰC SỰ nằm trong số dư đã đếm
# =============================================================================================

def test_ky_quy_o_tai_khoan_NGOAI_tap_da_dem_thi_KHONG_tru():
    """Trừ một khoản chưa từng được cộng là làm tiền khả dụng thấp hơn sự thật."""
    g = dict(CO_BAN, ky_quy_lu_hanh=500_000_000)
    a = KY.tien_duoc_phep_su_dung(g, {"thu_ho_khach": True, "ky_quy_lu_hanh": False},
                                  date(2026, 9, 10), datetime(2026, 9, 10, 17, 0), ["VCB-001"])
    assert a["so"] == 100_000_000
    dong = {d["ma"]: d for d in a["chi_tiet"]}
    assert dong["ky_quy_lu_hanh"]["co_tru"] is False


def test_ky_quy_NAM_TRONG_tap_da_dem_thi_CO_tru():
    g = dict(CO_BAN, ky_quy_lu_hanh=30_000_000)
    a = KY.tien_duoc_phep_su_dung(g, TRONG, date(2026, 9, 10),
                                  datetime(2026, 9, 10, 17, 0), ["VCB-001", "VCB-KQ"])
    assert a["so"] == 70_000_000


def test_CHUA_BIET_khoan_han_che_nam_o_dau_thi_KHONG_RA_SO():
    """Đoán 'có' thì trừ thừa, đoán 'không' thì trừ thiếu; cả hai cho một con số không ai kiểm
    được."""
    g = dict(CO_BAN, ky_quy_lu_hanh=30_000_000)
    a = KY.tien_duoc_phep_su_dung(g, {"thu_ho_khach": True}, date(2026, 9, 10))
    assert a["du_du_lieu"] is False and a["hien"] == KY.CHUA_XAC_MINH
    assert "so" not in a, "trả 'so': None thì nơi nhận rất dễ viết `so or 0`"
    assert a["chua_ro_vi_tri"] == ["ky_quy_lu_hanh"]
    assert "ký quỹ" in a["cau_thieu"]


def test_thieu_mot_thanh_phan_la_KHONG_ra_so():
    g = dict(CO_BAN); g["tien_mat"] = None
    a = KY.tien_duoc_phep_su_dung(g, TRONG, date(2026, 9, 10))
    assert a["du_du_lieu"] is False and "so" not in a
    assert "Tiền mặt" in a["cau_thieu"]


def test_so_khong_KHAC_han_voi_chua_co():
    a = KY.tien_duoc_phep_su_dung(dict(CO_BAN, tien_mat=0), TRONG, date(2026, 9, 10),
                                  datetime(2026, 9, 10, 17, 0), ["VCB-001"])
    assert a["du_du_lieu"] is True and a["so"] == 100_000_000


def test_thieu_ba_thu_ghi_nho_thi_canh_bao_du_ba_cau():
    a = KY.tien_duoc_phep_su_dung(CO_BAN, TRONG)
    c = a["canh_bao"]
    assert "mốc đối soát" in c and "mốc giờ chốt" in c and "danh sách tài khoản" in c


# =============================================================================================
# 5. Mốc chốt số dư — giao dịch tại mốc không được đếm lại
# =============================================================================================

MOC = datetime(2026, 9, 10, 17, 0)


def test_giao_dich_DUNG_TAI_moc_chot_KHONG_vao_du_bao():
    """Nó đã nằm trong số dư đầu kỳ rồi."""
    assert KY.sau_moc_chot(MOC, MOC) is False


def test_giao_dich_truoc_moc_khong_vao_sau_moc_thi_vao():
    assert KY.sau_moc_chot(datetime(2026, 9, 10, 16, 59), MOC) is False
    assert KY.sau_moc_chot(datetime(2026, 9, 10, 17, 1), MOC) is True


def test_khong_co_moc_thi_khong_chan_gi():
    assert KY.sau_moc_chot(datetime(2026, 9, 1), None) is True


# =============================================================================================
# 6. Thanh toán một phần
# =============================================================================================

def test_du_bao_PHAN_CON_LAI_chu_khong_phai_so_goc():
    """Cộng cả số gốc của một nghĩa vụ đã trả một phần là phóng đại nhu cầu tiền đúng bằng phần
    đã trả."""
    assert KY.con_phai_tra(100_000_000, 30_000_000) == 70_000_000
    assert KY.con_phai_tra(100_000_000, None) == 100_000_000


def test_tong_nghia_vu_rong_la_CHUA_AI_NHAP_chu_khong_phai_khong_no():
    assert KY.con_phai_tra(None, 0) is None


# =============================================================================================
# 7. Ngày đầu tiên thiếu tiền — phải tính THEO NGÀY
# =============================================================================================

def test_hut_tien_GIUA_khoang_van_bi_bat():
    """Đây là chỗ bản 11/9 sai về phương pháp. Ngày 20/9 hụt xuống −5 triệu rồi 25/9 tiền về;
    nhìn ở điểm cuối mốc thì số dư dương, ngày hụt biến mất."""
    chuoi = KY.chuoi_so_du_theo_ngay(
        10_000_000,
        {date(2026, 9, 20): -15_000_000, date(2026, 9, 25): +40_000_000},
        XEM, 30)
    cuoi = chuoi[-1]["so_du"]
    assert cuoi == 35_000_000, "nhìn ở điểm cuối thì mọi thứ đều ổn"
    r = KY.ngay_dau_thieu_tien(chuoi)
    assert r["co_thieu"] is True
    assert r["ngay"] == date(2026, 9, 20)
    assert r["muc_thieu_lon_nhat"] == 5_000_000


def test_ngay_dau_tien_va_muc_sau_nhat_la_HAI_con_so_khac_nhau():
    """Ngày đầu tiên trả lời 'khi nào', mức sâu nhất trả lời 'cần xoay bao nhiêu'. Ngày thiếu đầu
    tiên có thể chỉ hụt vài đồng."""
    chuoi = KY.chuoi_so_du_theo_ngay(
        1_000, {date(2026, 9, 12): -1_001, date(2026, 9, 18): -9_000_000}, XEM, 20)
    r = KY.ngay_dau_thieu_tien(chuoi)
    assert r["ngay"] == date(2026, 9, 12)
    assert r["ngay_thieu_nhieu_nhat"] == date(2026, 9, 18)
    assert r["muc_thieu_lon_nhat"] == 9_000_001


def test_khong_ngay_nao_thieu_thi_noi_ro():
    chuoi = KY.chuoi_so_du_theo_ngay(50_000_000, {}, XEM, 10)
    r = KY.ngay_dau_thieu_tien(chuoi)
    assert r["co_thieu"] is False and "Không có ngày nào thiếu" in r["hien"]


def test_chuoi_phu_het_hai_thang_khi_khong_noi_so_ngay():
    chuoi = KY.chuoi_so_du_theo_ngay(0, {}, XEM)
    assert chuoi[0]["ngay"] == XEM
    assert chuoi[-1]["ngay"] == KY.khoang(XEM, "2t")[1]


# =============================================================================================
# 8. Mức dự phòng tối thiểu — hai chữ ký, theo từng pháp nhân
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
    _dat_nguong(db, 1, "")
    assert KY.muc_du_phong(db, 1, date(2026, 9, 11))["co_nguong"] is False


# =============================================================================================
# 9. Dòng THIẾU SO VỚI MỨC DỰ PHÒNG
# =============================================================================================

def test_khong_co_nguong_thi_dong_THIEU_khong_tinh_duoc(db):
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    t = KY.thieu_so_voi_du_phong(2_000_000_000, n)
    assert t["tinh_duoc"] is False and t["hien"] == KY.CHUA_CO_NGUONG
    assert "so" not in t, "trả số 0 thì dòng THIẾU luôn báo đủ"


def test_dang_thieu_thi_tra_so_DUONG(db):
    _dat_nguong(db, 1, 3_000_000_000)
    n = KY.muc_du_phong(db, 1, date(2026, 9, 11))
    t = KY.thieu_so_voi_du_phong(2_000_000_000, n)
    assert t["so"] == 1_000_000_000 and t["du"] is False and t["hien"] == "1.000.000.000"


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
# 10. Hai góc nhìn — và dời lịch không xoá dấu quá hạn
# =============================================================================================

def test_hai_tab_co_hai_nhan_so_du_KHAC_nhau():
    a, b = KY.nhan_so_du(KY.CAM_KET), KY.nhan_so_du(KY.THUC_HIEN)
    assert a != b and "đúng hạn" in a and "kế hoạch" in b.lower()


def test_hai_tab_doc_HAI_COT_NGAY_khac_nhau():
    assert KY.CO_SO_NGAY[KY.CAM_KET]["cot_ngay"] == "ngay_cam_ket"
    assert KY.CO_SO_NGAY[KY.THUC_HIEN]["cot_ngay"] == "ngay_du_kien_tra"


def test_doi_lich_tra_KHONG_xoa_dau_qua_han_theo_cam_ket():
    """v1.1 mục IV.4 cấm thẳng. Nhãn quá hạn nói về lời đã hứa với bên kia, không nói về kế hoạch
    của mình."""
    nv = {"ngay_cam_ket": date(2026, 8, 1), "ngay_du_kien_tra": date(2026, 10, 1)}
    assert KY.con_qua_han_sau_khi_doi_lich(nv, XEM) is True
    assert KY.con_qua_han_sau_khi_doi_lich({"ngay_cam_ket": date(2026, 10, 5)}, XEM) is False


def test_co_so_ngay_la_thi_bao_loi():
    with pytest.raises(ValueError):
        KY.nhan_so_du("tuy_y")
