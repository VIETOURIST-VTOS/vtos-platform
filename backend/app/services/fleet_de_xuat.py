# -*- coding: utf-8 -*-
"""Tuyến duyệt đề xuất chi đội xe — ai được làm bước nào, và vì sao người lập không duyệt được.

Bản vẽ v3.3 §3 và §7. Mã nguồn của bảng ở `app/models/fleet_de_xuat.py`; tệp này chỉ giữ LUẬT.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN LUẬT, VÀ LÝ DO CỦA TỪNG LUẬT
═══════════════════════════════════════════════════════════════════════════════════════════════

**1 · NGƯỜI LẬP KHÔNG ĐƯỢC KIỂM, DUYỆT HAY THANH TOÁN PHIẾU CỦA MÌNH.**

v3.3 §7 và chính bản vẽ ghi: *"Không tự duyệt đề nghị của mình hoặc xác nhận đã thanh toán"*.

Chỗ dễ làm sai: chặn bằng VAI là không đủ. Một người có cả vai lập và vai duyệt — chuyện thật, vì
`cntt` và `chutich` đều nằm trong nhiều tuyến — thì hàng rào vai cho qua. Nên hàng rào thật là
`nguoi_lap != người đang bấm`, xét theo TÀI KHOẢN, ở `co_the()`.

Và nó chặn cả Chủ tịch. Không có ngoại lệ cho người cao nhất, vì ngoại lệ ấy là ngoại lệ mà mọi
phiếu sẽ đi qua vào đúng ngày gấp.

**2 · HẠN MỨC ĐỊNH TUYẾN, NHƯNG HẠN MỨC LÀ THAM SỐ.**

Khoản dưới hạn mức: Kế toán trưởng duyệt được. Từ hạn mức trở lên: phải TGĐ hoặc Chủ tịch.

Con số nằm ở tham số `xe_de_xuat_han_muc_tgd`, không nằm trong mã nguồn — đổi hạn mức là việc có
người ký, không phải việc triển khai lại phần mềm. Cùng lẽ ấy, `xe_de_xuat_nguoi_kiem_tra` và
`xe_de_xuat_nguoi_duyet` nhận danh sách tài khoản để siết hẹp hơn vai; **để trống là đi theo vai**,
chứ không phải là chặn hết. Để trống mà chặn hết thì ngày phát hành không ai làm được gì và cả
luồng bị tắt bằng một ô chưa khai.

**3 · `cntt` KHÔNG DUYỆT VÀ KHÔNG THANH TOÁN ĐƯỢC.**

Khác với phần lớn cửa ghi của VTOS, nơi `cntt` đứng cùng vai nghiệp vụ để còn sửa được dữ liệu.
Ở đây `cntt` chỉ ĐỌC và chỉ sửa được phiếu nháp của chính mình. Lý do: vai kỹ thuật tồn tại để hệ
thống chạy được, không để phê duyệt tiền ra. Mở cho `cntt` một lần là mở vĩnh viễn một đường duyệt
không ai nhìn.

Hệ quả phải nói ra: ngày chạy thử, người cầm `cntt` KHÔNG tự chạy hết một vòng được — phải có một
tài khoản vai duyệt thật bấm. Đó là chi phí có chủ ý.

**4 · TRẢ BỔ SUNG PHẢI CÓ LÝ DO, VÀ LƯU BẢN CHỤP PHIẾU LÚC BỊ TRẢ.**

Trả lại mà không ghi vì sao thì người lập chỉ thấy phiếu quay về, và lần gửi thứ hai cũng sai y
như lần đầu. Bản chụp nằm ở `FleetDeXuatLog.noi_dung_truoc` — xem chú thích đầu tệp mô hình.
"""
import json
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.attachments import Attachment
from app.models.fleet import TripCost
from app.models.fleet_de_xuat import (FleetDeXuat, FleetDeXuatLog, TRANG_THAI, KHEP,
                                      CON_SUA_DUOC, LOAI, NHOM_KHOAN, CAN_CU_THUE)
from app.models.hr import Vehicle
from app.models.suppliers import Supplier
from app.services import rules as R

