"""Cửa API màn hình Kinh doanh — doanh thu, chỉ tiêu, và xem xuống từng cấp.

TIỀN TỐ RIÊNG `/api/v1/kinh-doanh`. Bài học đã trả giá bốn lần trong kho này (`/api/v1/tong-dai`,
`/api/v1/so-con-no`, TC-73 và TC-74): gắn cửa mới vào một tiền tố rộng sẵn có là nới CẢ NHÓM cho mọi
vai đang có nhóm ấy — phần dôi ra vẫn là quyền đã cấp.

MỘT CỬA CHO CẢ HAI PHÒNG, PHÂN BIỆT BẰNG THAM SỐ `mang`

Bản bàn giao Kinh doanh Lẻ V5.0 đến trước, bản Kinh doanh Đoàn anh Tuấn gửi sau. Cửa này nhận
`mang=le` hoặc `mang=doan` và cắt phạm vi theo đúng cây của mảng ấy, nên khi bản Đoàn về thì chỉ
thêm một màn hình gọi `mang=doan`, không nhân đôi cửa. Hai cây đơn vị không dính nhau (xem
`models/to_chuc_kd.py`), nên một tham số là đủ để hai phòng không thấy số của nhau.

═══════════════════════════════════════════════════════════════════════════════════════════════
SEC-02 — PHÉP CẮT DÒNG NẰM TRÊN MÁY CHỦ, TRONG TRUY VẤN
═══════════════════════════════════════════════════════════════════════════════════════════════
Cửa này KHÔNG nhận tham số phạm vi từ trình duyệt. Không có `?don_vi_ids=`, không có `?tat_ca=1`.
Phạm vi được tính ở đây, từ phân công của chính người đăng nhập (`to_chuc_kd.pham_vi_xem`), rồi
truyền thẳng vào truy vấn. Một Team Leader gọi cửa này bằng tay cũng chỉ nhận về team mình.

Cửa `/don-vi/{id}` là chỗ dễ thủng nhất của cả vòng — nó nhận một id từ người gọi. Nên nó hỏi
`to_chuc_kd.duoc_xem` TRƯỚC khi đọc bất cứ gì, và trả 403 chứ không trả bảng rỗng: bảng rỗng làm
người ta tưởng đơn vị ấy không bán được đồng nào.

`pham_vi_xem` trả `None` nghĩa là XEM TẤT CẢ, còn DANH SÁCH RỖNG nghĩa là chưa được phân công nên
không thấy gì. Hai thứ ấy khác nhau và cả tệp này phải giữ đúng phân biệt đó — đừng viết
`if not pham_vi`.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN VAI, MỘT MÀN HÌNH
═══════════════════════════════════════════════════════════════════════════════════════════════
Giám đốc, Trưởng phòng, Team Leader, Nhân viên nhìn CÙNG MỘT màn hình; độ sâu do máy chủ quyết
theo phân công, không do màn hình tự chọn. Dựng bốn màn hình riêng thì bốn nơi cùng quyết một hàng
rào, và ngày một nơi quên thì không ai biết nơi nào.

`/toi-la-ai` trả về đúng những gì màn hình cần để vẽ: người này xem được tới cấp nào, gốc cây của
họ ở đâu, có được giao chỉ tiêu không. Màn hình dùng nó để ẩn nút, KHÔNG để cắt dòng — dòng đã
được cắt ở máy chủ rồi.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.to_chuc_kd import DonViKD
from app.services import chi_tieu_kd as CT
from app.services import doanh_thu_kd as DT
from app.services import to_chuc_kd as TC
from app.services.access import BASE_VIEW, SALES

# XEM rộng: cả khối Kinh doanh mở màn hình này hằng ngày, và Kế toán cần đối chiếu doanh thu ghi
# nhận với doanh thu tính chỉ tiêu. Dòng thì đã cắt theo phân công rồi, nên rộng ở đây không có
# nghĩa là ai cũng thấy số của người khác.
XEM = BASE_VIEW + SALES + ("hcns", "ketoan", "ptgd_doan", "cntt")

# GIAO CHỈ TIÊU hẹp: Ban Tổng giám đốc, Giám đốc Kinh doanh, Công nghệ thông tin.
#
# CÓ `gd_kd` Ở ĐÂY, khác hẳn `nguoi_ban_hang.GHI` vốn cố ý loại `gd_kd` ra — và chỗ khác nhau ấy
# đáng ghi: bật quyền BÁN cho một người là đổi doanh số của người ấy, nên người tự bật được cho
# mình là người tự cấp được doanh số cho mình. Còn GIAO CHỈ TIÊU thì ngược lại, nó là việc chính
# của một Giám đốc Kinh doanh, và hạ chỉ tiêu của chính mình xuống là thứ cấp trên nhìn thấy ngay
# trên cùng màn hình này. Không có `tp_kd`: Trưởng phòng nhận chỉ tiêu, không tự giao cho mình.
GIAO_CHI_TIEU = ("chutich", "tgd", "gd_kd", "cntt")

router = APIRouter(prefix="/api/v1/kinh-doanh", tags=["kinh-doanh"])


def _mang(m: str) -> str:
    if m not in ("le", "doan"):
        raise HTTPException(422, f"Mảng không hợp lệ: {m!r}. Chỉ có 'le' hoặc 'doan'.")
    return m


def _cuoi_ky(ky: str) -> date:
    from calendar import monthrange
    try:
        nam, thg = int(ky[:4]), int(ky[5:7])
        return date(nam, thg, monthrange(nam, thg)[1])
    except (ValueError, IndexError):
        raise HTTPException(422, f"Kỳ không đọc được: {ky!r}. Dạng đúng là 2026-10.")


def _pham_vi(db, u: User, ky: str, mang: str):
    """Phạm vi xem, tính TẠI NGÀY CUỐI KỲ — cùng mốc mà `doanh_thu_kd` xét đơn vị của người bán.

    Xét tại hôm nay thì một người vừa chuyển phòng sẽ mất luôn quyền xem báo cáo kỳ trước của
    phòng cũ, mà kỳ ấy chính là kỳ họ làm ra số.
    """
    return TC.pham_vi_xem(db, u, _cuoi_ky(ky), mang)


@router.get("/toi-la-ai")
def toi_la_ai(ky: str, mang: str = "le",
              u: User = Depends(require_roles(*XEM, mo_ta="vai của tôi ở màn hình Kinh doanh")),
              db: Session = Depends(get_db)):
    """Màn hình dùng để VẼ, không dùng để cắt dòng — dòng đã cắt ở máy chủ."""
    mang = _mang(mang)
    cuoi = _cuoi_ky(ky)
    pv = _pham_vi(db, u, ky, mang)
    dv = TC.don_vi_cua(db, u.id, cuoi, mang)
    return {
        "user_id": u.id, "ho_ten": u.full_name, "vai": u.role, "mang": mang, "ky": ky,
        "xem_toan_cay": pv is None,
        "so_don_vi_xem_duoc": (None if pv is None else len(pv)),
        "don_vi_cua_toi": ({"id": dv.id, "ma": dv.ma, "ten": dv.ten, "cap": dv.cap} if dv else None),
        "duoc_giao_chi_tieu": u.role in GIAO_CHI_TIEU,
        # Chưa phân công thì nói thẳng, đừng để màn hình hiện một bảng rỗng không lời giải thích.
        "canh_bao": ("" if pv is None or pv or dv else
                     "Bạn chưa được phân công vào đơn vị nào của mảng này, nên chưa thấy dòng nào. "
                     "Hành chính – Nhân sự phân công ở màn hình Cơ cấu tổ chức Kinh doanh."),
    }


@router.get("/thang")
def thang(ky: str, mang: str = "le", luong: str = "",
          u: User = Depends(require_roles(*XEM, mo_ta="doanh thu Kinh doanh theo tháng")),
          db: Session = Depends(get_db)):
    """Tổng hợp một kỳ trong phạm vi người này được xem, kèm chỉ tiêu đặt cạnh."""
    mang = _mang(mang)
    try:
        kq = DT.thang(db, ky, luong, _pham_vi(db, u, ky, mang))
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {**kq, "mang": mang, "chi_tieu": CT.tra_cuu(db, ky)}


@router.get("/don-vi/{don_vi_id}")
def mot_don_vi(don_vi_id: int, ky: str, mang: str = "le", luong: str = "",
               u: User = Depends(require_roles(*XEM, mo_ta="xem xuống một đơn vị Kinh doanh")),
               db: Session = Depends(get_db)):
    """Xem xuống một đơn vị: đơn vị con, người trong đơn vị, và số của chính nó.

    CHỖ DỄ THỦNG NHẤT CỦA VÒNG NÀY — nó nhận một id từ người gọi. Hỏi quyền TRƯỚC khi đọc, và trả
    403 chứ không trả bảng rỗng: bảng rỗng làm người ta tưởng đơn vị ấy không bán được đồng nào.
    """
    mang = _mang(mang)
    cuoi = _cuoi_ky(ky)
    dv = db.get(DonViKD, don_vi_id)
    if dv is None:
        raise HTTPException(404, f"Không có đơn vị id {don_vi_id}.")
    if not TC.duoc_xem(db, u, don_vi_id, cuoi, mang):
        raise HTTPException(403, f"Bạn không được xem đơn vị {dv.ten}.")

    # Phạm vi của LẦN XEM NÀY là cây con của đơn vị được chọn, giao với phạm vi của người xem.
    # `duoc_xem` ở trên đã bảo đảm đơn vị này nằm trong phạm vi, nên cây con của nó cũng nằm trong.
    trong_cay = TC.con_chau(db, don_vi_id, cuoi)
    try:
        kq = DT.thang(db, ky, luong, trong_cay)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    con = [{"id": c.id, "ma": c.ma, "ten": c.ten, "cap": c.cap}
           for c in db.query(DonViKD).filter(DonViKD.cha_id == don_vi_id).all()
           if c.dang_hieu_luc(cuoi)]
    return {**kq, "mang": mang,
            "don_vi": {"id": dv.id, "ma": dv.ma, "ten": dv.ten, "cap": dv.cap,
                       "cha_id": dv.cha_id},
            "don_vi_con": con,
            "nguoi_trong_don_vi": TC.nguoi_trong(db, [don_vi_id], cuoi),
            "chi_tieu": CT.tra_cuu(db, ky)}


@router.get("/cua-toi")
def cua_toi(ky: str, luong: str = "",
            u: User = Depends(require_roles(*XEM, mo_ta="doanh thu của chính tôi")),
            db: Session = Depends(get_db)):
    """Từng booking của chính người đăng nhập trong kỳ. Không nhận `user_id` — cố ý."""
    try:
        return DT.cua_nguoi(db, u.id, ky, luong)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/nhip-cua-toi")
def nhip_cua_toi(ky: str, mang: str = "le",
                 u: User = Depends(require_roles(*XEM, mo_ta="biểu đồ phấn đấu của chính tôi")),
                 db: Session = Depends(get_db)):
    """Chuỗi ngày cho biểu đồ phấn đấu của CHÍNH người đăng nhập: lũy kế, nhịp cần đi, vạch đích.

    KHÔNG nhận `user_id` — cố ý, đúng như `/cua-toi` ngay trên. Quản lý muốn xem nhịp của một nhân
    viên thì đi qua `/nguoi/{user_id}`, nơi đã có hàng rào phạm vi xem; mở thêm một tham số ở đây
    là dựng cửa thứ hai vào cùng dữ liệu, và cửa thứ hai bao giờ cũng là cửa bị quên khi siết.
    """
    try:
        return DT.nhip_cua_nguoi(db, u.id, ky, mang)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/nguoi/{user_id}")
def mot_nguoi(user_id: int, ky: str, mang: str = "le", luong: str = "",
              u: User = Depends(require_roles(*XEM, mo_ta="doanh thu của một nhân viên")),
              db: Session = Depends(get_db)):
    """Quản lý xem xuống một nhân viên. Chính mình thì luôn xem được, không cần phân công."""
    mang = _mang(mang)
    cuoi = _cuoi_ky(ky)
    if user_id != u.id:
        dv = TC.don_vi_cua(db, user_id, cuoi, mang)
        if dv is None or not TC.duoc_xem(db, u, dv.id, cuoi, mang):
            raise HTTPException(403, "Người này không nằm trong phạm vi bạn được xem.")
    try:
        return DT.cua_nguoi(db, user_id, ky, luong)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


# ─────────────────────────────────── CHỈ TIÊU ───────────────────────────────────

@router.get("/chi-tieu")
def xem_chi_tieu(ky: str, mang: str = "le",
                 u: User = Depends(require_roles(*XEM, mo_ta="chỉ tiêu Kinh doanh")),
                 db: Session = Depends(get_db)):
    mang = _mang(mang)
    try:
        return {"ky": ky, "mang": mang,
                "duoc_giao": u.role in GIAO_CHI_TIEU,
                "rows": CT.danh_sach(db, ky, _pham_vi(db, u, ky, mang))}
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class GiaoChiTieu(BaseModel):
    ky: str
    muc_tieu: float
    don_vi_id: int | None = None
    user_id: int | None = None
    luong: str = "tat_ca"
    ghi_chu: str = ""
    ly_do: str = ""


@router.post("/chi-tieu")
def giao_chi_tieu(data: GiaoChiTieu,
                  u: User = Depends(require_roles(*GIAO_CHI_TIEU, mo_ta="giao chỉ tiêu")),
                  db: Session = Depends(get_db)):
    """Giao chỉ tiêu cho một đơn vị hoặc một người.

    Người giao chỉ tiêu cũng bị cắt phạm vi: một Giám đốc Kinh doanh Lẻ không giao chỉ tiêu cho
    team của phòng Đoàn được. Kiểm ở đây chứ không ở lớp dịch vụ, vì lớp dịch vụ còn được gọi từ
    những chỗ không có người đăng nhập.
    """
    mang_cua_o = "le"
    if data.don_vi_id is not None:
        dv = db.get(DonViKD, data.don_vi_id)
        if dv is None:
            raise HTTPException(404, f"Không có đơn vị id {data.don_vi_id}.")
        mang_cua_o = dv.mang
        if not TC.duoc_xem(db, u, dv.id, _cuoi_ky(data.ky), dv.mang):
            raise HTTPException(403, f"Đơn vị {dv.ten} không nằm trong phạm vi bạn phụ trách.")
    elif data.user_id is not None:
        cuoi = _cuoi_ky(data.ky)
        dv = TC.don_vi_cua(db, data.user_id, cuoi, "le") or TC.don_vi_cua(db, data.user_id, cuoi, "doan")
        if dv is None:
            raise HTTPException(422,
                "Người này chưa được phân công vào đơn vị nào, chưa giao chỉ tiêu được. "
                "Phân công trước ở màn hình Cơ cấu tổ chức Kinh doanh.")
        mang_cua_o = dv.mang
        if not TC.duoc_xem(db, u, dv.id, cuoi, dv.mang):
            raise HTTPException(403, "Người này không nằm trong phạm vi bạn phụ trách.")

    try:
        ct = CT.dat(db, u, data.ky, data.muc_tieu, data.don_vi_id, data.user_id,
                    data.luong, data.ghi_chu, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"da_ghi": True, "id": ct.id, "mang": mang_cua_o,
            "message": f"Đã giao chỉ tiêu {float(ct.muc_tieu):,.0f} cho kỳ {ct.ky}"}


class XoaChiTieu(BaseModel):
    ly_do: str


@router.post("/chi-tieu/{chi_tieu_id}/xoa")
def xoa_chi_tieu(chi_tieu_id: int, data: XoaChiTieu,
                 u: User = Depends(require_roles(*GIAO_CHI_TIEU, mo_ta="xoá chỉ tiêu")),
                 db: Session = Depends(get_db)):
    from app.models.chi_tieu_kd import ChiTieuKD
    ct = db.get(ChiTieuKD, chi_tieu_id)
    if ct is None:
        raise HTTPException(404, f"Không có dòng chỉ tiêu id {chi_tieu_id}.")
    if ct.don_vi_id is not None:
        dv = db.get(DonViKD, ct.don_vi_id)
        if dv is not None and not TC.duoc_xem(db, u, dv.id, _cuoi_ky(ct.ky), dv.mang):
            raise HTTPException(403, f"Đơn vị {dv.ten} không nằm trong phạm vi bạn phụ trách.")
    try:
        kq = CT.xoa(db, u, chi_tieu_id, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return kq
