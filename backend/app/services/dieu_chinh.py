# -*- coding: utf-8 -*-
"""HAI MỐC THỜI GIAN CỦA BÚT TOÁN ĐIỀU CHỈNH — Đợt E14, 13/10/2026.

VÌ SAO CÓ TỆP NÀY

Đợt E3 (12/10/2026) đã tách NGÀY CHỨNG TỪ khỏi NGÀY GHI SỔ, vì trước đó một ngày gánh hai việc:
ngày trên tờ chứng từ và ngày vào sổ cái. Hai mốc ấy đủ cho nghiệp vụ bình thường.

Bút toán ĐIỀU CHỈNH thì không. Nó cần hai mốc nữa, và thiếu chúng thì hai câu hỏi không trả lời
được — mà cả hai câu đều có người hỏi thật:

  1. "SỬA CHO KỲ NÀO?" — thuyết minh BCTC phải nói *điều chỉnh của kỳ 09*. Không có ô này thì một
     bút toán ghi tháng 10 sửa số tháng 9 trông Y HỆT một nghiệp vụ phát sinh tháng 10, và người
     lập thuyết minh phải đi đọc từng diễn giải để đoán.
  2. "BIẾT TỪ BAO GIỜ, SỬA SAU BAO LÂU?" — kiểm toán hỏi đúng câu này. Khoảng cách giữa ngày phát
     hiện và ngày ghi sổ là thứ DUY NHẤT trả lời được nó. Một sai sót phát hiện hôm nay sửa ngày
     mai là chuyện bình thường; phát hiện tháng 7 mà sửa tháng 10 là một câu chuyện khác hẳn, và
     hệ thống hôm nay không phân biệt nổi hai thứ đó.

ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM

`ky_goc` KHÔNG MỞ ĐƯỢC KỲ ĐÃ KHÓA. Nó là một NHÃN nói bút toán này thuộc về câu chuyện của kỳ nào;
bút toán vẫn ghi vào kỳ đang mở theo `entry_date`. Muốn ghi THẲNG vào kỳ cũ thì đi cửa MỞ LẠI KỲ
của Đợt E6 — hai người ký. Nếu `ky_goc` tự ghi vào kỳ cũ thì nó là một đường vòng qua chính cửa
ấy, và cửa ấy mất nghĩa ngay ngày có đường vòng.
"""
from datetime import date

from app.services import chung_tu_loai as CTL

# ══════════════════════════════════════════════════════════════════════════════════════════════
# NGHIỆP VỤ NÀO LÀ ĐIỀU CHỈNH — khai ra, không suy theo tên
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Suy theo tên ("mã nào có chữ dieu_chinh") thì một nghiệp vụ mới tên `dieu_chinh_ty_gia` sẽ tự
# nhiên rơi vào đây mà không ai quyết — và đánh giá lại tỷ giá cuối kỳ KHÔNG phải sửa sai sót kỳ
# trước. Khai danh sách thì thêm một loại là một lần có người nghĩ.
#
# VÌ SAO `dieu_chinh_kiem_toan` KHÔNG NẰM Ở ĐÂY
#
# Nó có chữ "điều chỉnh" trong tên, nhưng nó không sửa sai sót của một kỳ TRƯỚC: cửa chốt sổ theo
# BCTC kiểm toán (`misa.import_audited_checkpoint`) ghi bút toán vào ĐÚNG ngày `as_of` của bộ số
# kiểm toán, nên "sửa cho kỳ nào" luôn trùng kỳ ghi sổ và "ngày phát hiện" luôn trùng ngày ghi sổ.
# Hai mốc ấy ở đấy không trả lời câu gì — chúng chỉ chép lại một con số đã có. Bắt khai chúng là
# bắt người dùng điền một ô vô nghĩa, và tệ hơn: nó làm ĐỎ một cửa đang chạy đúng. Nếu sau này có
# cửa nhận bộ số kiểm toán của một kỳ ĐÃ ĐÓNG, thì đó là một nghiệp vụ mới, khai thêm một dòng ở
# đây, chứ không phải nới nghĩa dòng cũ.
NGHIEP_VU_DIEU_CHINH = ("dieu_chinh_ky_truoc",)

