"""V4 – mười bốn bộ nạp còn thiếu theo phòng ban (lệnh giao việc 08/9/2026).

Tệp này KHÔNG có luồng nạp riêng. Mỗi bộ nạp ở đây là một khai báo đúng khuôn V1: bảng đích, phòng ban,
danh sách cột, một hàm kiểm, một hàm ghi. Máy đọc tệp, kiểm kiểu, kiểm kỳ khóa, chống trùng và ghi nhật
ký vẫn nằm ở app/services/intake.py và app/services/nhap_lieu.py – thêm một loại dữ liệu là thêm một
khai báo, không phải thêm một đường vào bảng.

Tách khỏi intake_phong_ban.py chứ không viết nối vào đó vì lý do vận hành: hai robot đang sửa cùng một
kho mã trong cùng một ngày, và một tệp dài 900 dòng do hai bên cùng sửa là một lần gộp hỏng chờ sẵn.

BỐN QUYẾT ĐỊNH NGHIỆP VỤ ĐÃ CÂN NHẮC, ghi lại để sau này còn đối chất:

  1. BẢNG LƯƠNG – nạp được, nhưng CHỈ KỲ CHƯA CHỐT. Nguyên tắc số 2 của bộ nạp phòng ban là "không nạp
     kết quả đã tính". Lệnh 08/9 lại ghi bảng lương là bắt buộc, vì số bảo hiểm lấy từ đó. Chỗ dung hòa
     đúng là: bộ nạp này ghi vào ĐẦU VÀO của kỳ (payroll_runs.inputs) và chỉ chạm được vào kỳ còn ở
     trạng thái nháp. Kỳ đã có chữ ký Kế toán trở đi thì từ chối – nạp đè lên một bảng đã ký là xóa mất
     căn cứ của chữ ký đó.
  2. BẢO HIỂM – bảng riêng, không phải một cột của bảng lương. Số chốt với cơ quan bảo hiểm và số bảng
     lương tính ra lệch nhau là chuyện thường (vào giữa tháng, nghỉ không lương, vượt trần, truy thu).
     Giữ một con số thì mỗi lần lệch không ai biết bên nào sai.
  3. THÙ LAO HDV – nạp lệnh phân công đã hoàn thành của kỳ TRƯỚC, không phải nơi tạo lời chào chuyến.
     Chào chuyến có cửa riêng, có hạn trả lời và có quyền từ chối; nạp hàng loạt qua đây là lách mất cả
     ba thứ đó. Vì vậy bộ nạp này chỉ ghi được bản ghi ở trạng thái đã xác nhận, và không gửi thông báo.
  4. TÀI SẢN & KHẤU HAO – nạp thẻ tài sản và bảng khấu hao ĐÃ TÍNH ở hệ thống cũ. Đây là ngoại lệ có ý
     thức với nguyên tắc "không nạp kết quả đã tính": số khấu hao của các kỳ trước khi lên VTOS không
     tính lại được (thiếu chính sách khấu hao từng thời kỳ), mà thiếu nó thì giá trị còn lại sai. Bù
     lại, bộ nạp chỉ nhận kỳ TRƯỚC kỳ bắt đầu tính trên VTOS của chính thẻ đó.
"""
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.orm import Session


def _lay(mod, ten):
    return getattr(mod, ten)


def _xe(db: Session, bien: str, luc=None):
    from app.services.fleet import xe_theo_bien
    return xe_theo_bien(db, bien, luc or date.today())


def _nv(db: Session, ma: str):
    from app.models.hr import Employee
    ma = str(ma or "").strip().upper()
    if not ma: return None
    return db.execute(select(Employee).where(func.upper(Employee.code) == ma)).scalars().first()


# ====================== ĐỘI XE – NHIÊN LIỆU (THẺ DẦU) ======================
def _gd_kiem(db: Session, r, source: str, nhan: str):
    """Kiểm chung cho hai bộ nạp giao dịch nguồn ngoài: thẻ dầu và ePass/VETC.

    Khóa chống trùng là nguồn + mã giao dịch gốc. Báo cáo ePass tháng 8/2026 có hai bản ghi lặp hoàn
    toàn; nạp lại tệp mà không có khóa này là cộng dư đúng bằng số đó, và bảng vẫn trông hợp lý."""
    from app.models.fleet import ExternalTxn
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    ma = str(r.get("ma_gd") or "").strip()
    try:
        d = _ngay(r.get("thoi_diem"))
    except ValueError as ex:
        return [str(ex)], cb, None
    if d and d > date.today():
        loi.append(f"Thời điểm {d:%d/%m/%Y} nằm ở tương lai – {nhan} không có giao dịch của ngày mai")
    bien = str(r.get("bien_so") or "").strip()
    if bien and d:
        v = _xe(db, bien, d)
        if v is None:
            cb.append(f"Chưa nhận ra xe của biển '{bien}' – giao dịch vẫn được ghi nhưng chưa gắn vào xe nào")
    elif not bien and not str(r.get("the_4so") or "").strip():
        cb.append("Không có biển số lẫn bốn số cuối thẻ – dòng này sẽ nằm ở nhóm chưa quy được về xe")
    if _so(r.get("so_tien")) <= 0:
        loi.append("Số tiền phải lớn hơn 0 – giao dịch 0 đồng là dòng rác trong sao kê, đừng nạp lên")
    trung = db.execute(select(ExternalTxn).where(
        ExternalTxn.source == source, ExternalTxn.ma_gd == ma)).scalars().first() if ma else None
    return loi, cb, (f"{nhan} {trung.ma_gd}" if trung is not None else None)


def _gd_nap(db: Session, r, boi, source: str):
    from app.models.fleet import ExternalTxn
    from app.services.intake import _so, _ngay
    d = _ngay(r.get("thoi_diem"))
    luc = datetime.combine(d, datetime.min.time()) if d else datetime.now()
    bien = str(r.get("bien_so") or "").strip()
    v = _xe(db, bien, d or date.today()) if bien else None
    t = ExternalTxn(source=source, ma_gd=str(r.get("ma_gd") or "").strip()[:120],
                    the_4so=str(r.get("the_4so") or "").strip()[:8], bien_so=bien[:20],
                    vehicle_id=(v.id if v is not None else None), thoi_diem=luc,
                    so_tien=_so(r.get("so_tien")), lit=_so(r.get("lit")),
                    mo_ta=str(r.get("mo_ta") or "").strip()[:300],
                    imported_by=boi, khop="chua_khop")
    db.add(t); db.flush()
    return f"{t.ma_gd} · {t.so_tien:,.0f} đ" + (f" · {v.plate}" if v is not None else " · chưa gắn xe")


def _dau_kiem(db, r): return _gd_kiem(db, r, "the_dau", "Thẻ dầu")
def _dau_nap(db, r, boi): return _gd_nap(db, r, boi, "the_dau")
def _epass_kiem(db, r): return _gd_kiem(db, r, "epass", "ePass/VETC")
def _epass_nap(db, r, boi): return _gd_nap(db, r, boi, "epass")


# ====================== ĐỘI XE – BẢO DƯỠNG, SỬA CHỮA ======================
def _bd_kiem(db: Session, r):
    from app.models.fleet import Maintenance
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    bien = str(r.get("bien_so") or "").strip()
    d = _ngay(r.get("ngay"))
    v = _xe(db, bien, d or date.today()) if bien else None
    if v is None:
        loi.append(f"Không tìm thấy xe của biển '{bien}' – chi phí bảo dưỡng phải gắn được vào một chiếc cụ thể")
    nd = str(r.get("noi_dung") or "").strip()
    km = r.get("km_luc_lam")
    if km is None or str(km).strip() == "":
        cb.append("Chưa có số km lúc làm – thiếu nó thì không phát hiện được chi phí ghi sai kỳ "
                  "(đúng lỗi đã xảy ra với xe 50H-496.23 tháng 8/2026)")
    elif v is not None and v.odo_km and _so(km) < v.odo_km - 50000:
        cb.append(f"Số km {_so(km):,.0f} thấp hơn nhiều so với đồng hồ đã xác nhận ({v.odo_km:,.0f}) – kiểm tra lại")
    bc = str(r.get("ben_chiu") or "chu_xe").strip()
    if bc not in ("chu_xe", "vietourist", "vietourist_tam_ung"):
        loi.append("Bên chịu phải là chu_xe / vietourist / vietourist_tam_ung")
    trung = None
    if v is not None and d and nd:
        trung = db.execute(select(Maintenance).where(
            Maintenance.vehicle_id == v.id, Maintenance.ngay == d,
            func.lower(Maintenance.noi_dung) == nd.lower())).scalars().first()
    return loi, cb, (f"{v.plate} {d:%d/%m/%Y}" if trung is not None else None)


def _bd_nap(db: Session, r, boi):
    from app.models.fleet import Maintenance
    from app.services.intake import _so, _ngay
    d = _ngay(r.get("ngay"))
    v = _xe(db, str(r.get("bien_so") or "").strip(), d or date.today())
    km = r.get("km_luc_lam"); kmt = r.get("km_ky_toi")
    m = Maintenance(vehicle_id=v.id, ngay=d, kind=str(r.get("loai") or "dinh_ky").strip()[:20],
                    km_luc_lam=(int(_so(km)) if str(km or "").strip() else None),
                    km_ky_toi=(int(_so(kmt)) if str(kmt or "").strip() else None),
                    noi_dung=str(r.get("noi_dung") or "").strip()[:300],
                    garage=str(r.get("garage") or "").strip()[:120],
                    so_tien=_so(r.get("so_tien")),
                    ben_chiu=str(r.get("ben_chiu") or "chu_xe").strip()[:24],
                    chung_tu=str(r.get("chung_tu") or "").strip()[:200], created_by=boi)
    db.add(m); db.flush()
    return f"{v.plate} · {d:%d/%m/%Y} · {m.so_tien:,.0f} đ"


# ====================== ĐỘI XE – ĐĂNG KIỂM ======================
def _dk_kiem(db: Session, r):
    from app.models.fleet import VehicleDocument
    from app.services.intake import _ngay
    loi, cb = [], []
    bien = str(r.get("bien_so") or "").strip()
    v = _xe(db, bien)
    if v is None:
        loi.append(f"Không tìm thấy xe của biển '{bien}'")
    het = _ngay(r.get("ngay_het_han"))
    cap = _ngay(r.get("ngay_cap"))
    if het and cap and het < cap:
        loi.append("Ngày hết hạn trước ngày cấp")
    if het is None:
        # Đặc tả §7: rỗng nghĩa là CHƯA BIẾT, không phải còn hạn. Cho nạp nhưng phải nói ra.
        cb.append("Chưa có ngày hết hạn – bản ghi này sẽ hiện là 'chưa đủ dữ liệu', không hiện màu xanh")
    elif het < date.today():
        cb.append(f"Đăng kiểm đã hết hạn từ {het:%d/%m/%Y} – xe không được phép lăn bánh")
    so = str(r.get("so_giay") or "").strip()
    trung = None
    if v is not None and so:
        trung = db.execute(select(VehicleDocument).where(
            VehicleDocument.vehicle_id == v.id, VehicleDocument.kind == "dang_kiem",
            func.upper(VehicleDocument.number) == so.upper())).scalars().first()
    return loi, cb, (f"{v.plate} · {so}" if trung is not None else None)


