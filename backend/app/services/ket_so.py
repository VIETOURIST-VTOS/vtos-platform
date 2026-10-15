"""V8 – hai chặng cuối của luồng từ chứng từ đến báo cáo tài chính (lệnh giao việc 08/9/2026).

Bốn chặng lệnh nêu, và hiện trạng thật khi bắt tay vào:

    1. Nhận diện dòng sao kê theo quy ước rồi ghi sổ HÀNG LOẠT     → CHƯA CÓ, viết ở tệp này.
    2. Bút toán lương, số bảo hiểm LẤY TỪ BẢNG LƯƠNG                → ĐÃ CÓ ở app/services/hr.py.
       Không viết lại. Thay vào đó có phép thử canh đúng điều lệnh yêu cầu: số bảo hiểm ghi sổ phải
       bằng số trên bảng lương, không phải một phép nhân tỷ lệ chạy lại lúc ghi sổ. Hai con số khác
       nhau lúc bảng lương có ngoại lệ – người vào giữa tháng, nghỉ không lương, vượt trần đóng – và
       lúc đó cái sai không hiện ra ở đâu cả, vì cả hai đều "đúng công thức".
    3. Kết chuyển cuối kỳ bốn bước                                   → CHƯA CÓ, viết ở tệp này.
    4. Lên báo cáo theo TT99 qua bs_debit / bs_credit / pl_code      → ĐÃ CÓ ở app/services/bctc.py.

MỘT QUYẾT ĐỊNH THIẾT KẾ PHẢI NÓI RÕ, VÌ NÓ LỆCH VỚI CHỮ CỦA BẢNG QUY ƯỚC

Bốn quy ước kết chuyển khai đích danh MỘT tài khoản mỗi bước: 5113 cho doanh thu, 632 cho giá vốn,
642 cho chi phí. Nếu chạy đúng theo chữ, thì doanh thu nằm ở 5111 hay 5112, và chi phí bán hàng ở
641, sẽ Ở LẠI sổ sau kết chuyển – và không có gì báo. Kết quả kinh doanh vẫn ra một con số, vẫn cân,
chỉ là thiếu mất phần đó.

Nên tệp này lấy TÀI KHOẢN ĐỐI ỨNG (911) và THỨ TỰ BƯỚC từ bảng quy ước, nhưng lấy DANH SÁCH TÀI KHOẢN
CẦN KẾT CHUYỂN từ chính sổ: mọi tài khoản chi tiết còn số dư thuộc nhóm của bước đó. Và tài khoản nào
còn dư mà không thuộc bước nào thì hiện ra thành một CẢNH BÁO có tên tài khoản, chứ không bị bỏ im
lặng. Máy vẫn chạy quy tắc; nó chỉ không giả vờ rằng danh mục tài khoản chỉ có đúng ba tài khoản.
"""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.payments import BankTransaction
from app.models.core import User

# Nhóm tài khoản của từng bước kết chuyển. Tiền tố chứ không phải tên tài khoản đích danh – xem
# phần giải thích ở đầu tệp về vì sao.
BUOC_KET_CHUYEN = {
    # BƯỚC 0 THÊM 08/10/2026 (Chủ tịch quyết): 627 KHÔNG đóng về 911 như ba bước dưới, nó chạy về
    # 154 – chi phí sản xuất chung nhập vào chi phí dở dang, rồi 154 mới ra 632 lúc quyết toán
    # chuyến. Vì đích khác nên mỗi bước nay mang `ve_tk` của riêng nó thay vì dùng chung 911.
    #
    # VÀ NẾU KHÔNG CÓ BƯỚC NÀY THÌ 627 LÀ MỘT LỖ THỦNG: `TIEN_TO_KQKD` nhận mọi tài khoản đầu 5/6/7/8,
    # nên ngay khi danh mục có 627, bộ dò "tài khoản không thuộc bước nào" sẽ kêu nó lên – kêu đúng,
    # nhưng cách chữa không phải là nhét 627 vào một bước đóng về 911 (làm thế là tính chi phí đội xe
    # hai lần: một lần qua 911, một lần nữa qua 154 -> 632).
    0: {"ten": "Kết chuyển chi phí sản xuất chung qua chi phí dở dang sang giá vốn",
        "quy_tac": "KC_627_154_632", "tien_to": ("627",), "ben_du": "no", "ve_tk": "154"},
    1: {"ten": "Kết chuyển doanh thu và thu nhập", "quy_tac": "KC_DOANH_THU",
        "tien_to": ("511", "515", "711"), "ben_du": "co", "ve_tk": "911"},
    2: {"ten": "Kết chuyển giá vốn", "quy_tac": "KC_GIA_VON",
        "tien_to": ("632", "635", "811"), "ben_du": "no", "ve_tk": "911"},
    3: {"ten": "Kết chuyển chi phí bán hàng và quản lý", "quy_tac": "KC_CHI_PHI",
        "tien_to": ("641", "642", "821"), "ben_du": "no", "ve_tk": "911"},
}
BUOC_VE_911 = (1, 2, 3)
TK_CHI_PHI_DO_DANG = "154"
TK_GIA_VON = "632"
# Chủ tịch quyết 09/10/2026: phần 154 nhận từ 627 đi THẲNG sang 632, KHÔNG chia cho từng chuyến.
#
# Lý do của quyết định, ghi lại để lần sau không ai sửa ngược: đội xe đã có màn hình lãi lỗ riêng
# (`/lai-lo-doi-xe`, `/hieu-qua-doi-xe`). Chia chi phí sửa xe vào lãi lỗ từng chuyến nữa là cùng một
# khoản nằm ở hai nơi, và hai nơi đọc cùng một khoản thì sớm muộn lệch nhau. Nên bước 0 ghi một
# chứng từ bốn dòng: Nợ 154 / Có 627 rồi Nợ 632 / Có 154 — đi ĐÚNG đường Chủ tịch nói ("cuối kỳ
# kết chuyển 154") và không để lại số dư dở dang nào không ai dọn.
KC0_QUA_154 = True
TK_XAC_DINH_KQ = "911"
TK_LAI_LO = "4212"
# Mọi tài khoản kết quả kinh doanh. Cái nào có tiền tố ở đây mà không nằm trong bước nào là một lỗ
# hổng phải nói ra, không phải một khoản được phép rơi.
TIEN_TO_KQKD = ("5", "6", "7", "8")
NGUON_SAO_KE = "sao_ke"
NGUON_KET_CHUYEN = "ket_chuyen"


