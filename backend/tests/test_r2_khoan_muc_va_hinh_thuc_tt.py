# -*- coding: utf-8 -*-
"""Đợt R2 (15/10/2026) — KHOẢN MỤC CHI PHÍ và HÌNH THỨC THANH TOÁN TRONG KHÓA.

HAI CHỖ HỎNG, ĐO ĐƯỢC TRƯỚC KHI VIẾT MỘT DÒNG MÃ NÀO

 1. ĐỌC `hach_toan.MAC_DINH` ngày 15/10/2026: mọi quy tắc tiền vào và tiền ra đều gõ cứng `1121`.
    KHÔNG CÓ MỘT ĐƯỜNG NÀO RA 1111. Một phiếu thu tiền mặt tại quầy chạy qua bộ quy tắc sẽ ghi
    vào TÀI KHOẢN NGÂN HÀNG. Sổ vẫn cân, tổng tiền vẫn đúng — chỉ có quỹ tiền mặt thiếu và số dư
    ngân hàng thừa đúng một khoản bằng nhau, và cái sai ấy chỉ lộ ra lúc đối chiếu sao kê.

 2. ĐỌC MISA AMIS của Vietourist ngày 15/10/2026: danh mục **Khoản mục chi phí TRỐNG HOÀN TOÀN**,
    nên cả một họ báo cáo "… theo khoản mục chi phí" của họ chạy ra bảng rỗng — không báo lỗi, chỉ
    không có dòng nào. VTOS đã có CHỖ GHI (`JournalLine.item_code`) nhưng không có danh mục để mã
    ấy trỏ vào, và không có luật nào nói dòng nào bắt buộc phải có nó.

TỆP NÀY CANH TÁM ĐIỀU

 1. Mười dòng khuôn nạp được, và nạp lại KHÔNG đè lên dòng Kế toán đã sửa.
 2. Mã khoản mục KHÔNG đổi được — chỉ ngừng dùng rồi thêm mã mới.
 3. **CỤ THỂ THẮNG CHUNG CHUNG** — và thắng vì một LUẬT, không vì hai con số ưu tiên tình cờ.
 4. Hình thức tiền mặt không được ghi vào 112x, và hình thức qua ngân hàng (kể cả Séc tiền mặt)
    không được ghi vào 111x.
 5. Bút toán tiền mặt ghi ĐÚNG 1111 — điều trước đợt này không đường nào làm được.
 6. Quy tắc `can_khoan_muc` mà thiếu mã khoản mục thì CHẶN, không tự điền "KM_KHAC".
 7. Mã khoản mục chảy xuống tới `JournalLine.item_code`, không rơi giữa đường.
 8. Bối cảnh sao kê ngân hàng KHÔNG bao giờ khớp quy tắc tiền mặt.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_r2.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                                        # noqa: E402
from sqlalchemy import create_engine, select                         # noqa: E402
from sqlalchemy.orm import sessionmaker                              # noqa: E402

from app.db.session import Base                                      # noqa: E402
from app.models.hach_toan import (QuyTacHachToan, HINH_THUC_TT,      # noqa: E402
                                  HTTT_QUA_NGAN_HANG, HTTT_QUA_TIEN_MAT,
                                  TK_TIEN_MAT, TK_TIEN_GUI)
from app.models.khoan_muc_chi_phi import KhoanMucChiPhi              # noqa: E402
from app.services import accounting as ACC                           # noqa: E402
from app.services import hach_toan as HT                             # noqa: E402
from app.services import khoan_muc_chi_phi as KM                     # noqa: E402


def _rieng():
    """MỘT CSDL RIÊNG TRONG BỘ NHỚ — cửa hẹp của CI chạy nhiều tệp trong MỘT tiến trình, nên ghi
    vào CSDL dùng chung thì làm lệch số của tệp khác (test_misa đối chiếu tới từng đồng)."""
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    HT.nap_mac_dinh(db)
    KM.nap_mac_dinh(db)
    return db


def _quy_tac(db, ma):
    return db.execute(select(QuyTacHachToan).where(QuyTacHachToan.ma == ma)).scalar_one()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1–2. DANH MỤC
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2_1_nap_lai_khong_de_len_dong_da_sua():
    db = _rieng()
    ds = KM.danh_sach(db)
    # ĐỢT R3a 16/10/2026 — đếm TỪ NGUỒN thay vì ghim con số 10. Việc phép thử này thật sự
    # canh là "nạp lại không thêm dòng nào", và điều ấy vẫn nguyên ở `them == 0` bên dưới.
    assert len(ds) == len(KM.MAC_DINH), f"Danh mục nạp thiếu/thừa: {len(ds)} vs {len(KM.MAC_DINH)}"
    assert {d["ma"] for d in ds} >= {"KM_LAND", "KM_VEMB", "KM_KS", "KM_HDV", KM.KM_KHAC}

    xe = next(d for d in ds if d["ma"] == "KM_XE")
    KM.sua(db, xe["id"], {"ten": "Xe (đội xe nhà + thuê ngoài)"})
    them = KM.nap_mac_dinh(db)       # chạy lại, y như một lần khởi động máy chủ
    assert them == 0, "Nạp lại không được thêm dòng nào"
    lai = next(d for d in KM.danh_sach(db) if d["ma"] == "KM_XE")
    assert lai["ten"] == "Xe (đội xe nhà + thuê ngoài)", (
        "Nạp lại ĐÃ ĐÈ lên tên Kế toán sửa. Bảng không còn là của họ.")


def test_r2_2_ma_khong_doi_duoc_chi_ngung_dung():
    db = _rieng()
    xe = next(d for d in KM.danh_sach(db) if d["ma"] == "KM_XE")
    KM.sua(db, xe["id"], {"ma": "KM_OTO", "ten": "Ô tô"})     # `ma` phải bị BỎ QUA
    k = db.get(KhoanMucChiPhi, xe["id"])
    assert k.ma == "KM_XE", (
        "Mã đã đổi. Mọi dòng sổ đã ghi mang item_code='KM_XE' lập tức trỏ vào một mã không còn "
        "tồn tại, và chúng biến mất khỏi báo cáo theo khoản mục mà không ai thấy gì sai.")
    KM.sua(db, xe["id"], {"dung": False})
    assert "KM_XE" not in {d["ma"] for d in KM.danh_sach(db)}
    assert "KM_XE" in {d["ma"] for d in KM.danh_sach(db, ca_ngung=True)}, (
        "Ngừng dùng phải GIỮ dòng lại — bút toán cũ còn trỏ vào nó.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3–5. HÌNH THỨC THANH TOÁN TRONG KHÓA
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2_3_cu_the_thang_chung_chung_va_thang_vi_mot_luat():
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA NỬA SAU TỆP NÀY.

    Hạ `uu_tien` của dòng tiền mặt XUỐNG DƯỚI dòng ngân hàng rồi vẫn phải thắng. Nếu nó thắng chỉ
    vì hai con số ưu tiên hơn kém nhau thì luật sẽ hỏng vào ngày có người chỉnh thứ tự ưu tiên vì
    một lý do khác hẳn — và hỏng im lặng, vì phiếu thu tiền mặt vẫn ghi sổ, chỉ ghi vào 1121.
    """
    db = _rieng()
    tm = _quy_tac(db, "THU_KHACH_TM")
    nh = _quy_tac(db, "THU_KHACH")
    tm.uu_tien = 900                 # tệ hơn hẳn dòng ngân hàng (10)
    db.commit()
    assert nh.uu_tien < tm.uu_tien

    q = HT.chon(db, "tien_vao", {"khop_don": True, "hinh_thuc_tt": "tien_mat"})
    assert q is not None and q.ma == "THU_KHACH_TM", (
        f"Bối cảnh nói rõ TIỀN MẶT mà chọn {q.ma if q else None}. Luật 'cụ thể thắng chung chung' "
        "đang dựa vào thứ tự ưu tiên chứ không phải vào cột hình thức thanh toán.")

    # Và chiều ngược lại: không nói gì thì vẫn là dòng cũ — không một đường gọi nào đang chạy bị đổi.
    q2 = HT.chon(db, "tien_vao", {"khop_don": True})
    assert q2 is not None and q2.ma == "THU_KHACH", (
        f"Bối cảnh KHÔNG khai hình thức mà chọn {q2.ma if q2 else None}. Đợt này đã làm đổi hành "
        "vi của những đường gọi cũ — đúng điều nó hứa sẽ không làm.")


