"""Phòng Hướng dẫn – màn hình của người điều phối, khi toàn bộ HDV là cộng tác viên.

Vì sao tách khỏi màn hình Điều hành (/ops?tab=guides) thay vì mở quyền cho Trưởng phòng Hướng dẫn vào đó:

  Màn hình Điều hành gộp ba tab – Visa, HDV, Đội xe – và gọi /employees để lấy danh sách người. Endpoint
  đó trả về CẢ LƯƠNG của mọi nhân sự trong công ty. Mở quyền cho Trưởng phòng Hướng dẫn vào màn hình ấy
  là để ông đọc bảng lương của tất cả các phòng, chỉ vì ông cần biết ai còn hạn thẻ. Ở đây trả đúng các
  trường của nghề hướng dẫn, không có một đồng lương nào của người khác.

Cách gọi trong phân hệ này CỐ Ý không dùng chữ "phân công". Toàn bộ HDV nay là cộng tác viên; luật xét
NỘI DUNG quan hệ chứ không xét tên hợp đồng, và dữ liệu hệ thống chính là nơi lưu bằng chứng về nội dung
đó. Một hệ thống ghi "phân công – bắt buộc xác nhận trong 24 giờ" là hệ thống tự sinh ra bằng chứng rằng
công ty quản lý, điều hành người mà công ty khai là cộng tác viên. Nên ở đây là "chào chuyến", và 24 giờ
là HẠN HIỆU LỰC CỦA LỜI CHÀO, không phải hạn tuân thủ của người nhận.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User, Tour
from app.models.hr import Employee, GuideAssignment, GuideRate
from app.services import hr as H

router = APIRouter(prefix="/api/v1/huong-dan", tags=["huong-dan"])

# Ai đọc được phần hướng dẫn: người điều phối, Điều hành (đặt nhu cầu), HCNS (hồ sơ), và các vai trò
# giám sát. Kế toán có mặt vì thù lao HDV là giá vốn của tour và phải đối chiếu được.
READ = ("chutich", "tgd", "ptgd_doan", "tp_hd", "tp_dh", "nv_dh", "hcns", "ketoan", "bks", "cntt")

SAP_HET_HAN = 60          # ngày: báo trước khi thẻ hành nghề hết hạn


def _hdv_ra(e: Employee, hom_nay: date) -> dict:
    ok, vi_sao = H.guide_eligible(e, hom_nay)
    con = (e.card_expiry - hom_nay).days if e.card_expiry else None
    return {"id": e.id, "code": e.code, "full_name": e.full_name, "phone": e.phone,
            "loai_hop_dong": e.contract_type, "the_so": e.card_no, "the_loai": e.card_type,
            "the_het_han": e.card_expiry, "con_lai_ngay": con,
            "sap_het_han": con is not None and 0 <= con <= SAP_HET_HAN,
            "hoi_vien": e.member_org, "hop_dong_cong_tac": e.ctv_contract,
            "han_muc_tam_ung": e.advance_limit, "dang_lam": e.active,
            "du_dieu_kien": ok, "vi_sao": vi_sao}


@router.get("/hdv")
def danh_sach_hdv(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách hướng dẫn viên kèm tình trạng hành nghề. KHÔNG có trường lương của bất kỳ ai.

    Ba điều kiện của Điều 58 Luật Du lịch hiển thị thành ba cột riêng, không gộp thành một chữ "đạt":
    người điều phối phải biết thiếu cái gì để đi đòi cái đó, chứ không phải biết là hỏng."""
    hom_nay = date.today()
    ds = [_hdv_ra(e, hom_nay) for e in db.execute(
        select(Employee).where(Employee.department == "huong_dan").order_by(Employee.code)).scalars()]
    return {"rows": ds,
            "tong": len(ds),
            "du_dieu_kien": sum(1 for x in ds if x["du_dieu_kien"] and x["dang_lam"]),
            "the_sap_het_han": sum(1 for x in ds if x["sap_het_han"]),
            "thieu_hop_dong": sum(1 for x in ds if x["loai_hop_dong"] == "ctv" and not x["hop_dong_cong_tac"]),
            "ghi_chu": ("Cổng 13 chặn chào chuyến khi thiếu một trong ba điều kiện hành nghề: thẻ còn hạn, "
                        "hội viên tổ chức xã hội – nghề nghiệp, hợp đồng cộng tác đã ký.")}


