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
from datetime import date, datetime, timedelta
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session
from app.models.hr import Vehicle, Employee, DispatchOrder
from app.models.fleet import VehiclePlate, VehicleDocument, FleetVerification, VEHICLE_DOCS, DRIVER_DOCS
from app.services import rules as R

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


def _hang_bang(kq: list, db: Session, g, v) -> None:
    """Hạng trên giấy phép có đủ cho số chỗ của chiếc xe không.

    Ba kết luận, và không có kết luận thứ tư: ĐỦ thì im lặng, KHÔNG ĐỦ thì chặn cứng, CHƯA ĐỌC ĐƯỢC
    thì trả về 'chưa đủ dữ liệu'. Đặc biệt KHÔNG có nhánh 'chắc là đủ' – thiếu hạng hay thiếu ngày
    cấp là thiếu, và người điều hành phải thấy mình đang thiếu cái gì."""
    from app.services.hang_gplx import so_cho_toi_da
    if g is None:
        return                      # thiếu hẳn giấy đã có cổng THIEU_GPLX ở trên, không báo hai lần
    so_cho = v.seats or 0
    if not so_cho:
        kq.append(_mo("XE_CHUA_CO_SO_CHO", UNKNOWN,
                      f"Xe {v.plate} chưa ghi số chỗ nên không đối chiếu được với hạng bằng lái",
                      "Nhập số chỗ của xe trong danh mục"))
        return
    toi_da, ly_do = so_cho_toi_da(g.hang, g.issued_on)
    if toi_da == -1:
        kq.append(_mo("CHUA_DOC_DUOC_HANG_BANG", UNKNOWN,
                      f"Chưa kết luận được hạng bằng lái của tài xế: {ly_do}",
                      "Bổ sung hạng và ngày cấp theo đúng giấy gốc"))
        return
    if toi_da is None:
        return                      # không giới hạn số chỗ
    if so_cho > toi_da:
        kq.append(_mo("HANG_BANG_KHONG_DU", BLOCK,
                      f"Xe {v.plate} có {so_cho} chỗ nhưng bằng lái của tài xế chỉ đủ {toi_da} chỗ "
                      f"({ly_do})",
                      "Đổi tài xế có hạng phù hợp; nâng hạng bằng là việc của người lái, không phải "
                      "việc điều chỉnh trên phần mềm"))


