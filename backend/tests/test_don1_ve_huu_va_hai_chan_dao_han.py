# -*- coding: utf-8 -*-
"""Đợt DỌN-1 (13/10/2026) — CHO VỀ HƯU THÌ THU HỒI KHOÁ, và hai chân đáo hạn là hai nghiệp vụ.

VÌ SAO CÓ TỆP NÀY

Đợt E3 (12/10/2026) dựng khoá chống ghi sổ hai lần: `khoa_su_kien` = nguồn + mã nguồn + loại
nghiệp vụ, có chỉ mục DUY NHẤT. Khoá ấy đúng, và nó đã chặn đúng. Nhưng nó là một cột GHI MỘT
LẦN lúc lập chứng từ, không phải một phép tính đọc lại từ `source_ref` — và E3 không đi hỏi
NHỮNG AI ĐANG ĐỔI `source_ref`.

Có hai nơi đang đổi, cả hai trong `misa.py`: khi nạp lại dữ liệu, và khi nạp lại mốc kiểm toán.
Chúng đổi mã nguồn thành `...:old` để cho chứng từ cũ VỀ HƯU. Cột khoá thì không đổi theo, nên
chứng từ đã về hưu vẫn giữ chỗ khoá và lần ghi mới đâm vào chính nó: cửa chốt sổ kiểm toán gọi
với `replace=true` trả về 422 kể từ 12/10/2026. Đây là một cửa THẬT, Kế toán bấm được.

LỖI THỨ HAI, nhẹ hơn: đáo hạn ngân hàng là HAI bút toán — trả gốc khoản cũ, nhận giải ngân khoản
mới — cùng một khế ước nên cùng một mã nguồn. Dưới một tên nghiệp vụ chung thì khoá coi chân thứ
hai là bản sao của chân thứ nhất. Hôm nay chưa chặn ai, vì màn hình bút toán tay gửi mã nguồn
RỖNG và mã nguồn rỗng đã nằm trong bảng miễn khoá; nó sẽ chặn thật vào ngày dựng cửa đáo hạn
riêng. Cách đúng KHÔNG phải mở ngoại lệ — mở ngoại lệ là bỏ khoá cho mọi bút toán đáo hạn về
sau — mà là GỌI ĐÚNG TÊN hai việc khác nhau, đúng lẽ của khoá ba phần mà Chủ tịch đã chọn.

ĐIỀU TỆP NÀY CANH: về hưu thì mất khoá; hai chân đáo hạn không va nhau; và KHÔNG nơi nào trong
`misa.py` còn tự đổi mã nguồn bằng tay — vế cuối mới là vế chặn nơi thứ ba quên vế thứ hai.
"""
import os
import re

import pytest

from app.services import accounting as ACC
from app.services import chung_tu_loai as CTL

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ChungTuGia:
    """Chứng từ dựng tay — phép thử này đo PHÉP SUY, không đo cơ sở dữ liệu."""

    def __init__(self, source_ref: str, khoa_su_kien: str | None):
        self.source_ref = source_ref
        self.khoa_su_kien = khoa_su_kien


class PhienGia:
    """Phiên làm việc giả, chỉ đếm số lần `flush`.

    Đếm `flush` KHÔNG phải đo chi tiết cài đặt: phiên thật đặt `autoflush=False`, nên một thay
    đổi chưa đẩy xuống thì câu truy vấn ngay sau đó không thấy — và đó đúng là lý do bản đầu của
    `cho_ve_huu` vẫn để cửa nhập số dư đầu kỳ trả 422.
    """

    def __init__(self):
        self.so_lan_flush = 0

    def flush(self):
        self.so_lan_flush += 1


# ══════════════════════════════════════════════════════════════════════════════════════════════
# VỀ HƯU THÌ MẤT KHOÁ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_don1_1_ve_huu_thi_thu_hoi_khoa():
    """CHÍNH LỖI 422 của cửa chốt sổ kiểm toán."""
    db = PhienGia()
    e = ChungTuGia("kt-close:20260930", "ket_chuyen|kt-close:20260930|ket_chuyen_chot_so")
    ACC.cho_ve_huu(db, e)
    assert e.source_ref == "kt-close:20260930:old"
    assert e.khoa_su_kien is None, \
        "Chứng từ về hưu mà vẫn giữ khoá thì lần ghi lại đâm vào chính nó — đúng lỗi 12/10/2026"
    assert db.so_lan_flush == 1, (
        "Thu hồi khoá mà không `flush` thì câu truy vấn ngay sau đó vẫn thấy khoá cũ: phiên làm "
        "việc đặt autoflush=False. Đây là nửa còn lại của lỗi, đo được 13/10/2026.")


