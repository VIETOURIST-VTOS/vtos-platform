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
from sqlalchemy import select, func
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
# "gd_doi_xe" mở 07/9/2026: Giám đốc điều hành đội xe phải đọc và ghi được chính phân hệ mình phụ trách.
# Trước đó ông mang chung vai trò với tài xế nên bị khoá ngoài, trong khi tham số xe_nguoi_lap_lenh lại chỉ
# định ông là người DUY NHẤT được lập lệnh điều xe – kết quả là không ai lập được lệnh.
READ = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt", "hcns", "gd_doi_xe")
# Sửa hồ sơ xe: người phụ trách đội xe và CNTT. Kế toán không sửa hồ sơ xe, BKS chỉ đọc.
WRITE = ("cntt", "hcns", "tp_dh", "nv_dh", "gd_doi_xe")


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
    phien_ban: int | None = None      # VPM-8 – bản màn hình đang cầm
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
    pb = d.pop("phien_ban", None)
    before = {k: getattr(v, k) for k in d}
    from app.services import ghi_mot_lan as GML
    GML.kiem_phien_ban(v, pb, f"Hồ sơ xe {v.code or v.plate}", lambda: {**before, "phien_ban": v.phien_ban})
    for k, val in d.items(): setattr(v, k, val)
    GML.tang_phien_ban(v)
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
    # ĐẾM ĐỦ NĂM MỨC, và tự kiểm tổng. Trước 07/10/2026 cửa này chỉ in ba mức (OK, UNKNOWN, BLOCK)
    # trong khi `san_sang()` trả về năm, nên xe ở mức REVIEW hay APPROVAL biến mất khỏi mọi ô đếm.
    # Đo trên hệ thật hôm ấy: 16 xe = 0 sẵn sàng + 0 chưa đủ dữ liệu + 5 chặn, và 11 chiếc không ở
    # đâu cả. Một ô đếm cộng không đủ tổng là một ô đếm nói sai, và nó nói sai một cách êm ái: không
    # báo lỗi, không hiện màu, chỉ thiếu.
    #
    # `thieu_trong_o_dem` là phần tự khai: nếu một ngày có người thêm mức thứ sáu mà quên thêm ô đếm,
    # con số này khác 0 và phép thử đỏ, thay vì lại mười một chiếc xe lặng lẽ rơi ra ngoài.
    theo_muc_day_du = {k: muc.get(k, 0) for k in FL.NANG}
    da_dem = sum(theo_muc_day_du.values())
    return {"tong_so_xe": len(ds), "theo_quyen_khai_thac": nhom, "theo_muc_kiem_tra": muc,
            "theo_muc_day_du": [{"muc": k, "ten": FL.MUC_TEN[k], "so_xe": theo_muc_day_du[k],
                                 "nang": FL.NANG[k]}
                                for k in sorted(theo_muc_day_du, key=lambda x: -FL.NANG[x])],
            "thieu_trong_o_dem": len(ds) - da_dem,
            "san_sang": muc.get(FL.OK, 0), "chua_du_du_lieu": muc.get(FL.UNKNOWN, 0), "bi_chan": muc.get(FL.BLOCK, 0),
            "can_xem_lai": muc.get(FL.REVIEW, 0), "can_duyet_ngoai_le": muc.get(FL.APPROVAL, 0),
            "viec_xac_minh_dang_mo": len(cho_xm), "chan_khi_thieu_giay": chan, "xe": ds,
            "ghi_chu": "Số xe sẵn sàng chỉ đếm xe đã đủ hồ sơ và qua kiểm tra. Xe ở mức 'Chưa đủ dữ liệu' "
                       "không được cộng vào sẵn sàng – thiếu dữ liệu không phải là đạt. Năm mức cộng lại "
                       "phải bằng tổng số xe; lệch là có mức bị bỏ khỏi ô đếm."}


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
from app.models.fleet import (Trip, TripCost, Maintenance, ExternalTxn, BEN_CHIU, COST_KINDS, NGUON_NGOAI,
                              BEN_CHIU_MAC_DINH, TRIP_STATUS, CO, MAINT_KINDS, VI_EPASS, KM_NGUON,
                              NGA_CHI_PHI, NGA_CUA_DOI_XE)

KETOAN = ("ketoan",)


def _mac_dinh_ben_chiu(db: Session, kind: str) -> str:
    """Bên chịu mặc định của một loại chi phí. Sửa chữa đọc từ tham số nên đổi điều khoản hợp đồng là đổi
    tham số, không phải sửa mã. Tham số ghi sai giá trị thì quay về mặc định trong mã chứ không ném lỗi
    giữa lúc người ta đang nhập chi phí."""
    if kind != "sua_chua":
        return BEN_CHIU_MAC_DINH.get(kind, "vietourist_tam_ung")
    v = (R.get_param_text(db, "xe_sua_chua_ben_chiu") or "").strip()
    return v if v in BEN_CHIU else BEN_CHIU_MAC_DINH["sua_chua"]


