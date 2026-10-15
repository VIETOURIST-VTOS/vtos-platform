# -*- coding: utf-8 -*-
"""Đợt R4a 15/10/2026 — MA TRẬN CẶP ĐỊNH KHOẢN, và đối chiếu nó với BẢNG QUY ƯỚC.

VÌ SAO CÓ TỆP NÀY

Bảng quy ước hạch toán (`services/hach_toan.py`) nói sổ NÊN có những cặp định khoản nào. Không có
gì nói sổ ĐANG có những cặp nào. Hai thứ ấy lệch nhau bằng đúng những bút toán ai đó định khoản
tay — và một bút toán tay sai tài khoản thì sổ vẫn cân, báo cáo vẫn ra số, không phép thử nào đỏ.

Báo cáo này liệt kê MỌI cặp (Nợ X / Có Y) đang có thật trong sổ kèm số tiền, rồi chỉ ra cặp nào
KHÔNG có trong bảng quy ước. Rẻ để viết, và bắt được loại lỗi mà không hàng rào nào khác bắt được,
vì nó không hỏi "phép tính có đúng không" mà hỏi "sổ có đang đi đúng những con đường đã khai không".

════ MỘT CHỖ KHÔNG CHIA ĐƯỢC, VÀ KHÔNG ĐƯỢC ĐOÁN ════

Một chứng từ MỘT vế Nợ – NHIỀU vế Có thì cặp nào bao nhiêu tiền là rõ: lấy số của vế Có.
Ngược lại cũng vậy. Nhưng chứng từ NHIỀU Nợ – NHIỀU Có thì KHÔNG CHIA ĐƯỢC: 2 dòng Nợ và 3 dòng
Có cho 6 cặp, mà tiền của từng cặp không nằm ở đâu trong sổ cả.

Chia bừa (chia đều, chia theo tỷ lệ) là bịa ra một con số chưa từng được ghi, rồi đặt nó vào một
báo cáo mà người đọc tin là đọc từ sổ. Nên những chứng từ ấy KHÔNG vào ma trận, và được đếm riêng
ở `nhieu_nhieu` kèm số tiền và danh sách mã chứng từ — người đọc thấy ngay phần nào không được
phân tích, thay vì thấy một ma trận trông đầy đủ mà thiếu thầm.

════ GIỚI HẠN BỘ NHỚ ════

Máy chủ 512 MB, sổ thật hơn 100.000 dòng. Cả hai phép đếm đều GOM Ở CƠ SỞ DỮ LIỆU — bài học Đợt
E18, nơi cửa BCTC kéo cả sổ về bộ nhớ rồi trả 502. Không có chỗ nào ở đây nạp dòng sổ lên Python.
"""
from datetime import date

from sqlalchemy import select, func, case, and_, distinct
from sqlalchemy.orm import Session, aliased

from app.models.accounting import Account, JournalEntry, JournalLine

POSTED = "da_ghi_so"
TRAN_DONG = 500          # trần số cặp trả về cho giao diện
TRAN_CHUNG_TU = 50       # trần số mã chứng từ liệt kê cho phần không chia được

# ══════════════════════════════════════════════════════════════════════════════════════════════
# NGUỒN KHÔNG ĐI QUA BẢNG QUY ƯỚC — và vì sao từng cái một
#
# Khai riêng ở đây chứ KHÔNG dùng chung danh sách của `accounting.account_rule_check`, dù hôm nay
# hai danh sách trùng nhau. Hai danh sách ấy trả lời HAI câu hỏi khác nhau: bên kia hỏi "dòng này
# có cần mã đối tượng / mã công trình không", bên này hỏi "cặp định khoản này có phải do bảng quy
# ước sinh ra không". Gộp làm một thì ngày một trong hai câu đổi, câu kia đổi theo mà không ai
# muốn — và cái đổi theo ấy sẽ im lặng.
# ══════════════════════════════════════════════════════════════════════════════════════════════
NGUON_KHONG_QUA_QUY_TAC = {
    "misa":          "Bút toán nhập từ sổ MISA — định khoản do MISA quyết, không phải bảng quy ước VTOS.",
    "so_du_dau_ky":  "Số dư đầu kỳ: một vế là tài khoản thật, vế kia là 411 cân đối. Không có nghiệp vụ.",
    "kiem_toan":     "Chốt sổ theo bộ số kiểm toán đã ký — con số là của kiểm toán, đường đi là chênh lệch.",
    "dao":           "Đảo bút toán: cặp của nó là cặp của bút toán gốc, lật ngược.",
    "luong":         "Bảng lương sinh bút toán theo bảng lương đã duyệt, không theo bảng quy ước.",
    "ket_chuyen":    "Kết chuyển cuối kỳ chạy theo `ket_so.BUOC_KET_CHUYEN`, một bảng khai khác.",
}


