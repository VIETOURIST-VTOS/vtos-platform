const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel, BorderStyle, ShadingType, LevelFormat, PageBreak, TabStopType, Footer, PageNumber } = require("docx");

const F = "Times New Roman";
const T = (t, o = {}) => new TextRun({ text: t, font: F, size: 24, ...o });
const P = (t, o = {}) => new Paragraph({ spacing: { after: 100, line: 300 }, alignment: AlignmentType.JUSTIFIED, ...o, children: typeof t === "string" ? [T(t, o.run || {})] : t });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, children: [new TextRun({ text: t, font: F, size: 28, bold: true, color: "000000" })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 80 }, children: [new TextRun({ text: t, font: F, size: 26, bold: true, color: "000000" })] });
const B = (t, lvl = 0) => new Paragraph({ numbering: { reference: "bul", level: lvl }, spacing: { after: 60, line: 290 }, alignment: AlignmentType.JUSTIFIED, children: typeof t === "string" ? [T(t)] : t });
const C = (t, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [T(t, o)] });

const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, opt = {}) {
  const tot = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, head, i) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders, margins: { top: 60, bottom: 60, left: 90, right: 90 },
    shading: head ? { type: ShadingType.CLEAR, fill: "D9E2F3", color: "auto" } : undefined,
    children: [new Paragraph({ alignment: head ? AlignmentType.CENTER : (opt.center && opt.center.includes(i) ? AlignmentType.CENTER : AlignmentType.LEFT), spacing: { after: 0, line: 260 }, children: [T(String(t), { bold: head, size: opt.size || 22 })] })] });
  return new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true, i)) }),
      ...rows.map(r => new TableRow({ children: r.map((c, i) => cell(c, widths[i], false, i)) }))] });
}
const gap = () => new Paragraph({ spacing: { after: 120 }, children: [] });

