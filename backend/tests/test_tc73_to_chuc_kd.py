"""TC-73 · CƠ CẤU TỔ CHỨC KHỐI KINH DOANH — anh Tuấn 19/9/2026.

Bộ bàn giao "VTOS-KDL-ban-giao-IT-v5.0" đòi bốn màn hình xem xuống bốn cấp: chi nhánh → phòng →
team → người. Anh Tuấn chọn phương án "dựng bảng tổ chức thật" thay vì tận dụng ba chuỗi chữ tự do
đang có (`users.department`, `users.sales_group`, `employees.office`).

═══════════════════════════════════════════════════════════════════════════════════════════════
PHÉP THỬ NÀY CANH CÁI GÌ
═══════════════════════════════════════════════════════════════════════════════════════════════
Không canh "màn hình có hiện cây không" — hỏng cái đó thì mở lên là thấy ngay. Bốn chỗ nguy hiểm,
đều là loại hỏng mà nhìn màn hình KHÔNG phát hiện được:

 1. BÁO CÁO KỲ CŨ ĐỔI SỐ SAU LƯNG NGƯỜI ĐỌC. Đây là lý do cả bảng `phan_cong_kd` tồn tại. Nếu
    `don_vi_cua()` bỏ qua ngày, thì hôm nay chuyển một người sang team khác là doanh thu tháng
    trước của họ chạy theo, và bảng đã trình Chủ tịch tuần trước in lại ra con số khác. Phép thử
    `test_chuyen_team_khong_lam_doi_ky_cu` canh đúng chỗ ấy.

 2. MỘT NGƯỜI ĐƯỢC ĐẾM Ở HAI TEAM. Hai dòng phân công cùng vai phủ cùng một ngày thì tổng phòng
    lớn hơn tổng các dòng con, mà không ai tìm ra vì sao — con số vẫn "đẹp", chỉ là sai. Chặn ở
    lúc GHI, không để bộ đối soát phát hiện sau.

 3. CÂY GÃY THỨ BẬC. Một "team" treo thẳng dưới chi nhánh thì mọi phép cộng theo cấp sai từ đó.
    Rẻ nhất để chặn lúc ghi, đắt nhất để dọn khi đã có dữ liệu.

 4. QUYỀN NỚI RA MÀ KHÔNG AI ĐỊNH NỚI. `gd_kd` cố ý KHÔNG nằm trong `XEM_TOAN_CAY` và cố ý KHÔNG
    nằm trong danh sách GHI: người tự vẽ được cây tổ chức của mình là người tự cấp được phạm vi
    xem của mình, và lúc ấy mọi rào ở tầng dưới chỉ còn là trang trí. Hai phép thử canh cả hai vế
    — có `gd_kd` trong XEM, không có trong GHI — để lần nới sau phải là một quyết định, không phải
    một dòng thêm cho tiện.

RANH GIỚI 09/9/2026 cũng được canh: bản alembic KHÔNG chép một dòng dữ liệu nào từ ba chuỗi cũ
sang, và màn hình KHÔNG có nút suy tự động. Chép sang là biến một đống chuỗi gõ tay bốn năm thành
một bảng quan hệ trông rất đáng tin — cùng dữ liệu, nhưng mất luôn dấu hiệu cho biết nó đáng ngờ.
"""
import datetime as dt
import os
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import User
from app.models.to_chuc_kd import CAP, CHA_HOP_LE, DonViKD, PhanCongKD
from app.services import access as AC
from app.services import to_chuc_kd as TC

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(ROOT, "web")
BE = os.path.join(ROOT, "backend")


def _doc(*p):
    return open(os.path.join(*p), encoding="utf-8").read()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _nguoi(db, ten, vai):
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _so():
    """Một chi nhánh, một phòng, hai team, và bốn tài khoản — đủ để hỏi mọi câu."""
    db = _db()
    hc = _nguoi(db, "hcns", "hcns")
    ct = TC.tao_don_vi(db, hc, "CT", "Chi nhánh Cần Thơ", "chi_nhanh",
                       hieu_luc_tu=dt.date(2026, 1, 1))
    p = TC.tao_don_vi(db, hc, "CT-P", "Phòng KDL Cần Thơ", "phong", cha_id=ct.id,
                      hieu_luc_tu=dt.date(2026, 1, 1))
    t1 = TC.tao_don_vi(db, hc, "CT-T1", "Team 1", "team", cha_id=p.id,
                       hieu_luc_tu=dt.date(2026, 1, 1))
    t2 = TC.tao_don_vi(db, hc, "CT-T2", "Team 2", "team", cha_id=p.id,
                       hieu_luc_tu=dt.date(2026, 1, 1))
    db.commit()
    return db, hc, ct, p, t1, t2


