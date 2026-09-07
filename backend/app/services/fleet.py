"""Kiểm tra điều kiện phát lệnh điều xe – Đợt 1 đặc tả "Quản lý vận hành xe Vietrip" v1.3 §7.

Đặc tả yêu cầu bốn mức, và điều đáng giá nhất nằm ở mức thứ tư:

  BLOCK              – điều kiện bắt buộc chưa đạt, không có nút vượt chung.
  APPROVAL_REQUIRED  – ngoại lệ chính sách, phải trình đúng người.
  REVIEW             – dữ liệu có chênh lệch, cần người xem.
  UNKNOWN            – CHƯA ĐỦ DỮ LIỆU để kết luận.

UNKNOWN là mức dễ bị bỏ qua nhất khi lập trình, và cũng là mức nguy hiểm nhất nếu bỏ: một chiếc xe chưa nhập
đăng kiểm mà màn hình hiện màu xanh thì người điều hành tin rằng đã kiểm tra rồi. Ở đây, thiếu dữ liệu không
bao giờ ra kết quả "đạt"; nó ra "chưa đủ dữ liệu" và nói rõ thiếu gì.

Về việc CHẶN: hôm nay hồ sơ giấy tờ 14 xe chưa nhập vào hệ thống. Nếu bật chặn ngay theo giấy tờ thì mọi lệnh
điều xe đều dừng – phần mềm sẽ bị tắt đi chứ không được sửa dữ liệu. Nên thiếu giấy tờ mặc định là UNKNOWN
(hiện rõ trên màn hình, ghi vào nhật ký), và có tham số chính sách `xe_chan_khi_thieu_giay` để bật thành BLOCK
khi Chủ tịch quyết. Những điều KHÔNG phụ thuộc nhập liệu – hết quyền khai thác, xe đã bán, trùng lịch – thì
chặn ngay từ hôm nay, vì chúng đúng bất kể hồ sơ đã nhập đủ hay chưa.
"""
from datetime import date
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session
from app.models.hr import Vehicle, Employee, DispatchOrder
from app.models.fleet import VehiclePlate, VehicleDocument, FleetVerification, VEHICLE_DOCS, DRIVER_DOCS

BLOCK, APPROVAL, REVIEW, UNKNOWN, OK = "BLOCK", "APPROVAL_REQUIRED", "REVIEW", "UNKNOWN", "OK"
NANG = {BLOCK: 4, APPROVAL: 3, REVIEW: 2, UNKNOWN: 1, OK: 0}      # để lấy mức nghiêm trọng nhất
MUC_TEN = {BLOCK: "Chặn", APPROVAL: "Cần duyệt ngoại lệ", REVIEW: "Cần xem lại", UNKNOWN: "Chưa đủ dữ liệu",
           OK: "Đạt"}
# Xe được phép điều đi khi quyền khai thác nằm trong nhóm này
QUYEN_DUOC_DIEU = ("so_huu", "hop_tac", "thue")


def _mo(code: str, level: str, msg: str, fix: str = "") -> dict:
    return {"code": code, "level": level, "msg": msg, "huong_xu_ly": fix}


def _docs(db: Session, vehicle_id: int | None, employee_id: int | None) -> dict[str, VehicleDocument]:
    """Giấy còn hiệu lực mới nhất theo từng loại. Giấy đã thay thì `active=False`, không xóa."""
    q = select(VehicleDocument).where(VehicleDocument.active == True)
    q = q.where(VehicleDocument.vehicle_id == vehicle_id) if vehicle_id else q.where(VehicleDocument.employee_id == employee_id)
    out: dict[str, VehicleDocument] = {}
    for d in db.execute(q.order_by(VehicleDocument.id)).scalars():
        cu = out.get(d.kind)
        # Giữ giấy có hạn XA nhất; giấy chưa có hạn không được lấn giấy đã có hạn.
        if cu is None or (d.expires_on and (cu.expires_on is None or d.expires_on > cu.expires_on)):
            out[d.kind] = d
    return out


def _giay(kq: list, chu_the: str, ten_loai: dict, docs: dict, den_ngay: date, chan_khi_thieu: bool):
    for kind, ten in ten_loai.items():
        d = docs.get(kind)
        if d is None:
            kq.append(_mo(f"THIEU_{kind.upper()}", BLOCK if chan_khi_thieu else UNKNOWN,
                          f"Chưa có dữ liệu {ten.lower()} của {chu_the}",
                          f"Nhập {ten.lower()} vào hồ sơ; chưa nhập thì hệ thống không kết luận là còn hạn"))
            continue
        if d.expires_on is None:
            kq.append(_mo(f"THIEU_HAN_{kind.upper()}", BLOCK if chan_khi_thieu else UNKNOWN,
                          f"{ten} của {chu_the} có số nhưng chưa có ngày hết hạn",
                          "Bổ sung ngày hết hạn theo giấy gốc"))
            continue
        if d.expires_on < den_ngay:
            kq.append(_mo(f"HET_HAN_{kind.upper()}", BLOCK,
                          f"{ten} của {chu_the} hết hạn {d.expires_on:%d/%m/%Y}, trước ngày kết thúc hành trình {den_ngay:%d/%m/%Y}",
                          "Gia hạn giấy hoặc đổi xe/tài xế khác"))
        elif d.verify != "da_xac_minh":
            kq.append(_mo(f"CHUA_DOI_CHIEU_{kind.upper()}", REVIEW,
                          f"{ten} của {chu_the} còn hạn theo dữ liệu nguồn nhưng chưa đối chiếu giấy gốc",
                          "Bộ phận phụ trách đối chiếu giấy gốc rồi đánh dấu đã xác minh"))


