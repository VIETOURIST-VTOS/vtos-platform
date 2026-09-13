"""Chủ tịch toàn quyền – MỘT luật, và phép thử canh cho nó không bị bỏ sót lần nữa.

Quyết định 06/9/2026 cho Chủ tịch toàn quyền chức năng. Nó cài vào `deps.FULL_ACCESS` kèm lời hứa
rằng đặt ở "đúng một chỗ" thì "không endpoint nào bị bỏ sót". Ngày 13/9/2026 lời hứa ấy vỡ: FULL_ACCESS
chỉ được đọc trong `require_roles`, còn 43 chỗ tự viết `if u.role not in X: raise 403` thì không.

Chủ tịch gặp nó ở tab Quyết toán chi tiết: cờ `nhap_duoc` tự kiểm `u.role in NHAP` bằng tay nên màn
hình báo ông không có quyền, trong khi cửa ghi phía sau VẪN MỞ cho ông. Cửa mở, biển đề đóng.

  TQ1  không còn chỗ từ chối theo vai trò nào chặn Chủ tịch mà chưa được khai
  TQ2  mọi dòng khai GIỮ ĐÓNG phải có LÝ DO viết ra – đó là lối thoát dễ nhất, nên phải trả giá
  TQ3  dòng khai cho hàm không còn tồn tại thì phải hiện ra, để dọn
  TQ4  bộ kiểm phải THẬT SỰ nhìn thấy cửa – xanh vì không thấy gì là xanh vô nghĩa
  TQ5  cửa mới chặn Chủ tịch phải bị bắt  (chốt chặn cho chính TQ1)
  TQ6  danh sách đã có "chutich" thì cho qua; bỏ "chutich" ra là đỏ ngay (chốt cho cách (2))
  TQ7  hai cửa TÁCH BẠCH TRÁCH NHIỆM quan trọng nhất phải còn nguyên trong bản khai
  TQ8  cờ `nhap_duoc` – đúng chỗ đã sai hôm 13/9 – phải trả đúng cho Chủ tịch
"""
import ast
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_toanquyen.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_toanquyen.db", "test_toanquyen.db-journal"):
    if os.path.exists(f):
        os.remove(f)


def test_tq1_khong_con_cua_nao_chan_chu_tich_ma_chua_khai():
    """Phép thử QUAN TRỌNG NHẤT của tệp này.

    Thông điệp lỗi cố ý nói ra cả hai lựa chọn, vì người gặp nó là người vừa viết một cửa mới và
    đang ở đúng lúc phải trả lời câu hỏi: cửa này là PHÂN QUYỀN hay là TÁCH BẠCH TRÁCH NHIỆM?
    """
    from app.services import ks_toan_quyen as TQ
    b = TQ.bang()
    assert not b["chan"], (
        "Có cửa từ chối theo vai trò đang chặn Chủ tịch, trái quyết định 06/9/2026. Chọn một trong "
        "hai: thêm `and not toan_quyen(u)` vào điều kiện nếu đây là chuyện PHÂN QUYỀN; hoặc khai vào "
        "ks_toan_quyen.GIU_DONG KÈM LÝ DO nếu đây là TÁCH BẠCH TRÁCH NHIỆM – việc phải do hai người "
        f"làm, bất kể hai người ấy to đến đâu: {b['chan']}")


def test_tq2_moi_dong_giu_dong_phai_co_ly_do_viet_ra():
    """“Khai để cho qua” là lối thoát dễ nhất khỏi TQ1. Bắt viết lý do là cách rẻ nhất buộc người
    khai phải thật sự nghĩ xem cửa ấy đóng để làm gì, thay vì gõ thêm một dòng cho phép thử xanh."""
    from app.services.ks_toan_quyen import GIU_DONG
    assert GIU_DONG, "phải có ít nhất vài cửa tách bạch trách nhiệm – chi tiền, đối chiếu độc lập…"
    for (tep, ham), ly_do in GIU_DONG.items():
        assert ly_do and len(ly_do.strip()) >= 60, \
            f"{tep}::{ham} khai giữ đóng nhưng lý do quá sơ sài: “{ly_do}”"


def test_tq3_khai_thua_thi_bao_ra_de_don():
    """Hàm đổi tên hoặc bị xoá thì dòng khai của nó thành vô nghĩa – và một dòng khai vô nghĩa nằm
    im lâu ngày sẽ che mất một cửa thật mang cùng tên hàm về sau."""
    from app.services import ks_toan_quyen as TQ
    b = TQ.bang()
    assert not b["khai_thua"], (
        "Có dòng khai GIỮ ĐÓNG không ứng với cửa nào trong mã – hàm đã đổi tên hoặc đã bỏ. Xoá dòng "
        f"khai, hoặc sửa khoá cho khớp tên hàm hiện tại: {b['khai_thua']}")


def test_tq4_bo_kiem_that_su_nhin_thay_cua():
    """Chốt chặn rẻ nhất và hay quên nhất: một bộ kiểm quét nhầm thư mục sẽ báo “không có vấn đề gì”
    và không ai nghi ngờ. Bản rà 13/9 đếm được 12 cửa; đòi tối thiểu 8 để còn chỗ cho việc dọn."""
    from app.services import ks_toan_quyen as TQ
    b = TQ.bang()
    assert b["so_cua"] >= 8, \
        f"chỉ thấy {b['so_cua']} cửa – bộ kiểm gần như chắc chắn đang quét nhầm chỗ, và TQ1 đang xanh vô nghĩa"


