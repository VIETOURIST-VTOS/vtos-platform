"""P1 – trong kho chỉ còn MỘT kiểu khai quyền, và máy đọc được nó mà không phải phân tích mã nguồn.

Vì sao việc này đáng một tệp phép thử riêng:

Ngày 07/9/2026 robot Kiểm soát chạy vòng quét đầu tiên trên hệ thống thật và báo 26 việc nghiêm
trọng. Cả 26 đều SAI. Nguyên nhân không nằm ở robot mà ở kho: tồn tại song song hai kiểu chặn vai
trò – khai ở chữ ký hàm, và gọi AC.require(...) trong thân hàm – còn bộ kiểm chỉ nhìn thấy kiểu thứ
nhất. GET /audit chặn đúng, chỉ là chặn ở kiểu thứ hai.

Sai sót của người canh gác đắt hơn sai sót của người bị canh: một robot giám sát kêu oan 26 lần ngay
ngày đầu thì lần sau không ai đọc nó nữa, và đúng lúc nó báo thật thì lời báo đã mất giá trị.

Ba phép thử dưới đây khoá lại cả ba mặt của việc đó.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_p1_quyen.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p1_quyen.db", "test_p1_quyen.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pathlib
from app.main import app
from app.services import ks_robot as KS

API = pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "v1"


def test_khong_con_chan_vai_tro_trong_than_ham():
    """Kiểu thứ hai đã bị dọn hết. Thêm lại một chỗ là phép thử này đỏ."""
    con = []
    for p in sorted(API.glob("*.py")):
        for i, dong in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "AC.require(" in dong or "access.require(" in dong:
                con.append(f"{p.name}:{i}")
    assert not con, ("Còn chặn vai trò trong thân hàm – khai ở chữ ký để máy đọc được mà không phải "
                     f"phân tích mã nguồn: {con}")


def test_khong_endpoint_nao_con_phai_doc_ma_nguon():
    """Bộ kiểm phải nhận ra quyền từ CHỮ KÝ. Còn endpoint nào chỉ nhận ra được nhờ đọc mã nguồn thì
    lưới an toàn đang gánh việc của đường chính – và lưới đó im lặng khi rách."""
    con = KS.endpoint_phai_doc_ma_nguon(app)
    assert not con, f"Những endpoint này chỉ nhận ra quyền khi đọc mã nguồn: {con}"


def test_thong_bao_403_noi_ro_thieu_quyen_gi():
    """Người bị chặn phải đọc được mình thiếu quyền gì, không phải đoán. Một màn hình thiếu nút mà
    không có lời giải thích thì người dùng không phân biệt được 'không có quyền' với 'phần mềm hỏng'."""
    import pytest
    from fastapi import HTTPException
    from app.api.deps import require_roles
    from app.models.core import User
    u = User(username="x", full_name="Thử", role="nv_kd", password_hash="")

    with pytest.raises(HTTPException) as ex:
        require_roles("ketoan", mo_ta="quyết toán tour")(u=u)
    assert "quyết toán tour" in str(ex.value.detail)

    # Không khai mô tả thì vẫn giữ câu chung như trước, không vỡ giao diện đang đọc thông báo cũ
    with pytest.raises(HTTPException) as ex2:
        require_roles("ketoan")(u=u)
    assert "không có quyền" in str(ex2.value.detail)

    # Chủ tịch đi qua mọi cửa (FULL_ACCESS) – đây là quyết định 06/9, không được vỡ khi sửa require_roles
    ct = User(username="ct", full_name="Chủ tịch", role="chutich", password_hash="")
    assert require_roles("ketoan", mo_ta="quyết toán tour")(u=ct) is ct


def test_moi_endpoint_khai_quyen_deu_doc_duoc_danh_sach_vai_tro():
    """require_roles gắn sẵn danh sách vai trò lên chính hàm phụ thuộc, để bộ kiểm đọc được mà không
    phải suy từ tên hàm."""
    from app.api.deps import require_roles
    dep = require_roles("ketoan", "hcns")
    assert getattr(dep, "vai_tro_yeu_cau", None) == ("ketoan", "hcns")
