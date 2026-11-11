# -*- coding: utf-8 -*-
"""MKT-1 · HAI BÀN LÀM VIỆC CỦA PHÒNG MARKETING — Chủ tịch duyệt 09/11/2026.

    "ok duyệt phòng marketing có 2 bàn làm việc của P.TGĐ và nhân viên"

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO HAI BÀN, KHÔNG PHẢI MỘT
═══════════════════════════════════════════════════════════════════════════════════════════════
Phòng Marketing có hai vai và hai vai ấy làm hai việc ngược chiều nhau. Phó TGĐ Marketing DUYỆT
và PHÁT NGÔN — hai chữ ký Chủ tịch ký ngày 18/9/2026 đều rơi vào vai này. Nhân viên Marketing
CHẠY NỘI DUNG và GIỮ LEAD.

Gộp chín ô vào một bàn thì nhân viên phải lọc mắt qua các ô duyệt mà họ không bấm được, và Phó
TGĐ phải lọc mắt qua các ô tác nghiệp không phải việc của ông. Một bàn làm việc mà người ngồi
phải bỏ qua nửa số ô thì nó đã thôi là bàn làm việc.

═══════════════════════════════════════════════════════════════════════════════════════════════
RANH GIỚI 09/9/2026 — TỆP NÀY KHÔNG TÍNH MỘT CON SỐ NÀO CỦA RIÊNG NÓ
═══════════════════════════════════════════════════════════════════════════════════════════════
Mỗi ô gọi đúng phép đếm mà màn hình nguồn đang dùng:

  · PR quá hạn            → `pr_hoat_dong.dem_qua_han` (ngưỡng đọc tham số `pr_khung_hoang_gio`)
  · Lead quá hạn của tôi  → `leads.dem_qua_han` trên câu truy vấn đã lọc theo người giữ
  · Lead chưa gắn         → `marketing.lead_chua_gan`
  · Kỳ chưa chốt số       → `doi_soat_marketing.do_troi(...)["da_chot"]`

Hai ô còn lại đếm thẳng trạng thái trên bảng gốc (`campaigns.status`, `content_items.status`),
và trạng thái ấy là bảng khai trong `models/marketing`, không phải một danh sách chép tay ở đây.

VÌ SAO KHÔNG GỌI `chuyen_doi_lead.ton_dong()` CHO Ô LEAD. Hàm ấy trả về `nguoi_giu` là TÊN hiển
thị, không phải mã người. Lọc bàn của một người bằng tên là cái bẫy chờ ngày công ty có hai người
trùng tên — và hôm ấy một người sẽ thấy việc của người kia trên bàn mình. Nên ô này lọc bằng
`Lead.sales_id`, rồi gọi ĐÚNG `leads.dem_qua_han` để định nghĩa "quá hạn" vẫn chỉ có một chỗ.

═══════════════════════════════════════════════════════════════════════════════════════════════
BÀN KHÔNG CÓ NÚT DUYỆT — giữ nguyên luật của bộ máy bàn làm việc 12/10/2026
═══════════════════════════════════════════════════════════════════════════════════════════════
Mọi ô chỉ DẪN SANG đúng tab của màn `/marketing`, nơi quyền và quy trình đã có chủ. Duyệt một nội
dung hay phát một thông cáo là việc phải ĐỌC thứ mình đang duyệt; một nút duyệt cạnh một dòng tóm
tắt là lời mời duyệt mà chưa mở ra xem. Bảy tab của `/marketing` không bị đụng một dòng nào.

BA ĐIỀU ÉP, chép đúng từ `ban_lam_viec.py` vì chúng không phải thói quen mà là ba lần suýt nói dối:
(a) `so_luong = None` là CHƯA ĐỌC ĐƯỢC, không phải bằng 0. Một ô hỏng mà hiện "0 việc" là nói với
    người ngồi bàn rằng hôm nay không có gì phải làm.
(b) Một ô hỏng không kéo sập cả bàn — mỗi ô bọc `try` riêng.
(c) Thiếu một ô thì KHÔNG có tổng (`tong_dang_cho = None`), chứ không cộng các ô còn lại rồi gọi
    đó là "tổng việc đang chờ".

CHƯA LÀM, ghi ra chứ không giấu — bốn ô đã dò ra dữ liệu nhưng CHƯA có phép đếm sẵn, nên chưa hứa:
ngân sách kỳ chờ duyệt, nội dung bị trả về nháp, bình luận Fanpage chưa xử lý, dấu quảng cáo chưa
ghép được lead. Chủ tịch chốt 09/11/2026: ship năm ô đã soát trước, bốn ô kia vào phần còn nợ.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.crm import Lead
from app.models.marketing import Campaign, ContentItem, MarketingBudget
from app.services import doi_soat_marketing as DSM
from app.services import leads as LD
from app.services import marketing as MKT
from app.services import pr_hoat_dong as PR

SAN_SANG = "san_sang"
LOI = "loi"
# MKT-11 · 12/11/2026 — TRẠNG THÁI THỨ BA. Tài liệu bàn giao đòi phân biệt rõ sáu cảnh:
# có số bằng 0 · chưa xác định · chưa lập · đang tải · lỗi tải · không có quyền. Bàn cũ chỉ
# có hai: đọc được và đọc hỏng. "Tỷ lệ chốt chưa xác định" mà vẽ số 0 là nói dối — chính
# `leads.py` đã viết "CHƯA ĐỐI CHIẾU THÌ KHÔNG XÁC ĐỊNH, KHÔNG PHẢI 0%". Ô mang trạng thái
# này đem theo trường `chu`: CHỮ để vẽ thay cho số, chứ không phải một con số mặc định.
CHUA_CO = "chua_co"

# Lead CHƯA XONG VIỆC. Hai trạng thái này là đúng bộ mà `chuyen_doi_lead.ton_dong` dùng — chép
# danh sách thì ngày thêm một trạng thái thứ ba, một trong hai chỗ sẽ quên.
LEAD_DANG_MO = ("moi", "dang_cham_soc")

# Nội dung CHỜ MỘT CHỮ KÝ. `cho_ky_2` là bản đã qua chữ ký thứ nhất và đang chờ Ban TGĐ hoặc Pháp
# chế ký tiếp — vẫn là việc đang nằm trên bàn người duyệt, nên nó đếm cùng `cho_duyet`.
ND_CHO_DUYET = ("cho_duyet", "cho_ky_2")


def _o(khoa: str, ten: str, so_luong, don_vi: str, den: str, nguon: str,
       muc: str = "", ghi_chu: str = "", trang_thai: str = SAN_SANG, ly_do: str = "",
       chu: str = "") -> dict:
    """Một ô hàng đợi. `so_luong = None` nghĩa là CHƯA ĐỌC ĐƯỢC, không phải bằng 0.

    `chu` (MKT-11): chữ vẽ THAY cho số khi ô mang trạng thái `CHUA_CO` — "chưa xác định",
    "chưa lập". Để trống ở mọi ô đếm được, nên nó không đổi một ô cũ nào.
    """
    return {"khoa": khoa, "ten": ten, "so_luong": so_luong, "don_vi": don_vi,
            "muc": muc, "ghi_chu": ghi_chu, "den": den, "nguon": nguon,
            "trang_thai": trang_thai, "ly_do": ly_do, "chu": chu}


def _chay(khoa: str, ten: str, ham) -> dict:
    """Điều (b): một ô hỏng hiện ra thành một ô màu riêng kèm lý do, không thành số 0."""
    try:
        return ham()
    except Exception as ex:                                   # noqa: BLE001 — xem điều (b)
        return _o(khoa, ten, None, "", "", "", trang_thai=LOI, ly_do=str(ex)[:200])


def ky_truoc(hom_nay: date | None = None) -> str:
    """Kỳ YYYY-MM liền trước tháng đang chạy.

    Ô "kỳ chưa chốt số" hỏi về tháng ĐÃ ĐÓNG, không hỏi tháng đang chạy: chốt số một tháng còn
    đang chạy là đóng một mốc chuẩn cho những ngày chưa xảy ra.
    """
    n = hom_nay or date.today()
    return f"{n.year - 1:04d}-12" if n.month == 1 else f"{n.year:04d}-{n.month - 1:02d}"


def ky_nay(hom_nay: date | None = None) -> str:
    """Kỳ YYYY-MM của tháng ĐANG chạy — khác `ky_truoc` ở ngay trên.

    Ba ô theo dõi của MKT-11 hỏi về tháng đang chạy: số điện thoại phát sinh trong kỳ, tỷ lệ
    chốt của kỳ, ngân sách của kỳ. Ô "kỳ chưa chốt số" thì vẫn hỏi tháng đã đóng — hai câu
    hỏi khác nhau nên hai hàm khác nhau, không dùng chung một tham số cho cả hai.
    """
    n = hom_nay or date.today()
    return "%04d-%02d" % (n.year, n.month)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BÀN PHÓ TGĐ MARKETING — người duyệt và người phát ngôn
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _pr_qua_han(db: Session) -> dict:
    n = PR.dem_qua_han(db)
    return _o("pr_qua_han", "PR quá hạn phản hồi", n, "việc",
              "/marketing?tab=thuonghieu",
              "pr_hoat_dong.dem_qua_han — ngưỡng đọc tham số pr_khung_hoang_gio",
              muc="do" if n else "",
              ghi_chu="Đồng hồ chạy theo giờ thật, không trừ ngày nghỉ: việc ghi lúc 22h thứ Bảy "
                      "thì 0h là quá hạn. Người phát ngôn là Phó TGĐ Marketing.")


def _noi_dung_cho_duyet(db: Session) -> dict:
    n = int(db.execute(select(func.count()).select_from(ContentItem)
                       .where(ContentItem.status.in_(ND_CHO_DUYET))).scalar() or 0)
    return _o("noi_dung_cho_duyet", "Nội dung chờ duyệt", n, "bản thảo",
              "/marketing?tab=noidung",
              "content_items.status ∈ (cho_duyet, cho_ky_2)",
              ghi_chu="Gồm cả bản đang chờ CHỮ KÝ THỨ HAI — bản có cam kết hoặc có số liệu tài "
                      "chính phải qua Ban TGĐ hoặc Pháp chế trước khi được duyệt.")


def _chien_dich_cho_duyet(db: Session) -> dict:
    n = int(db.execute(select(func.count()).select_from(Campaign)
                       .where(Campaign.status == "cho_duyet")).scalar() or 0)
    return _o("chien_dich_cho_duyet", "Chiến dịch chờ đưa vào chạy", n, "chiến dịch",
              "/marketing?tab=chiendich",
              "campaigns.status = cho_duyet",
              ghi_chu="Bản do AI đề xuất cũng dừng ở đây như mọi bản khác — AI được đề xuất, "
                      "người có thẩm quyền mới được cho chạy.")


def _ky_chua_chot(db: Session) -> dict:
    ky = ky_truoc()
    da_chot = bool(DSM.do_troi(db, ky).get("da_chot"))
    return _o("ky_chua_chot", f"Kỳ {ky} chưa chốt số", 0 if da_chot else 1, "kỳ",
              "/marketing?tab=doisoat",
              "doi_soat_marketing.do_troi(kỳ trước)['da_chot']",
              muc="" if da_chot else "vang",
              ghi_chu="Chưa chốt thì chưa có mốc để biết số của kỳ ấy đã trôi bao nhiêu. Trôi "
                      "KHÔNG phải lỗi — lead tháng trước chốt tháng này vẫn làm số tháng trước "
                      "tăng, đúng quy tắc Chủ tịch ký 14/9/2026.")


def _chien_dich_dang_chay(db: Session) -> dict:
    """MẪU SỐ, không phải việc phải làm — xem `MAU_SO` ở dưới."""
    n = int(db.execute(select(func.count()).select_from(Campaign)
                       .where(Campaign.status == "dang_chay")).scalar() or 0)
    return _o("chien_dich_dang_chay", "Chiến dịch đang chạy", n, "chiến dịch",
              "/marketing?tab=chiendich",
              "campaigns.status = dang_chay",
              ghi_chu="Mẫu số để đọc bốn ô trên, không phải việc phải làm — không cộng vào tổng.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BÀN NHÂN VIÊN MARKETING — người chạy nội dung và giữ lead
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _lead_qua_han_cua_toi(db: Session, u: User) -> dict:
    """Chủ tịch chốt 09/11/2026: ô này đếm ĐÚNG lead người đang xem giữ, không đếm cả phòng.

    Bàn trả lời câu "sáng nay TÔI phải làm gì". Một con số gồm cả lead người khác giữ là một con
    số người ngồi bàn không làm gì được với nó — và họ sẽ thôi đọc nó sau vài ngày.
    """
    qs = select(Lead).where(Lead.status.in_(LEAD_DANG_MO), Lead.sales_id == u.id)
    n = LD.dem_qua_han(db, qs)
    return _o("lead_qua_han_cua_toi", "Lead nằm im quá hạn tôi giữ", n, "lead",
              "/marketing?tab=khach",
              "leads.dem_qua_han trên Lead.sales_id = người đang xem",
              muc="do" if n else "",
              ghi_chu="Hạn lấy theo leads.han_hieu_luc: LỜI HẸN với khách thắng luật 24 giờ. "
                      "Chấm người ta theo luật chung trong khi họ đã hẹn khác là chấm sai.")


def _lead_chua_gan(db: Session) -> dict:
    n = int(MKT.lead_chua_gan(db).get("tong") or 0)
    return _o("lead_chua_gan", "Lead chưa gắn chiến dịch", n, "lead",
              "/marketing?tab=doisoat",
              "marketing.lead_chua_gan()['tong']",
              ghi_chu="Ô này là của CẢ PHÒNG, không cắt theo người: lead chưa gắn chiến dịch thì "
                      "cũng thường chưa giao ai, nên cắt theo người giữ là cách chắc chắn để "
                      "chúng không nằm trên bàn của ai.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# MKT-11 · BA Ô THEO DÕI VÀ HAI Ô VIỆC, đưa lên bàn Phó TGĐ ngày 12/11/2026
#
# GỌI ĐÚNG HÀM MÀN `/marketing` ĐANG GỌI, KHÔNG TỰ ĐẾM LẠI. Màn ấy đọc số điện thoại và tỷ
# lệ chốt từ `conversion_report`; hàm đếm theo kênh thì trả về số điện thoại của TỪNG kênh,
# cộng lại là đếm hai lần một số nằm ở hai kênh. Tự đếm lại là cách chắc chắn để hai màn
# hiện hai con số khác nhau cho cùng một thứ, rồi không ai biết tin cái nào.
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _bao_cao_ky(db: Session) -> dict:
    """Một lần đọc cho CẢ HAI ô số điện thoại và tỷ lệ chốt — chúng cùng một báo cáo."""
    return LD.conversion_report(db, ky_nay())


def _sdt_phat_sinh(db: Session) -> dict:
    """MẪU SỐ, không phải việc phải làm."""
    ky = ky_nay()
    n = int((_bao_cao_ky(db).get("total_current") or {}).get("so_sdt") or 0)
    return _o("sdt_phat_sinh", "Số điện thoại phát sinh", n, "số",
              "/marketing?tab=khach",
              "leads.conversion_report(kỳ này)['total_current']['so_sdt']",
              ghi_chu="Đếm trên tập số điện thoại ĐÃ CHUẨN HOÁ khác nhau của kỳ " + ky +
                      ". Hai người chung một số đếm thành một, một người đổi số đếm thành "
                      "hai — nên không cộng dồn số của từng kênh.")


def _ty_le_chot(db: Session) -> dict:
    """CHƯA ĐỐI CHIẾU THÌ CHƯA XÁC ĐỊNH, KHÔNG PHẢI 0% — luật của chính `leads.py`."""
    rep = _bao_cao_ky(db)
    if not rep.get("da_doi_chieu"):
        return _o("ty_le_chot", "Tỷ lệ chốt", None, "",
                  "/marketing?tab=doisoat",
                  "leads.conversion_report(kỳ này)['da_doi_chieu'] = sai",
                  trang_thai=CHUA_CO, chu="Chưa xác định", muc="vang",
                  ghi_chu="Chưa chạy đối chiếu lead ↔ booking. Đây là CHƯA XÁC ĐỊNH, không "
                          "phải 0% — hai thứ khác nhau và màn hình phải nói ra điều đó.")
    ty = (rep.get("total_current") or {}).get("ty_le_chot_overview")
    return _o("ty_le_chot", "Tỷ lệ chốt", round(float(ty or 0) * 100, 1), "%",
              "/marketing?tab=chuyendoi",
              "leads.conversion_report(kỳ này)['total_current']['ty_le_chot_overview']",
              ghi_chu="Quy tắc overview-v1 Chủ tịch ký 14/9/2026: tính cả phần chốt ở các "
                      "kỳ SAU, nên con số này còn tăng khi kỳ trước chốt muộn. Tăng KHÔNG "
                      "phải lỗi.")


def _ngan_sach_ky(db: Session) -> dict:
    """CHƯA LẬP là một trạng thái, không phải số 0 — không có dự toán thì không có chỗ để so."""
    ky = ky_nay()
    n = int(db.execute(select(func.count()).select_from(MarketingBudget)
                       .where(MarketingBudget.period == ky,
                              MarketingBudget.status.in_(("cho_duyet", "hieu_luc")))).scalar() or 0)
    if not n:
        return _o("ngan_sach_ky", "Ngân sách kỳ", None, "",
                  "/marketing?tab=ngansach",
                  "marketing_budgets kỳ " + ky + " ∈ (cho_duyet, hieu_luc) = 0 bản",
                  trang_thai=CHUA_CO, chu="Chưa lập", muc="vang",
                  ghi_chu="Chưa có dự toán thì không có chỗ để so phần đã chi. Đây là việc "
                          "còn thiếu, không phải ngân sách bằng 0.")
    return _o("ngan_sach_ky", "Ngân sách kỳ", n, "bản",
              "/marketing?tab=ngansach",
              "marketing_budgets kỳ " + ky + " ∈ (cho_duyet, hieu_luc)",
              ghi_chu="Thực chi đọc từ đề nghị chi ĐÃ DUYỆT, không nhập tay.")


def _lead_qua_han_phong(db: Session) -> dict:
    """CẢ PHÒNG, không cắt theo người — khác `_lead_qua_han_cua_toi` đúng một dòng lọc.

    Và đó là khác biệt có lý do: bàn nhân viên trả lời "sáng nay TÔI phải làm gì", bàn Phó
    TGĐ trả lời "phòng tôi đang nợ khách bao nhiêu lời hồi đáp". Một con số gồm cả lead
    người khác giữ là vô dụng với người ngồi bàn nhân viên, và là con số DUY NHẤT đúng với
    người quản. Chủ tịch duyệt 12/11/2026.
    """
    n = LD.dem_qua_han(db, select(Lead).where(Lead.status.in_(LEAD_DANG_MO)))
    return _o("lead_qua_han_phong", "Lead quá hạn liên hệ", n, "lead",
              "/marketing?tab=khach",
              "leads.dem_qua_han trên CẢ sổ lead đang mở, không lọc theo người giữ",
              muc="do" if n else "",
              ghi_chu="Hạn lấy theo leads.han_hieu_luc: LỜI HẸN với khách thắng luật 24 giờ. "
                      "Trạng thái vẫn là Mới và chưa ai liên hệ.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HAI BÀN
# ══════════════════════════════════════════════════════════════════════════════════════════════

# Ô là MẪU SỐ để đọc ô khác, không phải việc phải làm. Không cộng vào tổng đang chờ.
#
# MKT-11 · 12/11/2026 — NĂM Ô MỚI ĐỀU VÀO ĐÂY, và đây là một quyết định chứ không phải một
# dòng cho đủ. `tong_dang_cho` đang cộng bốn ô: 0+0+0+1 = 1 việc đang chờ. Cộng thêm 25 lead
# quá hạn và 7.355 lead chưa gắn thì tổng thành 7.381 "việc đang chờ" — một con số vô nghĩa,
# cộng kỳ với lead với bản thảo. Chính tài liệu bàn giao dặn: "một lead có thể thuộc nhiều
# nhóm nên không cộng các nhóm thành tổng người", và bản v32 cũng KHÔNG có ô tổng nào.
#
# Nên: năm ô mới không cộng vào tổng, màn hình mới không vẽ ô tổng, và `tong_dang_cho` giữ
# nguyên ý nghĩa cũ cho bàn nhân viên và cho bất kỳ nơi nào còn đọc nó.
MAU_SO = ("chien_dich_dang_chay", "sdt_phat_sinh", "ty_le_chot", "ngan_sach_ky",
          "lead_qua_han_phong", "lead_chua_gan")


def _dong_goi(ten: str, vai: str, o: list[dict]) -> dict:
    dem = [x for x in o if x["khoa"] not in MAU_SO]
    du = all(x["trang_thai"] == SAN_SANG for x in dem)
    return {
        "ten": ten, "vai": vai, "o": o,
        # Điều (c): thiếu một ô thì KHÔNG có tổng.
        "tong_dang_cho": sum(x["so_luong"] for x in dem) if du else None,
        "doc_luc": datetime.now(),
        # Lời cảnh báo đi CÙNG dữ liệu chứ không nằm trong mã màn hình: màn hình có thể được viết
        # lại, còn câu này là một phần của con số.
        "luu_y": "Bàn này CHỈ ĐỌC. Mọi ô dẫn sang đúng tab của màn Marketing, nơi quyền và quy "
                 "trình đã có chủ — không có nút duyệt nào trên bàn.",
    }


def ban_ptgd(db: Session) -> dict:
    """Bàn làm việc Phó TGĐ Marketing. Không nhận tham số kỳ: bốn ô đều là việc ĐANG treo hôm nay."""
    o = [
        _chay("pr_qua_han", "PR quá hạn phản hồi", lambda: _pr_qua_han(db)),
        _chay("noi_dung_cho_duyet", "Nội dung chờ duyệt", lambda: _noi_dung_cho_duyet(db)),
        _chay("chien_dich_cho_duyet", "Chiến dịch chờ đưa vào chạy", lambda: _chien_dich_cho_duyet(db)),
        _chay("ky_chua_chot", "Kỳ chưa chốt số", lambda: _ky_chua_chot(db)),
        _chay("chien_dich_dang_chay", "Chiến dịch đang chạy", lambda: _chien_dich_dang_chay(db)),
        # MKT-11 — ba ô theo dõi và hai ô việc. Đều là MẪU SỐ, xem chú thích ở `MAU_SO`.
        _chay("sdt_phat_sinh", "Số điện thoại phát sinh", lambda: _sdt_phat_sinh(db)),
        _chay("ty_le_chot", "Tỷ lệ chốt", lambda: _ty_le_chot(db)),
        _chay("ngan_sach_ky", "Ngân sách kỳ", lambda: _ngan_sach_ky(db)),
        _chay("lead_qua_han_phong", "Lead quá hạn liên hệ", lambda: _lead_qua_han_phong(db)),
        _chay("lead_chua_gan", "Lead chưa gắn chiến dịch", lambda: _lead_chua_gan(db)),
    ]
    return _dong_goi("Bàn làm việc Phó TGĐ Marketing", "ptgd_mkt", o)


def ban_nhan_vien(db: Session, u: User) -> dict:
    """Bàn làm việc nhân viên Marketing. Cần NGƯỜI đang xem: ô lead cắt theo người giữ."""
    o = [
        _chay("lead_qua_han_cua_toi", "Lead nằm im quá hạn tôi giữ",
              lambda: _lead_qua_han_cua_toi(db, u)),
        _chay("lead_chua_gan", "Lead chưa gắn chiến dịch", lambda: _lead_chua_gan(db)),
    ]
    b = _dong_goi("Bàn làm việc nhân viên Marketing", "nv_mkt", o)
    b["nguoi"] = u.full_name or u.username
    return b
