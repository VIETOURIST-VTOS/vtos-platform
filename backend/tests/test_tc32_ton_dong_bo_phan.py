# -*- coding: utf-8 -*-
"""TC-32 · Khối 04c Tồn đọng theo bộ phận — nối vào chuỗi chủ cảnh báo đã có (PQ-9).

Anh Tuấn hỏi 14/9/2026: bốn khối còn "Chưa kết nối", cái nào thiếu SỐ THẬT, cái nào chỉ thiếu một
BẢNG KHAI. Khối này không thiếu cả hai — chuỗi cảnh báo → người phụ trách → bộ phận đã có sẵn từ
vòng PQ-9. Nhưng nó dễ sai ở ba chỗ, và mỗi chỗ sai ra một con số TO, TRÔNG HỢP LÝ, VÀ SAI.

Phép thử dưới đây canh đúng ba chỗ ấy, cộng hàng rào SEC-02.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Alert, User
from app.services import ton_dong_bo_phan as TD

HOM_NAY = dt.date(2026, 9, 14)


def _luc(n: int) -> dt.datetime:
    """n ngày TRƯỚC ngày báo cáo."""
    return dt.datetime(2026, 9, 14) - dt.timedelta(days=n)


@pytest.fixture()
def db():
    """Sổ cảnh báo giả, dựng bằng chính mô hình thật — không dựng bản sao của mô hình.

    Chỉ dựng ĐÚNG HAI BẢNG mà khối này đọc, và KHÔNG đụng vào `Base.metadata` chung. Bản đầu của
    phép thử này gỡ hết bảng thừa ra khỏi sơ đồ rồi lắp lại lúc dọn — chạy một mình thì đúng, chạy
    chung cả bộ kiểm thì đang sửa một thứ dùng chung giữa chừng, và phép thử hỏng sẽ hiện ra ở
    tệp KHÁC. Truyền thẳng `tables=` thì không có chuyện ấy.
    """
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=[User.__table__, Alert.__table__])
    s = sessionmaker(bind=e)()
    try:
        yield s
    finally:
        s.close()


def _nguoi(db, i, ten, phong):
    db.add(User(id=i, username=f"u{i}", full_name=ten, role="nv_kd", department=phong,
                password_hash="x", active=True))


def _cb(db, kind, ref, ngay_truoc, *, chu=None, chu_pq=None, han=None, xong=False):
    db.add(Alert(kind=kind, ref=ref, level="red", message="m", to_roles="",
                 created_at=_luc(ngay_truoc), resolved=xong,
                 nguoi_nhan_id=chu, nguoi_phu_trach=chu_pq, han_xu_ly=han))


@pytest.fixture()
def so(db):
    """Sổ mẫu dùng chung cho phần lớn phép thử."""
    _nguoi(db, 1, "Nguyễn Thị Mai", "dieu_hanh")
    _nguoi(db, 2, "Trần Mỹ Duyên", "dieu_hanh")
    _nguoi(db, 3, "Hồ Bảo Hà", "kd_le")
    _nguoi(db, 4, "Lê Kim Oanh", "kd_doan")
    # Điều hành: TOUR-A phát BA cảnh báo nhưng vẫn là MỘT hồ sơ.
    _cb(db, "qua_han_qt", "TOUR-A", 42, chu=1, han=dt.datetime(2026, 9, 20))
    _cb(db, "qua_han_qt", "TOUR-A", 10, chu=1, han=dt.datetime(2026, 9, 16))
    _cb(db, "thieu_du_toan", "TOUR-A", 5, chu=2)
    _cb(db, "qua_han_qt", "TOUR-B", 12, chu=1)
    _cb(db, "qua_han_qt", "TOUR-C", 3, chu=2)
    # Kinh doanh Lẻ: chủ CHỈ có ở cột PQ-9.
    _cb(db, "qua_deadline_thu", "booking:BK1", 7, chu_pq=3)
    # Kinh doanh Đoàn: hai cột chủ lệch nhau.
    _cb(db, "sla_booking", "booking:BK2", 2, chu=4, chu_pq=3)
    # Chưa có chủ.
    _cb(db, "cham_soc_qua_han", "cs:9", 20)
    _cb(db, "sale_tra_loi_cham", "conv:5", 1)
    # Loại KHÔNG tính.
    for i in range(4):
        _cb(db, "dt_thieu_nguon", f"dt:{i}", 6, chu=3)
    _cb(db, "r9_chay_duoi_hoa_von", "TOUR-Z", 9)
    # Đã xử lý xong thì không phải tồn đọng nữa.
    _cb(db, "qua_han_qt", "TOUR-XONG", 30, chu=1, xong=True)
    db.commit()
    return db


def _theo(r):
    return {d["ma_bo_phan"]: d for d in r["dong"]}


# ───────────────── 1 · MỖI HỒ SƠ CHỈ TÍNH MỘT LẦN ─────────────────

def test_mot_ho_so_ba_canh_bao_van_la_mot_ho_so(so):
    """Bản vẽ nhấn mạnh điều này. Đếm theo dòng cảnh báo thì TOUR-A thành ba hồ sơ."""
    d = _theo(TD.theo_bo_phan(so, hom_nay=HOM_NAY))["dieu_hanh"]
    assert d["ho_so_qua_han"] == 3, (
        "Điều hành phải là 3 hồ sơ (TOUR-A, TOUR-B, TOUR-C) — TOUR-A phát ba cảnh báo vẫn là một."
    )


def test_cong_cac_bo_phan_cong_chua_ro_ra_dung_tong(so):
    """Không trùng, không hở. Một hồ sơ chỉ được thuộc MỘT bộ phận."""
    r = TD.theo_bo_phan(so, hom_nay=HOM_NAY)
    tong = sum(d["ho_so_qua_han"] for d in r["dong"]) + r["chua_ro_bo_phan"]["so"]
    assert tong == 7, f"Phải ra đúng 7 hồ sơ đang mở thuộc diện tính, đang ra {tong}."


def test_canh_bao_da_xu_ly_khong_con_la_ton_dong(so):
    """`resolved` = đã xong. Đếm cả nó là thổi phồng con số trên màn hình lãnh đạo."""
    r = TD.theo_bo_phan(so, hom_nay=HOM_NAY)
    hs = " ".join(d["ho_so_lau_nhat"] or "" for d in r["dong"])
    assert "TOUR-XONG" not in hs, "Hồ sơ đã xử lý xong vẫn bị tính là tồn đọng."


# ───────────────── 2 · LOẠI TRỪ ĐÚNG, VÀ NÓI RA ĐÃ LOẠI GÌ ─────────────────

def test_dt_thieu_nguon_khong_tinh_la_ho_so_qua_han(so):
    """Đo bản chạy thật 14/9: 60/60 dòng gửi kèm màn hình đều là loại này. Nó là một DÒNG DÒNG TIỀN
    CHƯA CÓ NGUỒN, không phải một hồ sơ nằm quá hạn ở phòng nào — và đã có chỗ riêng ở khối 06."""
    r = TD.theo_bo_phan(so, hom_nay=HOM_NAY)
    assert "dt_thieu_nguon" in TD.KHONG_TINH
    assert not any("dt:" in (d["ho_so_lau_nhat"] or "") for d in r["dong"])


def test_da_loai_phai_dem_duoc_va_co_ly_do(so):
    """Khối bên trên ghi 1.476, khối này ghi vài chục. Lệch mà không giải thích thì người đọc kết
    luận một trong hai cái sai — và họ có lý."""
    r = TD.theo_bo_phan(so, hom_nay=HOM_NAY)
    theo = {x["loai"]: x for x in r["da_loai"]}
    assert theo["dt_thieu_nguon"]["so_ho_so"] == 4
    assert all(x["ly_do"].strip() for x in r["da_loai"]), (
        "Mỗi loại bị loại BẮT BUỘC có lý do viết ra — 'loại này không tính' là lối thoát dễ nhất."
    )


def test_moi_dong_danh_sach_den_deu_phai_co_ly_do():
    """Canh ngay ở hằng số, để lần sau ai thêm một loại mà bỏ trống lý do là hỏng phép thử."""
    thieu = [k for k, v in TD.KHONG_TINH.items() if not (v or "").strip()]
    assert not thieu, f"Các loại bị loại mà không ghi lý do: {thieu}"


def test_khong_dung_danh_sach_trang():
    """Bộ mã loại cảnh báo là BỘ MỞ (canh_bao_trinh_bay.py đã đo: có chỗ truyền `kind` bằng biến).
    Khai 'chỉ những loại này mới tính' thì mỗi loại mới sinh ra sau này ÂM THẦM BIẾN MẤT khỏi khối
    04c, mà màn hình vẫn có số nên không ai biết."""
    ma = TD.__doc__ or ""
    assert "DANH SÁCH ĐEN" in ma.upper() or "danh sách đen" in ma
    nguon = open(TD.__file__, encoding="utf-8").read()
    assert "notin_" in nguon, "Phải lọc bằng NOT IN (danh sách đen), không phải IN (danh sách trắng)."


def test_loai_moi_chua_ai_xet_van_hien_ra(db):
    """Hệ quả kiểm được của danh sách đen: một mã loại chưa ai nghĩ tới vẫn lên bảng."""
    _nguoi(db, 1, "Người A", "cntt")
    _cb(db, "mot_loai_hoan_toan_moi_chua_ai_khai", "X-1", 3, chu=1)
    db.commit()
    r = TD.theo_bo_phan(db, hom_nay=HOM_NAY)
    assert _theo(r)["cntt"]["ho_so_qua_han"] == 1, "Loại mới phải hiện ra, không được biến mất."


# ───────────────── 3 · BỘ PHẬN SUY TỪ CHỦ, HỎNG PHẢI CÓ TIẾNG ─────────────────

def test_chu_chi_co_o_cot_pq9_van_suy_ra_duoc_bo_phan(so):
    """`alerts` có HAI cột chủ: `nguoi_nhan_id` (KS-4) và `nguoi_phu_trach` (PQ-9). Nối chỉ vào cột
    KS-4 thì mọi cảnh báo do PQ-9 giao rơi vào 'chưa rõ bộ phận' dù đã có chủ hẳn hoi."""
    assert _theo(TD.theo_bo_phan(so, hom_nay=HOM_NAY))["kd_le"]["ho_so_qua_han"] == 1


def test_hai_cot_chu_lech_nhau_phai_dem_duoc(so):
    """Lệch là dấu hiệu một trong hai vòng đang ghi vào cột không ai đọc. Gộp im lặng thì chỗ nợ ấy
    không bao giờ lộ ra."""
    assert TD.theo_bo_phan(so, hom_nay=HOM_NAY)["lech_hai_cot_chu"] == 1


def test_chua_co_chu_la_mot_dong_duoc_dem_khong_nhet_vao_phong_nao(so):
    r = TD.theo_bo_phan(so, hom_nay=HOM_NAY)
    assert r["chua_ro_bo_phan"]["so"] == 2
    assert r["chua_ro_bo_phan"]["vi_sao"].strip(), "Dòng chưa rõ phải nói VÌ SAO chưa rõ."
    assert TD.CHUA_RO not in [d["ma_bo_phan"] for d in r["dong"]], (
        "Dòng chưa rõ bộ phận không được nằm lẫn trong bảng bộ phận."
    )


def test_ma_bo_phan_chua_khai_thi_hien_nguyen_ma(db):
    """Đặt tên bừa nguy hơn để nguyên mã: một cái tên tiếng Việt trông như đã có người xét."""
    _nguoi(db, 1, "Người A", "phong_moi_chua_khai")
    _cb(db, "qua_han_qt", "T1", 2, chu=1)
    db.commit()
    assert _theo(TD.theo_bo_phan(db, hom_nay=HOM_NAY))["phong_moi_chua_khai"]["bo_phan"] \
        == "phong_moi_chua_khai"


# ───────────────── 4 · KHÔNG BỊA SỐ, KHÔNG BỊA NGÀY ─────────────────

def test_han_khac_phuc_lay_han_som_nhat(so):
    """TOUR-A có hai hạn: 20/9 và 16/9. Hạn GẦN NHẤT mới là hạn."""
    assert _theo(TD.theo_bo_phan(so, hom_nay=HOM_NAY))["dieu_hanh"]["han_khac_phuc"] == "16/09/2026"


def test_chua_ai_dat_han_thi_de_rong_khong_bia_ngay(so):
    assert _theo(TD.theo_bo_phan(so, hom_nay=HOM_NAY))["kd_le"]["han_khac_phuc"] is None


def test_ho_so_lau_nhat_tinh_tu_canh_bao_mo_som_nhat(so):
    d = _theo(TD.theo_bo_phan(so, hom_nay=HOM_NAY))["dieu_hanh"]
    assert d["ho_so_lau_nhat"].startswith("42 ngày · TOUR-A")


def test_phong_nhieu_nguoi_thi_noi_ro_con_bao_nhieu_nguoi(so):
    """Bản vẽ để MỘT ô 'người chịu trách nhiệm', mà một phòng có nhiều người. Hiện một cái tên rồi
    im là nói rằng chỉ người đó chịu."""
    assert "+1 người" in _theo(TD.theo_bo_phan(so, hom_nay=HOM_NAY))["dieu_hanh"]["nguoi_chiu_trach_nhiem"]


def test_so_rong_khong_ra_mot_hang_so_khong(db):
    """RỖNG KHÁC KHÔNG. Một bảng toàn số 0 đọc y hệt 'không phòng nào tồn đọng'."""
    r = TD.theo_bo_phan(db, hom_nay=HOM_NAY)
    assert r["dong"] == [] and r["chua_ro_bo_phan"] is None
    assert r["vi_sao"] == TD.LY_DO_RONG and r["vi_sao"].strip()


# ───────────────── 5 · SEC-02 · HÀNG RÀO LỌC TRONG CÂU TRUY VẤN ─────────────────

def test_vai_bi_gioi_han_chi_thay_phong_minh(so):
    r = TD.theo_bo_phan(so, bo_phan_duoc_xem={"kd_le"}, hom_nay=HOM_NAY)
    assert [d["ma_bo_phan"] for d in r["dong"]] == ["kd_le"]
    assert r["chua_ro_bo_phan"] is None, (
        "Dòng chưa rõ bộ phận là việc của cấp điều phối, không thuộc phòng nào — vai bị giới hạn "
        "không được thấy."
    )
    assert r["da_loai"] == []


def test_hang_rao_nam_trong_cau_truy_van_khong_loc_sau_khi_cong():
    """Cộng xong mới cắt là đã đọc số của phòng khác một lần rồi. Canh ngay trong mã nguồn."""
    nguon = open(TD.__file__, encoding="utf-8").read()
    than = nguon[nguon.index("def _loc("):nguon.index("def theo_bo_phan(")]
    assert "User.department.in_" in than, (
        "Hàng rào SEC-02 phải nằm trong câu truy vấn `_loc`, không lọc ở tầng Python."
    )


def test_pham_vi_rong_khac_han_so_rong(db):
    """Tài khoản chưa khai bộ phận nhìn thấy bảng trống. Nếu ô ấy ghi 'đây là số thật' thì họ kết
    luận công ty không tồn đọng gì, trong khi sự thật là họ không được phép thấy."""
    _nguoi(db, 1, "Người A", "dieu_hanh")
    _cb(db, "qua_han_qt", "T1", 5, chu=1)
    db.commit()
    rong = TD.theo_bo_phan(db, bo_phan_duoc_xem=set(), hom_nay=HOM_NAY)
    assert rong["dong"] == [], "Phạm vi rỗng phải KHÔNG thấy gì — không mặc định thành xem hết."
    assert rong["vi_sao"] == TD.LY_DO_NGOAI_PHAM_VI
    assert rong["vi_sao"] != TD.LY_DO_RONG, (
        "'Không được thấy' và 'không có gì' phải là hai câu khác nhau."
    )


def test_dashboard_khong_mac_dinh_mo_toan_bo_cho_vai_la():
    """Mặc định 'chưa khai bộ phận = xem hết' là cách một tài khoản THIẾU dữ liệu biến thành một
    tài khoản THỪA quyền. Canh ngay ở chỗ nối trong dashboard."""
    # Đọc theo ĐƯỜNG DẪN, không `import` – phép thử này chỉ soi chữ trong mã nguồn, mà nạp
    # dashboard.py thì kéo theo cả chuỗi mô hình và fastapi, biến một phép thử đọc chữ thành một
    # phép thử phụ thuộc toàn bộ kho.
    from pathlib import Path
    dash = Path(__file__).resolve().parents[1] / "app" / "services" / "dashboard.py"
    nguon = dash.read_text(encoding="utf-8")
    i = nguon.index("TC-32")
    khoi = nguon[i:i + 1400]
    assert "_pham_vi_bp = None" in khoi and "else set()" in khoi, (
        "Vai không thuộc nhóm lãnh đạo phải nhận phạm vi của phòng mình, và phạm vi RỖNG nếu chưa "
        "khai phòng — không được nhận None (xem toàn bộ)."
    )
