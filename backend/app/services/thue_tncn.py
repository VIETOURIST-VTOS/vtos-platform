"""Thuế thu nhập cá nhân lũy tiến từng phần — PHÉP TÍNH, và cái công tắc không nằm trong mã.

CĂN CỨ (tra ngày 08/10/2026, trước khi viết một dòng nào):
  · Luật Thuế thu nhập cá nhân 2025, số 109/2025/QH15 — hiệu lực 01/7/2026; phần thu nhập từ tiền
    lương, tiền công của cá nhân cư trú áp dụng TỪ KỲ TÍNH THUẾ NĂM 2026. Biểu lũy tiến rút từ
    bảy bậc xuống NĂM bậc.
  · Nghị quyết 110/2025/UBTVQH15 — giảm trừ gia cảnh: bản thân 15.500.000 đ/tháng, mỗi người phụ
    thuộc 6.200.000 đ/tháng, áp dụng từ kỳ tính thuế năm 2026. Mức cũ 11.000.000 / 4.400.000 theo
    NQ 954/2020/UBTVQH14 — VTOS vẫn đang mang mức cũ trong bảng tham số.

VÌ SAO TỆP NÀY KHÔNG TỰ BẬT. Trước bản này VTOS cộng TNCN đúng MỘT chỗ — 10% khấu trừ thù lao
cộng tác viên — còn người hợp đồng lao động đi qua bảng lương với cột TNCN bằng 0. Chủ tịch quyết
ngày 08/10/2026: "VTOS tính", áp dụng từ kỳ tới, cân đối khi quyết toán năm. Phép tính thì viết
được ngay; CÁI KHÔNG viết được bằng mã là lúc bật.

Lý do rất cụ thể, không phải sự dè dặt: thuế lũy tiến của người HĐLĐ CÓ THỂ ĐANG ĐƯỢC TÍNH Ở MISA.
Ngày VTOS bắt đầu trừ mà MISA chưa dừng thì cùng một khoản thuế bị trừ hai lần, và người lao động
là người phát hiện ra — vào ngày nhận lương. Nên bật là một việc có bàn giao, không phải một lần
sửa mã cho tiện. Công tắc là tham số `tncn_luy_tien_tu_ky`, ĐỂ TRỐNG trong bộ mặc định, mở bằng
hai chữ ký ở màn hình Tham số — đúng khuôn `ngay_van_hanh_that` và `ngay_du_lieu_that_vietrip`
đang để trống vì cùng một lẽ: điền sẵn một ngày vào đó là ký thay Chủ tịch bằng một dòng mã.

Chưa bật thì tệp này vẫn chạy, nhưng chỉ để TRẢ LỜI MỘT CÂU: bật thì mỗi người bị trừ bao nhiêu,
cả công ty bao nhiêu (`thu_neu_bat`). Quyết định lúc ấy có con số trong tay chứ không quyết mò.
"""
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr import Employee
from app.models.hrm import CONTRACT_KINDS
from app.services import rules as R
from app.services.thu_nhap_su_kien import LOAI_KHOAN

CAN_CU_BIEU = "Luật Thuế TNCN 2025 (109/2025/QH15), biểu lũy tiến 5 bậc, áp dụng từ kỳ tính thuế 2026"
CAN_CU_GIAM_TRU = "Nghị quyết 110/2025/UBTVQH15 – giảm trừ gia cảnh từ kỳ tính thuế 2026"
KY_TU_KY_KEY = "tncn_luy_tien_tu_ky"

# Biểu lũy tiến từng phần: (TRẦN thu nhập tính thuế của bậc theo THÁNG, thuế suất). None = bậc cuối.
# Để trong mã chứ không để trong tham số là có chủ ý: đây là BIỂU THUẾ CỦA LUẬT, đổi nó là đổi theo
# một đạo luật mới — việc ấy phải đi kèm người đọc lại luật và sửa cả phép thử mốc ở `test_ky1`,
# không phải một ô cho ai đó gõ đè. Mức GIẢM TRỪ thì ngược lại: Nhà nước nâng theo nghị quyết nhiều
# lần hơn và Kế toán phải chỉnh được, nên nó nằm trong bảng tham số.
BAC_THUE: tuple[tuple[float | None, float], ...] = (
    (10_000_000.0, 0.05),
    (30_000_000.0, 0.10),
    (60_000_000.0, 0.20),
    (100_000_000.0, 0.30),
    (None, 0.35),
)

