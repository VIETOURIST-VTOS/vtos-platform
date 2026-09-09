"""Sổ công nợ đội xe – chi tiết theo chủ xe, theo xe và theo chứng từ.

Bảng quyết toán Đợt 3 trả lời được "kỳ này phải trả chủ xe bao nhiêu". Sổ công nợ trả lời một câu khác, và
là câu người ta thật sự hỏi khi cầm tiền đi trả: **còn nợ ai bao nhiêu, và đã trả chưa**.

Bốn điều tệp này cố ý làm chặt, vì mỗi điều tương ứng một cách mất tiền có thật:

  1. BỐN TÚI CÔNG NỢ KHÔNG ĐƯỢC CỘNG CHUNG. Nợ chủ xe hợp tác, tiền còn phải thu của người mua xe, dư nợ
     ngân hàng có thế chấp xe, và khoản đã chi hộ chưa vào kỳ nào – bốn thứ này với BỐN đối tượng khác nhau.
     Cộng lại ra một con số "công nợ đội xe" nghe rất gọn và không có nghĩa gì cả. Ở đây chúng nằm bốn mục
     riêng, và không có trường nào là tổng của cả bốn.

  2. ĐÓNG KỲ KHÔNG PHẢI LÀ ĐÃ TRẢ. Kỳ đóng nghĩa là hai bên thống nhất con số. Tiền đi hay chưa là việc
     khác, ghi ở bảng `fleet_debt_payments`. Một sổ công nợ không phân biệt được hai điều này là sổ dẫn tới
     trả hai lần – nên "còn phải trả" ở đây luôn là *số đã chốt trừ số đã ghi nhận chi*.

  3. KỲ CHƯA CHỐT KHÔNG PHẢI LÀ NỢ. Bảng nháp đang tính dở không được cộng vào số phải trả, nhưng cũng
     không được giấu đi – nó nằm ở mục "đang tính, chưa chốt" để người đọc biết con số sẽ còn tăng.

  4. THIẾU DỮ LIỆU KHÔNG PHẢI LÀ HẾT NỢ. Chủ xe chưa có kỳ quyết toán nào thì ghi rõ "chưa có bảng quyết
     toán", không ghi 0 – vì 0 và "chưa biết" dẫn tới hai hành động khác nhau.

Dư nợ ngân hàng luôn cộng theo KHẾ ƯỚC, không theo xe: ngân hàng nhận cả gói nhiều xe cho một khoản vay,
cộng dư nợ theo từng xe sẽ ra một con số không tồn tại.
"""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.hr import Vehicle
from app.models.finance import FinContract
from app.models.fleet import (Trip, TripCost, Maintenance, PartnerOwner, SaleCase, Collateral, RepaymentPlan,
                              Settlement, DebtPayment, HUONG_TIEN)
from app.services import fleet_settlement as QT

CHUA_CO = "chua_co_bang_quyet_toan"
# Kỳ đã chốt con số với đối tác. Trước các trạng thái này thì con số còn đang tính, chưa phải công nợ.
DA_CHOT = ("da_duyet", "da_gui_doi_tac", "dong_ky")


def _q(x: float) -> float:
    return float(round(x or 0))


# ====================== ĐÃ TRẢ / ĐÃ THU ======================
def da_tra(db: Session, settlement_id: int) -> float:
    """Số đã ghi nhận chi cho một kỳ quyết toán."""
    return _q(db.execute(select(func.coalesce(func.sum(DebtPayment.so_tien), 0))
                         .where(DebtPayment.settlement_id == settlement_id,
                                DebtPayment.huong == "tra_chu_xe")).scalar() or 0)


def da_thu_ban_xe(db: Session, sale_case_id: int) -> float:
    return _q(db.execute(select(func.coalesce(func.sum(DebtPayment.so_tien), 0))
                         .where(DebtPayment.sale_case_id == sale_case_id,
                                DebtPayment.huong == "thu_ban_xe")).scalar() or 0)


