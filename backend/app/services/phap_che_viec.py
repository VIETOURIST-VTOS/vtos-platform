"""Đợt D2 – quy tắc của bàn làm việc Pháp chế.

Bốn quy tắc đáng gọi tên, vì mỗi cái chặn một lối đi tắt mà lúc bận ai cũng muốn đi:

  1. Đóng một yêu cầu PHẢI có kết quả viết ra. Đóng việc mà không nói đã trả gì thì sổ việc chỉ
     còn là một danh sách đã-bấm-nút.
  2. Kết luận "đạt có điều kiện" PHẢI có điều kiện. Không viết điều kiện thì sáu tháng sau đọc lại
     chỉ còn thấy chữ "đạt" — và đó đúng là cách một điều kiện bị bỏ quên.
  3. Một chữ ký PHẢI ghi căn cứ thẩm quyền. Đây là câu hỏi đầu tiên của mọi lần soát lại.
  4. Một bản ghi công bố còn xác nhận ở trạng thái "chờ" thì KHÔNG ghi được "đã công bố".

Tuổi việc (`so_ngay_treo`) tính bằng ngày, và nó KHÔNG phải một cột trong bảng: cột thì phải có
người cập nhật, mà con số không ai cập nhật là con số sai một cách im lặng.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.phap_che import BanGhiCongBo
from app.models.phap_che_viec import (BanGhiChuKy, KET_LUAN_RS, LOAI_YEU_CAU, MUC_RUI_RO,
                                      RaSoatHopDong, TRANG_THAI_YC, XacNhanChuSoLieu,
                                      YeuCauPhapChe)

# Việc "mới" quá bao nhiêu ngày thì coi là tồn. Một con số để dễ nhìn, không phải một hạn pháp lý.
NGAY_COI_LA_TON = 3
DANG_CHAY = ("moi", "dang_xu_ly", "cho_bo_sung")
DA_DONG = ("xong", "tu_choi")


# ─────────────────────────── yêu cầu ───────────────────────────
def tao_yeu_cau(db: Session, data: dict, boi: str) -> YeuCauPhapChe:
    yc = YeuCauPhapChe(trang_thai="moi", boi=boi, luc=datetime.now(), **data)
    db.add(yc)
    db.flush()
    return yc


def nhan_viec(db: Session, yc: YeuCauPhapChe, nguoi: str) -> YeuCauPhapChe:
    if yc.trang_thai in DA_DONG:
        raise ValueError(f"Yêu cầu đã đóng ({TRANG_THAI_YC[yc.trang_thai]}) – mở yêu cầu mới")
    yc.nguoi_nhan = nguoi
    yc.nhan_luc = yc.nhan_luc or datetime.now()
    yc.trang_thai = "dang_xu_ly"
    return yc


def cho_bo_sung(db: Session, yc: YeuCauPhapChe, ly_do: str) -> YeuCauPhapChe:
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi CẦN BỔ SUNG GÌ – 'chờ bổ sung' mà không nói chờ gì thì bên gửi "
                         "không biết phải làm gì, và việc nằm đó")
    if yc.trang_thai in DA_DONG:
        raise ValueError("Yêu cầu đã đóng")
    yc.trang_thai = "cho_bo_sung"
    yc.ket_qua = ly_do.strip()
    return yc


def dong_yeu_cau(db: Session, yc: YeuCauPhapChe, trang_thai: str, ket_qua: str,
                 boi: str) -> YeuCauPhapChe:
    """Đóng việc. Quy tắc 1: không có kết quả viết ra thì không đóng được."""
    if trang_thai not in DA_DONG:
        raise ValueError(f"Trạng thái đóng phải là một trong {DA_DONG}")
    if yc.trang_thai in DA_DONG:
        raise ValueError("Yêu cầu này đã đóng rồi")
    if not (ket_qua or "").strip():
        raise ValueError("Phải ghi KẾT QUẢ (hoặc lý do từ chối) – đóng việc mà không nói đã trả gì "
                         "thì sổ việc chỉ còn là danh sách đã bấm nút")
    yc.trang_thai = trang_thai
    yc.ket_qua = ket_qua.strip()
    yc.dong_luc = datetime.now()
    if not yc.nguoi_nhan:
        yc.nguoi_nhan = boi
    return yc


def so_ngay_treo(yc: YeuCauPhapChe, hom_nay: date | None = None) -> int | None:
    """Số ngày việc đang treo. RỖNG khi việc đã đóng – việc đóng rồi thì không còn treo."""
    if yc.trang_thai in DA_DONG:
        return None
    nay = hom_nay or date.today()
    bat_dau = yc.luc.date() if yc.luc else nay
    return (nay - bat_dau).days


def ra_yc(db: Session, yc: YeuCauPhapChe, hom_nay: date | None = None) -> dict:
    rs = db.execute(select(RaSoatHopDong).where(RaSoatHopDong.yeu_cau_id == yc.id)).scalars().first()
    treo = so_ngay_treo(yc, hom_nay)
    return {
        "id": yc.id, "loai": yc.loai, "loai_ten": LOAI_YEU_CAU.get(yc.loai, yc.loai),
        "tieu_de": yc.tieu_de, "noi_dung": yc.noi_dung,
        "phong_gui": yc.phong_gui, "nguoi_gui": yc.nguoi_gui,
        "muc_do": yc.muc_do, "han_mong_muon": yc.han_mong_muon,
        "trang_thai": yc.trang_thai, "trang_thai_ten": TRANG_THAI_YC.get(yc.trang_thai, yc.trang_thai),
        "nguoi_nhan": yc.nguoi_nhan, "nhan_luc": yc.nhan_luc,
        "ket_qua": yc.ket_qua, "dong_luc": yc.dong_luc,
        "so_ngay_treo": treo,
        "ton": treo is not None and treo >= NGAY_COI_LA_TON,
        "ra_soat_id": rs.id if rs else None,
        "attachment_id": yc.attachment_id,
        "boi": yc.boi, "luc": yc.luc,
    }


# ─────────────────────────── rà soát hợp đồng ───────────────────────────
def _loc_rui_ro(rui_ro) -> list:
    """Giữ đúng ba trường, và chỉ nhận mức có trong danh mục. Một mức lạ lọt vào đây sẽ không bao
    giờ hiện ra ở bộ lọc 'rủi ro cao', tức là biến mất mà không báo."""
    ra = []
    for r in (rui_ro or []):
        if not isinstance(r, dict):
            continue
        muc = str(r.get("muc", "")).strip()
        if muc not in MUC_RUI_RO:
            raise ValueError(f"Mức rủi ro không hợp lệ: '{muc}' (phải là {list(MUC_RUI_RO)})")
        noi_dung = str(r.get("noi_dung", "")).strip()
        if not noi_dung:
            raise ValueError("Mỗi rủi ro phải có nội dung – một mức độ không kèm nội dung thì "
                             "người đọc không biết phải sửa gì")
        ra.append({"muc": muc, "noi_dung": noi_dung,
                   "dieu_khoan": str(r.get("dieu_khoan", "")).strip()})
    return ra


def ghi_ra_soat(db: Session, yc: YeuCauPhapChe, data: dict, boi: str) -> RaSoatHopDong:
    """Quy tắc 2: 'đạt có điều kiện' mà không có điều kiện thì không ghi."""
    ket_luan = (data.get("ket_luan") or "").strip()
    if ket_luan and ket_luan not in KET_LUAN_RS:
        raise ValueError(f"Kết luận không hợp lệ: {ket_luan}")
    if ket_luan == "dat_co_dieu_kien" and not (data.get("dieu_kien") or "").strip():
        raise ValueError("Kết luận 'đạt CÓ ĐIỀU KIỆN' bắt buộc ghi ĐIỀU KIỆN – không viết ra thì "
                         "lần đọc lại chỉ còn thấy chữ 'đạt'")
    rui_ro = _loc_rui_ro(data.get("rui_ro"))
    rs = db.execute(select(RaSoatHopDong).where(RaSoatHopDong.yeu_cau_id == yc.id)).scalars().first()
    if rs is None:
        rs = RaSoatHopDong(yeu_cau_id=yc.id, boi=boi, luc=datetime.now())
        db.add(rs)
    for k in ("so_hop_dong", "doi_tac", "loai_hop_dong", "gia_tri", "ngay_nhan", "ngay_tra",
              "dieu_kien", "nguoi_ra_soat", "attachment_id"):
        if k in data:
            setattr(rs, k, data[k])
    if ket_luan:
        rs.ket_luan = ket_luan
    rs.rui_ro = rui_ro
    db.flush()
    return rs


def ra_rs(rs: RaSoatHopDong) -> dict:
    cao = [r for r in (rs.rui_ro or []) if r.get("muc") == "cao"]
    return {
        "id": rs.id, "yeu_cau_id": rs.yeu_cau_id, "so_hop_dong": rs.so_hop_dong,
        "doi_tac": rs.doi_tac, "loai_hop_dong": rs.loai_hop_dong,
        # K2: rỗng đi ra ngoài là rỗng, không đổi thành 0.
        "gia_tri": float(rs.gia_tri) if rs.gia_tri is not None else None,
        "ngay_nhan": rs.ngay_nhan, "ngay_tra": rs.ngay_tra,
        "ket_luan": rs.ket_luan, "ket_luan_ten": KET_LUAN_RS.get(rs.ket_luan, ""),
        "rui_ro": rs.rui_ro or [], "so_rui_ro_cao": len(cao),
        "dieu_kien": rs.dieu_kien, "nguoi_ra_soat": rs.nguoi_ra_soat,
        "attachment_id": rs.attachment_id, "boi": rs.boi, "luc": rs.luc,
    }


# ─────────────────────────── sổ chữ ký ───────────────────────────
def ghi_chu_ky(db: Session, data: dict, boi: str) -> BanGhiChuKy:
    """Quy tắc 3: không có căn cứ thẩm quyền thì không ghi vào sổ."""
    if not (data.get("can_cu_tham_quyen") or "").strip():
        raise ValueError("Phải ghi CĂN CỨ THẨM QUYỀN (điều lệ, nghị quyết, giấy uỷ quyền nào) – "
                         "đây là câu hỏi đầu tiên của mọi lần soát lại một chữ ký")
    if not (data.get("nguoi_ky") or "").strip():
        raise ValueError("Phải ghi NGƯỜI KÝ")
    if not data.get("van_ban_id") and not (data.get("mo_ta") or "").strip():
        raise ValueError("Phải trỏ tới một văn bản hoặc mô tả bằng lời đã ký cái gì")
    bg = BanGhiChuKy(boi=boi, luc=datetime.now(), **data)
    db.add(bg)
    db.flush()
    return bg


# ─────────────────────────── xác nhận chủ số liệu ───────────────────────────
def mo_xac_nhan(db: Session, bg: BanGhiCongBo, chi_muc: str, chu_so_lieu: str,
                boi: str) -> XacNhanChuSoLieu:
    if not (chi_muc or "").strip() or not (chu_so_lieu or "").strip():
        raise ValueError("Phải ghi CHỈ MỤC và CHỦ SỐ LIỆU – một xác nhận không biết hỏi ai thì "
                         "không bao giờ về")
    if bg.da_cong_bo_luc is not None:
        raise ValueError("Bản ghi đã công bố rồi – xin xác nhận sau khi công bố là xin cho có")
    cu = db.execute(select(XacNhanChuSoLieu).where(
        XacNhanChuSoLieu.ban_ghi_id == bg.id,
        XacNhanChuSoLieu.chi_muc == chi_muc.strip())).scalars().first()
    if cu is not None:
        raise ValueError(f"Chỉ mục '{chi_muc}' của bản ghi này đã có người được hỏi")
    x = XacNhanChuSoLieu(ban_ghi_id=bg.id, chi_muc=chi_muc.strip(),
                         chu_so_lieu=chu_so_lieu.strip(), trang_thai="cho",
                         boi=boi, luc=datetime.now())
    db.add(x)
    db.flush()
    return x


def tra_loi_xac_nhan(db: Session, x: XacNhanChuSoLieu, dong_y: bool, y_kien: str,
                     boi: str) -> XacNhanChuSoLieu:
    if x.trang_thai != "cho":
        raise ValueError("Xác nhận này đã trả lời rồi")
    if not dong_y and not (y_kien or "").strip():
        raise ValueError("Từ chối xác nhận phải có Ý KIẾN – từ chối không nêu lý do thì người làm "
                         "hồ sơ không biết sửa gì")
    x.trang_thai = "xac_nhan" if dong_y else "tu_choi"
    x.y_kien = (y_kien or "").strip()
    x.xac_nhan_boi = boi
    x.xac_nhan_luc = datetime.now()
    return x


def con_cho_xac_nhan(db: Session, ban_ghi_id: int) -> list[XacNhanChuSoLieu]:
    """Những xác nhận CHƯA về của một bản ghi công bố. Rỗng = không vướng gì."""
    return list(db.execute(select(XacNhanChuSoLieu).where(
        XacNhanChuSoLieu.ban_ghi_id == ban_ghi_id,
        XacNhanChuSoLieu.trang_thai == "cho")).scalars())


def tu_choi_xac_nhan(db: Session, ban_ghi_id: int) -> list[XacNhanChuSoLieu]:
    return list(db.execute(select(XacNhanChuSoLieu).where(
        XacNhanChuSoLieu.ban_ghi_id == ban_ghi_id,
        XacNhanChuSoLieu.trang_thai == "tu_choi")).scalars())


def chan_cong_bo(db: Session, ban_ghi_id: int) -> str:
    """Quy tắc 4. Trả về câu từ chối, hoặc chuỗi rỗng nếu không vướng.

    Lưu ý KHÔNG chặn khi bản ghi chưa ai mở xác nhận nào: bắt buộc mọi bản ghi phải có xác nhận là
    một quy tắc nghiệp vụ, và quy tắc nghiệp vụ thì phải có người ký — làn viết phần mềm không tự
    đặt. Ở đây chỉ chặn đúng chỗ ĐÃ HỎI mà CHƯA CÓ TRẢ LỜI, hoặc trả lời là KHÔNG.
    """
    cho = con_cho_xac_nhan(db, ban_ghi_id)
    if cho:
        ten = ", ".join(f"{x.chi_muc} ({x.chu_so_lieu})" for x in cho[:5])
        return (f"Còn {len(cho)} xác nhận chủ số liệu CHƯA về: {ten}. Con số ra khỏi công ty trước "
                f"khi người chịu trách nhiệm về nó xác nhận là con số không ai đứng tên.")
    tu_choi = tu_choi_xac_nhan(db, ban_ghi_id)
    if tu_choi:
        ten = ", ".join(f"{x.chi_muc} ({x.chu_so_lieu})" for x in tu_choi[:5])
        return (f"Có {len(tu_choi)} chủ số liệu TỪ CHỐI xác nhận: {ten}. Phải xử lý ý kiến của họ "
                f"rồi mở lại xác nhận, không công bố đè lên một lời từ chối.")
    return ""


def ra_xn(x: XacNhanChuSoLieu) -> dict:
    from app.models.phap_che_viec import TRANG_THAI_XN
    return {"id": x.id, "ban_ghi_id": x.ban_ghi_id, "chi_muc": x.chi_muc,
            "chu_so_lieu": x.chu_so_lieu, "trang_thai": x.trang_thai,
            "trang_thai_ten": TRANG_THAI_XN.get(x.trang_thai, x.trang_thai),
            "y_kien": x.y_kien, "xac_nhan_boi": x.xac_nhan_boi,
            "xac_nhan_luc": x.xac_nhan_luc, "boi": x.boi, "luc": x.luc}


# ─────────────────────────── bảng việc ───────────────────────────
def ban_lam_viec(db: Session, hom_nay: date | None = None) -> dict:
    nay = hom_nay or date.today()
    ds = [ra_yc(db, y, nay) for y in db.execute(
        select(YeuCauPhapChe).order_by(YeuCauPhapChe.id.desc())).scalars()]
    dang = [d for d in ds if d["trang_thai"] in DANG_CHAY]
    return {
        "hom_nay": nay,
        "ngay_coi_la_ton": NGAY_COI_LA_TON,
        "so_tat_ca": len(ds),
        "so_dang_chay": len(dang),
        "so_ton": len([d for d in dang if d["ton"]]),
        "so_gap_dang_chay": len([d for d in dang if d["muc_do"] == "gap"]),
        "rows": ds,
        "ghi_chu": ("Tuổi việc tính từ lúc nhận yêu cầu tới hôm nay, tính lúc đọc chứ không lưu "
                    "thành cột: một con số không ai cập nhật là một con số sai một cách im lặng."),
    }


# ─────────────── PC-1 · chuông «yêu cầu Pháp chế mới» (19/10/2026) ───────────────
CHUONG_YC_MOI = "phap_che_yc_moi"


def _ref_yc(yc: YeuCauPhapChe) -> str:
    return f"yeu_cau_phap_che:{yc.id}"


def bao_chuong_yc_moi(db: Session, yc: YeuCauPhapChe) -> None:
    """Một chuông cho Pháp chế khi trưởng phòng TỰ GỬI. Chưa ai nhận nên không có chủ — đúng."""
    from app.services import cskh as CS
    muc = "red" if yc.muc_do == "gap" else "warn"
    CS.giao_viec(db, CHUONG_YC_MOI, _ref_yc(yc),
                 f"Yêu cầu Pháp chế mới #{yc.id} · {yc.phong_gui or '—'} · «{yc.tieu_de[:120]}»"
                 + (" · GẤP" if yc.muc_do == "gap" else ""),
                 nguoi_id=None, han_gio=None, roles="ir_phapche", level=muc)


def tat_chuong_yc(db: Session, yc: YeuCauPhapChe, vi_sao: str) -> int:
    """Tự tắt chuông khi Pháp chế nhận việc hoặc đóng yêu cầu. Trả số chuông đã tắt."""
    from app.models.core import Alert
    n = 0
    for a in db.execute(select(Alert).where(Alert.kind == CHUONG_YC_MOI, Alert.ref == _ref_yc(yc),
                                            Alert.resolved == False)).scalars():  # noqa: E712
        a.resolved, a.trang_thai = True, "dong"
        a.dong_luc, a.bang_chung = datetime.now(), f"Tự đóng: {vi_sao}"
        n += 1
    return n
