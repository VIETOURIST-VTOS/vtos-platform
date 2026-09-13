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
  TQ7  cửa chữ ký hai người KHÔNG bao giờ mở theo công tắc – mở là ghi sai sổ, không phải nới quyền
  TQ8  cờ `nhap_duoc` – đúng chỗ đã sai hôm 13/9 – phải trả đúng cho Chủ tịch
  TQ9  cửa tách bạch phải gọi hàm CÓ công tắc, không gọi hàm trần (giữ công tắc khỏi thành đồ trang trí)
  TQ10 tắt công tắc thì cửa tách bạch phải ĐÓNG THẬT
  TQ11 đọc tham số hỏng thì đóng, không mở – công tắc an toàn hỏng về phía đóng
  TQ12 bật công tắc thì robot Kiểm soát phải nêu thành phát hiện, tắt thì phát hiện phải hết

Chủ tịch chốt 13/9/2026 mở cả cửa TÁCH BẠCH TRÁCH NHIỆM để chạy thử và trình diễn. Mở sau một CÔNG
TẮC (`chu_tich_mo_het_cua`) chứ không viết cứng: ngày vận hành thật, đóng lại là đổi một dòng tham số.
Bốn phép thử TQ9–TQ12 sinh ra vì một công tắc an toàn chỉ có giá trị khi nó thật sự tắt được, thật sự
hỏng về phía đóng, và người ngoài nhìn thấy được nó đang ở chế độ nào.
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


def test_tq2_moi_dong_khai_phai_co_ly_do_viet_ra():
    """“Khai để cho qua” là lối thoát dễ nhất khỏi TQ1 – với CẢ HAI bản khai. Bắt viết lý do là cách
    rẻ nhất buộc người khai phải thật sự nghĩ xem cửa ấy đóng (hay mở) để làm gì, thay vì gõ thêm
    một dòng cho phép thử xanh."""
    from app.services.ks_toan_quyen import GIU_DONG, MO_THEO_CONG_TAC
    assert GIU_DONG, "phải còn ít nhất cửa chữ ký hai người – cửa không công tắc nào mở được"
    assert MO_THEO_CONG_TAC, "phải có bản khai cửa mở theo công tắc, nếu không công tắc vô nghĩa"
    for ban in (GIU_DONG, MO_THEO_CONG_TAC):
        for (tep, cua), ly_do in ban.items():
            assert ly_do and len(ly_do.strip()) >= 60, \
                f"{tep}::{cua} có khai nhưng lý do quá sơ sài: “{ly_do}”"


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


def test_tq7_cua_chu_ky_hai_nguoi_khong_bao_gio_mo_theo_cong_tac():
    """Cửa `chu_ky.kiem_tra_nguoi_ky` phải nằm ở GIU_DONG và KHÔNG được lọt sang bản mở-theo-công-tắc.

    Lý do không phải phân quyền: ở cửa ấy Chủ tịch VỐN ĐÃ nằm trong danh sách được ký. Thứ nó chặn là
    một người ký thay cả hai vai – và mô hình dữ liệu chỉ có hai ô `signed_chutich` / `signed_tgd`,
    nên mở ra thì sổ ghi một chữ ký TGĐ mà TGĐ chưa hề bấm. Đó là GHI SAI SỔ, không phải nới quyền,
    và con số sai ấy không ai đọc lại mà biết được. Không công tắc nào được phép mở nó.
    """
    from app.services.ks_toan_quyen import GIU_DONG, MO_THEO_CONG_TAC
    assert ("services/chu_ky.py", "kiem_tra_nguoi_ky") in GIU_DONG, (
        "cửa chữ ký hai người biến mất khỏi bản GIỮ ĐÓNG – nếu nó vừa được mở thì hệ thống đang ghi "
        "được chữ ký mà không ai ký, và đó là việc phải có người quyết, không phải việc dọn danh sách")
    assert not [k for k in MO_THEO_CONG_TAC if k[0] == "services/chu_ky.py"], \
        "cửa chữ ký hai người lọt sang bản mở-theo-công-tắc – công tắc không được phép mở nó"


def test_tq9_cua_tach_bach_phai_goi_ham_CO_CONG_TAC_khong_goi_ham_tran():
    """Phép thử giữ cho cái CÔNG TẮC không thành đồ trang trí.

    Hai hàm cùng bắt đầu bằng `toan_quyen`, và nhìn lướt thì giống nhau. Nhưng `toan_quyen(u)` mở
    VĨNH VIỄN, còn `toan_quyen_ke_ca_tach_bach(u, db)` mở theo tham số. Hạ nhầm một cửa tách bạch
    xuống hàm trần thì công tắc vẫn còn đó, vẫn tắt bật được, mà cửa đã mở vĩnh viễn – và không ai
    nhận ra, vì cả hai đều xanh.
    """
    from app.services import ks_toan_quyen as TQ
    b = TQ.bang()
    assert not b["cong_tac_hong"], (
        "Có cửa khai là MỞ THEO CÔNG TẮC nhưng lại gọi `toan_quyen` trần – nghĩa là nó đang mở vĩnh "
        "viễn và tham số chu_tich_mo_het_cua không tắt được nó. Đổi sang "
        f"`toan_quyen_ke_ca_tach_bach(u, db)`: {b['cong_tac_hong']}")


