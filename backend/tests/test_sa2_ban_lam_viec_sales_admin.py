"""SA-2 · Bàn làm việc Sale Admin phòng Đoàn — hàng rào, 24/9/2026 (vòng 3/3).

Sáu khối việc theo bản mô tả công việc hiệu lực 01/9/2026. Màn hình CHỈ ĐỌC: hai cửa ghi của vai
này đã mở ở vòng 2 và nằm trên chính chuyến.

═══════════════════════════════════════════════════════════════════════════════════════════════
NĂM ĐIỀU TỆP NÀY CANH — VÀ CHÚNG ĐỀU LÀ CHUYỆN "ĐỪNG NÓI DỐI TRÊN MÀN HÌNH"
═══════════════════════════════════════════════════════════════════════════════════════════════
 1. KHÔNG DỰNG BẢN SAO THỨ HAI CỦA MỘT LUẬT. `thieu` gọi lại `tours._thieu_truong_de_chuyen`,
    hạn chốt sổ gọi lại `ptgd_doan.qua_han_quyet_toan`, khoản treo gọi lại `luong.khoan_treo`.
    Chép tay bất kỳ cái nào thì ngày luật gốc đổi, màn hình này nói sai mà vẫn xanh.
 2. CHƯA TRẢ LỜI KHÁC VỚI "KHÔNG CÓ". Ô hoa hồng khách rỗng phải đọc ra là CHƯA AI TRẢ LỜI. Gộp
    nó vào "không có" là xoá đúng cái mà lần thêm ô ngày 24/9 sinh ra để thấy.
 3. THOẢ THUẬN CHIA DATA TRẢ VỀ None, KHÔNG PHẢI "chưa ghi". Hệ thống chưa có ô ấy. In "chưa ghi"
    là nói với người dùng rằng họ quên một việc, trong khi là một việc phần mềm chưa mở cửa.
 4. KHÔNG CÓ CỬA GHI NÀO TRONG CẢ TỆP DỊCH VỤ. Một hàm `db.commit()` lọt vào đây là màn hình soát
    trở thành màn hình sửa, và người bị soát với người soát dùng chung một cái bàn.
 5. KHÔNG DỰNG HỘP THƯ THỨ HAI. Bản mô tả yêu cầu gửi báo cáo ngày qua thư; VTOS đã có cơ chế báo
    cáo ngày từ Điều 12 và Chủ tịch quyết 09/9/2026 là không gửi mail hay Zalo.
"""
import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import User
from app.services import sales_admin as SA
from app.services import tours as T

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("sadmin", "sales_admin"), ("nvdh", "nv_dh"), ("ct", "chutich")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


class _Data:
    def __init__(self, ma, loai="doan_noi_dia", **kw):
        self.code = ma
        self.name = kw.get("name", "Đoàn " + ma)
        self.tour_type = loai
        self.start_date = kw.get("start_date", HOM_NAY + dt.timedelta(days=20))
        self.end_date = kw.get("end_date", HOM_NAY + dt.timedelta(days=24))
        self.operator_id = kw.get("operator_id", 3)
        self.price_per_pax = kw.get("price_per_pax", 10_000_000.0)
        self.fixed_cost = kw.get("fixed_cost", 100_000_000.0)
        self.var_cost_per_pax = kw.get("var_cost_per_pax", 6_000_000.0)
        self.planned_pax = kw.get("planned_pax", 50)
        self.rest_stops = ""
        self.company_id = None
        self.note = ""
        self.hoa_hong_khach = kw.get("hoa_hong_khach", "")
        self.hoa_hong_khach_tien = kw.get("hoa_hong_khach_tien", 0)


# ───────────────────────── khối chờ chuyển ─────────────────────────

def test_sa2a_chi_liet_ke_doan_dang_o_buoc_kinh_doanh_soan():
    db = _db()
    T.create(db, _u(db, "nvkd"), _Data("MICE-2610-201", hoa_hong_khach="khong"))   # nhap_kd
    T.create(db, _u(db, "nvdh"), _Data("LE-2610-202", loai="le_noi_dia"))          # nhap, tour lẻ
    ma = [d["ma"] for d in SA.cho_toi_chuyen(db)]
    assert ma == ["MICE-2610-201"], "chỉ đoàn đang ở bước Kinh doanh soạn mới là việc của vai này"


def test_sa2b_thieu_truong_goi_lai_dung_luat_cua_cong_chuyen():
    """Không chép tay danh sách trường bắt buộc — xem ghi chú 1 ở đầu tệp."""
    import re
    nguon = open(SA.__file__, encoding="utf-8").read()
    i = nguon.find("def cho_toi_chuyen")
    than = re.sub(r'"""[\s\S]*?"""', "", nguon[i:nguon.find("\ndef ", i + 10)])
    assert "_thieu_truong_de_chuyen" in than, "phải hỏi lại luật của cổng chuyển"


