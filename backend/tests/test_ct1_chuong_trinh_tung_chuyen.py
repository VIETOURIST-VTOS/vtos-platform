# -*- coding: utf-8 -*-
"""CT-1 · 4.4.2 Chương trình của từng chuyến: chép một lần, đề xuất chứ không áp đặt.

HÀNG RÀO ĐẮT NHẤT TỆP NÀY là `test_sua_san_pham_KHONG_doi_chuong_trinh_chuyen`. Nó canh đúng cái
hỏng mà cả vòng này sinh ra để chữa: trước bản này chương trình chuyến đọc sống từ sản phẩm, nên
sửa sản phẩm hôm nay là viết lại lịch trình của một đoàn đã đi tuần trước — và bản khách cầm trong
tay không còn khớp với bản trên hệ thống, đúng lúc có tranh chấp thì không ai chứng minh được gì.

HÀNG RÀO THỨ HAI canh một cám dỗ: `test_de_xuat_tach_KHONG_BAO_GIO_tu_ghi`. Bộ tách rất dễ viết
thành "mở tab là tự đổ nội dung vào", và bản tự đổ trông gọn gàng nên không ai đọc lại. Một lịch
trình sai mà gọn thì tệ hơn một khung rỗng, vì khung rỗng thì người ta còn biết là phải soạn.
"""
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ct1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ct1.db"):
    os.remove("test_ct1.db")

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal, Base        # noqa: E402
from app.models.core import User, Tour, Product      # noqa: E402
from app.models.chuong_trinh import ChuongTrinhTour, ChuongTrinhNgay   # noqa: E402
from app.services import chuong_trinh_tour as CT     # noqa: E402

GOC = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _doc(*p) -> str:
    return (GOC.joinpath(*p)).read_text(encoding="utf-8")


def _dh(db):
    return db.execute(select(User).where(User.role == "nv_dh",
                                         User.active.is_(True))).scalars().first()


