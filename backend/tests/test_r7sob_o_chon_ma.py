"""ĐỢT R7-SOb 01/11/2026 — HAI Ô CHỌN TRÊN MÀN HÌNH SỔ KẾ TOÁN: NĂM LUẬT CANH.

Đợt R7-SO dựng màn hình, nhưng để ô "Mã đối tượng" và "Mã công trình" là HAI Ô GÕ TAY. Gõ tay
thì người dùng tự nghĩ ra một mã không tồn tại, bấm "Xem sổ", nhận một sổ rỗng, và không biết vì
sao — một sổ rỗng và một mã sai trông GIỐNG HỆT NHAU trên màn hình.

Đợt R7-MCT đã mở cửa hẹp `/books/ma-cong-trinh?q=`. Đợt này nối nó vào ô chọn.

Năm luật dưới đây canh đúng năm chỗ dễ tuột lại: ô quay về gõ tay, gọi nhầm cửa nặng, bỏ hoãn,
nuốt mất lời cảnh báo "chưa gắn vào sổ", và quy tắc 4.
"""
from pathlib import Path
import re

GOC = Path(__file__).resolve().parents[2]
MH = (GOC / "web" / "app" / "accounting" / "page.tsx").read_text(encoding="utf-8")
CUA = (GOC / "backend" / "app" / "api" / "v1" / "books.py").read_text(encoding="utf-8")
KHOI = MH.split("function SoKeToanPanel", 1)[1].split("\nfunction Accounting", 1)[0]
# Đo MÃ CHẠY, không đo lời ghi chú: bản đầu của luật 2 đỏ vì chính dòng ghi chú
# “KHÔNG gọi /api/v1/tours” của đợt này. Một phép đo bắt cả lời nói VỀ việc làm thì
# nó không đo việc làm.
MA_CHAY = "\n".join(d for d in MH.split("\n") if not d.strip().startswith("//"))


def test_r7sob_1_hai_o_la_o_chon_khong_phai_o_go_tay():
    """Mỗi ô phải trỏ tới một `<datalist>` CÓ THẬT trong chính khối này.

    Chỉ kiểm có chữ `list=` thì chưa đủ: trỏ vào một danh sách không tồn tại thì trình duyệt im
    lặng hiện một ô gõ tay y như cũ, và không ai biết.
    """
    for o, ds in (("partner_code", "ds-doi-tuong"), ("project_code", "ds-cong-trinh")):
        assert f'list="{ds}"' in KHOI, f"o {o} chua tro toi mot danh sach"
        assert f'<datalist id="{ds}">' in KHOI, f"danh sach {ds} khong ton tai"


def test_r7sob_2_doc_dung_cua_nhe_khong_goi_cua_nang():
    """Ô công trình đọc CỬA HẸP, và cửa hẹp ấy phải có thật ở máy chủ.

    `GET /api/v1/tours` đo được 16–30 giây trên hệ thật. Nhét nó vào một ô chọn là làm màn hình
    chờ nửa phút mỗi lần mở — luật này chặn đúng chỗ ấy.
    """
    assert '@router.get("/ma-cong-trinh")' in CUA, "cua hep chua co tren may chu"
    assert "/books/ma-cong-trinh?q=" in KHOI
    assert "/partners?q=" in KHOI and "limit=30" in KHOI
    assert "/tours" not in MA_CHAY, "man hinh goi cua nang /api/v1/tours"


def test_r7sob_3_co_hoan_truoc_khi_hoi():
    """Gõ mười một ký tự KHÔNG được thành mười một lần hỏi máy chủ.

    Đo được: mỗi ô có một `setTimeout` và một `clearTimeout` ở nhánh dọn dẹp — bỏ `clearTimeout`
    thì lần hỏi cũ vẫn chạy, và hoãn trở thành vô nghĩa.
    """
    assert KHOI.count("setTimeout(") >= 2, "thieu hoan cho mot trong hai o"
    assert KHOI.count("clearTimeout(") >= 2, "co hoan ma khong huy lan hoi cu"


def test_r7sob_4_noi_ra_khi_ma_chua_gan_vao_so():
    """Chọn một mã chưa gắn vào sổ thì màn hình PHẢI nói ra trước khi người dùng bấm Xem sổ.

    Sổ gom theo `project_code`. Mã chưa gắn thì chọn nó cũng không ra số. Giấu đi thì kế toán
    thấy sổ rỗng và tưởng đoàn ấy không phát sinh gì — đúng cái đợt này đi sửa.
    """
    assert "co_trong_so" in KHOI, "man hinh khong doc co cua cua hep"
    assert "CHƯA GẮN VÀO SỔ" in KHOI, "khong co loi canh bao nao cho ma chua gan"
    assert "không có tour nào mang mã này" in KHOI, "go mot ma khong ton tai van im lang"
    assert "không có đối tượng nào mang mã này" in KHOI


def test_r7sob_5_quy_tac_4_van_con():
    """Ô trống vẫn là CHƯA CÓ SỐ — đợt này không được làm hỏng luật của đợt trước."""
    assert "const oSo = (v: any) =>" in MH
    xau = re.findall(r"\|\| 0\)", KHOI)
    assert not xau, f"khoi So ke toan co {len(xau)} cho thay o trong bang 0"
