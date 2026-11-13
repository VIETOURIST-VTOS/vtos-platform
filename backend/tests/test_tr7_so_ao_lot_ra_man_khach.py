# -*- coding: utf-8 -*-
"""TR-7b · 13/11/2026 — SỐ GIỮ CHỖ KHÔNG ĐƯỢC LỌT RA MÀN KHÁCH.

KS-71 mục G4 đo được trên bản chạy thật: trang chi tiết in «Chi phí phụ thu phòng đơn:
00.000 VNĐ/khách». Số ấy là chỗ trống của người soạn bài trên vietourist.com.vn. Nội dung tour
đọc thẳng từ web cũ (Chủ tịch chốt mục 12 của KS-71), nên lỗi soạn bài bên ấy chảy ra màn khách.

VÌ SAO TỆP NÀY TỒN TẠI, VÀ VÌ SAO NÓ CANH CẢ HAI CHIỀU.

Bản viết ĐẦU TIÊN của bộ lọc bắt thẳng mẫu «0{1,3}.000». Nó khớp luôn phần đuôi của
«1.000.000» — tức một tour giá đúng một triệu sẽ bị GIẤU khỏi màn khách. Một bộ lọc dựng để
chặn số giả mà lại xoá số thật thì tệ hơn hẳn việc không lọc, vì nó hỏng âm thầm: không ai thấy
dòng biến mất. Bảng dưới đây bắt được lỗi ấy trước khi mã rời máy, nên nó ở lại đây mãi.

Hai chiều phải cùng đúng:
  · số giả PHẢI bị chặn — nếu không, lòng tin vào cả trang hỏng;
  · số thật PHẢI đi qua — kể cả 1.000.000, 10.000.000, và số điện thoại dạng 0909.000.111.
"""
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from app.services import tour_online as TR                     # noqa: E402


# ── 1 · SỐ GIẢ PHẢI BỊ CHẶN ──────────────────────────────────────────────────────────────────

def test_chan_dung_dong_KS_71_do_duoc():
    """Nguyên văn dòng đã lọt ra màn khách, đo 12/11/2026."""
    assert TR.co_so_ao("Chi phí phụ thu phòng đơn: 00.000 VNĐ/khách") is True


def test_chan_moi_dang_so_toan_so_khong():
    for s in ("Phụ thu phòng đơn: 000.000 VNĐ", "Giá 0.000 VNĐ", "Phụ thu 0,000 VND",
              "Trẻ em: 00.000", "Phụ thu 000.000.000 đ"):
        assert TR.co_so_ao(s) is True, s


def test_chan_cho_trong_chua_dien():
    for s in ("Phụ thu: X.XXX VNĐ", "Phụ thu: x.xxx", "Phụ thu phòng đơn: ______ VNĐ"):
        assert TR.co_so_ao(s) is True, s


def test_mot_so_gia_trong_dong_la_du_de_chan():
    """Dòng có cả số thật lẫn số giả vẫn là dòng không đưa ra được: khách không biết tin số nào."""
    assert TR.co_so_ao("Phụ thu phòng đơn 00.000 và vé tham quan 250.000") is True


# ── 2 · SỐ THẬT PHẢI ĐI QUA — ĐÂY LÀ CHIỀU DỄ LÀM HỎNG ───────────────────────────────────────

def test_mot_trieu_KHONG_bi_coi_la_so_gia():
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA TỆP.

    Bản viết đầu của em chặn nhầm đúng dòng này. Một tour giá 1.000.000 là tour có thật, và
    giấu giá của nó đi là làm hỏng chính việc mình đang đi sửa.
    """
    assert TR.co_so_ao("Phụ thu 1.000.000 VNĐ") is False
    assert TR.co_so_ao("Giá tour: 1.000.000 đ/khách") is False


def test_cac_so_tien_that_khac_deu_qua():
    for s in ("Giá tour: 1.390.000 VNĐ/khách", "Phụ thu 10.000 VNĐ", "Bao gồm vé tham quan 250.000",
              "Giá 10.000.000 VNĐ", "Trẻ 2-11 tuổi: 1.000.000", "Giá từ 990.000"):
        assert TR.co_so_ao(s) is False, s


def test_so_dien_thoai_khong_bi_nham_la_so_gia():
    """0909.000.111 có cụm «000» nhưng không phải mọi chữ số đều là 0."""
    assert TR.co_so_ao("Hotline 0909.000.111") is False


def test_chu_khong_co_so_thi_khong_chan():
    for s in ("Khách sạn 3 sao", "Xe 45 chỗ", "Trẻ em dưới 5 tuổi: 0 VNĐ", "", None):
        assert TR.co_so_ao(s) is False, s


# ── 3 · BỘ LỌC DÒNG: GIỮ THỨ TỰ, ĐẾM ĐÚNG ───────────────────────────────────────────────────

def test_loc_giu_nguyen_thu_tu_va_dem_dung_so_dong_bo():
    goc = ["Vé tham quan", "Phụ thu phòng đơn: 00.000 VNĐ", "Bảo hiểm du lịch",
           "Phụ thu lễ: X.XXX", "Nước uống 2 chai/ngày"]
    sach, bo = TR._loc_so_ao(goc)
    assert sach == ["Vé tham quan", "Bảo hiểm du lịch", "Nước uống 2 chai/ngày"]
    assert bo == 2


def test_khong_co_so_gia_thi_khong_bo_dong_nao():
    goc = ["Vé tham quan", "Bảo hiểm du lịch"]
    sach, bo = TR._loc_so_ao(goc)
    assert sach == goc and bo == 0


def test_quy_dinh_loc_theo_tung_dong():
    qd = "Huỷ trước 7 ngày: mất 50% cọc\nPhụ thu phòng đơn: 00.000 VNĐ\nTrẻ dưới 5 tuổi miễn phí"
    sach, bo = TR._quy_dinh_sach(qd)
    assert "00.000" not in sach
    assert "Huỷ trước 7 ngày: mất 50% cọc" in sach
    assert "Trẻ dưới 5 tuổi miễn phí" in sach
    assert bo == 1


# ── 4 · LỌC RỒI PHẢI BÁO, KHÔNG ĐƯỢC GIẤU IM ────────────────────────────────────────────────

def test_co_nhan_thieu_noi_dung_cho_so_gia():
    """Giấu dòng khỏi khách mà không báo cho người của anh thì lỗi nằm im trên web cũ mãi mãi.

    Màn `/tour-online` in danh sách thiếu nội dung theo đúng bảng này.
    """
    assert "gia_ao" in TR.THIEU_ND
    assert TR.THIEU_ND["gia_ao"]


def test_bon_nhan_cu_khong_bi_dong_nao_mat_di():
    """Thêm nhãn mới không được làm rơi nhãn cũ — màn hình đọc thẳng bảng này."""
    for k in ("anh", "lich", "bao_gom", "tre_em"):
        assert k in TR.THIEU_ND
