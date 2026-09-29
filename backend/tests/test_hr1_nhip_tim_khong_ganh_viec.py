# -*- coding: utf-8 -*-
"""NHỊP TIM KHÔNG ĐƯỢC GÁNH VIỆC — 27/9/2026.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

Suốt ngày 19/9 và 27/9/2026, VTOS trả 502/503 hết lần này tới lần khác. Nguyên nhân đã bị đổ cho
"máy 512 MB hết bộ nhớ" — và đó là một kết luận SAI, ghi ra đây để không ai đi lại đường ấy.

Sổ sự kiện Render ngày 27/9 ghi nguyên văn, nhiều lần:

    Instance failed — HTTP health check failed (timed out after 5 seconds) while running your code

Render gọi `/api/v1/health` khoảng 5 giây một lần. Quá 5 giây không trả lời là nó GIẾT máy chủ.
Mà bản cũ của cửa ấy gọi `R.verify_chain(db)` — duyệt lại chuỗi băm của TOÀN BỘ bản ghi kiểm toán,
4.259 bản ghi vào ngày đo. Bấm giờ năm lần trên hệ thật lúc máy rảnh hoàn toàn:

    1073 ms · 1509 ms · 724 ms · 1053 ms · 1530 ms

Một giây rưỡi lúc RẢNH. Chỉ cần một việc thật chạy song song trên gói 0,5 CPU là vượt 5 giây, máy
chủ bị giết, và yêu cầu đang chạy dở trả về 503 — trông y hệt một lỗi mã, nên người đọc đi tìm lỗi
ở đúng chỗ không có lỗi.

Phép đo ấy cũng là lý do tệp này KHÔNG bấm giờ. Một phép thử kiểu "health phải chạy dưới N mili
giây" sẽ đỏ theo tốc độ máy chạy CI chứ không theo mã, và một phép thử đỏ ngẫu nhiên là cách nhanh
nhất khiến người ta thôi nhìn CI. Nên canh bằng HÌNH của cửa, không bằng đồng hồ: cửa này không
nhận `db`, và không gọi tới phép soát chuỗi bằng bất kỳ đường nào.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hr1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hr1.db"):
    os.remove("test_hr1.db")

import inspect                                                  # noqa: E402
import pytest                                                   # noqa: E402
from fastapi.testclient import TestClient                       # noqa: E402

from app.main import app                                        # noqa: E402
from app.api.v1 import routes as RT                             # noqa: E402
from app.services import rules as R                             # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_nhip_tim_con_song(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json().get("time"), "phải nói được lúc nào, để đọc sổ còn đối chiếu được"


def test_nhip_tim_khong_nhan_ket_noi_csdl():
    """Cửa này KHÔNG có tham số nào, `db` càng không.

    Không phải để tiết kiệm một câu lệnh SQL. Là để nó không bao giờ phải XẾP HÀNG chờ một kết nối
    trong bể. Đúng lúc hệ thống bận nhất — lúc cần biết nó còn sống nhất — là lúc bể cạn; một nhịp
    tim phải chờ bể thì sẽ im đúng lúc không được phép im, và Render giết máy chủ.
    """
    ts = inspect.signature(RT.health).parameters
    assert "db" not in ts, f"nhịp tim lại nhận kết nối CSDL: {list(ts)}"
    assert not ts, f"nhịp tim không được phụ thuộc gì cả, đang có: {list(ts)}"


def test_nhip_tim_van_dap_du_phep_soat_chuoi_co_no(client, monkeypatch):
    """Phép soát chuỗi có nổ tung thì nhịp tim vẫn phải đập.

    Đây là phép thử hành vi đi kèm phép thử hình ở trên. Hình bắt "không nhận db"; phép thử này bắt
    "không gọi tới việc nặng ấy bằng bất kỳ đường nào khác" — ví dụ một bản sửa sau này gọi thẳng
    `R.verify_chain(SessionLocal())` mà không qua tham số.
    """
    def no(*a, **k):
        raise AssertionError("nhịp tim vừa gọi phép soát chuỗi — đúng thứ đã giết máy chủ 27/9")
    monkeypatch.setattr(R, "verify_chain", no)
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_khong_tra_bua_chuoi_lanh(client):
    """Bỏ khoá `audit_chain_ok` hẳn, chứ KHÔNG trả sẵn `true` cho gọn.

    Một cửa im lặng khai "chuỗi lành" mà không hề kiểm thì nguy hiểm hơn hẳn việc không có khoá ấy:
    người đọc tin vào một câu không ai kiểm chứng. Thiếu thì còn biết là phải đi tìm chỗ khác.
    """
    j = client.get("/api/v1/health").json()
    assert "audit_chain_ok" not in j
    assert "audit_records" not in j


def test_kha_nang_soat_chuoi_khong_bi_mat():
    """Không mất việc nào — chỉ thôi chạy nó 17.000 lần một ngày.

    Phép soát chuỗi vẫn sống ở cửa `/api/v1/audit` của Ban kiểm soát. Nếu một bản sửa sau này gỡ nốt
    chỗ ấy đi thì hệ thống mất hẳn khả năng biết sổ kiểm toán có bị sửa trộm hay không.
    """
    assert "verify_chain" in inspect.getsource(RT.list_audit), \
        "cửa nhật ký kiểm toán thôi soát chuỗi — mất hẳn khả năng biết sổ có bị sửa trộm"
