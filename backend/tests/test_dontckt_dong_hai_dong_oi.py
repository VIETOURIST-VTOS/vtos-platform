# -*- coding: utf-8 -*-
"""Đợt DỌN-TCKT 02/11/2026 — ĐÓNG NHỮNG DÒNG GIỮ CHỖ ĐÃ GỘP MÀ SỔ VẪN GIỮ.

Chủ tịch chốt 02/11/2026.

VÌ SAO ĐỢT NÀY SINH RA — nó là một việc hàng rào tự chỉ ra

Đợt LAN-TCKT dời bốn đợt R4c từ làn «Phân quyền» sang làn «TC-KT». Việc dời ấy biến những chồng
lấn TRONG một làn — mà hàng rào cố ý im lặng — thành chồng lấn GIỮA hai làn, là thứ nó phải kêu.
Nó kêu ba tệp:

    services/ket_so.py        R2-KC1  ×  R4c-2
    services/accounting.py    R2-KC1  ×  R4c-4
    services/ops.py           KS-16e  ×  R4c-3   (và KS-16d giữ cả api/v1/ops.py)

KHÔNG ĐOÁN DÒNG NÀO ÔI — ĐO. Đợt này KHÔNG chốt trước dòng nào sẽ đóng. Nó có một DANH SÁCH XÉT
và một PHÉP ĐO BA LỚP; dòng nào đủ ba lớp dấu trên main thì đóng, dòng nào thiếu một lớp thì để
nguyên. Nhờ vậy đợt này KHÔNG phụ thuộc thứ tự bấm: ai gộp xong trước thì dòng ấy đóng, ai chưa
thì dòng ấy còn giữ chỗ.

Ba lớp dấu — ba chỗ khác loại nên khó trùng:
    (1) tệp phép thử của đợt ấy có trên main
    (2) dấu mã của nó nằm trong TỪNG tệp mã mà dòng ấy khai
    (3) tệp di trú của nó có trên main (đợt nào không có di trú thì bỏ lớp này)

Đo được 02/11/2026 trước khi bấm:
  · KS-16d, KS-16e: đủ ba lớp → ôi, đóng.
  · R2-KC1: không một lớp nào (PR #578 đã đẩy, chưa gộp) → dòng ấy ĐÚNG, để nguyên. Nếu anh gộp
    #578 trước khi bấm đợt này thì nó tự đóng luôn dòng ấy, và R4c-2 với R4c-4 hết bị giữ.

ĐỢT NÀY KHÔNG ĐỤNG MỘT TỆP MÃ NÀO. Chỉ ô cuối của những dòng đã chứng minh được.
"""
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(GOC, "docs", "dang-lam")
PQ = os.path.join(THU_MUC, "phan-quyen.md")
TEP_DOT = os.path.join(THU_MUC, "phan-quyen", "DON-TCKT.md")

# DANH SACH XET — khong phai danh sach "se dong". Phep do quyet dinh.
XET = {
    "KS-16d": {
        "thu": "test_ks16d_de_nghi_chi_ncc.py",
        "ma": ["backend/app/services/ops.py",
               "backend/app/services/don_ks_vtd.py",
               "backend/app/services/dat_ban.py",
               "backend/app/api/v1/ops.py"],
        "di_tru": "ks16dc8e2b4f7a903_de_nghi_chi_ncc_thu_ho.py",
    },
    "KS-16e": {
        "thu": "test_ks16e_doanh_thu_hoa_hong.py",
        "ma": ["backend/app/services/ops.py",
               "backend/app/services/don_ks_vtd.py",
               "backend/app/services/dat_ban.py",
               "backend/app/services/chung_tu_loai.py"],
        "di_tru": "ks16ea3c5e7f9b104_doanh_thu_hoa_hong.py",
    },
    "R2-KC1": {
        "thu": "test_r2kc1_du_nguoc_chieu.py",
        "ma": ["backend/app/services/accounting.py",
               "backend/app/services/ket_so.py"],
        "di_tru": None,
    },
}