@router.get("/chuyen-can-hdv")
def chuyen_can_hdv(so_ngay: int = 30, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Tour sắp khởi hành mà chưa có HDV nhận – việc phải làm của người điều phối, xếp theo ngày gần nhất.

    Không trả danh sách khách: người điều phối cần biết tuyến, ngày và quy mô để chọn người, không cần
    biết ai đi tour đó."""
    hom_nay = date.today()
    den = hom_nay + timedelta(days=max(1, so_ngay))
    da_co = {a.tour_id for a in db.execute(select(GuideAssignment).where(
        GuideAssignment.status != "huy")).scalars()}
    out = []
    for t in db.execute(select(Tour).where(Tour.start_date >= hom_nay, Tour.start_date <= den)
                        .order_by(Tour.start_date)).scalars():
        if t.id in da_co: continue
        out.append({"tour_id": t.id, "code": t.code, "name": t.name, "start_date": t.start_date,
                    "end_date": t.end_date, "so_ngay": (t.end_date - t.start_date).days + 1,
                    "so_khach_du_kien": t.planned_pax, "trang_thai": t.status,
                    "con_lai_ngay": (t.start_date - hom_nay).days})
    return out


@router.get("/chao-chuyen")
def chao_chuyen(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Các lời chào chuyến đã gửi và tình trạng của chúng.

    'Quá hạn' ở đây nghĩa là lời chào hết hiệu lực và chuyến nên chào người khác – KHÔNG phải là HDV vi
    phạm. Khác biệt này là khác biệt giữa quan hệ dịch vụ và quan hệ lao động, nên nó phải nằm trong dữ
    liệu chứ không chỉ nằm trong lời nói."""
    hom_nay = date.today()
    ten = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    out = []
    for a in db.execute(select(GuideAssignment).order_by(desc(GuideAssignment.id)).limit(200)).scalars():
        t = db.get(Tour, a.tour_id)
        qua_han = (a.status == "cho_xac_nhan"
                   and (date.today() - a.assigned_at.date()).days >= 1)
        tre_bao_cao = (a.status == "da_xac_nhan" and t is not None and t.end_date < hom_nay
                       and not a.report_submitted and (hom_nay - t.end_date).days > 3)
        out.append({"id": a.id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
                    "khoi_hanh": t.start_date if t else None, "hdv": ten.get(a.guide_id, ""),
                    "so_ngay": a.days, "don_gia": a.rate_per_day, "le_tet": a.holiday,
                    "thu_lao": a.rate_per_day * a.days * (2 if a.holiday else 1),
                    "trang_thai": a.status, "chao_luc": a.assigned_at, "nhan_luc": a.confirmed_at,
                    "loi_chao_qua_han": qua_han, "da_bao_cao": a.report_submitted,
                    "tre_bao_cao": tre_bao_cao, "da_hoan_ung": a.advance_settled,
                    "treo_chao_moi": tre_bao_cao or not a.advance_settled})
    return out


@router.get("/tong-quan")
def tong_quan(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    hom_nay = date.today()
    hdv = [_hdv_ra(e, hom_nay) for e in db.execute(
        select(Employee).where(Employee.department == "huong_dan", Employee.active == True)).scalars()]  # noqa: E712
    chao = chao_chuyen(u, db)
    gia = db.execute(select(GuideRate).where(GuideRate.status == "active")).scalars().all()
    return {"hdv_dang_cong_tac": len(hdv),
            "du_dieu_kien": sum(1 for x in hdv if x["du_dieu_kien"]),
            "the_sap_het_han": sum(1 for x in hdv if x["sap_het_han"]),
            "cho_nhan_chuyen": sum(1 for c in chao if c["trang_thai"] == "cho_xac_nhan"),
            "loi_chao_qua_han": sum(1 for c in chao if c["loi_chao_qua_han"]),
            "tre_bao_cao": sum(1 for c in chao if c["tre_bao_cao"]),
            "dang_bi_treo": sum(1 for c in chao if c["treo_chao_moi"]),
            "tuyen_co_don_gia": len({g.route for g in gia}),
            "chuyen_chua_co_hdv": len(chuyen_can_hdv(30, u, db))}
