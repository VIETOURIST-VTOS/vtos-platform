# -*- coding: utf-8 -*-
"""ĐỢT KS-17 — đường nào GỬI TIN CHO KHÁCH thì lịch KHÔNG được gọi lại, và phải ghi sổ từng tin.

ĐO ĐƯỢC, KHÔNG SUY (21/10/2026). Dựng một máy chủ làm việc lâu hơn hạn chờ rồi gọi bằng ĐÚNG
dòng `call` của `robots.yml` (`curl -m 60 --retry 3 --retry-delay 15 --retry-all-errors`):

    may chu NHAN yeu cau #1 … #2 … #3 … #4
    may chu LAM XONG #1 … #2 … #3 … #4
    curl thoat ma 28   (bao hong ca bon lan)

Một lần gọi theo lịch → máy chủ chạy BỐN lần, cả bốn làm xong. `--retry-all-errors` thử lại cả
khi hết hạn chờ (mã 28), mà hết hạn chờ KHÔNG có nghĩa là việc chưa chạy: máy chủ vẫn chạy tiếp
sau khi curl bỏ đi (đường robot là hàm đồng bộ, không ai huỷ nó khi khách ngắt).

HAI LỖ, ĐỘC LẬP NHAU, và phải bịt cả hai — bịt một cái thì cái kia vẫn đủ gây gửi trùng:

  (a) PHÍA GỌI. `/robot/inbox/check` cho AI gửi tin cho khách; `/robot/zalo/send-pending` gửi tối
      đa 100 tin Zalo. Gọi lại hai đường ấy là gửi trùng cho khách. Tin đã bay đi không rút về
      được, nên thà bỏ một lượt 30 phút.

  (b) PHÍA MÁY CHỦ. `zalo.send_pending` bản cũ ghi sổ MỘT LẦN ở cuối, sau cả 100 lần gọi sang
      Zalo. Lượt thứ hai khởi động 15 giây sau đọc `status` vẫn là `cho_gui` — vì lượt đầu chưa
      ghi — nên gửi lại ĐÚNG những tin ấy. Ghi từng tin thì không lượt nào thấy tin người khác
      vừa gửi là còn chờ.

ĐỪNG sửa phép thử cho hết đỏ. Đỏ ở đây nghĩa là một tin có thể tới khách hai lần.
"""
import ast
import inspect
import os
import pathlib
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOC = pathlib.Path(__file__).resolve().parents[2]
LICH = GOC / ".github/workflows/robots.yml"

# Đường có tác động RA NGOÀI công ty: mỗi lần chạy là một tin nhắn tới khách.
GUI_RA_NGOAI = ("/robot/inbox/check", "/robot/zalo/send-pending")
HAN_TOI_THIEU = 170


def _lich() -> str:
    return LICH.read_text(encoding="utf-8")


def _dong_goi(duong: str) -> list[str]:
    return [l.strip() for l in _lich().splitlines()
            if duong in l and not l.strip().startswith("#")]


# ── (a) phía gọi ────────────────────────────────────────────────────────────────────────────
def test_ks17_1_lich_co_mot_cach_goi_KHONG_thu_lai():
    s = _lich()
    assert "goi_mot_lan() {" in s, "chưa có cách gọi không thử lại"
    than = s.split("goi_mot_lan() {", 1)[1].split("}", 1)[0]
    assert "--retry" not in than, "cách gọi một lần vẫn còn --retry — nó không khác gì `call`"
    assert "curl" in than


def test_ks17_2_call_cu_van_con_cho_duong_khong_gui_tin():
    """Đường chỉ kéo số về thì thử lại là ĐÚNG — bản vá không được bỏ mất nó."""
    s = _lich()
    assert "call() {" in s
    than = s.split("call() {", 1)[1].split("}", 1)[0]
    assert "--retry" in than


def test_ks17_3_duong_gui_tin_cho_khach_KHONG_duoc_goi_lai():
    for duong in GUI_RA_NGOAI:
        dong = _dong_goi(duong)
        assert dong, f"không thấy dòng nào gọi {duong} trong lịch"
        for l in dong:
            assert l.startswith("goi_mot_lan "), (
                f"{duong} đang gọi bằng `call` (có --retry) — một lần hết hạn chờ là khách "
                f"nhận tin bốn lần:\n    {l}")


def test_ks17_4_duong_gui_tin_phai_co_han_cho_du_dai():
    """Hết hạn chờ không còn gọi lại, nên hạn phải đủ dài để việc chạy xong trong một lượt."""
    for duong in GUI_RA_NGOAI:
        for l in _dong_goi(duong):
            m = re.search(r"-m (\d+)", l)
            assert m, f"dòng gọi {duong} không khai hạn chờ:\n    {l}"
            assert int(m.group(1)) >= HAN_TOI_THIEU, (
                f"{duong} chỉ có {m.group(1)} giây mà không được gọi lại — "
                f"việc chưa xong là mất cả lượt:\n    {l}")


# ── (b) phía máy chủ ────────────────────────────────────────────────────────────────────────
def _ghi_trong_vong_lap(ham) -> bool:
    """Có `db.commit()` nằm TRONG thân vòng lặp `for` không (chứ không chỉ ở cuối hàm)?

    Đọc bằng cây cú pháp chứ không bằng thụt đầu dòng: đầu vòng lặp của `send_pending` trải trên
    năm dòng, nên đếm khoảng trắng là đọc trượt — bản đầu của phép thử này trượt đúng như thế.
    """
    cay = ast.parse(textwrap.dedent(inspect.getsource(ham)))
    for nut in ast.walk(cay):
        if not isinstance(nut, (ast.For, ast.While)):
            continue
        for trong in ast.walk(ast.Module(body=nut.body, type_ignores=[])):
            if (isinstance(trong, ast.Call) and isinstance(trong.func, ast.Attribute)
                    and trong.func.attr == "commit"):
                return True
    return False


def test_ks17_5_zalo_ghi_so_tung_tin_mot():
    from app.services import zalo as Z
    assert _ghi_trong_vong_lap(Z.send_pending), (
        "send_pending vẫn dồn ghi sổ tới cuối — lượt chạy thứ hai sẽ thấy tin đã gửi là còn chờ "
        "và gửi lại cho khách")


def test_ks17_6_hop_thu_ghi_so_ngay_sau_moi_tin_gui():
    """`inbox._send` đã ghi ngay từ trước — phép thử này canh để không ai gỡ đi."""
    from app.services import inbox as IB
    ma = inspect.getsource(IB._send)
    assert "db.commit()" in ma, "inbox._send không ghi sổ — tin AI đã gửi có thể biến mất"


def test_ks17_7_phep_do_khong_tu_hong():
    """Phép thử trên đọc tệp lịch thật. Tệp không còn thì mọi phép trên xanh giả."""
    assert LICH.exists(), f"không thấy {LICH}"
    assert "VTOS robots" in _lich()
