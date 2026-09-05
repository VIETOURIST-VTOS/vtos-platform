const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel, BorderStyle, ShadingType, LevelFormat, Footer, PageNumber } = require("docx");
const F = "Times New Roman";
const T = (t, o = {}) => new TextRun({ text: t, font: F, size: 24, ...o });
const P = (t, o = {}) => new Paragraph({ spacing: { after: 100, line: 300 }, alignment: AlignmentType.JUSTIFIED, ...o, children: typeof t === "string" ? [T(t, o.run || {})] : t });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, children: [new TextRun({ text: t, font: F, size: 28, bold: true, color: "000000" })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 80 }, children: [new TextRun({ text: t, font: F, size: 26, bold: true, color: "000000" })] });
const B = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60, line: 290 }, alignment: AlignmentType.JUSTIFIED, children: typeof t === "string" ? [T(t)] : t });
const C = (t, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [T(t, o)] });
const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" }; const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, opt = {}) {
  const tot = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, head, i) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders, margins: { top: 50, bottom: 50, left: 80, right: 80 }, shading: head ? { type: ShadingType.CLEAR, fill: "D9E2F3", color: "auto" } : undefined,
    children: [new Paragraph({ alignment: head ? AlignmentType.CENTER : ((opt.center || []).includes(i) ? AlignmentType.CENTER : AlignmentType.LEFT), spacing: { after: 0, line: 250 }, children: [T(String(t), { bold: head, size: opt.size || 21 })] })] });
  return new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: widths, rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true, i)) }), ...rows.map(r => new TableRow({ children: r.map((c, i) => cell(c, widths[i], false, i)) }))] });
}
const gap = () => new Paragraph({ spacing: { after: 100 }, children: [] });

