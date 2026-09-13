/** CÂY CHỨC NĂNG của tám phân hệ – dựng từ bản vẽ "VTOS · Cấu trúc phân hệ đề xuất V1.3"
 *  (12/9/2026). Bấm vào một thanh phân hệ trên menu dọc thì mở trang /phan-he/<khoa> vẽ đúng cây
 *  này, mỗi mục ghi rõ ĐÃ CÓ TRANG hay CHƯA DỰNG.
 *
 *  VÌ SAO KHÔNG NHỒI CÂY NÀY VÀO MENU DỌC: v1.3 liệt kê 184 mục, VTOS thật có 62 trang. Menu chốt
 *  tối đa hai cấp (§I.2) còn v1.3 sâu bốn cấp, và hơn một trăm mục chưa có trang – đưa lên menu là
 *  link hỏng, ẩn đi thì không ai thấy còn nợ gì. Trang phân hệ giải cả hai: menu chỉ giữ mục đã
 *  dựng, còn phần còn nợ nằm ở đây, đọc được, không nói dối.
 *
 *  BA CỜ trên một mục:
 *    tab    – v1.3 ghi "Tab / nhánh chi tiết": đây là tab BÊN TRONG một trang, không phải trang
 *             riêng. Không bao giờ trở thành mục menu.
 *    them   – màn hình CÓ THẬT trong VTOS mà v1.3 không liệt kê. Thêm vào để không mất lối vào.
 *    chuyen – mục MANG MÃ của một phân hệ khác trong v1.3. Hiện chỉ có nhóm Chăm sóc & khiếu nại:
 *             v1.3 đánh mã 3.5 (Kinh doanh), nhưng anh Tuấn chốt 12/9 và xác nhận lại 13/9/2026 là
 *             nó THUỘC VỀ Marketing & PR. Giữ nguyên mã 3.5 để còn dò ngược được sang bản vẽ; cờ
 *             này chỉ để trang ghi chú lại chuyện ấy, không phải để hỏi lại.
 *
 *  Mục KHÔNG có `href` là mục CHƯA DỰNG. Đó là dữ kiện, không phải thiếu sót của tệp này – đừng
 *  đắp một đường dẫn gần đúng vào cho đủ, vì như thế người dùng bấm vào sẽ ra một màn hình khác
 *  với cái họ đang tìm.
 */
export type MucCay = {
  ma: string; ten: string; href?: string; tab?: boolean; them?: boolean; chuyen?: boolean;
  con?: MucCay[];
};
export type PhanHeCay = { khoa: string; ma: string; ten: string; tom_tat: string; con: MucCay[] };

