"""Cửa NỘI BỘ của đánh giá sau tour: bảng điểm và ba con số của báo cáo tuần.

Tách hẳn khỏi `khao_sat_cong_khai.py` — cửa công khai và cửa nội bộ không ở chung một tệp, để
người đọc không phải dò từng hàm xem cái nào cần đăng nhập.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.cskh import CareTicket
from app.models.danh_gia import DG_DOI_TUONG
from app.services import danh_gia as DG
from app.services import dem_luot as DEM

# Ai XEM bảng điểm. Hẹp đúng bằng dòng "/danh-gia" của MENU_ROLES.
#
# `nv_kd` và `tn_kd` KHÔNG có ở đây, và đó là một quyết định chứ không phải chỗ sót: bảng này là
# bảng XẾP HẠNG so với đồng nghiệp. Nhân viên đọc lời nhận xét của chính khách mình thì tốt cho
# công việc; đọc bảng xếp hạng cả phòng thì không còn là việc của họ. Lời nhận xét của từng khách
# nằm ở màn hình chăm sóc (/cham-soc), nơi bộ lọc theo người phụ trách đã có sẵn.
XEM = ("chutich", "tgd", "bks", "robot_ks", "ptgd_doan", "ptgd_mkt",
       "tp_dh", "nv_dh", "gd_kd", "tp_kd", "nv_mkt", "hcns", "cntt")

# ═══════════ PHẠM VI XEM BẢNG ĐIỂM — Đợt HD-Q1, Chủ tịch chốt 15/10/2026 ═══════════
#
# Trước đợt này: nhân viên Marketing và nhân viên Điều hành đọc được bảng điểm hướng dẫn viên lẫn
# bảng điểm tài xế, còn Trưởng phòng Hướng dẫn và Giám đốc Đội xe — trưởng bộ phận của chính những
# người bị chấm — bị chặn 403. Đo được bằng cách đăng nhập thật từng vai.
#
# Mỗi dòng dưới đây khai ĐỦ BA điều Chủ tịch nêu: vai nào, xem được LOẠI ĐỐI TƯỢNG nào, trong
# PHẠM VI phòng nào. Phòng lấy đúng khoá của `bao_cao_phong.PHONG`, cũng là giá trị cột
# `department` của hồ sơ nhân sự — không dựng khái niệm phạm vi thứ hai.
PV_THEO_PHONG = {
    "tp_hd":     {"doi_tuong": ("hdv",),    "phong": "huong_dan"},
    "gd_doi_xe": {"doi_tuong": ("tai_xe",), "phong": "doi_xe"},
}

# Ai xem được BẢNG ĐIỂM. Rộng hơn `XEM` đúng hai vai, và hai vai ấy bị `PV_THEO_PHONG` bó lại.
#
# KHÔNG nhập hai vai này vào `XEM`: `XEM` còn gác `/chi-so` (việc gửi tin khảo sát qua Zalo, việc
# của chăm sóc khách hàng) và `/chua-tra-loi` (trả về TÊN KHÁCH và tên người bán — đúng loại dữ
# liệu Chủ tịch dặn không mở mặc nhiên). Trưởng bộ phận cần điểm của người mình, không cần hai
# thứ đó.
XEM_BANG_DIEM = XEM + tuple(PV_THEO_PHONG)


def _pham_vi(u: User, doi_tuong: str) -> str | None:
    """Ba lớp cổng: vai trò → loại đối tượng → phạm vi. Trả về khoá phòng, hoặc None = toàn công ty.

    CHẶN Ở MÁY CHỦ, không ở màn hình. Đổi tham số trên đường dẫn, gọi thẳng API, xuất tệp hay mở
    chi tiết đều đi qua đúng hàm này — nguyên văn điều Chủ tịch dặn ngày 15/10/2026.

    KHÔNG CÓ LOẠI HỢP LỆ THÌ TỪ CHỐI, tuyệt đối không lùi về "xem tất cả". Một cổng mà lúc không
    khớp thì mở toang là một cổng chỉ tồn tại khi mọi thứ đã đúng.
    """
    from app.services.vai_ke_thua import vai_va_cha
    for v in vai_va_cha(u.role):
        d = PV_THEO_PHONG.get(v)
        if d is None:
            continue
        if doi_tuong not in d["doi_tuong"]:
            raise HTTPException(403, {
                "gate": "PHAM_VI_BANG_DIEM",
                "message": f"Vai «{v}» chỉ xem được bảng điểm "
                           f"{', '.join(DG_DOI_TUONG.get(x, x) for x in d['doi_tuong'])}, "
                           f"không xem được «{DG_DOI_TUONG.get(doi_tuong, doi_tuong)}»."})
        return d["phong"]
    return None


# Ai GHI HỘ khi khách không dùng Zalo. Đây là khối Kinh doanh và Marketing — người còn gọi khách.
GHI_HO = ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt", "ptgd_mkt", "nv_dh", "tp_dh")

router = APIRouter(prefix="/api/v1/danh-gia", tags=["danh-gia"])


class MotMuc(BaseModel):
    doi_tuong: str
    doi_tuong_id: int | None = None
    doi_tuong_ten: str = ""
    diem: int | None = None
    nhan_xet: str = ""


class GhiHo(BaseModel):
    diem: list[MotMuc] = []


def _ky(tu: str, den: str) -> tuple[date, date]:
    """Mặc định 30 ngày gần nhất. Không có mặc định thì màn hình mở ra trống và người dùng tưởng
    hệ thống chưa có dữ liệu."""
    d2 = date.fromisoformat(den) if den else date.today()
    d1 = date.fromisoformat(tu) if tu else d2 - timedelta(days=30)
    if d1 > d2: raise HTTPException(422, "Khoảng ngày ngược")
    return d1, d2


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM_BANG_DIEM, mo_ta="đánh giá sau tour")),
         db: Session = Depends(get_db)):
    return {"doi_tuong": DG_DOI_TUONG}


@router.get("/bang-diem/{doi_tuong}")
def bang_diem(doi_tuong: str, tu: str = "", den: str = "", chi_khach: bool = True,
              u: User = Depends(require_roles(*XEM_BANG_DIEM, mo_ta="bảng điểm đánh giá")),
              db: Session = Depends(get_db)):
    """`chi_khach` mặc định BẬT: chỉ cộng điểm khách tự chấm. Tắt đi thì cộng cả phần nhân viên ghi
    hộ — mở được để so hai con số, nhưng phải bấm, vì đó không phải cách đọc mặc định.

    PHẠM VI: trưởng bộ phận chỉ thấy người của phòng mình — xem `_pham_vi`. Phép kiểm chạy TRƯỚC
    khi đọc dữ liệu, và cổng đó là cổng duy nhất, nên đổi tham số trên đường dẫn không vượt được.
    """
    phong = _pham_vi(u, doi_tuong)
    d1, d2 = _ky(tu, den)
    kq = DG.bang_diem(db, doi_tuong, d1, d2, chi_khach, chi_phong=phong)
    DEM.ghi(u, "bang_diem", len(kq.get("rows") or []))
    return kq


@router.get("/chi-so")
def chi_so(tu: str = "", den: str = "",
           u: User = Depends(require_roles(*XEM, mo_ta="chỉ số khảo sát")),
           db: Session = Depends(get_db)):
    """Ba con số đứng cạnh nhau: đã gửi · đã trả lời · không gửi được."""
    d1, d2 = _ky(tu, den)
    kq = DG.chi_so(db, d1, d2)
    DEM.ghi(u, "chi_so", 0)
    return kq


@router.get("/chua-tra-loi")
def chua_tra_loi(tu: str = "", den: str = "",
                 u: User = Depends(require_roles(*GHI_HO, *XEM, mo_ta="khách chưa chấm điểm")),
                 db: Session = Depends(get_db)):
    """Danh sách khách đã được mời mà chưa chấm — việc của mục 6 trong đề xuất.

    Cắt theo phạm vi người xem: nhân viên chỉ thấy khách của mình. Đây là cửa ĐỌC đi kèm cửa GHI
    HỘ ngay dưới — một danh sách việc mà không bấm vào làm được gì thì là một bảng tin.
    """
    from app.services import access as AC
    d1, d2 = _ky(tu, den)
    vis = AC.sales_ids_visible(db, u)
    rows = DG.chua_tra_loi(db, d1, d2, vis)
    DEM.ghi(u, "chua_tra_loi", len(rows or []))
    return {"rows": rows}


@router.post("/ghi-ho/{care_id}")
def ghi_ho(care_id: int, data: GhiHo,
           u: User = Depends(require_roles(*GHI_HO, mo_ta="ghi đánh giá hộ khách")),
           db: Session = Depends(get_db)):
    """Khách không dùng Zalo, hoặc gọi điện xin sửa. Bản ghi mang `nguon = "nhan_vien"` — và cột ấy
    là thứ giữ cho bảng điểm còn đọc được."""
    c = db.get(CareTicket, care_id)
    if not c: raise HTTPException(404, "Không có phiếu chăm sóc")
    return DG.ghi_ho(db, u, c, data.model_dump())


# ═══════════ CỬA ĐẾM — Đợt HD-Q2a, Chủ tịch chốt 16/10/2026 ═══════════
#
# Chủ tịch duyệt khuôn «đếm được trước, chặn sau» ở HD-9 và HD-12, và nhắc lại ở HD-Q1: siết một
# quyền người ta dùng hằng ngày mà không đếm trước là sáng hôm sau một phòng mở máy không thấy
# việc của mình. Cửa này là phần ĐẾM. Nó KHÔNG đổi quyền của ai.
#
# Danh sách vai hẹp hơn mọi cửa khác trong tệp, và cố ý: đây là bảng nói ai đang mở màn hình nào
# bao nhiêu lần — một dạng theo dõi người lao động. Chỉ Chủ tịch, Tổng giám đốc, Ban Kiểm soát và
# Công nghệ thông tin đọc được, và chỉ ở mức ĐẾM, không có nội dung họ đã xem.
#
# Cửa này KHÔNG tự đếm chính nó: nếu đếm, thì mỗi lần Chủ tịch mở bảng lại tự cộng thêm một lượt
# vào chính bảng ấy, và con số sẽ nói về người đi đo chứ không nói về người bị đo.
DEM_XEM = ("chutich", "tgd", "bks", "robot_ks", "cntt")


@router.get("/dem-luot")
def dem_luot(tu: str = "", den: str = "",
             u: User = Depends(require_roles(*DEM_XEM, mo_ta="đếm lượt mở cửa đánh giá")),
             db: Session = Depends(get_db)):
    """Mỗi người × mỗi cửa một dòng: bao nhiêu lượt, bao nhiêu phút khác nhau, bao nhiêu ngày,
    bao nhiêu dòng dữ liệu đã trả về. Xem `services/dem_luot.py` để biết vì sao có cột số phút."""
    d1, d2 = _ky(tu, den)
    return DEM.bang(db, d1, d2)
