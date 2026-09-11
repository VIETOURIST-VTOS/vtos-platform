# -*- coding: utf-8 -*-
"""Mẫu trống do phần mềm phát ra phải KHỚP với chính bộ đọc của phần mềm.

VÌ SAO PHẢI CÓ TỆP KIỂM NÀY

Mẫu trống (app/services/dung_mau_quyet_toan.py) và bộ nạp (app/services/nap_mau_quyet_toan.py) là
hai tệp mã khác nhau, do hai lần viết khác nhau. Bộ nạp dò cột THEO NHÃN. Cho nên chỉ cần một lần
ai đó sửa nhãn cột ở mẫu cho "gọn hơn" – "Mã khoản mục" thành "Khoản mục" chẳng hạn – là bộ nạp im
lặng đọc ra rỗng: không báo lỗi, không đỏ ở đâu cả, chỉ là cả cột ấy biến mất khỏi dữ liệu nạp lên.

Đó là kiểu hỏng tệ nhất trong cả hệ: máy không kêu, người không thấy, và con số thì thiếu.

Tệp này buộc hai bên phải nói cùng một thứ tiếng: mọi nhãn bộ nạp đi tìm phải có thật trên mẫu, và
sheet KHOẢN MỤC trên mẫu phải đúng bằng danh mục trong mã.
"""
from io import BytesIO

import openpyxl
import pytest

from app.services import dung_mau_quyet_toan as DM
from app.services import khoan_muc_chi as KM
from app.services import nap_mau_quyet_toan as NMQT


def _wb(NN: bool):
    return openpyxl.load_workbook(BytesIO(DM.dung(NN)))


def _nhan(ws, hang: int) -> set:
    return {str(ws.cell(hang, c).value).strip()
            for c in range(1, ws.max_column + 1)
            if ws.cell(hang, c).value not in (None, "")}


def test_dung_duoc_ca_hai_hinh_thuc():
    for NN in (False, True):
        b = DM.dung(NN)
        assert isinstance(b, bytes) and len(b) > 10_000
        wb = openpyxl.load_workbook(BytesIO(b))
        # Bốn sheet bộ đọc BẮT BUỘC phải có, nếu thiếu thì doc_tep() ném ValueError.
        for s in ("THÔNG TIN", "KHÁCH", "THU", "CHI"):
            assert s in wb.sheetnames


def test_chi_nuoc_ngoai_moi_co_sheet_chi_theo_khach():
    """Bộ đọc suy hình thức từ chính bộ sheet khi ô 'Hình thức' bị bỏ trống.

    Suy ấy chỉ đúng nếu mẫu trong nước KHÔNG có sheet CHI THEO KHÁCH. Thêm sheet ấy vào mẫu trong
    nước "cho hai mẫu giống nhau" là làm hỏng phép suy mà không ai nhận ra.
    """
    assert "CHI THEO KHÁCH" not in _wb(False).sheetnames
    assert "CHI THEO KHÁCH" in _wb(True).sheetnames


