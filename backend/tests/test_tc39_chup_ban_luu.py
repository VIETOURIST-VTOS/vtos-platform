# -*- coding: utf-8 -*-
"""TC-39 · Chụp bản lưu cuối kỳ, và chốt chặn chống bản chụp muộn.

Anh Tuấn 15/9/2026 xem ba khu biểu đồ và hỏi ngay: "hình như em còn thiếu phải trả và tour chờ
quyết toán". Hai ô ấy trống vì HAI lý do khác hẳn nhau, và vòng này chỉ chữa được lý do thứ hai:

  · PHẢI TRẢ — máy chủ chưa có bảng công nợ phải trả. Không có số thì không vẽ được, và không có
    cách nào vẽ mà không bịa. Việc này thuộc về Kế toán nạp số.
  · TOUR CHỜ QUYẾT TOÁN — CÓ số của hôm nay, nhưng không có kỳ quá khứ nào. Và đây mới là chỗ có
    một việc còn thiếu thật sự trong hệ thống.

PHÁT HIỆN CỦA VÒNG NÀY
══════════════════════════════════════════════════════════════════════════════════════════════
`bao_cao_phong.luu()` đã được viết đầy đủ và chạy đúng từ 10/9/2026 — nhưng KHÔNG CÓ ĐƯỜNG NÀO
GỌI TỚI NÓ. Không router nào, không lịch nào. Nên bảng `bao_cao_luu` rỗng từ ngày nó ra đời.

Đây là kiểu việc còn thiếu tệ nhất: không lỗi, không màn hình nào báo đỏ, chỉ có một cái bảng
rỗng mà ai nhìn cũng nghĩ "chắc chưa tới lúc". Và mỗi tháng trôi qua là mất thêm một kỳ KHÔNG
BAO GIỜ lấy lại được.

VÌ SAO KHÔNG LẤY LẠI ĐƯỢC
══════════════════════════════════════════════════════════════════════════════════════════════
Hai loại chỉ tiêu, và chúng khác nhau ở đúng chỗ này:

  · DÒNG CHẢY (doanh thu, lợi nhuận) — cộng lại sổ quyết toán tháng 8 vào hôm nay vẫn ra đúng con
    số tháng 8. Mất bản lưu không sao.
  · TỒN KHO (tour đang bán, tour chờ quyết toán) — `Tour.status` chỉ giữ trạng thái HIỆN TẠI.
    Tour đã quyết toán xong thì không còn dấu vết nó từng nằm chờ. Không chụp lúc ấy thì câu hỏi
    "cuối tháng 8 có bao nhiêu tour chờ quyết toán" vĩnh viễn không có đáp án.

Và từ đó ra chốt chặn quan trọng nhất của vòng: chạy bù MUỘN cho một kỳ cũ vẫn chạy trơn tru, nó
tính lại từ cơ sở dữ liệu HÔM NAY rồi ghi vào ô mang nhãn kỳ cũ. Với dòng chảy thì đúng; với tồn
kho thì đó là một quá khứ chưa từng tồn tại — có số, có nhãn kỳ, có cột trên biểu đồ, và trông
hoàn toàn bình thường.
"""
import datetime as dt
import re
from pathlib import Path

import pytest

from app.services import dem_tour as DT
from app.services import xu_huong as XH

GOC = Path(__file__).resolve().parents[2]
BCP = GOC / "backend" / "app" / "services" / "bao_cao_phong.py"
ROUTER = GOC / "backend" / "app" / "api" / "v1" / "bao_cao.py"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


# ═════════════════ CHỐT CHẶN CHỐNG CHỤP MUỘN ═════════════════

CUOI_KY = dt.date(2026, 8, 31)


@pytest.mark.parametrize("ngay_chup,kip", [
    (dt.date(2026, 8, 31), True),    # chụp ngay trong đêm cuối kỳ
    (dt.date(2026, 9, 1), True),     # lịch chạy 00:30 ngày 1 — trường hợp bình thường
    (dt.date(2026, 9, 3), True),     # lịch lỡ hai hôm rồi chạy bù: vẫn chấp nhận
    (dt.date(2026, 9, 4), False),    # quá cửa sổ
    (dt.date(2026, 10, 1), False),   # chạy bù sau một tháng — số của tháng 9 dán nhãn tháng 8
    (dt.date(2026, 8, 15), False),   # chụp GIỮA kỳ: số giữa tháng dán nhãn cuối tháng
])
def test_cua_so_chup_hai_dau_deu_chan(ngay_chup, kip):
    assert XH.chup_kip_han(CUOI_KY, ngay_chup) is kip


