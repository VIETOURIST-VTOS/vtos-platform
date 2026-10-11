"""TC-100 · HỒ SƠ TÀI XẾ CÓ MÀN HÌNH THẬT, VÀ MỤC 4.1 MỞ ĐÚNG PHẠM VI — 05/10/2026.

Hai mục trong cây phân hệ Điều hành ghi "Đã có" nhưng đưa người dùng tới chỗ khác.

MỘT · 4.9.3 "TÀI XẾ" TRỎ VÀO MÀN HÌNH CỦA CHÍNH TÀI XẾ.
    Đường dẫn cũ là /xe-hdv — màn hình việc-của-tôi dành cho người ở hiện trường. Người quản lý đội
    xe bấm vào không thấy hồ sơ ai; tài khoản không gắn mã nhân viên chỉ nhận được một dòng "Tài
    khoản này chưa gắn với hồ sơ nhân sự". Hồ sơ tài xế chưa từng có màn hình, dù dữ liệu đã nằm sẵn
    trong hệ thống: `employees` giữ người, `vehicle_documents` giữ bằng lái, `hang_gplx` giữ luật
    hạng, `vehicles.driver_id` giữ xe ai đứng tên. Thiếu đúng một màn hình để đọc chúng.

    Anh Tuấn chọn phương án DỰNG MÀN HÌNH (05/10/2026), không phải đổi mục thành "Chưa dựng".

TAI · 4.1 "TỔNG QUAN ĐIỀU HÀNH" MỞ RA BÁO CÁO TOÀN CÔNG TY.
    Mục trỏ vào /bao-cao, nhưng màn hình ấy luôn đặt phạm vi về `pham_vi[0]` = Toàn công ty. Người
    Điều hành bấm "Tổng quan điều hành" rồi phải tự đi tìm ô phạm vi. Cửa máy chủ đã nhận tham số
    `pham_vi` từ lâu; chỉ giao diện là không đọc nó từ đường dẫn.

BA ĐIỀU DỄ LÀM HỎNG KHI DỰNG MÀN HÌNH TÀI XẾ, và cả ba đều có phép thử riêng ở dưới:

 1. KẾT LUẬN "ĐẠT" KHI THIẾU DỮ LIỆU. Bằng lái không ghi ngày hết hạn KHÔNG phải là còn hạn. Đây
    đúng là luật services/fleet.py đã giữ ở cổng điều xe, và màn hình phải nói y như cổng nói —
    hai nơi kết luận khác nhau về cùng một tài xế thì người điều hành sẽ tin nơi dễ chịu hơn.

 2. GỘP "CHƯA BIẾT" VỚI "KHÔNG ĐẠT". Hai người: một thiếu ngày hết hạn, một bằng đã hết hạn. Cùng
    là "không đủ điều kiện", nhưng việc phải làm khác hẳn — một bên đi đòi giấy, một bên ngừng
    điều xe. Gộp một chữ là xoá đúng chỗ khác nhau đó.

 3. HỎI CƠ SỞ DỮ LIỆU THEO TỪNG DÒNG. Bài học TC-99: cửa /cham-soc hỏi bốn lượt mỗi phiếu và mất
    12 giây với 1.267 dòng. Đội xe hôm nay mới mười mấy người, nhưng luật thì không đổi theo số
    dòng hiện có.
"""
import os
import re
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_tc100.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import datetime as dt

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.fleet import VehicleDocument
from app.models.hr import Employee, Vehicle
from app.services import access as AC
from app.services import tai_xe as TX

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOM_NAY = dt.date.today()


# ══════════════════════════ dựng dữ liệu ══════════════════════════
def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _nguoi(db, ma, ten, phong="doi_xe", vi_tri="nv", dang_lam=True) -> Employee:
    e = Employee(code=ma, full_name=ten, department=phong, position=vi_tri, active=dang_lam)
    db.add(e); db.flush(); return e


