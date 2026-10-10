"""Bộ kiểm tách bạch trách nhiệm theo NGƯỜI — Đợt E2a, 09/10/2026.

Lý do tồn tại và cách định danh người: xem `models/tach_nhiem.py`.

MỨC ĐỘ DÙNG CHUNG VỚI ĐỢT E1. Ba mức `khong_canh_bao / canh_bao_cho_qua / canh_bao_va_chan` đã
được đặt ra ở `models/muc_do_chan.py` và nhập từ đó, không chép lại thành bộ thứ hai — hai bộ mức
giống nhau là sớm muộn có người sửa một bộ.

CHƯA AI ĐẶT MỨC thì chạy ở mức nhẹ nhất NHƯNG BỊ ĐẾM LÊN (`cap_chua_dat_muc`). Cho qua mà có
người đếm thì được; cho qua trong im lặng thì không.

THẮT THÌ KẾ TOÁN LÀM ĐƯỢC, NỚI PHẢI CÓ CHỮ KÝ — cùng bất đối xứng đã dùng cho bảng quy ước hạch
toán và bảng mức độ chặn. Dựng thêm một cặp xung đột hay nâng mức của nó là THẮT. Hạ mức, tắt
`dang_ap_dung`, hoặc xoá một cặp là NỚI: phải có người ký, căn cứ, và ngày hiệu lực.

MỘT ĐIỀU BỘ KIỂM NÀY KHÔNG LÀM: nó không tự biết bước nào của nghiệp vụ nào. Nó chỉ so dấu chân
với bảng cặp. Chỗ nào gọi `ghi_buoc()` là chỗ ấy khai mình vừa làm bước gì — không khai thì không
có dấu chân, và không có dấu chân thì không bắt được gì. Phép thử `test_le2` canh đúng chuyện ấy
cho những bước đã nối.
"""
from datetime import datetime

from sqlalchemy import select

from app.models.muc_do_chan import MUC_DO, MUC_DO_KHI_CHUA_KHAI
from app.models.tach_nhiem import (BUOC, CAP_DA_KY, KHOA_BAT_BUOC_MA_NV, VAI_TIEN,
                                   BuocDaLam, CapTachNhiem, ma_nguoi)

# Mức nào là THẮT (ai cũng dựng được), mức nào là NỚI (phải ký).
THAT = ("canh_bao_va_chan",)
NOI = ("khong_canh_bao",)


def thieu_ma_nhan_vien(u) -> bool:
    """Tài khoản này làm việc với tiền mà chưa có mã nhân viên?

    Không có mã thì bộ kiểm coi nó là một người riêng, nên hai tài khoản của cùng một người
    đi được cả hai bước mà không ai thấy. Đây là lỗ CÒN LẠI sau khi so theo người, và nó chỉ
    bịt được bằng dữ liệu HCNS, không bịt được bằng mã.
    """
    return (getattr(u, "role", "") in VAI_TIEN
            and not (getattr(u, "staff_code", "") or "").strip())


def bat_buoc_ma_nv(db) -> bool:
    """Luật "vai tiền phải có mã nhân viên" đã tới ngày hiệu lực chưa?

    Tham số rỗng/lỗi → CHƯA, tức là chỉ đếm chứ chưa chặn. Một công tắc an toàn hỏng thì phải
    hỏng về phía KHÔNG KHÓA NGƯỜI RA NGOÀI: ở đây hậu quả của chặn nhầm (không ai chi được
    tiền) nặng hơn hậu quả của cho qua một vòng nữa, và chỗ cho qua vẫn bị đếm lên.
    """
    try:
        from app.services.rules import get_param
        return bool(get_param(db, KHOA_BAT_BUOC_MA_NV))
    except Exception:
        return False


def nap_cap_da_ky(db) -> list[str]:
    """Nạp các cặp Chủ tịch ĐÃ KÝ (xem `models/tach_nhiem.CAP_DA_KY`). Chạy lại được.

    CHỈ nạp đúng những dòng có chữ ký ghi trong mã, và KHÔNG đụng tới `muc_do` của dòng đã có
    — người ta đặt mức rồi thì lần nạp sau không được đặt lại hộ.
    """
    them = []
    for d in CAP_DA_KY:
        c = db.execute(select(CapTachNhiem)
                       .where(CapTachNhiem.ma_cap == d["ma_cap"])).scalars().first()
        if c is not None:
            continue
        db.add(CapTachNhiem(muc_do=None, dang_ap_dung=True, boi="he_thong",
                            ngay_hieu_luc=None, **d))
        them.append(d["ma_cap"])
    if them:
        db.commit()
    return them


