"""Hồ sơ kiểm toán – luật nghiệp vụ (V7 Đợt 3, 10/9/2026).

Bốn chốt chặn:

1. Một pháp nhân, một kỳ, một loại thì chỉ MỘT hồ sơ. Khoá duy nhất nằm ở lược đồ, và ở đây báo lỗi
   bằng tiếng người thay vì để lỗi ràng buộc của cơ sở dữ liệu văng ra màn hình.
2. Không phát hành được khi còn mục chưa gửi. Phát hành là lúc nói "đã cung cấp đủ" – còn mục chưa gửi
   mà vẫn đóng thì hồ sơ kiểm toán năm sau bắt đầu bằng một câu hỏi không ai trả lời được.
3. Ý kiến kiểm toán chỉ điền được ở bước phát hành, và ý kiến KHÔNG phải chấp nhận toàn phần thì bắt
   buộc ghi cơ sở của ý kiến ấy. Vietourist là công ty đại chúng – ngoại trừ mà không nói ngoại trừ cái
   gì là một thông tin công bố thiếu.
4. Bút toán điều chỉnh: "đã ghi sổ" thì phải có SỐ HIỆU bút toán thật; "không đồng ý" thì phải có lý do
   và tên người quyết. Không có ô số tiền – xem ghi chú đầu app/models/kiem_toan.py.

Danh mục tài liệu mẫu (MAU_DANH_MUC) là ĐIỂM KHỞI ĐẦU, không phải danh sách đóng. Kiểm toán viên mỗi kỳ
hỏi thêm những thứ khác nhau, nên mục thêm tay là chuyện bình thường và không bị chặn.
"""
from datetime import datetime, date
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models.core import User, Company
from app.models.accounting import JournalEntry
from app.models.attachments import Attachment, NHOM_HO_SO
from app.models.kiem_toan import (HoSoKiemToan, HoSoKiemToanMuc, HoSoKiemToanDieuChinh, KT_LOAI,
                                  KT_TRANG_THAI, KT_CHUYEN, KT_Y_KIEN, MUC_TRANG_THAI, DC_TRANG_THAI)
from app.services import rules as R

# Kế toán làm chủ hồ sơ. Ban Kiểm soát đọc theo nghĩa vụ Luật Doanh nghiệp (và bị chặn ghi ở lớp
# chung). CNTT có mặt vì phần lớn mục tài liệu ngày nay là bản kết xuất từ hệ thống.
GHI = ("ketoan", "tgd", "chutich", "cntt")
# Cập nhật MỘT MỤC thì rộng hơn: mục hợp đồng lao động do HCNS gửi, mục hồ sơ xe do đội xe gửi. Bắt mọi
# thứ đi qua Kế toán là biến Kế toán thành người đưa thư, và mục nào chậm cũng thành lỗi Kế toán.
GHI_MUC = GHI + ("hcns", "tp_dh", "gd_doi_xe", "ptgd_doan", "hanh_chinh")

