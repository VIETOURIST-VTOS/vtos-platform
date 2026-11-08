# -*- coding: utf-8 -*-
"""Đợt TSCD-1 08/11/2026 — TK NGUYÊN GIÁ TÀI SẢN CỐ ĐỊNH CÓ CHỖ CHỌN.

ĐO ĐƯỢC TRÊN HỆ THỐNG THẬT 08/11/2026, gọi thẳng `POST /fixed-assets` bốn lần:

    huu_hinh  -> 201, nhưng vào `211` — TÀI KHOẢN CHA (2111 / 2112 / 2113)
    vo_hinh   -> 422 «Tài khoản 2143 không có trong danh mục»
    thue_tc   -> 422 «Tài khoản 212 không có trong danh mục»
    bds_dt    -> 422 «Tài khoản 217 không có trong danh mục»

Tức form mời người dùng chọn BỐN loại mà chỉ MỘT loại lưu được, và lỗi trả về nói về một số
hiệu tài khoản — thứ người nhập tài sản không có cách nào hiểu là phải làm gì.

Chủ tịch chốt 08/11/2026: bắt buộc chọn NGAY (hệ thống đang có 0 tài sản nên siết lúc này không
làm ai đứng việc — đúng lập luận Đợt DL-7), và loại thiếu tài khoản thì NÓI RA kèm đúng số hiệu
cần mở chứ không ẩn đi. KHÔNG tự mở thêm tài khoản vào danh mục: đó là số liệu, việc của Kế toán
(ranh giới công việc 09/9/2026).

ĐỢT NÀY KHÔNG GHI SỔ GÌ: `asset_account` hiện không đi vào một bút toán nào — khấu hao chỉ ghi
`expense_account` / `depr_account`. Nó là nhãn trên thẻ và trong bảng kê MISA, và sai nhãn thì
báo cáo theo nhóm tài sản sai.

BỐN LUẬT:
  1. Bộ TK nguyên giá ĐỌC THẲNG DANH MỤC, không tin bảng mặc định `ASSET_KINDS`.
  2. Loại thiếu tài khoản được NÓI RA kèm đúng số hiệu, và cửa từ chối trước khi tạo thẻ.
  3. Một bộ luật, HAI đường nhập — nhập tay và nạp Excel cùng gọi một hàm.
  4. Thẻ tạo ra KHÔNG rơi vào tài khoản cha, và đợt này không ghi sổ gì.
"""
import inspect
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_tscd1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_tscd1.db"):
    os.remove("test_tscd1.db")

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


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _man():
    return open(MAN, encoding="utf-8").read()


