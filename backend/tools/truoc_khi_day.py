#!/usr/bin/env python3
"""KS-1 · Cửa chặn chạy TRƯỚC MỖI LẦN ĐẨY.

Khác với phép thử trong pytest ở đúng một điểm, và điểm ấy là toàn bộ lý do tệp này tồn tại: ở đây
KHÔNG có đường bỏ qua. Máy lập trình không phân giải được nhánh chính thì pytest cho qua, còn lúc đẩy
thì không — không đọc được nhánh chính nghĩa là không biết mình đang đẩy gì lên đâu, và đó là ĐỎ.

Cài một lần cho cả kho:

    git config core.hooksPath backend/tools

Chạy tay khi muốn xem trước:

    python backend/tools/truoc_khi_day.py

Mã thoát: 0 = đẩy được · 1 = mạch hỏng · 2 = không kiểm được (cũng là chặn).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import ks_mach as M  # noqa: E402

VACH = "─" * 72


def _in(*a):
    print(*a, file=sys.stderr)


def main() -> int:
    _in(VACH)
    _in("KS-1 · kiểm mạch nâng cấp trước khi đẩy")
    _in(VACH)

    cay = M.doc_mach_tu_cay()
    _in(" " + M.bao_cao(cay, "cây làm việc"))

    loi: list[str] = []

    treo_cay = M.moc_treo(cay)
    if treo_cay:
        loi.append(f"cây làm việc có móc treo: {treo_cay}")
    if M.vong_lap(cay):
        loi.append(f"cây làm việc có vòng lặp tại {M.vong_lap(cay)}")

    # Lấy bản mới nhất của nhánh chính về. Không có mạng thì vẫn dùng ref đang có, nhưng nói ra.
    if M._git("fetch", "--quiet", "origin", "main") is None:
        _in(" ! không fetch được origin/main — đang so với bản đã lấy về lần trước")

    ref = M.ref_dung_duoc()
    if ref is None:
        _in(VACH)
        _in(" CHẶN: không phân giải được nhánh chính (đã thử: %s)."
            % ", ".join((M.NHANH_CHINH,) + M.REF_DU_PHONG))
        _in(" Không đọc được nhánh chính thì không biết bản nâng cấp này sẽ móc vào đâu.")
        _in(" Đặt nhánh khác bằng biến môi trường VTOS_NHANH_CHINH nếu kho này không dùng main.")
        _in(VACH)
        return 2

    nhanh = M.doc_mach_tu_nhanh(ref)
    if not nhanh:
        _in(VACH)
        _in(f" CHẶN: đọc được ref {ref} nhưng không lấy được bản migration nào của nó.")
        _in(" Nhiều khả năng đường dẫn alembic/versions đã đổi chỗ mà KS-1 chưa biết.")
        _in(VACH)
        return 2

    _in(" " + M.bao_cao(nhanh, ref))

    treo_nhanh = M.moc_treo(nhanh)
    if treo_nhanh:
        loi.append(f"NHÁNH {ref} ĐANG HỎNG SẴN — có bản nối sau mã không tồn tại: {treo_nhanh}. "
                   f"Mọi lần triển khai đều chết ở 'alembic upgrade head'.")
    if len(M.dau_mach(nhanh)) != 1:
        loi.append(f"nhánh {ref} có {len(M.dau_mach(nhanh))} đầu mạch: {M.dau_mach(nhanh)}")

    hop, xung_dot = M.hop_mach(cay, nhanh)
    _in(" " + M.bao_cao(hop, "xem trước bản gộp"))

    moi = M.rieng_cua_cay(cay, nhanh)
    _in(f" bản sắp đẩy: {moi or '(không có)'}")

    if xung_dot:
        loi.append("đổi down_revision của bản ĐÃ có trên nhánh chính: "
                   + "; ".join(f"{r} ({a} → {b})" for r, a, b in xung_dot))
    if M.moc_treo(hop):
        loi.append(f"bản gộp vẫn còn móc treo: {M.moc_treo(hop)} — bản nền nằm ở nhánh thứ ba chưa gộp")
    if len(M.dau_mach(hop)) != 1:
        loi.append(f"GỘP VÀO LÀ {len(M.dau_mach(hop))} ĐẦU: {M.dau_mach(hop)}. Từng nhánh xanh, gộp lại hỏng. "
                   f"Cho bản CHƯA đẩy nối tiếp bản đã có trên nhánh chính.")

    for r in moi:
        di, cur = set(), hop.get(r)
        while cur is not None and cur not in di:
            if cur in nhanh:
                break
            di.add(cur)
            cur = hop.get(cur)
        else:
            loi.append(f"bản sắp đẩy {r} lần ngược tới {cur!r} mà không chạm được {ref} — "
                       f"nó đang móc vào cây làm việc, không móc vào nhánh chính")

    _in(VACH)
    if loi:
        _in(" CHẶN ĐẨY · %d việc phải sửa:" % len(loi))
        for i, l in enumerate(loi, 1):
            _in(f"  {i}. {l}")
        _in("")
        _in(" Ngày 10/9/2026 đúng lỗi này lọt qua và Render chết ở KeyError: 'v14b6e9c2a7d31'.")
        _in(" Web vẫn chạy vì máy chủ giữ bản cũ, nên không ai thấy — cho tới lần cần vá gấp.")
        _in(VACH)
        return 1

    _in(" mạch nâng cấp đạt · đẩy được")
    _in(VACH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