# Danh mục mẫu: (tên, nhóm hồ sơ, phòng ban chịu trách nhiệm).
MAU_DANH_MUC = (
    ("Báo cáo tài chính kỳ trước đã kiểm toán / soát xét", "08_Kiem_toan", "ketoan"),
    ("Bảng cân đối số phát sinh toàn kỳ", "02_Ke_toan", "ketoan"),
    ("Sổ nhật ký chung toàn kỳ", "02_Ke_toan", "ketoan"),
    ("Sổ chi tiết và biên bản đối chiếu công nợ phải thu (TK 131)", "02_Ke_toan", "ketoan"),
    ("Sổ chi tiết và biên bản đối chiếu công nợ phải trả (TK 331)", "02_Ke_toan", "ketoan"),
    ("Sao kê và thư xác nhận số dư ngân hàng tại ngày khoá sổ", "04_Ngan_hang_Vay", "ketoan"),
    ("Biên bản kiểm kê quỹ tiền mặt tại ngày khoá sổ", "02_Ke_toan", "ketoan"),
    ("Khế ước vay, lịch trả nợ và xác nhận dư nợ của ngân hàng", "04_Ngan_hang_Vay", "ketoan"),
    ("Bảng tính khấu hao tài sản cố định và hồ sơ tăng giảm trong kỳ", "02_Ke_toan", "ketoan"),
    ("Tờ khai thuế GTGT, TNDN, TNCN đã nộp trong kỳ", "03_Thue", "ketoan"),
    ("Danh sách hợp đồng khách hàng và hợp đồng nhà cung cấp lớn trong kỳ", "07_Hop_dong", "ketoan"),
    ("Bảng lương, hợp đồng lao động và hồ sơ bảo hiểm", "06_Nhan_su", "hcns"),
    ("Hồ sơ pháp lý: đăng ký kinh doanh, điều lệ, giấy phép lữ hành", "01_Phap_ly", "hanh_chinh"),
    ("Biên bản họp HĐQT, Đại hội đồng cổ đông và nghị quyết trong kỳ", "09_HDQT_Co_dong", "hanh_chinh"),
    ("Hồ sơ đội xe: đăng kiểm, bảo hiểm, hợp đồng thế chấp", "01_Phap_ly", "gd_doi_xe"),
    ("Danh sách các bên liên quan và giao dịch với bên liên quan trong kỳ", "08_Kiem_toan", "ketoan"),
    ("Thư giải trình của Ban Giám đốc", "08_Kiem_toan", "ketoan"),
)


def next_code(db: Session, ky: str) -> str:
    # Số lấy theo SỐ LỚN NHẤT đã cấp cho đúng tiền tố này, không phải số dòng cả bảng —
    # xem `services/ma_tu_sinh.py` cho ba chỗ hỏng của lối đếm cũ.
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, HoSoKiemToan, f"KT{(ky or '').upper()}-", 3)


def kiem_du_lieu(db: Session, d: dict, tru_id: int | None = None) -> None:
    if d.get("loai") not in KT_LOAI:
        raise ValueError(f"Loại kiểm toán không hợp lệ. Chỉ nhận: {', '.join(KT_LOAI)}")
    ky = (d.get("ky") or "").strip().upper()
    if not ky:
        raise ValueError("Phải ghi kỳ kiểm toán (ví dụ 2026H1, 2026, 2026Q3)")
    if d.get("company_id") and not db.get(Company, d["company_id"]):
        raise ValueError("Không có pháp nhân này")
    if not (d.get("don_vi_kiem_toan") or "").strip():
        raise ValueError("Phải ghi đơn vị kiểm toán – hồ sơ không có tên đơn vị thì không biết đang "
                         "cung cấp tài liệu cho ai")
    q = select(HoSoKiemToan).where(HoSoKiemToan.ky == ky, HoSoKiemToan.loai == d["loai"])
    q = q.where(HoSoKiemToan.company_id == d.get("company_id"))
    if tru_id:
        q = q.where(HoSoKiemToan.id != tru_id)
    if db.execute(q).scalars().first():
        raise ValueError(f"Đã có hồ sơ {KT_LOAI[d['loai']]} kỳ {ky} cho pháp nhân này. Mở hồ sơ đó ra "
                         "bổ sung, đừng lập hồ sơ thứ hai cho cùng một kỳ")


def _ngay(v) -> date | None:
    if not v:
        return None
    return date.fromisoformat(v) if isinstance(v, str) else v


def tao(db: Session, u: User, data: dict, dung_mau: bool = True) -> HoSoKiemToan:
    kiem_du_lieu(db, data)
    ky = data["ky"].strip().upper()
    hs = HoSoKiemToan(
        code=next_code(db, ky), company_id=data.get("company_id"), ky=ky, loai=data["loai"],
        don_vi_kiem_toan=data["don_vi_kiem_toan"].strip(),
        so_hop_dong=(data.get("so_hop_dong") or "").strip(),
        nguoi_dau_moi=(data.get("nguoi_dau_moi") or u.username).strip(),
        ngay_bat_dau=_ngay(data.get("ngay_bat_dau")), han_hoan_thanh=_ngay(data.get("han_hoan_thanh")),
        ghi_chu=(data.get("ghi_chu") or "").strip(), created_by=u.username)
    db.add(hs)
    db.flush()
    if dung_mau:
        them_muc_mau(db, hs)
    R.audit(db, u.username, u.role, "tao_ho_so_kiem_toan", f"ho_so_kiem_toan:{hs.code}",
            after={"ky": hs.ky, "loai": hs.loai, "don_vi": hs.don_vi_kiem_toan})
    return hs


