"""K1 và K2 – hai bộ kiểm nền tảng của robot Kiểm soát, viết TRƯỚC khi ai sửa.

K1: cột tiền đang khai kiểu số thực nhị phân (Float). Số thực nhị phân không biểu diễn chính xác được
    số tiền – cộng vài nghìn dòng là lệch vài đồng, và lệch ở chỗ không ai nhìn. Với công ty đại chúng
    thì đó đúng là chỗ kiểm toán đối chiếu đầu tiên.

K2: cột tiền khai mặc định 0 và KHÔNG cho phép rỗng. Ở những cột đó, "chưa có số" bị ghi thành 0 và
    không cách nào phân biệt với số 0 thật. Đây không phải lo xa: 76 dòng quyết toán không có giá vốn
    nạp thẳng vào hệ thống đã làm báo cáo hiện lãi 100%.

Điều tệp này CỐ TÌNH không làm: tự quyết cột nào là tiền. Nó ĐỀ XUẤT theo tên cột và ghi rõ dựa vào
đâu; cột nào tên không nói lên điều gì thì xếp "chưa rõ" và chờ người quyết. Một bộ kiểm tự tin xếp
loại sai 20 cột rồi bắt người khác sửa theo là bộ kiểm không ai dùng lần thứ hai.
"""
from datetime import datetime
from sqlalchemy import select, Float, Numeric
from sqlalchemy.orm import Session
from app.models.core import User
from app.models.ra_soat_tien import KsCotTien, XEP_LOAI, QUYET_K2
from app.services import rules as R

# --- Dấu hiệu KHÔNG phải tiền. Xét TRƯỚC, vì nhiều cột chứa cả chữ tiền lẫn chữ tỷ lệ
#     (fee_weight có "fee", vat_rate có "vat") và trong những trường hợp đó thì phần đuôi mới đúng.
# "_suat" thêm 09/9/2026: thue_suat và lai_suat là TỶ LỆ, nhưng cả hai đều chứa chữ nằm trong danh
# sách "là tiền" ("thue", "lai") nên bị xếp nhầm thành tiền. Bắt ở ĐUÔI chứ không ở giữa: cột bắt đầu
# bằng "suat" (suat_an – tiền ăn ca) vẫn là tiền thật.
# Tìm ra khi đổi kiểu 48 cột: purchase_invoices.thue_suat lọt vào danh sách đổi, và nó là cột DUY NHẤT
# trong 48 cột chưa có người xem lại. Bốn cột rate_per_day có người xem thì xếp đúng.
DUOI_KHONG_TIEN = ("_pct", "_rate", "_ratio", "_days", "_hours", "_hour", "_score", "_weight",
                   "_qty", "_count", "_km", "_percent", "_suat")
CHUA_KHONG_TIEN = ("ty_le", "he_so", "phan_tram", "diem", "score", "coef", "weight", "percent")
DUNG_KHONG_TIEN = ("days", "lit", "qty", "so_luong", "work", "ot_hours", "so_lan", "so_ngay",
                   "so_gio", "so_khach", "pax", "annual_leave_days")

# --- Dấu hiệu LÀ tiền. Không có "rate": rate_per_day là đơn giá thuê xe theo ngày (tiền) còn
#     interest_rate là lãi suất (không phải tiền) – một chữ không đủ để phân biệt, nên để người quyết.
CHUA_TIEN = ("amount", "tien", "gia_ban", "gia_von", "don_gia", "price", "cost", "salary", "luong",
             "revenue", "doanh_thu", "chi_phi", "debit", "credit", "paid", "budget", "ngan_sach",
             "von", "principal", "phi", "fee", "vat", "thue", "tax", "allowance", "phu_cap",
             "bonus", "thuong", "deposit", "coc", "discount", "giam", "promo", "salvage",
             "outstanding", "balance", "total", "tong", "limit", "han_muc", "luy_ke",
             "accumulated", "allocated", "remaining", "opening", "actual", "can_tru",
             "dieu_chinh", "base", "charge", "da_thu", "no_", "cong_no")


def xep_theo_ten(cot: str) -> tuple[str, str]:
    """Đề xuất xếp loại một cột theo TÊN. Trả về (xếp loại, lý do đọc được)."""
    t = (cot or "").lower()
    if t in DUNG_KHONG_TIEN:
        return "khong_tien", f"tên cột đúng bằng “{t}” – là số đếm/đơn vị đo, không phải tiền"
    for d in DUOI_KHONG_TIEN:
        if t.endswith(d):
            return "khong_tien", f"tên kết thúc bằng “{d}” – là tỷ lệ/hệ số/số đếm"
    for c in CHUA_KHONG_TIEN:
        if c in t:
            return "khong_tien", f"tên chứa “{c}” – là tỷ lệ/điểm số/hệ số"
    for c in CHUA_TIEN:
        if c in t:
            return "tien", f"tên chứa “{c}”"
    return "chua_ro", "tên cột không nói rõ là tiền hay không – cần người quyết"


