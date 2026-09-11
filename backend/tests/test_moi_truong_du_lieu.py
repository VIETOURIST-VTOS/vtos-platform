# -*- coding: utf-8 -*-
"""PQ-4 · Quy tắc phân biệt dữ liệu thử nghiệm với dữ liệu thật.

Phép thử ở đây canh LUẬT, không canh cột – cột là việc VPM-1. Nhưng luật sai thì cột dựng theo
luật cũng sai, và cột đã đóng dấu rồi thì không đóng lại được.

Hai chỗ đáng canh nhất, cả hai đều thuộc loại "hỏng thì phải ĐÓNG, không mở":
  · chưa chốt mốc ngày  -> chế độ THỬ NGHIỆM, không phải mặc định là thật
  · mốc gõ sai định dạng -> coi như chưa chốt, không đoán bừa một ngày
"""
from datetime import date, datetime

import pytest

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
from app.models.core import Param
from app.services import moi_truong_du_lieu as MT


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:")
    md.create_all(eng)
    with Session(eng) as s:
        yield s


def _chot_moc(db, gia_tri: str, hai_chu_ky=True, hieu_luc=date(2026, 1, 1)):
    db.add(Param(key=MT.THAM_SO_MOC, value=gia_tri, label="Mốc vận hành thật",
                 effective_from=hieu_luc, status="active" if hai_chu_ky else "pending",
                 signed_chutich=hai_chu_ky, signed_tgd=hai_chu_ky, proposed_by="chutich"))
    db.flush()
    from app.services import rules as R
    if hasattr(R, "clear_param_cache"):
        R.clear_param_cache()


# ---------------------------------------------------------------------------------------------

def test_chua_chot_moc_thi_toan_he_thong_la_thu_nghiem(db):
    """Mặc định phải là THỬ NGHIỆM. Mặc định ngược lại là đóng dấu 'thật' lên số chưa ai kiểm."""
    assert MT.moc_van_hanh_that(db) is None
    assert MT.che_do(db) == MT.THU_NGHIEM
    assert MT.co_cua_ban_ghi_moi(db) == MT.THU_NGHIEM


def test_moc_go_kieu_viet_nam_doc_duoc(db):
    """ĐỔI NGÀY 11/9/2026 theo quyết định của Chủ tịch: định dạng là DD-MM-YYYY, kiểu người Việt gõ.

    Bản trước của phép thử này khẳng định điều NGƯỢC LẠI – "01/10/2026" là gõ sai và phải đọc ra
    'chưa chốt'. Lúc ấy đúng, vì cửa chỉ nhận ISO. Nhưng nó đúng theo cách tệ: người có thẩm quyền
    ngồi ký sẽ gõ đúng kiểu mình vẫn viết, hệ thống nhận vào rồi lặng lẽ coi như chưa ký, và không
    ai tìm ra vì cả hai phía đều "chạy đúng". Sửa cửa cho hợp người, không bắt người hợp cửa.
    """
    _chot_moc(db, "01-10-2026")
    assert MT.moc_van_hanh_that(db) == date(2026, 10, 1)
    _chot_moc(db, "01/10/2026")            # dấu chéo – người ta gõ kiểu này nhiều hơn
    assert MT.moc_van_hanh_that(db) == date(2026, 10, 1)


def test_moc_go_sai_dinh_dang_thi_coi_nhu_chua_chot(db):
    """Hỏng thì ĐÓNG. Đoán bừa một ngày ở đây là đóng dấu không gỡ được lên dữ liệu thử.

    Nhận thêm dạng Việt Nam không có nghĩa là nhận mọi thứ: thứ không đọc chắc chắn được thì trả về
    'chưa chốt' để người nhập gõ lại, chứ không tự hiểu theo một cách rồi im lặng.
    """
    for xau in ("ngày 1 tháng 10", "01-13-2026", "31-02-2026", "1/10/26"):
        _chot_moc(db, xau)
        assert MT.moc_van_hanh_that(db) is None, f"đọc bừa được {xau!r}"
        assert MT.che_do(db) == MT.THU_NGHIEM


def test_truoc_moc_van_la_thu_nghiem_tu_moc_moi_la_that(db):
    _chot_moc(db, "2026-10-01")
    assert MT.moc_van_hanh_that(db) == date(2026, 10, 1)
    assert MT.che_do(db, date(2026, 9, 30)) == MT.THU_NGHIEM
    assert MT.che_do(db, date(2026, 10, 1)) == MT.THAT
    assert MT.che_do(db, datetime(2026, 10, 2, 8, 0)) == MT.THAT


