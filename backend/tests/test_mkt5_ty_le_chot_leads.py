# -*- coding: utf-8 -*-
"""MKT-5 · Tỷ lệ chốt trong `services/leads.py` — canh bốn chỗ đã sửa ngày 18/9/2026.

Tệp này canh MỘT loại lỗi duy nhất: con số sai mà trông như đúng. Cả bốn chỗ dưới đây đều không
làm chương trình đổ — chúng chỉ in ra một số phần trăm bình thường, và người đọc tin nó.

  1. Mẫu số lấy `max(khai_báo, đếm_được)` — chọn con số LỚN HƠN mà không nói đã chọn cái nào.
     Không truy được về nguồn, và tỷ lệ luôn nghiêng về phía thấp.
  2. Tử số đếm SỐ ĐIỆN THOẠI, mẫu số đếm SỐ DÒNG (hoặc số khai báo) — hai đơn vị chia cho nhau.
  3. Khoá `revenue` mang chi tiêu TRỌN ĐỜI của khách, nhưng tên nó đọc như doanh thu của kỳ–kênh.
  4. Báo cáo chỉ có MỘT khoá `rate`, trong khi Chủ tịch đã ký quy tắc `overview-v1` — hai cách
     tính khác nhau cùng một tên, không màn hình nào ghi mình đang dùng cách nào.

SỐ TRONG TỆP NÀY LÀ SỐ DỰNG TAY, chọn cho tròn để đọc ra phép tính bằng mắt. Không dùng số thật
của kỳ nào — số thật biến một phép thử QUY TẮC thành phép thử một ẢNH CHỤP: kỳ sau số khác thì đỏ
mà chẳng có gì hỏng.
"""
from datetime import date, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User  # noqa: F401  – bảng mà khoá ngoại trỏ tới
from app.models.crm import Lead, LeadChannelStat
from app.services import leads as L

KY = "2026-03"          # kỳ phát sinh lead
KENH = "Hotline 1"
THANG_BAO_CAO = "2026-04"


@pytest.fixture()
def db():
    m = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                         connect_args={"check_same_thread": False})
    Base.metadata.create_all(m)
    with Session(m) as s:
        yield s


_dem = [0]


def _dieu_hanh(db) -> User:
    u = db.execute(sa.select(User).where(User.username == "mkt5_dh")).scalars().first()
    if u is None:
        u = User(username="mkt5_dh", full_name="Điều hành thử", role="nv_dh",
                 department="Kiểm thử", password_hash="x", active=True)
        db.add(u); db.flush()
    return u


def _tour(db, ngay: date) -> Tour:
    _dem[0] += 1
    t = Tour(code=f"T{_dem[0]:04d}", name=f"Tour {_dem[0]}", tour_type="package",
             start_date=ngay, end_date=ngay, operator_id=_dieu_hanh(db).id,
             price_per_pax=1_000_000, planned_pax=10, status="da_duyet")
    db.add(t); db.flush(); return t


def _booking(db, sdt: str, khoi_hanh: date, tien: float, tao_luc: datetime | None = None) -> Booking:
    _dem[0] += 1
    t = _tour(db, khoi_hanh); u = _dieu_hanh(db)
    yc = ServiceRequest(tour_id=t.id, sales_id=u.id, customer_name=f"KH {_dem[0]}",
                        customer_phone=sdt, source="test", pax=1)
    db.add(yc); db.flush()
    b = Booking(code=f"B{_dem[0]:04d}", tour_id=t.id, request_id=yc.id, sales_id=u.id,
                source="test", created_by=u.username, customer_name=f"KH {_dem[0]}", customer_phone=sdt, pax=1, amount=tien,
                discount=0, cancelled=False, created_at=tao_luc or datetime(2026, 3, 5))
    db.add(b); db.flush(); return b


def _lead(db, sdt: str, ky: str = KY, kenh: str = KENH) -> Lead:
    l = Lead(phone=sdt, channel=kenh, lead_month=ky, created_by="test")
    db.add(l); db.flush(); return l


# =============================================================================================
# 1. Mẫu số: BỎ max(), và phải nói ra đã lấy mẫu số từ đâu
# =============================================================================================

