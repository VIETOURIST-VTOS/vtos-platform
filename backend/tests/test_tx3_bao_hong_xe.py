# -*- coding: utf-8 -*-
"""TX-3 · Báo hư hỏng xe — Chủ tịch chọn 06/10/2026.

Việc còn thiếu cuối cùng của nhóm TIỀN, và nó KHÔNG phải một đề nghị chi. Lúc tài xế phát hiện xe
hỏng thì chưa có số tiền và chưa chọn garage; bắt họ gõ hai con số ấy là bắt họ bịa.

Bộ hàng rào này canh năm điều, mỗi điều là một cách hỏng thật:

  1. Bảng báo hỏng KHÔNG được mọc ô tiền. Ngày nào nó có `so_tien` thì nó đã lặng lẽ trở thành một
     đề nghị chi thứ hai, chạy ngoài chuỗi TGĐ/CT ký.
  2. Luật "xe này có đang hỏng không" nằm ở MỘT chỗ, và cửa chặn lệnh điều xe hỏi đúng chỗ ấy.
  3. Tài xế chỉ báo được xe CỦA MÌNH, và chỉ ĐỌC được báo hỏng của chính mình.
  4. Mở tiền tố API cho tài xế là mở đúng nhánh con, không mở cả phân hệ đội xe.
  5. Bảng mới phải có CỬA NHẬP khai trong bộ kiểm cửa nhập — một bảng không cửa là việc còn thiếu.
"""
import os
import sys
import io
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.models.fleet import Fault, MUC_DO_HONG, TRANG_THAI_HONG   # noqa: E402
from app.services import fleet as FL                               # noqa: E402
from app.services import access as AC                              # noqa: E402
from app.services import ks_cua_nhap as CN                         # noqa: E402
from app.services import luong_viec as LV                          # noqa: E402


def _doc(*phan) -> str:
    return io.open(os.path.join(GOC, *phan), encoding="utf-8").read()


def test_tx3_1_bang_bao_hong_khong_duoc_moc_o_tien():
    """Báo hỏng ghi việc CHƯA LÀM GÌ CẢ. Có ô tiền là nó đã thành một đề nghị chi thứ hai."""
    cot = set(Fault.__table__.columns.keys())
    cam = {"so_tien", "amount", "gia", "chi_phi", "garage", "ncc", "supplier_name"}
    assert not (cot & cam), (
        f"bảng báo hỏng mọc ô tiền/garage: {sorted(cot & cam)}. Tiền xuất hiện ở bước SAU, bằng một "
        "đề nghị chi loại sua_chua_xe do đội xe lập khi có báo giá — chuỗi ấy có TGĐ/CT ký, chuỗi này "
        "thì không.")
    # Nối ngược về phiếu sửa chữa thì được: đó là ghi lại kết quả, không phải thu thập số tiền.
    assert "maintenance_id" in cot
    # Hai mức, không phải năm. Xem lý do ở docstring của model.
    assert set(MUC_DO_HONG) == {"con_chay_duoc", "phai_dung_xe"}
    assert set(TRANG_THAI_HONG) >= {"moi", "da_tiep_nhan", "da_dong"}


def test_tx3_2_luat_xe_dang_hong_nam_o_mot_cho():
    """Hai chỗ tự đếm thì có ngày cửa chặn nói XE ĐANG HỎNG còn màn hình nói xe sạch."""
    dv = _doc("app", "services", "fleet.py")
    than = dv[dv.index("def kiem_tra_dieu_xe("):]
    than = than[:than.index("\ndef ", 1)]
    assert "bao_hong_dang_mo(" in than, "cửa chặn lệnh điều xe chưa hỏi hàm chung"
    assert "Fault" not in than, "cửa chặn tự truy vấn bảng báo hỏng thay vì hỏi hàm chung"
    # Chỉ MỘT nơi trong toàn bộ dịch vụ đọc trạng thái "đang mở".
    assert dv.count("HONG_CON_MO") <= 3, "điều kiện 'đang mở' bị chép ra nhiều chỗ"
    assert FL.HONG_CON_MO == ("moi", "da_tiep_nhan")

    # Mức chặn đúng như đã chốt: phải dừng xe thì BLOCK, còn chạy được thì chỉ REVIEW.
    nguon = dv[dv.index("def bao_hong_dang_mo("):]
    nguon = nguon[:nguon.index("\ndef ", 1)]
    assert '"XE_DANG_BAO_HONG"' in nguon and "BLOCK" in nguon
    assert '"CO_BAO_HONG_CHUA_XU_LY"' in nguon and "REVIEW" in nguon


