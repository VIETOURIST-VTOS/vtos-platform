# -*- coding: utf-8 -*-
"""MKT-2 · CỬA NHẬP CỦA PHÒNG MARKETING – khách tiềm năng và số kênh theo tháng.

Khai theo đúng khuôn `bo_nap(_c)` mà `services/intake.py` gom lúc nạp mô-đun, nên một lần khai
dùng cho CẢ BA CỬA: nhập tay, tải tệp Excel, và ảnh do AI đọc. Đăng ký bằng đúng một dòng trong
intake.py, không sửa gì khác của làn khác.

════════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO PHẢI CÓ CỬA NÀY
════════════════════════════════════════════════════════════════════════════════════════════════
Ranh giới đã chốt 09/9/2026: hệ thống viết CẤU TRÚC và PHÉP TÍNH, còn SỐ thì bộ phận nghiệp vụ tự
nhập hoặc tự tải. Mỗi con số trên màn hình phải có một cửa. Đề xuất giao diện Marketing bản 1.1
đòi năm thứ mà bảng lead hôm nay chưa giữ được, và cả năm đều là SỐ NGƯỜI NHẬP BIẾT chứ không phải
số suy ra được:

    nguồn thu hút      – nhu cầu sinh ra ở đâu (Facebook, Tiktok, khách cũ giới thiệu…)
    điểm tiếp nhận     – cuộc liên hệ rơi vào đâu (hotline, web, VCHAT, Zalo OA)
    khách lẻ / MICE    – hai nhóm khách có quy trình bán khác hẳn nhau
    thời điểm giao     – lúc nào lead sang tay Sales
    hạn xử lý          – hẹn bao giờ phải liên hệ xong

Không cột nào trong năm cột này suy ra được bằng phép tính. Đây là lý do phải dựng cửa, không phải
viết thêm hàm.

════════════════════════════════════════════════════════════════════════════════════════════════
CHỖ QUAN TRỌNG NHẤT: MỘT CỘT `channel` ĐANG GÁNH HAI TRỤC
════════════════════════════════════════════════════════════════════════════════════════════════
Danh mục 11 kênh hiện có trộn hai câu hỏi khác nhau:

    NGUỒN   Tiktok Ads · Facebook · Appier · Livestream · Khách cũ
    ĐIỂM    Hotline 1 · Hotline 2 · Đặt tour web · VCHAT · Zalo OA

Khách thấy quảng cáo Facebook rồi gọi hotline thì người nhập chỉ chọn được MỘT, và thường chọn
"Hotline 1" vì đó là chỗ họ nghe máy. Từ đó câu hỏi "Facebook mang về bao nhiêu khách" không trả
lời được nữa – không phải vì thiếu báo cáo, mà vì dữ liệu chưa bao giờ được hỏi.

Cửa này hỏi HAI Ô RIÊNG. Và nó KHÔNG tự đoán ô còn lại từ ô đã có: đoán một lần là con số báo cáo
mang theo phép đoán ấy mãi mãi, không ai gỡ ra được.

════════════════════════════════════════════════════════════════════════════════════════════════
NHỮNG CHỖ CỬA NÀY CỐ Ý KHÔNG LÀM
════════════════════════════════════════════════════════════════════════════════════════════════
· KHÔNG tự gộp hai dòng chỉ vì trùng số điện thoại. Một khách liên hệ hai lần là HAI lượt thật;
  gộp là xoá mất một lần liên hệ có thật. Phép đếm khách duy nhất nằm ở `mkt_chi_so.py`, và nó
  đếm lúc BÁO CÁO chứ không sửa dữ liệu gốc.
· KHÔNG tự nhận cũng KHÔNG tự bỏ dòng trùng khít. Dòng giống hệt một dòng đã có thì đưa vào HÀNG
  ĐỢI XỬ LÝ và chờ người quyết. Xem phần dưới.
· KHÔNG tự điền hạn xử lý theo một quy tắc mặc định. "Quá hạn" là một lời buộc tội với người được
  giao; buộc tội theo một con số hệ thống tự đặt thì người bị buộc có quyền không nhận.
· KHÔNG nhận ô "doanh thu" ở cửa lead. Tiền của khách nằm ở booking; gõ tay vào đây là mở đường
  cho hai con số cùng nói về một khoản.

════════════════════════════════════════════════════════════════════════════════════════════════
BẢN 2 (14/9/2026) – SỬA THEO GÓP Ý ĐỘC LẬP NGÀY 13/9
════════════════════════════════════════════════════════════════════════════════════════════════
Góp ý mục 3 đòi thêm mã lần phát sinh nhu cầu, ngày giờ thật và mã booking; mục 7 đòi "nhập lại
cùng file không nhân đôi" và "dòng trùng hoàn toàn được phát hiện và đưa xử lý, không tự coi là
giao dịch mới".

Đo lại tệp lead thật xác nhận cả hai đòi hỏi. Con số đo được KHÔNG chép vào đây – chúng thuộc về
một kỳ cụ thể và sẽ sai ở kỳ sau; xem tài liệu rà soát Marketing. Hình dạng của vấn đề thì ổn định
và đó mới là thứ mã nguồn cần biết:

    · phần lớn số điện thoại lặp lại chỉ khác MỖI CỘT KÊNH – cùng khách, cùng tour, cùng ngày đi
    · một phần trùng khít mọi trường nghiệp vụ
    · rất ít trường hợp là hai chuyến đi khác nhau thật

Cho nên KHOÁ CHỐNG TRÙNG ĐỔI: trước đây là `sdt|tháng|điểm tiếp nhận`, nay là `mã lead`. Khoá cũ
sai theo cả hai chiều cùng lúc – khách gọi hotline hai lần trong tháng thì mất một lần, còn khách
đến từ hai kênh thì một chuyến đi bị đếm hai lần.

════════════════════════════════════════════════════════════════════════════════════════════════
BẢN 3 (14/9/2026) – QUY TẮC TỶ LỆ CHỐT ĐÃ ĐƯỢC CHỐT
════════════════════════════════════════════════════════════════════════════════════════════════
Chủ tịch chốt lấy cách tính của tệp tổng quan phòng Marketing: nhóm theo KỲ PHÁT SINH LEAD, tử số gồm CẢ phần
chốt trong kỳ và phần chốt ở các kỳ sau. Quy tắc mang mã `overview-v1` trong `mkt_chi_so.py`.

Hệ quả với cửa nhập này: phải có ô THỜI ĐIỂM CHỐT. Không có nó thì không tách được hai phần tử số
ấy, và khách đã chốt rơi vào nhóm thứ ba "chưa rõ lúc" – vẫn tính vào tổng, nhưng không lên được
bảng nào có hai cột. Ô này là ô người nhập biết, không phải số suy ra được.
"""
import hashlib
from datetime import date, datetime

