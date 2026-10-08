# -*- coding: utf-8 -*-
"""KQ-2 · VIETRIP LÀM THẾ NÀO THÌ VTOS THEO VẬY — doanh thu của chuyến chưa đóng số.

    "có bao nhiêu số liệu trên vietrip em cứ nối về vtos, ko cần phải đóng sổ, nghĩa là vietrip
     làm như thế nào thì vtos theo vậy"                        — Chủ tịch, 08/10/2026

ĐÂY LÀ MỘT LỖI ĐƯỢC VÁ, KHÔNG PHẢI MỘT LUẬT MỚI. Luật A (TC-71, 18/9) đã quyết rằng chuyến đã khởi
hành mà chưa đóng số thì CŨNG ĐƯỢC CỘNG, vì "670 chuyến đã chạy xong, có doanh thu thật trong máy,
tổng 24,38 tỷ — nhưng không hiện ở đâu trên màn hình chủ tịch". Luật ấy kéo đúng những chuyến ấy
vào tập cộng, rồi đọc doanh thu của chúng ở `tours.actual_revenue` — nơi mà
`services/vietrip.apply_tours` vừa GHI SỐ 0 vào cho mọi chuyến Vietrip chưa quyết toán. Chuyến vào
được tập cộng mà mang theo 0 đồng. Đo trên bàn chạy thật 08/10/2026: 637 chuyến đã khởi hành chưa
đóng số, sổ booking mang 24.490.260.789 đ; khối Doanh thu của Chủ tịch hiện tháng 9 là 8,51 tỷ
trong khi sổ booking tháng 9 là 17,1 tỷ.

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ HỎNG CỦA ĐÚNG BẢN VÁ NÀY — mỗi phép thử canh một chỗ
══════════════════════════════════════════════════════════════════════════════════════════════
1. CỘNG ĐÚP. Chuyến đã đóng số có CẢ sổ quyết toán CẢ sổ booking của chính nó. Cộng cả hai là
   nhân đôi doanh thu của mọi chuyến đã quyết toán — và tổng vẫn trông hợp lý nên không ai nhìn
   ra. Phải là CHỌN MỘT. (`kq2_1`)
2. GHI ĐÈ SỐ NGƯỜI ĐÃ NHẬP. Chuyến Kế toán trả lại có `closed_at = None` nhưng GIỮ hai cột tiền.
   Đọc booking thay cho con số ấy là ném đi một con số nhập tay. Sổ Vietrip là chỗ LÙI VỀ, không
   phải chỗ ghi đè. (`kq2_2`)
3. BIÊN 100%. Chuyến có booking mà chưa có dòng chi phí nào: cho nó vào cột chính là báo lãi bằng
   đúng toàn bộ doanh thu. Luật TC-47 — cột chính chỉ gồm chuyến ĐỦ SỐ — không được nới. (`kq2_3`)
4. GHI NHẬN TRƯỚC DOANH THU. Chuyến tháng sau chưa chạy mà đã cộng là sai ở mọi chuẩn kế toán.
   Luật A vốn đã chặn; bản vá này không được mở ra. (`kq2_4`)

5. BIÊN LỢI NHUẬN THÀNH PHÉP CHIA GIỮA HAI TẬP. Từ 08/10, cột doanh thu đi hết tập chuyến còn
   cột lãi chỉ đi tập có giá vốn (Chủ tịch: *"ý của anh là lấy số liệu y chang của vietrip"* —
   luật TC-47 "hai cột cùng một tập" bị đảo, ghi cả hai bên ở `ket_qua_that`). Chia hai ô ấy cho
   nhau là lấy tử của tập này trên mẫu của tập kia. Mẫu số thật PHẢI trả ra riêng, có tên, và
   phải đúng — nếu không thì đây là lỗi TC-45 nguyên bản chứ không phải một luật mới. (`kq2_8`)

`kq2_5` là phép thử canh chính bản vá: tắt sổ Vietrip đi thì con số phải TỤT lại đúng như trước.
Không có nó thì một bản sửa chẳng làm gì cả cũng xanh y như bản sửa đúng.
"""
import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Company, Tour, User
from app.models.vietrip import TourCostLine
from app.services import ket_qua_that as KQ
from app.services import lai_lo_tour as LL


