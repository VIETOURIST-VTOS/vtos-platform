# -*- coding: utf-8 -*-
"""TR-6 · 13/11/2026 — HÀNG RÀO PHẠM VI CỦA LỜI ĐỒNG Ý.

Đợt này đưa đánh giá khách lên `kh.vietourist.vn`, tức RA NGOÀI INTERNET. Luật đã ghi sẵn trong
`services/ho_so_hdv.py` từ 17/10/2026:

    «Mở ra ngoài internet là một phạm vi RỘNG HƠN điều khách đã đồng ý — phải hỏi lại khách bằng
     một câu mới, không phải đổi một dòng cấu hình.»

Tệp này canh đúng câu ấy. Nó không đo giao diện, không đo điểm trung bình — nó đo MỘT việc: một
lời đồng ý thu bằng câu hỏi CŨ không bao giờ được dùng cho trang bán tour.

VÌ SAO PHẢI CÓ PHÉP THỬ CHO ĐÚNG CHỖ NÀY. Nâng phạm vi là sửa một chuỗi — mười giây, không đỏ
một hàng rào nào, và không ai thấy. Hậu quả thì không rút lại được: lời của khách đã nằm trên
internet. Một dòng mã rẻ như thế mà hậu quả đắt như thế thì phải có người canh.
"""
import sys
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from app.services import dong_y as DY                      # noqa: E402


class _BanGhi:
    """Bản ghi đồng ý giả — chỉ mang đúng những cột `cong_khai_duoc()` đọc.

    KHÔNG dựng cơ sở dữ liệu: hàm đang đo là một hàm thuần, và một phép thử phải hỏng vì đúng
    thứ nó đo, không hỏng vì một cái bảng nào đó đổi cột.
    """

    def __init__(self, pham_vi, tra_loi="co", rut_luc=None, duyet_luc=datetime(2026, 11, 1),
                 duyet_ket_qua="dang"):
        self.pham_vi = pham_vi
        self.tra_loi = tra_loi
        self.rut_luc = rut_luc
        self.duyet_luc = duyet_luc
        self.duyet_ket_qua = duyet_ket_qua


# ── 1 · HAI PHẠM VI PHẢI KHÁC NHAU, VÀ KHÁC ĐÚNG Ở CHỖ NÀY ───────────────────────────────────

def test_dong_y_cu_KHONG_dang_duoc_tren_trang_tour():
    """Đây là phép thử quan trọng nhất của tệp.

    Đánh giá thu trước 13/11/2026 được hỏi bằng câu «đăng trên hồ sơ hướng dẫn viên tại VTOS».
    Trang bán tour là chỗ khác, rộng hơn. Dùng lại lời đồng ý ấy là dùng ra ngoài điều đã hỏi.
    """
    cu = _BanGhi(DY.PHAM_VI)
    assert DY.cong_khai_duoc(cu, "trang_tour") is False


def test_dong_y_cu_VAN_dang_duoc_tren_ho_so_hdv():
    """Siết chỗ mới KHÔNG được làm hỏng chỗ cũ — khách đã đồng ý đúng chỗ ấy."""
    cu = _BanGhi(DY.PHAM_VI)
    assert DY.cong_khai_duoc(cu, "ho_so_hdv") is True


def test_khong_truyen_noi_thi_giu_nguyen_hanh_vi_cu():
    """Mọi cửa viết trước đợt này gọi `cong_khai_duoc(r)` không kèm `noi`.

    Chúng đều đang hỏi về hồ sơ hướng dẫn viên. Mặc định phải đưa đúng câu trả lời cũ, nếu không
    thì đợt này âm thầm gỡ nhận xét khỏi hồ sơ hướng dẫn viên — sửa một lỗi, tạo một lỗi khác.
    """
    assert DY.cong_khai_duoc(_BanGhi(DY.PHAM_VI)) is True


def test_dong_y_moi_dang_duoc_ca_hai_cho():
    moi = _BanGhi(DY.PHAM_VI_2)
    assert DY.cong_khai_duoc(moi, "ho_so_hdv") is True
    assert DY.cong_khai_duoc(moi, "trang_tour") is True


