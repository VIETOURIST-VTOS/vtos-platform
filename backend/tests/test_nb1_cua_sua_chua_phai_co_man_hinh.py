"""NB1 – cửa SỬA CHỮA cũng phải có màn hình, không chỉ cửa nhập số liệu.

VIỆC NÀY SINH RA TỪ MỘT LẦN ĐO TRÊN HỆ THẬT, 07/10/2026. Robot Vietrip vẫn chạy hai lượt mỗi ngày và
vẫn kéo được tour, phiếu thu, chi NCC — nhưng cửa booking bên Vietrip trả rỗng suốt 12 lượt liền
(`bookings: 0` ở cả 12 dòng nhật ký `dong_bo_vietrip_tu_dong`). Hậu quả: 364 phiếu treo, TẤT CẢ cùng
một lý do "chưa có booking" — 299 phiếu thu 4.567.266.609 đ cộng 65 phiếu chi. Tiền khách đã về tài
khoản mà không thành doanh thu.

VTOS ĐÃ CÓ SẴN CỬA VÁ cho đúng tình huống ấy từ 26/9: `nap-bu/booking-cho-phieu-thu`, lần theo id của
những booking mà phiếu đang trỏ tới. Nhưng `grep -rn "nap-bu" web/` trả về RỖNG — không một màn hình
nào gọi tới nó. Cửa nằm trên máy chủ, người phát hiện ra hỏng hóc không với tới được, và suốt mười
một ngày không ai bấm được một nút nào.

VÌ SAO HÀNG RÀO CŨ KHÔNG BẮT ĐƯỢC. Kho đã có hai hàng rào gần giống:
  · `test_ks_cua_nhap` (CN1) hỏi "bảng này có cửa cho người ĐƯA SỐ LIỆU vào chưa" – cửa nạp bù không
    đưa số liệu mới nào vào, nó chỉ ánh xạ lại cái đã kéo về, nên nằm ngoài tầm;
  · `test_p11` hỏi "mục đã KHAI QUYỀN có trang chưa" – cửa nạp bù không phải một mục màn hình, nó là
    một nút nằm trong màn hình đã có, nên cũng nằm ngoài tầm.
Giữa hai hàng rào ấy có một khe, và một cửa sửa chữa lọt qua khe đó đúng mười một ngày.

RANH GIỚI 09/9/2026 nói: mỗi con số cần một cửa nhập hoặc cửa tải cho người dùng; không có cửa thì
đó là việc CÒN THIẾU. Tệp này nối dài đúng câu ấy sang cửa sửa chữa: có cửa trên máy chủ mà không có
nút trên màn hình thì cửa ấy CHƯA XONG.

TỆP NÀY ĐỌC MÃ NGUỒN GIAO DIỆN như một chuỗi chữ, và nói thẳng ra để không ai tin nó quá mức: nó
không chạy được React, nên nó canh "màn hình CÓ GỌI đường dẫn này" chứ không canh "nút ấy chạy đúng".
Phần chạy đúng là việc của người bấm thử.
"""
import os
import pathlib
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_nb1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_nb1.db", "test_nb1.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

from app.api.v1 import vietrip as VR  # noqa: E402
from app.main import app  # noqa: E402

GOC = pathlib.Path(__file__).resolve().parents[2]
WEB = GOC / "web"
MH_VIETRIP = WEB / "app" / "vietrip" / "page.tsx"
CUA_NAP_BU = "/import/vietrip/nap-bu/booking-cho-phieu-thu"

# Dấu hiệu một đường dẫn là cửa SỬA CHỮA: người bấm để gỡ một chỗ đã hỏng, không phải việc hằng ngày.
DAU_HIEU = ("/nap-bu/", "/repair-", "/dong-so-theo-buoc")

# Cửa sửa chữa CHƯA có màn hình, kèm lý do. Danh sách này phải KHỚP TỪNG DÒNG với thực tế: vá xong
# một cửa thì phải xoá dòng của nó ra khỏi đây, và thêm một cửa mới mà quên dựng nút thì đỏ ngay.
# Cố ý KHÔNG ghi hạn: hạn cho từng cửa là việc Chủ tịch định, không phải việc phép thử bịa ra. Cái
# phép thử canh được là danh sách KHÔNG DÀI THÊM trong im lặng.
CHUA_CO_MAN_HINH: dict[str, str] = {
    "/import/vietrip/repair-budget":        "dựng lại dự toán suy ra từ sản phẩm – chưa ai hỏi tới",
    "/import/vietrip/repair-phap-nhan":     "gán pháp nhân cho chuyến còn rỗng – chưa ai hỏi tới",
    "/import/vietrip/dong-so-theo-buoc":    "đóng số theo bước Vietrip – chưa ai hỏi tới",
    "/import/vietrip/nap-bu/tour":          "nạp bù tour còn thiếu – chưa ai hỏi tới",
    "/import/vietrip/nap-bu/quyet-toan":    "nạp bù quyết toán theo lô – chưa ai hỏi tới",
}


