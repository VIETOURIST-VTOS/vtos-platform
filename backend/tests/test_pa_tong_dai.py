"""Bộ đọc lịch sử cuộc gọi P.A Việt Nam – bước ĐO trước khi đề xuất chuyển giọng nói thành văn bản.

Đặc tả lấy từ trang quản trị của P.A (Người phát triển → Kiểm thử API), không đoán. Những phép thử
dưới đây gác đúng những chỗ dễ hỏng lặng lẽ ở một bộ nối bên ngoài:

  PA1  chưa khai khoá thì nói rõ chưa khai, không gọi ra ngoài rồi báo lỗi khó hiểu
  PA2  khoá KHÔNG bao giờ lọt vào thông báo lỗi
  PA3  mã lỗi của P.A dịch ra tiếng Việt cho người vận hành, không trả mã thô
  PA4  phép đo cộng đúng số cuộc / số phút / số cuộc có ghi âm
  PA5  phép đo KHÔNG trả về số điện thoại nào
  PA6  chạm trần số trang thì phải NÓI RA, vì con số khi đó là sàn chứ không phải tổng
  PA7  ước chi phí tính theo số phút đo được, và ghi rõ bảng giá ngày nào
"""
import os, sys, json
os.environ["DATABASE_URL"] = "sqlite:///./test_patd.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_patd.db", "test_patd.db-journal"):
    if os.path.exists(f): os.remove(f)
import pytest

KHOA_THU = "khoa-bi-mat-khong-duoc-lo-123456"


@pytest.fixture(autouse=True)
def _khoa():
    cu = os.environ.get("PA_TONG_DAI_API_KEY")
    os.environ["PA_TONG_DAI_API_KEY"] = KHOA_THU
    yield
    if cu is None: os.environ.pop("PA_TONG_DAI_API_KEY", None)
    else: os.environ["PA_TONG_DAI_API_KEY"] = cu


def _gia_lap(PA, trang_du_lieu, ghi_lai=None):
    """Thay tầng gọi mạng bằng dữ liệu dựng sẵn. Không phép thử nào được gọi ra internet thật."""
    def goi(url, tham_so):
        if ghi_lai is not None: ghi_lai.append((url, dict(tham_so)))
        t = int(tham_so.get("page", 1))
        return {"code": "1000", "message": "Successful", "data": trang_du_lieu(t)}
    PA._goi = goi


def test_pa1_chua_khai_khoa_thi_noi_ro():
    from app.services import pa_tong_dai as PA
    os.environ.pop("PA_TONG_DAI_API_KEY", None)
    assert PA.da_khai() is False
    with pytest.raises(ValueError) as e:
        PA._goi(PA.CDR, {})
    assert "PA_TONG_DAI_API_KEY" in str(e.value)


def test_pa2_khoa_khong_bao_gio_lot_vao_thong_bao_loi():
    """Khoá lọt vào một dòng lỗi là khoá nằm trong nhật ký máy chủ, trong ảnh chụp màn hình, trong
    khung chat. Chỗ nào cũng khó thu hồi."""
    from app.services import pa_tong_dai as PA
    import urllib.request
    goc = urllib.request.urlopen

    class Hong:
        def __enter__(self): raise OSError("mạng hỏng")
        def __exit__(self, *a): return False
    urllib.request.urlopen = lambda *a, **k: Hong()
    try:
        for ham, tham in ((PA.lich_su, ("2026-08-01", "2026-08-31")),):
            try:
                ham(*tham)
            except Exception as ex:
                assert KHOA_THU not in str(ex), "khoá lọt vào thông báo lỗi"
                assert KHOA_THU not in repr(ex)
    finally:
        urllib.request.urlopen = goc


