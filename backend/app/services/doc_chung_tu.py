"""V2 – đọc chứng từ ảnh ra số (lệnh giao việc 08/9/2026, cửa 3 của khuôn ba cửa).

Nhân viên chụp hóa đơn, máy điền sẵn số vào biểu, người sửa chỗ máy đọc sai rồi bấm xác nhận.

BỐN RÀNG BUỘC CỦA TỆP NÀY, VÀ CẢ BỐN ĐỀU CÓ PHÉP THỬ CANH

  1. KHÔNG CÓ ĐƯỜNG NÀO ĐI THẲNG VÀO BẢNG ĐÍCH. Cả tệp này chỉ có đúng một chỗ ghi vào bảng đích, và
     chỗ đó là hàm xac_nhan(), gọi đúng cửa 1 của khuôn ba cửa. Không có nhánh "tự tin thì ghi luôn",
     không có ngưỡng độ tin cậy nào mở được đường tắt. Nhóm tác vụ doc_chung_tu trong bảng quyền AI
     cao nhất là mức 2 – soạn nháp – và mã ở đây không có nhánh nào dùng mức 3 kể cả khi ai đó sửa
     bảng quyền lên mức 3.

  2. KHÔNG ĐỌC BẢNG LƯƠNG VÀ BẢNG BẢO HIỂM. Lệnh giao việc xếp chúng vào nhóm bốn loại mở trước; Chủ
     tịch quyết ngược lại ngay trong ngày. Đó là thu nhập của từng người – dữ liệu cá nhân theo Nghị
     định 13/2023 – và đưa qua mô hình ngôn ngữ là một lần chuyển dữ liệu cá nhân ra ngoài mà không
     ai trong danh sách đó đồng ý. Chặn ở tầng mã, không ở tầng cấu hình.

  3. Ô KHÔNG ĐỌC ĐƯỢC LÀ Ô RỖNG. Mô hình được lệnh để trống chứ không đoán, và tuyệt đối không điền 0.
     Sau khi mô hình trả lời, tệp này còn lọc thêm một lần: số 0 ở một ô tiền luôn bị đổi thành rỗng
     và tên ô được đưa vào danh sách "máy không đọc được". Quy tắc 4 của lệnh, và là lỗi đã làm sổ báo
     lãi 100% trên 2,65 tỷ doanh thu.

  4. MỌI LẦN ĐỌC ĐỀU CÓ VẾT, kể cả lần hỏng. Ghi một dòng vào ai_runs kèm băm của ẢNH GỐC – "chạy lại
     cùng ảnh phải ra cùng kết quả" thành điều kiểm chứng được thay vì một lời hứa.

MỘT CON SỐ TỆP NÀY SINH RA MÀ KHÔNG NƠI NÀO KHÁC SINH ĐƯỢC: tỷ lệ trường người phải sửa. Vượt 20% thì
đề xuất HẠ MỨC AI, không phải huấn luyện thêm. Đó là quyết định của Chủ tịch ngày 08/9, và nó đúng
hướng: khi máy đọc kém đi thì thứ phải giảm là mức tự chủ của máy, không phải mức chú ý của người.
"""
import base64
import json
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.doc_chung_tu import (BanDocChungTu, LOAI_CHUNG_TU, CAM_DOC_BANG_MAY, TRANG_THAI)

TAC_VU = "doc_chung_tu"
MUC_TOI_DA = 2          # soạn nháp. Không có mức cao hơn cho nhóm việc này, ở đây và ở bảng quyền.
NGUONG_HA_MUC = 0.20    # tỷ lệ trường phải sửa vượt mức này thì đề xuất hạ mức AI
BOI_BAT_THUONG = 3.0    # số tiền gấp mấy lần mức thường thì phải hỏi lại người xác nhận
ANH_HO_TRO = {"image/jpeg", "image/png", "image/gif", "image/webp"}
PDF = "application/pdf"

# Ô tiền: 0 ở đây luôn bị đọc thành "chưa có số". Một hóa đơn 0 đồng không tồn tại; một ô mờ thì có.
O_TIEN = {"tien_truoc_thue", "tien_thue", "tong_tien", "so_tien", "doanh_thu", "tien_dau",
          "cau_duong", "cong_tac_phi", "lit", "so_lit"}