def test_tx3_3_tai_xe_chi_cham_duoc_viec_cua_chinh_minh():
    cua = _doc("app", "api", "v1", "fleet.py")

    doc = cua[cua.index('@router.get("/bao-hong")'):]
    doc = doc[:doc.index('@router.post("/bao-hong"')]
    assert re.search(r'u\.role == "tai_xe"', doc) and "Fault.nguoi_bao_id == emp.id" in doc, (
        "cửa đọc sổ báo hỏng chưa lọc theo người báo — một tài xế sẽ đọc được tình trạng hỏng hóc "
        "của cả đội xe")

    ghi = cua[cua.index('@router.post("/bao-hong", status_code=201)'):]
    ghi = ghi[:ghi.index('@router.post("/bao-hong/{fid}/tiep-nhan")')]
    assert "v.driver_id != emp.id" in ghi and "DispatchOrder" in ghi, (
        "cửa ghi chưa canh xe của chính tài xế — báo hỏng cho xe người khác đang chạy thì chiếc xe ấy "
        "bị chặn mà tài xế của nó không hay")
    assert "hien_tuong" in ghi and "so_tien" not in ghi and "garage" not in ghi


def test_tx3_4_mo_tien_to_API_la_mo_dung_nhanh_con():
    """Hàng rào quyền so bằng startswith: khai '/api/v1/fleet' là mở luôn hồ sơ xe, bảng giá,
    quyết toán chủ xe cho một vai chỉ cần một cửa."""
    tt = AC.RESTRICTED_API_PREFIXES["tai_xe"]
    assert "/api/v1/fleet/bao-hong" in tt
    assert "/api/v1/fleet" not in tt, "khai tiền tố cha là mở toàn bộ phân hệ đội xe cho tài xế"
    # Vẫn đúng hai màn hình, không thêm menu nào.
    assert AC.RESTRICTED_ROLE_MENUS["tai_xe"] == ("/xe-hdv", "/doi-mat-khau")


def test_tx3_5_bang_moi_phai_co_cua_nhap_va_buoc_duoc_khai():
    """Một bảng không có cửa nhập là việc CÒN THIẾU (ranh giới 09/9/2026), không phải chỗ nhập hộ."""
    assert "fleet_faults" in CN.CUA_TAY, "bảng báo hỏng chưa khai cửa nhập tay"
    b = CN.bang()
    assert "fleet_faults" not in b["khong_cua"]

    # Ba bước của nghiệp vụ được khai, và bước ĐẦU có vai tài xế — đó là điểm của cả vòng này.
    ma = {x.ma for x in LV.theo_nghiep_vu("bao_hong_xe")}
    assert ma == {"bao", "tiep_nhan", "dong"}, f"bảng luồng công việc khai thiếu/thừa bước: {sorted(ma)}"
    bao = LV.buoc("bao_hong_xe", "bao")
    assert "tai_xe" in bao.vai_tro
    for x in LV.theo_nghiep_vu("bao_hong_xe"):
        assert len(x.vi_sao) >= 30 and x.nguon, f"{x.ma}: khai mà không nói vì sao / luật nằm ở đâu"
    # Tiếp nhận KHÔNG phải là đóng — hai bước riêng, và tài xế không đóng được việc của chính mình.
    assert "tai_xe" not in LV.buoc("bao_hong_xe", "dong").vai_tro


def test_tx3_6_hai_man_hinh_goi_dung_cua():
    tx = _doc("..", "web", "app", "xe-hdv", "page.tsx")
    assert '"/fleet/bao-hong"' in tx, "màn hình tài xế chưa gọi cửa báo hỏng"
    # Soát ĐÚNG phần thân hàm gửi báo hỏng, không soát cả tệp: chú thích giải thích vì sao KHÔNG hỏi
    # tiền và garage cũng chứa hai chữ ấy, và một hàng rào bắt nhầm chú thích thì người ta sẽ xoá chú
    # thích để qua hàng rào — mất đúng thứ đáng giữ nhất.
    than = tx[tx.index("const luuHong = async"):]
    than = than[:than.index("\n  };")]
    for cam in ("so_tien", "garage", "amount", "supplier"):
        assert cam not in than.split("json:")[1], f"thân gửi báo hỏng mọc ô “{cam}”"

    dx = _doc("..", "web", "app", "doi-xe", "page.tsx")
    assert "/fleet/bao-hong" in dx and "tiep-nhan" in dx and "/dong" in dx, (
        "màn hình đội xe thiếu hàng đợi báo hỏng hoặc thiếu một trong hai nút")