def _cua_sua_chua() -> list[str]:
    """Mọi đường dẫn GHI mang dấu hiệu cửa sửa chữa, đọc thẳng từ bảng đường dẫn của máy chủ."""
    ra = set()
    for r in app.routes:
        p = str(getattr(r, "path", ""))
        if not p.startswith("/api/v1/import/vietrip"):
            continue
        if not (set(getattr(r, "methods", []) or []) & {"POST", "PUT", "PATCH", "DELETE"}):
            continue
        if any(d in p for d in DAU_HIEU):
            ra.add(p[len("/api/v1"):])
    return sorted(ra)


def _man_hinh_nao_goi(duong_dan: str) -> list[str]:
    """Những tệp giao diện có nhắc tới đường dẫn này. Tìm bằng chuỗi vì client gọi `api("<đường dẫn>")`."""
    ra = []
    for p in WEB.rglob("*.tsx"):
        if "node_modules" in p.parts:
            continue
        if duong_dan in p.read_text(encoding="utf-8"):
            ra.append(str(p.relative_to(GOC)))
    return sorted(ra)


def test_nb1_1_cua_nap_bu_booking_da_co_man_hinh_goi_toi():
    """Việc chính của vòng này. Đây cũng là phép thử sẽ đỏ nếu một ngày ai gỡ nút ấy đi."""
    assert CUA_NAP_BU in _cua_sua_chua(), "Cửa nạp bù booking biến mất khỏi máy chủ"
    goi = _man_hinh_nao_goi(CUA_NAP_BU)
    assert goi, ("Cửa nạp bù booking cho phiếu thu không màn hình nào gọi tới. Có cửa trên máy chủ mà "
                 "người phải dùng không với tới được thì theo ranh giới 09/9/2026 đó là việc CÒN THIẾU.")


def test_nb1_2_danh_sach_cua_chua_co_man_hinh_phai_khop_tung_dong():
    """Hàng rào thật nằm ở đây, không ở phép thử trên.

    Canh HAI chiều cùng lúc: thêm một cửa sửa chữa mới mà quên dựng nút thì nó hiện ra ngoài danh
    sách và phép thử đỏ; vá xong một cửa mà quên xoá dòng khai thì cũng đỏ. Một danh sách ngoại lệ
    không ai dọn là một danh sách dài mãi, và tới lúc ấy nó thôi nói lên điều gì.
    """
    thieu = {d for d in _cua_sua_chua() if not _man_hinh_nao_goi(d)}
    khai = set(CHUA_CO_MAN_HINH)
    assert thieu == khai, (
        f"Danh sách cửa sửa chữa chưa có màn hình không khớp.\n"
        f"  Thiếu mà CHƯA KHAI (dựng nút, hoặc khai vào CHUA_CO_MAN_HINH kèm lý do): {sorted(thieu - khai)}\n"
        f"  KHAI MÀ ĐÃ CÓ màn hình (xoá dòng khai đi): {sorted(khai - thieu)}")


def test_nb1_3_nut_phai_goi_lap_theo_moc_cua_may_chu():
    """Gọi MỘT PHÁT là hỏng theo kiểu khó thấy nhất: nút chạy, báo thành công, và để lại phần lớn
    phiếu vẫn treo.

    Cửa máy chủ CỐ Ý chia lô — mỗi lượt lật tối đa ba trang Vietrip, rồi trả `bat_dau_tiep` để người
    gọi lật tiếp (bản đầu lật 60 trang một lượt và Render giết máy chủ giữa chừng vì nhịp tim quá 5
    giây). Màn hình phải ĐỌC cái mốc ấy. Phép thử canh đúng chữ `bat_dau_tiep`: đổi tên nó là đổi
    giao kèo của cửa, lúc ấy đỏ ở đây là đỏ đúng chỗ.
    """
    ma = MH_VIETRIP.read_text(encoding="utf-8")
    assert "bat_dau_tiep" in ma, ("Màn hình không đọc `bat_dau_tiep` – nghĩa là chỉ gọi một lượt rồi "
                                  "dừng, trong khi cửa máy chủ chia lô và chờ được gọi lại.")
    assert "bat_dau=" in ma, "Màn hình không truyền `bat_dau` – lượt sau sẽ lật lại đúng trang đầu."


def test_nb1_4_vai_tro_tren_man_hinh_khop_dung_cua_may_chu():
    """Giấu nút hẹp hơn quyền thật không chặn được ai – nó chỉ làm đúng người cần bấm không thấy nút.

    Đó chính là cái đã xảy ra: người đo ra hỏng hóc là Chủ tịch, mà hai nút cũ trên màn hình này chỉ
    mở cho `cntt` và `ketoan`. Phép thử buộc danh sách vai của NÚT NẠP BÙ khớp từng chữ với
    `SYNC_ROLES` của cửa máy chủ, nên hai bên không trôi ra xa nhau trong im lặng.
    """
    ma = MH_VIETRIP.read_text(encoding="utf-8")
    m = re.search(r"const\s+NAP_BU_VAI\s*=\s*\[([^\]]*)\]", ma)
    assert m, "Không tìm thấy `NAP_BU_VAI` trên màn hình Vietrip"
    tren_mh = sorted(x.strip().strip('"\'') for x in m.group(1).split(",") if x.strip())
    assert tren_mh == sorted(VR.SYNC_ROLES), (
        f"Vai bấm nút nạp bù trên màn hình {tren_mh} khác SYNC_ROLES của máy chủ {sorted(VR.SYNC_ROLES)}")
