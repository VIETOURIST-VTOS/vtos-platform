# -*- coding: utf-8 -*-
"""Đợt DỌN-R4c3 04/11/2026 — DỜI CỬA MỒ CÔI, VÀ DỰNG HAI LUẬT CHỐNG TÁI PHÁT.

Chủ tịch chốt 04/11/2026.

HAI ĐỢT, HAI NỬA CỦA MỘT CHỖ HỎNG, VÀ CẢ HAI ĐỀU XANH HẾT PHÉP THỬ

Ngày 02/11/2026 ô «hình thức thanh toán» ở màn hình đề nghị chi RỖNG trên bản chạy. Hai đợt sửa
nó, mỗi đợt một nửa, và giữa hai lần ấy KHÔNG MỘT PHÉP THỬ NÀO KÊU:

  · Đợt R4c-3 viết màn hình gọi `api("/hach-toan/bang")` — một đường KHÔNG CÓ trên máy chủ. Lỗi
    404 bị `.catch(() => {})` nuốt.
  · Đợt P2-1 thấy `test_p2` đỏ vì bản đồ thiếu đường ấy, nên khai `/api/v1/hach-toan/bang` vào
    `MAN_HINH_API["/expenses"]`. Khai đường HẸP chứ không khai cả nhóm — ý đúng. Nhưng nó khai
    một cửa KHÔNG TỒN TẠI, nên phép thử xanh lại mà ô vẫn rỗng: cái đỏ bị TẮT chứ không được CHỮA.
  · Đợt SUA-2 mới là đợt dựng THẬT cửa `GET /api/v1/hach-toan/bang`.

ĐỢT NÀY RÚT GỌN SAU KHI ĐO. Bản đầu của nó định mở thêm một cửa `/hinh-thuc-tt` cho cùng danh
sách ấy — tức là dựng NGUỒN THỨ HAI, đúng thứ nó lập luận để chống. Đo lại thấy SUA-2 đã làm
xong, nên bỏ. Còn lại một việc mã và hai luật.

HAI LUẬT, HAI CHIỀU, VÀ PHẢI ĐI THÀNH CẶP

    LUẬT 2 — màn hình gọi  →  cửa phải có thật      (chiều R4c-3 rơi vào)
    LUẬT 8 — bản đồ khai   →  cửa phải có thật      (chiều P2-1 rơi vào)

Có cả hai từ 02/11 thì cả hai đợt đã đỏ ngay trên máy. Có một thì vẫn còn một đường đi qua.

VIỆC MÃ: `@router.get("/tien-ghi-cap-cha")` nằm trên router `prefix="/api/v1"`, nên đường thật là
`/api/v1/tien-ghi-cap-cha` — một NHÓM API riêng, không màn hình nào khai, không vai nào chạm. Dời
về `/api/v1/accounting/tien-ghi-cap-cha`, nhóm mà `/ket-so` đã khai sẵn. Dời chỗ mắc, không vứt
việc: cửa ấy có lý do thật (Kế toán trưởng đi tìm từng chứng từ đã ghi tiền ở cấp cha).
"""
import os, sys, re, pathlib

os.environ["DATABASE_URL"] = "sqlite:///./test_donr4c3.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_donr4c3.db", "test_donr4c3.db-journal"):
    if os.path.exists(_f): os.remove(_f)

import pytest
from fastapi import HTTPException
from app.main import app
from app.services import access as AC

WEB = pathlib.Path(__file__).resolve().parents[2] / "web"
TRANG = WEB / "app" / "expenses" / "page.tsx"
CUA = "/api/v1/hach-toan/bang"


def _duong_that() -> set[str]:
    return {getattr(r, "path", "") for r in app.routes if getattr(r, "path", "").startswith("/api/v1/")}


def _goi_trong_trang(p: pathlib.Path) -> set[str]:
    """Mọi đường màn hình gọi, gom cả `api("/x")` lẫn `fetch("/api/v1/x")` về một dạng.

    Chép đúng cách đọc của `test_p2` để hai hàng rào không bao giờ đọc ra hai kết quả khác nhau.
    """
    src = p.read_text(encoding="utf-8")
    goi = set()
    for m in re.finditer(r'(?:api(?:<[^>]*>)?|fetch)\(\s*[`"\'](?:/api/v1)?/([a-z0-9\-]+(?:/[a-z0-9\-]+)*)', src):
        d = m.group(1)
        if d in ("api", "api/v1"):
            continue
        if d.startswith("api/v1/"):
            d = d[len("api/v1/"):]
        if d:
            goi.add("/api/v1/" + d)
    return goi


