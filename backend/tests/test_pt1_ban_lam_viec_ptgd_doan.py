"""PT-1 · Bàn làm việc của Phó TGĐ tour đoàn — hàng rào, 24/9/2026.

Màn hình này không thêm quyền nào. Nó làm cho một quyền đã có (Điều 4: tour đoàn → `ptgd_doan`
duyệt) nhìn thấy được. Vì thế thứ đáng canh KHÔNG phải "có hiện ra không" mà là BỐN chỗ hỏng mà
nhìn màn hình không phát hiện được:

 1. TOUR LẺ LỌT VÀO HÀNG ĐỢI CỦA NGƯỜI KHÔNG KÝ NÓ. Tour lẻ do Tổng giám đốc duyệt. Lọt vào đây thì
    P.TGĐ bấm ký và nhận 403 — hoặc tệ hơn, tưởng mình đã ký rồi.

 2. CHUYẾN DƯỚI BIÊN NẰM CHUNG HÀNG ĐỢI. Chuyến dưới ngưỡng biên phải đủ chữ ký Chủ tịch VÀ TGĐ.
    Trộn chung là vẽ ra một nút bấm vào sẽ hỏng; `test_pt3` ghim chúng ở khối riêng và ghim rằng
    khối ấy tự khai `toi_khong_ky_duoc`.

 3. "ĐỦ TRƯỜNG" NÓI DỐI. Danh sách thiếu phải tính lại từ chính luật của bước trình. Nếu nó là một
    bản chép tay thì ngày `tours.submit` siết thêm điều kiện, màn hình vẫn báo đủ cho một hồ sơ mà
    bước trình sẽ từ chối. `test_pt4` dựng đúng ba kiểu thiếu và đòi gọi tên từng kiểu.

 4. THƯỚC ĐO QUÁ HẠN TỰ LÀNH. Nếu chỉ đếm chuyến CHƯA đóng sổ thì mỗi lần ai đó đóng muộn một
    chuyến, con số tự đẹp lên — cái nó đo được thì biến mất. `test_pt5` đòi chuyến đóng muộn vẫn
    được đếm, ở một ngăn riêng.
"""
import datetime as dt
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour
from app.services import ptgd_doan as P
from app.services import rules as R

HOM_NAY = dt.date.today()


def _chi_ma(s: str) -> str:
    """Bỏ chuỗi tài liệu và chú thích, chỉ còn mã chạy được.

    Cần thật: phép thử dưới đây soi mã nguồn tìm chữ `tour_type`, mà chính chú thích giải thích vì
    sao KHÔNG được dùng `tour_type` lại chứa đúng chữ ấy. Soi cả chú thích thì một lời giải thích
    đúng cũng làm hàng rào đỏ, và người sửa sẽ học cách xoá lời giải thích đi cho xanh.
    """
    s = re.sub(r'"""[\s\S]*?"""', "", s)
    return re.sub(r"#[^\n]*", "", s)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _tour(db, ma, loai="doan_noi_dia", trang_thai="cho_duyet", **kw):
    """Dự toán mặc định ĐỦ TRƯỜNG và TRÊN biên: giá 10tr/khách, 50 khách, giá vốn 400tr → biên 20%."""
    mac_dinh = dict(price_per_pax=10_000_000.0, planned_pax=50, fixed_cost=100_000_000.0,
                    var_cost_per_pax=6_000_000.0, rest_stops="Trạm dừng Tân Phú", justification="")
    mac_dinh.update(kw)
    t = Tour(code=ma, name=ma, tour_type=loai,
             start_date=HOM_NAY + dt.timedelta(days=20), end_date=HOM_NAY + dt.timedelta(days=24),
             operator_id=1, status=trang_thai, **mac_dinh)
    db.add(t); db.commit()
    return t


# ───────────────────────────── PT-1 · định tuyến duyệt ─────────────────────────────

def test_pt1_chi_doan_vao_hang_doi_cua_ptgd_doan():
    db = _db()
    _tour(db, "MICE-A")
    _tour(db, "LE-B", loai="le_noi_dia")
    ma = [d["ma"] for d in P.cho_toi_duyet(db)]
    assert ma == ["MICE-A"], f"hàng đợi ra {ma} – tour lẻ do Tổng giám đốc duyệt, không được lọt vào đây"