# ══════════════════════════════════════════════════════════════════════════════════════════════
# Danh mục – tách hai trục
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Giữ nguyên chữ của 11 kênh đang dùng để dữ liệu cũ đọc lại được, chỉ xếp chúng về đúng trục.
NGUON_THU_HUT = {
    "facebook": "Facebook",
    "tiktok_ads": "Tiktok Ads",
    "appier": "Appier",
    "livestream": "Livestream",
    "khach_cu": "Khách cũ quay lại",
    "gioi_thieu": "Khách cũ giới thiệu",
    "google": "Google / tìm kiếm",
    "offline": "Sự kiện, hội chợ, phát tờ rơi",
    "khac": "Nguồn khác – ghi rõ ở ghi chú",
}
DIEM_TIEP_NHAN = {
    "hotline_1": "Hotline 1",
    "hotline_2": "Hotline 2",
    "web": "Đặt tour web",
    "vchat": "VCHAT",
    "zalo_oa": "Zalo OA",
    "fanpage": "Tin nhắn fanpage",
    "tai_quay": "Khách tới quầy",
    "khac": "Nơi nhận khác – ghi rõ ở ghi chú",
}
# "Khách cũ giới thiệu" tách khỏi "Khách cũ quay lại": một bên là khách tự đi tiếp, một bên là
# khách mang người mới tới. Gộp hai thứ ấy thì không đo được sức giới thiệu của tệp khách cũ.

MANG_KHACH = {"le": "Khách lẻ", "mice": "Đoàn / MICE"}

TRANG_THAI_LEAD = {
    "moi": "Mới, chưa giao",
    "da_giao": "Đã giao Sales",
    "dang_cham_soc": "Đang chăm sóc",
    "chot": "Đã chốt tour",
    "mat": "Không chốt",
}

# Lý do mất – bắt buộc khi trạng thái là "mat". Danh sách đóng, vì ô chữ tự do thì ba tháng sau
# không tổng hợp được gì: mỗi người viết một kiểu cho cùng một lý do.
LY_DO_MAT = {
    "gia": "Giá cao hơn nơi khác",
    "lich": "Không hợp lịch khởi hành",
    "san_pham": "Không có tuyến khách cần",
    "doi_y": "Khách đổi ý, hoãn chuyến",
    "khong_lien_lac": "Không liên lạc được",
    "doi_thu": "Chọn công ty khác",
    "khac": "Lý do khác – ghi rõ ở ghi chú",
}


def _so_dien_thoai(s) -> str:
    """Chuẩn hoá về 0xxxxxxxxx. Giữ đúng cách `services/zalo.norm_phone` làm, để hai bên khớp."""
    d = "".join(c for c in str(s or "") if c.isdigit())
    if d.startswith("84") and len(d) >= 11:
        d = "0" + d[2:]
    if len(d) == 9 and not d.startswith("0"):
        d = "0" + d
    return d[:15]


def _ngay(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    if not s:
        return None
    for khuon in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, khuon).date()
        except ValueError:
            continue
    return None


def _luc(v):
    """Đọc NGÀY GIỜ. Chỉ có ngày thì trả về 00:00 của ngày ấy, và người gọi biết là chỉ có ngày.

    KHÔNG lấy `datetime.now()` khi ô trống. Lấy giờ hiện tại thay giờ phát sinh là biến một ô chưa
    biết thành một câu trả lời chính xác đến từng giây – và mọi lead nhập muộn trở thành lead vừa
    phát sinh.
    """
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    s = str(v or "").strip()
    if not s:
        return None
    for khuon in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                  "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s, khuon)
        except ValueError:
            continue
    d = _ngay(s)
    return datetime(d.year, d.month, d.day) if d else None


