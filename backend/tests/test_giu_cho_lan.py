# -*- coding: utf-8 -*-
"""Bảng giữ chỗ của các làn – `docs/DANG-LAM.md` – phải là HÀNG RÀO, không phải lời hứa.

VÌ SAO CÓ TỆP NÀY

Ngày 11/9/2026 có HAI lần đụng độ trong một buổi chiều, và cả hai đều cùng một hình:

    VPM-11  ↔ Robot A   cùng viết sổ nghĩa vụ thanh toán
    Phân quyền ↔ Robot A cùng viết DT-1 và DT-3 (bốn mốc, tiền khả dụng, mức dự phòng)

Không làn nào chép của làn nào. Bốn làn cùng đọc một tài liệu rồi viết ra hai bản gần trùng khít –
cùng kẹp tháng lịch về cuối tháng ngắn, cùng năm thành phần tiền khả dụng, cùng "thiếu một thành
phần là không ra số", cùng chữ "Chưa có ngưỡng" thay cho số 0. Mất gần một buổi để gỡ.

Bảng khai một mình KHÔNG chữa được: một bảng không ai canh thì đúng ba ngày là không ai điền nữa.
Phép thử này là phần làm cho nó thành hàng rào.

BA ĐIỀU PHÉP THỬ NÀY CỐ Ý KHÔNG LÀM

1. KHÔNG đỏ theo thời gian. Không có luật "dòng 'đang làm' quá N ngày thì đỏ". Một phép thử tự đỏ
   mà không ai sửa mã là thứ làm người ta thôi nhìn CI – và chính mục F của lệnh giao việc đã cảnh
   báo "đỏ mãi thì rồi không ai nhìn CI nữa".

2. KHÔNG đòi tệp khai phải tồn tại. Khai trước khi viết nghĩa là phần lớn đường dẫn còn CHƯA CÓ.
   Đòi tệp phải tồn tại là đòi người ta khai sau khi viết – đúng lúc bảng hết tác dụng.

3. KHÔNG bắt phải đóng dòng. Xong việc mà quên đổi sang `xong` thì dòng ấy vẫn giữ chỗ, và làn sau
   sẽ đi hỏi. Hỏi thừa một câu rẻ hơn hai làn viết trùng một tuần.

ĐIỀU DUY NHẤT NÓ LÀM: hai dòng `đang làm` cùng khai một đường dẫn thì ĐỎ, và nói ra hai làn nào.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BANG = os.path.join(ROOT, "docs", "DANG-LAM.md")

DANG_LAM = "đang làm"
TRANG_THAI_HOP_LE = (DANG_LAM, "xong", "bỏ")
COT = ("Làn", "Mã việc", "Tệp sẽ đụng", "Bắt đầu", "Trạng thái")


def _doc_bang() -> list[dict]:
    """Đọc BẢNG cuối tệp – bảng năm cột, bỏ qua bảng hướng dẫn hai cột ở trên.

    Nhận bảng bằng SỐ CỘT chứ không bằng thứ tự xuất hiện: thêm một bảng hướng dẫn nữa ở giữa tệp
    thì cách đếm theo thứ tự sẽ đọc nhầm bảng, và nó sẽ hỏng im lặng.
    """
    assert os.path.exists(BANG), (
        f"Không có {BANG}. Bảng giữ chỗ là thứ bắt buộc – xem phần đầu tệp phép thử này.")
    dong = []
    for so, raw in enumerate(open(BANG, encoding="utf-8").read().splitlines(), start=1):
        s = raw.strip()
        if not s.startswith("|"):
            continue
        o = [x.strip() for x in s.strip("|").split("|")]
        if len(o) != len(COT):
            continue                      # bảng hướng dẫn hai cột ở trên
        if o[0] == COT[0] or set(o[0]) <= set("-: "):
            continue                      # hàng tiêu đề và hàng gạch
        dong.append({"so_dong": so, "lan": o[0], "ma_viec": o[1],
                     "tep": [t.strip() for t in o[2].split(",") if t.strip()],
                     "bat_dau": o[3], "trang_thai": o[4].lower()})
    return dong


def test_bang_giu_cho_doc_duoc_va_khai_du():
    """Một dòng khai thiếu cột là một dòng không giữ chỗ được cho ai."""
    ds = _doc_bang()
    assert ds, "Bảng giữ chỗ rỗng – ít nhất phải có dòng của làn đang làm việc"
    for d in ds:
        cho = f"{BANG} dòng {d['so_dong']}"
        assert d["lan"], f"{cho}: thiếu tên làn"
        assert d["ma_viec"], f"{cho}: thiếu mã việc – không có mã thì không tra được lệnh giao việc"
        assert d["tep"], f"{cho}: thiếu danh sách tệp – đây là phần DUY NHẤT giữ chỗ được"
        assert re.fullmatch(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}", d["bat_dau"]), \
            f"{cho}: giờ bắt đầu phải là DD-MM-YYYY HH:MM, đang là “{d['bat_dau']}”"
        assert d["trang_thai"] in TRANG_THAI_HOP_LE, \
            f"{cho}: trạng thái phải là một trong {TRANG_THAI_HOP_LE}, đang là “{d['trang_thai']}”"


def test_duong_dan_khai_tu_goc_kho_khong_phai_tu_thu_muc_con():
    """`app/services/x.py` và `backend/app/services/x.py` là MỘT tệp viết hai kiểu.

    Hai làn khai hai kiểu thì phép thử so chuỗi ở dưới không thấy chúng trùng nhau, và hàng rào
    thủng đúng chỗ nó sinh ra để canh. Nên ép một kiểu: luôn từ gốc kho.
    """
    goc_hop_le = ("backend/", "web/", "mobile/", "infra/", "docs/", "scripts/", ".github/")
    for d in _doc_bang():
        for t in d["tep"]:
            assert t.startswith(goc_hop_le), (
                f"{BANG} dòng {d['so_dong']} ({d['lan']} · {d['ma_viec']}): đường dẫn “{t}” không "
                f"bắt đầu từ gốc kho. Phải là một trong {goc_hop_le} – cùng một tệp viết hai kiểu "
                f"thì hai làn khai trùng mà máy không thấy trùng.")
            assert "\\" not in t, (
                f"{BANG} dòng {d['so_dong']}: “{t}” dùng dấu \\ – kho mã dùng dấu /, và hai kiểu "
                f"viết thì lại không so được với nhau.")


def test_hai_lan_KHONG_duoc_cung_giu_mot_tep():
    """ĐÂY LÀ PHÉP THỬ CHÍNH. Hai dòng 'đang làm' cùng khai một đường dẫn thì ĐỎ.

    Đỏ ở đây KHÔNG có nghĩa là ai đó viết sai mã. Nó có nghĩa là hai làn sắp đụng nhau, và người
    đọc phải đi hỏi – chứ không phải sửa phép thử cho hết đỏ.

    Cùng một làn khai lại chính tệp của mình ở hai dòng thì KHÔNG đỏ: một làn tự biết mình đang làm
    gì, và cấm chuyện ấy chỉ tổ đẩy người ta gộp hai việc vào một dòng cho xong.
    """
    dang = [d for d in _doc_bang() if d["trang_thai"] == DANG_LAM]
    giu: dict[str, dict] = {}
    dung_do = []
    for d in dang:
        for t in d["tep"]:
            cu = giu.get(t)
            if cu is not None and cu["lan"] != d["lan"]:
                dung_do.append(
                    f"  · {t}\n"
                    f"      {cu['lan']} ({cu['ma_viec']}, từ {cu['bat_dau']}, dòng {cu['so_dong']})\n"
                    f"      {d['lan']} ({d['ma_viec']}, từ {d['bat_dau']}, dòng {d['so_dong']})")
            giu.setdefault(t, d)
    assert not dung_do, (
        "HAI LÀN ĐANG GIỮ CÙNG MỘT TỆP. Đây không phải lỗi mã – đây là hai làn sắp viết đè lên "
        "nhau, đúng thứ đã xảy ra hai lần trong chiều 11/9/2026.\n\n"
        + "\n".join(dung_do)
        + "\n\nCách xử: hai làn nói chuyện và chốt ai giữ tệp nào, rồi sửa "
          f"{os.path.relpath(BANG, ROOT)}. ĐỪNG sửa phép thử này cho hết đỏ.")


@pytest.mark.parametrize("lan", ["Robot A", "Phân quyền", "Vòng", "VPM", "Kiểm soát", "Quyết toán"])
def test_ten_lan_nam_trong_danh_sach_da_biet(lan):
    """Tên làn viết tự do thì 'Phân quyền' và 'phan quyen' thành hai làn khác nhau, và phép thử
    chính ở trên coi hai dòng của CÙNG một làn là hai làn – rồi đỏ oan."""
    ds = {d["lan"] for d in _doc_bang()}
    la = ds - {"Robot A", "Phân quyền", "Vòng", "VPM", "Kiểm soát", "Quyết toán"}
    assert not la, (
        f"Tên làn lạ trong bảng: {sorted(la)}. Sáu tên hợp lệ: Robot A · Phân quyền · Vòng · VPM · "
        f"Kiểm soát · Quyết toán. Thêm làn mới thì thêm vào ĐÂY trước, để hai cách viết cùng một "
        f"làn không thành hai làn.")
