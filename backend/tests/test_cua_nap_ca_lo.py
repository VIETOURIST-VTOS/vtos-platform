# -*- coding: utf-8 -*-
"""CỬA NẠP CẢ LÔ — nhiều tệp một lượt, nhưng MỖI TỆP MỘT LẦN NẠP.

VÌ SAO CÓ CỬA NÀY

Kho quyết toán cũ là việc theo lô từ bản chất: tháng 1/2026 có 81 tệp, mỗi tệp một chuyến; T1–T6 có
604 tệp. Nhưng đến 14/9/2026 ô chọn tệp ở màn hình Nạp dữ liệu nhận đúng MỘT tệp (`files?.[0]`).

Nạp tháng 1 vì thế là 81 lượt chọn tệp cho cửa "Tạo chuyến", rồi 81 lượt nữa cho cửa "Kho quyết toán
CŨ" — 162 lượt; cả nửa năm là hơn 1.200 lượt. Theo đúng ranh giới Chủ tịch chốt 09/9 ("có việc thì
phải có cửa"), đó là một cửa CÒN THIẾU, không phải việc để người dùng bấm bù bằng tay.

MỘT KẾT LUẬN SAI ĐÃ BỊ CHÍNH PHÉP THỬ NÀY BÁC — GHI LẠI ĐỂ KHÔNG AI SUY LẠI

Bản nháp đầu của tệp này viết rằng gộp dòng nhiều tệp làm MỘT lần nạp sẽ cắt mất cầu nối tệp↔chuyến
(sổ `kho_cu_tep_chuyen`), và mối nối sang bản đối chiếu H1 rơi từ 95% xuống gần như không còn.

CHẠY THỬ THÌ KHÔNG PHẢI. Mỗi dòng mang sẵn `ten_tep` của chính nó, và `nap_lo` ghi sổ bằng tên nằm
trong DÒNG (`h["tep"]`) chứ không bằng tham số `ten_tep` của lần gọi. Gộp hai tệp rồi nạp một lần,
cầu nối vẫn ra đúng hai dòng, đúng hai tên tệp, trỏ đúng hai chuyến. CL3 dưới đây canh đúng điều ấy,
để lần sau không ai "sửa" một chỗ vốn không hỏng.

Lý do thật để gọi theo từng tệp nhỏ hơn, nhưng vẫn là lý do:

  1. NHẬT KÝ NẠP. `intake_runs` ghi một dòng cho mỗi lần gọi, kèm tên tệp và mã băm nội dung. Gộp
     81 tệp là MỘT dòng nhật ký mang một cái tên bịa cho dữ liệu của 81 tệp — câu "con số này ở đâu
     ra" hết trả lời được, mà đó là lý do cả màn hình Nhật ký nạp tồn tại.
  2. CÔ LẬP LỖI. Ô "bỏ qua dòng lỗi" là quyết định cho MỘT tệp; gộp lô thì nó áp lên cả 81 tệp.
  3. DỪNG GIỮA CHỪNG. Hỏng ở tệp thứ 57 mà gộp lô thì không biết gì đã vào, gì chưa.

  CL1  hai tệp nạp riêng thì nhật ký có HAI dòng, mỗi dòng đúng tên tệp của nó
  CL2  sổ tệp↔chuyến có một dòng cho MỖI tệp
  CL3  gộp lô thì cầu nối VẪN ĐÚNG — chốt lại sự thật đã đo, chống lại kết luận sai đã từng viết ra
  CL4  gộp lô làm MẤT dấu vết nguồn ở nhật ký — đây mới là cái giá thật của việc gộp
  CL5  màn hình có ô chọn NHIỀU tệp
  CL6  màn hình gọi nạp theo TỪNG tệp, không gộp dòng
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_nap_ca_lo.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_nap_ca_lo.db", "test_nap_ca_lo.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import pytest                                                          # noqa: E402

import app.models                                                      # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine                   # noqa: E402
from app.models.core import Tour, User                                  # noqa: E402
from app.models.intake import IntakeRun                                 # noqa: E402
from app.models.kho_cu import KhoCuTepChuyen                            # noqa: E402
from app.services import intake_tao_chuyen as ITC                       # noqa: E402
from app.services import tao_chuyen_kho_cu as TC                        # noqa: E402

Base.metadata.create_all(engine)

TEP_A = "QT NAM CÁT TIÊN 24.01.2026 (1 ngày).xlsx"
TEP_B = "QT NINH CHỮ - VĨNH HY 3N2D 05.01.2026.xlsx"

# `ten_tep` nằm NGAY TRONG DÒNG – đây chính là chi tiết mà cả tệp phép thử này xoay quanh. Bộ đọc
# `doc_tep_lo(noi_dung, ten_tep)` gắn nó vào lúc đọc, nên tên tệp đi theo dữ liệu chứ không đi theo
# lần gọi. Thiếu khoá này thì `bang()` không suy ra được ngày lẫn mã, và không tạo chuyến nào.
DONG_A = [{"ten_tep": TEP_A, "ma_tour": "", "ten_tour": "NAM CÁT TIÊN",
           "ngay_di": "24/01/2026", "ngay_ve": "24/01/2026", "so_khach": 20}]
DONG_B = [{"ten_tep": TEP_B, "ma_tour": "", "ten_tour": "NINH CHỮ - VĨNH HY",
           "ngay_di": "05/01/2026", "ngay_ve": "07/01/2026", "so_khach": 15}]


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(KhoCuTepChuyen).delete()
    s.query(IntakeRun).delete()
    s.query(Tour).delete()
    s.query(User).delete()
    # nap_lo DỪNG nếu không có tài khoản điều hành nhận lô – không lấy bừa một người đang làm việc.
    s.add(User(username="dieuhanhvietrip", full_name="Điều hành Vietrip", role="nv_dh",
               password_hash="x", active=True))
    s.commit()
    yield s
    s.close()


def _nap(db, rows, ten_tep):
    """Gọi thẳng bộ nạp theo lô, đúng như màn hình gọi qua /nap-du-lieu/nap."""
    kq = ITC.nap_lo(db, rows, boi="dieuhanhvietrip", ten_tep=ten_tep, bo_qua_dong_loi=False)
    db.add(IntakeRun(loai="tao_chuyen_kho_cu", ten_tep=ten_tep[:200], so_dong=len(rows),
                     da_nap=kq.get("da_nap", 0), boi="dieuhanhvietrip", nguon="nguoi_nhap"))
    db.commit()
    return kq


# ── Nạp từng tệp: cách ĐÚNG ──────────────────────────────────────────────────────────────────────

def test_cl1_hai_tep_nap_rieng_thi_nhat_ky_co_hai_dong_dung_ten(db):
    _nap(db, DONG_A, TEP_A)
    _nap(db, DONG_B, TEP_B)

    ten = sorted(r.ten_tep for r in db.query(IntakeRun).all())
    assert ten == sorted([TEP_A, TEP_B]), (
        "nhật ký nạp phải ghi ĐÚNG tên từng tệp – gộp lô là nhật ký nói dối về nguồn của con số")


def test_cl2_so_tep_chuyen_co_mot_dong_cho_moi_tep(db):
    _nap(db, DONG_A, TEP_A)
    _nap(db, DONG_B, TEP_B)

    cau = {r.ten_tep: r.tour_id for r in db.query(KhoCuTepChuyen).all()}
    assert set(cau) == {TEP_A, TEP_B}, "thiếu cầu nối tệp↔chuyến cho một trong hai tệp"
    assert cau[TEP_A] != cau[TEP_B], "hai tệp khác nhau lại trỏ về cùng một chuyến"
    assert all(v for v in cau.values()), "cầu nối có nhưng không trỏ vào chuyến nào"


def test_cl3_gop_lo_thi_cau_noi_VAN_DUNG(db):
    """Chốt lại một SỰ THẬT ĐÃ ĐO, để chống lại một kết luận sai đã từng được viết ra.

    Suy từ chữ ký hàm `nap_lo(db, rows, boi, ten_tep=...)` thì rất dễ kết luận rằng cả lô dùng chung
    một `ten_tep`, nên gộp lô là mất cầu nối tệp↔chuyến. Kết luận ấy SAI, và nó đã được viết vào mã
    lẫn vào chú thích trước khi có ai chạy thử.

    Sự thật: tên tệp đi kèm TRONG TỪNG DÒNG, và `nap_lo` ghi sổ bằng tên trong dòng. Phép thử này
    giữ lấy sự thật ấy, để lần sau không ai đi "sửa" một chỗ vốn không hỏng.
    """
    _nap(db, DONG_A + DONG_B, "ca-lo-thang-1.xlsx")

    assert db.query(Tour).count() == 2, "hai dòng phải tạo ra hai chuyến"
    cau = {r.ten_tep: r.tour_id for r in db.query(KhoCuTepChuyen).all()}
    assert set(cau) == {TEP_A, TEP_B}, (
        "gộp lô mà cầu nối tệp↔chuyến mất tên từng tệp – nếu đến một ngày điều này thành thật thì "
        "nap_lo đã đổi cách ghi sổ, và cửa nạp cả lô phải được đọc lại từ đầu")
    assert cau[TEP_A] != cau[TEP_B]
    khoa = {TC.khoa_tep(TEP_A), TC.khoa_tep(TEP_B)}
    assert khoa <= {r.khoa_tep for r in db.query(KhoCuTepChuyen).all()}, \
        "khoá tra cứu sang bản đối chiếu H1 phải còn nguyên cho từng tệp"


def test_cl4_gop_lo_lam_mat_dau_vet_nguon_o_nhat_ky(db):
    """CÁI GIÁ THẬT của việc gộp lô – nhỏ hơn cái đã bị bác ở CL3, nhưng có thật.

    Nhật ký nạp là chỗ trả lời câu "con số này ở đâu ra". Gộp 81 tệp thành một lần gọi thì nó ghi
    MỘT dòng mang một cái tên không phải tên của tệp nào cả.
    """
    _nap(db, DONG_A + DONG_B, "ca-lo-thang-1.xlsx")
    ls = db.query(IntakeRun).all()
    assert len(ls) == 1 and ls[0].ten_tep == "ca-lo-thang-1.xlsx"
    assert TEP_A not in {r.ten_tep for r in ls} and TEP_B not in {r.ten_tep for r in ls}, (
        "gộp lô đáng lẽ làm nhật ký mất tên tệp thật; nếu không thì phép thử này đã lỗi thời")
    assert ls[0].so_dong == 2, "một dòng nhật ký đang gánh dữ liệu của hai tệp"


# ── Màn hình ────────────────────────────────────────────────────────────────────────────────────

def _trang():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "web", "app", "nap-du-lieu", "page.tsx")
    if not os.path.exists(p):
        pytest.skip("không có cây web cạnh cây backend")
    return open(p, encoding="utf-8").read()


def test_cl5_man_hinh_co_o_chon_nhieu_tep():
    """Không có ô này thì nạp tháng 1 là 162 lượt chọn tệp, và thực tế là không ai nạp."""
    src = _trang()
    assert "multiple" in src, "màn hình Nạp dữ liệu không có ô chọn nhiều tệp"
    assert "kiemTraCaLo" in src and "napCaLo" in src, "thiếu đường đọc/nạp cả lô"


def test_cl6_man_hinh_nap_theo_tung_tep_chu_khong_gop_dong():
    """Chốt cuối, và là chốt canh đúng cái sai dễ xảy ra nhất.

    Đọc thẳng tệp màn hình vì chỗ hỏng nằm ở phía người dùng: máy chủ đã nhận `ten_tep` theo từng
    lần gọi, nên chỉ cần màn hình gộp dòng lại là hỏng, mà không endpoint nào biết để từ chối.
    """
    src = _trang()
    i = src.find("const napCaLo")
    assert i > 0, "không tìm thấy hàm nạp cả lô"
    than = src[i:i + 2000]
    assert "ten_tep: t.ten_tep" in than, (
        "nạp cả lô phải gửi TÊN CỦA TỪNG TỆP; gửi một tên chung là nhật ký nói dối và mất cầu nối "
        "tệp↔chuyến sang bản đối chiếu H1")
    assert "rows: t.rows" in than, "phải gửi dòng của từng tệp, không gộp"
    for xau in (".flat(", ".flatMap(", "concat("):
        assert xau not in than, f"nạp cả lô đang gộp dòng bằng {xau} – mỗi tệp phải một lần nạp"


def test_cl7_them_cua_ca_lo_khong_duoc_xoa_nut_tai_mau_xlsx():
    """CANH VIỆC CỦA LANE KHÁC TRÊN CÙNG MỘT MÀN HÌNH.

    Chuyện đã xảy ra thật, phát hiện ngày 15/9/2026 khi soi bản so sánh nhánh trước lúc gộp: bản
    thêm cửa nạp cả lô được viết đè lên một bản `page.tsx` CŨ, nên nó XOÁ MẤT `taiMauRieng` – hàm
    tải mẫu .xlsx mà lane khác vừa thêm vào `main`.

    Hàm ấy tồn tại vì một lý do cụ thể: `taiMau()` đọc phản hồi bằng `.text()`, đúng cho CSV nhưng
    làm hỏng .xlsx (tệp nén nhị phân, đọc thành chuỗi rồi gói lại là tệp Excel mở không lên). Gộp
    nhánh ấy vào là bật lại đúng cái lỗi kia, mà không phép thử nào của kho biết để kêu lên — vì
    không phép thử nào đứng canh.

    Nhiều làn cùng sửa một tệp màn hình thì mỗi làn phải để lại một chốt canh phần của mình.
    """
    src = _trang()
    assert "taiMauRieng" in src, (
        "màn hình Nạp dữ liệu mất hàm tải mẫu .xlsx – nhiều khả năng một bản sửa được viết đè lên "
        "page.tsx cũ. Lấy lại từ main, đừng viết lại từ đầu.")
    assert "mau_rieng" in src, "mất nhánh hiện nút mẫu riêng cho bộ nạp có mẫu .xlsx"
    assert ".blob()" in src, (
        "tải mẫu .xlsx phải đọc bằng .blob(); đọc bằng .text() là tệp Excel mở không lên")


def test_cl8_cua_soat_tra_ve_HAI_hinh_dang_va_man_hinh_phai_doc_ca_hai(db):
    """CỬA NẠP CẢ LÔ ĐỌC NHẦM KHOÁ NÊN KHÔNG NẠP ĐƯỢC GÌ — đo trên hệ thống thật 16/9/2026.

    `/nap-du-lieu/kiem-tra-tep` trả về HAI hình dạng khác nhau:

        bộ nạp thường  -> _kiem_tra_tung_dong  -> khoá `hop_le`
        bộ nạp THEO LÔ -> kiem_lo              -> khoá `da_nap`, KHÔNG có `hop_le`

    Hai cửa kho quyết toán cũ – đúng hai cửa mà màn hình nạp cả lô sinh ra để phục vụ – đều là bộ
    nạp theo lô. Bản đầu của màn hình chỉ đọc `d.hop_le`, nên với chúng nó luôn nhận `undefined`.

    Chạy thật trên vtos.infinitytours.org: chọn cả 81 tệp tháng 1/2026 thì bảng hiện đủ 81 dòng
    "sẵn sàng", không tệp nào lỗi — nhưng ô đếm ghi "0 dòng hợp lệ" và nút ghi "Nạp 0 TỆP vào hệ
    thống". Cửa mở ra mà không nạp được gì.

    Phép thử này giữ HAI điều: (a) sự thật về hình dạng phía máy chủ, (b) màn hình đọc cả hai khoá.
    Mai kia máy chủ đổi tên khoá thì (a) đỏ trước, không phải đợi người dùng phát hiện.
    """
    from app.services import intake as IN

    lo = sorted(k for k, v in IN.BO_NAP.items() if v.get("lo"))
    assert "tao_chuyen_kho_cu" in lo and "kho_quyet_toan_cu" in lo, (
        f"hai cửa kho quyết toán cũ phải là bộ nạp theo lô; đang có: {lo}")
    assert len(lo) >= 6, (
        f"chỉ tìm thấy {len(lo)} bộ nạp theo lô – lỗi đọc nhầm khoá ảnh hưởng TẤT CẢ chúng, "
        "không riêng hai cửa kho cũ")

    kq = IN.kiem_tra(db, "tao_chuyen_kho_cu", DONG_A)
    assert "da_nap" in kq, "bộ nạp theo lô phải trả khoá 'da_nap'"
    assert "hop_le" not in kq, (
        "bộ nạp theo lô nay đã trả 'hop_le' – nếu đổi thật thì sửa lại chú thích ở kiemTraCaLo, "
        "đừng bỏ phép thử này")

    src = _trang()
    i = src.find("const kiemTraCaLo")
    assert i > 0, "không tìm thấy hàm đọc thử cả lô"
    than = src[i:i + 2500]
    assert "d.da_nap" in than, (
        "màn hình nạp cả lô không đọc khoá 'da_nap' – hai cửa kho quyết toán cũ sẽ luôn hiện "
        "'Nạp 0 tệp' dù mọi tệp đều sạch")
    assert "??" in than, "phải dùng ?? chứ không phải || – số 0 là câu trả lời thật, không phải rỗng"