def ghi_thanh_toan(db: Session, huong: str, so_tien: float, ngay: date, idem_key: str, boi: str,
                   settlement_id: int | None = None, sale_case_id: int | None = None,
                   partner_id: int | None = None, chung_tu: str = "", note: str = "") -> dict:
    """Ghi một lần trả/thu tiền trên công nợ đội xe.

    Ba chặn, theo đúng thứ tự tiền hay đi lạc:
      - `idem_key` đã có thì trả lại bản ghi cũ, KHÔNG ghi thêm. Bấm hai lần một nút, chạy lại một tác vụ,
        nhập lại từ sao kê – đều không được thành hai lần trả.
      - Trả vượt số còn phải trả thì từ chối, và nói rõ còn bao nhiêu. Trả thừa rồi đòi lại là việc khó gấp
        nhiều lần so với chặn ngay tại đây.
      - Kỳ chưa chốt con số với đối tác thì chưa được chi. Chi theo một bảng còn đang tính là chi theo con
        số sẽ thay đổi.
    """
    if huong not in HUONG_TIEN:
        raise ValueError(f"Hướng tiền không hợp lệ. Chỉ nhận {', '.join(HUONG_TIEN)}")
    if so_tien <= 0:
        raise ValueError("Số tiền phải lớn hơn 0. Ghi âm để đảo một khoản đã trả là cách làm sai – "
                         "dùng bút toán điều chỉnh có người duyệt.")
    cu = db.execute(select(DebtPayment).where(DebtPayment.idem_key == idem_key)).scalars().first()
    if cu is not None:
        return {"id": cu.id, "so_tien": _q(cu.so_tien), "lap_lai": True,
                "message": "Lần ghi này đã có trước đó – không ghi thêm lần nữa"}

    st = sc = None
    if huong == "tra_chu_xe":
        if settlement_id is None:
            raise ValueError("Trả chủ xe phải gắn với một kỳ quyết toán cụ thể")
        st = db.get(Settlement, settlement_id)
        if st is None: raise ValueError("Không có kỳ quyết toán này")
        if st.status not in DA_CHOT:
            raise ValueError(f"Kỳ {st.ky} đang ở trạng thái '{st.status}' – con số chưa chốt với đối tác nên "
                             "chưa chi. Duyệt xong bảng rồi mới ghi chi.")
        con = _q((st.sau_can_tru or 0) - da_tra(db, st.id))
        if so_tien > con:
            raise ValueError(f"Chi {so_tien:,.0f} đ vượt số còn phải trả của kỳ {st.ky} ({con:,.0f} đ). "
                             "Nếu đúng là phải trả thêm thì tạo dòng điều chỉnh có người duyệt, "
                             "không chi vượt bảng.")
        partner_id = st.partner_id
    elif huong == "thu_ban_xe":
        if sale_case_id is None:
            raise ValueError("Thu tiền bán xe phải gắn với một hồ sơ bán xe")
        sc = db.get(SaleCase, sale_case_id)
        if sc is None: raise ValueError("Không có hồ sơ bán xe này")
        con = _q((sc.gia_ban or 0) - max((sc.da_thu or 0), da_thu_ban_xe(db, sc.id)))
        if so_tien > con:
            raise ValueError(f"Thu {so_tien:,.0f} đ vượt số còn phải thu của hồ sơ bán xe ({con:,.0f} đ)")

    p = DebtPayment(idem_key=idem_key, huong=huong, partner_id=partner_id, settlement_id=settlement_id,
                    sale_case_id=sale_case_id, company_id=(st.company_id if st else None),
                    ngay=ngay, so_tien=_q(so_tien), chung_tu=chung_tu, note=note, created_by=boi)
    db.add(p); db.flush()
    if sc is not None:
        sc.da_thu = _q(max((sc.da_thu or 0), 0) + so_tien)
    return {"id": p.id, "so_tien": _q(so_tien), "lap_lai": False,
            "message": f"Đã ghi {HUONG_TIEN[huong].lower()}: {so_tien:,.0f} đ"}


# ====================== CHI HỘ CHƯA VÀO KỲ NÀO ======================
def _xe_theo_chu(db: Session) -> dict[int, list[Vehicle]]:
    out: dict[int, list[Vehicle]] = {}
    for v in db.execute(select(Vehicle).where(Vehicle.partner_id.isnot(None))).scalars():
        out.setdefault(v.partner_id, []).append(v)
    return out