def test_pt1b_hang_doi_hoi_lai_chinh_luat_dinh_tuyen_chu_khong_doan_theo_loai_chuyen():
    """Ghim CÁCH lọc, không chỉ ghim kết quả.

    `rules.approver_role` là nơi duy nhất định nghĩa "đoàn thì ai duyệt". Một ngày nào đó mã MICE
    được coi là đoàn dù `tour_type` ghi lẻ (đúng như `rules.is_doan` đã mô tả) — lúc ấy hàng đợi
    phải đi theo, và nó chỉ đi theo nếu nó hỏi lại hàm kia thay vì tự đọc `tour_type`.
    """
    db = _db()
    t = _tour(db, "MICE-2610-001")
    assert R.approver_role(t) == "ptgd_doan"
    nguon = open(P.__file__, encoding="utf-8").read()
    than = _chi_ma(nguon[nguon.find("def cho_toi_duyet"):nguon.find("def duoi_bien_cho_hai_chu_ky")])
    assert "approver_role" in than, "hàng đợi phải hỏi rules.approver_role, đừng dựng định nghĩa 'đoàn' thứ hai"
    assert "tour_type" not in than, "đọc thẳng tour_type ở đây là bản sao thứ hai của luật phân mảng"


def test_pt2_chi_lay_trang_thai_cho_duyet():
    db = _db()
    _tour(db, "MICE-NHAP", trang_thai="nhap")
    _tour(db, "MICE-XN", trang_thai="cho_xac_nhan")
    _tour(db, "MICE-DUYET", trang_thai="da_duyet")
    _tour(db, "MICE-CHO", trang_thai="cho_duyet")
    assert [d["ma"] for d in P.cho_toi_duyet(db)] == ["MICE-CHO"]


# ───────────────────────────── PT-3 · dưới biên tách riêng ─────────────────────────────

def test_pt3_duoi_bien_ra_khoi_hang_doi_chinh_va_tu_khai_khong_ky_duoc():
    db = _db()
    _tour(db, "MICE-TREN")
    # Giá vốn cao → biên mỏng. `below_margin` là cờ do bước trình đặt; dựng thẳng để khỏi phải chạy
    # cả luồng trình chỉ để có một dòng dữ liệu.
    _tour(db, "MICE-DUOI", var_cost_per_pax=9_400_000.0, below_margin=True,
          justification="Khách cũ, đoàn thứ tư trong năm, bù bằng đoàn tháng sau, lỗ tối đa 20tr")
    chinh = [d["ma"] for d in P.cho_toi_duyet(db)]
    duoi = P.duoi_bien_cho_hai_chu_ky(db)
    assert chinh == ["MICE-TREN"], f"hàng đợi ký của P.TGĐ ra {chinh} – chuyến dưới biên không được nằm đây"
    assert [d["ma"] for d in duoi] == ["MICE-DUOI"]
    assert duoi[0]["toi_khong_ky_duoc"] is True, (
        "khối dưới biên phải TỰ KHAI trên dữ liệu rằng P.TGĐ không ký được – để màn hình tự đoán "
        "là sớm muộn có một màn hình đoán sai và vẽ ra nút ký"
    )


def test_pt3b_duoi_bien_noi_ro_con_thieu_chu_ky_nao_va_mot_chu_ky_chua_phai_la_gan_xong():
    """ĐỔI Ở ĐỢT LG3, vì NGƯỜI KÝ đổi chứ không vì phép thử sai.

    Bảng này từng đòi "Chủ tịch" và "Tổng giám đốc". Chuyến dưới biên nay do NGƯỜI ĐỨNG ĐẦU
    PHÒNG BÁN ký (Chủ tịch chốt 11/10/2026), và mã `MICE-` là mảng Đoàn, nên người thứ nhất là
    P.TGĐ tour đoàn. Chữ ký Chủ tịch trên một chuyến cũ vẫn còn trong sổ, nhưng nó không còn
    đếm vào luật hiện hành — nên chuyến D1 dưới đây ký bằng ĐÚNG vai của luật mới.

    ĐÂY LÀ MỘT LỖI LG2 ĐỂ LẠI VÀ LG3 SỬA: bảng việc viết thẳng hai cái tên, nên từ 11/10/2026
    nó báo sai tên người cần ký và đẩy người đọc đi gõ nhầm cửa.
    """
    db = _db()
    _tour(db, "MICE-D1", var_cost_per_pax=9_400_000.0, below_margin=True, signed_ptgd_doan=True,
          justification="Giải trình đủ bốn mục cho chuyến dưới biên, dài hơn ba mươi ký tự")
    _tour(db, "MICE-D2", var_cost_per_pax=9_400_000.0, below_margin=True,
          justification="Giải trình đủ bốn mục cho chuyến dưới biên, dài hơn ba mươi ký tự")
    theo_ma = {d["ma"]: d for d in P.duoi_bien_cho_hai_chu_ky(db)}
    assert theo_ma["MICE-D1"]["chu_ky_con_thieu"] == ["Tổng giám đốc"]
    assert theo_ma["MICE-D2"]["chu_ky_con_thieu"] == ["Phó TGĐ tour đoàn", "Tổng giám đốc"]

    # KHÔNG có trường nào kiểu "gan_xong" / "phan_tram": hai chữ ký thì một chữ ký là chưa có gì,
    # và một thanh tiến độ 50% trên màn hình người ký là một lời trấn an sai.
    assert not any(k for k in theo_ma["MICE-D1"] if "gan_xong" in k or "phan_tram" in k)


