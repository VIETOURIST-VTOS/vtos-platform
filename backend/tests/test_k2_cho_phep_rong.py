"""K2 bước 1 – 86 cột tiền được PHÉP rỗng. Quyết định Chủ tịch 09/9/2026.

Chủ tịch chốt: ở những cột này, MỌI số 0 nghĩa là "chưa nhập dữ liệu". Câu đó trả lời K2 cho cả 86 cột
một lượt. Nhưng nó không thi hành được trong một bước: trong mã có 316 dòng làm phép toán trên các cột
này, 242 dòng CHƯA an toàn với giá trị rỗng. Cho phép rỗng mà đồng thời để ô trống lưu rỗng là làm vỡ
242 chỗ đó, ở báo cáo cuối tháng.

  K2A  cả 86 cột đã cho phép rỗng trong mô hình
  K2B  mặc định VẪN là 0 – bước 1 không được đổi hành vi của bất kỳ dòng mã nào
  K2C  mạch nâng cấp khai đúng 86 cột, và chỉ nới ràng buộc chứ không đụng dữ liệu
  K2D  chiều hạ cấp nói rõ nó hỏng khi đã có dòng rỗng, và vì sao đó là hành vi đúng
  K2E  cho phép rỗng ở CSDL là CHƯA ĐỦ – mặc định 0 vẫn nuốt giá trị rỗng qua ORM
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


def test_k2a_86_cot_da_cho_phep_rong():
    import app.main  # noqa
    from app.db.session import Base
    sai = [f"{b}.{c}" for b, c in _cot() if not Base.metadata.tables[b].c[c].nullable]
    assert not sai, f"mô hình còn cấm rỗng thì cơ sở dữ liệu nới cũng vô nghĩa: {sai[:5]}"


def test_k2b_mac_dinh_van_la_0_buoc_1_khong_doi_hanh_vi():
    """Bước 1 chỉ mở KHẢ NĂNG. Đổi mặc định sang rỗng ngay bây giờ là đẩy giá trị rỗng vào 242 chỗ đọc
    chưa được gia cố – tức là làm đúng cái việc mà bước 1 cố tình tránh."""
    import app.main  # noqa
    from app.db.session import Base
    sai = []
    for b, c in _cot():
        d = Base.metadata.tables[b].c[c].default
        if getattr(d, "arg", None) != 0: sai.append(f"{b}.{c}")
    assert not sai, ("mặc định đã bị đổi khỏi 0 – bước 1 chưa được phép làm thế, phải gia cố 242 chỗ "
                     f"đọc trước: {sai[:5]}")


def test_k2c_mach_khai_dung_86_cot_va_chi_noi_rang_buoc():
    ds = _cot()
    assert len(ds) == 86 and len(set(ds)) == 86, f"phải đúng 86 cột, đang có {len(ds)}"
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


def test_k2e_cho_phep_rong_o_csdl_la_CHUA_DU_mac_dinh_0_van_nuot_gia_tri_rong():
    """PHÁT HIỆN quan trọng nhất của bước này, và nó phủ định chính kế hoạch ban đầu của bước này.

    Ý định ban đầu: bước 1 chỉ nới ràng buộc ở cơ sở dữ liệu, giữ mặc định 0, "an toàn tuyệt đối, mở
    sẵn khả năng ghi chưa-nhập cho bước sau". Phép thử này viết ra để chứng minh khả năng ấy đã mở.

    Nó chứng minh điều ngược lại: SQLAlchemy coi việc gán None là "hãy dùng giá trị mặc định". Nên
    chừng nào cột còn default=0 thì KHÔNG có cách nào ghi giá trị rỗng qua ORM – cơ sở dữ liệu cho
    phép rỗng, còn tầng ứng dụng thì nuốt mất nó.

    Hệ quả: K2 không tách được thành "an toàn trước, rủi ro sau" theo cách đã định. Muốn ô trống lưu
    thành rỗng thì phải bỏ mặc định 0, và ngay khi bỏ thì 242 chỗ đọc chưa gia cố sẽ gặp giá trị rỗng.
    Bước 1 vì vậy là ĐIỀU KIỆN CẦN, không phải một nửa việc đã xong.

    Giữ phép thử này lại chính vì nó nói ra điều đó. Ngày nào mặc định được bỏ, phép thử này đỏ – và
    đỏ đúng lúc: nó nhắc người sửa rằng 242 chỗ kia phải xong trước.
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

        # (1) ORM: gán None mà ra 0 – mặc định đã nuốt mất giá trị rỗng
        assert o.target_revenue == 0, (
            "Nếu dòng này đỏ nghĩa là mặc định 0 đã được bỏ. Trước khi mừng: 242 chỗ đọc chưa an toàn "
            "với giá trị rỗng đã được gia cố hết chưa?")

        # (2) cơ sở dữ liệu thì CHẤP NHẬN rỗng – phần nới ràng buộc đã có tác dụng thật
        db.execute(text("UPDATE mkt_budgets SET target_revenue = NULL WHERE id = :i"), {"i": o.id})
        db.commit()
        assert db.execute(text("SELECT target_revenue FROM mkt_budgets WHERE id = :i"),
                          {"i": o.id}).scalar() is None, \
            "cột chưa thật sự cho phép rỗng ở cơ sở dữ liệu"
    finally:
        db.execute(text("DELETE FROM mkt_budgets WHERE period = '2026-98'"))
        db.commit(); db.close()
