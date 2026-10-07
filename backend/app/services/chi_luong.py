"""Đợt A2 – Kế toán CHI, đọc Ủy nhiệm chi, đối chiếu với bản khóa, kết luận ĐÃ TRẢ.

BA TẦNG BẰNG CHỨNG, XẾP THEO ĐỘ CHẮC CHẮN GIẢM DẦN

  1. GIAO DỊCH SEPAY – tiền có thật sự rời khỏi tài khoản không. Đây là bằng chứng chắc nhất vì nó
     do ngân hàng đẩy về, không ai trong công ty gõ được.
  2. MẶT ỦY NHIỆM CHI – tổng số tiền, ngày, số tham chiếu. Máy đọc được; người sửa được.
  3. PHỤ LỤC TỪNG NGƯỜI – ai nhận bao nhiêu. Chỉ tầng này mới trả lời được câu "có ai bị sót không".

Thiếu tầng 3 thì vẫn kết luận được, nhưng chỉ ở mức tổng, và kết luận phải NÓI RA rằng nó chỉ ở mức
tổng. Một kết luận "đã trả đủ" dựa trên mỗi con số tổng là câu trả lời đúng cho câu hỏi sai: tổng
khớp vẫn có thể có một người nhận thừa và một người nhận thiếu.

VÌ SAO ĐỌC PHỤ LỤC BẰNG MÁY ĐƯỢC, CÒN BẢNG LƯƠNG THÌ KHÔNG

Lệnh 08/9/2026 cấm đọc bảng lương và bảng bảo hiểm bằng máy – dữ liệu cá nhân theo Nghị định
13/2023. Chủ tịch mở một ngoại lệ HẸP ngày 07/10/2026 cho phụ lục kèm Ủy nhiệm chi, và chỗ mở nằm ở
`models/doc_chung_tu.py::MO_DOC_CO_CHU_KY`, có phép thử canh. Hai khác biệt làm ngoại lệ này đứng
được, và cả hai đều là ràng buộc trong mã chứ không phải lời hứa:

  · Phụ lục chỉ có HỌ TÊN và SỐ TIỀN CHUYỂN. Không lương cơ bản, không phụ cấp, không bảo hiểm,
    không thuế, không khoản trừ – tức là không có cơ cấu thu nhập của ai cả.
  · KHÔNG ĐỌC SỐ TÀI KHOẢN. Hồ sơ nhân sự trong hệ thống không lưu số tài khoản người lao động,
    nên đọc ra cũng không đối chiếu được với gì; đọc một dữ liệu định danh mà không dùng được là
    rủi ro thuần. Khai vào `cam_truong`, và `_loc_phu_luc` bỏ nó kể cả khi mô hình tự trả về.

CÙNG ĐẦU VÀO RA CÙNG KẾT LUẬN

Mô hình ngôn ngữ chỉ làm đúng một việc: đọc chữ trên ảnh thành số. Việc so sánh và việc kết luận
đủ/một phần/lỗi là QUY TẮC XÁC ĐỊNH trong tệp này. Mô hình không bao giờ được hỏi "bảng này khớp
chưa" – nếu hỏi, thì cùng một tấm ảnh hôm nay nói khớp hôm mai nói không, và không ai dám dùng nó
để kết luận đã trả lương cho người lao động.
"""
from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chi_luong import ChiKyLuong, KET_LUAN, TRA_TRANG_THAI
from app.models.doc_chung_tu import MO_DOC_CO_CHU_KY
from app.models.hr import PayrollRun
from app.models.luong_khoa import BangLuongKhoa
from app.models.payments import BankTransaction

# Sai lệch bỏ qua được khi so tiền. Bảng lương làm tròn tới đồng; một đồng lệch là lỗi làm tròn,
# không phải lỗi trả tiền. Để rộng hơn thì bắt đầu che mất những khoản thiếu thật.
NGUONG_LAM_TRON = 1.0

# Cửa sổ tìm giao dịch SePay quanh ngày chuyển. Ngân hàng ghi nhận lệch ngày là chuyện thường
# (chuyển sau giờ cắt, cuối tuần), nên nới hai ngày mỗi bên chứ không đòi đúng ngày.
NGAY_TIM_SEPAY = 2