def _cot_so_thuc():
    """Mọi cột kiểu số thực trong toàn bộ mô hình dữ liệu, kèm ba dữ kiện K1/K2 cần.

    Đọc từ siêu dữ liệu SQLAlchemy chứ không đọc cơ sở dữ liệu: mô hình là thứ quyết định kiểu cột khi
    tạo bảng mới, nên sửa mô hình mới là sửa thật. Nạp app.main để chắc chắn mọi mô-đun mô hình đã vào
    siêu dữ liệu – thiếu một mô-đun là bộ kiểm báo thiếu cột và người đọc tưởng đã sửa xong.
    """
    import app.main  # noqa: F401
    from app.db.session import Base
    ra = []
    for t in Base.metadata.tables.values():
        for c in t.columns:
            if not isinstance(c.type, (Float, Numeric)): continue
            kieu = type(c.type).__name__
            mac_dinh_0 = False
            d = getattr(c, "default", None)
            if d is not None and getattr(d, "is_scalar", False):
                try: mac_dinh_0 = float(d.arg) == 0.0
                except Exception: mac_dinh_0 = False
            sd = getattr(c, "server_default", None)
            if sd is not None and getattr(sd, "arg", None) is not None:
                try: mac_dinh_0 = mac_dinh_0 or float(str(sd.arg).strip("'\" ")) == 0.0
                except Exception: pass
            ra.append({"bang": t.name, "cot": c.name, "kieu": kieu,
                       "cho_rong": bool(c.nullable), "mac_dinh_0": mac_dinh_0})
    return ra


def dong_bo(db: Session) -> dict:
    """Đối chiếu sổ rà soát với mô hình hiện tại. Không xóa dòng nào – cột biến mất thì tắt cờ `con`,
    vì quyết định của người về cột đó vẫn là dữ kiện lịch sử đáng giữ."""
    hien = {(x["bang"], x["cot"]): x for x in _cot_so_thuc()}
    cu = {(r.bang, r.cot): r for r in db.execute(select(KsCotTien)).scalars()}
    now = datetime.now(); them = doi_y = 0
    for k, x in hien.items():
        r = cu.get(k)
        if r is None:
            xep, ly_do = xep_theo_ten(x["cot"])
            db.add(KsCotTien(bang=x["bang"], cot=x["cot"], kieu=x["kieu"], xep_may=xep, ly_do_may=ly_do,
                             cho_rong=x["cho_rong"], mac_dinh_0=x["mac_dinh_0"],
                             lan_dau=now, lan_cuoi=now, con=True))
            them += 1
        else:
            # Kiểu và ràng buộc đọc lại mỗi lần: đó chính là thứ V9 sẽ sửa và K1 phải thấy giảm.
            r.kieu, r.cho_rong, r.mac_dinh_0 = x["kieu"], x["cho_rong"], x["mac_dinh_0"]
            r.lan_cuoi, r.con = now, True
            # XẾP LOẠI CỦA MÁY CŨNG TÍNH LẠI. Bản trước chỉ tính một lần, lúc dòng được ghi vào sổ –
            # nên vá bộ xếp loại xong thì mọi dòng đã ghi vẫn mang kết luận cũ, và bản vá coi như
            # không có tác dụng gì ngoài những cột thêm về sau.
            #
            # Tìm ra ngày 09/9/2026: sau khi thêm "_suat" vào danh sách "không phải tiền",
            # purchase_invoices.thue_suat VẪN hiện là tiền với lý do cũ "tên chứa thue".
            #
            # Quyết định của NGƯỜI không bị đụng tới – nó nằm ở quyet_nguoi và luôn thắng. Cái tính lại
            # ở đây là ĐỀ XUẤT của máy. Máy đổi ý trên một cột người đã quyết thì cũng đáng hiện ra:
            # đó là lúc nên hỏi lại người quyết, không phải lúc im lặng ghi đè.
            xep_moi, ly_do_moi = xep_theo_ten(x["cot"])
            if (r.xep_may, r.ly_do_may) != (xep_moi, ly_do_moi):
                r.xep_may, r.ly_do_may = xep_moi, ly_do_moi
                doi_y += 1
    mat = 0
    for k, r in cu.items():
        if k not in hien and r.con:
            r.con = False; mat += 1
    db.commit()
    return {"tong_cot": len(hien), "them_moi": them, "khong_con": mat,
            "may_doi_y": doi_y}


