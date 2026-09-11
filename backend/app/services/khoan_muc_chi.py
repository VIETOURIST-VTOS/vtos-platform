"""Danh mục KHOẢN MỤC CHI PHÍ TOUR – tên dịch vụ lập trình sẵn, nhân viên chỉ điền số tiền.

VÌ SAO DANH MỤC NÀY PHẢI NẰM TRONG MÃ

Trước bản này, cột "nội dung" của dòng chi là ô CHỮ TỰ DO. Đo trên tám tệp quyết toán thật thì cùng
một khoản được gọi bằng nhiều tên khác nhau:

    LAND · LAND MCB · Landtour ADL · Giá land · LAND TOUR
    PHÍ TL · CTP HDV · CTP · Chi phí chung HDV · CHI PHÍ TL
    PHÍ LSQ · PHÍ TLS CAO CẤP · PHÍ TLS CƠ BẢN · Phí visa · PHÍ LSQ + NHẬN VISA
    NÓN - BAO HỘ CHIẾU · NÓN BAO HC · NÓN+ BAO DA · Nón

Chữ tự do thì mỗi người gõ một kiểu, và hệ quả không phải là xấu bảng – là KHÔNG CỘNG ĐƯỢC. Câu hỏi
"cả năm công ty chi bao nhiêu tiền khách sạn" không có câu trả lời khi khách sạn nằm rải trong bốn
cách gõ. Với 1.258 chuyến thì đó là một khoảng mù rất lớn.

Nên danh mục ở đây là mã, không phải gợi ý. Người nhập CHỌN một khoản mục rồi điền số tiền; tên đối
tác thì chọn từ hồ sơ nhà cung cấp và hệ thống tự lấy mã số thuế, địa chỉ, số tài khoản.

VẪN CÓ ĐƯỜNG THOÁT, VÀ CÓ CHỦ Ý

Khoản mục "khac_<nhóm>" cho phép ghi một khoản chưa có trong danh mục, kèm mô tả tự do. Không có
đường thoát thì người ta sẽ nhét khoản lạ vào một mã gần đúng, và thế là hỏng im lặng – tệ hơn hẳn
một nhóm "khác" đếm được. Đếm được bao nhiêu tiền rơi vào "khác" chính là tín hiệu để biết danh mục
còn thiếu gì.

MỖI KHOẢN MỤC MANG SẴN BỐN MẶC ĐỊNH

    nhom            – nhóm khoản mục để cộng và để in ra đúng bố cục chiết tính của Điều hành
    doi_tuong       – người lớn / trẻ em / chung: ăn và lưu trú khác giá theo đối tượng
    quy_tac_phan_bo – chia đều mọi khách / chia đều khách có thu / theo đối tượng / không chia
    dich_danh       – True: khoản này mỗi khách một giá, KHÔNG chia (vé máy bay, visa, dịch thuật)

Mặc định là MẶC ĐỊNH, không phải khoá: người lập tờ đổi được từng dòng. Nhưng có mặc định đúng thì
phần lớn dòng không phải nghĩ, và phép kiểm "dòng chi chưa khai quy tắc phân bổ" gần như không còn
kêu – đó là cách làm cho một phép kiểm nghiêm mà vẫn dùng được.
"""

# Nhóm khoản mục. Mã nhóm đi vào cột tour_cost_lines.nhom; tên hiển thị theo bố cục Điều hành đang
# dùng ở sheet LAND của các tệp outbound (I/BUS, II/HOTEL, III/RESTAURANT, IV/ENTRANCE FEE…).
NHOM = {
    "VC": "A. VẬN CHUYỂN",
    "LT": "B. LƯU TRÚ",
    "AU": "C. ĂN UỐNG",
    "TQ": "D. THAM QUAN – VUI CHƠI",
    "HD": "E. HƯỚNG DẪN – ĐIỀU HÀNH",
    "VS": "F. VISA – GIẤY TỜ",
    "BH": "G. BẢO HIỂM",
    "QT": "H. QUÀ TẶNG – VẬT PHẨM",
    "PK": "I. PHÍ KHÁC",
}

