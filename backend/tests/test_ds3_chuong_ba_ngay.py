# -*- coding: utf-8 -*-
"""Đợt DS-3 06/11/2026 — CHUÔNG BA NGÀY CỦA SỔ GIỮ CHỖ (`TRAN_NGAY`).

Món nợ CÓ TÊN từ 28/10/2026: Đợt ĐS-1 mang ba luật của sổ giữ chỗ, đợt ấy bị đóng mà không gộp,
và cái chuông chưa bao giờ có. Hai luật kia — mỗi dòng đọc được mã việc, đọc được ngày bắt đầu —
đã vào ở Đợt DS-2. Đây là luật còn lại.

CHUÔNG HỎI MỘT CÂU, VÀ KHÔNG PHẢI CÂU «AI SAI»

Một dòng `đang làm` quá ba ngày thì **quyển sổ không còn đáng tin**. Nó không hỏi làn ấy đúng hay
sai. Kêu lên thì chỉ có hai khả năng, và cả hai đều phải nhìn:

  - làn ấy treo thật — và tệp của nó đang bị giữ cho một việc không ai làm;
  - hoặc sổ nói sai — việc xong rồi mà dòng chưa đóng.

Vì sao phải có: sổ vừa dồn tới **28 dòng ôi** mà không gì kêu lên, và đúng chuyện ấy đã chặn Đợt
QUY-2a hôm 04/11 (DỌN-R4c3 đã gộp từ hai ngày trước vẫn giữ `test_le2b`). Không có chuông thì nó
dồn lại, và lần sau cũng không ai biết cho tới khi một làn đâm vào.

MỘT CÁI CHUÔNG KHÔNG NỐI VÀO VIỆC CHẶN THÌ KHÔNG PHẢI CÁI CHUÔNG — luật 2 đo chính việc nối ấy.

MỘT CÁI CHUÔNG CÓ LỖ THỦNG THÌ KHÔNG PHẢI CÁI CHUÔNG — dòng không đọc được ngày tính là ĐANG KÊU,
chứ không lặng lẽ cho qua. Luật 3 đo cả hai chiều của phép tính ấy.
"""
import datetime
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_ds3.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CI = os.path.join(GOC, ".github", "workflows", "ci.yml")
TEP_NAY = "tests/test_ds3_chuong_ba_ngay.py"

# Ngưỡng của cái chuông, tính bằng NGÀY. Một hằng số có tên, ở đúng một chỗ.
#
# Ba ngày là con số Chủ tịch chốt 28/10/2026. Nó không phải "thời gian hợp lý để làm xong một
# việc" — nhiều đợt làm lâu hơn thế. Nó là thời gian hợp lý để một dòng sổ còn NÓI ĐÚNG về thực
# tế: quá ba ngày mà dòng không đổi thì hoặc việc đã xong (sổ sai), hoặc việc đang treo (phải
# biết). Nới con số này cho hết đỏ là bỏ cái chuông đi mà vẫn giữ hình nó.
TRAN_NGAY = 3


def _dong():
    """Mọi dòng bảng của MỌI quyển sổ, đọc bằng CHÍNH bộ đọc của hàng rào.

    Bài học Đợt DS-2, trả giá ba lần trong một ngày: một phép đo tự liệt kê nguồn sẽ bỏ sót, và
    bỏ sót thì nói ÍT hơn sự thật chứ không nói sai — nên nó không tự kêu lên.
    """
    from test_giu_cho_lan import _doc_bang
    return _doc_bang()


