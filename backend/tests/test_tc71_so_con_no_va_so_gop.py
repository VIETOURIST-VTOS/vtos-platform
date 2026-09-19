"""TC-71 · SỔ CHUYẾN CÒN NỢ VÀ CON SỐ DOANH THU GỘP — anh Tuấn 18/9/2026.

    "em dựng luôn và viết code thuật toán để kéo số liệu về màn hình CT, TGĐ và toàn bộ các phòng
     ban liên quan"

Ba lựa chọn anh chốt khi em hỏi lại:
  · Doanh thu màn hình chủ tịch: GỘP cả chuyến chưa đóng sổ thành một số.
  · Màn hình mới: danh sách + đường dẫn sang chuyến, KHÔNG đóng sổ hàng loạt.
  · Pháp nhân rỗng: quy về Vietourist cố định.

═══════════════════════════════════════════════════════════════════════════════════════════════
PHÉP THỬ NÀY CANH CÁI GÌ
═══════════════════════════════════════════════════════════════════════════════════════════════
Không phải canh "màn hình có hiện ra không" — hỏng cái đó thì mở lên là thấy. Ba chỗ nguy hiểm:

 1. CON SỐ GỘP MẤT ĐƯỜNG ĐỐI CHIẾU NGƯỢC. Gộp mà không tách được hai nửa thì ngày kiểm toán hỏi
    "VTOS báo 116 tỷ, BCTC báo 85 tỷ, chênh ở đâu" sẽ không ai trả lời được. Hai khoá
    `dt_da_dong_so` / `dt_chua_dong_so` là điều kiện TỒN TẠI của luật gộp, không phải số phụ.

 2. HAI MÀN HÌNH NÓI HAI CON SỐ. `ket_qua_that` và `so_con_no` cùng trả lời "còn bao nhiêu chưa
    đóng sổ". Hai nơi tự tính riêng thì đến ngày lệch nhau không ai biết tin bên nào — đúng cái
    bệnh "bốn công thức lãi lỗ" mà kho này đã mắc một lần.

 3. GHI VÀO CƠ SỞ DỮ LIỆU LÚC NÀO KHÔNG HAY. Quy tắc pháp nhân mặc định chỉ được gom LÚC TÍNH.
    Ghi vào cột `company_id` là em nhập số liệu hộ — phạm ranh giới 09/9 — và Hành chính mất
    đường gắn đè.
"""
import datetime as dt
import os
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Company, Tour, User
from app.services import ket_qua_that as KQ
from app.services import so_con_no as SN

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(ROOT, "web")


def _doc(*p):
    return open(os.path.join(*p), encoding="utf-8").read()


def _khong_ghi_chu(s):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


HOM_NAY = dt.date(2026, 9, 19)


def _so():
    """Sổ giả đúng sáu tình huống của màn hình này, mốc 19/9/2026."""
    db = _db()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    con = Company(code="VTR", name="Vận tải Vietrip", kind="con", active=True)
    db.add_all([me, con]); db.commit()
    u = User(username="ct", full_name="Chủ tịch", role="chutich", password_hash="x")
    dh = User(username="dh", full_name="Điều hành", role="nv_dh", password_hash="x",
              company_id=me.id)
    db.add_all([u, dh]); db.commit()

    def them(code, cid, ngay, rev, cost, closed=None, status="ket_thuc"):
        db.add(Tour(code=code, name=code, tour_type="package",
                    start_date=ngay, end_date=ngay + dt.timedelta(days=2),
                    operator_id=u.id, status=status, actual_revenue=rev, actual_cost=cost,
                    closed_at=closed, company_id=cid))

    # P — đã chạy, CHƯA đóng sổ, quá 30 ngày → phần chính của màn hình
    them("P", me.id, dt.date(2026, 6, 10), 100.0, 60.0)
    # Q — đã chạy, chưa đóng sổ, MỚI về (trong 30 ngày) → còn nợ nhưng chưa quá hạn
    them("Q", me.id, dt.date(2026, 9, 10), 50.0, 30.0)
    # R — ĐÃ đóng sổ → không được xuất hiện ở màn hình này
    them("R", me.id, dt.date(2026, 7, 1), 70.0, 40.0, dt.datetime(2026, 7, 20), "da_dong_so")
    # S — công ty CON, chưa đóng sổ → không được lọt vào phạm vi Vietourist
    them("S", con.id, dt.date(2026, 6, 1), 999.0, 1.0)
    # T — pháp nhân RỖNG, chưa đóng sổ → quy về Vietourist theo luật B
    them("T", None, dt.date(2026, 6, 5), 77.0, 7.0)
    # U — CHƯA khởi hành → không nợ ai cái gì
    them("U", me.id, dt.date(2026, 12, 1), 5000.0, 1.0, None, "da_duyet")
    # V — đã chạy, chưa đóng sổ, CHƯA AI NHẬP SỐ → rỗng khác không
    them("V", me.id, dt.date(2026, 8, 1), None, None)
    db.commit()
    return db, me, u, dh


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  1 · MÀN HÌNH LIỆT KÊ ĐÚNG TẬP CHUYẾN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_chi_liet_ke_chuyen_DA_CHAY_va_CHUA_DONG_SO():
    db, me, u, _ = _so()
    r = SN.danh_sach(db, u, hom_nay=HOM_NAY)
    ma = {x["ma"] for x in r["rows"]}
    assert ma == {"P", "Q", "T", "V"}, f"đang liệt kê {sorted(ma)}"
    assert "R" not in ma, "chuyến ĐÃ đóng sổ không còn nợ gì, không được nằm ở đây"
    assert "U" not in ma, "chuyến CHƯA khởi hành chưa nợ ai cái gì"
    assert "S" not in ma, "chuyến của công ty con không thuộc phạm vi Vietourist"


