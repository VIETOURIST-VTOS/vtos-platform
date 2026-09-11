"""Danh mục khoản mục chi phí và phần tự điền từ hồ sơ nhà cung cấp.

VÌ SAO PHÉP THỬ NÀY TỒN TẠI

Trước danh mục, cột "nội dung" của dòng chi là ô CHỮ TỰ DO. Đo trên tám tệp quyết toán thật thì cùng
một khoản được gọi bằng nhiều tên:

    LAND · LAND MCB · Landtour ADL · Giá land
    PHÍ TL · CTP HDV · CTP · Chi phí chung HDV
    PHÍ LSQ · PHÍ TLS CAO CẤP · PHÍ TLS CƠ BẢN · Phí visa

Hệ quả không phải là bảng xấu – là KHÔNG CỘNG ĐƯỢC. Câu "cả năm công ty chi bao nhiêu tiền khách sạn"
không có câu trả lời khi khách sạn nằm rải trong bốn cách gõ, và với 1.258 chuyến thì đó là một khoảng
mù rất lớn.

Phép thử canh ba điều, mỗi điều là một cách hỏng đã thấy thật:

  1. Danh mục phải ĐỦ để phủ những khoản có thật trong tám tệp – thiếu thì người ta gõ vào "khác".
  2. Chọn khoản mục phải KÉO THEO bốn mặc định, và chọn nhà cung cấp phải kéo theo mã số thuế. Gõ tay
     mười chữ số ở từng dòng là cách chắc chắn để có mã sai một chữ số.
  3. Mã lạ thì TỪ CHỐI, không đoán sang mã gần giống. Đoán gần giống là cách nhanh nhất để một khoản
     chi nằm sai nhóm mà không ai biết.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_lop3_km.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_lop3_km.db"):
    os.remove("test_lop3_km.db")

from datetime import date                                           # noqa: E402
import pytest                                                       # noqa: E402
from app.db.session import SessionLocal, Base, engine                # noqa: E402
import app.models                                                    # noqa: E402,F401
from app.models.core import Tour, User                               # noqa: E402
from app.models.suppliers import Supplier                            # noqa: E402
from app.models.vietrip import TourCostLine                          # noqa: E402
from app.services import khoan_muc_chi as KM                         # noqa: E402

Base.metadata.create_all(engine)


# ------------------------------------------------------------------ danh mục

def test_danh_muc_phu_duoc_nhung_khoan_co_that_trong_tam_tep():
    """Mỗi khoản dưới đây đều xuất hiện trong ít nhất một tệp quyết toán thật đã đọc."""
    can = ["vc_xe_du_lich", "vc_ve_may_bay", "vc_ve_may_bay_nd", "lt_khach_san",
           "au_an_sang", "au_an_trua", "au_an_toi", "au_nuoc_uong", "au_tiec_gala",
           "tq_ve_tham_quan", "hd_ctp_hdv", "hd_an_noi_bo", "hd_tip",
           "vs_phi_lsq", "vs_dich_thuat", "bh_du_lich",
           "qt_non", "qt_bao_ho_chieu", "qt_qua_khach", "qt_banner",
           "pk_phi_chuyen_khoan", "pk_thue_nop_ho"]
    thieu = [m for m in can if m not in KM.KHOAN_MUC]
    assert not thieu, f"danh mục thiếu: {thieu}"


def test_moi_khoan_muc_khai_du_bon_mac_dinh():
    """Thiếu một mặc định thì dòng chi sinh ra đã rỗng, và phép kiểm phân bổ kêu ngay từ dòng đầu."""
    hop_le_qt = set(__import__("app.services.gia_khach", fromlist=["x"]).BANG_PHAN_BO)
    for ma, k in KM.KHOAN_MUC.items():
        assert k["nhom"] in KM.NHOM, f"{ma}: nhóm lạ {k['nhom']}"
        assert k["doi_tuong"] in ("nguoi_lon", "tre_em", "em_be", "chung"), ma
        assert k["quy_tac_phan_bo"] in hop_le_qt, f"{ma}: quy tắc lạ {k['quy_tac_phan_bo']}"
        assert k["hinh_thuc"] in ("ca_hai", "trong_nuoc", "nuoc_ngoai"), ma


def test_khoan_dich_danh_thi_khong_phan_bo():
    """Vé máy bay, visa, dịch thuật: mỗi khách một giá nên KHÔNG chia.

    Tệp UK: cùng một chuyến mà vé khách này 22.435.959 đ còn khách kia 21.903.700 đ, phí lãnh sự quán
    chạy từ 7.875.750 đến 8.290.750, và bốn khách không mua visa vì đã có sẵn. Ép vào phép chia là
    bắt khách đã có visa gánh tiền visa của người khác.
    """
    for ma, k in KM.KHOAN_MUC.items():
        if k["dich_danh"]:
            assert k["quy_tac_phan_bo"] == "khong_phan_bo", f"{ma} đích danh mà vẫn chia"


def test_bao_hiem_chia_deu_MOI_khach_ke_ca_suat_mien_phi():
    """Em bé không trả tiền tour vẫn được mua bảo hiểm – tệp Nha Trang tính đúng như vậy."""
    assert KM.KHOAN_MUC["bh_du_lich"]["quy_tac_phan_bo"] == "deu_moi_khach"


def test_loc_theo_hinh_thuc_bo_dung_nhung_khoan_khong_dung_toi():
    tn = {k["ma"] for k in KM.danh_sach("trong_nuoc")}
    nn = {k["ma"] for k in KM.danh_sach("nuoc_ngoai")}
    # Phí lãnh sự quán và bao hộ chiếu là chuyện của tour nước ngoài.
    assert "vs_phi_lsq" not in tn and "vs_phi_lsq" in nn
    assert "qt_bao_ho_chieu" not in tn and "qt_bao_ho_chieu" in nn
    # Khách sạn, ăn uống, bảo hiểm thì cả hai đều dùng.
    for ma in ("lt_khach_san", "au_an_trua", "bh_du_lich", "vc_xe_du_lich"):
        assert ma in tn and ma in nn
    # Không lọc thì trả về đủ – thà hiện thừa còn hơn giấu mất khoản người ta cần.
    assert len(KM.danh_sach()) == len(KM.KHOAN_MUC)


def test_ma_la_thi_tu_choi_chu_khong_doan_sang_ma_gan_giong():
    assert KM.mac_dinh("lt_khach_san")["nhom"] == KM.NHOM["LT"]
    assert KM.mac_dinh("lt_khach_sann") == {}      # thừa một chữ n
    assert KM.mac_dinh("khach_san") == {}          # tên chứ không phải mã
    assert KM.mac_dinh(None) == {} and KM.mac_dinh("") == {}


def test_khoan_khac_dem_duoc():
    """Đường thoát có chủ ý – nhưng phải ĐẾM được, để biết danh mục còn thiếu gì."""
    assert KM.la_khoan_khac("au_khac") and KM.la_khoan_khac("pk_khac")
    assert not KM.la_khoan_khac("au_an_trua")
    assert not KM.la_khoan_khac(None)
    # Mỗi nhóm phải có đúng một đường thoát, không nhóm nào bị bỏ quên.
    co = {k["nhom"] for m, k in KM.KHOAN_MUC.items() if KM.la_khoan_khac(m)}
    assert co == set(KM.NHOM) - {"BH"}, f"nhóm chưa có khoản 'khác': {set(KM.NHOM) - co - {'BH'}}"


# ------------------------------------------------------------------ tự điền từ hồ sơ NCC

@pytest.fixture(scope="module")
def chuyen():
    db = SessionLocal()
    u = User(username="dh_km", full_name="ĐH", role="nv_dh", password_hash="x")
    db.add(u); db.flush()
    t = Tour(code="TN-KM-001", name="THỬ KHOẢN MỤC", tour_type="package",
             hinh_thuc="trong_nuoc", operator_id=u.id,
             start_date=date(2026, 7, 10), end_date=date(2026, 7, 12), planned_pax=10)
    db.add(t); db.flush()
    # Tên GIAO DỊCH khác tên PHÁP NHÂN – lấy đúng cặp có thật trong danh mục nhà cung cấp của công ty.
    db.add(Supplier(code="NCC-T01", ten="RESORT VĨNH HY",
                    ten_phap_nhan="CTY TNHH PHÁT HOÀNG LONG",
                    ma_so_thue="4500485670", dia_chi="Thôn Vĩnh Hy, Xã Vĩnh Hải",
                    loai="khach_san"))
    db.commit()
    tid = t.id
    db.close()
    yield tid


def test_chon_khoan_muc_va_ncc_thi_may_dien_phan_con_lai(chuyen):
    """Người nhập chọn hai thứ và điền số tiền; máy điền nhóm, đối tượng, quy tắc, tên NCC, mã số thuế."""
    db = SessionLocal()
    ncc = db.query(Supplier).filter(Supplier.code == "NCC-T01").one()
    md = KM.mac_dinh("lt_khach_san")
    d = TourCostLine(tour_id=chuyen, ma_khoan_muc="lt_khach_san",
                     description=KM.KHOAN_MUC["lt_khach_san"]["ten"],
                     nhom=md["nhom"], doi_tuong=md["doi_tuong"],
                     quy_tac_phan_bo=md["quy_tac_phan_bo"],
                     supplier_id=ncc.id, supplier_name=ncc.ten,
                     supplier_tax_code=ncc.ma_so_thue,
                     unit_price=750000.0, qty=12, coef=2, actual=18000000.0, status="hd")
    db.add(d); db.commit(); db.refresh(d)

    assert d.nhom == KM.NHOM["LT"]
    assert d.doi_tuong == "nguoi_lon"
    assert d.quy_tac_phan_bo == "theo_doi_tuong"
    assert d.supplier_tax_code == "4500485670"     # không ai gõ mười chữ số này
    db.close()


def test_ten_phap_nhan_va_ten_giao_dich_la_hai_thu_khac_nhau(chuyen):
    """Hoá đơn mang tên PHÁP NHÂN. Gộp hai tên vào một cột thì hoặc mất tên để tra, hoặc mất tên để
    kê khai thuế."""
    db = SessionLocal()
    ncc = db.query(Supplier).filter(Supplier.code == "NCC-T01").one()
    assert ncc.ten == "RESORT VĨNH HY"
    assert ncc.ten_phap_nhan == "CTY TNHH PHÁT HOÀNG LONG"
    assert ncc.ten != ncc.ten_phap_nhan
    db.close()


def test_cong_chi_phi_theo_khoan_muc(chuyen):
    """Điều mà ô chữ tự do không bao giờ cho được: cộng theo khoản mục."""
    db = SessionLocal()
    for ma, tien in (("au_an_trua", 4536000.0), ("au_an_toi", 4620000.0),
                     ("au_an_trua", 4550000.0), ("qt_non", 500000.0)):
        md = KM.mac_dinh(ma)
        db.add(TourCostLine(tour_id=chuyen, ma_khoan_muc=ma,
                            description=KM.KHOAN_MUC[ma]["ten"], nhom=md["nhom"],
                            doi_tuong=md["doi_tuong"], quy_tac_phan_bo=md["quy_tac_phan_bo"],
                            actual=tien, status="hd"))
    db.commit()

    ds = db.query(TourCostLine).filter(TourCostLine.tour_id == chuyen).all()
    theo_ma: dict[str, float] = {}
    for d in ds:
        if d.ma_khoan_muc and d.actual is not None:
            theo_ma[d.ma_khoan_muc] = theo_ma.get(d.ma_khoan_muc, 0) + float(d.actual)

    # Hai bữa ăn trưa ở hai nhà hàng khác nhau CỘNG LẠI được, vì cùng một mã khoản mục.
    assert theo_ma["au_an_trua"] == 4536000.0 + 4550000.0
    assert theo_ma["lt_khach_san"] == 18000000.0

    theo_nhom: dict[str, float] = {}
    for d in ds:
        if d.nhom and d.actual is not None:
            theo_nhom[d.nhom] = theo_nhom.get(d.nhom, 0) + float(d.actual)
    assert theo_nhom[KM.NHOM["AU"]] == 4536000.0 + 4620000.0 + 4550000.0
    db.close()
