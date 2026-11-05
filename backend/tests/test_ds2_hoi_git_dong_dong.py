# -*- coding: utf-8 -*-
"""Đợt DS-2 05/11/2026 — HỎI GIT, ĐÓNG MỌI DÒNG ĐÃ GỘP.

Bước một của hai; bước hai là treo chuông ba ngày. Chủ tịch chốt 05/11/2026: dọn trước, treo
chuông sau — đo được chín dòng đã quá ba ngày, và treo chuông chặn ngay sẽ làm main đỏ lập tức,
chặn cả những làn đang chạy việc khác.

NGUYÊN TẮC LÀ CỦA ĐỢT ĐS-1 (Chủ tịch duyệt 28/10/2026): **hỏi git, không gõ tay danh sách**. Mã ở
đầu mô tả khớp mã ở đầu tiêu đề commit trên main thì làn ấy đã gộp.

HAI LUẬT DƯỚI ĐÂY LÀ HAI LUẬT CÒN LẠI CỦA ĐS-1, và chúng là điều kiện để cái chuông có nghĩa:

  - Mỗi dòng phải đọc được MÃ VIỆC. Không có mã thì không bao giờ đóng tự động được — dòng ấy
    sống mãi và giữ tệp mãi, và cái chuông sẽ kêu về nó đến hết đời.
  - Mỗi dòng phải đọc được NGÀY BẮT ĐẦU. Một cái chuông có lỗ thủng thì không phải cái chuông:
    dòng không ngày là dòng chuông không bao giờ nhìn thấy.

LUẬT 1 ĐO BẰNG GIT và sẽ TỰ BỎ QUA nếu lịch sử git bị cắt nông — nói rõ lý do chứ không lặng lẽ
xanh. Lý do: máy chạy việc gộp thường lấy mã với `fetch-depth: 1`, lúc ấy mọi câu trả lời đều là
"chưa gộp", và đó là câu trả lời sai nguy hiểm nhất. Bản vá thì chạy trên máy có lịch sử đầy đủ.
"""
import os
import re
import subprocess
import sys

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_ds2.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOT_NAY = "DS-2"
TOI_THIEU = 50          # dưới ngần này tiêu đề commit thì KHÔNG kết luận — luật của ĐS-1


def _dong():
    """Mọi dòng bảng của MỌI quyển sổ, đọc bằng CHÍNH bộ đọc của hàng rào.

    `_doc_bang()` là thứ cả hai hàng rào đứng lên, nên luật ở đây thấy đúng những gì chúng thấy —
    không hơn, không kém. Khoá của mỗi dòng: `lan`, `ma_viec`, `tep`, `bat_dau`, `trang_thai`,
    `nguon`, `so_dong` (đo trên main 05/11/2026).
    """
    from test_giu_cho_lan import _doc_bang
    return _doc_bang()


def _ma(s):
    """Mã việc ở đầu ô mô tả. KHÔNG đòi phải có `**`.

    ĐÂY LÀ LỖI ĐỢT ĐS-1 ĐÃ MẮC RỒI VÀ ĐÃ SỬA (ghi trong hồ sơ 28/10/2026): bản đầu của nó đòi mã
    phải bọc `**`, nên nó coi bốn dòng hợp lệ — `D4-1`, `HQ-4/HQ-5`, `KS-18 (đẩy lại 23-10-2026)`
    — là dòng hỏng. Bản vá này mắc lại y hệt ở vòng chạy đầu 05/11/2026 và dừng ở ba dòng ấy.

    Nên: bỏ `*` ở đầu rồi lấy cụm chữ đầu tiên, cắt ở khoảng trắng, gạch dài hoặc ngoặc. Và cụm ấy
    phải TRÔNG NHƯ một mã — có chữ số hoặc dấu gạch, dài không quá 24 — để một mô tả mở đầu bằng
    chữ thường không lặng lẽ biến thành "mã" rồi lọt qua phép đo.
    """
    m = re.match(r"\s*\**\s*([^\s—\(|*]+)", str(s or ""))
    if not m:
        return ""
    ma = m.group(1).strip().rstrip(":,.")
    if len(ma) > 24 or not re.search(r"[-\d]", ma):
        return ""
    return ma


def _tieu_de_commit():
    """Tiêu đề commit của main. Rỗng nghĩa là KHÔNG đọc được — người gọi phải tự bỏ qua."""
    for lenh in (["git", "log", "origin/main", "--pretty=format:%s"],
                 ["git", "log", "--pretty=format:%s"]):
        try:
            # `encoding="utf-8", errors="replace"`: tren Windows, Python giai ma dau ra cua
            # git bang cp1252 va tieu de commit tieng Viet lam luong doc chet. Do duoc 05/11/2026.
            r = subprocess.run(lenh, cwd=GOC, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=60)
        except Exception:
            continue
        if r.returncode == 0 and r.stdout.strip():
            dong = [x.strip() for x in r.stdout.split("\n") if x.strip()]
            if len(dong) >= TOI_THIEU:
                return dong
    return []


