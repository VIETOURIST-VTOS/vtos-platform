"""VH-13 · XUẤT EXCEL ba bảng của đội xe (Chủ tịch duyệt bản xem trước 11/11/2026).

Chỉ ĐỌC lại đúng các hàm mà màn hình đang đọc — `fleet_ai.hieu_qua_ky`, `fleet_lai_lo.bao_cao`,
`fleet_lai_lo.theo_chuyen` và danh sách chuyến — rồi đổ ra tệp. Không tính lại con số nào ở đây: tệp và
màn hình phải ra cùng một số.

Ô "chưa đủ dữ liệu" để TRỐNG trong tệp, không ghi 0 — số 0 trong Excel đọc ra là "xe không tốn dầu"."""
from __future__ import annotations

import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CHUA_DU = "chua_du_du_lieu"
_NEN_DAU = PatternFill("solid", fgColor="183C69")
_CHU_DAU = Font(bold=True, color="FFFFFF")
_TIEN = '#,##0;[Red]-#,##0'
_TY_LE = '0.0%'


def _o(v):
    """Ô chưa tính được → trống. Ngày giữ kiểu ngày để Excel lọc được."""
    if v is None or v == CHUA_DU:
        return None
    return v


def _trang(wb: Workbook, ten: str, tieu_de: str, cot: list[tuple[str, str, str]], dong: list[dict]):
    """cot = [(khoá, tên cột, kiểu)] — kiểu: '' | 'tien' | 'ty_le' | 'so'."""
    ws = wb.create_sheet(ten[:31])
    ws.append([tieu_de])
    ws["A1"].font = Font(bold=True, size=13, color="183C69")
    ws.append([])
    ws.append([c[1] for c in cot])
    for i in range(1, len(cot) + 1):
        o = ws.cell(row=3, column=i)
        o.fill, o.font = _NEN_DAU, _CHU_DAU
        o.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in dong:
        ws.append([_o(r.get(c[0])) for c in cot])
    for i, (_, ten_cot, kieu) in enumerate(cot, start=1):
        chu = get_column_letter(i)
        ws.column_dimensions[chu].width = max(12, min(40, len(ten_cot) + 4))
        if kieu in ("tien", "ty_le"):
            for row in ws.iter_rows(min_row=4, min_col=i, max_col=i):
                row[0].number_format = _TIEN if kieu == "tien" else _TY_LE
    ws.freeze_panes = "A4"
    if dong:
        ws.auto_filter.ref = f"A3:{get_column_letter(len(cot))}{3 + len(dong)}"
    return ws


def _luu(wb: Workbook) -> bytes:
    if "Sheet" in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb["Sheet"]
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def ky_doc(ky: str) -> str:
    n, t = ky.split("-")
    return f"{t}/{n}"


# ---------- ① Xếp hạng xe & tài xế ----------
COT_XE = [("hang", "Hạng", "so"), ("ma_xe", "Mã xe", ""), ("xe", "Biển số", ""), ("so_chuyen", "Chuyến", "so"),
          ("so_chuyen_chua_qt", "Chuyến chưa QT", "so"), ("ngay_khai_thac", "Ngày khai thác", "so"),
          ("km", "Km", "so"), ("doanh_thu", "Doanh thu", "tien"), ("chi_phi", "Chi phí", "tien"),
          ("chi_phi_ky", "Trong đó chi phí kỳ", "tien"), ("loi_nhuan", "Lợi nhuận", "tien"),
          ("loi_nhuan_moi_ngay", "LN/ngày", "tien"), ("dau_dong_tren_km", "Dầu đ/km", "tien"),
          ("km_moi_lit", "Km/lít", "so"), ("sua_chua_tren_km", "Sửa chữa/km", "tien")]
COT_TX = [("hang", "Hạng", "so"), ("tai_xe", "Tài xế", ""), ("so_chuyen", "Chuyến", "so"),
          ("ngay_khai_thac", "Ngày công", "so"), ("km", "Km", "so"), ("doanh_thu", "Doanh thu", "tien"),
          ("chi_phi", "Chi phí", "tien"), ("loi_nhuan", "Lợi nhuận", "tien"),
          ("dau_dong_tren_km", "Dầu đ/km", "tien")]


def xep_hang(kq: dict, ky: str) -> bytes:
    wb = Workbook()
    _trang(wb, "Xe", f"Hiệu quả từng xe – kỳ {ky_doc(ky)}", COT_XE, kq.get("xe") or [])
    _trang(wb, "Tài xế", f"Hiệu quả từng tài xế – kỳ {ky_doc(ky)}", COT_TX, kq.get("tai_xe") or [])
    return _luu(wb)


# ---------- ② Lãi lỗ đội xe ----------
DONG_TONG = [("doanh_thu", "Doanh thu (chuyến đã quyết toán)"), ("chi_phi_chuyen", "Tầng 1 · Chi phí chuyến"),
             ("lai_gop_chuyen", "Lãi gộp chuyến"), ("chi_phi_xe", "Tầng 2 · Chi phí xe"),
             ("ket_qua_sau_chi_phi_xe", "Kết quả sau chi phí xe"), ("chi_phi_doi", "Tầng 3 · Chi phí đội"),
             ("gia_von", "Giá vốn vận tải (ba tầng)"), ("loi_nhuan", "Lợi nhuận"),
             ("chi_phi_tai_chinh", "Chi phí tài chính (ngoài giá vốn)"),
             ("ket_qua_sau_tai_chinh", "Kết quả sau tài chính"),
             ("so_chuyen_chua_quyet_toan", "Số chuyến chưa quyết toán (không vào lợi nhuận)"),
             ("doanh_thu_chua_quyet_toan", "Doanh thu chưa quyết toán (đang treo)")]
