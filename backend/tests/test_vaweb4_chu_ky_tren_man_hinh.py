# -*- coding: utf-8 -*-
"""Đợt VA-WEB4 (12/10/2026) — MÀN HÌNH PHẢI NÓI ĐÚNG SỐ CHỮ KÝ, và nói đúng NGƯỜI KÝ.

VÌ SAO CÓ TỆP NÀY

Ngày 12/10/2026 Chủ tịch ký tham số `nguong_chu_tich_duyet_chi` = 100.000.000. Dòng ấy vào
`active` ngay — đúng luật Đợt LG2: tham số chính sách cần MỘT chữ ký Chủ tịch. Nhưng trang
`/params` trên production hiện ra:

    100.000.000 · hiệu lực 12/10/2026 · active · CT ✔ · TGĐ …

Dấu "…" sau chữ TGĐ là chữ GÕ TAY trong mã web, không phải trạng thái thật của hồ sơ. Một dòng
đã đủ ký, đang có hiệu lực, hiện ra như còn thiếu người ký. Đo được bằng mắt trên production.

Bốn màn hình cùng một bệnh, và cái thứ tư nặng hơn ba cái đầu:

    /params              tham số chính sách     nói THỪA một chữ ký không ai cần
    HDV (đơn giá tuyến)  don_gia_hdv            nói THỪA
    Giá xe nội bộ        gia_xe                 nói THỪA
    Chi tiết chuyến      du_toan_duoi_bien      nói SAI NGƯỜI  ← nặng nhất

Cửa thứ tư viết "cần đủ 2 chữ ký: Chủ tịch ✔ · TGĐ ✔", trong khi luật từ 11/10/2026 là
(`ptgd_doan`, `tgd`) — Chủ tịch RA KHỎI luật, P.TGĐ tour đoàn VÀO. Nó hiện chữ ký của một vai
không còn trong luật và che mất vai đang trong luật. Cột `signed_ptgd_doan` đã có trên bảng
`tours` từ Đợt LG2; thiếu đúng một dòng gửi nó ra cho màn hình.

ĐIỀU PHÉP THỬ NÀY CANH, và vì sao canh ở HAI PHÍA

Luật mới nằm ở `chu_ky.chu_ky_de_hien`: ghép LUẬT (`can_ky`) với TRẠNG THÁI (`da_ky_cua`), chỉ
trả về những vai luật đòi. Một phép suy có tên thì phải canh cả chỗ VIẾT lẫn chỗ ĐỌC — bài học
Đợt LG1. Nên tệp này canh hai phía:

    phía máy chủ : hàm trả đúng theo bảng luật, kể cả khi hồ sơ có chữ ký của vai ngoài luật
    phía màn hình: ba tệp web KHÔNG còn chỗ nào gõ tay tên vai cạnh một cột `signed_`

Thiếu vế thứ hai thì đợt sau có người lại gõ "CT ✔ · TGĐ …" vào một màn hình mới, và không gì
đỏ cả — đúng cách bốn chỗ hôm nay lọt vào kho.
"""
import os
import re

import pytest

from app.models.core import ROLES, Param
from app.services import chu_ky as CK

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(GOC, "web")

BA_MAN_HINH = (
    os.path.join("app", "params", "page.tsx"),
    os.path.join("components", "HrScreens.tsx"),
    os.path.join("app", "tours", "[id]", "page.tsx"),
)


class HoSoGia:
    """Hồ sơ dựng tay — phép thử này đo PHÉP SUY, không đo cơ sở dữ liệu."""

    def __init__(self, **cot):
        for k, v in cot.items():
            setattr(self, k, v)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHÍA MÁY CHỦ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_vaweb4_1_tham_so_chi_mot_chu_ky_chu_tich():
    """Chính con số đã sai trên production: tham số cần ĐÚNG MỘT chữ ký."""
    ra = CK.chu_ky_de_hien("tham_so", HoSoGia(signed_chutich=True))
    assert len(ra) == 1, f"Tham số phải cần đúng 1 chữ ký, hàm trả {len(ra)}: {ra}"
    assert ra[0]["vai"] == "chutich"
    assert ra[0]["da_ky"] is True
    assert ra[0]["ten"] == ROLES["chutich"], "Tên vai phải đọc từ ROLES, không gõ tay"