# Khoản thu nhập KHÔNG tính vào thu nhập chịu thuế. Phân loại dựng TỪ `LOAI_KHOAN`, và phép thử
# `test_moi_loai_khoan_deu_duoc_xep_loai` bắt buộc ba túi dưới đây phủ kín nó — nên ngày ai đó thêm
# một loại khoản mới, phép thử đỏ và người thêm phải nói loại ấy có chịu thuế hay không. Mặc định
# im lặng "cứ coi là chịu thuế" thì một khoản miễn thuế sẽ bị trừ thuế mà không ai biết.
MIEN_THUE = {
    "cong_tac_phi_tx": "Công tác phí theo lệnh điều xe – phần khoán theo quy chế, không tính vào "
                       "thu nhập chịu thuế TNCN",
}
# Khoản đã khấu trừ theo cách KHÁC (10% thù lao cộng tác viên) – không đi vào biểu lũy tiến, nếu
# không thì một khoản bị tính thuế hai lần bằng hai cách.
KHAU_TRU_RIENG = {
    "thu_lao_hdv": "Thù lao HDV cộng tác viên – đã khấu trừ 10% ở services/hr.py",
}
CHIU_THUE = {k: v for k, v in LOAI_KHOAN.items() if k not in MIEN_THUE and k not in KHAU_TRU_RIENG}

# Cách khấu trừ theo loại hợp đồng. Luật: người ký HĐLĐ từ ba tháng trở lên tính theo biểu lũy tiến;
# người không ký hợp đồng hoặc ký dưới ba tháng thì khấu trừ 10% trên mỗi lần trả từ 2 triệu.
LUY_TIEN = "luy_tien"
KHAU_TRU_10 = "khau_tru_10"
CACH_THEO_LOAI_HD: dict[str, str] = {
    "xac_dinh_12": LUY_TIEN,
    "xac_dinh_36": LUY_TIEN,
    "khong_xac_dinh": LUY_TIEN,
    "thu_viec": KHAU_TRU_10,     # mặc định; `cach_khau_tru` đo ĐỘ DÀI hợp đồng thật nếu có ngày
    "ctv": KHAU_TRU_10,
    "khoan": KHAU_TRU_10,
}
CHUA_CO_HOP_DONG = "chua_co_hop_dong"


def thue_thang(tntt: float) -> dict:
    """Thuế của MỘT tháng từ thu nhập tính thuế, kèm phần ăn của từng bậc.

    Trả cả phần chia theo bậc chứ không chỉ một con số: người bị trừ tiền có quyền thấy vì sao, và
    một con số trần trụi thì không ai đối chiếu được với tờ khai. `tntt` âm hoặc 0 → thuế 0.
    """
    con = max(0.0, float(tntt or 0))
    tong, bac, duoi = 0.0, [], 0.0
    for tran, suat in BAC_THUE:
        if con <= 0:
            break
        rong = (tran - duoi) if tran is not None else con
        phan = min(con, rong)
        tien = phan * suat
        bac.append({"tu": duoi, "den": tran, "suat": suat, "phan": round(phan), "tien": round(tien)})
        tong += tien
        con -= phan
        duoi = tran if tran is not None else duoi
    return {"tntt": round(max(0.0, float(tntt or 0))), "thue": round(tong), "bac": bac,
            "can_cu": CAN_CU_BIEU}


def cach_khau_tru(db: Session, employee_id: int, on: date) -> tuple[str, str]:
    """(cách, lý do) cho một người tại một ngày. Không có hợp đồng hiệu lực thì KHÔNG đoán."""
    from app.services import hrm as H
    c = H.active_contract(db, employee_id, on)
    if c is None:
        return CHUA_CO_HOP_DONG, "không có hợp đồng lao động hiệu lực trong kỳ – chưa xác định được cách khấu trừ"
    kind = c.kind or ""
    ten = CONTRACT_KINDS.get(kind, {}).get("ten", kind)
    if kind == "thu_viec" and c.effective_from and c.effective_to:
        thang = (c.effective_to.year - c.effective_from.year) * 12 + (c.effective_to.month - c.effective_from.month)
        if thang >= 3:
            return LUY_TIEN, f"{ten} dài {thang} tháng – từ 3 tháng trở lên tính theo biểu lũy tiến"
        return KHAU_TRU_10, f"{ten} dài {thang} tháng – dưới 3 tháng, khấu trừ 10%"
    cach = CACH_THEO_LOAI_HD.get(kind)
    if cach is None:
        return CHUA_CO_HOP_DONG, f"loại hợp đồng '{kind}' chưa được xếp cách khấu trừ"
    return cach, ten