class KhongGhiDuoc(Exception):
    """Lỗi nghiệp vụ người dùng cần đọc được."""


# ====================== SỐ DƯ ĐỂ KẾT CHUYỂN ======================
def _du_trong_ky(db: Session, ky: str) -> dict[str, float]:
    """Phát sinh LŨY KẾ đến hết kỳ của các tài khoản kết quả kinh doanh, đã trừ phần đã kết chuyển.

    Lấy lũy kế chứ không lấy riêng phát sinh trong kỳ: một khoản ghi nhầm vào kỳ trước rồi kỳ trước
    kết chuyển thiếu sẽ nằm lại mãi mãi nếu mỗi kỳ chỉ nhìn đúng kỳ của mình. Lũy kế trừ đi phần đã
    kết chuyển thì phần sót đó xuất hiện ở kỳ này và được dọn.
    """
    q = (select(JournalLine.account_code,
                func.sum(JournalLine.debit), func.sum(JournalLine.credit))
         .join(JournalEntry)
         .where(JournalEntry.status == "da_ghi_so", JournalEntry.period <= ky)
         .group_by(JournalLine.account_code))
    out = {}
    for ma, no, co in db.execute(q).all():
        if not str(ma).startswith(TIEN_TO_KQKD):
            continue
        net = round((no or 0) - (co or 0), 0)
        if abs(net) >= 1:
            out[ma] = net
    return out


def _tk_cua_buoc(ma: str) -> int | None:
    for b, d in BUOC_KET_CHUYEN.items():
        if ma.startswith(d["tien_to"]):
            return b
    return None


def du_154_khong_cong_trinh(db: Session, ky: str) -> dict:
    """Phần 154 lũy kế KHÔNG mang mã công trình – hệ quả trực tiếp của bước 0, và phải nói ra.

    `account_rule_check` bắt mọi bút toán 154 phải có mã tour, TRỪ khi nguồn là `ket_chuyen`. Nhờ
    ngoại lệ ấy mà bước 0 ghi được 627 -> 154 mà không phải bịa ra một công thức chia chi phí đội
    xe cho từng chuyến. Nhưng cái giá của nó có thật: phần 154 ấy KHÔNG thuộc chuyến nào, nên đường
    quyết toán chuyến (Nợ 632 – Có 154 theo từng tour) sẽ không bao giờ dọn tới nó. Nó nằm lại.

    Chủ tịch quyết 09/10/2026: đẩy THẲNG sang 632, không chia theo chuyến – vì đội xe đã có màn hình
    lãi lỗ riêng, chia vào chuyến nữa là cùng một khoản nằm hai nơi. Nên bước 0 ghi cả hai chặng
    trong một chứng từ và số này PHẢI bằng 0 sau mỗi lần kết chuyển.

    Hàm vẫn ở lại, và đó là có chủ ý: nó đổi vai từ "đếm chỗ chưa quyết" thành CHÓ GIỮ NHÀ. Khác 0
    nghĩa là có ai đó ghi thẳng vào 154 bằng đường `ket_chuyen` mà không kèm chặng ra, hoặc bước 0
    bị sửa chỉ còn một chặng. Cả hai đều âm thầm: tiền vẫn cân, sổ vẫn chạy, chỉ có một khoản dở
    dang không chuyến nào nhận lớn dần lên.
    """
    q = (select(func.sum(JournalLine.debit), func.sum(JournalLine.credit))
         .join(JournalEntry)
         .where(JournalEntry.status == "da_ghi_so", JournalEntry.period <= ky,
                JournalLine.account_code.startswith(TK_CHI_PHI_DO_DANG),
                (JournalLine.project_code == "") | (JournalLine.project_code.is_(None)),
                JournalLine.tour_id.is_(None)))
    no, co = db.execute(q).one()
    du = round((no or 0) - (co or 0), 0)
    return {"ky": ky, "tai_khoan": TK_CHI_PHI_DO_DANG, "so_du": du, "phai_bang_khong": True,
            "viec_phai_quyet": ("Số này phải bằng 0: bước 0 đẩy chi phí đội xe qua 154 sang thẳng 632 "
                                "trong cùng một chứng từ (Chủ tịch quyết 09/10/2026, không chia theo "
                                "chuyến). Khác 0 nghĩa là có đường nào đó ghi vào 154 mà không có "
                                "chặng ra – tìm chứng từ nguồn 'ket_chuyen' ghi Nợ 154 không mã tour.")}


