# -*- coding: utf-8 -*-
"""CỬA LỌC TIN KHỦNG HOẢNG — xếp hàng những tin đáng đọc trước, cho Marketing.

──────────────────────────────────────────────────────────────────────────────────────────────
MỘT RANH GIỚI, VÀ CẢ TỆP NÀY NẰM SAU NÓ
──────────────────────────────────────────────────────────────────────────────────────────────

Bộ lọc chỉ được XẾP HÀNG. Nó không được QUYẾT ĐỊNH.

  · Nó KHÔNG tự đặt `la_khung_hoang`.
  · Nó KHÔNG tự bấm đồng hồ hai giờ.
  · Nó KHÔNG vứt tin nào đi — điểm dưới ngưỡng chỉ là xếp sau, không phải bị xoá; hạ ngưỡng trên
    màn hình là thấy lại ngay.

Lý do không nằm ở chỗ máy chấm kém. Nó nằm ở chỗ: một tin bị máy bỏ sót là một tin KHÔNG CÒN AI
NHÌN NỮA. Đồng hồ hai giờ Chủ tịch ký ngày 18/9/2026 sẽ vẫn xanh trên màn hình trong khi vụ thật
đang chạy ngoài kia — và không có phép đo nào bắt được, vì bản thân phép đo cũng đọc từ cùng một
bộ lọc. Cho máy quyết là tự bịt mắt mình rồi tự khen mình nhìn rõ.

Nên hình đúng là: máy lo KHÔNG ĐỂ SÓT, người lo QUYẾT ĐỊNH.

──────────────────────────────────────────────────────────────────────────────────────────────
BỘ LỌC NÀY PHỦ ĐƯỢC ĐẾN ĐÂU — NÓI TRƯỚC ĐỂ KHÔNG AI TIN QUÁ MỨC
──────────────────────────────────────────────────────────────────────────────────────────────

Hộp thư đa kênh của VTOS nhận TIN NHẮN RIÊNG: Facebook Messenger, Zalo OA, chat trên web
(`conversations.channel`). Nó KHÔNG nhận BÌNH LUẬN CÔNG KHAI dưới bài đăng Fanpage — Graph API
của bình luận là một luồng khác, chưa ai nối vào VTOS.

Đó là một khoảng trống thật, và là khoảng trống ở đúng chỗ đau nhất: một bình luận công khai thì
người ngoài đọc được ngay, còn tin nhắn riêng thì chưa. Màn hình Marketing vì thế phải ghi thẳng
"chưa có" cho phần bình luận công khai, chứ không được để người đọc tưởng hàng đợi này là tất cả.

──────────────────────────────────────────────────────────────────────────────────────────────
BA DẤU HIỆU, MỖI DẤU HIỆU MỘT LÝ DO
──────────────────────────────────────────────────────────────────────────────────────────────

  · TỪ ĐỎ (+2) — danh sách ký, sửa được bằng tham số `pr_tu_do` mà không phải đụng vào mã.
    Cộng 2 một lần thôi, dù khớp mấy từ: một câu chửi dài không nguy hiểm hơn một câu "tôi sẽ kiện".

  · DỐC (+1) — nhiều tin vào trong một khoảng ngắn trên cùng hội thoại. Một vụ thật thường trông
    giống một cái DỐC chứ không giống một cái TỪ; khách đang bình tĩnh không nhắn sáu tin trong
    mười phút.

  · QUÁ HẠN TRẢ LỜI (+1) — hội thoại chưa ai trả lời và đã quá hạn SLA của Sales. Một vụ nhỏ bị
    bỏ quên là cách phổ biến nhất để nó lớn lên; tin nhắn thứ hai của người đã bị lờ bao giờ cũng
    gắt hơn tin thứ nhất.

Ngưỡng mặc định 2 nghĩa là: một từ đỏ đủ để vào hàng đợi, hoặc dốc + quá hạn cộng lại cũng đủ.

──────────────────────────────────────────────────────────────────────────────────────────────
VÀ MỘT PHÉP ĐO CHÍNH NÓ — CHỖ MÀ HẦU HẾT HỆ THỐNG BỎ QUÊN
──────────────────────────────────────────────────────────────────────────────────────────────

Bộ lọc nào cũng mòn, và mòn TRONG IM LẶNG. `do_bo_loc()` trả ra ba con số mỗi kỳ:

  · BẮT ĐÚNG  – hàng đợi nêu, người xác nhận là khủng hoảng.
  · BÁO NHẦM  – hàng đợi nêu, người xem rồi bỏ qua. Cao quá thì người ta thôi mở hàng đợi; nhưng
                nó không làm chết ai.
  · BỎ SÓT    – một vụ khủng hoảng có gắn tin nguồn, mà chấm lại ngay bây giờ vẫn dưới ngưỡng.
                Đây là con số duy nhất thật sự quan trọng, và mục tiêu của nó là 0.

BỎ SÓT chỉ đo được trên những vụ CÓ GẮN TIN NGUỒN. Một vụ nổ trên báo thì không có tin nào trong
hộp thư để mà đối chiếu — `do_bo_loc()` nói thẳng con số ấy ra ở khoá `khong_co_tin_nguon` thay vì
lặng lẽ để nó rơi khỏi mẫu số và làm tỷ lệ đẹp lên.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.crm import Conversation, Message
from app.models.marketing import HopThuXuLy, PrHoatDong
from app.services import rules as R

THAM_SO_TU_DO = "pr_tu_do"
THAM_SO_NGUONG = "pr_nguong_canh_bao"
THAM_SO_CUM_PHUT = "pr_cum_phut"
THAM_SO_CUM_SO_TIN = "pr_cum_so_tin"

# Số ngày hàng đợi nhìn lại. Không phải tham số ký: đây là cỡ cửa sổ đọc của một màn hình, không
# phải một luật của công ty. Màn hình truyền số ngày của chính nó xuống.
NGAY_MAC_DINH = 7

DIEM_TU_DO = 2
DIEM_DOC = 1
DIEM_QUA_HAN = 1


# ---------------------------------------------------------------------------------------------
# Tham số đã ký
# ---------------------------------------------------------------------------------------------
def tu_do(db: Session) -> list[str]:
    """Danh sách từ đỏ, đã bỏ dấu và viết thường — so khớp không phân biệt hoa thường và dấu."""
    tho = R.get_param_chu(db, THAM_SO_TU_DO)
    return [bo_dau(t) for t in (x.strip() for x in tho.split(",")) if t]


def nguong(db: Session) -> int:
    return int(R.get_param(db, THAM_SO_NGUONG))


def cum_phut(db: Session) -> int:
    return int(R.get_param(db, THAM_SO_CUM_PHUT))


def cum_so_tin(db: Session) -> int:
    return int(R.get_param(db, THAM_SO_CUM_SO_TIN))


# ---------------------------------------------------------------------------------------------
# Chấm điểm — hàm thuần, không đụng cơ sở dữ liệu
# ---------------------------------------------------------------------------------------------
def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt và viết thường.

    Vì người đang bực gõ "lua dao" cũng nhiều như gõ "lừa đảo", và một bộ lọc bắt được cái này mà
    trượt cái kia thì nó chỉ bắt được những người còn đủ bình tĩnh để bật bộ gõ.
    """
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d")