LOAI_PHU_LUC = "phu_luc_unc_luong"


# ====================== CHUẨN HÓA TÊN ======================
def chuan_ten(s: str) -> str:
    """Tên để SO SÁNH, không phải tên để hiển thị.

    Phụ lục ngân hàng in tên không dấu, viết hoa, đôi khi thừa khoảng trắng; hồ sơ nhân sự lưu tên
    có dấu. So thẳng hai chuỗi ấy thì không bao giờ khớp, và cả bộ đối chiếu thành vô dụng.
    """
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("Đ", "D").replace("đ", "d")
    return " ".join(t.upper().split())


# ====================== ĐỌC MẶT UNC ======================
_NHAC_MAT_UNC = (
    "Đọc MẶT ỦY NHIỆM CHI trong ảnh và trả về DUY NHẤT một đối tượng JSON, không kèm lời giải thích.\n"
    "Các khóa cần có, đúng tên này:\n"
    "  - ngan_hang\n  - tai_khoan_cong_ty\n  - ngay_chuyen\n  - so_tham_chieu\n  - so_tien\n  - noi_dung\n\n"
    "Quy tắc bắt buộc:\n"
    "1. Ô nào không nhìn rõ, bị che, hoặc không có trên chứng từ thì để CHUỖI RỖNG \"\". TUYỆT ĐỐI "
    "không suy đoán và KHÔNG BAO GIỜ điền 0 thay cho \"không đọc được\".\n"
    "2. `tai_khoan_cong_ty` là tài khoản TRÍCH TIỀN (bên chi). KHÔNG đọc tài khoản người nhận.\n"
    "3. Số tiền ghi bằng chữ số, không dấu phân cách, không đơn vị. Ngày ghi dạng DD/MM/YYYY.\n"
    "4. KHÔNG đọc danh sách từng người trên tấm này, kể cả khi có. Chỉ đọc sáu ô trên.\n"
    "5. Thêm khóa \"_ghi_chu\": một câu ngắn về chất lượng ảnh hoặc chỗ đáng ngờ, để trống nếu không có.\n"
)

_NHAC_PHU_LUC = (
    "Đọc PHỤ LỤC DANH SÁCH CHUYỂN LƯƠNG kèm Ủy nhiệm chi và trả về DUY NHẤT một đối tượng JSON.\n"
    "Khóa duy nhất: \"dong\" – một danh sách, mỗi phần tử có ĐÚNG hai khóa:\n"
    "  - ho_ten\n  - so_tien\n\n"
    "Quy tắc bắt buộc:\n"
    "1. TUYỆT ĐỐI KHÔNG đọc và KHÔNG trả về số tài khoản, số CCCD, ngày sinh, số điện thoại, lương "
    "cơ bản, phụ cấp, bảo hiểm, thuế hay bất kỳ khoản trừ nào – kể cả khi chúng có trên chứng từ.\n"
    "2. Dòng nào không đọc được số tiền thì để \"so_tien\" là CHUỖI RỖNG \"\". KHÔNG điền 0.\n"
    "3. Số tiền ghi bằng chữ số, không dấu phân cách, không đơn vị.\n"
    "4. Bỏ qua dòng tổng cộng ở cuối bảng – chỉ lấy các dòng của từng người.\n"
    "5. Thêm khóa \"_ghi_chu\": một câu ngắn về chất lượng ảnh hoặc chỗ đáng ngờ, để trống nếu không có.\n"
)


def _so(v) -> float | None:
    """Chuỗi tiền của mô hình thành số. RỖNG TRẢ VỀ None, không trả về 0 (quy tắc K2)."""
    s = str(v if v is not None else "").strip()
    if not s:
        return None
    s = s.replace(",", "").replace(".", "").replace(" ", "").replace("đ", "").replace("₫", "")
    try:
        return float(s)
    except ValueError:
        return None