def xem_truoc_ket_chuyen(db: Session, ky: str) -> dict:
    """Bốn bước kết chuyển của kỳ, KHÔNG ghi gì. Đây là bản người đọc trước khi bấm."""
    du = _du_trong_ky(db, ky)
    accs = {a.code: a for a in db.execute(select(Account)).scalars()}
    da_ghi = {e.source_ref: e for e in db.execute(select(JournalEntry).where(
        JournalEntry.source_type == NGUON_KET_CHUYEN,
        JournalEntry.status == "da_ghi_so")).scalars()}

    buoc, bo_sot = [], []
    tong_911 = 0.0
    kc0_chua_ghi = 0.0
    # Duyệt THEO CHÍNH BẢNG `BUOC_KET_CHUYEN`, không theo một bộ số viết tay.
    #
    # Chỗ này từng là `(1, 2, 3)` viết tay, và bẻ ngược vòng KY-2 (08/10/2026) cho thấy nó là một lỗ
    # im lặng: bộ dò "tài khoản không thuộc bước nào" hỏi `_tk_cua_buoc()`, tức hỏi BẢNG; còn việc
    # kết chuyển có chạy hay không thì do VÒNG LẶP quyết. Hai nguồn sự thật. Xoá một bước khỏi vòng
    # lặp mà vẫn để nó trong bảng thì số dư của bước ấy không được kết chuyển VÀ cũng không bị báo
    # là bỏ sót — nó chỉ biến mất. Nay vòng lặp lấy khóa từ bảng, nên hai cái không lệch nhau được.
    for b in sorted(BUOC_KET_CHUYEN):
        d = BUOC_KET_CHUYEN[b]
        dong, tong = [], 0.0
        for ma, net in sorted(du.items()):
            if _tk_cua_buoc(ma) != b:
                continue
            # Bước doanh thu đóng số dư CÓ (net âm), hai bước chi phí đóng số dư NỢ (net dương).
            so = -net if d["ben_du"] == "co" else net
            if so <= 0:
                # Số dư ngược chiều: hàng bán bị trả lại nhiều hơn doanh thu, hoặc một khoản ghi sai
                # chiều. Vẫn kết chuyển, nhưng phải hiện ra chứ không lặng lẽ bỏ.
                if abs(so) >= 1:
                    dong.append({"tk": ma, "ten": accs[ma].name if ma in accs else "",
                                 "so_tien": so, "nguoc_chieu": True})
                    tong += so
                continue
            dong.append({"tk": ma, "ten": accs[ma].name if ma in accs else "", "so_tien": so,
                         "nguoc_chieu": False})
            tong += so
        # Bước 0 đẩy chi phí đội xe sang 632 NGAY TRONG LẦN CHẠY NÀY, nên bước 2 phải đóng cả phần ấy.
        # Không gộp thì 632 của đội xe nằm lại tới kỳ sau (`_du_trong_ky` lũy kế sẽ dọn muộn một kỳ),
        # và quan trọng hơn: BẢN XEM TRƯỚC sẽ nói sai với người sắp bấm. Chỉ gộp khi bước 0 CHƯA ghi —
        # ghi rồi thì số ấy đã nằm trong sổ và `_du_trong_ky` đã tính.
        if b == 2 and kc0_chua_ghi >= 1:
            dong.append({"tk": TK_GIA_VON, "ten": "Chi phí đội xe bước 0 vừa kết chuyển sang",
                         "so_tien": kc0_chua_ghi, "nguoc_chieu": False, "tu_buoc_0": True})
            tong += kc0_chua_ghi
        ref = f"kc:{ky}:{b}"
        buoc.append({
            "buoc": b, "ten": d["ten"], "quy_tac": d["quy_tac"], "ben_du": d["ben_du"],
            "dong": dong, "tong": round(tong, 0),
            "da_ghi": ref in da_ghi, "chung_tu": da_ghi[ref].code if ref in da_ghi else "",
        })
        # Bước 0 KHÔNG góp vào 911: nó chuyển chi phí sang 154, chưa ra kết quả kinh doanh. Cộng nó
        # vào đây là trừ chi phí đội xe vào lãi của kỳ MỘT LẦN NỮA, ngoài lần đã đi qua 632.
        if b in BUOC_VE_911:
            tong_911 += tong if d["ben_du"] == "co" else -tong
        if b == 0 and ref not in da_ghi:
            kc0_chua_ghi = round(tong, 0)

    for ma in sorted(du):
        if _tk_cua_buoc(ma) is None and not ma.startswith(TK_XAC_DINH_KQ):
            bo_sot.append({"tk": ma, "ten": accs[ma].name if ma in accs else "",
                           "so_du": du[ma]})

    du154 = du_154_khong_cong_trinh(db, ky)
    lai = round(tong_911, 0)
    ref4 = f"kc:{ky}:4"
    buoc.append({
        "buoc": 4, "ten": "Kết chuyển lãi lỗ sang lợi nhuận chưa phân phối",
        "quy_tac": "KC_LAI", "ben_du": "", "dong": [],
        "tong": abs(lai), "lai": lai,
        "da_ghi": ref4 in da_ghi, "chung_tu": da_ghi[ref4].code if ref4 in da_ghi else "",
    })
    return {
        "ky": ky, "buoc": buoc, "lai_truoc_buoc_4": lai,
        "tai_khoan_khong_thuoc_buoc_nao": bo_sot,
        "du_154_khong_cong_trinh": du154,
        "canh_bao": ([f"{len(bo_sot)} tài khoản kết quả kinh doanh còn số dư mà KHÔNG bước kết chuyển "
                      f"nào nhận: {', '.join(x['tk'] for x in bo_sot[:8])}. Kết chuyển xong chúng vẫn "
                      "nằm lại trên sổ và báo cáo kết quả kinh doanh sẽ thiếu đúng phần đó."]
                     if bo_sot else [])
                    + ([f"154 đang giữ {du154['so_du']:,.0f} đ KHÔNG thuộc chuyến nào, mà số này lẽ ra "
                        "phải bằng 0. " + du154["viec_phai_quyet"]]
                       if abs(du154["so_du"]) >= 1 else []),
        "ghi_chu": ("Đây là bản XEM TRƯỚC – chưa ghi gì. Danh sách tài khoản lấy từ SỔ, không lấy từ "
                    "tên tài khoản viết trong quy ước: quy ước khai 5113 nhưng doanh thu có thể nằm ở "
                    "5111, 5112, và phần đó không được phép rơi."),
    }