def chi_ho_chua_vao_ky(db: Session, xes: list[Vehicle], ky_da_dung: set[str]) -> list[dict]:
    """Khoản công ty đã chi hộ nhưng tháng đó chưa ai dựng bảng quyết toán.

    Đây là chỗ tiền công ty bỏ ra rồi nằm im: không ai nợ nó trên giấy tờ, vì cái giấy tờ đó chưa được lập.
    Gom theo tháng để người dùng biết cần dựng bảng nào."""
    ids = [v.id for v in xes]
    if not ids: return []
    theo_ky: dict[str, float] = {}
    trips = {t.id: t for t in db.execute(select(Trip).where(Trip.vehicle_id.in_(ids))).scalars()}
    if trips:
        for c in db.execute(select(TripCost).where(TripCost.trip_id.in_(list(trips)),
                                                   TripCost.ben_chiu == "vietourist_tam_ung")).scalars():
            t = trips.get(c.trip_id)
            if t is None or t.ngay_di is None: continue
            theo_ky[f"{t.ngay_di:%Y-%m}"] = theo_ky.get(f"{t.ngay_di:%Y-%m}", 0) + (c.amount or 0)
    for m in db.execute(select(Maintenance).where(Maintenance.vehicle_id.in_(ids),
                                                  Maintenance.ben_chiu == "vietourist_tam_ung")).scalars():
        if m.ngay is None: continue
        theo_ky[f"{m.ngay:%Y-%m}"] = theo_ky.get(f"{m.ngay:%Y-%m}", 0) + (m.so_tien or 0)
    return [{"ky": k, "so_tien": _q(v)} for k, v in sorted(theo_ky.items()) if k not in ky_da_dung and _q(v) > 0]


# ====================== CÔNG NỢ MỘT CHỦ XE ======================
def cong_no_chu_xe(db: Session, p: PartnerOwner, xes: list[Vehicle] | None = None) -> dict:
    """Sổ công nợ của một chủ xe hợp tác: từng kỳ, đã chốt hay chưa, đã trả bao nhiêu, còn lại bao nhiêu."""
    xes = xes if xes is not None else list(db.execute(
        select(Vehicle).where(Vehicle.partner_id == p.id)).scalars())
    sts = list(db.execute(select(Settlement).where(Settlement.partner_id == p.id)
                          .order_by(Settlement.ky)).scalars())
    cac_ky, phai_tra, dang_tinh, phai_thu = [], 0.0, 0.0, 0.0
    for st in sts:
        tra = da_tra(db, st.id)
        chot = st.status in DA_CHOT
        con = _q((st.sau_can_tru or 0) - tra) if chot else 0.0
        cac_ky.append({"settlement_id": st.id, "ky": st.ky, "status": st.status, "da_chot": chot,
                       "doanh_thu": _q(st.doanh_thu), "doi_tac_chiu": _q(st.doi_tac_chiu),
                       "can_tru": _q(st.can_tru), "phai_tra_theo_bang": _q(st.sau_can_tru),
                       "da_tra": tra, "con_phai_tra": con,
                       "chuyen_ky_sau": _q(st.chuyen_ky_sau),
                       "dong_ky_luc": st.closed_at.isoformat() if st.closed_at else None})
        if chot:
            phai_tra += con
        else:
            dang_tinh += _q((st.sau_can_tru or 0))
        phai_thu += _q(st.chuyen_ky_sau)

    lich = []
    for pl in db.execute(select(RepaymentPlan).where(RepaymentPlan.partner_id == p.id)).scalars():
        lich.append({"plan_id": pl.id, "ten": pl.ten, "status": pl.status, "principal": _q(pl.principal),
                     "da_can_tru": QT.da_ap_dung(db, pl.id), "con_lai": QT.con_lai(db, pl)})
    no_mua_xe = _q(sum(l["con_lai"] for l in lich if l["status"] == "hieu_luc"))

    treo = chi_ho_chua_vao_ky(db, xes, {s.ky for s in sts})
    return {
        "partner_id": p.id, "ho_ten": p.ho_ten, "company_id": p.company_id,
        "so_xe": len(xes), "xe": [{"id": v.id, "code": v.code, "plate": v.plate} for v in xes],
        "cong_ty_phai_tra": _q(phai_tra),
        "dang_tinh_chua_chot": _q(dang_tinh),
        "chu_xe_phai_tra_cong_ty": _q(phai_thu + no_mua_xe),
        "trong_do_chuyen_ky_sau": _q(phai_thu),
        "trong_do_no_theo_lich": no_mua_xe,
        "chi_ho_chua_vao_ky": treo,
        "tong_chi_ho_chua_vao_ky": _q(sum(x["so_tien"] for x in treo)),
        "cac_ky": cac_ky, "lich_can_tru": lich,
        "tinh_trang": CHUA_CO if not sts else "co_du_lieu",
        "ghi_chu": ("Chủ xe này chưa có bảng quyết toán nào – chưa biết số phải trả, KHÔNG phải bằng 0."
                    if not sts else ""),
    }


