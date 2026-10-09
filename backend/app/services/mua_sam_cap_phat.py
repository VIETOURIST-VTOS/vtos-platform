"""5.9.2 Đề nghị mua và 5.9.3 Cấp phát tài sản (Chủ tịch chốt 08/10/2026).

    "đề nghị mua đi qua TGĐ / Chủ tịch và Kế toán chi, cấp phát tài sản do HCNS làm"

HAI CHỮ KÝ, KHÔNG PHẢI MỘT — và đây là phần dễ làm sai nhất của 5.9.2. Người duyệt nói ĐƯỢC MUA;
Kế toán nói ĐÃ CHI. Gộp hai việc vào một trạng thái thì ngày Kế toán chưa chi được vì thiếu tiền,
đề nghị vẫn hiện "xong" — và người đề nghị ngồi đợi một món hàng không ai mua. Hai cột tiền cũng
vì thế: `uoc_tinh` là số người đề nghị đoán, `so_tien_chi` là số thật. Gộp một cột thì lần chi đầu
tiên xoá mất con số đã được duyệt, và không ai đối chiếu được "duyệt bao nhiêu, chi bao nhiêu".

5.9.3 KHÔNG PHẢI SỔ TÀI SẢN THỨ HAI. Sổ tài sản là `fixed_assets` (thẻ TSCĐ, nguyên giá, khấu hao);
bảng cấp phát chỉ trả lời MỘT MÓN ĐANG Ở TAY AI. Nối bằng `asset_id`, để rỗng được, vì phần lớn thứ
HCNS cấp — điện thoại, SIM, chìa khoá, đồng phục, thẻ ra vào — không đủ nguyên giá để thành một thẻ.
Bắt mọi món phải có thẻ trước khi cấp thì HCNS ghi ra giấy, và sổ máy rỗng trong khi đồ vẫn đi.
"""
from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.hr import Employee
from app.models.assets import FixedAsset
from app.models.nhan_su_danh_gia import (DeNghiMua, CapPhatTaiSan, DNM_TRANG_THAI, DNM_MUC_DO,
                                         CP_TRANG_THAI)

# Ai ký vế nào. Khai MỘT chỗ, vì hai vế có hai nhóm người khác nhau và trộn chúng là mất chính cái
# tách hai chữ ký ở trên.
VAI_DUYET_MUA = ("tgd", "chutich")
VAI_CHI = ("ketoan",)
VAI_CAP_PHAT = ("hcns",)


def _ma_moi(db: Session, model, tien_to: str) -> str:
    # Lọc theo tiền tố là ĐÚNG RỒI, nhưng ĐẾM số dòng khớp thì vẫn hỏng khi có dòng bị xoá: số
    # lùi một bước và mã kế tiếp đụng một mã đang còn sống, mà cột `ma` thì UNIQUE. Lấy số LỚN
    # NHẤT thì không — xem `services/ma_tu_sinh.py`.
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, model, f"{tien_to}{date.today().year}-", 4, cot="ma")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5.9.2 ĐỀ NGHỊ MUA
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _tom_tat_dnm(r: DeNghiMua) -> dict:
    return {"id": r.id, "ma": r.ma, "department": r.department, "nguoi_de_nghi": r.nguoi_de_nghi,
            "noi_dung": r.noi_dung, "so_luong": r.so_luong, "don_vi": r.don_vi,
            "uoc_tinh": None if r.uoc_tinh is None else float(r.uoc_tinh),
            "ly_do": r.ly_do, "muc_do": r.muc_do, "muc_do_ten": DNM_MUC_DO.get(r.muc_do, r.muc_do),
            "can_truoc_ngay": r.can_truoc_ngay.isoformat() if r.can_truoc_ngay else None,
            "trang_thai": r.trang_thai,
            "trang_thai_ten": DNM_TRANG_THAI.get(r.trang_thai, r.trang_thai),
            "duyet_boi": r.duyet_boi, "duyet_vai": r.duyet_vai,
            "duyet_luc": r.duyet_luc.isoformat() if r.duyet_luc else None,
            "duyet_ghi_chu": r.duyet_ghi_chu,
            "chi_boi": r.chi_boi, "chi_luc": r.chi_luc.isoformat() if r.chi_luc else None,
            "so_tien_chi": None if r.so_tien_chi is None else float(r.so_tien_chi),
            "chung_tu_ref": r.chung_tu_ref,
            # Chênh giữa số duyệt và số chi, in SẴN chứ không bắt người đọc tự trừ: chỗ lệch nằm
            # trong đầu người đọc thì không ai nhìn thấy nó hai lần liên tiếp.
            "lech_chi_so_voi_uoc": (None if r.so_tien_chi is None or r.uoc_tinh is None
                                    else float(r.so_tien_chi) - float(r.uoc_tinh))}