def test_chuyen_cua_cong_ty_con_bi_cat_TRONG_TRUY_VAN_chu_khong_o_giao_dien():
    """SEC-02. Dòng không được phép xem thì không rời khỏi cơ sở dữ liệu.

    Canh bằng CON SỐ, không bằng danh sách: 999 đ của công ty con không được xuất hiện ở bất kỳ
    con số nào mà cửa trả ra — kể cả ở tổng, kể cả ở bảng gom theo tháng. Lọc ở giao diện thì ai
    mở công cụ nhà phát triển cũng đọc được.
    """
    db, me, u, _ = _so()
    r = SN.danh_sach(db, u, hom_nay=HOM_NAY)
    assert r["tien"] == 227.0, "100 (P) + 50 (Q) + 77 (T); V chưa có số nên cộng 0"
    assert all(t["tien"] != 999.0 for t in r["theo_thang"])
    assert 999.0 not in [x["doanh_thu"] for x in r["rows"]]


def test_phap_nhan_rong_quy_ve_vietourist_va_noi_ra_la_mac_dinh():
    """Luật B. Chuyến T vào danh sách, VÀ mang dấu để Hành chính biết đường gắn đè."""
    db, me, u, _ = _so()
    r = SN.danh_sach(db, u, hom_nay=HOM_NAY)
    t = next(x for x in r["rows"] if x["ma"] == "T")
    assert t["gan_mac_dinh"] is True, (
        "Chuyến vào đây bằng quy tắc mặc định phải mang dấu — một quy tắc mặc định không đếm "
        "được là quy tắc không ai kiểm tra lại được."
    )
    assert db.query(Tour).filter_by(code="T").one().company_id is None, (
        "Quy tắc mặc định chỉ gom LÚC TÍNH. Ghi vào cột là nhập số liệu hộ (ranh giới 09/9)."
    )


def test_rong_khac_khong_o_tung_dong():
    """Chuyến V chưa ai nhập số: để None cho màn hình vẽ '—', không đọc thành 0 đồng."""
    db, me, u, _ = _so()
    r = SN.danh_sach(db, u, hom_nay=HOM_NAY)
    v = next(x for x in r["rows"] if x["ma"] == "V")
    assert v["doanh_thu"] is None and v["gia_von"] is None
    assert v["chua_co_so"] is True
    p = next(x for x in r["rows"] if x["ma"] == "P")
    assert p["chua_co_so"] is False


def test_qua_han_dem_theo_nguong_cua_may_chu():
    db, me, u, _ = _so()
    r = SN.danh_sach(db, u, hom_nay=HOM_NAY)
    assert r["ngay_qua_han"] == 30
    # P (10/6), T (5/6) và V (1/8) đã quá 30 ngày tính tới 19/9; Q (10/9) thì chưa.
    assert r["qua_han"] == 3
    q = next(x for x in r["rows"] if x["ma"] == "Q")
    assert q["qua_han"] is False and q["so_ngay_tre"] == 9


def test_cat_thi_duoc_im_lang_thi_khong():
    """Bài học KS-5. Người đọc phải biết mình đang nhìn một phần."""
    db, me, u, _ = _so()
    r = SN.danh_sach(db, u, hom_nay=HOM_NAY, gioi_han=2)
    assert len(r["rows"]) == 2 and r["tong"] == 4
    assert r["cham_tran"] is True, "cắt bớt mà không nói ra là để người đọc quyết trên phần bị cắt"
    assert SN.danh_sach(db, u, hom_nay=HOM_NAY)["cham_tran"] is False


