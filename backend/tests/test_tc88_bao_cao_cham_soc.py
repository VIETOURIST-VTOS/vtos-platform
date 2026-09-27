"""TC-88 · NĂM DÒNG CHĂM SÓC TRÊN BẢNG CHỈ TIÊU — và vì sao không có dòng "điểm trung bình".

Đề xuất tự động hoá CSKH 25/9/2026 có bước 7: báo cáo tự động hằng tuần gửi Ban lãnh đạo. Anh Tuấn
chốt 27/9: KHÔNG làm báo cáo gửi đi — báo cáo hằng ngày đã có sẵn trong `bao_cao_phong.py`, đúng
quyết định của Chủ tịch 09/9: báo cáo HIỆN trên màn hình, không gửi mail hay Zalo. Nên việc còn
lại chỉ là thêm dòng vào bảng đã có.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO BỐN TRONG NĂM DÒNG KHÔNG ĐO MỨC HÀI LÒNG
═══════════════════════════════════════════════════════════════════════════════════════════════
Đề xuất bỏ bộ phận chăm sóc riêng và giao việc gọi lại khách chấm thấp cho CHÍNH NGƯỜI ĐÃ BÁN tour
ấy. Mục 6 của chính đề xuất nhận ra rủi ro: hai phòng ấy có thể ít báo lên hơn, vì họ vừa bán vừa
vận hành. Một bảng chỉ có điểm trung bình KHÔNG BAO GIỜ lộ ra điều đó — điểm trung bình đẹp lên khi
người không hài lòng thôi trả lời, và đó là hướng nó tự trôi tới mà không ai làm gì sai cả.

Nên bốn dòng đo phần CÓ THỂ TRÔI: bao nhiêu khách thật sự trả lời, bao nhiêu điểm do nhân viên gõ
hộ, bao nhiêu phiếu chấm thấp còn treo, bao nhiêu chuyến không ai nói gì.

PHÉP THỬ NÀY CANH SÁU CHỖ:
 1. Năm dòng có mặt ở CẢ bảng Marketing lẫn bảng toàn công ty, và dùng CHUNG một hàm — chép công
    thức lần thứ hai là mở đường cho hai bảng nói hai số khác nhau về cùng một việc.
 2. Mẫu số của tỷ lệ trả lời chỉ đếm lời mời ĐÃ GỬI THẬT. Tin còn kẹt trong hàng đợi mà tính vào
    mẫu số là tự hạ tỷ lệ vì một lỗi cấu hình — con số khi ấy không nói gì về khách.
 3. Chưa gửi lời mời nào thì tỷ lệ là RỖNG, không phải 0. Rỗng nghĩa là chưa đo được.
 4. `hai_long = 0` là CHƯA CHẤM, không phải chấm 0 điểm — không được đếm vào nhóm 1–3 sao.
 5. Ghi hộ nhiều hơn khách tự chấm thì phải lên mức ĐỎ: phần điểm ấy do người bị đo nhập vào.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour, User
from app.models.crm import ZaloMessage
from app.models.cskh import CareTicket, Complaint
from app.models.danh_gia import DanhGiaSauTour
from app.services import bao_cao_phong as BC

HOM_NAY = dt.date.today()
TU, DEN = HOM_NAY - dt.timedelta(days=7), HOM_NAY


@pytest.fixture()
def db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    yield s
    s.close()


def _tour(db, ma):
    u = User(username="op" + ma, full_name="Op", role="nv_dh", password_hash="x")
    db.add(u); db.commit()
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=HOM_NAY - dt.timedelta(days=3),
             end_date=HOM_NAY - dt.timedelta(days=1), operator_id=u.id, status="ket_thuc")
    db.add(t); db.commit()
    return t


def _moi(db, n, trang_thai="da_gui"):
    for i in range(n):
        db.add(ZaloMessage(kind="zns", phone=f"0900{i:04d}", purpose="cham_soc", status=trang_thai))
    db.commit()


def _cham(db, t, care_id, nguon="khach", diem=5):
    db.add(DanhGiaSauTour(care_id=care_id, booking_id=care_id, tour_id=t.id, doi_tuong="tour",
                          doi_tuong_ten="Chuyến", diem=diem, nguon=nguon))
    db.commit()


def _lay(ds, ma):
    return next((x for x in ds if x["ma"] == ma), None)


def test_tc88_1_nam_dong_co_o_ca_hai_bang_va_dung_chung_mot_ham(db):
    mkt = BC._marketing(db, TU, DEN)
    cty = BC._toan_cty(db, TU, DEN)
    for ma in ("cs_ty_le_tra_loi", "cs_ghi_ho", "cs_thap_treo", "cs_im_lang", "cs_zalo_ket"):
        assert _lay(mkt, ma), f"bang Marketing thieu dong {ma}"
        assert _lay(cty, ma), f"bang toan cong ty thieu dong {ma}"
    ma_nguon = open(BC.__file__, encoding="utf-8").read()
    assert ma_nguon.count("def _cskh_dong") == 1, "chep cong thuc lan hai la mo duong cho hai so lech nhau"


def test_tc88_2_tin_ket_khong_tinh_vao_mau_so(db):
    t = _tour(db, "T1")
    _moi(db, 10, "da_gui")
    _moi(db, 90, "cho_cau_hinh")      # ket trong hang doi - KHONG phai loi moi
    for i in range(1, 6):
        _cham(db, t, care_id=i)

    ds = BC._marketing(db, TU, DEN)
    assert _lay(ds, "cs_ty_le_tra_loi")["gia_tri"] == 0.5, \
        "mau so phai la 10 tin da gui, khong phai 100 tin da xep"
    assert _lay(ds, "cs_zalo_ket")["gia_tri"] == 90
    assert _lay(ds, "cs_zalo_ket")["muc"] == "do"


def test_tc88_3_chua_gui_thi_rong_khong_phai_khong(db):
    ds = BC._marketing(db, TU, DEN)
    o = _lay(ds, "cs_ty_le_tra_loi")
    assert o["gia_tri"] is None, "chua gui loi moi nao thi la CHUA DO DUOC, khong phai 0%"
    assert o["muc"] == "", "rong thi khong to mau canh bao"


def test_tc88_4_diem_0_la_chua_cham_khong_phai_1_3_sao(db):
    t = _tour(db, "T2")
    db.add(CareTicket(booking_id=1, tour_id=t.id, han_lien_he=HOM_NAY, hai_long=0, status="moi"))
    db.add(CareTicket(booking_id=2, tour_id=t.id, han_lien_he=HOM_NAY, hai_long=2, status="moi"))
    db.commit()
    assert _lay(BC._marketing(db, TU, DEN), "cs_thap_treo")["gia_tri"] == 1, \
        "phieu chua cham (hai_long=0) bi dem nham vao nhom 1-3 sao"


def test_tc88_5_ghi_ho_nhieu_hon_khach_tu_cham_thi_do(db):
    t = _tour(db, "T3")
    _moi(db, 10, "da_gui")
    _cham(db, t, care_id=1, nguon="khach")
    for i in (2, 3, 4):
        _cham(db, t, care_id=i, nguon="nhan_vien")

    o = _lay(BC._marketing(db, TU, DEN), "cs_ghi_ho")
    assert o["gia_tri"] == 3
    assert o["muc"] == "do", "ghi ho nhieu hon khach tu cham ma bang van xanh thi bang khong do gi"


def test_tc88_6_chuyen_khong_ai_cham_phai_dem_duoc(db):
    t1, t2 = _tour(db, "T4"), _tour(db, "T5")
    _cham(db, t1, care_id=1)
    assert _lay(BC._marketing(db, TU, DEN), "cs_im_lang")["gia_tri"] == 1, \
        "chuyen khong ai cham la cho mu cua diem trung binh - phai dem duoc"

def test_tc88_7_dem_duoc_nguoi_xu_ly_tu_dong_ho_so_cua_minh(db):
    """Anh Tuấn chốt 27/9: độc lập bằng TẦM NHÌN, không bằng hàng rào — nên đo, không chặn.

    Mức 3 đã bị `cskh.dong()` cấm tự đóng từ trước. Mức 1–2 cố ý để mở; dòng này là thứ làm cho
    lựa chọn ấy có nghĩa. Không đếm được thì "để mở" chỉ là để đó.
    """
    bay_gio = dt.datetime.now()
    # Sale ban tour tu dong ho so cua chinh minh
    db.add(Complaint(code="KN-1", source="cham_soc", customer_name="A", nhom="hdv", level=1,
                     noi_dung="x", handler="sale.a", closed_by="sale.a", status="da_dong",
                     closed_at=bay_gio))
    # Nguoi khac dong - khong tinh
    db.add(Complaint(code="KN-2", source="cham_soc", customer_name="B", nhom="hdv", level=1,
                     noi_dung="x", handler="sale.b", closed_by="tp.kd", status="da_dong",
                     closed_at=bay_gio))
    # Nguon khac - ngoai pham vi dong nay
    db.add(Complaint(code="KN-3", source="dien_thoai", customer_name="C", nhom="xe", level=1,
                     noi_dung="x", handler="sale.c", closed_by="sale.c", status="da_dong",
                     closed_at=bay_gio))
    db.commit()

    o = _lay(BC._marketing(db, TU, DEN), "cs_tu_dong")
    assert o["gia_tri"] == 1, "chi dem ho so tu phieu cham soc ma nguoi xu ly nam trong nguoi ky dong"
    assert o["muc"] == "vang"
    assert any("KN-1" in x for x in (o["chi_tiet"] or [])), "phai chi ra duoc ho so nao, khong chi mot con so"
    assert _lay(BC._toan_cty(db, TU, DEN), "cs_tu_dong"), "Ban Giam doc va Chu tich phai thay dong nay"
