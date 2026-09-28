"""TC-93 · BÁO CÁO PHÒNG KINH DOANH — TÁCH LẺ VÀ ĐOÀN THÀNH HAI BẢNG (28/9/2026).

Hai lỗ hổng tìm được khi rà phân hệ Kinh doanh, và chúng là HAI MẶT của cùng một dòng mã:

  KD-1  Bảng tên "Kinh doanh" đếm MỌI booking, MỌI báo giá, MỌI yêu cầu dịch vụ – không lọc mảng ở
        dòng nào. Giám đốc Kinh doanh mở bảng "phòng mình" ra và thấy số của phòng Đoàn cộng vào.
  KD-2  Không có phạm vi `kd_doan` nào trong bảng PHONG, nên P.TGĐ tour đoàn không có bảng để mở.

Cả hai đều thuộc loại NHÌN MÀN HÌNH KHÔNG THẤY: bảng vẫn hiện đủ dòng, đủ màu, đủ cách tính; nó chỉ
trả lời sai câu hỏi "phòng tôi làm được bao nhiêu". Nên bộ kiểm này canh bằng dữ liệu dựng tay – một
chuyến lẻ và một chuyến đoàn có số tiền KHÁC NHAU rõ rệt – rồi đòi mỗi đồng nằm đúng một bảng.

BỐN CHỖ NGUY HIỂM:

 1. HAI BỘ TỪ VỰNG BỊ TRỘN. Mảng của tour là "le"/"doan"; mã phòng là "kd_le"/"kd_doan". Đem mã
    phòng đi so với mảng tour thì bộ lọc KHÔNG báo lỗi – nó trả về rỗng, và một bảng trống trông y
    hệt một phòng chưa làm gì.

 2. LUẬT MẢNG BỊ VIẾT LẠI LẦN THỨ HAI. "Thế nào là tour đoàn" đã có một chỗ duy nhất ở
    services/segments.py. Chép lại vào báo cáo là mở đường cho ngày một tour nằm ở bảng phòng này
    trong khi hoa hồng tính theo bậc thang phòng kia.

 3. DỊCH VỤ LẺ BIẾN MẤT. Tour non_package không thuộc mảng nào. Lọc theo mảng mà quên nó thì doanh
    thu ấy rơi khỏi CẢ HAI bảng và không ai thấy nó mất.

 4. LỢI NHUẬN ĐOÀN HIỆN 0 KHI CHƯA QUYẾT TOÁN. `settlement_summary` đọc actual_revenue/actual_cost;
    hai ô trống cho lợi nhuận 0 – không phân biệt được với "quyết toán xong, hoà vốn".
"""
import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.ban_hang import BaoGia
from app.models.core import Booking, Tour, User
from app.models.crm import Lead
from app.services import bao_cao_phong as BP
from app.services import rules as R
from app.services import segments as SEG

HOM_NAY = dt.date.today()
DAU_THANG = HOM_NAY.replace(day=1)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e, future=True)()
    R.seed_params(db)
    return db


def _u(db):
    u = User(username="s1", full_name="Sale 1", role="nv_kd", password_hash="x")
    db.add(u); db.commit()
    return u


def _tour(db, ma, loai="le_noi_dia", trang_thai="ket_thuc", dt_that=None, gv_that=None):
    t = Tour(code=ma, name=ma, tour_type=loai, start_date=DAU_THANG, end_date=HOM_NAY,
             operator_id=1, status=trang_thai, actual_revenue=dt_that, actual_cost=gv_that)
    db.add(t); db.commit()
    return t


def _bk(db, ma, t, u, tien):
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="K", customer_phone="0900000000", source="thu",
                pax=2, amount=tien, cancelled=False, counts_for_target=True,
                sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


def _gia_tri(db, phong, ma):
    b = BP.bao_cao(db, "thang", phong)
    return next(x for x in b["chi_tieu"] if x["ma"] == ma)


# ══════════════════ KD-2 – PHÒNG ĐOÀN PHẢI CÓ MỘT BẢNG ĐỂ MỞ ══════════════════
def test_phong_kinh_doanh_doan_co_bang_rieng_va_co_nguoi_xem_duoc():
    assert "kd_doan" in BP.PHONG, "KD-2: không có phạm vi báo cáo nào cho phòng Kinh doanh Đoàn"
    assert "kd_doan" in BP.HAM, "khai trong PHONG mà không có hàm tính thì mở bảng ra là lỗi 500"
    assert "ptgd_doan" in BP.pham_vi_duoc_xem("ptgd_doan") or True
    assert "kd_doan" in BP.pham_vi_duoc_xem("ptgd_doan"), \
        "P.TGĐ tour đoàn vẫn không mở được bảng phòng mình"


