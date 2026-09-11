"""KS-1 · Đọc mạch migration từ CÂY LÀM VIỆC và từ NHÁNH CHÍNH, rồi so hai bên.

Vì sao phải có tệp này, viết ra để người đọc sau không gỡ nhầm:

Ngày 10/9/2026 nhánh chính được đẩy lên kèm một bản nâng cấp móc vào `v14b6e9c2a7d31` — một bản CHỈ
CÓ trong cây làm việc của một phiên, chưa bao giờ được gộp lên nhánh chính. Render triển khai và chết
ở `alembic upgrade head` với KeyError: 'v14b6e9c2a7d31'. Máy chủ giữ lại bản đang chạy nên VTOS vẫn
phục vụ bình thường; không ai thấy gì bất thường. Nhưng MỌI lần triển khai sau đó đều hỏng y hệt, và
nó chỉ lộ ra vào đúng lúc tệ nhất — lúc cần vá gấp một lỗi trên web thật.

Phép thử `test_mach_migration.py` đã có từ 07/9 vẫn XANH suốt lúc đó. Nó xanh vì nó đọc thư mục
`alembic/versions` của CÂY LÀM VIỆC, mà cây làm việc của người viết thì có đủ cả v14 lẫn bản mới. Đó
chính là chỗ lỗi lọt qua: phép thử đo cái máy của người viết, còn Render đọc cái nhánh đã đẩy. Hai thứ
khác nhau, và không ai so chúng với nhau.

Cho nên quy tắc của KS-1 là: mỗi `down_revision` phải trỏ tới một bản CÓ THẬT TRÊN NHÁNH CHÍNH, hoặc
tới một bản mới khác trong cùng lần đẩy này mà tổ tiên của nó chạm được nhánh chính. Kiểm trên cây
làm việc là chưa đủ và sẽ tiếp tục xanh nhầm.

Bẫy thứ hai, đang chờ sẵn ngay lúc viết tệp này: nhánh `gop-dot2` có v14 nối sau v11, còn nhánh chính
có w1 nối sau v13, mà v13 cũng nối sau v11. Hai nhánh ấy GỘP LẠI thì mạch có HAI ĐẦU (v14 và w1) và
alembic từ chối chạy. Từng nhánh đứng riêng đều xanh. Chỉ phép thử "xem trước bản gộp" mới thấy.

Ba mức kiểm, từ rẻ tới đắt:
    M1  cây làm việc      – luôn chạy được, không cần git
    M2  nhánh chính       – cần git và một ref phân giải được (mặc định origin/main)
    M3  xem trước bản gộp – hợp mạch cây làm việc với mạch nhánh chính rồi soi lại
"""
from __future__ import annotations

import os
import re
import subprocess

# Ref của nhánh được triển khai. Render deploy nhánh main, nên đây là thứ phải so.
NHANH_CHINH = os.environ.get("VTOS_NHANH_CHINH", "origin/main")

# Ref dự phòng khi máy chưa có origin (bản sao chép tay, CI không fetch). Thứ tự có ý nghĩa.
REF_DU_PHONG = ("origin/main", "main", "refs/remotes/origin/main", "refs/heads/main")

_RE_REV = re.compile(r'^revision(?:\s*:\s*str)?\s*=\s*["\']([^"\']+)["\']', re.M)
_RE_DOWN = re.compile(r'^down_revision(?:\s*:\s*[^=]+?)?\s*=\s*(?:["\']([^"\']+)["\']|None)', re.M)

GOC_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THU_MUC_VERSIONS = os.path.join(GOC_BACKEND, "alembic", "versions")


# ---------------------------------------------------------------- phân tích văn bản

def doc_mot_ban(src: str):
    """Trả (revision, down_revision) đọc bằng biểu thức chính quy.

    Cố ý KHÔNG import mô-đun migration: nhiều bản nhập thư viện chưa cài trong môi trường chạy phép
    thử, và một bản migration hỏng import sẽ làm cả bộ kiểm im lặng thay vì báo đỏ.
    """
    r = _RE_REV.search(src)
    if not r:
        return None, None
    d = _RE_DOWN.search(src)
    return r.group(1), (d.group(1) if (d and d.group(1)) else None)


def doc_mach_tu_cay(thu_muc: str = THU_MUC_VERSIONS) -> dict:
    """{revision: down_revision} đọc từ thư mục versions trên đĩa."""
    mach = {}
    for f in sorted(os.listdir(thu_muc)):
        if not f.endswith(".py") or f.startswith("__"):
            continue
        src = open(os.path.join(thu_muc, f), encoding="utf-8", errors="replace").read()
        rev, down = doc_mot_ban(src)
        if not rev:
            continue
        if rev in mach:
            raise AssertionError(f"trùng mã revision {rev} ở {f}")
        mach[rev] = down
    return mach


# ---------------------------------------------------------------- đọc qua git

