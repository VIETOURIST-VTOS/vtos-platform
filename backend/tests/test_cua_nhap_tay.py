"""Rà soát cửa nhập 09/9 – chốt chặn cho lỗ hổng đã tìm ra: API có mà màn hình không có.

Bối cảnh: `POST /api/v1/nap-du-lieu/nhap-mot-dong` đã viết từ trước cho cả 27 bộ nạp, nhưng đếm bằng
lệnh trên web/ ra 0 lần gọi – tức là máy làm được mà người dùng không bấm được ở đâu. Trong hơn ba
tuần không ai phát hiện, vì bộ kiểm chỉ hỏi "API chạy không", không hỏi "có ai gọi được nó không".

Bộ kiểm này hỏi câu thứ hai. Nó cố ý đọc THƯ MỤC GIAO DIỆN chứ không đọc bảng khai báo màn hình: bảng
khai báo là bản sao, và một cửa bị bỏ quên thường bị bỏ quên ở cả bản sao lẫn bản gốc.

  C1 có ít nhất một trang giao diện gọi cửa nhập tay một dòng
  C2 trang đó có nút bấm ghi, không phải chỉ nhắc tới đường dẫn trong chú thích
  C3 mọi bộ nạp đều dùng chung cửa này – không bộ nào có đường riêng
  C4 chuỗi bán hàng có cửa SOẠN báo giá, không phải chỉ có cửa xem
  C5 quy ước hạch toán trình được bản mới từ màn hình, không phải nhờ kỹ thuật
  C6 khế ước vay gắn được bản gốc

────────────────────────────────────────────────────────────────────────────────
VIẾT LẠI THÀNH HÀM 09/9/2026 – và đây là một bài học đắt hơn nội dung phép thử
────────────────────────────────────────────────────────────────────────────────

Bản đầu viết kiểu KỊCH BẢN: các câu assert nằm thẳng ở thân mô-đun. Chạy tay bằng
`python3 tests/test_cua_nhap_tay.py` thì nó in ra "XANH" đầy đủ và em tin là xong.

Nhưng CI chạy `pytest` từng tệp một. Pytest thu thập tệp này ra KHÔNG CÓ HÀM TEST NÀO, in
"no tests ran" và trả mã 5. Mà `tests/run_all.sh` có `set -e`, nên mã 5 giết cả lượt chạy –
CI đỏ ở đúng tệp mà em vừa viết để canh chỗ khác.

Chỗ đáng nhớ: suốt cả ngày em thấy dòng "no tests ran in 0.6s" nhiều lần và ĐỌC NÓ THÀNH XANH,
vì em vẫn chạy tay bên cạnh và thấy chữ XANH. Một phép thử không được thu thập thì không canh gì
cả – nó chỉ trông giống một phép thử. Cùng một họ với ba lỗi hôm nay: đếm đầu mạch trên nhánh của
mình, cây làm việc lùi sau commit, và bây giờ là chạy phép thử bằng một cách khác với cách CI chạy.
Cả ba đều là ĐO SAI CHỖ, không phải viết sai.
"""
import os, sys, pathlib

os.environ["DATABASE_URL"] = "sqlite:///./test_cnt.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

GOC = pathlib.Path(__file__).resolve().parents[2]
WEB = GOC / "web" / "app"
DUONG_DAN = "nap-du-lieu/nhap-mot-dong"


def _trang() -> list[pathlib.Path]:
    return list(WEB.rglob("page.tsx"))


def _goi(duong_dan: str) -> list[pathlib.Path]:
    return [p for p in _trang() if duong_dan in p.read_text(encoding="utf-8")]


def test_c1_co_trang_goi_cua_nhap_tay():
    goi = _goi(DUONG_DAN)
    assert goi, ("C1 ĐỎ – không trang nào gọi " + DUONG_DAN + ". Cửa nhập tay của toàn hệ thống đang "
                 "đóng: nhân viên chỉ nạp được bằng tệp, sai một dòng phải sửa tệp rồi nạp lại cả lô.")


