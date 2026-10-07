"""Đợt B – khai LOẠI KHOẢN, ghi sổ sự kiện thu nhập, và ba phép chống trùng.

BA CHỖ TRÙNG KHÁC NHAU, BA PHÉP KIỂM KHÁC NHAU

  1. TRÙNG CĂN CỨ — cùng người, cùng loại khoản, cùng căn cứ, ở hai kỳ. Đây là chỗ trùng rõ nhất:
     cùng một lý do trả tiền hai lần. CHẶN.

  2. TRÙNG NGUỒN — căn cứ khác nhau (vì căn cứ của phần lớn khoản gắn với THÁNG), nhưng cùng một
     chuyến nằm trong nguồn của cả hai tháng. Đây là chỗ trùng thật sự nguy, vì nó đi qua được phép
     kiểm thứ nhất: chuyến chốt lại sang tháng sau thì sinh một căn cứ mới, trông như một khoản mới.
     CHẶN.

  3. MỘT CĂN CỨ CHIA CHO NHIỀU NGƯỜI — với loại khoản là MỘT TÚI TIỀN duy nhất, trả đủ túi cho mỗi
     người nghĩa là chi gấp số người. CẢNH BÁO, không chặn — xem chú thích ở `DOC_CHIEM`.

VÌ SAO KHÔNG PHẢI MỌI CĂN CỨ ĐỀU GẮN VỚI MỘT VẬT THỂ

Hoa hồng thang f tính trên TỔNG doanh thu tháng vượt mốc, không tính trên từng chuyến — nên căn cứ
của nó là tháng, không phải chuyến. Đó là bản chất của phép tính, không phải chỗ làm ẩu. Chính vì
vậy mới cần `nguon`: căn cứ nói "vì tháng này", còn nguồn nói "tháng này gồm những chuyến nào".
Trùng một chuyến giữa hai tháng là trùng, dù hai căn cứ khác tên.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.su_kien_thu_nhap import SuKienThuNhap

# Mọi loại khoản thu nhập biến đổi, khai một chỗ. Lời gọi `add` trong services/hr.py phải dùng một
# khoá ở đây — có phép thử canh. Loại nào không khai thì không chảy vào sổ, mà không vào sổ nghĩa là
# không ai chống trùng được cho nó.
LOAI_KHOAN = {
    "hh_thang_f": "Hoa hồng thang f – Kinh doanh lẻ",
    "ln_duoi_bien": "10% lợi nhuận booking chuyến duyệt chạy dưới biên",
    "ln_doan_cantho": "10% lợi nhuận đoàn tự chốt (Cần Thơ)",
    "che_tai_su_vu": "Chế tài sự vụ – trừ vào hoa hồng",
    "che_tai_ca_truc": "Chế tài ca trực page – trừ vào hoa hồng",
    "gd_kd_thuong": "Thưởng Giám đốc Kinh doanh theo tỷ lệ NV đạt chỉ tiêu",
    "hh_doan": "Hoa hồng Kinh doanh Đoàn trên lợi nhuận vượt mốc",
    "ptgd_doan": "Phó TGĐ tour đoàn – tỷ lệ trên lợi nhuận các đoàn có lãi",
    "sale_admin": "Sale Admin – tỷ lệ trên lợi nhuận các đoàn có lãi",
    "quy_dh_nv": "Thưởng chuyến Điều hành – 70% quỹ",
    "quy_dh_tp": "Trưởng phòng Điều hành – 30% quỹ toàn phòng",
    "quy_visa_hcm": "Quỹ visa HCM chia đều",
    "quy_visa_hn": "Quỹ visa Hà Nội hưởng riêng",
    "thu_lao_hdv": "Thù lao hướng dẫn viên theo chuyến",
    "cong_tac_phi_tx": "Công tác phí tài xế theo lệnh điều xe",
}

# LOẠI KHOẢN LÀ MỘT TÚI TIỀN DUY NHẤT: cả phòng chia một quỹ, không phải mỗi người một phần tính
# riêng. Trả đủ túi cho hai người là chi gấp đôi quỹ.
#
# CẢNH BÁO CHỨ KHÔNG CHẶN, và đây là một lựa chọn có lý do chứ không phải sự dè dặt: sửa cho đúng
# nghĩa là ĐỔI CÔNG THỨC CHIA TIỀN, mà công thức chia tiền thì phải có người ký. Làn viết phần mềm
# dựng chỗ nhìn thấy; chia lại hay giữ nguyên là chữ ký. Trước bản này không có chỗ nào nhìn thấy
# cả, nên câu hỏi chưa bao giờ được đặt ra.
DOC_CHIEM = ("quy_dh_tp",)


def khoa_su_kien(ma_nv: str, loai: str, can_cu: str) -> tuple[str, str, str]:
    return (str(ma_nv or ""), str(loai or ""), str(can_cu or ""))


def _da_ky(db: Session) -> list[SuKienThuNhap]:
    return list(db.execute(select(SuKienThuNhap)).scalars())


def ghi_so(db: Session, period: str, rows: list[dict], ban_khoa_id: int | None = None) -> int:
    """Ghi các khoản của một kỳ VỪA ĐƯỢC KÝ vào sổ. Gọi trong cùng giao dịch với `luong_khoa.khoa`.

    Bỏ qua dòng đã có đúng khoá – ký lại một kỳ thành bản 2 không được sinh dòng trùng, và cũng
    không được làm việc ký thất bại. Số tiền của bản sau ghi đè số của bản trước: bản đang hiệu lực
    là bản cuối, nên con số trong sổ phải là con số của nó.
    """
    co = {khoa_su_kien(s.ma_nv, s.loai, s.can_cu): s for s in _da_ky(db)}
    n = 0
    for r in rows:
        for k in (r.get("khoan") or []):
            loai, can_cu = k.get("loai") or "", k.get("can_cu") or ""
            if not loai or not can_cu:
                continue          # khoản chưa khai căn cứ – phép thử canh bắt ở chỗ khác, không bịa ở đây
            kh = khoa_su_kien(r.get("ma"), loai, can_cu)
            cu = co.get(kh)
            if cu is not None:
                cu.period, cu.so_tien, cu.ban_khoa_id = period, k.get("tien"), ban_khoa_id
                cu.nguon, cu.dien_giai = k.get("nguon") or [], k.get("ten") or ""
                continue
            s = SuKienThuNhap(period=period, ban_khoa_id=ban_khoa_id, ma_nv=r.get("ma"), loai=loai,
                              can_cu=can_cu, so_tien=k.get("tien"), nguon=k.get("nguon") or [],
                              dien_giai=(k.get("ten") or "")[:2000])
            db.add(s); co[kh] = s; n += 1
    db.flush()
    return n


def kiem_trung(db: Session, period: str, rows: list[dict]) -> list[dict]:
    """Ba phép chống trùng, chạy trên BẢN NHÁP trước khi ký. Quy tắc xác định, không suy đoán."""
    co = _da_ky(db)
    # Chỉ so với các kỳ KHÁC: trong cùng một kỳ, dòng cũ chính là lần ký trước của kỳ ấy.
    khac_ky = [s for s in co if s.period != period]
    theo_khoa = {khoa_su_kien(s.ma_nv, s.loai, s.can_cu): s for s in khac_ky}
    theo_nguon: dict[tuple[str, str, str], SuKienThuNhap] = {}
    for s in khac_ky:
        for g in (s.nguon or []):
            theo_nguon[(s.ma_nv, s.loai, str(g))] = s

    co_flags: list[dict] = []
    # ---- 1 & 2: so từng khoản của bản nháp với sổ ----
    for r in rows:
        for k in (r.get("khoan") or []):
            loai, can_cu = k.get("loai") or "", k.get("can_cu") or ""
            if not loai or not can_cu:
                continue
            cu = theo_khoa.get(khoa_su_kien(r.get("ma"), loai, can_cu))
            if cu is not None:
                co_flags.append({
                    "ma": "TRUNG_CAN_CU", "muc": "chan",
                    "thong_diep": (f"{r.get('ma')} – khoản '{LOAI_KHOAN.get(loai, loai)}' với căn cứ "
                                   f"'{can_cu}' ĐÃ được trả ở kỳ {cu.period}"),
                    "bang_chung": {"ma_nv": r.get("ma"), "loai": loai, "can_cu": can_cu,
                                   "ky_da_tra": cu.period, "so_tien_da_tra": cu.so_tien,
                                   "so_tien_ky_nay": k.get("tien")}})
                continue
            for g in (k.get("nguon") or []):
                cu2 = theo_nguon.get((str(r.get("ma")), loai, str(g)))
                if cu2 is not None:
                    co_flags.append({
                        "ma": "TRUNG_NGUON", "muc": "chan",
                        "thong_diep": (f"{r.get('ma')} – '{g}' đã nằm trong căn cứ của khoản "
                                       f"'{LOAI_KHOAN.get(loai, loai)}' kỳ {cu2.period}; kỳ này tính lại "
                                       f"dưới một căn cứ khác tên"),
                        "bang_chung": {"ma_nv": r.get("ma"), "loai": loai, "nguon": str(g),
                                       "ky_da_tra": cu2.period, "can_cu_cu": cu2.can_cu,
                                       "can_cu_moi": can_cu}})
                    break

    # ---- 3: một túi tiền chia cho nhiều người ----
    tui: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        for k in (r.get("khoan") or []):
            if (k.get("loai") or "") in DOC_CHIEM and k.get("can_cu"):
                tui.setdefault((k["loai"], k["can_cu"]), []).append(
                    {"ma_nv": r.get("ma"), "ten": r.get("ten"), "so_tien": k.get("tien")})
    for (loai, can_cu), ds in tui.items():
        if len(ds) > 1:
            co_flags.append({
                "ma": "CAN_CU_CHIA_NHIEU_NGUOI", "muc": "canh_bao",
                "thong_diep": (f"'{LOAI_KHOAN.get(loai, loai)}' là MỘT quỹ nhưng đang trả đủ cho "
                               f"{len(ds)} người – tổng chi gấp {len(ds)} lần quỹ. Chia lại hay giữ "
                               f"nguyên là quyết định về công thức, cần chữ ký."),
                "bang_chung": {"loai": loai, "can_cu": can_cu, "nguoi": ds,
                               "tong_chi": sum(float(x["so_tien"] or 0) for x in ds)}})
    return co_flags


def so_cua_ky(db: Session, period: str) -> list[dict]:
    ds = db.execute(select(SuKienThuNhap).where(SuKienThuNhap.period == period)
                    .order_by(SuKienThuNhap.ma_nv, SuKienThuNhap.loai)).scalars()
    return [{"ma_nv": s.ma_nv, "loai": s.loai, "loai_ten": LOAI_KHOAN.get(s.loai, s.loai),
             "can_cu": s.can_cu, "so_tien": s.so_tien, "nguon": s.nguon or [],
             "dien_giai": s.dien_giai, "ghi_luc": s.ghi_luc} for s in ds]
