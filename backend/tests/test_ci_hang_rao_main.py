# -*- coding: utf-8 -*-
"""CANH CHÍNH TỆP CI — để cửa hẹp trên main không lặng lẽ chạy thiếu (19/9/2026).

──────────────────────────────────────────────────────────────────────────────────────────────
VIỆC NÀY CANH CÁI GÌ
──────────────────────────────────────────────────────────────────────────────────────────────

`.github/workflows/ci.yml` nay chạy hai hình: ĐỦ BỘ trên PR (cửa chặn), và một CỬA HẸP 12 giây
trên main (cửa báo, soi chuyện hai làn đụng nhau). Cửa hẹp ấy gọi tên từng tệp phép thử bằng tay.

Gọi tên bằng tay có một chỗ hỏng không ai thấy: `pytest tests/khong_co_tep_nay.py` **thoát 4**, và
GitHub Actions coi mã thoát khác 0 là đỏ — nên đổi tên tệp thì CI đỏ, tốt. NHƯNG nếu ai đó xoá một
tệp khỏi dòng lệnh ấy (vì nó đang đỏ, vì cho nhanh), CI **vẫn xanh** và cửa hẹp từ đó soi thiếu một
hàng rào. Một cửa kiểm chạy thiếu mà vẫn xanh nguy hiểm hơn không có cửa nào: người ta tin nó.

Nên phép thử này giữ danh sách ở HAI CHỖ và bắt hai chỗ phải khớp nhau.

VÌ SAO ĐỌC TỆP YAML BẰNG TAY, KHÔNG DÙNG `import yaml`

PyYAML không có trong `requirements-dev.txt` — máy nào cũng đang có nó vì một gói khác kéo theo.
Dựa vào một gói không khai là cách để một ngày nào đó CI đỏ vì `ModuleNotFoundError` ở đúng cái
phép thử sinh ra để canh CI. Đọc bằng chuỗi thì không nợ ai cả.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
CI = GOC / ".github" / "workflows" / "ci.yml"

# Danh sách hàng rào — CHÉP TAY, và đó là chủ ý.
#
# Không suy ra được từ mã: "tệp nào là hàng rào chống hai làn đụng nhau" là một phán đoán của
# người, không phải một tính chất máy đo được. Nên nó nằm đây, có tên, và lệch với ci.yml là đỏ.
#
# THÊM MỘT HÀNG RÀO MỚI thì sửa CẢ HAI chỗ: dòng `pytest` trong ci.yml và danh sách này.
HANG_RAO = (
    "tests/test_mach_migration.py",
    "tests/test_menu.py",
    "tests/test_p11_khai_quyen_phai_co_man_hinh.py",
    "tests/test_ks_ma_tran.py",
    "tests/test_p2_pham_vi_vai_tro.py",
    "tests/test_giu_cho_lan.py",
    # 23/9/2026. Gọi tên ở đây KHÔNG phải để chạy ba luật của nó — ba luật ấy chỉ đo được trên PR,
    # nơi có danh sách tệp nhánh đổi. Gọi tên là để XOÁ TỆP NÀY THÌ ĐỎ: `pytest` gặp đường dẫn
    # không tồn tại thì thoát 4, và Actions coi mã thoát khác 0 là đỏ. Không có dây ấy thì gỡ hàng
    # rào chỉ cần xoá một tệp, vì run_all.sh quét theo mẫu tên chứ không theo danh sách.
    "tests/test_giu_cho_nhanh.py",
    "tests/test_ks_do_dai.py",
    "tests/test_ks2_khai_quyen_may_doc_duoc.py",
    "tests/test_ks_cua_nhap.py",
    "tests/test_man_hinh_co_cua_nhap.py",
    # ── NĂM TỆP THÊM NGÀY 13/10/2026, Chủ tịch chốt ───────────────────────────────────────────
    # Cả năm tệp này vừa bắt được lỗi thật do hai Đợt E3 và E4 để lại trên main, mà cửa hẹp cũ
    # không gọi nên không ai thấy: khoá chống ghi sổ hai lần chặn nhầm đường nạp lại mốc kiểm
    # toán, một cửa chặn Chủ tịch chưa khai, một vai mới xuất hiện ở chỗ chưa khai, và bảng luật
    # chữ ký thêm cửa thứ bảy mà sổ phép thử không biết.
    #
    # Chúng KHÔNG phải hàng rào "hai làn đụng nhau" như tám tệp trên — chúng là hàng rào KHAI
    # BÁO: mỗi tệp canh một bảng mà người phải khai tay, và bảng khai tay là thứ hỏng lặng lẽ
    # nhất khi ai đó thêm một dòng mã mà quên dòng khai. Cửa hẹp là chỗ duy nhất chạy đủ nhanh
    # để bắt chúng trước khi gộp.
    # 16/10/2026. Cua luong mo cho Ke toan truong ma chua ai ky (PR #370) nam im tren
    # main ca buoi: `test_lg5` bat duoc no, nhung tep nay khong co trong cua hep nen
    # khong ai chay. Mot dot khac gop main vao moi an du. Dung loai hong cua hep sinh ra
    # de bat — hai lan deu xanh rieng, gop lai moi hong — nen no thuoc ve day.
    "tests/test_lg1_hai_bang_quyen_khop_nhau.py",
    "tests/test_lg2_mot_bang_chu_ky.py",
    "tests/test_ks_toan_quyen.py",
    "tests/test_le2b_ba_vai_ke_toan.py",
    "tests/test_hach_toan.py",
    "tests/test_misa.py",
)


def _dong_lenh() -> list[str]:
    """Các dòng LỆNH của ci.yml — bỏ hết dòng chú thích.

    Bỏ dòng chú thích không phải cho gọn. Đầu tệp ci.yml có hẳn một đoạn giải thích nhắc tên
    `workflow_dispatch` và tên từng tệp hàng rào; tìm chuỗi trên cả tệp thì LỜI CHÚ làm phép thử
    xanh trong khi phần LỆNH đã mất thứ ấy rồi. Đo bằng phép thử đột biến ngày 19/9/2026: bỏ hẳn
    `workflow_dispatch:` khỏi khối `on:` mà bản đầu của tệp này vẫn xanh — đúng cái bẫy ấy.
    """
    return [d for d in CI.read_text(encoding="utf-8").splitlines() if not d.lstrip().startswith("#")]


def _khoi_viec() -> dict[str, list[str]]:
    """Cắt phần `jobs:` của ci.yml ra thành từng VIỆC, chỉ lấy dòng lệnh.

    VÌ SAO CẦN CẮT. Mấy phép thử đầu tiên của tệp này tìm chuỗi trên CẢ khối lệnh gộp lại. Cách ấy
    đủ cho câu hỏi "chuỗi này còn không", nhưng SAI cho câu hỏi "việc NÀO có điều kiện gì": cả
    `backend`, `web` và `docker` đều khai `if: github.event_name != 'push'`, nên chỉ cần một trong
    ba việc còn khai là phép thử tìm-chuỗi vẫn xanh dù hai việc kia đã mất điều kiện. Từ 09/10/2026
    còn một câu hỏi nữa chỉ trả lời được theo từng việc: cửa hẹp `hang-rao-gop` phải KHÔNG có `if:`.

    Cắt theo thụt lề hai khoảng trắng dưới `jobs:` — đúng hình tệp ci.yml đang viết. Phép thử
    `test_ci7` đỏ nếu không cắt ra được việc `hang-rao-gop`, nên đổi hình tệp mà quên sửa đây thì
    biết ngay, không lặng lẽ cắt ra một bảng rỗng rồi xanh.
    """
    khoi: dict[str, list[str]] = {}
    ten = None
    trong_jobs = False
    for d in _dong_lenh():
        if d.rstrip() == "jobs:":
            trong_jobs = True
            continue
        if not trong_jobs or not d.strip():
            continue
        if not d.startswith(" "):          # ra khỏi khối jobs:
            trong_jobs = False
            continue
        if re.fullmatch(r"  [A-Za-z0-9_-]+:", d.rstrip()):
            ten = d.strip().rstrip(":")
            khoi[ten] = []
            continue
        if ten is not None:
            khoi[ten].append(d)
    return khoi


def _dong_pytest() -> str:
    dong = [d for d in _dong_lenh() if "python -m pytest" in d and "tests/" in d]
    assert len(dong) == 1, (
        "Phải có ĐÚNG MỘT dòng `python -m pytest tests/...` trong ci.yml — thấy "
        f"{len(dong)}. Nhiều dòng thì phép thử này không biết canh dòng nào."
    )
    return dong[0]


def test_ci1_moi_tep_hang_rao_deu_co_that():
    """Tệp kể tên trong ci.yml mà không tồn tại thì CI trên main sẽ đỏ mỗi lần gộp."""
    thieu = [t for t in HANG_RAO if not (GOC / "backend" / t).exists()]
    assert not thieu, (
        f"Các tệp hàng rào sau được ci.yml gọi tên nhưng KHÔNG CÓ trong kho: {thieu}. "
        "Đổi tên một tệp phép thử thì phải sửa cả dòng `pytest` trong .github/workflows/ci.yml."
    )


def test_ci2_ci_yml_goi_du_danh_sach_hang_rao():
    """Ai bớt một tệp khỏi dòng lệnh cho nhanh thì phép thử này đỏ ngay, không đợi tới lúc mất."""
    dong = _dong_pytest()
    thieu = [t for t in HANG_RAO if t not in dong]
    assert not thieu, (
        f"ci.yml KHÔNG gọi các hàng rào sau khi đẩy vào main: {thieu}. "
        "Bớt một hàng rào khỏi cửa hẹp là mở lại đúng chỗ hở mà cửa ấy sinh ra để bịt."
    )


def test_ci3_khong_goi_thua_tep_ngoai_danh_sach():
    """Chiều ngược lại: thêm tệp vào ci.yml mà quên khai ở đây thì danh sách này thành nói dối."""
    trong_ci = set(re.findall(r"tests/[A-Za-z0-9_]+\.py", _dong_pytest()))
    thua = sorted(trong_ci - set(HANG_RAO))
    assert not thua, (
        f"ci.yml gọi thêm {thua} mà danh sách HANG_RAO ở tệp này chưa có. "
        "Khai vào đây kèm một dòng nói vì sao nó là hàng rào chống đụng độ."
    )


def _dieu_kien_cua_viec(ten: str) -> list[str]:
    """`if:` CỦA VIỆC (thụt lề 4), không gồm `if:` của một BƯỚC (thụt lề 8).

    Hai thứ khác hẳn nhau: `if:` của việc quyết việc có chạy hay không, `if:` của bước chỉ bỏ qua
    một bước. `test_ci7` đã học bài này một lần — bản đầu của nó gom cả hai nên tự đỏ ngay lần
    chạy đầu trong khi ci.yml không sai. Gom về một hàm để lần sau không ai học lại.
    """
    khoi = _khoi_viec()
    assert ten in khoi, (
        f"Không cắt ra được việc `{ten}` từ khối `jobs:` của ci.yml. Hoặc việc ấy đã bị xoá, hoặc "
        f"hình thụt lề của tệp đã đổi và `_khoi_viec` cắt sai — cả hai đều phải sửa bằng tay, "
        f"đừng sửa phép thử cho hết đỏ."
    )
    return [d.strip() for d in khoi[ten] if re.fullmatch(r"    if:\s.*", d.rstrip())]


def test_ci4_bo_do_du_chay_ca_tren_main_con_docker_thi_khong():
    """Chỗ rò tiền: bộ đủ chạy hai lần cho một việc.

    Ngày 19/9/2026 trần chi tiêu Actions chạm đáy lúc 13 giờ và GitHub dừng hẳn mọi việc của bốn
    làn. Nguyên nhân là bộ đủ chạy cả trên PR lẫn trên main — lần thứ hai không chặn được gì vì mã
    đã vào kho rồi. Phép thử này để lần sau không ai lặng lẽ bật lại.

    ─────────────────────────────────────────────────────────────────────────────────────────────
    SIẾT LẠI 12/10/2026, VÀ LÝ DO ĐÁNG GHI
    ─────────────────────────────────────────────────────────────────────────────────────────────

    Bản cũ hỏi `"if: github.event_name != 'push'" in lenh` trên CẢ khối lệnh gộp lại. Lúc viết,
    ba việc `backend`, `web`, `docker` cùng khai câu ấy, nên chuỗi có mặt là đủ. Nhưng câu phép
    thử ĐỊNH hỏi là "việc `backend` còn điều kiện không", mà câu nó THẬT SỰ hỏi là "trong cả tệp
    còn chỗ nào mang chuỗi ấy không" — hai câu khác nhau, và chúng trùng kết quả chỉ vì hoàn cảnh.
    Chính `_khoi_viec` ở trên đã ghi ra cái bẫy này từ 09/10 mà phép thử vẫn để nguyên.

    Vòng CI-2 (12/10/2026) bỏ `if:` của việc `web`, và lúc ấy hoàn cảnh hết trùng: nếu mai ai gỡ
    nốt điều kiện của `backend`, chuỗi vẫn còn ở `docker` và phép thử cũ VẪN XANH trong khi bộ 28
    phút đã chạy lại trên mọi lần gộp. Nên nay hỏi THEO TỪNG VIỆC.

    Đây là lần thứ năm trong hai ngày một hàng rào quét chuỗi trả lời nhầm câu hỏi. Bài học đã
    ghi ở sổ làn Vòng: neo vào CÚ PHÁP và neo vào ĐÚNG PHẠM VI.
    """
    # ĐẢO CHIỀU CHO `backend` — 16/10/2026, Chủ tịch quyết.
    #
    # Phép thử này trước đây ghim `backend` PHẢI có `if: != 'push'`, và lý do ghi ở trên vẫn đọc
    # rất xuôi: mã đã vào kho rồi, chạy lại trên main chặn được gì. Lý do ấy bỏ sót một chuyện,
    # và chuyện ấy xảy ra thật trong ngày: cửa chặn trên PR đo nhánh gộp với main TẠI LÚC CHẠY,
    # nên hai PR cùng xanh riêng lẻ mà gộp lần lượt thì cái thứ hai có thể làm đỏ — và backend
    # không chạy trên main nên KHÔNG AI THẤY. PR #370 làm `test_lg5` đỏ; cái đỏ ấy nằm im cho
    # đến khi PR #367 gộp main vào và ăn nguyên nó.
    #
    # Nay `backend` KHÔNG được khai `if:` nào, và phép thử ghim chiều mới — để lần sau không ai
    # lặng lẽ tắt nó đi với đúng cái lý do nghe-xuôi ở trên.
    assert _dieu_kien_cua_viec("backend") == [], (
        "Việc `backend` phải chạy trên CẢ pull_request VÀ push, nên không khai `if:` nào. Khai "
        "lại `!= 'push'` là trả main về chỗ ĐỎ ÂM THẦM: bộ đủ chỉ đo nhánh gộp với main tại lúc "
        "chạy, nên hai PR xanh riêng lẻ gộp lần lượt vẫn làm main đỏ mà không ai thấy — đúng "
        "chuyện ngày 16/10/2026, và làn gộp sau là người lãnh. Nếu muốn tắt vì tốn máy thì phải "
        "có một quyết định mới, không phải một dòng YAML."
    )
    assert _dieu_kien_cua_viec("docker") == ["if: github.event_name != 'push'"], (
        "Việc `docker` (dựng ảnh, `needs: [backend, web]`) VẪN phải có `if: != 'push'`. Nó khác "
        "`backend`: trên main nó chỉ chờ thêm 45 phút để dựng một ảnh không ai dùng tới. Hai việc "
        f"khác nhau, không gộp một quyết định — thấy {_dieu_kien_cua_viec('docker') or 'không có'}."
    )
    assert "hang-rao-gop" in _khoi_viec(), (
        "Phải còn cửa hẹp `hang-rao-gop`. Bỏ hẳn nó thì hai PR cùng xanh riêng lẻ mà gộp lại hỏng "
        "sẽ không ai biết — đúng chuyện suýt xảy ra hai lần ngày 19/9/2026. Việc nó chạy trên những "
        "sự kiện nào thì `test_ci7` canh."
    )


def test_ci8_viec_web_phai_chay_ca_tren_pr_va_tren_main():
    """LUẬT MỚI 12/10/2026: phía GIAO DIỆN cũng cần một cửa canh chuyện hai nhánh gộp lại.

    ─────────────────────────────────────────────────────────────────────────────────────────────
    ĐO ĐƯỢC, VÀ PHÉP ĐO LẬT NGƯỢC CHẨN ĐOÁN BAN ĐẦU
    ─────────────────────────────────────────────────────────────────────────────────────────────

    Lượt CI #750 của PR #290 (MT-1): `backend` ĐỎ sau 28 phút, `web` ĐỎ sau 35 GIÂY,
    `hang-rao-gop` ĐỎ sau 49 giây. Việc `web` ĐÃ chạy trên PR và ĐÃ bắt được lỗi `Shell.tsx` —
    rồi PR vẫn được gộp với cả ba dấu đỏ. Nên lý do "lỗi lọt vào main vì `web` không chạy trên
    push" là SAI; nó lọt vào vì một PR đỏ được gộp, và không một dòng YAML nào chữa được điều đó.

    ─────────────────────────────────────────────────────────────────────────────────────────────
    VẬY LUẬT NÀY CANH GÌ
    ─────────────────────────────────────────────────────────────────────────────────────────────

    Đúng một thứ, và là thứ PR không thể bắt: hai nhánh mỗi nhánh DỰNG ĐƯỢC riêng lẻ, gộp lại thì
    hỏng. Một nhánh đổi tên một thành phần dùng chung, nhánh kia thêm chỗ gọi theo tên cũ — cả hai
    xanh trên PR của mình. `hang-rao-gop` canh đúng hình ấy ở phía máy chủ từ 19/9; phía giao diện
    tới 12/10/2026 vẫn chưa có ai canh. 1 phút 28 giây là giá rẻ cho chỗ trống ấy.

    CON SỐ NÀY ĐÃ SAI MỘT LẦN, giữ lại vết. Bản đầu viết "35 giây", lấy từ lượt `web` ĐỎ
    của PR #290 — một bản dựng HỎNG chết sớm, nên đó là thời gian của một lần THẤT BẠI.
    Lượt CI #771 (lần gộp đầu tiên theo luật mới) đo bản dựng THÀNH CÔNG: 1 phút 28 giây,
    cả lượt 1 phút 31 giây, so với 52 giây của lần gộp trước khi chỉ có cửa hẹp. Sai gấp
    hai lần rưỡi, và đó là con số đã dùng để xin quyết định.

    NÓ KHÔNG CHẶN ĐƯỢC GÌ và phép thử này không giả vờ ngược lại: trên main mã đã vào kho, đỏ ở
    đây chỉ là BÁO. Chặn thật đòi "Require status checks", mà GitHub từ chối ô ấy cho kho riêng
    của tài khoản cá nhân cho tới khi chuyển sang tổ chức GitHub Team — đo ngày 12/10/2026, nguyên
    văn trang Rulesets. Thứ ấy không nằm trong mã nên không canh được từ đây.
    """
    dieu_kien = _dieu_kien_cua_viec("web")
    assert not dieu_kien, (
        "Việc `web` lại có điều kiện: " + "; ".join(dieu_kien) + "\n\n"
        "Nó phải chạy trên CẢ pull_request VÀ push, nên không khai `if:` nào cả. Khai lại "
        "`!= 'push'` là bỏ lại chỗ trống phía giao diện: hai nhánh cùng dựng được riêng lẻ mà gộp "
        "lại hỏng sẽ không ai biết, và bản hỏng nằm trên main cho tới khi có người tình cờ mở ra "
        "xem — đúng cái đã xảy ra ngày 12/10/2026 và mất mấy tiếng mới ai đó thấy.\n\n"
        "Nếu muốn cắt tiền Actions thì cắt ở chỗ khác: việc này tốn 1 phút 28 giây một lượt, còn "
        "`backend` tốn 28 phút và vẫn đang được miễn trên push."
    )


def test_ci6_buoc_tinh_danh_sach_tep_doi_con_nguyen():
    """Hàng rào giữ chỗ làn đứng trên MỘT bước của ci.yml — gỡ bước ấy là nó tắt mà vẫn xanh.

    `backend/tests/test_giu_cho_nhanh.py` không tự gọi `git`: nó đọc danh sách tệp nhánh đổi từ
    biến `VTOS_TEP_DOI` do ci.yml tính sẵn. Cách ấy tốt hơn (bộ phép thử còn chạy ở hai chỗ không
    có thư mục .git), nhưng đổi lại nó nợ ci.yml một bước — và một món nợ không ai canh thì có
    ngày mất.

    Phép thử `test_gn1` bên kia đỏ khi CHẠY trên PR mà không thấy danh sách. Phép thử này đỏ sớm
    hơn một nhịp: khi bước ấy biến khỏi tệp cấu hình, kể cả lúc đang chạy ở chỗ khác.
    """
    lenh = "\n".join(_dong_lenh())
    assert "VTOS_TEP_DOI" in lenh, (
        "ci.yml không còn đặt biến `VTOS_TEP_DOI`. Không có nó thì hàng rào “đẩy mã lên phải có "
        "dòng đang làm trong docs/DANG-LAM.md” lặng lẽ không chạy nữa — đúng kiểu hỏng đã để "
        "TC-76 và TC-77 đè lên làn khác hai lần trong ngày 23/9/2026, cả hai lần CI đều xanh."
    )
    assert "git diff --name-only" in lenh, (
        "Mất dòng `git diff --name-only` thì tệp danh sách rỗng, và một danh sách rỗng làm hàng "
        "rào giữ chỗ làn xanh với mọi nhánh."
    )
    assert "if: github.event_name == 'pull_request'" in lenh, (
        "Bước tính danh sách phải giới hạn ở pull request. Trên push vào main, HEAD là một lần "
        "gộp và phép so với nhánh gốc không còn nghĩa như trên PR."
    )
    # 09/10/2026: từ khi cửa hẹp chạy cả trên PR, có HAI việc cùng chạy hàng rào giữ chỗ nhánh, ở
    # hai máy khác nhau. Mỗi máy phải tự tính danh sách. Không đếm "phải có hai bản" — đếm thì
    # thêm việc thứ ba là phải sửa phép thử. Hỏi theo luật: việc nào chạy hàng rào ấy thì việc ấy
    # phải đặt VTOS_TEP_DOI. Thiếu thì cửa hẹp đỏ trên MỌI PR vì thiếu môi trường, không vì có lỗi.
    thieu_bien = []
    for ten, dong in _khoi_viec().items():
        than = "\n".join(dong)
        if "test_giu_cho_nhanh.py" not in than and "run_all.sh" not in than:
            continue
        if "VTOS_TEP_DOI" not in than:
            thieu_bien.append(ten)
    assert not thieu_bien, (
        f"Việc {thieu_bien} chạy hàng rào giữ chỗ nhánh nhưng KHÔNG đặt `VTOS_TEP_DOI`. Luật `gn1` "
        "của test_giu_cho_nhanh BẮT BUỘC thấy danh sách tệp nhánh đổi khi chạy trên pull request, "
        "nên việc ấy sẽ đỏ trên mọi PR — đỏ vì thiếu môi trường chứ không vì có lỗi thật, và đó là "
        "kiểu đỏ làm người ta tắt hàng rào. Mỗi việc chạy ở một máy riêng nên phải tự tính danh sách."
    )


def test_ci7_cua_hep_phai_chay_ca_tren_pr_va_tren_main():
    """LUẬT MỚI 09/10/2026: cửa hẹp phải CHẶN được, nên nó phải chạy cả trên PR.

    ─────────────────────────────────────────────────────────────────────────────────────────────
    CHUYỆN ĐÃ XẢY RA
    ─────────────────────────────────────────────────────────────────────────────────────────────

    Trước ngày này, `hang-rao-gop` khai `if: github.event_name == 'push'` — chỉ chạy SAU khi mã đã
    vào kho. Nó BÁO, không CHẶN. Và ngày 09/10/2026 main đỏ đúng vì thế: hai làn cùng giữ
    `backend/app/services/access.py` (VB-1 của làn Phân quyền và PD-1 của làn Vòng đều còn
    `đang làm`), `test_giu_cho_lan` đỏ — nhưng đỏ trên main, lúc đã muộn.

    Chỗ đau không phải là thiếu cửa chặn. Cửa chặn ĐÃ CÓ: bộ đủ trên PR cũng chạy
    `test_giu_cho_lan`. Nhưng bộ đủ mất ~37 phút, PR được gộp vài phút sau khi mở, và đến lúc main
    đã đỏ thì lượt ấy vẫn còn trạng thái "In progress". **Một cửa chặn mà không ai chờ nổi thì
    trên thực tế là không có cửa nào.** Nên cái phải sửa là THỜI GIAN CHỜ, không phải thêm phép thử.

    ─────────────────────────────────────────────────────────────────────────────────────────────
    LUẬT
    ─────────────────────────────────────────────────────────────────────────────────────────────

    `hang-rao-gop` KHÔNG được khai `if:`. Bỏ trống thì nó chạy trên push, pull_request và cả
    workflow_dispatch — tức là chặn được trên PR (12 giây, chờ được) mà vẫn báo được trên main
    (chống chuyện hai PR cùng xanh riêng lẻ, gộp lại hỏng).

    Phép thử này KHÔNG canh việc "Require status checks" đã bật trong Settings của kho hay chưa:
    thứ ấy không nằm trong mã nên không đo được từ đây. Nó chỉ canh điều đo được — rằng cửa hẹp
    còn chạy trên PR. Ai bật ô ấy ở Settings thì từ đó mọi lần gộp bị chặn 12 giây.

    Và KHÔNG được chữa chỗ này bằng cách thêm một việc thứ hai chạy lại cùng dòng `pytest`:
    `_dong_pytest` bắt ci.yml có ĐÚNG MỘT dòng ấy, vì hai bản danh sách hàng rào là hai bản để
    lệch nhau.
    """
    khoi = _khoi_viec()
    assert "hang-rao-gop" in khoi, (
        "Không cắt ra được việc `hang-rao-gop` từ khối `jobs:` của ci.yml. Hoặc việc ấy đã bị xoá, "
        "hoặc hình thụt lề của tệp đã đổi và `_khoi_viec` cắt sai — cả hai đều phải sửa bằng tay, "
        "đừng sửa phép thử cho hết đỏ."
    )
    # Chỉ lấy `if:` CỦA VIỆC (thụt lề 4), không lấy `if:` của một BƯỚC (thụt lề 8). Hai thứ khác
    # nhau hẳn: `if:` của việc quyết việc có chạy hay không; `if:` của bước chỉ bỏ qua một bước —
    # và cửa hẹp CÓ một bước như thế, bước tính danh sách tệp đổi, chỉ chạy trên PR. Bản đầu của
    # phép thử này gom cả hai nên tự đỏ ngay lần chạy đầu; chỗ ấy là lỗi của phép thử, không phải
    # của ci.yml, nên sửa phép thử mới đúng — ghi lại đây để người sau không gom lại lần nữa.
    dieu_kien = [d.strip() for d in khoi["hang-rao-gop"] if re.fullmatch(r"    if:\s.*", d.rstrip())]
    assert not dieu_kien, (
        "Việc `hang-rao-gop` lại có điều kiện: " + "; ".join(dieu_kien) + "\n\n"
        "Cửa hẹp phải chạy trên CẢ pull_request VÀ push, nên nó không khai `if:` nào cả. Khai lại "
        "`== 'push'` là trả nó về đúng chỗ hở đã làm main đỏ ngày 09/10/2026: nó chỉ báo sau khi "
        "gộp, trong khi cửa chặn thật nặng ~37 phút nên không ai chờ. Khai `== 'pull_request'` thì "
        "mất chiều ngược lại: hai PR cùng xanh riêng lẻ mà gộp lại hỏng sẽ không ai biết.\n\n"
        "Nếu muốn cắt bớt tiền Actions thì cắt ở chỗ khác — việc này tốn ~50 giây một lượt."
    )


def test_ci5_bo_du_van_chay_khi_bam_tay():
    """`workflow_dispatch` là lối chạy đủ bộ trên main trước khi ra bản thật. Mất nó là mất lối ấy."""
    assert any(d.strip() == "workflow_dispatch:" for d in _dong_lenh()), (
        "ci.yml phải giữ `workflow_dispatch`: sau khi cắt bộ đủ khỏi main, đây là cách duy nhất "
        "chạy lại 251 tệp trên main mà không phải mở một PR giả."
    )
