"""TC-77 · ĐÓNG GÓP DOANH THU CỦA MARKETING — hai lựa chọn anh Tuấn chốt 23/9/2026.

    "Chi phí theo chiến dịch"     →  THÊM CỘT nối dòng chi vào chiến dịch
    "Hai đường truy nguồn lệch"   →  ƯU TIÊN LEAD, booking là dự phòng

NĂM CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH — đều là loại nhìn màn hình KHÔNG phát hiện được:

 1. BẢNG XẾP HẠNG KÊNH TRÔNG THUYẾT PHỤC TRÊN MỘT ĐỘ PHỦ TỆ. Mọi bảng đều cộng đủ 100% phần nó
    thấy, kể cả khi nó chỉ thấy 12% doanh thu. `test_do_phu_*` ghim rằng con số độ phủ có thật và
    đúng, vì đó là thứ duy nhất cho người đọc biết bảng dưới đáng tin tới đâu.

 2. HAI ĐƯỜNG BẤT ĐỒNG BỊ NUỐT. Chọn một đường rồi im lặng về đường kia là biến một mâu thuẫn dữ
    liệu thành một con số trông rất gọn. `test_bat_dong_*` đòi những dòng ấy phải hiện ra.

 3. CHI CHƯA GẮN CHIẾN DỊCH BỊ CHIA ĐỀU. Chia đều làm bảng cân và làm mọi tỷ lệ sai cùng một lúc.

 4. CHIA CHO KHÔNG. Chiến dịch chưa gắn đồng chi nào mà tính "thu trên chi" là vừa ngã chương
    trình vừa ra một con số vô nghĩa. Ở đây trả RỖNG, và rỗng khác 0.

 5. CỬA GẮN NGUỒN SỬA ĐÈ LÊN CÂU TRẢ LỜI CŨ. Cửa ấy chỉ được ĐIỀN CHỖ TRỐNG. Ba phép thử canh ba
    hàng rào của nó.
"""
import ast
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Tour, User
from app.models.crm import Lead
from app.models.marketing import Campaign, MarketingBudget, MarketingBudgetLine
from app.services import dong_gop_marketing as DG

