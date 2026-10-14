"""V2 – đọc chứng từ ảnh ra số. Cửa thứ ba, và là cửa duy nhất có máy đứng giữa.

Bộ test này canh đúng một câu: KHÔNG CÓ ĐƯỜNG NÀO ĐỂ SỐ MÁY ĐỌC VÀO HỆ THỐNG MÀ THIẾU MỘT LẦN BẤM CỦA
NGƯỜI. Mọi phép thử dưới đây là một cách câu đó có thể bị phá:

  1. Thêm một nhánh ghi thẳng khi máy "đủ tự tin" — chặn bằng phép thử đếm chỗ gọi hàm ghi.
  2. Để bản nháp nằm trên bảng đích với một cái cờ, rồi một báo cáo quên lọc — chặn bằng bảng riêng.
  3. Cho người vận hành mô hình tự xác nhận kết quả của mô hình mình chạy — chặn bằng P5.
  4. Máy điền 0 vào ô mờ, người lướt qua không thấy gì lạ — chặn bằng lọc 0 thành RỖNG.
  5. Đưa bảng lương qua mô hình vì "cũng là chứng từ" — chặn bằng hằng số trong mã.
  6. Ghi hai lần một hóa đơn vì người dùng tải lại ảnh — chặn bằng chỉ mục duy nhất trên bản đang chờ.
  7. Máy đọc ngày một kém đi mà không ai biết — chặn bằng tỷ lệ ô phải sửa và ngưỡng hạ mức.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_docct.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
os.environ["STORAGE_DIR"] = os.path.join(tempfile.gettempdir(), "vtos_test_docct_files")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

# Một ảnh PNG 1x1 hợp lệ – đủ để đi qua kho tệp; nội dung không quan trọng vì mô hình được thay bằng
# hàm giả trong mọi phép thử cần số.
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
       b"\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00"
       b"\x00\x00IEND\xaeB`\x82")


def anh(n: int) -> bytes:
    """Ảnh khác nhau cho mỗi phép thử: băm khác nhau thì kho tệp và hàng chờ không lẫn vào nhau."""
    return PNG + b"\x00" * n


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


@pytest.fixture()
def may(monkeypatch):
    """Thay chỗ gọi mô hình. Phép thử không được phụ thuộc vào mạng, vào khóa API, hay vào việc một
    mô hình thật hôm nay đọc đúng hay sai."""
    from app.services import doc_chung_tu as D

    def dat(tho, loi=""):
        monkeypatch.setattr(D, "_goi_mo_hinh", lambda loai, data, kieu: {
            "nguon": "claude", "mo_hinh": "mo-hinh-thu", "tho": tho, "loi": loi,
            "tokens_vao": 100, "tokens_ra": 50})
    return dat


def _hd_tho(**kw):
    d = {"mst_nguoi_ban": "0301234567", "ten_nguoi_ban": "Khách sạn ABC", "ky_hieu": "1C26TAA",
         "so_hoa_don": "00000501", "ngay_hd": "20/08/2026", "noi_dung": "Tiền phòng đoàn",
         "tien_truoc_thue": "10000000", "thue_suat": "8", "tien_thue": "800000",
         "tong_tien": "10800000"}
    d.update(kw); return d


# ====================== ĐIỀU CẤM ======================
def test_khong_doc_bang_luong_va_bang_bao_hiem_bang_may(db):
    """CỬA PHẢI CHẬN, VÀ CÂU CHẬN PHẢI NÓI ĐÚNG CÁI LUẬT ĐÃ KHAI Ở MỘT CHỖ.

    ĐỢT DỌN-3 14/10/2026 — phép thử này từng ghim thẳng chuỗi "Nghị định 13/2023" vào đây, và
    nó Đỏ trên main: mã đã chuyển sang Luật Bảo vệ dữ liệu cá nhân 2025 + NĐ 356/2025 (NĐ 356/2025
    thay NĐ 13/2023 từ 01/01/2026), mà phép thử thì không ai sửa theo. Cửa vẫn chặn đúng suốt thời
    gian đó — chỉ có lời dẫn luật trong phép thử là cũ.

    Sửa bằng cách thay một con số là chép lại đúng cái lỗi ấy: số hiệu luật nằm ở HAI chỗ, và lần
    đổi luật sau nó lại lệch. Nên phép thử đọc THẮNG từ `CAM_DOC_BANG_MAY` — đúng cái bảng mà dịch
    vụ dùng để dựng câu báo lỗi. Luật khai MỘT CHỖ; phép thử hỏi "câu chặn có nói đúng cái đã khai
    ở chỗ ấy không", chứ không hỏi "có trùng chuỗi tôi gõ tay ở đây không".
    """
    from app.models.doc_chung_tu import CAM_DOC_BANG_MAY
    from app.services import doc_chung_tu as D
    for loai in ("bang_luong", "bang_bao_hiem"):
        with pytest.raises(D.KhongDocDuoc) as ex:
            D.doc(db, loai, "bl.png", anh(1), "image/png", "hcns", "hcns")
        ly_do = CAM_DOC_BANG_MAY[loai]
        assert ly_do, f"`CAM_DOC_BANG_MAY[{loai!r}]` rỗng — một điều cấm không nói lý do là một điều cấm sẽ bị gỡ"
        assert ly_do in str(ex.value), (
            f"Câu chặn không mang theo lý do đã khai ở `CAM_DOC_BANG_MAY[{loai!r}]`. "
            "Người dùng bị chặn mà không được biết vì sao thì lần sau họ đi tìm đường vòng.")


def test_dieu_cam_nam_trong_ma_chu_khong_phai_trong_cau_hinh():
    """Bỏ được bằng cách gạt một công tắc lúc 11 giờ đêm thì không phải là một điều cấm."""
    from app.models.doc_chung_tu import CAM_DOC_BANG_MAY, LOAI_CHUNG_TU
    assert set(CAM_DOC_BANG_MAY) == {"bang_luong", "bang_bao_hiem"}
    assert not (set(CAM_DOC_BANG_MAY) & set(LOAI_CHUNG_TU))


def test_bon_loai_mo_truoc_deu_tro_ve_mot_bo_nap_da_co():
    """Cửa 3 không có bảng đích riêng – đó là cả điểm của khuôn ba cửa."""
    from app.models.doc_chung_tu import LOAI_CHUNG_TU
    from app.services.intake import BO_NAP
    assert len(LOAI_CHUNG_TU) == 4
    for k, v in LOAI_CHUNG_TU.items():
        assert v["bo_nap"] in BO_NAP, f"{k} trỏ về bộ nạp không tồn tại"
        cot = {c["key"] for c in BO_NAP[v["bo_nap"]]["cot"]}
        la = [t for t in v["truong"] if t not in cot]
        assert not la, f"{k}: trường {la} không có trong bộ nạp {v['bo_nap']}"


def test_chi_co_dung_mot_cho_ghi_vao_bang_dich():
    """Phép thử cấu trúc. Thêm một nhánh ghi thẳng thì phép thử này đỏ trước khi ai kịp dùng nó."""
    import inspect
    from app.services import doc_chung_tu as D
    src = inspect.getsource(D)
    assert src.count("nhap_mot_dong(") == 1, "chỉ được có ĐÚNG MỘT chỗ gọi hàm ghi"
    assert "nhap_mot_dong(" in inspect.getsource(D.xac_nhan)
    for ten in ("doc", "bo", "ty_le_sua", "hang_cho", "bat_thuong"):
        assert "nhap_mot_dong" not in inspect.getsource(getattr(D, ten)), \
            f"{ten}() không được ghi vào bảng đích"


# ====================== ĐỌC RA NHÁP ======================
def test_doc_xong_so_nam_o_ban_nhap_khong_nam_o_bang_dich(db, may):
    from app.services import doc_chung_tu as D
    from app.models.nap_bo_sung import PurchaseInvoice
    may(_hd_tho(so_hoa_don="00000601"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(2), "image/png", "ketoan", "ketoan")
    assert b.trang_thai == "nhap" and b.so_may_doc["so_hoa_don"] == "00000601"
    # Bảng đích chưa có gì – và đây là điều quan trọng nhất của cả phân hệ.
    assert db.execute(select(PurchaseInvoice).where(
        PurchaseInvoice.so_hoa_don == "00000601")).scalars().first() is None


def test_o_tien_bang_khong_doc_thanh_rong_chu_khong_thanh_so_khong(db, may):
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000602", tien_thue="0", tong_tien="0"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(3), "image/png", "ketoan", "ketoan")
    assert b.so_may_doc["tien_thue"] == "" and b.so_may_doc["tong_tien"] == ""
    assert "tien_thue" in b.truong_khong_doc_duoc and "tong_tien" in b.truong_khong_doc_duoc


def test_khoa_la_mo_hinh_tu_them_thi_bo_di(db, may):
    from app.services import doc_chung_tu as D
    may({**_hd_tho(so_hoa_don="00000603"), "so_tai_khoan_nguoi_ban": "999", "_ghi_chu": "ảnh hơi mờ"})
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(4), "image/png", "ketoan", "ketoan")
    assert "so_tai_khoan_nguoi_ban" not in b.so_may_doc
    assert b.ghi_chu_may == "ảnh hơi mờ"


def test_o_may_tu_nhan_la_khong_chac_van_bi_danh_dau(db, may):
    from app.services import doc_chung_tu as D
    may({**_hd_tho(so_hoa_don="00000604"), "_khong_chac": ["mst_nguoi_ban"]})
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(5), "image/png", "ketoan", "ketoan")
    assert "mst_nguoi_ban" in b.truong_khong_doc_duoc


def test_tai_lai_cung_mot_anh_khong_sinh_ban_thu_hai(db, may):
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000605"))
    a = anh(6)
    b1 = D.doc(db, "hoa_don_gtgt", "hd.png", a, "image/png", "ketoan", "ketoan")
    b2 = D.doc(db, "hoa_don_gtgt", "hd-lan-2.png", a, "image/png", "ketoan", "ketoan")
    assert b1.id == b2.id, "tải lại vì tưởng lần trước hỏng là chuyện thường ngày"


def test_moi_lan_doc_deu_co_vet_ke_ca_khi_khong_co_mo_hinh(db):
    from app.services import doc_chung_tu as D
    from app.models.core import AiRun
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(7), "image/png", "ketoan", "ketoan")
    r = db.get(AiRun, b.ai_run_id)
    assert r is not None and r.tac_vu == "doc_chung_tu" and r.dau_vao_hash
    assert r.muc <= D.MUC_TOI_DA
    # Không có khóa API: biểu RỖNG, không phải số bịa.
    assert all(v == "" for v in b.so_may_doc.values())
    assert "ANTHROPIC_API_KEY" in b.ghi_chu_may


def test_vai_tro_chua_khai_trong_bang_quyen_ai_thi_khong_doc_duoc(db):
    """Mặc định phải là ĐÓNG. Một vai trò mới thêm mà chưa ai quyết mức AI của nó thì không được
    dùng máy đọc chứng từ – hỏng thì đóng, không mở."""
    from app.services import doc_chung_tu as D
    from app.services.ai_quyen import muc_cua
    assert muc_cua(db, "vai_tro_moi_chua_ai_quyet", "doc_chung_tu") == 0
    with pytest.raises(D.KhongDocDuoc) as ex:
        D.doc(db, "hoa_don_gtgt", "hd.png", anh(8), "image/png", "ai_do", "vai_tro_moi_chua_ai_quyet")
    assert "Bảng quyền AI" in str(ex.value)


def test_chi_nhan_anh_va_pdf(db):
    from app.services import doc_chung_tu as D
    with pytest.raises(D.KhongDocDuoc):
        D.doc(db, "hoa_don_gtgt", "hd.docx", anh(9), "application/msword", "ketoan", "ketoan")


# ====================== XÁC NHẬN ======================
def test_xac_nhan_di_dung_cua_mot_va_ghi_duoc_vao_bang_dich(db, may):
    from app.services import doc_chung_tu as D
    from app.models.nap_bo_sung import PurchaseInvoice
    from app.models.intake import IntakeRun
    may(_hd_tho(so_hoa_don="00000701"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(10), "image/png", "ketoan", "ketoan")
    kq = D.xac_nhan(db, b, dict(b.so_may_doc), "ketoan", "ketoan")
    assert kq["da_ghi"] and b.trang_thai == "da_xac_nhan" and b.dang_cho is None
    h = db.execute(select(PurchaseInvoice).where(
        PurchaseInvoice.so_hoa_don == "00000701")).scalars().first()
    assert h is not None and h.tong_tien == 10_800_000
    # Nhật ký nạp phải ghi rõ ĐI BẰNG CỬA NÀO và ẢNH NÀO đã đọc ra số này.
    run = db.get(IntakeRun, kq["run_id"])
    assert run.nguon == "doc_anh" and run.tac_nhan == f"ai_run:{b.ai_run_id}"


def test_dem_dung_so_o_nguoi_phai_sua(db, may):
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000702", ten_nguoi_ban="Khach san ABC", tien_thue="900000"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(11), "image/png", "ketoan", "ketoan")
    row = dict(b.so_may_doc)
    row["ten_nguoi_ban"] = "Khách sạn ABC"          # người sửa dấu
    row["tien_thue"] = "800000"                      # người sửa số
    kq = D.xac_nhan(db, b, row, "ketoan", "ketoan")
    assert kq["da_ghi"]
    assert set(b.truong_da_sua) == {"ten_nguoi_ban", "tien_thue"}
    # Số máy đọc GIỮ NGUYÊN, không bị người sửa đè lên – đây là mẫu đối chứng để đo chất lượng.
    assert b.so_may_doc["tien_thue"] == "900000" and b.so_da_sua["tien_thue"] == "800000"


def test_nguoi_van_hanh_mo_hinh_khong_duoc_xac_nhan_ket_qua_cua_no(db, may):
    """P5. Người chạy mô hình mà cũng là người xác nhận kết quả của nó thì không còn ai đứng ngoài
    để nói mô hình đọc sai."""
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000703"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(12), "image/png", "cntt", "cntt")
    with pytest.raises(D.KhongDocDuoc) as ex:
        D.xac_nhan(db, b, dict(b.so_may_doc), "cntt", "cntt")
    assert "không được xác nhận" in str(ex.value)
    assert b.trang_thai == "nhap"


def test_phong_khac_khong_xac_nhan_thay_so_cua_phong_so_huu(db, may):
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000704"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(13), "image/png", "ketoan", "ketoan")
    with pytest.raises(D.KhongDocDuoc):
        D.xac_nhan(db, b, dict(b.so_may_doc), "gd.doixe", "gd_doi_xe")


def test_ghi_khong_duoc_thi_ban_nhap_o_nguyen_hang_cho(db, may):
    """Đánh dấu đã xử lý một dòng chưa vào được hệ thống là cách chắc chắn nhất để nó biến mất."""
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000705"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(14), "image/png", "ketoan", "ketoan")
    row = dict(b.so_may_doc); row["tong_tien"] = "99000000"        # lệch tổng – bộ kiểm cửa 1 chặn
    kq = D.xac_nhan(db, b, row, "ketoan", "ketoan")
    assert not kq["da_ghi"]
    assert b.trang_thai == "nhap" and b.dang_cho == b.checksum_anh


def test_xac_nhan_hai_lan_thi_lan_hai_bi_tu_choi(db, may):
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000706"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(15), "image/png", "ketoan", "ketoan")
    D.xac_nhan(db, b, dict(b.so_may_doc), "ketoan", "ketoan")
    with pytest.raises(D.KhongDocDuoc):
        D.xac_nhan(db, b, dict(b.so_may_doc), "ketoan", "ketoan")


def test_bo_phai_ghi_ly_do(db, may):
    from app.services import doc_chung_tu as D
    may(_hd_tho(so_hoa_don="00000707"))
    b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(16), "image/png", "ketoan", "ketoan")
    with pytest.raises(D.KhongDocDuoc):
        D.bo(db, b, "  ", "ketoan")
    D.bo(db, b, "Máy đọc sai số hóa đơn, ảnh quá mờ", "ketoan")
    assert b.trang_thai == "bo" and b.dang_cho is None


# ====================== ĐO CHẤT LƯỢNG ======================
def test_chua_du_muoi_ban_thi_noi_chua_du_du_lieu(db):
    from app.services import doc_chung_tu as D
    kq = D.ty_le_sua(db, "sao_ke_anh")
    assert kq["du_du_lieu"] is False and kq["de_xuat_ha_muc"] is False
    assert "chưa đủ" in kq["ghi_chu"]


def test_ty_le_sua_dem_theo_O_va_de_xuat_ha_muc_khi_vuot_nguong(db, may):
    """Đếm theo ô chứ không theo bản: một bản sai một ô và một bản sai chín ô là hai mức chất lượng
    khác hẳn nhau, mà đếm theo bản thì cả hai đều là 'một bản bị sửa'."""
    from app.services import doc_chung_tu as D
    for i in range(12):
        may(_hd_tho(so_hoa_don=f"0000080{i:02d}", ky_hieu="1C26TZZ"))
        b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(100 + i), "image/png", "ketoan", "ketoan")
        row = dict(b.so_may_doc)
        row["noi_dung"] = "người sửa lại diễn giải"          # 1 ô
        row["ten_nguoi_ban"] = "Tên đúng theo hóa đơn"       # 2 ô
        row["ma_tour"] = ""                                   # không tính: không thuộc trường đã khai
        assert D.xac_nhan(db, b, row, "ketoan", "ketoan")["da_ghi"]
    kq = D.ty_le_sua(db, "hoa_don_gtgt")
    assert kq["du_du_lieu"] and kq["so_ban"] >= 12
    assert kq["so_o"] == kq["so_ban"] * 10 and kq["so_o_sua"] == kq["so_ban"] * 2
    assert abs(kq["ty_le"] - 0.2) < 1e-9
    assert kq["de_xuat_ha_muc"] is False          # đúng 20% chưa vượt 20%


def test_ban_khong_co_mo_hinh_khong_tinh_vao_ty_le(db):
    """Lần chạy không có khóa API trả biểu rỗng, người gõ toàn bộ – tính vào thì tỷ lệ luôn 100% và
    con số mất hết ý nghĩa."""
    from app.services import doc_chung_tu as D
    b = D.doc(db, "sao_ke_anh", "sk.png", anh(200), "image/png", "ketoan", "ketoan")
    assert b.mo_hinh == ""
    D.xac_nhan(db, b, {"ma_gd": "SK-V2-1", "ngan_hang": "TPBank", "thoi_diem": "20/08/2026",
                       "loai": "vao", "so_tien": "5000000", "noi_dung": "gõ tay"},
               "ketoan", "ketoan")
    assert D.ty_le_sua(db, "sao_ke_anh")["so_ban"] == 0


def test_bat_thuong_so_voi_trung_vi_chu_khong_phai_trung_binh(db, may):
    """Một hóa đơn 900 triệu lọt vào giữa các hóa đơn vài triệu sẽ kéo trung bình lên đủ để chính nó
    trông bình thường, và cả những cái sau nó cũng vậy."""
    from app.services import doc_chung_tu as D
    assert D.bat_thuong(db, "hoa_don_gtgt", 999_000_000) == "", "chưa đủ nền thì không nói gì"
    for i in range(6):
        may(_hd_tho(so_hoa_don=f"0000090{i:02d}", ky_hieu="1C26TBT",
                    tien_truoc_thue="10000000", tien_thue="800000", tong_tien="10800000"))
        b = D.doc(db, "hoa_don_gtgt", "hd.png", anh(300 + i), "image/png", "ketoan", "ketoan")
        assert D.xac_nhan(db, b, dict(b.so_may_doc), "ketoan", "ketoan")["da_ghi"]
    canh = D.bat_thuong(db, "hoa_don_gtgt", 900_000_000)
    assert "gấp" in canh and "ảnh gốc" in canh
    assert D.bat_thuong(db, "hoa_don_gtgt", 11_000_000) == ""


# ====================== MÀN HÌNH & QUYỀN ======================
def test_menu_va_pham_vi_api_khop_nhau():
    """Cánh cửa vẽ trên tường: menu hiện ra mà bấm vào là 403."""
    from app.services.access import MENU_ROLES, pham_vi_api
    for vt in MENU_ROLES["/doc-chung-tu"]:
        assert "/api/v1/doc-chung-tu" in pham_vi_api(vt), f"{vt} thấy màn hình mà không chạm được API"


def test_hcns_khong_co_man_hinh_nay():
    """Bốn loại đang mở không có loại nào của HCNS, và hai loại của họ thì cấm đọc bằng máy."""
    from app.services.access import MENU_ROLES
    assert "hcns" not in MENU_ROLES["/doc-chung-tu"]
