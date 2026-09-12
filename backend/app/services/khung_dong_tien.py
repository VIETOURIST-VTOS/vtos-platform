# -*- coding: utf-8 -*-
"""Ghép KHUNG theo vai (SEC-02) với SỐ của bảng bốn mốc (DT-3) — màn hình 01 Tổng quan điều hành.

Hai làn đã dựng sẵn hai nửa mà chưa nửa nào gặp nửa nào:

  * làn Phân quyền có `dong_tien_pham_vi` — vai nào thấy dòng nào, dòng đáy tên gì, ô cảnh báo nào,
    và ai chịu trách nhiệm nhập từng dòng (CF-07);
  * làn Robot A có `dong_tien.bang_bon_moc` — số của bốn mốc lũy kế.

Không có chỗ nào ghép hai nửa ấy, nên màn hình chỉ có hai lựa chọn đều sai: hoặc hiện toàn cảnh cho
mọi vai, hoặc tự lọc ở trình duyệt. Tệp này là chỗ ghép, và nó đứng ở MÁY CHỦ đúng theo SEC-02.

BA ĐIỀU TỆP NÀY GIỮ

1. TẬP DÒNG DO MÁY CHỦ CẮT. Hàm trả về đúng số dòng mà vai ấy được xem. Trình duyệt không nhận dòng
   thừa rồi ẩn đi — dòng nào không được xem thì không rời khỏi máy chủ.

2. DÒNG TỔNG CỘNG TỪ TẬP CỦA CHÍNH VAI ẤY. Cộng toàn cảnh rồi mới che bớt thì con số tổng vẫn mang
   phần đã bị che: cộng mắt các dòng ra một số, dòng tổng in ra một số khác.

3. RỖNG KHÁC KHÔNG. Dòng chưa có nguồn trả `None` kèm tên bộ phận phải nhập, không trả 0. Và khi
   trong tập dòng của vai ấy còn một dòng rỗng thì dòng tổng cũng rỗng — cộng chín dòng có số rồi
   bỏ qua một dòng trống là ra con số đẹp hơn thực tế.

MỘT VIỆC CÒN NỢ, ghi ra đây chứ không giấu: hai làn đặt MÃ DÒNG khác nhau cho cùng một dòng
("thu_cong_no_khac" ở làn Phân quyền là "thu_cong_no" ở làn Robot A, và ba dòng nữa như thế). Bảng
`MA_SEC_SANG_DT` dưới đây là cây cầu tạm. Cầu tạm nào cũng là chỗ một hôm nào đó thêm dòng ở một
bên mà quên bên kia — nên `thieu_cau()` liệt kê ngay dòng nào chưa bắc được cầu, và phép thử canh
cho danh sách ấy rỗng.
"""
from __future__ import annotations

from app.services import dong_tien_pham_vi as SEC
from app.services.lam_tron_tien import lam_tron

# Mã dòng của làn Phân quyền  ->  mã dòng của bảng bốn mốc (làn Robot A).
MA_SEC_SANG_DT = {
    "thu_khach": "thu_khach",
    "thu_cong_no_khac": "thu_cong_no",
    "giai_ngan_vay": "giai_ngan_vay",
    "tra_ncc": "tra_ncc",
    "hoan_tra_khach": "hoan_khach",
    "hoa_hong": "hoa_hong",
    "tra_goc_vay": "tra_goc_vay",
    "lai_phi_ngan_hang": "lai_phi_vay",
    "luong_bhxh": "luong_bhxh",
    "thue_nghia_vu": "thue",
    "van_hanh": "van_hanh",
}

# Hai dòng ghi nhớ không nằm trong bảng bốn mốc: chúng là MỘT số tại ngày đối soát, không phải một
# số cho mỗi mốc. Trải một con số ra bốn cột trông như bốn số đo được — thực ra là một số chép bốn
# lần, và người đọc sẽ so bốn cột với nhau.
GHI_NHO_SANG_DT = {
    "ghi_nho_thu_ho": "tien_thu_ho_khach",
    "ghi_nho_ky_quy": "ky_quy_giay_phep_lu_hanh",
}

# Dòng tự tính — không lấy số từ đâu, do chính hàm này cộng ra.
TU_TINH = ("tong_thu", "tong_chi", "so_du_du_kien_cuoi_khoang", "thieu_so_voi_muc_du_phong")


