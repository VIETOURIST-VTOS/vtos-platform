# -*- coding: utf-8 -*-
"""TC-44 · KẾT QUẢ KINH DOANH — hai biểu đồ cùng kỳ, theo bản vẽ anh Tuấn gửi chiều 16/9/2026.

    "em điều chỉnh chart doanh thu và lợi nhuận trước thuế như bản vẽ và chọn đúng tông màu của
     VTOS, và áp dụng từ năm 2026 về sau"

Bản vẽ: một khối "Kết quả kinh doanh" rộng hết bề ngang, bên trong hai thẻ cạnh nhau, một bộ nút
[Tháng][Quý][Năm] dùng chung kèm ô chọn năm, mười hai cột tháng có vạch kế hoạch nét đứt chạy theo
từng tháng, cột lãi/lỗ tô theo dấu, và bốn con số: tổng kỳ · mục tiêu · tỉ lệ đạt · biên lợi nhuận.

══════════════════════════════════════════════════════════════════════════════════════════════
NĂM CHỖ DỄ HỎNG CỦA VÒNG NÀY — MỖI PHÉP THỬ DƯỚI ĐÂY CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. MỤC TIÊU NĂM CỘNG TỪ MƯỜI HAI THÁNG. Cộng được, và ra một con số trông hợp lý — nhưng nó xoá
   mất một quyết định của Hội đồng quản trị và thay bằng một phép cộng. Anh Tuấn chốt 16/9: chỉ
   tiêu năm và quý do HĐQT nhập riêng.
2. KỲ ĐANG CHẠY TRẢ VỀ RỖNG. Luật "thiếu một tháng thì cả kỳ chưa có số" đúng cho kỳ ĐÃ ĐÓNG. Áp
   nó cho năm đang chạy thì cả năm 2026 hiện "—" tới hết tháng 12, vì tháng 11 chưa xảy ra.
3. "ĐẠT" NHẦM THÀNH "ĐI ĐƯỢC". Tỉ lệ luôn chia cho mục tiêu CẢ KỲ. Gọi nó là "đạt" khi kỳ mới đi
   hai phần ba đường là để người đọc so với 100% rồi kết luận đang hụt.
4. BIÊN LỢI NHUẬN TRÊN DOANH THU BẰNG 0. "Biên lợi nhuận của 0 đồng doanh thu" là câu không có
   nghĩa, và mọi con số trả ra cho nó đều gây hiểu nhầm.
5. HAI THẺ HAI KỲ KHÁC NHAU. Bản cũ (TC-42) cho mỗi ô một bộ nút riêng, nên xem được doanh thu quý
   cạnh lợi nhuận tháng. Không con số nào sai; cái sai là phép so mà người đọc tự làm.
"""
import datetime as dt
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.services import ke_hoach as KH
from app.services import ket_qua_kinh_doanh as KQ
from app.services import xu_huong as XH

GOC = Path(__file__).resolve().parents[2]
KHOI = GOC / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx"
BIEU_DO = GOC / "web" / "components" / "BieuDo.tsx"
SAU_O = GOC / "web" / "components" / "KhoiSauO.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"
CSS = GOC / "web" / "app" / "globals.css"
DICH_VU = GOC / "backend" / "app" / "services" / "ket_qua_kinh_doanh.py"

HOM_NAY = dt.date(2026, 9, 16)


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma(s: str) -> str:
    """Bỏ chú thích, để phép thử canh HÀNH VI chứ không canh chữ trong lời giải thích."""
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


# ═════════════════ 1 · KỲ MẶC ĐỊNH VÀ MÃ KỲ ═════════════════

def test_ky_mac_dinh_la_ky_dang_chay_khong_phai_ky_vua_dong():
    """Người mở bảng điều hành hỏi "công ty đang thế nào", không hỏi "tháng trước thế nào"."""
    assert KQ.ky_mac_dinh("thang", HOM_NAY) == "2026-09"
    assert KQ.ky_mac_dinh("quy", HOM_NAY) == "2026-Q3"
    assert KQ.ky_mac_dinh("nam", HOM_NAY) == "2026"


