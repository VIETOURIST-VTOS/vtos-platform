"""PL-1 · Phân loại nhà hàng (Chủ tịch duyệt bản xem thử 30/10/2026).

  · «Đặc sản địa phương»: MÁY tự gắn khi nguồn danh sách là TasteAtlas. Đổi tay (gắn / gỡ / về theo máy) đi qua
    đề xuất → chốt; gỡ nhãn phải ghi lý do.
  · Bậc sang trọng (4 bậc): MÁY chỉ GỢI Ý —
      1. thực đơn đang bán có giá → mức chi / người (trung vị giá người lớn): < 250k · 250–600k · 600k–1,5tr · > 1,5tr;
      2. không có thì theo mức giá Michelin Điều hành nhập (₫ … ₫₫₫₫ ↔ 4 bậc);
      3. có sao Michelin mà chưa ghi giá → ít nhất Cao cấp;
      4. không đủ căn cứ → không gợi ý, Điều hành chọn tay.
    NV Điều hành đề xuất → TP Điều hành chốt (người đề xuất không tự chốt). Chủ tịch / TGĐ chốt ngay.
  · Cổng khách chỉ hiện bậc ĐÃ CHỐT; nhà hàng chưa chốt không có nhãn mức, vẫn trong danh sách.
  · Hạng / mức giá Michelin do Điều hành nhập (tay hoặc tệp Excel) — VTOS không tự lấy từ trang Michelin.
Mọi thay đổi ghi nhật ký (rules.audit).
"""
from datetime import date, datetime
from statistics import median
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.nha_hang import NhaHang, ThucDonNhaHang
from app.services.nha_hang import TOAN_QUYEN, LoiNhaHang, _co, _con_ban, _chuan

BAC = {"binh_dan": "Bình dân", "tam_trung": "Tầm trung", "cao_cap": "Cao cấp", "sang_trong": "Sang trọng"}
HANG_MICHELIN = {"sao3": "3 sao", "sao2": "2 sao", "sao1": "1 sao", "bib": "Bib Gourmand", "selected": "Selected",
                 "khong": "Không có"}
NGUONG = (250_000, 600_000, 1_500_000)
GIA_BAC = {1: "binh_dan", 2: "tam_trung", 3: "cao_cap", 4: "sang_trong"}
DAC_SAN_TAY = {"gan": "Gắn tay", "go": "Gỡ tay", "may": "Về theo máy"}
VAI_DE_XUAT = ("nv_dh", "tp_dh") + TOAN_QUYEN
VAI_CHOT = ("tp_dh",) + TOAN_QUYEN


def _audit(db: Session, u: User, viec: str, n: NhaHang, truoc=None, sau=None) -> None:
    from app.services import rules as R
    R.audit(db, u.username, u.role, viec, f"nha_hang:{n.id}", before=truoc, after=sau)


def _nh(db: Session, nid: int) -> NhaHang:
    n = db.get(NhaHang, nid)
    if n is None:
        raise LoiNhaHang("Không có nhà hàng này")
    return n


def la_taste(n: NhaHang) -> bool:
    return "tasteatlas" in (n.nguon or "").lower().replace(" ", "")


def la_michelin(n: NhaHang) -> bool:
    return "michelin" in (n.nguon or "").lower() or (n.michelin_hang or "") in ("sao3", "sao2", "sao1", "bib", "selected")


def dac_san(n: NhaHang) -> bool:
    t = n.dac_san_tay or ""
    return t == "gan" or (t != "go" and la_taste(n))


def nhan_michelin(n: NhaHang) -> str:
    """Nhãn trên thẻ khách: chỉ khi Điều hành đã ghi hạng (không ghi «Không có»)."""
    h = n.michelin_hang or ""
    return f"Michelin {HANG_MICHELIN[h]}" if h in ("sao3", "sao2", "sao1", "bib", "selected") else ""


