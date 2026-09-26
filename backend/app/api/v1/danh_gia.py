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

# Ai XEM bảng điểm. Hẹp đúng bằng dòng "/danh-gia" của MENU_ROLES.
#
# `nv_kd` và `tn_kd` KHÔNG có ở đây, và đó là một quyết định chứ không phải chỗ sót: bảng này là
# bảng XẾP HẠNG so với đồng nghiệp. Nhân viên đọc lời nhận xét của chính khách mình thì tốt cho
# công việc; đọc bảng xếp hạng cả phòng thì không còn là việc của họ. Lời nhận xét của từng khách
# nằm ở màn hình chăm sóc (/cham-soc), nơi bộ lọc theo người phụ trách đã có sẵn.
XEM = ("chutich", "tgd", "bks", "robot_ks", "ptgd_doan", "ptgd_mkt",
       "tp_dh", "nv_dh", "gd_kd", "tp_kd", "nv_mkt", "hcns", "cntt")

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
def meta(u: User = Depends(require_roles(*XEM, mo_ta="đánh giá sau tour")), db: Session = Depends(get_db)):
    return {"doi_tuong": DG_DOI_TUONG}


@router.get("/bang-diem/{doi_tuong}")
def bang_diem(doi_tuong: str, tu: str = "", den: str = "", chi_khach: bool = True,
              u: User = Depends(require_roles(*XEM, mo_ta="bảng điểm đánh giá")),
              db: Session = Depends(get_db)):
    """`chi_khach` mặc định BẬT: chỉ cộng điểm khách tự chấm. Tắt đi thì cộng cả phần nhân viên ghi
    hộ — mở được để so hai con số, nhưng phải bấm, vì đó không phải cách đọc mặc định."""
    d1, d2 = _ky(tu, den)
    return DG.bang_diem(db, doi_tuong, d1, d2, chi_khach)


@router.get("/chi-so")
def chi_so(tu: str = "", den: str = "",
           u: User = Depends(require_roles(*XEM, mo_ta="chỉ số khảo sát")),
           db: Session = Depends(get_db)):
    """Ba con số đứng cạnh nhau: đã gửi · đã trả lời · không gửi được."""
    d1, d2 = _ky(tu, den)
    return DG.chi_so(db, d1, d2)


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
    return {"rows": DG.chua_tra_loi(db, d1, d2, vis)}


@router.post("/ghi-ho/{care_id}")
def ghi_ho(care_id: int, data: GhiHo,
           u: User = Depends(require_roles(*GHI_HO, mo_ta="ghi đánh giá hộ khách")),
           db: Session = Depends(get_db)):
    """Khách không dùng Zalo, hoặc gọi điện xin sửa. Bản ghi mang `nguon = "nhan_vien"` — và cột ấy
    là thứ giữ cho bảng điểm còn đọc được."""
    c = db.get(CareTicket, care_id)
    if not c: raise HTTPException(404, "Không có phiếu chăm sóc")
    return DG.ghi_ho(db, u, c, data.model_dump())
