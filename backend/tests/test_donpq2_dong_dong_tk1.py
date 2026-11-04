# -*- coding: utf-8 -*-
"""Đợt DỌN-PQ2 04/11/2026 — ĐÓNG DÒNG TK-1, CHỖ LỦNG MÀ ĐỢT DỌN-PQ BỎ SÓT.

LỖI CỦA ĐỢT TRƯỚC, GHI RA ĐÂY VÌ NÓ LÀ CÁI ĐÁNG HỌC

Đợt DỌN-PQ đo 21 dòng và đóng 20. Nó đọc **đúng một tệp**: `docs/dang-lam/phan-quyen.md`. Nhưng
từ Đợt SO-DOT (02/11), mỗi đợt CÓ THỂ có **tệp sổ riêng** trong `docs/dang-lam/<làn>/` — và làn
«Phân quyền» đang có hơn 20 tệp như thế. Phép đo bỏ sót toàn bộ chúng.

Chỗ lủng lộ ra ngay sau đó: `test_hai_lan_KHONG_duoc_cung_giu_mot_tep` vẫn ĐỎ, và nó chỉ ra
`TK-1` (mở 04/11 00:15, sổ riêng `phan-quyen/TK-1.md`) đang giữ `services/ks_cua_nhap.py` cùng
với Đợt QUY-1 — và sau khi đóng TK-1 thì **luật 4 của chính đợt này lại đỏ**, chỉ thêm `TK-1e`
và `TK-2` cũng giữ tệp ấy. Ba dòng, một lỗ đo.

BÀI HỌC: một phép đo đọc "quyển sổ" phải đọc ĐỦ MỌI NGUỒN của quyển sổ ấy. Đợt SO-DOT đổi hình
dạng của sổ từ MỘT tệp thành MỘT tệp + MỘT THƯ MỤC, và phép đo viết sau đó vẫn đọc theo hình
dạng cũ. Không phép thử nào bắt được, vì một phép đo bỏ sót thì nó chỉ NÓI ÍT HƠN sự thật chứ
không nói SAI — và nói ít hơn sự thật thì không có gì để đỏ. **Hàng rào bắt được.** Đó là lý do
hàng rào tồn tại, và là lý do không được sửa nó cho hết đỏ.

LUẬT 4 CỦA ĐỢT NÀY LÀ BẢN VÁ CHO CHÍNH CÁI LỖI ẤY: nó đọc đủ mọi nguồn sổ của làn «Phân quyền»
và đòi KHÔNG CÒN dòng ôi nào giữ hai tệp nóng — nên lần sau ai dọn sổ mà vẫn đọc một tệp thì
luật này đỏ chứ không im.

ĐỢT NÀY HẸP: chỉ xét **ba dòng cùng giữ `ks_cua_nhap.py`** — TK-1, TK-1e, TK-2 — vì đó đúng là
chỗ đang chặn Đợt QUY-1. Thư mục sổ của làn «Phân quyền» còn **14 dòng «đang làm» khác** CHƯA AI
ĐO; món nợ có tên, ghi ở «còn tồn», không làm im lặng ở đây.
"""
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(GOC, "docs", "dang-lam")
PQ_DIR = os.path.join(THU_MUC, "phan-quyen")
TEP_DOT = os.path.join(PQ_DIR, "DON-PQ2.md")

# Ba dòng cùng giữ `services/ks_cua_nhap.py`, cùng chặn Đợt QUY-1, cùng đo được là đã gộp ngày
# 04/11/2026. Mỗi dòng nằm trong TỆP SỔ RIÊNG của nó — đúng chỗ Đợt DỌN-PQ không đọc tới.
XET = {"TK-1": "TK-1.md", "TK-1e": "TK-1e.md", "TK-2": "TK-2.md"}