def test_hai_bang_kinh_doanh_co_TEN_KHAC_NHAU():
    """Hai mục cùng tên "Kinh doanh" trên một danh sách là một cái bẫy bấm nhầm, mỗi ngày."""
    ten_le, ten_doan = BP.PHONG["kd_le"]["ten"], BP.PHONG["kd_doan"]["ten"]
    assert ten_le != ten_doan
    assert "Lẻ" in ten_le and "Đoàn" in ten_doan


# ══════════════════ 1. HAI BỘ TỪ VỰNG KHÔNG ĐƯỢC TRỘN ══════════════════
def test_bang_dich_hai_bo_tu_vung_khai_dung_ca_hai_dau():
    """`MANG_CUA_PHONG` là chỗ DUY NHẤT nối mã phòng với mảng tour – hai đầu phải có thật."""
    from app.models.hr import DEPARTMENTS
    for phong, mang in BP.MANG_CUA_PHONG.items():
        assert phong in DEPARTMENTS, f"{phong} không phải một mã phòng ban có thật"
        assert phong in BP.PHONG, f"{phong} có trong bảng dịch mà không có bảng báo cáo"
        assert mang in SEG.MANG, f"{mang} không phải một mảng có thật trong segments"
    for phong in ("kd_le", "kd_doan"):
        assert phong in BP.MANG_CUA_PHONG, f"{phong} chưa được dịch sang mảng tour"


# ══════════════════ 2. KHÔNG VIẾT LẠI LUẬT MẢNG LẦN THỨ HAI ══════════════════
MA_MANG_CAM = {"doan_noi_dia", "doan_nuoc_ngoai", "le_noi_dia", "le_nuoc_ngoai",
               "non_package", "MICE", "MICE%"}


def _hang_so_chu_trong_MA(mo_dun) -> list[str]:
    """Mọi hằng chuỗi nằm trong MÃ CHẠY của một mô-đun – bỏ chú thích và bỏ lời khai (docstring).

    Phải lọc như vậy chứ không quét cả tệp: lời khai và chú thích của tệp này CÓ NHẮC tới mã MICE
    và tới loại chuyến, và phải được nhắc – người đọc mã cần biết luật ấy nói gì. Cái bị cấm là
    dùng chúng như một ĐIỀU KIỆN, tức là một hằng chuỗi trong mã chạy.
    """
    import ast, inspect
    cay = ast.parse(inspect.getsource(mo_dun))
    khai = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(n, clean=False) is not None:
                khai.add(id(n.body[0].value))
    return [n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in khai]


def test_bao_cao_phong_KHONG_tu_dinh_nghia_the_nao_la_tour_doan():
    """Đọc thẳng mã nguồn. Một phép thử về HÀNH VI không bắt được lỗi này: bản chép tay hôm nay cho
    kết quả giống hệt segments, và chỉ lệch vào ngày segments đổi luật – lúc ấy không ai nhớ ra."""
    import ast, inspect
    xau = MA_MANG_CAM & set(_hang_so_chu_trong_MA(BP))
    assert not xau, (f"bao_cao_phong.py đang tự viết luật mảng bằng hằng chuỗi {sorted(xau)}. "
                     "Luật ấy chỉ được ở một chỗ: services/segments.py")
    thuoc_tinh = {n.attr for n in ast.walk(ast.parse(inspect.getsource(BP)))
                  if isinstance(n, ast.Attribute)}
    assert "tour_type" not in thuoc_tinh, \
        "bao_cao_phong.py đang đọc thẳng cột tour_type – đó là luật mảng viết lại lần thứ hai"


def test_hang_rao_doc_ma_nay_that_su_bat_duoc():
    """Tự kiểm cái hàng rào trên: nó phải BẮT được một mô-đun có thật đang khai luật mảng."""
    xau = MA_MANG_CAM & set(_hang_so_chu_trong_MA(SEG))
    assert xau, "hàng rào đọc mã không bắt được cả segments.py – nó đang canh một cửa không khoá"


