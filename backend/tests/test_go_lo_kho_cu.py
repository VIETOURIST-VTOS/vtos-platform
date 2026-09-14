# -*- coding: utf-8 -*-
"""GỠ CẢ LÔ kho quyết toán cũ – đường đi ngược của hai cửa nạp.

VÌ SAO CÓ NÚT NÀY

Chủ tịch giao nạp thử tháng 1 trước. Nhưng nạp thử mà không gỡ lại được thì không phải "thử" – nó
là một chiều, và người ta hoặc không dám bấm, hoặc bấm rồi phải dọn tay mấy trăm dòng.

CÁI KHÓ THẬT: rà mô hình 13/9/2026 thấy **36 bảng có cột khoá ngoại trỏ về `tours.id`**. Xoá chuyến
bằng cách liệt kê tay là chắc chắn sót, và sót thì hoặc nổ, hoặc tệ hơn: để lại dòng mồ côi trỏ vào
chuyến không tồn tại – im lặng, rồi tháng sau một báo cáo nào đó cộng phải nó.

  GL1  danh sách bảng con HỎI MÔ HÌNH, không liệt kê tay – bảng thứ 37 tự có mặt
  GL2  mặc định KHÔNG gỡ gì; phải bấm xác nhận
  GL3  gỡ đúng dòng mang nhãn nguồn, KHÔNG đụng dòng của nguồn khác
  GL4  chuyến còn việc của người khác thì GIỮ LẠI và nói ra
  GL5  chuyến không do lô này tạo thì KHÔNG bao giờ đụng tới
  GL6  xem trước nói đúng con số mà nút gỡ sẽ làm
  GL7  gỡ xong nạp lại được, và ra đúng như lần đầu
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_golo.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_golo.db", "test_golo.db-journal"):
    if os.path.exists(f):
        os.remove(f)

from datetime import date                                            # noqa: E402

import pytest                                                        # noqa: E402

from app.core.security import hash_password                          # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.models.core import Tour, User                                # noqa: E402
from app.models.vietrip import TourCostLine                           # noqa: E402
from app.services import go_lo_kho_cu as GO                           # noqa: E402
from app.services import intake_tao_chuyen as TCN                     # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(TourCostLine).delete()
    s.query(Tour).delete()
    s.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).delete()
    s.add(User(username=TCN.TAI_KHOAN_MAC_DINH, full_name="Điều hành Vietrip", role="nv_kd",
               password_hash=hash_password("x"), active=False))
    s.commit()
    yield s
    s.close()


def _lo():
    return [
        {"ten_tep": "QT NHA TRANG 05.01.26.xlsx", "ma_tour": "NT001.03050126",
         "ngay_di": date(2026, 1, 5), "ngay_ve": None, "ten_tour": "NHA TRANG",
         "ten_doan": "", "so_khach": 30, "ngoai_te": []},
        {"ten_tep": "QT ĐÀ LẠT 08.01.26.xlsx", "ma_tour": "DL001.03080126",
         "ngay_di": date(2026, 1, 8), "ngay_ve": None, "ten_tour": "ĐÀ LẠT",
         "ten_doan": "", "so_khach": 40, "ngoai_te": []},
    ]


def _nap(db):
    r = TCN.nap_lo(db, _lo(), boi="thu")
    db.commit()
    return r


def test_gl1_danh_sach_bang_con_hoi_MO_HINH_khong_liet_ke_tay():
    """Chỗ quan trọng nhất. Danh sách viết tay hôm nay đúng 36 bảng; tháng sau có bảng thứ 37 thì
    danh sách ấy sai MỘT CÁCH IM LẶNG, và không phép thử nào biết."""
    ds = GO._bang_treo_vao_chuyen()
    ten = {b.name for b, _ in ds}
    assert len(ds) >= 30, f"chỉ dò ra {len(ds)} bảng – gần như chắc chắn đang dò nhầm chỗ"
    for phai_co in ("tour_cost_lines", "bookings", "booking_khach", "tour_hdv_chi"):
        assert phai_co in ten, f"không thấy bảng {phai_co} – bộ dò đang bỏ sót"
    assert "tours" not in ten, "chính bảng tours không phải bảng con của nó"

    # Bảng mới thêm vào mô hình phải TỰ có mặt, không phải sửa danh sách nào.
    from sqlalchemy import Column, ForeignKey, Integer, Table
    t = Table("bang_thu_treo_vao_tour_gl1", Base.metadata,
              Column("id", Integer, primary_key=True),
              Column("tour_id", Integer, ForeignKey("tours.id")), extend_existing=True)
    try:
        assert "bang_thu_treo_vao_tour_gl1" in {b.name for b, _ in GO._bang_treo_vao_chuyen()}, \
            "thêm bảng mới treo vào tours mà bộ dò không thấy – nó đang là danh sách chết"
    finally:
        Base.metadata.remove(t)


def test_gl2_mac_dinh_khong_go_gi_phai_bam_xac_nhan(db):
    """Đây là nút duy nhất trong hệ xoá một lượt mấy trăm dòng và mấy trăm chuyến."""
    _nap(db)
    n = db.query(Tour).count()
    r = GO.go(db, boi="thu")
    db.commit()
    assert r["da_xoa_chuyen"] == 0 and db.query(Tour).count() == n
    assert "CHƯA GỠ GÌ" in r["message"]


def test_gl3_go_dung_dong_mang_nhan_nguon_khong_dung_nguon_khac(db):
    _nap(db)
    ts = db.query(Tour).order_by(Tour.id).all()
    db.add(TourCostLine(tour_id=ts[0].id, line_no=1, description="dòng của lô", source=GO.NGUON))
    db.add(TourCostLine(tour_id=ts[0].id, line_no=2, description="Kế toán gõ tay", source="nguoi_nhap"))
    db.add(TourCostLine(tour_id=ts[1].id, line_no=1, description="dòng Vietrip", source="vietrip"))
    db.commit()

    GO.go(db, boi="thu", xac_nhan=True); db.commit()
    con = {(c.description, c.source) for c in db.query(TourCostLine)}
    assert ("Kế toán gõ tay", "nguoi_nhap") in con, "gỡ lô đã xoá mất dòng người nhập tay"
    assert ("dòng Vietrip", "vietrip") in con, "gỡ lô đã xoá mất dòng của Vietrip"
    assert not any(s == GO.NGUON for _, s in con), "dòng của chính lô vẫn còn"


def test_gl4_chuyen_con_viec_cua_nguoi_khac_thi_GIU_LAI_va_noi_ra(db):
    """Gỡ lô là gỡ đúng phần lô ấy mang vào, không phải "xoá sạch chuyến". Ai đã gắn việc lên chuyến
    sau khi nạp thì việc của họ phải còn nguyên."""
    _nap(db)
    ts = db.query(Tour).order_by(Tour.id).all()
    db.add(TourCostLine(tour_id=ts[0].id, line_no=9, description="việc người khác", source="nguoi_nhap"))
    db.commit()

    x = GO.xem(db)
    assert len(x["giu_lai"]) == 1 and x["giu_lai"][0]["ma"] == ts[0].code
    assert x["giu_lai"][0]["con_treo"].get("tour_cost_lines") == 1, "phải nói RA cái gì đang treo"

    r = GO.go(db, boi="thu", xac_nhan=True); db.commit()
    assert r["da_xoa_chuyen"] == 1, "phải xoá chuyến trống và chỉ chuyến trống"
    con = {t.code for t in db.query(Tour)}
    assert con == {ts[0].code}, f"chuyến còn việc của người khác không được giữ lại: {con}"


def test_gl5_chuyen_khong_do_lo_nay_tao_thi_KHONG_bao_gio_dung_toi(db):
    """Dấu nhận chuyến của lô là hai ô confirmed_by / approved_by mang nhãn nguồn. Chuyến của
    Vietrip hay chuyến người tạo tay không mang dấu ấy, và không được đụng tới dù đang trống."""
    nguoi = db.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).one()
    db.add(Tour(code="VT-KHONG-PHAI-CUA-LO", name="Chuyến của Vietrip", tour_type="le_noi_dia",
                start_date=date(2026, 1, 1), end_date=date(2026, 1, 2), operator_id=nguoi.id,
                status="ket_thuc", confirmed_by="vietrip", approved_by="vietrip"))
    db.commit()
    _nap(db)

    GO.go(db, boi="thu", xac_nhan=True); db.commit()
    assert db.query(Tour).filter(Tour.code == "VT-KHONG-PHAI-CUA-LO").count() == 1, \
        "gỡ lô đã xoá một chuyến KHÔNG do lô này tạo ra"


def test_gl6_xem_truoc_noi_dung_con_so_ma_nut_go_se_lam(db):
    _nap(db)
    ts = db.query(Tour).order_by(Tour.id).all()
    db.add(TourCostLine(tour_id=ts[0].id, line_no=1, description="d", source=GO.NGUON))
    db.add(TourCostLine(tour_id=ts[1].id, line_no=1, description="k", source="nguoi_nhap"))
    db.commit()

    x = GO.xem(db)
    r = GO.go(db, boi="thu", xac_nhan=True); db.commit()
    assert x["tong_dong"] == r["da_go_dong"], \
        f"xem trước hứa gỡ {x['tong_dong']} dòng nhưng gỡ {r['da_go_dong']}"
    assert len(x["xoa_duoc"]) == r["da_xoa_chuyen"], \
        f"xem trước hứa xoá {len(x['xoa_duoc'])} chuyến nhưng xoá {r['da_xoa_chuyen']}"


def test_gl7_go_xong_nap_lai_duoc_va_ra_dung_nhu_lan_dau(db):
    """Gỡ rồi nạp lại phải ra đúng kết quả cũ – nếu không thì "nạp thử" chỉ thử được một lần."""
    r1 = _nap(db)
    ma1 = sorted(t.code for t in db.query(Tour))
    GO.go(db, boi="thu", xac_nhan=True); db.commit()
    assert db.query(Tour).count() == 0

    r2 = _nap(db)
    ma2 = sorted(t.code for t in db.query(Tour))
    assert r2["da_tao"] == r1["da_tao"] and ma2 == ma1, \
        f"nạp lại sau khi gỡ ra kết quả khác: {ma1} -> {ma2}"


def test_gl8_hai_cua_api_khai_quyen_o_CHU_KY_va_hep_dung_bang_cua_tao():
    """Quyền khai ở chữ ký hàm (chỉ đạo P1 08/9) để bộ kiểm đọc được mà không phải phân tích mã.

    Và phải HẸP ĐÚNG BẰNG cửa tạo chuyến: hẹp hơn thì có người tạo được mà không gỡ được, mà một
    nút tạo không có nút gỡ tương ứng là nút không ai dám bấm.
    """
    from app.api.v1.quyet_toan_lop3 import GO_LO, go_lo_kho_cu, xem_go_lo_kho_cu
    from app.services.intake import VAI_TRO

    assert set(GO_LO) == set(VAI_TRO["tao_chuyen_kho_cu"]), (
        f"quyền GỠ {sorted(GO_LO)} khác quyền TẠO {sorted(VAI_TRO['tao_chuyen_kho_cu'])}")
    assert "nv_dh" not in GO_LO and "ketoan" not in GO_LO

    import inspect
    for ham in (xem_go_lo_kho_cu, go_lo_kho_cu):
        dep = [p.default for p in inspect.signature(ham).parameters.values()
               if getattr(p.default, "dependency", None) is not None]
        vai = [getattr(d.dependency, "vai_tro_yeu_cau", None) for d in dep]
        assert any(v and set(v) == set(GO_LO) for v in vai), \
            f"{ham.__name__} không khai vai trò ở chữ ký – bộ kiểm quyền sẽ không thấy nó"


def test_gl9_cua_go_mac_dinh_KHONG_xac_nhan(db):
    """Thân API nhận `xac_nhan` mặc định False. Gọi nhầm – hoặc gọi bằng thân rỗng – KHÔNG xoá gì."""
    from app.api.v1.quyet_toan_lop3 import GoLoVao
    assert GoLoVao().xac_nhan is False, \
        "thân yêu cầu mặc định xác_nhận=True thì một lời gọi rỗng cũng xoá sạch lô"


def test_gl10_go_lo_go_luon_PHIEU_DAT_do_lo_dung_ra(db):
    """13/9/2026 – lô nay còn dựng PHIẾU ĐẶT theo người bán, và gỡ phải gỡ luôn phần ấy.

    Sót một phiếu là để lại doanh thu ma trong bảng doanh số cá nhân, bảng hoa hồng và chỉ tiêu của
    một người thật — trong khi chuyến mang nó đã biến mất. Không bảng nào kêu, vì tổng nào cũng cộng
    từ dòng; người ta chỉ phát hiện khi có ai đó thắc mắc về tiền thưởng của mình.

    Và phiếu của NGUỒN KHÁC trên cùng chuyến thì phải còn nguyên, y như mọi dòng khác.
    """
    from app.models.core import Booking
    from app.services import phieu_dat_kho_cu as PD
    from app.services import khop_nguoi_ban as KN

    _nap(db)
    t = db.query(Tour).filter(Tour.code == "NT001.03050126").one()
    sale = User(username="kd.thu.gl10", full_name="Ninh Nữ Lệ Giang", role="nv_kd",
                department="kd_le", password_hash=hash_password("x"), active=True)
    db.add(sale)
    db.commit()

    khach = [{"ho_ten": "KHÁCH A", "sale": "NINH NỮ LỆ GIANG", "gia_ban": 5_000_000,
              "tong_thu": 5_000_000, "ma_dat_cho": ""}]
    KN.ghi_so(db, PD.dem_nguoi_ban([{"khach": khach}]))
    PD.sinh(db, t.id, khach, boi="thu")
    # Phiếu của nguồn khác trên CÙNG chuyến – việc của người khác, phải sống sót.
    db.add(Booking(code="BK-NGUON-KHAC", tour_id=t.id, request_id=0, sales_id=sale.id,
                   created_by=sale.id, customer_name="Khách của Vietrip", customer_phone="09",
                   source="vietrip", pax=1, amount=1_000_000))
    db.commit()

    xem = GO.xem(db)
    assert xem["dong_quyet_toan"].get("phiếu đặt") == 1, \
        "bản xem trước không đếm phiếu đặt – người bấm không biết mình sắp gỡ cả doanh số"

    GO.go(db, boi="thu", xac_nhan=True)
    db.commit()
    con = db.query(Booking).all()
    assert len(con) == 1 and con[0].source == "vietrip", \
        "gỡ lô để sót phiếu của lô, hoặc đã xoá nhầm phiếu của nguồn khác"