def _ngay(v):
    s = str(v or "").strip()
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def _loc_phu_luc(tho: dict) -> tuple[list[dict], list[str]]:
    """Lọc lần hai ở phía ta. Dặn mô hình đừng đọc số tài khoản là một lời dặn; bỏ nó ở đây là một
    ràng buộc. Trả về (các dòng sạch, tên các trường đã bị bỏ) – bỏ cái gì thì phải nói ra."""
    cam = set(MO_DOC_CO_CHU_KY[LOAI_PHU_LUC]["cam_truong"])
    cho_phep = MO_DOC_CO_CHU_KY[LOAI_PHU_LUC]["truong"]
    dong, da_bo = [], set()
    for d in (tho.get("dong") or []):
        if not isinstance(d, dict):
            continue
        da_bo |= (set(d) & cam)
        ten = " ".join(str(d.get("ho_ten") or "").split())
        if not ten:
            continue
        dong.append({k: (ten if k == "ho_ten" else _so(d.get(k))) for k in cho_phep})
    return dong, sorted(da_bo)


def doc_mat_unc(db: Session, chi: ChiKyLuong, ten_tep: str, data: bytes, kieu: str,
                boi: str, vai_tro: str) -> dict:
    """Máy đọc mặt UNC vào bản nháp của lần chi. Người sửa được trước khi bấm đối chiếu."""
    from app.services import doc_chung_tu as DCT, attachments as AT, ai_log as AL
    k = DCT._kieu_anh(kieu, ten_tep)
    if not k:
        raise DCT.KhongDocDuoc("Chỉ đọc được ảnh JPG/PNG/GIF/WEBP hoặc tệp PDF.")
    muc = _muc_ai(db, vai_tro)
    # Kho "bang_luong" nằm trong nhóm hồ sơ 06_Nhan_su – nhóm có phân quyền riêng theo Nghị định
    # 13/2023. Mặt UNC tự nó không có dữ liệu của ai, nhưng nó đi liền phụ lục; để chung một kho có
    # phân quyền chặt là bảo vệ thừa, còn tách ra là mời người ta mở nhầm chỗ.
    a, _ = AT.dinh_kem(db, "bang_luong", chi.period, ten_tep, data, kieu=k,
                       loai="chung_tu", mo_ta=f"Ủy nhiệm chi lương {chi.period} lần {chi.lan}",
                       boi=boi, nguon="nguoi_nhap", ky=chi.period)
    kq = DCT._goi_mo_hinh("", data, k, nhac=_NHAC_MAT_UNC)
    tho = kq["tho"] if isinstance(kq.get("tho"), dict) else {}
    chi.unc_attachment_id = a.id
    chi.ngan_hang = str(tho.get("ngan_hang") or "")[:60]
    chi.tai_khoan_cong_ty = str(tho.get("tai_khoan_cong_ty") or "")[:40]
    chi.ngay_chuyen = _ngay(tho.get("ngay_chuyen"))
    chi.so_tham_chieu = str(tho.get("so_tham_chieu") or "")[:80]
    chi.so_tien_unc = _so(tho.get("so_tien"))     # rỗng để NGUYÊN rỗng
    chi.noi_dung_unc = str(tho.get("noi_dung") or "")[:300]
    AL.ghi(db, tac_vu=DCT.TAC_VU, muc=muc, dau_vao=a.checksum,
           ket_qua=json.dumps(tho, ensure_ascii=False), nguon=kq["nguon"], mo_hinh=kq["mo_hinh"],
           ref=f"chi_luong:{chi.period}:{chi.lan}:mat_unc", vai_tro=vai_tro, nguoi=boi, so_ban_ghi=1,
           tokens_vao=kq["tokens_vao"], tokens_ra=kq["tokens_ra"],
           trang_thai="cho_hau_kiem", loi=kq["loi"])
    db.flush()
    return {"so_tien_unc": chi.so_tien_unc, "ghi_chu_may": str(tho.get("_ghi_chu") or ""), "loi": kq["loi"]}