# ====================== TOÀN ĐỘI XE ======================
def so_cong_no(db: Session) -> dict:
    """Bốn túi công nợ của đội xe, để riêng và không cộng chung."""
    theo_chu = _xe_theo_chu(db)
    chu_xe = []
    for p in db.execute(select(PartnerOwner).where(PartnerOwner.active == True)).scalars():
        chu_xe.append(cong_no_chu_xe(db, p, theo_chu.get(p.id, [])))

    ban_xe = []
    for sc in db.execute(select(SaleCase)).scalars():
        v = db.get(Vehicle, sc.vehicle_id)
        con = _q((sc.gia_ban or 0) - (sc.da_thu or 0))
        if con <= 0 and sc.da_sang_ten: continue
        ban_xe.append({"sale_case_id": sc.id, "vehicle_id": sc.vehicle_id,
                       "xe": (v.code or v.plate) if v else "", "plate": v.plate if v else "",
                       "gia_ban": _q(sc.gia_ban), "da_thu": _q(sc.da_thu), "con_phai_thu": con,
                       "stage": sc.stage, "da_ban_giao": sc.da_ban_giao, "da_giai_chap": sc.da_giai_chap,
                       "da_sang_ten": sc.da_sang_ten,
                       "canh_bao": ("Đã bàn giao/sang tên nhưng còn phải thu"
                                    if con > 0 and (sc.da_ban_giao or sc.da_sang_ten) else "")})

    vay = []
    for ct in db.execute(select(FinContract).where(FinContract.status != "tat_toan")).scalars():
        cols = list(db.execute(select(Collateral).where(Collateral.contract_id == ct.id,
                                                        Collateral.den_ngay.is_(None))).scalars())
        if not cols: continue
        xe = []
        for c in cols:
            v = db.get(Vehicle, c.vehicle_id)
            if v: xe.append({"id": v.id, "code": v.code, "plate": v.plate, "lifecycle": v.lifecycle})
        vay.append({"contract_id": ct.id, "code": ct.code, "ngan_hang": ct.partner,
                    "phap_nhan": ct.entity, "company_id": ct.company_id,
                    "du_no": _q(ct.outstanding), "lai_suat": ct.interest_rate,
                    "dao_han": ct.maturity.isoformat() if ct.maturity else None,
                    "so_xe_the_chap": len(xe), "xe": xe})

    return {
        "voi_chu_xe": {
            "cong_ty_phai_tra": _q(sum(c["cong_ty_phai_tra"] for c in chu_xe)),
            "chu_xe_phai_tra_cong_ty": _q(sum(c["chu_xe_phai_tra_cong_ty"] for c in chu_xe)),
            "dang_tinh_chua_chot": _q(sum(c["dang_tinh_chua_chot"] for c in chu_xe)),
            "chi_ho_chua_vao_ky": _q(sum(c["tong_chi_ho_chua_vao_ky"] for c in chu_xe)),
            "so_chu_xe_chua_co_bang": sum(1 for c in chu_xe if c["tinh_trang"] == CHUA_CO),
            "chi_tiet": chu_xe,
        },
        "ban_xe": {"con_phai_thu": _q(sum(b["con_phai_thu"] for b in ban_xe)), "chi_tiet": ban_xe},
        "vay_the_chap_xe": {"du_no_theo_khe_uoc": _q(sum(v["du_no"] for v in vay)), "chi_tiet": vay},
        "giai_thich": [
            "Bốn mục trên với bốn đối tượng khác nhau (chủ xe hợp tác, người mua xe, ngân hàng, và khoản "
            "công ty đã chi hộ chưa vào kỳ nào) nên KHÔNG cộng chung thành một con số.",
            "\"Công ty phải trả\" chỉ tính các kỳ ĐÃ CHỐT với đối tác và đã trừ phần đã ghi nhận chi. "
            "Kỳ còn đang tính nằm ở dòng \"đang tính, chưa chốt\".",
            "Dư nợ vay cộng theo KHẾ ƯỚC. Ngân hàng nhận cả gói nhiều xe cho một khoản vay nên chia dư nợ "
            "về từng xe rồi cộng lại sẽ ra một con số không có thật.",
            "Chủ xe chưa có bảng quyết toán nào thì ghi \"chưa có bảng quyết toán\", không ghi 0.",
        ],
        "tinh_den": datetime.now().isoformat(timespec="seconds"),
    }