# ───────────────────────────────────────────────────────────────────── LUẬT 1
def test_donr4c3_1_cua_danh_muc_co_that_va_chi_doc():
    """Cửa Đợt SUA-2 dựng phải tồn tại, và phải CHỈ ĐỌC.

    Không luật này thì ai gỡ nó đi, màn hình lại 404 và ô lại rỗng — y như 02/11.
    """
    assert CUA in _duong_that(), f"không thấy {CUA} trong bảng đường của máy chủ"
    ghi = [r for r in app.routes
           if getattr(r, "path", "") == CUA and set(getattr(r, "methods", ())) - {"GET", "HEAD", "OPTIONS"}]
    assert not ghi, f"{CUA} phải CHỈ ĐỌC — không được có đường ghi nào"


# ───────────────────────────────────────────────────────────────────── LUẬT 2
def test_donr4c3_2_moi_duong_man_hinh_de_nghi_chi_goi_deu_co_that():
    """PHÉP ĐO QUYẾT ĐỊNH, và là luật đáng lẽ phải có từ 02/11.

    `/hach-toan/bang` không tồn tại, lời gọi trả 404, `.catch(() => {})` nuốt lỗi, ô hình thức
    thanh toán rỗng — và không một phép thử nào kêu. Một đường gọi sai là một ô rỗng câm.
    """
    if not TRANG.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    that = _duong_that()
    thieu = []
    for g in sorted(_goi_trong_trang(TRANG)):
        if g in that:
            continue
        # đường có tham số: `/api/v1/tours/{id}` khớp lời gọi `/api/v1/tours/...`
        if any(t.startswith(g.rstrip("/") + "/") and "{" in t for t in that):
            continue
        thieu.append(g)
    assert not thieu, (
        f"/expenses gọi đường KHÔNG CÓ trên máy chủ: {thieu}. Lời gọi ấy trả 404 và nếu có "
        f"`.catch` thì không ai biết. Sửa đường gọi, đừng sửa phép thử này.")


# ───────────────────────────────────────────────────────────────────── LUẬT 3
def test_donr4c3_3_moi_vai_vao_duoc_man_hinh_deu_doc_duoc_cua():
    """Không luật này thì lần sau thêm một vai vào `/expenses` là ô ấy rỗng lại — vẫn im lặng.
    403 và 404 cho ra cùng một ô rỗng trên màn hình. Nên chặn cả hai đường dẫn tới nó.

    ĐO BẰNG TẬP ĐÃ NỚI, KHÔNG PHẢI TẬP KHAI TAY. Bản đầu của luật này so thẳng với
    `AC.PAYMENT_REQUEST_ROLES` và đỏ oan ba vai — `ketoan_truong`, `ketoan_tt`, `thu_quy` — trong
    khi cả ba VÀO ĐƯỢC thật: `require_roles` gọi `VKT.mo_rong(roles)` (Đợt LG1) nên vai con thấy
    mọi cửa vai cha thấy, và `thu_quy` thì Đợt SUA-2 khai thẳng. Đúng cái bẫy «cửa mở, biển đề
    đóng» mà LG1 dựng ra để chống, chỉ là lần này ở phía phép đo.

    `require_roles` ghi tập ĐÃ NỚI vào `dep.vai_tro_yeu_cau` chính vì chuyện này. Đọc ô ấy.
    """
    from app.api.v1 import hach_toan as API_HT

    import inspect

    cho_phep = set()
    for tham_so in inspect.signature(API_HT.danh_muc_httt).parameters.values():
        phu = getattr(tham_so.default, "dependency", None)
        vai = getattr(phu, "vai_tro_yeu_cau", None)
        if vai:
            cho_phep |= set(vai)
    assert cho_phep, (
        "không đọc được `vai_tro_yeu_cau` của cửa `/hach-toan/bang` — khuôn `require_roles` đã đổi, "
        "đo lại bằng tay trước khi tin phép thử này")

    vai_man_hinh = set(AC.MENU_ROLES.get("/expenses", ()))
    assert vai_man_hinh, "không đọc được danh sách vai của /expenses"
    thieu = sorted(vai_man_hinh - cho_phep)
    assert not thieu, (
        f"các vai vào được /expenses nhưng KHÔNG đọc được {CUA}: {thieu}. "
        f"Ô hình thức thanh toán sẽ rỗng với đúng những vai ấy, và không có gì báo.")


