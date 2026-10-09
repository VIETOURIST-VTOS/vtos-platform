"""PD-1 · Phạm vi P.TGĐ Đoàn: chuỗi bán hàng phải đủ ba màn hình (Chủ tịch chốt 09/10/2026).

CHỖ LỆCH TÌM RA. Hai P.TGĐ lệch nhau ở 11 màn hình; chín cái là màn hình Marketing và lệch đúng.
Hai cái còn lại nằm NGOÀI Marketing, và cả hai thuộc chuỗi bán hàng:

  · `/hop-dong-khach` — `nv_kd`, một NHÂN VIÊN bán hàng, xem được hợp đồng khách; P.TGĐ phụ trách
    mảng Đoàn thì không. Hợp đồng là căn cứ ghi nhận doanh thu của chính mảng ông chịu trách nhiệm.
  · `/bang-gia` — chính sách giá niêm yết mà mọi báo giá của mảng Đoàn phải theo. Ông duyệt báo
    giá (đã có `/bao-gia`) mà không đọc được con số gốc.

PHÉP THỬ NẶNG NHẤT KHÔNG PHẢI HAI DÒNG TRÊN — nó là điều kiện thứ ba: MỞ MÀN HÌNH KHÔNG PHẢI MỞ
QUYỀN. Ba màn hình của chuỗi bán hàng dùng CHUNG đúng một tiền tố API, mà P.TGĐ Đoàn đã có sẵn từ
`/bao-gia`. Nhờ thế lần nới này không chạm một quyền máy chủ nào, và số phạm vi ở `test_p2` đứng
yên. Ngày nào ai đó tách tiền tố của một trong ba màn hình ra khác nhau thì câu ấy HẾT ĐÚNG — và
lúc ấy mở màn hình sẽ thật sự là nới quyền, phải đếm lại và phải có người quyết. Phép thử dưới
đây đỏ đúng vào ngày đó.

CÁI KHÔNG VIẾT LẠI Ở ĐÂY, và lý do. Bản đầu của tệp này có thêm một phép thử hỏi "mọi màn hình
P.TGĐ Đoàn mở được đều có đủ tiền tố API đằng sau không" — tức bệnh "màn hình mở mà cửa trả 403"
mà vòng DH-1 đi chữa. Bỏ đi, vì `test_p2.test_moi_man_hinh_tren_menu_deu_co_du_api_dang_sau` đã
hỏi ĐÚNG câu ấy cho MỌI vai và MỌI màn hình. Chép lại ở đây là dựng cái đầu thứ hai cho một luật
đã có chủ — đúng thứ mấy vòng hôm nay đi gom lại. Một luật, một chỗ canh.
"""
import pytest

from app.services import access as AC

CHUOI_BAN_HANG = ("/bao-gia", "/bang-gia", "/hop-dong-khach")


def test_ptgd_doan_doc_duoc_ca_ba_man_hinh_cua_chuoi_ban_hang():
    thieu = [m for m in CHUOI_BAN_HANG if "ptgd_doan" not in AC.MENU_ROLES[m]]
    assert not thieu, (
        f"P.TGĐ Đoàn không mở được {thieu}. Chủ tịch chốt 09/10/2026 mở cả chuỗi: duyệt báo giá "
        "mà không đọc được bảng giá, chịu trách nhiệm doanh thu mà không đọc được hợp đồng, thì "
        "chữ ký ấy ký trên cái gì.")


def test_nhan_vien_ban_hang_xem_duoc_thi_nguoi_phu_trach_mang_cung_phai_xem_duoc():
    """Chỗ lệch rõ nhất của cả bảng, viết thành một câu hỏi thay vì một danh sách tên vai."""
    hd = AC.MENU_ROLES["/hop-dong-khach"]
    if "nv_kd" in hd:
        assert "ptgd_doan" in hd and "ptgd_mkt" in hd, (
            "Hợp đồng khách mở cho nhân viên bán hàng mà không mở cho P.TGĐ phụ trách mảng — "
            "một bảng phân quyền nói ngược chuỗi chỉ huy thì người đọc thôi tin nó.")


def test_mo_man_hinh_KHONG_PHAI_mo_quyen_may_chu():
    """Điều kiện khiến vòng này rẻ, và là điều kiện sẽ hết đúng trước nhất.

    Ba màn hình dùng chung một tiền tố API nên thêm tên vai vào MENU_ROLES không nới một quyền
    máy chủ nào. Tách tiền tố ra là câu ấy hết đúng.
    """
    tien_to = {m: tuple(AC.MAN_HINH_API.get(m, ())) for m in CHUOI_BAN_HANG}
    rieng = set(tien_to.values())
    assert len(rieng) == 1, (
        "Ba màn hình chuỗi bán hàng không còn chung một tiền tố API: "
        f"{tien_to}. Lúc này mở màn hình THẬT SỰ là nới quyền máy chủ — phải đếm lại bảng phạm vi "
        "ở `test_p2` và phải có người quyết, không được coi đây là một dòng hiển thị.")
    assert rieng == {("/api/v1/ban-hang",)}, f"Tiền tố đổi rồi: {rieng}"