# NGOẠI LỆ THỨ BA CỦA CÙNG MỘT HỌ LỖI, khai kèm lý do: {mã: {tệp: chuỗi thay cho mã}}.
# Rỗng ("") nghĩa là CHỈ cần tệp có thật.
#
# Dòng TK-2 khai `tk1e7b9d1f3a5c8e02_ngay_le_tet.py` — tệp di trú CỦA TK-1e — vì di trú của TK-2
# nối SAU nó. Một tệp mình chỉ NỐI VÀO thì không mang dấu của mình, nên soi dấu `TK-2` ở đó sẽ
# mãi mãi không thấy. Bài học lặp lần thứ ba (sau DK-1b/DK-2b và DỌN-MISA): phép đo chung nói
# sai về mọi tệp mà đợt KHAI nhưng không STAMP — tệp nó phụ thuộc, tệp nó nối vào, tệp nó chỉ
# thêm một tên bảng. Chỗ chữa không phải nới phép đo mà khai riêng, có tên, có lý do.
DO_RIENG = {
    "TK-2": {"backend/alembic/versions/tk1e7b9d1f3a5c8e02_ngay_le_tet.py": ""},
}



def _dong(ma):
    """Dòng mang mã này trong tệp sổ riêng của nó — đúng một dòng, không thì đỏ."""
    tep = os.path.join(PQ_DIR, XET[ma])
    ds = [d for d in open(tep, encoding="utf-8").read().splitlines()
          if d.strip().startswith("|") and ("**" + ma + " —") in d]
    assert len(ds) == 1, f"{XET[ma]}: tìm thấy {len(ds)} dòng mang mã {ma}, cần đúng 1"
    return [x.strip() for x in ds[0].strip().strip("|").split("|")]


def _thieu(ma):
    """Những lớp dấu CÒN THIẾU của mã này trên main. Rỗng = đã gộp, chứng minh được.

    Đọc danh sách tệp TỪ CHÍNH DÒNG SỔ chứ không gõ cứng: dòng sổ là thứ khai ra đợt ấy đụng
    những gì, nên nếu ai sửa dòng thì phép đo đi theo chứ không nói về một bản chụp cũ.
    """
    import glob as _glob
    rieng = DO_RIENG.get(ma, {})
    thieu = []
    for p in [x.strip() for x in _dong(ma)[2].split(",") if x.strip()]:
        if p in rieng:
            duong = os.path.join(GOC, *p.split("/"))
            if not os.path.exists(duong):
                thieu.append("tệp " + p)
            elif rieng[p] and rieng[p] not in open(duong, encoding="utf-8", errors="replace").read():
                thieu.append("dấu thay thế " + rieng[p] + " trong " + p)
            continue
        if p.startswith("docs/"):
            continue                       # mã luôn có trong sổ, không chứng minh được gì
        if "*" in p:
            if not _glob.glob(os.path.join(GOC, *p.split("/"))):
                thieu.append("tệp di trú " + os.path.basename(p))
            continue
        duong = os.path.join(GOC, *p.split("/"))
        if not os.path.exists(duong):
            thieu.append("tệp " + p)
            continue
        if p.startswith("backend/tests/") or p.startswith("web/"):
            continue                       # lớp (1): có tệp là đủ
        if ma not in open(duong, encoding="utf-8", errors="replace").read():
            thieu.append("dấu trong " + p)
    return thieu


# ───────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_donpq2_1_du_dau_thi_phai_la_xong():
    """Dòng nào chứng minh được là đã gộp thì KHÔNG được giữ chỗ nữa."""
    for ma in XET:
        if _thieu(ma):
            continue
        o = _dong(ma)
        assert o[4].lower() == "xong", (
            f"{ma} đủ ba lớp dấu trên main mà trạng thái vẫn là {o[4]!r}")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_donpq2_2_thieu_mot_lop_thi_KHONG_duoc_dong():
    """Chiều ngược, và đây là chiều nguy hơn: chưa chứng minh được thì không được đóng."""
    for ma in XET:
        thieu = _thieu(ma)
        if not thieu:
            continue
        o = _dong(ma)
        assert o[4].lower() == "đang làm", (
            f"{ma} đã bị đổi sang {o[4]!r} nhưng trên main còn thiếu: {thieu}")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_donpq2_3_khong_doi_mot_chu_nao_ngoai_o_trang_thai():
    """Chỉ ô cuối đổi. Sửa luôn mã việc của người khác là viết lại lịch sử của họ."""
    for ma in XET:
        o = _dong(ma)
        assert len(o) == 5, f"dòng {ma} không còn năm cột"
        assert o[0] == "Phân quyền", f"{ma}: cột Làn đã bị đổi thành {o[0]!r}"
        assert o[1].startswith("**" + ma + " —"), f"{ma}: mã việc đã bị sửa"
        assert re.fullmatch(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}", o[3]), f"{ma}: giờ bắt đầu bị sửa"
        assert "backend/app/services/ks_cua_nhap.py" in o[2], f"{ma}: danh sách tệp đã bị sửa"


