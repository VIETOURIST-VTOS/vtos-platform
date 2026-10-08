"""Ghi dấu nguồn quảng cáo: chuẩn hoá, chống trùng, khớp lead.

Tệp này KHÔNG quy kết doanh thu cho kênh nào. Xem chốt 1 ở `models/quang_cao.py`.
"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crm import Lead
from app.models.quang_cao import DauQuangCao
from app.services.zalo import norm_phone

# Dài hơn thì cắt – mọi cột chữ ở bảng này đều có trần, và để cơ sở dữ liệu báo lỗi độ dài thay
# vì cắt ở đây là để một webhook dài bất thường làm hỏng cả lượt nhận.
TRAN = {"nen_tang": 24, "loai_ma": 24, "ma": 200, "ma_chien_dich": 64, "ma_nhom_qc": 64,
        "ma_mau_qc": 64, "ten_chien_dich": 200, "sdt": 20, "zalo_uid": 40,
        "trang_dich": 500, "trang_gioi_thieu": 500, "nguon_ghi": 24, "ghi_chu": 300}


def _chu(v, cot: str) -> str:
    return str(v or "").strip()[:TRAN[cot]]


def _nhan(v) -> str:
    """Nhãn phân loại: thường hoá và bỏ khoảng trắng, để 'Facebook' và 'facebook' là một."""
    return "".join(ch for ch in str(v or "").strip().lower() if not ch.isspace())


def khoa(nen_tang: str, loai_ma: str, ma: str, sdt: str, cham_luc: datetime | None) -> str:
    """Khoá chống trùng. Có mã thì khoá LÀ mã; không mã thì ghép từ số và PHÚT chạm.

    Vì sao tới phút chứ không tới giây: tổng đài và webhook hay gửi lại cùng một sự kiện với
    đồng hồ lệch vài giây. Tới giây thì một cuộc gọi thành ba dòng. Tới phút thì hai cuộc gọi
    thật trong cùng một phút của cùng một số gộp làm một – chuyện ấy hiếm, và khi nó xảy ra thì
    đếm thiếu một lần chạm còn đỡ hơn đếm thừa hai lần không có thật.
    """
    nt, lm = _nhan(nen_tang) or "khac", _nhan(loai_ma) or "khac"
    m = str(ma or "").strip()
    if m:
        return f"{nt}:{lm}:{m}"[:160]
    phut = f"{cham_luc:%Y%m%d%H%M}" if cham_luc else "khong-gio"
    return f"{nt}:{lm}:{norm_phone(sdt) or 'khong-sdt'}:{phut}"[:160]


def tim_lead(db: Session, sdt: str, zalo_uid: str) -> Lead | None:
    """Khớp dấu với một lead đã có. KHÔNG tạo lead mới – xem chú thích ở `ghi()`."""
    uid = str(zalo_uid or "").strip()
    if uid:
        l = db.execute(select(Lead).where(Lead.zalo_uid == uid)
                       .order_by(Lead.id.desc())).scalars().first()
        if l:
            return l
    ph = norm_phone(sdt)
    if len(ph) >= 9:
        return db.execute(select(Lead).where(Lead.phone == ph)
                          .order_by(Lead.id.desc())).scalars().first()
    return None


def ghi(db: Session, d: dict, boi: str = "") -> tuple[DauQuangCao, bool]:
    """Ghi một lần chạm. Trả về (dòng, có_phải_dòng_mới).

    KHÔNG TẠO LEAD. Một dấu quảng cáo là bằng chứng ai đó đã bấm vào một mẫu quảng cáo; nó không
    đủ để nói đã có một khách hàng tiềm năng. Cho cửa này tạo lead là mở một đường thứ năm vào
    bảng `leads` – bên cạnh cửa nạp, nút nhập Excel cũ, nút nhập tay và webhook Zalo – và đường
    thứ năm ấy không đi qua bộ kiểm nào. Dấu nào chưa khớp được lead thì nằm chờ, và SỐ DÒNG CHỜ
    chính là con số đo được việc ghép có chạy hay không.

    Gọi lại với cùng một khoá thì KHÔNG ghi đè nội dung cũ, chỉ bù những ô đang rỗng. Webhook gửi
    lại thường mang ít thông tin hơn lần đầu; ghi đè là tự làm nghèo bản ghi của chính mình.
    """
    nen_tang = _nhan(d.get("nen_tang")) or "khac"
    loai_ma = _nhan(d.get("loai_ma")) or "khac"
    ma = _chu(d.get("ma"), "ma")
    sdt = norm_phone(d.get("sdt"))[:TRAN["sdt"]]
    uid = _chu(d.get("zalo_uid"), "zalo_uid")
    # Ô TRỐNG LÀ CHƯA BIẾT, KHÔNG PHẢI SAI. Cửa nhận khai `cham_luc: str = ""`, nên một gói
    # không gửi giờ sẽ tới đây là chuỗi rỗng. Coi nó là lỗi thì mọi dấu không kèm giờ – phần lớn
    # dấu từ mã khuyến mãi và từ tệp nạp – đều bị từ chối, và từ chối thì mất vĩnh viễn.
    cham = d.get("cham_luc")
    if isinstance(cham, str):
        cham = cham.strip()
        if not cham:
            cham = None
        else:
            try:
                cham = datetime.fromisoformat(cham)
            except ValueError:
                raise ValueError(f"cham_luc không đọc được: {cham!r} – cần dạng 2026-10-07 09:20:00")
    if cham is not None and not isinstance(cham, datetime):
        raise ValueError("cham_luc phải là thời điểm")
    # Thời điểm chạm Ở TƯƠNG LAI là dấu hiệu đồng hồ nguồn sai hoặc múi giờ chưa quy đổi. Nhận nó
    # vào thì mọi phép đếm theo kỳ lệch, và Google từ chối chuyển đổi có giờ sau giờ gửi.
    if cham is not None and cham > datetime.now():
        raise ValueError("cham_luc nằm ở tương lai – kiểm lại múi giờ của nguồn gửi")

    k = khoa(nen_tang, loai_ma, ma, sdt, cham)
    cu = db.execute(select(DauQuangCao).where(DauQuangCao.khoa_chong_trung == k)).scalars().first()
    if cu is not None:
        for cot in ("ma_chien_dich", "ma_nhom_qc", "ma_mau_qc"):
            if not getattr(cu, cot) and d.get(cot):
                setattr(cu, cot, _chu(d.get(cot), cot))
        for cot in ("ten_chien_dich", "trang_dich", "trang_gioi_thieu", "ghi_chu"):
            if not getattr(cu, cot) and d.get(cot):
                setattr(cu, cot, _chu(d.get(cot), cot))
        if not cu.sdt and sdt:
            cu.sdt = sdt
        if not cu.zalo_uid and uid:
            cu.zalo_uid = uid
        if not cu.utm and d.get("utm"):
            cu.utm = dict(d["utm"])
        if cu.lead_id is None:
            l = tim_lead(db, cu.sdt, cu.zalo_uid)
            if l:
                cu.lead_id = l.id
        return cu, False

    l = tim_lead(db, sdt, uid)
    row = DauQuangCao(
        nen_tang=nen_tang, loai_ma=loai_ma, ma=ma, khoa_chong_trung=k,
        ma_chien_dich=_chu(d.get("ma_chien_dich"), "ma_chien_dich") or None,
        ma_nhom_qc=_chu(d.get("ma_nhom_qc"), "ma_nhom_qc") or None,
        ma_mau_qc=_chu(d.get("ma_mau_qc"), "ma_mau_qc") or None,
        ten_chien_dich=_chu(d.get("ten_chien_dich"), "ten_chien_dich"),
        sdt=sdt, zalo_uid=uid, lead_id=(l.id if l else None),
        utm=dict(d.get("utm") or {}),
        trang_dich=_chu(d.get("trang_dich"), "trang_dich"),
        trang_gioi_thieu=_chu(d.get("trang_gioi_thieu"), "trang_gioi_thieu"),
        cham_luc=cham, nguon_ghi=_nhan(d.get("nguon_ghi")) or "khac",
        than_nguyen_van=str(d.get("than_nguyen_van") or ""),
        ghi_chu=_chu(d.get("ghi_chu"), "ghi_chu"), boi=str(boi or "")[:50])
    db.add(row)
    db.flush()
    return row, True


def ghep_lead_con_thieu(db: Session, toi_da: int = 2000) -> int:
    """Ghép lại những dấu chưa có lead – lead thường tới SAU cái chạm.

    Khách bấm quảng cáo lúc 9 giờ, tới 11 giờ mới gọi điện và Sales mới lập lead. Lúc ghi dấu thì
    chưa có gì để khớp. Hàm này là lượt quét lại, robot gọi.
    """
    n = 0
    for r in db.execute(select(DauQuangCao).where(DauQuangCao.lead_id.is_(None))
                        .order_by(DauQuangCao.id.desc()).limit(toi_da)).scalars():
        l = tim_lead(db, r.sdt, r.zalo_uid)
        if l:
            r.lead_id = l.id
            n += 1
    if n:
        db.commit()
    return n


def bang_do(db: Session) -> dict:
    """Mấy con số của màn hình. RỖNG KHÁC KHÔNG: chưa có dấu nào thì tỷ lệ ghép là None."""
    from sqlalchemy import func
    tong = int(db.execute(select(func.count()).select_from(DauQuangCao)).scalar() or 0)
    co_lead = int(db.execute(select(func.count()).select_from(DauQuangCao)
                             .where(DauQuangCao.lead_id.is_not(None))).scalar() or 0)
    theo_nen_tang = [{"nen_tang": k, "so": int(v)} for k, v in db.execute(
        select(DauQuangCao.nen_tang, func.count()).group_by(DauQuangCao.nen_tang)
        .order_by(func.count().desc())).all()]
    return {"tong": tong, "da_ghep_lead": co_lead, "chua_ghep": tong - co_lead,
            "ty_le_ghep": (round(co_lead / tong, 3) if tong else None),
            "theo_nen_tang": theo_nen_tang}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# LẦN CHẠM ĐẦU VÀ LẦN CHẠM CUỐI CỦA MỘT LEAD — Chủ tịch chốt HIỆN CẢ HAI, 08/10/2026
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
# VÌ SAO HAI CHỨ KHÔNG MỘT. Một khách thấy quảng cáo Facebook hôm thứ hai, thứ năm gõ tên công ty
# lên Google rồi bấm vào, thứ bảy mới gọi hotline. Lấy lần chạm ĐẦU là ghi công cho kênh MANG
# KHÁCH ĐẾN; lấy lần CUỐI là ghi công cho kênh CHỐT ĐƯỢC. Cả hai đều đúng một nửa, và chỗ chênh
# nhau giữa hai con số mới là thứ đáng xem: kênh nào đang nuôi quỹ khách mà không bao giờ được
# ghi công, kênh nào đang nhận công của người khác. Chọn sẵn một trong hai rồi chỉ hiện cái ấy là
# giấu đi nửa câu chuyện ngay trong lúc phòng Marketing đang quyết chia ngân sách.
#
# XẾP THEO GIỜ NÀO. `cham_luc` (nền tảng báo) là giờ thật, nhưng RỖNG ĐƯỢC – mã khuyến mãi và tệp
# nạp thường không kèm giờ. Nên khoá xếp là `cham_luc` rồi mới tới `nhan_luc` (lúc VTOS ghi), rồi
# tới `id` cho hai dòng cùng giờ vẫn ra một thứ tự cố định. NHƯNG ô `cham_luc` trả về cho màn hình
# vẫn là giá trị THẬT, rỗng thì để rỗng: lấy `nhan_luc` lấp vào chỗ `cham_luc` là bịa ra một mốc
# giờ khách chưa từng chạm, và mốc bịa ấy đi thẳng vào phép đếm 30 / 60 / 90 ngày.
#
# MỘT CÂU HỎI CHO CẢ TRANG. Màn hình lead trả tới 2000 dòng. Hỏi riêng từng lead là 2000 câu hỏi
# cho một lần mở màn hình. `dau_dau_cuoi()` nhận CẢ DANH SÁCH mã lead và chỉ bắn một câu.

# Lead chưa có dấu nào thì KHÔNG phải số không — là CHƯA BIẾT. Trả None chứ không trả một khối
# toàn chuỗi rỗng, để màn hình in "—" chứ không in ra một nền tảng tên là rỗng.
KHONG_CO_DAU = {"dau_cham_dau": None, "dau_cham_cuoi": None, "so_lan_cham": 0}


def _khoi_mot_dau(r: DauQuangCao) -> dict:
    """Một lần chạm, gọn còn tám ô đủ cho màn hình lead và cho báo cáo hiệu quả quảng cáo."""
    return {"nen_tang": r.nen_tang, "loai_ma": r.loai_ma,
            "ma_chien_dich": r.ma_chien_dich or "", "ten_chien_dich": r.ten_chien_dich or "",
            "cham_luc": r.cham_luc, "nhan_luc": r.nhan_luc,
            "nguon_ghi": r.nguon_ghi or "", "trang_dich": r.trang_dich or "",
            "utm": dict(r.utm or {})}


def _gio_xep(r: DauQuangCao):
    return (r.cham_luc or r.nhan_luc or datetime.min, r.id or 0)


def dau_dau_cuoi(db: Session, lead_ids) -> dict[int, dict]:
    """Lần chạm đầu và lần chạm cuối của TỪNG lead trong danh sách, bằng MỘT câu hỏi.

    Trả về một bảng tra `{mã lead: {dau_cham_dau, dau_cham_cuoi, so_lan_cham}}` có đủ MỌI mã lead
    được hỏi – lead không có dấu nào vẫn có một ô, mang khối rỗng. Người gọi nhờ thế không phải
    phân biệt 'không hỏi' với 'hỏi rồi mà không có'.
    """
    ids = sorted({int(i) for i in lead_ids if i})
    ket = {i: dict(KHONG_CO_DAU) for i in ids}
    if not ids:
        return ket
    theo = {}
    for r in db.execute(select(DauQuangCao)
                        .where(DauQuangCao.lead_id.in_(ids))).scalars():
        theo.setdefault(int(r.lead_id), []).append(r)
    for lid, ds in theo.items():
        ds.sort(key=_gio_xep)
        ket[lid] = {"dau_cham_dau": _khoi_mot_dau(ds[0]), "dau_cham_cuoi": _khoi_mot_dau(ds[-1]),
                    "so_lan_cham": len(ds)}
    return ket


def dau_cua_lead(db: Session, lead_id: int | None) -> dict:
    """Bản một lead, cho các cửa chỉ trả về MỘT dòng (tạo lead, sửa lead).

    Cửa danh sách KHÔNG được gọi hàm này trong vòng lặp – gọi `dau_dau_cuoi()` một lần cho cả
    trang. Phép thử `test_tc110` canh đúng chỗ ấy.
    """
    return dau_dau_cuoi(db, [lead_id]).get(int(lead_id or 0)) or dict(KHONG_CO_DAU)