def muc_chi(tds: list[ThucDonNhaHang], hn: date) -> int | None:
    g = [float(t.gia_nguoi_lon or 0) for t in tds if _con_ban(t, hn) and (t.gia_nguoi_lon or 0) and float(t.gia_nguoi_lon or 0) > 0]
    return int(median(g)) if g else None


def bac_theo_tien(m: int) -> str:
    return "binh_dan" if m < NGUONG[0] else "tam_trung" if m < NGUONG[1] else "cao_cap" if m <= NGUONG[2] else "sang_trong"


def goi_y(n: NhaHang, tds: list[ThucDonNhaHang], hn: date) -> tuple[str, str]:
    m = muc_chi(tds, hn)
    if m:
        return bac_theo_tien(m), f"mức chi {m:,} đ/người (thực đơn đang bán)".replace(",", ".")
    g = int(n.michelin_gia or 0)
    if g in GIA_BAC:
        return GIA_BAC[g], f"Michelin {'₫' * g}"
    if (n.michelin_hang or "") in ("sao3", "sao2", "sao1"):
        return "cao_cap", "có sao Michelin, chưa ghi mức giá"
    return "", "Chưa đủ căn cứ"


def _tds(db: Session, ids: list[int]) -> dict[int, list[ThucDonNhaHang]]:
    ra: dict[int, list] = {}
    if ids:
        for t in db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id.in_(ids))).scalars():
            ra.setdefault(t.nha_hang_id, []).append(t)
    return ra


def _luc(x: datetime | None) -> str | None:
    return x.isoformat(timespec="minutes") if x else None


def mot(n: NhaHang, tds: list[ThucDonNhaHang], hn: date) -> dict:
    gy, ly = goi_y(n, tds, hn)
    return {"id": n.id, "ma": n.ma, "ten": n.ten, "tinh_thanh": n.tinh_thanh, "nguon": n.nguon, "nguon_ref": n.nguon_ref,
            "la_taste": la_taste(n), "la_michelin": la_michelin(n),
            "dac_san": dac_san(n), "dac_san_tay": n.dac_san_tay or "", "dac_san_ly_do": n.dac_san_ly_do or "",
            "dac_san_de_xuat": n.dac_san_de_xuat or "", "dac_san_de_xuat_ly_do": n.dac_san_de_xuat_ly_do or "",
            "dac_san_de_xuat_boi": n.dac_san_de_xuat_boi or "", "dac_san_de_xuat_luc": _luc(n.dac_san_de_xuat_luc),
            "michelin_hang": n.michelin_hang or "", "michelin_gia": int(n.michelin_gia or 0),
            "michelin_boi": n.michelin_boi or "", "michelin_luc": _luc(n.michelin_luc),
            "muc_chi": muc_chi(tds, hn), "goi_y": gy, "goi_y_ly_do": ly,
            "bac": n.bac or "", "bac_chot_boi": n.bac_chot_boi or "", "bac_chot_luc": _luc(n.bac_chot_luc),
            "bac_de_xuat": n.bac_de_xuat or "", "bac_de_xuat_boi": n.bac_de_xuat_boi or "", "bac_de_xuat_luc": _luc(n.bac_de_xuat_luc)}


def _quyen(u: User) -> dict:
    return {"duoc_de_xuat": _co(u, VAI_DE_XUAT), "duoc_chot": _co(u, VAI_CHOT), "toan_quyen": _co(u, TOAN_QUYEN),
            "toi": u.username}


def ds(db: Session, u: User, hn: date | None = None) -> dict:
    hn = hn or date.today()
    nhs = db.execute(select(NhaHang).where(NhaHang.ngung.is_(False)).order_by(NhaHang.ten)).scalars().all()
    tds = _tds(db, [n.id for n in nhs])
    dong = [mot(n, tds.get(n.id, []), hn) for n in nhs]
    dem = {"tong": len(dong), "dac_san": sum(d["dac_san"] for d in dong), "da_chot": sum(bool(d["bac"]) for d in dong),
           "cho_chot": sum(bool(d["bac_de_xuat"] or d["dac_san_de_xuat"]) for d in dong),
           "chua_xep": sum(not d["bac"] for d in dong), "michelin": sum(d["la_michelin"] for d in dong),
           "michelin_chua_ghi": sum(d["la_michelin"] and not d["michelin_hang"] for d in dong)}
    return {"dong": dong, "dem": dem, "bac": BAC, "hang_michelin": HANG_MICHELIN, "nguong": NGUONG, **_quyen(u)}


