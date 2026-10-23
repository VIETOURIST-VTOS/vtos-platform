"""Chủ tịch toàn quyền – MỘT luật, và phép kiểm giữ cho nó không bị bỏ sót lần nữa.

QUYẾT ĐỊNH 06/9/2026: Chủ tịch HĐQT có toàn quyền chức năng trên mọi phân hệ. Nó được cài vào
`deps.FULL_ACCESS`, kèm một dòng chú thích nói rằng đặt ở "đúng một chỗ" thì "về sau không có endpoint
nào bị bỏ sót".

NGÀY 13/9/2026 CÂU ẤY HOÁ RA SAI, và sai theo đúng kiểu mà một hằng số hay sai. `FULL_ACCESS` chỉ được
đọc bên trong `require_roles`. Còn 43 chỗ khác trong kho tự viết `if u.role not in X: raise 403` ngay
trong thân hàm – không chỗ nào nhìn thấy nó.

Chủ tịch phát hiện khi mở tab “Quyết toán chi tiết” của một chuyến: màn hình báo “Vai trò của anh/chị
không khai được hình thức”. Cửa ghi thật sự VẪN MỞ cho ông – `require_roles(*NHAP)` cho qua nhờ
FULL_ACCESS – nhưng cái CỜ mà màn hình đọc để quyết định vẽ nút hay vẽ câu từ chối lại tự kiểm
`u.role in NHAP` bằng tay, ngay dưới một dòng chú thích tên là “MỘT NGUỒN SỰ THẬT VỀ QUYỀN NHẬP”.
Cửa mở, biển đề đóng. Người dùng tin biển.

PHÉP KIỂM TRẢ LỜI ĐÚNG MỘT CÂU: còn chỗ từ chối nào theo vai trò mà Chủ tịch bị chặn, và chỗ ấy chưa
được khai là CỐ Ý không?

BỐN CÁCH MỘT CHỖ TỪ CHỐI ĐƯỢC CHO QUA

  1. Gọi `toan_quyen(u)` trong chính điều kiện – cách đúng, và là cách bộ kiểm đọc được chắc chắn nhất.
  2. Danh sách vai trò của nó ĐÃ CÓ "chutich" – tra sống bằng cách nạp module rồi đọc tên. Không chép
     lại thành danh sách thứ hai: hôm nào ai đó bỏ "chutich" khỏi danh sách ấy thì bộ kiểm đỏ ngay.
  3. Gọi `toan_quyen_ke_ca_tach_bach(u, db)` VÀ được khai trong MO_THEO_CONG_TAC kèm lý do – cửa
     tách bạch trách nhiệm, chỉ mở khi tham số `chu_tich_mo_het_cua` đang bật.
  4. Khai vào GIU_DONG kèm lý do – cửa đóng với MỌI người, không công tắc nào mở được.

HAI LOẠI CỬA, VÀ TRỘN CHÚNG LÀ CÁCH HỎNG ÂM THẦM NHẤT

“Toàn quyền” là chuyện PHÂN QUYỀN: ai được làm việc gì. Có một loại cửa khác hẳn, gọi là TÁCH BẠCH
TRÁCH NHIỆM: việc này và việc kia phải do HAI NGƯỜI làm, bất kể hai người ấy to đến đâu. Người ký lệnh
chi và người bấm nút đã-chi mà là một người thì công ty mất lớp kiểm soát chống gian lận cổ điển nhất
đang có, và Ban Kiểm soát mất chỗ dựa để đối chiếu.

Chủ tịch chốt 13/9/2026 MỞ CẢ LOẠI THỨ HAI để chạy thử và trình diễn – nhưng mở sau một CÔNG TẮC
(tham số `chu_tich_mo_het_cua`), không viết cứng vào từng chỗ. Ba điều công tắc mua được, mà viết cứng
thì không:

  * Đóng lại vào ngày vận hành thật là đổi MỘT DÒNG tham số, không phải sửa chín chỗ trong sáu tệp,
    chạy lại phép thử và đẩy một bản nâng cấp. Một việc phải làm mà tốn một bản nâng cấp là một việc
    sẽ bị hoãn, rồi bị quên.
  * Tham số là con số ĐỌC ĐƯỢC, nên `quet()` dưới đây nêu nó thành phát hiện `tach_bach_dang_mo`.
    Ban Kiểm soát nhìn thấy hệ thống đang ở chế độ nào thay vì phải đọc mã nguồn. Một lớp kiểm soát
    bị tắt mà không ai NHÌN THẤY nó đang tắt thì tệ hơn là chưa từng có – người ta vẫn tin nó chạy.
  * Bộ kiểm phân biệt được cửa nào mở vĩnh viễn và cửa nào mở tạm. Nếu ai đó hạ một cửa tách bạch
    xuống `toan_quyen` trần, `cong_tac_hong` bắt ngay – nếu không, công tắc vẫn ở đó, vẫn tắt bật
    được, mà cửa thì đã mở vĩnh viễn và không ai nhận ra.

Cả (3) và (4) bắt buộc có LÝ DO viết ra, y như `ks_cua_nhap.MAY_SINH`: “khai để cho qua” là lối thoát
dễ nhất, nên phải viết được vì sao thì mới khai được.

CHỖ BỘ KIỂM NÀY KHÔNG NHÌN THẤY – nói ra để không ai đọc xong rồi yên tâm quá mức:

  * Nó đọc ĐIỀU KIỆN của lệnh từ chối, không chạy thử. Một hàm phụ trợ nhận `u.role` rồi tự chặn bên
    trong thì điều kiện ở đây chỉ là một lời gọi hàm – bộ kiểm không đi vào trong được, nên nó đòi
    những chỗ ấy phải KHAI (xem `intake`, `attachments` dưới đây). Khai chứ không lờ đi.
  * Danh sách vai trò dựng lúc chạy từ cơ sở dữ liệu (`nd_vai_tro_ky_2(db)`) thì không tra tĩnh được,
    nên cũng phải khai.
  * Nó không kiểm MÀN HÌNH. Màn hình tự suy quyền rồi ẩn nút thì đây không thấy – đó đúng là lỗi
    13/9 ở phía cờ `nhap_duoc`, và chỗ gác nó là phép thử của từng màn hình.
"""
import ast
import importlib
import os

