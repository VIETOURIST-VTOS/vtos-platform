"""Bảng lãi lỗ theo tour và theo khách – hai lớp, một chuẩn phép tính.

Cửa này CHỈ ĐỌC. Mọi con số đều lấy từ app/services/lai_lo_tour.py, không có phép tính nào viết lại ở
đây: bốn công thức lãi lỗ song song trong VTOS sinh ra chính vì mỗi màn hình từng tự cộng lấy một kiểu.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import Tour, User
from app.services import lai_lo_tour as LL
from app.services import pham_vi_phap_nhan as PV

router = APIRouter(prefix="/api/v1/lai-lo-tour", tags=["lai-lo-tour"])

# Lãi lỗ là số quản trị: Chủ tịch, TGĐ, Phó TGĐ đoàn, Điều hành, Kế toán, Kiểm soát, CNTT.
# Sale KHÔNG có trong danh sách – họ xem doanh thu và công nợ của booking mình phụ trách ở màn hình
# bán hàng, còn giá vốn của chuyến thì không thuộc phạm vi của họ.
XEM = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt")
SUA_HOA_DON = ("tp_dh", "nv_dh", "ketoan", "cntt")


@router.get("")
def bang(tu: date | None = None, den: date | None = None, loai: str = "ghep",
         trang_thai: str = "", gioi_han: int = 200, bo_qua: int = 0,
         u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """loai: ghep (tour ghép) | le (dịch vụ lẻ) | tat_ca.

    Mặc định 'ghep' vì trộn tour ghép với dịch vụ lẻ làm hỏng cả hai: dịch vụ lẻ có giá vốn theo từng
    khách, tour ghép thì không, nên cộng chung một bảng là cộng hai loại số khác nhau.
    """
    if loai not in ("ghep", "le", "tat_ca"):
        raise HTTPException(422, "loai phải là ghep / le / tat_ca")
    return LL.bang(db, u, tu=tu, den=den, loai=loai, trang_thai=trang_thai,
                   gioi_han=gioi_han, bo_qua=bo_qua)


def _tour_trong_pham_vi(db: Session, tid: int, u: User) -> Tour:
    """Lấy tour, và CHẶN nếu nó nằm ngoài phạm vi pháp nhân của phiên đăng nhập.

    Lọc theo pháp nhân trong VTOS hiện chỉ áp ở các cửa DANH SÁCH; cửa lấy một bản ghi theo mã số thì
    không kiểm. Ở danh sách thì đủ để không ai vô tình nhìn thấy, nhưng ai gõ thẳng mã số vẫn đọc được
    – mà đây là màn hình lãi lỗ, tức là đúng loại số không nên rò sang pháp nhân khác.
    """
    t = db.get(Tour, tid)
    if not t:
        raise HTTPException(404, "Không có tour")
    cid = PV.pham_vi(u)
    # Hồ sơ CHƯA GẮN pháp nhân vẫn cho xem – bỏ qua chúng là giấu luôn phần dữ liệu cần đi gán nhất.
    if cid is not None and t.company_id is not None and t.company_id != cid:
        raise HTTPException(403, "Tour thuộc pháp nhân khác – ngoài phạm vi của tài khoản")
    return t


@router.get("/{tid}")
def chi_tiet(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Lớp 2: khách của tour và chi phí theo nhà cung cấp (kèm mã số thuế, địa chỉ, số hoá đơn)."""
    return LL.chi_tiet(db, _tour_trong_pham_vi(db, tid, u))


class HoaDonIn(BaseModel):
    """Cửa nhập hoá đơn đầu vào cho một dòng chi phí.

    Cả bốn ô đều cho phép RỖNG: người nhập có thể mới cầm được số hoá đơn mà chưa có ngày, hoặc ngược
    lại. Ép nhập đủ mới cho lưu là đẩy người ta sang ghi ra giấy rồi nhập sau – và "nhập sau" thì
    thường là không bao giờ.
    """
    so_hoa_don: str | None = None
    ngay_hoa_don: date | None = None
    vat_hoa_don: float | None = None
    supplier_id: int | None = None


@router.put("/dong-chi-phi/{lid}/hoa-don")
def ghi_hoa_don(lid: int, data: HoaDonIn,
                u: User = Depends(require_roles(*SUA_HOA_DON)), db: Session = Depends(get_db)):
    """Ghi số hoá đơn đầu vào lên một dòng chi phí quyết toán.

    Trước 09/9/2026 VTOS chỉ có ô đúng/sai "có hoá đơn" trên đề nghị chi. Biết CÓ hoá đơn mà không tra
    được hoá đơn NÀO thì không đối chiếu được với tờ khai thuế.
    """
    from app.models.vietrip import TourCostLine
    from app.services import rules as R

    l = db.get(TourCostLine, lid)
    if not l:
        raise HTTPException(404, "Không có dòng chi phí")
    _tour_trong_pham_vi(db, l.tour_id, u)
    def _anh(o) -> dict:
        # Nhật ký kiểm toán lưu dạng JSON và không nhận kiểu ngày – phải đổi sang chuỗi ở đây.
        # Để nguyên đối tượng ngày thì INSERT nổ ngay giữa lúc ghi nhật ký, tức là mất cả bản ghi lẫn
        # dấu vết của nó.
        return {"so_hoa_don": o.so_hoa_don,
                "ngay_hoa_don": o.ngay_hoa_don.isoformat() if o.ngay_hoa_don else None,
                "vat_hoa_don": float(o.vat_hoa_don) if o.vat_hoa_don is not None else None,
                "supplier_id": o.supplier_id}

    truoc = _anh(l)
    l.so_hoa_don = (data.so_hoa_don or "").strip()[:30] or None
    l.ngay_hoa_don = data.ngay_hoa_don
    l.vat_hoa_don = data.vat_hoa_don
    l.supplier_id = data.supplier_id
    sau = _anh(l)
    R.audit(db, u.username, u.role, "ghi_hoa_don_dau_vao", f"dong_chi_phi:{l.id}", before=truoc, after=sau)
    db.commit()
    return {"message": "Đã ghi hoá đơn đầu vào", "line_id": l.id, **sau}