def test_sa2c_chuyen_duoc_noi_thang_chu_khong_de_man_hinh_tu_suy():
    db = _db()
    T.create(db, _u(db, "nvkd"), _Data("MICE-2610-203", hoa_hong_khach="khong"))
    T.create(db, _u(db, "nvkd"), _Data("MICE-2610-204"))          # chưa trả lời ô hoa hồng
    d = {x["ma"]: x for x in SA.cho_toi_chuyen(db)}
    assert d["MICE-2610-203"]["chuyen_duoc"] is True and not d["MICE-2610-203"]["thieu"]
    assert d["MICE-2610-204"]["chuyen_duoc"] is False
    assert any("hoa hồng" in x.lower() for x in d["MICE-2610-204"]["thieu"])


# ───────────────────────── khối soát giá vốn ─────────────────────────

def test_sa2d_chua_tra_loi_KHAC_voi_khong_co():
    """Ghi chú 2 đầu tệp. Gộp hai trạng thái ấy là xoá đúng thứ ô bắt buộc sinh ra để thấy."""
    db = _db()
    T.create(db, _u(db, "nvkd"), _Data("MICE-2610-205"))                              # ""
    T.create(db, _u(db, "nvkd"), _Data("MICE-2610-206", hoa_hong_khach="khong"))      # "khong"
    d = {x["ma"]: x for x in SA.soat_gia_von(db)}
    assert "MICE-2610-205" in d, "đoàn chưa trả lời phải nằm trong danh sách soát"
    assert d["MICE-2610-205"]["hoa_hong_khach"] == "" and d["MICE-2610-205"]["da_tra_loi_hoa_hong"] is False
    assert "MICE-2610-206" not in d, "đoàn đã trả lời và không có cảnh báo thì hết việc, không nằm lại"


def test_sa2e_bien_neu_chua_vao_gia_von_tinh_tu_so_da_khai():
    db = _db()
    T.create(db, _u(db, "nvkd"), _Data("MICE-2610-207", hoa_hong_khach="co",
                                       hoa_hong_khach_tien=50_000_000.0))
    r = [x for x in SA.soat_gia_von(db) if x["ma"] == "MICE-2610-207"]
    # Đoàn đã trả lời "co" và chưa có dòng chi phí nào nên không có cảnh báo → không nằm lại danh
    # sách soát. Đó là hành vi ĐÚNG: khai xong là hết việc ở khối này.
    assert r == []


def test_sa2f_bien_thu_hai_luon_thap_hon_hoac_bang_bien_da_nhap():
    """Nếu một ngày con số thứ hai CAO hơn con số thứ nhất thì phép trừ đã đảo dấu, và màn hình sẽ
    nói với người ký rằng bỏ sót hoa hồng làm chuyến LÃI hơn."""
    from app.services import rules as R
    db = _db()
    for tien in (1, 50_000_000.0, 400_000_000.0, 900_000_000.0):
        t = T.create(db, _u(db, "nvkd"), _Data(f"MICE-2610-3{int(tien)}", hoa_hong_khach="co",
                                               hoa_hong_khach_tien=tien))
        c = R.calc(t, 0.10)
        hh = R.bien_neu_hoa_hong_chua_vao(t, c)
        assert hh["bien_neu_chua_vao"] <= c["margin"]


# ───────────────────────── khối dữ liệu khách ─────────────────────────

def test_sa2g_thoa_thuan_chia_data_tra_None_chu_khong_phai_chua_ghi():
    """Ghi chú 3 đầu tệp. Ô ấy KHÔNG TỒN TẠI trong hệ thống hôm nay.

    Ngày nào có ô thật thì phép thử này đỏ — và đỏ đúng lúc, vì lúc ấy lời khai "chưa có ô nhập"
    trên màn hình mới là câu sai.
    """
    db = _db()
    T.create(db, _u(db, "nvkd"), _Data("MICE-2610-208", hoa_hong_khach="khong"))
    r = SA.du_lieu_khach(db)
    assert r and all(x["thoa_thuan_chia_data"] is None for x in r)
    from app.models.core import Booking
    assert not hasattr(Booking, "thoa_thuan_chia_data"), (
        "Đã có ô thoả thuận chia data — sửa `sales_admin.du_lieu_khach` để đọc nó, và sửa lời khai "
        "'chưa có ô nhập' trên màn hình /sales-admin.")


# ───────────────────────── không có cửa ghi ─────────────────────────

