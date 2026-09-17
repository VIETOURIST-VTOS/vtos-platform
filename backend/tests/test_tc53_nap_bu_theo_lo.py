# -*- coding: utf-8 -*-
"""TC-53 · NẠP BÙ THEO LÔ — hai cửa nhỏ thay cho một lần chạy dài không bao giờ xong.

    "Em cập nhat luôn từ thang 1 đến nay trong vtos da co dữ liệu ơ quyet toan tour"
                                                                — anh Tuấn, 17/9/2026

Đếm cùng ngày: VTOS không có chuyến nào KẾT THÚC trước tháng 6/2026 — T6 297, T7 289, T8 220,
T9 119, T1–T5 trống trơn. Không mất dữ liệu: lần đồng bộ đầu (05/9) đặt mốc từ 01/6 nên Vietrip
chỉ trả về tour từ tháng 6. Chưa bao giờ kéo về, chứ không phải kéo về rồi mất.

══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO KHÔNG GỌI `run_sync(from_date=2026-01-01)` CHO XONG
══════════════════════════════════════════════════════════════════════════════════════════════
Hai chỗ, và cả hai đã tự chứng minh sáng 17/9 khi job chết giữa chừng:
  · `run_sync` quét TỪNG BOOKING để lấy phiếu thu. Từ tháng 1 là hơn 12.000 lượt gọi.
  · Nó chọn bảng quyết toán theo `settlements_days` đếm lùi từ HÔM NAY; muốn với tới tháng 1 phải
    đặt ~260 ngày → hơn nghìn trang × ~10 giây ≈ ba tiếng.
Render gói miễn phí ngủ sau 15 phút, robot chạy nền nằm trong chính tiến trình ấy.

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. LÔ KHÔNG CÓ ĐÁY. Cửa nạp phải trả về `con_lai` và chỉ làm `gioi_han` cái mỗi lần. Không có đáy
   thì nó lại là một lần chạy dài, và ngủ giữa chừng là mất sạch tiến độ.
2. NẠP TRÙNG. Gọi lại phải bỏ qua chuyến đã có bảng, không tải lại và không đẻ bản ghi thứ hai.
3. MỘT TRANG HỎNG GIẾT CẢ LÔ. Một chuyến lỗi thì ghi vào `loi` rồi đi tiếp — không được để cả lô
   đổ theo, vì lô sau lại bắt đầu từ đúng trang hỏng ấy và vòng lặp đứng im mãi mãi.
4. LỌC THEO NGÀY KHỞI HÀNH THAY VÌ NGÀY KẾT THÚC. Chuyến khởi hành 29/12 kết thúc 02/01 thuộc kỳ
   tháng 1. Lọc nhầm mốc là mất đúng những chuyến vắt qua giao thừa — ít, nhưng sai mà không ai
   nhìn ra vì bảng vẫn có số.
"""
import datetime as dt
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Company, Tour, User
from app.models.vietrip import VtRecord
from app.services import vietrip_client as VC

GOC = Path(__file__).resolve().parents[2]
CLIENT = GOC / "backend" / "app" / "services" / "vietrip_client.py"
CUA = GOC / "backend" / "app" / "api" / "v1" / "vietrip.py"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma_py(s: str) -> str:
    s = re.sub(r'"""(?:.|\n)*?"""', " ", s)
    return re.sub(r"^\s*#.*$", " ", s, flags=re.M)


