# -*- coding: utf-8 -*-
"""MKT-10 — MỌI THAM SỐ MANG CHỮ PHẢI CÓ MỘT CỬA, HOẶC ĐƯỢC KHAI LÀ CHƯA CÓ CỬA.

Chín tháng màn Tham số chỉ nhận SỐ và NGÀY, và không ai biết, vì không ai thử ký lại một tham số
mang chữ. Lỗ ấy lộ ra ngày 11/11/2026 khi Chủ tịch bấm Trình để ký lại `pr_tu_do` của đợt MKT-9.

CA QUAN TRỌNG NHẤT Ở ĐÂY LÀ CA TỰ ĐẾM — `test_khong_tham_so_mang_chu_nao_bi_bo_quen`. Nó không
chép tay một danh sách nào; nó đọc chính bảng tham số đang chạy và đòi mọi giá trị không phải số
phải nằm trong một trong ba danh sách đã khai. Thêm một tham số chữ mới mà quên khai thì ca này
đỏ, nên lỗ này không mở lại trong im lặng được nữa.

Tệp này KHÔNG nằm trong 17 tệp của việc `hang-rao-gop` trên CI; nó chạy ở lượt hai của vòng.
"""
from __future__ import annotations

import json
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_mkt10.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_mkt10.db", "test_mkt10.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.core import User
from app.services import rules as R

client = TestClient(app)
MK = "mkt10test123456"
NGAY = "2026-11-12"

HINH_NGAY = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()
        for vai in ("ketoan", "chutich"):
            un = f"m10_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True))
        db.commit()
        db.close()
        yield


