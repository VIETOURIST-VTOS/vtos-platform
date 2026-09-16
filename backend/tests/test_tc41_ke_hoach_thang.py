# -*- coding: utf-8 -*-
"""TC-41 · Cửa nhập KẾ HOẠCH THÁNG — anh Tuấn duyệt mở 15/9/2026 ("mục 4 = có").

VIỆC NÀY LÀ MỘT CỬA CÒN THIẾU, KHÔNG PHẢI MỘT SỐ CÒN THIẾU
══════════════════════════════════════════════════════════════════════════════════════════════
Ranh giới Chủ tịch đặt 09/9/2026: phần mềm viết cấu trúc, phép tính và hệ điều hành; SỐ LIỆU do
người của bộ phận tự nhập. Hệ quả trực tiếp: mỗi con số trên màn hình phải lần ngược được về MỘT
CỬA có người đứng — không có cửa thì đó là việc còn thiếu, không phải việc để chờ ai nạp số.

Thẻ "Doanh thu tháng" đã in câu "chưa có kế hoạch tháng để so sánh (Kế toán)" suốt bốn vòng. Câu
ấy đúng, nhưng nó không phải một trạng thái tạm — nó là bản thú nhận rằng trong toàn hệ thống
không có bảng nào giữ chỉ tiêu và không có màn hình nào để Kế toán gõ nó vào. Vòng này dựng cửa.

BỐN CHỖ DỄ HỎNG, CẢ BỐN CANH ĐƯỢC BẰNG MÁY
══════════════════════════════════════════════════════════════════════════════════════════════
1. CỘNG THIẾU PHÁP NHÂN RỒI GỌI LÀ KẾ HOẠCH HỢP NHẤT. Đây là chỗ nguy hiểm nhất của cả vòng, vì
   nó không trông giống lỗi: kế hoạch thấp hơn thật, tỉ lệ đạt cao vọt, và mọi con số đều có mặt.
2. Ô TRỐNG THÀNH SỐ 0. Kế hoạch bằng không đồng là một quyết định; chưa ai nhập là một chỗ trống.
3. SỬA THÁNG ĐÃ KHÉP MÀ KHÔNG ĐỂ LẠI DẤU. Một thước đo sửa được sau khi đã đo thì không còn là
   thước — nhưng khoá cứng thì người ta sửa ở ngoài hệ thống, và bảng này thành bảng chết.
4. CẮT PHẠM VI Ở GIAO DIỆN thay vì trong truy vấn (SEC-02). Giao diện chỉ giấu, không chặn.
"""
import datetime as dt
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import AuditLog, Company, User
from app.models.ke_hoach import KeHoachThang
from app.services import ke_hoach as KH