def _hieu_luc(db: Session) -> list[KsCotTien]:
    return [r for r in db.execute(select(KsCotTien).where(KsCotTien.con == True)).scalars()]  # noqa: E712


# ============================== K1 ==============================
def _cot_tien_float(db: Session) -> list[dict]:
    """Bộ kiểm K1. Còn một cột tiền kiểu Float là còn phát hiện – phát hiện này phải ĐỎ tới khi V9 xong."""
    dong_bo(db)
    rows = _hieu_luc(db)
    float_tien = sorted([r for r in rows if r.xep() == "tien" and r.kieu == "Float"],
                        key=lambda r: (r.bang, r.cot))
    chua_ro = sorted([r for r in rows if r.xep() == "chua_ro"], key=lambda r: (r.bang, r.cot))
    ra = []
    if float_tien:
        theo_bang: dict[str, list[str]] = {}
        for r in float_tien: theo_bang.setdefault(r.bang, []).append(r.cot)
        ra.append({"ma": "cot_tien_float#tong", "loai": "cot_tien_float", "muc": "do",
                   "phong_ban": "Công nghệ thông tin", "doi_tuong": "mo_hinh_du_lieu",
                   "tom_tat": f"{len(float_tien)} cột tiền trên {len(theo_bang)} bảng đang khai kiểu số "
                              f"thực nhị phân (Float). Cộng dồn nhiều dòng sẽ lệch, và lệch ở chỗ không "
                              f"ai nhìn – đây là chỗ kiểm toán đối chiếu đầu tiên.",
                   "chi_tiet": {"so_cot": len(float_tien), "so_bang": len(theo_bang),
                                "theo_bang": theo_bang}})
    if chua_ro:
        ra.append({"ma": "cot_tien_chua_ro#tong", "loai": "cot_tien_float", "muc": "vang",
                   "phong_ban": "Kế toán", "doi_tuong": "mo_hinh_du_lieu",
                   "tom_tat": f"{len(chua_ro)} cột chưa xác định được là tiền hay không, chỉ nhìn tên cột "
                              f"thì không đủ. Cần người quyết trước khi V9 đổi kiểu – đổi nhầm một cột "
                              f"không phải tiền cũng tốn đúng một lần nâng cấp cơ sở dữ liệu.",
                   "chi_tiet": {"so_cot": len(chua_ro),
                                "cot": [f"{r.bang}.{r.cot}" for r in chua_ro]}})
    return ra


# ============================== K2 ==============================
def _thieu_khac_khong(db: Session) -> list[dict]:
    """Bộ kiểm K2. Cột tiền vừa mặc định 0 vừa KHÔNG cho rỗng thì "chưa có số" bị ghi thành 0."""
    dong_bo(db)
    rows = _hieu_luc(db)
    xau = sorted([r for r in rows if r.xep() == "tien" and r.mac_dinh_0 and not r.cho_rong
                  and r.quyet_k2 != "giu"], key=lambda r: (r.bang, r.cot))
    if not xau: return []
    chua_quyet = [r for r in xau if not r.quyet_k2]
    theo_bang: dict[str, list[str]] = {}
    for r in xau: theo_bang.setdefault(r.bang, []).append(r.cot)
    return [{"ma": "thieu_khac_0#tong", "loai": "thieu_khac_0", "muc": "do",
             "phong_ban": "Công nghệ thông tin", "doi_tuong": "mo_hinh_du_lieu",
             "tom_tat": f"{len(xau)} cột tiền đang mặc định 0 và không cho phép rỗng – ở những cột này "
                        f"“chưa có số” và “bằng 0” là một, không phân biệt được. "
                        f"{len(chua_quyet)} cột chưa ai quyết là sửa hay giữ.",
             "chi_tiet": {"so_cot": len(xau), "chua_quyet": len(chua_quyet), "theo_bang": theo_bang}}]