# ───────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_donpq2_4_doc_DU_MOI_NGUON_SO_chu_khong_mot_tep():
    """BẢN VÁ CHO CHÍNH LỖI SINH RA ĐỢT NÀY.

    Đọc đủ mọi nguồn sổ của làn «Phân quyền» — tệp phẳng VÀ thư mục của làn — rồi đòi hai tệp
    nóng không còn dòng «đang làm» nào của làn ấy giữ. Một phép đo chỉ đọc tệp phẳng sẽ bỏ sót,
    và bỏ sót thì không có gì đỏ; luật này làm cho chỗ bỏ sót ấy ĐỎ.

    Đo bằng chính bộ đọc của hàng rào (`_nguon`), không tự liệt kê tệp — nếu mai kia sổ đổi hình
    dạng lần nữa thì luật này đi theo, chứ không đứng lại ở hình dạng hôm nay.
    """
    from tests.test_giu_cho_lan import _nguon, _doc_mot_tep

    dang = [d for t in _nguon() for d in _doc_mot_tep(t) if d["trang_thai"] == "đang làm"]
    for tep in ("backend/app/services/ks_cua_nhap.py", "backend/app/services/access.py"):
        giu = sorted({d["lan"] for d in dang if tep in d["tep"]})
        assert "Phân quyền" not in giu, (
            f"{tep} vẫn bị làn «Phân quyền» giữ chỗ — còn dòng nào đó chưa ai đo, "
            f"nhiều phần nằm trong một tệp sổ riêng. Các làn đang giữ: {giu}")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 5
def test_donpq2_5_hang_rao_hai_lan_mot_tep_XANH_lai():
    """PHÉP ĐO QUYẾT ĐỊNH: gọi thẳng hàng rào, không soi chữ."""
    from tests.test_giu_cho_lan import test_hai_lan_KHONG_duoc_cung_giu_mot_tep as hang_rao

    hang_rao()


# ───────────────────────────────────────────────────────────────────────────── LUẬT 6
def test_donpq2_6_so_cua_dot_o_lan_phan_quyen_va_khong_dung_tep_ma_nao():
    """Sổ của đợt ở làn «Phân quyền» — việc của nó là một tệp sổ của làn ấy. Và đợt dọn sổ chỉ
    được đụng sổ."""
    from tests.test_giu_cho_lan import _nguon, _doc_mot_tep

    assert os.path.exists(TEP_DOT), "chưa tạo docs/dang-lam/phan-quyen/DON-PQ2.md"
    dong = _doc_mot_tep(TEP_DOT)
    assert len(dong) == 1, "tệp sổ của đợt phải có đúng một dòng"
    assert dong[0]["lan"] == "Phân quyền", f"dòng khai làn {dong[0]['lan']!r}"
    for ma in XET:
        assert "docs/dang-lam/phan-quyen/" + XET[ma] in dong[0]["tep"], (
            f"dòng sổ của đợt không khai {XET[ma]} — tệp nó thật sự sửa")
    la = [t for t in dong[0]["tep"]
          if not (t.startswith("docs/") or t.startswith("backend/tests/"))]
    assert not la, f"đợt dọn sổ mà khai đụng tệp mã: {la}"

    khac = [t for t in _nguon()
            if os.path.abspath(t) != os.path.abspath(TEP_DOT)
            and "DON-PQ2" in open(t, encoding="utf-8").read()]
    assert not khac, f"đợt này còn ghi vào {khac}"