def them_muc_mau(db: Session, hs: HoSoKiemToan) -> int:
    """Nạp danh mục mẫu. Chỉ thêm mục CHƯA có tên trùng – gọi lại lần hai không nhân đôi danh mục."""
    da_co = {m.ten for m in db.execute(select(HoSoKiemToanMuc)
                                       .where(HoSoKiemToanMuc.ho_so_id == hs.id)).scalars()}
    stt = int(db.execute(select(func.coalesce(func.max(HoSoKiemToanMuc.stt), 0))
                         .where(HoSoKiemToanMuc.ho_so_id == hs.id)).scalar() or 0)
    n = 0
    for ten, nhom, phong in MAU_DANH_MUC:
        if ten in da_co:
            continue
        stt += 1
        db.add(HoSoKiemToanMuc(ho_so_id=hs.id, stt=stt, ten=ten, nhom_ho_so=nhom, phong_ban=phong,
                               han_nop=hs.han_hoan_thanh))
        n += 1
    db.flush()
    return n


def them_muc(db: Session, u: User, hs: HoSoKiemToan, data: dict) -> HoSoKiemToanMuc:
    ten = (data.get("ten") or "").strip()
    if not ten:
        raise ValueError("Phải ghi tên tài liệu kiểm toán yêu cầu")
    nhom = (data.get("nhom_ho_so") or "08_Kiem_toan").strip()
    if nhom not in NHOM_HO_SO:
        raise ValueError(f"Nhóm hồ sơ không hợp lệ. Chỉ nhận: {', '.join(NHOM_HO_SO)}")
    stt = int(db.execute(select(func.coalesce(func.max(HoSoKiemToanMuc.stt), 0))
                         .where(HoSoKiemToanMuc.ho_so_id == hs.id)).scalar() or 0) + 1
    m = HoSoKiemToanMuc(ho_so_id=hs.id, stt=stt, ten=ten, nhom_ho_so=nhom,
                        phong_ban=(data.get("phong_ban") or "ketoan").strip(),
                        nguoi_phu_trach=(data.get("nguoi_phu_trach") or "").strip(),
                        han_nop=_ngay(data.get("han_nop")) or hs.han_hoan_thanh,
                        ghi_chu=(data.get("ghi_chu") or "").strip())
    db.add(m)
    db.flush()
    R.audit(db, u.username, u.role, "them_muc_kiem_toan", f"ho_so_kiem_toan_muc:{m.id}",
            after={"ho_so": hs.code, "ten": ten})
    return m


def sua_muc(db: Session, u: User, m: HoSoKiemToanMuc, data: dict) -> HoSoKiemToanMuc:
    truoc = {"trang_thai": m.trang_thai, "nguoi_phu_trach": m.nguoi_phu_trach}
    if "trang_thai" in data:
        tt = (data.get("trang_thai") or "").strip()
        if tt not in MUC_TRANG_THAI:
            raise ValueError(f"Trạng thái mục không hợp lệ. Chỉ nhận: {', '.join(MUC_TRANG_THAI)}")
        # "Không áp dụng" phải nói vì sao. Đây là lối thoát dễ nhất để một mục thiếu được cho qua, y
        # như "máy sinh" trong bộ kiểm cửa nhập – nên nó phải tốn công một câu giải thích.
        if tt == "khong_can" and not (data.get("ghi_chu") or m.ghi_chu or "").strip():
            raise ValueError("Đánh dấu 'Không áp dụng cho kỳ này' phải ghi lý do")
        if tt == "da_gui" and not m.ngay_gui and not data.get("ngay_gui"):
            m.ngay_gui = date.today()
        m.trang_thai = tt
    for k in ("nguoi_phu_trach", "cau_hoi", "tra_loi", "ghi_chu"):
        if k in data:
            setattr(m, k, (data.get(k) or "").strip())
    if "phong_ban" in data:
        m.phong_ban = (data.get("phong_ban") or "ketoan").strip()
    if "han_nop" in data:
        m.han_nop = _ngay(data.get("han_nop"))
    if "ngay_gui" in data:
        m.ngay_gui = _ngay(data.get("ngay_gui"))
    db.flush()
    R.audit(db, u.username, u.role, "sua_muc_kiem_toan", f"ho_so_kiem_toan_muc:{m.id}",
            before=truoc, after={"trang_thai": m.trang_thai, "nguoi_phu_trach": m.nguoi_phu_trach})
    return m