# Vai trò có toàn quyền. Đọc lại từ deps để không thành danh sách thứ hai.
from app.api.deps import FULL_ACCESS, KHOA_MO_HET_CUA

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # …/app

# Lời từ chối. Chỉ những thứ này mới làm một khối `if` trở thành CỬA CHẶN.
LOI_TU_CHOI = ("HTTPException", "PermissionError", "Gate", "ValueError")


# ---------------------------------------------------------------------------------------------
# HAI BẢN KHAI, VÀ SỰ KHÁC NHAU GIỮA CHÚNG LÀ ĐIỀU QUAN TRỌNG NHẤT TRONG TỆP NÀY
#
#   MO_THEO_CONG_TAC – cửa tách bạch trách nhiệm, mở cho Chủ tịch KHI VÀ CHỈ KHI tham số
#                      `chu_tich_mo_het_cua` đang bật. Chủ tịch chốt 13/9/2026 mở để chạy thử.
#                      Mỗi cửa ở đây phải gọi `toan_quyen_ke_ca_tach_bach`, KHÔNG được gọi
#                      `toan_quyen` trần – gọi trần là mở vĩnh viễn, và cái công tắc thành đồ trang
#                      trí. Phép thử TQ9 canh đúng chuyện đó.
#
#   GIU_DONG        – cửa đóng với MỌI người, không công tắc nào mở được, cộng vài cửa mà bộ kiểm
#                      không tự tra được nhưng đã tra tay là không chặn.
#
# Khoá là (đường dẫn tệp từ app/, tên hàm) chứ KHÔNG phải số dòng: số dòng đổi mỗi lần ai đó thêm
# một dòng phía trên, và một danh sách tự sai sau mỗi lần sửa là danh sách không ai giữ.
# ---------------------------------------------------------------------------------------------
MO_THEO_CONG_TAC: dict[tuple[str, str], str] = {

    # Khoá là (tệp, CÂU TỪ CHỐI mà người dùng nhìn thấy) chứ không phải tên hàm. Lý do cụ thể: hàm
    # ops.step chứa BA cửa khác loại nhau – một cửa phân quyền thường (trưởng bộ phận xác nhận, mở
    # thẳng) và hai cửa tách bạch trách nhiệm (Kế toán kiểm tra, Kế toán bấm ĐÃ CHI, mở theo công
    # tắc). Khoá theo tên hàm gộp cả ba làm một, nên hạ một cửa xuống `toan_quyen` trần mà bộ kiểm
    # vẫn xanh. Câu từ chối thì đúng một cửa một câu, và nó cũng là thứ dễ tra nhất: người gặp lỗi
    # đọc được đúng câu ấy trên màn hình.
    ("services/ops.py", "Chỉ Kế toán kiểm tra"):
        "Kế toán kiểm chứng từ trước khi trình duyệt. Bước duyệt ngay sau đó chính là chữ ký của "
        "Chủ tịch, nên lúc công tắc BẬT thì một người đi được cả hai bước. Chấp nhận khi chạy thử vì "
        "chưa có đồng tiền thật nào đi qua; vận hành thật thì phải đóng.",

    ("services/ops.py", "Chỉ Kế toán ghi nhận đã chi"):
        "Bấm ĐÃ CHI sau khi có lệnh chi được duyệt. Đây là nửa sau của lớp chống gian lận cổ điển "
        "nhất công ty đang có: người KÝ lệnh chi và người bấm ĐÃ CHI phải là hai người. Công tắc bật "
        "thì lớp ấy tạm thời không còn – đến ngày vận hành thật, ĐÂY LÀ CỬA ĐẦU TIÊN phải đóng lại.",

    ("services/tours.py", "Chỉ Kế toán xác nhận quyết toán"):
        "Con số được xác nhận ở bước này là căn cứ DUY NHẤT tính thưởng chuyến. Công tắc bật thì Chủ "
        "tịch chạy hết được vòng quyết toán khi trình diễn, không phải đi mượn tài khoản Kế toán.",

    ("services/tours.py", "Chỉ CNTT đối chiếu độc lập"):
        "CNTT đối chiếu doanh thu booking với doanh thu quyết toán rồi khoá chuyến. Công tắc bật thì "
        "Chủ tịch đưa được chuyến đi hết vòng tới trạng thái khoá. Lúc vận hành thật thì chữ “độc "
        "lập” phải trở lại đúng nghĩa của nó.",

    ("services/settlement.py", "Chỉ Kế toán trả lại quyết toán"):
        "Mặt kia của bước Kế toán xác nhận, mở cùng lý do: để chạy được cả vòng quay quyết toán trên "
        "một tài khoản khi trình diễn.",

    ("services/marketing.py",
     "Chữ ký thứ hai cho nội dung có cam kết hoặc số liệu tài chính phải là Ban TGĐ hoặc Pháp chế ("):
        "Phần chặn THEO VAI TRÒ của chữ ký thứ hai. Hai chốt còn lại trong chính hàm ấy KHÔNG mở "
        "theo công tắc, và cố ý thế: người soạn vẫn không tự duyệt được nội dung của mình, và một "
        "người vẫn không ký được hai lần.",

    ("api/v1/access.py", "Chỉ CNTT thao tác trên tài khoản lãnh đạo"):
        "Đổi vai trò tài khoản lãnh đạo (chutich/tgd). Công tắc bật thì Chủ tịch tự dựng và đổi được "
        "tài khoản thử mà không phải nhờ CNTT mỗi lần. ĐÂY LÀ CỬA RỦI RO NHẤT trong sáu cửa: lúc "
        "bật, ai chiếm được phiên đăng nhập của Chủ tịch cũng đổi được vai trò lãnh đạo. Chốt “không "
        "tự đổi vai trò của chính mình” vẫn còn nguyên – công tắc không mở nó.",

    ("api/v1/hr.py", "Chỉ CNTT thao tác trên tài khoản lãnh đạo"):
        "Sửa hồ sơ tài khoản lãnh đạo – cùng lý do và cùng rủi ro. Chốt “không tự khóa tài khoản của "
        "mình” vẫn còn nguyên, nên không tự nhốt mình ra ngoài hệ thống được.",

    ("api/v1/hr.py", "Chỉ CNTT đặt lại mật khẩu lãnh đạo"):
        "Đặt lại mật khẩu tài khoản lãnh đạo – để dựng được tài khoản tgd thử mà chạy luồng hai chữ "
        "ký cho đúng. Mật khẩu đặt lại luôn là mật khẩu TẠM, người nhận phải đổi ở lần đăng nhập đầu.",
}


