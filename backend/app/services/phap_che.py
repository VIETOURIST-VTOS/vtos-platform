"""Đợt D1 – phép tính của IR & Pháp chế. Quy tắc xác định, không suy đoán.

HAI VIỆC:

  · Sửa một văn bản ĐÃ CÓ HIỆU LỰC sinh PHIÊN BẢN MỚI, không ghi đè. Bản nháp thì sửa tại chỗ.
  · Trạng thái một lần công bố (chưa đến hạn / sắp đến hạn / quá hạn / đã công bố) tính từ hạn chốt
    và thời điểm đã công bố — không ai gõ trạng thái vào.

VÌ SAO KHÔNG CHO GÕ TRẠNG THÁI: một ô "đã công bố" người gõ được là một lời khai. Thứ chứng minh
được là THỜI ĐIỂM công bố cộng NƠI công bố cộng VĂN BẢN đã công bố — ba thứ ấy có thì trạng thái tự
ra, và ra giống nhau mọi lần chạy.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.phap_che import BanGhiCongBo, NghiaVuCongBo, VanBanPhapChe

# Bao nhiêu ngày trước hạn thì gọi là "sắp đến hạn". Đây là một lựa chọn VẬN HÀNH, không phải một
# con số luật: nó chỉ quyết định cảnh báo hiện sớm hay muộn, không đụng tới hạn thật.
NGAY_BAO_SOM = 7

TRANG_THAI_BG = {
    "chua_ro_han": "Chưa xác định được hạn",
    "chua_den_han": "Chưa đến hạn",
    "sap_den_han": "Sắp đến hạn",
    "qua_han": "QUÁ HẠN – chưa công bố",
    "da_cong_bo": "Đã công bố đúng hạn",
    "cong_bo_tre": "Đã công bố NHƯNG trễ hạn",
}

# Trạng thái phiên bản văn bản mà sửa vào đó phải sinh bản mới thay vì ghi đè.
DA_RA_NGOAI = ("hieu_luc", "thay_the", "het_hieu_luc")


# ====================== VĂN BẢN CÓ PHIÊN BẢN ======================
def cac_phien_ban(db: Session, goc_id: int) -> list[VanBanPhapChe]:
    return list(db.execute(select(VanBanPhapChe).where(VanBanPhapChe.goc_id == goc_id)
                           .order_by(VanBanPhapChe.so_ban)).scalars())


def ban_hieu_luc(db: Session, goc_id: int) -> VanBanPhapChe | None:
    for v in cac_phien_ban(db, goc_id):
        if v.trang_thai == "hieu_luc":
            return v
    return None


def tao_moi(db: Session, data: dict, boi: str) -> VanBanPhapChe:
    """Phiên bản 1 của một văn bản mới. `goc_id` trỏ về chính nó sau khi có id."""
    v = VanBanPhapChe(so_ban=1, boi=boi, luc=datetime.now(), **data)
    db.add(v)
    db.flush()
    v.goc_id = v.id
    db.flush()
    return v


def sua(db: Session, v: VanBanPhapChe, data: dict, ly_do: str, boi: str) -> VanBanPhapChe:
    """Sửa một phiên bản. Bản nháp sửa TẠI CHỖ; bản đã ra ngoài thì sinh PHIÊN BẢN MỚI.

    Ranh giới nằm ở chỗ văn bản đã rời khỏi tay người soạn hay chưa. Một bản nháp sửa tại chỗ là
    chuyện bình thường và không ai cần biết. Một bản ĐÃ CÓ HIỆU LỰC bị sửa tại chỗ thì mọi quyết
    định đã ra theo bản cũ trở thành không giải trình được — và chỗ hỏng ấy không hiện ra ngay, nó
    hiện ra lúc có người hỏi lại, thường là lúc muộn nhất.
    """
    if v.trang_thai not in DA_RA_NGOAI:
        for k, x in data.items():
            setattr(v, k, x)
        v.ly_do_sua = ly_do or v.ly_do_sua
        db.flush()
        return v
    if v.bi_thay_boi is not None:
        raise ValueError(f"Bản {v.so_ban} đã bị phiên bản sau thay thế – sửa bản mới nhất")
    cu = {"goc_id": v.goc_id, "loai": v.loai, "so_hieu": v.so_hieu, "tieu_de": v.tieu_de,
          "tom_tat": v.tom_tat, "hieu_luc_tu": v.hieu_luc_tu, "hieu_luc_den": v.hieu_luc_den,
          "nguoi_ky": v.nguoi_ky, "ngay_ky": v.ngay_ky, "attachment_id": v.attachment_id}
    cu.update(data)
    moi = VanBanPhapChe(so_ban=v.so_ban + 1, trang_thai="nhap", ly_do_sua=ly_do or "",
                        boi=boi, luc=datetime.now(), **cu)
    db.add(moi)
    db.flush()
    return moi


def ban_hanh(db: Session, v: VanBanPhapChe, hieu_luc_tu: date | None, boi: str) -> VanBanPhapChe:
    """Cho một phiên bản có hiệu lực, và đóng dấu phiên bản trước nó.

    Đóng bản trước TRONG CÙNG lời gọi này, không để thành hai bước: hai bước nghĩa là có một
    khoảnh khắc hai phiên bản cùng ở trạng thái hiệu lực, và mọi lần hỏng đều rơi vào khoảnh khắc ấy.
    """
    if v.trang_thai == "hieu_luc":
        raise ValueError("Phiên bản này đã có hiệu lực")
    cu = ban_hieu_luc(db, v.goc_id or v.id)
    tu = hieu_luc_tu or date.today()
    if cu is not None and cu.id != v.id:
        cu.trang_thai = "thay_the"
        cu.bi_thay_boi = v.id
        cu.hieu_luc_den = tu - timedelta(days=1)
    v.trang_thai = "hieu_luc"
    v.hieu_luc_tu = tu
    db.flush()
    return v


def ra_vb(v: VanBanPhapChe) -> dict:
    return {"id": v.id, "goc_id": v.goc_id, "phien_ban": v.so_ban, "loai": v.loai,
            "so_hieu": v.so_hieu, "tieu_de": v.tieu_de, "tom_tat": v.tom_tat,
            "trang_thai": v.trang_thai, "hieu_luc_tu": v.hieu_luc_tu,
            "hieu_luc_den": v.hieu_luc_den, "bi_thay_boi": v.bi_thay_boi,
            "ly_do_sua": v.ly_do_sua, "nguoi_ky": v.nguoi_ky, "ngay_ky": v.ngay_ky,
            "co_tep": v.attachment_id is not None, "boi": v.boi, "luc": v.luc}


# ====================== NGHĨA VỤ VÀ BẢN GHI CÔNG BỐ ======================
def trang_thai_bg(bg: BanGhiCongBo, hom_nay: date | None = None) -> str:
    """Quy tắc xác định. Cùng dữ liệu luôn ra cùng trạng thái, mọi lần chạy."""
    nay = hom_nay or date.today()
    if bg.da_cong_bo_luc is not None:
        if bg.han_chot is None:
            return "da_cong_bo"
        return "da_cong_bo" if bg.da_cong_bo_luc.date() <= bg.han_chot else "cong_bo_tre"
    if bg.han_chot is None:
        # RỖNG không phải "còn nhiều thời gian". Chưa biết hạn là một việc phải xử lý, không phải
        # một việc để yên tâm – nên nó có trạng thái riêng chứ không rơi vào "chưa đến hạn".
        return "chua_ro_han"
    if nay > bg.han_chot:
        return "qua_han"
    if (bg.han_chot - nay).days <= NGAY_BAO_SOM:
        return "sap_den_han"
    return "chua_den_han"


def han_tu_moc(nv: NghiaVuCongBo, moc: date | None) -> date | None:
    """Hạn chốt suy từ mốc phát sinh, CHỈ KHI nghĩa vụ khai hạn bằng số ngày.

    Không khai số ngày thì trả None, và người lập bản ghi tự điền hạn. Đoán một hạn ở đây là đoán
    một con số pháp lý – thứ lần viết phần mềm không được đặt.
    """
    if moc is None or nv.han_sau_ngay is None:
        return None
    return moc + timedelta(days=int(nv.han_sau_ngay))


def ra_bg(db: Session, bg: BanGhiCongBo, hom_nay: date | None = None) -> dict:
    nv = db.get(NghiaVuCongBo, bg.nghia_vu_id)
    tt = trang_thai_bg(bg, hom_nay)
    return {"id": bg.id, "nghia_vu_id": bg.nghia_vu_id,
            "nghia_vu_ma": nv.ma if nv else "", "nghia_vu_ten": nv.ten if nv else "",
            "ky": bg.ky, "moc_phat_sinh": bg.moc_phat_sinh, "han_chot": bg.han_chot,
            "da_cong_bo_luc": bg.da_cong_bo_luc, "noi_cong_bo": bg.noi_cong_bo,
            "van_ban_id": bg.van_ban_id, "ghi_chu": bg.ghi_chu,
            "trang_thai": tt, "trang_thai_ten": TRANG_THAI_BG[tt],
            "boi": bg.boi, "luc": bg.luc}


def bang_dieu_khien(db: Session, hom_nay: date | None = None) -> dict:
    """Những gì Pháp chế cần nhìn thấy mỗi sáng, xếp theo mức phải xử lý giảm dần."""
    nay = hom_nay or date.today()
    ds = [ra_bg(db, b, nay) for b in db.execute(select(BanGhiCongBo)).scalars()]
    nhom: dict[str, list] = {k: [] for k in TRANG_THAI_BG}
    for d in ds:
        nhom[d["trang_thai"]].append(d)
    for k in nhom:
        nhom[k].sort(key=lambda d: (d["han_chot"] is None, d["han_chot"] or date.max))
    so_nghia_vu = len(list(db.execute(select(NghiaVuCongBo)).scalars()))
    return {
        "hom_nay": nay, "ngay_bao_som": NGAY_BAO_SOM,
        "so_nghia_vu_da_khai": so_nghia_vu,
        "theo_trang_thai": {k: {"so": len(v), "ten": TRANG_THAI_BG[k], "rows": v}
                            for k, v in nhom.items()},
        "ghi_chu": ("Danh mục nghĩa vụ công bố và thời hạn là QUY ĐỊNH PHÁP LUẬT – hệ thống không "
                    "nạp sẵn dòng nào. Pháp chế khai từng nghĩa vụ kèm căn cứ điều khoản. Bảng "
                    "rỗng nghĩa là chưa ai khai, KHÔNG nghĩa là công ty không có nghĩa vụ nào."),
    }
