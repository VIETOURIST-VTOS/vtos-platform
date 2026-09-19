"""Đọc và ghi cơ cấu tổ chức khối Kinh doanh.

CHỖ DUY NHẤT TRẢ LỜI "NGÀY ẤY NGƯỜI NÀY THUỘC ĐƠN VỊ NÀO". Mọi báo cáo theo cấp sau này phải gọi
`don_vi_cua()` hoặc `pham_vi_xem()` ở đây, không tự đi đọc bảng. Lý do rất cụ thể: luật "phân công
có ngày hiệu lực" chỉ có giá trị khi KHÔNG nơi nào bỏ qua được nó, mà cách chắc chắn nhất để một
luật bị bỏ qua là để mỗi màn hình tự viết lại truy vấn của mình.

SEC-02 — PHẠM VI CẮT Ở MÁY CHỦ, TRONG TRUY VẤN. `pham_vi_xem()` trả về danh sách id đơn vị mà người
dùng được nhìn; hàm gọi phải đưa danh sách ấy vào mệnh đề lọc, không lọc sau khi đã lấy hết về rồi
bỏ bớt. Bản bàn giao V5.0 nói thẳng tình huống thử: nhân viên đổi id trên URL vẫn không đọc được
đơn vị ngoài quyền — muốn vậy thì phải cắt lúc truy vấn.

RANH GIỚI 09/9/2026. Tệp này viết CẤU TRÚC và PHÉP TÍNH; nó không nạp sẵn một chi nhánh, một phòng
hay một team nào. Danh mục đơn vị và phân công do Hành chính – Nhân sự nhập ở màn hình /to-chuc-kd.
"""
from datetime import date

from sqlalchemy import select

from app.models.core import User
from app.models.to_chuc_kd import CAP, CHA_HOP_LE, MANG, VAI_DON_VI, DonViKD, PhanCongKD
from app.services import rules as R

# Vai đăng nhập nhìn được TOÀN BỘ cây, bất kể có dòng phân công nào hay không. Cố ý HẸP: hai người
# của Ban Tổng giám đốc, hai tài khoản kiểm soát chỉ-đọc, Hành chính – Nhân sự (người giữ sổ cơ cấu)
# và Công nghệ thông tin (người sửa khi sổ hỏng).
#
# `gd_kd` KHÔNG có ở đây, và đó là chủ ý. Giám đốc Kinh doanh nhìn toàn khối bằng DÒNG PHÂN CÔNG
# "giam_doc" gắn vào chi nhánh/mảng của mình, chứ không bằng chức danh. Bản bàn giao V5.0 viết đúng
# câu ấy: "không gán quyền chỉ bằng tên chức danh". Nếu một ngày có hai Giám đốc Kinh doanh Lẻ ở hai
# vùng, cách này đã đúng sẵn; cách kia thì phải sửa mã.
XEM_TOAN_CAY = ("chutich", "tgd", "bks", "robot_ks", "hcns", "cntt")


def _kiem_cap(cap: str, cha: DonViKD | None) -> None:
    if cap not in CAP:
        raise ValueError(f"Cấp không hợp lệ: {cap!r}. Chỉ có {', '.join(CAP)}.")
    can_cha = CHA_HOP_LE.get(cap)
    if can_cha is None:
        if cha is not None:
            raise ValueError(f"Cấp {cap!r} là cấp gốc, không được treo dưới đơn vị nào.")
        return
    if cha is None:
        raise ValueError(f"Cấp {cap!r} phải nằm dưới một {can_cha!r}.")
    if cha.cap != can_cha:
        raise ValueError(f"Cấp {cap!r} phải nằm dưới {can_cha!r}, không phải {cha.cap!r}.")


def tao_don_vi(db, u: User, ma: str, ten: str, cap: str, mang: str = "le",
               cha_id: int | None = None, company_id: int | None = None,
               hieu_luc_tu: date | None = None, ghi_chu: str = "") -> DonViKD:
    ma = (ma or "").strip().upper()
    ten = (ten or "").strip()
    if not ma:
        raise ValueError("Thiếu mã đơn vị.")
    if not ten:
        raise ValueError("Thiếu tên đơn vị.")
    if mang not in MANG:
        raise ValueError(f"Mảng không hợp lệ: {mang!r}. Chỉ có {', '.join(MANG)}.")
    if db.execute(select(DonViKD).where(DonViKD.ma == ma)).scalar_one_or_none():
        raise ValueError(f"Mã {ma!r} đã có đơn vị khác dùng.")

    cha = db.get(DonViKD, cha_id) if cha_id else None
    if cha_id and cha is None:
        raise ValueError("Không tìm thấy đơn vị cha.")
    if cha is not None and cha.mang != mang:
        raise ValueError(f"Đơn vị cha thuộc mảng {cha.mang!r}, không thể treo đơn vị mảng {mang!r} vào.")
    _kiem_cap(cap, cha)

    dv = DonViKD(ma=ma, ten=ten, cap=cap, mang=mang, cha_id=cha_id, company_id=company_id,
                 hieu_luc_tu=hieu_luc_tu or date.today(), ghi_chu=ghi_chu, boi=u.username)
    db.add(dv)
    db.flush()
    R.audit(db, u.username, u.role, "tao_don_vi_kd", f"don_vi_kd:{dv.ma}",
            after={"ma": dv.ma, "ten": dv.ten, "cap": dv.cap, "mang": dv.mang, "cha_id": dv.cha_id})
    return dv


