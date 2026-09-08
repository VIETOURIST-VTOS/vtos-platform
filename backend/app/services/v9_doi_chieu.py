"""V9 – đối chiếu tổng TRƯỚC và SAU khi đổi kiểu cột tiền.

Nghiệm thu V9 đòi một điều duy nhất và đòi rất chặt: tổng phát sinh mọi tài khoản trước–sau KHÔNG
LỆCH MỘT ĐỒNG. Tệp này là cách chứng minh điều đó, và cách phát hiện trước khi mất số nếu có.

Vì sao phải có bước ĐẾM TRƯỚC chứ không chỉ so sau:

    numeric(18,2) giữ hai chữ số thập phân. Giá trị đang có chữ số thứ ba trở đi sẽ bị làm tròn lúc
    đổi kiểu, và ĐÂY LÀ THAY ĐỔI KHÔNG QUAY LẠI ĐƯỢC: downgrade khôi phục KIỂU, không khôi phục SỐ.
    So sau khi đã đổi thì chỉ biết mình vừa mất bao nhiêu, không ngăn được nữa.

    Với đồng Việt Nam, phần lẻ dưới đồng chỉ sinh ra từ phép chia – phân bổ, khấu hao, cấn trừ. Nếu
    kho dữ liệu thật không có dòng nào như vậy thì đổi kiểu là phép biến đổi không mất gì, và bảng
    đếm này nói đúng câu đó bằng số chứ không bằng lời hứa.

Cách dùng trên hệ thống thật:

    python -m app.services.v9_doi_chieu truoc  > /tmp/v9_truoc.json     # TRƯỚC khi nâng cấp
    alembic upgrade head
    python -m app.services.v9_doi_chieu sau /tmp/v9_truoc.json          # so lại, in ra chênh lệch

Bước đầu chỉ ĐỌC, không ghi gì – chạy được cả lúc hệ thống đang phục vụ.
"""
import json
import sys
from decimal import Decimal
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

# Tám cột của đợt 1. Giữ nguyên thứ tự với bản nâng cấp v9a1d6b4f8c02 để hai bên đọc là khớp.
COT_DOT1 = [
    ("journal_lines", "debit"),
    ("journal_lines", "credit"),
    ("invoices", "pre_tax"),
    ("invoices", "vat"),
    ("invoices", "total"),
    ("receipts", "amount"),
    ("bank_transactions", "amount"),
    ("payment_requests", "amount"),
]


def _tong_cot(db: Session, bang: str, cot: str) -> dict:
    """Tổng, số dòng, và số dòng có phần lẻ dưới đồng của một cột.

    Đếm phần lẻ bằng SQL chứ không kéo cả bảng về Python: journal_lines có thể vài trăm nghìn dòng,
    và một bước kiểm tra trước khi nâng cấp mà làm nghẽn máy chủ thì người ta sẽ bỏ qua nó."""
    try:
        tong, so_dong = db.execute(
            select(func.sum(text(cot)), func.count()).select_from(text(bang))).one()
    except Exception as ex:
        return {"loi": f"{type(ex).__name__}: {ex}"[:200]}
    # Dòng có chữ số thập phân thứ ba trở đi: giá trị nhân 100 không phải số nguyên.
    try:
        le = db.execute(text(
            f"SELECT COUNT(*) FROM {bang} WHERE {cot} IS NOT NULL "
            f"AND {cot} * 100 <> ROUND({cot} * 100)")).scalar() or 0
    except Exception:
        le = None                      # không đếm được thì nói KHÔNG BIẾT, không nói 0
    return {"tong": float(tong or 0), "so_dong": int(so_dong or 0), "so_dong_co_le_duoi_dong": le}


def tong_theo_tai_khoan(db: Session) -> dict:
    """Tổng phát sinh Nợ và Có theo TỪNG tài khoản. Đây mới là con số nghiệm thu nói tới.

    Tổng toàn bộ sổ luôn cân (Nợ = Có) nên nó không phát hiện được việc một đồng chạy nhầm từ tài
    khoản này sang tài khoản kia. Tách theo tài khoản thì phát hiện được."""
    ra = {}
    q = text("SELECT account_code, SUM(debit), SUM(credit), COUNT(*) FROM journal_lines "
             "GROUP BY account_code ORDER BY account_code")
    for ma, no, co, n in db.execute(q).all():
        ra[str(ma)] = {"no": float(no or 0), "co": float(co or 0), "so_dong": int(n or 0)}
    return ra


