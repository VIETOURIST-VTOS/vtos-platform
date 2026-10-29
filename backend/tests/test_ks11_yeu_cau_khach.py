# -*- coding: utf-8 -*-
"""KS-11 · Bảy phép thử cho cửa khách gửi yêu cầu. KHÔNG cần cơ sở dữ liệu.

Phép 6 và 7 đọc thẳng MÃ NGUỒN của cửa. Một phép thử gọi hàm chỉ chứng minh hàm chạy đúng;
nó không chứng minh được rằng KHÔNG CÓ cửa nào quên khoá, và «quên khoá một cửa» mới là cách
dữ liệu khách thật sự lọt ra ngoài.
"""
import os
import re
import types

from app.models import don_khach_san_ota as M
from app.services import dat_phong_ota as S

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUA = os.path.join(GOC, "app", "api", "v1", "don_khach_san_ota.py")

# Mã phiên tra giá của tài khoản đối tác Vietourist. Lọt ra ngoài là đưa chìa khoá kho giá.
MA_CUA_NGUON = ("ma_tim", "ma_khoi", "the_chao", "ma_goi_gia", "ma_phong", "ma_khach_san",
                "ma_don_nguon", "ma_hanh_trinh", "tham_chieu_nguon")

O_THE = re.compile(r"card_?number|so_the|cvv|cvc|card_holder|expiry", re.I)
MANG = re.compile(r"\b(httpx|aiohttp|urllib\.request|socket)\b|requests\.(get|post|put|delete)")


def _don(**kw):
    """Một đơn giả — đủ thuộc tính cho các hàm thuần, không chạm cơ sở dữ liệu."""
    d = types.SimpleNamespace(
        id=1, the_tham_chieu="VTDTEST", trang_thai="moi", tai_khoan_ngoai_id=None,
        noi_den="Đà Nẵng", ngay_nhan=None, ngay_tra=None, so_phong=1, nguoi_lon=2, tre_em=0,
        nguoi_nhan_phong="Trần A", yeu_cau_them="", gia_gom_thue=1234567, tien_te="VND",
        so_xac_nhan_ks="", gui_luc=None)
    for k, v in kw.items():
        setattr(d, k, v)
    return d


def _tk(**kw):
    t = types.SimpleNamespace(id=9, loai="khach_hang", trang_thai="hoat_dong")
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def test_ks11_1_moi_trang_thai_don_deu_co_cau_cho_khach():
    """Thiếu một khoá là một đơn hiện ra TRỐNG trên màn của khách."""
    thieu = [k for k in M.TRANG_THAI_DON if k not in M.DON_SANG_KHACH]
    assert thieu == [], "trạng thái chưa có câu cho khách: " + ", ".join(thieu)
    la = [v for v in M.DON_SANG_KHACH.values() if v not in M.TRANG_THAI_KHACH]
    assert la == [], "câu cho khách không có trong bảng chữ: " + ", ".join(la)


def test_ks11_2_bang_don_co_du_cot_chu_don():
    """Không có những cột này thì cửa khách KHÔNG được mở — đó là cả lý do của vòng này."""
    cot = M.DonKhachSanOta.__table__.columns
    for ten in ("tai_khoan_ngoai_id", "cong", "nguoi_nhan_phong", "lien_he", "noi_den",
                "yeu_cau_them", "gui_luc"):
        assert ten in cot, "thiếu cột " + ten
    assert cot["ota_id"].nullable, "ota_id phải nullable: yêu cầu của khách chưa có nguồn"
    assert cot["tai_khoan_ngoai_id"].nullable, "đơn Điều hành tự dựng không có chủ"


def test_ks11_3_khong_phai_chu_thi_khong_doc_duoc():
    """Biết thẻ tham chiếu KHÔNG phải là quyền đọc."""
    tk = _tk(id=9)
    assert S.la_chu_don(_don(tai_khoan_ngoai_id=9), tk) is True
    assert S.la_chu_don(_don(tai_khoan_ngoai_id=10), tk) is False
    # Đơn không có chủ: không ai ở cổng ngoài đọc được, kể cả người biết thẻ.
    assert S.la_chu_don(_don(tai_khoan_ngoai_id=None), tk) is False
    assert S.la_chu_don(_don(tai_khoan_ngoai_id=9), None) is False


