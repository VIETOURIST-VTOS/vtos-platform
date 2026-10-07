"""MỘT CHỖ GHI SỔ LÔ NẠP — để bộ đối chiếu K5 không còn vùng mù.

Bối cảnh, đo trên hệ thật: sổ `intake_runs` có ĐÚNG MỘT dòng (11 dòng bằng lái xe) trong khi cùng
tháng ấy 25.728 bút toán đã vào sổ qua bộ nạp MISA — một bộ nạp không ghi nhật ký lô. Lô nạp lớn
nhất hệ thống từng có là lô mà bộ đối chiếu lô không hề biết là có tồn tại. Đếm hết thì có MƯỜI MỘT
cửa nạp hàng loạt và đúng MỘT cửa ghi sổ.

`ks_nap_lo` đã tự nói ra vùng mù ấy từ 09/9/2026 và mở một phát hiện cho mỗi cửa. Vòng này bịt lại:
mỗi cửa gọi `ghi_lo` đúng một lần, ngay trước khi trả kết quả.

──────────────────────────────────────────────────────────────────────────────────────────────
BA LUẬT, và mỗi luật là một chỗ đã sai ở đâu đó rồi
──────────────────────────────────────────────────────────────────────────────────────────────

1. ĐẲNG THỨC PHẢI ĐÚNG: `so_dong = da_nap + bo_qua_da_co + dong_loi`. Đó chính là phép đối chiếu
   K5 sẽ chạy. Ghi bốn con số không cộng lại được thì mỗi lần nạp sinh ra một ngoại lệ đỏ, và một
   bảng ngoại lệ toàn báo sai là bảng không ai đọc nữa — tệ hơn là không ghi gì. Nên hàm này KIỂM
   đẳng thức ngay lúc ghi và ghi lời khai vào `ket_qua` khi lệch, thay vì để K5 phát hiện sau.

2. RỖNG ≠ 0. Ô tiền để TRỐNG nghĩa là "cửa này không đo được tiền"; số 0 nghĩa là "đo được và bằng
   không". `ks_nap_lo.bon_so_tien` phân biệt đúng hai thứ đó, nên điền 0 cho một cửa không đo được
   tiền sẽ làm nó báo thiếu tiền ở mọi lô đi qua cửa ấy.

3. GHI SỔ KHÔNG ĐƯỢC LÀM HỎNG LẦN NẠP. Nạp dữ liệu là việc chính; ghi sổ là việc quan sát. Một lỗi
   trong phần quan sát mà làm đổ cả lô nạp là đánh đổi sai. Nên toàn bộ thân hàm nằm trong `try`
   và nuốt lỗi của chính nó — cùng hình với lớp ghi sự kiện kỹ thuật ở `main.py`.

Hàm KHÔNG commit: nó `flush` và để lần commit của chính cửa nạp mang dòng sổ đi cùng. Ghi sổ mà
commit riêng thì lô nạp hỏng giữa chừng vẫn để lại một dòng sổ nói rằng nó đã chạy xong.
"""
import hashlib
import json
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.intake import IntakeRun


def _bam(dau_vao) -> str:
    """Mã băm của nội dung đã nạp — trả lời được “lần nạp hôm đó đúng là tệp này chứ không phải tệp
    đã sửa sau đó”. Nhận cả bytes (tệp gốc) lẫn danh sách dòng đã đọc."""
    if dau_vao is None:
        return ""
    try:
        if isinstance(dau_vao, (bytes, bytearray)):
            return hashlib.sha256(bytes(dau_vao)).hexdigest()
        noi_dung = json.dumps(dau_vao, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(noi_dung.encode("utf-8")).hexdigest()
    except Exception:      # noqa
        return ""


def ghi_lo(db: Session, *, loai: str, so_dong: int, da_nap: int, bo_qua_da_co: int = 0,
           dong_loi: int = 0, ten_tep: str = "", boi: str = "", nguon: str = "he_thong",
           tac_nhan: str = "", tong_tien_tep=None, tong_tien_da_nap=None, tong_tien_bo_qua=None,
           tong_tien_loi=None, cot_tien=None, dau_vao=None, ket_qua=None) -> int | None:
    """Ghi MỘT dòng nhật ký lô. Trả id của dòng, hoặc None nếu không ghi được.

    Mọi cửa nạp hàng loạt gọi hàm này đúng một lần, ngay trước khi trả kết quả. Không gọi trong
    vòng lặp: một lô là MỘT dòng sổ, còn chi tiết từng dòng thuộc về bảng nghiệp vụ.
    """
    try:
        so_dong = int(so_dong or 0); da_nap = int(da_nap or 0)
        bo_qua_da_co = int(bo_qua_da_co or 0); dong_loi = int(dong_loi or 0)
        kq = dict(ket_qua or {})
        lech = so_dong - (da_nap + bo_qua_da_co + dong_loi)
        if lech:
            # Nói ra ngay tại chỗ ghi, đừng để K5 phải đoán. Dòng này là chỗ người sửa sau đọc được
            # "cửa nào khai bốn con số không cộng lại được".
            kq["canh_bao_dang_thuc"] = (f"{so_dong} dòng nhưng cộng lại ra "
                                        f"{da_nap + bo_qua_da_co + dong_loi} (lệch {lech}) – "
                                        f"bốn con số của cửa “{loai}” chưa phủ hết mọi dòng")
        r = IntakeRun(
            loai=loai[:40], ten_tep=(ten_tep or "")[:200], nguon=(nguon or "he_thong")[:40],
            tac_nhan=(tac_nhan or boi or "")[:80], so_dong=so_dong, da_nap=da_nap,
            bo_qua_da_co=bo_qua_da_co, dong_loi=dong_loi,
            tong_tien_tep=None if tong_tien_tep is None else round(float(tong_tien_tep), 2),
            tong_tien_da_nap=None if tong_tien_da_nap is None else round(float(tong_tien_da_nap), 2),
            tong_tien_bo_qua=None if tong_tien_bo_qua is None else round(float(tong_tien_bo_qua), 2),
            tong_tien_loi=None if tong_tien_loi is None else round(float(tong_tien_loi), 2),
            cot_tien=list(cot_tien) if cot_tien else None,
            dau_vao_hash=_bam(dau_vao),
            ket_qua=json.dumps(kq, ensure_ascii=False, default=_json_an_toan)[:8000],
            boi=(boi or "")[:50], luc=datetime.now())
        db.add(r); db.flush()
        return r.id
    except Exception:      # noqa – ghi sổ hỏng KHÔNG được làm hỏng lần nạp
        return None


def _json_an_toan(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return str(v)
