"""Báo cáo tự động trên màn hình – lọc theo NGƯỜI ĐANG ĐĂNG NHẬP.

Chỗ chặn nằm ở đây chứ không ở màn hình: màn hình chỉ vẽ thứ máy chủ trả về, nên nếu máy chủ trả về
báo cáo của mọi phòng rồi để giao diện lọc thì ai mở công cụ nhà phát triển cũng đọc được hết.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.db.session import get_db
from app.models.core import User
from app.services import bao_cao_phong as BP

router = APIRouter(prefix="/api/v1/bao-cao", tags=["bao-cao-tu-dong"])

# Một câu duy nhất cho mọi cửa: người dùng gặp hai lời giải thích khác nhau cho cùng một lần chặn
# thì tưởng là hai lỗi khác nhau.
_NGOAI_PHAM_VI = ("Báo cáo này không thuộc phạm vi của vai trò anh/chị. Trưởng phòng xem báo cáo "
                  "phòng mình; báo cáo toàn công ty dành cho Chủ tịch, Tổng giám đốc và Ban Kiểm soát.")


def _grants_an_toan(db, u):
    """Ngoại lệ đang có của người này – để màn hình NÓI RA rằng phạm vi đang rộng hơn chức danh.

    Nói ra chứ không im lặng mở: một người thấy báo cáo phòng khác mà không hiểu vì sao thì hoặc
    tưởng hệ thống lỗi, hoặc tưởng ai cũng xem được – cả hai đều tệ hơn một dòng chữ giải thích."""
    from app.services import access as AC
    try:
        return [g for g in AC._grants(db, u) if g.kind == "capability"]
    except Exception:      # noqa
        return []


@router.get("/pham-vi")
def pham_vi(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Các báo cáo người này mở được. Rỗng = màn hình nói rõ 'chưa có báo cáo nào dành cho vai trò
    của anh/chị', chứ không hiện một trang trắng."""
    ds = BP.pham_vi_cho_nguoi(db, u)
    ten = {BP.TOAN_CTY: "Toàn công ty", **{k: v["ten"] for k, v in BP.PHONG.items()}}
    return {"pham_vi": [{"ma": p, "ten": ten[p]} for p in ds],
            "ky": [{"ma": k, "ten": v} for k, v in BP.TEN_KY.items()],
            "vai_tro": u.role,
            "mo_rong_theo_nguoi": BP.NANG_LUC_MOI_PHONG in
                                  [g.value for g in _grants_an_toan(db, u)]}


@router.get("")
def xem(pham_vi: str = BP.TOAN_CTY, kind: str = "ngay", ngay: str = "",
        u: User = Depends(current_user), db: Session = Depends(get_db)):
    if pham_vi not in BP.pham_vi_cho_nguoi(db, u):
        # Nói rõ là KHÔNG THUỘC PHẠM VI, không nói "không tồn tại": người dùng cần biết mình đang
        # đứng sai chỗ chứ không phải nghi hệ thống hỏng.
        raise HTTPException(403, _NGOAI_PHAM_VI)
    try:
        moc = date.fromisoformat(ngay) if ngay else None
        return BP.bao_cao(db, kind, pham_vi, moc)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/ban-luu")
def ban_luu_danh_sach(pham_vi: str = BP.TOAN_CTY, kind: str = "",
                      u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Các kỳ ĐÃ CHỤP của một phạm vi – mới nhất trước. Chỉ liệt kê, không mở nội dung.

    Cùng hàng rào phạm vi với báo cáo đang chạy: bản lưu là cùng những con số ấy, chỉ khác thời
    điểm. Nới hàng rào ở đây là mở toàn bộ lịch sử cho người không được xem hiện tại.
    """
    if pham_vi not in BP.pham_vi_cho_nguoi(db, u):
        raise HTTPException(403, _NGOAI_PHAM_VI)
    from app.models.bao_cao_luu import BaoCaoLuu
    from sqlalchemy import select
    q = select(BaoCaoLuu).where(BaoCaoLuu.pham_vi == pham_vi)
    if kind:
        q = q.where(BaoCaoLuu.kind == kind)
    rows = db.execute(q.order_by(BaoCaoLuu.tao_luc.desc()).limit(200)).scalars().all()
    return {"pham_vi": pham_vi,
            "rows": [{"kind": r.kind, "kind_ten": BP.TEN_KY.get(r.kind, r.kind), "ky": r.ky,
                      "tu": r.tu, "den": r.den, "so_viec_do": r.so_viec_do,
                      "so_can_ra_soat": r.so_can_ra_soat, "so_chua_co_so": r.so_chua_co_so,
                      "tao_boi": r.tao_boi, "tao_luc": r.tao_luc} for r in rows]}


@router.get("/ban-luu/{kind}/{ky}")
def ban_luu_mot_ky(kind: str, ky: str, pham_vi: str = BP.TOAN_CTY,
                   u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Bảng chỉ tiêu ĐÚNG NHƯ LÚC CHỤP – kể cả cách tính của từng dòng lúc ấy.

    Không có bản lưu thì trả 404 kèm lời giải thích, KHÔNG tính tạm một bản mới. Tính tạm là cách
    người ta hỏi 'cuối tháng trước thế nào' và nhận về số của hôm nay mà không hề biết.
    """
    if pham_vi not in BP.pham_vi_cho_nguoi(db, u):
        raise HTTPException(403, _NGOAI_PHAM_VI)
    r = BP.ban_luu(db, kind, ky, pham_vi)
    if r is None:
        raise HTTPException(404, f"Chưa chụp bản lưu {kind} kỳ {ky} cho phạm vi này. Bản lưu do "
                                 f"lịch tự động chụp; kỳ chưa tới hoặc lịch chưa chạy thì chưa có, "
                                 f"và hệ thống KHÔNG tính tạm một bản mới thay vào.")
    return {"kind": r.kind, "kind_ten": BP.TEN_KY.get(r.kind, r.kind), "ky": r.ky,
            "pham_vi": r.pham_vi, "pham_vi_ten": r.pham_vi_ten, "tu": r.tu, "den": r.den,
            "chi_tieu": r.chi_tieu, "markdown": r.markdown,
            "so_viec_do": r.so_viec_do, "so_can_ra_soat": r.so_can_ra_soat,
            "so_chua_co_so": r.so_chua_co_so, "tao_boi": r.tao_boi, "tao_luc": r.tao_luc,
            "ban_chup": True}
