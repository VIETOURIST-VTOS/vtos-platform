# -*- coding: utf-8 -*-
"""CỬA NẠP CÔNG NỢ VIETRIP – báo cáo 8h sáng mỗi ngày đẩy thẳng vào VTOS, tệp gốc lưu R2.

Xem `app/models/cong_no_vietrip.py` cho lý do của cấu trúc.

  POST /api/v1/cong-no-vietrip/nap        nạp (hoặc nạp lại) ảnh chụp của một ngày
  GET  /api/v1/cong-no-vietrip            ảnh mới nhất (hoặc ?ngay=) – 4 nhóm, chi tiết, theo sale
  GET  /api/v1/cong-no-vietrip/lich-su    tổng còn thiếu từng ngày, để thấy nợ tăng hay giảm

Đường dẫn cố ý KHÔNG nằm dưới /import/vietrip/…: router vietrip có `POST /import/vietrip/{entity}`
bắt mọi thứ đứng sau, và nó đăng ký trước.
"""
import calendar
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.cong_no_vietrip import (TEN_NHOM, CongNoVietripAnh, CongNoVietripDong,
                                        PhaiTraVietripAnh, PhaiTraVietripDong)
from app.models.core import User

router = APIRouter(prefix="/api/v1/cong-no-vietrip", tags=["cong-no-vietrip"])

NAP = ("chutich", "tgd", "ketoan", "cntt")
# `ketoan_tt` thêm 11/10/2026 (Đợt LG1) — xem chú thích ở `debts.READ`. Hai hằng số này phải
# đi cùng nhau: chú thích ngay đây đã nói "khớp READ của /cong-no", và lệch một vai là một nửa
# màn hình trả 403 trong khi nửa kia chạy.
XEM = ("chutich", "tgd", "bks", "ketoan", "ketoan_tt", "ptgd_doan", "tp_dh", "cntt")   # khớp READ của /cong-no


class DongIn(BaseModel):
    booking_id: str
    ma_tour: str = ""
    ten_tour: str = ""
    khach: str = ""
    sdt_khach: str = ""
    sales: str = ""
    sdt_sales: str = ""
    tong: float = 0
    da_thu: float = 0
    khoi_hanh: date | None = None
    ghi_chu: str = ""
    bao_luu: bool = False


class NapIn(BaseModel):
    ngay: date
    dong: list[DongIn]
    ghi_chu: str = ""


def _cong_thang(d: date) -> date:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def xep_nhom(khoi_hanh: date | None, ngay: date) -> int:
    """1 quá hạn (≤ hôm nay) · 2 ≤ +14 ngày · 3 ≤ +1 tháng · 4 xa hơn. Thiếu ngày KH → nhóm 1 để
    không ai bỏ sót (khoản không rõ ngày là khoản phải hỏi ngay)."""
    if khoi_hanh is None or khoi_hanh <= ngay:
        return 1
    if khoi_hanh <= ngay + timedelta(days=14):
        return 2
    if khoi_hanh <= _cong_thang(ngay):
        return 3
    return 4


def _luu_tep(ngay: date, noi_dung: bytes):
    """Lưu tệp gốc lên kho đối tượng (R2). Kho hỏng thì VẪN nạp số – báo lại chứ không chặn."""
    sha = hashlib.sha256(noi_dung).hexdigest()
    try:
        from app.services.storage import storage
        kho = storage()
        st = kho.put(f"cong-no-vietrip/{ngay:%Y/%m}/{ngay:%Y%m%d}-{sha[:16]}.json", noi_dung,
                     "application/json")
        return st.key, sha, bool(getattr(kho, "durable", False)), ""
    except Exception as ex:  # noqa: BLE001 – lỗi kho không được làm mất số của cả ngày
        return "", sha, False, f"Không lưu được tệp gốc lên kho: {ex.__class__.__name__}"


