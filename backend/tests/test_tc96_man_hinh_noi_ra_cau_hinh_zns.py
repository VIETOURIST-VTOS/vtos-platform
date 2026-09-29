"""TC-96 · MÀN HÌNH PHẢI NÓI RA TRẠNG THÁI CẤU HÌNH ZNS — 29/9/2026.

Anh Tuấn hỏi ngày 29/9: "Zalo duyệt xong sẽ báo về đâu?" Câu trả lời đúng, và khó chịu, là: báo về
trang ZNS của Zalo — còn VTOS thì KHÔNG BAO GIỜ TỰ BIẾT. Hệ thống chỉ đọc hai mã mẫu từ biến môi
trường `ZALO_ZNS_TEMPLATES`; duyệt xong mà chưa ai dán mã vào đó thì với VTOS không có gì đổi.

Trước vòng này trạng thái ấy KHÔNG hiện ở đâu cả. Bảng chỉ tiêu có dòng "Tin Zalo đang kẹt chờ cấu
hình" — nó nói CÓ chuyện, nhưng không nói cấu hình nào, nên:

  · người đọc bảng không biết phải làm gì;
  · người vừa dán mã xong không có chỗ nào xác nhận là đã xong;
  · và nếu mai kia ai đó lỡ xoá biến ấy, bảng sẽ im lặng cho tới khi hàng đợi lại dài ra.

Một mắt xích đi qua tay người thì phải có một ô trên màn hình nói nó đang ở đâu. Đó là cả nội dung
của vòng này.

HAI CHỖ DỄ HỎNG:
 1. ĐỌC LẤY BIẾN MÔI TRƯỜNG Ở CHỖ THỨ HAI. Bảng phải hỏi đúng `zalo.configured` — cùng hàm mà đường
    gửi thật dùng. Hai chỗ cùng trả lời một câu là hai chỗ có thể lệch, và lúc lệch thì màn hình
    báo "đã khai đủ" trong khi robot vẫn không gửi được tin nào.
 2. ĐẾM SỐ MẪU THAY VÌ SỐ MỤC ĐÍCH. Hệ thống cần đúng hai mẫu, mỗi mẫu một mục đích. Khai mười mẫu
    cho cùng một mục đích vẫn là thiếu.
"""
import ast
import inspect
import os
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_tc96.db")
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

from app.db.session import Base, SessionLocal, engine      # noqa: E402
from app.services import bao_cao_phong as BP               # noqa: E402
from app.services import rules as R                        # noqa: E402
from app.services import zalo as Z                         # noqa: E402

MA_DONG = "cs_zalo_cau_hinh"


def _dung_bang():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    R.seed_params(db)
    return db


def _dong(db):
    b = BP.bao_cao(db, "thang", "toan_cty")
    return next((x for x in b["chi_tieu"] if x["ma"] == MA_DONG), None)


def _gia_cau_hinh(monkeypatch, oa: bool, mau: dict):
    monkeypatch.setattr(Z, "configured", lambda db=None: {
        "oa": oa, "zns_templates": dict(mau), "webhook": True, "refresh": True})


# ═════════════ DÒNG PHẢI CÓ MẶT, VÀ NÓI ĐỦ ═════════════
def test_bang_co_dong_noi_ra_trang_thai_mau_ZNS():
    db = _dung_bang()
    x = _dong(db)
    assert x is not None, "bảng không có dòng nào nói về cấu hình ZNS — người dán mã xong " \
                          "không có chỗ nào xác nhận"
    assert x["cong_thuc"] and x["nguon"], "dòng thiếu cách tính hoặc nguồn"
    assert "ZALO_ZNS_TEMPLATES" in x["nguon"], "nguồn phải chỉ đúng chỗ người ta cần sửa"


def test_chua_khai_mau_nao_thi_DO_va_noi_phai_lam_gi(monkeypatch):
    db = _dung_bang()
    _gia_cau_hinh(monkeypatch, oa=True, mau={})
    x = _dong(db)
    assert x["gia_tri"] == 0
    assert x["muc"] == "do", "thiếu mẫu là chuyện phải xử lý, không phải chuyện để rà"
    assert x["viec"], "một con số đỏ mà không nói làm gì thì chỉ tạo lo lắng"
    assert "zalo.cloud" in x["viec"] and "ZALO_ZNS_TEMPLATES" in x["viec"]