GIU_DONG: dict[tuple[str, str], str] = {

    # ---- ĐÓNG VĨNH VIỄN – không công tắc nào mở, và lý do không phải là phân quyền ----
    ("api/v1/routes.py", "propose_param"):
        "Đợt LG2, Chủ tịch chốt 11/10/2026: tham số chính sách đi MỘT chữ ký Chủ tịch, và luật "
        "NGƯỜI TRÌNH KHÔNG TỰ KÝ giữ nguyên. Hai điều ấy cộng lại nghĩa là Chủ tịch tự trình một "
        "tham số thì KHÔNG AI KÝ ĐƯỢC nữa — nên cửa trình chặn ông ngay, kèm lời nhắn nhờ Kế "
        "toán / HCNS / CNTT trình. Đây là TÁCH BẠCH TRÁCH NHIỆM chứ không phải phân quyền: việc "
        "trình và việc ký phải là hai người, bất kể hai người ấy to đến đâu, và chính Chủ tịch "
        "chọn giữ luật ấy khi được hỏi. Mở ra thì một người làm trọn từ đầu đến cuối và ba cửa "
        "chính sách không còn lớp kiểm soát nào. Chặn này KHÔNG làm ông mất quyền quyết: ông vẫn "
        "ký, chỉ là không tự trình — và nó TỰ BIẾN MẤT nếu bảng chữ ký đổi lại thành hai vai, vì "
        "điều kiện có vế `len(can_ky_tham_so) == 1`.",

    ("api/v1/routes.py", "trinh_dieu_khoan"):
        "Đợt E4a, Chủ tịch chốt 12/10/2026: điều khoản thanh toán đi MỘT chữ ký Chủ tịch. Cộng với "
        "luật NGƯỜI TRÌNH KHÔNG TỰ KÝ, Chủ tịch tự trình một điều khoản là hồ sơ KHÔNG AI KÝ ĐƯỢC "
        "— nên cửa trình chặn ngay, kèm lời nhắn nhờ Kế toán / HCNS / CNTT trình. Cùng một lẽ và "
        "cùng một hình với `propose_param` ở trên: đây là TÁCH BẠCH TRÁCH NHIỆM, không phải phân "
        "quyền, và chính Chủ tịch chọn giữ luật ấy. Chặn này KHÔNG làm ông mất quyền quyết — ông "
        "vẫn ký — và nó TỰ BIẾN MẤT nếu bảng chữ ký đổi thành hai vai, vì điều kiện có vế "
        "`len(can) == 1`. Đợt E4a dựng cửa này mà quên khai vào đây, nên bộ kiểm toàn quyền đỏ "
        "trên main từ 12/10 đến 13/10; Đợt DỌN-1 khai nốt.",

    ("services/giu_luong.py", "lap"):
        "CN-2, Chủ tịch chốt 21/10/2026: bảng lương bổ sung đi CÙNG CHUỖI với bảng chính — HCNS lập "
        "và kiểm, Chủ tịch hoặc TGĐ ký. Bước lập chặn mọi vai khác, kể cả Chủ tịch, vì đây là TÁCH "
        "BẠCH TRÁCH NHIỆM chứ không phải phân quyền: người lập bảng lương và người ký nó phải là hai "
        "người, đúng như bảng chính (cửa kiểm cơ sở chỉ HCNS/CNTT bấm). Chặn này KHÔNG làm ông mất "
        "quyền quyết: ông vẫn ký ở bước cuối (`tien`, VAI_KY có chutich).",

    ("services/xac_nhan_cong.py", "hcns_xac_nhan"):
        "CN-1, Chủ tịch chốt 21/10/2026: công tháng đi HAI bước — HCNS lập và xác nhận, TGĐ duyệt "
        "(Chủ tịch duyệt được). Bước HCNS chặn mọi vai khác, kể cả Chủ tịch, vì đây là TÁCH BẠCH "
        "TRÁCH NHIỆM chứ không phải phân quyền: người lập bảng công và người duyệt nó phải là hai "
        "người. Mở bước lập cho Chủ tịch thì một người tự lập rồi tự duyệt, và chữ «đã duyệt» trên "
        "bảng lương không còn mang nghĩa có người thứ hai đã nhìn. Chặn này KHÔNG làm ông mất quyền "
        "quyết: ông vẫn duyệt ở bước hai (`tgd_duyet`, VAI_DUYET có chutich).",

    ("services/chu_ky.py", "kiem_tra_nguoi_ky"):
        "Bộ kiểm chữ ký nhiều vai dùng chung (Phụ lục 27/8/2026 mục 3.2). Ở cửa này Chủ tịch VỐN ĐÃ "
        "nằm trong danh sách được ký – nó không chặn ai vì vai trò. Thứ nó chặn là MỘT NGƯỜI KÝ THAY "
        "CẢ HAI VAI, và mô hình dữ liệu chỉ có hai ô signed_chutich / signed_tgd: mở ra thì sổ ghi "
        "một chữ ký TGĐ mà TGĐ chưa hề bấm. Đó không phải nới quyền, đó là GHI SAI SỔ – và con số "
        "sai ấy không ai đọc lại mà biết được. Muốn trình diễn luồng hai chữ ký thì dựng một tài "
        "khoản tgd thử và bấm bên ấy một cái; luồng chạy đủ và sổ ghi đúng.",

    # ---- KHÔNG CHẶN CHỦ TỊCH, nhưng bộ kiểm không tự thấy được ----
    ("api/v1/intake.py", "nhap_mot_dong"):
        "Quyền nạp và quyền xác nhận số máy đọc từ ảnh nằm trong intake.duoc_nap() / "
        "duoc_xac_nhan_anh() – bộ kiểm không đi vào trong hàm phụ trợ được. Đã tra tay 13/9/2026: "
        "Chủ tịch nạp được cả 30/30 bộ nạp và xác nhận ảnh được, vì QUAN_TRI = (chutich, tgd, cntt) "
        "là giá trị mặc định của mọi bộ. (Chỉ CNTT bị loại khỏi cửa xác nhận ảnh, vì CNTT vận hành "
        "mô hình đọc ảnh thì không được tự xác nhận kết quả của nó – P5 08/9/2026.) Không chặn.",

    ("api/v1/intake.py", "nap"):
        "Cùng hai hàm phụ trợ duoc_nap() / duoc_nap_tep() như trên. Không chặn Chủ tịch.",

    ("api/v1/attachments.py", "tai_ve"):
        "Đọc tệp nhạy cảm, cùng danh sách AT.VAI_TRO_NHAY_CAM đã có “chutich”. Quyền nằm trong "
        "AT.duoc_doc() nên bộ kiểm không tra tĩnh được. Không chặn.",

    ("services/chu_ho_so.py", "giao_ho_so"):
        "Điều kiện bộ kiểm bắt được là `nguoi_moi.role not in CHU_HO_SO_ROLES` — vai của NGƯỜI "
        "NHẬN hồ sơ, không phải vai của người gọi cửa. Bộ kiểm đọc mọi lệnh từ chối có chữ `role` "
        "và không phân biệt được hai thứ ấy, nên phải khai ra đây thay vì để nó báo oan. Cửa dành "
        "cho NGƯỜI GỌI nằm ngay phía trên và ĐÃ có `or toan_quyen(u)`: Chủ tịch bàn giao được hồ "
        "sơ của bất kỳ chuyến nào. Thứ dòng này chặn là giao hồ sơ quyết toán cho một vai không "
        "giữ hồ sơ quyết toán — Chủ tịch cũng không giao cho Kinh doanh được, và đó là cùng một "
        "ranh giới câu 7 ngày 25/9/2026 đã chốt: quyết toán là số của bên ĐẶT dịch vụ.",

    ("services/hrm.py", "decide_leave"):
        "CHÍNH CHỦ TỊCH ĐẶT CỬA NÀY, và đặt bằng một chữ trong câu nói ngày 30/9/2026: “nghỉ phép, "
        "ốm đau, vắng việc sẽ do Huấn duyệt, TGĐ và CT THẤY.” Thấy, không ký. Đây không phải lần "
        "phân quyền quên mở cho Chủ tịch — đây là tách bạch trách nhiệm do người có toàn quyền tự "
        "vạch ra cho mình, và loại cửa ấy mở ra thì không còn là cửa. "
        "VÀ NÓ KHÔNG PHẢI CỬA CHẶN CHỦ TỊCH THEO NGHĨA THƯỜNG: Chủ tịch vẫn ĐỌC được mọi đơn của "
        "mọi phòng (ông nằm trong HR_READ), vẫn ký được đơn của chín phòng chưa chốt người ký "
        "(hrm.KY_MAC_DINH có “chutich”). Thứ dòng này nói là đơn của Đội xe và Hướng dẫn đi về "
        "đúng một người — nếu không thì một đơn ký ở trên xuống sẽ qua mặt chính người quản lý "
        "trực tiếp, và người ấy không biết hôm sau thiếu ai. "
        "ĐỔI THÌ ĐỔI Ở BẢNG, KHÔNG ĐỔI Ở ĐÂY: thêm “chutich” vào hrm.TUYEN_KY_DON['doi_xe'] là "
        "một dòng, đọc được, và có người quyết. Thêm `or toan_quyen(u)` vào hàm thì cùng kết quả "
        "mà không ai thấy, và bảng luồng công việc vẫn khai một chuỗi chỉ huy không còn thật.",

    # ---- BỐN CỬA CỦA ĐỢT NS-5, Chủ tịch chốt 09/10/2026 là TÁCH BẠCH TRÁCH NHIỆM ----

    ("services/danh_gia_ns.py", "cham"):
        "Chấm ba ô B của bản đánh giá nhân sự. ĐÂY LÀ CÙNG MỘT CỬA VỚI `hrm.decide_leave` ở trên, "
        "chỉ khác tên: tuyến chấm dùng lại đúng `hrm.TUYEN_KY_DON`, tức là chính cái tuyến Chủ "
        "tịch tự vạch ra cho mình ngày 30/9/2026 — “nghỉ phép, ốm đau, vắng việc sẽ do Huấn duyệt, "
        "TGĐ và CT THẤY”. Thấy, không ký. Mở cửa chấm cho Chủ tịch mà không mở cửa ký đơn là để "
        "hai cửa cùng đọc một bảng mà trả lời ngược nhau. "
        "VÀ NÓ CÒN PHÁ MỘT CÁI NEO. Ba ô A do máy điền tồn tại để hệ thống in ra độ lệch “điểm "
        "người – điểm máy” theo TỪNG trưởng phòng: ai chấm tay cao hơn số máy đều đặn thì hiện ra "
        "ngay kỳ sau. Cái neo ấy chỉ có nghĩa khi mỗi phòng có đúng một người chấm. Thêm một người "
        "chấm được mọi phòng là độ lệch không còn quy về ai, và cột ấy thành một con số không ai "
        "đọc. "
        "Chủ tịch KHÔNG mất gì để xem: ông ĐỌC được mọi bản của mọi phòng, và điểm chỉ để XÉT — "
        "mức thưởng từng người vẫn do TGĐ và Chủ tịch quyết bằng tay, không một dòng mã nào biến "
        "điểm thành tiền. ĐỔI THÌ ĐỔI Ở `hrm.TUYEN_KY_DON`, một dòng đọc được và có người quyết.",

    ("services/mua_sam_cap_phat.py", "ghi_da_chi"):
        "Chữ ký THỨ HAI của đề nghị mua, và đây là cửa KHÔNG ĐƯỢC MỞ rõ ràng nhất trong bốn cửa: "
        "Chủ tịch ĐÃ là người ký vế MỘT — `VAI_DUYET_MUA = (tgd, chutich)`. Người duyệt nói ĐƯỢC "
        "MUA; Kế toán nói ĐÃ CHI. Cho cùng một người ký cả hai vế thì hai chữ ký còn đúng một, và "
        "nó sập đúng vào chỗ nguy nhất: một người vừa chuẩn chi vừa xác nhận tiền đã ra. Cùng một "
        "ranh giới mà `services/chu_ky.py` đã giữ từ Phụ lục 27/8/2026 mục 3.2. "
        "Chủ tịch vẫn ĐỌC được mọi đề nghị và mọi dòng đã chi; thứ ông không làm là tự tay đóng "
        "vế hai của chứng từ mình vừa duyệt.",

    ("services/mua_sam_cap_phat.py", "cap_phat"):
        "Lập biên bản cấp phát tài sản cho nhân viên — CHÍNH CHỦ TỊCH ĐẶT CỬA NÀY ngày 08/10/2026 "
        "(“cấp phát do HCNS lập”), và lời từ chối trong mã ghi thẳng ngày ấy. Biên bản cấp phát là "
        "một lời chứng về HIỆN VẬT: ai trao món đồ tận tay thì người ấy ký. Nó không phải một nấc "
        "quyền, nên mở theo vai trò là hiểu sai loại cửa. "
        "Thêm một lý do thứ hai cùng họ với cửa ghi-đã-chi ở trên: Chủ tịch nằm trong "
        "`VAI_DUYET_MUA`, nên mở cửa này ra là một người vừa duyệt mua một món vừa xác nhận món ấy "
        "đã được trao cho ai — hai đầu của cùng một chuỗi, không còn ai đối chiếu.",

    ("services/mua_sam_cap_phat.py", "ghi_tra"):
        "Ghi nhận trả lại tài sản — cùng một quyển sổ và cùng một đôi tay với cửa cấp phát ngay "
        "trên. Ghi trả là một lời chứng về TÌNH TRẠNG món đồ lúc nhận lại, và tình trạng ấy quyết "
        "định lần cấp cho người tiếp theo. Người trao là người nhận lại thì còn một người chịu "
        "trách nhiệm về hiện vật; hai đầu hai người thì mất đúng cái ấy. "
        "ĐỔI THÌ ĐỔI Ở `VAI_CAP_PHAT` của `services/mua_sam_cap_phat.py` — một dòng, đọc được, và "
        "có người quyết.",
}


