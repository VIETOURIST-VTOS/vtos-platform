# -*- coding: utf-8 -*-
"""DT-3 · DỰNG BẢNG DÒNG TIỀN BỐN MỐC – nối khung trình bày vào sổ nghĩa vụ thanh toán.

Ba tệp, ba việc, và tệp này là chỗ chúng gặp nhau:

    models/nghia_vu.py + services/nghia_vu.py   (VPM-11)  – SỔ: một nghĩa vụ một dòng, và phép
                                                            cộng đã lọc theo vai trò
    services/dong_tien_ky.py       (làn Phân quyền)       – KỲ: bốn mốc, luỹ kế, quá hạn, số dư
    services/dong_tien_pham_vi.py  (làn Phân quyền)       – KHUNG: ai thấy dòng nào, dòng đáy tên gì

Tệp này KHÔNG tự cộng tiền và KHÔNG tự khai quyền. Nó gọi `NV.cong()` của VPM-11 cho từng mốc,
rồi đổ kết quả vào khung của `dong_tien_pham_vi`. Tự cộng lấy là dựng lại đúng chỗ đếm trùng mà
sổ nghĩa vụ sinh ra để diệt.

────────────────────────────────────────────────────────────────────────────────────────────────
LUỸ KẾ ĐẾN TỪ KHOẢNG NGÀY, KHÔNG ĐẾN TỪ PHÉP CỘNG CÁC CỘT
────────────────────────────────────────────────────────────────────────────────────────────────
Cột "1 tháng" KHÔNG phải là cột "2 tuần" cộng thêm phần đuôi. Nó là `cong(hôm nay → hết 1 tháng)`
gọi lại từ đầu. Cộng dồn cột trước vào cột sau thì mỗi lần làm tròn một cột là một lần sai số
được nhân lên, và một khoản bị xếp nhầm cột sẽ sai ở mọi cột từ đó về sau.

────────────────────────────────────────────────────────────────────────────────────────────────
QUÁ HẠN: CHI CỘNG VÀO MỌI CỘT, THU KHÔNG CỘNG VÀO CỘT NÀO
────────────────────────────────────────────────────────────────────────────────────────────────
`NV.cong()` bắt đầu từ HÔM NAY nên khoản quá hạn nằm ngoài mọi cột của nó. Tệp này lấy khoản quá
hạn bằng chính hàm ấy với khoảng (rất xa → hôm qua), rồi cộng vào theo luật `dong_tien_ky.luy_ke`:

    CHI quá hạn → cộng vào MỌI cột. Nó là tiền đang phải trả, không thuộc riêng cột nào.
    THU quá hạn → KHÔNG cộng vào cột nào. Tiền ra thì mình quyết, tiền vào thì không; mặc định
                  rằng một khoản phải thu quá hạn sẽ thu được ngay là cách làm bảng đẹp hơn sự thật.

Lấy quá hạn qua `NV.cong()` chứ không qua `NV.ba_ro()["qua_han"]`: rổ ấy trả một TỔNG chung cho
cả hai hướng và danh sách chi tiết CẮT CÒN 200 DÒNG. Tách lại từ 200 dòng ấy thì công ty có
201 khoản quá hạn là bảng bắt đầu thiếu tiền mà không ai biết.

────────────────────────────────────────────────────────────────────────────────────────────────
HAI TÊN CHO MỘT CƠ SỞ NGÀY – CHỖ NÀY PHẢI DỊCH TAY, VÀ PHẢI CANH
────────────────────────────────────────────────────────────────────────────────────────────────
`dong_tien_ky` gọi hai cơ sở ngày là "cam_ket" và "thuc_hien"; `NV.cong()` gọi là "cam_ket" và
"du_kien". Nguy hiểm ở chỗ hàm của họ viết `if co_so_ngay == "cam_ket" ... else ngày dự kiến` –
tức MỌI chuỗi lạ, kể cả "thuc_hien" và kể cả một lỗi gõ, đều rơi êm vào nhánh ngày dự kiến và
CHẠY ĐÚNG MỘT NỬA thời gian. Nên ở đây dịch bằng một từ điển đóng, và chuỗi lạ thì NÉM LỖI.
"""
from datetime import date, timedelta

from sqlalchemy import func, select

from app.models.nghia_vu import NHOM, TRANG_THAI_DONG, NghiaVuThanhToan
from app.services import dong_tien_ky as KY
from app.services import dong_tien_pham_vi as PV
from app.services import lam_tron_tien as LT
from app.services import nghia_vu as NV