def _hieu_luc(c: CapTachNhiem, luc: datetime | None = None) -> bool:
    """Cặp này đang có hiệu lực chưa? Chưa tới ngày hiệu lực thì coi như chưa đặt."""
    if not c.dang_ap_dung:
        return False
    if c.ngay_hieu_luc and c.ngay_hieu_luc > (luc or datetime.utcnow()):
        return False
    return True


def muc_do(c: CapTachNhiem, luc: datetime | None = None) -> str:
    """Mức thực sự đang áp cho một cặp. Rỗng, sai chính tả, hay chưa tới ngày → mức nhẹ nhất."""
    if not _hieu_luc(c, luc):
        return MUC_DO_KHI_CHUA_KHAI
    return c.muc_do if c.muc_do in MUC_DO else MUC_DO_KHI_CHUA_KHAI


def cap_chua_dat_muc(db) -> list[str]:
    """Những cặp đang áp dụng mà chưa ai đặt mức — để màn hình đếm lên, không để im."""
    ra = []
    for c in db.execute(select(CapTachNhiem).where(CapTachNhiem.dang_ap_dung == True)).scalars():
        if c.muc_do not in MUC_DO:
            ra.append(c.ma_cap)
    return sorted(ra)


def ghi_buoc(db, pham_vi: str, ma_buoc: str, u) -> BuocDaLam:
    """Để lại một dấu chân. GHI THÊM — làm lại một bước là một dòng nữa, không ghi đè dòng cũ."""
    d = BuocDaLam(pham_vi=str(pham_vi), ma_buoc=ma_buoc,
                  ma_nguoi=ma_nguoi(u), username=getattr(u, "username", "") or "",
                  vai=getattr(u, "role", "") or "")
    db.add(d)
    db.flush()
    return d


def _buoc_doi_lap(db, ma_buoc: str, luc: datetime | None = None) -> list[tuple[CapTachNhiem, str]]:
    """Các cặp đang hiệu lực có chứa bước này, kèm BƯỚC KIA của cặp ấy."""
    ra = []
    for c in db.execute(select(CapTachNhiem)).scalars():
        if not _hieu_luc(c, luc):
            continue
        if c.buoc_a == ma_buoc:
            ra.append((c, c.buoc_b))
        elif c.buoc_b == ma_buoc:
            ra.append((c, c.buoc_a))
    return ra


def kiem(db, pham_vi: str, ma_buoc: str, u, luc: datetime | None = None) -> dict:
    """Người này có được làm bước này trong phạm vi này không?

    Trả về {"chan": bool, "muc_do": str, "vi_pham": [...]}. KHÔNG tự ném lỗi và không tự ghi dấu
    chân: nơi gọi quyết định làm gì với kết quả, và chỉ ghi dấu chân khi bước ĐÃ làm xong. Ghi
    trước rồi mới kiểm là tự tạo dấu chân cho một bước chưa xảy ra.
    """
    nguoi = ma_nguoi(u)
    thieu_ma = thieu_ma_nhan_vien(u)
    chan_vi_thieu_ma = thieu_ma and bat_buoc_ma_nv(db)
    da_lam = list(db.execute(
        select(BuocDaLam).where(BuocDaLam.pham_vi == str(pham_vi))).scalars())
    vi_pham, nang_nhat = [], "khong_canh_bao"
    for c, buoc_kia in _buoc_doi_lap(db, ma_buoc, luc):
        trung = [d for d in da_lam if d.ma_buoc == buoc_kia and d.ma_nguoi == nguoi]
        if not trung:
            continue
        m = muc_do(c, luc)
        vi_pham.append({
            "ma_cap": c.ma_cap, "ten": c.ten or c.ma_cap, "muc_do": m,
            "buoc_nay": ma_buoc, "buoc_kia": buoc_kia,
            "ma_nguoi": nguoi, "username": getattr(u, "username", ""),
            "da_lam_luc": trung[0].luc.isoformat() if trung[0].luc else "",
            "thong_diep": (f"{getattr(u, 'full_name', '') or getattr(u, 'username', '')} đã làm "
                           f"bước “{buoc_kia}” trên chứng từ này; quy chế “{c.ten or c.ma_cap}” "
                           f"đòi bước “{ma_buoc}” phải do người khác làm."),
        })
        if m == "canh_bao_va_chan":
            nang_nhat = m
        elif m == "canh_bao_cho_qua" and nang_nhat != "canh_bao_va_chan":
            nang_nhat = m
    return {
        "chan": nang_nhat == "canh_bao_va_chan" or chan_vi_thieu_ma,
        "muc_do": nang_nhat,
        "vi_pham": vi_pham,
        "thieu_ma_nhan_vien": thieu_ma,
        "chan_vi_thieu_ma_nhan_vien": chan_vi_thieu_ma,
        "thong_diep_thieu_ma": (
            f"Tài khoản {getattr(u, 'username', '')} làm bước có tiền nhưng chưa có mã nhân "
            f"viên, nên hệ thống không đối chiếu được đây có phải cùng một người với bước kia "
            f"hay không. HCNS điền mã nhân viên cho tài khoản này." if thieu_ma else ""),
    }