def dong_don_vi(db, u: User, don_vi_id: int, den_ngay: date, ly_do: str) -> DonViKD:
    """Đóng một đơn vị. KHÔNG XOÁ — xem quyết định HAI ở đầu models/to_chuc_kd.py."""
    dv = db.get(DonViKD, don_vi_id)
    if dv is None:
        raise ValueError("Không tìm thấy đơn vị.")
    if not (ly_do or "").strip():
        raise ValueError("Đóng một đơn vị phải ghi lý do.")
    if den_ngay < dv.hieu_luc_tu:
        raise ValueError("Ngày đóng không được trước ngày đơn vị bắt đầu có hiệu lực.")

    con = db.execute(select(DonViKD).where(DonViKD.cha_id == dv.id,
                                           DonViKD.hieu_luc_den.is_(None))).scalars().all()
    if con:
        raise ValueError("Còn " + str(len(con)) + " đơn vị con đang mở. Đóng từ dưới lên, "
                         "để không có đơn vị nào treo dưới một đơn vị đã đóng.")

    truoc = {"hieu_luc_den": dv.hieu_luc_den.isoformat() if dv.hieu_luc_den else None}
    dv.hieu_luc_den = den_ngay
    dv.ghi_chu = (dv.ghi_chu + "\n" if dv.ghi_chu else "") + f"Đóng {den_ngay}: {ly_do.strip()}"
    R.audit(db, u.username, u.role, "dong_don_vi_kd", f"don_vi_kd:{dv.ma}",
            before=truoc, after={"hieu_luc_den": den_ngay.isoformat(), "ly_do": ly_do.strip()})
    return dv


def phan_cong(db, u: User, user_id: int, don_vi_id: int, vai: str,
              tu_ngay: date, den_ngay: date | None = None, ly_do: str = "") -> PhanCongKD:
    """Ghi một người vào một đơn vị từ `tu_ngay`.

    Chặn chồng lấn (quyết định BỐN): cùng người, cùng mảng, cùng vai thì hai khoảng không được phủ
    nhau. Khác mảng thì được — một người phụ trách cả Lẻ lẫn Đoàn là chuyện có thật.
    """
    if vai not in VAI_DON_VI:
        raise ValueError(f"Vai trong đơn vị không hợp lệ: {vai!r}. Chỉ có {', '.join(VAI_DON_VI)}.")
    if db.get(User, user_id) is None:
        raise ValueError("Không tìm thấy tài khoản.")
    dv = db.get(DonViKD, don_vi_id)
    if dv is None:
        raise ValueError("Không tìm thấy đơn vị.")
    if den_ngay is not None and den_ngay < tu_ngay:
        raise ValueError("Ngày kết thúc không được trước ngày bắt đầu.")
    if not dv.dang_hieu_luc(tu_ngay):
        raise ValueError(f"Đơn vị {dv.ma} không có hiệu lực vào ngày {tu_ngay}.")

    for cu in _phan_cong_cua(db, user_id):
        if cu.vai != vai:
            continue
        dv_cu = db.get(DonViKD, cu.don_vi_id)
        if dv_cu is None or dv_cu.mang != dv.mang:
            continue
        if _chong_lan(cu.tu_ngay, cu.den_ngay, tu_ngay, den_ngay):
            raise ValueError(
                f"Người này đã có phân công {cu.vai!r} ở {dv_cu.ma} từ {cu.tu_ngay}"
                + (f" đến {cu.den_ngay}" if cu.den_ngay else " (chưa kết thúc)")
                + ". Kết thúc dòng cũ trước, không để hai dòng phủ cùng một ngày.")

    pc = PhanCongKD(user_id=user_id, don_vi_id=don_vi_id, vai=vai, tu_ngay=tu_ngay,
                    den_ngay=den_ngay, ly_do=ly_do.strip(), boi=u.username)
    db.add(pc)
    db.flush()
    R.audit(db, u.username, u.role, "phan_cong_kd", f"user:{user_id}",
            after={"don_vi": dv.ma, "vai": vai, "tu_ngay": tu_ngay.isoformat(),
                   "den_ngay": den_ngay.isoformat() if den_ngay else None})
    return pc


