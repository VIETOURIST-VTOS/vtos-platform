# -*- coding: utf-8 -*-
"""TM-1 · TÁCH MÀN /lenh-dieu-xe THÀNH SÁU MÀN — 17/10/2026 (Chủ tịch duyệt bản xem thử 16/10/2026).

Màn cũ gánh 13 khối và 41 biến trạng thái trên một trang. Bảng tách Chủ tịch duyệt:

    /lenh-dieu-xe                 màn chính — lệnh đã lập          còn thanh dọc
    /lenh-dieu-xe/de-nghi         khối 1–5 — đề nghị đang chờ      còn thanh dọc
    /lenh-dieu-xe/lap-lenh        khối 8–12 — tìm phương án, chốt  còn thanh dọc
    /lenh-dieu-xe/de-nghi/moi     khối 6 — Điều hành đề nghị xe    TOÀN MÀN
    /lenh-dieu-xe/chua-nhan       khối 7 — tài xế chưa nhận        TOÀN MÀN
    /lenh-dieu-xe?ma=<id>         một lệnh                         TOÀN MÀN

Bốn luật Chủ tịch chốt cho thanh việc, và mỗi luật có một phép thử dưới đây — vì ba lần trước
chính phiên làm việc đã đoán sai, và một luật chỉ nằm trong trí nhớ thì lần thứ tư sẽ lại sai:

  TM1  sáu màn có thật, và trang con được khai (ALL_MENU_PATHS + danh sách cho phép của gd_doi_xe)
  TM2  màn nào toàn màn thì toàn màn, màn nào còn thanh dọc thì còn
  TM3  nút trên thanh việc mở TAB MỚI — trừ «‹ Lên một cấp», đi trong cùng tab
  TM4  trạng thái mẫu lập lệnh nằm TRÊN ĐƯỜNG DẪN — thiếu thì tab mới mở ra trống
  TM5  màn nào GHI thì phải báo cho tab khác (dải băng «Đã có thay đổi»)

Mỗi phép đều có bản tự phá ở cuối tệp: một hàng rào không đỏ được là một hàng rào rỗng.
"""
from __future__ import annotations
import re
from pathlib import Path

from app.services import access as AC

GOC = Path(__file__).resolve().parents[2]
WEB = GOC / "web"
LDX = WEB / "app" / "lenh-dieu-xe"

TRANG = {
    "/lenh-dieu-xe": LDX / "page.tsx",
    "/lenh-dieu-xe/de-nghi": LDX / "de-nghi" / "page.tsx",
    "/lenh-dieu-xe/lap-lenh": LDX / "lap-lenh" / "page.tsx",
    "/lenh-dieu-xe/de-nghi/moi": LDX / "de-nghi" / "moi" / "page.tsx",
    "/lenh-dieu-xe/chua-nhan": LDX / "chua-nhan" / "page.tsx",
}
TOAN_MAN = {"/lenh-dieu-xe/de-nghi/moi", "/lenh-dieu-xe/chua-nhan"}
CON_THANH_DOC = {"/lenh-dieu-xe/de-nghi", "/lenh-dieu-xe/lap-lenh"}
THAM_SO_LAP_LENH = ("tu", "den", "khach", "km", "tour", "rate", "de_nghi")
GOI_GHI = re.compile(r'method:\s*"(POST|PUT|DELETE)"')