# ── 3. Cây không được gãy thứ bậc ──────────────────────────────────────────────────────────────

def test_team_phai_nam_duoi_phong():
    db, hc, ct, p, t1, t2 = _so()
    with pytest.raises(ValueError) as e:
        TC.tao_don_vi(db, hc, "CT-TX", "Team lạc", "team", cha_id=ct.id)
    assert "phong" in str(e.value)


def test_chi_nhanh_khong_duoc_co_cha():
    db, hc, ct, p, t1, t2 = _so()
    with pytest.raises(ValueError):
        TC.tao_don_vi(db, hc, "CT2", "Chi nhánh con", "chi_nhanh", cha_id=ct.id)


def test_ma_trung_bi_chan():
    db, hc, ct, p, t1, t2 = _so()
    with pytest.raises(ValueError) as e:
        TC.tao_don_vi(db, hc, "ct-t1", "Trùng mã viết thường", "chi_nhanh")
    assert "đã có" in str(e.value)


def test_khong_treo_don_vi_khac_mang():
    db, hc, ct, p, t1, t2 = _so()
    with pytest.raises(ValueError) as e:
        TC.tao_don_vi(db, hc, "DOAN-T", "Team đoàn", "team", mang="doan", cha_id=p.id)
    assert "mảng" in str(e.value)


def test_cha_hop_le_phu_du_moi_cap():
    """Mỗi cấp trừ cấp gốc phải khai cha hợp lệ — thêm cấp mới mà quên khai là cây gãy."""
    goc = [c for c in CAP if c not in CHA_HOP_LE]
    assert goc == ["chi_nhanh"], f"Chỉ được có đúng một cấp gốc, đang có: {goc}"
    for cap, cha in CHA_HOP_LE.items():
        assert cap in CAP and cha in CAP
        assert CAP.index(cha) == CAP.index(cap) - 1, f"{cap!r} phải treo ngay dưới cấp liền trên"


# ── Đơn vị không bị xoá, chỉ đóng ──────────────────────────────────────────────────────────────

def test_dong_don_vi_giu_lai_ban_ghi():
    db, hc, ct, p, t1, t2 = _so()
    TC.dong_don_vi(db, hc, t2.id, dt.date(2026, 6, 30), "Gộp vào Team 1")
    db.commit()
    assert db.get(DonViKD, t2.id) is not None, "Đóng đơn vị không được xoá bản ghi"
    assert t2.dang_hieu_luc(dt.date(2026, 6, 30)) is True
    assert t2.dang_hieu_luc(dt.date(2026, 7, 1)) is False


def test_dong_don_vi_phai_co_ly_do():
    db, hc, ct, p, t1, t2 = _so()
    with pytest.raises(ValueError):
        TC.dong_don_vi(db, hc, t2.id, dt.date(2026, 6, 30), "   ")


def test_khong_dong_cha_khi_con_dang_mo():
    db, hc, ct, p, t1, t2 = _so()
    with pytest.raises(ValueError) as e:
        TC.dong_don_vi(db, hc, p.id, dt.date(2026, 6, 30), "Giải thể phòng")
    assert "con" in str(e.value).lower()


# ── 2. Một người không được đếm ở hai team ─────────────────────────────────────────────────────

def test_phan_cong_chong_lan_bi_chan():
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    with pytest.raises(ValueError) as e:
        TC.phan_cong(db, hc, nv.id, t2.id, "nhan_vien", dt.date(2026, 5, 1))
    assert "phủ cùng một ngày" in str(e.value)