def thieu_cau() -> list[str]:
    """Dòng của bảng v1.1 chưa bắc được cầu sang bảng bốn mốc. Danh sách này phải RỖNG."""
    return [d.ma for d in SEC.CAC_DONG
            if d.ma not in TU_TINH
            and d.ma not in MA_SEC_SANG_DT
            and d.ma not in GHI_NHO_SANG_DT
            and d.ma != "tien_kha_dung_dau_ky"]


def _cua(ma: str) -> dict:
    """Cửa nhập của một dòng (CF-07). Dòng tự tính không có cửa — gõ đè lên một kết quả tính được
    là chỗ số liệu bắt đầu nói khác sổ."""
    if ma in TU_TINH:
        return {"tu_tinh": True}
    c = SEC.CUA_NHAP.get(ma)
    if c is None:
        return {"tu_tinh": False, "thieu_khai_cua": True}
    return {"tu_tinh": False, "nguon": c.nguon, "cua": c.cua, "bo_phan": c.bo_phan,
            "da_co_nguon": c.da_co_nguon(), "cua_do_de_xuat": c.tu_de_xuat}


def ghep(vai_tro: str, bang: dict, so_du_ngay: dict | None = None) -> dict:
    """Khung của `vai_tro` đã điền số từ `bang` (kết quả bang_bon_moc) — KHÔNG chạm cơ sở dữ liệu.

    Tách khỏi tầng đường dẫn để phép thử gọi thẳng bằng một bảng dựng tay: một hàm phải mở cả cơ sở
    dữ liệu mới thử được là một hàm hiếm khi được thử đủ nhánh.
    """
    khung = SEC.khung_bang(vai_tro)
    if not khung.get("xem_duoc"):
        return {"xem_duoc": False, "ly_do": khung.get("ly_do", "")}

    cot = [c["ma"] for c in bang.get("cot", [])]
    so_theo_ma = {d["ma"]: d for d in bang.get("dong", [])}
    ghi_nho = bang.get("ghi_nho") or {}
    dau_ky = bang.get("tien_kha_dung_dau_ky")
    sdn = so_du_ngay or {}

    dong: list[dict] = []
    for d in khung["dong"]:
        ma = d["ma"]
        o: dict = {"ma": ma, "ten": d["ten"], "phia": d["phia"], **_cua(ma)}

        if ma == "tien_kha_dung_dau_ky":
            o["mot_moc"] = True
            o["so_mot_moc"] = dau_ky
            o["vi_sao_rong"] = "" if dau_ky is not None else (
                "Chưa ai chốt số dư đã đối soát — mở cửa Chốt số dư ở màn hình Dòng tiền.")
        elif ma in GHI_NHO_SANG_DT:
            v = ghi_nho.get(GHI_NHO_SANG_DT[ma])
            o["mot_moc"] = True
            o["so_mot_moc"] = v
            o["vi_sao_rong"] = "" if v is not None else "Chưa có nguồn cho dòng ghi nhớ này."
        elif ma in MA_SEC_SANG_DT:
            g = so_theo_ma.get(MA_SEC_SANG_DT[ma], {})
            o["so"] = {c: (g.get("so") or {}).get(c) for c in cot}
            o["chua_co_nguon"] = bool(g.get("chua_co_nguon"))
            if g.get("chua_co_nguon"):
                o["bo_phan_chiu_trach_nhiem"] = g.get("bo_phan_chiu_trach_nhiem") or ""
        dong.append(o)

    # ---- dòng tự tính, cộng TỪ TẬP DÒNG CỦA CHÍNH VAI NÀY ----
    lay = {o["ma"]: o for o in dong}

    def _cong(ma_cac_dong: list[str]) -> tuple[dict, list[str]]:
        tong: dict = {}
        rong: list[str] = []
        for ma in ma_cac_dong:
            o = lay.get(ma)
            if o is None or o.get("chua_co_nguon"):
                rong.append(o["ten"] if o else ma)
        for c in cot:
            if rong:
                tong[c] = None
                continue
            tong[c] = sum(lam_tron((lay[m].get("so") or {}).get(c) or 0) for m in ma_cac_dong)
        return tong, rong

    thu, rong_thu = _cong(khung["cong_thu"])
    chi, rong_chi = _cong(khung["cong_chi"])
    _dat(lay, "tong_thu", thu, rong_thu)
    _dat(lay, "tong_chi", chi, rong_chi)

    thuan = {c: (None if thu[c] is None or chi[c] is None else thu[c] - chi[c]) for c in cot}

    so_du: dict = {}
    if "so_du_du_kien_cuoi_khoang" in lay:
        for c in cot:
            so_du[c] = None if (thuan[c] is None or dau_ky is None) else lam_tron(dau_ky) + thuan[c]
        _dat(lay, "so_du_du_kien_cuoi_khoang", so_du,
             (rong_thu + rong_chi) or ([] if dau_ky is not None else ["Tiền khả dụng đầu kỳ"]))

    if "thieu_so_voi_muc_du_phong" in lay:
        muc = sdn.get("muc_du_phong")
        thieu: dict = {}
        for c in cot:
            if muc is None or so_du.get(c) is None:
                thieu[c] = None
            else:
                thieu[c] = max(0, lam_tron(muc) - so_du[c])
        _dat(lay, "thieu_so_voi_muc_du_phong", thieu,
             [] if muc is not None else [sdn.get("vi_sao_chua_co_nguong")
                                         or "Chưa chốt mức dự phòng (tham số hai chữ ký)"])

    return {
        "xem_duoc": True,
        "vai_tro": vai_tro,
        "muc_xem": khung["muc_xem"],
        "cau_pham_vi": khung["cau_pham_vi"],
        "ten_dong_day": khung["ten_dong_day"],
        "cot": bang.get("cot", []),
        "dong": dong,
        "dong_tien_thuan": thuan,
        "ten_dong_thuan": ("Dòng tiền thuần trong khoảng" if khung["muc_xem"] == SEC.TOAN_CANH
                           else khung["ten_dong_day"]),
        "canh_bao": _canh_bao(khung["canh_bao"], sdn),
        "cong_bon_cot_la_sai": bang.get("cong_bon_cot_la_sai", ""),
        "vi_sao_khong_co_so_cuoi": bang.get("vi_sao_khong_co_so_cuoi", ""),
        "phap_nhan": bang.get("phap_nhan"),
        "hom_nay": bang.get("hom_nay"),
        "doi_soat_den_ngay": bang.get("doi_soat_den_ngay"),
    }


