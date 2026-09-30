"""Robot Kiểm soát – vị trí Kiểm soát do AI giữ (chỉ đạo anh Trần Tuấn 07/9/2026).

Bốn việc anh giao: kiểm tra, thử, giám sát, báo cáo mọi phòng ban về Chủ tịch.

Ba nguyên tắc viết vào mã để không ai phải nhớ:

1. ROBOT KHÔNG SỬA SỐ CỦA PHÒNG BAN NÓ GIÁM SÁT. Nó chỉ ghi vào ba bảng của chính nó và ghi giải trình
   vào ngoại lệ. Mở việc ra được, ĐÓNG lại thì không – đóng là quyền của người. Đó là điều làm cho báo
   cáo của nó có giá trị; một người vừa chấm điểm vừa sửa được số thì điểm không có nghĩa gì.

2. KHÔNG ĐỦ DỮ LIỆU THÌ NÓI LÀ KHÔNG ĐỦ, KHÔNG CHẤM 0. Phòng chưa có số liệu và phòng làm kém là hai
   chuyện khác nhau. Chấm 0 cho phòng chưa có số là vu oan bằng số học.

3. CHỈ BÁO CÁO KHI CÓ VIỆC NGHIÊM TRỌNG (anh Tuấn chốt). Báo cáo định kỳ đều đặn là thứ người ta thôi
   đọc sau ba tuần. Một báo cáo chỉ đến khi có chuyện thì lúc nó đến, người ta mở ra.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session

from app.models.core import User, Tour, Booking, AuditLog, AiRun, ROLES
from app.models.kiem_soat import KsPhatHien, KsDiem, KsBaoCao, MUC_KS, LOAI_PHAT_HIEN
from app.services import rules as R
from app.services import access as AC
from app.services import ngoai_le as NL

# Ngoại lệ nghiêm trọng tồn quá số ngày này thì robot coi là việc của nó.
NGAY_TON_TOI_DA = 14
# Vai trò → phòng ban chịu trách nhiệm, dùng khi gán việc cho đúng người.
PHONG_CUA_VAI_TRO = {
    "tp_dh": "Điều hành", "nv_dh": "Điều hành",
    "gd_kd": "Kinh doanh", "tp_kd": "Kinh doanh", "tn_kd": "Kinh doanh", "nv_kd": "Kinh doanh",
    "nv_mkt": "Marketing", "ptgd_mkt": "Marketing",
    "ketoan": "Kế toán", "hcns": "Hành chính Nhân sự", "hanh_chinh": "Hành chính Nhân sự",
    "cntt": "Công nghệ thông tin", "nv_visa": "Visa",
    "gd_doi_xe": "Đội xe", "xe_hdv": "Đội xe", "tp_hd": "Hướng dẫn",
    "ptgd_doan": "Ban Tổng giám đốc", "tgd": "Ban Tổng giám đốc", "chutich": "Ban Tổng giám đốc",
}


# ============================== KIỂM TRA & THỬ ==============================
def _mach_migration() -> list[dict]:
    """Mạch nâng cấp cơ sở dữ liệu phải có ĐÚNG MỘT đầu. Nhiều đầu thì lệnh nâng cấp lúc khởi động
    dừng lại, và máy chủ không lên được – nên đây là kiểm tra đầu tiên, không phải kiểm tra cuối."""
    import os, re, pathlib
    thu_muc = pathlib.Path(__file__).resolve().parents[2] / "alembic" / "versions"
    if not thu_muc.is_dir(): return []
    d = {}
    for f in thu_muc.glob("*.py"):
        s = f.read_text(encoding="utf-8", errors="ignore")
        rev = re.search(r"^revision(?::.*?)?\s*=\s*['\"]([^'\"]+)", s, re.M)
        down = re.search(r"^down_revision(?::.*?)?\s*=\s*['\"]?([^'\"\s]+)", s, re.M)
        if rev: d[rev.group(1)] = (down.group(1).strip() if down else None)
    con = set(d.values())
    dau = [k for k in d if k not in con]
    if len(dau) <= 1: return []
    return [{"ma": "mach_migration#nhieu_dau", "loai": "mach_migration", "muc": "do",
             "phong_ban": "Công nghệ thông tin", "doi_tuong": "alembic",
             "tom_tat": f"Mạch nâng cấp cơ sở dữ liệu đang có {len(dau)} đầu ({', '.join(dau)}). "
                        f"Lần phát hành tới máy chủ sẽ không khởi động được.",
             "chi_tiet": {"dau": dau}}]


def _quyen_lech(db: Session) -> list[dict]:
    """Màn hình tiền ẩn khỏi menu một vai trò thì API đằng sau cũng phải đóng. Ẩn khỏi mắt mà vẫn đọc
    được bằng đường dẫn trực tiếp thì không chặn gì cả."""
    from app.main import app
    CUA_TIEN = {"/bank-accounts": "/api/v1/bank-accounts", "/finance": "/api/v1/finance",
                "/accounting": "/api/v1/accounting", "/audit": "/api/v1/audit",
                "/hr": "/api/v1/payroll"}
    ra = []
    for man, tien_to in CUA_TIEN.items():
        cho_phep = AC.MENU_ROLES.get(man)
        if not cho_phep: continue
        for vai in ROLES:
            if vai in cho_phep: continue
            # Kiểm ở mức khai báo: endpoint nào KHÔNG khai require_roles thì mọi vai trò đăng nhập đều
            # gọi được. Đây là cách kiểm tĩnh, không phải gọi thật – gọi thật thuộc bộ kiểm thử tự động.
            mo = [r for r in app.routes
                  if getattr(r, "path", "").startswith(tien_to) and "{" not in getattr(r, "path", "")
                  and "GET" in (getattr(r, "methods", None) or set())
                  and not _co_chan_vai_tro(r)]
            if mo:
                ra.append({"ma": f"quyen_lech#{man}#{vai}", "loai": "quyen_lech", "muc": "do",
                           "phong_ban": PHONG_CUA_VAI_TRO.get(vai, ""), "vai_tro": vai,
                           "doi_tuong": man,
                           "tom_tat": f"{ROLES[vai]} không thấy {man} trên menu, nhưng "
                                      f"{len(mo)} đường dẫn API đằng sau không khai vai trò nào",
                           "chi_tiet": {"duong_dan": [r.path for r in mo][:20]}})
    return ra


# Lịch sử của hàm dưới đây, vì nó giải thích cả thiết kế lẫn một phép thử:
#
# Trong kho từng tồn tại HAI kiểu chặn vai trò – khai ở chữ ký, và gọi AC.require(...) trong thân hàm.
# Bộ kiểm chỉ nhìn thấy kiểu thứ nhất, nên lần chạy đầu trên hệ thống thật nó báo oan 26 việc, trong
# đó có GET /audit vốn chặn đúng. Vá tạm bằng cách đọc thêm mã nguồn hàm (df7f5f4). Ngày 08/9/2026,
# việc P1 dọn hẳn: cả 16 chỗ chặn trong thân hàm đã chuyển lên chữ ký, kho chỉ còn MỘT kiểu khai.
#
# Vì sao vẫn giữ phần đọc mã nguồn: nó là lưới an toàn cho chặn phụ thuộc dữ liệu (ví dụ lọc theo tab
# bảng lương) mà chữ ký không diễn tả được. Nhưng lưới đó phải RỖNG trong điều kiện bình thường – phép
# thử test_khong_endpoint_nao_con_phai_doc_ma_nguon canh đúng chỗ ấy: có ai lại thêm một chỗ chặn
# trong thân hàm thì phép thử đỏ, chứ không phải robot lặng lẽ mù đi một lần nữa.
CHAN_TRONG_THAN = ("AC.require(", "access.require(", "require_roles", "bang_luong", "_require(",
                   "check_readonly_write", "hr_tabs_for", "co_quyen(")


def chan_o_chu_ky(route) -> bool:
    """Đọc quyền TỪ CHỮ KÝ, không phân tích mã nguồn. Đây là đường chính."""
    try:
        dep = getattr(route, "dependant", None)
        for d in (getattr(dep, "dependencies", None) or []):
            call = getattr(d, "call", None)
            if call is None:
                continue
            if (hasattr(call, "vai_tro_yeu_cau") or getattr(call, "la_cong_chan_quyen", False)
                    or "require_roles" in getattr(call, "__qualname__", "")):
                return True
        for d in (getattr(route, "dependencies", None) or []):
            if "require_roles" in str(d):
                return True
    except Exception:
        return False
    return False


def _doc_ma_nguon(route) -> bool:
    try:
        import inspect
        return any(k in inspect.getsource(route.endpoint) for k in CHAN_TRONG_THAN)
    except Exception:
        return True


def _co_chan_vai_tro(route) -> bool:
    """True nếu endpoint có chặn vai trò. Không đọc được thì trả True – robot thà bỏ sót còn hơn tố
    oan; việc bỏ sót đã có bộ kiểm thử vai trò gọi thật để bắt."""
    return chan_o_chu_ky(route) or _doc_ma_nguon(route)


def endpoint_phai_doc_ma_nguon(app) -> list[str]:
    """Những endpoint mà bộ kiểm chỉ nhận ra được nhờ đọc mã nguồn. Danh sách này phải RỖNG."""
    ra = []
    for r in app.routes:
        if not hasattr(r, "endpoint") or not str(getattr(r, "path", "")).startswith("/api/v1"):
            continue
        if not chan_o_chu_ky(r) and _doc_ma_nguon(r):
            ra.append(f"{sorted(getattr(r, 'methods', []) or [])} {r.path}")
    return sorted(set(ra))


def _vai_tro_trong(db: Session) -> list[dict]:
    """Vai trò không mở được màn hình nào là vai trò đăng nhập vào và nhìn thấy hệ thống trống.

    Đếm qua CẢ HAI nguồn khai màn hình, không chỉ ma trận: bảy vai trò hẹp (bốn của người, ba của máy)
    lấy màn hình từ danh sách CHO PHÉP chứ không từ MENU_ROLES. Chỉ đếm một nguồn thì bộ dò báo đỏ đúng
    những vai trò đã khai đầy đủ nhất – và một cảnh báo đỏ sai là thứ dạy người đọc bỏ qua cảnh báo đỏ.
    """
    ra = []
    for vai in ROLES:
        so = len(AC.RESTRICTED_ROLE_MENUS.get(vai) or
                 [m for m, cho in AC.MENU_ROLES.items() if vai in cho])
        if so == 0:
            ra.append({"ma": f"vai_tro_trong#{vai}", "loai": "vai_tro_trong", "muc": "do",
                       "phong_ban": PHONG_CUA_VAI_TRO.get(vai, ""), "vai_tro": vai, "doi_tuong": vai,
                       "tom_tat": f"{ROLES[vai]} không được khai ở màn hình nào trong ma trận phân quyền",
                       "chi_tiet": {}})
    return ra


def _vai_tro_khong_co_nguoi(db: Session) -> list[dict]:
    """Vai trò có trong ma trận nhưng không tài khoản nào đang hoạt động giữ nó.

    Vì sao đây là việc phải mở ra chứ không phải lập tài khoản giả cho đủ: một vai trò không có người
    là một khoảng trống QUẢN LÝ – có màn hình, có quyền, có việc, mà không ai làm. Tạo tám tài khoản
    đăng nhập được để "cho đủ bảng" thì bảng trông đẹp còn khoảng trống vẫn nguyên, và đổi lại hệ thống
    của một công ty đại chúng có thêm tám lối vào mà không ai dùng – nghĩa là không ai để ý khi có người
    dùng chúng.

    Mức VÀNG chứ không đỏ: đây là việc bố trí người, không phải lỗ hổng bảo mật.
    """
    from app.models.core import User
    ra = []
    co_nguoi = {u.role for u in db.execute(select(User).where(User.active == True)).scalars()}   # noqa: E712
    for vai in ROLES:
        if vai in co_nguoi or AC.la_vai_tro_may(vai):
            continue          # vai trò MÁY không bao giờ có "người" – hỏi ở đây là hỏi sai câu
        so_man = len([m for m, cho in AC.MENU_ROLES.items() if vai in cho])
        ra.append({"ma": f"vai_tro_khong_co_nguoi#{vai}", "loai": "vai_tro_khong_co_nguoi", "muc": "vang",
                   "phong_ban": PHONG_CUA_VAI_TRO.get(vai, ""), "vai_tro": vai, "doi_tuong": vai,
                   "tom_tat": f"{ROLES[vai]} được khai {so_man} màn hình trong ma trận nhưng chưa có "
                              f"tài khoản nào giữ vai trò này – quyền đã cấp mà chưa ai nhận việc",
                   "chi_tiet": {"so_man_hinh": so_man}})
    return ra


def _quyen_tung_vai_tro(db: Session) -> list[dict]:
    """Quét quyền của TỪNG vai trò trên hệ thống thật, không cần tài khoản và không cần đăng nhập.

    Bộ kiểm thử ở máy đã quét vai trò bằng cách tạo tài khoản robot rồi gọi thật. Trên hệ thống thật
    thì không làm thế được – tạo tài khoản để robot đăng nhập là tạo lối vào thật, và cất mật khẩu cho
    nó là một bài toán khác. Nhưng không cần: hai lớp chặn đều là hàm thuần của chuỗi vai trò, nên dựng
    một User trong bộ nhớ rồi gọi thẳng hàng rào là đủ để biết vai trò đó đi được tới đâu.
    """
    from app.models.core import User
    from fastapi import HTTPException
    from app.main import app
    ra = []
    duong_dan = sorted({r.path for r in app.routes
                        if str(getattr(r, "path", "")).startswith("/api/v1") and "{" not in r.path
                        and "GET" in (getattr(r, "methods", None) or set())})
    for vai in ROLES:
        u = User(username=f"_quet_{vai}", full_name="quét quyền", role=vai, password_hash="")
        mo = 0
        for d in duong_dan:
            try:
                AC.check_restricted_scope(u, d)
                mo += 1
            except HTTPException:
                pass
        if mo == 0:
            ra.append({"ma": f"quyen_tung_vai_tro#{vai}", "loai": "vai_tro_trong", "muc": "do",
                       "phong_ban": PHONG_CUA_VAI_TRO.get(vai, ""), "vai_tro": vai, "doi_tuong": vai,
                       "tom_tat": f"{ROLES[vai]} bị hàng rào phạm vi chặn ở MỌI đường dẫn – vai trò này "
                                  f"đăng nhập vào là nhìn thấy hệ thống trống",
                       "chi_tiet": {"so_duong_dan": len(duong_dan)}})
    return ra


def _ngoai_le_ton(db: Session) -> list[dict]:
    """Ngoại lệ nghiêm trọng để lâu không ai trả lời."""
    ra = []
    try:
        ds = NL.danh_sach(db, cat_moi_loai=0)["rows"]
    except Exception as ex:
        return [{"ma": "ngoai_le_ton#loi_doc", "loai": "ngoai_le_ton", "muc": "vang", "phong_ban": "",
                 "doi_tuong": "ngoai_le", "tom_tat": f"Không đọc được danh sách ngoại lệ: {str(ex)[:140]}",
                 "chi_tiet": {}}]
    ton = [r for r in ds if r["muc"] == "do" and r["trang_thai"] != "dong"
           and (r["so_ngay_ton"] or 0) > NGAY_TON_TOI_DA]
    theo_loai: dict[str, int] = {}
    for r in ton: theo_loai[r["loai"]] = theo_loai.get(r["loai"], 0) + 1
    for loai, n in theo_loai.items():
        ra.append({"ma": f"ngoai_le_ton#{loai}", "loai": "ngoai_le_ton", "muc": "do", "phong_ban": "",
                   "doi_tuong": loai,
                   "tom_tat": f"{n} ngoại lệ nghiêm trọng loại “{NL.LOAI[loai]['ten']}” tồn quá "
                              f"{NGAY_TON_TOI_DA} ngày, chưa ai giải trình",
                   "chi_tiet": {"so_luong": n}})
    return ra


def _ai_chua_hau_kiem(db: Session) -> list[dict]:
    n = db.execute(select(func.count(AiRun.id)).where(AiRun.trang_thai == "cho_hau_kiem")).scalar() or 0
    if n < 10: return []
    return [{"ma": "ai_chua_hau_kiem#tich_luy", "loai": "ai_chua_hau_kiem",
             "muc": "do" if n >= 50 else "vang", "phong_ban": "Marketing", "doi_tuong": "ai_runs",
             "tom_tat": f"{n} nội dung AI mức 3 đã chạy mà chưa ai hậu kiểm. Mức 3 không hậu kiểm "
                        f"chính là mức 3 không hạn mức.",
             "chi_tiet": {"so_luong": n}}]


# K1, K2, K6 (lệnh 08/9/2026). Ba bộ kiểm này viết TRƯỚC khi ai sửa mã, để đo được sửa tới đâu:
# hai bộ đầu đếm cột tiền còn sai kiểu và cột "chưa có số" đang bị ghi thành 0; bộ thứ ba là chỗ robot
# nhìn thấy sức khỏe của chính máy chủ chứ không chỉ số liệu của các phòng ban.
from app.services.ks_cot_tien import _cot_tien_float, _thieu_khac_khong   # noqa: E402
from app.services.ky_thuat import _su_kien_ky_thuat                       # noqa: E402

# K3 – lớp bảo vệ thay cho khâu trưởng phòng duyệt đã bỏ. Chạy trong cùng vòng quét chứ không thành
# một lịch riêng: một bộ hậu kiểm có lịch riêng là một bộ hậu kiểm sẽ có ngày không ai chạy.
from app.services.ks_nhap_tay import _hau_kiem_nhap_tay                   # noqa: E402
from app.services.ks_do_dai import _do_dai_du_lieu                       # noqa: E402
from app.services.ks_ma_tran import _ma_tran_quyen                       # noqa: E402
from app.services.ks_nap_lo import _doi_chieu_lo_nap            # noqa: E402  – K5
from app.services.ks_cua_nhap import _cua_nhap_du_lieu
from app.services.ks_toan_quyen import _tach_bach_dang_mo        # noqa: E402  – công tắc mở hết cửa        # noqa: E402  – mọi số phải có cửa
from app.services.ks_tien_vao import _hai_duong_tien_vao      # noqa: E402  – hai đường tiền vào

# HỢP của hai nhánh, không phải chọn một: nhánh phân quyền thêm hai bộ kiểm về vai trò, nhánh kiểm
# soát thêm bộ hậu kiểm số nhập tay. Gộp mà bỏ mất một bên thì bộ kiểm đó im lặng biến mất – và một
# bộ kiểm biến mất không báo lỗi, nó chỉ ngừng tìm ra vấn đề.
def _vai_tro_may_chua_co_tai_khoan(db: Session) -> list[dict]:
    """Vai trò máy đã khai quyền nhưng chưa có tài khoản nào giữ nó.

    Câu hỏi này thay cho "vai trò chưa có người" ở ba vai trò robot, và nó KHÁC hẳn về hướng xử lý:
    vai trò người thiếu người là việc bố trí nhân sự; vai trò máy thiếu tài khoản nghĩa là robot vẫn
    đang chạy dưới tên một con người, nên nhật ký vẫn chưa phân biệt được ai làm gì – đúng vấn đề mà
    P8 sinh ra để giải.

    Cũng báo khi MỘT vai trò máy có nhiều hơn một tài khoản: hai tài khoản cùng một vai trò máy thì
    lại không truy được lần chạy nào của bên nào.
    """
    from app.models.core import User
    dem: dict[str, list[str]] = {}
    for u in db.execute(select(User).where(User.active == True)).scalars():   # noqa: E712
        if AC.la_vai_tro_may(u.role):
            dem.setdefault(u.role, []).append(u.username)
    ra = []
    for vai in AC.VAI_TRO_MAY:
        ten = dem.get(vai, [])
        if len(ten) == 1:
            continue
        thieu = not ten
        ra.append({"ma": f"vai_tro_may#{vai}", "loai": "vai_tro_khong_co_nguoi", "muc": "vang",
                   "phong_ban": "", "vai_tro": vai, "doi_tuong": vai,
                   "tom_tat": (f"{ROLES[vai]} chưa có tài khoản riêng – robot vẫn chạy dưới tên một "
                               f"con người, nhật ký chưa phân biệt được ai làm gì" if thieu
                               else f"{ROLES[vai]} có {len(ten)} tài khoản ({', '.join(ten)}) – "
                                    f"không truy được lần chạy nào của bên nào"),
                   "chi_tiet": {"tai_khoan": ten}})
    return ra


BO_KIEM = (_mach_migration, _quyen_lech, _vai_tro_trong, _vai_tro_khong_co_nguoi,
           _vai_tro_may_chua_co_tai_khoan,
           _quyen_tung_vai_tro, _ngoai_le_ton, _ai_chua_hau_kiem,
           _cot_tien_float, _thieu_khac_khong, _su_kien_ky_thuat, _hau_kiem_nhap_tay,
           _do_dai_du_lieu, _ma_tran_quyen, _doi_chieu_lo_nap,
           _cua_nhap_du_lieu, _hai_duong_tien_vao, _tach_bach_dang_mo)


def quet(db: Session, boi: str = "robot_ks") -> dict:
    """Chạy một vòng quét. Ghi phát hiện vào bảng của robot; KHÔNG đụng dữ liệu nghiệp vụ."""
    thay: list[dict] = []
    loi_bo_kiem = []
    for f in BO_KIEM:
        try:
            thay += (f(db) if f is not _mach_migration else f())
        except Exception as ex:
            loi_bo_kiem.append(f"{f.__name__}: {str(ex)[:160]}")

    now = datetime.now()
    ma_thay = {t["ma"] for t in thay}
    cu = {p.ma: p for p in db.execute(select(KsPhatHien)).scalars()}
    moi = lap_lai = 0
    for t in thay:
        p = cu.get(t["ma"])
        if p is None:
            db.add(KsPhatHien(ma=t["ma"], loai=t["loai"], muc=t["muc"], phong_ban=t.get("phong_ban", ""),
                              vai_tro=t.get("vai_tro", ""), doi_tuong=t.get("doi_tuong", ""),
                              tom_tat=t["tom_tat"], chi_tiet=t.get("chi_tiet"),
                              lan_dau=now, lan_cuoi=now, so_lan=1, con=True))
            moi += 1
        else:
            p.lan_cuoi, p.so_lan, p.con = now, p.so_lan + 1, True
            p.muc, p.tom_tat, p.chi_tiet = t["muc"], t["tom_tat"], t.get("chi_tiet")
            lap_lai += 1
    het = 0
    for ma, p in cu.items():
        if ma not in ma_thay and p.con:
            p.con = False; het += 1

    R.audit(db, boi, "bks", "robot_ks_quet", "kiem_soat",
            after={"moi": moi, "lap_lai": lap_lai, "het": het, "loi_bo_kiem": loi_bo_kiem})
    db.commit()

    bc = _bao_cao_neu_nghiem_trong(db, boi)
    return {"moi": moi, "van_con": lap_lai, "da_het": het, "loi_bo_kiem": loi_bo_kiem,
            "bao_cao_id": bc.id if bc else None,
            "ghi_chu": "Không có việc nghiêm trọng nào mới – không sinh báo cáo" if not bc else
                       f"Đã lập báo cáo gửi Chủ tịch: {bc.ly_do}"}


# ============================== BÁO CÁO (chỉ khi nghiêm trọng) ==============================
def _bao_cao_neu_nghiem_trong(db: Session, boi: str) -> KsBaoCao | None:
    do = [p for p in db.execute(select(KsPhatHien).where(KsPhatHien.con == True,      # noqa: E712
                                                          KsPhatHien.muc == "do",
                                                          KsPhatHien.da_bao_cao == False)).scalars()]
    if not do: return None
    vang = db.execute(select(func.count(KsPhatHien.id)).where(KsPhatHien.con == True,   # noqa: E712
                                                              KsPhatHien.muc == "vang")).scalar() or 0
    dong = [f"- [{LOAI_PHAT_HIEN.get(p.loai, p.loai)}] {p.tom_tat}"
            + (f"  (phòng {p.phong_ban})" if p.phong_ban else "") for p in do]
    noi_dung = ("Robot Kiểm soát báo cáo Chủ tịch. Báo cáo này chỉ được lập khi có việc nghiêm trọng, "
                "không có bản định kỳ.\n\nViệc nghiêm trọng mới phát hiện:\n" + "\n".join(dong) +
                f"\n\nNgoài ra còn {vang} việc ở mức cần rà soát, xem màn hình Kiểm soát.")
    bc = KsBaoCao(ly_do=f"{len(do)} việc nghiêm trọng mới", so_do=len(do), so_vang=vang,
                  noi_dung=noi_dung, ma_phat_hien={"ma": [p.ma for p in do]})
    db.add(bc)
    for p in do: p.da_bao_cao = True
    R.audit(db, boi, "bks", "robot_ks_bao_cao", "kiem_soat",
            after={"so_do": len(do), "ly_do": bc.ly_do})
    db.commit()
    return bc


# ============================== CHẤM ĐIỂM PHÒNG BAN ==============================
# Bốn chỉ tiêu, mỗi chỉ tiêu 25 điểm. Chỉ tiêu nào KHÔNG có dữ liệu thì bị loại khỏi mẫu số chứ không
# tính 0 – phòng chưa có số liệu và phòng làm kém là hai chuyện khác nhau.
CHI_TIEU = {
    "ngoai_le": "Ngoại lệ chưa giải trình",
    "phat_hien": "Việc robot phát hiện còn tồn",
    "quyet_toan": "Chuyến quá hạn quyết toán",
    "du_toan": "Chuyến bán khi dự toán chưa đủ cơ sở",
}


def cham_diem(db: Session, ky: str | None = None, boi: str = "robot_ks") -> dict:
    from app.services import ai_log as AL
    ky = ky or f"{date.today():%Y-%m}"
    phong = sorted({p for p in PHONG_CUA_VAI_TRO.values()})

    try:
        ngoai_le = NL.danh_sach(db, cat_moi_loai=0)["rows"]
    except Exception:
        ngoai_le = []
    ph = [p for p in db.execute(select(KsPhatHien).where(KsPhatHien.con == True)).scalars()]  # noqa: E712
    hom_nay = date.today()
    qua_han = [t for t in db.execute(select(Tour).where(Tour.status == "ket_thuc")).scalars()
               if R.settlement_deadline(db, t) < hom_nay]

    ra = []
    for p in phong:
        can_cu, diem_phan, co_so = {}, [], []
        n_ph = len([x for x in ph if x.phong_ban == p])
        can_cu["phat_hien"] = n_ph
        diem_phan.append(max(0, 25 - n_ph * 5)); co_so.append("phat_hien")

        # Ngoại lệ và quyết toán chỉ gán được cho phòng khi phòng đó thực sự nắm nghiệp vụ đó.
        if p in ("Điều hành", "Kế toán"):
            n_nl = len([x for x in ngoai_le if x["trang_thai"] != "dong" and x["muc"] == "do"])
            can_cu["ngoai_le"] = n_nl
            diem_phan.append(25 if n_nl == 0 else max(0, 25 - min(25, n_nl)))
            co_so.append("ngoai_le")
        if p == "Điều hành":
            can_cu["quyet_toan"] = len(qua_han)
            diem_phan.append(max(0, 25 - len(qua_han) * 2)); co_so.append("quyet_toan")

        du = len(co_so) >= 2      # dưới hai chỉ tiêu có số thì không đủ cơ sở chấm
        diem = round(sum(diem_phan) / len(diem_phan) * 4, 1) if (du and diem_phan) else None
        nhan_xet = (f"Chấm trên {len(co_so)} chỉ tiêu có số liệu: "
                    + "; ".join(f"{CHI_TIEU[k]} = {can_cu[k]}" for k in co_so)) if du else \
                   ("Chưa đủ cơ sở chấm: phòng này mới có "
                    f"{len(co_so)} chỉ tiêu có số liệu, cần ít nhất 2. Không chấm 0 – chưa có số liệu "
                    "và làm kém là hai chuyện khác nhau.")

        cu = db.execute(select(KsDiem).where(KsDiem.ky == ky, KsDiem.phong_ban == p)).scalars().first()
        if cu is None:
            cu = KsDiem(ky=ky, phong_ban=p); db.add(cu)
        cu.diem, cu.can_cu, cu.nhan_xet, cu.du_co_so = diem, can_cu, nhan_xet, du
        cu.trang_thai, cu.luc = "cho_hau_kiem", datetime.now()
        ra.append({"phong_ban": p, "diem": diem, "du_co_so": du, "nhan_xet": nhan_xet, "can_cu": can_cu})

    # Chấm điểm con người là ô rủi ro cao nhất trong bảng quyền AI: phải để lại vết ở nhật ký AI, và
    # kết quả ở trạng thái CHỜ HẬU KIỂM của Chủ tịch chứ không phải kết luận.
    try:
        AL.ghi(db, tac_vu="cham_diem", muc=3, ref=f"ks_diem:{ky}", vai_tro="bks",
               nguon="quy_tac", so_ban_ghi=len(ra),
               ket_qua="; ".join(f"{r['phong_ban']}={r['diem'] if r['du_co_so'] else 'chưa đủ cơ sở'}" for r in ra),
               trang_thai="cho_hau_kiem")
    except Exception:
        pass
    R.audit(db, boi, "bks", "robot_ks_cham_diem", f"ks_diem:{ky}",
            after={"so_phong": len(ra), "chua_du_co_so": [r["phong_ban"] for r in ra if not r["du_co_so"]]})
    db.commit()
    return {"ky": ky, "rows": ra, "chi_tieu": CHI_TIEU,
            "ghi_chu": "Điểm do máy chấm là ĐỀ XUẤT, có hiệu lực sau khi Chủ tịch hậu kiểm."}


def hau_kiem_diem(db: Session, u: User, diem_id: int, chap_nhan: bool, ghi_chu: str = "") -> str:
    from fastapi import HTTPException
    d = db.get(KsDiem, diem_id)
    if d is None: raise HTTPException(404, "Không có bản chấm điểm này")
    d.trang_thai = "chap_nhan" if chap_nhan else "bac"
    d.hau_kiem_boi, d.hau_kiem_luc, d.hau_kiem_ghi_chu = u.username, datetime.now(), ghi_chu
    R.audit(db, u.username, u.role, "hau_kiem_diem_phong_ban", f"ks_diem:{d.id}",
            after={"phong_ban": d.phong_ban, "ky": d.ky, "chap_nhan": chap_nhan, "ghi_chu": ghi_chu})
    db.commit()
    return "Đã ghi nhận hậu kiểm"


# ============================== ĐỌC ==============================
# Bàn giám sát quá bao nhiêu giờ thì phải nói ra là mình đang cũ. 26 giờ = một ngày cộng hai giờ
# rộng rãi cho lượt 20:30 VN chạy trễ hoặc trượt một lượt vì Render đang khởi động lại.
GIO_BAN_CU = 26


def quet_lan_cuoi(db: Session) -> datetime | None:
    """Lần vòng quét gần nhất, đọc từ chuỗi kiểm toán – KHÔNG đọc từ `lan_cuoi` của phát hiện.

    `max(lan_cuoi)` trông như cùng một con số nhưng nó trả lời câu khác: một vòng quét không tìm thấy
    gì thì không có phát hiện nào để đóng dấu thời gian, và khi ấy `max(lan_cuoi)` đứng lại y như lúc
    robot chết. Hệ quả đúng là hệ quả xấu nhất: bảng sạch và bảng đứng hình đọc ra giống nhau.
    """
    r = db.execute(select(AuditLog).where(AuditLog.action == "robot_ks_quet")
                   .order_by(desc(AuditLog.ts)).limit(1)).scalars().first()
    return r.ts if r else None


def bang(db: Session) -> dict:
    ph = db.execute(select(KsPhatHien).order_by(KsPhatHien.con.desc(), KsPhatHien.muc,
                                                desc(KsPhatHien.lan_cuoi))).scalars().all()
    bc = db.execute(select(KsBaoCao).order_by(desc(KsBaoCao.luc)).limit(20)).scalars().all()
    dm = db.execute(select(KsDiem).order_by(desc(KsDiem.ky), KsDiem.phong_ban)).scalars().all()
    return {
        "phat_hien": [{"id": p.id, "ma": p.ma, "loai": p.loai, "loai_ten": LOAI_PHAT_HIEN.get(p.loai, p.loai),
                       "muc": p.muc, "muc_ten": MUC_KS.get(p.muc, p.muc), "phong_ban": p.phong_ban,
                       "vai_tro": p.vai_tro, "doi_tuong": p.doi_tuong, "tom_tat": p.tom_tat,
                       "chi_tiet": p.chi_tiet, "lan_dau": p.lan_dau.isoformat(),
                       "lan_cuoi": p.lan_cuoi.isoformat(), "so_lan": p.so_lan, "con": p.con,
                       "da_bao_cao": p.da_bao_cao} for p in ph],
        "bao_cao": [{"id": b.id, "luc": b.luc.isoformat(), "ly_do": b.ly_do, "so_do": b.so_do,
                     "so_vang": b.so_vang, "noi_dung": b.noi_dung, "da_xem": b.da_xem,
                     "xem_boi": b.xem_boi} for b in bc],
        "diem": [{"id": d.id, "ky": d.ky, "phong_ban": d.phong_ban, "diem": d.diem,
                  "du_co_so": d.du_co_so, "nhan_xet": d.nhan_xet, "can_cu": d.can_cu,
                  "trang_thai": d.trang_thai, "hau_kiem_boi": d.hau_kiem_boi,
                  "hau_kiem_ghi_chu": d.hau_kiem_ghi_chu, "luc": d.luc.isoformat()} for d in dm],
        "tong_hop": {
            "con_do": len([p for p in ph if p.con and p.muc == "do"]),
            "con_vang": len([p for p in ph if p.con and p.muc == "vang"]),
            "da_het": len([p for p in ph if not p.con]),
            "bao_cao_chua_xem": len([b for b in bc if not b.da_xem]),
            "diem_cho_hau_kiem": len([d for d in dm if d.trang_thai == "cho_hau_kiem"]),
        },
        "chi_tieu": CHI_TIEU, "loai_phat_hien": LOAI_PHAT_HIEN, "muc": MUC_KS,
        # Ba ô dưới đây để màn hình nói được TUỔI của tấm ảnh nó đang vẽ. Thiếu chúng thì ngày
        # 30/9/2026 Chủ tịch đọc một bàn giám sát chốt ngày 10/9 mà không có gì trên màn hình cho
        # biết điều đó – và tưởng "1 việc nghiêm trọng còn tồn" là tình trạng hôm nay.
        # RỖNG = chưa quét lần nào, khác hẳn "quét rồi mà không thấy gì".
        **_tuoi_ban(db),
    }


def _tuoi_ban(db: Session) -> dict:
    lc = quet_lan_cuoi(db)
    if lc is None:
        return {"quet_lan_cuoi": None, "quet_cach_day_gio": None, "ban_cu": True,
                "ban_cu_ly_do": "Chưa có vòng quét nào – mọi con số trên bàn này đều chưa được kiểm"}
    gio = (datetime.now() - lc).total_seconds() / 3600
    cu = gio > GIO_BAN_CU
    return {"quet_lan_cuoi": lc.isoformat(), "quet_cach_day_gio": round(gio, 1), "ban_cu": cu,
            "ban_cu_ly_do": (f"Vòng quét gần nhất cách đây {round(gio / 24, 1)} ngày – bàn này là ảnh cũ, "
                             f"việc đã hết vẫn treo và việc mới chưa mở" if cu else "")}


def danh_dau_da_xem(db: Session, u: User, bao_cao_id: int) -> str:
    from fastapi import HTTPException
    b = db.get(KsBaoCao, bao_cao_id)
    if b is None: raise HTTPException(404, "Không có báo cáo này")
    b.da_xem, b.xem_boi, b.xem_luc = True, u.username, datetime.now()
    R.audit(db, u.username, u.role, "xem_bao_cao_kiem_soat", f"ks_bao_cao:{b.id}")
    db.commit()
    return "Đã đánh dấu đã xem"