def test_phan_cong_noi_tiep_thi_duoc():
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1), dt.date(2026, 4, 30))
    TC.phan_cong(db, hc, nv.id, t2.id, "nhan_vien", dt.date(2026, 5, 1))
    db.commit()
    assert len(TC.lich_su_cua(db, nv.id)) == 2


def test_chong_lan_khac_mang_van_duoc():
    """Một người phụ trách cả Lẻ lẫn Đoàn là chuyện có thật — luật chống chồng lấn chỉ trong MỘT mảng."""
    db, hc, ct, p, t1, t2 = _so()
    dct = TC.tao_don_vi(db, hc, "D-CT", "Chi nhánh Cần Thơ (Đoàn)", "chi_nhanh", mang="doan",
                        hieu_luc_tu=dt.date(2026, 1, 1))
    db.commit()
    nv = _nguoi(db, "chi", "nv_kd")
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    TC.phan_cong(db, hc, nv.id, dct.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    assert TC.don_vi_cua(db, nv.id, dt.date(2026, 6, 1), "le").ma == "CT-T1"
    assert TC.don_vi_cua(db, nv.id, dt.date(2026, 6, 1), "doan").ma == "D-CT"


# ── 1. Báo cáo kỳ cũ KHÔNG được đổi số ─────────────────────────────────────────────────────────

def test_chuyen_team_khong_lam_doi_ky_cu():
    """Đây là phép thử quan trọng nhất của cả vòng.

    Người chuyển từ Team 1 sang Team 2 ngày 01/5. Hỏi "ngày 15/3 người này ở đâu" thì phải ra
    Team 1, mãi mãi — kể cả khi hôm nay họ đã ở Team 2 được nửa năm.
    """
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1), dt.date(2026, 4, 30))
    TC.phan_cong(db, hc, nv.id, t2.id, "nhan_vien", dt.date(2026, 5, 1), ly_do="Chuyển team")
    db.commit()
    assert TC.don_vi_cua(db, nv.id, dt.date(2026, 3, 15)).ma == "CT-T1"
    assert TC.don_vi_cua(db, nv.id, dt.date(2026, 4, 30)).ma == "CT-T1"
    assert TC.don_vi_cua(db, nv.id, dt.date(2026, 5, 1)).ma == "CT-T2"
    assert TC.don_vi_cua(db, nv.id, dt.date(2026, 9, 19)).ma == "CT-T2"


def test_den_ngay_rong_la_chua_ket_thuc_khong_phai_het_han():
    """RỖNG KHÁC KHÔNG, và cũng khác một ngày xa tít được điền thay cho rỗng."""
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    pc = TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    assert pc.den_ngay is None
    assert pc.dang_hieu_luc(dt.date(2099, 1, 1)) is True


def test_truoc_ngay_bat_dau_thi_chua_thuoc_don_vi_nao():
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 5, 1))
    db.commit()
    assert TC.don_vi_cua(db, nv.id, dt.date(2026, 4, 30)) is None


def test_ket_thuc_phan_cong_phai_co_ly_do():
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    pc = TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    with pytest.raises(ValueError):
        TC.ket_thuc_phan_cong(db, hc, pc.id, dt.date(2026, 6, 30), "")


# ── Phạm vi xem ────────────────────────────────────────────────────────────────────────────────

def test_pham_vi_gom_ca_cap_duoi():
    db, hc, ct, p, t1, t2 = _so()
    tp = _nguoi(db, "tp", "tp_kd")
    TC.phan_cong(db, hc, tp.id, p.id, "truong_phong", dt.date(2026, 1, 1))
    db.commit()
    pv = TC.pham_vi_xem(db, tp, dt.date(2026, 9, 19))
    assert set(pv) == {p.id, t1.id, t2.id}, "Trưởng phòng phải thấy cả hai team dưới phòng mình"
    assert ct.id not in pv, "…nhưng KHÔNG thấy ngược lên chi nhánh"


def test_leader_khong_thay_team_ben_canh():
    db, hc, ct, p, t1, t2 = _so()
    ld = _nguoi(db, "leader", "tn_kd")
    TC.phan_cong(db, hc, ld.id, t1.id, "leader", dt.date(2026, 1, 1))
    db.commit()
    assert TC.duoc_xem(db, ld, t1.id) is True
    assert TC.duoc_xem(db, ld, t2.id) is False
    assert TC.duoc_xem(db, ld, p.id) is False


