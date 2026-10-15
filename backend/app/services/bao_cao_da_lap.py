# -*- coding: utf-8 -*-
"""BẢN BÁO CÁO ĐÃ LẬP — Đợt R1, 15/10/2026.

LẬP là TÍNH; LƯU BẢN là CHỐT. Hai việc, hai nút, hai bước — đúng cách MISA chia, và đúng lẽ Đợt
E16 đã dựng cho bộ số kiểm toán: ký là xác nhận bản ĐÚNG, không phải lúc tính.

ĐƯỜNG ĐI MỘT BẢN

    Kế toán bấm LẬP      → bản `nhap`, số đã đóng băng, lập lại thì ra bản nháp mới
    Kế toán bấm TRÌNH    → `cho_ky`
    Chủ tịch bấm KÝ      → `da_ky`; bản `da_ky` cũ CÙNG (loại, pháp nhân, kỳ) → `da_thay_the`
    Chủ tịch bấm TỪ CHỐI → `tu_choi`, bắt buộc ghi lý do

NGƯỜI LẬP KHÔNG TỰ KÝ — cùng câu của Đợt E16: việc trình và việc ký phải là hai người, bất kể hai
người ấy to đến đâu.

MỘT ĐIỀU ĐỢT NÀY CỐ Ý KHÔNG LÀM: không đụng một dòng nào của `services/bctc.py`. Bản đã lập gọi
đúng `BCTC.bctc()` mà màn hình vẫn gọi, rồi đóng băng kết quả. Nếu con số của bản khác con số
màn hình thì nguyên nhân nằm ở SỔ (có người ghi thêm bút toán đề ngày cũ) — và đó chính là điều
bảng này sinh ra để chỉ mặt.
"""
from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bao_cao_da_lap import (BANG_SO, LOAI_BAN, LOAI_KY, TRANG_THAI_BAN,
                                       BanBaoCao, DongBanBaoCao)
from app.models.core import ROLES, User
from app.services import bctc as BCTC
from app.services import chu_ky as _CK
from app.services import pham_vi_phap_nhan as PV
from app.services import rules as R

LOAI_CHU_KY = "ban_bao_cao"


class SaiBanBaoCao(ValueError):
    """Không lập/ký được, kèm câu nói ra vì sao."""


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 1. LẬP — tính từ sổ rồi ĐÓNG BĂNG
# ──────────────────────────────────────────────────────────────────────────────────────────────
def _dong_tu_bo(rep: dict) -> list[dict]:
    """Bộ báo cáo → danh sách dòng đóng băng.

    Đọc ĐÚNG ba khóa mà `BCTC.bctc()` trả về. Dòng tiêu đề (không có mã chỉ tiêu) bị bỏ: nó là
    chữ, không phải số, và mẫu báo cáo đã có sẵn chữ ấy.
    """
    out: list[dict] = []
    for bang in BANG_SO:
        for r in rep.get(bang) or []:
            ma = (r.get("code") or "").strip()
            if not ma:
                continue
            out.append({"bang": bang, "ma": ma, "ten": (r.get("name") or "")[:300],
                        "gia_tri": float(r.get("now") or 0.0),
                        "gia_tri_ss": float(r.get("prev") or 0.0)})
    return out