def test_ma_ky_phai_dung_be_rong_da_chon():
    """Gửi "2026-09" kèm kind="quy" là hai câu hỏi khác nhau chồng lên nhau. Từ chối, không đoán.

    Đoán hộ ở đây nghĩa là trả về số của một kỳ mà người dùng không hỏi, và màn hình sẽ dán nhãn
    "Quý 3" lên con số của tháng 9.
    """
    db = _db()
    with pytest.raises(ValueError):
        KQ.bang(db, kind="quy", ky="2026-09", hom_nay=HOM_NAY)
    with pytest.raises(ValueError):
        KQ.bang(db, kind="nam", ky="2026-Q3", hom_nay=HOM_NAY)
    with pytest.raises(ValueError):
        KQ.bang(db, kind="tuan", ky="", hom_nay=HOM_NAY)


# ═════════════════ 2 · BIÊN LỢI NHUẬN ═════════════════

@pytest.mark.parametrize("ln,dt_,mong", [
    (10.0, 100.0, 0.1),
    (-5.0, 100.0, -0.05),
    (10.0, 0.0, None),      # chia cho 0 — câu hỏi không có nghĩa
    (None, 100.0, None),    # thiếu tử
    (10.0, None, None),     # thiếu mẫu
])
def test_bien_loi_nhuan(ln, dt_, mong):
    assert KQ.bien_loi_nhuan(ln, dt_) == mong


def test_bien_loi_nhuan_khong_bao_gio_tra_0_thay_cho_rong():
    """Rỗng KHÁC 0 ở đây còn nguy hơn chỗ khác: "biên 0%" đọc ra là hoà vốn, không phải chưa có số."""
    assert KQ.bien_loi_nhuan(None, None) is None


# ═════════════════ 3 · TỔNG KỲ ═════════════════

def test_tong_thieu_mot_thang_thi_ca_ky_chua_co_so():
    assert KQ._tong([1.0, 2.0, 3.0]) == 6.0
    assert KQ._tong([1.0, None, 3.0]) is None, (
        "Cộng phần đã có rồi gọi đó là tổng kỳ cho ra một con số nhỏ hơn thật mà nhìn không khác "
        "gì con số đầy đủ."
    )


def _db():
    """Kho rỗng trong bộ nhớ, dựng ĐÚNG những bảng khai được.

    Vì sao không `create_all()` thẳng: bộ thử này chạy chung một tiến trình với mọi tệp thử khác,
    nên `Base.metadata` mang theo cả những bảng do tệp khác nạp vào. Chỉ cần một bảng trong số ấy
    trỏ khoá ngoại tới một bảng chưa được nạp là `create_all` gãy — và gãy ở đây thì lỗi báo về
    một bảng mà phép thử này không hề đụng tới, khiến người đọc đi tìm sai chỗ. Lọc trước thì phép
    thử đứng độc lập với thứ tự chạy, mà vẫn dựng đủ mọi bảng nó cần.
    """
    co = set(Base.metadata.tables)
    # Duyệt `tables.values()` chứ KHÔNG phải `sorted_tables`: phép sắp xếp kia tự đi giải mọi khoá
    # ngoại trước khi trả về, nên nó gãy ngay trước khi bộ lọc kịp chạy.
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def test_ky_dang_chay_cong_thang_da_troi_va_noi_ro_dieu_do():
    """Chỗ hỏng số 2. Năm 2026 xem ngày 16/9 phải có số, kèm dấu hiệu "mới đi 9/12 tháng"."""
    db = _db()
    b = KQ.bang(db, kind="nam", ky="2026", hom_nay=HOM_NAY)
    assert b["dang_chay"] is True
    assert b["so_thang_trong_ky"] == 12 and b["so_thang_da_troi"] == 9, (
        "Màn hình phải đọc được 'mới đi 9 trong 12 tháng' từ chính dữ liệu, không tự đếm lịch."
    )
    # Cùng năm ấy, nhìn từ 2027: kỳ đã đóng, và luật 'thiếu một tháng thì rỗng' áp trở lại.
    c = KQ.bang(db, kind="nam", ky="2026", hom_nay=dt.date(2027, 3, 1))
    assert c["dang_chay"] is False and c["so_thang_da_troi"] == 12


