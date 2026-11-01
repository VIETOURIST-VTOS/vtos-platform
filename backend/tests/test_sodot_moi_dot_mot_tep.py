# -*- coding: utf-8 -*-
"""Đợt SO-DOT 02/11/2026 — MỖI ĐỢT MỘT TỆP SỔ, HẾT HẲN XUNG ĐỘT SỔ GIỮ CHỖ.

Chủ tịch chốt 02/11/2026 (cách B), sau khi đã xem giá của nó: đợt này đụng HAI hàng rào mà mọi
làn đứng lên, và làm MỘT phép thử đang xanh đổi nghĩa.

VÌ SAO TÁCH LÀN CHƯA ĐỦ

Tách làn ngày 06/10 chữa xung đột GIỮA các làn, và nó chạy đúng: 02/11 làn `at2-nha-hang-agoda`
gộp vào main mà không đụng `phan-quyen.md`. Nhưng nó không chữa được hai đợt của CÙNG một làn —
cả hai vẫn nối vào cuối một tệp. Đo được 02/11: bốn nhánh R4c liên tiếp không gộp được, và
`phan-quyen.md` đã là **444 KB · 187 dòng · 16 dòng “đang làm”** trong khi `vpm.md` là 334 byte.

Từ đợt này một đợt TẠO một tệp mới. Git không có gì để hoà — không phải hoà khéo hơn, mà là
không có xung đột nào tồn tại.

HAI CHỖ ĐỢT NÀY PHẢI CẨN THẬN NHẤT, và cả hai đều có luật riêng ở dưới

  · Bộ đọc bỏ sót nguồn. Chính `test_giu_cho_lan` gọi đây là “chỗ dễ hỏng im lặng nhất của việc
    tách 06/10”: bỏ sót một nguồn thì MỌI phép thử vẫn xanh, vì chúng chỉ xét những dòng chúng
    nhìn thấy. Luật 3 và luật 4 canh hai chiều.
  · N2 rộng ra một bậc, nên chỗ chặn thư mục lạ chuyển từ `la_tep_so` sang hàng rào một-đổi-một.
    Luật 5 đo lại điều ấy, để nó là thứ đo được chứ không phải một câu hứa trong lời chú thích.
"""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(GOC, "docs", "dang-lam")
TM_LAN = os.path.join(THU_MUC, "tc-kt")
TEP_DOT = os.path.join(TM_LAN, "SO-DOT.md")


# ───────────────────────────────────────────────────────────────────── LUẬT 1
def test_sodot_1_thu_muc_lan_va_tep_dot_dau_tien():
    """Thư mục của làn TC-KT có thật, và tệp của chính đợt này nằm trong đó."""
    from tests.test_giu_cho_lan import LAN_TEP, _doc_mot_tep

    assert LAN_TEP.get("TC-KT") == "tc-kt", "thiếu Đợt LAN-TCKT trên main"
    assert os.path.isdir(TM_LAN), "chưa tạo docs/dang-lam/tc-kt/"
    assert os.path.exists(TEP_DOT), "chưa tạo docs/dang-lam/tc-kt/SO-DOT.md"

    dong = _doc_mot_tep(TEP_DOT)
    assert len(dong) == 1, f"tệp của một đợt phải có ĐÚNG một dòng, đang có {len(dong)}"
    assert dong[0]["lan"] == "TC-KT"
    assert "SO-DOT" in dong[0]["ma_viec"]


# ───────────────────────────────────────────────────────────────────── LUẬT 2
def test_sodot_2_hai_dang_song_chung_duoc():
    """Tệp phẳng `tc-kt.md` và thư mục `tc-kt/` cùng tồn tại, và CẢ HAI đều vào tập gộp.

    Ép dời là làm gãy nhánh đang bay — cùng lẽ với việc giữ `docs/DANG-LAM.md`. Nên luật này
    đòi hai dạng sống chung, chứ không đòi dạng mới thắng dạng cũ.
    """
    from tests.test_giu_cho_lan import _nguon, _tep_trong_lan

    phang = os.path.join(THU_MUC, "tc-kt.md")
    assert os.path.exists(phang), "Đợt LAN-TCKT tạo tc-kt.md — đợt này KHÔNG được xoá nó"

    cua_lan = [os.path.normpath(d) for d in _tep_trong_lan("tc-kt")]
    assert os.path.normpath(phang) in cua_lan
    assert os.path.normpath(TEP_DOT) in cua_lan

    nguon = [os.path.normpath(d) for d in _nguon()]
    assert os.path.normpath(TEP_DOT) in nguon, "tệp của đợt KHÔNG vào danh sách nguồn"
    assert os.path.normpath(phang) in nguon, "tệp phẳng rơi khỏi danh sách nguồn"