def test_sa2h_tep_dich_vu_KHONG_co_mot_cua_ghi_nao():
    """Ghi chú 4 đầu tệp. Một `db.commit()` lọt vào đây là màn hình soát thành màn hình sửa."""
    import re
    nguon = re.sub(r'"""[\s\S]*?"""', "", open(SA.__file__, encoding="utf-8").read())
    nguon = re.sub(r"#[^\n]*", "", nguon)
    for cam in ("db.commit(", "db.add(", "db.delete(", "db.flush("):
        assert cam not in nguon, f"bàn làm việc chỉ đọc mà có {cam} – vai này không sửa số của ai"


def test_sa2i_cua_API_hep_dung_bang_dong_MENU_ROLES():
    """Hai bảng lệch nhau là có vai thấy mục menu rồi bấm vào nhận 403, hoặc mở được cửa mà không
    có mục menu để tới."""
    from app.api.v1 import sales_admin as API
    from app.services import access as AC
    assert set(API.XEM) == set(AC.MENU_ROLES["/sales-admin"])


def test_sa2j_khong_dung_toi_khoi_kinh_doanh():
    """Màn hình này là chỗ SOÁT hồ sơ của khối Kinh doanh. Để người bị soát đứng cùng chỗ với
    người soát thì cái cổng chỉ còn là một dòng chữ."""
    from app.services import access as AC
    for vai in AC.SALES:
        assert vai not in AC.MENU_ROLES["/sales-admin"], f"{vai} mở được bàn soát hồ sơ của chính mình"


# ───────────────────────── báo cáo ngày ─────────────────────────

def test_sa2k_khong_dung_hop_thu_thu_hai():
    """Ghi chú 5 đầu tệp. Bản mô tả viết là gửi thư; VTOS đã có cơ chế báo cáo ngày từ Điều 12, và
    Chủ tịch quyết 09/9/2026: báo cáo lập tự động trên màn hình, không gửi mail hay Zalo."""
    # Bỏ chú thích và docstring TRƯỚC khi quét: chính đoạn giải thích "không dựng SMTP" ở đầu tệp
    # chứa chữ SMTP, và một phép thử quét chữ trên cả tệp sẽ đỏ vì đọc được lời hứa của chính nó.
    # Đây là lần thứ hai bẫy này bắt (lần đầu: test_pt1b, 24/9/2026) — nên nó được ghi ra đây.
    import re
    nguon = open(SA.__file__, encoding="utf-8").read()
    nguon = re.sub(r'"""[\s\S]*?"""', "", nguon)
    nguon = re.sub(r"#[^\n]*", "", nguon)
    for cam in ("smtplib", "SMTP", "send_email", "gui_email", "sendmail"):
        assert cam not in nguon, f"{cam} trong bàn làm việc — Chủ tịch đã quyết không gửi thư"
    db = _db()
    bc = SA.ban_lam_viec(db)["bao_cao_ngay"]
    assert bc["han"] == "20:00" and bc["man_hinh"].startswith("/")


# ───────────────────────── gọi lại luật gốc ─────────────────────────

def test_sa2l_qua_han_quyet_toan_goi_lai_ham_cua_PTGD():
    """Chép luật 7 ngày sang đây là dựng bản sao thứ hai: ngày Chủ tịch đổi tham số `han_qt_doan`,
    một trong hai màn hình sẽ nói sai."""
    import re
    nguon = open(SA.__file__, encoding="utf-8").read()
    i = nguon.find("def tien_do_quyet_toan")
    than = re.sub(r'"""[\s\S]*?"""', "", nguon[i:nguon.find("\ndef ", i + 10)])
    assert "qua_han_quyet_toan" in than and "khoan_treo" in than
    assert "timedelta(days=7" not in than and "han_qt_doan" not in than, (
        "hạn chốt sổ phải đi qua `ptgd_doan.qua_han_quyet_toan`, không đọc tham số lần thứ hai")


def test_sa2m_ban_lam_viec_chay_duoc_tren_kho_rong():
    """Kho rỗng là trạng thái ngày đầu tiên của mọi khách hàng. Màn hình nổ ở đó thì không ai tới
    được ngày thứ hai."""
    db = _db()
    d = SA.ban_lam_viec(db)
    for k in ("cho_toi_chuyen", "soat_gia_von", "ho_so_doan", "tien_do_thu_tien",
              "tien_do_quyet_toan", "du_lieu_khach", "bao_cao_ngay", "dem"):
        assert k in d
    assert all(isinstance(v, int) for v in d["dem"].values())


def test_sa2n_nam_loai_giay_to_deu_da_khai_bao_duoc():
    """Checklist hồ sơ chỉ đúng khi `LOAI_TEP` có đủ năm khoá. Thiếu khoá nào thì cột ấy luôn hiện
    "thiếu", và đó là lỗi cấu hình chứ không phải lỗi của người làm hồ sơ."""
    from app.models.attachments import LOAI_TEP
    thieu = [k for k, _ in SA.HO_SO_DOAN if k not in LOAI_TEP]
    assert not thieu, f"loại tệp chưa khai báo: {thieu}"
