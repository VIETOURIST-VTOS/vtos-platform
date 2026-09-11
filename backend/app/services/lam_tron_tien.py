# -*- coding: utf-8 -*-
"""Làm tròn tiền – MỘT hàm duy nhất cho cả màn hình và tệp Excel (chỉ đạo Chủ tịch 11/9/2026).

Chủ tịch chốt hai điều, và cả hai đều là điều dễ vi phạm mà không ai thấy:

  (1) LÀM TRÒN Ở BƯỚC HIỂN THỊ, không đổi kiểu dữ liệu gốc. Cột so_luong và đơn giá giữ nguyên số
      thực; cái được làm tròn là con số ĐƯA RA MẮT NGƯỜI, không phải con số đem đi tính tiếp.

  (2) DÒNG TỔNG PHẢI BẰNG TỔNG CỦA CÁC DÒNG ĐÃ LÀM TRÒN – không phải phần làm tròn của một tổng
      chưa làm tròn. Hai cách ấy lệch nhau vài đồng, và vài đồng trên một bảng quyết toán là chỗ
      kế toán ngồi dò cả buổi chiều mà không tìm ra, vì không có dòng nào sai cả.

  (3) MÀN HÌNH VÀ EXCEL DÙNG CHUNG MỘT HÀM. Không phải "hai hàm cho ra kết quả giống nhau" – dùng
      chung ĐÚNG MỘT hàm. Hai hàm giống nhau hôm nay là hai hàm khác nhau sau lần sửa đầu tiên, và
      lần ấy sẽ không ai sửa cả hai.

Vì sao phải có tệp riêng chứ không viết round() tại chỗ: round() của Python làm tròn về số CHẴN
(banker's rounding) – round(0.5) ra 0, round(1.5) ra 2. Trên tiền thì đó là một quy tắc không ai
đọc hóa đơn mà đoán ra được. Ở đây dùng ROUND_HALF_UP: 0,5 đồng luôn lên 1 đồng, kể cả số âm thì
lên về phía xa số 0 – đối xứng, nên một khoản thu và một khoản chi cùng độ lớn triệt tiêu nhau
đúng bằng 0 chứ không còn dư một đồng.

Cách dùng, đúng một kiểu:

    from app.services.lam_tron_tien import o_tien, cong

    dong = [o_tien(x) for x in cac_so]
    tong = cong(cac_so)          # tong["so"] == sum(d["so_da_tron"] for d in dong)  – luôn đúng
"""
from decimal import Decimal, ROUND_HALF_UP

# Đơn vị nhỏ nhất mà bảng tiền Việt còn hiển thị. Chốt 11/9/2026: làm tròn tới ĐỒNG.
DON_VI = Decimal(1)

# Tên hàm mà mọi nơi phải gọi. Phép thử canh chuỗi này để một lần sửa "cho nhanh" ở một phía
# (màn hình hoặc Excel) không lặng lẽ tách đôi quy tắc làm tròn.
HAM_DUY_NHAT = "app.services.lam_tron_tien.lam_tron"


def lam_tron(x) -> int:
    """Làm tròn một số tiền tới đồng, nửa đồng lên trên, số âm lên về phía xa 0.

    Nhận None và trả về None – KHÔNG trả 0. Rỗng nghĩa là chưa có số, và một ô chưa ai điền hiện
    ra "0" là nói với người đọc rằng đã đếm xong và kết quả bằng không.
    """
    if x is None:
        return None
    return int(Decimal(str(x)).quantize(DON_VI, rounding=ROUND_HALF_UP))


def hien(x) -> str:
    """Chuỗi đã làm tròn, chấm phân cách nghìn theo lối Việt Nam. None ra chuỗi rỗng, không ra '0'."""
    n = lam_tron(x)
    if n is None:
        return ""
    return f"{n:,}".replace(",", ".")


def o_tien(x) -> dict:
    """Một ô tiền như mọi API của làn Phân quyền trả xuống.

      so          : số nguyên vẹn, chưa làm tròn – dùng khi còn phải tính tiếp.
      so_da_tron  : số nguyên sau khi làm tròn – đây mới là số đem đi CỘNG cho dòng tổng.
      hien        : chuỗi vẽ thẳng lên màn hình hoặc đổ thẳng vào ô Excel.

    Trả cả ba chứ không chỉ "hien" vì bên nhận sẽ cần cộng, và nếu chỉ có chuỗi thì họ sẽ tự tách
    dấu chấm ra để cộng lại – và ở đó quy tắc làm tròn tách làm đôi lần nữa.
    """
    return {"so": x, "so_da_tron": lam_tron(x), "hien": hien(x)}


def cong(cac_so) -> dict:
    """Dòng tổng: CỘNG CÁC DÒNG ĐÃ LÀM TRÒN.

    Đây là chỗ ràng buộc (2) của Chủ tịch sống hay chết. Viết lam_tron(sum(cac_so)) thì nhanh hơn
    một chữ và sai theo cách không ai nhìn ra.

    Ô rỗng bị BỎ QUA khi cộng, không coi là 0 – nhưng số ô bị bỏ qua được đếm và trả về, để màn
    hình nói được "tổng của 12 trên 15 dòng" thay vì im lặng đưa ra một tổng thiếu.
    """
    da_tron = [lam_tron(x) for x in cac_so]
    co = [n for n in da_tron if n is not None]
    t = sum(co)
    return {"so": t, "so_da_tron": t, "hien": hien(t),
            "so_dong": len(da_tron), "so_dong_co_so": len(co),
            "so_dong_rong": len(da_tron) - len(co)}


def bang_tien(cac_so) -> dict:
    """Cả bảng một lượt: các dòng và dòng tổng, đảm bảo sẵn đẳng thức tổng = tổng các dòng đã tròn."""
    dong = [o_tien(x) for x in cac_so]
    t = cong(cac_so)
    return {"dong": dong, "tong": t}