def _dk_nap(db: Session, r, boi):
    from app.models.fleet import VehicleDocument
    from app.services.intake import _ngay
    v = _xe(db, str(r.get("bien_so") or "").strip())
    het = _ngay(r.get("ngay_het_han"))
    # Giấy đăng kiểm mới thì giấy cũ của chính xe đó thôi hiệu lực – nhưng KHÔNG xóa, chỉ tắt cờ active.
    if het is not None:
        for cu in db.execute(select(VehicleDocument).where(
                VehicleDocument.vehicle_id == v.id, VehicleDocument.kind == "dang_kiem",
                VehicleDocument.active == True)).scalars():          # noqa: E712
            if cu.expires_on is None or cu.expires_on <= het:
                cu.active = False
    g = VehicleDocument(vehicle_id=v.id, kind="dang_kiem", number=str(r.get("so_giay") or "").strip()[:60],
                        issued_on=_ngay(r.get("ngay_cap")), expires_on=het,
                        source=str(r.get("nguon_giay") or "nạp tệp đăng kiểm")[:120],
                        verify="nguon_ghi", note=str(r.get("ghi_chu") or "").strip()[:300],
                        created_by=boi)
    db.add(g); db.flush()
    return f"{v.plate} · hạn {het:%d/%m/%Y}" if het else f"{v.plate} · chưa có hạn"


# ====================== ĐỘI XE – CHI PHÍ CỦA KỲ ======================
def _cpk_kiem(db: Session, r):
    from app.models.fleet import FleetPeriodCost, NHOM_CHI_PHI_KY
    from app.services.intake import _so
    loi, cb = [], []
    nhom = str(r.get("nhom") or "").strip()
    if nhom not in NHOM_CHI_PHI_KY:
        return [f"Nhóm '{nhom}' không có trong danh mục"], cb, None
    ten_nhom, pham_vi = NHOM_CHI_PHI_KY[nhom]
    bien = str(r.get("bien_so") or "").strip()
    v = _xe(db, bien) if bien else None
    if pham_vi == "xe":
        if v is None:
            loi.append(f"Nhóm '{ten_nhom}' là chi phí CỦA TỪNG XE – phải ghi biển số quy được về một chiếc")
    elif v is not None:
        loi.append(f"Nhóm '{ten_nhom}' là chi phí của CẢ ĐỘI – không gắn vào xe nào. "
                   "Chia lãi vay hay phí bãi cho từng xe theo doanh thu hay theo ngày chạy đều ra số khác "
                   "nhau và đều 'có lý'; hệ thống cố ý không chọn hộ.")
    if _so(r.get("so_tien")) <= 0:
        loi.append("Số tiền phải lớn hơn 0")
    ky = str(r.get("ky") or "").strip()
    mo_ta = str(r.get("mo_ta") or "").strip()
    trung = db.execute(select(FleetPeriodCost).where(
        FleetPeriodCost.ky == ky, FleetPeriodCost.nhom == nhom,
        FleetPeriodCost.vehicle_id == (v.id if v is not None else None),
        FleetPeriodCost.mo_ta == mo_ta)).scalars().first() if ky else None
    return loi, cb, (f"{ky} · {ten_nhom}" if trung is not None else None)


def _cpk_nap(db: Session, r, boi):
    from app.models.fleet import FleetPeriodCost, NHOM_CHI_PHI_KY
    from app.services.intake import _so
    nhom = str(r.get("nhom") or "").strip()
    ten_nhom, pham_vi = NHOM_CHI_PHI_KY[nhom]
    bien = str(r.get("bien_so") or "").strip()
    v = _xe(db, bien) if bien else None
    c = FleetPeriodCost(ky=str(r.get("ky") or "").strip()[:7], pham_vi=pham_vi,
                        vehicle_id=(v.id if v is not None else None), nhom=nhom,
                        mo_ta=str(r.get("mo_ta") or "").strip()[:200], so_tien=_so(r.get("so_tien")),
                        chung_tu=str(r.get("chung_tu") or "").strip()[:200], nguon="nap_tep", boi=boi)
    db.add(c); db.flush()
    return f"{c.ky} · {ten_nhom} · {c.so_tien:,.0f} đ" + (f" · {v.plate}" if v is not None else "")


# ====================== MARKETING – CHI THEO KÊNH ======================
def _mkt_kiem(db: Session, r):
    from app.models.nap_bo_sung import MktChannelSpend, KENH_MKT
    from app.services.intake import _so
    loi, cb = [], []
    kenh = str(r.get("kenh") or "").strip()
    if kenh not in KENH_MKT:
        return [f"Kênh '{kenh}' không có trong danh mục ({', '.join(list(KENH_MKT)[:6])}…)"], cb, None
    if _so(r.get("so_tien")) <= 0:
        loi.append("Số tiền phải lớn hơn 0")
    lead = r.get("so_lead")
    if str(lead or "").strip() == "":
        cb.append("Chưa có số lead – chưa tính được chi phí trên mỗi lead của kênh này")
    elif _so(lead) > 0 and _so(r.get("so_tien")) / _so(lead) > 5_000_000:
        cb.append(f"Chi phí mỗi lead {_so(r.get('so_tien'))/_so(lead):,.0f} đ – cao bất thường, kiểm tra lại số lead")
    ky = str(r.get("ky") or "").strip()
    cd = str(r.get("chien_dich") or "").strip()
    trung = db.execute(select(MktChannelSpend).where(
        MktChannelSpend.ky == ky, MktChannelSpend.kenh == kenh,
        MktChannelSpend.chien_dich == cd)).scalars().first() if ky else None
    return loi, cb, (f"{ky} · {KENH_MKT[kenh]}" + (f" · {cd}" if cd else "") if trung is not None else None)


def _mkt_nap(db: Session, r, boi):
    from app.models.nap_bo_sung import MktChannelSpend, KENH_MKT
    from app.services.intake import _so

    def _n(k):
        return int(_so(r.get(k))) if str(r.get(k) or "").strip() != "" else None

    s = MktChannelSpend(ky=str(r.get("ky") or "").strip()[:7], kenh=str(r.get("kenh") or "").strip()[:20],
                        chien_dich=str(r.get("chien_dich") or "").strip()[:120],
                        so_tien=_so(r.get("so_tien")), luot_hien_thi=_n("luot_hien_thi"),
                        luot_nhap=_n("luot_nhap"), so_lead=_n("so_lead"),
                        mo_ta=str(r.get("mo_ta") or "").strip()[:300],
                        chung_tu=str(r.get("chung_tu") or "").strip()[:200], nguon="nap_tep", boi=boi)
    db.add(s); db.flush()
    return f"{s.ky} · {KENH_MKT.get(s.kenh, s.kenh)} · {s.so_tien:,.0f} đ"


# ====================== KINH DOANH – DOANH SỐ THEO TƯ VẤN VIÊN ======================
def _ds_kiem(db: Session, r):
    from app.models.nap_bo_sung import SalesByConsultant
    from app.services.intake import _so
    loi, cb = [], []
    e = _nv(db, r.get("ma_nv"))
    if e is None:
        return [f"Không có nhân sự mã '{r.get('ma_nv')}' – doanh số phải gắn vào một người có hồ sơ"], cb, None
    dt = _so(r.get("doanh_thu"))
    dathu = r.get("doanh_thu_da_thu")
    if str(dathu or "").strip() != "" and _so(dathu) > dt:
        loi.append(f"Đã thu {_so(dathu):,.0f} lớn hơn doanh thu {dt:,.0f} – một trong hai số ghi sai")
    hh = r.get("hoa_hong")
    if str(hh or "").strip() != "" and dt > 0 and _so(hh) / dt > 0.15:
        cb.append(f"Hoa hồng bằng {_so(hh)/dt*100:.1f}% doanh số – vượt xa mức thường, cần người duyệt xem lại")
    ky = str(r.get("ky") or "").strip()
    trung = db.execute(select(SalesByConsultant).where(
        SalesByConsultant.ky == ky, SalesByConsultant.employee_id == e.id)).scalars().first() if ky else None
    return loi, cb, (f"{ky} · {e.code}" if trung is not None else None)


def _ds_nap(db: Session, r, boi):
    from app.models.nap_bo_sung import SalesByConsultant
    from app.services.intake import _so
    e = _nv(db, r.get("ma_nv"))

    def _t(k):
        return _so(r.get(k)) if str(r.get(k) or "").strip() != "" else None

    s = SalesByConsultant(ky=str(r.get("ky") or "").strip()[:7], employee_id=e.id,
                          nhom_kd=(str(r.get("nhom_kd") or "").strip() or e.sales_group)[:20],
                          so_booking=(int(_so(r.get("so_booking"))) if str(r.get("so_booking") or "").strip() else None),
                          so_khach=(int(_so(r.get("so_khach"))) if str(r.get("so_khach") or "").strip() else None),
                          doanh_thu=_t("doanh_thu"), doanh_thu_da_thu=_t("doanh_thu_da_thu"),
                          hoa_hong=_t("hoa_hong"), ghi_chu=str(r.get("ghi_chu") or "").strip()[:300],
                          nguon="nap_tep", boi=boi)
    db.add(s); db.flush()
    return f"{s.ky} · {e.code} {e.full_name} · {(s.doanh_thu or 0):,.0f} đ"


# ====================== HƯỚNG DẪN – THÙ LAO HDV THEO CHUYẾN ======================
def _tl_kiem(db: Session, r):
    from app.models.core import Tour
    from app.models.hr import Employee, GuideAssignment
    from app.services.intake import _so
    loi, cb = [], []
    ma = str(r.get("ma_tour") or "").strip()
    t = db.execute(select(Tour).where(func.upper(Tour.code) == ma.upper())).scalars().first() if ma else None
    if t is None:
        return [f"Không có tour mã '{ma}' – thù lao phải gắn vào một chuyến có thật"], cb, None
    the = str(r.get("the_so") or "").strip()
    g = None
    if the:
        g = db.execute(select(Employee).where(func.upper(Employee.card_no) == the.upper())).scalars().first()
    if g is None:
        g = _nv(db, r.get("ma_nv"))
    if g is None:
        return ["Không nhận ra hướng dẫn viên: thiếu cả số thẻ lẫn mã nhân viên khớp hồ sơ"], cb, None
    ngay = _so(r.get("so_ngay"))
    if ngay <= 0:
        loi.append("Số ngày phải lớn hơn 0")
    if t.start_date and t.end_date:
        toi_da = (t.end_date - t.start_date).days + 1
        if ngay > toi_da:
            loi.append(f"Số ngày {ngay:.0f} lớn hơn độ dài chuyến ({toi_da} ngày)")
    dg = r.get("don_gia_ngay")
    if str(dg or "").strip() == "":
        cb.append("Chưa có đơn giá ngày – bản ghi sẽ để trống thù lao, không tự điền theo bảng giá")
    if not g.ctv_contract:
        cb.append(f"{g.full_name} chưa ghi nhận hợp đồng cộng tác – toàn bộ HDV đã là cộng tác viên từ 07/9/2026")
    trung = db.execute(select(GuideAssignment).where(
        GuideAssignment.tour_id == t.id, GuideAssignment.guide_id == g.id)).scalars().first()
    return loi, cb, (f"{t.code} · {g.full_name}" if trung is not None else None)


