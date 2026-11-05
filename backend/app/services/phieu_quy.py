# -*- coding: utf-8 -*-
"""Phiếu quỹ tiền mặt — quỹ vào sổ kế toán bằng một CỬA, không bằng tay ai đó.

Chủ tịch chốt 04/11/2026: bảng phiếu quỹ RIÊNG, và GHI SỔ NGAY (không thêm bước xác nhận).

VÌ SAO KHÔNG DÙNG `Receipt`: `Receipt.booking_id` là NOT NULL ở tầng cơ sở dữ liệu, nên một khoản
nộp quỹ / hoàn ký quỹ / thu khác không thể là một `Receipt`. Và `Receipt` là phiếu thu CỦA KHÁCH
(`payer`, `bank_txn_id`, `method`); nhét "nộp quỹ vào ngân hàng" vào đấy là mô hình sai.

KHÔNG MỘT CẶP TÀI KHOẢN NÀO GÕ CỨNG TRONG TỆP NÀY. Phiếu quỹ dựng bối cảnh rồi hỏi bảng quy ước
(`hach_toan.xem_truoc`). Không có quy tắc nào khớp thì TỪ CHỐI lập phiếu — không lưu một phiếu
treo. Lưu phiếu mà không ghi sổ là dựng một rổ chờ thứ hai không ai canh, và số dư quỹ trên màn
hình sẽ lệch với sổ mà không gì kêu lên. Đúng ranh giới 09/9/2026: máy không đoán hộ người.
"""
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.payments import PhieuQuy
from app.services import accounting as ACC
from app.services import hach_toan as HT
from app.services import ket_so as KS
from app.services import ma_tu_sinh as MTS

# chiều → (nguồn nghiệp vụ của bảng quy ước, tiền tố mã phiếu, mã nghiệp vụ chứng từ)
#
# Tiền tố PTQ / PCQ chứ không PT / PC: `Receipt` đã cấp mã `PT{yymm}-nnnn`, và `ma_tu_sinh.tiep_theo`
# đếm theo TIỀN TỐ trên từng bảng. Dùng lại `PT` thì hai bảng cấp hai dãy số trùng nhau, và lúc
# đối chiếu với kiểm toán sẽ có hai tờ chứng từ khác nhau cùng mang một số.
CHIEU = {
    "thu": ("tien_vao", "PTQ", "thu_quy_tien_mat"),
    "chi": ("tien_ra", "PCQ", "chi_quy_tien_mat"),
}
# KS-19j (06/11/2026): `post_entry` nhận tên nghiệp vụ qua BIẾN (theo chiều thu/chi) — khai bảng riêng để
# phép thử E3 (test_e3_3b/3c) kiểm được từng giá trị có trong `chung_tu_loai.NGHIEP_VU`.
NGHIEP_VU_THEO_CHIEU = {k: v[2] for k, v in CHIEU.items()}


def ly_do_nhan_duoc(db: Session, chieu: str) -> list[dict]:
    """Những lý do bảng quy ước ĐANG nhận cho chiều này, kèm quy tắc tương ứng.

    Đọc SỐNG từ bảng quy ước qua `ket_so.goi_y_phan_loai` chứ không chép thành một danh sách thứ
    hai: thêm một quy tắc là lý do mới tự hiện ra ở ô chọn, và không ai phải sửa hai chỗ.
    """
    if chieu not in CHIEU:
        raise ValueError(f"Chiều phiếu quỹ phải là 'thu' hoặc 'chi', không phải {chieu!r}")
    return KS.goi_y_phan_loai(db, CHIEU[chieu][0])


def _boi_canh(code: str, ngay: date, chieu: str, ly_do: str, noi_dung: str,
              ten_doi_tuong: str, ma_doi_tuong: str, booking_id: int | None,
              khoan_muc: str) -> dict:
    """Bối cảnh để tra bảng quy ước.

    `hinh_thuc_tt = "tien_mat"` là BIẾT CHẮC chứ không đoán: tờ phiếu này là tờ phiếu quỹ, tiền
    đi qua quỹ. Nhờ luật "cụ thể thắng chung chung" (xem `hach_toan.dang_hieu_luc`), sáu dòng tiền
    mặt của Đợt R2 thắng sáu dòng ngân hàng tương ứng — vì một LUẬT, không vì hai con số ưu tiên
    tình cờ hơn kém nhau.

    BỐN KHOÁ ĐỐI TƯỢNG CÙNG MỘT GIÁ TRỊ, và đó là chủ ý: quy tắc khai `doi_tuong` của riêng nó
    (`khach` / `ncc` / `nhan_vien` / `ngan_hang`), và `dung_but_toan` chỉ đọc đúng khoá nó khai.
    Bắt người lập phiếu chọn thêm "đây là đối tượng loại gì" là bắt họ đoán lại một thứ bảng quy
    ước đã khai rồi — và đoán sai thì bút toán thiếu mã đối tượng, mà 131/331/141 bắt buộc có.
    """
    khoa_ly_do = "muc_thu" if chieu == "thu" else "muc_chi"
    bc = {
        "noi_dung": noi_dung or "",
        "ma": code,
        "so_chung_tu": code,
        "hinh_thuc_tt": "tien_mat",
        "khop_don": bool(booking_id),
        "booking_id": booking_id,
        "ky": f"{ngay:%Y-%m}",
    }
    if (ly_do or "").strip():
        bc[khoa_ly_do] = ly_do.strip()
    if khoan_muc:
        bc["khoan_muc"] = khoan_muc.strip().upper()
    ten, ma = (ten_doi_tuong or "").strip(), (ma_doi_tuong or "").strip()
    if ten or ma:
        for k in ("khach", "ncc", "nhan_vien", "ngan_hang"):
            bc[k] = ten or ma
            bc["ma_" + k] = ma or ten
    return bc


