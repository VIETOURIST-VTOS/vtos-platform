# -*- coding: utf-8 -*-
"""HẠN XỬ LÝ cho dòng dòng tiền chưa có nguồn — anh Tuấn chốt 14/9/2026: TRONG VÒNG 24 GIỜ.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO KHÔNG PHẢI LÀ MỘT BẢNG MỚI
═══════════════════════════════════════════════════════════════════════════════════════════════
Trang /dong-tien/nguon vẫn ghi "chưa đặt" ở cột Hạn xử lý vì hệ thống chưa có chỗ nào giữ hạn cho
từng dòng. Phản xạ đầu tiên là dựng một bảng mới. Rà lại kho mã trước khi dựng thì thấy bảng ấy ĐÃ
CÓ: bản nâng cấp KS-4 (11/9/2026) thêm vào `alerts` đúng chín cột của một vòng đời việc phải làm —
`trang_thai`, `nguoi_nhan_id`, `nhan_luc`, `han_xu_ly`, `dong_luc`, `dong_boi_id`, `bang_chung`,
`nguon`, `gom_khoa`.

Dựng bảng thứ hai cho cùng một nghĩa là tự tạo ra hai danh sách việc phải làm: một cái hiện ở chuông,
một cái chỉ hiện ở trang dòng tiền, và không ai biết phải nhìn cái nào. Nên dòng tiền thiếu nguồn đi
vào ĐÚNG sổ cảnh báo đang có, với một loại riêng.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN ĐIỀU TỆP NÀY GIỮ
═══════════════════════════════════════════════════════════════════════════════════════════════

1. HẠN ĐẾM TỪ LÚC PHÁT HIỆN, KHÔNG PHẢI TỪ LÚC MỞ TRANG. Đây là chỗ dễ sai nhất. Nếu hạn là "bây giờ
   + 24 giờ" tính lúc vẽ trang thì một dòng treo cả tuần vẫn hiện "còn 24 giờ" mỗi lần mở — hạn trôi
   theo người xem và KHÔNG BAO GIỜ quá hạn. Nên hạn được GHI XUỐNG một lần, lúc lượt quét đầu tiên
   thấy dòng ấy thiếu, và từ đó không đổi nữa.

2. ĐỌC KHÔNG GHI. `gan_han()` chạy trên đường vẽ màn hình và tuyệt đối không tạo cảnh báo: một cửa
   GET mà đẻ dữ liệu thì số cảnh báo tăng theo số lần người ta bấm F5. Việc sinh hạn là của
   `quet()`, chạy trong lượt quét định kỳ cùng chỗ với mọi cảnh báo khác.

3. CHƯA QUÉT THÌ NÓI CHƯA QUÉT. Dòng đang thiếu mà lượt quét chưa chạy tới thì trả `han_chua_quet`
   và màn hình ghi "chờ lượt quét", KHÔNG bịa ra một hạn tại chỗ. Bịa một hạn là hạn ấy trôi qua mà
   không ai biết mình đã lỡ cái gì — đúng câu đã viết trên trang nguồn số từ vòng TC-25.

4. 24 GIỜ LÀ MỘT THAM SỐ, KHÔNG PHẢI MỘT SỐ GÕ CỨNG. `dong_tien_han_xu_ly_gio` nằm trong sổ tham số,
   nên Chủ tịch đổi được mà không phải sửa mã. Và đổi tham số CHỈ áp cho dòng phát hiện từ lúc ấy trở
   đi: hạn đã ghi cho dòng đang treo giữ nguyên — dời hạn cũ một cách lặng lẽ là xoá mất bằng chứng
   ai đã trễ bao lâu.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Alert, Company
from app.services import khung_dong_tien as KHUNG

# Loại cảnh báo riêng cho dòng tiền thiếu nguồn. Riêng chứ không dùng chung với cảnh báo nghiệp vụ:
# việc ở đây là ĐI ĐÒI MỘT CON SỐ, khác hẳn "chuyến này dưới hoà vốn".
LOAI = "dt_thieu_nguon"

# Ai được báo tin. Đây là `to_roles` — danh sách được XEM, không phải người chịu trách nhiệm (PQ-9
# phân biệt hai thứ ấy). Người phải nhập nằm ở tên bộ phận trong câu thông báo; giao đích danh cho
# một tài khoản là việc của làn Phân quyền khi họ khai xong bảng bộ phận -> người.
BAO_TIN = "ketoan,tgd,chutich,bks"

THAM_SO_HAN = "dong_tien_han_xu_ly_gio"
GIO_MAC_DINH = 24.0          # anh Tuấn chốt 14/9/2026

# Vai dùng cho LƯỢT QUÉT. Lượt quét không phải một người đang xem màn hình, nên nó phải thấy đủ tập
# dòng — cắt theo vai ở đây thì dòng nào Chủ tịch thấy mà vai quét không thấy sẽ không bao giờ có
# hạn. SEC-02 nói về cái người dùng NHẬN ĐƯỢC qua đường mạng, không nói về cái máy chủ tự đọc.
VAI_QUET = "chutich"

_MUC = {KHUNG.CON_THIEU: "red", KHUNG.CHUA_DOI_SOAT: "warn"}


def _bay_gio() -> datetime:
    """Cả kho mã dùng `datetime.now()` không mang múi giờ. Giữ đúng một quy ước — trộn giờ có múi
    với giờ không múi là chỗ phép trừ ra một con số lệch bảy tiếng mà không ai thấy."""
    return datetime.now()


def khoa(company_id: int, ma_dong: str) -> str:
    """`ref` của cảnh báo. Một pháp nhân một dòng một cảnh báo — lượt quét sau tìm đúng dòng này chứ
    không đẻ bản trùng."""
    return f"{company_id}:{ma_dong}"


def _gio_han(db: Session) -> float:
    from app.services.rules import get_param
    try:
        return float(get_param(db, THAM_SO_HAN)) or GIO_MAC_DINH
    except KeyError:
        return GIO_MAC_DINH


def _dang_mo(db: Session, company_id: int) -> dict[str, Alert]:
    """Cảnh báo dòng tiền CÒN MỞ của một pháp nhân, tra theo mã dòng."""
    dau = f"{company_id}:"
    ra: dict[str, Alert] = {}
    for a in db.execute(select(Alert).where(
            Alert.kind == LOAI, Alert.resolved == False,          # noqa: E712
            Alert.ref.like(dau + "%"))).scalars():
        ra[a.ref[len(dau):]] = a
    return ra


def _hien(luc: datetime | None) -> str:
    """Chuỗi ngày giờ do MÁY CHỦ dựng. Trình duyệt chỉ đọc chuỗi, không tự gõ lại định dạng — bài
    học vòng TC-26, khi hai nơi cùng dựng ngày ra "14/09/2026 – 20-09-2026"."""
    return luc.strftime("%d-%m-%Y %H:%M") if luc else ""


def _tre_hien(han: datetime, gio_nay: datetime) -> str:
    giay = (gio_nay - han).total_seconds()
    if giay <= 0:
        return ""
    gio = int(giay // 3600)
    if gio < 24:
        return f"trễ {max(gio, 1)} giờ"
    return f"trễ {gio // 24} ngày"


# ═══════════════════════ PHẦN QUYẾT ĐỊNH — thuần, không chạm cơ sở dữ liệu ═══════════════════════
#
# Hai hàm dưới đây giữ TOÀN BỘ phép quyết định của tệp này, và cố ý không nhận `db`. Một hàm phải mở
# cơ sở dữ liệu mới thử được là một hàm hiếm khi được thử đủ nhánh — và đúng những nhánh hiếm (dòng
# vừa đủ nguồn, dòng đã có hạn, dòng chưa quét tới) mới là chỗ sai nằm im lâu nhất.

MO, DONG, GIU, BO_QUA = "mo", "dong", "giu", "bo_qua"


def quyet_dinh(o: dict, da_co_han: bool) -> str:
    """Lượt quét phải làm gì với một dòng: mở hạn mới · đóng hạn cũ · giữ nguyên · bỏ qua."""
    if o.get("tu_tinh"):
        return BO_QUA                  # dòng tự cộng không có cửa nhập nên không đòi được ai
    if o.get("trang_thai") == KHUNG.DAY_DU:
        return DONG if da_co_han else BO_QUA
    return GIU if da_co_han else MO     # GIU: hạn cũ giữ nguyên — xem điều 1 ở đầu tệp


def _gan(goi: dict, han_theo_ma: dict, gio_nay: datetime, gio_han: float) -> dict:
    """Gắn hạn vào từng dòng của gói. `han_theo_ma` là {mã dòng: datetime hạn}."""
    qua = 0
    for o in goi.get("dong") or []:
        o["han_xu_ly"] = None
        o["han_hien"] = ""
        o["qua_han"] = False
        o["tre_hien"] = ""
        o["han_chua_quet"] = False
        if o.get("tu_tinh") or o.get("trang_thai") == KHUNG.DAY_DU:
            continue
        han = han_theo_ma.get(o["ma"])
        if han is None:
            # Thiếu nguồn nhưng lượt quét chưa chạy tới. Nói thẳng là chưa quét — KHÔNG lấy
            # "bây giờ + 24 giờ" cho có, vì cái hạn ấy sẽ lùi lại mỗi lần mở trang.
            o["han_chua_quet"] = True
            continue
        o["han_xu_ly"] = han.isoformat()
        o["han_hien"] = _hien(han)
        o["qua_han"] = han < gio_nay
        o["tre_hien"] = _tre_hien(han, gio_nay)
        if o["qua_han"]:
            qua += 1

    goi["so_qua_han"] = qua
    goi["gio_han"] = gio_han
    goi["cau_han"] = (
        f"Dòng chưa đủ nguồn phải xong trong {int(gio_han)} giờ kể từ lúc lượt quét phát hiện."
        + (f" Đang có {qua} dòng quá hạn." if qua else "")
    )
    return goi


# ═════════════════════════════ ĐƯỜNG GHI — chạy trong lượt quét ═════════════════════════════

def quet(db: Session) -> int:
    """Mở hạn cho dòng mới thiếu, đóng hạn cho dòng đã đủ nguồn. Trả về số cảnh báo MỚI.

    Gọi từ `rules.run_robots` cùng chỗ với mọi robot cảnh báo khác — không gọi từ cửa GET.
    """
    from app.services import dong_tien as DT

    gio_nay = _bay_gio()
    han = gio_nay + timedelta(hours=_gio_han(db))
    moi = 0

    for c in db.execute(select(Company)).scalars():
        try:
            bang = DT.bang_bon_moc(db, c.id, None)
            sdn = DT.so_du_tung_ngay(db, c.id, None)
        except Exception:
            # Pháp nhân chưa có nền dữ liệu dòng tiền thì KHÔNG sinh hạn. Sinh hạn cho một pháp nhân
            # chưa ai bắt đầu nhập là đẻ ra việc trễ ngay từ ngày đầu — đó là tiếng ồn, không phải
            # thông tin.
            continue

        goi = KHUNG.ghep(VAI_QUET, bang, sdn)
        if not goi.get("xem_duoc"):
            continue

        # DÒ DÒNG ĐANG MỞ — viết THẲNG ở đây chứ không gọi `_dang_mo()`, dù hai chỗ cùng một câu
        # truy vấn. Phép thử VD-4 của bộ KS-4 đọc MÃ NGUỒN: hàm nào dựng `Alert(...)` thì trong
        # CHÍNH hàm ấy phải nhìn thấy câu truy vấn dò trùng. Đẩy phép dò sang một hàm phụ thì người đọc
        # `quet()` không còn thấy nó, và người sửa sau có thể bỏ lời gọi ấy mà không biết mình vừa
        # mở cửa cho mỗi lượt quét đẻ thêm một lượt dòng — 1.703 thành 3.406. CI bắt đúng chỗ này
        # ngày 14/9/2026; phép thử ấy đúng, nên chữa mã chứ không xin miễn trừ.
        dau = f"{c.id}:"
        mo = {a.ref[len(dau):]: a for a in db.execute(select(Alert).where(
            Alert.kind == LOAI, Alert.resolved == False,            # noqa: E712
            Alert.ref.like(dau + "%"))).scalars()}

        for o in goi.get("dong") or []:
            ma = o["ma"]
            cu = mo.get(ma)
            viec = quyet_dinh(o, cu is not None)

            if viec in (BO_QUA, GIU):
                continue

            if viec == DONG:
                cu.resolved = True
                cu.trang_thai = "dong"
                cu.dong_luc = gio_nay
                cu.bang_chung = (cu.bang_chung or "") + \
                    f"Lượt quét {_hien(gio_nay)}: dòng đã có nguồn đầy đủ."
                continue

            bp = o.get("bo_phan") or "bộ phận phụ trách"
            db.add(Alert(
                kind=LOAI,
                level=_MUC.get(o.get("trang_thai"), "warn"),
                ref=khoa(c.id, ma),
                message=f"Dòng tiền “{o.get('ten') or ma}” của {c.code or c.id} chưa đủ nguồn — "
                        f"{bp} phải nhập. {o.get('nguyen_nhan') or ''}".strip(),
                to_roles=BAO_TIN,
                gom_khoa=f"{LOAI}:{khoa(c.id, ma)}",
                han_xu_ly=han,
            ))
            moi += 1

    return moi


# ═════════════════════════════ ĐƯỜNG ĐỌC — chạy khi vẽ màn hình ═════════════════════════════

def gan_han(db: Session, company_id: int, goi: dict) -> dict:
    """Gắn hạn xử lý vào gói đã dựng bởi `KHUNG.ghep`. KHÔNG ghi gì.

    Gắn thêm cho mỗi dòng: `han_xu_ly` (ISO, cho máy) · `han_hien` (chuỗi đọc, cho người) ·
    `qua_han` · `tre_hien` · `han_chua_quet`. Và ở mức gói: `so_qua_han` · `gio_han`.
    """
    if not goi.get("xem_duoc"):
        return goi
    han_theo_ma = {ma: a.han_xu_ly for ma, a in _dang_mo(db, company_id).items()
                   if a.han_xu_ly is not None}
    return _gan(goi, han_theo_ma, _bay_gio(), _gio_han(db))