def _tl_nap(db: Session, r, boi):
    from app.models.core import Tour
    from app.models.hr import Employee, GuideAssignment
    from app.services.intake import _so
    from app.services.nhap_lieu import _co
    ma = str(r.get("ma_tour") or "").strip()
    t = db.execute(select(Tour).where(func.upper(Tour.code) == ma.upper())).scalars().first()
    the = str(r.get("the_so") or "").strip()
    g = db.execute(select(Employee).where(func.upper(Employee.card_no) == the.upper())).scalars().first() if the else None
    if g is None: g = _nv(db, r.get("ma_nv"))
    dg = _so(r.get("don_gia_ngay")) if str(r.get("don_gia_ngay") or "").strip() != "" else 0.0
    a = GuideAssignment(tour_id=t.id, guide_id=g.id, days=int(_so(r.get("so_ngay"))), rate_per_day=dg,
                        holiday=_co(r.get("le_tet")), assigned_by=boi,
                        assigned_at=datetime.now(), confirmed_at=datetime.now(),
                        report_submitted=_co(r.get("da_nop_bao_cao")), advance_settled=True,
                        status="da_xac_nhan")
    db.add(a); db.flush()
    thu_lao = a.days * a.rate_per_day * (2 if a.holiday else 1)
    return f"{t.code} · {g.full_name} · {a.days} ngày · " + (f"{thu_lao:,.0f} đ" if dg else "chưa có đơn giá")


# ====================== KẾ TOÁN – HÓA ĐƠN ĐẦU VÀO ======================
def _hd_kiem(db: Session, r):
    from app.models.nap_bo_sung import PurchaseInvoice
    from app.models.suppliers import Supplier
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    mst = str(r.get("mst_nguoi_ban") or "").strip()
    kh = str(r.get("ky_hieu") or "").strip()
    so = str(r.get("so_hoa_don") or "").strip()
    if not mst:
        loi.append("Thiếu mã số thuế người bán – bộ ba MST + ký hiệu + số hóa đơn mới định danh được "
                   "một hóa đơn; hai nhà cung cấp cùng có hóa đơn số 42 là chuyện thường ngày")
    elif not (10 <= len(mst.replace("-", "")) <= 14):
        cb.append(f"Mã số thuế '{mst}' không đúng độ dài 10 hoặc 13 chữ số – kiểm tra lại")
    truoc = _so(r.get("tien_truoc_thue"))
    thue = _so(r.get("tien_thue"))
    tong = r.get("tong_tien")
    if str(tong or "").strip() != "" and truoc:
        lech = abs(_so(tong) - (truoc + thue))
        if lech > 1000:
            loi.append(f"Tổng tiền lệch {lech:,.0f} đ so với trước thuế + thuế – một trong ba số ghi sai")
    ts = r.get("thue_suat")
    if str(ts or "").strip() != "":
        v = _so(ts)
        v = v / 100 if v > 1 else v
        if v not in (0, 0.05, 0.08, 0.1):
            cb.append(f"Thuế suất {v*100:.0f}% không nằm trong 0 / 5 / 8 / 10% – kiểm tra lại")
    d = _ngay(r.get("ngay_hd"))
    if d and d > date.today():
        loi.append(f"Ngày hóa đơn {d:%d/%m/%Y} nằm ở tương lai")
    if not str(r.get("ten_nguoi_ban") or "").strip():
        cb.append("Chưa có tên người bán")
    ncc = None
    if mst:
        ncc = db.execute(select(Supplier).where(Supplier.ma_so_thue == mst)).scalars().first()
        if ncc is None:
            cb.append("Chưa có nhà cung cấp nào mang mã số thuế này trong danh mục – hóa đơn vẫn được ghi, "
                      "nhưng chưa gắn được vào hồ sơ đối tác")
    trung = db.execute(select(PurchaseInvoice).where(
        PurchaseInvoice.mst_nguoi_ban == mst, PurchaseInvoice.ky_hieu == kh,
        PurchaseInvoice.so_hoa_don == so)).scalars().first() if (mst and so) else None
    return loi, cb, (f"{kh} {so}" if trung is not None else None)


def _hd_nap(db: Session, r, boi):
    from app.models.nap_bo_sung import PurchaseInvoice
    from app.models.suppliers import Supplier
    from app.services.intake import _so, _ngay
    mst = str(r.get("mst_nguoi_ban") or "").strip()
    ncc = db.execute(select(Supplier).where(Supplier.ma_so_thue == mst)).scalars().first() if mst else None

    def _t(k):
        return _so(r.get(k)) if str(r.get(k) or "").strip() != "" else None

    ts = _t("thue_suat")
    if ts is not None and ts > 1: ts = ts / 100
    truoc, thue = _t("tien_truoc_thue"), _t("tien_thue")
    tong = _t("tong_tien")
    if tong is None and truoc is not None:
        tong = truoc + (thue or 0)
    h = PurchaseInvoice(mst_nguoi_ban=mst[:20], ten_nguoi_ban=str(r.get("ten_nguoi_ban") or "").strip()[:200],
                        ky_hieu=str(r.get("ky_hieu") or "").strip()[:20],
                        so_hoa_don=str(r.get("so_hoa_don") or "").strip()[:20],
                        ngay_hd=_ngay(r.get("ngay_hd")),
                        noi_dung=str(r.get("noi_dung") or "").strip()[:300],
                        tien_truoc_thue=truoc, thue_suat=ts, tien_thue=thue, tong_tien=tong,
                        ma_tour=str(r.get("ma_tour") or "").strip()[:60],
                        supplier_id=(ncc.id if ncc is not None else None),
                        khop="chua_khop", chung_tu=str(r.get("chung_tu") or "").strip()[:200],
                        nguon="nap_tep", boi=boi)
    db.add(h); db.flush()
    return f"{h.ky_hieu} {h.so_hoa_don} · {h.ten_nguoi_ban} · " + (f"{tong:,.0f} đ" if tong is not None else "chưa có số tiền")


# ====================== HCNS – BẢO HIỂM THEO KỲ ======================
def _bh_kiem(db: Session, r):
    from app.models.nap_bo_sung import SocialInsurancePeriod
    from app.services.intake import _so
    loi, cb = [], []
    e = _nv(db, r.get("ma_nv"))
    if e is None:
        return [f"Không có nhân sự mã '{r.get('ma_nv')}'"], cb, None
    if e.contract_type == "ctv":
        loi.append(f"{e.full_name} là cộng tác viên – công ty không đóng bảo hiểm bắt buộc cho cộng tác "
                   "viên. Nếu người này thật sự thuộc diện đóng thì phải sửa loại hợp đồng trước.")
    tt = str(r.get("trang_thai") or "dang_dong").strip()
    if tt not in ("dang_dong", "bao_giam", "truy_thu"):
        loi.append("Trạng thái phải là dang_dong / bao_giam / truy_thu")
    muc = _so(r.get("muc_dong"))
    if muc and e.bhxh_base and abs(muc - e.bhxh_base) > 1:
        cb.append(f"Mức đóng {muc:,.0f} khác mức ghi trong hồ sơ ({e.bhxh_base:,.0f}) – "
                  "nạp xong nên xem lại hồ sơ nhân sự hay bảng chốt bên nào đúng")
    ky = str(r.get("ky") or "").strip()
    trung = db.execute(select(SocialInsurancePeriod).where(
        SocialInsurancePeriod.ky == ky,
        SocialInsurancePeriod.employee_id == e.id)).scalars().first() if ky else None
    return loi, cb, (f"{ky} · {e.code}" if trung is not None else None)


def _bh_nap(db: Session, r, boi):
    from app.models.nap_bo_sung import SocialInsurancePeriod
    from app.services.intake import _so
    e = _nv(db, r.get("ma_nv"))

    def _t(k):
        return _so(r.get(k)) if str(r.get(k) or "").strip() != "" else None

    b = SocialInsurancePeriod(ky=str(r.get("ky") or "").strip()[:7], employee_id=e.id,
                              muc_dong=_t("muc_dong"), cty_dong=_t("cty_dong"), nld_dong=_t("nld_dong"),
                              so_ngay_dong=_t("so_ngay_dong"),
                              trang_thai=str(r.get("trang_thai") or "dang_dong").strip()[:20],
                              ghi_chu=str(r.get("ghi_chu") or "").strip()[:300], nguon="nap_tep", boi=boi)
    db.add(b); db.flush()
    return f"{b.ky} · {e.code} {e.full_name}"


# ====================== HCNS – BẢNG LƯƠNG (KỲ CHƯA CHỐT) ======================
LUONG_CHOT = ("kt_xac_nhan", "hcns_lap", "tgd_ky")


def _bl_kiem(db: Session, r):
    from app.models.hr import PayrollRun
    from app.services.intake import _so
    loi, cb = [], []
    e = _nv(db, r.get("ma_nv"))
    if e is None:
        return [f"Không có nhân sự mã '{r.get('ma_nv')}'"], cb, None
    ky = str(r.get("ky") or "").strip()
    run = db.execute(select(PayrollRun).where(PayrollRun.period == ky)).scalars().first() if ky else None
    if run is not None and run.status in LUONG_CHOT:
        loi.append(f"Bảng lương kỳ {ky} đã ở trạng thái '{run.status}' – nạp đè lên một bảng đã có chữ ký "
                   "là xóa mất căn cứ của chữ ký đó. Muốn sửa thì lập điều chỉnh ở kỳ sau.")
    cong = _so(r.get("cong_thuc_te"))
    chuan = _so(r.get("cong_chuan")) or 26
    if cong <= 0:
        loi.append("Công thực tế phải lớn hơn 0 – người không đi làm ngày nào thì không có dòng lương")
    elif cong > chuan + 5:
        cb.append(f"Công thực tế {cong:g} vượt công chuẩn {chuan:g} khá nhiều – kiểm tra lại phần tăng ca")
    tt = r.get("thuc_linh")
    if str(tt or "").strip() == "":
        cb.append("Chưa có thực lĩnh – dòng này chỉ là đầu vào để hệ thống tính, không phải số đã chốt")
    trung = None
    if run is not None:
        da = (run.inputs or {}).get("theo_ma_nv") or {}
        if e.code in da: trung = f"{ky} · {e.code}"
    return loi, cb, trung


def _bl_nap(db: Session, r, boi):
    from app.models.hr import PayrollRun
    from app.services.intake import _so
    ky = str(r.get("ky") or "").strip()[:7]
    e = _nv(db, r.get("ma_nv"))
    run = db.execute(select(PayrollRun).where(PayrollRun.period == ky)).scalars().first()
    if run is None:
        run = PayrollRun(period=ky, status="nhap", rows=[], totals={}, inputs={})
        db.add(run); db.flush()
    inputs = dict(run.inputs or {})
    theo = dict(inputs.get("theo_ma_nv") or {})

    def _t(k):
        return _so(r.get(k)) if str(r.get(k) or "").strip() != "" else None

    theo[e.code] = {"cong_thuc_te": _so(r.get("cong_thuc_te")), "ho_ten": e.full_name,
                    "luong_cong_viec": _t("luong_cong_viec"), "phu_cap": _t("phu_cap"),
                    "thuong": _t("thuong"), "khau_tru": _t("khau_tru"), "thuc_linh": _t("thuc_linh"),
                    "ghi_chu": str(r.get("ghi_chu") or "").strip()[:200], "nguon": "nap_tep", "boi": boi}
    inputs["theo_ma_nv"] = theo
    if str(r.get("cong_chuan") or "").strip():
        inputs["cong_chuan"] = _so(r.get("cong_chuan"))
    run.inputs = inputs
    run.updated_at = datetime.now()
    db.add(run); db.flush()
    return f"{ky} · {e.code} {e.full_name} · {_so(r.get('cong_thuc_te')):g} công"