# ============================== BÀN LÀM VIỆC CỦA NGƯỜI ==============================
def bang(db: Session, loc: str = "") -> dict:
    dong_bo(db)
    rows = sorted(_hieu_luc(db), key=lambda r: (r.bang, r.cot))
    def ra1(r: KsCotTien) -> dict:
        return {"id": r.id, "bang": r.bang, "cot": r.cot, "kieu": r.kieu,
                "xep_may": r.xep_may, "xep_may_ten": XEP_LOAI.get(r.xep_may, r.xep_may),
                "ly_do_may": r.ly_do_may, "quyet_nguoi": r.quyet_nguoi,
                "xep": r.xep(), "xep_ten": XEP_LOAI.get(r.xep(), r.xep()),
                "quyet_boi": r.quyet_boi, "quyet_luc": r.quyet_luc, "ghi_chu": r.ghi_chu,
                "cho_rong": r.cho_rong, "mac_dinh_0": r.mac_dinh_0,
                # Cột người đã quyết GIỮ (kèm lý do) không còn nằm trong danh sách phải sửa. Con số
                # người đọc trên màn hình và con số robot báo lên Chủ tịch phải là MỘT – lệch nhau thì
                # bảng nào cũng mất giá trị.
                "thieu_thanh_0": bool(r.xep() == "tien" and r.mac_dinh_0 and not r.cho_rong
                                      and r.quyet_k2 != "giu"),
                "da_quyet_giu": r.quyet_k2 == "giu",
                "quyet_k2": r.quyet_k2, "quyet_k2_ten": QUYET_K2.get(r.quyet_k2, r.quyet_k2),
                "can_doi_kieu": bool(r.xep() == "tien" and r.kieu == "Float")}
    ds = [ra1(r) for r in rows]
    if loc == "tien": ds = [x for x in ds if x["xep"] == "tien"]
    elif loc == "chua_ro": ds = [x for x in ds if x["xep"] == "chua_ro"]
    elif loc == "thieu_thanh_0": ds = [x for x in ds if x["thieu_thanh_0"]]
    elif loc == "can_doi_kieu": ds = [x for x in ds if x["can_doi_kieu"]]
    tong = [ra1(r) for r in rows]
    return {"rows": ds,
            "tong_cot": len(tong),
            "so_tien": sum(1 for x in tong if x["xep"] == "tien"),
            "so_khong_tien": sum(1 for x in tong if x["xep"] == "khong_tien"),
            "so_chua_ro": sum(1 for x in tong if x["xep"] == "chua_ro"),
            "so_float_tien": sum(1 for x in tong if x["can_doi_kieu"]),
            "so_thieu_thanh_0": sum(1 for x in tong if x["thieu_thanh_0"]),
            "so_giu_co_ly_do": sum(1 for x in tong if x["da_quyet_giu"]),
            # Quyết "sửa" KHÔNG làm cột biến mất khỏi danh sách: nó vẫn đang hỏng cho tới khi mô hình
            # đổi thật. Con số đo tiến độ của người là "chưa ai quyết", con số đo tiến độ sửa là
            # "so_thieu_thanh_0" ở trên – hai việc khác nhau, đừng gộp.
            "so_k2_chua_quyet": sum(1 for x, r in zip(tong, rows) if x["thieu_thanh_0"] and not r.quyet_k2),
            "so_nguoi_da_quyet": sum(1 for r in rows if r.quyet_nguoi)}


def quyet(db: Session, u: User, ds: list[dict]) -> dict:
    """Người xác nhận xếp loại (K1) và/hoặc quyết sửa–giữ (K2). Robot không gọi hàm này."""
    n1 = n2 = 0
    for x in ds:
        r = db.get(KsCotTien, int(x["id"])) if x.get("id") else None
        if r is None: raise ValueError(f"Không có dòng rà soát id={x.get('id')}")
        xep = (x.get("quyet_nguoi") or "").strip()
        if xep:
            if xep not in ("tien", "khong_tien"):
                raise ValueError("Xếp loại chỉ nhận 'tien' hoặc 'khong_tien' – 'chưa rõ' là trạng thái "
                                 "chờ, không phải một quyết định")
            r.quyet_nguoi, r.quyet_boi, r.quyet_luc = xep, u.username, datetime.now()
            n1 += 1
        k2 = (x.get("quyet_k2") or "").strip()
        if k2:
            if k2 not in ("sua", "giu"): raise ValueError("Quyết định K2 chỉ nhận 'sua' hoặc 'giu'")
            if k2 == "giu" and not (x.get("ghi_chu") or r.ghi_chu or "").strip():
                raise ValueError(f"Giữ nguyên {r.bang}.{r.cot} thì phải ghi vì sao 0 ở cột này là số "
                                 f"thật – không có lý do thì lần rà sau không ai biết đã cân nhắc chưa")
            r.quyet_k2, r.quyet_k2_boi, r.quyet_k2_luc = k2, u.username, datetime.now()
            n2 += 1
        if x.get("ghi_chu") is not None: r.ghi_chu = str(x["ghi_chu"])[:2000]
    R.audit(db, u.username, u.role, "quyet_cot_tien", "ks_cot_tien",
            after={"so_xep_loai": n1, "so_quyet_k2": n2})
    db.commit()
    return {"da_xep_loai": n1, "da_quyet_k2": n2}


