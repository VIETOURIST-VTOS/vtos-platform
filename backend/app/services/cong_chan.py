"""Cổng chặn giá vốn: chưa có giá vốn thì không ghi doanh thu.

Quyết định của Chủ tịch ngày 08/9/2026: MỌI đơn đều có doanh thu và giá vốn – tour trọn gói,
tour gom khách lẻ, visa, vé máy bay, gia hạn visa, land. Công ty là bên chính, thu hộ chi hộ và
ăn phần chênh lệch. Vì vậy "giá vốn bằng 0" không bao giờ là một bản chất nghiệp vụ khác; nó là
một ô dữ liệu chưa ai điền.

Hệ quả lập trình, và đây là lý do tồn tại của tệp này: nếu vẫn ghi doanh thu cho đơn thiếu giá vốn
thì sổ có 100% lãi trên đơn đó, lãi gộp toàn công ty bị thổi lên, và không ai nhìn thấy vì con số
vẫn "chạy được". Nên đơn thiếu giá vốn bị GIỮ LẠI ở hàng đợi, không được sinh bút toán doanh thu,
và đứng tên một phòng ban cụ thể cho tới khi phòng đó nhập đủ.

Số thật đo được trên quyết toán T7–T8/2026: 76 dòng thiếu giá vốn, tổng doanh thu 2.654.940.111đ.
"""
from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, User
from app.models.hach_toan import ThieuGiaVon
from app.services import rules as R

LY_DO = {
    "thieu_gia_von": "Có doanh thu, chưa có giá vốn",
    "gia_von_am": "Giá vốn âm",
    "lai_bat_thuong": "Giá vốn quá nhỏ so với doanh thu – biên trên 60%, gần như chắc chắn thiếu dòng chi phí",
    "thieu_dien_giai": "Không đọc được đơn này là dịch vụ gì",
}
TRANG_THAI = {"cho": "Chờ Điều hành bổ sung", "da_bo_sung": "Đã bổ sung đủ", "bo_qua": "Đã xử lý ngoài hệ thống"}

# Biên trên ngưỡng này ở một đơn lữ hành gần như luôn là thiếu dòng chi phí, không phải lãi thật.
BIEN_NGO = 0.60


def _ly_do(dt: float, gv: float, ten: str) -> str:
    if gv < 0:
        return "gia_von_am"
    if dt > 0 and gv <= 0:
        return "thieu_gia_von"
    if dt > 0 and (dt - gv) / dt > BIEN_NGO:
        return "lai_bat_thuong"
    if len((ten or "").strip()) < 5:
        return "thieu_dien_giai"
    return ""


def kiem_tra(t: Tour) -> str:
    """Trả mã lý do nếu đơn KHÔNG được ghi doanh thu, chuỗi rỗng nếu qua cổng."""
    dt = float(t.actual_revenue or 0)
    gv = float(t.actual_cost or 0)
    if dt <= 0:
        return ""          # chưa có doanh thu thì chưa đến lượt cổng này
    return _ly_do(dt, gv, t.name)


def chan(t: Tour) -> None:
    """Gọi ngay trước khi sinh bút toán doanh thu. Không qua cổng thì ném lỗi – không ghi nửa vời."""
    ld = kiem_tra(t)
    if ld:
        raise ValueError(f"{t.code}: {LY_DO[ld]} – không ghi doanh thu cho tới khi Điều hành nhập đủ giá vốn")


