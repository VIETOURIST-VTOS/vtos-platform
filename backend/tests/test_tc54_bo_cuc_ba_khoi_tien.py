# -*- coding: utf-8 -*-
"""TC-54 · BA KHỐI TIỀN MỘT HÀNG, PHẢI THU ĐỨNG SONG SONG PHẢI TRẢ.

    "em kiem tra lai bản thu 01, hien tai tren man hinh chu tich van chua đúng,
     phai thu - phai tra song song nhau, va cac ô o dưới cung chưa cân xứng"
                                                              — anh Tuấn, 17/9/2026

TC-42 xếp BỐN khối (Dòng tiền · Phải thu · Phải trả · Tồn đọng) vào một lưới hai cột, nên chúng
rơi thành:

        Dòng tiền  │  Phải thu
        Phải trả   │  Tồn đọng

Phải thu và Phải trả nằm CHÉO nhau. Mà hai khối ấy dùng CHUNG một bộ bảy mốc hạn (TC-45) — cái
lợi lớn nhất của chúng là đọc SO HÀNG NGANG: "quá hạn phải thu 12,1 tỷ, quá hạn phải trả 5,3 tỷ"
chỉ đọc ra khi hai hàng ấy ngang tầm mắt. Bản thử anh Tuấn duyệt đặt cả ba khối tiền một hàng.

══════════════════════════════════════════════════════════════════════════════════════════════
LUẬT TC-42 BỊ ĐẢO, VÀ GHI LẠI CẢ HAI VẾ
══════════════════════════════════════════════════════════════════════════════════════════════
TC-42 đặt `align-items:start` với lý lẽ: "khoảng trắng dưới một khối trông giống dữ liệu còn
thiếu". Trên bản chạy thật điều ngược lại xảy ra — ba khối cao thấp so le làm cả hàng trông như
chưa dựng xong. Khoảng trắng BÊN TRONG một khung có viền đọc ra là khoảng thở; ba đáy khung lệch
nhau thì không đọc ra gì cả.

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. TỒN ĐỌNG Ở LẠI TRONG LƯỚI. Bốn khối trong lưới ba cột thì khối thứ tư tụt xuống một mình, và
   Phải thu / Phải trả lại lệch hàng ở bề ngang khác. Tồn đọng phải RỜI hẳn ra hàng riêng.
2. BỀ NGANG TRUNG GIAN LÀM CHÚNG LỆCH LẠI. Ở 900–1279px lưới còn hai cột; để nó tự chia thì
   Dòng tiền chiếm ô 1, Phải thu ô 2, Phải trả tụt xuống ô 3 — CHÉO NHAU ĐÚNG NHƯ CŨ, mà chỉ lộ
   ra ở một khoảng bề ngang nên dễ lọt qua mắt. Dòng tiền phải chiếm TRỌN hàng trên ở khoảng ấy.
3. `align-items:start` CÒN SÓT. Chỉ cần một chỗ còn `start` là cả hàng lại so le.
4. THỨ TỰ BA KHỐI BỊ ĐẢO. Lớp CSS trỏ tới Dòng tiền bằng `:first-child`; đổi thứ tự trong
   page.tsx là đổi luôn khối nào chiếm trọn hàng, mà không có lỗi biên dịch nào báo.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "page.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma_tsx(s: str) -> str:
    """Bỏ chú thích {/* … */} và // … — canh HÀNH VI, không canh chữ trong lời giải thích (TC-41)."""
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


def _ma_css(s: str) -> str:
    return re.sub(r"/\*(?:.|\n)*?\*/", " ", s)


def _khoi_luoi(ma: str) -> str:
    """Nội dung giữa <div className="mh01-sau-o"> và </div> đóng nó."""
    i = ma.index('className="mh01-sau-o"')
    j = ma.index("</div>", i)
    return ma[i:j]


# ═════════════════ 1 · TỒN ĐỌNG RỜI KHỎI LƯỚI ═════════════════

