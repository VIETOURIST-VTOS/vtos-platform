"""Mỗi con số phải có một CỬA cho người nhập – phép thử giữ cho quy tắc ấy không mòn.

Ranh giới Chủ tịch đặt 09/9/2026: phần mềm viết cấu trúc, phép tính và luồng quản trị; SỐ LIỆU do nhân
viên tự nhập – gõ biểu, tải tệp, tải ảnh. Bảng nào không có cửa nào là VIỆC CÒN THIẾU, không phải chỗ
để ai đó nhập hộ vào cơ sở dữ liệu.

Bản rà tay 09/9 kết luận 120/128 bảng đủ cửa, 8 bảng máy sinh. Rà tay chỉ đúng tại thời điểm rà – bảng
thứ 129 thêm vào tuần sau sẽ không có ai rà lại. Những phép thử này là chỗ thay cho lần rà đó.

  CN1  mọi bảng trong mô hình phải có cửa, hoặc được khai là máy sinh KÈM LÝ DO
  CN2  cửa tải tệp đọc SỐNG từ sổ bộ nạp, không chép lại thành danh sách thứ hai
  CN3  "máy sinh" phải có lý do viết ra – đó là lối thoát dễ nhất cho một bảng thiếu cửa
  CN4  dòng khai cho bảng không còn trong mô hình thì báo, nhưng KHÔNG phải lỗi
  CN5  đã gắn vào vòng quét của robot, và mở đúng loại phát hiện
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_cuanhap.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_cuanhap.db", "test_cuanhap.db-journal"):
    if os.path.exists(f): os.remove(f)


def test_cn1_moi_bang_deu_phai_co_cua_hoac_duoc_khai_la_may_sinh():
    """Phép thử QUAN TRỌNG NHẤT của tệp này, và nó phải đỏ ngay khi ai đó thêm bảng mà quên cửa.

    Thông điệp lỗi cố ý nói ba lựa chọn, vì người gặp nó thường là người vừa thêm bảng và chưa nghĩ tới
    chuyện số liệu vào bằng đường nào – câu hỏi cần đặt ra đúng lúc đó, không phải một tháng sau.
    """
    from app.services import ks_cua_nhap as CN
    b = CN.bang()
    assert not b["khong_cua"], (
        "Có bảng không có cửa nào để người dùng đưa số liệu vào. Theo ranh giới 09/9/2026 thì đây là "
        "việc CÒN THIẾU, không phải chỗ để nhập hộ vào cơ sở dữ liệu. Chọn một trong ba: thêm bộ nạp "
        "tệp (intake.BO_NAP kèm bang_dich), thêm màn hình nhập tay rồi khai vào CUA_TAY, hoặc khai vào "
        f"MAY_SINH KÈM LÝ DO nếu người thật sự không bao giờ chạm tới: {b['khong_cua']}")
    assert b["so_bang"] > 100, "nạp thiếu mô hình thì phép thử này xanh một cách vô nghĩa"


def test_cn2_cua_tai_tep_doc_song_tu_so_bo_nap():
    """Chép danh sách bảng đích ra một chỗ thứ hai thì sớm muộn hai bảng lệch, và lúc lệch không ai
    biết bảng nào đúng. Nên phép thử này đòi con số đi thẳng từ sổ bộ nạp."""
    from app.services import ks_cua_nhap as CN
    from app.services.intake import BO_NAP
    tep = CN.cua_tai_tep()
    assert tep, "phải có bảng đích đọc được từ BO_NAP"
    for ma, bo in BO_NAP.items():
        b = bo.get("bang_dich")
        if b: assert ma in tep.get(b, []), f"bộ nạp {ma} khai bang_dich={b} nhưng không hiện ra"


def test_cn3_may_sinh_phai_co_ly_do_viet_ra():
    """“Máy sinh” là lối thoát dễ nhất để một bảng thiếu cửa được cho qua. Bắt viết lý do là cách rẻ
    nhất để người khai phải thật sự nghĩ: ai ghi vào bảng này, và vì sao người không cần chạm tới."""
    from app.services.ks_cua_nhap import MAY_SINH
    assert MAY_SINH, "phải có ít nhất vài bảng máy sinh – nhật ký robot, phát hiện kiểm soát…"
    for t, ly_do in MAY_SINH.items():
        assert ly_do and len(ly_do.strip()) >= 20, \
            f"bảng “{t}” khai là máy sinh nhưng lý do quá sơ sài: “{ly_do}”"


def test_cn4_khai_thua_thi_bao_nhung_khong_phai_loi():
    """Nhánh đang làm dở có bảng chưa gộp về (chuỗi bán hàng V6). Bắt lỗi ở đây thì mỗi lần đổi nhánh
    là một lần đỏ giả, và đỏ giả lặp lại là cách nhanh nhất để người ta thôi đọc phép thử."""
    from app.services import ks_cua_nhap as CN
    b = CN.bang()
    assert isinstance(b["khai_thua"], list), "phải nêu ra được, để dọn dần"
    mo = CN._bang_mo_hinh()
    for t in b["khai_thua"]:
        assert t not in mo


def test_cn5_da_gan_vao_vong_quet_va_khai_dung_loai_phat_hien():
    from app.services.ks_robot import BO_KIEM
    from app.services.ks_cua_nhap import _cua_nhap_du_lieu
    from app.models.kiem_soat import LOAI_PHAT_HIEN
    assert _cua_nhap_du_lieu in BO_KIEM, "bộ kiểm không nằm trong vòng quét thì nó không tồn tại"
    assert "bang_khong_cua_nhap" in LOAI_PHAT_HIEN, "chưa khai loại thì màn hình hiện mã thô"


def test_cn6_bang_moi_khong_cua_thi_phai_bi_bat():
    """Chốt chặn cho chính phép thử CN1: nếu nó xanh vì không nhìn thấy gì thì nó vô dụng.

    Dựng một bảng mới ngay trong mô hình rồi đòi bộ kiểm phát hiện ra – nếu không phát hiện thì CN1
    đang xanh một cách sai.
    """
    from app.services import ks_cua_nhap as CN
    from app.db.session import Base
    from sqlalchemy import Table, Column, Integer
    ten = "bang_thu_khong_cua_k5"
    t = Table(ten, Base.metadata, Column("id", Integer, primary_key=True), extend_existing=True)
    try:
        b = CN.bang()
        assert ten in b["khong_cua"], "bảng mới không cửa mà bộ kiểm không thấy thì CN1 vô dụng"
        ds = CN.quet(None)
        assert any(x["doi_tuong"] == ten for x in ds)
        assert all(x["loai"] == "bang_khong_cua_nhap" for x in ds)
    finally:
        Base.metadata.remove(t)
