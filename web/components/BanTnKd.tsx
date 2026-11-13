"use client";
import BanKdKhung, { BangDoiNgu, BangThucBan, BieuDo12, KhoiPhaiThu, OSo, giaTriDt, so, type Tab } from "@/components/BanKdKhung";

/** R5-7 · BÀN LÀM VIỆC TRƯỞNG NHÓM KINH DOANH — Chủ tịch duyệt bản xem trước 13/11/2026.
 *  Số CỦA NHÓM; giữ ô «Doanh thu của tôi» vì trưởng nhóm vẫn đi bán (Chủ tịch: «giữ»). Đội ngũ = người
 *  trong nhóm. Chỉ đọc; mọi thẻ mở màn gốc ngay trong bàn. Khung chung: components/BanKdKhung.tsx. */
const TAB: Tab[] = [
  { ma: "tq", ten: "Tổng quan", the: [] },
  { ma: "ban", ten: "Bán hàng", the: [
    { ten: "Bàn bán tour lẻ", mo_ta: "Chỗ trống, ngày đi và dự toán chuyến", toi: "/ban-tour-le" },
    { ten: "Lịch khởi hành", mo_ta: "Danh sách chuyến tour lẻ", toi: "/tours?mang=le" },
    { ten: "Báo giá", mo_ta: "Soạn nháp, kiểm tra biên trước khi gửi khách", toi: "/bao-gia?mang=kd_le" },
    { ten: "Giá & chính sách bán", mo_ta: "Bảng giá và thời hạn áp dụng", toi: "/bang-gia" }] },
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
      const dn = giaTriDt(th.doanh_thu), dtoi = giaTriDt(th.doanh_thu_toi);
      return <>
        <p className="g5-nhom">KẾT QUẢ NHÓM · THÁNG NÀY</p>
        <div className="g5-dai5">
          <OSo nhan="Doanh thu nhóm" v={d ? dn.v : undefined} phu={dn.phu} lk="Chi tiết" bam={() => moToi("/fit")} />
          <OSo nhan="Doanh thu của tôi" v={d ? dtoi.v : undefined} phu={d ? dtoi.phu : ""} lk="Của tôi" bam={() => moToi("/fit")} />
          <OSo nhan="Booking nhóm" v={d ? so(th.booking_moi?.so) : undefined} phu={d ? `Tháng này · ${so(th.booking_moi?.chua_coc)} chưa cọc` : ""} lk="Booking" bam={() => moToi("/bookings?mang=le")} />
          <OSo nhan="Lead mới chưa liên hệ" nong v={d ? so(th.lead_moi?.so) : undefined} phu="Của người trong nhóm" lk="Lead" bam={() => moToi("/leads?tab=leads")} />
          <OSo nhan="Chăm sóc quá hạn" nong v={d ? so(th.cham_soc_qua_han?.so) : undefined} phu="Của người trong nhóm" lk="Chăm sóc" bam={() => moToi("/cham-soc")} />
        </div>
        <div className="g5-hai">
          <BangDoiNgu ds={d?.doi_ngu || []} don />
          <BieuDo12 dt={dt} ten="Doanh thu – chỉ tiêu nhóm" />
        </div>
        <KhoiPhaiThu pt={d?.phai_thu} moToi={moToi} />
        <BangThucBan ds={d?.thuc_ban} moToi={moToi} />
      </>;
    }} />;
}
