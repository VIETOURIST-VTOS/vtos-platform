# -*- coding: utf-8 -*-
"""BỘ SỐ BCTC KIỂM TOÁN — TẢI LÊN, KÝ, DÙNG ĐỂ CHỐT SỔ. Đợt E16, 14/10/2026.

Chủ tịch chốt 14/10/2026, ba câu hỏi ba câu trả lời:

  1. VTOS XUẤT MẪU EXCEL, Kế toán điền rồi tải lên — không gõ tay 45 dòng trên màn hình, và không
     để máy tự suy từ MISA.
  2. GỠ BỘ SỐ KHỎI KHO MÃ, bắt tải lên mới chạy được. Bút toán đã ghi trước đây không đụng tới.
  3. KẾ TOÁN TRÌNH, CHỦ TỊCH KÝ — hai chữ ký, cùng hình dáng với Đợt E6.

VÌ SAO PHÉP KIỂM Ở ĐÂY NẶNG HƠN MỌI BỘ NẠP KHÁC

Mọi bộ nạp khác nạp SỐ PHÁT SINH: sai một dòng thì sổ lệch một dòng, và đối chiếu sẽ tìm ra. Bộ số
này là ĐÁP ÁN — `misa.import_audited_checkpoint` lấy nó làm chuẩn rồi kéo toàn bộ sổ về bằng chênh
lệch. Một con số sai ở đây không lệch một dòng; nó viết lại cả bảng cân đối.

Nên bốn phép kiểm chạy TRƯỚC khi ghi một dòng nào, và sai một phép là trả cả tệp:

  K1. Mỗi dòng đối tượng phải thuộc một tài khoản CÓ MẶT trong tệp. Dòng đối tượng mồ côi là
      dòng sẽ không ai cộng vào đâu cả.
  K2. Tổng dư Nợ = tổng dư Có trên các dòng TÀI KHOẢN, cho CẢ hai cột đầu kỳ và cuối kỳ. Một bộ số
      không cân thì bút toán điều chỉnh sinh ra từ nó cũng không cân, và `post_entry` sẽ ném ra một
      câu nói về bút toán — người đọc đi sửa nhầm chỗ.
  K3. Các dòng đối tượng của một tài khoản cộng lại = dòng tài khoản ấy. Mã cũ TIN điều này mà
      không kiểm (xem chú thích "target được tính sẵn bằng tổng các đối tượng" trong misa.py); tin
      mà không kiểm thì lệch chui vào qua đúng chỗ ấy.
  K4. Mã tài khoản không trùng, (tài khoản, mã đối tượng) không trùng, ô tiền phải là SỐ.

MỘT CHỖ CỐ Ý KHÔNG CHẶN: tệp có tài khoản mà sổ VTOS chưa có. `import_audited_checkpoint` tự mở
tài khoản ấy — đó là hành vi sẵn có và đúng, vì kiểm toán phân loại ra tài khoản mà MISA chưa dùng
là chuyện thường. Chặn ở đây là bắt Kế toán đi mở tay 30 tài khoản trước khi tải được một tệp.
"""
from __future__ import annotations

import io
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bo_so_kiem_toan import BoSoKiemToan, DongBoSoKiemToan, TRANG_THAI_BO_SO
from app.models.core import ROLES, User
from app.models.kiem_toan import KT_LOAI
from app.services import chu_ky as _CK
from app.services import pham_vi_phap_nhan as PV
from app.services import rules as R
from app.services import so_lo_nap as SLN

LOAI_CHU_KY = "bo_so_kiem_toan"
SAI_SO = 1.0          # dưới một đồng là chuyện làm tròn, không phải chuyện lệch số

# Cột của mẫu Excel. Khai MỘT chỗ: bộ xuất mẫu và bộ đọc tệp đọc chung bảng này, nên không có
# đường nào để mẫu xuất ra một đằng và bộ đọc chờ một nẻo.
COT = (
    ("code",          "Tài khoản (*)"),
    ("name",          "Tên tài khoản"),
    ("ma_doi_tuong",  "Mã đối tượng"),
    ("ten_doi_tuong", "Tên đối tượng"),
    ("open_d",        "Dư Nợ đầu kỳ"),
    ("open_c",        "Dư Có đầu kỳ"),
    ("close_d",       "Dư Nợ cuối kỳ"),
    ("close_c",       "Dư Có cuối kỳ"),
)
COT_TIEN = ("open_d", "open_c", "close_d", "close_c")


