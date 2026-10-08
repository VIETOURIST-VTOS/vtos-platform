"""Đợt D3 – quy tắc của quan hệ nhà đầu tư.

Bốn quy tắc, và cả bốn đều nói về cùng một thứ: thông tin chưa công bố đi ra ngoài thì phải để lại
dấu vết.

  1. Lưu email/điện thoại PHẢI ghi căn cứ thu thập (Nghị định 13/2023).
  2. Che bớt dữ liệu cá nhân với vai chỉ cần biết "đã tiếp xúc với ai".
  3. Đánh dấu "có nói thông tin chưa công bố" mà chưa nối tới bản công bố nào = một việc PHẢI xử
     lý, hiện lên bảng điều khiển, không im lặng.
  4. Cấp quyền xem hồ sơ CHƯA CÔNG BỐ phải có cam kết bảo mật; cấp không thời hạn có trạng thái
     riêng, không trộn vào "đang hiệu lực".
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nha_dau_tu import (HINH_THUC_TIEP_XUC, LOAI_LIEN_HE, LienHeNhaDauTu,
                                   QuyenTruyCapHoSo, TuongTacNhaDauTu)

# Vai được xem đầy đủ email/điện thoại. HẸP HƠN danh sách xem màn hình, và đó là chủ ý: Ban Kiểm
# soát và CNTT cần biết đã tiếp xúc với ai, không cần số điện thoại của họ. Đây là thu hẹp, không
# phải nới quyền — nên không chạm tới bảng phạm vi đã chốt.
VAI_XEM_DU_LIEN_HE = ("chutich", "tgd", "ir_phapche")

TRANG_THAI_QUYEN = {
    "dang_hieu_luc": "Đang hiệu lực",
    "khong_co_han": "Cấp KHÔNG thời hạn – phải xử lý",
    "het_han": "Đã hết hạn",
    "da_thu_hoi": "Đã thu hồi",
}

# Số ngày trước khi hết hạn thì báo sớm.
NGAY_BAO_SOM = 7


def _che(s: str) -> str:
    """Che một email hoặc số điện thoại: giữ đủ để nhận ra, không đủ để liên lạc."""
    s = (s or "").strip()
    if not s:
        return ""
    if "@" in s:
        ten, mien = s.split("@", 1)
        return (ten[:2] + "***@" + mien) if len(ten) > 2 else ("***@" + mien)
    return ("***" + s[-3:]) if len(s) > 3 else "***"


# ─────────────────────────── danh bạ ───────────────────────────
def tao_lien_he(db: Session, data: dict, boi: str) -> LienHeNhaDauTu:
    """Quy tắc 1: có email hoặc điện thoại thì phải ghi căn cứ thu thập."""
    if (data.get("loai") or "khac") not in LOAI_LIEN_HE:
        raise ValueError(f"Loại liên hệ không hợp lệ: {data.get('loai')}")
    if not (data.get("ten") or "").strip():
        raise ValueError("Phải ghi TÊN")
    co_ca_nhan = bool((data.get("email") or "").strip() or (data.get("dien_thoai") or "").strip())
    if co_ca_nhan and not (data.get("can_cu_thu_thap") or "").strip():
        raise ValueError("Lưu email hoặc điện thoại phải ghi CĂN CỨ THU THẬP (họ tự cung cấp ở "
                         "ĐHĐCĐ nào, công bố công khai ở đâu…) – Nghị định 13/2023")
    lh = LienHeNhaDauTu(boi=boi, luc=datetime.now(), **data)
    db.add(lh)
    db.flush()
    return lh


def ra_lh(lh: LienHeNhaDauTu, vai: str) -> dict:
    """Quy tắc 2: vai không nằm trong VAI_XEM_DU_LIEN_HE thì email/điện thoại bị che."""
    du = vai in VAI_XEM_DU_LIEN_HE
    return {
        "id": lh.id, "ten": lh.ten, "to_chuc": lh.to_chuc, "chuc_danh": lh.chuc_danh,
        "loai": lh.loai, "loai_ten": LOAI_LIEN_HE.get(lh.loai, lh.loai),
        "email": lh.email if du else _che(lh.email),
        "dien_thoai": lh.dien_thoai if du else _che(lh.dien_thoai),
        "da_che": not du,
        "can_cu_thu_thap": lh.can_cu_thu_thap, "ghi_chu": lh.ghi_chu,
        "dang_hoat_dong": lh.dang_hoat_dong, "boi": lh.boi, "luc": lh.luc,
    }


# ─────────────────────────── sổ tiếp xúc ───────────────────────────
def ghi_tuong_tac(db: Session, data: dict, boi: str) -> TuongTacNhaDauTu:
    if (data.get("hinh_thuc") or "gap") not in HINH_THUC_TIEP_XUC:
        raise ValueError(f"Hình thức tiếp xúc không hợp lệ: {data.get('hinh_thuc')}")
    if data.get("co_thong_tin_chua_cong_bo") and not (data.get("thong_tin_da_tiet_lo") or "").strip():
        raise ValueError("Đã đánh dấu CÓ nói thông tin chưa công bố thì phải ghi ĐÃ NÓI GÌ – một "
                         "dấu tích không kèm nội dung thì không xử lý được")
    tt = TuongTacNhaDauTu(boi=boi, luc=datetime.now(), **data)
    db.add(tt)
    db.flush()
    return tt


def chua_xu_ly_tiet_lo(tt: TuongTacNhaDauTu) -> bool:
    """Đã nói thông tin chưa công bố mà chưa nối tới bản công bố nào."""
    return bool(tt.co_thong_tin_chua_cong_bo) and tt.ban_ghi_cong_bo_id is None


def noi_ban_cong_bo(db: Session, tt: TuongTacNhaDauTu, ban_ghi_id: int) -> TuongTacNhaDauTu:
    from app.models.phap_che import BanGhiCongBo
    bg = db.get(BanGhiCongBo, ban_ghi_id)
    if bg is None:
        raise ValueError("Không có bản ghi công bố này")
    if not tt.co_thong_tin_chua_cong_bo:
        raise ValueError("Lần tiếp xúc này không đánh dấu có thông tin chưa công bố")
    if bg.da_cong_bo_luc is None:
        raise ValueError("Bản ghi công bố ấy CHƯA công bố – nối vào đây là nói rằng việc đã xong "
                         "trong khi thông tin vẫn chưa ra công chúng")
    tt.ban_ghi_cong_bo_id = bg.id
    return tt


def ra_tt(db: Session, tt: TuongTacNhaDauTu, vai: str) -> dict:
    lh = db.get(LienHeNhaDauTu, tt.lien_he_id)
    return {
        "id": tt.id, "lien_he_id": tt.lien_he_id,
        "lien_he_ten": lh.ten if lh else "", "lien_he_to_chuc": lh.to_chuc if lh else "",
        "ngay": tt.ngay, "hinh_thuc": tt.hinh_thuc,
        "hinh_thuc_ten": HINH_THUC_TIEP_XUC.get(tt.hinh_thuc, tt.hinh_thuc),
        "noi_dung_tom_tat": tt.noi_dung_tom_tat, "nguoi_du": tt.nguoi_du or [],
        "co_thong_tin_chua_cong_bo": tt.co_thong_tin_chua_cong_bo,
        "thong_tin_da_tiet_lo": tt.thong_tin_da_tiet_lo,
        "ban_ghi_cong_bo_id": tt.ban_ghi_cong_bo_id,
        "chua_xu_ly_tiet_lo": chua_xu_ly_tiet_lo(tt),
        "boi": tt.boi, "luc": tt.luc,
    }


# ─────────────────────────── quyền xem hồ sơ ───────────────────────────
def cap_quyen(db: Session, data: dict, boi: str) -> QuyenTruyCapHoSo:
    """Quy tắc 4: hồ sơ chưa công bố thì phải có cam kết bảo mật, có căn cứ ghi ra."""
    if not (data.get("ho_so") or "").strip() or not (data.get("nguoi_duoc_cap") or "").strip():
        raise ValueError("Phải ghi HỒ SƠ và NGƯỜI ĐƯỢC CẤP")
    if not (data.get("ly_do") or "").strip():
        raise ValueError("Phải ghi LÝ DO cấp – một quyền không ai nhớ vì sao cấp là một quyền "
                         "không ai dám thu hồi")
    chua_cb = data.get("ho_so_chua_cong_bo", True)
    if chua_cb:
        if not data.get("cam_ket_bao_mat"):
            raise ValueError("Hồ sơ CHƯA CÔNG BỐ: phải có CAM KẾT BẢO MẬT trước khi cấp quyền")
        if not (data.get("can_cu_cam_ket") or "").strip():
            raise ValueError("Phải ghi căn cứ cam kết bảo mật (NDA số mấy, ký ngày nào) – một cam "
                             "kết không chỉ ra được văn bản nào thì không viện dẫn được")
    q = QuyenTruyCapHoSo(boi=boi, luc=datetime.now(), **data)
    db.add(q)
    db.flush()
    return q


def thu_hoi(db: Session, q: QuyenTruyCapHoSo, boi: str) -> QuyenTruyCapHoSo:
    if q.thu_hoi_luc is not None:
        raise ValueError("Quyền này đã thu hồi rồi")
    q.thu_hoi_luc = datetime.now()
    q.thu_hoi_boi = boi
    return q


def trang_thai_quyen(q: QuyenTruyCapHoSo, hom_nay: date | None = None) -> str:
    if q.thu_hoi_luc is not None:
        return "da_thu_hoi"
    nay = hom_nay or date.today()
    if q.den_ngay is None:
        # RỖNG không phải "còn hiệu lực dài dài" – nó là một việc phải xử lý.
        return "khong_co_han"
    return "het_han" if q.den_ngay < nay else "dang_hieu_luc"


def ra_q(q: QuyenTruyCapHoSo, hom_nay: date | None = None) -> dict:
    nay = hom_nay or date.today()
    tt = trang_thai_quyen(q, nay)
    con = (q.den_ngay - nay).days if (q.den_ngay is not None and tt == "dang_hieu_luc") else None
    return {
        "id": q.id, "ho_so": q.ho_so, "nguoi_duoc_cap": q.nguoi_duoc_cap, "to_chuc": q.to_chuc,
        "lien_he_id": q.lien_he_id, "ly_do": q.ly_do,
        "ho_so_chua_cong_bo": q.ho_so_chua_cong_bo,
        "cam_ket_bao_mat": q.cam_ket_bao_mat, "can_cu_cam_ket": q.can_cu_cam_ket,
        "tu_ngay": q.tu_ngay, "den_ngay": q.den_ngay,
        "thu_hoi_luc": q.thu_hoi_luc, "thu_hoi_boi": q.thu_hoi_boi,
        "trang_thai": tt, "trang_thai_ten": TRANG_THAI_QUYEN[tt],
        "con_lai_ngay": con,
        "sap_het_han": con is not None and con <= NGAY_BAO_SOM,
        "boi": q.boi, "luc": q.luc,
    }


# ─────────────────────────── bảng điều khiển ───────────────────────────
def bang_nha_dau_tu(db: Session, vai: str, hom_nay: date | None = None) -> dict:
    nay = hom_nay or date.today()
    lh = [ra_lh(x, vai) for x in db.execute(
        select(LienHeNhaDauTu).order_by(LienHeNhaDauTu.ten)).scalars()]
    tt = [ra_tt(db, x, vai) for x in db.execute(
        select(TuongTacNhaDauTu).order_by(TuongTacNhaDauTu.ngay.desc(),
                                          TuongTacNhaDauTu.id.desc())).scalars()]
    q = [ra_q(x, nay) for x in db.execute(
        select(QuyenTruyCapHoSo).order_by(QuyenTruyCapHoSo.id.desc())).scalars()]
    return {
        "hom_nay": nay,
        "lien_he": {"so": len(lh), "rows": lh, "da_che": vai not in VAI_XEM_DU_LIEN_HE},
        "tiep_xuc": {"so": len(tt), "rows": tt,
                     "so_chua_xu_ly_tiet_lo": len([x for x in tt if x["chua_xu_ly_tiet_lo"]])},
        "quyen": {"so": len(q), "rows": q,
                  "so_khong_co_han": len([x for x in q if x["trang_thai"] == "khong_co_han"]),
                  "so_sap_het_han": len([x for x in q if x["sap_het_han"]]),
                  "so_dang_hieu_luc": len([x for x in q if x["trang_thai"] == "dang_hieu_luc"])},
        "ghi_chu": ("Bảng này KHÔNG lưu số cổ phần sở hữu: sở hữu là dữ liệu của sổ cổ đông. Chép "
                    "tay vào đây là tạo con số thứ hai, và hai con số về cùng một thứ thì sớm "
                    "muộn sẽ lệch."),
    }