# ====================== TÀI SẢN – THẺ TÀI SẢN CỐ ĐỊNH ======================
def _ts_kiem(db: Session, r):
    from app.models.assets import FixedAsset, ASSET_KINDS
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    ma = str(r.get("ma_ts") or "").strip().upper()
    loai = str(r.get("loai") or "huu_hinh").strip()
    if loai not in ASSET_KINDS:
        loi.append(f"Loại tài sản '{loai}' không hợp lệ ({', '.join(ASSET_KINDS)})")
    ng = _so(r.get("nguyen_gia"))
    if ng <= 0:
        loi.append("Nguyên giá phải lớn hơn 0")
    thang = _so(r.get("so_thang_kh"))
    if thang < 0:
        loi.append("Thời gian sử dụng không được âm")
    tl = _so(r.get("hao_mon_luy_ke"))
    if tl > ng:
        loi.append(f"Hao mòn lũy kế {tl:,.0f} lớn hơn nguyên giá {ng:,.0f}")
    if tl > 0 and not str(r.get("ky_so_du") or "").strip():
        loi.append("Có hao mòn lũy kế thì phải ghi kỳ tương ứng – nếu không thì không biết số đó tính đến lúc nào")
    try:
        _ngay(r.get("ngay_bat_dau_kh")); _ngay(r.get("ngay_mua"))
    except ValueError as ex:
        loi.append(str(ex))
    trung = db.execute(select(FixedAsset).where(
        func.upper(FixedAsset.code) == ma)).scalars().first() if ma else None
    return loi, cb, (trung.code if trung is not None else None)


def _ts_nap(db: Session, r, boi):
    from app.models.assets import FixedAsset, ASSET_KINDS
    from app.services.intake import _so, _ngay
    loai = str(r.get("loai") or "huu_hinh").strip()
    m = ASSET_KINDS[loai]
    a = FixedAsset(code=str(r.get("ma_ts") or "").strip().upper()[:30],
                   name=str(r.get("ten") or "").strip()[:200], kind=loai,
                   group=str(r.get("nhom") or "").strip()[:60],
                   asset_account=m["tk_nguyen_gia"], depr_account=m["tk_hao_mon"],
                   partner_code=str(r.get("nha_cung_cap") or "").strip()[:60],
                   department=str(r.get("bo_phan") or "").strip()[:20],
                   purchase_date=_ngay(r.get("ngay_mua")),
                   start_date=_ngay(r.get("ngay_bat_dau_kh")) or date.today(),
                   cost=_so(r.get("nguyen_gia")), depr_months=int(_so(r.get("so_thang_kh"))),
                   opening_accumulated=_so(r.get("hao_mon_luy_ke")),
                   opening_period=str(r.get("ky_so_du") or "").strip()[:7],
                   quantity=int(_so(r.get("so_luong")) or 1),
                   note=str(r.get("ghi_chu") or "").strip()[:300], source="vtos", created_by=boi)
    db.add(a); db.flush()
    return f"{a.code} · {a.name} · {a.cost:,.0f} đ"


# ====================== TÀI SẢN – CÔNG CỤ DỤNG CỤ / CHI PHÍ TRẢ TRƯỚC ======================
def _cc_kiem(db: Session, r):
    from app.models.assets import PrepaidExpense, PREPAID_KINDS
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    ma = str(r.get("ma_ccdc") or "").strip().upper()
    loai = str(r.get("loai") or "ccdc").strip()
    if loai not in PREPAID_KINDS:
        loi.append(f"Loại '{loai}' không hợp lệ ({', '.join(PREPAID_KINDS)})")
    gt = _so(r.get("gia_tri"))
    if gt <= 0: loi.append("Giá trị phân bổ phải lớn hơn 0")
    ky = int(_so(r.get("so_ky_pb")) or 0)
    if ky <= 0: loi.append("Số kỳ phân bổ phải lớn hơn 0")
    dpb = _so(r.get("da_phan_bo"))
    if dpb > gt: loi.append(f"Đã phân bổ {dpb:,.0f} lớn hơn giá trị {gt:,.0f}")
    if dpb > 0 and not str(r.get("ky_so_du") or "").strip():
        loi.append("Có số đã phân bổ thì phải ghi kỳ tương ứng")
    try:
        _ngay(r.get("ngay_bat_dau_pb"))
    except ValueError as ex:
        loi.append(str(ex))
    trung = db.execute(select(PrepaidExpense).where(
        func.upper(PrepaidExpense.code) == ma)).scalars().first() if ma else None
    return loi, cb, (trung.code if trung is not None else None)


def _cc_nap(db: Session, r, boi):
    from app.models.assets import PrepaidExpense
    from app.services.intake import _so, _ngay
    p = PrepaidExpense(code=str(r.get("ma_ccdc") or "").strip().upper()[:30],
                       name=str(r.get("ten") or "").strip()[:200],
                       kind=str(r.get("loai") or "ccdc").strip()[:20],
                       partner_code=str(r.get("nha_cung_cap") or "").strip()[:60],
                       department=str(r.get("bo_phan") or "").strip()[:20],
                       start_date=_ngay(r.get("ngay_bat_dau_pb")) or date.today(),
                       amount=_so(r.get("gia_tri")), months=int(_so(r.get("so_ky_pb")) or 1),
                       opening_allocated=_so(r.get("da_phan_bo")),
                       opening_period=str(r.get("ky_so_du") or "").strip()[:7],
                       quantity=int(_so(r.get("so_luong")) or 1),
                       note=str(r.get("ghi_chu") or "").strip()[:300], source="vtos", created_by=boi)
    db.add(p); db.flush()
    return f"{p.code} · {p.name} · {p.amount:,.0f} đ / {p.months} kỳ"


# ====================== TÀI SẢN – KHẤU HAO KỲ ĐÃ TÍNH Ở HỆ THỐNG CŨ ======================
def _kh_kiem(db: Session, r):
    from app.models.assets import FixedAsset, AssetDepreciation
    from app.services.intake import _so
    loi, cb = [], []
    ma = str(r.get("ma_ts") or "").strip().upper()
    a = db.execute(select(FixedAsset).where(func.upper(FixedAsset.code) == ma)).scalars().first() if ma else None
    if a is None:
        return [f"Không có thẻ tài sản mã '{ma}' – nạp thẻ tài sản trước rồi mới nạp bảng khấu hao"], cb, None
    ky = str(r.get("ky") or "").strip()
    st = _so(r.get("khau_hao_ky"))
    if st < 0: loi.append("Khấu hao trong kỳ không được âm")
    lk = _so(r.get("luy_ke"))
    if lk and lk > a.cost:
        loi.append(f"Lũy kế {lk:,.0f} lớn hơn nguyên giá {a.cost:,.0f} của thẻ {a.code}")
    # Ngoại lệ có ý thức: chỉ nhận kỳ TRƯỚC kỳ VTOS bắt đầu tự tính cho chính thẻ này.
    if a.start_date and ky and ky >= f"{a.start_date:%Y-%m}":
        loi.append(f"Kỳ {ky} là kỳ VTOS tự tính khấu hao cho thẻ {a.code} (bắt đầu {a.start_date:%m/%Y}). "
                   "Bộ nạp này chỉ dành cho các kỳ ĐÃ TÍNH Ở HỆ THỐNG CŨ – nạp đè lên kỳ VTOS tự tính là "
                   "thay một con số kiểm tra được bằng một con số gõ tay.")
    trung = db.execute(select(AssetDepreciation).where(
        AssetDepreciation.asset_id == a.id, AssetDepreciation.period == ky)).scalars().first() if ky else None
    return loi, cb, (f"{a.code} · {ky}" if trung is not None else None)


def _kh_nap(db: Session, r, boi):
    from app.models.assets import FixedAsset, AssetDepreciation
    from app.services.intake import _so
    ma = str(r.get("ma_ts") or "").strip().upper()
    a = db.execute(select(FixedAsset).where(func.upper(FixedAsset.code) == ma)).scalars().first()
    st = _so(r.get("khau_hao_ky"))
    lk = _so(r.get("luy_ke")) or st
    d = AssetDepreciation(asset_id=a.id, period=str(r.get("ky") or "").strip()[:7],
                          amount=st, accumulated=lk, remaining=max(a.cost - lk, 0.0))
    db.add(d); db.flush()
    return f"{a.code} · {d.period} · {st:,.0f} đ (còn lại {d.remaining:,.0f})"


# ====================== ĐỘI XE – BẰNG LÁI XE ======================
def _gplx_kiem(db: Session, r):
    from app.models.fleet import VehicleDocument
    from app.services.intake import _ngay
    from app.services.hang_gplx import so_cho_toi_da, tach_hang
    loi, cb = [], []
    e = _nv(db, r.get("ma_nv"))
    if e is None:
        return [f"Không có nhân sự mã '{r.get('ma_nv')}' – nạp hồ sơ nhân sự trước rồi mới nạp bằng lái"], cb, None
    so = str(r.get("so_gplx") or "").strip()
    if so and not so.isdigit():
        cb.append(f"Số GPLX '{so}' có ký tự không phải chữ số – giấy phép Việt Nam là dãy 12 chữ số")
    elif so and len(so) != 12:
        cb.append(f"Số GPLX '{so}' dài {len(so)} chữ số, giấy phép Việt Nam là 12 chữ số – kiểm tra lại")
    cap = _ngay(r.get("ngay_cap"))
    het = _ngay(r.get("ngay_het_han"))
    if cap and het and het < cap:
        loi.append("Ngày hết hạn trước ngày cấp")
    if het is None:
        cb.append("Chưa có ngày hết hạn – bản ghi sẽ hiện 'chưa đủ dữ liệu', không hiện màu xanh")
    elif het < date.today():
        cb.append(f"Bằng đã hết hạn từ {het:%d/%m/%Y} – tài xế này chưa được điều xe")
    hang = str(r.get("hang") or "").strip()
    if not hang:
        cb.append("Chưa ghi hạng – cổng điều xe sẽ không kết luận được người này lái được xe bao nhiêu chỗ")
    else:
        toi_da, ly_do = so_cho_toi_da(hang, cap)
        if toi_da == -1:
            cb.append(ly_do)
        elif toi_da == 0:
            loi.append(ly_do)
        elif toi_da is not None:
            cb.append(f"{ly_do} – không điều được xe lớn hơn")
    trung = db.execute(select(VehicleDocument).where(
        VehicleDocument.employee_id == e.id, VehicleDocument.kind == "gplx",
        func.upper(VehicleDocument.number) == so.upper())).scalars().first() if so else None
    return loi, cb, (f"{e.code} · {so}" if trung is not None else None)