def doc_phu_luc(db: Session, chi: ChiKyLuong, ten_tep: str, data: bytes, kieu: str,
                boi: str, vai_tro: str) -> dict:
    """Máy đọc phụ lục từng người. Mở theo ngoại lệ có chữ ký, và hẹp đúng hai trường."""
    from app.services import doc_chung_tu as DCT, attachments as AT, ai_log as AL
    kiem_ngoai_le_con_hieu_luc()
    k = DCT._kieu_anh(kieu, ten_tep)
    if not k:
        raise DCT.KhongDocDuoc("Chỉ đọc được ảnh JPG/PNG/GIF/WEBP hoặc tệp PDF.")
    muc = _muc_ai(db, vai_tro)
    a, _ = AT.dinh_kem(db, "bang_luong", chi.period, ten_tep, data, kieu=k,
                       loai="chung_tu", mo_ta=f"Phụ lục chuyển lương {chi.period} lần {chi.lan}",
                       boi=boi, nguon="nguoi_nhap", ky=chi.period)
    kq = DCT._goi_mo_hinh("", data, k, nhac=_NHAC_PHU_LUC)
    tho = kq["tho"] if isinstance(kq.get("tho"), dict) else {}
    dong, da_bo = _loc_phu_luc(tho)
    chi.phu_luc_attachment_id = a.id
    chi.dong_phu_luc = dong
    ghi_chu = str(tho.get("_ghi_chu") or "")
    if da_bo:
        ghi_chu = (ghi_chu + " | Đã BỎ các trường mô hình tự trả về ngoài phạm vi cho phép: "
                   + ", ".join(da_bo)).strip(" |")
    chi.phu_luc_ghi_chu = (ghi_chu or kq["loi"])[:2000]
    run = AL.ghi(db, tac_vu=DCT.TAC_VU, muc=muc, dau_vao=a.checksum,
                 ket_qua=json.dumps({"so_dong": len(dong)}, ensure_ascii=False),
                 nguon=kq["nguon"], mo_hinh=kq["mo_hinh"],
                 ref=f"chi_luong:{chi.period}:{chi.lan}:phu_luc", vai_tro=vai_tro, nguoi=boi,
                 so_ban_ghi=len(dong), tokens_vao=kq["tokens_vao"], tokens_ra=kq["tokens_ra"],
                 trang_thai="cho_hau_kiem", loi=kq["loi"])
    db.flush()
    chi.phu_luc_ai_run_id = run.id
    # Nhật ký AI ghi SỐ DÒNG, không ghi tên và số tiền từng người. Nhật ký là chỗ nhiều vai trò đọc
    # được để xem máy chạy thế nào; đổ danh sách lương vào đó là mở lại đúng cánh cửa vừa đóng.
    return {"so_dong": len(dong), "da_bo_truong": da_bo, "ghi_chu_may": ghi_chu, "loi": kq["loi"]}


def _muc_ai(db: Session, vai_tro: str) -> int:
    from app.services import ai_quyen as AQ, doc_chung_tu as DCT
    muc = min(AQ.muc_cua(db, vai_tro, DCT.TAC_VU), DCT.MUC_TOI_DA)
    if muc < 1:
        raise DCT.KhongDocDuoc(f"Vai trò '{vai_tro}' không được dùng máy đọc chứng từ. "
                               "Bảng quyền AI quyết điều này, không phải màn hình.")
    return muc


def kiem_ngoai_le_con_hieu_luc() -> None:
    """Ngoại lệ phải còn trong bảng khai thì mới đọc được. Xoá khai là tắt được tính năng mà không
    phải đi tìm từng chỗ gọi – đó là lý do bảng khai nằm một chỗ."""
    from app.services import doc_chung_tu as DCT
    if LOAI_PHU_LUC not in MO_DOC_CO_CHU_KY:
        raise DCT.KhongDocDuoc(
            "Phụ lục chuyển lương chưa được mở đọc bằng máy. Mở ngoại lệ này cần chữ ký và cần sửa "
            "models/doc_chung_tu.py::MO_DOC_CO_CHU_KY – không mở được bằng một công tắc trên màn hình.")