# Mã đối tượng trong kho tệp chung — **dùng lại đúng mã KS-64 đã khai**, không khai mã thứ hai.
#
# KS-64 (09/11/2026) đã thêm `"de_xuat_chi_xe": ("Đề xuất chi đội xe", "doi_xe", "02_Ke_toan", True)`
# vào `attachments.DOI_TUONG_DAY_DU` cùng ô đính kèm ở `components/doixe/BonBuocDeXuatChi.tsx`. Nên
# vòng này KHÔNG đụng vào `attachments.py`: thêm một mã riêng cho phiếu bảy bước là chia tệp của
# cùng một khoản tiền thành hai kho, và lúc người duyệt mở phiếu ra thì nửa số chứng từ nằm ở mã
# kia. `so_tep()` dưới đây đếm đúng những tệp cửa bốn bước đã gắn.
DOI_TUONG_TEP = "de_xuat_chi_xe"

# ── Vai theo từng bước. Khai một chỗ; cửa API đọc vào chứ không khai lần thứ hai.
VAI_LAP = ("gd_doi_xe", "cntt")
VAI_KIEM_TRA = ("tp_dh", "nv_dh", "ketoan", "kt_truong")
VAI_DUYET_THUONG = ("kt_truong", "tgd", "chutich")
VAI_DUYET_LON = ("tgd", "chutich")          # từ hạn mức trở lên — xem luật 2 đầu tệp
VAI_THANH_TOAN = ("ketoan", "kt_truong")
VAI_DOI_SOAT = ("ketoan", "kt_truong")
# Đọc được sổ: mọi vai trong tuyến, cộng vai xem báo cáo đội xe.
VAI_XEM = tuple(sorted(set(VAI_LAP + VAI_KIEM_TRA + VAI_DUYET_THUONG + VAI_THANH_TOAN
                           + ("tp_hd", "tgd", "chutich"))))

# ── Bảng chuyển bước: hành động → (các trạng thái được phép bấm, trạng thái sau).
# "da_tt" là trạng thái SUY RA từ số tiền đã trả, nên `thanh_toan` không có đích cố định.
CHUYEN = {
    "gui":        (("nhap", "tra_bo_sung"), "cho_kiem_tra"),
    "kiem_tra":   (("cho_kiem_tra",), "cho_duyet"),
    "duyet":      (("cho_duyet",), "da_duyet"),
    "tra":        (("cho_kiem_tra", "cho_duyet"), "tra_bo_sung"),
    "thanh_toan": (("da_duyet", "da_tt_mot_phan"), None),
    "doi_soat":   (("da_tt",), "da_doi_soat"),
    "huy":        (("nhap", "tra_bo_sung", "cho_kiem_tra", "cho_duyet", "da_duyet"), "huy"),
}
# Hành động nào cần lý do bằng chữ. Trả lại và hủy một khoản tiền là hai việc người sau sẽ hỏi.
CAN_LY_DO = ("tra", "huy")


def _ds(db: Session, khoa: str) -> tuple[str, ...]:
    """Danh sách tài khoản trong một tham số chữ. Rỗng = chưa siết, đi theo vai (luật 2)."""
    try:
        raw = R.get_param_text(db, khoa)
    except KeyError:
        return ()
    return tuple(x.strip() for x in (raw or "").split(",") if x.strip())


def han_muc(db: Session) -> float:
    try:
        return R.get_param(db, "xe_de_xuat_han_muc_tgd")
    except KeyError:
        return 0.0


def _nguong_chung_tu(db: Session) -> float:
    """Ngưỡng tiền bắt buộc có chứng từ gốc — chặn cứng B6, dùng chung với chi phí chuyến."""
    try:
        return R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    except KeyError:
        return 0.0


def vai_duyet(db: Session, so_tien: float | None) -> tuple[str, ...]:
    """Vai được duyệt một khoản bao nhiêu tiền.

    `so_tien` rỗng thì trả về tuyến NGHIÊM hơn, không trả tuyến thường. Chưa biết số tiền mà cho
    tuyến nhẹ là để một phiếu chưa điền tiền đi qua cửa dễ rồi mới điền tiền vào — đúng cái lỗ mà
    hạn mức sinh ra để bịt.
    """
    hm = han_muc(db)
    if so_tien is None:
        return VAI_DUYET_LON
    return VAI_DUYET_LON if (hm and float(so_tien) >= hm) else VAI_DUYET_THUONG