def test_r2_4_hinh_thuc_va_tai_khoan_tien_phai_khop_nhau():
    db = _rieng()
    chung = dict(ten="Thử", nguon="tien_ra", dieu_kien={}, effective_from=date(2026, 1, 1))

    class _U:
        username, role = "ketoan", "ketoan"

    with pytest.raises(ValueError, match="TIỀN MẶT"):
        HT.de_xuat(db, _U(), dict(chung, ma="SAI_TM", tk_no="331", tk_co="1121",
                                  hinh_thuc_tt="tien_mat"))
    with pytest.raises(ValueError, match="ngân hàng"):
        HT.de_xuat(db, _U(), dict(chung, ma="SAI_UNC", tk_no="331", tk_co="1111",
                                  hinh_thuc_tt="unc"))
    # Séc tiền mặt nằm bên NGÂN HÀNG — séc lĩnh tiền mặt vẫn rút trên tài khoản ngân hàng.
    assert "sec_tien_mat" in HTTT_QUA_NGAN_HANG and "sec_tien_mat" not in HTTT_QUA_TIEN_MAT
    with pytest.raises(ValueError, match="ngân hàng"):
        HT.de_xuat(db, _U(), dict(chung, ma="SAI_SEC", tk_no="331", tk_co="1111",
                                  hinh_thuc_tt="sec_tien_mat"))
    with pytest.raises(ValueError, match="không hợp lệ"):
        HT.de_xuat(db, _U(), dict(chung, ma="SAI_GO", tk_no="331", tk_co="1111",
                                  hinh_thuc_tt="tien_mat "))     # thừa một dấu cách


