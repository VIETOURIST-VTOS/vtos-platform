+-------------------------------+--------------------------------------+
| **CÔNG TY CP DU LỊCH          | **CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT     |
| VIETOURIST**                  | NAM**                                |
|                               |                                      |
| VIETOURIST HOLDINGS           | **Độc lập -- Tự do -- Hạnh phúc**    |
|                               |                                      |
| ------------------------      | ------------------------             |
+-------------------------------+--------------------------------------+

**BIÊN BẢN NGHIỆM THU**

**HỆ THỐNG QUẢN TRỊ NỘI BỘ VTOS (VIETOURIST OPERATING SYSTEM)**

*Giai đoạn 1--3 và đồng bộ dữ liệu Vietrip tháng 6--9/2026*

Số: ....../BB-VTOS TP. Hồ Chí Minh, ngày 05 tháng 9 năm 2026

Căn cứ *Thiết kế hệ thống VTOS v1.7* và bộ chính sách quản trị hiệu lực
từ 01/9/2026 (ký ngày 27/8/2026); căn cứ kết quả triển khai trên môi
trường web thật (https://vtos.infinitytours.org) đến ngày 05/9/2026, hôm
nay các bên tiến hành nghiệm thu như sau:

**I. THÀNH PHẦN**

-   Bên giao (Bên B): Chuyên viên Hệ thống AI -- bộ phận CNTT (Claude,
    vận hành theo yêu cầu của anh Trần Tuấn).

-   Bên nhận (Bên A): Công ty CP Du lịch Vietourist -- đại diện: ông
    Trần Tuấn (chủ trì chuyển đổi số); thành phần tham dự: Kế toán,
    Trưởng phòng Điều hành, Giám đốc Kinh doanh, Nhân sự Hành chính, Ban
    Kiểm soát.

**II. NỘI DUNG NGHIỆM THU**

**1. Hạng mục phần mềm**

  -----------------------------------------------------------------------------------
  **TT**   **Hạng mục**   **Nội dung đã hoàn thành**              **Kết luận**
  -------- -------------- --------------------------------------- -------------------
  1        Nền tảng & hạ  Monorepo GitHub (backend FastAPI +      Đạt
           tầng           PostgreSQL/Alembic, web Next.js 14 PWA, 
                          mobile Capacitor, CI); web              
                          https://vtos.infinitytours.org          
                          (Vercel), API Render (Singapore); đăng  
                          nhập JWT, phân quyền 14 vai trò; nhật   
                          ký bất biến hash-chain                  

  2        Lõi vận hành   Tour & dự toán 3 con số, cổng biên      Đạt
           (GĐ1)          10% + 2 chữ ký, giải trình, mã KM       
                          chặn--treo; yêu cầu → booking một cửa   
                          Điều hành (SLA 2 giờ, 4 trường bắt      
                          buộc); quyết toán 7/3 ngày; Kế toán xác 
                          nhận, CNTT khóa; D-7; tham số chính     
                          sách 2 chữ ký hiệu lực theo ngày; cảnh  
                          báo                                     

  3        Thu tiền --    Webhook SePay; khớp tuyệt đối mã        Đạt -- chờ anh dán
           SePay (R1,     booking + số tiền → phiếu thu tự động;  khóa webhook vào
           GĐ2.1)         lệch → hàng chờ Kế toán; tiền mặt; công my.sepay.vn
                          nợ theo booking                         

  4        Kế toán TT99 + Hệ thống TK rút gọn; bút toán tự động   Đạt -- adapter HĐĐT
           HĐĐT (R2,      (thu 111/112--131; hóa đơn              nội bộ, chưa nối
           GĐ2.2)         131--511/3331; quyết toán 154--331/335, nhà cung cấp HĐĐT
                          632--154; đề nghị chi 154/641/642--331; 
                          lương 642--334, 3335); chứng từ bất     
                          biến + đảo; sổ cái, cân đối phát sinh;  
                          hóa đơn GTGT từ booking (adapter, VAT   
                          tham số); khóa kỳ                       

  5        Nhân sự --     Hồ sơ nhân sự; bảng lương tháng theo    Đạt -- ngưỡng f
           Lương (R6,     mục 6.4: thang giảm KD Lẻ, thang        Bảng B.1 và đơn giá
           GĐ2.3)         f0--f19, hoa hồng đoàn & thang đoàn,    HDV tạm, chờ anh
                          quỹ Điều hành 70/30, quỹ visa, HDV CTV  nạp chính thức
                          (cổng 13, TNCN 10%), tài xế theo lệnh   
                          điều xe, sự vụ; luồng KT → HCNS → TGĐ   
                          ký lô → bút toán; bảng giá xe theo      
                          tuyến (6/5/2026)                        

  6        Báo cáo ngày,  Báo cáo ngày Điều 12 (trước 20h, robot  Đạt
           ca trực, chi   chấm nháp, TP chấm, xếp loại A/B/C/D);  
           tiền (R3,      ca trực page (cổng 11); đề nghị chi --  
           GĐ2.4)         lệnh chi (cổng 14 mã tour, cổng 15      
                          ngoài dự toán/MKT ≥ 5 triệu → 2 chữ     
                          ký), SePay tiền ra; dòng tiền tour      

  7        BCTC & thuế    B01/B02/B03 rút gọn theo TK cấp 1, kết  Đạt -- mẫu rút gọn,
           (R5/R7, GĐ3a)  chuyển 911 nháp; tờ khai 01/GTGT,       KTT đối chiếu mẫu
                          05/KK-TNCN xuất XML nạp HTKK/eTax       đầy đủ trước khi
                                                                  phát hành

  8        Tài chính --   Hợp đồng vay (lịch gốc/lãi), đầu tư --  Đạt
           ngân quỹ       hợp tác -- ký quỹ -- cọc (bắt buộc NQ   
           (GĐ3b)         HĐQT, cờ GDLK); thực hiện lịch → bút    
                          toán; dự báo dòng tiền 13 tuần (ngưỡng  
                          500 triệu); báo cáo tài chính tuần      

  9        Dashboard &    Bảng điều khiển theo vai trò: "việc chờ Đạt -- chưa đặt
           robot báo cáo  tôi xử lý", KPI HĐQT/BĐH, khối theo     ANTHROPIC_API_KEY
           (R7, GĐ3c)     phòng; robot báo cáo ngày/tuần/tháng có và lịch n8n
                          nhận xét (Claude API khi cấu hình); API 
                          cho n8n gửi Zalo/Email                  

  10       Đồng bộ        Phân tích cấu trúc Vietrip; bổ sung     Đạt -- 205 phiếu
           Vietrip → VTOS trường tour/booking, dòng chi phí tour, thu chờ booking, tự
           (R8)           bảng trung gian; API nạp/ánh xạ         khớp ở lần đồng bộ
                          idempotent; trang Đồng bộ Vietrip; kịch sau
                          bản chạy trong trình duyệt đã đăng nhập 
                          (không lưu mật khẩu). Đã nạp dữ liệu    
                          6--9/2026 (bảng 2)                      
  -----------------------------------------------------------------------------------

Kiểm thử tự động: 40 kịch bản (backend/tests, chạy độc lập từng phân hệ)
-- toàn bộ đạt tại thời điểm nghiệm thu. Mã nguồn: kho riêng
infinispathway-admin/vtos-platform, 21 lần cập nhật, phiên bản cuối
e6a6ab3 ngày 05/9/2026.

**2. Dữ liệu Vietrip đã nạp vào VTOS (tháng 6--9/2026)**

  ------------------------------------------------------------------------
  **Đối tượng**   **Số lượng**              **Ghi chú**
  --------------- ------------------------- ------------------------------
  Người dùng / xe 154 / 10                  Tài khoản tạo mật khẩu ngẫu
                                            nhiên, HCNS cấp lại; tài xế
                                            gắn xe

  Tour            1.244 (T6: 311, T7: 292,  Trạng thái theo ngày kết thúc;
                  T8: 223, T9: 180; 238     10 tour tạm tạo từ mã (tour đã
                  tour sau 30/9)            gộp/hủy trên Vietrip)

  Booking (đặt    10.295                    Booking hủy ghi 0 đồng;
  1/6--5/9)                                 booking của tour hủy bỏ qua
                                            (235)

  Quyết toán chi  837 tour -- 6.439 dòng    Tổng thu ≈ 74,1 tỷ; dòng chi
  tiết tour       chi phí                   phí giữ NCC (MST), đơn giá,
                                            SL, hệ số, thực chi, đã trả

  Phiếu thu/chi   5.946 (5.776 thu đã xác   T6 21,5 · T7 25,4 · T8 20,9 ·
  khách           nhận ≈ 69,5 tỷ; 162 chi   T9 1,7 tỷ; 205 phiếu chờ
                  hoàn khách)               booking

  Lệnh chi NCC    4.807 (4.508 đã chi ≈     Từ 24/6 (Vietrip chỉ trả
                  31,9 tỷ)                  \~6.000 lệnh gần nhất)
  ------------------------------------------------------------------------

Dữ liệu nhập giữ mã Vietrip để tra ngược (VT\<id\>, VTPT\<id\>,
VTPC\<id\>, VTDC\<id\>), không sinh bút toán kế toán; số dư đầu kỳ sẽ
nhập từ MISA khi cắt chuyển. Kịch bản đồng bộ chạy lại nhiều lần không
nhân bản dữ liệu.

**3. Tồn tại và việc phải làm tiếp**

  -----------------------------------------------------------------------------
  **TT**   **Tồn tại**                     **Xử lý / người thực     **Thời
                                           hiện**                   hạn**
  -------- ------------------------------- ------------------------ -----------
  1        Ngưỡng thang f (Bảng B.1), đơn  Anh Tuấn nạp qua Tham số Trước kỳ
           giá HDV 23 tuyến, bảng phân mức chính sách (2 chữ ký)    lương
           sự vụ đang dùng giá trị tạm                              9/2026

  2        Khóa webhook SePay chưa dán vào Anh Tuấn / CNTT          Tuần 2
           my.sepay.vn; ANTHROPIC_API_KEY,                          tháng 9
           lịch n8n chưa cấu hình                                   

  3        Adapter HĐĐT nội bộ -- chưa nối CNTT + Kế toán (chọn NCC Q4/2026
           nhà cung cấp HĐĐT; BCTC mẫu rút HĐĐT; KTT đối chiếu mẫu  
           gọn                             đầy đủ TT99)             

  4        Số dư đầu kỳ (MISA) chưa nhập;  Kế toán cung cấp bảng    Trước cắt
           dữ liệu Vietrip nhập không sinh cân đối 31/8; CNTT xây   chuyển
           bút toán                        công cụ nhập             

  5        205 phiếu thu Vietrip chưa khớp Chạy lại kịch bản đồng   Liên tục
           booking; lệnh chi NCC tháng 6   bộ hằng ngày; Kế toán    
           chỉ từ 24/6                     đối chiếu                

  6        Chạy song song với MISA/Vietrip HĐQT quyết định; CNTT    Q4/2026
           một quý; hạ tầng miễn phí       triển khai               
           (Render ngủ khi rảnh) -- cần                             
           VPS/DB trả phí khi chạy thật                             
  -----------------------------------------------------------------------------

**III. KẾT LUẬN**

Bên A nghiệm thu các hạng mục 1--10 nêu tại mục II.1 để đưa vào chạy
song song với MISA/Vietrip từ tháng 9/2026; các tồn tại tại mục II.3
được theo dõi và đóng theo thời hạn. Biên bản lập thành 02 bản, mỗi bên
giữ 01 bản, có giá trị như nhau.

+-----------------------------------+-----------------------------------+
| **ĐẠI DIỆN BÊN A**                | **ĐẠI DIỆN BÊN B**                |
|                                   |                                   |
| *(Ký, ghi rõ họ tên)*             | *(Ký, ghi rõ họ tên)*             |
|                                   |                                   |
| Trần Tuấn                         | Bộ phận CNTT                      |
+-----------------------------------+-----------------------------------+

**PHỤ LỤC -- HƯỚNG DẪN SỬ DỤNG VTOS THEO VAI TRÒ**

*(kèm Biên bản nghiệm thu ngày 05/9/2026)*

**1. Truy cập và đăng nhập**

-   Địa chỉ: https://vtos.infinitytours.org (dùng được trên điện thoại
    -- thêm vào màn hình chính như ứng dụng).