def _gan_doi_tuong(lines: list[dict], ten: str, ma: str) -> None:
    """Điền mã đối tượng người lập chỉ định vào những dòng còn thiếu.

    Cùng việc và cùng lý do với `ket_so._gan_doi_tuong`, viết riêng vì hàm kia nhận một dòng sao
    kê ngân hàng chứ không nhận một tờ phiếu quỹ.

    VÌ SAO CẦN: một số tài khoản BẮT BUỘC có mã đối tượng (131, 331, 3388, 141, 341…), nhưng quy
    tắc chỉ điền đối tượng cho vế nó KHAI trong cột `doi_tuong`. `THU_CHUA_RO_TM` khai
    `doi_tuong = ""` mà vế Có của nó là 3388 — nên nếu không có bước này, mọi phiếu thu tiền mặt
    chưa rõ đơn đều bị `post_entry` chặn với câu "Tài khoản 3388 phải ghi mã đối tượng", và người
    thủ quỹ không có cách nào đi tiếp. Đo được lúc chạy thật 04/11/2026.

    KHÔNG tự nghĩ ra mã: chỉ điền thứ NGƯỜI LẬP đã gõ. Không gõ thì để trống và `post_entry` chặn
    — đúng vậy, vì lúc ấy tờ phiếu thật sự thiếu một thông tin bắt buộc.
    """
    ten, ma = (ten or "").strip(), (ma or "").strip()
    if not ten and not ma:
        return
    for l in lines:
        if not (l.get("partner_code") or l.get("partner")):
            l["partner_code"] = (ma or ten)[:60]
            l["partner"] = (ten or ma)[:160]


