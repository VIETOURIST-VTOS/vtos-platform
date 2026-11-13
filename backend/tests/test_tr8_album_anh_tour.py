# -*- coding: utf-8 -*-
"""TR-8 · 13/11/2026 — ALBUM ẢNH TOUR.

Đo trên kh.vietourist.vn/tours ngày 13/11/2026: **13 trong 85 tour không có một tấm ảnh nào**,
và trong 33 tour đang có chuyến mở bán thì **22 tour thiếu ảnh**. Nội dung tour đọc từ
vietourist.com.vn nên chỗ này không sửa được bằng mã — chỉ sửa được bằng một cửa để người của
anh đưa ảnh lên. Tệp này canh cái cửa ấy.

BỐN ĐIỀU PHẢI ĐÚNG, VÀ MỖI ĐIỀU LÀ MỘT CÁCH HỎNG THẬT:

  1. ẢNH TẢI LÊN ĐỨNG TRƯỚC, ẢNH WEB NỐI SAU, KHÔNG MẤT TẤM NÀO. Nếu ghép sai thứ tự thì công
     sức chụp ảnh nằm dưới đáy; nếu ghép kiểu thay thế thì web cũ mất trắng.
  2. BẢN GỐC KHÔNG BAO GIỜ RA CỔNG. Ảnh gốc mang EXIF — toạ độ GPS của người chụp. Một đường
     rò ảnh gốc là công bố nơi ở của nhân viên cho bất kỳ ai tải ảnh về.
  3. ẢNH GỠ LÀ BIẾN KHỎI CỔNG NGAY. Gỡ một tấm sai mà khách vẫn thấy thì nút gỡ vô nghĩa.
  4. KHÔNG PHẢI AI CŨNG XOÁ ĐƯỢC ẢNH CỦA NGƯỜI KHÁC.
"""
import datetime as dt
import io

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 11, 13, 9, 0)
HOM_NAY = NOW.date()


def _anh_that(mau=(200, 80, 40), co=(60, 40)) -> bytes:
    """Một tấm PNG thật — phép thử phải đi qua đúng đường xử lý ảnh, không giả bytes."""
    from PIL import Image
    o = io.BytesIO()
    Image.new("RGB", co, mau).save(o, "PNG")
    return o.getvalue()


@pytest.fixture()
def db(monkeypatch, tmp_path):
    import app.models  # noqa: F401
    from app.core.config import settings
    from app.db.session import Base
    from app.models.core import User
    from app.services import cong_khach as K
    from app.services import storage as ST
    settings.VISA_STORAGE = "local"
    settings.VISA_DOC_DIR = str(tmp_path / "kho")
    ST.reset_storage()
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("mkt", "nv_mkt"), ("ptgd", "ptgd_mkt"), ("dh", "nv_dh"), ("tpdh", "tp_dh"),
                     ("ct", "chutich"), ("kt", "ketoan"), ("sa", "sales_admin")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, department="", password_hash="x"))
    s.commit()
    monkeypatch.setattr(K, "_hom_nay", lambda: HOM_NAY)
    yield s
    s.close()
    ST.reset_storage()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _sp(s, ma="DL001", anh_web=None):
    from app.models.core import Product
    p = Product(code=ma, name=f"TOUR {ma}", tour_type="le_noi_dia", departure_point="TP HCM",
                transport="Xe", days=3, length_text="3N2Đ", deposit_pct=30, days_to_close=3,
                program="", status="active",
                noi_dung_web={"anh": list(anh_web)} if anh_web else None)
    s.add(p); s.commit()
    return p


def _tai(s, ten_nguoi, pid, mau=(200, 80, 40), nhom="diem_den", **kw):
    from app.services import anh_tour as AT
    return AT.tai_anh(s, _u(s, ten_nguoi), pid, kw.pop("ten_tep", "anh.png"), _anh_that(mau),
                      {"nhom": nhom, "can_cu": kw.pop("can_cu", "vtd_chup"), **kw}, NOW)


# ── 1 · TẢI LÊN ─────────────────────────────────────────────────────────────────────────────

def test_ba_phong_deu_tai_duoc(db):
    """Chủ tịch chốt 13/11: Marketing, Điều hành, Kinh doanh."""
    from app.services import anh_tour as AT
    p = _sp(db)
    for i, ai in enumerate(("mkt", "ptgd", "dh", "tpdh")):
        x, moi = _tai(db, ai, p.id, mau=(10 * i + 1, 20, 30))
        assert moi is True and x.tai_boi == ai
    assert len(AT._cua(db, p.id)) == 4