# ---------------------------------------------------------------------------------------------
# Bộ đọc
# ---------------------------------------------------------------------------------------------
def _ten_module(duong_dan: str) -> str:
    return "app." + os.path.relpath(duong_dan, GOC)[:-3].replace(os.sep, ".")


def _tra(ten: ast.expr, mod) -> tuple[bool, object]:
    """Tra một tên (NHAP, AC.REQUEST_CREATE_ROLES) ra giá trị thật. (tra_được, giá_trị)."""
    if isinstance(ten, (ast.Tuple, ast.List, ast.Set)):
        try:
            return True, ast.literal_eval(ten)
        except (ValueError, TypeError, SyntaxError):
            return False, None
    if isinstance(ten, ast.Constant):
        return True, ten.value
    if isinstance(ten, ast.Name):
        return (True, getattr(mod, ten.id)) if hasattr(mod, ten.id) else (False, None)
    if isinstance(ten, ast.Attribute):
        goc, duoi = ten.value, ten.attr
        if isinstance(goc, ast.Name) and hasattr(mod, goc.id):
            o = getattr(mod, goc.id)
            return (True, getattr(o, duoi)) if hasattr(o, duoi) else (False, None)
    return False, None


def _la_u_role(n: ast.expr) -> bool:
    return isinstance(n, ast.Attribute) and n.attr == "role" and isinstance(n.value, ast.Name)


