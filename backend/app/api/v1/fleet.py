"""API nền dữ liệu đội xe Vietrip – Đợt 1 (đặc tả v1.3, 06/9/2026).

Mọi đường ở đây nằm dưới /api/v1/fleet/. Phân hệ Nhân sự đã có sẵn "/api/v1/vehicles" và "/api/v1/fleet/summary"
cho phần bảng lương – không đụng vào, để hai bên không tranh đường. Đường "/api/v1/fleet/summary" cũ vẫn thuộc
router Nhân sự; router này chỉ nhận các đường sâu hơn (/fleet/xe, /fleet/kiem-tra…).

Đổi biển, đổi quyền khai thác và đóng việc xác minh đều đi qua endpoint HÀNH ĐỘNG riêng, không có đường nào
nhận thẳng một cột trạng thái. Lý do: đổi biển không phải sửa một ô chữ, nó phải đóng dòng lịch sử cũ và mở
dòng mới trong cùng một giao dịch – để giữa chừng có lỗi thì không còn chiếc xe nào mang hai biển hiệu lực.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User, Company
from app.models.hr import Vehicle, Employee
from app.models.fleet import (VehiclePlate, VehicleDocument, FleetVerification, LIFECYCLE, OP_RIGHT,
                              DOC_KINDS, VEHICLE_DOCS, DRIVER_DOCS, VERIFY, VERIFY_STATUS)
from app.services import fleet as FL
from app.services import rules as R

router = APIRouter(prefix="/api/v1/fleet", tags=["fleet"])

# Xem hồ sơ đội xe: Vận tải, Điều hành, Ban Giám đốc, Kế toán, BKS, CNTT, HCNS.
READ = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt", "hcns")
# Sửa hồ sơ xe: người phụ trách đội xe và CNTT. Kế toán không sửa hồ sơ xe, BKS chỉ đọc.
WRITE = ("cntt", "hcns", "tp_dh", "nv_dh")


def _chan_khi_thieu_giay(db: Session) -> bool:
    """Tham số chính sách. Mặc định TẮT vì hồ sơ giấy tờ 14 xe chưa nhập; bật lên khi dữ liệu đã đủ."""
    try:
        return bool(R.get_param(db, "xe_chan_khi_thieu_giay"))
    except Exception:
        return False


def _xe_out(db: Session, v: Vehicle, cos: dict, emps: dict, kem_kiem_tra: bool = False) -> dict:
    d = {"id": v.id, "code": v.code, "plate": v.plate, "vin": v.vin, "seats": v.seats, "kind": v.kind,
         "lifecycle": v.lifecycle, "lifecycle_ten": LIFECYCLE.get(v.lifecycle, v.lifecycle),
         "op_right": v.op_right, "op_right_ten": OP_RIGHT.get(v.op_right, v.op_right),
         "owner_company": cos[v.company_id].name if v.company_id in cos else "",
         "operator_company": cos[v.operator_company_id].name if v.operator_company_id in cos else "",
         "partner_name": v.partner_name, "contract_ref": v.contract_ref,
         "contract_from": v.contract_from, "contract_to": v.contract_to,
         "driver": emps.get(v.driver_id, ""), "odo_km": v.odo_km, "odo_at": v.odo_at,
         "active": v.active, "source_note": v.source_note}
    if kem_kiem_tra:
        d["san_sang"] = FL.san_sang(db, v, _chan_khi_thieu_giay(db))
    return d


@router.get("/danh-muc")
def danh_muc(u: User = Depends(require_roles(*READ))):
    return {"lifecycle": LIFECYCLE, "op_right": OP_RIGHT, "giay_xe": VEHICLE_DOCS, "giay_tai_xe": DRIVER_DOCS,
            "muc_do_xac_minh": VERIFY, "trang_thai_xac_minh": VERIFY_STATUS, "muc_kiem_tra": FL.MUC_TEN}


@router.get("/xe")
def danh_sach_xe(kem_kiem_tra: bool = False, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách xe kèm ba trục sở hữu / khai thác / hợp đồng. `kem_kiem_tra` chạy thêm bộ điều kiện cho từng
    xe – nặng hơn, nên mặc định tắt và chỉ bật ở màn hình tổng quan đội xe."""
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    return [_xe_out(db, v, cos, emps, kem_kiem_tra)
            for v in db.execute(select(Vehicle).order_by(Vehicle.code, Vehicle.plate)).scalars()]


