"""TM-1 · vietourist.com.vn chạy SONG SONG với vietourist.vn (Chủ tịch chốt 02/11/2026).

crm./kh./dt./ir.vietourist.com.vn vào đúng cổng như bản .vn; kh.vietourist.com.vn/tours, /hotel, /restaurant
như kh.vietourist.vn. Tên gốc vietourist.com.vn và www. vẫn là WEB CŨ (máy chủ 103.216.118.43) — cổng thẻ
KHÔNG được trả khách về đó, và một tên giả dạng (…com.vn.evil.com) cũng không.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


def _doc(p: str) -> str:
    return (GOC / p).read_text(encoding="utf-8")


def test_luat_1_cong_the_tra_ve_dung_ho_com_vn():
    from app.services import tour_online as TR
    assert TR.goc_tra_ve("https://kh.vietourist.com.vn") == "https://kh.vietourist.com.vn/tours"
    assert TR.goc_tra_ve("https://ir.vietourist.com.vn/") == "https://ir.vietourist.com.vn/tours"
    assert TR.goc_tra_ve("https://crm.vietourist.com.vn") == "https://crm.vietourist.com.vn/kham-pha/tours"
    # bản .vn giữ nguyên
    assert TR.goc_tra_ve("https://kh.vietourist.vn") == "https://kh.vietourist.vn/tours"


def test_luat_2_web_cu_va_ten_gia_dang_khong_nhan():
    from app.services import tour_online as TR
    mac_dinh = "https://kh.vietourist.vn/tours"
    for o in ("https://vietourist.com.vn", "https://www.vietourist.com.vn", "https://hotel.vietourist.com.vn",
              "http://kh.vietourist.com.vn", "https://kh.vietourist.com.vn.evil.com", "https://evilkh.vietourist.com.vn"):
        assert TR.goc_tra_ve(o) == mac_dinh, o


def test_luat_3_dat_ban_va_khach_san_cung_luat():
    from app.api.v1 import dat_ban as DB

    class R:
        def __init__(self, o): self.headers = {"origin": o}
    assert DB._goc(R("https://kh.vietourist.com.vn")) == "https://kh.vietourist.com.vn"
    assert DB._goc(R("https://kh.vietourist.vn")) == "https://kh.vietourist.vn"
    for o in ("https://vietourist.com.vn", "https://www.vietourist.com.vn", "https://kh.vietourist.com.vn.evil.com"):
        assert DB._goc(R(o)) == DB.GOC_MAC_DINH, o


def test_luat_4_ba_trang_rieng_tren_kh_com_vn():
    s = _doc("web/next.config.mjs")
    m = re.search(r'type:\s*"host",\s*value:\s*"([^"]+)"', s)
    assert m
    rx = re.compile(m.group(1).replace("\\\\", "\\"))
    for h in ("kh.vietourist.vn", "dt.vietourist.vn", "ir.vietourist.vn",
              "kh.vietourist.com.vn", "dt.vietourist.com.vn", "ir.vietourist.com.vn"):
        assert rx.fullmatch(h), h
    for h in ("crm.vietourist.vn", "crm.vietourist.com.vn", "vietourist.com.vn", "www.vietourist.com.vn"):
        assert not rx.fullmatch(h), h       # /tours ở crm là màn VTOS; gốc .com.vn là web cũ


def test_luat_5_khoa_cung_cg3_cho_ca_ho_com_vn():
    s = _doc("web/lib/cong.ts")
    m = re.search(r"TEN_MIEN_CONG\s*=\s*\[(.*?)\];", s, re.S)
    ds = set(re.findall(r'"([a-z.]+)"', m.group(1)))
    assert ds == {"kh.vietourist.vn", "dt.vietourist.vn", "ir.vietourist.vn",
                  "kh.vietourist.com.vn", "dt.vietourist.com.vn", "ir.vietourist.com.vn"}
    assert '"https://crm.vietourist.com.vn"' in s and '"https://crm.vietourist.vn"' in s
