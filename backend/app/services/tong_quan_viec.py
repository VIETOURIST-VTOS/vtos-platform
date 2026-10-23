# -*- coding: utf-8 -*-
"""TQ-1 · MỤC «VẬN HÀNH & CÔNG VIỆC» TRÊN MÀN HÌNH CHỦ TỊCH — phần máy chủ.

Chủ tịch chốt bản v1.1 ngày 22/10/2026. Bản cũ in «10.037 việc» nhưng con số ấy là 10.037 LƯỢT
CẢNH BÁO đang mở: một tour có ba cảnh báo thì bị đếm ba lần, và ai mở màn hình cũng thấy cùng
một tổng dù họ chỉ được xem một phần. Tệp này trả lời câu «còn bao nhiêu VIỆC», theo đúng thứ tự
Chủ tịch duyệt:

    người xem → LỌC cảnh báo được phép xem → ÁNH XẠ về hồ sơ → GỘP, lấy mức cao nhất → ĐẾM

LỌC TRƯỚC, GỘP SAU. Gộp trước thì mức «nghiêm trọng» của một cảnh báo người xem không được thấy
vẫn nhuộm đỏ cả việc — tức lộ đúng thứ bộ lọc sinh ra để che.

LUẬT XEM DÙNG CHUNG với cửa `/alerts` (`loc_theo_vai` dưới đây; routes.list_alerts gọi lại đúng
hàm này). Hai luật xem cho cùng một bảng là hai chỗ sẽ lệch nhau.

ÁNH XẠ LÀ DANH SÁCH ĐÓNG. `alerts.ref` không có khuôn chung: chỗ ghi mã tour trần, chỗ có tiền
tố, chỗ là chuỗi cố định của hệ thống. Ref nào không khớp luật nào thì KHÔNG đoán: mỗi cảnh báo
ấy đứng thành một việc riêng (khoá theo id cảnh báo) và được đếm vào «chưa ánh xạ» — để con số
ấy hiện ra và có người đi khai thêm luật, chứ không lặng lẽ gộp nhầm hay rơi khỏi tổng.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.core import Alert, User
from app.services import canh_bao_muc as CBM
from app.services import canh_bao_trinh_bay as CBTB

# ─────────────────────────────── lọc theo quyền xem ───────────────────────────────
def thay_tat_ca(u: User) -> bool:
    from app.services import access as AC
    return u.role in AC.BASE_VIEW + ("ketoan", "cntt")


def loc_theo_vai(qs, u: User):
    """Câu truy vấn Alert chỉ còn những dòng người này được xem. MỘT luật cho mọi nơi.

    `to_roles` là chuỗi ngăn bằng dấu phẩy, nên khớp CẢ MẨU (bốn vị trí: một mình, đầu, cuối,
    giữa) chứ không `LIKE '%vai%'` — tìm chuỗi con thì «kt» trúng luôn dòng gửi «ketoan».
    """
    if thay_tat_ca(u):
        return qs
    vai = u.role
    return qs.where(or_(Alert.to_roles == vai, Alert.to_roles.like(f"{vai},%"),
                        Alert.to_roles.like(f"%,{vai}"), Alert.to_roles.like(f"%,{vai},%")))


# ─────────────────────────────── ánh xạ cảnh báo → hồ sơ ───────────────────────────────
# Ref là chuỗi cố định của hệ thống: không gắn hồ sơ nghiệp vụ nào — mỗi (kind) là một việc.
REF_HE_THONG = {"zalo_oa", "zalo:cho_cau_hinh", "sepay"}

# Ref là MÃ TRẦN, nghĩa phụ thuộc loại cảnh báo.
THEO_KIND = {
    "d7": "tour", "qua_han_qt": "tour", "kt_cham": "tour", "thieu_du_toan": "tour",
    # Hai loại này cùng ghi MÃ KHIẾU NẠI (cskh.py) — cùng một hồ sơ, gộp được.
    "kn_qua_han": "khieu_nai", "cham_soc_diem_thap": "khieu_nai",
    "su_co_tour_muc3": "su_co_tour", "su_co_tour_qua_han": "su_co_tour",
    # ops.check_missing_reports: ref = «mã NV:ngày» — mỗi người-ngày một việc.
    "bc_ngay_1": "bao_cao_ngay", "bc_ngay_2": "bao_cao_ngay",
    "dt_thieu_nguon": "dong_tien_phap_nhan",       # han_dong_tien.khoa: «id pháp nhân:mã dòng»
    "khung_hoang": "khung_hoang",                  # bao_dong_khung_hoang: «nguồn:id nguồn»
}

# Ref có TIỀN TỐ — tiền tố nói loại hồ sơ. `giucho:` ghi mã BOOKING (giu_cho.py), nên về booking.
TIEN_TO = (
    ("tour:", "tour"), ("booking:", "booking"), ("giucho:", "booking"), ("baoluu:", "bao_luu"),
    ("receipt:", "phieu_thu"), ("dc:", "de_nghi_chi"), ("conv:", "hoi_thoai"),
    ("sale:", "nhan_vien_sale"), ("cong:", "cong_phong_ky"),
    ("yeu_cau_phap_che:", "yeu_cau_phap_che"), ("luong:", "luong_phong_ky"),
    # `cs:{id}` là ID phiếu chăm sóc — KHÁC không gian mã với mã khiếu nại ở trên, nên tách loại.
    ("cs:", "phieu_cham_soc"),
    ("YC-", "yeu_cau_dich_vu"),
)

TEN_LOAI = {
    "tour": "Tour", "booking": "Booking", "bao_luu": "Bảo lưu", "khieu_nai": "Khiếu nại",
    "su_co_tour": "Sự cố tour", "bao_cao_ngay": "Báo cáo ngày", "dong_tien_phap_nhan": "Dòng tiền",
    "khung_hoang": "Khủng hoảng", "phieu_thu": "Phiếu thu", "de_nghi_chi": "Đề nghị chi",
    "hoi_thoai": "Hội thoại khách", "nhan_vien_sale": "Nhân viên sale", "cong_phong_ky": "Công tháng",
    "yeu_cau_phap_che": "Yêu cầu Pháp chế", "luong_phong_ky": "Lương giữ lại",
    "phieu_cham_soc": "Phiếu chăm sóc", "yeu_cau_dich_vu": "Yêu cầu dịch vụ",
    "he_thong": "Hệ thống", "chua_anh_xa": "Chưa ánh xạ",
}


def khoa_ho_so(alert_id: int, kind: str, ref: str) -> tuple[str, str]:
    """(loại hồ sơ, mã hồ sơ). Không khớp luật nào → ('chua_anh_xa', 'a{id}') — không đoán."""
    ref = (ref or "").strip()
    kind = kind or ""
    if ref in REF_HE_THONG:
        return "he_thong", kind
    if kind in THEO_KIND and ref:
        return THEO_KIND[kind], ref
    for tien_to, loai in TIEN_TO:
        if ref.startswith(tien_to) and len(ref) > len(tien_to):
            return loai, ref[len(tien_to):]
    return "chua_anh_xa", f"a{alert_id}"


def _hang(level: str) -> int:
    """Thứ tự mức: Nghiêm trọng < Cảnh báo < Theo dõi < Chưa phân loại (nhỏ = nặng)."""
    for i, (ma, _) in enumerate(CBM.MUC):
        if level == ma:
            return i
    return len(CBM.MUC)


def _ma_muc(hang: int) -> str:
    return CBM.MUC[hang][0] if hang < len(CBM.MUC) else CBM.CHUA_PHAN_LOAI


# ─────────────────────────────── gộp ───────────────────────────────
def gop(db: Session, u: User) -> dict[tuple[str, str], dict]:
    """{(loại, mã): việc}. Chỉ đọc bốn cột, không nạp đối tượng ORM — 10 nghìn dòng vẫn nhẹ."""
    qs = loc_theo_vai(select(Alert.id, Alert.kind, Alert.ref, Alert.level, Alert.han_xu_ly,
                             Alert.nguoi_nhan_id, Alert.created_at)
                      .where(Alert.resolved == False), u)  # noqa: E712
    viec: dict[tuple[str, str], dict] = {}
    for aid, kind, ref, level, han, nguoi, luc in db.execute(qs).all():
        k = khoa_ho_so(aid, kind, ref)
        v = viec.get(k)
        h = _hang(str(level or ""))
        if v is None:
            viec[k] = v = {"loai": k[0], "ma": k[1], "hang": h, "so_canh_bao": 0, "kinds": set(),
                           "chua_phan_loai": 0, "han": None, "nguoi_nhan_id": None, "moi_nhat": None,
                           "alert_ids": []}
        v["so_canh_bao"] += 1
        v["hang"] = min(v["hang"], h)
        v["kinds"].add(kind or "")
        v["alert_ids"].append(aid)
        if h == len(CBM.MUC):
            v["chua_phan_loai"] += 1
        if han and (v["han"] is None or han < v["han"]):
            v["han"] = han
        if nguoi and v["nguoi_nhan_id"] is None:
            v["nguoi_nhan_id"] = nguoi
        if luc and (v["moi_nhat"] is None or luc > v["moi_nhat"]):
            v["moi_nhat"] = luc
    return viec


def tong(db: Session, u: User, viec: dict | None = None) -> dict:
    """Số cho ô «Việc nghiêm trọng» và khối «Tồn đọng công việc»."""
    viec = gop(db, u) if viec is None else viec
    theo = []
    for i, (ma, ten) in enumerate(CBM.MUC + ((CBM.CHUA_PHAN_LOAI, CBM.TEN_CHUA_PHAN_LOAI),)):
        ds = [v for v in viec.values() if v["hang"] == i]
        if ma == CBM.CHUA_PHAN_LOAI and not ds:
            continue
        theo.append({"ma": ma, "ten": ten, "viec": len(ds), "canh_bao": sum(v["so_canh_bao"] for v in ds)})
    return {"viec": len(viec), "canh_bao": sum(v["so_canh_bao"] for v in viec.values()),
            "theo_muc": theo,
            "chua_anh_xa": sum(v["so_canh_bao"] for v in viec.values() if v["loai"] == "chua_anh_xa"),
            # Cảnh báo mang mức lạ, đếm RIÊNG dù việc của nó đã mang mức khác — không để một cảnh
            # báo đỏ cùng hồ sơ che mất một mức viết sai chính tả.
            "canh_bao_chua_phan_loai": sum(v["chua_phan_loai"] for v in viec.values()),
            "pham_vi": "toan_bo" if thay_tat_ca(u) else f"vai:{u.role}",
            "luc": datetime.now().isoformat(timespec="seconds")}


def danh_sach(db: Session, u: User, muc: str = "", trang: int = 1, co: int = 50) -> dict:
    """Danh sách việc — CÙNG phép gộp với ô, tính lại ngay lúc mở (Chủ tịch chốt TT02: tính lại
    khi mở danh sách và báo mốc mới). Thứ tự: nặng trước, hạn gần trước, rồi loại + mã (ổn định
    để chia trang không lặp, không sót)."""
    viec = gop(db, u)
    t = tong(db, u, viec)
    ds = list(viec.values())
    if muc:
        ds = [v for v in ds if _ma_muc(v["hang"]) == muc]
    ds.sort(key=lambda v: (v["hang"], v["han"] is None, v["han"] or datetime.max, v["loai"], v["ma"]))
    co = max(1, min(int(co or 50), 200))
    trang = max(1, int(trang or 1))
    phan = ds[(trang - 1) * co: trang * co]
    ten = {}
    ids = {v["nguoi_nhan_id"] for v in phan if v["nguoi_nhan_id"]}
    if ids:
        ten = dict(db.execute(select(User.id, User.full_name).where(User.id.in_(ids))).all())
    return {"tong": t, "so_dong": len(ds), "trang": trang, "co": co,
            "dong": [{"loai": v["loai"], "loai_ten": TEN_LOAI.get(v["loai"], v["loai"]), "ma": v["ma"],
                      "muc": _ma_muc(v["hang"]), "so_canh_bao": v["so_canh_bao"],
                      "loai_canh_bao": sorted(v["kinds"]),
                      # Nhãn do MÁY CHỦ dịch, cùng bảng với màn hình điều hành (GD-1) — màn hình
                      # không tự dịch mã. Mã chưa khai thì hiện nguyên mã, không đặt tên bừa.
                      "nhan_canh_bao": [CBTB.nhan_cua(k)["nhan"] for k in sorted(v["kinds"])],
                      "han_xu_ly": v["han"],
                      "nguoi_phu_trach": ten.get(v["nguoi_nhan_id"]) if v["nguoi_nhan_id"] else None,
                      "cap_nhat": v["moi_nhat"], "alert_ids": sorted(v["alert_ids"])[:20]}
                     for v in phan]}