def test_chup_som_bi_tu_choi_chu_khong_chi_chup_muon():
    """Chụp giữa tháng cũng sai y như chụp muộn: con số là số giữa tháng, mà nhãn ghi cuối tháng.
    Chỉ chặn một đầu là để lọt đúng một nửa số cách làm sai."""
    assert XH.chup_kip_han(CUOI_KY, dt.date(2026, 8, 1)) is False


def test_nhan_ca_chuoi_ngay_va_datetime():
    """`BaoCaoLuu.den` là chuỗi, `tao_luc` là datetime — hàm phải đọc được đúng thứ bảng đang lưu,
    không bắt chỗ gọi tự đổi kiểu."""
    assert XH.chup_kip_han("2026-08-31", dt.datetime(2026, 9, 1, 0, 30)) is True
    assert XH.chup_kip_han("2026-08-31", dt.datetime(2026, 10, 1, 0, 30)) is False


def test_thieu_du_lieu_thi_coi_nhu_khong_kip():
    """Không biết chụp lúc nào thì KHÔNG được coi là hợp lệ. Mặc định 'cho qua' ở đây là để lọt
    đúng những bản lưu cũ chưa ghi thời điểm — tức là những bản đáng ngờ nhất."""
    assert XH.chup_kip_han(None, dt.date(2026, 9, 1)) is False
    assert XH.chup_kip_han("2026-08-31", None) is False
    assert XH.chup_kip_han("khong-phai-ngay", dt.date(2026, 9, 1)) is False


def test_cho_doc_moi_chan_chu_khong_phai_cho_ghi():
    """Chỗ ghi thì ai cũng có thể chạy bù (và bản lưu vẫn có giá trị cho chỉ tiêu dòng chảy và cho
    việc đối chiếu). Chỗ đọc thì chỉ có một. Chặn ở chỗ ghi là vứt luôn cả phần đúng."""
    nguon = _doc(GOC / "backend" / "app" / "services" / "xu_huong.py")
    than = nguon[nguon.index("def _doc_ban_luu"):]
    assert "chup_kip_han" in than, "Hàm đọc bản lưu phải kiểm thời điểm chụp."
    # Bỏ chú thích và chuỗi tài liệu trước khi soi: cửa chụp NÊN nhắc tới chốt chặn này trong phần
    # giải thích — cái không được phép là GỌI nó.
    ma_router = re.sub(r'"""(?:.|\n)*?"""', "", _doc(ROUTER))
    ma_router = re.sub(r"^\s*#.*$", "", ma_router, flags=re.M)
    assert "chup_kip_han" not in ma_router, "Cửa chụp KHÔNG được tự chặn chạy bù."


def test_han_chup_khai_thanh_hang_so_co_ten():
    """Một con số 3 nằm trần trong phép so sánh thì ba tháng sau không ai biết nó là gì."""
    assert XH.HAN_CHUP_NGAY >= 1
    assert "HAN_CHUP_NGAY" in _doc(GOC / "backend" / "app" / "services" / "xu_huong.py")


# ═════════════════ MỘT CHỖ ĐỊNH NGHĨA "ĐANG BÁN" / "CHỜ QUYẾT TOÁN" ═════════════════

def test_hai_trang_thai_deu_thuoc_cho_quyet_toan():
    """`ket_thuc` là chuyến đã đi xong chưa đóng sổ; `da_dong_so` là đã đóng sổ chưa xác nhận. Cả
    hai đều là tiền chưa chốt được, nên Chủ tịch đọc chúng như MỘT việc."""
    assert set(DT.CHO_QUYET_TOAN) == {"ket_thuc", "da_dong_so"}
    assert set(DT.DANG_BAN) == {"da_duyet"}


def test_hai_nhom_khong_giao_nhau():
    """Một tour nằm ở cả hai nhóm thì tổng hai con số lớn hơn số tour có thật."""
    assert not (set(DT.DANG_BAN) & set(DT.CHO_QUYET_TOAN))


def test_cong_dung_tu_bang_dem_co_san_khong_hoi_lai_co_so_du_lieu():
    """`_toan_cty` đếm một lần rồi truyền bảng đếm vào cả hai hàm. Gọi hai lần là hai lượt truy vấn
    cho cùng một câu hỏi, và tệ hơn: hai lượt ở hai thời điểm khác nhau."""
    dem = {"da_duyet": 46, "ket_thuc": 12, "da_dong_so": 6, "nhap": 3}
    assert DT.dang_ban(None, dem) == 46
    assert DT.cho_quyet_toan(None, dem) == 18