def lap(db: Session, u: User, *, loai: str = "bctc", loai_ky: str, ky: str,
        tu_ngay: date, den_ngay: date, so_sanh_den: date | None = None,
        nguoi_dai_dien: str = "", ghi_chu: str = "", company_id: int | None = None) -> BanBaoCao:
    """Tính bộ báo cáo tại thời điểm NÀY và đóng băng nó thành một bản nháp."""
    if loai not in LOAI_BAN:
        raise SaiBanBaoCao(f"Loại báo cáo “{loai}” chưa khai ở `LOAI_BAN`.")
    if loai_ky not in LOAI_KY:
        raise SaiBanBaoCao(f"Loại kỳ “{loai_ky}” chưa khai ở `LOAI_KY`.")
    if not (ky or "").strip():
        raise SaiBanBaoCao("Phải đặt tên kỳ — một bản không nói được nó của kỳ nào thì không ai "
                           "tìm lại được nó.")
    if den_ngay < tu_ngay:
        raise SaiBanBaoCao("Đến ngày sớm hơn từ ngày.")

    rep = BCTC.bctc(db, den_ngay, tu_ngay, so_sanh_den)
    dong = _dong_tu_bo(rep)
    if not dong:
        raise SaiBanBaoCao("Bộ báo cáo không có chỉ tiêu nào — không đóng băng một bản rỗng.")

    tham_so = {"loai": loai, "loai_ky": loai_ky, "ky": ky,
               "tu_ngay": f"{tu_ngay:%Y-%m-%d}", "den_ngay": f"{den_ngay:%Y-%m-%d}",
               "so_sanh_den": f"{so_sanh_den:%Y-%m-%d}" if so_sanh_den else None,
               "company_id": company_id,
               # Hai cờ của chính bộ báo cáo, giữ lại để sau này đọc được bản đã lập có cân hay
               # không mà không phải tính lại.
               "balanced": bool(rep.get("balanced")),
               "unposted_pl": float(rep.get("unposted_pl") or 0.0)}

    b = BanBaoCao(company_id=company_id, loai=loai, loai_ky=loai_ky, ky=ky.strip()[:24],
                  tu_ngay=tu_ngay, den_ngay=den_ngay, so_sanh_den=so_sanh_den,
                  tham_so=json.dumps(tham_so, ensure_ascii=False),
                  nguoi_dai_dien=(nguoi_dai_dien or "").strip()[:160],
                  ngay_lap=date.today(), ghi_chu=(ghi_chu or "").strip(),
                  trang_thai="nhap",
                  lap_boi=u.username, lap_vai=u.role, lap_luc=datetime.now())
    db.add(b)
    db.flush()
    for d in dong:
        db.add(DongBanBaoCao(ban_id=b.id, **d))
    R.audit(db, u.username, u.role, "lap_ban_bao_cao", f"bao_cao_da_lap:{b.id}",
            after={"ky": b.ky, "so_dong": len(dong), "balanced": tham_so["balanced"]})
    db.commit()
    db.refresh(b)
    return b


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 2. TRÌNH · KÝ · TỪ CHỐI
# ──────────────────────────────────────────────────────────────────────────────────────────────
def trinh(db: Session, u: User, b: BanBaoCao) -> dict:
    """Kế toán trình bản nháp lên cho Chủ tịch ký."""
    if b.trang_thai != "nhap":
        raise SaiBanBaoCao(f"Bản này không còn ở trạng thái nháp (đang “{b.trang_thai}”).")
    if not b.nguoi_dai_dien:
        raise SaiBanBaoCao("Phải điền người đại diện theo pháp luật trước khi trình — đó là tên "
                           "sẽ in dưới bộ báo cáo.")
    b.trang_thai, b.trinh_boi, b.trinh_luc = "cho_ky", u.username, datetime.now()
    R.audit(db, u.username, u.role, "trinh_ban_bao_cao", f"bao_cao_da_lap:{b.id}",
            after={"ky": b.ky})
    db.commit()
    return {"message": f"Đã trình bản {b.ky}. Chờ Chủ tịch HĐQT ký."}


def ky(db: Session, u: User, b: BanBaoCao) -> dict:
    """Chủ tịch ký. Bản cũ CÙNG (loại, pháp nhân, kỳ) chuyển sang “đã bị thay thế”, KHÔNG xoá."""
    if b.trang_thai != "cho_ky":
        raise SaiBanBaoCao(f"Bản này không còn chờ ký (trạng thái {b.trang_thai}).")
    can = _CK.can_ky(LOAI_CHU_KY)
    if u.role not in can:
        raise SaiBanBaoCao("Chỉ " + " và ".join(ROLES.get(v, v) for v in can)
                           + " ký bản báo cáo được.")
    if u.username in (b.lap_boi, b.trinh_boi):
        raise SaiBanBaoCao("Người lập hoặc người trình không tự ký. Việc trình và việc ký phải là "
                           "hai người, bất kể hai người ấy to đến đâu.")

    cu = ban_da_ky(db, b.loai, b.ky, b.company_id)
    if cu and cu.id != b.id:
        cu.trang_thai = "da_thay_the"
        b.thay_the_id = cu.id
    b.ky_boi, b.ky_vai, b.ky_luc, b.trang_thai = u.username, u.role, datetime.now(), "da_ky"
    R.audit(db, u.username, u.role, "ky_ban_bao_cao", f"bao_cao_da_lap:{b.id}",
            before={"thay_the": cu.id if cu else None}, after={"ky": b.ky})
    db.commit()
    return {"message": f"Đã ký bản báo cáo kỳ {b.ky}. Từ nay màn hình đọc bản này khi bật “Lấy "
                       f"từ bản đã ký”."
                       + (f" Bản ký trước (#{cu.id}) chuyển sang “đã bị thay thế”." if cu and cu.id != b.id else "")}


