"""R5 · Bàn làm việc Giám đốc Kinh doanh lẻ — Chủ tịch duyệt bản xem trước 13/11/2026 03:21.

Phép thử canh những thứ dễ hỏng nhất của một bàn CHỈ ĐỌC gom số từ nhiều màn:

    1. `None` KHÁC 0 — chưa khai đơn vị Lẻ thì ô doanh thu tính chỉ tiêu là «chưa đo» kèm lý do,
       không phải 0 đồng. Khai một đơn vị thì ô ấy có số.
    2. Số trên bàn ĐỌC LẠI hàm của màn gốc, không đếm lại: thay số ở màn gốc là số trên bàn đổi.
    3. Bảy việc đúng thứ tự bản vẽ; hộp thư và chăm sóc gắn nhãn toàn công ty (Chủ tịch đồng ý).
    4. «Chuyến cần thúc bán» chỉ lấy chuyến khởi hành trong 7 ngày còn chỗ, trống nhiều đứng đầu.
    5. Ba chỗ khai vai (cửa API, MENU_ROLES, chip trên thanh dọc) không lệch nhau.
    6. Trang không viết cứng con số đo tay, không có ô nhập, không có backtick trong khối style.
"""
import datetime as dt
import pathlib
import re

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.models.crm import Conversation
from app.models.to_chuc_kd import DonViKD
from app.services import access as AC
from app.services import ban_kd_le as S
from app.services import ban_tour_le as BTL
from app.api.v1 import ban_kd_le as API

HOM_NAY = dt.date.today()
GOC = pathlib.Path(__file__).resolve().parents[2]
# R5-4: thân bàn ở components/BanGdKdLe.tsx (dùng chung cho /ban-kd-le và /fit của GĐ KD).
TRANG = (GOC / "web/components/BanGdKdLe.tsx").read_text(encoding="utf-8")
SHELL = (GOC / "web/components/Shell.tsx").read_text(encoding="utf-8")


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("nvdh", "nv_dh"), ("gdkd", "gd_kd")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _tour(db, ma, ngay, cho=20, fc=20_000_000):
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=HOM_NAY + dt.timedelta(days=ngay),
             end_date=HOM_NAY + dt.timedelta(days=ngay + 2), operator_id=_u(db, "nvdh").id,
             status="da_duyet", price_per_pax=5_000_000, fixed_cost=fc, var_cost_per_pax=2_000_000,
             planned_pax=cho, seats_open=cho)
    db.add(t); db.commit(); return t


def _ban(db, t, n):
    for i in range(n):
        r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name=f"K{i}",
                           customer_phone=f"09{t.id:03d}{i:05d}", source="web", pax=1)
        db.add(r); db.flush()
        db.add(Booking(code=f"{t.code}-B{i}", tour_id=t.id, request_id=r.id, sales_id=_u(db, "nvkd").id,
                       created_by=_u(db, "nvdh").id, customer_name=f"K{i}",
                       customer_phone=f"09{t.id:03d}{i:05d}", source="web", pax=1, amount=t.price_per_pax))
    db.commit()


def test_bay_viec_dung_thu_tu_va_nhan_toan_cong_ty():
    db = _db()
    kq = S.tong_quan(db)
    assert [v["ma"] for v in kq["viec"]] == ["chua_don_vi", "chua_du_toan", "cham_soc_qua_han", "hop_thu_cho",
                                             "sap_khoi_hanh", "lech_mang", "cho_dieu_hanh"]
    pv = {v["ma"]: v["pham_vi"] for v in kq["viec"]}
    assert pv["hop_thu_cho"] == "toan_cong_ty" and pv["cham_soc_qua_han"] == "toan_cong_ty"
    assert pv["chua_du_toan"] == "kd_le"
    # Mọi việc có số (trừ việc chờ) đều chỉ ra màn đang giữ nghiệp vụ.
    for v in kq["viec"]:
        assert v["muc"] == "cho" or v["toi"].startswith("/"), v