const menu = [
  ["Ban Giám Đốc", "Tổng quan · Thông tin Tour · Duyệt chi · Duyệt đề xuất chi · Lịch sử Email", "Chủ tịch/TGĐ/GĐ (chucVu = Giám đốc)", "Duyệt dự toán, duyệt chi NCC, duyệt đề xuất chi"],
  ["Quản lý User", "Danh sách người dùng (chức vụ Admin/Giám đốc/Trưởng phòng/Nhân viên × phòng ban × nơi làm việc)", "IT", "Phân quyền phẳng theo 4 chức vụ, không theo nghiệp vụ"],
  ["Quản Lý Xe", "Danh sách xe (biển số, đời xe, tài xế, tổng km)", "Đội xe", "Chỉ hồ sơ xe – không lệnh điều xe, không giá thuê nội bộ"],
  ["Quản Lý Tour (Kinh doanh)", "Đặt Tour (tìm tour còn chỗ, sơ đồ chỗ ngồi) · Thông tin Booking · Dịch vụ Non-Package · Mở khóa booking", "KD Lẻ, Đoàn (phòng Tour 72 NV, Tour MICE 15)", "Sale tự tạo booking; deadline hủy chỗ; % cọc theo sản phẩm"],
  ["Điều Hành", "Danh sách/Tạo Sản phẩm (tour cha, cơ cấu chi phí 11 khoản) · Đặt Tour · Non-package · Thông tin Booking · Tiền bảo lưu · Thông tin Tour (chi tiết + quyết toán) · Đề xuất chi NCC", "Điều hành (19 NV + 1 TP)", "Trung tâm vận hành: mở tour từ sản phẩm, dự toán → quyết toán, đề xuất chi"],
  ["Kế Toán", "Xác nhận Thu Chi Khách · Xác nhận Thu Chi NCC · Thông tin Booking · Duyệt đề xuất chi", "Kế toán (7 NV, 1 TP, 3 GĐ, 1 Admin)", "Xác nhận phiếu thu/chi theo UNC/biên lai; chi NCC theo lệnh"],
  ["Marketing / CSKH / Khách hàng", "Khuyến mãi · Khách đã đi tour · Chiến dịch · Đề xuất chi MKT · Tương tác KH · Phân loại KH (hành vi, tần suất, độ tuổi) · Hồ sơ KH (lịch sử, chi tiêu, tour yêu thích, dịp đi, người đi cùng) · CSKH (cảm ơn, khảo sát, ưu đãi) · Zalo", "Marketing (3 NV, 2 GĐ), CSKH (3)", "Nhiều màn hình mới, phần lớn đang hoàn thiện"],
  ["Báo cáo", "Tour lẻ (bán tour, ngày, nhắc thu tiền) · Điều hành (bán tour nội địa, chi tiết tour lẻ, hủy chỗ của sale, kinh doanh) · Marketing (chiến dịch, KH, chuyển đổi – đang phát triển)", "Quản lý", "Xuất Excel theo khoảng ngày/mã tour; nhiều báo cáo 'đang phát triển'"],
];
const flow = [
  ["1", "Khởi tạo quy trình xử lý tour", "NV Điều hành", "Mở tour từ sản phẩm (mã SP.NNddmmyy), số chỗ, giá ADL/CHD/INF (+KM)"],
  ["2", "Đề nghị phê duyệt dự toán", "NV Điều hành", "Bảng dự chi theo NCC (loại DV, đơn giá, SL, hệ số) kèm lời giải trình"],
  ["3", "Xác nhận, đề nghị phê duyệt", "Trưởng phòng Điều hành", "Kiểm tra dự toán"],
  ["4", "Phê duyệt dự toán", "Giám đốc", "Không có cổng biên tự động – GĐ tự cân nhắc (ví dụ tour PT001.03060926 biên 5,3% vẫn duyệt)"],
  ["4b", "Xác nhận tạm ứng (nếu có)", "Kế toán", "Workflow tự chuyển nếu không tạm ứng"],
  ["5", "Lập quyết toán tour", "NV Điều hành", "Cập nhật thực chi từng dòng NCC (MST), file chứng từ, đã thanh toán"],
  ["6", "Duyệt chi → Khóa tour (KTQT)", "GĐ · Kế toán", "Nút 'Duyệt chi', 'Quyết toán', 'Khóa Tour (KTQT)' trên trang Chi tiết Tour; chi NCC qua Đề xuất chi → Xác nhận chi NCC"],
];
const thieu_vietrip = [
  ["Trang Chi tiết Tour", "Chưa hoàn thiện: bảng đặt chỗ hiện dữ liệu mẫu (BK-2024001 Nguyễn Văn A), 'Còn trống: NaN', Doanh thu/Chi phí/Lợi nhuận = 0; danh sách tour cũng không có doanh thu – số thật chỉ nằm ở trang Quyết toán"],
  ["Dự toán 3 con số & cổng biên", "Không có: dự toán chỉ là bảng dự chi theo NCC; biên lợi nhuận không chặn, không cần 2 chữ ký, không giải trình bắt buộc"],
  ["Booking", "Chỉ 3 trường (tour, tên, SĐT, số khách); không có nguồn khách, ghi chú chăm sóc; sale tự tạo booking (không qua Điều hành một cửa); không mốc D-7; mã KM tách ở Marketing"],
  ["Phân quyền", "4 chức vụ × 9 phòng ban; không theo nghiệp vụ (ai cũng thấy Thông tin Booking ở 3 menu khác nhau); không nhật ký bất biến"],
  ["Nhân sự – lương – HDV", "Không có: phân công HDV, đơn giá, thang lương, báo cáo ngày, sự vụ; xe chỉ có hồ sơ"],
  ["Kế toán", "Chỉ xác nhận phiếu thu/chi; không sổ sách, không bút toán, không HĐĐT, không BCTC/thuế (đang nằm ở MISA)"],
  ["Báo cáo & API", "Nhiều báo cáo 'đang phát triển'; API nội bộ không có lọc đến-ngày, giới hạn phân trang ~1.100 dòng, không có API mở cho hệ thống khác"],
];
const vtos_thieu = [
  ["Sản phẩm tour (tour cha) + cơ cấu chi phí chuẩn 11 khoản (vé MB, land, LSQ, bảo hiểm, quà tặng, phí TL, họp đoàn, điều hành, dịch thuật, hoa hồng vé, phí CK)", "P1", "Mở tour từ sản phẩm → dự toán 3 con số tự sinh; đồng bộ /operations/products"],
  ["Trang Chi tiết Tour đầy đủ theo tab: thông tin · chỗ & giá · dự toán · booking · thu tiền · chi NCC · quyết toán (dòng NCC MST, file) · lịch sử quy trình", "P1", "VTOS đã có dữ liệu (1.244 tour, dòng chi phí) nhưng màn hình Tour hiện chỉ là danh sách + dự toán"],
  ["Quy trình 6 bước có lịch sử + lời giải trình (như Quy trình & Lịch sử của Vietrip) gắn với cổng biên/2 chữ ký của VTOS", "P1", "Giữ thói quen người dùng, thêm kiểm soát"],
  ["Tiền bảo lưu (booking hủy giữ tiền → dùng cho tour sau / hoàn), deadline hủy chỗ, mở khóa booking, % cọc theo sản phẩm", "P1", "Đang phát sinh hằng ngày ở KD Lẻ"],
  ["Dịch vụ Non-package (vé lẻ, khách sạn, visa lẻ) – bán không theo tour", "P2", "Doanh thu ngoài tour, hiện VTOS không ghi nhận"],
  ["Đồng bộ Vietrip hằng ngày bằng robot (tour, booking, thu chi, quyết toán) + ánh xạ phòng ban/chức vụ → vai trò VTOS", "P1", "Đã có kịch bản; cần lịch chạy tự động và bảng ánh xạ vai trò"],
  ["CRM nhẹ: hồ sơ khách, lịch sử tour, phân loại, chiến dịch/khuyến mãi, cảm ơn sau tour, Zalo", "P2", "Vietrip đang xây; VTOS làm sau khi lõi vận hành ổn"],
  ["Sơ đồ chỗ ngồi, nhiều điểm bán/văn phòng (8 nơi làm việc), lịch sử email/thông báo", "P3", ""],
];
const de_xuat = [
  ["Tuần 1", "Sản phẩm tour + cơ cấu chi phí; Chi tiết Tour theo tab; quy trình 6 bước có lịch sử; robot đồng bộ Vietrip hằng đêm + ánh xạ vai trò; sửa Bảng điều khiển tải chậm (75 giây với 10.000 booking → tính sẵn theo lô)"],
  ["Tuần 2", "Tiền bảo lưu, deadline hủy chỗ, mở khóa booking, % cọc; Non-package; báo cáo bán tour lẻ / nhắc thu tiền / hủy chỗ của sale trên VTOS"],
  ["Tuần 3", "CRM nhẹ + khuyến mãi gắn mã KM; Zalo thông báo qua n8n; rà lại phân quyền theo nghiệp vụ"],
  ["Song song", "Từ tháng 10: Điều hành mở tour trên VTOS trước, Vietrip chỉ đọc; Kế toán xác nhận thu/chi trên VTOS (SePay đã nối); cắt chuyển khi khớp 1 kỳ lương + 1 kỳ BCTC"],
];

