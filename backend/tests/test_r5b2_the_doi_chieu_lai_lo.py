# -*- coding: utf-8 -*-
"""Đợt R5b-2 06/11/2026 — THẺ ĐỌC «ĐỐI CHIẾU LÃI LỖ TOUR» TRÊN MÀN KẾT SỔ.

Cửa `/api/v1/accounting/doi-chieu-lai-lo` vào main hôm nay (Đợt R5b-1, viết 02/11 và nằm chờ bấm
bốn ngày). Nhưng KHÔNG màn hình nào gọi nó — và theo ranh giới công việc 09/9/2026, một con số
không có chỗ để đọc là việc CÒN THIẾU, không phải việc đã xong. Đúng hình Đợt TKC-1 sáng nay.

ĐỢT NÀY KHÔNG ĐỔI MỘT CON SỐ NÀO. Nó chỉ mở một chỗ để đọc con số đã có. Không đụng máy chủ,
không đụng bảng quyền, không đụng `lai_lo_tour` hay `books`.

ĐO BẰNG CỬA THẬT qua `TestClient`, không đọc mã nguồn — trừ đúng hai luật nói VỀ màn hình, và
hai luật ấy nói rõ chúng đang đọc tệp giao diện.
"""
import os
import re
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_r5b2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_r5b2.db"):
    os.remove("test_r5b2.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "ket-so", "page.tsx")
CUA = "/api/v1/accounting/doi-chieu-lai-lo"
TU, DEN = "2026-10-01", "2026-10-31"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _doc(**q):
    r = client.get(CUA, params={"tu": TU, "den": DEN, **q}, headers=login("ketoan"))
    assert r.status_code == 200, f"{CUA} trả {r.status_code}: {r.text[:300]}"
    return r.json()


def _than_the():
    """Thân hàm thẻ trên màn hình, cắt riêng — KHÔNG đo cả tệp.

    Cả tệp `ket-so/page.tsx` có nút ghi thật ở chỗ khác (ghi sổ sao kê, kết chuyển, khóa kỳ).
    Đo cả tệp là đo nhầm người: thẻ này phải chỉ đọc, cả màn hình thì không.
    """
    assert os.path.exists(MAN), "khong thay web/app/ket-so/page.tsx"
    s = open(MAN, encoding="utf-8").read()
    i = s.find("function DoiChieuLaiLo(")
    assert i > 0, (
        "Chưa có thẻ `DoiChieuLaiLo` trên màn Kết sổ — cửa `doi-chieu-lai-lo` vẫn không ai gọi, "
        "và một con số không có chỗ đọc là việc còn thiếu (ranh giới 09/9/2026).")
    j = s.find("\nfunction ", i + 1)
    return s, s[i:j if j > 0 else len(s)]


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_r5b2_1_cua_tra_du_moi_o_ma_the_doc():
    """Thẻ đọc ô nào thì cửa phải trả ô ấy — liệt kê ra, không tin ngầm.

    Vì sao phải đo: thiếu một ô thì thẻ KHÔNG đỏ, nó chỉ hiện trống hoặc `undefined`. Một màn
    hình nói sai mà không ai thấy nó nói sai là thứ tệ hơn một màn hình hỏng hẳn.
    """
    d = _doc()
    thieu = [k for k in ("tu", "den", "dong", "tong_dong", "hien_dong", "cat_bot", "cong",
                         "chi_co_trong_so", "chi_co_bang_tinh", "canh_bao", "khop",
                         "co_so_ngay", "ghi_chu") if k not in d]
    assert not thieu, "cửa thiếu ô mà thẻ đọc: " + repr(thieu)
    thieu_c = [k for k in ("so_dong_so_duoc", "so_dong_chua_so_duoc",
                           "so_doanh_thu", "so_chi_phi", "so_loi_nhuan",
                           "bt_doanh_thu", "bt_gia_von", "bt_loi_nhuan",
                           "lech_doanh_thu", "lech_chi_phi", "lech_loi_nhuan")
               if k not in (d["cong"] or {})]
    assert not thieu_c, "`cong` thiếu ô mà dòng Cộng đọc: " + repr(thieu_c)
    for k in ("so", "bang_tinh"):
        assert (d["co_so_ngay"] or {}).get(k), (
            "`co_so_ngay` thiếu vế `" + k + "`. Hai cơ sở ngày khác nhau mà màn hình không nói "
            "ra thì người đọc tưởng hai cột cùng một khoảng — và lệch thật bị đọc thành lỗi.")
    for cb in d["canh_bao"]:
        assert {"loai", "muc", "so_dong", "ten", "chi_tiet"} <= set(cb), repr(cb)


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_r5b2_2_dong_Cong_chi_gop_dong_SO_DUOC_va_the_khong_tu_cong_lai():
    """Hai vế, và cần cả hai.

    (a) Máy chủ: `cong` chỉ gộp dòng so được cả hai bên — `so_dong_so_duoc` cộng
        `so_dong_chua_so_duoc` phải đúng bằng `tong_dong`, không hơn không kém.
    (b) Màn hình: dòng Cộng phải LẤY THẲNG từ `cong`, KHÔNG tự cộng lại từ `dong` — vì `dong` bị
        cắt ở `gioi_han`, nên cộng ở màn hình là cộng một phần rồi gọi đó là tổng.
    """
    d = _doc()
    c = d["cong"]
    assert c["so_dong_so_duoc"] + c["so_dong_chua_so_duoc"] == d["tong_dong"], (
        "so được " + str(c["so_dong_so_duoc"]) + " + chưa so được "
        + str(c["so_dong_chua_so_duoc"]) + " ≠ tổng " + str(d["tong_dong"]))
    # Cắt thật chặt: tổng và `cong` KHÔNG được đổi theo `gioi_han`.
    hep = _doc(gioi_han=1)
    assert hep["tong_dong"] == d["tong_dong"], "`tong_dong` đổi theo `gioi_han`"
    assert hep["cong"] == c, "`cong` đổi theo `gioi_han` — nó phải là tổng, không phải tổng phần"
    assert len(hep["dong"]) <= 1 and hep["hien_dong"] == len(hep["dong"])

    _s, than = _than_the()
    # Dòng Cộng đọc `cong` của máy chủ.
    assert "c.so_loi_nhuan" in than and "c.bt_loi_nhuan" in than and "c.lech_loi_nhuan" in than, (
        "Dòng Cộng không đọc `cong` của máy chủ.")
    # Và KHÔNG tự cộng lại từ `dong`.
    tu_cong = re.findall(r"\.(?:reduce|map)\s*\(", than)
    assert "reduce(" not in than, (
        "Thẻ có `reduce(` — nghi là tự cộng lại từ `dong`, mà `dong` đã bị cắt ở `gioi_han`. "
        "Dòng Cộng phải lấy thẳng từ `cong` của máy chủ. (tìm thấy: " + repr(tu_cong) + ")")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_r5b2_3_CHI_DOC_va_dong_thieu_mot_ben_la_TRANG_THAI_THU_BA():
    """Đối chiếu là để NÓI RA chênh lệch, không để sửa cho khớp.

    Và: dòng thiếu một bên phải hiện «chưa so được», KHÔNG phải một con số lệch. Một tour chưa
    ghi sổ mà báo lệch 900 triệu là nói SỔ SAI, trong khi sự thật là sổ chưa có gì.
    """
    for cach in ("post", "put", "patch", "delete"):
        r = getattr(client, cach)(CUA, headers=login("ketoan"))
        assert r.status_code in (404, 405), (
            cach.upper() + " " + CUA + " trả " + str(r.status_code) + " — cửa phải CHỈ ĐỌC.")
    _s, than = _than_the()
    xau = [m for m in re.findall(r'method:\s*"([A-Z]+)"', than) if m != "GET"]
    assert not xau, "thẻ `DoiChieuLaiLo` có đường ghi " + repr(xau) + " — nó phải CHỈ ĐỌC."
    assert "chua_so_duoc" in than, (
        "Thẻ không xét `chua_so_duoc`. Thiếu nó thì dòng thiếu một bên sẽ in ra một con số lệch "
        "bịa — và con số ấy đổ oan cho bên có số.")
    # Máy chủ cũng phải giữ đúng chiều ấy: dòng `chua_so_duoc` thì lệch là None, không phải 0.
    for r in _doc()["dong"]:
        if r["chua_so_duoc"]:
            assert r["lech_loi_nhuan"] is None, (
                "dòng " + str(r["ma"]) + " chưa so được mà lệch = " + repr(r["lech_loi_nhuan"])
                + " — phải là rỗng, vì 0 đọc như «hai bên bằng nhau».")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_r5b2_4_the_duoc_GOI_dung_mot_lan_va_KHONG_mo_rong_cho_ai():
    """Khai một thẻ mà không gọi thì vẫn không ai đọc được — đo cả hai.

    Và đợt này KHÔNG nới quyền: cửa giữ nguyên bộ vai `READ` của kế toán, cố ý không mở cho Điều
    hành (bảng đối chiếu với sổ là việc của Kế toán; mở cho Điều hành là bày sổ kế toán ra một
    màn hình Điều hành — quyền chưa ai ký). Đo bằng một vai NGOÀI `READ` nhận 403.
    """
    s, _than = _than_the()
    assert s.count("<DoiChieuLaiLo />") == 1, (
        "Thẻ phải được gọi ĐÚNG MỘT lần trên màn hình (đếm được "
        + str(s.count("<DoiChieuLaiLo />")) + ").")
    # ĐẶT Ở `/ket-so` LÀ MỘT QUYẾT ĐỊNH VỀ QUYỀN, không phải chuyện bày biện — nên luật đo nó.
    #
    # Màn `/accounting` KHÔNG khai nhóm `/api/v1/accounting` trong `MAN_HINH_API`, nên đặt thẻ ở
    # đó buộc phải thêm một dòng vào bảng quyền, và dòng ấy cộng vào `pham_vi_day_du` — bảng ký
    # sẽ nói `tp_dh` với tới được cửa này, đúng thứ Đợt R5b-1 cố ý không mở. `/ket-so` đã khai
    # sẵn cả nhóm ấy. Chủ tịch chốt 06/11/2026.
    from app.services import access as AC
    assert "/api/v1/accounting" in AC.MAN_HINH_API.get("/ket-so", ()), (
        "`/ket-so` không còn khai nhóm `/api/v1/accounting` — thẻ mất chỗ đứng, DỪNG LẠI.")
    assert "/api/v1/accounting/doi-chieu-lai-lo" not in AC.MAN_HINH_API.get("/accounting", ()), (
        "Bảng quyền đã khai cửa đối chiếu cho màn `/accounting`. Đó là NỚI quyền: `tp_dh` thấy "
        "màn ấy, nên `pham_vi_day_du` sẽ nói Điều hành với tới được bảng đối chiếu với sổ — "
        "đúng thứ Đợt R5b-1 cố ý không mở. Nếu đây là quyết định mới thì phải có chữ ký.")
    assert "<TienCapCha />" in s, (
        "Thẻ «tài khoản cha» biến mất khỏi màn Kết sổ — hai thẻ đối chiếu vốn đứng cạnh nhau.")
    r = client.get(CUA, params={"tu": TU, "den": DEN}, headers=login("kd.hoa"))
    assert r.status_code == 403, (
        "Vai ngoài nhóm đọc của kế toán phải nhận 403, nhận " + str(r.status_code)
        + ". Cửa này không được mở rộng cho ai trong đợt này.")
