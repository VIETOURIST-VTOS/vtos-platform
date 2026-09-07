"""Nhà cung cấp và đơn đặt dịch vụ – phần nghiệp vụ.

Điểm cốt lõi của tệp này không phải danh mục, mà là HAI CHỐT CHẶN trên đường tiền ra:

  1. Số tài khoản nhà cung cấp chỉ đổi được qua một đề nghị có NGƯỜI THỨ HAI xác nhận. Cho tới lúc đó, số
     đang hiệu lực không thay đổi – nghĩa là mọi khoản chi vẫn đi vào tài khoản cũ. Đây là cách gian lận
     phổ biến nhất trong thanh toán: đổi số tài khoản của một nhà cung cấp có thật.
  2. Người đề nghị KHÔNG tự xác nhận được. Một chốt chặn hai người mà một người bấm được cả hai nút thì
     không phải chốt chặn, chỉ là hai lần bấm.
"""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour
from app.models.suppliers import (Supplier, SupplierBankChange, ServiceOrder, LOAI_NCC, TRANG_THAI_DON)


def sinh_ma(db: Session, prefix: str, model, col) -> str:
    n = db.execute(select(func.count(model.id))).scalar() or 0
    return f"{prefix}{n + 1:04d}"


def tao_ncc(db: Session, data: dict, boi: str) -> Supplier:
    ten = (data.get("ten") or "").strip()
    if not ten: raise ValueError("Phải có tên nhà cung cấp")
    if data.get("loai") and data["loai"] not in LOAI_NCC:
        raise ValueError(f"Loại nhà cung cấp không hợp lệ. Chỉ nhận {', '.join(LOAI_NCC)}")
    trung = db.execute(select(Supplier).where(func.lower(Supplier.ten) == ten.lower())).scalars().first()
    if trung is not None:
        raise ValueError(f"Đã có nhà cung cấp tên \"{trung.ten}\" (mã {trung.code}) – dùng lại hồ sơ đó thay vì "
                         "tạo bản thứ hai, nếu không công nợ của một đối tác sẽ nằm ở hai chỗ")
    s = Supplier(code=sinh_ma(db, "NCC", Supplier, Supplier.id), ten=ten,
                 loai=data.get("loai") or "khac", ma_so_thue=(data.get("ma_so_thue") or "").strip(),
                 dia_chi=data.get("dia_chi") or "", nguoi_lien_he=data.get("nguoi_lien_he") or "",
                 dien_thoai=data.get("dien_thoai") or "", email=data.get("email") or "",
                 so_tai_khoan=(data.get("so_tai_khoan") or "").strip(),
                 ngan_hang=data.get("ngan_hang") or "", chu_tai_khoan=data.get("chu_tai_khoan") or "",
                 dieu_khoan_tt=data.get("dieu_khoan_tt") or "", note=data.get("note") or "",
                 created_by=boi)
    db.add(s); db.flush()
    return s


def canh_bao(db: Session, s: Supplier) -> list[str]:
    """Những điều cần biết TRƯỚC khi đặt dịch vụ hoặc chi tiền cho nhà cung cấp này."""
    cb = []
    if not (s.ma_so_thue or "").strip():
        cb.append("Chưa có mã số thuế – khoản chi cho nhà cung cấp này sẽ khó lấy hóa đơn GTGT, "
                  "và chi không có hóa đơn thì không được trừ khi tính thuế TNDN")
    if not (s.so_tai_khoan or "").strip():
        cb.append("Chưa có số tài khoản – chỉ thanh toán được bằng tiền mặt")
    cho = db.execute(select(SupplierBankChange)
                     .where(SupplierBankChange.supplier_id == s.id,
                            SupplierBankChange.status == "cho_xac_nhan")).scalars().first()
    if cho is not None:
        cb.append(f"Đang có đề nghị ĐỔI SỐ TÀI KHOẢN chờ người thứ hai xác nhận (do {cho.de_nghi_boi} đề nghị "
                  f"ngày {cho.de_nghi_luc:%d/%m/%Y}). Số đang hiệu lực vẫn là số cũ – đừng chuyển tiền theo "
                  "số mới khi chưa xác nhận.")
    if not s.active:
        cb.append("Nhà cung cấp đã ngưng hoạt động")
    return cb


