# -*- coding: utf-8 -*-
"""Cửa nạp cho quyết toán tour chi tiết – bộ nạp thứ hai của cùng một phòng.

Bộ nạp mà không có cửa thì bằng không: mã đọc được tệp nhưng không màn hình nào gọi tới, và người
Điều hành vẫn gửi Excel qua Zalo. Đây là dạng thiếu mà phép thử chức năng không bắt được, vì từng
hàm đều chạy đúng – chỉ có điều không ai gọi được chúng.
"""
import pytest

from app.services import intake_phong_ban_3 as PB3


def _c(key, ten, bat_buoc=False, kieu="chu", vi_du="", ghi_chu="", chon=None, **kw):
    """Bản rút gọn của hàm khai cột trong intake.py – đủ để đọc khai báo mà không kéo cả khung nạp."""
    return {"key": key, "ten": ten, "bat_buoc": bat_buoc, "kieu": kieu,
            "vi_du": vi_du, "ghi_chu": ghi_chu, "chon": chon}


BO = PB3.bo_nap(_c)["quyet_toan_tour_chi_tiet"]


def test_bo_nap_khai_du_ba_ham_cua_che_do_lo():
    """Chế độ lô cần đủ doc_tep, kiem_lo, nap_lo. Thiếu một cái là màn hình gọi vào rỗng.

    Khung nạp không kiểm chuyện này lúc khởi động – nó chỉ nổ vào đúng lúc có người bấm nạp, tức là
    lúc tệ nhất.
    """
    assert BO["lo"] is True
    for ham in ("doc_tep", "kiem_lo", "nap_lo"):
        assert callable(BO[ham]), f"thiếu {ham}"
    assert BO["khoa_chong_trung"] == "Mã tour"


def test_doc_tep_tra_ve_MOT_ban_khong_phai_nhieu_dong_phang():
    """Một tệp là MỘT chuyến. Ép thành nhiều dòng phẳng là mất cấu trúc bốn mặt.

    Và mất đúng những chỗ chỉ lộ ra khi đặt bốn mặt cạnh nhau – ngày khởi hành lệch giữa các sheet,
    HDV chi nhiều hơn chiết tính. Cả hai đều vô hình nếu chỉ còn một bảng phẳng.
    """
    from tests.test_lop2_quyet_toan_tour import _tep
    rows = BO["doc_tep"](_tep(), "thu.xlsx")
    assert isinstance(rows, list) and len(rows) == 1
    ban = rows[0]
    for mat in ("dong", "ctt", "hdv_chi", "dt"):
        assert mat in ban, f"thiếu mặt {mat}"
    # Doanh thu phải nằm phẳng ở gốc, nếu không nhật ký nạp ghi tổng tiền của tệp bằng 0 và bộ kiểm
    # K5 báo "lô không có cột tiền" ở mọi lần nạp đi qua đường này.
    assert ban["doanh_thu"] and ban["doanh_thu"] > 0
    assert ban["ma_tour"] == "NT001.03100726"


def test_moi_cot_da_khai_deu_co_mat_phang_trong_ban_doc_ra():
    """Khai tám cột thì bản đọc ra phải có đủ tám – bảng xem trước dựng theo đúng danh sách khai.

    Ngày 10/9 chỉ có 'doanh_thu' và 'ma_tour' được để phẳng. Chạy thử trên tệp Nha Trang thật thì
    bảng xem trước hiện tên tour, ngày đi, ngày về, số khách, HDV, biển số đều RỖNG – trong khi bộ
    đọc đã đọc đủ cả sáu ô ấy ở đầu sheet QT. Người nạp nhìn bảng trống thì kết luận tệp hỏng và bỏ
    đi, đúng vào lúc bộ kiểm vừa đọc xong xuôi. Phép thử chức năng cũ không bắt được vì nó soi kết
    quả GHI VÀO SỔ, mà sổ thì lấy số từ kiem() chứ không lấy từ mấy ô phẳng này.
    """
    from tests.test_lop2_quyet_toan_tour import _tep
    ban = BO["doc_tep"](_tep(), "thu.xlsx")[0]
    for c in BO["cot"]:
        assert c["key"] in ban, f"cột đã khai nhưng bản đọc ra không có: {c['key']}"
    assert ban["ten_chuong_trinh"], "tên chương trình không được rỗng khi tệp có ô ấy"
    assert ban["so_khach"], "số khách không được rỗng khi tệp có ô ấy"


def test_cot_khai_bao_co_doanh_thu_kieu_tien():
    """Cột tiền phải được khai đúng kiểu, vì nhật ký nạp cộng tổng tiền của tệp theo khai báo này."""
    cot_tien = [c for c in BO["cot"] if c["kieu"] == "tien"]
    assert [c["key"] for c in cot_tien] == ["doanh_thu"]