def _thang_cua(luc, thang_khai: str) -> str:
    """Kỳ của lead. Ưu tiên thời điểm phát sinh thật; ô khai tay chỉ dùng khi không có giờ."""
    return f"{luc:%Y-%m}" if luc else str(thang_khai or "").strip()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Mã lead, mã khách, và dấu vân tay chống nhập trùng
# ══════════════════════════════════════════════════════════════════════════════════════════════
def sinh_ma_lead(db, thang: str) -> str:
    """Cấp mã cho MỘT LẦN PHÁT SINH NHU CẦU: L2026-09-0001.

    Hệ thống cấp, không để người nhập tự đặt. Người nhập tự đặt thì hai người đặt trùng nhau, và
    mã trùng còn tệ hơn không có mã: nó làm hai lần liên hệ của hai khách khác nhau dính vào một.
    """
    from app.models.crm import Lead

    dau = f"L{thang}-"
    n = db.query(Lead).filter(Lead.ma_lead.like(dau + "%")).count()
    return f"{dau}{n + 1:04d}"


# KHÔNG CÓ HÀM SINH MÃ KHÁCH – chốt của Chủ tịch 14/9/2026: hệ thống không cấp mã khách, người
# nhập chỉ nhập MÃ TOUR. Đơn vị "một người" khi báo cáo lấy theo SỐ ĐIỆN THOẠI đã chuẩn hoá.
#
# Hai sai số của cách ấy phải nói ra chứ không được giấu: hai người dùng chung một số thì đếm
# thành một; một người đổi số thì đếm thành hai. Vì vậy báo cáo gọi con số ấy là "số điện thoại
# khác nhau", KHÔNG gọi là "số khách đã xác minh".


# Các trường làm nên "một lần phát sinh nhu cầu khác nhau". KHÔNG có tên khách: cùng một người
# nhưng lần nhập này gõ có dấu, lần sau gõ không dấu, thì đó vẫn là một lần liên hệ.
TRUONG_VAN_TAY = ("sdt", "luc", "diem_tiep_nhan", "nguon_thu_hut", "quan_tam")


def dau_van_tay(r, *, luc=None, thang: str = "") -> str:
    """Dấu để nhận ra một dòng ĐÃ TỪNG được nhập. Không phải khoá nghiệp vụ.

    Dùng ở đúng một việc: nhập lại cùng một tệp thì không sinh thêm lead. Nó KHÔNG dùng để kết luận
    hai dòng là một nghiệp vụ – hai lần liên hệ thật của cùng một khách trong cùng một phút, cùng
    một điểm tiếp nhận, hỏi cùng một tour là chuyện có thể xảy ra, và khi ấy hệ thống phải hỏi
    người chứ không tự quyết.
    """
    phan = [
        _so_dien_thoai(r.get("sdt")),
        f"{luc:%Y-%m-%d %H:%M}" if luc else thang,
        str(r.get("diem_tiep_nhan") or "").strip(),
        str(r.get("nguon_thu_hut") or "").strip(),
        str(r.get("quan_tam") or "").strip().lower(),
    ]
    return hashlib.sha1("".join(phan).encode("utf-8")).hexdigest()[:16]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Phép kiểm của cửa KHÁCH TIỀM NĂNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
