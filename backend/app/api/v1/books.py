"""API Sổ kế toán chuẩn: Nhật ký chung, Sổ Cái, Sổ chi tiết TK, Sổ quỹ tiền mặt, Sổ tiền gửi, Sổ công nợ."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.services import books as BK
from app.services import rules as R_

router = APIRouter(prefix="/api/v1/books", tags=["so-ke-toan"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks", "ptgd_doan")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(content: bytes, name: str) -> Response:
    return Response(content=content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _tag(since: date, upto: date) -> str:
    return f"{since:%d%m%y}_{upto:%d%m%y}"


@router.get("")
def catalog(u: User = Depends(require_roles(*READ))):
    """Danh mục sổ kế toán hệ thống xuất được – để dựng menu "Sổ kế toán" giống MISA."""
    return [
        {"key": "nhat-ky-chung", "ten": "Sổ Nhật ký chung", "mau": "S03a-DN", "path": "/api/v1/books/nhat-ky-chung"},
        {"key": "so-cai", "ten": "Sổ Cái tài khoản", "mau": "S03b-DN", "path": "/api/v1/books/so-cai", "tham_so": ["account"]},
        {"key": "so-chi-tiet", "ten": "Sổ chi tiết tài khoản", "mau": "S38-DN", "path": "/api/v1/books/so-chi-tiet", "tham_so": ["account", "partner_code", "project_code"]},
        {"key": "so-quy", "ten": "Sổ quỹ tiền mặt", "mau": "S07-DN", "path": "/api/v1/books/so-quy"},
        {"key": "so-tien-gui", "ten": "Sổ tiền gửi ngân hàng", "mau": "S08-DN", "path": "/api/v1/books/so-tien-gui", "tham_so": ["partner_code"]},
        {"key": "cong-no", "ten": "Sổ chi tiết công nợ theo đối tượng", "mau": "S31-DN / S51-DN", "path": "/api/v1/books/cong-no", "tham_so": ["account", "partner_code"]},
        {"key": "cong-no-tong-hop", "ten": "Sổ tổng hợp công nợ theo đối tượng", "mau": "Tổng hợp", "path": "/api/v1/books/cong-no-tong-hop", "tham_so": ["account"]},
    ]


# ---------- Nhật ký chung ----------

@router.get("/nhat-ky-chung")
def journal(since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return BK.journal_book(db, since, upto)


@router.get("/nhat-ky-chung.xlsx")
def journal_xlsx(since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    rep = BK.journal_book(db, since, upto)
    R_.audit(db, u.username, u.role, "xuat_so_ke_toan", f"nkc:{since}:{upto}", after={"so_dong": len(rep["rows"])}); db.commit()
    return _xlsx(BK.journal_book_xlsx(rep), f"SO_NHAT_KY_CHUNG_{_tag(since, upto)}.xlsx")


# ---------- Sổ Cái / Sổ chi tiết tài khoản ----------

@router.get("/so-cai")
def general_ledger(account: str, since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return BK.account_book(db, account, since, upto)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/so-cai.xlsx")
def general_ledger_xlsx(account: str, since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        rep = BK.account_book(db, account, since, upto)
    except ValueError as ex:
        raise HTTPException(404, str(ex))
    return _xlsx(BK.account_book_xlsx(rep), f"SO_CAI_{account}_{_tag(since, upto)}.xlsx")


@router.get("/so-chi-tiet")
def account_detail(account: str, since: date, upto: date, partner_code: str = "", project_code: str = "",
                   u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return BK.account_book(db, account, since, upto, partner_code, project_code, detail=True)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/so-chi-tiet.xlsx")
def account_detail_xlsx(account: str, since: date, upto: date, partner_code: str = "", project_code: str = "",
                        u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        rep = BK.account_book(db, account, since, upto, partner_code, project_code, detail=True)
    except ValueError as ex:
        raise HTTPException(404, str(ex))
    return _xlsx(BK.account_book_xlsx(rep), f"SO_CHI_TIET_TK_{account}_{_tag(since, upto)}.xlsx")


# ---------- Sổ quỹ tiền mặt / Sổ tiền gửi ----------

@router.get("/so-quy")
def cash_book(since: date, upto: date, account: str = BK.CASH_ACCOUNT,
              u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return BK.cash_book(db, since, upto, account)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/so-quy.xlsx")
def cash_book_xlsx(since: date, upto: date, account: str = BK.CASH_ACCOUNT,
                   u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        rep = BK.cash_book(db, since, upto, account)
    except ValueError as ex:
        raise HTTPException(404, str(ex))
    return _xlsx(BK.cash_book_xlsx(rep), f"SO_QUY_TIEN_MAT_{_tag(since, upto)}.xlsx")


@router.get("/so-tien-gui")
def bank_book(since: date, upto: date, partner_code: str = "", account: str = BK.BANK_ACCOUNT,
              u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return BK.cash_book(db, since, upto, account, partner_code)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/so-tien-gui.xlsx")
def bank_book_xlsx(since: date, upto: date, partner_code: str = "", account: str = BK.BANK_ACCOUNT,
                   u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        rep = BK.cash_book(db, since, upto, account, partner_code)
    except ValueError as ex:
        raise HTTPException(404, str(ex))
    return _xlsx(BK.cash_book_xlsx(rep), f"SO_TIEN_GUI_{partner_code or 'TATCA'}_{_tag(since, upto)}.xlsx")


@router.get("/ngan-hang")
def banks(since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Các ngân hàng có phát sinh trên TK 112 trong kỳ, kèm dư đầu – phát sinh – dư cuối."""
    return {"since": since, "upto": upto, "rows": BK.bank_accounts(db, since, upto)}


# ---------- Sổ công nợ ----------

@router.get("/cong-no")
def partner_ledger(account: str, partner_code: str, since: date, upto: date,
                   u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return BK.partner_ledger(db, account, partner_code, since, upto)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/cong-no.xlsx")
def partner_ledger_xlsx(account: str, partner_code: str, since: date, upto: date,
                        u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        rep = BK.partner_ledger(db, account, partner_code, since, upto)
    except ValueError as ex:
        raise HTTPException(404, str(ex))
    return _xlsx(BK.account_book_xlsx(rep), f"SO_CONG_NO_{account}_{partner_code}_{_tag(since, upto)}.xlsx")


@router.get("/cong-no-tong-hop")
def partner_summary(account: str, since: date, upto: date, min_amount: float = 0,
                    u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return BK.partner_summary(db, account, since, upto, min_amount)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/cong-no-tong-hop.xlsx")
def partner_summary_xlsx(account: str, since: date, upto: date, min_amount: float = 0,
                         u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        rep = BK.partner_summary(db, account, since, upto, min_amount)
    except ValueError as ex:
        raise HTTPException(404, str(ex))
    R_.audit(db, u.username, u.role, "xuat_so_ke_toan", f"congno:{account}", after={"so_doi_tuong": len(rep["rows"])}); db.commit()
    return _xlsx(BK.partner_summary_xlsx(rep), f"TONG_HOP_CONG_NO_{account}_{_tag(since, upto)}.xlsx")
