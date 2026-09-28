"""TC-91 · BIỂU ĐỒ PHẤN ĐẤU CỦA NHÂN VIÊN KINH DOANH — Chủ tịch chốt 28/9/2026.

Nguyên văn yêu cầu: "mức 500 triệu/nhân viên kinh doanh lẻ, 50 triệu lợi nhuận cho /nvkd đoàn …
để cho nv thấy được động lực phấn đấu hằng ngày theo biểu đồ doanh thu của mình".

Và một lựa chọn thứ hai, hỏi lại rồi mới làm: hai con số ấy là ĐÍCH PHẤN ĐẤU, KHÔNG phải mốc tính
tiền. Mốc tính tiền giữ nguyên 200tr/120tr/20tr. Phân biệt ấy là thứ phép thử này canh gắt nhất,
vì hai bộ số nằm cạnh nhau trong cùng một bảng và chênh nhau đúng 2,5 lần.

NĂM CHỖ NGUY HIỂM — đều thuộc loại nhìn màn hình KHÔNG thấy:

 1. ĐÍCH BỊ DÙNG ĐỂ TÍNH TIỀN. Nâng mốc chỉ tiêu lên 2,5 lần thì thang f đẩy hoa hồng của hầu hết
    nhân viên về 0. `test_dich_khong_duoc_dung_trong_tinh_luong` đọc mã và chặn ngay ở mức nguồn.

 2. CHƯA KHAI ĐÍCH MÀ HIỆN 0%. "Chưa giao đích" và "giao rồi mà chưa bán được đồng nào" là hai
    tình huống ngược nhau. Rỗng, không phải 0.

 3. HAI LUẬT VĂN PHÒNG. Đích phải chia HCM/tỉnh bằng ĐÚNG hàm `hr.moc_of` mà mốc tiền đang dùng.
    Viết lại luật "hcm hay không" lần thứ hai thì một ngày Bình Dương sẽ nằm hai bên.

 4. ĐOÀN BỊ ĐO BẰNG DOANH THU. Tour đoàn giá trị lớn nhưng biên mỏng; đo doanh thu là dạy nhân
    viên bán rẻ để chạy số. Chủ tịch chốt đoàn đo LỢI NHUẬN.

 5. LỢI NHUẬN DỰ KIẾN BỊ GỘP VÀO LỢI NHUẬN THẬT. Lợi nhuận đoàn chỉ chắc sau quyết toán. Gộp hai
    lớp vào một đường là tạo một con số đẹp mà không ai kiểm được.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Param, Tour, User
from app.models.hr import Employee
from app.services import doanh_thu_kd as DT
from app.services import hr as HR
from app.services import rules as R


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e, future=True)()
    R.seed_params(db)
    return db


def _dat(db, key, value):
    db.add(Param(key=key, value=str(value), label=key, unit="", effective_from=dt.date.today(),
                 source="test", status="active", signed_chutich=True, signed_tgd=True,
                 proposed_by="test"))
    db.commit()
    R.clear_param_cache()


def _u(db, ten, office="hcm"):
    u = User(username=ten, full_name=ten, role="nv_kd", password_hash="x")
    db.add(u); db.commit()
    db.add(Employee(code="NV" + str(u.id), user_id=u.id, full_name=ten, office=office,
                    department="kd")); db.commit()
    return u


def _tour(db, ma, ket_thuc, loai="le_noi_dia"):
    t = Tour(code=ma, name=ma, tour_type=loai,
             start_date=ket_thuc - dt.timedelta(days=2), end_date=ket_thuc,
             operator_id=1, status="ket_thuc")
    db.add(t); db.commit()
    return t


def _bk(db, ma, t, u, tien):
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="K", customer_phone="0900000000", source="thu",
                pax=2, amount=tien, cancelled=False, counts_for_target=True,
                sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


# ── 1. Đích KHÔNG được chạm vào tiền ────────────────────────────────────────────

def test_dich_khong_duoc_dung_trong_tinh_luong():
    """Hàng rào ở mức NGUỒN: ba khóa đích không được xuất hiện trong mã tính lương.

    Không đòi đổi gì — nó khóa một ranh giới. Ngày ai đó "thống nhất cho gọn" bằng cách cho payroll
    đọc `dich_dt_nv_le_hcm`, phép thử này đỏ trước khi bảng lương chạy sai.
    """
    ma_luong = open(HR.__file__, encoding="utf-8").read()
    for khoa in ("dich_dt_nv_le_hcm", "dich_dt_nv_le_tinh", "dich_ln_nv_doan"):
        assert khoa not in ma_luong, (
            f"{khoa} là ĐÍCH PHẤN ĐẤU, không phải mốc tính tiền — nó vừa lọt vào mã tính lương")


def test_moc_tinh_tien_van_nguyen_gia_tri_cu():
    db = _db()
    assert R.get_param(db, "moc_chi_tieu_hcm") == 200_000_000
    assert R.get_param(db, "moc_chi_tieu_cantho") == 120_000_000
    assert R.get_param(db, "hh_doan_moc") == 20_000_000


def test_ba_dich_moi_dung_con_so_chu_tich_chot():
    db = _db()
    assert R.get_param(db, "dich_dt_nv_le_hcm") == 500_000_000
    assert R.get_param(db, "dich_dt_nv_le_tinh") == 300_000_000
    assert R.get_param(db, "dich_ln_nv_doan") == 50_000_000


# ── 2. Rỗng khác không ──────────────────────────────────────────────────────────

def test_dat_dich_ve_0_la_cach_TAT_va_tra_RONG_khong_phai_0():
    """Đặt đích = 0 trên màn hình Chính sách là cách tắt vạch đích mà không phải sửa mã.

    `get_param` luôn có giá trị mặc định lấy từ `DEFAULT_PARAMS`, nên "chưa khai" không xảy ra
    được với ba khóa này — cửa tắt duy nhất là đặt về 0. Và 0 phải trả RỖNG: "không giao đích"
    khác hẳn "giao đích bằng không", hiện cùng một con số 0% là sai.
    """
    db = _db(); u = _u(db, "an")
    _dat(db, "dich_dt_nv_le_hcm", 0)
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "le")
    assert kq["dich"] is None, "chưa khai đích thì phải rỗng"
    assert kq["dat_pct"] is None, "không có đích thì không có phần trăm đạt"
    assert all(d["nhip"] is None for d in kq["diem"]), "không có đích thì không vẽ được nhịp"


# ── 3. Một luật văn phòng, dùng chung với mốc tiền ──────────────────────────────

@pytest.mark.parametrize("office,mong_doi", [
    ("hcm", 500_000_000), ("binhduong", 500_000_000),
    ("cantho", 300_000_000), ("hanoi", 300_000_000),
])
def test_dich_theo_van_phong_dung_chung_luat_voi_moc_tien(office, mong_doi):
    db = _db(); u = _u(db, "nv_" + office, office)
    assert DT.nhip_cua_nguoi(db, u.id, "2026-09", "le")["dich"] == mong_doi


def test_dung_dung_ham_moc_of_chu_khong_viet_lai_luat():
    ma = open(DT.__file__, encoding="utf-8").read()
    assert "moc_of" in ma, "phải gọi hr.moc_of, không tự viết lại luật hcm/binhduong"
    assert '"binhduong"' not in ma, "luật văn phòng bị chép lần thứ hai vào doanh_thu_kd"


# ── 4. Nhịp cần đi ──────────────────────────────────────────────────────────────

def test_nhip_ngay_n_bang_dich_nhan_n_chia_so_ngay():
    db = _db(); u = _u(db, "an")
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "le")       # tháng 9 có 30 ngày
    assert len(kq["diem"]) == 30
    assert kq["diem"][14]["nhip"] == pytest.approx(500_000_000 * 15 / 30)
    assert kq["diem"][-1]["nhip"] == pytest.approx(500_000_000)


def test_luy_ke_khop_tong_cua_nguoi_va_khong_bao_gio_giam():
    db = _db(); u = _u(db, "an")
    t1 = _tour(db, "T1", dt.date(2026, 9, 10)); _bk(db, "B1", t1, u, 60_000_000)
    t2 = _tour(db, "T2", dt.date(2026, 9, 20)); _bk(db, "B2", t2, u, 40_000_000)
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "le")
    luy = [d["luy_ke"] for d in kq["diem"]]
    assert luy == sorted(luy), "lũy kế không được giảm"
    assert luy[-1] == 100_000_000
    assert luy[-1] == DT.cua_nguoi(db, u.id, "2026-09")["tien"], "phải khớp con số tính chỉ tiêu"
    assert kq["dat_pct"] == pytest.approx(20.0)


# ── 5. Đoàn đo LỢI NHUẬN, và hai lớp không gộp ──────────────────────────────────

def test_doan_do_loi_nhuan_khong_phai_doanh_thu():
    db = _db(); u = _u(db, "doan1")
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "doan")
    assert kq["thuoc_do"] == "loi_nhuan"
    assert kq["dich"] == 50_000_000


def test_doan_tach_da_quyet_toan_va_du_kien():
    db = _db(); u = _u(db, "doan1")
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "doan")
    d = kq["diem"][0]
    assert "luy_ke" in d and "luy_ke_du_kien" in d, (
        "đoàn phải có HAI lớp: đã quyết toán và dự kiến — gộp là tạo một con số không ai kiểm được")


def test_le_khong_co_lop_du_kien():
    db = _db(); u = _u(db, "an")
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "le")
    assert kq["thuoc_do"] == "doanh_thu"
    assert kq["diem"][0].get("luy_ke_du_kien") is None


def test_chia_loi_nhuan_doan_dung_mot_ham_chung():
    assert R.ln_doan_cua_booking(10_000_000, 100_000_000, 25_000_000) == pytest.approx(2_500_000)
    assert R.ln_doan_cua_booking(10_000_000, 0, 25_000_000) == 0.0, "chia cho 0 phải trả 0"


def test_khong_con_ban_sao_nao_cua_phep_chia_loi_nhuan_doan():
    """Luật chia tiền chỉ được có MỘT bản.

    Ngày 28/9/2026 công thức này đang nằm chép ba lần: bảng lương, bảng thưởng Điều hành, và biểu
    đồ phấn đấu. Ba bản sao của một luật chia tiền là ba nơi có thể lệch — và chỗ lệch im lặng, vì
    cả ba đều trông hợp lý, chỉ khác con số. Phép thử này đếm, không đọc hiểu: chuỗi công thức thô
    không được xuất hiện ở đâu nữa ngoài chính hàm chung.
    """
    tho = '(b.amount or 0) / (s["revenue"] or 0)'
    for mod in (HR, R, DT):
        assert tho not in open(mod.__file__, encoding="utf-8").read(), (
            f"{mod.__name__} còn một bản sao phép chia lợi nhuận đoàn — phải gọi R.ln_doan_cua_booking")
    assert "ln_doan_cua_booking" in open(DT.__file__, encoding="utf-8").read()
    assert "ln_doan_cua_booking" in open(HR.__file__, encoding="utf-8").read()


# ── 6. Cửa này không nhận user_id từ ngoài ──────────────────────────────────────

def test_ky_sai_thi_bao_loi_ro_chu_khong_am_tham_tra_rong():
    db = _db(); u = _u(db, "an")
    with pytest.raises(ValueError):
        DT.nhip_cua_nguoi(db, u.id, "thang chin", "le")


# ── 7. Nấc thang: nhiều mức, không trần ────────────────────────────────────────

def test_thang_le_doc_tu_bang_chinh_sach_chu_khong_chep_lai():
    db = _db()
    nac = DT.thang_nac(db, "le", None)
    assert len(nac) == 20, "thang lẻ có 20 nấc trong thang_f_bang"
    assert nac[0]["pct_moc"] == 65 and nac[-1]["pct_moc"] == 1000
    ma = open(DT.__file__, encoding="utf-8").read()
    assert "thang_f_bang" in ma and "65:0,70:0" not in ma, "không được chép bảng vào mã"


def test_hoa_hong_moi_nac_tinh_tren_PHAN_VUOT_MOC():
    """Hoa hồng = hệ số × (doanh thu − MỐC), không phải × doanh thu.

    Chép nhầm chỗ này là hứa với nhân viên một số tiền không có thật — ở nấc f5 sai gấp 11 lần.
    """
    db = _db()
    f5 = [n for n in DT.thang_nac(db, "le", None) if n["pct_moc"] == 110][0]
    assert f5["nguong"] == 220_000_000 and f5["he_so"] == pytest.approx(0.005)
    assert f5["hoa_hong_uoc"] == 100_000, "0,5% × (220tr − 200tr) = 100 nghìn, KHÔNG phải 1,1 triệu"
    f9 = [n for n in DT.thang_nac(db, "le", None) if n["pct_moc"] == 250][0]
    assert f9["hoa_hong_uoc"] == 5_100_000


def test_dich_chi_DANH_DAU_mot_nac_chu_khong_cat_thang():
    db = _db()
    nac = DT.thang_nac(db, "le", 500_000_000)
    danh_dau = [n for n in nac if n["la_dich"]]
    assert len(danh_dau) == 1 and danh_dau[0]["pct_moc"] == 250, "500 triệu là nấc f9, 250% mốc"
    tren_dich = [n for n in nac if n["nguong"] > 500_000_000]
    assert len(tren_dich) == 11, "trên đích phải còn 11 nấc — một vạch đích là một cái trần"


def test_thang_doan_lay_tu_phu_luc_A_va_KHONG_dung_tinh_tien():
    db = _db()
    nac = DT.thang_nac(db, "doan", 50_000_000)
    assert len(nac) == 11, "Phụ lục A có 11 bậc: f0…f9 và Đạt"
    dat = [n for n in nac if n["bac"] == "Đạt"][0]
    assert dat["nguong"] == 30_000_000, "Đạt = chỉ tiêu 30 triệu, Điều 4"
    assert all(n["y_nghia"] == "phần trăm lương cơ bản" for n in nac)
    # Hoa hồng đoàn TUYẾN TÍNH 10% phần vượt 20 triệu — Điều 7 cố ý bỏ bậc nhảy.
    assert dat["hoa_hong_uoc"] == 1_000_000, "10% × (30tr − 20tr)"


def test_doan_xep_bac_theo_BINH_QUAN_BA_THANG_khong_phai_thang_don():
    """Điều 5: một đoàn lớn mất hai ba tháng mới ra lợi nhuận, nên chấm theo bình quân ba tháng.

    Xếp bậc theo tháng đơn là đúng cái Điều 5 cố ý tránh — và sẽ lệch với phiếu lương.
    """
    db = _db(); u = _u(db, "doan1")
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "doan")
    assert kq["co_so_xep_bac"] == "binh_quan_3_thang"
    bq = kq["binh_quan_3_thang"]
    assert bq is not None and bq["so_ky"] == 3
    assert [x["ky"] for x in bq["cac_ky"]] == ["2026-07", "2026-08", "2026-09"]


def test_le_xep_bac_theo_thang_va_khong_co_binh_quan():
    db = _db(); u = _u(db, "an")
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "le")
    assert kq["co_so_xep_bac"] == "luy_ke_thang"
    assert kq["binh_quan_3_thang"] is None


def test_luon_con_nac_phia_truoc_va_bao_con_thieu_bao_nhieu():
    db = _db(); u = _u(db, "an")
    t = _tour(db, "T1", dt.date(2026, 9, 10)); _bk(db, "B1", t, u, 250_000_000)
    kq = DT.nhip_cua_nguoi(db, u.id, "2026-09", "le")
    assert kq["bac_dang_o"]["pct_moc"] == 110, "250tr = 125% mốc → đứng ở nấc 110%"
    assert kq["bac_ke_tiep"]["pct_moc"] == 130
    assert kq["bac_ke_tiep"]["con_thieu"] == 10_000_000, "260tr − 250tr"