def kiem_lead(db, r):
    """Trả (lỗi, cảnh báo, khoá chống trùng).

    LỖI  = không nhận dòng. Dành cho chỗ mà nhận vào là hỏng số liệu.
    CẢNH BÁO = vẫn nhận, nhưng nói ra. Dành cho chỗ dữ liệu đúng mà chưa đủ.

    Ranh giới giữa hai loại là chỗ dễ làm sai nhất: bắt lỗi quá tay thì nhân viên không nhập được
    và quay về Excel; cảnh báo quá tay thì không ai đọc nữa. Quy ước ở đây: chỉ báo LỖI khi dòng
    ấy sẽ làm SAI một con số, còn thiếu thông tin thì cảnh báo.
    """
    loi, cb = [], []

    sdt = _so_dien_thoai(r.get("sdt"))
    if not sdt:
        loi.append("Thiếu số điện thoại – đây là thứ duy nhất nối lead với booking sau này")
    elif len(sdt) < 10:
        cb.append(f"Số điện thoại '{r.get('sdt')}' chỉ có {len(sdt)} chữ số – giữ nguyên nhưng "
                  "sẽ không đối chiếu được với booking")

    luc = _luc(r.get("phat_sinh_luc"))
    thang = _thang_cua(luc, r.get("thang"))
    if not thang:
        loi.append("Thiếu kỳ phát sinh nhu cầu")
    if luc and luc > datetime.now():
        loi.append(f"Thời điểm phát sinh ({luc:%d/%m/%Y %H:%M}) ở tương lai")
    if not luc:
        # Cảnh báo, không phải lỗi: dữ liệu cũ chỉ có tháng, và chặn thì không nạp được lịch sử.
        # Nhưng phải nói ra hệ quả, vì hệ quả không nhìn thấy được trên màn hình nhập.
        cb.append("Chỉ có kỳ, chưa có ngày giờ phát sinh. Dòng này KHÔNG vào được các phép tính "
                  "theo mốc 30/60/90 ngày – nó sẽ nằm ở nhóm 'chưa đủ dữ liệu ngày', không phải "
                  "nhóm 'chưa chốt'.")

    nguon = str(r.get("nguon_thu_hut") or "").strip()
    diem = str(r.get("diem_tiep_nhan") or "").strip()
    if nguon and nguon not in NGUON_THU_HUT:
        loi.append(f"Nguồn thu hút '{nguon}' không có trong danh mục")
    if diem and diem not in DIEM_TIEP_NHAN:
        loi.append(f"Điểm tiếp nhận '{diem}' không có trong danh mục")
    if not diem:
        loi.append("Thiếu điểm tiếp nhận – phải biết cuộc liên hệ này rơi vào đâu")
    if not nguon:
        # KHÔNG suy nguồn từ điểm tiếp nhận. Khách gọi hotline có thể đến từ Facebook, từ biển
        # quảng cáo, từ bạn giới thiệu – đoán một lần là con số mang phép đoán ấy mãi mãi.
        cb.append("Chưa biết nguồn thu hút. Dòng vẫn được nhận và vẫn đếm vào tổng, nhưng không "
                  "vào được bảng 'kênh nào mang về khách'. Hỏi khách biết tới mình từ đâu.")

    mang = str(r.get("mang") or "").strip()
    if mang and mang not in MANG_KHACH:
        loi.append(f"Nhóm khách '{mang}' không hợp lệ ({', '.join(MANG_KHACH)})")
    if not mang:
        cb.append("Chưa ghi khách lẻ hay đoàn – hai nhóm có quy trình bán khác nhau, báo cáo tách "
                  "riêng sẽ thiếu dòng này")

    tt = str(r.get("trang_thai") or "moi").strip()
    if tt not in TRANG_THAI_LEAD:
        loi.append(f"Trạng thái '{tt}' không hợp lệ ({', '.join(TRANG_THAI_LEAD)})")

    nguoi_nhan = str(r.get("nguoi_nhan") or "").strip()
    giao_luc = _ngay(r.get("giao_luc"))
    han = _ngay(r.get("han_xu_ly"))

    # Ba thứ của việc giao Sales đi VỚI NHAU. Thiếu một thì "quá hạn" không tính được, và thẻ
    # "Lead quá hạn" trên màn hình sẽ hiện 0 – một con số đọc là "mọi lead đều đúng hạn".
    if tt == "da_giao" and not nguoi_nhan:
        loi.append("Trạng thái 'Đã giao Sales' mà không ghi người nhận")
    if nguoi_nhan and not giao_luc:
        cb.append("Có người nhận nhưng chưa ghi thời điểm giao – chưa tính được lead có quá hạn "
                  "hay không")
    if nguoi_nhan and not han:
        cb.append("Có người nhận nhưng chưa ghi hạn xử lý – chưa tính được lead có quá hạn hay không")
    if giao_luc and han and han < giao_luc:
        loi.append(f"Hạn xử lý ({han:%d/%m/%Y}) trước thời điểm giao ({giao_luc:%d/%m/%Y})")
    if giao_luc and giao_luc > date.today():
        loi.append(f"Thời điểm giao ({giao_luc:%d/%m/%Y}) ở tương lai")

    ly_do = str(r.get("ly_do_mat") or "").strip()
    if tt == "mat" and not ly_do:
        loi.append("Lead không chốt thì phải chọn lý do – không có lý do thì không cải thiện được gì")
    if ly_do and ly_do not in LY_DO_MAT:
        loi.append(f"Lý do mất '{ly_do}' không có trong danh mục")
    if ly_do and tt != "mat":
        cb.append("Có lý do mất nhưng trạng thái không phải 'Không chốt' – kiểm lại")

    chot_luc = _luc(r.get("chot_luc"))
    if chot_luc and chot_luc > datetime.now():
        loi.append(f"Thời điểm chốt ({chot_luc:%d/%m/%Y}) ở tương lai")
    if chot_luc and luc and chot_luc < luc:
        loi.append(f"Thời điểm chốt ({chot_luc:%d/%m/%Y}) trước lúc phát sinh nhu cầu "
                   f"({luc:%d/%m/%Y})")
    if tt == "chot" and not chot_luc:
        # Quy tắc tỷ lệ chốt chốt ngày 14/9/2026 chia tử số làm hai: chốt TRONG KỲ và chốt KỲ SAU.
        # Không có thời điểm chốt thì không tách được, và khách ấy rơi vào nhóm thứ ba "chưa rõ
        # lúc". Vẫn được tính vào tổng, nhưng không vào được bảng nào có hai cột ấy.
        cb.append("Đã chốt nhưng chưa ghi thời điểm chốt. Chuyển đổi này vẫn tính vào tổng, nhưng "
                  "không tách được là chốt trong kỳ hay chốt kỳ sau – hai con số mà quy tắc tỷ lệ "
                  "chốt đang dùng.")
    if chot_luc and tt != "chot":
        cb.append("Có thời điểm chốt nhưng trạng thái không phải 'Đã chốt tour' – kiểm lại")

    ma_booking = str(r.get("ma_booking") or "").strip()
    if ma_booking and tt != "chot":
        cb.append(f"Có mã booking '{ma_booking}' nhưng trạng thái chưa phải 'Đã chốt tour' – kiểm lại")
    if tt == "chot" and not ma_booking:
        cb.append("Đánh dấu đã chốt nhưng chưa có mã booking. Không có mã thì chuyển đổi này không "
                  "truy ngược được tới doanh thu, và sẽ nằm ngoài mọi phép tính tiền.")
    if r.get("doanh_thu") not in (None, ""):
        loi.append("Cửa lead không nhận ô doanh thu – tiền đọc từ booking theo mã booking")

    # Khoá chống trùng ĐỔI (bản 2): mã lead, không còn là sdt|kỳ|điểm tiếp nhận.
    # Nguồn nào đã có mã thì dùng mã ấy; nguồn chưa có thì hệ thống cấp lúc nạp.
    khoa = str(r.get("ma_lead") or "").strip() or None
    return loi, cb, khoa