const doc = new Document({
  styles: { default: { document: { run: { font: F, size: 24 } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1134, bottom: 1134, left: 1418, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [T("Phân tích cấu trúc Vietrip & đề xuất bổ sung VTOS – 05/9/2026 – Trang ", { size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: F, size: 18 })] })] }) },
    children: [
      C("CÔNG TY CP DU LỊCH VIETOURIST – BỘ PHẬN CNTT", { bold: true, size: 22 }),
      C("PHÂN TÍCH CẤU TRÚC PHẦN MỀM VIETRIP", { bold: true, size: 32 }),
      C("Bố trí phòng ban, luồng quản trị tour và đề xuất bổ sung cho VTOS", { bold: true, size: 26 }),
      C("Khảo sát trực tiếp app.vietrip.com.vn ngày 05/9/2026 (tài khoản Giám đốc) – trình anh Trần Tuấn", { italics: true }),
      gap(),
      H1("1. Tóm tắt"),
      P("Vietrip là phần mềm vận hành tour theo mô hình \"sản phẩm → tour → booking → thu/chi → quyết toán\", tổ chức menu theo phòng ban (Ban Giám đốc, Kinh doanh, Điều hành, Kế toán, Marketing/CSKH, Đội xe, Báo cáo) với 154 người dùng ở 9 phòng ban, 4 chức vụ, 8 nơi làm việc. Điểm mạnh là quy trình tour 6 bước có lịch sử và bảng quyết toán chi phí theo nhà cung cấp (có MST, chứng từ). Điểm yếu là thiếu kiểm soát tự động (không cổng biên, không 2 chữ ký, không nhật ký bất biến), booking thiếu trường, trang chi tiết tour chưa hoàn thiện, không có nhân sự – lương – kế toán, và nhiều màn hình Marketing/Báo cáo đang phát triển. VTOS đã bao phủ toàn bộ phần kiểm soát và hậu cần (kế toán, lương, HDV, xe, SePay, dự báo dòng tiền) nhưng còn thiếu chính phần \"lõi vận hành tour\" mà người dùng đang quen trên Vietrip: sản phẩm tour, trang chi tiết tour theo tab, tiền bảo lưu, non-package, quy trình có lịch sử. Đề xuất bổ sung 3 tuần theo thứ tự ưu tiên ở mục 6."),
      H1("2. Bố trí phòng ban trên Vietrip"),
      table(["Nhóm menu", "Màn hình", "Phòng ban sử dụng", "Nhận xét"], menu, [1500, 3600, 1900, 2600]),
      gap(),
      P("Người dùng (154): Tour 72 NV + 2 TP + 1 GĐ; Tour MICE 15 NV + 1 GĐ; Điều hành 19 NV + 1 TP; Kế toán 7 NV + 1 TP + 3 GĐ + 1 Admin; Hướng dẫn 7; Marketing 3 NV + 2 GĐ; CSKH 3; IT 1 NV + 2 Admin; Giám đốc 2; Kinh doanh 1; Đối tác 1; 9 tài khoản không có phòng ban. Nơi làm việc: TP.HCM, Hà Nội, Hải Phòng, An Giang, Bình Dương, Đà Nẵng, Gia Lai, Phan Thiết – trong đó Hà Nội/Hải Phòng đã đóng theo sơ đồ 01/9/2026 nhưng tài khoản vẫn còn."),
      H1("3. Luồng quản trị tour trên Vietrip (quan sát từ tour PT001.03060926)"),
      table(["Bước", "Việc", "Ai làm", "Ghi nhận"], flow, [600, 2600, 1900, 4500], { center: [0] }),
      gap(),
      P("Dữ liệu đi kèm: Sản phẩm (mã, tên, điểm KH, loại nội địa/quốc tế, vùng, quốc gia, điểm bán, phương tiện, loại xe, độ dài, số ngày, giá tham khảo, % cọc, số ngày đóng tour, cần xác nhận; cơ cấu chi phí 11 khoản) → Tour (mã SP.NN+ddmmyy, ngày KH/KT/đóng, số chỗ thường/KM, giá ADL/CHD/INF thường/KM, trạng thái hoạt động/chờ xác nhận/hủy) → Booking (người book, SĐT, ADL/CHD/INF, tổng tiền, tình trạng UNPAID/DEPO/PAID, deadline hủy chỗ, người tạo, trạng thái OK/hủy) → Phiếu thu/chi khách (hình thức, TK công ty, file UNC, Kế toán xác nhận) → Đề xuất chi NCC (tour, NCC, hình thức TT, loại tiền, dòng dịch vụ) → Xác nhận chi NCC (OrgID, FOP, TK NCC, KC/QQ/XX/GD) → Quyết toán (dòng chi phí theo NCC MST, đơn giá, SL, hệ số, thực chi, đã thanh toán, file) → Tiền bảo lưu (booking gốc, số tiền, tình trạng hoàn)."),
      H1("4. Điểm còn thiếu / rủi ro trên Vietrip"),
      table(["Khu vực", "Quan sát"], thieu_vietrip, [2300, 7300]),
      H1("5. VTOS còn thiếu gì so với Vietrip (cần bổ sung)"),
      table(["Hạng mục", "Ưu tiên", "Lý do"], vtos_thieu, [5400, 900, 3300], { center: [1] }),
      gap(),
      P("Ngược lại, VTOS đã có mà Vietrip không có: dự toán 3 con số + cổng biên 10% + 2 chữ ký + giải trình; booking 4 trường bắt buộc và một cửa Điều hành (SLA 2 giờ); mốc D-7; quyết toán 7/3 ngày; kế toán TT99 (bút toán tự động, sổ, BCTC, thuế); SePay hai chiều; nhân sự – lương – HDV – xe – sự vụ; báo cáo ngày; dự báo dòng tiền 13 tuần; hợp đồng tài chính; dashboard theo vai trò; robot báo cáo; nhật ký bất biến."),
      H1("6. Đề xuất triển khai"),
      table(["Thời gian", "Việc"], de_xuat, [1500, 8100]),
      gap(),
      P("Nguyên tắc: giữ nguyên thói quen thao tác của Điều hành/Kinh doanh (mã tour, bảng quyết toán theo NCC, quy trình có lịch sử) và bọc thêm kiểm soát của bộ chính sách 01/9/2026; mọi dữ liệu Vietrip tiếp tục đồng bộ hằng ngày cho tới ngày cắt chuyển nên không mất số liệu; phân quyền VTOS ánh xạ từ (phòng ban, chức vụ, nơi làm việc) của Vietrip theo bảng CNTT + HCNS chốt."),
      P("Anh duyệt thứ tự ưu tiên ở mục 5–6, em bắt đầu ngay từ mục P1 (sản phẩm tour, chi tiết tour theo tab, quy trình có lịch sử, robot đồng bộ, sửa dashboard)."),
    ] }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2], b); console.log("ok", b.length); });