def ket_chuyen(db: Session, u: User, ky: str, buoc_chon: list[int] | None = None) -> dict:
    """Ghi sổ kết chuyển. Bước đã ghi rồi thì BỎ QUA, không ghi lần thứ hai."""
    from app.services import accounting as ACC
    if ACC.is_locked(db, ky):
        raise KhongGhiDuoc(f"Kỳ {ky} đã khóa sổ – không kết chuyển được nữa.")
    xt = xem_truoc_ket_chuyen(db, ky)
    chon = set(buoc_chon if buoc_chon is not None else [0, 1, 2, 3, 4])
    d = date(int(ky[:4]), int(ky[5:7]), 28)      # ngày trong kỳ, để period_of ra đúng kỳ
    ra, bo_qua = [], []

    for b in sorted(chon):
        info = next(x for x in xt["buoc"] if x["buoc"] == b)
        if info["da_ghi"]:
            bo_qua.append({"buoc": b, "ly_do": f"đã ghi ở chứng từ {info['chung_tu']}"}); continue
        if b < 4:
            if not info["dong"] or abs(info["tong"]) < 1:
                bo_qua.append({"buoc": b, "ly_do": "không có số dư để kết chuyển"}); continue
            lines = []
            for r in info["dong"]:
                if BUOC_KET_CHUYEN[b]["ben_du"] == "co":
                    lines.append({"account": r["tk"], "debit": r["so_tien"], "note": f"kết chuyển kỳ {ky}"})
                else:
                    lines.append({"account": r["tk"], "credit": r["so_tien"], "note": f"kết chuyển kỳ {ky}"})
            ve = BUOC_KET_CHUYEN[b]["ve_tk"]
            if BUOC_KET_CHUYEN[b]["ben_du"] == "co":
                lines.append({"account": ve, "credit": info["tong"]})
            else:
                lines.append({"account": ve, "debit": info["tong"]})
            if b == 0 and KC0_QUA_154:
                # Chặng thứ hai, trong CÙNG một chứng từ: Nợ 632 / Có 154. Đi qua 154 chứ không
                # nhảy thẳng 627 -> 632, vì Chủ tịch nói "cuối kỳ kết chuyển 154" và sổ phải đọc ra
                # đúng câu ấy. Cùng một chứng từ chứ không phải hai, để không bao giờ có trạng thái
                # "đã đẩy vào 154 mà chưa đẩy ra" — trạng thái ấy là số dư dở dang không ai dọn.
                lines.append({"account": TK_GIA_VON, "debit": info["tong"],
                              "note": f"chi phí đội xe kỳ {ky} – không chia theo chuyến (Chủ tịch quyết 09/10/2026)"})
                lines.append({"account": TK_CHI_PHI_DO_DANG, "credit": info["tong"]})
        else:
            lai = xt["lai_truoc_buoc_4"]
            if abs(lai) < 1:
                bo_qua.append({"buoc": 4, "ly_do": "kết quả kỳ bằng 0"}); continue
            if lai > 0:      # lãi: Nợ 911 – Có 4212
                lines = [{"account": TK_XAC_DINH_KQ, "debit": lai},
                         {"account": TK_LAI_LO, "credit": lai}]
            else:            # lỗ: Nợ 4212 – Có 911
                lines = [{"account": TK_LAI_LO, "debit": -lai},
                         {"account": TK_XAC_DINH_KQ, "credit": -lai}]
        try:
            e = ACC.post_entry(db, u.username, u.role, d,
                               f"{info['ten']} – kỳ {ky}", lines,
                               NGUON_KET_CHUYEN, f"kc:{ky}:{b}", nghiep_vu="ket_chuyen_cuoi_ky")
        except ValueError as ex:
            raise KhongGhiDuoc(f"Bước {b} ({info['ten']}): {ex}")
        ra.append({"buoc": b, "chung_tu": e.code, "so_tien": abs(info["tong"])})
    return {"ky": ky, "da_ghi": ra, "bo_qua": bo_qua,
            "tai_khoan_khong_thuoc_buoc_nao": xt["tai_khoan_khong_thuoc_buoc_nao"],
            "canh_bao": xt["canh_bao"],
            "message": (f"Đã ghi {len(ra)} bước kết chuyển kỳ {ky}."
                        + (f" Bỏ qua {len(bo_qua)} bước." if bo_qua else ""))}