def test_chua_khai_don_vi_thi_cong_ca_khoi_kd_khai_roi_thi_theo_cay():
    db = _db()
    # R5-9 (Chủ tịch 13/11/2026 «GĐ tính cả khối KD»): chưa có đơn vị Lẻ thì cộng cả khối KD — có số thật
    # (ở đây 0 vì chưa bán booking nào), không còn để trống.
    kq = S.tong_quan(db)
    o = kq["the"]["doanh_thu_chi_tieu"]
    assert kq["doanh_thu_pham_vi"] == "ca_khoi_kd" and o["so"] is not None and o["ly_do"] == ""
    db.add(DonViKD(ma="LE-1", ten="Phòng Lẻ 1", cap="phong", mang="le", hieu_luc_tu=HOM_NAY - dt.timedelta(days=30)))
    db.commit()
    o = S.tong_quan(db)["the"]["doanh_thu_chi_tieu"]
    assert o["so"] is not None and o["ly_do"] == ""


def test_so_doc_lai_tu_man_goc_khong_dem_lai():
    db = _db()
    _tour(db, "LE-GAN", 3, cho=10); _ban(db, _tour(db, "LE-XA", 30, cho=10), 4)
    _tour(db, "LE-KHONG-DT", 5, cho=8, fc=0)
    goc = BTL.ban_lam_viec(db)["tong"]
    kq = S.tong_quan(db)
    assert kq["the"]["chuyen_dang_ban"]["so"] == goc["chuyen"] == 3
    assert kq["the"]["cho_con"]["so"] == goc["cho_con"]
    assert kq["the"]["sap_khoi_hanh"]["so"] == goc["sap_khoi_hanh"] == 2
    viec = {v["ma"]: v for v in kq["viec"]}
    assert viec["chua_du_toan"]["so"] == goc["chua_du_co_so"]
    # Hộp thư: đếm hội thoại khách nhắn chưa ai trả lời.
    db.add(Conversation(channel="facebook", external_id="a", unanswered=True))
    db.add(Conversation(channel="facebook", external_id="b", unanswered=False))
    db.commit()
    assert {v["ma"]: v for v in S.tong_quan(db)["viec"]}["hop_thu_cho"]["so"] == 1


def test_chuyen_can_thuc_ban_chi_lay_7_ngay_con_cho_trong_nhieu_dung_dau():
    db = _db()
    a = _tour(db, "LE-A", 2, cho=10); _ban(db, a, 8)        # còn 2
    b = _tour(db, "LE-B", 6, cho=40)                         # còn 40
    c = _tour(db, "LE-C", 4, cho=5); _ban(db, c, 5)          # kín chỗ — không thúc
    _tour(db, "LE-D", 20, cho=40)                            # xa — không thúc
    ma = [r["code"] for r in S.tong_quan(db)["thuc_ban"]]
    assert ma == ["LE-B", "LE-A"]


def test_ba_cho_khai_vai_khop_nhau():
    # R5-5: bàn chỉ còn ở /fit; hàng rào thật là API.XEM, nhóm API tới được qua /fit, và mọi vai của bàn mở được /fit.
    menu = set(API.XEM)
    assert "/api/v1/ban-kd-le" in AC.MAN_HINH_API["/fit"]
    assert "/ban-kd-le" not in AC.MENU_ROLES
    assert menu <= set(AC.MENU_ROLES["/fit"]), "vai của bàn mà không mở được /fit"
    assert set(API.XEM) == menu
    m = re.search(r"export const VAI_BAN_KD_LE = \[([^\]]*)\]", SHELL)
    assert m, "Shell.tsx mất VAI_BAN_KD_LE"
    assert set(re.findall(r'"([a-z_]+)"', m.group(1))) == menu
    # Chip «Kinh doanh lẻ» đi qua hàm theo vai, không gọi thẳng đường cố định.
    assert "href={duongPhongTheoVai(p.khoa, vai)}" in SHELL
    for vai in ("tp_kd", "tn_kd", "nv_kd"):
        assert vai not in menu, f"{vai} chưa được vào bàn ở đợt này (Chủ tịch chốt 13/11/2026)"