def _cuoi_ky(period: str) -> date:
    y, m = int(period[:4]), int(period[5:7])
    return date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)


def muc_giam_tru(db: Session, period: str) -> dict:
    """Mức giảm trừ ÁP CHO KỲ ẤY, không phải mức của hôm nay.

    Đọc tham số bằng `on=` ngày cuối kỳ: bảng tham số có hiệu lực theo ngày, nên kỳ tháng 7 phải
    đọc mức của tháng 7 kể cả khi hôm nay tháng 10 đã ký mức mới. Trước bản này `pit_deduction()`
    gọi không kèm ngày, tức mọi kỳ cũ đều lấy mức mới nhất — tính lại một kỳ đã qua sẽ ra số khác.
    """
    on = _cuoi_ky(period)
    ban_than = R.get_param(db, "giam_tru_ban_than", on=on)
    npt = R.get_param(db, "giam_tru_nguoi_phu_thuoc", on=on)
    return {"ban_than": ban_than, "nguoi_phu_thuoc": npt, "can_cu": CAN_CU_GIAM_TRU,
            "theo_luat_2026": {"ban_than": 15_500_000.0, "nguoi_phu_thuoc": 6_200_000.0}}


def tham_so_lac_hau(db: Session, period: str) -> list[dict]:
    """Mức giảm trừ đang áp so với mức luật của kỳ tính thuế 2026 — nói ra chênh, KHÔNG tự sửa.

    Tham số có hai chữ ký (Kế toán đề xuất, Chủ tịch / TGĐ ký) và cửa ấy đã có ở màn hình Tham số.
    Một dòng mã đè lên giá trị đang hiệu lực là đi vòng qua đúng cái cửa mà hệ thống dựng ra để
    không ai đổi tiền của người khác một mình. Nên ở đây chỉ đếm chênh.
    """
    if int(period[:4]) < 2026:
        return []
    m = muc_giam_tru(db, period)
    ra = []
    for k, ten, khoa in (("ban_than", "Giảm trừ bản thân", "giam_tru_ban_than"),
                         ("nguoi_phu_thuoc", "Giảm trừ mỗi người phụ thuộc", "giam_tru_nguoi_phu_thuoc")):
        dang, luat = m[k], m["theo_luat_2026"][k]
        if abs(dang - luat) >= 1:
            ra.append({"khoa": khoa, "ten": ten, "dang_ap": dang, "theo_luat": luat,
                       "chenh": round(luat - dang), "can_cu": CAN_CU_GIAM_TRU,
                       "viec_phai_lam": "Kế toán đề xuất ở màn hình Tham số, Chủ tịch hoặc TGĐ ký. "
                                        "Mức cũ làm thuế tạm tính CAO hơn mức phải nộp."})
    return ra


def ky_bat_dau(db: Session) -> str:
    """Kỳ đầu tiên VTOS tự khấu trừ lũy tiến. Rỗng = CHƯA BẬT."""
    try:
        return (R.get_param_text(db, KY_TU_KY_KEY) or "").strip()
    except KeyError:
        return ""


def da_bat(db: Session, period: str) -> bool:
    tu = ky_bat_dau(db)
    return bool(tu) and period >= tu