# ───────────────────────────── PT-4 · "đủ trường" phải nói thật ─────────────────────────────

def test_pt4_ba_kieu_thieu_deu_duoc_goi_ten():
    db = _db()
    _tour(db, "MICE-DU")
    _tour(db, "MICE-THIEU-DUNG-NGHI", rest_stops="")
    _tour(db, "MICE-THIEU-GIA-VON", fixed_cost=0.0, var_cost_per_pax=0.0)
    _tour(db, "MICE-THIEU-GIAI-TRINH", var_cost_per_pax=9_400_000.0, justification="ngắn")
    theo_ma = {d["ma"]: d["thieu"] for d in P.cho_toi_duyet(db)}
    assert theo_ma["MICE-DU"] == []
    assert "điểm dừng nghỉ" in theo_ma["MICE-THIEU-DUNG-NGHI"]
    assert any("chi phí" in x for x in theo_ma["MICE-THIEU-GIA-VON"]), theo_ma["MICE-THIEU-GIA-VON"]
    assert any("giải trình" in x for x in theo_ma["MICE-THIEU-GIAI-TRINH"]), theo_ma["MICE-THIEU-GIAI-TRINH"]


def test_pt4b_thieu_gia_von_khong_bao_gio_ra_bien_100_phan_tram():
    """Ý kiến thẩm định 06/9/2026 mục B1: giá vốn 0 từng cho biên 100% nên cổng biên luôn ĐẠT.

    Màn hình người ký là chỗ lỗi ấy đắt nhất: một con số biên rất đẹp nằm ngay cạnh nút duyệt.
    """
    db = _db()
    _tour(db, "MICE-0", fixed_cost=0.0, var_cost_per_pax=0.0)
    d = P.cho_toi_duyet(db)[0]
    assert d["thieu"], "dự toán không có giá vốn phải bị gọi tên là thiếu, không được coi là đủ"


def test_pt4c_dem_tach_rieng_so_ho_so_du_truong_va_so_sap_khoi_hanh():
    db = _db()
    _tour(db, "MICE-DU-XA")
    t = _tour(db, "MICE-DU-GAN")
    t.start_date = HOM_NAY + dt.timedelta(days=3); db.commit()
    _tour(db, "MICE-THIEU", rest_stops="")
    dem = P.ban_lam_viec(db, f"{HOM_NAY:%Y-%m}")["dem"]
    assert dem["cho_toi_duyet"] == 3
    assert dem["cho_toi_duyet_du_truong"] == 2
    assert dem["cho_toi_duyet_khoi_hanh_duoi_7_ngay"] == 1, (
        "một hàng đợi 3 dòng mà 1 dòng khởi hành trong 3 ngày thì con số 3 không nói lên điều gì"
    )


# ───────────────────────────── PT-5 · thước đo quá hạn không tự lành ─────────────────────────────

def _tour_da_chay(db, ma, ket_thuc, dong_luc=None):
    t = Tour(code=ma, name=ma, tour_type="doan_noi_dia",
             start_date=ket_thuc - dt.timedelta(days=3), end_date=ket_thuc,
             operator_id=1, status="ket_thuc", closed_at=dong_luc,
             price_per_pax=10_000_000.0, planned_pax=50, fixed_cost=100_000_000.0,
             var_cost_per_pax=6_000_000.0, actual_revenue=500_000_000.0, actual_cost=400_000_000.0)
    db.add(t); db.commit()
    return t