def test_pham_vi_rong_khac_voi_xem_tat_ca():
    """`[]` = chưa ai phân công, `None` = xem tất cả. Trộn hai thứ là mở toang cho người chưa khai."""
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    assert TC.pham_vi_xem(db, nv) == [], "Chưa phân công thì phạm vi RỖNG"
    assert TC.duoc_xem(db, nv, t1.id) is False
    chu_tich = _nguoi(db, "ct", "chutich")
    assert TC.pham_vi_xem(db, chu_tich) is None, "Chủ tịch xem tất cả"
    assert TC.duoc_xem(db, chu_tich, t1.id) is True


def test_gd_kd_khong_xem_toan_cay_bang_chuc_danh():
    """Quyết định có chủ ý — xem khối "QUYẾT ĐỊNH" ở đầu services/to_chuc_kd.py.

    Giám đốc Kinh doanh nhìn toàn khối bằng DÒNG PHÂN CÔNG, không bằng tên chức danh. Bản bàn giao
    V5.0 viết đúng câu ấy: "không gán quyền chỉ bằng tên chức danh".
    """
    assert "gd_kd" not in TC.XEM_TOAN_CAY
    db, hc, ct, p, t1, t2 = _so()
    gd = _nguoi(db, "gd", "gd_kd")
    assert TC.pham_vi_xem(db, gd) == [], "Chức danh không tự cấp phạm vi"
    TC.phan_cong(db, hc, gd.id, ct.id, "giam_doc", dt.date(2026, 1, 1))
    db.commit()
    assert set(TC.pham_vi_xem(db, gd)) == {ct.id, p.id, t1.id, t2.id}