@router.post("/nap")
def nap(data: NapIn, u: User = Depends(require_roles(*NAP)), db: Session = Depends(get_db)):
    if data.ngay > date.today() + timedelta(days=1):
        raise HTTPException(422, "Ngày báo cáo nằm ở tương lai.")
    ids = [str(d.booking_id).strip() for d in data.dong]
    trung = sorted({i for i in ids if ids.count(i) > 1})
    if trung:
        raise HTTPException(422, f"Booking ID bị trùng trong lô: {', '.join(trung[:10])}")
    if any(not i for i in ids):
        raise HTTPException(422, "Có dòng thiếu Booking ID.")

    dong, bo_qua = [], 0
    for d in data.dong:
        con = round(float(d.tong or 0) - float(d.da_thu or 0), 2)
        if con <= 0 and not d.bao_luu:
            bo_qua += 1
            continue
        dong.append((d, con, 0 if d.bao_luu else xep_nhom(d.khoi_hanh, data.ngay)))

    tho = json.dumps(data.model_dump(mode="json"), ensure_ascii=False, sort_keys=True).encode("utf-8")
    key, sha, ben, loi_kho = _luu_tep(data.ngay, tho)

    anh = db.execute(select(CongNoVietripAnh).where(CongNoVietripAnh.ngay == data.ngay)).scalar_one_or_none()
    if anh is None:
        anh = CongNoVietripAnh(ngay=data.ngay, so_lan_nap=1)
        db.add(anh)
        db.flush()
    else:
        db.execute(delete(CongNoVietripDong).where(CongNoVietripDong.anh_id == anh.id))
        anh.so_lan_nap = (anh.so_lan_nap or 0) + 1
    no = [x for x in dong if x[2] > 0]
    anh.so_booking = len(no)
    anh.tong_con_thieu = round(sum(x[1] for x in no), 2)
    anh.tep_key, anh.tep_sha256, anh.tep_ben_vung = key, sha, ben
    anh.ghi_chu = data.ghi_chu or ""
    anh.nguoi_nap = u.username
    anh.luc = datetime.now()
    for d, con, nhom in dong:
        db.add(CongNoVietripDong(
            anh_id=anh.id, booking_id=str(d.booking_id).strip(), ma_tour=d.ma_tour, ten_tour=d.ten_tour,
            khach=d.khach, sdt_khach=str(d.sdt_khach or ""), sales=d.sales, sdt_sales=str(d.sdt_sales or ""),
            tong=float(d.tong), da_thu=float(d.da_thu), con_thieu=con, khoi_hanh=d.khoi_hanh,
            nhom=nhom, bao_luu=bool(d.bao_luu), ghi_chu=d.ghi_chu or ""))
    db.commit()
    kq = _tom_tat(db, anh)
    kq.update({"nhan": len(data.dong), "bo_qua_het_no": bo_qua, "canh_bao_kho": loi_kho})
    # 28/9/2026: khối Phải thu của màn hình Chủ tịch đọc sổ nghĩa vụ, và phía thu khách của sổ nay
    # lấy từ ảnh Vietrip mới nhất — nên dựng lại sổ ngay để số lên trong cùng lượt nạp.
    try:
        from app.api.v1.dong_tien import KHO_KHUNG
        from app.services import nghia_vu as NV
        kq["so_nghia_vu"] = NV.dong_bo(db)
        db.commit()
        KHO_KHUNG.xoa()
    except Exception as e:      # noqa: BLE001 — ảnh đã lưu; sổ dựng lại ở lượt robot kế tiếp
        db.rollback()
        kq["canh_bao_so_nghia_vu"] = f"{type(e).__name__}: {str(e)[:300]}"
    return kq


def _tom_tat(db: Session, anh: CongNoVietripAnh, chi_tiet: bool = False) -> dict:
    rows = db.execute(select(CongNoVietripDong).where(CongNoVietripDong.anh_id == anh.id)
                      .order_by(desc(CongNoVietripDong.con_thieu))).scalars().all()
    rows = sorted(rows, key=lambda r: r.nhom or 9)          # nhóm 1→4, bảo lưu (0) xuống cuối
    nhom = {k: {"nhom": k, "ten": TEN_NHOM[k], "so_booking": 0, "con_thieu": 0.0} for k in TEN_NHOM}
    sale = defaultdict(lambda: [0, 0.0])
    for r in rows:
        nhom[r.nhom]["so_booking"] += 1
        nhom[r.nhom]["con_thieu"] += float(r.con_thieu or 0)
        if r.nhom > 0:
            s = sale[r.sales or "(trống)"]
            s[0] += 1
            s[1] += float(r.con_thieu or 0)
    kq = {"ngay": anh.ngay, "so_booking": anh.so_booking, "tong_con_thieu": float(anh.tong_con_thieu or 0),
          "so_lan_nap": anh.so_lan_nap, "luc": anh.luc, "nguoi_nap": anh.nguoi_nap,
          "tep": {"key": anh.tep_key, "sha256": anh.tep_sha256, "ben_vung": anh.tep_ben_vung},
          "nhom": [nhom[k] for k in (1, 2, 3, 4, 0)]}
    if chi_tiet:
        kq["theo_sale"] = sorted(({"sales": k, "so_booking": v[0], "con_thieu": round(v[1], 2)}
                                  for k, v in sale.items()), key=lambda x: -x["con_thieu"])
        kq["dong"] = [{"booking_id": r.booking_id, "ma_tour": r.ma_tour, "ten_tour": r.ten_tour,
                       "khach": r.khach, "sdt_khach": r.sdt_khach, "sales": r.sales,
                       "sdt_sales": r.sdt_sales, "tong": float(r.tong or 0), "da_thu": float(r.da_thu or 0),
                       "con_thieu": float(r.con_thieu or 0), "khoi_hanh": r.khoi_hanh, "nhom": r.nhom,
                       "bao_luu": r.bao_luu, "ghi_chu": r.ghi_chu} for r in rows]
    return kq


