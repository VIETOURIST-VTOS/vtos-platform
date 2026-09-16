"""Báo cáo tự động trên màn hình – lọc theo NGƯỜI ĐANG ĐĂNG NHẬP.

Chỗ chặn nằm ở đây chứ không ở màn hình: màn hình chỉ vẽ thứ máy chủ trả về, nên nếu máy chủ trả về
báo cáo của mọi phòng rồi để giao diện lọc thì ai mở công cụ nhà phát triển cũng đọc được hết.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import current_user, robot_auth
from app.db.session import get_db
from app.models.core import User
from app.services import bao_cao_phong as BP

router = APIRouter(prefix="/api/v1/bao-cao", tags=["bao-cao-tu-dong"])

# Một câu duy nhất cho mọi cửa: người dùng gặp hai lời giải thích khác nhau cho cùng một lần chặn
# thì tưởng là hai lỗi khác nhau.
_NGOAI_PHAM_VI = ("Báo cáo này không thuộc phạm vi của vai trò anh/chị. Trưởng phòng xem báo cáo "
                  "phòng mình; báo cáo toàn công ty dành cho Chủ tịch, Tổng giám đốc và Ban Kiểm soát.")


def _grants_an_toan(db, u):
    """Ngoại lệ đang có của người này – để màn hình NÓI RA rằng phạm vi đang rộng hơn chức danh.

    Nói ra chứ không im lặng mở: một người thấy báo cáo phòng khác mà không hiểu vì sao thì hoặc
    tưởng hệ thống lỗi, hoặc tưởng ai cũng xem được – cả hai đều tệ hơn một dòng chữ giải thích."""
    from app.services import access as AC
    try:
        return [g for g in AC._grants(db, u) if g.kind == "capability"]
    except Exception:      # noqa
        return []


@router.get("/pham-vi")
def pham_vi(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Các báo cáo người này mở được. Rỗng = màn hình nói rõ 'chưa có báo cáo nào dành cho vai trò
    của anh/chị', chứ không hiện một trang trắng."""
    ds = BP.pham_vi_cho_nguoi(db, u)
    ten = {BP.TOAN_CTY: "Toàn công ty", **{k: v["ten"] for k, v in BP.PHONG.items()}}
    return {"pham_vi": [{"ma": p, "ten": ten[p]} for p in ds],
            "ky": [{"ma": k, "ten": v} for k, v in BP.TEN_KY.items()],
            "vai_tro": u.role,
            "mo_rong_theo_nguoi": BP.NANG_LUC_MOI_PHONG in
                                  [g.value for g in _grants_an_toan(db, u)]}


@router.get("")
def xem(pham_vi: str = BP.TOAN_CTY, kind: str = "ngay", ngay: str = "",
        u: User = Depends(current_user), db: Session = Depends(get_db)):
    if pham_vi not in BP.pham_vi_cho_nguoi(db, u):
        # Nói rõ là KHÔNG THUỘC PHẠM VI, không nói "không tồn tại": người dùng cần biết mình đang
        # đứng sai chỗ chứ không phải nghi hệ thống hỏng.
        raise HTTPException(403, _NGOAI_PHAM_VI)
    try:
        moc = date.fromisoformat(ngay) if ngay else None
        return BP.bao_cao(db, kind, pham_vi, moc)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/ban-luu")