def trung_lich(db: Session, vehicle_id: int, d1: date, d2: date, bo_qua: int | None = None) -> list[DispatchOrder]:
    """Lệnh còn hiệu lực của cùng chiếc xe chồng ngày với khoảng đang xét.

    Hai khoảng chồng nhau khi bắt_đầu_A <= kết_thúc_B và bắt_đầu_B <= kết_thúc_A – viết thẳng như vậy thay vì
    liệt kê các trường hợp, vì liệt kê là chỗ hay sót đúng một ca."""
    q = select(DispatchOrder).where(DispatchOrder.vehicle_id == vehicle_id,
                                    DispatchOrder.status.in_(["cho_xac_nhan", "da_xac_nhan"]),
                                    DispatchOrder.date_from <= d2, DispatchOrder.date_to >= d1)
    if bo_qua: q = q.where(DispatchOrder.id != bo_qua)
    return list(db.execute(q).scalars())


def kiem_tra_dieu_xe(db: Session, v: Vehicle, d1: date, d2: date, driver_id: int | None = None,
                     bo_qua_lenh: int | None = None, chan_khi_thieu_giay: bool = False) -> dict:
    """Chạy toàn bộ điều kiện cho một phương án điều xe. Luôn trả về ĐẦY ĐỦ danh sách, không dừng ở lỗi đầu.

    Dừng ở lỗi đầu tiên khiến người dùng sửa xong một chỗ lại gặp chỗ khác, mỗi vòng một lần – việc đáng lẽ
    làm một lần thành ba lần."""
    kq: list[dict] = []
    if not v:
        return {"muc": BLOCK, "muc_ten": MUC_TEN[BLOCK], "items": [_mo("KHONG_CO_XE", BLOCK, "Không tìm thấy xe")]}

    # 1. Quyền khai thác và vòng đời tài sản – hai việc khác nhau, kiểm riêng.
    if v.op_right not in QUYEN_DUOC_DIEU:
        kq.append(_mo("KHONG_QUYEN_KHAI_THAC", BLOCK,
                      f"Xe {v.plate} không có quyền khai thác đang hiệu lực",
                      "Cập nhật hợp đồng/quyền khai thác trước khi điều xe"))
    if v.lifecycle == "da_ban" and v.op_right != "hop_tac":
        kq.append(_mo("XE_DA_BAN", BLOCK,
                      f"Xe {v.plate} đã bán và không có hợp đồng hợp tác để tiếp tục khai thác",
                      "Nếu vẫn khai thác theo hợp đồng thì đặt quyền khai thác là hợp tác và nhập số hợp đồng"))
    if v.lifecycle == "cho_kiem_tra":
        kq.append(_mo("XE_CHO_KIEM_TRA", BLOCK, f"Xe {v.plate} đang chờ kiểm tra sau sự cố",
                      "Người được giao xác nhận xe đủ điều kiện sau xử lý"))
    if v.lifecycle == "ngung":
        kq.append(_mo("XE_NGUNG_KHAI_THAC", BLOCK, f"Xe {v.plate} đã ngừng khai thác"))
    if not v.active:
        kq.append(_mo("XE_KHONG_HOAT_DONG", BLOCK, f"Xe {v.plate} đang tắt trong danh mục"))

    # 2. Hợp đồng hợp tác phải phủ hết hành trình – hết hạn giữa chuyến cũng là hết quyền.
    if v.op_right in ("hop_tac", "thue"):
        if not v.contract_ref:
            kq.append(_mo("THIEU_HOP_DONG", BLOCK if chan_khi_thieu_giay else UNKNOWN,
                          f"Xe {v.plate} khai thác theo hợp đồng nhưng chưa nhập số hợp đồng",
                          "Nhập số hợp đồng, ngày hiệu lực và bên chịu chi phí"))
        if v.contract_to and v.contract_to < d2:
            kq.append(_mo("HOP_DONG_HET_HAN", BLOCK,
                          f"Hợp đồng {v.contract_ref} hết hiệu lực {v.contract_to:%d/%m/%Y}, trước ngày kết thúc hành trình",
                          "Gia hạn hợp đồng hoặc chọn xe khác"))
        if v.contract_from and v.contract_from > d1:
            kq.append(_mo("HOP_DONG_CHUA_HIEU_LUC", BLOCK,
                          f"Hợp đồng {v.contract_ref} tới {v.contract_from:%d/%m/%Y} mới hiệu lực"))

    # 3. Giấy tờ xe và giấy phép lái xe – thiếu thì UNKNOWN, hết hạn thì BLOCK.
    _giay(kq, f"xe {v.plate}", VEHICLE_DOCS, _docs(db, v.id, None), d2, chan_khi_thieu_giay)
    did = driver_id or v.driver_id
    if did:
        e = db.get(Employee, did)
        _giay(kq, f"tài xế {e.full_name if e else did}", DRIVER_DOCS, _docs(db, None, did), d2, chan_khi_thieu_giay)
    else:
        kq.append(_mo("CHUA_GAN_TAI_XE", BLOCK if v.op_right == "so_huu" else UNKNOWN,
                      f"Xe {v.plate} chưa gán tài xế",
                      "Gán tài xế; xe hợp tác do đối tác tự lái thì ghi rõ vai trò tài xế của đối tác"))

    # 4. Trùng lịch – điều kiện này đúng bất kể hồ sơ đã nhập đủ hay chưa, nên chặn ngay từ hôm nay.
    for d in trung_lich(db, v.id, d1, d2, bo_qua_lenh):
        kq.append(_mo("TRUNG_LICH", BLOCK,
                      f"Xe {v.plate} đã có lệnh #{d.id} từ {d.date_from:%d/%m} đến {d.date_to:%d/%m}",
                      "Chọn xe khác hoặc hủy lệnh cũ trước"))

    # 5. Việc xác minh đang treo của chính chiếc xe này – không chặn, nhưng người điều hành phải thấy.
    n = db.execute(select(FleetVerification).where(FleetVerification.vehicle_id == v.id,
                                                  FleetVerification.status.in_(["cho_xac_minh", "dang_xu_ly"]))).scalars().all()
    if n:
        kq.append(_mo("CON_VIEC_XAC_MINH", REVIEW,
                      f"Xe {v.plate} còn {len(n)} việc xác minh hồ sơ chưa xong: {n[0].issue[:90]}",
                      "Xem hàng đợi xác minh hồ sơ đội xe"))

    muc = max((k["level"] for k in kq), key=lambda x: NANG[x]) if kq else OK
    return {"muc": muc, "muc_ten": MUC_TEN[muc], "items": kq,
            "ghi_chu": "Thiếu dữ liệu KHÔNG được coi là đạt: mức 'Chưa đủ dữ liệu' nghĩa là hệ thống chưa "
                       "kiểm tra được, không phải đã kiểm tra xong."}