def _bo_dau(s):
    """Bo dau tieng Viet de so ma. `DỌN-PQ` trong so va `DON-PQ:` trong tieu de commit la MOT.

    Do duoc luc chay that 05/11/2026: bon dong DỌN-* bi de nguyen chi vi so viet co dau con nguoi
    viet commit go khong dau. Bat hai ben phai giong nhau den tung dau la bat con nguoi nho mot
    quy uoc ma khong gi nhac — va luc quen thi dong treo lai, lang le.
    """
    import unicodedata
    s = str(s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def _da_gop(ma: str, tieu_de) -> bool:
    """Mã khớp đầu tiêu đề commit, CÓ DẤU HAI CHẤM — nên `TK-1` không nuốt `TK-1b` — và SO KHÔNG DẤU."""
    mau = re.compile(r"^(?:Dot |Dot |Dơt )?" + re.escape(_bo_dau(ma)) + r"\s*:", re.I)
    return any(mau.match(_bo_dau(t)) for t in tieu_de)


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_ds2_1_khong_con_dong_dang_lam_nao_da_gop_roi():
    """Dòng của một đợt ĐÃ GỘP mà vẫn `đang làm` là một dòng treo: nó giữ tệp mà không ai làm.

    Đúng thứ đã chặn Đợt QUY-2a hôm 04/11, khi DỌN-R4c3 (đã gộp) còn giữ `test_le2b`.
    """
    td = _tieu_de_commit()
    if not td:
        pytest.skip(
            f"khong doc duoc it nhat {TOI_THIEU} tieu de commit — lich su git o day bi cat nong "
            "(may chay viec gop thuong lay ma voi fetch-depth: 1). KHONG ket luan, vi luc do moi "
            "cau tra loi deu la 'chua gop' va do la cau tra loi sai nguy hiem nhat.")
    treo = [d for d in _dong()
            if str(d.get("trang_thai", "")).startswith("đang làm")
            and _ma(d["ma_viec"])
            and _ma(d["ma_viec"]) != DOT_NAY
            and _da_gop(_ma(d["ma_viec"]), td)]
    assert not treo, (
        "những dòng này ĐÃ GỘP vào main mà sổ vẫn ghi `đang làm` — chúng đang giữ tệp của mình "
        "cho một việc không còn ai làm:\n" +
        "\n".join("   " + _ma(d["ma_viec"]) + "  (làn " +
                  str(d.get("lan")) + ")" for d in treo))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_ds2_2_moi_dong_doc_duoc_MA_VIEC():
    """Luật của ĐS-1. Không có mã thì không bao giờ đóng tự động được — dòng ấy sống mãi và giữ
    tệp mãi, và cái chuông sắp treo sẽ kêu về nó đến hết đời."""
    # CHỈ xét dòng «đang làm». Dòng đã `xong` là lịch sử: nó không giữ tệp của ai, và cái chuông
    # sắp treo cũng không nhìn tới nó. Bắt cả lịch sử phải đúng khuôn là bắt một phép thử hôm nay
    # chịu trách nhiệm cho mọi dòng từng được viết — nó sẽ đỏ vì những thứ không còn sửa được.
    thieu = [d for d in _dong()
             if str(d["trang_thai"]).startswith("đang làm") and not _ma(d["ma_viec"])]
    assert not thieu, (
        "những dòng này không đọc được mã việc (khuôn: `**MÃ — mô tả**` ở đầu ô):\n" +
        "\n".join("   làn " + str(d.get("lan")) + ": " +
                  str(d["ma_viec"])[:70] for d in thieu))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_ds2_3_moi_dong_doc_duoc_NGAY_BAT_DAU():
    """Luật của ĐS-1. Một cái chuông có lỗ thủng thì không phải cái chuông: dòng không ngày là
    dòng chuông không bao giờ nhìn thấy."""
    xau = []
    for d in _dong():
        if not str(d["trang_thai"]).startswith("đang làm"):
            continue                      # dòng đã `xong` là lịch sử — xem ghi chú ở luật 2
        bd = str(d.get("bat_dau") or "")
        if not re.match(r"\d{2}-\d{2}-\d{4}", bd):
            xau.append("   làn " + str(d.get("lan")) + " · " +
                       (_ma(d["ma_viec"]) or "(không mã)") +
                       " · ngày đọc được: " + repr(bd))
    assert not xau, ("những dòng này không đọc được ngày bắt đầu (khuôn `DD-MM-YYYY HH:MM`):\n"
                     + "\n".join(xau))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_ds2_4_hai_lan_khong_cung_giu_mot_tep():
    """Đo bằng CHÍNH bộ đọc của hàng rào, trên MỌI nguồn sổ — bài học Đợt DỌN-PQ2.

    Đợt này đóng nhiều dòng cùng lúc, nên nó phải tự chứng minh rằng việc đóng ấy không làm hai
    làn còn lại đâm vào nhau.
    """
    giu, dung_do = {}, []
    for d in _dong():
        if not str(d.get("trang_thai", "")).startswith("đang làm"):
            continue
        for t in d.get("tep", []):
            cu = giu.get(t)
            if cu is not None and cu["lan"] != d["lan"]:
                dung_do.append("   " + t + "\n      " + str(cu["lan"]) + "\n      " + str(d["lan"]))
            giu.setdefault(t, d)
    assert not dung_do, "HAI LÀN ĐANG GIỮ CÙNG MỘT TỆP:\n" + "\n".join(dung_do)
