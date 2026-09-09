"""K2 – 83 cột tiền được phép rỗng, VÀ ô trống thật sự lưu thành rỗng. Quyết định Chủ tịch 09/9/2026.

Chủ tịch chốt: ở những cột này, MỌI số 0 nghĩa là "chưa nhập dữ liệu". Câu đó trả lời K2 cho cả 83 cột
một lượt – nhưng không thi hành được trong một bước. Trong mã có 316 dòng làm phép toán trên các cột
này, 242 dòng chưa an toàn với giá trị rỗng; cho phép rỗng mà chưa gia cố là làm vỡ 242 chỗ đó, ở báo
cáo cuối tháng chứ không phải lúc sửa.

Nên K2 đi ba bước, và tệp này ghi lại cả ba vì bước sau phủ định giả định của bước trước:

  bước 1  nới ràng buộc ở cơ sở dữ liệu (giữ nguyên mặc định 0)
  bước 2  gia cố 228 chỗ đọc – `or 0` ở tầng Python, `coalesce` ở tầng SQL
  bước 3  BỎ mặc định 0, để ô trống lưu thành rỗng

  K2A  cả 83 cột đã cho phép rỗng trong mô hình
  K2B  mặc định 0 đã được bỏ – và chỉ được bỏ SAU khi 228 chỗ đọc đã gia cố
  K2C  mạch nâng cấp khai đúng 83 cột, và chỉ nới ràng buộc chứ không đụng dữ liệu
  K2D  chiều hạ cấp nói rõ nó hỏng khi đã có dòng rỗng, và vì sao đó là hành vi đúng
  K2E  ô trống đi qua ORM và nằm lại trong cơ sở dữ liệu là rỗng, không bị nuốt thành 0

Ba cột từng nằm trong danh sách 86 đã bị loại: hai cột đúng/sai (`khong_phai_chi_phi`, `over_budget`)
và một cột đếm chỗ (`seats_promo`). Rỗng ở một cột đúng/sai nghĩa là "chưa biết", một khái niệm khác
hẳn "chưa nhập số tiền" – gộp vào là hứa một đằng làm một nẻo. K2 chỉ nhận cột tiền.
"""
import os, sys, re, pathlib
os.environ["DATABASE_URL"] = "sqlite:///./test_k2rong.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_k2rong.db", "test_k2rong.db-journal"):
    if os.path.exists(f): os.remove(f)

MACH = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions" / "ze5f6a7b8c9d_k2_cho_phep_rong.py"


def _cot():
    s = MACH.read_text(encoding="utf-8")
    i = s.index("COT = (")
    return re.findall(r'\("([^"]+)",\s*"([^"]+)"\)', s[i:s.index("\n)", i)])


def test_k2a_83_cot_da_cho_phep_rong():
    import app.main  # noqa
    from app.db.session import Base
    sai = [f"{b}.{c}" for b, c in _cot() if not Base.metadata.tables[b].c[c].nullable]
    assert not sai, f"mô hình còn cấm rỗng thì cơ sở dữ liệu nới cũng vô nghĩa: {sai[:5]}"


def test_k2b_mac_dinh_0_da_duoc_bo():
    """Đây là dòng thật sự đổi hành vi phần mềm: từ đây, ô trống lưu thành rỗng chứ không thành 0.

    Phép thử này trước kia khẳng định điều NGƯỢC LẠI – "mặc định vẫn phải là 0" – và nó đúng ở thời
    điểm ấy, vì 242 chỗ đọc chưa gia cố. Đảo nó là việc phải làm ở bước 3, không phải việc lén sửa cho
    xanh: điều kiện để đảo là phép thử canh chỗ đọc (test_k2_doc_an_toan.py) xanh.
    """
    import app.main  # noqa
    from app.db.session import Base
    sai = []
    for b, c in _cot():
        d = Base.metadata.tables[b].c[c].default
        if d is not None: sai.append(f"{b}.{c}={getattr(d, 'arg', d)}")
    assert not sai, ("còn cột giữ mặc định – ô trống ở những cột này vẫn bị ghi thành 0, tức là vẫn "
                     f"không phân biệt được 'chưa nhập' với 'bằng 0': {sai[:5]}")