# Ngày mở sổ giả định – chỉ để làm cận dưới cho khoảng "quá hạn". Lấy một mốc xa hẳn chứ không
# lấy date.min: một số trình điều khiển cơ sở dữ liệu không so sánh được năm 1.
NGAY_MO_SO = date(2000, 1, 1)

# Dịch tên cơ sở ngày. Đóng, không có giá trị mặc định – xem lý lẽ ở đầu tệp.
CO_SO_SANG_VPM = {KY.CAM_KET: "cam_ket", KY.THUC_HIEN: "du_kien"}


def _co_so_vpm(co_so: str) -> str:
    if co_so not in CO_SO_SANG_VPM:
        raise ValueError(
            f"Cơ sở ngày '{co_so}' không hợp lệ. Hai giá trị: "
            f"'{KY.CAM_KET}' (nghĩa vụ đến hạn) hoặc '{KY.THUC_HIEN}' (kế hoạch thực thu–chi).")
    return CO_SO_SANG_VPM[co_so]


def _huong(ma_dong: str) -> str:
    """Hướng của một dòng, đọc từ SỔ chứ không đoán theo phía trên bảng."""
    return NHOM[ma_dong][0] if ma_dong in NHOM else ""


# =============================================================================================
# Lý do một ô KHÔNG có số. Mỗi lý do phải nói được người đọc cần làm gì tiếp.
# =============================================================================================
KHONG_CO_SO = {
    "ngoai_pham_vi": "Dòng này không thuộc phạm vi xem của bạn.",
    "chua_tach_pham_vi": PV.CAU_CHUA_TACH,
    "chua_co_cua_nhap": "Chưa có cửa nhập cho dòng này – số chưa vào được hệ thống.",
    "thieu_so_dau_ky": "Chưa chốt tiền được phép sử dụng đầu kỳ, nên chưa tính được số dư.",
    "khong_thuoc_muc_xem": "Dòng số dư chỉ có trên bảng toàn cảnh.",
}


def _o_trong(ly_do: str) -> dict:
    """Ô không có số. KHÔNG trả khoá "so" – để bên nhận không viết được `o["so"] or 0`.

    Đây là cùng một hàng rào đã dựng ở `tien_duoc_phep_su_dung()`: thiếu dữ liệu thì không đưa ra
    một con số, và cũng không đưa ra một chỗ để người khác điền 0 vào thay mình.
    """
    return {"co_so": False, "ly_do": ly_do, "hien": KHONG_CO_SO.get(ly_do, ly_do)}


def _o(x) -> dict:
    o = LT.o_tien(x)
    o["co_so"] = True
    return o


# =============================================================================================
# Đọc sổ cho một mốc
# =============================================================================================
def doc_mot_moc(db, vai_tro: str, ma_moc: str, *, hom_nay: date,
                co_so: str = KY.CAM_KET, company_id: int | None = None,
                loai_tien: str = "VND", qua_han: dict | None = None) -> dict:
    """Số theo nhóm cho MỘT cột, đã gồm phần quá hạn theo đúng luật THU/CHI.

    `qua_han` truyền vào từ ngoài để bốn cột dùng CHUNG một lần đọc – đọc lại bốn lần vừa tốn vừa
    mở đường cho bốn kết quả khác nhau nếu có ai ghi sổ xen giữa.
    """
    _tu, den = KY.khoang(hom_nay, ma_moc)
    trong = NV.cong(db, hom_nay, den, co_so_ngay=_co_so_vpm(co_so),
                    company_id=company_id, loai_tien=loai_tien, vai_tro=vai_tro)
    qh = qua_han if qua_han is not None else {}
    ra = dict(trong)
    for nhom, tien in qh.items():
        # Luật nằm ở dong_tien_ky, không chép lại ở đây.
        if ma_moc in KY.luy_ke(KY.QUA_HAN, _huong(nhom)):
            ra[nhom] = ra.get(nhom, 0.0) + tien
    return _sang_ma_dong(ra)


def _sang_ma_dong(theo_nhom: dict) -> dict:
    """Đổi khoá từ tiếng của SỔ sang tiếng của BẢNG. MỘT chỗ dịch, đặt ngay sau chỗ đọc sổ.

    Mọi hàm phía dưới tra số bằng MÃ DÒNG (`d["ma"]`, `khung["cong_thu"]`), còn `NV.cong()` trả về
    theo MÃ NHÓM. Bảy cặp tên khác nhau – xem `dong_tien_pham_vi.Dong`. Không dịch thì
    `.get(ma, 0.0)` trả 0.0 cho bảy dòng chi, và bảng in ra một con số ĐẸP HƠN SỰ THẬT mà không
    dòng nào báo.

    Nhóm KHÔNG có dòng nào nhận (nhóm mới của sổ, chưa lên bảng) thì GIỮ NGUYÊN tên, không vứt đi:
    nó phải còn đó cho `day_du()` / `nhom_chua_phan_loai` nhìn thấy và tự khai là báo cáo chưa đủ.
    Vứt lặng lẽ một nhóm là bỏ sót tiền.
    """
    return {PV.NHOM_SANG_MA.get(k, k): v for k, v in theo_nhom.items()}