// ---------- Nội dung ----------
const hang_muc = [
  ["1", "Nền tảng & hạ tầng", "Monorepo GitHub (backend FastAPI + PostgreSQL/Alembic, web Next.js 14 PWA, mobile Capacitor, CI); web https://vtos.infinitytours.org (Vercel), API Render (Singapore); đăng nhập JWT, phân quyền 14 vai trò; nhật ký bất biến hash-chain", "Đạt"],
  ["2", "Lõi vận hành (GĐ1)", "Tour & dự toán 3 con số, cổng biên 10% + 2 chữ ký, giải trình, mã KM chặn–treo; yêu cầu → booking một cửa Điều hành (SLA 2 giờ, 4 trường bắt buộc); quyết toán 7/3 ngày; Kế toán xác nhận, CNTT khóa; D-7; tham số chính sách 2 chữ ký hiệu lực theo ngày; cảnh báo", "Đạt"],
  ["3", "Thu tiền – SePay (R1, GĐ2.1)", "Webhook SePay; khớp tuyệt đối mã booking + số tiền → phiếu thu tự động; lệch → hàng chờ Kế toán; tiền mặt; công nợ theo booking", "Đạt – chờ anh dán khóa webhook vào my.sepay.vn"],
  ["4", "Kế toán TT99 + HĐĐT (R2, GĐ2.2)", "Hệ thống TK rút gọn; bút toán tự động (thu 111/112–131; hóa đơn 131–511/3331; quyết toán 154–331/335, 632–154; đề nghị chi 154/641/642–331; lương 642–334, 3335); chứng từ bất biến + đảo; sổ cái, cân đối phát sinh; hóa đơn GTGT từ booking (adapter, VAT tham số); khóa kỳ", "Đạt – adapter HĐĐT nội bộ, chưa nối nhà cung cấp HĐĐT"],
  ["5", "Nhân sự – Lương (R6, GĐ2.3)", "Hồ sơ nhân sự; bảng lương tháng theo mục 6.4: thang giảm KD Lẻ, thang f0–f19, hoa hồng đoàn & thang đoàn, quỹ Điều hành 70/30, quỹ visa, HDV CTV (cổng 13, TNCN 10%), tài xế theo lệnh điều xe, sự vụ; luồng KT → HCNS → TGĐ ký lô → bút toán; bảng giá xe theo tuyến (6/5/2026)", "Đạt – ngưỡng f Bảng B.1 và đơn giá HDV tạm, chờ anh nạp chính thức"],
  ["6", "Báo cáo ngày, ca trực, chi tiền (R3, GĐ2.4)", "Báo cáo ngày Điều 12 (trước 20h, robot chấm nháp, TP chấm, xếp loại A/B/C/D); ca trực page (cổng 11); đề nghị chi – lệnh chi (cổng 14 mã tour, cổng 15 ngoài dự toán/MKT ≥ 5 triệu → 2 chữ ký), SePay tiền ra; dòng tiền tour", "Đạt"],
  ["7", "BCTC & thuế (R5/R7, GĐ3a)", "B01/B02/B03 rút gọn theo TK cấp 1, kết chuyển 911 nháp; tờ khai 01/GTGT, 05/KK-TNCN xuất XML nạp HTKK/eTax", "Đạt – mẫu rút gọn, KTT đối chiếu mẫu đầy đủ trước khi phát hành"],
  ["8", "Tài chính – ngân quỹ (GĐ3b)", "Hợp đồng vay (lịch gốc/lãi), đầu tư – hợp tác – ký quỹ – cọc (bắt buộc NQ HĐQT, cờ GDLK); thực hiện lịch → bút toán; dự báo dòng tiền 13 tuần (ngưỡng 500 triệu); báo cáo tài chính tuần", "Đạt"],
  ["9", "Dashboard & robot báo cáo (R7, GĐ3c)", "Bảng điều khiển theo vai trò: “việc chờ tôi xử lý”, KPI HĐQT/BĐH, khối theo phòng; robot báo cáo ngày/tuần/tháng có nhận xét (Claude API khi cấu hình); API cho n8n gửi Zalo/Email", "Đạt – chưa đặt ANTHROPIC_API_KEY và lịch n8n"],
  ["10", "Đồng bộ Vietrip → VTOS (R8)", "Phân tích cấu trúc Vietrip; bổ sung trường tour/booking, dòng chi phí tour, bảng trung gian; API nạp/ánh xạ idempotent; trang Đồng bộ Vietrip; kịch bản chạy trong trình duyệt đã đăng nhập (không lưu mật khẩu). Đã nạp dữ liệu 6–9/2026 (bảng 2)", "Đạt – 205 phiếu thu chờ booking, tự khớp ở lần đồng bộ sau"],
];
const du_lieu = [
  ["Người dùng / xe", "154 / 10", "Tài khoản tạo mật khẩu ngẫu nhiên, HCNS cấp lại; tài xế gắn xe"],
  ["Tour", "1.244 (T6: 311, T7: 292, T8: 223, T9: 180; 238 tour sau 30/9)", "Trạng thái theo ngày kết thúc; 10 tour tạm tạo từ mã (tour đã gộp/hủy trên Vietrip)"],
  ["Booking (đặt 1/6–5/9)", "10.295", "Booking hủy ghi 0 đồng; booking của tour hủy bỏ qua (235)"],
  ["Quyết toán chi tiết tour", "837 tour – 6.439 dòng chi phí", "Tổng thu ≈ 74,1 tỷ; dòng chi phí giữ NCC (MST), đơn giá, SL, hệ số, thực chi, đã trả"],
  ["Phiếu thu/chi khách", "5.946 (5.776 thu đã xác nhận ≈ 69,5 tỷ; 162 chi hoàn khách)", "T6 21,5 · T7 25,4 · T8 20,9 · T9 1,7 tỷ; 205 phiếu chờ booking"],
  ["Lệnh chi NCC", "4.807 (4.508 đã chi ≈ 31,9 tỷ)", "Từ 24/6 (Vietrip chỉ trả ~6.000 lệnh gần nhất)"],
];
const vai_tro = [
  ["Chủ tịch HĐQT", "chutich", "Ký tham số chính sách, bảng giá xe, đề nghị chi 2 chữ ký, dự toán ngoài cổng; xem KPI HĐQT, dự báo 13 tuần, danh mục đầu tư", "Bảng điều khiển · Tham số chính sách · Chi tiền · Tài chính · Robot báo cáo"],
  ["Tổng giám đốc", "tgd", "Ký chữ ký thứ 2; duyệt đề nghị chi, mã KM khi biên < 10%; ký lô bảng lương; duyệt hợp đồng tài chính", "Bảng điều khiển · Chi tiền · Nhân sự – Lương · Tài chính · Tour"],
  ["Phó TGĐ tour đoàn / Marketing", "ptgd.doan / ptgd.mkt", "Duyệt dự toán đoàn biên ≥ 10%; duyệt chi Marketing < 5 triệu; theo dõi KPI phòng", "Tour & dự toán · Chi tiền · Bảng điều khiển"],
  ["Trưởng phòng Điều hành", "tp.dieuhanh", "Duyệt dự toán tour lẻ trong cổng; phân điều hành; chấm báo cáo ngày; theo dõi quá hạn quyết toán, chuyến 21 ngày tới", "Tour & dự toán · Yêu cầu & booking · Báo cáo ngày"],
  ["Nhân viên Điều hành", "dh.*", "Lập tour & dự toán 3 con số; nhận yêu cầu, tạo booking trong 2 giờ (4 trường bắt buộc); lệnh điều xe; quyết toán tour trong 7/3 ngày; đề nghị chi NCC", "Tour & dự toán · Yêu cầu & booking · Chi tiền · Báo cáo ngày"],
  ["Kinh doanh (Lẻ / Đoàn)", "kd.*", "Gửi yêu cầu booking, theo dõi D-7, thu tiền khách (SePay/tiền mặt), báo cáo ngày trước 20h, ca trực page; xem thang lương/hoa hồng của mình", "Yêu cầu & booking · Thu tiền · Báo cáo ngày · Nhân sự – Lương (bản thân)"],
  ["Giám đốc Kinh doanh", "gd.kd", "Duyệt yêu cầu, xếp ca trực, chấm báo cáo ngày, theo dõi chỉ tiêu theo mốc, thưởng theo tháng quyết toán", "Bảng điều khiển · Yêu cầu & booking · Báo cáo ngày"],
  ["Kế toán", "ketoan", "Xác nhận phiếu thu lệch, xác nhận quyết toán tour, ghi sổ chứng từ nháp, phát hành HĐĐT, khóa kỳ, BCTC & tờ khai, lệnh chi & SePay tiền ra, cơ sở lương gửi HCNS, hợp đồng tài chính, dự báo 13 tuần; chạy đồng bộ Vietrip", "Thu tiền · Chi tiền · Kế toán · Tài chính · Nhân sự – Lương · Đồng bộ Vietrip"],
  ["Nhân sự Hành chính", "hcns", "Hồ sơ nhân sự, hợp đồng, visa; lập bảng lương từ cơ sở Kế toán xác nhận; sự vụ; tỷ lệ báo cáo ngày; đội xe & tài xế", "Nhân sự – Lương · Báo cáo ngày"],
  ["CNTT", "cntt", "Quản trị tài khoản, tham số kỹ thuật, khóa tour sau KT xác nhận, đồng bộ Vietrip, robot & n8n, sao lưu, xử lý sự cố; không được sửa số liệu nghiệp vụ", "Đồng bộ Vietrip · Nhật ký · Tham số · Robot báo cáo"],
  ["Ban Kiểm soát", "bks", "Chỉ đọc toàn bộ: nhật ký hash-chain, chứng từ, quyết toán, bảng lương, đối chiếu Vietrip", "Nhật ký · Kế toán · Đồng bộ Vietrip · Bảng điều khiển"],
];
const ton_tai = [
  ["1", "Ngưỡng thang f (Bảng B.1), đơn giá HDV 23 tuyến, bảng phân mức sự vụ đang dùng giá trị tạm", "Anh Tuấn nạp qua Tham số chính sách (2 chữ ký)", "Trước kỳ lương 9/2026"],
  ["2", "Khóa webhook SePay chưa dán vào my.sepay.vn; ANTHROPIC_API_KEY, lịch n8n chưa cấu hình", "Anh Tuấn / CNTT", "Tuần 2 tháng 9"],
  ["3", "Adapter HĐĐT nội bộ – chưa nối nhà cung cấp HĐĐT; BCTC mẫu rút gọn", "CNTT + Kế toán (chọn NCC HĐĐT; KTT đối chiếu mẫu đầy đủ TT99)", "Q4/2026"],
  ["4", "Số dư đầu kỳ (MISA) chưa nhập; dữ liệu Vietrip nhập không sinh bút toán", "Kế toán cung cấp bảng cân đối 31/8; CNTT xây công cụ nhập", "Trước cắt chuyển"],
  ["5", "205 phiếu thu Vietrip chưa khớp booking; lệnh chi NCC tháng 6 chỉ từ 24/6", "Chạy lại kịch bản đồng bộ hằng ngày; Kế toán đối chiếu", "Liên tục"],
  ["6", "Chạy song song với MISA/Vietrip một quý; hạ tầng miễn phí (Render ngủ khi rảnh) – cần VPS/DB trả phí khi chạy thật", "HĐQT quyết định; CNTT triển khai", "Q4/2026"],
];

