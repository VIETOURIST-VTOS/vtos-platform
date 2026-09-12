# -*- coding: utf-8 -*-
"""TC-8 · Màn hình 01 Tổng quan điều hành — khung theo vai ĐÃ ĐIỀN SỐ.

Tệp này canh chỗ nối giữa hai làn, và chỗ nối là chỗ dễ hỏng nhất vì không làn nào coi nó là của
mình:

  1. Hai làn đặt MÃ DÒNG khác nhau cho cùng một dòng ("thu_cong_no_khac" ở làn Phân quyền là
     "thu_cong_no" ở làn Robot A). Thêm một dòng ở một bên mà quên bên kia thì dòng ấy lặng lẽ
     rỗng trên màn hình — không lỗi, không cảnh báo, chỉ là một ô trống trông như "chưa có số".

  2. Dòng TỔNG cộng từ toàn cảnh rồi mới cắt. Khi ấy bảng của TGĐ tự mâu thuẫn: cộng mắt các dòng
     ra một số, dòng tổng in ra một số khác.

  3. Dòng bị cắt vẫn RỜI KHỎI máy chủ rồi mới bị trình duyệt ẩn đi. Ai mở công cụ nhà phát triển
     cũng đọc được — SEC-02 gọi đó là lỗi đỏ.
"""
import os
import re

import pytest

from app.services import dong_tien_pham_vi as SEC
from app.services import khung_dong_tien as K

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COT = [
    {"ma": "7n", "ten": "Lũy kế 7 ngày", "tu_ngay": "2026-09-12", "den_ngay": "2026-09-18"},
    {"ma": "14n", "ten": "Lũy kế 14 ngày", "tu_ngay": "2026-09-12", "den_ngay": "2026-09-25"},
]


def _bang(thieu: tuple[str, ...] = (), dau_ky: float | None = 1_000_000) -> dict:
    """Bảng bốn mốc dựng tay. `thieu` là các MÃ CỦA LÀN ROBOT A chưa có nguồn."""
    dong = []
    for i, (ma, ten, chieu, nguon, bo_phan) in enumerate(
            [("thu_khach", "Thu khách", "vao", "x", ""),
             ("thu_cong_no", "Thu công nợ khác", "vao", "x", "Kế toán"),
             ("giai_ngan_vay", "Giải ngân vay", "vao", "x", ""),
             ("tra_ncc", "Trả nhà cung cấp", "ra", "x", ""),
             ("hoan_khach", "Hoàn khách", "ra", "x", "Kế toán"),
             ("hoa_hong", "Hoa hồng", "ra", "x", "Kinh doanh"),
             ("tra_goc_vay", "Trả gốc vay", "ra", "x", ""),
             ("lai_phi_vay", "Lãi và phí", "ra", "x", ""),
             ("luong_bhxh", "Lương", "ra", "x", "Nhân sự"),
             ("thue", "Thuế", "ra", "x", "Kế toán"),
             ("van_hanh", "Vận hành", "ra", "x", "Các phòng")]):
        rong = ma in thieu
        d = {"ma": ma, "ten": ten, "chieu": chieu,
             "so": {c["ma"]: (None if rong else (i + 1) * 1000) for c in COT}}
        if rong:
            d["chua_co_nguon"] = True
            d["bo_phan_chiu_trach_nhiem"] = bo_phan
        dong.append(d)
    return {"cot": COT, "dong": dong, "tien_kha_dung_dau_ky": dau_ky,
            "ghi_nho": {"tien_thu_ho_khach": 7000, "ky_quy_giay_phep_lu_hanh": None},
            "doi_soat_den_ngay": "2026-09-11", "hom_nay": "2026-09-12",
            "phap_nhan": {"id": 1, "code": "VTD"},
            "cong_bon_cot_la_sai": "Bốn cột lũy kế chồng lên nhau – không cộng.",
            "vi_sao_khong_co_so_cuoi": ""}


SDN = {"muc_du_phong": 2_000_000, "ngay": [{"ngay": "2026-09-13"}],
       "ngay_dau_thieu_tien": "2026-09-14", "muc_thieu_lon_nhat": 500_000,
       "vi_sao_chua_co_nguong": "", "vi_sao_khong_ve_duoc": ""}


# =============================================================================================
# 1. Cây cầu giữa hai làn
# =============================================================================================

def test_moi_dong_cua_v11_deu_bac_duoc_cau_sang_bang_bon_moc():
    """Danh sách này rỗng thì thôi; không rỗng nghĩa là có một dòng sẽ lặng lẽ trống trên màn hình."""
    assert K.thieu_cau() == []


def test_ma_ben_kia_cau_deu_co_that_trong_bang_bon_moc():
    from app.services.dong_tien import DONG_BANG
    co = {d[0] for d in DONG_BANG}
    thieu = [v for v in K.MA_SEC_SANG_DT.values() if v not in co]
    assert thieu == [], f"mã không có trong DONG_BANG: {thieu}"