def chi_tiet(db: Session, u: User, nid: int, hn: date | None = None) -> dict:
    n = _nh(db, nid)
    return {**mot(n, _tds(db, [n.id]).get(n.id, []), hn or date.today()), "bac_ten": BAC, "hang_michelin": HANG_MICHELIN,
            **_quyen(u)}


# ── Michelin: Điều hành ghi hạng / mức giá ─────────────────────────────────────────────────────────────
def _kiem_michelin(hang: str, gia) -> tuple[str, int]:
    hang = (hang or "").strip()
    if hang and hang not in HANG_MICHELIN:
        raise LoiNhaHang("Hạng Michelin không hợp lệ")
    try:
        gia = int(gia or 0)
    except (TypeError, ValueError):
        raise LoiNhaHang("Mức giá Michelin không hợp lệ")
    if gia not in (0, 1, 2, 3, 4):
        raise LoiNhaHang("Mức giá Michelin từ ₫ đến ₫₫₫₫")
    return hang, gia


def ghi_michelin(db: Session, u: User, nid: int, hang: str, gia, now: datetime | None = None, _commit: bool = True) -> NhaHang:
    if not _co(u, VAI_DE_XUAT):
        raise LoiNhaHang("Chỉ Điều hành ghi hạng / mức giá Michelin")
    n = _nh(db, nid)
    hang, gia = _kiem_michelin(hang, gia)
    truoc = {"hang": n.michelin_hang, "gia": n.michelin_gia}
    if truoc == {"hang": hang, "gia": gia}:
        return n
    n.michelin_hang, n.michelin_gia = hang, gia
    n.michelin_boi, n.michelin_luc = u.username, now or datetime.now()
    _audit(db, u, "nha_hang_michelin", n, truoc, {"hang": hang, "gia": gia})
    if _commit:
        db.commit()
    return n


# ── Bậc sang trọng: đề xuất → chốt ───────────────────────────────────────────────────────────────────
def de_xuat_bac(db: Session, u: User, nid: int, bac: str, now: datetime | None = None) -> dict:
    if not _co(u, VAI_DE_XUAT):
        raise LoiNhaHang("Chỉ Điều hành đề xuất bậc")
    if bac not in BAC:
        raise LoiNhaHang("Bậc không hợp lệ")
    n = _nh(db, nid)
    now = now or datetime.now()
    if _co(u, TOAN_QUYEN):
        truoc = n.bac
        n.bac, n.bac_chot_boi, n.bac_chot_luc = bac, u.username, now
        n.bac_de_xuat, n.bac_de_xuat_boi, n.bac_de_xuat_luc = "", "", None
        _audit(db, u, "nha_hang_bac_chot", n, {"bac": truoc}, {"bac": bac, "cach": "chốt ngay"})
        db.commit()
        return {"message": f"{n.ten}: đã chốt bậc «{BAC[bac]}»"}
    if bac == n.bac and not n.bac_de_xuat:
        raise LoiNhaHang(f"Nhà hàng đã ở bậc «{BAC[bac]}»")
    n.bac_de_xuat, n.bac_de_xuat_boi, n.bac_de_xuat_luc = bac, u.username, now
    _audit(db, u, "nha_hang_bac_de_xuat", n, {"bac": n.bac}, {"de_xuat": bac})
    db.commit()
    return {"message": f"{n.ten}: đã đề xuất «{BAC[bac]}» — chờ TP Điều hành chốt"}