def test_mau_so_khong_con_lay_con_so_LON_HON_ma_khong_noi_lay_o_dau(db):
    """Đếm được 4 số điện thoại, Marketing khai 10. `max()` cũ trả 10 và im lặng.

    Nay phải trả 10 NHƯNG ghi rõ `nguon_mau_so = "khai_bao"`, và phơi ra phần chênh. Chênh lớn
    nghĩa là tệp nguồn chỉ có phần chi tiết của một số kênh — đó là VIỆC CÒN THIẾU, không phải
    một con số để dùng.
    """
    for i in range(4):
        _lead(db, f"090000000{i}")
    L.set_stat(db, "test", KY, KENH, leads=10)
    db.commit()

    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    a = next(x for x in r["by_channel_month"] if x["channel"] == KENH)
    assert a["so_sdt"] == 4
    assert a["so_khai_bao"] == 10
    assert a["nguon_mau_so"] == "khai_bao"
    assert a["leads"] == 10
    assert a["lech_khai_bao"] == 6, "phần chênh giữa lời khai và số đếm được đang bị san phẳng"


def test_khong_co_khai_bao_thi_lay_so_dem_duoc_va_noi_dung_ten(db):
    for i in range(3):
        _lead(db, f"091000000{i}")
    db.commit()
    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    a = next(x for x in r["by_channel_month"] if x["channel"] == KENH)
    assert a["nguon_mau_so"] == "dem_duoc"
    assert a["leads"] == 3 and a["so_sdt"] == 3
    assert a["lech_khai_bao"] is None, "không có lời khai thì không có phần chênh để nói"


def test_khai_bao_NHO_HON_so_dem_duoc_van_lay_khai_bao_chu_khong_lay_cai_lon(db):
    """Đây là ca mà `max()` cũ làm sai: đếm được 5, khai 2 → max trả 5 và giấu mất mâu thuẫn.

    Nay lấy lời khai (2) và NÓI RA lệch −3. Con số âm ấy là dấu hiệu tệp nguồn khai thiếu — phải
    nhìn thấy được, chứ không phải bị một phép max() nuốt đi.
    """
    for i in range(5):
        _lead(db, f"092000000{i}")
    L.set_stat(db, "test", KY, KENH, leads=2)
    db.commit()
    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    a = next(x for x in r["by_channel_month"] if x["channel"] == KENH)
    assert a["leads"] == 2, "đang lấy lại con số LỚN HƠN — max() đã quay về"
    assert a["so_sdt"] == 5 and a["lech_khai_bao"] == -3


# =============================================================================================
# 2. Tử số và mẫu số phải CÙNG MỘT ĐƠN VỊ
# =============================================================================================

def test_MOT_NGUOI_hai_kenh_trong_mot_thang_van_la_MOT_so_dien_thoai(db):
    """Một người liên hệ qua hai kênh trong cùng tháng: hai dòng, hai kênh — nhưng MỘT người.

    Cộng số người của từng kênh lại thì thành hai. Mức tháng phải đếm lại trên tập hợp, không cộng
    dồn. Lỗi này vô hình vì nó chỉ làm mẫu số to lên một chút, và tỷ lệ chốt nhỏ đi một chút.
    """
    sdt = "0933000001"
    _lead(db, sdt, kenh="Hotline 1")
    _lead(db, sdt, kenh="Zalo OA")
    b = _booking(db, sdt, date(2026, 4, 10), 1_000_000)
    for l in db.execute(sa.select(Lead)).scalars():
        l.booking_id = b.id; l.converted_at = b.created_at
    db.commit()

    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    mm = next(x for x in r["by_month"] if x["lead_month"] == KY)
    assert mm["so_dong"] == 2, "hai dòng là đúng — người ấy liên hệ hai lần qua hai kênh"
    assert mm["so_sdt"] == 1, "đang cộng số người của từng kênh — một người thành hai"
    assert mm["chot_moi_luc"] == 1
    assert mm["ty_le_chot_overview"] == 1.0
    assert mm["ty_le_tren_sdt_dem_duoc"] == 1.0, "mẫu số mức tháng đang lấy số DÒNG, không phải số người"