def test_hai_dong_ghi_nho_tro_dung_khoa_cua_ban_ghi_nho():
    """Khoá đúng là `ky_quy_giay_phep_lu_hanh`. Trang tạm của làn A gõ thiếu hai chữ cuối nên ô ấy
    hiện '—' vĩnh viễn dù máy chủ có số — một lỗi không ai thấy vì nó trông y như 'chưa có số'."""
    b = _bang()
    assert set(K.GHI_NHO_SANG_DT.values()) <= set(b["ghi_nho"])


# =============================================================================================
# 2. Máy chủ cắt tập dòng, không phải trình duyệt
# =============================================================================================

def test_chu_tich_thay_du_moi_dong():
    r = K.ghep("chutich", _bang(), SDN)
    assert r["xem_duoc"] is True
    assert [d["ma"] for d in r["dong"]] == [d.ma for d in SEC.CAC_DONG]


def test_tgd_khong_nhan_dong_tai_chinh_ngay_TRONG_GOI_TRA_VE():
    """Không phải 'không hiện' mà là KHÔNG CÓ trong gói trả về."""
    r = K.ghep("tgd", _bang(), SDN)
    ma = {d["ma"] for d in r["dong"]}
    assert not ({"giai_ngan_vay", "tra_goc_vay", "lai_phi_ngan_hang", "thue_nghia_vu",
                 "ghi_nho_ky_quy", "tien_kha_dung_dau_ky", "so_du_du_kien_cuoi_khoang",
                 "thieu_so_voi_muc_du_phong"} & ma)
    assert "Giải ngân vay" not in repr(r), "tên dòng tài chính vẫn lọt vào gói của TGĐ"


def test_vai_khong_duoc_khai_thi_khong_nhan_gi():
    for vai in ("ptgd_kd", "nv_kd", ""):
        r = K.ghep(vai, _bang(), SDN)
        assert r["xem_duoc"] is False and "dong" not in r


def test_ten_dong_day_di_theo_pham_vi():
    assert K.ghep("tgd", _bang(), SDN)["ten_dong_day"] == "Dòng tiền thuần từ hoạt động tour và xe"
    assert "SỐ DƯ" in K.ghep("chutich", _bang(), SDN)["ten_dong_day"]


# =============================================================================================
# 3. Dòng tổng cộng từ tập dòng CỦA CHÍNH VAI ẤY
# =============================================================================================

def _o(r, ma):
    return next(d for d in r["dong"] if d["ma"] == ma)


def test_tong_thu_cua_tgd_khong_cong_khoan_giai_ngan_vay():
    ct = _o(K.ghep("chutich", _bang(), SDN), "tong_thu")["so"]["7n"]
    tgd = _o(K.ghep("tgd", _bang(), SDN), "tong_thu")["so"]["7n"]
    assert tgd == 1000 + 2000            # thu khách + thu công nợ khác
    assert ct == 1000 + 2000 + 3000      # cộng thêm giải ngân vay
    assert tgd != ct


def test_dong_thuan_bang_dung_tong_thu_tru_tong_chi_cua_chinh_vai_ay():
    r = K.ghep("tgd", _bang(), SDN)
    thu = _o(r, "tong_thu")["so"]["7n"]
    chi = _o(r, "tong_chi")["so"]["7n"]
    assert r["dong_tien_thuan"]["7n"] == thu - chi


def test_ghi_nho_khong_bao_gio_lot_vao_phep_cong():
    r = K.ghep("chutich", _bang(), SDN)
    tong = _o(r, "tong_thu")["so"]["7n"] + _o(r, "tong_chi")["so"]["7n"]
    assert 7000 not in (tong, _o(r, "tong_thu")["so"]["7n"])


# =============================================================================================
# 4. Rỗng khác không
# =============================================================================================

def test_mot_dong_thieu_nguon_thi_dong_tong_RONG_chu_khong_phai_so_dep():
    r = K.ghep("chutich", _bang(thieu=("thu_khach",)), SDN)
    assert _o(r, "tong_thu")["so"]["7n"] is None
    assert _o(r, "tong_thu")["chua_co_nguon"] is True
    assert "Thu khách" in _o(r, "tong_thu")["vi_sao_rong"]
    assert r["dong_tien_thuan"]["7n"] is None


def test_thieu_tien_dau_ky_thi_khong_co_so_du_cuoi():
    r = K.ghep("chutich", _bang(dau_ky=None), SDN)
    assert _o(r, "so_du_du_kien_cuoi_khoang")["so"]["7n"] is None
    assert _o(r, "tien_kha_dung_dau_ky")["so_mot_moc"] is None


def test_chua_chot_muc_du_phong_thi_dong_thieu_de_RONG():
    sdn = {**SDN, "muc_du_phong": None, "vi_sao_chua_co_nguong": "Chưa đủ hai chữ ký"}
    r = K.ghep("chutich", _bang(), sdn)
    assert _o(r, "thieu_so_voi_muc_du_phong")["so"]["7n"] is None
    assert "hai chữ ký" in _o(r, "thieu_so_voi_muc_du_phong")["vi_sao_rong"]