def test_quy_dang_chay_van_la_dang_chay_du_du_ba_thang_trong_danh_sach():
    """Quý 3 xem ngày 16/9 có đủ ba tháng trong danh sách, nhưng tháng 9 mới đi được nửa."""
    db = _db()
    b = KQ.bang(db, kind="quy", ky="2026-Q3", hom_nay=HOM_NAY)
    assert b["dang_chay"] is True
    assert b["so_thang_trong_ky"] == b["so_thang_da_troi"] == 3


# ═════════════════ 4 · MỤC TIÊU ĐỌC THẲNG Ô KỲ ẤY ═════════════════

def test_muc_tieu_ky_khong_bao_gio_cong_tu_thang():
    """Chỗ hỏng số 1 — canh bằng MÃ, vì bằng số thì phải có sổ kế hoạch mới thử được.

    `bang()` được phép gọi `hop_nhat` nhiều lần (mỗi tháng một lần để dựng đường kế hoạch), nhưng
    con số MỤC TIÊU phải đến từ `hop_nhat(db, ky)` — ô của chính kỳ ấy.
    """
    ma = _ma(_doc(DICH_VU))
    assert "muc_tieu = KH.hop_nhat(db, ky)" in ma, (
        "Mục tiêu kỳ phải đọc thẳng ô kỳ ấy. Cộng 12 tháng lại là xoá một quyết định quản trị và "
        "thay bằng một phép cộng."
    )
    assert "sum(" not in ma.split("muc_tieu = ")[1], (
        "Sau dòng đọc mục tiêu không được còn phép cộng nào chen vào giữa nó và giá trị trả ra."
    )


def test_duong_ke_hoach_chay_theo_tung_thang():
    """Một vạch ngang duy nhất là nói dối về mười một tháng còn lại: chỉ tiêu T1 khác T12."""
    ma = _ma(_doc(DICH_VU))
    assert "for t in cac_thang" in ma and "ke_hoach = [" in ma, (
        "Đường kế hoạch phải là MỘT DÃY mười hai giá trị, không phải một con số."
    )
    db = _db()
    b = KQ.bang(db, kind="nam", ky="2026", hom_nay=HOM_NAY)
    dt_ = [c for c in b["chi_tieu"] if c["ma"] == "doanh_thu"][0]
    assert dt_["ke_hoach"] is not None and len(dt_["ke_hoach"]) == 12
    ln = [c for c in b["chi_tieu"] if c["ma"] == "loi_nhuan_truoc_thue"][0]
    assert ln["ke_hoach"] is None, (
        "Lợi nhuận chưa khai `co_ke_hoach` thì KHÔNG được vẽ đường: một đường kế hoạch dựng từ chỉ "
        "tiêu doanh thu đặt trên biểu đồ lợi nhuận là con số của một đại lượng khác hẳn."
    )


def test_muoi_hai_cot_luon_du_va_danh_dau_thang_nao_trong_ky():
    db = _db()
    for kind, ky, so in (("nam", "2026", 12), ("quy", "2026-Q2", 3), ("thang", "2026-05", 1)):
        b = KQ.bang(db, kind=kind, ky=ky, hom_nay=HOM_NAY)
        for ct in b["chi_tieu"]:
            assert len(ct["cot"]) == 12, "Cả ba bề rộng dùng CÙNG mười hai cột — anh Tuấn chốt 16/9."
            assert [c["thang"] for c in ct["cot"]] == list(range(1, 13))
            assert sum(1 for c in ct["cot"] if c["trong_ky"]) == so
        assert b["nam"] == 2026


def test_nam_chon_duoc_bat_dau_tu_2026():
    """"Áp dụng từ năm 2026 về sau" — bày năm 2025 ra chỉ để ai bấm vào cũng gặp hình rỗng."""
    b = KQ.bang(_db(), kind="nam", ky="2026", hom_nay=HOM_NAY)
    assert b["nam_chon_duoc"] == [2026]
    assert min(KH.cac_nam(dt.date(2028, 2, 1))) == 2026
    assert b["ky_hien_tai"] == "2026", (
        "Màn hình phải biết hôm nay là kỳ nào TỪ MÁY CHỦ — đọc đồng hồ máy người dùng thì một máy "
        "sai ngày là một bảng điều hành lệch một tháng mà không ai phát hiện."
    )


