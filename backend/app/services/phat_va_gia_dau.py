# -*- coding: utf-8 -*-
"""DX-3 — PHẠT TÀI XẾ và GIÁ DẦU THEO NGÀY.

Hai việc cuối của danh sách bảy việc lập trình đội xe (chốt 11/10/2026), Chủ tịch duyệt 16/10/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
PHẠT TÀI XẾ ĐI VÀO LƯƠNG, KHÔNG ĐI VÀO GIÁ VỐN XE
═══════════════════════════════════════════════════════════════════════════════════════════════

Đây là luật quan trọng nhất của tệp này, và nó dễ bị phá bằng một dòng vô ý. Khoản phạt là tiền
của NGƯỜI LÁI; chiếc xe không làm gì sai. Cộng nó vào chi phí của xe thì:

  · lãi lỗ từng xe sai — một chiếc có tài xế hay bị phạt trông như một chiếc tốn kém;
  · và tệ hơn, công ty thu lại tiền phạt nhưng sổ vẫn ghi xe đã tiêu khoản ấy, tức tính hai lần
    theo hai chiều ngược nhau.

Nên bảng này KHÔNG có đường nào chảy vào `fleet_period_costs` hay `fleet_trip_costs`, và có một
phép thử đọc mã nguồn canh đúng điều đó.

HCNS ĐỐI CHIẾU, KHÔNG PHẢI DUYỆT (Chủ tịch chọn 16/10/2026). Giám đốc đội xe là người thấy lỗi
nên là người ghi. HCNS nhìn thấy khoản ấy khi chốt lương và đánh dấu đã đối chiếu — dấu ấy nói
«đã có người thứ hai nhìn», không phải «đã được phê». Dựng một hàng đợi phê duyệt ở đây là thêm
một chỗ tắc cho một khoản tiền thường nhỏ.

═══════════════════════════════════════════════════════════════════════════════════════════════
GIÁ DẦU: QUY TIỀN RA LÍT, VÀ NÓI RA KHI KHÔNG QUY ĐƯỢC
═══════════════════════════════════════════════════════════════════════════════════════════════

Sao kê thẻ dầu cho TIỀN, không cho lít. Ngày 14/10 ô «Tiêu hao» của đội xe đọc ra 7,6 L/100km vì
cả 80 dòng nhật trình đều trống số lít — một con số không ai kiểm được, tệ hơn là không có số.

`lit_tu_tien` KHÔNG ĐOÁN. Không có giá đúng ngày ấy thì trả về None kèm lý do, chứ không lấy giá
gần nhất: giá dầu đổi mười ngày một lần, lấy giá cách đó ba tuần ra một số lít sai mà trông vẫn
hợp lý — và một con số sai trông hợp lý thì không ai đi kiểm lại.
"""
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fleet import GiaDauNgay, LOAI_DAU, PhatTaiXe
from app.models.hr import Employee


class KhongGhiDuoc(ValueError):
    """Cửa từ chối. Nơi gọi đổi thành HTTP 422 kèm nguyên văn câu này."""


# ─────────────────────────────────────────── PHẠT TÀI XẾ
def _dung_ky(ky: str) -> str:
    ky = (ky or "").strip()
    try:
        datetime.strptime(ky, "%Y-%m")
    except ValueError:
        raise KhongGhiDuoc("Kỳ lương phải ở dạng YYYY-MM, ví dụ 2026-10")
    return ky


def ghi_phat(db: Session, driver_id: int, ky: str, ngay: date, so_tien: float,
             ly_do: str, boi: str, trip_id: int | None = None,
             vehicle_id: int | None = None) -> PhatTaiXe:
    """Giám đốc đội xe ghi một khoản phạt. Nơi gọi `commit`."""
    nv = db.get(Employee, driver_id)
    if nv is None:
        raise KhongGhiDuoc("Không có nhân sự này")
    if nv.department != "doi_xe":
        raise KhongGhiDuoc(f"{nv.full_name} không thuộc đội xe")
    ky = _dung_ky(ky)
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise KhongGhiDuoc("Phải ghi lý do phạt – một khoản trừ vào lương mà không nói vì sao "
                           "thì tháng sau không ai trả lời được cho người bị trừ")
    if not so_tien or so_tien <= 0:
        raise KhongGhiDuoc("Số tiền phạt phải lớn hơn 0")
    p = PhatTaiXe(driver_id=driver_id, ky=ky, ngay=ngay, so_tien=so_tien, ly_do=ly_do,
                  trip_id=trip_id, vehicle_id=vehicle_id, created_by=(boi or "")[:50])
    db.add(p); db.flush()
    return p


def hcns_doi_chieu(db: Session, p: PhatTaiXe, boi: str) -> PhatTaiXe:
    """HCNS đánh dấu đã nhìn khoản này khi chốt lương. Không phải phê duyệt — xem đầu tệp."""
    if p.hcns_doi_chieu_luc is not None:
        raise KhongGhiDuoc(f"Khoản phạt #{p.id} đã được đối chiếu rồi")
    p.hcns_doi_chieu_luc = datetime.now()
    p.hcns_doi_chieu_boi = (boi or "")[:50]
    db.flush()
    return p


