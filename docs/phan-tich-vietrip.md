**CÔNG TY CP DU LỊCH VIETOURIST -- BỘ PHẬN CNTT**

**PHÂN TÍCH CẤU TRÚC PHẦN MỀM VIETRIP**

**Bố trí phòng ban, luồng quản trị tour và đề xuất bổ sung cho VTOS**

*Khảo sát trực tiếp app.vietrip.com.vn ngày 05/9/2026 (tài khoản Giám
đốc) -- trình anh Trần Tuấn*

**1. Tóm tắt**

Vietrip là phần mềm vận hành tour theo mô hình \"sản phẩm → tour →
booking → thu/chi → quyết toán\", tổ chức menu theo phòng ban (Ban Giám
đốc, Kinh doanh, Điều hành, Kế toán, Marketing/CSKH, Đội xe, Báo cáo)
với 154 người dùng ở 9 phòng ban, 4 chức vụ, 8 nơi làm việc. Điểm mạnh
là quy trình tour 6 bước có lịch sử và bảng quyết toán chi phí theo nhà
cung cấp (có MST, chứng từ). Điểm yếu là thiếu kiểm soát tự động (không
cổng biên, không 2 chữ ký, không nhật ký bất biến), booking thiếu
trường, trang chi tiết tour chưa hoàn thiện, không có nhân sự -- lương
-- kế toán, và nhiều màn hình Marketing/Báo cáo đang phát triển. VTOS đã
bao phủ toàn bộ phần kiểm soát và hậu cần (kế toán, lương, HDV, xe,
SePay, dự báo dòng tiền) nhưng còn thiếu chính phần \"lõi vận hành
tour\" mà người dùng đang quen trên Vietrip: sản phẩm tour, trang chi
tiết tour theo tab, tiền bảo lưu, non-package, quy trình có lịch sử. Đề
xuất bổ sung 3 tuần theo thứ tự ưu tiên ở mục 6.

**2. Bố trí phòng ban trên Vietrip**

  -------------------------------------------------------------------------
  **Nhóm      **Màn hình**               **Phòng ban sử **Nhận xét**
  menu**                                 dụng**         
  ----------- -------------------------- -------------- -------------------
  Ban Giám    Tổng quan · Thông tin Tour Chủ            Duyệt dự toán,
  Đốc         · Duyệt chi · Duyệt đề     tịch/TGĐ/GĐ    duyệt chi NCC,
              xuất chi · Lịch sử Email   (chucVu = Giám duyệt đề xuất chi
                                         đốc)           

  Quản lý     Danh sách người dùng (chức IT             Phân quyền phẳng
  User        vụ Admin/Giám đốc/Trưởng                  theo 4 chức vụ,
              phòng/Nhân viên × phòng                   không theo nghiệp
              ban × nơi làm việc)                       vụ

  Quản Lý Xe  Danh sách xe (biển số, đời Đội xe         Chỉ hồ sơ xe --
              xe, tài xế, tổng km)                      không lệnh điều xe,
                                                        không giá thuê nội
                                                        bộ

  Quản Lý     Đặt Tour (tìm tour còn     KD Lẻ, Đoàn    Sale tự tạo
  Tour (Kinh  chỗ, sơ đồ chỗ ngồi) ·     (phòng Tour 72 booking; deadline
  doanh)      Thông tin Booking · Dịch   NV, Tour MICE  hủy chỗ; % cọc theo
              vụ Non-Package · Mở khóa   15)            sản phẩm
              booking                                   

  Điều Hành   Danh sách/Tạo Sản phẩm     Điều hành (19  Trung tâm vận hành:
              (tour cha, cơ cấu chi phí  NV + 1 TP)     mở tour từ sản
              11 khoản) · Đặt Tour ·                    phẩm, dự toán →
              Non-package · Thông tin                   quyết toán, đề xuất
              Booking · Tiền bảo lưu ·                  chi
              Thông tin Tour (chi tiết +                
              quyết toán) · Đề xuất chi                 
              NCC                                       

  Kế Toán     Xác nhận Thu Chi Khách ·   Kế toán (7 NV, Xác nhận phiếu
              Xác nhận Thu Chi NCC ·     1 TP, 3 GĐ, 1  thu/chi theo
              Thông tin Booking · Duyệt  Admin)         UNC/biên lai; chi
              đề xuất chi                               NCC theo lệnh

  Marketing / Khuyến mãi · Khách đã đi   Marketing (3   Nhiều màn hình mới,
  CSKH /      tour · Chiến dịch · Đề     NV, 2 GĐ),     phần lớn đang hoàn
  Khách hàng  xuất chi MKT · Tương tác   CSKH (3)       thiện
              KH · Phân loại KH (hành                   
              vi, tần suất, độ tuổi) ·                  
              Hồ sơ KH (lịch sử, chi                    
              tiêu, tour yêu thích, dịp                 
              đi, người đi cùng) · CSKH                 
              (cảm ơn, khảo sát, ưu đãi)                
              · Zalo                                    

  Báo cáo     Tour lẻ (bán tour, ngày,   Quản lý        Xuất Excel theo
              nhắc thu tiền) · Điều hành                khoảng ngày/mã
              (bán tour nội địa, chi                    tour; nhiều báo cáo
              tiết tour lẻ, hủy chỗ của                 \'đang phát triển\'
              sale, kinh doanh) ·                       
              Marketing (chiến dịch, KH,                
              chuyển đổi -- đang phát                   
              triển)                                    
  -------------------------------------------------------------------------