def _dong_cua(ma):
    """Dòng trong phan-quyen.md mang mã này — đúng một dòng, không thì đỏ."""
    ds = [d for d in open(PQ, encoding="utf-8").read().splitlines()
          if d.strip().startswith("|") and ("**" + ma + " —") in d]
    assert len(ds) == 1, f"{ma}: tìm thấy {len(ds)} dòng, cần đúng 1"
    return ds[0]


def _o(d):
    return [x.strip() for x in d.strip().strip("|").split("|")]


def _thieu(ma):
    """Những lớp dấu CÒN THIẾU của mã này trên main. Rỗng = đã gộp, chứng minh được."""
    cc = XET[ma]
    thieu = []
    if not os.path.exists(os.path.join(GOC, "backend", "tests", cc["thu"])):
        thieu.append("tệp phép thử " + cc["thu"])
    for tep in cc["ma"]:
        duong = os.path.join(GOC, *tep.split("/"))
        if not os.path.exists(duong):
            thieu.append("tệp " + tep)
        elif ma not in open(duong, encoding="utf-8").read():
            thieu.append("dấu trong " + tep)
    if cc["di_tru"] and not os.path.exists(
            os.path.join(GOC, "backend", "alembic", "versions", cc["di_tru"])):
        thieu.append("tệp di trú " + cc["di_tru"])
    return thieu


# ───────────────────────────────────────────────────────────────────── LUẬT 1
def test_dontckt_1_du_ba_lop_dau_thi_phai_la_xong():
    """Dòng nào chứng minh được là đã gộp thì KHÔNG được giữ chỗ nữa.

    Một dòng ôi giữ một tệp là một làn khác không viết được vào tệp ấy, và hàng rào đỏ vì một
    việc KHÔNG CÒN TỒN TẠI. Đó là cái giá của việc không ai dọn sổ.
    """
    for ma in XET:
        if _thieu(ma):
            continue
        o = _o(_dong_cua(ma))
        assert len(o) == 5, f"{ma}: dòng không còn năm cột"
        assert o[4].lower() == "xong", (
            f"{ma}: đủ ba lớp dấu trên main mà trạng thái vẫn là {o[4]!r}")


# ───────────────────────────────────────────────────────────────────── LUẬT 2
def test_dontckt_2_thieu_mot_lop_thi_KHONG_duoc_dong():
    """Chiều ngược, và đây là chiều nguy hơn.

    Đóng một dòng mà không chứng minh được là mở đường cho hai làn viết đè lên nhau mà hàng rào
    im lặng — đúng cái việc đợt này sinh ra để chống. Thiếu một lớp là chưa chứng minh được.
    """
    for ma in XET:
        thieu = _thieu(ma)
        if not thieu:
            continue
        o = _o(_dong_cua(ma))
        assert o[4].lower() == "đang làm", (
            f"{ma} đã bị đổi sang {o[4]!r} nhưng trên main còn thiếu: {thieu}. "
            f"Nếu nó gộp thật thì phải thấy đủ ba lớp dấu, không thấy thì không được đóng.")


# ───────────────────────────────────────────────────────────────────── LUẬT 3
def test_dontckt_3_it_nhat_hai_dong_da_dong():
    """Đo được 02/11/2026: KS-16d và KS-16e đủ ba lớp. Đợt này ít nhất phải đóng hai dòng ấy.

    Không có luật này thì một bản vá hỏng mà không vá được gì vẫn xanh, và cả đợt thành vô ích
    một cách im lặng.
    """
    xong = [ma for ma in XET if _o(_dong_cua(ma))[4].lower() == "xong"]
    assert "KS-16d" in xong and "KS-16e" in xong, (
        f"KS-16d và KS-16e phải «xong» sau đợt này; đang «xong»: {xong}")


