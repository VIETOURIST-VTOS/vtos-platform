"""Mạch migration phải luôn có ĐÚNG MỘT đầu.

Vì sao cần phép thử này: Dockerfile chạy `alembic upgrade head` khi container khởi động. Alembic từ
chối chạy khi có nhiều hơn một đầu, nên hai nhánh migration cùng nối một gốc = container không lên
được = API sập ở lần deploy tới. Lỗi này KHÔNG lộ ra khi chạy test thường (test dùng create_all, không
chạy migration) và cũng không lộ khi chạy thử ở máy, nên nó chỉ hiện ra đúng lúc tệ nhất.

Ngày 07/9/2026 việc này xảy ra BA lần trong một buổi, vì hai phiên làm việc song song trên cùng một kho
cùng viết migration mới trên cùng một gốc. Người viết sau không thấy bản của người viết trước.
"""
import os, re, sys

VERSIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic", "versions")


def doc_mach() -> dict:
    """{revision: down_revision}. Đọc bằng biểu thức chính quy chứ không nạp mô-đun: các tệp migration
    có thể nhập những thứ chưa cài trong môi trường chạy test."""
    mach = {}
    for f in sorted(os.listdir(VERSIONS)):
        if not f.endswith(".py") or f.startswith("__"): continue
        src = open(os.path.join(VERSIONS, f), encoding="utf-8").read()
        r = re.search(r'^revision(?:\s*:\s*str)?\s*=\s*["\']([^"\']+)["\']', src, re.M)
        d = re.search(r'^down_revision(?:\s*:\s*[^=]+?)?\s*=\s*(?:["\']([^"\']+)["\']|None)', src, re.M)
        if not r: continue
        assert r.group(1) not in mach, f"trùng revision {r.group(1)} ở {f}"
        mach[r.group(1)] = d.group(1) if (d and d.group(1)) else None
    return mach


def test_dung_mot_dau_mach():
    mach = doc_mach()
    da_duoc_noi = {d for d in mach.values() if d}
    dau = sorted(r for r in mach if r not in da_duoc_noi)
    assert len(dau) == 1, (
        f"mạch migration có {len(dau)} đầu: {dau}. Dockerfile chạy 'alembic upgrade head' – nhiều hơn "
        f"một đầu là container không khởi động được. Sửa bằng cách cho bản viết sau nối tiếp bản viết trước "
        f"(đổi down_revision), KHÔNG gộp bằng merge revision.")


def test_dung_mot_goc_va_khong_dut_doan():
    mach = doc_mach()
    goc = [r for r, d in mach.items() if d is None]
    assert len(goc) == 1, f"phải có đúng một bản khởi tạo, đang có {goc}"
    for r, d in mach.items():
        assert d is None or d in mach, f"{r} nối sau {d} nhưng không có bản migration nào mang mã đó"


def test_khong_co_vong_lap():
    mach = doc_mach()
    for r in mach:
        di, cur = set(), r
        while cur is not None:
            assert cur not in di, f"mạch migration có vòng lặp tại {cur}"
            di.add(cur); cur = mach.get(cur)


def test_moi_ban_deu_co_ham_upgrade_va_downgrade():
    """Không có downgrade thì một bản vá hỏng trên web thật là không lùi lại được."""
    thieu = []
    for f in sorted(os.listdir(VERSIONS)):
        if not f.endswith(".py") or f.startswith("__"): continue
        src = open(os.path.join(VERSIONS, f), encoding="utf-8").read()
        if "def upgrade(" not in src or "def downgrade(" not in src: thieu.append(f)
    assert not thieu, f"migration thiếu upgrade/downgrade: {thieu}"