def test_tq10_cong_tac_tat_thi_cua_tach_bach_dong_lai():
    """Công tắc phải THẬT SỰ tắt được. Một công tắc chỉ có tên mà không đổi được hành vi là thứ làm
    người ta yên tâm sai – họ tin cửa đã đóng trong khi nó vẫn mở."""
    from app.api.deps import toan_quyen, toan_quyen_ke_ca_tach_bach

    ct = type("U", (), {"role": "chutich"})()
    kt = type("U", (), {"role": "ketoan"})()

    class _DbGia:
        """Giả bảng tham số: chỉ cần get_param đọc ra được giá trị."""
        def __init__(self, bat): self.bat = bat

    import app.services.rules as R
    that = R.get_param
    try:
        R.get_param = lambda db, key, on=None: (1.0 if db.bat else 0.0)
        assert toan_quyen_ke_ca_tach_bach(ct, _DbGia(True)) is True, "bật mà không mở thì công tắc hỏng"
        assert toan_quyen_ke_ca_tach_bach(ct, _DbGia(False)) is False, \
            "TẮT mà vẫn mở – công tắc chỉ là đồ trang trí, và đây là cách tệ nhất: ai đọc tham số " \
            "cũng tưởng cửa đã đóng"
        assert toan_quyen_ke_ca_tach_bach(kt, _DbGia(True)) is False, \
            "công tắc mở cửa cho vai trò KHÁC Chủ tịch – nó chỉ được nới cho người đã có toàn quyền"
        assert toan_quyen(ct) is True and toan_quyen(kt) is False, "hàm trần phải giữ nguyên nghĩa cũ"
    finally:
        R.get_param = that


def test_tq11_cong_tac_hong_thi_DONG_chu_khong_mo():
    """Một công tắc an toàn hỏng phải hỏng về phía ĐÓNG. Bảng tham số chưa có, phiên hỏng, cơ sở dữ
    liệu cũ – mọi đường hỏng đều phải ra “đóng”, không được ra “mở”."""
    from app.api.deps import toan_quyen_ke_ca_tach_bach
    import app.services.rules as R
    ct = type("U", (), {"role": "chutich"})()
    that = R.get_param
    try:
        def _no(db, key, on=None): raise RuntimeError("bảng tham số chưa có")
        R.get_param = _no
        assert toan_quyen_ke_ca_tach_bach(ct, object()) is False, \
            "đọc tham số hỏng mà vẫn MỞ cửa tách bạch – công tắc an toàn phải hỏng về phía đóng"
    finally:
        R.get_param = that


def test_tq12_bat_cong_tac_thi_robot_kiem_soat_phai_neu_ra():
    """Một lớp kiểm soát bị tắt mà không ai NHÌN THẤY nó đang tắt thì tệ hơn là chưa từng có: người
    ta vẫn tin nó đang chạy. Nên bật công tắc phải sinh đúng một phát hiện, và tắt thì phải hết."""
    from app.services import ks_toan_quyen as TQ
    from app.services.ks_robot import BO_KIEM
    from app.models.kiem_soat import LOAI_PHAT_HIEN

    assert TQ._tach_bach_dang_mo in BO_KIEM, "bộ kiểm không nằm trong vòng quét thì nó không tồn tại"
    assert "tach_bach_dang_mo" in LOAI_PHAT_HIEN, "chưa khai loại thì màn hình hiện mã thô"

    import app.services.rules as R
    that = R.get_param
    try:
        R.get_param = lambda db, key, on=None: 1.0
        ds = TQ.quet(object())
        assert len(ds) == 1 and ds[0]["loai"] == "tach_bach_dang_mo"
        assert "ĐÃ CHI" in ds[0]["tom_tat"], \
            "câu tóm tắt phải nói ra bước NGUY HIỂM NHẤT đang mở, không chỉ nói chung chung"
        assert len(ds[0]["chi_tiet"]["cua"]) == len(TQ.MO_THEO_CONG_TAC)

        R.get_param = lambda db, key, on=None: 0.0
        assert TQ.quet(object()) == [], "tắt công tắc rồi mà phát hiện vẫn còn thì nó là phát hiện ma"
    finally:
        R.get_param = that


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