def tinh_cho_dong(db: Session, period: str, r: dict, e: Employee | None, giam_tru: dict,
                  so_npt: int) -> dict:
    """Thuế lũy tiến tạm tính của MỘT dòng bảng lương. Không sửa `r` — nơi gọi quyết định có ghi hay không.

    Nền thu nhập lấy THẲNG `r["thu_nhap"]` mà bảng lương đã cộng, trừ đi các khoản miễn thuế. Không
    dựng lại một định nghĩa "thu nhập" thứ hai ở đây: hai định nghĩa thu nhập trong cùng một hệ
    thống sẽ lệch nhau ở lần sửa thứ nhất, và lần ấy không ai thấy vì cả hai đều ra số.
    """
    on = _cuoi_ky(period)
    cach, ly_do = (CHUA_CO_HOP_DONG, "không tìm thấy nhân sự") if e is None else cach_khau_tru(db, e.id, on)
    mien = sum(float(k.get("tien") or 0) for k in (r.get("khoan") or [])
               if k.get("loai") in MIEN_THUE and float(k.get("tien") or 0) > 0)
    rieng = sum(float(k.get("tien") or 0) for k in (r.get("khoan") or [])
                if k.get("loai") in KHAU_TRU_RIENG and float(k.get("tien") or 0) > 0)
    chiu_thue = max(0.0, float(r.get("thu_nhap") or 0) - mien - rieng)
    bh = float(r.get("bhxh") or 0)
    gt = giam_tru["ban_than"] + giam_tru["nguoi_phu_thuoc"] * so_npt
    tntt = chiu_thue - bh - gt
    kq = thue_thang(tntt)
    canh = []
    if r.get("thieu_muc_bhxh"):
        canh.append("CHƯA CÓ MỨC ĐÓNG BHXH – chưa trừ bảo hiểm trước khi tính thuế, nên thuế tạm "
                    "tính đang CAO hơn số phải nộp")
    if cach == CHUA_CO_HOP_DONG:
        canh.append(ly_do)
    return {"ma": r.get("ma"), "ho_ten": r.get("ten"), "cach": cach, "cach_ly_do": ly_do,
            "thu_nhap": round(float(r.get("thu_nhap") or 0)), "mien_thue": round(mien),
            "khau_tru_rieng": round(rieng), "thu_nhap_chiu_thue": round(chiu_thue),
            "bao_hiem": round(bh), "so_nguoi_phu_thuoc": so_npt, "giam_tru": round(gt),
            "tntt": kq["tntt"], "thue": kq["thue"] if cach == LUY_TIEN else 0.0,
            "bac": kq["bac"], "canh_bao": canh}


def npt_theo_nguoi(db: Session, period: str) -> dict[int, int]:
    from app.services import hrm as H
    ra: dict[int, int] = {}
    for e in db.execute(select(Employee).where(Employee.active == True)).scalars():
        ra[e.id] = len(H.dependents_of(db, e.id, period))
    return ra


def thu_neu_bat(db: Session, period: str, rows: list[dict] | None) -> dict:
    """Bật lên thì kỳ này khấu trừ bao nhiêu, của bao nhiêu người — trả lời TRƯỚC khi ai bấm.

    Chạy được cả khi chưa bật. Đây là cái làm cho quyết định "có bật không" được quyết bằng con số
    chứ không bằng cảm giác, và cũng là cái cho Kế toán đối chiếu với số MISA đang khấu trừ TRƯỚC
    ngày bàn giao — nếu hai bên lệch nhau thì phải biết lúc này, không phải vào ngày trả lương.
    """
    rows = rows or []
    ma_nv = {e.code: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars()}
    npt = npt_theo_nguoi(db, period)
    gt = muc_giam_tru(db, period)
    dong, tong, chua_hd = [], 0.0, 0
    for r in rows:
        e = ma_nv.get(str(r.get("ma") or ""))
        if e is None or e.contract_type != "hdld":
            continue
        d = tinh_cho_dong(db, period, r, e, gt, npt.get(e.id, 0))
        if d["cach"] == CHUA_CO_HOP_DONG:
            chua_hd += 1
        tong += d["thue"]
        dong.append(d)
    phai_nop = [d for d in dong if d["thue"] > 0]
    return {"period": period, "da_bat": da_bat(db, period), "ky_bat_dau": ky_bat_dau(db),
            "muc_giam_tru": gt, "tham_so_lac_hau": tham_so_lac_hau(db, period),
            "so_nguoi_xet": len(dong), "so_nguoi_phai_nop": len(phai_nop),
            "tong_thue": round(tong), "so_nguoi_chua_co_hop_dong": chua_hd,
            "dong": sorted(dong, key=lambda d: -d["thue"]),
            "ghi_chu": ("Số tạm tính theo tháng. Thuế TNCN quyết toán theo NĂM, nên kỳ bật giữa năm "
                        "không làm sai nghĩa vụ cả năm – phần các kỳ trước cân đối khi quyết toán."
                        if da_bat(db, period) else
                        "CHƯA BẬT – bảng lương chưa khấu trừ số này. Đây là số NẾU bật. Mở bằng tham "
                        f"số '{KY_TU_KY_KEY}' ở màn hình Tham số (hai chữ ký). Trước khi bật phải "
                        "chắc MISA đã dừng khấu trừ cùng kỳ, nếu không một khoản thuế bị trừ hai lần.")}
