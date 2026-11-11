# -*- coding: utf-8 -*-
"""GD-1 · BỀ NGANG KHUNG NỘI DUNG, VÀ NHÃN BIỂU ĐỒ KHÔNG ĐƯỢC ĐẨY TRANG TRÀN NGANG — 12/11/2026.

VÌ SAO CÓ VÒNG NÀY. Anh Tuấn: «mở rộng chiều ngang, khoảng trống bên phải đang quá lớn». Đo trên
chính máy anh trước khi sửa: cửa sổ 1920px · thanh dọc 331px · khung nội dung 1180px · TRỐNG BÊN
PHẢI 409px. Hai dòng CSS gây ra: `main{max-width:1180px}` đặt trần cứng, và `.shell main{margin:0}`
đè mất `margin:0 auto` nên trống dồn hết một bên thay vì chia đôi.

VÀ MỘT LỖI CÓ SẴN LỘ RA KHI NỚI. Nới xong trang TRÀN NGANG 16px: nhãn hiện-khi-rê-chuột của chấm
CUỐI trên biểu đồ đường căn giữa chấm, mà chấm cuối nay sát mép cửa sổ. Bề ngang 1180 chỉ giấu nó
đi. Nới rộng không tạo ra lỗi ấy — nên sửa nhãn, không phải thôi nới rộng.

PHÉP THỬ NÀY ĐỌC CSS BẰNG BỘ PHÂN TÍCH, KHÔNG DÒ CHUỖI. Dò chuỗi thì một luật viết sau đè lên mà
phép thử vẫn xanh — và trong CSS, AI ĐỨNG SAU LÀ AI THẮNG. Bộ dưới đây tách luật theo khối, biết
luật nào nằm trong `@media` nào, rồi mới hỏi «ở màn rộng thì luật nào thắng».

  gd1_1  khung trong vỏ ứng dụng không còn bị một con số px cứng chặn
  gd1_2  trần tính theo cỡ chữ, và rộng hơn trần cũ ở cỡ chữ gốc
  gd1_3  chỗ thừa chia đôi hai bên, không dồn một bên
  gd1_4  luật của vỏ đứng SAU luật chung — không thì nó không thắng
  gd1_5  điện thoại (≤900px) vẫn bỏ trần, không bị bóp
  gd1_6  nhãn chấm đầu và chấm cuối neo vào trong khung
  gd1_7  chấm GIỮA vẫn căn giữa — sửa hai đầu, không phá luật gốc
  gd1_8  màn hình gắn đúng lớp `dau`/`cuoi` cho chấm đầu và chấm cuối
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent.parent / "web"
CSS = GOC / "app" / "globals.css"
TSX = GOC / "components" / "BieuDo.tsx"

TRAN_CU = 1180          # con số cũ, giữ ở đây để nói «phải rộng hơn cái này»
NGUONG_NGAN_KEO = 900   # trùng NGUONG_NGAN_KEO trong Shell.tsx


def _bo_ghi_chu(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def doc_luat(duong: pathlib.Path):
    """Tách CSS thành danh sách luật: (thu_tu, dieu_kien_media, bo_chon, phan_khai).

    `dieu_kien_media` là chuỗi rỗng khi luật nằm ngoài mọi `@media`. Bộ này KHÔNG phải một bộ
    phân tích CSS đầy đủ — nó chỉ cần đúng với cách tệp này được viết: `@media` một tầng, không
    lồng nhau. `gd1_0` canh đúng giả thiết ấy.
    """
    s = _bo_ghi_chu(duong.read_text(encoding="utf-8"))
    luat, i, thu_tu, media = [], 0, 0, ""
    dau = 0
    while i < len(s):
        c = s[i]
        if c == "{":
            dau_de = s[dau:i].strip()
            than_dau = i + 1
            sau = 1
            j = than_dau
            while j < len(s) and sau:
                if s[j] == "{":
                    sau += 1
                elif s[j] == "}":
                    sau -= 1
                j += 1
            than = s[than_dau:j - 1]
            if dau_de.startswith("@"):
                if "{" in than:                      # khối lồng: đi vào trong
                    cu = media
                    media = dau_de
                    for t in doc_luat_chuoi(than, thu_tu, media):
                        luat.append(t)
                        thu_tu = t[0] + 1
                    media = cu
            else:
                luat.append((thu_tu, media, dau_de, than))
                thu_tu += 1
            i = j
            dau = i
        else:
            i += 1
    return luat


def doc_luat_chuoi(than: str, thu_tu0: int, media: str):
    ra, i, dau, thu_tu = [], 0, 0, thu_tu0
    while i < len(than):
        if than[i] == "{":
            bo_chon = than[dau:i].strip()
            j, sau = i + 1, 1
            while j < len(than) and sau:
                if than[j] == "{":
                    sau += 1
                elif than[j] == "}":
                    sau -= 1
                j += 1
            ra.append((thu_tu, media, bo_chon, than[i + 1:j - 1]))
            thu_tu += 1
            i = j
            dau = i
        else:
            i += 1
    return ra


def khai(phan: str, ten: str):
    """Giá trị CUỐI CÙNG của một thuộc tính trong một khai báo (khai sau đè khai trước)."""
    gt = None
    for mau in phan.split(";"):
        if ":" not in mau:
            continue
        k, v = mau.split(":", 1)
        if k.strip() == ten:
            gt = v.strip()
    return gt


def tran_tren_man_rong():
    """Luật `.shell main` THẮNG ở màn rộng: luật cuối cùng, bỏ qua các `@media` màn hẹp."""
    ra = None
    for thu_tu, media, bo_chon, phan in doc_luat(CSS):
        if not any(b.strip() == ".shell main" for b in bo_chon.split(",")):
            continue
        if media:
            m = re.search(r"max-width\s*:\s*(\d+)", media)
            if m and int(m.group(1)) <= NGUONG_NGAN_KEO:
                continue                              # luật của màn hẹp, không tính
        ra = (thu_tu, media, phan)
    return ra


LUAT = doc_luat(CSS)


def test_gd1_0_bo_doc_css_doc_duoc_tep_nay():
    """Phép thử dưới chỉ đáng tin nếu bộ đọc đọc được thật. Neo vào ba luật đã biết chắc."""
    bo_chon = [b for _, _, b, _ in LUAT]
    assert any(b == "main" for b in bo_chon), "không tách được luật `main`"
    assert any(".shell main" in b for b in bo_chon), "không tách được luật `.shell main`"
    assert len(LUAT) > 300, f"tách được quá ít luật ({len(LUAT)}) — bộ đọc đang hỏng"


def test_gd1_1_khung_trong_vo_khong_con_bi_so_px_cung_chan():
    t = tran_tren_man_rong()
    assert t, "không tìm thấy luật `.shell main` nào ở màn rộng"
    _, _, phan = t
    mw = khai(phan, "max-width")
    assert mw, "`.shell main` không khai `max-width` → nó ăn theo `main{max-width:1180px}`"
    assert not re.fullmatch(r"\d+px", mw), \
        f"trần vẫn là một con số px cứng ({mw}) — phóng to cỡ chữ là khung lại chật"


def test_gd1_2_tran_tinh_theo_co_chu_va_rong_hon_tran_cu():
    _, _, phan = tran_tren_man_rong()
    mw = khai(phan, "max-width")
    assert "rem" in mw, f"trần không theo cỡ chữ: {mw}"
    m = re.search(r"calc\(\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*\*\s*1rem\s*\)", mw)
    assert m, f"không đọc được trần: {mw}"
    o_co_goc = float(m.group(1)) / float(m.group(2)) * 14      # quy về cỡ chữ 14px
    assert o_co_goc > TRAN_CU, \
        f"trần mới {o_co_goc:.0f}px ở cỡ chữ gốc — KHÔNG rộng hơn trần cũ {TRAN_CU}px"


def test_gd1_3_cho_thua_chia_doi_hai_ben():
    """Trần mà dồn hết chỗ thừa sang một bên thì trên màn siêu rộng vẫn lệch — đúng cái anh Tuấn
    nhìn thấy. `margin:0` là thứ đã lấy mất phần căn giữa của `main{margin:0 auto}`."""
    _, _, phan = tran_tren_man_rong()
    mi = khai(phan, "margin-inline") or ""
    mg = khai(phan, "margin") or ""
    assert "auto" in mi or re.search(r"\bauto\b", mg), \
        f"không căn giữa: margin-inline={mi!r} margin={mg!r}"
    assert khai(phan, "margin") != "0", "`margin:0` đè mất phần căn giữa"


def test_gd1_4_luat_cua_vo_dung_sau_luat_chung():
    """Trong CSS ai đứng sau người ấy thắng (cùng độ cụ thể thì theo thứ tự). `.shell main` cụ thể
    hơn `main` nên vẫn thắng, nhưng đặt nó TRƯỚC là dựng một cái bẫy cho người sửa sau."""
    chung = [t for t, md, b, _ in LUAT if b == "main" and not md]
    assert chung, "không thấy luật `main` chung"
    thu_tu_vo = tran_tren_man_rong()[0]
    assert thu_tu_vo > min(chung), "luật của vỏ đứng TRƯỚC luật chung"


def test_gd1_5_dien_thoai_van_bo_tran():
    """Dưới 900px thanh dọc xếp thành ngăn kéo nằm ngang, `main` chiếm trọn — có trần ở đó là bóp
    màn hình điện thoại cho hẹp lại mà chẳng vì cái gì."""
    thay = False
    for _, media, bo_chon, phan in LUAT:
        if ".shell main" not in bo_chon or not media:
            continue
        m = re.search(r"max-width\s*:\s*(\d+)", media)
        if m and int(m.group(1)) <= NGUONG_NGAN_KEO and khai(phan, "max-width") == "none":
            thay = True
    assert thay, f"≤{NGUONG_NGAN_KEO}px không còn luật bỏ trần cho `.shell main`"


@pytest.mark.parametrize("lop,neo", [("dau", "left"), ("cuoi", "right")])
def test_gd1_6_nhan_cham_dau_va_cuoi_neo_vao_trong_khung(lop, neo):
    thay = None
    for _, media, bo_chon, phan in LUAT:
        if f".bd-cham.{lop} .bd-cham-so" in bo_chon and not media:
            thay = phan
    assert thay, f"không có luật neo nhãn cho chấm «{lop}» — nhãn vẫn thò ra ngoài khung"
    assert khai(thay, "transform") == "none", \
        "còn `transform` căn giữa thì nhãn vẫn bị kéo lệch nửa bề rộng ra ngoài"
    assert khai(thay, neo) == "0", f"nhãn chấm «{lop}» phải neo vào mép {neo} của chấm"


def test_gd1_7_cham_giua_van_can_giua():
    """Sửa hai đầu, KHÔNG phá luật gốc: ba chục chấm ở giữa vẫn phải có nhãn căn giữa."""
    goc = None
    for _, media, bo_chon, phan in LUAT:
        if bo_chon.strip() == ".bd-cham-so" and not media:
            goc = phan
    assert goc, "mất luật gốc của nhãn chấm"
    assert "translateX(-50%)" in (khai(goc, "transform") or ""), \
        "chấm giữa không còn căn giữa — nhãn lệch khỏi chấm nó đang nói về"


def test_gd1_8_man_hinh_gan_dung_lop_cho_cham_dau_va_cham_cuoi():
    """CSS có luật mà màn hình không gắn lớp thì luật ấy không bao giờ chạy — và phép thử CSS ở
    trên vẫn xanh. Đây là chỗ nối giữa hai bên."""
    s = TSX.read_text(encoding="utf-8")
    kh = re.search(r'"bd-cham "\s*\+\s*d\.lop\s*\+?([^\n]*(?:\n[^\n]*){0,3})', s)
    assert kh, "không tìm thấy chỗ dựng lớp cho chấm"
    doan = kh.group(0)
    assert '" dau"' in doan and '" cuoi"' in doan, f"chưa gắn lớp dau/cuoi: {doan!r}"
    assert "i === 0" in doan, "lớp «dau» không gắn theo chấm ĐẦU"
    assert re.search(r"i\s*===\s*d\.diem\.length\s*-\s*1", doan), \
        "lớp «cuoi» không gắn theo chấm CUỐI"