def chup(db: Session) -> dict:
    """Ảnh chụp toàn bộ con số cần đối chiếu. Chỉ đọc."""
    return {
        "cot": {f"{b}.{c}": _tong_cot(db, b, c) for b, c in COT_DOT1},
        "theo_tai_khoan": tong_theo_tai_khoan(db),
    }


def so_sanh(truoc: dict, sau: dict) -> dict:
    """So hai ảnh chụp. Lệch dù một đồng cũng phải hiện ra, kèm tên cột hoặc tên tài khoản."""
    lech_cot, lech_tk = [], []
    for k, a in (truoc.get("cot") or {}).items():
        b = (sau.get("cot") or {}).get(k)
        if b is None:
            lech_cot.append({"cot": k, "van_de": "sau khi nâng cấp không đọc được cột này"}); continue
        if "loi" in a or "loi" in b:
            continue
        d = round(b["tong"] - a["tong"], 2)
        if abs(d) >= 0.005 or a["so_dong"] != b["so_dong"]:
            lech_cot.append({"cot": k, "truoc": a["tong"], "sau": b["tong"], "lech": d,
                             "so_dong_truoc": a["so_dong"], "so_dong_sau": b["so_dong"]})
    ma = set(truoc.get("theo_tai_khoan") or {}) | set(sau.get("theo_tai_khoan") or {})
    for m in sorted(ma):
        a = (truoc.get("theo_tai_khoan") or {}).get(m, {"no": 0, "co": 0, "so_dong": 0})
        b = (sau.get("theo_tai_khoan") or {}).get(m, {"no": 0, "co": 0, "so_dong": 0})
        dn, dc = round(b["no"] - a["no"], 2), round(b["co"] - a["co"], 2)
        if abs(dn) >= 0.005 or abs(dc) >= 0.005 or a["so_dong"] != b["so_dong"]:
            lech_tk.append({"tai_khoan": m, "lech_no": dn, "lech_co": dc,
                            "no_truoc": a["no"], "no_sau": b["no"],
                            "co_truoc": a["co"], "co_sau": b["co"]})
    khop = not lech_cot and not lech_tk
    return {
        "khop": khop, "lech_theo_cot": lech_cot, "lech_theo_tai_khoan": lech_tk,
        "ket_luan": ("Tổng trước và sau khớp tuyệt đối trên cả tám cột và mọi tài khoản."
                     if khop else
                     f"LỆCH: {len(lech_cot)} cột và {len(lech_tk)} tài khoản không khớp. "
                     "Không đóng đợt nâng cấp này cho tới khi giải thích được từng dòng."),
    }


def canh_bao_lam_tron(anh: dict) -> list[str]:
    """Dòng nào sẽ bị làm tròn khi đổi kiểu. Gọi TRƯỚC khi nâng cấp."""
    ra = []
    for k, v in (anh.get("cot") or {}).items():
        n = v.get("so_dong_co_le_duoi_dong")
        if n is None:
            ra.append(f"{k}: KHÔNG ĐẾM ĐƯỢC phần lẻ dưới đồng – kiểm tay trước khi nâng cấp")
        elif n:
            ra.append(f"{k}: {n} dòng có chữ số thập phân thứ ba trở đi, sẽ bị LÀM TRÒN và "
                      "không quay lại được")
    return ra


def _main(argv: list[str]) -> int:
    from app.db.session import SessionLocal
    if len(argv) < 2 or argv[1] not in ("truoc", "sau"):
        print(__doc__); return 2
    with SessionLocal() as db:
        anh = chup(db)
    if argv[1] == "truoc":
        for c in canh_bao_lam_tron(anh):
            print("CẢNH BÁO:", c, file=sys.stderr)
        print(json.dumps(anh, ensure_ascii=False, indent=2))
        return 0
    if len(argv) < 3:
        print("Thiếu đường dẫn tệp ảnh chụp trước khi nâng cấp.", file=sys.stderr); return 2
    with open(argv[2], encoding="utf-8") as f:
        truoc = json.load(f)
    kq = so_sanh(truoc, anh)
    print(json.dumps(kq, ensure_ascii=False, indent=2))
    return 0 if kq["khop"] else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
