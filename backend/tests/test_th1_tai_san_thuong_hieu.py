# -*- coding: utf-8 -*-
"""TH-1 · Sổ tài sản thương hiệu — dùng chung bảng TSCĐ của Kế toán.

Chủ tịch chốt 18/9/2026 ba điều, và cả ba đều là loại quyết định mà làm sai thì KHÔNG NỔ:

  1. DÙNG CHUNG bảng `fixed_assets`, không dựng bảng riêng cho Marketing.
  2. Dòng thương hiệu chỉ vào danh sách và báo cáo TSCĐ của Kế toán KHI ĐÃ KHAI NGUYÊN GIÁ.
     Sai ở đây thì hồ sơ kiểm kê tài sản cuối năm có mấy chục dòng logo — mọi tổng vẫn cân, chỉ là
     danh sách ký tên bị sai.
  3. Một bộ nhận diện mới phải có HAI chữ ký: Chủ tịch và P.TGĐ Marketing. Sai ở đây thì một bộ
     nhận diện có hiệu lực mà không ai ký, và không cách nào lần ra ai đã cho qua.

Khối này canh đúng ba điều ấy, cộng hai chỗ nối dễ tuột: LUẬT VIẾT HAI LẦN (một bản Python, một
bản SQL) phải ra cùng một tập thẻ, và cửa nhập phải tự chặn mình ở hai ô nó không được phép ghi.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_th1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_th1.db", "test_th1.db-journal"):
    if os.path.exists(f):
        os.remove(f)

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
import re  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models.assets import TH_LOAI, FixedAsset  # noqa: E402
from app.services import intake_thuong_hieu as IN  # noqa: E402
from app.services import tai_san_thuong_hieu as TH  # noqa: E402

Base.metadata.create_all(engine)
HOM_NAY = date.today()


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(FixedAsset).delete()
    s.commit()
    yield s
    s.close()


def dong(**kw):
    return {"loai": "logo", "ten": "Logo Vietourist", "phien_ban": "v3",
            "hieu_luc_tu": "2027-01-01", "noi_su_dung": "Biển hiệu, đồng phục, website", **kw}


def the_ke_toan(db, **kw):
    """Một thẻ TSCĐ THƯỜNG của Kế toán – thứ không bao giờ được biến mất vì hàng rào của sổ này."""
    a = FixedAsset(code=kw.pop("code", "TS0001"), name="Máy chủ Dell", kind="huu_hinh",
                   start_date=date(2026, 1, 1), cost=120_000_000, depr_months=36, **kw)
    db.add(a)
    db.flush()
    return a


# =============================================================================================
# 1. DÙNG CHUNG BẢNG — và `kind` không bị mượn làm dấu phân biệt
# =============================================================================================

def test_so_nay_ghi_vao_DUNG_bang_tai_san_cua_ke_toan(db):
    """Dựng bảng thứ hai là để hai sổ cùng nói về một tài sản."""
    from app.services.intake import BO_NAP

    assert BO_NAP["tai_san_thuong_hieu"]["bang_dich"] == "fixed_assets"
    a, _ = IN.nap(db, dong(), "nv_mkt")
    db.commit()
    assert db.get(FixedAsset, a.id) is not None


def test_DAU_PHAN_BIET_la_mot_cot_rieng_KHONG_phai_kind(db):
    """`kind` quyết định TK nguyên giá và TK hao mòn. Mượn nó làm dấu "thuộc sổ thương hiệu" là
    đổi định khoản của một thẻ — và định khoản sai thì đi thẳng vào sổ cái."""
    a, _ = IN.nap(db, dong(), "nv_mkt")
    db.commit()
    assert a.th_so is True, "phải có một cột riêng đánh dấu thẻ thuộc sổ thương hiệu"
    assert a.kind == "vo_hinh" and a.asset_account == "213", \
        "logo là TSCĐ vô hình – TK 213, đúng như bảng Kế toán quy định"
    assert "thuong_hieu" not in str(a.kind), "`kind` không được mang giá trị của sổ thương hiệu"


# =============================================================================================
# 2. LUẬT VÀO SỔ KẾ TOÁN: chỉ khi đã khai nguyên giá
# =============================================================================================

def test_the_TSCD_THUONG_luon_hien_du_hang_rao_co_mat(db):
    """Hàng rào của sổ này không được động tới một thẻ nào của Kế toán."""
    a = the_ke_toan(db)
    assert TH.hien_o_so_ke_toan(a) is True
    a.cost = None                                   # thẻ Kế toán chưa khai nguyên giá vẫn là của họ
    assert TH.hien_o_so_ke_toan(a) is True


def test_the_THUONG_HIEU_chua_khai_nguyen_gia_thi_KHONG_vao_so_ke_toan(db):
    a, _ = IN.nap(db, dong(), "nv_mkt")
    db.commit()
    assert a.cost is None
    assert TH.hien_o_so_ke_toan(a) is False


def test_the_THUONG_HIEU_da_khai_nguyen_gia_thi_VAO_so_ke_toan(db):
    """Bộ nhận diện mua ngoài có hoá đơn: Kế toán ghi tăng, và nó là TSCĐ vô hình thật."""
    a, _ = IN.nap(db, dong(), "nv_mkt")
    a.cost = 200_000_000
    db.commit()
    assert TH.hien_o_so_ke_toan(a) is True


def test_NGUYEN_GIA_BANG_0_KHAC_nguyen_gia_RONG(db):
    """Rỗng = chưa ai khai. 0 = có người khai rằng bằng không — một câu trả lời, và thẻ có câu trả
    lời thì thuộc về sổ Kế toán. Quy ước "rỗng khác 0" là quy ước chung của lược đồ từ đợt K2."""
    a, _ = IN.nap(db, dong(), "nv_mkt")
    a.cost = 0
    db.commit()
    assert TH.hien_o_so_ke_toan(a) is True, "0 là một con số đã khai, không phải ô trống"


def test_HAI_BAN_CUA_MOT_LUAT_python_va_SQL_phai_ra_cung_mot_tap(db):
    """`hien_o_so_ke_toan` (Python) và `loc_so_ke_toan` (SQL) là hai bản của MỘT luật. Hai bản thì
    lệch nhau, và lệch vào đúng hôm sổ có một thẻ lạ — nên phải có một phép thử chéo.

    Sổ dựng ra cố ý có đủ bốn dạng thẻ, kể cả hai dạng dễ quên: thẻ Kế toán không nguyên giá, và
    thẻ thương hiệu nguyên giá bằng 0.
    """
    the_ke_toan(db, code="TS0001")
    b = the_ke_toan(db, code="TS0002")
    b.cost = None
    IN.nap(db, dong(phien_ban="v1"), "nv_mkt")                       # thương hiệu, nguyên giá rỗng
    c, _ = IN.nap(db, dong(phien_ban="v2"), "nv_mkt")
    c.cost = 0                                                       # thương hiệu, nguyên giá 0
    d, _ = IN.nap(db, dong(phien_ban="v3"), "nv_mkt")
    d.cost = 50_000_000                                              # thương hiệu, có nguyên giá
    db.commit()

    theo_python = {a.id for a in db.execute(select(FixedAsset)).scalars() if TH.hien_o_so_ke_toan(a)}
    theo_sql = {a.id for a in db.execute(TH.loc_so_ke_toan(select(FixedAsset))).scalars()}
    assert theo_python == theo_sql, "bộ lọc SQL và phép tính Python đang nói hai điều khác nhau"
    assert len(theo_python) == 4 and len(theo_sql) == 4


def test_MAN_HINH_TAI_SAN_va_BANG_KHAU_HAO_deu_di_qua_hang_rao():
    """Hai chỗ liệt kê thẻ TSCĐ. Một chỗ quên rào là logo lọt vào bảng Kế toán in ra và ký.

    Kiểm ở mức MÃ NGUỒN chứ không chỉ ở hành vi: một chỗ đọc mới thêm vào ngày mai mà tự viết lại
    điều kiện thì phép thử hành vi vẫn xanh, còn phép thử này đỏ.
    """
    import inspect

    from app.api.v1 import assets as API
    from app.services import assets as SV

    # ĐỌC TÊN HÀM KHÔNG ĐỦ, và đây là chỗ bản đầu của phép thử này SAI. Bẻ mã bỏ lời gọi mà GIỮ
    # dòng `import` thì tên hàm vẫn nằm trong mã nguồn, và phép thử vẫn xanh. Phải đọc đúng hình
    # LỜI GỌI: hàng rào bọc quanh câu truy vấn.
    for ham, ten in ((API.list_assets, "danh sách thẻ TSCĐ (/tai-san)"),
                     (SV.depreciation_table, "bảng tính khấu hao")):
        ma = inspect.getsource(ham)
        assert "loc_so_ke_toan(select(FixedAsset))" in ma, \
            f"{ten} chưa đi qua hàng rào sổ thương hiệu"


def test_the_thuong_hieu_khong_lot_vao_DANH_SACH_the_TSCD(db):
    """Phép thử HÀNH VI, đi kèm phép thử đọc mã ở trên. Đọc mã bắt được chỗ ai đó gỡ hàng rào;
    phép thử này bắt được chỗ hàng rào còn nguyên mà lọc sai."""
    from app.api.v1 import assets as API

    the_ke_toan(db)
    a, _ = IN.nap(db, dong(), "nv_mkt")
    b, _ = IN.nap(db, dong(phien_ban="v9"), "nv_mkt")
    b.cost = 80_000_000
    db.commit()
    ma = {r["code"] for r in API.list_assets(status="", department="", u=None, db=db)}
    assert "TS0001" in ma, "thẻ TSCĐ thường biến mất – hàng rào đang chặn nhầm sổ của Kế toán"
    assert b.code in ma, "thẻ nhận diện ĐÃ khai nguyên giá phải hiện như TSCĐ vô hình"
    assert a.code not in ma, "thẻ nhận diện chưa khai nguyên giá lọt vào danh sách thẻ TSCĐ"


def test_the_thuong_hieu_khong_lot_vao_bang_tinh_khau_hao(db):
    from app.services import assets as SV

    the_ke_toan(db)
    a, _ = IN.nap(db, dong(), "nv_mkt")
    db.commit()
    ma = {r["code"] for r in SV.depreciation_table(db, f"{HOM_NAY:%Y-%m}")["rows"]}
    assert a.code not in ma, "thẻ nhận diện chưa khai nguyên giá lọt vào bảng tính khấu hao"


# =============================================================================================
# 3. HAI CHỮ KÝ
# =============================================================================================

def test_the_moi_nam_o_NHAP_chu_khong_tu_co_hieu_luc(db):
    a, _ = IN.nap(db, dong(), "nv_mkt")
    db.commit()
    assert a.th_trang_thai == "nhap"
    assert TH.du_hai_chu_ky(a) is False
    assert set(TH.con_thieu_chu_ky(a)) == {"chutich", "ptgd_mkt"}


def test_MOT_chu_ky_chua_du_de_co_hieu_luc(db):
    a, _ = IN.nap(db, dong(), "nv_mkt")
    kq = TH.ky(db, a, "chutich", "chutich")
    db.commit()
    assert kq["du_hai_chu_ky"] is False
    assert a.th_trang_thai == "nhap", "một chữ ký mà đã có hiệu lực thì chữ ký thứ hai là để làm gì"
    assert TH.con_thieu_chu_ky(a) == ["ptgd_mkt"]


def test_DU_HAI_chu_ky_thi_chuyen_sang_dang_dung(db):
    a, _ = IN.nap(db, dong(), "nv_mkt")
    TH.ky(db, a, "chutich", "chutich")
    kq = TH.ky(db, a, "ptgd_mkt", "ptgd.mkt")
    db.commit()
    assert kq["du_hai_chu_ky"] is True and kq["chuyen_sang_dang_dung"] is True
    assert a.th_trang_thai == "dang_dung"
    assert a.th_hieu_luc_tu is not None, "đang dùng mà không có ngày hiệu lực thì không ai biết từ bao giờ"


def test_VAI_NGOAI_DANH_SACH_khong_ky_duoc(db):
    a, _ = IN.nap(db, dong(), "nv_mkt")
    db.commit()
    with pytest.raises(ValueError):
        TH.ky(db, a, "nv_mkt", "nv_mkt")
    with pytest.raises(ValueError):
        TH.ky(db, a, "tgd", "tgd")


def test_BA_DAU_KHAI_DANH_SACH_VAI_KY_khong_duoc_lech_nhau():
    """Danh sách "ai được ký một bộ nhận diện" được viết ở BA chỗ, và ba chỗ ấy phải khớp:

      1. `require_roles(...)` ở đường API  – HÀNG RÀO THẬT, và là chỗ duy nhất máy đọc được để rà
         soát phân quyền toàn hệ (KS-2, P-1).
      2. `TH.VAI_KY`                       – ánh xạ vai → ô cờ trong sổ.
      3. Tham số `thuong_hieu_vai_ky`      – BẢN GHI CHỮ KÝ: ai chốt, ngày nào. `require_roles`
         không mang được thông tin ấy, nên nó không thay được chỗ này.

    Ba chỗ là ba chỗ sẽ lệch. Phép thử này là lý do chúng không lệch — sửa một chỗ mà quên hai chỗ
    kia thì đỏ ngay, chứ không đợi tới hôm một P.TGĐ bấm nút và bị từ chối.
    """
    import inspect

    from app.api.v1 import marketing as API
    from app.services import rules as R

    ma = inspect.getsource(API.ky_thuong_hieu)
    trong_rao = set(re.findall(r'require_roles\(([^)]*)\)', ma)[0].replace('"', "").replace(" ", "").split(","))
    dong_ts = next((t for t in R.DEFAULT_PARAMS if t[0] == TH.THAM_SO_HAI_CHU_KY), None)
    assert dong_ts, f"thiếu tham số {TH.THAM_SO_HAI_CHU_KY} trong sổ tham số"

    assert trong_rao == set(TH.VAI_KY), "hàng rào API và TH.VAI_KY đang khai hai danh sách khác nhau"
    assert set(dong_ts[1].split(",")) == set(TH.VAI_KY), "tham số và mã đang khai hai danh sách khác nhau"
    assert dong_ts[4], "tham số không ghi ai chốt – một quyết định không có người ký là một quyết định không ai bảo vệ"


def test_KHONG_ai_ky_thay_ca_hai_vai(db):
    """Chủ tịch đi qua được gần hết các cửa trong hệ. KHÔNG đi qua cửa này — thứ nó chặn không phải
    vai trò mà là việc sổ ghi một chữ ký P.TGĐ mà P.TGĐ chưa hề bấm."""
    import inspect

    from app.api.v1 import marketing as API

    ma = inspect.getsource(API.ky_thuong_hieu)
    assert "u.role" in ma, "vai trò phải lấy từ tài khoản đang đăng nhập, không nhận từ thân yêu cầu"
    assert "chutich" in ma, "Chủ tịch PHẢI đi qua được cửa này – ông là một trong hai người ký"
    a, _ = IN.nap(db, dong(), "nv_mkt")
    TH.ky(db, a, "chutich", "chutich")
    TH.ky(db, a, "chutich", "chutich")          # bấm lại lần nữa cũng chỉ là MỘT chữ ký
    db.commit()
    assert a.th_ky_ptgd_mkt is False and a.th_trang_thai == "nhap"


# =============================================================================================
# 4. CỬA NHẬP TỰ CHẶN MÌNH
# =============================================================================================

def test_cua_nhap_KHONG_cho_khai_nguyen_gia(db):
    """Nguyên giá quyết định thẻ có vào sổ Kế toán hay không. Mở ô ấy ở đây là để một người ngoài
    phòng Kế toán tự đẩy một thẻ vào bảng cân đối."""
    loi, _, _ = IN.kiem(db, dong(nguyen_gia="200000000"))
    assert any("Nguyên giá" in x for x in loi)
    keys = {c["key"] for c in IN.bo_nap(__import__("app.services.intake", fromlist=["_c"])._c)
            ["tai_san_thuong_hieu"]["cot"]}
    assert "nguyen_gia" not in keys and "cost" not in keys


def test_cua_nhap_KHONG_cho_dat_thang_trang_thai_dang_dung(db):
    """"Đang dùng" là KẾT QUẢ của hai chữ ký, không phải một ô để gõ."""
    loi, _, _ = IN.kiem(db, dong(trang_thai="dang_dung"))
    assert any("HAI chữ ký" in x for x in loi)
    assert IN.kiem(db, dong(trang_thai="nhap"))[0] == []


def test_nap_lai_cung_loai_cung_phien_ban_thi_THAY_khong_de_ban_thu_hai(db):
    IN.nap(db, dong(noi_su_dung="Biển hiệu"), "nv_mkt")
    db.commit()
    a2, tt = IN.nap(db, dong(noi_su_dung="Biển hiệu, đồng phục"), "nv_mkt")
    db.commit()
    assert tt == "thay_ban_cu"
    assert db.query(FixedAsset).count() == 1
    assert a2.th_noi_su_dung == "Biển hiệu, đồng phục"


def test_nap_lai_KHONG_duoc_lam_mat_hai_chu_ky_da_co(db):
    """Nạp lại để sửa một ô nhỏ mà chữ ký bay mất thì bộ nhận diện đang dùng lặng lẽ hết hiệu lực."""
    a, _ = IN.nap(db, dong(), "nv_mkt")
    TH.ky(db, a, "chutich", "chutich")
    TH.ky(db, a, "ptgd_mkt", "ptgd.mkt")
    db.commit()
    a2, _ = IN.nap(db, dong(noi_su_dung="Thêm website"), "nv_mkt")
    db.commit()
    assert a2.th_ky_chutich and a2.th_ky_ptgd_mkt
    assert a2.th_trang_thai == "dang_dung"


def test_hieu_luc_den_dung_truoc_hieu_luc_tu_la_LOI(db):
    loi, _, _ = IN.kiem(db, dong(hieu_luc_tu="2027-01-01", hieu_luc_den="2026-12-01"))
    assert any("đứng trước" in x for x in loi)


def test_thieu_phien_ban_chi_la_CANH_BAO_chu_khong_chan(db):
    """Bắt lỗi quá tay thì nhân viên không nhập được và quay về Excel."""
    loi, cb, _ = IN.kiem(db, dong(phien_ban=""))
    assert loi == []
    assert any("phiên bản" in x for x in cb)


def test_loai_ngoai_danh_muc_la_LOI(db):
    assert any("không có trong danh mục" in x for x in IN.kiem(db, dong(loai="banner"))[0])
    assert set(TH_LOAI) >= {"logo", "phong_chu", "bo_mau", "an_pham"}


# =============================================================================================
# 5. BẢN NÀO ĐANG CÓ HIỆU LỰC — câu hỏi thật của người đi in ấn phẩm
# =============================================================================================

def test_ban_dang_dung_doc_theo_NGAY_HIEU_LUC_chu_khong_chi_theo_trang_thai(db):
    cu, _ = IN.nap(db, dong(phien_ban="v2", hieu_luc_tu="2025-01-01",
                            hieu_luc_den="2026-12-31"), "nv_mkt")
    cu.th_trang_thai = "da_thay"
    moi, _ = IN.nap(db, dong(phien_ban="v3", hieu_luc_tu="2027-01-01"), "nv_mkt")
    moi.th_trang_thai = "dang_dung"
    db.commit()
    assert TH.ban_dang_dung(db, "logo", date(2026, 6, 1)).id == cu.id
    assert TH.ban_dang_dung(db, "logo", date(2027, 6, 1)).id == moi.id


def test_ban_NHAP_khong_bao_gio_la_ban_dang_dung(db):
    a, _ = IN.nap(db, dong(phien_ban="v4", hieu_luc_tu=str(HOM_NAY - timedelta(days=1))), "nv_mkt")
    db.commit()
    assert a.th_trang_thai == "nhap"
    assert TH.ban_dang_dung(db, "logo", HOM_NAY) is None, \
        "bản chưa đủ chữ ký mà đã có hiệu lực thì hai chữ ký không có tác dụng gì"
