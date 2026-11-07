# -*- coding: utf-8 -*-
"""Đợt TKC-5 08/11/2026 — NHỊP 2c: HOA HỒNG, KHUYẾN MÃI, CHI PHÍ TRẢ TRƯỚC.

Đợt TKC-3 (PR #720) dựng bảng khai chung và nắn ba đường; Đợt TKC-4 (PR #723) nắn bốn đường nữa.
Đợt này nắn ba đường còn lại trong nhóm «suy ra được từ dữ liệu», qua CÙNG bảng khai ấy:

  doanh thu hoa hồng khách sạn / nhà hàng (511) · voucher VTD Rewards (641) · CCDC & chi phí
  trả trước (242)

CHỖ KHÁC HẲN BA ĐỢT TRƯỚC: `242` đã có SẴN dữ liệu mang tài khoản cha. Các khoản CCDC nhập
trước đợt này đang giữ `asset_account = "242"` trên bản ghi, nên nắn ở chỗ KHAI thôi là không
đủ — bút toán phân bổ của chúng vẫn ghi vào cha. Đợt này nắn ở chỗ GHI SỔ và KHÔNG sửa lùi một
bản ghi nào của người nhập (Chủ tịch chốt 02/11/2026: để nguyên số cũ).

BỐN LUẬT:
  1. Năm khóa mới nằm trong BẢNG CŨ, không mở bảng thứ hai, và không khóa nào trỏ vào cha.
  2. `242` suy theo SỐ KỲ, và khoản đã khai tay thì GIỮ NGUYÊN.
  3. Khoản CŨ mang `242` vẫn ghi sổ vào tài khoản con — mà bản ghi KHÔNG bị sửa lùi.
  4. Hai đường nhập CCDC (tay và hàng loạt) cùng ra tài khoản con; hoa hồng và khuyến mãi đã nắn.
"""
import inspect
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_tkc5.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_tkc5.db"):
    os.remove("test_tkc5.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOI = ("hoa_hong_khach_san", "hoa_hong_nha_hang", "khuyen_mai_rewards",
       "ccdc_ngan_han", "ccdc_dai_han")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _khong_cm(x) -> str:
    """Mã đã BỎ chú thích `#` — bẫy đã mất hai lần (Đợt TZ-1, Đợt CPTT-1)."""
    src = x if isinstance(x, str) else inspect.getsource(x)
    return "\n".join(d.split("#")[0] for d in src.split("\n"))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tkc5_1_nam_khoa_moi_trong_BANG_CU_va_khong_khoa_nao_vao_CHA():
    """Thêm vào bảng cũ, không mở bảng thứ hai — và hỏi DANH MỤC THẬT, không đoán theo độ dài mã."""
    from app.services import rules as R
    from app.services import tk_chi_tiet as TK

    assert TK.__dict__["KHOA"] and all(k in TK.KHOA for k in MOI), (
        "chưa khai: " + repr([k for k in MOI if k not in TK.KHOA]))
    assert inspect.getsource(TK).count("KHOA: dict") == 1, "có bảng khai thứ hai"

    co = {k: v for k, v, *_ in R.DEFAULT_PARAMS}
    with _db() as db:
        xau = []
        for khoa in MOI:
            mac_dinh = TK.KHOA[khoa][0]
            assert TK.KEY(khoa) in co, "khóa `" + khoa + "` không có dòng tham số"
            assert co[TK.KEY(khoa)] == mac_dinh, "hai nguồn đã lệch ở `" + khoa + "`"
            loi = TK.kiem(db, mac_dinh)
            if loi:
                xau.append(khoa + " = " + mac_dinh + " → " + loi)
        assert not xau, "khóa khai sai:\n  " + "\n  ".join(xau)

        # ── VÀ MỘT LUẬT CHO CẢ BẢNG, không chỉ năm khóa của đợt này.
        #
        # Khóa nào trỏ vào `154` / `5113` / `632` thì bút toán của nó BẮT BUỘC mang mã công
        # trình, không thì `post_entry` từ chối. Khóa như thế chỉ an toàn khi chỗ ghi sổ luôn có
        # chuyến, hoặc nghiệp vụ nằm trong danh sách miễn — và điều đó phải được KHAI RA ở
        # `CAN_CONG_TRINH`, không phải nhớ trong đầu ai.
        #
        # Đây là luật sinh ra TỪ MỘT LỖI THẬT: Đợt TKC-4 cho hóa đơn không gắn chuyến ghi vào
        # `51136` và hóa đơn ấy không phát hành được. Luật của TKC-4 chỉ đo CHỌN tài khoản nào.
        from app.services.accounting import NEED_PROJECT
        quen = [k for k, (md, _) in TK.KHOA.items()
                if md.startswith(NEED_PROJECT) and k not in TK.CAN_CONG_TRINH]
        assert not quen, (
            "khóa trỏ vào tài khoản BẮT BUỘC mã công trình mà chưa khai lý do ở "
            "`CAN_CONG_TRINH`: " + repr(quen))
        thua = [k for k in TK.CAN_CONG_TRINH
                if k in TK.KHOA and not TK.KHOA[k][0].startswith(NEED_PROJECT)]
        assert not thua, (
            "khai thừa ở `CAN_CONG_TRINH` — các khóa này không còn trỏ vào tài khoản bắt buộc "
            "mã công trình, để lại là bảng nói một thứ không còn đúng: " + repr(thua))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tkc5_2_242_suy_theo_SO_KY_va_khoan_khai_tay_thi_GIU_NGUYEN():
    """Hai điều, và điều thứ hai mới là điều dễ mất.

    Một hàm chỉ biết suy ra sẽ ĐÈ lên lựa chọn của người nhập: Kế toán trưởng đặt tay `2422`
    cho một khoản 10 kỳ (có lý do riêng), lưu xong mở lại thấy `2421` — và không ai hiểu vì sao.
    """
    from app.services import tk_chi_tiet as TK
    with _db() as db:
        assert TK.cho_phan_bo(db, 1) == "2421" and TK.cho_phan_bo(db, 12) == "2421", (
            "từ 12 kỳ trở xuống phải là NGẮN hạn")
        assert TK.cho_phan_bo(db, 13) == "2422" and TK.cho_phan_bo(db, 36) == "2422", (
            "trên 12 kỳ phải là DÀI hạn")
        # Đúng mốc 12 là ngắn hạn, 13 mới là dài hạn — đo cả hai bên mốc.
        assert TK.cho_phan_bo(db, 12) != TK.cho_phan_bo(db, 13)

        # GIỮ NGUYÊN tài khoản chi tiết người nhập đã khai, kể cả khi nó "trái" với số kỳ.
        assert TK.cho_phan_bo_cua(db, "2422", 6) == "2422", (
            "đè lên lựa chọn của người nhập — ô `asset_account` của cửa nhập thành vô nghĩa")
        assert TK.cho_phan_bo_cua(db, "2421", 36) == "2421"
        # Nhưng tài khoản CHA thì nắn, và để trống cũng nắn.
        assert TK.cho_phan_bo_cua(db, "242", 6) == "2421"
        assert TK.cho_phan_bo_cua(db, "242", 36) == "2422"
        assert TK.cho_phan_bo_cua(db, "", 6) == "2421"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tkc5_3_khoan_CU_mang_242_van_ghi_so_vao_con_ma_KHONG_bi_sua_lui():
    """Chỗ khác hẳn ba đợt trước: ở đây ĐÃ CÓ dữ liệu mang tài khoản cha.

    Nắn ở chỗ KHAI thôi thì các khoản nhập trước đợt này vẫn phân bổ vào `242` mãi mãi. Nắn
    bằng cách đi sửa bản ghi của người nhập thì vi phạm quyết định 02/11/2026 (để nguyên số cũ)
    và để lại một thay đổi không ai rà lại được. Nên nắn ở chỗ GHI SỔ — và luật này đo CẢ HAI
    vế: bút toán ra tài khoản con, VÀ bản ghi vẫn còn nguyên `242`.
    """
    from sqlalchemy import select
    from app.models.assets import PrepaidExpense
    from app.services import assets as AS
    with _db() as db:
        p = PrepaidExpense(code="TKC5-CU", name="Khoản nhập trước Đợt TKC-5", kind="ccdc",
                           asset_account="242", expense_account="6423",
                           start_date=date(2026, 1, 1), amount=24_000_000, months=24,
                           status="dang_pb", source="vtos", created_by="test")
        db.add(p)
        db.flush()

        tab = AS.allocation_table(db, "2026-03")
        dong = next((r for r in tab["rows"] if r["code"] == "TKC5-CU"), None)
        assert dong is not None, "không thấy khoản phép thử trong bảng phân bổ"
        assert dong["asset_account"] == "242", "bảng phân bổ đã đọc ra một tài khoản khác bản ghi"

        # Vế 1: chỗ ghi sổ nắn xuống con — `24` kỳ nên là DÀI hạn.
        from app.services import tk_chi_tiet as TK
        assert TK.cho_phan_bo_cua(db, dong["asset_account"], dong["months"]) == "2422", (
            "khoản 24 kỳ mang `242` phải ghi sổ vào `2422`")

        # Vế 2: bản ghi KHÔNG bị sửa lùi.
        db.refresh(p)
        assert p.asset_account == "242", (
            "bản vá đã tự sửa dữ liệu người nhập — Chủ tịch chốt 02/11/2026 để nguyên số cũ")

    # Và chỗ ghi sổ phải THẬT SỰ gọi hàm ấy, không chỉ có hàm nằm đó.
    ma = _khong_cm(AS.post_allocation)
    assert "TKCT.cho_phan_bo_cua(db, r[\"asset_account\"], r[\"months\"])" in ma, (
        "`post_allocation` không nắn tài khoản nguồn — khoản cũ vẫn phân bổ vào `242`")
    assert 'k = (r["expense_account"], src,' in ma, "gộp vẫn dùng tài khoản chưa nắn"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_tkc5_4_hai_duong_nhap_CCDC_cung_ra_con_va_hoa_hong_khuyen_mai_da_nan():
    """Một đường nhập nắn còn đường kia không là đúng lỗ Đợt CPTT-1 đã để lại và CPTT-2 phải bịt.

    `create_prepaid` (nhập tay) và `_cc_nap` (nạp Excel) tạo bản ghi ở HAI CHỖ KHÁC NHAU — đường
    Excel không đi qua `create_prepaid`. Nên phải đo cả hai, bằng BẢN GHI tạo ra.
    """
    from sqlalchemy import select
    from app.models.assets import PrepaidExpense
    from app.models.core import User
    from app.services import assets as AS
    from app.services import intake_phong_ban_2 as IN

    with _db() as db:
        u = db.execute(select(User)).scalars().first()

        # ── đường NHẬP TAY: bỏ trống TK chờ phân bổ → suy theo số kỳ (18 kỳ → dài hạn).
        a = AS.create_prepaid(db, u, {"code": "TKC5-TAY", "name": "Nhập tay", "kind": "ccdc",
                                      "expense_account": "6423", "start_date": date(2026, 2, 1),
                                      "amount": 18_000_000, "months": 18})
        db.flush()
        assert a.asset_account == "2422", (
            "cửa nhập tay ra " + repr(a.asset_account) + " — 18 kỳ phải là dài hạn")

        # ── và ĐẶT TAY thì giữ nguyên.
        b = AS.create_prepaid(db, u, {"code": "TKC5-TAY2", "name": "Nhập tay đặt tay", "kind": "ccdc",
                                      "expense_account": "6423", "asset_account": "2422",
                                      "start_date": date(2026, 2, 1), "amount": 6_000_000, "months": 6})
        db.flush()
        assert b.asset_account == "2422", "đè lên lựa chọn của người nhập"

        # ── đường NẠP EXCEL: cùng một luật, và nó KHÔNG đi qua `create_prepaid`.
        IN._cc_nap(db, {"ma_ccdc": "TKC5-NAP", "ten": "Nạp hàng loạt", "loai": "ccdc",
                        "bo_phan": "doi_xe", "tk_chi_phi": "6423", "ma_cong_trinh": "",
                        "ngay_bat_dau_pb": "01/02/2026", "gia_tri": 24_000_000,
                        "so_ky_pb": 24}, "test")
        db.flush()
        c = db.execute(select(PrepaidExpense).where(
            PrepaidExpense.code == "TKC5-NAP")).scalars().first()
        assert c is not None, "không nạp được dòng hợp lệ"
        assert c.asset_account == "2422", (
            "đường nạp Excel ra " + repr(c.asset_account) + " — rơi vào mặc định `242` của mô "
            "hình thì bằng không nắn, đúng lỗ Đợt CPTT-2 đã bịt cho TK chi phí")

        # ── hoa hồng và khuyến mãi: không còn số hiệu cha, và có đọc bảng khai.
        from app.services import dat_ban as DB2
        from app.services import don_ks_vtd as KS
        from app.services import tk_chi_tiet as TK
        # `5118` chứ không phải `5113x`: mọi tài khoản dưới `5113` bắt buộc có mã công trình
        # (`accounting.NEED_PROJECT`), mà đơn khách sạn và đơn đặt bàn không thuộc chuyến nào.
        from app.services.accounting import NEED_PROJECT
        for khoa in ("hoa_hong_khach_san", "hoa_hong_nha_hang", "hd_doanh_thu_khong_tour"):
            tk = TK.chon(db, khoa)
            assert not tk.startswith(NEED_PROJECT), (
                khoa + " ra `" + tk + "` — tài khoản này BẮT BUỘC mã công trình, mà doanh thu "
                "không gắn chuyến thì không có mã nào để ghi; bút toán sẽ bị từ chối")
        assert TK.chon(db, "khuyen_mai_rewards") == "6418"

    # Đo trên mã đã bỏ chú thích, và đo HAI CHIỀU. Phép đo ngược 08/11/2026 bắt được bản đầu
    # chỉ tìm chuỗi `khuyen_mai_rewards` — mà chuỗi ấy CŨNG là tên nghiệp vụ của chính bút toán
    # (`f"{d.ma}:km", "khuyen_mai_rewards"`), nên gõ cứng lại `641` vẫn xanh. Nay đòi đúng lời
    # gọi `TKCT.chon(...)`, và đòi KHÔNG còn một số hiệu cha nào trong vế tài khoản.
    for ten, mo in (("đặt bàn", DB2), ("đơn khách sạn", KS)):
        ma = _khong_cm(inspect.getsource(mo))
        assert 'TK_KM = "641"' not in ma, ten + " còn hằng số `641`"
        assert 'TK_DT_HH = "511"' not in ma, ten + " còn hằng số `511`"
        assert '"account": TK_KM' not in ma and '"account": TK_DT_HH' not in ma, (
            ten + " còn ghi vào một hằng số cấp cha")
        for x in ("511", "641", "3331", "642", "632"):
            assert ('{"account": "' + x + '"') not in ma, ten + " còn gõ cứng `" + x + "`"
        assert 'TKCT.chon(db, "khuyen_mai_rewards")' in ma, (
            ten + " không đọc bảng khai cho voucher")
        assert 'TKCT.chon(db, "hoa_hong_' in ma, (
            ten + " không đọc bảng khai cho doanh thu hoa hồng")