Người dùng (154): Tour 72 NV + 2 TP + 1 GĐ; Tour MICE 15 NV + 1 GĐ; Điều
hành 19 NV + 1 TP; Kế toán 7 NV + 1 TP + 3 GĐ + 1 Admin; Hướng dẫn 7;
Marketing 3 NV + 2 GĐ; CSKH 3; IT 1 NV + 2 Admin; Giám đốc 2; Kinh doanh
1; Đối tác 1; 9 tài khoản không có phòng ban. Nơi làm việc: TP.HCM, Hà
Nội, Hải Phòng, An Giang, Bình Dương, Đà Nẵng, Gia Lai, Phan Thiết --
trong đó Hà Nội/Hải Phòng đã đóng theo sơ đồ 01/9/2026 nhưng tài khoản
vẫn còn.

**3. Luồng quản trị tour trên Vietrip (quan sát từ tour
PT001.03060926)**

  -------------------------------------------------------------------------------
  **Bước**   **Việc**            **Ai làm**     **Ghi nhận**
  ---------- ------------------- -------------- ---------------------------------
  1          Khởi tạo quy trình  NV Điều hành   Mở tour từ sản phẩm (mã
             xử lý tour                         SP.NNddmmyy), số chỗ, giá
                                                ADL/CHD/INF (+KM)

  2          Đề nghị phê duyệt   NV Điều hành   Bảng dự chi theo NCC (loại DV,
             dự toán                            đơn giá, SL, hệ số) kèm lời giải
                                                trình

  3          Xác nhận, đề nghị   Trưởng phòng   Kiểm tra dự toán
             phê duyệt           Điều hành      

  4          Phê duyệt dự toán   Giám đốc       Không có cổng biên tự động -- GĐ
                                                tự cân nhắc (ví dụ tour
                                                PT001.03060926 biên 5,3% vẫn
                                                duyệt)

  4b         Xác nhận tạm ứng    Kế toán        Workflow tự chuyển nếu không tạm
             (nếu có)                           ứng

  5          Lập quyết toán tour NV Điều hành   Cập nhật thực chi từng dòng NCC
                                                (MST), file chứng từ, đã thanh
                                                toán

  6          Duyệt chi → Khóa    GĐ · Kế toán   Nút \'Duyệt chi\', \'Quyết
             tour (KTQT)                        toán\', \'Khóa Tour (KTQT)\' trên
                                                trang Chi tiết Tour; chi NCC qua
                                                Đề xuất chi → Xác nhận chi NCC
  -------------------------------------------------------------------------------

