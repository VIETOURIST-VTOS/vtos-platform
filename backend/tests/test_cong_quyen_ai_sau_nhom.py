# -*- coding: utf-8 -*-
"""PQ-3 · Cổng quyền AI phải áp cho CẢ SÁU nhóm việc, không riêng tin cho khách.

Đo ngày 10/9/2026 trên mã đang chạy: bảng quyền AI khai sáu nhóm việc, nhưng chỉ hai nhóm thật sự
bị chặn — tin_khach đi qua duoc_tu_gui() kiểm đủ bốn điều; doc_chung_tu chỉ đọc MỨC rồi thôi; còn
vb_noi_bo, cham_diem, hoi_dap, canh_bao chạy mà không hỏi bảng. Cả sáu vẫn hiện trên màn hình
/ai-roles y như nhau, nên nhìn vào thì tưởng cả sáu đều đang được điều khiển.

Tệp này canh cổng duoc_lam(). Việc NỐI cổng vào từng chỗ gọi mô hình là VPM-6 — phép thử của việc
ấy thuộc làn Viết phần mềm, không nằm ở đây.
"""
from datetime import datetime, timedelta

import pytest

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401  – nạp AiPosition, AiPause, AiRun
from app.models.core import AiPosition, AiPause
from app.services import ai_quyen as AQ

TRONG_GIO = datetime(2026, 9, 10, 10, 0)      # 10:00, trong khung 08:00-21:00
NGOAI_GIO = datetime(2026, 9, 10, 23, 30)


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):      # bảng bị tham chiếu mà tệp model chưa nạp
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:")
    md.create_all(eng)
    with Session(eng) as s:
        yield s


def _dat(db, vai_tro, tac_vu, muc, han_muc=None):
    db.add(AiPosition(vai_tro=vai_tro, tac_vu=tac_vu, muc=muc,
                      han_muc=dict(han_muc) if han_muc is not None
                      else (dict(AQ.HAN_MUC_MAC_DINH) if muc == 3 else {})))
    db.flush()


def _tam_dung(db, ly_do="thử"):
    db.add(AiPause(id=1, tam_dung=True, ly_do=ly_do, boi="chutich", luc=datetime.now()))
    db.flush()


# ---------------------------------------------------------------------------------------------

def test_cong_ap_cho_ca_sau_nhom_viec_khong_rieng_tin_khach(db):
    """Sáu ô trên màn hình thì sáu ô phải hỏi được cổng. Ô nào không hỏi được là ô trang trí."""
    for tac_vu in AQ.COT:
        muc = 4 if tac_vu in AQ.TAC_VU_MA_XAC_DINH else 3
        _dat(db, "nv_mkt", tac_vu, muc)
        ok, ly_do = AQ.duoc_lam(db, "nv_mkt", tac_vu, TRONG_GIO)
        assert ok, f"{tac_vu} đủ điều kiện mà vẫn bị chặn: {ly_do}"


def test_ha_muc_xuong_thi_bi_chan_va_noi_ro_ly_do(db):
    """Đột biến sáu chiều: hạ từng ô xuống mức 1 rồi gọi đúng ô ấy – phải bị chặn, kèm lý do.

    Đây là phép thử đắt nhất trong tệp: nó chứng minh bảng ĐIỀU KHIỂN HÀNH VI chứ không chỉ hiển
    thị. Ô nào vẫn chạy được sau khi hạ mức là ô đó chưa nối cổng.
    """
    for tac_vu in AQ.COT:
        _dat(db, "tp_kd", tac_vu, 1)
        ok, ly_do = AQ.duoc_lam(db, "tp_kd", tac_vu, TRONG_GIO)
        assert not ok, f"{tac_vu}: hạ xuống mức 1 mà vẫn cho làm"
        assert "mức đang áp dụng là 1" in ly_do and "Quan sát" in ly_do


def test_muc_4_chi_danh_cho_viec_do_ma_xac_dinh_lam(db):
    """Việc do mô hình ngôn ngữ làm thì TRẦN là mức 3 – luôn có hạn mức và người hậu kiểm.

    Đặt mức 4 cho một việc mô hình làm là bỏ luôn khung giờ, số lượt và người hậu kiểm cùng lúc –
    ba thứ vốn là toàn bộ lý do bảng này tồn tại. Bỏ ba thứ ấy chỉ bằng một thao tác đổi một ô.
    """
    for tac_vu in AQ.TAC_VU_MO_HINH:
        _dat(db, "gd_kd", tac_vu, 4)
        ok, ly_do = AQ.duoc_lam(db, "gd_kd", tac_vu, TRONG_GIO)
        assert not ok, f"{tac_vu}: mức 4 cho việc mô hình làm mà vẫn cho qua"
        assert "trần là mức 3" in ly_do
    _dat(db, "gd_kd", "canh_bao", 4)
    assert AQ.duoc_lam(db, "gd_kd", "canh_bao", TRONG_GIO)[0]


def test_bon_phep_kiem_cu_van_nguyen_cho_moi_nhom_viec(db):
    """Bốn phép kiểm của bản cũ – mức, hạn mức, khung giờ, số lượt – nay áp cho mọi nhóm việc."""
    _dat(db, "nv_mkt", "vb_noi_bo", 3, han_muc={"khung_gio": "08:00-21:00", "so_luot_ngay": 2})
    ok, ly_do = AQ.duoc_lam(db, "nv_mkt", "vb_noi_bo", TRONG_GIO)
    assert not ok and "thiếu hạn mức" in ly_do
    assert "loai_noi_dung" in ly_do and "nguoi_hau_kiem" in ly_do

    _dat(db, "tp_dh", "cham_diem", 3)
    assert AQ.duoc_lam(db, "tp_dh", "cham_diem", TRONG_GIO)[0]
    ok, ly_do = AQ.duoc_lam(db, "tp_dh", "cham_diem", NGOAI_GIO)
    assert not ok and "ngoài khung giờ" in ly_do


