# -*- coding: utf-8 -*-
"""Đợt LAN-TCKT 02/11/2026 — MỞ LÀN RIÊNG CHO TÀI CHÍNH – KẾ TOÁN.

Chủ tịch chốt 02/11/2026 sau khi bốn nhánh R4c lần lượt không gộp được.

ĐO ĐƯỢC TRƯỚC KHI VIẾT

`docs/dang-lam/README.md` ghi lại quyết định 06/10/2026: tách quyển sổ chung thành mỗi làn một
tệp, vì quyển chung «bị đè hoặc gây xung đột NĂM LẦN TRONG BA TUẦN, và nó là thứ DUY NHẤT gây
xung đột trong những lần ấy — không một tệp mã nào».

Việc tách ấy chạy đúng. Hôm nay làn `at2-nha-hang-agoda` gộp vào main mà KHÔNG đụng
`phan-quyen.md`. Nhưng bốn đợt R4c đều khai làn «Phân quyền», nên cả bốn nối vào CUỐI cùng một
tệp — và đo được tệp ấy đã thành chỗ chứa chung:

    phan-quyen.md   444 KB · 187 dòng · 16 dòng còn «đang làm»
    vpm.md          334 byte

Tức là cùng một hỏng hóc của ngày 06/10, lặp lại ở một tầng sâu hơn: không phải giữa các làn
nữa, mà TRONG một làn đã phình thành sáu làn đội lốt một.

ĐỢT NÀY KHÔNG DỜI MỘT DÒNG NÀO của ai. Nó chỉ mở chỗ mới. Luật 5 canh đúng việc ấy.
"""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(GOC, "docs", "dang-lam")
TEP_LAN = os.path.join(THU_MUC, "tc-kt.md")
README = os.path.join(THU_MUC, "README.md")

TEN_LAN = "TC-KT"
TEN_TEP = "tc-kt"


# ───────────────────────────────────────────────────────────────────── LUẬT 1
def test_lantckt_1_lan_moi_khai_du_hai_dau():
    """Khai trong `LAN_TEP` VÀ có tệp — thiếu một đầu là tách nửa vời.

    `test_moi_lan_deu_co_mot_tep_va_khong_tep_nao_thua` của hàng rào đòi một-đổi-một. Luật này
    đo lại độc lập, vì một đợt làm hỏng hàng rào rồi hỏi chính hàng rào ấy thì bao giờ cũng được
    trả lời là ổn.
    """
    from tests.test_giu_cho_lan import LAN_TEP

    assert LAN_TEP.get(TEN_LAN) == TEN_TEP, f"LAN_TEP chưa khai làn {TEN_LAN}"
    assert os.path.exists(TEP_LAN), "chưa tạo docs/dang-lam/tc-kt.md"

    co = {t[:-3] for t in os.listdir(THU_MUC) if t.endswith(".md") and t != "README.md"}
    assert co == set(LAN_TEP.values()), (
        f"thư mục và LAN_TEP lệch nhau:\n  thiếu: {sorted(set(LAN_TEP.values()) - co)}"
        f"\n  thừa : {sorted(co - set(LAN_TEP.values()))}")


# ───────────────────────────────────────────────────────────────────── LUẬT 2
def test_lantckt_2_tep_moi_doc_duoc_bang_CHINH_bo_doc_cua_hang_rao():
    """Đọc bằng `_doc_mot_tep` của hàng rào, không bằng một bộ đọc viết riêng ở đây.

    Viết bộ đọc riêng thì phép thử chỉ chứng minh «tệp này đúng khuôn mà TÔI nghĩ», còn thứ cần
    chứng minh là «hàng rào thật đọc được nó». Một tệp sai khuôn mà hàng rào bỏ qua im lặng là
    đúng cái kiểu hỏng README cảnh báo.
    """
    from tests.test_giu_cho_lan import _doc_mot_tep, COT

    dong = _doc_mot_tep(TEP_LAN)
    assert dong, "hàng rào đọc tc-kt.md ra RỖNG — bảng sai khuôn, hoặc thiếu dòng của đợt này"
    for d in dong:
        assert d["lan"] == TEN_LAN, (
            f"dòng {d['so_dong']} trong tc-kt.md khai làn {d['lan']!r} — luật 2 của README: "
            f"dòng nằm trong tệp của làn nào thì cột Làn phải là làn ấy")
        assert d["ma_viec"], f"dòng {d['so_dong']} thiếu mã việc"
        assert d["tep"], f"dòng {d['so_dong']} thiếu danh sách tệp"
    assert len(COT) == 5


