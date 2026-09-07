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