def chot_bac(db: Session, u: User, nid: int, dong_y: bool, now: datetime | None = None) -> dict:
    if not _co(u, VAI_CHOT):
        raise LoiNhaHang("Chỉ TP Điều hành, Chủ tịch, TGĐ chốt bậc")
    n = _nh(db, nid)
    if not n.bac_de_xuat:
        raise LoiNhaHang("Nhà hàng này không có đề xuất bậc đang chờ")
    if n.bac_de_xuat_boi == u.username and not _co(u, TOAN_QUYEN):
        raise LoiNhaHang("Người đề xuất không tự chốt — cần TP Điều hành khác hoặc Chủ tịch / TGĐ")
    de, truoc = n.bac_de_xuat, n.bac
    if dong_y:
        n.bac, n.bac_chot_boi, n.bac_chot_luc = de, u.username, now or datetime.now()
    n.bac_de_xuat, n.bac_de_xuat_boi, n.bac_de_xuat_luc = "", "", None
    _audit(db, u, "nha_hang_bac_chot" if dong_y else "nha_hang_bac_tra_lai", n, {"bac": truoc, "de_xuat": de},
           {"bac": n.bac})
    db.commit()
    return {"message": f"{n.ten}: " + (f"đã chốt bậc «{BAC[de]}»" if dong_y else "đã trả lại đề xuất")}


# ── Nhãn «Đặc sản địa phương»: đề xuất → chốt ───────────────────────────────────────────────────────────
def _ap_dac_san(n: NhaHang, tay: str, ly_do: str) -> None:
    n.dac_san_tay = "" if tay == "may" else tay
    n.dac_san_ly_do = "" if tay == "may" else ly_do[:200]


def de_xuat_dac_san(db: Session, u: User, nid: int, tay: str, ly_do: str = "", now: datetime | None = None) -> dict:
    if not _co(u, VAI_DE_XUAT):
        raise LoiNhaHang("Chỉ Điều hành đề xuất gắn / gỡ nhãn")
    if tay not in DAC_SAN_TAY:
        raise LoiNhaHang("Chọn gắn, gỡ, hoặc về theo máy")
    ly_do = (ly_do or "").strip()
    if tay == "go" and len(ly_do) < 5:
        raise LoiNhaHang("Gỡ nhãn «Đặc sản địa phương» phải ghi lý do (ít nhất 5 ký tự)")
    n = _nh(db, nid)
    now = now or datetime.now()
    truoc = {"dac_san": dac_san(n), "tay": n.dac_san_tay}
    if _co(u, TOAN_QUYEN):
        _ap_dac_san(n, tay, ly_do)
        n.dac_san_de_xuat, n.dac_san_de_xuat_ly_do, n.dac_san_de_xuat_boi, n.dac_san_de_xuat_luc = "", "", "", None
        _audit(db, u, "nha_hang_dac_san_chot", n, truoc, {"dac_san": dac_san(n), "tay": n.dac_san_tay, "ly_do": ly_do,
                                                            "cach": "chốt ngay"})
        db.commit()
        return {"message": f"{n.ten}: " + ("đã gắn" if dac_san(n) else "đã bỏ") + " nhãn «Đặc sản địa phương»"}
    n.dac_san_de_xuat, n.dac_san_de_xuat_ly_do = tay, ly_do[:200]
    n.dac_san_de_xuat_boi, n.dac_san_de_xuat_luc = u.username, now
    _audit(db, u, "nha_hang_dac_san_de_xuat", n, truoc, {"de_xuat": tay, "ly_do": ly_do})
    db.commit()
    return {"message": f"{n.ten}: đã đề xuất «{DAC_SAN_TAY[tay]}» — chờ TP Điều hành chốt"}