class KhongDocDuoc(Exception):
    """Lỗi người dùng cần đọc được, không phải lỗi kỹ thuật."""


# ====================== ĐỌC ======================
def _kieu_anh(kieu: str, ten_tep: str) -> str:
    k = (kieu or "").split(";")[0].strip().lower()
    if k in ANH_HO_TRO or k == PDF:
        return k
    duoi = ten_tep.rsplit(".", 1)[-1].lower() if "." in ten_tep else ""
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif",
            "webp": "image/webp", "pdf": PDF}.get(duoi, "")


def _nhac_viec(loai: str) -> str:
    bo = LOAI_CHUNG_TU[loai]
    truong = "\n".join(f"  - {t}" for t in bo["truong"])
    return (
        f"Đọc {bo['ten']} trong ảnh và trả về DUY NHẤT một đối tượng JSON, không kèm lời giải thích.\n"
        f"Các khóa cần có, đúng tên này:\n{truong}\n\n"
        "Quy tắc bắt buộc:\n"
        "1. Ô nào không nhìn rõ, bị che, hoặc không có trên chứng từ thì để CHUỖI RỖNG \"\". "
        "TUYỆT ĐỐI không suy đoán, không lấy số ở ô khác, và KHÔNG BAO GIỜ điền 0 thay cho "
        "\"không đọc được\" – hai chuyện đó khác hẳn nhau và điền nhầm sẽ làm sai sổ kế toán.\n"
        "2. Số tiền ghi bằng chữ số, không dấu phân cách, không đơn vị. Ngày ghi dạng DD/MM/YYYY.\n"
        "3. Thêm khóa \"_khong_chac\": danh sách tên các ô bạn đọc được nhưng KHÔNG chắc chắn.\n"
        "4. Thêm khóa \"_ghi_chu\": một câu ngắn về chất lượng ảnh hoặc chỗ đáng ngờ, để trống nếu không có.\n"
    )


def _loc_ket_qua(loai: str, tho: dict) -> tuple[dict, list, str]:
    """Lọc lần hai ở phía ta, không tin hoàn toàn vào việc mô hình đã tuân lệnh.

    Hai việc: (a) chỉ giữ đúng các ô đã khai, bỏ mọi khóa lạ mô hình tự thêm; (b) ô tiền bằng 0 đổi
    thành RỖNG và ghi tên ô vào danh sách không đọc được. Điều (b) là chỗ quan trọng: dặn mô hình đừng
    điền 0 là một lời dặn, còn đổi 0 thành rỗng ở đây là một ràng buộc."""
    bo = LOAI_CHUNG_TU[loai]
    so, thieu = {}, []
    for t in bo["truong"]:
        v = tho.get(t)
        v = "" if v is None else str(v).strip()
        if t in O_TIEN and v not in ("",):
            try:
                if float(v.replace(",", "").replace(".", "") or 0) == 0:
                    v = ""
            except ValueError:
                pass
        if v == "":
            thieu.append(t)
        so[t] = v
    for t in (tho.get("_khong_chac") or []):
        if t in bo["truong"] and t not in thieu:
            thieu.append(t)
    return so, thieu, str(tho.get("_ghi_chu") or "")[:2000]