def test_du_lieu_dang_co_deu_mang_nhan_thu_nghiem(db):
    """Đóng dấu hàng loạt cho kho hiện tại là an toàn, và câu ấy kiểm được chứ không phải niềm tin.

    Mốc chưa chốt lần nào nghĩa là chưa có bản ghi nào ra đời trong chế độ thật. Nếu một ngày
    phép thử này đỏ thì nghĩa là mốc ĐÃ chốt – và khi ấy không được đóng dấu hàng loạt nữa.
    """
    assert MT.co_cua_du_lieu_dang_co() == MT.THU_NGHIEM
    assert MT.moc_van_hanh_that(db) is None, (
        "mốc đã chốt rồi thì không còn được đóng dấu hàng loạt 'thử nghiệm' cho cả kho")


def test_khong_ai_doi_duoc_co_va_tu_choi_luon_chi_ra_duong_dung(db):
    """Sửa được cờ nghĩa là sớm muộn có người 'dọn dẹp' số thử thành số thật."""
    assert MT.AI_DUOC_DOI_CO == ()
    for vai_tro in ("chutich", "tgd", "cntt", "ketoan", "nv_dh"):
        duoc, ly_do = MT.doi_co_duoc_khong(vai_tro)
        assert not duoc, f"{vai_tro} đổi được cờ – luật đã bị nới"
        assert MT.THAM_SO_MOC in ly_do, "từ chối mà không chỉ ra đường đi đúng"
        assert "hai chữ ký" in ly_do


def test_bao_cao_khong_duoc_im_lang_khi_dang_dem_so_thu(db):
    """Một báo cáo lặng lẽ đếm số thử rồi trình ra như số thật là đúng thứ luật này sinh ra để chặn."""
    n = MT.nhan_bao_cao(db)
    assert n["phai_hien"] and n["che_do"] == MT.THU_NGHIEM
    assert "THỬ NGHIỆM" in n["cau"] and "chưa chốt" in n["cau"]

    _chot_moc(db, "2026-10-01")
    n = MT.nhan_bao_cao(db, date(2026, 9, 30))
    assert n["che_do"] == MT.THU_NGHIEM and "2026-10-01" in n["cau"] and "chưa tới" in n["cau"]

    # Từ 11/9/2026 có HAI mốc, nên "mọi thứ đều thật" chỉ đạt được khi cả hai mốc đã qua. Trước
    # bản sửa ấy, phép thử này chốt một mốc rồi đòi chế độ THẬT – nay cấu hình đó là quãng TRỘN,
    # và trộn mới là câu trả lời đúng. Sửa phép thử vì LUẬT đổi, không phải vì mã hỏng.
    db.add(Param(key=MT.THAM_SO_MOC_NGUON["vietrip"], value="2026-10-01", label="Mốc Vietrip",
                 effective_from=date(2026, 1, 1), status="active",
                 signed_chutich=True, signed_tgd=True, proposed_by="chutich"))
    db.flush()
    from app.services import rules as R
    if hasattr(R, "clear_param_cache"):
        R.clear_param_cache()

    n = MT.nhan_bao_cao(db, date(2026, 12, 5))
    assert n["che_do"] == MT.THAT and n["phai_hien"], "sang chế độ thật vẫn phải nói rõ đang đếm gì"
    assert "không tính vào" in n["cau"]


def test_bon_nhom_bang_khong_chong_nhau_va_deu_co_ly_do():
    """Một bảng nằm hai nhóm là hai câu trả lời khác nhau cho cùng một câu hỏi."""
    ds = [t for t, _ in MT.BANG_MANG_CO] + [t for t, _c, _l in MT.BANG_THUA_KE] \
         + [t for t, _ in MT.BANG_LOC_THEO_NGUON] + [t for t, _ in MT.BANG_KHONG_MANG_CO]
    assert len(ds) == len(set(ds)), "có bảng được khai ở hai nhóm"
    for t, ly_do in MT.BANG_MANG_CO + MT.BANG_LOC_THEO_NGUON + MT.BANG_KHONG_MANG_CO:
        assert len(ly_do) >= 20, f"{t}: khai mà không nói vì sao"
    for t, cha, ly_do in MT.BANG_THUA_KE:
        assert cha in dict(MT.BANG_MANG_CO), f"{t} thừa kế từ {cha} mà {cha} lại không mang cờ"
        assert ly_do