# ============================== QUYẾT ĐỊNH ĐÃ CÓ NGƯỜI KÝ ==============================
# Chủ tịch quyết ngày 08/9/2026, ghi vào mã để lần triển khai nào cũng có mặt – KHÔNG phải để robot
# tự quyết. Danh sách viết THẲNG RA từng cột chứ không viết thành quy tắc: quy tắc thì mọi cột thêm
# về sau cũng bị quyết hộ, mà cột mới thì chưa ai xem.
#
# Tám cột dưới đây trước đó robot xếp "chưa rõ" vì chỉ nhìn tên thì không phân biệt được lãi suất với
# đơn giá. Đọc trong mô hình mới rõ, và lý do đọc được ghi ngay cạnh để sau này còn đối chất.
QUYET_08_09_2026 = {
    "guide_assignments.rate_per_day":
        "Đơn giá thù lao HDV theo ngày – lệnh phân công ghi rõ “thù lao = đơn giá tuyến × ngày”",
    "guide_rates.rate_per_day": "Đơn giá HDV theo ngày trong bảng giá tuyến, có hai chữ ký duyệt",
    "guide_rates.old_rate_per_day": "Đơn giá cũ giữ lại để đối chiếu khi đổi bảng giá",
    "vehicles.internal_rate_per_day": "Đơn giá xe nội bộ theo ngày, dùng khi tuyến không có trong bảng giá",
    "fleet_repayment_plans.moi_ky": "Số tiền phải trả mỗi kỳ – bằng gốc chia số kỳ",
    "fleet_settlements.doi_tac_huong": "Phần doanh thu đối tác được hưởng trong kỳ quyết toán",
    "fleet_settlements.doi_tac_chiu": "Phần chi phí đối tác chịu trong kỳ quyết toán",
    "fleet_settlements.chuyen_ky_sau": "Số tiền còn lại chuyển sang kỳ sau",
}

# Chủ tịch quyết SỬA cho toàn bộ cột tiền đang mặc định 0 mà không cho rỗng, tính tại ngày 08/9/2026.
# "Sửa" là hướng an toàn: cho phép để trống thì "chưa có số" nói được ra, chứ không mất số nào. Cột
# nào cần GIỮ thì phải quay lại ghi lý do – chiều ngược lại mới là chiều phải giải trình.
QUYET_K2_SUA_08_09_2026 = (
    "asset_depreciations.accumulated", "asset_depreciations.amount", "asset_depreciations.remaining",
    "bank_accounts_cat.opening_balance", "bank_doc_map.amount", "bookings.amount",
    "bookings.cancel_charge", "bookings.cost_amount", "bookings.discount",
    "bookings.paid", "campaigns.budget", "dispatch_orders.internal_price",
    "employees.advance_limit", "employees.base_salary", "employees.bhxh_base",
    "fin_contracts.outstanding", "fin_contracts.principal", "fixed_assets.cost",
    "fixed_assets.opening_accumulated", "fixed_assets.salvage", "fleet_debt_payments.so_tien",
    "fleet_external_txns.so_tien", "fleet_maintenance.so_tien", "fleet_offset_applications.amount",
    "fleet_period_costs.so_tien", "fleet_repayment_installments.amount_applied",
    "fleet_repayment_installments.amount_due",
    "fleet_repayment_plans.moi_ky", "fleet_repayment_plans.principal", "fleet_sale_cases.da_thu",
    "fleet_sale_cases.gia_ban", "fleet_settlement_lines.amount", "fleet_settlements.can_tru",
    "fleet_settlements.chuyen_ky_sau", "fleet_settlements.dieu_chinh", "fleet_settlements.doanh_thu",
    "fleet_settlements.doi_tac_chiu", "fleet_settlements.doi_tac_huong", "fleet_settlements.sau_can_tru",
    "fleet_settlements.truoc_can_tru", "fleet_shared_invoice_lines.amount",
    "fleet_shared_invoices.tong_tien",
    "fleet_shared_invoices.vat", "fleet_trip_costs.amount", "fleet_trips.doanh_thu",
    "guide_assignments.rate_per_day", "guide_rates.old_rate_per_day", "guide_rates.rate_per_day",
    "invoices.pre_tax", "invoices.total", "invoices.vat",
    "journal_lines.credit", "journal_lines.debit", "labor_contracts.allowance",
    "labor_contracts.salary", "labor_contracts.si_salary", "lead_channel_stats.cost",
    "mkt_budget_lines.amount", "mkt_budgets.target_revenue", "prepaid_allocations.allocated",
    "prepaid_allocations.amount", "prepaid_allocations.remaining", "prepaid_expenses.amount",
    "prepaid_expenses.opening_allocated", "products.reference_price", "retentions.amount",
    "retentions.remaining", "service_orders.don_gia", "service_orders.thanh_tien",
    "service_requests.discount", "thieu_gia_von.doanh_thu", "thieu_gia_von.gia_von",
    "tour_cost_lines.actual", "tour_cost_lines.budget", "tour_cost_lines.paid",
    "tour_cost_lines.unit_price", "tours.actual_cost", "tours.actual_revenue",
    "tours.fixed_cost", "tours.price_chd", "tours.price_inf",
    "tours.price_per_pax", "tours.price_promo", "tours.promo_value",
    "tours.var_cost_per_pax", "vehicle_rates.internal_price", "vehicle_rates.partner_price",
    "vehicles.internal_rate_per_day", "visa_files.revenue", "vt_records.amount",
)