def co_the(db: Session, p: FleetDeXuat, hanh_dong: str, tai_khoan: str, vai: str) -> str:
    """Trả về "" nếu được làm; nếu không, trả về CÂU GIẢI THÍCH cho người đọc.

    Trả câu chữ chứ không trả False: màn hình phải in được VÌ SAO nút mờ. Nút mờ không lý do là
    thứ người dùng sẽ gọi điện hỏi, và câu trả lời sẽ là một người đoán hộ một người.
    """
    if hanh_dong not in CHUYEN:
        return f"Không có hành động «{hanh_dong}»"
    duoc, _ = CHUYEN[hanh_dong]
    if p.trang_thai in KHEP:
        return f"Phiếu đã {TRANG_THAI[p.trang_thai].lower()} — không chuyển bước nữa"
    if p.trang_thai not in duoc:
        return (f"Phiếu đang ở «{TRANG_THAI.get(p.trang_thai, p.trang_thai)}», "
                f"bước này chỉ bấm được khi phiếu ở "
                + " hoặc ".join(f"«{TRANG_THAI[t]}»" for t in duoc))

    # Luật 1 — người lập không kiểm, không duyệt, không thanh toán phiếu của mình. Không trừ ai.
    if hanh_dong in ("kiem_tra", "duyet", "thanh_toan", "doi_soat") and tai_khoan == (p.nguoi_lap or ""):
        return ("Người lập phiếu không kiểm, duyệt hay thanh toán phiếu của chính mình "
                "(v3.3 §7). Chuyển cho người có quyền trong tuyến.")

    if hanh_dong in ("gui", "huy"):
        # Gửi và hủy là việc của người lập. Người khác trong tuyến hủy được khi phiếu đã rời tay
        # người lập — vì lúc ấy người lập không còn sửa được nữa, mà phiếu sai thì phải đóng lại.
        if tai_khoan == (p.nguoi_lap or "") or vai in VAI_LAP:
            return ""
        if hanh_dong == "huy" and vai in (VAI_KIEM_TRA + VAI_DUYET_THUONG):
            return ""
        return "Chỉ người lập phiếu (hoặc vai Giám đốc đội xe) gửi được phiếu này"

    if hanh_dong == "kiem_tra":
        ds = _ds(db, "xe_de_xuat_nguoi_kiem_tra")
        if ds and tai_khoan not in ds:
            return "Tài khoản của bạn không nằm trong danh sách người kiểm tra đã khai (tham số xe_de_xuat_nguoi_kiem_tra)"
        return "" if vai in VAI_KIEM_TRA else "Vai của bạn không kiểm tra được đề xuất chi đội xe"

    if hanh_dong == "duyet":
        ds = _ds(db, "xe_de_xuat_nguoi_duyet")
        if ds and tai_khoan not in ds:
            return "Tài khoản của bạn không nằm trong danh sách người duyệt đã khai (tham số xe_de_xuat_nguoi_duyet)"
        vd = vai_duyet(db, p.so_tien)
        if vai in vd:
            return ""
        hm = han_muc(db)
        if hm and (p.so_tien or 0) >= hm:
            return (f"Khoản từ {hm:,.0f} đ trở lên phải do Tổng giám đốc hoặc Chủ tịch duyệt "
                    f"(hạn mức ở tham số xe_de_xuat_han_muc_tgd)")
        return "Vai của bạn không duyệt được đề xuất chi đội xe"

    if hanh_dong == "tra":
        return "" if vai in (VAI_KIEM_TRA + VAI_DUYET_THUONG) else "Vai của bạn không trả bổ sung được phiếu này"
    if hanh_dong == "thanh_toan":
        return "" if vai in VAI_THANH_TOAN else "Chỉ Kế toán thực hiện thanh toán"
    if hanh_dong == "doi_soat":
        return "" if vai in VAI_DOI_SOAT else "Chỉ Kế toán đối soát khép phiếu"
    return ""


def so_tep(db: Session, p: FleetDeXuat) -> int:
    return int(db.execute(select(func.count(Attachment.id)).where(
        Attachment.doi_tuong == DOI_TUONG_TEP,
        Attachment.doi_tuong_id == str(p.id))).scalar() or 0)