def test_k2c_mach_khai_dung_83_cot_va_chi_noi_rang_buoc():
    ds = _cot()
    assert len(ds) == 83 and len(set(ds)) == 83, f"phải đúng 83 cột, đang có {len(ds)}"
    s = MACH.read_text(encoding="utf-8")
    assert "DROP NOT NULL" in s
    for cam in ("UPDATE ", "DELETE ", "INSERT "):
        assert cam not in s.upper(), f"bước 1 không đụng dữ liệu – không được có “{cam.strip()}”"


def test_k2d_ha_cap_noi_ro_no_hong_khi_da_co_dong_rong():
    """Người chạy hạ cấp lúc sự cố cần biết ngay: lệnh này DỪNG nếu đã có dòng rỗng, và dừng là đúng.

    Nếu nó tự biến "chưa nhập" thành 0 để đặt lại được NOT NULL thì nó vừa dựng lại đúng chỗ mù mà K2
    sinh ra để xoá.
    """
    s = MACH.read_text(encoding="utf-8")
    doc = s[s.index("def downgrade"):]
    assert "CHỈ CHẠY ĐƯỢC" in doc or "chỉ chạy được" in doc.lower()
    assert "âm thầm" in doc or "không được phép" in doc


def test_k2e_o_trong_di_qua_ORM_van_con_la_rong():
    """Phép thử từng phủ định kế hoạch của chính đợt này. Giờ nó xác nhận điều ngược lại.

    Bản đầu tiên viết ra để chứng minh "bước 1 đã mở sẵn khả năng ghi chưa-nhập". Nó chứng minh điều
    ngược lại: SQLAlchemy coi việc gán None là "hãy dùng giá trị mặc định", nên chừng nào cột còn
    default=0 thì KHÔNG có cách nào ghi rỗng qua ORM – cơ sở dữ liệu cho phép rỗng, còn tầng ứng dụng
    nuốt mất nó. Nhờ đó mới biết K2 không tách được thành "an toàn trước, rủi ro sau", và bước 1 là
    điều kiện cần chứ không phải một nửa việc đã xong.

    Bước 3 bỏ mặc định. Phép thử giữ nguyên cấu trúc, đảo kỳ vọng: gán None phải ra None, và đọc lại
    từ cơ sở dữ liệu vẫn phải là None. Đây là chỗ duy nhất chứng minh cả đường đi – biểu nhập gửi ô
    trống, ORM ghi, cơ sở dữ liệu giữ – chứ không chỉ chứng minh cột đã cho phép rỗng.
    """
    import app.main  # noqa
    from app.db.session import SessionLocal, Base, engine
    from app.models.marketing import MarketingBudget as MktBudget
    from sqlalchemy import text
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        o = MktBudget(period="2026-98", target_revenue=None)
        db.add(o); db.commit(); db.refresh(o)

        # (1) ORM: gán rỗng phải RA rỗng. Nếu ra 0 nghĩa là còn một mặc định ở đâu đó nuốt mất nó.
        assert o.target_revenue is None, (
            f"gán rỗng mà đọc lại ra {o.target_revenue!r} – còn mặc định nuốt giá trị rỗng, "
            "ô trống trên biểu nhập vẫn sẽ bị ghi thành 0")

        # (2) và cơ sở dữ liệu cũng giữ đúng rỗng, không phải chỉ đối tượng trong bộ nhớ
        assert db.execute(text("SELECT target_revenue FROM mkt_budgets WHERE id = :i"),
                          {"i": o.id}).scalar() is None, \
            "đối tượng thì rỗng nhưng cơ sở dữ liệu lại có số – tầng ghi đang tự điền"

        # (3) 0 vẫn phải ghi được là 0. Phân biệt được hai thứ mới là mục đích, không phải cấm số 0.
        z = MktBudget(period="2026-97", target_revenue=0)
        db.add(z); db.commit(); db.refresh(z)
        assert z.target_revenue == 0, "0 do người nhập cố ý phải lưu là 0, không được biến thành rỗng"
    finally:
        db.execute(text("DELETE FROM mkt_budgets WHERE period IN ('2026-98', '2026-97')"))
        db.commit(); db.close()