def test_LAN_LIEN_HE_THU_HAI_cung_ky_cung_kenh_NAY_DA_LUU_DUOC(db):
    """Khách gọi hotline ngày 3 rồi GỌI LẠI ngày 20 cùng tháng — nay lưu được thành HAI dòng.

    LẬT NGƯỢC NGÀY 18/9/2026, và đây là ngày mà bản cũ của chính phép thử này đã hẹn trước.
    Trước hôm nay, ràng buộc `uq_lead_phone_month_channel` từ chối dòng thứ hai, nên một lần liên
    hệ CÓ THẬT biến mất và cửa nhập buộc phải ghi đè lên lần thứ nhất. Bản nâng cấp
    `mkt1a9c4e7b2d63` gỡ ràng buộc ấy và chuyển tính duy nhất sang `ma_lead`.

    Bản cũ viết: "NGÀY NÀO BẢN ẤY LÊN, phép thử này sẽ đỏ — và lúc ấy phải đổi nó thành phép thử
    ngược lại. Đỏ ở đây là TIN TỐT." Hôm nay là ngày ấy, và đây là câu ngược lại.
    """
    sdt = "0933000099"
    _lead(db, sdt)
    db.add(Lead(phone=sdt, channel=KENH, lead_month=KY, created_by="test", note="gọi lại ngày 20"))
    db.commit()                      # KHÔNG còn IntegrityError
    assert db.query(Lead).filter(Lead.phone == sdt, Lead.lead_month == KY).count() == 2, (
        "Hai lần liên hệ thật phải nằm thành hai dòng. Gộp lại là xoá mất một lần có thật.")

def test_khong_co_sdt_nao_thi_ty_le_cung_don_vi_la_KHONG_XAC_DINH_chu_khong_phai_0(db):
    L.set_stat(db, "test", KY, KENH, leads=7)      # khai 7, nhưng không có dòng chi tiết nào
    db.commit()
    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    a = next(x for x in r["by_channel_month"] if x["channel"] == KENH)
    assert a["so_sdt"] == 0
    assert a["ty_le_tren_sdt_dem_duoc"] is None, (
        "0% đọc là 'chạy mà không ra khách'; chưa xác định đọc là 'chưa có dòng nào để đếm'")


# =============================================================================================
# 3. Doanh thu: chi tiêu TRỌN ĐỜI không được đọc như doanh thu của kỳ–kênh
# =============================================================================================

def test_tach_doanh_thu_cua_booking_da_chot_khoi_chi_tieu_tron_doi(db):
    """Khách đã đi một chuyến cũ 5 triệu, nay chốt một chuyến 2 triệu khởi hành trong tháng T.

    `revenue` giữ NGUYÊN nghĩa cũ (trọn đời = 7 triệu) để không bạn đọc nào lặng lẽ đổi ý nghĩa.
    Nhưng phải có thêm một khoá gọi đúng tên phần thuộc về kỳ này: 2 triệu.
    """
    sdt = "0944000001"
    _lead(db, sdt)
    _booking(db, sdt, date(2026, 1, 20), 5_000_000)                    # chuyến cũ
    b = _booking(db, sdt, date(2026, 4, 12), 2_000_000)                # chuyến chốt trong tháng T
    for l in db.execute(sa.select(Lead)).scalars():
        l.booking_id = b.id; l.converted_at = b.created_at
    db.commit()

    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    a = next(x for x in r["by_channel_month"] if x["channel"] == KENH)
    assert a["revenue"] == 7_000_000, "khoá cũ đổi nghĩa — mọi bảng đang đọc nó sẽ lệch mà không báo"
    assert a["doanh_thu_booking_chot"] == 2_000_000
    d = r["detail"][0]
    assert d["revenue_tron_doi"] == 7_000_000 and d["doanh_thu_booking_chot"] == 2_000_000


# =============================================================================================
# 4. HAI tỷ lệ, HAI tên — quy tắc Chủ tịch ký phải có mặt và phải khác tỷ lệ chéo
# =============================================================================================

def test_ty_le_theo_quy_tac_da_ky_GOM_CA_phan_chot_o_ky_SAU(db):
    """Bốn lead kỳ tháng 3. Một chốt tour khởi hành tháng 4 (trong kỳ báo cáo), một chốt tour
    khởi hành tháng 6 (kỳ SAU). Hai lead còn lại không chốt.

        tỷ lệ chéo (khởi hành trong tháng 4) = 1/4 = 25%
        overview-v1 (chốt mọi lúc)           = 2/4 = 50%

    Hai con số này KHÁC NHAU, và đó chính là lý do chúng phải có hai cái tên. Trước bản sửa, báo
    cáo chỉ in 25% dưới cái tên "tỷ lệ chốt" — thấp hơn con số Chủ tịch đã ký, vì thiếu phần chốt
    muộn.
    """
    a1, a2 = "0955000001", "0955000002"
    l1 = _lead(db, a1); l2 = _lead(db, a2)
    _lead(db, "0955000003"); _lead(db, "0955000004")
    b1 = _booking(db, a1, date(2026, 4, 15), 1_000_000)
    b2 = _booking(db, a2, date(2026, 6, 15), 1_000_000)
    l1.booking_id, l1.converted_at = b1.id, b1.created_at
    l2.booking_id, l2.converted_at = b2.id, b2.created_at
    db.commit()

    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    a = next(x for x in r["by_channel_month"] if x["channel"] == KENH)
    assert a["so_sdt"] == 4
    assert a["converted"] == 1 and a["rate"] == 0.25
    assert a["chot_moi_luc"] == 2
    assert a["ty_le_chot_overview"] == 0.5, (
        "tử số đang bỏ phần chốt ở kỳ sau — đây KHÔNG phải quy tắc overview-v1")
    assert r["quy_tac_ty_le_chot"] == "overview-v1"
    assert r["tinh_den_ngay"] is not None, "con số này còn tăng, nên phải kèm mốc tính đến ngày"