# ───────────────────────────────────────────────────────────────────── LUẬT 4
def test_dontckt_4_khong_doi_mot_chu_nao_ngoai_o_trang_thai():
    """Chỉ ô cuối đổi. Sửa luôn mã việc của người khác là viết lại lịch sử của họ."""
    for ma, cc in XET.items():
        o = _o(_dong_cua(ma))
        assert o[0] == "Phân quyền", f"{ma}: cột Làn đã bị đổi thành {o[0]!r}"
        assert o[1].startswith("**" + ma + " —"), f"{ma}: mã việc đã bị sửa"
        assert re.fullmatch(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}", o[3]), f"{ma}: giờ bắt đầu đã bị sửa"
        for tep in cc["ma"]:
            assert tep in o[2], f"{ma}: danh sách tệp đã bị sửa — mất {tep}"


# ───────────────────────────────────────────────────────────────────── LUẬT 5
def test_dontckt_5_hai_tep_ops_khong_con_lan_nao_khac_giu():
    """ĐỢT NÀY ĐỂ LÀM GÌ: nhả `ops.py` và `api/v1/ops.py` cho R4c-3.

    Đo bằng chính bộ đọc của hàng rào, trên TOÀN BỘ các sổ, không soi chữ một tệp.
    """
    from tests.test_giu_cho_lan import _nguon, _doc_mot_tep

    dang = [d for t in _nguon() for d in _doc_mot_tep(t) if d["trang_thai"] == "đang làm"]
    for tep in ("backend/app/services/ops.py", "backend/app/api/v1/ops.py"):
        giu = sorted({d["lan"] for d in dang if tep in d["tep"]})
        assert giu in ([], ["TC-KT"]), f"{tep} vẫn bị các làn {giu} giữ chỗ"


# ───────────────────────────────────────────────────────────────────── LUẬT 6
def test_dontckt_6_hang_rao_hai_lan_mot_tep_XANH_lai():
    """PHÉP ĐO QUYẾT ĐỊNH: gọi thẳng hàng rào, không soi chữ.

    Hàng rào sẽ ĐỎ LẠI khi R4c-2 hoặc R4c-4 gộp vào trong lúc R2-KC1 (PR #578) còn giữ chỗ — đó
    là nó làm đúng việc, và cách xử là gộp #578 rồi đóng dòng ấy, KHÔNG phải sửa phép thử này.
    """
    from tests.test_giu_cho_lan import test_hai_lan_KHONG_duoc_cung_giu_mot_tep as hang_rao

    hang_rao()


# ───────────────────────────────────────────────────────────────────── LUẬT 7
def test_dontckt_7_so_cua_dot_o_lan_phan_quyen_va_khong_cho_nao_khac():
    """Sổ của đợt này ở làn «Phân quyền», không phải «TC-KT».

    Việc của đợt là quyển sổ `phan-quyen.md` — và chính tệp sổ ấy cũng là một tệp CÓ GIỮ CHỖ
    (SO-5 đang giữ). Khai nó ở làn TC-KT là tự tạo ra một chồng lấn GIỮA hai làn, đúng cái hàng
    rào vừa kêu. Đợt SO-DOT cho phép một làn vừa có tệp phẳng vừa có thư mục, nên sổ của đợt này
    là `docs/dang-lam/phan-quyen/DON-TCKT.md`.
    """
    from tests.test_giu_cho_lan import _nguon, _doc_mot_tep

    assert os.path.exists(TEP_DOT), "chưa tạo docs/dang-lam/phan-quyen/DON-TCKT.md"
    dong = _doc_mot_tep(TEP_DOT)
    assert len(dong) == 1, "tệp sổ của đợt phải có đúng một dòng"
    assert dong[0]["lan"] == "Phân quyền", f"dòng khai làn {dong[0]['lan']!r}"
    assert "docs/dang-lam/phan-quyen.md" in dong[0]["tep"], "dòng không khai tệp nó thật sự sửa"

    khac = [t for t in _nguon()
            if os.path.abspath(t) != os.path.abspath(TEP_DOT)
            and re.search(r"DON-TCKT(?!\w)", open(t, encoding="utf-8").read())]   # KS-19p: không bắt nhầm DON-TCKT2
    assert not khac, f"đợt này còn ghi vào {khac}"