def test_don1_2_khoa_phai_la_RONG_chu_khong_phai_mot_gia_tri_khac():
    """NULL không va nhau trong chỉ mục duy nhất; một chuỗi `...:old` thì vẫn chiếm chỗ.

    Về hưu LẦN HAI cùng một sự kiện là chuyện có thật: kiểm toán gửi số mới hai lần trong một kỳ.
    Nếu khoá cũ chỉ được đổi tên chứ không xoá thì lần thứ hai va vào lần thứ nhất.
    """
    db = PhienGia()
    a = ChungTuGia("kt:20260930", "kiem_toan|kt:20260930|dieu_chinh_kiem_toan")
    b = ChungTuGia("kt:20260930", "kiem_toan|kt:20260930|dieu_chinh_kiem_toan")
    ACC.cho_ve_huu(db, a)
    ACC.cho_ve_huu(db, b)
    assert a.khoa_su_kien is None and b.khoa_su_kien is None


def test_don1_3_hau_to_doi_duoc_nhung_mac_dinh_la_old():
    db = PhienGia()
    e = ChungTuGia("misa:2026-09", "misa|misa:2026-09|chung_tu_misa")
    ACC.cho_ve_huu(db, e, ":bo")
    assert e.source_ref == "misa:2026-09:bo" and e.khoa_su_kien is None


def test_don1_4_misa_khong_con_tu_doi_ma_nguon_bang_tay():
    """Vế chặn nơi thứ ba quên vế thứ hai — hai nơi hiện có đã quên đúng một lần rồi."""
    t = open(os.path.join(GOC, "backend", "app", "services", "misa.py"), encoding="utf-8").read()
    sai = [m.group(0)[:70] for m in re.finditer(r"\.source_ref\s*=\s*f?[\"'][^\"']*:old", t)]
    assert not sai, ("misa.py còn tự đổi mã nguồn bằng tay: " + repr(sai) +
                     " — dùng `accounting.cho_ve_huu(e)` để khoá được thu hồi cùng lúc.")
    assert t.count("ACC.cho_ve_huu(db, e)") == 2, "Phải đúng hai nơi cho chứng từ về hưu"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HAI CHÂN ĐÁO HẠN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_don1_5_hai_chan_dao_han_khong_va_nhau():
    """Cùng nguồn, cùng mã nguồn, KHÁC nghiệp vụ — khoá phải ra hai giá trị khác nhau."""
    k1 = CTL.khoa("quy_tac", "dao_han:DH0826", "tra_goc_vay")
    k2 = CTL.khoa("quy_tac", "dao_han:DH0826", "nhan_giai_ngan_vay")
    assert k1 and k2 and k1 != k2, (k1, k2)


def test_don1_6_cung_mot_chan_ghi_hai_lan_thi_van_bi_chan():
    """Đợt này KHÔNG nới khoá: ghi lại ĐÚNG một chân vẫn phải ra cùng một khoá."""
    assert CTL.khoa("quy_tac", "dao_han:DH0826", "tra_goc_vay") \
        == CTL.khoa("quy_tac", "dao_han:DH0826", "tra_goc_vay")


@pytest.mark.parametrize("ma", ["tra_goc_vay", "nhan_giai_ngan_vay"])
def test_don1_7_hai_ten_nghiep_vu_moi_duoc_khai_du(ma):
    """Khai nửa vời thì `nghiep_vu_hop_le` ném lỗi ngay lúc ghi sổ — khai đủ hay đừng khai."""
    assert CTL.nghiep_vu_hop_le(ma) == ma
    assert CTL.chung_tu_cua(ma) == "PKT"
    assert CTL.ten_nghiep_vu(ma) != ma, "Phải có tên tiếng Việt đọc được trên sổ"


def test_don1_8_khong_mo_ngoai_le_nao_moi():
    """Đợt này sửa bằng cách GỌI ĐÚNG TÊN, không bằng cách bỏ khoá. Bảng miễn khoá phải y nguyên."""
    assert set(CTL.KHONG_KHOA_SU_KIEN) == {"", "quy_tac:"}, (
        "Đợt DỌN-1 không được thêm dòng miễn khoá nào: " + repr(sorted(CTL.KHONG_KHOA_SU_KIEN)))
    assert CTL.duoc_mien_khoa("dao_han:DH0826") == "", "Đáo hạn KHÔNG được miễn khoá"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CỬA HẸP CỦA CI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_don1_9_cua_hep_phai_chay_ca_tren_PR():
    """Đây là đường mà bốn chỗ đỏ đi vào kho mà không ai thấy.

    `if: github.event_name == 'push'` nghĩa là cửa hẹp chỉ chạy SAU khi gộp. Cửa chặn đủ bộ nặng
    khoảng 37 phút nên không ai chờ; cửa hẹp ~50 giây là thứ thật sự được đọc trước khi bấm Merge.
    """
    ci = open(os.path.join(GOC, ".github", "workflows", "ci.yml"), encoding="utf-8").read()
    khoi = ci[ci.index("hang-rao-gop:"):]
    dau = khoi[:khoi.index("steps:")]
    assert "github.event_name == 'push'" not in dau, \
        "Cửa hẹp lại chỉ chạy trên push — nó sẽ chỉ báo sau khi đã gộp"
    assert "VTOS_TEP_DOI" in khoi[:khoi.index("pytest")], \
        "Cửa hẹp phải TỰ tính danh sách tệp nhánh đổi: mỗi việc chạy ở một máy riêng"