-   Tài khoản: theo bảng dưới; mật khẩu lần đầu do HCNS/CNTT cấp, đổi
    ngay sau khi đăng nhập. Tài khoản mẫu khi chạy thử dùng mật khẩu
    123456 -- phải đổi trước khi chạy thật.

-   Mọi thao tác đều ghi nhật ký bất biến (tab Nhật ký) -- không sửa/xóa
    được; sai thì lập chứng từ đảo hoặc giải trình.

**2. Nguyên tắc chung (theo bộ chính sách 01/9/2026)**

-   Hai chữ ký Chủ tịch + TGĐ cho: tham số chính sách, bảng giá xe, dự
    toán ngoài cổng biên 10%, đề nghị chi ngoài dự toán hoặc Marketing ≥
    5 triệu, hợp đồng tài chính.

-   Dự toán tour có 3 con số (doanh thu -- chi phí -- biên); biên \< 10%
    bị chặn, mã khuyến mãi làm biên \< 10% treo chờ TGĐ.

-   Điều hành là nơi duy nhất tạo booking (trong 2 giờ, 4 trường bắt
    buộc); mốc D-7 thu đủ tiền; quyết toán đoàn 7 ngày, lẻ 3 ngày; Kế
    toán xác nhận → CNTT khóa.

-   Báo cáo ngày trước 20h thay chấm công; thưởng tính theo tháng quyết
    toán, trên số liệu Kế toán xác nhận.

