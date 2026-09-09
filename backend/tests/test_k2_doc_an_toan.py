"""Canh cửa cho bước 2 của K2: mọi chỗ ĐỌC cột tiền trong phép tính phải chịu được giá trị rỗng.

Vì sao cần một phép thử canh chuyện này thay vì tin vào lần sửa hôm nay:

Bước 1 của K2 cho phép 86 cột tiền nhận giá trị rỗng, vì "0" và "chưa nhập" là hai chuyện khác nhau
và trước đó phần mềm không phân biệt được. Bước 2 gia cố 228 chỗ đọc để phép tính không vỡ khi gặp
rỗng. Nhưng chỗ đọc thì mỗi tuần lại thêm, còn cái vỡ thì không kêu: `None - 0` ném lỗi ngay giữa
một báo cáo, và người dùng chỉ thấy màn hình trắng chứ không thấy dòng nào sai.

Nên phép thử này quét mã nguồn, không quét dữ liệu. Nó đọc danh sách cột tiền TỪ MÔ HÌNH chứ không
từ một danh sách chép tay - thêm cột tiền mới là nó tự canh luôn, không phải nhớ sửa chỗ này.

Bốn chỗ ĐƯỢC bỏ qua, và lý do:
  * tên lớp viết hoa (`JournalLine.debit`) - đó là cột SQL để dựng câu truy vấn, không phải giá trị
    Python. Bọc `or 0` vào đấy làm SQLAlchemy ném lỗi. Bản chạy tự động ngày 09/9 đã bọc nhầm 16 chỗ.
  * vế trái phép gán - `x.amount = ...` không phải phép đọc.
  * vế đang so sánh với None - `if x.amount is None` là chốt kiểm có chủ ý, bọc vào là phá nó.
  * chuỗi ký tự.

Khi phép thử này đỏ: KHÔNG nới danh sách bỏ qua. Sửa dòng mã, thêm `or 0`.

Có đúng một lối thoát, và nó cố ý phiền: viết `# k2-doc-an-toan: <lý do>` ở cuối dòng. Dùng khi chỗ
đọc thật sự an toàn theo cách máy quét chữ không thấy được - ví dụ giá trị đi qua một hàm tự ép rỗng
thành 0. Phải có lý do bằng chữ; để trống là phép thử vẫn đỏ. Lối thoát này nằm trong bản vá nên
người duyệt nhìn thấy, khác hẳn việc lặng lẽ nới danh sách bỏ qua trong chính phép thử.
"""
import pathlib
import re

from sqlalchemy import Float, Numeric

from app.db.session import Base
import app.models  # noqa: F401  - nạp đủ mô hình trước khi đọc Base.metadata

GOC = pathlib.Path(__file__).resolve().parents[1] / "app"

# Dấu hiệu "dòng này có phép tính". Cố ý rộng: thà xét thừa một dòng rồi bỏ qua, còn hơn bỏ sót.
TOAN = re.compile(r"[-+*/]|\bsum\(|\bround\(|\babs\(|\bmax\(|\bmin\(")
SAU_GAN = re.compile(r"\s*(?:\+=|-=|\*=|/=|=(?!=))")
SO_SANH_NONE = re.compile(r"\s*(?:is\s+(?:not\s+)?|[=!]=\s*)None\b")
# Lối thoát có ghi lý do. Không có lý do thì không được miễn.
MIEN = re.compile(r"#\s*k2-doc-an-toan:(.*)$")


def ten_cot_tien() -> set:
    """Tên các cột tiền ĐƯỢC PHÉP rỗng, đọc thẳng từ mô hình.

    Numeric mà không phải Float là quy ước kiểu tiền của V9. `nullable` là điều kiện khiến việc đọc
    trở nên nguy hiểm: cột không cho rỗng thì đọc thẳng vẫn an toàn.
    """
    return {c.name for t in Base.metadata.tables.values() for c in t.columns
            if isinstance(c.type, Numeric) and not isinstance(c.type, Float) and c.nullable}


