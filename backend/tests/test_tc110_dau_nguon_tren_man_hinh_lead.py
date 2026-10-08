"""TC-110 · Dấu nguồn quảng cáo hiện ra màn hình lead — CẢ lần chạm đầu LẪN lần chạm cuối.

Chỗ hổng tìm ra ngày 08/10/2026: bảng `dau_quang_cao` có cột `lead_id` trỏ sang lead từ TC-106,
nhưng chiều ngược lại chưa ai nối. Cửa `GET /leads` trả 23 khoá — số điện thoại, kênh, tháng,
sale, trạng thái, booking, hạn xử lý — KHÔNG một khoá nào nói khách từ quảng cáo nào tới. Nên ba
bộ gửi Meta / TikTok / Zalo dựng xong tuần này đang ghi dấu vào một bảng mà không màn hình nào
đọc.

Chủ tịch chốt 08/10/2026: hiện CẢ HAI lần chạm, hai cột riêng. Lần đầu là kênh MANG KHÁCH ĐẾN,
lần cuối là kênh CHỐT ĐƯỢC; chênh lệch giữa hai cột mới là chỗ cho thấy kênh nào đang nuôi quỹ
khách mà không được ghi công — và đó đúng là câu hỏi phòng Marketing cần trả lời khi chia ngân
sách.

SÁU ĐIỀU TỆP NÀY CANH:

  1. ĐẦU LÀ ĐẦU, CUỐI LÀ CUỐI, xếp theo `cham_luc` chứ không theo thứ tự ghi vào bảng.
  2. `cham_luc` RỖNG thì xếp nhờ `nhan_luc`, NHƯNG ô trả về vẫn rỗng — không lấy giờ VTOS ghi
     lấp vào chỗ giờ khách chạm. Lấp là bịa một mốc, và mốc bịa đi thẳng vào phép đếm 30/60/90.
  3. LEAD KHÔNG CÓ DẤU NÀO thì trả None, không trả một khối toàn chuỗi rỗng. Rỗng khác không.
  4. MỘT CÂU HỎI CHO CẢ TRANG. Màn hình lead trả tới 2000 dòng; hỏi từng dòng là 2000 câu.
  5. CỬA DANH SÁCH PHẢI DÙNG BẢN GOM SẴN. Hàng rào này canh đúng chỗ N+1 hay quay lại.
  6. QUYỀN SỬA TRÊN MÀN HÌNH KHỚP `EDIT_ROLES` CỦA MÁY CHỦ. Trước hôm nay màn hình hẹp hơn máy
     chủ: tn_kd, tp_kd, nv_mkt được phép sửa mà không thấy nút nào.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.core import User  # noqa: F401  – bảng mà khoá ngoại của Lead trỏ tới
from app.models.crm import Lead
from app.models.quang_cao import DauQuangCao
from app.services import dau_quang_cao as DQC
from app.services import leads as L

GOC = Path(__file__).resolve().parents[1]
WEB = GOC.parents[0] / "web" / "app" / "leads" / "page.tsx"
BAY_GIO = datetime(2026, 10, 8, 12, 0, 0)


@pytest.fixture()
def may():
    m = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                         connect_args={"check_same_thread": False})
    Base.metadata.create_all(m)
    return m


@pytest.fixture()
def db(may):
    with Session(may) as s:
        yield s


_dem = [0]


def _lead(db, **kw):
    _dem[0] += 1
    d = {"phone": f"091000{_dem[0]:04d}", "channel": "Facebook", "lead_month": "2026-10",
         "received_at": BAY_GIO, "status": "moi"}
    d.update(kw)
    l = Lead(**d)
    db.add(l)
    db.flush()
    return l


def _dau(db, lead, nen_tang, gio_cham, gio_ghi=None, ten=""):
    r = DauQuangCao(nen_tang=nen_tang, loai_ma="khac", ma="",
                    khoa_chong_trung=f"{nen_tang}:{lead.id}:{gio_ghi or gio_cham}:{_dem[0]}",
                    ten_chien_dich=ten, sdt=lead.phone, zalo_uid="", lead_id=lead.id, utm={},
                    cham_luc=gio_cham, nhan_luc=gio_ghi or (gio_cham or BAY_GIO),
                    nguon_ghi="web")
    db.add(r)
    db.flush()
    return r


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · ĐẦU LÀ ĐẦU, CUỐI LÀ CUỐI
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_dau_va_cuoi_xep_theo_gio_cham_chu_khong_theo_thu_tu_ghi(db):
    """Dấu vào bảng theo thứ tự webhook về, không theo thứ tự khách chạm. Hai thứ khác nhau."""
    l = _lead(db)
    # Ghi NGƯỢC thứ tự thật: cái chạm sau cùng lại vào bảng trước.
    _dau(db, l, "google", BAY_GIO - timedelta(days=1), ten="Search thương hiệu")
    _dau(db, l, "facebook", BAY_GIO - timedelta(days=10), ten="Tour Nhật tháng 11")
    _dau(db, l, "tiktok", BAY_GIO - timedelta(days=5))

    k = DQC.dau_dau_cuoi(db, [l.id])[l.id]
    assert k["dau_cham_dau"]["nen_tang"] == "facebook", (
        "Lần chạm ĐẦU phải là cái sớm nhất theo `cham_luc`, không phải dòng vào bảng trước. "
        f"Đang trả: {k['dau_cham_dau']}")
    assert k["dau_cham_cuoi"]["nen_tang"] == "google", (
        f"Lần chạm CUỐI phải là cái muộn nhất theo `cham_luc`. Đang trả: {k['dau_cham_cuoi']}")
    assert k["so_lan_cham"] == 3
    assert k["dau_cham_dau"]["ten_chien_dich"] == "Tour Nhật tháng 11"


def test_mot_lan_cham_thi_dau_va_cuoi_la_cung_mot_cai(db):
    l = _lead(db)
    _dau(db, l, "zalo", BAY_GIO - timedelta(hours=3))
    k = DQC.dau_dau_cuoi(db, [l.id])[l.id]
    assert k["so_lan_cham"] == 1
    assert k["dau_cham_dau"] == k["dau_cham_cuoi"]


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · GIỜ CHẠM RỖNG: XẾP NHỜ GIỜ GHI, NHƯNG KHÔNG BỊA RA GIỜ CHẠM
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_gio_cham_rong_van_xep_duoc_va_o_tra_ve_van_rong(db):
    """Mã khuyến mãi và tệp nạp thường không kèm giờ chạm. Bỏ qua chúng là mất cả một kênh."""
    l = _lead(db)
    _dau(db, l, "su_kien", None, gio_ghi=BAY_GIO - timedelta(days=20))
    _dau(db, l, "google", BAY_GIO - timedelta(days=2))

    k = DQC.dau_dau_cuoi(db, [l.id])[l.id]
    assert k["so_lan_cham"] == 2, "Dấu không có giờ chạm vẫn phải được đếm, không bị loại."
    assert k["dau_cham_dau"]["nen_tang"] == "su_kien", (
        "Thiếu `cham_luc` thì xếp nhờ `nhan_luc` — dòng ghi từ 20 ngày trước vẫn là lần chạm đầu.")
    assert k["dau_cham_dau"]["cham_luc"] is None, (
        "Ô `cham_luc` trả về phải GIỮ NGUYÊN RỖNG. Lấy `nhan_luc` lấp vào là bịa ra một mốc giờ "
        "khách chưa từng chạm, và mốc bịa ấy đi thẳng vào phép đếm 30 / 60 / 90 ngày.")
    assert k["dau_cham_dau"]["nhan_luc"] is not None, (
        "Vẫn phải trả `nhan_luc` để màn hình nói được 'xếp theo lúc VTOS ghi'.")


def test_lead_khong_co_dau_nao_thi_rong_chu_khong_phai_khoi_toan_chuoi_rong(db):
    l = _lead(db)
    k = DQC.dau_dau_cuoi(db, [l.id])[l.id]
    assert k == {"dau_cham_dau": None, "dau_cham_cuoi": None, "so_lan_cham": 0}


def test_moi_ma_lead_duoc_hoi_deu_co_mot_o_trong_bang_tra(db):
    """Người gọi không phải phân biệt 'không hỏi' với 'hỏi rồi mà không có'."""
    a, b = _lead(db), _lead(db)
    _dau(db, a, "facebook", BAY_GIO)
    bang = DQC.dau_dau_cuoi(db, [a.id, b.id])
    assert set(bang) == {a.id, b.id}
    assert bang[b.id]["so_lan_cham"] == 0


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · MỘT CÂU HỎI CHO CẢ TRANG
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_hoi_ca_trang_chi_ton_dung_mot_cau_hoi(may, db):
    """Màn hình lead trả tới 2000 dòng. Hỏi từng dòng là 2000 câu cho một lần mở màn hình —
    kiểu chậm chỉ lộ ra khi bảng đã to, tức là lúc không ai còn nhớ dòng nào sinh ra nó."""
    ds = [_lead(db) for _ in range(30)]
    for l in ds[:20]:
        _dau(db, l, "facebook", BAY_GIO - timedelta(days=3))
    db.flush()

    dem = []

    @sa.event.listens_for(may, "before_cursor_execute")
    def _ghi(conn, cur, cau, tham_so, ngu_canh, nhieu):  # noqa: ANN001
        if "dau_quang_cao" in cau:
            dem.append(cau)

    try:
        bang = DQC.dau_dau_cuoi(db, [l.id for l in ds])
    finally:
        sa.event.remove(may, "before_cursor_execute", _ghi)

    assert len(bang) == 30
    assert len(dem) == 1, (
        f"Hỏi bảng dấu {len(dem)} lần cho 30 lead. Phải đúng MỘT câu hỏi cho cả trang — "
        "`dau_dau_cuoi()` nhận cả danh sách mã lead chính là để tránh chỗ này.")


def test_cua_danh_sach_lead_dung_ban_gom_san(db):
    """Hàng rào canh N+1 quay lại: `GET /leads` phải gom một lần rồi truyền vào `lead_out`."""
    than = (GOC / "app" / "api" / "v1" / "crm.py").read_text(encoding="utf-8")
    i = than.index("def list_leads(")
    j = than.index("def create_lead(", i)
    doan = than[i:j]
    assert "dau_dau_cuoi(" in doan, (
        "Cửa GET /leads không gọi `dau_dau_cuoi()`. Gọi `dau_cua_lead()` trong vòng lặp là một "
        "câu hỏi cho mỗi dòng.")
    assert "dau_cua_lead(" not in doan, (
        "Cửa GET /leads đang gọi bản MỘT LEAD trong vòng lặp — đó đúng là chỗ N+1 phải tránh.")
    assert re.search(r"lead_out\(\s*l\s*,\s*db\s*,", doan), (
        "`lead_out` trong vòng lặp phải nhận khối dấu đã gom sẵn làm tham số thứ ba; để trống thì "
        "nó tự đi hỏi lại từng dòng.")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 4 · MỘT DÒNG LEAD TRẢ RA CÓ ĐỦ KHỐI DẤU NGUỒN
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_lead_out_mang_du_ba_khoa_dau_nguon(db):
    l = _lead(db)
    _dau(db, l, "tiktok", BAY_GIO - timedelta(days=4), ten="Reels tháng 10")
    d = L.lead_out(l, db)
    for k in ("dau_cham_dau", "dau_cham_cuoi", "so_lan_cham"):
        assert k in d, f"`lead_out` thiếu khoá {k!r} — màn hình lead không có gì để hiện."
    assert d["dau_cham_dau"]["nen_tang"] == "tiktok"
    for o in ("nen_tang", "loai_ma", "ma_chien_dich", "ten_chien_dich",
              "cham_luc", "nhan_luc", "nguon_ghi", "trang_dich"):
        assert o in d["dau_cham_dau"], f"Khối một lần chạm thiếu ô {o!r}."


def test_lead_out_khong_kem_db_thi_khong_doan_bua(db):
    """Gọi không kèm `db` thì không có đường nào biết dấu — trả rỗng, không trả số 0 giả."""
    l = _lead(db)
    d = L.lead_out(l)
    assert d["dau_cham_dau"] is None and d["so_lan_cham"] == 0


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 5 · MÀN HÌNH
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def _bang_lead() -> str:
    than = WEB.read_text(encoding="utf-8")
    i = than.index("<table><thead><tr><th>SĐT</th>")
    return than[i:than.index("</table>", i)]


def test_man_hinh_lead_co_du_hai_cot_cham_dau_va_cham_cuoi():
    bang = _bang_lead()
    assert "<th>Chạm đầu</th>" in bang and "<th>Chạm cuối</th>" in bang, (
        "Chủ tịch chốt 08/10/2026 hiện CẢ HAI lần chạm, hai cột riêng. Chỉ hiện một cột là giấu "
        "đi nửa câu chuyện đúng lúc phòng Marketing đang chia ngân sách.")
    assert "l.dau_cham_dau" in bang and "l.dau_cham_cuoi" in bang, (
        "Có tiêu đề cột mà không đọc dữ liệu thì cột ấy rỗng — tệ hơn là không có cột.")


def test_so_o_trong_mot_dong_khop_so_tieu_de_va_khop_colspan():
    """Thêm cột mà quên sửa `colSpan` thì dòng 'chưa có lead' lệch khỏi bảng."""
    bang = _bang_lead()
    dau = bang[:bang.index("</thead>")]
    so_th = dau.count("<th>")
    m = re.search(r"colSpan=\{(\d+)\}", bang)
    assert m, "Không tìm thấy colSpan của dòng rỗng trong bảng lead."
    assert int(m.group(1)) == so_th, (
        f"Bảng lead có {so_th} tiêu đề cột nhưng dòng rỗng khai colSpan={m.group(1)}.")


def test_quyen_sua_tren_man_hinh_khop_edit_roles_cua_may_chu():
    """Hẹp hơn máy chủ thì người có quyền không thấy nút; rộng hơn thì bấm vào ăn 403."""
    than_web = WEB.read_text(encoding="utf-8")
    m = re.search(r"const canEdit = \[(.*?)\]\.includes\(role\)", than_web, re.S)
    assert m, "Không tìm thấy `canEdit` trong màn hình lead."
    man_hinh = set(re.findall(r'"([a-z_]+)"', m.group(1)))

    than_api = (GOC / "app" / "api" / "v1" / "crm.py").read_text(encoding="utf-8")
    m2 = re.search(r"^EDIT_ROLES = \((.*?)\)$", than_api, re.M)
    assert m2, "Không tìm thấy `EDIT_ROLES` trong crm.py."
    may_chu = set(re.findall(r'"([a-z_]+)"', m2.group(1)))

    assert man_hinh == may_chu, (
        f"Màn hình cho sửa {sorted(man_hinh)}, máy chủ cho sửa {sorted(may_chu)}. "
        f"Thiếu trên màn hình: {sorted(may_chu - man_hinh)}; thừa: {sorted(man_hinh - may_chu)}.")