def _dem_ve(since: date | None, upto: date):
    """Mỗi chứng từ có mấy vế Nợ, mấy vế Có. Gom ở CSDL, trả về một bảng con."""
    q = (select(JournalLine.entry_id.label("entry_id"),
                func.count(case((JournalLine.debit > 0, 1))).label("n_no"),
                func.count(case((JournalLine.credit > 0, 1))).label("n_co"))
         .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
         .where(JournalEntry.status == POSTED, JournalEntry.entry_date <= upto))
    if since:
        q = q.where(JournalEntry.entry_date >= since)
    return q.group_by(JournalLine.entry_id).subquery()


def ma_tran(db: Session, upto: date, since: date | None = None,
            tran: int = TRAN_DONG) -> dict:
    """Mọi cặp (Nợ X / Có Y) có thật trong sổ, kèm số tiền và số chứng từ.

    Cặp lấy từ CHÍNH SỔ, không lấy từ bảng quy ước — đó là cả ý nghĩa của báo cáo này.
    """
    dem = _dem_ve(since, upto)
    A, B = aliased(JournalLine), aliased(JournalLine)

    # Số tiền của một cặp:
    #   một vế Nợ   -> lấy số của vế Có   (chia hết, không mất đồng nào)
    #   một vế Có   -> lấy số của vế Nợ
    #   nhiều–nhiều -> 0 ở đây, và đếm riêng ở `nhieu_nhieu` phía dưới
    tien = case((dem.c.n_no == 1, B.credit), (dem.c.n_co == 1, A.debit), else_=0)
    chia_duoc = (dem.c.n_no == 1) | (dem.c.n_co == 1)

    q = (select(A.account_code.label("tk_no"), B.account_code.label("tk_co"),
                func.sum(tien).label("so_tien"),
                func.count(distinct(A.entry_id)).label("so_chung_tu"))
         .select_from(A)
         .join(B, B.entry_id == A.entry_id)
         .join(dem, dem.c.entry_id == A.entry_id)
         .join(JournalEntry, JournalEntry.id == A.entry_id)
         .where(A.debit > 0, B.credit > 0, chia_duoc,
                JournalEntry.status == POSTED, JournalEntry.entry_date <= upto))
    if since:
        q = q.where(JournalEntry.entry_date >= since)
    q = q.group_by(A.account_code, B.account_code).order_by(func.sum(tien).desc())

    rows = db.execute(q).all()
    ten = {a.code: a.name for a in db.execute(select(Account)).scalars()}
    cap = [{"tk_no": r.tk_no, "ten_no": ten.get(r.tk_no, ""),
            "tk_co": r.tk_co, "ten_co": ten.get(r.tk_co, ""),
            "so_tien": round(r.so_tien or 0, 0), "so_chung_tu": r.so_chung_tu}
           for r in rows]

    return {"tu_ngay": since, "den_ngay": upto,
            "so_cap": len(cap), "cap": cap[:tran], "cat_bot": len(cap) > tran,
            "tong_tien": round(sum(c["so_tien"] for c in cap), 0),
            "nhieu_nhieu": _nhieu_nhieu(db, upto, since)}


def _nhieu_nhieu(db: Session, upto: date, since: date | None) -> dict:
    """Chứng từ nhiều vế Nợ VÀ nhiều vế Có — phần KHÔNG chia được, nói ra chứ không giấu."""
    dem = _dem_ve(since, upto)
    q = (select(JournalEntry.id, JournalEntry.code,
                func.sum(JournalLine.debit).label("tien"))
         .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
         .join(dem, dem.c.entry_id == JournalEntry.id)
         .where(dem.c.n_no > 1, dem.c.n_co > 1,
                JournalEntry.status == POSTED, JournalEntry.entry_date <= upto))
    if since:
        q = q.where(JournalEntry.entry_date >= since)
    rows = db.execute(q.group_by(JournalEntry.id, JournalEntry.code)).all()
    return {
        "so_chung_tu": len(rows),
        "so_tien": round(sum(r.tien or 0 for r in rows), 0),
        "chung_tu": [r.code for r in rows[:TRAN_CHUNG_TU]],
        "vi_sao": ("Chứng từ có NHIỀU vế Nợ và NHIỀU vế Có thì tiền của từng cặp không nằm ở đâu "
                   "trong sổ cả. Chia đều hay chia theo tỷ lệ là bịa ra một con số chưa từng được "
                   "ghi, nên những chứng từ này KHÔNG vào ma trận. Muốn phân tích được chúng thì "
                   "tách chứng từ lúc ghi sổ, không phải đoán lúc đọc báo cáo."),
    }