def so_phat(db: Session, ky: str = "", driver_id: int | None = None) -> dict:
    """Sổ phạt. `chua_doi_chieu` là con số HCNS cần nhìn trước khi chốt lương kỳ ấy."""
    q = select(PhatTaiXe).order_by(PhatTaiXe.ngay.desc(), PhatTaiXe.id.desc())
    if ky:
        q = q.where(PhatTaiXe.ky == ky)
    if driver_id:
        q = q.where(PhatTaiXe.driver_id == driver_id)
    ds = list(db.execute(q).scalars())
    ten = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    return {
        "tong_tien": sum(float(p.so_tien or 0) for p in ds),
        "so_khoan": len(ds),
        "chua_doi_chieu": sum(1 for p in ds if p.hcns_doi_chieu_luc is None),
        "rows": [{"id": p.id, "driver_id": p.driver_id, "tai_xe": ten.get(p.driver_id, ""),
                  "ky": p.ky, "ngay": p.ngay.isoformat(), "so_tien": float(p.so_tien or 0),
                  "ly_do": p.ly_do, "trip_id": p.trip_id, "vehicle_id": p.vehicle_id,
                  "da_doi_chieu": p.hcns_doi_chieu_luc is not None,
                  "doi_chieu_boi": p.hcns_doi_chieu_boi, "boi": p.created_by} for p in ds],
        "ghi_chu": ("Khoản phạt trừ vào LƯƠNG của tài xế. Không cộng vào chi phí của chiếc xe — "
                    "chiếc xe không làm gì sai, và cộng vào đó thì lãi lỗ từng xe sai."),
    }


def tru_luong_ky(db: Session, ky: str) -> dict:
    """Tổng phạt từng người trong một kỳ, để bảng lương trừ. Trả về {employee_id: số tiền}."""
    ds = db.execute(select(PhatTaiXe).where(PhatTaiXe.ky == _dung_ky(ky))).scalars()
    ra: dict[int, float] = {}
    for p in ds:
        ra[p.driver_id] = ra.get(p.driver_id, 0) + float(p.so_tien or 0)
    return ra


# ─────────────────────────────────────────── GIÁ DẦU
def ghi_gia(db: Session, ngay: date, loai: str, gia_lit: float, nguon: str, boi: str) -> GiaDauNgay:
    """Một giá cho một (ngày, loại). Ghi đè giá cũ của đúng ngày ấy thay vì thêm dòng thứ hai."""
    if loai not in LOAI_DAU:
        raise KhongGhiDuoc(f"Loại nhiên liệu phải thuộc {sorted(LOAI_DAU)}")
    if not gia_lit or gia_lit <= 0:
        raise KhongGhiDuoc("Giá một lít phải lớn hơn 0")
    co = db.execute(select(GiaDauNgay).where(GiaDauNgay.ngay == ngay,
                                             GiaDauNgay.loai == loai)).scalars().first()
    if co is not None:
        co.gia_lit, co.nguon, co.boi, co.luc = gia_lit, (nguon or "")[:120], (boi or "")[:50], datetime.now()
        db.flush()
        return co
    g = GiaDauNgay(ngay=ngay, loai=loai, gia_lit=gia_lit, nguon=(nguon or "")[:120],
                   boi=(boi or "")[:50])
    db.add(g); db.flush()
    return g


def gia_ngay(db: Session, ngay: date, loai: str = "do") -> float | None:
    """Giá ĐÚNG ngày ấy, hoặc None. KHÔNG lấy giá gần nhất — xem phần đầu tệp."""
    g = db.execute(select(GiaDauNgay).where(GiaDauNgay.ngay == ngay,
                                            GiaDauNgay.loai == loai)).scalars().first()
    return float(g.gia_lit) if g else None


def lit_tu_tien(db: Session, ngay: date, so_tien: float, loai: str = "do") -> dict:
    """Quy tiền ra lít. Không quy được thì NÓI RA vì sao, không trả về một con số đoán."""
    if not so_tien or so_tien <= 0:
        return {"lit": None, "vi_sao": "Dòng chi phí chưa có số tiền"}
    gia = gia_ngay(db, ngay, loai)
    if gia is None:
        return {"lit": None, "gia_lit": None,
                "vi_sao": f"Chưa khai giá {LOAI_DAU.get(loai, loai)} ngày {ngay.isoformat()} – "
                          "Kế toán nhập giá ngày ở màn hình Đội xe thì ô này tự tính"}
    return {"lit": round(so_tien / gia, 2), "gia_lit": gia, "vi_sao": ""}


def ngay_thieu_gia(db: Session, ngay_can: list[date], loai: str = "do") -> list[str]:
    """Những ngày đã có chi phí dầu mà chưa khai giá. Đếm được thì mới sửa được."""
    co = {g.ngay for g in db.execute(select(GiaDauNgay).where(GiaDauNgay.loai == loai)).scalars()}
    return sorted({d.isoformat() for d in ngay_can if d not in co})