def trung_lich_tai_xe(db: Session, driver_id: int, d1: date, d2: date, bo_qua: int | None = None) -> list[DispatchOrder]:
    """Lệnh còn hiệu lực của cùng một TÀI XẾ chồng ngày với khoảng đang xét.

    Chốt 07/9/2026: không đặt định mức giờ lái cố định (xe chạy theo tour, theo tuyến), nhưng một người vẫn
    không thể ở hai chuyến cùng ngày."""
    q = select(DispatchOrder).where(DispatchOrder.driver_id == driver_id,
                                    DispatchOrder.status.in_(["cho_xac_nhan", "da_xac_nhan"]),
                                    DispatchOrder.date_from <= d2, DispatchOrder.date_to >= d1)
    if bo_qua: q = q.where(DispatchOrder.id != bo_qua)
    return list(db.execute(q).scalars())


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
    # 4b. Trùng lịch TÀI XẾ. Chốt 07/9/2026: bỏ ràng buộc giờ lái liên tục (xe chạy theo tour, theo tuyến),
    # nhưng GIỮ ràng buộc một tài xế không nhận hai lệnh chồng ngày. Không có ràng buộc này thì một người bị
    # xếp hai chuyến cùng ngày và chỉ vỡ ra vào sáng hôm khởi hành.
    if did:
        for d in trung_lich_tai_xe(db, did, d1, d2, bo_qua_lenh):
            kq.append(_mo("TAI_XE_TRUNG_LICH", BLOCK,
                          f"Tài xế đã có lệnh #{d.id} từ {d.date_from:%d/%m} đến {d.date_to:%d/%m}",
                          "Chọn tài xế khác hoặc dời lịch"))
    # 4c. Mốc bảo dưỡng (chặn cứng B3 của đặc tả). Chưa biết mốc thì là CHƯA ĐỦ DỮ LIỆU, không phải là đạt –
    # đây đúng là chỗ dễ mặc định thành "không sao" rồi để xe chạy quá kỳ mà không ai biết.
    bd = moc_bao_duong(db, v)
    if bd["km_ky_toi"] is None:
        kq.append(_mo("CHUA_BIET_MOC_BAO_DUONG", UNKNOWN,
                      f"Xe {v.plate}: {bd.get('ghi_chu', 'chưa xác định được mốc bảo dưỡng kỳ tới')}",
                      "Nhập phiếu bảo dưỡng gần nhất kèm số km lúc làm"))
    elif not v.odo_km:
        kq.append(_mo("CHUA_CO_SO_KM", UNKNOWN,
                      f"Xe {v.plate} chưa có số km đồng hồ đã xác nhận nên không so được với mốc bảo dưỡng",
                      "Cập nhật số km đồng hồ trước khi lập kế hoạch mới"))
    elif v.odo_km > bd["km_ky_toi"]:
        kq.append(_mo("VUOT_MOC_BAO_DUONG", BLOCK,
                      f"Xe {v.plate} đã ở {v.odo_km:,} km, vượt mốc bảo dưỡng {bd['km_ky_toi']:,} km",
                      "Làm bảo dưỡng hoặc đổi xe khác"))
    else:
        con = bd["km_ky_toi"] - v.odo_km
        gap = int(R.get_param(db, "xe_bd_gap_km"))
        if con <= gap:
            kq.append(_mo("SAP_TOI_MOC_BAO_DUONG", REVIEW,
                          f"Xe {v.plate} còn {con:,} km tới mốc bảo dưỡng {bd['km_ky_toi']:,} km",
                          "Đặt lịch garage trước khi phát lệnh dài ngày"))

    # 4d. Giấy tờ sắp hết hạn – vàng/đỏ theo tham số chính sách, tách khỏi nhánh ĐÃ hết hạn ở trên.
    vang = int(R.get_param(db, "xe_giay_to_vang_ngay")); do = int(R.get_param(db, "xe_giay_to_do_ngay"))
    for kind, ten in VEHICLE_DOCS.items():
        g = _docs(db, v.id, None).get(kind)
        if g and g.expires_on: _han_giay(kq, f"xe {v.plate}", ten, g.expires_on, d2, vang, do)
    if did:
        g = _docs(db, None, did).get("gplx")
        if g and g.expires_on: _han_giay(kq, "tài xế", "Giấy phép lái xe", g.expires_on, d2, vang, do)
        # 4e. HẠNG bằng có đủ cho số chỗ của chiếc xe này không.
        #
        # Trước bản này hệ thống chỉ hỏi "giấy còn hạn không". Một tấm giấy còn hạn mười năm mà hạng
        # chỉ đủ 30 chỗ vẫn không cho phép cầm lái xe 45 chỗ – và đó mới là câu hỏi mà 45 hành khách
        # trên xe quan tâm. Xem app/services/hang_gplx.py về việc chữ D đảo nghĩa giữa hai luật.
        _hang_bang(kq, db, g, v)

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


# ====================== ĐỢT 2: KHỚP NGUỒN NGOÀI, BẢO DƯỠNG, CANH HẠN GIẤY TỜ ======================
from datetime import datetime, timedelta
from app.models.fleet import (Trip, TripCost, Maintenance, ExternalTxn, BEN_CHIU_MAC_DINH, COST_KINDS)


def chuan_bien(bien: str) -> str:
    """Biển số về một dạng duy nhất để so khớp: bỏ dấu cách, gạch, chấm và viết hoa.

    Cùng một chiếc xe được ghi ba kiểu ở ba nguồn – "50F-017.37" trong VTOS, "50F 017.37" trên phần mềm
    Vietrip, "50F01737" trong nội dung chuyển khoản. So khớp nguyên văn thì cả ba đều là ba xe khác nhau,
    và tiền của một chiếc bị chẻ làm ba chỗ không ai cộng lại được. Chỉ dùng để SO KHỚP – biển số vẫn được
    lưu nguyên văn theo nguồn, vì đó mới là cái đối chiếu được với giấy tờ."""
    return "".join(c for c in (bien or "").upper() if c.isalnum())