def ban_luu_danh_sach(pham_vi: str = BP.TOAN_CTY, kind: str = "",
                      u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Các kỳ ĐÃ CHỤP của một phạm vi – mới nhất trước. Chỉ liệt kê, không mở nội dung.

    Cùng hàng rào phạm vi với báo cáo đang chạy: bản lưu là cùng những con số ấy, chỉ khác thời
    điểm. Nới hàng rào ở đây là mở toàn bộ lịch sử cho người không được xem hiện tại.
    """
    if pham_vi not in BP.pham_vi_cho_nguoi(db, u):
        raise HTTPException(403, _NGOAI_PHAM_VI)
    from app.models.bao_cao_luu import BaoCaoLuu
    from sqlalchemy import select
    q = select(BaoCaoLuu).where(BaoCaoLuu.pham_vi == pham_vi)
    if kind:
        q = q.where(BaoCaoLuu.kind == kind)
    rows = db.execute(q.order_by(BaoCaoLuu.tao_luc.desc()).limit(200)).scalars().all()
    return {"pham_vi": pham_vi,
            "rows": [{"kind": r.kind, "kind_ten": BP.TEN_KY.get(r.kind, r.kind), "ky": r.ky,
                      "tu": r.tu, "den": r.den, "so_viec_do": r.so_viec_do,
                      "so_can_ra_soat": r.so_can_ra_soat, "so_chua_co_so": r.so_chua_co_so,
                      "tao_boi": r.tao_boi, "tao_luc": r.tao_luc} for r in rows]}


@router.get("/ban-luu/{kind}/{ky}")
def ban_luu_mot_ky(kind: str, ky: str, pham_vi: str = BP.TOAN_CTY,
                   u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Bảng chỉ tiêu ĐÚNG NHƯ LÚC CHỤP – kể cả cách tính của từng dòng lúc ấy.

    Không có bản lưu thì trả 404 kèm lời giải thích, KHÔNG tính tạm một bản mới. Tính tạm là cách
    người ta hỏi 'cuối tháng trước thế nào' và nhận về số của hôm nay mà không hề biết.
    """
    if pham_vi not in BP.pham_vi_cho_nguoi(db, u):
        raise HTTPException(403, _NGOAI_PHAM_VI)
    r = BP.ban_luu(db, kind, ky, pham_vi)
    if r is None:
        raise HTTPException(404, f"Chưa chụp bản lưu {kind} kỳ {ky} cho phạm vi này. Bản lưu do "
                                 f"lịch tự động chụp; kỳ chưa tới hoặc lịch chưa chạy thì chưa có, "
                                 f"và hệ thống KHÔNG tính tạm một bản mới thay vào.")
    return {"kind": r.kind, "kind_ten": BP.TEN_KY.get(r.kind, r.kind), "ky": r.ky,
            "pham_vi": r.pham_vi, "pham_vi_ten": r.pham_vi_ten, "tu": r.tu, "den": r.den,
            "chi_tieu": r.chi_tieu, "markdown": r.markdown,
            "so_viec_do": r.so_viec_do, "so_can_ra_soat": r.so_can_ra_soat,
            "so_chua_co_so": r.so_chua_co_so, "tao_boi": r.tao_boi, "tao_luc": r.tao_luc,
            "ban_chup": True}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# TC-39 · CỬA CHO LỊCH TỰ ĐỘNG CHỤP BẢN LƯU
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Trước vòng này `bao_cao_phong.luu()` đã có đủ và chạy đúng — NHƯNG KHÔNG CÓ ĐƯỜNG NÀO GỌI TỚI
# NÓ. Cả bảng `bao_cao_luu` vì thế rỗng từ đầu, và mọi chỉ tiêu "số tại một thời điểm" (tour đang
# bán, tour chờ quyết toán) không có lấy một kỳ quá khứ nào để vẽ xu hướng.
#
# Đây là kiểu việc còn thiếu tệ nhất: không có lỗi nào, không có màn hình nào báo đỏ, chỉ có một
# cái bảng rỗng mà ai nhìn cũng nghĩ "chắc chưa tới lúc". Và mỗi tháng trôi qua là mất thêm một kỳ
# KHÔNG BAO GIỜ lấy lại được — khác hẳn doanh thu, vốn cộng lại sổ quyết toán lúc nào cũng ra.
#
# XÁC THỰC BẰNG ROBOT_TOKEN, giống mọi đường robot đã có (/robot/inbox/check, /tu-dong/bao-cao).
# KHÔNG dựng thêm một kiểu xác thực thứ ba cho riêng cửa này: mỗi kiểu xác thực là một chỗ phải
# canh, và cái yếu nhất quyết định mức an toàn của cả hệ thống.
@router.post("/chup", dependencies=[Depends(robot_auth)])
def chup(kind: str = "thang", ngay: str = "", db: Session = Depends(get_db)):
    """Chụp bản lưu của kỳ ĐANG CHỨA `ngay` (mặc định: hôm nay), cho mọi phạm vi.

    LỊCH GỌI VÀO ĐÂY:
      · tháng — 00:30 ngày 1 hằng tháng, với ngay = ngày cuối tháng trước
      · tuần  — 00:30 thứ Hai, với ngay = Chủ nhật vừa rồi
      · ngày  — 00:30 mỗi ngày, với ngay = hôm qua

    Vì sao lịch phải TRUYỀN NGÀY vào chứ không để mặc định: chạy lúc 00:30 ngày 1 mà không truyền
    ngày thì `khoang("thang")` trả về THÁNG MỚI — tức là chụp một tháng mới đi được nửa tiếng, rồi
    ghi đè lên đúng ô đáng ra phải chứa tháng vừa đóng. Một dòng cấu hình lịch sai chỗ này là hỏng
    vĩnh viễn số liệu của kỳ ấy, nên hàm này để `ngay` ra ngoài cho lịch nói rõ ý định.

    Chạy lại cùng một kỳ thì ĐÈ, nhờ khoá (kind, ky, pham_vi) — nên chạy bù an toàn, và gọi hai
    lần không sinh hai bản. Nhưng chạy bù MUỘN không cứu được chỉ tiêu tồn kho: xem
    `services/xu_huong.chup_kip_han`, chỗ đọc sẽ bỏ qua bản chụp muộn thay vì dùng một con số của
    tháng khác. Cửa này KHÔNG tự chặn chạy muộn, vì bản lưu vẫn có giá trị cho các chỉ tiêu dòng
    chảy và cho việc đối chiếu — chặn ở đây là vứt luôn cả phần đúng.
    """
    if kind not in BP.TEN_KY:
        raise HTTPException(422, f"Kỳ phải là một trong {list(BP.TEN_KY)}")
    try:
        moc = date.fromisoformat(ngay) if ngay else None
    except ValueError:
        raise HTTPException(422, f"Ngày '{ngay}' không đúng dạng YYYY-MM-DD")
    kq = BP.luu(db, kind, moc, boi="lich")
    # Phạm vi hỏng KHÔNG làm cả mẻ thất bại, nhưng PHẢI hiện ra trong kết quả trả về: lịch tự động
    # chỉ đọc mã trạng thái, nên một mẻ "thành công" mà thiếu ba phòng thì không ai biết.
    return {**kq,
            "message": (f"Đã chụp {len(kq['da_luu'])} phạm vi cho kỳ {kq['ky']}"
                        + (f"; {len(kq['hong'])} phạm vi lỗi" if kq["hong"] else ""))}
