# -*- coding: utf-8 -*-
"""Đợt DỌN-TCKT2 05/11/2026 — ĐÓNG SÁU DÒNG GIỮ CHỖ ĐÃ GỘP CỦA LÀN TC-KT.

Đo trên main 05/11/2026: `docs/dang-lam/tc-kt/` có sáu tệp và cả sáu còn `đang làm`. Các làn khác
có bước tự đóng sổ (commit «Đóng sổ: … đã gộp»), nhưng không có commit nào như thế cho một nhánh
`tckt-*` nào — nên làn này tích dòng treo.

HỆ QUẢ CỤ THỂ, KHÔNG PHẢI LO XA: R4c-4 gộp từ 02/11 mà vẫn giữ `accounting.py`, `finance.py`,
`payments.py` và `web/app/collections/page.tsx` — bốn tệp nóng nhất của làn. Đúng kiểu dòng treo
đã chặn Đợt QUY-2a hôm qua, khi DỌN-R4c3 (đã gộp) còn giữ `test_le2b_ba_vai_ke_toan.py`.

HAI CHIỀU SAI CỦA MỘT PHÉP DỌN, VÀ CẢ HAI ĐỀU ĐƯỢC CANH Ở ĐÂY:

  1. Đóng NHẦM một đợt đang làm thật → luật 2 đòi mỗi đợt đã đóng phải có đủ hai dấu trên main.
  2. BỎ SÓT một dòng → luật 1 quét cả thư mục chứ không đọc một danh sách chép tay.

Chiều thứ hai là bài học Đợt DỌN-PQ: bản ấy chỉ đọc tệp sổ phẳng cũ trong khi Đợt SO-DOT đã dời
các dòng sang `docs/dang-lam/<làn>/`, nên nó báo "đã dọn xong" về một nửa sự thật — và KHÔNG phép
thử nào đỏ, vì một phép đo bỏ sót nguồn thì nói ÍT hơn sự thật chứ không nói sai.
"""
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_dontckt2.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(GOC, "docs", "dang-lam", "tc-kt")
DOT_NAY = "DỌN-TCKT2"

# Hai dấu cho mỗi đợt: tệp phép thử riêng của nó, và một dấu đặc trưng trong tệp nguồn nó khai.
# Dấu rỗng nghĩa là "chỉ cần tệp tồn tại".
BANG_CHUNG = {
    "QUY-1": [("backend/tests/test_quy1_so_quy_tien_mat.py", ""),
              ("backend/app/models/payments.py", "class PhieuQuy(Base):")],
    "QUY-2a": [("backend/tests/test_quy2_cua_tai_lo_so_quy.py", ""),
               ("backend/app/services/intake_so_quy.py", "")],
    "QUY-2b": [("backend/tests/test_quy2b_man_so_quy.py", ""),
               ("web/app/collections/page.tsx", "const VAI_SO_QUY")],
    "QUY-3": [("backend/tests/test_quy3_so_du_quy.py", ""),
              ("backend/app/services/books.py", "def so_du_tien(")],
    "R4c-2": [("backend/tests/test_r4c2_o_hinh_thuc_tt.py", ""),
              ("backend/app/services/ket_so.py", "R4c-2")],
    "R4c-4": [("backend/tests/test_r4c4_ve_tien_cap_chi_tiet.py", ""),
              ("backend/app/services/finance.py", "TK_TIEN_GUI_CT")],
    "SO-DOT": [("backend/tests/test_sodot_moi_dot_mot_tep.py", ""),
               ("backend/tests/test_giu_cho_nhanh.py", "def test_gn11b")],
}


def _dong_bang():
    """Mọi dòng bảng trong MỌI tệp sổ của làn TC-KT. Quét thư mục, không chép danh sách."""
    out = []
    assert os.path.isdir(THU_MUC), "khong thay docs/dang-lam/tc-kt/"
    for ten in sorted(os.listdir(THU_MUC)):
        if not ten.endswith(".md"):
            continue
        for i, d in enumerate(open(os.path.join(THU_MUC, ten), encoding="utf-8").read().split("\n"), 1):
            if not d.startswith("|") or "---|" in d or "| Làn |" in d:
                continue
            c = [x.strip() for x in d.split("|")]
            if len(c) < 7:
                continue
            out.append({"tep": ten, "dong": i, "lan": c[1], "mo_ta": c[2],
                        "tep_giu": [t.strip() for t in c[3].split(",") if t.strip()],
                        "trang_thai": c[5]})
    return out