def _goi_mo_hinh(loai: str, data: bytes, kieu: str) -> dict:
    """Gọi mô hình. Không có khóa API thì trả về biểu RỖNG chứ không trả về số bịa.

    Biểu rỗng vẫn hữu ích: người dùng có sẵn ảnh gắn vào bản ghi và một biểu đúng cột để gõ tay, và
    nhật ký vẫn ghi rằng lần đọc này chạy mà không có mô hình."""
    if not settings.ANTHROPIC_API_KEY:
        return {"nguon": "quy_tac", "mo_hinh": "", "tho": {},
                "loi": "chưa cấu hình ANTHROPIC_API_KEY – biểu để trống, mời nhập tay",
                "tokens_vao": 0, "tokens_ra": 0}
    khoi = ({"type": "image", "source": {"type": "base64", "media_type": kieu,
                                         "data": base64.b64encode(data).decode()}}
            if kieu != PDF else
            {"type": "document", "source": {"type": "base64", "media_type": PDF,
                                            "data": base64.b64encode(data).decode()}})
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=settings.ANTHROPIC_MODEL, max_tokens=1500,
            messages=[{"role": "user", "content": [khoi, {"type": "text", "text": _nhac_viec(loai)}]}])
        text = "".join(getattr(b, "text", "") for b in msg.content).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        tho = json.loads(text)
        if not isinstance(tho, dict):
            raise ValueError("mô hình không trả về một đối tượng JSON")
        return {"nguon": "claude", "mo_hinh": settings.ANTHROPIC_MODEL, "tho": tho, "loi": "",
                "tokens_vao": getattr(msg.usage, "input_tokens", 0),
                "tokens_ra": getattr(msg.usage, "output_tokens", 0)}
    except Exception as ex:
        # Lần gọi hỏng cũng là việc phần mềm đã làm thay người, nên vẫn ghi vết và vẫn trả biểu rỗng.
        return {"nguon": "claude", "mo_hinh": settings.ANTHROPIC_MODEL, "tho": {},
                "loi": f"{type(ex).__name__}: {ex}"[:300], "tokens_vao": 0, "tokens_ra": 0}


def doc(db: Session, loai: str, ten_tep: str, data: bytes, kieu: str, boi: str, vai_tro: str,
        doi_tuong_id: str = "", phap_nhan: str = "", ky: str = "") -> BanDocChungTu:
    """Đọc một tấm ảnh chứng từ thành BẢN NHÁP. Không ghi gì vào bảng đích."""
    if loai in CAM_DOC_BANG_MAY:
        raise KhongDocDuoc(
            f"Không đọc bằng máy: {CAM_DOC_BANG_MAY[loai]}. Loại chứng từ này nhập tay, và tệp gốc "
            "vẫn lưu vào kho hồ sơ nhân sự với phân quyền riêng.")
    if loai not in LOAI_CHUNG_TU:
        raise KhongDocDuoc(f"Chưa mở đọc máy cho loại '{loai}'. Đang mở: "
                           + ", ".join(v["ten"] for v in LOAI_CHUNG_TU.values()))
    from app.services import ai_quyen as AQ
    muc = min(AQ.muc_cua(db, vai_tro, TAC_VU), MUC_TOI_DA)
    if muc < 1:
        raise KhongDocDuoc(f"Vai trò '{vai_tro}' không được dùng máy đọc chứng từ. "
                           "Bảng quyền AI quyết điều này, không phải màn hình.")
    k = _kieu_anh(kieu, ten_tep)
    if not k:
        raise KhongDocDuoc("Chỉ đọc được ảnh JPG/PNG/GIF/WEBP hoặc tệp PDF.")

    from app.services import attachments as AT, ai_log as AL
    bo = LOAI_CHUNG_TU[loai]
    a, _moi = AT.dinh_kem(db, bo["doi_tuong_tep"], doi_tuong_id or f"CHUA-GAN-{loai}", ten_tep, data,
                          kieu=k, loai="hoa_don" if "hoa_don" in loai else "chung_tu",
                          mo_ta=f"Ảnh chứng từ cho máy đọc – {bo['ten']}", boi=boi,
                          nguon="nguoi_nhap", phap_nhan=phap_nhan, ky=ky)
    # Ảnh này đã có một bản nháp đang chờ thì trả lại đúng bản đó. Người dùng tải lại vì tưởng lần
    # trước hỏng là chuyện thường ngày; sinh bản thứ hai là mời người xác nhận ghi hai lần một hóa đơn.
    dang_co = db.execute(select(BanDocChungTu).where(
        BanDocChungTu.loai == loai, BanDocChungTu.dang_cho == a.checksum)).scalars().first()
    if dang_co is not None:
        return dang_co

    kq = _goi_mo_hinh(loai, data, k)
    so, thieu, ghi_chu = _loc_ket_qua(loai, kq["tho"])
    run = AL.ghi(db, tac_vu=TAC_VU, muc=muc, dau_vao=a.checksum,
                 ket_qua=json.dumps(so, ensure_ascii=False), nguon=kq["nguon"], mo_hinh=kq["mo_hinh"],
                 ref=f"tep:{a.id}", vai_tro=vai_tro, nguoi=boi, so_ban_ghi=1,
                 tokens_vao=kq["tokens_vao"], tokens_ra=kq["tokens_ra"],
                 trang_thai="cho_hau_kiem", loi=kq["loi"])
    db.flush()
    b = BanDocChungTu(loai=loai, bo_nap=bo["bo_nap"], attachment_id=a.id, checksum_anh=a.checksum,
                      ai_run_id=run.id, mo_hinh=kq["mo_hinh"], so_may_doc=so,
                      truong_khong_doc_duoc=thieu,
                      ghi_chu_may=(ghi_chu or kq["loi"])[:2000],
                      trang_thai="nhap", dang_cho=a.checksum, boi=boi)
    db.add(b); db.flush()
    return b