def test_c2_co_loi_goi_POST_kem_nut_bam():
    """Xét MỌI lần xuất hiện của đường dẫn, không chỉ lần đầu.

    Sửa 09/9 sau khi gộp: bản màn hình trên main nhắc đường dẫn trong CHÚ THÍCH ở đầu tệp rồi mới
    gọi thật ở dưới, nên xét lần đầu tiên là xét đúng chỗ chú thích và kết luận "không có nút" –
    phép thử đỏ vì chính nó viết hẹp, không phải vì cửa hỏng. Một phép thử báo động giả cũng làm
    người ta thôi tin nó, y như một cửa hỏng.
    """
    co_nut = False
    for p in _goi(DUONG_DAN):
        noi_dung = p.read_text(encoding="utf-8")
        if "<button" not in noi_dung:
            continue
        vi_tri = [i for i in range(len(noi_dung)) if noi_dung.startswith(DUONG_DAN, i)]
        for i in vi_tri:
            if 'method: "POST"' in noi_dung[max(0, i - 600): i + 600]:
                co_nut = True
    assert co_nut, ("C2 ĐỎ – có nhắc tới đường dẫn nhưng không thấy lời gọi POST kèm nút bấm. "
                    "Một đường dẫn trong chú thích không phải là một cái cửa.")


def test_c3_moi_bo_nap_dung_chung_mot_bieu():
    from app.services import intake as IN
    assert len(IN.BO_NAP) >= 27, f"C3 ĐỎ – chỉ thấy {len(IN.BO_NAP)} bộ nạp"
    thieu_cot = [k for k, v in IN.BO_NAP.items() if not v.get("cot")]
    assert not thieu_cot, ("C3 ĐỎ – bộ nạp không khai cột thì màn hình không dựng được biểu nhập tay: "
                           + ", ".join(thieu_cot))


def test_c4_soan_duoc_bao_gia_moi():
    """V6 có màn hình XEM báo giá từ đầu, nhưng khâu SOẠN thì chưa – chuỗi bán hàng đứt ngay ở khâu
    đầu tiên. Cùng một loại lỗ hổng với C1: đường đi có, cửa vào thì không."""
    soan = [p for p in _trang()
            if 'method: "POST"' in p.read_text(encoding="utf-8")
            and "/ban-hang/bao-gia" in p.read_text(encoding="utf-8")]
    assert soan, ("C4 ĐỎ – không màn hình nào gửi POST /ban-hang/bao-gia. Xem được báo giá nhưng "
                  "không soạn được báo giá mới thì chuỗi bán hàng đứt ở khâu đầu.")


def test_c5_trinh_duoc_quy_uoc_hach_toan_moi():
    """Quy ước hạch toán quyết định bút toán vay chạy vào tài khoản nào. Trước 09/9 chỉ đọc được trên
    màn hình; đổi một dòng phải nhờ kỹ thuật, và việc nhờ kỹ thuật không đi qua đường hai chữ ký."""
    c5 = [p for p in _trang() if "/hach-toan/quy-tac" in p.read_text(encoding="utf-8")]
    assert c5, "C5 ĐỎ – không màn hình nào trình được quy ước hạch toán mới."


def test_c6_khe_uoc_vay_gan_duoc_ban_goc():
    """Bộ nạp Excel chỉ mang được con số; bản gốc là giấy có chữ ký và dấu."""
    from app.models.attachments import DOI_TUONG_DAY_DU
    assert "khe_uoc_vay" in DOI_TUONG_DAY_DU, "C6 ĐỎ – chưa khai đối tượng đính kèm cho khế ước vay"
    c6 = [p for p in _trang() if '"khe_uoc_vay"' in p.read_text(encoding="utf-8")]
    assert c6, "C6 ĐỎ – khai đối tượng rồi nhưng không màn hình nào gắn được tệp vào khế ước."