def test_don_vi_cua_lay_cap_thap_nhat():
    """Trưởng phòng kiêm bán hàng: chỗ làm việc hằng ngày là team, không phải cả phòng."""
    db, hc, ct, p, t1, t2 = _so()
    tp = _nguoi(db, "tp", "tp_kd")
    TC.phan_cong(db, hc, tp.id, p.id, "truong_phong", dt.date(2026, 1, 1))
    TC.phan_cong(db, hc, tp.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    assert TC.don_vi_cua(db, tp.id, dt.date(2026, 9, 19)).ma == "CT-T1"


# ── Danh sách đối chiếu ────────────────────────────────────────────────────────────────────────

def test_chua_phan_cong_liet_ke_dung_nguoi_kinh_doanh():
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    _nguoi(db, "dh", "nv_dh")          # không phải khối Kinh doanh – không được lọt vào danh sách
    assert [r["tai_khoan"] for r in TC.chua_phan_cong(db)] == ["chi"]
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    assert TC.chua_phan_cong(db) == []


def test_cay_dem_nguoi_dung_nut():
    """Số người đếm vào ĐÚNG nút được phân công, không cộng dồn lên cha — cộng dồn là cộng trùng."""
    db, hc, ct, p, t1, t2 = _so()
    nv = _nguoi(db, "chi", "nv_kd")
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    cay = TC.cay(db, "le", dt.date(2026, 9, 19))
    nut_ct = cay[0]
    assert nut_ct["ma"] == "CT" and nut_ct["so_nguoi"] == 0
    nut_t1 = nut_ct["con"][0]["con"][0]
    assert nut_t1["ma"] == "CT-T1" and nut_t1["so_nguoi"] == 1


# ── 4. Quyền không được nới ngoài ý muốn ───────────────────────────────────────────────────────

def test_ghi_hep_hon_xem_va_khong_co_gd_kd():
    from app.api.v1 import to_chuc_kd as API
    assert set(API.GHI) < set(API.XEM), "Mọi vai ghi được thì đương nhiên xem được"
    assert "gd_kd" in API.XEM, "Giám đốc Kinh doanh phải XEM được sơ đồ của khối mình"
    assert "gd_kd" not in API.GHI, (
        "Giám đốc Kinh doanh cố ý KHÔNG tự sửa được cây tổ chức: người tự vẽ được cây của mình là "
        "người tự cấp được phạm vi xem của mình. Muốn nới thì nới bằng ngoại lệ theo người "
        "(UserGrant, có hạn, có lý do), đừng nới cả vai trò.")


def test_tien_to_api_rieng_khong_gan_vao_nhom_co_san():
    """Bài học đã trả giá hai lần: gắn cửa mới vào tiền tố rộng là nới CẢ NHÓM cho mọi vai có nhóm ấy."""
    assert AC.MAN_HINH_API["/to-chuc-kd"] == ("/api/v1/to-chuc-kd",)
    for man, tien_to in AC.MAN_HINH_API.items():
        if man == "/to-chuc-kd":
            continue
        assert "/api/v1/to-chuc-kd" not in tien_to, (
            f"Tiền tố /api/v1/to-chuc-kd còn nằm trong nhóm của màn hình {man} – "
            "phần dôi ra vẫn là quyền đã cấp.")


def test_man_hinh_khai_trong_menu_roles():
    vai = AC.MENU_ROLES["/to-chuc-kd"]
    for phai_co in ("chutich", "tgd", "hcns", "cntt", "gd_kd", "tp_kd", "tn_kd", "nv_kd"):
        assert phai_co in vai, f"{phai_co} phải mở được sơ đồ tổ chức khối Kinh doanh"
    for khong_duoc in ("nv_visa", "tp_hd"):
        assert khong_duoc not in vai, f"{khong_duoc} không thuộc khối Kinh doanh"


# ── Ranh giới 09/9: không nhập hộ số liệu ──────────────────────────────────────────────────────

def test_migration_khong_chep_du_lieu_cu_sang():
    s = _doc(BE, "alembic", "versions", "tc73kd0a1b2c3d_to_chuc_kd.py")
    than = re.sub(r'"""[\s\S]*?"""|#[^\n]*', "", s)
    for cam in ("INSERT", "insert(", "sales_group", "department", "office"):
        assert cam not in than, (
            f"Bản alembic đang đụng tới {cam!r}. TC-73 chỉ TẠO BẢNG RỖNG: ba chuỗi chữ cũ gõ tay "
            "suốt bốn năm, chép sang là biến một đống không ai dám tin thành một bảng trông rất "
            "đáng tin. Hành chính – Nhân sự khai lại ở màn hình /to-chuc-kd.")


def test_man_hinh_khong_co_nut_suy_tu_dong():
    s = _doc(WEB, "app", "to-chuc-kd", "page.tsx")
    assert "/to-chuc-kd/don-vi" in s and "/to-chuc-kd/phan-cong" in s, "Màn hình phải có cửa nhập"
    assert "suy-tu" not in s and "derive" not in s, (
        "Màn hình cố ý KHÔNG có nút suy đơn vị từ sales_group – xem lời mở đầu của page.tsx.")


def test_menu_co_muc_co_cau_to_chuc():
    s = _doc(WEB, "lib", "cay_phan_he.ts")
    assert 'href: "/to-chuc-kd"' in s, "Dựng màn hình mà không treo vào menu thì không ai vào được"
    assert s.count('href: "/to-chuc-kd"') == 1, (
        "Chỉ một lối vào cho một màn hình – hai lối vào là cách chắc chắn để người dùng không biết "
        "nên bấm vào đâu (bài học TC-70).")
    for khoa in ('"kdle"', '"kddoan"'):
        i = s.index(f"khoa: {khoa}")
        doan = s[i:i + 400]
        assert '"3.6"' in doan, f"Phân hệ con {khoa} phải lấy được nhánh 3.6"


def test_bang_khong_giu_so_tien_nao():
    """Cơ cấu tổ chức chỉ trả lời "ai ở đâu, từ bao giờ". Chỉ tiêu và phân bổ là bảng của vòng sau."""
    for bang in (DonViKD, PhanCongKD):
        for cot in bang.__table__.columns:
            assert "tien" not in cot.name and "doanh_thu" not in cot.name and "gia_tri" not in cot.name, (
                f"{bang.__tablename__}.{cot.name} mang dáng một cột tiền. Gộp chỉ tiêu vào bảng cơ "
                "cấu thì mỗi lần đổi chỉ tiêu lại đụng vào tổ chức.")