def _bang(db, e, hang="D", cap=None, het=None, so="012345678901", con_hieu_luc=True):
    """Mặc định hạng D cấp sau 01/01/2025 – luật mới, chở khách không giới hạn số chỗ.

    KHÔNG dùng "E" làm mặc định: chữ E là hạng của LUẬT CŨ, và với giấy cấp sau khi Luật
    TTATGTĐB 2024 có hiệu lực thì nó không còn là hạng chở khách. Lần đầu viết tệp này đã lấy E
    làm mặc định và ba phép thử đỏ – chúng vô tình kiểm nhánh "hạng không chở khách" chứ không
    kiểm cái định kiểm. Xem app/services/hang_gplx.py.
    """
    g = VehicleDocument(employee_id=e.id, kind="gplx", number=so, hang=hang,
                        issued_on=cap or (HOM_NAY - dt.timedelta(days=400)),
                        expires_on=het, active=con_hieu_luc)
    db.add(g); db.flush(); return g


def _xe(db, bien, so_cho, e=None, ma="XE9"):
    v = Vehicle(code=ma, plate=bien, seats=so_cho, driver_id=e.id if e else None)
    db.add(v); db.flush(); return v


def _theo_ma(d, ma):
    return next(x for x in d["rows"] if x["code"] == ma)


# ═══════ LUẬT 1 · AI LÀ TÀI XẾ – MỘT ĐỊNH NGHĨA, KHÔNG HAI ═══════
def test_nhan_ca_nguoi_phong_doi_xe_lan_nguoi_chuc_danh_tai_xe():
    db = _db()
    _nguoi(db, "NS01", "Phòng đội xe", phong="doi_xe", vi_tri="nv")
    _nguoi(db, "NS02", "Chức danh tài xế", phong="dieu_hanh", vi_tri="tai_xe")
    _nguoi(db, "NS03", "Không liên quan", phong="ketoan", vi_tri="nv")
    db.commit()
    ma = {x["code"] for x in TX.danh_sach(db)["rows"]}
    assert ma == {"NS01", "NS02"}, (
        "định nghĩa tài xế phải khớp services/drivers.py dòng 62 – hai nơi đếm hai kiểu là hai con số "
        f"khác nhau cho cùng một câu hỏi; đang ra {sorted(ma)}")


# ═══════ LUẬT 2 · THIẾU DỮ LIỆU KHÔNG PHẢI LÀ ĐẠT ═══════
def test_bang_khong_ghi_ngay_het_han_thi_KHONG_tinh_la_du_dieu_kien():
    db = _db()
    e = _nguoi(db, "NS01", "Không ghi hạn")
    _bang(db, e, het=None)
    db.commit()
    d = TX.danh_sach(db)
    x = _theo_ma(d, "NS01")
    assert not x["du_dieu_kien"], "bằng chưa ghi ngày hết hạn mà vẫn tính là đủ điều kiện"
    assert x["chua_du_du_lieu"] and not x["khong_dat"], \
        "thiếu ngày hết hạn là CHƯA BIẾT, không phải KHÔNG ĐẠT – việc phải làm là đi đòi giấy"
    assert d["du_dieu_kien"] == 0 and d["chua_du_du_lieu"] == 1


def test_chua_co_bang_trong_ho_so_cung_la_chua_biet_chu_khong_phai_dat():
    db = _db()
    _nguoi(db, "NS01", "Chưa nộp bằng")
    db.commit()
    x = _theo_ma(TX.danh_sach(db), "NS01")
    assert not x["du_dieu_kien"] and x["chua_du_du_lieu"]
    assert x["so_cho_toi_da"] == -1, "chưa có bằng thì số chỗ tối đa là CHƯA ĐỌC ĐƯỢC, không phải 0"


# ═══════ LUẬT 3 · CHƯA BIẾT VÀ KHÔNG ĐẠT LÀ HAI CỜ RIÊNG ═══════
def test_bang_het_han_la_KHONG_DAT_chu_khong_phai_chua_biet():
    db = _db()
    e = _nguoi(db, "NS01", "Bằng hết hạn")
    _bang(db, e, het=HOM_NAY - dt.timedelta(days=1))
    db.commit()
    d = TX.danh_sach(db)
    x = _theo_ma(d, "NS01")
    assert x["khong_dat"] and not x["chua_du_du_lieu"], (
        "bằng đã hết hạn là một kết luận ĐÃ CÓ, không phải thiếu dữ liệu – người này phải ngừng điều xe")
    assert d["khong_dat"] == 1 and d["chua_du_du_lieu"] == 0