def xe_theo_bien(db: Session, bien: str, luc: date):
    """Tra xe từ biển số TẠI THỜI ĐIỂM giao dịch, không theo biển hiện tại.

    Đây là chỗ đối soát ePass vỡ nếu làm sai: xe đổi biển giữa kỳ mà tra theo biển hiện tại thì toàn bộ giao
    dịch nửa đầu kỳ rơi ra ngoài, và người đối chiếu sẽ đi tìm một khoản tiền không thuộc về ai."""
    b = chuan_bien(bien)
    if not b: return None
    rows = [p for p in db.execute(select(VehiclePlate)).scalars() if chuan_bien(p.plate) == b]
    for p in rows:
        if (p.from_date is None or p.from_date <= luc) and (p.to_date is None or luc <= p.to_date):
            return db.get(Vehicle, p.vehicle_id)
    if rows:                                   # có trong lịch sử nhưng ngoài khoảng ngày đã ghi
        return db.get(Vehicle, rows[0].vehicle_id)
    return next((v for v in db.execute(select(Vehicle)).scalars() if chuan_bien(v.plate) == b), None)


def nhap_giao_dich(db: Session, source: str, rows: list[dict], boi: str) -> dict:
    """Nhập giao dịch nguồn ngoài, khử trùng theo mã giao dịch gốc.

    Bản ghi trùng KHÔNG bị bỏ đi: nó được ghi với cờ `trung=True` và trỏ về bản gốc. Bỏ đi là mất khả năng
    chứng minh mình đã loại đúng cái gì – mà đây là dữ liệu dùng để chi tiền cho đối tác."""
    da_co = {(t.source, t.ma_gd): t.id for t in
             db.execute(select(ExternalTxn).where(ExternalTxn.source == source, ExternalTxn.trung == False)).scalars()}
    them = trung = 0
    for r in rows:
        ma = (r.get("ma_gd") or "").strip()
        if not ma: continue
        luc = r.get("thoi_diem")
        if isinstance(luc, str): luc = datetime.fromisoformat(luc)
        goc = da_co.get((source, ma))
        v = None
        if r.get("bien_so"): v = xe_theo_bien(db, r["bien_so"], luc.date())
        elif r.get("the_4so"):
            v = db.execute(select(Vehicle).join(Employee, Employee.id == Vehicle.driver_id)
                           .where(Employee.fuel_card_last4 == r["the_4so"])).scalars().first()
        khong_cp = bool(r.get("khong_phai_chi_phi"))
        t = ExternalTxn(source=source, ma_gd=ma, tai_khoan=r.get("tai_khoan", ""), the_4so=r.get("the_4so", ""),
                        bien_so=r.get("bien_so", ""), vehicle_id=v.id if v else None, thoi_diem=luc,
                        so_tien=float(r.get("so_tien") or 0), lit=float(r.get("lit") or 0),
                        mo_ta=r.get("mo_ta", ""), imported_by=boi,
                        nhom=r.get("nhom", ""), khong_phai_chi_phi=khong_cp,
                        trung=goc is not None, trung_cua_id=goc,
                        co="do" if (goc is None and v is None and not khong_cp) else "vang",
                        ghi_chu=("Bản ghi lặp – giữ lại để đối chiếu, KHÔNG đưa vào tính toán" if goc
                                 else ("Khoản điều chuyển tiền nội bộ – không phải chi phí, không quy về xe"
                                       if khong_cp else
                                       ("Chưa tra được xe từ biển số/số thẻ tại thời điểm giao dịch"
                                        if v is None else ""))))
        db.add(t); db.flush()
        if goc is None:
            da_co[(source, ma)] = t.id; them += 1
        else:
            trung += 1
    return {"da_nhap": them, "ban_ghi_lap": trung,
            "ghi_chu": "Bản ghi lặp được giữ trong bảng thô với cờ trùng và không cộng vào số liệu tính toán. "
                       "Dòng đánh dấu không_phải_chi_phí (điều chuyển tiền nội bộ) cũng được giữ nhưng "
                       "không cộng vào tổng chi phí."}