def quet(db: Session, ky: str = "") -> dict:
    """Quét toàn bộ đơn đã kết thúc, đưa đơn không qua cổng vào hàng đợi.

    Chạy lại được: đơn đã bổ sung đủ thì đóng lại chứ không xóa – giữ dấu vết là nó từng thiếu.
    """
    cu = {r.ma_don: r for r in db.execute(select(ThieuGiaVon)).scalars()}
    them, dong, con = 0, 0, 0
    q = select(Tour).where(Tour.status.in_(["ket_thuc", "da_duyet"]))
    for t in db.execute(q).scalars():
        dt = float(t.actual_revenue or 0)
        if dt <= 0:
            continue
        ld = kiem_tra(t)
        r = cu.get(t.code)
        if not ld:
            if r is not None and r.trang_thai == "cho":
                r.trang_thai, r.xu_ly_luc = "da_bo_sung", datetime.now()
                r.gia_von = float(t.actual_cost or 0)
                dong += 1
            continue
        kyt = f"{t.end_date:%Y-%m}" if t.end_date else ""
        if ky and kyt != ky:
            continue
        nguoi = ""
        if t.operator_id:
            o = db.get(User, t.operator_id)
            nguoi = f"{o.full_name} ({o.username})" if o else ""
        if r is None:
            db.add(ThieuGiaVon(ma_don=t.code, ky=kyt, ten=t.name or "", doanh_thu=dt,
                               gia_von=float(t.actual_cost or 0), ly_do=ld,
                               phong_ban="dieu_hanh", nguoi_phu_trach=nguoi))
            them += 1
        else:
            r.doanh_thu, r.gia_von, r.ly_do, r.ten = dt, float(t.actual_cost or 0), ld, t.name or ""
            if r.nguoi_phu_trach != nguoi and nguoi:
                r.nguoi_phu_trach = nguoi
            if r.trang_thai == "cho":
                con += 1
    db.commit()
    return {"them": them, "da_bo_sung": dong, "con_cho": con}


def danh_sach(db: Session, trang_thai: str = "cho", ky: str = "", ly_do: str = "") -> dict:
    q = select(ThieuGiaVon)
    if trang_thai:
        q = q.where(ThieuGiaVon.trang_thai == trang_thai)
    if ky:
        q = q.where(ThieuGiaVon.ky == ky)
    if ly_do:
        q = q.where(ThieuGiaVon.ly_do == ly_do)
    rows = db.execute(q).scalars().all()
    rows.sort(key=lambda r: (-float(r.doanh_thu or 0),))
    tong = sum(float(r.doanh_thu or 0) for r in rows)
    theo_ly_do: dict[str, dict] = {}
    for r in rows:
        o = theo_ly_do.setdefault(r.ly_do, {"ten": LY_DO.get(r.ly_do, r.ly_do), "so_don": 0, "doanh_thu": 0.0})
        o["so_don"] += 1
        o["doanh_thu"] += float(r.doanh_thu or 0)
    return {
        "ly_do": LY_DO, "trang_thai": TRANG_THAI,
        "tong_so_don": len(rows), "tong_doanh_thu": tong, "theo_ly_do": theo_ly_do,
        "rows": [{"id": r.id, "ma_don": r.ma_don, "ky": r.ky, "ten": r.ten,
                  "doanh_thu": float(r.doanh_thu or 0), "gia_von": float(r.gia_von or 0),
                  "ly_do": r.ly_do, "ly_do_ten": LY_DO.get(r.ly_do, r.ly_do),
                  "phong_ban": r.phong_ban, "nguoi_phu_trach": r.nguoi_phu_trach,
                  "trang_thai": r.trang_thai, "giai_trinh": r.giai_trinh,
                  "nguoi_xu_ly": r.nguoi_xu_ly, "xu_ly_luc": r.xu_ly_luc,
                  "phat_hien_luc": r.phat_hien_luc,
                  "duong_dan": f"/tours?q={r.ma_don}"} for r in rows],
    }


def bo_qua(db: Session, u: User, ma_don: str, giai_trinh: str) -> ThieuGiaVon:
    """Đóng một dòng mà KHÔNG bổ sung giá vốn. Phải nêu lý do – và việc này đi vào nhật ký bất biến,
    vì đây chính là lúc một đơn được cho qua cổng bằng tay."""
    r = db.execute(select(ThieuGiaVon).where(ThieuGiaVon.ma_don == ma_don)).scalars().first()
    if r is None:
        raise ValueError(f"Không có đơn {ma_don} trong hàng đợi")
    if r.trang_thai != "cho":
        raise ValueError("Dòng này đã xử lý")
    if len((giai_trinh or "").strip()) < 20:
        raise ValueError("Phải ghi rõ vì sao đơn này không cần giá vốn (ít nhất 20 ký tự)")
    r.trang_thai, r.giai_trinh = "bo_qua", giai_trinh.strip()
    r.nguoi_xu_ly, r.xu_ly_luc = u.username, datetime.now()
    R.audit(db, u.username, u.role, "bo_qua_cong_gia_von", f"tour:{ma_don}",
            after={"doanh_thu": float(r.doanh_thu or 0), "ly_do": r.ly_do, "giai_trinh": r.giai_trinh})
    db.commit()
    return r