# ══════════════════ KD-1 – MỖI ĐỒNG NẰM ĐÚNG MỘT BẢNG ══════════════════
def test_bang_LE_khong_dem_booking_cua_DOAN_va_nguoc_lai():
    db = _db(); u = _u(db)
    _bk(db, "BK-LE", _tour(db, "LE-001", "le_noi_dia"), u, 10_000_000)
    _bk(db, "BK-DOAN", _tour(db, "MICE-001", "doan_noi_dia"), u, 700_000_000)

    le = _gia_tri(db, "kd_le", "doanh_thu")["gia_tri"]
    doan = _gia_tri(db, "kd_doan", "doanh_thu")["gia_tri"]
    assert le == 10_000_000, f"bảng Lẻ đang ăn cả tiền của phòng Đoàn: {le:,.0f}"
    assert doan == 700_000_000, f"bảng Đoàn không thấy tiền của mình: {doan:,.0f}"
    assert _gia_tri(db, "kd_le", "booking")["gia_tri"] == 1
    assert _gia_tri(db, "kd_doan", "booking")["gia_tri"] == 1


def test_tour_ma_MICE_nhung_loai_chuyen_ghi_LE_van_ve_bang_DOAN():
    """Quy tắc hợp của segments: bất đồng thì không bỏ sót. Chép tay một quy tắc thì mất tour này."""
    db = _db(); u = _u(db)
    _bk(db, "BK-X", _tour(db, "MICE-LECH", "le_noi_dia"), u, 500_000_000)
    assert _gia_tri(db, "kd_doan", "doanh_thu")["gia_tri"] == 500_000_000
    assert _gia_tri(db, "kd_le", "doanh_thu")["gia_tri"] == 0


def test_dong_LECH_QUY_TAC_hien_o_CA_HAI_bang_va_chi_dich_danh_tour():
    db = _db(); u = _u(db)
    _bk(db, "BK-X", _tour(db, "MICE-LECH", "le_noi_dia"), u, 1_000_000)
    for phong in ("kd_le", "kd_doan"):
        x = _gia_tri(db, phong, "lech_quy_tac_mang")
        assert x["gia_tri"] == 1, f"{phong}: không nêu tour bất đồng"
        assert "MICE-LECH" in x["chi_tiet"], "nêu con số mà không chỉ đích danh thì không sửa được"
        assert x["muc"] == "vang" and x["viec"], "có việc phải làm mà không nói làm gì"


# ══════════════════ 3. DỊCH VỤ LẺ KHÔNG ĐƯỢC BIẾN MẤT ══════════════════
def test_dich_vu_le_khong_thuoc_mang_nao_van_duoc_DEM_va_GIONG_NHAU_o_hai_bang():
    db = _db(); u = _u(db)
    _bk(db, "BK-NP", _tour(db, "NP-001", "non_package"), u, 33_000_000)
    le = _gia_tri(db, "kd_le", "dung_chung_dich_vu_le")
    doan = _gia_tri(db, "kd_doan", "dung_chung_dich_vu_le")
    assert le["gia_tri"] == doan["gia_tri"] == 1, "dịch vụ lẻ rơi khỏi cả hai bảng"
    assert le["chi_tiet"] == doan["chi_tiet"], "cùng một tập booking mà hai bảng nói khác nhau"
    # và nó KHÔNG được cộng vào doanh thu của phòng nào
    assert _gia_tri(db, "kd_le", "doanh_thu")["gia_tri"] == 0
    assert _gia_tri(db, "kd_doan", "doanh_thu")["gia_tri"] == 0


def test_lead_la_dong_DUNG_CHUNG_va_noi_thang_ra_la_chua_chia_duoc():
    db = _db(); u = _u(db)
    db.add(Lead(phone="0900000001", name="A", channel="hotline",
                lead_month=f"{HOM_NAY:%Y-%m}", received_at=dt.datetime.now()))
    db.commit()
    le = _gia_tri(db, "kd_le", "lead")
    doan = _gia_tri(db, "kd_doan", "lead")
    assert le["gia_tri"] == doan["gia_tri"] == 1
    assert "DÙNG CHUNG" in le["ten"], "không nói ra là dùng chung thì hai phòng cùng nhận là của mình"
    assert "chưa" in le["cong_thuc"].lower() and "mảng" in le["cong_thuc"].lower()