Dữ liệu đi kèm: Sản phẩm (mã, tên, điểm KH, loại nội địa/quốc tế, vùng,
quốc gia, điểm bán, phương tiện, loại xe, độ dài, số ngày, giá tham
khảo, % cọc, số ngày đóng tour, cần xác nhận; cơ cấu chi phí 11 khoản) →
Tour (mã SP.NN+ddmmyy, ngày KH/KT/đóng, số chỗ thường/KM, giá
ADL/CHD/INF thường/KM, trạng thái hoạt động/chờ xác nhận/hủy) → Booking
(người book, SĐT, ADL/CHD/INF, tổng tiền, tình trạng UNPAID/DEPO/PAID,
deadline hủy chỗ, người tạo, trạng thái OK/hủy) → Phiếu thu/chi khách
(hình thức, TK công ty, file UNC, Kế toán xác nhận) → Đề xuất chi NCC
(tour, NCC, hình thức TT, loại tiền, dòng dịch vụ) → Xác nhận chi NCC
(OrgID, FOP, TK NCC, KC/QQ/XX/GD) → Quyết toán (dòng chi phí theo NCC
MST, đơn giá, SL, hệ số, thực chi, đã thanh toán, file) → Tiền bảo lưu
(booking gốc, số tiền, tình trạng hoàn).

**4. Điểm còn thiếu / rủi ro trên Vietrip**

  -----------------------------------------------------------------------
  **Khu vực**       **Quan sát**
  ----------------- -----------------------------------------------------
  Trang Chi tiết    Chưa hoàn thiện: bảng đặt chỗ hiện dữ liệu mẫu
  Tour              (BK-2024001 Nguyễn Văn A), \'Còn trống: NaN\', Doanh
                    thu/Chi phí/Lợi nhuận = 0; danh sách tour cũng không
                    có doanh thu -- số thật chỉ nằm ở trang Quyết toán

  Dự toán 3 con số  Không có: dự toán chỉ là bảng dự chi theo NCC; biên
  & cổng biên       lợi nhuận không chặn, không cần 2 chữ ký, không giải
                    trình bắt buộc

  Booking           Chỉ 3 trường (tour, tên, SĐT, số khách); không có
                    nguồn khách, ghi chú chăm sóc; sale tự tạo booking
                    (không qua Điều hành một cửa); không mốc D-7; mã KM
                    tách ở Marketing

  Phân quyền        4 chức vụ × 9 phòng ban; không theo nghiệp vụ (ai
                    cũng thấy Thông tin Booking ở 3 menu khác nhau);
                    không nhật ký bất biến

  Nhân sự -- lương  Không có: phân công HDV, đơn giá, thang lương, báo
  -- HDV            cáo ngày, sự vụ; xe chỉ có hồ sơ

  Kế toán           Chỉ xác nhận phiếu thu/chi; không sổ sách, không bút
                    toán, không HĐĐT, không BCTC/thuế (đang nằm ở MISA)

  Báo cáo & API     Nhiều báo cáo \'đang phát triển\'; API nội bộ không
                    có lọc đến-ngày, giới hạn phân trang \~1.100 dòng,
                    không có API mở cho hệ thống khác
  -----------------------------------------------------------------------

