# -*- coding: utf-8 -*-
"""NS-1 · Đơn nghỉ phép / ốm / vắng việc của đội xe — Chủ tịch quyết 30/9/2026.

> "Liên quan đến con người như nghỉ phép, ốm đau, vắng việc sẽ do Huấn duyệt, TGĐ và CT thấy."

Vòng này KHÔNG dựng bảng mới. Bảng `leave_requests`, phép năm theo Bộ luật Lao động, và cả đường
ghi sang bảng chấm công đã chạy từ trước. Cái còn thiếu là hai thứ khác, và cả hai đều là thứ chỉ
thấy khi đi hỏi đúng câu:

  1. KHÔNG MÀN HÌNH NÀO GỌI TỚI. `leave_requests` được khai "có cửa nhập tay" trong bộ kiểm cửa
     nhập, nhưng rà cả thư mục `web/app` thì không một tệp nào gọi `/leaves`. Một cửa có trên máy
     chủ mà người phải dùng không với tới thì vẫn là việc CÒN THIẾU — đúng loại lệch mà chính
     docstring của `ks_cua_nhap` cảnh báo là phép thử ở đó không bắt được.

  2. AI KÝ ĐƠN CỦA AI thì chưa ai hỏi. Trước bản này bảy vai trong chữ ký cửa `/leaves/{id}/decide`
     ký được đơn của BẤT KỲ ai trong công ty: một Trưởng phòng Kinh doanh ký được đơn nghỉ của một
     tài xế. Không phải vì ai quyết thế — vì câu hỏi chưa được đặt. Đơn vẫn chạy đúng suốt thời
     gian qua chỉ vì trên thực tế HCNS là người bấm.

Bộ hàng rào này canh sáu điều, mỗi điều là một cách hỏng thật.
"""
import os
import sys
import io
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.models.hr import DEPARTMENTS             # noqa: E402
from app.services import hrm as H                 # noqa: E402
from app.services import access as AC             # noqa: E402
from app.services import luong_viec as LV         # noqa: E402
from app.api.v1 import hrm as API                 # noqa: E402


def _doc(*phan) -> str:
    return io.open(os.path.join(GOC, *phan), encoding="utf-8").read()


def test_ns1_1_tuyen_ky_dung_nhu_chu_tich_quyet():
    """Đội xe: ĐÚNG MỘT vai ký. Thêm vai thứ hai vào đây là nới quyền ký, phải có người quyết."""
    assert H.TUYEN_KY_DON["doi_xe"] == ("gd_doi_xe",), (
        "Chủ tịch quyết 30/9/2026: đơn nghỉ của đội xe do Giám đốc đội xe ký, một chữ ký. "
        f"Đang là {H.TUYEN_KY_DON.get('doi_xe')}")
    assert H.TUYEN_KY_DON["huong_dan"] == ("tp_hd",), (
        "Hệ quả đã ghi trong chính lý do tách vai 05/10/2026 (models/core.py): đơn của hướng dẫn "
        "viên đi về Trưởng phòng Hướng dẫn")

    # TGĐ và Chủ tịch THẤY mọi đơn (họ nằm trong nhóm đọc), nhưng KHÔNG ký ở bước này. Trộn hai thứ
    # là chỗ quyền bị nới mà không ai quyết định.
    for vai in ("tgd", "chutich"):
        assert vai in API.HR_READ, f"{vai} phải ĐỌC được mọi đơn"
        assert vai not in H.TUYEN_KY_DON["doi_xe"], f"{vai} không ký đơn đội xe – Chủ tịch nói Huấn ký"


def test_ns1_2_chan_nam_trong_ham_khong_chi_o_cua_api():
    """Chữ ký cửa nói AI gõ được vào cửa; chỉ cái trong hàm còn đúng khi có cửa thứ hai gọi vào."""
    dv = _doc("app", "services", "hrm.py")
    than = dv[dv.index("def decide_leave("):]
    than = than[:than.index("\ndef ", 1)]
    assert "nguoi_ky_don(" in than, "decide_leave chưa hỏi bảng tuyến ký"
    assert "u.role not in" in than, "decide_leave chưa chặn người ký sai phòng"
    assert "e.user_id == u.id" in than, "thiếu chặn tự duyệt đơn của chính mình"

    # Chữ ký cửa API phải SUY RA từ bảng luật, không khai tay lần thứ hai. Hai bảng khai tay thì sớm
    # muộn cũng lệch, và lúc lệch thì hoặc một người ký được thứ không phải của mình, hoặc một người
    # đúng luật lại bị cửa chặn mà không ai hiểu vì sao.
    cua = _doc("app", "api", "v1", "hrm.py")
    assert "TUYEN_KY_DON.values()" in cua, "KY_DON khai tay thay vì suy từ bảng luật"
    for phong, vais in H.TUYEN_KY_DON.items():
        for v in vais:
            assert v in API.KY_DON, f"{v} ký đơn phòng {phong} mà cửa API không cho gõ vào"
    assert set(H.KY_MAC_DINH) <= set(API.KY_DON), "bản này siết mất một vai đang ký được – không phải ý"


