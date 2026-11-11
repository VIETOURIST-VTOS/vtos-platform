"""API nền dữ liệu đội xe Vietrip – Đợt 1 (đặc tả v1.3, 06/9/2026).

Mọi đường ở đây nằm dưới /api/v1/fleet/. Phân hệ Nhân sự đã có sẵn "/api/v1/vehicles" và "/api/v1/fleet/summary"
cho phần bảng lương – không đụng vào, để hai bên không tranh đường. Đường "/api/v1/fleet/summary" cũ vẫn thuộc
router Nhân sự; router này chỉ nhận các đường sâu hơn (/fleet/xe, /fleet/kiem-tra…).

Đổi biển, đổi quyền khai thác và đóng việc xác minh đều đi qua endpoint HÀNH ĐỘNG riêng, không có đường nào
nhận thẳng một cột trạng thái. Lý do: đổi biển không phải sửa một ô chữ, nó phải đóng dòng lịch sử cũ và mở
dòng mới trong cùng một giao dịch – để giữa chừng có lỗi thì không còn chiếc xe nào mang hai biển hiệu lực.
"""
import re
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles, robot_auth
from app.models.core import User, Company
from app.models.hr import Vehicle, Employee
from app.models.fleet import (VehiclePlate, VehicleDocument, FleetVerification, LIFECYCLE, OP_RIGHT,
                              DOC_KINDS, VEHICLE_DOCS, DRIVER_DOCS, VERIFY, VERIFY_STATUS)
from app.services import fleet as FL
from app.services import rules as R
from app.services import nhan_lenh as _NL

router = APIRouter(prefix="/api/v1/fleet", tags=["fleet"])

# Xem hồ sơ đội xe: Vận tải, Điều hành, Ban Giám đốc, Kế toán, BKS, CNTT, HCNS.
# "gd_doi_xe" mở 07/9/2026: Giám đốc điều hành đội xe phải đọc và ghi được chính phân hệ mình phụ trách.
# Trước đó ông mang chung vai trò với tài xế nên bị khoá ngoài, trong khi tham số xe_nguoi_lap_lenh lại chỉ
# định ông là người DUY NHẤT được lập lệnh điều xe – kết quả là không ai lập được lệnh.
READ = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt", "hcns", "gd_doi_xe")

# HAI CỬA ĐỌC HẸP HƠN `READ`, LẤY THẲNG TỪ MA TRẬN MÀN HÌNH.
#
# Vì sao phải có: `READ` mở cho cả 10 vai trò, nên trước bản này `GET /hieu-qua` trả số cho `cntt`,
# `nv_dh`, `ptgd_doan` – đúng những vai mà `MENU_ROLES` đã đóng. Phép thử `test_ma_tran_quyen.py::
# test_cntt_khong_xem_dong_tien_va_hieu_qua_doi_xe` khẳng định CNTT không xem được màn Hiệu quả đội xe,
# và nó vẫn XANH, vì nó chỉ kiểm menu. Giấu một màn hình khỏi menu không phải là đóng cửa: ai gọi thẳng
# API vẫn lấy được số. Hàng rào tiền tố `/api/v1/fleet` cũng không tách được `/hieu-qua` khỏi `/xe`.
#
# Vì sao SUY TỪ `MENU_ROLES` chứ không chép tay ra đây: chép là để hai nơi trôi khỏi nhau lần nữa – đúng
# cái vừa xảy ra. Suy ra thì sửa ma trận một chỗ là cửa API đổi theo, và `test_cua_doc_khop_ma_tran`
# canh cho chúng không bao giờ lệch.
def _vai_tro_cua_man(man: str) -> tuple:
    from app.services import access as AC
    return tuple(AC.MENU_ROLES[man])


XEM_HIEU_QUA = _vai_tro_cua_man("/hieu-qua-doi-xe")
XEM_LAI_LO = _vai_tro_cua_man("/lai-lo-doi-xe")
# KS-46 (08/11/2026) — bàn làm việc một màn của Giám đốc đội xe. Suy từ ma trận
# như hai dòng trên, KHÔNG chép tay danh sách vai: chép là để hai nơi trôi khỏi
# nhau lần nữa.
XEM_BAN_LAM_VIEC = _vai_tro_cua_man("/xe")
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
         "active": v.active, "source_note": v.source_note,
         # TK-1d: đơn giá ngày xe nhà — tạm tính tour đoàn dùng khi hành trình không trùng tuyến trong bảng giá xe
         "internal_rate_per_day": v.internal_rate_per_day, "phien_ban": v.phien_ban}
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
    internal_rate_per_day: float | None = None   # TK-1d: đơn giá ngày xe nhà (đ/ngày), Đội xe nhập


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
    if "internal_rate_per_day" in d and d["internal_rate_per_day"] is not None and not 0 <= d["internal_rate_per_day"] <= 1e9:
        raise HTTPException(422, "Đơn giá ngày không hợp lệ")
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
                              NGA_CHI_PHI, NGA_CUA_DOI_XE, TRA_BANG)

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
    # Đội xe v3.3 (Chủ tịch 10/11/2026): báo cáo xe nhập qua cửa bốn bước gửi `false` — chuyến CHƯA vào lợi
    # nhuận, vào khi Chủ tịch duyệt tờ quyết toán (`quyet_toan_chuyen.ky`, bước `tgd`). Cửa cũ không gửi gì
    # thì giữ như trước (KS-65: không đổi một đồng nào của sổ lịch sử).
    quyet_toan: bool = True


from app.models.fleet import QT_TRANG_THAI as _QT_TEN  # noqa: E402


