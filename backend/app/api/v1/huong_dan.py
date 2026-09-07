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
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User, Tour
from app.models.hr import Employee, GuideAssignment, GuideRate
from app.services import hr as H, rules as R

router = APIRouter(prefix="/api/v1/huong-dan", tags=["huong-dan"])

# Ai đọc được phần hướng dẫn: người điều phối, Điều hành (đặt nhu cầu), HCNS (hồ sơ), và các vai trò
# giám sát. Kế toán có mặt vì thù lao HDV là giá vốn của tour và phải đối chiếu được.
READ = ("chutich", "tgd", "ptgd_doan", "tp_hd", "tp_dh", "nv_dh", "hcns", "ketoan", "bks", "cntt")

SAP_HET_HAN = 60          # ngày: báo trước khi thẻ hành nghề hết hạn
DIEU_PHOI = ("tp_hd", "tp_dh", "nv_dh", "hcns", "cntt")     # người được chào chuyến


def han_tra_loi(db: Session, tu: datetime | None = None) -> datetime:
    """Lời chào hết hiệu lực lúc nào. Đọc từ tham số, không viết cứng 24 giờ vào mã nguồn."""
    try:
        gio = R.get_param(db, "hdv_han_tra_loi_gio")
    except KeyError:
        gio = 24
    return (tu or datetime.now()) + timedelta(hours=float(gio or 24))


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
        qua_han = (a.status == "cho_xac_nhan" and a.han_tra_loi is not None
                   and datetime.now() > a.han_tra_loi)
        tre_bao_cao = (a.status == "da_xac_nhan" and t is not None and t.end_date < hom_nay
                       and not a.report_submitted and (hom_nay - t.end_date).days > 3)
        out.append({"id": a.id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
                    "khoi_hanh": t.start_date if t else None, "hdv": ten.get(a.guide_id, ""),
                    "so_ngay": a.days, "don_gia": a.rate_per_day, "le_tet": a.holiday,
                    "thu_lao": a.rate_per_day * a.days * (2 if a.holiday else 1),
                    "trang_thai": a.status, "chao_luc": a.assigned_at, "nhan_luc": a.confirmed_at,
                    "loi_chao_qua_han": qua_han, "han_tra_loi": a.han_tra_loi, "ly_do": a.ly_do,
                    "da_bao_cao": a.report_submitted,
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


# ====================== CHÀO CHUYẾN ======================
class ChaoIn(BaseModel):
    tour_id: int
    guide_id: int
    days: int
    rate_per_day: float
    rate_id: int | None = None
    holiday: bool = False


@router.post("/chao-chuyen", status_code=201)
def chao(data: ChaoIn, u: User = Depends(require_roles(*DIEU_PHOI)), db: Session = Depends(get_db)):
    """Chào một chuyến cho một hướng dẫn viên.

    Vẫn qua cổng 13: có quyền chào không có nghĩa là chào được cho người thiếu điều kiện hành nghề –
    một chuyến dẫn thiếu thẻ hoặc thiếu hợp đồng thì cả doanh nghiệp lẫn người dẫn cùng bị xử phạt."""
    e = db.get(Employee, data.guide_id); t = db.get(Tour, data.tour_id)
    if e is None or t is None: raise HTTPException(404, "Không có hướng dẫn viên hoặc tour")
    ok, vi_sao = H.guide_eligible(e, t.start_date)
    if not ok: raise HTTPException(422, {"gate": "CONG_13", "message": f"Không chào chuyến được: {vi_sao}"})
    dang_cho = db.execute(select(GuideAssignment).where(
        GuideAssignment.tour_id == t.id,
        GuideAssignment.status.in_(("cho_xac_nhan", "da_xac_nhan")))).scalars().first()
    if dang_cho is not None:
        raise HTTPException(422, "Chuyến này đang có lời chào chờ trả lời hoặc đã có người nhận. Đóng lời "
                                 "chào cũ trước khi chào người khác – hai người cùng nhận một chuyến thì "
                                 "công ty trả thù lao hai lần.")
    treo = _dang_treo(db, e.id)
    if treo:
        raise HTTPException(422, f"Hướng dẫn viên đang bị treo chào chuyến: {treo}")
    a = GuideAssignment(tour_id=t.id, guide_id=e.id, days=data.days, rate_per_day=data.rate_per_day,
                        rate_id=data.rate_id, holiday=data.holiday, assigned_by=u.username,
                        han_tra_loi=han_tra_loi(db))
    db.add(a); db.flush()
    R.audit(db, u.username, u.role, "chao_chuyen_hdv", f"tour:{t.code}",
            after={"hdv": e.full_name, "so_ngay": a.days, "don_gia": a.rate_per_day,
                   "han_tra_loi": f"{a.han_tra_loi:%Y-%m-%d %H:%M}"})
    db.commit()
    return {"id": a.id, "message": f"Đã chào chuyến {t.code} cho {e.full_name}. Lời chào có hiệu lực đến "
                                   f"{a.han_tra_loi:%H:%M %d/%m/%Y}; quá hạn thì chào người khác."}


def _dang_treo(db: Session, guide_id: int) -> str:
    """Treo chào chuyến khi còn nợ báo cáo tour hoặc chưa hoàn ứng.

    Đây là điều kiện của HỢP ĐỒNG DỊCH VỤ – chưa nghiệm thu xong việc trước thì chưa giao việc sau –
    chứ không phải hình thức kỷ luật. Khác biệt đó quan trọng với một đội ngũ cộng tác viên."""
    hom_nay = date.today()
    for a in db.execute(select(GuideAssignment).where(
            GuideAssignment.guide_id == guide_id, GuideAssignment.status == "da_xac_nhan")).scalars():
        t = db.get(Tour, a.tour_id)
        if t is None or t.end_date >= hom_nay: continue
        qua = (hom_nay - t.end_date).days
        if qua > 3 and not a.report_submitted:
            return f"chưa nộp báo cáo tour {t.code} (kết thúc {t.end_date:%d/%m}, quá {qua} ngày)"
        if not a.advance_settled:
            return f"chưa hoàn ứng tour {t.code}"
    return ""


class DongIn(BaseModel):
    ly_do: str = ""


@router.post("/chao-chuyen/{aid}/dong")
def dong_loi_chao(aid: int, data: DongIn, u: User = Depends(require_roles(*DIEU_PHOI)),
                  db: Session = Depends(get_db)):
    """Đóng một lời chào đã quá hạn để chào người khác.

    Trạng thái ghi là HẾT HẠN, không phải vi phạm: lời chào là lời chào, hết hiệu lực thì thôi."""
    a = db.get(GuideAssignment, aid)
    if a is None: raise HTTPException(404, "Không có lời chào này")
    if a.status != "cho_xac_nhan":
        raise HTTPException(422, f"Lời chào đang ở trạng thái '{a.status}', không đóng được")
    a.status = "het_han"; a.ly_do = (data.ly_do or "hết hạn trả lời")[:200]; a.tra_loi_luc = datetime.now()
    R.audit(db, u.username, u.role, "dong_loi_chao_hdv", f"assign:{a.id}", after={"ly_do": a.ly_do})
    db.commit()
    return {"message": "Đã đóng lời chào – chuyến này chào được cho người khác."}


# ====================== FORM HỒ SƠ HÀNH NGHỀ ======================
class HoSoIn(BaseModel):
    """Đúng các trường của NGHỀ HƯỚNG DẪN, không có trường nào khác.

    Cố ý không nhận full_name, department, base_salary, contract_type: form này để người phụ trách cập
    nhật hồ sơ hành nghề, không phải để sửa lương hay chuyển phòng cho ai. Một biểu mẫu nhận cả những
    trường nó không có nhiệm vụ sửa là biểu mẫu sớm muộn sẽ sửa nhầm chúng."""
    the_so: str | None = None
    the_loai: str | None = None
    the_het_han: date | None = None
    hoi_vien: bool | None = None
    hop_dong_cong_tac: bool | None = None
    dien_thoai: str | None = None
    tuyen_phu_trach: str | None = None
    han_muc_tam_ung: float | None = None


def _kiem_ho_so(db: Session, data: HoSoIn, e: Employee | None = None) -> None:
    if data.the_loai is not None and data.the_loai not in ("", "noi_dia", "quoc_te"):
        raise HTTPException(422, "Loại thẻ phải là nội địa hoặc quốc tế")
    if data.han_muc_tam_ung is not None and data.han_muc_tam_ung < 0:
        raise HTTPException(422, "Hạn mức tạm ứng không được âm")
    the = (data.the_so or "").strip()
    if the:
        trung = db.execute(select(Employee).where(Employee.card_no == the)).scalars().first()
        if trung is not None and (e is None or trung.id != e.id):
            raise HTTPException(422, f"Số thẻ {the} đã gắn với {trung.full_name} ({trung.code}). Một thẻ "
                                     "chỉ thuộc một người – trùng thẻ là hai người cùng dẫn bằng một thẻ, "
                                     "và cả hai chuyến đều sai hồ sơ.")


def _ap_ho_so(e: Employee, data: HoSoIn) -> None:
    if data.the_so is not None: e.card_no = data.the_so.strip()[:30]
    if data.the_loai is not None: e.card_type = data.the_loai.strip()[:20]
    if data.the_het_han is not None: e.card_expiry = data.the_het_han
    if data.hoi_vien is not None: e.member_org = data.hoi_vien
    if data.hop_dong_cong_tac is not None: e.ctv_contract = data.hop_dong_cong_tac
    if data.dien_thoai is not None: e.phone = data.dien_thoai.strip()[:30]
    if data.tuyen_phu_trach is not None: e.duties = data.tuyen_phu_trach.strip()
    if data.han_muc_tam_ung is not None: e.advance_limit = data.han_muc_tam_ung


@router.put("/hdv/{eid}")
def sua_ho_so(eid: int, data: HoSoIn, u: User = Depends(require_roles(*DIEU_PHOI)),
              db: Session = Depends(get_db)):
    """Cập nhật hồ sơ hành nghề của một hướng dẫn viên."""
    e = db.get(Employee, eid)
    if e is None or e.department != "huong_dan":
        raise HTTPException(404, "Không có hướng dẫn viên này")
    _kiem_ho_so(db, data, e)
    truoc = {"the_so": e.card_no, "the_het_han": str(e.card_expiry or ""), "hoi_vien": e.member_org,
             "hop_dong_cong_tac": e.ctv_contract}
    _ap_ho_so(e, data)
    db.flush()
    ok, vi_sao = H.guide_eligible(e, date.today())
    R.audit(db, u.username, u.role, "sua_ho_so_hdv", f"employee:{e.code}", before=truoc,
            after={"the_so": e.card_no, "the_het_han": str(e.card_expiry or ""),
                   "hoi_vien": e.member_org, "hop_dong_cong_tac": e.ctv_contract})
    db.commit()
    return {**_hdv_ra(e, date.today()),
            "message": ("Đã lưu. Đủ điều kiện hành nghề – chào chuyến được." if ok
                        else f"Đã lưu, nhưng còn thiếu: {vi_sao}. Cổng 13 vẫn chặn chào chuyến.")}


class HdvMoiIn(HoSoIn):
    ho_ten: str
    ma_nv: str = ""


@router.post("/hdv", status_code=201)
def them_hdv(data: HdvMoiIn, u: User = Depends(require_roles(*DIEU_PHOI)), db: Session = Depends(get_db)):
    """Thêm một hướng dẫn viên cộng tác mới.

    Loại hợp đồng ghi cứng là cộng tác viên: toàn bộ HDV đã chuyển sang cộng tác viên (07/9/2026), và
    một ô chọn ở đây chỉ tạo ra đường mở lại quan hệ lao động mà không ai để ý."""
    if not data.ho_ten.strip(): raise HTTPException(422, "Thiếu họ tên")
    ma = (data.ma_nv or "").strip().upper()
    if ma and db.execute(select(Employee).where(Employee.code == ma)).scalars().first() is not None:
        raise HTTPException(422, f"Mã nhân viên {ma} đã có người dùng")
    _kiem_ho_so(db, data, None)
    e = Employee(code=ma or H.next_code(db, Employee, "NS"), full_name=data.ho_ten.strip()[:120],
                 department="huong_dan", position="hdv", contract_type="ctv")
    _ap_ho_so(e, data)
    db.add(e); db.flush()
    R.audit(db, u.username, u.role, "them_hdv", f"employee:{e.code}",
            after={"ho_ten": e.full_name, "the_so": e.card_no})
    db.commit()
    return {**_hdv_ra(e, date.today()), "message": f"Đã tạo hồ sơ {e.code} – {e.full_name}."}