# ====================== SAO KÊ → BÚT TOÁN HÀNG LOẠT ======================
def _boi_canh(db: Session, t: BankTransaction, phan_loai: dict | None = None) -> dict:
    """Bối cảnh để tra bảng quy ước.

    Hai loại khóa, và ranh giới giữa chúng là chỗ phân hệ này suýt hỏng:

      SUY RA ĐƯỢC TỪ DỮ LIỆU – nội dung, mã tham chiếu, ngân hàng, và `khop_don` (dòng tiền này đã
      khớp vào một booking chưa). Máy tự điền.

      KHÔNG SUY RA ĐƯỢC – `muc_chi` và `muc_thu`: một dòng tiền ra 50 triệu là trả nhà cung cấp, tạm
      ứng cho hướng dẫn viên, trả gốc vay hay trả lương, thì SAO KÊ KHÔNG NÓI. Đó là một phán đoán
      nghiệp vụ, và máy không được đoán hộ. Người phân loại một lần cho từng dòng (hoặc cho cả nhóm
      cùng kiểu), rồi cả lô mới ghi sổ được.

    Bản đầu của hàm này không truyền hai khóa đó, và hậu quả không phải là báo lỗi: điều kiện thiếu
    khóa trong bối cảnh bị coi là KHÔNG khớp, nên mọi dòng đều rơi vào rổ 'chưa nhận diện' và tính
    năng ghi sổ hàng loạt trông như chạy được mà thật ra không ghi gì bao giờ.
    """
    kh, ma_kh = "", ""
    if t.booking_id:
        from app.models.core import Booking
        b = db.get(Booking, t.booking_id)
        if b is not None:
            kh = getattr(b, "customer_name", "") or ""
            ma_kh = getattr(b, "code", "") or ""
    return {"noi_dung": t.content or "", "ma": (t.reference_code or "").upper(),
            "so_chung_tu": t.reference_code or "", "ngan_hang": t.gateway or "",
            "ma_ngan_hang": t.account_number or "", "booking_id": t.booking_id,
            "khop_don": bool(t.booking_id), "khach": kh, "ma_khach": ma_kh,
            # ĐỢT R2 15/10/2026 — bối cảnh này dựng từ MỘT DÒNG SAO KÊ NGÂN HÀNG, nên hình thức
            # thanh toán của nó là chuyển khoản, biết chắc chứ không phải đoán. Khai ra để sáu
            # quy tắc tiền mặt của đợt R2 KHÔNG bao giờ khớp đường sao kê — nếu để trống thì luật
            # "cụ thể thắng chung chung" sẽ không có gì để so, và `THU_KHACH_TM` (ghi Nợ 1111)
            # vẫn thua `THU_KHACH` như cũ, nhưng vì một lẽ tình cờ chứ không vì một luật.
            # Kế toán ghi đè được qua `phan_loai` ở cuối hàm, cho dòng sao kê thật ra là nộp quỹ.
            "hinh_thuc_tt": "chuyen_khoan",
            "ky": f"{t.transaction_date:%Y-%m}" if t.transaction_date else "",
            "ky": f"{t.transaction_date:%Y-%m}" if t.transaction_date else "",
            **{k: v for k, v in (phan_loai or {}).items() if v not in (None, "")}}


def goi_y_phan_loai(db: Session, nguon: str) -> list[dict]:
    """Những giá trị `muc_chi` / `muc_thu` mà bảng quy ước ĐANG nhận, kèm quy ước tương ứng.

    Màn hình dùng cái này làm danh sách chọn cho dòng chưa nhận diện. Nói cho người dùng biết phân
    loại nào sẽ khớp thì họ chọn được trong một giây; bắt họ đoán thì họ chọn bừa, và một dòng phân
    loại bừa nguy hiểm hơn một dòng để trống."""
    from app.services import hach_toan as HT
    ra = []
    for q in HT.dang_hieu_luc(db, nguon):
        for k in ("muc_chi", "muc_thu"):
            for v in (q.dieu_kien or {}).get(k, []) or []:
                ra.append({"khoa": k, "gia_tri": v, "quy_tac": q.ma, "ten": q.ten,
                           "tk_no": q.tk_no, "tk_co": q.tk_co})
    return ra


def _gan_doi_tuong(lines: list[dict], pl: dict, t: BankTransaction) -> None:
    """Điền mã đối tượng do Kế toán chỉ định vào những dòng còn thiếu.

    Vì sao cần bước này: một số tài khoản BẮT BUỘC có mã đối tượng (131, 331, 3388, 141, 341…), mà
    sao kê chỉ mang tên người chuyển – không mang mã khách hay mã nhà cung cấp trong danh mục. Nên
    người phân loại dòng cũng là người chỉ ra đối tượng, cùng một lần, cùng một ô.

    Nếu Kế toán không chỉ định thì KHÔNG lấy tên người chuyển làm mã đối tượng: tên trên sao kê là
    chữ tự do, dùng nó làm mã là cách chắc chắn để sổ công nợ có ba mã cho cùng một nhà cung cấp.
    """
    ma = str(pl.get("ma_doi_tuong") or pl.get("ma_ncc") or pl.get("ma_khach")
             or pl.get("ma_nhan_vien") or pl.get("ma_ngan_hang") or "").strip()
    ten = str(pl.get("doi_tuong") or pl.get("ncc") or pl.get("khach")
              or pl.get("nhan_vien") or pl.get("ngan_hang") or "").strip()
    if not ma and not ten:
        return
    for l in lines:
        if not (l.get("partner_code") or l.get("partner")):
            l["partner_code"] = ma[:60]
            l["partner"] = (ten or ma)[:160]


