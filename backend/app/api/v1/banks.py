"""API Tài khoản ngân hàng: danh mục, mở tiểu khoản 112, gán sổ cũ về đúng ngân hàng, số dư từng ngân hàng."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.models.banks import BankAccount, CURRENCIES
from app.services import banks as BA

router = APIRouter(prefix="/api/v1/bank-accounts", tags=["tai-khoan-ngan-hang"])
# Đọc = đúng ma trận phân quyền màn hình /bank-accounts (FINANCE_ROLES: Chủ tịch, TGĐ, Ban Kiểm soát,
# Kế toán). Trước bản này danh sách ở đây rộng hơn menu – Đợt 3 đã gỡ Phó TGĐ tour đoàn và CNTT khỏi màn
# hình Tài khoản ngân hàng, nhưng API vẫn cho họ đọc, nên ẩn menu chỉ là ẩn khỏi mắt chứ không chặn.
# Robot kiểm thử vai trò (tests/test_robot_vai_tro.py) tìm ra chỗ này. Lấy thẳng từ access.py để không
# còn hai danh sách phải nhớ đồng bộ bằng tay.
from app.services.access import FINANCE_ROLES

READ = FINANCE_ROLES
WRITE = ("ketoan",)      # Chủ tịch vẫn qua được – xem FULL_ACCESS trong app/api/deps.py


def out(b: BankAccount) -> dict:
    return {"id": b.id, "code": b.code, "bank_name": b.bank_name, "account_number": b.account_number,
            "account_name": b.account_name, "branch": b.branch, "currency": b.currency,
            "account_code": b.account_code, "parent_account": b.parent_account,
            "match_prefixes": b.match_prefixes or [], "match_keywords": b.match_keywords or [],
            "sepay_account_number": b.sepay_account_number, "opening_balance": b.opening_balance,
            "active": b.active, "note": b.note, "created_by": b.created_by}


class BankIn(BaseModel):
    code: str
    bank_name: str
    account_number: str = ""
    account_name: str = ""
    branch: str = ""
    currency: str = "VND"
    match_prefixes: list[str] = []
    match_keywords: list[str] = []
    sepay_account_number: str = ""
    opening_balance: float = 0
    note: str = ""


class BankPatch(BaseModel):
    bank_name: str | None = None
    account_number: str | None = None
    account_name: str | None = None
    branch: str | None = None
    match_prefixes: list[str] | None = None
    match_keywords: list[str] | None = None
    sepay_account_number: str | None = None
    active: bool | None = None
    note: str | None = None


@router.get("")
def list_banks(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return {"currencies": CURRENCIES,
            "rows": [out(b) for b in db.execute(select(BankAccount).order_by(BankAccount.code)).scalars()]}


@router.post("", status_code=201)
def add_bank(data: BankIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    try:
        b = BA.create_bank_account(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return out(b)


@router.patch("/{code}")
def edit_bank(code: str, data: BankPatch, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    b = db.execute(select(BankAccount).where(BankAccount.code == code.upper())).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "Không có tài khoản ngân hàng này")
    for k, v in data.model_dump().items():
        if v is None:
            continue
        if k in ("match_prefixes", "match_keywords"):
            v = [str(x).strip().upper() for x in v if str(x).strip()]
        setattr(b, k, v)
    db.commit()
    return out(b)


@router.get("/goi-y")
def suggest(since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Đọc sổ 112 hiện có, thống kê tiền tố số chứng từ và tên ngân hàng để Kế toán biết cần mở tài khoản nào."""
    try:
        return BA.suggest_from_ledger(db, since, upto)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/phan-loai/xem-truoc")
def preview(since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Xem trước việc gán dòng sổ 112 về đúng tiểu khoản ngân hàng – KHÔNG đụng vào sổ."""
    try:
        return BA.classify(db, since, upto, apply=False)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.post("/phan-loai/thuc-hien")
def apply(since: date, upto: date, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Thực hiện gán. Chỉ đổi mã tài khoản trong cây 112; nếu số dư 112 thay đổi thì tự hoàn tác."""
    try:
        return BA.classify(db, since, upto, apply=True, u=u)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.post("/{code}/huy-phan-loai")
def revert(code: str, since: date, upto: date, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Trả các dòng của một ngân hàng về lại tài khoản cha (khi gán nhầm)."""
    try:
        return BA.revert(db, u, code, since, upto)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/so-du")
def balances(since: date, upto: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Số dư đầu – phát sinh – cuối của từng ngân hàng, kèm phần chưa nhận diện được còn ở tài khoản cha."""
    return BA.balances(db, since, upto)


# ---------- Nạp bản đồ chứng từ → ngân hàng từ Sổ tiền gửi của MISA ----------

@router.post("/nap-so-tien-gui")
async def import_bank_book(file: UploadFile = File(...), u: User = Depends(require_roles(*WRITE)),
                           db: Session = Depends(get_db)):
    """Nạp file "Sổ tiền gửi ngân hàng" xuất từ MISA (in theo từng tài khoản ngân hàng).

    Tự mở tài khoản ngân hàng còn thiếu kèm tiểu khoản 112, và dựng bản đồ chứng từ → ngân hàng để bước gán
    không phải đoán theo tiền tố. KHÔNG đụng vào sổ – muốn đổi sổ vẫn phải chạy xem trước rồi mới thực hiện."""
    try:
        return BA.import_bank_book(db, u, await file.read(), file.filename or "")
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/ban-do")
def doc_map_status(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Tình trạng bản đồ chứng từ → ngân hàng hiện có."""
    exact, single = BA.load_doc_map(db)
    from collections import Counter
    by_bank = Counter(v for v in exact.values())
    return {"map_rows": len(exact), "docs_single_bank": len(single),
            "by_bank": [{"code": k, "rows": v} for k, v in by_bank.most_common()]}
