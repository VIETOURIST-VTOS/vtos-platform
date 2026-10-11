"""Báo cáo tự động trên màn hình – lọc theo NGƯỜI ĐANG ĐĂNG NHẬP.

Chỗ chặn nằm ở đây chứ không ở màn hình: màn hình chỉ vẽ thứ máy chủ trả về, nên nếu máy chủ trả về
báo cáo của mọi phòng rồi để giao diện lọc thì ai mở công cụ nhà phát triển cũng đọc được hết.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles, robot_auth
from app.db.session import get_db
from app.models.core import User
from app.services import bao_cao_phong as BP
from app.services import nho_tam as NHO
# Cùng danh sách XEM với cửa kế hoạch: hai cửa nói về cùng một con số chỉ tiêu.
from app.api.v1.ke_hoach import XEM as KQ_XEM

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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BD-1 · BÀN LÀM VIỆC CỦA MỘT PHÒNG — gắn vào ĐÚNG tiền tố này, cố ý
# ══════════════════════════════════════════════════════════════════════════════════════════════
# `so_con_no.py` đã ghi một bài học ngược lại: đừng gắn cửa mới vào một tiền tố rộng hơn người
# dùng của nó, vì phần dôi ra VẪN LÀ QUYỀN ĐÃ CẤP. Bài học ấy đúng, và nó KHÔNG áp vào đây —
# người xem bàn làm việc của một phòng đúng bằng người xem bảng chỉ tiêu của phòng ấy, không
# thừa một ai. Dựng một tiền tố thứ hai cho cùng một tập người là dựng hai hàng rào phải canh
# cho một cánh cửa, và ngày nào siết một bên quên bên kia thì chính là lỗ.
#
# HÀNG RÀO DÙNG LẠI NGUYÊN VĂN `pham_vi_cho_nguoi`: cùng một câu hỏi, cùng một câu trả lời, cùng
# một lời từ chối. Người dùng gặp hai lời giải thích khác nhau cho cùng một lần chặn thì tưởng là
# hai lỗi khác nhau.
#
# KHÔNG NHỚ TẠM. Đây là DANH SÁCH VIỆC PHẢI LÀM: người vừa xử lý xong một hồ sơ bấm lại mà nó vẫn
# nằm đó thì họ tưởng bấm hụt, và sẽ bấm lần nữa. Cùng lý lẽ với `/api/v1/so-con-no`.
@router.get("/ban-lam-viec")
def ban_lam_viec(phong: str = "", u: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    """Việc cần làm của một phòng: các hàng đợi đã có, gom về một chỗ.

    Chỉ đọc. Không duyệt, không xác nhận, không đóng sổ — mọi ô chỉ dẫn sang màn hình nguồn, nơi
    quyền và quy trình đã có chủ.
    """
    from app.services import ban_lam_viec as BLV
    if phong not in BP.pham_vi_cho_nguoi(db, u):
        raise HTTPException(403, _NGOAI_PHAM_VI)
    return BLV.ban(db, phong)


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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# TC-43 · MỘT LỊCH DUY NHẤT — CỬA CHO LỊCH TỰ ĐỘNG GỌI MỖI NGÀY MỘT LẦN
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Cửa /chup ở trên đòi lịch tự truyền `kind` và `ngay`, và chú thích của chính nó cảnh báo rằng gõ
# sai ô ngày là hỏng vĩnh viễn số liệu của kỳ ấy. Cảnh báo đúng — nhưng nó đặt phần DỄ SAI NHẤT
# vào một ô cấu hình nằm ngoài kho mã, nơi không bộ kiểm nào canh và sai thì im lặng. Ba lịch là
# ba ô như thế.
#
# Cửa này đảo lại: lịch chỉ còn phải biết MỘT việc — gọi mỗi ngày một lần, không tham số. Việc
# "hôm nay là kỳ gì, mốc ngày nào" chuyển vào services/lich_chup.ky_den_han, nơi test_tc43 canh
# từng trường hợp biên: mùng 1, thứ Hai, mùng 1 rơi đúng thứ Hai, và mốc qua đầu năm.
#
# /chup CŨ GIỮ NGUYÊN, không bỏ: nó là cửa CHẠY BÙ THỦ CÔNG cho một kỳ cũ, và việc ấy phải nói rõ
# kỳ nào — đúng chỗ để người gọi tự truyền ngày.
@router.post("/chup-hom-nay", dependencies=[Depends(robot_auth)])
def chup_hom_nay(db: Session = Depends(get_db)):
    """Chụp mọi kỳ ĐẾN HẠN hôm nay. Lịch gọi 00:30 mỗi ngày, không truyền gì cả.

    MỘT KỲ HỎNG KHÔNG ĐƯỢC LÀM CHẾT NHỮNG KỲ CÒN LẠI. Ngày 1 rơi đúng thứ Hai thì có ba kỳ phải
    chụp, và ba kỳ ấy là ba câu hỏi khác nhau về cùng một ngày cuối — mất kỳ nào là mất vĩnh viễn
    kỳ ấy, vì chỉ tiêu tồn kho không tính lại được. Nên mỗi kỳ bọc try riêng, và kỳ hỏng hiện ra ở
    `hong` chứ không ném lỗi ra ngoài.

    Mã trạng thái vẫn 200 kể cả khi có kỳ hỏng — nhưng `so_ky_hong` > 0 nói rõ, và lịch tự động nên
    đọc trường ấy. Trả 500 thì n8n báo đỏ và người ta chạy lại cả mẻ, ghi đè lên những kỳ VỪA chụp
    xong đúng — tức là lấy một kỳ hỏng đổi lấy ba kỳ hỏng.
    """
    from app.services import lich_chup as LC
    ra, hong = [], []
    for kind, moc in LC.ky_den_han():
        try:
            kq = BP.luu(db, kind, moc, boi="lich")
            ra.append({"kind": kind, "moc": moc.isoformat(), "ky": kq["ky"],
                       "so_pham_vi": len(kq["da_luu"]), "pham_vi_hong": kq["hong"]})
        except Exception as ex:      # noqa – xem chú thích trên: một kỳ hỏng không kéo theo kỳ khác
            hong.append({"kind": kind, "moc": moc.isoformat(), "ly_do": str(ex)[:300]})
    return {"da_chup": ra, "hong": hong,
            "so_ky_hong": len(hong),
            "vi_sao": LC.mo_ta(),
            "message": (f"Đã chụp {len(ra)} kỳ"
                        + (f"; {len(hong)} kỳ lỗi" if hong else ""))}

# ══════════════════════════════════════════════════════════════════════════════════════════════
# TC-44 · KẾT QUẢ KINH DOANH — cửa riêng cho khối hai biểu đồ của màn hình Chủ tịch
# ══════════════════════════════════════════════════════════════════════════════════════════════
# CỬA RIÊNG chứ không nhét vào /dashboard, và đó là điều đáng nói: khối này có ô chọn kỳ, nên mỗi
# lần anh Tuấn bấm sang Quý là màn hình phải đi lấy số mới. Nếu số nằm trong /dashboard thì mỗi lần
# bấm là tải lại TOÀN BỘ bảng điều hành — hàng chục truy vấn cho một khối đổi kỳ.
#
# Danh sách vai trò lấy ĐÚNG danh sách của /ke-hoach (XEM): hai chỗ nói về cùng một con số chỉ tiêu,
# và mở rộng một chỗ mà quên chỗ kia là để lộ chỉ tiêu qua đường vòng.
# TC-64 · CHỖ NHỚ NĂM PHÚT — anh Tuấn 18/9/2026: "kiểm tra lý do load rất chậm".
#
# Đo trên bản chạy thật: cửa này mất 1,7–2,3 giây MỖI lần, không lần nào nhanh hơn, vì nó dựng lại
# cả mười hai tháng từ đầu. Trên máy chủ nửa lõi CPU, hai giây ấy làm những cửa khác của cùng một
# lần mở màn hình phải xếp hàng — `/dashboard` vốn 0,25 giây bị đẩy lên 8 giây.
#
# BA LÝ DO ĐỂ NHỚ ĐƯỢC Ở ĐÂY:
#   · Con số này KHÔNG đổi theo vai. Hàm `bang()` không nhận `u`; nó trả kết quả hợp nhất của
#     Vietourist mẹ, và cửa đã chặn theo vai bằng `require_roles` trước khi vào tới đây. Dù vậy
#     khoá vẫn mang vai — xem luật 1 ở services/nho_tam.py: quên vai là cách lộ dữ liệu, và một
#     ngày nào đó `bang()` có thể nhận `u`.
#   · Nguồn của nó đổi CHẬM: một chuyến được đóng số, một bút toán được ghi. Năm phút chậm trên
#     một bảng điều hành là mức `/dashboard` đã chấp nhận từ trước, không phải mức mới.
#   · Có cửa làm mới: `?refresh=true`, đúng như `/dashboard`.
KHO_KQKD = NHO.Kho("bao_cao.ket_qua_kinh_doanh")


@router.get("/ket-qua-kinh-doanh")
def ket_qua_kinh_doanh(kind: str = "nam", ky: str = "", refresh: bool = False,
                       u: User = Depends(require_roles(*KQ_XEM, mo_ta="kết quả kinh doanh")),
                       db: Session = Depends(get_db)):
    """12 cột tháng của một năm, cộng bốn con số của kỳ đang chọn.

    `kind` là bề rộng (thang · quy · nam); `ky` là mã kỳ. Bỏ trống `ky` thì lấy kỳ ĐANG CHẠY của
    bề rộng ấy — người mở bảng điều hành hỏi "công ty đang thế nào", không hỏi "tháng trước".

    `refresh=true` bỏ qua chỗ nhớ và dựng lại — dành cho người vừa đóng số một chuyến.
    """
    from app.services import ket_qua_kinh_doanh as KQ
    khoa = NHO.khoa_vai(u.role, kind, ky)
    if not refresh:
        cu = KHO_KQKD.lay(khoa)
        if cu is not None:
            return {**cu, "nho_tam": True}
    try:
        return KHO_KQKD.dat(khoa, KQ.bang(db, kind=kind, ky=ky))
    except ValueError as ex:
        # KHÔNG ghi lỗi vào chỗ nhớ (luật 3 ở services/nho_tam.py): nhớ một lỗi năm phút là biến
        # một mã kỳ gõ sai thành năm phút hỏng cho mọi người cùng vai.
        raise HTTPException(422, str(ex))