def test_o_canh_bao_chua_noi_nguon_thi_khong_bien_mat_va_khong_hien_0():
    o = {c["ma"]: c for c in K.ghep("chutich", _bang(), SDN)["canh_bao"]}
    assert set(o) == {"phai_tra_qua_han", "phai_tra_7_ngay", "ngay_dau_thieu_tien",
                      "muc_thieu_lon_nhat"}
    assert o["phai_tra_qua_han"]["gia_tri"] is None
    assert o["phai_tra_qua_han"]["bo_phan"], "ô chưa nối nguồn phải nói ai đi nối"
    assert o["ngay_dau_thieu_tien"]["gia_tri"] == "2026-09-14"


def test_tgd_chi_thay_hai_o_canh_bao():
    ma = {c["ma"] for c in K.ghep("tgd", _bang(), SDN)["canh_bao"]}
    assert ma == {"phai_tra_qua_han", "phai_tra_7_ngay"}


# =============================================================================================
# 5. CF-07 · mọi dòng nhập tay đều nói được AI nhập
# =============================================================================================

def test_moi_dong_khong_tu_tinh_deu_co_cua_va_bo_phan():
    for vai in ("chutich", "tgd"):
        for d in K.ghep(vai, _bang(), SDN)["dong"]:
            if d.get("tu_tinh"):
                continue
            assert d.get("cua") and d.get("bo_phan"), f"{vai}/{d['ma']} không nói ai nhập"
            assert not d.get("thieu_khai_cua"), f"{vai}/{d['ma']} chưa khai cửa nhập"


def test_dong_tu_tinh_khong_duoc_co_cua_nhap():
    """Có cửa nhập cho một dòng tính ra được tức là cho phép gõ đè lên kết quả — chỗ số liệu bắt
    đầu nói khác sổ."""
    for d in K.ghep("chutich", _bang(), SDN)["dong"]:
        if d["ma"] in K.TU_TINH:
            assert d.get("tu_tinh") is True and "cua" not in d


# =============================================================================================
# 6. Màn hình KHÔNG được tự lọc
# =============================================================================================

def _doc(duong: str) -> str:
    with open(os.path.join(GOC, duong), encoding="utf-8") as f:
        return f.read()


def test_khoi_dong_tien_khong_nhac_ten_vai_tro_nao():
    """Màn hình vẽ đúng những gì máy chủ trả. Một câu `if (vai === "tgd")` ở đây nghĩa là dòng bị
    ẩn vẫn đã rời khỏi máy chủ."""
    src = _doc("web/components/KhoiDongTien.tsx")
    than = re.sub(r"/\*.*?\*/", "", src, flags=re.S)      # bỏ chú thích, ở đó có nhắc tên vai
    for vai in ('"tgd"', '"chutich"', '"ketoan"', '"bks"'):
        assert vai not in than, f"màn hình đang tự xử theo vai {vai}"


def test_khoi_dong_tien_goi_dung_cua_khung_theo_vai():
    src = _doc("web/components/KhoiDongTien.tsx")
    assert "/dong-tien/khung/" in src
    assert "Chưa có nguồn" in src, "ô rỗng phải nói 'Chưa có nguồn', không để trống trơn"


def test_trang_chu_co_khoi_dong_tien():
    src = _doc("web/app/page.tsx")
    assert "KhoiDongTien" in src and "@/components/KhoiDongTien" in src


def test_bang_co_cot_cua_nhap():
    """CF-07 trên màn hình: mỗi dòng phải nhìn thấy được ai nhập, không chỉ nằm trong gói JSON."""
    src = _doc("web/components/KhoiDongTien.tsx")
    assert "Cửa nhập" in src


# =============================================================================================
# 7. Thứ tự pháp nhân trong ô chọn đơn vị (chốt 12/9/2026)
# =============================================================================================

def test_thu_tu_phap_nhan_dat_cong_ty_me_len_dau():
    """Xếp theo bảng chữ cái thì Buffalotours đứng đầu và Vietourist Holdings nằm gần cuối — con số
    đầu tiên đập vào mắt người mở màn hình là con số họ ít cần nhất."""
    src = _doc("web/lib/thu_tu_don_vi.ts")
    ma = re.findall(r'"([A-Z0-9\-]+)",\s*//', src)
    assert ma[:4] == ["VTD", "VTRIP-VT", "LANGAU", "HKTN"], f"thứ tự đang là {ma}"


def test_ma_la_van_hien_du_chu_khong_bi_bo_qua():
    """Thêm một pháp nhân mới mà quên sửa tệp thứ tự thì nó vẫn phải xuất hiện, chỉ xếp sau."""
    src = _doc("web/lib/thu_tu_don_vi.ts")
    assert "THU_TU_MA.length" in src, "mã lạ phải rơi xuống cuối, không được lọc bỏ"
    assert "localeCompare" in src, "phần còn lại xếp theo bảng chữ cái"


def test_khoi_dong_tien_dung_thu_tu_chung_va_chon_don_vi_dau_tien():
    src = _doc("web/components/KhoiDongTien.tsx")
    assert "xepDonVi" in src, "màn hình phải dùng thứ tự dùng chung, không tự xếp"
    assert "setPn(ds[0].id)" in src, "mặc định chọn pháp nhân đứng đầu thứ tự"
