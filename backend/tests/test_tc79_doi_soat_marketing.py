"""TC-79 · ĐỐI SOÁT DỮ LIỆU MARKETING — nhóm 2.8, bàn cân.

NĂM CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH — đều là loại nhìn màn hình KHÔNG phát hiện được:

 1. BÀN CÂN TỰ SINH RA VẬT ĐỂ CÂN. Nếu tệp này tự đếm doanh thu hay tỷ lệ, nó sẽ có một con số
    thứ hai cho cùng một câu hỏi, và chính nó thành thứ cần đối soát. `test_khong_tu_tinh_lai_gi`
    đọc mã bằng cây cú pháp và đòi nó gọi lại máy của nhóm 2.6/2.7.

 2. "KHỚP" BỊ NHẦM VỚI "CHƯA AI KHAI". Kỳ chưa ai khai số lead mà báo chênh 0 là báo cáo một sự
    khớp nhau chưa từng được kiểm. Rỗng phải ra rỗng.

 3. HAI LOẠI TRÙNG BỊ GỘP. Hai lead cùng số điện thoại là chuyện BÌNH THƯỜNG — một khách hỏi hai
    tour là hai lead thật. Hai lead cùng DẤU VÂN TAY mới là trùng thật, và tìm thấy nghĩa là phép
    chống trùng của đường nạp đã rò. Gộp hai con số ấy là vừa báo động giả vừa giấu mất báo động thật.

 4. NHẬT KÝ CHỐT SỐ GHI TRẠNG THÁI SAU KHI ĐÃ GHI ĐÈ. Chốt lại là ghi đè mốc cũ; đọc bản cũ sau
    khi đã gán bản mới thì cột "before" ghi lại đúng bản mới. Lỗi này đã bắt được hai lần trong
    kho (gộp tài khoản, bàn giao lead), nên ở đây có phép thử riêng.

 5. MỘT BẢNG CHỤP SỐ THỨ HAI. Kho đã có `bao_cao_luu`. Dựng bảng riêng cho Marketing là cách chắc
    chắn để lịch sử một kỳ nằm ở hai chỗ và không chỗ nào đủ.
"""
import ast
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.bao_cao_luu import BaoCaoLuu
from app.models.core import Booking, Tour, User
from app.models.crm import Lead, LeadChannelStat
from app.services import doi_soat_marketing as DS

GOC = Path(__file__).resolve().parents[1]
T0 = dt.datetime(2026, 9, 1, 8, 0)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten, vai="ptgd_mkt"):
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _lead(db, sdt, kenh="facebook", **kw):
    d = dict(phone=sdt, name="L" + sdt, channel=kenh, lead_month="2026-09",
             received_at=T0, status="moi")
    d.update(kw)
    l = Lead(**d); db.add(l); db.commit()
    return l


def _khai(db, kenh, so, chi=None, ky="2026-09"):
    s = LeadChannelStat(lead_month=ky, channel=kenh, leads=so, cost=chi, updated_by="mkt")
    db.add(s); db.commit()
    return s


