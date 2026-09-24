"""TC-84 · KHUNG MỞ RA NGOÀI TẦM NHÌN — "bấm không ăn" lần thứ hai của cùng một màn hình.

Anh Tuấn báo 25/9/2026: "a bấm vào nút gộp, xóa, sửa nhưng ko ăn". Màn hình có đủ ba nút, bấm
không báo lỗi gì, và không có gì xảy ra.

KHÔNG có gì hỏng ở nút. `moSua` là một lệnh đặt trạng thái thuần, không gọi máy chủ, không thể
"không chạy" — khung Sửa CHẮC CHẮN đã mở mỗi lần anh bấm. Cái hỏng là chỗ nó mở ra: ba khung Xem
trước / Sửa / Xoá được vẽ SAU bảng tài khoản trùng, mà bảng ấy cao 8 dòng. Trên điện thoại, khung
mở ở dưới màn hình một quãng dài. Người bấm thấy màn hình đứng im và kết luận nút hỏng — kết luận
hợp lý, vì từ chỗ họ ngồi thì không có cách nào phân biệt "nút không chạy" với "nút chạy mà không
thấy".

ĐÂY LÀ LẦN THỨ HAI cùng một màn hình bị báo đúng ba chữ "bấm không ăn". Lần đầu (24/9, dẫn tới
TC-83) là nút Gộp thật sự không làm gì, vì tài khoản thừa rỗng trơn nên bước xem trước trả về 0
dòng và không có hành động nào tiếp theo. Hai nguyên nhân khác hẳn nhau, một triệu chứng. Ghi cả
hai ở đây vì lần thứ ba mà lại có người đi sửa đúng chỗ đã sửa rồi thì phí một vòng.

CÁCH SỬA, VÀ CÁCH KHÔNG SỬA. Không dời ba khung lên trên bảng: khung mở ra TỪ MỘT DÒNG cụ thể,
người đọc nó phải còn thấy dòng nào đang được nói tới. Giữ nguyên thứ tự, cuộn khung vừa mở vào
tầm nhìn. Cách ấy giữ được cả hai điều.

PHÉP THỬ NÀY CANH BỐN CHỖ, và chúng đều là chỗ dễ mất im lặng khi ai đó sửa lại bố cục:

 1. CÓ LỆNH CUỘN, và nó chạy khi một trong ba khung mở — không phải chỉ một khung.
 2. BA KHUNG NẰM TRONG ĐÚNG Ô ĐƯỢC CUỘN TỚI. Một khung để lọt ra ngoài ô ấy là một khung lại mở
    ngoài tầm nhìn, mà phép thử canh lệnh cuộn thì vẫn xanh.
 3. BA KHUNG VẪN Ở SAU BẢNG. Nếu mai này có người dời chúng lên trước bảng, dòng đang nói tới
    biến mất khỏi màn hình — đó là đổi một lỗi lấy một lỗi khác, và phải thấy dòng này khi làm.
 4. BA CỬA MỞ KHUNG VẪN CÒN. Bản vá chỉ được thêm đường cuộn, không được đụng vào ba nút.
"""
from pathlib import Path

TRANG = Path(__file__).resolve().parents[2] / "web" / "app" / "gop-tai-khoan" / "page.tsx"


def _ma() -> str:
    return TRANG.read_text(encoding="utf-8")


def test_tc84_1_co_lenh_cuon_va_chay_cho_ca_ba_khung():
    ma = _ma()
    assert "useRef" in ma, "phải nhập useRef thì mới trỏ được tới ô chứa ba khung"
    assert "khungRef" in ma, "phải có một ô được đặt tên để cuộn tới"
    assert "scrollIntoView" in ma, "mở khung mà không cuộn tới thì người dùng vẫn không thấy gì"

    # Lệnh cuộn phải phụ thuộc vào CẢ BA trạng thái. Thiếu một cái là đúng một nút lại "không ăn".
    sau = ma[ma.index("scrollIntoView"):]
    phu_thuoc = sau[: sau.index("]") + 1]
    for ten in ("xt", "sua", "xoa"):
        assert ten in phu_thuoc, f"lệnh cuộn không chạy lại khi {ten} đổi – nút ấy vẫn sẽ 'không ăn'"


def test_tc84_2_ba_khung_nam_trong_o_duoc_cuon_toi():
    ma = _ma()
    mo_o = ma.index("ref={khungRef}")
    dong_o = ma.index("{/* ───────────── BIA MỘ ─────────────", mo_o)
    trong_o = ma[mo_o:dong_o]
    for khung, nhan in (("{xt &&", "Xem trước gộp"), ("{sua &&", "Sửa hồ sơ"), ("{xoa &&", "Xoá")):
        assert khung in trong_o, f"khung {nhan} nằm ngoài ô được cuộn tới – nó sẽ lại mở ngoài tầm nhìn"


def test_tc84_3_ba_khung_van_o_sau_bang():
    """Xem ghi chú đầu tệp: dời khung lên trước bảng là đổi một lỗi lấy một lỗi khác."""
    ma = _ma()
    assert ma.index("Những người có nhiều hơn một tài khoản") < ma.index("ref={khungRef}")


def test_tc84_4_ba_cua_mo_khung_van_con():
    ma = _ma()
    for cua in ("onClick={() => xem(", "onClick={() => moSua(", "onClick={() => moXoa("):
        assert cua in ma, f"mất cửa mở khung: {cua}"