def test_bao_cao_noi_ra_ten_thuoc_da_dung(db):
    _lead(db, "0966000001"); db.commit()
    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    assert r["quy_tac_ty_le_chot"] == L.QUY_TAC_TY_LE_CHOT
    assert L.QUY_TAC_TY_LE_CHOT == "overview-v1"


def test_chua_doi_chieu_thi_ty_le_da_ky_la_KHONG_XAC_DINH_va_bao_cao_TU_KEU(db):
    """Chưa ai chạy `match_conversions()` thì không lead nào có `booking_id`.

    Lúc ấy 0% là một câu KHẲNG ĐỊNH SAI: nó đọc là "chạy mà không ra khách", trong khi sự thật là
    "chưa ai so sổ". Phải trả None, và báo cáo phải tự nói ra điều đó.
    """
    for i in range(3):
        _lead(db, f"097700000{i}")
    _booking(db, "0977000000", date(2026, 4, 10), 1_000_000)   # có booking, nhưng CHƯA đối chiếu
    db.commit()

    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    a = next(x for x in r["by_channel_month"] if x["channel"] == KENH)
    assert a["ty_le_chot_overview"] is None
    assert r["da_doi_chieu"] is False
    assert r["canh_bao"] and "CHƯA XÁC ĐỊNH" in r["canh_bao"][0]


def test_tong_thang_va_tong_ky_deu_mang_du_ba_con_so(db):
    """Dòng tổng cũng phải có đủ ba con số. Tổng chỉ có `rate` là chỗ người đọc quay về hiểu nhầm."""
    a1 = "0988000001"
    l1 = _lead(db, a1); _lead(db, "0988000002")
    b1 = _booking(db, a1, date(2026, 7, 1), 1_000_000)      # chốt ở kỳ SAU
    l1.booking_id, l1.converted_at = b1.id, b1.created_at
    db.commit()

    r = L.conversion_report(db, THANG_BAO_CAO, lead_months=[KY])
    mm = next(x for x in r["by_month"] if x["lead_month"] == KY)
    assert mm["so_sdt"] == 2 and mm["chot_moi_luc"] == 1
    assert mm["ty_le_chot_overview"] == 0.5
    assert mm["converted"] == 0 and mm["rate"] == 0.0, "không ai khởi hành trong tháng báo cáo"


def test_dong_TONG_cua_ky_bao_cao_cung_dem_NGUOI_chu_khong_cong_don_tung_kenh(db):
    """Cùng lỗi với by_month, nhưng ở dòng TỔNG — và dòng tổng là dòng người ta đọc đầu tiên.

    Lead phát sinh ngay trong kỳ báo cáo, một người qua hai kênh. Tổng phải là MỘT số điện thoại.
    Đo được 18/9/2026: bỏ phép đếm lại trên tập hợp ở dòng tổng thì KHÔNG phép thử nào kêu — nên
    câu này ra đời để bịt đúng chỗ ấy.
    """
    sdt = "0912340001"
    _lead(db, sdt, ky=THANG_BAO_CAO, kenh="Hotline 1")
    _lead(db, sdt, ky=THANG_BAO_CAO, kenh="Zalo OA")
    b = _booking(db, sdt, date(2026, 4, 20), 1_000_000)
    for l in db.execute(sa.select(Lead)).scalars():
        l.booking_id = b.id; l.converted_at = b.created_at
    db.commit()

    t = L.conversion_report(db, THANG_BAO_CAO, lead_months=[THANG_BAO_CAO])["total_current"]
    assert t["so_sdt"] == 1, "dòng tổng đang cộng số người của từng kênh — một người thành hai"
    assert t["chot_moi_luc"] == 1
    assert t["ty_le_chot_overview"] == 1.0