def test_loc_theo_khoang_thang_khoi_hanh():
    db, me, u, _ = _so()
    r = SN.danh_sach(db, u, tu="2026-06", den="2026-06", hom_nay=HOM_NAY)
    assert {x["ma"] for x in r["rows"]} == {"P", "T"}


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  2 · HAI MÀN HÌNH, MỘT LUẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_hai_man_hinh_khong_duoc_noi_hai_con_so():
    """`ket_qua_that` và `so_con_no` cùng trả lời 'còn bao nhiêu chưa đóng sổ'.

    Hai nơi tự tính riêng thì đến ngày lệch nhau không ai biết tin bên nào — đúng bệnh 'bốn công
    thức lãi lỗ' mà kho này đã mắc một lần. Cộng `dt_chua_dong_so` của từng tháng phải ra đúng
    `tien` của màn hình sổ còn nợ.
    """
    db, me, u, _ = _so()
    sn = SN.danh_sach(db, u, hom_nay=HOM_NAY)
    tong_kq = sum(KQ.thang(db, f"2026-{m:02d}")["dt_chua_dong_so"] for m in range(1, 13))
    assert tong_kq == sn["tien"], (
        f"hai màn hình nói hai con số: kết quả kinh doanh {tong_kq}, sổ còn nợ {sn['tien']}"
    )


def test_so_con_no_dung_lai_dung_hai_hang_so_cua_ket_qua_that():
    """Không chép luật sang tệp thứ hai. Hai bản của cùng một luật là hai bản sẽ lệch nhau."""
    src = _khong_ghi_chu(_doc(ROOT, "backend", "app", "services", "so_con_no.py"))
    assert "from app.services.ket_qua_that import" in src, (
        "phải dùng lại CHUA_DONG_SO và cong_ty_me của ket_qua_that, không khai lại"
    )
    assert "CHUA_DONG_SO" in src
    assert not re.search(r'CHUA_DONG_SO\s*=\s*\(', src), "khai lại hằng số là dựng bản sao thứ hai"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  3 · CON SỐ GỘP PHẢI ĐỐI CHIẾU NGƯỢC ĐƯỢC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_con_so_gop_luon_tach_duoc_hai_nua():
    """Điều kiện TỒN TẠI của luật gộp, không phải số phụ.

    Gộp mà không tách được thì ngày kiểm toán hỏi 'VTOS 116 tỷ, BCTC 85 tỷ, chênh ở đâu' sẽ không
    ai trả lời được — và lúc ấy con số gộp thành một lời nói dối chứ không còn là một lựa chọn.
    """
    db, me, u, _ = _so()
    r = KQ.thang(db, "2026-06")
    assert r["dt_da_dong_so"] == 0.0
    assert r["dt_chua_dong_so"] == 177.0, "P (100) + T (77)"
    assert r["chuyen_chua_dong_so"] == 2
    # Và hai nửa phải cộng lại đúng bằng toàn bộ doanh thu của tập chuyến thuộc mẹ trong tháng.
    assert r["dt_da_dong_so"] + r["dt_chua_dong_so"] == 177.0


def test_thang_chi_co_chuyen_da_dong_so_thi_nua_kia_bang_khong():
    """Tháng sạch nợ phải nói ra bằng 0, không phải bằng None — ở đây 0 là sự thật, không phải
    'chưa ai điền'. Đúng luật rỗng-khác-không, áp đúng chiều."""
    db, me, u, _ = _so()
    r = KQ.thang(db, "2026-07")
    assert r["dt_chua_dong_so"] == 0.0 and r["chuyen_chua_dong_so"] == 0
    assert r["dt_da_dong_so"] == 70.0


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  4 · MÀN HÌNH CHỈ ĐỌC, VÀ NÓI ĐÚNG CƠ SỞ CỦA CON SỐ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_man_hinh_khong_co_cua_ghi_nao():
    """Anh Tuấn chọn 'danh sách + đường dẫn sang chuyến', KHÔNG đóng sổ hàng loạt.

    Đóng sổ là việc khó lùi: làm hàng loạt từ một màn hình tổng thì một cú bấm nhầm đi xa hơn
    nhiều so với cái lợi về tốc độ. Canh ở cả hai đầu — dịch vụ không có hàm ghi, màn hình không
    gọi cửa ghi nào.
    """
    src = _khong_ghi_chu(_doc(ROOT, "backend", "app", "services", "so_con_no.py"))
    for cam in ("db.add", "db.commit", "db.delete", "db.merge"):
        assert cam not in src, f"màn hình chỉ đọc mà có `{cam}` — đây là cửa ghi lọt vào"
    web = _khong_ghi_chu(_doc(WEB, "app", "so-con-no", "page.tsx"))
    for cam in ('method: "POST"', 'method: "PUT"', 'method: "DELETE"', "dong_so("):
        assert cam not in web, f"màn hình gọi cửa ghi: {cam}"


