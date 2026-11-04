# -*- coding: utf-8 -*-
"""Đợt DỌN-PQ 04/11/2026 — ĐÓNG NHỮNG DÒNG GIỮ CHỖ ĐÃ GỘP MÀ SỔ «PHÂN QUYỀN» VẪN GIỮ.

Chủ tịch chốt 04/11/2026.

VÌ SAO ĐỢT NÀY SINH RA

`docs/dang-lam/phan-quyen.md` đang có **21 dòng «đang làm»**, dòng cũ nhất từ 28/10/2026. Đo ba
lớp dấu trên main ngày 04/11: **20 trong 21 dòng chứng minh được là đã gộp**. Hậu quả không phải
một quyển sổ xấu — ba tệp nóng bị giữ bởi những việc KHÔNG CÒN TỒN TẠI:

    services/ks_cua_nhap.py   TR-1 · DK-1b · DK-2b
    services/access.py        R7-SO · TR-1 · P2-1

nên bất kỳ làn nào cần chạm hai tệp ấy đều làm `test_hai_lan_KHONG_duoc_cung_giu_mot_tep` đỏ, và
đỏ vì một lý do sai. Một cái chuông kêu suốt là một cái chuông không ai nghe nữa — đó mới là chỗ
hỏng, chứ không phải dòng sổ thừa.

KHÔNG ĐOÁN DÒNG NÀO ÔI — ĐO. Đợt này KHÔNG chốt trước dòng nào sẽ đóng. Nó có một DANH SÁCH XÉT
(21 mã đã đo ngày 04/11) và một PHÉP ĐO; dòng nào đủ dấu trên main thì đóng, thiếu một lớp thì để
nguyên. Dòng nào KHÔNG nằm trong danh sách xét thì KHÔNG đụng tới — một dòng mới ai đó thêm vào
sau phép đo này phải được để yên, kể cả khi nó trông như đã gộp.

PHÉP ĐO BA LỚP — ba chỗ khác loại nên khó trùng:
    (1) tệp phép thử của đợt ấy có trên main
    (2) dấu mã của nó nằm trong TỪNG tệp mã mà dòng ấy khai
    (3) tệp di trú của nó có trên main (đợt nào không có di trú thì bỏ lớp này)

BA DÒNG CẦN PHÉP ĐO RIÊNG, VÀ ĐÂY LÀ PHẦN ĐÁNG ĐỌC NHẤT

Phép đo chung soi DẤU MÃ. Với ba dòng dưới đây nó trả lời SAI — không phải vì chúng chưa gộp, mà
vì thứ chúng sinh ra không mang mã đợt:

  · `DK-1b` và `DK-2b` thêm một TÊN BẢNG vào `ks_cua_nhap.CUA_TAY`. Một tên bảng không mang mã
    đợt, nên soi dấu `DK-1b` trong tệp ấy sẽ mãi mãi không thấy. Đo đúng thứ chúng sinh ra:
    `"don_dang_ky"` và `"may_da_nho"` có trong `CUA_TAY` hay chưa.
  · `DỌN-MISA` sửa `main.py` từ "nhập TÊN" sang "nhập MÔ-ĐUN" — một thay đổi không để lại dấu.
    Đo đúng thứ nó sinh ra: `tests/csdl_rieng.py` có trên main hay chưa.

Bài học ghi lại: một phép đo chung áp lên mọi dòng sẽ nói sai về những dòng mà sản phẩm của chúng
không mang tên chúng. Chỗ chữa KHÔNG phải nới phép đo cho dễ qua, mà khai riêng từng ngoại lệ KÈM
chỗ đo thay thế — có tên, có lý do, đọc lại được.

ĐỢT NÀY KHÔNG ĐỤNG MỘT TỆP MÃ NÀO. Chỉ ô cuối của những dòng đã chứng minh được.
"""
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(GOC, "docs", "dang-lam")
PQ = os.path.join(THU_MUC, "phan-quyen.md")
TEP_DOT = os.path.join(THU_MUC, "phan-quyen", "DON-PQ.md")

# DANH SÁCH XÉT — 21 mã đo được ngày 04/11/2026. KHÔNG phải danh sách "sẽ đóng": phép đo quyết
# định. Dòng nào không có tên ở đây thì đợt này không đụng tới, kể cả khi nó trông như đã gộp.
XET = ["SO-5", "PL-1", "KS-12", "KS-13", "KS-14", "SP-1", "KS-15", "KS-16", "KS-16b", "KS-16c",
       "KS-16f", "R7-SO", "R7-MCT", "R7-SOb", "DỌN-MISA", "TR-1", "TR-1b", "DK-1b", "P2-1",
       "DK-2", "DK-2b"]

