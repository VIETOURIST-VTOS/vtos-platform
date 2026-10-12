"""BD-1 · BÀN LÀM VIỆC CỦA PHÒNG ĐIỀU HÀNH — bộ kiểm.

Bộ này canh bốn nhóm, và nhóm thứ hai là nhóm không phép thử thông thường nào bắt được:

  B1 CẮT ĐÚNG NGƯỜI   – bàn đi qua đúng hàng rào phạm vi của bảng chỉ tiêu, không nới một ai
  B2 SỐ 0 KHÔNG LẪN LỖI – ô đọc hỏng phải để trống, KHÔNG được hiện 0; tổng thiếu phải là None
  B3 CHỈ ĐỌC          – bàn không có cửa ghi nào, mọi ô chỉ dẫn sang màn hình nguồn
  B4 KHÔNG BỊA DÒNG   – ô quyết toán chỉ mang những trạng thái tour CÓ THẬT trong TOUR_STATUS

Vì sao B2 đáng một nhóm riêng: một ô đọc hỏng mà in "0 việc" vẫn hiện ra bình thường, không lỗi,
không đỏ — nó chỉ nói với trưởng phòng rằng hôm nay không có gì phải làm. Đó là lời nói dối tệ
nhất mà một bàn làm việc có thể nói, và nó im lặng.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_bd1.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
import inspect
import re
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.services import ban_lam_viec as BLV

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str) -> dict:
    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()  # noqa: E712
        if u is None: pytest.skip(f"dữ liệu mẫu không có vai trò {vai}")
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ban(db=None):
    from app.db.session import SessionLocal
    if db is not None: return BLV.ban(db, "dieu_hanh")
    with SessionLocal() as s:
        return BLV.ban(s, "dieu_hanh")


# ══════════════════════════ B1 – CẮT ĐÚNG NGƯỜI ══════════════════════════
def test_bd1_truong_phong_dieu_hanh_mo_duoc_ban_cua_phong_minh():
    r = client.get("/api/v1/bao-cao/ban-lam-viec?phong=dieu_hanh", headers=login("tp_dh"))
    assert r.status_code == 200, r.text
    assert r.json()["co_ban"] is True


def test_bd1_nguoi_ngoai_pham_vi_bi_chan_bang_dung_hang_rao_cua_bang_chi_tieu():
    """KHÔNG dựng hàng rào mới cho cửa này.

    Ai xem được bảng chỉ tiêu của phòng nào là câu trả lời của `bao_cao_phong.pham_vi_cho_nguoi`.
    Cửa bàn làm việc hỏi đúng hàm ấy, nên mở thêm một cửa KHÔNG nới một quyền nào, và ngày nào
    bảng vai trò siết lại thì cả hai cửa siết theo trong cùng một nhịp. Phép thử canh đúng điều
    đó: vai nào không có `dieu_hanh` trong phạm vi thì phải nhận 403.
    """
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.services import bao_cao_phong as BP
    with SessionLocal() as s:
        vais = sorted({u.role for u in s.execute(select(User).where(User.active == True)).scalars()})  # noqa: E712
        ngoai = [v for v in vais if "dieu_hanh" not in BP.pham_vi_duoc_xem(v)]
    if not ngoai: pytest.skip("dữ liệu mẫu không có vai trò nào nằm ngoài phạm vi Điều hành")
    for v in ngoai[:4]:
        r = client.get("/api/v1/bao-cao/ban-lam-viec?phong=dieu_hanh", headers=login(v))
        assert r.status_code == 403, f"vai {v} mở được bàn của Điều hành (mã {r.status_code})"


def test_bd1_phong_chua_khai_ban_thi_noi_thang_la_chua_co():
    """Phòng chưa khai KHÔNG được trả về một cái bàn rỗng: bàn rỗng trông y hệt 'hôm nay không có
    việc gì', mà sự thật là chưa ai dựng hàng đợi cho phòng ấy."""
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        d = BLV.ban(s, "marketing")
    assert d["co_ban"] is False
    assert d["o"] == []
    assert d["tong_dang_cho"] is None
    assert d["vi_sao"]


