# -*- coding: utf-8 -*-
"""ĐỐI CHIẾU SỐ DƯ ĐẦU KỲ — Đợt R6b-1, 23/10/2026.

BA LUẬT, và cả ba đều là quyết định của Chủ tịch ngày 23/10/2026 chứ không phải lựa chọn kỹ thuật:

  1. TỔNG SỔ PHỤ PHẢI BẰNG CỬA CHỐT. Lệch thì nói to, và KHÔNG tự sửa bên nào cho khớp.
  2. DÒNG THIẾU MÃ ĐỐI TƯỢNG KHÔNG VÀO TỔNG. Cộng nó vào thì cửa chốt trông như đã khớp trong
     khi một phần tiền chưa biết thuộc về ai — tức là phép đối chiếu báo xanh đúng lúc nó
     đáng ra phải báo đỏ.
  3. DÒNG THIẾU MÃ KHÔNG BỊ XOÁ. Nó là số liệu thật người nhập vừa đưa vào. Xoá đi là làm mất
     tiền khỏi sổ để bảng trông sạch.

Luật 2 và 3 nghe ngược nhau nhưng không ngược: dòng ấy nằm trong SỔ, chỉ không nằm trong TỔNG.
Hệ quả đo được, và là hệ quả cố ý: khi mọi dòng thiếu mã nằm trên một tài khoản thì số lệch của
tài khoản ấy BẰNG ĐÚNG tổng tiền của các dòng thiếu mã. Người đọc thấy ngay việc phải làm là
gán mã, không phải đi tìm một con số sai.

TỆP NÀY KHÔNG GHI MỘT DÒNG NÀO. Nó chỉ đọc và trả lời. Cửa ghi là bộ nạp tệp
(`intake_so_du_dau_ky`) và màn hình nhập tay — theo ranh giới 09/9/2026.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.accounting import Account
from app.models.so_du_dau_ky import (SoDuDauKy, SoDuDauKyDoDang, SoDuDauKyKhachHang,
                                     SoDuDauKyNganHang, SoDuDauKyNhaCungCap, SoDuDauKyNhanVien,
                                     SoDuDauKyTaiSan, SoDuDauKyTraTruoc)

# Bảy sổ phụ, theo đúng thứ tự hiện trên màn hình. `cot_no` / `cot_co` nói cột nào của sổ phụ
# cộng về cột nào của cửa chốt — khai ra đây chứ không viết cứng trong vòng lặp, vì ba sổ cuối
# có hình cột khác hẳn bốn sổ đầu (tài sản cộng bằng NGUYÊN GIÁ, dở dang chỉ có một cột tiền).
SO_PHU = (
    {"ma": "ngan_hang", "ten": "Số dư TK ngân hàng", "lop": SoDuDauKyNganHang,
     "cot_no": "du_no", "cot_co": "du_co", "doi_tuong": "Mã ngân hàng / tài khoản"},
    {"ma": "khach_hang", "ten": "Công nợ khách hàng", "lop": SoDuDauKyKhachHang,
     "cot_no": "du_no", "cot_co": "du_co", "doi_tuong": "Mã khách hàng"},
    {"ma": "nha_cung_cap", "ten": "Công nợ nhà cung cấp", "lop": SoDuDauKyNhaCungCap,
     "cot_no": "du_no", "cot_co": "du_co", "doi_tuong": "Mã nhà cung cấp"},
    {"ma": "nhan_vien", "ten": "Công nợ nhân viên", "lop": SoDuDauKyNhanVien,
     "cot_no": "du_no", "cot_co": "du_co", "doi_tuong": "Mã nhân viên"},
    # Nguyên giá, không phải giá trị còn lại: cửa chốt của TK 211 là nguyên giá, còn khấu hao
    # lũy kế là cửa chốt của TK 214. Cộng giá trị còn lại về 211 là lệch đúng bằng khấu hao.
    {"ma": "tai_san", "ten": "Tài sản cố định", "lop": SoDuDauKyTaiSan,
     "cot_no": "nguyen_gia", "cot_co": None, "doi_tuong": "Mã tài sản"},
    {"ma": "tra_truoc", "ten": "Chi phí trả trước", "lop": SoDuDauKyTraTruoc,
     "cot_no": "con_lai", "cot_co": None, "doi_tuong": "Mã khoản trả trước"},
    {"ma": "do_dang", "ten": "Chi phí dở dang", "lop": SoDuDauKyDoDang,
     "cot_no": "so_tien", "cot_co": None, "doi_tuong": "Mã công trình (mã tour)"},
)

SO_PHU_THEO_MA = {s["ma"]: s for s in SO_PHU}


def _cot(lop, ten: str | None):
    return getattr(lop, ten) if ten else None


def tong_so_phu(db: Session, ky: str, ma: str) -> dict:
    """Tổng một sổ phụ theo tài khoản, TÁCH dòng có mã khỏi dòng thiếu mã.

    Trả về {tk: {"no", "co", "no_thieu_ma", "co_thieu_ma", "so_dong", "so_dong_thieu_ma"}}.
    Hai nhóm đi riêng từ đây chứ không gộp rồi trừ ở chỗ khác: gộp rồi trừ là chỗ một dấu trừ
    gõ sai làm dòng thiếu mã lặng lẽ vào tổng, mà không phép thử số học nào bắt được.
    """
    s = SO_PHU_THEO_MA[ma]
    lop, cno, cco = s["lop"], _cot(s["lop"], s["cot_no"]), _cot(s["lop"], s["cot_co"])
    # Chuẩn hóa ngay trong câu truy vấn: một ô người nhập để " " là ô CHƯA GÁN MÃ, không phải
    # một mã tên là dấu cách. Nếu chỉ so với chuỗi rỗng thì dòng ấy lọt vào tổng.
    co_ma = func.length(func.trim(func.coalesce(lop.ma_doi_tuong, ""))) > 0
    ra: dict[str, dict] = {}
    cot = [lop.tk, co_ma.label("co_ma"), func.count().label("n"), func.sum(cno).label("no")]
    if cco is not None:
        cot.append(func.sum(cco).label("co"))
    for h in db.execute(select(*cot).where(lop.ky == ky).group_by(lop.tk, co_ma)).all():
        d = ra.setdefault(h.tk, {"no": 0.0, "co": 0.0, "no_thieu_ma": 0.0, "co_thieu_ma": 0.0,
                                 "so_dong": 0, "so_dong_thieu_ma": 0})
        hau = "" if h.co_ma else "_thieu_ma"
        d["no" + hau] += float(h.no or 0)
        if cco is not None:
            d["co" + hau] += float(getattr(h, "co", 0) or 0)
        d["so_dong" + hau] += int(h.n or 0)
    return ra


def cua_chot(db: Session, ky: str) -> dict[str, dict]:
    return {r.tk: {"no": float(r.du_no or 0), "co": float(r.du_co or 0)}
            for r in db.execute(select(SoDuDauKy).where(SoDuDauKy.ky == ky)).scalars()}


def doi_chieu(db: Session, ky: str) -> dict:
    """Bảng đối chiếu cửa chốt ↔ bảy sổ phụ cho một kỳ gốc.

    `khop` chỉ TRUE khi mọi tài khoản có sổ phụ đều lệch 0 VÀ không còn dòng nào thiếu mã. Hai
    điều kiện chứ không một: một kỳ có thể lệch 0 mà vẫn còn dòng thiếu mã — đúng lúc cửa chốt
    cũng bị nhập thiếu đúng bằng phần ấy. Lúc ấy số dư đầu kỳ vẫn chưa dùng được, vì phần tiền
    kia chưa biết thuộc về ai.
    """
    chot = cua_chot(db, ky)
    ten_tk = {a.code: a.name for a in db.execute(select(Account)).scalars()}
    dong, canh_bao = [], []
    tong_thieu_ma, tong_dong_thieu_ma = 0.0, 0
    for s in SO_PHU:
        phu = tong_so_phu(db, ky, s["ma"])
        for tk in sorted(phu):
            p = phu.get(tk, {})
            c = chot.get(tk)
            p_no, p_co = p.get("no", 0.0), p.get("co", 0.0)
            tm_no, tm_co = p.get("no_thieu_ma", 0.0), p.get("co_thieu_ma", 0.0)
            n_tm = p.get("so_dong_thieu_ma", 0)
            tong_thieu_ma += tm_no + tm_co
            tong_dong_thieu_ma += n_tm
            lech_no = (c["no"] if c else 0.0) - p_no
            lech_co = (c["co"] if c else 0.0) - p_co
            dong.append({
                "so": s["ma"], "so_ten": s["ten"], "tk": tk, "ten_tk": ten_tk.get(tk, ""),
                "chua_nhap_cua_chot": c is None,
                "chot_no": c["no"] if c else None, "chot_co": c["co"] if c else None,
                "phu_no": p_no, "phu_co": p_co,
                "lech_no": lech_no, "lech_co": lech_co,
                "so_dong": p.get("so_dong", 0), "so_dong_thieu_ma": n_tm,
                "tien_thieu_ma": tm_no + tm_co,
                "khop": c is not None and abs(lech_no) < 1 and abs(lech_co) < 1,
            })
            if n_tm:
                canh_bao.append(
                    f"{s['ten']} · TK {tk}: {n_tm} dòng chưa có mã đối tượng "
                    f"({_tien(tm_no + tm_co)} đ) — KHÔNG được cộng vào tổng, và cũng KHÔNG bị bỏ đi. "
                    f"Gán mã thì phần này vào tổng ngay")
    # Tài khoản có cửa chốt nhưng chưa có sổ phụ nào: nói riêng, vì đó là "chưa nhập", khác hẳn
    # "đã nhập và lệch". Gộp hai thứ ấy làm một là lý do người ta đi tìm sai chỗ.
    co_phu = {d["tk"] for d in dong}
    chua_co_so_phu = sorted(t for t in chot if t not in co_phu and _can_so_phu(db, t))
    lech = [d for d in dong if not d["khop"]]
    return {
        "ky": ky,
        "dong": dong,
        "lech": lech,
        "chua_co_so_phu": chua_co_so_phu,
        "tien_thieu_ma": tong_thieu_ma,
        "so_dong_thieu_ma": tong_dong_thieu_ma,
        "canh_bao": canh_bao,
        "khop": not lech and not chua_co_so_phu and tong_dong_thieu_ma == 0,
    }


def _can_so_phu(db: Session, tk: str) -> bool:
    """Tài khoản này có BẮT BUỘC sổ phụ không — đọc cờ của Đợt E1, không khai lần thứ hai.

    `accounts.td_doi_tuong` là chỗ MISA và VTOS đều khai "theo dõi chi tiết theo đối tượng".
    Khai lại một danh sách tài khoản ở tệp này là dựng nguồn thứ hai cho cùng một sự thật, và
    lúc hai nguồn lệch thì không ai biết nguồn nào đúng — đúng lỗi Đợt E1 phải đi gỡ.
    """
    a = db.get(Account, tk)
    return bool(a and (a.td_doi_tuong or a.td_cong_trinh))


def _tien(v: float) -> str:
    return f"{int(round(v or 0)):,}".replace(",", ".")