def test_trang_chi_doc_khong_so_viet_cung():
    assert 'api("/ban-kd-le/tong-quan")' in TRANG
    for so in ("167", "5.694", "5694", "1.667", "1667", "2.144", "2144"):
        assert so not in TRANG, f"trang viết cứng con số đo tay {so}"
    assert "<input" not in TRANG and "<select" not in TRANG and "<textarea" not in TRANG
    assert 'method: "POST"' not in TRANG
    khoi = TRANG.split("<style>{`", 1)[1].split("`}</style>", 1)[0]
    assert "`" not in khoi
    # Ô null in «chưa đo», không in 0.
    assert "chưa đo" in TRANG
    # Trang con mở TRONG bàn, không nhảy màn.
    assert "<KhungNhung" in TRANG and "window.location.assign(\"/\")" in TRANG
    assert "/sales-admin" not in TRANG, "Sales Admin làm đợt riêng"


def test_ba_con_so_dong_luc_tren_tung_chuyen():
    """R5-4 · hòa vốn, lãi ngưỡng biên, lãi khi bán đủ 45 khách — chỉ khi đủ ba con số dự toán."""
    db = _db()
    t = _tour(db, "LE-DL", 3, cho=50, fc=20_000_000)   # p 5tr, v 2tr, f 20tr
    _ban(db, t, 5)
    r = BTL.ban_lam_viec(db)["rows"][0]
    assert r["khach_hoa_von"] == 7                      # 20/(5-2) = 6,67 → 7
    # lãi ≥ 10%: n ≥ 20 / (0,9·5 − 2) = 8
    assert r["khach_dat_bien"] == 8 and abs(r["bien_muc_tieu"] - 0.10) < 1e-9
    assert r["khach_toi_da"] == 45                      # chuyến 50 chỗ → trần 45
    assert abs(r["bien_khi_day"] - ((3 * 45 - 20) / (5 * 45))) < 1e-9
    nho = _tour(db, "LE-NHO", 4, cho=10, fc=20_000_000)
    r2 = [x for x in BTL.ban_lam_viec(db)["rows"] if x["code"] == "LE-NHO"][0]
    assert r2["khach_toi_da"] == 10, "chuyến mở ít chỗ hơn 45 thì tính theo số chỗ mở"
    kd = _tour(db, "LE-KHONG", 5, cho=20, fc=0)
    t3 = db.get(Tour, kd.id); t3.var_cost_per_pax = 0; db.commit()
    r3 = [x for x in BTL.ban_lam_viec(db)["rows"] if x["code"] == "LE-KHONG"][0]
    if r3["trang_thai_cong"] == "chua_du_co_so":
        assert r3["khach_hoa_von"] is None and r3["bien_khi_day"] is None, "thiếu dự toán thì None, không 0"


def test_phai_thu_le_chia_theo_ngay_khoi_hanh():
    db = _db()
    a = _tour(db, "LE-PT", 10, cho=20); _ban(db, a, 2)   # 2 booking × 5tr, chưa thu
    pt = S.phai_thu_le(db)
    assert pt["tong"] == 10_000_000 and pt["so_booking"] == 2
    assert pt["nhom"]["2 tuần"] == 10_000_000
    for bk in a.bookings:
        bk.paid = bk.amount
    db.commit()
    assert S.phai_thu_le(db)["tong"] is None, "không ai nợ thì None kèm lý do, không phải 0"


def test_r5_5_mot_duong_dan():
    """R5-5 · Chủ tịch «ok sửa»: một bàn, một đường dẫn — /ban-kd-le chỉ chuyển về /fit, thanh dọc không còn mục riêng."""
    trang = (GOC / "web/app/ban-kd-le/page.tsx").read_text(encoding="utf-8")
    assert 'location.replace("/fit")' in trang and "BanGdKdLe" not in trang and len(trang) < 400
    assert '"/ban-kd-le"]' not in SHELL, "thanh dọc còn mục Bàn làm việc GĐ Kinh doanh lẻ riêng"
    assert 'h.startsWith("/ban-kd-le")' not in TRANG