@router.get("")
def xem(ngay: date | None = None, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    q = select(CongNoVietripAnh)
    q = q.where(CongNoVietripAnh.ngay == ngay) if ngay else q.order_by(desc(CongNoVietripAnh.ngay)).limit(1)
    anh = db.execute(q).scalars().first()
    if anh is None:
        return {"co_du_lieu": False,
                "thong_bao": "Chưa có báo cáo công nợ Vietrip nào được nạp" + (f" cho ngày {ngay:%d/%m/%Y}." if ngay else ".")}
    kq = _tom_tat(db, anh, chi_tiet=True)
    kq["co_du_lieu"] = True
    kq["cu_ngay"] = (date.today() - anh.ngay).days
    return kq


# ─────────────────── VT-1 · THỬ ĐƯỜNG SANG VIETRIP (05/11/2026) ───────────────────
#
# Vietrip mở hai cửa JSON chỉ đọc (`/receipts`, `/receivables`) thay cho hai đường VTOS đang
# dùng: nạp tay mỗi sáng, và bộ đọc HTML đăng nhập bằng mật khẩu. Vòng này CHƯA đồng bộ gì —
# nó chỉ dựng một cửa để NGƯỜI THẬT tự xem đường có thông không.
#
# VÌ SAO PHẢI CÓ CỬA NÀY TRƯỚC KHI VIẾT BỘ ĐỒNG BỘ. Không máy nào trong tay làn này gọi được
# tới `app.vietrip.com.vn` — cả máy Chủ tịch lẫn máy của làn đều bị chặn ra miền ấy. Viết bộ
# đồng bộ ngay bây giờ là viết dựa trên một tệp PDF chứ không dựa trên thứ máy chủ Vietrip
# thật sự trả về. Máy chủ VTOS trên Render thì gọi được — nên chỗ đầu tiên biết sự thật là nó.
#
# ĐẶT Ở ROUTER NÀY, KHÔNG PHẢI `routes.py`: vòng KS-18 đang giữ `routes.py` và chưa gộp. Hai
# vòng cùng sửa một tệp là một lần xung đột không cần thiết.
#
# CHỈ ĐỌC, KHÔNG GHI: cửa này không chạm cơ sở dữ liệu. Vai đọc đúng bằng `XEM` của màn công
# nợ — ai xem được công nợ thì xem được đường lấy công nợ ấy có thông không.
@router.get("/thu-ket-noi")
def thu_ket_noi(cua: str = "receivables", u: User = Depends(require_roles(*XEM))):
    """Thử gọi Vietrip MỘT lần nhẹ nhất (`pageSize=1`) và nói kết quả bằng tiếng Việt.

    KHÔNG trả về dòng dữ liệu nào, và KHÔNG BAO GIỜ in khoá — kể cả khi hỏng. Cửa này sinh ra
    để Chủ tịch tự mở xem, đúng cách `/he-thong/gio-may-chu` của vòng KS-18.
    """
    from app.services import vietrip_tai_chinh as VTC
    if cua not in VTC.CUA:
        raise HTTPException(422, f"cửa lạ «{cua}» — chỉ có {', '.join(VTC.CUA)}")
    return {**VTC.thu_ket_noi(cua), "ten_bien_moi_truong": VTC.TEN_BIEN}


@router.get("/lich-su")
def lich_su(so_ngay: int = 60, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    tu = date.today() - timedelta(days=max(1, min(so_ngay, 400)))
    anhs = db.execute(select(CongNoVietripAnh).where(CongNoVietripAnh.ngay >= tu)
                      .order_by(CongNoVietripAnh.ngay)).scalars().all()
    return [{"ngay": a.ngay, "so_booking": a.so_booking, "tong_con_thieu": float(a.tong_con_thieu or 0)} for a in anhs]


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 29/9/2026 · PHẢI TRẢ NCC THEO DỰ TOÁN TOUR (Vietrip → Quyết toán tour → Thống kê thu chi)
# ═══════════════════════════════════════════════════════════════════════════════════════════════
class TourPhaiTraIn(BaseModel):
    tour_id: int
    ma_tour: str = ""
    ten_tour: str = ""
    khoi_hanh: date | None = None
    ket_thuc: date | None = None
    tong_chi: float = 0          # Tổng chi (dự toán)
    da_chi: float = 0            # Thực tế đã chi


class NapPhaiTraIn(BaseModel):
    ngay: date
    dong: list[TourPhaiTraIn]
    ghi_chu: str = ""


def _dung_lai_so(db: Session, kq: dict) -> None:
    try:
        from app.api.v1.dong_tien import KHO_KHUNG
        from app.services import nghia_vu as NV
        kq["so_nghia_vu"] = NV.dong_bo(db)
        db.commit()
        KHO_KHUNG.xoa()
    except Exception as e:      # noqa: BLE001 — ảnh đã lưu; sổ dựng lại ở lượt robot kế tiếp
        db.rollback()
        kq["canh_bao_so_nghia_vu"] = f"{type(e).__name__}: {str(e)[:300]}"


@router.post("/nap-phai-tra")
def nap_phai_tra(data: NapPhaiTraIn, u: User = Depends(require_roles(*NAP)), db: Session = Depends(get_db)):
    """Nạp ảnh phải trả NCC theo dự toán từng tour. Còn phải chi = Tổng chi − Đã chi (máy chủ tính);
    tour hết phải chi thì bỏ. Nạp lại cùng ngày thì THAY ảnh."""
    if data.ngay > date.today() + timedelta(days=1):
        raise HTTPException(422, "Ngày báo cáo nằm ở tương lai.")
    ids = [d.tour_id for d in data.dong]
    trung = sorted({i for i in ids if ids.count(i) > 1})
    if trung:
        raise HTTPException(422, f"Tour trùng trong lô: {', '.join(map(str, trung[:10]))}")
    con = [(d, round(float(d.tong_chi or 0) - float(d.da_chi or 0), 2)) for d in data.dong]
    no = [(d, c) for d, c in con if c > 0]
    anh = db.execute(select(PhaiTraVietripAnh).where(PhaiTraVietripAnh.ngay == data.ngay)).scalar_one_or_none()
    if anh is None:
        anh = PhaiTraVietripAnh(ngay=data.ngay, so_lan_nap=1)
        db.add(anh)
        db.flush()
    else:
        db.execute(delete(PhaiTraVietripDong).where(PhaiTraVietripDong.anh_id == anh.id))
        anh.so_lan_nap = (anh.so_lan_nap or 0) + 1
    anh.so_tour = len(no)
    anh.tong_con_phai_chi = round(sum(c for _, c in no), 2)
    anh.ghi_chu = data.ghi_chu or ""
    anh.nguoi_nap = u.username
    anh.luc = datetime.now()
    for d, c in no:
        db.add(PhaiTraVietripDong(
            anh_id=anh.id, tour_id=d.tour_id, ma_tour=d.ma_tour, ten_tour=d.ten_tour,
            khoi_hanh=d.khoi_hanh, ket_thuc=d.ket_thuc, tong_chi=float(d.tong_chi or 0),
            da_chi=float(d.da_chi or 0), con_phai_chi=c))
    db.commit()
    kq = {"ngay": anh.ngay, "so_tour": anh.so_tour, "tong_con_phai_chi": float(anh.tong_con_phai_chi or 0),
          "nhan": len(data.dong), "bo_qua_het_no": len(data.dong) - len(no), "so_lan_nap": anh.so_lan_nap}
    _dung_lai_so(db, kq)
    return kq


@router.get("/phai-tra")
def xem_phai_tra(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    anh = db.execute(select(PhaiTraVietripAnh).order_by(desc(PhaiTraVietripAnh.ngay)).limit(1)).scalars().first()
    if anh is None:
        return {"co_du_lieu": False, "thong_bao": "Chưa có ảnh phải trả NCC theo dự toán Vietrip."}
    rows = db.execute(select(PhaiTraVietripDong).where(PhaiTraVietripDong.anh_id == anh.id)
                      .order_by(desc(PhaiTraVietripDong.con_phai_chi))).scalars().all()
    return {"co_du_lieu": True, "ngay": anh.ngay, "so_tour": anh.so_tour,
            "tong_con_phai_chi": float(anh.tong_con_phai_chi or 0), "luc": anh.luc,
            "dong": [{"tour_id": r.tour_id, "ma_tour": r.ma_tour, "ten_tour": r.ten_tour,
                      "khoi_hanh": r.khoi_hanh, "ket_thuc": r.ket_thuc, "tong_chi": float(r.tong_chi or 0),
                      "da_chi": float(r.da_chi or 0), "con_phai_chi": float(r.con_phai_chi or 0)} for r in rows]}