def tim_tu_do(text: str, danh_sach: list[str]) -> list[str]:
    """Những từ đỏ có mặt trong tin. Khớp theo RANH GIỚI TỪ, không khớp giữa chữ.

    "tố" nằm giữa "tối nay" không phải là tố cáo; khớp lỏng ở đây sinh ra một hàng đợi toàn tin
    vô hại, và một hàng đợi toàn tin vô hại là một hàng đợi không ai mở.
    """
    kho = bo_dau(text)
    thay = []
    for t in danh_sach:
        if t and re.search(r"(?<![0-9a-z])" + re.escape(t) + r"(?![0-9a-z])", kho):
            thay.append(t)
    return thay


def cham_diem(text: str, danh_sach_tu_do: list[str], la_doc: bool = False,
              qua_han_tra_loi: bool = False) -> tuple[int, list[str]]:
    """Trả về (điểm, danh sách lý do đọc được). Lý do là thứ người trực đọc, nên nó viết bằng
    tiếng người chứ không phải mã."""
    diem, ly_do = 0, []
    thay = tim_tu_do(text, danh_sach_tu_do)
    if thay:
        diem += DIEM_TU_DO
        ly_do.append("Từ đỏ: " + ", ".join(thay))
    if la_doc:
        diem += DIEM_DOC
        ly_do.append("Dốc: nhiều tin liên tiếp trong thời gian ngắn")
    if qua_han_tra_loi:
        diem += DIEM_QUA_HAN
        ly_do.append("Quá hạn trả lời: chưa ai trả lời và đã quá hạn SLA")
    return diem, ly_do