def _dat(lay: dict, ma: str, so: dict, rong: list) -> None:
    o = lay.get(ma)
    if o is None:
        return
    o["so"] = so
    o["chua_co_nguon"] = bool(rong)
    if rong:
        o["vi_sao_rong"] = ("Còn dòng chưa có nguồn nên không cộng được: "
                            + "; ".join(str(x) for x in rong))


# Hai ô cảnh báo lấy được số ngay từ đường số dư từng ngày; hai ô kia đợi sổ nghĩa vụ (VPM-11) nối
# vào. Ô chưa nối KHÔNG hiện 0 và cũng không biến mất khỏi màn hình: nó ở lại, mang tên bộ phận phải
# nối nguồn. Một ô biến mất là một việc không ai nhớ nữa.
CHO_NOI = {
    "phai_tra_qua_han": ("Sổ nghĩa vụ thanh toán (VPM-11) chưa nối vào ô cảnh báo", "Kế toán"),
    "phai_tra_7_ngay": ("Sổ nghĩa vụ thanh toán (VPM-11) chưa nối vào ô cảnh báo", "Kế toán"),
}


def _canh_bao(cac_o: list[dict], sdn: dict) -> list[dict]:
    ve_duoc = bool(sdn.get("ngay"))
    ra = []
    for o in cac_o:
        ma, nhan = o["ma"], o["nhan"]
        m: dict = {"ma": ma, "nhan": nhan, "kieu": "tien", "gia_tri": None, "vi_sao": ""}
        if ma in CHO_NOI:
            m["vi_sao"], m["bo_phan"] = CHO_NOI[ma]
        elif ma == "ngay_dau_thieu_tien":
            m["kieu"] = "ngay"
            if not ve_duoc:
                m["vi_sao"] = sdn.get("vi_sao_khong_ve_duoc") or "Chưa dựng được đường số dư."
            else:
                m["gia_tri"] = sdn.get("ngay_dau_thieu_tien")
                m["vi_sao"] = "" if m["gia_tri"] else "Không có ngày nào dự kiến thiếu tiền."
        elif ma == "muc_thieu_lon_nhat":
            if not ve_duoc:
                m["vi_sao"] = sdn.get("vi_sao_khong_ve_duoc") or "Chưa dựng được đường số dư."
            else:
                m["gia_tri"] = sdn.get("muc_thieu_lon_nhat")
                m["vi_sao"] = "" if m["gia_tri"] else "Không có ngày nào hụt so với mức dự phòng."
        ra.append(m)
    return ra
