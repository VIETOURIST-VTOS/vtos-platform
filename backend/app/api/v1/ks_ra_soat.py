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
                   "cham_tran": len(rows) > NT.TRAN_DONG,
                   # Ai nhập và nhập trong bao lâu. Không có cột này thì "hai mươi lăm nghìn dòng nhập
                   # tay" và "một bản nhập hàng loạt bị gán nhầm" trông giống hệt nhau.
                   "theo_nguoi": NT.thong_ke_nguoi(db, ng, a, b)})
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


@router.get("/lo-nap")
def lo_nap(limit: int = 100, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """K5 – từng lô nạp với bốn con số DÒNG và bốn con số TIỀN, kèm phần bộ đối chiếu KHÔNG che được.

    Cột `cua_khong_ghi_so` là phần quan trọng nhất của bảng này: nó liệt kê những cửa nạp hàng loạt
    ghi thẳng vào bảng mà không để lại nhật ký lô. Một bộ đối chiếu im lặng về vùng mù của mình khiến
    người đọc yên tâm sai chỗ.
    """
    from app.services import ks_nap_lo as NL
    return NL.bang(db, limit)


@router.get("/cua-nhap")
def cua_nhap(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Mỗi bảng dữ liệu có cửa nào để người dùng đưa số liệu vào: tải tệp, nhập tay, hay máy sinh.

    `khong_cua` là cột phải luôn rỗng. Có tên trong đó nghĩa là hệ thống đang cần một con số mà không
    có đường nào cho người nhập nó – theo ranh giới 09/9/2026 thì đó là việc còn thiếu.
    """
    from app.services import ks_cua_nhap as CN
    return CN.bang(db)


@router.get("/cot-tien/phan-le")
def cot_tien_phan_le(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """K1 – bao nhiêu dòng sẽ bị LÀM TRÒN nếu đổi cột số thực nhị phân sang numeric(18,2)?

    Phải chạy TRƯỚC khi đổi kiểu: đổi rồi thì đếm luôn ra 0, vì cột mới không giữ nổi chữ số thứ ba.
    Cửa sổ đo này chỉ mở một lần. CHỈ ĐỌC.
    """
    return CT.dem_phan_le(db)


@router.get("/cot-tien/so-0")
def cot_tien_so_0(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """K2 – mỗi cột "mặc định 0, không cho rỗng" đang có bao nhiêu dòng mang số 0.

    Con số để quyết TỪNG cột là sửa hay giữ, thay vì quyết cả 91 cột bằng một cảm giác chung. CHỈ ĐỌC.
    """
    return CT.dem_so_0(db)