def _booking(db, tien, nguon=""):
    u = db.execute(select(User)).scalars().first() or _u(db, "sale1", "nv_kd")
    t = Tour(code="T1", name="T1", tour_type="le_noi_dia", start_date=dt.date(2026, 9, 18),
             end_date=dt.date(2026, 9, 20), operator_id=1, status="ket_thuc", actual_revenue=0.0)
    db.add(t); db.commit()
    b = Booking(code="B1", tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="K", customer_phone="0900000099", source=nguon, campaign_code="",
                pax=2, amount=tien, cancelled=False, counts_for_target=True,
                sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


# ═════════════════════════ 2.8.2 — ĐỐI CHIẾU ═════════════════════════

def test_lech_so_lead_dem_dung_theo_tung_kenh():
    db = _db()
    _lead(db, "0900000001", "facebook"); _lead(db, "0900000002", "facebook")
    _lead(db, "0900000003", "zalo")
    _khai(db, "facebook", 5)
    _khai(db, "zalo", 3)
    kq = DS.doi_chieu(db, "2026-09")
    r = {x["kenh"]: x for x in kq["theo_kenh"]}
    assert r["facebook"]["lech_lead"] == -3, "Sổ 2, khai 5 → chênh -3"
    assert r["zalo"]["lech_lead"] == -2


def test_kenh_chua_ai_khai_thi_lech_la_RONG_chu_khong_phai_0():
    """Chỗ nguy hiểm số 2 ở đầu tệp: báo chênh 0 là báo một sự khớp chưa từng được kiểm."""
    db = _db()
    _lead(db, "0900000001", "facebook")
    kq = DS.doi_chieu(db, "2026-09")
    assert kq["theo_kenh"][0]["lech_lead"] is None
    assert kq["tong_lead_khai_bao"] is None
    assert "CHƯA XÁC ĐỊNH" in kq["canh_bao_chua_khai"]


def test_kenh_chi_co_trong_khai_bao_van_hien_ra():
    """Marketing khai một kênh mà sổ lead không có dòng nào — đó là chênh lớn nhất có thể, và nó
    sẽ biến mất nếu chỉ duyệt theo sổ lead."""
    db = _db()
    _lead(db, "0900000001", "facebook")
    _khai(db, "tiktok", 40)
    r = {x["kenh"]: x for x in DS.doi_chieu(db, "2026-09")["theo_kenh"]}
    assert "tiktok" in r
    assert (r["tiktok"]["so_lead_so_sach"], r["tiktok"]["lech_lead"]) == (0, -40)


def test_hai_so_chi_phi_dat_canh_nhau_va_KHONG_chon_ben_nao():
    db = _db()
    _lead(db, "0900000001", "facebook")
    _khai(db, "facebook", 1, chi=30_000_000)
    kq = DS.doi_chieu(db, "2026-09")["hai_so_chi_phi"]
    assert kq["theo_kenh_khai"] == 30_000_000
    assert kq["theo_ngan_sach"] == 0            # chưa lập ngân sách kỳ này
    assert kq["lech"] == -30_000_000
    assert "KHÔNG buộc phải bằng nhau" in kq["co_so"]


def test_chua_ai_khai_chi_thi_lech_chi_phi_cung_RONG():
    db = _db()
    _lead(db, "0900000001", "facebook")
    _khai(db, "facebook", 1)                    # khai số lead nhưng không khai chi
    kq = DS.doi_chieu(db, "2026-09")["hai_so_chi_phi"]
    assert kq["theo_kenh_khai"] is None and kq["lech"] is None


def test_dem_rieng_so_dong_va_so_dien_thoai():
    """Hai đơn vị, không gộp. Nhãn phải gọi đúng tên — hai người chung một số đếm thành một."""
    db = _db()
    _lead(db, "0900000001", "facebook"); _lead(db, "0900000001", "facebook")
    r = DS.doi_chieu(db, "2026-09")["theo_kenh"][0]
    assert (r["so_lead_so_sach"], r["so_sdt_so_sach"]) == (2, 1)


def test_doanh_thu_lay_tu_may_cua_nhom_2_7_khong_dem_lai():
    db = _db()
    _booking(db, 500_000_000, nguon="zalo")
    kq = DS.doi_chieu(db, "2026-09")["doanh_thu"]
    assert kq["tong"] == 500_000_000
    assert kq["truy_duoc_nguon"] == 500_000_000


# ═════════════════════════ 2.8.1 — TRÙNG & THIẾU NGUỒN ═════════════════════════

def test_hai_loai_trung_de_RIENG_khong_gop():
    """Chỗ nguy hiểm số 3 ở đầu tệp."""
    db = _db()
    _lead(db, "0900000001", "facebook")                       # cùng số, khác lead — bình thường
    _lead(db, "0900000001", "zalo")
    _lead(db, "0900000002", "facebook", dau_van_tay="VT1")    # cùng dấu vân tay — rò thật
    _lead(db, "0900000003", "facebook", dau_van_tay="VT1")
    kq = DS.trung_va_thieu_nguon(db, "2026-09")
    assert kq["nhieu_lead_cung_sdt"]["so_sdt"] == 1
    assert kq["trung_dau_van_tay"]["so_nhom"] == 1
    assert "KHÔNG phải lỗi" in kq["nhieu_lead_cung_sdt"]["co_so"]
    assert "rò" in kq["trung_dau_van_tay"]["co_so"]


def test_lead_thieu_kenh_hien_ra_tung_dong():
    db = _db()
    _lead(db, "0900000001", "")
    _lead(db, "0900000002", "facebook")
    kq = DS.trung_va_thieu_nguon(db, "2026-09")["lead_thieu_kenh"]
    assert kq["so_lead"] == 1 and kq["rows"][0]["phone"] == "0900000001"


def test_booking_thieu_nguon_lay_tu_may_nhom_2_7():
    db = _db()
    _booking(db, 250_000_000, nguon="")
    kq = DS.trung_va_thieu_nguon(db, "2026-09")["booking_thieu_nguon"]
    assert kq["so_booking"] == 1 and kq["tien"] == 250_000_000


# ═════════════════════════ 2.8.3 — CHUẨN KỲ & ĐỘ TRÔI ═════════════════════════

def test_chua_chot_thi_noi_ro_chua_co_moc_de_so():
    db = _db()
    _lead(db, "0900000001")
    kq = DS.do_troi(db, "2026-09")
    assert kq["da_chot"] is False and kq["dong"] == []
    assert "chưa ai chốt số" in kq["canh_bao"]


def test_chot_ky_ghi_vao_bang_bao_cao_luu_SAN_CO():
    """Chỗ nguy hiểm số 5 ở đầu tệp: không dựng bảng chụp số thứ hai."""
    db = _db()
    boi = _u(db, "mkt1")
    _lead(db, "0900000001")
    DS.chot_ky(db, boi, "2026-09", "chốt lần đầu")
    db.commit()
    r = db.execute(select(BaoCaoLuu).where(BaoCaoLuu.kind == "mkt")).scalars().all()
    assert len(r) == 1
    assert (r[0].ky, r[0].pham_vi, r[0].tao_boi) == ("2026-09", "marketing", "mkt1")
    assert r[0].chi_tieu["tong_lead"] == 1


def test_chot_lai_la_GHI_DE_chu_khong_them_dong():
    db = _db()
    boi = _u(db, "mkt1")
    _lead(db, "0900000001")
    DS.chot_ky(db, boi, "2026-09"); db.commit()
    _lead(db, "0900000002")
    DS.chot_ky(db, boi, "2026-09", "chốt lại sau khi bổ sung lead"); db.commit()
    r = db.execute(select(BaoCaoLuu).where(BaoCaoLuu.kind == "mkt")).scalars().all()
    assert len(r) == 1, "Mỗi kỳ giữ đúng MỘT mốc chuẩn"
    assert r[0].chi_tieu["tong_lead"] == 2


def test_nhat_ky_chot_lai_ghi_BO_SO_CU_o_cot_before():
    """Chỗ nguy hiểm số 4 ở đầu tệp — lỗi này đã bắt được hai lần trong kho."""
    db = _db()
    from app.models.core import AuditLog
    boi = _u(db, "mkt1")
    _lead(db, "0900000001")
    DS.chot_ky(db, boi, "2026-09"); db.commit()
    _lead(db, "0900000002")
    DS.chot_ky(db, boi, "2026-09", "bổ sung"); db.commit()
    nk = db.query(AuditLog).filter(AuditLog.action == "chot_so_ky_marketing").all()
    assert len(nk) == 2
    assert nk[0].before is None, "Lần chốt đầu thì trước đó không có gì"
    assert nk[1].before["tong_lead"] == 1, "Cột before phải là bộ số CŨ"
    assert nk[1].after["tong_lead"] == 2


def test_do_troi_tinh_dung_va_noi_ro_troi_khong_phai_loi():
    db = _db()
    boi = _u(db, "mkt1")
    _lead(db, "0900000001")
    DS.chot_ky(db, boi, "2026-09"); db.commit()
    _lead(db, "0900000002"); _lead(db, "0900000003")
    kq = DS.do_troi(db, "2026-09")
    o = {d["o"]: d for d in kq["dong"]}
    assert (o["tong_lead"]["luc_chot"], o["tong_lead"]["hien_tai"], o["tong_lead"]["troi"]) == (1, 3, 2)
    assert kq["co_troi"] is True
    assert "KHÔNG phải là lỗi" in kq["co_so"]


def test_khong_troi_thi_noi_ro_la_khong_troi():
    db = _db()
    boi = _u(db, "mkt1")
    _lead(db, "0900000001")
    DS.chot_ky(db, boi, "2026-09"); db.commit()
    kq = DS.do_troi(db, "2026-09")
    assert kq["co_troi"] is False
    assert all(d["troi"] == 0 for d in kq["dong"])


def test_o_khong_co_trong_ban_chup_cu_thi_troi_la_RONG_chu_khong_quy_ve_0():
    """Quy về 0 là bịa ra một lần trôi chưa từng xảy ra."""
    db = _db()
    boi = _u(db, "mkt1")
    db.add(BaoCaoLuu(kind="mkt", ky="2026-09", pham_vi="marketing",
                     chi_tieu={"tong_lead": 5}, tao_boi="cu", tao_luc=T0))
    db.commit()
    o = {d["o"]: d for d in DS.do_troi(db, "2026-09")["dong"]}
    assert o["tong_doanh_thu"]["luc_chot"] is None
    assert o["tong_doanh_thu"]["troi"] is None


# ═════════════════════════ CẤU TRÚC ═════════════════════════

def test_khong_tu_tinh_lai_gi():
    """Chỗ nguy hiểm số 1 ở đầu tệp. Bàn cân tự sinh ra vật để cân là bàn cân vô nghĩa."""
    cay = ast.parse((GOC / "app" / "services" / "doi_soat_marketing.py").read_text(encoding="utf-8"))
    nhap = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            nhap.update(a.name for a in n.names)
    assert {"dong_gop_marketing", "chuyen_doi_lead"} <= nhap, (
        "Phải gọi lại máy của nhóm 2.6 và 2.7, không tự tính doanh thu hay tỷ lệ của riêng mình.")
    assert "Tour" not in nhap, "Đếm lại chuyến ở đây là mở đường cho hai bảng nói hai số."


def test_cua_dung_tien_to_rieng_va_chot_hep_hon_xem():
    from app.api.v1 import doi_soat_marketing as API
    assert API.router.prefix == "/api/v1/doi-soat-marketing"
    assert set(API.CHOT) < set(API.XEM)
    assert "nv_mkt" not in API.CHOT, (
        "Chốt số là đặt một mốc mà mọi báo cáo sau đó đem ra so. Người tự đặt được mốc cho mình "
        "là người tự chấm được mình — dù nv_mkt ghi được ở cả nhóm 2.6 lẫn 2.7.")


def test_man_hinh_khai_dung_mot_nhom_cua():
    from app.services.access import MAN_HINH_API
    assert MAN_HINH_API["/doi-soat-marketing"] == ("/api/v1/doi-soat-marketing",)


def test_vong_nay_khong_them_bang_va_khong_them_ban_nang_cap():
    """Nhóm 2.8 dùng lại `bao_cao_luu` sẵn có. Một bản nâng cấp mới ở đây là dấu hiệu đã bỏ sót
    bảng ấy."""
    assert not list((GOC / "alembic" / "versions").glob("tc79*.py"))
    assert DS.KIND == "mkt" and DS.PHAM_VI == "marketing"