def kiem(db: Session, p: FleetDeXuat, buoc: int = 3) -> list[str]:
    """Những chỗ còn thiếu, theo đúng từng bước của bản vẽ. Danh sách rỗng = đủ để đi tiếp.

    Cùng một hàm dùng cho CẢ giao diện (hiện ô đỏ) và cửa API (chặn). Hai bộ luật riêng cho hai nơi
    là cách chắc chắn để màn hình nói "đủ rồi" mà máy chủ trả 422.
    """
    loi: list[str] = []
    if buoc >= 0:
        if p.pham_vi not in ("xe", "doi"):
            loi.append("Chọn phạm vi khoản chi: một xe hay toàn đội.")
        elif p.pham_vi == "xe":
            v = db.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
            if v is None or not v.active:
                loi.append("Chọn một xe thuộc phạm vi đang khai thác.")
        if p.loai not in LOAI:
            loi.append("Chọn loại đề nghị: thanh toán, tạm ứng hay hoàn ứng.")
        if p.nhom not in NHOM_KHOAN:
            loi.append("Chọn nhóm khoản.")
        if not (p.noi_dung or "").strip():
            loi.append("Nhập nội dung và căn cứ đề nghị.")
        if not p.supplier_id and not (p.ben_nhan_de_nghi or "").strip():
            loi.append("Nhập bên nhận / nhà cung cấp.")
    if buoc >= 1:
        t = p.so_tien
        if t is None or float(t) <= 0 or float(t) != int(float(t)):
            loi.append("Số tiền đề nghị phải là số nguyên đồng lớn hơn 0.")
        if p.ngay_can is None:
            loi.append("Nhập ngày cần xử lý.")
        if p.can_cu_thue not in CAN_CU_THUE:
            loi.append("Chọn căn cứ số tiền và thuế / phí.")
        if not (p.so_chung_tu or "").strip() and not p.hen_bo_sung and not so_tep(db, p):
            loi.append("Bổ sung chứng từ hoặc ghi lý do sẽ bổ sung sau.")
        if p.hen_bo_sung and not (p.ly_do_bo_sung or "").strip():
            loi.append("Nhập lý do và thời hạn bổ sung chứng từ.")
    if buoc >= 3:
        # Chỉ lúc GỬI mới bắt buộc bên nhận phải CÓ TRONG DANH MỤC — xem luật 1 của tệp mô hình.
        if not p.supplier_id:
            loi.append("Bên nhận phải chọn từ danh mục nhà cung cấp trước khi gửi. Bên nhận chưa "
                       "có trong danh mục thì nhờ Kế toán thêm vào — thông tin ngân hàng do Kế "
                       "toán kiểm soát, không nhập ở màn này.")
        elif db.get(Supplier, p.supplier_id) is None:
            loi.append("Nhà cung cấp đã chọn không còn trong danh mục.")
        nguong = _nguong_chung_tu(db)
        if nguong and (p.so_tien or 0) >= nguong and not (p.so_chung_tu or "").strip() and not so_tep(db, p):
            loi.append(f"Khoản từ {nguong:,.0f} đ bắt buộc có số chứng từ gốc hoặc tệp đính kèm "
                       f"(chặn cứng B6) — lời hẹn bổ sung không thay được ở mức tiền này.")
    return loi