def nap_quyet_dinh(db: Session) -> dict:
    """Ghi các quyết định đã có người ký vào sổ rà soát. Chỉ điền ô CÒN TRỐNG.

    Gọi lúc khởi động, sau khi đồng bộ. Không bao giờ đè lên quyết định người khác ghi sau đó – một
    hàm nạp mặc định mà ghi đè quyết định của người là hàm xoá dấu vết.
    """
    dong_bo(db)
    rows = {(r.bang, r.cot): r for r in db.execute(select(KsCotTien)).scalars()}
    n1 = n2 = 0
    for ten, ly_do in QUYET_08_09_2026.items():
        bang, cot = ten.split(".", 1)
        r = rows.get((bang, cot))
        if r is None or r.quyet_nguoi: continue
        r.quyet_nguoi, r.quyet_boi = "tien", "chutich"
        r.quyet_luc = r.quyet_luc or datetime(2026, 9, 8)
        r.ghi_chu = r.ghi_chu or ly_do
        n1 += 1
    for ten in QUYET_K2_SUA_08_09_2026:
        bang, cot = ten.split(".", 1)
        r = rows.get((bang, cot))
        if r is None or r.quyet_k2: continue
        r.quyet_k2, r.quyet_k2_boi = "sua", "chutich"
        r.quyet_k2_luc = r.quyet_k2_luc or datetime(2026, 9, 8)
        n2 += 1
    if n1 or n2: db.commit()
    return {"xep_loai": n1, "quyet_k2": n2}


# ============================== ĐẾM PHẦN LẺ TRƯỚC KHI ĐỔI KIỂU ==============================
#
# Cửa sổ đo này chỉ mở MỘT LẦN. numeric(18,2) giữ đúng hai chữ số thập phân; giá trị đang có chữ số
# thứ ba trở đi sẽ bị LÀM TRÒN lúc đổi kiểu, và đó là thay đổi không quay lại được – hạ cấp khôi phục
# KIỂU, không khôi phục SỐ. Đếm sau khi đã đổi thì luôn ra 0, vì cột mới không giữ nổi chữ số thứ ba,
# nên nó không chứng minh được gì.
#
# Truy vấn tự tìm MỌI cột số thực nhị phân trong cơ sở dữ liệu chứ không đọc từ danh sách chép tay:
# danh sách chép tay thì cột thêm sau sẽ lọt. Nội dung SQL lấy từ
# docs/VTOS_V9_dot3_dem_phan_le_truoc_khi_doi_kieu.sql (làn V9 soạn 09/9/2026).
#
# CHỈ ĐỌC. Chạy được lúc hệ thống đang phục vụ.

SQL_PHAN_LE = """
SELECT c.table_name || '.' || c.column_name AS cot,
       (xpath('/row/c/text()', query_to_xml(
          format('SELECT COUNT(*) AS c FROM public.%I WHERE %I IS NOT NULL AND %I*100 <> ROUND(%I::numeric*100)',
                 c.table_name, c.column_name, c.column_name, c.column_name),
          false, true, '')))[1]::text::bigint AS so_dong_co_le
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema
 AND t.table_name  = c.table_name
 AND t.table_type  = 'BASE TABLE'
WHERE c.table_schema = 'public'
  AND c.data_type IN ('double precision', 'real')
ORDER BY 2 DESC, 1
"""