def test_ba_bang_lon_nhat_deu_phai_mang_co():
    """Ba bảng đang giữ toàn bộ số thử: chuyến, booking, bút toán. Thiếu một là hỏng cả quy tắc."""
    mang = dict(MT.BANG_MANG_CO)
    for t in ("tours", "bookings", "journal_entries"):
        assert t in mang, f"{t} phải mang cờ"
    assert "25.728" in mang["journal_entries"], "ghi lại con số đo được để lần sau đối chiếu"


def test_danh_muc_khong_bi_dong_dau_thu_nghiem():
    """Nhà cung cấp khai lúc chạy thử vẫn là nhà cung cấp có thật.

    Đóng dấu tràn lan là tự tay làm dữ liệu danh mục thành vô dụng: sau ngày vận hành thật, cả
    danh mục mang nhãn 'thử nghiệm' và không ai dám dùng.
    """
    khong = dict(MT.BANG_KHONG_MANG_CO)
    for t in ("suppliers", "companies", "users", "employees", "products", "params"):
        assert t in khong, f"{t} không được mang cờ"
    mang = {t for t, _ in MT.BANG_MANG_CO}
    assert not (mang & set(khong)), "một bảng vừa mang cờ vừa không mang cờ"


def test_nhat_ky_bat_bien_khong_mang_co():
    """audit_log ghi MỌI việc, kể cả chính lần chuyển sang vận hành thật – nó đứng ngoài hai loại."""
    khong = dict(MT.BANG_KHONG_MANG_CO)
    assert "audit_log" in khong and "khoa_ghi" in khong


def test_tra_cuu_nhom_va_bang_cha():
    m = MT.moi_bang_da_khai()
    assert m["tours"] == "mang_co"
    assert m["journal_lines"] == "thua_ke"
    assert m["alerts"] == "loc_theo_nguon"
    assert m["suppliers"] == "khong_mang_co"
    assert MT.bang_cha("tour_cost_lines") == "tours"
    assert MT.bang_cha("tours") == ""


# ---------------------------------------------------------------------------------------------
# Bổ sung 11/9/2026 – Chủ tịch chốt HAI mốc, không phải một
# ---------------------------------------------------------------------------------------------

def _chot(db, khoa, gia_tri):
    db.add(Param(key=khoa, value=gia_tri, label=khoa, effective_from=date(2026, 1, 1),
                 status="active", signed_chutich=True, signed_tgd=True, proposed_by="chutich"))
    db.flush()
    from app.services import rules as R
    if hasattr(R, "clear_param_cache"):
        R.clear_param_cache()


def _chot_hai_moc(db):
    _chot(db, MT.THAM_SO_MOC, "2026-12-01")
    _chot(db, MT.THAM_SO_MOC_NGUON["vietrip"], "2026-10-01")


def test_hai_thang_du_lieu_vietrip_khong_bi_dong_dau_thu_nghiem(db):
    """Quyết định 11/9: vận hành thật 01/12, nhưng từ 01/10 đổ số THẬT từ Vietrip về hàng ngày.

    Với một mốc duy nhất như bản đầu, hai tháng booking thật – tiền thật của khách thật – sẽ mang
    nhãn thử nghiệm và bị loại khỏi mọi báo cáo. Hỏng theo chiều ngược lại, nhưng vẫn là hỏng.
    """
    _chot_hai_moc(db)
    ngay = date(2026, 10, 15)
    assert MT.co_cua_ban_ghi_moi(db, "vietrip", ngay) == MT.THAT
    assert MT.co_cua_ban_ghi_moi(db, "nguoi_nhap", ngay) == MT.THU_NGHIEM
    assert MT.co_cua_ban_ghi_moi(db, "nap_tep", ngay) == MT.THU_NGHIEM
    # Gọi KHÔNG truyền nguồn – đúng cách một chỗ gọi cẩu thả sẽ gọi. Mặc định phải là "người nhập",
    # tức là THỬ NGHIỆM: hỏng thì đóng. Bản đầu của phép thử này truyền "" tường minh nên mặc định
    # chưa bao giờ được thử, và một đột biến đổi mặc định thành "vietrip" đã lọt qua cả bộ.
    assert MT.co_cua_ban_ghi_moi(db, luc=ngay) == MT.THU_NGHIEM, "bỏ trống nguồn phải coi là người nhập"
    assert MT.co_cua_ban_ghi_moi(db, "", ngay) == MT.THU_NGHIEM