# ---------------------------------------------------------------------------------------------
# Hàng đợi
# ---------------------------------------------------------------------------------------------
def _moc(ngay: int, bay_gio: datetime | None = None) -> datetime:
    return (bay_gio or datetime.now()) - timedelta(days=max(1, int(ngay)))


TRAN_DONG = 5000


def ung_vien(db: Session, ngay: int = NGAY_MAC_DINH, bay_gio: datetime | None = None) -> list:
    """Tin khách gửi vào trong cửa sổ ngày — KHÔNG lọc thô bằng từ đỏ ở máy chủ.

    ĐÃ THỬ LỌC THÔ BẰNG `LIKE '%lua dao%'` VÀ NÓ SAI LẶNG. Chuỗi trong cơ sở dữ liệu có dấu
    ("lừa đảo"), còn danh sách từ đỏ đã bỏ dấu để so khớp cho cả hai cách gõ. `LIKE` của SQL không
    biết bỏ dấu, nên đúng những tin viết ĐÚNG CHÍNH TẢ — tức là phần lớn — không bao giờ lọt qua
    cửa lọc thô để được chấm. Màn hình vẫn chạy, hàng đợi vẫn có dòng, và không con số nào kêu lên.
    Đó là kiểu hỏng tệ nhất của một bộ lọc: nó vẫn trông như đang làm việc.

    Nên cửa này chỉ cắt theo THỜI GIAN, và việc chấm để nguyên ở Python nơi phép bỏ dấu sống. Cửa
    sổ mặc định là 7 ngày; số dòng thật của bảy ngày ở Vietourist là vài trăm, không phải trăm
    nghìn (con số 117.208 dòng của bảng `messages` là hậu quả của lỗi nạp bù trùng đã sửa).

    TRẦN 5.000 DÒNG, và khi chạm trần thì NÓI RA (`cat_bot`) chứ không im lặng trả về một danh
    sách thiếu — một hàng đợi thiếu dòng mà không báo thì tệ hơn hẳn một hàng đợi chậm.
    """
    moc = _moc(ngay, bay_gio)
    q = (select(Message, Conversation)
         .join(Conversation, Conversation.id == Message.conversation_id)
         .where(Message.direction == "in", Message.at >= moc)
         .order_by(Message.at.desc()).limit(TRAN_DONG + 1))
    return list(db.execute(q).all())


def _dem_cum(db: Session, ids: list[int], phut: int, bay_gio: datetime | None = None) -> dict:
    """Số tin vào của mỗi hội thoại trong `phut` phút gần nhất.

    `conversation_id.in_(ids)` ở đây là CẮT BỚT CHO NHANH, không phải một luật. Bỏ nó đi thì kết
    quả cho những id đang cần vẫn y nguyên — phép gom vẫn gom theo từng hội thoại — chỉ là truy
    vấn đếm thừa cả hộp thư. Bẻ mã 19/9/2026 (M7) đã thử bỏ và không phép thử nào đỏ, và đó là
    ĐÚNG: đây là một đột biến tương đương, không phải một khe hở. Ghi lại để người sau khỏi đi viết
    một phép thử giả chỉ để nó đỏ.

    Luật thật — "dốc đếm theo HỘI THOẠI, không theo cả hộp thư" — nằm ở `group_by` dưới đây, và
    phép thử `test_C_doc_dem_theo_HOI_THOAI_khong_theo_ca_hop_thu` gác đúng chỗ ấy.
    """
    if not ids:
        return {}
    moc = (bay_gio or datetime.now()) - timedelta(minutes=max(1, int(phut)))
    rows = db.execute(
        select(Message.conversation_id, func.count(Message.id))
        .where(Message.direction == "in", Message.conversation_id.in_(ids), Message.at >= moc)
        .group_by(Message.conversation_id)).all()
    return {cid: n for cid, n in rows}


