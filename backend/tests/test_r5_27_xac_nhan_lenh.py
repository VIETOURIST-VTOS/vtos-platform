# -*- coding: utf-8 -*-
"""R5-27 · GĐ đội xe xác nhận lệnh ngay trên màn một lệnh (Chủ tịch chọn 14/11/2026 «Xác nhận lệnh»).

Trước đây nút «Xác nhận» chỉ có ở màn cũ cho cntt / tp_dh / nv_dh / hcns, trong khi máy chủ chỉ cho người lập
lệnh (`xe_nguoi_lap_lenh`) xác nhận — nên lệnh kẹt ở «chờ xác nhận» và không đóng được."""
from pathlib import Path

S = (Path(__file__).resolve().parents[2] / "web/app/lenh-dieu-xe/page.tsx").read_text(encoding="utf-8")


def test_nut_xac_nhan_tren_thanh_viec_man_mot_lenh():
    assert '{ nhan: "Xác nhận lệnh", href: `${veMot}&viec=xac-nhan`' in S
    assert 'viec === "xac-nhan" && <XacNhanLenh' in S


def test_xac_nhan_goi_dung_cua_va_dung_trang_thai():
    k = S[S.index("function XacNhanLenh("):S.index("/** DL-3 · ĐÓNG LỆNH")]
    assert '`/dispatch/${lenh.id}/update`' in k and 'status: "da_xac_nhan"' in k
    assert 'lenh.status !== "cho_xac_nhan"' in k
    assert "nhận lại" in k                       # nói trước: xác nhận lại thì dấu nhận hết hiệu lực
    assert "const VIEC_MOT = [\"xac-nhan\"," in S
