"""Kết nối API SePay (my.sepay.vn) – chiều kéo (pull), bổ sung cho webhook (push).

- Webhook: SePay đẩy từng giao dịch về POST /api/v1/sepay/webhook (Authorization: Apikey SEPAY_WEBHOOK_KEY).
- API: VTOS chủ động kéo lịch sử giao dịch bằng SEPAY_API_TOKEN (Bearer) – dùng khi mới kết nối (nạp lại lịch sử),
  khi webhook lỗi/mất gói, và để robot đối chiếu định kỳ. Cùng đi qua ingest_sepay → idempotent theo id giao dịch.
Tài liệu SePay: https://docs.sepay.vn (User API: /userapi/transactions/list, /userapi/transactions/count, /userapi/bankaccounts/list).
"""
import json, urllib.request, urllib.parse, urllib.error
from datetime import date
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services import payments as P

BASE = "https://my.sepay.vn/userapi"


class SePayError(Exception):
    pass


def _get(path: str, params: dict | None = None, token: str | None = None) -> dict:
    tok = token or settings.SEPAY_API_TOKEN
    if not tok:
        raise SePayError("Chưa cấu hình SEPAY_API_TOKEN (Render → Environment). Tạo token tại my.sepay.vn → Cấu hình → API Access.")
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "User-Agent": "VTOS/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        raise SePayError(f"SePay trả {e.code}: {body or e.reason}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise SePayError(f"Không gọi được SePay: {e}")
    if data.get("status") not in (200, "200") and not (data.get("messages") or {}).get("success", True):
        raise SePayError(f"SePay báo lỗi: {data.get('error') or data.get('messages')}")
    return data


def bank_accounts(token: str | None = None) -> list[dict]:
    data = _get("/bankaccounts/list", token=token)
    return [{"id": a.get("id"), "bank": a.get("bank_short_name") or a.get("bank_full_name"), "account_number": a.get("account_number"),
             "holder": a.get("account_holder_name"), "active": a.get("active"), "last_transaction": a.get("last_transaction")}
            for a in data.get("bankaccounts", [])]


def list_transactions(from_date: date | None, to_date: date | None, account_number: str = "", limit: int = 5000, token: str | None = None) -> list[dict]:
    params = {"transaction_date_min": f"{from_date} 00:00:00" if from_date else None, "transaction_date_max": f"{to_date} 23:59:59" if to_date else None,
              "account_number": account_number or None, "limit": limit}
    data = _get("/transactions/list", params, token=token)
    return data.get("transactions", [])


def _first(t: dict, *keys) -> str:
    for k in keys:
        v = t.get(k)
        if v is not None and str(v).strip() and str(v).strip().lower() != "null": return str(v).strip()
    return ""


def to_webhook_payload(t: dict) -> dict:
    """Chuẩn hóa bản ghi User API về dạng webhook để dùng chung ingest_sepay."""
    amt_in = float(t.get("amount_in") or 0); amt_out = float(t.get("amount_out") or 0)
    content = _first(t, "transaction_content", "content", "description", "transaction_description", "note", "memo", "remark")
    return {"id": t.get("id"), "gateway": t.get("bank_brand_name") or t.get("bank_short_name") or "", "transactionDate": t.get("transaction_date"),
            "accountNumber": t.get("account_number") or "", "subAccount": t.get("sub_account"), "transferType": "in" if amt_in > 0 else "out",
            "transferAmount": amt_in if amt_in > 0 else amt_out, "accumulated": t.get("accumulated"), "code": t.get("code"),
            "content": content, "referenceCode": _first(t, "reference_number", "reference_code", "ref_no"), "description": content,
            "_source": "sepay_api"}


def pull(db: Session, from_date: date | None, to_date: date | None, account_number: str = "") -> dict:
    rows = list_transactions(from_date, to_date, account_number)
    new = matched = pending = 0
    for t in sorted(rows, key=lambda x: str(x.get("transaction_date") or "")):
        pl = to_webhook_payload(t)
        txn, created = P.ingest_sepay(db, pl)
        if not created and (txn.content or "").strip().lower() in ("", "null") and pl["content"]:
            txn.content, txn.reference_code, txn.raw = pl["content"], pl["referenceCode"], t   # bổ sung nội dung cho bản ghi kéo trước đó
            if txn.transfer_type == "in" and txn.match_status in ("cho_ke_toan", "chua_khop"): P.match_transaction(db, txn)
            db.commit()
        if created:
            new += 1
            if txn.match_status == "da_khop": matched += 1
            elif txn.match_status == "cho_ke_toan": pending += 1
    return {"fetched": len(rows), "new": new, "matched": matched, "pending": pending, "from": str(from_date or ""), "to": str(to_date or "")}


def status(db: Session) -> dict:
    from sqlalchemy import select, func, desc
    from app.models.payments import BankTransaction
    total = db.execute(select(func.count()).select_from(BankTransaction)).scalar() or 0
    last = db.execute(select(BankTransaction).order_by(desc(BankTransaction.transaction_date)).limit(1)).scalars().first()
    out = {"webhook_key_set": bool(settings.SEPAY_WEBHOOK_KEY), "api_token_set": bool(settings.SEPAY_API_TOKEN),
           "webhook_url": "/api/v1/sepay/webhook", "transactions": total,
           "last_transaction": {"date": last.transaction_date, "amount": last.amount, "content": last.content[:80]} if last else None, "accounts": [], "error": ""}
    if settings.SEPAY_API_TOKEN:
        try: out["accounts"] = bank_accounts()
        except SePayError as e: out["error"] = str(e)
    return out