def tai_khoan_thieu_ma_nv(db) -> list[dict]:
    """Danh sách tài khoản vai tiền chưa có mã nhân viên — để HCNS đi điền, và để đếm được.

    Trả về danh sách chứ không chỉ một con số: một con số thì không ai biết phải đi tìm ai.
    """
    from app.models.core import User
    ra = []
    for x in db.execute(select(User).where(User.active == True)).scalars():
        if thieu_ma_nhan_vien(x):
            ra.append({"id": x.id, "username": x.username, "ho_ten": x.full_name,
                       "vai": x.role, "bo_phan": x.department or ""})
    return sorted(ra, key=lambda d: (d["vai"], d["username"]))


# ══════════════════════════════════════════════════════════════════════════════════════════
# HAI VAI KHÔNG ĐƯỢC KIÊM NHAU — Chủ tịch chốt 10/10/2026.
#
# Quyết định: HCNS RIÊNG, thủ quỹ RIÊNG. Nó THAY phương án "thủ quỹ kiêm HCNS" từng được ghi là
# đã chốt, và nó BỎ ĐƯỢC một cặp tách nhiệm thứ ba: không ai kiêm thì không cần cặp để canh.
#
# ĐÂY LÀ LUẬT CẤP QUYỀN, KHÔNG PHẢI LUẬT MÃ. `users.role` là MỘT chuỗi, nên một tài khoản không
# thể vừa `hcns` vừa `thu_quy` — mã đã chặn sẵn mà không ai phải viết gì. Chỗ lọt được là MỘT
# NGƯỜI HAI TÀI KHOẢN, và nó lọt trong im lặng vì cả hai tài khoản đều trông đúng.
#
# NÊN PHẦN MỀM ĐẾM VÀ GỌI TÊN, KHÔNG CHẶN HỘ. Chặn ở đây là chặn sai chỗ: việc phải sửa là việc
# cấp quyền của HCNS, không phải một bước nghiệp vụ trong sổ kế toán. Cùng lựa chọn đã dùng cho
# `tai_khoan_thieu_ma_nv`: cái gì chỉ con người sửa được thì phần mềm làm cho nó ĐẾM ĐƯỢC.
#
# PHÉP ĐO MÙ Ở ĐÚNG MỘT CHỖ, và chỗ ấy ghi ra đây để không ai đọc con số 0 thành "sạch": tài
# khoản chưa có mã nhân viên thì `ma_nguoi()` trả `u:<id>`, nên mỗi tài khoản là một người riêng
# và hai tài khoản của cùng một người KHÔNG bị ghép. Hai phép đo bù nhau — `tai_khoan_thieu_ma_nv`
# đếm chỗ mù, hàm này đếm chỗ thấy được.
CAP_VAI_KHONG_KIEM = (
    {"ma": "hcns-vs-thu-quy", "vai_a": "hcns", "vai_b": "thu_quy",
     "ten": "Nhân sự Hành chính và Thủ quỹ",
     "can_cu": "Chủ tịch chốt 10/10/2026: HCNS riêng và thủ quỹ riêng, bỏ bố trí kiêm nhiệm. "
               "Người nhập dữ liệu công và lương không đồng thời là người giữ tiền."},
)


