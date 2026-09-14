"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, vnd, fmtD, fmtDT } from "@/lib/api";
import { ACTION_LABEL } from "@/lib/meta";
import { Tag, errMsg } from "@/components/ui";
import KhoiDongTien from "@/components/KhoiDongTien";
import KhoiTonDong from "@/components/KhoiTonDong";
import {
  KhoiHieuQuaXe, KhoiTonDongBoPhan, KhoiPhaiThu, KhoiPhaiTra, KhoiRuiRo, KhoiTienDoBaoCao,
} from "@/components/KhoiV14";
import {
  DongLoc, KhoiQuyetDinh, TamThe, TieuDe, tien, dem, type The,
} from "@/components/DauManHinh01";

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
  const tam: The[] = [
    /* Bản vẽ V1.4 chốt dòng phụ của thẻ này là "so với kế hoạch và kỳ trước". Máy chủ chưa có kế
       hoạch tháng và chưa trả kết quả kỳ trước, nên KHÔNG bịa một tỷ lệ phần trăm: ghi thẳng là
       chưa có nguồn so sánh và ai phải nhập. Một mũi tên tăng-giảm dựng từ số không có thật thì
       Chủ tịch đọc là kết quả, chứ không đọc là chỗ trống. */
    { nhan: "Doanh thu tháng", so: tien(k.doanh_thu_thang),
      duoi: `${k.so_chuyen_thang ?? 0} chuyến đã quyết toán · chưa có kế hoạch tháng và kỳ trước để so sánh (Kế toán)` },
    { nhan: "Lợi nhuận trước thuế", so: tien(k.ln_ke_toan_thang),
      duoi: "Lợi nhuận kế toán tháng, cùng phạm vi" },
    /* Bản vẽ chốt dòng phụ là "Khách đã chốt / chỗ còn". Máy chủ chưa trả sức chứa từng chuyến nên
       chưa tính được "chỗ còn" – ghi ra chỗ thiếu, không thay bằng con số khác rồi để người đọc
       tưởng đó là chỗ còn. */
    { nhan: "Tour đang bán", so: dem(c.da_duyet ?? 0),
      duoi: `${d.n_tours ?? 0} tour trên hệ thống · chưa có sức chứa từng chuyến nên chưa tính được chỗ còn (Điều hành)` },
    { nhan: "Tour chờ quyết toán", so: dem((c.ket_thuc || 0) + (c.da_dong_so || 0)),
      duoi: `${sec.qua_han_qt?.length ?? 0} chuyến quá hạn quyết toán`,
      do: (sec.qua_han_qt?.length ?? 0) > 0 },
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

  return (<>
    <TieuDe vai={user?.role} ten_vai={user?.role_name} />
    <DongLoc />
    <KhoiQuyetDinh ds={d.approvals || []} vai={user?.role} />
    <TamThe ds={tam} />

    {/* ══ THỨ TỰ KHỐI LẤY ĐÚNG BẢN VẼ V1.4 (anh Tuấn gửi lại tệp và đối chiếu 14/9/2026) ══
        Bản vẽ xếp: Cần quyết định → tám thẻ → Điều hành 14 ngày → Hiệu quả đội xe → Tồn đọng theo
        bộ phận → Phải thu → Phải trả → Dòng tiền → Rủi ro → Tiến độ báo cáo.

        Trước vòng này VTOS đặt khối Dòng tiền NGAY SAU tám thẻ (theo bản vẽ V1.2 cũ) và chèn năm
        khối riêng của VTOS vào giữa — nên đọc từ trên xuống ra một thứ tự khác hẳn bản vẽ.

        Năm khối riêng của VTOS (Việc cần xử lý · Tồn đọng cần xử lý · Kinh doanh Lẻ · Kinh doanh
        Đoàn · Báo cáo ngày) KHÔNG bỏ đi — chúng là việc thật và đang có số thật. Chúng chuyển
        XUỐNG DƯỚI, sau khối cuối của bản vẽ, dưới một đường ngăn nói rõ đây là phần thêm. */}

    <div className="grid" style={{ marginTop: 14 }}>
      {/* KHỐI 04a · ĐIỀU HÀNH. Bản vẽ V1.4 đòi bảy cột: Chuyến · Ngày đi · Số khách · Dịch vụ còn
          thiếu · Xe · HDV · Phụ trách, và ưu tiên chuyến CÒN THIẾU ĐIỀU KIỆN lên trước.

          Máy chủ hôm nay mới trả ba cột đầu. Bốn cột sau vẫn DỰNG ĐỦ ĐẦU CỘT và ghi "chưa nối" ở
          từng ô: đầu cột chính là bản mô tả việc còn nợ, giấu đi thì đến lúc dựng phải đi tìm lại
          bản vẽ. Cũng KHÔNG suy "đã đủ điều kiện" từ việc thiếu dữ liệu – bản vẽ ghi thẳng: không
          mặc định chuyến đã sẵn sàng.

          SỐ NGÀY: anh Tuấn chốt 14/9/2026 lấy theo BẢN VẼ, tức 14 ngày. Máy chủ đổi từ 21 xuống
          14 và TRẢ LUÔN con số ấy ra (`sap_khoi_hanh_so_ngay`); màn hình đọc nó chứ không gõ lại.
          Trước đó hai nơi mang hai con số nên phải in cả hai ra — mà in cả hai thì chẳng ai biết
          tin con nào. */}
      {sec.sap_khoi_hanh && <div className="panel" id="dieu-hanh"><h2>Điều hành – chuyến khởi hành {soNgayKH} ngày tới</h2>
        <p className="muted">Ưu tiên chuyến còn thiếu điều kiện — <b>không</b> mặc định chuyến đã sẵn sàng.</p>
        {sec.sap_khoi_hanh.length ? <div className="wrap"><table className="v14-bang">
          <thead><tr><th>Chuyến</th><th>Ngày đi</th><th>Số khách</th><th>Dịch vụ còn thiếu</th><th>Xe</th><th>HDV</th><th>Phụ trách</th></tr></thead>
          <tbody>{sec.sap_khoi_hanh.map((r: any) => <tr key={r.code}>
            <td>{r.code}</td>
            <td>{fmtD(r.start)} (D-{r.days_left})</td>
            {/* MỐC HOÀ VỐN BẰNG 0 KHÔNG PHẢI LÀ ĐẠT MỐC. Máy chủ hiện trả breakeven = 0 cho hầu hết
                chuyến vì chưa ai nhập điểm hoà vốn. Câu cũ `r.below ? đỏ : xanh` đọc số 0 ấy thành
                "đã vượt mốc" và dán nhãn xanh "ok" lên cả chuyến 0 khách — đúng cái bản vẽ cấm:
                không mặc định chuyến đã sẵn sàng. Chưa có mốc thì nói chưa có mốc. */}
            <td>{r.booked}/{r.breakeven || "—"} khách {
              !r.breakeven
                ? <Tag>chưa có mốc hoà vốn</Tag>
                : r.below ? <Tag cls="red">dưới hòa vốn</Tag> : <Tag cls="ok">ok</Tag>
            }</td>
            <td>{r.dich_vu_thieu ?? <span className="muted">chưa nối</span>}</td>
            <td>{r.xe ?? <span className="muted">chưa nối</span>}</td>
            <td>{r.hdv ?? <span className="muted">chưa nối</span>}</td>
            <td>{r.phu_trach ?? <span className="muted">chưa nối</span>}</td>
          </tr>)}</tbody></table></div> : <p className="muted">Không có chuyến.</p>}
        <p className="muted">Bốn cột <b>Dịch vụ còn thiếu · Xe · HDV · Phụ trách</b> máy chủ chưa trả — <b>Điều hành</b> nhập ở <Link className="the-cua" href="/lenh-dieu-xe">Lệnh điều xe →</Link></p>
        {sec.qua_han_qt?.length > 0 && <p><Tag cls="red">Quá hạn quyết toán</Tag> {sec.qua_han_qt.map((t: any) => t.code).join(", ")}</p>}</div>}
    </div>

    {/* ══ PHẦN CÒN LẠI CỦA BẢN VẼ V1.4, đúng thứ tự khối 04 → 08 ══
        04b Hiệu quả đội xe · 04c Tồn đọng theo bộ phận · 05 Phải thu và Phải trả theo hạn ·
        07 Rủi ro trọng yếu · 08 Tiến độ báo cáo. Khối 06 Dòng tiền nằm đúng chỗ bản vẽ đặt: sau Phải
        trả, trước Rủi ro. */}
    <KhoiHieuQuaXe d={sec.hieu_qua_xe} />
    <KhoiTonDongBoPhan ds={sec.ton_dong_bo_phan} />
    {/* Hai khối hạn xếp DỌC, không cạnh nhau. Đặt cạnh nhau thì mỗi khối chỉ còn nửa bề ngang,
        năm nhóm vỡ thành 2+2+1 và nhóm "Dài hạn" đứng trơ một mình một hàng — đọc thành "bốn nhóm
        và một cái gì đó". Bản vẽ cũng xếp dọc, năm nhóm một hàng. */}
    <KhoiPhaiThu ds={sec.phai_thu_theo_han} chua_co_han={sec.phai_thu_chua_co_han}
      vi_sao={sec.phai_thu_vi_sao} />
    <KhoiPhaiTra ds={sec.phai_tra_theo_han} qua_han={sec.phai_tra_qua_han}
      chua_co_han={sec.phai_tra_chua_co_han} vi_sao={sec.phai_tra_vi_sao} />
    {/* KHỐI 06 · DÒNG TIỀN — bản vẽ đặt SAU hai khối công nợ và TRƯỚC Rủi ro trọng yếu.
        Bản vẽ vẽ nó thành một thẻ gọn với một câu "chưa đủ dữ liệu"; VTOS dựng thành bảng bốn mốc
        có trạng thái ba mức — đó là phương án dung hoà anh Tuấn chốt 13/9, giữ nguyên. Chỗ đứng
        thì lấy theo bản vẽ.

        Bản vẽ xếp Dòng tiền và Rủi ro CẠNH NHAU hai cột. VTOS xếp DỌC, vì thẻ dòng tiền của bản
        vẽ là một ô rỗng còn bảng của VTOS có bốn cột tiền: ép xuống nửa bề ngang thì bốn cột vỡ
        — đúng lỗi đã mất ba vòng để chữa ở khối Phải thu/Phải trả. */}
    <KhoiDongTien />
    <KhoiRuiRo ds={sec.rui_ro_trong_yeu} />
    <KhoiTienDoBaoCao ds={sec.tien_do_bao_cao} />


    {/* ══ PHẦN RIÊNG CỦA VTOS, KHÔNG CÓ TRONG BẢN VẼ ══════════════════════════════════════════
        Bốn khối dưới đây đang có SỐ THẬT và người dùng thật, nên không bỏ. Nhưng bản vẽ không có
        chúng, và trước vòng này chúng nằm CHEN GIỮA các khối của bản vẽ — đọc từ trên xuống ra
        một thứ tự khác hẳn. Nay xuống dưới, sau đường ngăn, để phần trên đúng bản vẽ. */}
    <hr className="mh01-ngan" />
    <h2 className="mh01-them">Thêm ngoài bản vẽ — khối riêng của VTOS</h2>
    <div className="grid">

      <div id="viec-cua-toi" className="panel"><h2>Việc cần xử lý</h2>
        {d.todo.length ? <ul>{d.todo.map((t: any, i: number) => <li key={i}><Link href={`/tours/${t.tour_id}`}>{t.code}</Link> – {t.name}: <b>{ACTION_LABEL[t.action] || t.action}</b></li>)}</ul> : <p className="muted">Không có việc chờ ở vai trò này.</p>}
        {d.pending_params > 0 && ["chutich", "tgd"].includes(user?.role || "") && <p><Link href="/params">{d.pending_params} tham số chính sách chờ ký</Link></p>}
      </div>
      {/* Bảng cảnh báo phẳng cũ đã thay bằng khối gom nhóm: sáu mươi dòng gần giống hệt nhau thì
          cuộn hết màn hình mà vẫn không cho biết tồn đọng nằm ở đâu. Danh sách từng dòng vẫn còn,
          nằm trong phần bung ra của khối. */}
      <KhoiTonDong ds={d.alerts || []} tong={k.canh_bao_do ?? null} />
    </div>
    <div className="grid" style={{ marginTop: 14 }}>
      {sec.kd_le && <div className="panel"><h2>Kinh doanh Lẻ – doanh thu tính chỉ tiêu tháng (quyết toán)</h2><p className="muted"><Link href="/sales-reports?mang=le">Báo cáo bán hàng phòng Lẻ →</Link></p>{sec.kd_le.length ? <div className="wrap"><table><tbody>{sec.kd_le.map((r: any) => <tr key={r.sales}><td>{r.sales}</td><td style={{ textAlign: "right" }}>{vnd(r.revenue)}</td><td>{Math.round(r.pct * 100)}% mốc {r.pct >= 1 ? <Tag cls="ok">đạt</Tag> : <Tag cls="warn">chưa</Tag>}</td></tr>)}</tbody></table></div> : <p className="muted">Chưa có chuyến quyết toán trong tháng.</p>}</div>}
      {sec.kd_doan && <div className="panel"><h2>Kinh doanh Đoàn (MICE) – lợi nhuận chia tháng (quyết toán)</h2>
        <p className="muted">Phòng Đoàn hưởng theo <b>chia lợi nhuận</b> chuyến đã quyết toán, không theo mốc doanh thu như phòng Lẻ – nên bảng này là lợi nhuận, không phải doanh thu. Số chính thức nằm ở bảng lương.</p>
        {sec.kd_doan.rows.length ? <div className="wrap"><table><tbody>{sec.kd_doan.rows.map((r: any) => <tr key={r.sales}><td>{r.sales}</td><td style={{ textAlign: "right" }}>{vnd(r.profit_share)}</td><td>{r.profit_share > 0 ? <Tag cls="ok">có lãi</Tag> : <Tag cls="red">lỗ</Tag>}</td></tr>)}</tbody></table></div>
          : <p className="muted">Chưa có chuyến đoàn quyết toán trong tháng.</p>}
        <p className="muted">{sec.kd_doan.so_chuyen} chuyến đoàn đã quyết toán trong tháng. <Link href="/sales-reports?mang=doan">Báo cáo bán hàng phòng Đoàn →</Link></p></div>}
      {sec.bao_cao_ngay && <div className="panel"><h2>Báo cáo ngày (Điều 12) – tháng này</h2><p>{sec.bao_cao_ngay.nhan_su} nhân sự · {sec.bao_cao_ngay.ngay_lam_viec} ngày làm việc · tỷ lệ nộp <b>{Math.round(sec.bao_cao_ngay.ty_le_nop * 100)}%</b> · thiếu 2 ngày liên tiếp: {sec.bao_cao_ngay.thieu_2_ngay}</p><Link href="/reports">Xem tổng hợp</Link></div>}
    </div>

    <p className="muted">Ngưỡng biên đang áp dụng {pct(d.threshold)} · Robot chạy mỗi 10 phút; CNTT có thể chạy tay ở trang Cảnh báo.</p>
  </>);
}
export default function Page() { return <Shell><Dash /></Shell>; }
