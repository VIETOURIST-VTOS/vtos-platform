# -*- coding: utf-8 -*-
"""ĐỢT HDV-1 (làn R2) — hàng rào cho PHÉP ĐO nền địa bàn, và cho CỔNG 95%.

Phép thử quan trọng nhất ở tệp này KHÔNG đo dữ liệu — nó canh hai con số đã chốt TRƯỚC khi đo:
cổng 95% và "đủ 5 chuyến". Một phép đo mà ngưỡng sửa được sau khi nhìn kết quả thì không còn nói
gì cả; hạ cổng xuống 50% cho vừa dữ liệu là cách hỏng êm nhất, vì mọi thứ vẫn xanh.

Phần còn lại canh đúng ba chỗ phép đo dễ nói dối theo chiều dễ chịu:
  · đếm "đủ số chuyến" bằng MỌI chuyến thay vì chuyến NỐI ĐƯỢC về địa bàn,
  · mẫu số bằng 0 mà trả 0,0% thay vì "chưa đo được",
  · đếm một người hai lần khi một chuyến có hai dòng phân công.
"""
import os
import sys
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import Base  # noqa: E402
from app.models.core import Product, Tour  # noqa: E402
from app.models.hr import GuideAssignment  # noqa: E402
from app.services import dia_ban_hdv as DB_  # noqa: E402

HOM_QUA = date.today() - timedelta(days=30)
HOM_SAU = date.today() + timedelta(days=30)


@pytest.fixture()
def db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    yield s
    s.close()


def _san_pham(db, ma, region):
    p = Product(code=ma, name=ma, region=region)
    db.add(p); db.flush(); return p


def _chuyen(db, ma, product=None, da_chay=True, chi_ma=False):
    """`chi_ma=True`: chuyến chỉ có `product_code`, KHÔNG có `product_id` — đúng cảnh robot Vietrip
    để lại khi sản phẩm chưa kịp dựng."""
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia",
             start_date=(HOM_QUA if da_chay else HOM_SAU) - timedelta(days=2),
             end_date=(HOM_QUA if da_chay else HOM_SAU), operator_id=1,
             product_id=(None if (chi_ma or not product) else product.id),
             product_code=(product.code if product else ""))
    db.add(t); db.flush(); return t


def _phan(db, guide_id, tour):
    db.add(GuideAssignment(tour_id=tour.id, guide_id=guide_id)); db.flush()


# ── 1. hai con số đã CHỐT, và không ai được hạ ──────────────────────────────────────────────
def test_hd13_1_cong_phai_dung_95_khong_duoc_ha():
    """ĐIỀU CẤM của Chủ tịch nằm ở đây. Dưới 95% thì BÁO LẠI, không hạ cổng cho vừa dữ liệu.

    Đổi `CONG` thành 50 là phép thử này ĐỎ — đúng ý: hạ cổng phải là một quyết định có người ký,
    không phải một con số ai đó sửa cho hết đỏ.
    """
    assert DB_.CONG == 95.0, "cổng đã bị đổi khỏi 95% — ai đổi phải có quyết định của Chủ tịch"


def test_hd13_2_nguong_du_chuyen_phai_dung_5():
    assert DB_.NGUONG_CHUYEN == 5, "ngưỡng 'đủ số chuyến' chốt 22/10/2026 TRƯỚC khi đo, đừng sửa sau"