def test_hang_khong_cho_khach_la_KHONG_DAT():
    """Hạng B1 không được chở khách. Đó là kết luận, không phải thiếu dữ liệu."""
    db = _db()
    e = _nguoi(db, "NS01", "Hạng B1")
    _bang(db, e, hang="B1", het=HOM_NAY + dt.timedelta(days=365))
    db.commit()
    x = _theo_ma(TX.danh_sach(db), "NS01")
    assert x["khong_dat"] and not x["du_dieu_kien"]


def test_chu_E_voi_giay_cap_sau_luat_moi_la_KHONG_DAT():
    """Phát hiện lúc viết tệp này, giữ lại vì nó dễ đi qua mắt người.

    Cùng một chữ "E" trên giấy: cấp thời luật cũ thì chở khách không giới hạn số chỗ, cấp sau khi
    Luật TTATGTĐB 2024 có hiệu lực thì KHÔNG phải hạng chở khách. Màn hình không được đọc mỗi chữ
    hạng rồi kết luận – ngày cấp là thứ duy nhất phân biệt hai hệ, và services/hang_gplx.py đã lo
    phần ấy. Phép thử này canh rằng màn hình dùng đúng hàm đó chứ không tự suy.
    """
    db = _db()
    cu = _nguoi(db, "NS01", "E luật cũ")
    _bang(db, cu, hang="E", cap=dt.date(2020, 5, 1), het=HOM_NAY + dt.timedelta(days=365))
    moi = _nguoi(db, "NS02", "E luật mới")
    _bang(db, moi, hang="E", cap=dt.date(2025, 6, 1), het=HOM_NAY + dt.timedelta(days=365))
    db.commit()
    d = TX.danh_sach(db)
    assert _theo_ma(d, "NS01")["du_dieu_kien"], "E cấp thời luật cũ vẫn là hạng chở khách"
    assert _theo_ma(d, "NS02")["khong_dat"], "E cấp sau luật mới không còn là hạng chở khách"


def test_hang_de_trong_la_chua_biet():
    db = _db()
    e = _nguoi(db, "NS01", "Không ghi hạng")
    _bang(db, e, hang="", het=HOM_NAY + dt.timedelta(days=365))
    db.commit()
    x = _theo_ma(TX.danh_sach(db), "NS01")
    assert x["chua_du_du_lieu"] and not x["khong_dat"]


def test_bang_con_han_va_doc_duoc_hang_thi_du_dieu_kien():
    db = _db()
    e = _nguoi(db, "NS01", "Đủ điều kiện")
    _bang(db, e, hang="D", het=HOM_NAY + dt.timedelta(days=365))
    db.commit()
    d = TX.danh_sach(db)
    x = _theo_ma(d, "NS01")
    assert x["du_dieu_kien"] and not x["thieu"]
    assert x["so_cho_toi_da"] is None, "hạng D luật mới không giới hạn số chỗ – None, KHÁC với -1 là chưa đọc được"
    assert d["du_dieu_kien"] == 1


# ═══════ LUẬT 4 · BẰNG NÀO ĐƯỢC LẤY, VÀ XE AI ĐỨNG TÊN ═══════
def test_lay_bang_co_han_xa_nhat_va_bo_qua_bang_da_tat_hieu_luc():
    """Cùng luật chọn với fleet._docs: giấy đã thay thì active=False chứ không xoá."""
    db = _db()
    e = _nguoi(db, "NS01", "Đổi bằng")
    _bang(db, e, so="111", het=HOM_NAY + dt.timedelta(days=30), con_hieu_luc=False)
    _bang(db, e, so="222", het=HOM_NAY + dt.timedelta(days=100))
    _bang(db, e, so="333", het=HOM_NAY + dt.timedelta(days=900))
    db.commit()
    x = _theo_ma(TX.danh_sach(db), "NS01")
    assert x["gplx_so"] == "333", f"phải lấy bằng hạn xa nhất còn hiệu lực, đang lấy {x['gplx_so']}"


def test_bang_chua_ghi_han_khong_duoc_lan_bang_da_ghi_han():
    db = _db()
    e = _nguoi(db, "NS01", "Hai bằng")
    _bang(db, e, so="111", het=HOM_NAY + dt.timedelta(days=100))
    _bang(db, e, so="222", het=None)
    db.commit()
    assert _theo_ma(TX.danh_sach(db), "NS01")["gplx_so"] == "111"


