# -*- coding: utf-8 -*-
"""Đợt GTGT-2 07/11/2026 — THẺ ĐỌC «BÙ TRỪ THUẾ GTGT» TRÊN MÀN KẾT SỔ.

Đợt GTGT-1 (PR #703) đưa hai cửa `GET /ket-so/bu-tru-gtgt/xem-truoc` và `POST /ket-so/bu-tru-gtgt`
vào main, nhưng KHÔNG màn hình nào gọi. Lại đúng một «cửa mồ côi» — thứ đã dọn hai lần ngày
06/11/2026 (Đợt R5b-2 và V341-1). Theo ranh giới công việc 09/9/2026, một con số không có chỗ để
đọc là việc CÒN THIẾU, không phải việc đã xong.

ĐỢT NÀY KHÔNG ĐỔI MỘT CON SỐ NÀO: không đụng `ket_so.py`, không đụng bảng quyền (màn `/ket-so`
đã khai sẵn nhóm `/api/v1/ket-so`).

BỐN LUẬT:
  1. Cửa trả ĐỦ mọi ô thẻ đọc — thiếu một ô là thẻ in `undefined` giữa một bảng tiền.
  2. Thẻ được GỌI đúng một lần, và KHÔNG tự cộng lại con số nào.
  3. Thẻ in ra MỌI cảnh báo máy chủ trả, và chỉ hiện nút ghi khi máy chủ nói ghi được.
  4. Đợt này không mở nhóm API mới cho màn Kết sổ.
"""
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_gtgt2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_gtgt2.db"):
    os.remove("test_gtgt2.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "ket-so", "page.tsx")


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


def _than_the():
    """Cắt RIÊNG khối thẻ để đo, không đo cả tệp.

    `ket-so/page.tsx` có nhiều nút ghi thật ở chỗ khác (ghi sổ sao kê, kết chuyển, khóa kỳ) — đo
    cả tệp là đo nhầm người, đúng bài học Đợt R5b-2 (06/11/2026).
    """
    s = open(MAN, encoding="utf-8").read()
    i = s.find("<b>Bù trừ thuế GTGT đầu vào – đầu ra</b>")
    assert i > 0, "không thấy thân thẻ bù trừ GTGT trên màn Kết sổ"
    j = s.find("</div>)}", i)
    assert j > i, "không cắt được thân thẻ"
    return s, s[i:j]


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_gtgt2_1_cua_tra_du_moi_o_the_doc():
    """Thẻ đọc ô nào thì cửa phải có ô ấy.

    Ô thiếu thì thẻ in `undefined`, và `undefined` giữa một bảng tiền tệ hơn một ô trống: người
    đọc tưởng số bằng không.
    """
    r = client.get("/api/v1/ket-so/bu-tru-gtgt/xem-truoc", headers=login("ketoan"),
                   params={"ky": "2026-03"})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    for o in ("da_ghi", "chung_tu", "ky_ke_khai", "da_bat", "dau_ra_phai_nop",
              "dau_vao_duoc_khau_tru", "so_bu_tru", "con_phai_nop", "con_duoc_khau_tru",
              "tk_no", "tk_co", "but_toan", "canh_bao", "ghi_chu"):
        assert o in d, "cửa thiếu ô `" + o + "` mà thẻ đọc"

    # Và thẻ phải ĐỌC đúng những ô ấy — khai ở cửa mà thẻ không dùng thì cũng vô nghĩa.
    _, than = _than_the()
    for o in ("dau_ra_phai_nop", "dau_vao_duoc_khau_tru", "so_bu_tru", "con_phai_nop",
              "con_duoc_khau_tru", "tk_no", "tk_co", "ky_ke_khai", "da_ghi", "chung_tu"):
        assert "gt." + o in than, "thẻ không đọc ô `" + o + "`"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_gtgt2_2_the_duoc_goi_DUNG_MOT_lan_va_KHONG_tu_cong_lai():
    """Cộng ở màn hình là cộng cái mình đang thấy rồi gọi nó là tổng.

    Mọi con số của thẻ này phải lấy thẳng từ máy chủ — máy chủ đã tính `min(đầu ra, đầu vào)` và
    đã trừ ra `con_phai_nop` / `con_duoc_khau_tru`. Thẻ tính lại là dựng một nguồn sự thật thứ hai.
    """
    s, than = _than_the()
    assert ".reduce(" not in than, "thẻ tự cộng lại bằng `.reduce(`"
    assert "Math.min(" not in than and "Math.max(" not in than, (
        "thẻ tự chọn số nhỏ hơn — việc ấy của máy chủ, và hai chỗ cùng chọn thì sớm muộn lệch nhau")
    assert s.count("<b>Bù trừ thuế GTGT đầu vào – đầu ra</b>") == 1, (
        "thẻ được gọi nhiều hơn một lần trên màn hình")
    assert s.count("const buTruGt") == 1 and s.count("onClick={buTruGt}") == 1, (
        "hàm ghi phải khai một lần và gắn vào đúng một nút")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_gtgt2_3_in_ra_MOI_canh_bao_va_chi_hien_nut_khi_ghi_duoc():
    """Hai điều, và cả hai là chỗ Đợt R2-KC1 (23/10/2026) đã mất một lần.

    Một dấu không ai đọc được thì bằng không có dấu: cửa trả `canh_bao` mà thẻ không in thì câu
    «chưa đặt kỳ kê khai» hay «có tiền nằm trên tài khoản cha» không tới được người nào.

    Và nút chỉ hiện khi máy chủ nói ghi được — hiện một nút chỉ để nhận 400 là mời người bấm vào
    một cánh cửa khoá.
    """
    _, than = _than_the()
    assert "gt.canh_bao?.map(" in than, (
        "thẻ không in `canh_bao` của máy chủ — cảnh báo không tới được người nào")
    assert "gt.ghi_chu" in than, "thẻ không in câu đối chiếu tờ khai [40] / [43]"
    assert "!gt.da_ghi" in than and "gt.da_bat" in than, (
        "nút ghi không xét `da_ghi` và `da_bat` — sẽ hiện cả khi đã ghi hoặc chưa đặt kỳ kê khai")
    assert "but_toan" in than, "nút ghi không xét có bút toán nào để ghi không"

    # Đo bằng CỬA THẬT: chưa đặt kỳ kê khai thì `da_bat` phải là False, tức nút phải ẩn.
    d = client.get("/api/v1/ket-so/bu-tru-gtgt/xem-truoc", headers=login("ketoan"),
                   params={"ky": "2026-03"}).json()
    assert d["da_bat"] is False, (
        "bộ dữ liệu mẫu để trống `gtgt_ky_ke_khai` nên `da_bat` phải là False — nếu khác thì ai "
        "đó đã điền sẵn một chính sách thuế vào bộ mặc định")
    assert any("gtgt_ky_ke_khai" in c for c in d["canh_bao"]), (
        "chưa đặt kỳ kê khai mà cửa không nói tên tham số cần đặt")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_gtgt2_4_KHONG_mo_nhom_API_moi_cho_man_ket_so():
    """Đợt này không ký nới quyền.

    Thẻ chỉ gọi cửa trong nhóm `/api/v1/ket-so` mà màn hình đã khai sẵn. Gọi ra ngoài nhóm là
    buộc phải thêm một dòng vào bảng quyền, và dòng ấy cộng phạm vi cho MỌI vai đang có màn này
    (bài học Đợt R5b-2).
    """
    from app.services.access import MAN_HINH_API
    assert "/api/v1/ket-so" in MAN_HINH_API["/ket-so"], (
        "màn `/ket-so` không còn khai nhóm `/api/v1/ket-so` — DỪNG LẠI")

    s = open(MAN, encoding="utf-8").read()
    i = s.find("const taiGt = useCallback(")
    j = s.find("\n  const ketChuyen", i + 1)
    khoi = s[i:j if j > i else len(s)] if i > 0 else ""
    assert khoi, "không cắt được khối hàm của thẻ"
    for p in re.findall(r'api<any>\(`([^`]+)`', khoi) + re.findall(r'api<any>\("([^"]+)"', khoi):
        assert p.startswith("/ket-so/"), (
            "thẻ gọi `" + p + "` nằm ngoài nhóm `/api/v1/ket-so`")

    # Và một vai ngoài Kế toán vẫn không ghi được — «không nới quyền» phải đo được ở cửa, không
    # chỉ đúng trên giấy.
    r = client.post("/api/v1/ket-so/bu-tru-gtgt", json={"ky": "2026-03"}, headers=login("kd.hoa"))
    assert r.status_code == 403, (
        "một vai Kinh doanh phải nhận 403 ở cửa ghi bù trừ GTGT, nhận " + str(r.status_code))
