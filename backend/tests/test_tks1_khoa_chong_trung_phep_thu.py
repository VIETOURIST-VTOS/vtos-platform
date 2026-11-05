# -*- coding: utf-8 -*-
"""Đợt TKS-1 06/11/2026 — KHOÁ CHỐNG TRÙNG CỦA PHÉP THỬ KẾT SỔ KHÔNG ĐƯỢC DỰA VÀO ĐỒNG HỒ.

Đo trên main 06/11/2026: `test_ket_so.but_toan()` lấy `f"test:{datetime.now().timestamp()}"` làm
**mã nguồn** truyền cho `post_entry`. `datetime.now()` trên Windows nhảy từng ~15,6 ms, nên hai
bút toán gọi liền nhau trong cùng một nhịp nhận CÙNG MỘT mã — và khoá chống ghi sổ hai lần của
Đợt E3 (nguồn + mã nguồn + loại nghiệp vụ) chặn cái thứ hai.

LỖI NẰM Ở PHÉP THỬ, KHÔNG Ở SẢN PHẨM. `post_entry` cư xử đúng: nó từ chối ghi hai lần một sự
kiện. Chỗ chữa là làm mã nguồn duy nhất DO CÁCH DỰNG, không phải nới khoá cho dễ qua — nới khoá
để một phép thử hết đỏ là mở lại đúng chỗ hở mà khoá ấy sinh ra để bịt.

VÌ SAO NÓ CHỈ ĐỎ HÔM NAY: hai vòng bấm Đợt DS-3 ngày 06/11 đỏ ở đây (vòng đầu một phép thử, vòng
sau hai), trong khi ba vòng hôm 05/11 đều xanh. Một phép thử phụ thuộc TỐC ĐỘ MÁY chứ không phụ
thuộc mã là thứ sẽ quay lại vào đúng ngày bận nhất — và lúc ấy người ta sẽ nghi ngờ bản vá đang
chạy chứ không nghi phép thử.
"""
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_tks1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ket_so.py")


def test_tks1_1_ma_nguon_duy_nhat_KHI_DONG_HO_DUNG_YEN():
    """Đóng băng đồng hồ rồi đòi một nghìn lần gọi ra một nghìn mã khác nhau.

    Đóng băng là cách duy nhất đo được chuyện này cho CHẮC. Để đồng hồ chạy thật thì phép thử
    xanh trên máy chậm và đỏ trên máy nhanh — tức là nó đo tốc độ máy, không đo mã, và đó đúng
    là cái bệnh đợt này đang chữa.

    CẮT ĐÚNG HAI ĐỊNH NGHĨA RA CHẠY RIÊNG, không `import test_ket_so`: nhập cả tệp ấy kéo theo
    `app.main` và cả bộ mô hình, nên một phép đo hai dòng sẽ phụ thuộc vào việc cả ứng dụng nạp
    được hay không. Cắt bằng cây cú pháp thì nó đo ĐÚNG đoạn mã thật, và chỉ đoạn ấy.
    """
    import ast as _ast
    import itertools as _it

    cay = _ast.parse(open(TEP, encoding="utf-8").read())
    lay = [n for n in cay.body
           if (isinstance(n, _ast.FunctionDef) and n.name == "_ma_nguon")
           or (isinstance(n, _ast.Assign) and any(
               getattr(t, "id", "") == "_DEM_MA_NGUON" for t in n.targets))]
    assert len(lay) == 2, (
        "test_ket_so.py phải có ĐÚNG một bộ đếm `_DEM_MA_NGUON` và một hàm `_ma_nguon()` ở mức "
        f"mô-đun — thấy {len(lay)}. Không có chúng thì khoá chống trùng của phép thử lại dựa vào "
        "đồng hồ lúc nào không ai biết.")

    class _DongHoDungYen:
        @staticmethod
        def now():
            class _T:
                @staticmethod
                def timestamp():
                    return 1793900000.0
            return _T
    ns = {"itertools": _it, "datetime": _DongHoDungYen}
    exec(compile(_ast.Module(body=lay, type_ignores=[]), "<test_ket_so>", "exec"), ns)
    ra = {ns["_ma_nguon"]() for _ in range(1000)}
    assert len(ra) == 1000, (
        f"một nghìn lần gọi chỉ ra {len(ra)} mã khác nhau — mã nguồn vẫn dựa vào đồng hồ, nên "
        "hai bút toán gọi sát nhau sẽ nhận cùng một mã và khoá chống ghi sổ hai lần chặn cái "
        "thứ hai. Mã phải duy nhất DO CÁCH DỰNG.")


def test_tks1_2_phep_thu_ket_so_khong_con_lay_MOI_dong_ho_lam_khoa():
    """Chiều ngược: nếu ai đó lắp lại cách cũ thì luật này đỏ.

    Soi đúng khuôn cũ — một chuỗi mã nguồn kết thúc ngay sau `timestamp()` — chứ không cấm gọi
    đồng hồ: ghép thêm đồng hồ cho dễ đọc nhật ký thì vẫn tốt, miễn có bộ đếm đi kèm.
    """
    src = open(TEP, encoding="utf-8").read()
    ma = "\n".join(d for d in src.split("\n") if not d.lstrip().startswith("#"))
    xau = re.findall(r'f"test:\{[^}]*timestamp\(\)\}"', ma)
    assert not xau, (
        f"`test_ket_so.py` vẫn lấy MỖI đồng hồ làm khoá chống trùng: {xau}. Trên Windows đồng hồ "
        "nhảy từng ~15,6 ms nên hai bút toán liền nhau nhận cùng một mã.")
    assert "_ma_nguon()" in ma, "`but_toan()` không dùng `_ma_nguon()`"
