"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, pct } from "@/lib/api";
import { errMsg } from "@/components/ui";
import KhoiDongTien from "@/components/KhoiDongTien";
import { KhoiHieuQuaXe, KhoiPhaiThu, KhoiPhaiTra } from "@/components/KhoiV14";
import {
  KhoiKinhDoanhLe, KhoiKinhDoanhDoan, KhoiBaoCaoNgay,
} from "@/components/KhoiKinhDoanh";
import {
  DongLoc, KhoiQuyetDinh, TamThe, TieuDe, tien, dem, docHoKeHoach, type The,
} from "@/components/DauManHinh01";
import { bieuDoCua } from "@/components/BaKhuBieuDo";

function Dash() {
  const { user } = useShell();
  const [d, setD] = useState<any>(null);
  // Trước đây lỗi bị nuốt bằng .catch(() => {}) nên máy chủ trả 500 mà người dùng chỉ thấy
  // "Đang tải…" đứng im vĩnh viễn – lỗi PostgreSQL ngày 07/9 sống sót nhiều ngày vì đúng chỗ này.
  const [loi, setLoi] = useState<string>("");
  const tai = () => { setLoi(""); api("/dashboard").then(setD).catch((e) => setLoi(errMsg(e) || "Không tải được bảng điều khiển")); };
  useEffect(tai, []);
  if (loi) return <div className="panel" style={{ borderColor: "var(--red)" }}>
    <b style={{ color: "var(--red)" }}>Không tải được bảng điều khiển.</b>
    <div className="muted" style={{ margin: "6px 0" }}>{loi}</div>
    <div className="muted">Các màn hình khác vẫn dùng được. Nếu lặp lại, báo CNTT kèm nguyên văn dòng trên.</div>
    <button className="act" onClick={tai}>Thử lại</button>
  </div>;
  if (!d) return <p className="muted">Đang tải…</p>;
  const c = d.counts || {};
  const k = d.kpis || {}; const sec = d.sections || {};
  /* Cửa sổ ngày khởi hành do MÁY CHỦ khai (services/dashboard.py · SO_NGAY_SAP_KHOI_HANH). Màn
     hình chỉ đọc — gõ lại con số ở đây là mở đường cho hai nơi nói khác nhau, đúng lỗi vừa sửa ở
     đầu cột bảng dòng tiền. Lối lui 14 chỉ dùng khi máy chủ cũ chưa trả trường này. */
  const soNgayKH = sec.sap_khoi_hanh_so_ngay ?? 14;

  /* TÁM THẺ CHỈ TIÊU theo bản vẽ V1.2. Mỗi thẻ chỉ ra đúng một con số chính, một dòng so sánh và
     một dòng trạng thái dữ liệu – không nhồi ba số vào một ô như hàng KPI cũ.

     KỲ BÁO CÁO: màn hình này CHỈ theo THÁNG (anh Tuấn chốt 13/9). Quý và năm xem ở báo cáo chi
     tiết – hàng lọc có đường dẫn sang đó. Nhờ vậy tám thẻ không phải mang theo một nhánh "nếu
     chọn quý thì rỗng", và không có chỗ nào lấy số tháng dán nhãn quý. */
  /* TC-36 · Xu hướng do MÁY CHỦ quyết: lấy kỳ nào, kỳ nào rỗng, đủ điểm để vẽ chưa. Màn hình chỉ
     gắn đúng chuỗi vào đúng thẻ. Thẻ nào máy chủ chưa trả xu hướng thì không vẽ gì — không dựng
     một dãy cột rỗng cho "đỡ trống". */
  const xh = sec.xu_huong || {};
  /* TC-41 · KẾ HOẠCH THÁNG — cửa nhập mở ngày 16/9/2026 ở /ke-hoach-thang.
     Bản vẽ V1.4 chốt dòng phụ của thẻ Doanh thu là "so với kế hoạch và kỳ trước". Suốt bốn vòng
     dòng ấy chỉ in được một câu thú nhận, vì trong hệ thống không có bảng nào giữ chỉ tiêu.
     Nay có. Nhưng ba trạng thái phải giữ nguyên vẹn khác nhau, và `docHoKeHoach` giữ chúng:
     chưa ai nhập · nhập thiếu pháp nhân · đủ. Trạng thái giữa là trạng thái nguy hiểm — cộng phần
     đã nhập lại sẽ ra một chỉ tiêu thấp hơn thật, và tỉ lệ đạt cao vọt mà không có gì trông giống
     lỗi cả. Máy chủ quyết đủ hay chưa (cờ `du`), màn hình chỉ đọc cờ ấy. */
  const kh = k.ke_hoach_thang;
  const tam: The[] = [
    { nhan: "Doanh thu tháng", so: tien(k.doanh_thu_thang),
      duoi: `${k.so_chuyen_thang ?? 0} chuyến đã quyết toán · `
            + docHoKeHoach(kh, "doanh_thu", kh?.ty_le_dat_doanh_thu),
      xu_huong: xh.doanh_thu_thang },
    { nhan: "Lợi nhuận trước thuế", so: tien(k.ln_ke_toan_thang),
      duoi: `Lợi nhuận kế toán tháng, cùng phạm vi · `
            + docHoKeHoach(kh, "loi_nhuan_truoc_thue", kh?.ty_le_dat_loi_nhuan),
      xu_huong: xh.ln_ke_toan_thang },
    /* Bản vẽ chốt dòng phụ là "Khách đã chốt / chỗ còn". Máy chủ chưa trả sức chứa từng chuyến nên
       chưa tính được "chỗ còn" – ghi ra chỗ thiếu, không thay bằng con số khác rồi để người đọc
       tưởng đó là chỗ còn. */
    { nhan: "Tour đang bán", so: dem(c.da_duyet ?? 0),
      duoi: `${d.n_tours ?? 0} tour trên hệ thống · chưa có sức chứa từng chuyến nên chưa tính được chỗ còn (Điều hành)`,
      xu_huong: xh.tour_dang_ban },
    { nhan: "Tour chờ quyết toán", so: dem((c.ket_thuc || 0) + (c.da_dong_so || 0)),
      duoi: `${sec.qua_han_qt?.length ?? 0} chuyến quá hạn quyết toán`,
      do: (sec.qua_han_qt?.length ?? 0) > 0, xu_huong: xh.tour_cho_quyet_toan },
    { nhan: "Tour sắp khởi hành", so: dem(sec.sap_khoi_hanh?.length),
      duoi: `${soNgayKH} ngày tới`,
      ai: "Điều hành", cua: "/tours" },
    { nhan: "Đội xe hôm nay", so: null,
      ai: "Đội xe", cua: "/doi-xe",
      duoi: "Đang chạy / đủ điều kiện · xe trống · bảo dưỡng" },
    { nhan: "Marketing & PR", phu: "Khách tiềm năng mới", so: null,
      ai: "Marketing", cua: "/leads?tab=leads",
      duoi: "Đã chuyển Kinh doanh · đã chốt" },
    /* SỬA 13/9/2026 – thẻ này từng in `d.alerts.length`, tức SỐ DÒNG máy chủ gửi kèm trang này
       (đang cắt ở 60), chứ không phải số tồn đọng thật. Trên bản chạy thật nó ra "60" trong khi
       dòng phụ ngay dưới ghi "1387 cảnh báo đỏ đang mở": con số nhỏ nằm ở chỗ to nhất màn hình,
       con số thật nằm ở dòng chữ nhỏ. Nay lấy đúng `k.canh_bao_do`; nếu máy chủ không gửi thì thẻ
       để trống kèm cửa nhập, không lấy độ dài danh sách thay vào. */
    /* Bản vẽ chốt ba chỉ số: hồ sơ quá hạn · nghiêm trọng · chưa có người nhận. Máy chủ mới có
       "nghiêm trọng" (cảnh báo đỏ); chưa gán người nhận cho cảnh báo nên chưa đếm được cái thứ ba,
       và chưa tách hồ sơ quá hạn ra khỏi cảnh báo đỏ. Nói ra hai cái còn thiếu. */
    { nhan: "Tồn đọng cần xử lý", so: dem(k.canh_bao_do),
      duoi: "cảnh báo mức nghiêm trọng · chưa tách được hồ sơ quá hạn và hồ sơ chưa có người nhận (CNTT)",
      do: (k.canh_bao_do ?? 0) > 0, ai: "Công nghệ thông tin", cua: "/alerts" },
  ];

  /* Biểu đồ dựng một lần, giao cho từng khối tự bày. Khối nào chưa đủ số thì nhận `null` và chỉ
     hiện ô số của nó — ô số vốn đã ghi "Chưa kết nối" kèm bộ phận và cửa nhập. */
  const bd = bieuDoCua(sec);

  return (<>
    <TieuDe vai={user?.role} ten_vai={user?.role_name} />
    <DongLoc />

    {/* ══ TC-40 · MÀN HÌNH CHỦ TỊCH SAU KHI ANH TUẤN SOÁT TỪNG KHỐI (15/9/2026) ═══════════════
        Anh Tuấn mở bản chạy thật, chụp ảnh từng khối, và chốt danh sách GIỮ:
          · Tám thẻ chỉ tiêu          · Hiệu quả đội xe (thêm chọn tháng / quý / năm)
          · Phải thu theo hạn          · Phải trả theo hạn
          · Kinh doanh Lẻ · Đoàn · Báo cáo ngày
          · Dòng tiền — "số 6 dòng tiền em giữ nguyên", tức giữ NGUYÊN VẸN, cả bốn ô cảnh báo
        Cộng thêm một khối ông ấy không đụng tới: Cần quyết định — việc chờ chữ ký của chính ông
        ấy, không ai làm thay được.

        BỎ: Điều hành 14 ngày · Tồn đọng theo bộ phận · Tiến độ báo cáo · Rủi ro trọng yếu · Việc
        cần xử lý · Tồn đọng cần xử lý · và khu biểu đồ riêng có đánh số.

        HAI LUẬT RÚT RA, cả hai kiểm được bằng máy:

        1. MỘT CON SỐ — MỘT CHỖ — MỘT HÌNH. Trước vòng này cảnh báo tồn đọng nằm ở BỐN chỗ và
           doanh thu nhân viên nằm ở HAI chỗ. Bốn chỗ cùng nói một chuyện thì không chỗ nào còn
           đáng đọc, và đến lúc bốn chỗ ra bốn con số thì không ai biết tin chỗ nào.

        2. BIỂU ĐỒ Ở CẠNH CON SỐ NÓ VẼ. Vòng TC-38 gom biểu đồ ra ba khu riêng — nghe rất hợp lý,
           vì "khu biểu đồ" là thứ bảng điều hành nào cũng có. Nhưng trên bản chạy thật nó tách
           con số khỏi hình của chính con số ấy, và người đọc phải cuộn qua lại để ghép hai thứ
           vốn là một. Nay hình về nằm trong khối.

        BỎ KHỎI MÀN HÌNH KHÔNG PHẢI BỎ SỐ — chỗ dễ hiểu nhầm nhất, nên nói rõ. Mỗi khối gỡ đi đều
        còn nguyên ở chỗ của nó: Điều hành ở /tours và /lenh-dieu-xe (mã giữ trong
        components/KhoiDieuHanh.tsx), tồn đọng ở /alerts, tiến độ báo cáo ở /reports. Bảng điều
        hành Chủ tịch trả lời câu "có gì cần tôi quyết"; nó không phải chỗ chứa mọi bảng của công
        ty.

        KHÁC BẢN VẼ V1.4, VÀ LÀ KHÁC CÓ CHỦ Ý. Ghi ra để vòng sau không ai "sửa lại cho đúng bản
        vẽ" mà không biết vì sao: bản vẽ là bản vẽ của một hệ thống ĐÃ CÓ SỐ; hôm nay VTOS đang
        dựng, và những khối bị gỡ chưa có sổ nào phía sau. */}

    <KhoiQuyetDinh ds={d.approvals || []} vai={user?.role} />
    <TamThe ds={tam} />

    <KhoiHieuQuaXe d={sec.hieu_qua_xe} theo_ky={sec.hieu_qua_xe_theo_ky} />

    <KhoiDongTien />

    <KhoiPhaiThu ds={sec.phai_thu_theo_han} chua_co_han={sec.phai_thu_chua_co_han}
      vi_sao={sec.phai_thu_vi_sao} bieu_do={bd.phai_thu} />
    <KhoiPhaiTra ds={sec.phai_tra_theo_han} qua_han={sec.phai_tra_qua_han}
      chua_co_han={sec.phai_tra_chua_co_han} vi_sao={sec.phai_tra_vi_sao} bieu_do={bd.phai_tra} />

    {/* Ba khối kinh doanh & nội bộ xếp một hàng: cả ba đều ngắn sau khi bỏ bảng, và đọc cạnh nhau
        thì thấy được bức tranh "bán hàng · lợi nhuận · kỷ luật nội bộ" trong một cái nhìn. */}
    <div className="mh01-hang-3">
      <KhoiKinhDoanhLe ds={sec.kd_le} bieu_do={bd.kd_le} />
      <KhoiKinhDoanhDoan d={sec.kd_doan} bieu_do={bd.kd_doan} />
      <KhoiBaoCaoNgay d={sec.bao_cao_ngay} bieu_do={bd.bao_cao_ngay} />
    </div>

    <p className="muted">Ngưỡng biên đang áp dụng {pct(d.threshold)} · Robot chạy mỗi 10 phút; CNTT có thể chạy tay ở trang Cảnh báo.</p>
  </>);
}
export default function Page() { return <Shell><Dash /></Shell>; }