def lap(db: Session, u: User, chieu: str, ngay: date, so_tien: float, ly_do: str,
        noi_dung: str = "", ten_doi_tuong: str = "", ma_doi_tuong: str = "",
        booking_id: int | None = None, khoan_muc: str = "",
        so_goc: str = "") -> tuple[PhieuQuy, dict]:
    """Lập một phiếu quỹ và ghi sổ NGAY. Không khớp quy tắc nào thì ném lỗi, không lưu gì."""
    if chieu not in CHIEU:
        raise ValueError(f"Chiều phiếu quỹ phải là 'thu' hoặc 'chi', không phải {chieu!r}")
    so_tien = round(float(so_tien or 0), 0)
    if so_tien <= 0:
        raise ValueError("Số tiền phải lớn hơn 0")
    ly_do = (ly_do or "").strip()

    # LÝ DO LÀ MỘT TỪ VỰNG ĐÓNG, VÀ PHẢI CHẶN Ở ĐÂY CHỨ KHÔNG Ở BẢNG QUY ƯỚC.
    #
    # Đo được lúc chạy thật ngày 04/11/2026: với chiều THU, một lý do gõ sai KHÔNG rơi xuống
    # "không có quy tắc nào khớp" — nó rơi vào `THU_CHUA_RO_TM`, vì điều kiện của dòng ấy là
    # `{"khop_don": False}` và KHÔNG nhắc tới `muc_thu` chút nào. Hậu quả: một lỗi gõ của thủ quỹ
    # lặng lẽ thành 1111/3388 "tiền chưa rõ", và không gì kêu lên. Đó đúng là loại sai mà cả đợt
    # này sinh ra để chống.
    #
    # Nên chặn TRƯỚC khi hỏi bảng quy ước: lý do nào không có trong từ vựng thì từ chối ngay.
    #
    # ĐỂ TRỐNG THÌ ĐƯỢC, và đó không phải lối thoát: `THU_KHACH_TM` (có booking) và
    # `THU_CHUA_RO_TM` (không có booking) khớp bằng `khop_don`, không bằng lý do — chúng KHÔNG
    # khai một `muc_thu` nào nên không hiện ra trong từ vựng. Bắt buộc có lý do sẽ chặn mất hai
    # đường thu tiền mặt thật nhất của quầy.
    if ly_do:
        tu_vung = {g["gia_tri"] for g in ly_do_nhan_duoc(db, chieu)}
        if ly_do not in tu_vung:
            raise ValueError(
                f"Lý do `{ly_do}` không có trong bảng quy ước cho phiếu {chieu} quỹ tiền mặt. "
                f"Bảng quy ước đang nhận: {', '.join(sorted(tu_vung)) if tu_vung else '(chưa có lý do nào)'}. "
                "Để TRỐNG lý do nếu đây là thu/chi tiền mặt thẳng với khách; còn nếu cần một lý "
                "do mới thì Kế toán trình quy tắc hạch toán cho nó (cần hai chữ ký) rồi lập lại "
                "phiếu — máy KHÔNG đoán hộ cặp tài khoản.")

    nguon, tien_to, _ = CHIEU[chieu]
    nghiep_vu = NGHIEP_VU_THEO_CHIEU[chieu]
    code = MTS.tiep_theo(db, PhieuQuy, f"{tien_to}{ngay:%y%m}-", 4)
    bc = _boi_canh(code, ngay, chieu, ly_do, noi_dung, ten_doi_tuong, ma_doi_tuong,
                   booking_id, khoan_muc)

    bt = HT.xem_truoc(db, nguon, so_tien, bc, on=ngay)
    if not bt.get("khop"):
        # NÓI RA CHỌN GÌ ĐƯỢC. Người gặp lỗi này thường là thủ quỹ đang cầm tờ phiếu trên tay;
        # một câu "không khớp quy tắc nào" mà không kèm danh sách thì họ chỉ còn cách đoán tiếp.
        co = sorted({g["gia_tri"] for g in ly_do_nhan_duoc(db, chieu)})
        raise ValueError(
            f"Không có quy tắc hạch toán nào khớp phiếu {chieu} quỹ tiền mặt với lý do "
            f"`{ly_do or '(để trống)'}`. "
            f"Bảng quy ước đang nhận: {', '.join(co) if co else '(chưa có lý do nào)'}. "
            "Kế toán trình quy tắc cho lý do này qua màn hình Quy tắc hạch toán (cần hai chữ ký) "
            "rồi lập lại phiếu — máy KHÔNG đoán hộ cặp tài khoản.")

    _gan_doi_tuong(bt["lines"], ten_doi_tuong, ma_doi_tuong)

    e = ACC.post_entry(
        db, u.username, u.role, ngay, bt["dien_giai"], bt["lines"],
        source_type="phieu_quy", source_ref=code, nghiep_vu=nghiep_vu, ngay_chung_tu=ngay)

    p = PhieuQuy(
        code=code, chieu=chieu, ngay=ngay, so_tien=so_tien, ly_do=(ly_do or "").strip()[:40],
        noi_dung=(noi_dung or "")[:200], ten_doi_tuong=(ten_doi_tuong or "")[:160],
        ma_doi_tuong=(ma_doi_tuong or "")[:60], khoan_muc=(khoan_muc or "").strip().upper()[:40],
        booking_id=booking_id, quy_tac=bt["quy_tac"][:40], journal_entry_id=e.id,
        so_goc=(so_goc or "").strip()[:40], created_by=u.username)
    db.add(p)
    db.flush()
    db.commit()
    db.refresh(p)
    return p, bt


def danh_sach(db: Session, tu_ngay: date | None = None, den_ngay: date | None = None,
              chieu: str = "", gioi_han: int = 200) -> list[PhieuQuy]:
    q = select(PhieuQuy)
    if tu_ngay:
        q = q.where(PhieuQuy.ngay >= tu_ngay)
    if den_ngay:
        q = q.where(PhieuQuy.ngay <= den_ngay)
    if chieu:
        q = q.where(PhieuQuy.chieu == chieu)
    return list(db.execute(q.order_by(PhieuQuy.ngay.desc(), PhieuQuy.id.desc())
                           .limit(max(1, min(int(gioi_han or 200), 1000)))).scalars().all())


def ra(p: PhieuQuy) -> dict:
    return {"id": p.id, "code": p.code, "chieu": p.chieu, "ngay": str(p.ngay),
            "so_tien": p.so_tien, "ly_do": p.ly_do, "noi_dung": p.noi_dung,
            "ten_doi_tuong": p.ten_doi_tuong, "ma_doi_tuong": p.ma_doi_tuong,
            "khoan_muc": p.khoan_muc, "so_goc": p.so_goc,
            "booking_id": p.booking_id, "quy_tac": p.quy_tac,
            "journal_entry_id": p.journal_entry_id, "created_by": p.created_by,
            "created_at": p.created_at.isoformat() if p.created_at else ""}