const doc = new Document({
  styles: { default: { document: { run: { font: F, size: 24 } } } },
  numbering: { config: [{ reference: "bul", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1000, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { margin: { top: 1134, bottom: 1134, left: 1418, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [T("VTOS – Biên bản nghiệm thu & Hướng dẫn theo vai trò – Trang ", { size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: F, size: 18 })] })] }) },
    children: [
      new Table({ width: { size: 9600, type: WidthType.DXA }, columnWidths: [4300, 5300], rows: [new TableRow({ children: [
        new TableCell({ width: { size: 4300, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [C("CÔNG TY CP DU LỊCH VIETOURIST", { bold: true, size: 22 }), C("VIETOURIST HOLDINGS", { size: 22 }), C("––––––––––––", { size: 22 })] }),
        new TableCell({ width: { size: 5300, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [C("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", { bold: true, size: 22 }), C("Độc lập – Tự do – Hạnh phúc", { bold: true, size: 22 }), C("––––––––––––", { size: 22 })] })] })] }),
      gap(),
      C("BIÊN BẢN NGHIỆM THU", { bold: true, size: 32 }),
      C("HỆ THỐNG QUẢN TRỊ NỘI BỘ VTOS (VIETOURIST OPERATING SYSTEM)", { bold: true, size: 26 }),
      C("Giai đoạn 1–3 và đồng bộ dữ liệu Vietrip tháng 6–9/2026", { italics: true, size: 24 }),
      C("Số: ……/BB-VTOS          TP. Hồ Chí Minh, ngày 05 tháng 9 năm 2026", { size: 24 }),
      gap(),
      P([T("Căn cứ ", {}), T("Thiết kế hệ thống VTOS v1.7", { italics: true }), T(" và bộ chính sách quản trị hiệu lực từ 01/9/2026 (ký ngày 27/8/2026); căn cứ kết quả triển khai trên môi trường web thật (https://vtos.infinitytours.org) đến ngày 05/9/2026, hôm nay các bên tiến hành nghiệm thu như sau:")]),
      H1("I. THÀNH PHẦN"),
      B("Bên giao (Bên B): Chuyên viên Hệ thống AI – bộ phận CNTT (Claude, vận hành theo yêu cầu của anh Trần Tuấn)."),
      B("Bên nhận (Bên A): Công ty CP Du lịch Vietourist – đại diện: ông Trần Tuấn (chủ trì chuyển đổi số); thành phần tham dự: Kế toán, Trưởng phòng Điều hành, Giám đốc Kinh doanh, Nhân sự Hành chính, Ban Kiểm soát."),
      H1("II. NỘI DUNG NGHIỆM THU"),
      H2("1. Hạng mục phần mềm"),
      table(["TT", "Hạng mục", "Nội dung đã hoàn thành", "Kết luận"], hang_muc, [500, 1900, 5300, 1900], { center: [0] }),
      gap(),
      P("Kiểm thử tự động: 40 kịch bản (backend/tests, chạy độc lập từng phân hệ) – toàn bộ đạt tại thời điểm nghiệm thu. Mã nguồn: kho riêng infinispathway-admin/vtos-platform, 21 lần cập nhật, phiên bản cuối e6a6ab3 ngày 05/9/2026."),
      H2("2. Dữ liệu Vietrip đã nạp vào VTOS (tháng 6–9/2026)"),
      table(["Đối tượng", "Số lượng", "Ghi chú"], du_lieu, [2100, 3400, 4100]),
      gap(),
      P("Dữ liệu nhập giữ mã Vietrip để tra ngược (VT<id>, VTPT<id>, VTPC<id>, VTDC<id>), không sinh bút toán kế toán; số dư đầu kỳ sẽ nhập từ MISA khi cắt chuyển. Kịch bản đồng bộ chạy lại nhiều lần không nhân bản dữ liệu."),
      H2("3. Tồn tại và việc phải làm tiếp"),
      table(["TT", "Tồn tại", "Xử lý / người thực hiện", "Thời hạn"], ton_tai, [500, 4300, 3300, 1500], { center: [0] }),
      H1("III. KẾT LUẬN"),
      P("Bên A nghiệm thu các hạng mục 1–10 nêu tại mục II.1 để đưa vào chạy song song với MISA/Vietrip từ tháng 9/2026; các tồn tại tại mục II.3 được theo dõi và đóng theo thời hạn. Biên bản lập thành 02 bản, mỗi bên giữ 01 bản, có giá trị như nhau."),
      gap(),
      new Table({ width: { size: 9600, type: WidthType.DXA }, columnWidths: [4800, 4800], rows: [new TableRow({ children: [
        new TableCell({ width: { size: 4800, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [C("ĐẠI DIỆN BÊN A", { bold: true }), C("(Ký, ghi rõ họ tên)", { italics: true, size: 22 }), gap(), gap(), gap(), C("Trần Tuấn")] }),
        new TableCell({ width: { size: 4800, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [C("ĐẠI DIỆN BÊN B", { bold: true }), C("(Ký, ghi rõ họ tên)", { italics: true, size: 22 }), gap(), gap(), gap(), C("Bộ phận CNTT")] })] })] }),
      new Paragraph({ children: [new PageBreak()] }),
      C("PHỤ LỤC – HƯỚNG DẪN SỬ DỤNG VTOS THEO VAI TRÒ", { bold: true, size: 28 }),
      C("(kèm Biên bản nghiệm thu ngày 05/9/2026)", { italics: true }),
      H1("1. Truy cập và đăng nhập"),
      B("Địa chỉ: https://vtos.infinitytours.org (dùng được trên điện thoại – thêm vào màn hình chính như ứng dụng)."),
      B("Tài khoản: theo bảng dưới; mật khẩu lần đầu do HCNS/CNTT cấp, đổi ngay sau khi đăng nhập. Tài khoản mẫu khi chạy thử dùng mật khẩu 123456 – phải đổi trước khi chạy thật."),
      B("Mọi thao tác đều ghi nhật ký bất biến (tab Nhật ký) – không sửa/xóa được; sai thì lập chứng từ đảo hoặc giải trình."),
      H1("2. Nguyên tắc chung (theo bộ chính sách 01/9/2026)"),
      B("Hai chữ ký Chủ tịch + TGĐ cho: tham số chính sách, bảng giá xe, dự toán ngoài cổng biên 10%, đề nghị chi ngoài dự toán hoặc Marketing ≥ 5 triệu, hợp đồng tài chính."),
      B("Dự toán tour có 3 con số (doanh thu – chi phí – biên); biên < 10% bị chặn, mã khuyến mãi làm biên < 10% treo chờ TGĐ."),
      B("Điều hành là nơi duy nhất tạo booking (trong 2 giờ, 4 trường bắt buộc); mốc D-7 thu đủ tiền; quyết toán đoàn 7 ngày, lẻ 3 ngày; Kế toán xác nhận → CNTT khóa."),
      B("Báo cáo ngày trước 20h thay chấm công; thưởng tính theo tháng quyết toán, trên số liệu Kế toán xác nhận."),
      H1("3. Hướng dẫn theo vai trò"),
      table(["Vai trò", "Tài khoản", "Việc làm trên VTOS", "Tab sử dụng"], vai_tro, [1700, 1300, 4600, 2000]),
      gap(),
      H1("4. Quy trình thao tác chính"),
      H2("4.1 Tour & dự toán → booking → thu tiền"),
      B("Điều hành: Tour & dự toán › Tạo tour › nhập dự toán (doanh thu, chi phí, biên) › Gửi duyệt. Biên ≥ 10%: TP Điều hành duyệt; < 10%: Chủ tịch + TGĐ ký kèm giải trình."),
      B("Kinh doanh: Yêu cầu & booking › Gửi yêu cầu (tour, khách, SĐT, số khách, giá). Điều hành tạo booking trong 2 giờ; khách chuyển khoản ghi mã booking → SePay tự lập phiếu thu; tiền mặt: Thu tiền › Lập phiếu tiền mặt."),
      B("Kế toán: Thu tiền › Hàng chờ – xác nhận các giao dịch lệch mã/số tiền; công nợ D-7 hiện ở Cảnh báo."),
      H2("4.2 Chi tiền – quyết toán – kế toán"),
      B("Bộ phận: Chi tiền › Đề nghị chi (bắt buộc mã tour, NCC, số tiền, hóa đơn) › Kế toán kiểm › TGĐ duyệt (2 chữ ký nếu ngoài dự toán / MKT ≥ 5 triệu) › Kế toán chi (chuyển khoản SePay hoặc tiền mặt)."),
      B("Điều hành: Tour › Quyết toán trong 7/3 ngày sau kết thúc – nhập thực thu/thực chi theo dòng chi phí (mẫu Vietrip). Kế toán › Xác nhận → hệ thống ghi 154/335, 632 → CNTT khóa tour."),
      B("Kế toán: Kế toán › Chứng từ nháp – ghi sổ; Hóa đơn – phát hành GTGT từ booking; Khóa kỳ cuối tháng; BCTC / Tờ khai thuế – xuất XML nạp HTKK."),
      H2("4.3 Nhân sự – lương – báo cáo ngày"),
      B("Nhân viên: Báo cáo ngày trước 20h (4 phần); trang ca trực theo lịch. Trưởng phòng chấm; robot xếp loại A/B/C/D."),
      B("Kế toán xác nhận cơ sở lương (doanh thu quyết toán, hoa hồng) › HCNS lập bảng lương (Nhân sự – Lương › Tính nháp › Kiểm tra) › TGĐ ký lô › hệ thống ghi bút toán lương."),
      H2("4.4 Tài chính và báo cáo lãnh đạo"),
      B("Kế toán: Tài chính › Hợp đồng (vay/đầu tư/ký quỹ) – đính kèm NQ HĐQT; Thực hiện lịch khi ngân hàng báo có; Dự báo 13 tuần xem hằng tuần."),
      B("Lãnh đạo: Bảng điều khiển – “việc chờ tôi xử lý” và KPI; Robot báo cáo – báo cáo ngày/tuần/tháng có nhận xét (tự gửi Zalo/Email khi n8n bật)."),
      H2("4.5 Đồng bộ Vietrip (giai đoạn chạy song song)"),
      B("Kế toán/CNTT: đăng nhập Vietrip trên Chrome › mở Console (F12) › dán kịch bản docs/vietrip-sync.js › chạy với khoảng ngày cần lấy. Kịch bản chỉ dùng phiên đăng nhập của người chạy, không lưu mật khẩu; chạy lại không nhân bản."),
      B("Trang Đồng bộ Vietrip: xem số lượng đã nạp/ánh xạ theo loại; bản ghi “chưa có booking/tour” tự khớp ở lần sau; CNTT gỡ bản ghi nhầm bằng API xóa (ghi nhật ký)."),
      H1("5. Hỗ trợ"),
      B("Sự cố đăng nhập, phân quyền, dữ liệu Vietrip: CNTT (tài khoản cntt). Nghiệp vụ kế toán – lương: Kế toán / HCNS. Thay đổi chính sách: Tham số chính sách (Chủ tịch + TGĐ ký)."),
    ],
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2], b); console.log("ok", b.length); });
