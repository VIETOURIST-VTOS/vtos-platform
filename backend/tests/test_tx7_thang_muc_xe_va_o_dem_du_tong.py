# -*- coding: utf-8 -*-
"""TX-7 · Thang mức của xe, và ô đếm phải CỘNG ĐỦ TỔNG — Chủ tịch chốt 07/10/2026.

Vòng này sinh ra từ một mâu thuẫn ĐO ĐƯỢC trên hệ thật, không từ đọc mã:

    màn hình /doi-xe   16  xe trong danh mục
                        0  sẵn sàng
                        0  chưa đủ dữ liệu      ← mười một chiếc đáng nằm ở đây
                        5  đang bị chặn khai thác

    16 ≠ 0 + 0 + 5. Mười một chiếc biến mất khỏi mọi ô đếm.

HAI chỗ hỏng cộng lại mới ra con số ấy, và cả hai đều im lặng:

  1. THANG MỨC để REVIEW che UNKNOWN. Mười một chiếc vừa THIẾU dữ liệu đăng kiểm (UNKNOWN) vừa có
     giấy còn hạn mà chưa đối chiếu bản gốc (REVIEW). Thang cũ {BLOCK:4, APPROVAL:3, REVIEW:2,
     UNKNOWN:1, OK:0} cho REVIEW nặng hơn, nên mức tổng ra REVIEW.
  2. Ô ĐẾM chỉ in BA trong NĂM mức mà máy chủ trả về (OK, UNKNOWN, BLOCK). Nên chiếc xe ở mức REVIEW
     không nằm trong ô nào.

Dấu vết của nó nhìn thấy được ngay trên màn hình, nếu để ý: dòng xe in LÝ DO của UNKNOWN ("Chưa có
dữ liệu đăng kiểm của xe 50F-017.37" — `san_sang()` chỉ lấy lý do từ BLOCK và UNKNOWN) nhưng NHÃN
của REVIEW ("Cần xem lại"). Một chiếc xe mang lý do của mức này và nhãn của mức kia.

Và thang cũ trái đúng câu `services/fleet.py` tự viết ở đầu tệp: "UNKNOWN là mức dễ bị bỏ qua nhất
khi lập trình, và cũng là mức nguy hiểm nhất nếu bỏ".

Chủ tịch chốt: "KHÔNG BIẾT" nặng hơn "biết và cần xem lại" — cần xem lại thì đã có người nhìn và
biết nhìn cái gì; chưa đủ dữ liệu thì chưa ai biết mình đang thiếu gì.

BỘ HÀNG RÀO NÀY KHÔNG CHỈ CANH THANG MỨC. Thang mức là ca cụ thể; cái đáng canh là LUẬT: một ô đếm
phải cộng đủ tổng, và rổ đếm phải dựng TỪ thang mức chứ không gõ tay. Gõ tay là lần sau thêm mức thứ
sáu lại có người quên, và lại mười một chiếc xe lặng lẽ rơi ra ngoài.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DATABASE_URL"] = "sqlite:///./test_tx7.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
if os.path.exists("test_tx7.db"):
    os.remove("test_tx7.db")
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_KHO = os.path.dirname(GOC)

import pytest                                                          # noqa: E402
from fastapi.testclient import TestClient                              # noqa: E402
from app.main import app                                               # noqa: E402
from app.services import fleet as FL                                   # noqa: E402

client = TestClient(app)
TOK = {}


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


def _doc(*phan):
    goc = GOC_KHO if phan and phan[0] == "web" else GOC
    with open(os.path.join(goc, *phan), encoding="utf-8") as f:
        return f.read()


# ───────────────────── thang mức ─────────────────────
def test_chua_du_du_lieu_nang_hon_can_xem_lai_va_can_duyet():
    """Chủ tịch chốt 07/10/2026: "chưa đủ dữ liệu" nặng thứ hai, ngay sau "chặn"."""
    assert FL.NANG[FL.UNKNOWN] > FL.NANG[FL.REVIEW], (
        "Thang mức để 'cần xem lại' nặng hơn 'chưa đủ dữ liệu'. Hệ quả đã xảy ra thật: một chiếc xe "
        "vừa thiếu dữ liệu đăng kiểm vừa chưa đối chiếu bản gốc thì xếp vào 'cần xem lại', rồi biến "
        "mất khỏi ô đếm — 16 xe = 0 + 0 + 5 trên hệ thật ngày 07/10/2026.")
    assert FL.NANG[FL.UNKNOWN] > FL.NANG[FL.APPROVAL], (
        "'Chưa đủ dữ liệu' phải nặng hơn 'cần duyệt ngoại lệ': cần duyệt là đã biết mình xin duyệt "
        "cái gì; chưa đủ dữ liệu là chưa ai biết mình đang thiếu gì.")


def test_chan_van_o_tren_cung_va_khong_duoc_doi():
    """BLOCK là mức DUY NHẤT chặn lệnh điều xe. Đổi nó là đổi luật cho xe ra đường."""
    assert FL.NANG[FL.BLOCK] == max(FL.NANG.values()), (
        "BLOCK phải nặng nhất. Đây là mức duy nhất api/v1/hr.py dùng để chặn lệnh điều xe; hạ nó "
        "xuống là cho một chiếc xe không đủ điều kiện ra đường.")
    assert FL.NANG[FL.OK] == min(FL.NANG.values()), "OK phải nhẹ nhất – 'đạt' không che được gì."
    assert len(set(FL.NANG.values())) == len(FL.NANG), (
        "Hai mức không được cùng độ nặng: `max()` chọn cái nào là tuỳ thứ tự từ điển, tức là tuỳ may.")

def test_moi_muc_deu_co_ten_de_in_ra():
    """Mỗi mức phải có tên tiếng Việt, không thì màn hình in ra mã máy."""
    for k in FL.NANG:
        assert k in FL.MUC_TEN and FL.MUC_TEN[k].strip(), (
            f"Mức '{k}' không có tên trong MUC_TEN. Màn hình lấy tên từ đây (danh-muc.muc_kiem_tra); "
            "thiếu tên thì người dùng đọc được chữ 'APPROVAL_REQUIRED' trên bảng.")


# ───────────────────── luật: ô đếm phải cộng đủ tổng ─────────────────────
def test_o_dem_tong_quan_in_du_nam_muc():
    """Ô đếm của /tong-quan phải in đủ năm mức, và tự khai phần lệch."""
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert '"theo_muc_day_du"' in nguon, (
        "/tong-quan phải trả về đủ năm mức. Bản cũ chỉ trả ba (OK, UNKNOWN, BLOCK) trong khi "
        "san_sang() xếp theo năm, nên xe ở mức REVIEW hay APPROVAL không nằm trong ô nào.")
    assert '"thieu_trong_o_dem"' in nguon, (
        "Phải TỰ KHAI số xe không nằm trong ô đếm nào. Một ô đếm cộng không đủ tổng là một ô đếm nói "
        "sai, và nó nói sai êm ái: không báo lỗi, không hiện màu, chỉ thiếu.")
    for khoa in ('"can_xem_lai"', '"can_duyet_ngoai_le"'):
        assert khoa in nguon, f"Thiếu ô đếm {khoa} – đúng hai mức đã làm 11 chiếc xe biến mất."


def test_ro_dem_dung_tu_thang_muc_khong_go_tay():
    """Rổ đếm phải dựng TỪ `FL.NANG`, không gõ lại danh sách mức.

    Đây là luật, không phải ca cụ thể: gõ tay thì lần sau thêm mức thứ sáu lại có người quên, và lại
    một nắm xe lặng lẽ rơi ra ngoài. Cửa bảo dưỡng đã mắc đúng lỗi ấy — gõ bốn mức, thiếu APPROVAL."""
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert "{k: 0 for k in FL.NANG}" in nguon, (
        "Rổ đếm của cửa bảo dưỡng phải dựng từ FL.NANG. Bản cũ gõ tay bốn mức và thiếu "
        "APPROVAL_REQUIRED, nên một chiếc xe ở mức ấy không được cộng vào đâu.")
    assert "{k: muc.get(k, 0) for k in FL.NANG}" in nguon, (
        "Bảng năm mức của /tong-quan cũng phải dựng từ FL.NANG, cùng một lý do.")


def test_man_hinh_in_du_va_noi_ra_khi_lech():
    nguon = _doc("web", "app", "doi-xe", "page.tsx")
    assert "tq.can_xem_lai" in nguon and "tq.can_duyet_ngoai_le" in nguon, (
        "Dãy ô đếm trên /doi-xe phải in cả hai mức ấy. Máy chủ trả về mà màn hình không in thì người "
        "đọc vẫn thấy 16 = 0 + 0 + 5.")
    assert "tq.thieu_trong_o_dem" in nguon, (
        "Màn hình phải NÓI RA khi năm mức cộng không đủ tổng, đừng để người đọc tự trừ.")


def test_man_hinh_lenh_dieu_xe_khong_go_lai_thang_muc():
    """Một xe BỊ CHẶN không được hiện là 'cần xem lại' — nhẹ hơn sự thật, đúng chỗ không được nhẹ."""
    # Tách màn 17/10/2026: bảng phương án đề xuất nay ở trang con /lenh-dieu-xe/lap-lenh.
    nguon = _doc("web", "app", "lenh-dieu-xe", "lap-lenh", "page.tsx")
    assert "dm?.muc_kiem_tra?.[p.muc_kiem_tra]" in nguon, (
        "Màn hình lệnh điều xe phải lấy tên mức từ danh mục máy chủ. Bản cũ gõ ba nhánh và dồn mọi "
        "mức khác OK/UNKNOWN vào 'Cần xem lại', nên một xe BỊ CHẶN cũng hiện là cần xem lại.")
    assert '=== "BLOCK" ? "red"' in nguon, (
        "Xe bị chặn phải hiện màu đỏ, không phải màu vàng như mọi cảnh báo khác.")


# ───────────────────── chạy thật: tổng phải khớp ─────────────────────
def test_chay_that_nam_muc_cong_du_tong_so_xe():
    """Phép thử chạy trên máy chủ thật: gọi /tong-quan và cộng lại.

    Đây là phép thử duy nhất trong tệp này bắt được chỗ hỏng gốc mà không cần biết nó hỏng ở đâu —
    nó chỉ hỏi một câu: các ô đếm có cộng đủ số xe không."""
    r = client.get("/api/v1/fleet/tong-quan", headers=login("cntt"))
    assert r.status_code == 200, r.text
    d = r.json()
    tong_cac_muc = sum(x["so_xe"] for x in d["theo_muc_day_du"])
    assert tong_cac_muc == d["tong_so_xe"], (
        f"Năm mức cộng lại {tong_cac_muc} nhưng tổng số xe là {d['tong_so_xe']}. "
        "Có mức bị bỏ khỏi ô đếm – đúng chỗ hỏng ngày 07/10/2026.")
    assert d["thieu_trong_o_dem"] == 0, (
        f"Máy chủ tự khai còn {d['thieu_trong_o_dem']} xe không nằm trong ô đếm nào.")
    assert {x["muc"] for x in d["theo_muc_day_du"]} == set(FL.NANG), (
        "Bảng năm mức phải phủ đúng các mức trong thang, không thừa không thiếu.")
