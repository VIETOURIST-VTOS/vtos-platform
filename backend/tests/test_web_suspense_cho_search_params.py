# -*- coding: utf-8 -*-
"""MÀN HÌNH ĐỌC THAM SỐ ĐƯỜNG DẪN THÌ PHẢI BỌC `Suspense` — 11/10/2026.

──────────────────────────────────────────────────────────────────────────────────────────────
LUẬT NÀY TỪ ĐÂU RA
──────────────────────────────────────────────────────────────────────────────────────────────

Next bắt buộc: thành phần nào gọi `useSearchParams()` phải nằm trong một ranh giới `Suspense`,
không thì `npm run build` DỪNG ở đúng trang ấy. Đây không phải lời khuyên về phong cách — nó là
lỗi dựng bản, và nó chỉ lộ ra ở việc `web` trên PR, sau khi người viết đã nghĩ là mình xong.

Sáu màn hình trong kho đã viết đúng hình ấy từ trước (bookings · tours · doi-xe · requests ·
sales-reports · kinh-doanh-le). Nhưng đó là SÁU LẦN NHỚ, không phải một luật: người thứ bảy
không có cách nào biết, vì không chỗ nào nói ra. Vòng 11/10/2026 là người thứ bảy, và đã viết
thiếu đúng chỗ ấy — bắt được lúc tự soát, không phải nhờ hàng rào nào. Nên dựng hàng rào.

VÌ SAO KHÔNG ĐỂ VIỆC `web` LO. Việc ấy có bắt thật, nhưng nó chỉ chạy trên PR và nằm sau một
lượt `npm ci` — tới lúc nó nói thì người viết đã chuyển sang việc khác. Phép thử này trả lời
trong một phần giây, ngay trên máy, lúc còn đang sửa.

CHỈ SOI TỆP TRANG, CỐ Ý: `Suspense` phải bọc ở nơi dựng cây màn hình. Một thành phần dùng chung
gọi `useSearchParams` thì chính trang nhập nó mới là chỗ bọc được, nên trang là chỗ đúng để hỏi.

──────────────────────────────────────────────────────────────────────────────────────────────
VÀ LUẬT CHỈ ÁP CHO ĐƯỜNG DẪN TĨNH — ĐÂY LÀ MỘT PHÉP ĐO, KHÔNG PHẢI MỘT NGOẠI LỆ CHO TIỆN
──────────────────────────────────────────────────────────────────────────────────────────────

Bản đầu của tệp này đòi MỌI trang phải bọc, và nó đỏ ngay lần chạy đầu ở
`app/tours/[id]/page.tsx` — một trang đang nằm trên main, với nhịp `web` xanh. Nghĩa là luật
viết rộng hơn sự thật; gộp nguyên như thế là tự tay làm main đỏ.

Đo lại thì hình rõ hẳn: bảy trang dùng `useSearchParams`, sáu trang TĨNH đều bọc, một trang
ĐƯỜNG DẪN ĐỘNG không bọc. Và kho KHÔNG có một `generateStaticParams` nào, nên nhánh động không
bị dựng sẵn — không dựng sẵn thì Next không đòi ranh giới.

Nên luật loại nhánh động ra. Điều kiện làm luật ấy hết đúng được ghi ngay đây, và ĐO ĐƯỢC: ngày
nào có `generateStaticParams`, nhánh động bị dựng sẵn và phải bọc như mọi trang khác. Phép thử
thứ ba dưới đây canh đúng điều kiện ấy, nên không ai phải nhớ.
"""
from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"