def _chuyen_moi(db, ngay_bat_dau: date, so_ngay: int = 3, program: str = ""):
    """Dựng một chuyến RIÊNG cho phép thử, kèm sản phẩm riêng — không mượn dữ liệu chuyến khác."""
    sp = Product(code=f"CT1-{ngay_bat_dau:%Y%m%d}-{so_ngay}", name="San pham thu CT-1",
                 program=program, days=so_ngay)
    db.add(sp)
    db.flush()
    dh = _dh(db)
    t = Tour(code=f"CT1T-{ngay_bat_dau:%Y%m%d}-{so_ngay}", name="Chuyen thu CT-1",
             tour_type="trong_nuoc", start_date=ngay_bat_dau,
             end_date=ngay_bat_dau + timedelta(days=so_ngay - 1),
             operator_id=dh.id, product_id=sp.id, days=so_ngay)
    db.add(t)
    db.flush()
    return t, sp, dh


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CẤU TRÚC
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_hai_bang_co_that_mot_migration_mot_dau_alembic():
    for b in ("chuong_trinh_tour", "chuong_trinh_ngay"):
        assert b in Base.metadata.tables, f"bảng {b} không vào Base.metadata"
    thu_muc = GOC / "backend" / "alembic" / "versions"
    # Mô hình có bảng KHÔNG đủ — phải có migration tạo ra bảng ấy. Máy phép thử dựng bằng
    # create_all nên vẫn xanh; bản chạy thật dựng bằng alembic nên sẽ thiếu bảng.
    co = [p.name for p in thu_muc.glob("*.py")
          if all(b in p.read_text(encoding="utf-8")
                 for b in ("chuong_trinh_tour", "chuong_trinh_ngay"))]
    assert len(co) == 1, f"hai bảng phải nằm trong ĐÚNG MỘT migration, đang thấy: {co}"
    rev, down = {}, {}
    for p in thu_muc.glob("*.py"):
        s = p.read_text(encoding="utf-8")
        r = re.search(r'^revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        d = re.search(r'^down_revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        if r:
            rev[r.group(1)] = p.name
            down[r.group(1)] = d.group(1) if d else None
    dau = [k for k in rev if k not in set(down.values())]
    assert len(dau) == 1, f"alembic phải có ĐÚNG MỘT đầu: {[rev[k] for k in dau]}"


def test_migration_KHONG_chep_san_du_lieu():
    """Không một dòng INSERT nào trong migration.

    Chép hàng loạt chương trình sản phẩm vào hàng trăm chuyến là ghi vào sổ một nội dung mà không
    người điều hành nào đọc qua — và từ đó nó trông như đã được duyệt.
    """
    import ast
    thu_muc = GOC / "backend" / "alembic" / "versions"
    tep = next(p for p in thu_muc.glob("*.py") if "chuong_trinh_ngay" in p.read_text(encoding="utf-8"))
    nguon = tep.read_text(encoding="utf-8")
    # Đọc THÂN HÀM, không đọc cả tệp: lời khai ở đầu tệp có nhắc chính câu lệnh nó từ chối viết,
    # nên quét cả tệp thì hàng rào bắt đúng lời khai của mình. (Đã xảy ra lần chạy đầu.)
    than = []
    for nut in ast.parse(nguon).body:
        if isinstance(nut, ast.FunctionDef) and nut.name in ("upgrade", "downgrade"):
            than.append(ast.get_source_segment(nguon, nut) or "")
    than = "\n".join(than).lower()
    assert than, "không đọc được thân hàm upgrade/downgrade"
    for cam in ("insert into", "bulk_insert", "select program", "update products"):
        assert cam not in than, f"migration đang chép sẵn dữ liệu ({cam!r})"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CHÉP MỘT LẦN, KHÔNG NỐI SỐNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_mo_lan_dau_dung_du_ngay_RONG_va_chup_ban_san_pham():
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date(2027, 6, 1), 3, "Ngày 1: Đi\nNgày 2: Chơi\nNgày 3: Về")
        d = CT.mo(db, dh, t.id)
        assert len(d["rows"]) == 3, "dựng không đủ số ngày của chuyến"
        assert all(r["trong"] for r in d["rows"]), (
            "mở tab mà đã có nội dung — hệ thống vừa tự đổ bản sản phẩm vào, đúng việc nó không "
            "được làm")
        assert d["ngay_trong"] == [1, 2, 3]
        assert d["ban_san_pham_goc"].startswith("Ngày 1"), "không chụp lại bản sản phẩm"
        assert d["rows"][0]["ngay"] == "2027-06-01" and d["rows"][2]["ngay"] == "2027-06-03"
        db.rollback()


def test_sua_san_pham_KHONG_doi_chuong_trinh_chuyen():
    """Cái hỏng mà cả vòng này sinh ra để chữa.

    Sửa chương trình SẢN PHẨM sau khi chuyến đã chép: chuyến phải giữ nguyên nội dung của nó, và
    hệ thống phải BÁO là sản phẩm đã đổi — báo chứ không tự chép lại.
    """
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date(2027, 7, 1), 2, "Ngày 1: Bản CŨ\nNgày 2: Bản CŨ")
        CT.mo(db, dh, t.id)
        CT.sua_ngay(db, dh, t.id, 1, {"noi_dung": "Điều hành soạn tay cho chuyến này"})
        sp.program = "Ngày 1: Bản MỚI của sản phẩm\nNgày 2: Bản MỚI"
        db.flush()
        d = CT.xem(db, t.id)
        assert d["rows"][0]["noi_dung"] == "Điều hành soạn tay cho chuyến này", (
            "sửa sản phẩm đã viết đè lên chương trình của chuyến — đây đúng là cái hỏng vòng này "
            "đi chữa: một đoàn đã đi xong sẽ bị viết lại lịch trình")
        assert d["lech_voi_san_pham"]["co_lech"] is True, (
            "sản phẩm đã đổi mà hệ thống không báo — người điều hành không có cách nào biết")
        assert d["ban_san_pham_goc"].find("Bản CŨ") >= 0, "ảnh chụp bị ghi đè"
        db.rollback()


