# -*- coding: utf-8 -*-
"""CỬA TỶ GIÁ – nhân viên tự nhập tỷ giá từng ngày, kèm chứng từ.

Chủ tịch chốt 16/9/2026: *"tỷ giá để nhân viên tự nhập tại từng thời điểm; tạo form để nhân viên tự
nhập tay và tải tệp/ảnh."*

VÌ SAO CỬA NÀY PHẢI CÓ, ĐO CHỨ KHÔNG SUY

  Tệp quyết toán UK: HAI tỷ giá GBP trong CÙNG MỘT TỆP – 36.000 ở sheet chiết tính, 35.944 ở sheet
  quyết toán. Trên giá land 692,34 GBP × 43 khách, 56 đồng chênh ấy là 1.667.155 đ.

  21 tệp quyết toán visa T1–T6/2026: tỷ giá nằm rải trong ô đầu bảng (CAD 19.000, USD 25.500,
  AUD 18.500) và không tệp nào ghi tỷ giá ấy lấy từ đâu, ngày nào.

Tám điều, mỗi điều là một cách hỏng đã nghĩ ra trước:

  TG1  tra cứu KHÔNG chọn hộ – hai nguồn lệch nhau thì bày cả hai ra
  TG2  không có tỷ giá đúng ngày thì lấy ngày GẦN NHẤT và NÓI RÕ là ngày khác
  TG3  tỷ giá quá cũ thì thà nói không có, còn hơn đưa một cái bẫy
  TG4  KHÔNG ghi đè âm thầm – trùng (đồng tiền, ngày, nguồn) thì chặn và chỉ chỗ sửa
  TG5  hai NGUỒN khác nhau cùng ngày thì được phép cùng tồn tại
  TG6  sửa phải có lý do, và số cũ KHÔNG biến mất
  TG7  tỷ giá 0, âm, hay của ngày chưa tới thì chặn
  TG8  tỷ giá có cửa đính kèm chứng từ – không thì nó là con số không ai kiểm được
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_tygia.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_tygia.db", "test_tygia.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest                                              # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

from app.main import app                                   # noqa: E402
from app.models.attachments import DOI_TUONG_DAY_DU        # noqa: E402

client = TestClient(app)

HOM_QUA = date.today() - timedelta(days=1)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str) -> dict:
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()  # noqa: E712
        assert u is not None, f"không có tài khoản vai trò {vai} trong dữ liệu mẫu"
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _them(h, tien_te, ngay, ty_gia, nguon="", **kw):
    return client.post("/api/v1/ty-gia", headers=h, json={
        "tien_te": tien_te, "ngay": str(ngay), "ty_gia": ty_gia, "nguon": nguon, **kw})


# =============================================================================================
# TG1 · TRA CỨU KHÔNG CHỌN HỘ
# =============================================================================================
def test_tg1_hai_nguon_lech_nhau_thi_BAY_CA_HAI_chu_khong_chon_ho():
    """Hai tỷ giá khác nhau cho cùng một ngày KHÔNG phải lỗi dữ liệu – đó là hai sự thật.

    "Vietcombank bán ra 25.500" và "thực tế chuyển khoản 25.620" đều đúng. Khoản nào dùng số nào là
    việc của người lập chứng từ. Máy chọn hộ thì cái chênh lệch ấy biến mất khỏi tầm mắt đúng vào
    lúc cần nhìn nhất – 120 đồng trên 40.000 USD là 4,8 triệu.
    """
    h = login("ketoan")
    n = date(2026, 4, 4)
    assert _them(h, "USD", n, 25500, "Vietcombank bán ra").status_code == 201
    assert _them(h, "USD", n, 25620, "Thực tế chuyển khoản").status_code == 201

    r = client.get(f"/api/v1/ty-gia/tra-cuu?tien_te=USD&ngay={n}", headers=h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["dung_ngay"]) == 2, f"phải bày cả hai nguồn, đang trả {j['dung_ngay']}"
    assert j["nhieu_nguon"] is True, "hai nguồn lệch nhau là việc NGƯỜI NHẬP cần biết, phải nói ra"
    assert {x["ty_gia"] for x in j["dung_ngay"]} == {25500.0, 25620.0}


# =============================================================================================
# TG2 · KHÔNG CÓ ĐÚNG NGÀY THÌ PHẢI NÓI LÀ NGÀY KHÁC
# =============================================================================================
def test_tg2_khong_co_dung_ngay_thi_lay_gan_nhat_va_NOI_RO_la_ngay_khac():
    """Đưa ra một tỷ giá của ngày khác mà không nói, là để người ta nhân nhầm mà không biết."""
    h = login("ketoan")
    assert _them(h, "AUD", date(2026, 4, 1), 18500, "Vietcombank").status_code == 201

    r = client.get("/api/v1/ty-gia/tra-cuu?tien_te=AUD&ngay=2026-04-04", headers=h)
    j = r.json()
    assert j["dung_ngay"] == []
    assert j["gan_nhat"] is not None, "có tỷ giá cách 3 ngày thì phải gợi ý"
    assert j["gan_nhat"]["lech_ngay"] == 3
    assert "KHÔNG phải ngày" in j["gan_nhat"]["canh_bao"], \
        "phải nói thẳng đây là tỷ giá của ngày khác"
    assert "ngày này" in j["ghi_chu"]


# =============================================================================================
# TG3 · QUÁ CŨ THÌ THÀ NÓI KHÔNG CÓ
# =============================================================================================
def test_tg3_ty_gia_qua_cu_KHONG_duoc_dua_ra_lam_goi_y():
    """Tỷ giá của hai tháng trước không phải một gợi ý tử tế, nó là một cái bẫy: nó điền sẵn vào
    form, trông như có căn cứ, và người nhập vội thì bấm qua."""
    h = login("ketoan")
    assert _them(h, "GBP", date(2026, 1, 5), 31000, "Vietcombank").status_code == 201

    r = client.get("/api/v1/ty-gia/tra-cuu?tien_te=GBP&ngay=2026-06-05", headers=h)
    j = r.json()
    assert j["gan_nhat"] is None, "cách 5 tháng mà vẫn điền sẵn thì thà đừng gợi ý"
    assert "tự nhập" in j["ghi_chu"]


# =============================================================================================
# TG4 · KHÔNG GHI ĐÈ ÂM THẦM
# =============================================================================================
def test_tg4_trung_dong_tien_ngay_nguon_thi_CHAN_va_chi_cho_sua():
    """Ghi đè âm thầm là cách một con số tỷ giá đổi mà không ai biết. Chặn, và chỉ đúng chỗ sửa."""
    h = login("ketoan")
    n = date(2026, 5, 6)
    assert _them(h, "CAD", n, 19000, "Vietcombank").status_code == 201
    r = _them(h, "CAD", n, 19400, "Vietcombank")
    assert r.status_code == 409, f"phải chặn, đang trả {r.status_code}"
    assert "19,000" in r.text or "19000" in r.text, "phải nói số CŨ là bao nhiêu"
    assert "lý do" in r.text, "phải chỉ ra rằng muốn đổi thì sửa kèm lý do"


# =============================================================================================
# TG5 · HAI NGUỒN CÙNG NGÀY THÌ ĐƯỢC PHÉP CÙNG TỒN TẠI
# =============================================================================================
def test_tg5_cung_ngay_khac_NGUON_thi_khong_chan():
    """Gộp 'Vietcombank bán ra' với 'tỷ giá trên hợp đồng' làm một dòng là bịa ra một sự thật thứ ba
    không tồn tại."""
    h = login("ketoan")
    n = date(2026, 5, 7)
    assert _them(h, "EUR", n, 27800, "Vietcombank").status_code == 201
    assert _them(h, "EUR", n, 27950, "Hợp đồng đối tác").status_code == 201


# =============================================================================================
# TG6 · SỬA PHẢI CÓ LÝ DO, VÀ SỐ CŨ KHÔNG BIẾN MẤT
# =============================================================================================
def test_tg6_sua_phai_co_ly_do_va_so_cu_van_con_trong_lich_su():
    """Sửa 25.500 thành 25.620 trên một khoản 40.000 USD là 4,8 triệu đổi chủ. 'sửa' không nói được
    vì sao."""
    h = login("ketoan")
    n = date(2026, 5, 8)
    tid = _them(h, "SGD", n, 19000, "Vietcombank").json()["row"]["id"]

    r = client.put(f"/api/v1/ty-gia/{tid}", headers=h, json={"ty_gia": 19250, "ly_do_sua": "sửa"})
    assert r.status_code == 422, "lý do ba chữ không phải một lý do"

    r = client.put(f"/api/v1/ty-gia/{tid}", headers=h,
                   json={"ty_gia": 19250, "ly_do_sua": "Ngân hàng đính chính bảng niêm yết 08/05"})
    assert r.status_code == 200, r.text
    row = r.json()["row"]
    assert row["ty_gia"] == 19250.0
    assert row["so_lan_sua"] == 1
    assert "19,000" in row["lich_su"], "SỐ CŨ phải còn trong lịch sử – không thì không truy được"
    assert "đính chính" in row["lich_su"], "lý do phải được giữ lại cùng lần sửa"

    # Sửa LẦN THỨ HAI. Phải kiểm đúng chỗ này: một lần sửa thì ghi đè và nối thêm cho ra kết quả
    # giống hệt nhau, nên bài thử một lần KHÔNG chứng minh được lịch sử có tích luỹ hay không.
    # Cái sai thật là lần sửa thứ hai xoá mất lần thứ nhất – và nó chỉ lộ ra từ lần thứ hai trở đi.
    r = client.put(f"/api/v1/ty-gia/{tid}", headers=h,
                   json={"ty_gia": 19180, "ly_do_sua": "Đối chiếu sao kê: thực tế chuyển 19.180"})
    assert r.status_code == 200, r.text
    row = r.json()["row"]
    assert row["so_lan_sua"] == 2
    assert "đính chính" in row["lich_su"], \
        "lần sửa THỨ HAI không được xoá lần thứ nhất – ghi đè là mất dấu vết"
    assert "sao kê" in row["lich_su"], "lần sửa thứ hai cũng phải được ghi lại"
    assert "19,250" in row["lich_su"], "số của lần sửa trước phải còn"
    assert len([d for d in row["lich_su"].split("\n") if d.strip()]) == 2, \
        "hai lần sửa phải là hai dòng lịch sử"


# =============================================================================================
# TG7 · SỐ VÔ LÝ THÌ CHẶN
# =============================================================================================
def test_tg7_ty_gia_khong_duong_hoac_ngay_chua_toi_thi_chan():
    """Tỷ giá 0 nhân vào tiền ra 0, và không ai nhìn lại con số ấy nữa. Ngày chưa tới thì không ngân
    hàng nào đã niêm yết."""
    h = login("ketoan")
    assert _them(h, "JPY", HOM_QUA, 0, "x").status_code == 422
    assert _them(h, "JPY", HOM_QUA, -170, "x").status_code == 422
    assert _them(h, "JPY", date.today() + timedelta(days=3), 170, "x").status_code == 422
    assert _them(h, "VND", HOM_QUA, 1, "x").status_code == 422, \
        "đồng Việt Nam không có tỷ giá sang chính nó"
    assert _them(h, "US", HOM_QUA, 25000, "x").status_code == 422, "mã đồng tiền phải đúng 3 chữ"


# =============================================================================================
# TG8 · PHẢI CÓ CỬA ĐÍNH KÈM CHỨNG TỪ
# =============================================================================================
def test_tg8_ty_gia_phai_co_cua_dinh_kem_chung_tu():
    """Chủ tịch chốt: nhân viên tự nhập tay VÀ tải tệp/ảnh. Không có cửa đính kèm thì tỷ giá là một
    con số người gõ vào mà không ai kiểm được – mà nó là con số NHÂN vào tiền.

    Dùng kho hồ sơ chung, không dựng kho ảnh riêng: một kho chung là một bộ quy tắc chung về kích
    thước, loại tệp, ai xem được, và thu hồi thay vì xoá.
    """
    assert "ty_gia" in DOI_TUONG_DAY_DU, \
        "tỷ giá chưa có trong danh mục đối tượng đính kèm – nhân viên không tải ảnh lên được"
    ten, phong, nhom, theo_doi_tuong = DOI_TUONG_DAY_DU["ty_gia"]
    assert nhom == "02_Ke_toan", "chứng từ tỷ giá là chứng từ ghi sổ, thuộc nhóm hồ sơ Kế toán"
    assert theo_doi_tuong is False, \
        ("lưu theo THÁNG: một tỷ giá thuộc về một NGÀY, xếp theo id dòng thì không ai tìm ra ảnh "
         "của cả tháng để đối chiếu một lượt")

    h = login("ketoan")
    r = client.get("/api/v1/tep/cau-hinh", headers=h)
    assert r.status_code == 200, r.text
    assert "ty_gia" in str(r.json()), "cửa đính kèm phải BÀY RA loại hồ sơ tỷ giá cho người dùng"


# =============================================================================================
# TG9 · MÔ HÌNH VÀ BẢN NÂNG CẤP PHẢI KHAI CÙNG MỘT THỨ
# =============================================================================================
def test_tg9_mo_hinh_va_ban_nang_cap_khai_cung_mot_bang():
    """Hai chỗ khai cùng một bảng thì sớm muộn lệch nhau, và lệch ở chỗ không ai nhìn.

    Phép thử ở máy dùng `create_all` (đọc MÔ HÌNH), còn hệ thống thật chạy `alembic upgrade head`
    (đọc BẢN NÂNG CẤP). Thiếu một cột ở bản nâng cấp thì mọi phép thử ở máy vẫn xanh, và cột ấy chỉ
    vắng mặt trên hệ thống thật – lỗi hiện ra lúc người dùng bấm, không phải lúc chạy thử.

    Cùng một lớp lỗi đã làm hỏng `alembic upgrade head` ngày 14/9/2026 (DEFAULT 0 cho cột BOOLEAN).
    """
    import re
    from pathlib import Path

    from app.models.ty_gia import TyGia

    thu_muc = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    # Phải khớp ĐÚNG lệnh tạo BẢNG ty_gia. Tìm chuỗi '"ty_gia"' không thôi thì trúng cả những bản
    # nâng cấp có CỘT tên ty_gia trên bảng khác – đo được: 3 bản (vé máy bay, lịch thanh toán, dự
    # toán lớp 3) đều có cột ấy.
    tao = re.compile(r'op\.create_table\(\s*"ty_gia"')
    ban = [p for p in thu_muc.glob("*.py") if tao.search(p.read_text(encoding="utf-8"))]
    assert len(ban) == 1, f"phải có ĐÚNG MỘT bản nâng cấp tạo bảng ty_gia, đang thấy {len(ban)}"
    noi_dung = ban[0].read_text(encoding="utf-8")

    cot_ban = set(re.findall(r'sa\.Column\(\s*"([a-z_]+)"', noi_dung))
    cot_mo_hinh = {c.name for c in TyGia.__table__.columns}
    assert cot_ban == cot_mo_hinh, (
        f"mô hình và bản nâng cấp lệch nhau.\n"
        f"  chỉ có ở mô hình:      {sorted(cot_mo_hinh - cot_ban)}\n"
        f"  chỉ có ở bản nâng cấp: {sorted(cot_ban - cot_mo_hinh)}")

    # Chỉ mục duy nhất phải là (tien_te, ngay, NGUON) – KHÔNG phải (tien_te, ngay). Hai nguồn khác
    # nhau trong cùng một ngày là hai sự thật; chặn chúng là ép người nhập bịa.
    # Kiểm ĐÚNG danh sách cột của chỉ mục duy nhất, không chỉ kiểm hai chuỗi có mặt đâu đó trong
    # tệp: "nguon" còn xuất hiện ở dòng khai cột, nên phép kiểm lỏng vẫn xanh khi chỉ mục đã bị rút
    # còn (tien_te, ngay) – thử bẻ thì thấy.
    duy_nhat = re.search(r"op\.create_index\(\s*[^)]*?unique=True", noi_dung, re.S)
    assert duy_nhat and '"nguon"' in duy_nhat.group(0), (
        "chỉ mục duy nhất phải là (tien_te, ngay, NGUON). Rút còn (tien_te, ngay) là cấm hai nguồn "
        "khác nhau cùng một ngày – mà đó là hai sự thật, ép chúng thành một là ép người nhập bịa.")
    ix = {i.name for i in TyGia.__table__.indexes}
    assert "ux_ty_gia_mot_nguon_mot_ngay" in ix, "mô hình thiếu chỉ mục duy nhất"

    # Bản nâng cấp lùi lại được – bảng mới, không sửa bảng nào đang có.
    assert "def downgrade" in noi_dung and 'op.drop_table("ty_gia")' in noi_dung, \
        "bản nâng cấp phải lùi lại được sạch"

    # Tỷ giá là TỶ LỆ, không phải tiền: Numeric(18, 6) chứ không phải kiểu TIEN (18, 2).
    # 1 KRW ≈ 0,0181 đ – làm tròn 2 chữ số thành 0,02 là sai 10%.
    assert "scale=6" in noi_dung, "tỷ giá phải giữ 6 chữ số thập phân, không dùng kiểu TIEN"
