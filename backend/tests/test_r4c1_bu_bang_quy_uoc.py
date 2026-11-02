# -*- coding: utf-8 -*-
"""ĐỢT R4c-1 02/11/2026 — BÙ BẢNG QUY ƯỚC: BỐN TÀI KHOẢN VÀ HAI Ô CỦA CỬA TRÌNH. NĂM LUẬT.

Chủ tịch chốt 02/11/2026 mười quy tắc hạch toán bù (42 → 52). Đo trước khi soạn thì ra hai chỗ
chặn, và cả hai KHÔNG phải quy tắc — chúng là cấu trúc:

1. BỐN TÀI KHOẢN CHƯA CÓ TRONG DANH MỤC. `de_xuat()` có dòng
   `if tk and not db.get(Account, tk): raise ValueError(f"Tài khoản {tk} không có trong danh mục")`.
   Đo trên main 02/11/2026: tìm "5211" trong CẢ KHO → **0 kết quả**. Nên ba quy tắc giảm trừ
   doanh thu Chủ tịch vừa chốt sẽ bị cửa trình TỪ CHỐI. (`5118` của PHI_HUY thì CÓ.)

2. CỬA TRÌNH KHÔNG TRUYỀN ĐƯỢC HAI Ô, và hậu quả nặng hơn "thiếu một ô".
   `QuyTacIn` trong `api/v1/hach_toan.py` không khai `hinh_thuc_tt` và `can_khoan_muc`, nhưng
   `HT.de_xuat()` ĐỌC cả hai qua `data.get(...)`. Nên qua cửa, hai ô ấy LUÔN rỗng/False, và:

     · không trình được một quy tắc tiền mặt nào — chỉ thêm được bằng cách sửa mã;
     · BA PHÉP KIỂM hình thức thanh toán trong `de_xuat` KHÔNG BAO GIỜ CHẠY TỚI. Hai trong ba
       (`HTTT_QUA_TIEN_MAT` và `HTTT_QUA_NGAN_HANG`) chỉ đúng khi ô ấy khác rỗng, nên qua cửa
       chúng là MÃ CHẾT. Đợt R2 viết chúng để chặn đúng loại sai "quỹ tiền mặt và số dư ngân
       hàng cùng lệch một khoản bằng nhau"; suốt từ 15/10/2026 chúng chưa chặn được gì qua API.
     · không trình được quy tắc BẮT BUỘC mã khoản mục, nên cổng khoản mục của Đợt R2 cũng không
       đặt được cho một quy tắc mới.

ĐỢT NÀY KHÔNG THÊM MỘT DÒNG QUY TẮC NÀO — luật 5 soi lại điều đó. Mười dòng Chủ tịch chốt là DỮ
LIỆU CHÍNH SÁCH, phải đi qua cửa trình và hai chữ ký; `nap_mac_dinh()` ghi
`signed_chutich=True, signed_tgd=True`, nên thêm vào `MAC_DINH` là tự ký cả hai chữ ký.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENV", "dev")

from datetime import date  # noqa: E402

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.session import Base  # noqa: E402
from app.models.accounting import Account  # noqa: E402
from app.models.core import User  # noqa: E402
from app.models.hach_toan import (HINH_THUC_TT, HTTT_QUA_NGAN_HANG,  # noqa: E402
                                  HTTT_QUA_TIEN_MAT, QuyTacHachToan)
from app.services import accounting as ACC  # noqa: E402
from app.services import hach_toan as HT  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Bốn tài khoản của quyết định 02/11/2026: Chủ tịch chọn CẢ BA cách giảm trừ, nên cần cả ba tài
# khoản con, cộng tài khoản cha.
BON_TK = {
    "521": ("Các khoản giảm trừ doanh thu", "DT", "", 1, False),
    "5211": ("Chiết khấu thương mại", "DT", "521", 2, True),
    "5212": ("Hàng bán bị trả lại", "DT", "521", 2, True),
    "5213": ("Giảm giá hàng bán", "DT", "521", 2, True),
}


def _rieng():
    """CSDL riêng trong bộ nhớ — khuôn của `test_r6b_so_du_dau_ky.py`."""
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    u = User(username="phepthu.r4c1", full_name="Phép thử R4c-1", role="ketoan",
             password_hash="x")
    db.add(u)
    db.flush()
    db.info["u"] = u
    return db


def _ma(duong: str) -> str:
    with open(os.path.join(GOC, *duong.split("/")), encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 1 — BỐN TÀI KHOẢN CÓ TRONG DANH MỤC, ĐÚNG CHA CON
# ─────────────────────────────────────────────────────────────────────────────

def test_r4c1_1_bon_tai_khoan_co_trong_danh_muc():
    """Soi qua `seed_accounts` chứ không đọc tệp JSON: bộ gieo có nhánh đọc danh mục MISA và
    nhánh dự phòng `CHART`, và phép thử phải đúng với CÁI MÁY THẬT CHẠY, không với một tệp.

    `is_detail` suy ra từ việc có ai nhận mình làm cha — nên 521 KHÔNG chi tiết (không ghi bút
    toán thẳng vào nó) còn ba con thì có. Khai sai chỗ này thì cửa nạp số dư đầu kỳ nhận một
    tài khoản tổng hợp, và số dư của nó cộng hai lần.
    """
    db = _rieng()
    for ma, (ten, kind, cha, cap, chi_tiet) in BON_TK.items():
        a = db.get(Account, ma)
        assert a is not None, f"danh muc KHONG co tai khoan {ma} — ba quy tac giam tru doanh thu " \
                              f"cua quyet dinh 02/11/2026 se bi cua trinh TU CHOI"
        assert a.kind == kind, f"TK {ma} khai loai {a.kind}, can {kind}"
        assert (a.parent or "") == cha, f"TK {ma} khai cha '{a.parent}', can '{cha}'"
        assert a.level == cap, f"TK {ma} khai cap {a.level}, can {cap}"
        assert bool(a.is_detail) is chi_tiet, (
            f"TK {ma}: is_detail={a.is_detail}, can {chi_tiet} — 521 la tai khoan TONG HOP")
    # Và 5118 của PHI_HUY phải có sẵn từ trước — đợt này KHÔNG thêm nó.
    assert db.get(Account, "5118") is not None, "danh muc mat 5118"


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 2 — CỬA TRÌNH NHẬN ĐƯỢC HAI Ô
# ─────────────────────────────────────────────────────────────────────────────

def test_r4c1_2_cua_trinh_nhan_duoc_hai_o():
    """`QuyTacIn` phải khai cả hai ô, và `model_dump()` phải MANG chúng sang `de_xuat`.

    Đo trên CHÍNH mô hình Pydantic của cửa, không đọc chuỗi trong tệp: một ô khai đúng tên mà
    sai kiểu vẫn làm `data.get(...)` trả về thứ `de_xuat` không dùng được, và đọc chuỗi thì
    không thấy.
    """
    from app.api.v1.hach_toan import QuyTacIn
    truong = set(QuyTacIn.model_fields)
    for o in ("hinh_thuc_tt", "can_khoan_muc"):
        assert o in truong, f"QuyTacIn khong khai o '{o}' — cua trinh khong truyen duoc"
    m = QuyTacIn(ma="X", ten="x", nguon="tien_ra", tk_no="1111", tk_co="1111",
                 effective_from=date(2026, 11, 1),
                 hinh_thuc_tt="tien_mat", can_khoan_muc=True)
    d = m.model_dump()
    assert d["hinh_thuc_tt"] == "tien_mat", d
    assert d["can_khoan_muc"] is True, d
    # Và mặc định phải GIỮ NGUYÊN hành vi cũ: rỗng / False, nên không quy tắc nào đang chạy đổi.
    m0 = QuyTacIn(ma="X", ten="x", nguon="tien_ra", tk_no="1121", tk_co="131",
                  effective_from=date(2026, 11, 1))
    assert m0.model_dump()["hinh_thuc_tt"] == ""
    assert m0.model_dump()["can_khoan_muc"] is False


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 3 — TRÌNH ĐƯỢC MỘT QUY TẮC TIỀN MẶT, VÀ BẢN GHI MANG ĐÚNG HAI Ô
# ─────────────────────────────────────────────────────────────────────────────

def test_r4c1_3_trinh_duoc_mot_quy_tac_tien_mat():
    """Đi qua `HT.de_xuat` thật, rồi đọc lại bản ghi trong bảng.

    Trước đợt này hai ô luôn rỗng qua cửa, nên một quy tắc tiền mặt trình xong sẽ nằm trong bảng
    với `hinh_thuc_tt=""` — tức là nó khớp MỌI bối cảnh, kể cả chuyển khoản. Một quy tắc ghi vào
    1111 mà khớp cả chuyển khoản là đúng loại sai Đợt R2 sinh ra để chặn.
    """
    db = _rieng()
    q = HT.de_xuat(db, db.info["u"], {
        "ma": "R4C1_THU_TM", "ten": "Phép thử: thu tiền mặt", "nguon": "tien_vao",
        "dieu_kien": {"khop_don": True}, "tk_no": "1111", "tk_co": "131",
        "effective_from": date(2026, 11, 1),
        "hinh_thuc_tt": "tien_mat", "can_khoan_muc": True,
    })
    lai = db.execute(select(QuyTacHachToan).where(QuyTacHachToan.ma == "R4C1_THU_TM")).scalars().first()
    assert lai is not None
    assert lai.hinh_thuc_tt == "tien_mat", f"ban ghi mang '{lai.hinh_thuc_tt}', mat o hinh thuc"
    assert lai.can_khoan_muc is True, "ban ghi mat o can_khoan_muc"
    # Trình KHÔNG có hiệu lực ngay: vẫn chờ hai chữ ký.
    assert lai.status == "pending", f"trinh ma da active — mat hang rao hai chu ky"
    assert lai.signed_chutich is False and lai.signed_tgd is False


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 4 — BA PHÉP KIỂM HÌNH THỨC CỦA ĐỢT R2 NAY CHẠY TỚI ĐƯỢC
# ─────────────────────────────────────────────────────────────────────────────

def test_r4c1_4_ba_phep_kiem_hinh_thuc_nay_chay_toi_duoc():
    """Đây là lý do thật của đợt này, và nó quan trọng hơn hai ô.

    `de_xuat` có ba phép kiểm hình thức. Hai trong ba chỉ đúng khi `hinh_thuc_tt` khác rỗng, mà
    qua cửa nó LUÔN rỗng — nên từ 15/10/2026 tới nay chúng là MÃ CHẾT trên đường API. Luật này
    chạy cả ba và đòi chúng chặn thật.
    """
    db = _rieng()
    u = db.info["u"]
    goc = {"ma": "R4C1_SAI", "ten": "Phép thử", "nguon": "tien_ra",
           "effective_from": date(2026, 11, 1)}

    # (a) hình thức không có trong danh sách
    with pytest.raises(ValueError) as e:
        HT.de_xuat(db, u, {**goc, "tk_no": "331", "tk_co": "1111",
                           "hinh_thuc_tt": "tien_mat_ "})
    assert "Hình thức thanh toán không hợp lệ" in str(e.value)

    # (b) khai TIỀN MẶT mà ghi vào tài khoản tiền gửi
    with pytest.raises(ValueError) as e:
        HT.de_xuat(db, u, {**goc, "tk_no": "331", "tk_co": "1121",
                           "hinh_thuc_tt": "tien_mat"})
    assert "TIỀN MẶT" in str(e.value) and "tiền gửi" in str(e.value)

    # (c) khai hình thức qua NGÂN HÀNG mà ghi vào tài khoản tiền mặt — kể cả "Séc tiền mặt",
    #     vì séc lĩnh tiền mặt vẫn rút trên tài khoản ngân hàng.
    for ht in HTTT_QUA_NGAN_HANG:
        with pytest.raises(ValueError) as e:
            HT.de_xuat(db, u, {**goc, "tk_no": "331", "tk_co": "1111", "hinh_thuc_tt": ht})
        assert "tiền mặt" in str(e.value), (ht, str(e.value))

    # Và chiều xuôi: khai đúng thì qua. Thiếu nửa này thì luật trên vẫn xanh với một cửa
    # từ chối MỌI thứ.
    for ht in HTTT_QUA_TIEN_MAT:
        q = HT.de_xuat(db, u, {**goc, "ma": f"R4C1_OK_{ht}", "tk_no": "331", "tk_co": "1111",
                               "hinh_thuc_tt": ht})
        assert q.hinh_thuc_tt == ht
    assert "" in HINH_THUC_TT, "o rong phai la mot gia tri hop le — moi quy tac cu dang dung no"


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 5 — ĐỢT NÀY KHÔNG THÊM MỘT DÒNG QUY TẮC NÀO
# ─────────────────────────────────────────────────────────────────────────────

def test_r4c1_5_khong_them_mot_dong_quy_tac_nao():
    """Mười quy tắc Chủ tịch chốt 02/11/2026 là DỮ LIỆU CHÍNH SÁCH, không phải cấu trúc.

    `nap_mac_dinh()` ghi mỗi dòng với `status="active", signed_chutich=True, signed_tgd=True`.
    Nên thêm một dòng vào `MAC_DINH` là TỰ KÝ CẢ HAI CHỮ KÝ — đúng việc mà chính tệp
    `api/v1/hach_toan.py` cấm: "không ai một mình đổi được một dòng định khoản, kể cả Kế toán
    trưởng". Mười dòng ấy phải đi qua `POST /hach-toan/quy-tac` rồi hai người ký.

    Soi bằng cách ĐẾM, không bằng cách đọc tên: thêm một dòng mang tên khác vẫn bị bắt.
    """
    assert len(HT.MAC_DINH) == 36, f"MAC_DINH doi so dong: {len(HT.MAC_DINH)}, can 36"
    assert len(HT.MAC_DINH_TIEN_MAT) == 6, (
        f"MAC_DINH_TIEN_MAT doi so dong: {len(HT.MAC_DINH_TIEN_MAT)}, can 6")
    db = _rieng()
    them = HT.nap_mac_dinh(db)
    assert them == 42, f"bo quy uoc mac dinh nap {them} dong, can dung 42"
    # Và không một quy tắc nào của quyết định 02/11 lọt vào bộ mặc định.
    ma_moi = {"HOAN_KHACH", "HOAN_KHACH_TM", "PHI_HUY", "NOP_TIEN_MAT", "RUT_TIEN_MAT",
              "BU_TRU_GTGT", "PHAN_BO_TRA_TRUOC", "MUA_TSCD",
              "GIAM_TRU_DT_CKTM", "GIAM_TRU_DT_TRA_LAI", "GIAM_TRU_DT_GIAM_GIA"}
    co = {q.ma for q in db.execute(select(QuyTacHachToan)).scalars()}
    lot = sorted(ma_moi & co)
    assert not lot, (
        "dot nay da tu ky quy tac chinh sach: " + repr(lot) +
        " — muoi dong ay phai di qua cua trinh va hai chu ky")
    # Mã nguồn cũng không được nhắc tới chúng trong bộ mặc định.
    than = "\n".join(d for d in _ma("app/services/hach_toan.py").splitlines()
                     if not d.lstrip().startswith("#"))
    bo = than.split("MAC_DINH = [", 1)[1].split("\ndef nap_mac_dinh", 1)[0]
    for m in sorted(ma_moi):
        assert f'("{m}"' not in bo, f"ma {m} da bi nhet vao bo quy uoc mac dinh"