def doc_qua_han(db, vai_tro: str, *, hom_nay: date, co_so: str = KY.CAM_KET,
                company_id: int | None = None, loai_tien: str = "VND") -> dict:
    """Khoản đã đến hạn TRƯỚC hôm nay, theo nhóm. Dùng chính phép cộng của sổ."""
    return NV.cong(db, NGAY_MO_SO, hom_nay - timedelta(days=1),
                   co_so_ngay=_co_so_vpm(co_so), company_id=company_id,
                   loai_tien=loai_tien, vai_tro=vai_tro)


# =============================================================================================
# Dựng cả bảng
# =============================================================================================
def bang(db, vai_tro: str, *, hom_nay: date | None = None, co_so: str = KY.CAM_KET,
         company_id: int | None = None, loai_tien: str = "VND",
         dau_ky=None, nhom_chua_phan_loai: list[str] | None = None) -> dict:
    """Bảng dòng tiền bốn mốc cho MỘT vai trò, MỘT pháp nhân, MỘT cơ sở ngày.

    `dau_ky` là chỉ tiêu A – TIỀN ĐƯỢC PHÉP SỬ DỤNG, CHƯA trừ lệnh chi đã duyệt. Truyền chỉ tiêu B
    vào đây là đưa lại đúng lỗi trừ hai lần đã sửa ngày 13/9; `tien_con_bo_tri_moi()` mang sẵn cờ
    `dung_lam_dau_ky=False` và hàm này kiểm cờ ấy.

    Ba tham số `vai_tro`, `company_id`, `loai_tien` đi THẲNG xuống `NV.cong()`. Không có chỗ nào
    trong tệp này đọc sổ mà bỏ qua chúng – phép thử canh đúng điều đó.
    """
    hom_nay = hom_nay or date.today()
    khung = PV.khung_bang(vai_tro, nhom_chua_phan_loai)
    if not khung["xem_duoc"]:
        return khung

    if isinstance(dau_ky, dict) and dau_ky.get("dung_lam_dau_ky") is False:
        raise ValueError(
            "Số đầu kỳ phải là chỉ tiêu A (Tiền được phép sử dụng, CHƯA trừ lệnh chi). "
            "Đang nhận chỉ tiêu B (Tiền còn có thể bố trí mới) – dùng B làm đầu kỳ là trừ lệnh chi "
            "hai lần, vì bảng dự báo dưới đây đọc lại chính các lệnh chi ấy từ sổ nghĩa vụ.")

    qh = doc_qua_han(db, vai_tro, hom_nay=hom_nay, co_so=co_so,
                     company_id=company_id, loai_tien=loai_tien)
    theo_moc = {ma: doc_mot_moc(db, vai_tro, ma, hom_nay=hom_nay, co_so=co_so,
                                company_id=company_id, loai_tien=loai_tien, qua_han=qh)
                for ma in KY.MA_MOC}

    cot = KY.cac_khoang(hom_nay)
    dong = []
    for d in khung["dong"]:
        dong.append({**d, "o": _o_mot_dong(d, khung, theo_moc, dau_ky, hom_nay)})

    ra = {
        **khung,
        "dong": dong,
        "cot": cot,
        "co_so_ngay": co_so,
        "nhan_co_so": KY.CO_SO_NGAY[co_so]["nhan"],
        "nhan_so_du": KY.nhan_so_du(co_so),
        "hom_nay": hom_nay,
        "qua_han_theo_nhom": {k: LT.o_tien(v) for k, v in qh.items()},
        "canh_bao_pham_vi": nhom_mat_vi_chua_ro_phap_nhan(
            db, company_id=company_id, hom_nay=hom_nay, co_so=co_so, loai_tien=loai_tien),
        "ba_ro": NV.ba_ro(db, KY.khoang(hom_nay, KY.MA_MOC[-1])[1], co_so_ngay=_co_so_vpm(co_so),
                          company_id=company_id, loai_tien=loai_tien, hom_nay=hom_nay,
                          vai_tro=vai_tro),
    }
    return ra


