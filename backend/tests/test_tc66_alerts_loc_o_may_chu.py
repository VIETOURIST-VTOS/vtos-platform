# -*- coding: utf-8 -*-
"""TC-66 · CỬA CẢNH BÁO LỌC Ở MÁY CHỦ, VÀ MÃ PHÁP NHÂN ĐI CÙNG GÓI /dashboard.

    "/alerts giờ là cửa chậm nhất còn lại (1,67 giây) … = ok"
    "/dong-tien/meta → /dong-tien/khung vẫn xếp hàng dọc … chỉ duy nhất 1 pháp nhân là VIETOURIST"
                                                                    — anh Tuấn, 18/9/2026

══════════════════════════════════════════════════════════════════════════════════════════════
SỐ ĐO THẬT TRƯỚC KHI SỬA (vtos.infinitytours.org, 18/9/2026, mỗi cửa gọi ba lần)
══════════════════════════════════════════════════════════════════════════════════════════════
    /alerts             0,87s   0,95s   1,30s     ← lần nào cũng chậm, không có lần nhanh
    /dong-tien/meta     0,85s   rồi mới gọi được /dong-tien/khung → cộng ~1,1 giây vào cuối

══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ DỄ HỎNG NGUY HIỂM NHẤT CỦA CẢ VÒNG — VÀ VÌ SAO NÓ ĐÁNG MỘT TỆP PHÉP THỬ RIÊNG
══════════════════════════════════════════════════════════════════════════════════════════════
Vòng này chuyển một phép LỌC PHÂN QUYỀN từ Python xuống câu truy vấn SQL. Luật không đổi một chữ,
nhưng chỗ thi hành thì đổi — và đó đúng là loại thay đổi làm lộ dữ liệu mà không ai thấy bằng mắt:
màn hình vẫn chạy, vẫn có dòng, chỉ là nhiều hơn hoặc ít hơn đúng vài dòng mà không ai đếm.

`to_roles` là một chuỗi ngăn bằng dấu phẩy ("chutich,ketoan"). Cách sai kinh điển là
`LIKE '%vai%'`: vai "kt" lúc ấy trúng mọi dòng gửi cho "ketoan", tức NỚI QUYỀN. Cách đúng phải
so khớp CẢ MẨU, và phải phủ đủ bốn vị trí một mẩu có thể đứng: một mình · đầu · cuối · giữa.

Nên phép thử ở đây KHÔNG canh "câu SQL trông thế nào". Nó dựng sổ thật trong SQLite, chạy CẢ HAI
luật — luật Python cũ và luật SQL mới — trên cùng một tập dữ liệu, rồi đòi hai bên ra ĐÚNG cùng
một tập. Đó là cách duy nhất chứng minh được "luật không đổi một chữ".
"""
import re
import pytest
from pathlib import Path
from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Alert

GOC = Path(__file__).resolve().parents[2]
ROUTES = GOC / "backend" / "app" / "api" / "v1" / "routes.py"
DT = GOC / "backend" / "app" / "api" / "v1" / "dong_tien.py"
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"


def _ma_py(p: Path) -> str:
    s = p.read_text(encoding="utf-8")
    s = re.sub(r'"""(?:.|\n)*?"""', " ", s)
    return re.sub(r"^\s*#.*$", " ", s, flags=re.M)


def _ma_tsx(p: Path) -> str:
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


# ───────────────────── 1 · HAI LUẬT PHẢI RA CÙNG MỘT TẬP ─────────────────────

# Mười một chuỗi `to_roles`, cố ý chọn để bẫy đúng những cách so khớp sai. Ba vai dưới đây là
# những mẩu LỒNG NHAU thật trong hệ thống: "kt" nằm trong "ketoan", "dh" nằm trong "nv_dh" và
# "tp_dh". Một phép `LIKE '%vai%'` sẽ trượt ngay ở hàng đầu tiên.
SO_CANH_BAO = [
    "chutich",
    "ketoan",
    "kt",
    "chutich,ketoan",
    "ketoan,chutich",
    "nv_dh,tp_dh",
    "dh",
    "tp_dh,dh,ketoan",
    "ketoan,kt",
    "kt,ketoan",
    "",
]
VAI_THU = ["kt", "dh", "ketoan", "chutich", "nv_dh", "tp_dh", "khong_ai"]


