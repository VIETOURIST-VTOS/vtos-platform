"""K12 – đối chiếu ma trận phân quyền với thư mục trang giao diện.

Đọc thẳng hai nguồn gốc: `access.MENU_ROLES` và `web/app/*/page.tsx`. KHÔNG đi qua tệp menu của giao
diện – menu là bản sao thứ ba, và một màn hình bị bỏ quên thường bị bỏ quên ở cả ba chỗ; đối chiếu hai
bản sao cùng thiếu thì lúc nào cũng khớp, lúc nào cũng xanh.

  MT1 khai quyền cho màn hình không tồn tại – đúng danh sách đã biết, thêm cái mới thì đỏ
  MT2 có màn hình mà không khai quyền – đúng danh sách đã biết, thêm cái mới thì đỏ
  MT3 dựng một màn hình mới không khai quyền thì bộ kiểm bắt được ngay (thử ngược, chiều nguy hiểm nhất)
  MT4 khai quyền cho một màn hình không có thật thì bộ kiểm bắt được (thử ngược chiều còn lại)
  MT5 mỗi ngoại lệ phải tự bảo vệ được, không phải danh sách để giấu việc
  MT6 bộ kiểm đã nối vào vòng quét của robot
  MT7 /kiem-soat khai đúng người quyết K1/K2 – chốt dứt điểm mâu thuẫn 07/9
"""
import os, sys, pathlib
os.environ["DATABASE_URL"] = "sqlite:///./test_mt.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_mt.db"): os.remove("test_mt.db")

from app.services import access as AC
from app.services import ks_ma_tran as MT

# Việc ĐANG MỞ, tính tới 08/9/2026. Robot đo được và mở việc; sửa là việc của người (P11/V8b), nên phép
# thử ghi nhận đúng hiện trạng thay vì đỏ mãi mãi – một phép thử đỏ thường trực là phép thử không ai đọc.
# Sửa xong một dòng thì phép thử đỏ và phải xoá dòng đó khỏi đây: đó là cách nó không bị bỏ quên.
KHAI_THIEU_MAN_HINH = ["ket-so"]        # menu dẫn tới trang không có
# Ba màn hình này KHÔNG khai trong MENU_ROLES mà khai qua MAN_HINH_MOI_NGUOI – chúng mở cho mọi tài
# khoản đăng nhập theo đúng thiết kế, và bộ dò này chỉ đọc MENU_ROLES nên vẫn kể tên chúng ra.
# phieu-luong vào danh sách ngày 08/9/2026 – màn hình phiếu lương của chính người đăng nhập.
MAN_HINH_THIEU_QUYEN = ["alerts", "phieu-luong", "reports"]


def test_mt1_khai_quyen_cho_man_hinh_khong_ton_tai():
    d = MT.doi_chieu()
    assert d["doc_duoc"], "không đọc được thư mục giao diện – phép thử này không kiểm được gì"
    assert d["khai_thieu_man_hinh"] == KHAI_THIEU_MAN_HINH, (
        "danh sách màn hình khai quyền mà không có trang đã đổi. Thêm mới thì phải sửa; "
        "sửa xong một cái thì xoá khỏi danh sách trong tệp phép thử này.")


def test_mt2_co_man_hinh_ma_khong_khai_quyen():
    """Chiều nguy hiểm hơn: quy ước là "trang không liệt kê = ai đăng nhập cũng thấy", nên quên khai
    KHÔNG khoá màn hình lại mà mở toang nó."""
    d = MT.doi_chieu()
    assert d["man_hinh_thieu_quyen"] == MAN_HINH_THIEU_QUYEN, (
        "có màn hình mới chưa khai quyền – theo quy ước hiện hành nó đang mở cho mọi tài khoản")


def test_mt3_dung_man_hinh_moi_khong_khai_quyen_thi_bat_duoc():
    """Thử ngược: tạo đúng một thư mục trang rồi xoá đi."""
    web = MT.thu_muc_web()
    assert web is not None
    moi = web / "man-hinh-thu-cua-robot"
    moi.mkdir(exist_ok=True)
    (moi / "page.tsx").write_text("export default function Page(){return null}", encoding="utf-8")
    try:
        d = MT.doi_chieu()
        assert "man-hinh-thu-cua-robot" in d["man_hinh_thieu_quyen"], \
            "dựng một màn hình mới không khai quyền mà bộ kiểm không thấy thì nó không canh gì cả"
    finally:
        (moi / "page.tsx").unlink(); moi.rmdir()
    assert MT.doi_chieu()["man_hinh_thieu_quyen"] == MAN_HINH_THIEU_QUYEN


