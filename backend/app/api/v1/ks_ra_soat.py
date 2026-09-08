"""K1, K2, K6 – bàn làm việc cho phần NGƯỜI QUYẾT của robot Kiểm soát.

Robot liệt kê và đề xuất; ba đường dẫn dưới đây là chỗ người trả lời. Vai trò bks (robot) CỐ TÌNH
không nằm trong nhóm được quyết: robot vừa xếp loại vừa chốt xếp loại thì con số nó báo lên Chủ tịch
là con số nó tự đặt ra.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.services import ks_cot_tien as CT
from app.services import ky_thuat as KT

router = APIRouter(prefix="/api/v1/kiem-soat", tags=["kiem-soat"])

XEM = ("chutich", "tgd", "bks", "cntt", "ketoan")
# Ai được QUYẾT một cột là tiền hay không, và sửa hay giữ: Kế toán trưởng (nghiệp vụ) và CNTT (kỹ
# thuật), Chủ tịch/TGĐ đi qua FULL_ACCESS. Không có bks.
QUYET = ("ketoan", "cntt")


# ============================ BÀN RÀ SOÁT CỘT TIỀN – ĐỊA CHỈ RIÊNG ============================
#
# Chủ tịch quyết 08/9/2026: Kế toán KHÔNG xem màn hình Kiểm soát. Nhưng Kế toán trưởng vẫn là người
# QUYẾT một cột có phải tiền hay không.
#
# Hai việc đó ở chung một tiền tố đường dẫn thì không tách quyền được, vì hàng rào phạm vi ngoài chỉ
# phân biệt tới ĐOẠN ĐẦU của đường dẫn (/api/v1/kiem-soat). Cho Kế toán chạm tiền tố đó là mở luôn
# hậu kiểm số nhập tay và sự kiện kỹ thuật – tức là phòng ban đọc kết quả giám sát chính mình.
#
# Nên bàn rà soát có ĐỊA CHỈ RIÊNG. Cùng một hàm xử lý, khác đường vào: màn hình Kiểm soát của lãnh
# đạo gọi đường cũ, màn hình Rà soát cột tiền của Kế toán gọi đường này. Đây không phải bí danh cho
# gọn – nó là cách duy nhất để hàng rào ngoài nói được điều Chủ tịch đã quyết.
rst = APIRouter(prefix="/api/v1/ra-soat-cot-tien", tags=["ra-soat-cot-tien"])


@router.get("/cot-tien")
@rst.get("")
def cot_tien(loc: str = "", u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Sổ rà soát cột tiền. loc: tien | khong_tien | chua_ro | thieu_thanh_0 | can_doi_kieu."""
    return CT.bang(db, loc)


class QuyetDong(BaseModel):
    id: int
    quyet_nguoi: str = ""      # "" giữ nguyên · tien · khong_tien
    quyet_k2: str = ""         # "" giữ nguyên · sua · giu
    ghi_chu: str | None = None


class QuyetIn(BaseModel):
    dong: list[QuyetDong] = []


@router.post("/cot-tien/quyet")
@rst.post("/quyet")
def quyet_cot_tien(data: QuyetIn, u: User = Depends(require_roles(*QUYET)),
                   db: Session = Depends(get_db)):
    if not data.dong: raise HTTPException(422, "Chưa chọn dòng nào để quyết")
    try:
        return CT.quyet(db, u, [d.model_dump() for d in data.dong])
    except ValueError as ex:
        db.rollback(); raise HTTPException(422, str(ex))


@router.get("/su-kien-ky-thuat")
def su_kien(ngay: int = 7, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Lỗi 5xx, đường dẫn chậm, tác vụ nền hỏng, lần khởi động máy chủ."""
    return KT.bang(db, ngay)


@router.get("/nhap-tay/do-nguong")
def do_nguong(thang: str = "", lan: str = "2,3,5,10",
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """K3 – bảng “ngưỡng này ra bao nhiêu dòng”, chạy trên dữ liệu thật. CHỈ ĐỌC.

    Có bảng này thì người quyết chọn ngưỡng bằng số liệu chứ không bằng cảm giác – và đó là điều kiện
    để tiêu chí nghiệm thu “danh sách đọc hết trong mười phút” có nghĩa.
    """
    from datetime import date
    from app.services import ks_nhap_tay as NT
    return NT.do_nguong(db, thang or f"{date.today():%Y-%m}", lan)


@router.get("/nhap-tay/nguon")
def nhap_tay_nguon(thang: str = "", u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Mỗi nguồn có bao nhiêu dòng do NGƯỜI nhập trong tháng, và tổng tiền. Dùng để biết quy mô trước
    khi chạy cả bộ hậu kiểm – một nguồn vài chục nghìn dòng thì phải xử lý khác."""
    from datetime import date
    from app.services import ks_nhap_tay as NT
    th = thang or f"{date.today():%Y-%m}"
    a, b = NT._khoang_thang(th); kho: dict = {}
    ra = []
    for ng in NT.NGUON:
        import time as _t
        t0 = _t.perf_counter()
        rows = NT._doc(db, ng, a, b, kho)
        ra.append({"nguon": ng["ma"], "ten": ng["ten"], "bang": ng["bang"], "so_dong": len(rows),
                   "tong_tien": sum(x["tien"] for x in rows), "giay": round(_t.perf_counter() - t0, 2),
                   "cham_tran": len(rows) > NT.TRAN_DONG})
    return {"thang": th, "nguon": ra, "tong_giay": round(sum(x["giay"] for x in ra), 2)}


@router.get("/nhap-tay")
def nhap_tay(thang: str = "", u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Danh sách dấu hiệu bất thường của một tháng, theo ngưỡng đang hiệu lực."""
    from datetime import date
    from app.services import ks_nhap_tay as NT
    th = thang or f"{date.today():%Y-%m}"
    kho: dict = {}
    ds = NT.quet_thang(db, th, None, kho)
    theo = {}
    for d in ds: theo[d["loai"]] = theo.get(d["loai"], 0) + 1
    return {"thang": th, "loai": NT.LOAI_TEN, "nguon": {n["ma"]: n["ten"] for n in NT.NGUON},
            "tong": len(ds), "theo_dau_hieu": theo,
            # Giây của từng dấu hiệu: bộ này chạy trong vòng quét robot trên máy chủ 0,5 CPU, nên
            # "chậm ở đâu" là dữ kiện vận hành chứ không phải chuyện gỡ lỗi tạm thời.
            "giay_moi_dau_hieu": kho.get("_dong_ho", {}), "rows": ds}