# ══════════════════════════ B2 – SỐ 0 KHÔNG LẪN LỖI ══════════════════════════
def test_bd1_moi_o_deu_khai_du_nguon_dich_den_va_trang_thai():
    """Một ô thiếu `nguon` vẫn hiện bình thường trên màn hình. Nó chỉ hỏng ở chỗ người dùng không
    dò ngược được con số, và một con số không dò được thì không ai dùng."""
    d = _ban()
    assert len(d["o"]) == 5, f"bàn Điều hành phải có đúng 5 ô, đang có {len(d['o'])}"
    for o in d["o"]:
        assert o["khoa"] and o["ten"], o
        assert o["trang_thai"] in (BLV.SAN_SANG, BLV.THIEU_NGUON, BLV.LOI), o["trang_thai"]
        if o["trang_thai"] == BLV.SAN_SANG:
            assert o["nguon"], f"ô {o['khoa']} không khai nguồn dữ liệu"
            assert o["den"], f"ô {o['khoa']} không có đường sang màn hình nguồn"
            assert isinstance(o["so_luong"], int) and o["so_luong"] >= 0, o
            assert o["nhan_muc"], f"ô {o['khoa']} có màu mà không có chữ đi kèm"
        else:
            assert o["so_luong"] is None, f"ô {o['khoa']} đọc không được mà vẫn hiện một con số"
            assert o["ly_do"], f"ô {o['khoa']} hỏng mà không nói vì sao"


def test_bd1_mot_o_hong_khong_keo_sap_ca_ban_va_lam_tong_thanh_None(monkeypatch):
    """Phép thử canh chính bản vá. Không có nó thì một bản sửa chẳng làm gì cả cũng xanh."""
    def _no(*a, **k): raise RuntimeError("nguồn giả vờ hỏng")
    monkeypatch.setattr(BLV, "_su_co_qua_han", _no)
    d = _ban()
    assert len(d["o"]) == 5, "một ô hỏng đã kéo mất các ô khác"
    hong = [o for o in d["o"] if o["trang_thai"] == BLV.LOI]
    assert len(hong) == 1 and hong[0]["so_luong"] is None
    assert d["tong_dang_cho"] is None, "thiếu một ô mà vẫn in ra một con số tổng"


def test_bd1_tong_bang_dung_tong_cac_o_khi_ca_nam_o_san_sang():
    d = _ban()
    if any(o["trang_thai"] != BLV.SAN_SANG for o in d["o"]):
        pytest.skip("dữ liệu mẫu đang có ô chưa đọc được")
    assert d["tong_dang_cho"] == sum(o["so_luong"] for o in d["o"])


def test_bd1_so_dong_mau_dung_ba_va_khong_o_nao_vuot():
    """Chủ tịch chốt BA dòng ngày 12/10/2026 sau khi xem bản dựng thử: cả năm ô nằm gọn một màn
    hình, không phải cuộn. Bốn dòng là đổi quyết định ấy, nên phải có người ký."""
    assert BLV.SO_DONG_MAU == 3
    for o in _ban()["o"]:
        assert len(o["dong"]) <= BLV.SO_DONG_MAU, f"ô {o['khoa']} bày {len(o['dong'])} dòng"


def test_bd1_ban_khong_cong_chi_tieu_bao_cao_vao_hang_doi():
    """Hai nguồn riêng, hai câu hỏi khác nhau. Chỉ tiêu đếm theo KỲ, hàng đợi đếm hồ sơ ĐANG chờ
    tại thời điểm này — cộng vào nhau là ra một con số không trả lời câu nào."""
    from app.db.session import SessionLocal
    from app.services import bao_cao_phong as BP
    with SessionLocal() as s:
        bc = BP.bao_cao(s, "ngay", "dieu_hanh")
        d = BLV.ban(s, "dieu_hanh")
    if d["tong_dang_cho"] is None: pytest.skip("có ô chưa đọc được")
    ma_bc = {x["ma"] for x in bc["chi_tieu"]}
    ma_o = {o["khoa"] for o in d["o"]}
    assert not (ma_bc & ma_o), f"hai bảng dùng chung mã: {ma_bc & ma_o} — sẽ bị cộng nhầm"


