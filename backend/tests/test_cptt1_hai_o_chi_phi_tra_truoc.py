# -*- coding: utf-8 -*-
"""Đợt CPTT-1 07/11/2026 — HAI Ô CÒN THIẾU CỦA CHI PHÍ TRẢ TRƯỚC 242.

Phân bổ 242 ĐÃ CÓ SẴN gần hết — bảng, phép tính, bút toán `Nợ TK chi phí / Có 242`, cửa
`POST /api/v1/prepaid`, màn `/tai-san`, bảng quyền. Đo trên main 07/11/2026 trước khi viết một
dòng nào, và nhờ đo mà đợt này KHÔNG dựng một cửa 242 thứ hai.

Chỗ thiếu thật là hai ô trên MÀN HÌNH: bảng có cột `expense_account` và `project_code`, cửa
`PrepaidIn` NHẬN cả hai, nhưng form không gửi — nên `create_prepaid` rơi vào mặc định `"6423"`
(Chi phí đồ dùng văn phòng). Bảo hiểm xe lẽ ra vào 6323, thuê văn phòng lẽ ra vào 6427, tất cả
chạy vào 6423; sổ vẫn cân, chỉ cơ cấu chi phí là sai, và người nhập không có cách nào chọn khác.

BỐN LUẬT:
  1. Cửa BẮT BUỘC `expense_account`, và mặc định `6423` đã biến mất khỏi `create_prepaid`.
  2. Chỉ nhận TÀI KHOẢN CHI TIẾT — tài khoản cha bị từ chối.
  3. Cửa danh mục trả đúng bộ TK nhận phân bổ, và KHÔNG có tài khoản cha nào trong đó.
  4. Màn hình gửi cả hai ô, và NÓI RA khoản nào đang mang TK mặc định cũ.

ĐƯỜNG NẠP EXCEL KHÔNG NẰM TRONG ĐỢT NÀY (Chủ tịch chốt 07/11/2026): `intake_phong_ban_2._cc_nap`
tạo thẳng `PrepaidExpense`, không đi qua `create_prepaid`, nên vẫn rơi vào mặc định của MÔ HÌNH.
Thêm một cột vào mẫu Excel là đổi một tệp nhân viên đang dùng — đáng một đợt riêng. Luật 4 canh
rằng màn hình NÓI RA những khoản ấy thay vì để chúng lẫn vào.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_cptt1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_cptt1.db"):
    os.remove("test_cptt1.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "tai-san", "page.tsx")


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


def _them(**o):
    goc = {"name": "CPTT-1 dựng cảnh", "kind": "cp_tra_truoc", "start_date": "2027-01-01",
           "amount": 12_000_000, "months": 12}
    return client.post("/api/v1/prepaid", headers=login("ketoan"), json={**goc, **o})


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_cptt1_1_cua_BAT_BUOC_tk_chi_phi_va_mac_dinh_6423_da_bien_mat():
    """Để mặc định là để máy trả lời hộ một câu chưa ai hỏi — và câu trả lời ấy sai với hầu hết
    khoản mục. Hai chiều, và cần cả hai.
    """
    thieu = _them(code="CPTT1-THIEU")
    assert thieu.status_code == 422, (
        "không gửi TK chi phí mà cửa vẫn nhận (" + str(thieu.status_code) + ") — khoản ấy sẽ "
        "phân bổ vào 6423 mà không ai chọn")
    assert "chi phí" in thieu.text.lower(), "câu từ chối phải nói rõ thiếu ô nào: " + thieu.text[:200]

    ok = _them(code="CPTT1-OK", expense_account="627", project_code="CPTT1TOUR")
    assert ok.status_code == 201, ok.text[:300]
    d = ok.json()
    assert d["expense_account"] == "627", "cửa không giữ TK chi phí đã gửi: " + repr(d["expense_account"])
    assert d["project_code"] == "CPTT1TOUR", "cửa không giữ mã công trình đã gửi"

    # Mặc định `6423` phải BIẾN MẤT khỏi `create_prepaid`, không chỉ bị ô bắt buộc che đi.
    import inspect
    from app.services import assets as AS
    than = inspect.getsource(AS.create_prepaid)
    # BỎ CHÚ THÍCH TRƯỚC KHI TÌM. Thân hàm ấy có một câu chú thích nhắc lại `"6423"` để giải
    # thích vì sao mặc định bị bỏ — không bỏ chú thích thì phép đo khớp vào chính câu ấy và đỏ
    # trong khi mã đã sạch. Đúng cái bẫy đã làm Đợt TZ-1 đỏ một lần (06/11/2026).
    than_ma = "\n".join(d.split("#")[0] for d in than.split("\n"))
    assert '"6423"' not in than_ma, (
        "`create_prepaid` vẫn còn mặc định `6423` — ô bắt buộc chỉ che nó đi, và lần sau ai nới "
        "ô ấy ra thì mặc định quay lại mà không ai thấy")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_cptt1_2_chi_nhan_TAI_KHOAN_CHI_TIET_khong_nhan_tai_khoan_cha():
    """Chủ tịch chốt 07/11/2026: không hạch toán vào tài khoản cha.

    `642` và `641` đều LÀ tài khoản cha trên danh mục — nhận chúng ở đây là tự tay dựng thêm chỗ
    phải nắn lại ở đợt chặn.
    """
    cha = _them(code="CPTT1-CHA", expense_account="642")
    assert cha.status_code == 422, (
        "`642` là tài khoản cha mà cửa vẫn nhận (" + str(cha.status_code) + ")")
    assert "642" in cha.text, "câu từ chối phải nói rõ tài khoản nào"

    bia = _them(code="CPTT1-BIA", expense_account="9999")
    assert bia.status_code == 422, "tài khoản không có trong danh mục mà cửa vẫn nhận"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_cptt1_3_cua_danh_muc_tra_dung_bo_TK_nhan_phan_bo():
    """Màn hình dựng ô chọn từ cửa này. Cửa trả sai thì ô chọn sai, và không ai đọc mã để biết."""
    r = client.get("/api/v1/assets/meta", headers=login("ketoan"))
    assert r.status_code == 200, r.text[:300]
    ds = r.json().get("tk_chi_phi")
    assert ds, "cửa `/assets/meta` chưa trả danh mục `tk_chi_phi` — màn hình lấy đâu ra ô chọn"
    ma = [x["ma"] for x in ds]
    assert all("ma" in x and "ten" in x for x in ds), "mỗi dòng phải có cả mã lẫn tên"
    assert "6423" in ma and "6422" in ma and "627" in ma, (
        "thiếu TK chi tiết lẽ ra phải có: " + repr(ma[:14]))
    # 632x KHÔNG được có mặt: MISA không liệt kê giá vốn làm đích phân bổ, và chi phí đội xe ở
    # VTOS đi 627 → 154 → 632 qua bước 0 của kết sổ. Cho chọn thẳng 632x là tính hai lần.
    assert not [x for x in ma if x.startswith("632")], (
        "danh mục có tài khoản giá vốn 632x — chi phí sẽ bị tính hai lần: " + repr(ma))
    # KHÔNG tài khoản cha nào được lọt vào ô chọn.
    assert "642" not in ma and "641" not in ma, (
        "danh mục ô chọn còn tài khoản CHA — " + repr([x for x in ma if x in ("641", "642")]))
    # Và không nhóm nào ngoài đích phân bổ.
    la = [x for x in ma if not x.startswith(("154", "622", "623", "627", "635", "641", "642", "241"))]
    assert not la, "danh mục có tài khoản ngoài nhóm nhận phân bổ: " + repr(la)


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_cptt1_4_man_hinh_gui_ca_hai_o_va_NOI_RA_khoan_mang_tk_mac_dinh_cu():
    """Hai ô có trên form thì chưa đủ — chúng phải ĐI VÀO thân yêu cầu.

    Và màn hình phải nói ra những khoản nhập trước đợt này: chúng vẫn mang `6423` vì đường nạp
    Excel (`intake_phong_ban_2._cc_nap`) tạo thẳng bản ghi, không đi qua cửa. Im chỗ đó là để
    chúng lẫn vào những khoản đã chọn đúng.
    """
    assert os.path.exists(MAN), "không thấy web/app/tai-san/page.tsx"
    s = open(MAN, encoding="utf-8").read()
    i = s.find("const ghi = async")
    j = s.find("\n  const ", i + 1)
    than_luu = s[i:j if j > i else len(s)] if i > 0 else ""
    assert than_luu, "không cắt được thân hàm `ghi` trên màn hình"
    # Hai ô này chỉ đúng cho NHÁNH chi phí trả trước, nên phải nằm trong nhánh `else` ấy chứ
    # không rải chung cho cả tài sản cố định — TSCĐ có đường khấu hao riêng.
    assert "amount: soTien(f.cost)" in than_luu, "không thấy nhánh chi phí trả trước trong `ghi`"
    for o in ("expense_account", "project_code"):
        assert o in than_luu, (
            "thân yêu cầu KHÔNG gửi `" + o + "` — ô có trên form mà không đi vào máy chủ thì "
            "bằng không có ô")
    assert "tk_chi_phi" in s, "màn hình không đọc danh mục TK chi phí từ `/assets/meta`"
    assert "CANH_BAO_TK_CU" in s, (
        "màn hình chưa nói ra khoản nào đang mang TK mặc định cũ — đường nạp Excel vẫn tạo ra "
        "chúng, và đợt này cố ý chưa bịt đường ấy")
