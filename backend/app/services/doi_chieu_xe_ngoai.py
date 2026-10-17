# -*- coding: utf-8 -*-
"""DX-2 — BÁO CÁO NHÌN LẠI: đã trả tiền thuê xe ngoài trong khi xe nhà đậu bãi.

Chủ tịch chọn làm việc này trước năm việc còn lại của đội xe (16/10/2026), vì nó là thứ đã bắt
được tiền thật: **51.348.800 đ nhóm A tháng 9/2026** — thuê xe ngoài trong khi xe nhà không chạy.

VÌ SAO PHẢI CÓ BÁO CÁO NHÌN LẠI, khi đã có gợi ý điều xe. `fleet_ai.goi_y_dieu_xe` nhìn VỀ TRƯỚC:
nó giúp người sắp lập lệnh chọn xe rảnh. Nó không bao giờ trả lời được câu «tháng vừa rồi mình đã
trả bao nhiêu ra ngoài một cách không cần thiết» — và đó mới là câu làm người ta đổi cách làm.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA NHÓM, KHÔNG PHẢI MỘT CON SỐ
═══════════════════════════════════════════════════════════════════════════════════════════════

Gộp cả ba thành một con số «đã phí bao nhiêu» là cách chắc chắn để không ai tin báo cáo này sau
lần thứ hai. Nên tách ra, và mỗi nhóm trả lời một câu khác nhau:

  A · ĐÁNG LẼ KHÔNG CẦN THUÊ. Chặng ô tô thuê ngoài, có ngày, và hôm ấy có xe nhà đủ chỗ mà
     không chạy chuyến nào. Đây là nhóm ra tiền.

  B · NGHI KHAI NHẦM. Chặng khai là thuê ngoài nhưng biển số trùng một chiếc xe trong danh mục.
     Nếu đúng là xe nhà thì khoản ấy là công nợ nội bộ, không phải tiền trả bên thứ ba — hai
     đường hạch toán khác nhau, và khi hợp nhất báo cáo thì nó phải loại trừ. Không tự sửa:
     chỉ nêu ra cho người có sổ xác nhận.

  C · KHÔNG ĐỐI CHIẾU ĐƯỢC. Chặng không có ngày. Đếm riêng và nói ra — giấu đi thì nhóm A trông
     nhỏ hơn thực tế, và người đọc tin rằng đã soát hết.

═══════════════════════════════════════════════════════════════════════════════════════════════
«XE NHÀ RẢNH» ĐỌC NHẬT TRÌNH, KHÔNG ĐỌC LỆNH
═══════════════════════════════════════════════════════════════════════════════════════════════

Dùng lại `fleet.trung_nhat_ky` — hàm đã có, đã viết sẵn lý do, và đã được một vòng trước sửa đúng
chỗ hỏng này: hệ thống tra bảng LỆNH, không thấy lệnh nào, nên coi mọi xe là rảnh suốt. Hôm nay
còn 0 lệnh điều xe trong khi nhật trình có 780 chuyến, nên dựng một phép đếm thứ hai ở đây là tự
tay dựng lại đúng cái bẫy ấy.

Lượt chạy thuê ngoài (không nối tour) VẪN TÍNH LÀ BẬN — Chủ tịch chốt 11/10/2026. Báo một chiếc
xe đang đi kiếm tiền là «đậu bãi» thì nhóm A phình lên bằng những dòng sai.

SỐ CHỖ LÀ ĐIỀU KIỆN, KHÔNG PHẢI GHI CHÚ. Xe 16 chỗ rảnh không thay được chặng 45 khách. Không so
số chỗ thì báo cáo đầy những dòng «đáng lẽ không cần thuê» mà người điều hành biết ngay là vô lý —
và một báo cáo sai ở chỗ dễ thấy thì không ai đọc tới chỗ khó thấy.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour
from app.models.hr import Vehicle
from app.services import xe_nha as XN
from app.models.lop3_tour import TourPhuongTien
from app.services import fleet as FL

LOAI_XE = "o_to"


def _bien_chuan(s: str | None) -> str:
    """Bỏ mọi ký tự không phải chữ-số rồi viết hoa. `51B-456.78`, `51B 45678`, `51b45678` là một."""
    return "".join(ch for ch in (s or "") if ch.isalnum()).upper()


def _thue_ngoai(x: TourPhuongTien) -> bool:
    """Chặng này có phải thuê ngoài không.

    `vehicle_id` CÓ GIÁ TRỊ thì chắc chắn là xe nhà, bất kể ô `xe_nha` khai gì — một con trỏ tới
    hồ sơ xe là bằng chứng mạnh hơn một ô đánh dấu. Ngược lại thì đọc `xe_nha`, và ô ấy mặc định
    là 0, nên «chưa ai khai» cũng rơi vào đây — đó chính là lý do có nhóm B ở dưới.
    """
    if x.vehicle_id is not None:
        return False
    return not bool(x.xe_nha)


def _xe_nha_ranh(db: Session, ngay: date, so_cho_can: int | None) -> list[Vehicle]:
    """Xe đang khai thác, đủ chỗ, và hôm ấy không có lượt nào trong nhật trình."""
    ra = []
    for v in db.execute(select(Vehicle).where(Vehicle.active.is_(True))
                        .order_by(Vehicle.plate)).scalars():
        if v.lifecycle != "dang_khai_thac" or v.op_right not in FL.QUYEN_DUOC_DIEU:
            continue
        if so_cho_can and (v.seats or 0) < so_cho_can:
            continue
        if FL.trung_nhat_ky(db, v.id, ngay, ngay):
            continue
        ra.append(v)
    return ra


def _so_cho_can(x: TourPhuongTien) -> int | None:
    """Số chỗ chặng ấy cần. Ưu tiên số chỗ đã khai, không có thì lấy số khách thực dùng."""
    return x.so_cho or x.so_khach_su_dung or None


def soat(db: Session, tu: date, den: date, gioi_han: int = 200) -> dict:
    """Đối chiếu một kỳ. CHỈ ĐỌC — không ghi, không sửa, không tự gắn xe vào chặng nào."""
    if den < tu:
        raise ValueError("Ngày cuối kỳ trước ngày đầu kỳ")

    # Chỉ XE NHÀ (17/10/2026): biển trùng một xe hợp tác hay xe thuê thì chặng ấy đúng là thuê
    # ngoài — bản cũ so với cả danh mục nên gọi nhầm chúng là «nghi khai nhầm». Cùng một luật với
    # ô chọn xe và cửa gắn tay trên tờ quyết toán: app/services/xe_nha.py.
    bien_cua_xe = XN.xe_nha_theo_bien(db)

    chang = list(db.execute(select(TourPhuongTien).where(TourPhuongTien.loai == LOAI_XE)).scalars())
    ma_tour = {t.id: t for t in db.execute(select(Tour)).scalars()}

    nhom_a, nhom_b, nhom_c = [], [], []
    for x in chang:
        if not _thue_ngoai(x):
            continue
        t = ma_tour.get(x.tour_id)
        goc = {"chang_id": x.id, "tour_id": x.tour_id,
               "ma_tour": t.code if t else "", "ten_tour": (t.name if t else "")[:80],
               "chang": x.chang or "", "nha_cung_cap": x.nha_cung_cap or "",
               "so_hieu": x.so_hieu or "", "so_cho": x.so_cho,
               "so_khach": x.so_khach_su_dung,
               "thanh_tien": float(x.thanh_tien) if x.thanh_tien is not None else None}

        # NHÓM B trước nhóm A: một chặng nghi là xe nhà khai nhầm thì KHÔNG được đồng thời đếm
        # vào tiền «đáng lẽ không cần thuê» — chưa biết nó có phải tiền trả ra ngoài hay không.
        trung = bien_cua_xe.get(_bien_chuan(x.so_hieu))
        if trung is not None:
            nhom_b.append({**goc, "xe_trong_danh_muc": trung.plate, "ma_xe": trung.code,
                           "vi_sao": "Biển số trên chặng trùng một chiếc xe nhà trong danh mục – "
                                     "nếu đúng là xe nhà thì đây là công nợ nội bộ, không phải "
                                     "tiền trả bên thứ ba"})
            continue

        if x.ngay is None:
            nhom_c.append({**goc, "vi_sao": "Chặng không có ngày nên không đối chiếu được với "
                                            "nhật trình xe"})
            continue
        if not (tu <= x.ngay <= den):
            continue

        can = _so_cho_can(x)
        ranh = _xe_nha_ranh(db, x.ngay, can)
        if ranh:
            nhom_a.append({**goc, "ngay": x.ngay.isoformat(), "so_cho_can": can,
                           "xe_nha_ranh": [{"id": v.id, "bien": v.plate, "ma": v.code,
                                            "ghe": v.seats} for v in ranh[:10]],
                           "so_xe_ranh": len(ranh)})

    tien_a = sum(d["thanh_tien"] or 0 for d in nhom_a)
    thieu_tien_a = sum(1 for d in nhom_a if d["thanh_tien"] is None)
    return {
        "tu": tu.isoformat(), "den": den.isoformat(),
        "a_dang_le_khong_can_thue": {
            "so_chang": len(nhom_a), "tien": tien_a,
            "so_chang_chua_co_tien": thieu_tien_a,
            "danh_sach": nhom_a[:gioi_han],
            "ghi_chu": ("Chặng ô tô thuê ngoài mà hôm ấy có xe nhà đủ chỗ không chạy lượt nào. "
                        "Số tiền chỉ cộng những chặng ĐÃ có thành tiền; chặng chưa có tiền đếm "
                        "riêng để con số không trông nhỏ hơn thực tế."),
        },
        "b_nghi_khai_nham": {
            "so_chang": len(nhom_b), "danh_sach": nhom_b[:gioi_han],
            "ghi_chu": ("Khai là thuê ngoài nhưng biển số trùng một xe nhà trong danh mục. Hệ thống "
                        "KHÔNG tự sửa: chỉ người có sổ mới biết chặng ấy thật sự chạy bằng xe nào. "
                        "Đúng là xe nhà thì bấm «Gắn tay» ở mục Phương tiện của tờ quyết toán."),
        },
        "c_khong_doi_chieu_duoc": {
            "so_chang": len(nhom_c), "danh_sach": nhom_c[:gioi_han],
            "ghi_chu": "Chặng không có ngày. Khai ngày vào thì chúng vào được nhóm A hoặc rớt ra.",
        },
    }


def ky_thang(nam: int, thang: int) -> tuple[date, date]:
    """Đầu và cuối một tháng. Để màn hình không phải tự tính ngày cuối tháng."""
    tu = date(nam, thang, 1)
    den = date(nam + (thang == 12), (thang % 12) + 1, 1) - timedelta(days=1)
    return tu, den