@router.get("/xe/{vid}")
def ho_so_xe(vid: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    v = db.get(Vehicle, vid)
    if not v: raise HTTPException(404, "Không có xe")
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    giay = [{"id": d.id, "kind": d.kind, "kind_ten": DOC_KINDS.get(d.kind, d.kind), "number": d.number,
             "issued_on": d.issued_on, "expires_on": d.expires_on, "source": d.source, "verify": d.verify,
             "cho_ai": "xe" if d.vehicle_id else "tai_xe", "note": d.note}
            for d in db.execute(select(VehicleDocument).where(VehicleDocument.active == True,
                                                              VehicleDocument.vehicle_id == vid)).scalars()]
    if v.driver_id:
        giay += [{"id": d.id, "kind": d.kind, "kind_ten": DOC_KINDS.get(d.kind, d.kind), "number": d.number,
                  "issued_on": d.issued_on, "expires_on": d.expires_on, "source": d.source, "verify": d.verify,
                  "cho_ai": "tai_xe", "note": d.note}
                 for d in db.execute(select(VehicleDocument).where(VehicleDocument.active == True,
                                                                   VehicleDocument.employee_id == v.driver_id)).scalars()]
    xm = [{"id": x.id, "issue": x.issue, "status": x.status, "source": x.source, "created_at": x.created_at}
          for x in db.execute(select(FleetVerification).where(FleetVerification.vehicle_id == vid)).scalars()]
    return {**_xe_out(db, v, cos, emps, kem_kiem_tra=True), "lich_su_bien": FL.bien_hien_hanh(db, vid),
            "giay_to": giay, "viec_xac_minh": xm}


class HoSoXeIn(BaseModel):
    code: str | None = None
    vin: str | None = None
    seats: int | None = None
    lifecycle: str | None = None
    op_right: str | None = None
    company_id: int | None = None
    operator_company_id: int | None = None
    partner_name: str | None = None
    contract_ref: str | None = None
    contract_from: date | None = None
    contract_to: date | None = None
    odo_km: int | None = None
    odo_at: date | None = None
    source_note: str | None = None


@router.put("/xe/{vid}")
def cap_nhat_ho_so(vid: int, data: HoSoXeIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Sửa hồ sơ xe – KHÔNG nhận biển số ở đây. Đổi biển đi qua /xe/{id}/doi-bien để lịch sử được ghi."""
    v = db.get(Vehicle, vid)
    if not v: raise HTTPException(404, "Không có xe")
    d = data.model_dump(exclude_unset=True)
    if "lifecycle" in d and d["lifecycle"] not in LIFECYCLE:
        raise HTTPException(422, f"Vòng đời không hợp lệ. Chỉ nhận {', '.join(LIFECYCLE)}")
    if "op_right" in d and d["op_right"] not in OP_RIGHT:
        raise HTTPException(422, f"Quyền khai thác không hợp lệ. Chỉ nhận {', '.join(OP_RIGHT)}")
    if d.get("code"):
        trung = db.execute(select(Vehicle).where(Vehicle.code == d["code"], Vehicle.id != vid)).scalars().first()
        if trung: raise HTTPException(422, f"Mã xe {d['code']} đã dùng cho xe {trung.plate}")
    before = {k: getattr(v, k) for k in d}
    for k, val in d.items(): setattr(v, k, val)
    R.audit(db, u.username, u.role, "sua_ho_so_doi_xe", f"vehicle:{v.code or v.plate}",
            before={k: str(x) for k, x in before.items()}, after=data.model_dump(mode="json", exclude_unset=True))
    db.commit()
    return {"message": f"Đã cập nhật hồ sơ xe {v.plate}"}


class DoiBienIn(BaseModel):
    plate: str
    from_date: date
    source: str = ""
    note: str = ""


@router.post("/xe/{vid}/doi-bien", status_code=201)
def doi_bien(vid: int, data: DoiBienIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Đổi biển số trên CÙNG một xe. Đây là lý do tồn tại của Đợt 1: trước đây đổi biển nghĩa là tạo xe mới,
    và lịch sử chuyến của chiếc xe bị chẻ làm đôi."""
    v = db.get(Vehicle, vid)
    if not v: raise HTTPException(404, "Không có xe")
    moi = (data.plate or "").strip().upper()
    if not moi: raise HTTPException(422, "Thiếu biển số mới")
    if moi == (v.plate or "").upper(): raise HTTPException(422, "Biển số mới trùng biển đang dùng")
    khac = db.execute(select(Vehicle).where(Vehicle.plate == moi, Vehicle.id != vid)).scalars().first()
    if khac:
        raise HTTPException(422, f"Biển {moi} đang gắn cho xe khác (mã {khac.code or khac.id}). "
                                 "Nếu đây là cùng một chiếc xe thì gộp hồ sơ, đừng tạo bản ghi thứ hai.")
    cu = v.plate
    FL.doi_bien(db, v, moi, data.from_date, data.source, u.username)
    R.audit(db, u.username, u.role, "doi_bien_so_xe", f"vehicle:{v.code or v.id}",
            before={"bien": cu}, after={"bien": moi, "tu_ngay": str(data.from_date), "nguon": data.source})
    db.commit()
    return {"message": f"Đã ghi nhận xe {v.code or v.id} đổi biển {cu} → {moi} từ {data.from_date:%d/%m/%Y}",
            "lich_su_bien": FL.bien_hien_hanh(db, vid)}


class GiayToIn(BaseModel):
    kind: str
    vehicle_id: int | None = None
    employee_id: int | None = None
    number: str = ""
    issued_on: date | None = None
    expires_on: date | None = None
    source: str = ""
    verify: str = "nguon_ghi"
    note: str = ""


@router.post("/giay-to", status_code=201)
def them_giay_to(data: GiayToIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Thêm giấy tờ có hạn. Giấy cùng loại của cùng chủ thể sẽ được đánh dấu hết hiệu lực chứ không bị xóa –
    lịch sử gia hạn là bằng chứng khi có tranh chấp."""
    if data.kind not in DOC_KINDS: raise HTTPException(422, f"Loại giấy không hợp lệ. Chỉ nhận {', '.join(DOC_KINDS)}")
    if data.verify not in VERIFY: raise HTTPException(422, f"Mức xác minh không hợp lệ. Chỉ nhận {', '.join(VERIFY)}")
    if bool(data.vehicle_id) == bool(data.employee_id):
        raise HTTPException(422, "Giấy phải thuộc ĐÚNG một chủ thể: xe hoặc tài xế")
    if data.vehicle_id and data.kind not in VEHICLE_DOCS: raise HTTPException(422, f"{data.kind} là giấy của người, không phải của xe")
    if data.employee_id and data.kind not in DRIVER_DOCS: raise HTTPException(422, f"{data.kind} là giấy của xe, không phải của người")
    if data.vehicle_id and not db.get(Vehicle, data.vehicle_id): raise HTTPException(404, "Không có xe")
    if data.employee_id and not db.get(Employee, data.employee_id): raise HTTPException(404, "Không có nhân sự")
    q = select(VehicleDocument).where(VehicleDocument.kind == data.kind, VehicleDocument.active == True)
    q = q.where(VehicleDocument.vehicle_id == data.vehicle_id) if data.vehicle_id else q.where(VehicleDocument.employee_id == data.employee_id)
    for cu in db.execute(q).scalars(): cu.active = False
    d = VehicleDocument(**data.model_dump(), created_by=u.username)
    db.add(d); db.flush()
    R.audit(db, u.username, u.role, "them_giay_to_doi_xe", f"vehicle:{data.vehicle_id or ''}emp:{data.employee_id or ''}",
            after=data.model_dump(mode="json"))
    db.commit()
    return {"message": f"Đã ghi {DOC_KINDS[data.kind]}" + (f", hết hạn {data.expires_on:%d/%m/%Y}" if data.expires_on
                                                            else " – CHƯA có ngày hết hạn nên hệ thống không kết luận còn hạn")}


@router.get("/kiem-tra")
def kiem_tra(vehicle_id: int, date_from: date, date_to: date, driver_id: int | None = None,
             u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Chạy thử bộ điều kiện phát lệnh cho một phương án – không tạo lệnh, không ghi gì."""
    if date_to < date_from: raise HTTPException(422, "Ngày kết thúc trước ngày bắt đầu")
    v = db.get(Vehicle, vehicle_id)
    if not v: raise HTTPException(404, "Không có xe")
    return FL.kiem_tra_dieu_xe(db, v, date_from, date_to, driver_id, chan_khi_thieu_giay=_chan_khi_thieu_giay(db))


@router.get("/tong-quan")
def tong_quan(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Tổng quan đội xe. Đặc tả yêu cầu rõ: số xe SẴN SÀNG không mặc định bằng tổng số xe, và phải tách được
    xe sở hữu với xe hợp tác. Nên ở đây trả về từng nhóm chứ không phải một con số đẹp."""
    chan = _chan_khi_thieu_giay(db)
    nhom = {"so_huu": 0, "hop_tac": 0, "thue": 0, "khong": 0}
    muc = {FL.OK: 0, FL.UNKNOWN: 0, FL.REVIEW: 0, FL.APPROVAL: 0, FL.BLOCK: 0}
    ds = []
    for v in db.execute(select(Vehicle)).scalars():
        nhom[v.op_right] = nhom.get(v.op_right, 0) + 1
        s = FL.san_sang(db, v, chan)
        muc[s["muc"]] = muc.get(s["muc"], 0) + 1
        ds.append({"id": v.id, "code": v.code, "plate": v.plate, "op_right": v.op_right,
                   "lifecycle": v.lifecycle, "muc": s["muc"], "ly_do": s["ly_do"]})
    cho_xm = db.execute(select(FleetVerification).where(FleetVerification.status.in_(["cho_xac_minh", "dang_xu_ly"]))).scalars().all()
    return {"tong_so_xe": len(ds), "theo_quyen_khai_thac": nhom, "theo_muc_kiem_tra": muc,
            "san_sang": muc.get(FL.OK, 0), "chua_du_du_lieu": muc.get(FL.UNKNOWN, 0), "bi_chan": muc.get(FL.BLOCK, 0),
            "viec_xac_minh_dang_mo": len(cho_xm), "chan_khi_thieu_giay": chan, "xe": ds,
            "ghi_chu": "Số xe sẵn sàng chỉ đếm xe đã đủ hồ sơ và qua kiểm tra. Xe ở mức 'Chưa đủ dữ liệu' "
                       "không được cộng vào sẵn sàng – thiếu dữ liệu không phải là đạt."}


class ViecXacMinhIn(BaseModel):
    entity: str = "vehicle"
    ref: str = ""
    vehicle_id: int | None = None
    issue: str
    source: str = ""


@router.get("/xac-minh")
def hang_doi(status: str = "", u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    if status and status not in VERIFY_STATUS:
        raise HTTPException(422, f"Trạng thái không hợp lệ. Chỉ nhận {', '.join(VERIFY_STATUS)}")
    q = select(FleetVerification).order_by(FleetVerification.status, FleetVerification.id)
    if status: q = q.where(FleetVerification.status == status)
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    return [{"id": x.id, "entity": x.entity, "ref": x.ref or veh.get(x.vehicle_id, ""), "issue": x.issue,
             "source": x.source, "status": x.status, "status_ten": VERIFY_STATUS.get(x.status, x.status),
             "resolution": x.resolution, "created_at": x.created_at, "resolved_at": x.resolved_at,
             "resolved_by": x.resolved_by} for x in db.execute(q).scalars()]


@router.post("/xac-minh", status_code=201)
def them_viec(data: ViecXacMinhIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    x = FleetVerification(**data.model_dump())
    db.add(x); db.flush()
    R.audit(db, u.username, u.role, "them_viec_xac_minh_doi_xe", f"fleet_verify:{x.id}", after=data.model_dump(mode="json"))
    db.commit()
    return {"id": x.id, "message": "Đã thêm việc xác minh vào hàng đợi"}


class KetLuanIn(BaseModel):
    status: str
    resolution: str


@router.post("/xac-minh/{xid}/ket-luan")
def ket_luan(xid: int, data: KetLuanIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Đóng một việc xác minh. Bắt buộc có kết luận bằng chữ: đóng mà không ghi lý do thì lần sau không ai
    biết chuyện đã được xử lý thế nào, và việc lại được mở ra lần nữa."""
    x = db.get(FleetVerification, xid)
    if not x: raise HTTPException(404, "Không có việc xác minh")
    if data.status not in VERIFY_STATUS: raise HTTPException(422, f"Trạng thái không hợp lệ. Chỉ nhận {', '.join(VERIFY_STATUS)}")
    if data.status in ("xong", "khong_ap_dung") and not (data.resolution or "").strip():
        raise HTTPException(422, "Phải ghi kết luận khi đóng việc xác minh")
    from datetime import datetime as _dt
    x.status = data.status; x.resolution = data.resolution
    if data.status in ("xong", "khong_ap_dung"):
        x.resolved_at = _dt.now(); x.resolved_by = u.username
    R.audit(db, u.username, u.role, "ket_luan_xac_minh_doi_xe", f"fleet_verify:{x.id}", after=data.model_dump(mode="json"))
    db.commit()
    return {"message": "Đã cập nhật việc xác minh"}


# ====================== ĐỢT 2: NHẬT TRÌNH, BẢO DƯỠNG, NGUỒN NGOÀI ======================
from app.models.fleet import (Trip, TripCost, Maintenance, ExternalTxn, BEN_CHIU, COST_KINDS,
                              BEN_CHIU_MAC_DINH, TRIP_STATUS, CO, MAINT_KINDS)

KETOAN = ("ketoan",)


@router.get("/danh-muc-dot2")
def danh_muc_dot2(u: User = Depends(require_roles(*READ))):
    return {"ben_chiu": BEN_CHIU, "loai_chi_phi": COST_KINDS, "ben_chiu_mac_dinh": BEN_CHIU_MAC_DINH,
            "trang_thai_chuyen": TRIP_STATUS, "co": CO, "loai_bao_duong": MAINT_KINDS,
            "ghi_chu": "Chốt 07/9/2026: Vietourist tạm ứng nhiên liệu, cầu đường, công tác phí, bãi xe. "
                       "KHÔNG tạm ứng sửa chữa – chủ xe tự chịu, và không tự trừ vào công nợ nếu chưa có "
                       "văn bản đồng ý của chủ xe."}


class ChuyenIn(BaseModel):
    vehicle_id: int
    driver_id: int | None = None
    dispatch_id: int | None = None
    tour_id: int | None = None
    ten_tour: str = ""
    ngay_di: date
    ngay_ve: date
    km_dau: int | None = None
    km_cuoi: int | None = None
    km_gps: int | None = None
    km_nguon: str = "nhap_tay"
    doanh_thu: float = 0
    note: str = ""


def _chuyen_out(db: Session, t: Trip, veh: dict, emps: dict) -> dict:
    cps = list(db.execute(select(TripCost).where(TripCost.trip_id == t.id)).scalars())
    return {"id": t.id, "vehicle_id": t.vehicle_id, "xe": veh.get(t.vehicle_id, ""),
            "tai_xe": emps.get(t.driver_id, ""), "ten_tour": t.ten_tour, "ngay_di": t.ngay_di,
            "ngay_ve": t.ngay_ve, "so_ngay": (t.ngay_ve - t.ngay_di).days + 1,
            "km_dau": t.km_dau, "km_cuoi": t.km_cuoi, "km_gps": t.km_gps,
            "km_chay": (t.km_cuoi - t.km_dau) if (t.km_dau is not None and t.km_cuoi is not None) else None,
            "doanh_thu": t.doanh_thu, "status": t.status, "co": t.co, "co_ly_do": t.co_ly_do,
            "chi_phi": [{"id": c.id, "kind": c.kind, "kind_ten": COST_KINDS.get(c.kind, c.kind),
                         "amount": c.amount, "lit": c.lit, "ben_chiu": c.ben_chiu,
                         "ben_chiu_ten": BEN_CHIU.get(c.ben_chiu, c.ben_chiu), "chung_tu": c.chung_tu,
                         "nguon": c.nguon} for c in cps],
            "tong_chi_vietourist": sum(c.amount for c in cps if c.ben_chiu == "vietourist_tam_ung"),
            "tong_chi_chu_xe": sum(c.amount for c in cps if c.ben_chiu == "chu_xe")}


@router.get("/chuyen")
def danh_sach_chuyen(vehicle_id: int | None = None, tu: date | None = None, den: date | None = None,
                     u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(Trip).order_by(Trip.ngay_di.desc(), Trip.id.desc())
    if vehicle_id: q = q.where(Trip.vehicle_id == vehicle_id)
    # Chuyến được gán vào kỳ theo NGÀY KHỞI HÀNH (đề nghị trong tài liệu 07/9 cho chuyến vắt qua hai tháng).
    if tu: q = q.where(Trip.ngay_di >= tu)
    if den: q = q.where(Trip.ngay_di <= den)
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    return [_chuyen_out(db, t, veh, emps) for t in db.execute(q.limit(500)).scalars()]


@router.post("/chuyen", status_code=201)
def tao_chuyen(data: ChuyenIn, u: User = Depends(require_roles(*WRITE, *KETOAN)), db: Session = Depends(get_db)):
    """Nhật trình chuyến. Km đầu/cuối để trống nghĩa là CHƯA ĐO, không phải bằng 0 – nên hệ thống không tự
    điền 0 và không tính ra quãng đường âm."""
    v = db.get(Vehicle, data.vehicle_id)
    if not v: raise HTTPException(404, "Không có xe")
    if data.ngay_ve < data.ngay_di: raise HTTPException(422, "Ngày về trước ngày đi")
    if data.km_dau is not None and data.km_cuoi is not None and data.km_cuoi < data.km_dau:
        raise HTTPException(422, "Km cuối nhỏ hơn km đầu – kiểm tra lại số đọc trên đồng hồ")
    t = Trip(**data.model_dump(), created_by=u.username)
    db.add(t); db.flush()
    kt = FL.kiem_chuyen(db, t)
    t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    R.audit(db, u.username, u.role, "nhat_trinh_chuyen", f"vehicle:{v.code or v.plate}",
            after={**data.model_dump(mode="json"), "co": t.co})
    db.commit()
    return {"id": t.id, "co": kt["co"], "ly_do": kt["ly_do"],
            "message": f"Đã ghi nhật trình chuyến của xe {v.plate}"}


class ChiPhiIn(BaseModel):
    kind: str
    amount: float
    ben_chiu: str | None = None
    lit: float = 0
    chung_tu: str = ""
    nguon: str = "nhap_tay"
    note: str = ""


@router.post("/chuyen/{tid}/chi-phi", status_code=201)
def them_chi_phi(tid: int, data: ChiPhiIn, u: User = Depends(require_roles(*WRITE, *KETOAN)), db: Session = Depends(get_db)):
    """Thêm một dòng chi phí. `ben_chiu` không truyền thì lấy mặc định theo loại chi phí – sửa chữa mặc định
    là CHỦ XE theo quy tắc chốt 07/9/2026."""
    t = db.get(Trip, tid)
    if not t: raise HTTPException(404, "Không có chuyến")
    if t.status == "da_xac_nhan": raise HTTPException(422, "Chuyến đã xác nhận – sửa phải qua điều chỉnh, không ghi đè")
    if data.kind not in COST_KINDS: raise HTTPException(422, f"Loại chi phí không hợp lệ. Chỉ nhận {', '.join(COST_KINDS)}")
    bc = data.ben_chiu or BEN_CHIU_MAC_DINH.get(data.kind, "vietourist_tam_ung")
    if bc not in BEN_CHIU: raise HTTPException(422, f"Bên chịu không hợp lệ. Chỉ nhận {', '.join(BEN_CHIU)}")
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if data.amount >= nguong and not (data.chung_tu or "").strip():
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc có chứng từ gốc đính kèm (chặn cứng B6)")
    c = TripCost(trip_id=tid, **{**data.model_dump(exclude={"ben_chiu"}), "ben_chiu": bc}, created_by=u.username)
    db.add(c); db.flush()
    kt = FL.kiem_chuyen(db, t); t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    R.audit(db, u.username, u.role, "chi_phi_chuyen", f"trip:{tid}", after={**data.model_dump(mode="json"), "ben_chiu": bc})
    db.commit()
    return {"id": c.id, "ben_chiu": bc, "co_chuyen": kt["co"],
            "message": f"Đã ghi {COST_KINDS[data.kind]} – {BEN_CHIU[bc]}"}


@router.post("/chuyen/{tid}/xac-nhan")
def xac_nhan_chuyen(tid: int, u: User = Depends(require_roles("cntt", "tp_dh", "nv_dh")), db: Session = Depends(get_db)):
    t = db.get(Trip, tid)
    if not t: raise HTTPException(404, "Không có chuyến")
    kt = FL.kiem_chuyen(db, t)
    if kt["co"] == "do":
        raise HTTPException(422, {"message": "Chuyến còn cờ đỏ – không xác nhận được", "ly_do": kt["ly_do"]})
    from datetime import datetime as _dt
    t.status = "da_xac_nhan"; t.confirmed_at = _dt.now(); t.confirmed_by = u.username
    t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    R.audit(db, u.username, u.role, "xac_nhan_chuyen", f"trip:{tid}", after={"co": kt["co"]})
    db.commit()
    return {"message": "Đã xác nhận chuyến", "co": kt["co"], "ly_do": kt["ly_do"]}


class BaoDuongIn(BaseModel):
    vehicle_id: int
    ngay: date
    kind: str = "dinh_ky"
    km_luc_lam: int | None = None
    km_ky_toi: int | None = None
    noi_dung: str = ""
    garage: str = ""
    so_tien: float = 0
    ben_chiu: str | None = None
    chung_tu: str = ""


@router.get("/bao-duong")
def ds_bao_duong(vehicle_id: int | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(Maintenance).order_by(Maintenance.ngay.desc(), Maintenance.id.desc())
    if vehicle_id: q = q.where(Maintenance.vehicle_id == vehicle_id)
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    return [{"id": m.id, "xe": veh.get(m.vehicle_id, ""), "vehicle_id": m.vehicle_id, "ngay": m.ngay,
             "kind": m.kind, "kind_ten": MAINT_KINDS.get(m.kind, m.kind), "km_luc_lam": m.km_luc_lam,
             "km_ky_toi": m.km_ky_toi, "noi_dung": m.noi_dung, "garage": m.garage, "so_tien": m.so_tien,
             "ben_chiu": m.ben_chiu, "ben_chiu_ten": BEN_CHIU.get(m.ben_chiu, m.ben_chiu),
             "chung_tu": m.chung_tu} for m in db.execute(q.limit(500)).scalars()]


@router.post("/bao-duong", status_code=201)
def them_bao_duong(data: BaoDuongIn, u: User = Depends(require_roles(*WRITE, *KETOAN)), db: Session = Depends(get_db)):
    """Ghi bảo dưỡng/sửa chữa. Không có số km lúc làm thì hệ thống nói thẳng là không tính được mốc kỳ tới,
    thay vì im lặng suy ra từ chu kỳ chung – đó là cách chi phí bị ghi sai kỳ mà không ai phát hiện."""
    v = db.get(Vehicle, data.vehicle_id)
    if not v: raise HTTPException(404, "Không có xe")
    if data.kind not in MAINT_KINDS: raise HTTPException(422, f"Loại không hợp lệ. Chỉ nhận {', '.join(MAINT_KINDS)}")
    bc = data.ben_chiu or ("chu_xe" if v.op_right == "hop_tac" else "vietourist_tam_ung")
    if bc not in BEN_CHIU: raise HTTPException(422, f"Bên chịu không hợp lệ. Chỉ nhận {', '.join(BEN_CHIU)}")
    # Mốc km ghi trên phiếu nhỏ hơn số km đồng hồ đã xác nhận là dấu hiệu ghi sai ngày hoặc sai kỳ –
    # đúng kiểu sai đã xảy ra với xe 50H-496.23 tháng 8/2026 (mốc 130.300 lớn hơn km cuối 130.245).
    canh_bao = []
    if data.km_luc_lam and v.odo_km and data.km_luc_lam > v.odo_km:
        canh_bao.append(f"Km lúc làm ({data.km_luc_lam:,}) lớn hơn km đồng hồ đã xác nhận của xe ({v.odo_km:,}) "
                        "– kiểm tra lại ngày thực hiện và kỳ phân bổ")
    m = Maintenance(**{**data.model_dump(exclude={"ben_chiu"}), "ben_chiu": bc}, created_by=u.username)
    db.add(m); db.flush()
    R.audit(db, u.username, u.role, "bao_duong_xe", f"vehicle:{v.code or v.plate}",
            after={**data.model_dump(mode="json"), "ben_chiu": bc})
    db.commit()
    return {"id": m.id, "ben_chiu": bc, "canh_bao": canh_bao,
            "moc_ky_toi": FL.moc_bao_duong(db, v),
            "message": f"Đã ghi {MAINT_KINDS[data.kind].lower()} cho xe {v.plate}"}


class GiaoDichIn(BaseModel):
    source: str                      # the_dau / epass
    rows: list[dict]


@router.post("/giao-dich/nhap", status_code=201)
def nhap_giao_dich(data: GiaoDichIn, u: User = Depends(require_roles(*WRITE, *KETOAN)), db: Session = Depends(get_db)):
    """Nhập sao kê thẻ dầu hoặc báo cáo ePass. Khử trùng theo mã giao dịch gốc.

    Nghiệm thu của đặc tả: nhập lại CÙNG một file hai lần không sinh bản ghi trùng. Bản ghi lặp vẫn được giữ
    trong bảng thô với cờ trùng để còn chứng minh mình đã loại đúng cái gì."""
    if data.source not in ("the_dau", "epass"): raise HTTPException(422, "Nguồn chỉ nhận the_dau hoặc epass")
    if not data.rows: raise HTTPException(422, "Không có dòng nào để nhập")
    try:
        kq = FL.nhap_giao_dich(db, data.source, data.rows, u.username)
    except (ValueError, TypeError) as ex:
        raise HTTPException(422, f"Dữ liệu nguồn không đọc được: {ex}")
    R.audit(db, u.username, u.role, "nhap_giao_dich_doi_xe", f"nguon:{data.source}", after=kq)
    db.commit()
    return kq


@router.get("/giao-dich")
def ds_giao_dich(source: str = "", chua_khop: bool = False, gom_ban_trung: bool = False,
                 u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(ExternalTxn).order_by(ExternalTxn.thoi_diem.desc(), ExternalTxn.id.desc())
    if source: q = q.where(ExternalTxn.source == source)
    if not gom_ban_trung: q = q.where(ExternalTxn.trung == False)   # mặc định KHÔNG hiện bản lặp
    if chua_khop: q = q.where(ExternalTxn.khop == "chua_khop")
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    rows = list(db.execute(q.limit(1000)).scalars())
    return {"rows": [{"id": t.id, "source": t.source, "ma_gd": t.ma_gd, "thoi_diem": t.thoi_diem,
                      "bien_so": t.bien_so, "the_4so": t.the_4so, "xe": veh.get(t.vehicle_id, ""),
                      "vehicle_id": t.vehicle_id, "so_tien": t.so_tien, "lit": t.lit, "khop": t.khop,
                      "co": t.co, "trung": t.trung, "ghi_chu": t.ghi_chu} for t in rows],
            "tong_tien": sum(t.so_tien for t in rows),
            "ghi_chu": "Số liệu này đã loại bản ghi lặp. Thêm gom_ban_trung=true để xem cả bản đã loại."}