def _phep_so_vai_tro(dieu_kien: ast.expr) -> list[ast.Compare]:
    """Mọi phép so sánh có vế là <ai đó>.role."""
    ra = []
    for n in ast.walk(dieu_kien):
        if isinstance(n, ast.Compare) and (_la_u_role(n.left)
                                           or any(_la_u_role(c) for c in n.comparators)):
            ra.append(n)
    return ra


def _role_di_vao_loi_goi(dieu_kien: ast.expr) -> bool:
    """u.role bị truyền vào một hàm khác – quyền nằm trong hàm ấy, đọc từ đây không thấy."""
    for n in ast.walk(dieu_kien):
        if isinstance(n, ast.Call) and any(_la_u_role(a) for a in n.args):
            return True
    return False


def _chan_chu_tich(so: ast.Compare, mod) -> bool | None:
    """Phép so sánh này, với role = "chutich", có cho ra KẾT QUẢ TỪ CHỐI không?

    None = không tra được danh sách, phải khai.
    """
    if len(so.ops) != 1 or len(so.comparators) != 1:
        return None
    op, ve_kia = so.ops[0], so.comparators[0]
    if not _la_u_role(so.left):                 # dạng "chutich" == u.role – hiếm, đảo lại
        if _la_u_role(ve_kia):
            ve_kia = so.left
        else:
            return None
    duoc, gia_tri = _tra(ve_kia, mod)
    if not duoc:
        return None
    cho_moi = FULL_ACCESS[0]
    try:
        if isinstance(op, ast.NotIn):
            return cho_moi not in gia_tri       # not in ⇒ True nghĩa là bị từ chối
        if isinstance(op, ast.In):
            return cho_moi in gia_tri
        if isinstance(op, ast.NotEq):
            return cho_moi != gia_tri
        if isinstance(op, ast.Eq):
            return cho_moi == gia_tri
    except TypeError:
        return None
    return None