@pytest.fixture()
def so():
    """Chỉ dựng ĐÚNG bảng mà phép thử này đọc, và KHÔNG đụng `Base.metadata` chung — sửa một thứ
    dùng chung giữa chừng thì phép thử hỏng sẽ hiện ra ở TỆP KHÁC (bài học TC-32)."""
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=[Alert.__table__])
    s = sessionmaker(bind=e)()
    try:
        for i, tr in enumerate(SO_CANH_BAO):
            s.add(Alert(kind="thu", level="info", message="thu", ref=f"r{i}",
                        to_roles=tr, resolved=False))
        s.commit()
        yield s
    finally:
        s.close()
        Base.metadata.drop_all(e, tables=[Alert.__table__])


def _loc_python_cu(rows, vai: str) -> set:
    """Nguyên văn luật cũ, chép lại ở đây làm BẢN ĐỐI CHỨNG.

    Chép chứ không gọi: nếu gọi hàm thật thì ngày ai đó sửa hàm thật, bản đối chứng sửa theo và
    phép thử vẫn xanh trong khi luật đã đổi. Bản đối chứng phải đứng yên.
    """
    return {a.ref for a in rows if vai in (a.to_roles or "").split(",")}


def _loc_sql_moi(s, vai: str) -> set:
    """Nguyên văn phép lọc mới trong routes.list_alerts."""
    qs = select(Alert).where(or_(Alert.to_roles == vai,
                                 Alert.to_roles.like(f"{vai},%"),
                                 Alert.to_roles.like(f"%,{vai}"),
                                 Alert.to_roles.like(f"%,{vai},%")))
    return {a.ref for a in s.execute(qs).scalars()}


def test_loc_sql_moi_ra_dung_tap_ma_luat_python_cu_ra(so):
    """Chỗ hỏng nguy hiểm nhất: chuyển phép lọc phân quyền xuống SQL mà lệch đi vài dòng."""
    tat_ca = list(so.execute(select(Alert)).scalars())
    for vai in VAI_THU:
        cu = _loc_python_cu(tat_ca, vai)
        moi = _loc_sql_moi(so, vai)
        assert moi == cu, (
            f"Vai {vai!r}: phép lọc SQL mới ra tập khác luật cũ.\n"
            f"  thừa (NỚI QUYỀN): {sorted(moi - cu)}\n"
            f"  thiếu (mất việc): {sorted(cu - moi)}"
        )


def test_mau_long_nhau_khong_lot_qua(so):
    """Vế nói thẳng của phép thử trên, để lỗi báo ra đúng nguyên nhân chứ không chỉ 'lệch tập'.

    "kt" là một mẩu nằm trong "ketoan". Một phép `LIKE '%kt%'` cho vai "kt" thấy luôn mọi cảnh báo
    gửi cho Kế toán — nới quyền, và không màn hình nào cho thấy điều đó.
    """
    assert _loc_sql_moi(so, "kt") == {"r2", "r8", "r9"}, (
        "Vai 'kt' phải thấy ĐÚNG ba dòng có mẩu 'kt' đứng riêng, không được thấy dòng của 'ketoan'."
    )
    assert _loc_sql_moi(so, "dh") == {"r6", "r7"}, (
        "Vai 'dh' không được thấy dòng gửi cho 'nv_dh' hay 'tp_dh'."
    )


# ───────────────────── 2 · KHÔNG ĐỌC CẢ BẢNG NỮA ─────────────────────

def test_cua_canh_bao_cat_trang_trong_cau_truy_van():
    """Cái làm cửa này chậm là ĐỌC CẢ BẢNG rồi mới cắt trang bằng Python (KS-5 đo 1.703 dòng).

    Trần `limit` cũ chỉ cắt phần TRẢ VỀ, không cắt phần ĐỌC LÊN. Phép thử canh rằng `offset` và
    `limit` nay nằm trong câu truy vấn, và không còn chỗ nào đọc hết rồi cắt bằng lát cắt Python.
    """
    ma = _ma_py(ROUTES)
    i = ma.index("def list_alerts")
    than = ma[i:ma.index("\n@router", i)]
    assert ".offset(offset).limit(tran)" in than, (
        "Cửa cảnh báo vẫn chưa cắt trang trong câu truy vấn."
    )
    assert "duoc[offset:offset + tran]" not in than, (
        "Vẫn còn lát cắt Python — tức vẫn đọc cả bảng lên rồi mới cắt."
    )
    assert "select(_f.count())" in than, (
        "`tong` phải đếm bằng COUNT; đọc cả bảng chỉ để đếm là quay lại đúng cái vừa bỏ."
    )


