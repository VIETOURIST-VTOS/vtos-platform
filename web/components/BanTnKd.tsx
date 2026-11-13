"use client";
import BanKdKhung, { BangDoiNgu, BangThucBan, HangTien, OSo, so, type Tab } from "@/components/BanKdKhung";

/** R5-7 · BÀN LÀM VIỆC TRƯỞNG NHÓM KINH DOANH — Chủ tịch duyệt bản xem trước 13/11/2026.
 *  Số CỦA NHÓM; giữ ô «Doanh thu của tôi» vì trưởng nhóm vẫn đi bán (Chủ tịch: «giữ»). Đội ngũ = người
 *  trong nhóm. Chỉ đọc; mọi thẻ mở màn gốc ngay trong bàn. Khung chung: components/BanKdKhung.tsx. */
const TAB: Tab[] = [
  { ma: "tq", ten: "Tổng quan", the: [] },
  { ma: "ban", ten: "Bán hàng", the: [
    { ten: "Bàn bán tour lẻ", mo_ta: "Chỗ trống, ngày đi và dự toán chuyến", toi: "/ban-tour-le" },
    { ten: "Chính sách bán", mo_ta: "Chiết khấu, giá trẻ em, khuyến mãi · hoa hồng đối tác/CTV · điểm Rewards", toi: "/chinh-sach-ban" },
    { ten: "Dịch vụ lẻ", mo_ta: "Visa, vé, phòng, xe, gửi khách hưởng hoa hồng", toi: "/non-package" }] },
  { ma: "khach", ten: "Khách & booking", tieu_de: "Khách & booking", the: [
    { ten: "Khách hàng & lead", mo_ta: "Lead của nhóm, nguồn khách", toi: "/leads?tab=leads" },
    { ten: "Hộp thư đa kênh", mo_ta: "Hội thoại và khách chờ sale", toi: "/inbox" },
    { ten: "Yêu cầu đặt dịch vụ", mo_ta: "Gửi Điều hành, theo dõi hạn xử lý", toi: "/requests?mang=le" },
    { ten: "Booking & bảo lưu", mo_ta: "Cọc, thu tiền, giữ chỗ, hủy", toi: "/bookings?mang=le" }] },
  { ma: "cs", ten: "Chăm sóc", tieu_de: "Chăm sóc khách hàng", the: [
    { ten: "Chăm sóc sau tour", mo_ta: "Phiếu của nhóm, quá hạn", toi: "/cham-soc" },
    { ten: "Phản hồi & khiếu nại", mo_ta: "Hồ sơ khiếu nại", toi: "/khieu-nai" }] },
  { ma: "doi", ten: "Đội ngũ", tieu_de: "Đội ngũ nhóm", the: [
    { ten: "Cơ cấu tổ chức", mo_ta: "Người trong nhóm", toi: "/to-chuc-kd" },
    { ten: "Báo cáo công việc", mo_ta: "Báo cáo ngày / tuần của nhóm", toi: "/reports" }] },
  { ma: "bc", ten: "Báo cáo", tieu_de: "Báo cáo", the: [
    { ten: "Doanh thu & chỉ tiêu", mo_ta: "Của nhóm và từng người", noi: "doanh-thu" },
    { ten: "Báo cáo bán hàng", mo_ta: "Bán tour, nhắc thu, hủy chỗ", toi: "/sales-reports?mang=le" },
    { ten: "Phiếu lương của tôi", mo_ta: "Lương, thưởng, hoa hồng", toi: "/phieu-luong" }] },
];

export default function BanTnKd() {
  return <BanKdKhung ten="Bàn làm việc Trưởng nhóm Kinh doanh" tabs={TAB}
    phamVi={(d) => `${d.don_vi?.ten || "chưa phân công"} · ${so(d.so_nguoi)} người`}
    tongQuan={({ d, dt, moToi }) => {
      const th = d?.the || {};
      return <>
        {/* R5-14: bỏ hai ô doanh thu (trùng khối Doanh thu – Chỉ tiêu, có nút «Của tôi»). */}
        <p className="g5-nhom">VIỆC CẦN XỬ LÝ</p>
        <div className="g5-dai3">
          <OSo nhan="Lead mới chưa liên hệ" nong v={d ? so(th.lead_moi?.so) : undefined} phu="Của người trong nhóm" lk="Lead" bam={() => moToi("/leads?tab=leads")} />
          <OSo nhan="Chăm sóc quá hạn" nong v={d ? so(th.cham_soc_qua_han?.so) : undefined} phu="Của người trong nhóm" lk="Chăm sóc" bam={() => moToi("/cham-soc")} />
          <OSo nhan="Booking nhóm" v={d ? so(th.booking_moi?.so) : undefined} phu={d ? `Tháng này · ${so(th.booking_moi?.chua_coc)} chưa cọc` : ""} lk="Booking" bam={() => moToi("/bookings?mang=le")} />
        </div>
        <BangThucBan ds={d?.thuc_ban} moToi={moToi} />
        <p className="g5-nhom">TIỀN · THÁNG NÀY</p>
        <HangTien duong="/ban-kd-le/vai/nhip" coToi pt={d?.phai_thu} moToi={moToi} />
        <p className="g5-nhom">ĐỘI NGŨ</p>
        <BangDoiNgu ds={d?.doi_ngu || []} don />
      </>;
    }} />;
}
