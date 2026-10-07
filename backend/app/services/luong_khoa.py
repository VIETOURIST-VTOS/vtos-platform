"""Kiểm cơ sở và khóa kỳ lương. Quy tắc xác định, không phải suy đoán của mô hình ngôn ngữ.

HAI VIỆC TRONG MỘT TỆP, VÌ CHÚNG LÀ HAI ĐẦU CỦA CÙNG MỘT SỢI DÂY:

  · `kiem_co_so` chạy TRƯỚC khi người ký nhìn bảng — nó trả lời "bảng này đủ điều kiện trình chưa".
  · `khoa` chạy ĐÚNG LÚC có chữ ký — nó chụp lại thứ người ấy vừa ký.

Thiếu cái đầu thì người ký nhìn một bảng có thể còn sai. Thiếu cái sau thì chữ ký không gắn vào gì cả.

VÌ SAO KHÔNG ĐỂ MÔ HÌNH NGÔN NGỮ QUYẾT

Chủ tịch gọi bước này là "AI kiểm tra cơ sở". Mã thực hiện nó bằng QUY TẮC XÁC ĐỊNH — cùng đầu vào
luôn ra cùng danh sách cờ, chạy lại được, giải thích được từng dòng. Mô hình ngôn ngữ có thể giải
thích một cờ cho dễ hiểu, nhưng không được là thứ quyết định bảng lương có đi tiếp hay không: một
bộ kiểm mà hôm nay nói đạt hôm mai nói không, với cùng con số, thì không ai dùng để trả tiền.

Nguyên tắc chung của hệ: cờ CHẶN thì chặn, cờ CẢNH BÁO thì cho đi tiếp nhưng ghi lại là đã biết.
Không có cờ KHÔNG có nghĩa là bảng đúng — chỉ nghĩa là những thứ đã biết cách kiểm thì đều sạch.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Param, Tour, User
from app.models.hr import PayrollRun
from app.models.luong_khoa import BangLuongKhoa

# Tham số mà bộ tính lương đọc. Chụp lại đúng những khóa này lúc ký, không chụp cả bảng `params`:
# cả bảng thì bản chụp phình theo thời gian và không ai đọc nổi để so.
#
# THÊM MỘT THAM SỐ MỚI VÀO BỘ TÍNH THÌ PHẢI THÊM VÀO ĐÂY. Phép thử canh danh sách này so với các
# lời gọi `get_param` trong services/hr.py — quên một khóa là bản chụp thiếu căn cứ, mà bản chụp
# thiếu căn cứ còn nguy hơn không chụp: nó trông như đủ.
THAM_SO_LUONG = (
    "bhxh_nld", "cong_chuan", "doan_phi_ty_le", "gd_kd_thuong_50", "gd_kd_thuong_85",
    "hdv_tncn", "hh_doan_moc", "hh_doan_ty_le", "moc_chi_tieu_cantho", "moc_chi_tieu_hcm",
    "moc_luong_doan", "nguong_bien", "phat_su_vu", "ptgd_doan_ty_le", "sale_admin_ty_le",
    "tai_xe_cong_tac_phi", "thang_f_bang", "visa_gui_doi_tac", "visa_lien_minh", "visa_tu_xu_ly",
)

MUC_CO = {"chan": "Chặn trình", "canh_bao": "Cảnh báo – xem rồi vẫn đi tiếp được"}


def _ky_sang_nam_thang(period: str) -> tuple[int, int]:
    y, m = period.split("-")
    return int(y), int(m)


def chup_tham_so(db: Session, period: str) -> dict:
    """Giá trị các tham số lương tại ngày cuối kỳ, kèm ngày hiệu lực của chính dòng được chọn.

    Lưu CẢ ngày hiệu lực chứ không chỉ giá trị: hai kỳ cùng ra 5.000.000 nhưng một kỳ dùng dòng ký
    tháng 3 còn kỳ kia dùng dòng ký tháng 9 là hai câu chuyện khác nhau khi có người hỏi lại.
    """
    y, m = _ky_sang_nam_thang(period)
    cuoi_ky = date(y + (m // 12), (m % 12) + 1, 1)
    ra: dict = {}
    for k in THAM_SO_LUONG:
        dong = [p for p in db.execute(select(Param).where(Param.key == k)).scalars()
                if p.status == "active" and p.effective_from < cuoi_ky]
        dong.sort(key=lambda p: (p.effective_from, p.id))
        if dong:
            p = dong[-1]
            ra[k] = {"gia_tri": p.value, "hieu_luc_tu": str(p.effective_from),
                     "ky_chutich": p.signed_chutich, "ky_tgd": p.signed_tgd}
        else:
            # RỖNG LÀ MỘT CÂU TRẢ LỜI: "kỳ này không có dòng tham số nào hiệu lực". Khác với số 0.
            ra[k] = None
    return ra


def van_tay(noi_dung: dict, quy_tac: dict) -> str:
    """Băm của bản chụp. Bỏ mọi dấu thời gian trước khi băm — xem chú thích `_dau_van_tay` ở hr.py.

    Dùng sha256 chứ không dùng chuỗi JSON thô: vân tay để NGƯỜI KHÁC kiểm lại, và một chuỗi vài trăm
    nghìn ký tự thì không ai dán vào đâu được để so.
    """
    import copy
    sach = copy.deepcopy(noi_dung)
    for r in sach.get("rows") or []:
        xd = r.get("xac_dinh_luong")
        if isinstance(xd, dict):
            xd.pop("snapshot_at", None)
    goi = json.dumps([sach, quy_tac], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def kiem_co_so(db: Session, run: PayrollRun) -> list[dict]:
    """Danh sách cờ của một kỳ. Mỗi cờ: mã, mức, thông điệp, và BẰNG CHỨNG để người xử lý mở ra xem.

    Mỗi cờ phải chỉ được tới một thứ có thật. Một cảnh báo không mở ra được là một cảnh báo người ta
    học cách bỏ qua, và bộ kiểm nào bị bỏ qua quen thì coi như không có.
    """
    from app.services import luong as L

    co: list[dict] = []

    # 1 · Xung đột hồ sơ — một mã dùng cho hai người thì hệ thống không biết trả tiền cho ai.
    for x in L.xung_dot_ho_so(db):
        co.append({"ma": "XUNG_DOT_HO_SO", "muc": "chan",
                   "thong_diep": x.get("thong_diep", "Xung đột hồ sơ nhân sự"), "bang_chung": x})

    # 2 · Tham số: chưa có dòng hiệu lực, hay có mà chưa ai ký.
    #
    #     CẢ HAI ĐỀU LÀ CẢNH BÁO, KHÔNG CHẶN — và đây là một lựa chọn, không phải sự lười.
    #
    #     Chặn là đúng về nguyên tắc: một con số lương dựa trên tham số chưa ai ký là một con số
    #     không ai chịu trách nhiệm. Nhưng bật chặn ngay hôm nay sẽ khóa mọi kỳ lương cho tới khi
    #     có người ngồi ký đủ hai mươi tham số — đó là quyết định về VẬN HÀNH, thuộc về người ký,
    #     không thuộc về làn viết phần mềm. Mã dựng sẵn cái cửa; siết hay không là chữ ký.
    #
    #     Chỗ nguy hiểm nhất là tham số chạy bằng mặc định trong mã: nó chạy êm, không ai thấy gì
    #     bất thường, nên không ai nhớ rằng con số ấy do người lập trình đặt. Cờ này tồn tại để
    #     mỗi kỳ có một dòng nhắc, chứ không để ai đó phát hiện ra sau hai năm.
    for k, v in chup_tham_so(db, run.period).items():
        if v is None:
            co.append({"ma": "THAM_SO_CHAY_MAC_DINH", "muc": "canh_bao",
                       "thong_diep": f"Tham số '{k}' chưa có dòng nào hiệu lực trong kỳ {run.period} – "
                                     f"đang chạy bằng mặc định trong mã, mà mặc định thì không ai ký",
                       "bang_chung": {"tham_so": k}})
        elif not (v["ky_chutich"] or v["ky_tgd"]):
            co.append({"ma": "THAM_SO_CHUA_KY", "muc": "canh_bao",
                       "thong_diep": f"Tham số '{k}' đang dùng nhưng chưa có chữ ký Chủ tịch hoặc TGĐ",
                       "bang_chung": {"tham_so": k, "hieu_luc_tu": v["hieu_luc_tu"]}})

    # 3 · Khoản treo — hoa hồng và thưởng chuyến chưa chốt quyết toán. KHÔNG chặn: chuyến chưa chốt
    #     là chuyện bình thường giữa kỳ. Nhưng phải nói ra, vì đây là chỗ người lao động mất tiền mà
    #     không ai phát hiện: khoản treo không hiện trên phiếu lương nào.
    try:
        treo = L.khoan_treo(db)
        n = len(treo.get("dong") or []) if isinstance(treo, dict) else 0
        if n:
            co.append({"ma": "KHOAN_TREO", "muc": "canh_bao",
                       "thong_diep": f"Có {n} khoản hoa hồng/thưởng đang treo vì chuyến chưa chốt quyết toán",
                       "bang_chung": {"so_khoan": n}})
    except Exception:
        pass

    # 4 · Dòng lương âm hoặc rỗng thực nhận. Số âm không tự nó sai, nhưng nó phải có người nhìn.
    for r in run.rows or []:
        tn = r.get("thuc_nhan")
        if tn is None:
            co.append({"ma": "THUC_NHAN_RONG", "muc": "chan",
                       "thong_diep": f"{r.get('ma')} – chưa tính được thực nhận; rỗng KHÔNG phải số 0",
                       "bang_chung": {"ma_nv": r.get("ma")}})
        elif float(tn) < 0:
            co.append({"ma": "THUC_NHAN_AM", "muc": "canh_bao",
                       "thong_diep": f"{r.get('ma')} – thực nhận âm {tn:,.0f}; cần người xác nhận trước khi trình",
                       "bang_chung": {"ma_nv": r.get("ma"), "thuc_nhan": tn}})

    # 5 · Chống trùng thu nhập liên phòng, liên kỳ. Ba phép, xem services/thu_nhap_su_kien.py.
    from app.services import thu_nhap_su_kien as TN
    co.extend(TN.kiem_trung(db, run.period, run.rows or []))

    return co


def co_chan(co: list[dict]) -> list[dict]:
    return [c for c in co if c["muc"] == "chan"]


def ban_dang_hieu_luc(db: Session, period: str) -> BangLuongKhoa | None:
    for b in db.execute(select(BangLuongKhoa).where(BangLuongKhoa.period == period)
                        .order_by(BangLuongKhoa.ban_so.desc())).scalars():
        if b.bi_thay_boi is None:
            return b
    return None


def khoa(db: Session, run: PayrollRun, u: User) -> BangLuongKhoa:
    """Chụp bản khóa tại lúc ký. Gọi TRONG cùng giao dịch với việc đổi trạng thái, không gọi sau."""
    cu = db.execute(select(BangLuongKhoa).where(BangLuongKhoa.period == run.period)
                    .order_by(BangLuongKhoa.ban_so.desc())).scalars().first()
    ban_so = (cu.ban_so + 1) if cu else 1
    noi_dung = {"rows": run.rows or [], "totals": run.totals or {}}
    quy_tac = chup_tham_so(db, run.period)
    b = BangLuongKhoa(period=run.period, ban_so=ban_so, noi_dung=noi_dung, quy_tac=quy_tac,
                      dau_van_tay=van_tay(noi_dung, quy_tac),
                      khoa_boi=u.username, khoa_vai=u.role, khoa_luc=datetime.now())
    db.add(b)
    db.flush()
    # Ghi sổ sự kiện thu nhập TRONG CÙNG GIAO DỊCH với bản khóa. Tách ra một bước sau nghĩa là có
    # một khoảnh khắc kỳ đã ký mà sổ chưa ghi, và mọi lần hỏng đều rơi đúng vào khoảnh khắc ấy.
    from app.services import thu_nhap_su_kien as TN
    TN.ghi_so(db, run.period, run.rows or [], ban_khoa_id=b.id)
    return b


def doi_chieu_voi_ban_khoa(db: Session, run: PayrollRun) -> dict:
    """Tính lại HÔM NAY rồi so với bản đã khóa. KHÔNG ghi đè gì — đây là phép đọc.

    Đây là câu trả lời cho "cùng snapshot có ra cùng kết quả không". Lệch nghĩa là có thứ đã đổi sau
    lưng kỳ ấy: tham số, hồ sơ nhân sự, hoặc quyết toán một chuyến. Lệch KHÔNG tự động là sai — nhưng
    nó phải hiện ra chứ không được im.
    """
    b = ban_dang_hieu_luc(db, run.period)
    if b is None:
        return {"co_ban_khoa": False, "thong_diep": "Kỳ này chưa có bản khóa nào"}
    from app.services.hr import compute_draft
    rows, totals = compute_draft(db, run.period, run.inputs or {})
    nay = van_tay({"rows": rows, "totals": totals}, chup_tham_so(db, run.period))
    khop = nay == b.dau_van_tay
    return {"co_ban_khoa": True, "ban_so": b.ban_so, "khoa_luc": b.khoa_luc,
            "van_tay_da_khoa": b.dau_van_tay, "van_tay_tinh_lai": nay, "khop": khop,
            "thong_diep": ("Tính lại ra đúng con số đã ký" if khop else
                           "LỆCH – có thứ đã đổi sau khi ký. Số đã ký vẫn là số có hiệu lực; "
                           "muốn đổi phải mở kỳ và ký lại.")}