# ───────────────────────────────────────────────────────────────────── LUẬT 4
def test_donr4c3_4_man_hinh_goi_dung_cua_da_dung():
    """Màn hình phải gọi ĐÚNG cửa Đợt SUA-2 dựng.

    Bản đầu của luật này đòi `/hach-toan/bang` KHÔNG tồn tại — viết theo ảnh main ngày 03/11, khi
    SUA-2 chưa gộp. Bấm thật ngày 04/11 thì nó đỏ, và nó đỏ ĐÚNG: main đã đi tiếp, cửa đã có thật.
    Ghi lại đây vì đó là bài học của cả đợt — một phép đo viết theo ảnh cũ của main là một phép đo
    nói về quá khứ.
    """
    if not TRANG.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    assert CUA in _goi_trong_trang(TRANG), f"/expenses không còn gọi {CUA}"


# ───────────────────────────────────────────────────────────────────── LUẬT 5
def test_donr4c3_5_khai_dung_cua_hep_khong_khai_ca_nhom():
    """Khai cả nhóm `/api/v1/hach-toan` cho `/expenses` là trao cửa ghi quy ước và cửa ghi sổ."""
    khai = tuple(AC.MAN_HINH_API.get("/expenses", ()))
    assert CUA in khai, f"MAN_HINH_API['/expenses'] chưa khai {CUA}"
    assert "/api/v1/hach-toan" not in khai, (
        "MAN_HINH_API['/expenses'] khai CẢ NHÓM `/api/v1/hach-toan` — thế là mở cả cửa ghi quy "
        "ước (`/quy-tac`, `/ky`) và cửa ghi sổ (`/ghi-so`) cho người đề nghị chi.")


# ───────────────────────────────────────────────────────────────────── LUẬT 6
def test_donr4c3_6_cua_tien_cap_cha_het_mo_coi():
    """Cửa của Kế toán trưởng dời về nhóm `/api/v1/accounting` mà `/ket-so` đã khai sẵn."""
    that = _duong_that()
    assert "/api/v1/tien-ghi-cap-cha" not in that, (
        "cửa còn nằm ở nhóm riêng `/api/v1/tien-ghi-cap-cha` — không màn hình nào khai, không vai "
        "nào chạm được")
    assert "/api/v1/accounting/tien-ghi-cap-cha" in that, "không thấy cửa ở chỗ mới"
    assert "/api/v1/accounting" in tuple(AC.MAN_HINH_API.get("/ket-so", ())), (
        "/ket-so không còn khai nhóm `/api/v1/accounting` — cửa lại mồ côi")


# ───────────────────────────────────────────────────────────────────── LUẬT 8
def test_donr4c3_8_ban_do_khong_tro_vao_cua_khong_co_that():
    """Chiều còn lại, và là chiều Đợt P2-1 (02/11) rơi vào.

    P2-1 chữa chỗ đỏ của `test_p2` bằng cách khai `/api/v1/hach-toan/bang` vào bản đồ. Ý nó đúng
    một nửa — CỐ Ý khai đường hẹp thay vì cả nhóm, và lý do viết ra rất rõ. Nhưng nó không đo một
    điều: đường ấy KHÔNG TỒN TẠI. Khai một cửa không có thật thì phép thử xanh lại, còn lỗi 404 và
    ô rỗng trên màn hình thì còn nguyên — cái đỏ bị TẮT chứ không được CHỮA.

    Luật 2 canh chiều «màn hình gọi → cửa phải có thật». Luật này canh chiều «bản đồ khai → cửa
    phải có thật». Thiếu một trong hai là còn một đường để im lặng đi qua.
    """
    that = _duong_that()
    chet = []
    for k in tuple(AC.MAN_HINH_API.get("/expenses", ())):
        if k in that or any(t == k or t.startswith(k.rstrip("/") + "/") for t in that):
            continue
        chet.append(k)
    assert not chet, (
        f"MAN_HINH_API['/expenses'] khai đường KHÔNG CÓ trên máy chủ: {chet}. Một dòng bản đồ trỏ "
        f"vào hư không chỉ làm phép thử xanh, không mở được cửa nào.")


# ───────────────────────────────────────────────────────────────────── LUẬT 7
def test_donr4c3_7_goi_thang_hai_hang_rao_da_do():
    """PHÉP ĐO CUỐI: gọi thẳng đúng hai luật đã đỏ trên #590, không soi chữ."""
    from tests.test_p2_pham_vi_vai_tro import (
        test_khong_nhom_api_nao_mo_coi as mo_coi,
        test_ban_do_man_hinh_api_khong_lech_voi_giao_dien as khop,
    )

    mo_coi()
    khop()