def test_vaweb4_2_vai_ngoai_luat_khong_duoc_hien_ra():
    """ĐÚNG LỖI NGÀY 12/10/2026: hồ sơ có cột `signed_tgd` nhưng luật không đòi TGĐ.

    Trước đợt này màn hình đọc cột ấy rồi hiện "TGĐ …". Hàm mới phải KHÔNG trả vai ấy ra —
    dù cột có tồn tại, dù nó mang giá trị gì.
    """
    for tgd_da_ky in (False, True):
        ra = CK.chu_ky_de_hien("tham_so", HoSoGia(signed_chutich=True, signed_tgd=tgd_da_ky))
        assert [k["vai"] for k in ra] == ["chutich"], \
            f"signed_tgd={tgd_da_ky} vẫn làm TGĐ lọt vào danh sách: {ra}"


def test_vaweb4_3_hai_cua_con_hai_chu_ky_phai_giu_du_hai():
    """Đợt này KHÔNG nới cho ai: hai cửa thật sự cần hai chữ ký vẫn phải hiện đủ hai."""
    for loai in ("quy_tac_hach_toan", "che_tai_muc_3"):
        ra = CK.chu_ky_de_hien(loai, HoSoGia(signed_chutich=True, signed_tgd=False))
        assert [k["vai"] for k in ra] == ["chutich", "tgd"], f"{loai}: {ra}"
        assert [k["da_ky"] for k in ra] == [True, False]


def test_vaweb4_4_duoi_bien_la_ptgd_doan_khong_phai_chu_tich():
    """CỬA THỨ TƯ. Chủ tịch đã ra khỏi luật này từ 11/10/2026.

    Hồ sơ dựng ở đây CÓ chữ ký Chủ tịch — y như một chuyến ký trước ngày đổi luật. Hàm vẫn
    không được hiện Chủ tịch ra, vì màn hình hiện một chữ ký không còn giá trị pháp lý là nói
    với người đọc rằng bước ký đã xong trong khi nó chưa.
    """
    ra = CK.chu_ky_de_hien("du_toan_duoi_bien",
                           HoSoGia(signed_chutich=True, signed_tgd=True, signed_ptgd_doan=False))
    assert [k["vai"] for k in ra] == ["ptgd_doan", "tgd"], ra
    assert "chutich" not in [k["vai"] for k in ra], "Chủ tịch đã RA KHỎI luật dưới biên 11/10/2026"
    assert ra[0]["da_ky"] is False, "P.TGĐ tour đoàn chưa ký thì phải nói là chưa"
    assert ra[0]["ten"] == ROLES["ptgd_doan"]


def test_vaweb4_5_cot_khong_co_doc_thanh_chua_ky_chu_khong_no():
    """`params` không có cột `signed_ptgd_doan`. Đọc cột không có phải ra CHƯA KÝ, không được nổ."""
    ra = CK.chu_ky_de_hien("du_toan_duoi_bien", HoSoGia())
    assert [k["da_ky"] for k in ra] == [False, False]


@pytest.mark.parametrize("loai", sorted(CK.VAI_KY_CAN))
def test_vaweb4_6_moi_loai_trong_bang_luat_deu_suy_duoc(loai):
    """Mọi dòng của bảng luật phải đi qua được hàm mới, và tên vai nào cũng phải có trong ROLES."""
    ra = CK.chu_ky_de_hien(loai, HoSoGia())
    assert ra, f"{loai}: bảng luật khai rỗng?"
    assert len(ra) == len(CK.can_ky(loai))
    for k in ra:
        assert k["ten"] != k["vai"], f"{loai}: vai {k['vai']} chưa có tên trong ROLES"
    assert CK.ten_vai_ky(loai) == [k["ten"] for k in ra]


def test_vaweb4_7_ten_vai_ky_tra_ten_chu_khong_tra_ma():
    """Nút bấm là chỗ người đọc: phải ra "Chủ tịch HĐQT", không ra "chutich"."""
    assert CK.ten_vai_ky("tham_so") == ["Chủ tịch HĐQT"]
    assert CK.ten_vai_ky("du_toan_duoi_bien") == [ROLES["ptgd_doan"], ROLES["tgd"]]


def test_vaweb4_8_go_sai_ten_loai_thi_vo_ngay():
    """Giữ nguyên tính nết của `can_ky`: gõ sai tên loại là KeyError, không trả mặc định im lặng."""
    with pytest.raises(KeyError):
        CK.chu_ky_de_hien("khong_co_loai_nay", HoSoGia())