def _db():
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _so_gia(so_chuyen=10, so_da_co_bang=3):
    """N chuyến kết thúc tháng 1/2026, trong đó vài chuyến đã có bảng quyết toán."""
    db = _db()
    db.add(Company(code="VTD", name="Vietourist Holdings", kind="me", active=True))
    db.commit()
    u = User(username="dh", full_name="Điều hành", role="nv_dh", password_hash="x")
    db.add(u); db.commit()
    for i in range(so_chuyen):
        code = f"T{i:03d}"
        db.add(VtRecord(entity="tour", vietrip_id=str(9000 + i), ref=code, applied=True, raw={
            "recID": 9000 + i, "tourcode": code,
            "ngayKhoiHanh": "2026-01-05T00:00:00", "ngayKetThuc": "2026-01-08T00:00:00"}))
        if i < so_da_co_bang:
            db.add(VtRecord(entity="settlement", vietrip_id=code, ref=code, applied=True,
                            raw={"tourcode": code, "step": "Bước 5: Lập Quyết toán", "lines": []}))
    # một chuyến kết thúc tháng 6 — ngoài kỳ, không được đụng tới
    db.add(VtRecord(entity="tour", vietrip_id="8000", ref="NGOAI", applied=True, raw={
        "recID": 8000, "tourcode": "NGOAI",
        "ngayKhoiHanh": "2026-06-01T00:00:00", "ngayKetThuc": "2026-06-04T00:00:00"}))
    db.commit()
    return db


class _GiaClient:
    """Thay cho Client thật: đếm số trang đã tải, và có thể cho một mã cụ thể ném lỗi."""
    def __init__(self, ma_hong: set[int] | None = None):
        self.da_tai: list[str] = []
        self.ma_hong = ma_hong or set()

    def get(self, path, timeout=90):
        rid = int(path.rstrip("/").split("/")[-1])
        self.da_tai.append(path)
        if rid in self.ma_hong:
            raise RuntimeError("trang hỏng")
        return "<html></html>"


def _gan(monkeypatch, client, ghi=None):
    monkeypatch.setattr(VC, "_dang_nhap", lambda: client)
    monkeypatch.setattr(VC, "parse_settlement",
                        lambda html, tour: {"tourId": tour["recID"], "tourcode": tour["tourcode"],
                                            "tong_thu": 0, "tong_chi": 0, "lines": [], "step": "", "history": []})
    if ghi is not None:
        monkeypatch.setattr(VC.VT, "apply_settlements", lambda db, limit=400: 0)


# ═════════════════ 1 · LÔ PHẢI CÓ ĐÁY ═════════════════

def test_moi_lo_chi_lam_dung_gioi_han_va_bao_con_lai(monkeypatch):
    """Chỗ hỏng số 1."""
    db = _so_gia(so_chuyen=10, so_da_co_bang=0)
    c = _GiaClient(); _gan(monkeypatch, c, ghi=True)
    ra = VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=4)
    assert ra["da_nap"] == 4 and len(c.da_tai) == 4, (
        "Không có đáy thì nó lại là một lần chạy dài, và Render ngủ giữa chừng là mất sạch tiến độ."
    )
    assert ra["con_lai"] == 6


def test_goi_lap_toi_khi_het_va_khong_chay_vo_han(monkeypatch):
    db = _so_gia(so_chuyen=10, so_da_co_bang=0)
    c = _GiaClient(); _gan(monkeypatch, c, ghi=True)
    tong, vong = 0, 0
    while vong < 20:
        ra = VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=3)
        tong += ra["da_nap"]; vong += 1
        if ra["con_lai"] == 0: break
    assert tong == 10 and ra["con_lai"] == 0 and vong == 4


# ═════════════════ 2 · KHÔNG NẠP TRÙNG ═════════════════

def test_bo_qua_chuyen_da_co_bang_khong_tai_lai(monkeypatch):
    """Chỗ hỏng số 2."""
    db = _so_gia(so_chuyen=10, so_da_co_bang=3)
    c = _GiaClient(); _gan(monkeypatch, c, ghi=True)
    ra = VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=20)
    assert ra["da_nap"] == 7 and ra["con_lai"] == 0
    for p in c.da_tai:
        assert not p.endswith(("/9000", "/9001", "/9002")), "Tải lại bảng đã có là tốn 10 giây cho không."


def test_chay_lan_hai_khong_con_gi_de_nap(monkeypatch):
    db = _so_gia(so_chuyen=5, so_da_co_bang=0)
    c = _GiaClient(); _gan(monkeypatch, c)
    VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=20)
    lan_hai = VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=20)
    assert lan_hai["da_nap"] == 0 and lan_hai["con_lai"] == 0