# ====================== ĐỐI CHIẾU ======================
def tim_sepay(db: Session, chi: ChiKyLuong) -> dict | None:
    """Giao dịch tiền RA khớp số tiền UNC quanh ngày chuyển. Bằng chứng tiền đã rời tài khoản.

    Không có giao dịch KHÔNG kết luận là chưa chi: webhook có thể chưa về, hoặc công ty chuyển từ
    một tài khoản chưa nối SePay. Trả None và để phần kết luận nói rõ là thiếu tầng bằng chứng này.
    """
    if chi.so_tien_unc is None or chi.ngay_chuyen is None:
        return None
    tu = datetime.combine(chi.ngay_chuyen - timedelta(days=NGAY_TIM_SEPAY), datetime.min.time())
    den = datetime.combine(chi.ngay_chuyen + timedelta(days=NGAY_TIM_SEPAY), datetime.max.time())
    for t in db.execute(select(BankTransaction).where(
            BankTransaction.transfer_type == "out",
            BankTransaction.transaction_date >= tu,
            BankTransaction.transaction_date <= den)).scalars():
        if abs(float(t.amount or 0) - float(chi.so_tien_unc)) <= NGUONG_LAM_TRON:
            return {"sepay_id": t.sepay_id, "gateway": t.gateway, "amount": float(t.amount or 0),
                    "transaction_date": str(t.transaction_date), "reference_code": t.reference_code}
    return None


def doi_chieu(db: Session, chi: ChiKyLuong, ban: BangLuongKhoa) -> dict:
    """So lần chi này với bản khóa. QUY TẮC XÁC ĐỊNH – không hỏi mô hình ngôn ngữ câu nào ở đây."""
    rows = (ban.noi_dung or {}).get("rows") or []
    tong_ban = float(((ban.noi_dung or {}).get("totals") or {}).get("thuc_nhan") or 0)

    # ---- tầng 1 + 2: tổng ----
    tong = {"ban_khoa": tong_ban, "unc": chi.so_tien_unc,
            "lech": None if chi.so_tien_unc is None else round(float(chi.so_tien_unc) - tong_ban, 2),
            "sepay": tim_sepay(db, chi)}
    tong["khop"] = tong["lech"] is not None and abs(tong["lech"]) <= NGUONG_LAM_TRON

    # ---- tầng 3: từng người ----
    theo_ten: dict[str, list[dict]] = {}
    for r in rows:
        theo_ten.setdefault(chuan_ten(r.get("ten")), []).append(r)

    khop, lech, thieu, thua, nhap_nhang = [], [], [], [], []
    da_dung: set[int] = set()
    for d in (chi.dong_phu_luc or []):
        key = chuan_ten(d.get("ho_ten"))
        ung = theo_ten.get(key) or []
        if not ung:
            thua.append({"ho_ten": d.get("ho_ten"), "so_tien": d.get("so_tien"),
                         "ly_do": "Phụ lục có người này, bảng đã ký thì không"})
            continue
        if len(ung) > 1:
            # Hai người trùng tên thì KHÔNG đoán. Đoán sai ở đây nghĩa là báo "đã trả" cho người
            # chưa nhận tiền, và người ấy không có cách nào biết để khiếu nại.
            nhap_nhang.append({"ho_ten": d.get("ho_ten"), "ma_nv": [x.get("ma") for x in ung],
                               "ly_do": "Bảng đã ký có nhiều người cùng tên – máy không tự chọn"})
            continue
        r = ung[0]
        da_dung.add(id(r))
        can = float(r.get("thuc_nhan") or 0)
        co = d.get("so_tien")
        mot = {"ma_nv": r.get("ma"), "ho_ten": r.get("ten"), "phai_tra": can, "da_chuyen": co}
        if co is None:
            mot["ly_do"] = "Máy không đọc được số tiền dòng này – rỗng không phải số 0"
            lech.append(mot)
        elif abs(float(co) - can) <= NGUONG_LAM_TRON:
            khop.append(mot)
        else:
            mot["lech"] = round(float(co) - can, 2)
            lech.append(mot)
    for r in rows:
        if id(r) not in da_dung and (chi.dong_phu_luc or []):
            thieu.append({"ma_nv": r.get("ma"), "ho_ten": r.get("ten"),
                          "phai_tra": float(r.get("thuc_nhan") or 0),
                          "ly_do": "Bảng đã ký có người này, phụ lục thì không"})

    tung_nguoi = {"co_phu_luc": bool(chi.dong_phu_luc), "so_dong_phu_luc": len(chi.dong_phu_luc or []),
                  "so_nguoi_bang_ky": len(rows), "khop": khop, "lech": lech, "thieu": thieu,
                  "thua": thua, "nhap_nhang": nhap_nhang}

    ket_luan, ly_do = _ket_luan(tong, tung_nguoi)
    return {"tong": tong, "tung_nguoi": tung_nguoi, "ket_luan": ket_luan, "ly_do": ly_do,
            "ban_khoa": {"ban_so": ban.ban_so, "dau_van_tay": ban.dau_van_tay,
                         "khoa_boi": ban.khoa_boi, "khoa_luc": str(ban.khoa_luc)}}