def them_dieu_chinh(db: Session, u: User, hs: HoSoKiemToan, data: dict) -> HoSoKiemToanDieuChinh:
    if not (data.get("noi_dung") or "").strip():
        raise ValueError("Phải ghi kiểm toán đề nghị điều chỉnh nội dung gì")
    dc = HoSoKiemToanDieuChinh(ho_so_id=hs.id, noi_dung=data["noi_dung"].strip(),
                               trang_thai="de_xuat", created_by=u.username)
    db.add(dc)
    db.flush()
    R.audit(db, u.username, u.role, "them_dieu_chinh_kiem_toan", f"ho_so_kiem_toan:{hs.code}",
            after={"noi_dung": dc.noi_dung[:200]})
    return dc


def quyet_dieu_chinh(db: Session, u: User, dc: HoSoKiemToanDieuChinh, data: dict) -> HoSoKiemToanDieuChinh:
    """Ghi sổ hay không ghi – và cả hai đều phải để lại dấu vết."""
    tt = (data.get("trang_thai") or "").strip()
    if tt not in DC_TRANG_THAI:
        raise ValueError(f"Trạng thái điều chỉnh không hợp lệ. Chỉ nhận: {', '.join(DC_TRANG_THAI)}")
    if tt == "da_ghi_so":
        je_id = data.get("journal_entry_id")
        if not je_id:
            raise ValueError("Đánh dấu 'đã ghi sổ' phải kèm số hiệu bút toán – không có bút toán thì "
                             "chưa ghi sổ, dù đã đồng ý")
        if not db.get(JournalEntry, je_id):
            raise ValueError("Không có bút toán này trong sổ")
        dc.journal_entry_id = je_id
    if tt == "khong_dong_y":
        if len((data.get("ly_do") or "").strip()) < 20:
            raise ValueError("Không đồng ý với điều chỉnh của kiểm toán phải nêu lý do rõ ràng (ít "
                             "nhất 20 ký tự) – đây là phần kiểm toán sẽ hỏi lại bằng văn bản")
        dc.journal_entry_id = None
    truoc = {"trang_thai": dc.trang_thai}
    dc.trang_thai = tt
    dc.ly_do = (data.get("ly_do") or "").strip()
    dc.nguoi_quyet = u.username
    db.flush()
    R.audit(db, u.username, u.role, "quyet_dieu_chinh_kiem_toan", f"ho_so_kiem_toan_dieu_chinh:{dc.id}",
            before=truoc, after={"trang_thai": tt, "journal_entry_id": dc.journal_entry_id})
    return dc


def con_thieu(db: Session, hs: HoSoKiemToan) -> list:
    """Mục chưa gửi và không được đánh dấu không áp dụng."""
    return [m for m in db.execute(select(HoSoKiemToanMuc).where(HoSoKiemToanMuc.ho_so_id == hs.id)
                                  .order_by(HoSoKiemToanMuc.stt)).scalars()
            if m.trang_thai in ("chua_gui", "hoi_them")]