def _db():
    """Kho rỗng trong bộ nhớ — cùng cách dựng với TC-44/45/46/47."""
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _so_gia():
    """Tháng 8/2026, năm chuyến dựng đúng những hình có thật trong kho sau một đêm robot chạy."""
    db = _db()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    db.add(me); db.commit()
    u = User(username="dh", full_name="Điều hành", role="nv_dh", password_hash="x")
    db.add(u); db.commit()

    def tour(code, rev, cost, closed, status, ngay=dt.date(2026, 8, 1)):
        t = Tour(code=code, name=code, tour_type="package", start_date=ngay,
                 end_date=ngay + dt.timedelta(days=2), operator_id=u.id, status=status,
                 actual_revenue=rev, actual_cost=cost, closed_at=closed, company_id=me.id)
        db.add(t); db.commit()
        return t

    def booking(t, tien, ma):
        db.add(Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                       customer_name="K", customer_phone="", source="vietrip", pax=1,
                       amount=tien, discount=0.0, cancelled=False))
        db.commit()

    def chi_phi(t, tien):
        db.add(TourCostLine(tour_id=t.id, line_no=1, description="Land", actual=tien,
                            status="hd", source="vietrip"))
        db.commit()

    ra = {}
    # A · ĐÃ ĐÓNG SỐ, và có cả booking. Chỗ hỏng 1: doanh thu phải là 100 (sổ quyết toán), KHÔNG
    #     phải 100 + 900. Booking dựng lệch hẳn con số quyết toán để cộng đúp là lộ ngay.
    ra["A"] = tour("A", 100.0, 60.0, dt.datetime(2026, 8, 10), "da_dong_so")
    booking(ra["A"], 900.0, "BK-A")

    # B · CHƯA ĐÓNG SỐ, hai cột tiền bị `apply_tours` ghi số 0, có booking VÀ có dòng chi phí.
    #     Đây là hình của chuyến mà vòng này sinh ra để cứu: phải vào cột chính.
    ra["B"] = tour("B", 0.0, 0.0, None, "ket_thuc")
    booking(ra["B"], 500.0, "BK-B")
    chi_phi(ra["B"], 300.0)

    # C · CHƯA ĐÓNG SỐ, có booking, KHÔNG có dòng chi phí nào. Chỗ hỏng 3: ra khúc mờ, không vào
    #     cột chính.
    ra["C"] = tour("C", 0.0, 0.0, None, "ket_thuc")
    booking(ra["C"], 70.0, "BK-C")

    # D · KẾ TOÁN TRẢ LẠI: `closed_at` rỗng nhưng hai cột tiền còn nguyên số người đã nhập.
    #     Chỗ hỏng 2: booking 999 KHÔNG được ghi đè lên 40.
    ra["D"] = tour("D", 40.0, 20.0, None, "ket_thuc")
    booking(ra["D"], 999.0, "BK-D")

    # E · CHƯA KHỞI HÀNH. Chỗ hỏng 4: không được cộng dù có đủ booking và chi phí.
    #
    # NGÀY TÍNH TỪ `date.today()`, KHÔNG GÕ CỨNG. Bản đầu của tệp này gõ 20/9/2026 và phép thử đỏ
    # ngay hôm viết, vì hôm nay đã là 07/10 — ngày 20/9 là một ngày ĐÃ khởi hành. Một phép thử
    # canh "chưa tới ngày" bằng một ngày gõ cứng thì hoặc đỏ hôm nay, hoặc đỏ vào một ngày nào đó
    # sau này mà không ai hiểu vì sao; cả hai đều tệ hơn là tính từ hôm nay.
    ra["mai"] = dt.date.today() + dt.timedelta(days=30)
    ra["E"] = tour("E", 0.0, 0.0, None, "da_duyet", ra["mai"])
    booking(ra["E"], 800.0, "BK-E")
    chi_phi(ra["E"], 100.0)
    return db, ra