def _ket_luan(tong: dict, tung_nguoi: dict) -> tuple[str, str]:
    """Đủ / một phần / lỗi. Thứ tự xét là thứ tự nghiêm trọng giảm dần, và dừng ở cái đầu tiên đúng.

    LỖI xếp trước MỘT PHẦN có chủ đích: trả thừa, trả cho người không có trong bảng, hay trùng tên
    không phân định được đều là chuyện phải có người xử lý ngay; gọi chúng là "một phần" thì chúng
    nằm chung hàng chờ với việc bình thường và sẽ nằm đó.
    """
    if tong["unc"] is None:
        return "", "Chưa đọc được số tiền trên mặt Ủy nhiệm chi – chưa đối chiếu được"
    if tung_nguoi["thua"] or tung_nguoi["nhap_nhang"]:
        return "loi", ("Phụ lục có người không nằm trong bảng đã ký, hoặc có tên không phân định được")
    if tong["lech"] is not None and tong["lech"] > NGUONG_LAM_TRON:
        return "loi", f"Số tiền chuyển đi nhiều hơn bảng đã ký {tong['lech']:,.0f} đồng"
    if any((d.get("lech") or 0) > 0 for d in tung_nguoi["lech"]):
        return "loi", "Có người nhận nhiều hơn số đã ký"
    if tung_nguoi["co_phu_luc"]:
        if tung_nguoi["thieu"] or tung_nguoi["lech"]:
            n = len(tung_nguoi["thieu"]) + len(tung_nguoi["lech"])
            return "mot_phan", f"Còn {n} người chưa nhận hoặc nhận chưa đủ"
        if not tong["khop"]:
            return "mot_phan", (f"Từng người đều khớp nhưng tổng chuyển lệch "
                                f"{tong['lech']:,.0f} đồng so với bảng đã ký")
        return "du", "Tổng khớp và từng người khớp với bản đã ký"
    # Không có phụ lục: chỉ kết luận được ở mức tổng, và phải nói ra là chỉ ở mức tổng.
    if tong["khop"]:
        return "du", ("Tổng khớp bản đã ký. CHƯA có phụ lục từng người, nên chưa trả lời được "
                      "câu 'có ai bị sót không'")
    return "mot_phan", f"Tổng chuyển thiếu {abs(tong['lech']):,.0f} đồng so với bảng đã ký"


# ====================== GHI NHẬN ĐÃ TRẢ ======================
def trang_thai_ky(db: Session, period: str) -> str:
    """Trạng thái trả tiền của CẢ KỲ, cộng từ các lần chi. Các lần chi là bản gốc; cột trên
    `payroll_runs` chỉ là bản tóm cho báo cáo đọc, và được ghi trong cùng giao dịch với nơi sinh ra
    nó – không có đường nào sửa được một trong hai mà không sửa cái kia."""
    ds = list(db.execute(select(ChiKyLuong).where(ChiKyLuong.period == period)).scalars())
    if not ds:
        return ""
    if any(c.ket_luan == "loi" for c in ds):
        return "loi_chi"
    if any(c.ket_luan == "du" for c in ds):
        return "da_tra_du"
    return "dang_chi"


def ghi_nhan(db: Session, chi: ChiKyLuong, ban: BangLuongKhoa, run: PayrollRun) -> dict:
    kq = doi_chieu(db, chi, ban)
    chi.ket_qua = kq
    chi.ket_luan = kq["ket_luan"]
    chi.doi_chieu_luc = datetime.now()
    db.flush()
    run.tra_trang_thai = trang_thai_ky(db, chi.period)
    run.tra_luc = datetime.now()
    return kq