def test_vai_ngoai_ba_phong_bi_chan(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    for ai in ("kt", "sa"):
        with pytest.raises(AT.LoiTour):
            _tai(db, ai, p.id)
    db.rollback()
    assert AT._cua(db, p.id) == []


def test_tai_la_HIEN_NGAY_khong_co_buoc_duyet(db):
    """KS-16c (31/10/2026), nhắc lại cho tour 13/11: bỏ duyệt ảnh — tải là hiện.

    Nếu ai đó thêm lại bước duyệt mà quên đổi chỗ này, ảnh tải lên sẽ nằm im không ra cổng và
    không ai hiểu vì sao.
    """
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    assert x.trang_thai == "da_duyet"


def test_anh_dau_tien_la_anh_bia(db):
    p = _sp(db)
    a, _ = _tai(db, "mkt", p.id, mau=(1, 2, 3))
    b, _ = _tai(db, "mkt", p.id, mau=(9, 9, 9))
    assert a.la_bia is True and b.la_bia is False
    assert (a.thu_tu, b.thu_tu) == (1, 2)


def test_tai_lai_cung_mot_tam_khong_sinh_ban_trung(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    a, moi1 = _tai(db, "mkt", p.id, mau=(7, 7, 7))
    b, moi2 = _tai(db, "dh", p.id, mau=(7, 7, 7))
    assert (moi1, moi2) == (True, False)
    assert a.id == b.id and len(AT._cua(db, p.id)) == 1


def test_tep_khong_phai_anh_bi_chan(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    with pytest.raises(AT.LoiTour):
        AT.tai_anh(db, _u(db, "mkt"), p.id, "hop_dong.pdf", b"%PDF-1.4 xin chao",
                   {"nhom": "diem_den", "can_cu": "vtd_chup"}, NOW)


def test_phai_chon_nhom_va_can_cu_hop_le(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    with pytest.raises(AT.LoiTour):
        _tai(db, "mkt", p.id, nhom="")
    with pytest.raises(AT.LoiTour):
        _tai(db, "mkt", p.id, can_cu="muon_tren_mang")


def test_can_cu_mac_dinh_la_chua_xac_minh_chu_khong_phai_da_co_quyen(db):
    """Mặc định phải là điều AN TOÀN để nói: chưa xác minh. Mặc định «đã có quyền» là tự khai
    một điều chưa ai kiểm — và ảnh thì đang nằm công khai trên internet."""
    from app.models.anh_tour import AnhTour
    from app.services import anh_tour as AT
    assert AnhTour.__table__.c.can_cu.default.arg == "chua_xac_minh"
    assert "chua_xac_minh" in AT.CAN_CU_ANH_TOUR


# ── 2 · GHÉP VÀO CỔNG KHÁCH: TẢI LÊN TRƯỚC, WEB SAU ─────────────────────────────────────────

def test_anh_tai_len_dung_TRUOC_anh_web_va_khong_mat_anh_web(db):
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA TỆP — đúng câu Chủ tịch chốt 13/11/2026."""
    from app.services import tour_online as TR
    web = ["https://vietourist.com.vn/a.jpg", "https://vietourist.com.vn/b.jpg"]
    p = _sp(db, anh_web=web)
    x, _ = _tai(db, "mkt", p.id)
    the = TR.the_san_pham(p, [], 2, HOM_NAY, False, TR._anh_tai(db, [p.id]).get(p.id))
    assert the["anh"][0] == f"/api/v1/cong/mo/tour-online/anh/{x.id}/hien"
    assert the["anh"][1:] == web                      # ảnh web còn nguyên, nối ngay sau


def test_khong_tai_anh_nao_thi_cong_van_dung_anh_web(db):
    from app.services import tour_online as TR
    web = ["https://vietourist.com.vn/a.jpg"]
    p = _sp(db, anh_web=web)
    the = TR.the_san_pham(p, [], 2, HOM_NAY, False, TR._anh_tai(db, [p.id]).get(p.id))
    assert the["anh"] == web


def test_duong_ra_cong_la_cua_CONG_KHAI_va_chi_ban_hien_thi(db):
    """Cửa trong nhà đòi đăng nhập — khách không mở được. Đưa nhầm đường ấy ra thẻ tour thì
    mọi ảnh thành ô trống, và không ai thấy lỗi cho tới khi khách phàn nàn."""
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    d = AT.duong_cong(db, [p.id])[p.id][0]
    assert d.startswith("/api/v1/cong/mo/")
    assert d.endswith("/hien") and "/goc" not in d


# ── 3 · BẢN GỐC KHÔNG BAO GIỜ RA NGOÀI ──────────────────────────────────────────────────────

def test_cong_khach_KHONG_doc_duoc_ban_goc(db):
    """Bản gốc mang EXIF: toạ độ GPS, giờ chụp, số máy của người chụp."""
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    with pytest.raises(AT.LoiTour):
        AT.tep(db, None, x.id, "goc")
    assert AT.tep(db, None, x.id, "hien")[0]            # bản hiển thị thì được


def test_nguoi_trong_nha_doc_duoc_ban_goc(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    assert AT.tep(db, _u(db, "mkt"), x.id, "goc")[0]


def test_ban_hien_thi_la_WEBP_va_nhe_hon_hoac_bang_ban_goc(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    data, a = AT.tep(db, None, x.id, "hien")
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"


# ── 4 · GỠ ẢNH SAI LÀ BIẾN KHỎI CỔNG NGAY ───────────────────────────────────────────────────

def test_an_anh_thi_cong_khach_khong_con_thay(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    assert AT.duong_cong(db, [p.id]).get(p.id)
    AT.an(db, _u(db, "mkt"), x.id, True)
    assert AT.duong_cong(db, [p.id]).get(p.id) is None
    with pytest.raises(AT.LoiTour):
        AT.tep(db, None, x.id, "hien")


def test_bat_lai_thi_hien_lai(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    AT.an(db, _u(db, "mkt"), x.id, True)
    AT.an(db, _u(db, "mkt"), x.id, False)
    assert AT.duong_cong(db, [p.id]).get(p.id)


def test_nguoi_khac_khong_go_duoc_anh_cua_minh(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id)
    with pytest.raises(AT.LoiTour):
        AT.an(db, _u(db, "dh"), x.id, True)             # cùng quyền tải, nhưng không phải ảnh của mình
    db.rollback()
    with pytest.raises(AT.LoiTour):
        AT.xoa(db, _u(db, "dh"), x.id)
    db.rollback()
    assert AT.duong_cong(db, [p.id]).get(p.id)


def test_ptgd_marketing_va_tp_dieu_hanh_go_duoc_moi_anh(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    x, _ = _tai(db, "mkt", p.id, mau=(1, 1, 1))
    y, _ = _tai(db, "mkt", p.id, mau=(2, 2, 2))
    AT.an(db, _u(db, "ptgd"), x.id, True)
    AT.xoa(db, _u(db, "tpdh"), y.id)
    assert AT._cua(db, p.id) == [db.get(type(x), x.id)]


# ── 5 · THIẾU ẢNH: BÁO ĐÚNG SAU KHI ĐÃ TẢI ──────────────────────────────────────────────────

def test_tai_anh_xong_thi_het_bi_bao_thieu_anh(db):
    """Màn /tour-online in «Thiếu ảnh» để người của anh biết đi vá. Vá xong mà vẫn báo thiếu
    thì danh sách việc không bao giờ ngắn lại và không ai tin nó nữa."""
    from app.services import tour_online as TR
    p = _sp(db)
    assert "anh" in TR.thieu_noi_dung(p, [], False, False)
    assert "anh" not in TR.thieu_noi_dung(p, [], False, True)


# ── 6 · TRẦN ALBUM VÀ THỨ TỰ ────────────────────────────────────────────────────────────────

def test_xep_lai_thu_tu_va_anh_dau_thanh_anh_bia(db):
    from app.services import anh_tour as AT
    p = _sp(db)
    a, _ = _tai(db, "mkt", p.id, mau=(1, 1, 1))
    b, _ = _tai(db, "mkt", p.id, mau=(2, 2, 2))
    AT.xep(db, _u(db, "mkt"), p.id, [b.id, a.id])
    db.refresh(a); db.refresh(b)
    assert (b.thu_tu, b.la_bia) == (1, True)
    assert (a.thu_tu, a.la_bia) == (2, False)
    assert AT.duong_cong(db, [p.id])[p.id][0].endswith(f"/{b.id}/hien")


def test_khong_xep_duoc_anh_cua_san_pham_khac(db):
    from app.services import anh_tour as AT
    p1, p2 = _sp(db, "DL001"), _sp(db, "DL002")
    a, _ = _tai(db, "mkt", p1.id, mau=(3, 3, 3))
    b, _ = _tai(db, "mkt", p2.id, mau=(4, 4, 4))
    with pytest.raises(AT.LoiTour):
        AT.xep(db, _u(db, "mkt"), p1.id, [a.id, b.id])


# ── 7 · LÕI DÙNG CHUNG VỚI CỔNG NHÀ HÀNG ────────────────────────────────────────────────────

def test_hai_cong_dung_CHUNG_mot_bo_xu_ly_anh():
    """Chép bộ xử lý ảnh ra hai bản nghĩa là sáu tháng sau sửa một bên, bên kia vẫn sai.
    Phép thử này đỏ ngay khi có người chép lại."""
    from app.services import anh_chung as AC
    from app.services import nha_hang as NH
    assert NH.KIEU_ANH is AC.KIEU_ANH
    assert (NH.CANH_HIEN, NH.CANH_NHO) == (AC.CANH_HIEN, AC.CANH_NHO)
    assert NH._lam_nhe(_anh_that()) [0] == AC.lam_nhe(_anh_that())[0]


def test_lam_nhe_tra_ve_hai_co_va_kich_thuoc_that():
    from app.services import anh_chung as AC
    hien, nho, rong, cao = AC.lam_nhe(_anh_that(co=(2000, 1000)))
    assert hien and nho and (rong, cao) == (2000, 1000)
    assert len(nho) < len(hien)
