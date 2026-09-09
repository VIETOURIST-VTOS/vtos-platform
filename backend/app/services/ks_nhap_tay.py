"""K3 – HẬU KIỂM SỐ NHÂN VIÊN NHẬP TAY.

Đây là việc quan trọng nhất phát sinh từ quyết định "nhập là dùng luôn" (Chủ tịch, 08/9/2026). Bỏ khâu
trưởng phòng duyệt từng dòng là bỏ một lớp chặn CÓ THẬT. Đổi lại, lớp còn lại phải chặt hơn chứ không
lỏng hơn – và lớp còn lại chính là tệp này: mỗi ngày rà toàn bộ số nhân viên vừa nhập, tìm ra cái bất
thường TRƯỚC khi nó thành báo cáo tháng.

Sáu dấu hiệu, mỗi dấu hiệu một loại riêng để người xử lý biết phải đi hỏi ai:
  1. lech_ky      – lệch bất thường so với chính chỉ tiêu đó kỳ trước
  2. so_tron      – số tròn trịa đáng ngờ ở khoản lớn, lặp lại nhiều dòng
  3. ngoai_gio    – nhập ngoài giờ làm việc, hoặc nhập dồn nhiều dòng trong vài phút
  4. khac_phong   – một người nhập số cho phòng khác
  5. lui_ngay     – nhập lùi ngày vào kỳ đã khóa hoặc sắp khóa
  6. sua_da_chot  – sửa lại một số đã dùng để lên báo cáo

MỌI NGƯỠNG NẰM Ở THAM SỐ CHÍNH SÁCH, không viết cứng. Lý do không phải là nguyên tắc suông: đặt chặt
quá thì mỗi ngày hàng trăm dòng và không ai đọc, lỏng quá thì bỏ lọt. Con số đúng chỉ tìm được bằng
cách chạy thử trên dữ liệu thật – nên tệp này có sẵn hàm đo (`do_nguong`) để trình người quyết một
bảng "ngưỡng này ra bao nhiêu dòng" thay vì bắt họ đoán.

Tệp này KHÔNG sửa một con số nghiệp vụ nào. Nó chỉ đọc và mở việc.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.services import rules as R

# Sổ có số tiền do người nhập. `phong` để trống nghĩa là nguồn này ai nhập cũng hợp lệ – dấu hiệu
# "nhập cho phòng khác" bỏ qua nguồn đó thay vì báo oan.
NGUON = (
    {"ma": "chi", "ten": "Đề nghị chi", "bang": "payment_requests", "tien": "amount",
     "nguoi": "created_by", "luc": "created_at", "ngay": "", "phong": ""},
    {"ma": "thu", "ten": "Phiếu thu", "bang": "receipts", "tien": "amount",
     "nguoi": "created_by", "luc": "created_at", "ngay": "", "phong": "Kế toán"},
    # `may_sinh`: (tên cột, giá trị nghĩa là NGƯỜI GÕ). Cột này là thứ phân biệt máy nạp với người gõ
    # duy nhất đáng tin – xem ghi chú ở _chi_nguoi_go. Nguồn không khai thì không lọc.
    {"ma": "but_toan", "ten": "Bút toán", "bang": "journal_entries", "tien": "",
     "nguoi": "created_by", "luc": "created_at", "ngay": "entry_date", "phong": "Kế toán",
     "may_sinh": ("source_type", "thu_cong")},
    # Sổ chi phí chuyến xe gọi cột đó là `nguon` và giá trị người-gõ là "nhap_tay" (máy: bao_cao_vietrip
    # / the_dau / epass / ocr). Khác tên, khác giá trị, cùng một ý – nên khai theo từng nguồn.
    {"ma": "chi_phi_chuyen", "ten": "Chi phí chuyến xe", "bang": "fleet_trip_costs", "tien": "amount",
     "nguoi": "created_by", "luc": "created_at", "ngay": "", "phong": "Đội xe",
     "may_sinh": ("nguon", "nhap_tay")},
    {"ma": "bao_duong", "ten": "Bảo dưỡng xe", "bang": "fleet_maintenance", "tien": "so_tien",
     "nguoi": "created_by", "luc": "created_at", "ngay": "ngay", "phong": "Đội xe"},
    {"ma": "hoa_don", "ten": "Hóa đơn", "bang": "invoices", "tien": "total",
     "nguoi": "created_by", "luc": "created_at", "ngay": "", "phong": "Kế toán"},
)
# Tài khoản máy: robot nạp dữ liệu và các bộ đồng bộ. Không phải "người nhập", nên loại khỏi hậu kiểm –
# để lại thì mọi dấu hiệu đều chỉ vào chúng và phần của con người chìm nghỉm.
BO_QUA_NGUOI = ("robot", "", "system", "vietrip", "sepay", "dieuhanhvietrip")


def _chi_nguoi_go(t, ng: dict):
    """Điều kiện SQL giữ lại đúng những dòng do NGƯỜI gõ. Trả None nếu nguồn không có cột phân biệt.

    Vì sao không lọc bằng tên tài khoản: bản đầu tiên chỉ có BO_QUA_NGUOI, một danh sách tên. Đo trên
    máy chủ thật ngày 08/9/2026 thì tháng 9 có 25.728 "dòng nhập tay" – trong khi số người thật gõ vào
    sổ bút toán tháng đó đếm trên đầu ngón tay. Toàn bộ phần còn lại là bản nạp MISA, chạy dưới tên
    `misa`, một cái tên không có trong danh sách.

    Danh sách tên luôn thiếu, vì mỗi lần nối thêm một hệ thống là thêm một cái tên phải nhớ bổ sung –
    và không ai nhớ. Cột `source_type` thì ngược lại: nó do CHÍNH chỗ ghi sổ đặt, nên một nguồn máy mới
    tự khai mình là máy mà không cần ai sửa tệp này.

    Cùng ngày, cùng cách đo, sổ chi phí chuyến xe cho ra 87 dòng "nhập tay" – toàn bộ đều mang
    nguon="bao_cao_vietrip", tức bản nạp từ báo cáo VieTrip. Hai sổ, hai cái tên cột khác nhau, cùng một
    kiểu nhầm.

    Hậu quả của việc lọc sai không phải là báo thừa vài dòng. Hai mươi lăm nghìn dòng máy nạp đội lốt
    số nhập tay thì mọi ngưỡng hiệu chỉnh trên đó đều hiệu chỉnh cho một hệ thống không tồn tại, và
    người đọc bảng ngoại lệ chỉ thấy tên `misa` lặp lại – đọc vài lần rồi thôi đọc. Bộ kiểm soát chết
    vì bị phớt lờ, không phải vì hỏng.

    Dòng để trống cột này thì VẪN ĐEM RA HẬU KIỂM. Trong một bộ kiểm soát, im lặng phải do có bằng
    chứng là máy sinh, chứ không do thiếu dữ liệu.
    """
    khai = ng.get("may_sinh")
    if not khai: return None
    cot, nguoi_go = khai
    if cot not in t.c: return None
    return func.coalesce(t.c[cot], nguoi_go) == nguoi_go


def _bang(ten: str):
    from app.db.session import Base
    import app.main  # noqa: F401 – nạp đủ mọi mô-đun mô hình
    return Base.metadata.tables.get(ten)


TRAN_DONG = 50_000       # trần an toàn cho một nguồn trong một tháng


def _doc(db: Session, ng: dict, tu: datetime, den: datetime, kho: dict | None = None) -> list[dict]:
    """Đọc các dòng của một nguồn trong khoảng thời gian NHẬP (không phải ngày chứng từ).

    `kho` là bộ đệm dùng chung trong MỘT lần quét. Bản đầu tiên không có nó và mỗi dấu hiệu tự đọc lại
    bảng của mình – sáu dấu hiệu × sáu nguồn thành ba mươi sáu lần quét bảng, và trên dữ liệu thật thì
    cổng trả 502 trước khi hàm kịp chạy xong. Đọc một lần, dùng chung.
    """
    if kho is not None:
        k = (ng["ma"], tu, den)
        if k in kho: return kho[k]
    t = _bang(ng["bang"])
    if t is None or ng["nguoi"] not in t.c or ng["luc"] not in t.c: return []
    cols = [t.c.id, t.c[ng["nguoi"]].label("nguoi"), t.c[ng["luc"]].label("luc")]
    cols.append((t.c[ng["tien"]] if ng["tien"] and ng["tien"] in t.c else func.cast(0, t.c.id.type)).label("tien"))
    cols.append((t.c[ng["ngay"]] if ng["ngay"] and ng["ngay"] in t.c else t.c[ng["luc"]]).label("ngay"))
    # Lọc tài khoản máy NGAY TRONG SQL, không đọc về rồi bỏ: trên hệ thống thật phần lớn dòng là do
    # robot nạp, đọc hết về Python rồi vứt đi là trả giá cho đúng phần không dùng.
    dk = [t.c[ng["luc"]] >= tu, t.c[ng["luc"]] < den,
          func.lower(func.coalesce(t.c[ng["nguoi"]], "")).notin_(BO_QUA_NGUOI)]
    loc_may = _chi_nguoi_go(t, ng)
    if loc_may is not None: dk.append(loc_may)
    q = select(*cols).where(*dk).limit(TRAN_DONG + 1)
    ra = [{"id": r.id, "nguoi": r.nguoi, "luc": r.luc, "tien": float(r.tien or 0), "ngay": r.ngay}
          for r in db.execute(q).all()]
    if kho is not None: kho[(ng["ma"], tu, den)] = ra
    return ra


def _tong_tien(db: Session, ng: dict, tu: datetime, den: datetime) -> float:
    """Tổng tiền của một nguồn trong khoảng – cộng bằng SQL, không nạp dòng nào về bộ nhớ."""
    t = _bang(ng["bang"])
    if t is None or not ng["tien"] or ng["tien"] not in t.c or ng["luc"] not in t.c: return 0.0
    dk = [t.c[ng["luc"]] >= tu, t.c[ng["luc"]] < den,
          func.lower(func.coalesce(t.c[ng["nguoi"]], "")).notin_(BO_QUA_NGUOI)]
    loc_may = _chi_nguoi_go(t, ng)
    if loc_may is not None: dk.append(loc_may)
    return float(db.execute(select(func.coalesce(func.sum(t.c[ng["tien"]]), 0.0)).where(*dk)).scalar() or 0)


def thong_ke_nguoi(db: Session, ng: dict, tu: datetime, den: datetime, toi_da: int = 12) -> list[dict]:
    """Ai nhập, bao nhiêu dòng, từ lúc nào tới lúc nào – ĐẾM BẰNG SQL, không nạp dòng nào về bộ nhớ.

    Vì sao cần: con số "25.728 dòng người nhập trong tháng 9" tự nó không nói được điều gì. Hai mươi lăm
    nghìn dòng có thể là cả phòng Kế toán gõ suốt tháng, cũng có thể là MỘT tài khoản đổ một bản nhập
    hàng loạt trong mười phút và bị gán nhầm là số nhập tay. Hai chuyện đó dẫn tới hai kết luận trái
    ngược nhau về hậu kiểm, nên phải phân biệt được TRƯỚC khi đặt ngưỡng – đặt ngưỡng trên dữ liệu chưa
    hiểu là đặt ngưỡng cho một hệ thống khác.

    Khoảng cách giữa `nhanh_nhat` và `cham_nhat` là chỗ đọc ra câu trả lời: vài phút cho hàng nghìn dòng
    thì đó là máy đổ vào, không phải người gõ.
    """
    t = _bang(ng["bang"])
    if t is None or ng["nguoi"] not in t.c or ng["luc"] not in t.c: return []
    n = t.c[ng["nguoi"]]; l = t.c[ng["luc"]]
    tien = t.c[ng["tien"]] if ng["tien"] and ng["tien"] in t.c else None
    cot = [n.label("nguoi"), func.count().label("so_dong"),
           func.min(l).label("dau"), func.max(l).label("cuoi")]
    if tien is not None: cot.append(func.coalesce(func.sum(tien), 0).label("tong"))
    dk = [l >= tu, l < den, func.lower(func.coalesce(n, "")).notin_(BO_QUA_NGUOI)]
    loc_may = _chi_nguoi_go(t, ng)
    if loc_may is not None: dk.append(loc_may)
    q = select(*cot).where(*dk).group_by(n).order_by(func.count().desc()).limit(toi_da)
    ra = []
    for r in db.execute(q).all():
        dau, cuoi = r.dau, r.cuoi
        phut = round((cuoi - dau).total_seconds() / 60, 1) if isinstance(dau, datetime) and isinstance(cuoi, datetime) else None
        ra.append({"nguoi": r.nguoi, "so_dong": int(r.so_dong),
                   "tong_tien": float(getattr(r, "tong", 0) or 0),
                   "nhanh_nhat": str(dau), "cham_nhat": str(cuoi), "trai_dai_phut": phut,
                   # Dòng mỗi phút: người gõ tay hiếm khi vượt vài dòng một phút. Số này lớn thì dòng
                   # đó là máy đổ vào chứ không phải người nhập, và hậu kiểm nhập tay không áp được.
                   "dong_moi_phut": round(int(r.so_dong) / phut, 1) if phut else None})
    return ra


def _khoang_thang(thang: str) -> tuple[datetime, datetime]:
    y, m = int(thang[:4]), int(thang[5:7])
    dau = datetime(y, m, 1)
    sau = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    return dau, sau


def _thang_truoc(thang: str) -> str:
    y, m = int(thang[:4]), int(thang[5:7])
    return f"{y-1}-12" if m == 1 else f"{y}-{m-1:02d}"


# ============================== SÁU DẤU HIỆU ==============================
def _tong_theo_nguon(db: Session, thang: str, kho: dict) -> dict:
    """Tổng tiền tháng này và tháng trước của từng nguồn. Đệm lại: bảng đo bốn ngưỡng chỉ khác nhau ở
    PHÉP SO, không khác nhau ở số liệu – tính lại bốn lần là trả giá bốn lần cho cùng một con số."""
    k = ("tong", thang)
    if k in kho: return kho[k]
    a, b = _khoang_thang(thang); c, d = _khoang_thang(_thang_truoc(thang))
    ra = {ng["ma"]: (_tong_tien(db, ng, a, b), _tong_tien(db, ng, c, d)) for ng in NGUON if ng["tien"]}
    kho[k] = ra
    return ra


def _lech_ky(db: Session, thang: str, lan: float, toi_thieu: float, kho: dict | None = None) -> list[dict]:
    """Tổng tháng này so với tổng CHÍNH nguồn đó tháng trước. So với chính nó chứ không so giữa các
    phòng: mỗi phòng một quy mô, so chéo thì phòng lớn luôn bị báo và phòng nhỏ không bao giờ."""
    ra = []
    tong = _tong_theo_nguon(db, thang, kho if kho is not None else {})
    for ng in NGUON:
        if not ng["tien"]: continue
        nay, truoc = tong.get(ng["ma"], (0.0, 0.0))
        if truoc <= 0 or nay <= 0: continue          # chưa có kỳ trước thì không có gì để so
        ty = nay / truoc
        if max(ty, 1 / ty) < lan: continue
        if abs(nay - truoc) < toi_thieu: continue    # lệch nhiều lần nhưng số bé thì không đáng gọi ai
        ra.append({"loai": "nt_lech_ky", "nguon": ng["ma"],
                   "tom_tat": f"{ng['ten']} tháng {thang}: {nay:,.0f}đ, gấp {ty:.1f} lần tháng "
                              f"{_thang_truoc(thang)} ({truoc:,.0f}đ)" if ty >= 1 else
                              f"{ng['ten']} tháng {thang}: {nay:,.0f}đ, chỉ bằng 1/{1/ty:.1f} tháng "
                              f"{_thang_truoc(thang)} ({truoc:,.0f}đ)",
                   "chi_tiet": {"thang": thang, "nay": nay, "truoc": truoc, "ty_le": round(ty, 2)}})
    return ra


def _so_tron(db: Session, thang: str, tu_muc: float, lap: int, kho: dict | None = None) -> list[dict]:
    """Số chẵn triệu ở khoản lớn, cùng một người lặp lại nhiều dòng. Một con số tròn không nói lên gì;
    cùng một con số tròn lặp lại thì đó là người đang ƯỚC chứ không phải đang chép từ chứng từ."""
    a, b = _khoang_thang(thang); ra = []
    for ng in NGUON:
        if not ng["tien"]: continue
        dem: dict[tuple, int] = {}
        for x in _doc(db, ng, a, b, kho):
            if x["tien"] >= tu_muc and x["tien"] % 1_000_000 == 0:
                k = (x["nguoi"], x["tien"]); dem[k] = dem.get(k, 0) + 1
        for (nguoi, tien), n in dem.items():
            if n < lap: continue
            ra.append({"loai": "nt_so_tron", "nguon": ng["ma"], "nguoi": nguoi,
                       "tom_tat": f"{ng['ten']}: {nguoi} nhập đúng {tien:,.0f}đ {n} lần trong tháng "
                                  f"{thang} – số chẵn lặp lại ở khoản lớn thường là số ước, không phải "
                                  f"số chép từ chứng từ",
                       "chi_tiet": {"thang": thang, "nguoi": nguoi, "so_tien": tien, "so_lan": n}})
    return ra


def _ngoai_gio(db: Session, thang: str, gio_dau: int, gio_cuoi: int, don_dong: int, kho: dict | None = None) -> list[dict]:
    """Ngoài giờ làm việc, hoặc nhập dồn nhiều dòng trong năm phút."""
    a, b = _khoang_thang(thang); ra = []
    for ng in NGUON:
        rows = _doc(db, ng, a, b, kho)
        ngoai: dict[str, int] = {}
        for x in rows:
            h = x["luc"].hour if isinstance(x["luc"], datetime) else None
            if h is None: continue
            if h < gio_dau or h >= gio_cuoi: ngoai[x["nguoi"]] = ngoai.get(x["nguoi"], 0) + 1
        for nguoi, n in ngoai.items():
            if n < 3: continue        # một hai dòng ngoài giờ là chuyện thường của ngành lữ hành
            ra.append({"loai": "nt_ngoai_gio", "nguon": ng["ma"], "nguoi": nguoi,
                       "tom_tat": f"{ng['ten']}: {nguoi} nhập {n} dòng ngoài giờ làm việc "
                                  f"({gio_dau}h–{gio_cuoi}h) trong tháng {thang}",
                       "chi_tiet": {"thang": thang, "nguoi": nguoi, "so_dong": n}})
        # nhập dồn: sắp theo người rồi trượt cửa sổ năm phút
        theo_nguoi: dict[str, list] = {}
        for x in rows:
            if isinstance(x["luc"], datetime): theo_nguoi.setdefault(x["nguoi"], []).append(x["luc"])
        for nguoi, ds in theo_nguoi.items():
            # Cửa sổ trượt bằng HAI CON TRỎ, không phải hai vòng lồng nhau. Bản cũ, với mỗi mốc lại dò
            # lại từ đầu cửa sổ, là O(n²): một bản nhập hàng loạt 25.728 bút toán cùng rơi vào vài phút
            # thì thành hơn ba trăm triệu phép trừ thời gian, và trên máy chủ 0,5 CPU cổng trả 502
            # trước khi hàm chạy xong – tức là dấu hiệu "nhập dồn" TẮT đúng vào lúc có nhập dồn thật.
            # Danh sách đã sắp tăng dần nên `dau` không bao giờ phải lùi: mỗi mốc vào và ra đúng một
            # lần, O(n).
            ds.sort(); dinh = 0; dau = 0
            for cuoi in range(len(ds)):
                while (ds[cuoi] - ds[dau]).total_seconds() > 300: dau += 1
                dinh = max(dinh, cuoi - dau + 1)
            if dinh >= don_dong:
                ra.append({"loai": "nt_ngoai_gio", "nguon": ng["ma"], "nguoi": nguoi,
                           "tom_tat": f"{ng['ten']}: {nguoi} nhập {dinh} dòng trong vòng 5 phút tháng "
                                      f"{thang} – nhập dồn thường là chép lại từ một bảng có sẵn, "
                                      f"không phải nhập theo chứng từ",
                           "chi_tiet": {"thang": thang, "nguoi": nguoi, "dong_5_phut": dinh}})
    return ra


def _khac_phong(db: Session, thang: str, kho: dict | None = None) -> list[dict]:
    from app.models.core import User
    from app.services.ks_robot import PHONG_CUA_VAI_TRO
    a, b = _khoang_thang(thang)
    vai = {u.username: PHONG_CUA_VAI_TRO.get(u.role, "") for u in db.execute(select(User)).scalars()}
    ra = []
    for ng in NGUON:
        if not ng["phong"]: continue
        dem: dict[str, int] = {}
        for x in _doc(db, ng, a, b, kho):
            p = vai.get(x["nguoi"])
            # Không biết người này thuộc phòng nào thì IM LẶNG. Đoán rồi báo là cách nhanh nhất để
            # người ta thôi đọc bảng ngoại lệ.
            if p and p != ng["phong"] and p != "Ban Tổng giám đốc":
                dem[x["nguoi"]] = dem.get(x["nguoi"], 0) + 1
        for nguoi, n in dem.items():
            ra.append({"loai": "nt_khac_phong", "nguon": ng["ma"], "nguoi": nguoi,
                       "tom_tat": f"{ng['ten']} là sổ của phòng {ng['phong']}, nhưng {nguoi} "
                                  f"({vai.get(nguoi)}) nhập {n} dòng trong tháng {thang}",
                       "chi_tiet": {"thang": thang, "nguoi": nguoi, "so_dong": n,
                                    "phong_so": ng["phong"], "phong_nguoi": vai.get(nguoi)}})
    return ra


def _lui_ngay(db: Session, thang: str, kho: dict | None = None) -> list[dict]:
    """Ngày chứng từ thuộc kỳ ĐÃ KHÓA mà dòng được nhập sau đó. Với quyết định "nhập là dùng luôn",
    kỳ khóa là chốt chặn cuối cùng còn lại – nên mọi lần lách nó phải hiện ra."""
    from app.models.accounting import PeriodLock
    a, b = _khoang_thang(thang)
    khoa = {p.period for p in db.execute(select(PeriodLock)).scalars()}
    if not khoa: return []
    ra = []
    for ng in NGUON:
        dem: dict[str, int] = {}
        for x in _doc(db, ng, a, b, kho):
            d = x["ngay"]
            ky = f"{d.year}-{d.month:02d}" if isinstance(d, (date, datetime)) else ""
            if ky and ky in khoa: dem[x["nguoi"]] = dem.get(x["nguoi"], 0) + 1
        for nguoi, n in dem.items():
            ra.append({"loai": "nt_lui_ngay", "nguon": ng["ma"], "nguoi": nguoi,
                       "tom_tat": f"{ng['ten']}: {nguoi} nhập {n} dòng mang ngày thuộc kỳ ĐÃ KHÓA, "
                                  f"nhập trong tháng {thang}",
                       "chi_tiet": {"thang": thang, "nguoi": nguoi, "so_dong": n}})
    return ra


def _sua_da_chot(db: Session, thang: str, kho: dict | None = None) -> list[dict]:
    """Sửa một số đã dùng để lên báo cáo. Đọc từ nhật ký bất biến – đó là chỗ duy nhất còn giữ được
    việc một con số từng mang giá trị khác."""
    if kho is not None and ("sua", thang) in kho: return kho[("sua", thang)]
    from app.models.core import AuditLog
    from app.models.accounting import PeriodLock
    a, b = _khoang_thang(thang)
    khoa = sorted({p.period for p in db.execute(select(PeriodLock)).scalars()})
    if not khoa:
        if kho is not None: kho[("sua", thang)] = []
        return []
    moc = max(khoa)
    # Chỉ soi BA kỳ khóa gần nhất. Nhật ký bất biến là bảng lớn nhất hệ thống và mỗi kỳ thêm một mệnh
    # đề LIKE không dùng được chỉ mục; soi hết mọi kỳ đã khóa từ đầu là cách chắc chắn làm cổng hết giờ.
    khoa = khoa[-3:]
    # Lọc trong SQL và CHỈ lấy hai cột. Nhật ký bất biến là bảng lớn nhất hệ thống; nạp cả cột
    # before/after về Python để tìm chuỗi là cách chắc chắn làm cổng trả 502.
    from sqlalchemy import or_
    dieu_kien = or_(*[func.lower(AuditLog.action).like(f"%{k}%")
                      for k in ("sua", "cap_nhat", "dieu_chinh", "mo_lai", "huy")])
    ky_dieu_kien = or_(*[AuditLog.entity.like(f"%{k}%") for k in khoa])
    q = (select(AuditLog.actor, func.count())
         .where(AuditLog.ts >= a, AuditLog.ts < b, dieu_kien, ky_dieu_kien,
                func.lower(func.coalesce(AuditLog.actor, "")).notin_(BO_QUA_NGUOI))
         .group_by(AuditLog.actor))
    dem = {actor: int(n) for actor, n in db.execute(q).all() if actor}
    ket = [{"loai": "nt_sua_da_chot", "nguon": "nhat_ky", "nguoi": ng,
             "tom_tat": f"{ng} có {n} thao tác sửa/điều chỉnh chạm vào kỳ đã khóa (tới {moc}) trong "
                        f"tháng {thang} – số đã lên báo cáo mà đổi thì báo cáo cũ không còn đúng",
             "chi_tiet": {"thang": thang, "nguoi": ng, "so_thao_tac": n}}
           for ng, n in dem.items() if n > 0]
    if kho is not None: kho[("sua", thang)] = ket
    return ket


# ============================== CHẠY & ĐO ==============================
def _nguong(db: Session) -> dict:
    g = lambda k, m: float(R.get_param(db, k) or m)   # noqa: E731
    return {"lan": g("ks_lech_lan", 3), "lech_toi_thieu": g("ks_lech_toi_thieu", 20_000_000),
            "tron_tu": g("ks_tron_tu", 10_000_000), "tron_lap": int(g("ks_tron_lap", 3)),
            "gio_dau": int(g("ks_gio_bat_dau", 7)), "gio_cuoi": int(g("ks_gio_ket_thuc", 21)),
            "don_dong": int(g("ks_don_dong", 10))}


def quet_thang(db: Session, thang: str, n: dict | None = None, kho: dict | None = None) -> list[dict]:
    n = n or _nguong(db)
    kho = {} if kho is None else kho
    ra: list[dict] = []
    import time as _t
    dong_ho = kho.setdefault("_dong_ho", {})
    for ten, f in (("nt_lech_ky", lambda: _lech_ky(db, thang, n["lan"], n["lech_toi_thieu"], kho)),
                   ("nt_so_tron", lambda: _so_tron(db, thang, n["tron_tu"], n["tron_lap"], kho)),
                   ("nt_ngoai_gio", lambda: _ngoai_gio(db, thang, n["gio_dau"], n["gio_cuoi"], n["don_dong"], kho)),
                   ("nt_khac_phong", lambda: _khac_phong(db, thang, kho)),
                   ("nt_lui_ngay", lambda: _lui_ngay(db, thang, kho)),
                   ("nt_sua_da_chot", lambda: _sua_da_chot(db, thang, kho))):
        t0 = _t.perf_counter()
        try:
            ra += f()
        except Exception as ex:      # noqa – một dấu hiệu hỏng không được làm trắng cả bộ hậu kiểm
            ra.append({"loai": "nt_lech_ky", "nguon": "he_thong", "loi": True,
                       "tom_tat": f"Một dấu hiệu hậu kiểm lỗi, danh sách có thể THIẾU: {str(ex)[:160]}",
                       "chi_tiet": {}})
        # Đo từng dấu hiệu và trả ra: đoán chỗ chậm là cách mất một lần triển khai cho mỗi lần đoán sai.
        dong_ho[ten] = round(dong_ho.get(ten, 0.0) + (_t.perf_counter() - t0), 2)
    return ra


LOAI_TEN = {
    "nt_lech_ky": "Lệch bất thường so với kỳ trước",
    "nt_so_tron": "Số tròn trịa lặp lại ở khoản lớn",
    "nt_ngoai_gio": "Nhập ngoài giờ hoặc nhập dồn",
    "nt_khac_phong": "Một người nhập số cho phòng khác",
    "nt_lui_ngay": "Nhập lùi ngày vào kỳ đã khóa",
    "nt_sua_da_chot": "Sửa số đã dùng để lên báo cáo",
}


def do_nguong(db: Session, thang: str, lan: str = "2,3,5,10") -> dict:
    """Ngưỡng này ra bao nhiêu dòng? Bảng để NGƯỜI chọn con số, thay vì bắt họ đoán.

    Tiêu chí nghiệm thu của K3 là "danh sách đọc hết trong mười phút". Hàm này cho thấy trước mỗi ngưỡng
    sẽ ra bao nhiêu dòng, nên chọn được ngưỡng bằng số liệu chứ không bằng cảm giác.
    """
    goc = _nguong(db)
    bang = []
    kho: dict = {}       # đọc dữ liệu MỘT lần cho cả bảng đo, không mỗi ngưỡng một lần
    for x in [float(v) for v in lan.split(",") if v.strip()]:
        n = dict(goc, lan=x)
        ds = quet_thang(db, thang, n, kho)
        theo = {}
        for d in ds: theo[d["loai"]] = theo.get(d["loai"], 0) + 1
        bang.append({"lech_bao_nhieu_lan": x, "tong_dong": len(ds),
                     "theo_dau_hieu": {k: theo.get(k, 0) for k in LOAI_TEN}})
    return {"thang": thang, "nguong_dang_dung": goc, "loai": LOAI_TEN, "bang": bang,
            "ghi_chu": "Chỉ ngưỡng lệch-so-kỳ-trước thay đổi giữa các dòng; các dấu hiệu khác dùng "
                       "ngưỡng đang hiệu lực. Đọc cột tổng dòng: quá vài chục là ngưỡng còn lỏng."}


def _hau_kiem_nhap_tay(db: Session) -> list[dict]:
    """Bộ kiểm cho vòng quét của robot. Rà THÁNG NÀY và tháng trước – tháng trước vì số nhập muộn của
    kỳ vừa đóng mới là chỗ dễ có chuyện nhất."""
    hom_nay = date.today()
    thang = [f"{hom_nay:%Y-%m}"]
    tt = _thang_truoc(thang[0])
    if hom_nay.day <= int(R.get_param(db, "han_nhap_lieu_ngay") or 5) + 10: thang.append(tt)
    ra = []
    for th in thang:
        for d in quet_thang(db, th):
            if d.get("loi"):
                ra.append({"ma": "nhap_tay#loi_bo_do", "loai": "nhap_tay_bat_thuong", "muc": "vang",
                           "phong_ban": "Công nghệ thông tin", "doi_tuong": "hau_kiem",
                           "tom_tat": d["tom_tat"], "chi_tiet": {}})
                continue
            ma = f"{d['loai']}#{th}#{d.get('nguon','')}#{d.get('nguoi','')}"
            ra.append({"ma": ma[:160], "loai": "nhap_tay_bat_thuong",
                       "muc": "do" if d["loai"] in ("nt_lui_ngay", "nt_sua_da_chot") else "vang",
                       "phong_ban": "", "vai_tro": "", "doi_tuong": LOAI_TEN.get(d["loai"], d["loai"]),
                       "tom_tat": d["tom_tat"], "chi_tiet": d.get("chi_tiet", {})})
    return ra