def _gplx_nap(db: Session, r, boi):
    from app.models.fleet import VehicleDocument
    from app.services.intake import _ngay
    e = _nv(db, r.get("ma_nv"))
    het = _ngay(r.get("ngay_het_han"))
    # Bằng mới thì bằng cũ của chính người đó thôi hiệu lực – nhưng KHÔNG xóa, chỉ tắt cờ active.
    if het is not None:
        for cu in db.execute(select(VehicleDocument).where(
                VehicleDocument.employee_id == e.id, VehicleDocument.kind == "gplx",
                VehicleDocument.active == True)).scalars():          # noqa: E712
            if cu.expires_on is None or cu.expires_on <= het:
                cu.active = False
    g = VehicleDocument(employee_id=e.id, kind="gplx",
                        number=str(r.get("so_gplx") or "").strip()[:60],
                        hang=str(r.get("hang") or "").strip().upper()[:30],
                        issued_on=_ngay(r.get("ngay_cap")), expires_on=het,
                        source=str(r.get("nguon_giay") or "bản chụp giấy phép lái xe")[:120],
                        verify="nguon_ghi", note=str(r.get("ghi_chu") or "").strip()[:300],
                        created_by=boi)
    db.add(g); db.flush()
    return (f"{e.code} {e.full_name} · hạng {g.hang or '(chưa ghi)'} · "
            + (f"hạn {het:%d/%m/%Y}" if het else "chưa có hạn"))


# ====================== HCNS – HỢP ĐỒNG LAO ĐỘNG ======================
def _hdld_kiem(db: Session, r):
    from app.models.hrm import LaborContract, CONTRACT_KINDS
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    e = _nv(db, r.get("ma_nv"))
    if e is None:
        return [f"Không có nhân sự mã '{r.get('ma_nv')}' – nạp hồ sơ nhân sự trước rồi mới nạp hợp đồng"], cb, None
    loai = str(r.get("loai") or "").strip()
    if loai not in CONTRACT_KINDS:
        return [f"Loại hợp đồng '{loai}' không hợp lệ ({', '.join(CONTRACT_KINDS)})"], cb, None
    tu = _ngay(r.get("hieu_luc_tu"))
    den = _ngay(r.get("hieu_luc_den"))
    if tu and den and den < tu:
        loi.append("Ngày hết hiệu lực trước ngày có hiệu lực")
    if loai == "khong_xac_dinh" and den is not None:
        loi.append("Hợp đồng KHÔNG XÁC ĐỊNH thời hạn thì không được ghi ngày hết hiệu lực – "
                   "ghi vào là biến nó thành hợp đồng có thời hạn trên sổ")
    if loai != "khong_xac_dinh" and den is None:
        cb.append("Chưa có ngày hết hiệu lực – cảnh báo hợp đồng đến hạn sẽ KHÔNG chạy cho người này")
    # Loại hợp đồng và loại ghi ở hồ sơ nhân sự phải cùng nói một điều. Lệch nhau là chỗ bảng lương và
    # bảng bảo hiểm bắt đầu tính sai mà không ai thấy: hồ sơ nói cộng tác viên, hợp đồng nói HĐLĐ.
    ctv_hd = loai in ("ctv", "khoan")
    ctv_hs = e.contract_type == "ctv"
    if ctv_hd != ctv_hs:
        cb.append(f"Hồ sơ nhân sự ghi loại '{e.contract_type}' nhưng hợp đồng là '{CONTRACT_KINDS[loai]['ten']}' "
                  "– một trong hai đang sai, và bảng lương lấy theo hồ sơ")
    if CONTRACT_KINDS[loai]["bhxh"] and _so(r.get("luong_bhxh")) <= 0:
        cb.append(f"{CONTRACT_KINDS[loai]['ten']} thuộc diện đóng bảo hiểm nhưng chưa ghi mức lương đóng")
    ma = str(r.get("so_hop_dong") or "").strip()
    trung = db.execute(select(LaborContract).where(
        func.upper(LaborContract.code) == ma.upper())).scalars().first() if ma else None
    return loi, cb, (trung.code if trung is not None else None)


def _hdld_nap(db: Session, r, boi):
    from app.models.hrm import LaborContract, CONTRACT_KINDS
    from app.services.intake import _so, _ngay
    e = _nv(db, r.get("ma_nv"))
    loai = str(r.get("loai") or "").strip()
    tu = _ngay(r.get("hieu_luc_tu"))
    # Hợp đồng mới của cùng một người thì hợp đồng cũ chuyển sang "hết hạn" – KHÔNG xóa, và không đụng
    # bản đã chấm dứt (chấm dứt và hết hạn là hai chuyện khác nhau trên hồ sơ lao động).
    if tu is not None:
        for cu in db.execute(select(LaborContract).where(
                LaborContract.employee_id == e.id, LaborContract.status == "hieu_luc")).scalars():
            if cu.effective_from <= tu:
                cu.status = "het_han"
    def _t(k):
        return _so(r.get(k)) if str(r.get(k) or "").strip() != "" else 0.0
    c = LaborContract(employee_id=e.id, code=str(r.get("so_hop_dong") or "").strip()[:40], kind=loai,
                      signed_on=_ngay(r.get("ngay_ky")), effective_from=tu or date.today(),
                      effective_to=_ngay(r.get("hieu_luc_den")),
                      salary=_t("luong_chinh"), si_salary=_t("luong_bhxh"), allowance=_t("phu_cap"),
                      annual_leave_days=(_so(r.get("ngay_phep_nam")) if str(r.get("ngay_phep_nam") or "").strip() else 12),
                      note=str(r.get("ghi_chu") or "").strip()[:300], created_by=boi)
    db.add(c); db.flush()
    return (f"{c.code} · {e.code} {e.full_name} · {CONTRACT_KINDS[loai]['ten']}"
            + (f" · đến {c.effective_to:%d/%m/%Y}" if c.effective_to else " · không thời hạn"))


# ====================== KHAI BÁO ======================
# ====================== V12 – KHẾ ƯỚC VAY ======================
def _ku_kiem(db: Session, r):
    """Kiểm một dòng khế ước vay trước khi nạp.

    Bộ nạp này khác phần lớn bộ nạp khác ở một chỗ: nó không chỉ ghi một bản ghi, nó còn SINH RA
    LỊCH TRẢ NỢ bằng công thức. Nên phần kiểm phải chặt hơn – một khế ước sai công thức đẻ ra hàng
    chục dòng lịch sai, và mỗi dòng sai ấy về sau thành một bút toán sai.
    """
    from app.models.finance import FinContract
    from app.services.lich_tra_no import CONG_THUC, sinh_lich
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    so_hd = str(r.get("so_khe_uoc") or "").strip()
    if not so_hd:
        loi.append("Thiếu số khế ước")
    ngan_hang = str(r.get("ngan_hang") or "").strip()
    if not ngan_hang:
        loi.append("Thiếu tên ngân hàng – bên cho vay phải có tên, kể cả khi là cá nhân")
    goc = _so(r.get("so_tien_vay"))
    if goc <= 0:
        loi.append("Số tiền vay phải lớn hơn 0")
    ls = _so(r.get("lai_suat"))
    if ls < 0:
        loi.append("Lãi suất không được âm")
    elif ls > 30:
        cb.append(f"Lãi suất {ls}%/năm – cao bất thường, kiểm lại xem có nhập nhầm lãi suất THÁNG không")
    elif ls == 0:
        cb.append("Lãi suất bằng 0 – nếu đúng là vay không lãi thì phải có căn cứ, vì đây là giao "
                  "dịch có thể bị coi là giao dịch liên kết")
    try:
        ky_dau = _ngay(r.get("ngay_tra_dau"))
        _ngay(r.get("ngay_ky"))
    except ValueError as ex:
        loi.append(str(ex)); ky_dau = None
    so_ky = int(_so(r.get("so_ky")) or 0)
    if so_ky <= 0:
        loi.append("Số kỳ phải lớn hơn 0")
    ct = str(r.get("cong_thuc") or "goc_deu").strip() or "goc_deu"
    if ct not in CONG_THUC:
        loi.append(f"Công thức '{ct}' không có – chọn: " + " / ".join(CONG_THUC))
    if not str(r.get("nhom_vay") or "").strip():
        cb.append("Chưa ghi nhóm khoản vay – sao kê ngân hàng gộp chung vay mua xe, vay bất động sản "
                  "và vay vốn lưu động, để trống thì màn hình nợ đội xe sẽ hút nhầm khoản khác vào")
    trung = None
    if so_hd:
        trung = db.execute(select(FinContract).where(
            func.lower(FinContract.contract_no) == so_hd.lower())).scalars().first()
    # Thử sinh lịch NGAY LÚC KIỂM, không đợi tới lúc nạp: sai công thức thì phải hiện ở bước xem
    # trước, chứ không phải hiện sau khi đã ghi mấy chục dòng lịch vào cơ sở dữ liệu.
    if not loi and ky_dau:
        try:
            kq = sinh_lich(goc, ls, so_ky, ky_dau, ct)
            for c in kq["canh_bao"]:
                loi.append(c)
            cb.append(f"Lịch sẽ sinh {kq['so_ky']} kỳ, tổng lãi {kq['tong_lai']:,.0f}đ, "
                      f"tổng phải trả {kq['tong_phai_tra']:,.0f}đ ({kq['cong_thuc_ten']})")
        except ValueError as ex:
            loi.append(f"Không dựng được lịch trả nợ: {ex}")
    return loi, cb, (trung.code if trung is not None else None)


def _ku_nap(db: Session, r, boi):
    """Ghi khế ước và SINH LỊCH TRẢ NỢ từ công thức.

    Gốc và lãi tách thành HAI dòng lịch cho mỗi kỳ, vì chúng là hai bút toán (quyết định 08/9: không
    bù trừ). Kỳ có gốc bằng 0 – các kỳ đầu của kiểu trả cuối kỳ – thì KHÔNG sinh dòng gốc: một dòng
    lịch số tiền 0 là một dòng không ai ghi sổ được mà vẫn nằm chờ trong danh sách.
    """
    from app.models.finance import FinContract, FinSchedule
    from app.services.lich_tra_no import sinh_lich
    from app.services.intake import _so, _ngay
    goc = _so(r.get("so_tien_vay"))
    ls = _so(r.get("lai_suat"))
    so_ky = int(_so(r.get("so_ky")) or 0)
    ky_dau = _ngay(r.get("ngay_tra_dau"))
    ct = str(r.get("cong_thuc") or "goc_deu").strip() or "goc_deu"
    n = db.execute(select(func.count()).select_from(FinContract)).scalar() or 0
    c = FinContract(
        code=f"KU{n + 1:05d}", kind="vay",
        partner=str(r.get("ngan_hang") or "").strip()[:160],
        contract_no=str(r.get("so_khe_uoc") or "").strip()[:80],
        signed_on=_ngay(r.get("ngay_ky")), principal=goc, outstanding=goc,
        interest_rate=ls, maturity=_ngay(r.get("ngay_dao_han")),
        loan_group=str(r.get("nhom_vay") or "").strip()[:24],
        collateral=str(r.get("tai_san_bao_dam") or "")[:300],
        purpose=str(r.get("muc_dich") or "")[:300],
        note=str(r.get("ghi_chu") or "")[:300], created_by=boi)
    db.add(c); db.flush()
    kq = sinh_lich(goc, ls, so_ky, ky_dau, ct)
    for d in kq["dong"]:
        if d["goc"] > 0:
            db.add(FinSchedule(contract_id=c.id, ky=d["ky"], due_date=d["ngay"],
                               kind="tra_goc", amount=d["goc"]))
        if d["lai"] > 0:
            db.add(FinSchedule(contract_id=c.id, ky=d["ky"], due_date=d["ngay"],
                               kind="tra_lai", amount=d["lai"]))
    db.flush()
    return (f"{c.code} – {c.partner}: {kq['so_ky']} kỳ, tổng lãi {kq['tong_lai']:,.0f}đ "
            f"({kq['cong_thuc_ten']})")