def test_pt5_dong_so_muon_van_duoc_dem_o_ngan_rieng():
    db = _db()
    ket = HOM_NAY - dt.timedelta(days=40)
    _tour_da_chay(db, "MICE-CHUA", ket)                                        # chưa đóng, quá hạn
    _tour_da_chay(db, "MICE-MUON", ket,
                  dong_luc=dt.datetime.combine(ket + dt.timedelta(days=30), dt.time(9)))
    _tour_da_chay(db, "MICE-DUNG-HAN", ket,
                  dong_luc=dt.datetime.combine(ket + dt.timedelta(days=2), dt.time(9)))
    qh = P.qua_han_quyet_toan(db)
    assert [d["ma"] for d in qh["chua_dong_so"]] == ["MICE-CHUA"]
    assert [d["ma"] for d in qh["dong_muon"]] == ["MICE-MUON"], (
        "đóng muộn phải vẫn bị đếm – nếu không thì mỗi lần ai đó đóng muộn, thước đo tự đẹp lên"
    )
    assert qh["han_theo_tham_so_ngay"] == 7, "hạn quyết toán đoàn đọc từ tham số han_qt_doan"


def test_pt5b_tour_le_khong_vao_so_qua_han_cua_phong_doan():
    db = _db()
    ket = HOM_NAY - dt.timedelta(days=40)
    t = _tour_da_chay(db, "LE-CHUA", ket); t.tour_type = "le_noi_dia"; db.commit()
    qh = P.qua_han_quyet_toan(db)
    assert qh["chua_dong_so"] == [] and qh["dong_muon"] == []


# ───────────────────────────── PT-6 · lãi lỗ đặt hai biên cạnh nhau ─────────────────────────────

def test_pt6_bang_lai_lo_luon_co_ca_bien_ke_hoach_lan_bien_thuc_te():
    db = _db()
    ket = HOM_NAY.replace(day=15)
    t = _tour_da_chay(db, "MICE-QT", ket,
                      dong_luc=dt.datetime.combine(ket + dt.timedelta(days=2), dt.time(9)))
    t.actual_revenue, t.actual_cost = 500_000_000.0, 450_000_000.0      # biên thực tế 10%
    db.commit()
    kq = P.lai_lo_da_quyet_toan(db, f"{ket:%Y-%m}")
    assert kq["so_chuyen"] == 1
    d = kq["rows"][0]
    for cot in ("bien_ke_hoach", "bien_thuc_te", "lech_bien"):
        assert cot in d, (
            f"thiếu cột {cot} – bảng chỉ có biên thực tế trả lời được 'chuyến này lãi bao nhiêu' "
            "nhưng không trả lời được 'lúc tôi ký thì tôi được cho xem con số nào'"
        )
    assert d["lech_bien"] < 0, "chuyến này thực tế mỏng hơn kế hoạch, cột lệch phải âm"


def test_pt6b_xau_nhat_len_dau_chu_khong_phai_to_nhat_len_dau():
    db = _db()
    ket = HOM_NAY.replace(day=15)
    dong = dt.datetime.combine(ket + dt.timedelta(days=2), dt.time(9))
    t1 = _tour_da_chay(db, "MICE-TO", ket, dong_luc=dong)
    t1.actual_revenue, t1.actual_cost = 2_000_000_000.0, 1_600_000_000.0     # 20%, đúng kế hoạch
    t2 = _tour_da_chay(db, "MICE-NHO-LECH", ket, dong_luc=dong)
    t2.actual_revenue, t2.actual_cost = 100_000_000.0, 98_000_000.0          # 2%, lệch rất xấu
    db.commit()
    kq = P.lai_lo_da_quyet_toan(db, f"{ket:%Y-%m}")
    assert [d["ma"] for d in kq["rows"]][0] == "MICE-NHO-LECH", (
        "xếp theo độ lệch biên, không theo doanh thu – một chuyến nhỏ lệch rất xấu là tin đáng đọc "
        "trước một chuyến to đúng kế hoạch"
    )


def test_pt6c_ky_khong_doc_duoc_thi_nem_loi_chu_khong_doan_ky_mac_dinh():
    db = _db()
    for xau in ("2026-9x", "thang 9", "", "20269"):
        try:
            P.lai_lo_da_quyet_toan(db, xau)
        except (ValueError, IndexError):
            continue
        raise AssertionError(f"kỳ {xau!r} đọc không ra mà vẫn trả về bảng – in số thật dưới một cái tên sai")