def kiem_trung(db: Session, p: FleetDeXuat) -> list[str]:
    """Cảnh báo phiếu có thể đã ghi nhận ở chỗ khác (WF06). CẢNH BÁO, không chặn.

    Vì sao không chặn: hai đề nghị cùng số chứng từ có thể là việc thật — một hoá đơn trả hai lần
    theo tiến độ. Chặn cứng thì người lập sẽ đổi một chữ trong số chứng từ để đi qua, và lúc ấy
    hệ thống mất luôn cả manh mối. Nói ra và để người quyết thì manh mối còn nguyên trong nhật ký.
    """
    cb: list[str] = []
    song = [t for t in TRANG_THAI if t not in KHEP]
    if p.trip_cost_id:
        k = db.execute(select(FleetDeXuat).where(
            FleetDeXuat.id != p.id, FleetDeXuat.trip_cost_id == p.trip_cost_id,
            FleetDeXuat.trang_thai.in_(song))).scalars().first()
        if k is not None:
            cb.append(f"Khoản chi gốc này đã có phiếu {k.ma_phieu} ({TRANG_THAI[k.trang_thai]}).")
        c = db.get(TripCost, p.trip_cost_id)
        if c is not None:
            cb.append(f"Khoản gốc đã nằm trong chi phí chuyến (dòng #{c.id}) — đề nghị này là "
                      f"thanh toán cho khoản ĐÃ GHI, không phải một chi phí mới.")
    if (p.ma_khoan_goc or "").strip():
        k = db.execute(select(FleetDeXuat).where(
            FleetDeXuat.id != p.id, FleetDeXuat.ma_khoan_goc == p.ma_khoan_goc.strip(),
            FleetDeXuat.trang_thai.in_(song))).scalars().first()
        if k is not None:
            cb.append(f"Mã khoản gốc «{p.ma_khoan_goc.strip()}» đã dùng ở phiếu {k.ma_phieu}.")
    if (p.so_chung_tu or "").strip() and p.so_tien:
        k = db.execute(select(FleetDeXuat).where(
            FleetDeXuat.id != p.id, FleetDeXuat.so_chung_tu == p.so_chung_tu.strip(),
            FleetDeXuat.so_tien == p.so_tien, FleetDeXuat.supplier_id == p.supplier_id,
            FleetDeXuat.trang_thai.in_(song))).scalars().first()
        if k is not None:
            cb.append(f"Đã có phiếu {k.ma_phieu} cùng chứng từ, cùng bên nhận và cùng số tiền.")
    return cb


def ma_moi(db: Session) -> str:
    """DX-YYYYMM-NNNN. Đếm theo THÁNG LẬP, không đếm cả bảng: số phiếu của một tháng là con số
    người giữ sổ đọc được, còn số thứ tự toàn bảng thì không nói gì."""
    dau = date.today().replace(day=1)
    n = db.execute(select(func.count(FleetDeXuat.id))
                   .where(FleetDeXuat.ngay_lap >= dau)).scalar() or 0
    return f"DX-{date.today():%Y%m}-{n + 1:04d}"


def _chup(p: FleetDeXuat) -> str:
    return json.dumps({
        "pham_vi": p.pham_vi, "vehicle_id": p.vehicle_id, "loai": p.loai, "nhom": p.nhom,
        "noi_dung": p.noi_dung, "supplier_id": p.supplier_id,
        "ben_nhan_de_nghi": p.ben_nhan_de_nghi, "so_tien": float(p.so_tien or 0),
        "ngay_can": str(p.ngay_can or ""), "can_cu_thue": p.can_cu_thue,
        "so_chung_tu": p.so_chung_tu, "hen_bo_sung": p.hen_bo_sung,
        "ly_do_bo_sung": p.ly_do_bo_sung, "ma_khoan_goc": p.ma_khoan_goc,
        "trip_cost_id": p.trip_cost_id, "ghi_chu": p.ghi_chu,
        "so_tien_da_tt": float(p.so_tien_da_tt or 0), "trang_thai": p.trang_thai,
    }, ensure_ascii=False)


def ghi_log(db: Session, p: FleetDeXuat, hanh_dong: str, den: str, ly_do: str,
            boi: str, vai: str, chup: str | None = None) -> None:
    db.add(FleetDeXuatLog(de_xuat_id=p.id, hanh_dong=hanh_dong, tu_trang_thai=p.trang_thai,
                          den_trang_thai=den, ly_do=(ly_do or "")[:2000],
                          phien_ban_truoc=p.phien_ban,
                          noi_dung_truoc=chup if chup is not None else _chup(p),
                          boi=boi, vai=vai))