GOC = Path(__file__).resolve().parents[2]
DICH_VU = GOC / "backend" / "app" / "services" / "ke_hoach.py"
ROUTER = GOC / "backend" / "app" / "api" / "v1" / "ke_hoach.py"
MAIN = GOC / "backend" / "app" / "main.py"
ACCESS = GOC / "backend" / "app" / "services" / "access.py"
BANG_DIEU_KHIEN = GOC / "backend" / "app" / "services" / "dashboard.py"
MAN_HINH = GOC / "web" / "app" / "ke-hoach-thang" / "page.tsx"
SHELL = GOC / "web" / "components" / "Shell.tsx"
DAU = GOC / "web" / "components" / "DauManHinh01.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"
# TC-42 (16/9/2026): câu đọc hộ kế hoạch chuyển từ DauManHinh01 sang KhoiSauO, đi theo hai ô lớn
# Doanh thu và Lợi nhuận. Phép thử đổi CHỖ NHÌN, luật không đổi.
SAU_O = GOC / "web" / "components" / "KhoiSauO.tsx"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma(src: str) -> str:
    """Bỏ chú thích. Các tệp của vòng này ghi lại lý do rất dài, và gần như mọi chuỗi đáng cấm đều
    xuất hiện trong phần giải thích vì sao nó bị cấm."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    src = re.sub(r'^\s*"""(?:.|\n)*?"""', " ", src)
    return re.sub(r"^\s*#.*$", " ", src, flags=re.M)


# ═════════════════ 0 · SỔ GIẢ, DỰNG BẰNG CHÍNH MÔ HÌNH THẬT ═════════════════
#
# Phần lớn phép thử của vòng này đọc mã nguồn, vì phần lớn luật ở đây là luật về HÌNH DẠNG của mã.
# Nhưng ba luật lớn — thiếu pháp nhân là chưa có kế hoạch · ô trống khác số 0 · tháng đã khép đòi
# lý do — là luật về HÀNH VI, và hành vi thì chỉ chạy thật mới biết. Đọc mã chỉ chứng minh được
# rằng có một dòng `if` trông đúng.
#
# Dựng ĐÚNG những bảng cần và truyền thẳng `tables=`, không đụng `Base.metadata` chung: gỡ bảng ra
# khỏi sơ đồ chung rồi lắp lại là sửa một thứ dùng chung giữa chừng, và phép thử hỏng sẽ hiện ra ở
# một tệp KHÁC.

@pytest.fixture()
def db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=[Company.__table__, User.__table__,
                                        KeHoachThang.__table__, AuditLog.__table__])
    s = sessionmaker(bind=e)()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def so(db):
    """Hai pháp nhân hợp nhất, một công ty liên kết, một pháp nhân đã ngừng hoạt động.

    Ba loại sau đều PHẢI nằm ngoài phép cộng hợp nhất, và mỗi loại nằm ngoài vì một lý do khác
    nhau — nên cả ba đều có mặt trong sổ mẫu chứ không chỉ một.
    """
    db.add_all([
        Company(id=1, code="VTD", name="Vietourist Holdings", kind="me", active=True),
        Company(id=2, code="VTR", name="Vận tải Vietrip", kind="con", active=True),
        Company(id=3, code="LKT", name="Công ty liên kết", kind="lien_ket", active=True),
        Company(id=4, code="CU", name="Pháp nhân đã ngừng", kind="con", active=False),
    ])
    db.add(User(id=1, username="ketoan1", full_name="Kế toán", role="ketoan",
                password_hash="x", active=True))
    db.flush()
    return db


def _u(db):
    return db.get(User, 1)


def _ky_sau(n: int = 1) -> str:
    """Một kỳ CHƯA KHÉP, tính từ hôm nay.

    Viết cứng "2026-12" thì phép thử đúng tới hết năm 2026 rồi lặng lẽ đổi nghĩa: từ tháng 1/2027
    nó thành phép thử về tháng ĐÃ KHÉP, và nhánh nó định canh không còn được chạy nữa.
    """
    d = dt.date.today()
    thang = d.month + n
    return f"{d.year + (thang - 1) // 12:04d}-{(thang - 1) % 12 + 1:02d}"


def test_chi_cong_phap_nhan_trong_pham_vi_hop_nhat_va_dang_hoat_dong(so):
    ds = KH.phap_nhan_hop_nhat(so)
    assert [c.code for c in ds] == ["VTD", "VTR"], (
        "Công ty liên kết áp dụng phương pháp vốn chủ sở hữu nên không hợp nhất; pháp nhân đã "
        "ngừng hoạt động thì không còn chỉ tiêu. Cả hai lọt vào là thổi kế hoạch tập đoàn lên."
    )


def test_thieu_mot_phap_nhan_thi_ke_hoach_hop_nhat_la_rong_kem_ten_nguoi_thieu(so):
    """LUẬT 1 chạy thật — đây là phép thử quan trọng nhất của cả vòng.

    Nhập cho VTD, chưa nhập cho VTR. Nếu hàm cộng phần đã nhập lại thì màn hình Chủ tịch sẽ lấy
    doanh thu thực hiện của CẢ HAI pháp nhân chia cho kế hoạch của MỘT, và báo về một tỉ lệ đạt kế
    hoạch cao vọt mà không có gì trông giống lỗi.
    """
    ky = _ky_sau(3)
    KH.ghi(so, ky, 1, "doanh_thu", 10_000.0, "", _u(so))
    h = KH.hop_nhat(so, ky)
    assert h["doanh_thu"]["du"] is False
    assert h["doanh_thu"]["gia_tri"] is None, (
        "Chưa đủ thì giá trị hợp nhất phải RỖNG, không phải tổng của phần đã nhập."
    )
    assert h["doanh_thu"]["thieu"] == ["Vận tải Vietrip"], (
        "Phải kê đích danh pháp nhân còn thiếu — 'thiếu 1 pháp nhân' không giúp ai đi đòi."
    )

    KH.ghi(so, ky, 2, "doanh_thu", 4_000.0, "", _u(so))
    h = KH.hop_nhat(so, ky)
    assert h["doanh_thu"]["du"] is True and h["doanh_thu"]["gia_tri"] == 14_000.0
    # Chỉ tiêu KIA vẫn chưa ai nhập, và nó độc lập hoàn toàn với chỉ tiêu vừa đủ.
    assert h["loi_nhuan_truoc_thue"]["du"] is False


def test_o_de_trong_bi_xoa_chu_khong_bi_dat_ve_khong(so):
    ky = _ky_sau(3)
    KH.ghi(so, ky, 1, "doanh_thu", 10_000.0, "", _u(so))
    KH.ghi(so, ky, 1, "doanh_thu", None, "", _u(so))
    assert KH._dong(so, ky, 1, "doanh_thu") is None, (
        "Lưu ô trống phải XOÁ dòng. Ghi 0 vào thay là biến 'chưa ai nhập' thành 'chỉ tiêu bằng "
        "không đồng' — hai câu hoàn toàn khác nhau, và cột Hợp nhất sẽ cộng con số 0 ấy vào."
    )


def test_thang_da_khep_doi_ly_do_va_dem_so_lan_sua(so):
    ky_cu = KH.ky_cua(dt.date(2020, 1, 15))          # chắc chắn đã khép
    with pytest.raises(ValueError) as e:
        KH.ghi(so, ky_cu, 1, "doanh_thu", 500.0, "", _u(so))
    assert "đã khép" in str(e.value)

    with pytest.raises(ValueError):
        KH.ghi(so, ky_cu, 1, "doanh_thu", 500.0, "gõ nhầm", _u(so))   # lý do quá ngắn

    KH.ghi(so, ky_cu, 1, "doanh_thu", 500.0, "Nghị quyết HĐQT điều chỉnh chỉ tiêu", _u(so))
    r = KH._dong(so, ky_cu, 1, "doanh_thu")
    assert r.so_lan_sua_muon == 1 and "HĐQT" in r.ly_do_sua

    # Lưu lại ĐÚNG giá trị đang có không phải một lần sửa — nếu không, mỗi lần bấm Lưu cả bảng là
    # mọi dòng tăng thêm một lần, và cột đếm ấy lập tức vô nghĩa.
    kq = KH.ghi(so, ky_cu, 1, "doanh_thu", 500.0, "", _u(so))
    assert kq["trang_thai"] == "khong_doi"
    assert KH._dong(so, ky_cu, 1, "doanh_thu").so_lan_sua_muon == 1


def test_thang_dang_chay_va_thang_toi_sua_tu_do(so):
    nay = KH.ky_cua(dt.date.today())
    KH.ghi(so, nay, 1, "doanh_thu", 700.0, "", _u(so))
    assert KH._dong(so, nay, 1, "doanh_thu").so_lan_sua_muon == 0, (
        "Tháng đang chạy sửa tự do: đòi lý do ở đây là bắt Kế toán giải trình cho việc đang làm."
    )


def test_khong_noi_suy_thang_trong(so):
    """Tháng trước có kế hoạch KHÔNG làm tháng sau có kế hoạch."""
    day, sau = _ky_sau(1), _ky_sau(2)
    KH.ghi(so, day, 1, "doanh_thu", 10_000.0, "", _u(so))
    KH.ghi(so, day, 2, "doanh_thu", 4_000.0, "", _u(so))
    assert KH.hop_nhat(so, day)["doanh_thu"]["du"] is True
    assert KH.hop_nhat(so, sau)["doanh_thu"]["gia_tri"] is None, (
        "Tháng 12 chưa ai nhập thì nó TRỐNG — không lấy tháng 11 làm lối lui."
    )


def test_chi_tieu_la_hoi_va_ky_sai_dang_deu_bi_tu_choi(so):
    with pytest.raises(ValueError):
        KH.ghi(so, _ky_sau(1), 1, "so_khach", 10.0, "", _u(so))
    with pytest.raises(ValueError):
        KH.ghi(so, "2026-13", 1, "doanh_thu", 10.0, "", _u(so))
    with pytest.raises(ValueError):
        KH.ghi(so, _ky_sau(1), 3, "doanh_thu", 10.0, "", _u(so))   # công ty liên kết
    with pytest.raises(ValueError):
        KH.ghi(so, _ky_sau(1), 4, "doanh_thu", 10.0, "", _u(so))   # đã ngừng hoạt động


def test_moi_lan_ghi_de_lai_mot_dong_nhat_ky_co_ca_gia_tri_cu(so):
    ky = _ky_sau(1)
    KH.ghi(so, ky, 1, "doanh_thu", 10_000.0, "", _u(so))
    KH.ghi(so, ky, 1, "doanh_thu", 12_000.0, "", _u(so))
    nk = so.query(AuditLog).order_by(AuditLog.id).all()
    assert len(nk) == 2
    assert nk[1].before == {"gia_tri": 10_000.0}, (
        "Nhật ký chỉ giữ giá trị mới thì ba tháng sau biết ai sửa mà không biết sửa từ bao nhiêu."
    )
    assert nk[1].after["gia_tri"] == 12_000.0


def test_doc_nam_tra_du_muoi_hai_thang_va_o_chua_nhap_la_None(so):
    ky = _ky_sau(1)
    nam = int(ky.split("-")[0])
    KH.ghi(so, ky, 1, "doanh_thu", 900.0, "", _u(so))
    b = KH.doc_nam(so, nam, _u(so))
    assert len(b["thang"]) == 12, "Tháng chưa ai nhập vẫn phải có mặt — đó là ô để người ta điền."
    t5 = [t for t in b["thang"] if t["ky"] == ky][0]
    co = [o for o in t5["o"] if o["company_id"] == 1 and o["chi_tieu"] == "doanh_thu"][0]
    chua = [o for o in t5["o"] if o["company_id"] == 2 and o["chi_tieu"] == "doanh_thu"][0]
    assert co["gia_tri"] == 900.0
    assert chua["gia_tri"] is None, "Ô chưa nhập phải là None, tuyệt đối không phải 0."


# ═════════════════ 1 · MÃ KỲ VÀ MỐC KHÉP ═════════════════

def test_ky_cua_dem_thang_co_so_khong_dung_dau():
    assert KH.ky_cua(dt.date(2026, 9, 16)) == "2026-09"
    # Tháng một chữ số PHẢI có số 0 đứng đầu: mã kỳ được so sánh bằng phép so CHUỖI ở `da_khep`,
    # và "2026-9" > "2026-10" khi so chuỗi — tức là tháng 9 bị coi là sau tháng 10.
    assert KH.ky_cua(dt.date(2026, 1, 5)) == "2026-01"


@pytest.mark.parametrize("ky,hop_le", [
    ("2026-09", True), ("2026-01", True), ("2026-12", True),
    ("2026-13", False),     # tháng 13
    ("2026-00", False),     # tháng 0
    ("2026-9", False),      # thiếu số 0 đứng đầu
    ("26-09", False), ("thang sau", False), ("", False),
])
def test_ky_sai_dang_bi_chan_o_cua(ky, hop_le):
    """Cột `ky` là CHUỖI, nên cơ sở dữ liệu nhận hết. Một dòng mang kỳ '2026-13' không báo lỗi ở
    đâu cả; nó chỉ làm mọi phép so sánh kỳ sau đó âm thầm trả về sai."""
    assert KH.hop_le_ky(ky) is hop_le


@pytest.mark.parametrize("ky,khep", [
    ("2026-08", True),      # tháng đã qua
    ("2026-09", False),     # tháng đang chạy — còn sửa tự do
    ("2026-10", False),     # tháng tương lai
    ("2025-12", True),
])
def test_thang_da_qua_thi_khep(ky, khep):
    assert KH.da_khep(ky, dt.date(2026, 9, 16)) is khep


def test_moc_khep_la_moc_lich_va_ghi_ro_con_no_moc_ket_so():
    """Mốc khép TẠM dùng lịch, không dùng kỳ kết sổ kế toán — và tệp phải nói ra điều ấy.

    Chọn mốc lịch không bao giờ sai theo hướng nguy hiểm: nó khoá SỚM hơn mốc kết sổ, tức là đòi lý
    do ở vài ngày đáng ra chưa cần đòi, chứ không thả lỏng những ngày đáng ra phải đòi. Nhưng đó là
    một món nợ, và món nợ không ghi ra thì vòng sau đọc mã tưởng đây là thiết kế cuối cùng.
    """
    nguon = _doc(DICH_VU)
    assert "kết sổ" in nguon.lower(), (
        "services/ke_hoach.py phải ghi rõ mốc khép hiện là mốc lịch và còn nợ mốc kết sổ."
    )


# ═════════════════ 2 · KHÔNG CÓ KẾ HOẠCH KHÁC VỚI KẾ HOẠCH BẰNG 0 ═════════════════

@pytest.mark.parametrize("thuc_hien,ke_hoach,mong", [
    (800.0, 1000.0, 0.8),
    (0.0, 1000.0, 0.0),        # làm được 0 đồng trên chỉ tiêu 1000 → đạt 0%, một câu có nghĩa
    (800.0, None, None),       # chưa có kế hoạch → KHÔNG có tỉ lệ
    (None, 1000.0, None),      # chưa có thực hiện → KHÔNG có tỉ lệ
    (800.0, 0.0, None),        # "đạt bao nhiêu phần trăm của 0" là câu không có nghĩa
    (0.0, 0.0, None),
])
def test_ty_le_dat_khong_tra_loi_cau_khong_co_nghia(thuc_hien, ke_hoach, mong):
    assert KH.ty_le_dat(thuc_hien, ke_hoach) == mong


def test_dich_vu_khong_lay_khong_lam_loi_lui_cho_o_trong():
    """Không có `or 0`, `?? 0`, `coalesce(..., 0)` trên giá trị kế hoạch.

    Một lối lui về 0 ở đây làm đúng điều mà cả khối này đang chống: biến "chưa ai lập kế hoạch"
    thành "kế hoạch bằng không đồng", và cột Hợp nhất sẽ cộng con số ấy vào như một chỉ tiêu thật.
    """
    ma = _ma(_doc(DICH_VU))
    for xau in ("gia_tri or 0", "gia_tri, 0", "or 0.0", "coalesce"):
        assert xau not in ma, f"services/ke_hoach.py không được dùng lối lui '{xau}'."


def test_man_hinh_nhap_khong_dien_0_vao_o_trong():
    ma = _ma(_doc(MAN_HINH))
    for xau in ("?? 0", "|| 0"):
        assert xau not in ma, (
            f"Màn hình nhập không được dùng '{xau}' trên giá trị kế hoạch: ô rỗng phải hiện ra rỗng."
        )
    # Ô để trống gửi lên `null`, và máy chủ XOÁ dòng. Gửi 0 là nói "chỉ tiêu bằng không đồng".
    assert "docSo" in ma, "Phải có hàm đọc số riêng, phân biệt ô để trống với ô gõ sai."


def test_gia_tri_none_la_xoa_o_chu_khong_phai_dat_bang_khong():
    nguon = _doc(DICH_VU)
    assert "db.delete(r)" in nguon, (
        "gia_tri=None phải XOÁ dòng. Ghi 0 vào thay là biến một ô chưa nhập thành một chỉ tiêu."
    )


# ═════════════════ 3 · LUẬT LỚN: THIẾU MỘT PHÁP NHÂN LÀ CHƯA CÓ KẾ HOẠCH ═════════════════

def test_hop_nhat_tra_ve_danh_sach_thieu_chu_khong_tra_ve_tong_mot_phan():
    """Chỗ nguy hiểm nhất của vòng này, nên canh ở cả mã lẫn chữ.

    Kế toán nhập xong ba pháp nhân, còn hai để mai. Cộng ba pháp nhân đã nhập rồi gọi kết quả là
    "kế hoạch tháng của tập đoàn" cho ra một con số NHỎ HƠN thật — nhưng trông không khác gì một
    con số đầy đủ. Màn hình Chủ tịch lấy doanh thu thực hiện của cả năm pháp nhân chia cho kế hoạch
    của ba, và báo về một tỉ lệ đạt kế hoạch cao vọt. Không ai phát hiện, vì không có gì trông
    giống lỗi cả.
    """
    nguon = _doc(DICH_VU)
    assert '"thieu"' in nguon or "'thieu'" in nguon or "thieu:" in nguon or "thieu," in nguon, (
        "hop_nhat() phải trả về danh sách pháp nhân CÒN THIẾU, không chỉ trả về một con số."
    )
    ma = _ma(nguon)
    assert "du = len(cty) > 0 and not thieu" in ma, (
        "Cờ `du` phải đòi ĐỦ mọi pháp nhân, và phải chặn luôn trường hợp danh sách pháp nhân rỗng "
        "— không pháp nhân nào thì tổng bằng 0, và 0 ấy không phải một kế hoạch."
    )
    assert '"gia_tri": tong if du else None' in ma, (
        "Chưa đủ thì giá trị hợp nhất là None, KHÔNG phải tổng của phần đã nhập."
    )


def test_man_hinh_01_giu_du_ba_trang_thai_cua_ke_hoach():
    """Chưa ai nhập · nhập thiếu pháp nhân · đủ. Ba câu khác hẳn nhau.

    SỬA 16/9/2026 (TC-42): hàm đổi tên thành `docHoKeHoachKy` và sang KhoiSauO.tsx cùng hai ô lớn.
    Nó biết thêm một việc bản cũ không biết — kế hoạch CHỈ có cho kỳ tháng — nên phép thử canh
    thêm nhánh thứ tư ấy.
    """
    sau_o = _doc(SAU_O)
    assert "docHoKeHoachKy" in sau_o, "Câu đọc hộ kế hoạch phải là một hàm riêng, kiểm được."
    assert "Chưa có kế hoạch tháng" in sau_o, "Thiếu nhánh 'chưa ai nhập'."
    assert "chưa đủ" in sau_o and "còn thiếu" in sau_o, "Thiếu nhánh 'nhập thiếu pháp nhân'."
    assert "đạt" in sau_o, "Thiếu nhánh 'đủ' — nơi in chỉ tiêu và tỉ lệ đạt."
    assert 'if (ky !== "thang")' in _ma(sau_o), (
        "Bấm sang Quý mà vẫn vẽ vạch mốc dựng từ KẾ HOẠCH THÁNG là bịa ra một chỉ tiêu chưa ai "
        "duyệt: chỉ tiêu quý và năm là quyết định riêng của Hội đồng quản trị, không phải tổng "
        "ba tháng."
    )
    # Cả HAI ô lớn đều so với kế hoạch, không chỉ ô Doanh thu.
    assert sau_o.count("docHoKeHoachKy(ky") >= 2, (
        "Cả ô Doanh thu lẫn ô Lợi nhuận trước thuế đều phải so với kế hoạch."
    )


def test_man_hinh_khong_tu_tinh_ty_le_dat():
    """Ranh giới 09/9: phép chia nằm ở máy chủ. Màn hình chỉ nhân 100 để in phần trăm."""
    for tep in (DAU, MAN_HINH, TRANG, SAU_O):
        ma = _ma(_doc(tep))
        assert "/ ke_hoach" not in ma and "/ o.gia_tri" not in ma, (
            f"{tep.name} đang tự chia thực hiện cho kế hoạch — phép ấy thuộc về máy chủ."
        )


def test_bang_dieu_khien_goi_hop_nhat_va_khong_tu_cong():
    ma = _ma(_doc(BANG_DIEU_KHIEN))
    assert "KH.hop_nhat(db" in ma, "dashboard phải gọi ke_hoach.hop_nhat, không tự cộng lấy."
    assert "KH.ty_le_dat(" in ma, "Tỉ lệ đạt phải do services/ke_hoach tính."


# ═════════════════ 4 · THÁNG ĐÃ KHÉP: SỬA ĐƯỢC, NHƯNG PHẢI ĐỂ LẠI DẤU ═════════════════

def test_ly_do_phai_du_dai_de_doc_ra_chuyen_gi():
    assert KH.DAI_TOI_THIEU_LY_DO >= 10, (
        "Ô lý do cho phép gõ 'ok' thì trong vòng một tháng mọi lý do trong bảng đều là 'ok', và "
        "cột lý do thành cột trang trí."
    )


def test_dich_vu_doi_ly_do_va_dem_so_lan_sua_muon():
    ma = _ma(_doc(DICH_VU))
    assert "if khep and len(ly_do) < DAI_TOI_THIEU_LY_DO" in ma, (
        "Sửa tháng đã khép phải bị chặn khi lý do quá ngắn."
    )
    assert "so_lan_sua_muon" in ma, (
        "Phải đếm số lần sửa muộn: một dòng sửa bảy lần thì con số bảy đã là câu hỏi, trước cả khi "
        "đọc từng lý do."
    )
    assert 'cu == gia_tri' in ma, (
        "Lưu đúng giá trị đang có KHÔNG được tính là một lần sửa — nếu không, mỗi lần bấm Lưu cả "
        "bảng là mọi dòng tăng thêm một lần, và cột đếm ấy lập tức vô nghĩa."
    )


def test_ghi_de_lai_ca_gia_tri_cu_trong_nhat_ky():
    ma = _ma(_doc(DICH_VU))
    assert "R.audit(" in ma, "Mọi lần ghi phải vào nhật ký bất biến."
    assert "before=" in ma and "after=" in ma, (
        "Nhật ký phải giữ CẢ giá trị cũ lẫn mới: chỉ giữ giá trị mới thì ba tháng sau biết ai sửa "
        "mà không biết sửa từ bao nhiêu — tức là không biết sửa nhiều hay ít."
    )


def test_khoa_duy_nhat_lam_thao_tac_luu_thanh_ghi_de():
    mh = GOC / "backend" / "app" / "models" / "ke_hoach.py"
    ma = _ma(_doc(mh))
    assert "UniqueConstraint" in ma and '"ky", "company_id", "chi_tieu"' in ma, (
        "Thiếu khoá duy nhất thì bảng kế hoạch THÊM DÒNG được, và đến cuối năm một tháng có ba con "
        "số doanh thu mà không ai biết con số nào là chỉ tiêu đã chốt."
    )


# ═════════════════ 5 · PHẠM VI PHÁP NHÂN CẮT TRONG TRUY VẤN (SEC-02) ═════════════════

def test_cot_phap_nhan_dat_dung_ten_company_id():
    """`pham_vi_phap_nhan.bang_co_cot_phap_nhan()` QUÉT mô hình tìm cột tên `company_id`.

    Đặt tên khác đi — `phap_nhan_id` chẳng hạn — thì bảng này lọt khỏi phép đo độ phủ pháp nhân,
    khỏi hàm lọc phạm vi và khỏi bộ kiểm SEC-02. Im lặng, không lỗi nào.
    """
    from app.models.ke_hoach import KeHoachThang
    assert "company_id" in KeHoachThang.__table__.c, (
        "Cột pháp nhân phải tên là company_id để hệ phạm vi nhìn thấy bảng này."
    )


def test_cat_dong_nam_trong_truy_van_khong_o_giao_dien():
    ma = _ma(_doc(DICH_VU))
    assert "PV.loc(q, KeHoachThang, u)" in ma, (
        "Phải lọc phạm vi NGAY TRONG truy vấn. Trả cả bảng rồi để giao diện lọc là cách một người "
        "mở công cụ nhà phát triển đọc được kế hoạch của pháp nhân mình không có quyền xem."
    )
    assert "PV.pham_vi(u)" in ma, "Cửa ghi phải chặn người bị giới hạn ghi sang pháp nhân khác."

    # Màn hình KHÔNG tự lọc pháp nhân: nó bày đúng danh sách máy chủ gửi. Lọc ở đây nghĩa là máy
    # chủ đã gửi xuống cả phần không được xem rồi, và trình duyệt chỉ giấu đi.
    giao_dien = _ma(_doc(MAN_HINH))
    assert "phap_nhan.filter" not in giao_dien and "phap_nhan.slice" not in giao_dien, (
        "Màn hình không được cắt bớt danh sách pháp nhân — phần bị cắt vẫn đã rời khỏi máy chủ."
    )


def test_chi_hop_nhat_moi_cong_va_chi_cong_pham_nhan_trong_pham_vi_hop_nhat():
    ma = _ma(_doc(DICH_VU))
    assert 'KIND_HOP_NHAT = ("me", "con", "chi_nhanh")' in ma, (
        "Công ty liên kết áp dụng phương pháp vốn chủ sở hữu nên doanh thu của nó KHÔNG cộng vào "
        "doanh thu hợp nhất; cộng vào là thổi doanh thu tập đoàn lên đúng bằng phần không hợp nhất."
    )


# ═════════════════ 6 · CỬA PHẢI CÓ ĐƯỜNG TỚI, VÀ QUYỀN XEM KHÁC QUYỀN GHI ═════════════════

def test_router_duoc_dang_ky_trong_main():
    """Ba lần trong tuần 11/9 một phân hệ viết xong mà quên dòng đăng ký router: mã có đủ, đường
    dẫn trả 404, và không phép thử nào kêu vì không ai gọi thử."""
    ma = _ma(_doc(MAIN))
    assert "from app.api.v1.ke_hoach import router as ke_hoach_router" in ma
    assert "app.include_router(ke_hoach_router)" in ma


def test_quyen_xem_rong_hon_quyen_ghi():
    ma = _ma(_doc(ROUTER))
    assert "XEM = (" in ma and "GHI = (" in ma, "Phải có HAI danh sách, không phải một."
    xem = re.search(r"XEM = \(([^)]*)\)", ma).group(1)
    ghi = re.search(r"GHI = \(([^)]*)\)", ma).group(1)
    assert "bks" in xem and "bks" not in ghi, (
        "Ban Kiểm soát ĐỌC được chỉ tiêu để đối chiếu, nhưng không SỬA được thước đo mà mình đang "
        "dùng để đo."
    )
    assert "ketoan" in ghi, "Kế toán là cửa nhập chính."
    assert "chutich" in ghi, (
        "Chủ tịch phải sửa được khi Hội đồng quản trị điều chỉnh, không phải mượn tài khoản Kế toán."
    )


def test_man_hinh_co_trong_ma_tran_quyen_va_co_muc_menu():
    acc = _doc(ACCESS)
    assert '"/ke-hoach-thang": ("/api/v1/ke-hoach",)' in acc, (
        "Màn hình phải khai phạm vi API, và phạm vi ấy phải HẸP: chỉ nhánh /ke-hoach."
    )
    assert acc.count('"/ke-hoach-thang": BASE_VIEW') == 2, (
        "Phải khai ở CẢ HAI chỗ (MAN_HINH_API và MENU_ROLES). Lệch một chỗ là có vai trò thấy mục "
        "menu rồi bấm vào nhận 403, hoặc mở được màn hình mà không có mục menu để tới nó."
    )
    assert '["Kế hoạch tháng", "/ke-hoach-thang"]' in _doc(SHELL), (
        "Cửa nhập không có mục menu là một cửa không ai tìm thấy."
    )


def test_mot_bang_cho_ca_nam_khong_phai_muoi_hai_khung_giong_nhau():
    """Bản đầu của màn hình này dựng mỗi tháng MỘT khung riêng, mỗi khung có tiêu đề, bảng và nút
    Lưu của nó. Đọc mã thì hợp lý; dựng ra ảnh mới thấy mười hai khung gần trùng khít nhau, dài hơn
    bốn màn hình, và cái người ta thật sự muốn — so tháng này với tháng kia — thì không làm được vì
    hai tháng không bao giờ nằm cùng tầm mắt.

    Đúng điều anh Tuấn chốt ở vòng TC-40: "những phần lặp lại thì bỏ". Ghim lại để vòng sau không
    tách ra lần nữa với lý do "mỗi tháng một khung cho rõ".
    """
    ma = _ma(_doc(MAN_HINH))
    assert ma.count("<section") <= 1, (
        "Cả năm nằm trong MỘT bảng, mỗi tháng một DÒNG — không phải mười hai khung giống nhau."
    )
    assert "rowSpan={2}" in ma and "colSpan={b.chi_tieu.length}" in ma, (
        "Tiêu đề hai tầng: tầng trên pháp nhân, tầng dưới chỉ tiêu. Gộp một tầng thì nhãn cột dài "
        "gấp đôi mà vẫn phải đọc từng chữ."
    )


def test_nhan_chi_tieu_khong_deo_lop_num():
    """Bài học chỉ dựng ảnh mới thấy, nên ghim lại bằng phép thử.

    Lớp `.num` đổi sang phông chữ đơn cách, và phông ấy KHÔNG có chữ "Ế": nhãn "LỢI NHUẬN TRƯỚC
    THUẾ" in ra thành "THUÊ´" — dấu sắc rơi ra thành một ký tự riêng đứng sau. Đọc mã thì đoạn ấy
    trông hoàn toàn bình thường.
    """
    ma = _ma(_doc(MAN_HINH))
    assert '{c.ten}</th>' in ma, "Nhãn chỉ tiêu phải nằm ở ô tiêu đề."
    assert 'className="num">{c.ten}' not in ma, (
        'Nhãn chỉ tiêu không được đeo lớp .num — phông đơn cách của lớp ấy thiếu chữ "Ế".'
    )


def test_man_hinh_khong_doc_doanh_thu_thuc_hien():
    """Chỗ so kế hoạch với thực hiện là màn hình 01. Kéo con số thực hiện về màn hình nhập để
    "tiện đối chiếu" là dựng phép so thứ hai cho cùng một câu hỏi — và hai phép so thì sớm muộn ra
    hai kết quả. Một con số, một chỗ, một hình (luật TC-40)."""
    ma = _ma(_doc(MAN_HINH))
    assert "/dashboard" not in ma, "Màn hình nhập kế hoạch không được gọi bảng điều khiển."
    acc = _doc(ACCESS)
    i = acc.find('"/ke-hoach-thang": ("/api/v1/ke-hoach",)')
    assert "/api/v1/dashboard" not in acc[i:i + 200], (
        "Phạm vi API của màn hình này không được kèm /dashboard."
    )