# ══════════════════════════ B3 – CHỈ ĐỌC ══════════════════════════
def test_bd1_khong_co_cua_ghi_nao_mang_ten_ban_lam_viec():
    """Bàn tổng hợp mà duyệt được là chỗ một cú bấm nhầm đi xa nhất. Quyền duyệt nằm ở màn hình
    nguồn, và nó phải ở lại đó."""
    duong = [(r.path, m) for r in app.routes for m in getattr(r, "methods", set())
             if "ban-lam-viec" in getattr(r, "path", "")]
    assert duong, "không tìm thấy cửa bàn làm việc"
    for p, m in duong:
        assert m in ("GET", "HEAD"), f"cửa {p} nhận {m} — bàn làm việc phải là cửa chỉ đọc"


def test_bd1_dich_den_cua_moi_o_la_man_hinh_co_that():
    """Một ô trỏ vào màn hình không tồn tại thì người dùng bấm vào và rơi ra trang trắng — tệ hơn
    là không có nút nào."""
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[2] / "web" / "app"
    if not goc.is_dir(): pytest.skip("không có cây web trong lần chạy này")
    for o in _ban()["o"]:
        if o["trang_thai"] != BLV.SAN_SANG: continue
        trang = o["den"].split("?")[0].strip("/")
        assert (goc / trang / "page.tsx").is_file(), f"ô {o['khoa']} trỏ vào /{trang} không có trang"


def test_bd1_tep_dich_vu_khong_ghi_mot_dong_nao_vao_co_so_du_lieu():
    """Quét mã nguồn, không quét hành vi: một lệnh ghi nằm trong nhánh hiếm có thể không chạy
    trong lần kiểm này mà vẫn chạy trên bàn thật."""
    ma = inspect.getsource(BLV)
    for cam in ("db.add(", "db.commit(", "db.delete(", "db.flush(", "update(", "db.merge("):
        assert cam not in ma, f"dịch vụ bàn làm việc có lệnh ghi `{cam}`"


# ══════════════════════════ B4 – KHÔNG BỊA DÒNG ══════════════════════════
def test_bd1_o_quyet_toan_chi_dung_trang_thai_tour_co_that():
    """Bản dựng thử ngày 12/10 có dòng 'Kế toán trả lại, cần sửa'. VTOS KHÔNG có trạng thái ấy —
    `TOUR_STATUS` đi một chiều, không có đường lùi nào mang tên 'trả lại'. Vẽ dòng ấy ra là dựng
    một hàng đợi không có hồ sơ nào chảy vào, và nó sẽ mãi mãi bằng 0 mà không ai biết vì sao.

    Phép thử này đỏ vào đúng ngày ai đó thêm trạng thái trả lại thật — lúc ấy mở lại dòng ấy là
    đúng, và dòng chú thích trong `_quyet_toan_cho` phải sửa theo.
    """
    from app.models.core import TOUR_STATUS
    assert "ket_thuc" in TOUR_STATUS and "da_dong_so" in TOUR_STATUS
    assert not [k for k in TOUR_STATUS if "tra_lai" in k], \
        "đã có trạng thái trả lại quyết toán — mở lại dòng thứ ba của ô quyết toán"
    # SOI DÒNG THẬT, KHÔNG SOI MÃ NGUỒN. Bản đầu của phép thử này quét `inspect.getsource` tìm
    # chữ "Kế toán trả lại" và tự đỏ ngay lần chạy đầu — vì chính đoạn chú thích GIẢI THÍCH vì sao
    # không có dòng ấy cũng chứa chữ ấy. Một phép thử bắt được lời giải thích thay vì bắt được
    # hành vi thì nó dạy người ta xoá lời giải thích. Nay soi đúng thứ hiện lên màn hình.
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        o = [x for x in BLV.ban(s, "dieu_hanh")["o"] if x["khoa"] == "quyet_toan"][0]
    if o["trang_thai"] != BLV.SAN_SANG: pytest.skip("ô quyết toán chưa đọc được")
    bia = [d for d in o["dong"] if "trả lại" in d["chinh"].lower()]
    assert not bia, f"ô quyết toán bày dòng {bia} trong khi VTOS không có trạng thái trả lại"


