"""Cửa API: Báo chí, KOL & sự kiện — mục 2.2.2.

TIỀN TỐ RIÊNG `/api/v1/bao-chi-kol` cho phần MỚI. Phần sổ PR đã có cửa sẵn dưới `/api/v1/marketing`
và màn hình gọi thẳng vào đó — KHÔNG dựng cửa đọc thứ hai cho cùng một bảng. Kiểm trước khi làm
vậy: danh sách vai của màn hình này (`XEM` dưới đây) nằm gọn trong danh sách vai của màn hình
`/marketing`, nên khai thêm tiền tố `/api/v1/marketing` cho màn hình này KHÔNG nới thêm nhóm nào
cho bất kỳ vai nào. Nếu một ngày `XEM` rộng ra thì phải kiểm lại đúng chỗ này.

CỬA TẠO HOẠT ĐỘNG PR NẰM Ở ĐÂY, KHÔNG Ở api/v1/marketing.py. Lý do thực tế, ghi thẳng ra: sổ PR
tới hôm nay chỉ có cửa ĐỌC, cửa PHÁT và cửa PHẢN HỒI — không có cửa TẠO nào ngoài nút "lập PR" trên
hàng đợi tin cảnh báo. Nghĩa là một bài báo không sinh ra từ hộp thư thì không có đường nào vào sổ,
và nhân viên Marketing không có chỗ nào để ghi. Đúng ranh giới 09/9/2026: cửa còn thiếu là việc còn
thiếu. Cửa mới đặt cùng chỗ với phần còn lại của màn hình để người sửa màn hình không phải đi hai
tệp; hàng rào dữ liệu thì nằm trong `pr_hoat_dong.kiem_du_lieu`, chỗ cả hai cửa cùng đi qua.

SỰ KIỆN DÙNG CHUNG SỔ PR, lọc theo `loai="su_kien"` — anh Tuấn chốt 24/9/2026. Không dựng bảng thứ
hai: một bảng riêng cho sự kiện là hai nơi cùng đếm "tháng này làm bao nhiêu việc truyền thông", và
ngày một nơi lệch thì hai báo cáo ra hai con số mà không ai biết bên nào đúng.

BA TẦNG VAI, hẹp dần theo mức không gỡ lại được:
    XEM  — cả phòng Marketing đọc được sổ và danh bạ
    GHI  — thêm KOL, ghi một lần hợp tác, tạo dòng PR ở trạng thái nháp
    PHÁT — nằm ở cửa cũ `/marketing/pr/{id}/phat`, CHỈ P.TGĐ Marketing, và cố ý không có ở đây:
           phát ngôn ra ngoài là một VỊ TRÍ có tên, không phải một mức quyền.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import kol as KOL
from app.services import pr_hoat_dong as PR
from app.services.access import BASE_VIEW, MARKETING

XEM = BASE_VIEW + MARKETING + ("ptgd_mkt", "cntt")
GHI = ("nv_mkt", "ptgd_mkt", "chutich", "tgd", "cntt")

router = APIRouter(prefix="/api/v1/bao-chi-kol", tags=["bao-chi-kol"])


# ────────────────────────────── DANH MỤC ──────────────────────────────

@router.get("/danh-muc")
def danh_muc(u: User = Depends(require_roles(*XEM, mo_ta="danh mục màn hình Báo chí & KOL")),
             db: Session = Depends(get_db)):
    """Mọi ô chọn của màn hình, lấy một lượt.

    CỬA NÀY TỒN TẠI ĐỂ MÀN HÌNH KHÔNG PHẢI GỌI SANG PHÂN HỆ KHÁC chỉ để đổ một ô chọn. Bài học đã
    trả giá ở `/to-chuc-kd`: bản đầu gọi thẳng `/api/v1/access` và `/api/v1/companies` cho hai ô
    chọn, và bộ đối chiếu bản đồ màn hình bắt phải khai thêm hai tiền tố ấy cho cả mười hai vai.
    """
    from app.models.kol import HT_LOAI, HT_TRANG_THAI, KOL_KENH, KOL_TRANG_THAI
    from app.models.marketing import Campaign
    from sqlalchemy import select

    from app.services import pham_vi_phap_nhan as PV
    q = PV.loc(select(Campaign).order_by(Campaign.id.desc()), Campaign, u)
    return {
        "kol_kenh": KOL_KENH, "kol_trang_thai": KOL_TRANG_THAI,
        "hop_tac_loai": HT_LOAI, "hop_tac_trang_thai": HT_TRANG_THAI,
        "pr": PR.dinh_nghia_cot(),
        "chien_dich": [{"id": c.id, "ma": c.code, "ten": c.name}
                       for c in db.execute(q.limit(300)).scalars()],
    }


# ────────────────────────────── HOẠT ĐỘNG PR ──────────────────────────────

class PrMoi(BaseModel):
    loai: str
    tieu_de: str
    tom_tat: str = ""
    noi_dang: str = ""
    link: str = ""
    campaign_id: int | None = None
    la_khung_hoang: bool = False
    muc_do: str = ""
    ghi_chu: str = ""


@router.post("/pr", status_code=201)
def pr_tao(data: PrMoi,
           u: User = Depends(require_roles(*GHI, mo_ta="ghi một việc vào sổ hoạt động PR")),
           db: Session = Depends(get_db)):
    """Ghi một bài báo, thông cáo, sự kiện hay phát ngôn vào sổ — ở trạng thái NHÁP.

    LUÔN LÀ NHÁP, không có tham số nào đổi được điều đó. Đưa một câu ra ngoài là việc của nút PHÁT,
    và nút ấy chỉ P.TGĐ Marketing bấm. Cho cửa tạo đặt thẳng `da_phat` là mở một đường vòng qua
    người phát ngôn — đúng thứ mà tách bạch trách nhiệm sinh ra để ngăn.

    ĐÁNH DẤU KHỦNG HOẢNG LÀ BẤM ĐỒNG HỒ. `ghi_nhan_luc` do cơ sở dữ liệu đặt lúc dòng vào sổ, và
    mốc hai giờ chạy từ đó theo đồng hồ thật — không trừ ngày nghỉ, không quy ra giờ hành chính.
    """
    try:
        h = PR.tao(db, data.model_dump(), u.username, tu_tay=True)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"id": h.id, "ma": h.ma, "trang_thai": h.trang_thai,
            "message": f"Đã ghi {h.ma} vào sổ ở trạng thái nháp."
                       + (" Đồng hồ khủng hoảng bắt đầu chạy." if h.la_khung_hoang else "")}


# ────────────────────────────── KOL / KOC ──────────────────────────────

@router.get("/kol")
def kol_danh_sach(trang_thai: str = "", kenh: str = "",
                  u: User = Depends(require_roles(*XEM, mo_ta="danh bạ KOL")),
                  db: Session = Depends(get_db)):
    return KOL.danh_sach(db, trang_thai=trang_thai, kenh=kenh)


@router.get("/kol/{kol_id}")
def kol_chi_tiet(kol_id: int,
                 u: User = Depends(require_roles(*XEM, mo_ta="chi tiết một KOL")),
                 db: Session = Depends(get_db)):
    try:
        return KOL.chi_tiet(db, kol_id)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


class KolMoi(BaseModel):
    ho_ten: str
    kenh: str
    link_kenh: str
    biet_danh: str = ""
    luong_theo_doi: int | None = None
    theo_doi_do_ngay: date | None = None
    gia_tham_khao: float | None = None
    nguoi_lien_he: str = ""
    dien_thoai: str = ""
    email: str = ""
    trang_thai: str = "dang_hop_tac"
    ly_do_ngung: str = ""
    ghi_chu: str = ""
    company_id: int | None = None
    # Người gõ đã nhìn cảnh báo trùng tên và vẫn muốn thêm. Xem `/kol/soat-trung`.
    bo_qua_canh_bao_trung_ten: bool = False


@router.get("/kol/soat-trung/{ho_ten}")
def kol_soat_trung(ho_ten: str,
                   u: User = Depends(require_roles(*XEM, mo_ta="soát trùng tên KOL")),
                   db: Session = Depends(get_db)):
    """Gọi TRƯỚC khi thêm, để màn hình hỏi lại người gõ. Trùng tên là cảnh báo, không phải lỗi."""
    return {"trung_ten": KOL.canh_bao_trung_ten(db, ho_ten)}


@router.post("/kol", status_code=201)
def kol_them(data: KolMoi,
             u: User = Depends(require_roles(*GHI, mo_ta="thêm KOL vào danh bạ")),
             db: Session = Depends(get_db)):
    """Thêm một kênh vào danh bạ.

    HAI MỨC CHỐNG TRÙNG, cố ý khác nhau: cùng ĐƯỜNG DẪN KÊNH thì chặn cứng (chắc chắn là bản khai
    lặp); cùng TÊN thì chỉ hỏi lại, vì hai người thật có thể trùng tên. Cùng nếp với nhóm 2.8 —
    trùng số điện thoại là bình thường, trùng dấu vân tay mới là rò.
    """
    d = data.model_dump()
    bo_qua = d.pop("bo_qua_canh_bao_trung_ten", False)
    if not bo_qua:
        trung = KOL.canh_bao_trung_ten(db, d["ho_ten"])
        if trung:
            raise HTTPException(409, {
                "message": f"Đã có {len(trung)} người cùng tên trong danh bạ. Kiểm lại có phải "
                           "cùng một người không; nếu đúng là người khác thì bấm thêm lần nữa.",
                "trung_ten": trung})
    try:
        k = KOL.them(db, u, d)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"id": k.id, "ma": k.ma, "message": f"Đã thêm {k.ho_ten} ({k.ma})."}


class KolSua(BaseModel):
    ho_ten: str | None = None
    biet_danh: str | None = None
    kenh: str | None = None
    link_kenh: str | None = None
    luong_theo_doi: int | None = None
    gia_tham_khao: float | None = None
    nguoi_lien_he: str | None = None
    dien_thoai: str | None = None
    email: str | None = None
    trang_thai: str | None = None
    ly_do_ngung: str | None = None
    ghi_chu: str | None = None


@router.put("/kol/{kol_id}")
def kol_sua(kol_id: int, data: KolSua,
            u: User = Depends(require_roles(*GHI, mo_ta="sửa hồ sơ KOL")),
            db: Session = Depends(get_db)):
    d = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        k = KOL.sua(db, u, kol_id, d)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"id": k.id, "message": f"Đã cập nhật {k.ho_ten}."}


class HopTacMoi(BaseModel):
    ky: str
    noi_dung: str
    loai: str = "bai_dang"
    campaign_id: int | None = None
    link_bai: str = ""
    ngay_dang: date | None = None
    # RỖNG KHÁC KHÔNG: bỏ trống là "chưa thoả thuận giá", gõ 0 là "không mất tiền".
    chi_phi: float | None = None
    payment_request_id: int | None = None
    trang_thai: str = "du_kien"
    luot_xem: int | None = None
    luot_tuong_tac: int | None = None
    so_lead_khai: int | None = None
    ghi_chu: str = ""


@router.post("/kol/{kol_id}/hop-tac", status_code=201)
def hop_tac_ghi(kol_id: int, data: HopTacMoi,
                u: User = Depends(require_roles(*GHI, mo_ta="ghi một lần hợp tác KOL")),
                db: Session = Depends(get_db)):
    """Ghi một lần hợp tác.

    `chi_phi` là số THOẢ THUẬN, không phải tiền đã ra khỏi tài khoản. Tiền thật đi đường đề nghị
    chi; gắn chiến dịch ở phiếu chi ấy thì nó chảy vào bảng hiệu quả chiến dịch của nhóm 2.7 qua
    đúng MỘT đường. Cửa này cố ý KHÔNG tự lập phiếu chi: lập phiếu là mở một luồng duyệt có Kế
    toán và Ban TGĐ trong đó, không phải một tác dụng phụ của việc ghi sổ Marketing.
    """
    try:
        h = KOL.ghi_hop_tac(db, u, kol_id, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    nhac = ""
    if (h.chi_phi or 0) > 0 and not h.payment_request_id:
        nhac = (" Khoản này chưa nối phiếu chi nào — tiền chỉ vào bảng hiệu quả chiến dịch khi có "
                "đề nghị chi đã gắn chiến dịch.")
    return {"id": h.id, "message": "Đã ghi lần hợp tác." + nhac}


class HopTacSua(BaseModel):
    ky: str | None = None
    noi_dung: str | None = None
    loai: str | None = None
    campaign_id: int | None = None
    link_bai: str | None = None
    ngay_dang: date | None = None
    chi_phi: float | None = None
    payment_request_id: int | None = None
    trang_thai: str | None = None
    ly_do_huy: str | None = None
    luot_xem: int | None = None
    luot_tuong_tac: int | None = None
    so_lead_khai: int | None = None
    ghi_chu: str | None = None


@router.put("/hop-tac/{ht_id}")
def hop_tac_sua(ht_id: int, data: HopTacSua,
                u: User = Depends(require_roles(*GHI, mo_ta="sửa một lần hợp tác KOL")),
                db: Session = Depends(get_db)):
    """Sửa, kể cả để gõ số lượt xem sau khi bài đã đăng vài ngày — đó là việc thường của nghề."""
    d = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        h = KOL.sua_hop_tac(db, u, ht_id, d)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"id": h.id, "message": "Đã cập nhật."}