def _thong_diep(than: list[ast.stmt]) -> str:
    """Câu từ chối mà người dùng nhìn thấy – khoá của MO_THEO_CONG_TAC.

    Bền hơn tên hàm (một hàm có thể chứa nhiều cửa khác loại) và bền hơn số dòng. Chuỗi ghép f-string
    thì lấy đoạn chữ ĐẦU TIÊN, vì phần biến đổi theo dữ liệu không dùng làm khoá được.
    """
    for n in ast.walk(ast.Module(body=than, type_ignores=[])):
        if not (isinstance(n, ast.Raise) and n.exc is not None):
            continue
        e = n.exc
        args = e.args if isinstance(e, ast.Call) else []
        for a in args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.strip():
                return a.value
            if isinstance(a, ast.JoinedStr):
                for ph in a.values:
                    if isinstance(ph, ast.Constant) and isinstance(ph.value, str) and ph.value.strip():
                        return ph.value
    return ""


def _ham_bao(cay: ast.Module, dong: int) -> str:
    """Tên hàm chứa dòng này – khoá của GIU_DONG, bền hơn số dòng."""
    ten = ""
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.lineno <= dong <= (n.end_lineno or n.lineno):
                ten = n.name
    return ten


def _co_loi_tu_choi(than: list[ast.stmt]) -> bool:
    for n in ast.walk(ast.Module(body=than, type_ignores=[])):
        if isinstance(n, ast.Raise) and n.exc is not None:
            e = n.exc
            f = e.func if isinstance(e, ast.Call) else e
            ten = getattr(f, "id", None) or getattr(f, "attr", None)
            if ten not in LOI_TU_CHOI:
                continue
            if ten == "HTTPException" and isinstance(e, ast.Call) and e.args:
                a = e.args[0]
                if isinstance(a, ast.Constant) and a.value != 403:
                    continue
                if isinstance(a, ast.Attribute) and "403" not in ast.unparse(a):
                    continue
            return True
    return False