def _cap_trong_quy_uoc(db: Session, on: date | None = None) -> list[dict]:
    """Cặp định khoản mà bảng quy ước ĐANG cho phép, kèm cả vế thuế.

    Khai theo TÀI KHOẢN CHA (quy ước ghi "154", "331"), nên đối chiếu bằng TIỀN TỐ — đúng lệ V8:
    luật khai ở cấp cha, con lấy từ sổ.
    """
    from app.services import hach_toan as HT
    ra = []
    for q in HT.dang_hieu_luc(db, "", on):
        ra.append({"ma": q.ma, "no": q.tk_no, "co": q.tk_co, "vai": "chính"})
        if q.tk_thue and q.ben_thue == "no":
            ra.append({"ma": q.ma, "no": q.tk_thue, "co": q.tk_co, "vai": "thuế đầu vào"})
        elif q.tk_thue and q.ben_thue == "co":
            ra.append({"ma": q.ma, "no": q.tk_no, "co": q.tk_thue, "vai": "thuế đầu ra"})
    return ra


def ngoai_luat(db: Session, upto: date, since: date | None = None,
               on: date | None = None, tran: int = TRAN_DONG) -> dict:
    """Cặp có trong SỔ mà KHÔNG có trong bảng quy ước — tức là định khoản ngoài luật đã khai.

    KHÔNG tự sửa gì, và cũng không gọi đây là "lỗi": một cặp ngoài luật có thể là một nghiệp vụ
    thật mà bảng quy ước còn thiếu dòng. Báo cáo chỉ ra CHỖ PHẢI NHÌN, rồi Kế toán trưởng quyết
    hoặc thêm một dòng quy ước, hoặc sửa bút toán.
    """
    mt = ma_tran(db, upto, since, tran=10 ** 9)
    quy_uoc = _cap_trong_quy_uoc(db, on)

    # Nguồn nào không đi qua bảng quy ước thì cặp của nó không được coi là ngoài luật.
    dem = _dem_ve(since, upto)
    A, B = aliased(JournalLine), aliased(JournalLine)
    # Hai CỘT rồi gom thành tập trong Python, chứ không nối chuỗi trong SQL: `concat` không cùng
    # một phương ngữ giữa SQLite (phép thử) và Postgres (máy chủ), và một câu truy vấn chỉ chạy
    # được ở một trong hai nơi là một chỗ hỏng chỉ lộ ra lúc triển khai.
    qm = (select(A.account_code, B.account_code).distinct()
          .select_from(A)
          .join(B, B.entry_id == A.entry_id)
          .join(dem, dem.c.entry_id == A.entry_id)
          .join(JournalEntry, JournalEntry.id == A.entry_id)
          .where(A.debit > 0, B.credit > 0,
                 (dem.c.n_no == 1) | (dem.c.n_co == 1),
                 JournalEntry.status == POSTED, JournalEntry.entry_date <= upto,
                 JournalEntry.source_type.in_(tuple(NGUON_KHONG_QUA_QUY_TAC))))
    if since:
        qm = qm.where(JournalEntry.entry_date >= since)
    mien = {(a, b) for a, b in db.execute(qm).all()}

    ra = []
    for c in mt["cap"]:
        if (c["tk_no"], c["tk_co"]) in mien:
            continue
        if any(c["tk_no"].startswith(q["no"]) and c["tk_co"].startswith(q["co"])
               for q in quy_uoc):
            continue
        ra.append(c)

    return {
        "tu_ngay": since, "den_ngay": upto,
        "so_cap_trong_so": mt["so_cap"],
        "so_cap_trong_quy_uoc": len(quy_uoc),
        "so_cap_ngoai_luat": len(ra),
        "cap_ngoai_luat": ra[:tran], "cat_bot": len(ra) > tran,
        "so_tien_ngoai_luat": round(sum(c["so_tien"] for c in ra), 0),
        "nguon_duoc_mien": NGUON_KHONG_QUA_QUY_TAC,
        "nhieu_nhieu": mt["nhieu_nhieu"],
        "ghi_chu": ("Một cặp ngoài luật KHÔNG đương nhiên là sai: có thể là nghiệp vụ thật mà bảng "
                    "quy ước còn thiếu dòng. Báo cáo chỉ ra chỗ phải nhìn; Kế toán trưởng quyết "
                    "thêm một dòng quy ước hay sửa bút toán. Và phần `nhieu_nhieu` KHÔNG được xét "
                    "ở đây — đọc nó trước khi kết luận là sổ sạch."),
    }
