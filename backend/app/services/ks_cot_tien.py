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
DUOI_KHONG_TIEN = ("_pct", "_rate", "_ratio", "_days", "_hours", "_hour", "_score", "_weight",
                   "_qty", "_count", "_km", "_percent")
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
    now = datetime.now(); them = 0
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
    mat = 0
    for k, r in cu.items():
        if k not in hien and r.con:
            r.con = False; mat += 1
    db.commit()
    return {"tong_cot": len(hien), "them_moi": them, "khong_con": mat}


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
