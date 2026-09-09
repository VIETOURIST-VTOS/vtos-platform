"""V9/K1 – 47 cột tiền đổi từ số thực nhị phân sang numeric(18,2). Quyết định Chủ tịch 09/9/2026.

Vì sao đổi: cộng dồn số thực nhị phân thì lệch vài đồng, và lệch ở chỗ không ai nhìn. Với công ty đại
chúng thì đó đúng là chỗ kiểm toán đối chiếu đầu tiên. Phát hiện K1 mở từ 08/9.

Đo TRƯỚC khi đổi trên dữ liệu thật (09/9): trong toàn bộ cơ sở dữ liệu chỉ có 6 dòng mang phần lẻ dưới
đồng, và cả 6 nằm ở hai cột KHÔNG PHẢI TIỀN – fleet_trip_costs.lit (5 dòng, số lít) và ks_diem.diem
(1 dòng, điểm chấm). Không cột tiền nào mất số khi đổi. Phép đo ấy chỉ chạy được MỘT LẦN, trước khi
đổi – sau khi đổi thì luôn ra 0 vì cột mới không giữ nổi chữ số thứ ba.

  DK1  47 cột trong mô hình đã là Numeric, không còn Float
  DK2  purchase_invoices.thue_suat KHÔNG bị đổi – đó là thuế suất, không phải tiền
  DK3  mạch nâng cấp có đối chiếu tổng trước/sau và NÉM LỖI khi lệch (cuộn lại toàn bộ)
  DK4  mạch nâng cấp khai đúng 47 cột, không thừa không thiếu
  DK5  bộ xếp loại nay nhận ra "_suat" là tỷ lệ, nhưng không bắt nhầm cột bắt đầu bằng "suat"
  DK6  chiều hạ cấp nói rõ nó khôi phục KIỂU chứ không khôi phục SỐ
"""
import os, sys, io, json, re, pathlib
os.environ["DATABASE_URL"] = "sqlite:///./test_doikieu.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_doikieu.db", "test_doikieu.db-journal"):
    if os.path.exists(f): os.remove(f)

MACH = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions" / "zd4e5f6a7b8c_doi_kieu_cot_tien.py"


def _cot_trong_mach():
    s = MACH.read_text(encoding="utf-8")
    i = s.index("COT = (")
    return re.findall(r'\("([^"]+)",\s*"([^"]+)"\)', s[i:s.index("\n)", i)])


def test_dk1_47_cot_trong_mo_hinh_da_thanh_numeric():
    import app.main  # noqa
    from app.db.session import Base
    from sqlalchemy import Float, Numeric
    sai = []
    for bang, cot in _cot_trong_mach():
        c = Base.metadata.tables[bang].c[cot]
        if isinstance(c.type, Float) or not isinstance(c.type, Numeric):
            sai.append(f"{bang}.{cot} vẫn là {c.type}")
    assert not sai, ("Mạch nâng cấp đổi kiểu ở cơ sở dữ liệu nhưng mô hình còn khai Float – hai bên "
                     f"lệch nhau thì SQLAlchemy đọc ra sai kiểu: {sai}")


def test_dk2_thue_suat_khong_bi_doi_vi_no_la_ty_le_khong_phai_tien():
    """Cột DUY NHẤT trong 48 cột mà chưa có người xem lại, và nó là cột xếp sai.

    Máy xếp "tiền" vì tên chứa "thue". Bốn cột rate_per_day thì ngược lại: máy xếp "chưa rõ", người
    quyết "tiền", và người quyết đúng. Cơ chế K1 làm đúng việc – chỗ có người xem thì đúng, chỗ không
    ai xem thì sai.
    """
    import app.main  # noqa
    from app.db.session import Base
    from sqlalchemy import Float
    assert ("purchase_invoices", "thue_suat") not in _cot_trong_mach(), \
        "thuế suất không phải tiền – không được đổi kiểu theo diện cột tiền"
    assert isinstance(Base.metadata.tables["purchase_invoices"].c["thue_suat"].type, Float)


def test_dk3_mach_doi_chieu_tong_truoc_sau_va_nem_loi_khi_lech():
    """Lệnh DDL của PostgreSQL nằm trong giao dịch, nên ném lỗi là cuộn lại TOÀN BỘ 47 cột – không có
    trạng thái nửa vời. Đó là lý do phép đối chiếu phải nằm TRONG mạch, không nằm ở kịch bản chạy sau."""
    s = MACH.read_text(encoding="utf-8")
    assert "SUM(" in s, "phải cộng tổng để đối chiếu"
    assert s.count("SUM(") >= 2, "phải cộng CẢ TRƯỚC lẫn SAU, không chỉ một lần"
    assert "raise RuntimeError" in s, "lệch tổng mà không ném lỗi thì phép đối chiếu chỉ để trang trí"
    assert "ROUND(" in s, "viết rõ phép làm tròn thay vì để PostgreSQL tự ép"


def test_dk4_mach_khai_dung_47_cot():
    ds = _cot_trong_mach()
    assert len(ds) == 47, f"phải đúng 47 cột, đang có {len(ds)}"
    assert len(set(ds)) == 47, "có cột khai trùng"


def test_dk5_bo_xep_loai_nhan_ra_suat_la_ty_le():
    from app.services.ks_cot_tien import xep_theo_ten
    assert xep_theo_ten("thue_suat")[0] == "khong_tien"
    assert xep_theo_ten("lai_suat")[0] == "khong_tien", "lãi suất cũng là tỷ lệ"
    # nhưng không được bắt nhầm cột BẮT ĐẦU bằng suat
    assert xep_theo_ten("suat_an")[0] != "khong_tien", "tiền ăn ca là tiền thật"
    assert xep_theo_ten("tien_thue")[0] == "tien", "tiền thuế vẫn là tiền"


def test_dk6_ha_cap_noi_ro_no_khoi_phuc_kieu_chu_khong_khoi_phuc_so():
    """Người chạy lệnh hạ cấp lúc sự cố cần biết ngay điều này, không phải đọc mã mới hiểu."""
    s = MACH.read_text(encoding="utf-8")
    i = s.index("def downgrade")
    doc = s[i:i + 900]
    assert "KHÔNG khôi phục SỐ" in doc or "không khôi phục SỐ" in doc
