"""Quyết toán chủ xe hợp tác, cấn trừ có kiểm soát, và năm chặn cứng còn lại – Đợt 3 đội xe Vietrip.

Cả tệp này chỉ làm một việc: ra đúng con số phải trả cho chủ xe, và ra được cùng con số đó lần thứ hai.

Công thức thì đơn giản, nhưng ba chỗ dưới đây mới là chỗ tiền đi lạc trong thực tế:

  1. SỐ ÂM KHÔNG ĐƯỢC THÀNH PHIẾU CHI ÂM. Kỳ mà đối tác chịu nhiều hơn được hưởng thì phần âm là khoản PHẢI
     THU, chuyển sang kỳ sau – không phải một phiếu chi mang dấu trừ đi qua bàn duyệt.
  2. MỘT KHOẢN CHỈ ĐƯỢC CẤN TRỪ MỘT LẦN. Dựng lại bảng quyết toán là việc người ta làm nhiều lần trong một
     kỳ; nếu mỗi lần dựng lại là một lần trừ thêm thì đối tác mất tiền mà bảng vẫn trông hợp lý. Vì vậy mỗi
     lần áp dụng có khóa chống lặp riêng, và tổng áp dụng luôn bị chặn bằng số dư còn đủ điều kiện.
  3. CẤN TRỪ PHẢI ĐÚNG PHÁP NHÂN. Không tự bù nợ của công ty A vào khoản công ty B phải trả – hai pháp nhân
     là hai túi tiền khác nhau, gộp lại là sai cả sổ lẫn thuế.

Kỳ quyết toán là THÁNG DƯƠNG LỊCH (chốt 07/9/2026) và chuyến gán vào kỳ theo NGÀY KHỞI HÀNH.
"""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User
from app.models.hr import Vehicle
from app.models.finance import FinContract
from app.models.fleet import (Trip, TripCost, Maintenance, PartnerOwner, SaleCase, Collateral, RepaymentPlan,
                              RepaymentInstallment, OffsetApplication, Settlement, SettlementLine,
                              SharedInvoice, SharedInvoiceLine, COST_KINDS)
from app.services import rules as R

DONG = 1  # làm tròn tới đồng: tiền Việt không có phần lẻ, và giữ số lẻ float là cách sinh ra chênh 1 đồng


def _q(x: float) -> float:
    return float(round(x))


def ky_ap_dung(db: Session) -> str:
    """Kỳ đầu tiên máy được phép dựng bảng quyết toán. Mặc định 2026-09 (chốt 07/9/2026: cách cắt kỳ theo
    tháng dương lịch áp dụng từ 01/9; tháng 7 và tháng 8 đã xử lý xong tay theo cách cũ)."""
    try:
        v = (R.get_param_text(db, "xe_ky_quyet_toan_ap_dung_tu") or "").strip()
    except KeyError:
        v = ""
    return v if len(v) == 7 and v[4] == "-" else "2026-09"


def ky_range(ky: str) -> tuple[date, date]:
    """Kỳ là tháng dương lịch: [ngày 1, ngày cuối tháng]."""
    y, m = map(int, ky.split("-"))
    d1 = date(y, m, 1)
    d2 = date(y + (m == 12), m % 12 + 1, 1)
    from datetime import timedelta
    return d1, d2 - timedelta(days=1)