export const CAY_PHAN_HE: PhanHeCay[] = [
  { khoa: "tongquan", ma: "01", ten: "Tổng quan",
    tom_tat: "Điểm truy cập chung và công việc theo tài khoản",
    con: [
      { ma: "1.1", ten: "Bảng điều hành", href: "/" },
      { ma: "1.2", ten: "Công việc của tôi", href: "/#viec-cua-toi" },
      { ma: "1.3", ten: "Chờ duyệt", href: "/#cho-toi-duyet" },
      { ma: "1.4", ten: "Thông báo", href: "/alerts" },
      { ma: "1.5", ten: "Trợ lý AI" }
    ] },
  { khoa: "marketing", ma: "02", ten: "Marketing & PR",
    tom_tat: "Ngân sách · Thương hiệu · Nội dung · Khách tiềm năng · Chăm sóc sau bán",
    con: [
      { ma: "2.1", ten: "Ngân sách & chiến dịch",
        con: [
          { ma: "2.1.1", ten: "Kế hoạch, ngân sách & thực chi", href: "/marketing?tab=ngansach" },
          { ma: "2.1.2", ten: "Chiến dịch & quảng cáo", href: "/marketing" }
        ] },
      { ma: "2.2", ten: "Thương hiệu & PR",
        con: [
          { ma: "2.2.1", ten: "Nhận diện & thư viện thương hiệu", href: "/noi-dung" },
          { ma: "2.2.2", ten: "Báo chí, KOL & sự kiện" }
        ] },
      { ma: "2.3", ten: "Nội dung & kênh truyền thông",
        con: [
          { ma: "2.3.1", ten: "Lịch nội dung & duyệt bài", href: "/noi-dung" },
          { ma: "2.3.2", ten: "Website, mạng xã hội & chăm sóc" }
        ] },
      { ma: "2.4", ten: "Khách hàng tiềm năng",
        con: [
          { ma: "2.4.1", ten: "Nguồn khách & chống trùng", href: "/leads?tab=leads" },
          { ma: "2.4.2", ten: "Bàn giao Sales & theo dõi xử lý" }
        ] },
      { ma: "2.5", ten: "Báo cáo hiệu quả",
        con: [
          { ma: "2.5.1", ten: "Lead, tỷ lệ chốt & chi phí/khách", href: "/leads?tab=report" },
          { ma: "2.5.2", ten: "Doanh thu truy vết & hiệu quả kênh" }
        ] },
      { ma: "2.6", ten: "Chuyển đổi & phối hợp Sales",
        con: [
          { ma: "2.6.1", ten: "Chuyển đổi sau 30 / 60 / 90 ngày" },
          { ma: "2.6.2", ten: "Lead tồn đọng & thời hạn xử lý" },
          { ma: "2.6.3", ten: "Lý do mất khách & tái chăm sóc" }
        ] },
      { ma: "2.7", ten: "Đóng góp doanh thu",
        con: [
          { ma: "2.7.1", ten: "Truy vết nguồn đến booking" },
          { ma: "2.7.2", ten: "Hiệu quả khách lẻ & MICE" },
          { ma: "2.7.3", ten: "Doanh thu theo kênh & chiến dịch" }
        ] },
      { ma: "2.8", ten: "Đối soát dữ liệu",
        con: [
          { ma: "2.8.1", ten: "Trùng khách & thiếu nguồn" },
          { ma: "2.8.2", ten: "Đối chiếu lead, booking & chi phí" },
          { ma: "2.8.3", ten: "Chuẩn kỳ báo cáo & lịch sử cập nhật" }
        ] },
      { ma: "3.5", ten: "Chăm sóc khách hàng", chuyen: true,
        con: [
          { ma: "3.5.1", ten: "Chăm sóc sau tour", href: "/cham-soc", chuyen: true },
          { ma: "3.5.2", ten: "Phản hồi & khiếu nại", href: "/khieu-nai", chuyen: true },
          { ma: "3.5.3", ten: "Báo cáo chăm sóc", chuyen: true }
        ] }
    ] },
  { khoa: "khachhang", ma: "03", ten: "Kinh doanh",
    tom_tat: "Bán lẻ · Bán đoàn · Hộp thư và hồ sơ khách",
    con: [
      { ma: "3.1", ten: "Hộp thư", href: "/inbox" },
      { ma: "3.2", ten: "Khách hàng",
        con: [
          { ma: "3.2.1", ten: "Hồ sơ khách hàng", href: "/leads?tab=leads" },
          { ma: "3.2.2", ten: "Khách tiềm năng", href: "/leads?tab=leads" },
          { ma: "3.2.3", ten: "Nguồn khách", href: "/leads?tab=leads" }
        ] },
      { ma: "3.3", ten: "Kinh doanh Lẻ",
        con: [
          { ma: "3.3.1", ten: "Lịch khởi hành", href: "/tours?mang=le" },
          { ma: "3.3.2", ten: "Quản lý booking", href: "/bookings?mang=le",
            con: [
              { ma: "3.3.2.1", ten: "Thông tin đặt chỗ", tab: true },
              { ma: "3.3.2.2", ten: "Danh sách khách", tab: true },
              { ma: "3.3.2.3", ten: "Theo dõi thanh toán", tab: true },
              { ma: "3.3.2.4", ten: "Đổi, hủy & bảo lưu", tab: true }
            ] },
          { ma: "3.3.3", ten: "Yêu cầu đặt dịch vụ", href: "/requests?mang=le" },
          { ma: "3.3.4", ten: "Dịch vụ riêng lẻ", href: "/non-package" },
          { ma: "3.3.5", ten: "Chính sách bán hàng", href: "/bang-gia" },
          { ma: "3.3.6", ten: "Báo cáo kinh doanh", href: "/sales-reports?mang=le" },
          { ma: "3.3.7", ten: "Báo giá lẻ", href: "/bao-gia?mang=kd_le", them: true }
        ] },
      { ma: "3.4", ten: "Kinh doanh Đoàn",
        con: [
          { ma: "3.4.1", ten: "Cơ hội kinh doanh", href: "/requests?mang=doan" },
          { ma: "3.4.2", ten: "Hồ sơ đoàn", href: "/tours?mang=doan",
            con: [
              { ma: "3.4.2.1", ten: "Tổng quan", tab: true },
              { ma: "3.4.2.2", ten: "Chương trình", tab: true },
              { ma: "3.4.2.3", ten: "Dự toán", tab: true },
              { ma: "3.4.2.4", ten: "Báo giá", tab: true },
              { ma: "3.4.2.5", ten: "Hợp đồng", tab: true },
              { ma: "3.4.2.6", ten: "Danh sách khách", tab: true },
              { ma: "3.4.2.7", ten: "Thanh toán", tab: true },
              { ma: "3.4.2.8", ten: "Điều hành", tab: true },
              { ma: "3.4.2.9", ten: "Tài liệu & lịch sử", tab: true }
            ] },
          { ma: "3.4.3", ten: "Báo giá", href: "/bao-gia?mang=kd_doan" },
          { ma: "3.4.4", ten: "Hợp đồng", href: "/hop-dong-khach" },
          { ma: "3.4.5", ten: "Yêu cầu điều hành", href: "/requests?mang=doan" },
          { ma: "3.4.6", ten: "Báo cáo kinh doanh", href: "/sales-reports?mang=doan" },
          { ma: "3.4.7", ten: "Booking & bảo lưu đoàn", href: "/bookings?mang=doan", them: true }
        ] },
      { ma: "3.5", ten: "Chăm sóc khách hàng",
        con: [
          { ma: "3.5.1", ten: "Chăm sóc sau tour", href: "/cham-soc" },
          { ma: "3.5.2", ten: "Phản hồi & khiếu nại", href: "/khieu-nai" },
          { ma: "3.5.3", ten: "Báo cáo chăm sóc" }
        ] }
    ] },
  { khoa: "vanhanh", ma: "04", ten: "Điều hành",
    tom_tat: "Sản phẩm · Chuyến · Dịch vụ · Đội xe và Hướng dẫn viên là hai nhóm độc lập",
    con: [
      { ma: "4.1", ten: "Tổng quan điều hành", href: "/bao-cao" },
      { ma: "4.2", ten: "Danh mục tour", href: "/products" },
      { ma: "4.3", ten: "Yêu cầu điều hành", href: "/requests" },
      { ma: "4.4", ten: "Điều hành tour", href: "/tours",
        con: [
          { ma: "4.4.1", ten: "Tổng quan chuyến" },
          { ma: "4.4.2", ten: "Chương trình" },
          { ma: "4.4.3", ten: "Danh sách khách" },
          { ma: "4.4.4", ten: "Dịch vụ" },
          { ma: "4.4.5", ten: "Nhân sự" },
          { ma: "4.4.6", ten: "Dự toán" },
          { ma: "4.4.7", ten: "Phát sinh" },
          { ma: "4.4.8", ten: "Quyết toán" },
          { ma: "4.4.9", ten: "Tài liệu & lịch sử" }
        ] },
      { ma: "4.5", ten: "Quyết toán tour", href: "/tours" },
      { ma: "4.6", ten: "Sự cố & phát sinh", href: "/su-co-tour" },
      { ma: "4.7", ten: "Hiệu quả tour", href: "/lai-lo-tour" },
      { ma: "4.8", ten: "Dịch vụ",
        con: [
          { ma: "4.8.1", ten: "Nhà cung cấp", href: "/nha-cung-cap" },
          { ma: "4.8.2", ten: "Đặt dịch vụ", href: "/nha-cung-cap" },
          { ma: "4.8.3", ten: "Hồ sơ visa", href: "/visa" }
        ] },
      { ma: "4.9", ten: "Quản lý đội xe",
        con: [
          { ma: "4.9.1", ten: "Tổng quan đội xe" },
          { ma: "4.9.2", ten: "Hồ sơ xe", href: "/doi-xe" },
          { ma: "4.9.3", ten: "Tài xế", href: "/xe-hdv" },
          { ma: "4.9.4", ten: "Bảng giá vận tải", href: "/ops?tab=fleet" },
          { ma: "4.9.5", ten: "Lịch & lệnh điều xe", href: "/lenh-dieu-xe" },
          { ma: "4.9.6", ten: "Bảo dưỡng & sửa chữa" },
          { ma: "4.9.7", ten: "Quyết toán chuyến xe" },
          { ma: "4.9.8", ten: "Hiệu quả khai thác", href: "/hieu-qua-doi-xe" },
          { ma: "4.9.9", ten: "Lãi lỗ đội xe", href: "/lai-lo-doi-xe", them: true }
        ] },
      { ma: "4.10", ten: "Hướng dẫn viên",
        con: [
          { ma: "4.10.1", ten: "Tổng quan hướng dẫn", href: "/huong-dan" },
          { ma: "4.10.2", ten: "Hồ sơ hướng dẫn viên", href: "/huong-dan" },
          { ma: "4.10.3", ten: "Lịch & bố trí hướng dẫn", href: "/ops?tab=guides" },
          { ma: "4.10.4", ten: "Báo cáo sau tour" },
          { ma: "4.10.5", ten: "Đối soát thù lao" },
          { ma: "4.10.6", ten: "Việc của tài xế & hướng dẫn viên", href: "/xe-hdv", them: true }
        ] }
    ] },
  { khoa: "nhansu", ma: "05", ten: "Nhân sự – Hành chính",
    tom_tat: "Con người · Thu nhập · Hành chính · Tài sản",
    con: [
      { ma: "5.1", ten: "Tổng quan nhân sự" },
      { ma: "5.2", ten: "Hồ sơ nhân sự", href: "/hr?tab=employees" },
      { ma: "5.3", ten: "Hợp đồng nhân sự", href: "/hop-dong-lao-dong" },
      { ma: "5.4", ten: "Chấm công & nghỉ phép" },
      { ma: "5.5", ten: "Lương & thu nhập", href: "/hr?tab=payroll" },
      { ma: "5.6", ten: "Đánh giá nhân sự", href: "/hr?tab=incidents" },
      { ma: "5.7", ten: "Hồ sơ sự vụ", href: "/hr?tab=incidents" },
      { ma: "5.8", ten: "Báo cáo nhân sự", href: "/reports" },
      { ma: "5.9", ten: "Hành chính",
        con: [
          { ma: "5.9.1", ten: "Văn bản & quy trình", href: "/params" },
          { ma: "5.9.2", ten: "Mua sắm", href: "/tai-san" },
          { ma: "5.9.3", ten: "Tài sản & cấp phát", href: "/tai-san" }
        ] }
    ] },
  { khoa: "taichinh", ma: "06", ten: "Tài chính – Kế toán",
    tom_tat: "Thu–chi · Ngân quỹ · Kế toán · Hợp nhất",
    con: [
      { ma: "6.1", ten: "Tổng quan tài chính" },
      { ma: "6.2", ten: "Thu – Chi & Công nợ",
        con: [
          { ma: "6.2.1", ten: "Thu tiền", href: "/collections" },
          { ma: "6.2.2", ten: "Đề nghị thanh toán", href: "/expenses" },
          { ma: "6.2.3", ten: "Công nợ", href: "/cong-no",
            con: [
              { ma: "6.2.3.1", ten: "Phải thu khách hàng", tab: true },
              { ma: "6.2.3.2", ten: "Phải trả nhà cung cấp", tab: true },
              { ma: "6.2.3.3", ten: "Phải thu, phải trả khác", tab: true },
              { ma: "6.2.3.4", ten: "Đối chiếu công nợ", tab: true }
            ] },
          { ma: "6.2.4", ten: "Tạm ứng & quyết toán" },
          { ma: "6.2.5", ten: "Bảo lưu & hoàn tiền", href: "/bookings",
            con: [
              { ma: "6.2.5.1", ten: "Số dư bảo lưu", tab: true },
              { ma: "6.2.5.2", ten: "Yêu cầu hoàn tiền", tab: true },
              { ma: "6.2.5.3", ten: "Lịch sử sử dụng", tab: true }
            ] }
        ] },
      { ma: "6.3", ten: "Ngân quỹ",
        con: [
          { ma: "6.3.1", ten: "Quỹ & ngân hàng", href: "/bank-accounts" },
          { ma: "6.3.2", ten: "Đối soát ngân hàng" },
          { ma: "6.3.3", ten: "Dòng tiền", href: "/dong-tien",
            con: [
              { ma: "6.3.3.1", ten: "Thực tế", tab: true },
              { ma: "6.3.3.2", ten: "Dự báo", tab: true },
              { ma: "6.3.3.3", ten: "Mốc tổng hợp", tab: true },
              { ma: "6.3.3.4", ten: "Kịch bản", tab: true }
            ] },
          { ma: "6.3.4", ten: "Vay & đầu tư", href: "/finance?tab=contracts" }
        ] },
      { ma: "6.4", ten: "Kế toán",
        con: [
          { ma: "6.4.1", ten: "Chứng từ kế toán", href: "/doc-chung-tu" },
          { ma: "6.4.2", ten: "Sổ kế toán", href: "/accounting?tab=journal" },
          { ma: "6.4.3", ten: "Hóa đơn", href: "/accounting?tab=invoices" },
          { ma: "6.4.4", ten: "Thuế", href: "/accounting?tab=invoices" },
          { ma: "6.4.5", ten: "Tài sản & phân bổ", href: "/tai-san" },
          { ma: "6.4.6", ten: "Kết sổ & khóa kỳ", href: "/ket-so" },
          { ma: "6.4.7", ten: "Báo cáo tài chính", href: "/accounting?tab=bctc" },
          { ma: "6.4.8", ten: "Hồ sơ kiểm toán", href: "/ho-so-kiem-toan" },
          { ma: "6.4.9", ten: "Khóa kỳ", href: "/accounting?tab=periods", them: true }
        ] },
      { ma: "6.5", ten: "Thiết lập kế toán",
        con: [
          { ma: "6.5.1", ten: "Quy tắc hạch toán", href: "/hach-toan" },
          { ma: "6.5.2", ten: "Kết nối dữ liệu kế toán", href: "/accounting?tab=misa" }
        ] },
      { ma: "6.6", ten: "Báo cáo hợp nhất Holdings",
        con: [
          { ma: "6.6.1", ten: "Tiếp nhận báo cáo thành viên" },
          { ma: "6.6.2", ten: "Kiểm tra & đối chiếu" },
          { ma: "6.6.3", ten: "Điều chỉnh & loại trừ" },
          { ma: "6.6.4", ten: "Báo cáo tài chính hợp nhất" },
          { ma: "6.6.5", ten: "Phê duyệt & phát hành" }
        ] }
    ] },
  { khoa: "baocao", ma: "07", ten: "Báo cáo – Phân tích",
    tom_tat: "Góc nhìn tổng hợp từ dữ liệu nghiệp vụ dùng chung",
    con: [
      { ma: "7.1", ten: "Tổng quan quản trị", href: "/robot-reports" },
      { ma: "7.2", ten: "Kinh doanh", href: "/sales-reports" },
      { ma: "7.3", ten: "Marketing", href: "/leads?tab=report" },
      { ma: "7.4", ten: "Chăm sóc khách hàng" },
      { ma: "7.5", ten: "Điều hành du lịch", href: "/bao-cao" },
      { ma: "7.6", ten: "Đội xe", href: "/lai-lo-doi-xe" },
      { ma: "7.7", ten: "Nhân sự", href: "/reports" },
      { ma: "7.8", ten: "Tài chính", href: "/accounting?tab=bctc" },
      { ma: "7.9", ten: "Tổng quan hợp nhất Holdings" }
    ] },
  { khoa: "quantri", ma: "08", ten: "Quản trị hệ thống",
    tom_tat: "Tổ chức · Quyền · Kết nối · Tự động hóa · Giám sát",
    con: [
      { ma: "8.1", ten: "Tổ chức & truy cập",
        con: [
          { ma: "8.1.1", ten: "Cơ cấu tổ chức", href: "/companies" },
          { ma: "8.1.2", ten: "Tài khoản", href: "/access" },
          { ma: "8.1.3", ten: "Vai trò & phân quyền", href: "/access" }
        ] },
      { ma: "8.2", ten: "Dữ liệu & kết nối",
        con: [
          { ma: "8.2.1", ten: "Danh mục dùng chung" },
          { ma: "8.2.2", ten: "Kết nối dữ liệu",
            con: [
              { ma: "8.2.2.1", ten: "Vietrip", href: "/vietrip" },
              { ma: "8.2.2.2", ten: "Phần mềm kế toán", href: "/accounting?tab=misa" },
              { ma: "8.2.2.3", ten: "Ngân hàng & SePay", href: "/vietrip" }
            ] },
          { ma: "8.2.3", ten: "Nhập & đối chiếu", href: "/nap-du-lieu" },
          { ma: "8.2.4", ten: "Kho tài liệu", href: "/tep" }
        ] },
      { ma: "8.3", ten: "Quy trình & tự động hóa",
        con: [
          { ma: "8.3.1", ten: "Quy trình phê duyệt" },
          { ma: "8.3.2", ten: "Quy tắc tự động", href: "/tu-dong-hoa" },
          { ma: "8.3.3", ten: "Trợ lý AI", href: "/ai-roles" }
        ] },
      { ma: "8.4", ten: "Giám sát",
        con: [
          { ma: "8.4.1", ten: "Nhật ký hệ thống", href: "/audit" },
          { ma: "8.4.2", ten: "Tình trạng kết nối", href: "/kiem-soat" },
          { ma: "8.4.3", ten: "Cảnh báo nghiệp vụ", href: "/alerts", them: true },
          { ma: "8.4.4", ten: "Ngoại lệ cần xử lý", href: "/ngoai-le", them: true },
          { ma: "8.4.5", ten: "Rà soát cột tiền", href: "/ra-soat-cot-tien", them: true }
        ] }
    ] },
];