TEN_HAM_CONG_TAC = "toan_quyen_ke_ca_tach_bach"


def bang() -> dict:
    """Trả về bốn thứ, và ba trong bốn phải rỗng:

      chan        – cửa đang chặn Chủ tịch mà chưa ai khai. Phải rỗng.
      cong_tac_hong – cửa KHAI là mở-theo-công-tắc nhưng lại gọi `toan_quyen` TRẦN, nghĩa là nó mở
                      vĩnh viễn và cái công tắc chỉ còn là đồ trang trí. Phải rỗng.
      khai_thua   – dòng khai không ứng với cửa nào trong mã. Phải rỗng.
      so_cua      – đếm được bao nhiêu cửa; dùng để biết bộ kiểm có thật sự nhìn thấy gì không.
    """
    chan, thay, cong_tac_hong, thay_cong_tac = [], set(), [], set()
    for thu_muc, _, tep in os.walk(GOC):
        for t in sorted(tep):
            if not t.endswith(".py"):
                continue
            p = os.path.join(thu_muc, t)
            rel = os.path.relpath(p, GOC).replace(os.sep, "/")
            try:
                cay = ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError:
                continue
            mod = None
            for n in ast.walk(cay):
                if not isinstance(n, ast.If) or not _co_loi_tu_choi(n.body):
                    continue
                dk = n.test
                chu = ast.unparse(dk)
                if "toan_quyen" in chu or "FULL_ACCESS" in chu:
                    # Cách (1) – cửa đã hỏi một trong hai hàm. Nhưng HỎI HÀM NÀO mới là chuyện: cửa
                    # tách bạch trách nhiệm phải hỏi hàm CÓ CÔNG TẮC, không được hỏi hàm trần. Hỏi
                    # trần là mở vĩnh viễn, và cái công tắc thành đồ trang trí – không ai nhận ra,
                    # vì cả hai đều xanh và cả hai đều tên là toan_quyen…
                    khoa = (rel, _thong_diep(n.body))
                    if khoa in MO_THEO_CONG_TAC:
                        thay_cong_tac.add(khoa)
                        if TEN_HAM_CONG_TAC not in chu:
                            cong_tac_hong.append({"tep": rel, "cau": khoa[1], "dong": n.lineno,
                                                  "dieu_kien": chu[:160]})
                    continue
                so = _phep_so_vai_tro(dk)
                qua_loi_goi = _role_di_vao_loi_goi(dk)
                if not so and not qua_loi_goi:
                    continue                                   # không phải cửa theo vai trò
                if mod is None:
                    try:
                        mod = importlib.import_module(_ten_module(p))
                    except Exception:                          # noqa – tệp không nạp được thì tra tay
                        mod = object()
                ket = [_chan_chu_tich(s, mod) for s in so]
                if not qua_loi_goi and ket and all(k is False for k in ket):
                    continue                                   # cách (2): danh sách đã có Chủ tịch
                ham = _ham_bao(cay, n.lineno)
                khoa = (rel, ham)
                thay.add(khoa)
                if khoa in GIU_DONG:
                    continue                                   # cách (3)
                chan.append({"tep": rel, "ham": ham, "dong": n.lineno, "dieu_kien": chu[:160]})
    thua = ((set(GIU_DONG) - thay) | (set(MO_THEO_CONG_TAC) - thay_cong_tac))
    return {"chan": chan, "cong_tac_hong": cong_tac_hong,
            "so_cua": len(thay) + len(thay_cong_tac),
            "khai_thua": sorted(f"{a}::{b}" for a, b in thua)}


