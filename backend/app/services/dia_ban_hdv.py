# -*- coding: utf-8 -*-
"""ĐỢT HDV-1 (làn R2) — NHỊP 1: ĐO NỀN ĐỊA BÀN HƯỚNG DẪN VIÊN. KHÔNG SỬA MỘT DÒNG DỮ LIỆU NÀO.

VÌ SAO ĐO TRƯỚC. Hệ thống chưa nối chuyến về địa bàn. Hệ quả đã phải trả: Đợt HD-14 phải TẮT khoá
tuyến trong hồ sơ hướng dẫn viên, và màn duyệt nhận xét phải lùi nhãn về chỉ còn tháng. Nhịp 2 —
nối chuyến về địa bàn và bật `CO_TRUONG_TUYEN` — chỉ bắt đầu khi nhịp 1 qua cổng.

CHUỖI DỮ LIỆU, đọc được trên mã ngày 22/10/2026:

    guide_assignments.tour_id ──► tours.product_id   ──► products.id   ──► products.region
                              └──► tours.product_code ──► products.code ──┘
    guide_assignments.guide_id ─► employees.id

HAI KHOÁ, KHÔNG PHẢI MỘT — và đây là chỗ bản đầu của phép đo này suýt báo thiếu. Robot Vietrip
(`services/vietrip.py:138`) LUÔN ghi `tours.product_code`, còn `tours.product_id` chỉ được điền
khi tìm thấy một `Product` có mã khớp (`:169`, `:381`). Đo bằng mỗi `product_id` là bỏ sót đúng
những chuyến mà sản phẩm chưa kịp dựng — tức là báo độ phủ THẤP HƠN sự thật, và nhịp 2 bị chặn oan.

Nên phép đo nối theo `product_id` TRƯỚC, không có thì rơi sang `product_code`, và BÁO RIÊNG từng
đường để người đọc biết nền đang dựa vào khoá nào.

`tours.product_id` cho phép rỗng, `tours.product_code` mặc định rỗng, và `products.region` mặc
định là chuỗi rỗng. Ba chỗ rỗng ấy chính là thứ phép đo này đếm.

HAI CON SỐ, và cổng 95% Chủ tịch đặt:
  (1) ĐỘ PHỦ CHUYẾN  — trong các chuyến ĐÃ CHẠY, bao nhiêu phần trăm nối được về một địa bàn.
  (2) ĐỘ PHỦ NGƯỜI   — bao nhiêu phần trăm hướng dẫn viên có ĐỦ SỐ CHUYẾN để kết luận địa bàn.

════════════════════════════════════════════════════════════════════════════════════════════
HAI CON SỐ CHỐT TRƯỚC KHI ĐO — ghi ra đây lúc 22/10/2026, TRƯỚC khi chạy phép đo lần nào.
Chốt sau khi nhìn số là chọn ngưỡng cho vừa dữ liệu, và lúc ấy phép đo không còn nói gì.

  · CỔNG = 95%      — Chủ tịch đặt. ĐIỀU CẤM: dưới 95% thì BÁO LẠI, tuyệt đối không hạ cổng.
                      `test_hd13` ghim con số này; hạ xuống 50% là ĐỎ.
  · ĐỦ = 5 chuyến   — Chủ tịch để làn tự quyết (22/10/2026). Chọn 5 vì: 3 chuyến cùng một miền
                      vẫn có thể là ngẫu nhiên của lịch phân công, còn 10 thì loại gần hết hướng
                      dẫn viên thời vụ — mà chính họ là nhóm cần biết địa bàn nhất khi xếp lịch.
════════════════════════════════════════════════════════════════════════════════════════════

"ĐỦ SỐ CHUYẾN" ĐẾM CHUYẾN NỐI ĐƯỢC VỀ ĐỊA BÀN, không đếm mọi chuyến. Một người có 20 chuyến mà
cả 20 đều không có `region` thì vẫn KHÔNG kết luận được địa bàn của người ấy — đếm họ là "đủ" thì
con số thứ hai nói dối theo đúng chiều dễ chịu.

CHỈ ĐỌC. Hàm trong tệp này không `add`, không `commit`, không đổi một ô nào. `test_hd13` canh.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Product, Tour
from app.models.hr import GuideAssignment

CONG = 95.0          # phần trăm. Chủ tịch đặt. ĐỪNG hạ.
NGUONG_CHUYEN = 5    # "đủ số chuyến để kết luận". Chốt 22/10/2026, trước khi đo.


def _phan_tram(tu: int, mau: int) -> float | None:
    """Mẫu bằng 0 trả None, KHÔNG trả 0,0. Không có chuyến nào thì độ phủ là CHƯA ĐO ĐƯỢC,
    còn 0,0% đọc ra là "đo rồi, phủ bằng không" — hai câu khác hẳn nhau."""
    return round(tu * 100 / mau, 1) if mau else None


def dia_ban_cua_chuyen(db: Session, den_ngay: date | None = None) -> dict[int, tuple[str, str]]:
    """{tour_id: (địa bàn, nối bằng khoá nào)} cho các chuyến ĐÃ CHẠY.

    Chuyến không nối được vẫn có mặt với địa bàn rỗng — bỏ nó đi là mất mẫu số.
    "nối bằng khoá nào" là `id`, `code`, hoặc `` (không nối được): con số tổng không nói được
    nền đang dựa vào khoá nào, mà nhịp 2 cần đúng điều đó.
    """
    moc = den_ngay or date.today()
    theo_id = {pid: (r or "").strip() for pid, r in db.execute(select(Product.id, Product.region)).all()}
    theo_ma = {(c or "").strip(): (r or "").strip()
               for c, r in db.execute(select(Product.code, Product.region)).all() if (c or "").strip()}
    ra: dict[int, tuple[str, str]] = {}
    for tid, pid, ma in db.execute(
            select(Tour.id, Tour.product_id, Tour.product_code).where(Tour.end_date < moc)).all():
        vung = theo_id.get(pid, "") if pid is not None else ""
        if vung:
            ra[tid] = (vung, "id"); continue
        vung = theo_ma.get((ma or "").strip(), "")
        ra[tid] = (vung, "code") if vung else ("", "")
    return ra


def do_nen(db: Session, nguong_chuyen: int = NGUONG_CHUYEN,
           den_ngay: date | None = None) -> dict[str, Any]:
    """Hai con số của nhịp 1. CHỈ ĐỌC."""
    moc = den_ngay or date.today()
    cua_chuyen = dia_ban_cua_chuyen(db, moc)
    so_chuyen = len(cua_chuyen)
    chuyen_co_dia_ban = {t for t, (r, _) in cua_chuyen.items() if r}
    theo_khoa = Counter(k for _, k in cua_chuyen.values() if k)

    # Mỗi (người, chuyến) chỉ đếm một lần: một chuyến có thể phân công cùng người hai dòng.
    cap = {(gid, tid) for gid, tid in db.execute(
        select(GuideAssignment.guide_id, GuideAssignment.tour_id)).all()
        if tid in cua_chuyen}
    dem_co: Counter[int] = Counter()
    nguoi = set()
    for gid, tid in cap:
        nguoi.add(gid)
        if tid in chuyen_co_dia_ban:
            dem_co[gid] += 1
    du = {g for g in nguoi if dem_co[g] >= nguong_chuyen}

    phu_chuyen = _phan_tram(len(chuyen_co_dia_ban), so_chuyen)
    phu_nguoi = _phan_tram(len(du), len(nguoi))
    qua = (phu_chuyen is not None and phu_nguoi is not None
           and phu_chuyen >= CONG and phu_nguoi >= CONG)
    return {
        "do_luc": moc.isoformat(),
        "cong_phan_tram": CONG,
        "nguong_chuyen": nguong_chuyen,
        "do_phu_chuyen": phu_chuyen,
        "do_phu_nguoi": phu_nguoi,
        "so_chuyen_da_chay": so_chuyen,
        "so_chuyen_co_dia_ban": len(chuyen_co_dia_ban),
        "so_hdv_co_chuyen": len(nguoi),
        "so_hdv_du_chuyen": len(du),
        "noi_bang_product_id": theo_khoa.get("id", 0),
        "noi_bang_product_code": theo_khoa.get("code", 0),
        "qua_cong": qua,
        "ket_luan": (
            "QUA CỔNG — nhịp 2 bắt đầu được." if qua else
            "CHƯA QUA CỔNG — BÁO LẠI Chủ tịch. Nhịp 2 KHÔNG bắt đầu. "
            "Tuyệt đối không hạ cổng cho vừa dữ liệu."),
    }


def _in_ra(kq: dict[str, Any]) -> str:
    def s(x):
        return "chưa đo được (mẫu số bằng 0)" if x is None else f"{x}%"
    return "\n".join([
        f"ĐO NỀN ĐỊA BÀN HDV — ngày {kq['do_luc']}",
        f"  cổng                 : {kq['cong_phan_tram']}%   · đủ số chuyến: {kq['nguong_chuyen']}",
        f"  (1) độ phủ CHUYẾN    : {s(kq['do_phu_chuyen'])}"
        f"   ({kq['so_chuyen_co_dia_ban']}/{kq['so_chuyen_da_chay']} chuyến đã chạy nối được địa bàn"
        f" — {kq['noi_bang_product_id']} qua product_id, {kq['noi_bang_product_code']} qua product_code)",
        f"  (2) độ phủ NGƯỜI     : {s(kq['do_phu_nguoi'])}"
        f"   ({kq['so_hdv_du_chuyen']}/{kq['so_hdv_co_chuyen']} HDV có ≥{kq['nguong_chuyen']} chuyến có địa bàn)",
        f"  {kq['ket_luan']}",
    ])


def main(argv: list[str]) -> int:
    """Chạy trên dữ liệu thật: `python -m app.services.dia_ban_hdv` (dùng DATABASE_URL đang khai)."""
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        print(_in_ra(do_nen(db)))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