def test_hd13_3_ha_cong_xuong_50_thi_mot_bo_du_lieu_truot_se_thanh_qua(db):
    """Bẻ ngược, đúng câu nghiệm thu: bộ dữ liệu phủ ĐÚNG 60% ở CẢ HAI con số.

    60% trượt cổng 95 và qua cổng 50 — nên hạ cổng xuống 50 là phép thử này ĐỎ.

    BẢN ĐẦU CỦA PHÉP THỬ NÀY XANH VÌ LÝ DO SAI, và đó là lý do nó được viết lại. Bản ấy chỉ dựng
    độ phủ CHUYẾN 60%, còn độ phủ NGƯỜI rơi về 0% (một người 3 chuyến, chưa đủ 5). `qua_cong` đòi
    CẢ HAI con số qua cổng, nên nó vẫn False khi hạ cổng xuống 50 — phép thử xanh cả hai bên, tức
    không canh gì. Đo ra lúc chạy bẻ ngược lần đầu: hạ cổng chỉ làm ĐỎ phép thử ghim hằng số.
    """
    co = _san_pham(db, "SP-CO", "Miền Tây")
    n = 0
    for g in (1, 2, 3):                       # 3/5 người có đủ 5 chuyến CÓ địa bàn
        for _ in range(5):
            n += 1; _phan(db, g, _chuyen(db, f"T-CO{n}", co))
    for g in (4, 5):                          # 2/5 người chỉ có chuyến KHÔNG địa bàn
        for _ in range(5):
            n += 1; _phan(db, g, _chuyen(db, f"T-KHONG{n}", None))
    kq = DB_.do_nen(db)
    assert kq["do_phu_chuyen"] == 60.0 and kq["do_phu_nguoi"] == 60.0, kq
    assert kq["qua_cong"] is False, "cổng đã bị hạ: bộ dữ liệu phủ 60% mà vẫn báo QUA"
    assert "BÁO LẠI" in kq["ket_luan"]


# ── 2. ba chỗ phép đo dễ nói dối ────────────────────────────────────────────────────────────
def test_hd13_4_du_so_chuyen_chi_dem_chuyen_NOI_DUOC_ve_dia_ban(db):
    """20 chuyến không có địa bàn vẫn KHÔNG kết luận được địa bàn của người ấy."""
    for i in range(20):
        _phan(db, 7, _chuyen(db, f"T-R{i}", None))
    kq = DB_.do_nen(db)
    assert kq["so_hdv_co_chuyen"] == 1
    assert kq["so_hdv_du_chuyen"] == 0, "đếm cả chuyến không có địa bàn là 'đủ' — con số nói dối"
    assert kq["do_phu_nguoi"] == 0.0


def test_hd13_5_mau_so_bang_0_tra_CHUA_DO_DUOC_chu_khong_tra_0(db):
    """Không có chuyến nào đã chạy thì độ phủ là CHƯA ĐO ĐƯỢC. 0,0% đọc ra là 'đo rồi, phủ không'."""
    kq = DB_.do_nen(db)
    assert kq["do_phu_chuyen"] is None and kq["do_phu_nguoi"] is None, kq
    assert kq["qua_cong"] is False


def test_hd13_6_mot_chuyen_hai_dong_phan_cong_chi_dem_mot_lan(db):
    co = _san_pham(db, "SP-X", "Tây Nguyên")
    t = _chuyen(db, "T-X", co)
    _phan(db, 9, t); _phan(db, 9, t)
    for i in range(4):
        _phan(db, 9, _chuyen(db, f"T-Y{i}", co))
    kq = DB_.do_nen(db)
    assert kq["so_hdv_du_chuyen"] == 1, "5 chuyến thật mới là đủ — đếm trùng thì 4 chuyến đã 'đủ'"


def test_hd13_7_chuyen_CHUA_chay_khong_tinh_vao_mau(db):
    co = _san_pham(db, "SP-Z", "Miền Bắc")
    _phan(db, 3, _chuyen(db, "T-DA", co))
    _phan(db, 3, _chuyen(db, "T-CHUA", None, da_chay=False))
    kq = DB_.do_nen(db)
    assert kq["so_chuyen_da_chay"] == 1, "chuyến chưa khởi hành bị tính vào mẫu"
    assert kq["do_phu_chuyen"] == 100.0


def test_hd13_8_dia_ban_chi_co_khoang_trang_coi_nhu_RONG(db):
    _phan(db, 4, _chuyen(db, "T-TRANG", _san_pham(db, "SP-TRANG", "   ")))
    assert DB_.do_nen(db)["so_chuyen_co_dia_ban"] == 0