def tu_choi(db: Session, u: User, b: BanBaoCao, ly_do: str) -> dict:
    if b.trang_thai != "cho_ky":
        raise SaiBanBaoCao(f"Bản này không còn chờ ký (trạng thái {b.trang_thai}).")
    if u.role not in _CK.can_ky(LOAI_CHU_KY):
        raise SaiBanBaoCao("Chỉ người ký của bản báo cáo mới từ chối được.")
    if not (ly_do or "").strip():
        raise SaiBanBaoCao("Phải ghi lý do từ chối — người lập cần biết sửa gì để lập lại.")
    b.trang_thai, b.ky_boi, b.ky_vai, b.ky_luc = "tu_choi", u.username, u.role, datetime.now()
    b.tu_choi_ly_do = ly_do.strip()[:500]
    R.audit(db, u.username, u.role, "tu_choi_ban_bao_cao", f"bao_cao_da_lap:{b.id}",
            after={"ly_do": b.tu_choi_ly_do})
    db.commit()
    return {"message": f"Đã từ chối bản {b.ky}."}


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 3. ĐỌC RA
# ──────────────────────────────────────────────────────────────────────────────────────────────
def ban_da_ky(db: Session, loai: str = "bctc", ky: str | None = None,
              company_id: int | None = None) -> BanBaoCao | None:
    """Bản ĐÃ KÝ còn hiệu lực của một kỳ. `ky` rỗng thì lấy bản có ngày kết thúc MỚI NHẤT.

    Trả `None` khi chưa có bản nào — RỖNG, không phải một bản trống. Nơi gọi phải nói ra điều ấy
    thành một câu người đọc được, chứ không trả về một bộ báo cáo toàn số 0.
    """
    q = select(BanBaoCao).where(BanBaoCao.trang_thai == "da_ky", BanBaoCao.loai == loai)
    if ky:
        q = q.where(BanBaoCao.ky == ky)
    if company_id is not None:
        q = q.where(BanBaoCao.company_id == company_id)
    return db.execute(q.order_by(BanBaoCao.den_ngay.desc(), BanBaoCao.id.desc())).scalars().first()


def du_lieu(b: BanBaoCao) -> dict:
    """Bản đã lập → ĐÚNG hình dáng mà màn hình vẫn đọc từ `BCTC.bctc()`.

    Giữ nguyên hình dáng là có chủ ý: màn hình không cần biết con số đến từ sổ hay từ bản đã ký,
    nên không có nhánh `if` nào trên giao diện — chỉ có một cờ `tu_ban` để người đọc biết mình
    đang nhìn cái gì.
    """
    # Dòng TỔNG (có công thức trong mẫu) in đậm trên màn hình. Lấy từ chính MẪU TT99 chứ không
    # lưu thêm một cột: đậm hay không là chuyện TRÌNH BÀY của mẫu, không phải một con số của bản,
    # và lưu nó vào bản là để hai nơi nói hai kiểu khi mẫu đổi.
    nhom = {bg: {m["code"] for m in BCTC.MAU.get(bg, []) if m.get("formula")} for bg in BANG_SO}
    nhom["lctt"] = {"08", "20", "30", "40", "50", "70"}
    bang: dict[str, list] = {k: [] for k in BANG_SO}
    for d in sorted(b.dong, key=lambda x: x.id):
        bang.setdefault(d.bang, []).append(
            {"code": d.ma, "name": d.ten, "note": "",
             "now": float(d.gia_tri), "prev": float(d.gia_tri_ss),
             "group": d.ma in nhom.get(d.bang, set())})
    try:
        ts = json.loads(b.tham_so or "{}")
    except ValueError:
        ts = {}
    return {"tu_ban": True, "ban_id": b.id, "ky": b.ky,
            "since": b.tu_ngay, "upto": b.den_ngay, "compare_upto": b.so_sanh_den,
            "nguoi_dai_dien": b.nguoi_dai_dien, "ngay_lap": b.ngay_lap,
            "ky_boi": b.ky_boi, "ky_luc": b.ky_luc,
            "balanced": bool(ts.get("balanced")), "unposted_pl": float(ts.get("unposted_pl") or 0.0),
            **bang}


def mot_ban(b: BanBaoCao, day_du: bool = False) -> dict:
    d = {"id": b.id, "loai": b.loai, "loai_ky": b.loai_ky, "ky": b.ky,
         "tu_ngay": b.tu_ngay, "den_ngay": b.den_ngay, "so_sanh_den": b.so_sanh_den,
         "company_id": b.company_id, "nguoi_dai_dien": b.nguoi_dai_dien, "ngay_lap": b.ngay_lap,
         "trang_thai": b.trang_thai, "trang_thai_ten": TRANG_THAI_BAN.get(b.trang_thai, b.trang_thai),
         "lap_boi": b.lap_boi, "lap_luc": b.lap_luc, "trinh_boi": b.trinh_boi,
         "ky_boi": b.ky_boi, "ky_luc": b.ky_luc, "tu_choi_ly_do": b.tu_choi_ly_do,
         "thay_the_id": b.thay_the_id, "so_dong": len(b.dong), "ghi_chu": b.ghi_chu}
    if day_du:
        d["du_lieu"] = du_lieu(b)
    return d


def danh_sach(db: Session, u: User, loai: str = "bctc",
              company_id: int | None = None) -> list[dict]:
    q = select(BanBaoCao).where(BanBaoCao.loai == loai)
    if company_id is not None:
        q = q.where(BanBaoCao.company_id == company_id)
    q = PV.loc(q, BanBaoCao, u)
    rows = db.execute(q.order_by(BanBaoCao.den_ngay.desc(), BanBaoCao.id.desc())).scalars().all()
    return [mot_ban(b) for b in rows]