# =============================================================================================
# ĐỘT BIẾN TƯƠNG ĐƯƠNG — đo được, ghi lại thay vì giấu
# =============================================================================================
# Thử 13 phép đột biến trên `conversion_report`; 12 bị bắt. Con thứ 13 THOÁT:
#
#     đổi  a["ty_le_tren_sdt_dem_duoc"] = converted / a["so_sdt"]
#     thành a["ty_le_tren_sdt_dem_duoc"] = converted / a["so_dong"]
#
# Đo lại thì ở MỨC KÊNH đây là đột biến TƯƠNG ĐƯƠNG, không phải lỗ hổng của bộ phép thử: ràng buộc
# `uq_lead_phone_month_channel` đang bảo đảm mỗi (SĐT, kỳ, kênh) chỉ có MỘT dòng, nên trong một
# kênh thì `so_dong` LUÔN bằng `so_sdt`. Hai cách viết cho cùng kết quả.
#
# TƯƠNG ĐƯƠNG ẤY ĐỨNG ĐƯỢC NHỜ CHÍNH RÀNG BUỘC SẼ BỊ GỠ. Bản nâng cấp của gói Marketing gỡ nó để
# khách gọi lại lần hai trong tháng lưu được thành dòng thứ hai — và ngày ấy `so_dong` sẽ khác
# `so_sdt`, đột biến này hết tương đương ngay, rồi lặng lẽ chia tử số cho số DÒNG.
#
# Hai câu dưới đây ghim đúng chỗ ấy:
#   · test_RANG_BUOC_DUY_NHAT_dang_chan_lan_lien_he_thu_hai_cung_ky_cung_kenh — hàng rào còn sống
#   · test_MOT_NGUOI_hai_kenh_trong_mot_thang_van_la_MOT_so_dien_thoai — mức THÁNG đã bắt được
#     đúng phép đột biến ấy, vì ở mức tháng `so_dong` và `so_sdt` khác nhau được ngay hôm nay.
#
# Khi hàng rào được gỡ: câu ràng buộc ở trên sẽ ĐỎ. Người gỡ phải quay lại đây, đổi câu ấy thành
# "hai lần liên hệ lưu được thành hai dòng", và thêm một câu mức KÊNH cho tỷ lệ cùng đơn vị.

def test_MOT_NGUOI_goi_HAI_LAN_cung_kenh_la_HAI_DONG_nhung_MOT_nguoi(db):
    """Đây là phép thử THAY CHỖ câu ghim đột biến M10, và nó ra đời đúng ngày câu ghim ấy đỏ.

    LỊCH SỬ NGẮN, ghi ra để lần sau ai đọc còn hiểu vì sao có câu này:
    Ngày 18/9/2026 em chạy đột biến trên tệp này. Đột biến M10 — đổi `so_sdt` thành `so_dong` ở
    mức kênh — KHÔNG bị bắt. Lúc ấy nó là đột biến TƯƠNG ĐƯƠNG thật: ràng buộc duy nhất
    (phone, lead_month, channel) ép mỗi khách chỉ có một dòng mỗi kênh, nên hai con số luôn bằng
    nhau và không phép thử nào phân biệt được. Em đã ghim điều kiện ấy lại bằng một câu đọc thẳng
    khai báo bảng, để ngày nào ràng buộc biến mất thì nó đỏ lên mà nhắc.

    Hôm nay ràng buộc đã biến mất. M10 KHÔNG còn tương đương — và đây là câu giết nó.
    """
    sdt = "0933111222"
    _lead(db, sdt)                                    # lần liên hệ thứ nhất
    _lead(db, sdt)                                    # lần thứ hai, CÙNG kênh cùng kỳ
    _lead(db, "0933111333")                           # một người khác
    db.commit()

    r = L.conversion_report(db, THANG_BAO_CAO)
    dong = [a for a in r["by_channel_month"] if a["channel"] == KENH and a["lead_month"] == KY]
    assert len(dong) == 1
    a = dong[0]
    assert a["so_dong"] == 3, f"Ba lần liên hệ là ba DÒNG; đang đếm {a['so_dong']}"
    assert a["so_sdt"] == 2, (
        f"Ba dòng ấy chỉ của HAI số điện thoại; đang đếm {a['so_sdt']}. Đếm dòng thay vì đếm "
        f"người là làm mẫu số phồng lên, và tỷ lệ chốt tụt xuống mà không ai biết vì sao.")