# ====================== XÁC NHẬN ======================
def _chuan(v) -> str:
    return " ".join(str(v if v is not None else "").split()).strip()


def bat_thuong(db: Session, loai: str, so_tien: float) -> str:
    """Số này có gấp nhiều lần mức thường của cùng loại chứng từ không.

    Ngưỡng 3 lần là quyết định của Chủ tịch ngày 08/9. So với TRUNG VỊ chứ không so với trung bình:
    một hóa đơn 900 triệu lọt vào giữa các hóa đơn vài triệu sẽ kéo trung bình lên đủ để chính nó
    trông bình thường, và cả những cái sau nó cũng vậy."""
    if so_tien <= 0:
        return ""
    tu = date.today() - timedelta(days=90)
    ds = []
    for b in db.execute(select(BanDocChungTu).where(
            BanDocChungTu.loai == loai, BanDocChungTu.trang_thai == "da_xac_nhan",
            BanDocChungTu.luc >= datetime.combine(tu, datetime.min.time()))).scalars():
        for k in ("tong_tien", "so_tien", "doanh_thu"):
            v = (b.so_da_sua or {}).get(k) or (b.so_may_doc or {}).get(k)
            try:
                n = float(str(v).replace(",", "").replace(".", "")) if v else 0
            except ValueError:
                n = 0
            if n > 0:
                ds.append(n); break
    if len(ds) < 5:          # chưa đủ nền để nói cái gì là bất thường thì không nói
        return ""
    ds.sort()
    tv = ds[len(ds) // 2]
    if tv > 0 and so_tien >= tv * BOI_BAT_THUONG:
        return (f"Số tiền {so_tien:,.0f} đ gấp {so_tien/tv:.1f} lần mức thường của loại chứng từ này "
                f"({tv:,.0f} đ trong 90 ngày qua). Nhìn lại ảnh gốc trước khi xác nhận.")
    return ""


def xac_nhan(db: Session, b: BanDocChungTu, row: dict, boi: str, vai_tro: str) -> dict:
    """CHỖ DUY NHẤT trong phân hệ này ghi vào bảng đích – và nó đi đúng cửa 1, không có đường riêng.

    Ai bấm nút này chịu trách nhiệm về con số y như người gõ tay. Vì vậy quyền bấm là quyền của phòng
    SỞ HỮU con số, và người vận hành mô hình (CNTT) cố ý không có quyền này: người chạy mô hình mà
    cũng là người xác nhận kết quả của nó thì không còn ai đứng ngoài để nói mô hình đọc sai."""
    from app.services.intake import duoc_xac_nhan_anh, nhap_mot_dong
    if b.trang_thai != "nhap":
        raise KhongDocDuoc(f"Bản đọc này đã ở trạng thái '{TRANG_THAI.get(b.trang_thai, b.trang_thai)}'.")
    if not duoc_xac_nhan_anh(b.bo_nap, vai_tro):
        raise KhongDocDuoc(
            f"Vai trò '{vai_tro}' không được xác nhận số cho '{b.bo_nap}'. Xác nhận là hành vi nhập "
            "liệu: người bấm chịu trách nhiệm về con số, nên phải là người của phòng sở hữu con số.")

    row = {k: v for k, v in (row or {}).items() if k in LOAI_CHUNG_TU[b.loai]["truong"]}
    da_sua = [k for k in LOAI_CHUNG_TU[b.loai]["truong"]
              if _chuan(row.get(k)) != _chuan((b.so_may_doc or {}).get(k))]

    kq = nhap_mot_dong(db, b.bo_nap, row, boi, cua="doc_anh", tac_nhan=f"ai_run:{b.ai_run_id}")
    if not kq.get("da_ghi"):
        # Không ghi được thì bản nháp Ở NGUYÊN trạng thái chờ. Đánh dấu đã xử lý một dòng chưa vào
        # được hệ thống là cách chắc chắn nhất để nó biến mất khỏi hàng chờ mà không ai biết.
        return {**kq, "ban_doc_id": b.id, "truong_da_sua": da_sua}

    b.so_da_sua = row
    b.truong_da_sua = da_sua
    b.trang_thai = "da_xac_nhan"
    b.dang_cho = None
    b.xac_nhan_boi = boi
    b.xac_nhan_luc = datetime.now()
    b.ket_qua_ghi = str(kq.get("ket_qua") or "")[:300]
    b.intake_run_id = kq.get("run_id")
    if b.ai_run_id:
        from app.models.core import AiRun
        r = db.get(AiRun, b.ai_run_id)
        if r is not None:
            r.trang_thai = "da_sua" if da_sua else "da_duyet"
            r.hau_kiem_boi = boi
            r.hau_kiem_luc = datetime.now()
            r.hau_kiem_ghi_chu = (f"Người xác nhận sửa {len(da_sua)}/{len(LOAI_CHUNG_TU[b.loai]['truong'])} ô: "
                                  + ", ".join(da_sua))[:300] if da_sua else "Xác nhận nguyên số máy đọc"
    db.flush()
    return {**kq, "ban_doc_id": b.id, "truong_da_sua": da_sua,
            "so_o_da_sua": len(da_sua), "so_o": len(LOAI_CHUNG_TU[b.loai]["truong"])}


def bo(db: Session, b: BanDocChungTu, ly_do: str, boi: str) -> BanDocChungTu:
    """Bỏ một bản nháp. Bắt buộc có lý do: 'máy đọc sai' và 'chứng từ này không dùng' là hai chuyện
    khác nhau, và chỉ cái thứ nhất mới là tín hiệu về chất lượng mô hình."""
    if b.trang_thai != "nhap":
        raise KhongDocDuoc("Chỉ bỏ được bản còn đang chờ xác nhận.")
    if not str(ly_do or "").strip():
        raise KhongDocDuoc("Phải ghi lý do bỏ.")
    b.trang_thai = "bo"
    b.dang_cho = None
    b.ly_do_bo = str(ly_do).strip()[:300]
    b.xac_nhan_boi = boi
    b.xac_nhan_luc = datetime.now()
    db.flush()
    return b


# ====================== ĐO CHẤT LƯỢNG ======================
def hang_cho(db: Session, loai: str = "", boi: str = "") -> list[BanDocChungTu]:
    q = select(BanDocChungTu).where(BanDocChungTu.trang_thai == "nhap")
    if loai: q = q.where(BanDocChungTu.loai == loai)
    if boi: q = q.where(BanDocChungTu.boi == boi)
    return list(db.execute(q.order_by(desc(BanDocChungTu.luc))).scalars())


def ty_le_sua(db: Session, loai: str = "", ngay: int = 30) -> dict:
    """Tỷ lệ Ô mà người phải sửa lại sau khi máy đọc.

    Đếm theo Ô chứ không theo BẢN: một bản sai một ô và một bản sai chín ô là hai mức chất lượng khác
    hẳn nhau, mà đếm theo bản thì cả hai đều là 'một bản bị sửa'.

    Vượt 20% là đề xuất HẠ MỨC, không phải huấn luyện thêm – quyết định của Chủ tịch 08/9. Chỉ tính
    trên các bản do MÔ HÌNH đọc: lần chạy không có khóa API trả biểu rỗng, người gõ toàn bộ, tính vào
    thì tỷ lệ luôn là 100% và con số mất hết ý nghĩa."""
    tu = datetime.now() - timedelta(days=ngay)
    q = select(BanDocChungTu).where(BanDocChungTu.trang_thai == "da_xac_nhan",
                                    BanDocChungTu.luc >= tu, BanDocChungTu.mo_hinh != "")
    if loai: q = q.where(BanDocChungTu.loai == loai)
    ban = list(db.execute(q).scalars())
    theo_loai: dict[str, dict] = {}
    tong_o = tong_sua = 0
    for b in ban:
        n = len(LOAI_CHUNG_TU.get(b.loai, {}).get("truong", ()))
        s = len(b.truong_da_sua or [])
        d = theo_loai.setdefault(b.loai, {"ten": LOAI_CHUNG_TU.get(b.loai, {}).get("ten", b.loai),
                                          "so_ban": 0, "so_o": 0, "so_o_sua": 0})
        d["so_ban"] += 1; d["so_o"] += n; d["so_o_sua"] += s
        tong_o += n; tong_sua += s
    for d in theo_loai.values():
        d["ty_le"] = round(d["so_o_sua"] / d["so_o"], 4) if d["so_o"] else None
        d["de_xuat_ha_muc"] = bool(d["ty_le"] is not None and d["so_ban"] >= 10
                                   and d["ty_le"] > NGUONG_HA_MUC)
    ty_le = round(tong_sua / tong_o, 4) if tong_o else None
    return {
        "so_ngay": ngay, "so_ban": len(ban), "so_o": tong_o, "so_o_sua": tong_sua,
        "ty_le": ty_le, "nguong_ha_muc": NGUONG_HA_MUC, "theo_loai": theo_loai,
        # Dưới 10 bản thì một bản xấu cũng đủ vượt ngưỡng. Nói "chưa đủ dữ liệu" chứ không im lặng
        # trả về một tỷ lệ trông như đã đo được.
        "du_du_lieu": len(ban) >= 10,
        "de_xuat_ha_muc": bool(ty_le is not None and len(ban) >= 10 and ty_le > NGUONG_HA_MUC),
        "ghi_chu": ("Tỷ lệ ô người phải sửa. Vượt 20% thì hạ mức AI, không phải huấn luyện thêm."
                    if len(ban) >= 10 else
                    f"Mới {len(ban)} bản có mô hình đọc – chưa đủ để kết luận (cần từ 10 bản)."),
    }


def ra(b: BanDocChungTu) -> dict:
    bo = LOAI_CHUNG_TU.get(b.loai, {})
    return {"id": b.id, "loai": b.loai, "ten_loai": bo.get("ten", b.loai), "bo_nap": b.bo_nap,
            "attachment_id": b.attachment_id, "mo_hinh": b.mo_hinh,
            "so_may_doc": b.so_may_doc or {}, "truong_khong_doc_duoc": b.truong_khong_doc_duoc or [],
            "ghi_chu_may": b.ghi_chu_may, "trang_thai": b.trang_thai,
            "ten_trang_thai": TRANG_THAI.get(b.trang_thai, b.trang_thai),
            "truong_da_sua": b.truong_da_sua or [], "xac_nhan_boi": b.xac_nhan_boi,
            "ket_qua_ghi": b.ket_qua_ghi, "ly_do_bo": b.ly_do_bo,
            "boi": b.boi, "luc": b.luc.isoformat() if b.luc else ""}


def meta() -> dict:
    return {
        "loai": [{"ma": k, "ten": v["ten"], "bo_nap": v["bo_nap"], "truong": list(v["truong"])}
                 for k, v in LOAI_CHUNG_TU.items()],
        "cam_doc": [{"ma": k, "ly_do": v} for k, v in CAM_DOC_BANG_MAY.items()],
        "muc_toi_da": MUC_TOI_DA,
        "nguyen_tac": ("Máy soạn nháp, người xác nhận. Số máy đọc KHÔNG vào bất kỳ báo cáo nào cho tới "
                       "khi có một lần bấm của người, và lần bấm đó đi đúng cửa nhập tay."),
    }