def _da_xu_ly(db: Session, ids: list[int]) -> dict:
    if not ids:
        return {}
    rows = db.execute(select(HopThuXuLy).where(HopThuXuLy.message_id.in_(ids))).scalars().all()
    return {x.message_id: x for x in rows}


def canh_bao(db: Session, ngay: int = NGAY_MAC_DINH, nguong_tuy: int | None = None,
             ke_ca_da_xu_ly: bool = False, bay_gio: datetime | None = None) -> dict:
    """Hàng đợi tin đáng đọc trước.

    `nguong_tuy` cho màn hình hạ ngưỡng xuống để XEM LẠI những tin bị xếp sau — đó là cách giữ lời
    hứa "không vứt tin nào đi". Nó không sửa tham số đã ký; nó chỉ đổi cách nhìn của một lần xem.
    """
    n = int(nguong_tuy) if nguong_tuy is not None else nguong(db)
    ds = tu_do(db)
    hang = ung_vien(db, ngay, bay_gio)
    cat_bot = len(hang) > TRAN_DONG
    hang = hang[:TRAN_DONG]
    ids_hoi_thoai = sorted({c.id for _m, c in hang})
    cum = _dem_cum(db, ids_hoi_thoai, cum_phut(db), bay_gio)
    nguong_cum = cum_so_tin(db)
    gio = bay_gio or datetime.now()

    cham = []
    for m, c in hang:
        la_doc = cum.get(c.id, 0) >= nguong_cum
        tre = bool(c.unanswered and c.sla_due_at and c.sla_due_at < gio)
        diem, ly_do = cham_diem(m.text or "", ds, la_doc, tre)
        if diem >= n:
            cham.append((m, c, diem, ly_do))

    xu_ly = _da_xu_ly(db, [m.id for m, _c, _d, _l in cham])
    dong = []
    for m, c, diem, ly_do in cham:
        x = xu_ly.get(m.id)
        if x is not None and not ke_ca_da_xu_ly:
            continue
        dong.append(mot_dong(m, c, diem, ly_do, x))
    dong.sort(key=lambda d: (-d["diem"], d["luc"]), reverse=False)
    dong.sort(key=lambda d: d["diem"], reverse=True)

    return {
        "rows": dong,
        "nguong": n,
        "nguong_ky": nguong(db),
        "ngay": int(ngay),
        "tu_do": ds,
        # Chạm trần thì nói ra. Màn hình phải hiện dòng này — một hàng đợi thiếu dòng mà im lặng
        # tệ hơn hẳn một hàng đợi chậm.
        "cat_bot": cat_bot,
        "tran_dong": TRAN_DONG,
        "dem": {
            "cho_xem": sum(1 for d in dong if d["ket_luan"] == ""),
            "co_tu_do": sum(1 for d in dong if d["co_tu_do"]),
            "tong_cham": len(cham),
        },
    }


def mot_dong(m: Message, c: Conversation, diem: int, ly_do: list[str], x) -> dict:
    """Một dòng hàng đợi.

    KHÔNG trả về số điện thoại của khách. Màn hình này mở cho cả phòng Marketing, và một vụ khủng
    hoảng không cần số điện thoại để xử lý — nó cần nội dung và thời điểm. Ai cần gọi khách thì vào
    hộp thư, nơi quyền đã được đặt riêng cho việc ấy.
    """
    return {
        "message_id": m.id,
        "conversation_id": c.id,
        "kenh": c.channel,
        "khach": c.customer_name or "(chưa có tên)",
        "trich": (m.text or "")[:400],
        "luc": f"{m.at:%Y-%m-%d %H:%M:%S}" if m.at else "",
        "diem": diem,
        "ly_do": ly_do,
        "co_tu_do": any(l.startswith("Từ đỏ") for l in ly_do),
        "ket_luan": (x.ket_luan if x is not None else ""),
        "pr_id": (x.pr_id if x is not None else None),
        "xu_ly_boi": (x.nguoi if x is not None else ""),
        "xu_ly_luc": (f"{x.luc:%Y-%m-%d %H:%M:%S}" if x is not None and x.luc else ""),
    }