def tao_de_nghi(db: Session, boi: User, noi_dung: str, so_luong: float = 1, don_vi: str = "cái",
                uoc_tinh: float | None = None, ly_do: str = "", muc_do: str = "thuong",
                can_truoc_ngay: date | None = None, department: str = "") -> dict:
    if not (noi_dung or "").strip():
        raise ValueError("Phải ghi mua cái gì.")
    if muc_do not in DNM_MUC_DO:
        raise ValueError(f"Mức độ không hợp lệ: {muc_do!r}.")
    nv = db.execute(select(Employee).where(Employee.user_id == boi.id)).scalars().first()
    r = DeNghiMua(ma=_ma_moi(db, DeNghiMua, "DNM"),
                  department=department or (nv.department if nv else "") or "",
                  nguoi_de_nghi=boi.username, noi_dung=noi_dung.strip()[:300],
                  so_luong=float(so_luong or 1), don_vi=(don_vi or "cái")[:20],
                  uoc_tinh=None if uoc_tinh in (None, "") else float(uoc_tinh),
                  ly_do=(ly_do or "").strip(), muc_do=muc_do, can_truoc_ngay=can_truoc_ngay,
                  trang_thai="cho_duyet")
    db.add(r)
    db.flush()
    return _tom_tat_dnm(r)


def duyet(db: Session, boi: User, de_nghi_id: int, dong_y: bool, ghi_chu: str = "") -> dict:
    """Chữ ký 1 — TGĐ / Chủ tịch. KHÔNG kèm việc chi: chi là chữ ký thứ hai, của người khác."""
    r = db.get(DeNghiMua, de_nghi_id)
    if r is None:
        raise ValueError(f"Không có đề nghị id={de_nghi_id}.")
    if boi.role not in VAI_DUYET_MUA:
        raise PermissionError(f"Chỉ {', '.join(VAI_DUYET_MUA)} duyệt đề nghị mua; "
                              f"tài khoản này là {boi.role!r}.")
    if r.trang_thai != "cho_duyet":
        raise ValueError(f"Đề nghị đang ở trạng thái {r.trang_thai!r}, không còn chờ duyệt.")
    if not dong_y and not (ghi_chu or "").strip():
        raise ValueError("Không duyệt thì phải ghi lý do — người đề nghị cần biết sửa gì để gửi lại.")
    r.trang_thai = "da_duyet" if dong_y else "tu_choi"
    r.duyet_boi, r.duyet_vai, r.duyet_luc = boi.username, boi.role, datetime.now()
    r.duyet_ghi_chu = (ghi_chu or "").strip()
    db.flush()
    return _tom_tat_dnm(r)


def ghi_da_chi(db: Session, boi: User, de_nghi_id: int, so_tien: float,
               chung_tu_ref: str = "") -> dict:
    """Chữ ký 2 — Kế toán. Chỉ ghi được trên đề nghị ĐÃ DUYỆT: chi trước khi có người duyệt là
    đúng cái vòng này sinh ra để chặn."""
    r = db.get(DeNghiMua, de_nghi_id)
    if r is None:
        raise ValueError(f"Không có đề nghị id={de_nghi_id}.")
    if boi.role not in VAI_CHI:
        raise PermissionError(f"Chỉ {', '.join(VAI_CHI)} ghi đã chi; tài khoản này là {boi.role!r}.")
    if r.trang_thai != "da_duyet":
        raise ValueError(f"Chỉ ghi chi trên đề nghị ĐÃ DUYỆT. Đề nghị này đang {r.trang_thai!r}.")
    if so_tien is None or float(so_tien) <= 0:
        raise ValueError("Số tiền chi phải lớn hơn 0.")
    r.so_tien_chi = float(so_tien)
    r.chung_tu_ref = (chung_tu_ref or "").strip()[:60]
    r.chi_boi, r.chi_luc, r.trang_thai = boi.username, datetime.now(), "da_chi"
    db.flush()
    return _tom_tat_dnm(r)


def danh_sach_de_nghi(db: Session, trang_thai: str = "", phong: str = "") -> list[dict]:
    q = select(DeNghiMua)
    if trang_thai:
        q = q.where(DeNghiMua.trang_thai == trang_thai)
    if phong:
        q = q.where(DeNghiMua.department == phong)
    return [_tom_tat_dnm(r) for r in db.execute(q.order_by(DeNghiMua.id.desc())).scalars().all()]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5.9.3 CẤP PHÁT TÀI SẢN
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _tom_tat_cp(db: Session, r: CapPhatTaiSan) -> dict:
    nv = db.get(Employee, r.employee_id)
    ts = db.get(FixedAsset, r.asset_id) if r.asset_id else None
    return {"id": r.id, "ma": r.ma, "asset_id": r.asset_id,
            "ma_tai_san": ts.code if ts else "",
            "ten_tai_san": r.ten_tai_san or (ts.name if ts else ""),
            "so_luong": r.so_luong, "don_vi": r.don_vi,
            "employee_id": r.employee_id, "ho_ten": nv.full_name if nv else "",
            "ma_nv": nv.code if nv else "", "department": r.department,
            "cap_ngay": r.cap_ngay.isoformat() if r.cap_ngay else None,
            "muc_dich": r.muc_dich, "tinh_trang_khi_cap": r.tinh_trang_khi_cap,
            "trang_thai": r.trang_thai,
            "trang_thai_ten": CP_TRANG_THAI.get(r.trang_thai, r.trang_thai),
            "tra_ngay": r.tra_ngay.isoformat() if r.tra_ngay else None,
            "tinh_trang_khi_tra": r.tinh_trang_khi_tra,
            "nguoi_lap": r.nguoi_lap, "ghi_chu": r.ghi_chu}


