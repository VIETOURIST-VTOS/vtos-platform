"""R5 · Bàn làm việc Giám đốc Kinh doanh lẻ — Chủ tịch duyệt bản xem trước 13/11/2026 03:21.

CHỈ ĐỌC, KHÔNG SỞ HỮU CON SỐ NÀO. Mỗi số trên bàn đọc lại từ MỘT hàm đang nuôi một màn có sẵn:

    chuyến đang bán · chỗ trống · sắp khởi hành · chưa có dự toán   ← services.ban_tour_le (/ban-tour-le)
    tài khoản chưa có đơn vị · số đơn vị mảng Lẻ                    ← services.to_chuc_kd (/to-chuc-kd)
    phiếu chăm sóc quá hạn                                           ← services.cskh (/cham-soc)
    khách chờ trả lời                                                ← bảng hội thoại (/inbox, cửa status)
    booking · doanh thu · lead · tour lệch quy tắc mảng              ← services.bao_cao_phong (/fit)
    doanh thu tính chỉ tiêu                                          ← services.doanh_thu_kd (/fit, tab doanh thu)

Không chép lại phép tính nào: chép là dựng bản thứ hai, và bản thứ hai rồi cũng lệch.

`None` KHÁC 0. Ô nào chưa có cơ sở để tính thì trả `None` kèm `ly_do`; màn hình in chữ «chưa đo»
cùng lý do, không in số 0 (ranh giới 09/9/2026 — không điền số tạm).

Hộp thư và chăm sóc là số TOÀN CÔNG TY: hai màn ấy chưa có phép lọc mảng. Chủ tịch đồng ý
13/11/2026 để nguyên và gắn nhãn `pham_vi = "toan_cong_ty"` — không đoán phần của Lẻ.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.crm import Conversation
from app.models.to_chuc_kd import DonViKD
from app.services import ban_tour_le as BTL
from app.services import bao_cao_phong as BP
from app.services import cskh as CS
from app.services import doanh_thu_kd as DT
from app.services import to_chuc_kd as TC

TOAN_CTY = "toan_cong_ty"


def _o(so, nguon: str, ly_do: str = "", pham_vi: str = "kd_le") -> dict:
    return {"so": so, "nguon": nguon, "ly_do": "" if so is not None else (ly_do or "chưa có cửa đo"),
            "pham_vi": pham_vi}


def _chi_tieu(db: Session, tu: date, den: date) -> dict:
    """Các chỉ tiêu của bảng /fit phòng Kinh doanh lẻ, theo mã."""
    return {c["ma"]: c for c in BP._kd_le(db, tu, den)}


def _doanh_thu_tinh_chi_tieu(db: Session, ky: str, ids: list[int]):
    if not ids:
        return None, "Chưa khai đơn vị Kinh doanh lẻ nên chưa có phạm vi để cộng."
    try:
        return DT.thang(db, ky, "", ids).get("tong_tinh_chi_tieu"), ""
    except Exception as ex:  # noqa: BLE001 — một ô hỏng không được làm sập cả bàn
        return None, f"Không đọc được: {ex}"


def tong_quan(db: Session, hom_nay: date | None = None) -> dict:
    d = hom_nay or date.today()
    ky = f"{d:%Y-%m}"

    btl = BTL.ban_lam_viec(db)
    rows, t = btl["rows"], btl["tong"]
    n = len(rows)

    don_vi = [dv.id for dv in db.execute(select(DonViKD).where(DonViKD.mang == "le")).scalars()
              if dv.dang_hieu_luc(d)]
    chua_pc = len(TC.chua_phan_cong(db, d, "le"))

    cs = CS.chi_so_cham_soc(db)
    cho_tra_loi = int(db.execute(select(func.count()).select_from(Conversation)
                                 .where(Conversation.unanswered == True)).scalar() or 0)  # noqa: E712

    ct = _chi_tieu(db, d.replace(day=1), d)
    g = lambda ma: (ct.get(ma) or {}).get("gia_tri")  # noqa: E731

    dt, ly_do_dt = _doanh_thu_tinh_chi_tieu(db, ky, don_vi)
    co_du_toan = n - t["chua_du_co_so"]
    co_gia = sum(1 for r in rows if (r["gia_ban"] or 0) > 0)
    co_cpcd = sum(1 for r in rows if (r["chi_phi_co_dinh"] or 0) > 0)

    the = {
        "chuyen_dang_ban": _o(t["chuyen"], "/ban-tour-le"),
        "cho_con": _o(t["cho_con"], "/ban-tour-le"),
        "sap_khoi_hanh": _o(t["sap_khoi_hanh"], "/ban-tour-le"),
        "doanh_thu_chi_tieu": _o(dt, "/fit", ly_do_dt),   # R5-2: /kinh-doanh-le gộp vào /fit
    }

    # Bảy việc, đúng thứ tự bản vẽ đã duyệt. `toi` = màn đang giữ nghiệp vụ (bàn mở nó trong khung).
    viec = [
        {"ma": "chua_don_vi", "muc": "do", "toi": "/to-chuc-kd",
         "ten": "Tài khoản kinh doanh chưa có đơn vị",
         "mo_ta": "Gốc của các việc khác: chưa khai đơn vị thì doanh thu và chỉ tiêu không có phạm vi. "
                  "Khai danh mục là việc của Hành chính – Nhân sự.",
         **_o(chua_pc, "/to-chuc-kd · chưa phân công")},
        {"ma": "chua_du_toan", "muc": "do", "toi": "/ban-tour-le",
         "ten": "Chuyến đang bán chưa có dự toán riêng",
         "mo_ta": "Các chuyến này ghi lợi nhuận «chưa đủ cơ sở tính».",
         **_o(t["chua_du_co_so"], "/ban-tour-le")},
        {"ma": "cham_soc_qua_han", "muc": "do", "toi": "/cham-soc",
         "ten": "Phiếu chăm sóc quá hạn liên hệ",
         "mo_ta": f"{cs['chua_ghi']} phiếu chưa ghi kết quả.",
         **_o(cs["qua_han"], "/cham-soc · chỉ số", pham_vi=TOAN_CTY)},
        {"ma": "hop_thu_cho", "muc": "cam", "toi": "/inbox",
         "ten": "Khách đang chờ sale trả lời",
         "mo_ta": "Hội thoại khách nhắn chưa ai trả lời.",
         **_o(cho_tra_loi, "/inbox", pham_vi=TOAN_CTY)},
        {"ma": "sap_khoi_hanh", "muc": "cam", "toi": "/ban-tour-le",
         "ten": "Chuyến khởi hành trong 7 ngày",
         "mo_ta": "Hết ngày khởi hành là hết bán. Danh sách ở bảng «Chuyến cần thúc bán».",
         **_o(t["sap_khoi_hanh"], "/ban-tour-le")},
        {"ma": "lech_mang", "muc": "vang", "toi": "/fit",
         "ten": "Tour hai quy tắc mảng nói khác nhau",
         "mo_ta": "Kinh doanh sửa dữ liệu gốc (loại chuyến hoặc mã tour) để hai quy tắc khớp lại.",
         **_o(g("lech_quy_tac_mang"), "/fit")},
        {"ma": "cho_dieu_hanh", "muc": "cho", "toi": "",
         "ten": "Lịch khởi hành do Phòng Điều hành mở",
         "mo_ta": "Bàn này không mở chuyến mới được. Đây là việc chờ, không phải việc tồn của phòng.",
         "so": None, "nguon": "", "ly_do": "", "pham_vi": "kd_le"},
    ]

    ket_qua = {"ky": ky, "booking": g("booking"), "doanh_thu": g("doanh_thu"), "lead": g("lead"),
               "ty_le_chot": g("ty_le_chot"), "nguon": "/fit"}

    san_sang = [
        {"ten": "Có lịch khởi hành đang bán", "dat": n > 0, "so": f"{n}"},
        {"ten": "Có giá bán trên từng chuyến", "dat": n > 0 and co_gia == n, "so": f"{co_gia} / {n}"},
        {"ten": "Dự toán riêng từng chuyến", "dat": n > 0 and co_du_toan == n, "so": f"{co_du_toan} / {n}"},
        {"ten": "Chi phí cố định từng chuyến", "dat": n > 0 and co_cpcd == n, "so": f"{co_cpcd} / {n}"},
        {"ten": "Đơn vị kinh doanh", "dat": bool(don_vi) and chua_pc == 0,
         "so": f"{len(don_vi)} đơn vị · {chua_pc} người chưa gắn"},
    ]

    # Chuyến cần thúc bán: khởi hành trong 7 ngày, còn chỗ, trống nhiều đứng đầu.
    thuc = sorted([r for r in rows if r["days_left"] <= 7 and r["cho_con"] > 0],
                  key=lambda r: (-r["cho_con"], r["start_date"]))
    thuc_ban = [{"id": r["id"], "code": r["code"], "name": r["name"], "start_date": r["start_date"],
                 "cho_da_ban": r["cho_da_ban"], "cho_mo_ban": r["cho_mo_ban"], "cho_con": r["cho_con"],
                 "gia_ban": r["gia_ban"], "loi_nhuan_tai_so_dang_ban": r["loi_nhuan_tai_so_dang_ban"],
                 "trang_thai_cong": r["trang_thai_cong"]} for r in thuc]

    return {"ngay": d.isoformat(), "the": the, "viec": viec, "ket_qua": ket_qua,
            "san_sang": san_sang, "thuc_ban": thuc_ban}