def ngoai_le(db: Session) -> list[dict]:
    """Đưa hàng đợi này lên màn hình Ngoại lệ cần xử lý – không dựng hàng đợi thứ hai cho phòng ban."""
    ra = []
    for r in db.execute(select(ThieuGiaVon).where(ThieuGiaVon.trang_thai == "cho")).scalars():
        ra.append({"ma": f"thieu_gia_von#{r.ma_don}", "loai": "thieu_gia_von", "muc": "do",
                   "luc": r.phat_hien_luc or datetime.now(), "doi_tuong": f"tour:{r.ma_don}",
                   "nguoi_quyet": "", "ly_do": "",
                   "tom_tat": f"{r.ma_don} – {LY_DO.get(r.ly_do, r.ly_do)}, doanh thu {float(r.doanh_thu or 0):,.0f}đ",
                   "duong_dan": f"/hach-toan?tab=thieu-gia-von&q={r.ma_don}"})
    return ra

# ============================ CỔNG ĐÁO HẠN ============================
# Đáo hạn ngân hàng là hai nghiệp vụ, không phải một: trả gốc khoản cũ, rồi nhận giải ngân khoản mới.
# Cái sai của đáo hạn không nằm ở định khoản – hai chân đều đơn giản. Nó nằm ở chỗ BÙ TRỪ hai chân lại
# thành một dòng cho gọn. Khi đó dư nợ vay trên sổ không bao giờ đứng ở đỉnh, và dòng tiền mất hẳn một
# vòng ra rồi vào. Với công ty đại chúng thì cả hai con số đó đều là con số công bố.
#
# Cách nối hai chân: cả hai chứng từ mang cùng một source_ref "dao_han:<mã>". Thiếu một chân là ngoại lệ.
CHAN_DAO_HAN = {"VAY_TRA_GOC": "tra_goc", "VAY_NHAN": "nhan_moi"}


def dao_han_thieu_chan(db: Session) -> list[dict]:
    """Tìm những lần đáo hạn chỉ ghi một chân. Đọc thẳng từ chứng từ, không dựng bảng thứ hai."""
    from app.models.accounting import JournalEntry, JournalLine
    ra = []
    rows = db.execute(select(JournalEntry).where(JournalEntry.source_ref.like("dao_han:%"),
                                                 JournalEntry.status == "da_ghi_so")).scalars().all()
    theo_ma: dict[str, list] = {}
    for e in rows:
        theo_ma.setdefault(e.source_ref.split(":", 1)[1], []).append(e)
    for ma, es in theo_ma.items():
        co_tra = any(any(l.account_code.startswith("341") and l.debit for l in e.lines) for e in es)
        co_nhan = any(any(l.account_code.startswith("341") and l.credit for l in e.lines) for e in es)
        if co_tra and co_nhan:
            continue
        thieu = "nhận giải ngân khoản mới" if co_tra else "trả gốc khoản cũ"
        so = max((sum(l.debit + l.credit for l in e.lines) for e in es), default=0) / 2
        ra.append({"ma": f"dao_han_thieu_chan#{ma}", "loai": "dao_han_thieu_chan", "muc": "do",
                   "luc": min(e.created_at for e in es), "doi_tuong": f"dao_han:{ma}",
                   "nguoi_quyet": "", "ly_do": "",
                   "tom_tat": f"Đáo hạn {ma} mới ghi một chân, thiếu chân {thieu} – khoảng {so:,.0f}đ",
                   "duong_dan": f"/accounting?tab=journal&q=dao_han:{ma}"})
    return ra