def moc_bao_duong(db: Session, v: Vehicle) -> dict:
    """Mốc km của kỳ bảo dưỡng tới. Lấy từ lần bảo dưỡng gần nhất; chưa có lần nào thì CHƯA BIẾT.

    Đặc tả cấm dùng 9.000 km cố định cho mọi xe vì nguồn ghi các mốc khác nhau – nên chu kỳ trong tham số chỉ
    dùng khi chính lần bảo dưỡng trước không ghi mốc kế tiếp."""
    bd = db.execute(select(Maintenance).where(Maintenance.vehicle_id == v.id, Maintenance.kind == "dinh_ky")
                    .order_by(Maintenance.ngay.desc(), Maintenance.id.desc())).scalars().first()
    if bd is None:
        return {"km_ky_toi": None, "nguon": "chua_co_lich_su",
                "ghi_chu": "Chưa có lịch sử bảo dưỡng nên chưa biết mốc kỳ tới – không suy ra từ chu kỳ chung"}
    if bd.km_ky_toi:
        return {"km_ky_toi": bd.km_ky_toi, "nguon": "ghi_tren_phieu", "lan_truoc": bd.ngay}
    if bd.km_luc_lam:
        chu_ky = int(R.get_param(db, "xe_chu_ky_bao_duong_km"))
        return {"km_ky_toi": bd.km_luc_lam + chu_ky, "nguon": "chu_ky_chung", "lan_truoc": bd.ngay,
                "ghi_chu": f"Phiếu lần trước không ghi mốc kế tiếp – tạm lấy chu kỳ chung {chu_ky:,} km"}
    return {"km_ky_toi": None, "nguon": "phieu_thieu_km",
            "ghi_chu": "Phiếu bảo dưỡng lần trước không ghi số km lúc làm – không tính được mốc kỳ tới"}


def _han_giay(kq: list, chu_the: str, ten: str, het: date, den_ngay: date, vang: int, do: int):
    con = (het - date.today()).days
    if het < den_ngay:
        return                                   # đã có nhánh HET_HAN xử lý ở kiểm tra Đợt 1
    if con <= do:
        kq.append(_mo(f"SAP_HET_HAN_{ten}", REVIEW, f"{ten} của {chu_the} còn {con} ngày (hết {het:%d/%m/%Y})",
                      "Gia hạn ngay – dưới ngưỡng đỏ theo tham số chính sách"))
    elif con <= vang:
        kq.append(_mo(f"GAN_HET_HAN_{ten}", REVIEW, f"{ten} của {chu_the} còn {con} ngày (hết {het:%d/%m/%Y})",
                      "Đưa vào lịch gia hạn"))


def kiem_chuyen(db: Session, t) -> dict:
    """Chấm cờ cho một chuyến theo ba mức xanh / vàng / đỏ của đặc tả §1.

    Nguyên tắc giữ nguyên từ Đợt 1: thiếu số đo KHÔNG ra màu xanh. Một chuyến chưa đọc được km mà hiện xanh
    thì người xác nhận tin rằng đã đối chiếu xong."""
    ly_do: list[str] = []; muc = "xanh"

    def vang(m):
        nonlocal muc
        ly_do.append(m)
        if muc == "xanh": muc = "vang"

    def do(m):
        nonlocal muc
        ly_do.append(m); muc = "do"

    if t.km_dau is None or t.km_cuoi is None:
        vang("Chưa có đủ số km đầu/cuối – chưa tính được quãng đường thực tế")
    else:
        km = t.km_cuoi - t.km_dau
        if km < 0:
            do(f"Km cuối nhỏ hơn km đầu ({t.km_cuoi:,} < {t.km_dau:,})")
        elif t.km_gps:
            lech = abs(km - t.km_gps) / t.km_gps if t.km_gps else 0
            nguong = R.get_param(db, "xe_lech_km_gps")
            if lech > nguong:
                do(f"Km đọc từ đồng hồ lệch GPS {lech*100:.1f}% (ngưỡng {nguong*100:.0f}%)")
        # Nối chuyến: km cuối chuyến trước phải khớp km đầu chuyến sau của cùng chiếc xe.
        truoc = db.execute(select(Trip).where(Trip.vehicle_id == t.vehicle_id, Trip.id != t.id,
                                              Trip.ngay_ve <= t.ngay_di)
                           .order_by(Trip.ngay_ve.desc(), Trip.id.desc())).scalars().first()
        if truoc is not None and truoc.km_cuoi is not None and t.km_dau is not None:
            hut = t.km_dau - truoc.km_cuoi
            nguong_km = int(R.get_param(db, "xe_lech_km_noi_chuyen"))
            if abs(hut) > nguong_km:
                vang(f"Km đầu chuyến này lệch km cuối chuyến trước {hut:,} km – có thể có chuyến chưa khai báo, "
                     f"hoặc chặng chạy rỗng/đi garage chưa ghi")

    cps = list(db.execute(select(TripCost).where(TripCost.trip_id == t.id)).scalars())
    nguong_ct = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    for c in cps:
        if (c.amount or 0) >= nguong_ct and not (c.chung_tu or "").strip():
            do(f"{COST_KINDS.get(c.kind, c.kind)} {c.amount:,.0f} đ không có chứng từ gốc (chặn cứng B6)")
    # Tiêu hao nhiên liệu ngoài dải hợp lý – chỉ chấm khi có ĐỦ cả số lít lẫn quãng đường.
    lit = sum(c.lit for c in cps if c.kind == "dau")
    if lit > 0 and t.km_dau is not None and t.km_cuoi is not None and t.km_cuoi > t.km_dau:
        km_l = (t.km_cuoi - t.km_dau) / lit
        lo = R.get_param(db, "xe_tieu_hao_min"); hi = R.get_param(db, "xe_tieu_hao_max")
        if km_l < lo or km_l > hi:
            vang(f"Tiêu hao {km_l:.2f} km/lít nằm ngoài dải hợp lý {lo}–{hi} km/lít")
    if not cps:
        vang("Chuyến chưa có dòng chi phí nào")
    return {"co": muc, "ly_do": ly_do}