def test_khai_du_hai_muc_dich_thi_HET_do(monkeypatch):
    db = _dung_bang()
    _gia_cau_hinh(monkeypatch, oa=True,
                  mau={"cham_soc": "T1", "cham_soc_nhac": "T2"})
    x = _dong(db)
    assert x["gia_tri"] == 2
    assert x["muc"] == "", "khai đủ rồi mà vẫn đỏ thì lần sau không ai tin màu của bảng"
    assert x["viec"] == ""


def test_khai_MOT_muc_dich_van_con_do_va_chi_dich_danh_cai_thieu(monkeypatch):
    db = _dung_bang()
    _gia_cau_hinh(monkeypatch, oa=True, mau={"cham_soc": "T1"})
    x = _dong(db)
    assert x["gia_tri"] == 1 and x["muc"] == "do"
    assert any("cham_soc_nhac" in c and "CHƯA" in c for c in x["chi_tiet"]), \
        "nói thiếu mà không nói thiếu CÁI NÀO thì người sửa phải đi đoán"


def test_dem_MUC_DICH_chu_khong_dem_so_mau(monkeypatch):
    """Khai mười mã cho cùng một mục đích vẫn là thiếu."""
    db = _dung_bang()
    _gia_cau_hinh(monkeypatch, oa=True, mau={"cham_soc": "T1,T2,T3"})
    x = _dong(db)
    assert x["gia_tri"] == 1, "đang đếm mã thay vì đếm mục đích"


def test_noi_ro_ca_tinh_trang_tai_khoan_OA(monkeypatch):
    """Có đủ mẫu ZNS mà chưa nối OA thì vẫn không gửi được gì — phải thấy điều đó trên bảng."""
    db = _dung_bang()
    _gia_cau_hinh(monkeypatch, oa=False,
                  mau={"cham_soc": "T1", "cham_soc_nhac": "T2"})
    x = _dong(db)
    assert any("CHƯA nối" in c for c in x["chi_tiet"])


# ═════════════ MỘT CHỖ TRẢ LỜI, KHÔNG PHẢI HAI ═════════════
def test_bang_HOI_zalo_configured_chu_khong_tu_doc_bien_moi_truong():
    """Hai chỗ cùng trả lời một câu là hai chỗ có thể lệch, và lúc lệch thì màn hình báo 'đã khai
    đủ' trong khi robot vẫn không gửi được tin nào. Canh bằng cây cú pháp, vì một bản tự đọc lấy
    biến môi trường hôm nay cho KẾT QUẢ GIỐNG HỆT — nó chỉ sai vào ngày luật đọc cấu hình đổi."""
    cay = ast.parse(inspect.getsource(BP))
    ten_goi = {n.func.attr for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "configured" in ten_goi, "bảng không còn hỏi services.zalo.configured"
    hang_so = {n.value for n in ast.walk(cay)
               if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "ZALO_ZNS_TEMPLATES" not in hang_so or True   # tên biến ĐƯỢC phép xuất hiện trong lời khai
    thuoc_tinh = {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    assert "ZALO_ZNS_TEMPLATES" not in thuoc_tinh, \
        "bao_cao_phong đang đọc thẳng settings.ZALO_ZNS_TEMPLATES — đó là chỗ trả lời thứ hai"


# ═════════════ HỎNG CHỖ ĐỌC CẤU HÌNH KHÔNG ĐƯỢC LÀM CHẾT CẢ BẢNG ═════════════
def test_doc_cau_hinh_hong_thi_bang_van_hien_va_NOI_RA_la_hong(monkeypatch):
    def no(db=None):
        raise RuntimeError("mat ket noi")
    monkeypatch.setattr(Z, "configured", no)
    db = _dung_bang()
    b = BP.bao_cao(db, "thang", "toan_cty")
    assert b["chi_tieu"], "một chỗ đọc cấu hình hỏng đã làm chết cả bảng chỉ tiêu"
    x = next(x for x in b["chi_tieu"] if x["ma"] == MA_DONG)
    assert any("Không đọc được cấu hình" in c for c in x["chi_tiet"])


# ═════════════ HÀNG RÀO TỰ KIỂM ═════════════
def test_phep_thu_nay_that_su_no(monkeypatch):
    """Nếu bỏ dòng ấy đi thì bộ kiểm này PHẢI đỏ — chứ không phải xanh vì không tìm thấy gì."""
    _gia_cau_hinh(monkeypatch, oa=True, mau={"cham_soc": "T1", "cham_soc_nhac": "T2"})
    db = _dung_bang()
    assert _dong(db) is not None
    that = BP._cskh_dong
    monkeypatch.setattr(BP, "_cskh_dong", lambda db, tu, den: [
        x for x in that(db, tu, den) if x["ma"] != MA_DONG])
    assert _dong(db) is None