**3. Hướng dẫn theo vai trò**

  ----------------------------------------------------------------------------
  **Vai trò**  **Tài khoản** **Việc làm trên VTOS**             **Tab sử
                                                                dụng**
  ------------ ------------- ---------------------------------- --------------
  Chủ tịch     chutich       Ký tham số chính sách, bảng giá    Bảng điều
  HĐQT                       xe, đề nghị chi 2 chữ ký, dự toán  khiển · Tham
                             ngoài cổng; xem KPI HĐQT, dự báo   số chính sách
                             13 tuần, danh mục đầu tư           · Chi tiền ·
                                                                Tài chính ·
                                                                Robot báo cáo

  Tổng giám    tgd           Ký chữ ký thứ 2; duyệt đề nghị     Bảng điều
  đốc                        chi, mã KM khi biên \< 10%; ký lô  khiển · Chi
                             bảng lương; duyệt hợp đồng tài     tiền · Nhân sự
                             chính                              -- Lương · Tài
                                                                chính · Tour

  Phó TGĐ tour ptgd.doan /   Duyệt dự toán đoàn biên ≥ 10%;     Tour & dự toán
  đoàn /       ptgd.mkt      duyệt chi Marketing \< 5 triệu;    · Chi tiền ·
  Marketing                  theo dõi KPI phòng                 Bảng điều
                                                                khiển

  Trưởng phòng tp.dieuhanh   Duyệt dự toán tour lẻ trong cổng;  Tour & dự toán
  Điều hành                  phân điều hành; chấm báo cáo ngày; · Yêu cầu &
                             theo dõi quá hạn quyết toán,       booking · Báo
                             chuyến 21 ngày tới                 cáo ngày

  Nhân viên    dh.\*         Lập tour & dự toán 3 con số; nhận  Tour & dự toán
  Điều hành                  yêu cầu, tạo booking trong 2 giờ   · Yêu cầu &
                             (4 trường bắt buộc); lệnh điều xe; booking · Chi
                             quyết toán tour trong 7/3 ngày; đề tiền · Báo cáo
                             nghị chi NCC                       ngày

  Kinh doanh   kd.\*         Gửi yêu cầu booking, theo dõi D-7, Yêu cầu &
  (Lẻ / Đoàn)                thu tiền khách (SePay/tiền mặt),   booking · Thu
                             báo cáo ngày trước 20h, ca trực    tiền · Báo cáo
                             page; xem thang lương/hoa hồng của ngày · Nhân sự
                             mình                               -- Lương (bản
                                                                thân)

  Giám đốc     gd.kd         Duyệt yêu cầu, xếp ca trực, chấm   Bảng điều
  Kinh doanh                 báo cáo ngày, theo dõi chỉ tiêu    khiển · Yêu
                             theo mốc, thưởng theo tháng quyết  cầu & booking
                             toán                               · Báo cáo ngày

  Kế toán      ketoan        Xác nhận phiếu thu lệch, xác nhận  Thu tiền · Chi
                             quyết toán tour, ghi sổ chứng từ   tiền · Kế toán
                             nháp, phát hành HĐĐT, khóa kỳ,     · Tài chính ·
                             BCTC & tờ khai, lệnh chi & SePay   Nhân sự --
                             tiền ra, cơ sở lương gửi HCNS, hợp Lương · Đồng
                             đồng tài chính, dự báo 13 tuần;    bộ Vietrip
                             chạy đồng bộ Vietrip               

  Nhân sự Hành hcns          Hồ sơ nhân sự, hợp đồng, visa; lập Nhân sự --
  chính                      bảng lương từ cơ sở Kế toán xác    Lương · Báo
                             nhận; sự vụ; tỷ lệ báo cáo ngày;   cáo ngày
                             đội xe & tài xế                    

  CNTT         cntt          Quản trị tài khoản, tham số kỹ     Đồng bộ
                             thuật, khóa tour sau KT xác nhận,  Vietrip · Nhật
                             đồng bộ Vietrip, robot & n8n, sao  ký · Tham số ·
                             lưu, xử lý sự cố; không được sửa   Robot báo cáo
                             số liệu nghiệp vụ                  

  Ban Kiểm     bks           Chỉ đọc toàn bộ: nhật ký           Nhật ký · Kế
  soát                       hash-chain, chứng từ, quyết toán,  toán · Đồng bộ
                             bảng lương, đối chiếu Vietrip      Vietrip · Bảng
                                                                điều khiển
  ----------------------------------------------------------------------------