# ---------------------------------------------------------------------------------------------
# Ghi kết luận của NGƯỜI
# ---------------------------------------------------------------------------------------------
def _ghi(db: Session, m: Message, c: Conversation, diem: int, ly_do: list[str],
         ket_luan: str, boi: str, ghi_chu: str = "", pr_id: int | None = None) -> HopThuXuLy:
    x = db.execute(select(HopThuXuLy).where(HopThuXuLy.message_id == m.id)).scalars().first()
    if x is None:
        x = HopThuXuLy(message_id=m.id, conversation_id=c.id)
        db.add(x)
    x.diem_luc_do = diem
    x.ly_do_luc_do = " | ".join(ly_do)
    x.co_tu_do = any(l.startswith("Từ đỏ") for l in ly_do)
    x.ket_luan = ket_luan
    x.ghi_chu = (ghi_chu or "")[:300]
    x.pr_id = pr_id
    x.nguoi = (boi or "")[:50]
    x.luc = datetime.now()
    db.flush()
    return x


def _lay(db: Session, message_id: int, bay_gio: datetime | None = None):
    """Lấy tin + hội thoại + điểm CHẤM LẠI TẠI THỜI ĐIỂM BẤM.

    Chấm lại chứ không đọc lại điểm cũ: tham số có thể đã đổi giữa lúc màn hình tải và lúc người
    bấm, và con số được lưu phải là con số bộ lọc thật sự nói ra lúc ấy — nếu không thì phép đo
    `do_bo_loc()` đo một bộ lọc không còn tồn tại.
    """
    row = db.execute(
        select(Message, Conversation)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == int(message_id))).first()
    if row is None:
        return None, None, 0, []
    m, c = row
    gio = bay_gio or datetime.now()
    cum = _dem_cum(db, [c.id], cum_phut(db), gio)
    la_doc = cum.get(c.id, 0) >= cum_so_tin(db)
    tre = bool(c.unanswered and c.sla_due_at and c.sla_due_at < gio)
    diem, ly_do = cham_diem(m.text or "", tu_do(db), la_doc, tre)
    return m, c, diem, ly_do


def bo_qua(db: Session, message_id: int, boi: str, ly_do: str) -> dict:
    """Người xem xong và kết luận đây không phải việc của Marketing.

    `ly_do` BẮT BUỘC. Không phải để hành người trực, mà vì hàng đợi này chỉ sống được nếu tỷ lệ
    báo nhầm đọc được: một trăm dòng "bỏ qua" không lý do không nói được bộ lọc sai ở đâu, còn
    một trăm dòng có lý do thì đọc mười dòng là thấy ngay từ nào đang bắt nhầm.
    """
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi lý do bỏ qua – hàng đợi chỉ sửa được khi biết nó sai ở đâu")
    m, c, diem, ds_ly_do = _lay(db, message_id)
    if m is None:
        raise ValueError("Không tìm thấy tin này")
    _ghi(db, m, c, diem, ds_ly_do, "bo_qua", boi, ly_do)
    db.commit()
    return {"message": "Đã bỏ qua", "message_id": m.id}


