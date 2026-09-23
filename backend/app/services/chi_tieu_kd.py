"""Giao và đọc chỉ tiêu của khối Kinh doanh.

CHỈ TIÊU LÀ ĐIỀU NGƯỜI TA QUYẾT ĐỊNH, KHÔNG PHẢI ĐIỀU HỆ THỐNG ĐO ĐƯỢC. Tệp này cố ý KHÔNG có hàm
nào suy chỉ tiêu ra từ thực hiện kỳ trước, dù làm thì dễ. Suy như thế là biến thước đo thành cái
bóng của chính số bị đo: tháng nào bán kém thì tháng sau chỉ tiêu tự hạ xuống, và không ai thấy gì
bất thường. Cùng một lý do đã ghi cho `ke_hoach_thang` ở `services/ks_cua_nhap.py`.

BA PHÉP KIỂM Ở ĐÂY, VÀ LÝ DO TỪNG PHÉP

MỘT — ĐÚNG MỘT NƠI NHẬN. `don_vi_id` hoặc `user_id`, không cả hai, không rỗng cả hai. Ràng buộc duy
nhất ở cơ sở dữ liệu KHÔNG bắt được chuyện này (nó chỉ chặn trùng ô), nên chặn ở đây là chặn duy
nhất.

HAI — TRÙNG Ô. `UniqueConstraint("ky","don_vi_id","user_id","luong")` có hai cột cho rỗng, mà trong
SQL thì RỖNG KHÁC RỖNG: hai dòng cùng kỳ, cùng người, cùng luồng, cả hai `don_vi_id` rỗng vẫn ghi
được cả hai. Nên phép tìm dòng cũ dưới đây là lưới thật, không phải lưới dự phòng.

BA — NƠI NHẬN PHẢI CÓ THẬT VÀ CÒN HIỆU LỰC. Giao chỉ tiêu cho một team đã đóng là một con số không
bao giờ có ai thực hiện, mà nó vẫn cộng vào tổng chỉ tiêu của phòng — tức là phòng ấy vĩnh viễn
không đạt, vì một lý do không ai nhìn ra khi đọc bảng.
"""
from datetime import date, datetime

from sqlalchemy import select

from app.models.chi_tieu_kd import LUONG_CHI_TIEU, ChiTieuKD
from app.models.core import User
from app.models.to_chuc_kd import DonViKD
from app.services import rules as R


def _kiem_ky(ky: str) -> str:
    """'2026-10' hoặc ném ValueError. Không nhận '2026-9' — một chữ số thì sắp xếp chuỗi sai thứ tự."""
    s = (ky or "").strip()
    if len(s) != 7 or s[4] != "-" or not s[:4].isdigit() or not s[5:].isdigit():
        raise ValueError(f"Kỳ không đọc được: {ky!r}. Dạng đúng là 2026-10 (tháng luôn hai chữ số).")
    if not 1 <= int(s[5:]) <= 12:
        raise ValueError(f"Tháng không hợp lệ trong kỳ {ky!r}.")
    return s


def _kiem_noi_nhan(db, don_vi_id: int | None, user_id: int | None, ngay: date):
    """Trả (don_vi, nguoi) — đúng một trong hai khác None. Ném ValueError nếu sai."""
    if (don_vi_id is None) == (user_id is None):
        raise ValueError(
            "Một chỉ tiêu giao cho ĐÚNG MỘT nơi nhận: hoặc một đơn vị, hoặc một người. "
            "Giao cho cả team lẫn từng người trên cùng một dòng thì cộng lên sẽ đếm hai lần.")
    if don_vi_id is not None:
        dv = db.get(DonViKD, don_vi_id)
        if dv is None:
            raise ValueError(f"Không có đơn vị id {don_vi_id}.")
        if not dv.dang_hieu_luc(ngay):
            raise ValueError(
                f"Đơn vị {dv.ten} đã đóng, không giao chỉ tiêu mới được. Một chỉ tiêu giao cho đơn "
                "vị đã đóng là con số không ai thực hiện, mà vẫn cộng vào tổng của phòng cha.")
        return dv, None
    u = db.get(User, user_id)
    if u is None:
        raise ValueError(f"Không có tài khoản id {user_id}.")
    if not u.active:
        raise ValueError(f"Tài khoản {u.username} đang bị khoá, không giao chỉ tiêu được.")
    return None, u