**4. Quy trình thao tác chính**

**4.1 Tour & dự toán → booking → thu tiền**

-   Điều hành: Tour & dự toán › Tạo tour › nhập dự toán (doanh thu, chi
    phí, biên) › Gửi duyệt. Biên ≥ 10%: TP Điều hành duyệt; \< 10%: Chủ
    tịch + TGĐ ký kèm giải trình.

-   Kinh doanh: Yêu cầu & booking › Gửi yêu cầu (tour, khách, SĐT, số
    khách, giá). Điều hành tạo booking trong 2 giờ; khách chuyển khoản
    ghi mã booking → SePay tự lập phiếu thu; tiền mặt: Thu tiền › Lập
    phiếu tiền mặt.

-   Kế toán: Thu tiền › Hàng chờ -- xác nhận các giao dịch lệch mã/số
    tiền; công nợ D-7 hiện ở Cảnh báo.

**4.2 Chi tiền -- quyết toán -- kế toán**

-   Bộ phận: Chi tiền › Đề nghị chi (bắt buộc mã tour, NCC, số tiền, hóa
    đơn) › Kế toán kiểm › TGĐ duyệt (2 chữ ký nếu ngoài dự toán / MKT ≥
    5 triệu) › Kế toán chi (chuyển khoản SePay hoặc tiền mặt).