def test_man_hinh_chu_tich_ghi_ro_co_so_cua_con_so_gop():
    """Con số gộp KHÔNG khớp sổ kế toán. Không ghi ra thì VTOS và BCTC báo hai con số doanh thu
    khác nhau mà không ai giải thích được, và người hỏi đầu tiên sẽ là kiểm toán."""
    src = _doc(WEB, "components", "KhoiKetQuaKinhDoanh.tsx")
    assert "doanh thu vận hành" in src, "phải gọi tên cơ sở của con số"
    assert "không khớp sổ kế toán" in src, "phải nói thẳng là không khớp sổ kế toán"
    assert "tien_da_dong_so" in src, "phải bày cả phần đã đóng sổ ngay cạnh"
    assert "/so-con-no" in src, "phải có đường dẫn sang chỗ xem chi tiết"


def test_cau_chua_gan_phap_nhan_da_doi_theo_luat_moi():
    """Luật B đảo chiều thì CHỮ trên màn hình phải đảo theo.

    Để nguyên câu cũ ('không cộng vào Vietourist') trong khi mã đã cộng vào là màn hình nói ngược
    sự thật — và đó là kiểu sai không ai phát hiện, vì câu chữ vẫn trôi chảy.
    """
    src = _doc(WEB, "components", "KhoiKetQuaKinhDoanh.tsx")
    assert "quy về Vietourist theo quy tắc mặc định" in src
    assert "không cộng vào Vietourist vì" not in src, "câu của luật cũ còn sót lại"


def test_nguong_qua_han_khong_bi_go_cung_o_giao_dien():
    """Ngưỡng do máy chủ quyết. Gõ cứng 30 ở màn hình là dựng con số thứ hai cho cùng một luật,
    và ngày máy chủ đổi thì màn hình nói sai mà không ai hay."""
    web = _khong_ghi_chu(_doc(WEB, "app", "so-con-no", "page.tsx"))
    assert "ngay_qua_han" in web, "màn hình phải đọc ngưỡng từ máy chủ"
    assert not re.search(r'>\s*30\s*ngày', web), "ngưỡng bị gõ cứng trong chữ"


def test_cua_so_con_no_da_khai_quyen_va_dung_lai_danh_sach_co_san():
    """Bài học TC-67b: cửa mới không khai quyền thì CI đỏ ở bộ kiểm khai quyền.

    Và khai bằng danh sách CÓ SẴN chứ không bịa danh sách mới: một danh sách vai riêng cho mỗi
    màn hình là cách ma trận quyền mục ruỗng dần.
    """
    acc = _doc(ROOT, "backend", "app", "services", "access.py")
    assert '"/so-con-no": ("/api/v1/so-con-no",)' in acc, "thiếu khai cửa của màn hình"
    assert re.search(r'"/so-con-no":\s*BASE_VIEW \+ OPERATIONS', acc), "thiếu khai vai xem"
    api = _doc(ROOT, "backend", "app", "api", "v1", "so_con_no.py")
    assert "COST_ROLES as XEM" in api, "phải dùng lại COST_ROLES, không bịa danh sách mới"
    assert "require_roles(*XEM" in api, "quyền phải đọc được từ CHỮ KÝ hàm"
    # ── TIỀN TỐ RIÊNG, không nằm trong /api/v1/bao-cao ───────────────────────────────────────
    # Bản nháp đầu của vòng này đặt cửa trong `bao_cao.py`. Bộ kiểm P2 đo ra ngay: `nv_dh` và
    # `cntt` được nới TOÀN BỘ nhóm báo cáo chỉ vì mở được màn hình này. Đúng cái bẫy kho này đã
    # ghi ở nhóm `/api/v1/tong-dai` ngày 09/9: "phần dôi ra vẫn là quyền đã cấp".
    assert 'prefix="/api/v1/so-con-no"' in api, "cửa phải có tiền tố riêng"
    bc = _doc(ROOT, "backend", "app", "api", "v1", "bao_cao.py")
    assert "so_con_no" not in bc, (
        "cửa không được nằm trong nhóm /api/v1/bao-cao — gắn vào đó là nới cả nhóm báo cáo cho "
        "hai vai chỉ cần đúng một cửa"
    )
    main = _doc(ROOT, "backend", "app", "main.py")
    assert "so_con_no_router" in main, "router mới phải được đăng ký, nếu không cửa trả 404"