def test_ks11_4_tom_tat_khach_khong_lot_ma_cua_nguon():
    """Màn của khách không được mang theo mã phiên tra giá của Vietourist."""
    r = S.tom_tat_khach(_don(tai_khoan_ngoai_id=9, trang_thai="da_hoi_gia"))
    lot = [k for k in MA_CUA_NGUON if k in r]
    assert lot == [], "mã của nguồn lọt ra màn khách: " + ", ".join(lot)
    assert r["trang_thai"] == "co_gia"
    assert r["gia_gom_thue"] is not None
    # Chưa tra xong thì KHÔNG hiện số 0 — hiện 0 là nói dối khách một con số.
    assert S.tom_tat_khach(_don(trang_thai="moi"))["gia_gom_thue"] is None


def test_ks11_5_thieu_gi_thi_goi_dung_ten_o_ay():
    assert S.thieu_de_gui_yeu_cau(None, {}) == ["chưa đăng nhập cổng"]
    t = S.thieu_de_gui_yeu_cau(_tk(trang_thai="khoa"), {})
    assert any("khoá" in x for x in t)
    t = S.thieu_de_gui_yeu_cau(_tk(), {"noi_den": "Huế", "ngay_nhan": "2026-12-02",
                                       "ngay_tra": "2026-12-01", "so_phong": 1,
                                       "nguoi_lon": 2, "nguoi_nhan_phong": "A",
                                       "lien_he": "a@b.c"})
    assert t == ["ngày trả phải sau ngày nhận"]
    t = S.thieu_de_gui_yeu_cau(_tk(), {"noi_den": "Huế", "ngay_nhan": "2026-12-01",
                                       "ngay_tra": "2026-12-03", "so_phong": 1,
                                       "nguoi_lon": 2, "nguoi_nhan_phong": "A",
                                       "lien_he": "a@b.c"})
    assert t == []


def test_ks11_6_khach_khong_nhet_duoc_so_cua_nguon_vao_don():
    """`gui_yeu_cau` chỉ đọc những khoá khách được khai — danh sách ấy là hàng rào."""
    for k in S.SO_CUA_NGUON:
        assert k not in S.O_KHACH_KHAI, "khách không được khai " + k
    n = open(os.path.join(GOC, "app", "services", "dat_phong_ota.py"),
             encoding="utf-8").read()
    than = n[n.index("def gui_yeu_cau("):n.index("def don_cua_toi(")]
    for k in S.SO_CUA_NGUON:
        assert ('d.get("%s"' % k) not in than, "gui_yeu_cau đang đọc " + k

def test_ks11_7_soi_nguon_cua_cong_khach():
    """Mọi cửa cổng khách phải đi qua phiên cổng ngoài, và không cửa nào nhận số thẻ."""
    n = open(CUA, encoding="utf-8").read()
    assert O_THE.search(n) is None, "cửa đơn khách sạn KHÔNG được có ô số thẻ"
    assert MANG.search(n) is None, "tệp cửa không được gọi mạng — chỗ nối là nhan_so_nguon"
    assert 'APIRouter(prefix="/api/v1/cong/khach-san"' in n, \
        "cửa khách phải gắn vào tiền tố đã có, không mở nhóm API mới"
    khoi = n[n.index("router_cong = APIRouter"):]
    tay = re.findall(r"@router_cong\.\w+\([^\n]*\)\s*\ndef (\w+)\((.*?)\):\s*\n", khoi, re.S)
    assert len(tay) >= 3, "phải có đủ ba cửa cho khách, thấy %d" % len(tay)
    for ten, tham in tay:
        assert "Depends(tai_khoan_ngoai)" in tham, "cửa %s quên khoá phiên cổng" % ten