# Ngoại lệ có TÊN và có LÝ DO: {mã: {đường dẫn tệp: chuỗi phải tìm thấy thay cho mã}}.
# Rỗng ("") nghĩa là CHỈ cần tệp có thật, không soi chữ.
DO_RIENG = {
    "DK-1b":    {"backend/app/services/ks_cua_nhap.py": '"don_dang_ky"'},
    "DK-2b":    {"backend/app/services/ks_cua_nhap.py": '"may_da_nho"'},
    "DỌN-MISA": {"backend/app/main.py": ""},
}

DANG_LAM = "đang làm"


def _bang():
    """{mã: (số dòng, các ô)} cho mọi dòng của bảng trong phan-quyen.md."""
    ra = {}
    for i, d in enumerate(open(PQ, encoding="utf-8").read().splitlines(), 1):
        t = d.strip()
        if not t.startswith("|"):
            continue
        o = [x.strip() for x in t.strip("|").split("|")]
        if len(o) != 5:
            continue
        ma = o[1].split("—")[0].replace("*", "").strip()
        if ma in XET:
            assert ma not in ra, f"{ma}: tìm thấy hai dòng mang mã này"
            ra[ma] = (i, o)
    return ra


def _thieu(ma, tep_str):
    """Những lớp dấu CÒN THIẾU của mã này trên main. Rỗng = đã gộp, chứng minh được."""
    rieng = DO_RIENG.get(ma, {})
    thieu = []
    for p in [x.strip() for x in tep_str.split(",") if x.strip()]:
        if p.startswith("docs/"):
            continue                       # mã luôn có trong sổ, không chứng minh được gì
        if "*" in p:                       # di trú khai bằng mẫu *
            import glob
            if not glob.glob(os.path.join(GOC, *p.split("/"))):
                thieu.append("tệp di trú " + os.path.basename(p))
            continue
        duong = os.path.join(GOC, *p.split("/"))
        if not os.path.exists(duong):
            thieu.append("tệp " + p)
            continue
        if p in rieng:
            can = rieng[p]
            if can and can not in open(duong, encoding="utf-8", errors="replace").read():
                thieu.append(f"dấu thay thế {can} trong {p}")
            continue
        if p.startswith("backend/tests/") or p.startswith("web/"):
            continue                       # lớp (1): có tệp là đủ
        if ma not in open(duong, encoding="utf-8", errors="replace").read():
            thieu.append("dấu trong " + p)
    return thieu


# ───────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_donpq_1_du_dau_thi_phai_la_xong():
    """Dòng nào chứng minh được là đã gộp thì KHÔNG được giữ chỗ nữa.

    Một dòng ôi giữ một tệp là một làn khác không viết được vào tệp ấy, và hàng rào đỏ vì một
    việc KHÔNG CÒN TỒN TẠI. Đó là cái giá của việc không ai dọn sổ — và ở đây nó đã lên tới ba
    tệp nóng và hai mươi dòng.
    """
    for ma, (dong, o) in _bang().items():
        if o[4].lower() != DANG_LAM or _thieu(ma, o[2]):
            continue
        raise AssertionError(
            f"{ma} (dòng {dong}): đủ dấu trên main mà trạng thái vẫn là {o[4]!r}")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_donpq_2_thieu_mot_lop_thi_KHONG_duoc_dong():
    """Chiều ngược, và đây là chiều nguy hơn.

    Đóng một dòng mà không chứng minh được là mở đường cho hai làn viết đè lên nhau mà hàng rào
    im lặng — đúng cái việc đợt này sinh ra để chống. Thiếu một lớp là chưa chứng minh được.
    """
    for ma, (dong, o) in _bang().items():
        thieu = _thieu(ma, o[2])
        if not thieu:
            continue
        assert o[4].lower() == DANG_LAM, (
            f"{ma} (dòng {dong}) đã bị đổi sang {o[4]!r} nhưng trên main còn thiếu: {thieu}. "
            f"Nếu nó gộp thật thì phải thấy đủ dấu; không thấy thì không được đóng.")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_donpq_3_it_nhat_hai_muoi_dong_da_dong():
    """Đo được 04/11/2026: 20 trong 21 dòng đủ dấu. Đợt này ít nhất phải đóng hai mươi dòng ấy.

    Không có luật này thì một bản vá hỏng mà không vá được gì vẫn xanh, và cả đợt thành vô ích
    một cách im lặng.
    """
    xong = [ma for ma, (_, o) in _bang().items() if o[4].lower() == "xong"]
    assert len(xong) >= 20, f"mới đóng {len(xong)} dòng, cần ít nhất 20: {sorted(xong)}"


