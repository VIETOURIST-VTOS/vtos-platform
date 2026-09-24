"""Phép nghiệp vụ của sổ KOL / KOC — mục 2.2.2, phần người hợp tác nội dung.

BA ĐIỀU TỆP NÀY GIỮ

1. MỘT KOL LÀ MỘT KÊNH. Cùng một đường dẫn kênh không được khai hai lần — chặn cứng. Cùng TÊN thì
   chỉ cảnh báo, vì hai người thật có thể trùng tên. Hai mức khác nhau cho hai loại trùng khác
   nhau, cùng nếp với nhóm 2.8: trùng số điện thoại là bình thường, trùng dấu vân tay mới là rò.

2. TIỀN Ở ĐÂY LÀ TIỀN GHI CHÉP. `chi_phi` là con số Marketing thoả thuận. Tiền THẬT ra khỏi tài
   khoản đi đường đề nghị chi như mọi khoản khác. Tệp này KHÔNG tự lập đề nghị chi và KHÔNG tự sửa
   một đề nghị đã lập — nó chỉ giữ một đường nối, và in ra phần chênh khi hai số khác nhau.

   Vì sao không tự đồng bộ: thoả thuận 20 triệu mà đề nghị chi 22 triệu là một việc có thật cần
   người giải thích. Một phép tính tự san bằng nó đi là xoá mất câu hỏi.

3. KHÔNG TỰ TÍNH HIỆU QUẢ TỪ SỐ LIỆU NỀN TẢNG. Lượt xem, tương tác, số lead là con số nhân viên đọc
   từ trang quản trị của kênh rồi gõ vào — VTOS không với tới chúng. Rỗng là CHƯA AI GÕ, và bảng
   phải in chữ "chưa có" chứ không in số 0.

MỘT CHỖ CỐ Ý KHÔNG LÀM: không cộng `chi_phi` vào bảng chi phí của nhóm 2.7. Nhóm ấy đọc đề nghị chi
— tiền đã thật sự ra — và đó là một sổ. Cộng thêm sổ thoả thuận vào là dựng sổ tiền thứ hai, đúng
cái bệnh nhóm 2.8 sinh ra để chữa. Chỗ nối là `payment_request_id`: lập phiếu chi cho lần hợp tác,
gắn chiến dịch ở phiếu ấy, thì tiền tự chảy vào bảng 2.7 qua đúng một đường.
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.kol import (HT_LOAI, HT_TRANG_THAI, KOL_KENH, KOL_TRANG_THAI, MktKol,
                            MktKolHopTac)
from app.models.marketing import Campaign
from app.models.ops import PaymentRequest
from app.services import rules as R


def _chuan_ten(s: str) -> str:
    """Bỏ dấu và gom khoảng trắng — chỉ để SO SÁNH cảnh báo trùng tên, không để lưu."""
    import re
    import unicodedata
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", s)).upper().strip()


def ma_moi(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(MktKol)).scalar() or 0
    return f"KOL-{n + 1:04d}"


def _kiem_kol(db: Session, d: dict, tru_id: int | None = None) -> None:
    if not (d.get("ho_ten") or "").strip():
        raise ValueError("Phải có họ tên.")
    if d.get("kenh") not in KOL_KENH:
        raise ValueError(f"Kênh không hợp lệ: {d.get('kenh')}")
    link = (d.get("link_kenh") or "").strip()
    if not link:
        raise ValueError(
            "Phải có đường dẫn kênh. Một KOL trong sổ này là MỘT KÊNH — không có đường dẫn thì "
            "không phân biệt được hai kênh của cùng một người, và cũng không chống trùng được.")
    if d.get("trang_thai") and d["trang_thai"] not in KOL_TRANG_THAI:
        raise ValueError(f"Trạng thái không hợp lệ: {d['trang_thai']}")
    if d.get("trang_thai") == "ngung" and not (d.get("ly_do_ngung") or "").strip():
        raise ValueError(
            "Ngừng hợp tác thì phải ghi lý do. Một người bị loại mà không ai ghi vì sao thì sáu "
            "tháng sau có người lại đề xuất đúng người ấy.")
    q = select(MktKol).where(MktKol.kenh == d["kenh"], MktKol.link_kenh == link)
    if tru_id:
        q = q.where(MktKol.id != tru_id)
    if db.execute(q).scalars().first():
        raise ValueError(f"Kênh này đã có trong sổ: {link}")


def canh_bao_trung_ten(db: Session, ho_ten: str, tru_id: int | None = None) -> list[dict]:
    """CẢNH BÁO, không chặn. Hai người thật có thể trùng tên — xem ghi chú đầu tệp."""
    k = _chuan_ten(ho_ten)
    if not k:
        return []
    ra = []
    for u in db.execute(select(MktKol)).scalars():
        if u.id != tru_id and _chuan_ten(u.ho_ten) == k:
            ra.append({"id": u.id, "ma": u.ma, "ho_ten": u.ho_ten,
                       "kenh": u.kenh, "link_kenh": u.link_kenh})
    return ra


def them(db: Session, boi, d: dict) -> MktKol:
    _kiem_kol(db, d)
    k = MktKol(
        ma=ma_moi(db), ho_ten=d["ho_ten"].strip()[:160],
        biet_danh=(d.get("biet_danh") or "").strip()[:160],
        kenh=d["kenh"], link_kenh=d["link_kenh"].strip()[:400],
        luong_theo_doi=d.get("luong_theo_doi"), theo_doi_do_ngay=d.get("theo_doi_do_ngay"),
        gia_tham_khao=d.get("gia_tham_khao"),
        nguoi_lien_he=(d.get("nguoi_lien_he") or "").strip()[:160],
        dien_thoai=(d.get("dien_thoai") or "").strip()[:30],
        email=(d.get("email") or "").strip()[:120],
        trang_thai=d.get("trang_thai") or "dang_hop_tac",
        ghi_chu=(d.get("ghi_chu") or "").strip(),
        company_id=d.get("company_id"), nguoi_tao=boi.username,
    )
    db.add(k)
    db.flush()
    R.audit(db, boi.username, boi.role, "them_kol", f"kol:{k.ma}",
            after={"ho_ten": k.ho_ten, "kenh": k.kenh, "link": k.link_kenh})
    return k


def sua(db: Session, boi, kol_id: int, d: dict) -> MktKol:
    k = db.get(MktKol, kol_id)
    if k is None:
        raise ValueError(f"Không có KOL id {kol_id}.")
    moi = {**{c: getattr(k, c) for c in
              ("ho_ten", "kenh", "link_kenh", "trang_thai", "ly_do_ngung")}, **d}
    _kiem_kol(db, moi, tru_id=k.id)
    # CHỤP TRẠNG THÁI TRƯỚC KHI SỬA. Gọi sau khi đã gán thì cột "before" của nhật ký ghi lại đúng
    # trạng thái SAU — nhật ký nói dối còn tệ hơn không có. Bài học TC-78, ghi lại để không lặp.
    truoc = {c: getattr(k, c) for c in
             ("ho_ten", "biet_danh", "kenh", "link_kenh", "luong_theo_doi", "gia_tham_khao",
              "nguoi_lien_he", "dien_thoai", "email", "trang_thai", "ly_do_ngung")}
    for c in truoc:
        if c in d:
            setattr(k, c, d[c])
    if "ghi_chu" in d:
        k.ghi_chu = (d["ghi_chu"] or "").strip()
    R.audit(db, boi.username, boi.role, "sua_kol", f"kol:{k.ma}",
            before=truoc, after={c: getattr(k, c) for c in truoc})
    return k


# ────────────────────────────── MỘT LẦN HỢP TÁC ──────────────────────────────

def _kiem_hop_tac(db: Session, d: dict) -> None:
    if not (d.get("noi_dung") or "").strip():
        raise ValueError("Phải ghi nội dung hợp tác.")
    ky = (d.get("ky") or "").strip()
    if len(ky) != 7 or ky[4] != "-" or not (ky[:4].isdigit() and ky[5:].isdigit()):
        raise ValueError(f"Kỳ phải dạng YYYY-MM: {ky!r}")
    if d.get("loai") and d["loai"] not in HT_LOAI:
        raise ValueError(f"Loại nội dung không hợp lệ: {d['loai']}")
    if d.get("trang_thai") and d["trang_thai"] not in HT_TRANG_THAI:
        raise ValueError(f"Trạng thái không hợp lệ: {d['trang_thai']}")
    if d.get("chi_phi") is not None and float(d["chi_phi"]) < 0:
        raise ValueError("Chi phí không âm được.")
    if d.get("campaign_id") and db.get(Campaign, int(d["campaign_id"])) is None:
        raise ValueError(f"Không có chiến dịch id {d['campaign_id']}.")
    if d.get("payment_request_id"):
        pr = db.get(PaymentRequest, int(d["payment_request_id"]))
        if pr is None:
            raise ValueError(f"Không có đề nghị chi id {d['payment_request_id']}.")
        if pr.category != "marketing":
            raise ValueError(
                f"Đề nghị chi {pr.code} không phải khoản marketing (loại {pr.category!r}). "
                "Nối nhầm phiếu thì tiền của tour sẽ bị đếm thành tiền KOL.")
    if d.get("trang_thai") == "huy" and not (d.get("ly_do_huy") or "").strip():
        raise ValueError("Huỷ thì phải ghi lý do.")


def ghi_hop_tac(db: Session, boi, kol_id: int, d: dict) -> MktKolHopTac:
    if db.get(MktKol, kol_id) is None:
        raise ValueError(f"Không có KOL id {kol_id}.")
    _kiem_hop_tac(db, d)
    h = MktKolHopTac(
        kol_id=kol_id, campaign_id=d.get("campaign_id"), ky=d["ky"].strip(),
        loai=d.get("loai") or "bai_dang", noi_dung=d["noi_dung"].strip()[:300],
        link_bai=(d.get("link_bai") or "").strip()[:400], ngay_dang=d.get("ngay_dang"),
        # RỖNG KHÁC KHÔNG: không gõ gì là "chưa thoả thuận giá"; gõ 0 là "không mất tiền".
        chi_phi=(None if d.get("chi_phi") is None else float(d["chi_phi"])),
        payment_request_id=d.get("payment_request_id"),
        trang_thai=d.get("trang_thai") or "du_kien",
        luot_xem=d.get("luot_xem"), luot_tuong_tac=d.get("luot_tuong_tac"),
        so_lead_khai=d.get("so_lead_khai"),
        ghi_chu=(d.get("ghi_chu") or "").strip(), nguoi_tao=boi.username,
    )
    db.add(h)
    db.flush()
    R.audit(db, boi.username, boi.role, "ghi_hop_tac_kol", f"kol_hop_tac:{h.id}",
            after={"kol_id": kol_id, "ky": h.ky, "chi_phi": h.chi_phi,
                   "chien_dich": h.campaign_id})
    return h


def sua_hop_tac(db: Session, boi, ht_id: int, d: dict) -> MktKolHopTac:
    h = db.get(MktKolHopTac, ht_id)
    if h is None:
        raise ValueError(f"Không có dòng hợp tác id {ht_id}.")
    moi = {**{c: getattr(h, c) for c in
              ("ky", "loai", "noi_dung", "chi_phi", "trang_thai", "ly_do_huy",
               "campaign_id", "payment_request_id")}, **d}
    _kiem_hop_tac(db, moi)
    truoc = {c: getattr(h, c) for c in
             ("ky", "loai", "noi_dung", "link_bai", "chi_phi", "trang_thai", "ly_do_huy",
              "campaign_id", "payment_request_id", "luot_xem", "luot_tuong_tac", "so_lead_khai")}
    for c in truoc:
        if c in d:
            setattr(h, c, d[c])
    h.sua_boi, h.sua_luc = boi.username, datetime.now()
    R.audit(db, boi.username, boi.role, "sua_hop_tac_kol", f"kol_hop_tac:{h.id}",
            before=truoc, after={c: getattr(h, c) for c in truoc})
    return h


# ────────────────────────────── BẢNG ĐỌC ──────────────────────────────

def _mot_kol(k: MktKol) -> dict:
    return {"id": k.id, "ma": k.ma, "ho_ten": k.ho_ten, "biet_danh": k.biet_danh,
            "kenh": k.kenh, "kenh_ten": KOL_KENH.get(k.kenh, k.kenh), "link_kenh": k.link_kenh,
            # RỖNG KHÁC KHÔNG. Chưa ai đo lượng theo dõi thì trả None, và màn hình in "chưa đo".
            "luong_theo_doi": k.luong_theo_doi,
            "theo_doi_do_ngay": k.theo_doi_do_ngay.isoformat() if k.theo_doi_do_ngay else "",
            "gia_tham_khao": float(k.gia_tham_khao) if k.gia_tham_khao is not None else None,
            "nguoi_lien_he": k.nguoi_lien_he, "dien_thoai": k.dien_thoai, "email": k.email,
            "trang_thai": k.trang_thai,
            "trang_thai_ten": KOL_TRANG_THAI.get(k.trang_thai, k.trang_thai),
            "ly_do_ngung": k.ly_do_ngung, "ghi_chu": k.ghi_chu}


def danh_sach(db: Session, trang_thai: str = "", kenh: str = "") -> dict:
    """Danh bạ, kèm số lần hợp tác và tổng chi phí thoả thuận của từng người."""
    q = select(MktKol).order_by(MktKol.ho_ten)
    if trang_thai:
        q = q.where(MktKol.trang_thai == trang_thai)
    if kenh:
        q = q.where(MktKol.kenh == kenh)
    ds = list(db.execute(q).scalars())

    dem: dict[int, dict] = {}
    for h in db.execute(select(MktKolHopTac)).scalars():
        d = dem.setdefault(h.kol_id, {"so_lan": 0, "tong_chi_thoa_thuan": 0.0,
                                      "so_lan_chua_co_gia": 0, "da_dang": 0})
        d["so_lan"] += 1
        # HUỶ KHÔNG TÍNH TIỀN. Một lần hợp tác đã huỷ mà vẫn cộng chi phí vào là thổi phồng con số
        # người đọc dùng để quyết định có nên tiếp tục với người này không.
        if h.trang_thai != "huy":
            # Rỗng không cộng vào đâu cả, và đếm riêng để bảng nói được "tổng này còn thiếu mấy
            # dòng chưa có giá" thay vì im lặng trả một con số nhỏ hơn sự thật.
            if h.chi_phi is None:
                d["so_lan_chua_co_gia"] = d.get("so_lan_chua_co_gia", 0) + 1
            else:
                d["tong_chi_thoa_thuan"] += float(h.chi_phi)
        if h.trang_thai == "da_dang":
            d["da_dang"] += 1

    rows = []
    for k in ds:
        rows.append({**_mot_kol(k),
                     **dem.get(k.id, {"so_lan": 0, "tong_chi_thoa_thuan": 0.0,
                                      "so_lan_chua_co_gia": 0, "da_dang": 0})})
    return {"rows": rows, "tong": len(rows), "kenh": KOL_KENH, "trang_thai_ds": KOL_TRANG_THAI}


def chi_tiet(db: Session, kol_id: int) -> dict:
    """Một KOL và toàn bộ lần hợp tác, kèm phần chênh giữa số thoả thuận và số đề nghị chi."""
    k = db.get(MktKol, kol_id)
    if k is None:
        raise ValueError(f"Không có KOL id {kol_id}.")
    cd = {c.id: c for c in db.execute(select(Campaign)).scalars()}
    dong = []
    for h in db.execute(select(MktKolHopTac).where(MktKolHopTac.kol_id == kol_id)
                        .order_by(MktKolHopTac.ky.desc(), MktKolHopTac.id.desc())).scalars():
        pr = db.get(PaymentRequest, h.payment_request_id) if h.payment_request_id else None
        thoa = None if h.chi_phi is None else float(h.chi_phi)
        pr_tien = float(pr.amount) if pr else None
        dong.append({
            "id": h.id, "ky": h.ky, "loai": h.loai, "loai_ten": HT_LOAI.get(h.loai, h.loai),
            "noi_dung": h.noi_dung, "link_bai": h.link_bai,
            "ngay_dang": h.ngay_dang.isoformat() if h.ngay_dang else "",
            "chi_phi_thoa_thuan": thoa,
            "chien_dich_id": h.campaign_id,
            "chien_dich_ma": cd[h.campaign_id].code if h.campaign_id in cd else "",
            "trang_thai": h.trang_thai,
            "trang_thai_ten": HT_TRANG_THAI.get(h.trang_thai, h.trang_thai),
            "ly_do_huy": h.ly_do_huy,
            # RỖNG KHÁC KHÔNG ở cả ba ô đo: chưa ai gõ thì None, và màn hình in "chưa có".
            "luot_xem": h.luot_xem, "luot_tuong_tac": h.luot_tuong_tac,
            "so_lead_khai": h.so_lead_khai,
            # Đường sang tiền THẬT. Rỗng nghĩa là CHƯA LẬP PHIẾU CHI, không phải "miễn phí".
            "phieu_chi_id": h.payment_request_id,
            "phieu_chi_ma": pr.code if pr else "",
            "phieu_chi_trang_thai": pr.status if pr else "",
            "phieu_chi_tien": pr_tien,
            # Hai số cố ý KHÔNG tự đồng bộ — in phần chênh ra cho người giải thích. Thiếu BẤT KỲ
            # vế nào thì không có phần chênh nào để nói: rỗng, không phải 0.
            "lech_tien": ((thoa - pr_tien) if (pr_tien is not None and thoa is not None)
                          else None),
            "ghi_chu": h.ghi_chu,
        })
    con_thieu_phieu = [d for d in dong
                       if d["trang_thai"] != "huy"
                       and (d["chi_phi_thoa_thuan"] or 0) > 0
                       and not d["phieu_chi_id"]]
    return {
        "kol": _mot_kol(k),
        "hop_tac": dong,
        "tong_thoa_thuan": sum(d["chi_phi_thoa_thuan"] or 0
                               for d in dong if d["trang_thai"] != "huy"),
        "so_lan_chua_co_gia": sum(1 for d in dong if d["trang_thai"] != "huy"
                                  and d["chi_phi_thoa_thuan"] is None),
        "so_lan_chua_lap_phieu_chi": len(con_thieu_phieu),
        "ghi_chu": ("Chi phí ở đây là số THOẢ THUẬN, không phải tiền đã ra khỏi tài khoản. Tiền "
                    "thật đi đường đề nghị chi; gắn chiến dịch ở phiếu chi thì nó vào bảng hiệu "
                    "quả chiến dịch của nhóm 2.7. Phần chênh giữa hai số in ở cột riêng và "
                    "KHÔNG được san bằng tự động."),
        "loai": HT_LOAI, "trang_thai_ds": HT_TRANG_THAI,
    }