def chuyen_trang_thai(db: Session, u: User, hs: HoSoKiemToan, moi: str, data: dict | None = None) -> HoSoKiemToan:
    data = data or {}
    if moi not in KT_TRANG_THAI:
        raise ValueError("Trạng thái không hợp lệ")
    if moi not in KT_CHUYEN.get(hs.trang_thai, ()):
        raise ValueError(f"Không chuyển từ '{KT_TRANG_THAI[hs.trang_thai]}' sang "
                         f"'{KT_TRANG_THAI[moi]}' được")
    if moi == "da_phat_hanh":
        thieu = con_thieu(db, hs)
        if thieu:
            raise ValueError(
                f"Còn {len(thieu)} mục chưa cung cấp xong: "
                + "; ".join(f"#{m.stt} {m.ten}" for m in thieu[:5])
                + ("…" if len(thieu) > 5 else "")
                + ". Gửi nốt, hoặc đánh dấu 'Không áp dụng cho kỳ này' kèm lý do.")
        yk = (data.get("loai_y_kien") or "").strip()
        if yk not in KT_Y_KIEN:
            raise ValueError(f"Phải chọn loại ý kiến kiểm toán. Chỉ nhận: {', '.join(KT_Y_KIEN)}")
        if not (data.get("so_bao_cao") or "").strip():
            raise ValueError("Phải ghi số báo cáo kiểm toán")
        if yk != "chap_nhan_toan_phan" and len((data.get("van_de_nhan_manh") or "").strip()) < 20:
            raise ValueError("Ý kiến khác 'chấp nhận toàn phần' thì phải ghi nguyên văn cơ sở của ý "
                             "kiến ấy – công ty đại chúng công bố ý kiến ngoại trừ mà không nói ngoại "
                             "trừ cái gì là công bố thiếu")
        hs.loai_y_kien = yk
        hs.so_bao_cao = data["so_bao_cao"].strip()
        hs.ngay_bao_cao = _ngay(data.get("ngay_bao_cao")) or date.today()
        hs.van_de_nhan_manh = (data.get("van_de_nhan_manh") or "").strip()
    if moi == "dong":
        cho = [d for d in db.execute(select(HoSoKiemToanDieuChinh)
                                     .where(HoSoKiemToanDieuChinh.ho_so_id == hs.id)).scalars()
               if d.trang_thai == "de_xuat"]
        if cho:
            raise ValueError(f"Còn {len(cho)} bút toán điều chỉnh chưa quyết – ghi sổ hoặc ghi rõ "
                             "công ty không đồng ý, rồi mới đóng hồ sơ")
        hs.closed_at = datetime.now()
    cu = hs.trang_thai
    hs.trang_thai = moi
    db.flush()
    R.audit(db, u.username, u.role, "chuyen_ho_so_kiem_toan", f"ho_so_kiem_toan:{hs.code}",
            before={"trang_thai": cu}, after={"trang_thai": moi, "loai_y_kien": hs.loai_y_kien})
    return hs


def dem_tep(db: Session, ma_muc: int) -> int:
    """Số tệp đã gắn cho một mục. Đếm SỐNG từ kho tệp chung, không lưu thành cột.

    Lưu thành cột thì mỗi lần ai đó gỡ một tệp là con số sai, và không ai nhớ chạy lại phép đếm.
    """
    return int(db.execute(select(func.count()).select_from(Attachment)
                          .where(Attachment.doi_tuong == "ho_so_kiem_toan_muc",
                                 Attachment.doi_tuong_id == str(ma_muc))).scalar() or 0)


def chi_so(db: Session, hs: HoSoKiemToan) -> dict:
    muc = list(db.execute(select(HoSoKiemToanMuc).where(HoSoKiemToanMuc.ho_so_id == hs.id)).scalars())
    hom_nay = date.today()
    theo_tt = {}
    tre = 0
    for m in muc:
        theo_tt[m.trang_thai] = theo_tt.get(m.trang_thai, 0) + 1
        if m.trang_thai in ("chua_gui", "hoi_them") and m.han_nop and m.han_nop < hom_nay:
            tre += 1
    return {"tong_muc": len(muc), "theo_trang_thai": theo_tt, "tre_han": tre,
            "con_thieu": len([m for m in muc if m.trang_thai in ("chua_gui", "hoi_them")])}