def test_xe_dang_dung_ten_va_nguoi_chua_gan_xe():
    db = _db()
    a = _nguoi(db, "NS01", "Có xe")
    _nguoi(db, "NS02", "Chưa có xe")
    _xe(db, "51B-111.11", 45, a, ma="XE1")
    _xe(db, "51B-222.22", 29, a, ma="XE2")
    db.commit()
    d = TX.danh_sach(db)
    assert [v["bien"] for v in _theo_ma(d, "NS01")["xe_dang_dung_ten"]] == ["51B-111.11", "51B-222.22"]
    assert _theo_ma(d, "NS02")["xe_dang_dung_ten"] == []
    assert d["chua_gan_xe"] == 1


def test_o_dem_chi_tinh_nguoi_dang_lam():
    db = _db()
    a = _nguoi(db, "NS01", "Đang làm")
    _bang(db, a, het=HOM_NAY + dt.timedelta(days=365))
    b = _nguoi(db, "NS02", "Đã nghỉ", dang_lam=False)
    _bang(db, b, het=HOM_NAY + dt.timedelta(days=365))
    db.commit()
    d = TX.danh_sach(db)
    assert d["tong"] == 2 and d["dang_lam"] == 1 and d["du_dieu_kien"] == 1, \
        "người đã nghỉ vẫn phải còn trong danh sách để tra cứu, nhưng không được đếm vào ô sẵn sàng"


# ═══════ LUẬT 5 · KHÔNG HỎI CSDL THEO TỪNG DÒNG (bài học TC-99) ═══════
def _dem_truy_van(db, viec):
    dem = [0]
    bind = db.get_bind()

    def _ghi(conn, cursor, statement, parameters, context, executemany):
        dem[0] += 1

    event.listen(bind, "before_cursor_execute", _ghi)
    try:
        viec()
    finally:
        event.remove(bind, "before_cursor_execute", _ghi)
    return dem[0]


def test_so_luot_hoi_khong_tang_theo_so_tai_xe():
    it, nhieu = _db(), _db()
    for db, n in ((it, 2), (nhieu, 12)):
        for i in range(n):
            e = _nguoi(db, f"NS{i:02d}", f"Tài xế {i}")
            _bang(db, e, het=HOM_NAY + dt.timedelta(days=100 + i))
            _xe(db, f"51B-{i:03d}.00", 45, e, ma=f"XE{i}")
        db.commit()
    a = _dem_truy_van(it, lambda: (it.expunge_all(), TX.danh_sach(it)))
    b = _dem_truy_van(nhieu, lambda: (nhieu.expunge_all(), TX.danh_sach(nhieu)))
    assert a == b, f"2 tài xế tốn {a} lượt hỏi, 12 tài xế tốn {b} – số lượt vẫn tăng theo số dòng"
    assert b <= 6, f"đọc cả danh sách tốn {b} lượt; cần một lượt cho mỗi bảng tra kèm, không hơn"


# ═══════ LUẬT 6 · MÀN HÌNH CÓ THẬT, VÀ QUYỀN KHÔNG LỆCH VỚI HỒ SƠ XE ═══════
def test_man_hinh_tai_xe_ton_tai_va_cay_phan_he_tro_dung_vao_do():
    cay = open(os.path.join(GOC, "web", "lib", "cay_phan_he.ts"), encoding="utf-8").read()
    assert os.path.exists(os.path.join(GOC, "web", "app", "tai-xe", "page.tsx")), \
        "cây phân hệ sắp trỏ tới /tai-xe nhưng trang chưa có"
    assert re.search(r'ma:\s*"4\.9\.3".*?href:\s*"/tai-xe"', cay), \
        "mục 4.9.3 Tài xế vẫn chưa trỏ vào màn hình hồ sơ tài xế"
    assert not re.search(r'ma:\s*"4\.9\.3".*?href:\s*"/xe-hdv"', cay), \
        "mục 4.9.3 vẫn trỏ vào /xe-hdv – đó là màn hình việc-của-chính-tài-xế, không phải hồ sơ"