@router.get("/danh-muc-dot2")
def danh_muc_dot2(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    sc = _mac_dinh_ben_chiu(db, "sua_chua")
    return {"ben_chiu": BEN_CHIU, "loai_chi_phi": COST_KINDS,
            "ben_chiu_mac_dinh": {**BEN_CHIU_MAC_DINH, "sua_chua": sc},
            "trang_thai_chuyen": TRIP_STATUS, "co": CO, "loai_bao_duong": MAINT_KINDS,
            # Hai bảng khai báo mới 07/10/2026. Mở ra ở đây để màn hình dựng ô chọn từ MỘT nguồn, không
            # gõ lại danh sách trong TypeScript – gõ lại là ngày nào đó hai bên lệch nhau mà không ai biết.
            "km_nguon": KM_NGUON, "vi_epass": VI_EPASS,
            "nga_chi_phi": NGA_CHI_PHI, "nga_cua_doi_xe": list(NGA_CUA_DOI_XE),
            "ghi_chu": "Chốt 07/9/2026: Vietourist tạm ứng nhiên liệu, cầu đường, công tác phí, bãi xe. "
                       f"Sửa chữa hiện đặt là \"{BEN_CHIU[sc]}\" (chủ tịch chốt lại cuối ngày 07/9/2026: giữ "
                       "cách chi hộ rồi cấn trừ). Khoản chi hộ vẫn phải có chứng từ và có căn cứ đồng ý của "
                       "chủ xe lưu trong hồ sơ."}


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
    doanh_thu: float | None = None
    note: str = ""


def _chuyen_out(db: Session, t: Trip, veh: dict, emps: dict) -> dict:
    cps = list(db.execute(select(TripCost).where(TripCost.trip_id == t.id)).scalars())
    return {"id": t.id, "vehicle_id": t.vehicle_id, "xe": veh.get(t.vehicle_id, ""),
            "tai_xe": emps.get(t.driver_id, ""), "ten_tour": t.ten_tour, "ngay_di": t.ngay_di,
            "ngay_ve": t.ngay_ve, "so_ngay": (t.ngay_ve - t.ngay_di).days + 1,
            "km_dau": t.km_dau, "km_cuoi": t.km_cuoi, "km_gps": t.km_gps,
            "km_nguon": t.km_nguon, "km_nguon_ten": KM_NGUON.get(t.km_nguon, t.km_nguon or ""),
            "km_lech_gps": (abs((t.km_cuoi - t.km_dau) - t.km_gps) if
                            (t.km_dau is not None and t.km_cuoi is not None and t.km_gps) else None),
            "km_chay": (t.km_cuoi - t.km_dau) if (t.km_dau is not None and t.km_cuoi is not None) else None,
            "doanh_thu": t.doanh_thu, "status": t.status, "co": t.co, "co_ly_do": t.co_ly_do,
            "note": t.note, "ma_phieu": t.ma_phieu, "nguon": t.nguon,
            "chi_phi": [{"id": c.id, "kind": c.kind, "kind_ten": COST_KINDS.get(c.kind, c.kind),
                         "amount": c.amount, "lit": c.lit, "ben_chiu": c.ben_chiu,
                         "ben_chiu_ten": BEN_CHIU.get(c.ben_chiu, c.ben_chiu), "chung_tu": c.chung_tu,
                         "nguon": c.nguon} for c in cps],
            "tong_chi_vietourist": sum((c.amount or 0) for c in cps if c.ben_chiu == "vietourist_tam_ung"),
            "tong_chi_chu_xe": sum((c.amount or 0) for c in cps if c.ben_chiu == "chu_xe")}


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
    if data.km_nguon and data.km_nguon not in KM_NGUON:
        raise HTTPException(422, f"Nguồn số km '{data.km_nguon}' không có trong danh mục. "
                                 f"Chỉ nhận: {', '.join(KM_NGUON)}")
    # Số GPS mà không nói lấy từ cổng nào thì sau này không đối chất được với bên nào. Ba cổng đang dùng:
    # TTC, TCD, Vietmap (Chủ tịch cho biết 07/10/2026) – khai đủ trong KM_NGUON.
    if data.km_gps and not data.km_nguon:
        raise HTTPException(422, "Có số km theo GPS nhưng chưa ghi nguồn số km – chọn cổng GPS đã lấy số "
                                 "(gps_ttc / gps_tcd / gps_vietmap) hoặc nguồn của số đồng hồ")
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
    """Thêm một dòng chi phí. `ben_chiu` không truyền thì lấy mặc định theo loại chi phí; riêng sửa chữa đọc
    từ tham số `xe_sua_chua_ben_chiu` (mặc định Vietourist chi hộ – chủ tịch chốt lại cuối ngày 07/9/2026)."""
    t = db.get(Trip, tid)
    if not t: raise HTTPException(404, "Không có chuyến")
    if t.status == "da_xac_nhan": raise HTTPException(422, "Chuyến đã xác nhận – sửa phải qua điều chỉnh, không ghi đè")
    if data.kind not in COST_KINDS: raise HTTPException(422, f"Loại chi phí không hợp lệ. Chỉ nhận {', '.join(COST_KINDS)}")
    bc = data.ben_chiu or _mac_dinh_ben_chiu(db, data.kind)
    if bc not in BEN_CHIU: raise HTTPException(422, f"Bên chịu không hợp lệ. Chỉ nhận {', '.join(BEN_CHIU)}")
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if (data.amount or 0) >= nguong and not (data.chung_tu or "").strip():
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc có chứng từ gốc đính kèm (chặn cứng B6)")
    c = TripCost(trip_id=tid, **{**data.model_dump(exclude={"ben_chiu"}), "ben_chiu": bc}, created_by=u.username)
    db.add(c); db.flush()
    kt = FL.kiem_chuyen(db, t); t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    R.audit(db, u.username, u.role, "chi_phi_chuyen", f"trip:{tid}", after={**data.model_dump(mode="json"), "ben_chiu": bc})
    db.commit()
    return {"id": c.id, "ben_chiu": bc, "co_chuyen": kt["co"],
            "message": f"Đã ghi {COST_KINDS[data.kind]} – {BEN_CHIU[bc]}"}


class SuaChuyenIn(BaseModel):
    phien_ban: int | None = None      # VPM-8 – bản màn hình đang cầm
    ten_tour: str | None = None
    ngay_di: date | None = None
    ngay_ve: date | None = None
    km_dau: int | None = None
    km_cuoi: int | None = None
    km_gps: int | None = None
    km_nguon: str | None = None
    doanh_thu: float | None = None
    driver_id: int | None = None
    note: str | None = None


@router.put("/chuyen/{tid}")
def sua_chuyen(tid: int, data: SuaChuyenIn, u: User = Depends(require_roles(*WRITE, *KETOAN, "chutich", "tgd")),
               db: Session = Depends(get_db)):
    """Sửa nhật trình một chuyến CHƯA xác nhận.

    Chuyến đã xác nhận thì khoá: muốn sửa phải mở lại có lý do (POST /chuyen/{id}/mo-lai). Sửa thẳng vào
    chuyến đã chốt là sửa con số hai bên đã đối chiếu xong mà không để lại dấu vết ai sửa, sửa gì."""
    t = db.get(Trip, tid)
    if not t: raise HTTPException(404, "Không có chuyến")
    if t.status == "da_xac_nhan":
        raise HTTPException(422, "Chuyến đã xác nhận – mở lại (kèm lý do) rồi mới sửa được")
    truoc = {"ten_tour": t.ten_tour, "ngay_di": str(t.ngay_di), "ngay_ve": str(t.ngay_ve),
             "km_dau": t.km_dau, "km_cuoi": t.km_cuoi, "km_gps": t.km_gps, "km_nguon": t.km_nguon,
             "doanh_thu": t.doanh_thu}
    d = data.model_dump(exclude_none=True)
    from app.services import ghi_mot_lan as GML
    GML.kiem_phien_ban(t, d.pop("phien_ban", None), f"Chuyến {t.id}",
                       lambda: {**truoc, "phien_ban": t.phien_ban})
    for k, v in d.items(): setattr(t, k, v)
    GML.tang_phien_ban(t)
    if t.ngay_ve < t.ngay_di: raise HTTPException(422, "Ngày về trước ngày đi")
    if t.km_dau is not None and t.km_cuoi is not None and t.km_cuoi < t.km_dau:
        raise HTTPException(422, "Km cuối nhỏ hơn km đầu – kiểm tra lại số đọc trên đồng hồ")
    if t.km_nguon and t.km_nguon not in KM_NGUON:
        raise HTTPException(422, f"Nguồn số km '{t.km_nguon}' không có trong danh mục. "
                                 f"Chỉ nhận: {', '.join(KM_NGUON)}")
    if t.km_gps and not t.km_nguon:
        raise HTTPException(422, "Có số km theo GPS nhưng chưa ghi nguồn số km – chọn cổng GPS đã lấy số "
                                 "(gps_ttc / gps_tcd / gps_vietmap) hoặc nguồn của số đồng hồ")
    db.flush()
    kt = FL.kiem_chuyen(db, t); t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    R.audit(db, u.username, u.role, "sua_chuyen", f"trip:{tid}", before=truoc,
            after=data.model_dump(mode="json", exclude_none=True))
    db.commit()
    return {"id": t.id, "co": t.co, "ly_do": kt["ly_do"], "message": "Đã cập nhật nhật trình chuyến"}


class MoLaiIn(BaseModel):
    ly_do: str


@router.post("/chuyen/{tid}/mo-lai")
def mo_lai_chuyen(tid: int, data: MoLaiIn, u: User = Depends(require_roles(*KETOAN, "chutich", "tgd", "tp_dh")),
                  db: Session = Depends(get_db)):
    """Mở lại một chuyến đã xác nhận để sửa. Bắt buộc có lý do, và lý do được ghi vào nhật ký chuyến.

    Không cho mở lại chuyến thuộc kỳ quyết toán ĐÃ ĐÓNG: kỳ đóng là con số hai bên đã thỏa thuận, sửa ngược
    vào đó là sửa một khoản đã trả tiền."""
    t = db.get(Trip, tid)
    if not t: raise HTTPException(404, "Không có chuyến")
    if not (data.ly_do or "").strip():
        raise HTTPException(422, "Phải ghi lý do mở lại – không có lý do thì sau này không ai biết vì sao số đổi")
    ky = f"{t.ngay_di:%Y-%m}"
    v = db.get(Vehicle, t.vehicle_id)
    if v is not None and v.partner_id:
        st = db.execute(select(Settlement).where(Settlement.ky == ky, Settlement.partner_id == v.partner_id,
                                                 Settlement.status == "dong_ky")).scalars().first()
        if st is not None:
            raise HTTPException(422, f"Kỳ {ky} của chủ xe đã ĐÓNG – sửa phải tạo dòng điều chỉnh ở kỳ sau, "
                                     "không sửa ngược vào chuyến đã quyết toán")
    from datetime import datetime as _dt
    t.status = "cho_xac_nhan"
    t.note = (f"[Mở lại {_dt.now():%d/%m %H:%M} bởi {u.username}: {data.ly_do.strip()}] " + (t.note or ""))[:300]
    R.audit(db, u.username, u.role, "mo_lai_chuyen", f"trip:{tid}", after={"ly_do": data.ly_do})
    db.commit()
    return {"id": t.id, "status": t.status, "message": "Đã mở lại chuyến để sửa – nhớ xác nhận lại sau khi sửa xong"}


class SuaChiPhiIn(BaseModel):
    amount: float | None = None
    lit: float | None = None
    ben_chiu: str | None = None
    chung_tu: str | None = None
    note: str | None = None


@router.put("/chuyen/{tid}/chi-phi/{cid}")
def sua_chi_phi(tid: int, cid: int, data: SuaChiPhiIn,
                u: User = Depends(require_roles(*WRITE, *KETOAN, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Sửa một dòng chi phí của chuyến chưa xác nhận."""
    t = db.get(Trip, tid); c = db.get(TripCost, cid)
    if not t or not c or c.trip_id != tid: raise HTTPException(404, "Không có dòng chi phí này trong chuyến")
    if t.status == "da_xac_nhan": raise HTTPException(422, "Chuyến đã xác nhận – mở lại rồi mới sửa được")
    truoc = {"amount": c.amount, "lit": c.lit, "ben_chiu": c.ben_chiu}
    d = data.model_dump(exclude_none=True)
    if "ben_chiu" in d and d["ben_chiu"] not in BEN_CHIU:
        raise HTTPException(422, f"Bên chịu không hợp lệ. Chỉ nhận {', '.join(BEN_CHIU)}")
    for k, v in d.items(): setattr(c, k, v)
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if (c.amount or 0) >= nguong and not (c.chung_tu or "").strip():
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc có chứng từ gốc đính kèm (chặn cứng B6)")
    db.flush()
    kt = FL.kiem_chuyen(db, t); t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    R.audit(db, u.username, u.role, "sua_chi_phi_chuyen", f"trip:{tid}", before=truoc,
            after=data.model_dump(mode="json", exclude_none=True))
    db.commit()
    return {"id": c.id, "co_chuyen": t.co, "message": "Đã cập nhật dòng chi phí"}


@router.delete("/chuyen/{tid}/chi-phi/{cid}")
def xoa_chi_phi(tid: int, cid: int, u: User = Depends(require_roles(*WRITE, *KETOAN, "chutich", "tgd")),
                db: Session = Depends(get_db)):
    """Xóa một dòng chi phí nhập nhầm, chỉ khi chuyến chưa xác nhận. Nhật ký kiểm toán giữ lại nội dung đã xóa."""
    t = db.get(Trip, tid); c = db.get(TripCost, cid)
    if not t or not c or c.trip_id != tid: raise HTTPException(404, "Không có dòng chi phí này trong chuyến")
    if t.status == "da_xac_nhan": raise HTTPException(422, "Chuyến đã xác nhận – mở lại rồi mới xóa được")
    R.audit(db, u.username, u.role, "xoa_chi_phi_chuyen", f"trip:{tid}",
            before={"kind": c.kind, "amount": c.amount, "lit": c.lit, "ben_chiu": c.ben_chiu,
                    "chung_tu": c.chung_tu})
    db.delete(c); db.flush()
    kt = FL.kiem_chuyen(db, t); t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    db.commit()
    return {"co_chuyen": t.co, "message": "Đã xóa dòng chi phí"}


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
    so_tien: float | None = None
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


@router.get("/bao-duong/theo-xe")
def bao_duong_theo_xe(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Cả đội xe đứng đâu so với mốc bảo dưỡng — câu người quản đội hỏi mỗi sáng.

    Trước bản này luật ngưỡng chỉ chạy BÊN TRONG `kiem_tra()`, tức là chỉ trả lời được khi đang lập
    một lệnh điều xe cụ thể. Cửa này gọi ĐÚNG hàm ấy (`FL.tinh_trang_bao_duong`) chứ không dựng lại
    phép so sánh: hai bản chép của một ngưỡng thì ngày ai đó đổi tham số, hai chỗ nói hai điều.

    Xe đã thanh lý/ngừng khai thác không nằm trong danh sách — nhắc bảo dưỡng một chiếc xe đã bán là
    một dòng cảnh báo không ai xử lý được, và hàng đợi có dòng như thế thì người ta thôi đọc nó.
    """
    # Dựng rổ đếm TỪ chính thang mức, không gõ lại danh sách: bản cũ gõ tay bốn mức và thiếu
    # APPROVAL_REQUIRED, nên một chiếc xe ở mức ấy không được cộng vào đâu. Cùng một chỗ hỏng với ô
    # đếm của /tong-quan, chỉ nhỏ hơn nên lâu hơn mới có người thấy.
    ds, dem = [], {k: 0 for k in FL.NANG}
    for v in db.execute(select(Vehicle).where(Vehicle.active == True).order_by(Vehicle.code, Vehicle.plate)).scalars():
        t = FL.tinh_trang_bao_duong(db, v)
        dem[t["muc"]] = dem.get(t["muc"], 0) + 1
        ds.append({"vehicle_id": v.id, "code": v.code, "plate": v.plate, "lifecycle": v.lifecycle, **t,
                   "muc_ten": FL.MUC_TEN.get(t["muc"], t["muc"])})
    return {"xe": ds, "theo_muc": dem,
            "ghi_chu": "“Chưa đủ dữ liệu” KHÔNG được đọc là đạt: đó là xe chưa có lịch sử bảo dưỡng "
                       "hoặc chưa có số km đồng hồ đã xác nhận, nên máy không so được với mốc nào."}


# ─────────────────────────── BÁO HƯ HỎNG ───────────────────────────
# Cửa GHI đầu tiên của tài xế trên phân hệ đội xe (Chủ tịch chọn 06/10/2026).
#
# Ba điều cửa này CỐ Ý KHÔNG hỏi: số tiền, garage, và "nên sửa thế nào". Lúc đứng bên đường thì tài
# xế không biết ba thứ ấy, và một ô bắt buộc mà người gõ không biết câu trả lời thì ô ấy sẽ được
# điền bừa. Đề nghị sửa chữa (loại chi `sua_chua_xe`) do Giám đốc đội xe lập sau khi có báo giá.
from datetime import datetime                                     # noqa: E402
from app.models.hr import DispatchOrder                           # noqa: E402
from app.models.fleet import Fault, MUC_DO_HONG, TRANG_THAI_HONG  # noqa: E402


class BaoHongIn(BaseModel):
    vehicle_id: int
    hien_tuong: str
    muc_do: str = "con_chay_duoc"
    odo_km: int | None = None
    noi_xay_ra: str = ""


class XuLyHongIn(BaseModel):
    ket_qua: str = ""
    maintenance_id: int | None = None


def _hong_ra(f: Fault, xe: dict, ten: dict) -> dict:
    return {"id": f.id, "vehicle_id": f.vehicle_id, "plate": xe.get(f.vehicle_id, ""),
            "nguoi_bao": ten.get(f.nguoi_bao_id, "") or f.created_by,
            "bao_luc": f.bao_luc, "hien_tuong": f.hien_tuong,
            "muc_do": f.muc_do, "muc_do_ten": MUC_DO_HONG.get(f.muc_do, f.muc_do),
            "odo_km": f.odo_km, "noi_xay_ra": f.noi_xay_ra,
            "trang_thai": f.trang_thai, "trang_thai_ten": TRANG_THAI_HONG.get(f.trang_thai, f.trang_thai),
            "tiep_nhan_boi": f.tiep_nhan_boi, "tiep_nhan_luc": f.tiep_nhan_luc,
            "ket_qua": f.ket_qua, "maintenance_id": f.maintenance_id}


@router.get("/bao-hong")
def danh_sach_bao_hong(u: User = Depends(require_roles(*READ, "tai_xe")), db: Session = Depends(get_db)):
    """Sổ báo hỏng. Tài xế CHỈ thấy báo hỏng của chính mình — lọc ở đây, không lọc ở màn hình.

    Lọc ở màn hình là lọc tin được; lọc ở máy chủ mới là lọc. Mở tiền tố `/api/v1/fleet/bao-hong` cho
    vai `tai_xe` mà quên dòng này là cho một tài xế đọc toàn bộ tình trạng hỏng hóc của cả đội xe.
    """
    q = select(Fault).order_by(Fault.id.desc())
    if u.role == "tai_xe":
        emp = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
        if not emp:
            raise HTTPException(404, "Tài khoản chưa ghép với hồ sơ nhân sự — báo HCNS")
        q = q.where(Fault.nguoi_bao_id == emp.id)
    rows = list(db.execute(q.limit(300)).scalars())
    xe = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    ten = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    dem = {"dang_mo": sum(1 for f in rows if f.trang_thai in FL.HONG_CON_MO),
           "phai_dung_xe": sum(1 for f in rows if f.trang_thai in FL.HONG_CON_MO and f.muc_do == "phai_dung_xe")}
    return {"rows": [_hong_ra(f, xe, ten) for f in rows], "dem": dem,
            "muc_do": MUC_DO_HONG, "trang_thai": TRANG_THAI_HONG,
            "ghi_chu": "Báo hỏng KHÔNG có ô tiền và ô garage: lúc báo thì chưa ai biết hai con số ấy. "
                       "Đề nghị sửa chữa do đội xe lập sau khi có báo giá."}


@router.post("/bao-hong", status_code=201)
def them_bao_hong(data: BaoHongIn, u: User = Depends(require_roles(*WRITE, "tai_xe")),
                  db: Session = Depends(get_db)):
    """Báo một chiếc xe đang hỏng.

    Tài xế chỉ báo được xe CỦA MÌNH — xe đang đứng tên, hoặc xe có lệnh điều cho mình. Không phải để
    giữ bí mật, mà vì một báo hỏng cho chiếc xe người khác đang chạy thì người tiếp nhận không biết
    hỏi ai, còn chiếc xe ấy thì bị chặn lệnh mà tài xế của nó không hay.
    """
    v = db.get(Vehicle, data.vehicle_id)
    if not v: raise HTTPException(404, "Không có xe")
    if data.muc_do not in MUC_DO_HONG:
        raise HTTPException(422, f"Mức độ không hợp lệ. Chỉ nhận {', '.join(MUC_DO_HONG)}")
    if not data.hien_tuong.strip():
        raise HTTPException(422, "Ghi rõ hiện tượng — người tiếp nhận cần biết hỏng cái gì")

    emp = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if u.role == "tai_xe":
        if not emp:
            raise HTTPException(404, "Tài khoản chưa ghép với hồ sơ nhân sự — báo HCNS")
        co_lenh = db.execute(select(DispatchOrder).where(
            DispatchOrder.vehicle_id == v.id, DispatchOrder.driver_id == emp.id,
            DispatchOrder.status != "huy")).scalars().first()
        if v.driver_id != emp.id and not co_lenh:
            raise HTTPException(403, f"Xe {v.plate} không phải xe bạn đứng tên và cũng không có lệnh "
                                     "điều xe cho bạn. Báo trực tiếp cho Giám đốc đội xe.")
    f = Fault(vehicle_id=v.id, nguoi_bao_id=emp.id if emp else None,
              hien_tuong=data.hien_tuong.strip()[:300], muc_do=data.muc_do,
              odo_km=data.odo_km, noi_xay_ra=data.noi_xay_ra.strip()[:160],
              created_by=u.username)
    db.add(f); db.flush()
    R.audit(db, u.username, u.role, "bao_hong_xe", f"vehicle:{v.code or v.plate}",
            after=data.model_dump(mode="json"))
    db.commit()
    chan = data.muc_do == "phai_dung_xe"
    return {"id": f.id, "chan_lenh_dieu_xe": chan,
            "message": (f"Đã báo hỏng xe {v.plate}. " +
                        ("Xe này sẽ BỊ CHẶN khi lập lệnh điều xe cho tới khi đội xe đóng báo hỏng."
                         if chan else
                         "Người lập lệnh điều xe sẽ nhìn thấy báo hỏng này trước khi ký, nhưng xe "
                         "vẫn điều được."))}


@router.post("/bao-hong/{fid}/tiep-nhan")
def tiep_nhan_bao_hong(fid: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Đội xe xác nhận đã thấy. KHÔNG đóng — xe vẫn bị chặn nếu mức là phải dừng xe.

    Tách tiếp nhận khỏi đóng là để trả lời được hai câu khác nhau: "đã có ai nhìn chưa" và "đã sửa
    xong chưa". Gộp làm một thì một người bấm cho hết hàng đợi là xe hỏng biến khỏi màn hình.
    """
    f = db.get(Fault, fid)
    if not f: raise HTTPException(404, "Không có báo hỏng")
    if f.trang_thai != "moi": raise HTTPException(422, "Báo hỏng này đã được tiếp nhận hoặc đã đóng")
    f.trang_thai, f.tiep_nhan_boi, f.tiep_nhan_luc = "da_tiep_nhan", u.username, datetime.now()
    R.audit(db, u.username, u.role, "tiep_nhan_bao_hong", f"fleet_faults:{f.id}")
    db.commit()
    return {"id": f.id, "trang_thai": f.trang_thai, "message": "Đã tiếp nhận. Xe vẫn ở trạng thái đang hỏng."}


@router.post("/bao-hong/{fid}/dong")
def dong_bao_hong(fid: int, data: XuLyHongIn, u: User = Depends(require_roles(*WRITE)),
                  db: Session = Depends(get_db)):
    """Đóng báo hỏng. Bắt buộc ghi KẾT QUẢ — đóng mà không nói đã làm gì thì sổ báo hỏng chỉ còn là
    một danh sách đã-bấm-nút, và lần sau cùng hiện tượng ấy không ai tra được lần trước xử lý sao."""
    f = db.get(Fault, fid)
    if not f: raise HTTPException(404, "Không có báo hỏng")
    if f.trang_thai == "da_dong": raise HTTPException(422, "Báo hỏng này đã đóng")
    if not data.ket_qua.strip():
        raise HTTPException(422, "Ghi kết quả xử lý — đóng mà không nói đã làm gì thì lần sau không ai tra được")
    if data.maintenance_id and not db.get(Maintenance, data.maintenance_id):
        raise HTTPException(404, "Không có phiếu bảo dưỡng ấy")
    f.trang_thai, f.ket_qua = "da_dong", data.ket_qua.strip()[:300]
    f.maintenance_id, f.dong_boi, f.dong_luc = data.maintenance_id, u.username, datetime.now()
    R.audit(db, u.username, u.role, "dong_bao_hong", f"fleet_faults:{f.id}", after=data.model_dump(mode="json"))
    db.commit()
    v = db.get(Vehicle, f.vehicle_id)
    return {"id": f.id, "trang_thai": f.trang_thai,
            "message": f"Đã đóng báo hỏng xe {v.plate if v else ''}. Xe hết bị chặn vì lý do này."}


@router.post("/bao-duong", status_code=201)
def them_bao_duong(data: BaoDuongIn, u: User = Depends(require_roles(*WRITE, *KETOAN)), db: Session = Depends(get_db)):
    """Ghi bảo dưỡng/sửa chữa. Không có số km lúc làm thì hệ thống nói thẳng là không tính được mốc kỳ tới,
    thay vì im lặng suy ra từ chu kỳ chung – đó là cách chi phí bị ghi sai kỳ mà không ai phát hiện."""
    v = db.get(Vehicle, data.vehicle_id)
    if not v: raise HTTPException(404, "Không có xe")
    if data.kind not in MAINT_KINDS: raise HTTPException(422, f"Loại không hợp lệ. Chỉ nhận {', '.join(MAINT_KINDS)}")
    # Xe hợp tác cũng theo tham số: chủ tịch chốt cuối ngày 07/9/2026 là giữ cách chi hộ rồi cấn trừ.
    bc = data.ben_chiu or _mac_dinh_ben_chiu(db, "sua_chua")
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
    source: str                      # the_dau / epass / de_xuat_vietrip
    rows: list[dict]


@router.post("/giao-dich/nhap", status_code=201)
def nhap_giao_dich(data: GiaoDichIn, u: User = Depends(require_roles(*WRITE, *KETOAN)), db: Session = Depends(get_db)):
    """Nhập sao kê thẻ dầu hoặc báo cáo ePass. Khử trùng theo mã giao dịch gốc.

    Nghiệm thu của đặc tả: nhập lại CÙNG một file hai lần không sinh bản ghi trùng. Bản ghi lặp vẫn được giữ
    trong bảng thô với cờ trùng để còn chứng minh mình đã loại đúng cái gì."""
    if data.source not in NGUON_NGOAI:
        raise HTTPException(422, f"Nguồn không hợp lệ. Chỉ nhận {', '.join(NGUON_NGOAI)}")
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
    return {"rows": [{"id": t.id, "source": t.source, "source_ten": NGUON_NGOAI.get(t.source, t.source),
                      "ma_gd": t.ma_gd, "thoi_diem": t.thoi_diem,
                      "tai_khoan": t.tai_khoan,
                      "nga": t.nga, "nga_ten": NGA_CHI_PHI.get(t.nga, ""),
                      "nga_ly_do": t.nga_ly_do, "nga_boi": t.nga_boi, "nga_luc": t.nga_luc,
                      "vi": VI_EPASS.get(t.tai_khoan, "") if t.source == "epass" else "",
                      "bien_so": t.bien_so, "the_4so": t.the_4so, "xe": veh.get(t.vehicle_id, ""),
                      "vehicle_id": t.vehicle_id, "so_tien": t.so_tien, "lit": t.lit, "khop": t.khop,
                      "co": t.co, "trung": t.trung, "nhom": t.nhom,
                      "khong_phai_chi_phi": t.khong_phai_chi_phi, "ghi_chu": t.ghi_chu} for t in rows],
            "tong_chi_phi": sum((t.so_tien or 0) for t in rows if not t.khong_phai_chi_phi),
            "tong_dieu_chuyen": sum((t.so_tien or 0) for t in rows if t.khong_phai_chi_phi),
            "tong_chua_quy_ve_xe": sum((t.so_tien or 0) for t in rows
                                       if not t.khong_phai_chi_phi and t.vehicle_id is None),
            "theo_nhom": [{"nhom": n or "(không ghi nhóm)",
                           "so_khoan": sum(1 for t in rows if (t.nhom or "") == n),
                           "so_tien": sum((t.so_tien or 0) for t in rows if (t.nhom or "") == n)}
                          for n in sorted({(t.nhom or "") for t in rows})],
            # Chia theo VÍ ePass. Đội xe đi đường bằng hai ví thuộc hai pháp nhân khác nhau (VI_EPASS);
            # trước bản 07/10/2026 cột `tai_khoan` không ai ghi và cũng không ai đọc, nên chi phí cầu
            # đường của hai pháp nhân cộng chung một rổ. Tổng vẫn khớp – chỉ phần của từng bên là sai,
            # nên không ai nhìn ra. Nhóm "(chưa ghi tài khoản)" là nợ số liệu của các kỳ cũ: ĐẾM ĐƯỢC
            # ở đây, nạp lại tệp có cột tài khoản là hết, chứ không phải chia hộ theo tỷ lệ.
            "theo_vi": [{"tai_khoan": tk or "",
                         "ten": (VI_EPASS.get(tk, "(ví chưa khai trong hệ thống)") if tk
                                 else "(chưa ghi tài khoản – chưa quy về pháp nhân nào)"),
                         "so_khoan": sum(1 for t in rows if t.source == "epass" and (t.tai_khoan or "") == tk),
                         "so_tien": sum((t.so_tien or 0) for t in rows
                                        if t.source == "epass" and (t.tai_khoan or "") == tk
                                        and not t.khong_phai_chi_phi)}
                        for tk in sorted({(t.tai_khoan or "") for t in rows if t.source == "epass"})],
            "tong_chua_quy_ve_vi": sum((t.so_tien or 0) for t in rows
                                       if t.source == "epass" and not (t.tai_khoan or "")
                                       and not t.khong_phai_chi_phi),
            "vi_epass": VI_EPASS,
            # Chia theo NGẢ. Trước 07/10/2026 màn hình chỉ có một con số "chưa quy được về xe nào",
            # và trên hệ thật nó bằng ĐÚNG tổng chi phí — 100%, cả 36 dòng. Con số ấy đọc ra như
            # "chi phí đội xe chưa gắn xe", trong khi phần lớn là khoản của TOUR: phiếu đề xuất chi
            # Vietrip gắn vào tour và KHÔNG có ô xe (khảo sát 05/9/2026). Một con số gộp hai thứ
            # khác bản chất thì mỗi tháng báo động một tỷ hai mà không ai làm được gì.
            "theo_nga": [{"nga": k, "ten": NGA_CHI_PHI.get(k, "Chưa định tuyến — chưa ai đọc chứng từ"),
                          "cua_doi_xe": k in NGA_CUA_DOI_XE,
                          "so_khoan": sum(1 for t in rows if (t.nga or "") == k),
                          "so_tien": sum((t.so_tien or 0) for t in rows if (t.nga or "") == k)}
                         for k in sorted({(t.nga or "") for t in rows})],
            "tong_chua_dinh_tuyen": sum((t.so_tien or 0) for t in rows if not (t.nga or "")),
            "nga_chi_phi": NGA_CHI_PHI, "nga_cua_doi_xe": list(NGA_CUA_DOI_XE),
            "nguon": NGUON_NGOAI,
            "ghi_chu": "Đã loại bản ghi lặp (thêm gom_ban_trung=true để xem cả bản đã loại). Tổng chi phí "
                       "KHÔNG bao gồm khoản điều chuyển tiền nội bộ – hai thứ đó khác bản chất, cộng chung "
                       "là báo cáo sai. Riêng ePass còn chia theo VÍ: hai ví là hai pháp nhân, cộng chung "
                       "thì tổng đúng mà phần của từng bên sai."}


# ====================== ĐỢT 3: CHỦ XE, CÔNG NỢ, CẤN TRỪ, THẾ CHẤP, QUYẾT TOÁN ======================
from app.models.fleet import (PartnerOwner, SaleCase, Collateral, RepaymentPlan, RepaymentInstallment,
                              OffsetApplication, Settlement, SettlementLine, SharedInvoice, SharedInvoiceLine,
                              SALE_STAGES, PLAN_STATUS, SETTLE_STATUS, SETTLE_LINE_KINDS)
from app.models.finance import FinContract
from app.services import fleet_settlement as QT
from app.services import fleet_lai_lo as LL
from app.models.fleet import FleetPeriodCost, NHOM_CHI_PHI_KY

# Quyết toán và cấn trừ là việc của Kế toán; duyệt nội bộ và đóng kỳ là việc của lãnh đạo.
QT_WRITE = ("ketoan", "cntt", "gd_doi_xe")   # dựng bảng quyết toán; ĐÓNG kỳ vẫn là QT_DUYET
QT_DUYET = ("chutich", "tgd", "ketoan")


@router.get("/danh-muc-dot3")
def danh_muc_dot3(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    ai, ly_do = FL.nguoi_duoc_lap_lenh(db)
    return {"giai_doan_ban_xe": SALE_STAGES, "trang_thai_lich": PLAN_STATUS,
            "trang_thai_quyet_toan": SETTLE_STATUS, "loai_dong": SETTLE_LINE_KINDS,
            "nguoi_lap_lenh": [{"username": x.username, "full_name": x.full_name} for x in ai],
            "nguoi_lap_lenh_ghi_chu": ly_do}


class ChuXeIn(BaseModel):
    ho_ten: str
    tax_code: str = ""
    phone: str = ""
    company_id: int | None = None
    note: str = ""


@router.get("/chu-xe")
def ds_chu_xe(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    cos = {c.id: c.name for c in db.execute(select(Company)).scalars()}
    out = []
    for p in db.execute(select(PartnerOwner).order_by(PartnerOwner.ho_ten)).scalars():
        xes = list(db.execute(select(Vehicle).where(Vehicle.partner_id == p.id)).scalars())
        no = 0.0
        for pl in db.execute(select(RepaymentPlan).where(RepaymentPlan.partner_id == p.id,
                                                          RepaymentPlan.status == "hieu_luc")).scalars():
            no += QT.con_lai(db, pl)
        out.append({"id": p.id, "ho_ten": p.ho_ten, "tax_code": p.tax_code, "phone": p.phone,
                    "company": cos.get(p.company_id, ""), "company_id": p.company_id, "xac_minh": p.xac_minh,
                    "so_xe": len(xes), "xe": [v.plate for v in xes], "cong_no_con_lai": round(no),
                    "note": p.note})
    return out


@router.post("/chu-xe", status_code=201)
def them_chu_xe(data: ChuXeIn, u: User = Depends(require_roles(*WRITE, *QT_WRITE)), db: Session = Depends(get_db)):
    p = PartnerOwner(**data.model_dump()); db.add(p); db.flush()
    R.audit(db, u.username, u.role, "them_chu_xe_hop_tac", f"partner:{p.id}", after=data.model_dump(mode="json"))
    db.commit()
    return {"id": p.id, "message": f"Đã thêm chủ xe hợp tác {p.ho_ten}"}


class GanXeIn(BaseModel):
    vehicle_id: int
    partner_id: int | None = None


@router.post("/chu-xe/gan-xe")
def gan_xe(data: GanXeIn, u: User = Depends(require_roles(*WRITE, *QT_WRITE)), db: Session = Depends(get_db)):
    v = db.get(Vehicle, data.vehicle_id)
    if not v: raise HTTPException(404, "Không có xe")
    if data.partner_id and not db.get(PartnerOwner, data.partner_id): raise HTTPException(404, "Không có chủ xe")
    v.partner_id = data.partner_id
    R.audit(db, u.username, u.role, "gan_xe_cho_chu_xe", f"vehicle:{v.code or v.plate}",
            after={"partner_id": data.partner_id}); db.commit()
    return {"message": f"Đã gán xe {v.plate}" + (f" cho chủ xe #{data.partner_id}" if data.partner_id else " về không có chủ xe hợp tác")}


class LichIn(BaseModel):
    partner_id: int
    ten: str
    principal: float | None = None
    so_ky: int = 0
    moi_ky: float | None = None
    bat_dau: date | None = None
    creditor_company_id: int | None = None
    sale_case_id: int | None = None
    nguon: str = ""


@router.post("/lich-can-tru", status_code=201)
def tao_lich(data: LichIn, u: User = Depends(require_roles(*QT_WRITE)), db: Session = Depends(get_db)):
    """Lịch cấn trừ. Chưa có ngày bắt đầu hợp lệ thì giữ trạng thái nháp và KHÔNG phát cảnh báo quá hạn –
    báo quá hạn cho một lịch chưa ai xác nhận là cách nhanh nhất làm người dùng bỏ qua mọi cảnh báo."""
    if not db.get(PartnerOwner, data.partner_id): raise HTTPException(404, "Không có chủ xe")
    if (data.principal or 0) <= 0: raise HTTPException(422, "Số tiền phải lớn hơn 0")
    if not data.so_ky and not data.moi_ky: raise HTTPException(422, "Phải có số kỳ hoặc số tiền mỗi kỳ")
    pl = RepaymentPlan(**data.model_dump(), created_by=u.username)
    pl.status = "hieu_luc" if data.bat_dau else "nhap_chua_xac_nhan"
    db.add(pl); db.flush()
    ks = QT.tao_ky_cho_lich(db, pl)
    R.audit(db, u.username, u.role, "tao_lich_can_tru", f"plan:{pl.id}", after=data.model_dump(mode="json"))
    db.commit()
    return {"id": pl.id, "status": pl.status, "so_ky": len(ks),
            "cac_ky": [{"ky": k.ky, "due_date": k.due_date, "amount_due": k.amount_due} for k in ks],
            "message": f"Đã tạo lịch {len(ks)} kỳ" + ("" if data.bat_dau else
                       " – chưa có ngày bắt đầu nên giữ trạng thái nháp, chưa phát cảnh báo quá hạn")}


@router.get("/lich-can-tru")
def ds_lich(partner_id: int | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(RepaymentPlan).order_by(RepaymentPlan.id)
    if partner_id: q = q.where(RepaymentPlan.partner_id == partner_id)
    out = []
    for pl in db.execute(q).scalars():
        ks = list(db.execute(select(RepaymentInstallment).where(RepaymentInstallment.plan_id == pl.id)
                             .order_by(RepaymentInstallment.ky)).scalars())
        out.append({"id": pl.id, "partner_id": pl.partner_id, "ten": pl.ten, "principal": pl.principal,
                    "status": pl.status, "status_ten": PLAN_STATUS.get(pl.status, pl.status),
                    "da_ap_dung": QT.da_ap_dung(db, pl.id), "con_lai": QT.con_lai(db, pl),
                    "cac_ky": [{"ky": k.ky, "due_date": k.due_date, "amount_due": k.amount_due,
                                "amount_applied": k.amount_applied} for k in ks]})
    return out


class HoaDonChungIn(BaseModel):
    so_hoa_don: str
    ngay: date
    nha_cung_cap: str = ""
    company_id: int | None = None
    loai: str = "giu_xe"
    tong_tien: float | None = None
    vat: float | None = None
    xe: list[dict] = []          # [{vehicle_id, amount?, he_so?}] – lấy từ PHỤ LỤC hóa đơn


@router.post("/hoa-don-chung", status_code=201)
def them_hoa_don_chung(data: HoaDonChungIn, u: User = Depends(require_roles(*QT_WRITE)), db: Session = Depends(get_db)):
    """Hóa đơn dùng chung nhiều xe.

    Quy tắc sinh ra từ lỗi phân bổ tiền nước tháng 8/2026: chỉ chia cho những xe CÓ TÊN trên chính hóa đơn đó.
    Vì vậy đường này bắt gửi DANH SÁCH XE, không nhận "số lượng xe" – có ô số lượng là có ngày ai đó gõ 11 và
    chi phí chạy sang cả những xe không nằm trên hóa đơn, kể cả xe của pháp nhân khác."""
    if not data.xe: raise HTTPException(422, "Phải chọn danh sách xe từ phụ lục hóa đơn – không nhận số lượng xe")
    ids = [x.get("vehicle_id") for x in data.xe]
    if len(set(ids)) != len(ids): raise HTTPException(422, "Một xe xuất hiện hai lần trong phụ lục")
    cos = set()
    for vid in ids:
        v = db.get(Vehicle, vid)
        if not v: raise HTTPException(404, f"Không có xe id={vid}")
        if v.company_id: cos.add(v.company_id)
    if len(cos) > 1:
        raise HTTPException(422, "Phụ lục có xe của hai pháp nhân khác nhau – không chia chéo giữa hai pháp nhân. "
                                 "Tách thành hai hóa đơn theo đúng pháp nhân.")
    inv = SharedInvoice(**data.model_dump(exclude={"xe"}), created_by=u.username)
    db.add(inv); db.flush()
    for x in data.xe:
        db.add(SharedInvoiceLine(invoice_id=inv.id, vehicle_id=x["vehicle_id"],
                                 amount=float(x.get("amount") or 0), he_so=float(x.get("he_so") or 1)))
    db.flush()
    pb = QT.phan_bo_hoa_don_chung(db, inv)
    R.audit(db, u.username, u.role, "hoa_don_dung_chung", f"invoice:{inv.so_hoa_don}",
            after={"so_xe": len(ids), "tong": (data.tong_tien or 0) + (data.vat or 0)})
    db.commit()
    return {"id": inv.id, "phan_bo": pb, "message": f"Đã ghi hóa đơn {inv.so_hoa_don} và phân bổ cho {len(pb)} xe có tên trên phụ lục"}


class TheChapIn(BaseModel):
    contract_id: int
    vehicle_id: int
    tu_ngay: date | None = None
    phuong_an_rut_tai_san: str = ""
    nguon: str = ""


@router.post("/the-chap", status_code=201)
def them_the_chap(data: TheChapIn, u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd")), db: Session = Depends(get_db)):
    if not db.get(FinContract, data.contract_id): raise HTTPException(404, "Không có khế ước")
    if not db.get(Vehicle, data.vehicle_id): raise HTTPException(404, "Không có xe")
    c = Collateral(**data.model_dump()); db.add(c); db.flush()
    R.audit(db, u.username, u.role, "ghi_tai_san_the_chap", f"collateral:{c.id}", after=data.model_dump(mode="json"))
    db.commit()
    return {"id": c.id, "message": "Đã ghi xe vào tài sản thế chấp của khế ước"}


class GiaiChapIn(BaseModel):
    van_ban: str


@router.post("/the-chap/{cid}/giai-chap")
def giai_chap(cid: int, data: GiaiChapIn, u: User = Depends(require_roles("chutich", "tgd", "ketoan")), db: Session = Depends(get_db)):
    """Đánh dấu giải chấp. Bắt buộc có số văn bản: đặc tả nói rõ không tự coi tài sản không thấy trong danh
    sách ngân hàng là đã giải chấp."""
    c = db.get(Collateral, cid)
    if not c: raise HTTPException(404, "Không có bản ghi thế chấp")
    if not (data.van_ban or "").strip(): raise HTTPException(422, "Phải có số văn bản giải chấp của ngân hàng")
    from datetime import date as _d
    c.den_ngay = _d.today(); c.van_ban_giai_chap = data.van_ban; c.duyet_boi = u.username
    R.audit(db, u.username, u.role, "giai_chap_tai_san", f"collateral:{cid}", after={"van_ban": data.van_ban})
    db.commit()
    return {"message": "Đã ghi nhận giải chấp"}


class GoTheoDoiIn(BaseModel):
    ly_do: str


@router.post("/the-chap/{cid}/go-khoi-theo-doi")
def go_khoi_theo_doi(cid: int, data: GoTheoDoiIn, u: User = Depends(require_roles("chutich", "tgd")),
                     db: Session = Depends(get_db)):
    """Gỡ một xe khỏi danh sách tài sản bảo đảm ĐANG THEO DÕI, theo quyết định của lãnh đạo.

    Đây KHÔNG phải giải chấp. Giải chấp là ngân hàng trả tài sản lại và phải có văn bản – đường đó
    nằm ở /the-chap/{id}/giai-chap. Đường này chỉ nói: hồ sơ này thôi không theo dõi trên VTOS nữa.

    Vì hai việc khác nhau nên bản ghi cũng khác nhau: gỡ theo dõi ghi rõ 'GỠ KHỎI THEO DÕI (không
    phải giải chấp)' kèm lý do và người quyết định. Ghi nhầm thành giải chấp là đưa vào sổ một điều
    ngân hàng chưa xác nhận, và sau này không ai phân biệt được xe nào thật sự đã được rút ra.
    """
    c = db.get(Collateral, cid)
    if not c: raise HTTPException(404, "Không có bản ghi thế chấp")
    if not (data.ly_do or "").strip(): raise HTTPException(422, "Phải ghi lý do gỡ khỏi theo dõi")
    if c.den_ngay is not None: raise HTTPException(422, "Bản ghi này đã kết thúc theo dõi trước đó")
    v = db.get(Vehicle, c.vehicle_id); ct = db.get(FinContract, c.contract_id)
    from datetime import date as _d
    c.den_ngay = _d.today()
    c.van_ban_giai_chap = f"GỠ KHỎI THEO DÕI (không phải giải chấp) – {data.ly_do.strip()}"
    c.duyet_boi = u.username
    R.audit(db, u.username, u.role, "go_xe_khoi_theo_doi_the_chap", f"collateral:{cid}",
            after={"xe": v.plate if v else "", "khe_uoc": ct.contract_no if ct else "", "ly_do": data.ly_do,
                   "luu_y": "Không phải giải chấp – ngân hàng chưa xác nhận trả tài sản"})
    db.commit()
    return {"message": f"Đã gỡ xe {v.plate if v else cid} khỏi theo dõi thế chấp của khế ước "
                       f"{ct.contract_no if ct else ''} – ghi rõ đây KHÔNG phải giải chấp"}


class BanXeIn(BaseModel):
    vehicle_id: int
    partner_id: int | None = None
    seller_company_id: int | None = None
    ngay_ky: date | None = None
    gia_ban: float | None = None
    da_thu: float | None = None
    nguoi_mua: str = ""
    han_thu_du: date | None = None
    nguon: str = ""


@router.post("/ban-xe", status_code=201)
def tao_ho_so_ban(data: BanXeIn, u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd")), db: Session = Depends(get_db)):
    if not db.get(Vehicle, data.vehicle_id): raise HTTPException(404, "Không có xe")
    sc = SaleCase(**data.model_dump(), created_by=u.username)
    db.add(sc); db.flush()
    canh_bao = QT.kiem_ban_xe(db, sc)
    R.audit(db, u.username, u.role, "ho_so_ban_xe", f"sale:{sc.id}", after=data.model_dump(mode="json"))
    db.commit()
    return {"id": sc.id, "canh_bao": canh_bao,
            "message": "Đã tạo hồ sơ bán xe – các trục hợp đồng, thu tiền, bàn giao, giải chấp, sang tên theo dõi riêng"}


class SuaHoSoBanIn(BaseModel):
    nguoi_mua: str | None = None
    gia_ban: float | None = None
    da_thu: float | None = None
    han_thu_du: date | None = None
    ngay_ky: date | None = None
    nguon: str | None = None
    note: str | None = None


@router.get("/ban-xe")
def danh_sach_ban_xe(u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd", "ketoan", "bks", "cntt")), db: Session = Depends(get_db)):
    """Hồ sơ bán xe kèm số còn phải thu. Không có màn hình đọc thì không ai biết hồ sơ nào còn dở."""
    from datetime import date as _d
    out = []
    for sc in db.execute(select(SaleCase).order_by(SaleCase.id.desc())).scalars():
        v = db.get(Vehicle, sc.vehicle_id)
        con = (sc.gia_ban or 0) - (sc.da_thu or 0)
        out.append({"id": sc.id, "xe": v.plate if v else "", "nguoi_mua": sc.nguoi_mua, "ngay_ky": sc.ngay_ky,
                    "gia_ban": sc.gia_ban, "da_thu": sc.da_thu, "con_phai_thu": con, "han_thu_du": sc.han_thu_du,
                    "qua_han_thu": bool(sc.han_thu_du and con > 0 and sc.han_thu_du < _d.today()),
                    "stage": sc.stage, "da_ban_giao": sc.da_ban_giao, "da_giai_chap": sc.da_giai_chap,
                    "van_ban_giai_chap": sc.van_ban_giai_chap, "da_sang_ten": sc.da_sang_ten,
                    "chua_co_gia_ban": not (sc.gia_ban or 0), "nguon": sc.nguon, "note": sc.note})
    return out


@router.put("/ban-xe/{sid}")
def sua_ho_so_ban(sid: int, data: SuaHoSoBanIn, u: User = Depends(require_roles("ketoan", "chutich", "tgd")),
                  db: Session = Depends(get_db)):
    """Cập nhật giá bán và số tiền đã thu. Kế toán ghi dần theo từng lần khách trả, nên đây là thao tác
    lặp lại chứ không phải nhập một lần lúc tạo hồ sơ.

    Đã thu KHÔNG được vượt giá bán: vượt nghĩa là một trong hai con số nhập sai, và nếu để lọt thì
    "còn phải thu" thành số âm, hồ sơ trông như đã thu xong trong khi chưa.
    """
    sc = db.get(SaleCase, sid)
    if not sc: raise HTTPException(404, "Không có hồ sơ bán xe")
    d = data.model_dump(exclude_unset=True)
    gia = d.get("gia_ban", sc.gia_ban) or 0
    thu = d.get("da_thu", sc.da_thu) or 0
    if gia and thu > gia:
        raise HTTPException(422, f"Đã thu {thu:,.0f}đ vượt giá bán {gia:,.0f}đ – kiểm lại một trong hai con số")
    if thu < 0 or gia < 0: raise HTTPException(422, "Giá bán và số đã thu không được âm")
    before = {k: str(getattr(sc, k)) for k in d}
    for k, val in d.items(): setattr(sc, k, val)
    R.audit(db, u.username, u.role, "sua_ho_so_ban_xe", f"sale:{sid}", before=before,
            after=data.model_dump(mode="json", exclude_unset=True))
    db.commit()
    con = (sc.gia_ban or 0) - (sc.da_thu or 0)
    return {"id": sc.id, "con_phai_thu": con,
            "message": f"Đã cập nhật hồ sơ bán xe – còn phải thu {con:,.0f}đ"
                       + (f", hạn {sc.han_thu_du:%d/%m/%Y}" if sc.han_thu_du and con > 0 else "")}


class ChuyenBuocBanIn(BaseModel):
    stage: str
    van_ban_giai_chap: str = ""
    ly_do_vuot: str = ""


@router.post("/ban-xe/{sid}/chuyen-buoc")
def chuyen_buoc_ban(sid: int, data: ChuyenBuocBanIn, u: User = Depends(require_roles("chutich", "tgd", "ketoan")),
                    db: Session = Depends(get_db)):
    """Chuyển bước hồ sơ bán xe. Bước SANG TÊN đi qua chặn cứng B7 và B8."""
    sc = db.get(SaleCase, sid)
    if not sc: raise HTTPException(404, "Không có hồ sơ bán xe")
    if data.stage not in SALE_STAGES: raise HTTPException(422, f"Bước không hợp lệ. Chỉ nhận {', '.join(SALE_STAGES)}")
    if data.van_ban_giai_chap: sc.van_ban_giai_chap = data.van_ban_giai_chap
    if data.stage == "sang_ten":
        loi = [x for x in QT.kiem_ban_xe(db, sc, muon_sang_ten=True) if x["level"] == FL.BLOCK]
        if loi:
            raise HTTPException(422, {"message": "Không đủ điều kiện sang tên xe", "vi_pham": loi})
        sc.da_sang_ten = True
    if data.stage == "giai_chap":
        if not (sc.van_ban_giai_chap or "").strip():
            raise HTTPException(422, "Phải có văn bản giải chấp của ngân hàng – không suy ra từ việc không thấy xe trong danh sách")
        sc.da_giai_chap = True
    if data.stage == "ban_giao": sc.da_ban_giao = True
    sc.stage = data.stage
    R.audit(db, u.username, u.role, "chuyen_buoc_ban_xe", f"sale:{sid}", after=data.model_dump(mode="json"))
    db.commit()
    return {"message": f"Đã chuyển sang bước: {SALE_STAGES[data.stage]}"}


@router.post("/quyet-toan/{ky}/{partner_id}/dung")
def dung_ky(ky: str, partner_id: int, u: User = Depends(require_roles(*QT_WRITE)), db: Session = Depends(get_db)):
    """Dựng (hoặc dựng lại) bảng quyết toán nháp của một kỳ. Dựng lại KHÔNG cấn trừ thêm lần nào."""
    try:
        st = QT.dung_quyet_toan(db, partner_id, ky, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "dung_quyet_toan_chu_xe", f"settlement:{st.id}",
            after={"ky": ky, "truoc_can_tru": st.truoc_can_tru})
    db.commit()
    return _qt_out(db, st)


def _qt_out(db: Session, st: Settlement) -> dict:
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    p = db.get(PartnerOwner, st.partner_id)
    lines = list(db.execute(select(SettlementLine).where(SettlementLine.settlement_id == st.id)
                            .order_by(SettlementLine.kind, SettlementLine.id)).scalars())
    return {"id": st.id, "ky": st.ky, "chu_xe": p.ho_ten if p else "", "partner_id": st.partner_id,
            "status": st.status, "status_ten": SETTLE_STATUS.get(st.status, st.status),
            "doanh_thu": st.doanh_thu, "doi_tac_huong": st.doi_tac_huong, "doi_tac_chiu": st.doi_tac_chiu,
            "dieu_chinh": st.dieu_chinh, "truoc_can_tru": st.truoc_can_tru, "can_tru": st.can_tru,
            "sau_can_tru": st.sau_can_tru, "chuyen_ky_sau": st.chuyen_ky_sau, "ghi_chu": st.ghi_chu,
            "cong_thuc": "Trước cấn trừ = đối tác được hưởng − đối tác phải chịu + điều chỉnh được duyệt. "
                         "Sau cấn trừ = trước cấn trừ − cấn trừ đủ điều kiện. Số âm ghi phải thu và chuyển "
                         "kỳ sau, KHÔNG tạo phiếu chi âm.",
            "dong": [{"id": l.id, "kind": l.kind, "kind_ten": SETTLE_LINE_KINDS.get(l.kind, l.kind),
                      "xe": veh.get(l.vehicle_id, ""), "trip_id": l.trip_id, "mo_ta": l.mo_ta,
                      "amount": l.amount, "ben_chiu": l.ben_chiu, "chung_tu": l.chung_tu,
                      "duyet_boi": l.duyet_boi} for l in lines]}


@router.get("/quyet-toan")
def ds_quyet_toan(ky: str = "", partner_id: int | None = None, u: User = Depends(require_roles(*READ)),
                  db: Session = Depends(get_db)):
    q = select(Settlement).order_by(Settlement.ky.desc(), Settlement.id.desc())
    if ky: q = q.where(Settlement.ky == ky)
    if partner_id: q = q.where(Settlement.partner_id == partner_id)
    return [_qt_out(db, s) for s in db.execute(q.limit(200)).scalars()]


class CanTruIn(BaseModel):
    plan_id: int
    so_tien: float = 0        # 0 = lấy tối đa theo số phải trả của kỳ


@router.post("/quyet-toan/{sid}/can-tru", status_code=201)
def can_tru(sid: int, data: CanTruIn, u: User = Depends(require_roles(*QT_WRITE)), db: Session = Depends(get_db)):
    """Áp dụng cấn trừ vào một kỳ quyết toán.

    Ba điều kiện phải đúng cùng lúc: cùng đối tác, cùng pháp nhân, và kỳ chưa đóng. Không tự bù nợ của công ty
    này vào khoản công ty kia phải trả – hai pháp nhân là hai túi tiền khác nhau."""
    st = db.get(Settlement, sid)
    if not st: raise HTTPException(404, "Không có kỳ quyết toán")
    if st.status == "dong_ky": raise HTTPException(422, "Kỳ đã đóng – phải tạo bút toán điều chỉnh ở kỳ sau")
    pl = db.get(RepaymentPlan, data.plan_id)
    if not pl: raise HTTPException(404, "Không có lịch cấn trừ")
    if pl.partner_id != st.partner_id:
        raise HTTPException(422, "Lịch cấn trừ thuộc đối tác khác – không bù nợ của người này vào khoản người kia")
    if pl.creditor_company_id and st.company_id and pl.creditor_company_id != st.company_id:
        raise HTTPException(422, "Lịch cấn trừ thuộc pháp nhân khác với kỳ quyết toán – hai pháp nhân là hai túi tiền")
    so_tien = (data.so_tien or 0) if (data.so_tien or 0) > 0 else max(0.0, (st.truoc_can_tru or 0) - (st.can_tru or 0))
    kq = QT.ap_dung_can_tru(db, pl, so_tien, idem_key=f"qt{st.id}:plan{pl.id}:{round(so_tien)}",
                            boi=u.username, settlement_id=st.id, chung_tu=f"Quyết toán {st.ky}")
    QT.dung_quyet_toan(db, st.partner_id, st.ky, u.username)
    R.audit(db, u.username, u.role, "can_tru_quyet_toan", f"settlement:{st.id}",
            after={"plan_id": pl.id, "da_tru": kq["da_tru"], "lap_lai": kq["lap_lai"]})
    db.commit()
    return {**kq, "quyet_toan": _qt_out(db, db.get(Settlement, sid))}


class DieuChinhIn(BaseModel):
    mo_ta: str
    amount: float
    chung_tu: str = ""


@router.post("/quyet-toan/{sid}/dieu-chinh", status_code=201)
def them_dieu_chinh(sid: int, data: DieuChinhIn, u: User = Depends(require_roles(*QT_DUYET)), db: Session = Depends(get_db)):
    """Dòng điều chỉnh phải có người duyệt – đó là điều kiện đóng kỳ (B9)."""
    st = db.get(Settlement, sid)
    if not st: raise HTTPException(404, "Không có kỳ quyết toán")
    if st.status == "dong_ky": raise HTTPException(422, "Kỳ đã đóng – điều chỉnh phải ghi vào kỳ sau")
    if not (data.mo_ta or "").strip(): raise HTTPException(422, "Phải ghi lý do điều chỉnh")
    db.add(SettlementLine(settlement_id=sid, kind="dieu_chinh", mo_ta=data.mo_ta, amount=data.amount,
                          chung_tu=data.chung_tu, duyet_boi=u.username))
    db.flush()
    QT.dung_quyet_toan(db, st.partner_id, st.ky, u.username)
    R.audit(db, u.username, u.role, "dieu_chinh_quyet_toan", f"settlement:{sid}", after=data.model_dump(mode="json"))
    db.commit()
    return {"message": "Đã ghi dòng điều chỉnh", "quyet_toan": _qt_out(db, db.get(Settlement, sid))}


@router.post("/quyet-toan/{sid}/dong-ky")
def dong_ky(sid: int, u: User = Depends(require_roles("chutich", "tgd", "ketoan")), db: Session = Depends(get_db)):
    """Đóng kỳ. Chặn cứng B9: còn cờ đỏ chưa xử lý thì không đóng được.

    Đóng rồi thì khóa: sửa phải tạo bút toán điều chỉnh ở kỳ sau, không sửa ngược vào một con số đã chốt với
    đối tác."""
    st = db.get(Settlement, sid)
    if not st: raise HTTPException(404, "Không có kỳ quyết toán")
    if st.status == "dong_ky": return {"message": "Kỳ này đã đóng trước đó"}
    loi = QT.kiem_dong_ky(db, st)
    if loi: raise HTTPException(422, {"message": "Không đóng được kỳ", "vi_pham": loi})
    from datetime import datetime as _dt
    st.status = "dong_ky"; st.closed_at = _dt.now(); st.closed_by = u.username
    R.audit(db, u.username, u.role, "dong_ky_quyet_toan", f"settlement:{sid}",
            after={"ky": st.ky, "sau_can_tru": st.sau_can_tru, "chuyen_ky_sau": st.chuyen_ky_sau})
    db.commit()
    return {"message": f"Đã đóng kỳ {st.ky}", "quyet_toan": _qt_out(db, st)}


class KiemChiIn(BaseModel):
    tour_id: int | None = None
    so_tien: float
    partner_id: int | None = None
    co_dong_khau_tru: bool = False
    chung_tu: str = ""


@router.post("/kiem-chi")
def kiem_chi(data: KiemChiIn, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Chạy chặn cứng B4, B5, B6 cho một đề nghị chi trước khi đưa lên bàn duyệt. Chỉ kiểm, không ghi gì."""
    items = QT.kiem_chi(db, data.tour_id, data.so_tien, data.partner_id, data.co_dong_khau_tru, data.chung_tu)
    muc = FL.BLOCK if any(i["level"] == FL.BLOCK for i in items) else (FL.OK if not items else FL.REVIEW)
    return {"muc": muc, "muc_ten": FL.MUC_TEN[muc], "items": items}


# ====================== ĐỢT 4: LỆNH ĐIỀU XE, HIỆU QUẢ, BẢN TIN SÁNG ======================
from app.models.hr import DispatchOrder
from app.models.fleet import AiRunLog
from app.services import fleet_ai as AI


@router.get("/goi-y-dieu-xe")
def goi_y_dieu_xe(date_from: date, date_to: date, so_khach: int = 0, km_du_kien: int = 0,
                  u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Gợi ý xe cho một khoảng ngày: lọc cứng trước, xếp hạng sau, kèm lý do bằng lời.

    Đây là GỢI Ý, không phải quyết định – người chốt lệnh vẫn là người quyết, và nếu chọn khác gợi ý thì hệ
    thống bắt ghi lý do (xem POST /dispatch)."""
    if date_to < date_from: raise HTTPException(422, "Ngày kết thúc trước ngày bắt đầu")
    kq = AI.goi_y_dieu_xe(db, date_from, date_to, so_khach, km_du_kien)
    AI.ghi_run(db, "A1", {"tu": str(date_from), "den": str(date_to), "khach": so_khach, "km": km_du_kien},
               kq, len(kq["phuong_an"]) + len(kq["bi_loai"]), len(kq["bi_loai"]), u.username)
    db.commit()
    return kq


@router.get("/de-lap-lenh")
def de_lap_lenh(tu: date, den: date, u: User = Depends(require_roles(*READ)),
                db: Session = Depends(get_db)):
    """Những thứ CẦN CÓ để chốt một lệnh điều xe, gom vào một đường dưới hàng rào đội xe.

    Vì sao phải có đường riêng thay vì để màn hình gọi /api/v1/tours và /api/v1/vehicle-rates:

      Tham số chính sách xe_nguoi_lap_lenh chỉ định Giám đốc điều hành đội xe là người DUY NHẤT được
      chốt lệnh (chỉ đạo Chủ tịch 07/9/2026). Nhưng phạm vi API của vai trò gd_doi_xe – đo ngày
      09/9/2026 – có /api/v1/dispatch và /api/v1/vehicles, KHÔNG có /api/v1/tours và
      /api/v1/vehicle-rates. Mà POST /dispatch bắt buộc có tour_id. Nghĩa là người duy nhất được lập
      lệnh không có cách nào biết mã tour để điền vào lệnh.

      Cách chữa dễ nhất là mở /api/v1/tours cho ông. Không làm thế: phân hệ tour mang giá bán, dự
      toán, biên lợi nhuận và giải trình dưới biên – mở cả cụm để lấy bốn cột lịch trình là nới hàng
      rào rộng hơn nhiều lần việc cần làm. Đường này trả về ĐÚNG bốn cột ấy: mã, tên, ngày đi, ngày về,
      số khách dự kiến. Không có một con số tiền nào của tour.

    Trả kèm ai được lập lệnh, để màn hình nói trước bằng lời thay vì để người dùng bấm rồi nhận 403.
    """
    if den < tu: raise HTTPException(422, "Ngày kết thúc trước ngày bắt đầu")
    from app.models.core import Tour as _Tour
    from app.models.hr import VehicleRate as _Rate
    # Tour GIAO NHAU với khoảng ngày, không phải tour nằm gọn trong khoảng: một đoàn khởi hành hôm
    # trước và về hôm sau vẫn là đoàn cần xe trong ngày đang xếp.
    tours = db.execute(select(_Tour).where(_Tour.start_date <= den, _Tour.end_date >= tu)
                       .order_by(_Tour.start_date)).scalars().all()
    rates = db.execute(select(_Rate).where(_Rate.status == "active")
                       .order_by(_Rate.route)).scalars().all()
    ai, ly_do = FL.nguoi_duoc_lap_lenh(db)
    return {
        "tour": [{"id": t.id, "code": t.code, "name": t.name, "start_date": t.start_date,
                  "end_date": t.end_date, "planned_pax": t.planned_pax} for t in tours],
        "bang_gia": [{"id": r.id, "route": r.route, "days": r.days,
                      "internal_price": r.internal_price, "partner_price": r.partner_price}
                     for r in rates],
        "nguoi_duoc_lap_lenh": [{"username": x.username, "full_name": x.full_name} for x in ai],
        "ly_do_khong_gioi_han": ly_do,
        "toi_duoc_lap": (not ai) or u.id in {x.id for x in ai},
        "ghi_chu": ("Danh sách tour ở đây chỉ có lịch trình và số khách – không kèm giá bán hay dự "
                    "toán. Đội xe cần mã tour để lập lệnh, không cần biết tour lãi bao nhiêu."),
    }


# ====================== LÃI LỖ ĐỘI XE ======================
@router.get("/lai-lo")
def lai_lo(ky: str, phan_bo: str = "khong", u: User = Depends(require_roles(*READ)),
           db: Session = Depends(get_db)):
    """Lãi lỗ đội xe của một kỳ: ba tầng chi phí để riêng, không tầng nào lẫn vào tầng nào.

    Mặc định KHÔNG phân bổ chi phí đội về từng xe. Muốn xem thử thì phải chọn tiêu thức, và kết quả sau
    phân bổ nằm ở cột riêng có tên nói rõ đó là số phân bổ."""
    try:
        QT.ky_range(ky)
    except Exception:
        raise HTTPException(422, "Kỳ phải có dạng YYYY-MM")
    try:
        return LL.bao_cao(db, ky, phan_bo)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/lai-lo/theo-chuyen")
def lai_lo_chuyen(ky: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Quyết toán theo TOUR: mỗi chuyến một dòng kèm lãi gộp và suất tiêu hao của chính chuyến đó."""
    try:
        QT.ky_range(ky)
    except Exception:
        raise HTTPException(422, "Kỳ phải có dạng YYYY-MM")
    return LL.theo_chuyen(db, ky)


@router.get("/chi-phi-ky")
def chi_phi_ky(ky: str = "", u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(FleetPeriodCost).order_by(FleetPeriodCost.ky.desc(), FleetPeriodCost.id.desc())
    if ky: q = q.where(FleetPeriodCost.ky == ky)
    xe = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    return {"nhom": [{"ma": k, "ten": v[0], "pham_vi": v[1]} for k, v in NHOM_CHI_PHI_KY.items()],
            "rows": [{"id": r.id, "ky": r.ky, "pham_vi": r.pham_vi, "vehicle_id": r.vehicle_id,
                      "xe": xe.get(r.vehicle_id, ""), "nhom": r.nhom,
                      "nhom_ten": NHOM_CHI_PHI_KY.get(r.nhom, (r.nhom,))[0], "mo_ta": r.mo_ta,
                      "so_tien": r.so_tien, "chung_tu": r.chung_tu, "nguon": r.nguon,
                      "boi": r.boi, "luc": r.luc}
                     for r in db.execute(q.limit(500)).scalars()]}


class ChiPhiKyIn(BaseModel):
    ky: str
    nhom: str
    so_tien: float
    vehicle_id: int | None = None
    mo_ta: str = ""
    chung_tu: str = ""


@router.post("/chi-phi-ky", status_code=201)
def them_chi_phi_ky(data: ChiPhiKyIn, u: User = Depends(require_roles(*QT_WRITE)),
                    db: Session = Depends(get_db)):
    """Ghi một khoản chi phí kỳ (bảo hiểm, lương tài xế, phí bãi, lãi vay…)."""
    try:
        QT.ky_range(data.ky)
    except Exception:
        raise HTTPException(422, "Kỳ phải có dạng YYYY-MM")
    if data.nhom not in NHOM_CHI_PHI_KY:
        raise HTTPException(422, f"Nhóm chi phí không hợp lệ: {data.nhom}")
    if (data.so_tien or 0) <= 0: raise HTTPException(422, "Số tiền phải lớn hơn 0")
    pham_vi = NHOM_CHI_PHI_KY[data.nhom][1]
    if pham_vi == "xe" and not data.vehicle_id:
        raise HTTPException(422, f"'{NHOM_CHI_PHI_KY[data.nhom][0]}' là chi phí của một chiếc xe cụ thể "
                                 "– phải chọn xe. Không chọn xe thì khoản này rơi vào khối chi phí "
                                 "chung và không còn quy được về chiếc nào.")
    if pham_vi == "doi" and data.vehicle_id:
        raise HTTPException(422, f"'{NHOM_CHI_PHI_KY[data.nhom][0]}' là chi phí của cả đội, không gắn "
                                 "vào một xe. Gắn vào một xe là làm chiếc đó gánh phần của cả đội.")
    trung = db.execute(select(FleetPeriodCost).where(
        FleetPeriodCost.ky == data.ky, FleetPeriodCost.nhom == data.nhom,
        FleetPeriodCost.vehicle_id == data.vehicle_id,
        FleetPeriodCost.mo_ta == (data.mo_ta or ""))).scalars().first()
    if trung is not None:
        raise HTTPException(422, f"Kỳ {data.ky} đã có khoản '{NHOM_CHI_PHI_KY[data.nhom][0]}"
                                 f"{(' – ' + data.mo_ta) if data.mo_ta else ''}' "
                                 f"({trung.so_tien:,.0f} đ). Sửa dòng đã có, đừng ghi thêm dòng thứ hai "
                                 "– nhập lại bảng tháng lần nữa là chi phí nhân đôi.")
    r = FleetPeriodCost(ky=data.ky, pham_vi=pham_vi, vehicle_id=data.vehicle_id, nhom=data.nhom,
                        mo_ta=data.mo_ta[:200], so_tien=data.so_tien, chung_tu=data.chung_tu[:200],
                        boi=u.username)
    db.add(r); db.flush()
    R.audit(db, u.username, u.role, "them_chi_phi_ky_doi_xe", f"ky:{data.ky}",
            after={"nhom": data.nhom, "so_tien": data.so_tien, "xe": data.vehicle_id})
    db.commit()
    return {"id": r.id, "message": f"Đã ghi {data.so_tien:,.0f} đ vào kỳ {data.ky}."}


@router.put("/chi-phi-ky/{cid}")
def sua_chi_phi_ky(cid: int, data: ChiPhiKyIn, u: User = Depends(require_roles(*QT_WRITE)),
                   db: Session = Depends(get_db)):
    r = db.get(FleetPeriodCost, cid)
    if r is None: raise HTTPException(404, "Không có khoản này")
    if (data.so_tien or 0) <= 0: raise HTTPException(422, "Số tiền phải lớn hơn 0")
    truoc = {"so_tien": r.so_tien, "mo_ta": r.mo_ta}
    r.so_tien = data.so_tien; r.mo_ta = data.mo_ta[:200]; r.chung_tu = data.chung_tu[:200]
    R.audit(db, u.username, u.role, "sua_chi_phi_ky_doi_xe", f"chi_phi_ky:{r.id}", before=truoc,
            after={"so_tien": r.so_tien, "mo_ta": r.mo_ta})
    db.commit()
    return {"message": "Đã cập nhật."}


@router.delete("/chi-phi-ky/{cid}")
def xoa_chi_phi_ky(cid: int, ly_do: str = "", u: User = Depends(require_roles(*QT_WRITE)),
                   db: Session = Depends(get_db)):
    """Gỡ một khoản khỏi kỳ. Bắt buộc ghi lý do – một khoản chi phí biến mất khỏi báo cáo mà không ai
    biết vì sao là cách nhanh nhất làm cho lãi lỗ tháng không đối chiếu được với tháng trước."""
    if not ly_do.strip(): raise HTTPException(422, "Gỡ một khoản chi phí phải ghi lý do")
    r = db.get(FleetPeriodCost, cid)
    if r is None: raise HTTPException(404, "Không có khoản này")
    R.audit(db, u.username, u.role, "xoa_chi_phi_ky_doi_xe", f"chi_phi_ky:{r.id}",
            before={"ky": r.ky, "nhom": r.nhom, "so_tien": r.so_tien}, after={"ly_do": ly_do})
    db.delete(r); db.commit()
    return {"message": "Đã gỡ khoản này khỏi kỳ."}


@router.get("/hieu-qua")
def hieu_qua(ky: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Hiệu quả xe và tài xế của một kỳ. Chỉ đọc và tính, không ghi số liệu nghiệp vụ nào."""
    try:
        QT.ky_range(ky)
    except Exception:
        raise HTTPException(422, "Kỳ phải có dạng YYYY-MM")
    kq = AI.hieu_qua_ky(db, ky)
    AI.ghi_run(db, "A9", {"ky": ky}, {"so_xe": len(kq["xe"]), "so_tai_xe": len(kq["tai_xe"])},
               len(kq["xe"]) + len(kq["tai_xe"]), 0, u.username)
    db.commit()
    return kq


class KhuyenNghiBanIn(BaseModel):
    vehicle_id: int
    gia_chao: float
    dinh_gia_noi_bo: float = 0


@router.post("/khuyen-nghi-ban-xe")
def khuyen_nghi_ban(data: KhuyenNghiBanIn, u: User = Depends(require_roles("chutich", "tgd", "ketoan", "cntt")),
                    db: Session = Depends(get_db)):
    """So sánh giá chào bán với định giá nội bộ và lợi nhuận khai thác. Chỉ phân tích, không tạo hồ sơ bán."""
    if not db.get(Vehicle, data.vehicle_id): raise HTTPException(404, "Không có xe")
    return AI.khuyen_nghi_ban_xe(db, data.vehicle_id, data.gia_chao, data.dinh_gia_noi_bo)


@router.get("/ban-tin-sang")
def ban_tin_sang(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return AI.ban_tin_sang(db)


@router.post("/nang-muc-canh-bao")
def nang_muc(u: User = Depends(require_roles("cntt", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Nâng mức cảnh báo tồn quá 3 ngày – chỉ những cảnh báo đã có người nhận."""
    kq = AI.nang_muc_canh_bao(db)
    AI.ghi_run(db, "A0", {"ngay": str(date.today())}, kq, len(kq["da_nang"]) + len(kq["bo_qua"]),
               len(kq["da_nang"]), u.username)
    R.audit(db, u.username, u.role, "nang_muc_canh_bao_doi_xe", "alerts", after={"da_nang": len(kq["da_nang"])})
    db.commit()
    return kq


@router.get("/nhat-ky-tu-dong")
def nhat_ky_tu_dong(agent: str = "", limit: int = 100, u: User = Depends(require_roles(*READ)),
                    db: Session = Depends(get_db)):
    """Nhật ký các lần tác vụ tự động chạy. Có mã băm dữ liệu đầu vào để đối chiếu "chạy lại cùng dữ liệu
    phải ra cùng kết quả" – không có bảng này thì không kiểm toán được phần mềm đã tự làm những gì."""
    q = select(AiRunLog).order_by(AiRunLog.id.desc())
    if agent: q = q.where(AiRunLog.agent == agent)
    return [{"id": r.id, "agent": r.agent, "rule_version": r.rule_version, "thoi_diem": r.thoi_diem,
             "dau_vao_hash": r.dau_vao_hash[:16], "so_ban_ghi": r.so_ban_ghi, "so_co": r.so_co,
             "chay_boi": r.chay_boi, "loi": r.loi} for r in db.execute(q.limit(min(limit, 500))).scalars()]


@router.get("/lenh-dieu-xe")
def ds_lenh(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Lệnh điều xe kèm ghi vết gợi ý: máy đề xuất gì, người chọn gì, và lý do nếu chọn khác."""
    veh = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    out = []
    for d in db.execute(select(DispatchOrder).order_by(DispatchOrder.id.desc()).limit(300)).scalars():
        v = veh.get(d.vehicle_id)
        from app.models.core import Tour as _T
        t = db.get(_T, d.tour_id)
        out.append({"id": d.id, "tour": t.code if t else "", "xe": v.plate if v else "",
                    "ma_xe": v.code if v else "", "tai_xe": emps.get(d.driver_id, ""),
                    "date_from": d.date_from, "date_to": d.date_to,
                    "so_ngay": (d.date_to - d.date_from).days + 1, "internal_price": (d.internal_price or 0),
                    "status": d.status, "created_by": d.created_by, "confirmed_at": d.confirmed_at,
                    "theo_goi_y": bool(d.phuong_an_da_chon) and not d.ly_do_khac_goi_y,
                    "phuong_an_da_chon": d.phuong_an_da_chon, "ly_do_khac_goi_y": d.ly_do_khac_goi_y})
    return out


# ====================== SỔ CÔNG NỢ ĐỘI XE ======================
from app.models.fleet import DebtPayment, HUONG_TIEN
from app.services import fleet_debt as CN


@router.get("/cong-no")
def so_cong_no(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Sổ công nợ đội xe: bốn túi nợ để riêng, không cộng chung thành một con số."""
    return CN.so_cong_no(db)


@router.get("/cong-no/chu-xe/{partner_id}")
def cong_no_mot_chu_xe(partner_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Sổ chi tiết một chủ xe: từng kỳ, đã chốt hay chưa, đã trả bao nhiêu, còn lại bao nhiêu."""
    p = db.get(PartnerOwner, partner_id)
    if p is None: raise HTTPException(404, "Không có chủ xe này")
    d = CN.cong_no_chu_xe(db, p)
    d["thanh_toan"] = [{"id": x.id, "ngay": x.ngay.isoformat(), "huong": x.huong,
                        "huong_ten": HUONG_TIEN.get(x.huong, x.huong), "so_tien": x.so_tien,
                        "settlement_id": x.settlement_id, "chung_tu": x.chung_tu, "note": x.note,
                        "boi": x.created_by}
                       for x in db.execute(select(DebtPayment).where(DebtPayment.partner_id == partner_id)
                                           .order_by(DebtPayment.ngay.desc(), DebtPayment.id.desc())).scalars()]
    return d


class ThanhToanIn(BaseModel):
    huong: str
    so_tien: float
    ngay: date
    idem_key: str
    settlement_id: int | None = None
    sale_case_id: int | None = None
    partner_id: int | None = None
    chung_tu: str = ""
    note: str = ""


@router.post("/cong-no/thanh-toan", status_code=201)
def ghi_thanh_toan(data: ThanhToanIn, u: User = Depends(require_roles(*QT_DUYET)), db: Session = Depends(get_db)):
    """Ghi một lần trả/thu tiền trên công nợ đội xe.

    `idem_key` là bắt buộc và duy nhất ở cơ sở dữ liệu: bấm hai lần một nút, chạy lại một tác vụ, hay nhập
    lại từ sao kê đều không được thành hai lần trả."""
    if not (data.idem_key or "").strip():
        raise HTTPException(422, "Thiếu khóa chống lặp (idem_key) – không ghi tiền khi không chống được lặp")
    try:
        r = CN.ghi_thanh_toan(db, data.huong, data.so_tien, data.ngay, data.idem_key.strip(), u.username,
                              settlement_id=data.settlement_id, sale_case_id=data.sale_case_id,
                              partner_id=data.partner_id, chung_tu=data.chung_tu, note=data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if not r["lap_lai"]:
        R.audit(db, u.username, u.role, "thanh_toan_cong_no_xe", f"payment:{r['id']}",
                after=data.model_dump(mode="json"))
    db.commit()
    return r


# ====================== NẠP DỮ LIỆU THẬT TỪ BÁO CÁO NGOÀI ======================
class NhapChuyenIn(BaseModel):
    nguon: str = "bao_cao_vietrip"
    tao_xe_thieu: bool = False
    rows: list[dict]


@router.post("/chuyen/nhap-hang-loat", status_code=201)
def nhap_chuyen_hang_loat(data: NhapChuyenIn, u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd")),
                          db: Session = Depends(get_db)):
    """Nạp nhật trình chuyến từ báo cáo bên ngoài, khử trùng theo mã phiếu gốc.

    `tao_xe_thieu` mặc định TẮT: biển số không tra ra xe thì hệ thống báo ra chứ không tự tạo xe mới, vì một
    biển gõ sai mà tự tạo xe là từ đó số liệu của một chiếc chia làm hai chỗ."""
    if not data.rows: raise HTTPException(422, "Không có dòng nào để nạp")
    try:
        kq = FL.nhap_chuyen_hang_loat(db, data.nguon, data.rows, u.username, data.tao_xe_thieu)
    except (ValueError, TypeError) as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "nhap_chuyen_hang_loat", f"nguon:{data.nguon}",
            after={k: v for k, v in kq.items() if k != "chi_tiet"})
    db.commit()
    return kq


class PhanLoaiIn(BaseModel):
    source: str
    items: list[dict]                 # {ma_gd, nhom?, khong_phai_chi_phi?}


@router.post("/giao-dich/phan-loai")
def phan_loai_giao_dich(data: PhanLoaiIn, u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd")),
                        db: Session = Depends(get_db)):
    """Sửa lại NHÓM và cờ "không phải chi phí" của các dòng nguồn ngoài đã nạp.

    Cần có vì phân loại là việc của người đọc chứng từ, không phải của lần nạp đầu tiên: một khoản "nạp thẻ
    dầu 150 triệu" nhìn như chi phí nhiên liệu, nhưng thực chất là NẠP QUỸ – tiền dầu thật đã nằm ở phiếu
    chi phí của từng chuyến. Xếp nhầm là cộng đúp tiền dầu của cả tháng.

    Chỉ sửa hai cột phân loại. Số tiền, ngày và mã gốc KHÔNG sửa được ở đây – sửa số liệu gốc phải sửa ở
    nguồn rồi nạp lại, để hai bên còn đối chiếu được với nhau."""
    if data.source not in NGUON_NGOAI:
        raise HTTPException(422, f"Nguồn không hợp lệ. Chỉ nhận {', '.join(NGUON_NGOAI)}")
    theo_ma = {t.ma_gd: t for t in db.execute(
        select(ExternalTxn).where(ExternalTxn.source == data.source, ExternalTxn.trung == False)).scalars()}
    sua, khong_thay = 0, []
    for it in data.items:
        ma = (it.get("ma_gd") or "").strip()
        t = theo_ma.get(ma)
        if t is None:
            khong_thay.append(ma); continue
        if "nhom" in it: t.nhom = (it.get("nhom") or "")[:60]
        if "khong_phai_chi_phi" in it:
            t.khong_phai_chi_phi = bool(it["khong_phai_chi_phi"])
            if t.khong_phai_chi_phi and t.co == "do" and t.vehicle_id is None:
                t.co = "vang"
                t.ghi_chu = "Không phải chi phí kỳ này – không cần tra về xe"
        if it.get("ghi_chu"): t.ghi_chu = str(it["ghi_chu"])[:300]
        sua += 1
    R.audit(db, u.username, u.role, "phan_loai_giao_dich", f"nguon:{data.source}",
            after={"da_sua": sua, "khong_thay": khong_thay})
    db.commit()
    return {"da_sua": sua, "khong_tim_thay": khong_thay,
            "ghi_chu": "Chỉ sửa nhóm và cờ không-phải-chi-phí. Số tiền và ngày phải sửa ở nguồn rồi nạp lại."}


class DinhTuyenIn(BaseModel):
    """Định tuyến một hoặc nhiều giao dịch nguồn ngoài về một NGẢ."""
    ma_gd: list[str]
    nga: str
    ly_do: str = ""
    bien_so: str = ""                 # chỉ dùng cho ngả "xe": gắn luôn vào chiếc nào


@router.post("/giao-dich/dinh-tuyen")
def dinh_tuyen_giao_dich(data: DinhTuyenIn,
                         u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd")),
                         db: Session = Depends(get_db)):
    """Trả lời câu hỏi "khoản này chạy về đâu" cho một dòng nguồn ngoài.

    Vì sao cần một câu hỏi MỚI thay vì tra thêm cho ra xe: phiếu đề xuất chi trên Vietrip gắn vào
    TOUR và không có ô xe (khảo sát 05/9/2026, bộ trường: tour · NCC · hình thức TT · loại tiền ·
    dòng dịch vụ). Hỏi mãi "của xe nào" thì mỗi tháng lại một nắm dòng không ai trả lời được.

    Ba điều cửa này BẮT BUỘC, và cả ba đều vì ngả quyết định tiền vào sổ của ai:

      1. Ngả phải nằm trong danh mục. Chữ tự do thì ba tháng sau có "doi", "đội", "Đội xe" cùng một cột
         và không phép tính nào gom lại được — đúng chỗ cột `nhom` đang hỏng.
      2. Ngả "xe" phải quy được về MỘT CHIẾC. Nói "của xe" mà không nói xe nào là không nói gì.
      3. Phải có LÝ DO và tên người. Đây là một phán xét của người đọc chứng từ, không phải phép tính;
         ba tháng sau có người hỏi "vì sao khoản này là của đội" thì phải có câu trả lời tại chỗ.

    Cửa này KHÔNG tự cộng tiền vào báo cáo. Nó chỉ ghi ngả. Khoản của đội muốn vào ba tầng chi phí thì
    vẫn phải đi qua cửa "Chi phí kỳ của đội xe" — một khoản, một cửa, một lần; cộng ở hai đường là
    tính hai lần đúng một khoản."""
    if data.nga not in NGA_CHI_PHI:
        raise HTTPException(422, f"Ngả '{data.nga}' không có trong danh mục. "
                                 f"Chỉ nhận: {', '.join(NGA_CHI_PHI)}")
    if not (data.ly_do or "").strip():
        raise HTTPException(422, "Phải ghi lý do chọn ngả này – đây là phán xét của người đọc chứng "
                                 "từ, không phải phép tính, nên phải để lại căn cứ")
    if not data.ma_gd:
        raise HTTPException(422, "Không có dòng nào để định tuyến")
    v = None
    if data.nga == "xe":
        bien = (data.bien_so or "").strip()
        if not bien:
            raise HTTPException(422, "Ngả 'của một chiếc xe cụ thể' phải kèm biển số – nói 'của xe' "
                                     "mà không nói xe nào thì chưa trả lời câu hỏi")
        v = FL.xe_theo_bien(db, bien, date.today())
        if v is None:
            raise HTTPException(422, f"Không tra được xe nào từ biển '{bien}'")
    theo_ma = {t.ma_gd: t for t in db.execute(
        select(ExternalTxn).where(ExternalTxn.ma_gd.in_(data.ma_gd),
                                  ExternalTxn.trung == False)).scalars()}   # noqa: E712
    sua, khong_thay = [], []
    for ma in data.ma_gd:
        t = theo_ma.get((ma or "").strip())
        if t is None:
            khong_thay.append(ma); continue
        t.nga = data.nga
        t.nga_ly_do = data.ly_do.strip()[:300]
        t.nga_boi = u.username
        t.nga_luc = datetime.now()
        if data.nga == "khong_phai_chi_phi":
            t.khong_phai_chi_phi = True
        if v is not None and t.vehicle_id is None:
            t.vehicle_id = v.id
        sua.append(t.ma_gd)
    R.audit(db, u.username, u.role, "dinh_tuyen_giao_dich", f"nga:{data.nga}",
            after={"so_dong": len(sua), "nga": data.nga, "ly_do": data.ly_do[:200],
                   "xe": (v.plate if v is not None else ""), "khong_thay": khong_thay})
    db.commit()
    return {"da_dinh_tuyen": len(sua), "ma_gd": sua, "khong_tim_thay": khong_thay,
            "nga": data.nga, "nga_ten": NGA_CHI_PHI[data.nga],
            "ghi_chu": ("Đã ghi ngả. Khoản của ĐỘI muốn vào ba tầng chi phí của báo cáo lãi lỗ thì "
                        "vẫn phải nạp qua cửa 'Chi phí kỳ của đội xe' – một khoản một cửa, cộng ở "
                        "hai đường là tính hai lần.")}


@router.post("/giao-dich/tra-lai-xe")
def tra_lai_xe_giao_dich(source: str = "", u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd")),
                         db: Session = Depends(get_db)):
    """Tra lại xe theo biển số cho các dòng nguồn ngoài chưa gắn được xe. Xem services/fleet.py."""
    if source and source not in NGUON_NGOAI:
        raise HTTPException(422, f"Nguồn không hợp lệ. Chỉ nhận {', '.join(NGUON_NGOAI)}")
    kq = FL.tra_lai_xe(db, source)
    R.audit(db, u.username, u.role, "tra_lai_xe_giao_dich", f"nguon:{source or 'tat_ca'}",
            after={k: v for k, v in kq.items() if k != "dong"})
    db.commit()
    return kq


@router.post("/chuyen/tinh-lai-co")
def tinh_lai_co(tu: date | None = None, den: date | None = None,
                u: User = Depends(require_roles(*QT_WRITE, "chutich", "tgd")),
                db: Session = Depends(get_db)):
    """Tính lại cờ của các chuyến theo luật kiểm hiện hành. Xem services/fleet.py."""
    kq = FL.tinh_lai_co_chuyen(db, tu, den)
    R.audit(db, u.username, u.role, "tinh_lai_co_chuyen", f"tu:{tu}|den:{den}",
            after={k: v for k, v in kq.items() if k != "dong"})
    db.commit()
    return kq


class DeXuatChiIn(BaseModel):
    """Một đề xuất chi nhập tay trên VTOS – cùng bộ trường với phiếu đề xuất chi trên phần mềm Vietrip."""
    ngay: date
    so_tien: float
    noi_dung: str
    bien_so: str = ""                 # để trống = đề xuất chung, không thuộc xe nào
    nhom: str = ""
    khong_phai_chi_phi: bool = False
    nguoi_thu_huong: str = ""
    so_tai_khoan: str = ""
    ngan_hang: str = ""
    chung_tu: str = ""
    ma_gd: str = ""                   # để trống thì hệ thống tự sinh


@router.post("/de-xuat-chi", status_code=201)
def tao_de_xuat_chi(data: DeXuatChiIn, u: User = Depends(require_roles(*WRITE, *KETOAN, "chutich", "tgd")),
                    db: Session = Depends(get_db)):
    """Lập một đề xuất chi ngay trên VTOS, không phải nhập lại từ Vietrip.

    Hai điều bắt buộc, và đều là điều kiện để con số sau này còn dùng được:
      - Có NHÓM: "nạp thẻ dầu" và "sửa xe" nhìn giống nhau lúc lập phiếu nhưng một cái là nạp quỹ, một cái
        là chi phí. Không phân loại lúc lập thì cuối tháng phải đọc lại từng phiếu để đoán.
      - Số tiền lớn phải có chứng từ, đúng ngưỡng chặn cứng B6 đang áp cho chi phí chuyến.
    """
    if (data.so_tien or 0) <= 0: raise HTTPException(422, "Số tiền phải lớn hơn 0")
    if not (data.noi_dung or "").strip(): raise HTTPException(422, "Phải ghi nội dung đề xuất")
    if not (data.nhom or "").strip():
        raise HTTPException(422, "Phải chọn nhóm khoản chi – không phân loại lúc lập thì cuối tháng "
                                 "phải đọc lại từng phiếu để đoán khoản nào là chi phí, khoản nào là nạp quỹ")
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if (data.so_tien or 0) >= nguong and not (data.chung_tu or "").strip() and not data.khong_phai_chi_phi:
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc ghi số chứng từ gốc (chặn cứng B6)")

    ma = (data.ma_gd or "").strip()
    if not ma:
        n = db.execute(select(func.count(ExternalTxn.id))
                       .where(ExternalTxn.source == "de_xuat_vietrip")).scalar() or 0
        ma = f"VTOS-DX-{date.today():%Y%m}-{n + 1:04d}"
    tk = " · ".join(x for x in [data.nguoi_thu_huong, data.so_tai_khoan, data.ngan_hang] if x.strip())
    rows = [{"ma_gd": ma, "thoi_diem": f"{data.ngay}T00:00:00", "bien_so": data.bien_so,
             "so_tien": data.so_tien, "nhom": data.nhom,
             "khong_phai_chi_phi": data.khong_phai_chi_phi,
             "tai_khoan": data.so_tai_khoan[:40],
             "mo_ta": (data.noi_dung.strip() + (f" | Thụ hưởng: {tk}" if tk else ""))[:300]}]
    try:
        kq = FL.nhap_giao_dich(db, "de_xuat_vietrip", rows, u.username)
    except (ValueError, TypeError) as ex:
        raise HTTPException(422, f"Không ghi được đề xuất: {ex}")
    if kq["da_nhap"] == 0:
        raise HTTPException(422, f"Mã đề xuất {ma} đã tồn tại – đổi mã khác hoặc để trống cho hệ thống tự sinh")
    if (data.chung_tu or "").strip():
        t = db.execute(select(ExternalTxn).where(ExternalTxn.ma_gd == ma)).scalars().first()
        if t is not None: t.ghi_chu = (f"Chứng từ: {data.chung_tu.strip()} · " + (t.ghi_chu or ""))[:300]
    R.audit(db, u.username, u.role, "de_xuat_chi_xe", f"de_xuat:{ma}", after=data.model_dump(mode="json"))
    db.commit()
    return {"ma_gd": ma, "message": f"Đã lập đề xuất chi {ma} – {data.so_tien:,.0f} đ"}