# ══════════════════ BÁO GIÁ ĐI THEO CỘT `mang` CỦA CHÍNH NÓ ══════════════════
def test_bao_gia_loc_theo_COT_mang_chu_khong_suy_tu_tour():
    """Báo giá có thể chưa gắn tour nào (`bao_gia.tour_id` cho phép rỗng). Suy từ tour thì mọi báo
    giá chưa gắn tour biến mất khỏi cả hai bảng – đúng lúc nó đang chờ khách trả lời."""
    db = _db()
    db.add(BaoGia(ma="BQ1", mang="kd_le", khach_ten="A", trang_thai="da_gui", tour_id=None))
    db.add(BaoGia(ma="BQ2", mang="kd_doan", khach_ten="B", trang_thai="da_gui", tour_id=None))
    db.add(BaoGia(ma="BQ3", mang="kd_doan", khach_ten="C", trang_thai="khach_chot", tour_id=None))
    db.commit()
    assert _gia_tri(db, "kd_le", "bao_gia_cho")["gia_tri"] == 1
    assert _gia_tri(db, "kd_doan", "bao_gia_cho")["gia_tri"] == 1
    assert _gia_tri(db, "kd_le", "bao_gia_chot")["gia_tri"] == 0
    assert _gia_tri(db, "kd_doan", "bao_gia_chot")["gia_tri"] == 1
    assert _gia_tri(db, "kd_doan", "ty_le_chot")["gia_tri"] == 50.0
    assert _gia_tri(db, "kd_le", "ty_le_chot")["gia_tri"] == 0.0


def test_ty_le_chot_RONG_khi_phong_chua_gui_bao_gia_nao():
    db = _db()
    db.add(BaoGia(ma="BQ1", mang="kd_le", khach_ten="A", trang_thai="da_gui"))
    db.commit()
    x = _gia_tri(db, "kd_doan", "ty_le_chot")
    assert x["gia_tri"] is None, "phòng chưa gửi báo giá nào mà tỷ lệ chốt ra một con số"
    assert x["muc"] == "", "ô rỗng không được tô màu cảnh báo"


# ══════════════════ 4. ĐOÀN ĐO LỢI NHUẬN, VÀ RỖNG KHÁC 0 ══════════════════
def test_bang_DOAN_co_dong_loi_nhuan_con_bang_LE_thi_khong():
    db = _db()
    assert any(x["ma"] == "loi_nhuan_dong_so" for x in BP.bao_cao(db, "thang", "kd_doan")["chi_tieu"])
    assert not any(x["ma"] == "loi_nhuan_dong_so" for x in BP.bao_cao(db, "thang", "kd_le")["chi_tieu"])


def test_loi_nhuan_doan_RONG_khi_chua_chuyen_nao_dong_so_KHONG_phai_0():
    db = _db(); u = _u(db)
    # Chuyến đoàn đã kết thúc nhưng CHƯA đóng sổ, và chưa ai nhập doanh thu/giá vốn thật.
    _bk(db, "BK-D", _tour(db, "MICE-CHUA", "doan_noi_dia", trang_thai="ket_thuc"), u, 800_000_000)
    x = _gia_tri(db, "kd_doan", "loi_nhuan_dong_so")
    assert x["gia_tri"] is None, "chưa quyết toán mà hiện 0 đồng lợi nhuận – hai chuyện ngược nhau"
    assert x["muc"] == ""


def test_loi_nhuan_doan_CONG_dung_khi_chuyen_da_dong_so():
    db = _db(); u = _u(db)
    t = _tour(db, "MICE-XONG", "doan_noi_dia", trang_thai="da_dong_so",
              dt_that=900_000_000, gv_that=800_000_000)
    _bk(db, "BK-D", t, u, 900_000_000)
    x = _gia_tri(db, "kd_doan", "loi_nhuan_dong_so")
    assert x["gia_tri"] == 100_000_000, f"lợi nhuận đóng sổ ra {x['gia_tri']}"
    assert "MICE-XONG" in x["chi_tiet"]


# ══════════════════ HÀNG RÀO TỰ KIỂM ══════════════════
def test_phep_thu_nay_that_su_no():
    """Nếu bỏ bộ lọc mảng đi thì bộ kiểm này PHẢI đỏ. Dựng lại đúng cảnh cũ: đếm mọi booking không
    lọc gì – và đòi con số ấy KHÁC con số bảng Lẻ đang cho. Giống nhau nghĩa là bộ lọc chưa cắt gì,
    và cả tệp này đang canh một cánh cửa không khoá."""
    from sqlalchemy import select
    db = _db(); u = _u(db)
    _bk(db, "BK-LE", _tour(db, "LE-001", "le_noi_dia"), u, 10_000_000)
    _bk(db, "BK-DOAN", _tour(db, "MICE-001", "doan_noi_dia"), u, 700_000_000)
    cach_cu = sum((b.amount or 0) - (b.discount or 0)
                  for b in db.execute(select(Booking)).scalars())
    assert cach_cu == 710_000_000
    assert _gia_tri(db, "kd_le", "doanh_thu")["gia_tri"] != cach_cu
