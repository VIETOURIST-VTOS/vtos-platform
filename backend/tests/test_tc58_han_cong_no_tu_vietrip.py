# -*- coding: utf-8 -*-
"""TC-58 · BẢY Ô HẠN CÓ SỐ KHI SỔ NGHĨA VỤ ĐƯỢC NẠP TỪ VIETRIP.

    "em đọc hướng dẫn này vào vietrip cập nhật nợ phải thu - phải trả"
                                                          — anh Tuấn, 17/9/2026

Bản hướng dẫn anh Tuấn tự viết chỉ ra hai nguồn: phải THU nằm ở danh sách phiếu đặt (Tổng − Đã thu),
phải TRẢ nằm ở quyết toán từng tour và hàng đợi duyệt chi. Đi soát thì cả hai ĐÃ về VTOS đủ — 12.198
phiếu đặt trong `bookings`, 4.815 chứng từ chi trong `payment_requests` — và hàm dựng sổ nghĩa vụ từ
hai bảng ấy cũng đã có sẵn.

Thứ thiếu là ba cái, và vòng này làm cả ba:

  1. MỘT CỬA để bấm dựng sổ. Không có cửa thì hàm ấy không bao giờ chạy, và hai khối đọc một cuốn sổ
     rỗng. Đúng ranh giới 09/9: "không có cửa thì đó là việc còn thiếu".
  2. CƠ SỞ NGÀY "han" = cam kết nếu có, không thì dự kiến. Vietrip không có ô ngày cam kết, nên cộng
     riêng theo cam kết là bảy ô trống vĩnh viễn.
  3. MỐC CHO PHÍA CHI: ngày kết thúc tour, theo chốt của anh Tuấn — "sau khi tour về gọi là quá hạn".

══════════════════════════════════════════════════════════════════════════════════════════════
NĂM CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. MỐC SUY RA LEO VÀO CỘT CAM KẾT. Ghi ngày kết thúc tour vào `ngay_cam_ket` thì bảy ô có số ngay,
   trông y hệt kết quả đúng — nhưng câu "quá hạn theo cam kết" của hai tab dòng tiền chết lặng lẽ,
   và không phép cộng nào phát hiện được.
2. NGÀY THẬT BỊ MỐC SUY RA ĐÈ. Kế toán gõ ngày đến hạn rồi mà robot vẫn ghi đè bằng ngày kết thúc
   tour thì công gõ ấy mất, mỗi lần đồng bộ một lần mất.
3. Ô "CHƯA CÓ HẠN" PHỒNG LÊN. Định nghĩa cũ là "rỗng cột cam kết", nên khoản có ngày dự kiến vẫn bị
   đếm vào đó — ô ấy to lên, bảy ô kia hụt đúng phần chênh, mà tổng tám ô vẫn khớp tổng công nợ.
4. Ô "QUÁ HẠN" PHÍA THU KHÔNG BAO GIỜ CÓ SỐ. Phép kéo `max(hôm_nay, …)` của bản cũ đẩy mọi khoản
   quá khứ về hôm nay, nên khách đi tour từ tháng 6 chưa trả vẫn nằm ở ô "1 tuần".
5. HAI TAB DÒNG TIỀN BỊ KÉO THEO. Cơ sở "han" chỉ dành cho hai khối công nợ; lẫn sang tab cam kết là
   đúng chỗ hỏng số 1 nhưng ở một tệp khác.
"""
import datetime as dt
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Tour
from app.models.nghia_vu import NghiaVuThanhToan
from app.models.ops import PaymentRequest
from app.services import han_cong_no as HCN
from app.services import nghia_vu as NV

GOC = Path(__file__).resolve().parents[2]
CUA = GOC / "backend" / "app" / "api" / "v1" / "dong_tien.py"
SO = GOC / "backend" / "app" / "services" / "nghia_vu.py"

HOM_NAY = dt.date(2026, 9, 17)


def _db():
    """Kho rỗng, dựng đúng những bảng khai được — xem chú thích cùng tên ở test_tc46."""
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _tour(db, code, tu, den, status="da_duyet"):
    db.execute(insert(Tour.__table__), [
        dict(code=code, name=code, tour_type="package", operator_id=1,
             start_date=tu, end_date=den, status=status)])
    db.commit()
    return db.query(Tour).filter(Tour.code == code).one()