def test_r2_5_moi_quy_tac_trong_bang_tu_khop_voi_hinh_thuc_cua_no():
    """Canh CẢ BẢNG, không chỉ sáu dòng vừa thêm — kể cả dòng Kế toán thêm sau này."""
    db = _rieng()
    for q in db.execute(select(QuyTacHachToan)).scalars():
        assert q.hinh_thuc_tt in HINH_THUC_TT, f"{q.ma}: hình thức '{q.hinh_thuc_tt}' không khai"
        cham = (q.tk_no, q.tk_co)
        if q.hinh_thuc_tt in HTTT_QUA_TIEN_MAT:
            assert not any(t.startswith(TK_TIEN_GUI) for t in cham), f"{q.ma} tiền mặt mà ghi 112x"
        if q.hinh_thuc_tt in HTTT_QUA_NGAN_HANG:
            assert not any(t.startswith(TK_TIEN_MAT) for t in cham), f"{q.ma} ngân hàng mà ghi 111x"
    # Và lỗ thủng đã bịt: PHẢI có ít nhất một đường ra 1111.
    co_tien_mat = [q.ma for q in db.execute(select(QuyTacHachToan)).scalars()
                   if any(t.startswith(TK_TIEN_MAT) for t in (q.tk_no, q.tk_co))]
    assert len(co_tien_mat) >= 6, (
        f"Chỉ có {len(co_tien_mat)} quy tắc chạm tài khoản tiền mặt. Trước Đợt R2 con số này là "
        "KHÔNG, và đó chính là lỗ thủng đợt này bịt.")


def test_r2_6_but_toan_tien_mat_ghi_dung_1111():
    db = _rieng()
    q = HT.chon(db, "tien_vao", {"khop_don": True, "hinh_thuc_tt": "tien_mat"})
    bt = HT.dung_but_toan(q, 5_000_000, {"ma": "HT001", "khach": "Khách lẻ", "ma_khach": "KH01",
                                         "hinh_thuc_tt": "tien_mat"})
    tk_no = [d["account"] for d in bt["lines"] if d.get("debit")]
    assert tk_no == ["1111"], f"Thu tiền mặt mà ghi Nợ {tk_no} — phải là quỹ tiền mặt 1111."


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6–8. CHIỀU KHOẢN MỤC CHI PHÍ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2_7_thieu_khoan_muc_thi_chan_chu_khong_tu_dien():
    db = _rieng()
    q = _quy_tac(db, "MUA_CO_HD")
    assert q.can_khoan_muc is True, "MUA_CO_HD phải bắt buộc mã khoản mục"
    with pytest.raises(ValueError, match="khoản mục chi phí"):
        HT.dung_but_toan(q, 10_000_000, {"ma": "HT001", "ncc": "Land ABC", "co_hoa_don": True})

    # Và KHÔNG được lặng lẽ điền "KM_KHAC": điền hộ thì bảng phân tích vẫn ra đủ dòng mà rỗng nghĩa.
    bt = HT.dung_but_toan(q, 10_000_000, {"ma": "HT001", "ncc": "Land ABC", "co_hoa_don": True,
                                          "khoan_muc": "KM_LAND"})
    assert all(d.get("item_code") == "KM_LAND" for d in bt["lines"]), (
        "Mã khoản mục rơi mất giữa đường — `JournalLine.item_code` là chỗ mọi báo cáo theo khoản "
        "mục đọc, nên rơi ở đây nghĩa là chiều phân tích không bao giờ có dữ liệu.")


def test_r2_8_bon_duong_thanh_gia_von_deu_bat_buoc_khoan_muc():
    db = _rieng()
    for ma in HT.CAN_KHOAN_MUC:
        assert _quy_tac(db, ma).can_khoan_muc is True, f"{ma} không bật chiều khoản mục"
    # Quy tắc KHÔNG thuộc bốn đường ấy thì không được đòi khoản mục — đòi khắp nơi là đòi ở đâu
    # cũng gõ cho xong, và một chiều phân tích gõ cho xong thì vô dụng y như chiều rỗng.
    assert _quy_tac(db, "TRA_LUONG").can_khoan_muc is False
    assert _quy_tac(db, "KC_LAI").can_khoan_muc is False


def test_r2_9_sao_ke_ngan_hang_khong_bao_gio_khop_quy_tac_tien_mat():
    """Bối cảnh dựng từ một dòng sao kê là CHUYỂN KHOẢN — biết chắc, không đoán."""
    db = _rieng()
    from app.services import ket_so as KS
    import inspect
    nguon = inspect.getsource(KS._boi_canh)
    assert '"hinh_thuc_tt": "chuyen_khoan"' in nguon, (
        "`_boi_canh` không khai hình thức thanh toán. Khi ấy quy tắc tiền mặt vẫn THUA quy tắc "
        "ngân hàng — nhưng vì một lẽ tình cờ, không vì một luật, và lẽ tình cờ ấy đổi bất cứ lúc nào.")
    q = HT.chon(db, "tien_vao", {"khop_don": True, "hinh_thuc_tt": "chuyen_khoan"})
    assert q.ma == "THU_KHACH" and q.tk_no == "1121"