def _ma(src: str) -> str:
    """Bỏ chú thích: một dòng chú thích nhắc tên `Suspense` không phải là bọc `Suspense`."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _la_duong_dan_dong(p: Path) -> bool:
    """Nhánh có `[tham_so]` ở bất kỳ cấp nào — Next dựng theo yêu cầu, không dựng sẵn."""
    return any(x.startswith("[") for x in p.relative_to(WEB / "app").parts)


def test_trang_TINH_dung_useSearchParams_deu_boc_Suspense():
    thieu = []
    for p in sorted(WEB.glob("app/**/page.tsx")):
        src = _ma(p.read_text(encoding="utf-8"))
        if "useSearchParams" not in src or _la_duong_dan_dong(p):
            continue
        if "Suspense" not in src:
            thieu.append(str(p.relative_to(WEB)).replace("\\", "/"))
    assert not thieu, (
        "Các trang sau gọi `useSearchParams` mà không bọc `Suspense`: " + ", ".join(thieu) +
        ". Next sẽ làm `npm run build` chết ở đúng những trang này. Cách sửa đúng một dòng, "
        'theo hình sáu màn hình đã có: `export default function Page() { return '
        "<Shell><Suspense><X /></Suspense></Shell>; }`.")


def test_hang_rao_nay_bat_duoc_ban_thieu():
    """Tự kiểm: đưa một trang thiếu Suspense vào thì phép thử trên PHẢI thấy.

    Không có dòng này thì hàng rào trên có thể đang xanh vì KHÔNG TÌM THẤY TỆP NÀO — ví dụ đường
    dẫn `WEB` sai sau một lần dọn thư mục — và một hàng rào quét trúng tập rỗng thì luôn xanh.
    """
    gia = '"use client";\nimport { useSearchParams } from "next/navigation";\n'
    assert "useSearchParams" in _ma(gia) and "Suspense" not in _ma(gia)
    co_that = [p for p in WEB.glob("app/**/page.tsx") if "useSearchParams" in _ma(p.read_text(encoding="utf-8"))]
    assert len(co_that) >= 6, (
        f"chỉ thấy {len(co_that)} trang dùng useSearchParams — nghi là đường dẫn quét sai, "
        "vì một hàng rào quét trúng tập rỗng thì luôn xanh")


def test_khong_co_generateStaticParams_nao_lam_nhanh_dong_bi_dung_san():
    """Điều kiện khiến luật trên hẹp lại — canh nó, thay vì bắt người sau phải nhớ.

    Nhánh động được MIỄN bọc `Suspense` chỉ vì nó không bị dựng sẵn. Thêm `generateStaticParams`
    là nhánh ấy bị dựng sẵn, và từ giây đó nó phải bọc y như trang tĩnh — nếu không `npm run
    build` chết. Phép thử này đỏ đúng lúc điều kiện đổi, và nói thẳng phải làm gì.
    """
    co = []
    for p in sorted(WEB.glob("app/**/page.tsx")):
        if not _la_duong_dan_dong(p):
            continue
        src = _ma(p.read_text(encoding="utf-8"))
        if "generateStaticParams" in src and "useSearchParams" in src and "Suspense" not in src:
            co.append(str(p.relative_to(WEB)).replace("\\", "/"))
    assert not co, (
        "Các nhánh động sau nay CÓ `generateStaticParams`, nghĩa là bị dựng sẵn, mà vẫn gọi "
        "`useSearchParams` không bọc `Suspense`: " + ", ".join(co) + ". Bọc lại, hoặc bỏ "
        "`generateStaticParams` đi.")


# ── Đợt PH-1 · 09/11/2026 — BỊT MỘT LỖ THỦNG CHÍNH ĐỢT NÀY TẠO RA ────────────────────────────
#
# Phép thử đầu tệp chỉ soi TỆP TRANG: nó tìm chữ `useSearchParams` ngay trong `page.tsx`. Lời
# giải thích đi kèm nói rõ vì sao — `Suspense` phải bọc ở nơi dựng cây màn hình, nên trang là chỗ
# đúng để hỏi. Câu ấy vẫn đúng. Nhưng nó ngầm giả định một điều khác: rằng trang nào cần bọc thì
# chính trang ấy gọi hook.
#
# Đợt PH-1 làm giả định đó sai. Năm trang `/fit`, `/mice`, `/op`, `/xe`, `/guide` không gọi
# `useSearchParams` dòng nào — chúng gọi `components/TrangPhanHe`, và HOOK NẰM TRONG ĐÓ. Phép thử
# đầu tệp bỏ qua cả năm, và nó XANH mà không hề kiểm bài. Nếu em quên bọc một trang trong năm
# trang ấy thì không có gì đỏ, chỉ có `npm run build` chết — mà build thì chạy muộn hơn nhiều.
#
# Phép thử dưới đây đi THEO MỘT BƯỚC NHẬP: trang nhập thành phần nào thì đọc luôn mã thành phần
# ấy. Đúng khuôn `test_man_hinh_co_cua_nhap._ma_cua_man_hinh` đã làm từ 11/10/2026, và cùng một
# lý do: "một màn hình dọn mã sang thành phần sẽ TRÔNG NHƯ không đọc, không ghi gì cả".
#
# MỘT BƯỚC LÀ ĐỦ, không đệ quy: đi sâu nữa thì gần như mọi trang đều chạm tới một thành phần nào
# đó có hook, và phép thử hoá ra bắt cả những trang không liên quan. Một bước bắt đúng hình mà
# đợt này tạo ra — trang mỏng gọi thẳng một thành phần mang hook.


def _thanh_phan_nhap(src: str) -> list[Path]:
    """Các tệp `@/components/...` mà một trang nhập vào. Chỉ một bước, không đi tiếp."""
    ra = []
    for ten in re.findall(r'from\s+"@/components/([A-Za-z0-9_/]+)"', src):
        for duoi in (".tsx", ".ts"):
            f = WEB / "components" / (ten + duoi)
            if f.exists():
                ra.append(f)
                break
    return ra


def test_trang_TINH_goi_hook_QUA_THANH_PHAN_cung_phai_boc_Suspense():
    """Trang không tự gọi hook, nhưng thành phần nó nhập thì có — vẫn phải bọc.

    Bẻ ngược: bỏ `Suspense` khỏi `web/app/fit/page.tsx` thì phép thử này ĐỎ, trong khi phép thử
    đầu tệp vẫn xanh. Đó chính là lỗ thủng nó bịt.
    """
    thieu = []
    for p in sorted(WEB.glob("app/**/page.tsx")):
        src = _ma(p.read_text(encoding="utf-8"))
        if _la_duong_dan_dong(p) or "useSearchParams" in src or "Suspense" in src:
            continue
        for tp in _thanh_phan_nhap(src):
            if "useSearchParams" in _ma(tp.read_text(encoding="utf-8")):
                thieu.append(f"{p.relative_to(WEB)} (qua {tp.name})".replace("\\", "/"))
                break
    assert not thieu, (
        "Các trang sau KHÔNG tự gọi `useSearchParams`, nhưng thành phần chúng nhập thì có — và "
        "chúng không bọc `Suspense`: " + ", ".join(thieu) + ". Next dựng sẵn trang tĩnh, nên "
        "`npm run build` sẽ chết ở đúng những trang này. Bọc như năm trang phân hệ: "
        "`<Shell><Suspense fallback={...}><X /></Suspense></Shell>`.")


def test_hang_rao_theo_thanh_phan_that_su_nhin_thay_gi_do():
    """Tự kiểm, cùng hình với `test_hang_rao_nay_bat_duoc_ban_thieu` ở trên.

    Nếu cách đọc nhập hỏng thì `_thanh_phan_nhap` trả về rỗng ở mọi trang, phép thử trên không
    bao giờ đỏ, và cả hai cùng xanh suốt đời. Chốt một sàn để chỗ ấy không im lặng.
    """
    co = [p for p in WEB.glob("app/**/page.tsx")
          if _thanh_phan_nhap(_ma(p.read_text(encoding="utf-8")))]
    assert len(co) >= 20, (
        f"chỉ thấy {len(co)} trang nhập thành phần dùng chung — nghi là cách đọc dòng `import` "
        "đã hỏng, chứ không phải kho chỉ có bằng ấy.")