def test_ns1_3_phong_chua_chot_nguoi_ky_phai_dem_duoc():
    """Bản này CỐ Ý chỉ sửa hai phòng Chủ tịch đã nói, không nhân tiện đặt luật cho chín phòng kia.

    Chỗ chưa quyết phải ĐẾM ĐƯỢC để câu hỏi còn nhìn thấy, y như `misa.thieu_tai_khoan()` giữ cho
    câu hỏi tài khoản của `sua_chua_xe` khỏi chìm đi.
    """
    chua = set(H.phong_chua_chot_nguoi_ky())
    assert "doi_xe" not in chua and "huong_dan" not in chua, "hai phòng đã chốt mà vẫn báo là chưa"
    assert chua, (
        "mọi phòng đều đã chốt người ký — nếu đúng thì sửa phép thử này kèm ngày và người quyết, "
        "đừng xoá nó đi")
    assert chua <= set(DEPARTMENTS), f"tên phòng lạ trong bảng: {chua - set(DEPARTMENTS)}"
    for p in chua:
        assert H.nguoi_ky_don(p) == H.KY_MAC_DINH, f"{p} chưa chốt mà đã đổi người ký"


def test_ns1_4_mo_cua_cho_hien_truong_khong_thanh_mo_so_don_cong_ty():
    """Ba lớp, và phép thử đòi đủ ba. Bỏ lớp nào thì một tài xế đọc được đơn không phải của mình."""
    # Lớp 1 – tiền tố API khai, nên bộ tra cứu ngược đọc được phạm vi của hai vai hiện trường.
    for vai in ("tai_xe", "hdv"):
        assert "/api/v1/leaves" in AC.RESTRICTED_API_PREFIXES[vai]
        # Vai này KHÔNG được thêm màn hình nào. Mở tiền tố API không phải mở menu.
        assert AC.RESTRICTED_ROLE_MENUS[vai] == ("/xe-hdv", "/doi-mat-khau")

    # Lớp 2 – cửa ĐỌC lọc ba tầng, và tầng giữa (người ký thấy phòng mình) nằm Ở MÁY CHỦ.
    cua = _doc("app", "api", "v1", "hrm.py")
    than = cua[cua.index('@router.get("/leaves")'):]
    than = than[:than.index("\n@router.post")]
    assert "phong_minh_ky(" in than, "cửa đọc chưa có tầng người ký – Giám đốc đội xe mở ra sẽ không thấy đơn nào"
    assert "HR_READ" in than and "LeaveRequest.employee_id == me.id" in than, (
        "cửa đọc mất tầng 'chỉ đơn của chính mình' – một tài xế sẽ đọc được đơn của cả công ty")

    # Lớp 3 – HAI NGƯỜI KÝ phải có tiền tố, nếu không màn hình hiện nút mà bấm vào là 403. Hai vai
    # này lấy /xe-hdv từ danh sách CHO PHÉP chứ không từ ma trận menu, nên không suy ra được.
    for vai in ("gd_doi_xe", "tp_hd"):
        assert "/api/v1/leaves" in AC.pham_vi_day_du(vai), (
            f"{vai} là người ký mà không chạm được cửa đơn – bảng luồng công việc đang khai một "
            "người ký không ký được")

    # Và mở nhánh con chứ không mở cả phân hệ nhân sự. KHÔNG kể "/api/v1/employees" ở đây: hai vai
    # hiện trường đã có nhóm ấy từ trước bản này (nền chung, không phải do vòng này mở), và một phép
    # thử mới mà đỏ vì chuyện cũ thì người gặp nó sẽ sửa nhầm chỗ. Nếu nhóm ấy rộng quá thì đó là
    # một việc riêng, có người quyết, không phải thứ sửa kèm ở đây.
    for vai in ("tai_xe", "hdv"):
        pv = AC.pham_vi_day_du(vai)
        for cam in ("/api/v1/hrm", "/api/v1/payroll", "/api/v1/attendance", "/api/v1/labor-contracts"):
            assert cam not in pv, f"{vai} chạm được {cam} – đó là hồ sơ và lương của người khác"


