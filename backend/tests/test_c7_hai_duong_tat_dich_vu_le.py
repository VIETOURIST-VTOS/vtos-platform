"""C7 · Hai đường tắt của dịch vụ lẻ — Chủ tịch quyết 25/9/2026: "gỡ quyền".

Dịch vụ lẻ (non_package) dùng chung kho với chuyến đoàn: cùng bảng `tours`, cùng `TourCostLine`,
cùng bút toán. Nhưng nó được viết như một màn hình nhỏ gọn, nên hai luật của chuyến đoàn không
theo sang — và hai chỗ hở ấy chỉ nhìn thấy khi đặt hai bên cạnh nhau.

    ĐƯỜNG TẮT 1 · GIÁ VỐN vượt khoá "Một cửa".
        Chuyến đoàn: chỉ người điều hành của chuyến ghi được giá vốn.
        Dịch vụ lẻ  : cả khối Kinh doanh ghi được — và ghi ô ấy là ghi thẳng `t.fixed_cost`
                      cùng một dòng `TourCostLine`. Giá vốn là MẪU SỐ của hoa hồng phòng ấy nhận.
        Chủ tịch 25/9/2026: "Phòng kinh doanh lẻ gỡ hết, không liên quan giá vốn; chỉ nắm được dự
        toán 3 con số đã có trong phần quyết toán tour." — gỡ CẢ sale phụ trách, và chỉ ở dịch vụ
        lẻ. Phòng Kinh doanh ĐOÀN không đụng tới: `access.can_see_cost_tren_chuyen` vẫn mở giá vốn
        cho họ trên chính chuyến đoàn của họ, và luật ấy vốn đã loại tour lẻ ra từ 24/9.

    ĐƯỜNG TẮT 2 · CHỐT THÁNG ký thay Kế toán.
        Chuyến đoàn: `close` (đóng số) rồi `kt_confirm` (Kế toán ký) — hai người, hai bước.
        Dịch vụ lẻ  : `close_month` đặt một lượt `status="kt_xac_nhan"` + `kt_confirmed_at` rồi
                      chạy bút toán. Cho tp_dh hoặc tgd bấm là cho họ ký thay Kế toán.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO HAI VIỆC NÀY CẦN PHÉP THỬ CANH, KHÔNG CHỈ CẦN SỬA
═══════════════════════════════════════════════════════════════════════════════════════════════
Cả hai đều là lần SIẾT, và cả hai đều gây phiền ngay tuần đầu: sẽ có người gọi lên bảo "tôi sửa
giá vốn cho nhanh mà không được". Một lần siết không có phép thử canh thì đúng lúc ấy có người
thêm lại một vai vào danh sách, và không ai biết là đang mở lại cánh cửa vừa đóng có lý do.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import User
from app.services import nonpackage as NP

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("nvkd2", "nv_kd"), ("tnkd", "tn_kd"), ("tpkd", "tp_kd"),
                     ("gdkd", "gd_kd"), ("nvdh", "nv_dh"), ("tpdh", "tp_dh"), ("ketoan", "ketoan"),
                     ("tgd", "tgd"), ("ct", "chutich")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _dv(db, nguoi_tao="nvdh", gia_von=2_000_000):
    """Mặc định do ĐIỀU HÀNH tạo, vì từ 25/9/2026 chỉ họ mới gõ được ô giá vốn lúc tạo."""
    u = _u(db, nguoi_tao)
    d = {"service_type": "VISA", "description": "Visa Hàn", "customer_name": "Khách A",
         "customer_phone": "0900000000", "source": "web", "amount": 3_000_000,
         "service_date": HOM_NAY.isoformat()}
    if gia_von: d["cost_amount"] = gia_von
    t, b = NP.create(db, u, d)
    return t, b


# ───────────────────── đường tắt 1 · giá vốn ─────────────────────

def test_c7a_ca_khoi_kinh_doanh_KHONG_con_sua_gia_von():
    """Lần SIẾT. Gỡ HẾT khối Kinh doanh, kể cả nhân viên bán — giá vốn là số của bên ĐẶT DỊCH VỤ
    với nhà cung cấp, không phải của bên bán."""
    db = _db()
    _, b = _dv(db)
    for vai in ("tpkd", "gdkd", "tnkd", "nvkd"):
        with pytest.raises(Exception) as e:
            NP.update(db, _u(db, vai), b, {"cost_amount": 500_000})
        assert "403" in str(e.value) or "giá vốn" in str(e.value)


def test_c7b_va_khong_sua_duoc_ca_nha_cung_cap():
    """Nhà cung cấp đi CÙNG giá vốn: `update` ghi `supplier_name` vào chính dòng TourCostLine ấy.
    Chặn một ô mà để hở ô kia thì vẫn sửa được chứng từ của một khoản chi."""
    db = _db()
    _, b = _dv(db)
    with pytest.raises(Exception):
        NP.update(db, _u(db, "tpkd"), b, {"supplier_name": "NCC khác"})


def test_c7c_nhung_van_sua_duoc_thong_tin_khach():
    """Không siết quá tay: sửa tên khách, số điện thoại, ngày dịch vụ vẫn là việc của họ."""
    db = _db()
    _, b = _dv(db)
    NP.update(db, _u(db, "tpkd"), b, {"customer_name": "Khách B"})
    assert b.customer_name == "Khách B"


def test_c7d_sale_phu_trach_cung_KHONG_sua_duoc_gia_von_cua_chinh_minh():
    """Đây là chỗ bản đầu em làm sai và Chủ tịch sửa lại 25/9/2026.

    Em đã giữ sale lại với lý do "`create` đặt operator_id = sales_id, nên sale ấy LÀ người điều
    hành của dịch vụ". Lý do đó lấy một chi tiết kỹ thuật làm căn cứ cho một ranh giới nghề
    nghiệp — và chi tiết kỹ thuật ấy đổi một dòng là ranh giới đi theo. Gỡ hết.
    """
    db = _db()
    t, b = _dv(db, nguoi_tao="nvkd", gia_von=0)
    assert t.operator_id == _u(db, "nvkd").id, "create đã đổi cách đặt operator_id"
    with pytest.raises(Exception):
        NP.update(db, _u(db, "nvkd"), b, {"cost_amount": 1_800_000})


def test_c7e_cua_TAO_cung_qua_cong_ay():
    """Chặn cửa sửa mà để hở cửa tạo thì người bị gỡ quyền chỉ cần tạo lại một dòng mới."""
    db = _db()
    with pytest.raises(Exception):
        NP.create(db, _u(db, "nvkd"), {"service_type": "VISA", "description": "Visa Nhật",
                                       "customer_name": "K", "customer_phone": "0901",
                                       "source": "web", "amount": 3_000_000,
                                       "cost_amount": 2_000_000})


def test_c7e2_sale_van_tao_duoc_dich_vu_khi_KHONG_go_gia_von():
    """Không siết quá tay: bán một cái visa vẫn là việc của họ. Ô giá vốn để TRỐNG chờ Điều hành,
    và trống ở đây là trống thật — không phải 0."""
    db = _db()
    t, b = _dv(db, nguoi_tao="nvkd", gia_von=0)
    assert b.amount == 3_000_000
    assert not b.cost_amount


def test_c7f_dieu_hanh_sua_duoc_gia_von_moi_dich_vu():
    """Phòng Điều hành là bên đặt dịch vụ với nhà cung cấp — họ cầm con số thật."""
    db = _db()
    _, b = _dv(db)
    for vai in ("nvdh", "tpdh"):
        NP.update(db, _u(db, vai), b, {"cost_amount": 1_900_000})
    assert b.cost_amount == 1_900_000


def test_c7g_cong_dung_TRUOC_moi_lenh_gan():
    """Từ chối rồi mà bản ghi đã đổi một nửa là thứ tệ hơn cả không chặn: phiên còn đi tiếp và
    `db.commit()` ở cửa sau sẽ lưu phần dở dang ấy."""
    db = _db()
    _, b = _dv(db)
    with pytest.raises(Exception):
        NP.update(db, _u(db, "tpkd"), b, {"customer_name": "ĐỔI RỒI", "cost_amount": 1})
    assert b.customer_name == "Khách A", "tên khách đã bị ghi trước khi cổng từ chối"


def test_c7h_chu_tich_di_qua_bang_LUAT_TOAN_QUYEN_chu_khong_co_ten_trong_danh_sach():
    db = _db()
    _, b = _dv(db)
    assert "chutich" not in NP.GIA_VON_ROLES, "Chủ tịch đi qua bằng một luật, không bằng nhiều danh sách"
    NP.update(db, _u(db, "ct"), b, {"cost_amount": 1_700_000})
    assert b.cost_amount == 1_700_000


# ───────────────────── đường tắt 2 · chốt tháng ─────────────────────

def test_c7i_chi_KE_TOAN_chot_thang():
    for vai in ("tp_dh", "tgd", "gd_kd", "nv_dh"):
        assert vai not in NP.CHOT_THANG_ROLES, (
            f"{vai} chốt được dịch vụ lẻ tháng — nút ấy vừa đóng số vừa ký xác nhận kế toán")
    assert NP.CHOT_THANG_ROLES == ("ketoan",)


def test_c7j_nut_chot_van_dat_ca_hai_moc_mot_luot_nen_no_phai_la_tay_ke_toan():
    """Phép thử này KHÔNG đòi đổi mã. Nó khoá LÝ DO: ngày nào `close_month` còn đặt cả
    `kt_xac_nhan` lẫn `kt_confirmed_at` thì ngày ấy danh sách vai vẫn phải chỉ có Kế toán. Nếu ai
    đó tách nó thành hai bước thật, phép thử đỏ và người sửa đọc được vì sao từng siết."""
    nguon = open(NP.__file__, encoding="utf-8").read()
    i = nguon.find("def close_month")
    than = nguon[i:nguon.find("\ndef ", i + 10)]
    mot_luot = "kt_confirmed_at" in than and '"kt_xac_nhan"' in than
    assert not mot_luot or NP.CHOT_THANG_ROLES == ("ketoan",), (
        "chốt tháng vẫn gộp đóng số với chữ ký kế toán nhưng danh sách vai đã nới ra")


def test_c7k_endpoint_khai_quyen_giong_than_ham():
    """Bệnh KS-2: bốn cửa dịch vụ lẻ khai quyền ở thân hàm còn chữ ký để trống, nên bản khai quyền
    của hệ thống nói "ai đăng nhập cũng gọi được"."""
    from app.api.v1 import nonpackage as API
    nguon = open(API.__file__, encoding="utf-8").read()
    for ham in ("create_np", "edit_np", "print_np", "close_month"):
        i = nguon.find(f"def {ham}(")
        chu_ky = nguon[i:nguon.find("\n", i)]
        assert "require_roles" in chu_ky, f"{ham} vẫn để trống chữ ký quyền — xem KS-2"


def test_c7l_endpoint_chot_thang_doc_CHINH_danh_sach_cua_than_ham():
    """Hai bản khai rời nhau rồi sẽ lệch. Chữ ký phải trỏ vào hằng số, không chép lại chuỗi."""
    from app.api.v1 import nonpackage as API
    nguon = open(API.__file__, encoding="utf-8").read()
    i = nguon.find("def close_month(")
    chu_ky = nguon[i:nguon.find("\n", i)]
    assert "CHOT_THANG_ROLES" in chu_ky, "endpoint chép lại danh sách vai thay vì đọc hằng số"


def test_c7n_PHONG_KINH_DOANH_DOAN_KHONG_bi_dong_theo():
    """Chủ tịch nói rõ 25/9: "Ý là PKDL, còn PKDĐ vẫn giữ nguyên."

    Lần siết này chỉ ở dịch vụ lẻ. Quyền xem giá vốn của Kinh doanh Đoàn trên chính chuyến đoàn
    của họ (mở 24/9/2026) không đụng tới — và luật ấy vốn đã tự loại tour lẻ ra, nên hai việc
    không giẫm lên nhau. Phép thử này canh đúng chỗ ấy: siết một phòng mà kéo theo phòng kia là
    lỗi im lặng, vì màn hình chỉ hiện dấu gạch ngang chứ không báo 403.
    """
    import datetime as _dt
    from app.models.core import Tour
    from app.services import access as AC
    doan = Tour(code="D1", name="Đoàn", tour_type="doan_noi_dia",
                start_date=HOM_NAY, end_date=HOM_NAY + _dt.timedelta(days=2))
    le = Tour(code="L1", name="Lẻ", tour_type="le_noi_dia",
              start_date=HOM_NAY, end_date=HOM_NAY)
    db = _db()
    for vai in ("nvkd", "tpkd", "gdkd"):
        u = _u(db, vai)
        assert AC.can_see_cost_tren_chuyen(u, doan), f"{vai} mất quyền xem giá vốn chuyến ĐOÀN"
        assert not AC.can_see_cost_tren_chuyen(u, le), f"{vai} xem được giá vốn tour LẺ"


def test_c7m_sua_dich_vu_le_van_mo_cho_sale_phu_trach():
    """SUA_ROLES phải đủ rộng để không chặn nhầm người mà thân hàm sẽ cho qua bằng `b.sales_id`.
    Chữ ký hẹp hơn thân hàm là một cửa đóng ở nơi không ai đọc lý do."""
    assert "nv_kd" in NP.SUA_ROLES