def ket_thuc_phan_cong(db, u: User, phan_cong_id: int, den_ngay: date, ly_do: str) -> PhanCongKD:
    pc = db.get(PhanCongKD, phan_cong_id)
    if pc is None:
        raise ValueError("Không tìm thấy dòng phân công.")
    if not (ly_do or "").strip():
        raise ValueError("Kết thúc một phân công phải ghi lý do.")
    if den_ngay < pc.tu_ngay:
        raise ValueError("Ngày kết thúc không được trước ngày bắt đầu.")
    truoc = {"den_ngay": pc.den_ngay.isoformat() if pc.den_ngay else None}
    pc.den_ngay = den_ngay
    pc.ly_do = (pc.ly_do + " | " if pc.ly_do else "") + ly_do.strip()
    R.audit(db, u.username, u.role, "ket_thuc_phan_cong_kd", f"phan_cong_kd:{pc.id}",
            before=truoc, after={"den_ngay": den_ngay.isoformat(), "ly_do": ly_do.strip()})
    return pc


def _chong_lan(a1: date, a2: date | None, b1: date, b2: date | None) -> bool:
    """Hai khoảng [a1,a2] và [b1,b2] có phủ nhau không. `None` ở vế sau = chưa kết thúc."""
    if a2 is not None and b1 > a2:
        return False
    if b2 is not None and a1 > b2:
        return False
    return True


def _phan_cong_cua(db, user_id: int) -> list[PhanCongKD]:
    return list(db.execute(select(PhanCongKD).where(PhanCongKD.user_id == user_id)).scalars())


def don_vi_cua(db, user_id: int, ngay: date, mang: str = "le") -> DonViKD | None:
    """Ngày ấy người này thuộc đơn vị nào của mảng ấy. Không có phân công thì trả về None —
    RỖNG KHÁC KHÔNG: "chưa phân công" không phải là "thuộc chi nhánh mặc định"."""
    sau = None
    for pc in _phan_cong_cua(db, user_id):
        if not pc.dang_hieu_luc(ngay):
            continue
        dv = db.get(DonViKD, pc.don_vi_id)
        if dv is None or dv.mang != mang:
            continue
        # Nhiều dòng hợp lệ cùng lúc chỉ xảy ra khi khác vai (chồng lấn cùng vai đã bị chặn lúc
        # ghi). Lấy đơn vị ở cấp THẤP NHẤT: một Trưởng phòng kiêm bán hàng thì chỗ làm việc hằng
        # ngày của họ là team, không phải cả phòng.
        if sau is None or CAP.index(dv.cap) > CAP.index(sau.cap):
            sau = dv
    return sau


def con_chau(db, don_vi_id: int, ngay: date | None = None) -> list[int]:
    """Id của đơn vị này và mọi đơn vị nằm dưới nó. `ngay` lọc theo hiệu lực nếu có truyền."""
    ra: list[int] = []
    hang = [don_vi_id]
    while hang:
        cur = hang.pop()
        dv = db.get(DonViKD, cur)
        if dv is None:
            continue
        if ngay is not None and not dv.dang_hieu_luc(ngay):
            continue
        ra.append(cur)
        hang.extend(r for (r,) in db.execute(select(DonViKD.id).where(DonViKD.cha_id == cur)))
    return ra


def pham_vi_xem(db, u: User, ngay: date | None = None, mang: str = "le") -> list[int] | None:
    """Danh sách id đơn vị người này được nhìn. `None` = nhìn tất cả (xem XEM_TOAN_CAY).

    Danh sách RỖNG khác `None`: rỗng nghĩa là người này không được nhìn đơn vị nào — chưa ai phân
    công họ. Hàm gọi phải phân biệt hai thứ ấy, đừng dùng `if not pham_vi`.
    """
    if u.role in XEM_TOAN_CAY:
        return None
    ngay = ngay or date.today()
    ra: list[int] = []
    for pc in _phan_cong_cua(db, u.id):
        if not pc.dang_hieu_luc(ngay):
            continue
        dv = db.get(DonViKD, pc.don_vi_id)
        if dv is None or dv.mang != mang:
            continue
        for i in con_chau(db, dv.id):
            if i not in ra:
                ra.append(i)
    return ra


def duoc_xem(db, u: User, don_vi_id: int, ngay: date | None = None, mang: str = "le") -> bool:
    pv = pham_vi_xem(db, u, ngay, mang)
    return pv is None or don_vi_id in pv