GOC = Path(__file__).resolve().parents[1]


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten, vai="nv_mkt"):
    u = User(username=ten, full_name=ten, role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _tour(db, ma, ket_thuc, loai="le_noi_dia"):
    t = Tour(code=ma, name=ma, tour_type=loai, start_date=ket_thuc - dt.timedelta(days=2),
             end_date=ket_thuc, operator_id=1, status="ket_thuc", actual_revenue=0.0)
    db.add(t); db.commit()
    return t


def _bk(db, ma, t, u, tien, nguon="", ma_cd="", sdt="0900000001", huy=False):
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="Khách " + ma, customer_phone=sdt, source=nguon,
                campaign_code=ma_cd, pax=2, amount=tien, cancelled=huy,
                counts_for_target=True, sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


def _cd(db, ma, ten, ngan_sach=0.0):
    c = Campaign(code=ma, name=ten, objective="doanh_thu", mang="le", channels=[],
                 from_date=dt.date(2026, 9, 1), budget=ngan_sach, status="dang_chay")
    db.add(c); db.commit()
    return c


def _lead(db, sdt, kenh, cd=None, booking=None, luc=None):
    l = Lead(phone=sdt, name="L" + sdt, channel=kenh, lead_month="2026-09",
             received_at=luc or dt.datetime(2026, 9, 1, 8, 0),
             campaign_id=cd.id if cd else None,
             booking_id=booking.id if booking else None)
    db.add(l); db.commit()
    return l


def _chi(db, ky, hang_muc, tien, cd=None):
    b = db.query(MarketingBudget).filter(MarketingBudget.period == ky).first()
    if b is None:
        b = MarketingBudget(period=ky, target_leads=10, target_revenue=0, rationale="thử",
                            status="hieu_luc", created_by="mkt")
        db.add(b); db.commit()
    db.add(MarketingBudgetLine(budget_id=b.id, hang_muc=hang_muc, amount=tien,
                               campaign_id=cd.id if cd else None))
    db.commit()


def _nen(db):
    """Một kỳ 2026-09 với ba booking: một qua lead-có-chiến-dịch, một chỉ có ô trên booking, một trống."""
    u = _u(db, "sale1", "nv_kd")
    t = _tour(db, "T1", dt.date(2026, 9, 20))
    cdA = _cd(db, "CD-A", "Chiến dịch A", 100_000_000)
    b1 = _bk(db, "B1", t, u, 500_000_000, sdt="0900000001")
    _lead(db, "0900000001", "facebook", cdA, b1)
    _bk(db, "B2", t, u, 300_000_000, nguon="zalo", ma_cd="CD-A", sdt="0900000002")
    _bk(db, "B3", t, u, 200_000_000, sdt="0900000003")
    return u, t, cdA


# ═════════════════════════ LUẬT CŨ ĐƯỢC NỚI — GHI CẢ HAI VẾ ═════════════════════════

def test_tc77_luat_cu_duoc_noi_va_ghi_ca_hai_ve():
    """CŨ: mỗi hạng mục chỉ được MỘT dòng trong một kỳ.
       MỚI: mỗi (hạng mục × chiến dịch) một dòng.

    Phép thử này ghim CẢ HAI vế, vì cả hai đều còn đúng ở đúng phần của nó — và vì một luật bị nới
    mà không ai ghi lại thì sáu tháng nữa sẽ có người đọc mã, thấy luật lỏng, và nới thêm lần nữa.
    """
    from app.services import marketing as MK
    db = _db()
    u = _u(db, "mkt1")
    a = _cd(db, "CD-A", "A"); b = _cd(db, "CD-B", "B")

    # VẾ MỚI: cùng hạng mục, KHÁC chiến dịch → CHO. Đây đúng là việc cột mới sinh ra để làm.
    kq = MK.tao_ngan_sach(db, u, {
        "period": "2026-09", "target_leads": 10, "rationale": "thử nới luật",
        "lines": [{"hang_muc": "quang_cao", "amount": 100, "campaign_id": a.id},
                  {"hang_muc": "quang_cao", "amount": 50, "campaign_id": b.id}]})
    assert kq is not None

    # VẾ CŨ VẪN CÒN NGUYÊN: cùng hạng mục, cùng để TRỐNG chiến dịch → CHẶN. Đó đúng là trường hợp
    # luật cũ nói tới: một khoản chi bị gõ hai lần.
    with pytest.raises(ValueError, match="một dòng"):
        MK.tao_ngan_sach(db, u, {
            "period": "2026-10", "target_leads": 10, "rationale": "thử vế cũ",
            "lines": [{"hang_muc": "quang_cao", "amount": 100},
                      {"hang_muc": "quang_cao", "amount": 50}]})


def test_dong_chi_gan_chien_dich_khong_co_that_thi_bi_chan():
    from app.services import marketing as MK
    db = _db()
    u = _u(db, "mkt1")
    with pytest.raises(ValueError, match="chiến dịch"):
        MK.tao_ngan_sach(db, u, {
            "period": "2026-09", "target_leads": 10, "rationale": "thử",
            "lines": [{"hang_muc": "quang_cao", "amount": 100, "campaign_id": 999}]})


def test_dong_chi_khong_gan_chien_dich_van_hop_le():
    """Chi chung cả tháng là việc có thật. Ép gắn chiến dịch là ép người nhập chọn bừa cho qua cửa."""
    from app.services import marketing as MK
    db = _db()
    u = _u(db, "mkt1")
    assert MK.tao_ngan_sach(db, u, {
        "period": "2026-09", "target_leads": 10, "rationale": "chi chung",
        "lines": [{"hang_muc": "quang_cao", "amount": 100}]}) is not None


# ═════════════════════════ LUẬT ƯU TIÊN: LEAD TRƯỚC ═════════════════════════

def test_lead_thang_o_tren_booking():
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    a = _cd(db, "CD-A", "A"); b = _cd(db, "CD-B", "B")
    bk = _bk(db, "B1", t, u, 100, nguon="zalo", ma_cd="CD-B")
    _lead(db, bk.customer_phone, "facebook", a, bk)
    kq = DG.thang(db, "2026-09")
    assert [c["ma"] for c in kq["theo_chien_dich"]] == ["CD-A"], "Lead phải thắng ô trên booking"


def test_bat_dong_hien_ra_chu_khong_bi_nuot():
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    a = _cd(db, "CD-A", "A"); _cd(db, "CD-B", "B")
    bk = _bk(db, "B1", t, u, 100, ma_cd="CD-B")
    _lead(db, bk.customer_phone, "facebook", a, bk)
    kq = DG.thang(db, "2026-09")
    assert kq["bat_dong"]["so_dong"] == 1
    r = kq["bat_dong"]["rows"][0]
    assert (r["theo_lead"], r["theo_booking"]) == ("CD-A", "CD-B")


def test_mot_ben_trong_KHONG_phai_bat_dong():
    """Một bên chưa ghi thì đó là thiếu dữ liệu, không phải mâu thuẫn. Gộp hai thứ ấy làm một là
    dựng ra một danh sách 'cần soát' dài tới mức không ai soát."""
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    a = _cd(db, "CD-A", "A")
    bk = _bk(db, "B1", t, u, 100)          # booking không ghi gì
    _lead(db, bk.customer_phone, "facebook", a, bk)
    assert DG.thang(db, "2026-09")["bat_dong"]["so_dong"] == 0


def test_nhieu_lead_mot_booking_lay_lead_som_nhat():
    """Khớp theo số điện thoại thì một khách gọi ba lần qua ba kênh sinh ba lead cùng trỏ một đơn.
    Kênh kéo được khách đến LẦN ĐẦU mới là kênh tạo ra đơn ấy."""
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    som = _cd(db, "CD-SOM", "Sớm"); muon = _cd(db, "CD-MUON", "Muộn")
    bk = _bk(db, "B1", t, u, 100)
    _lead(db, bk.customer_phone, "tiktok", muon, bk, dt.datetime(2026, 9, 10))
    _lead(db, bk.customer_phone, "facebook", som, bk, dt.datetime(2026, 9, 1))
    kq = DG.thang(db, "2026-09")
    assert [c["ma"] for c in kq["theo_chien_dich"]] == ["CD-SOM"]
    assert kq["nhieu_lead_mot_booking"] == 1


# ═════════════════════════ ĐỘ PHỦ ═════════════════════════

def test_do_phu_dem_dung_va_khong_giau_phan_chua_ro():
    db = _db()
    _nen(db)
    kq = DG.thang(db, "2026-09")
    assert kq["tong_doanh_thu"] == 1_000_000_000
    assert kq["do_phu"]["chua_ro_nguon"] == 200_000_000
    assert kq["do_phu"]["so_booking_chua_ro"] == 1
    assert abs(kq["do_phu"]["ty_le"] - 0.8) < 1e-9


def test_do_phu_liet_ke_tung_dong_chua_ro():
    """Một con số '1 booking chưa rõ nguồn' không ai sửa được; một danh sách có nút gắn thì sửa được."""
    db = _db()
    _nen(db)
    rows = DG.thang(db, "2026-09")["do_phu"]["rows"]
    assert [r["ma"] for r in rows] == ["B3"]


def test_ky_rong_khong_lam_nga_phep_chia():
    db = _db()
    kq = DG.thang(db, "2026-09")
    assert kq["tong_doanh_thu"] == 0
    assert kq["do_phu"]["ty_le"] is None, "Kỳ rỗng phải trả RỖNG, không phải 0% và không chia cho 0"


def test_booking_da_huy_khong_vao_so():
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    _bk(db, "B1", t, u, 100, nguon="zalo")
    _bk(db, "B2", t, u, 999, nguon="zalo", huy=True, sdt="0900000009")
    assert DG.thang(db, "2026-09")["tong_doanh_thu"] == 100


# ═════════════════════════ CHI PHÍ ═════════════════════════

def test_chi_chua_gan_chien_dich_KHONG_bi_chia_deu():
    """Chia đều làm bảng cân và làm mọi tỷ lệ sai cùng một lúc."""
    db = _db()
    _, _, cdA = _nen(db)
    _chi(db, "2026-09", "quang_cao", 100_000_000, cdA)
    _chi(db, "2026-09", "su_kien", 40_000_000)            # không gắn chiến dịch
    kq = DG.thang(db, "2026-09")
    assert kq["chi_marketing"]["tong_chi"] == 140_000_000
    assert kq["chi_marketing"]["chi_chua_gan"] == 40_000_000
    cd = [c for c in kq["theo_chien_dich"] if c["ma"] == "CD-A"][0]
    assert cd["chi_thuc_te"] == 100_000_000, "Chỉ nhận phần chi ĐÃ gắn đúng chiến dịch ấy"


def test_chien_dich_chua_gan_dong_chi_nao_thi_thu_tren_chi_la_RONG():
    """Rỗng khác 0. 'Chưa gắn đồng chi nào' khác hẳn 'chi mà không thu được gì'."""
    db = _db()
    _nen(db)
    cd = [c for c in DG.thang(db, "2026-09")["theo_chien_dich"] if c["ma"] == "CD-A"][0]
    assert cd["chi_thuc_te"] == 0
    assert cd["thu_tren_chi"] is None


def test_chien_dich_co_chi_ma_khong_doanh_thu_van_hien_ra():
    """Nhóm đáng xem nhất, và nó không tự hiện ra nếu chỉ duyệt theo booking."""
    db = _db()
    _nen(db)
    lo = _cd(db, "CD-LO", "Đốt tiền")
    _chi(db, "2026-09", "quang_cao", 70_000_000, lo)
    cd = [c for c in DG.thang(db, "2026-09")["theo_chien_dich"] if c["ma"] == "CD-LO"]
    assert len(cd) == 1 and cd[0]["tien"] == 0 and cd[0]["chi_thuc_te"] == 70_000_000


def test_luon_co_canh_bao_lech_ky():
    """Chi theo tháng ngân sách, thu theo tháng tour kết thúc. Bỏ câu cảnh báo là để người đọc tự vấp."""
    kq = DG.thang(_db(), "2026-09")
    assert "THÁNG NGÂN SÁCH" in kq["canh_bao_lech_ky"]
    assert "TOUR KẾT THÚC" in kq["canh_bao_lech_ky"]


# ═════════════════════════ CỬA GẮN NGUỒN — BA HÀNG RÀO ═════════════════════════

def test_gan_nguon_chi_dien_cho_TRONG():
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    mkt = _u(db, "mkt1")
    bk = _bk(db, "B1", t, u, 100, nguon="zalo")
    with pytest.raises(ValueError, match="đã có nguồn"):
        DG.gan_nguon(db, mkt, bk.id, kenh="facebook", ly_do="soát lại")


def test_gan_nguon_khong_dong_vao_booking_da_co_lead():
    """Ghi đè ô trên booking khi đã có lead là tạo ra đúng cái bất đồng màn hình sinh ra để phát hiện."""
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    mkt = _u(db, "mkt1")
    a = _cd(db, "CD-A", "A")
    bk = _bk(db, "B1", t, u, 100)
    _lead(db, bk.customer_phone, "facebook", a, bk)
    with pytest.raises(ValueError, match="lead"):
        DG.gan_nguon(db, mkt, bk.id, kenh="zalo", ly_do="soát lại")


def test_gan_nguon_bat_buoc_ghi_ly_do():
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    mkt = _u(db, "mkt1")
    bk = _bk(db, "B1", t, u, 100)
    with pytest.raises(ValueError, match="lý do"):
        DG.gan_nguon(db, mkt, bk.id, kenh="facebook", ly_do="")


def test_gan_nguon_rong_khong_gan_gi_ca():
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    mkt = _u(db, "mkt1")
    bk = _bk(db, "B1", t, u, 100)
    with pytest.raises(ValueError, match="kênh hoặc chiến dịch"):
        DG.gan_nguon(db, mkt, bk.id, ly_do="soát lại")


def test_gan_nguon_xong_thi_doanh_thu_chay_vao_dung_chien_dich_va_co_nhat_ky():
    db = _db()
    u = _u(db, "s", "nv_kd"); t = _tour(db, "T1", dt.date(2026, 9, 20))
    mkt = _u(db, "mkt1")
    a = _cd(db, "CD-A", "A")
    bk = _bk(db, "B1", t, u, 250)
    assert DG.thang(db, "2026-09")["do_phu"]["chua_ro_nguon"] == 250

    DG.gan_nguon(db, mkt, bk.id, kenh="facebook", chien_dich_id=a.id, ly_do="khách xác nhận qua FB")
    db.commit()

    kq = DG.thang(db, "2026-09")
    assert kq["do_phu"]["chua_ro_nguon"] == 0
    assert [c["ma"] for c in kq["theo_chien_dich"]] == ["CD-A"]

    from app.models.core import AuditLog
    nk = db.query(AuditLog).filter(AuditLog.action == "gan_nguon_marketing").all()
    assert len(nk) == 1, "Mỗi lần gắn nguồn phải để lại đúng một dòng nhật ký"


# ═════════════════════════ CẤU TRÚC ═════════════════════════

def test_khong_co_truy_van_doanh_thu_rieng_cho_marketing():
    """Marketing tự đếm doanh thu bằng truy vấn riêng thì sớm muộn hai bảng ra hai con số, và cuộc
    họp nào cũng mất nửa giờ cãi bên nào đúng trước khi bàn được việc.

    Đọc bằng cây cú pháp: tệp này phải gọi `doanh_thu_kd`, và KHÔNG được nhập `Tour` — mọi câu hỏi
    về chuyến đã nằm trong ống số kia rồi. (`Booking` được phép: cửa gắn nguồn ghi vào chính bảng
    ấy, đó là GHI chứ không phải đếm lại doanh thu.)
    """
    cay = ast.parse((GOC / "app" / "services" / "dong_gop_marketing.py").read_text(encoding="utf-8"))
    nhap = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            nhap.update(a.name for a in n.names)
    assert "doanh_thu_kd" in nhap, "Phải dùng lại ống số chung, không dựng ống thứ hai"
    assert "Tour" not in nhap, "Đếm lại chuyến ở đây là mở đường cho hai bảng nói hai số"


def test_cua_dung_tien_to_rieng_va_ghi_hep_hon_xem():
    from app.api.v1 import dong_gop_marketing as API
    assert API.router.prefix == "/api/v1/dong-gop-marketing"
    assert set(API.GHI) < set(API.XEM), "Nhóm ghi phải hẹp hơn nhóm xem"
    for vai in ("gd_kd", "ketoan", "bks", "robot_ks"):
        assert vai not in API.GHI, (
            f"{vai} đọc bảng này để đối chiếu, không phải người biết booking đến từ kênh nào.")


def test_man_hinh_khai_dung_mot_nhom_cua():
    from app.services.access import MAN_HINH_API
    assert MAN_HINH_API["/dong-gop-marketing"] == ("/api/v1/dong-gop-marketing",)


def test_ban_nang_cap_chi_them_cot_rong():
    tep = list((GOC / "alembic" / "versions").glob("tc77*.py"))
    assert len(tep) == 1
    s = tep[0].read_text(encoding="utf-8")
    for xau in ("bulk_insert", "INSERT INTO", "UPDATE "):
        assert xau not in s, f"Bản nâng cấp TC-77 có '{xau}' — không suy ngược nguồn cho dòng cũ."