def test_pa3_ma_loi_dich_ra_tieng_viet():
    from app.services import pa_tong_dai as PA
    import urllib.request
    goc = urllib.request.urlopen

    class Tra:
        def __init__(self, s): self.s = s
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"code": "1004", "message": "not allowed"}).encode()
    urllib.request.urlopen = lambda *a, **k: Tra("")
    try:
        with pytest.raises(ValueError) as e:
            PA.lich_su("2026-08-01", "2026-08-31")
        assert "khoá API" in str(e.value), f"phải dịch ra tiếng Việt, đang trả: {e.value}"
        assert "1004" not in str(e.value) or "khoá API" in str(e.value)
    finally:
        urllib.request.urlopen = goc


def test_pa4_cong_dung_so_cuoc_so_phut_va_so_cuoc_co_ghi_am():
    from app.services import pa_tong_dai as PA
    goc = PA._goi
    du = [{"date_create": "2026-08-01 09:00:00", "duration": 120, "recording": "a.wav", "status": "answered"},
          {"date_create": "2026-08-01 10:00:00", "duration": 60, "recording": "", "status": "not_answer"},
          {"date_create": "2026-08-02 11:00:00", "duration": 300, "recording": "b.wav", "status": "answered"}]
    _gia_lap(PA, lambda t: du if t == 1 else [])
    try:
        d = PA.do_khoi_luong("2026-08-01", "2026-08-31")
        assert d["so_cuoc"] == 3
        assert d["tong_phut"] == 8.0, d                      # (120+60+300)/60
        assert d["so_cuoc_co_ghi_am"] == 2
        assert d["phut_co_ghi_am"] == 7.0                    # (120+300)/60
        assert d["theo_trang_thai"] == {"answered": 2, "not_answer": 1}
        assert d["so_ngay_co_cuoc"] == 2
        assert d["cham_tran"] is False
    finally:
        PA._goi = goc


def test_pa5_phep_do_khong_tra_ve_so_dien_thoai_nao():
    """Lịch sử cuộc gọi là danh sách số điện thoại khách hàng. Câu hỏi "một tháng gọi bao nhiêu phút"
    không cần biết số của ai – đưa cả danh sách ra chỉ vì tiện là cách một phép đo biến thành một kho
    dữ liệu cá nhân."""
    from app.services import pa_tong_dai as PA
    goc = PA._goi
    du = [{"date_create": "2026-08-01 09:00:00", "duration": 120, "recording": "a.wav",
           "status": "answered", "from": "0987133383", "to": "02822317777"}]
    _gia_lap(PA, lambda t: du if t == 1 else [])
    try:
        d = PA.do_khoi_luong("2026-08-01", "2026-08-31")
        chuoi = json.dumps(d, ensure_ascii=False)
        assert "0987133383" not in chuoi and "02822317777" not in chuoi, \
            "phép đo không được mang số điện thoại ra ngoài"
    finally:
        PA._goi = goc


def test_pa6_cham_tran_so_trang_thi_phai_noi_ra():
    """Chạm trần thì con số là SÀN, không phải tổng. Một con số thiếu mà không ai biết là thiếu còn tệ
    hơn không có con số nào."""
    from app.services import pa_tong_dai as PA
    goc = PA._goi
    day = [{"date_create": "2026-08-01 09:00:00", "duration": 60, "recording": "", "status": "answered"}] * PA.TRAN_MOI_TRANG
    _gia_lap(PA, lambda t: day)          # trang nào cũng đầy → không bao giờ hết
    try:
        d = PA.do_khoi_luong("2026-08-01", "2026-08-31", tran_trang=3)
        assert d["cham_tran"] is True
        assert d["so_cuoc"] == 3 * PA.TRAN_MOI_TRANG
    finally:
        PA._goi = goc


def test_pa7_uoc_chi_phi_theo_so_phut_do_duoc_va_ghi_ro_ngay_bang_gia():
    from app.services import pa_tong_dai as PA
    u = PA.uoc_chi_phi_chuyen_chu(1000)
    assert u["phut"] == 1000
    assert u["ngay_bang_gia"], "không ghi ngày bảng giá thì sang năm không ai biết con số này cũ tới đâu"
    assert u["usd_moi_thang"]["gpt-4o-mini-transcribe"] == 3.0
    assert u["usd_moi_thang"]["whisper-1 / gpt-4o-transcribe"] == 6.0