def dem_phan_le(db: Session) -> dict:
    """Bao nhiêu dòng sẽ bị LÀM TRÒN nếu đổi cột số thực nhị phân sang numeric(18,2)?

    Ra 0 ở mọi cột nghĩa là đổi kiểu là phép biến đổi không mất gì – lúc đó mới nên đổi. Khác 0 thì
    phải xem từng cột và quyết TRƯỚC, không đổi rồi mới xem.
    """
    from sqlalchemy import text
    if db.bind.dialect.name != "postgresql":
        return {"chay_duoc": False,
                "vi_sao": "Phép đo này chỉ chạy trên PostgreSQL. Máy lập trình dùng SQLite – nơi kiểu "
                          "cột không được ép, nên đo ở đó không nói gì về máy chủ thật.",
                "cot": [], "tong_dong_se_lam_tron": None}
    hang = db.execute(text(SQL_PHAN_LE)).all()
    cot = [{"cot": r[0], "so_dong_co_le": int(r[1] or 0)} for r in hang]
    return {"chay_duoc": True,
            "so_cot_so_thuc": len(cot),
            "cot_co_phan_le": [c for c in cot if c["so_dong_co_le"] > 0],
            "tong_dong_se_lam_tron": sum(c["so_dong_co_le"] for c in cot),
            "ket_luan": ("Không dòng nào mất số khi đổi kiểu."
                         if not any(c["so_dong_co_le"] for c in cot) else
                         "CÓ dòng sẽ bị làm tròn – phải quyết từng cột TRƯỚC khi đổi."),
            "cot": cot}


# ============================== K2: ĐẾM SỐ 0 TRƯỚC KHI QUYẾT ==============================
#
# K2 nói: cột tiền vừa mặc định 0 vừa không cho rỗng thì "chưa có số" và "bằng 0" là một. Nhưng
# "không phân biệt được" là một câu ĐỊNH TÍNH – nó không nói cho người quyết biết chuyện này lớn cỡ nào
# ở từng cột. Một cột có 0/1000 dòng bằng 0 thì gần như không có gì để lo; một cột có 900/1000 dòng
# bằng 0 thì gần như toàn bộ cột ấy là dấu hỏi.
#
# Con số ấy phải có TRƯỚC khi quyết, vì việc quyết là quyết từng cột:
#   · "sửa"  – cho phép rỗng, và đây là chỗ phải cẩn thận: sau khi cho rỗng thì số 0 ĐANG CÓ vẫn là 0,
#              không tự thành rỗng. Đổi kiểu không tách được hai nghĩa đã trộn vào nhau; nó chỉ ngăn
#              chuyện trộn TIẾP TỤC xảy ra.
#   · "giữ"  – kèm lý do, cho những cột mà 0 đúng là 0 (ví dụ: giảm giá, phụ cấp – không có thì bằng 0).
#
# CHỈ ĐỌC, chạy được lúc hệ thống đang phục vụ. Một truy vấn duy nhất cho toàn bộ danh sách: hỏi 91 câu
# riêng lẻ trên máy chủ 0,5 CPU là tự làm nghẽn chính mình.

SQL_DEM_0 = """
SELECT c.table_name || '.' || c.column_name AS cot,
       (xpath('/row/c/text()', query_to_xml(
          format('SELECT COUNT(*) AS c FROM public.%I', c.table_name),
          false, true, '')))[1]::text::bigint AS tong_dong,
       (xpath('/row/c/text()', query_to_xml(
          format('SELECT COUNT(*) AS c FROM public.%I WHERE %I = 0', c.table_name, c.column_name),
          false, true, '')))[1]::text::bigint AS so_dong_bang_0
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema
 AND t.table_name  = c.table_name
 AND t.table_type  = 'BASE TABLE'
WHERE c.table_schema = 'public'
  AND c.table_name || '.' || c.column_name = ANY(:ds)
"""