def _thieu_gi(db: Session, lines: list[dict]) -> list[str]:
    """Dòng bút toán dựng xong rồi còn thiếu gì để ghi được. Trả về danh sách lý do, rỗng là đủ.

    Dùng ĐÚNG hàm kiểm mà lúc ghi sổ sẽ chạy, chứ không chép lại luật vào đây: chép là hai bên sẽ
    lệch nhau, và bên lỏng hơn luôn là bên người dùng nhìn thấy."""
    from app.services import accounting as ACC
    ra = []
    for l in lines:
        try:
            ACC.account_rule_check(db, str(l["account"]), l, NGUON_SAO_KE)
        except ValueError as ex:
            ra.append(str(ex))
    return ra


def _da_ghi_so(db: Session, ids: list[int]) -> dict[int, JournalEntry]:
    if not ids: return {}
    refs = [f"bank:{i}" for i in ids]
    out = {}
    for e in db.execute(select(JournalEntry).where(
            JournalEntry.source_type == NGUON_SAO_KE,
            JournalEntry.source_ref.in_(refs))).scalars():
        try:
            out[int(e.source_ref.split(":")[1])] = e
        except (IndexError, ValueError):
            pass
    return out


def xem_truoc_sao_ke(db: Session, ky: str, phan_loai: dict | None = None) -> dict:
    """Nhận diện từng dòng sao kê của kỳ theo bảng quy ước. KHÔNG ghi gì.

    Chia làm ba rổ, và ranh giới giữa chúng là điều quan trọng nhất của hàm này:

      khớp        – có đúng một quy ước nhận, bút toán dựng được, chờ người bấm ghi cả lô.
      chưa nhận   – KHÔNG quy ước nào khớp. Đây KHÔNG phải lỗi và cũng không được đoán: nó vào hàng
                    chờ để Kế toán định khoản tay. Đoán tài khoản cho một dòng tiền là cách nhanh
                    nhất để có một sổ trông đầy đủ mà sai.
      đã ghi      – đã có chứng từ mang đúng mã dòng này. Bấm ghi lô lần thứ hai không sinh bản sao.
    """
    from app.services import hach_toan as HT
    q = select(BankTransaction).order_by(BankTransaction.transaction_date, BankTransaction.id)
    ds = [t for t in db.execute(q).scalars()
          if t.transaction_date and f"{t.transaction_date:%Y-%m}" == ky]
    da = _da_ghi_so(db, [t.id for t in ds])

    khop, chua, roi = [], [], []
    for t in ds:
        mo_ta = {"id": t.id, "ngay": t.transaction_date.date() if t.transaction_date else None,
                 "chieu": t.transfer_type, "so_tien": t.amount,
                 "noi_dung": (t.content or "")[:200], "ma_tham_chieu": t.reference_code or "",
                 "ngan_hang": t.gateway or ""}
        if t.id in da:
            roi.append({**mo_ta, "chung_tu": da[t.id].code}); continue
        if not (t.amount or 0) or (t.amount or 0) <= 0:
            chua.append({**mo_ta, "ly_do": "số tiền không dương – dòng này không ghi sổ được"}); continue
        nguon = "tien_vao" if t.transfer_type == "in" else "tien_ra"
        pl = (phan_loai or {}).get(t.id) or (phan_loai or {}).get(str(t.id)) or {}
        bt = HT.xem_truoc(db, nguon, t.amount, _boi_canh(db, t, pl),
                          on=t.transaction_date.date() if t.transaction_date else None)
        if not bt.get("khop"):
            chua.append({**mo_ta, "nguon": nguon,
                         "ly_do": bt.get("ly_do", "không có quy ước nào khớp"),
                         "phan_loai_giup_khop": goi_y_phan_loai(db, nguon)}); continue
        # Nhận ra quy ước CHƯA ĐỦ để ghi được. Quy ước TRA_NCC ghi vào 331, mà 331 bắt buộc có mã
        # đối tượng – thứ sao kê không mang theo. Kiểm ngay ở bước xem trước, đừng để nó nổ lúc ghi
        # cả lô: lúc đó người dùng đã bấm rồi và chỉ thấy một danh sách lỗi không hiểu vì sao.
        _gan_doi_tuong(bt["lines"], pl, t)
        thieu = _thieu_gi(db, bt["lines"])
        if thieu:
            chua.append({**mo_ta, "nguon": nguon, "quy_tac": bt["quy_tac"],
                         "ly_do": "; ".join(thieu),
                         "can_bo_sung": True,
                         "phan_loai_giup_khop": goi_y_phan_loai(db, nguon)}); continue
        khop.append({**mo_ta, "quy_tac": bt["quy_tac"], "ten_quy_tac": bt["ten_quy_tac"],
                     "dien_giai": bt["dien_giai"], "lines": bt["lines"]})

    return {
        "ky": ky, "so_dong": len(ds),
        "khop": khop, "chua_nhan_dien": chua, "da_ghi_so": roi,
        "tong_khop": round(sum((x["so_tien"] or 0) for x in khop), 0),
        "tong_chua_nhan_dien": round(sum((x["so_tien"] or 0) for x in chua), 0),
        "ghi_chu": ("Đây là bản XEM TRƯỚC cả lô – chưa ghi gì. Dòng chưa nhận diện KHÔNG bị đoán tài "
                    "khoản: chúng chờ Kế toán định khoản tay, vì một sổ trông đầy đủ mà sai thì tệ "
                    "hơn một sổ còn thiếu và biết mình thiếu."),
    }