def nguoi_duoc_lap_lenh(db: Session) -> tuple[list, str]:
    """Ai được tạo và chốt lệnh điều xe (chỉ đạo Chủ tịch 07/9/2026).

    Tham số `xe_nguoi_lap_lenh` nhận tài khoản hoặc mã nhân viên, ngăn bởi dấu phẩy. Ghi trong tham số chứ
    không viết tên người vào mã: thay người phụ trách thì sửa một dòng cấu hình, không phải triển khai lại.

    Nếu tham số có giá trị nhưng KHÔNG khớp tài khoản đang hoạt động nào (dữ liệu demo, hoặc người phụ trách
    đã nghỉ), hàm trả về danh sách rỗng kèm lý do. Nơi gọi khi đó giữ quy tắc theo vai trò như cũ và NÓI RA –
    im lặng bỏ qua thì chỉ đạo "chỉ một người" âm thầm hết hiệu lực mà không ai biết; còn chặn sạch thì cả
    đội xe đứng vì một ô cấu hình gõ sai."""
    from app.models.core import User as U
    raw = (R.get_param_text(db, "xe_nguoi_lap_lenh") or "").strip()
    if not raw:
        return [], "Chưa cấu hình người lập lệnh – áp dụng quy tắc theo vai trò"
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    users = list(db.execute(select(U).where(U.active == True,
                                            or_(U.username.in_(keys), U.staff_code.in_(keys)))).scalars())
    if not users:
        return [], (f"Tham số xe_nguoi_lap_lenh đang đặt là \"{raw}\" nhưng không khớp tài khoản đang hoạt "
                    "động nào – tạm áp dụng quy tắc theo vai trò, cần sửa lại tham số")
    return users, ""


# ====================== NẠP NHẬT TRÌNH TỪ BÁO CÁO NGOÀI ======================
CHI_PHI_CHUYEN = {"dau": "dau", "cau_duong": "cau_duong", "cong_tac_phi": "cong_tac_phi", "giu_xe": "giu_xe"}


