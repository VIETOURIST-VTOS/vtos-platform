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
"""
import os, sys, pathlib, re

os.environ["DATABASE_URL"] = "sqlite:///./test_cnt.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_cnt.db"): os.remove("test_cnt.db")

GOC = pathlib.Path(__file__).resolve().parents[2]
WEB = GOC / "web" / "app"
DUONG_DAN = "nap-du-lieu/nhap-mot-dong"

trang = [p for p in WEB.rglob("page.tsx")]
goi = [p for p in trang if DUONG_DAN in p.read_text(encoding="utf-8")]

# C1
assert goi, ("C1 ĐỎ – không trang nào gọi " + DUONG_DAN + ". Cửa nhập tay của toàn hệ thống đang đóng: "
             "nhân viên chỉ nạp được bằng tệp, sai một dòng phải sửa tệp rồi nạp lại cả lô.")
print(f"C1 XANH – {len(goi)} trang gọi cửa nhập tay: " + ", ".join(str(p.relative_to(WEB)) for p in goi))

# C2 – gọi trong một hàm gửi đi kèm nút bấm, không phải chỉ nằm trong chú thích
co_nut = False
for p in goi:
    s = p.read_text(encoding="utf-8")
    i = s.find(DUONG_DAN)
    quanh = s[max(0, i - 600): i + 600]
    if "method: \"POST\"" in quanh and "<button" in s:
        co_nut = True
assert co_nut, ("C2 ĐỎ – có nhắc tới đường dẫn nhưng không thấy lời gọi POST kèm nút bấm. "
                "Một đường dẫn trong chú thích không phải là một cái cửa.")
print("C2 XANH – có lời gọi POST và có nút bấm trên màn hình")

# C3 – màn hình dựng biểu từ khai báo cột của máy chủ, nên mọi bộ nạp đều đi qua đây
from app.services import intake as IN
assert len(IN.BO_NAP) >= 27, f"C3 ĐỎ – chỉ thấy {len(IN.BO_NAP)} bộ nạp"
thieu_cot = [k for k, v in IN.BO_NAP.items() if not v.get("cot")]
assert not thieu_cot, ("C3 ĐỎ – bộ nạp không khai cột thì màn hình không dựng được biểu nhập tay: "
                       + ", ".join(thieu_cot))
print(f"C3 XANH – {len(IN.BO_NAP)} bộ nạp đều khai đủ cột, dùng chung một biểu")
# C4 – V6 có màn hình xem báo giá từ đầu, nhưng khâu SOẠN thì chưa; chuỗi bán hàng đứt ngay ở khâu
# đầu tiên. Cùng một loại lỗ hổng với C1: đường đi có, cửa vào thì không.
soan = [p for p in trang if 'method: "POST"' in p.read_text(encoding="utf-8")
        and "/ban-hang/bao-gia" in p.read_text(encoding="utf-8")]
assert soan, ("C4 ĐỎ – không màn hình nào gửi POST /ban-hang/bao-gia. Xem được báo giá nhưng không "
              "soạn được báo giá mới thì chuỗi bán hàng đứt ở khâu đầu.")
print("C4 XANH – " + ", ".join(str(p.relative_to(WEB)) for p in soan) + " soạn được báo giá mới")

# C5 – quy ước hạch toán quyết định bút toán vay chạy vào tài khoản nào. Trước 09/9 chỉ đọc được trên
# màn hình; đổi một dòng phải nhờ kỹ thuật, và việc nhờ kỹ thuật không đi qua đường hai chữ ký.
c5 = [p for p in trang if "/hach-toan/quy-tac" in p.read_text(encoding="utf-8")
      or ('"quy-tac"' in p.read_text(encoding="utf-8") and "hach-toan" in p.read_text(encoding="utf-8"))]
assert c5, "C5 ĐỎ – không màn hình nào trình được quy ước hạch toán mới."
print("C5 XANH – " + ", ".join(str(p.relative_to(WEB)) for p in c5) + " trình được quy ước mới")

# C6 – khế ước vay: bộ nạp Excel chỉ mang được con số, bản gốc là giấy có chữ ký và dấu.
from app.models.attachments import DOI_TUONG_DAY_DU
assert "khe_uoc_vay" in DOI_TUONG_DAY_DU, "C6 ĐỎ – chưa khai đối tượng đính kèm cho khế ước vay"
c6 = [p for p in trang if '"khe_uoc_vay"' in p.read_text(encoding="utf-8")]
assert c6, "C6 ĐỎ – khai đối tượng rồi nhưng không màn hình nào gắn được tệp vào khế ước."
print("C6 XANH – " + ", ".join(str(p.relative_to(WEB)) for p in c6) + " gắn được bản gốc khế ước")

print("TEST CUA NHAP TAY: XANH")