def test_trang_thai_vang_mat_tinh_la_0_khong_phai_loi():
    """Nhóm theo trạng thái thì trạng thái không có tour nào sẽ KHÔNG có mặt trong kết quả. Đây là
    chỗ 0 đúng là 0: không có tour nào ở trạng thái ấy là một sự thật, không phải chỗ trống."""
    assert DT.dang_ban(None, {}) == 0
    assert DT.cho_quyet_toan(None, {"da_duyet": 5}) == 0


def test_mon_no_routes_py_duoc_ghi_ra_chu_khong_de_vo_hinh():
    """routes.py vẫn tự gom nhóm cùng phép đếm này. Vòng này chưa sửa vì đó là tệp trung tâm của
    toàn bộ API và bản checkout ở đây không đủ để chạy thử nó. Món nợ được ghi ra thì lần sau còn
    tìm thấy; không ghi thì nó thành hai chỗ đếm mà không ai biết."""
    t = _doc(GOC / "backend" / "app" / "services" / "dem_tour.py")
    assert "routes.py" in t and "group_by" in t


# ═════════════════ HAI CHỈ TIÊU MỚI TRONG BẢN LƯU ═════════════════

def test_ban_luu_co_dung_hai_ma_ma_xu_huong_di_tim():
    """Sai một chữ trong mã là bản lưu có số mà biểu đồ vẫn trống, và không chỗ nào báo lỗi."""
    t = _doc(BCP)
    for ma in ("tour_dang_ban", "tour_cho_quyet_toan"):
        assert f'ct("{ma}"' in t, f"Bản lưu toàn công ty thiếu chỉ tiêu {ma}"
        assert XH.CHI_TIEU[ma].khoa_luu == ma


def test_cong_thuc_noi_ro_day_la_so_tai_mot_thoi_diem():
    """Ba tháng nữa người đọc bản lưu chỉ thấy JSON, không thấy tệp mã. Câu cảnh báo phải nằm
    trong phần CÔNG THỨC của chính chỉ tiêu, không nằm trong chú thích mã."""
    t = _doc(BCP)
    khuc = t[t.index('ct("tour_dang_ban"'): t.index('ct("tour_cho_quyet_toan"') + 600]
    assert khuc.count("TẠI THỜI ĐIỂM CHỤP") == 2
    assert khuc.count("không tính lại được") == 2


def test_hai_chi_tieu_nay_thuoc_loai_ton_kho():
    """Khai nhầm sang dòng chảy là `doc_that` sẽ đi tính lại chúng từ dữ liệu hôm nay — đúng cái
    sai mà cả vòng này dựng ra để chặn."""
    assert XH.CHI_TIEU["tour_dang_ban"].loai == XH.TON_KHO
    assert XH.CHI_TIEU["tour_cho_quyet_toan"].loai == XH.TON_KHO


# ═════════════════ CỬA CHO LỊCH TỰ ĐỘNG ═════════════════

def test_co_cua_chup_va_xac_thuc_bang_robot_token():
    """Không dựng kiểu xác thực thứ ba cho riêng cửa này: mỗi kiểu là một chỗ phải canh, và cái
    yếu nhất quyết định mức an toàn của cả hệ thống."""
    t = _doc(ROUTER)
    assert '@router.post("/chup"' in t
    assert "robot_auth" in t
    assert re.search(r"from app\.api\.deps import [^\n]*robot_auth", t)


def test_cua_chup_nhan_ngay_de_lich_noi_ro_y_dinh():
    """Chạy 00:30 ngày 1 mà không truyền ngày thì `khoang("thang")` trả về THÁNG MỚI — tức chụp
    một tháng mới đi được nửa tiếng rồi ghi đè lên đúng ô đáng ra chứa tháng vừa đóng. Một dòng
    cấu hình lịch sai chỗ này là hỏng vĩnh viễn số liệu kỳ ấy."""
    t = _doc(ROUTER)
    than = t[t.index('@router.post("/chup"'):]
    assert "ngay: str" in than
    assert "THÁNG MỚI" in than, "Cái bẫy này phải được ghi ngay tại cửa, không để trong bộ kiểm."


def test_cua_chup_tra_ve_ca_pham_vi_hong():
    """Một phạm vi hỏng không làm cả mẻ thất bại — nhưng lịch tự động chỉ đọc mã trạng thái, nên
    một mẻ 'thành công' mà thiếu ba phòng thì không ai biết."""
    than = _doc(ROUTER)
    than = than[than.index('@router.post("/chup"'):]
    assert "kq['hong']" in than or 'kq["hong"]' in than


def test_cua_chup_tu_choi_ky_la_va_ngay_sai_dang():
    than = _doc(ROUTER)[_doc(ROUTER).index('@router.post("/chup"'):]
    assert "BP.TEN_KY" in than and "422" in than
    assert "fromisoformat" in than and "ValueError" in than