def dem_so_0(db: Session) -> dict:
    """Mỗi cột tiền đang có bao nhiêu dòng mang số 0?

    Trước khi K2 xong: đếm trên những cột CÒN CHỜ QUYẾT, để người quyết chọn "sửa" hay "giữ" cho TỪNG
    cột thay vì quyết cả 91 cột bằng một cảm giác chung.

    Sau khi K2 xong (danh sách chờ rỗng): đếm trên MỌI cột tiền đã cho phép rỗng, vì lúc đó câu hỏi
    đã đổi – không còn là "cột nào cần sửa" mà là "còn bao nhiêu dòng CŨ mang số 0 mà không ai biết
    đó là 'bằng 0' hay 'chưa nhập'". Trả về `xong_k2` để màn hình gọi đúng tên con số nó đang xem.
    """
    from sqlalchemy import text
    dong_bo(db)
    xau = sorted([r for r in _hieu_luc(db)
                  if r.xep() == "tien" and r.mac_dinh_0 and not r.cho_rong and r.quyet_k2 != "giu"],
                 key=lambda r: (r.bang, r.cot))

    # Ngày 09/9/2026 K2 sửa xong cả 91 cột, và danh sách chờ trên về rỗng. Lúc ấy hàm này trả
    # "0 cột · 0 dòng bằng 0" – đọc lên nghe như "dữ liệu đã sạch", trong khi nó chỉ có nghĩa "không
    # còn cột nào trong diện chờ quyết". Hai câu đó khác nhau rất xa, và bảng đang nói câu dễ hiểu
    # lầm hơn: số 0 CŨ vẫn nằm nguyên trong cơ sở dữ liệu.
    #
    # Bản nâng cấp K2 cố ý không đụng một dòng dữ liệu nào – nó chỉ ngăn chuyện trộn TIẾP TỤC xảy ra.
    # Nên sau K2, con số đáng hỏi đã đổi: không còn là "cột nào cần quyết" mà là "bao nhiêu dòng CŨ
    # đang mang số 0 mà không ai còn biết đó là 'bằng 0' hay 'chưa nhập'". Đó là phần K2 không chữa
    # được, và là việc của người – không phải việc của một bản nâng cấp.
    xong_k2 = not xau
    if xong_k2:
        xau = sorted([r for r in _hieu_luc(db) if r.xep() == "tien" and r.cho_rong],
                     key=lambda r: (r.bang, r.cot))
    ten = [f"{r.bang}.{r.cot}" for r in xau]
    quyet = {f"{r.bang}.{r.cot}": (r.quyet_k2 or "") for r in xau}
    if db.bind.dialect.name != "postgresql":
        return {"chay_duoc": False,
                "vi_sao": "Chỉ chạy trên PostgreSQL – máy lập trình dùng SQLite, dữ liệu ở đó là dữ "
                          "liệu nạp mẫu nên đếm ra con số không nói gì về hệ thống thật.",
                "so_cot": len(ten), "xong_k2": xong_k2, "cot": []}
    hang = db.execute(text(SQL_DEM_0), {"ds": ten}).all()
    ra = []
    for c, tong, so0 in hang:
        tong, so0 = int(tong or 0), int(so0 or 0)
        ra.append({"cot": c, "tong_dong": tong, "so_dong_bang_0": so0,
                   "ty_le_0": round(so0 / tong * 100, 1) if tong else None,
                   "quyet_k2": quyet.get(c, "")})
    ra.sort(key=lambda x: (-(x["ty_le_0"] or 0), -x["so_dong_bang_0"]))
    co_du_lieu = [x for x in ra if x["tong_dong"] > 0]
    return {"chay_duoc": True, "so_cot": len(ra),
            "so_cot_bang_trong": len(ra) - len(co_du_lieu),
            "so_cot_toan_bo_bang_0": len([x for x in co_du_lieu if x["ty_le_0"] == 100.0]),
            "tong_dong_bang_0": sum(x["so_dong_bang_0"] for x in ra),
            "xong_k2": xong_k2,
            "dang_dem": ("so 0 CU con lai" if xong_k2 else "cot cho quyet"),
            "tieu_de": ("Số 0 CŨ còn lại – nhập trước ngày K2, không còn biết là 'bằng 0' hay 'chưa nhập'"
                        if xong_k2 else "Cột tiền còn chờ quyết sửa hay giữ"),
            "ghi_chu": ("Mọi cột tiền đã cho phép rỗng – từ nay ô để trống lưu thành RỖNG. Nhưng bản "
                        "nâng cấp cố ý không đụng dữ liệu cũ, nên những số 0 dưới đây vẫn còn nguyên và "
                        "vẫn mang hai nghĩa lẫn nhau. Không có phép nào tách chúng ra được: chỉ người "
                        "biết việc mới nói được dòng nào là 'đúng bằng 0', dòng nào là 'chưa ai nhập'."
                        if xong_k2 else
                        "Bảng đang trống thì chưa có gì để lo – nhưng cột vẫn cần quyết trước khi có dữ "
                        "liệu, vì sau đó thì số 0 đã trộn vào rồi."),
            "cot": ra}