def test_quyen_man_hinh_tai_xe_dung_bang_quyen_ho_so_xe():
    assert AC.MENU_ROLES["/tai-xe"] == AC.MENU_ROLES["/doi-xe"], (
        "hồ sơ xe và hồ sơ người lái xe là cùng một tập hồ sơ đội xe; mở lệch nhau là mở một đường "
        "vòng vào thứ vừa đóng ở cửa kia")


def test_vai_doc_duoc_cua_may_chu_khop_voi_ma_tran():
    from app.api.v1 import tai_xe as API
    assert set(API.READ) == set(AC.MENU_ROLES["/tai-xe"]), (
        "danh sách vai trên router và dòng trong ma trận quyền lệch nhau – một trong hai đang nói dối")


# ═══════ LUẬT 7 · MỤC 4.1 MỞ ĐÚNG PHẠM VI ĐIỀU HÀNH ═══════
def test_muc_tong_quan_dieu_hanh_mang_theo_pham_vi():
    cay = open(os.path.join(GOC, "web", "lib", "cay_phan_he.ts"), encoding="utf-8").read()
    assert re.search(r'ma:\s*"4\.1".*?href:\s*"/bao-cao\?pham_vi=dieu_hanh"', cay), \
        "mục 4.1 vẫn mở ra báo cáo toàn công ty, người Điều hành phải tự đổi ô phạm vi"


def test_man_hinh_bao_cao_doc_pham_vi_tu_duong_dan():
    """11/10/2026 — ĐỌC CẢ TỆP TRANG LẪN THÀNH PHẦN, vì mã đã dọn chỗ.

    Luật không đổi một chữ: màn hình báo cáo phải đọc `?pham_vi=` từ đường dẫn, và phạm vi lạ thì
    rơi về mặc định chứ không để màn hình trống. Đổi là CHỖ Ở của mã: từ hôm nay bảng chỉ tiêu
    nằm ở `components/BangChiTieuPhong.tsx`, dùng chung cho hai cửa `/bao-cao` và
    `/phan-he/<khoa>`, nên tệp trang chỉ còn là một cái vỏ.

    Ghép hai tệp lại rồi mới soi, thay vì chỉ đổi sang tệp thành phần: như thế phép thử đúng dù
    mã nằm ở trang hay ở thành phần, và lần dọn mã sau nó không đỏ oan một lần nữa.
    """
    ma = "\n".join(
        open(os.path.join(GOC, *q), encoding="utf-8").read()
        for q in (("web", "app", "bao-cao", "page.tsx"),
                  ("web", "components", "BangChiTieuPhong.tsx")))
    khong_chu_thich = re.sub(r"/\*.*?\*/|//[^\n]*", "", ma, flags=re.S)
    assert 'get("pham_vi")' in khong_chu_thich, "màn hình báo cáo chưa đọc tham số pham_vi"
    # KHÔNG ghim TÊN BIẾN. Bản đầu của hai dòng dưới đòi đúng chữ `m.pham_vi[...]`, nên hôm
    # 11/10/2026 đổi tên biến từ `m` sang `meta` lúc dọn mã là phép thử đỏ — trong khi luật nó
    # canh vẫn đúng nguyên. Một hàng rào đỏ vì tên biến là hàng rào dạy người ta sửa phép thử cho
    # hết đỏ; nên nó soi PHÉP TÍNH (`pham_vi[0].ma`), không soi cách đặt tên.
    assert not re.search(r"if \(\w+\.pham_vi\.length\)\s*setPv\(\w+\.pham_vi\[0\]\.ma\);", khong_chu_thich), \
        "vẫn còn dòng luôn kéo phạm vi về Toàn công ty"
    assert "pham_vi[0].ma" in khong_chu_thich, \
        "phạm vi lạ trong đường dẫn phải rơi về mặc định, không để màn hình trống"


def test_hang_rao_bat_duoc_ban_cu():
    """Tự kiểm: đưa đúng hai dòng của bản trước 05/10 vào thì hai hàng rào trên PHẢI đỏ."""
    cu_cay = '{ ma: "4.1", ten: "Tổng quan điều hành", href: "/bao-cao" },'
    cu_bc = "      if (m.pham_vi.length) setPv(m.pham_vi[0].ma);"
    assert not re.search(r'ma:\s*"4\.1".*?href:\s*"/bao-cao\?pham_vi=dieu_hanh"', cu_cay)
    assert 'get("pham_vi")' not in cu_bc