def test_ns1_5_hai_buoc_khai_trong_bang_luong_viec():
    """Bước và cửa phải ra cùng một vòng: `test_luong_viec` canh bảng khớp luật đang chạy."""
    ma = {x.ma for x in LV.theo_nghiep_vu("don_nhan_su")}
    assert ma == {"gui", "quyet"}, f"bảng luồng công việc khai thiếu/thừa bước: {sorted(ma)}"

    quyet = LV.buoc("don_nhan_su", "quyet")
    # Bước duyệt KHÔNG khai cứng vai trò: người ký phụ thuộc PHÒNG của người làm đơn. Khai cứng ở
    # đây là khai luật lần thứ hai, và hai bảng khai tay thì sớm muộn cũng lệch.
    assert quyet.vai_tro == () and "nguoi_ky_don" in quyet.vai_tro_dong, (
        "bước duyệt khai cứng danh sách vai – luật người ký nằm ở hrm.TUYEN_KY_DON, một chỗ")
    assert quyet.nguon == "hrm.py::decide_leave"
    for x in LV.theo_nghiep_vu("don_nhan_su"):
        assert len(x.vi_sao) >= 30 and x.nguon, f"{x.ma}: khai mà không nói vì sao / luật nằm ở đâu"

    # Chuỗi dừng ở MỘT chữ ký: không có bước nào sau bước duyệt. Nhóm này không sinh tiền nên không
    # đi qua bàn ký tiền; thêm một bước ở đây là đổi quyết định của Chủ tịch.
    assert len(LV.theo_nghiep_vu("don_nhan_su")) == 2, "chuỗi đơn nhân sự mọc thêm bước ký"


def test_ns1_6_man_hinh_goi_dung_cua_va_khong_tu_dat_luat():
    """08/10/2026 — KHUNG ĐƠN NGHỈ ĐÃ RỜI /xe-hdv sang thành phần dùng chung `DonNghiPhep`.

    Vòng NS-2 mở đơn nghỉ cho cả mười một phòng, nên khung ấy không còn là của riêng màn hình hiện
    trường. Phép thử đi theo chỗ mã chuyển tới, và SIẾT thêm một điều: màn hình /xe-hdv phải thật sự
    dựng thành phần ấy. Nếu chỉ đổi đường đọc sang tệp thành phần mà không hỏi câu thứ hai thì có thể
    gỡ khung khỏi /xe-hdv mà phép thử vẫn xanh — người ở hiện trường mất ô gửi đơn trong im lặng.
    """
    mh = _doc("..", "web", "app", "xe-hdv", "page.tsx")
    # Hỏi THẺ JSX `<DonNghiPhep`, không hỏi chữ "DonNghiPhep". Bản đầu hỏi chữ, và kiểm ngược bắt
    # được ngay: gỡ thẻ ra khỏi phần kết xuất thì phép thử vẫn XANH, vì dòng `import` còn chứa đúng
    # chữ ấy. Một hàng rào hỏi tên tệp thay vì hỏi chỗ dùng là hàng rào xanh đúng lúc màn hình trống.
    assert "<DonNghiPhep" in mh, "màn hình hiện trường không còn DỰNG khung gửi đơn nghỉ"
    mh = mh + _doc("..", "web", "components", "DonNghiPhep.tsx")
    assert '"/leaves"' in mh, "màn hình chưa gọi cửa đơn nghỉ"
    assert '"/leave-balance"' in mh, "màn hình chưa đọc quỹ phép – người gửi đơn không biết mình còn mấy ngày"
    assert "/decide" in mh, "màn hình thiếu nút quyết định của người ký"

    # Màn hình KHÔNG tự khai ai ký được đơn nào: nút Duyệt chỉ hiện theo cờ máy chủ trả về.
    assert "co_the_ky" in mh, "màn hình tự suy người ký thay vì đọc cờ của máy chủ"
    assert "gd_doi_xe" not in mh and "TUYEN_KY" not in mh, (
        "màn hình khai cứng vai người ký – luật phải nằm ở máy chủ, một chỗ")

    # Từ chối bắt buộc ghi lý do, ở CẢ HAI chỗ. Máy chủ đòi để không ai lách được bằng cửa khác;
    # màn hình đòi để người dùng khỏi gửi đi rồi bị trả về.
    cua = _doc("app", "api", "v1", "hrm.py")
    than = cua[cua.index('@router.post("/leaves/{lid}/decide")'):]
    than = than[:than.index("\n@router.get")]
    assert re.search(r"not data\.approve and not .*note", than), "cửa duyệt chưa bắt lý do khi từ chối"
    assert re.search(r"Từ chối.*ghi lý do", mh, re.S), "màn hình chưa bắt lý do khi từ chối"