TRUNG_CHO_XU_LY = "trung_cho_xu_ly"


def nap_lead(db, r, boi, *, nguoi_da_xac_nhan_la_lan_khac: bool = False):
    """Ghi một dòng lead. Gọi sau khi `kiem_lead` đã sạch lỗi.

    Trả (đối_tượng, trạng_thái) với trạng_thái là một trong:
        "moi"              – lead mới, đã ghi
        "cap_nhat"         – đã có mã lead ấy, ghi đè
        TRUNG_CHO_XU_LY    – trùng khít một dòng đã có; CHƯA GHI GÌ, chờ người quyết

    Ba lối ra thay vì hai là chỗ khác hẳn bản 1. Bản 1 chỉ có "mới" và "cập nhật", nên một dòng
    trùng khít hoặc lặng lẽ thành lead mới (đội tử số lên), hoặc lặng lẽ ghi đè lên dòng cũ (mất
    một lần liên hệ). Cả hai đều sai và cả hai đều KHÔNG KÊU. Góp ý mục 7 đòi đúng điều này: dòng
    trùng hoàn toàn phải được phát hiện và đưa xử lý, không tự coi là giao dịch mới.
    """
    from app.models.crm import Lead

    sdt = _so_dien_thoai(r.get("sdt"))
    luc = _luc(r.get("phat_sinh_luc"))
    thang = _thang_cua(luc, r.get("thang"))
    diem = str(r.get("diem_tiep_nhan") or "").strip()
    ma = str(r.get("ma_lead") or "").strip()
    van_tay = dau_van_tay(r, luc=luc, thang=thang)

    cu = db.query(Lead).filter(Lead.ma_lead == ma).first() if ma else None
    if cu is None:
        trung = db.query(Lead).filter(Lead.dau_van_tay == van_tay).first()
        if trung is not None and not nguoi_da_xac_nhan_la_lan_khac:
            return trung, TRUNG_CHO_XU_LY
        ma = ma or sinh_ma_lead(db, thang)

    ld = cu or Lead(phone=sdt, lead_month=thang, channel=diem)
    ld.ma_lead = ma
    ld.ma_tour = str(r.get("ma_tour") or "").strip() or None
    ld.phat_sinh_luc = luc
    ld.dau_van_tay = van_tay
    ld.ma_booking = str(r.get("ma_booking") or "").strip() or None
    ld.converted_at = _luc(r.get("chot_luc"))
    ld.phone, ld.lead_month, ld.channel = sdt, thang, diem
    ld.name = str(r.get("ten") or ld.name or "")
    ld.interest = str(r.get("quan_tam") or ld.interest or "")
    ld.status = str(r.get("trang_thai") or "moi").strip()
    ld.note = str(r.get("ghi_chu") or ld.note or "")
    ld.created_by = boi

    # Năm cột mới. Ghi bằng setattr có kiểm: cho tới khi bản nâng cấp cơ sở dữ liệu chạy xong,
    # các cột này chưa tồn tại. Đổ vỡ ở đây thì cả cửa nhập chết theo, nên phải chịu được cả hai
    # trạng thái – và phải NÓI RA ldà đang thiếu, chứ không âm thầm bỏ dữ liệu người ta vừa gõ.
    # Ô trống ghi None, KHÔNG ghi chuỗi rỗng. Chuỗi rỗng ldà một giá trị: nó gom thành một nhóm
    # riêng trên báo cáo và đọc ldà "kênh tên ldà rỗng". None đọc đúng cái nó ldà – CHƯA AI HỎI.
    def _hoac_rong(v):
        s = str(v or "").strip()
        return s or None

    chua_luu = []
    for cot, gia_tri in (("nguon_thu_hut", _hoac_rong(r.get("nguon_thu_hut"))),
                         ("diem_tiep_nhan", _hoac_rong(diem)),
                         ("mang", _hoac_rong(r.get("mang"))),
                         ("giao_luc", _ngay(r.get("giao_luc"))),
                         ("han_xu_ly", _ngay(r.get("han_xu_ly"))),
                         ("ly_do_mat", _hoac_rong(r.get("ly_do_mat")))):
        if hasattr(ld, cot):
            setattr(ld, cot, gia_tri)
        elif gia_tri:
            chua_luu.append(cot)
    if chua_luu:
        dau = "[chưa có cột: " + ", ".join(chua_luu) + "]"
        ld.note = (ld.note + " " + dau).strip() if dau not in (ld.note or "") else ld.note

    if cu is None:
        db.add(ld)
        db.flush()
        ghi_ban_giao(db, ld, r, boi)
        return ld, "moi"
    ghi_ban_giao(db, ld, r, boi)
    return ld, "cap_nhat"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Lịch sử giao – nhận Sales
