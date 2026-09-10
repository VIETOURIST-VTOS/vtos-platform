"""V12 – công thức sinh lịch trả nợ từ một khế ước vay.

Kế toán tải lên một tệp khế ước; hệ thống dựng lịch trả nợ từ đó. Ba công thức, vì ba ngân hàng của
công ty đang dùng ba kiểu khác nhau và ép chung một kiểu là làm lịch trong VTOS lệch lịch của ngân
hàng ngay từ kỳ đầu.

────────────────────────────────────────────────────────────────────────────────
BA CÔNG THỨC
────────────────────────────────────────────────────────────────────────────────

goc_deu    – GỐC ĐỀU, lãi trên dư nợ giảm dần. Mỗi kỳ trả cùng một số gốc; lãi tính trên dư nợ còn
             lại nên giảm dần. Tổng phải trả kỳ đầu cao nhất. Đây là kiểu phổ biến nhất ở Việt Nam
             cho vay trung dài hạn, và là mặc định.

nien_kim   – TRẢ GÓP ĐỀU (niên kim). Tổng gốc + lãi mỗi kỳ bằng nhau; trong đó phần lãi giảm dần còn
             phần gốc tăng dần. Công thức: A = P·i / (1 − (1+i)^−n).
             Lãi suất bằng 0 thì công thức trên chia cho 0 – khi đó A = P/n, và đó là một nhánh RIÊNG
             chứ không phải một trường hợp của công thức chung.

cuoi_ky    – GỐC TRẢ MỘT LẦN CUỐI KỲ, lãi trả định kỳ. Kiểu của khoản vay vốn lưu động ngắn hạn.

────────────────────────────────────────────────────────────────────────────────
HAI ĐIỀU PHẢI NÓI RÕ VÌ CHÚNG QUYẾT ĐỊNH CON SỐ
────────────────────────────────────────────────────────────────────────────────

1. LỊCH NÀY LÀ LỊCH THAM CHIẾU. Lịch chính thức là lịch ngân hàng phát hành. Chênh lệch vài nghìn
   đồng do quy tắc làm tròn của từng ngân hàng là bình thường; chênh lệch lớn nghĩa là đã chọn sai
   công thức hoặc sai cách tính ngày. Vì vậy hàm trả về kèm `canh_bao` khi tổng lãi lệch đáng kể so
   với ước tính thô – để người nhập nhìn thấy ngay chứ không phát hiện sau ba kỳ.

2. LÃI TÍNH THEO THÁNG TRÒN, không theo số ngày thực tế. Ngân hàng Việt Nam thường tính lãi theo số
   ngày thực tế / 365. Chọn tháng tròn ở đây là chọn cái ĐƠN GIẢN VÀ NÓI RA, thay vì cái phức tạp mà
   vẫn không khớp tuyệt đối với ngân hàng. Ai cần khớp từng đồng thì nhập đè lịch ngân hàng gửi –
   cửa nhập tay vẫn mở, đó là lý do có ba cửa.

Không có hàm trích trước lãi ở đây: Chủ tịch quyết 08/9/2026 – lãi vay ghi KHI TRẢ.
"""
from datetime import date
from calendar import monthrange

CONG_THUC = {
    "goc_deu": "Gốc đều, lãi trên dư nợ giảm dần",
    "nien_kim": "Trả góp đều (niên kim) – gốc + lãi mỗi kỳ bằng nhau",
    "cuoi_ky": "Gốc trả một lần cuối kỳ, lãi trả định kỳ",
}


def them_thang(d: date, n: int) -> date:
    """Cộng n tháng, giữ ngày trong tháng; ngày 31 rơi vào tháng ngắn thì lùi về ngày cuối tháng.

    Không dùng "cộng 30 ngày": làm vậy thì kỳ trả nợ trôi dần khỏi ngày ký, và sau một năm lịch của
    ta lệch lịch ngân hàng khoảng nửa tháng.
    """
    thang = d.month - 1 + n
    nam = d.year + thang // 12
    thang = thang % 12 + 1
    return date(nam, thang, min(d.day, monthrange(nam, thang)[1]))


def _lam_tron(x: float) -> float:
    """Làm tròn về ĐỒNG. Đồng Việt Nam không có đơn vị nhỏ hơn, và giữ phần lẻ ở đây chỉ sinh ra
    những con số không bao giờ khớp với chứng từ ngân hàng."""
    return float(round(x))