def _khong_cm(x) -> str:
    src = x if isinstance(x, str) else inspect.getsource(x)
    return "\n".join(d.split("#")[0] for d in src.split("\n"))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tscd1_1_bo_TK_nguyen_gia_doc_THANG_danh_muc():
    """Gõ cứng một danh sách ngắn trong mã thì danh mục đổi là danh sách lệch, mà không ai biết.

    `ASSET_KINDS` khai mặc định theo MISA; danh mục THẬT của từng công ty mở tới đâu thì chỉ
    danh mục mới biết. Đây đúng chỗ `211` lọt qua suốt: bảng khai nó, danh mục nói nó là cha.
    """
    from sqlalchemy import select
    from app.models.accounting import Account
    from app.services import assets as AS
    with _db() as db:
        cha = {a.parent for a in db.execute(select(Account)).scalars() if a.parent}

        ds = AS.tk_nguyen_gia_cua_loai(db, "huu_hinh")
        ma = [x["ma"] for x in ds]
        assert ma == ["2111", "2112", "2113"], "bộ TK nguyên giá của TSCĐ hữu hình: " + repr(ma)
        assert "211" not in ma, "`211` là tài khoản cha mà vẫn được mời chọn"
        for x in ds:
            assert x["ma"] not in cha, x["ma"] + " là tài khoản cha"
            assert x["ten"], "thiếu tên tài khoản — người chọn không biết mình chọn gì"

        # Gốc chỉ có MỘT con thì trả về chính con ấy — nơi gọi không phải biết cây sâu mấy tầng.
        assert [x["ma"] for x in AS.tk_nguyen_gia_cua_loai(db, "vo_hinh")] == ["2131"]

        # VÀ BỎ TRỐNG THÌ RA CON ẤY, KHÔNG RA GỐC. Đây là chỗ phép đo ngược 08/11/2026 bắt được
        # một luật nói nhiều hơn nó đo: với `huu_hinh` thì `kiem_tk_nguyen_gia` đã chặn ô trống
        # từ trước, nên đổi `tk_nguyen_gia_chon` thành «lấy mặc định của ASSET_KINDS» vẫn xanh.
        # Với `vo_hinh` thì ô trống ĐƯỢC PHÉP (chỉ một lựa chọn), và lúc ấy mặc định là `213` —
        # TÀI KHOẢN CHA. Chỉ cảnh này mới phân biệt được hai cách viết.
        assert AS.tk_nguyen_gia_chon(db, "vo_hinh", "") == "2131", (
            "bỏ trống ở loại chỉ có một lựa chọn phải ra tài khoản CON, không ra gốc `213`")
        assert AS.tk_nguyen_gia_chon(db, "huu_hinh", "2112") == "2112", "đè lên lựa chọn người nhập"
        assert AS.tk_nguyen_gia_chon(db, "huu_hinh", "") == "", (
            "nhiều lựa chọn mà vẫn tự chọn hộ — việc ấy `kiem_tk_nguyen_gia` phải từ chối trước")

        # LỌC TÀI KHOẢN CHA phải đo trên một cây SÂU HƠN HAI TẦNG, không thì phép đo ngược không
        # phân biệt được: dưới `211` không con nào lại có con, nên bỏ bộ lọc đi vẫn ra đúng ba mã.
        # Bộ dữ liệu mẫu không có cây ba tầng nào dùng làm gốc tài sản, nên DỰNG một cảnh: mở
        # tạm một tài khoản con dưới `2113`, rồi đòi `2113` BIẾN MẤT khỏi danh sách mời chọn.
        # Trên sổ THẬT của anh cảnh này có sẵn — `1121` có 20 tài khoản ngân hàng nằm dưới.
        from app.models.assets import ASSET_KINDS as _AK
        db.add(Account(code="21131", name="Cảnh đo – xe khách", kind="TS", parent="2113",
                       level=3, is_detail=True))
        db.flush()
        try:
            sau = [x["ma"] for x in AS.tk_nguyen_gia_cua_loai(db, "huu_hinh")]
            assert "21131" in sau, "không thấy tài khoản con vừa mở — DỪNG LẠI"
            assert "2113" not in sau, (
                "`2113` nay LÀ tài khoản cha mà vẫn được mời chọn — bộ lọc tài khoản cha không "
                "làm việc, và trên sổ thật đây đúng là cảnh của `1121` với 20 tài khoản ngân hàng")
        finally:
            db.rollback()

    # Và cửa `meta` phải TRẢ bộ ấy ra, không thì form không có gì để dựng.
    d = client.get("/api/v1/assets/meta", headers=login("ketoan")).json()
    hh = d["asset_kinds"]["huu_hinh"]
    assert [x["ma"] for x in hh["tk_nguyen_gia_chon"]] == ["2111", "2112", "2113"]
    assert hh["dung_duoc"] is True


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tscd1_2_loai_thieu_tai_khoan_duoc_NOI_RA_kem_dung_so_hieu():
    """Một câu «không dùng được» mà không nói thiếu gì thì người đọc không làm được gì với nó.

    Và nói ra TRƯỚC khi bấm Lưu, chứ không để họ gặp 422 về một số hiệu tài khoản.
    """
    from app.services import assets as AS
    d = client.get("/api/v1/assets/meta", headers=login("ketoan")).json()["asset_kinds"]

    for loai, can in (("vo_hinh", "2143"), ("thue_tc", "212"), ("bds_dt", "217")):
        o = d[loai]
        assert o["dung_duoc"] is False, loai + " phải báo là chưa dùng được"
        assert can in o["thieu"], (
            loai + " phải nói rõ thiếu `" + can + "`, nhận " + repr(o["thieu"]))

    with _db() as db:
        loi = AS.kiem_tk_nguyen_gia(db, "thue_tc", "")
        assert "212" in loi and "Danh mục" in loi, "câu từ chối không nói số hiệu cần mở: " + loi

    # Cửa tạo thẻ TỪ CHỐI trước khi tạo, và nói đúng câu ấy.
    r = client.post("/api/v1/fixed-assets", headers=login("ketoan"),
                    json={"code": "TSCD1-TC", "name": "Thuê tài chính phép thử", "kind": "thue_tc",
                          "start_date": "2026-11-01", "cost": 1_000_000, "depr_months": 12})
    assert r.status_code == 422, "loại thiếu tài khoản mà cửa vẫn tạo thẻ: " + str(r.status_code)
    assert "212" in r.json()["detail"], r.json()["detail"]

    # Màn hình phải ĐỌC cờ ấy và KHÓA nút Lưu — nói ra mà vẫn cho bấm thì bằng không nói.
    s = _man()
    assert "loaiTs?.dung_duoc === false" in s, "form không đọc cờ `dung_duoc`"
    assert "loaiTs.thieu" in s, "form không in ra số hiệu tài khoản còn thiếu"
    i = s.find('<button className="act teal"')
    j = s.find("onClick={ghi}", i)
    nut = s[i:j] if j > i > 0 else ""
    assert nut, "không cắt được nút Ghi"
    assert "loaiTs?.dung_duoc === false" in nut, "nút Ghi không khóa khi loại chưa dùng được"
    assert "!f.asset_account" in nut, "nút Ghi không khóa khi chưa chọn TK nguyên giá"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tscd1_3_MOT_bo_luat_HAI_duong_nhap():
    """Nắn một đường còn đường kia gán thẳng mặc định thì bằng không nắn.

    Đúng lỗ Đợt CPTT-1 để lại và CPTT-2 phải bịt lần thứ hai: `create_asset` (nhập tay) và
    `_ts_nap` (nạp Excel) tạo bản ghi ở HAI CHỖ KHÁC NHAU, và đường Excel KHÔNG đi qua
    `create_asset`.
    """
    from app.services import assets as AS
    from app.services import intake_phong_ban_2 as IN
    assert hasattr(AS, "kiem_tk_nguyen_gia"), "chưa rút bộ luật ra thành một hàm dùng chung"

    for ten, ham in (("nhập tay", AS.create_asset), ("nạp Excel", IN._ts_kiem)):
        assert "kiem_tk_nguyen_gia" in _khong_cm(ham), ten + " không gọi hàm chung"
    assert "tk_nguyen_gia_chon" in _khong_cm(IN._ts_nap), (
        "`_ts_nap` không đọc cột — cột có trong mẫu mà không đọc thì bằng không có cột")
    assert 'm["tk_nguyen_gia"]' not in _khong_cm(IN._ts_nap), (
        "`_ts_nap` còn gán thẳng mặc định `211` của ASSET_KINDS")

    # Mẫu Excel phải CÓ cột ấy, và nó BẮT BUỘC — lấy qua bộ nạp đã ghép, đúng đường cửa tải đọc.
    from app.services.intake import BO_NAP
    assert "tai_san_co_dinh" in BO_NAP, "không thấy mẫu `tai_san_co_dinh` — DỪNG LẠI, main đã đổi"
    cot = {c["key"]: c for c in BO_NAP["tai_san_co_dinh"]["cot"]}
    assert "tk_nguyen_gia" in cot, "mẫu Excel nạp TSCĐ không có cột `tk_nguyen_gia`"
    assert cot["tk_nguyen_gia"]["bat_buoc"] is True, "cột `tk_nguyen_gia` không bắt buộc"
    with _db() as db:
        assert AS.kiem_tk_nguyen_gia(db, "huu_hinh", cot["tk_nguyen_gia"]["vi_du"]) == "", (
            "ví dụ trong mẫu không qua được chính cửa kiểm: " + repr(cot["tk_nguyen_gia"]["vi_du"]))

    # Và đường Excel TỪ CHỐI đúng từng loại sai.
    def _dong(**o):
        return {"ma_ts": "TSCD1-X", "ten": "Xe phép thử", "loai": "huu_hinh",
                "tk_nguyen_gia": "2113", "ngay_bat_dau_kh": "01/01/2026",
                "nguyen_gia": 500_000_000, "so_thang_kh": 60, **o}

    with _db() as db:
        ok, _, _ = IN._ts_kiem(db, _dong())
        assert not ok, "dòng hợp lệ mà vẫn bị từ chối: " + repr(ok)
        cha, _, _ = IN._ts_kiem(db, _dong(tk_nguyen_gia="211"))
        assert any("211" in x for x in cha), "`211` là tài khoản cha mà cửa kiểm vẫn nhận: " + repr(cha)
        trong, _, _ = IN._ts_kiem(db, _dong(tk_nguyen_gia=""))
        assert any("Chưa chọn TK nguyên giá" in x for x in trong), repr(trong)
        bia, _, _ = IN._ts_kiem(db, _dong(tk_nguyen_gia="9999"))
        assert any("không có trong danh mục" in x for x in bia), repr(bia)


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_tscd1_4_the_tao_ra_KHONG_roi_vao_tai_khoan_cha_va_dot_nay_khong_ghi_so():
    """Khai đúng trong bảng mà thẻ vẫn mang `211` thì bằng không khai — đo bằng BẢN GHI tạo ra."""
    from sqlalchemy import select, func
    from app.models.accounting import Account, JournalLine
    from app.models.assets import FixedAsset
    from app.services import intake_phong_ban_2 as IN

    with _db() as db:
        cha = {a.parent for a in db.execute(select(Account)).scalars() if a.parent}

        def _du_112():
            return float(db.execute(
                select(func.coalesce(func.sum(JournalLine.debit), 0)
                       - func.coalesce(func.sum(JournalLine.credit), 0))).scalar() or 0)

        truoc = _du_112()

        # ── đường NHẬP TAY, qua cửa thật.
        r = client.post("/api/v1/fixed-assets", headers=login("ketoan"),
                        json={"code": "TSCD1-XE", "name": "Xe phép thử", "kind": "huu_hinh",
                              "asset_account": "2113", "expense_account": "6424",
                              "start_date": "2026-11-01", "cost": 600_000_000, "depr_months": 60})
        assert r.status_code == 201, r.text[:300]
        assert r.json()["asset_account"] == "2113", r.json()["asset_account"]

        # Bỏ trống khi có nhiều lựa chọn thì TỪ CHỐI, không đoán hộ.
        r2 = client.post("/api/v1/fixed-assets", headers=login("ketoan"),
                         json={"code": "TSCD1-TRONG", "name": "Bỏ trống", "kind": "huu_hinh",
                               "expense_account": "6424", "start_date": "2026-11-01",
                               "cost": 1_000_000, "depr_months": 12})
        assert r2.status_code == 422 and "2111" in r2.json()["detail"], r2.text[:200]

        # ── đường NẠP EXCEL, cùng một luật.
        IN._ts_nap(db, {"ma_ts": "TSCD1-NAP", "ten": "Máy chủ nạp", "loai": "huu_hinh",
                        "tk_nguyen_gia": "2112", "ngay_bat_dau_kh": "01/11/2026",
                        "nguyen_gia": 200_000_000, "so_thang_kh": 36}, "test")
        db.commit()
        a = db.execute(select(FixedAsset).where(
            FixedAsset.code == "TSCD1-NAP")).scalars().first()
        assert a is not None, "không nạp được dòng hợp lệ"
        assert a.asset_account == "2112", (
            "đường nạp Excel ra " + repr(a.asset_account) + " — rơi vào mặc định `211` thì bằng "
            "không nắn, đúng lỗ Đợt CPTT-2 đã bịt cho TK chi phí")

        # KHÔNG thẻ nào rơi vào tài khoản cha.
        for x in db.execute(select(FixedAsset)).scalars():
            assert x.asset_account not in cha, (
                "thẻ " + x.code + " mang tài khoản cha " + x.asset_account)

        # Và đợt này KHÔNG ghi sổ: tạo thẻ không đẻ ra một dòng sổ nào.
        assert abs(_du_112() - truoc) < 1, "tạo thẻ tài sản mà sổ đổi — đợt này không được ghi sổ"