def vi_tri_gan(dong: str) -> int:
    """Vị trí dấu '=' của phép gán ở mức ngoài cùng; -1 nếu dòng này không phải phép gán.

    Phải tự dò thay vì dùng biểu thức chính quy vì `a, b.amount, c = ...` cũng là vế trái, mà dấu '='
    thì nằm cách xa. Bản chạy tự động ngày 09/9 vấp đúng chỗ này.
    """
    sau = 0
    nhay = None
    i = 0
    while i < len(dong):
        c = dong[i]
        if nhay:
            if c == "\\":
                i += 2
                continue
            if c == nhay:
                nhay = None
        elif c in "\"'":
            nhay = c
        elif c == "#":
            break
        elif c in "([{":
            sau += 1
        elif c in ")]}":
            sau -= 1
        elif c == "=" and sau == 0:
            if dong[i - 1:i] in ("=", "!", "<", ">", "+", "-", "*", "/", "%") or dong[i + 1:i + 2] == "=":
                i += 1
                continue
            return i
        i += 1
    return -1


def quet() -> list:
    ten = ten_cot_tien()
    if not ten:
        return []
    mau = re.compile(r"(?<![\w.])([A-Za-z_][\w\.]*?)\.(%s)\b"
                     % "|".join(map(re.escape, sorted(ten, key=len, reverse=True))))
    xau = []
    for tep in sorted(GOC.rglob("*.py")):
        for so, dong in enumerate(tep.read_text(encoding="utf-8").split("\n"), 1):
            if "mapped_column" in dong or not TOAN.search(dong):
                continue
            mien = MIEN.search(dong)
            if mien and mien.group(1).strip():
                continue
            g = vi_tri_gan(dong)
            for m in mau.finditer(dong):
                dau, cuoi = m.start(), m.end()
                if m.group(1)[0].isupper():          # cột SQL, không phải giá trị Python
                    continue
                if dong[cuoi:cuoi + 5] == " or 0":   # đã gia cố
                    continue
                if cuoi < len(dong) and dong[cuoi] == "(":
                    continue
                if SAU_GAN.match(dong, cuoi) or (g != -1 and dau < g):
                    continue
                if SO_SANH_NONE.match(dong[cuoi:]):
                    continue
                if dau > 0 and dong[dau - 1] in "\"'":
                    continue
                xau.append((str(tep.relative_to(GOC.parent)), so, dong.strip()[:120]))
    return xau


def test_khong_con_cho_doc_cot_tien_chua_chiu_duoc_rong():
    xau = quet()
    assert not xau, (
        "Có chỗ đọc cột tiền trong phép tính mà chưa chịu được giá trị rỗng. Cột tiền được phép rỗng "
        "từ đợt K2 - rỗng ở đây không phải lỗi dữ liệu mà là 'nhân viên chưa nhập'. Sửa bằng cách bọc "
        "`or 0` quanh chỗ ĐỌC, đừng nới danh sách bỏ qua của phép thử này:\n"
        + "\n".join(f"  {t}:{s}  |  {d}" for t, s, d in xau[:40])
        + (f"\n  ... và {len(xau) - 40} chỗ nữa" if len(xau) > 40 else ""))


def test_phep_thu_nay_con_nhin_thay_cot_tien():
    """Nếu cách đọc mô hình hỏng thì hàm quét trả về rỗng và phép thử trên xanh vĩnh viễn - xanh giả.

    Một phép thử canh cửa mà không còn nhìn thấy cái nó canh thì tệ hơn là không có, vì nó vẫn báo yên.
    """
    ten = ten_cot_tien()
    assert len(ten) >= 50, f"Chi thay {len(ten)} ten cot tien cho phep rong - dot K2 khai 86 cot (56 ten khac nhau). Cach doc mo hinh hong?"
    assert "amount" in ten, "Khong thay ca cot 'amount' - gan nhu chac chan mo hinh chua duoc nap du."