# ═════════════════ 1 · CHỌN MỘT SỔ, KHÔNG CỘNG HAI SỔ ═════════════════

def test_kq2_1_chuyen_da_dong_so_doc_so_quyet_toan_chu_khong_cong_them_booking():
    """Chỗ hỏng 1 — chỗ nguy hiểm nhất của vòng này, vì tổng cộng đúp vẫn trông hợp lý."""
    db, ra = _so_gia()
    so = KQ.so_cua_chuyen(db, [ra["A"]])
    assert so[ra["A"].id] == (100.0, 60.0), (
        "Chuyến đã đóng số phải đọc ĐÚNG sổ quyết toán. Ra 1000 nghĩa là đang cộng cả booking — "
        f"nhân đôi doanh thu của mọi chuyến đã quyết toán. {so}")


def test_kq2_2_so_vietrip_la_cho_lui_ve_khong_phai_cho_ghi_de():
    """Chỗ hỏng 2. Kế toán trả lại chuyến thì `closed_at` rỗng mà hai cột tiền còn nguyên."""
    db, ra = _so_gia()
    so = KQ.so_cua_chuyen(db, [ra["D"]])
    assert so[ra["D"].id] == (40.0, 20.0), (
        "Chuyến Kế toán trả lại vẫn giữ số người đã nhập tay (40/20). Ra 999 là booking đã ghi đè "
        f"lên một con số có người chịu trách nhiệm. {so}")


# ═════════════════ 2 · CỨU ĐƯỢC CHUYẾN BỊ GHI 0, MÀ KHÔNG NỚI LUẬT ĐỦ SỐ ═════════════════

def test_kq2_3_chuyen_bi_ghi_0_nay_vao_doanh_thu_con_lai_thi_chi_tap_du_so():
    """Chỗ hỏng 3, và là phần việc chính của vòng.

    Doanh thu đi HẾT (A + B + C + D); lãi chỉ tập có giá vốn (A + B + D). Chuyến C vẫn đếm riêng
    để vẽ khúc mờ và để nêu tên bộ phận đi nhập, nhưng nó KHÔNG được góp một đồng lãi nào.
    """
    db, ra = _so_gia()
    r = KQ.thang(db, "2026-08")
    # A 100 (sổ quyết toán) + B 500 (sổ booking) + C 70 (booking, chưa có giá vốn) + D 40 = 710.
    assert r["doanh_thu"] == 710.0, (
        "Chuyến B bị `apply_tours` ghi 0 vào hai cột tiền nhưng có booking 500 và dòng chi phí "
        "300; chuyến C có booking 70 mà chưa có giá vốn — Chủ tịch chốt 08/10 là lấy y chang của "
        f"Vietrip nên CẢ HAI vào doanh thu. Ra 140 nghĩa là bản vá chưa chạy. {r['doanh_thu']}")
    assert r["lai_tour"] == 40.0 + 200.0 + 20.0, (
        "Lãi KHÔNG được nhận chuyến C: Vietrip chưa có một dòng chi phí nào của nó, cho nó vào là "
        "báo lãi 100% trên 70 đồng — đúng lỗi TC-47 chỗ hỏng số 1, luật ấy KHÔNG bị đảo.")
    assert r["dt_co_gia_von"] == 640.0, "Mẫu số của cột lãi: A + B + D, không có C."
    assert r["thieu_gia_von"] == 1 and r["dt_thieu_gia_von"] == 70.0, (
        "Chuyến C vẫn phải đếm được RIÊNG — hình vẽ cột đặc 640 rồi nối khúc mờ 70 cho đủ 710.")