def test_tq5_cua_moi_chan_chu_tich_thi_phai_bi_bat():
    """Chốt chặn cho TQ1. Dựng một tệp .py mới trong cây app/ với đúng một cửa chặn Chủ tịch, rồi
    đòi bộ kiểm nhặt ra. Không nhặt ra thì TQ1 đang xanh một cách sai."""
    from app.services import ks_toan_quyen as TQ
    p = os.path.join(TQ.GOC, "services", "_thu_toan_quyen_tq5.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("from fastapi import HTTPException\n\n\n"
                "def cua_thu(u):\n"
                '    if u.role not in ("ketoan",):\n'
                '        raise HTTPException(403, "khong duoc")\n')
    try:
        b = TQ.bang()
        thay = [x for x in b["chan"] if x["ham"] == "cua_thu"]
        assert thay, "cửa mới chặn Chủ tịch mà bộ kiểm không thấy thì TQ1 vô dụng"
    finally:
        os.remove(p)


def test_tq6_danh_sach_da_co_chutich_thi_cho_qua_va_bo_ra_thi_do():
    """Chốt chặn cho cách (2). Cách (2) là chỗ dễ xanh sai nhất: nó cho qua hàng loạt cửa mà không
    ai phải khai gì. Nên phải chứng minh được rằng bỏ "chutich" khỏi danh sách thì nó đỏ ngay."""
    from app.services import ks_toan_quyen as TQ
    p = os.path.join(TQ.GOC, "services", "_thu_toan_quyen_tq6.py")
    khung = ('from fastapi import HTTPException\n\n'
             'CHO_PHEP = %s\n\n\n'
             'def cua_thu6(u):\n'
             '    if u.role not in CHO_PHEP:\n'
             '        raise HTTPException(403, "khong duoc")\n')
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(khung % '("chutich", "ketoan")')
        assert not [x for x in TQ.bang()["chan"] if x["ham"] == "cua_thu6"], \
            "danh sách đã có Chủ tịch mà vẫn báo chặn – cách (2) đang báo oan"

        with open(p, "w", encoding="utf-8") as f:
            f.write(khung % '("ketoan",)')
        for m in [k for k in sys.modules if k.endswith("_thu_toan_quyen_tq6")]:
            del sys.modules[m]
        assert [x for x in TQ.bang()["chan"] if x["ham"] == "cua_thu6"], \
            "bỏ “chutich” khỏi danh sách mà bộ kiểm vẫn cho qua – cách (2) đang xanh một cách sai"
    finally:
        if os.path.exists(p):
            os.remove(p)
        for m in [k for k in sys.modules if k.endswith("_thu_toan_quyen_tq6")]:
            del sys.modules[m]


def test_tq7_hai_cua_tach_bach_quan_trong_nhat_con_nguyen():
    """Bản khai GIỮ ĐÓNG có thể bị ai đó dọn nhầm cho “gọn”. Hai dòng dưới đây là hai dòng mà mất đi
    thì công ty mất lớp kiểm soát chứ không phải mất một dòng chú thích:

      * người KÝ lệnh chi và người bấm ĐÃ CHI phải là hai người (ops.step)
      * chỉ CNTT thao tác được trên tài khoản lãnh đạo – chốt chống leo thang quyền (hr.reset_password)
    """
    from app.services.ks_toan_quyen import GIU_DONG
    for khoa in (("services/ops.py", "step"), ("api/v1/hr.py", "reset_password")):
        assert khoa in GIU_DONG, (
            f"{khoa[0]}::{khoa[1]} biến mất khỏi bản khai GIỮ ĐÓNG. Nếu cửa ấy vừa được mở cho Chủ "
            "tịch thì đó là một quyết định về kiểm soát nội bộ, phải có người quyết – không phải "
            "việc dọn dẹp danh sách.")


def test_tq8_co_nhap_duoc_tra_dung_cho_chu_tich():
    """Đúng chỗ đã sai hôm 13/9: cờ màn hình đọc để vẽ nút, chứ không phải cửa chặn.

    Đọc thẳng biểu thức trong mã thay vì dựng cả một phiên đăng nhập: phép thử này canh việc CỜ ẤY
    CÓ HỎI toan_quyen hay không, và đó chính là thứ đã thiếu.
    """
    import app.api.v1.quyet_toan_lop3 as Q3
    nguon = open(Q3.__file__, encoding="utf-8").read()
    cay = ast.parse(nguon)
    thay = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value == "nhap_duoc":
                    thay.append(ast.unparse(v))
    assert thay, "không còn cờ nhap_duoc – nếu đã đổi tên thì sửa phép thử này theo"
    for bt in thay:
        assert "toan_quyen" in bt, (
            f"cờ nhap_duoc tự kiểm vai trò bằng tay mà không hỏi toan_quyen: “{bt}”. Đây đúng là lỗi "
            "13/9/2026 – cửa ghi phía sau vẫn mở cho Chủ tịch, chỉ có cái biển treo trên cửa ghi "
            "“không có quyền”, và người dùng tin cái biển.")
    assert "chutich" not in Q3.NHAP, \
        "nếu thêm thẳng chutich vào NHAP thì quyền lại nằm ở hai chỗ – đúng cái vừa gây ra lỗi này"