def san_sang(db: Session, v: Vehicle, chan_khi_thieu_giay: bool = False) -> dict:
    """Xe có sẵn sàng khai thác hôm nay không – dùng cho ô đếm trên màn hình tổng quan.

    Đặc tả nói rõ: số xe sẵn sàng KHÔNG mặc định bằng tổng số xe. Nên hàm này trả về ba nhóm chứ không phải
    một số: sẵn sàng, chưa đủ dữ liệu, và bị chặn."""
    r = kiem_tra_dieu_xe(db, v, date.today(), date.today(), chan_khi_thieu_giay=chan_khi_thieu_giay)
    return {"muc": r["muc"], "ly_do": [i["msg"] for i in r["items"] if i["level"] in (BLOCK, UNKNOWN)][:3]}


def bien_hien_hanh(db: Session, vehicle_id: int) -> list[dict]:
    rows = db.execute(select(VehiclePlate).where(VehiclePlate.vehicle_id == vehicle_id)
                      .order_by(VehiclePlate.from_date, VehiclePlate.id)).scalars()
    return [{"plate": p.plate, "from_date": p.from_date, "to_date": p.to_date, "source": p.source,
             "verify": p.verify, "note": p.note} for p in rows]


def doi_bien(db: Session, v: Vehicle, plate_moi: str, tu_ngay: date, nguon: str, boi: str) -> VehiclePlate:
    """Ghi nhận đổi biển mà KHÔNG tạo xe mới – đây chính là điều đặc tả yêu cầu.

    Biển cũ được đóng lại ở ngày liền trước, biển mới mở ra; mã xe, số khung, lịch sử chuyến và khế ước giữ
    nguyên trên cùng một `vehicle_id`."""
    from datetime import timedelta
    cu = db.execute(select(VehiclePlate).where(VehiclePlate.vehicle_id == v.id, VehiclePlate.to_date == None)
                    .order_by(VehiclePlate.id.desc())).scalars().first()
    if cu is None and v.plate:                       # xe có sẵn trong hệ thống nhưng chưa có dòng lịch sử nào
        cu = VehiclePlate(vehicle_id=v.id, plate=v.plate, source="dữ liệu có sẵn trước Đợt 1", created_by=boi)
        db.add(cu); db.flush()
    if cu is not None:
        cu.to_date = tu_ngay - timedelta(days=1)
    moi = VehiclePlate(vehicle_id=v.id, plate=plate_moi, from_date=tu_ngay, source=nguon, created_by=boi)
    db.add(moi)
    v.plate = plate_moi                              # `plate` trên hồ sơ xe = biển ĐANG dùng
    return moi