def cay(db, mang: str = "le", ngay: date | None = None) -> list[dict]:
    """Cây đơn vị của một mảng, mỗi nút kèm số người đang phân công vào ĐÚNG nút ấy."""
    ngay = ngay or date.today()
    tat_ca = list(db.execute(select(DonViKD).where(DonViKD.mang == mang)).scalars())
    dem: dict[int, int] = {}
    for pc in db.execute(select(PhanCongKD)).scalars():
        if pc.dang_hieu_luc(ngay):
            dem[pc.don_vi_id] = dem.get(pc.don_vi_id, 0) + 1

    theo_cha: dict[int | None, list[DonViKD]] = {}
    for dv in tat_ca:
        theo_cha.setdefault(dv.cha_id, []).append(dv)

    def dung(cha_id: int | None) -> list[dict]:
        ra = []
        for dv in sorted(theo_cha.get(cha_id, []), key=lambda x: x.ma):
            ra.append({
                "id": dv.id, "ma": dv.ma, "ten": dv.ten, "cap": dv.cap, "mang": dv.mang,
                "company_id": dv.company_id,
                "hieu_luc_tu": dv.hieu_luc_tu.isoformat(),
                "hieu_luc_den": dv.hieu_luc_den.isoformat() if dv.hieu_luc_den else None,
                "con_hieu_luc": dv.dang_hieu_luc(ngay),
                "so_nguoi": dem.get(dv.id, 0),
                "ghi_chu": dv.ghi_chu,
                "con": dung(dv.id),
            })
        return ra

    return dung(None)


def nguoi_trong(db, don_vi_ids: list[int], ngay: date | None = None) -> list[dict]:
    """Ai đang thuộc những đơn vị này vào `ngay`."""
    ngay = ngay or date.today()
    ra = []
    for pc in db.execute(select(PhanCongKD).where(PhanCongKD.don_vi_id.in_(don_vi_ids))).scalars():
        if not pc.dang_hieu_luc(ngay):
            continue
        nguoi = db.get(User, pc.user_id)
        dv = db.get(DonViKD, pc.don_vi_id)
        ra.append({
            "phan_cong_id": pc.id,
            "user_id": pc.user_id,
            "ho_ten": nguoi.full_name if nguoi else f"(tài khoản {pc.user_id} đã xoá)",
            "tai_khoan": nguoi.username if nguoi else "",
            "vai_dang_nhap": nguoi.role if nguoi else "",
            "don_vi_id": pc.don_vi_id,
            "don_vi": dv.ten if dv else "",
            "don_vi_ma": dv.ma if dv else "",
            "vai": pc.vai,
            "tu_ngay": pc.tu_ngay.isoformat(),
            "den_ngay": pc.den_ngay.isoformat() if pc.den_ngay else None,
            "ly_do": pc.ly_do,
        })
    return sorted(ra, key=lambda x: (x["don_vi_ma"], x["vai"], x["ho_ten"]))


def lich_su_cua(db, user_id: int) -> list[dict]:
    """Toàn bộ đường đi của một người qua các đơn vị — cái làm cho báo cáo kỳ cũ giữ nguyên số."""
    ra = []
    for pc in sorted(_phan_cong_cua(db, user_id), key=lambda x: x.tu_ngay):
        dv = db.get(DonViKD, pc.don_vi_id)
        ra.append({
            "phan_cong_id": pc.id,
            "don_vi": dv.ten if dv else "", "don_vi_ma": dv.ma if dv else "",
            "cap": dv.cap if dv else "", "mang": dv.mang if dv else "",
            "vai": pc.vai,
            "tu_ngay": pc.tu_ngay.isoformat(),
            "den_ngay": pc.den_ngay.isoformat() if pc.den_ngay else None,
            "ly_do": pc.ly_do, "boi": pc.boi,
        })
    return ra


def chua_phan_cong(db, ngay: date | None = None, mang: str = "le") -> list[dict]:
    """Tài khoản kinh doanh chưa có đơn vị vào `ngay` — danh sách đối chiếu, không phải lỗi.

    Cùng nếp với màn hình Pháp nhân: ô trống hiện ra ở một danh sách để người có thẩm quyền chỉ
    định, chứ không tự điền một giá trị mặc định.
    """
    ngay = ngay or date.today()
    VAI_KD = ("gd_kd", "tp_kd", "tn_kd", "nv_kd")
    ra = []
    for nguoi in db.execute(select(User).where(User.role.in_(VAI_KD))).scalars():
        if not nguoi.active:
            continue
        if don_vi_cua(db, nguoi.id, ngay, mang) is None:
            ra.append({"user_id": nguoi.id, "ho_ten": nguoi.full_name,
                       "tai_khoan": nguoi.username, "vai_dang_nhap": nguoi.role,
                       "sales_group": nguoi.sales_group or ""})
    return sorted(ra, key=lambda x: x["ho_ten"] or "")