def chuyen_buoc(db: Session, p: FleetDeXuat, hanh_dong: str, tai_khoan: str, vai: str,
                ly_do: str = "", so_tien_tra: float | None = None) -> dict:
    """Một bước chuyển. Kiểm quyền → kiểm dữ liệu → ghi log (bản chụp TRƯỚC) → đổi trạng thái."""
    vi_sao = co_the(db, p, hanh_dong, tai_khoan, vai)
    if vi_sao:
        raise HTTPException(403, vi_sao)
    if hanh_dong in CAN_LY_DO and not (ly_do or "").strip():
        raise HTTPException(422, "Phải ghi lý do — người lập cần biết vì sao, nếu không lần gửi "
                                 "thứ hai cũng sai y như lần đầu")
    canh_bao: list[str] = []
    if hanh_dong == "gui":
        loi = kiem(db, p, 3)
        if loi:
            raise HTTPException(422, " ".join(loi))
        canh_bao = kiem_trung(db, p)

    chup = _chup(p)
    den = CHUYEN[hanh_dong][1]

    if hanh_dong == "thanh_toan":
        if so_tien_tra is None or float(so_tien_tra) <= 0:
            raise HTTPException(422, "Nhập số tiền đã thanh toán")
        da = float(p.so_tien_da_tt or 0) + float(so_tien_tra)
        tong = float(p.so_tien or 0)
        if da > tong + 0.5:
            raise HTTPException(422, f"Thanh toán {da:,.0f} đ vượt số đề nghị {tong:,.0f} đ")
        p.so_tien_da_tt = da
        # Khép khi trả đủ. Ngưỡng nửa đồng chứ không so bằng: tiền lưu dạng số thực, và so bằng
        # trên số thực là chỗ một phiếu trả đủ mãi mãi hiện "một phần".
        den = "da_tt" if da >= tong - 0.5 else "da_tt_mot_phan"
        p.nguoi_thanh_toan = tai_khoan
    elif hanh_dong == "kiem_tra":
        p.nguoi_kiem_tra = tai_khoan
    elif hanh_dong == "duyet":
        p.nguoi_duyet = tai_khoan
    elif hanh_dong == "doi_soat":
        p.nguoi_doi_soat = tai_khoan
    elif hanh_dong == "gui" and not p.ma_phieu:
        p.ma_phieu = ma_moi(db)

    ghi_log(db, p, hanh_dong, den, ly_do, boi=tai_khoan, vai=vai, chup=chup)
    p.trang_thai = den
    p.phien_ban = (p.phien_ban or 1) + 1
    p.sua_luc = datetime.now()
    return {"ma_phieu": p.ma_phieu, "trang_thai": p.trang_thai,
            "trang_thai_ten": TRANG_THAI[p.trang_thai], "canh_bao_trung": canh_bao,
            "message": f"Phiếu {p.ma_phieu} → {TRANG_THAI[p.trang_thai]}"}


def tuyen(db: Session, p: FleetDeXuat) -> list[dict]:
    """Bốn chặng của bản vẽ, kèm chặng nào đã đi qua và ai đã đi.

    Tên chặng lấy đúng bản vẽ 09/11/2026: GĐ đội xe → Người được phân quyền → Kế toán được phân
    quyền → Bộ phận đối soát.
    """
    xong_lap = p.trang_thai not in ("nhap",)
    xong_duyet = p.trang_thai in ("da_duyet", "da_tt_mot_phan", "da_tt", "da_doi_soat")
    xong_tt = p.trang_thai in ("da_tt", "da_doi_soat")
    return [
        {"ai": "GĐ đội xe", "viec": "Lập và gửi đề nghị",
         "xong": xong_lap, "nguoi": p.nguoi_lap or ""},
        {"ai": "Người được phân quyền", "viec": "Kiểm tra, duyệt hoặc trả bổ sung",
         "xong": xong_duyet, "nguoi": " · ".join(x for x in [p.nguoi_kiem_tra, p.nguoi_duyet] if x)},
        {"ai": "Kế toán được phân quyền", "viec": "Kiểm tra bên nhận và thực hiện thanh toán",
         "xong": xong_tt, "nguoi": p.nguoi_thanh_toan or ""},
        {"ai": "Bộ phận đối soát", "viec": "Liên kết chứng từ và khoản chi gốc",
         "xong": p.trang_thai == "da_doi_soat", "nguoi": p.nguoi_doi_soat or ""},
    ]