def vai_can_ma_de_phep_do_thay(db=None) -> tuple[str, ...]:
    """Mọi vai mà thiếu mã nhân viên làm MỘT PHÉP ĐO BỊ MÙ — rộng hơn `VAI_TIEN`.

    Hai danh sách khác nhau và cố ý khác nhau. `VAI_TIEN` là danh sách vai BỊ CHẶN khi thiếu mã
    (luật của Đợt E2a, bật theo ngày hiệu lực). Danh sách này là vai mà thiếu mã làm phép đo
    KHÔNG THẤY — gồm `VAI_TIEN` cộng mọi vai xuất hiện trong các cặp vai không được kiêm nhau.

    Bản rà soát 10/10/2026 bắt đúng khoảng giữa hai danh sách: `hcns` không thuộc `VAI_TIEN`,
    nên tài khoản HCNS thiếu mã không được đếm; thủ quỹ có mã, HCNS cùng người không có, phép
    đo không ghép được VÀ cờ mù vẫn báo không mù. Màn hình khi ấy hiện "Không trường hợp nào"
    trên một phép đo đang mù — đúng kiểu sai mà không có lỗi nào hiện ra.

    Mở rộng danh sách CHẶN thì sẽ chặn HCNS ở những bước họ không làm, nên không mở; thay vào
    đó đếm riêng, bằng hàm riêng, đặt tên theo đúng việc của nó.
    """
    ra = set(VAI_TIEN)
    for c in CAP_VAI_KHONG_KIEM:
        ra.add(c["vai_a"])
        ra.add(c["vai_b"])
    return tuple(sorted(ra))


def thieu_ma_lam_mu_phep_do(db) -> list[dict]:
    """Tài khoản thiếu mã nhân viên thuộc một vai mà phép đo cần đọc được.

    Trả danh sách, không trả số: con số nói có vấn đề, danh sách nói đi tìm ai.
    """
    from app.models.core import User
    vai = vai_can_ma_de_phep_do_thay()
    ra = []
    for x in db.execute(select(User).where(User.active == True)).scalars():   # noqa: E712
        if (getattr(x, "role", "") in vai
                and not (getattr(x, "staff_code", "") or "").strip()):
            ra.append({"id": x.id, "username": x.username, "ho_ten": x.full_name,
                       "vai": x.role, "bo_phan": x.department or ""})
    return sorted(ra, key=lambda d: (d["vai"], d["username"]))


def hai_vai_trung_nguoi(db) -> list[dict]:
    """Những người đang giữ cả hai tài khoản của một cặp vai không được kiêm nhau.

    Trả về danh sách có TÊN và có TÀI KHOẢN, không chỉ một con số: một con số thì không ai biết
    phải đi tìm ai mà thu hồi quyền.
    """
    from app.models.core import User
    theo_nguoi: dict[str, list] = {}
    for x in db.execute(select(User).where(User.active == True)).scalars():   # noqa: E712
        theo_nguoi.setdefault(ma_nguoi(x), []).append(x)

    ra = []
    for c in CAP_VAI_KHONG_KIEM:
        for ma, ds in theo_nguoi.items():
            if ma.startswith("u:"):
                continue      # chưa có mã nhân viên — chỗ mù, xem `tai_khoan_thieu_ma_nv`
            a = [x for x in ds if x.role == c["vai_a"]]
            b = [x for x in ds if x.role == c["vai_b"]]
            if a and b:
                ra.append({
                    "ma_cap": c["ma"], "ten": c["ten"], "ma_nguoi": ma,
                    "ho_ten": (a[0].full_name or b[0].full_name or ""),
                    "vai_a": c["vai_a"], "vai_b": c["vai_b"],
                    "tai_khoan": sorted(x.username for x in a + b),
                    "can_cu": c["can_cu"],
                })
    return sorted(ra, key=lambda d: (d["ma_cap"], d["ma_nguoi"]))


def dau_chan(db, pham_vi: str) -> list[dict]:
    """Toàn bộ dấu chân của một phạm vi, cũ trước — để Ban Kiểm soát đọc được ai làm gì."""
    ds = db.execute(
        select(BuocDaLam).where(BuocDaLam.pham_vi == str(pham_vi))
        .order_by(BuocDaLam.id)).scalars()
    return [{"ma_buoc": d.ma_buoc, "ma_nguoi": d.ma_nguoi, "username": d.username,
             "vai": d.vai, "luc": d.luc.isoformat() if d.luc else ""} for d in ds]
