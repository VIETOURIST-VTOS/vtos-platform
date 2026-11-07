# -*- coding: utf-8 -*-
"""Đợt A1 08/11/2026 — Ô NHẬN DIỆN NGÂN HÀNG CÓ CHỖ NHẬP.

Việc A (tiền gửi về đúng tiểu khoản) đo xong 08/11/2026 trên SỔ THẬT, và kết quả đảo ngược thứ
tự em tưởng:

  · 20 tài khoản ngân hàng đã khai, CẢ 20 đã có tiểu khoản riêng (`11211` … `112120`)
  · máy phân loại sổ đã có đủ: cửa xem trước, cửa ghi, màn hình gọi nó
  · bản đồ chứng từ nạp từ MISA đã có 22.095 dòng
  · CHẠY THẬT: 26 dòng nằm trên `1121`, khớp được ĐÚNG 0

Vì ba ô dùng để nhận diện ngân hàng — `sepay_account_number`, `match_prefixes`,
`match_keywords` — TRỐNG Ở CẢ 20 TÀI KHOẢN. Và cửa sửa chúng (`PATCH /bank-accounts/{code}`) đã
có trong mã từ lâu mà KHÔNG màn hình nào gọi: lại một «cửa mồ côi», thứ làn này đã dọn ba lần
(Đợt R5b-2, V341-1, GTGT-2 — 06 và 07/11/2026).

Theo ranh giới công việc 09/9/2026: một con số hệ thống cần mà không có cửa nhập cho người dùng
là việc CÒN THIẾU, không phải việc để máy đoán hộ. Đợt này mở đúng cái cửa ấy.

ĐỢT NÀY KHÔNG ĐỔI MỘT DÒNG SỔ NÀO: không phân loại, không ghi sổ, không đụng `1121`, không đụng
bảng quyền (màn `/bank-accounts` đã khai sẵn nhóm `/api/v1/bank-accounts`).

BỐN LUẬT:
  1. Cửa `PATCH` không còn mồ côi — màn hình GỌI nó, đúng một lần.
  2. Ba ô nhận diện ĐI VÀO bản ghi — đo bằng cửa thật, không đọc mã.
  3. Máy chủ chuẩn hóa tiền tố / từ khóa MỘT LẦN, và màn hình không chuẩn hóa lần thứ hai.
  4. Không nới quyền, và đợt này KHÔNG ghi sổ gì.
"""
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_a1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_a1.db"):
    os.remove("test_a1.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "bank-accounts", "page.tsx")


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


def _man():
    return open(MAN, encoding="utf-8").read()


def _mot_tk():
    """Một tài khoản ngân hàng để thử. Chưa có thì mở một cái — qua ĐÚNG cửa người dùng dùng."""
    r = client.get("/api/v1/bank-accounts", headers=login("ketoan"))
    assert r.status_code == 200, r.text[:300]
    rows = r.json()["rows"]
    if rows:
        return rows[0]["code"]
    t = client.post("/api/v1/bank-accounts", headers=login("ketoan"),
                    json={"code": "A1TEST", "bank_name": "Ngân hàng phép thử",
                          "account_number": "0123456789", "currency": "VND"})
    assert t.status_code == 201, t.text[:300]
    return t.json()["code"]


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_a1_1_cua_PATCH_khong_con_mo_coi():
    """Một cửa không màn hình nào gọi thì bằng không có cửa.

    Đây là lần thứ TƯ trong làn này: R5b-2 (thẻ đối chiếu), V341-1 (chi tiết vay 341), GTGT-2
    (bù trừ GTGT), và nay là đây. Lần nào cũng cùng một hình: mã đủ, hàng rào không có.
    """
    s = _man()
    assert "/bank-accounts/${encodeURIComponent(sua.code)}" in s, (
        "màn hình không gọi cửa `PATCH /bank-accounts/{code}` — cửa vẫn mồ côi")
    assert s.count('method: "PATCH"') == 1, (
        "cửa PATCH được gọi " + str(s.count('method: "PATCH"')) + " lần (cần đúng 1)")
    assert "const luuSua = " in s and "onClick={luuSua}" in s, (
        "hàm lưu phải khai một lần và gắn vào đúng một nút")
    assert s.count("onClick={luuSua}") == 1, "nút Lưu gắn nhiều hơn một chỗ"

    # Và cửa ấy phải CÒN TỒN TẠI ở máy chủ — màn hình gọi một cửa đã bị gỡ thì cũng vô nghĩa.
    ma = _mot_tk()
    r = client.patch(f"/api/v1/bank-accounts/{ma}", headers=login("ketoan"), json={"note": "a1"})
    assert r.status_code == 200, "cửa PATCH không còn chạy: " + r.text[:200]


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_a1_2_ba_o_nhan_dien_DI_VAO_ban_ghi():
    """Ô có trên form mà không tới được bản ghi thì bằng không có ô.

    Đúng chỗ Đợt CPTT-1 phát hiện ở màn tài sản, và Đợt CPTT-2 phải bịt lại lần thứ hai cho
    đường nạp Excel. Nên đo bằng CỬA THẬT: gửi đi rồi đọc lại.
    """
    ma = _mot_tk()
    r = client.patch(f"/api/v1/bank-accounts/{ma}", headers=login("ketoan"),
                     json={"sepay_account_number": "9988776655",
                           "match_prefixes": ["a1x", " a1y "],
                           "match_keywords": ["ngan hang phep thu"]})
    assert r.status_code == 200, r.text[:300]

    doc = next(x for x in client.get("/api/v1/bank-accounts", headers=login("ketoan")).json()["rows"]
               if x["code"] == ma)
    assert doc["sepay_account_number"] == "9988776655", (
        "số SePay không vào bản ghi, nhận " + repr(doc["sepay_account_number"]))
    assert doc["match_prefixes"] == ["A1X", "A1Y"], (
        "tiền tố không vào bản ghi hoặc không được chuẩn hóa, nhận " + repr(doc["match_prefixes"]))
    assert doc["match_keywords"] == ["NGAN HANG PHEP THU"], (
        "từ khóa không vào bản ghi, nhận " + repr(doc["match_keywords"]))

    # Và màn hình phải GỬI đủ ba ô — khai ô trên form mà không gửi thì cũng bằng không có ô.
    s = _man()
    for o in ("sepay_account_number:", "match_prefixes:", "match_keywords:"):
        assert o in s, "màn hình không gửi `" + o + "`"
    for o in ("form.sepay", "form.prefixes", "form.keywords"):
        assert o in s, "form không có ô `" + o + "`"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_a1_3_chuan_hoa_MOT_lan_o_may_chu_chu_khong_hai_lan():
    """Hai chỗ cùng chuẩn hóa một thứ thì sớm muộn hai chỗ khác nhau.

    Máy chủ đã viết hoa và bỏ ô trống trong `BankPatch`. Màn hình viết hoa lần nữa thì hôm nay
    giống nhau, và hỏng vào cái ngày một trong hai chỗ đổi — mà không ai nhớ còn chỗ kia.
    """
    ma = _mot_tk()
    r = client.patch(f"/api/v1/bank-accounts/{ma}", headers=login("ketoan"),
                     json={"match_prefixes": ["  ", "tpb1", ""], "match_keywords": []})
    assert r.status_code == 200, r.text[:300]
    doc = next(x for x in client.get("/api/v1/bank-accounts", headers=login("ketoan")).json()["rows"]
               if x["code"] == ma)
    assert doc["match_prefixes"] == ["TPB1"], (
        "máy chủ phải bỏ ô trống và viết hoa, nhận " + repr(doc["match_prefixes"]))

    s = _man()
    i = s.find("const tach = ")
    j = s.find("\n\n", i) if i > 0 else -1
    than_tach = s[i:j] if j > i > 0 else ""
    assert than_tach, "không thấy hàm tách chuỗi của màn hình"
    assert "toUpperCase" not in than_tach, (
        "màn hình viết hoa lần thứ hai — việc ấy máy chủ đã làm trong `BankPatch`")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_a1_4_KHONG_noi_quyen_va_KHONG_ghi_so_gi():
    """Hai điều, và cả hai là ranh giới của đợt này.

    (a) Đợt này không ký nới quyền: màn `/bank-accounts` đã khai sẵn nhóm `/api/v1/bank-accounts`,
        và màn hình không gọi ra ngoài nhóm ấy. Gọi ra ngoài là buộc phải thêm một dòng vào bảng
        quyền, và dòng ấy cộng phạm vi cho MỌI vai đang có màn này (bài học Đợt R5b-2).
    (b) Đợt này KHÔNG đổi một dòng sổ nào — nó chỉ khai cách nhận ra ngân hàng. Số dư `112` trước
        và sau phải y nguyên.
    """
    from app.services.access import MAN_HINH_API
    assert "/api/v1/bank-accounts" in MAN_HINH_API["/bank-accounts"], (
        "màn `/bank-accounts` không còn khai nhóm `/api/v1/bank-accounts` — DỪNG LẠI")

    s = _man()
    for p in re.findall(r'api[^(]*\(`([^`]+)`', s) + re.findall(r'api[^(]*\("([^"]+)"', s):
        assert p.startswith("/bank-accounts"), "màn hình gọi `" + p + "` ngoài nhóm đã khai"

    # Một vai ngoài Kế toán KHÔNG sửa được — «không nới quyền» phải đo được ở cửa, không chỉ
    # đúng trên giấy.
    ma = _mot_tk()
    r = client.patch(f"/api/v1/bank-accounts/{ma}", headers=login("kd.hoa"),
                     json={"sepay_account_number": "0000"})
    assert r.status_code == 403, (
        "một vai Kinh doanh phải nhận 403 ở cửa sửa tài khoản ngân hàng, nhận " + str(r.status_code))

    # Và đợt này không ghi sổ: số dư toàn cây `112` không đổi sau khi sửa ô nhận diện.
    from sqlalchemy import select, func
    from app.db.session import SessionLocal
    from app.models.accounting import JournalLine

    def _du():
        with SessionLocal() as db:
            return float(db.execute(
                select(func.coalesce(func.sum(JournalLine.debit), 0)
                       - func.coalesce(func.sum(JournalLine.credit), 0))
                .where(JournalLine.account_code.like("112%"))).scalar() or 0)

    truoc = _du()
    client.patch(f"/api/v1/bank-accounts/{ma}", headers=login("ketoan"),
                 json={"match_keywords": ["A1 KHONG GHI SO"]})
    assert abs(_du() - truoc) < 1, "sửa ô nhận diện mà số dư 112 đổi — đợt này không được ghi sổ"

    # Màn hình cũng không tự gọi cửa GHI SỔ ở bước nào của form sửa.
    i = s.find("const luuSua = ")
    j = s.find("\n\n", i) if i > 0 else -1
    than_luu = s[i:j] if j > i > 0 else ""
    assert than_luu, "không cắt được hàm lưu"
    assert "phan-loai" not in than_luu, "nút Lưu lại gọi cả cửa phân loại — hai việc khác nhau"