class SaiBoSo(ValueError):
    """Không nhận được bộ số, kèm câu nói ra vì sao."""


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 1. MẪU EXCEL
# ──────────────────────────────────────────────────────────────────────────────────────────────
def mau_excel() -> bytes:
    """Mẫu TRỐNG — tiêu đề, lời dẫn, và KHÔNG một con số nào.

    Mẫu có sẵn số là mẫu người ta sẽ sửa vài ô rồi tải lên, và phần không sửa là số của robot đi
    thẳng vào bảng cân đối dưới chữ ký của người khác.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Bo so kiem toan"
    for dong in (
        ["BỘ SỐ BCTC ĐÃ KIỂM TOÁN / SOÁT XÉT — mẫu nạp vào VTOS"],
        ["Mỗi tài khoản MỘT dòng, mã đối tượng để TRỐNG. Tài khoản xét theo đối tượng (131, 331…)"],
        ["ghi thêm các dòng ĐỐI TƯỢNG ngay dưới, cùng mã tài khoản, có mã đối tượng."],
        ["Máy kiểm trước khi nhận: tổng Nợ = tổng Có (cả hai cột), và các dòng đối tượng của một"],
        ["tài khoản cộng lại phải bằng đúng dòng tài khoản ấy. Đơn vị: đồng."],
        [],
    ):
        ws.append(dong)
    ws.append([nhan for _, nhan in COT])
    for i, _ in enumerate(COT, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = 18 if i > 4 else 26
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 2. ĐỌC TỆP
# ──────────────────────────────────────────────────────────────────────────────────────────────
def _so(x, o: str, dong: int) -> float:
    """Ô tiền → số. RỖNG là 0 Ở ĐÂY và chỉ ở đây: một ô bỏ trống trong bảng số dư nghĩa là tài
    khoản không có dư bên ấy, đó là cách người ta điền bảng cân đối. Nhưng một ô có CHỮ thì ném —
    `float("1.234.567")` hỏng, còn `int("")` thì im lặng, và im lặng ở bảng này là mất tiền."""
    if x is None or (isinstance(x, str) and not x.strip()):
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    else:
        s = s.replace(".", "") if s.count(".") > 1 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        raise SaiBoSo(f"Dòng {dong}, cột “{o}”: “{x}” không phải một con số.")


def doc_excel(data: bytes) -> list[dict]:
    """Tệp → danh sách dòng đã kiểm. Ném `SaiBoSo` ở lỗi ĐẦU TIÊN, kèm số dòng trong tệp."""
    try:
        ws = load_workbook(io.BytesIO(data), read_only=True, data_only=True).worksheets[0]
    except Exception as ex:
        raise SaiBoSo(f"Không mở được tệp Excel: {ex}")

    hang = list(ws.iter_rows(values_only=True))
    vt = None
    for i, r in enumerate(hang):
        o = [str(c or "").strip().lower() for c in r]
        if any(c.startswith("tài khoản") for c in o) and any(c.startswith("dư nợ cuối") for c in o):
            vt = i
            cot = {}
            for ten, nhan in COT:
                nl = nhan.replace(" (*)", "").lower()
                cot[ten] = next((j for j, c in enumerate(o) if c.startswith(nl)), None)
            break
    if vt is None:
        raise SaiBoSo("Không tìm thấy dòng tiêu đề. Dùng đúng mẫu tải từ nút “Tải mẫu Excel” — "
                      "dòng tiêu đề phải có “Tài khoản (*)” và “Dư Nợ cuối kỳ”.")
    thieu = [n for t, n in COT if cot[t] is None]
    if thieu:
        raise SaiBoSo(f"Tệp thiếu cột: {', '.join(thieu)}.")

    dong, da_co = [], set()
    for i, r in enumerate(hang[vt + 1:], start=vt + 2):
        lay = lambda t: r[cot[t]] if cot[t] < len(r) else None          # noqa: E731
        code = str(lay("code") or "").strip()
        if not code:
            continue
        if not code.isdigit():
            raise SaiBoSo(f"Dòng {i}: “{code}” không phải số hiệu tài khoản (chỉ gồm chữ số).")
        ma = str(lay("ma_doi_tuong") or "").strip()
        if (code, ma) in da_co:
            raise SaiBoSo(f"Dòng {i}: tài khoản {code}"
                          + (f" đối tượng {ma}" if ma else "") + " đã có ở một dòng trên.")
        da_co.add((code, ma))
        d = {"code": code, "name": str(lay("name") or "").strip()[:200],
             "ma_doi_tuong": ma[:50], "ten_doi_tuong": str(lay("ten_doi_tuong") or "").strip()[:200]}
        for t in COT_TIEN:
            d[t] = _so(lay(t), dict(COT)[t], i)
        dong.append(d)
    if not dong:
        raise SaiBoSo("Tệp không có dòng số liệu nào.")
    kiem(dong)
    return dong


def kiem(dong: list[dict]) -> None:
    """Bốn phép kiểm K1–K4 (K4 đã làm lúc đọc từng dòng). Ném ở lỗi đầu tiên."""
    tk = {d["code"] for d in dong if not d["ma_doi_tuong"]}
    mo_coi = sorted({d["code"] for d in dong if d["ma_doi_tuong"] and d["code"] not in tk})
    if mo_coi:
        raise SaiBoSo(
            f"K1 — có dòng đối tượng của tài khoản {', '.join(mo_coi)} mà tệp KHÔNG có dòng tổng "
            f"của chính tài khoản ấy. Mỗi tài khoản phải có một dòng để trống mã đối tượng; dòng "
            f"đối tượng mồ côi là dòng không ai cộng vào đâu cả.")

    for nhan, cd, cc in (("đầu kỳ", "open_d", "open_c"), ("cuối kỳ", "close_d", "close_c")):
        no = sum(d[cd] for d in dong if not d["ma_doi_tuong"])
        co = sum(d[cc] for d in dong if not d["ma_doi_tuong"])
        if abs(no - co) >= SAI_SO:
            raise SaiBoSo(
                f"K2 — bộ số KHÔNG CÂN ở cột {nhan}: tổng dư Nợ {no:,.0f} ≠ tổng dư Có {co:,.0f} "
                f"(lệch {no - co:,.0f}). Tài sản phải bằng Nguồn vốn. Bộ số này là ĐÁP ÁN để kéo "
                f"cả sổ về, nên nhận một bộ số không cân là viết một bảng cân đối không cân.")

    theo_tk: dict[str, dict] = {d["code"]: d for d in dong if not d["ma_doi_tuong"]}
    cong: dict[str, dict] = {}
    for d in dong:
        if d["ma_doi_tuong"]:
            g = cong.setdefault(d["code"], {t: 0.0 for t in COT_TIEN})
            for t in COT_TIEN:
                g[t] += d[t]
    for code, g in sorted(cong.items()):
        t = theo_tk[code]
        for nhan, cd, cc in (("đầu kỳ", "open_d", "open_c"), ("cuối kỳ", "close_d", "close_c")):
            rong_tk, rong_dt = t[cd] - t[cc], g[cd] - g[cc]
            if abs(rong_tk - rong_dt) >= SAI_SO:
                raise SaiBoSo(
                    f"K3 — tài khoản {code} cột {nhan}: các dòng đối tượng cộng lại ròng "
                    f"{rong_dt:,.0f} ≠ dòng tài khoản {rong_tk:,.0f} (lệch {rong_tk - rong_dt:,.0f}). "
                    f"Bộ nạp ghi sổ THEO TỪNG ĐỐI TƯỢNG cho các tài khoản này, nên dòng tổng và "
                    f"các dòng chi tiết lệch nhau là hai con số cùng tên nói hai điều khác nhau.")


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 3. TẢI LÊN · KÝ · TỪ CHỐI
# ──────────────────────────────────────────────────────────────────────────────────────────────
def tai_len(db: Session, u: User, data: bytes, ten_tep: str, as_of: date, ky: str,
            don_vi_kiem_toan: str, so_bao_cao: str, ngay_bao_cao: date | None,
            loai_bao_cao: str = "soat_xet", company_id: int | None = None,
            ghi_chu: str = "") -> BoSoKiemToan:
    """Kế toán tải một bản lên. KHÔNG chốt sổ gì cả — chỉ lập hồ sơ, chờ Chủ tịch ký."""
    thieu = [n for n, v in (("đơn vị kiểm toán", don_vi_kiem_toan), ("số báo cáo", so_bao_cao),
                            ("ngày báo cáo", ngay_bao_cao)) if not v]
    if thieu:
        raise SaiBoSo(
            f"Phải khai {', '.join(thieu)}. Ba ô này là thứ phân biệt một bộ số đã kiểm toán với "
            f"một bảng Excel bất kỳ — thiếu chúng thì sáu tháng sau không ai đối chiếu lại được "
            f"bộ số này với bản báo cáo nào.")
    if not as_of:
        raise SaiBoSo("Phải ghi ngày số liệu (ngày kết thúc kỳ của bộ số).")
    if loai_bao_cao not in KT_LOAI:
        raise SaiBoSo(f"Loại báo cáo “{loai_bao_cao}” không có trong danh mục: {', '.join(KT_LOAI)}.")

    # NGƯỜI TRÌNH KHÔNG TỰ KÝ. Cùng một phép chặn, cùng một câu, với `mo_lai_ky.de_nghi` (Đợt E6):
    # Chủ tịch là người ký duy nhất nên ông tự tải lên là một hồ sơ KHÔNG AI KÝ ĐƯỢC.
    can = _CK.can_ky(LOAI_CHU_KY)
    if u.role in can and len(can) == 1:
        raise SaiBoSo(
            f"{ROLES.get(u.role, u.role)} là người ký DUY NHẤT của bộ số kiểm toán, nên không tự "
            f"tải lên bộ số mình sẽ ký — chữ ký ấy khi đó không còn là một lớp kiểm soát. Nhờ Kế "
            f"toán tải lên, rồi ký.")

    dong = doc_excel(data)
    b = BoSoKiemToan(
        company_id=company_id, as_of=as_of, ky=(ky or "")[:20],
        don_vi_kiem_toan=don_vi_kiem_toan[:160], so_bao_cao=so_bao_cao[:80],
        ngay_bao_cao=ngay_bao_cao, loai_bao_cao=loai_bao_cao, ghi_chu=ghi_chu or "",
        trang_thai="cho_ky", ten_tep=(ten_tep or "")[:200],
        tai_len_boi=u.username, tai_len_vai=u.role, tai_len_luc=datetime.now())
    b.dong = [DongBoSoKiemToan(**d) for d in dong]
    db.add(b)
    db.flush()
    tong = sum(d["close_d"] for d in dong if not d["ma_doi_tuong"])
    # Ghi nhật ký lô: đây là một cửa nạp hàng loạt thật, và `ks_nap_lo.CUA_NAP` khai nó là CÓ ghi.
    SLN.ghi_lo(db, loai="bo_so_kiem_toan", so_dong=len(dong), da_nap=len(dong),
               tong_tien_tep=tong, tong_tien_da_nap=tong, tong_tien_bo_qua=0, tong_tien_loi=0,
               cot_tien=["dư nợ cuối kỳ"], boi=u.username, nguon="nap_tep", dau_vao=ten_tep,
               ket_qua={"bo_so_id": b.id, "as_of": str(as_of), "so_tai_khoan": len(
                   [d for d in dong if not d["ma_doi_tuong"]])})
    R.audit(db, u.username, u.role, "tai_len_bo_so_kiem_toan", f"bo_so_kiem_toan:{b.id}",
            after={"as_of": str(as_of), "nguon": nguon(b), "so_dong": len(dong)})
    db.commit()
    return b


def ky(db: Session, u: User, b: BoSoKiemToan) -> dict:
    """Chủ tịch ký. Bộ số thành DÙNG ĐƯỢC để chốt sổ — nhưng KHÔNG chốt sổ ở đây."""
    if b.trang_thai != "cho_ky":
        raise SaiBoSo(f"Bản này không còn chờ ký (trạng thái {b.trang_thai}).")
    can = _CK.can_ky(LOAI_CHU_KY)
    if u.role not in can:
        raise SaiBoSo("Chỉ " + " và ".join(ROLES.get(v, v) for v in can) + " ký bộ số kiểm toán được.")
    if u.username == b.tai_len_boi:
        raise SaiBoSo("Người tải lên không tự ký. Việc trình và việc ký phải là hai người, "
                      "bất kể hai người ấy to đến đâu.")

    cu = ban_da_ky(db, b.as_of, b.company_id)
    if cu:
        cu.trang_thai = "da_thay_the"
        b.thay_the_id = cu.id
    b.ky_boi, b.ky_vai, b.ky_luc, b.trang_thai = u.username, u.role, datetime.now(), "da_ky"
    R.audit(db, u.username, u.role, "ky_bo_so_kiem_toan", f"bo_so_kiem_toan:{b.id}",
            before={"thay_the": cu.id if cu else None}, after={"nguon": nguon(b)})
    db.commit()
    return {"message": f"Đã ký bộ số {b.as_of:%d/%m/%Y}. Chốt sổ là việc riêng — bấm “Chốt sổ "
                       f"theo BCTC kiểm toán” khi muốn kéo sổ về đúng bộ số này."
                       + (f" Bản ký trước (#{cu.id}) chuyển sang “đã bị thay thế”." if cu else "")}


def tu_choi(db: Session, u: User, b: BoSoKiemToan, ly_do: str) -> dict:
    if b.trang_thai != "cho_ky":
        raise SaiBoSo(f"Bản này không còn chờ ký (trạng thái {b.trang_thai}).")
    if u.role not in _CK.can_ky(LOAI_CHU_KY):
        raise SaiBoSo("Chỉ người ký của bộ số kiểm toán mới từ chối được.")
    if not (ly_do or "").strip():
        raise SaiBoSo("Phải ghi lý do từ chối — người tải lên cần biết sửa gì để tải lại.")
    b.trang_thai, b.ky_boi, b.ky_vai, b.ky_luc = "tu_choi", u.username, u.role, datetime.now()
    b.tu_choi_ly_do = ly_do.strip()[:500]
    R.audit(db, u.username, u.role, "tu_choi_bo_so_kiem_toan", f"bo_so_kiem_toan:{b.id}",
            after={"ly_do": b.tu_choi_ly_do})
    db.commit()
    return {"message": f"Đã từ chối bộ số {b.as_of:%d/%m/%Y}."}


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 4. ĐỌC RA
# ──────────────────────────────────────────────────────────────────────────────────────────────
def ban_da_ky(db: Session, as_of: date | None = None,
              company_id: int | None = None) -> BoSoKiemToan | None:
    """Bản ĐÃ KÝ còn hiệu lực. `as_of` rỗng thì lấy bản có ngày số liệu MỚI NHẤT.

    Trả `None` khi chưa có bản nào — RỖNG, không phải một bộ số trống. Nơi gọi phải nói ra điều ấy
    thành một câu người đọc được, chứ không chốt sổ bằng một bộ số không có dòng nào.
    """
    q = select(BoSoKiemToan).where(BoSoKiemToan.trang_thai == "da_ky")
    if as_of:
        q = q.where(BoSoKiemToan.as_of == as_of)
    if company_id is not None:
        q = q.where(BoSoKiemToan.company_id == company_id)
    return db.execute(q.order_by(BoSoKiemToan.as_of.desc(), BoSoKiemToan.id.desc())).scalars().first()


def ban_de_chot(db: Session, bo_id: int | None = None) -> BoSoKiemToan:
    """Bộ số dùng để chốt sổ, hoặc NÉM một câu nói rõ phải làm gì."""
    b = db.get(BoSoKiemToan, bo_id) if bo_id else ban_da_ky(db)
    if not b:
        raise SaiBoSo(
            "Chưa có bộ số BCTC kiểm toán nào ĐÃ KÝ. Trước đây ba mươi con số ấy nằm trong kho mã "
            "do robot gõ; từ 14/10/2026 chúng phải do Kế toán tải lên và Chủ tịch ký. Vào màn hình "
            "Kế toán → “Nạp từ MISA” → khung 7, tải mẫu Excel, điền theo bản BCTC đã ký rồi tải lên.")
    if b.trang_thai != "da_ky":
        raise SaiBoSo(f"Bộ số #{b.id} đang ở trạng thái “{b.trang_thai}”, chưa ký thì chưa chốt sổ "
                      f"theo nó được.")
    if not b.dong:
        raise SaiBoSo(f"Bộ số #{b.id} không có dòng nào.")
    return b


def nguon(b: BoSoKiemToan) -> str:
    """Câu MỘT DÒNG ghi vào diễn giải mọi bút toán sinh ra từ bộ số này.

    Dựng TỪ các ô khai nguồn chứ không để ai gõ tay một câu: câu gõ tay thì mỗi kỳ một kiểu, và ba
    tháng sau không lọc được bút toán nào thuộc bản báo cáo nào.
    """
    p = [KT_LOAI.get(b.loai_bao_cao, b.loai_bao_cao)]
    if b.ky:
        p.append(b.ky)
    p.append(b.don_vi_kiem_toan)
    p.append(f"số {b.so_bao_cao}")
    if b.ngay_bao_cao:
        p.append(f"ngày {b.ngay_bao_cao:%d/%m/%Y}")
    return " – ".join(x for x in p if x)


def du_lieu(b: BoSoKiemToan) -> dict:
    """Bộ số → ĐÚNG hình dáng mà `misa.import_audited_checkpoint` vẫn đọc từ tệp JSON cũ.

    Giữ nguyên hình dáng là có chủ ý: phần tính toán của bộ chốt sổ không đổi một dòng nào trong
    đợt này, nên nếu con số sau đợt này khác trước thì nguyên nhân nằm ở BỘ SỐ, không nằm ở phép
    tính — và đó là điều đáng tin cậy nhất mà một đợt đổi nguồn dữ liệu có thể giữ.
    """
    tk = []
    doi_tuong: dict[str, list] = {}
    for d in b.dong:
        if d.ma_doi_tuong:
            doi_tuong.setdefault(d.code, []).append(
                {"ma": d.ma_doi_tuong, "ten": d.ten_doi_tuong, "close_d": float(d.close_d),
                 "close_c": float(d.close_c), "open_d": float(d.open_d), "open_c": float(d.open_c)})
    for d in b.dong:
        if d.ma_doi_tuong:
            continue
        a = {"code": d.code, "name": d.name, "close_d": float(d.close_d),
             "close_c": float(d.close_c), "open_d": float(d.open_d), "open_c": float(d.open_c)}
        if d.code in doi_tuong:
            a["doi_tuong"] = doi_tuong[d.code]
        tk.append(a)
    return {"nguon": nguon(b), "as_of": b.as_of, "tai_khoan": tk}


def mot_dong(b: BoSoKiemToan, day_du: bool = False) -> dict:
    """Một dòng cho màn hình. Gửi cả tên vai đọc được, không bắt màn hình tự dịch mã vai."""
    tk = [d for d in b.dong if not d.ma_doi_tuong]
    r = {"id": b.id, "company_id": b.company_id, "as_of": b.as_of, "ky": b.ky,
         "loai_bao_cao": b.loai_bao_cao, "loai_ten": KT_LOAI.get(b.loai_bao_cao, b.loai_bao_cao),
         "don_vi_kiem_toan": b.don_vi_kiem_toan, "so_bao_cao": b.so_bao_cao,
         "ngay_bao_cao": b.ngay_bao_cao, "nguon": nguon(b), "ghi_chu": b.ghi_chu,
         "trang_thai": b.trang_thai, "trang_thai_ten": TRANG_THAI_BO_SO.get(b.trang_thai, b.trang_thai),
         "so_tai_khoan": len(tk), "so_doi_tuong": len(b.dong) - len(tk),
         "ten_tep": b.ten_tep, "tai_len_boi": b.tai_len_boi,
         "tai_len_vai": ROLES.get(b.tai_len_vai, b.tai_len_vai), "tai_len_luc": b.tai_len_luc,
         "ky_boi": b.ky_boi, "ky_vai": ROLES.get(b.ky_vai, b.ky_vai), "ky_luc": b.ky_luc,
         "tu_choi_ly_do": b.tu_choi_ly_do, "thay_the_id": b.thay_the_id}
    if day_du:
        r["dong"] = [{"code": d.code, "name": d.name, "ma_doi_tuong": d.ma_doi_tuong,
                      "ten_doi_tuong": d.ten_doi_tuong, "open_d": float(d.open_d),
                      "open_c": float(d.open_c), "close_d": float(d.close_d),
                      "close_c": float(d.close_c)} for d in b.dong]
    return r


def danh_sach(db: Session, u: User, company_id: int | None = None) -> list[dict]:
    """Danh sách các bản, ĐÃ CẮT theo phạm vi pháp nhân của người xem.

    Cắt ở TRUY VẤN chứ không ở màn hình: một hàng rào chỉ đứng trên giao diện thì mọi cửa khác đi
    vòng qua được. Bộ số của Vietrip lọt sang người phụ trách công ty mẹ là số của hai pháp nhân
    nằm chung một bảng — đúng điều `PHAI_LOC` sinh ra để chặn.
    """
    q = select(BoSoKiemToan)
    if company_id is not None:
        q = q.where(BoSoKiemToan.company_id == company_id)
    q = PV.loc(q, BoSoKiemToan, u)
    return [mot_dong(b) for b in
            db.execute(q.order_by(BoSoKiemToan.as_of.desc(), BoSoKiemToan.id.desc())).scalars()]