def ghi_so_sao_ke(db: Session, u: User, ky: str, chi_dinh: list[int] | None = None,
                  phan_loai: dict | None = None) -> dict:
    """Ghi sổ cả lô những dòng đã nhận diện được. Dòng chưa nhận diện KHÔNG bao giờ đi qua đây."""
    from app.services import accounting as ACC
    if ACC.is_locked(db, ky):
        raise KhongGhiDuoc(f"Kỳ {ky} đã khóa sổ.")
    xt = xem_truoc_sao_ke(db, ky, phan_loai)
    loc = set(chi_dinh) if chi_dinh else None
    ra, hong = [], []
    for x in xt["khop"]:
        if loc is not None and x["id"] not in loc:
            continue
        try:
            e = ACC.post_entry(db, u.username, u.role,
                               x["ngay"] or date.today(), x["dien_giai"], x["lines"],
                               NGUON_SAO_KE, f"bank:{x['id']}", nghiep_vu="but_toan_sao_ke")
            ra.append({"id": x["id"], "chung_tu": e.code, "so_tien": x["so_tien"],
                       "quy_tac": x["quy_tac"]})
        except ValueError as ex:
            # Một dòng hỏng không được làm hỏng cả lô, nhưng phải hiện ra kèm lý do và kèm mã dòng.
            hong.append({"id": x["id"], "so_tien": x["so_tien"], "loi": str(ex)})
    return {"ky": ky, "da_ghi": ra, "hong": hong,
            "con_chua_nhan_dien": len(xt["chua_nhan_dien"]),
            "tong_da_ghi": round(sum((x["so_tien"] or 0) for x in ra), 0),
            "message": (f"Đã ghi sổ {len(ra)} dòng sao kê kỳ {ky}"
                        + (f", {len(hong)} dòng lỗi" if hong else "")
                        + (f". Còn {len(xt['chua_nhan_dien'])} dòng chờ Kế toán định khoản tay."
                           if xt["chua_nhan_dien"] else "."))}


# ====================== TRẠNG THÁI CẢ KỲ ======================
def quy_uoc_khong_bao_gio_ghi_duoc(db: Session) -> list[dict]:
    """Quy ước ghi vào tài khoản BẮT BUỘC có mã đối tượng nhưng lại khai 'không cần đối tượng'.

    Một quy ước như vậy không bao giờ ghi sổ được: nó khớp, dựng ra bút toán, rồi bị chặn ở bước
    kiểm cuối – và người dùng chỉ thấy 'dòng này không ghi được' mà không hiểu vì sao, vì lỗi nằm ở
    bảng quy ước chứ không nằm ở dòng dữ liệu của họ.

    Nguyên tắc của cả phân hệ là 'người sửa quy tắc chứ không sửa từng bút toán', nên chỗ hỏng phải
    được chỉ ra ở cấp quy tắc. Hàm này không tự sửa gì – sửa quy ước là việc cần hai chữ ký."""
    from app.services import accounting as ACC
    from app.services import hach_toan as HT
    ra = []
    for nguon in ("tien_vao", "tien_ra"):
        for q in HT.dang_hieu_luc(db, nguon):
            if q.doi_tuong:
                continue
            for tk in (q.tk_no, q.tk_co):
                if tk and tk.startswith(ACC.NEED_PARTNER):
                    ra.append({"quy_tac": q.ma, "ten": q.ten, "nguon": nguon, "tai_khoan": tk,
                               "ly_do": (f"Tài khoản {tk} bắt buộc có mã đối tượng, nhưng quy ước "
                                         f"{q.ma} khai 'không cần đối tượng'. Mọi dòng khớp quy ước "
                                         "này sẽ dừng ở bước kiểm cuối cho tới khi Kế toán chỉ định "
                                         "đối tượng cho từng dòng – hoặc cho tới khi quy ước được "
                                         "sửa lại (cần hai chữ ký).")})
                    break
    return ra


def tinh_trang_ky(db: Session, ky: str) -> dict:
    """Một kỳ đi tới đâu rồi. Màn hình đọc cái này để biết còn thiếu chặng nào trước khi lên báo cáo."""
    from app.services import accounting as ACC
    from app.models.hr import PayrollRun
    sk = xem_truoc_sao_ke(db, ky)
    kc = xem_truoc_ket_chuyen(db, ky)
    luong = db.execute(select(PayrollRun).where(PayrollRun.period == ky)).scalars().first()
    chua_xong = []
    if sk["chua_nhan_dien"]:
        chua_xong.append(f"{len(sk['chua_nhan_dien'])} dòng sao kê chưa định khoản "
                         f"({sk['tong_chua_nhan_dien']:,.0f} đ)")
    if sk["khop"]:
        chua_xong.append(f"{len(sk['khop'])} dòng sao kê đã nhận diện nhưng chưa ghi sổ")
    if luong is None:
        chua_xong.append("chưa có bảng lương kỳ này")
    elif luong.status != "tgd_ky":
        chua_xong.append(f"bảng lương mới ở bước '{luong.status}', chưa ghi sổ")
    thieu_kc = [b["buoc"] for b in kc["buoc"] if not b["da_ghi"] and abs(b["tong"]) >= 1]
    if thieu_kc:
        chua_xong.append("chưa kết chuyển bước " + ", ".join(str(x) for x in thieu_kc))
    return {
        "ky": ky, "da_khoa": ACC.is_locked(db, ky),
        "sao_ke": {"tong_dong": sk["so_dong"], "da_ghi": len(sk["da_ghi_so"]),
                   "cho_ghi": len(sk["khop"]), "chua_nhan_dien": len(sk["chua_nhan_dien"])},
        "bang_luong": {"co": luong is not None, "trang_thai": luong.status if luong else "",
                       "so_chung_tu": len(luong.entry_ids or []) if luong else 0},
        "ket_chuyen": [{"buoc": b["buoc"], "ten": b["ten"], "da_ghi": b["da_ghi"],
                        "tong": b["tong"]} for b in kc["buoc"]],
        "canh_bao": kc["canh_bao"] + [x["ly_do"] for x in quy_uoc_khong_bao_gio_ghi_duoc(db)],
        "chua_xong": chua_xong,
        "san_sang_len_bao_cao": not chua_xong,
        "ghi_chu": ("Sẵn sàng lên báo cáo nghĩa là mọi chứng từ của kỳ đã vào sổ – KHÔNG có nghĩa là "
                    "số đã đúng. Đối chiếu vẫn là việc của người."),
    }