# ───────────────────────────────────────────────────────────────────── LUẬT 3
def test_sodot_3_tap_gop_thay_du_moi_tep_tren_dia():
    """Đếm từ HỆ TỆP rồi so với tập gộp — không hỏi `_nguon()` xem nó có bỏ sót gì không.

    Hỏi chính cái hàm đang nghi ngờ thì bao giờ cũng nhận được câu “không bỏ sót gì”.
    """
    from tests.test_giu_cho_lan import _doc_bang, _doc_mot_tep

    tren_dia = []
    for goc, _tm, teps in os.walk(THU_MUC):
        tren_dia += [os.path.join(goc, t) for t in teps if t.endswith(".md") and t != "README.md"]

    gop = {}
    for d in _doc_bang():
        gop[d["nguon"]] = gop.get(d["nguon"], 0) + 1

    thieu = []
    for duong in sorted(tren_dia):
        ten = os.path.relpath(duong, GOC).replace("\\", "/")
        co = len(_doc_mot_tep(duong))
        if gop.get(ten, 0) != co:
            thieu.append(f"{ten}: đĩa {co} dòng, tập gộp {gop.get(ten, 0)}")
    assert not thieu, "TẬP GỘP BỎ SÓT: " + " · ".join(thieu)


# ───────────────────────────────────────────────────────────────────── LUẬT 4
def test_sodot_4_mot_bac_nua_thi_PHAI_DO_chu_khong_im_lang():
    """Phép phá: đặt một tệp sổ ở bậc thứ hai, hàng rào phải kêu.

    Bộ đọc chỉ đi MỘT bậc. Nếu bậc sâu hơn rơi khỏi tập gộp mà không gì đỏ, thì hàng rào “hai làn
    cùng một tệp” tắt ngấm đúng lúc nó vừa được nới ra cho dễ dùng — và đó là toàn bộ nỗi lo của
    việc chọn cách B.
    """
    import pytest

    from tests.test_giu_cho_lan import test_moi_lan_deu_co_mot_tep_va_khong_tep_nao_thua as mot_doi_mot

    sau = os.path.join(TM_LAN, "_pha_sodot")
    os.makedirs(sau, exist_ok=True)
    try:
        with open(os.path.join(sau, "x.md"), "w", encoding="utf-8") as f:
            f.write("| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |\n"
                    "|---|---|---|---|---|\n"
                    "| TC-KT | **PHÁ** | backend/x.py | 02-11-2026 00:00 | đang làm |\n")
        with pytest.raises(AssertionError) as ex:
            mot_doi_mot()
        assert "THƯ MỤC CON" in str(ex.value)
    finally:
        for t in os.listdir(sau):
            os.remove(os.path.join(sau, t))
        os.rmdir(sau)

    # Và sau khi dọn, hàng rào phải XANH lại — nếu không thì phép phá tự nó làm hỏng kho.
    mot_doi_mot()


# ───────────────────────────────────────────────────────────────────── LUẬT 5
def test_sodot_5_N2_rong_ra_nhung_cho_chan_khong_mat():
    """N2 nhận một bậc; thư mục lạ nay bị chặn ở hàng rào một-đổi-một. Đo cả hai vế."""
    from tests.test_giu_cho_lan import LAN_TEP
    from tests.test_giu_cho_nhanh import la_tep_so

    assert la_tep_so("docs/dang-lam/tc-kt/SO-DOT.md"), "N2 không nhận cách ghi sổ mới"
    assert not la_tep_so("docs/dang-lam/tc-kt/sau/nua.md"), "N2 nhận hai bậc — bộ đọc không thấy"
    assert not la_tep_so("docs/dang-lam/README.md")
    assert not la_tep_so("docs/dang-lam/tc-kt/README.md")

    co = set()
    for t in os.listdir(THU_MUC):
        if os.path.isdir(os.path.join(THU_MUC, t)):
            co.add(t)
        elif t.endswith(".md") and t != "README.md":
            co.add(t[:-3])
    assert co == set(LAN_TEP.values()), "một-đổi-một lệch — chỗ chặn thư mục lạ đang hở"


# ───────────────────────────────────────────────────────────────────── LUẬT 6
def test_sodot_6_hai_hang_rao_cu_khong_mat_phep_do_nao():
    """Đợt này sửa hai tệp hàng rào. Đếm lại để chắc không phép đo nào bị bỏ.

    Đo được trên main trước khi vá: `test_giu_cho_lan` 15 phép (sau Đợt LAN-TCKT),
    `test_giu_cho_nhanh` 12 phép. Đợt này THÊM một phép vào tệp thứ hai (gn11b), không bớt.
    """
    t = os.path.join(GOC, "backend", "tests")
    a = open(os.path.join(t, "test_giu_cho_lan.py"), encoding="utf-8").read()
    b = open(os.path.join(t, "test_giu_cho_nhanh.py"), encoding="utf-8").read()

    assert a.count("\ndef test_") >= 8, "test_giu_cho_lan mất hàm phép thử"
    assert b.count("\ndef test_") >= 12, "test_giu_cho_nhanh mất hàm phép thử"
    assert "def test_gn11b_thu_muc_la_van_bi_chan_nhung_o_hang_rao_kia" in b
    # Hai câu nói rõ chỗ đổi nghĩa phải CÒN trong mã — người sửa sau phải đọc được lý do.
    assert "ĐỢT SO-DOT" in a and "ĐỢT SO-DOT" in b
