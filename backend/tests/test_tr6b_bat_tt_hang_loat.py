# -*- coding: utf-8 -*-
"""TR-6b · 13/11/2026 — CỬA BẬT / ĐÓNG THANH TOÁN HÀNG LOẠT.

VÌ SAO TỆP NÀY TỒN TẠI. Chủ tịch yêu cầu mở thanh toán cho cả 380 sản phẩm. Không có cửa hàng
loạt nên cách duy nhất là gọi cửa một-sản-phẩm 380 lượt, và việc ấy đã làm VTOS mất API HAI lần
trong một đêm (02:11–02:16 và 02:21–02:25, 13/11/2026) — lần sau đi chậm hơn vẫn chết. Hàm
`bat_tt_hang_loat` đổi vài trăm lượt ấy thành MỘT giao dịch.

Một hàm sinh ra để đổi vài trăm dòng trong một nhịp thì phải bị canh đúng ba chỗ:

  1. QUYỀN — nó cao hơn cửa một sản phẩm, vì mở cả kho là quyết định kinh doanh.
  2. ĐẾM — `da_doi` phải là số dòng THỰC SỰ đổi, nếu không người bấm không biết lần đầu đã ăn.
  3. KHÔNG VƯỢT PHẠM VI — nó chỉ chạm cột `mo_thanh_toan` của sản phẩm đang hoạt động, KHÔNG
     chạm công tắc chung và KHÔNG chạm sản phẩm đã nghỉ.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 11, 13, 9, 0)
HOM_NAY = NOW.date()


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import cong_khach as K
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("tpdh", "tp_dh"), ("ct", "chutich"), ("kd", "nv_kd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, department="", password_hash="x"))
    s.commit()
    monkeypatch.setattr(K, "_hom_nay", lambda: HOM_NAY)
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _sp(s, ma, trang_thai="active", mo=False):
    from app.models.core import Product
    p = Product(code=ma, name=f"SẢN PHẨM {ma}", tour_type="le_noi_dia", departure_point="TP HCM",
                transport="Xe giường nằm", days=3, length_text="3N2Đ", deposit_pct=30, days_to_close=3,
                program="", status=trang_thai, mo_thanh_toan=mo)
    s.add(p); s.commit()
    return p


def _tour(s, p, ngay=dt.date(2026, 11, 20), gia=2_590_000, cho=10):
    from app.models.core import Tour
    t = Tour(code=f"{p.code}.{ngay:%d%m%y}", name="Tour package", tour_type=p.tour_type, start_date=ngay,
             end_date=ngay + dt.timedelta(days=2), operator_id=_u(s, "dh").id, status="da_duyet",
             price_per_pax=gia, price_chd=1_790_000, seats_open=cho, planned_pax=cho, imported=True,
             product_id=p.id, product_code=p.code)
    s.add(t); s.commit()
    return t


def _so_nhat_ky(s, hanh_dong=None):
    from app.models.core import AuditLog
    q = select(func.count()).select_from(AuditLog)
    if hanh_dong:
        q = q.where(AuditLog.action == hanh_dong)
    return s.execute(q).scalar_one()


# ── 1 · QUYỀN: CAO HƠN CỬA MỘT SẢN PHẨM ──────────────────────────────────────────────────────

def test_chi_chu_tich_tgd_duoc_bat_hang_loat(db):
    """Đây là phép thử quan trọng nhất của tệp.

    `bat_tt_sp` (một sản phẩm) cho TP Điều hành và TP/GĐ Kinh doanh — mở một tour là việc thường
    ngày của họ. Mở CẢ KHO một phát thì khác hẳn về mức. Nếu cửa hàng loạt dùng lại đúng bộ vai
    của cửa một sản phẩm thì ta đã lặng lẽ nâng quyền của ba vai kia mà không ai quyết định điều đó.
    """
    from app.services import tour_online as TR
    p = _sp(db, "DL001"); _tour(db, p)

    with pytest.raises(TR.LoiTour):
        TR.bat_tt_hang_loat(db, _u(db, "tpdh"), True, "tat_ca", HOM_NAY)   # được phép mở MỘT sản phẩm
    with pytest.raises(TR.LoiTour):
        TR.bat_tt_hang_loat(db, _u(db, "kd"), True, "tat_ca", HOM_NAY)
    db.rollback()

    assert TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "tat_ca", HOM_NAY)["da_doi"] == 1


def test_quyen_hang_loat_HEP_hon_quyen_cua_mot_san_pham(db):
    """Ghi thành phép thử để lần sau ai nới bộ vai hàng loạt thì hàng rào đỏ ngay.

    Quan hệ phải là tập con THỰC SỰ: mọi vai mở được cả kho thì cũng mở được một tour, nhưng
    không ngược lại.
    """
    from app.services import tour_online as TR
    assert set(TR.VAI_TT_CHUNG) < set(TR.VAI_GHEP)
    assert "tp_dh" in TR.VAI_GHEP and "tp_dh" not in TR.VAI_TT_CHUNG


def test_vai_bi_chan_thi_khong_doi_mot_dong_nao(db):
    """Chặn quyền phải chặn TRƯỚC khi gán, không phải gán rồi mới báo lỗi."""
    from app.services import tour_online as TR
    p = _sp(db, "DL001"); _tour(db, p)
    with pytest.raises(TR.LoiTour):
        TR.bat_tt_hang_loat(db, _u(db, "tpdh"), True, "tat_ca", HOM_NAY)
    db.rollback()
    assert bool(db.get(type(p), p.id).mo_thanh_toan) is False
    assert _so_nhat_ky(db) == 0


# ── 2 · BỘ LỌC ───────────────────────────────────────────────────────────────────────────────

def test_co_chuyen_chi_cham_san_pham_dang_co_chuyen_ban(db):
    """Bộ lọc mặc định. Mở thanh toán cho sản phẩm không có chuyến nào đang bán thì khách bấm
    vào cũng không trả được tiền — mở nó chỉ làm bẩn số liệu."""
    from app.services import tour_online as TR
    co = _sp(db, "DL001"); _tour(db, co)
    khong = _sp(db, "DL002")                                          # không có chuyến
    qua = _sp(db, "DL003"); _tour(db, qua, ngay=dt.date(2026, 11, 1))  # chuyến đã khởi hành

    kq = TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "co_chuyen", HOM_NAY)
    assert (kq["so_xet"], kq["da_doi"]) == (1, 1)
    assert bool(db.get(type(co), co.id).mo_thanh_toan) is True
    assert bool(db.get(type(khong), khong.id).mo_thanh_toan) is False
    assert bool(db.get(type(qua), qua.id).mo_thanh_toan) is False


def test_tat_ca_cham_moi_san_pham_dang_hoat_dong(db):
    from app.services import tour_online as TR
    a = _sp(db, "DL001"); _tour(db, a)
    b = _sp(db, "DL002")
    kq = TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "tat_ca", HOM_NAY)
    assert (kq["so_xet"], kq["da_doi"]) == (2, 2)
    assert bool(db.get(type(b), b.id).mo_thanh_toan) is True


def test_san_pham_da_nghi_KHONG_bi_cham(db):
    """Sản phẩm `status` khác `active` là sản phẩm đã rút khỏi kho. «Tất cả» nghĩa là tất cả
    sản phẩm đang hoạt động, không phải tất cả dòng trong bảng."""
    from app.services import tour_online as TR
    song = _sp(db, "DL001")
    nghi = _sp(db, "DL009", trang_thai="inactive")
    kq = TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "tat_ca", HOM_NAY)
    assert (kq["so_xet"], kq["da_doi"]) == (1, 1)
    assert bool(db.get(type(song), song.id).mo_thanh_toan) is True
    assert bool(db.get(type(nghi), nghi.id).mo_thanh_toan) is False


def test_bo_loc_la_thi_bao_loi_chu_khong_doan(db):
    """Gõ nhầm tên bộ lọc («co-chuyen» thay vì «co_chuyen») phải ra lỗi.

    Nếu bộ lọc lạ rơi về «tất cả» thì một lỗi chính tả mở cả kho."""
    from app.services import tour_online as TR
    p = _sp(db, "DL001")
    for la in ("co-chuyen", "", "tatca", "ALL"):
        with pytest.raises(TR.LoiTour):
            TR.bat_tt_hang_loat(db, _u(db, "ct"), True, la, HOM_NAY)
    db.rollback()
    assert bool(db.get(type(p), p.id).mo_thanh_toan) is False


# ── 3 · ĐẾM: `da_doi` LÀ SỐ DÒNG THỰC SỰ ĐỔI ─────────────────────────────────────────────────

def test_bam_lan_hai_ra_khong_doi_dong_nao(db):
    """Cách duy nhất người bấm biết lần đầu đã ăn.

    Nếu `da_doi` đếm số dòng XÉT thay vì số dòng ĐỔI thì lần nào bấm cũng báo «đã đổi 380» và
    con số ấy không nói lên điều gì."""
    from app.services import tour_online as TR
    for ma in ("DL001", "DL002", "DL003"):
        _tour(db, _sp(db, ma))
    mot = TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "co_chuyen", HOM_NAY)
    hai = TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "co_chuyen", HOM_NAY)
    assert (mot["so_xet"], mot["da_doi"]) == (3, 3)
    assert (hai["so_xet"], hai["da_doi"]) == (3, 0)


def test_chi_dem_dong_dang_khac_trang_thai_muon_den(db):
    from app.services import tour_online as TR
    _tour(db, _sp(db, "DL001", mo=True))        # đã mở sẵn
    _tour(db, _sp(db, "DL002"))
    kq = TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "co_chuyen", HOM_NAY)
    assert (kq["so_xet"], kq["da_doi"]) == (2, 1)


def test_dong_hang_loat_cung_dem_dung(db):
    """Cửa phải đóng được, không chỉ mở được — sự cố thì cần một nhịp rút lại."""
    from app.services import tour_online as TR
    a = _sp(db, "DL001", mo=True); _tour(db, a)
    b = _sp(db, "DL002", mo=True); _tour(db, b)
    kq = TR.bat_tt_hang_loat(db, _u(db, "ct"), False, "co_chuyen", HOM_NAY)
    assert (kq["bat"], kq["so_xet"], kq["da_doi"]) == (False, 2, 2)
    assert bool(db.get(type(a), a.id).mo_thanh_toan) is False


# ── 4 · KHÔNG VƯỢT PHẠM VI ───────────────────────────────────────────────────────────────────

def test_bat_hang_loat_KHONG_bat_cong_tac_chung(db):
    """Hai công tắc, hai quyết định.

    `mo_thanh_toan(db, p, chung)` đòi CẢ HAI cùng bật. Nếu cửa hàng loạt cũng bật luôn công tắc
    chung thì một lần bấm mở bán cả hệ thống — đúng thứ công tắc chung được dựng để ngăn.
    """
    from app.services import tour_online as TR
    p = _sp(db, "DL001"); _tour(db, p)
    assert TR.tt_chung(db) is False
    TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "co_chuyen", HOM_NAY)
    assert TR.tt_chung(db) is False
    assert TR.mo_thanh_toan(db, db.get(type(p), p.id), TR.tt_chung(db)) is False


# ── 5 · NHẬT KÝ: MỘT DÒNG, CÓ SỐ, CÓ BỘ LỌC ──────────────────────────────────────────────────

def test_mot_thao_tac_mot_dong_nhat_ky_mang_du_so(db):
    """Một thao tác đổi 300 dòng mà nhật ký không nói nó đổi những gì thì sáu tháng sau không
    ai dựng lại được chuyện đã xảy ra. Và nó phải là MỘT dòng, không phải 300 dòng."""
    from app.models.core import AuditLog
    from app.services import tour_online as TR
    for ma in ("DL001", "DL002", "DL003"):
        _tour(db, _sp(db, ma))
    TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "co_chuyen", HOM_NAY)

    assert _so_nhat_ky(db) == 1
    r = db.execute(select(AuditLog)).scalars().one()
    assert r.action == "tour_tt_hang_loat_mo"
    assert r.actor == "ct"
    assert r.entity == "tour-online:co_chuyen"
    assert (r.after["bo_loc"], r.after["so_xet"], r.after["so_doi"]) == ("co_chuyen", 3, 3)
    assert sorted(r.after["ma"]) == ["DL001", "DL002", "DL003"]


def test_dong_hang_loat_ghi_hanh_dong_khac(db):
    from app.services import tour_online as TR
    _tour(db, _sp(db, "DL001", mo=True))
    TR.bat_tt_hang_loat(db, _u(db, "ct"), False, "co_chuyen", HOM_NAY)
    assert _so_nhat_ky(db, "tour_tt_hang_loat_dong") == 1
    assert _so_nhat_ky(db, "tour_tt_hang_loat_mo") == 0


def test_chuoi_nhat_ky_van_lien_mach(db):
    """Một dòng nhật ký ghi trong cùng giao dịch với vài trăm dòng dữ liệu vẫn phải nối đúng
    băm trước — nếu không, cả chuỗi kiểm toán đứt từ chỗ này."""
    from app.services import rules as R
    from app.services import tour_online as TR
    for ma in ("DL001", "DL002"):
        _tour(db, _sp(db, ma))
    TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "co_chuyen", HOM_NAY)
    TR.bat_tt_hang_loat(db, _u(db, "ct"), False, "tat_ca", HOM_NAY)
    ok, n, _ = R.verify_chain(db)
    assert ok is True and n == 2


def test_lo_lon_van_MOT_dong_nhat_ky_va_danh_sach_ma_bi_cat(db):
    """Lô thật là 380 sản phẩm. Hai điều phải đúng cùng lúc ở quy mô ấy:

      · vẫn MỘT dòng nhật ký — đây là lý do hàm này tồn tại;
      · danh sách mã cắt ở 200 để không nhồi cả kho vào một ô JSON, nhưng `so_doi` vẫn là số
        THẬT, không phải số đã cắt.
    """
    from app.models.core import AuditLog
    from app.services import tour_online as TR
    for i in range(1, 231):
        _sp(db, f"DL{i:03d}")
    kq = TR.bat_tt_hang_loat(db, _u(db, "ct"), True, "tat_ca", HOM_NAY)

    assert (kq["so_xet"], kq["da_doi"]) == (230, 230)
    assert _so_nhat_ky(db) == 1
    r = db.execute(select(AuditLog)).scalars().one()
    assert r.after["so_doi"] == 230
    assert len(r.after["ma"]) == 200


# ── 6 · BỘ LỌC PHẢI LÀ MỘT DANH SÁCH ĐÓNG, CÓ TÊN TIẾNG VIỆT ─────────────────────────────────

def test_moi_bo_loc_co_ten_de_hien_len_man(db):
    from app.services import tour_online as TR
    assert set(TR.LOC_HANG_LOAT) == {"tat_ca", "co_chuyen"}
    for ma, ten in TR.LOC_HANG_LOAT.items():
        assert ten and ten != ma