def test_kq2_4_chuyen_chua_khoi_hanh_van_khong_duoc_cong():
    """Chỗ hỏng 4. Luật A chỉ nhận chuyến ĐÃ khởi hành; bản vá không được nới chỗ ấy."""
    db, ra = _so_gia()
    r = KQ.thang(db, f"{ra['mai']:%Y-%m}")
    assert r["doanh_thu"] is None, (
        f"Chuyến E khởi hành {ra['mai']} (còn 30 ngày nữa) có booking 800 và chi phí 100. Cộng nó "
        f"là ghi nhận trước doanh thu — sai ở mọi chuẩn kế toán. {r['doanh_thu']}")
    assert r["du_so"] == 0 and r["chuyen_chua_dong_so"] == 0


# ═════════════════ 3 · PHÉP THỬ CANH CHÍNH BẢN VÁ ═════════════════

def test_kq2_5_tat_so_vietrip_di_thi_con_so_phai_tut_lai_nhu_cu():
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA TỆP NÀY.

    Con số phải lên VÌ ĐỌC SỔ VIETRIP, không phải vì một lý do nào khác tình cờ cũng cho ra 640.
    Thay `so_theo_vietrip` bằng một hàm trả rỗng — đúng trạng thái trước bản vá — thì B phải rời
    cột chính và doanh thu tụt về 140. Không có phép thử này thì một bản sửa chẳng làm gì cả cũng
    xanh y như bản sửa đúng.
    """
    db, ra = _so_gia()
    that = LL.so_theo_vietrip
    try:
        LL.so_theo_vietrip = lambda db_, tours: {t.id: (None, None) for t in tours}
        r = KQ.thang(db, "2026-08")
        # CỘT ĐẶC tụt về 100 (chỉ còn A, chuyến đã đóng số): `so_theo_vietrip` cấp CẢ giá vốn cho
        # chuyến chưa đóng số, nên tắt nó đi thì B, C, D đều mất giá vốn và rời tập `du`. Ghi rõ
        # ra đây vì đó là điều phép thử này VÔ TÌNH phát hiện và đáng nói: cả ba chuyến chưa đóng
        # số đều đi qua MỘT cửa duy nhất.
        assert r["dt_co_gia_von"] == 100.0, (
            "Tắt sổ Vietrip mà mẫu số của cột lãi vẫn 640 — nghĩa là giá vốn không đến từ sổ "
            f"Vietrip và phép thử kq2_3 đang xanh vì một lý do khác. {r['dt_co_gia_von']}")
        assert r["lai_tour"] == 40.0, "Chỉ còn lãi của chuyến A."
        # DOANH THU tụt về 140: A (100, sổ quyết toán) + D (40, số nhập tay còn trên hàng). B và C
        # chỉ có booking nên mất hẳn — đúng trạng thái trước bản vá.
        assert r["doanh_thu"] == 140.0, (
            f"Tắt sổ Vietrip thì B (500) và C (70) phải mất khỏi doanh thu. {r['doanh_thu']}")
        assert r["thieu_gia_von"] == 3
    finally:
        LL.so_theo_vietrip = that
    assert KQ.thang(db, "2026-08")["doanh_thu"] == 710.0


def test_kq2_6_hai_nua_cong_lai_bang_tong_cua_ca_thang():
    """Hai nửa `dt_da_dong_so` / `dt_chua_dong_so` là thứ giữ cho con số gộp đối chiếu ngược được
    về sổ kế toán (xem luật A ở đầu `ket_qua_that`). Chúng phải cộng đủ CẢ phần khúc mờ, nếu không
    ngày kiểm toán hỏi chỗ chênh nằm ở đâu thì không ai chỉ ra được."""
    db, ra = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["dt_da_dong_so"] == 100.0
    assert r["dt_chua_dong_so"] == 500.0 + 70.0 + 40.0
    # Từ 08/10 `doanh_thu` đã gồm phần thiếu giá vốn, nên đẳng thức gọn lại đúng bằng nó.
    assert r["dt_da_dong_so"] + r["dt_chua_dong_so"] == r["doanh_thu"] == 710.0
    assert r["chuyen_da_dong_so"] == 1 and r["chuyen_chua_dong_so"] == 3


def test_kq2_7_doanh_thu_theo_mang_cong_lai_bang_cot_chinh():
    """`theo_mang` là thứ màn hình Chủ tịch in ra theo phòng. Nó chia ĐÚNG tập đã cộng ra
    `doanh_thu`, nên tổng các ngăn phải bằng cột chính — hai con số trên cùng một màn hình mà
    không cộng lại được với nhau là lỗi TC-98 vừa sửa ngày 07/10."""
    db, ra = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert sum(v["doanh_thu"] for v in r["theo_mang"].values()) == r["doanh_thu"]
    # `du_so_dt` chứ không `du_so`: từ 08/10 cột doanh thu rộng hơn tập có giá vốn, và `theo_mang`
    # chia theo cột doanh thu. So với `du_so` thì phép thử này đỏ đúng vào bản sửa đúng.
    assert sum(v["chuyen"] for v in r["theo_mang"].values()) == r["du_so_dt"] == 4


# ═════════════════ 4 · LUẬT BỊ ĐẢO PHẢI GÁNH LẠI LÝ DO CỦA LUẬT CŨ ═════════════════

def test_kq2_8_bien_loi_nhuan_van_tinh_dung_duoc_du_hai_cot_khac_tap():
    """Chỗ hỏng 5 — cái giá của việc đảo luật TC-47, và chỗ phải trả giá ấy.

    Luật cũ bắt hai cột cùng một tập VÌ người đọc sẽ chia chúng cho nhau. Lệnh 08/10 làm cột
    doanh thu rộng hơn cột lãi, nên phép chia `lai_tour / doanh_thu` từ nay SAI — và điều giữ cho
    việc đảo luật này không thành lỗi TC-45 là `dt_co_gia_von`: mẫu số thật, có tên, trả ra riêng.

    Phép thử dựng đúng cái bẫy: biên đọc sai là 260/710 = 36,6%, biên thật là 260/640 = 40,6%.
    """
    db, ra = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["dt_co_gia_von"] is not None, (
        "Thiếu mẫu số thì không ai tính được biên đúng, và mọi màn hình sẽ tự chia bằng "
        "`doanh_thu` — tức tái tạo đúng lỗi mà luật cũ sinh ra để chặn.")
    assert r["dt_co_gia_von"] < r["doanh_thu"], (
        "Bộ số giả phải có chuyến thiếu giá vốn, nếu không phép thử này xanh mà không chứng minh "
        "được gì.")
    assert abs(r["lai_tour"] / r["dt_co_gia_von"] - 260.0 / 640.0) < 1e-12
    # Và nói ra con số sai để người đọc sau này thấy khoảng cách: 2,1 điểm phần trăm trên bộ số
    # giả này: 4 điểm phần trăm. Trên bàn chạy thật tháng 9, phần thiếu giá vốn là 10,58 tỷ
    # trong 116 chuyến đã khởi hành chưa đóng số — tức phần lớn cột doanh thu không có lãi đi kèm.
    assert abs(r["lai_tour"] / r["doanh_thu"] - 260.0 / 710.0) < 1e-12

    # RỖNG KHÁC KHÔNG ở đây nữa: tháng chưa chuyến nào đủ số thì mẫu số là None, không phải 0 —
    # chia cho 0 và chia cho "chưa biết" là hai việc khác nhau.
    rong = KQ.thang(db, f"{ra['mai']:%Y-%m}")
    assert rong["dt_co_gia_von"] is None and rong["lai_tour"] is None
