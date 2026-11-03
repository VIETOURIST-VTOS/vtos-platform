# -*- coding: utf-8 -*-
"""KS-18 · Thẻ phòng chưa gắn ảnh riêng thì mượn ảnh khách sạn, có nhãn (Chủ tịch chọn «3» 03/11/2026).

Đọc thẳng tệp giao diện cổng — hai chiều:
  1. Phòng có ảnh riêng vẫn dùng ảnh riêng, không nhãn; phòng chưa có thì mượn ảnh khách sạn, nhãn «Ảnh khách sạn».
  2. Thứ tự mượn: nhóm «Phòng» chưa gắn phòng → album không phải bìa → mọi ảnh chưa gắn → mọi ảnh; mỗi thẻ một ảnh.
  3. Khách sạn không có ảnh nào thì vẫn ô «Ảnh đang cập nhật» (không bịa ảnh).
"""
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TEP = GOC / "web" / "components" / "cong" / "KhachSanVtd.tsx"


def _s() -> str:
    return TEP.read_text(encoding="utf-8")


def test_ks18_1_rieng_truoc_tam_sau_co_nhan():
    s = _s()
    assert "const rieng = p.anh?.[0] || aP[0];" in s
    assert "const anhP = rieng || anhTamPhong(anh, iP), tam = !rieng && !!anhP;" in s
    assert '{tam && <span className="ksv-ct ksv-tam">Ảnh khách sạn</span>}' in s, "ảnh mượn phải ghi rõ là ảnh khách sạn"


def test_ks18_2_thu_tu_muon_anh():
    s = _s()
    f = s[s.index("export function anhTamPhong"):]
    f = f[:f.index("\n}\n")]
    assert 'const tu = anh.filter((a) => !a.loai_phong_id);' in f, "không mượn ảnh đã gắn cho phòng khác"
    assert f.index('a.nhom === "phong"') < f.index("!a.la_bia"), "ưu tiên nhóm «Phòng» trước album"
    assert "kho[i % kho.length]" in f, "mỗi thẻ một ảnh, xoay vòng"


def test_ks18_3_khong_anh_thi_van_o_trong():
    s = _s()
    assert "return kho.length ? kho[i % kho.length] : null;" in s
    assert ': <AnhTrong k={ks} cao={150} />}' in s and "Ảnh đang cập nhật" in s