# ── 2 · BỐN ĐIỀU KIỆN CŨ VẪN PHẢI CHẶN, Ở CẢ HAI CHỖ ─────────────────────────────────────────

def test_rut_roi_thi_khong_cho_nao_dang_duoc():
    rut = _BanGhi(DY.PHAM_VI_2, rut_luc=datetime(2026, 11, 12))
    assert DY.cong_khai_duoc(rut, "ho_so_hdv") is False
    assert DY.cong_khai_duoc(rut, "trang_tour") is False


def test_tra_loi_khong_thi_khong_cho_nao_dang_duoc():
    k = _BanGhi(DY.PHAM_VI_2, tra_loi="khong")
    assert DY.cong_khai_duoc(k, "trang_tour") is False


def test_chua_duyet_thi_chua_dang():
    chua = _BanGhi(DY.PHAM_VI_2, duyet_luc=None, duyet_ket_qua="")
    assert DY.cong_khai_duoc(chua, "trang_tour") is False


def test_duyet_khong_dang_thi_khong_dang():
    kh = _BanGhi(DY.PHAM_VI_2, duyet_ket_qua="khong_dang")
    assert DY.cong_khai_duoc(kh, "trang_tour") is False


def test_khong_co_ban_ghi_thi_khong_dang():
    assert DY.cong_khai_duoc(None, "trang_tour") is False


# ── 3 · HAI CÁI BẪY ──────────────────────────────────────────────────────────────────────────

def test_pham_vi_la_thi_KHONG_dang():
    """Dữ liệu cũ, hoặc ai đó gõ tay vào cơ sở dữ liệu.

    Không biết lời đồng ý ấy cho phép những đâu thì câu trả lời duy nhất đúng là «không». Mặc
    định của `.get` phải là tuple RỖNG, không phải «cho qua».
    """
    assert DY.cong_khai_duoc(_BanGhi("mot_pham_vi_la_hoac"), "trang_tour") is False
    assert DY.cong_khai_duoc(_BanGhi(""), "ho_so_hdv") is False


def test_noi_la_thi_KHONG_dang():
    """Gõ nhầm tên chỗ đăng («trang-tour» thay vì «trang_tour») phải ra KHÔNG, không ra có."""
    assert DY.cong_khai_duoc(_BanGhi(DY.PHAM_VI_2), "trang-tour") is False
    assert DY.cong_khai_duoc(_BanGhi(DY.PHAM_VI_2), "") is False


# ── 4 · CÂU HỎI PHẢI NÓI ĐÚNG CHỖ NÓ XIN ─────────────────────────────────────────────────────

def test_cau_hoi_moi_co_nhac_trang_ban_tour():
    """Câu hỏi phải nêu ĐÍCH DANH chỗ sẽ đăng.

    `cau_hoi` được chép nguyên văn vào từng bản ghi để sáu tháng sau còn chứng minh được khách
    đã đồng ý với điều gì. Một câu hỏi không nói rõ chỗ thì bản ghi ấy không chứng minh được gì.
    """
    assert "kh.vietourist.vn" in DY.CAU_HOI_2
    assert "hướng dẫn viên" in DY.CAU_HOI_2


def test_cau_hoi_moi_van_hua_khong_kem_ten():
    """Lời hứa che danh tính không được rơi rụng khi mở rộng chỗ đăng."""
    assert "không kèm tên và thông tin liên hệ" in DY.CAU_HOI_2


def test_cau_hoi_cu_khong_bi_sua_mot_chu():
    """Câu cũ là nguyên văn Chủ tịch đưa 16/10/2026, và các bản ghi cũ đã chép nó.

    Sửa nó bây giờ là làm sai lệch bằng chứng của những lời đồng ý đã thu.
    """
    assert DY.CAU_HOI == ("Anh/chị có đồng ý đăng công khai nhận xét này trên hồ sơ hướng dẫn "
                          "viên tại VTOS, không kèm tên và thông tin liên hệ của anh/chị không?")


def test_hai_pham_vi_khong_trung_ten():
    assert DY.PHAM_VI != DY.PHAM_VI_2
    assert set(DY.NOI_CHO_PHEP) == {DY.PHAM_VI, DY.PHAM_VI_2}
