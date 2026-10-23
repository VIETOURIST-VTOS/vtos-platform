"""API ngân quỹ – tài chính: hợp đồng vay/đầu tư (3.9), lịch thu-trả, dự báo 13 tuần, báo cáo tài chính tuần."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User
from app.models.finance import FinContract, FinSchedule, CashPlanItem, CONTRACT_KINDS
from app.services import finance as F
from app.services import pham_vi_phap_nhan as PV
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["tai-chinh"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks")
WRITE = ("ketoan",)


def c_out(c: FinContract) -> dict:
    return {"id": c.id, "code": c.code, "kind": c.kind, "kind_name": CONTRACT_KINDS.get(c.kind, c.kind), "entity": c.entity, "company_id": c.company_id, "loan_group": c.loan_group, "partner": c.partner, "contract_no": c.contract_no,
            "signed_on": c.signed_on, "principal": c.principal, "outstanding": c.outstanding, "interest_rate": c.interest_rate, "maturity": c.maturity, "collateral": c.collateral,
            "purpose": c.purpose, "owner": c.owner, "approval_ref": c.approval_ref, "related_party": c.related_party, "status": c.status, "note": c.note,
            "schedule": [{"id": s.id, "due_date": s.due_date, "kind": s.kind, "amount": s.amount, "status": s.status, "done_on": s.done_on, "bank_ref": s.bank_ref} for s in c.schedule]}


@router.get("/fin/meta")
def meta(u: User = Depends(current_user)):
    return {"kinds": CONTRACT_KINDS}


@router.get("/fin/contracts")
def contracts(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    F.mark_overdue(db)
    return [c_out(c) for c in db.execute(select(FinContract).order_by(FinContract.kind, desc(FinContract.id))).scalars()]


class ContractIn(BaseModel):
    kind: str
    entity: str = "Công ty mẹ"
    company_id: int | None = None
    loan_group: str = ""
    partner: str
    contract_no: str = ""
    signed_on: date | None = None
    principal: float | None = None
    outstanding: float | None = None
    interest_rate: float = 0
    maturity: date | None = None
    collateral: str = ""
    purpose: str = ""
    owner: str = ""
    approval_ref: str = ""
    related_party: bool = False
    note: str = ""
    months: int = 0
    first_due: date | None = None


@router.post("/fin/contracts", status_code=201)
def create(data: ContractIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    d = data.model_dump(); months = d.pop("months"); first = d.pop("first_due")
    try:
        c = F.create_contract(db, u, d, months, first)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"contract": c_out(c), "message": f"Đã lập hồ sơ {c.code}" + (f" – {len(c.schedule)} dòng lịch" if c.schedule else "")}


class SchedIn(BaseModel):
    due_date: date
    kind: str
    amount: float
    ky: int | None = None            # V12 – số kỳ trong lịch trả nợ
    ma_dao_han: str = ""             # V12 – hai chân một lần đảo nợ mang cùng mã này


@router.post("/fin/contracts/{cid}/schedule", status_code=201)
def add_sched(cid: int, data: SchedIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = db.get(FinContract, cid)
    if not c: raise HTTPException(404, "Không có hợp đồng")
    if data.kind not in ("tra_goc", "tra_lai", "thu_hoi", "giai_ngan", "nhan_vay"): raise HTTPException(422, "Loại lịch không hợp lệ")
    db.add(FinSchedule(contract_id=c.id, **data.model_dump()))
    R.audit(db, u.username, u.role, "them_lich_tai_chinh", f"fin:{c.code}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã thêm dòng lịch"}


class SettleIn(BaseModel):
    done_on: date
    bank_ref: str = ""
    amount: float | None = None


@router.post("/fin/schedule/{sid}/settle")
def settle(sid: int, data: SettleIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    s = db.get(FinSchedule, sid)
    if not s: raise HTTPException(404, "Không có dòng lịch")
    try:
        F.settle(db, u, s, data.done_on, data.bank_ref, data.amount)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã ghi nhận {s.kind} {s.amount:,.0f} đ – dư nợ còn {s.contract.outstanding:,.0f} đ"}


class DaoHanIn(BaseModel):
    tra_goc_id: int
    nhan_moi_id: int
    ma: str


@router.post("/fin/dao-han")
def dat_dao_han(data: DaoHanIn, u: User = Depends(require_roles(*WRITE)),
                db: Session = Depends(get_db)):
    """V12 – nối hai chân một lần đảo nợ bằng một mã chung, TRƯỚC khi ghi sổ.

    Đảo nợ là trả gốc khoản cũ và nhận giải ngân khoản mới trong cùng một ngày; tiền thực chất không
    ra khỏi ngân hàng. Ghi hai bút toán rời rạc thì sổ đúng nhưng không ai đọc ra được đó là một lần
    đảo, và chỉ tiêu "tiền chi trả nợ gốc vay" trên lưu chuyển tiền tệ bị thổi lên bằng đúng số tiền
    không hề chuyển đi đâu.
    """
    from app.services import vay_but_toan as VBT
    a, b = db.get(FinSchedule, data.tra_goc_id), db.get(FinSchedule, data.nhan_moi_id)
    if a is None or b is None:
        raise HTTPException(404, "Không có dòng lịch")
    if not data.ma.strip():
        raise HTTPException(422, "Phải có mã đáo hạn – mã rỗng thì hai chân không nối được với nhau")
    VBT.dat_ma_dao_han(db, a, b, data.ma.strip()[:40])
    R.audit(db, u.username, u.role, "dat_ma_dao_han", f"dao_han:{data.ma}",
            after={"tra_goc": a.id, "nhan_moi": b.id})
    db.commit()
    return {"message": f"Đã nối hai chân đáo hạn bằng mã '{data.ma.strip()}'"}


@router.get("/fin/doi-chieu-vay")
def doi_chieu_vay(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """V12 nghiệm thu: dư nợ vay TRÊN SỔ có khớp LỊCH TRẢ NỢ không, và lệch vì đâu."""
    from app.services import vay_but_toan as VBT
    return VBT.doi_chieu(db)


@router.get("/fin/schedule/{sid}/xem-truoc-but-toan")
def xem_truoc_but_toan(sid: int, u: User = Depends(require_roles(*READ)),
                       db: Session = Depends(get_db)):
    """Bút toán SẼ ghi cho một kỳ. Chỉ đọc – xem trước rồi mới bấm ghi."""
    from app.services import vay_but_toan as VBT
    s = db.get(FinSchedule, sid)
    if s is None: raise HTTPException(404, "Không có dòng lịch")
    return VBT.xem_truoc(db, s)


@router.get("/fin/forecast")
def forecast(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return F.forecast_13w(db)


@router.get("/fin/weekly")
def weekly(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    F.mark_overdue(db)
    return F.weekly_finance(db)


@router.get("/fin/plan")
def plan(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return [{"id": i.id, "due_date": i.due_date, "direction": i.direction, "category": i.category, "description": i.description, "amount": i.amount, "recurring_monthly": i.recurring_monthly}
            for i in db.execute(select(CashPlanItem).order_by(CashPlanItem.due_date)).scalars()]


class PlanIn(BaseModel):
    due_date: date
    direction: str
    category: str
    description: str
    amount: float
    recurring_monthly: bool = False


@router.post("/fin/plan", status_code=201)
def plan_add(data: PlanIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    if data.direction not in ("in", "out"): raise HTTPException(422, "direction: in/out")
    db.add(CashPlanItem(**data.model_dump(), created_by=u.username)); db.commit()
    return {"message": "Đã thêm khoản kế hoạch"}


@router.delete("/fin/plan/{pid}")
def plan_del(pid: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    i = db.get(CashPlanItem, pid)
    if i: db.delete(i); db.commit()
    return {"message": "Đã xóa"}


@router.get("/fin/vay-xe")
def vay_xe(u: User = Depends(require_roles(*READ, "tp_dh")), db: Session = Depends(get_db)):
    """Bản đồ khế ước vay ↔ xe thế chấp, cảnh báo đáo hạn và xe đã ra khỏi đội nhưng còn thế chấp."""
    return F.vay_xe(db)


class KheUocNapIn(BaseModel):
    contract_no: str
    partner: str
    entity: str = "Công ty mẹ"
    loan_group: str = "vay_xe_45cho"
    principal: float | None = None
    outstanding: float | None = None
    interest_rate: float = 0
    signed_on: date | None = None
    maturity: date | None = None
    collateral: str = ""
    purpose: str = ""
    note: str = ""
    xe: list[str] = []


class NapVayIn(BaseModel):
    khe_uoc: list[KheUocNapIn]
    nguon: str = ""
    tao_xe_da_ban: list[dict] = []


@router.post("/fin/vay-xe/nap")
def nap_vay_xe(data: NapVayIn, u: User = Depends(require_roles("ketoan", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Nạp hồ sơ khế ước vay từ bộ hồ sơ ngân hàng, kèm danh sách xe là tài sản bảo đảm.

    Khớp theo SỐ HỢP ĐỒNG: chạy lại lần hai chỉ cập nhật dư nợ/lãi suất/đáo hạn của khế ước đã có,
    không tạo bản ghi trùng. Biển số không tìm thấy trong danh mục xe được trả về để rà chứ không
    tự tạo xe – trừ những xe đã bán khai báo riêng ở `tao_xe_da_ban`, vì chính những xe đó mới là
    lý do phải theo dõi: xe đã ra khỏi đội nhưng hồ sơ vay vẫn ghi là tài sản bảo đảm.
    """
    from app.models.hr import Vehicle
    from app.models.fleet import Collateral
    from app.models.core import Company
    cty = {c.name.lower(): c.id for c in db.execute(select(Company)).scalars()}

    def tim_cty(ten: str) -> int | None:
        t = (ten or "").lower()
        for name, cid in cty.items():
            if t and (t in name or name in t): return cid
        return None

    tao_xe = []
    for x in data.tao_xe_da_ban:
        plate = (x.get("plate") or "").strip()
        if not plate: continue
        v = db.execute(select(Vehicle).where(Vehicle.plate == plate)).scalar_one_or_none()
        if v is None:
            v = Vehicle(plate=plate, seats=45, active=False, lifecycle="da_ban", source_note=x.get("note", ""))
            db.add(v); db.flush(); tao_xe.append(plate)
    db.flush()
    xe_map = {v.plate: v for v in db.execute(select(Vehicle)).scalars()}

    tao, cap_nhat, gan_xe, khong_thay_xe = [], [], 0, []
    for k in data.khe_uoc:
        c = db.execute(select(FinContract).where(FinContract.contract_no == k.contract_no, FinContract.kind == "vay")).scalar_one_or_none()
        d = k.model_dump(); plates = d.pop("xe")
        if c is None:
            c = FinContract(code=F.next_code(db), kind="vay", created_by=u.username, **d)
            if not c.outstanding: c.outstanding = c.principal
            db.add(c); db.flush(); tao.append(c.contract_no)
        else:
            for f in ("partner", "entity", "loan_group", "principal", "outstanding", "interest_rate", "signed_on", "maturity", "collateral", "purpose", "note"):
                if d.get(f) not in (None, "", 0): setattr(c, f, d[f])
            cap_nhat.append(c.contract_no)
        c.company_id = tim_cty(k.entity) or c.company_id
        for plate in plates:
            v = xe_map.get(plate)
            if v is None:
                khong_thay_xe.append(plate); continue
            da_co = db.execute(select(Collateral).where(Collateral.contract_id == c.id, Collateral.vehicle_id == v.id,
                                                        Collateral.den_ngay.is_(None))).scalar_one_or_none()
            if da_co is None:
                db.add(Collateral(contract_id=c.id, vehicle_id=v.id, nguon=data.nguon or "Hồ sơ khế ước ngân hàng")); gan_xe += 1
    R.audit(db, u.username, u.role, "nap_ho_so_khe_uoc_vay", "fin:vay-xe",
            after={"tao": tao, "cap_nhat": cap_nhat, "gan_xe": gan_xe, "nguon": data.nguon})
    db.commit()
    return {"tao_moi": tao, "cap_nhat": cap_nhat, "so_xe_gan_the_chap": gan_xe,
            "xe_da_ban_tao_moi": tao_xe, "bien_so_khong_co_trong_danh_muc": khong_thay_xe,
            "message": f"Đã nạp {len(tao)} khế ước mới, cập nhật {len(cap_nhat)} khế ước, gắn {gan_xe} xe vào tài sản bảo đảm"}