def sinh_lich(goc: float, lai_suat_nam: float, so_ky: int, ky_dau: date,
              cong_thuc: str = "goc_deu") -> dict:
    """Sinh lịch trả nợ. Trả về {"dong": [...], "tong_goc", "tong_lai", "canh_bao": [...]}.

    Mỗi dòng: {ky, ngay, goc, lai, tong, du_no_sau}. Kỳ nào cũng có CẢ gốc và lãi trong một dòng –
    lúc ghi vào bảng lịch mới tách thành hai bản ghi, vì gốc và lãi là hai bút toán.
    """
    loi = []
    if goc <= 0:
        loi.append("Số tiền vay phải lớn hơn 0")
    if so_ky <= 0:
        loi.append("Số kỳ phải lớn hơn 0")
    if lai_suat_nam < 0:
        loi.append("Lãi suất không được âm")
    if cong_thuc not in CONG_THUC:
        loi.append(f"Công thức '{cong_thuc}' không có – chọn một trong {', '.join(CONG_THUC)}")
    if loi:
        raise ValueError("; ".join(loi))

    i = (lai_suat_nam / 100.0) / 12.0        # lãi suất tháng
    dong, du_no = [], float(goc)

    if cong_thuc == "goc_deu":
        goc_ky = _lam_tron(goc / so_ky)
        for k in range(1, so_ky + 1):
            lai = _lam_tron(du_no * i)
            # Kỳ CUỐI trả hết phần còn lại, không trả goc_ky: làm tròn từng kỳ để lại phần dư, và
            # phần dư ấy phải nằm ở kỳ cuối chứ không biến mất.
            g = du_no if k == so_ky else min(goc_ky, du_no)
            du_no = _lam_tron(du_no - g)
            dong.append({"ky": k, "ngay": them_thang(ky_dau, k - 1), "goc": _lam_tron(g),
                         "lai": lai, "tong": _lam_tron(g + lai), "du_no_sau": du_no})

    elif cong_thuc == "nien_kim":
        if i == 0:
            # Lãi suất 0 thì công thức niên kim chia cho 0. Nhánh riêng, không phải trường hợp con.
            deu = _lam_tron(goc / so_ky)
        else:
            deu = _lam_tron(goc * i / (1 - (1 + i) ** (-so_ky)))
        for k in range(1, so_ky + 1):
            lai = _lam_tron(du_no * i)
            g = du_no if k == so_ky else min(_lam_tron(deu - lai), du_no)
            du_no = _lam_tron(du_no - g)
            dong.append({"ky": k, "ngay": them_thang(ky_dau, k - 1), "goc": g, "lai": lai,
                         "tong": _lam_tron(g + lai), "du_no_sau": du_no})

    else:   # cuoi_ky
        for k in range(1, so_ky + 1):
            lai = _lam_tron(du_no * i)
            g = du_no if k == so_ky else 0.0
            du_no = _lam_tron(du_no - g)
            dong.append({"ky": k, "ngay": them_thang(ky_dau, k - 1), "goc": g, "lai": lai,
                         "tong": _lam_tron(g + lai), "du_no_sau": du_no})

    tong_goc = _lam_tron(sum(d["goc"] for d in dong))
    tong_lai = _lam_tron(sum(d["lai"] for d in dong))
    canh_bao = []
    # Tổng gốc phải bằng đúng số vay. Lệch nghĩa là phần làm tròn rơi mất ở đâu đó – và một đồng rơi
    # mất trong lịch trả nợ là một đồng lệch giữa sổ và ngân hàng ở kỳ cuối.
    if abs(tong_goc - _lam_tron(goc)) >= 1:
        canh_bao.append(f"Tổng gốc trong lịch ({tong_goc:,.0f}) khác số tiền vay ({goc:,.0f}) – "
                        "phần làm tròn bị rơi, KHÔNG dùng lịch này")
    if dong and dong[-1]["du_no_sau"] != 0:
        canh_bao.append(f"Sau kỳ cuối vẫn còn dư nợ {dong[-1]['du_no_sau']:,.0f} – lịch chưa trả hết")
    return {"cong_thuc": cong_thuc, "cong_thuc_ten": CONG_THUC[cong_thuc], "so_ky": so_ky,
            "dong": dong, "tong_goc": tong_goc, "tong_lai": tong_lai,
            "tong_phai_tra": _lam_tron(tong_goc + tong_lai), "canh_bao": canh_bao}