# ───────────────────────────────────────────────────────────────────── LUẬT 3
def test_lantckt_3_tep_moi_vao_duoc_tap_gop():
    """Tệp mới phải nằm trong tập gộp — nếu không, hàng rào «hai làn cùng một tệp» không thấy nó.

    Đây là chỗ hỏng IM LẶNG: bộ đọc bỏ sót một nguồn thì mọi phép thử vẫn xanh, vì chúng chỉ xét
    những dòng chúng nhìn thấy, và ít dòng hơn thì càng ít khả năng đỏ.
    """
    from tests.test_giu_cho_lan import _doc_bang, _nguon

    nguon = [os.path.normpath(d) for d in _nguon()]
    assert os.path.normpath(TEP_LAN) in nguon, "tc-kt.md KHÔNG nằm trong danh sách nguồn"
    assert any(d["lan"] == TEN_LAN for d in _doc_bang()), "tập gộp không thấy dòng nào của TC-KT"


# ───────────────────────────────────────────────────────────────────── LUẬT 4
def test_lantckt_4_hang_rao_thu_hai_nhan_tep_moi_ma_khong_phai_sua():
    """`test_giu_cho_nhanh` nhận tệp sổ theo KHUÔN ĐƯỜNG DẪN, không theo danh sách làn.

    Đo điều đó chứ không tin nó: nếu nó cũng có một danh sách làn gõ tay thì đợt này còn thiếu
    một nửa, và luật N2 sẽ chặn mọi nhánh TC-KT với lời «nhánh này chưa ghi sổ».
    """
    from tests.test_giu_cho_nhanh import la_tep_so

    assert la_tep_so("docs/dang-lam/tc-kt.md"), "hàng rào N2 KHÔNG coi tc-kt.md là sổ"
    assert not la_tep_so("docs/dang-lam/README.md")
    assert not la_tep_so("docs/dang-lam/tc-kt/R4c-3.md"), \
        "N2 nhận cả tệp trong thư mục con — khuôn đường dẫn đã đổi, đọc lại trước khi tin"


# ───────────────────────────────────────────────────────────────────── LUẬT 5
def test_lantckt_5_khong_doi_mot_dong_nao_cua_lan_khac():
    """Đợt này MỞ CHỖ MỚI, không dọn nhà hộ ai.

    `phan-quyen.md` còn 16 dòng «đang làm», trong đó có dòng của làn khác và của đợt chưa gộp.
    Dời chúng sang đây là sửa sổ của người khác mà không ai nhờ, và là làm gãy những nhánh đang
    bay trỏ vào đúng dòng ấy — đúng lý do README giữ `docs/DANG-LAM.md` chứ không xoá.
    """
    from tests.test_giu_cho_lan import _doc_mot_tep

    pq = _doc_mot_tep(os.path.join(THU_MUC, "phan-quyen.md"))
    assert pq, "không đọc được phan-quyen.md"
    assert all(d["lan"] != TEN_LAN for d in pq), \
        "có dòng TC-KT nằm trong phan-quyen.md — đợt này đã dời dòng, hoặc ghi nhầm tệp"
    assert sum(1 for d in pq if d["trang_thai"] == "đang làm") >= 16, \
        "số dòng «đang làm» của phan-quyen.md GIẢM — đợt này đã đụng vào sổ của làn khác"


# ───────────────────────────────────────────────────────────────────── LUẬT 6
def test_lantckt_6_hai_bang_khai_lan_khong_lech_nhau():
    """README liệt kê làn, `LAN_TEP` cũng liệt kê làn. Hai bảng khai cùng một thứ thì sớm muộn
    cũng lệch, nên phải có một phép đo nối chúng lại — bài học của chính `test_tx2` và của
    `CONFIRMER` ở màn hình đề nghị chi."""
    from tests.test_giu_cho_lan import LAN_TEP

    chu = open(README, encoding="utf-8").read()
    for lan, tep in LAN_TEP.items():
        assert f"`docs/dang-lam/{tep}.md`" in chu, f"README thiếu dòng cho làn {lan}"
        assert lan in chu, f"README thiếu tên làn {lan}"