class SaoKeDong(BaseModel):
    ke_uoc: str
    du_no: float = 0
    lai_suat: float | None = None
    dao_han: date | None = None
    giai_ngan: date | None = None
    muc_dich: str = ""
    loai: str = ""
    nhom: str = ""      # von_luu_dong / bds / khac → xếp vào "ngoài phạm vi theo dõi vay xe"


class SaoKeIn(BaseModel):
    ngan_hang: str = ""
    phap_nhan: str = ""
    den_ngay: date | None = None
    dong: list[SaoKeDong]


@router.post("/fin/doi-chieu-sao-ke")
def doi_chieu_sao_ke(data: SaoKeIn, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """So sao kê khoản vay của ngân hàng với khế ước đang theo dõi. Chỉ đọc và báo cáo, không sửa dữ liệu."""
    return F.doi_chieu_sao_ke(db, [d.model_dump() for d in data.dong], data.ngan_hang, data.den_ngay, data.phap_nhan)


class CapNhatSauDoiChieuIn(BaseModel):
    ngan_hang: str = ""
    den_ngay: date | None = None
    dong: list[SaoKeDong]


@router.post("/fin/cap-nhat-theo-sao-ke")
def cap_nhat_theo_sao_ke(data: CapNhatSauDoiChieuIn, u: User = Depends(require_roles("ketoan", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Ghi dư nợ / lãi suất / ngày đáo hạn theo sao kê cho những khế ước KHỚP MÃ.

    Chỉ chạm vào khế ước có mã trùng: dòng sao kê lạ không tự tạo khế ước mới, và khế ước không có trên
    sao kê không bị đóng – hai việc đó phải có người quyết định và có xác nhận của ngân hàng.
    """
    loans = {c.contract_no.strip(): c for c in
             db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars()
             if (c.contract_no or "").strip()}
    da_sua, bo_qua = [], []
    for d in data.dong:
        c = loans.get(d.ke_uoc.strip())
        if c is None: bo_qua.append(d.ke_uoc); continue
        thay_doi = {}
        # DOT R6b-1 24/10/2026 - dung LOI THOAT CO Y PHIEN cua `test_k2_doc_an_toan`, khong
        # rac `or 0` vao day. Vi sao dong nay bong bi soi: bo quet doi chieu theo TEN COT, ma
        # dot nay vua them cot tien `du_no` CHO RONG vao tam bang so du dau ky - nen tu nay
        # moi cho doc `.du_no` trong ca kho deu bi soi.
        #
        # Nhung `d` o day KHONG phai mot dong CSDL: no la mo hinh Pydantic khai ngay tren,
        # `du_no: float = 0`, nen o nay khong bao gio rong. Boc `or 0` vao mot cho von khong
        # the rong la them nhieu vao ma cua lan khac ma khong mua duoc gi - dung thu `or 0`
        # dat sai cho ma chinh dau tep phep thu ay canh.
        if d.du_no and abs((c.outstanding or 0) - d.du_no) >= 1:  # k2-doc-an-toan: `d` la mo hinh Pydantic (du_no: float = 0), khong phai cot CSDL
            thay_doi["du_no"] = [c.outstanding, d.du_no]; c.outstanding = d.du_no
        if d.lai_suat is not None and abs(c.interest_rate - d.lai_suat) >= 0.01:
            thay_doi["lai_suat"] = [c.interest_rate, d.lai_suat]; c.interest_rate = d.lai_suat
        if d.dao_han and c.maturity != d.dao_han:
            thay_doi["dao_han"] = [str(c.maturity or ""), str(d.dao_han)]; c.maturity = d.dao_han
        if thay_doi: da_sua.append({"ke_uoc": d.ke_uoc, "thay_doi": thay_doi})
    R.audit(db, u.username, u.role, "cap_nhat_khe_uoc_theo_sao_ke", f"fin:sao-ke:{data.ngan_hang}",
            after={"nguon": f"Sao kê {data.ngan_hang} đến {data.den_ngay}", "so_khe_uoc_sua": len(da_sua), "chi_tiet": da_sua})
    db.commit()
    return {"da_cap_nhat": da_sua, "khong_co_trong_he_thong": bo_qua,
            "message": f"Đã cập nhật {len(da_sua)} khế ước theo sao kê {data.ngan_hang}"}


# ══════════════════════════════════════════════════════════════════════════════
# VPM-11 – SỔ NGHĨA VỤ THANH TOÁN
#
# Đặt trong router NÀY, dưới tiền tố `/fin` đã được cấp, và dùng ĐÚNG danh sách vai trò `READ`/`WRITE`
# đã khai sẵn ở đầu tệp. Mở một nhóm API mới (`/api/v1/nghia-vu`) là xin thêm quyền cho một loạt vai
# trò mà chưa ai ký – lane Viết phần mềm không tự khai quyền.
#
# `READ` ở đây đang là (ketoan, cntt, tgd, chutich, bks): hai Phó Tổng giám đốc KHÔNG có trong danh
# sách, đúng yêu cầu SEC-02 của đề xuất 11/9/2026. Đây là trùng hợp có lợi, không phải do bản vá này
# đặt ra – muốn đổi thì robot Phân quyền đổi ở access.py, không đổi ở đây.
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/fin/nghia-vu")
def so_nghia_vu(company_id: int | None = None, loai_tien: str = "VND",
                u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Tổng hợp sổ nghĩa vụ: cộng theo nhóm trên hai cơ sở ngày, kèm ba rổ không được bỏ im lặng."""
    from app.services import nghia_vu as NV
    return NV.bang(db, company_id=company_id, loai_tien=loai_tien, vai_tro=u.role)


@router.get("/fin/nghia-vu/chi-tiet")
def nghia_vu_chi_tiet(nhom: str | None = None, co_so_ngay: str = "cam_ket",
                      tu: date | None = None, den: date | None = None,
                      company_id: int | None = None, loai_tien: str = "VND",
                      u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách chứng từ đứng sau một con số – mục IV.2 của đề xuất: bấm vào số tiền phải ra tờ giấy."""
    from app.models.nghia_vu import NHOM, TRANG_THAI_DONG, NghiaVuThanhToan
    from app.services import nghia_vu as NV
    if nhom is not None and nhom not in NHOM:
        raise HTTPException(422, f"Không có nhóm nghĩa vụ “{nhom}”")
    if co_so_ngay not in ("cam_ket", "du_kien"):
        raise HTTPException(422, "Cơ sở ngày phải là “cam_ket” hoặc “du_kien” – không trộn hai loại")
    cot = (NghiaVuThanhToan.ngay_cam_ket if co_so_ngay == "cam_ket"
           else NghiaVuThanhToan.ngay_du_kien_tra)
    q = select(NghiaVuThanhToan).where(
        NghiaVuThanhToan.ghi_nho == False,                                   # noqa: E712
        NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG),
        NghiaVuThanhToan.loai_tien == loai_tien)
    # P6 – phạm vi pháp nhân của PHIÊN ĐĂNG NHẬP. Khác hẳn tham số `company_id` phía dưới: tham số
    # là người xem TỰ CHỌN xem pháp nhân nào, hàng rào này là điều họ KHÔNG ĐƯỢC chọn. Thiếu nó thì
    # bỏ tham số đi là thấy cả nhóm — mà bảng dòng tiền là đúng chỗ không được lộ chéo pháp nhân.
    q = PV.loc(q, NghiaVuThanhToan, u)
    # Chốt 11/9: Tổng giám đốc CHỈ xem tài chính hoạt động tour và xe. Lọc theo NHÓM đặt ngay ở đây,
    # cùng một phép lọc mà bảng tổng hợp dùng – không để màn hình tự giấu dòng, vì gọi thẳng đường
    # dẫn này là thấy lại.
    from app.models.nghia_vu import nhom_duoc_xem
    duoc = nhom_duoc_xem(u.role)
    if nhom is not None and nhom not in duoc:
        raise HTTPException(403, f"Vai trò “{u.role}” không xem nhóm “{NHOM[nhom][1]}”")
    q = q.where(NghiaVuThanhToan.nhom.in_(sorted(duoc)))
    if nhom is not None: q = q.where(NghiaVuThanhToan.nhom == nhom)
    if company_id is not None: q = q.where(NghiaVuThanhToan.company_id == company_id)
    if tu is not None: q = q.where(cot.is_not(None), cot >= tu)
    if den is not None: q = q.where(cot.is_not(None), cot <= den)
    ds = [nv for nv in db.execute(q).scalars() if nv.con_lai() > 0]
    ds.sort(key=lambda x: -x.con_lai())
    return {"so_khoan": len(ds), "tong": round(sum(x.con_lai() for x in ds)),
            "co_so_ngay": co_so_ngay, "chi_tiet": [NV.dong(x) for x in ds[:500]]}


# ĐỢT E5 13/10/2026 — các đợt của MỘT nghĩa vụ, cho ô chọn đợt trên màn hình phân bổ tiền ra.
# Nằm dưới tiền tố `/fin` đã khai, và dùng đúng bộ vai READ của màn hình Ngân quỹ.
@router.get("/fin/nghia-vu/{nv_id}/dot")
def dot_cua_nghia_vu(nv_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Đợt nào còn phải trả. Trả cả đợt đã trả đủ, có cờ, để người xem biết đợt ấy đã xong."""
    from app.models.nghia_vu import DotThanhToan
    ds = db.execute(select(DotThanhToan).where(DotThanhToan.nghia_vu_id == nv_id)
                    .order_by(DotThanhToan.so_thu_tu)).scalars().all()
    return [{"id": d.id, "so_thu_tu": d.so_thu_tu, "so_tien": d.so_tien, "da_tra": d.da_tra,
             "con_lai": d.con_lai(), "da_tra_du": d.da_tra_du(),
             "ngay_han": d.ngay_han_suy or d.ngay_han, "can_cu_han": d.can_cu_han} for d in ds]


@router.post("/fin/nghia-vu/dong-bo")
def dong_bo_nghia_vu(u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Dựng lại sổ từ sáu bảng chứng từ gốc. Chạy lại được – gọi nhiều lần không sinh dòng thừa."""
    from app.services import nghia_vu as NV
    kq = NV.dong_bo(db)
    R.audit(db, u.username, u.role, "dong_bo_so_nghia_vu", "nghia_vu", after=kq)
    db.commit()
    return {**kq, "message": f"Đã dựng lại sổ nghĩa vụ – {kq['tong_dong']} dòng"}