def dat(db, boi: User, ky: str, muc_tieu: float, don_vi_id: int | None = None,
        user_id: int | None = None, luong: str = "tat_ca", ghi_chu: str = "",
        ly_do: str = "") -> ChiTieuKD:
    """Giao chỉ tiêu cho một ô. Ô đã có số thì ĐÈ LÊN dòng cũ, không thêm dòng thứ hai.

    `ly_do` bắt buộc khi đè lên một con số đã có: đổi chỉ tiêu giữa chừng là thứ người ta sẽ hỏi lại
    vào cuối kỳ, và lúc ấy không còn ai nhớ.
    """
    ky = _kiem_ky(ky)
    if luong not in LUONG_CHI_TIEU:
        raise ValueError(f"Luồng không hợp lệ: {luong!r}. Chỉ có {', '.join(LUONG_CHI_TIEU)}.")
    try:
        so = float(muc_tieu)
    except (TypeError, ValueError):
        raise ValueError(f"Mức chỉ tiêu phải là một con số, nhận được {muc_tieu!r}.")
    if so < 0:
        raise ValueError("Chỉ tiêu âm không có nghĩa. Muốn bỏ chỉ tiêu thì xoá ô, đừng đặt số âm.")

    # Ngày xét hiệu lực của nơi nhận là NGÀY CUỐI KỲ, cùng mốc mà `doanh_thu_kd` dùng để xét đơn vị
    # của người bán. Hai nơi xét hai mốc khác nhau thì chỉ tiêu và thực hiện sẽ rơi vào hai đơn vị.
    from calendar import monthrange
    nam, thg = int(ky[:4]), int(ky[5:])
    cuoi_ky = date(nam, thg, monthrange(nam, thg)[1])
    _kiem_noi_nhan(db, don_vi_id, user_id, cuoi_ky)

    cu = db.execute(select(ChiTieuKD).where(
        ChiTieuKD.ky == ky, ChiTieuKD.luong == luong,
        ChiTieuKD.don_vi_id.is_(None) if don_vi_id is None else ChiTieuKD.don_vi_id == don_vi_id,
        ChiTieuKD.user_id.is_(None) if user_id is None else ChiTieuKD.user_id == user_id,
    )).scalars().first()

    if cu is None:
        ct = ChiTieuKD(ky=ky, don_vi_id=don_vi_id, user_id=user_id, luong=luong, muc_tieu=so,
                       ghi_chu=(ghi_chu or "").strip(), nguoi_nhap=boi.username,
                       tao_luc=datetime.now(), sua_luc=datetime.now())
        db.add(ct)
        db.flush()
        R.audit(db, boi.username, boi.role, "dat_chi_tieu_kd", f"chi_tieu_kd:{ct.id}",
                before=None, after=_tom_tat(ct))
        return ct

    if not (ly_do or "").strip():
        raise ValueError(
            f"Ô này đã có chỉ tiêu {cu.muc_tieu:,.0f}. Đè lên một con số đã giao thì phải ghi lý "
            "do — cuối kỳ sẽ có người hỏi vì sao chỉ tiêu đổi, và lúc ấy không còn ai nhớ.")
    truoc = _tom_tat(cu)
    cu.muc_tieu = so
    if (ghi_chu or "").strip():
        cu.ghi_chu = ghi_chu.strip()
    cu.ly_do_sua = ly_do.strip()
    cu.so_lan_sua = (cu.so_lan_sua or 0) + 1
    cu.nguoi_nhap = boi.username
    cu.sua_luc = datetime.now()
    R.audit(db, boi.username, boi.role, "sua_chi_tieu_kd", f"chi_tieu_kd:{cu.id}",
            before=truoc, after=_tom_tat(cu))
    return cu