def test_lech_voi_san_pham_so_voi_ANH_CHUP_chu_khong_so_voi_chuong_trinh_chuyen():
    """So nhầm thì dòng cảnh báo thành vô nghĩa: chương trình chuyến sửa có chủ ý, lúc nào cũng lệch."""
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date(2027, 8, 1), 2, "Ngày 1: A\nNgày 2: B")
        CT.mo(db, dh, t.id)
        CT.sua_ngay(db, dh, t.id, 1, {"noi_dung": "khác hẳn sản phẩm"})
        assert CT.xem(db, t.id)["lech_voi_san_pham"]["co_lech"] is False, (
            "sửa chương trình CHUYẾN mà lại báo SẢN PHẨM đã đổi — đang so nhầm hai thứ")
        db.rollback()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỀ XUẤT, KHÔNG ÁP ĐẶT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_de_xuat_tach_chi_nhan_moc_ngay_ro_rang():
    d = CT.de_xuat_tach("Ngày 1: Hà Nội – Sa Pa\nĂn trưa\n\nNgày 2: Fansipan\nLeo núi")
    assert d["tach_duoc"] and d["so_ngay"] == 2
    assert [r["ngay_thu"] for r in d["rows"]] == [1, 2]
    assert d["rows"][0]["tieu_de"].startswith("Hà Nội")
    # Không có mốc thì KHÔNG tách — không chia đều theo đoạn, không đoán.
    for xau in ("Chương trình trọn gói 3 ngày 2 đêm, bao gồm ăn ở đi lại.",
                "Sáng: đi. Trưa: ăn. Tối: về.", ""):
        k = CT.de_xuat_tach(xau)
        assert k["tach_duoc"] is False and k["rows"] == [], (
            f"đã tách một văn bản không có mốc ngày: {xau!r} — đó là đoán, và chỗ đoán nằm đúng "
            "trong thứ sẽ gửi cho khách")


def test_de_xuat_tach_KHONG_BAO_GIO_tu_ghi():
    """Gọi đề xuất bao nhiêu lần cũng không đổi một chữ nào trong cơ sở dữ liệu."""
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date(2027, 9, 1), 2, "Ngày 1: X\nNgày 2: Y")
        CT.mo(db, dh, t.id)
        for _ in range(3):
            CT.de_xuat_tach(CT.xem(db, t.id)["ban_san_pham_goc"])
        assert all(r["trong"] for r in CT.xem(db, t.id)["rows"]), (
            "gọi đề xuất đã ghi vào cơ sở dữ liệu — đề xuất phải là đề xuất")
        db.rollback()


def test_nhan_de_xuat_chi_ghi_vao_ngay_RONG():
    """Người ta soạn tay rồi bấm nhầm nút thì mất công cả buổi, mà bản đè lên lại trông hợp lý."""
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date(2027, 10, 1), 2, "Ngày 1: tự động\nNgày 2: tự động")
        CT.mo(db, dh, t.id)
        CT.sua_ngay(db, dh, t.id, 1, {"noi_dung": "SOẠN TAY – không được đè"})
        r = CT.nhan_de_xuat(db, dh, t.id)
        assert r["da_ghi"] == [2] and r["bo_qua_vi_da_co_noi_dung"] == [1]
        d = CT.xem(db, t.id)
        assert d["rows"][0]["noi_dung"] == "SOẠN TAY – không được đè"
        assert "tự động" in d["rows"][1]["noi_dung"]
        db.rollback()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# KHÔNG TỰ SỬA CHO KHỚP
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_lech_so_ngay_duoc_NOI_RA_chu_khong_tu_them_hay_xoa():
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date(2027, 11, 1), 3)
        CT.mo(db, dh, t.id)
        t.end_date = t.start_date + timedelta(days=4)      # chuyến kéo dài thành 5 ngày
        db.flush()
        d = CT.xem(db, t.id)
        assert d["lech_so_ngay"]["co_lech"] is True
        assert d["lech_so_ngay"]["khung"] == 3 and d["lech_so_ngay"]["chuyen"] == 5
        assert len(d["rows"]) == 3, (
            "hệ thống vừa tự thêm ngày — tự thêm là in ra một ngày trống không ai biết từ đâu ra")
        CT.them_ngay(db, dh, t.id)
        assert len(CT.xem(db, t.id)["rows"]) == 4, "thêm tay không ăn"
        db.rollback()