# ═════════════════ 3 · MỘT TRANG HỎNG KHÔNG GIẾT CẢ LÔ ═════════════════

def test_mot_trang_hong_thi_ghi_lai_roi_di_tiep(monkeypatch):
    """Chỗ hỏng số 3 — nếu không, lô sau lại bắt đầu từ đúng trang hỏng và đứng im mãi mãi."""
    db = _so_gia(so_chuyen=5, so_da_co_bang=0)
    c = _GiaClient(ma_hong={9002}); _gan(monkeypatch, c, ghi=True)
    ra = VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=5)
    assert ra["da_nap"] == 4, "Bốn trang lành phải nạp được."
    assert len(ra["loi"]) == 1 and "T002" in ra["loi"][0], "Trang hỏng phải hiện ra kèm mã chuyến."
    assert len(c.da_tai) == 5, "Phải thử hết cả lô, không dừng ở trang hỏng."


# ═════════════════ 4 · LỌC THEO NGÀY KẾT THÚC ═════════════════

def test_loc_theo_ngay_ket_thuc_chu_khong_phai_ngay_khoi_hanh(monkeypatch):
    """Chỗ hỏng số 4: chuyến khởi hành 29/12/2025, kết thúc 02/01/2026 thuộc kỳ tháng 1."""
    db = _so_gia(so_chuyen=0, so_da_co_bang=0)
    db.add(VtRecord(entity="tour", vietrip_id="7777", ref="GIAOTHUA", applied=True, raw={
        "recID": 7777, "tourcode": "GIAOTHUA",
        "ngayKhoiHanh": "2025-12-29T00:00:00", "ngayKetThuc": "2026-01-02T00:00:00"}))
    db.commit()
    c = _GiaClient(); _gan(monkeypatch, c, ghi=True)
    ra = VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=10)
    assert ra["da_nap"] == 1, (
        "Chuyến vắt qua giao thừa phải vào kỳ tháng 1. Lọc nhầm sang ngày khởi hành là mất đúng "
        "những chuyến ấy — ít, nhưng sai mà bảng vẫn có số nên không ai nhìn ra."
    )


def test_chuyen_ngoai_khoang_khong_bi_dung_toi(monkeypatch):
    db = _so_gia(so_chuyen=2, so_da_co_bang=0)
    c = _GiaClient(); _gan(monkeypatch, c, ghi=True)
    VC.nap_quyet_toan_thieu(db, dt.date(2026, 1, 1), dt.date(2026, 1, 31), gioi_han=20)
    assert not any(p.endswith("/8000") for p in c.da_tai), "Chuyến tháng 6 nằm ngoài kỳ đang nạp bù."


# ═════════════════ HAI CỬA KHÔNG ĐƯỢC ĐỤNG BOOKING / PHIẾU THU ═════════════════

def test_hai_cua_nap_bu_khong_quet_booking_hay_phieu_thu():
    """Canh HÀNH VI: vòng lặp theo booking chính là chỗ làm chết job của `run_sync`."""
    ma = _ma_py(_doc(CLIENT))
    for ten in ("nap_tour_theo_khoang", "nap_quyet_toan_thieu"):
        khoi = ma[ma.index(f"def {ten}"):]
        khoi = khoi[:khoi.index("\ndef ", 10)]
        assert "/payments" not in khoi and "GetPaymentData" not in khoi, (
            f"`{ten}` không được đụng tới booking/phiếu thu — đó là chỗ đẻ ra hơn 12.000 lượt gọi."
        )


def test_hai_cua_co_that_trong_api_va_co_gac_vai_tro():
    ma = _doc(CUA)
    for duong in ("nap-bu/tour", "nap-bu/quyet-toan"):
        assert duong in ma, f"Thiếu cửa POST /import/vietrip/{duong}."
    khoi = ma[ma.index("nap-bu/quyet-toan"):]
    khoi = khoi[:khoi.index("@router", 10)] if "@router" in khoi[10:] else khoi
    assert "require_roles" in khoi, "Cửa nạp bù phải có gác vai trò."