def chot_dac_san(db: Session, u: User, nid: int, dong_y: bool) -> dict:
    if not _co(u, VAI_CHOT):
        raise LoiNhaHang("Chỉ TP Điều hành, Chủ tịch, TGĐ chốt nhãn")
    n = _nh(db, nid)
    if not n.dac_san_de_xuat:
        raise LoiNhaHang("Nhà hàng này không có đề xuất nhãn đang chờ")
    if n.dac_san_de_xuat_boi == u.username and not _co(u, TOAN_QUYEN):
        raise LoiNhaHang("Người đề xuất không tự chốt — cần TP Điều hành khác hoặc Chủ tịch / TGĐ")
    truoc = {"dac_san": dac_san(n), "tay": n.dac_san_tay, "de_xuat": n.dac_san_de_xuat}
    if dong_y:
        _ap_dac_san(n, n.dac_san_de_xuat, n.dac_san_de_xuat_ly_do)
    n.dac_san_de_xuat, n.dac_san_de_xuat_ly_do, n.dac_san_de_xuat_boi, n.dac_san_de_xuat_luc = "", "", "", None
    _audit(db, u, "nha_hang_dac_san_chot" if dong_y else "nha_hang_dac_san_tra_lai", n, truoc,
           {"dac_san": dac_san(n), "tay": n.dac_san_tay})
    db.commit()
    return {"message": f"{n.ten}: " + (("đã gắn" if dac_san(n) else "đã bỏ") + " nhãn «Đặc sản địa phương»" if dong_y
                                       else "đã trả lại đề xuất")}


# ── Excel: tệp mẫu Michelin + nhập lại ─────────────────────────────────────────────────────────────────
COT_MAU = ["Mã", "Tên nhà hàng", "Thành phố", "Trang Michelin", "Hạng Michelin", "Mức giá Michelin"]


def _link(ref: str) -> str:
    return next((x.strip() for x in (ref or "").split("·") if x.strip().startswith("http")), "")


def mau_xlsx(db: Session) -> bytes:
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.worksheet.datavalidation import DataValidation
    nhs = [n for n in db.execute(select(NhaHang).where(NhaHang.ngung.is_(False)).order_by(NhaHang.ten)).scalars() if la_michelin(n)]
    wb = Workbook(); ws = wb.active; ws.title = "Michelin"
    ws.append(COT_MAU)
    for c in ws[1]:
        c.font = Font(bold=True)
    for n in nhs:
        ws.append([n.ma, n.ten, n.tinh_thanh, _link(n.nguon_ref), HANG_MICHELIN.get(n.michelin_hang or "", ""),
                   "₫" * int(n.michelin_gia or 0)])
    for col, w in zip("ABCDEF", (12, 34, 18, 60, 16, 16)):
        ws.column_dimensions[col].width = w
    if nhs:
        dv1 = DataValidation(type="list", formula1='"' + ",".join(HANG_MICHELIN.values()) + '"', allow_blank=True)
        dv2 = DataValidation(type="list", formula1='"₫,₫₫,₫₫₫,₫₫₫₫"', allow_blank=True)
        ws.add_data_validation(dv1); ws.add_data_validation(dv2)
        dv1.add(f"E2:E{len(nhs) + 1}"); dv2.add(f"F2:F{len(nhs) + 1}")
    hd = wb.create_sheet("Hướng dẫn")
    for r in (["Điền 2 cột «Hạng Michelin» và «Mức giá Michelin» đúng như trang Michelin của nhà hàng."],
              ["Hạng: " + " · ".join(HANG_MICHELIN.values())], ["Mức giá: ₫ · ₫₫ · ₫₫₫ · ₫₫₫₫ (gõ số 1–4 cũng được)"],
              ["Ô để trống: giữ nguyên giá trị đang có. Không sửa cột «Mã»."],
              ["Máy gợi ý bậc: ₫ Bình dân · ₫₫ Tầm trung · ₫₫₫ Cao cấp · ₫₫₫₫ Sang trọng. Bậc vẫn do Điều hành đề xuất, TP Điều hành chốt."]):
        hd.append(r)
    hd.column_dimensions["A"].width = 120
    o = BytesIO(); wb.save(o)
    return o.getvalue()