# ====================== ĐỔI SỐ TÀI KHOẢN: HAI NGƯỜI ======================
def de_nghi_doi_tk(db: Session, s: Supplier, data: dict, boi: str) -> SupplierBankChange:
    moi = (data.get("so_tk_moi") or "").strip()
    if not moi: raise ValueError("Phải nhập số tài khoản mới")
    if moi == (s.so_tai_khoan or "").strip() and (data.get("ngan_hang_moi") or "") == s.ngan_hang:
        raise ValueError("Số tài khoản mới trùng số đang hiệu lực – không có gì để đổi")
    if not (data.get("chung_tu") or "").strip():
        raise ValueError("Phải ghi số/tên văn bản của nhà cung cấp thông báo đổi tài khoản. Đổi tài khoản "
                         "không có văn bản là đường vào của gian lận thanh toán.")
    dang_cho = db.execute(select(SupplierBankChange)
                          .where(SupplierBankChange.supplier_id == s.id,
                                 SupplierBankChange.status == "cho_xac_nhan")).scalars().first()
    if dang_cho is not None:
        raise ValueError("Nhà cung cấp này đang có một đề nghị đổi tài khoản chờ xác nhận – xử lý xong "
                         "đề nghị đó rồi mới tạo đề nghị mới")
    c = SupplierBankChange(supplier_id=s.id, so_tk_cu=s.so_tai_khoan, ngan_hang_cu=s.ngan_hang,
                           chu_tk_cu=s.chu_tai_khoan, so_tk_moi=moi,
                           ngan_hang_moi=data.get("ngan_hang_moi") or "",
                           chu_tk_moi=data.get("chu_tk_moi") or "",
                           ly_do=data.get("ly_do") or "", chung_tu=data.get("chung_tu") or "",
                           de_nghi_boi=boi)
    db.add(c); db.flush()
    return c


def xac_nhan_doi_tk(db: Session, c: SupplierBankChange, boi: str, dong_y: bool, ghi_chu: str = "") -> dict:
    if c.status != "cho_xac_nhan":
        raise ValueError(f"Đề nghị này đã ở trạng thái '{c.status}', không xử lý lại")
    if (c.de_nghi_boi or "").strip().lower() == (boi or "").strip().lower():
        raise ValueError("Người đề nghị không tự xác nhận được. Một chốt chặn hai người mà một người bấm "
                         "được cả hai nút thì không phải chốt chặn.")
    s = db.get(Supplier, c.supplier_id)
    c.xac_nhan_boi, c.xac_nhan_luc, c.ghi_chu = boi, datetime.now(), ghi_chu[:300]
    if not dong_y:
        c.status = "tu_choi"
        return {"status": c.status, "message": "Đã từ chối – số tài khoản giữ nguyên"}
    c.status = "da_xac_nhan"
    s.so_tai_khoan, s.ngan_hang, s.chu_tai_khoan = c.so_tk_moi, c.ngan_hang_moi, c.chu_tk_moi
    return {"status": c.status,
            "message": f"Đã đổi số tài khoản của {s.ten} sang {c.so_tk_moi} – có hiệu lực từ bây giờ"}


# ====================== ĐƠN ĐẶT DỊCH VỤ ======================
def tao_don(db: Session, data: dict, boi: str) -> ServiceOrder:
    s = db.get(Supplier, int(data.get("supplier_id") or 0))
    if s is None: raise ValueError("Không có nhà cung cấp này")
    if not s.active: raise ValueError(f"Nhà cung cấp {s.ten} đã ngưng hoạt động – không đặt dịch vụ mới")
    t = db.get(Tour, int(data.get("tour_id") or 0))
    if t is None:
        raise ValueError("Đơn đặt dịch vụ phải gắn TOUR. Chi phí không gắn tour thì không quy được vào giá "
                         "thành, và cuối kỳ nó nằm trong một cục chi phí chung không ai chia lại được.")
    if not (data.get("noi_dung") or "").strip():
        raise ValueError("Phải ghi nội dung dịch vụ đặt")
    sl = float(data.get("so_luong") or 0); dg = float(data.get("don_gia") or 0)
    tt = float(data.get("thanh_tien") or 0) or round(sl * dg)
    if tt <= 0: raise ValueError("Thành tiền phải lớn hơn 0")
    d = ServiceOrder(code=sinh_ma(db, "DV", ServiceOrder, ServiceOrder.id), supplier_id=s.id, tour_id=t.id,
                     loai=data.get("loai") or s.loai, noi_dung=data["noi_dung"][:300],
                     ngay_su_dung=data.get("ngay_su_dung"), so_luong=sl, don_vi=data.get("don_vi") or "",
                     don_gia=dg, thanh_tien=tt, note=data.get("note") or "", created_by=boi)
    db.add(d); db.flush()
    return d


def chuyen_trang_thai(db: Session, d: ServiceOrder, moi: str, boi: str, xac_nhan_ncc: str = "") -> dict:
    if moi not in TRANG_THAI_DON:
        raise ValueError(f"Trạng thái không hợp lệ. Chỉ nhận {', '.join(TRANG_THAI_DON)}")
    if moi == "da_xac_nhan" and not (xac_nhan_ncc or d.xac_nhan_ncc).strip():
        raise ValueError("Ghi nhận nhà cung cấp đã xác nhận thì phải có căn cứ (số văn bản, tin nhắn, email) "
                         "– không thì sau này không ai biết đơn đã được nhận hay chưa")
    if xac_nhan_ncc: d.xac_nhan_ncc = xac_nhan_ncc[:200]
    d.status = moi
    return {"status": d.status, "message": f"Đơn {d.code}: {TRANG_THAI_DON[moi]}"}


def tong_hop_theo_tour(db: Session, tour_id: int) -> dict:
    rows = list(db.execute(select(ServiceOrder).where(ServiceOrder.tour_id == tour_id,
                                                      ServiceOrder.status != "huy")).scalars())
    return {"so_don": len(rows), "tong_tien": float(round(sum(r.thanh_tien for r in rows)))}