def test_xoa_ngay_bat_buoc_ly_do_va_chi_xoa_duoc_ngay_CUOI():
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date(2027, 12, 1), 3)
        CT.mo(db, dh, t.id)
        with pytest.raises(ValueError):
            CT.xoa_ngay(db, dh, t.id, 3, "")
        with pytest.raises(ValueError) as e:
            CT.xoa_ngay(db, dh, t.id, 2, "bỏ bớt")       # giữa khung
        assert "CUỐI" in str(e.value)
        CT.xoa_ngay(db, dh, t.id, 3, "khách đổi lịch, về sớm một ngày")
        d = CT.xem(db, t.id)
        assert [r["ngay_thu"] for r in d["rows"]] == [1, 2]
        db.rollback()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# SỬA SAU KHI KHỞI HÀNH
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_sua_sau_khoi_hanh_KHONG_bi_cam_nhung_phai_ghi_ly_do_va_duoc_DEM():
    """Cấm thì người ta sửa ở chỗ khác và hệ thống mất dấu hoàn toàn — mất dấu tệ hơn một dòng lý do."""
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date.today() - timedelta(days=2), 3)
        CT.mo(db, dh, t.id)
        assert CT.xem(db, t.id)["da_khoi_hanh"] is True
        with pytest.raises(ValueError) as e:
            CT.sua_ngay(db, dh, t.id, 2, {"noi_dung": "đổi điểm"})
        assert "lý do" in str(e.value)
        CT.sua_ngay(db, dh, t.id, 2, {"noi_dung": "đổi điểm"}, "mưa lớn, không lên được đèo")
        r = CT.xem(db, t.id)["rows"][1]
        assert r["lan_sua_sau_khoi_hanh"] == 1 and "mưa lớn" in r["ly_do_sua_gan_nhat"]
        CT.sua_ngay(db, dh, t.id, 2, {"noi_dung": "đổi tiếp"}, "khách xin về sớm")
        assert CT.xem(db, t.id)["rows"][1]["lan_sua_sau_khoi_hanh"] == 2, (
            "sửa lần hai mà bộ đếm không tăng — không đếm thì không ai thấy một chuyến bị sửa "
            "năm lần sau khi đã đi")
        db.rollback()


def test_chuyen_chua_khoi_hanh_thi_sua_tu_do():
    with SessionLocal() as db:
        t, sp, dh = _chuyen_moi(db, date.today() + timedelta(days=30), 2)
        CT.mo(db, dh, t.id)
        CT.sua_ngay(db, dh, t.id, 1, {"noi_dung": "soạn bình thường"})
        r = CT.xem(db, t.id)["rows"][0]
        assert r["lan_sua_sau_khoi_hanh"] == 0 and r["noi_dung"] == "soạn bình thường"
        db.rollback()


def test_cua_ghi_hep_hon_cua_xem_va_kinh_doanh_doc_duoc():
    from app.api.v1 import chuong_trinh as API
    assert set(API.GHI) < set(API.XEM), "nhóm ghi phải HẸP HƠN THẬT SỰ nhóm xem"
    from app.services.access import READ_ALL
    assert not (set(API.GHI) & set(READ_ALL)), (
        "Ban kiểm soát và robot kiểm soát không soạn chương trình tour. Lớp READ_ONLY_ROLES ở "
        "access.py chặn họ, nên để tên họ ở đây không hở quyền — nhưng danh sách đọc ra là sai, và "
        "người sửa mã sau này tin vào danh sách chứ không đi tìm lớp chặn.")
    for vai in ("nv_kd", "tp_kd", "sales_admin"):
        assert vai in API.XEM, f"{vai} phải đọc được chương trình để trả lời khách"
        assert vai not in API.GHI, f"{vai} không soạn chương trình — việc ấy của Điều hành"
    for vai in ("tp_dh", "nv_dh"):
        assert vai in API.GHI


