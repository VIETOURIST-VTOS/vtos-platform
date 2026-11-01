# -*- coding: utf-8 -*-
"""Bảng giữ chỗ của các làn phải là HÀNG RÀO, không phải lời hứa.

VÌ SAO CÓ TỆP NÀY

Ngày 11/9/2026 có HAI lần đụng độ trong một buổi chiều, và cả hai đều cùng một hình:

    VPM-11  ↔ Robot A   cùng viết sổ nghĩa vụ thanh toán
    Phân quyền ↔ Robot A cùng viết DT-1 và DT-3 (bốn mốc, tiền khả dụng, mức dự phòng)

Không làn nào chép của làn nào. Bốn làn cùng đọc một tài liệu rồi viết ra hai bản gần trùng khít –
cùng kẹp tháng lịch về cuối tháng ngắn, cùng năm thành phần tiền khả dụng, cùng "thiếu một thành
phần là không ra số", cùng chữ "Chưa có ngưỡng" thay cho số 0. Mất gần một buổi để gỡ.

Bảng khai một mình KHÔNG chữa được: một bảng không ai canh thì đúng ba ngày là không ai điền nữa.
Phép thử này là phần làm cho nó thành hàng rào.

TÁCH TỆP — 06/10/2026, Chủ tịch quyết

Tới 06/10/2026 cả sáu làn ghi chung vào `docs/DANG-LAM.md`. Mỗi lần đẩy là một dòng thêm vào CUỐI
tệp, nên hai nhánh song song luôn sửa đúng một chỗ: quyển sổ chung bị đè hoặc gây xung đột NĂM lần
trong ba tuần (19/9, 23/9, 30/9 và hai lần ngày 06/10) và là thứ DUY NHẤT gây xung đột trong những
lần ấy – không một tệp mã nào. Từ nay mỗi làn ghi vào `docs/dang-lam/<làn>.md` của chính mình.

Phép thử này đọc TẤT CẢ các tệp ấy CỘNG với quyển sổ cũ, rồi xét trên tập gộp – nên luật không đổi
một chữ: hai dòng `đang làm` của hai làn cùng khai một tệp thì vẫn đỏ, dù chúng nằm ở hai tệp khác
nhau. Quyển sổ cũ CỐ Ý không bị xoá: nó còn giữ lịch sử và còn nhánh đang bay của làn khác trỏ vào.

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
BANG_CU = os.path.join(ROOT, "docs", "DANG-LAM.md")
THU_MUC = os.path.join(ROOT, "docs", "dang-lam")

DANG_LAM = "đang làm"
TRANG_THAI_HOP_LE = (DANG_LAM, "xong", "bỏ")
COT = ("Làn", "Mã việc", "Tệp sẽ đụng", "Bắt đầu", "Trạng thái")

# Tên làn → tệp của làn ấy. Thêm làn mới thì thêm vào ĐÂY, và tạo tệp cùng tên.
LAN_TEP = {
    "Robot A": "robot-a",
    "Phân quyền": "phan-quyen",
    "Vòng": "vong",
    "VPM": "vpm",
    "Kiểm soát": "kiem-soat",
    "Quyết toán": "quyet-toan",
    # Làn R2 — phân hệ Hướng dẫn. Khai ở ĐÂY trước, rồi mới tạo `docs/dang-lam/r2.md`:
    # `test_moi_lan_deu_co_mot_tep_va_khong_tep_nao_thua` đỏ nếu tạo tệp trước khi khai.
    "R2": "r2",
    # Lan TC-KT — Chu tich chot 02/11/2026. Bon nhanh R4c lien tiep khong gop duoc vi ca
    # bon khai lan "Phan quyen" roi cung noi vao CUOI mot tep. Do duoc hom ay:
    # phan-quyen.md 444 KB / 187 dong / 16 dong "dang lam"; vpm.md 334 byte. Dung hong hoc
    # ngay 06/10 lap lai o mot tang sau hon — khong phai giua cac lan nua, ma TRONG mot lan
    # da phinh thanh sau lan doi lot mot.
    "TC-KT": "tc-kt",
}
LAN_HOP_LE = tuple(LAN_TEP)


def _la_md(ten: str) -> bool:
    return ten.endswith(".md") and ten != "README.md"


def _tep_trong_lan(slug: str) -> list[str]:
    """Mọi tệp sổ của MỘT làn: tệp phẳng `<slug>.md`, rồi từng tệp trong thư mục `<slug>/`.

    ĐỢT SO-DOT 02/11/2026 — mỗi ĐỢT một tệp. Tách làn (06/10) chữa xung đột GIỮA các làn; nó
    không chữa được hai đợt của CÙNG một làn, vì cả hai vẫn nối vào cuối một tệp. Đo được
    02/11: bốn nhánh R4c liên tiếp không gộp, và `phan-quyen.md` đã là 444 KB / 187 dòng /
    16 dòng "đang làm" trong khi `vpm.md` là 334 byte.

    Một đợt TẠO một tệp mới thì git không có gì để hoà — không phải hoà khéo hơn, mà là không có
    xung đột nào tồn tại. Đó là khác biệt giữa chữa triệu chứng và bỏ nguyên nhân.

    Hai dạng sống chung có chủ ý: làn cũ giữ tệp phẳng, làn mới dùng thư mục, và một làn dùng cả
    hai cũng được. Ép dời là làm gãy nhánh đang bay — cùng lẽ với việc giữ `docs/DANG-LAM.md`.
    """
    ds = []
    phang = os.path.join(THU_MUC, slug + ".md")
    if os.path.exists(phang):
        ds.append(phang)
    thu_muc = os.path.join(THU_MUC, slug)
    if os.path.isdir(thu_muc):
        ds += [os.path.join(thu_muc, t) for t in sorted(os.listdir(thu_muc)) if _la_md(t)]
    return ds


def _lan_cua_tep(duong: str) -> str:
    """Tệp này là sổ của làn nào — rỗng nếu không ứng với làn nào đã khai."""
    r = os.path.relpath(duong, THU_MUC).replace("\\", "/")
    slug = r.split("/")[0][:-3] if "/" not in r else r.split("/")[0]
    for lan, s in LAN_TEP.items():
        if s == slug:
            return lan
    return ""


def _nguon() -> list[str]:
    """Mọi tệp sổ, theo thứ tự cố định: quyển cũ trước, rồi từng làn theo tên làn.

    Thứ tự cố định chứ không theo `os.listdir` là có chủ ý: lời báo lỗi của phép thử chính liệt kê
    "dòng nào gặp trước" nên thứ tự đổi theo hệ tệp sẽ làm cùng một lỗi in ra hai kiểu trên hai máy.

    ĐỢT SO-DOT: đi qua `LAN_TEP` chứ không qua `os.listdir(THU_MUC)`. Một thư mục lạ trong
    `docs/dang-lam/` KHÔNG lặng lẽ thành nguồn — nó bị
    `test_moi_lan_deu_co_mot_tep_va_khong_tep_nao_thua` chặn, và đó là chỗ nó phải kêu.
    """
    ds = []
    if os.path.exists(BANG_CU):
        ds.append(BANG_CU)
    if os.path.isdir(THU_MUC):
        for slug in sorted(LAN_TEP.values()):
            ds += _tep_trong_lan(slug)
    return ds


def _doc_mot_tep(duong: str) -> list[dict]:
    """Đọc BẢNG năm cột trong một tệp – bỏ qua bảng hướng dẫn hai cột.

    Nhận bảng bằng SỐ CỘT chứ không bằng thứ tự xuất hiện: thêm một bảng hướng dẫn nữa ở giữa tệp
    thì cách đếm theo thứ tự sẽ đọc nhầm bảng, và nó sẽ hỏng im lặng.
    """
    dong = []
    for so, raw in enumerate(open(duong, encoding="utf-8").read().splitlines(), start=1):
        s = raw.strip()
        if not s.startswith("|"):
            continue
        o = [x.strip() for x in s.strip("|").split("|")]
        if len(o) != len(COT):
            continue                      # bảng hướng dẫn hai cột ở trên
        if o[0] == COT[0] or set(o[0]) <= set("-: "):
            continue                      # hàng tiêu đề và hàng gạch
        dong.append({"so_dong": so, "nguon": os.path.relpath(duong, ROOT).replace("\\", "/"),
                     "lan": o[0], "ma_viec": o[1],
                     "tep": [t.strip() for t in o[2].split(",") if t.strip()],
                     "bat_dau": o[3], "trang_thai": o[4].lower()})
    return dong


def _doc_bang() -> list[dict]:
    """Tập GỘP của mọi tệp sổ. Đây là thứ cả hai hàng rào đứng lên.

    Gộp chứ không xét từng tệp một là điểm mấu chốt của việc tách ngày 06/10: tách tệp để GHI khỏi
    đụng nhau, nhưng xét vẫn phải xét chung – không thì mỗi làn chỉ còn so với chính mình, và hàng
    rào "hai làn cùng một tệp" tắt ngấm đúng lúc nó vừa được tách cho dễ dùng.
    """
    ds = _nguon()
    assert ds, (
        f"Không có tệp sổ giữ chỗ nào: không thấy {BANG_CU} lẫn {THU_MUC}/*.md. "
        f"Sổ giữ chỗ là thứ bắt buộc – xem phần đầu tệp phép thử này.")
    ra = []
    for d in ds:
        ra.extend(_doc_mot_tep(d))
    return ra


def _goi(d: dict) -> str:
    """Tên gọn của một dòng trong lời báo lỗi.

    Cột `Mã việc` trong sổ thật đã có dòng dài hơn hai nghìn chữ. In nguyên vào lời báo thì người
    đọc phải cuộn qua một bài văn mới thấy dòng thứ hai – đo được ngày 06/10, lời báo của chính
    phép thử này dài tới mức không đọc nổi. Cắt ở đây, không cắt trong sổ.
    """
    mv = re.sub(r"\s+", " ", d["ma_viec"]).strip()
    if len(mv) > 60:
        mv = mv[:57] + "…"
    return f"{d['lan']} ({mv}, từ {d['bat_dau']}, {d['nguon']} dòng {d['so_dong']})"


def test_khong_dong_nao_bi_bo_qua_vi_sai_so_cot():
    """Mọi dòng bắt đầu bằng `|` phải đọc được — 2 cột (bảng hướng dẫn) hoặc 5 cột (sổ).

    CHUYỆN ĐÃ XẢY RA 12/10/2026, và nó là kiểu hỏng tệ nhất của cả bộ hàng rào này: một dòng sổ
    có ký tự `|` LỌT VÀO phần mô tả — `_doc_mot_tep` tách cột bằng `|` nên dòng ấy ra 6 cột, không
    khớp 5, và bị `continue` BỎ QUA. Người đọc sổ vẫn thấy dòng ấy nằm đó, đủ cột, đẹp đẽ. Máy thì
    không thấy gì cả.

    Hệ quả: vòng ấy tưởng đã giữ chỗ bốn tệp mã, thực tế không giữ tệp nào — và nếu một làn khác
    cùng lúc chạm vào bốn tệp đó thì `test_hai_lan_KHONG_duoc_cung_giu_mot_tep` cũng im lặng, vì
    với nó dòng kia không tồn tại. Tức là một ký tự trong câu văn tắt được cả hai hàng rào cùng
    lúc, mà không hàng rào nào kêu. `test_gn3` có bắt được, nhưng chỉ bắt trên pull request và chỉ
    nói "tệp này không ai giữ" — không nói vì sao, nên người sửa sẽ đi thêm một dòng nữa vào sổ và
    nó lại biến mất y như vậy.

    Chữ `|` trong mô tả không cách nào thoát được: bộ đọc tách theo ký tự thô, nên `\|` của
    markdown cũng tách. Cách duy nhất là ĐỪNG viết nó — dùng chữ "hoặc", hoặc viết `date or None`.
    """
    hong = []
    for duong in _nguon():
        for so, raw in enumerate(open(duong, encoding="utf-8").read().splitlines(), start=1):
            t = raw.strip()
            if not t.startswith("|"):
                continue
            n = len([x for x in t.strip("|").split("|")])
            if n not in (2, len(COT)):
                hong.append(f"{os.path.relpath(duong, ROOT)} dòng {so}: {n} cột "
                            f"(cần {len(COT)}) — có `|` lọt vào phần mô tả?")
    assert not hong, (
        "DÒNG SỔ BỊ BỎ QUA VÌ SAI SỐ CỘT — nó nằm trong tệp nhưng KHÔNG tồn tại với hàng rào:\n"
        + "\n".join("  · " + h for h in hong)
        + "\n\nCách xử: bỏ ký tự `|` khỏi phần mô tả của dòng ấy. Không thoát được bằng dấu gạch "
          "chéo — bộ đọc tách theo ký tự thô.")


def test_bang_giu_cho_doc_duoc_va_khai_du():
    """Một dòng khai thiếu cột là một dòng không giữ chỗ được cho ai."""
    ds = _doc_bang()
    assert ds, "Sổ giữ chỗ rỗng – ít nhất phải có dòng của làn đang làm việc"
    for d in ds:
        cho = f"{d['nguon']} dòng {d['so_dong']}"
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
                f"{d['nguon']} dòng {d['so_dong']} ({d['lan']} · {d['ma_viec'][:40]}): đường dẫn "
                f"“{t[:80]}” không bắt đầu từ gốc kho. Phải là một trong {goc_hop_le} – cùng một "
                f"tệp viết hai kiểu thì hai làn khai trùng mà máy không thấy trùng.")
            assert "\\" not in t, (
                f"{d['nguon']} dòng {d['so_dong']}: “{t[:80]}” dùng dấu \\ – kho mã dùng dấu /, và "
                f"hai kiểu viết thì lại không so được với nhau.")


def test_hai_lan_KHONG_duoc_cung_giu_mot_tep():
    """ĐÂY LÀ PHÉP THỬ CHÍNH. Hai dòng 'đang làm' cùng khai một đường dẫn thì ĐỎ.

    Đỏ ở đây KHÔNG có nghĩa là ai đó viết sai mã. Nó có nghĩa là hai làn sắp đụng nhau, và người
    đọc phải đi hỏi – chứ không phải sửa phép thử cho hết đỏ.

    Cùng một làn khai lại chính tệp của mình ở hai dòng thì KHÔNG đỏ: một làn tự biết mình đang làm
    gì, và cấm chuyện ấy chỉ tổ đẩy người ta gộp hai việc vào một dòng cho xong.

    Xét trên TẬP GỘP của mọi tệp sổ, nên tách tệp ngày 06/10 không làm hàng rào này yếu đi một chút
    nào: hai làn giữ cùng một tệp vẫn đỏ, dù hai dòng ấy nay nằm ở hai tệp khác nhau.
    """
    dang = [d for d in _doc_bang() if d["trang_thai"] == DANG_LAM]
    giu: dict[str, dict] = {}
    dung_do = []
    for d in dang:
        for t in d["tep"]:
            cu = giu.get(t)
            if cu is not None and cu["lan"] != d["lan"]:
                dung_do.append(f"  · {t}\n      {_goi(cu)}\n      {_goi(d)}")
            giu.setdefault(t, d)
    assert not dung_do, (
        "HAI LÀN ĐANG GIỮ CÙNG MỘT TỆP. Đây không phải lỗi mã – đây là hai làn sắp viết đè lên "
        "nhau, đúng thứ đã xảy ra hai lần trong chiều 11/9/2026.\n\n"
        + "\n".join(dung_do)
        + "\n\nCách xử: hai làn nói chuyện và chốt ai giữ tệp nào, rồi sửa dòng của mình trong "
          "docs/dang-lam/<làn>.md. Làn nào làm xong phần của mình thì đổi dòng ấy sang `xong` – "
          "`xong` không giữ chỗ nữa. ĐỪNG sửa phép thử này cho hết đỏ.")


def test_dong_nam_trong_tep_cua_lan_nao_thi_phai_la_lan_ay():
    """Tách tệp chỉ mua được gì nếu mỗi làn ghi vào ĐÚNG tệp của mình.

    Một làn ghi dòng của mình vào tệp làn khác thì hai làn lại cùng sửa một tệp mỗi lần đẩy – tức
    là xung đột quay về nguyên vẹn, mà lần này còn khó thấy hơn vì nhìn cây thư mục thì tưởng đã
    tách rồi. Quyển sổ cũ `docs/DANG-LAM.md` KHÔNG bị luật này ràng: nó là tệp chung của mọi làn
    cho tới khi từng làn tự dời dòng của mình đi.
    """
    if not os.path.isdir(THU_MUC):
        pytest.skip("Chưa tách tệp")
    # ĐỢT SO-DOT: duyệt theo LAN_TEP nên bắt cả tệp phẳng lẫn tệp trong thư mục làn.
    sai = []
    for slug in sorted(LAN_TEP.values()):
        chu = [l for l, s in LAN_TEP.items() if s == slug]
        assert chu
        for duong in _tep_trong_lan(slug):
            ten = os.path.relpath(duong, ROOT).replace("\\", "/")
            for d in _doc_mot_tep(duong):
                if d["lan"] != chu[0]:
                    sai.append(f"  · {ten} dòng {d['so_dong']}: khai làn “{d['lan']}”, "
                               f"nhưng chỗ này là của làn “{chu[0]}”")
    assert not sai, (
        "DÒNG NẰM NHẦM TỆP LÀN:\n" + "\n".join(sai)
        + "\n\nMỗi làn ghi vào tệp của chính mình – đó là toàn bộ cái mua được khi tách sổ ngày "
          "06/10/2026. Ghi nhờ tệp làn khác là hai làn lại cùng sửa một tệp mỗi lần đẩy.")


@pytest.mark.parametrize("lan", LAN_HOP_LE)
def test_ten_lan_nam_trong_danh_sach_da_biet(lan):
    """Tên làn viết tự do thì 'Phân quyền' và 'phan quyen' thành hai làn khác nhau, và phép thử
    chính ở trên coi hai dòng của CÙNG một làn là hai làn – rồi đỏ oan."""
    ds = {d["lan"] for d in _doc_bang()}
    la = ds - set(LAN_HOP_LE)
    assert not la, (
        f"Tên làn lạ trong sổ: {sorted(la)}. Sáu tên hợp lệ: {' · '.join(LAN_HOP_LE)}. "
        f"Thêm làn mới thì thêm vào LAN_TEP trong tệp này TRƯỚC, để hai cách viết cùng một làn "
        f"không thành hai làn.")


def test_moi_lan_deu_co_mot_tep_va_khong_tep_nao_thua():
    """Sáu tên làn ↔ sáu tệp, một đổi một.

    Thiếu một tệp thì làn ấy không có chỗ ghi và sẽ quay về quyển sổ chung – tức là tách nửa vời,
    kiểu tệ nhất vì nhìn thì tưởng đã xong. Thừa một tệp thì có một tệp không hàng rào nào đọc.
    """
    if not os.path.isdir(THU_MUC):
        pytest.skip("Chưa tách tệp")
    # ĐỢT SO-DOT 02/11/2026 — một làn có thể là MỘT TỆP `<slug>.md`, một THƯ MỤC `<slug>/`, hoặc
    # cả hai. Tên ở đây là tên chỗ chứa, không còn là tên tệp.
    co = set()
    for t in os.listdir(THU_MUC):
        duong = os.path.join(THU_MUC, t)
        if os.path.isdir(duong):
            co.add(t)
        elif t.endswith(".md") and t != "README.md":
            co.add(t[:-3])
    can = set(LAN_TEP.values())
    assert co == can, (
        f"docs/dang-lam/ không khớp danh sách làn.\n"
        f"  thiếu : {sorted(can - co)}\n  thừa  : {sorted(co - can)}\n"
        f"Khai làn mới trong LAN_TEP rồi tạo đúng tệp — hoặc thư mục — cùng tên.")
    # Thư mục của một làn KHÔNG được có thư mục con: `_tep_trong_lan` chỉ đọc một bậc, nên một
    # bậc nữa là những dòng ấy biến mất khỏi tập gộp mà không gì kêu lên.
    sau = []
    for slug in can:
        tm = os.path.join(THU_MUC, slug)
        if os.path.isdir(tm):
            sau += [f"docs/dang-lam/{slug}/{t}" for t in sorted(os.listdir(tm))
                    if os.path.isdir(os.path.join(tm, t))]
    assert not sau, (
        "THƯ MỤC CON TRONG THƯ MỤC LÀN: " + ", ".join(sau)
        + "\nBộ đọc chỉ đi MỘT bậc, nên mọi dòng nằm sâu hơn sẽ rơi khỏi tập gộp trong im lặng.")


def test_tap_gop_khong_bo_sot_mot_tep_nguon_nao():
    """CHỖ DỄ HỎNG IM LẶNG NHẤT của việc tách ngày 06/10.

    Nếu bộ đọc lỡ chỉ đọc quyển cũ, hoặc chỉ đọc các tệp làn, thì MỌI phép thử ở trên vẫn xanh –
    chúng chỉ xét những dòng chúng nhìn thấy, và ít dòng hơn thì càng ít khả năng đỏ. Hàng rào
    “hai làn cùng một tệp” sẽ tắt ngấm mà không ai biết, đúng kiểu hỏng mà cả tệp này sinh ra để
    chống.

    NÊN PHÉP THỬ NÀY KHÔNG ĐƯỢC GỌI `_nguon()`. Hỏi chính cái hàm đang nghi ngờ xem nó bỏ sót gì
    thì bao giờ cũng nhận được câu “không bỏ sót gì” – thử lần đầu viết kiểu ấy, và cả hai phép
    phá (bỏ quyển cũ, bỏ các tệp làn) đều SỐNG. Danh sách nguồn ở đây dựng thẳng từ hệ tệp.
    """
    # ĐỢT SO-DOT: danh sách này vẫn dựng THẲNG TỪ HỆ TỆP — `os.walk`, không gọi `_nguon()` và
    # cũng không gọi `_tep_trong_lan()`. Hỏi chính cái hàm đang nghi ngờ xem nó bỏ sót gì thì bao
    # giờ cũng nhận được câu “không bỏ sót gì”. Đi SÂU hơn một bậc có chủ ý: nếu ai đó để một
    # tệp sổ ở bậc thứ hai, phép thử này phải THẤY nó và báo bộ đọc đang bỏ sót.
    can = []
    if os.path.exists(BANG_CU):
        can.append(BANG_CU)
    if os.path.isdir(THU_MUC):
        for goc, _tm, teps in os.walk(THU_MUC):
            can += [os.path.join(goc, t) for t in sorted(teps)
                    if t.endswith(".md") and t != "README.md"]
        can.sort()
    assert can, "Không thấy tệp sổ nào trên đĩa"

    gop: dict[str, int] = {}
    for d in _doc_bang():
        gop[d["nguon"]] = gop.get(d["nguon"], 0) + 1

    thieu = []
    for duong in can:
        ten = os.path.relpath(duong, ROOT).replace("\\", "/")
        co = len(_doc_mot_tep(duong))
        if gop.get(ten, 0) != co:
            thieu.append(f"  · {ten}: trên đĩa {co} dòng, bộ đọc trả về {gop.get(ten, 0)}")
    assert not thieu, (
        "BỘ ĐỌC BỎ SÓT NGUỒN:\n" + "\n".join(thieu) +
        "\n\nTách sổ để GHI khỏi đụng nhau, nhưng XÉT phải xét trên tập gộp. Bỏ sót một nguồn là "
        "tắt hàng rào “hai làn cùng một tệp” mà mọi phép thử khác vẫn xanh.")
    assert set(gop) <= {os.path.relpath(d, ROOT).replace("\\", "/") for d in can}, (
        f"Bộ đọc trả về dòng từ nguồn LẠ: {sorted(set(gop))}")