-   Điều hành: Tour › Quyết toán trong 7/3 ngày sau kết thúc -- nhập
    thực thu/thực chi theo dòng chi phí (mẫu Vietrip). Kế toán › Xác
    nhận → hệ thống ghi 154/335, 632 → CNTT khóa tour.

-   Kế toán: Kế toán › Chứng từ nháp -- ghi sổ; Hóa đơn -- phát hành
    GTGT từ booking; Khóa kỳ cuối tháng; BCTC / Tờ khai thuế -- xuất XML
    nạp HTKK.

**4.3 Nhân sự -- lương -- báo cáo ngày**

-   Nhân viên: Báo cáo ngày trước 20h (4 phần); trang ca trực theo lịch.
    Trưởng phòng chấm; robot xếp loại A/B/C/D.

-   Kế toán xác nhận cơ sở lương (doanh thu quyết toán, hoa hồng) › HCNS
    lập bảng lương (Nhân sự -- Lương › Tính nháp › Kiểm tra) › TGĐ ký lô
    › hệ thống ghi bút toán lương.

**4.4 Tài chính và báo cáo lãnh đạo**

-   Kế toán: Tài chính › Hợp đồng (vay/đầu tư/ký quỹ) -- đính kèm NQ
    HĐQT; Thực hiện lịch khi ngân hàng báo có; Dự báo 13 tuần xem hằng
    tuần.

-   Lãnh đạo: Bảng điều khiển -- "việc chờ tôi xử lý" và KPI; Robot báo
    cáo -- báo cáo ngày/tuần/tháng có nhận xét (tự gửi Zalo/Email khi
    n8n bật).

**4.5 Đồng bộ Vietrip (giai đoạn chạy song song)**

-   Kế toán/CNTT: đăng nhập Vietrip trên Chrome › mở Console (F12) › dán
    kịch bản docs/vietrip-sync.js › chạy với khoảng ngày cần lấy. Kịch
    bản chỉ dùng phiên đăng nhập của người chạy, không lưu mật khẩu;
    chạy lại không nhân bản.

-   Trang Đồng bộ Vietrip: xem số lượng đã nạp/ánh xạ theo loại; bản ghi
    "chưa có booking/tour" tự khớp ở lần sau; CNTT gỡ bản ghi nhầm bằng
    API xóa (ghi nhật ký).

**5. Hỗ trợ**

-   Sự cố đăng nhập, phân quyền, dữ liệu Vietrip: CNTT (tài khoản cntt).
    Nghiệp vụ kế toán -- lương: Kế toán / HCNS. Thay đổi chính sách:
    Tham số chính sách (Chủ tịch + TGĐ ký).