def nhap_chuyen_hang_loat(db: Session, nguon: str, rows: list[dict], boi: str,
                          tao_xe_thieu: bool = False) -> dict:
    """Nạp nhật trình chuyến từ một báo cáo bên ngoài (ví dụ báo cáo quyết toán xe của VieTrip).

    Ba điều tệp này giữ, vì nạp dữ liệu là lúc dễ làm hỏng sổ nhất:

      1. `ma_phieu` DUY NHẤT: nạp lại cùng một báo cáo không sinh ra bộ chuyến thứ hai. Đây là lỗi tốn kém
         nhất của mọi lần nạp dữ liệu – doanh thu và chi phí đều nhân đôi, và không ai nhìn ra ngay.
      2. KHÔNG tự tạo xe từ biển số trong file, trừ khi người nạp nói rõ. Một biển gõ sai mà hệ thống tự tạo
         xe mới thì từ đó có hai chiếc xe cùng tồn tại và số liệu chia đôi.
      3. Chuyến thiếu ngày KHÔNG bị bỏ im lặng: bỏ đi là mất doanh thu khỏi báo cáo mà không ai biết. Người
         nạp phải gửi kèm ngày tạm và ghi chú; hệ thống gắn cờ đỏ để còn nhớ mà sửa.
    """
    from app.models.fleet import Trip, TripCost
    da_co = {t.ma_phieu for t in db.execute(select(Trip).where(Trip.ma_phieu.isnot(None))).scalars()}
    them = bo_qua = 0
    thieu_xe: dict[str, int] = {}
    da_tao_xe: list[str] = []
    ket = []
    for r in rows:
        ma = (r.get("ma_phieu") or "").strip()
        if not ma:
            raise ValueError("Mỗi dòng phải có mã phiếu gốc – không có thì không chống được nạp trùng")
        if ma in da_co:
            bo_qua += 1; continue
        bien = (r.get("bien_so") or "").strip()
        d1 = r.get("ngay_di"); d2 = r.get("ngay_ve")
        if isinstance(d1, str): d1 = date.fromisoformat(d1)
        if isinstance(d2, str): d2 = date.fromisoformat(d2)
        if d1 is None or d2 is None:
            raise ValueError(f"Phiếu {ma} thiếu ngày đi hoặc ngày về – nguồn không ghi thì phải xử lý ở nguồn, "
                             "hệ thống không tự đoán ngày")
        v = xe_theo_bien(db, bien, d1)
        if v is None:
            if not tao_xe_thieu:
                thieu_xe[bien] = thieu_xe.get(bien, 0) + 1
                continue
            v = Vehicle(plate=bien.strip().upper(), seats=int(r.get("so_cho") or 45), kind="noi_bo",
                        op_right="so_huu", lifecycle="dang_khai_thac",
                        source_note=f"Tạo khi nạp {nguon}")
            db.add(v); db.flush()
            db.add(VehiclePlate(vehicle_id=v.id, plate=v.plate, from_date=d1,
                                source=f"Nạp từ {nguon}", verify="nguon_ghi"))
            da_tao_xe.append(v.plate)

        t = Trip(vehicle_id=v.id, driver_id=v.driver_id, ten_tour=(r.get("ten_tour") or "")[:160],
                 ngay_di=d1, ngay_ve=d2, km_dau=r.get("km_dau"), km_cuoi=r.get("km_cuoi"),
                 km_nguon="nhap_tay", doanh_thu=float(r.get("doanh_thu") or 0),
                 status="da_xac_nhan", confirmed_at=datetime.now(), confirmed_by=boi,
                 ma_phieu=ma, nguon=nguon, note=(r.get("note") or "")[:300],
                 created_by=boi)
        db.add(t); db.flush()
        cp = r.get("chi_phi") or {}
        for kind in CHI_PHI_CHUYEN:
            tien = float(cp.get(kind) or 0)
            if tien <= 0: continue
            db.add(TripCost(trip_id=t.id, kind=kind, amount=tien,
                            lit=float(cp.get("lit") or 0) if kind == "dau" else 0,
                            ben_chiu="vietourist_tam_ung", nguon=nguon,
                            chung_tu=ma, created_by=boi))
        db.flush()
        kt = kiem_chuyen(db, t)
        t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
        if r.get("co") == "do":                      # nguồn đã báo là dữ liệu chưa đủ
            t.co = "do"
            t.co_ly_do = ((r.get("co_ly_do") or "") + (" · " + t.co_ly_do if t.co_ly_do else ""))[:2000]
        da_co.add(ma); them += 1
        ket.append({"ma_phieu": ma, "trip_id": t.id, "xe": v.plate, "co": t.co})
    return {"da_nhap": them, "bo_qua_da_co": bo_qua,
            "xe_khong_tra_ra": [{"bien_so": b, "so_phieu": n} for b, n in sorted(thieu_xe.items())],
            "da_tao_xe": da_tao_xe, "chi_tiet": ket,
            "ghi_chu": ("Phiếu đã có mã trong hệ thống thì BỎ QUA, không ghi đè – nạp lại cùng báo cáo "
                        "không nhân đôi doanh thu. Biển số không tra ra xe thì KHÔNG tự tạo xe, mà báo ra "
                        "để người nạp quyết.")}