def dang_mo_het(db) -> bool:
    """Công tắc `chu_tich_mo_het_cua` đang bật? Hỏi tham số, không đoán."""
    try:
        from app.services.rules import get_param
        return bool(get_param(db, KHOA_MO_HET_CUA))
    except Exception:      # noqa – chưa có bảng tham số thì coi như đóng
        return False


def quet(db) -> list[dict]:
    """Cửa vào cho vòng quét của robot Kiểm soát.

    Một lớp kiểm soát bị tắt mà không ai NHÌN THẤY nó đang tắt thì tệ hơn là chưa từng có: người ta
    vẫn tin nó đang chạy. Nên khi công tắc bật, robot nêu thành một phát hiện đứng tên toàn hệ thống,
    và nó tự biến mất ngay lần quét sau khi ai đó đặt tham số về 0.
    """
    if not dang_mo_het(db):
        return []
    cua = sorted(f"{a}::{b}" for a, b in MO_THEO_CONG_TAC)
    return [{"ma": "tach_bach_dang_mo#chu_tich", "loai": "tach_bach_dang_mo", "muc": "vang",
             "phong_ban": "", "vai_tro": "chutich", "doi_tuong": KHOA_MO_HET_CUA,
             "tom_tat": (f"Tham số {KHOA_MO_HET_CUA} đang BẬT: Chủ tịch đi qua được cả "
                         f"{len(cua)} cửa tách bạch trách nhiệm, trong đó có bước Kế toán bấm ĐÃ CHI "
                         f"và bước CNTT đối chiếu độc lập. Chủ tịch chốt 13/9/2026 mở để chạy thử và "
                         f"trình diễn. Đến ngày vận hành thật phải đặt lại về 0 – trong lúc còn bật, "
                         f"đừng đọc hai bước ấy như một lớp kiểm soát độc lập"),
             "chi_tiet": {"tham_so": KHOA_MO_HET_CUA, "cua": cua}}]


def _tach_bach_dang_mo(db) -> list[dict]:
    return quet(db)