def test_bd1_hang_doi_bao_cao_ngay_cat_theo_phong_chu_khong_dem_ca_cong_ty():
    """Ô 'báo cáo ngày chưa chấm' trên bảng điều hành `/` đếm báo cáo của MỌI phòng rồi hiện cho
    bảy vai. Ở bàn của một phòng thì con số ấy phải là của phòng ấy, nếu không bấm vào sẽ ra một
    danh sách không phải việc của mình."""
    from app.db.session import SessionLocal
    from app.models.ops import DailyReport
    with SessionLocal() as s:
        ca_cong_ty = len(list(s.execute(select(DailyReport)
                                        .where(DailyReport.reviewed_by == "")).scalars()))
        o = [x for x in BLV.ban(s, "dieu_hanh")["o"] if x["khoa"] == "bao_cao_ngay"][0]
    if o["trang_thai"] != BLV.SAN_SANG: pytest.skip("ô này chưa đọc được")
    assert o["so_luong"] <= ca_cong_ty
    assert "PHONG_CUA_VAI_TRO" in o["nguon"] or "phòng này" in o["nguon"]


def test_bd1_so_yeu_cau_cho_booking_khop_dung_phep_loc_cua_chi_tieu():
    """Hai chỗ cùng đếm 'yêu cầu chưa tạo booking' — bảng chỉ tiêu và bàn làm việc. Lệch nhau một
    hồ sơ là người dùng mất lòng tin vào cả hai, nên phép thử ghim chúng vào nhau."""
    from app.db.session import SessionLocal
    from app.models.core import ServiceRequest
    with SessionLocal() as s:
        that = s.execute(select(ServiceRequest).where(ServiceRequest.booking_id == None)).scalars().all()  # noqa: E711
        o = [x for x in BLV.ban(s, "dieu_hanh")["o"] if x["khoa"] == "yeu_cau_booking"][0]
    if o["trang_thai"] != BLV.SAN_SANG: pytest.skip("ô này chưa đọc được")
    assert o["so_luong"] == len(that)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# BÀN HỎNG PHẢI NÓI RA ĐƯỢC — thêm 12/10/2026, và nó là ĐIỀU 1 của chính tệp này ở cấp độ CẢ BÀN
# ═════════════════════════════════════════════════════════════════════════════════════════════
#
# Điều 1 của vòng BD-1 viết cho MỘT Ô: số 0 không được lẫn với lỗi, ô đọc hỏng để trống chứ không
# in 0, vì "0 việc" là nói với trưởng phòng rằng hôm nay không có gì phải làm. Luật ấy được canh
# cẩn thận ở phía máy chủ và ở từng ô của màn hình.
#
# Ở cấp độ CẢ BÀN thì nó bị quên. Màn hình trả `null` cho hai trường hợp khác hẳn nhau: (a) đọc
# cửa hỏng, (b) phòng chưa ai dựng hàng đợi. Trường hợp (b) trả `null` là đúng. Trường hợp (a)
# trả `null` là đúng cái điều 1 cấm, chỉ to hơn: cả khối biến mất, trưởng phòng mở trang thấy
# thẳng bảng chỉ tiêu và không có cách nào biết hệ thống hôm nay không đọc được việc của mình.
#
# Lời nhắc (toast) KHÔNG đủ và đó là lý do bộ kiểm này tồn tại: nó tắt sau vài giây, nó không bắn
# lại cho người mở trang muộn hơn, và trên điện thoại thì thường chẳng ai kịp đọc.
_TSX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "web", "components", "BanLamViecPhong.tsx")


def _man_hinh() -> str:
    with open(_TSX, encoding="utf-8") as f:
        return f.read()