def _chuyen_out(db: Session, t: Trip, veh: dict, emps: dict, kg: dict | None = None,
                cps: list | None = None) -> dict:
    # NHANH-1 (11/11/2026): danh sách chuyến truyền sẵn `cps` đọc MỘT lần cho cả trang — trước đó mỗi chuyến
    # một truy vấn (500 chuyến = 500 lượt hỏi CSDL, đo trên bản thật 1,2–1,6 giây). Gọi lẻ thì vẫn tự đọc.
    if cps is None:
        cps = list(db.execute(select(TripCost).where(TripCost.trip_id == t.id).order_by(TripCost.id)).scalars())
    if kg is None:
        from app.services import ops as _O
        kg = _O.de_nghi_theo_khoan_goc(db)
    return {"id": t.id, "vehicle_id": t.vehicle_id, "xe": veh.get(t.vehicle_id, ""),
            "driver_id": t.driver_id, "tai_xe": emps.get(t.driver_id, ""), "ten_tour": t.ten_tour, "ngay_di": t.ngay_di,
            "ngay_ve": t.ngay_ve, "so_ngay": (t.ngay_ve - t.ngay_di).days + 1,
            "km_dau": t.km_dau, "km_cuoi": t.km_cuoi, "km_gps": t.km_gps,
            "km_nguon": t.km_nguon, "km_nguon_ten": KM_NGUON.get(t.km_nguon, t.km_nguon or ""),
            "km_lech_gps": (abs((t.km_cuoi - t.km_dau) - t.km_gps) if
                            (t.km_dau is not None and t.km_cuoi is not None and t.km_gps) else None),
            "km_chay": (t.km_cuoi - t.km_dau) if (t.km_dau is not None and t.km_cuoi is not None) else None,
            "doanh_thu": t.doanh_thu, "status": t.status, "co": t.co, "co_ly_do": t.co_ly_do,
            "quyet_toan": t.quyet_toan,
            # v3.3 màn gọn: trạng thái tờ báo cáo xe (Đang nhập → Chờ Chủ tịch duyệt → Chờ Kế toán chi → …)
            "qt_trang_thai": t.qt_trang_thai or "nhap",
            "qt_ten_trang_thai": _QT_TEN.get(t.qt_trang_thai or "nhap", ""),
            "qt_tra_lai_ly_do": t.qt_tra_lai_ly_do or "",
            "note": t.note, "ma_phieu": t.ma_phieu, "nguon": t.nguon,
            "chi_phi": [{"id": c.id, "kind": c.kind, "kind_ten": COST_KINDS.get(c.kind, c.kind),
                         "amount": c.amount, "lit": c.lit, "ben_chiu": c.ben_chiu,
                         "ben_chiu_ten": BEN_CHIU.get(c.ben_chiu, c.ben_chiu), "chung_tu": c.chung_tu,
                         # `ben_chiu` tra loi AI GANH khoan nay khi quyet toan voi chu xe hop tac.
                         # `tra_bang` tra loi AI BO TIEN RA TAI CHO. Hai cau hoi khac nhau: xe cua
                         # Vietourist thi ben_chiu luon la Vietourist, nhung tien dau co the la tai
                         # xe ung tien mat, the cong ty, hay tru thang tai khoan (ePass). Mau 2 tach
                         # "TONG TAI XE CHI" voi "TONG CONG TY CHI" theo cau hoi THU HAI.
                         "tra_bang": c.tra_bang or "",
                         "tra_bang_ten": TRA_BANG.get(c.tra_bang or "", ""),
                         "nguon": c.nguon,
                         # Chống ghi hai lần (10/11/2026): khoản này đã là khoản gốc của đề nghị chi nào.
                         "de_nghi_chi": kg.get(f"tc:{c.id}")} for c in cps],
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
    from app.services import ops as _O
    kg = _O.de_nghi_theo_khoan_goc(db)
    trips = list(db.execute(q.limit(500)).scalars())
    cp_theo: dict[int, list] = {t.id: [] for t in trips}
    if trips:
        for c in db.execute(select(TripCost).where(TripCost.trip_id.in_(list(cp_theo))).order_by(TripCost.id)).scalars():
            cp_theo[c.trip_id].append(c)
    return [_chuyen_out(db, t, veh, emps, kg, cps=cp_theo[t.id]) for t in trips]


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
    # Vào vận hành (Chủ tịch duyệt 10/11/2026): phiếu gắn lệnh điều xe thì lệnh phải đúng xe, và MỘT lệnh MỘT
    # phiếu — lệnh đã có phiếu (kể cả phiếu tài xế ghi trên điện thoại) thì mở phiếu ấy, không lập phiếu thứ hai.
    if data.dispatch_id:
        from app.models.hr import DispatchOrder
        ld = db.get(DispatchOrder, data.dispatch_id)
        if ld is None or ld.status == "huy":
            raise HTTPException(422, "Lệnh điều xe không có hoặc đã huỷ")
        if ld.vehicle_id != data.vehicle_id:
            raise HTTPException(422, "Lệnh điều xe này của xe khác – chọn đúng xe của lệnh")
        cu = db.execute(select(Trip).where(Trip.dispatch_id == ld.id, Trip.status != "huy")).scalars().first()
        if cu is not None:
            raise HTTPException(422, f"Lệnh này đã có phiếu chuyến #{cu.id} – mở phiếu ấy, không lập phiếu thứ hai")
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
    tra_bang: str | None = None       # ai bo tien ra tai cho - de trong nghia la CHUA KHAI
    # VH-2: cửa bốn bước gửi `lit: null` cho mọi khoản không phải dầu — trước đây cả dòng bị từ chối 422 và
    # cầu đường / công tác phí / gửi xe không vào sổ. Rỗng = không có lít.
    lit: float | None = 0
    chung_tu: str = ""
    nguon: str = "nhap_tay"
    note: str = ""
    # Khai khi dòng này CHÍNH LÀ phiếu bảo dưỡng kia, để báo cáo không cộng một khoản hai lần.
    maintenance_id: int | None = None


@router.get("/san-sang-van-hanh")
def san_sang_van_hanh(ky: str | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Bảng sẵn sàng vận hành đội xe (Chủ tịch duyệt 10/11/2026) — luật ở `services/san_sang_doi_xe.py`."""
    from app.services import san_sang_doi_xe as SS
    if ky and not re.fullmatch(r"\d{4}-\d{2}", ky):
        raise HTTPException(422, "Kỳ phải dạng YYYY-MM")
    return SS.bang(db, ky)


@router.get("/lenh-cho-bao-cao")
def lenh_cho_bao_cao(xe_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Lệnh điều xe của MỘT xe để gắn vào báo cáo xe (bước 1 của cửa bốn bước — Chủ tịch duyệt 10/11/2026).

    Mỗi lệnh kèm phiếu chuyến đã có: phiếu tài xế đã gửi thì Giám đốc đội xe mở đúng phiếu ấy để kiểm và thêm
    doanh thu; phiếu đội xe đã lập thì không lập lại. Không trả giá thuê nội bộ — màn này không cần."""
    from app.models.hr import DispatchOrder
    from app.models.core import Tour
    hom = date.today()
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    ra = []
    for ld in db.execute(select(DispatchOrder).where(DispatchOrder.vehicle_id == xe_id, DispatchOrder.status != "huy",
                                                     DispatchOrder.date_from >= hom - timedelta(days=75),
                                                     DispatchOrder.date_from <= hom + timedelta(days=7))
                         .order_by(DispatchOrder.date_from.desc())).scalars():
        t = db.get(Tour, ld.tour_id) if ld.tour_id else None
        p = db.execute(select(Trip).where(Trip.dispatch_id == ld.id, Trip.status != "huy")).scalars().first()
        cps = list(db.execute(select(TripCost).where(TripCost.trip_id == p.id)).scalars()) if p else []
        ra.append({"id": ld.id, "tour_id": ld.tour_id, "tour": f"{t.code} · {t.name}" if t else "",
                   "driver_id": ld.driver_id, "tai_xe": emps.get(ld.driver_id, ""),
                   "date_from": ld.date_from, "date_to": ld.date_to, "da_nhan": ld.nhan_luc is not None,
                   "phieu": None if p is None else {
                       "id": p.id, "status": p.status, "tu_tai_xe": p.nguon == "tai_xe",
                       "tai_xe_da_gui": p.nguon == "tai_xe" and p.status != "nhap",
                       "km_dau": p.km_dau, "km_cuoi": p.km_cuoi, "doanh_thu": p.doanh_thu,
                       "phien_ban": p.phien_ban,
                       "khoan": [{"kind": c.kind, "so_tien": c.amount, "lit": c.lit} for c in cps]}})
    return {"rows": ra}


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
    if (data.tra_bang or "") and data.tra_bang not in TRA_BANG:
        raise HTTPException(422, f"Trả bằng không hợp lệ. Chỉ nhận {', '.join(TRA_BANG)}")
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if (data.amount or 0) >= nguong and not (data.chung_tu or "").strip():
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc có chứng từ gốc đính kèm (chặn cứng B6)")
    c = TripCost(trip_id=tid, **{**data.model_dump(exclude={"ben_chiu"}), "ben_chiu": bc,
                                 "tra_bang": data.tra_bang or "", "lit": data.lit or 0}, created_by=u.username)
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
    # Bật khi chuyến đang chạy đã quyết toán xong. Đi cùng đường sửa nhật trình, nên vẫn phải mở lại
    # chuyến (kèm lý do) mới đổi được — chốt một chuyến vào ô tiền là việc để lại dấu vết, không phải
    # một cú gạt công tắc lặng lẽ.
    quyet_toan: bool | None = None


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
             "doanh_thu": t.doanh_thu, "quyet_toan": t.quyet_toan, "driver_id": t.driver_id}
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


@router.post("/chuyen/{tid}/huy")
def huy_chuyen(tid: int, data: MoLaiIn, u: User = Depends(require_roles(*KETOAN, "chutich", "tgd", "tp_dh")),
               db: Session = Depends(get_db)):
    """Hủy một chuyến ghi nhầm. Bắt buộc có lý do.

    VÌ SAO HỦY CHỨ KHÔNG XÓA: chuyến đã có mã phiếu gốc, đã có dòng chi phí, có thể đã được ai đó đối
    chiếu. Xóa đi thì sổ hôm nay không khớp sổ hôm qua mà không còn dấu vết nào giải thích. Chuyến `huy`
    nằm lại trong cơ sở dữ liệu, giữ nguyên mã phiếu (nên nạp lại báo cáo cũ vẫn không sinh bản thứ hai),
    và bị loại khỏi MỌI ô tiền và ô đếm của báo cáo.

    Trước bản này `TRIP_STATUS` có khai giá trị "huy" nhưng không dòng mã nào gán nó – nên một chuyến gõ
    nhầm không có đường nào ra. Hai phiếu dò khuôn ZZPROBE-1/2 ngày 19/10/2026 còn nằm trong sổ vì thế.

    Cùng hàng rào với mở lại: kỳ quyết toán ĐÃ ĐÓNG thì không hủy ngược vào được."""
    t = db.get(Trip, tid)
    if not t: raise HTTPException(404, "Không có chuyến")
    if not (data.ly_do or "").strip():
        raise HTTPException(422, "Hủy một chuyến phải ghi lý do – một chuyến biến khỏi báo cáo mà không ai "
                                 "biết vì sao là cách nhanh nhất làm lãi lỗ tháng không đối chiếu được")
    if t.status == "huy":
        raise HTTPException(422, "Chuyến này đã hủy rồi")
    ky = f"{t.ngay_di:%Y-%m}"
    v = db.get(Vehicle, t.vehicle_id)
    if v is not None and v.partner_id:
        st = db.execute(select(Settlement).where(Settlement.ky == ky, Settlement.partner_id == v.partner_id,
                                                 Settlement.status == "dong_ky")).scalars().first()
        if st is not None:
            raise HTTPException(422, f"Kỳ {ky} của chủ xe đã ĐÓNG – hủy một chuyến đã quyết toán phải đi "
                                     "bằng dòng điều chỉnh ở kỳ sau")
    from datetime import datetime as _dt
    truoc = {"status": t.status, "doanh_thu": t.doanh_thu}
    t.status = "huy"
    t.note = (f"[Hủy {_dt.now():%d/%m %H:%M} bởi {u.username}: {data.ly_do.strip()}] " + (t.note or ""))[:300]
    R.audit(db, u.username, u.role, "huy_chuyen", f"trip:{tid}", before=truoc,
            after={"status": "huy", "ly_do": data.ly_do})
    db.commit()
    return {"id": t.id, "status": t.status,
            "message": "Đã hủy chuyến – chuyến vẫn nằm trong sổ kèm lý do, nhưng không còn vào báo cáo nào"}


class SuaChiPhiIn(BaseModel):
    amount: float | None = None
    lit: float | None = None
    ben_chiu: str | None = None
    tra_bang: str | None = None
    chung_tu: str | None = None
    note: str | None = None


@router.put("/chuyen/{tid}/chi-phi/{cid}")
def sua_chi_phi(tid: int, cid: int, data: SuaChiPhiIn,
                u: User = Depends(require_roles(*WRITE, *KETOAN, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Sửa một dòng chi phí của chuyến chưa xác nhận."""
    t = db.get(Trip, tid); c = db.get(TripCost, cid)
    if not t or not c or c.trip_id != tid: raise HTTPException(404, "Không có dòng chi phí này trong chuyến")
    if t.status == "da_xac_nhan": raise HTTPException(422, "Chuyến đã xác nhận – mở lại rồi mới sửa được")
    truoc = {"amount": c.amount, "lit": c.lit, "ben_chiu": c.ben_chiu, "tra_bang": c.tra_bang}
    d = data.model_dump(exclude_none=True)
    if "ben_chiu" in d and d["ben_chiu"] not in BEN_CHIU:
        raise HTTPException(422, f"Bên chịu không hợp lệ. Chỉ nhận {', '.join(BEN_CHIU)}")
    if d.get("tra_bang") and d["tra_bang"] not in TRA_BANG:
        raise HTTPException(422, f"Trả bằng không hợp lệ. Chỉ nhận {', '.join(TRA_BANG)}")
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
def xoa_chi_phi(tid: int, cid: int, ly_do: str = "",
                u: User = Depends(require_roles(*WRITE, *KETOAN, "chutich", "tgd")),
                db: Session = Depends(get_db)):
    """Xóa một dòng chi phí nhập nhầm, chỉ khi chuyến chưa xác nhận. Bắt buộc ghi lý do.

    Lý do là bắt buộc vì đây là cùng một loại hành vi với `DELETE /chi-phi-ky/{cid}`, `mo-lai` và
    `go-khoi-theo-doi` – những cửa đã đòi lý do từ đầu. Trước bản này riêng cửa này không đòi, nên một
    khoản chi phí có thể biến khỏi báo cáo mà nhật ký chỉ ghi được SỐ đã xóa, không ghi được VÌ SAO."""
    t = db.get(Trip, tid); c = db.get(TripCost, cid)
    if not t or not c or c.trip_id != tid: raise HTTPException(404, "Không có dòng chi phí này trong chuyến")
    if not ly_do.strip(): raise HTTPException(422, "Xóa một dòng chi phí phải ghi lý do")
    if t.status == "da_xac_nhan": raise HTTPException(422, "Chuyến đã xác nhận – mở lại rồi mới xóa được")
    R.audit(db, u.username, u.role, "xoa_chi_phi_chuyen", f"trip:{tid}",
            before={"kind": c.kind, "amount": c.amount, "lit": c.lit, "ben_chiu": c.ben_chiu,
                    "chung_tu": c.chung_tu}, after={"ly_do": ly_do})
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
                      # KS-64 · 09/11/2026 — `mo_ta` TRƯỚC NAY KHÔNG ĐƯỢC TRẢ RA.
                      #
                      # Nó vẫn được lưu (`nhap_giao_dich` ghi `mo_ta=r.get("mo_ta","")`), nhưng
                      # dòng trả về của cửa này bỏ sót, nên NỘI DUNG mà người lập đề xuất gõ vào
                      # — tiền này chi cho việc gì — chưa bao giờ hiện trên màn Đối soát. Màn hình
                      # có mã phiếu, số tiền, nhóm và ghi chú của máy, thiếu đúng câu của con người.
                      #
                      # Dấu vết: phép thử cũ `test_lap_de_xuat_chi_tren_vtos` viết
                      # `assert "Năm Tuội" in dong["mo_ta"] if "mo_ta" in dong else True` — một lối
                      # lui để phép thử khỏi đỏ, và nó đã che chỗ này suốt từ đó.
                      "mo_ta": t.mo_ta,
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
            "nguoi_lap_lenh_ghi_chu": ly_do,
            # KS-64: ngưỡng chứng từ bắt buộc (chặn cứng B6) trả về cho màn hình, để bước 2 của
            # hai cửa nhập bốn bước BÁO TRƯỚC bằng đúng con số đang áp — thay vì để người gõ đi
            # hết bốn bước rồi mới bị máy chủ từ chối ở lần bấm Gửi.
            #
            # Trả từ máy chủ chứ KHÔNG gõ lại số 10.000.000 trong mã web: gõ lại là ngày nào đó
            # ai sửa tham số trên màn Chính sách & định mức, còn màn hình vẫn báo con số cũ, và
            # hai bên nói hai điều khác nhau về cùng một hàng rào.
            "nguong_chung_tu": R.get_param(db, "xe_chung_tu_bat_buoc_tu")}


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
def lai_lo(ky: str, phan_bo: str = "khong", u: User = Depends(require_roles(*XEM_LAI_LO)),
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
def lai_lo_chuyen(ky: str, u: User = Depends(require_roles(*XEM_LAI_LO)), db: Session = Depends(get_db)):
    """Quyết toán theo TOUR: mỗi chuyến một dòng kèm lãi gộp và suất tiêu hao của chính chuyến đó."""
    try:
        QT.ky_range(ky)
    except Exception:
        raise HTTPException(422, "Kỳ phải có dạng YYYY-MM")
    return LL.theo_chuyen(db, ky)


@router.get("/chi-phi-ky")
def chi_phi_ky(ky: str = "", u: User = Depends(require_roles(*XEM_LAI_LO)), db: Session = Depends(get_db)):
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
    """Ghi một khoản chi phí kỳ (bảo hiểm, lương tài xế, phí bãi, lãi vay…).

    Lãi vay nhập qua đúng cửa này, nhưng nó không vào giá vốn: `NGOAI_GIA_VON` trong mô hình quyết
    điều đó, không phải ô người nhập (Chủ tịch quyết 11/10/2026).
    """
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
    # CHẶN CỨNG B6 CŨNG ÁP Ở ĐÂY. Trước bản này ngưỡng chứng từ chỉ áp cho chi phí CHUYẾN và đề nghị chi,
    # còn sổ chi phí kỳ nhận `chung_tu` như chuỗi tự do không ai kiểm – trong khi đây đúng là chỗ ghi
    # những khoản lớn nhất của đội xe: bảo hiểm, bảo dưỡng, bãi xe, lãi vay.
    #
    # ĐẶT SAU chốt chống nhân đôi, cố ý: người nhập lại đúng bảng tháng lần thứ hai cần nghe "khoản này
    # đã có rồi", không phải "thiếu chứng từ". Báo sai lý do thì họ đi tìm chứng từ rồi nhập lại lần nữa.
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if (data.so_tien or 0) >= nguong and not (data.chung_tu or "").strip():
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc có chứng từ gốc đính kèm "
                                 "(chặn cứng B6)")
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
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if (data.so_tien or 0) >= nguong and not (data.chung_tu or "").strip():
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc có chứng từ gốc đính kèm "
                                 "(chặn cứng B6)")
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
def hieu_qua(ky: str, u: User = Depends(require_roles(*XEM_HIEU_QUA)), db: Session = Depends(get_db)):
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


@router.get("/ban-lam-viec")
def ban_lam_viec(ky: str = "", u: User = Depends(require_roles(*XEM_BAN_LAM_VIEC)),
                 db: Session = Depends(get_db)):
    """MỘT cửa cho cả màn `/xe`: hàng đợi việc, số kỳ, xe hôm nay, diễn biến.

    Vì sao một cửa chứ không bốn: bốn cửa thì bốn lần chờ, và bốn cơ hội để hai
    vùng trên cùng một màn nói hai con số khác nhau.

    `ky` phải đủ dạng YYYY-MM. Đây đúng chỗ đã gây lỗi trên màn Lãi lỗ: giao diện
    gửi giá trị tháng gõ dở, máy chủ nhận bừa rồi trả số của một kỳ khác (gõ
    «102026» ra kỳ 2026-01 với 796.985.460 đ). Nhận bừa một lần là người đọc tin
    một con số không thuộc kỳ nào.
    """
    from app.services import ban_lam_viec_xe as BLV
    ky = ky or date.today().strftime("%Y-%m")
    try:
        QT.ky_range(ky)
    except Exception:
        raise HTTPException(422, "Kỳ phải có dạng YYYY-MM")
    # Quyền GHI vẫn do từng cửa chặn riêng; ở đây chỉ nói cho giao diện biết nút
    # nào vẽ được. Ẩn nút KHÔNG phải là kiểm soát quyền — máy chủ vẫn chặn thật.
    quyen = {"quyet_toan": u.role in QT_WRITE, "ghi_chi_phi_ky": u.role in QT_WRITE,
             "ghi_bao_duong": u.role in WRITE, "duyet_de_xuat": False}
    return BLV.ban_lam_viec(db, ky, quyen) | {"vai": u.role, "quyen": quyen,
                                              "chi_xem": not quyen["ghi_chi_phi_ky"]}


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
                    "phuong_an_da_chon": d.phuong_an_da_chon, "ly_do_khac_goi_y": d.ly_do_khac_goi_y,
                    # DL-5 · 15/10/2026: màn hình gửi lại con số này khi đổi xe. Thiếu nó thì màn
                    # hình gửi `undefined`, `kiem_phien_ban` cho qua theo đúng luật "chưa gửi thì
                    # không chặn", và khoá chống ghi đè tắt lặng lẽ – đúng kiểu báo an toàn giả.
                    "phien_ban": d.phien_ban,
                    # VH-3: màn gọn «Lập lệnh» cho thấy tài xế đã bấm nhận chưa và hạn nhận.
                    "trang_thai_nhan": _NL.trang_thai_nhan(d), "nhan_luc": d.nhan_luc,
                    "han_nhan": _NL.han_nhan(d)})
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
    """Một đề xuất chi nhập tay trên VTOS – cùng bộ trường với phiếu đề xuất chi trên phần mềm Vietrip.

    KS-64 · 09/11/2026 — thêm sáu trường của bản v3.3 (bốn bước). Chúng khai ở ĐÂY chứ không
    chỉ ở màn hình, vì pydantic BỎ LẶNG LẼ trường lạ: một ô trên giao diện gửi lên tên trường
    máy chủ không biết thì người gõ thấy mình đã khai, mà sổ không có gì cả. Đó là loại sai
    không ai phát hiện được — không có thông báo đỏ ở đâu hết.

    Sáu trường này KHÔNG thêm bảng, KHÔNG thêm cột: chúng đi vào `mo_ta` và `ghi_chu` của dòng
    `ExternalTxn` đang có, và vào nhật ký `audit` dưới dạng đầy đủ.
    """
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
    # ── v3.3 bước 1 ──
    pham_vi: str = ""                 # "xe" = chi phí một xe · "doi" = chi phí toàn đội
    loai: str = ""                    # thanh_toan | tam_ung | hoan_ung
    # ── v3.3 bước 2 ──
    can_cu_so_tien: str = ""          # §2 "không tự cộng VAT": người lập phải NÓI RA căn cứ
    ma_khoan_goc: str = ""            # WF06 – liên kết khoản đã ghi ở phiếu chuyến, chống cộng hai lần
    hen_bo_sung: str = ""             # lý do + thời hạn, khi gửi mà chứng từ chưa về
    ghi_chu_kiem_tra: str = ""        # ghi chú gửi người kiểm tra
    # ── bước 4 ──
    cho_phep_trung: bool = False      # chỉ đặt True khi người lập đã xem phiếu trùng và vẫn muốn gửi


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỘI XE v3.3 · ĐỀ XUẤT CHI ĐI VÀO ĐỀ NGHỊ CHI 05-TT — Chủ tịch chốt 10/11/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Màn bốn bước của GĐ đội xe lập ở ĐÂY. Phiếu là một đề nghị chi loại `chi_doi_xe` (services/ops.py):
# cùng mã DC…, cùng hàng đợi Kế toán, cùng mốc duyệt chung, cùng luật người lập không tự ký. Không có
# bảng phiếu riêng và không có mốc duyệt riêng của đội xe (tài liệu v3.3 mục 3).
#
# Cửa cũ `POST /de-xuat-chi` ngay dưới GIỮ NGUYÊN: nó là cửa ghi một dòng ĐỐI CHIẾU nguồn ngoài, không
# phải cửa lập phiếu nữa — màn bốn bước thôi gọi nó.
LOAI_CHI_XE = ("chi_doi_xe", "sua_chua_xe", "tam_ung_tai_xe")


class DeNghiChiXeIn(BaseModel):
    so_tien: float
    ngay: date | None = None              # ngày cần xử lý → ngày đến hạn của đề nghị chi
    noi_dung: str
    nguoi_thu_huong: str
    ma_so_thue: str = ""
    chung_tu: str = ""
    pham_vi: str = "xe"
    bien_so: str = ""
    loai: str = "thanh_toan"
    nhom: str = ""
    can_cu_so_tien: str = ""
    ma_khoan_goc: str = ""
    hen_bo_sung: str = ""
    ghi_chu_kiem_tra: str = ""
    cho_phep_trung: bool = False
    so_tai_khoan: str = ""                # vai GĐ đội xe gửi ô này là bị từ chối (services/ops.py)
    ngan_hang: str = ""


@router.post("/de-nghi-chi", status_code=201)
def lap_de_nghi_chi_xe(data: DeNghiChiXeIn, u: User = Depends(require_roles("gd_doi_xe", "cntt")),
                       db: Session = Depends(get_db)):
    from app.services import ops as O
    if (data.so_tien or 0) <= 0: raise HTTPException(422, "Số tiền phải lớn hơn 0")
    if not (data.noi_dung or "").strip(): raise HTTPException(422, "Phải ghi nội dung đề xuất")
    # Ngưỡng chứng từ bắt buộc của đội xe (chặn cứng B6) — giữ y như cửa cũ. Tạm ứng / nạp quỹ không có
    # hóa đơn lúc lập, nên không áp.
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if ((data.so_tien or 0) >= nguong and not (data.chung_tu or "").strip() and data.loai == "thanh_toan"
            and not data.nhom.startswith("Nạp quỹ")):
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc ghi số chứng từ gốc (chặn cứng B6)")
    # VH-21 · Chủ tịch chốt 11/11/2026: số đề nghị KHÔNG ĐƯỢC VƯỢT khoản gốc đã gắn. Thử thật DC2611-0001: xin
    # 630.000 mà khoản gốc (công tác phí) chỉ 600.000 — 30.000 gửi xe đi kèm không có khoản gốc nào đứng sau.
    # Đặt ở cửa này chứ không ở `services/ops.py` vì tệp ấy đang do làn TC-KT giữ chỗ (TT-TBS).
    kg = O.khoan_goc(db, data.ma_khoan_goc) if (data.ma_khoan_goc or "").strip() else None
    _xe = db.execute(select(Vehicle).where(Vehicle.plate == (data.bien_so or "").strip())).scalars().first()
    if kg and _xe is not None and kg["vehicle_id"] != _xe.id:
        kg = None                  # khoản gốc của xe khác: để `services/ops.py` báo đúng lỗi «xe khác»
    if kg and float(kg["so_tien"] or 0) > 0 and (data.so_tien or 0) > float(kg["so_tien"]) + 0.5:
        raise HTTPException(422, f"Số đề nghị {data.so_tien:,.0f} đ vượt khoản gốc {kg['ten']} "
                                 f"({float(kg['so_tien']):,.0f} đ). Mỗi đề nghị chi chỉ chi tối đa đúng khoản gốc "
                                 "đã gắn — phần còn lại lập phiếu riêng gắn khoản của nó.")
    ngan = " · ".join(x.strip() for x in (data.so_tai_khoan, data.ngan_hang) if x.strip())
    try:
        r = O.create_request(db, u, {
            "category": "chi_doi_xe", "supplier_name": data.nguoi_thu_huong.strip()[:160],
            "supplier_tax_code": data.ma_so_thue.strip()[:20], "supplier_bank": ngan[:120],
            "amount": data.so_tien, "description": data.noi_dung.strip()[:300],
            "has_document": bool(data.chung_tu.strip()), "document_ref": data.chung_tu.strip()[:120],
            "ngay_den_han": data.ngay, "cho_phep_trung": data.cho_phep_trung,
            "doi_xe": {"pham_vi": data.pham_vi, "bien_so": data.bien_so, "loai": data.loai, "nhom": data.nhom,
                       "can_cu": data.can_cu_so_tien, "ma_khoan_goc": data.ma_khoan_goc,
                       "hen_bo_sung": data.hen_bo_sung, "ghi_chu_kiem_tra": data.ghi_chu_kiem_tra}})
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    ai = O.cap_duyet(db, r)["ai"]
    # Chống ghi hai lần (10/11/2026): cùng số chứng từ ở đề nghị chi khác → CẢNH BÁO (không chặn).
    trung = O.chung_tu_trung(db, r.document_ref, r.id)
    return {"id": r.id, "code": r.code, "status": r.status, "chung_tu_trung": trung,
            "message": f"Đã gửi {r.code} — chờ {ai} duyệt, rồi Kế toán kiểm chứng từ và chi"
                       + (f". Lưu ý: số chứng từ {r.document_ref} đã có ở {', '.join(trung)}" if trung else "")}


@router.get("/khoan-goc")
def ds_khoan_goc(xe_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách khoản đã ghi của MỘT xe để chọn làm «khoản gốc» của đề xuất chi (Chủ tịch duyệt 10/11/2026):
    dòng chi phí chuyến và phiếu bảo dưỡng / sửa chữa, kèm đề nghị chi đã gắn — khoản đã có đề nghị chi thì
    màn hình hiện mã DC và không cho chọn lại."""
    from app.services import ops as O
    da = O.de_nghi_theo_khoan_goc(db)
    ra = []
    for c, t in db.execute(select(TripCost, Trip).join(Trip, Trip.id == TripCost.trip_id)
                           .where(Trip.vehicle_id == xe_id).order_by(Trip.ngay_di.desc(), TripCost.id.desc())
                           .limit(120)).all():
        ma = f"tc:{c.id}"
        ra.append({"ma": ma, "loai": "Chi phí chuyến", "ngay": t.ngay_di,
                   "ten": f"{t.ma_phieu or 'Chuyến ' + str(t.id)} · {COST_KINDS.get(c.kind, c.kind)}",
                   "so_tien": c.amount, "chung_tu": c.chung_tu or "", "de_nghi_chi": da.get(ma)})
    for b in db.execute(select(Maintenance).where(Maintenance.vehicle_id == xe_id)
                        .order_by(Maintenance.ngay.desc()).limit(60)).scalars():
        ma = f"bd:{b.id}"
        ra.append({"ma": ma, "loai": "Bảo dưỡng / sửa chữa", "ngay": b.ngay, "ten": (b.noi_dung or b.kind)[:80],
                   "so_tien": b.so_tien, "chung_tu": b.chung_tu or "", "de_nghi_chi": da.get(ma)})
    return {"rows": ra}


@router.get("/de-nghi-chi")
def ds_de_nghi_chi_xe(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách đề nghị chi CỦA ĐỘI XE — cùng một nguồn cho nút tạo mới, thanh con «Đề xuất chi» và hồ sơ xe
    (tài liệu v3.3 mục 1). Chỉ ba loại chi của đội xe; không mở sổ chi của phòng khác cho vai đội xe."""
    from app.models.ops import PaymentRequest
    from app.services import ops as O
    BUOC = {"cho_tp": "Chờ bộ phận xác nhận", "cho_kt": "Kế toán kiểm", "cho_duyet": "Chờ ký lệnh chi",
            "cho_chi": "Chờ Kế toán chi", "da_chi": "Đã chi", "tu_choi": "Từ chối",
            "tra_bo_sung": "Trả bổ sung — sửa rồi gửi lại"}
    ds = db.execute(select(PaymentRequest).where(PaymentRequest.category.in_(LOAI_CHI_XE))
                    .order_by(PaymentRequest.id.desc()).limit(200)).scalars().all()
    ra = []
    for r in ds:
        x = r.doi_xe or {}
        buoc = BUOC.get(r.status, r.status)
        if r.status == "cho_duyet":
            buoc = f"Chờ {O.cap_duyet(db, r)['ai'] or 'chốt mốc'} ký"
        if r.status == "cho_chi" and (r.da_chi_tien or 0) > 0:
            buoc = f"Đã chi một phần {float(r.da_chi_tien or 0):,.0f} đ"
        ra.append({"id": r.id, "code": r.code, "loai_chi": r.category, "ngay": r.created_at.date().isoformat() if r.created_at else None,
                   "noi_dung": r.description, "ben_nhan": r.supplier_name, "so_tien": r.amount,
                   "bien_so": x.get("bien_so") or "", "pham_vi": x.get("pham_vi") or "", "nhom": x.get("nhom") or "",
                   "loai": O.LOAI_DOI_XE.get(x.get("loai") or "", ""), "trang_thai": r.status, "buoc": buoc,
                   "ly_do_tu_choi": r.reject_reason or "", "nguoi_lap": r.created_by,
                   "da_chi_tien": float(r.da_chi_tien or 0), "ma_so_thue": r.supplier_tax_code or "",
                   "can_cu": x.get("can_cu") or "",
                   **_dxc_chi_tiet(db, u, r, x)})
    # VH-23: danh mục hình thức thanh toán cho ô «Đã chi» của Kế toán ngay trên màn /xe — cùng bảng tĩnh
    # mà /expenses đọc qua `/hach-toan/bang`; trả kèm ở đây để màn /xe không phải gọi sang nhóm khác.
    from app.models.hach_toan import HINH_THUC_TT
    return {"de_nghi": ra, "hinh_thuc_tt": HINH_THUC_TT if u.role in O.VAI_GHI_DA_CHI else {}}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# VH-23 · ĐỀ XUẤT CHI ĐỘI XE BẢN 2, ĐỢT 1 (Chủ tịch duyệt bản xem trước 12/11/2026 00:04).
#
# Một màn trong /xe cho cả người lập (GĐ đội xe), người ký (Chủ tịch) và người chi (Kế toán). Hai luật:
#   · NÚT DO MÁY CHỦ TRẢ (`viec`). Màn hình chỉ vẽ đúng các việc này — không tự suy vai nào bấm được gì.
#     Máy chủ vẫn chặn thật ở `services/ops.py::step`; `viec` chỉ để không vẽ ra một nút bấm vào là lỗi
#     và không giấu đi một nút đáng lẽ phải có (bài học F1, 10/10/2026).
#   · KIỂM HIỆN RA (`kiem`): những gì máy đã soát, xanh / đỏ / vàng, để người ký đọc trước khi ký.
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _dxc_chi_tiet(db: Session, u: User, r, x: dict) -> dict:
    from app.services import ops as O
    viec: list[list[str]] = []
    st, chi = r.status, float(r.da_chi_tien or 0)
    if st == "cho_duyet":
        if u.role in O.vai_ky_duoc(db, r) and u.username != r.created_by:
            viec.append(["approve", "Ký lệnh chi"])
        if O._ai_tra_duoc(db, u, r):
            viec.append(["tra_bo_sung", "Trả bổ sung"])
    if st == "cho_chi":
        if u.role in O.VAI_GHI_DA_CHI:
            viec.append(["pay", "Đã chi"])
        if chi <= 0 and O._ai_tra_duoc(db, u, r):
            viec.append(["tra_bo_sung", "Trả bổ sung"])
    if st not in ("da_chi", "tu_choi") and chi <= 0 and u.role in ("chutich", "tgd", "ketoan") \
            and (st != "cho_chi" or u.role == "ketoan") and u.username != r.created_by:
        viec.append(["reject", "Từ chối"])
    if st == "tra_bo_sung" and u.username == r.created_by:
        viec.append(["gui_lai", "Bổ sung & gửi lại"])
    # ── máy đã kiểm ──
    kiem: list[dict] = []
    # Tệp THẬT trong kho «de_xuat_chi_xe», không phải một số chứng từ gõ tay: người ký cần nhìn thấy giấy.
    co_tep = O.co_tep_doi_xe(db, r)
    if co_tep:
        kiem.append({"muc": "ok", "chu": "Đã đính tệp chứng từ"})
    else:
        kiem.append({"muc": "vang", "chu": (f"Có số chứng từ «{r.document_ref}» nhưng chưa đính tệp chứng từ"
                                            if (r.document_ref or "").strip() else "Chưa đính tệp chứng từ")
                     + " — người ký chưa nhìn thấy giấy"})
    kg_ma = (x.get("ma_khoan_goc") or "").strip()
    kg = O.khoan_goc(db, kg_ma) if kg_ma else None
    if kg:
        goc = float(kg["so_tien"] or 0)
        xin = float(r.amount or 0)
        if goc > 0 and xin > goc + 0.5:
            kiem.append({"muc": "do", "chu": f"Xin {xin:,.0f} đ, khoản gốc gắn chỉ {goc:,.0f} đ — vượt "
                                            f"{xin - goc:,.0f} đ (luật VH-21: không chi vượt khoản gốc)"})
        else:
            kiem.append({"muc": "ok", "chu": f"Số tiền khớp khoản gốc {kg['ten']} ({goc:,.0f} đ)"})
    elif x.get("loai") != "tam_ung" and not (x.get("nhom") or "").startswith("Nạp quỹ"):
        kiem.append({"muc": "vang", "chu": "Không gắn khoản gốc — máy không đối chiếu được với phiếu chuyến / bảo dưỡng"})
    trung = O.chung_tu_trung(db, r.document_ref, r.id) if (r.document_ref or "").strip() else []
    if trung:
        kiem.append({"muc": "vang", "chu": f"Số chứng từ {r.document_ref} cũng có ở {', '.join(trung)}"})
    can_mst = x.get("loai") == "thanh_toan" and (x.get("nhom") or "") not in O.NHOM_DOI_XE_KHONG_MST
    if can_mst and not (r.supplier_tax_code or "").strip():
        kiem.append({"muc": "vang", "chu": "Bên nhận chưa có mã số thuế — Kế toán cần trước khi chi"})
    if r.created_by and r.approved_by and r.created_by == r.approved_by:
        kiem.append({"muc": "do", "chu": "Người lập trùng người ký"})
    return {"viec": viec, "kiem": kiem, "can_mst": can_mst, "chung_tu": r.document_ref or "",
            "co_tep": co_tep, "co_unc": O.co_unc(db, r) if st == "cho_chi" else None,
            "con_phai_chi": max(0.0, float(r.amount or 0) - chi),
            "khoan_goc": ({"ma": kg_ma, "ten": kg["ten"], "so_tien": float(kg["so_tien"] or 0)} if kg else None),
            "ghi_chu_kiem_tra": x.get("ghi_chu_kiem_tra") or "", "hen_bo_sung": x.get("hen_bo_sung") or "",
            "luc_lap": r.created_at.isoformat() if r.created_at else None,
            "tuyen": [b for b in (
                {"buoc": "Lập", "nguoi": r.created_by, "luc": r.created_at.isoformat() if r.created_at else None},
                {"buoc": "Ký lệnh chi", "nguoi": r.approved_by or "", "luc": r.approved_at.isoformat() if r.approved_at else None},
                {"buoc": "Đã chi", "nguoi": "", "luc": r.paid_at.isoformat() if getattr(r, "paid_at", None) else None})]}


class BuocDxcIn(BaseModel):
    action: str
    reason: str = ""
    hinh_thuc_tt: str = ""
    so_tien: float | None = None


@router.post("/de-nghi-chi/{rid}/buoc")
def buoc_de_nghi_chi_xe(rid: int, data: BuocDxcIn, u: User = Depends(require_roles(*READ)),
                        db: Session = Depends(get_db)):
    """VH-23 · Ký / trả bổ sung / từ chối / ghi đã chi một đề xuất chi đội xe NGAY TRÊN màn /xe. Cửa mỏng: chỉ
    nhận ba loại chi của đội xe, rồi gọi ĐÚNG hàm bước của đề nghị chi (`services/ops.py::step`) — mọi luật
    (ai ký, tách người, UNC trước «Đã chi», kiểm chứng từ và MST) vẫn nằm một chỗ ở đó."""
    from app.models.ops import PaymentRequest
    from app.services import ops as O
    r = db.get(PaymentRequest, rid)
    if r is None or r.category not in LOAI_CHI_XE:
        raise HTTPException(404, "Không có đề xuất chi đội xe này")
    if data.action not in ("approve", "tra_bo_sung", "reject", "pay"):
        raise HTTPException(422, "Việc không hợp lệ")
    try:
        msg = O.step(db, u, r, data.action, data.reason, data.hinh_thuc_tt, data.so_tien)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": msg, "trang_thai": r.status}


class GuiLaiXeIn(BaseModel):
    so_tien: float | None = None
    noi_dung: str | None = None
    nguoi_thu_huong: str | None = None
    ma_so_thue: str | None = None
    can_cu: str | None = None
    hen_bo_sung: str | None = None


@router.post("/de-nghi-chi/{rid}/gui-lai")
def gui_lai_de_nghi_chi_xe(rid: int, data: GuiLaiXeIn, u: User = Depends(require_roles("gd_doi_xe", "cntt")),
                           db: Session = Depends(get_db)):
    """GĐ đội xe sửa đề nghị chi bị «Trả bổ sung» rồi gửi lại (Chủ tịch duyệt 10/11/2026). Cửa riêng của đội
    xe vì vai đội xe không có màn Đề nghị chi chung; luật nằm MỘT chỗ ở `services/ops.py::gui_lai`."""
    from app.models.ops import PaymentRequest
    from app.services import ops as O
    r = db.get(PaymentRequest, rid)
    if not r or r.category not in LOAI_CHI_XE:
        raise HTTPException(404, "Không có đề nghị chi của đội xe")
    d = data.model_dump(exclude_unset=True)
    vao = {k2: d[k1] for k1, k2 in (("so_tien", "amount"), ("noi_dung", "description"),
                                     ("nguoi_thu_huong", "supplier_name"), ("ma_so_thue", "supplier_tax_code"))
           if k1 in d}
    dx = {k: d[k] for k in ("can_cu", "hen_bo_sung") if k in d}
    if dx:
        vao["doi_xe"] = dx
    try:
        msg = O.gui_lai(db, u, r, vao)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": msg + " — chờ Chủ tịch duyệt", "id": r.id, "status": r.status}


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

    # ── KS-64 · B6 của bản v3.3 — Ô NGÂN HÀNG KHÔNG THUỘC VAI GIÁM ĐỐC ĐỘI XE ──
    #
    # v3.3 §2 và §7: "GĐ đội xe không nhập hoặc thay tài khoản ngân hàng tùy ý trong màn đề nghị",
    # và ma trận quyền ghi "Đổi thông tin ngân hàng — không theo vai GĐ".
    #
    # Chặn ở ĐÂY, không chỉ ẩn ô trên màn hình. Ẩn nút là một lời đề nghị, không phải một hàng
    # rào: ai cũng gọi thẳng được cửa này bằng một dòng fetch. Một kiểm soát chi tiền mà chỉ
    # sống ở lớp giao diện thì nó không tồn tại.
    #
    # Người thụ hưởng VẪN ghi được — v3.3 giữ ô "Bên nhận / nhà cung cấp" cho GĐ. Cái bị lấy ra
    # khỏi tay GĐ là SỐ TÀI KHOẢN và NGÂN HÀNG: hai thứ quyết định tiền chạy vào đâu.
    if u.role == "gd_doi_xe" and ((data.so_tai_khoan or "").strip() or (data.ngan_hang or "").strip()):
        raise HTTPException(422, "Số tài khoản và ngân hàng của bên nhận do Kế toán kiểm soát, không nhập "
                                 "ở màn Giám đốc đội xe (v3.3 §2, §7). Ghi tên bên nhận vào ô Bên nhận; "
                                 "Kế toán đối chiếu tài khoản theo danh mục đã quản lý.")

    # Ngưỡng chứng từ bắt buộc GIỮ NGUYÊN LÀ CHẶN CỨNG. Bước 2 của bản v3.3 có ô "hẹn bổ sung
    # chứng từ", và sẽ rất dễ để ô ấy mở ngưỡng này ra — nhưng §11 xếp "trường hợp được gửi thiếu
    # chứng từ" vào danh sách năm cấu hình PHẢI CÓ NGƯỜI CHỐT trước khi phát hành. Một dòng lý do
    # gõ tay không phải một người chốt. Nên `hen_bo_sung` chỉ được GHI LẠI (xem phần ghi_chu dưới),
    # nó KHÔNG cho qua ngưỡng. Hôm nào anh Tuấn chốt ai được miễn và miễn tới mức nào thì sửa đúng
    # chỗ này, và sửa có chủ ý.
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if (data.so_tien or 0) >= nguong and not (data.chung_tu or "").strip() and not data.khong_phai_chi_phi:
        raise HTTPException(422, f"Khoản chi từ {nguong:,.0f} đ bắt buộc ghi số chứng từ gốc (chặn cứng B6)")

    # ── KS-64 · B2 – GỬI HAI LẦN THÌ CHỈ MỘT PHIẾU ──
    #
    # Bốn bước làm việc này cần thiết hơn một trang: ở bước cuối người ta bấm Gửi, trang chưa kịp
    # trả lời, họ bấm lại hoặc tải lại. Trước bản này mỗi lần bấm sinh một mã mới nên hệ thống
    # KHÔNG thấy gì trùng — hai phiếu khác mã, cùng một khoản tiền thật.
    #
    # Dấu nhận biết lấy đúng bộ mà người kế toán dùng để nhận ra phiếu lặp: cùng số chứng từ,
    # cùng số tiền, cùng bên nhận. Không có số chứng từ thì KHÔNG đoán — nói ra là không kiểm
    # được, chứ không im lặng cho qua.
    if not data.cho_phep_trung and (data.chung_tu or "").strip():
        ct = data.chung_tu.strip()
        cu = db.execute(select(ExternalTxn).where(ExternalTxn.source == "de_xuat_vietrip",
                                                  ExternalTxn.so_tien == data.so_tien)).scalars().all()
        for t in cu:
            kho = f"{t.mo_ta or ''} {t.ghi_chu or ''}"
            if ct in kho and (not (data.nguoi_thu_huong or "").strip()
                              or data.nguoi_thu_huong.strip() in kho):
                raise HTTPException(422, f"Đã có phiếu {t.ma_gd} cùng chứng từ {ct}, cùng số tiền "
                                         f"{data.so_tien:,.0f} đ và cùng bên nhận. Nếu đây là khoản KHÁC "
                                         "thì gửi lại với ô «vẫn gửi dù trùng»; nếu là lần bấm thứ hai thì "
                                         "phiếu cũ đã vào sổ rồi, không cần gửi nữa.")

    ma = (data.ma_gd or "").strip()
    if not ma:
        n = db.execute(select(func.count(ExternalTxn.id))
                       .where(ExternalTxn.source == "de_xuat_vietrip")).scalar() or 0
        ma = f"VTOS-DX-{date.today():%Y%m}-{n + 1:04d}"
    tk = " · ".join(x for x in [data.nguoi_thu_huong, data.so_tai_khoan, data.ngan_hang] if x.strip())
    # KS-64: ba trường mới của bước 1–2 đi vào chính `mo_ta`, vì đó là ô mà màn Đối soát và mọi
    # bản xuất đang ĐỌC. Nhét vào `ghi_chu` cả thì người xem danh sách không thấy, mà một căn cứ
    # số tiền không ai thấy thì nó không khác gì chưa khai.
    LOAI_TEN = {"thanh_toan": "Thanh toán", "tam_ung": "Tạm ứng", "hoan_ung": "Hoàn ứng / hoàn chi"}
    duoi = [x for x in [
        LOAI_TEN.get((data.loai or "").strip(), ""),
        f"Thụ hưởng: {tk}" if tk else "",
        f"Căn cứ: {data.can_cu_so_tien.strip()}" if (data.can_cu_so_tien or "").strip() else "",
        f"Khoản gốc: {data.ma_khoan_goc.strip()}" if (data.ma_khoan_goc or "").strip() else "",
    ] if x]
    rows = [{"ma_gd": ma, "thoi_diem": f"{data.ngay}T00:00:00", "bien_so": data.bien_so,
             "so_tien": data.so_tien, "nhom": data.nhom,
             "khong_phai_chi_phi": data.khong_phai_chi_phi,
             "tai_khoan": data.so_tai_khoan[:40],
             "mo_ta": (data.noi_dung.strip() + ("".join(" | " + x for x in duoi)))[:300]}]
    try:
        kq = FL.nhap_giao_dich(db, "de_xuat_vietrip", rows, u.username)
    except (ValueError, TypeError) as ex:
        raise HTTPException(422, f"Không ghi được đề xuất: {ex}")
    if kq["da_nhap"] == 0:
        raise HTTPException(422, f"Mã đề xuất {ma} đã tồn tại – đổi mã khác hoặc để trống cho hệ thống tự sinh")
    # Chứng từ, hẹn bổ sung và ghi chú cho người kiểm tra vào `ghi_chu`. Hẹn bổ sung phải nằm
    # trong sổ chứ không chỉ trong nhật ký: nó là lời hứa còn nợ giấy, và người đi thu hồi chứng
    # từ đọc danh sách giao dịch, không đọc audit log.
    phu = [x for x in [
        f"Chứng từ: {data.chung_tu.strip()}" if (data.chung_tu or "").strip() else "",
        f"CHƯA CÓ CHỨNG TỪ – hẹn: {data.hen_bo_sung.strip()}" if (data.hen_bo_sung or "").strip() else "",
        f"Phạm vi: {'toàn đội' if (data.pham_vi or '') == 'doi' else 'một xe'}" if (data.pham_vi or "").strip() else "",
        data.ghi_chu_kiem_tra.strip() if (data.ghi_chu_kiem_tra or "").strip() else "",
    ] if x]
    if phu:
        t = db.execute(select(ExternalTxn).where(ExternalTxn.ma_gd == ma)).scalars().first()
        if t is not None: t.ghi_chu = (" · ".join(phu) + (" · " + t.ghi_chu if t.ghi_chu else ""))[:300]
    R.audit(db, u.username, u.role, "de_xuat_chi_xe", f"de_xuat:{ma}", after=data.model_dump(mode="json"))
    db.commit()
    return {"ma_gd": ma, "message": f"Đã lập đề xuất chi {ma} – {data.so_tien:,.0f} đ"}


# ══════════════════ QT-1 · QUYẾT TOÁN CHUYẾN THEO MẪU 2 (13/10/2026) ══════════════════
#
# Tài xế ký trên GIẤY rồi gửi Zalo về Đội xe; Đội xe nhập hộ (Chủ tịch chọn 13/10/2026). Nên cửa
# ghi mở cho Đội xe, còn ba cửa KÝ mở theo đúng vai của từng bước — khai một chỗ ở
# `quyet_toan_chuyen.VAI_KY`, không khai lại ở đây.
QT_GHI = ("cntt", "gd_doi_xe", "tp_dh", "nv_dh")
QT_XEM = READ
# Mọi vai ký được BẤT KỲ bước nào — bước nào của ai thì `quyet_toan_chuyen.co_the_ky` xét, và nó
# xét cả thứ tự nữa. Hàng rào vai ở đây chỉ chặn người hoàn toàn ngoài tuyến; khai lại từng bước ở
# đây là dựng chỗ cho hai bảng vai nói khác nhau.
from app.services.quyet_toan_chuyen import VAI_KY as _VAI_KY   # noqa: E402
QT_KY = tuple(sorted({v for ds in _VAI_KY.values() for v in ds}))


class QuyetToanIn(BaseModel):
    hdv: str | None = None
    hanh_trinh: str | None = None
    km_dau: int | None = None
    km_cuoi: int | None = None
    km_tour_tren_giay: int | None = None     # con số VIẾT TAY trên tờ giấy – nguồn thứ hai để đối chiếu
    tam_ung: float | None = None
    hoan_tra: float | None = None
    chi_them: float | None = None
    phu_thu: float | None = None
    bc_tinh_trang_xe: str | None = None


class KyIn(BaseModel):
    buoc: str


class TraLaiIn(BaseModel):
    ly_do: str


def _chuyen(db: Session, tid: int):
    from app.models.fleet import Trip
    t = db.get(Trip, tid)
    if t is None:
        raise HTTPException(404, "Không có chuyến này")
    return t


@router.get("/quyet-toan-chuyen/cho-toi-ky")
def qt_cho_toi_ky(u: User = Depends(require_roles(*QT_XEM)), db: Session = Depends(get_db)):
    """VH-3 · 10/11/2026 — những tờ báo cáo xe đang chờ ĐÚNG người đăng nhập ký.

    Bấm thử VH-2 cho thấy Chủ tịch và Kế toán phải lục nhật trình mới tìm ra tờ của mình. Ô «Chờ tôi
    ký» chỉ lấy tờ mà bước đang chờ (`CHO_BUOC`) có vai của người này trong `VAI_KY` — cùng hai bảng
    mà cửa ký đọc, nên ô này không bao giờ mời ai ký một tờ mà cửa ký sẽ từ chối.
    """
    from app.models.fleet import Trip, QT_TRANG_THAI
    from app.models.core import Tour
    from app.services.quyet_toan_chuyen import CHO_BUOC
    trang_thai = [k for k, buoc in CHO_BUOC.items() if u.role in _VAI_KY.get(buoc, ())]
    if not trang_thai:
        return {"rows": [], "tong": 0, "vai": u.role}
    veh = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    out = []
    for t in db.execute(select(Trip).where(Trip.qt_trang_thai.in_(trang_thai), Trip.status != "huy")
                        .order_by(Trip.ngay_di, Trip.id)).scalars():
        v = veh.get(t.vehicle_id)
        tour = db.get(Tour, t.tour_id) if t.tour_id else None
        out.append({"id": t.id, "xe": v.plate if v else "", "tour": tour.code if tour else "",
                    "ten_tour": t.ten_tour, "ngay_di": t.ngay_di, "ngay_ve": t.ngay_ve,
                    "doanh_thu": t.doanh_thu or 0, "qt_trang_thai": t.qt_trang_thai,
                    "buoc_ten": QT_TRANG_THAI.get(t.qt_trang_thai, t.qt_trang_thai)})
    return {"rows": out, "tong": len(out), "vai": u.role}


@router.get("/xe-hom-nay-gon")
def xe_hom_nay_gon(ngay: str = "", u: User = Depends(require_roles(*READ)),
                   db: Session = Depends(get_db)):
    """VH-3 · 10/11/2026 — Xe hôm nay tính từ dữ liệu VTOS, không từ sheet.

    Ba nhóm, mỗi xe đang chạy đúng một nhóm: BỊ CHẶN (báo hỏng mức phải dừng xe chưa đóng) xếp trước
    ĐANG ĐI (lệnh VTOS phủ ngày này), còn lại là Ở BÃI. Xe chạy ngoài lệnh không có trong VTOS nên
    nằm ở «ở bãi» — màn hình nói rõ câu này, không để người đọc tưởng xe ấy rảnh thật.
    """
    from datetime import date as _d
    from app.models.fleet import Fault
    from app.models.core import Tour
    from app.models.hr import DispatchOrder
    hom_nay = _d.fromisoformat(ngay) if ngay else _d.today()
    xe = [v for v in db.execute(select(Vehicle).order_by(Vehicle.plate)).scalars()
          if getattr(v, "active", True)]
    chan = {}
    for f in db.execute(select(Fault).where(Fault.trang_thai.in_(FL.HONG_CON_MO),
                                            Fault.muc_do == "phai_dung_xe")
                        .order_by(Fault.id.desc())).scalars():
        chan.setdefault(f.vehicle_id, f.hien_tuong)
    lenh = {}
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.date_from <= hom_nay,
                                                    DispatchOrder.date_to >= hom_nay,
                                                    DispatchOrder.status != "huy")).scalars():
        lenh.setdefault(d.vehicle_id, d)
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    dang_di, bi_chan, o_bai = [], [], []
    for v in xe:
        if v.id in chan:
            bi_chan.append({"id": v.id, "xe": v.plate, "ly_do": chan[v.id]})
        elif v.id in lenh:
            d = lenh[v.id]
            t = db.get(Tour, d.tour_id) if d.tour_id else None
            dang_di.append({"id": v.id, "xe": v.plate, "tour": t.code if t else "",
                            "ten_tour": t.name if t else "", "ve": d.date_to,
                            "tai_xe": emps.get(d.driver_id, ""), "lenh_id": d.id})
        else:
            o_bai.append({"id": v.id, "xe": v.plate})
    return {"ngay": hom_nay, "dang_di": dang_di, "bi_chan": bi_chan, "o_bai": o_bai,
            "ghi_chu": "«Đang đi» chỉ tính xe có lệnh VTOS; xe chạy ngoài lệnh vẫn hiện là ở bãi."}


@router.get("/quyet-toan-chuyen/{tid}")
def qt_xem(tid: int, km_tour_tren_giay: int | None = None,
           u: User = Depends(require_roles(*QT_XEM)), db: Session = Depends(get_db)):
    from app.services import quyet_toan_chuyen as QT
    t = _chuyen(db, tid)
    o = QT.xem(db, t)
    if km_tour_tren_giay is not None:
        o["diem_lech"] = QT.kiem(db, t, km_tour_tren_giay=km_tour_tren_giay)
    # Man hinh KHONG chep lai bang vai. Chep lai la dung hai bang vai, va hai bang vai thi som muon
    # cung noi khac nhau: nut hien ra roi bam vao an 403, hoac nut an di trong khi nguoi ay ky duoc.
    # `buoc_ky_duoc` do chinh `co_the_ky` sinh ra - cung ham ma cua ky goi khi ghi that.
    o["quyen"] = {
        "ghi": u.role in QT_GHI and (t.qt_trang_thai or "nhap") in ("nhap", "tra_lai"),
        "ky": u.role in QT_KY,
        "buoc_ky_duoc": [b for b in QT.QT_BUOC if QT.co_the_ky(t, b, u.role) == ""],
        "vi_sao_chua_ky": {b: QT.co_the_ky(t, b, u.role) for b in QT.QT_BUOC
                           if QT.co_the_ky(t, b, u.role)},
    }
    return o


@router.put("/quyet-toan-chuyen/{tid}")
def qt_ghi(tid: int, data: QuyetToanIn, u: User = Depends(require_roles(*QT_GHI)),
           db: Session = Depends(get_db)):
    from app.services import quyet_toan_chuyen as QT
    t = _chuyen(db, tid)
    if t.qt_trang_thai not in ("nhap", "tra_lai"):
        raise HTTPException(422, f"Tờ này đang ở '{QT.QT_TRANG_THAI.get(t.qt_trang_thai, '?')}' – "
                                 f"trả lại trước thì mới sửa được")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "km_tour_tren_giay":
            continue
        setattr(t, k, v)
    R.audit(db, u.username, u.role, "qt_chuyen_ghi", f"chuyen:{tid}",
            after=data.model_dump(mode="json", exclude_unset=True))
    db.commit()
    return qt_xem(tid, data.km_tour_tren_giay, u, db)


@router.post("/quyet-toan-chuyen/{tid}/gui")
def qt_gui(tid: int, u: User = Depends(require_roles(*QT_GHI)), db: Session = Depends(get_db)):
    from app.services import quyet_toan_chuyen as QT
    t = _chuyen(db, tid)
    try:
        kq = QT.gui_di(db, t, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "qt_chuyen_gui", f"chuyen:{tid}", after=kq)
    db.commit()
    return kq


@router.post("/quyet-toan-chuyen/{tid}/ky")
def qt_ky(tid: int, data: KyIn, u: User = Depends(require_roles(*QT_KY)),
          db: Session = Depends(get_db)):
    from app.services import quyet_toan_chuyen as QT
    t = _chuyen(db, tid)
    try:
        kq = QT.ky(db, t, data.buoc, u.username, u.role)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "qt_chuyen_ky", f"chuyen:{tid}", after={"buoc": data.buoc, **kq})
    db.commit()
    return kq


@router.post("/quyet-toan-chuyen/{tid}/tra-lai")
def qt_tra_lai(tid: int, data: TraLaiIn, u: User = Depends(require_roles(*QT_KY)),
               db: Session = Depends(get_db)):
    from app.services import quyet_toan_chuyen as QT
    t = _chuyen(db, tid)
    try:
        kq = QT.tra_lai(db, t, data.ly_do, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "qt_chuyen_tra_lai", f"chuyen:{tid}", after=kq)
    db.commit()
    return kq


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# HQ-2 (13/10/2026) — Ô CHỌN KỲ CHO KHỐI «HIỆU QUẢ ĐỘI XE», VÀ ĐỊNH MỨC DẦU.
#
# Vì sao cần một đường riêng: khối Chủ tịch xưa nay đọc số kèm trong `/dashboard`, mà `/dashboard`
# chỉ tính được MỘT mốc — hôm nay. Muốn xem tháng 9 thì phải có chỗ để hỏi.
#
# MỘT CHỖ KHÁC VỚI Ô «THỜI ĐIỂM» CỦA MÀN HÌNH ĐIỀU HÀNH XE, viết ra để sau không ai nhầm hai cơ
# chế: ô bên ấy mở BẢN CHỤP, vì những con số ấy đếm hàng đợi TẠI MỘT THỜI ĐIỂM — qua rồi thì không
# tính lại được. Bốn chỉ số đội xe thì ngược lại: mỗi chuyến thuộc về một kỳ theo NGÀY ĐI của nó,
# nên tháng 9 lúc nào cũng tính lại được và luôn ra đúng con số của sổ sách hiện có. Đường này
# TÍNH LẠI, không đọc bản chụp — và hệ quả phải nói ra: Đội xe nạp bù chuyến tháng 9 tuần sau thì
# số tháng 9 ở đây SẼ ĐỔI. Đó là đúng.
# ═══════════════════════════════════════════════════════════════════════════════════════════════

HQ_NGUONG_GHI = ("cntt", "gd_doi_xe", "tp_dh")


@router.get("/hieu-qua-doi-xe")
def hq_theo_ky(moc: date | None = None, u: User = Depends(require_roles(*READ)),
               db: Session = Depends(get_db)):
    from app.services import hieu_qua_xe as HQ
    hom_nay = date.today()
    o = HQ.theo_ky(db, moc or hom_nay, hom_nay=hom_nay)
    o["ky_co_chuyen"] = HQ.ky_co_chuyen(db)
    return o


# ══════════════════ DX-4 · BHXH phần công ty đóng — CỬA ĐỐI CHIẾU, không phải cửa ghi
#
# Phía đội xe ĐÃ CÓ cửa nhập (nhóm `bhxh` của chi phí kỳ). Cái thiếu là một phép soi lại: con số
# nhập tay không có gì đối chiếu, gõ nhầm một chữ số hay quên một kỳ thì giá vốn đội xe lệch mà
# không ai biết. Cửa này đặt số máy tính cạnh số nhập tay rồi DỪNG — ranh giới Chủ tịch đặt
# 09/9/2026: hệ thống viết phép tính, người của bộ phận nhập số liệu.
@router.get("/bhxh-doi-xe")
def bhxh_doi_xe(ky: str = "", u: User = Depends(require_roles(*READ)),
                db: Session = Depends(get_db)):
    """Đối chiếu BHXH phần công ty đóng của đội xe một kỳ (YYYY-MM)."""
    from app.services import bhxh_cong_ty as BH
    ky = (ky or "").strip()
    if not ky:
        raise HTTPException(422, "Phải chọn kỳ, dạng YYYY-MM")
    return BH.doi_chieu(db, ky)


# ══════════════════ DX-3 · PHẠT TÀI XẾ (vào lương) và GIÁ DẦU THEO NGÀY
#
# VAI GHI PHẠT HẸP HƠN `WRITE`: Chủ tịch chốt 16/10/2026 là Giám đốc đội xe ghi. Để nguyên `WRITE`
# thì Điều hành cũng trừ được lương tài xế — một quyền chưa ai trao.
#
# VAI ĐỐI CHIẾU LÀ HCNS, và đó là người KHÁC. Cùng một người vừa ghi vừa đánh dấu đã đối chiếu thì
# dấu ấy không nói thêm được gì.
GHI_PHAT = ("cntt", "gd_doi_xe")
DOI_CHIEU_PHAT = ("cntt", "hcns")
GHI_GIA_DAU = ("cntt", "ketoan", "gd_doi_xe")


class PhatVao(BaseModel):
    driver_id: int
    ky: str
    ngay: date
    so_tien: float
    ly_do: str = ""
    trip_id: int | None = None
    vehicle_id: int | None = None


@router.get("/phat-tai-xe")
def ds_phat(ky: str = "", driver_id: int = 0, u: User = Depends(require_roles(*READ)),
            db: Session = Depends(get_db)):
    """Sổ phạt tài xế. `chua_doi_chieu` là con số HCNS cần nhìn trước khi chốt lương kỳ ấy."""
    from app.services import phat_va_gia_dau as PG
    return PG.so_phat(db, ky, driver_id or None)


@router.get("/tai-xe-chon")
def ds_tai_xe_chon(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Tài xế để chọn trên ô nhập phiếu phạt — id, họ tên, mã. Không có trường lương nào.

    Ở TRONG NHÓM FLEET LÀ CỐ Ý. Nhóm "/api/v1/tai-xe" đã có một cửa danh sách tài xế, nhưng nhóm ấy
    không nằm trong `MAN_HINH_API["/doi-xe"]`; trang con "/doi-xe/phat-tai-xe" gọi nó là vỡ hàng rào
    quyền của chính trang ấy. Xem ghi chú đầy đủ ở `services/phat_va_gia_dau.tai_xe_chon`.

    Chỉ `READ`, KHÔNG phải `GHI_PHAT`: ai xem được sổ phạt thì xem được tên tài xế. Quyền GHI vẫn
    nằm nguyên ở `POST /phat-tai-xe`.
    """
    from app.services import phat_va_gia_dau as PG
    return PG.tai_xe_chon(db)


@router.post("/phat-tai-xe", status_code=201)
def them_phat(v: PhatVao, u: User = Depends(require_roles(*GHI_PHAT)),
              db: Session = Depends(get_db)):
    from app.services import phat_va_gia_dau as PG
    try:
        p = PG.ghi_phat(db, v.driver_id, v.ky, v.ngay, v.so_tien, v.ly_do, u.username,
                        v.trip_id, v.vehicle_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    R.audit(db, u.username, u.role, "phat_tai_xe", f"employee:{v.driver_id}",
            after={"ky": p.ky, "ngay": p.ngay.isoformat(), "so_tien": float(p.so_tien),
                   "ly_do": p.ly_do})
    db.commit()
    return {"id": p.id, "message": f"Đã ghi khoản phạt kỳ {p.ky}. Khoản này trừ vào LƯƠNG, "
                                   "không cộng vào chi phí của xe."}


@router.post("/phat-tai-xe/{pid}/doi-chieu")
def doi_chieu_phat(pid: int, u: User = Depends(require_roles(*DOI_CHIEU_PHAT)),
                   db: Session = Depends(get_db)):
    """HCNS đánh dấu đã nhìn khoản này khi chốt lương. KHÔNG phải phê duyệt."""
    from app.models.fleet import PhatTaiXe
    from app.services import phat_va_gia_dau as PG
    p = db.get(PhatTaiXe, pid)
    if not p:
        raise HTTPException(404, "Không có khoản phạt này")
    try:
        PG.hcns_doi_chieu(db, p, u.username)
    except ValueError as e:
        raise HTTPException(422, str(e))
    R.audit(db, u.username, u.role, "doi_chieu_phat_tai_xe", f"phat:{pid}", after={"ky": p.ky})
    db.commit()
    return {"message": f"Đã đối chiếu khoản phạt #{pid}"}


class GiaDauVao(BaseModel):
    ngay: date
    loai: str = "do"
    gia_lit: float
    nguon: str = ""


@router.get("/gia-dau")
def ds_gia_dau(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    from app.models.fleet import GiaDauNgay, LOAI_DAU
    rows = db.execute(select(GiaDauNgay).order_by(GiaDauNgay.ngay.desc())).scalars()
    return {"loai": [{"ma": k, "ten": v} for k, v in LOAI_DAU.items()],
            "rows": [{"id": g.id, "ngay": g.ngay.isoformat(), "loai": g.loai,
                      "loai_ten": LOAI_DAU.get(g.loai, g.loai), "gia_lit": float(g.gia_lit),
                      "nguon": g.nguon, "boi": g.boi} for g in rows],
            "ghi_chu": ("Sao kê thẻ dầu cho TIỀN, không cho lít. Khai giá từng ngày thì ô Tiêu hao "
                        "mới có số lít để tính. Máy KHÔNG lấy giá gần nhất khi thiếu ngày – giá "
                        "dầu đổi mười ngày một lần, lấy giá cách đó ba tuần ra số lít sai mà "
                        "trông vẫn hợp lý.")}


@router.post("/gia-dau", status_code=201)
def them_gia_dau(v: GiaDauVao, u: User = Depends(require_roles(*GHI_GIA_DAU)),
                 db: Session = Depends(get_db)):
    """Một giá cho một (ngày, loại). Ghi lại cùng ngày thì ĐÈ giá cũ, không thêm dòng thứ hai."""
    from app.services import phat_va_gia_dau as PG
    try:
        g = PG.ghi_gia(db, v.ngay, v.loai, v.gia_lit, v.nguon, u.username)
    except ValueError as e:
        raise HTTPException(422, str(e))
    R.audit(db, u.username, u.role, "gia_dau_ngay", f"ngay:{v.ngay.isoformat()}",
            after={"loai": g.loai, "gia_lit": float(g.gia_lit), "nguon": g.nguon})
    db.commit()
    return {"id": g.id, "message": f"Đã khai giá {g.loai} ngày {g.ngay.isoformat()}"}


# ══════════════════ DX-2 · BÁO CÁO NHÌN LẠI: thuê xe ngoài trong khi xe nhà đậu
#
# Chủ tịch chọn việc này trước năm việc còn lại của đội xe (16/10/2026): nó là thứ đã bắt được
# 51.348.800 đ nhóm A tháng 9/2026.
#
# CỬA ĐỌC THUẦN, không có cửa ghi đi kèm — có chủ đích. Báo cáo này nêu ra chỗ nghi, người có sổ
# mới biết chặng ấy thật sự chạy bằng xe nào. Dựng thêm một nút «gắn xe vào chặng» ngay đây là mời
# người ta sửa sổ quyết toán từ một màn hình không hiển thị tờ quyết toán — đúng lẽ Chủ tịch đã
# chốt 18/9 với sổ chuyến còn nợ: danh sách và đường dẫn, không làm hàng loạt từ màn hình tổng.
@router.get("/doi-chieu-xe-ngoai")
def doi_chieu_xe_ngoai(tu: str = "", den: str = "", nam: int = 0, thang: int = 0,
                       u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Đối chiếu chặng ô tô thuê ngoài với xe nhà rảnh cùng ngày, theo kỳ.

    Nhận kỳ theo hai cách: `nam`+`thang`, hoặc `tu`+`den`. Thiếu cả hai thì lấy tháng trước —
    báo cáo nhìn lại mà mặc định là tháng này thì nửa tháng đầu nó luôn gần rỗng.
    """
    from datetime import date as _date
    from app.services import doi_chieu_xe_ngoai as DX
    if nam and thang:
        d1, d2 = DX.ky_thang(nam, thang)
    elif tu and den:
        try:
            d1, d2 = _date.fromisoformat(tu), _date.fromisoformat(den)
        except ValueError:
            raise HTTPException(422, "Ngày phải ở dạng YYYY-MM-DD")
    else:
        h = _date.today()
        d1, d2 = DX.ky_thang(h.year - (h.month == 1), 12 if h.month == 1 else h.month - 1)
    try:
        return DX.soat(db, d1, d2)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/dinh-muc-dau")
def hq_dinh_muc(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Ngưỡng tiêu hao theo số chỗ, KÈM các số chỗ đang có xe mà chưa ai khai.

    Trả cả phần CHƯA khai chứ không chỉ phần đã khai: màn hình phải in ra được ô trống có tên, nếu
    không thì Đội xe không biết mình còn thiếu loại nào.
    """
    from app.models.fleet import FuelNorm
    da = {n.seats: {"seats": n.seats, "l_100km": n.l_100km, "ghi_chu": n.ghi_chu,
                    "boi": n.boi, "luc": n.luc} for n in db.execute(select(FuelNorm)).scalars()}
    dem: dict[int, int] = {}
    for v in db.execute(select(Vehicle).where(Vehicle.active.is_(True))).scalars():
        dem[v.seats] = dem.get(v.seats, 0) + 1
    return {"rows": [da.get(s) or {"seats": s, "l_100km": None, "ghi_chu": "", "boi": "", "luc": None}
                     for s in sorted(set(da) | set(dem))],
            "so_xe_theo_cho": dem,
            "bo_phan": "Đội xe"}


class DinhMucDauIn(BaseModel):
    seats: int
    l_100km: float | None = None      # None = xoá ngưỡng của loại xe này
    ghi_chu: str = ""


@router.put("/dinh-muc-dau")
def hq_dat_dinh_muc(data: DinhMucDauIn, u: User = Depends(require_roles(*HQ_NGUONG_GHI)),
                    db: Session = Depends(get_db)):
    from app.models.fleet import FuelNorm
    if data.seats <= 0:
        raise HTTPException(422, "Số chỗ phải lớn hơn 0")
    if data.l_100km is not None and data.l_100km <= 0:
        raise HTTPException(422, "Định mức phải lớn hơn 0 — để trống nghĩa là CHƯA KHAI, "
                                 "không phải bằng 0")
    n = db.execute(select(FuelNorm).where(FuelNorm.seats == data.seats)).scalars().first()
    truoc = n.l_100km if n else None
    if data.l_100km is None:
        if n is not None:
            db.delete(n)
    elif n is None:
        db.add(FuelNorm(seats=data.seats, l_100km=data.l_100km, ghi_chu=data.ghi_chu,
                        boi=u.username))
    else:
        from datetime import datetime as _dtn
        n.l_100km, n.ghi_chu, n.boi = data.l_100km, data.ghi_chu, u.username
        n.luc = _dtn.now()
    R.audit(db, u.username, u.role, "dinh_muc_dau", f"seats:{data.seats}",
            before={"l_100km": truoc}, after=data.model_dump(mode="json"))
    db.commit()
    return {"seats": data.seats, "l_100km": data.l_100km,
            "message": ("Đã xoá định mức" if data.l_100km is None
                        else f"Đã đặt {data.l_100km} L/100km cho xe {data.seats} chỗ")}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# XE-1 (14/10/2026) — XOÁ MỘT DÒNG XE TẠO NHẦM.
#
# Chủ tịch chọn 14/10/2026 sau khi đo trên hệ thật: danh mục 16 xe, hai dòng là dữ liệu mẫu
# (51B-123.45, 51B-678.90) không bán được, không ngừng khai thác được, và không có cách nào bỏ đi.
#
# CHỈ CNTT. Không phải vì Đội xe kém tin cậy hơn, mà vì đây là thao tác DUY NHẤT trong phân hệ xe
# làm mất hẳn một dòng — mọi thao tác khác đều chỉ đổi trạng thái. Để một vai dùng hằng ngày giữ
# nút ấy là sớm muộn có người bấm nhầm thay vì ghi "ngừng khai thác".
#
# Hai cửa chứ không một: cửa SOÁT đọc được bằng vai READ, để Đội xe tự thấy chiếc nào xoá được và
# chiếc nào vướng gì — không phải hỏi CNTT rồi chờ.
# ═══════════════════════════════════════════════════════════════════════════════════════════════

# Chủ tịch chốt 14/10/2026: thêm vai Chủ tịch vào nút xoá. Em dựng ban đầu CHỈ cntt, và
# chính điều đó chặn Chủ tịch lúc cần xoá — ông là người quyết, không phải người đi xin.
# Danh sách này PHẢI khớp với XOA_XE_VAI trong web/app/doi-xe/page.tsx; có phép thử canh.
XOA_XE = ("cntt", "chutich")


@router.get("/xe/{vid}/xoa-duoc")
def xe_xoa_duoc(vid: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    from app.services import xoa_xe as XX
    v = db.get(Vehicle, vid)
    if v is None:
        raise HTTPException(404, "Không có xe này")
    return XX.soat(db, v)


@router.delete("/xe/{vid}")
def xe_xoa(vid: int, ly_do: str, u: User = Depends(require_roles(*XOA_XE)),
           db: Session = Depends(get_db)):
    from app.services import xoa_xe as XX
    v = db.get(Vehicle, vid)
    if v is None:
        raise HTTPException(404, "Không có xe này")
    bien = v.plate
    try:
        kq = XX.xoa(db, v, ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    # Nhật ký giữ NGUYÊN nội dung dòng đã xoá: xoá nhầm thì còn dựng lại được bằng tay.
    R.audit(db, u.username, u.role, "xoa_xe", f"vehicle:{kq['da_xoa'].get('code') or bien}",
            before={k: (x.isoformat() if hasattr(x, "isoformat") else x)
                    for k, x in kq["da_xoa"].items()},
            after={"ly_do": kq["ly_do"], "lich_su_bien": len(kq["lich_su_bien"])})
    db.commit()
    return {"message": f"Đã xoá xe {bien} khỏi danh mục", "ly_do": kq["ly_do"]}


# ── XS-1 (Chủ tịch duyệt bản xem thử 25/10/2026) · xe đang đi theo sheet quyết toán của Đội xe ──
# CHỈ ĐỌC: không ghi gì vào sheet, không nạp chuyến nào vào VTOS. Xem `services/xe_theo_sheet.py`.
@router.get("/xe-theo-sheet")
def xe_theo_sheet(doc_lai: int = Query(0, ge=0, le=1), u: User = Depends(require_roles(*READ)),
                  db: Session = Depends(get_db)):
    """`doc_lai=1` bỏ qua đệm 15 phút — nút «Đọc lại ngay» trên màn chi tiết."""
    from app.services import xe_theo_sheet as XS
    return XS.bao_cao(db, date.today(), doc_lai=bool(doc_lai)) | {
        "cho_ky": XS.cho_ky(db), "duoc_dan": u.role in GHI_LINK_SHEET}


# XS-1b (Chủ tịch 25/10/2026, «Giữ ký duyệt Chủ tịch»): ai được DÁN link. Chủ tịch không nằm đây vì
# Chủ tịch là người ký duy nhất của tham số, và người trình không tự ký (`sign_param`).
GHI_LINK_SHEET = ("gd_doi_xe", "tp_dh", "cntt")


class LinkSheetVao(BaseModel):
    url: str
    chi_doc_thu: bool = False


@router.post("/xe-theo-sheet/link")
def dan_link_sheet(v: LinkSheetVao, u: User = Depends(require_roles(*GHI_LINK_SHEET)),
                   db: Session = Depends(get_db)):
    """Đọc thử, rồi (nếu không phải chỉ đọc thử) TRÌNH link chờ Chủ tịch ký — không ghi thẳng.

    Đọc thử trước khi trình là bắt buộc: một link không đọc được mà vẫn trình thì Chủ tịch ký xong
    robot vẫn không có số, và lỗi lộ ra ở màn hình Chủ tịch chứ không ở chỗ người dán.
    """
    from app.models.core import Param
    from app.services import xe_theo_sheet as XS
    url = (v.url or "").strip()
    try:
        nguong = R.get_param(db, "xe_lech_km_noi_chuyen")
    except KeyError:
        nguong = 50
    thu = XS.doc_thu(url, nguong)
    if not thu["ok"] or v.chi_doc_thu:
        return {"doc_thu": thu, "da_trinh": False}
    ref = db.execute(select(Param).where(Param.key == XS.KHOA_LINK).order_by(Param.id.desc())).scalars().first()
    if ref is None:
        raise HTTPException(409, "Hệ chưa có tham số xe_sheet_csv_url — báo CNTT.")
    p = Param(key=XS.KHOA_LINK, value=url, label=ref.label, unit=ref.unit, effective_from=date.today(),
              source=f"Dán ở màn Đội xe bởi {u.username}", status="pending", proposed_by=u.username)
    db.add(p); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_tham_so", f"param:{XS.KHOA_LINK}",
            before={"value": ref.value}, after={"value": url, "hieu_luc": str(p.effective_from)})
    db.commit()
    return {"doc_thu": thu, "da_trinh": True, "id": p.id,
            "message": "Đã trình link — chờ Chủ tịch ký ở màn Chính sách & định mức. Ký xong robot mới đọc."}


# ══════════════════ VH-9 · LỊCH XE 90 NGÀY TỚI (Chủ tịch duyệt 11/11/2026) ══════════════════
from app.services import lich_xe_tuong_lai as LX                       # noqa: E402
# Phòng Kinh doanh và Ban lãnh đạo xem KHOẢNG TRỐNG để đẩy bán — không thấy tên tour, giá nội bộ.
KHOANG_TRONG_XEM = tuple(sorted(set(READ) | {"chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh",
                                             "gd_kd", "tp_kd", "cntt", "robot_ks", "tp_hd"}))   # robot_ks = bks, chỉ đọc
# VH-17 · 11/11/2026: cùng nhóm vai này đọc CẢ lưới lịch 90 ngày (/lich-xe-trong nay là màn lịch đầy đủ
# cho lãnh đạo và trưởng phòng). TRÙNG KHÍT MENU_ROLES["/lich-xe-trong"]; +tp_hd theo «tất cả trưởng phòng».


@router.get("/lich-xe-tuong-lai")
def lich_xe_tuong_lai(so_ngay: int = 90, u: User = Depends(require_roles(*KHOANG_TRONG_XEM)), db: Session = Depends(get_db)):
    """Lưới xe × ngày 90 ngày tới, công suất, khoảng trống. Chỉ đọc lệnh, đề nghị, báo hỏng đã có.

    VH-17: vai ngoài đội xe (không thuộc READ) thấy ô BẬN nhưng không thấy tên tour trên Sheet — Chủ tịch
    chốt cho Kinh doanh «không xem tour» (XE-KD-1); cắt ở máy chủ, không giấu ở màn hình."""
    b = LX.bang(db, so_ngay=so_ngay)
    if u.role not in READ:
        for h in b["xe"]:
            h["tour_sheet"] = {}
    return b


@router.get("/lich-xe-tuong-lai/khoang-trong")
def lich_xe_khoang_trong(u: User = Depends(require_roles(*KHOANG_TRONG_XEM)), db: Session = Depends(get_db)):
    return LX.khoang_trong_cho_kinh_doanh(db)


@router.post("/robot/lich-xe-gui-tuan", dependencies=[Depends(robot_auth)])
def lich_xe_gui_tuan(db: Session = Depends(get_db)):
    """Robot gọi sáng thứ Hai (n8n): một tin «xe còn trống 30 ngày tới» cho Ban lãnh đạo, Điều hành, Kinh doanh,
    Marketing, Đoàn. Mỗi tuần MỘT tin (ref theo tuần ISO) — robot gọi lại trong tuần thì không đẻ tin thứ hai."""
    from datetime import date as _d
    from app.models.core import Alert
    y, w, _ = _d.today().isocalendar()
    ref = f"tuan:{y}-W{w:02d}"
    if db.execute(select(Alert).where(Alert.kind == "xe_trong_tuan", Alert.ref == ref)).scalars().first():
        return {"da_gui": False, "ly_do": "Tuần này đã gửi", "ref": ref}
    # VH-15: không đủ dữ liệu thì KHÔNG gửi «xe trống» — gửi là bảo Kinh doanh bán ngày xe đã có khách.
    ly_do = LX.chua_du_du_lieu(LX.bang(db, _d.today(), 30))
    if ly_do:
        return {"da_gui": False, "ly_do": ly_do, "ref": ref}
    db.add(Alert(kind="xe_trong_tuan", level="info", ref=ref, message=LX.tin_tuan(db),
                 to_roles=",".join(LX.NGUOI_NHAN_TUAN)))
    R.audit(db, "robot", "robot", "gui_lich_xe_trong_tuan", ref, after={"nguoi_nhan": list(LX.NGUOI_NHAN_TUAN)})
    db.commit()
    return {"da_gui": True, "ref": ref, "nguoi_nhan": list(LX.NGUOI_NHAN_TUAN)}


# ====================== VH-13 · XUẤT EXCEL BA BẢNG ĐỘI XE ======================
# Chủ tịch duyệt bản xem trước 11/11/2026. Mỗi cửa đọc ĐÚNG hàm mà màn hình đọc, cùng nhóm vai được xem
# màn ấy — tệp không mở rộng quyền xem, và không ra con số khác màn hình.
from fastapi import Response as _Resp                               # noqa: E402
from app.services import xuat_excel_doi_xe as XL                    # noqa: E402

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _tep(b: bytes, ten: str):
    return _Resp(content=b, media_type=_XLSX, headers={"Content-Disposition": f'attachment; filename="{ten}"'})


def _ky_hop_le(ky: str):
    try:
        return QT.ky_range(ky)
    except Exception:
        raise HTTPException(422, "Kỳ phải có dạng YYYY-MM")


@router.get("/hieu-qua.xlsx")
def hieu_qua_xlsx(ky: str, u: User = Depends(require_roles(*XEM_HIEU_QUA)), db: Session = Depends(get_db)):
    _ky_hop_le(ky)
    return _tep(XL.xep_hang(AI.hieu_qua_ky(db, ky), ky), XL.ten_tep("XEP_HANG_XE_TAI_XE", ky))


@router.get("/lai-lo.xlsx")
def lai_lo_xlsx(ky: str, u: User = Depends(require_roles(*XEM_LAI_LO)), db: Session = Depends(get_db)):
    _ky_hop_le(ky)
    return _tep(XL.lai_lo(LL.bao_cao(db, ky, "khong"), LL.theo_chuyen(db, ky), ky), XL.ten_tep("LAI_LO_DOI_XE", ky))


@router.get("/chuyen.xlsx")
def chuyen_xlsx(ky: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    d1, d2 = _ky_hop_le(ky)
    ds = danh_sach_chuyen(vehicle_id=None, tu=d1, den=d2, u=u, db=db)
    return _tep(XL.bao_cao_xe(ds, ky), XL.ten_tep("BAO_CAO_TUNG_XE", ky))