def login(vai):
    r = client.post("/api/v1/auth/login", data={"username": f"m10_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def trinh(khoa, gia_tri):
    return client.post("/api/v1/params", headers=login("ketoan"),
                       json={"key": khoa, "value": gia_tri, "effective_from": NGAY,
                             "source": "phép thử MKT-10"})


def loi_doc_duoc(r) -> str:
    """Lời báo của cửa, ĐÃ GIẢI MÃ dấu tiếng Việt.

    `r.text` là JSON thô nên "phải là số" nằm trong đó dưới dạng \\u1ea3i – so chuỗi trên bản thô
    là một phép so KHÔNG BAO GIỜ khớp, và ca thử sẽ xanh vì lý do sai.
    """
    try:
        return json.dumps(r.json(), ensure_ascii=False)
    except Exception:
        return r.text


# ══════════════════════════════════════════════════════════════════════════════════════════
# Ca tự đếm — ca giữ cho lỗ này không mở lại
# ══════════════════════════════════════════════════════════════════════════════════════════
def test_khong_tham_so_mang_chu_nao_bi_bo_quen():
    """Đọc CHÍNH bảng tham số đang chạy, không chép tay danh sách nào.

    Một tham số có giá trị không rỗng mà không phải số và không phải hình dạng ngày thì nó mang
    CHỮ, và nó phải nằm trong một trong ba danh sách đã khai. Không nằm ở đâu nghĩa là nó rơi
    xuống nhánh `float()` của cửa trình — tức là không ai đổi được nó, y như `pr_tu_do` suốt chín
    tháng vừa rồi.

    Ô TRỐNG KHÔNG TÍNH, và đó là chỗ ca này cố ý không đòi: một ô trống không nói được nó là số
    hay chữ. Những ô trống đã phân loại được bằng tay thì nằm trong `THAM_SO_CHUA_CO_CUA`.
    """
    da_khai = set(R.THAM_SO_NGAY) | set(R.THAM_SO_CHU) | set(R.THAM_SO_CHUA_CO_CUA)
    bo_quen = []
    for k, v, *_ in R.DEFAULT_PARAMS:
        if k in da_khai:
            continue
        s = str(v).strip()
        if not s:
            continue
        try:
            float(s)
            continue
        except ValueError:
            pass
        bo_quen.append((k, s[:48]))
    assert not bo_quen, (
        "THAM SỐ MANG CHỮ MÀ KHÔNG CÓ CỬA NHẬP — cửa trình sẽ trả về “Giá trị phải là số” và "
        "không ai đổi được chúng:\n"
        + "\n".join("  · %s = “%s”" % (k, v) for k, v in bo_quen)
        + "\n\nCách xử: khai tên nó vào `rules.THAM_SO_CHU` nếu nó là chữ thật, hoặc vào "
          "`rules.THAM_SO_CHUA_CO_CUA` nếu phần ấy thuộc làn khác quyết — xem sổ đợt MKT-10.")


def test_ba_danh_sach_khai_dung_ten_that_va_khong_chong_nhau():
    """Một tên khai sai chính tả là một dòng khai KHÔNG canh gì cả, và nó im lặng."""
    co_that = {k for k, *_ in R.DEFAULT_PARAMS}
    for ten, ds in (("THAM_SO_NGAY", R.THAM_SO_NGAY), ("THAM_SO_CHU", R.THAM_SO_CHU),
                    ("THAM_SO_CHUA_CO_CUA", R.THAM_SO_CHUA_CO_CUA)):
        la = [k for k in ds if k not in co_that]
        assert not la, f"{ten} khai tên không có trong bảng tham số: {la}"
    cap = [("THAM_SO_NGAY", set(R.THAM_SO_NGAY)), ("THAM_SO_CHU", set(R.THAM_SO_CHU)),
           ("THAM_SO_CHUA_CO_CUA", set(R.THAM_SO_CHUA_CO_CUA))]
    for i in range(len(cap)):
        for j in range(i + 1, len(cap)):
            chung = cap[i][1] & cap[j][1]
            assert not chung, f"{cap[i][0]} và {cap[j][0]} cùng khai: {sorted(chung)}"


def test_cua_chua_co_thi_khai_dung_ly_do_da_do_duoc():
    """`THAM_SO_CHUA_CO_CUA` chỉ được chứa hai loại, không phải một chỗ để cất tham số lười khai.

    Hai loại: hình dạng NGÀY mà chưa khai trong `THAM_SO_NGAY`, hoặc GIÁ TRỊ TRỐNG. Một tham số
    có giá trị chữ rõ ràng mà bị bỏ vào đây là tránh việc chứ không phải để lại có lý do.
    """
    gia_tri = {k: str(v).strip() for k, v, *_ in R.DEFAULT_PARAMS}
    sai = []
    for k in R.THAM_SO_CHUA_CO_CUA:
        s = gia_tri.get(k, "")
        if s and not HINH_NGAY.match(s):
            sai.append((k, s[:40]))
    assert not sai, (
        "THAM_SO_CHUA_CO_CUA chỉ dành cho tham số hình dạng NGÀY chưa khai, hoặc tham số GIÁ TRỊ "
        "TRỐNG. Những dòng dưới đây mang chữ rõ ràng nên phải vào `THAM_SO_CHU`:\n"
        + "\n".join("  · %s = “%s”" % (k, v) for k, v in sai))


# ══════════════════════════════════════════════════════════════════════════════════════════
# Cửa thật — gọi đúng cửa người dùng bấm
# ══════════════════════════════════════════════════════════════════════════════════════════
def test_cua_nhan_mot_tham_so_mang_chu():
    """Đây là lần bấm mà Chủ tịch đã bấm hôm 11/11 và bị chặn."""
    r = trinh("pr_tu_do", "lua dao,kiện,báo chí,nhà báo,tố")
    assert r.status_code == 201, r.text
    assert r.json()["param"]["value"] == "lua dao,kiện,báo chí,nhà báo,tố"
    assert r.json()["param"]["status"] == "pending"


def test_cua_van_tu_choi_chu_o_mot_tham_so_so():
    """Mở cửa cho chữ KHÔNG được làm thủng cửa số. Ngưỡng cảnh báo vẫn phải là một con số."""
    r = trinh("pr_nguong_canh_bao", "hai")
    assert r.status_code != 201, r.text
    assert "phải là số" in loi_doc_duoc(r), loi_doc_duoc(r)


def test_tham_so_chu_khong_duoc_de_trong_hay_xuong_dong():
    """Rỗng không phải một giá trị đã ký; xuống dòng cắt đôi mọi danh sách ngăn bằng dấu phẩy."""
    r = trinh("pr_tu_do", "   ")
    assert r.status_code != 201 and "để trống" in loi_doc_duoc(r), loi_doc_duoc(r)
    r = trinh("pr_tu_do", "lua dao\nkiện")
    assert r.status_code != 201 and "xuống dòng" in loi_doc_duoc(r), loi_doc_duoc(r)


def test_tham_so_chua_co_cua_noi_that_chu_khong_noi_phai_la_so():
    """Lời báo SAI tốn nhiều thời gian hơn không có lời báo.

    Bảo "giá trị phải là số" cho một tham số chưa có cửa thì người nhập đi sửa giá trị — mà thứ
    thiếu là cái cửa. Câu mới nói đúng chỗ thiếu và chỉ sang sổ.
    """
    r = trinh("cong_qr_tai_khoan", "0123456789")
    assert r.status_code != 201, r.text
    assert "CHƯA CÓ CỬA NHẬP" in loi_doc_duoc(r), loi_doc_duoc(r)
    assert "phải là số" not in loi_doc_duoc(r)


def test_tham_so_ngay_van_di_qua_cua_ngay_nhu_cu():
    """Đợt này không được đụng vào nhánh ngày đã mở từ 11/9/2026."""
    r = trinh("ngay_van_hanh_that", "khong-phai-ngay")
    assert r.status_code != 201, r.text
    assert "phải là ngày" in loi_doc_duoc(r), loi_doc_duoc(r)
