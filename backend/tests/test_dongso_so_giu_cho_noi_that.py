# -*- coding: utf-8 -*-
"""ĐỢT ĐÓNG-SỔ (28/10/2026) — QUYỂN SỔ GIỮ CHỖ PHẢI NÓI THẬT.

VÌ SAO CÓ TỆP NÀY

Quyển sổ `docs/dang-lam/phan-quyen.md` là hàng rào chống hai làn cùng sửa một tệp. Nó chỉ có giá
trị khi nó NÓI THẬT. Ngày 28/10/2026 đo được 13 dòng `đang làm` mà phần lớn đã gộp vào main từ
hai ngày trước — và quyển sổ ấy chặn đúng một đợt hợp lệ (DỌN-MISA).

Một hàng rào nói sai còn tệ hơn không có hàng rào: hàng rào thật thì người ta tin, nên khi nó nói
sai thì người ta tin điều sai. Đây là lần thứ tư trong tuần cùng một hình — chặn IM LẶNG:

  · chốt canh `git log -40` hết hạn, chặn Đợt R2-KC1 mà chỉ nói "không thấy";
  · `test_misa` đỏ vì tệp khác chiếm cơ sở dữ liệu, mà đỏ ở chỗ không gây ra lỗi;
  · bước so làn của Đợt R6b-1 tách dòng sai số cột nên bỏ qua MỌI dòng rồi báo an toàn;
  · và quyển sổ này.
"""
import datetime
import pathlib
import re

SO = pathlib.Path(__file__).resolve().parents[2] / "docs" / "dang-lam"

# Mã việc ở đầu phần mô tả: `**BC-1 — ...`, `**CG-1b — ...`, `**DỌN-MT — ...`.
MA_DONG = re.compile(r"^\s*(?:\*\*\s*)?([A-ZĐ][A-ZĐa-z0-9]{0,3}-[0-9]+[a-z]?)\b")

# Một làn lành mạnh sống vài giờ: lấy main, vá, chạy phép thử, đẩy. BA NGÀY là đã rộng rãi gấp
# nhiều lần. Con số này KHÔNG phải để đúng tới từng giờ — nó là một cái chuông. Chuông kêu thì
# chỉ có hai khả năng, và cả hai đều là việc phải nhìn: làn treo thật, hoặc quyển sổ nói sai.
TRAN_NGAY = 3


def _dong_dang_lam():
    ra = []
    for p in sorted(SO.glob("*.md")):
        for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not l.rstrip().endswith("| đang làm |"):
                continue
            o = l.split("|")
            if len(o) != 7:
                continue          # số cột là việc của `test_giu_cho_lan`
            ra.append((p.name, i, o[2].strip(), o[4].strip()))
    return ra


def test_dongso_1_dong_dang_lam_khong_duoc_de_qua_lau():
    """Cái chuông. Nó không hỏi làn ấy đúng hay sai — nó hỏi quyển sổ còn đáng tin không."""
    cu = []
    for ten, so_dong, mo_ta, bat_dau in _dong_dang_lam():
        try:
            ngay = datetime.datetime.strptime(bat_dau.split()[0], "%d-%m-%Y").date()
        except (ValueError, IndexError):
            continue          # ngày không đọc được là việc của luật 3
        tuoi = (datetime.date.today() - ngay).days
        if tuoi > TRAN_NGAY:
            cu.append(f"{ten}:{so_dong} — {mo_ta[:60]} (bắt đầu {bat_dau}, {tuoi} ngày)")

    assert not cu, (
        f"Dòng `đang làm` để quá {TRAN_NGAY} ngày:\n  " + "\n  ".join(cu) + "\n\n"
        "Chỉ có hai khả năng, và cả hai đều phải nhìn: (1) làn ấy TREO THẬT — ai đó bỏ dở giữa "
        "chừng, và tệp nó giữ đang chặn người khác; (2) làn ấy ĐÃ GỘP mà quên đóng dòng — lúc "
        "ấy quyển sổ nói sai, và nó chặn những đợt hợp lệ trong im lặng. Đóng dòng đã gộp "
        "thành `xong`, hoặc nói rõ vì sao làn kia còn treo.")


def test_dongso_2_moi_dong_phai_doc_duoc_ma_viec():
    """Không có mã việc thì không ai — người hay máy — biết làn ấy đã gộp chưa.

    Bản vá của đợt này đóng dòng bằng cách hỏi git: mã việc ở đầu mô tả có khớp mã ở đầu một
    tiêu đề commit trên main không. Một dòng không mang mã là một dòng KHÔNG BAO GIỜ đóng được
    tự động — nó sống mãi và giữ tệp mãi.
    """
    xau = [f"{ten}:{so_dong} — {mo_ta[:70]}"
           for ten, so_dong, mo_ta, _ in _dong_dang_lam() if not MA_DONG.match(mo_ta)]
    assert not xau, (
        "Dòng `đang làm` không đọc được mã việc ở đầu mô tả:\n  " + "\n  ".join(xau) + "\n\n"
        "Mô tả phải mở đầu bằng `**<MÃ> — ...**`, ví dụ `**BC-1 — BÁO CÁO NGÀY...**`, và mã ấy "
        "phải trùng mã đặt ở đầu tiêu đề commit (`BC-1: bao cao ngay...`). Đó là sợi dây duy "
        "nhất nối một dòng sổ với lịch sử main.")


def test_dongso_3_moi_dong_phai_doc_duoc_ngay_bat_dau():
    """Ngày không đọc được thì cái chuông ở luật 1 lặng lẽ bỏ qua dòng ấy — và một cái chuông
    có lỗ thủng thì không phải là một cái chuông."""
    xau = []
    for ten, so_dong, mo_ta, bat_dau in _dong_dang_lam():
        try:
            datetime.datetime.strptime(bat_dau.split()[0], "%d-%m-%Y")
        except (ValueError, IndexError):
            xau.append(f"{ten}:{so_dong} — cột Bắt đầu là {bat_dau!r} ({mo_ta[:40]})")
    assert not xau, (
        "Cột `Bắt đầu` không đọc được theo khuôn `dd-mm-yyyy HH:MM`:\n  " + "\n  ".join(xau))