def _man_hinh_lenh() -> str:
    """Màn hình, BỎ HẾT CHÚ THÍCH — và cái hàm này sinh ra từ một lần tự ngã.

    Bản đầu của `test_bd1_ban_hong_phai_noi_ra_chu_khong_bien_mat` dò `s.find(...)` trên cả tệp
    và ĐỎ NGAY LẦN CHẠY ĐẦU, trong khi mã hoàn toàn đúng: đoạn chú thích GIẢI THÍCH vì sao nhánh
    báo lỗi phải đứng trước có nhắc nguyên văn câu lệnh `if (!d || !d.co_ban) return null`, nên
    `find` vớ phải lời giải thích ở trên trước khi tới câu lệnh thật ở dưới — và kết luận ngược
    hẳn sự thật.

    Đây là lần thứ SÁU trong hai ngày một hàng rào quét chuỗi trả lời nhầm câu hỏi, và là lần thứ
    ba nó bắt đúng vào lời giải thích. Một phép thử bắt được chú thích thay vì bắt được hành vi
    thì nó dạy người ta XOÁ CHÚ THÍCH — thứ đắt nhất trong tệp. `test_ci_hang_rao_main._dong_lenh`
    đã dựng đúng hàm này cho `ci.yml` từ 19/9/2026 vì cùng một lý do; đây là bản cho tệp .tsx.
    """
    ra = []
    for d in _man_hinh().splitlines():
        t = d.strip()
        if t.startswith("//") or t.startswith("/*") or t.startswith("*"):
            continue
        ra.append(d.split("//")[0] if "//" in d else d)
    return "\n".join(ra)


def test_bd1_doc_hong_thi_ghi_lai_ly_do_chu_khong_chi_ban_mot_loi_nhac():
    """Nhánh `catch` phải GIỮ lý do lại, không chỉ bắn một lời nhắc rồi quên."""
    s = _man_hinh_lenh()
    m = re.search(r"\.catch\(\(e\)\s*=>\s*\{([^}]*)\}", s)
    assert m, "không tìm thấy nhánh `.catch` của lời gọi cửa bàn làm việc"
    than = m.group(1)
    assert "setLoi(" in than, (
        "nhánh `catch` không ghi lý do vào một ô nhớ — nó chỉ bắn lời nhắc rồi quên. Lời nhắc tắt "
        "sau vài giây và không bắn lại cho người mở trang muộn hơn, nên cái hỏng trở lại vô hình.")


def test_bd1_ban_hong_phai_noi_ra_chu_khong_bien_mat():
    """LUẬT CHÍNH, và THỨ TỰ hai nhánh là nửa quan trọng nhất của nó.

    Lúc đọc hỏng thì `d` là null. Nên nếu `if (!d || !d.co_ban) return null` chạy TRƯỚC, nó nuốt
    luôn trường hợp hỏng và khối báo lỗi không bao giờ hiện — mã trông như đã sửa, màn hình thì y
    như cũ. Một phép thử chỉ hỏi "có khối báo lỗi không" sẽ xanh trong khi người dùng vẫn thấy
    trang trống; nên phép thử này hỏi cả VỊ TRÍ, và hỏi trên bản ĐÃ BỎ CHÚ THÍCH (xem `_man_hinh_lenh`).
    """
    s = _man_hinh_lenh()
    i_loi = s.find("if (loi)")
    assert i_loi > 0, (
        "màn hình không có nhánh nào dựng hình khi đọc cửa hỏng — đọc hỏng và `phòng chưa khai "
        "bàn` lại trông y hệt nhau, cả hai là một khoảng trống.")
    i_co_ban = s.find("if (!d || !d.co_ban) return null")
    assert i_co_ban > 0, (
        "mất nhánh `co_ban` — phòng chưa khai hàng đợi sẽ bị vẽ ra một cái bàn trống, mà bàn trống "
        "trông y hệt `hôm nay không có việc gì`.")
    assert i_loi < i_co_ban, (
        "nhánh báo lỗi đứng SAU nhánh `co_ban`. Lúc đọc hỏng thì `d` là null nên nhánh `co_ban` "
        "trả null trước, và khối báo lỗi không bao giờ chạy — sửa mà như không sửa.")


def test_bd1_khoi_bao_hong_phai_cho_thu_lai():
    """Một cái hỏng nói ra mà không cho làm gì thì mới đi được nửa đường.

    Phần lớn lần hỏng ở đây là một nhịp mạng hoặc một lần máy chủ bận. Bắt người dùng tải lại cả
    trang để thử lại là bắt họ trả giá cho một việc máy làm được trong một giây.
    """
    s = _man_hinh_lenh()
    i = s.find("if (loi)")
    khoi = s[i:i + 1600]
    assert "setLan(" in khoi, "khối báo hỏng không có nút thử lại"
    assert re.search(r"\}, \[phong, toast, lan\]\)", s), (
        "nút thử lại có mà `useEffect` không nghe `lan` — bấm vào không gọi lại cửa, nút chết.")