def test_khong_chua_cua_canh_bao_bang_cho_nho():
    """Ranh giới của vòng này, ghi ra để vòng sau không "tối ưu" thêm một bước sai.

    `/alerts` là cửa CẢNH BÁO. Cho nó chỗ nhớ năm phút như `/dashboard` nghĩa là giữ một cảnh báo
    cũ trên màn hình năm phút — và giữ một cảnh báo ĐÃ XỬ LÝ cũng đúng ngần ấy lâu. Cái sai của
    cửa này là đọc quá nhiều, nên phải chữa đúng chỗ ấy.
    """
    ma = _ma_py(ROUTES)
    i = ma.index("def list_alerts")
    than = ma[i:ma.index("\n@router", i)]
    assert "Kho(" not in than and "nho_tam" not in than, (
        "Cửa cảnh báo đang dùng chỗ nhớ — xem lý do ở chuỗi tài liệu của phép thử này."
    )


# ───────────────────── 3 · BỎ XẾP HÀNG DỌC, KHÔNG NỚI QUYỀN ─────────────────────

def test_danh_muc_phap_nhan_chi_dung_MOT_lan_cho_ca_hai_cua():
    """Hai bản chép của một phép lọc phạm vi thì sớm muộn lệch nhau, và ngày chúng lệch là ngày
    một vai nhìn thấy pháp nhân mà vai ấy không được thấy — kiểu sai không ai phát hiện bằng mắt.
    """
    ma = _ma_py(DT)
    assert "def danh_muc_phap_nhan" in ma, "Thiếu hàm dựng danh mục pháp nhân dùng chung."
    assert ma.count("PV.loc(select(Company)") == 1, (
        "Phép lọc phạm vi pháp nhân đang được chép ở hơn một chỗ."
    )
    meta = ma[ma.index("def meta("):]
    meta = meta[:meta.index("\n@router")] if "\n@router" in meta else meta
    assert "danh_muc_phap_nhan(db, u)" in meta, "`/dong-tien/meta` phải gọi hàm dùng chung."


def test_dashboard_chi_gui_danh_muc_cho_vai_duoc_xem_dong_tien():
    """KHÔNG NỚI QUYỀN MỘT LI — đây là điều kiện để vòng này được phép tồn tại.

    Gửi sớm hơn thì được; gửi cho thêm người thì không. Hàng rào phải đúng bằng hàng rào của
    `/dong-tien/meta`, tức chính hằng `XEM` của phân hệ dòng tiền — không chép lại danh sách vai.
    """
    ma = _ma_py(ROUTES)
    i = ma.index("def _dashboard_payload")
    than = ma[i:ma.index("\n@router", i)] if "\n@router" in ma[i:] else ma[i:]
    assert "from app.api.v1.dong_tien import XEM as DT_XEM" in than, (
        "Phải dùng CHÍNH hằng `XEM` của phân hệ dòng tiền, không chép lại danh sách vai."
    )
    assert "if u.role in DT_XEM" in than, "Thiếu hàng rào vai trò trước khi gửi danh mục."
    assert "dong_tien_phap_nhan" in than


def test_man_hinh_van_con_loi_lui_khi_may_chu_khong_gui():
    """Lối lui không thừa: máy chủ bản cũ chưa có trường này, và vai ngoài `XEM` thì máy chủ cố ý
    KHÔNG gửi. Bỏ lối lui đi là một ngày nào đó khối dòng tiền im lặng biến mất khỏi màn hình mà
    không lỗi nào báo."""
    ma = _ma_tsx(KHOI)
    assert "if (phap_nhan)" in ma, "Thiếu nhánh dùng danh mục do /dashboard gửi kèm."
    assert 'api("/dong-tien/meta")' in ma, "Mất lối lui tự gọi `/dong-tien/meta`."
    assert "phap_nhan={d.dong_tien_phap_nhan}" in _ma_tsx(TRANG), (
        "Trang không truyền danh mục xuống khối dòng tiền — lượt gọi thừa vẫn còn."
    )