# (mã, tên, nhóm, đối tượng, quy tắc phân bổ, đích danh, hình thức, loại NCC gợi ý)
#
# hinh_thuc: "ca_hai" | "trong_nuoc" | "nuoc_ngoai" – lọc danh sách theo đúng loại tour đang lập, để
# người làm tour nội địa không phải cuộn qua phí lãnh sự quán.
_D = [
    # ---------------------------------------------------------------- A. VẬN CHUYỂN
    ("vc_xe_du_lich", "Xe du lịch (thuê nguyên chuyến)", "VC", "chung", "deu_khach_co_thu", False, "ca_hai", "xe"),
    ("vc_xe_trung_chuyen", "Xe trung chuyển – đưa đón sân bay", "VC", "chung", "deu_khach_co_thu", False, "ca_hai", "xe"),
    ("vc_ve_may_bay", "Vé máy bay quốc tế", "VC", "chung", "khong_phan_bo", True, "nuoc_ngoai", "hang_khong"),
    ("vc_ve_may_bay_nd", "Vé máy bay nội địa", "VC", "chung", "khong_phan_bo", True, "ca_hai", "hang_khong"),
    ("vc_phu_thu_ve", "Phụ thu vé – dời chặng, đổi tên, charge", "VC", "chung", "khong_phan_bo", True, "ca_hai", "hang_khong"),
    ("vc_tau_hoa", "Vé tàu hoả", "VC", "chung", "theo_doi_tuong", False, "ca_hai", "van_tai"),
    ("vc_tau_thuy", "Tàu thuỷ / ca nô / phà", "VC", "chung", "theo_doi_tuong", False, "ca_hai", "van_tai"),
    ("vc_khac", "Vận chuyển khác (ghi rõ)", "VC", "chung", "deu_khach_co_thu", False, "ca_hai", "xe"),
    # ---------------------------------------------------------------- B. LƯU TRÚ
    ("lt_khach_san", "Khách sạn – phòng đôi/ba", "LT", "nguoi_lon", "theo_doi_tuong", False, "ca_hai", "khach_san"),
    ("lt_khach_san_te", "Khách sạn – trẻ em (giường phụ)", "LT", "tre_em", "theo_doi_tuong", False, "ca_hai", "khach_san"),
    ("lt_phu_thu_phong_don", "Phụ thu phòng đơn", "LT", "chung", "khong_phan_bo", True, "ca_hai", "khach_san"),
    ("lt_city_tax", "Thuế lưu trú địa phương (city tax)", "LT", "chung", "deu_khach_co_thu", False, "nuoc_ngoai", "khach_san"),
    ("lt_khac", "Lưu trú khác (ghi rõ)", "LT", "chung", "theo_doi_tuong", False, "ca_hai", "khach_san"),
    # ---------------------------------------------------------------- C. ĂN UỐNG
    ("au_an_sang", "Ăn sáng", "AU", "nguoi_lon", "theo_doi_tuong", False, "ca_hai", "nha_hang"),
    ("au_an_trua", "Ăn trưa", "AU", "nguoi_lon", "theo_doi_tuong", False, "ca_hai", "nha_hang"),
    ("au_an_toi", "Ăn tối", "AU", "nguoi_lon", "theo_doi_tuong", False, "ca_hai", "nha_hang"),
    ("au_an_sang_te", "Ăn sáng – trẻ em", "AU", "tre_em", "theo_doi_tuong", False, "ca_hai", "nha_hang"),
    ("au_an_trua_te", "Ăn trưa – trẻ em", "AU", "tre_em", "theo_doi_tuong", False, "ca_hai", "nha_hang"),
    ("au_an_toi_te", "Ăn tối – trẻ em", "AU", "tre_em", "theo_doi_tuong", False, "ca_hai", "nha_hang"),
    ("au_tiec_gala", "Tiệc gala – liên hoan", "AU", "chung", "deu_khach_co_thu", False, "ca_hai", "nha_hang"),
    ("au_nuoc_uong", "Nước uống trên xe", "AU", "chung", "deu_moi_khach", False, "ca_hai", "khac"),
    ("au_banh_trai_cay", "Bánh – trái cây – khăn lạnh", "AU", "chung", "deu_moi_khach", False, "ca_hai", "khac"),
    ("au_khac", "Ăn uống khác (ghi rõ)", "AU", "chung", "theo_doi_tuong", False, "ca_hai", "nha_hang"),
    # ---------------------------------------------------------------- D. THAM QUAN
    ("tq_ve_tham_quan", "Vé tham quan", "TQ", "nguoi_lon", "theo_doi_tuong", False, "ca_hai", "diem_den"),
    ("tq_ve_tham_quan_te", "Vé tham quan – trẻ em", "TQ", "tre_em", "theo_doi_tuong", False, "ca_hai", "diem_den"),
    ("tq_combo_ve", "Combo vé – nhiều điểm", "TQ", "nguoi_lon", "theo_doi_tuong", False, "ca_hai", "diem_den"),
    ("tq_ve_show", "Vé show – biểu diễn", "TQ", "chung", "theo_doi_tuong", False, "ca_hai", "diem_den"),
    ("tq_khac", "Tham quan khác (ghi rõ)", "TQ", "chung", "theo_doi_tuong", False, "ca_hai", "diem_den"),
    # ---------------------------------------------------------------- E. HƯỚNG DẪN – ĐIỀU HÀNH
    ("hd_ctp_hdv", "Công tác phí hướng dẫn viên", "HD", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("hd_ctp_tl", "Công tác phí trưởng đoàn", "HD", "chung", "deu_khach_co_thu", False, "nuoc_ngoai", "khac"),
    ("hd_luu_tru_hdv", "Lưu trú hướng dẫn viên", "HD", "chung", "deu_khach_co_thu", False, "ca_hai", "khach_san"),
    ("hd_ve_may_bay_hdv", "Vé máy bay hướng dẫn viên", "HD", "chung", "deu_khach_co_thu", False, "ca_hai", "hang_khong"),
    ("hd_an_noi_bo", "Ăn ở nội bộ – nhân viên đi cùng", "HD", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("hd_tip", "Tip hướng dẫn – tài xế – phục vụ", "HD", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("hd_phi_dieu_hanh", "Phí điều hành", "HD", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("hd_khac", "Hướng dẫn – điều hành khác (ghi rõ)", "HD", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    # ---------------------------------------------------------------- F. VISA – GIẤY TỜ
    ("vs_phi_lsq", "Phí lãnh sự quán", "VS", "chung", "khong_phan_bo", True, "nuoc_ngoai", "visa"),
    ("vs_phi_dich_vu_visa", "Phí dịch vụ visa", "VS", "chung", "khong_phan_bo", True, "nuoc_ngoai", "visa"),
    ("vs_dich_thuat", "Dịch thuật – công chứng hồ sơ", "VS", "chung", "khong_phan_bo", True, "nuoc_ngoai", "visa"),
    ("vs_nhan_visa", "Phí nhận visa – chuyển phát", "VS", "chung", "khong_phan_bo", True, "nuoc_ngoai", "visa"),
    ("vs_khac", "Visa – giấy tờ khác (ghi rõ)", "VS", "chung", "khong_phan_bo", True, "nuoc_ngoai", "visa"),
    # ---------------------------------------------------------------- G. BẢO HIỂM
    # Bảo hiểm chia đều MỌI khách, kể cả suất miễn phí: em bé không trả tiền tour vẫn được mua bảo
    # hiểm, và tệp Nha Trang cũng tính đúng như vậy – hai cháu miễn phí vẫn chịu 5.000 đ mỗi cháu.
    ("bh_du_lich", "Bảo hiểm du lịch – khách", "BH", "chung", "deu_moi_khach", False, "ca_hai", "bao_hiem"),
    ("bh_hdv", "Bảo hiểm hướng dẫn viên", "BH", "chung", "deu_khach_co_thu", False, "ca_hai", "bao_hiem"),
    # ---------------------------------------------------------------- H. QUÀ TẶNG – VẬT PHẨM
    ("qt_non", "Nón du lịch", "QT", "chung", "deu_moi_khach", False, "ca_hai", "khac"),
    ("qt_bao_ho_chieu", "Bao hộ chiếu – bao da", "QT", "chung", "deu_moi_khach", False, "nuoc_ngoai", "khac"),
    ("qt_qua_khach", "Quà tặng khách", "QT", "chung", "deu_moi_khach", False, "ca_hai", "khac"),
    ("qt_qua_truong_doan", "Quà trưởng đoàn – đại diện", "QT", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("qt_banner", "Banner – backdrop – chụp hình", "QT", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("qt_vat_pham_gala", "Vật phẩm gala – nến, bánh kem, cây vân tay", "QT", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("qt_khac", "Quà tặng – vật phẩm khác (ghi rõ)", "QT", "chung", "deu_moi_khach", False, "ca_hai", "khac"),
    # ---------------------------------------------------------------- I. PHÍ KHÁC
    ("pk_phi_chuyen_khoan", "Phí chuyển khoản – phí ngân hàng", "PK", "chung", "deu_khach_co_thu", False, "ca_hai", "ngan_hang"),
    ("pk_thue_nop_ho", "Thuế nộp hộ – thuế nhà thầu", "PK", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("pk_sim_wifi", "SIM – wifi – thiết bị", "PK", "chung", "deu_moi_khach", False, "nuoc_ngoai", "khac"),
    ("pk_phat_sinh", "Chi phí phát sinh trên đường", "PK", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
    ("pk_khac", "Phí khác (ghi rõ)", "PK", "chung", "deu_khach_co_thu", False, "ca_hai", "khac"),
]

KHOAN_MUC = {
    ma: {"ma": ma, "ten": ten, "nhom": nhom, "ten_nhom": NHOM[nhom], "doi_tuong": dt,
         "quy_tac_phan_bo": qt, "dich_danh": dd, "hinh_thuc": ht, "loai_ncc": ncc}
    for ma, ten, nhom, dt, qt, dd, ht, ncc in _D
}


def danh_sach(hinh_thuc: str | None = None) -> list[dict]:
    """Danh mục để màn hình dựng ô chọn, lọc theo hình thức tour.

    Không lọc khi chưa biết hình thức: thà hiện thừa vài khoản còn hơn giấu mất khoản người ta cần
    rồi họ gõ vào ô "khác".
    """
    ds = list(KHOAN_MUC.values())
    if hinh_thuc in ("trong_nuoc", "nuoc_ngoai"):
        ds = [k for k in ds if k["hinh_thuc"] in ("ca_hai", hinh_thuc)]
    return sorted(ds, key=lambda k: (k["nhom"], k["ma"]))


def mac_dinh(ma: str | None) -> dict:
    """Bốn mặc định của một khoản mục. Mã lạ thì trả rỗng chứ KHÔNG đoán sang mã gần giống.

    Đoán "gần giống" ở đây là cách nhanh nhất để một khoản chi nằm sai nhóm mà không ai biết – và
    nhóm sai thì báo cáo chi phí theo khoản mục sai theo, im lặng.
    """
    k = KHOAN_MUC.get(ma or "")
    if not k:
        return {}
    return {"nhom": k["ten_nhom"], "doi_tuong": k["doi_tuong"],
            "quy_tac_phan_bo": k["quy_tac_phan_bo"], "dich_danh": k["dich_danh"]}


def la_khoan_khac(ma: str | None) -> bool:
    """Khoản mục thuộc nhóm 'khác' – chưa có mã riêng trong danh mục.

    Đếm tiền rơi vào đây là cách biết danh mục còn thiếu gì. Nhiều tiền ở 'khác' không phải lỗi của
    người nhập; đó là việc phải bổ sung danh mục.
    """
    return bool(ma) and ma.endswith("_khac")
