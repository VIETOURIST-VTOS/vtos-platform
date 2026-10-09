# -*- coding: utf-8 -*-
"""SỔ HOẠT ĐỘNG PR — việc truyền thông đã ra ngoài, và ai chịu trách nhiệm cho nó.

Hai chữ ký của Chủ tịch ngày 18/9/2026 sống ở tệp này:

    1. NGƯỜI PHÁT NGÔN LÀ P.TGĐ MARKETING.
    2. KHỦNG HOẢNG TRUYỀN THÔNG: 2 GIỜ kể từ lúc việc được ghi vào sổ.

──────────────────────────────────────────────────────────────────────────────────────────────
ĐIỀU 1: "NGƯỜI PHÁT NGÔN" KHÔNG PHẢI MỘT Ô GÕ TÊN
──────────────────────────────────────────────────────────────────────────────────────────────

Cách rẻ nhất là thêm một cột chữ rồi để người nhập gõ tên vào. Cách ấy hỏng LẶNG: sổ vẫn đầy đủ,
mọi dòng đều có tên, và đúng vào hôm cần tra "ai đã nói câu đó" thì cái tên ấy không nối được với
một tài khoản nào, không ai xác nhận, không ai chịu trách nhiệm.

Nên: `nguoi_phat_ngon` do HỆ THỐNG ghi, lúc người có vai phát ngôn bấm nút phát. Hàng rào nằm ở
đường API (`require_roles`) như mọi đường ghi khác trong hệ — không phải một câu `if` trong thân
hàm, vì bảng phân quyền toàn hệ không đếm được một câu `if`. Đây là bài học vừa trả giá cùng ngày:
ba bộ kiểm KS-2, P-1, TQ-1 đỏ đúng chỗ ấy ở sổ tài sản thương hiệu.

Tham số `pr_vai_phat_ngon` giữ BẢN GHI CHỮ KÝ của quyết định — ai chốt, ngày nào — thứ mà
`require_roles` không mang được. Hai chỗ không được lệch nhau và có phép thử chốt.

──────────────────────────────────────────────────────────────────────────────────────────────
ĐIỀU 2: HAI GIỜ, THEO ĐỒNG HỒ THẬT
──────────────────────────────────────────────────────────────────────────────────────────────

Không trừ ngày nghỉ, không quy ra giờ hành chính. Một việc ghi vào sổ lúc 22h thứ Bảy thì 0h là
quá hạn — và đó đúng là bản chất của khủng hoảng truyền thông. Bịa thêm một luật giờ làm việc là
tự ký thay một điều không ai ký. (Cùng cách VTOS đã làm với hạn xử lý lead 24 giờ.)

MỐC BẮT ĐẦU ĐẾM LÀ LÚC VÀO SỔ, không phải lúc việc xảy ra ngoài đời. Lấy lúc xảy ra thì một vụ
phát hiện muộn ba ngày đã quá hạn ngay khi vừa ghi, và con số "quá hạn" thành vô nghĩa. Lấy lúc
vào sổ thì nó đo đúng cái đo được: từ khi công ty BIẾT, bao lâu thì công ty TRẢ LỜI.

CHỈ VIỆC KHỦNG HOẢNG MỚI CÓ HẠN. Một bài đăng mạng xã hội không có hạn hai giờ, và gán hạn cho nó
là làm hỏng chính con số cần nhìn: bảng "quá hạn" đầy những dòng không ai coi là gấp thì không ai
nhìn bảng ấy nữa.

BỘ LỌC SQL VÀ PHÉP TÍNH PYTHON LÀ HAI BẢN CỦA MỘT LUẬT, và có một phép thử chéo bắt chúng ra cùng
một tập trên cùng một sổ.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.marketing import PR_LOAI, PR_TRANG_THAI, PrHoatDong  # noqa: F401

THAM_SO_GIO = "pr_khung_hoang_gio"
THAM_SO_VAI_PHAT_NGON = "pr_vai_phat_ngon"


def gio_han(db: Session) -> float:
    """Số giờ phải phản hồi, đọc SỐNG từ sổ tham số. Không viết cứng con số 2 vào mã."""
    from app.services import rules as R
    return float(R.get_param(db, THAM_SO_GIO))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HẠN PHẢN HỒI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def han_phan_hoi(h: PrHoatDong, gio: float) -> datetime | None:
    """Mốc phải có phản hồi. `None` khi việc này KHÔNG phải khủng hoảng — không có hạn."""
    if not h.la_khung_hoang or h.ghi_nhan_luc is None:
        return None
    return h.ghi_nhan_luc + timedelta(hours=gio)


def da_phan_hoi(h: PrHoatDong) -> bool:
    return h.phan_hoi_luc is not None


def qua_han(h: PrHoatDong, gio: float, bay_gio: datetime | None = None) -> bool:
    han = han_phan_hoi(h, gio)
    if han is None or da_phan_hoi(h):
        return False
    return (bay_gio or datetime.now()) > han


def loc_qua_han(qs, gio: float, bay_gio: datetime | None = None):
    """Cùng luật ấy, viết bằng SQL. Xem phép thử chéo trong test_pr1."""
    moc = (bay_gio or datetime.now()) - timedelta(hours=gio)
    return qs.where(
        PrHoatDong.la_khung_hoang.is_(True),
        PrHoatDong.phan_hoi_luc.is_(None),
        PrHoatDong.ghi_nhan_luc < moc,
    )


def dem_qua_han(db: Session, gio: float | None = None, bay_gio: datetime | None = None) -> int:
    """Đếm trên CẢ SỔ, không đếm trên trang đang xem.

    Đếm trên một câu truy vấn đã cắt trang thì con số nhỏ hơn sự thật, và nhỏ một cách im lặng —
    đúng lỗi đã mắc và đã sửa ở sổ lead ngày 18/9. Nên hàm này tự dựng câu truy vấn của mình.
    """
    g = gio if gio is not None else gio_han(db)
    q = loc_qua_han(select(PrHoatDong), g, bay_gio)
    return int(db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHÁT NGÔN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def phat(db: Session, h: PrHoatDong, boi: str) -> dict:
    """Bấm PHÁT. Vai trò đã được hàng rào ở đường API chặn trước khi tới đây.

    Ghi tên NGƯỜI BẤM chứ không ghi tên vai: sáu tháng sau câu hỏi là "ai đã nói", không phải
    "vai nào đã nói".
    """
    from app.services import rules as R

    if h.trang_thai == "da_phat":
        raise ValueError(f"Việc này đã phát lúc {h.phat_luc:%d/%m/%Y %H:%M} rồi")
    if h.trang_thai == "khong_phat":
        raise ValueError("Việc này đã có quyết định KHÔNG phát – mở lại bằng cách sửa trạng thái")
    h.trang_thai = "da_phat"
    h.nguoi_phat_ngon = (boi or "")[:50]
    h.phat_luc = datetime.now()
    # Phát ngôn CHÍNH LÀ phản hồi, với một vụ khủng hoảng. Bắt người ta bấm thêm một nút "đã phản
    # hồi" nữa là dựng ra một ô sẽ bị quên, và bảng quá hạn sẽ đầy những dòng đã xử lý xong.
    if h.la_khung_hoang and h.phan_hoi_luc is None:
        h.phan_hoi_luc = h.phat_luc
        h.phan_hoi_boi = h.nguoi_phat_ngon
    R.audit(db, boi, "", "phat_ngon_pr", f"mkt_pr_hoat_dong:{h.id}",
            after={"ma": h.ma, "nguoi_phat_ngon": h.nguoi_phat_ngon,
                   "luc": f"{h.phat_luc:%Y-%m-%d %H:%M:%S}"})
    db.flush()
    return {"id": h.id, "ma": h.ma, "trang_thai": h.trang_thai,
            "nguoi_phat_ngon": h.nguoi_phat_ngon, "phat_luc": h.phat_luc,
            "message": f"Đã phát lúc {h.phat_luc:%H:%M %d/%m/%Y}, đứng tên {h.nguoi_phat_ngon}."}


def ghi_phan_hoi(db: Session, h: PrHoatDong, boi: str) -> dict:
    """Ghi rằng đã có phản hồi, cho vụ khủng hoảng xử lý bằng đường khác (gọi điện, gặp trực tiếp).

    Không phải vụ nào cũng kết thúc bằng một bài đăng. Không có cửa này thì những vụ ấy nằm mãi ở
    bảng quá hạn, và bảng quá hạn mất hết ý nghĩa.
    """
    from app.services import rules as R

    if not h.la_khung_hoang:
        raise ValueError("Việc này không phải khủng hoảng – không có hạn phản hồi để ghi")
    if h.phan_hoi_luc is not None:
        raise ValueError(f"Đã ghi phản hồi lúc {h.phan_hoi_luc:%d/%m/%Y %H:%M}")
    h.phan_hoi_luc = datetime.now()
    h.phan_hoi_boi = (boi or "")[:50]
    R.audit(db, boi, "", "ghi_phan_hoi_khung_hoang", f"mkt_pr_hoat_dong:{h.id}",
            after={"ma": h.ma, "luc": f"{h.phan_hoi_luc:%Y-%m-%d %H:%M:%S}"})
    db.flush()
    cham = round((h.phan_hoi_luc - h.ghi_nhan_luc).total_seconds() / 3600, 1)
    return {"id": h.id, "ma": h.ma, "phan_hoi_luc": h.phan_hoi_luc, "sau_bao_lau_gio": cham,
            "message": f"Đã ghi phản hồi, {cham} giờ kể từ lúc vào sổ."}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỌC SỔ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def mot_dong(h: PrHoatDong, gio: float, bay_gio: datetime | None = None) -> dict:
    han = han_phan_hoi(h, gio)
    return {
        "id": h.id, "ma": h.ma, "loai": h.loai, "loai_ten": PR_LOAI.get(h.loai, h.loai),
        "tieu_de": h.tieu_de, "tom_tat": h.tom_tat, "noi_dang": h.noi_dang, "link": h.link,
        "trang_thai": h.trang_thai,
        "trang_thai_ten": PR_TRANG_THAI.get(h.trang_thai, h.trang_thai),
        "nguoi_phat_ngon": h.nguoi_phat_ngon, "phat_luc": h.phat_luc,
        "la_khung_hoang": h.la_khung_hoang, "muc_do": h.muc_do,
        "ghi_nhan_luc": h.ghi_nhan_luc,
        "han_phan_hoi": han, "phan_hoi_luc": h.phan_hoi_luc, "phan_hoi_boi": h.phan_hoi_boi,
        "qua_han": qua_han(h, gio, bay_gio),
        "campaign_id": h.campaign_id, "ghi_chu": h.ghi_chu,
    }


def bang(db: Session, loai: str = "", trang_thai: str = "",
         chi_khung_hoang: bool = False, u=None) -> dict:
    """`u` là người đang xem. Truyền vào thì danh sách bị CẮT theo phạm vi pháp nhân của người ấy.

    `PrHoatDong` khai trong `pham_vi_phap_nhan.PHAI_LOC` — một bài báo, một sự kiện, một vụ khủng
    hoảng đều xảy ra dưới thương hiệu của một pháp nhân cụ thể. Khai mà không nối là một lời hứa
    không giữ, nên chỗ nối nằm ngay đây.
    """
    from app.services import pham_vi_phap_nhan as PV

    g = gio_han(db)
    q = select(PrHoatDong).order_by(PrHoatDong.ghi_nhan_luc.desc(), PrHoatDong.id.desc())
    if u is not None:
        q = PV.loc(q, PrHoatDong, u)
    if loai:
        q = q.where(PrHoatDong.loai == loai)
    if trang_thai:
        q = q.where(PrHoatDong.trang_thai == trang_thai)
    if chi_khung_hoang:
        q = q.where(PrHoatDong.la_khung_hoang.is_(True))
    rows = [mot_dong(h, g) for h in db.execute(q).scalars()]
    return {
        "rows": rows,
        "han_khung_hoang_gio": g,
        "dem": {
            "tong": len(rows),
            "da_phat": sum(1 for r in rows if r["trang_thai"] == "da_phat"),
            "cho_phat": sum(1 for r in rows if r["trang_thai"] == "cho_phat"),
            "khung_hoang": sum(1 for r in rows if r["la_khung_hoang"]),
            # Đếm QUÁ HẠN trên CẢ SỔ, không đếm trên danh sách đang lọc: người đọc thẻ này hỏi
            # "công ty đang nợ mấy câu trả lời", không hỏi "trang này có mấy dòng đỏ".
            "qua_han": dem_qua_han(db, g),
        },
        "loai": PR_LOAI, "trang_thai_ds": PR_TRANG_THAI,
    }


def ma_moi(db: Session, luc: datetime | None = None) -> str:
    d = luc or datetime.now()
    # Lọc theo tiền tố là ĐÚNG RỒI, nhưng ĐẾM số dòng khớp thì vẫn hỏng khi có dòng bị xoá:
    # số lùi một bước và mã kế tiếp đụng một mã đang còn sống. Lấy số LỚN NHẤT thì không.
    from app.services.ma_tu_sinh import tiep_theo
    dau = f"PR-{d:%Y-%m}-"
    return tiep_theo(db, PrHoatDong, dau, 4, cot="ma")


def kiem_du_lieu(db: Session, r: dict, tu_tay: bool = False) -> None:
    """Hàng rào của cửa tạo — THÊM 24/9/2026 khi sổ này có cửa tạo tay đầu tiên.

    Tới hôm nay `tao()` chỉ được gọi từ một chỗ: nút "lập PR" trên hàng đợi tin cảnh báo, nơi
    `loai` do chính mã ấy đặt. Nên chưa ai gõ sai được, và hàm không cần kiểm gì. Nay mục 2.2.2 có
    màn hình với ô nhập thật, người gõ được mọi thứ — và một `loai` sai chính tả sẽ nằm im trong
    sổ, không lọt vào bộ lọc nào, không hiện ở thẻ nào, mà cũng không báo lỗi.

    KIỂM Ở SERVICE CHỨ KHÔNG Ở CỬA API: hai cửa gọi chung một hàm này, và hàng rào đặt ở cửa thì
    cửa thứ ba viết sau sẽ quên.
    """
    from app.models.marketing import Campaign

    if r.get("loai") not in PR_LOAI:
        raise ValueError(f"Loại hoạt động không hợp lệ: {r.get('loai')!r}")
    if not str(r.get("tieu_de") or "").strip():
        raise ValueError("Phải có tiêu đề — một dòng không tên thì ba tháng sau không ai tra ra.")
    muc = str(r.get("muc_do") or "").strip()
    if muc and muc not in ("nhe", "vua", "nghiem_trong"):
        raise ValueError(f"Mức độ không hợp lệ: {muc!r}")
    # MỨC ĐỘ BẮT BUỘC Ở CỬA TAY, KHÔNG BẮT BUỘC Ở LUỒNG HỘP THƯ — và chỗ khác nhau này đáng ghi,
    # vì bản đầu của vòng TC-81 đặt nó thành luật chung rồi làm gãy bảy phép thử của cửa lọc tin.
    #
    # Người ngồi gõ một bài báo vào sổ thì đã đọc xong bài ấy: hỏi thêm một ô mức độ không tốn gì,
    # và bỏ trống ô ấy nghĩa là sổ có một vụ khủng hoảng không ai xếp hạng.
    #
    # Người bấm "lập PR" trên hàng đợi tin cảnh báo lúc hai giờ sáng thì KHÁC HẲN. Việc của họ lúc
    # ấy là đưa vụ vào sổ để đồng hồ bắt đầu chạy — nhanh nhất có thể. Bắt họ dừng lại chọn một ô
    # là đặt thêm một bước vào đúng khoảnh khắc phải ít bước nhất, và bộ lọc thì đã chấm điểm tin
    # ấy rồi. Xếp hạng để sau, sửa được bất cứ lúc nào.
    if tu_tay and r.get("la_khung_hoang") and not muc:
        raise ValueError(
            "Đánh dấu khủng hoảng thì phải chọn mức độ. Mốc hai giờ bắt đầu chạy từ lúc dòng này "
            "vào sổ, và người trực cần biết ngay nó nặng tới đâu.")
    cd = r.get("campaign_id")
    if cd and db.get(Campaign, int(cd)) is None:
        raise ValueError(f"Không có chiến dịch id {cd}.")


def tao(db: Session, r: dict, boi: str, tu_tay: bool = False) -> PrHoatDong:
    """Ghi một việc vào sổ. `ghi_nhan_luc` do HỆ THỐNG đặt – xem ghi chú ở models/marketing.py.

    `tu_tay=True` là gọi từ màn hình có người ngồi gõ; mặc định False là luồng hộp thư cảnh báo.
    Khác nhau đúng một điều: mức độ của vụ khủng hoảng. Xem `kiem_du_lieu`.
    """
    kiem_du_lieu(db, r, tu_tay=tu_tay)
    h = PrHoatDong(
        ma=ma_moi(db),
        loai=str(r.get("loai") or "").strip()[:16],
        tieu_de=str(r.get("tieu_de") or "").strip()[:300],
        tom_tat=str(r.get("tom_tat") or "").strip(),
        noi_dang=str(r.get("noi_dang") or "").strip()[:200],
        link=str(r.get("link") or "").strip()[:400],
        la_khung_hoang=bool(r.get("la_khung_hoang")),
        muc_do=str(r.get("muc_do") or "").strip()[:12],
        ghi_chu=str(r.get("ghi_chu") or "").strip(),
        # THÊM 24/9/2026 — hai ô sổ vẫn có cột mà `tao()` chưa bao giờ điền, vì cửa duy nhất gọi nó
        # (nút "lập PR" từ hàng đợi tin) không biết chiến dịch nào. Nay màn hình 2.2.2 hỏi được.
        campaign_id=r.get("campaign_id"),
        company_id=r.get("company_id"),
        trang_thai="nhap", nguoi_tao=(boi or "")[:50],
        ghi_nhan_luc=datetime.now(),
    )
    db.add(h)
    db.flush()
    return h


def dinh_nghia_cot() -> dict:
    """Ánh xạ mã ↔ tên, cho màn hình và cho cửa nhập dùng chung một danh mục."""
    return {"loai": PR_LOAI, "trang_thai": PR_TRANG_THAI,
            "muc_do": {"nhe": "Nhẹ", "vua": "Vừa", "nghiem_trong": "Nghiêm trọng"}}
