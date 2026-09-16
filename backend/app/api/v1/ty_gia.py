# -*- coding: utf-8 -*-
"""CỬA TỶ GIÁ – nhân viên tự nhập tỷ giá của từng ngày, kèm chứng từ.

Chủ tịch chốt 16/9/2026: *"tỷ giá để nhân viên tự nhập tại từng thời điểm; tạo form để nhân viên tự
nhập tay và tải tệp/ảnh."* Đây là cửa ấy. Xem `app/models/ty_gia.py` cho lý do của cả cái trục.

────────────────────────────────────────────────────────────────────────────────
CỬA NÀY KHÔNG CHỌN HỘ, VÀ ĐÓ LÀ ĐIỀU QUAN TRỌNG NHẤT
────────────────────────────────────────────────────────────────────────────────

`/tra-cuu` trả về TẤT CẢ tỷ giá đã nhập cho ngày ấy chứ không trả về "tỷ giá đúng". Có một dòng thì
form điền sẵn; có hai dòng khác nhau thì form bày cả hai ra và người nhập chọn.

Vì sao không lấy dòng mới nhất, hay dòng của ngân hàng lớn nhất: hai tỷ giá khác nhau cho cùng một
ngày KHÔNG phải lỗi dữ liệu, nó là hai sự thật – "Vietcombank bán ra 25.500" và "thực tế chuyển
khoản 25.620" đều đúng, và khoản nào dùng số nào là việc của người lập chứng từ. Máy chọn hộ thì
cái chênh lệch ấy biến mất khỏi tầm mắt đúng vào lúc cần nhìn nhất.

Không có tỷ giá của đúng ngày thì trả về dòng GẦN NHẤT TRƯỚC ĐÓ, kèm số ngày cách xa, và nói thẳng
rằng đây không phải tỷ giá của ngày được hỏi. KHÔNG nội suy giữa hai ngày: nội suy ra một con số
chưa từng tồn tại ở bất kỳ ngân hàng nào.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.ty_gia import DONG_TIEN_HAY_GAP, LOAI_GIA, TyGia

router = APIRouter(prefix="/api/v1/ty-gia", tags=["ty-gia"])

# Ai được XEM. Rộng: tỷ giá là con số ai lập chứng từ ngoại tệ cũng cần tra.
XEM = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt", "visa", "kd_le")
# Ai được NHẬP. Hẹp hơn: Kế toán giữ sổ, Điều hành nhập tỷ giá của chuyến mình chi.
NHAP = ("ketoan", "tp_dh", "nv_dh", "cntt")

DAI_NHAT_LY_DO = 10     # "sửa" không phải một lý do

# Xa hơn ngần này thì tỷ giá gần nhất KHÔNG còn là một gợi ý tử tế nữa – nói là không có.
QUA_XA_NGAY = 30


def _hoa(s: str) -> str:
    return (s or "").strip().upper()


def _dong(x: TyGia, ngay_hoi: date | None = None) -> dict:
    d = {"id": x.id, "tien_te": x.tien_te, "ngay": x.ngay, "ty_gia": float(x.ty_gia),
         "nguon": x.nguon, "loai_gia": x.loai_gia, "ten_loai_gia": LOAI_GIA.get(x.loai_gia, ""),
         "ghi_chu": x.ghi_chu, "nguoi_nhap": x.nguoi_nhap, "luc": x.luc,
         "so_lan_sua": x.so_lan_sua, "lich_su": x.lich_su}
    if ngay_hoi is not None and x.ngay != ngay_hoi:
        d["lech_ngay"] = (ngay_hoi - x.ngay).days
        d["canh_bao"] = (f"Đây là tỷ giá ngày {x.ngay:%d/%m/%Y}, KHÔNG phải ngày {ngay_hoi:%d/%m/%Y} "
                         f"được hỏi – cách {(ngay_hoi - x.ngay).days} ngày.")
    return d


@router.get("/danh-muc")
def danh_muc(u: User = Depends(require_roles(*XEM))):
    """Đồng tiền hay gặp và loại giá – để form bày ra, KHÔNG để chặn đồng tiền lạ."""
    return {"dong_tien": DONG_TIEN_HAY_GAP, "loai_gia": LOAI_GIA,
            "ghi_chu": "Danh sách đồng tiền là GỢI Ý. Gặp đồng tiền ngoài danh sách vẫn nhập được."}


@router.get("")
def danh_sach(tien_te: str = "", tu: date | None = None, den: date | None = None,
              gioi_han: int = 200, u: User = Depends(require_roles(*XEM)),
              db: Session = Depends(get_db)):
    q = select(TyGia)
    if tien_te:
        q = q.where(TyGia.tien_te == _hoa(tien_te))
    if tu:
        q = q.where(TyGia.ngay >= tu)
    if den:
        q = q.where(TyGia.ngay <= den)
    rows = db.scalars(q.order_by(TyGia.ngay.desc(), TyGia.tien_te).limit(min(gioi_han, 1000))).all()
    return {"so_dong": len(rows), "rows": [_dong(x) for x in rows]}


@router.get("/tra-cuu")
def tra_cuu(tien_te: str, ngay: date, u: User = Depends(require_roles(*XEM)),
            db: Session = Depends(get_db)):
    """Tỷ giá đã nhập cho MỘT đồng tiền MỘT ngày. Trả về tất cả, không chọn hộ.

    `nhieu_nguon = True` là một sự việc người nhập cần biết, không phải chi tiết máy giữ cho riêng
    mình: hai nguồn lệch nhau nghĩa là con số họ sắp nhân vào tiền có hai phiên bản.
    """
    tt = _hoa(tien_te)
    if tt in ("", "VND"):
        return {"tien_te": "VND", "dung_ngay": [], "gan_nhat": None, "nhieu_nguon": False,
                "ghi_chu": "Khoản đồng Việt Nam không cần tỷ giá."}

    dung = db.scalars(select(TyGia).where(TyGia.tien_te == tt, TyGia.ngay == ngay)
                      .order_by(TyGia.nguon)).all()
    gan = None
    if not dung:
        truoc = db.scalars(select(TyGia).where(TyGia.tien_te == tt, TyGia.ngay < ngay)
                           .order_by(TyGia.ngay.desc()).limit(1)).first()
        # Quá xa thì thà nói không có. Một tỷ giá của hai tháng trước không phải gợi ý, nó là bẫy.
        if truoc is not None and (ngay - truoc.ngay).days <= QUA_XA_NGAY:
            gan = _dong(truoc, ngay)

    return {
        "tien_te": tt, "ngay": ngay,
        "dung_ngay": [_dong(x) for x in dung],
        "gan_nhat": gan,
        "nhieu_nguon": len(dung) > 1,
        # KHÔNG nội suy giữa hai ngày – xem chú thích đầu tệp.
        "ghi_chu": ("" if dung else
                    ("Chưa có tỷ giá cho ngày này. " +
                     ("Dòng gợi ý bên dưới là của NGÀY KHÁC – sửa lại trước khi dùng."
                      if gan else "Người lập phải tự nhập và đính kèm chứng từ."))),
    }


class TyGiaVao(BaseModel):
    tien_te: str
    ngay: date
    ty_gia: float
    nguon: str = ""
    loai_gia: str = ""
    ghi_chu: str = ""


@router.post("", status_code=201)
def them(v: TyGiaVao, u: User = Depends(require_roles(*NHAP)), db: Session = Depends(get_db)):
    tt = _hoa(v.tien_te)
    if not tt or len(tt) != 3:
        raise HTTPException(422, "Mã đồng tiền phải đúng 3 chữ, ví dụ USD, AUD, GBP.")
    if tt == "VND":
        raise HTTPException(422, "Không nhập tỷ giá cho đồng Việt Nam.")
    # Tỷ giá 0 hoặc âm nhân vào tiền ra 0 hoặc số âm, và không ai nhìn lại con số ấy nữa.
    # `or 0` quanh chỗ đọc là luật K2: cột tiền được phép rỗng, và rỗng ở đây nghĩa là "chưa nhập"
    # – rơi đúng vào nhánh từ chối bên dưới, không nổ TypeError khi so với 0.
    if not ((v.ty_gia or 0) > 0):
        raise HTTPException(422, "Tỷ giá phải lớn hơn 0.")
    if v.ngay > date.today():
        raise HTTPException(422, "Không nhập tỷ giá của ngày chưa tới.")
    if v.loai_gia and v.loai_gia not in LOAI_GIA:
        raise HTTPException(422, f"Loại giá phải nằm trong: {', '.join(k for k in LOAI_GIA if k)}")

    ng = (v.nguon or "").strip()[:60]
    cu = db.scalars(select(TyGia).where(TyGia.tien_te == tt, TyGia.ngay == v.ngay,
                                        TyGia.nguon == ng)).first()
    if cu is not None:
        # KHÔNG ghi đè âm thầm. Sửa là một việc riêng, có cửa riêng, và đòi lý do.
        raise HTTPException(409, f"Đã có tỷ giá {tt} ngày {v.ngay:%d/%m/%Y} từ nguồn "
                                 f"{ng or '(không ghi nguồn)'!s}: {float(cu.ty_gia):,.4f}. "
                                 f"Muốn đổi thì sửa dòng #{cu.id} kèm lý do, hoặc nhập với NGUỒN khác.")

    x = TyGia(tien_te=tt, ngay=v.ngay, ty_gia=v.ty_gia, nguon=ng,
              loai_gia=v.loai_gia or "", ghi_chu=(v.ghi_chu or "")[:2000],
              nguoi_nhap=u.username, luc=datetime.now())
    db.add(x)
    db.commit()
    db.refresh(x)
    return {"row": _dong(x),
            "message": f"Đã ghi tỷ giá {tt} ngày {v.ngay:%d/%m/%Y} = {float(v.ty_gia):,.4f}. "
                       f"Đính kèm ảnh bảng tỷ giá hoặc sao kê vào hồ sơ 'ty_gia' mã {x.id}."}


class TyGiaSua(BaseModel):
    ty_gia: float | None = None
    nguon: str | None = None
    loai_gia: str | None = None
    ghi_chu: str | None = None
    ly_do_sua: str


@router.put("/{tid}")
def sua(tid: int, v: TyGiaSua, u: User = Depends(require_roles(*NHAP)),
        db: Session = Depends(get_db)):
    """Sửa một dòng tỷ giá. Số cũ KHÔNG biến mất – nó đi vào `lich_su`.

    Vì sao bắt buộc lý do dài hơn 10 chữ: tỷ giá là con số NHÂN vào tiền. Sửa 25.500 thành 25.620
    trên một khoản 40.000 USD là 4,8 triệu. "sửa" không nói được vì sao 4,8 triệu ấy đổi chủ.
    """
    x = db.get(TyGia, tid)
    if x is None:
        raise HTTPException(404, "Không có dòng tỷ giá này")
    ly = (v.ly_do_sua or "").strip()
    if len(ly) < DAI_NHAT_LY_DO:
        raise HTTPException(422, f"Phải ghi lý do sửa, ít nhất {DAI_NHAT_LY_DO} ký tự.")

    doi = []
    if v.ty_gia is not None:
        if not ((v.ty_gia or 0) > 0):
            raise HTTPException(422, "Tỷ giá phải lớn hơn 0.")
        if float(v.ty_gia) != float(x.ty_gia):
            doi.append(f"tỷ giá {float(x.ty_gia):,.4f} → {float(v.ty_gia):,.4f}")
            x.ty_gia = v.ty_gia
    if v.nguon is not None and v.nguon.strip()[:60] != x.nguon:
        doi.append(f"nguồn {x.nguon!r} → {v.nguon.strip()[:60]!r}")
        x.nguon = v.nguon.strip()[:60]
    if v.loai_gia is not None and v.loai_gia != x.loai_gia:
        if v.loai_gia and v.loai_gia not in LOAI_GIA:
            raise HTTPException(422, "Loại giá không hợp lệ")
        doi.append(f"loại giá {x.loai_gia!r} → {v.loai_gia!r}")
        x.loai_gia = v.loai_gia
    if v.ghi_chu is not None:
        x.ghi_chu = v.ghi_chu[:2000]

    if not doi:
        return {"row": _dong(x), "message": "Không có gì đổi."}

    x.lich_su = (f"{x.lich_su}\n" if x.lich_su else "") + (
        f"{datetime.now():%d/%m/%Y %H:%M} · {u.username} · {'; '.join(doi)} · lý do: {ly}")
    x.so_lan_sua = (x.so_lan_sua or 0) + 1
    db.commit()
    db.refresh(x)
    return {"row": _dong(x), "message": "Đã sửa và ghi lại lần sửa này: " + "; ".join(doi)}