# ══════════════════════════════════════════════════════════════════════════════════════════════
def ghi_ban_giao(db, ld, r, boi, *, quy_tac: str | None = None):
    """Ghi một dòng lịch sử khi việc giao hoặc hạn xử lý THAY ĐỔI so với thứ đang lưu.

    Chỉ ghi khi có đổi thật. Ghi mỗi lần lưu thì ba tháng sau lịch sử toàn dòng giống nhau và
    không ai đọc nữa – một lịch sử không ai đọc thì bằng không có.

    Hàm này KHÔNG nhận thời điểm từ người dùng: `luc` do cơ sở dữ liệu đặt. Cho sửa thời điểm thao
    tác thì bảng này thôi là bằng chứng.
    """
    from app.models.crm import LeadBanGiao

    nguoi_moi = str(r.get("nguoi_nhan") or "").strip() or None
    han_moi = _ngay(r.get("han_xu_ly"))

    # Trạng thái ĐANG GIỮ đọc từ dòng lịch sử gần nhất, không đọc từ biến tạm trên đối tượng.
    # Biến tạm chỉ sống trong một phiên; lần nhập sau mở phiên khác và sẽ thấy "chưa giao ai",
    # rồi ghi một dòng "giao" thứ hai cho cùng một việc. Lịch sử sai theo hướng phồng lên.
    truoc = (db.query(LeadBanGiao)
               .filter(LeadBanGiao.lead_id == ld.id)
               .order_by(LeadBanGiao.luc.desc(), LeadBanGiao.id.desc())
               .first())
    # Chỉ đọc từ lịch sử. KHÔNG đọc `ld.han_xu_ly`: lúc hàm này chạy, cột ấy đã bị ghi giá trị MỚI
    # ở trên rồi, nên lấy nó làm "hạn cũ" thì hạn cũ luôn bằng hạn mới và không dòng đổi hạn nào
    # được ghi. Đây là loại lỗi không kêu: bảng lịch sử vẫn có, chỉ là trống.
    nguoi_cu = truoc.den_nguoi if truoc else None
    han_cu = truoc.han_moi if truoc else None

    ra = []
    if nguoi_moi and nguoi_moi != nguoi_cu:
        ra.append(LeadBanGiao(lead_id=ld.id, viec=("giao_lai" if nguoi_cu else "giao"),
                              tu_nguoi=nguoi_cu, den_nguoi=nguoi_moi,
                              han_cu=han_cu, han_moi=han_moi,
                              phien_ban_quy_tac=quy_tac, boi=boi))
    elif han_moi and han_moi != han_cu:
        ra.append(LeadBanGiao(lead_id=ld.id, viec="doi_han", tu_nguoi=nguoi_cu,
                              den_nguoi=nguoi_moi, han_cu=han_cu, han_moi=han_moi,
                              phien_ban_quy_tac=quy_tac, boi=boi))
    for d in ra:
        db.add(d)
    return ra


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Phép kiểm của cửa SỐ KÊNH THEO THÁNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
def kiem_so_kenh(db, r):
    """Con số Marketing khai tay cho từng kênh từng tháng, kèm chi phí kênh.

    Cửa này CỐ Ý tách khỏi cửa lead. Số khai tay và số đếm được từ dữ liệu thô là HAI NGUỒN khác
    nhau, và việc đối chiếu chúng chính là nhóm "Đối soát dữ liệu" của đề xuất. Gộp hai cửa làm
    một là xoá mất chính việc ấy.
    """
    from app.services.intake import _so

    loi, cb = [], []
    thang = str(r.get("thang") or "").strip()
    if not thang:
        loi.append("Thiếu kỳ")

    kenh = str(r.get("kenh") or "").strip()
    if not kenh:
        loi.append("Thiếu kênh")
    elif kenh not in NGUON_THU_HUT and kenh not in DIEM_TIEP_NHAN:
        loi.append(f"Kênh '{kenh}' không có trong hai danh mục nguồn thu hút và điểm tiếp nhận")

    n = _so(r.get("so_lead"))
    if n < 0:
        loi.append("Số lead không âm được")
    if n == 0:
        cb.append("Khai 0 lead cho kênh này – nếu ý là 'kỳ này không chạy kênh ấy' thì đừng khai "
                  "dòng, vì 0 và 'không chạy' là hai chuyện khác nhau trên báo cáo")

    chi_phi = r.get("chi_phi")
    if chi_phi not in (None, "") and _so(chi_phi) < 0:
        loi.append("Chi phí không âm được")
    if chi_phi in (None, ""):
        cb.append("Chưa có chi phí kênh – chưa tính được chi phí trên mỗi lead và chưa tính được "
                  "hiệu quả chi quảng cáo")

    # ── Thêm 14/9/2026 sau khi đọc OVERVIEW 2026 của phòng Marketing ──────────────────────
    # Trong tệp ấy, bảng NGÂN SÁCH khai theo NGUỒN THU HÚT (Facebook, Google, Appier, Tiktok,
    # Web, Khác) còn bảng LEAD khai theo ĐIỂM TIẾP NHẬN (Hotline 1, Hotline 2, VCHAT, Đặt tour
    # web…). Rồi "chi phí trung bình mỗi chuyển đổi" lấy TỔNG ngân sách chia cho TỔNG lead.
    # Phép chia ấy lấy tiền quảng cáo chia cho một số đếm có cả cuộc gọi hotline không tốn đồng
    # quảng cáo nào. Con số ra vẫn đẹp, vẫn xuống đều qua các tháng, và không đọc được.
    #
    # Cửa này chặn ngay ở chỗ nhập: tiền chỉ gắn được vào NGUỒN THU HÚT. Một điểm tiếp nhận
    # không "tốn tiền quảng cáo" – nó là cái ống khách đi vào, không phải chỗ mua khách.
    if chi_phi not in (None, "") and kenh in DIEM_TIEP_NHAN and kenh not in NGUON_THU_HUT:
        loi.append(
            f"'{DIEM_TIEP_NHAN[kenh]}' là ĐIỂM TIẾP NHẬN, không gắn chi phí quảng cáo vào đây "
            f"được. Tiền khai theo NGUỒN THU HÚT ({', '.join(sorted(NGUON_THU_HUT))}). "
            f"Chia tiền quảng cáo cho số lead của điểm tiếp nhận là chia hai thứ khác nhau.")

    return loi, cb, (f"{thang}|{kenh}" if thang and kenh else None)