def test_truoc_01_10_thi_ca_vietrip_cung_la_thu_nghiem(db):
    _chot_hai_moc(db)
    assert MT.co_cua_ban_ghi_moi(db, "vietrip", date(2026, 9, 30)) == MT.THU_NGHIEM
    assert MT.co_cua_ban_ghi_moi(db, "vietrip", date(2026, 10, 1)) == MT.THAT


def test_tu_01_12_thi_ca_hai_nguon_deu_that(db):
    _chot_hai_moc(db)
    ngay = date(2026, 12, 1)
    assert MT.co_cua_ban_ghi_moi(db, "vietrip", ngay) == MT.THAT
    assert MT.co_cua_ban_ghi_moi(db, "nguoi_nhap", ngay) == MT.THAT
    assert not MT.dang_o_giai_doan_tron(db, ngay), "hết quãng trộn thì phải báo là hết"


def test_quang_tron_duoc_nhan_ra_va_bao_cao_phai_noi_ra(db):
    """10–11/2026 là quãng dễ ra báo cáo sai nhất trong cả vòng đời hệ thống."""
    _chot_hai_moc(db)
    assert MT.dang_o_giai_doan_tron(db, date(2026, 10, 15))
    n = MT.nhan_bao_cao(db, date(2026, 10, 15))
    assert n["che_do"] == "tron" and n["phai_hien"]
    assert "TRỘN" in n["cau"] and "vietrip" in n["cau"]
    assert "2026-10-01" in n["cau"] and "2026-12-01" in n["cau"]


def test_quang_tron_hinh_dang_nguoc_cung_khong_no(db):
    """Người nhập đã thật mà nguồn máy chưa chốt mốc – cấu hình ngược, vẫn phải mô tả đúng.

    Bản đầu chỉ viết cho một hình dạng rồi lấy phần tử [0] của một danh sách rỗng: IndexError.
    """
    _chot(db, MT.THAM_SO_MOC, "2026-10-01")
    n = MT.nhan_bao_cao(db, date(2026, 10, 15))
    assert n["che_do"] == "tron" and "TRỘN" in n["cau"] and "chưa chốt mốc cho nguồn đó" in n["cau"]


def test_so_tong_hop_chi_that_khi_moi_ho_so_cau_thanh_deu_that():
    """Chuyến kéo từ Vietrip (thật) + quyết toán điều hành viên gõ để tập (thử) = số TRỘN.

    Gọi nó là thật thì sai vì giá vốn chưa ai kiểm; gọi nó là thử thì cũng sai vì doanh thu có
    thật. Phải có tên riêng, và báo cáo phải hiện đúng tên ấy.
    """
    assert MT.muc_do_that([MT.THAT, MT.THAT]) == MT.THAT
    assert MT.muc_do_that([MT.THU_NGHIEM, MT.THU_NGHIEM]) == MT.THU_NGHIEM
    assert MT.muc_do_that([MT.THAT, MT.THU_NGHIEM]) == "tron"
    assert MT.muc_do_that([]) == MT.THU_NGHIEM, "không biết gì thì coi là thử – hỏng thì đóng"


def test_dong_dau_hang_loat_co_han_chot_that():
    """Sau 01/10 mà mới chạy UPDATE quét cả bảng là đóng dấu 'thử' lên số thật vừa đồng bộ về."""
    assert MT.HAN_CHOT_DONG_DAU_HANG_LOAT == date(2026, 10, 1)
    assert MT.DE_XUAT_MOC[MT.THAM_SO_MOC_NGUON["vietrip"]] == "2026-10-01"
    assert MT.DE_XUAT_MOC[MT.THAM_SO_MOC] == "2026-12-01"


def test_de_xuat_moc_khong_duoc_tu_co_hieu_luc(db):
    """Hai ngày Chủ tịch nêu chỉ là tài liệu cho tới khi đủ hai chữ ký.

    Nếu mã tự lấy chúng làm mặc định thì mốc có hiệu lực mà chưa qua cửa duyệt – tức mang chữ ký
    của người viết mã. Đây đúng là chỗ dễ "cho tiện" nhất trong cả tệp.
    """
    assert MT.moc_van_hanh_that(db) is None
    assert MT.moc_cua_nguon(db, "vietrip") is None
    assert MT.che_do(db, date(2026, 12, 5)) == MT.THU_NGHIEM
    assert MT.co_cua_ban_ghi_moi(db, "vietrip", date(2026, 10, 15)) == MT.THU_NGHIEM