# ── 3. nhịp 1 KHÔNG được sửa một dòng dữ liệu nào ───────────────────────────────────────────
def test_hd13_9_phep_do_khong_ghi_gi_vao_co_so_du_lieu():
    import inspect
    ma = inspect.getsource(DB_)
    for cam in ("db.add(", "db.commit(", "db.delete(", "db.merge(", "update("):
        assert cam not in ma, f"nhịp 1 chỉ ĐO, không được sửa dữ liệu — thấy `{cam}`"


def test_hd13_10_in_ra_co_NGAY_va_hai_con_so(db):
    """Nghiệm thu đòi 'hai con số CÓ NGÀY' — một con số không ngày thì tháng sau không ai đối chiếu được."""
    ra = DB_._in_ra(DB_.do_nen(db))
    assert str(date.today().isoformat()) in ra
    assert "độ phủ CHUYẾN" in ra and "độ phủ NGƯỜI" in ra
# ── 4. HAI khoá nối, không phải một ─────────────────────────────────────────────────────────
def test_hd13_11_chuyen_chi_co_product_code_VAN_noi_duoc_ve_dia_ban(db):
    """Robot Vietrip LUÔN ghi `product_code`, còn `product_id` chỉ điền khi có sản phẩm khớp
    (`services/vietrip.py:138, :169, :381`). Đo bằng mỗi `product_id` là báo độ phủ THẤP HƠN sự
    thật, và nhịp 2 bị chặn oan. Bản đầu của phép đo này chỉ nối theo `product_id`."""
    co = _san_pham(db, "SP-MA", "Miền Trung")
    _phan(db, 1, _chuyen(db, "T-CHI-MA", co, chi_ma=True))
    kq = DB_.do_nen(db)
    assert kq["so_chuyen_co_dia_ban"] == 1, "chuyến chỉ có product_code bị coi là không có địa bàn"
    assert kq["do_phu_chuyen"] == 100.0


def test_hd13_12_bao_RIENG_tung_duong_noi(db):
    """Con số tổng không nói được nền đang dựa vào khoá nào — mà nhịp 2 cần đúng điều đó."""
    co = _san_pham(db, "SP-HAI", "Miền Tây")
    _phan(db, 1, _chuyen(db, "T-ID", co))
    _phan(db, 1, _chuyen(db, "T-MA", co, chi_ma=True))
    _phan(db, 1, _chuyen(db, "T-KHONG", None))
    kq = DB_.do_nen(db)
    assert kq["noi_bang_product_id"] == 1 and kq["noi_bang_product_code"] == 1, kq
    assert kq["so_chuyen_co_dia_ban"] == 2 and kq["so_chuyen_da_chay"] == 3
    assert "product_code" in DB_._in_ra(kq)


# ── 5. cửa CHỈ ĐỌC để đo trên hệ thật ───────────────────────────────────────────────────────
def test_hd13_13_co_cua_de_do_tren_he_that():
    """Nghiệm thu đòi hai con số CHẠY TRÊN DỮ LIỆU THẬT. Không có cửa thì không bao giờ đo được.

    Cửa phải CHỈ ĐỌC và phải đứng riêng — KHÔNG gắn vào `/health`, cửa Render gọi 5 giây một lần
    và đã từng làm sập máy chủ vì nặng.
    """
    import pathlib
    ma = (pathlib.Path(__file__).resolve().parents[1] / "app/api/v1/huong_dan.py").read_text(encoding="utf-8")
    assert '@router.get("/dia-ban/do-nen")' in ma, "chưa có cửa đo nền địa bàn"
    than = ma.split('@router.get("/dia-ban/do-nen")', 1)[1].split("@router.", 1)[0]
    assert "require_roles" in than, "cửa đo không có hàng rào quyền"
    for cam in (".post(", "db.add(", "db.commit("):
        assert cam not in than, f"cửa nhịp 1 phải CHỈ ĐỌC — thấy `{cam}`"
    rt = (pathlib.Path(__file__).resolve().parents[1] / "app/api/v1/routes.py").read_text(encoding="utf-8")
    hp = rt.split('@router.get("/health"', 1)[1].split("@router.", 1)[0]
    assert "dia_ban" not in hp, "đừng cắm phép đo vào /health"