def nhom_mat_vi_chua_ro_phap_nhan(db, *, company_id: int | None, hom_nay: date,
                                  co_so: str = KY.CAM_KET, loai_tien: str = "VND") -> dict:
    """Nghĩa vụ RƠI RA NGOÀI bảng của một pháp nhân vì chưa biết nó của pháp nhân nào.

    ĐO ĐƯỢC 13/9/2026, và đây là một lỗ thật:
        `cash_plan_items` KHÔNG CÓ cột `company_id`. Bộ nạp của VPM-11 viết
        `getattr(it, "company_id", None)`, nên MỌI nghĩa vụ sinh từ bảng ấy vào sổ với pháp nhân
        RỖNG. Mà `_loc()` lọc `company_id == <id>`, nên rỗng thì bị loại.

    `cash_plan_items` lại là NGUỒN DUY NHẤT của ba nhóm: lương–bảo hiểm, thuế, và thu công nợ khác.
    Hệ quả: bảng của TỪNG pháp nhân mất sạch ba nhóm ấy, còn bảng toàn tập đoàn thì vẫn đủ. Không
    ô nào báo đỏ, không dòng nào trống – ba dòng chỉ đơn giản bằng 0, và 0 đọc là "kỳ này không
    phải trả lương".

    Hàm này không vá được cái lỗ (cột thiếu nằm ở bảng của làn khác), nhưng nó KHÔNG ĐỂ LỖ ẤY IM
    LẶNG: bảng nào lọc theo pháp nhân đều mang theo con số đang rơi ra ngoài, kèm tên nhóm.

    Bảng toàn tập đoàn (`company_id=None`) không lọc nên không mất gì – trả rỗng.
    """
    if company_id is None:
        return {"co_khoan_roi_ra_ngoai": False, "theo_nhom": {}, "tong": 0, "cau": ""}

    cot = (NghiaVuThanhToan.ngay_cam_ket if _co_so_vpm(co_so) == "cam_ket"
           else NghiaVuThanhToan.ngay_du_kien_tra)
    _, den = KY.khoang(hom_nay, KY.MA_MOC[-1])
    q = (select(NghiaVuThanhToan.nhom,
                func.sum(NghiaVuThanhToan.tong_nghia_vu - func.coalesce(NghiaVuThanhToan.da_tra, 0)))
         .where(NghiaVuThanhToan.company_id.is_(None),
                NghiaVuThanhToan.ghi_nho == False,                          # noqa: E712
                NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG),
                NghiaVuThanhToan.loai_tien == loai_tien,
                cot.is_not(None), cot <= den)
         .group_by(NghiaVuThanhToan.nhom))
    theo_nhom = {n: LT.lam_tron(t) for n, t in db.execute(q).all() if (t or 0) > 0}
    if not theo_nhom:
        return {"co_khoan_roi_ra_ngoai": False, "theo_nhom": {}, "tong": 0, "cau": ""}

    ten = ", ".join(NHOM[n][1] for n in sorted(theo_nhom) if n in NHOM)
    tong = sum(theo_nhom.values())
    return {
        "co_khoan_roi_ra_ngoai": True,
        "theo_nhom": {n: LT.o_tien(v) for n, v in theo_nhom.items()},
        "tong": tong,
        "cau": (f"Bảng này ĐANG THIẾU {LT.hien(tong)} đ: {len(theo_nhom)} nhóm nghĩa vụ "
                f"({ten}) chưa xác định thuộc pháp nhân nào nên không vào được bảng của pháp nhân "
                "nào cả. Phần lớn đến từ kế hoạch tiền – bảng ấy chưa có cột pháp nhân."),
    }


def _o_mot_dong(d: dict, khung: dict, theo_moc: dict, dau_ky, hom_nay: date) -> dict:
    """Bốn ô của một dòng. Trả về {mã mốc: ô}."""
    ma = d["ma"]

    if d["an_gia_tri"]:
        return {c: _o_trong("chua_tach_pham_vi") for c in KY.MA_MOC}

    if ma in ("tong_thu", "tong_chi"):
        phia = PV.VAO if ma == "tong_thu" else PV.RA
        de_cong = khung["cong_thu"] if ma == "tong_thu" else khung["cong_chi"]
        ra = {}
        for c in KY.MA_MOC:
            t = LT.cong([theo_moc[c].get(m, 0.0) for m in de_cong])
            t["co_so"] = True
            ra[c] = t
        _ = phia
        return ra

    if d["phia"] == PV.GHI_NHO:
        # Hai dòng ghi nhớ chưa có nguồn nào (đo 13/9). Hiện dòng, không hiện số – chứ không hiện
        # số 0: số 0 ở đây đọc là "công ty không giữ đồng thu hộ nào", một câu khẳng định sai.
        return {c: _o_trong("chua_co_cua_nhap") for c in KY.MA_MOC}

    if d["phia"] == PV.SO_DU:
        return _o_dong_so_du(ma, khung, theo_moc, dau_ky)

    return {c: _o(theo_moc[c].get(ma, 0.0)) for c in KY.MA_MOC}


