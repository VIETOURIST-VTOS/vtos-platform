"""ĐỢT R7-SO 28/10/2026 — MÀN HÌNH SỔ KẾ TOÁN: NĂM LUẬT CANH.

Phân hệ `/api/v1/books` có 13 sổ từ Đợt R4a–R4b, kèm một cửa danh mục viết sẵn "để dựng menu
Sổ kế toán giống MISA". Suốt ba tuần KHÔNG MÀN HÌNH NÀO GỌI NÓ: `/accounting` gọi `/ledger` và
`/trial-balance` — hai cửa cũ, hẹp hơn. Nên 13 sổ ấy, trên thực tế, chưa ai mở được.

Năm luật dưới đây canh đúng năm chỗ dễ tuột lại: bộ chọn lệch danh mục, quyền hụt, thẻ cũ sống
sót, danh sách Excel khai tay, và ô trống bị thay bằng số không.
"""
import os
import re
import sys
from pathlib import Path

# CACH CA KHO NAY KHAI DUONG DAN: moi tep phep thu tu them `backend/` vao sys.path, vi
# `tests/run_all.sh` chay pytest TU `backend/`, con nguoi go tay thi hay chay tu goc kho.
# Lan chay dau 28/10/2026 do dung hai luat duoi vi thieu dong nay — khong phai loi cua ma.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENV", "dev")

GOC = Path(__file__).resolve().parents[2]
MH = (GOC / "web" / "app" / "accounting" / "page.tsx").read_text(encoding="utf-8")
CUA = (GOC / "backend" / "app" / "api" / "v1" / "books.py").read_text(encoding="utf-8")


def _khoa_danh_muc() -> set:
    """Khóa của 13 sổ, đọc từ CHÍNH hàm `catalog` trong cửa — không chép tay sang đây."""
    than = CUA.split('@router.get("")', 1)[1].split("@router.get", 1)[0]
    return set(re.findall(r'\{"key": "([a-z0-9\-]+)"', than))


def _duong_cua() -> set:
    return set(re.findall(r'@router\.get\("/([a-z0-9\-]+)"\)', CUA))


def test_r7so_1_bo_chon_va_danh_muc_khop_nhau():
    """Mỗi sổ trong bộ chọn phải có cửa thật, và mỗi sổ của danh mục phải lên màn hình.

    Hai chiều, vì một chiều vẫn hụt: thiếu chiều "danh mục → màn hình" thì thêm sổ mới ở máy
    chủ xong không ai nhớ mở cửa cho người dùng — ĐÚNG CÁI ĐÃ XẢY RA suốt ba tuần.
    """
    danh_muc = _khoa_danh_muc()
    assert len(danh_muc) == 13, "danh muc so doi so luong: " + repr(sorted(danh_muc))
    nhom = set(re.findall(r'"([a-z0-9\-]+)"', MH.split("const SO_NHOM", 1)[1].split("];", 1)[0]))
    thieu_cua = sorted(k for k in nhom if k not in _duong_cua())
    assert not thieu_cua, "bo chon co so KHONG co cua: " + repr(thieu_cua)
    thieu_man_hinh = sorted(danh_muc - nhom)
    assert not thieu_man_hinh, "danh muc co so chua len man hinh: " + repr(thieu_man_hinh)
    bang_cot = MH.split("const SO_COT", 1)[1].split("\n};", 1)[0]
    thieu_cot = sorted(k for k in danh_muc if '"' + k + '":' not in bang_cot)
    assert not thieu_cot, "so chua khai cot de hien thi: " + repr(thieu_cot)


def test_r7so_2_ke_toan_truong_mo_duoc_man_hinh_va_cua():
    """Kế toán trưởng phải vào được `/accounting` VÀ đọc được `/api/v1/books`.

    Mở cửa mà không mở menu thì người có chìa khóa vẫn không thấy cửa. Đợt R4b-2b mở cửa
    23/10/2026; đợt này mở nốt menu.
    """
    from app.services import access as AC
    from app.api.v1 import books as API

    assert "ketoan_truong" in AC.MENU_ROLES["/accounting"]
    assert "ketoan_truong" in API.READ
    assert "/api/v1/books" in AC.MAN_HINH_API["/accounting"]


def test_r7so_3_truong_phong_dieu_hanh_khong_thay_the_so():
    """`tp_dh` vào `/accounting` xem hóa đơn của đoàn, nhưng KHÔNG thấy thẻ Sổ kế toán.

    `books.READ` đã chặn vai ấy, nên để thẻ hiện ra chỉ tạo một nút bấm vào là 403. Giao diện
    ẩn cho đỡ khó chịu; CHẶN THẬT vẫn ở `require_roles` của cửa — luật này canh cả hai vế.
    """
    from app.api.v1 import books as API

    assert "tp_dh" not in API.READ, "cua so ke toan da mo cho tp_dh — luat nay phai xem lai"
    assert 'user?.role !== "tp_dh"' in MH
    assert 'k !== "so" || xemSo' in MH
    assert '{tab === "so" && xemSo &&' in MH, "khoi So chua chan khi vao bang ?tab=so"


def test_r7so_4_hai_the_cu_da_bien():
    """Hai thẻ cũ phải BIẾN, không phải nằm cạnh thẻ mới.

    Để cạnh nhau là để hai sổ cái trên một màn hình: một bản có TK đối ứng và Dư Nợ/Dư Có, một
    bản không. Sớm muộn có người đối chiếu nhầm bản, và không ai biết mình đang xem bản nào.
    """
    bang = MH.split("const TABS", 1)[1].split("];", 1)[0]
    assert '"ledger"' not in bang and '"tb"' not in bang, "the cu con trong danh sach the"
    assert '"so", "Sổ kế toán"' in bang
    assert 'tab === "ledger"' not in MH and 'tab === "tb"' not in MH, "khoi hien thi cu con song"
    assert "/trial-balance?period=" not in MH and "/ledger?account=" not in MH


def test_r7so_5_danh_sach_excel_khop_cua_va_o_trong_khong_thanh_so_khong():
    """Hai món một luật: danh sách Excel phải ĐO từ cửa, và ô trống không được thành 0.

    Danh sách khai tay thì hôm nay đúng, thêm một `.xlsx` ở máy chủ là lệch — cùng bài học Đợt
    ĐÓNG-SỔ: HỎI HỆ THỐNG, ĐỪNG GÕ TAY.

    Quy tắc 4 là luật của cả kho: ô trống là CHƯA CÓ SỐ. Ở Bảng cân đối tài khoản, ô "Dư cuối
    Nợ" trống nghĩa là số dư KHÔNG nằm bên Nợ — viết 0 vào đó là nói sai một điều kế toán.
    """
    khai = set(re.findall(r'"([a-z0-9\-]+)"', MH.split("const SO_XLSX", 1)[1].split("];", 1)[0]))
    that = set(re.findall(r'@router\.get\("/([a-z0-9\-]+)\.xlsx"\)', CUA))
    assert khai == that, "danh sach Excel lech cua: thua " + repr(sorted(khai - that)) + ", thieu " + repr(sorted(that - khai))

    than = MH.split("function SoKeToanPanel", 1)[1]
    assert "const oSo = (v: any) =>" in MH, "thieu ham hien thi so dung chung"
    xau = re.findall(r"\|\| 0\)", than)
    assert not xau, "khoi So ke toan co " + str(len(xau)) + " cho thay o trong bang 0"