def _booking(db, tour, code, tong, da_thu):
    db.execute(insert(Booking.__table__), [
        dict(code=code, tour_id=tour.id, request_id=0, sales_id=1, created_by=1,
             sla_minutes=0, sla_ok=True, customer_name="Khách " + code, customer_phone="0900000000",
             source="Vietrip", amount=tong, paid=da_thu, cancelled=False)])
    db.commit()


def _de_nghi_chi(db, tour, code, tien, ngay_den_han=None):
    db.execute(insert(PaymentRequest.__table__), [
        dict(code=code, category="chi_tour", supplier_name="NCC " + code, amount=tien,
             description="", created_by="vietrip", status="cho_duyet",
             tour_id=None if tour is None else tour.id, ngay_den_han=ngay_den_han)])
    db.commit()


def _ma(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    s = p.read_text(encoding="utf-8")
    return re.sub(r"#.*$", " ", s, flags=re.M)


# ═════════════════ 1 · MỐC SUY RA KHÔNG LEO VÀO CỘT CAM KẾT ═════════════════

def test_moc_suy_ra_cua_phai_tra_nam_o_cot_du_kien_chu_khong_phai_cam_ket():
    """Chỗ hỏng số 1.

    Anh Tuấn chốt 17/9: hạn phải trả là ngày tour về. Nhưng không ai KÝ ngày ấy với nhà cung cấp,
    nên nó là một mốc SUY RA. Hai cột ngày tách ra từ đầu chính là để có chỗ cho một mốc như thế
    mà không phải nói dối rằng có người đã ký.
    """
    db = _db()
    t = _tour(db, "VN001", dt.date(2026, 9, 1), dt.date(2026, 9, 5))
    _de_nghi_chi(db, t, "VTDC1", 100_000_000)
    NV.dong_bo(db, hom_nay=HOM_NAY)
    db.commit()

    nv = db.query(NghiaVuThanhToan).filter(NghiaVuThanhToan.nguon_ma == "VTDC1").one()
    assert nv.ngay_cam_ket is None, (
        "Ngày kết thúc tour là mốc SUY RA. Ghi nó vào cột cam kết thì bảy ô có số ngay và trông "
        "đúng, nhưng câu 'quá hạn theo cam kết' của hai tab dòng tiền chết lặng lẽ."
    )
    assert nv.ngay_du_kien_tra == dt.date(2026, 9, 5), (
        "Mốc suy ra phải bằng ngày KẾT THÚC tour — 'sau khi tour về gọi là quá hạn', chốt 17/9."
    )


def test_ke_toan_go_ngay_that_thi_ngay_go_thang_moc_suy_ra():
    """Chỗ hỏng số 2 — công gõ tay không được mất sau mỗi lần đồng bộ."""
    db = _db()
    t = _tour(db, "VN002", dt.date(2026, 9, 1), dt.date(2026, 9, 5))
    _de_nghi_chi(db, t, "VTDC2", 50_000_000, ngay_den_han=dt.date(2026, 10, 20))
    NV.dong_bo(db, hom_nay=HOM_NAY)
    db.commit()

    nv = db.query(NghiaVuThanhToan).filter(NghiaVuThanhToan.nguon_ma == "VTDC2").one()
    assert nv.ngay_cam_ket == dt.date(2026, 10, 20), "Ngày Kế toán gõ là ngày CÓ NGƯỜI KÝ."
    assert nv.ngay_du_kien_tra == dt.date(2026, 10, 20), (
        "Ngày gõ phải thắng mốc suy ra ở CẢ HAI cột, không thì mỗi lần đồng bộ là một lần mất công gõ."
    )


# ═════════════════ 2 · BẢY Ô CÓ SỐ, VÀ Ô "CHƯA CÓ HẠN" KHÔNG PHỒNG ═════════════════

def test_bay_o_han_co_so_that_thay_vi_rong_het():
    """Cả vòng này sinh ra để phép thử này chuyển từ đỏ sang xanh.

    Trước TC-58: sổ nạp từ Vietrip không có ngày cam kết nào, `cong()` cộng riêng cột cam kết, nên
    cả bảy ô trả 0 và toàn bộ tiền dồn vào ô "Chưa có hạn".
    """
    db = _db()
    t = _tour(db, "VN003", dt.date(2026, 9, 20), dt.date(2026, 9, 25))
    _de_nghi_chi(db, t, "VTDC3", 80_000_000)
    NV.dong_bo(db, hom_nay=HOM_NAY)
    db.commit()

    ra = HCN.theo_han(db, HCN.CHI, hom_nay=HOM_NAY)
    assert ra["vi_sao"] == "", "Sổ có khoản thì không được trả lý do 'sổ rỗng'."
    assert ra["nhom"]["2 tuần"] == 80_000_000, (
        "Tour về 25/9, hôm nay 17/9 — đúng 8 ngày, tức mép TRƯỚC của ô '2 tuần' (hôm nay +8). Rơi "
        f"sang ô khác là mép ô lệch một ngày. Bảy ô hiện đang là: {ra['nhom']}"
    )
    assert sum(v for v in ra["nhom"].values() if v) == 80_000_000, (
        "Tổng bảy ô phải bằng đúng tổng công nợ: bảy ô không trùng nhau, không hở."
    )
    assert ra["chua_co_han"] == 0, (
        "Khoản đã có mốc suy ra thì KHÔNG còn là 'chưa có hạn'. Đếm cả nó vào đó là làm ô ấy phồng "
        "lên và bảy ô kia hụt đúng phần chênh — mà tổng tám ô vẫn khớp, nên không ai phát hiện."
    )


def test_chua_co_han_chi_dem_khoan_rong_ca_hai_cot_ngay():
    """Chỗ hỏng số 3, canh thẳng vào định nghĩa."""
    db = _db()
    _de_nghi_chi(db, None, "VTDC4", 30_000_000)      # không tour, không ngày → thật sự chưa có hạn
    t = _tour(db, "VN005", dt.date(2026, 9, 20), dt.date(2026, 9, 25))
    _de_nghi_chi(db, t, "VTDC5", 70_000_000)         # có mốc suy ra
    NV.dong_bo(db, hom_nay=HOM_NAY)
    db.commit()

    ra = HCN.theo_han(db, HCN.CHI, hom_nay=HOM_NAY)
    assert ra["chua_co_han"] == 30_000_000, (
        "Chỉ khoản RỖNG CẢ HAI CỘT ngày mới là 'chưa có hạn'. Đây là khoản không gắn tour nào — "
        "đúng loại việc phải đi đòi người nhập."
    )
    assert sum(v for v in ra["nhom"].values() if v) == 70_000_000


# ═════════════════ 3 · Ô "QUÁ HẠN" PHÍA THU CÓ SỐ ═════════════════

def test_khach_da_di_tour_ma_chua_tra_du_thi_vao_o_qua_han():
    """Chỗ hỏng số 4 — đúng nhóm 1 trong bản hướng dẫn anh Tuấn gửi.

    Nguyên văn bản hướng dẫn: "1 — Quá hạn · Đã qua hoặc hôm nay · Gọi ngay, khách đi tour mà chưa
    trả đủ". Bản cũ kéo mọi ngày quá khứ về hôm nay nên ô này vĩnh viễn trống.
    """
    db = _db()
    t = _tour(db, "VN006", dt.date(2026, 6, 10), dt.date(2026, 6, 15))
    _booking(db, t, "VT900", 200_000_000, 120_000_000)
    NV.dong_bo(db, hom_nay=HOM_NAY)
    db.commit()

    ra = HCN.theo_han(db, HCN.THU, hom_nay=HOM_NAY)
    assert ra["nhom"]["Quá hạn"] == 80_000_000, (
        "Khách đi tour từ tháng 6 còn nợ 80 triệu thì đó là QUÁ HẠN, không phải 'sắp tới hạn'. "
        f"Bảy ô hiện đang là: {ra['nhom']}"
    )

    nv = db.query(NghiaVuThanhToan).filter(NghiaVuThanhToan.nguon_ma == "VT900").one()
    assert nv.trang_thai == "qua_han", (
        "Nhãn trạng thái phải nói cùng một điều với ô hạn. Nhãn 'Dự kiến' gõ cứng là thứ người đọc "
        "tin trước cả con số."
    )


def test_booking_sap_khoi_hanh_van_xep_theo_luat_D7_cua_vtos():
    """Anh Tuấn 17/9, phía thu: "em tính theo luật của VTOS" — tức D-7 trước khởi hành, luật có sẵn."""
    db = _db()
    t = _tour(db, "VN007", dt.date(2026, 9, 30), dt.date(2026, 10, 3))
    _booking(db, t, "VT901", 100_000_000, 0)
    NV.dong_bo(db, hom_nay=HOM_NAY)
    db.commit()

    nv = db.query(NghiaVuThanhToan).filter(NghiaVuThanhToan.nguon_ma == "VT901").one()
    assert nv.ngay_du_kien_tra == dt.date(2026, 9, 23), "D-7 trước ngày khởi hành 30/9."
    assert nv.ngay_cam_ket is None, "Không ai ký lịch thu với khách — cột cam kết vẫn rỗng."


# ═════════════════ 4 · HAI TAB DÒNG TIỀN KHÔNG BỊ KÉO THEO ═════════════════

def test_co_so_ngay_cam_ket_van_chi_doc_cot_cam_ket():
    """Chỗ hỏng số 5 — cơ sở 'han' là cơ sở THỨ BA, không phải nới lỏng cơ sở cũ."""
    db = _db()
    t = _tour(db, "VN008", dt.date(2026, 9, 20), dt.date(2026, 9, 25))
    _de_nghi_chi(db, t, "VTDC8", 90_000_000)
    NV.dong_bo(db, hom_nay=HOM_NAY)
    db.commit()

    theo_cam_ket = NV.cong(db, dt.date(2026, 1, 1), dt.date(2026, 12, 31), co_so_ngay="cam_ket")
    assert theo_cam_ket == {}, (
        "Khoản chỉ có mốc suy ra KHÔNG được xuất hiện ở tab Nghĩa vụ đến hạn: tab ấy trả lời câu "
        "'ai đã ký ngày nào', và một mốc suy ra chen vào đó là một câu trả lời sai."
    )
    theo_han = NV.cong(db, dt.date(2026, 1, 1), dt.date(2026, 12, 31), co_so_ngay="han")
    assert theo_han == {"tra_ncc": 90_000_000}


def test_han_cong_no_khai_co_so_ngay_mot_cho_va_dung_co_so_han():
    """Cơ sở ngày khai một chỗ, để đổi nó là một dòng chứ không phải đi tìm từng lời gọi."""
    assert HCN.CO_SO_NGAY == "han"
    ma = _ma(GOC / "backend" / "app" / "services" / "han_cong_no.py")
    assert 'co_so_ngay="cam_ket"' not in ma, (
        "Còn một lời gọi nào cộng theo cam kết là bảy ô lại hụt đúng phần Vietrip nạp về."
    )


# ═════════════════ 5 · CỬA DỰNG SỔ CÓ THẬT ═════════════════

def test_co_mot_cua_de_bam_dung_lai_so_nghia_vu():
    """Ranh giới 09/9/2026: không có cửa thì đó là việc còn thiếu, không phải việc để Claude nhập hộ.

    Hàm `dong_bo` đã nằm trong mã từ VPM-11 nhưng KHÔNG cửa nào gọi nó, nên sổ chưa bao giờ được
    dựng và hai khối công nợ đọc một cuốn sổ rỗng suốt bốn ngày.
    """
    ma = _ma(CUA)
    assert "/nghia-vu/dong-bo" in ma, "Thiếu cửa dựng sổ nghĩa vụ."
    assert "NV.dong_bo(db)" in ma, "Cửa phải gọi đúng hàm dựng sổ, không viết lại phép dựng thứ hai."
    assert "require_roles" in ma


def test_dong_bo_chay_lai_duoc_khong_nhan_doi_so():
    """Bấm cửa hai lần không được ra hai sổ. Khoá (nguồn bảng, nguồn id) là thứ giữ điều đó."""
    db = _db()
    t = _tour(db, "VN009", dt.date(2026, 9, 20), dt.date(2026, 9, 25))
    _de_nghi_chi(db, t, "VTDC9", 40_000_000)
    _booking(db, t, "VT902", 60_000_000, 10_000_000)
    lan_1 = NV.dong_bo(db, hom_nay=HOM_NAY); db.commit()
    lan_2 = NV.dong_bo(db, hom_nay=HOM_NAY); db.commit()
    assert lan_1["tong_dong"] == lan_2["tong_dong"] == 2
