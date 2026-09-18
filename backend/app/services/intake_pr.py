# -*- coding: utf-8 -*-
"""CỬA NHẬP SỔ HOẠT ĐỘNG PR — bài báo, thông cáo, sự kiện, phát ngôn, và vụ khủng hoảng.

Ranh giới 09/9/2026: mỗi con số phải có một cửa cho người nhập. Sổ PR không có cửa thì con số
"bao nhiêu vụ quá hạn" không thể có, kể cả ước lượng.

──────────────────────────────────────────────────────────────────────────────────────────────
BA Ô CỬA NÀY CỐ Ý KHÔNG MỞ
──────────────────────────────────────────────────────────────────────────────────────────────

  · `ghi_nhan_luc`   – MỐC BẮT ĐẦU ĐẾM hai giờ. Do cơ sở dữ liệu đặt. Cho người nhập gõ thì ai
                       sắp quá hạn chỉ cần lùi mốc lại, và con số "quá hạn" không còn nghĩa gì.
  · `nguoi_phat_ngon`– do hệ thống ghi lúc người có vai phát ngôn bấm nút. Ô gõ tên tự do thì
                       ba tháng sau cái tên ấy không nối được với tài khoản nào.
  · `trang_thai`     – "Đã phát" là KẾT QUẢ của một lần bấm nút, không phải một ô để gõ.

Cùng một hình với cửa tài sản thương hiệu cùng ngày: cửa nhập tự chặn mình ở đúng những ô mà nếu
mở ra thì một con số có hai nguồn.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.marketing import PR_LOAI
from app.services import pr_hoat_dong as PR

MUC_DO = {"nhe": "Nhẹ", "vua": "Vừa", "nghiem_trong": "Nghiêm trọng"}


def kiem(db: Session, r: dict) -> tuple[list, list, str | None]:
    loi, cb = [], []

    loai = str(r.get("loai") or "").strip()
    if not loai:
        loi.append("Thiếu loại hoạt động")
    elif loai not in PR_LOAI:
        loi.append(f"Loại '{loai}' không có trong danh mục ({', '.join(list(PR_LOAI)[:5])}…)")

    if not str(r.get("tieu_de") or "").strip():
        loi.append("Thiếu tiêu đề – một dòng không có tiêu đề thì không ai tra lại được")

    kh = bool(r.get("la_khung_hoang"))
    md = str(r.get("muc_do") or "").strip()
    if md and md not in MUC_DO:
        loi.append(f"Mức độ '{md}' không hợp lệ ({', '.join(MUC_DO)})")
    if kh and not md:
        # Cảnh báo chứ không chặn: lúc một vụ vừa nổ ra, người ghi chưa chắc đã biết nó to đến
        # đâu. Chặn ở đây là buộc người ta đoán một mức độ, hoặc không ghi gì cả — mà không ghi
        # thì đồng hồ hai giờ không bao giờ bắt đầu chạy.
        cb.append("Chưa ghi mức độ cho vụ khủng hoảng này. Dòng vẫn được nhận và đồng hồ hai giờ "
                  "bắt đầu chạy ngay – điền mức độ khi biết rõ hơn")
    if md and not kh:
        cb.append("Có mức độ nhưng không đánh dấu là khủng hoảng – dòng này sẽ KHÔNG có hạn hai giờ")

    for o, ten in (("ghi_nhan_luc", "Thời điểm ghi nhận"), ("nguoi_phat_ngon", "Người phát ngôn"),
                   ("phan_hoi_luc", "Thời điểm phản hồi")):
        if str(r.get(o) or "").strip():
            loi.append(f"{ten}: ô này do hệ thống ghi, cửa nhập không khai – xem mô tả của cửa")
    tt = str(r.get("trang_thai") or "").strip()
    if tt and tt != "nhap":
        loi.append("Trạng thái 'Đã phát' là KẾT QUẢ của một lần bấm nút phát, không phải ô để gõ")

    return loi, cb, None


def nap(db: Session, r: dict, boi: str):
    """Mỗi dòng là MỘT VIỆC, không có khoá chống trùng – và đó là chủ ý.

    Hai bài báo cùng tiêu đề trên hai tờ báo là hai việc thật. Gộp chúng lại là xoá mất một việc
    đã xảy ra. Nạp lại cùng một tệp thì đúng là sinh ra bản ghi thứ hai, nhưng cái giá của việc
    ấy (một dòng thừa, người ta xoá) rẻ hơn nhiều so với việc mất một dòng có thật.
    """
    return PR.tao(db, r, boi), "moi"


def bo_nap(_c) -> dict:
    return {
        "hoat_dong_pr": {
            "bang_dich": "mkt_pr_hoat_dong",
            "phong_ban": "marketing",
            "ten": "Hoạt động PR & truyền thông",
            "mo_ta":
                "Sổ ghi việc truyền thông ĐÃ XẢY RA và ai chịu trách nhiệm cho nó — khác với màn "
                "hình Nội dung, chỗ giữ BẢN THẢO trước khi đăng.\n\n"
                "BA Ô CỬA NÀY KHÔNG MỞ, và mỗi ô có một lý do:\n"
                "· Thời điểm ghi nhận — là mốc bắt đầu đếm hạn hai giờ, do hệ thống đặt. Cho gõ "
                "thì ai sắp quá hạn chỉ cần lùi mốc lại.\n"
                "· Người phát ngôn — hệ thống ghi tên người bấm nút phát, và chỉ P.TGĐ Marketing "
                "bấm được (Chủ tịch chốt 18/9/2026).\n"
                "· Trạng thái 'Đã phát' — là kết quả của một lần bấm nút, không phải một ô để gõ.\n\n"
                "ĐÁNH DẤU KHỦNG HOẢNG LÀ BẤM ĐỒNG HỒ. Dòng có đánh dấu thì hạn phản hồi là 2 GIỜ "
                "kể từ lúc vào sổ, chạy theo đồng hồ thật — không trừ ngày nghỉ, không quy ra giờ "
                "hành chính. Dòng không đánh dấu thì KHÔNG có hạn, và cũng không nằm trong con số "
                "quá hạn — để bảng quá hạn chỉ chứa thứ thật sự gấp.\n\n"
                "Mỗi dòng là MỘT VIỆC và KHÔNG có khoá chống trùng: hai bài báo cùng tiêu đề trên "
                "hai tờ báo là hai việc thật.",
            "khoa_chong_trung": "Không có – mỗi dòng là một việc đã xảy ra",
            "cot": [
                _c("loai", "Loại hoạt động", True, kieu="chon", vi_du="bai_bao", chon=PR_LOAI),
                _c("tieu_de", "Tiêu đề", True, vi_du="Vietourist mở tuyến charter Phú Quốc"),
                _c("tom_tat", "Tóm tắt nội dung",
                   ghi_chu="đủ để người đọc sáu tháng sau hiểu việc gì đã xảy ra"),
                _c("noi_dang", "Đăng ở đâu / diễn ra ở đâu", vi_du="Báo Thanh Niên"),
                _c("link", "Đường dẫn", vi_du="https://…"),
                _c("la_khung_hoang", "Là vụ khủng hoảng", kieu="co_khong",
                   ghi_chu="ĐÁNH DẤU LÀ BẤM ĐỒNG HỒ: hạn phản hồi 2 giờ kể từ lúc vào sổ"),
                _c("muc_do", "Mức độ", kieu="chon", chon=MUC_DO,
                   ghi_chu="chỉ dùng cho vụ khủng hoảng; chưa biết thì để trống, đồng hồ vẫn chạy"),
                _c("ghi_chu", "Ghi chú"),
            ],
            "kiem": kiem, "nap": nap,
        },
    }


def vai_tro(quan_tri: tuple) -> dict:
    """Marketing ghi sổ của Marketing. Mở thêm cho Ban TGĐ vì một vụ khủng hoảng thường được người
    ở trên biết trước người trong phòng, và phút đầu tiên của hai giờ là phút đắt nhất."""
    return {"hoat_dong_pr": quan_tri + ("nv_mkt", "ptgd_mkt", "ptgd_doan")}