def test_vaweb4_9_cua_tham_so_that_su_gui_chu_ky_ra():
    """Đo CHÍNH cửa, không chỉ đo hàm: `param_out` phải mang `chu_ky` và `ten_vai_ky`."""
    from app.api.v1.routes import param_out
    p = Param(key="nguong_chu_tich_duyet_chi", value="100000000", label="Ngưỡng duyệt chi",
              unit="đồng", status="active", signed_chutich=True, signed_tgd=False)
    ra = param_out(p)
    assert "chu_ky" in ra and "ten_vai_ky" in ra, "Cửa /params chưa gửi chữ ký đã lọc theo luật"
    assert [k["vai"] for k in ra["chu_ky"]] == ["chutich"], ra["chu_ky"]
    assert ra["chu_ky"][0]["da_ky"] is True
    assert ra["ten_vai_ky"] == ["Chủ tịch HĐQT"]
    # Hai cột thô vẫn còn: nơi khác đang đọc chúng, đợt này KHÔNG bỏ.
    assert ra["signed_chutich"] is True and ra["signed_tgd"] is False


def test_vaweb4_10_ba_cua_con_lai_doc_dung_ten_loai():
    """Ba cửa kia gọi đúng tên loại của chính nó — gọi nhầm tên là hiện luật của cửa khác."""
    can = {os.path.join("app", "api", "v1", "hr.py"):
           ('_CK.chu_ky_de_hien("don_gia_hdv"', '_CK.chu_ky_de_hien("gia_xe"'),
           os.path.join("app", "services", "tours.py"):
           ('_CK.chu_ky_de_hien("du_toan_duoi_bien"', '"signed_ptgd_doan"')}
    for rel, phai_co in can.items():
        t = open(os.path.join(GOC, "backend", rel), encoding="utf-8").read()
        for c in phai_co:
            assert c in t, f"{rel} thiếu {c}"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHÍA MÀN HÌNH — hàng rào thật của đợt này
# ══════════════════════════════════════════════════════════════════════════════════════════════

# Hình của lỗi: một tên vai viết tay đứng ngay cạnh một cột `signed_`.
GO_TAY = re.compile(r"(CT|TGĐ|Chủ tịch|Tổng giám đốc|P\.TGĐ)\s*\{[^}]*signed_")


@pytest.mark.parametrize("rel", BA_MAN_HINH)
def test_vaweb4_11_man_hinh_khong_go_tay_ten_vai(rel):
    """Không màn hình nào được tự biết ai phải ký. Đó là việc của bảng luật."""
    duong = os.path.join(WEB, rel)
    if not os.path.exists(duong):
        pytest.skip(f"không có {rel} trong cây này")
    t = open(duong, encoding="utf-8").read()
    sai = [f"dòng {t[:m.start()].count(chr(10)) + 1}: {m.group(0)[:60]}" for m in GO_TAY.finditer(t)]
    assert not sai, (
        f"{rel} còn gõ tay tên vai cạnh một cột `signed_`:\n  " + "\n  ".join(sai) +
        "\n\nDùng <KyO ky={...} /> và để máy chủ nói ai phải ký — xem `chu_ky.chu_ky_de_hien`.")
    assert "Trình Chủ tịch + TGĐ" not in t, f"{rel}: nút Trình còn gõ tay hai vai"


def test_vaweb4_12_ky_o_la_cho_dung_chung_va_duoc_nhap_vao_noi_dung():
    """`KyO` phải nằm ở `ui.tsx` (một chỗ) và phải được ba màn hình nhập vào thật."""
    ui = open(os.path.join(WEB, "components", "ui.tsx"), encoding="utf-8").read()
    assert "export const KyO" in ui, "KyO phải là thành phần dùng chung ở components/ui.tsx"
    for rel in BA_MAN_HINH:
        duong = os.path.join(WEB, rel)
        if not os.path.exists(duong):
            continue
        t = open(duong, encoding="utf-8").read()
        assert "KyO" in t, f"{rel} chưa dùng KyO"
        assert re.search(r"import \{[^}]*KyO[^}]*\} from \"@/components/ui\"", t), \
            f"{rel} dùng KyO mà không nhập từ components/ui"


def test_vaweb4_13_rong_khong_phai_du_ky():
    """Luật K2 ở chỗ dễ sai nhất: danh sách RỖNG là CHƯA BIẾT, không phải ĐỦ KÝ."""
    ui = open(os.path.join(WEB, "components", "ui.tsx"), encoding="utf-8").read()
    than = ui[ui.index("export const KyO"):]
    than = than[:than.index("export const tenKy")]
    assert "!ky || !ky.length" in than, "KyO phải xử lý danh sách rỗng trước mọi việc khác"
    assert "✔" not in than.split("return")[1].split(";")[0], \
        "Nhánh rỗng không được hiện dấu đã ký"