_HANG_CHU = {"3 sao": "sao3", "3 star": "sao3", "3 stars": "sao3", "three stars": "sao3", "2 sao": "sao2", "2 star": "sao2",
             "2 stars": "sao2", "two stars": "sao2", "1 sao": "sao1", "1 star": "sao1", "one star": "sao1", "bib gourmand": "bib",
             "bib": "bib", "selected": "selected", "michelin selected": "selected", "selected restaurant": "selected",
             "recommended": "selected", "khong co": "khong", "khong": "khong", "none": "khong"}


def _doc_hang(x) -> str | None:
    """None = ô trống (giữ nguyên); "?" = không hiểu."""
    s = _chuan(x)
    if not s:
        return None
    return _HANG_CHU.get(s, "?")


def _doc_gia(x) -> int | None:
    s = str(x if x is not None else "").strip()
    if not s:
        return None
    try:
        g = int(float(s.replace(",", ".")))
    except ValueError:
        g = sum(s.count(c) for c in "₫$€")
    return g if g in (1, 2, 3, 4) else -1


def nhap_xlsx(db: Session, u: User, ten_tep: str, data: bytes, thu: bool = True, now: datetime | None = None) -> dict:
    if not _co(u, VAI_DE_XUAT):
        raise LoiNhaHang("Chỉ Điều hành nhập hạng / mức giá Michelin")
    from app.services.nha_hang import _bang_tep
    if not data:
        raise LoiNhaHang("Tệp rỗng")
    try:
        bang = _bang_tep(ten_tep, data)
    except Exception as ex:
        raise LoiNhaHang(f"Không đọc được tệp: {ex}")
    dau = cot = None
    for i, r in enumerate(bang[:20]):
        nhan = [_chuan(x) for x in r]
        if "ma" in nhan and any(h.startswith("hang") for h in nhan):
            cot = {"ma": nhan.index("ma"), "hang": next(j for j, h in enumerate(nhan) if h.startswith("hang")),
                   "gia": next((j for j, h in enumerate(nhan) if h.startswith("muc gia")), None)}
            dau = i
            break
    if dau is None:
        raise LoiNhaHang("Không thấy dòng tiêu đề có cột «Mã» và «Hạng Michelin» — dùng tệp mẫu của VTOS")
    theo_ma = {n.ma: n for n in db.execute(select(NhaHang)).scalars()}
    doi, loi, giu = [], [], 0
    for so, r in enumerate(bang[dau + 1:], start=dau + 2):
        g = lambda j: r[j] if j is not None and j < len(r) else None   # noqa: E731
        ma = str(g(cot["ma"]) or "").strip()
        if not ma:
            continue
        n = theo_ma.get(ma)
        if n is None:
            loi.append({"dong": so, "ma": ma, "loi": "Không có mã này"}); continue
        h, gia = _doc_hang(g(cot["hang"])), _doc_gia(g(cot["gia"]))
        if h == "?":
            loi.append({"dong": so, "ma": ma, "loi": f"Hạng «{g(cot['hang'])}» không hiểu"}); continue
        if gia == -1:
            loi.append({"dong": so, "ma": ma, "loi": f"Mức giá «{g(cot['gia'])}» không hiểu"}); continue
        moi_h = n.michelin_hang if h is None else h
        moi_g = int(n.michelin_gia or 0) if gia is None else gia
        if (moi_h, moi_g) == (n.michelin_hang or "", int(n.michelin_gia or 0)):
            giu += 1; continue
        doi.append({"id": n.id, "ma": ma, "ten": n.ten, "hang_cu": HANG_MICHELIN.get(n.michelin_hang or "", ""),
                    "gia_cu": int(n.michelin_gia or 0), "hang": HANG_MICHELIN.get(moi_h or "", ""), "gia": moi_g,
                    "_h": moi_h or "", "_g": moi_g})
    if not thu:
        now = now or datetime.now()
        for d in doi:
            ghi_michelin(db, u, d["id"], d["_h"], d["_g"], now, _commit=False)
        db.commit()
    return {"doi": [{k: v for k, v in d.items() if not k.startswith("_")} for d in doi], "loi": loi, "giu_nguyen": giu,
            "da_ghi": not thu}