def test_khong_loi_nao_cho_bks_ghi_chuong_trinh():
    """Gọi THẬT một lệnh ghi bằng tài khoản `bks`, không chỉ đọc danh sách.

    Có HAI hàng rào chặn Ban kiểm soát ghi, ở hai tệp khác nhau: danh sách `GHI` của cửa này, và lớp
    `READ_ONLY_ROLES` ở access.py chặn mọi lệnh ghi của `bks`/`robot_ks` trên toàn hệ thống. Phép
    kiểm này đã được KIỂM NGƯỢC, và đây là kết quả đo được — ghi ra để không ai nhầm nó đo gì:

      · thêm `bks` vào `GHI`, giữ `READ_ONLY_ROLES`  → phép kiểm này VẪN XANH
        (lớp kia đỡ), nhưng `test_cua_ghi_hep_hon_cua_xem_va_kinh_doanh_doc_duoc` đỏ.
      · nới `READ_ONLY_ROLES = ()`, giữ `GHI`         → phép kiểm này VẪN XANH (danh sách đỡ).
      · phá CẢ HAI                                    → phép kiểm này ĐỎ.

    Nên nó KHÔNG đo riêng lớp `READ_ONLY_ROLES`. Nó đo điều hẹp hơn nhưng là điều thật sự đáng đo:
    không còn một lối nào cho Ban kiểm soát ghi. Đó là trường hợp duy nhất mà hai phép kiểm kia đều
    không bắt được — ai nới một hàng rào thì bị phép kiểm danh sách chặn, nhưng ai nới cả hai cùng
    lúc (và việc ấy có thật khi người ta "dọn" quyền) thì chỉ phép kiểm này còn lại.
    """
    with TestClient(app) as c:
        with SessionLocal() as db:
            t, sp, dh = _chuyen_moi(db, date.today() + timedelta(days=30), 2)
            CT.mo(db, dh, t.id)
            db.commit()
            tid = t.id
        for vai in ("bks", "robot_ks"):
            r = c.post("/api/v1/auth/login", data={"username": vai, "password": "Vtos@Demo#2026"})
            if r.status_code != 200:
                continue                      # tài khoản mẫu không có trong bản gieo này
            h = {"Authorization": f"Bearer {r.json()['access_token']}"}
            assert c.get(f"/api/v1/chuong-trinh/{tid}", headers=h).status_code == 200, \
                f"{vai} phải ĐỌC được — họ là vai đọc tất cả"
            w = c.put(f"/api/v1/chuong-trinh/{tid}/ngay/1", headers=h,
                      json={"noi_dung": "bks sua thu"})
            assert w.status_code == 403, \
                f"{vai} ghi được chương trình tour — CẢ HAI hàng rào đã hở: danh sách GHI của cửa " \
                "này và lớp READ_ONLY_ROLES ở access.py"
        with SessionLocal() as db:
            db.query(ChuongTrinhNgay).delete()
            db.query(ChuongTrinhTour).delete()
            db.commit()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# MÀN HÌNH
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_cay_khong_con_khai_la_chi_XEM_va_the_duoc_dung_that():
    cay = _doc("web", "lib", "cay_phan_he.ts")
    dong = next(d for d in cay.splitlines() if d.strip().startswith('{ ma: "4.4.2"'))
    assert "chỉ XEM" not in dong and "chưa" not in dong, (
        f"4.4.2 đã dựng thật mà cây vẫn khai là chỉ xem: {dong.strip()}")
    trang = _doc("web", "app", "tours", "[id]", "page.tsx")
    assert '["chuongtrinh", "Chương trình"]' in trang, "trang chuyến chưa khai thẻ Chương trình"
    assert "<ChuongTrinhChuyen tourId={t.id} />" in trang, (
        "thẻ khai rồi mà KHÔNG dựng khối nào — hỏi chỗ dựng chứ không hỏi tên mô-đun")
    tp = _doc("web", "components", "ChuongTrinhChuyen.tsx")
    for phai_co in ("/chuong-trinh/", "lech_voi_san_pham", "ngay_trong", "ban_san_pham_goc"):
        assert phai_co in tp, f"màn hình không in {phai_co}"
    assert "lan_sua_sau_khoi_hanh" in tp, "màn hình không in số lần sửa sau khi khởi hành"
