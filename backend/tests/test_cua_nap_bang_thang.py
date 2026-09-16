# -*- coding: utf-8 -*-
"""CỬA NẠP BẢNG THÁNG DỊCH VỤ LẺ (vá 10b).

VÌ SAO KHỐI NÀY TỒN TẠI

Vá 10a dựng bộ ĐỌC và dừng ở đó: 49 tệp, 672 dòng khách, thu 10,29 tỷ — đọc được hết nhưng chưa một
đồng nào vào hệ. Vá 10b là cái cửa. Cửa ghi tiền thì mọi thứ nó ghi sai đều sai LẶNG: tổng vẫn cân,
bảng vẫn cân, chỉ là cân ở sai chỗ và sai tên người.

  BT-N1   cửa có mặt trong khung nạp, đủ ba hàm lô, và KHÔNG mở rộng quyền cho ai ngoài danh sách
  BT-N2   soát (`kiem_lo`) KHÔNG ghi một dòng nào — xem trước phải thật sự là xem trước
  BT-N3   tệp không nói tháng/năm thì BỎ, không đoán hộ
  BT-N4   ngoại tệ giữ SỐ GỐC, tỷ giá RỖNG, số VND RỖNG — không tự quy đổi
  BT-N5   tên người bán chưa gán được: vẫn có doanh thu, nhưng KHÔNG vào chỉ tiêu của ai
  BT-N6   tên đã gán được thì doanh thu về ĐÚNG người ấy và CÓ vào chỉ tiêu
  BT-N7   `gan_lai` với tới được phiếu của cửa này — nếu không, cột SALES vĩnh viễn không ai gán
  BT-N8   nạp lại thì THAY, không nhân đôi tiền
  BT-N9   sổ tháng là `non_package` mã DVL-…, KHÔNG phải một chuyến đi bịa ra
  BT-N10  cột có tiền mà không nhận ra thì NÊU RA, và KHÔNG cộng vào đâu cả
  BT-N11  tổng của bảng xem trước bằng đúng tổng thật sự ghi xuống — bảng không được nói dối
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_capbangthang.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_capbangthang.db", "test_capbangthang.db-journal"):
    if os.path.exists(f):
        os.remove(f)

from datetime import date                                            # noqa: E402

import pytest                                                        # noqa: E402

from app.core.security import hash_password                          # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.models.core import Booking, Tour, User                       # noqa: E402
from app.models.kho_cu import KhoCuNguoiBan                           # noqa: E402
from app.models.lop3_tour import BookingKhach                         # noqa: E402
from app.models.vietrip import TourCostLine                           # noqa: E402
from app.services import intake_bang_thang as BT                      # noqa: E402
from app.services import intake_tao_chuyen as TCN                     # noqa: E402
from app.services import khop_nguoi_ban as KN                         # noqa: E402
from app.services import phieu_dat_kho_cu as PD                       # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(BookingKhach).delete()
    s.query(TourCostLine).delete()
    s.query(Booking).delete()
    s.query(KhoCuNguoiBan).delete()
    s.query(Tour).delete()
    s.query(User).delete()
    # Tài khoản điều hành KHOÁ – chỗ đỗ của dòng chưa gán được người bán. `active=False`: nó giữ dữ
    # liệu, không phải một người đăng nhập được.
    s.add(User(username=TCN.TAI_KHOAN_MAC_DINH, full_name="Điều hành Vietrip", role="nv_dh",
               password_hash=hash_password("x"), active=False))
    s.add(User(username="uyennhi", full_name="Lê Thị Uyển Nhi", role="nv_kd", department="kd_le",
               password_hash=hash_password("x"), active=True))
    s.commit()
    yield s
    s.close()


def _uid(db, u):
    return db.query(User).filter(User.username == u).one().id


def _dong(ten, sale, thu, chi=None, ngoai_te=None, la=None):
    """Một dòng khách như bộ đọc vá 10a trả về."""
    return {"_hang": 7, "ten_khach": ten, "sale": sale, "doi_tac": "VP VFS", "dich_vu": "Visa",
            "thu": float(thu), "chi": float(sum(x["so_tien"] for x in (chi or []))),
            "khoan_chi": chi or [], "ngoai_te": ngoai_te or [],
            "tong_thu_trong_tep": None, "tong_chi_trong_tep": None,
            "o_khong_nhan_ra": la or [],
            "cho_ty_gia": bool(ngoai_te), "lai": None}


def _tep(ten_tep="QUYẾT TOÁN VISA LẺ THÁNG 03.2026.xlsx", dong=None, ky=(2026, 3),
         loai="VISA", la_cot=None):
    """Một tệp như `nap_bang_thang.doc_tep` trả về."""
    dong = dong if dong is not None else [
        _dong("NGUYỄN VĂN A", "UYỂN NHI", 6_790_000,
              chi=[{"khoan": "Phí LSQ", "so_tien": 2_000_000}]),
        _dong("TRẦN THỊ B", "MAI VIGO", 6_590_000,
              chi=[{"khoan": "Phí dịch thuật", "so_tien": 450_000}]),
    ]
    return {"ten_tep": ten_tep, "loai_dich_vu": loai, "ky": ky, "so_sheet": 1, "hang_tieu_de": 5,
            "dong": dong, "thieu": [], "cot_khong_nhan_ra": la_cot or [],
            "tong_thu": round(sum(x["thu"] for x in dong), 2),
            "tong_chi": round(sum(x["chi"] for x in dong), 2),
            "so_cho_ty_gia": sum(1 for x in dong if x["cho_ty_gia"]),
            "tong_trong_tep": None, "lai": None}


def _nap(db, rows, boi="thu"):
    KN.ghi_so(db, PD.dem_nguoi_ban([{"khach": BT._khach_cho_phieu(d)} for d in rows]))
    kq = BT.nap_lo(db, rows, boi=boi)
    db.commit()
    return kq


def _so(db):
    """Số đang có trong hệ, đọc TỪ CƠ SỞ DỮ LIỆU chứ không từ bản trả về của cửa."""
    t = db.query(Tour).filter(Tour.code.like(BT.TIEN_TO + "%")).all()
    ds = db.query(Booking).filter(Booking.tour_id.in_([x.id for x in t])).all() if t else []
    kh = db.query(BookingKhach).filter(
        BookingKhach.tour_id.in_([x.id for x in t])).all() if t else []
    cp = db.query(TourCostLine).filter(
        TourCostLine.tour_id.in_([x.id for x in t])).all() if t else []
    return {"tour": t, "phieu": ds, "khach": kh, "chi": cp,
            "thu": round(sum(float(b.amount or 0) for b in ds), 2)}


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N1 · cửa có mặt, và KHÔNG mở rộng quyền
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn1_cua_co_mat_trong_khung_nap_va_khong_noi_quyen():
    """Khai thiếu một hàm lô là cửa nạp hàng loạt gọi vào chỗ rỗng — và nó nổ ở giữa một lô đang ghi.

    Quyền chốt cứng ở đây: mở cho Kinh doanh là mở cho người có doanh số nằm trong chính lô này.
    """
    from app.services import intake as I

    assert "bang_thang_dich_vu_le" in I.BO_NAP, "cửa chưa được đăng ký vào khung nạp"
    b = I.BO_NAP["bang_thang_dich_vu_le"]
    assert b["lo"] is True
    for k in ("kiem_lo", "nap_lo", "doc_tep", "kiem", "nap"):
        assert callable(b[k]), f"thiếu hàm {k}"
    # Bảng phụ phải khai đủ: phép kiểm "mọi bảng phải có một cửa" đọc SỐNG từ chỗ này.
    assert set(b["bang_phu"]) == {"tours", "booking_khach", "tour_cost_lines"}
    assert I.VAI_TRO["bang_thang_dich_vu_le"] == ("chutich", "tgd", "cntt", "tp_dh", "ketoan")
    for xau in ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_dh"):
        assert xau not in I.VAI_TRO["bang_thang_dich_vu_le"], \
            f"{xau} không được nạp lô này — doanh số của chính họ nằm trong đây"


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N2 · xem trước phải thật sự là xem trước
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn2_soat_khong_ghi_mot_dong_nao(db):
    """Một cửa soát có ghi là một cửa mà người duyệt bấm 'xem' rồi mất quyền đổi ý."""
    truoc = _so(db)
    assert not truoc["tour"] and not truoc["phieu"]
    kq = BT.kiem_lo(db, [_tep()])
    db.commit()
    sau = _so(db)
    assert not sau["tour"], "soát mà đã dựng sổ tháng"
    assert not sau["phieu"] and not sau["khach"] and not sau["chi"]
    assert kq["da_nap"] == 1 and kq["dem"]["so_khach"] == 2
    assert "chưa ghi gì" in kq["ghi_chu"]


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N3 · không đoán kỳ
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn3_tep_khong_noi_thang_nam_thi_bo_chu_khong_doan(db):
    """Đoán sai kỳ một lần là cả một tháng tiền nằm nhầm năm tài chính — và KHÔNG có gì kêu lên,
    vì mọi tổng vẫn cân."""
    thieu_nam = _tep(ten_tep="QUYẾT TOÁN VISA LẺ THÁNG 03.xlsx", ky=(None, 3))
    khong_ky = _tep(ten_tep="QUYẾT TOÁN VISA LẺ.xlsx", ky=None)
    kq = _nap(db, [thieu_nam, khong_ky])
    assert kq["da_nap"] == 0, "không được nạp tệp thiếu kỳ"
    assert _so(db)["tour"] == []
    for h in kq["chi_tiet"]:
        assert h["viec"] == "bo_qua"
        assert "tháng/năm" in h["vi_sao"]


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N4 · ngoại tệ: giữ số gốc, KHÔNG quy đổi
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn4_ngoai_te_giu_so_goc_va_de_trong_so_vnd(db):
    """Chủ tịch chốt 16/9: không tự quy đổi. Số VND sẵn trong tệp không dùng được — không ai biết
    tỷ giá ấy của ngày nào, lấy ở đâu."""
    d = _tep(dong=[_dong("NGUYỄN VĂN A", "UYỂN NHI", 10_000_000,
                         chi=[{"khoan": "Phí hồ sơ", "so_tien": 1_000_000}],
                         ngoai_te=[{"khoan": "PHÍ VISA (AUD)", "tien_te": "AUD",
                                    "so_tien_goc": 436.2}])])
    kq = _nap(db, [d])
    assert kq["da_nap"] == 1

    ngoai = [c for c in _so(db)["chi"] if c.tien_te]
    assert len(ngoai) == 1, "khoản ngoại tệ phải thành MỘT dòng chi riêng"
    c = ngoai[0]
    assert c.tien_te == "AUD" and float(c.so_tien_goc) == pytest.approx(436.2)
    assert c.ty_gia is None, "cửa nạp KHÔNG được tự đặt tỷ giá"
    assert c.actual is None, "chưa có tỷ giá thì chưa có số VND — để RỖNG, không đặt 0 và không bịa"
    assert "CHỜ TỶ GIÁ" in (c.note or "")

    # Và chỗ thiếu ấy phải được NÓI RA, không im lặng.
    assert kq["tien"]["so_khoan_cho_ty_gia"] == 1
    assert float(kq["tien"]["tien_goc_cho_ty_gia"]) == pytest.approx(436.2)
    assert kq["tien"]["lai"] is None, "còn khoản chờ tỷ giá thì CHƯA có lãi"
    assert "chờ tỷ giá" in kq["message"].lower()


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N5 · tên chưa gán được: có doanh thu, KHÔNG có chỉ tiêu
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn5_nguoi_ban_chua_gan_thi_khong_vao_chi_tieu_cua_ai(db):
    """Chủ tịch chốt: gán bừa vào tài khoản là đụng vào thưởng của người thật.

    Doanh thu KHÔNG được bỏ (tiền công ty thu thật), nhưng cũng không được cộng cho ai.
    """
    _nap(db, [_tep()])
    s = _so(db)
    do = [b for b in s["phieu"] if not b.counts_for_target]
    assert len(do) == 1, "'MAI VIGO' không có tài khoản — phải có đúng một phiếu đỗ"
    b = do[0]
    assert b.sales_id == _uid(db, TCN.TAI_KHOAN_MAC_DINH), \
        "phiếu chưa gán phải đứng tên tài khoản hệ thống KHOÁ, không phải một nhân viên thật"
    assert float(b.amount) == 6_590_000, "doanh thu vẫn phải vào hệ"
    assert PD.ten_trong_phieu(b) == "MAI VIGO", \
        "tên gốc phải được giữ lại — không giữ thì gán xong không lần ra được của ai"

    # Không một nhân viên thật nào bị cộng nhầm.
    that = [x for x in s["phieu"] if x.sales_id == _uid(db, "uyennhi")]
    assert all(x.counts_for_target for x in that)
    assert sum(float(x.amount) for x in that) == 6_790_000, \
        "Uyển Nhi chỉ được cộng đúng phần mình bán"


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N6 · tên gán được thì về đúng người
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn6_ten_khop_duoc_thi_doanh_thu_ve_dung_nguoi(db):
    _nap(db, [_tep()])
    s = _so(db)
    cua_nhi = [b for b in s["phieu"] if b.sales_id == _uid(db, "uyennhi")]
    assert len(cua_nhi) == 1 and cua_nhi[0].counts_for_target is True
    # Dòng khách treo vào ĐÚNG phiếu của người đã bán ra khách ấy.
    kh = db.query(BookingKhach).filter(BookingKhach.booking_id == cua_nhi[0].id).all()
    assert [x.ho_ten for x in kh] == ["NGUYỄN VĂN A"]


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N7 · `gan_lai` phải với tới được phiếu của cửa này
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn7_gan_ten_xong_thi_gan_lai_cham_toi_phieu_cua_cua_nay(db):
    """ĐÂY LÀ PHÉP THỬ BẢO VỆ MỘT QUYẾT ĐỊNH THIẾT KẾ, không phải một nhánh mã.

    `phieu_dat_kho_cu.gan_lai` lọc phiếu theo `bookings.source`. Cửa này CỐ Ý đi qua `PD.sinh` chứ
    không tự dựng phiếu, nên phiếu của nó mang đúng cái nguồn mà `gan_lai` đi tìm. Tự dựng phiếu với
    một nguồn riêng cho "sạch lane" thì phiếu nằm ngoài tầm với của màn hình gán, và cột SALES của
    49 tệp vĩnh viễn không ai gán được — hỏng LẶNG, vì mọi tổng vẫn cân.

    Phép thử này chốt cả hai đầu của mối nối: nguồn ghi ra, và nguồn `gan_lai` đọc vào.
    """
    _nap(db, [_tep()])
    truoc = [b for b in _so(db)["phieu"] if not b.counts_for_target]
    assert len(truoc) == 1
    # ĐẦU GHI: phiếu phải mang đúng nguồn mà `gan_lai` lọc. Bản đầu của phép thử này chỉ kiểm hành
    # vi của `gan_lai`, nên khi bẻ mã đặt một nguồn riêng cho cửa nạp thì nó VẪN XANH — vì
    # `PD.sinh` lấy nguồn của chính nó chứ không lấy của cửa gọi. Hai dòng dưới đây là chỗ vá.
    assert {b.source for b in _so(db)["phieu"]} == {PD.NGUON}, \
        "phiếu của cửa này phải mang đúng nguồn của phiếu đặt kho cũ"
    assert BT.NGUON == PD.NGUON, \
        "cửa nạp và phiếu đặt phải cùng một nguồn — lệch là gan_lai không thấy phiếu nào"

    # Điều hành gán "MAI VIGO" về một tài khoản có thật.
    kho = db.query(KhoCuNguoiBan).filter(
        KhoCuNguoiBan.khoa_ten == KN.chuan("MAI VIGO")).one()
    KN.gan_tay(db, kho.khoa_ten, _uid(db, "uyennhi"), boi="tp_dh")
    db.commit()

    xem = PD.gan_lai(db, boi="tp_dh")
    assert len(xem["doi_duoc"]) == 1, "gán xong mà gan_lai không thấy phiếu của cửa này"
    assert xem["da_doi"] == 0, "mặc định phải là XEM TRƯỚC"

    PD.gan_lai(db, boi="tp_dh", xac_nhan=True)
    db.commit()
    sau = _so(db)
    assert all(b.counts_for_target for b in sau["phieu"]), "phiếu phải chuyển về đúng người"
    assert sum(float(b.amount) for b in sau["phieu"]
               if b.sales_id == _uid(db, "uyennhi")) == 13_380_000
    assert sau["thu"] == 13_380_000, "đổi chủ phiếu KHÔNG được làm thay đổi tổng doanh thu"


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N8 · nạp lại thì THAY
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn8_nap_lai_thi_thay_khong_nhan_doi_tien(db):
    """Nhân đôi ở đây không ai nhìn ra: sổ tháng vẫn cân, lãi lỗ vẫn cân, chỉ là gấp đôi."""
    _nap(db, [_tep()])
    m = _so(db)
    assert m["thu"] == 13_380_000 and len(m["khach"]) == 2 and len(m["chi"]) == 2

    _nap(db, [_tep()])
    h = _so(db)
    assert len(h["tour"]) == 1, "nạp lại không được dựng sổ tháng thứ hai"
    assert h["thu"] == 13_380_000, "nạp lại đã NHÂN ĐÔI doanh thu"
    assert len(h["khach"]) == 2 and len(h["chi"]) == 2
    assert len(h["phieu"]) == len(m["phieu"])


def test_btn8b_nap_lai_khi_tep_bot_khach_thi_khach_cu_phai_bien_mat(db):
    """Thay mà chỉ thay phần trùng là để lại rác của lần nạp trước, và rác ấy có mang tiền."""
    _nap(db, [_tep()])
    assert _so(db)["thu"] == 13_380_000
    it_hon = _tep(dong=[_dong("NGUYỄN VĂN A", "UYỂN NHI", 6_790_000,
                              chi=[{"khoan": "Phí LSQ", "so_tien": 2_000_000}])])
    _nap(db, [it_hon])
    s = _so(db)
    assert s["thu"] == 6_790_000 and len(s["khach"]) == 1 and len(s["chi"]) == 1


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N9 · sổ tháng, không phải chuyến đi bịa ra
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn9_so_thang_la_non_package_khong_phai_chuyen_di(db):
    """'VISA LẺ THÁNG 3' không phải một chuyến đi. Ghi nó như một chuyến đi là dựng chuyến ma —
    đúng cái mà cửa tạo chuyến đã cố ý từ chối làm."""
    _nap(db, [_tep()])
    t = _so(db)["tour"][0]
    assert t.tour_type == "non_package"
    assert t.code.startswith("DVL-VISA032026-"), \
        "mã sổ = tiền tố + loại + tháng/năm + đuôi của TÊN TỆP"
    assert t.code == BT.ma_chuyen(_tep()), "mã phải ổn định: cùng tệp ra cùng mã"
    assert _tep()["ten_tep"] in t.name, \
        "tên sổ phải mang tên tệp — mã có đuôi băm cho máy, người đọc thì đọc tên"
    assert t.start_date == date(2026, 3, 31) and t.end_date == date(2026, 3, 31), \
        "bảng tháng chốt cuối tháng — lấy ngày đầu là đặt doanh thu trước lúc nó phát sinh"
    assert t.hinh_thuc is None, "ô quyết định phép tính — để người khai, không suy ngầm"
    assert t.operator_id == _uid(db, TCN.TAI_KHOAN_MAC_DINH)


def test_btn9b_hai_loai_cung_thang_la_hai_so_rieng(db):
    """Visa và Land cùng tháng 3 là hai sổ khác nhau. Gộp lại là trộn hai loại dịch vụ vào một
    khoản lãi, và không ai tách ra lại được."""
    _nap(db, [_tep(), _tep(ten_tep="QUYẾT TOÁN LAND THÁNG 03.2026.xlsx", loai="LAND")])
    ma = sorted(t.code for t in _so(db)["tour"])
    assert len(ma) == 2 and ma[0].startswith("DVL-LAND032026-") and ma[1].startswith("DVL-VISA032026-")


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N10 · cột lạ phải được nêu ra
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn10_cot_co_tien_ma_khong_nhan_ra_thi_neu_ra_va_khong_cong_vao_dau(db):
    """Cộng bừa một cột không rõ THU hay CHI là sai số theo hướng không ai đoán được. Bỏ im lặng
    thì còn tệ hơn: không ai biết là có chỗ bỏ."""
    d = _tep(la_cot=["HÓA ĐƠN", "Người dịch"])
    kq = _nap(db, [d])
    assert kq["cot_khong_nhan_ra"] == ["HÓA ĐƠN", "Người dịch"]
    assert "HÓA ĐƠN" in kq["ghi_chu"] and "Người dịch" in kq["ghi_chu"]
    # Và chúng KHÔNG được lẻn vào tiền.
    assert kq["tien"]["thu"] == 13_380_000 and kq["tien"]["chi"] == 2_450_000


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N11 · bảng xem trước không được nói dối
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn11_so_o_bang_xem_truoc_bang_dung_so_ghi_xuong(db):
    """Bảng xem trước nói 'sẽ nạp 13.380.000' rồi ghi xuống số khác là một bảng không ai tin được
    nữa — và người duyệt mất chỗ duy nhất họ có để kiểm trước khi bấm."""
    rows = [_tep(), _tep(ten_tep="QUYẾT TOÁN LAND THÁNG 04.2026.xlsx", loai="LAND", ky=(2026, 4))]
    xem = BT.kiem_lo(db, rows)
    db.commit()
    kq = _nap(db, rows)
    s = _so(db)
    assert xem["tien"]["thu"] == kq["tien"]["thu"] == s["thu"]
    assert xem["dem"]["so_khach"] == len(s["khach"])
    assert xem["da_nap"] == kq["da_nap"] == len(s["tour"]) == 2


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N12 · dòng không có TÊN KHÁCH mà có TIỀN thì vẫn phải vào
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn12_dong_khong_ten_khach_ma_co_tien_thi_van_giu(db):
    """Bỏ dòng ấy là mất doanh thu công ty thu thật, và mất LẶNG — tổng nào cũng cân vì tổng nào
    cũng cộng từ những dòng còn lại.

    Phép thử này thêm sau khi bẻ mã: đổi `not ten and thu <= 0` thành `not ten or thu <= 0` mà bộ
    phép thử VẪN XANH, vì mọi dòng trong bài thử đều có tên khách. Một luật không có bài thử nào
    chạm tới thì nó chỉ là một câu ghi chú.
    """
    d = _tep(dong=[
        _dong("NGUYỄN VĂN A", "UYỂN NHI", 6_790_000,
              chi=[{"khoan": "Phí LSQ", "so_tien": 2_000_000}]),
        _dong("", "UYỂN NHI", 5_000_000),          # tệp quên ghi tên khách, nhưng CÓ tiền
        _dong("", "UYỂN NHI", 0),                  # dòng trắng thật – cái này mới được bỏ
    ])
    kq = _nap(db, [d])
    s = _so(db)
    assert kq["dem"]["so_khach"] == 2, "dòng trắng bỏ, dòng có tiền giữ"
    assert s["thu"] == 11_790_000, "mất dòng không tên là mất 5.000.000 đ có thật"
    assert sorted(x.ho_ten for x in s["khach"]) == ["(tệp không ghi tên khách)", "NGUYỄN VĂN A"], \
        "dòng không tên phải mang nhãn nói rõ là tệp không ghi, không bịa tên"


# ──────────────────────────────────────────────────────────────────────────────────────────────
# BT-N13 · HAI TỆP KHÁC NHAU, CÙNG LOẠI, CÙNG THÁNG — phép thử sinh ra từ một lỗi thật
# ──────────────────────────────────────────────────────────────────────────────────────────────
def test_btn13_hai_tep_khac_nhau_cung_loai_cung_thang_la_hai_so_rieng(db):
    """PHÉP THỬ NÀY VIẾT SAU KHI CHẠY TRÊN TỆP THẬT, vì bộ phép thử cũ KHÔNG bắt được lỗi.

    Bản đầu đặt mã sổ theo LOẠI + THÁNG. Tháng 3/2026 có nhiều tệp visa khác nhau — 'VISA LẺ CHÂU
    ÂU T3.2026' và 'VISA LẺ T3.2026 ĐH PHẠM THỊ THÚY VY' là hai sổ của hai người. Chúng rơi vào
    cùng một mã và tệp sau ghi đè tệp trước: bảng xem trước nói 43 sổ / 8.372.328.008 đ, ghi xuống
    thật còn 17 sổ / 4.511.136.000 đ. **Mất 3,86 tỷ, mất im lặng.**

    BT-N11 ('bảng xem trước không được nói dối') lẽ ra phải bắt đúng chuyện này, và nó VẪN XANH —
    vì bài thử của nó không có hai tệp nào trùng loại và trùng tháng. Một phép thử không chạm tới
    tình huống thật thì nó chỉ là một câu ghi chú.
    """
    a = _tep(ten_tep="QUYẾT TOÁN VISA LẺ CHÂU ÂU T3.2026.xlsx")
    b = _tep(ten_tep="QUYẾT TOÁN VISA LẺ T3.2026 ĐH PHẠM THỊ THÚY VY.xlsx",
             dong=[_dong("LÊ VĂN C", "UYỂN NHI", 4_000_000,
                         chi=[{"khoan": "Phí LSQ", "so_tien": 1_000_000}])])
    assert BT.ma_chuyen(a) != BT.ma_chuyen(b), "hai tệp khác nhau KHÔNG được dùng chung một sổ"

    xem = BT.kiem_lo(db, [a, b])
    db.commit()
    kq = _nap(db, [a, b])
    s = _so(db)
    assert len(s["tour"]) == 2, "hai tệp phải ra HAI sổ — một sổ nghĩa là một tệp đã bị ghi đè"
    assert s["thu"] == 17_380_000, "tiền của cả hai tệp phải vào đủ, không tệp nào bị nuốt"
    assert len(s["khach"]) == 3
    # Và bảng xem trước phải nói đúng con số ấy TRƯỚC khi bấm.
    assert xem["tien"]["thu"] == kq["tien"]["thu"] == s["thu"]
    assert xem["da_nap"] == kq["da_nap"] == 2


def test_btn13b_dung_mot_tep_gui_hai_lan_trong_lo_thi_tru_ra_chu_khong_cong_doi(db):
    """Khác hẳn trên: đây là CÙNG MỘT tệp gửi trùng. Chỉ lần đầu được ghi — và bảng xem trước phải
    TRỪ nó ra khỏi tổng, không chỉ ghi chú bên cạnh."""
    a = _tep()
    xem = BT.kiem_lo(db, [a, _tep()])
    db.commit()
    assert xem["da_nap"] == 1, "cùng một tệp hai lần chỉ nạp được một"
    assert xem["tien"]["thu"] == 13_380_000, "tổng xem trước KHÔNG được cộng đôi"
    assert xem["dem"]["trung_trong_lo"] == 1
    kq = _nap(db, [a, _tep()])
    s = _so(db)
    assert len(s["tour"]) == 1 and s["thu"] == 13_380_000 == kq["tien"]["thu"]
    # `da_nap` phải bằng đúng con số bảng xem trước đã hứa. Thêm sau khi bẻ mã: bỏ chỗ chặn trùng
    # trong `nap_lo` mà bộ phép thử VẪN XANH — vì không chỗ nào so hai con số ấy với nhau. Cửa nói
    # "đã nạp 2" trong khi chỉ có 1 sổ là cửa tự mâu thuẫn, và người đọc tin con số to hơn.
    assert kq["da_nap"] == xem["da_nap"] == 1, \
        "số đã nạp phải khớp bảng xem trước, không đếm tệp trùng thành hai"