# ═════════════════ 5 · MÀN HÌNH ═════════════════

def test_khoi_moi_thay_hai_o_cu_va_khong_de_lai_ban_sao():
    """Chỗ hỏng số 5. Hai ô cũ phải BIẾN MẤT khỏi trang, không nằm song song bản mới."""
    trang = _ma(_doc(TRANG))
    assert "<KhoiKetQuaKinhDoanh" in trang, "Màn hình 01 thiếu khối Kết quả kinh doanh."
    for cu in ("<KhoiDoanhThu", "<KhoiLoiNhuan"):
        assert cu not in trang, (
            f"{cu} vẫn còn trên trang. Giữ cả hai bản là để một con số nằm hai chỗ với hai bộ chọn "
            "kỳ riêng — đúng trạng thái mà bản vẽ 16/9 sinh ra để bỏ đi."
        )
    sau_o = _doc(SAU_O)
    assert "export function KhoiDoanhThu" not in sau_o and "export function KhoiLoiNhuan" not in sau_o, (
        "Bản cũ phải XOÁ chứ không để lại 'phòng khi cần': hai cái tên cùng vẽ doanh thu là hai "
        "chỗ phải sửa khi luật đổi, và sẽ có ngày chỉ một chỗ được sửa."
    )


def test_mot_bo_chon_ky_dung_chung_cho_ca_hai_the():
    ma = _ma(_doc(KHOI))
    assert ma.count("v14-ky-nut") == 1, (
        "Phải đúng MỘT bộ nút Tháng/Quý/Năm cho cả khối. Hai bộ nút là cho phép xem doanh thu quý "
        "cạnh lợi nhuận tháng."
    )
    assert ma.count("<BieuDoCot") == 2, "Khối phải có đúng hai biểu đồ: doanh thu và lợi nhuận."
    assert "useState<Ky>" in ma and ma.count("useState<Ky>") == 1, (
        "Bề rộng kỳ phải là MỘT ô trạng thái duy nhất của cả khối."
    )


def test_man_hinh_khong_tu_tinh_gi_ca():
    """Ranh giới 09/9: mọi phép tính nghiệp vụ nằm ở máy chủ."""
    ma = _ma(_doc(KHOI))
    for dau in ("/ mt.gia_tri", "/ so_dt", "/ tong", "/ d.muc_tieu"):
        assert dau not in ma, f"Màn hình đang tự chia ({dau}) — phép ấy thuộc về máy chủ."
    assert "bien_loi_nhuan" in ma and "d.bien_loi_nhuan" in ma, (
        "Biên lợi nhuận phải LẤY từ máy chủ, không nhân chia tại chỗ."
    )
    assert "ty_le_dat" not in ma.replace("d.ty_le_dat", ""), "Tỉ lệ đạt cũng vậy."


def test_ky_dang_chay_phai_noi_ra_bang_chu_khong_de_nguoi_doc_tu_doan():
    """Chỗ hỏng số 3: tổng chín tháng và tổng mười hai tháng nhìn giống hệt nhau."""
    khoi = _doc(KHOI)
    assert "đến hôm nay" in khoi, "Thiếu nhãn 'đến hôm nay' cho kỳ đang chạy."
    assert "Đi được" in khoi and "Đạt" in khoi, (
        "Kỳ ĐANG CHẠY nói 'đi được', kỳ ĐÃ ĐÓNG mới nói 'đạt'. Một chữ 'đạt' đặt lên kỳ mới đi hai "
        "phần ba đường là để người đọc so với 100% rồi kết luận đang hụt."
    )
    ma = _ma(khoi)
    assert "d.dang_chay" in ma, "Phân biệt hai câu ấy phải dựa vào cờ của máy chủ, không vào lịch."


