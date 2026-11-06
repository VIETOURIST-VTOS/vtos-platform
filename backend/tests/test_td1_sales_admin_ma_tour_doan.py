# -*- coding: utf-8 -*-
"""Đợt TD-1 06/11/2026 — SALES ADMIN MỞ TOUR ĐOÀN, VÀ ĐẶT LẠI MÃ Ở CỔNG CHUYỂN.

Chủ tịch chốt 06/11/2026: «mã tour lẻ do Điều hành nhập lúc mở tour lẻ, mã tour đoàn do Sales
Admin nhập lúc mở tour đoàn», và «cả hai đều mở được».

HAI VIỆC, VÀ CHÚNG KHÁC NHAU:

  1. Sales Admin MỞ được tour đoàn. Đo ra thì đây KHÔNG phải nới bảng quyền: `MAN_HINH["/tours"]`
     đã có `SALES_ADMIN` và `MAN_HINH_API["/tours"]` đã có `/api/v1/tours`. Thứ chặn họ là một
     dòng luật nghiệp vụ gõ cứng trong `tours.create`, kèm câu «Chủ tịch quyết 24/9/2026». Nên
     đây là SỬA MỘT QUYẾT ĐỊNH CŨ, không phải ký nới quyền — và đợt này KHÔNG đụng `access.py`.

  2. Sales Admin ĐẶT LẠI MÃ ở cổng chuyển. Cho họ mở thì họ gõ mã lúc mở; nhưng nếu Kinh doanh
     Đoàn mở trước thì người gõ mã vẫn là Kinh doanh — nên cần chỗ đặt lại.

CHỖ NẶNG NHẤT, VÀ LUẬT 3 ĐO CHÍNH NÓ: mã tour được CHÉP THÀNH CHUỖI vào `project_code` của từng
dòng sổ lúc ghi, không phải một mối nối sống. Đổi mã sau khi sổ đã ghi thì những dòng cũ ở lại
với mã cũ — bảng đối chiếu lãi lỗ xếp chúng vào rổ «chỉ có trong sổ» còn chuyến rơi vào rổ «chỉ
có bảng tính», tức sổ của một chuyến bị cắt đôi, và không ai thấy cho tới lúc đối chiếu. Nên cửa
TỪ CHỐI khi đã có dòng sổ. Chủ tịch chốt: chặn cứng, KHÔNG sửa `project_code` của sổ đã ghi.
"""
import os
import re
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_td1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_td1.db"):
    os.remove("test_td1.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "tours", "[id]", "page.tsx")


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


def _vai(ten):
    """Một tài khoản đang sống mang vai ấy. Không gõ cứng tên đăng nhập — bộ dữ liệu thử đổi thì
    một tên gõ cứng thành bom hẹn giờ (bài học `ma_bk` của `test_accounting`).

    KHÔNG CÓ THÌ DỰNG, KHÔNG BỎ QUA — và đây là chỗ bản đầu của đợt này sai, đo được:

        ---------- test_td1_sales_admin_ma_tour_doan.py ----------
        ssss      [100%]      4 skipped

    Bản đầu `pytest.skip` khi bộ dữ liệu không có vai ấy. Mà `services/seed.py::USERS` gieo 14
    tài khoản mẫu và KHÔNG có tài khoản `sales_admin` nào — nên cả bốn luật của đợt rụng ngay
    dòng đầu, hàng rào in xanh, và cái xanh ấy không đo một dòng mã nào của đợt. Một luật không
    bao giờ chạy thì không phải luật (bài học Đợt TKC-1, cùng ngày). Nên: dựng tài khoản.
    """
    for x in client.get("/api/v1/users", headers=login("chutich")).json():
        if x.get("role") == ten:
            return x["username"]
    return _dung_tai_khoan(ten)


def _dung_tai_khoan(ten):
    """Dựng một tài khoản mang vai `ten` với mật khẩu mẫu, để `login()` dùng được ngay.

    Ghi thẳng vào CSDL thử chứ không qua cửa `/api/v1/accounts`: cửa ấy đặt mật khẩu tạm = mã
    nhân viên và bật `must_change_password`, tức dựng cảnh xong còn phải đi qua màn đổi mật khẩu
    — một đoạn đường không liên quan gì tới thứ đợt này đo.
    """
    from sqlalchemy import select as _sel
    from app.db.session import SessionLocal
    from app.models.core import User as _U
    from app.core.security import hash_password
    un = f"td1.{ten}"
    with SessionLocal() as db:
        if db.execute(_sel(_U).where(_U.username == un)).scalars().first() is None:
            db.add(_U(username=un, full_name=f"TD-1 dựng cảnh ({ten})", role=ten,
                      department="Kinh doanh Đoàn", active=True,
                      password_hash=hash_password("Vtos@Demo#2026")))
            db.commit()
    return un


def _id_cua(un):
    """Số hiệu của một tài khoản. `TourCreate.operator_id` là ô BẮT BUỘC — mở tour là giao luôn
    cho một người Điều hành, kể cả khi người mở là Kinh doanh hay Sales Admin."""
    for x in client.get("/api/v1/users", headers=login("chutich")).json():
        if x["username"] == un:
            return x["id"]
    raise AssertionError(f"không tìm thấy tài khoản {un} để lấy số hiệu")


def _du_lieu_tour(ma, doan=True):
    """LOẠI CHUYẾN PHẢI LÀ TÊN THẬT. `services/segments.py` chỉ nhận `doan_noi_dia` /
    `doan_nuoc_ngoai` là đoàn và `le_noi_dia` / `le_nuoc_ngoai` là lẻ. Bản đầu của đợt này gõ
    `"doan"`, và một chuỗi không có trong hai bộ ấy thì `mang_of` xếp chuyến vào mảng LẺ — luật 1
    sẽ đo một tour lẻ rồi tưởng mình đang đo tour đoàn.
    """
    d = date.today() + timedelta(days=30)
    return {"code": ma, "name": "TD-1 dựng cảnh",
            "tour_type": "doan_noi_dia" if doan else "le_noi_dia",
            "operator_id": _id_cua(_vai("nv_dh")),
            "start_date": str(d), "end_date": str(d + timedelta(days=2)),
            "price_per_pax": 5000000, "fixed_cost": 1000000,
            "var_cost_per_pax": 3000000, "planned_pax": 20}


def _tao(vai, ma, doan=True):
    return client.post("/api/v1/tours", json=_du_lieu_tour(ma, doan), headers=login(_vai(vai)))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_td1_1_sales_admin_mo_duoc_tour_DOAN_nhung_khong_mo_duoc_tour_LE():
    """Hai chiều, và cần cả hai.

    Chiều xuôi: Sales Admin mở được tour đoàn — việc Chủ tịch vừa chốt.
    Chiều ngược: tour LẺ vẫn chỉ Điều hành. Một bản chỉ làm chiều xuôi có thể mở toang cả hai
    loại mà vẫn xanh, và lúc ấy «Tour lẻ: chỉ Phòng Điều hành» (ĐH Điều 2) mất mà không ai thấy.
    """
    r = _tao("sales_admin", "TD1DOAN010101")
    assert r.status_code in (200, 201), (
        "Sales Admin phải mở được tour ĐOÀN (Chủ tịch chốt 06/11/2026), nhận "
        + str(r.status_code) + ": " + r.text[:300])
    t = r.json()
    assert t["status"] == "nhap_kd", (
        "Tour do Sales Admin mở phải đứng ở `nhap_kd` y như khi Kinh doanh Đoàn mở — rồi chính "
        "họ bấm «Chuyển Điều hành». Nhận: " + repr(t["status"]))

    r2 = _tao("sales_admin", "TD1LE010101", doan=False)
    assert r2.status_code == 403, (
        "Tour LẺ vẫn chỉ Phòng Điều hành tạo (ĐH Điều 2) — Sales Admin phải nhận 403, nhận "
        + str(r2.status_code))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_td1_2_doi_ma_duoc_khi_so_CHUA_dung_ma_va_cong_trinh_di_theo():
    """Đổi mã xong thì BẢN GHI CÔNG TRÌNH phải mang mã mới.

    Mã công trình = mã tour (`misa.ensure_project_for_tour`). Bỏ quên nó thì danh mục công trình
    giữ mã cũ, và sổ chi tiết theo công trình tìm không ra chuyến này.
    """
    t = _tao("sales_admin", "TD1CU020202").json()
    r = client.post(f"/api/v1/tours/{t['id']}/doi-ma", json={"ma": "TD1MOI020202"},
                    headers=login(_vai("sales_admin")))
    assert r.status_code == 200, r.text[:300]
    sau = client.get(f"/api/v1/tours/{t['id']}", headers=login("chutich")).json()
    assert sau["code"] == "TD1MOI020202", "mã tour chưa đổi: " + repr(sau["code"])

    # `q=TD1`: cửa `/api/v1/projects` cắt ở `limit=50` và xếp theo mã, nên không lọc thì công
    # trình của đợt này có thể nằm ngoài trang đầu và luật đỏ vì một lý do không phải lỗi.
    cts = client.get("/api/v1/projects", headers=login("ketoan"), params={"q": "TD1"}).json()
    ma_ct = {c.get("code") for c in (cts if isinstance(cts, list) else cts.get("rows", []))}
    assert "TD1MOI020202" in ma_ct, (
        "Công trình chưa mang mã mới. Mã công trình = mã tour; bỏ quên nó thì sổ chi tiết theo "
        "công trình tìm không ra chuyến này.")
    assert "TD1CU020202" not in ma_ct, "còn sót công trình mang mã cũ: TD1CU020202"

    # Mã trùng tour khác thì từ chối — cột `code` là UNIQUE, để lọt là lỗi 500 cho người dùng.
    t2 = _tao("sales_admin", "TD1KHAC020202").json()
    r2 = client.post(f"/api/v1/tours/{t2['id']}/doi-ma", json={"ma": "TD1MOI020202"},
                     headers=login(_vai("sales_admin")))
    assert r2.status_code in (400, 409, 422), "mã trùng mà vẫn cho đổi: " + str(r2.status_code)


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_td1_3_SO_DA_DUNG_MA_thi_TU_CHOI_va_so_khong_doi_mot_dong_nao():
    """Chỗ nặng nhất của đợt. Chủ tịch chốt: chặn cứng, không sửa sổ đã ghi.

    Dựng cảnh thật: mở tour, ghi một bút toán mang `project_code` = mã tour, rồi đòi cửa từ chối
    — VÀ đòi sổ không đổi một dòng nào sau cú từ chối ấy.
    """
    t = _tao("sales_admin", "TD1SO030303").json()
    bt = client.post("/api/v1/journal", json={
        "entry_date": str(date.today()),
        "description": "TD-1 dựng cảnh — dòng sổ mang mã công trình",
        "lines": [{"account": "642", "debit": 1000000, "project_code": "TD1SO030303"},
                  {"account": "331", "credit": 1000000, "partner_code": "NCC-TD1",
                   "project_code": "TD1SO030303"}],
        "post": True}, headers=login("ketoan"))
    # KHÔNG `skip` Ở ĐÂY. Dựng cảnh hỏng thì luật này im lặng biến mất, mà nó là luật nặng nhất
    # của đợt. Hỏng thì phải ĐỎ và nói ra máy chủ trả gì.
    assert bt.status_code in (200, 201), (
        "không ghi được bút toán dựng cảnh (" + str(bt.status_code) + "): " + bt.text[:300])

    def _dem():
        r = client.get("/api/v1/books/cong-trinh", headers=login("ketoan"),
                       params={"project_code": "TD1SO030303",
                               "since": str(date.today().replace(day=1)), "upto": str(date.today())})
        return len(r.json().get("rows", [])) if r.status_code == 200 else -1

    truoc = _dem()
    assert truoc > 0, "cảnh chưa dựng được: sổ không có dòng nào mang mã TD1SO030303"

    r = client.post(f"/api/v1/tours/{t['id']}/doi-ma", json={"ma": "TD1DOI030303"},
                    headers=login(_vai("sales_admin")))
    assert r.status_code in (400, 409, 422), (
        "Sổ đã có dòng mang mã này mà cửa VẪN cho đổi (nhận " + str(r.status_code) + "). "
        "Đổi mã lúc này là cắt đôi sổ của chuyến: dòng cũ ở lại mã cũ, chuyến mang mã mới.")
    assert "TD1SO030303" in r.text, "câu từ chối phải nói rõ mã nào đang bị sổ dùng"

    sau = client.get(f"/api/v1/tours/{t['id']}", headers=login("chutich")).json()
    assert sau["code"] == "TD1SO030303", "cửa từ chối mà mã tour vẫn đổi"
    assert _dem() == truoc, "cửa từ chối mà sổ vẫn đổi — không được đụng một dòng nào"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_td1_4_chi_SALE_ADMIN_dat_lai_ma_va_chi_o_buoc_Kinh_doanh_soan():
    """Mở cho Kinh doanh Đoàn thì mã lại do người mở đặt, và cả đợt này mất nghĩa.

    Và chỉ ở bước `nhap_kd`: qua bước sau thì mã đã đi vào hồ sơ của Điều hành và của sổ.
    """
    t = _tao("sales_admin", "TD1VAI040404").json()
    kd = _vai("nv_kd")
    r = client.post(f"/api/v1/tours/{t['id']}/doi-ma", json={"ma": "TD1KD040404"},
                    headers=login(kd))
    assert r.status_code == 403, (
        "Kinh doanh Đoàn phải nhận 403 khi đặt lại mã, nhận " + str(r.status_code))

    # Qua bước sau thì khoá. Chuyển sang Điều hành rồi đòi đổi mã.
    ch = client.post(f"/api/v1/tours/{t['id']}/chuyen-dieu-hanh", json={"note": "TD-1 dựng cảnh"},
                     headers=login(_vai("sales_admin")))
    if ch.status_code == 200:
        r2 = client.post(f"/api/v1/tours/{t['id']}/doi-ma", json={"ma": "TD1SAU040404"},
                         headers=login(_vai("sales_admin")))
        assert r2.status_code in (400, 409, 422), (
            "Qua bước Kinh doanh soạn rồi mà vẫn đổi được mã: " + str(r2.status_code))

    # Màn hình: ô đặt lại mã phải nằm TRONG khối chỉ hiện ở `nhap_kd`, không rải ra ngoài.
    assert os.path.exists(MAN), "khong thay web/app/tours/[id]/page.tsx"
    s = open(MAN, encoding="utf-8").read()
    assert s.count("doi-ma") >= 1, "màn hình chưa gọi cửa `doi-ma` — cửa có mà không ai bấm được"
    i = s.find('t.status === "nhap_kd"')
    j = s.find('t.status === "nhap"', i + 1)
    assert i > 0 and j > i, "không cắt được khối `nhap_kd` trên màn hình"
    # TRONG khối thì tìm `onClick={doiMa}`, KHÔNG tìm chuỗi `doi-ma`: chuỗi ấy nằm ở thân hàm
    # `doiMa` phía trên (dòng gọi `api("/tours/.../doi-ma")`), ngoài mọi khối trạng thái. Tìm nó
    # ở đây là tìm một thứ không bao giờ có trong khối — phép đo nhắm sai chỗ, y như cái moc
    # `"doi-ma"` đã làm bước vá màn hình bị bỏ qua lặng lẽ lúc chạy thử.
    assert "onClick={doiMa}" in s[i:j], (
        "Ô đặt lại mã nằm NGOÀI khối `nhap_kd` — nó sẽ hiện cả ở bước mà máy chủ đã khoá, và "
        "người dùng bấm vào một nút chỉ để nhận lỗi.")