def test_ai_nap_duoc_va_ke_toan_phai_co_trong_do():
    """Kế toán nạp được vì sheet chiết tính mang số hoá đơn và MST nhà cung cấp.

    Đó là dữ liệu của Kế toán chứ không phải của Điều hành: nó đi vào bảng kê thuế GTGT đầu vào.
    Bỏ Kế toán ra khỏi cửa này thì họ phải nhờ Điều hành nạp hộ, và nhật ký ghi sai tên người chịu
    trách nhiệm về con số – đúng thứ mà cả thiết kế phân quyền đang cố tránh.
    """
    vt = PB3.vai_tro(("chutich", "tgd", "cntt"))["quyet_toan_tour_chi_tiet"]
    assert "ketoan" in vt
    assert "tp_dh" in vt and "nv_dh" in vt
    assert "nv_kd" not in vt, "Kinh doanh không nạp quyết toán – đó là sổ của phòng khác"


def test_la_bo_nap_cham_tien_nen_cua_tai_tep_hep_hon_cua_nhap_tay():
    """Quy tắc P4: nhập tay sai một dòng thì sửa một dòng, tải tệp sai là cả tệp vào bảng cùng lúc.

    Bộ nạp này chạm thẳng vào tiền (doanh thu và giá vốn của một chuyến), nên phải nằm trong danh
    sách chạm tiền – khi ấy nhân viên nhập tay được mà không tải tệp hàng loạt được.
    """
    assert "quyet_toan_tour_chi_tiet" in PB3.CHAM_TIEN


def test_khong_trung_ten_voi_bo_nap_quyet_toan_thang():
    """Hai bộ nạp phải là hai cửa riêng, không phải một cửa đoán hai hình dạng tệp.

    quyet_toan_tour nhận tệp CẢ THÁNG (mỗi điều hành viên một sheet, mỗi dòng một chuyến).
    quyet_toan_tour_chi_tiet nhận tệp MỘT chuyến (bốn sheet). Gộp lại thì bộ đọc phải đoán đang cầm
    loại nào, và đoán sai một lần là nạp tổng tháng vào chỗ dành cho một chuyến.
    """
    assert "quyet_toan_tour_chi_tiet" != "quyet_toan_tour"

    # Tệp này khai NHIỀU HƠN MỘT bộ nạp kể từ 11/9/2026, nên phép thử không còn chốt được bằng một
    # tên duy nhất. Điều cần giữ vẫn y nguyên: MỖI HÌNH DẠNG TỆP MỘT CỬA RIÊNG, không cửa nào phải
    # đoán mình đang cầm loại nào.
    #
    #   quyet_toan_tour         – tệp CẢ THÁNG, mỗi điều hành viên một sheet (ở tệp nạp khác)
    #   quyet_toan_tour_chi_tiet – tệp MỘT chuyến, bốn sheet theo mẫu cũ của điều hành
    #   mau_quyet_toan_tour      – tệp MỘT chuyến theo HAI MẪU CHUẨN Chủ tịch chốt 11/9 (trong nước /
    #                              nước ngoài); mẫu do máy sinh ra ở /quyet-toan-lop3/mau-trong
    #
    # Chốt danh sách ra đây để thêm cửa thứ tư là phải sửa dòng này – tức là phải nghĩ một lần nữa
    # xem cửa mới có thật sự là một hình dạng tệp khác không, hay chỉ là cửa cũ nhận thêm biến thể.
    KHAI = set(PB3.bo_nap(_c))
    assert KHAI == {"quyet_toan_tour_chi_tiet", "mau_quyet_toan_tour"}, \
        f"Có cửa nạp mới trong intake_phong_ban_3: {KHAI}. Thêm vào danh sách này kèm lý do, và nói rõ nó nhận hình dạng tệp nào."
    assert "quyet_toan_tour" not in KHAI, "Bộ nạp tệp cả tháng phải ở cửa khác, không gộp vào đây"

    # Mọi cửa trong tệp này đều thuộc Điều hành và đều CHẠM TIỀN – thiếu một trong hai khai báo thì
    # cửa lọt ra ngoài hàng rào mà không ai thấy.
    for ten in KHAI:
        assert PB3.PHONG_BAN[ten] == "dieu_hanh", f"{ten} chưa khai phòng ban"
        assert ten in PB3.CHAM_TIEN, f"{ten} chạm tiền nhưng chưa khai vào CHAM_TIEN"


def test_kiem_lo_khong_nhan_tep_co_nhieu_hon_mot_chuyen():
    """Hai chuyến trong một tệp là dấu hiệu người nạp chọn nhầm cửa – phải nói ra, không nạp bừa."""
    from app.services import quyet_toan_chi_tiet as QTCT
    with pytest.raises(ValueError, match="một chuyến"):
        QTCT._mot_ban([{"a": 1}, {"b": 2}])
    with pytest.raises(ValueError):
        QTCT._mot_ban([])