def _ma(src: str) -> str:
    """Bỏ chú thích: một chú thích nhắc tên `toanMan` không phải là bật toàn màn."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"\{\s*/\*.*?\*/\s*\}", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _doc(duong: str) -> str:
    return _ma(TRANG[duong].read_text(encoding="utf-8"))


def _co_web() -> bool:
    return LDX.exists()


# ── TM1 ──────────────────────────────────────────────────────────────────────────────────────
def test_tm1_sau_man_co_that_va_trang_con_duoc_khai():
    if not _co_web():
        return
    thieu = [d for d, p in TRANG.items() if not p.exists()]
    assert not thieu, f"thiếu màn: {thieu}"
    # Trang con phải nằm trong ALL_MENU_PATHS (test_ai_log canh chung) VÀ trong danh sách cho phép
    # của gd_doi_xe: ông là người duy nhất chốt lệnh, mà danh sách ẩn lại gọi tên màn lập lệnh
    # của ông thì màn hình nào đọc danh sách ấy cũng sẽ giấu nó đi.
    for p in sorted(LDX.glob("*/**/page.tsx")):
        duong = "/" + p.parent.relative_to(WEB / "app").as_posix()
        assert duong in AC.ALL_MENU_PATHS, f"{duong} chưa khai trong ALL_MENU_PATHS"
        assert duong in AC.RESTRICTED_ROLE_MENUS["gd_doi_xe"], (
            f"{duong} không có trong danh sách cho phép của gd_doi_xe — người chốt lệnh bị ẩn mất màn của mình")
    # Màn một lệnh và bốn việc của nó là trạng thái trên đường dẫn, KHÔNG phải thư mục trang thứ bảy.
    chinh = _doc("/lenh-dieu-xe")
    assert 'q.get("ma")' in chinh, "màn chính không còn đọc `?ma=` — màn một lệnh mất đường vào"
    for v in ("doi-xe", "doi-tai-xe", "dong-lenh", "xoa-lenh"):
        assert f'"{v}"' in chinh, f"màn một lệnh thiếu việc `{v}`"


# ── TM2 ──────────────────────────────────────────────────────────────────────────────────────
def test_tm2_toan_man_dung_cho():
    if not _co_web():
        return
    for d in TOAN_MAN:
        assert re.search(r"<ThanhViec\b[^>]*\btoanMan\b", _doc(d)), f"{d} phải là màn TOÀN MÀN"
    for d in CON_THANH_DOC:
        assert not re.search(r"\btoanMan\b", _doc(d)), f"{d} phải GIỮ thanh dọc"
    # Màn chính: danh sách giữ thanh dọc, màn một lệnh thì toàn màn — cả hai ở cùng tệp.
    chinh = _doc("/lenh-dieu-xe")
    ds = chinh[chinh.index("function DanhSach"):chinh.index("function MotLenh")]
    mot = chinh[chinh.index("function MotLenh"):]
    assert "<ThanhViec" in ds and not re.search(r"\btoanMan\b", ds), "danh sách lệnh phải giữ thanh dọc"
    assert re.search(r"<ThanhViec\b[^>]*\btoanMan\b", mot), "màn một lệnh phải là TOÀN MÀN"
    # Toàn màn thật sự giấu thanh dọc — không phải chỉ đổi tên một biến.
    tv = _ma((WEB / "components" / "ThanhViec.tsx").read_text(encoding="utf-8"))
    assert re.search(r"aside\.side\{display:none", tv), "chế độ toàn màn không còn giấu thanh dọc"


# ── TM3 ──────────────────────────────────────────────────────────────────────────────────────
def test_tm3_nut_thanh_viec_mo_tab_moi():
    if not _co_web():
        return
    tv = _ma((WEB / "components" / "ThanhViec.tsx").read_text(encoding="utf-8"))
    # Một chỗ duy nhất quyết chuyện mở tab: nút không phải `len` thì có target _blank.
    assert re.search(r'v\.len\s*\?\s*\{\}\s*:\s*\{\s*target:\s*"_blank"', tv), (
        "nút thanh việc không còn mở tab mới — Chủ tịch chọn tab mới, không phải cửa sổ nổi")
    # Đường vào màn một lệnh và «Lấy vào mẫu» cũng mở tab mới.
    assert re.search(r'href=\{`/lenh-dieu-xe\?ma=\$\{d\.id\}`\}\s*target="_blank"', _doc("/lenh-dieu-xe"))
    assert re.search(r'target="_blank"[^>]*\s+href=\{`/lenh-dieu-xe/lap-lenh\?de_nghi=', _doc("/lenh-dieu-xe/de-nghi"))


# ── TM4 ──────────────────────────────────────────────────────────────────────────────────────
def test_tm4_trang_thai_lap_lenh_nam_tren_duong_dan():
    if not _co_web():
        return
    src = _doc("/lenh-dieu-xe/lap-lenh")
    m = re.search(r"ghiUrl\(\{([^}]*)\}\)", src)
    assert m, "màn lập lệnh không ghi trạng thái lên đường dẫn"
    ghi = m.group(1)
    thieu_ghi = [k for k in THAM_SO_LAP_LENH if not re.search(rf"\b{k}\b", ghi)]
    thieu_doc = [k for k in THAM_SO_LAP_LENH if f'q.get("{k}")' not in src]
    assert not thieu_ghi and not thieu_doc, (
        f"tham số không đi qua đường dẫn — ghi thiếu {thieu_ghi}, đọc thiếu {thieu_doc}. "
        "Tab mới mở ra sẽ không dựng lại được mẫu đang lập.")


# ── TM5 ──────────────────────────────────────────────────────────────────────────────────────
def test_tm5_man_nao_ghi_thi_bao_cho_tab_khac():
    if not _co_web():
        return
    im_lang = []
    for d in TRANG:
        src = _doc(d)
        # Màn lập lệnh ghi bằng fetch POST /api/v1/dispatch, các màn khác bằng api(..., {method}).
        ghi = GOI_GHI.search(src) or re.search(r'fetch\("/api/v1/dispatch",\s*\{\s*method:\s*"POST"', src)
        if ghi and "baoDaDoi(" not in src:
            im_lang.append(d)
    assert not im_lang, (
        f"{im_lang} ghi dữ liệu mà không báo cho tab khác — tab danh sách sẽ hiện số cũ im lặng.")


# ── TỰ PHÁ: mỗi phép trên phải đỏ được ─────────────────────────────────────────────────────────
def test_tm_tu_pha():
    if not _co_web():
        return
    lap = _doc("/lenh-dieu-xe/lap-lenh")
    # TM4: bỏ `rate` khỏi lượt ghi đường dẫn → phải bắt được.
    hong = re.sub(r"(ghiUrl\(\{[^}]*?)\brate\b,?", r"\1", lap, count=1)
    m = re.search(r"ghiUrl\(\{([^}]*)\}\)", hong)
    assert m and not re.search(r"\brate\b", m.group(1)), "bản tự phá TM4 không phá được"
    # TM2: bật toanMan trên màn lập lệnh → phải bắt được.
    assert re.search(r"\btoanMan\b", lap.replace("<ThanhViec ", "<ThanhViec toanMan ", 1))
    # TM5: bỏ baoDaDoi khỏi màn đề nghị → màn ấy vẫn có lời ghi, nên phải bị gọi tên.
    dn = _doc("/lenh-dieu-xe/de-nghi").replace("baoDaDoi(", "khongBao(")
    assert GOI_GHI.search(dn) and "baoDaDoi(" not in dn
    # Chú thích không được tính: một chú thích nhắc `toanMan` không làm màn thành toàn màn.
    assert not re.search(r"\btoanMan\b", _ma("/* toanMan */ <ThanhViec viec={[]} />"))