def lap_pr(db: Session, message_id: int, boi: str, r: dict) -> dict:
    """Người xem xong và lập một dòng vào sổ hoạt động PR.

    ĐÂY LÀ CHỖ DUY NHẤT `la_khung_hoang` ĐƯỢC ĐẶT TỪ HÀNG ĐỢI, và nó đọc từ ô người tích, không
    phải từ điểm của bộ lọc. Đồng hồ hai giờ bắt đầu chạy đúng lúc người tích — không sớm hơn vì
    máy đoán, không muộn hơn vì máy còn đang nghĩ.
    """
    from app.services import pr_hoat_dong as PR

    m, c, diem, ds_ly_do = _lay(db, message_id)
    if m is None:
        raise ValueError("Không tìm thấy tin này")
    cu = db.execute(select(HopThuXuLy).where(HopThuXuLy.message_id == m.id)).scalars().first()
    if cu is not None and cu.ket_luan == "lap_pr" and cu.pr_id:
        raise ValueError(f"Tin này đã lập dòng PR rồi (#{cu.pr_id}) – không lập hai lần")

    tieu_de = str(r.get("tieu_de") or "").strip() or f"Tin từ {c.channel}: {(m.text or '')[:80]}"
    h = PR.tao(db, {
        "loai": str(r.get("loai") or "khung_hoang").strip() or "khung_hoang",
        "tieu_de": tieu_de,
        "tom_tat": (m.text or "")[:2000],
        "noi_dang": f"Hộp thư đa kênh – {c.channel}",
        "la_khung_hoang": bool(r.get("la_khung_hoang")),
        "muc_do": str(r.get("muc_do") or "").strip(),
        "ghi_chu": str(r.get("ghi_chu") or "").strip(),
    }, boi)
    h.nguon_message_id = m.id
    _ghi(db, m, c, diem, ds_ly_do, "lap_pr", boi, str(r.get("ghi_chu") or ""), pr_id=h.id)
    db.commit()
    return {"message": f"Đã lập dòng {h.ma}", "pr_id": h.id, "ma": h.ma,
            "la_khung_hoang": bool(h.la_khung_hoang)}


# ---------------------------------------------------------------------------------------------
# Đo chính bộ lọc
# ---------------------------------------------------------------------------------------------
def do_bo_loc(db: Session, tu: datetime | None = None, den: datetime | None = None,
              bay_gio: datetime | None = None) -> dict:
    """Ba con số, và một con số thứ tư nói ra phần KHÔNG đo được.

    BỎ SÓT chấm LẠI bằng bộ lọc HIỆN TẠI, không đọc điểm đã lưu. Vì câu hỏi cần trả lời không phải
    "hồi đó bộ lọc thế nào" mà "bộ lọc BÂY GIỜ có bắt được vụ ấy không" — đó mới là con số dùng để
    quyết có sửa danh sách từ đỏ hay không.
    """
    q = select(PrHoatDong).where(PrHoatDong.la_khung_hoang.is_(True))
    if tu is not None:
        q = q.where(PrHoatDong.ghi_nhan_luc >= tu)
    if den is not None:
        q = q.where(PrHoatDong.ghi_nhan_luc < den)
    vu = db.execute(q).scalars().all()

    n = nguong(db)
    bo_sot, khong_co_tin, bat_dung = [], 0, 0
    for h in vu:
        if not h.nguon_message_id:
            khong_co_tin += 1
            continue
        _m, _c, diem, _ly = _lay(db, h.nguon_message_id, bay_gio)
        if _m is None:
            khong_co_tin += 1
        elif diem >= n:
            bat_dung += 1
        else:
            bo_sot.append({"ma": h.ma, "tieu_de": h.tieu_de, "diem_cham_lai": diem,
                           "message_id": h.nguon_message_id})

    qbo = select(func.count(HopThuXuLy.id)).where(HopThuXuLy.ket_luan == "bo_qua")
    if tu is not None:
        qbo = qbo.where(HopThuXuLy.luc >= tu)
    if den is not None:
        qbo = qbo.where(HopThuXuLy.luc < den)
    bao_nham = int(db.execute(qbo).scalar() or 0)

    return {
        "bat_dung": bat_dung,
        "bao_nham": bao_nham,
        "bo_sot": len(bo_sot),
        "bo_sot_ds": bo_sot,
        "khong_co_tin_nguon": khong_co_tin,
        "nguong": n,
        "ghi_chu": "Bỏ sót chỉ đo được trên vụ CÓ gắn tin nguồn; vụ nổ trên báo không có tin nào "
                   "trong hộp thư để đối chiếu và được đếm riêng ở khong_co_tin_nguon.",
    }