# ====================== LỊCH CẤN TRỪ ======================
def dung_lich(principal: float, moi_ky: float) -> list[float]:
    """Chia một khoản thành các kỳ bằng nhau, KỲ CUỐI ôm phần dư.

    Ví dụ trong tài liệu: 200.000.000 với mức 14.000.000/tháng ra 14 kỳ đủ mức và kỳ cuối 4.000.000 – KHÔNG
    phải 15 kỳ đủ 14 triệu. Sai chỗ này là thu thừa của đối tác đúng 10 triệu, và bảng vẫn trông hợp lý."""
    if principal <= 0 or moi_ky <= 0:
        return []
    n = int(principal // moi_ky)
    du = _q(principal - n * moi_ky)
    ks = [_q(moi_ky)] * n
    if du > 0: ks.append(du)
    return ks


def chia_deu(principal: float, so_ky: int) -> list[float]:
    """Chia đều thành đúng `so_ky` kỳ; phần dư do làm tròn dồn vào KỲ CUỐI để tổng khớp tuyệt đối.

    Ví dụ tài liệu: 400.000.000 chia 36 kỳ → 35 kỳ 11.111.111 và kỳ cuối 11.111.115."""
    if principal <= 0 or so_ky <= 0:
        return []
    moi = int(principal // so_ky)
    ks = [float(moi)] * so_ky
    ks[-1] = _q(principal - moi * (so_ky - 1))
    return ks


def tao_ky_cho_lich(db: Session, plan: RepaymentPlan) -> list[RepaymentInstallment]:
    """Sinh các kỳ của một lịch. Chưa có ngày bắt đầu hợp lệ thì kỳ không có ngày đáo hạn, và lịch ở trạng
    thái nháp – không phát cảnh báo quá hạn cho một lịch chưa ai xác nhận."""
    cu = list(db.execute(select(RepaymentInstallment).where(RepaymentInstallment.plan_id == plan.id)).scalars())
    if cu: return cu
    amounts = chia_deu(plan.principal, plan.so_ky) if plan.so_ky else dung_lich(plan.principal, plan.moi_ky)
    out = []
    for i, a in enumerate(amounts, start=1):
        due = None
        if plan.bat_dau:
            y, m = plan.bat_dau.year, plan.bat_dau.month + i - 1
            y += (m - 1) // 12; m = (m - 1) % 12 + 1
            try: due = date(y, m, plan.bat_dau.day)
            except ValueError: due = date(y, m, 28)
        r = RepaymentInstallment(plan_id=plan.id, ky=i, due_date=due, amount_due=a)
        db.add(r); out.append(r)
    db.flush()
    return out


def da_ap_dung(db: Session, plan_id: int) -> float:
    """Tổng đã cấn trừ của một lịch, ĐÃ TRỪ các bút toán đảo."""
    s = db.execute(select(func.coalesce(func.sum(OffsetApplication.amount), 0))
                   .where(OffsetApplication.plan_id == plan_id)).scalar() or 0
    return _q(s)


def con_lai(db: Session, plan: RepaymentPlan) -> float:
    return _q(max(0.0, (plan.principal or 0) - da_ap_dung(db, plan.id)))


def ap_dung_can_tru(db: Session, plan: RepaymentPlan, so_tien: float, idem_key: str, boi: str,
                    settlement_id: int | None = None, chung_tu: str = "") -> dict:
    """Áp dụng một lần cấn trừ. Trả về số THỰC SỰ được trừ.

    Hai chốt chặn ở đây, và cả hai đều là chuyện tiền:
      - `idem_key` duy nhất ở cơ sở dữ liệu: gọi lại cùng bối cảnh trả về kết quả cũ, không trừ lần hai.
      - Tổng áp dụng không bao giờ vượt số dư còn lại của chính lịch đó.
    """
    cu = db.execute(select(OffsetApplication).where(OffsetApplication.idem_key == idem_key)).scalars().first()
    if cu is not None:
        return {"da_tru": _q(cu.amount), "lap_lai": True, "id": cu.id,
                "ghi_chu": "Lần áp dụng này đã được ghi trước đó – không trừ thêm lần nữa"}
    if plan.status != "hieu_luc":
        return {"da_tru": 0.0, "lap_lai": False,
                "ghi_chu": f"Lịch cấn trừ đang ở trạng thái '{plan.status}' nên chưa được áp dụng"}
    du = con_lai(db, plan)
    tru = _q(min(max(0.0, so_tien), du))
    if tru <= 0:
        return {"da_tru": 0.0, "lap_lai": False, "ghi_chu": "Lịch đã tất toán hoặc không còn số dư đủ điều kiện"}
    ky = next((k for k in sorted(tao_ky_cho_lich(db, plan), key=lambda x: x.ky)
               if k.amount_applied < k.amount_due), None)
    a = OffsetApplication(idem_key=idem_key, plan_id=plan.id, installment_id=ky.id if ky else None,
                          settlement_id=settlement_id, amount=tru, chung_tu=chung_tu, created_by=boi)
    db.add(a)
    con = tru
    for k in sorted(tao_ky_cho_lich(db, plan), key=lambda x: x.ky):
        if con <= 0: break
        chua = (k.amount_due or 0) - (k.amount_applied or 0)
        if chua <= 0: continue
        x = min(chua, con); k.amount_applied = (k.amount_applied or 0) + x; con -= x
    if con_lai(db, plan) - tru <= 0:
        pass
    db.flush()
    if _q((plan.principal or 0) - da_ap_dung(db, plan.id)) <= 0:
        plan.status = "tat_toan"
    return {"da_tru": tru, "lap_lai": False, "id": a.id,
            "ghi_chu": "" if tru == so_tien else f"Chỉ trừ được {tru:,.0f} đ – số dư còn lại của lịch"}


# ====================== DỰNG KỲ QUYẾT TOÁN ======================
def _xe_cua_doi_tac(db: Session, partner_id: int) -> list[Vehicle]:
    return list(db.execute(select(Vehicle).where(Vehicle.partner_id == partner_id)).scalars())


def phan_bo_hoa_don_chung(db: Session, inv: SharedInvoice) -> list[dict]:
    """Chia hóa đơn dùng chung cho ĐÚNG những xe có tên trên phụ lục của chính hóa đơn đó.

    Không có dòng nào thì trả về rỗng và không chia gì cả – đây là chỗ mà "chia cho 11 xe" từng được gõ tay
    và chi phí chạy sang cả những xe không có trên hóa đơn."""
    lines = list(db.execute(select(SharedInvoiceLine).where(SharedInvoiceLine.invoice_id == inv.id)).scalars())
    if not lines: return []
    co_san = [l for l in lines if l.amount]
    if co_san and len(co_san) == len(lines):
        return [{"vehicle_id": l.vehicle_id, "amount": _q(l.amount)} for l in lines]
    tong_he_so = sum(l.he_so or 1 for l in lines)
    tong = _q((inv.tong_tien or 0) + (inv.vat or 0))
    out, used = [], 0.0
    for l in lines[:-1]:
        a = _q(tong * (l.he_so or 1) / tong_he_so); used += a
        out.append({"vehicle_id": l.vehicle_id, "amount": a})
    out.append({"vehicle_id": lines[-1].vehicle_id, "amount": _q(tong - used)})   # dồn lẻ vào dòng cuối
    return out


def dung_quyet_toan(db: Session, partner_id: int, ky: str, boi: str) -> Settlement:
    """Dựng (hoặc dựng lại) bảng quyết toán nháp của một kỳ.

    Dựng lại KHÔNG cấn trừ thêm lần nào: phần cấn trừ đọc từ các lần áp dụng đã ghi, không tính lại từ đầu."""
    p = db.get(PartnerOwner, partner_id)
    if p is None: raise ValueError("Không có chủ xe hợp tác này")
    tu = ky_ap_dung(db)
    if ky < tu:
        # Kỳ trước mốc áp dụng đã quyết toán và trả tiền xong theo cách cắt kỳ cũ. Dựng lại bằng máy sẽ cắt
        # theo tháng dương lịch, ra một con số khác con số đã trả, và đó là lúc người ta trả bù lần hai.
        raise ValueError(f"Kỳ {ky} nằm trước mốc áp dụng {tu} – các kỳ này đã quyết toán xong theo cách cũ. "
                         "Muốn điều chỉnh thì tạo dòng điều chỉnh ở kỳ hiện tại, không dựng lại kỳ cũ.")
    d1, d2 = ky_range(ky)
    st = db.execute(select(Settlement).where(Settlement.ky == ky, Settlement.partner_id == partner_id)).scalars().first()
    if st is None:
        st = Settlement(ky=ky, partner_id=partner_id, company_id=p.company_id, created_by=boi)
        db.add(st); db.flush()
    if st.status == "dong_ky":
        raise ValueError(f"Kỳ {ky} đã đóng – sửa phải tạo bút toán điều chỉnh ở kỳ sau, không sửa ngược vào kỳ đã chốt")
    # Xóa các dòng máy dựng, GIỮ dòng điều chỉnh do người nhập và đã có người duyệt.
    for l in db.execute(select(SettlementLine).where(SettlementLine.settlement_id == st.id)).scalars():
        if l.kind != "dieu_chinh": db.delete(l)
    db.flush()

    xes = _xe_cua_doi_tac(db, partner_id)
    ids = [v.id for v in xes]
    doanh_thu = chi_ho = chu_xe_chiu = 0.0
    if ids:
        # Chuyến gán vào kỳ theo NGÀY KHỞI HÀNH (chốt 07/9/2026 cho chuyến vắt qua hai tháng).
        trips = list(db.execute(select(Trip).where(Trip.vehicle_id.in_(ids), Trip.ngay_di >= d1,
                                                   Trip.ngay_di <= d2)).scalars())
        for t in trips:
            if t.doanh_thu:
                db.add(SettlementLine(settlement_id=st.id, kind="doanh_thu", vehicle_id=t.vehicle_id,
                                      trip_id=t.id, mo_ta=t.ten_tour or f"Chuyến {t.ngay_di:%d/%m}",
                                      amount=_q(t.doanh_thu)))
                doanh_thu += (t.doanh_thu or 0)
            for c in db.execute(select(TripCost).where(TripCost.trip_id == t.id)).scalars():
                kind = "chi_ho" if c.ben_chiu == "vietourist_tam_ung" else "chu_xe_chiu"
                db.add(SettlementLine(settlement_id=st.id, kind=kind, vehicle_id=t.vehicle_id, trip_id=t.id,
                                      mo_ta=COST_KINDS.get(c.kind, c.kind), amount=_q(c.amount),
                                      ben_chiu=c.ben_chiu, chung_tu=c.chung_tu))
                if c.ben_chiu == "vietourist_tam_ung": chi_ho += (c.amount or 0)
                else: chu_xe_chiu += (c.amount or 0)
        # Bảo dưỡng, sửa chữa trong kỳ. Chủ tịch chốt lại cuối ngày 07/9/2026: giữ cách đang làm, Vietourist
        # CHI HỘ sửa chữa rồi cấn trừ vào công nợ chủ xe. Bên chịu vẫn đọc từ CỘT trên từng dòng chứ không
        # suy ra ở đây – dòng ghi trước ngày chốt vẫn giữ đúng bên chịu lúc đó, không bị viết lại ngược.
        for m in db.execute(select(Maintenance).where(Maintenance.vehicle_id.in_(ids), Maintenance.ngay >= d1,
                                                      Maintenance.ngay <= d2)).scalars():
            kind = "chi_ho" if m.ben_chiu == "vietourist_tam_ung" else "chu_xe_chiu"
            db.add(SettlementLine(settlement_id=st.id, kind=kind, vehicle_id=m.vehicle_id,
                                  mo_ta=f"Bảo dưỡng/sửa chữa {m.ngay:%d/%m}: {m.noi_dung[:120]}",
                                  amount=_q(m.so_tien), ben_chiu=m.ben_chiu, chung_tu=m.chung_tu))
            if m.ben_chiu == "vietourist_tam_ung": chi_ho += (m.so_tien or 0)
            else: chu_xe_chiu += (m.so_tien or 0)
        # Hóa đơn dùng chung: chỉ những xe CÓ TÊN trên chính hóa đơn đó.
        for inv in db.execute(select(SharedInvoice).where(SharedInvoice.ngay >= d1, SharedInvoice.ngay <= d2)).scalars():
            for r in phan_bo_hoa_don_chung(db, inv):
                if r["vehicle_id"] not in ids: continue
                db.add(SettlementLine(settlement_id=st.id, kind="phan_bo", vehicle_id=r["vehicle_id"],
                                      mo_ta=f"Phân bổ hóa đơn {inv.so_hoa_don} ({inv.nha_cung_cap})",
                                      amount=r["amount"], ben_chiu="vietourist_tam_ung",
                                      chung_tu=inv.so_hoa_don))
                chi_ho += r["amount"]

    dieu_chinh = sum((l.amount or 0) for l in db.execute(
        select(SettlementLine).where(SettlementLine.settlement_id == st.id,
                                     SettlementLine.kind == "dieu_chinh")).scalars())
    st.doanh_thu = _q(doanh_thu)
    st.doi_tac_huong = _q(doanh_thu)
    st.doi_tac_chiu = _q(chi_ho)              # khoản công ty đã chi hộ, đối tác phải hoàn lại
    st.dieu_chinh = _q(dieu_chinh)
    st.truoc_can_tru = _q(st.doi_tac_huong - st.doi_tac_chiu + (st.dieu_chinh or 0))
    st.can_tru = _q(db.execute(select(func.coalesce(func.sum(OffsetApplication.amount), 0))
                               .where(OffsetApplication.settlement_id == st.id)).scalar() or 0)
    sau = _q((st.truoc_can_tru or 0) - (st.can_tru or 0))
    # Số âm là khoản PHẢI THU, chuyển kỳ sau – không tạo phiếu chi âm.
    st.sau_can_tru = max(0.0, sau)
    st.chuyen_ky_sau = _q(-sau) if sau < 0 else 0.0
    st.ghi_chu = (f"Khoản Vietourist chi hộ trong kỳ: {_q(chi_ho):,.0f} đ (cấn trừ vào công nợ chủ xe theo "
                  f"cách đang làm, chốt 07/9/2026). Khoản chủ xe tự chịu: {_q(chu_xe_chiu):,.0f} đ.")
    db.flush()
    return st


def kiem_dong_ky(db: Session, st: Settlement) -> list[dict]:
    """Chặn cứng B9: không đóng kỳ khi còn cờ đỏ chưa xử lý thuộc kỳ đó."""
    from app.services import fleet as FL
    loi = []
    d1, d2 = ky_range(st.ky)
    ids = [v.id for v in _xe_cua_doi_tac(db, st.partner_id)]
    if ids:
        for t in db.execute(select(Trip).where(Trip.vehicle_id.in_(ids), Trip.ngay_di >= d1,
                                               Trip.ngay_di <= d2, Trip.co == "do")).scalars():
            loi.append({"code": "B9_CHUYEN_CO_DO", "level": FL.BLOCK,
                        "msg": f"Chuyến #{t.id} ngày {t.ngay_di:%d/%m} còn cờ đỏ: {t.co_ly_do[:140]}",
                        "huong_xu_ly": "Xử lý cờ đỏ của chuyến rồi dựng lại kỳ"})
    tong_dong = _q(sum((l.amount or 0) for l in db.execute(
        select(SettlementLine).where(SettlementLine.settlement_id == st.id,
                                     SettlementLine.kind == "doanh_thu")).scalars()))
    if tong_dong != st.doanh_thu:
        loi.append({"code": "B9_TONG_KHONG_KHOP_DONG", "level": FL.BLOCK,
                    "msg": f"Bảng tổng ({st.doanh_thu:,.0f}) không khớp tổng các dòng chi tiết ({tong_dong:,.0f})",
                    "huong_xu_ly": "Dựng lại kỳ; nếu vẫn lệch thì phải có giải trình được duyệt"})
    for l in db.execute(select(SettlementLine).where(SettlementLine.settlement_id == st.id,
                                                     SettlementLine.kind == "dieu_chinh")).scalars():
        if not (l.duyet_boi or "").strip():
            loi.append({"code": "B9_DIEU_CHINH_CHUA_DUYET", "level": FL.BLOCK,
                        "msg": f"Dòng điều chỉnh {l.amount:,.0f} đ chưa có người duyệt: {l.mo_ta[:120]}",
                        "huong_xu_ly": "Người có thẩm quyền duyệt dòng điều chỉnh trước khi đóng kỳ"})
    return loi


# ====================== CHẶN CỨNG B4, B5, B7, B8 ======================
def kiem_chi(db: Session, tour_id: int | None, so_tien: float, partner_id: int | None,
             co_dong_khau_tru: bool, chung_tu: str) -> list[dict]:
    """B4, B5, B6 cho một đề nghị chi."""
    from app.services import fleet as FL
    from app.models.core import Booking
    loi = []
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if so_tien >= nguong and not (chung_tu or "").strip():
        loi.append({"code": "B6_THIEU_CHUNG_TU", "level": FL.BLOCK,
                    "msg": f"Khoản chi {so_tien:,.0f} đ từ mức {nguong:,.0f} đ bắt buộc có chứng từ gốc",
                    "huong_xu_ly": "Đính kèm hóa đơn hoặc chứng từ gốc"})
    if tour_id:
        da_thu = float(db.execute(select(func.coalesce(func.sum(Booking.paid), 0))
                                  .where(Booking.tour_id == tour_id, Booking.cancelled == False)).scalar() or 0)
        if so_tien > da_thu:
            loi.append({"code": "B4_CHI_VUOT_DA_THU", "level": FL.BLOCK,
                        "msg": f"Chi {so_tien:,.0f} đ vượt số đã thu của tour ({da_thu:,.0f} đ)",
                        "huong_xu_ly": "Thu đủ tiền khách trước, hoặc trình duyệt ngoại lệ có hạn mức"})
    if partner_id and not co_dong_khau_tru:
        for pl in db.execute(select(RepaymentPlan).where(RepaymentPlan.partner_id == partner_id,
                                                         RepaymentPlan.status == "hieu_luc")).scalars():
            du = con_lai(db, pl)
            if du > 0:
                loi.append({"code": "B5_CHUA_CAN_TRU", "level": FL.BLOCK,
                            "msg": f"Bên nhận còn công nợ {du:,.0f} đ theo lịch \"{pl.ten}\" mà phiếu chi "
                                   "không có dòng khấu trừ",
                            "huong_xu_ly": "Thêm dòng cấn trừ theo lịch, hoặc trình Giám đốc duyệt bỏ dòng này"})
    return loi


def kiem_ban_xe(db: Session, sc: SaleCase, muon_sang_ten: bool = False) -> list[dict]:
    """B7 và B8 – hai chặn cứng giữ cho một chiếc xe không được sang tên khi ngân hàng còn giữ nó."""
    from app.services import fleet as FL
    loi = []
    dang_the_chap = list(db.execute(select(Collateral).where(Collateral.vehicle_id == sc.vehicle_id,
                                                             Collateral.den_ngay == None)).scalars())
    if muon_sang_ten and dang_the_chap and not (sc.van_ban_giai_chap or "").strip():
        ma = ", ".join(str(db.get(FinContract, c.contract_id).contract_no if db.get(FinContract, c.contract_id) else c.contract_id)
                       for c in dang_the_chap)
        loi.append({"code": "B7_SANG_TEN_CON_THE_CHAP", "level": FL.BLOCK,
                    "msg": f"Xe còn nằm trong tài sản bảo đảm ({ma}) và chưa có văn bản giải chấp đính kèm",
                    "huong_xu_ly": "Có văn bản giải chấp của ngân hàng rồi mới chuyển trạng thái sang tên"})
    for c in dang_the_chap:
        anh_em = db.execute(select(func.count()).select_from(Collateral)
                            .where(Collateral.contract_id == c.contract_id, Collateral.den_ngay == None)).scalar() or 0
        if anh_em > 1 and not (c.phuong_an_rut_tai_san or "").strip():
            ct = db.get(FinContract, c.contract_id)
            loi.append({"code": "B8_GOI_THE_CHAP_NHIEU_XE", "level": FL.BLOCK,
                        "msg": f"Khế ước {ct.contract_no if ct else c.contract_id} đang thế chấp {anh_em} xe "
                               "và chưa có phương án rút tài sản được duyệt",
                        "huong_xu_ly": "Thỏa thuận phương án rút tài sản với ngân hàng, ghi vào hồ sơ thế chấp"})
    if not dang_the_chap and not (sc.nguon or "").strip():
        loi.append({"code": "CHUA_RO_TINH_TRANG_THE_CHAP", "level": FL.UNKNOWN,
                    "msg": "Không thấy bản ghi thế chấp nào cho xe này – chưa đủ căn cứ kết luận là đã giải chấp",
                    "huong_xu_ly": "Đối chiếu bản đồ xe – khế ước – tài sản bảo đảm với ngân hàng"})
    return loi