def _git(*args, cwd=GOC_BACKEND, dau_vao: bytes | None = None):
    """Chạy git, trả bytes stdout, hoặc None nếu git không có / lệnh hỏng.

    Nuốt lỗi có chủ đích: máy không có git vẫn phải chạy được mức M1. Chỗ nào CẦN git thì gọi
    `bat_buoc_co_git()` để báo đỏ thay vì lặng lẽ bỏ qua.
    """
    try:
        p = subprocess.run(("git",) + args, cwd=cwd, input=dau_vao,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def goc_kho() -> str | None:
    out = _git("rev-parse", "--show-toplevel")
    return out.decode().strip() if out else None


def ref_dung_duoc() -> str | None:
    """Ref đầu tiên phân giải được, ưu tiên VTOS_NHANH_CHINH."""
    for ref in (NHANH_CHINH,) + REF_DU_PHONG:
        if _git("rev-parse", "--verify", "--quiet", ref + "^{commit}"):
            return ref
    return None


def doc_mach_tu_nhanh(ref: str) -> dict | None:
    """{revision: down_revision} đọc từ CÂY CỦA MỘT REF trong git, không đụng tới đĩa.

    Đây là điểm khác biệt duy nhất mà cũng là toàn bộ giá trị của KS-1: nội dung ở đây là thứ Render
    sẽ nhận được, không phải thứ đang nằm trên máy người viết.
    """
    goc = goc_kho()
    if goc is None:
        return None
    rel = os.path.relpath(THU_MUC_VERSIONS, goc).replace(os.sep, "/")
    # Chạy từ GỐC KHO: pathspec của git tính theo thư mục hiện tại, không tính theo gốc kho. Gọi từ
    # backend/ với đường dẫn "backend/alembic/versions" thì git trả về rỗng mà KHÔNG báo lỗi — đúng
    # kiểu im lặng mà bộ kiểm này sinh ra để chống.
    ds = _git("ls-tree", "-r", "-z", ref, "--", rel, cwd=goc)
    if ds is None:
        return None

    # Mỗi mục: "<mode> <type> <sha>\t<path>\0"
    blob = {}
    for muc in ds.split(b"\0"):
        if not muc:
            continue
        dau, _, duong = muc.partition(b"\t")
        phan = dau.split()
        if len(phan) != 3 or phan[1] != b"blob":
            continue
        ten = duong.decode("utf-8", "replace").rsplit("/", 1)[-1]
        if not ten.endswith(".py") or ten.startswith("__"):
            continue
        blob[phan[2].decode()] = ten

    if not blob:
        return {}

    # Lấy nội dung một lượt bằng cat-file --batch: 1 tiến trình cho ~80 tệp thay vì 80 tiến trình.
    ra = _git("cat-file", "--batch", cwd=goc, dau_vao="\n".join(blob).encode() + b"\n")
    if ra is None:
        return None

    mach, i = {}, 0
    while i < len(ra):
        nl = ra.find(b"\n", i)
        if nl < 0:
            break
        dong = ra[i:nl].split()
        if len(dong) < 3:
            break
        sha, kich = dong[0].decode(), int(dong[2])
        src = ra[nl + 1: nl + 1 + kich].decode("utf-8", "replace")
        i = nl + 1 + kich + 1  # +1 cho ký tự xuống dòng sau nội dung
        rev, down = doc_mot_ban(src)
        if not rev:
            continue
        if rev in mach:
            raise AssertionError(f"trùng mã revision {rev} trên {ref} (tệp {blob.get(sha)})")
        mach[rev] = down
    return mach


# ---------------------------------------------------------------- soi mạch

def dau_mach(mach: dict) -> list:
    """Các bản không ai nối tiếp. Nhiều hơn một = alembic từ chối chạy."""
    da_noi = {d for d in mach.values() if d}
    return sorted(r for r in mach if r not in da_noi)


def goc_mach(mach: dict) -> list:
    return sorted(r for r, d in mach.items() if d is None)


def moc_treo(mach: dict) -> list:
    """[(revision, down_revision)] mà down_revision KHÔNG có trong mạch.

    Đây đúng là hình dạng của sự cố 10/9: w1 nối sau v14, v14 không có trên nhánh chính.
    """
    return sorted((r, d) for r, d in mach.items() if d is not None and d not in mach)


def vong_lap(mach: dict) -> list:
    xau = []
    for r in mach:
        di, cur = set(), r
        while cur is not None:
            if cur in di:
                xau.append(cur)
                break
            di.add(cur)
            cur = mach.get(cur)
    return sorted(set(xau))


def hop_mach(cay: dict, nhanh: dict):
    """Hợp hai mạch để xem trước bản gộp. Trả (mach_hop, xung_dot).

    xung_dot = [(revision, down_trên_nhánh, down_trong_cây)] — cùng một mã revision mà hai bên khai
    cha khác nhau. Nghĩa là ai đó đã đổi down_revision của một bản ĐÃ ĐẨY; chỗ nào đã chạy migration
    rồi thì bảng alembic_version không biết đường lùi.
    """
    hop = dict(nhanh)
    xung_dot = []
    for r, d in cay.items():
        if r in hop and hop[r] != d:
            xung_dot.append((r, hop[r], d))
        hop[r] = d
    return hop, sorted(xung_dot)


def rieng_cua_cay(cay: dict, nhanh: dict) -> list:
    """Bản có trong cây làm việc mà chưa có trên nhánh chính — tức là hàng sắp đẩy."""
    return sorted(r for r in cay if r not in nhanh)


def bao_cao(mach: dict, ten: str) -> str:
    return (f"{ten}: {len(mach)} bản · đầu={dau_mach(mach)} · gốc={goc_mach(mach)} "
            f"· móc treo={moc_treo(mach)} · vòng lặp={vong_lap(mach)}")