def test_thieu_muc_tieu_thi_noi_thieu_va_chi_cua_nhap():
    """Ranh giới 09/9: mỗi con số còn thiếu phải kèm AI nhập và NHẬP Ở ĐÂU."""
    khoi = _doc(KHOI)
    assert "Chưa có mục tiêu" in khoi, "Thiếu nhánh 'chưa ai nhập chỉ tiêu kỳ này'."
    assert "còn thiếu" in khoi, (
        "Thiếu nhánh 'nhập thiếu pháp nhân' — nhánh đáng canh nhất: bỏ nó đi thì phần đã nhập bị "
        "cộng lại thành chỉ tiêu, và tỉ lệ đạt cao vọt mà không có gì trông giống lỗi."
    )
    assert "/ke-hoach-thang" in khoi, "Thiếu cửa nhập."
    assert "Hội đồng quản trị" in khoi or "Kế toán" in khoi, "Phải nói AI nhập."


# ═════════════════ 6 · BỘ BIỂU ĐỒ ═════════════════

def test_duong_ke_hoach_dut_doan_o_ky_chua_co_chi_tieu():
    """Nối liền qua chỗ trống là bịa ra một chỉ tiêu chưa ai duyệt."""
    ma = _ma(_doc(BIEU_DO))
    assert 'if (typeof k !== "number" || typeof k2 !== "number") return null;' in ma, (
        "Thiếu một đầu chỉ tiêu thì KHÔNG vẽ đoạn ấy."
    )
    assert "vector-effect" in _doc(CSS), (
        "viewBox bị kéo giãn ngang; không có vector-effect thì nét đứt kéo dẹt thành nét liền và "
        "đường kế hoạch nhìn hệt một đường số thật."
    )


def test_cot_ngoai_ky_mo_di_chu_khong_bien_mat():
    ma = _ma(_doc(BIEU_DO))
    assert '(d.mo ? " mo" : "")' in ma
    assert ma.count('(d.mo ? " mo" : "")') >= 2, (
        "Cả cột CÓ SỐ lẫn ô TRỐNG đều phải mờ khi nằm ngoài kỳ: tháng 11 ngoài kỳ mà không mờ thì "
        "nhìn hệt một tháng trống NẰM TRONG kỳ, hai việc khác hẳn nhau."
    )
    css = _doc(CSS)
    assert ".bd-mot.mo{opacity" in css


def test_mau_lay_tu_bien_nhan_dien_khong_go_ma_mau():
    """Anh Tuấn: "chọn đúng tông màu của VTOS". Đúng tông nghĩa là đúng BIẾN, không phải gõ lại mã."""
    css = _doc(CSS)
    khoi_mau = re.sub(r"/\*(?:.|\n)*?\*/", " ", css)
    lac = {m for m in re.findall(r"#[0-9a-fA-F]{3,8}", khoi_mau)} - {"#fff"}
    assert not lac, f"globals.css có mã màu gõ thẳng: {sorted(lac)}"
    for lop, bien in ((".bd-thanh.lai", "--vtos-success"), (".bd-thanh.lo", "--vtos-danger"),
                      (".bd-duong line", "--vtos-warning")):
        i = css.find(lop)
        assert i > 0, f"Thiếu lớp {lop}"
        assert bien in css[i:i + 240], f"{lop} phải lấy màu từ {bien}"


def test_bieu_do_day_cot_thu_hep_o_be_ngang_dien_thoai():
    """Mười hai cột ở 390px làm nhãn "T10" cắt cụt thành "T.." — tìm ra bằng cách dựng ảnh."""
    ma = _ma(_doc(BIEU_DO))
    assert 'diem.length > 8 ? " day" : ""' in ma, (
        "Hình dày cột phải tự khai ra, để CSS thu hẹp ĐÚNG nó mà không động tới hình sáu cột."
    )
    css = _doc(CSS)
    assert ".bd-than.day" in css, "Thiếu luật thu hẹp cho hình dày cột."


def test_nhan_so_chi_ghi_o_hai_dau_ky():
    """Mười hai con số chen nhau thì không đọc được cái nào."""
    ma = _ma(_doc(KHOI))
    assert "nhan_so: ghi.has(i)" in ma
    assert "trong[0]" in ma and "trong[trong.length - 1]" in ma, (
        "Hai đầu phải là hai đầu CỦA KỲ ĐANG CHỌN, không phải cột 1 và cột 12."
    )