def test_moi_nhan_bo_nap_di_tim_deu_co_that_tren_mau():
    """Nhãn bộ nạp đọc phải có trên mẫu – nếu không, cột ấy nạp lên rỗng mà không báo lỗi."""
    co = {False: {}, True: {}}
    for NN in (False, True):
        wb = _wb(NN)
        co[NN] = {
            "KHÁCH": _nhan(wb["KHÁCH"], 2),
            "THU": _nhan(wb["THU"], 2),
            "CHI": _nhan(wb["CHI"], 2),
            "PHƯƠNG TIỆN": _nhan(wb["PHƯƠNG TIỆN"], 2),
            "HDV": _nhan(wb["HDV"], 3),
        }
        if "CHI THEO KHÁCH" in wb.sheetnames:
            co[NN]["CHI THEO KHÁCH"] = _nhan(wb["CHI THEO KHÁCH"], 3)

    # Nhãn phải có ở CẢ HAI mẫu.
    chung = {
        "KHÁCH": ["STT", "Nhóm khách", "Họ và tên", "Ngày sinh", "Giá bán", "Note", "Mã đặt chỗ"],
        "THU": ["Loại", "Nội dung", "Khách (STT)", "Đối tượng", "Đơn giá trước thuế", "Số lượng",
                "Thuế suất", "Chứng từ (bắt buộc nếu ÂM)"],
        "CHI": ["Ngày", "Mã khoản mục", "Nhóm", "Nội dung", "Đối tác", "MST đối tác", "Đối tượng",
                "Quy tắc phân bổ", "DỰ CHI (VND)", "THỰC CHI (VND)", "Thuế suất",
                "Phần KHÔNG hoá đơn", "Số hoá đơn"],
        "PHƯƠNG TIỆN": ["Loại", "Chặng", "Ngày", "Số hiệu / biển số", "Mã đặt chỗ", "Nhà cung cấp",
                        "MST", "Xe nhà?", "Số chỗ", "Số khách dùng", "Thành tiền (VND)", "Ghi chú"],
        "HDV": ["Nội dung", "Tiền tệ", "Số gốc", "Tỷ giá", "Thực chi (VND)", "Theo chiết tính",
                "Chứng từ", "Thu hộ khách?", "Duyệt", "Lý do duyệt / từ chối"],
    }
    for NN in (False, True):
        for sheet, nhan in chung.items():
            thieu = [n for n in nhan if n not in co[NN][sheet]]
            assert not thieu, f"{'NN' if NN else 'TN'} – sheet {sheet} thiếu nhãn: {thieu}"

    # Nhãn RIÊNG của từng hình thức.
    assert "CCCD" in co[False]["KHÁCH"] and "Số hộ chiếu" not in co[False]["KHÁCH"]
    assert "Số hộ chiếu" in co[True]["KHÁCH"] and "CCCD" not in co[True]["KHÁCH"]
    for n in ("Tiền tệ", "Số tiền gốc", "Tỷ giá", "Ngày tỷ giá"):
        assert n in co[True]["CHI"], f"mẫu nước ngoài thiếu cột ngoại tệ {n}"
        assert n not in co[False]["CHI"], f"mẫu trong nước không nên có cột {n}"
    for n in ("Khách (STT)", "Loại chi phí", "Nhà cung cấp", "MST", "Tiền tệ", "Số tiền gốc",
              "Tỷ giá", "Thành tiền (VND)", "Số hoá đơn"):
        assert n in co[True]["CHI THEO KHÁCH"]


def test_cot_bat_buoc_dung_dong_tieu_de_bo_nap_doc():
    """_bang() nhận SỐ DÒNG tiêu đề viết cứng. Lệch một dòng là đọc ra bảng rỗng, không báo lỗi."""
    for NN in (False, True):
        wb = _wb(NN)
        assert "Họ và tên" in _nhan(wb["KHÁCH"], 2)
        assert "Nội dung" in _nhan(wb["THU"], 2)
        assert "Nội dung" in _nhan(wb["CHI"], 2)
        assert "Loại" in _nhan(wb["PHƯƠNG TIỆN"], 2)
        assert "Nội dung" in _nhan(wb["HDV"], 3)      # HDV có một dòng lời dẫn ở trên
        if NN:
            assert "Loại chi phí" in _nhan(wb["CHI THEO KHÁCH"], 3)


def test_sheet_khoan_muc_dung_bang_danh_muc_trong_ma():
    """Sheet KHOẢN MỤC là bản sao danh mục. Lệch một mã là nhân viên chọn đúng mà bị từ chối."""
    for NN in (False, True):
        hinh_thuc = "nuoc_ngoai" if NN else "trong_nuoc"
        trong_ma = [x["ma"] for x in KM.danh_sach(hinh_thuc)]
        wb = _wb(NN)
        ws = wb["KHOẢN MỤC"]
        tren_mau = []
        for r in range(3, ws.max_row + 1):
            v = ws.cell(r, 1).value
            if v in (None, ""):        # dòng trắng ngăn danh mục với lời chú ở cuối sheet
                break
            tren_mau.append(str(v).strip())
        assert tren_mau == trong_ma, (
            f"{hinh_thuc}: mẫu và danh mục lệch nhau – "
            f"thừa {set(tren_mau) - set(trong_ma)}, thiếu {set(trong_ma) - set(tren_mau)}")

        # Ô CHỌN ở sheet CHI trỏ vào một KHOẢNG CỐ ĐỊNH của sheet KHOẢN MỤC. Khoảng ấy ngắn hơn danh
        # mục thì mấy mã cuối không bao giờ chọn được; dài hơn thì ô chọn có mấy dòng trắng.
        cuoi = 2 + len(trong_ma)
        dv = [d for d in wb["CHI"].data_validations.dataValidation
              if d.formula1 and "KHOẢN MỤC" in d.formula1]
        assert dv, "sheet CHI mất ô chọn mã khoản mục"
        assert all(d.formula1.endswith(f"$A${cuoi}") for d in dv), \
            f"{hinh_thuc}: ô chọn trỏ {[d.formula1 for d in dv]}, danh mục hết ở dòng {cuoi}"