def test_mt4_khai_quyen_cho_man_hinh_khong_co_that_thi_bat_duoc():
    goc = dict(AC.MENU_ROLES)
    AC.MENU_ROLES["/man-hinh-khong-co-that"] = ("chutich",)
    try:
        assert "man-hinh-khong-co-that" in MT.doi_chieu()["khai_thieu_man_hinh"]
    finally:
        AC.MENU_ROLES.clear(); AC.MENU_ROLES.update(goc)
    assert MT.doi_chieu()["khai_thieu_man_hinh"] == KHAI_THIEU_MAN_HINH


def test_mt5_moi_ngoai_le_phai_tu_bao_ve_duoc():
    """Danh sách ngoại lệ là chỗ dễ biến thành nơi giấu việc nhất, nên nó bị soi kỹ nhất."""
    web = MT.thu_muc_web()
    assert set(MT.NGOAI_LE) == {"login", "doi-mat-khau", "payroll"}, \
        "thêm ngoại lệ là mở một màn hình cho mọi tài khoản – phải có người quyết, không thêm âm thầm"
    for ten, ly_do in MT.NGOAI_LE.items():
        assert len(ly_do) > 30, f"ngoại lệ {ten} không ghi lý do đủ để người sau đọc lại còn hiểu"
        assert (web / ten / "page.tsx").exists(), f"ngoại lệ {ten} trỏ tới màn hình không tồn tại"
    # payroll được miễn vì nó CHỈ chuyển hướng – kiểm lại điều đó, đừng tin lời ghi chú
    ma = (web / "payroll" / "page.tsx").read_text(encoding="utf-8")
    assert 'location.replace("/hr")' in ma and len(ma) < 400, \
        "payroll không còn là trang chuyển hướng nữa – phải khai quyền cho nó"
    # Phiếu lương CÁ NHÂN là màn hình khác, đường dẫn khác, và KHÔNG được nằm trong danh sách ngoại lệ:
    # nó hiển thị dữ liệu thật nên phải khai quyền thật. Đổi nghĩa của /payroll để dùng lại chỗ miễn trừ
    # của nó là cách lặng lẽ lật lại quyết định 07/9 về việc tài xế không được thấy bảng lương.
    assert "phieu-luong" not in MT.NGOAI_LE, "màn hình hiển thị dữ liệu thật không được miễn khai quyền"
    assert AC.MAN_HINH_API.get("/phieu-luong"), "màn hình phiếu lương cá nhân chưa khai nhóm API nào"
    assert "/phieu-luong" in AC.MAN_HINH_KHONG_DUOC_AN, \
        "phiếu lương của chính mình mà ẩn được khỏi menu thì người lao động không có lối vào"


def test_mt6_da_noi_vao_vong_quet_cua_robot():
    from app.services import ks_robot as KS
    from app.models.kiem_soat import LOAI_PHAT_HIEN
    assert MT._ma_tran_quyen in KS.BO_KIEM
    for l in ("quyen_thua_man_hinh", "man_hinh_ho_quyen"):
        assert l in LOAI_PHAT_HIEN, f"loại {l} chưa khai tên tiếng Việt – màn hình sẽ hiện mã trần"


def test_mt7_kiem_soat_khai_dung_nguoi_quyet_k1_k2():
    """07/9 nói Kế toán không xem màn hình Kiểm soát; K1/K2 lại đặt Kế toán trưởng làm người quyết một
    cột là tiền hay không. Để lửng thì bàn làm việc mở ra mà mọi nút bấm đều 403. Đã chốt: Kế toán XEM
    được, và quyền GHI vẫn nằm ở chữ ký endpoint chứ không ở menu."""
    from app.api.v1 import ks_ra_soat as KR
    assert "/kiem-soat" in AC.MENU_ROLES
    vai = set(AC.MENU_ROLES["/kiem-soat"])
    assert "ketoan" in vai and "cntt" in vai
    assert set(KR.QUYET) <= vai, "người được quyết mà không mở được màn hình thì nút nào cũng 403"
    assert "bks" not in KR.QUYET, "robot không tự chốt xếp loại của chính mình"
    for v in KR.XEM:
        assert v in vai, f"{v} xem được qua API nhưng không mở được màn hình – hai cửa lệch nhau"