export function timPhanHe(khoa: string): PhanHeCay | undefined {
  return CAY_PHAN_HE.find((p) => p.khoa === khoa);
}

/** Một mục CHỈ LÀ NHÃN GOM NHÓM: có mục con nhưng bản thân không dẫn tới màn hình nào. "Quản lý
 *  đội xe" là nhãn như thế – nó không phải một màn hình còn nợ, nên không được ghi "Chưa dựng" và
 *  không được tính vào mẫu số. Ngược lại "Điều hành tour" vừa là màn hình thật vừa có tab bên
 *  trong, nên vẫn tính. */
export const laNhan = (m: MucCay) => !m.href && !m.tab && !!m.con?.length;

/** Đếm mục THỰC SỰ là một màn hình. Bỏ tab (tab không phải trang riêng) và bỏ nhãn gom nhóm – đếm
 *  cả hai thứ ấy thì tỷ lệ "đã dựng / tổng" thấp hơn thực tế và người đọc tưởng còn nợ nhiều hơn. */
export function demMuc(ds: MucCay[]): { tong: number; co: number } {
  let tong = 0, co = 0;
  const di = (l: MucCay[]) => l.forEach((m) => {
    if (!m.tab && !laNhan(m)) { tong++; if (m.href) co++; }
    if (m.con) di(m.con);
  });
  di(ds);
  return { tong, co };
}
