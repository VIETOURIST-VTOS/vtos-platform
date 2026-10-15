# -*- coding: utf-8 -*-
"""DL-5 — ĐỔI XE / ĐỔI TÀI XẾ trên một lệnh điều xe đã lập.

Chủ tịch chốt 15/10/2026, sau khi đo lại phân hệ điều hành: cửa sửa lệnh (`dispatch_update`) chỉ
nhận ĐÚNG HAI thứ — `status` và `incident_note`. Không có đường nào đổi xe hay đổi tài xế. Nên khi
xe hỏng trước giờ khởi hành, Điều hành phải XOÁ lệnh rồi LẬP LẠI: mất dấu lệnh cũ, mất dấu ai đã
nhận, và tháng sau không ai trả lời được vì sao đổi.

Ba quyết định của Chủ tịch (15/10/2026):

  1. Đổi được ở `cho_xac_nhan` VÀ `da_xac_nhan`. Chặn ở `hoan_thanh` và `huy`.
     Lý do chặn `hoan_thanh` không phải vì sợ: lệnh hoàn thành ĐÃ SINH RA một chuyến trong nhật
     trình (DL-3). Đổi xe lúc ấy là sửa lịch sử, và doanh thu đội xe tháng ấy đổi theo. Nếu thật
     sự cần, đó là một việc riêng có tên riêng, không phải nhánh `if` nối thêm vào cửa này.
  2. Giá nội bộ TÍNH LẠI theo xe mới, và trả về CẢ giá cũ lẫn giá mới để màn hình hiện ra.
  3. Có cửa ĐỔI TÀI XẾ riêng, giữ nguyên xe.

═══════════════════════════════════════════════════════════════════════════════════════════════
MỘT PHÉP TÍNH GIÁ, MỘT CHỖ
═══════════════════════════════════════════════════════════════════════════════════════════════

Giá nội bộ phụ thuộc LOẠI XE: `hop_tac` ăn `partner_price` của tuyến, xe nhà ăn `internal_price`.
Phép tính ấy đang nằm thẳng trong `dispatch_create`. Chép nó sang đây là đúng cái hình đã làm hỏng
cửa xoá lệnh hôm 15/10 — chép dáng mà sót một dòng, rồi mười hai phép thử vẫn xanh. Nên phép tính
được RÚT RA thành `tinh_gia()` và CẢ HAI cửa gọi chung. Sửa công thức giá sau này là sửa một chỗ.

═══════════════════════════════════════════════════════════════════════════════════════════════
HAI CÁCH KIỂM KHÁC NHAU, CÓ CHỦ ĐÍCH
═══════════════════════════════════════════════════════════════════════════════════════════════

ĐỔI XE — xe mới phải tự đứng được. Chạy `kiem_tra_dieu_xe` cho xe mới, mức BLOCK thì chặn thật,
không có nút vượt riêng. Nếu không thì ai muốn lách hàng rào chỉ cần lập lệnh bằng xe sạch rồi đổi
sang xe hết đăng kiểm — cửa đổi thành cửa sau của cửa lập.

ĐỔI TÀI XẾ — xe KHÔNG đổi, nên bắt lệnh phải sạch toàn bộ là bắt người đổi gánh một lỗi có từ
trước. Tài xế bệnh lúc 10 giờ đêm mà cửa báo «đăng kiểm xe hết hạn tháng sau» rồi không cho đổi
người thì cửa ấy vô dụng. Luật ở đây là **ĐỔI KHÔNG ĐƯỢC LÀM LỆNH XẤU ĐI**: chạy kiểm hai lần —
một lần với tài xế cũ, một lần với tài xế mới — và chỉ chặn trên những vi phạm MỚI SINH RA. Luật
này không đọc tên mã vi phạm, nên thêm một điều kiện tài xế vào tháng sau là nó tự che.

`bo_qua_lenh=d.id` là bắt buộc ở cả hai: không bỏ qua chính nó thì lệnh đang sửa tự báo mình
trùng lịch với mình.

KHOÁ PHIÊN BẢN KHÔNG NẰM Ở ĐÂY mà ở cửa (`hr._doi`), có chủ đích. Khoá ấy so bản người gọi đang
cầm với bản trong kho — chỉ cửa mới nhận được "bản người gọi đang cầm". Tăng phiên bản trong dịch
vụ, nơi không ai kiểm, là tăng một con số mà không ai so: đúng hình "có cột mà không ai đọc".

═══════════════════════════════════════════════════════════════════════════════════════════════
TÀI XẾ ĐI THEO XE
═══════════════════════════════════════════════════════════════════════════════════════════════

`dispatch_create` lấy `driver_id = v.driver_id`. Nên đổi xe thì tài xế đổi theo — đó là điều đúng
với đội xe (người quen xe nào chạy xe ấy) nhưng phải NÓI RA, vì người bấm đang nghĩ mình chỉ đổi
một thứ. Muốn giữ người mà đổi xe thì dùng hai cửa liên tiếp.

Xe `hop_tac` có thể không có tài xế trong hồ sơ. `dispatch_create` lúc ấy tạm gắn một nhân sự đội
xe để có chỗ ghi. Ở đây KHÔNG lặp lại mẹo ấy: giữ nguyên tài xế đang có trên lệnh. Gắn lại một
người thứ hai cho cùng một lệnh chỉ làm sổ trùng lịch thêm một người không liên quan.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr import DispatchOrder, Employee, Vehicle, VehicleRate
from app.services import fleet as FL
from app.services import nhan_lenh as NL

# Hai trạng thái đổi được (Chủ tịch chốt 15/10/2026). Để thành hằng số có tên vì phép thử đọc
# chính nó — thêm một trạng thái vào đây mà quên phép thử thì phép thử sẽ đỏ, không im lặng.
TRANG_THAI_DOI_DUOC = ("cho_xac_nhan", "da_xac_nhan")

TRANG_THAI_TEN = {"cho_xac_nhan": "chờ xác nhận", "da_xac_nhan": "đã xác nhận",
                  "hoan_thanh": "hoàn thành", "huy": "đã huỷ"}


class KhongDoiDuoc(ValueError):
    """Cửa từ chối. Nơi gọi đổi thành HTTP 422 kèm nguyên văn câu này."""


class ViPhamDieuKien(ValueError):
    """Xe mới (hoặc tài xế mới) vướng điều kiện mức chặn. Mang theo danh sách vi phạm."""

    def __init__(self, thong_diep: str, vi_pham: list[dict]):
        super().__init__(thong_diep)
        self.vi_pham = vi_pham


# ─────────────────────────────────────────────────────────────────────────────────────────────
def tinh_gia(v: Vehicle, rt: VehicleRate | None, d1: date, d2: date,
             gia_tay: float | None = None) -> float:
    """Giá thuê nội bộ cả chuyến. MỘT phép tính dùng chung cho cửa lập lệnh và cửa đổi xe.

    Có tuyến trong bảng giá thì lấy theo bảng giá — `hop_tac` ăn giá đối tác, xe nhà ăn giá nội
    bộ. Không có tuyến thì lấy giá người nhập tay, không có nữa thì đơn giá ngày × số ngày.
    """
    if rt:
        gia = rt.partner_price if v.kind == "hop_tac" else rt.internal_price
        if (gia or 0) <= 0:
            raise KhongDoiDuoc(f"Tuyến {rt.route} không có giá cho loại xe {v.kind}")
        return gia
    return (gia_tay or 0) or (v.internal_rate_per_day or 0) * ((d2 - d1).days + 1)


def _chan_khi_thieu_giay(db: Session) -> bool:
    from app.services import rules as R
    return bool(R.get_param(db, "xe_chan_khi_thieu_giay"))


def _kiem(db: Session, d: DispatchOrder, v: Vehicle, driver_id: int | None) -> dict:
    return FL.kiem_tra_dieu_xe(db, v, d.date_from, d.date_to, driver_id,
                               bo_qua_lenh=d.id,
                               chan_khi_thieu_giay=_chan_khi_thieu_giay(db))


def _ten(db: Session, nv_id: int | None) -> str:
    if not nv_id:
        return ""
    nv = db.get(Employee, nv_id)
    return nv.full_name if nv else ""


def _dung_trang_thai(d: DispatchOrder) -> None:
    if d.status not in TRANG_THAI_DOI_DUOC:
        ten = TRANG_THAI_TEN.get(d.status, d.status)
        them = ("" if d.status != "hoan_thanh" else
                " – lệnh đã hoàn thành thì đã sinh chuyến trong nhật trình, đổi xe lúc này là sửa "
                "lịch sử và đổi doanh thu đội xe của tháng")
        raise KhongDoiDuoc(f"Lệnh đang {ten} nên không đổi được{them}")


def _dung_ly_do(ly_do: str) -> str:
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise KhongDoiDuoc("Phải ghi lý do đổi – không có ô này thì đổi xe chỉ là một cách xoá "
                           "dấu vết êm hơn xoá lệnh")
    return ly_do


# ─────────────────────────────────────────────────────────────────────────────────────────────
def soat_doi_xe(db: Session, d: DispatchOrder, xe_moi: Vehicle) -> dict:
    """CHỈ ĐỌC – dựng bảng «cũ → mới» cho màn hình xác nhận. Không ghi gì."""
    xe_cu = db.get(Vehicle, d.vehicle_id)
    rt = db.get(VehicleRate, d.rate_id) if d.rate_id else None
    try:
        gia_moi = tinh_gia(xe_moi, rt, d.date_from, d.date_to, d.internal_price)
        loi_gia = ""
    except KhongDoiDuoc as ex:
        gia_moi, loi_gia = None, str(ex)
    kt = _kiem(db, d, xe_moi, xe_moi.driver_id)
    return {
        "doi_duoc": d.status in TRANG_THAI_DOI_DUOC,
        "trang_thai": d.status, "trang_thai_ten": TRANG_THAI_TEN.get(d.status, d.status),
        "xe_cu": xe_cu.plate if xe_cu else "", "xe_moi": xe_moi.plate,
        "tai_xe_cu": _ten(db, d.driver_id), "tai_xe_moi": _ten(db, xe_moi.driver_id),
        "tai_xe_doi_theo": (xe_moi.driver_id or d.driver_id) != d.driver_id,
        "gia_cu": float(d.internal_price) if d.internal_price is not None else None,
        "gia_moi": float(gia_moi) if gia_moi is not None else None,
        "loi_gia": loi_gia,
        "muc": kt["muc"], "muc_ten": kt["muc_ten"],
        "vi_pham": [i for i in kt["items"] if i["level"] == FL.BLOCK],
        "canh_bao": [i["msg"] for i in kt["items"] if i["level"] != FL.BLOCK],
        "se_xoa_dau_nhan": d.nhan_luc is not None or bool((d.tu_choi_nhan_ly_do or "").strip()),
    }


def doi_xe(db: Session, d: DispatchOrder, xe_moi: Vehicle, ly_do: str, boi: str = "") -> dict:
    """Đổi xe của một lệnh đã lập. Gọi trong cùng giao dịch với `db.commit()` của nơi gọi."""
    _dung_trang_thai(d)
    ly_do = _dung_ly_do(ly_do)
    if xe_moi.id == d.vehicle_id:
        raise KhongDoiDuoc(f"Lệnh đang là xe {xe_moi.plate} rồi")

    kt = _kiem(db, d, xe_moi, xe_moi.driver_id)
    if kt["muc"] == FL.BLOCK:
        raise ViPhamDieuKien(f"Xe {xe_moi.plate} không đủ điều kiện nhận lệnh này",
                             [i for i in kt["items"] if i["level"] == FL.BLOCK])

    rt = db.get(VehicleRate, d.rate_id) if d.rate_id else None
    gia_moi = tinh_gia(xe_moi, rt, d.date_from, d.date_to, d.internal_price)

    xe_cu = db.get(Vehicle, d.vehicle_id)
    truoc = {"xe": xe_cu.plate if xe_cu else "", "tai_xe": _ten(db, d.driver_id),
             "gia_noi_bo": float(d.internal_price) if d.internal_price is not None else None}

    d.vehicle_id = xe_moi.id
    # Tài xế đi theo xe. Xe hợp tác không có tài xế trong hồ sơ thì GIỮ NGUYÊN người đang ghi
    # trên lệnh – xem phần đầu tệp, không gắn bừa người thứ hai.
    if xe_moi.driver_id:
        d.driver_id = xe_moi.driver_id
    d.internal_price = gia_moi
    d.phuong_an_da_chon = xe_moi.code or xe_moi.plate
    da_xoa = NL.xoa_dau_nhan(db, d, f"đổi xe sang {xe_moi.plate}", boi)
    db.flush()

    sau = {"xe": xe_moi.plate, "tai_xe": _ten(db, d.driver_id), "gia_noi_bo": float(gia_moi)}
    return _ket_qua(db, d, "doi_xe", truoc, sau, ly_do, da_xoa, kt, boi)


def doi_tai_xe(db: Session, d: DispatchOrder, nv_moi: Employee, ly_do: str, boi: str = "") -> dict:
    """Đổi tài xế, GIỮ NGUYÊN xe. Giá không đổi – giá tính theo xe và tuyến, không theo người lái."""
    _dung_trang_thai(d)
    ly_do = _dung_ly_do(ly_do)
    if nv_moi.id == d.driver_id:
        raise KhongDoiDuoc(f"Lệnh đang là tài xế {nv_moi.full_name} rồi")
    if not nv_moi.active:
        raise KhongDoiDuoc(f"{nv_moi.full_name} không còn hoạt động trong danh mục nhân sự")
    if nv_moi.department != "doi_xe":
        raise KhongDoiDuoc(f"{nv_moi.full_name} không thuộc đội xe")

    v = db.get(Vehicle, d.vehicle_id)
    if not v:
        raise KhongDoiDuoc("Lệnh không còn xe trong danh mục")
    # ĐỔI KHÔNG ĐƯỢC LÀM LỆNH XẤU ĐI: chỉ chặn trên vi phạm MỚI SINH RA, không bắt người đổi
    # tài xế gánh lỗi của xe đã có từ trước. Xem phần đầu tệp.
    cu = {i["code"] for i in _kiem(db, d, v, d.driver_id)["items"] if i["level"] == FL.BLOCK}
    kt = _kiem(db, d, v, nv_moi.id)
    moi = [i for i in kt["items"] if i["level"] == FL.BLOCK and i["code"] not in cu]
    if moi:
        raise ViPhamDieuKien(f"Đổi sang {nv_moi.full_name} làm lệnh vướng thêm điều kiện", moi)

    truoc = {"tai_xe": _ten(db, d.driver_id)}
    d.driver_id = nv_moi.id
    da_xoa = NL.xoa_dau_nhan(db, d, f"đổi tài xế sang {nv_moi.full_name}", boi)
    db.flush()
    return _ket_qua(db, d, "doi_tai_xe", truoc, {"tai_xe": nv_moi.full_name},
                    ly_do, da_xoa, kt, boi)


def _ket_qua(db: Session, d: DispatchOrder, viec: str, truoc: dict, sau: dict,
             ly_do: str, da_xoa: bool, kt: dict, boi: str) -> dict:
    """Ghi MỘT dòng nhật ký mang cả cũ lẫn mới, rồi trả về đúng những gì màn hình cần nói lại.

    Ghi cả hai vế vào cùng một dòng, không phải hai dòng: đọc nhật ký để trả lời «tháng trước ai
    đổi xe gì sang xe gì» mà phải ghép hai dòng cạnh nhau là chỗ người ta ghép nhầm.
    """
    from app.services import rules as R
    R.audit(db, boi, "", viec, f"dispatch:{d.id}",
            before=truoc, after={**sau, "ly_do": ly_do, "phien_ban": d.phien_ban})
    noi = " · ".join(f"{k}: {truoc.get(k) or '(trống)'} → {sau[k]}" for k in sau if k in truoc)
    if da_xoa:
        noi += " · dấu nhận của tài xế đã được xoá, lệnh cần tài xế nhận lại"
    return {"viec": viec, "truoc": truoc, "sau": sau, "ly_do": ly_do,
            "xoa_dau_nhan": da_xoa, "phien_ban": d.phien_ban, "noi": noi,
            "canh_bao": [i["msg"] for i in kt["items"] if i["level"] != FL.BLOCK]}


# ─────────────────────────────────────────────────────────────────────────────────────────────
def xe_thay_the_duoc(db: Session, d: DispatchOrder) -> list[dict]:
    """Danh sách xe thay thế được cho màn hình. KHÔNG lọc sẵn xe vướng điều kiện — in kèm mức.

    Lọc sẵn thì người điều hành thấy một danh sách ngắn mà không hiểu vì sao chiếc mình định lấy
    không có trong đó, rồi gọi điện hỏi IT. In cả ra kèm lý do thì họ tự thấy phải sửa gì.
    """
    ra = []
    rt = db.get(VehicleRate, d.rate_id) if d.rate_id else None
    for v in db.execute(select(Vehicle).where(Vehicle.active.is_(True))
                        .order_by(Vehicle.plate)).scalars():
        if v.id == d.vehicle_id:
            continue
        kt = _kiem(db, d, v, v.driver_id)
        try:
            gia = tinh_gia(v, rt, d.date_from, d.date_to, d.internal_price)
        except KhongDoiDuoc:
            gia = None
        ra.append({"id": v.id, "bien": v.plate, "ma": v.code, "ghe": v.seats, "loai": v.kind,
                   "tai_xe": _ten(db, v.driver_id), "gia": float(gia) if gia is not None else None,
                   "muc": kt["muc"], "muc_ten": kt["muc_ten"], "nhan_duoc": kt["muc"] != FL.BLOCK,
                   "ly_do": [i["msg"] for i in kt["items"]]})
    return ra


def tai_xe_thay_the_duoc(db: Session, d: DispatchOrder) -> list[dict]:
    """Danh sách tài xế thay thế được, theo cùng luật «không được làm lệnh xấu đi»."""
    v = db.get(Vehicle, d.vehicle_id)
    if not v:
        return []
    cu = {i["code"] for i in _kiem(db, d, v, d.driver_id)["items"] if i["level"] == FL.BLOCK}
    ra = []
    for nv in db.execute(select(Employee).where(Employee.department == "doi_xe",
                                                Employee.active.is_(True))
                         .order_by(Employee.full_name)).scalars():
        if nv.id == d.driver_id:
            continue
        kt = _kiem(db, d, v, nv.id)
        moi = [i for i in kt["items"] if i["level"] == FL.BLOCK and i["code"] not in cu]
        ra.append({"id": nv.id, "ten": nv.full_name, "ma": nv.code,
                   "nhan_duoc": not moi, "ly_do": [i["msg"] for i in kt["items"]]})
    return ra