def cap_phat(db: Session, boi: User, employee_id: int, cap_ngay: date,
             ten_tai_san: str = "", asset_id: int | None = None, so_luong: float = 1,
             don_vi: str = "cái", muc_dich: str = "", tinh_trang_khi_cap: str = "",
             ghi_chu: str = "") -> dict:
    if boi.role not in VAI_CAP_PHAT:
        raise PermissionError(f"Cấp phát tài sản do {', '.join(VAI_CAP_PHAT)} lập "
                              f"(Chủ tịch chốt 08/10/2026); tài khoản này là {boi.role!r}.")
    nv = db.get(Employee, employee_id)
    if nv is None:
        raise ValueError(f"Không có hồ sơ nhân sự id={employee_id}.")
    ts = db.get(FixedAsset, asset_id) if asset_id else None
    if asset_id and ts is None:
        raise ValueError(f"Không có thẻ tài sản id={asset_id}.")
    # Tên món là BẮT BUỘC khi không có thẻ TSCĐ. Một dòng cấp phát không nói được cấp CÁI GÌ thì
    # nó không trả lời được câu hỏi duy nhất bảng này sinh ra để trả lời.
    if not ts and not (ten_tai_san or "").strip():
        raise ValueError("Không nối thẻ tài sản thì phải ghi tên món được cấp.")
    r = CapPhatTaiSan(ma=_ma_moi(db, CapPhatTaiSan, "CP"), asset_id=asset_id,
                      ten_tai_san=(ten_tai_san or "").strip()[:200], so_luong=float(so_luong or 1),
                      don_vi=(don_vi or "cái")[:20], employee_id=employee_id,
                      department=nv.department or "", cap_ngay=cap_ngay,
                      muc_dich=(muc_dich or "").strip()[:300],
                      tinh_trang_khi_cap=(tinh_trang_khi_cap or "").strip()[:100],
                      nguoi_lap=boi.username, ghi_chu=(ghi_chu or "").strip())
    db.add(r)
    db.flush()
    return _tom_tat_cp(db, r)


def ghi_tra(db: Session, boi: User, cap_phat_id: int, tra_ngay: date, tinh_trang: str,
            mat_hong: bool = False) -> dict:
    if boi.role not in VAI_CAP_PHAT:
        raise PermissionError(f"Chỉ {', '.join(VAI_CAP_PHAT)} ghi trả; tài khoản này là {boi.role!r}.")
    r = db.get(CapPhatTaiSan, cap_phat_id)
    if r is None:
        raise ValueError(f"Không có biên bản cấp phát id={cap_phat_id}.")
    if r.trang_thai != "dang_giu":
        raise ValueError(f"Biên bản này đang {r.trang_thai!r}, không còn ở trạng thái đang giữ.")
    # Tình trạng khi trả là BẮT BUỘC. "Đã trả" mà không nói trả về trong tình trạng nào thì lần
    # cấp cho người tiếp theo không ai biết món ấy còn dùng được không.
    if not (tinh_trang or "").strip():
        raise ValueError("Phải ghi tình trạng món đồ khi trả.")
    r.trang_thai = "mat_hong" if mat_hong else "da_tra"
    r.tra_ngay, r.tinh_trang_khi_tra = tra_ngay, tinh_trang.strip()[:200]
    db.flush()
    return _tom_tat_cp(db, r)


def dang_giu_cua_nguoi(db: Session, employee_id: int) -> list[dict]:
    """Người này đang giữ những gì — câu hỏi duy nhất bảng này sinh ra để trả lời, và là câu HCNS
    phải hỏi mỗi lần có người nghỉ việc."""
    ds = db.execute(select(CapPhatTaiSan).where(CapPhatTaiSan.employee_id == employee_id,
                                                CapPhatTaiSan.trang_thai == "dang_giu")).scalars().all()
    return [_tom_tat_cp(db, r) for r in ds]


def danh_sach_cap_phat(db: Session, trang_thai: str = "", phong: str = "") -> list[dict]:
    q = select(CapPhatTaiSan)
    if trang_thai:
        q = q.where(CapPhatTaiSan.trang_thai == trang_thai)
    if phong:
        q = q.where(CapPhatTaiSan.department == phong)
    return [_tom_tat_cp(db, r) for r in db.execute(q.order_by(CapPhatTaiSan.id.desc())).scalars().all()]


def meta() -> dict:
    return {"dnm_trang_thai": DNM_TRANG_THAI, "dnm_muc_do": DNM_MUC_DO,
            "cp_trang_thai": CP_TRANG_THAI, "vai_duyet_mua": list(VAI_DUYET_MUA),
            "vai_chi": list(VAI_CHI), "vai_cap_phat": list(VAI_CAP_PHAT)}