def _o_dong_so_du(ma: str, khung: dict, theo_moc: dict, dau_ky) -> dict:
    """Ba dòng số dư. Chỉ có trên bảng toàn cảnh, và chỉ khi đã chốt số đầu kỳ.

    Không có số đầu kỳ thì KHÔNG suy ra số dư từ phần chênh lệch thu–chi: một bảng ghi "số dư cuối
    khoảng 1,2 tỷ" mà thực ra chỉ là "thu trừ chi trong khoảng" là một câu nói dối đúng đến từng
    chữ số.
    """
    if khung["muc_xem"] != PV.TOAN_CANH:
        return {c: _o_trong("khong_thuoc_muc_xem") for c in KY.MA_MOC}
    so_dau = _so_dau_ky(dau_ky)
    if so_dau is None:
        return {c: _o_trong("thieu_so_dau_ky") for c in KY.MA_MOC}

    if ma == "tien_kha_dung_dau_ky":
        return {c: _o(so_dau) for c in KY.MA_MOC}

    ra = {}
    for c in KY.MA_MOC:
        thu = LT.cong([theo_moc[c].get(m, 0.0) for m in khung["cong_thu"]])["so_da_tron"]
        chi = LT.cong([theo_moc[c].get(m, 0.0) for m in khung["cong_chi"]])["so_da_tron"]
        cuoi = LT.lam_tron(so_dau) + thu - chi
        if ma == "so_du_du_kien_cuoi_khoang":
            ra[c] = _o(cuoi)
        else:
            # thieu_so_voi_muc_du_phong – ngưỡng do hai chữ ký đặt, tầng gọi truyền xuống. Chưa có
            # ngưỡng thì không có "thiếu", và cũng không mặc định ngưỡng bằng 0.
            ra[c] = _o_trong("thieu_so_dau_ky") if khung.get("nguong") is None else \
                _o(max(0, khung["nguong"] - cuoi))
    return ra


def _so_dau_ky(dau_ky):
    """Rút số ra khỏi chỉ tiêu A. Rỗng, hoặc A chưa tính được, đều trả None – không trả 0."""
    if dau_ky is None:
        return None
    if isinstance(dau_ky, dict):
        return dau_ky.get("so")       # tien_duoc_phep_su_dung() KHÔNG trả khoá "so" khi chưa đủ
    return dau_ky


def kiem_khong_doc_so_khi_thieu_vai_tro(nguon: str | None = None) -> list[str]:
    """Mọi lần gọi NV.cong()/NV.ba_ro() trong tệp này phải truyền vai_tro. Danh sách phải RỖNG.

    `_loc()` của VPM-11 viết rõ: `vai_tro` rỗng nghĩa là người gọi ở TRONG máy chủ và KHÔNG lọc
    theo nhóm. Quên một chỗ là chỗ ấy trả về CẢ SỔ, và không có gì trên màn hình cho thấy điều đó –
    bảng của Tổng giám đốc vẫn đủ dòng, chỉ là mỗi dòng mang số của toàn tập đoàn.

    Đọc CÂY CÚ PHÁP chứ không dò chuỗi: bản đầu của hàm này viết bằng biểu thức chính quy và bắt
    nhầm cả chữ "NV.cong()" nằm trong chú thích, tức nó báo đỏ ở chỗ không có lỗi và sẽ bị người
    ta tắt đi. Một hàm canh kêu oan là một hàm canh sắp bị gỡ.

    `nguon` cho phép soi một đoạn mã bất kỳ thay vì tệp này. Có tham số ấy thì phép thử chứng minh
    được hàm canh CÓ KÊU khi đáng kêu – không có nó thì một hàm canh bị làm cho câm vẫn trả về
    danh sách rỗng, và phép thử vẫn xanh y như khi mọi thứ đều đúng.
    """
    import ast
    import inspect
    cay = ast.parse(nguon if nguon is not None
                    else inspect.getsource(inspect.getmodule(bang)))
    thieu = []
    for n in ast.walk(cay):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "NV"
                and n.func.attr in ("cong", "ba_ro")
                and not any(k.arg == "vai_tro" for k in n.keywords)):
            thieu.append(f"NV.{n.func.attr}() dòng {n.lineno}")
    return sorted(thieu)
