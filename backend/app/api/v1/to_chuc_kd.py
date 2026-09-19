"""Cửa API của cơ cấu tổ chức khối Kinh doanh.

TIỀN TỐ RIÊNG `/api/v1/to-chuc-kd`, KHÔNG GẮN VÀO NHÓM CÓ SẴN. Bài học đã trả giá hai lần trong kho
này (`/api/v1/tong-dai`, rồi `/api/v1/so-con-no` ở TC-71): gắn một cửa mới vào một tiền tố rộng cho
tiện thì mọi vai đang có tiền tố ấy được thêm CẢ NHÓM, không phải một cửa. Phần dôi ra vẫn là quyền
đã cấp, dù không ai định cấp.

HAI DANH SÁCH VAI, VÌ ĐÂY LÀ HAI VIỆC KHÁC NHAU

`XEM` rộng: cả khối Kinh doanh cần biết mình thuộc đâu và ai cùng team. Sơ đồ tổ chức không phải bí
mật — giấu nó chỉ làm người ta hỏi nhau qua Zalo.

`GHI` hẹp: chỉ Hành chính – Nhân sự, Công nghệ thông tin và Ban Tổng giám đốc. Cố ý KHÔNG có `gd_kd`
dù nghe thì hợp lý — người tự vẽ được cây tổ chức của mình là người tự cấp được phạm vi xem của
mình, và lúc ấy mọi rào phạm vi ở tầng dưới chỉ còn là trang trí. Chuyển người giữa các team là
việc có thật và làm hằng tháng, nên nếu anh Tuấn thấy quy trình qua HC-NS chậm quá thì nới bằng
NGOẠI LỆ THEO NGƯỜI (`UserGrant`, có hạn, có lý do, có người duyệt) chứ đừng nới cả vai trò.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.to_chuc_kd import DonViKD
from app.services import to_chuc_kd as TC
from app.services.access import BASE_VIEW, SALES

XEM = BASE_VIEW + SALES + ("hcns", "hanh_chinh", "ptgd_doan", "cntt")
GHI = ("chutich", "tgd", "hcns", "cntt")

router = APIRouter(prefix="/api/v1/to-chuc-kd", tags=["to-chuc-kd"])


def _ngay(s: str | None) -> date:
    if not s:
        return date.today()
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(422, f"Ngày không đọc được: {s!r}. Dạng đúng là 2026-09-19.")


@router.get("/cay")
def cay(mang: str = "le", ngay: str = "",
        u: User = Depends(require_roles(*XEM, mo_ta="cơ cấu tổ chức Kinh doanh")),
        db: Session = Depends(get_db)):
    """Cây chi nhánh → phòng → team của một mảng, kèm số người đang phân công vào từng nút.

    Trả về CẢ CÂY cho mọi vai xem được: sơ đồ tổ chức là thông tin chung. Phạm vi của người đang
    đăng nhập trả kèm ở `pham_vi` để giao diện tô đậm phần của họ — cắt DỮ LIỆU theo phạm vi là
    việc của các cửa báo cáo ở vòng sau, không phải của cửa này.
    """
    d = _ngay(ngay)
    pv = TC.pham_vi_xem(db, u, d, mang)
    return {"mang": mang, "ngay": d.isoformat(), "cay": TC.cay(db, mang, d),
            "pham_vi": pv, "xem_toan_cay": pv is None}


@router.get("/nguoi")
def nguoi(don_vi_id: int, ca_cap_duoi: bool = True, ngay: str = "",
          u: User = Depends(require_roles(*XEM, mo_ta="danh sách người trong đơn vị")),
          db: Session = Depends(get_db)):
    """Ai đang thuộc đơn vị này (và các đơn vị dưới nó, nếu `ca_cap_duoi`).

    ĐÂY LÀ CỬA CÓ CẮT PHẠM VI: danh sách người là dữ liệu, không phải sơ đồ. Nhân viên đổi
    `don_vi_id` trên URL sang team khác thì nhận 403, đúng tình huống thử của bản bàn giao V5.0.
    """
    d = _ngay(ngay)
    dv = db.get(DonViKD, don_vi_id)
    if dv is None:
        raise HTTPException(404, "Không tìm thấy đơn vị.")
    if not TC.duoc_xem(db, u, don_vi_id, d, dv.mang):
        raise HTTPException(403, "Đơn vị này nằm ngoài phạm vi của bạn.")
    ids = TC.con_chau(db, don_vi_id, d) if ca_cap_duoi else [don_vi_id]
    return {"don_vi_id": don_vi_id, "ngay": d.isoformat(), "rows": TC.nguoi_trong(db, ids, d)}


@router.get("/lich-su/{user_id}")
def lich_su(user_id: int,
            u: User = Depends(require_roles(*XEM, mo_ta="lịch sử đơn vị của một người")),
            db: Session = Depends(get_db)):
    """Đường đi của một người qua các đơn vị. Người nào cũng xem được lịch sử CỦA CHÍNH MÌNH."""
    if user_id != u.id:
        d = date.today()
        dv = TC.don_vi_cua(db, user_id, d)
        if dv is None or not TC.duoc_xem(db, u, dv.id, d, dv.mang):
            raise HTTPException(403, "Người này nằm ngoài phạm vi của bạn.")
    return {"user_id": user_id, "rows": TC.lich_su_cua(db, user_id)}


@router.get("/chua-phan-cong")
def chua_phan_cong(mang: str = "le", ngay: str = "",
                   u: User = Depends(require_roles(*XEM, mo_ta="danh sách chưa phân công")),
                   db: Session = Depends(get_db)):
    """Tài khoản kinh doanh chưa có đơn vị — danh sách đối chiếu để HC-NS chỉ định."""
    d = _ngay(ngay)
    rows = TC.chua_phan_cong(db, d, mang)
    return {"mang": mang, "ngay": d.isoformat(), "tong": len(rows), "rows": rows}


@router.get("/danh-muc")
def danh_muc(u: User = Depends(require_roles(*GHI, mo_ta="danh mục để khai cơ cấu")),
             db: Session = Depends(get_db)):
    """Pháp nhân đang hoạt động và tài khoản, để hai ô chọn của khung khai dùng.

    VÌ SAO CỬA NÀY TỒN TẠI THAY VÌ MÀN HÌNH GỌI THẲNG `/api/v1/companies` VÀ `/api/v1/access`

    Gọi thẳng thì bộ đối chiếu `test_ban_do_man_hinh_api_khong_lech_voi_giao_dien` bắt phải khai cả
    hai tiền tố ấy vào `MAN_HINH_API["/to-chuc-kd"]` — và khai xong là MỌI vai mở được màn hình này,
    kể cả `nv_kd`, được thêm TRỌN nhóm phân quyền lẫn nhóm pháp nhân. Một nhân viên kinh doanh cần
    nhìn sơ đồ team mình, không cần đọc danh sách 220 tài khoản toàn công ty.

    Nên cửa này trả đúng hai danh sách ấy, và chỉ trả cho vai GHI. Màn hình vì thế chỉ gọi duy nhất
    tiền tố `/api/v1/to-chuc-kd` — phạm vi cấp ra đúng bằng phạm vi cần dùng.
    """
    from app.models.core import Company
    from sqlalchemy import select
    cong_ty = [{"id": c.id, "code": c.code, "name": c.name}
               for c in db.execute(select(Company).where(Company.active == True)
                                   .order_by(Company.code)).scalars()]
    tai_khoan = [{"id": x.id, "username": x.username, "full_name": x.full_name, "role": x.role}
                 for x in db.execute(select(User).where(User.active == True)
                                     .order_by(User.full_name)).scalars()]
    return {"cong_ty": cong_ty, "tai_khoan": tai_khoan}


class DonViMoi(BaseModel):
    ma: str
    ten: str
    cap: str
    mang: str = "le"
    cha_id: int | None = None
    company_id: int | None = None
    hieu_luc_tu: date | None = None
    ghi_chu: str = ""


@router.post("/don-vi")
def tao_don_vi(data: DonViMoi,
               u: User = Depends(require_roles(*GHI, mo_ta="tạo đơn vị Kinh doanh")),
               db: Session = Depends(get_db)):
    try:
        dv = TC.tao_don_vi(db, u, data.ma, data.ten, data.cap, data.mang, data.cha_id,
                           data.company_id, data.hieu_luc_tu, data.ghi_chu)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": f"Đã tạo đơn vị {dv.ma}", "id": dv.id}


class DongDonVi(BaseModel):
    den_ngay: date
    ly_do: str


@router.post("/don-vi/{don_vi_id}/dong")
def dong_don_vi(don_vi_id: int, data: DongDonVi,
                u: User = Depends(require_roles(*GHI, mo_ta="đóng đơn vị Kinh doanh")),
                db: Session = Depends(get_db)):
    try:
        dv = TC.dong_don_vi(db, u, don_vi_id, data.den_ngay, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": f"Đã đóng đơn vị {dv.ma} từ {data.den_ngay}"}


class PhanCongMoi(BaseModel):
    user_id: int
    don_vi_id: int
    vai: str = "nhan_vien"
    tu_ngay: date
    den_ngay: date | None = None
    ly_do: str = ""


@router.post("/phan-cong")
def phan_cong(data: PhanCongMoi,
              u: User = Depends(require_roles(*GHI, mo_ta="phân công người vào đơn vị")),
              db: Session = Depends(get_db)):
    try:
        pc = TC.phan_cong(db, u, data.user_id, data.don_vi_id, data.vai,
                          data.tu_ngay, data.den_ngay, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": "Đã ghi phân công", "id": pc.id}


class KetThuc(BaseModel):
    den_ngay: date
    ly_do: str


@router.post("/phan-cong/{phan_cong_id}/ket-thuc")
def ket_thuc_phan_cong(phan_cong_id: int, data: KetThuc,
                       u: User = Depends(require_roles(*GHI, mo_ta="kết thúc một phân công")),
                       db: Session = Depends(get_db)):
    try:
        TC.ket_thuc_phan_cong(db, u, phan_cong_id, data.den_ngay, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": f"Đã kết thúc phân công từ {data.den_ngay}"}