def xoa(db, boi: User, chi_tieu_id: int, ly_do: str) -> dict:
    """Bỏ hẳn một ô chỉ tiêu. Khác với đặt về 0: 0 nghĩa là "không được giao đồng nào", còn bỏ ô
    nghĩa là "nơi này không nhận chỉ tiêu ở kỳ này". Hai câu khác nhau, màn hình hiện khác nhau."""
    ct = db.get(ChiTieuKD, chi_tieu_id)
    if ct is None:
        raise ValueError(f"Không có dòng chỉ tiêu id {chi_tieu_id}.")
    if not (ly_do or "").strip():
        raise ValueError("Xoá một chỉ tiêu đã giao thì phải ghi lý do.")
    truoc = _tom_tat(ct)
    R.audit(db, boi.username, boi.role, "xoa_chi_tieu_kd", f"chi_tieu_kd:{chi_tieu_id}",
            before=truoc, after={"ly_do": ly_do.strip()})
    db.delete(ct)
    return {"da_xoa": True, "dong": truoc}


def _tom_tat(ct: ChiTieuKD) -> dict:
    return {"id": ct.id, "ky": ct.ky, "don_vi_id": ct.don_vi_id, "user_id": ct.user_id,
            "luong": ct.luong, "muc_tieu": float(ct.muc_tieu or 0),
            "ghi_chu": ct.ghi_chu or "", "so_lan_sua": ct.so_lan_sua or 0,
            "nguoi_nhap": ct.nguoi_nhap or ""}


def danh_sach(db, ky: str, don_vi_ids: list[int] | None = None) -> list[dict]:
    """Mọi chỉ tiêu của kỳ, kèm tên nơi nhận.

    `don_vi_ids` là phạm vi người xem được nhìn. `None` = xem tất cả. DANH SÁCH RỖNG KHÁC `None`:
    rỗng nghĩa là người này chưa được phân công đơn vị nào nên không thấy dòng nào — đừng viết
    `if not don_vi_ids`.
    """
    ky = _kiem_ky(ky)
    ds = list(db.execute(select(ChiTieuKD).where(ChiTieuKD.ky == ky)).scalars())
    ten_dv = {d.id: d for d in db.execute(select(DonViKD)).scalars()}
    ten_ng = {u.id: u for u in db.execute(select(User)).scalars()}

    ra = []
    for ct in ds:
        dv = ten_dv.get(ct.don_vi_id) if ct.don_vi_id else None
        u = ten_ng.get(ct.user_id) if ct.user_id else None
        # Chỉ tiêu của một NGƯỜI thuộc phạm vi nào? Thuộc đơn vị của người ấy. Không tra được đơn vị
        # thì dòng ấy chỉ người xem-toàn-cây mới thấy — để trống thì an toàn hơn đoán.
        thuoc = ct.don_vi_id
        if thuoc is None and u is not None:
            from app.services import to_chuc_kd as TC
            from calendar import monthrange
            nam, thg = int(ky[:4]), int(ky[5:])
            cuoi = date(nam, thg, monthrange(nam, thg)[1])
            d2 = TC.don_vi_cua(db, u.id, cuoi, "le") or TC.don_vi_cua(db, u.id, cuoi, "doan")
            thuoc = d2.id if d2 else None
        if don_vi_ids is not None and (thuoc is None or thuoc not in don_vi_ids):
            continue
        ra.append({**_tom_tat(ct),
                   "nhan_la": ct.nhan_la,
                   "ten_noi_nhan": (dv.ten if dv else (u.full_name if u else "")),
                   "ma_noi_nhan": (dv.ma if dv else (u.username if u else "")),
                   "cap": dv.cap if dv else "",
                   "thuoc_don_vi_id": thuoc})
    return sorted(ra, key=lambda x: (x["nhan_la"], -x["muc_tieu"]))


def tra_cuu(db, ky: str) -> dict:
    """Bảng tra nhanh cho màn hình: {"don_vi": {(id,luong): số}, "nguoi": {(id,luong): số}}.

    Trả về dạng khoá chuỗi `"<id>|<luong>"` để dùng được thẳng trong JSON.
    """
    ky = _kiem_ky(ky)
    ra: dict[str, dict[str, float]] = {"don_vi": {}, "nguoi": {}}
    for ct in db.execute(select(ChiTieuKD).where(ChiTieuKD.ky == ky)).scalars():
        if ct.don_vi_id is not None:
            ra["don_vi"][f"{ct.don_vi_id}|{ct.luong}"] = float(ct.muc_tieu or 0)
        elif ct.user_id is not None:
            ra["nguoi"][f"{ct.user_id}|{ct.luong}"] = float(ct.muc_tieu or 0)
    return ra