COT_LL_XE = [("ma_xe", "Mã xe", ""), ("xe", "Biển số", ""), ("so_chuyen", "Chuyến", "so"),
             ("ngay_khai_thac", "Ngày khai thác", "so"), ("cong_suat", "Công suất", "ty_le"),
             ("km", "Km", "so"), ("doanh_thu", "Doanh thu", "tien"), ("chi_phi_chuyen", "Chi phí chuyến", "tien"),
             ("lai_gop_chuyen", "Lãi gộp chuyến", "tien"), ("ty_le_lai_gop", "Tỷ lệ lãi gộp", "ty_le"),
             ("chi_phi_xe", "Chi phí xe", "tien"), ("ket_qua_xe", "Kết quả xe", "tien"),
             ("km_moi_lit", "Km/lít", "so")]
COT_LL_CHUYEN = [("ma_phieu", "Mã phiếu", ""), ("xe", "Xe", ""), ("tai_xe", "Tài xế", ""), ("ten_tour", "Tour", ""),
                 ("ngay_di", "Ngày đi", ""), ("ngay_ve", "Ngày về", ""), ("so_ngay", "Số ngày", "so"),
                 ("quyet_toan_chu", "Quyết toán", ""), ("doanh_thu", "Doanh thu", "tien"),
                 ("chi_phi_chuyen", "Chi phí chuyến", "tien"), ("lai_gop", "Lãi gộp", "tien"),
                 ("ty_le", "Tỷ lệ", "ty_le"), ("km", "Km", "so"), ("tien_dau", "Tiền dầu", "tien"),
                 ("km_moi_lit", "Km/lít", "so"), ("dau_moi_km", "Dầu đ/km", "tien")]


def lai_lo(bc: dict, chuyen: list[dict], ky: str) -> bytes:
    wb = Workbook()
    t = bc.get("tong") or {}
    ws = wb.create_sheet("Tổng kỳ")
    ws.append([f"Lãi lỗ đội xe – kỳ {ky_doc(ky)}"])
    ws["A1"].font = Font(bold=True, size=13, color="183C69")
    ws.append([])
    ws.append(["Khoản", "Số tiền"])
    for o in ws[3]:
        o.fill, o.font = _NEN_DAU, _CHU_DAU
    for k, ten in DONG_TONG:
        ws.append([ten, _o(t.get(k))])
        ws.cell(row=ws.max_row, column=2).number_format = _TIEN
        if k in ("loi_nhuan", "gia_von"):
            ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
            ws.cell(row=ws.max_row, column=2).font = Font(bold=True)
    ws.append(["Tỷ lệ lợi nhuận", _o(t.get("ty_le_loi_nhuan"))])
    ws.cell(row=ws.max_row, column=2).number_format = _TY_LE
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 52, 20
    _trang(wb, "Theo xe", f"Lãi lỗ theo xe – kỳ {ky_doc(ky)}", COT_LL_XE, bc.get("xe") or [])
    rows = [{**c, "quyet_toan_chu": "Đã quyết toán" if c.get("quyet_toan") else "Chưa quyết toán"} for c in chuyen]
    _trang(wb, "Theo chuyến", f"Lãi lỗ theo chuyến – kỳ {ky_doc(ky)}", COT_LL_CHUYEN, rows)
    return _luu(wb)


# ---------- ③ Báo cáo từng xe (nhật trình chuyến) ----------
COT_CHUYEN = [("ma_phieu", "Mã phiếu", ""), ("xe", "Xe", ""), ("tai_xe", "Tài xế", ""), ("ten_tour", "Tour", ""),
              ("ngay_di", "Ngày đi", ""), ("ngay_ve", "Ngày về", ""), ("so_ngay", "Số ngày", "so"),
              ("km_dau", "Km đầu", "so"), ("km_cuoi", "Km cuối", "so"), ("km_chay", "Km chạy", "so"),
              ("doanh_thu", "Doanh thu", "tien"), ("tong_chi_phi", "Chi phí ghi nhận", "tien"),
              ("trang_thai", "Trạng thái quyết toán", ""), ("note", "Ghi chú", "")]


def bao_cao_xe(chuyen: list[dict], ky: str) -> bytes:
    rows = []
    for c in chuyen:
        tt = c.get("qt_ten_trang_thai") or ("Đã quyết toán" if c.get("quyet_toan") else "Chưa quyết toán")
        cp = sum((x.get("amount") or 0) for x in (c.get("chi_phi") or []))
        rows.append({**c, "trang_thai": tt, "tong_chi_phi": cp})
    wb = Workbook()
    _trang(wb, "Báo cáo từng xe", f"Báo cáo từng xe – chuyến khởi hành trong kỳ {ky_doc(ky)}", COT_CHUYEN, rows)
    return _luu(wb)


def ten_tep(goc: str, ky: str) -> str:
    return f"{goc}_{ky.replace('-', '')}_{date.today().strftime('%Y%m%d')}.xlsx"