def bo_nap(_c) -> dict:
    from app.models.fleet import NHOM_CHI_PHI_KY
    from app.models.nap_bo_sung import KENH_MKT
    from app.models.assets import ASSET_KINDS, PREPAID_KINDS
    from app.models.hrm import CONTRACT_KINDS
    nhom_ky = {k: v[0] + (" (theo xe)" if v[1] == "xe" else " (cả đội)") for k, v in NHOM_CHI_PHI_KY.items()}
    return {
        # ---------- ĐỘI XE ----------
        "nhien_lieu": {
            "bang_dich": "fleet_external_txns", "phong_ban": "doi_xe",
            "ten": "Nhiên liệu – sao kê thẻ dầu",
            "mo_ta": "Sao kê thẻ dầu tải từ ngân hàng. Giao dịch nạp lên nằm ở trạng thái CHƯA KHỚP – "
                     "ghép vào chuyến nào là bước riêng có người xác nhận. Nạp lại cùng một tệp không "
                     "sinh bản ghi thứ hai: khóa là nguồn + mã giao dịch gốc.",
            "khoa_chong_trung": "Mã giao dịch trên sao kê thẻ dầu",
            "cot": [_c("ma_gd", "Mã giao dịch", True, vi_du="FT26240012345",
                       ghi_chu="mã ngân hàng in trên sao kê – khóa chống nạp trùng"),
                    _c("thoi_diem", "Thời điểm", True, kieu="ngay", vi_du="31/08/2026",
                       khong_tuong_lai=True),
                    _c("bien_so", "Biển số xe", vi_du="50F-034.71",
                       ghi_chu="tra về xe theo LỊCH SỬ biển số tại thời điểm giao dịch"),
                    _c("the_4so", "Bốn số cuối thẻ", ghi_chu="thẻ gắn với TÀI XẾ, không gắn với xe"),
                    _c("so_tien", "Số tiền", True, kieu="tien", min=0, vi_du="8460000"),
                    _c("lit", "Số lít", kieu="so", vi_du="423"),
                    _c("mo_ta", "Nội dung giao dịch")],
            "kiem": _dau_kiem, "nap": _dau_nap,
        },
        "phi_cau_duong": {
            "bang_dich": "fleet_external_txns", "phong_ban": "doi_xe",
            "ten": "Phí cầu đường – báo cáo ePass / VETC",
            "mo_ta": "Báo cáo trạm thu phí. Báo cáo ePass tháng 8/2026 có hai bản ghi lặp hoàn toàn – bản "
                     "trùng vẫn được GIỮ trong bảng thô với cờ riêng, chỉ loại ở tầng tính, để còn chứng "
                     "minh được mình đã loại đúng cái gì.",
            "khoa_chong_trung": "Mã giao dịch trên báo cáo ePass/VETC",
            "cot": [_c("ma_gd", "Mã giao dịch", True, vi_du="EP2608310001"),
                    _c("thoi_diem", "Thời điểm", True, kieu="ngay", vi_du="31/08/2026",
                       khong_tuong_lai=True),
                    _c("bien_so", "Biển số xe", vi_du="50F-034.71"),
                    _c("so_tien", "Số tiền", True, kieu="tien", min=0, vi_du="1180000"),
                    _c("mo_ta", "Trạm / tuyến")],
            "kiem": _epass_kiem, "nap": _epass_nap,
        },
        "bao_duong": {
            "bang_dich": "fleet_maintenance", "phong_ban": "doi_xe",
            "ten": "Bảo dưỡng, sửa chữa xe",
            "mo_ta": "Mỗi dòng phải quy được về một chiếc cụ thể. Số km lúc làm không bắt buộc về kỹ "
                     "thuật nhưng thiếu nó thì không phát hiện được chi phí ghi sai kỳ – đúng lỗi đã xảy "
                     "ra với xe 50H-496.23 tháng 8/2026.",
            "khoa_chong_trung": "Xe + ngày + nội dung",
            "cot": [_c("bien_so", "Biển số xe", True, vi_du="50F-034.71"),
                    _c("ngay", "Ngày làm", True, kieu="ngay", vi_du="12/08/2026",
                       khoa_ky=True, khong_tuong_lai=True),
                    _c("loai", "Loại", kieu="chon", vi_du="dinh_ky",
                       chon={"dinh_ky": "Bảo dưỡng định kỳ", "sua_chua": "Sửa chữa", "lop": "Lốp",
                             "dong_son": "Đồng sơn", "khac": "Khác"}),
                    _c("noi_dung", "Nội dung", True, vi_du="Thay dầu máy, lọc gió"),
                    _c("km_luc_lam", "Km lúc làm", kieu="so", vi_du="216511"),
                    _c("km_ky_toi", "Km kỳ tới", kieu="so", vi_du="221000"),
                    _c("garage", "Gara"),
                    _c("so_tien", "Số tiền", kieu="tien", min=0,
                       ghi_chu="để TRỐNG nếu chưa có hóa đơn – đừng ghi 0"),
                    _c("ben_chiu", "Bên chịu", kieu="chon", vi_du="chu_xe",
                       chon={"chu_xe": "Chủ xe tự chịu", "vietourist": "Vietourist chịu",
                             "vietourist_tam_ung": "Vietourist tạm ứng, cấn trừ sau"}),
                    _c("chung_tu", "Chứng từ")],
            "kiem": _bd_kiem, "nap": _bd_nap,
        },
        "dang_kiem": {
            "bang_dich": "vehicle_documents", "phong_ban": "doi_xe",
            "ten": "Đăng kiểm xe",
            "mo_ta": "Giấy đăng kiểm và hạn của nó. Ngày hết hạn để rỗng KHÔNG có nghĩa là còn hạn – nó "
                     "có nghĩa là chưa biết, và màn hình sẽ hiện 'chưa đủ dữ liệu' chứ không hiện màu "
                     "xanh. Nạp giấy mới thì giấy cũ của chính xe đó thôi hiệu lực nhưng KHÔNG bị xóa.",
            "khoa_chong_trung": "Xe + số giấy đăng kiểm",
            "cot": [_c("bien_so", "Biển số xe", True, vi_du="50F-034.71"),
                    _c("so_giay", "Số giấy chứng nhận", True, vi_du="AB-1234567"),
                    _c("ngay_cap", "Ngày cấp", kieu="ngay", vi_du="15/03/2026"),
                    _c("ngay_het_han", "Ngày hết hạn", kieu="ngay", vi_du="15/09/2026",
                       ghi_chu="để trống = CHƯA BIẾT, không phải còn hạn"),
                    _c("nguon_giay", "Nguồn dữ liệu", vi_du="Bản chụp giấy đăng kiểm"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _dk_kiem, "nap": _dk_nap,
        },
        "chi_phi_ky_doi_xe": {
            "bang_dich": "fleet_period_costs", "phong_ban": "doi_xe",
            "ten": "Chi phí kỳ của đội xe",
            "mo_ta": "Khoản không gắn vào chuyến nào: bảo hiểm, lương tài xế, phí bãi, lãi vay. Nhóm "
                     "'theo xe' bắt buộc có biển số; nhóm 'cả đội' bắt buộc KHÔNG có – hệ thống cố ý "
                     "không chia lãi vay hay phí bãi cho từng chiếc, vì mọi cách chia đều 'có lý' và ra "
                     "số khác nhau.",
            "khoa_chong_trung": "Kỳ + nhóm + xe + diễn giải",
            "cot": [_c("ky", "Kỳ", True, kieu="thang", vi_du="2026-08"),
                    _c("nhom", "Nhóm chi phí", True, kieu="chon", vi_du="lai_vay", chon=nhom_ky),
                    _c("bien_so", "Biển số xe", ghi_chu="chỉ điền cho nhóm theo xe"),
                    _c("mo_ta", "Diễn giải", vi_du="Lãi vay tháng 8 – VPBank"),
                    _c("so_tien", "Số tiền", True, kieu="tien", min=0, vi_du="327000000"),
                    _c("chung_tu", "Chứng từ")],
            "kiem": _cpk_kiem, "nap": _cpk_nap,
        },
        "bang_lai_xe": {
            "bang_dich": "vehicle_documents", "phong_ban": "doi_xe",
            "ten": "Bằng lái xe của tài xế",
            "mo_ta": "Giấy phép lái xe: số, HẠNG, ngày cấp, ngày hết hạn. Hạng và ngày cấp phải đi "
                     "cùng nhau – chữ D đảo nghĩa giữa luật cũ (tối đa 30 chỗ) và luật mới từ "
                     "01/01/2025 (hạng cao nhất), và ngày cấp là thứ duy nhất phân biệt được. Thiếu "
                     "một trong hai thì cổng điều xe trả 'chưa đủ dữ liệu', không trả 'đạt'.",
            "khoa_chong_trung": "Mã nhân viên + số GPLX",
            "cot": [_c("ma_nv", "Mã nhân viên", True, vi_du="NS0013"),
                    _c("so_gplx", "Số GPLX", True, vi_du="790118255611",
                       ghi_chu="12 chữ số, in trên giấy phép"),
                    _c("hang", "Hạng", True, vi_du="E",
                       ghi_chu="chép NGUYÊN VĂN trên giấy: E / D / A1, E, FC / D, CE"),
                    _c("ngay_cap", "Ngày cấp", True, kieu="ngay", vi_du="30/08/2022",
                       ghi_chu="bắt buộc – quyết định đọc hạng theo luật cũ hay luật mới"),
                    _c("ngay_het_han", "Ngày hết hạn", kieu="ngay", vi_du="30/08/2027",
                       ghi_chu="để trống = CHƯA BIẾT, không phải còn hạn"),
                    _c("nguon_giay", "Nguồn dữ liệu", vi_du="Bản chụp GPLX"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _gplx_kiem, "nap": _gplx_nap,
        },
        # ---------- MARKETING ----------
        "chi_marketing_kenh": {
            "bang_dich": "mkt_channel_spend", "phong_ban": "marketing",
            "ten": "Chi phí marketing theo kênh",
            "mo_ta": "Số THỰC CHI của từng kênh trong kỳ, kèm số đo của kênh đó. Ngân sách dự toán nằm ở "
                     "bảng khác và cố ý không trộn vào đây. Lượt hiển thị / nhấp / lead để RỖNG khi chưa "
                     "lấy được báo cáo – ghi 0 sẽ làm phép tính chi phí mỗi lead chia cho một số 0 giả.",
            "khoa_chong_trung": "Kỳ + kênh + chiến dịch",
            "cot": [_c("ky", "Kỳ", True, kieu="thang", vi_du="2026-08"),
                    _c("kenh", "Kênh", True, kieu="chon", vi_du="facebook_ads", chon=KENH_MKT),
                    _c("chien_dich", "Chiến dịch", ghi_chu="để trống = chi chung của kênh"),
                    _c("so_tien", "Số tiền đã chi", True, kieu="tien", min=0, vi_du="45000000"),
                    _c("luot_hien_thi", "Lượt hiển thị", kieu="so"),
                    _c("luot_nhap", "Lượt nhấp", kieu="so"),
                    _c("so_lead", "Số lead", kieu="so",
                       ghi_chu="để TRỐNG nếu chưa lấy được số – đừng ghi 0"),
                    _c("mo_ta", "Diễn giải"), _c("chung_tu", "Chứng từ")],
            "kiem": _mkt_kiem, "nap": _mkt_nap,
        },
        # ---------- KINH DOANH ----------
        "doanh_so_tu_van_vien": {
            "bang_dich": "sales_by_consultant", "phong_ban": "kd_le",
            "ten": "Doanh số theo tư vấn viên",
            "mo_ta": "Số Kinh doanh chốt với nhau để tính hoa hồng. Đây là bảng GHI NHẬN, không phải phép "
                     "tính: VTOS cộng được doanh số từ booking, nhưng quy ước tính hoa hồng có riêng của "
                     "nó. Giữ cả hai con số mới nhìn thấy được chênh lệch; bỏ một con số không làm chúng "
                     "giống nhau.",
            "khoa_chong_trung": "Kỳ + mã nhân viên",
            "cot": [_c("ky", "Kỳ", True, kieu="thang", vi_du="2026-08"),
                    _c("ma_nv", "Mã nhân viên", True, vi_du="NS0142"),
                    _c("nhom_kd", "Nhóm kinh doanh", ghi_chu="để trống thì lấy theo hồ sơ nhân sự"),
                    _c("so_booking", "Số booking", kieu="so"),
                    _c("so_khach", "Số khách", kieu="so"),
                    _c("doanh_thu", "Doanh thu", kieu="tien", min=0, vi_du="850000000"),
                    _c("doanh_thu_da_thu", "Trong đó đã thu", kieu="tien", min=0),
                    _c("hoa_hong", "Hoa hồng", kieu="tien", min=0,
                       ghi_chu="để TRỐNG nếu kỳ chưa duyệt tỷ lệ"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _ds_kiem, "nap": _ds_nap,
        },
        # ---------- HƯỚNG DẪN ----------
        "thu_lao_hdv": {
            "bang_dich": "guide_assignments", "phong_ban": "huong_dan",
            "ten": "Thù lao hướng dẫn viên theo chuyến",
            "mo_ta": "Nạp các chuyến ĐÃ ĐI của kỳ trước để tính thù lao. Đây KHÔNG phải nơi tạo lời chào "
                     "chuyến: chào chuyến có cửa riêng, có hạn trả lời và có quyền từ chối, nạp hàng "
                     "loạt qua đây là lách mất cả ba. Bản ghi tạo ở đây vào thẳng trạng thái đã xác "
                     "nhận và không gửi thông báo cho ai.",
            "khoa_chong_trung": "Mã tour + hướng dẫn viên",
            "cot": [_c("ma_tour", "Mã tour", True, vi_du="DL2608-01"),
                    _c("the_so", "Số thẻ HDV", vi_du="HDV-NĐ-2023-0451",
                       ghi_chu="ưu tiên tra theo số thẻ; không có thì tra theo mã nhân viên"),
                    _c("ma_nv", "Mã nhân viên", vi_du="NS0210"),
                    _c("so_ngay", "Số ngày", True, kieu="so", vi_du="4"),
                    _c("don_gia_ngay", "Đơn giá ngày", kieu="tien", min=0, vi_du="700000",
                       ghi_chu="để TRỐNG nếu chưa có bảng giá tuyến – hệ thống KHÔNG tự điền"),
                    _c("le_tet", "Lễ Tết", ghi_chu="ghi x nếu chuyến rơi vào lễ Tết (đơn giá ×2)"),
                    _c("da_nop_bao_cao", "Đã nộp báo cáo tour", ghi_chu="ghi x nếu đã nộp")],
            "kiem": _tl_kiem, "nap": _tl_nap,
        },
        # ---------- KẾ TOÁN ----------
        "hoa_don_dau_vao": {
            "bang_dich": "purchase_invoices", "phong_ban": "ketoan",
            "ten": "Hóa đơn GTGT đầu vào",
            "mo_ta": "Hóa đơn nhà cung cấp xuất cho công ty. Khóa chống trùng là bộ ba MST người bán + "
                     "ký hiệu + số hóa đơn, đúng bộ ba định danh một hóa đơn ở cơ quan thuế – lấy số hóa "
                     "đơn một mình thì hai nhà cung cấp cùng có hóa đơn số 42 sẽ đè lên nhau. Nạp lên "
                     "KHÔNG tự ghi sổ và không tự gắn vào tour.",
            "khoa_chong_trung": "MST người bán + ký hiệu + số hóa đơn",
            "cot": [_c("mst_nguoi_ban", "MST người bán", True, vi_du="0301234567"),
                    _c("ten_nguoi_ban", "Tên người bán", vi_du="Công ty TNHH Khách sạn ABC"),
                    _c("ky_hieu", "Ký hiệu", True, vi_du="1C26TAA"),
                    _c("so_hoa_don", "Số hóa đơn", True, vi_du="00001234"),
                    _c("ngay_hd", "Ngày hóa đơn", True, kieu="ngay", vi_du="20/08/2026",
                       khoa_ky=True, khong_tuong_lai=True),
                    _c("noi_dung", "Nội dung", vi_du="Tiền phòng đoàn Đà Lạt 17-19/8"),
                    _c("tien_truoc_thue", "Tiền trước thuế", kieu="tien", min=0),
                    _c("thue_suat", "Thuế suất", kieu="so", vi_du="8", ghi_chu="0 / 5 / 8 / 10"),
                    _c("tien_thue", "Tiền thuế", kieu="tien", min=0),
                    _c("tong_tien", "Tổng tiền", kieu="tien", min=0,
                       ghi_chu="để trống thì hệ thống cộng trước thuế + thuế"),
                    _c("ma_tour", "Mã tour liên quan", ghi_chu="gợi ý để kế toán ghép, chưa phải ràng buộc"),
                    _c("chung_tu", "Tệp hóa đơn trong kho")],
            "kiem": _hd_kiem, "nap": _hd_nap,
        },
        # ---------- HÀNH CHÍNH & NHÂN SỰ ----------
        "bao_hiem_ky": {
            "bang_dich": "social_insurance_periods", "phong_ban": "hcns",
            "ten": "Bảo hiểm phải đóng theo kỳ",
            "mo_ta": "Số ĐÃ CHỐT VỚI CƠ QUAN BẢO HIỂM. Cố ý là bảng riêng chứ không phải một cột của "
                     "bảng lương: người vào giữa tháng, nghỉ không lương, vượt trần đóng hay truy thu "
                     "đều làm hai số lệch nhau, và giữ một con số thì mỗi lần lệch không ai biết bên "
                     "nào sai.",
            "khoa_chong_trung": "Kỳ + mã nhân viên",
            "cot": [_c("ky", "Kỳ", True, kieu="thang", vi_du="2026-08"),
                    _c("ma_nv", "Mã nhân viên", True, vi_du="NS0142"),
                    _c("muc_dong", "Mức lương đóng bảo hiểm", kieu="tien", min=0),
                    _c("cty_dong", "Phần công ty đóng", kieu="tien", min=0),
                    _c("nld_dong", "Phần người lao động đóng", kieu="tien", min=0),
                    _c("so_ngay_dong", "Số ngày đóng trong kỳ", kieu="so"),
                    _c("trang_thai", "Trạng thái", kieu="chon", vi_du="dang_dong",
                       chon={"dang_dong": "Đang đóng", "bao_giam": "Báo giảm", "truy_thu": "Truy thu"}),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _bh_kiem, "nap": _bh_nap,
        },
        "bang_luong": {
            "bang_dich": "payroll_runs", "phong_ban": "hcns",
            "ten": "Bảng lương – kỳ chưa chốt",
            "mo_ta": "Ghi vào ĐẦU VÀO của kỳ lương, và chỉ chạm được vào kỳ còn ở trạng thái nháp. Kỳ đã "
                     "có xác nhận của Kế toán trở đi thì từ chối: nạp đè lên một bảng đã ký là xóa mất "
                     "căn cứ của chữ ký đó. Các cột tiền để trống được – dòng này là số để hệ thống "
                     "tính, không phải số đã chốt.",
            "khoa_chong_trung": "Kỳ + mã nhân viên",
            "cot": [_c("ky", "Kỳ lương", True, kieu="thang", vi_du="2026-08"),
                    _c("ma_nv", "Mã nhân viên", True, vi_du="NS0142"),
                    _c("cong_thuc_te", "Công thực tế", True, kieu="so", vi_du="24"),
                    _c("cong_chuan", "Công chuẩn của kỳ", kieu="so",
                       ghi_chu="chỉ cần ghi ở một dòng của kỳ"),
                    _c("luong_cong_viec", "Lương công việc", kieu="tien", min=0),
                    _c("phu_cap", "Phụ cấp", kieu="tien", min=0),
                    _c("thuong", "Thưởng", kieu="tien", min=0),
                    _c("khau_tru", "Khấu trừ", kieu="tien", min=0),
                    _c("thuc_linh", "Thực lĩnh", kieu="tien", min=0,
                       ghi_chu="để TRỐNG nếu chưa chốt – hệ thống vẫn tính lại"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _bl_kiem, "nap": _bl_nap,
        },
        "hop_dong_lao_dong": {
            "bang_dich": "labor_contracts", "phong_ban": "hcns",
            "ten": "Hợp đồng lao động",
            "mo_ta": "Mỗi lần ký là một bản ghi, giữ đủ lịch sử. Nạp hợp đồng mới thì bản cũ còn hiệu "
                     "lực của chính người đó chuyển sang HẾT HẠN – không xóa, và không đụng bản đã "
                     "chấm dứt: chấm dứt và hết hạn là hai chuyện khác nhau trên hồ sơ lao động. "
                     "Hợp đồng không xác định thời hạn thì KHÔNG được ghi ngày hết hiệu lực.",
            "khoa_chong_trung": "Số hợp đồng",
            "cot": [_c("so_hop_dong", "Số hợp đồng", True, vi_du="HDLD-2026-014"),
                    _c("ma_nv", "Mã nhân viên", True, vi_du="NS0142"),
                    _c("loai", "Loại hợp đồng", True, kieu="chon", vi_du="xac_dinh_12",
                       chon={k: v["ten"] for k, v in CONTRACT_KINDS.items()}),
                    _c("ngay_ky", "Ngày ký", kieu="ngay", vi_du="01/08/2026"),
                    _c("hieu_luc_tu", "Hiệu lực từ", True, kieu="ngay", vi_du="01/08/2026"),
                    _c("hieu_luc_den", "Hiệu lực đến", kieu="ngay", vi_du="31/07/2027",
                       ghi_chu="để TRỐNG cho hợp đồng không xác định thời hạn"),
                    _c("luong_chinh", "Lương chính", kieu="tien", min=0),
                    _c("luong_bhxh", "Mức lương đóng BHXH", kieu="tien", min=0,
                       ghi_chu="khác lương chính; loại thuộc diện đóng mà để trống sẽ bị cảnh báo"),
                    _c("phu_cap", "Phụ cấp", kieu="tien", min=0),
                    _c("ngay_phep_nam", "Ngày phép năm", kieu="so", vi_du="12"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _hdld_kiem, "nap": _hdld_nap,
        },
        # ---------- TÀI SẢN & MUA SẮM ----------
        "tai_san_co_dinh": {
            "bang_dich": "fixed_assets", "phong_ban": "ketoan",
            "ten": "Thẻ tài sản cố định",
            "mo_ta": "Thẻ TSCĐ theo cấu trúc MISA. Có hao mòn lũy kế thì BẮT BUỘC ghi kỳ tương ứng – "
                     "một con số lũy kế không biết tính đến lúc nào thì không dùng được vào việc gì. "
                     "Nạp chỉ tạo mới: mã đã có thì bỏ qua, không ghi đè nguyên giá.",
            "khoa_chong_trung": "Mã tài sản",
            "cot": [_c("ma_ts", "Mã tài sản", True, vi_du="TS0001"),
                    _c("ten", "Tên tài sản", True, vi_du="Xe khách Universe 45 chỗ"),
                    _c("loai", "Loại", kieu="chon", vi_du="huu_hinh",
                       chon={k: v["ten"] for k, v in ASSET_KINDS.items()}),
                    _c("nhom", "Nhóm", vi_du="Phương tiện vận tải"),
                    _c("nha_cung_cap", "Nhà cung cấp"),
                    _c("bo_phan", "Bộ phận sử dụng", vi_du="doi_xe"),
                    _c("ngay_mua", "Ngày mua", kieu="ngay"),
                    _c("ngay_bat_dau_kh", "Ngày bắt đầu khấu hao", True, kieu="ngay", vi_du="01/01/2024"),
                    _c("nguyen_gia", "Nguyên giá", True, kieu="tien", min=0, vi_du="3200000000"),
                    _c("so_thang_kh", "Số tháng khấu hao", kieu="so", vi_du="120"),
                    _c("hao_mon_luy_ke", "Hao mòn lũy kế khi nạp", kieu="tien", min=0),
                    _c("ky_so_du", "Kỳ của số lũy kế", kieu="thang", vi_du="2025-12",
                       ghi_chu="bắt buộc nếu có hao mòn lũy kế"),
                    _c("so_luong", "Số lượng", kieu="so"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _ts_kiem, "nap": _ts_nap,
        },
        "cong_cu_dung_cu": {
            "bang_dich": "prepaid_expenses", "phong_ban": "ketoan",
            "ten": "Công cụ dụng cụ & chi phí trả trước",
            "mo_ta": "Thẻ CCDC / chi phí trả trước phân bổ đều theo tháng vào TK 242. Cùng quy tắc với "
                     "tài sản cố định: có số đã phân bổ thì phải ghi kỳ tương ứng.",
            "khoa_chong_trung": "Mã công cụ dụng cụ",
            "cot": [_c("ma_ccdc", "Mã CCDC", True, vi_du="CC0001"),
                    _c("ten", "Tên", True, vi_du="Bộ lốp xe 50F-034.71"),
                    _c("loai", "Loại", kieu="chon", vi_du="ccdc",
                       chon={k: v["ten"] for k, v in PREPAID_KINDS.items()}),
                    _c("nha_cung_cap", "Nhà cung cấp"),
                    _c("bo_phan", "Bộ phận sử dụng", vi_du="doi_xe"),
                    _c("ngay_bat_dau_pb", "Ngày bắt đầu phân bổ", True, kieu="ngay", vi_du="01/08/2026"),
                    _c("gia_tri", "Giá trị phân bổ", True, kieu="tien", min=0, vi_du="48000000"),
                    _c("so_ky_pb", "Số kỳ phân bổ", True, kieu="so", vi_du="12"),
                    _c("da_phan_bo", "Đã phân bổ trước khi lên VTOS", kieu="tien", min=0),
                    _c("ky_so_du", "Kỳ của số đã phân bổ", kieu="thang", vi_du="2026-07"),
                    _c("so_luong", "Số lượng", kieu="so"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _cc_kiem, "nap": _cc_nap,
        },
        # ---------- V12: KHẾ ƯỚC VAY ----------
        "khe_uoc_vay": {
            "bang_dich": "fin_contracts", "phong_ban": "ketoan",
            "ten": "Khế ước vay ngân hàng",
            "mo_ta": "Nạp khế ước và TỰ SINH LỊCH TRẢ NỢ theo công thức. Ba công thức vì ba ngân hàng "
                     "của công ty dùng ba kiểu: gốc đều (lãi giảm dần) · niên kim (gốc+lãi mỗi kỳ "
                     "bằng nhau) · trả gốc một lần cuối kỳ. Lịch sinh ra là lịch THAM CHIẾU – lịch "
                     "chính thức là lịch ngân hàng phát hành; lệch vài nghìn đồng do quy tắc làm "
                     "tròn là bình thường, lệch lớn nghĩa là chọn sai công thức. Gốc và lãi tách "
                     "thành hai dòng lịch vì chúng là hai bút toán, không bù trừ.",
            "khoa_chong_trung": "Số khế ước",
            "cot": [_c("so_khe_uoc", "Số khế ước", True, vi_du="KU-2026-018",
                       ghi_chu="số ghi trên hợp đồng tín dụng – khóa chống nạp trùng"),
                    _c("ngan_hang", "Ngân hàng / bên cho vay", True, vi_du="TPBank – CN Bến Thành",
                       ghi_chu="cá nhân cho vay cũng phải ghi tên"),
                    _c("so_tien_vay", "Số tiền vay", True, kieu="tien", min=0, vi_du="1200000000"),
                    _c("lai_suat", "Lãi suất (%/năm)", True, kieu="so", min=0, vi_du="9.5",
                       ghi_chu="ghi theo NĂM, không theo tháng"),
                    _c("so_ky", "Số kỳ trả", True, kieu="so", min=1, vi_du="12",
                       ghi_chu="số kỳ THÁNG của lịch trả nợ"),
                    _c("ngay_tra_dau", "Ngày trả kỳ đầu", True, kieu="ngay", vi_du="15/10/2026"),
                    _c("cong_thuc", "Công thức lịch trả nợ", kieu="chon", vi_du="goc_deu",
                       chon={"goc_deu": "Gốc đều, lãi trên dư nợ giảm dần",
                             "nien_kim": "Trả góp đều (niên kim)",
                             "cuoi_ky": "Gốc trả một lần cuối kỳ"},
                       ghi_chu="để trống = gốc đều"),
                    _c("ngay_ky", "Ngày ký khế ước", kieu="ngay", vi_du="10/10/2026",
                       khong_tuong_lai=True),
                    _c("ngay_dao_han", "Ngày đáo hạn", kieu="ngay", vi_du="15/09/2027"),
                    _c("nhom_vay", "Nhóm khoản vay", kieu="chon", vi_du="vay_xe_45cho",
                       chon={"vay_xe_45cho": "Vay mua xe 45 chỗ", "vay_xe_khac": "Vay mua xe khác",
                             "von_luu_dong": "Vay vốn lưu động", "bds": "Vay bất động sản",
                             "khac": "Khác"},
                       ghi_chu="để trống thì màn hình nợ đội xe sẽ hút nhầm khoản khác vào"),
                    _c("tai_san_bao_dam", "Tài sản bảo đảm", vi_du="Xe 50F-009.60"),
                    _c("muc_dich", "Mục đích vay", vi_du="Mua xe 45 chỗ"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _ku_kiem, "nap": _ku_nap,
        },
        "khau_hao_ky": {
            "bang_dich": "asset_depreciations", "phong_ban": "ketoan",
            "ten": "Khấu hao kỳ đã tính ở hệ thống cũ",
            "mo_ta": "Ngoại lệ CÓ Ý THỨC với nguyên tắc 'không nạp kết quả đã tính'. Khấu hao các kỳ "
                     "trước khi lên VTOS không tính lại được vì thiếu chính sách khấu hao từng thời kỳ, "
                     "mà thiếu nó thì giá trị còn lại sai. Bù lại, bộ nạp chỉ nhận kỳ TRƯỚC kỳ VTOS bắt "
                     "đầu tự tính cho chính thẻ đó – không nạp đè lên kỳ máy tự tính được. Khấu hao là "
                     "khoản chênh lớn nhất giữa lãi theo đoàn và lãi trên sổ: 3,46 tỷ trong 6 tháng đầu "
                     "2026.",
            "khoa_chong_trung": "Mã tài sản + kỳ",
            "cot": [_c("ma_ts", "Mã tài sản", True, vi_du="TS0001"),
                    _c("ky", "Kỳ", True, kieu="thang", vi_du="2025-12"),
                    _c("khau_hao_ky", "Khấu hao trong kỳ", True, kieu="tien", min=0, vi_du="26666667"),
                    _c("luy_ke", "Lũy kế đến hết kỳ", kieu="tien", min=0,
                       ghi_chu="để trống thì lấy bằng khấu hao trong kỳ")],
            "kiem": _kh_kiem, "nap": _kh_nap,
        },
    }


# Ai được nạp loại nào. Khai ở đây rồi intake.py gộp vào VAI_TRO chung – để thêm một bộ nạp là sửa
# đúng một tệp, không phải hai.
def vai_tro(QUAN_TRI: tuple) -> dict:
    return {
        "nhien_lieu":           QUAN_TRI + ("gd_doi_xe", "tp_dh", "nv_dh", "ketoan"),
        "phi_cau_duong":        QUAN_TRI + ("gd_doi_xe", "tp_dh", "nv_dh", "ketoan"),
        "bao_duong":            QUAN_TRI + ("gd_doi_xe", "ketoan"),
        "dang_kiem":            QUAN_TRI + ("gd_doi_xe",),
        "chi_phi_ky_doi_xe":    QUAN_TRI + ("gd_doi_xe", "ketoan"),
        "bang_lai_xe":          QUAN_TRI + ("gd_doi_xe", "hcns"),
        "chi_marketing_kenh":   QUAN_TRI + ("ptgd_mkt", "nv_mkt", "ketoan"),
        "doanh_so_tu_van_vien": QUAN_TRI + ("gd_kd", "tp_kd", "ketoan"),
        "thu_lao_hdv":          QUAN_TRI + ("tp_hd", "tp_dh", "ketoan"),
        "hoa_don_dau_vao":      QUAN_TRI + ("ketoan",),
        "bao_hiem_ky":          QUAN_TRI + ("hcns", "ketoan"),
        "bang_luong":           QUAN_TRI + ("hcns",),
        "hop_dong_lao_dong":    QUAN_TRI + ("hcns",),
        "tai_san_co_dinh":      QUAN_TRI + ("ketoan",),
        "cong_cu_dung_cu":      QUAN_TRI + ("ketoan",),
        "khe_uoc_vay":          QUAN_TRI + ("ketoan",),
        "khau_hao_ky":          QUAN_TRI + ("ketoan",),
    }


# Bộ nạp nào CHẠM THẲNG VÀO TIỀN – nhân viên nhập tay được, tải tệp hàng loạt thì không (quy tắc P4).
CHAM_TIEN = ("nhien_lieu", "phi_cau_duong", "bao_duong", "chi_phi_ky_doi_xe", "chi_marketing_kenh",
             "doanh_so_tu_van_vien", "thu_lao_hdv", "hoa_don_dau_vao", "bao_hiem_ky", "bang_luong",
             "hop_dong_lao_dong", "tai_san_co_dinh", "cong_cu_dung_cu", "khau_hao_ky",
             # V12 – một dòng khế ước sai đẻ ra hàng chục dòng lịch sai, và mỗi dòng lịch sai về sau
             # thành một bút toán sai. Nhập tay từng cái thì còn nhìn thấy; một tệp thì không.
             "khe_uoc_vay")