def test_khung_gio_sai_dinh_dang_thi_coi_la_ngoai_gio(db):
    """Hỏng thì ĐÓNG, không mở. Một khung giờ gõ sai không được biến thành 'chạy cả ngày'."""
    _dat(db, "nv_mkt", "hoi_dap", 3, han_muc={**AQ.HAN_MUC_MAC_DINH, "khung_gio": "8h tới 21h"})
    ok, ly_do = AQ.duoc_lam(db, "nv_mkt", "hoi_dap", TRONG_GIO)
    assert not ok and "ngoài khung giờ" in ly_do


def test_tat_khan_chan_viec_mo_hinh_nhung_khong_tat_canh_bao(db):
    """Tắt khẩn dừng việc do mô hình làm. Nó KHÔNG được tắt cảnh báo do mã xác định sinh ra.

    Tắt luôn cảnh báo đúng lúc đang có sự cố là tắt đúng cái đang cần nhất. Đây cũng là hành vi
    của muc_cua() từ trước: tắt khẩn chỉ hạ mức 3 xuống 2, không chạm mức 4.
    """
    _dat(db, "nv_mkt", "tin_khach", 3)
    _dat(db, "nv_mkt", "canh_bao", 4)
    _tam_dung(db, "nghi ngờ trả lời sai giá")

    ok, ly_do = AQ.duoc_lam(db, "nv_mkt", "tin_khach", TRONG_GIO)
    assert not ok and "tạm dừng" in ly_do and "nghi ngờ trả lời sai giá" in ly_do
    assert AQ.duoc_lam(db, "nv_mkt", "canh_bao", TRONG_GIO)[0], "tắt khẩn không được tắt cảnh báo"


def test_chua_cau_hinh_thi_tu_choi_chu_khong_mac_dinh_cho_phep(db):
    """Không có dòng trong bảng nghĩa là CHƯA AI QUYẾT – phải từ chối, không suy ra là được phép."""
    ok, ly_do = AQ.duoc_lam(db, "nv_visa", "vb_noi_bo", TRONG_GIO)
    assert not ok and "chưa cấu hình quyền AI" in ly_do
    ok, ly_do = AQ.duoc_lam(db, "nv_mkt", "viec_khong_co_that", TRONG_GIO)
    assert not ok and "không phải nhóm việc" in ly_do


def test_duoc_tu_gui_giu_nguyen_hanh_vi_va_dung_chung_mot_luat(db):
    """duoc_tu_gui() phải là lớp mỏng trên duoc_lam(), không phải bản sao thứ hai của luật.

    Hai bản sao của cùng một luật là cách chắc chắn để sau vài tháng chúng nói khác nhau — và
    VTOS đã có tiền lệ: bốn công thức lãi lỗ tour chạy song song cho bốn kết quả.
    """
    _dat(db, AQ.CHU_QUAN_HOP_THU, "tin_khach", 3)
    assert AQ.duoc_tu_gui(db, TRONG_GIO) == AQ.duoc_lam(db, AQ.CHU_QUAN_HOP_THU, "tin_khach", TRONG_GIO)
    assert AQ.duoc_tu_gui(db, TRONG_GIO)[0]
    assert not AQ.duoc_tu_gui(db, NGOAI_GIO)[0]

    import inspect
    than = inspect.getsource(AQ.duoc_tu_gui)
    assert "duoc_lam(" in than
    assert "_trong_khung_gio" not in than, "duoc_tu_gui đang chép lại luật thay vì gọi duoc_lam"


def test_moi_lan_tu_choi_deu_kem_ly_do(db):
    """Không bao giờ trả về (False, "") – người đọc nhật ký phải biết vì sao AI im lặng."""
    _dat(db, "hcns", "tin_khach", 0)
    _dat(db, "hcns", "cham_diem", 3, han_muc={})
    for tac_vu in ("tin_khach", "cham_diem", "hoi_dap"):
        ok, ly_do = AQ.duoc_lam(db, "hcns", tac_vu, TRONG_GIO)
        assert not ok
        assert ly_do.strip(), f"{tac_vu}: từ chối mà không nói lý do"


def test_het_luot_trong_ngay_thi_dung_dung_theo_tung_nhom_viec(db):
    """Số lượt đếm RIÊNG từng nhóm việc – dùng hết lượt soạn văn bản không được khoá luôn hộp thư."""
    from app.models.core import AiRun
    _dat(db, "nv_mkt", "vb_noi_bo", 3, han_muc={**AQ.HAN_MUC_MAC_DINH, "so_luot_ngay": 2})
    _dat(db, "nv_mkt", "tin_khach", 3)
    for _ in range(2):
        db.add(AiRun(tac_vu="vb_noi_bo", muc=3, ts=TRONG_GIO))
    db.flush()
    ok, ly_do = AQ.duoc_lam(db, "nv_mkt", "vb_noi_bo", TRONG_GIO)
    assert not ok and "hết 2 lượt" in ly_do
    assert AQ.duoc_lam(db, "nv_mkt", "tin_khach", TRONG_GIO)[0], "hết lượt nhóm này khoá nhầm nhóm kia"
