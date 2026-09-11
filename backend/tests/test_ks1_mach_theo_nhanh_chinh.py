"""KS-1 · Mạch nâng cấp phải đúng so với NHÁNH CHÍNH, không phải so với cây làm việc.

Sự việc 10/9/2026, chép lại để người sửa sau biết phép thử này canh cái gì:

  Nhánh chính được đẩy kèm bản `w1a2b3c4d5e6` khai `down_revision = "v14b6e9c2a7d31"`. Bản v14 lúc ấy
  chỉ nằm trên nhánh `gop-dot2`, chưa gộp. Render triển khai, `alembic upgrade head` chết với
  KeyError: 'v14b6e9c2a7d31'. Máy chủ giữ bản cũ nên VTOS vẫn chạy — KHÔNG AI THẤY GÌ BẤT THƯỜNG — mà
  mọi lần triển khai sau đều hỏng y hệt.

  `test_mach_migration.py` vẫn xanh suốt lúc đó, và nó xanh ĐÚNG theo cách nó được viết: nó đọc thư
  mục versions trên đĩa, mà đĩa của người viết có đủ v14. Đó chính là chỗ lỗi lọt. Phép thử đo máy
  người viết; Render đọc nhánh đã đẩy.

Bốn phép thử dưới đây, và ý nghĩa của từng cái khi nó đỏ:

  KS1-1  cây làm việc kín mạch          – rẻ, luôn chạy; giữ nguyên mức bảo vệ cũ
  KS1-2  NHÁNH CHÍNH kín mạch           – đỏ = nhánh đang triển khai đã hỏng, mọi deploy sẽ chết
  KS1-3  NHÁNH CHÍNH đúng một đầu       – đỏ = alembic từ chối chạy trên nhánh ấy
  KS1-4  XEM TRƯỚC BẢN GỘP đúng một đầu – đỏ = từng nhánh xanh nhưng gộp vào là hỏng
  KS1-5  không đổi cha của bản đã đẩy   – đỏ = nơi đã chạy migration không lùi lại được
  KS1-6  bản mới phải bám được nhánh chính – đỏ = đúng hình dạng sự cố 10/9, bắt TRƯỚC khi đẩy

Bẫy đang chờ sẵn lúc viết tệp này (11/9/2026): `gop-dot2` có v14 nối sau v11; nhánh chính có w1 nối
sau v13, v13 cũng nối sau v11. Gộp hai nhánh thì mạch có HAI ĐẦU. Từng nhánh đứng riêng đều xanh.
KS1-4 là phép thử duy nhất nhìn thấy chuyện đó, và nó phải đỏ cho tới khi v14 được trỏ lại sau w1.

Chạy độc lập, không cần cơ sở dữ liệu:  pytest backend/tests/test_ks1_mach_theo_nhanh_chinh.py
Chạy trước khi đẩy:                     python backend/tools/truoc_khi_day.py
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import ks_mach as M  # noqa: E402


# Khi máy không có git, hoặc không phân giải được nhánh chính, ba phép thử M2/M3 tự bỏ qua. Đó là
# nhượng bộ CÓ CHỦ ĐÍCH và chỉ dành cho máy lập trình: lúc ĐẨY thì `truoc_khi_day.py` fetch trước và
# BÁO ĐỎ nếu không phân giải được, nên không có đường nào lọt ra ngoài mà không ai biết.
_REF = M.ref_dung_duoc()
_LY_DO_BO_QUA = (
    "không phân giải được nhánh chính (thử: %s). Trên máy lập trình thì bỏ qua được; lúc đẩy thì "
    "backend/tools/truoc_khi_day.py sẽ fetch và BÁO ĐỎ chứ không bỏ qua." % (
        ", ".join((M.NHANH_CHINH,) + M.REF_DU_PHONG))
)
can_git = pytest.mark.skipif(_REF is None, reason=_LY_DO_BO_QUA)


def _nhanh():
    mach = M.doc_mach_tu_nhanh(_REF)
    assert mach is not None, f"đọc được ref {_REF} nhưng không lấy được thư mục versions của nó"
    assert mach, (
        f"nhánh {_REF} không có bản migration nào. Nếu đúng là kho VTOS thì đây là dấu hiệu đường dẫn "
        f"alembic/versions đã đổi chỗ mà KS-1 chưa biết — sửa THU_MUC_VERSIONS trong tools/ks_mach.py.")
    return mach


# ------------------------------------------------------------------ KS1-1

def test_ks1_1_cay_lam_viec_kin_mach():
    """Mức rẻ nhất, luôn chạy. Đây là mức bảo vệ cũ, giữ lại chứ không thay thế."""
    cay = M.doc_mach_tu_cay()
    treo = M.moc_treo(cay)
    assert not treo, (
        f"trong cây làm việc có bản nối sau một mã không tồn tại: {treo}. "
        f"{M.bao_cao(cay, 'cây làm việc')}")
    assert not M.vong_lap(cay), f"mạch trong cây làm việc có vòng lặp tại {M.vong_lap(cay)}"


# ------------------------------------------------------------------ KS1-2

@can_git
def test_ks1_2_nhanh_chinh_kin_mach():
    """ĐỎ Ở ĐÂY = NHÁNH ĐANG TRIỂN KHAI ĐÃ HỎNG SẴN, mọi lần deploy tới đều chết.

    Đây đúng là phép thử mà sự cố 10/9 cần và không có. Nó không đọc đĩa; nó đọc thứ nằm trên nhánh.
    """
    nhanh = _nhanh()
    treo = M.moc_treo(nhanh)
    assert not treo, (
        f"NHÁNH {_REF} ĐANG HỎNG: {[f'{r} nối sau {d} — không có bản nào mang mã {d} trên nhánh này' for r, d in treo]}\n"
        f"Render chạy 'alembic upgrade head' lúc khởi động container và sẽ chết với KeyError. Máy chủ "
        f"giữ bản cũ nên web vẫn chạy và KHÔNG AI THẤY GÌ — nhưng mọi lần triển khai sau đều hỏng y hệt.\n"
        f"Cách sửa: gộp bản còn thiếu lên nhánh chính TRƯỚC, hoặc trỏ down_revision về một bản có thật "
        f"trên nhánh. Đừng sửa bằng merge revision.\n{M.bao_cao(nhanh, _REF)}")


@can_git
def test_ks1_3_nhanh_chinh_dung_mot_dau_va_mot_goc():
    nhanh = _nhanh()
    dau = M.dau_mach(nhanh)
    assert len(dau) == 1, (
        f"nhánh {_REF} có {len(dau)} đầu mạch: {dau}. alembic từ chối chạy khi có nhiều hơn một đầu, "
        f"nên container không khởi động được.\n{M.bao_cao(nhanh, _REF)}")
    goc = M.goc_mach(nhanh)
    assert len(goc) == 1, f"nhánh {_REF} phải có đúng một bản khởi tạo, đang có {goc}"
    assert not M.vong_lap(nhanh), f"nhánh {_REF} có vòng lặp tại {M.vong_lap(nhanh)}"


# ------------------------------------------------------------------ KS1-4

@can_git
def test_ks1_4_xem_truoc_ban_gop_van_dung_mot_dau():
    """Từng nhánh xanh mà gộp vào là hỏng — phép thử duy nhất nhìn thấy chuyện đó.

    Hình dạng: nhánh A viết bản mới nối sau X, nhánh B cũng viết bản mới nối sau X. Mỗi nhánh đứng
    riêng vẫn đúng một đầu. Gộp lại thành hai đầu, và người gộp chỉ biết khi container không lên.
    """
    cay = M.doc_mach_tu_cay()
    nhanh = _nhanh()
    hop, _ = M.hop_mach(cay, nhanh)

    treo = M.moc_treo(hop)
    assert not treo, (
        f"bản gộp (cây làm việc + {_REF}) vẫn còn móc treo: {treo}. Bản còn thiếu nằm ở một nhánh thứ "
        f"ba chưa gộp — phải gộp nhánh ấy trước.\n{M.bao_cao(hop, 'bản gộp')}")

    dau = M.dau_mach(hop)
    assert len(dau) == 1, (
        f"GỘP VÀO LÀ HAI ĐẦU: {dau}. Cây làm việc đúng một đầu và {_REF} cũng đúng một đầu, nhưng hợp "
        f"lại thì không.\nCách sửa: chọn một thứ tự, cho bản viết sau nối tiếp bản viết trước bằng "
        f"cách đổi down_revision của NÓ (bản chưa đẩy), tuyệt đối không đổi down_revision của bản đã "
        f"có trên nhánh chính.\n"
        f"{M.bao_cao(cay, 'cây làm việc')}\n{M.bao_cao(nhanh, _REF)}\n{M.bao_cao(hop, 'bản gộp')}")


# ------------------------------------------------------------------ KS1-5

@can_git
def test_ks1_5_khong_doi_cha_cua_ban_da_day():
    """Đổi down_revision của một bản ĐÃ có trên nhánh chính là việc không lùi lại được.

    Nơi nào đã chạy bản ấy thì bảng alembic_version ghi mã cũ; đổi cha xong, đường downgrade không
    còn khớp với thứ đã chạy. Bản CHƯA đẩy thì đổi thoải mái — đó mới là chỗ để sửa.
    """
    cay = M.doc_mach_tu_cay()
    nhanh = _nhanh()
    _, xung_dot = M.hop_mach(cay, nhanh)
    assert not xung_dot, (
        "có bản ĐÃ trên nhánh chính bị đổi down_revision trong cây làm việc:\n"
        + "\n".join(f"  {r}: trên {_REF} nối sau {a}, trong cây nối sau {b}" for r, a, b in xung_dot)
        + "\nNơi đã chạy migration sẽ không lùi lại được. Muốn đổi thứ tự thì đổi down_revision của "
          "bản CHƯA đẩy, không đổi của bản đã đẩy.")


# ------------------------------------------------------------------ KS1-6

@can_git
def test_ks1_6_ban_moi_phai_bam_duoc_vao_nhanh_chinh():
    """Đúng hình dạng sự cố 10/9, nhưng bắt TRƯỚC khi đẩy chứ không phải sau khi Render chết.

    Mỗi bản sắp đẩy phải lần được tổ tiên về tới một bản CÓ THẬT trên nhánh chính. Bản nào lần ngược
    lên mà rơi vào khoảng không là bản đang móc vào cây làm việc của chính người viết.
    """
    cay = M.doc_mach_tu_cay()
    nhanh = _nhanh()
    moi = M.rieng_cua_cay(cay, nhanh)
    if not moi:
        pytest.skip("cây làm việc không có bản nào mới hơn nhánh chính")

    hop, _ = M.hop_mach(cay, nhanh)
    hong = []
    for r in moi:
        di, cur = set(), hop.get(r)
        while cur is not None and cur not in di:
            if cur in nhanh:
                break
            di.add(cur)
            cur = hop.get(cur)
        else:
            hong.append((r, f"lần ngược tới {cur!r} rồi hết mạch mà chưa chạm được nhánh chính"))

    assert not hong, (
        f"bản sắp đẩy không bám được vào {_REF}:\n"
        + "\n".join(f"  {r}: {ly}" for r, ly in hong)
        + f"\nĐây đúng là hình dạng đã làm Render chết ngày 10/9. Gộp bản nền lên nhánh chính trước, "
          f"rồi mới đẩy bản này.\nCác bản sắp đẩy: {moi}")


# ------------------------------------------------------------------ cửa chặn phải còn nguyên

def test_ks1_7_cua_chan_truoc_khi_day_van_con():
    """Phép thử chỉ có giá trị khi nó THỰC SỰ chạy trước mỗi lần đẩy.

    Xoá kịch bản chặn đi thì cả KS-1 thành trang trí. Phép thử này giữ cho việc đó không xảy ra âm
    thầm: ai bỏ cửa chặn phải bỏ luôn dòng này, và dòng bị bỏ thì nhìn thấy trong bản thay đổi.
    """
    tools = os.path.join(M.GOC_BACKEND, "tools")
    for ten in ("ks_mach.py", "truoc_khi_day.py", "pre-push"):
        assert os.path.exists(os.path.join(tools, ten)), (
            f"thiếu backend/tools/{ten} — cửa chặn trước khi đẩy của KS-1 không còn nguyên. "
            f"Cài lại bằng: git config core.hooksPath backend/tools")