def _ma_cua(mo_ta: str) -> str:
    m = re.search(r"\*\*([^\s—]+)", mo_ta)
    return m.group(1).strip() if m else ""


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_dontckt2_1_khong_con_dong_treo_nao_trong_lan_TC_KT():
    """Quét CẢ thư mục, không đọc một danh sách chép tay.

    Một phép dọn đọc danh sách chép tay chỉ dọn được những gì người viết nghĩ ra lúc viết; thêm
    một tệp sổ sau đó là nó im lặng bỏ qua. Đó đúng là cách Đợt DỌN-PQ nói sai về một nửa sự
    thật mà không phép thử nào đỏ.
    """
    # KS-19p (06/11/2026): chỉ xét các mã ĐỢT NÀY dọn (BANG_CHUNG). Đợt TC-KT mở SAU ngày dọn (TKC-1 đang làm thật)
    # không phải dòng treo — đếm cả chúng thì phép thử đỏ mỗi lần làn ấy mở việc mới, đúng chuyện đã gặp ở
    # LANTCKT («≥16 đang làm») và DỌN-PQ2 luật 4, sửa cùng cách.
    treo = [d for d in _dong_bang()
            if d["trang_thai"].startswith("đang làm") and DOT_NAY not in d["mo_ta"] and _ma_cua(d["mo_ta"]) in BANG_CHUNG]
    assert not treo, (
        "làn TC-KT còn dòng giữ chỗ chưa đóng:\n" +
        "\n".join(f"   {d['tep']} dòng {d['dong']}: {_ma_cua(d['mo_ta']) or d['mo_ta'][:60]}"
                  for d in treo) +
        "\n\nNếu đợt ấy ĐÃ gộp thì đổi dòng sang `xong`; nếu chưa thì để nguyên và nói ra ở đây.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_dontckt2_2_moi_dot_da_dong_THAT_SU_co_tren_main():
    """Đóng nhầm một đợt đang làm thật thì tệp của nó thành không ai giữ — và đợt sau ghi đè lên.

    Đo LẠI, độc lập với bản vá: mỗi đợt đã đóng phải có đủ hai dấu trên main — tệp phép thử riêng
    của nó, và một dấu đặc trưng trong tệp nguồn nó khai. Luật này cố ý lặp lại việc bản vá đã
    làm: bản vá có thể sai, còn phép thử thì chạy trên cây mã thật sau khi vá.
    """
    for ma, dau in BANG_CHUNG.items():
        thieu = []
        for duong, chuoi in dau:
            p = os.path.join(GOC, *duong.split("/"))
            if not os.path.exists(p):
                thieu.append(f"{duong} (không có tệp)")
            elif chuoi and chuoi not in open(p, encoding="utf-8").read():
                thieu.append(f"{duong} (không mang dấu `{chuoi}`)")
        assert not thieu, (
            f"đợt {ma} đã bị đóng sổ nhưng trên main còn thiếu {thieu} — nghĩa là nó có thể ĐANG "
            "LÀM thật, và đóng dòng của nó là thả tệp cho đợt khác ghi đè lên")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_dontckt2_3_khong_bo_sot_mot_ma_nao_ngoai_bang_bang_chung():
    """Mọi mã đã đóng trong làn phải nằm trong bảng bằng chứng, và ngược lại.

    Nếu một mã mới xuất hiện mà bảng không biết, luật 2 sẽ không đo nó — và lúc ấy nó được đóng
    mà KHÔNG ai kiểm. Luật này bắt hai bên khớp nhau, nên quên cập nhật bảng là đỏ.
    """
    co = {_ma_cua(d["mo_ta"]) for d in _dong_bang() if DOT_NAY not in d["mo_ta"]}
    co.discard("")
    # KS-19p (06/11/2026): chiều «mã có trong sổ mà không có trong bảng» bỏ đi — mã của các đợt mở SAU ngày dọn
    # (DS-3, TKS-1, TZ-1, TKC-1…) không thuộc đợt này, mỗi đợt có phép thử riêng của nó. Chiều ngược lại giữ nguyên.
    thieu = sorted(set(BANG_CHUNG) - co)
    assert not thieu, (
        f"bảng bằng chứng nhắc những mã KHÔNG còn trong sổ TC-KT: {thieu} — bảng đang nói về một "
        "ảnh cũ của thư mục")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_dontckt2_4_hai_lan_khong_cung_giu_mot_tep():
    """Đo bằng CHÍNH bộ đọc của hàng rào, trên MỌI nguồn sổ — không tự dựng một bộ đọc thứ hai.

    Đây là bài học Đợt DỌN-PQ2: một phép dọn tự đọc lấy sổ thì nó chỉ thấy những nguồn nó biết,
    và nói "sạch rồi" về phần nó nhìn thấy. Gọi `_nguon()` của `test_giu_cho_lan` nghĩa là luật
    này thấy đúng những gì hàng rào thấy — không hơn, không kém.
    """
    from test_giu_cho_lan import _doc_mot_tep, _nguon
    giu, dung_do = {}, []
    for nguon in _nguon():
        for d in _doc_mot_tep(nguon):
            if not str(d.get("trang_thai", "")).startswith("đang làm"):
                continue
            for t in d.get("tep", []):
                cu = giu.get(t)
                if cu is not None and cu["lan"] != d["lan"]:
                    dung_do.append(f"   {t}\n      {cu['lan']}\n      {d['lan']}")
                giu.setdefault(t, d)
    assert not dung_do, "HAI LÀN ĐANG GIỮ CÙNG MỘT TỆP:\n" + "\n".join(dung_do)
