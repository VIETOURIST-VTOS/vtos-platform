"use client";
import BanKdKhung, { DoiNguVaNhom, BangThucBan, KhoiNhipDoanhThu, KhoiPhaiThu, OSo, giaTriDt, so, tien, type Tab } from "@/components/BanKdKhung";

/** R5-7 · BÀN LÀM VIỆC TRƯỞNG PHÒNG KINH DOANH LẺ — Chủ tịch duyệt bản xem trước 13/11/2026.
 *  Số CẢ PHÒNG (đơn vị được phân công và mọi đơn vị con); khối Đội ngũ xếp hạng từng người, khối Theo nhóm.
 *  Chỉ đọc; mọi thẻ mở màn gốc ngay trong bàn. Khung chung: components/BanKdKhung.tsx. */
const TAB: Tab[] = [
  { ma: "tq", ten: "Tổng quan", the: [] },
  { ma: "ban", ten: "Bán hàng", the: [
    { ten: "Bàn bán tour lẻ", mo_ta: "Chỗ trống, ngày đi và dự toán chuyến", toi: "/ban-tour-le" },
    { ten: "Lịch khởi hành", mo_ta: "Danh sách chuyến tour lẻ", toi: "/tours?mang=le" },
    { ten: "Báo giá", mo_ta: "Soạn nháp, kiểm tra biên trước khi gửi khách", toi: "/bao-gia?mang=kd_le" },
    { ten: "Giá & chính sách bán", mo_ta: "Bảng giá và thời hạn áp dụng", toi: "/bang-gia" },
    { ten: "Dịch vụ lẻ", mo_ta: "Visa, vé, phòng, xe và dịch vụ rời", toi: "/non-package" }] },
  { ma: "khach", ten: "Khách & booking", tieu_de: "Khách & booking", the: [
    { ten: "Khách hàng & phân lead", mo_ta: "Lead mới, giao người chăm, nguồn khách", toi: "/leads?tab=leads" },
    { ten: "Hộp thư đa kênh", mo_ta: "Hội thoại và khách chờ sale", toi: "/inbox" },
    { ten: "Yêu cầu đặt dịch vụ", mo_ta: "Gửi Điều hành, theo dõi hạn xử lý", toi: "/requests?mang=le" },
    { ten: "Booking & bảo lưu", mo_ta: "Cọc, thu tiền, giữ chỗ, hủy", toi: "/bookings?mang=le" }] },
  { ma: "cs", ten: "Chăm sóc", tieu_de: "Chăm sóc khách hàng", the: [
    { ten: "Chăm sóc sau tour", mo_ta: "Phiếu của cả phòng, quá hạn", toi: "/cham-soc" },
    { ten: "Phản hồi & khiếu nại", mo_ta: "Hồ sơ khiếu nại", toi: "/khieu-nai" },
    { ten: "Đánh giá sau tour", mo_ta: "Điểm khách chấm", toi: "/danh-gia" }] },
  { ma: "doi", ten: "Đội ngũ", tieu_de: "Đội ngũ kinh doanh", the: [
    { ten: "Cơ cấu tổ chức", mo_ta: "Phòng → nhóm → người", toi: "/to-chuc-kd" },
    { ten: "Báo cáo công việc", mo_ta: "Báo cáo ngày / tuần của người trong phòng", toi: "/reports" }] },
  { ma: "ct", ten: "Chỉ tiêu & báo cáo", tieu_de: "Chỉ tiêu & báo cáo", the: [
    { ten: "Doanh thu & chỉ tiêu", mo_ta: "Theo người, theo nhóm, theo kỳ", noi: "doanh-thu" },
    { ten: "Báo cáo bán hàng", mo_ta: "Bán tour, nhắc thu, hủy chỗ", toi: "/sales-reports?mang=le" },
    { ten: "Bảng chỉ tiêu phòng", mo_ta: "Ngày / tuần / tháng", noi: "bang" }] },
];

export default function BanTpKd() {
  return <BanKdKhung ten="Bàn làm việc Trưởng phòng Kinh doanh lẻ" tabs={TAB}
    phamVi={(d) => `${d.don_vi?.ten || "chưa phân công"} · ${so(d.so_nguoi)} người`}
    tongQuan={({ d, dt, moToi }) => {
      const th = d?.the || {};
      const dtp = giaTriDt(th.doanh_thu);
      return <>
        <p className="g5-nhom">KẾT QUẢ PHÒNG · THÁNG NÀY</p>
        <div className="g5-dai5">
          <OSo nhan="Doanh thu phòng" v={d ? dtp.v : undefined} phu={dtp.phu} lk="Doanh thu & chỉ tiêu" bam={() => moToi("/fit")} />
          <OSo nhan="Booking mới" v={d ? so(th.booking_moi?.so) : undefined} phu={d ? `Tháng này · ${so(th.booking_moi?.chua_coc)} chưa cọc` : ""} lk="Booking" bam={() => moToi("/bookings?mang=le")} />
          <OSo nhan="Lead chưa ai nhận" nong v={d ? so(th.lead_chua_nhan?.so) : undefined} phu="Toàn công ty · chưa phân người" lk="Phân lead" bam={() => moToi("/leads?tab=leads")} />
          <OSo nhan="Chăm sóc quá hạn" nong v={d ? so(th.cham_soc_qua_han?.so) : undefined} phu="Phiếu của người trong phòng" lk="Chăm sóc" bam={() => moToi("/cham-soc")} />
          <OSo nhan="Phải thu khách" v={d ? (th.phai_thu?.so == null ? null : tien(th.phai_thu.so)) : undefined} chua="—" phu={d ? `${so(th.phai_thu?.so_booking || 0)} booking lẻ còn nợ` : ""} lk="Booking còn nợ" bam={() => moToi("/bookings?mang=le")} />
        </div>
        <DoiNguVaNhom doi={d?.doi_ngu || []} nhom={d?.theo_nhom} dang={!d} />
        <KhoiNhipDoanhThu duong="/ban-kd-le/vai/nhip" coToi />
        <KhoiPhaiThu pt={d?.phai_thu} moToi={moToi} />
        <BangThucBan ds={d?.thuc_ban} moToi={moToi} />
      </>;
    }} />;
}