def hien(db: Session, p: FleetDeXuat, tai_khoan: str = "", vai: str = "",
         day_du: bool = False) -> dict:
    """Một phiếu, đúng khuôn giao diện cần. `day_du` thêm tuyến, nhật ký và các nút bấm được."""
    ncc = db.get(Supplier, p.supplier_id) if p.supplier_id else None
    v = db.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
    ra = {
        "id": p.id, "ma_phieu": p.ma_phieu, "trang_thai": p.trang_thai,
        "trang_thai_ten": TRANG_THAI.get(p.trang_thai, p.trang_thai),
        "pham_vi": p.pham_vi, "vehicle_id": p.vehicle_id,
        "xe": (v.plate if v else ""), "ma_xe": (v.code if v else ""),
        "loai": p.loai, "loai_ten": LOAI.get(p.loai, p.loai),
        "nhom": p.nhom, "nhom_ten": (NHOM_KHOAN.get(p.nhom) or (p.nhom, ""))[0],
        "noi_dung": p.noi_dung,
        "supplier_id": p.supplier_id, "ben_nhan": (ncc.ten if ncc else ""),
        "ben_nhan_de_nghi": p.ben_nhan_de_nghi,
        "so_tien": p.so_tien, "so_tien_da_tt": p.so_tien_da_tt,
        "con_phai_tra": (None if p.so_tien is None
                         else float(p.so_tien) - float(p.so_tien_da_tt or 0)),
        "ngay_can": p.ngay_can, "ngay_lap": p.ngay_lap,
        "can_cu_thue": p.can_cu_thue, "can_cu_thue_ten": CAN_CU_THUE.get(p.can_cu_thue, ""),
        "so_chung_tu": p.so_chung_tu, "so_tep": so_tep(db, p),
        "hen_bo_sung": p.hen_bo_sung, "ly_do_bo_sung": p.ly_do_bo_sung,
        "ma_khoan_goc": p.ma_khoan_goc, "trip_cost_id": p.trip_cost_id,
        "ghi_chu": p.ghi_chu, "buoc_nhap": p.buoc_nhap, "phien_ban": p.phien_ban,
        "nguoi_lap": p.nguoi_lap, "sua_duoc": p.trang_thai in CON_SUA_DUOC,
    }
    if not day_du:
        return ra
    ra["tuyen"] = tuyen(db, p)
    ra["con_thieu"] = kiem(db, p, 3)
    ra["canh_bao_trung"] = kiem_trung(db, p)
    ra["han_muc_tgd"] = han_muc(db)
    ra["bam_duoc"] = {h: co_the(db, p, h, tai_khoan, vai) for h in CHUYEN}
    ra["nhat_ky"] = [
        {"luc": g.luc, "hanh_dong": g.hanh_dong, "boi": g.boi, "vai": g.vai,
         "tu": TRANG_THAI.get(g.tu_trang_thai, g.tu_trang_thai),
         "den": TRANG_THAI.get(g.den_trang_thai, g.den_trang_thai), "ly_do": g.ly_do}
        for g in db.execute(select(FleetDeXuatLog)
                            .where(FleetDeXuatLog.de_xuat_id == p.id)
                            .order_by(FleetDeXuatLog.luc)).scalars()
    ]
    return ra


def danh_muc(db: Session) -> dict:
    """Mọi danh sách giao diện cần để dựng form — máy chủ trả, màn hình KHÔNG gõ lại.

    Gõ lại bảy nhóm khoản ở phía giao diện là dựng chỗ cho ngày thêm nhóm thứ tám: máy chủ nhận
    nhóm mới, màn hình vẫn bảy ô, và không ai thấy gì sai cho tới lúc đối chiếu sổ.
    """
    return {
        "trang_thai": [{"ma": k, "ten": v} for k, v in TRANG_THAI.items()],
        "loai": [{"ma": k, "ten": v} for k, v in LOAI.items()],
        "nhom": [{"ma": k, "ten": v[0], "pham_vi": v[1]} for k, v in NHOM_KHOAN.items()],
        "can_cu_thue": [{"ma": k, "ten": v} for k, v in CAN_CU_THUE.items()],
        "han_muc_tgd": han_muc(db),
        "chung_tu_bat_buoc_tu": _nguong_chung_tu(db),
        # Tên bốn bước lấy đúng bản vẽ 09/11/2026. Trả từ máy chủ vì bước là LUẬT, không phải nhãn.
        "buoc": ["Nội dung", "Tiền & chứng từ", "Kiểm tra", "Gửi xử lý"],
    }