# ───────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_donpq_4_khong_doi_mot_chu_nao_ngoai_o_trang_thai():
    """Chỉ ô cuối đổi. Sửa luôn mã việc của người khác là viết lại lịch sử của họ."""
    for ma, (dong, o) in _bang().items():
        assert len(o) == 5, f"{ma} (dòng {dong}): không còn năm cột"
        assert o[0] == "Phân quyền", f"{ma}: cột Làn đã bị đổi thành {o[0]!r}"
        assert o[1].startswith("**" + ma), f"{ma}: mã việc đã bị sửa"
        assert re.fullmatch(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}", o[3]), f"{ma}: giờ bắt đầu đã bị sửa"
        assert o[2].strip(), f"{ma}: danh sách tệp đã bị xóa"


# ───────────────────────────────────────────────────────────────────────────── LUẬT 5
def test_donpq_5_hai_tep_nong_khong_con_lan_nao_giu():
    """ĐỢT NÀY ĐỂ LÀM GÌ: nhả `ks_cua_nhap.py` và `access.py`.

    Đo bằng chính bộ đọc của hàng rào, trên TOÀN BỘ các sổ, không soi chữ một tệp.
    """
    from tests.test_giu_cho_lan import _nguon, _doc_mot_tep

    dang = [d for t in _nguon() for d in _doc_mot_tep(t) if d["trang_thai"] == DANG_LAM]
    for tep in ("backend/app/services/ks_cua_nhap.py", "backend/app/services/access.py"):
        giu = sorted({d["lan"] for d in dang if tep in d["tep"]})
        assert giu in ([], ["Phân quyền"], ["TC-KT"]), f"{tep} vẫn bị các làn {giu} giữ chỗ"


# ───────────────────────────────────────────────────────────────────────────── LUẬT 6
def test_donpq_6_hang_rao_hai_lan_mot_tep_XANH_lai():
    """PHÉP ĐO QUYẾT ĐỊNH: gọi thẳng hàng rào, không soi chữ.

    Hàng rào sẽ ĐỎ LẠI khi một làn khác mở một dòng mới chạm tệp mà làn «Phân quyền» còn giữ —
    đó là nó làm đúng việc, và cách xử là hai làn nói chuyện, KHÔNG phải sửa phép thử này.
    """
    from tests.test_giu_cho_lan import test_hai_lan_KHONG_duoc_cung_giu_mot_tep as hang_rao

    hang_rao()


# ───────────────────────────────────────────────────────────────────────────── LUẬT 7
def test_donpq_7_so_cua_dot_o_lan_phan_quyen_va_khong_cho_nao_khac():
    """Sổ của đợt này ở làn «Phân quyền», không phải một làn khác.

    Việc của đợt là quyển sổ `phan-quyen.md` — và chính tệp sổ ấy cũng là một tệp CÓ GIỮ CHỖ
    (SO-5 đang giữ, và SO-5 là một trong những dòng đợt này đóng). Khai nó ở làn khác là tự tạo
    ra một chồng lấn GIỮA hai làn, đúng cái hàng rào vừa kêu. Đợt SO-DOT cho phép một làn vừa có
    tệp phẳng vừa có thư mục, nên sổ của đợt này là `docs/dang-lam/phan-quyen/DON-PQ.md`.
    """
    from tests.test_giu_cho_lan import _nguon, _doc_mot_tep

    assert os.path.exists(TEP_DOT), "chưa tạo docs/dang-lam/phan-quyen/DON-PQ.md"
    dong = _doc_mot_tep(TEP_DOT)
    assert len(dong) == 1, "tệp sổ của đợt phải có đúng một dòng"
    assert dong[0]["lan"] == "Phân quyền", f"dòng khai làn {dong[0]['lan']!r}"
    assert "docs/dang-lam/phan-quyen.md" in dong[0]["tep"], "dòng không khai tệp nó thật sự sửa"

    khac = [t for t in _nguon()
            if os.path.abspath(t) != os.path.abspath(TEP_DOT)
            and "DON-PQ" in open(t, encoding="utf-8").read()]
    assert not khac, f"đợt này còn ghi vào {khac}"


# ───────────────────────────────────────────────────────────────────────────── LUẬT 8
def test_donpq_8_khong_dung_mot_tep_ma_nao():
    """Đợt dọn sổ chỉ được đụng sổ. Dòng sổ của chính nó phải nói đúng điều ấy."""
    from tests.test_giu_cho_lan import _doc_mot_tep

    tep = _doc_mot_tep(TEP_DOT)[0]["tep"]
    la = [t for t in tep if not (t.startswith("docs/") or t.startswith("backend/tests/"))]
    assert not la, f"đợt dọn sổ mà khai đụng tệp mã: {la}"