def nap_so_kenh(db, r, boi):
    from app.models.crm import LeadChannelStat
    from app.services.intake import _so

    thang = str(r.get("thang") or "").strip()
    kenh = str(r.get("kenh") or "").strip()
    cu = db.query(LeadChannelStat).filter(LeadChannelStat.lead_month == thang,
                                          LeadChannelStat.channel == kenh).first()
    s = cu or LeadChannelStat(lead_month=thang, channel=kenh)
    s.leads = int(_so(r.get("so_lead")))
    s.cost = None if r.get("chi_phi") in (None, "") else _so(r.get("chi_phi"))
    s.updated_by = boi
    if cu is None:
        db.add(s)
    return s, (cu is None)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Khai cửa – intake.py gọi hàm này lúc nạp mô-đun
# ══════════════════════════════════════════════════════════════════════════════════════════════
def bo_nap(_c) -> dict:
    return {
        "khach_tiem_nang": {
            "bang_dich": "leads",
            "phong_ban": "marketing",
            "ten": "Khách tiềm năng",
            "mo_ta":
                "Mỗi lần khách liên hệ là MỘT DÒNG. Cùng một khách gọi hotline rồi nhắn Zalo trong "
                "một tháng thì ghi hai dòng – đó là hai lượt liên hệ thật. Phép đếm 'bao nhiêu "
                "khách khác nhau' làm ở bước báo cáo, không làm bằng cách xoá bớt dòng ở đây.\n\n"
                "HAI Ô KÊNH, KHÔNG PHẢI MỘT: 'nguồn thu hút' là khách biết tới mình từ đâu; 'điểm "
                "tiếp nhận' là cuộc liên hệ rơi vào đâu. Khách thấy quảng cáo Facebook rồi gọi "
                "hotline thì nguồn là Facebook, điểm tiếp nhận là Hotline. Hệ thống KHÔNG đoán ô "
                "còn lại từ ô đã có.",
            "khoa_chong_trung": "Mã lead (hệ thống cấp); dòng trùng khít đưa hàng đợi xử lý",
            "cot": [
                _c("ma_lead", "Mã lead", kieu="he_thong_cap", vi_du="L2026-09-0001",
                   ghi_chu="hệ thống cấp; chỉ điền khi nguồn bên ngoài đã có mã riêng"),
                _c("sdt", "Số điện thoại", True, vi_du="0901234567",
                   ghi_chu="thứ duy nhất nối lead với booking sau này"),
                _c("ten", "Tên khách", vi_du="Nguyễn Văn A"),
                _c("phat_sinh_luc", "Thời điểm phát sinh", kieu="ngay_gio",
                   khong_tuong_lai=True, vi_du="2026-09-13 09:20",
                   ghi_chu="giờ nhu cầu sinh ra ở nguồn, KHÔNG phải giờ nhập tệp; thiếu thì dòng "
                           "này nằm ngoài mọi phép tính theo mốc 30/60/90 ngày"),
                _c("thang", "Kỳ phát sinh nhu cầu", True, kieu="thang", vi_du="2026-09",
                   ghi_chu="chỉ dùng khi không có thời điểm phát sinh"),
                _c("diem_tiep_nhan", "Điểm tiếp nhận", True, kieu="chon", vi_du="hotline_1",
                   chon=DIEM_TIEP_NHAN, ghi_chu="cuộc liên hệ này rơi vào đâu"),
                _c("nguon_thu_hut", "Nguồn thu hút", kieu="chon", vi_du="facebook",
                   chon=NGUON_THU_HUT,
                   ghi_chu="khách biết tới mình từ đâu – hỏi khách, đừng suy từ điểm tiếp nhận"),
                _c("mang", "Nhóm khách", kieu="chon", vi_du="le", chon=MANG_KHACH),
                _c("quan_tam", "Tour khách hỏi", vi_du="Hàn Quốc 5N4Đ tháng 10"),
                _c("nguoi_nhan", "Sales được giao", vi_du="NV0021"),
                _c("giao_luc", "Thời điểm giao", kieu="ngay", khong_tuong_lai=True,
                   vi_du="2026-09-13", ghi_chu="đi cùng hạn xử lý – thiếu một trong hai thì không "
                                               "tính được lead quá hạn"),
                _c("han_xu_ly", "Hạn xử lý", kieu="ngay", vi_du="2026-09-15",
                   ghi_chu="hẹn bao giờ phải liên hệ xong; hệ thống KHÔNG tự đặt hộ"),
                _c("trang_thai", "Trạng thái", kieu="chon", vi_du="moi", chon=TRANG_THAI_LEAD),
                _c("chot_luc", "Thời điểm chốt", kieu="ngay_gio", khong_tuong_lai=True,
                   vi_du="2026-09-20 15:40",
                   ghi_chu="bắt buộc trên thực tế nếu muốn tách 'chốt trong kỳ' và 'chốt kỳ sau' "
                           "– hai con số của quy tắc tỷ lệ chốt"),
                _c("ma_tour", "Mã tour khách hỏi", vi_du="DLPT",
                   ghi_chu="chọn từ danh mục tour, KHÔNG gõ tự do – phép đếm 'bao nhiêu chuyến' "
                           "dùng mã này; chữ tự do thì cùng một tour thành nhiều tour"),
                _c("ma_booking", "Mã booking khi chốt", vi_du="BK-2026-08-0731",
                   ghi_chu="ô MÃ, không phải ô tiền. Doanh thu đọc từ booking theo mã này – "
                           "Marketing không gõ lại số tiền ở đây"),
                _c("ly_do_mat", "Lý do không chốt", kieu="chon", vi_du="gia", chon=LY_DO_MAT,
                   ghi_chu="bắt buộc khi trạng thái là Không chốt"),
                _c("ghi_chu", "Ghi chú",
                   ghi_chu="ghi rõ nguồn hoặc nơi nhận khi chọn 'khác'; và mọi điều người "
                           "sau cần biết mà không có ô riêng"),
            ],
            "kiem": kiem_lead, "nap": nap_lead,
        },

        "so_kenh_marketing": {
            "bang_dich": "lead_channel_stats",
            "phong_ban": "marketing",
            "ten": "Số lead và chi phí theo kênh",
            "mo_ta":
                "Con số Marketing tổng hợp được cho từng kênh từng tháng, kèm chi phí kênh. Đây là "
                "nguồn THỨ HAI, độc lập với danh sách lead thô ở cửa trên.\n\n"
                "Hai nguồn lệch nhau là chuyện BÌNH THƯỜNG và là việc phải đối soát – không phải "
                "chỗ để lấy số lớn hơn. Báo cáo sẽ hiện cả hai con số cạnh nhau kèm phần lệch.",
            "khoa_chong_trung": "Kỳ + kênh",
            "cot": [
                _c("thang", "Kỳ", True, kieu="thang", vi_du="2026-09"),
                _c("kenh", "Kênh", True, kieu="chon", vi_du="facebook",
                   chon={**NGUON_THU_HUT, **DIEM_TIEP_NHAN}),
                _c("so_lead", "Số lead khai", True, kieu="so", min=0, vi_du="147"),
                _c("chi_phi", "Chi phí kênh trong kỳ", kieu="tien", min=0, vi_du="45000000",
                   ghi_chu="để trống nếu chưa có – hệ thống ghi 'chưa tính được', không ghi 0"),
            ],
            "kiem": kiem_so_kenh, "nap": nap_so_kenh,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Ai được nạp cửa nào – intake.py gọi hàm này cùng lúc với bo_nap()
# ══════════════════════════════════════════════════════════════════════════════════════════════
def vai_tro(quan_tri: tuple) -> dict:
    """Phân quyền đặt Ở ĐÂY, không đặt ở màn hình: mở được trang nạp dữ liệu không có nghĩa là
    nạp được mọi thứ.

    Hai cửa KHÔNG cùng một danh sách vai trò, và đó là chủ ý:

    · `khach_tiem_nang` mở rộng như cửa `khach_hang` đang có – Kinh doanh cũng nhập lead, vì
      phần lớn lead đi thẳng tới Sales chứ không vòng qua Marketing.

    · `so_kenh_marketing` HẸP HƠN: chỉ Marketing. Cửa này mang NGÂN SÁCH QUẢNG CÁO. Người ngoài
      phòng không biết tháng ấy chạy bao nhiêu tiền cho kênh nào, và một con số chi phí gõ nhầm
      thì kéo theo cả chi phí trên mỗi lead lẫn hiệu quả chi quảng cáo – hai chỉ tiêu dùng để
      quyết định tăng hay cắt ngân sách.
    """
    return {
        "khach_tiem_nang": quan_tri + ("nv_mkt", "ptgd_mkt", "gd_kd", "tp_kd", "tn_kd", "nv_kd"),
        "so_kenh_marketing": quan_tri + ("nv_mkt", "ptgd_mkt"),
    }
