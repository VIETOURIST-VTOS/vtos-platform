# -*- coding: utf-8 -*-
"""Đợt TKC-1 06/11/2026 — CỬA ĐỌC «BÚT TOÁN GHI VÀO TÀI KHOẢN CHA», NỚI RA MỌI TÀI KHOẢN CHA.

HAI CHUYỆN, VÀ CHÚNG KHÁC NHAU:

  - Cửa `/api/v1/accounting/tien-ghi-cap-cha` đã có trên main từ Đợt R4c-3, nhưng nó soi ĐÚNG BA
    tài khoản tiền `111/112/113`. Câu Kế toán trưởng phải trả lời là «có chặn ghi vào tài khoản
    cha hay không», và câu ấy nói về MỌI tài khoản cha — danh mục có 38 cái. Một con số hẹp hơn
    câu hỏi thì dễ bị đọc như thể nó là câu trả lời đầy đủ.

  - Và cho tới hôm nay KHÔNG màn hình nào gọi cửa ấy. Theo ranh giới công việc 09/9/2026, một con
    số không có chỗ để đọc là việc CÒN THIẾU, không phải việc đã xong.

ĐỢT NÀY KHÔNG SỬA MỘT BÚT TOÁN NÀO. Chủ tịch chốt 02/11/2026: sổ đã ghi là sổ đã ghi. Cửa chỉ
đọc, thẻ chỉ đọc, và luật 3 đo chính điều ấy chứ không chỉ hứa.

ĐO BẰNG CỬA THẬT, KHÔNG ĐỌC MÃ NGUỒN. Một luật đọc mã nguồn chỉ chứng minh được rằng chữ ấy có
trong tệp, không chứng minh được cửa trả về gì. Bốn luật dưới đây gọi cửa qua `TestClient`.
"""
import os
import re
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_tkc1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_tkc1.db"):
    os.remove("test_tkc1.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "ket-so", "page.tsx")
CUA = "/api/v1/accounting/tien-ghi-cap-cha"


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
    r = client.get(CUA, params=q, headers=login("ketoan"))
    assert r.status_code == 200, f"{CUA} trả {r.status_code}: {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="module", autouse=True)
def _dung_canh(_startup):
    """TỰ DỰNG CẢNH, không chờ bộ dữ liệu thử tình cờ có sẵn.

    Vòng bấm đầu 06/11/2026: luật 2 BỊ BỎ QUA vì bộ dữ liệu thử không có bút toán nào vào tài
    khoản cha. Một luật không bao giờ chạy thì không phải luật — nó chỉ làm hàng rào trông dài
    hơn sự thật. Nên luật tự ghi lấy hai bút toán vào `111` (tài khoản CHA, có con 1111/1112),
    rồi mới đo.

    Hai chứ không một: luật 2 cắt bảng ở `gioi_han=1` rồi đòi bảng gộp vẫn đếm đủ — có một dòng
    thì cắt hay không cắt cũng như nhau, và phép đo ấy sẽ xanh mà chẳng chứng minh được gì.
    """
    for i, tien in enumerate((500000, 700000), 1):
        r = client.post("/api/v1/journal", json={
            "entry_date": str(date.today()),
            "description": f"TKC-1 dựng cảnh {i} — ghi thẳng vào tài khoản cha 111",
            "lines": [{"account": "642", "debit": tien}, {"account": "111", "credit": tien}],
            "post": True,
        }, headers=login("ketoan"))
        # 201 chứ không phải 200 — đo được ở vòng bấm 06/11/2026, và đó là lỗi của phép kiểm chứ
        # không phải của cửa: bút toán ĐÃ ghi (`status: da_ghi_so`), chỉ con số em đoán là sai.
        assert r.status_code in (200, 201), (
            "không dựng được cảnh (ghi bút toán vào tài khoản cha 111): "
            f"{r.status_code} {r.text[:300]}")
        assert r.json()["entry"]["status"] == "da_ghi_so", (
            "bút toán dựng cảnh còn ở trạng thái nháp — cửa chỉ đếm dòng ĐÃ ghi sổ, nên cảnh "
            "chưa dựng xong: " + r.text[:200])
    yield


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tkc1_1_cua_soi_MOI_tai_khoan_cha_chu_khong_chi_ba_tai_khoan_tien():
    """Danh sách tài khoản cha của cửa phải KHỚP bảng quan hệ cha–con của chính danh mục.

    Không so với một con số gõ tay (hôm nay 38, mai Kế toán thêm một tiểu khoản là 39) — so với
    CHÍNH danh mục, nên luật này đúng cả khi danh mục đổi.
    """
    d = _doc()
    tk = client.get("/api/v1/accounts", headers=login("ketoan")).json()
    cha_that = sorted({a["parent"] for a in tk if a.get("parent")} & {a["code"] for a in tk})
    assert d["tai_khoan_cap_cha"] == cha_that, (
        "Cửa nói có " + str(len(d["tai_khoan_cap_cha"])) + " tài khoản cha, danh mục nói "
        + str(len(cha_that)) + ".\n  cửa thiếu: "
        + repr(sorted(set(cha_that) - set(d["tai_khoan_cap_cha"])))
        + "\n  cửa thừa: " + repr(sorted(set(d["tai_khoan_cap_cha"]) - set(cha_that))))
    assert d["so_tai_khoan_cha"] == len(cha_that)
    # Chỗ này là CHÍNH việc của đợt: bản cũ soi đúng ba tài khoản tiền.
    assert len(cha_that) > 3, "danh mục thử chỉ có <= 3 tài khoản cha — không đo được việc nới"
    assert set(d["tai_khoan_cap_cha"]) - {"111", "112", "113"}, (
        "Cửa vẫn chỉ soi nhóm tiền 111/112/113 — đợt này nới ra mọi tài khoản cha mà chưa nới.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tkc1_2_bang_gop_dem_tren_TOAN_BO_chu_khong_phai_tren_phan_da_cat():
    """Bảng «từng chứng từ» bị cắt ở `gioi_han`; bảng «theo tài khoản» thì KHÔNG được cắt.

    Vì sao phải đo: ai cộng nhẩm trên bảng đã cắt sẽ cộng một phần rồi tưởng là toàn bộ. Nếu hai
    bảng cùng bị cắt thì cái sai ấy không có chỗ nào tự lộ ra.
    """
    het = _doc()
    # KHÔNG bỏ qua khi rỗng. Cảnh đã được dựng ở `_dung_canh`, nên rỗng ở đây nghĩa là cửa không
    # nhìn thấy bút toán vừa ghi vào `111` — đó là một cái đỏ thật, không phải lý do để im.
    assert het["so_dong"] >= 2, (
        "Vừa ghi hai bút toán vào tài khoản cha `111` mà cửa chỉ thấy "
        + str(het["so_dong"]) + " dòng.")
    # Cắt thật chặt để bảng chứng từ chắc chắn bị cắt, rồi đòi bảng gộp vẫn đếm đủ.
    hep = _doc(gioi_han=1)
    assert len(hep["dong"]) <= 1
    assert hep["so_dong"] == het["so_dong"], "`so_dong` đổi theo `gioi_han` — nó phải là TỔNG"
    assert hep["cat_bot"] is (het["so_dong"] > 1)
    assert hep["so_tien"] == het["so_tien"], "`so_tien` đổi theo `gioi_han` — nó phải là TỔNG"
    tong_gop = sum(g["so_dong"] for g in hep["theo_tai_khoan"])
    assert tong_gop == het["so_dong"], (
        "Bảng «theo tài khoản» cộng lại được " + str(tong_gop) + " dòng, trong khi tổng là "
        + str(het["so_dong"]) + " — bảng gộp đang bị cắt theo `gioi_han`, và đó đúng là cái bẫy "
        "mà hai bảng sinh ra để tránh.")
    assert hep["theo_tai_khoan"] == het["theo_tai_khoan"], "bảng gộp đổi theo `gioi_han`"
    for g in het["theo_tai_khoan"]:
        assert g["tai_khoan"] in het["tai_khoan_cap_cha"]
        assert g["so_con"] >= 1, g["tai_khoan"] + ": là tài khoản cha mà đếm được 0 con"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tkc1_3_CHI_DOC_khong_mot_duong_nao_doi_so():
    """Chủ tịch chốt 02/11/2026 để nguyên bút toán cũ. Luật này đo, không hứa.

    Hai vế: (a) chính cửa ấy không nhận POST/PUT/PATCH/DELETE; (b) gọi cửa hai lần thì sổ không
    đổi một dòng nào — một cửa «chỉ đọc» mà lại ghi gì đó là thứ không ai đi tìm.
    """
    truoc = _doc()
    for cach in ("post", "put", "patch", "delete"):
        r = getattr(client, cach)(CUA, headers=login("ketoan"))
        assert r.status_code in (404, 405), (
            cach.upper() + " " + CUA + " trả " + str(r.status_code) +
            " — cửa này phải CHỈ ĐỌC, không nhận đường ghi nào.")
    sau = _doc()
    assert sau["so_dong"] == truoc["so_dong"] and sau["so_tien"] == truoc["so_tien"], (
        "Đọc cửa hai lần mà số đổi — nghĩa là nó không chỉ đọc.")
    # Và thẻ trên màn hình cũng không được mang một nút ghi nào.
    assert os.path.exists(MAN), "khong thay web/app/ket-so/page.tsx"
    s = open(MAN, encoding="utf-8").read()
    i = s.find("function TienCapCha()")
    assert i > 0, "chưa có thẻ `TienCapCha` trên màn Kết sổ — cửa vẫn không ai gọi"
    j = s.find("\nfunction ", i + 1)
    than = s[i:j if j > 0 else len(s)]
    xau = [m for m in re.findall(r'method:\s*"([A-Z]+)"', than) if m != "GET"]
    assert not xau, "thẻ `TienCapCha` có đường ghi " + repr(xau) + " — nó phải CHỈ ĐỌC."


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_tkc1_4_co_is_detail_lech_thi_NOI_RA_chu_khong_lang_le_chon_mot_ben():
    """Cửa đọc bảng quan hệ cha–con, KHÔNG đọc cờ `is_detail`. Hai bên lệch thì phải nói ra.

    Vì sao: cờ `is_detail` chỉ được đặt trên đường nạp danh mục MISA, nên một tài khoản thêm bằng
    đường khác vẫn mang `is_detail=True` dù nó đã có con. Ai sau này viết phép CHẶN dựa vào cờ ấy
    sẽ chặn sai chỗ — nên chỗ lệch phải hiện ra bây giờ, lúc còn rẻ, chứ không phải lúc đã chặn.
    """
    d = _doc()
    assert "co_is_detail_lech" in d, (
        "Cửa không trả ô `co_is_detail_lech`. Thiếu ô ấy thì chỗ lệch giữa cờ và bảng quan hệ "
        "không có đường nào lộ ra, và một thứ không lộ ra thì không ai dọn.")
    assert isinstance(d["co_is_detail_lech"], list)
    # Mọi mã trong đó phải là mã có thật — một danh sách cảnh báo chứa mã bịa thì tệ hơn là không có.
    ma = {a["code"] for a in client.get("/api/v1/accounts", headers=login("ketoan")).json()}
    la = [c for c in d["co_is_detail_lech"] if c not in ma]
    assert not la, "ô cảnh báo chứa mã không có trong danh mục: " + repr(la)
