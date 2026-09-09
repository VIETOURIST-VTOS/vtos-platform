"""Quyền làm một việc và màn hình để làm việc ấy phải nói cùng một điều.

Hệ thống có hàng rào hai lớp: lớp ngoài là phạm vi đường API theo vai trò, lớp trong là chữ ký từng
đường. Hai lớp ấy để lớp ngoài rộng, lớp trong hẹp – KHÔNG phải để hai lớp nói hai điều khác nhau
về cùng một vai trò. Cạnh chúng còn lớp thứ ba mà phép thử hay quên: danh sách MÀN HÌNH. Quyền gọi
một đường mà không màn hình nào có nút gọi nó thì cũng bằng không có quyền, và chiều ngược lại –
thấy màn hình mà máy chủ trả 403 – còn tệ hơn, vì người dùng đọc nó là hệ thống hỏng chứ không đọc
là mình không được phép.

Bản rà 09/9/2026 tìm được bốn chỗ ba lớp ấy lệch nhau. Ba chỗ đã sửa (lệnh điều xe, cửa gõ tay,
ô đính kèm); phép thử này giữ chỗ thứ tư và canh để loại lệch ấy không sinh lại.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_cua_theo_vai_tro.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_cua_theo_vai_tro.db"): os.remove("test_cua_theo_vai_tro.db")
import re
from pathlib import Path
import pytest
from app.services import access as AC, intake as IN
from app.services import attachments as ATS
from app.api.v1 import attachments as AT

WEB = Path(__file__).resolve().parents[2] / "web"


class _nguoi:
    def __init__(self, vai): self.role = vai; self.hr_tabs = None; self.id = 0


def _thay(vai) -> set:
    return set(AC.menus_for(_nguoi(vai)))


# ------------------------------------------------------------------ 1. Robot Kiểm soát đọc được tệp
def test_robot_kiem_soat_doc_duoc_tep_dung_nhu_bks():
    """Chủ tịch chốt vai trò robot_ks là "đọc toàn bộ như BKS, chỉ đọc".

    Danh sách màn hình đã đúng thế – 46 màn hình, y hệt BKS, trong đó có /tep. Nhưng danh sách vai trò
    ở router đính kèm thì quên, nên mọi lần đọc trả 403: robot đứng trước đúng màn hình nó phải kiểm
    và không thấy một chứng từ nào. Không có lỗi nào được ghi ra – chỉ là báo cáo kiểm soát nói "không
    có chứng từ nào", câu ấy đọc y hệt câu "đã kiểm, sạch".
    """
    assert "/tep" in _thay("robot_ks"), "robot_ks không còn thấy màn hình Tệp – phép thử dưới mất nghĩa"
    assert "robot_ks" in AT.READ, (
        "robot_ks thấy màn hình /tep nhưng không đọc được tệp nào (403). Thấy màn hình mà máy chủ chặn "
        "thì người đọc kết luận là hệ thống hỏng, chứ không kết luận là mình không được phép.")


def test_robot_kiem_soat_khong_ghi_va_khong_doc_ho_so_nhan_su():
    """Hai vế của "chỉ đọc", và vế thứ hai không suy ra từ vế thứ nhất.

    Không ghi: robot kiểm soát mà sửa được chứng từ thì nó kiểm chính việc nó làm.
    Không đọc hồ sơ nhân sự: BKS là NGƯỜI, có tên, ký vào biên bản kiểm tra. Một tác vụ máy đọc hồ sơ
    nhân sự là việc khác về bản chất – Nghị định 13/2023 nói về dữ liệu cá nhân, không nói về mức tin
    cậy của người đọc. Chủ tịch mở thêm được, nhưng phải là một câu nói ra, không phải một hệ quả kèm
    theo của câu "đọc toàn bộ như BKS".
    """
    assert "robot_ks" not in AT.WRITE, "robot kiểm soát gắn được tệp thì nó kiểm chính việc nó làm"
    assert "robot_ks" not in AT.GO, "robot kiểm soát thu hồi được chứng từ"
    assert "robot_ks" not in ATS.VAI_TRO_NHAY_CAM, (
        "robot_ks đang đọc được hồ sơ nhóm 06_Nhan_su. Nếu đó là quyết định của Chủ tịch thì sửa phép "
        "thử này kèm ngày và câu chỉ đạo – không để nó lọt vào như hệ quả của một câu nói về BKS.")


# ------------------------------------------------------------------ 2. Được nạp thì phải thấy cửa nạp
# Vai trò nằm trong danh sách được nạp nhưng KHÔNG thấy màn hình Nạp dữ liệu, kèm lý do thật.
# Vai trò nằm trong danh sách được nạp nhưng KHÔNG thấy màn hình Nạp dữ liệu, kèm lý do thật.
#
# Rỗng từ 09/9/2026. Hai dòng đầu tiên của danh sách này là ptgd_doan và ptgd_mkt: quyền cho phép hai
# ông nạp dữ liệu của phòng mình, menu thì không có màn hình. Câu hỏi đặt cho Chủ tịch là "nếu Phó TGĐ
# không phải người gõ số thì bỏ khỏi danh sách quyền; nếu có thì mở màn hình", và Chủ tịch trả lời
# ngay trong ngày: hai Phó TGĐ quản lý phòng của mình. Menu là chỗ lạc hậu – đã mở.
#
# Giữ lại cái ô rỗng chứ không xoá, vì chỗ dùng của nó là lần lệch sau. Và ghi lại luôn hình dạng của
# lần này: hỏi một câu ngắn có hai đường ra rõ ràng thì được trả lời trong ngày; còn đoán hộ rồi tự
# sửa thì cái sai nằm lại trong mã và không ai biết nó ở đó.
NAP_KHONG_CO_MAN_HINH = {}


def test_duoc_nap_du_lieu_thi_phai_thay_man_hinh_nap():
    xau = {}
    for k in IN.BO_NAP:
        for vai in IN.VAI_TRO.get(k, IN.QUAN_TRI):
            if "/nap-du-lieu" not in _thay(vai):
                xau.setdefault(vai, []).append(k)
    thieu = {v: ks for v, ks in xau.items() if v not in NAP_KHONG_CO_MAN_HINH}
    assert not thieu, (
        f"Vai trò được nạp dữ liệu nhưng không thấy màn hình Nạp dữ liệu: {thieu}. Quyền mà không có "
        "cửa thì bằng không có quyền. Mở màn hình, bỏ khỏi danh sách quyền, hoặc thêm vào "
        "NAP_KHONG_CO_MAN_HINH kèm lý do.")


def test_duoc_gan_tep_thi_phai_co_mot_cho_de_gan():
    """Được gắn tệp thì phải có ÍT NHẤT một màn hình có ô gắn – /tep, hoặc màn hình của phòng mình."""
    if not WEB.exists():
        return
    co_o = set()
    for p in list(WEB.glob("app/**/*.tsx")):
        if "<DinhKem" in p.read_text(encoding="utf-8") or 'type="file"' in p.read_text(encoding="utf-8"):
            co_o.add("/" + p.parent.relative_to(WEB / "app").as_posix())
    thieu = []
    for vai in AT.WRITE:
        thay = _thay(vai)
        if "/tep" not in thay and not (thay & co_o):
            thieu.append(vai)
    assert not thieu, (
        f"Vai trò được gắn tệp nhưng không màn hình nào của họ có ô tải lên: {thieu}")


def test_danh_sach_hoan_co_tran_va_co_ly_do_that():
    """Danh sách hoãn không trần là cách một phép thử tự tắt mình."""
    assert len(NAP_KHONG_CO_MAN_HINH) <= 3, (
        f"Đang hoãn {len(NAP_KHONG_CO_MAN_HINH)} vai trò. Ngày 09/9/2026 là 2.")
    for vai, ly_do in NAP_KHONG_CO_MAN_HINH.items():
        assert len(ly_do) > 80, f"Lý do hoãn cho '{vai}' quá ngắn để là một lý do thật"