**5. VTOS còn thiếu gì so với Vietrip (cần bổ sung)**

  -------------------------------------------------------------------------
  **Hạng mục**                            **Ưu     **Lý do**
                                          tiên**   
  --------------------------------------- -------- ------------------------
  Sản phẩm tour (tour cha) + cơ cấu chi   P1       Mở tour từ sản phẩm → dự
  phí chuẩn 11 khoản (vé MB, land, LSQ,            toán 3 con số tự sinh;
  bảo hiểm, quà tặng, phí TL, họp đoàn,            đồng bộ
  điều hành, dịch thuật, hoa hồng vé, phí          /operations/products
  CK)                                              

  Trang Chi tiết Tour đầy đủ theo tab:    P1       VTOS đã có dữ liệu
  thông tin · chỗ & giá · dự toán ·                (1.244 tour, dòng chi
  booking · thu tiền · chi NCC · quyết             phí) nhưng màn hình Tour
  toán (dòng NCC MST, file) · lịch sử quy          hiện chỉ là danh sách +
  trình                                            dự toán

  Quy trình 6 bước có lịch sử + lời giải  P1       Giữ thói quen người
  trình (như Quy trình & Lịch sử của               dùng, thêm kiểm soát
  Vietrip) gắn với cổng biên/2 chữ ký của          
  VTOS                                             

  Tiền bảo lưu (booking hủy giữ tiền →    P1       Đang phát sinh hằng ngày
  dùng cho tour sau / hoàn), deadline hủy          ở KD Lẻ
  chỗ, mở khóa booking, % cọc theo sản             
  phẩm                                             

  Dịch vụ Non-package (vé lẻ, khách sạn,  P2       Doanh thu ngoài tour,
  visa lẻ) -- bán không theo tour                  hiện VTOS không ghi nhận

  Đồng bộ Vietrip hằng ngày bằng robot    P1       Đã có kịch bản; cần lịch
  (tour, booking, thu chi, quyết toán) +           chạy tự động và bảng ánh
  ánh xạ phòng ban/chức vụ → vai trò VTOS          xạ vai trò

  CRM nhẹ: hồ sơ khách, lịch sử tour,     P2       Vietrip đang xây; VTOS
  phân loại, chiến dịch/khuyến mãi, cảm            làm sau khi lõi vận hành
  ơn sau tour, Zalo                                ổn

  Sơ đồ chỗ ngồi, nhiều điểm bán/văn      P3       
  phòng (8 nơi làm việc), lịch sử                  
  email/thông báo                                  
  -------------------------------------------------------------------------

Ngược lại, VTOS đã có mà Vietrip không có: dự toán 3 con số + cổng biên
10% + 2 chữ ký + giải trình; booking 4 trường bắt buộc và một cửa Điều
hành (SLA 2 giờ); mốc D-7; quyết toán 7/3 ngày; kế toán TT99 (bút toán
tự động, sổ, BCTC, thuế); SePay hai chiều; nhân sự -- lương -- HDV -- xe
-- sự vụ; báo cáo ngày; dự báo dòng tiền 13 tuần; hợp đồng tài chính;
dashboard theo vai trò; robot báo cáo; nhật ký bất biến.

**6. Đề xuất triển khai**

  -----------------------------------------------------------------------
  **Thời      **Việc**
  gian**      
  ----------- -----------------------------------------------------------
  Tuần 1      Sản phẩm tour + cơ cấu chi phí; Chi tiết Tour theo tab; quy
              trình 6 bước có lịch sử; robot đồng bộ Vietrip hằng đêm +
              ánh xạ vai trò; sửa Bảng điều khiển tải chậm (75 giây với
              10.000 booking → tính sẵn theo lô)

  Tuần 2      Tiền bảo lưu, deadline hủy chỗ, mở khóa booking, % cọc;
              Non-package; báo cáo bán tour lẻ / nhắc thu tiền / hủy chỗ
              của sale trên VTOS

  Tuần 3      CRM nhẹ + khuyến mãi gắn mã KM; Zalo thông báo qua n8n; rà
              lại phân quyền theo nghiệp vụ

  Song song   Từ tháng 10: Điều hành mở tour trên VTOS trước, Vietrip chỉ
              đọc; Kế toán xác nhận thu/chi trên VTOS (SePay đã nối); cắt
              chuyển khi khớp 1 kỳ lương + 1 kỳ BCTC
  -----------------------------------------------------------------------

Nguyên tắc: giữ nguyên thói quen thao tác của Điều hành/Kinh doanh (mã
tour, bảng quyết toán theo NCC, quy trình có lịch sử) và bọc thêm kiểm
soát của bộ chính sách 01/9/2026; mọi dữ liệu Vietrip tiếp tục đồng bộ
hằng ngày cho tới ngày cắt chuyển nên không mất số liệu; phân quyền VTOS
ánh xạ từ (phòng ban, chức vụ, nơi làm việc) của Vietrip theo bảng
CNTT + HCNS chốt.

Anh duyệt thứ tự ưu tiên ở mục 5--6, em bắt đầu ngay từ mục P1 (sản phẩm
tour, chi tiết tour theo tab, quy trình có lịch sử, robot đồng bộ, sửa
dashboard).
