"""Nhận, cất và trả lại tệp/hình ảnh đính kèm cho mọi phân hệ.

Ba chỗ dễ hỏng mà lớp này đứng chắn:

  1. LOẠI TỆP. Chỉ nhận ảnh, PDF và bảng biểu/văn bản của bộ Office. Tệp chạy được (.exe, .bat, .js, .sh…)
     bị từ chối thẳng: một kho chứng từ mà nhận tệp chạy được là một kho phát tán.
  2. KÍCH THƯỚC. Máy chủ chỉ có 512 MB; một ảnh chụp màn hình 40 MB tải lên giữa giờ cao điểm là đủ để
     cả hệ thống chậm cho mọi người. Giới hạn nằm ở đây, nói rõ bằng số cho người tải.
  3. TRÙNG. Cùng một ảnh gửi hai lần vào cùng một chứng từ không tạo hai bản ghi – nó trả về đúng bản đã có.
     Không phải để tiết kiệm chỗ, mà để người đọc hồ sơ không phải đoán hai bản giống nhau khác nhau chỗ nào.
"""
import hashlib
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.attachments import (Attachment, DOI_TUONG, DOI_TUONG_DAY_DU, LOAI_TEP,
                                     NHOM_HO_SO, NHOM_NHAY_CAM)
from app.services.storage import storage, StorageError