def test_ton_dong_khong_con_nam_trong_luoi_ba_khoi_tien():
    """Chỗ hỏng số 1."""
    ma = _ma_tsx(_doc(TRANG))
    assert "KhoiTonDongMuc" in ma, "Khối Tồn đọng phải còn trên màn hình, chỉ là ở hàng riêng."
    assert "KhoiTonDongMuc" not in _khoi_luoi(ma), (
        "Bốn khối trong lưới ba cột thì khối thứ tư tụt xuống một mình và Phải thu / Phải trả lại "
        "lệch hàng. Tồn đọng là loại khác — ba dòng theo mức độ, không có trục nào để so với hai "
        "bảng hạn — nên nó đứng hàng riêng."
    )


def test_luoi_chi_con_dung_ba_khoi_tien_dung_thu_tu():
    """Chỗ hỏng số 4: lớp CSS trỏ tới Dòng tiền bằng `:first-child`."""
    khoi = _khoi_luoi(_ma_tsx(_doc(TRANG)))
    thu_tu = [t for t in ("KhoiDongTien", "KhoiPhaiThu", "KhoiPhaiTra") if t in khoi]
    assert thu_tu == ["KhoiDongTien", "KhoiPhaiThu", "KhoiPhaiTra"], (
        "Ba khối phải đúng thứ tự Dòng tiền → Phải thu → Phải trả. CSS chiếm-trọn-hàng trỏ tới "
        "khối đầu bằng `:first-child`; đảo thứ tự là đổi bố cục mà không có lỗi biên dịch nào báo."
    )
    assert khoi.index("KhoiPhaiThu") < khoi.index("KhoiPhaiTra"), "Phải thu đứng trước Phải trả."


# ═════════════════ 2 · BỀ NGANG TRUNG GIAN ═════════════════

def test_be_ngang_trung_gian_dong_tien_chiem_tron_hang_de_hai_khoi_kia_song_song():
    """Chỗ hỏng số 2 — chỗ chỉ lộ ra ở một khoảng bề ngang nên dễ lọt qua mắt."""
    css = _ma_css(_doc(CSS))
    i = css.index(".mh01-sau-o{")
    khoi = css[i:i + 1200]
    assert re.search(r"\.mh01-sau-o>:first-child\{grid-column:1\s*/\s*-1\}", khoi), (
        "Ở 900–1279px lưới còn hai cột. Không cho Dòng tiền chiếm trọn hàng trên thì Phải thu ô 2, "
        "Phải trả tụt xuống ô 3 — chéo nhau đúng như lỗi vừa sửa."
    )
    assert "grid-template-columns:1.25fr 1fr 1fr" in khoi, (
        "Màn rộng phải là BA cột, Dòng tiền rộng hơn vì biểu đồ 13 tuần cần chỗ."
    )


# ═════════════════ 3 · KHÔNG CÒN align-items:start ═════════════════

def test_khong_con_align_items_start_o_hai_hang_khoi():
    """Chỗ hỏng số 3 — chỉ cần một chỗ còn `start` là cả hàng lại so le."""
    css = _ma_css(_doc(CSS))
    for lop in (".mh01-sau-o{", ".mh01-hang-3{"):
        i = css.index(lop)
        dong = css[i:css.index("}", i)]
        assert "align-items:start" not in dong, (
            f"`{lop[:-1]}` còn `align-items:start`: ba khối cao thấp so le làm cả hàng trông như "
            "chưa dựng xong — đúng chữ anh Tuấn dùng, 'chưa cân xứng'."
        )
        assert "align-items:stretch" in dong, f"`{lop[:-1]}` phải khai rõ `align-items:stretch`."


def test_ghi_lai_ca_hai_ve_cua_luat_bi_dao():
    """Luật TC-42 bị đảo thì phải để lại dấu vết, không lặng lẽ sửa.

    Bài học TC-49: một luật bị đảo mà không ghi lý do cũ thì vòng sau có người khôi phục nó lại,
    tưởng đang sửa một thiếu sót.
    """
    css = _doc(CSS)
    i = css.index(".mh01-sau-o{")
    trich = css[max(0, i - 1800):i]
    assert "align-items:start" in trich and "TC-42" in trich, (
        "Phải ghi lại lý lẽ cũ của TC-42 ngay cạnh chỗ đảo nó."
    )
    assert "cân xứng" in trich, "Phải ghi lại lý do đảo, bằng chính chữ anh Tuấn dùng."
