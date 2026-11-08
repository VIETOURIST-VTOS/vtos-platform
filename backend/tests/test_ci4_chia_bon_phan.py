"""CI-4 (08/11/2026) — bộ phép thử backend chia bốn máy chạy song song.

Chủ tịch chọn «Chia 4 máy chạy song song». Việc `backend` chạy lần lượt từng tệp trên một máy đã
dài 1 giờ 8 phút (sau #726) → 1 giờ 28 phút (sau #728) → vượt hạn 90 phút và bị huỷ (PR #731).

Hai điều canh ở đây:
  1. Chia phần KHÔNG bỏ sót và KHÔNG chạy trùng: hợp bốn phần đúng bằng toàn bộ tệp, từng đôi rời
     nhau. Một tệp rơi khỏi mọi phần là một hàng rào lặng lẽ không chạy — kiểu hỏng `run_all.sh`
     đã gặp ngày 11/9/2026.
  2. ci.yml khai đúng bốn phần và chuyển số phần xuống `run_all.sh`.
"""
import os, re, subprocess
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
RUN = GOC / "backend" / "tests" / "run_all.sh"
CI = GOC / ".github" / "workflows" / "ci.yml"


def _tep_cua_phan(phan: int, so: int) -> list[str]:
    """Chạy ĐÚNG đoạn chia phần của run_all.sh (không chạy pytest) và lấy danh sách tệp."""
    src = RUN.read_text(encoding="utf-8")
    i, j = src.index('SO_PHAN="${VTOS_SO_PHAN:-1}"'), src.index('echo "--- phần')
    doan = src[i:j] + 'printf "%s\\n" "${TEP[@]}"\n'
    kq = subprocess.run(["bash", "-c", doan], cwd=GOC / "backend", capture_output=True, text=True,
                        env={**os.environ, "VTOS_PHAN": str(phan), "VTOS_SO_PHAN": str(so)})
    assert kq.returncode == 0, kq.stderr
    return [d for d in kq.stdout.splitlines() if d.strip()]


def test_ci4_1_bon_phan_phu_du_va_khong_trung():
    tat_ca = sorted(str(p.relative_to(GOC / "backend")) for p in (GOC / "backend" / "tests").glob("test_*.py"))
    phan = [_tep_cua_phan(k, 4) for k in range(4)]
    gop = [t for p in phan for t in p]
    assert sorted(gop) == tat_ca, "hợp bốn phần phải đúng bằng toàn bộ tệp phép thử"
    assert len(gop) == len(set(gop)), "một tệp không được nằm ở hai phần"
    assert max(map(len, phan)) - min(map(len, phan)) <= 1, "bốn phần phải đều nhau"


def test_ci4_2_khong_dat_bien_thi_chay_het_nhu_cu():
    tat_ca = sorted(str(p.relative_to(GOC / "backend")) for p in (GOC / "backend" / "tests").glob("test_*.py"))
    src = RUN.read_text(encoding="utf-8")
    i, j = src.index('SO_PHAN="${VTOS_SO_PHAN:-1}"'), src.index('echo "--- phần')
    env = {k: v for k, v in os.environ.items() if k not in ("VTOS_PHAN", "VTOS_SO_PHAN")}
    kq = subprocess.run(["bash", "-c", src[i:j] + 'printf "%s\\n" "${TEP[@]}"\n'], cwd=GOC / "backend",
                        capture_output=True, text=True, env=env)
    assert sorted(d for d in kq.stdout.splitlines() if d.strip()) == tat_ca


def test_ci4_3_ci_yml_khai_bon_phan_va_chuyen_xuong_run_all():
    lenh = "\n".join(d for d in CI.read_text(encoding="utf-8").splitlines() if not d.lstrip().startswith("#"))
    i = lenh.index("\n  backend:")
    j = re.search(r"\n  [A-Za-z0-9_-]+:\n", lenh[i + 5:]).start() + i + 5
    than = lenh[i:j]
    assert "phan: [0, 1, 2, 3]" in than and "fail-fast: false" in than
    assert "VTOS_PHAN: ${{ matrix.phan }}" in than and "VTOS_SO_PHAN: 4" in than
    assert "bash tests/run_all.sh" in than