GIOI_HAN_MB = 25
ANH = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/gif"}
CHO_PHEP = ANH | {
    "application/pdf", "text/csv", "text/plain",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DUOI_CHO_PHEP = {"jpg", "jpeg", "png", "webp", "heic", "heif", "gif", "pdf", "csv", "txt",
                 "xls", "xlsx", "doc", "docx"}
DUOI_CAM = {"exe", "bat", "cmd", "com", "msi", "scr", "js", "vbs", "ps1", "sh", "jar", "apk", "dll"}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _duoi(ten: str) -> str:
    return (ten or "").rsplit(".", 1)[-1].lower() if "." in (ten or "") else ""


def kiem_tra_tep(ten_tep: str, kieu: str, data: bytes) -> None:
    """Từ chối SỚM và nói rõ vì sao. Người tải phải biết sửa gì, không phải đoán."""
    if not data:
        raise ValueError("Tệp rỗng – không có gì để lưu")
    mb = len(data) / 1024 / 1024
    if mb > GIOI_HAN_MB:
        raise ValueError(f"Tệp nặng {mb:.1f} MB, vượt mức cho phép {GIOI_HAN_MB} MB. Ảnh chụp màn hình thì "
                         "xuất lại ở mức vừa; tài liệu nhiều trang thì tách nhỏ theo phần.")
    d = _duoi(ten_tep)
    if d in DUOI_CAM:
        raise ValueError(f"Không nhận tệp .{d}. Kho chứng từ không chứa tệp chạy được.")
    if d and d not in DUOI_CHO_PHEP:
        raise ValueError(f"Không nhận tệp .{d}. Nhận: ảnh (jpg, png, webp, heic), pdf, "
                         "excel (xls, xlsx, csv), word (doc, docx).")
    if kieu and kieu.split(";")[0].strip() not in CHO_PHEP and d not in DUOI_CHO_PHEP:
        raise ValueError(f"Loại nội dung '{kieu}' không nằm trong danh sách được nhận")


def _an_toan(s: str) -> str:
    """Giữ lại chữ, số, gạch – bỏ dấu cách và ký tự lạ khỏi đường dẫn."""
    return "".join(ch if (ch.isalnum() or ch in "-_.") else "-" for ch in str(s or "")).strip("-")[:60] or "KHONG-MA"


def khoa_luu(doi_tuong: str, doi_tuong_id: str, checksum: str, phap_nhan: str = "", nam: int = 0,
             ky: str = "", ten_tep: str = "", loai: str = "") -> str:
    """Đường dẫn theo Mô hình quản trị số hóa mục 7.2: Pháp nhân / Năm / Nhóm hồ sơ / Tháng-hoặc-Đối tượng / Tệp.

    Vì sao không cất phẳng theo id: kiểm toán viên mở kho của một pháp nhân họ chưa từng làm việc cùng
    vẫn phải tìm ra hồ sơ mà không cần hỏi ai. Cấu trúc giống nhau ở mọi pháp nhân thì điều đó khả thi;
    mỗi phân hệ một kiểu đặt tên thì không.

    Tour và nhân sự lưu theo MÃ ĐỐI TƯỢNG (mã tour, mã NV), các nhóm còn lại theo tháng – đúng mục 7.2:
    hồ sơ một người hay một tour phải nằm gọn một chỗ, không rải ra mười hai thư mục tháng.

    Tên tệp theo quy ước Ngày_LoạiCT_MãĐốiTượng_Mã băm, KHÔNG lấy tên người dùng đặt: tên gốc chỉ để
    hiển thị, còn đường dẫn phải do hệ thống quyết định."""
    ten, _pb, nhom, theo_doi_tuong = DOI_TUONG_DAY_DU[doi_tuong]
    nam = nam or date.today().year
    muc = _an_toan(doi_tuong_id) if theo_doi_tuong else (ky or f"{date.today():%Y-%m}")
    duoi = _duoi(ten_tep)
    ten_chuan = (f"{date.today():%Y-%m-%d}_{_an_toan(loai or 'CT').upper()}_"
                 f"{_an_toan(doi_tuong_id)}_{checksum[:12]}" + (f".{duoi}" if duoi else ""))
    return f"{_an_toan(phap_nhan) if phap_nhan else 'CHUA_XAC_DINH'}/{nam}/{nhom}/{muc}/{ten_chuan}"


def dinh_kem(db: Session, doi_tuong: str, doi_tuong_id: str, ten_tep: str, data: bytes,
             kieu: str = "", loai: str = "chung_tu", mo_ta: str = "", boi: str = "",
             nguon: str = "nguoi_nhap", tac_nhan: str = "", phap_nhan: str = "", nam: int = 0,
             ky: str = "") -> tuple[Attachment, bool]:
    """Gắn một tệp vào một bản ghi. Trả về (bản ghi, có phải bản mới không)."""
    if doi_tuong not in DOI_TUONG:
        raise ValueError(f"Không gắn tệp vào '{doi_tuong}' – đối tượng hợp lệ: {', '.join(DOI_TUONG)}")
    if not str(doi_tuong_id or "").strip():
        raise ValueError("Thiếu mã bản ghi cần gắn tệp – tệp không gắn vào đâu thì sau này không ai tìm ra")
    if loai not in LOAI_TEP:
        raise ValueError(f"Loại tệp '{loai}' không hợp lệ ({', '.join(LOAI_TEP)})")
    kiem_tra_tep(ten_tep, kieu, data)
    doi_tuong_id = str(doi_tuong_id).strip()
    _ten, _pb, nhom, _td = DOI_TUONG_DAY_DU[doi_tuong]
    cs = _sha(data)
    da_co = db.execute(select(Attachment).where(
        Attachment.doi_tuong == doi_tuong, Attachment.doi_tuong_id == doi_tuong_id,
        Attachment.checksum == cs)).scalars().first()
    if da_co is not None:
        if da_co.thu_hoi:
            # Tệp từng bị thu hồi mà nay được gắn lại: mở lại chính bản ghi cũ và GIỮ dấu vết lần thu hồi
            # trong mô tả, chứ không tạo bản ghi mới sạch sẽ như chưa có gì xảy ra.
            da_co.thu_hoi = False
            da_co.mo_ta = (da_co.mo_ta + f" [gắn lại {datetime.now():%d/%m/%Y} bởi {boi}; "
                                         f"trước đó thu hồi vì: {da_co.ly_do_thu_hoi or 'không ghi lý do'}]").strip()
            db.flush()
        return da_co, False
    nam = nam or date.today().year
    key = khoa_luu(doi_tuong, doi_tuong_id, cs, phap_nhan, nam, ky, ten_tep, loai)
    luu = storage().put(key, data, kieu or "application/octet-stream")
    a = Attachment(doi_tuong=doi_tuong, doi_tuong_id=doi_tuong_id, phong_ban=DOI_TUONG[doi_tuong][1],
                   phap_nhan=(phap_nhan or "")[:30], nam=nam, nhom_ho_so=nhom,
                   nhay_cam=nhom in NHOM_NHAY_CAM,
                   loai=loai, ten_tep=(ten_tep or "tep")[:200], kieu_noi_dung=(kieu or "")[:80],
                   kich_thuoc=len(data), checksum=luu.checksum, khoa_luu=luu.key,
                   la_anh=(kieu or "").split(";")[0].strip() in ANH or _duoi(ten_tep) in
                   {"jpg", "jpeg", "png", "webp", "heic", "heif", "gif"},
                   mo_ta=(mo_ta or "")[:2000], nguon=nguon, tac_nhan=(tac_nhan or "")[:80], boi=boi)
    db.add(a); db.flush()
    return a, True


def doc(db: Session, a: Attachment) -> bytes:
    """Đọc lại nội dung và ĐỐI CHIẾU băm. Lệch băm là dừng, không trả về nội dung sai."""
    data = storage().get(a.khoa_luu)
    if _sha(data) != a.checksum:
        raise StorageError("Nội dung tệp không khớp mã kiểm tra ghi lúc tải lên – tệp có thể đã bị thay "
                           "đổi hoặc lẫn với tệp khác. Không trả về nội dung này.")
    return data


def thu_hoi(db: Session, a: Attachment, boi: str, ly_do: str) -> Attachment:
    """Gỡ một tệp khỏi hồ sơ. Bản ghi vẫn còn – biến mất không dấu vết là cách làm bế tắc một cuộc kiểm toán."""
    if not str(ly_do or "").strip():
        raise ValueError("Gỡ tệp phải ghi lý do – người đọc hồ sơ sau này cần biết tệp đó đi đâu")
    if a.thu_hoi:
        raise ValueError("Tệp này đã được thu hồi trước đó")
    a.thu_hoi = True; a.thu_hoi_boi = boi; a.thu_hoi_luc = datetime.now()
    a.ly_do_thu_hoi = str(ly_do).strip()[:200]
    db.flush()
    return a


def ra(a: Attachment) -> dict:
    return {"id": a.id, "doi_tuong": a.doi_tuong, "phap_nhan": a.phap_nhan, "nam": a.nam,
            "nhom_ho_so": a.nhom_ho_so, "nhom_ten": NHOM_HO_SO.get(a.nhom_ho_so, (a.nhom_ho_so, ""))[0],
            "thoi_han_luu": NHOM_HO_SO.get(a.nhom_ho_so, ("", ""))[1], "nhay_cam": a.nhay_cam, "doi_tuong_ten": DOI_TUONG.get(a.doi_tuong, (a.doi_tuong,))[0],
            "doi_tuong_id": a.doi_tuong_id, "phong_ban": a.phong_ban, "loai": a.loai,
            "loai_ten": LOAI_TEP.get(a.loai, a.loai), "ten_tep": a.ten_tep, "kieu": a.kieu_noi_dung,
            "kich_thuoc": a.kich_thuoc, "la_anh": a.la_anh, "mo_ta": a.mo_ta, "nguon": a.nguon,
            "tac_nhan": a.tac_nhan, "boi": a.boi, "luc": a.luc, "hash": a.checksum[:12],
            "thu_hoi": a.thu_hoi, "thu_hoi_boi": a.thu_hoi_boi, "thu_hoi_luc": a.thu_hoi_luc,
            "ly_do_thu_hoi": a.ly_do_thu_hoi}


# Ai đọc được hồ sơ nhân sự (Nghị định 13/2023 + mục 7.3): HCNS giữ hồ sơ, Ban TGĐ và Chủ tịch điều hành,
# Ban Kiểm soát rà soát. CNTT vận hành hệ thống nhưng KHÔNG đọc hợp đồng lao động của từng người.
VAI_TRO_NHAY_CAM = ("hcns", "tgd", "chutich", "bks")


def duoc_doc(a: Attachment, vai_tro: str) -> bool:
    return (not a.nhay_cam) or vai_tro in VAI_TRO_NHAY_CAM


def danh_sach(db: Session, doi_tuong: str = "", doi_tuong_id: str = "", phong_ban: str = "",
              ke_ca_thu_hoi: bool = False, limit: int = 200, vai_tro: str = "",
              nhom_ho_so: str = "", phap_nhan: str = "") -> list[dict]:
    q = select(Attachment).order_by(Attachment.id.desc())
    if nhom_ho_so: q = q.where(Attachment.nhom_ho_so == nhom_ho_so)
    if phap_nhan: q = q.where(Attachment.phap_nhan == phap_nhan)
    if vai_tro and vai_tro not in VAI_TRO_NHAY_CAM:
        q = q.where(Attachment.nhay_cam == False)   # noqa: E712
    if doi_tuong: q = q.where(Attachment.doi_tuong == doi_tuong)
    if doi_tuong_id: q = q.where(Attachment.doi_tuong_id == str(doi_tuong_id).strip())
    if phong_ban: q = q.where(Attachment.phong_ban == phong_ban)
    if not ke_ca_thu_hoi: q = q.where(Attachment.thu_hoi == False)   # noqa: E712
    return [ra(a) for a in db.execute(q.limit(limit)).scalars()]