TOI_THIEU_LY_DO = 0   # lý do đi ở `description`, đã bắt buộc sẵn ở `post_entry`


class SaiDieuChinh(ValueError):
    """Hai mốc của bút toán điều chỉnh khai sai, kèm câu nói ra vì sao."""


def la_dieu_chinh(nghiep_vu: str) -> bool:
    return (nghiep_vu or "") in NGHIEP_VU_DIEU_CHINH


def kiem(nghiep_vu: str, ky_goc: str | None, ngay_phat_hien: date | None,
         entry_date: date, period: str) -> None:
    """Kiểm hai mốc TRƯỚC khi ghi sổ. Ném `SaiDieuChinh` kèm câu người đọc hiểu được.

    BỐN PHÉP KIỂM, và phép thứ nhất đi CẢ HAI CHIỀU — đó là chỗ dễ bỏ sót nhất: điều chỉnh mà
    thiếu hai mốc là mất câu trả lời, còn nghiệp vụ thường mà ĐIỀN hai mốc là một lời nói dối nhỏ
    nằm trong sổ, vì nó khai một bút toán bình thường là bút toán sửa sai.
    """
    co = la_dieu_chinh(nghiep_vu)

    if not co:
        if ky_goc or ngay_phat_hien:
            raise SaiDieuChinh(
                f"Hai mốc 'sửa cho kỳ' và 'ngày phát hiện' chỉ dành cho bút toán ĐIỀU CHỈNH "
                f"({', '.join(CTL.NGHIEP_VU[x][0] for x in NGHIEP_VU_DIEU_CHINH if x in CTL.NGHIEP_VU)}). "
                f"Nghiệp vụ này là '{CTL.NGHIEP_VU.get(nghiep_vu, (nghiep_vu,))[0]}' — điền hai mốc "
                f"vào đây là khai một bút toán bình thường thành bút toán sửa sai.")
        return

    if not ky_goc:
        raise SaiDieuChinh(
            "Bút toán điều chỉnh phải khai SỬA CHO KỲ NÀO. Thiếu ô này thì một bút toán ghi tháng "
            "này sửa số tháng trước trông y hệt một nghiệp vụ phát sinh tháng này, và người lập "
            "thuyết minh BCTC phải đọc từng diễn giải để đoán.")
    if not ngay_phat_hien:
        raise SaiDieuChinh(
            "Bút toán điều chỉnh phải khai NGÀY PHÁT HIỆN sai sót. Kiểm toán hỏi 'biết từ bao giờ, "
            "sửa sau bao lâu', và khoảng cách giữa ngày phát hiện với ngày ghi sổ là thứ duy nhất "
            "trả lời được câu ấy.")

    # KỲ GỐC KHÔNG ĐƯỢC SAU KỲ GHI SỔ. Sửa cho một kỳ chưa tới là một câu không có nghĩa.
    if ky_goc > period:
        raise SaiDieuChinh(
            f"Kỳ gốc {ky_goc} nằm SAU kỳ ghi sổ {period}. Một bút toán không sửa được cho một kỳ "
            f"chưa tới.")

    # NGÀY PHÁT HIỆN KHÔNG ĐƯỢC SAU NGÀY GHI SỔ. Biết sau khi đã sửa là chuyện không xảy ra được.
    if ngay_phat_hien > entry_date:
        raise SaiDieuChinh(
            f"Ngày phát hiện {ngay_phat_hien:%d/%m/%Y} nằm SAU ngày ghi sổ {entry_date:%d/%m/%Y}. "
            f"Không ai sửa một sai sót trước khi phát hiện ra nó — xem lại một trong hai ngày.")


def so_ngay_de_sua(e) -> int | None:
    """Phát hiện rồi bao lâu mới sửa. `None` khi không phải bút toán điều chỉnh.

    Đây là con số kiểm toán hỏi, và nó KHÔNG lưu trong bảng: lưu thì nó đóng băng, mà hai ngày
    kia có thể được sửa lại (bút toán nháp chưa ghi sổ). Tính lại lúc đọc thì nó luôn đúng.
    """
    if not getattr(e, "ngay_phat_hien", None) or not getattr(e, "entry_date", None):
        return None
    return (e.entry_date - e.ngay_phat_hien).days
