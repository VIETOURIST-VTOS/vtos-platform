# -*- coding: utf-8 -*-
"""Đợt TKC-2 07/11/2026 — NHỊP 1: ĐƯỜNG GHI NÀO ĐANG GHI VÀO TÀI KHOẢN CHA.

Chủ tịch chốt 07/11/2026, ba nhịp: **ĐO trên dữ liệu thật → NẮN từng đường ghi → mới BẬT CHẶN**.
Đợt này là nhịp 1, và nó CHỈ ĐỌC, CHỈ ĐẾM — không chặn gì, không sửa một bút toán nào.

Vì sao phải có: đo ngày 07/11/2026 bằng một bộ đo gắn tạm vào `post_entry` rồi gỡ ra, trên dữ
liệu MẪU có 42 bút toán ghi vào 12 tài khoản cha — từ phát hành hóa đơn, lương, chi quỹ, quyết
toán tour, kết chuyển. Bật chặn cứng ngay là gãy các đường chạy hằng ngày. Nhưng đó là dữ liệu
mẫu; và thẻ của Đợt TKC-1 mới đếm TÀI KHOẢN, chưa nói ĐƯỜNG GHI nào tạo ra chúng — mà nhịp 2 là
sửa mã của từng đường ghi, nên danh sách ấy là thứ phải có trước.

BỐN LUẬT:
  1. Cửa trả `theo_duong_ghi` đủ mọi ô thẻ đọc, và gộp ĐÚNG theo cặp (nguồn, nghiệp vụ).
  2. Đếm TRÊN TOÀN BỘ, không cắt ở `gioi_han` — bảng cắt mà gọi là tổng là chỗ hỏng kinh điển.
  3. `ky_dau` / `ky_cuoi` đúng, vì `ky_cuoi` là cột để quyết nhịp 2.
  4. Đợt này KHÔNG chặn gì: cửa vẫn CHỈ ĐỌC, và ghi vào tài khoản cha vẫn qua được.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_tkc2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_tkc2.db"):
    os.remove("test_tkc2.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "ket-so", "page.tsx")

KY_CU, NGAY_CU = "2027-02", "2027-02-20"
KY_MOI, NGAY_MOI = "2027-05", "2027-05-20"


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
        _dung_canh()
        yield


def _ghi(mo_ta, ngay, lines):
    r = client.post("/api/v1/journal", json={"entry_date": ngay, "description": mo_ta,
                                             "lines": lines, "post": True}, headers=login("ketoan"))
    assert r.status_code in (200, 201), (
        "không dựng được cảnh (" + str(r.status_code) + "): " + r.text[:300])


def _dung_canh():
    """Ba bút toán ghi vào TÀI KHOẢN CHA, hai kỳ khác nhau, cùng một đường ghi.

    Cảnh phải làm ba điều lộ ra, và cả ba đều là điều luật tuyên bố:

      · GỘP theo cặp (nguồn, nghiệp vụ): ba bút toán cùng đường thì phải ra MỘT dòng, không ba.
      · ĐẾM ĐÚNG số dòng và số CHỨNG TỪ — hai con số khác nhau, và lẫn chúng là nói sai quy mô.
      · `ky_dau` / `ky_cuoi` trải hai kỳ, nên bản nào chỉ lấy một kỳ sẽ lộ ra.

    Ghi vào `133` — tài khoản CHA (có con `1331`). Dùng cửa nhập tay thật, không ghi thẳng CSDL:
    phải chứng minh cửa ấy VẪN NHẬN, vì luật 4 nói đợt này chưa chặn gì.
    """
    for mo_ta, ngay in ((("TKC-2 dựng cảnh — kỳ cũ A"), NGAY_CU),
                        (("TKC-2 dựng cảnh — kỳ cũ B"), NGAY_CU),
                        (("TKC-2 dựng cảnh — kỳ mới"), NGAY_MOI)):
        _ghi(mo_ta, ngay, [{"account": "133", "debit": 1_000_000},
                           {"account": "331", "credit": 1_000_000, "partner_code": "NCC-TKC2"}])


def _d(**params):
    r = client.get("/api/v1/accounting/tien-ghi-cap-cha", headers=login("ketoan"), params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _duong(d):
    """Dòng gộp của đường ghi mà cảnh vừa dựng."""
    ds = [g for g in d["theo_duong_ghi"]
          if g["nguon"] == "thu_cong" and g["nghiep_vu"] == "but_toan_tay"]
    assert len(ds) == 1, (
        "ba bút toán cùng một đường ghi phải gộp thành ĐÚNG MỘT dòng, nhận " + str(len(ds)))
    return ds[0]


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tkc2_1_cua_tra_theo_duong_ghi_va_gop_dung_theo_cap_nguon_nghiep_vu():
    """Tài khoản không cho biết phải sửa tệp nào; đường ghi thì cho.

    Nên bảng này gộp theo cặp (nguồn, nghiệp vụ) — gộp theo mỗi `nguon` là trộn những việc khác
    hẳn nhau (`luong` gồm cả lương HĐLĐ lẫn BHXH), và nhịp 2 sẽ không biết sửa chỗ nào.
    """
    d = _d(tu="2027-01-01", den="2027-12-31")
    assert "theo_duong_ghi" in d, "cửa chưa trả bảng gộp theo đường ghi"
    g = _duong(d)
    for o in ("nguon", "nghiep_vu", "ten_nghiep_vu", "so_dong", "so_chung_tu",
              "tai_khoan", "ky_dau", "ky_cuoi", "no", "co"):
        assert o in g, "thiếu ô `" + o + "` mà thẻ đọc"
    assert g["ten_nghiep_vu"], (
        "`ten_nghiep_vu` rỗng — thẻ sẽ in mã máy thay vì tên người đọc được")
    assert g["tai_khoan"] == ["133"], (
        "ô `tai_khoan` phải liệt kê tài khoản cha mà đường ghi này chạm, nhận " + repr(g["tai_khoan"]))
    # Số DÒNG và số CHỨNG TỪ là hai con số khác nhau — lẫn chúng là nói sai quy mô.
    assert g["so_dong"] == 3 and g["so_chung_tu"] == 3, (
        "cảnh dựng 3 chứng từ, mỗi chứng từ 1 dòng chạm tài khoản cha — nhận "
        + str(g["so_dong"]) + " dòng / " + str(g["so_chung_tu"]) + " chứng từ")
    assert g["no"] == 3_000_000, "tổng Nợ phải là 3.000.000, nhận " + str(g["no"])


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tkc2_2_dem_tren_TOAN_BO_khong_cat_o_gioi_han():
    """Bảng từng chứng từ bị cắt ở `gioi_han`; bảng gộp thì KHÔNG.

    Cộng nhẩm một bảng đã cắt rồi tưởng là toàn bộ chính là chỗ hỏng mà bảng gộp theo tài khoản
    của Đợt TKC-1 sinh ra để chặn — bảng mới này phải giữ đúng tính chất ấy.
    """
    d = _d(tu="2027-01-01", den="2027-12-31", gioi_han=1)
    assert len(d["dong"]) <= 1, "bảng từng chứng từ phải bị cắt theo `gioi_han`"
    assert d["cat_bot"] is True, "cửa không nói ra rằng bảng đã cắt bớt"
    g = _duong(d)
    assert g["so_dong"] == 3 and g["so_chung_tu"] == 3, (
        "bảng gộp bị cắt theo `gioi_han` — nó phải đếm trên TOÀN BỘ. Nhận "
        + str(g["so_dong"]) + " dòng")
    assert g["no"] == 3_000_000, "tổng tiền của bảng gộp cũng bị cắt"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tkc2_3_ky_dau_va_ky_cuoi_dung__cot_de_quyet_nhip_2():
    """`ky_cuoi` chia nhịp 2 thành hai loại việc khác hẳn nhau.

    Còn ghi gần đây → đường vẫn chạy, phải NẮN MÃ trước khi bật chặn.
    Kỳ cuối đã lâu → chỉ còn SỐ CŨ, là việc Kế toán trưởng quyết riêng, không sửa dòng mã nào.

    Sai cột này là chia nhầm việc, nên luật đo cả hai đầu chứ không chỉ một.
    """
    g = _duong(_d(tu="2027-01-01", den="2027-12-31"))
    assert g["ky_dau"] == KY_CU, "`ky_dau` phải là kỳ sớm nhất " + KY_CU + ", nhận " + repr(g["ky_dau"])
    assert g["ky_cuoi"] == KY_MOI, (
        "`ky_cuoi` phải là kỳ muộn nhất " + KY_MOI + ", nhận " + repr(g["ky_cuoi"]) +
        " — lấy nhầm kỳ đầu thì một đường đang chạy bị đọc thành đường đã ngừng")

    # Lọc khoảng ngày chỉ còn kỳ cũ thì cả hai mốc phải co lại theo.
    g2 = _duong(_d(tu="2027-01-01", den="2027-03-31"))
    assert g2["ky_dau"] == g2["ky_cuoi"] == KY_CU, (
        "lọc theo khoảng ngày mà hai mốc kỳ không co lại: " + repr((g2["ky_dau"], g2["ky_cuoi"])))
    assert g2["so_dong"] == 2, "lọc còn kỳ cũ thì phải còn 2 dòng, nhận " + str(g2["so_dong"])


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_tkc2_4_dot_nay_KHONG_chan_gi__cua_van_CHI_DOC():
    """Nhịp 1 là ĐO, không phải CHẶN. Hai chiều, và cần cả hai.

    Nếu đợt này lỡ chặn thì phát hành hóa đơn, lương, chi quỹ và kết chuyển gãy ngay — đó đúng là
    điều phép đo 07/11/2026 cảnh báo, và là lý do ba nhịp tồn tại.
    """
    # Chiều xuôi: ghi vào tài khoản CHA vẫn qua được cửa ghi sổ.
    _ghi("TKC-2 — ghi vào tài khoản cha SAU khi mở thẻ", NGAY_MOI,
         [{"account": "133", "debit": 500_000},
          {"account": "331", "credit": 500_000, "partner_code": "NCC-TKC2"}])

    # Chiều ngược: cửa đo không có đường GHI nào.
    import inspect
    from app.api.v1 import accounting as A
    than = inspect.getsource(A.tien_ghi_cap_cha)
    for cam in ("db.add(", "db.commit(", "db.delete(", "post_entry("):
        assert cam not in than, "cửa CHỈ ĐỌC mà có `" + cam + "`"

    # Và thẻ phải đọc đúng bảng mới — khai ở cửa mà màn hình không dùng thì cũng vô nghĩa.
    s = open(MAN, encoding="utf-8").read()
    i = s.find("Theo đường ghi")
    assert i > 0, "thẻ trên màn Kết sổ chưa có bảng «Theo đường ghi»"
    j = s.find("</table>", i)
    than_bang = s[i:j] if j > i else ""
    # ĐO NGUỒN DỮ LIỆU TRƯỚC, RỒI MỚI ĐO CÁC Ô. Bản đầu của luật này chỉ đo các ô `g.xxx`, và
    # đo ngược cho thấy nó KHÔNG CẮN: thay `d.theo_duong_ghi.map(...)` bằng `[].map(...)` thì
    # bảng rỗng hoàn toàn mà luật vẫn xanh — vì mọi chữ `g.xxx` còn nguyên trong thân `.map`.
    # Một luật đo cái vỏ chứ không đo cái chạy thì không phải luật.
    assert "d.theo_duong_ghi.map(" in than_bang, (
        "bảng không được dựng từ `d.theo_duong_ghi` — nó đang vẽ ra từ một nguồn khác, hoặc từ "
        "không gì cả")
    for o in ("g.nguon", "g.ten_nghiep_vu", "g.so_dong", "g.so_chung_tu", "g.tai_khoan",
              "g.ky_dau", "g.ky_cuoi"):
        assert o in than_bang, "bảng trên thẻ không đọc ô `" + o + "`"
    assert s.count("d.theo_duong_ghi?.length") == 1, "bảng được gọi nhiều hơn một lần"
    assert ".reduce(" not in than_bang, "thẻ tự cộng lại — số đã có sẵn từ máy chủ"