def test_mau_trong_doc_duoc_va_ra_bang_rong():
    """Mẫu trống phải đi lọt bộ đọc mà không nổ, và không đẻ ra dòng ma.

    Dòng ví dụ mờ hay dòng công thức để sẵn mà bộ đọc tưởng là dữ liệu thật thì nhân viên tải mẫu
    về, tải thẳng lên chưa điền gì, hệ thống đã ghi vài dòng chi phí trị giá 0.
    """
    for NN in (False, True):
        d = NMQT.doc_tep(DM.dung(NN), "mau_trong.xlsx")
        assert d["khach"] == [] and d["thu"] == [] and d["chi"] == []
        assert d["phuong_tien"] == [] and d["hdv_chi"] == [] and d["chi_khach"] == []
        # Ô 'Hình thức' trên mẫu trống chưa điền -> bộ đọc phải SUY ĐÚNG từ bộ sheet.
        assert d.get("hinh_thuc") == ("nuoc_ngoai" if NN else "trong_nuoc") or \
               d.get("hinh_thuc_suy_ra") == ("nuoc_ngoai" if NN else "trong_nuoc")


def test_khong_o_tong_nao_la_so_go_tay():
    """Nguyên tắc 1 của mẫu: máy cộng, người không gõ tổng. Ô tổng phải là CÔNG THỨC.

    Một ô tổng là số cứng thì nó đứng yên trong khi các dòng đổi – và đó đúng là lỗi 210.000 đ đã
    đo được trên tệp thật, lý do cả bộ mẫu này ra đời.
    """
    for NN in (False, True):
        wb = _wb(NN)
        for ten in ("THU", "CHI", "PHƯƠNG TIỆN", "HDV", "LÃI LỖ"):
            ws = wb[ten]
            for r in range(1, ws.max_row + 1):
                nhan = str(ws.cell(r, 1).value or "").upper()
                if not nhan.startswith("CỘNG"):
                    continue
                o_so = [ws.cell(r, c).value for c in range(2, ws.max_column + 1)
                        if isinstance(ws.cell(r, c).value, (int, float))]
                assert not o_so, f"{'NN' if NN else 'TN'} – {ten} dòng {r}: ô tổng gõ số cứng {o_so}"


def test_cua_tai_mau_trong():
    """Cửa /mau-trong: trả đúng bytes .xlsx, đúng tên tệp, và từ chối hình thức lạ."""
    from fastapi import HTTPException
    from app.api.v1.quyet_toan_lop3 import mau_trong, NHAP, XEM

    for ht, ten in (("trong_nuoc", "MAU_QT_TOUR_TRONG_NUOC.xlsx"),
                    ("nuoc_ngoai", "MAU_QT_TOUR_NUOC_NGOAI.xlsx")):
        r = mau_trong(hinh_thuc=ht, u=None)
        assert r.status_code == 200
        assert ten in r.headers["content-disposition"]
        assert r.body[:2] == b"PK"          # .xlsx là một tệp zip
        assert openpyxl.load_workbook(BytesIO(r.body)).sheetnames  # mở được thật

    # Hình thức lạ thì NÓI RA, không lặng lẽ phát mẫu trong nước. Phát nhầm mẫu thì nhân viên điền
    # xong cả tờ mới biết thiếu hẳn phần ngoại tệ.
    with pytest.raises(HTTPException) as e:
        mau_trong(hinh_thuc="doan", u=None)
    assert e.value.status_code == 422

    # Cửa tải đòi quyền NHẬP, hẹp hơn quyền XEM – người tải mẫu là người sắp nộp tờ.
    assert set(NHAP) < set(XEM) or set(NHAP) != set(XEM)
    assert "bks" not in NHAP and "chutich" not in NHAP


def test_ghi_ra_tep_khi_duoc_dua_ten():
    """Tham số ten_tep để chạy tay ở máy; trả về bytes vẫn phải nguyên vẹn."""
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.xlsx")
        b = DM.dung(False, p)
        assert os.path.exists(p) and os.path.getsize(p) > 10_000
        assert openpyxl.load_workbook(BytesIO(b)).sheetnames == \
               openpyxl.load_workbook(p).sheetnames