def qua_han(bat_dau, hom_nay=None, tran=TRAN_NGAY):
    """Dòng này đã quá hạn chưa? Ngày KHÔNG ĐỌC ĐƯỢC tính là ĐÃ QUÁ HẠN.

    Chiều ấy là chủ ý, không phải cho tiện: nếu ngày hỏng mà tính là chưa quá hạn thì ai muốn tắt
    chuông chỉ cần làm hỏng ô ngày — và cái chuông có một lỗ thủng đúng bằng cỡ người muốn lách.
    """
    m = re.match(r"\s*(\d{2})-(\d{2})-(\d{4})", str(bat_dau or ""))
    if not m:
        return True
    try:
        bd = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return True
    return (( hom_nay or datetime.date.today()) - bd).days > tran


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_ds3_1_khong_dong_nao_dang_lam_qua_ba_ngay():
    """CÁI CHUÔNG.

    Đỏ ở đây KHÔNG có nghĩa là ai đó viết sai mã. Nó có nghĩa là quyển sổ đã quá hạn nói thật, và
    người đọc phải đi hỏi — chứ không phải sửa phép thử cho hết đỏ.

    Hai cách xử, cả hai đều ở sổ chứ không ở đây: đợt ấy ĐÃ GỘP thì đổi dòng sang `xong` (Đợt DS-2
    làm việc ấy bằng cách hỏi git); đợt ấy CÒN LÀM THẬT thì cập nhật dòng — đổi ngày bắt đầu kèm
    một câu nói vì sao nó còn mở.
    """
    hom_nay = datetime.date.today()
    oi = [d for d in _dong()
          if str(d.get("trang_thai", "")).startswith("đang làm")
          and qua_han(d.get("bat_dau"), hom_nay)]
    assert not oi, (
        f"SỔ GIỮ CHỖ CÓ {len(oi)} DÒNG «đang làm» QUÁ {TRAN_NGAY} NGÀY.\n\n"
        "Đây không phải lỗi mã. Nó nói quyển sổ đã quá hạn nói thật — hoặc làn ấy treo thật và "
        "đang giữ tệp cho một việc không ai làm, hoặc việc xong rồi mà dòng chưa đóng.\n\n"
        + "\n".join(
            f"   {d.get('nguon')} dòng {d.get('so_dong')} · làn {d.get('lan')} · "
            f"từ {d.get('bat_dau')}" for d in oi)
        + "\n\nCách xử ở SỔ, không ở đây: đã gộp thì đổi dòng sang `xong`; còn làm thật thì cập "
          "nhật dòng. ĐỪNG nới `TRAN_NGAY` cho hết đỏ — nới là bỏ cái chuông mà vẫn giữ hình nó.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_ds3_2_chuong_phai_duoc_noi_vao_viec_CHAN():
    """Một cái chuông không nối vào việc chặn thì không phải cái chuông.

    Nó phải nằm ở CẢ HAI chỗ: dòng `pytest` của việc `hang-rao-gop` trong `ci.yml`, và danh sách
    `HANG_RAO` của `test_ci_hang_rao_main.py`. Hai chỗ chứ không một, vì `test_ci2` và `test_ci3`
    bắt hai bên phải khớp nhau — ai gỡ một bên thì bên kia đỏ.
    """
    assert os.path.exists(CI), "khong thay .github/workflows/ci.yml"
    # Bỏ dòng chú thích trước khi tìm — bài học `test_ci_hang_rao_main`: tên tệp có nhắc trong
    # phần giải thích đầu ci.yml, nên tìm trên cả tệp thì LỜI CHÚ làm phép thử xanh trong khi
    # phần LỆNH đã mất thứ ấy rồi.
    lenh = "\n".join(d for d in open(CI, encoding="utf-8").read().split("\n")
                     if not d.strip().startswith("#"))
    assert TEP_NAY in lenh, (
        f"`{TEP_NAY}` KHÔNG có trong phần lệnh của ci.yml — cái chuông không được treo vào việc "
        "`hang-rao-gop`, nên nó kêu ở một chỗ không ai nghe.")
    from test_ci_hang_rao_main import HANG_RAO
    assert TEP_NAY in HANG_RAO, (
        f"`{TEP_NAY}` chưa khai trong `HANG_RAO` của test_ci_hang_rao_main.py — `test_ci3` sẽ đỏ, "
        "và danh sách ấy đang nói dối về cửa hẹp.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_ds3_3_phep_tinh_qua_han_dung_ca_hai_chieu():
    """Đo CHÍNH phép tính của cái chuông, bằng ngày dựng sẵn — không chờ lịch sử tự dựng cảnh.

    Một cái chuông chỉ được đo khi nó đang xanh thì không ai biết nó có kêu nổi hay không.
    """
    hn = datetime.date(2026, 11, 6)
    # RANH GIỚI NÓI RÕ: «quá ba ngày» là HƠN ba ngày, nên tròn ba ngày thì CHƯA kêu. Bản đầu
    # của luật này đòi tròn ba ngày phải kêu và đỏ — kỳ vọng sai, phép tính đúng. Ghi lại để lần
    # sau không ai sửa phép tính cho khớp một kỳ vọng nhầm.
    assert qua_han("01-11-2026 09:30", hn) is True, "năm ngày mà chuông không kêu"
    assert qua_han("02-11-2026 09:30", hn) is True, "bốn ngày mà chuông không kêu"
    assert qua_han("03-11-2026 09:30", hn) is False, "tròn ba ngày — chưa QUÁ ba ngày"
    assert qua_han("04-11-2026 23:59", hn) is False, "hai ngày mà chuông đã kêu"
    assert qua_han("06-11-2026 00:01", hn) is False, "mở hôm nay mà chuông đã kêu"
    # Ngày hỏng tính là ĐANG KÊU. Nếu chiều này đảo lại thì ai muốn tắt chuông chỉ cần làm hỏng
    # ô ngày — và cái chuông có một lỗ thủng đúng bằng cỡ người muốn lách.
    for xau in ("", "   ", "hôm qua", "2026-11-02", "32-11-2026 00:00", None):
        assert qua_han(xau, hn) is True, f"ngày không đọc được {xau!r} mà chuông im"
    # Ngưỡng là một hằng số có tên, đọc được từ ngoài — nới nó là một việc nhìn thấy được.
    assert TRAN_NGAY == 3, "ngưỡng chuông đã bị đổi — đổi là một quyết định, phải nói ra ở sổ"