# ====================== TÁCH CHÊNH LỆCH TỶ GIÁ RA 635 / 515 (KY-4) ======================
#
# Chủ tịch quyết 09/10/2026: "nên tách, và bắt đầu tính từ hôm nay về sau".
#
# ĐẶT Ở ĐÂY CHỨ KHÔNG THÀNH MỘT BƯỚC CỦA `BUOC_KET_CHUYEN`, và đó là một phân biệt có lý do: bốn
# bước kia lấy số từ SỔ (`_du_trong_ky` đọc số dư tài khoản), còn số này tính TỪ CÁC DÒNG QUYẾT
# TOÁN ở ngoài sổ. Nhét nó vào bảng ấy thì bộ dò "tài khoản không thuộc bước nào" và phép kiểm phủ
# hết các bước — hai thứ dựng trên giả định "mọi bước đều đọc sổ" — sẽ nói những câu vô nghĩa.
#
# Nhưng vẫn ĐI QUA `post_entry` với nguồn `ket_chuyen`, vì nó đúng là một bút toán phân loại lại
# cuối kỳ, và vì nguồn ấy được `account_rule_check` miễn đòi mã công trình — chênh lệch tỷ giá của
# cả kỳ không thuộc riêng chuyến nào.
NGUON_TACH_TY_GIA = "ket_chuyen"


def xem_truoc_tach_ty_gia(db: Session, ky: str) -> dict:
    """Bản xem trước. Mọi đường GHI ở tệp này đều có một đường XEM TRƯỚC – xem ghi chú đầu tệp."""
    from app.services import chenh_lech_ty_gia as CL
    kq = CL.tinh_tach(db, ky)
    ref = f"tgia:{ky}"
    da = db.execute(select(JournalEntry).where(JournalEntry.source_type == NGUON_TACH_TY_GIA,
                                               JournalEntry.source_ref == ref,
                                               JournalEntry.status == "da_ghi_so")).scalars().first()
    canh = []
    if kq["so_thieu_ty_gia_so"]:
        canh.append(f"{kq['so_thieu_ty_gia_so']} dòng KHÔNG tách được vì sổ tỷ giá chưa có ngày ấy. "
                    "Nhập tỷ giá ở màn hình Tỷ giá rồi chạy lại – chạy bây giờ thì phần đó ở lại "
                    "trong giá vốn chuyến.")
    if kq["so_khong_ro"]:
        canh.append(f"{kq['so_khong_ro']} dòng không tính được chênh vì không khai rõ số tiền "
                    "nguyên tệ. Đây là chỗ hở của mô hình, không phải của kỳ này.")
    if kq["so_truoc_moc"]:
        canh.append(f"{kq['so_truoc_moc']} dòng có ngày trước mốc {kq['tu_ngay']} – KHÔNG tách và "
                    "KHÔNG sửa lùi, theo đúng quyết định 'từ hôm nay về sau'.")
    return {**kq, "da_ghi": da is not None, "chung_tu": da.code if da else "", "canh_bao": canh}


def tach_ty_gia(db: Session, u: User, ky: str) -> dict:
    """Ghi MỘT bút toán phân loại lại cho cả kỳ. Ghi rồi thì bỏ qua, không ghi lần hai."""
    from app.services import accounting as ACC
    if ACC.is_locked(db, ky):
        raise KhongGhiDuoc(f"Kỳ {ky} đã khóa sổ – không ghi được nữa.")
    xt = xem_truoc_tach_ty_gia(db, ky)
    if not xt["da_bat"]:
        raise KhongGhiDuoc("Chưa đặt mốc ngày tách (tham số 'tach_ty_gia_tu_ngay') – không tách gì cả.")
    if xt["da_ghi"]:
        return {**xt, "message": f"Kỳ {ky} đã tách ở chứng từ {xt['chung_tu']} – bỏ qua."}
    if not xt["but_toan"]:
        return {**xt, "message": f"Kỳ {ky} không có chênh lệch tỷ giá nào để tách."}
    d = date(int(ky[:4]), int(ky[5:7]), 28)
    try:
        e = ACC.post_entry(db, u.username, u.role, d,
                           f"Tách chênh lệch tỷ giá ra 635/515 – kỳ {ky}", list(xt["but_toan"]),
                           NGUON_TACH_TY_GIA, f"tgia:{ky}", nghiep_vu="tach_ty_gia")
    except ValueError as ex:
        raise KhongGhiDuoc(f"Tách chênh lệch tỷ giá kỳ {ky}: {ex}")
    return {**xt, "da_ghi": True, "chung_tu": e.code,
            "message": (f"Đã tách chênh lệch tỷ giá kỳ {ky}: lỗ {xt['lo']:,.0f} đ, "
                        f"lãi {xt['lai']:,.0f} đ, trên {len(xt['tach_duoc'])} dòng.")}
