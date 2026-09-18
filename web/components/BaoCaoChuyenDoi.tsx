"use client";
import { vnd, pct, fmtD } from "@/lib/api";
import { Tag } from "@/components/ui";

/** BẢNG LEAD → CHUYỂN ĐỔI — MỘT ĐẦU, HAI NƠI GỌI (18/9/2026)
 *
 *  Bảng này trước đây được viết TAY ở `app/leads/page.tsx`. Nay không gian Marketing cũng cần đúng
 *  bảng ấy, và chép sang là có hai đầu: sửa một chỗ thì chỗ kia lặng lẽ hiện số theo quy tắc cũ. Đã
 *  có ba tai nạn kiểu đó trong dự án này, nên bảng được rút ra đây và CẢ HAI màn hình cùng gọi.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════════
 *  BỐN CHỖ MÀN HÌNH PHẢI NÓI RA, vì PR #94 đã sửa ở phía sổ (backend/app/services/leads.py):
 *  ═══════════════════════════════════════════════════════════════════════════════════════════════
 *
 *  1. MẪU SỐ LẤY TỪ ĐÂU. Trước 18/9 mẫu số là `max(khai_báo, đếm_được)` — chọn con số lớn hơn mà
 *     không nói đã chọn cái nào. Nay sổ trả về `nguon_mau_so`, và bảng PHẢI in nó ra: một tỷ lệ
 *     không truy được về mẫu số là một tỷ lệ không kiểm được.
 *
 *  2. HAI TỶ LỆ, HAI TÊN, KHÔNG ĐƯỢC GỘP.
 *       `rate`                – bảng chéo của CHÍNH báo cáo này: lead kỳ X chốt tour KHỞI HÀNH
 *                               trong tháng T. Có ích riêng, nhưng không phải tỷ lệ của phòng.
 *       `ty_le_chot_overview` – QUY TẮC CHỦ TỊCH KÝ 14/9/2026 (`overview-v1`): nhóm theo kỳ phát
 *                               sinh lead, tử số gồm CẢ phần chốt ở các kỳ SAU.
 *     Hai cột riêng, hai nhãn riêng. In chung một cột "Tỷ lệ chốt" là cách chắc chắn nhất để hai
 *     người đọc hai nghĩa khác nhau mà không ai biết.
 *
 *  3. CHƯA ĐỐI CHIẾU LÀ **CHƯA XÁC ĐỊNH**, KHÔNG PHẢI 0%. Sổ trả `null` chứ không trả 0 khi chưa ai
 *     chạy đối chiếu lead ↔ booking. `tyLe()` bên dưới giữ đúng sự khác biệt ấy: 0% đọc ra là "chạy
 *     mà không ra khách", chưa xác định đọc ra là "chưa ai so sổ". Ép `null` thành 0 ở tầng giao
 *     diện là xoá mất lời cảnh báo mà tầng dưới vừa nhọc công dựng lên.
 *
 *  4. TỶ LỆ THEO overview-v1 CÒN TĂNG SAU KHI KỲ ĐÃ ĐÓNG — lead tháng 7 có thể chốt vào tháng 9.
 *     Nên mọi chỗ in con số ấy phải kèm `tinh_den_ngay`. In nó như một con số cuối cùng là hứa một
 *     điều không đúng, và tháng sau cùng một kỳ ra số khác thì người đọc tưởng có ai sửa sổ.
 */

/** null/undefined KHÁC 0. Xem ghi chú 3 ở trên — đây là chỗ giữ sự khác biệt ấy. */
export const tyLe = (x: number | null | undefined) =>
  x === null || x === undefined ? <span className="muted">chưa xác định</span> : <>{pct(x)}</>;

const NGUON: Record<string, string> = { khai_bao: "Khai báo", dem_duoc: "Đếm được" };

/** Cột LỆCH: chênh giữa lời khai của Marketing và số điện thoại đếm được trong sổ. Hiện ra, không
 *  san phẳng — lệch lớn nghĩa là tệp nguồn chỉ có phần chi tiết của vài kênh, đó là việc còn thiếu
 *  chứ không phải một con số để dùng. */
const Lech = ({ v }: { v: number | null | undefined }) => {
  if (v === null || v === undefined) return <span className="muted">—</span>;
  if (v === 0) return <span className="muted">0</span>;
  return <Tag cls="warn">{v > 0 ? "+" : ""}{v}</Tag>;
};

export default function BaoCaoChuyenDoi({ rep }: { rep: any }) {
  if (!rep) return <p className="muted">Chưa có số liệu.</p>;
  const tinhDen = rep.tinh_den_ngay || rep.as_of;

  return (<>
    {/* DÒNG KHAI QUY TẮC. Phải đứng TRƯỚC bảng: đọc xong con số rồi mới biết nó theo luật nào thì
        đã muộn — người ta đã ghi con số vào đầu rồi. */}
    <p className="muted">
      Tỷ lệ chốt theo quy tắc <b>{rep.quy_tac_ty_le_chot || "—"}</b> (Chủ tịch ký 14/9/2026)
      {tinhDen && <> · tính đến <b>{fmtD(String(tinhDen))}</b></>}
      {" "}— con số này <b>còn tăng</b> sau khi kỳ đã đóng, vì lead kỳ trước vẫn có thể chốt ở kỳ sau.
    </p>

    {(rep.canh_bao || []).map((c: string, i: number) => (
      <div className="panel" key={i} style={{ borderColor: "var(--vtos-warning)" }}>
        <b>⚠ {c}</b>
      </div>
    ))}

    <h2>1. Lead tháng {rep.target_month} → tour khởi hành tháng {rep.target_month}, theo kênh</h2>
    <div className="wrap"><table>
      <thead><tr>
        <th>Kênh</th>
        <th>Nguồn mẫu số</th>
        <th className="num">Mẫu số</th>
        <th className="num">SĐT đếm được</th>
        <th className="num">Lệch</th>
        <th className="num">Chốt trong kỳ</th>
        <th className="num">Tỷ lệ bảng chéo</th>
        <th className="num">Chốt mọi lúc</th>
        <th className="num">Tỷ lệ {rep.quy_tac_ty_le_chot || "đã ký"}</th>
        <th className="num">Khách mới</th>
        <th className="num">Quay lại</th>
        <th className="num">DT lũy kế</th>
        <th className="num">DT booking đã chốt</th>
        <th className="num">Chi phí / lead</th>
      </tr></thead>
      <tbody>
        {(rep.by_channel_current || []).map((c: any, i: number) => <tr key={i}>
          <td>{c.channel}</td>
          <td className="muted">{NGUON[c.nguon_mau_so] || c.nguon_mau_so}</td>
          <td className="num">{c.leads}</td>
          <td className="num">{c.so_sdt}</td>
          <td className="num"><Lech v={c.lech_khai_bao} /></td>
          <td className="num">{c.converted}</td>
          <td className="num">{pct(c.rate)}</td>
          <td className="num">{c.chot_moi_luc}</td>
          <td className="num"><b>{tyLe(c.ty_le_chot_overview)}</b></td>
          <td className="num">{c.new}</td>
          <td className="num">{c.returning}</td>
          <td className="num">{vnd(c.revenue)}</td>
          <td className="num">{vnd(c.doanh_thu_booking_chot)}</td>
          <td className="num">{c.cost_per_lead ? vnd(c.cost_per_lead) : "—"}</td>
        </tr>)}
        {rep.total_current && <tr>
          <td><b>TỔNG</b></td>
          <td className="muted">—</td>
          <td className="num"><b>{rep.total_current.leads}</b></td>
          <td className="num"><b>{rep.total_current.so_sdt}</b></td>
          <td className="num">—</td>
          <td className="num"><b>{rep.total_current.converted}</b></td>
          <td className="num"><b>{pct(rep.total_current.rate)}</b></td>
          <td className="num"><b>{rep.total_current.chot_moi_luc}</b></td>
          <td className="num"><b>{tyLe(rep.total_current.ty_le_chot_overview)}</b></td>
          <td colSpan={5}></td>
        </tr>}
      </tbody>
    </table></div>
    {/* Dòng TỔNG không phải tổng của các dòng kênh: một người liên hệ qua hai kênh trong cùng tháng
        là MỘT số điện thoại. Nói ra để không ai đi cộng tay rồi tưởng bảng sai. */}
    <p className="muted">Dòng <b>TỔNG</b> đếm trên tập số điện thoại, <b>không</b> cộng dồn từng
      kênh — một người liên hệ qua hai kênh trong cùng tháng vẫn là một người.</p>

    <h2>2. Lead các tháng → tour khởi hành tháng {rep.target_month}</h2>
    <div className="wrap"><table>
      <thead><tr>
        <th>Tháng lead</th>
        <th className="num">Mẫu số</th>
        <th className="num">SĐT đếm được</th>
        <th className="num">Chốt trong kỳ</th>
        <th className="num">Tỷ lệ bảng chéo</th>
        <th className="num">Chốt mọi lúc</th>
        <th className="num">Tỷ lệ {rep.quy_tac_ty_le_chot || "đã ký"}</th>
        <th className="num">Khách mới</th>
        <th className="num">Quay lại</th>
        <th className="num">DT lũy kế</th>
      </tr></thead>
      <tbody>{(rep.by_month || []).map((m: any) => <tr key={m.lead_month}>
        <td>{m.lead_month}</td>
        <td className="num">{m.leads}</td>
        <td className="num">{m.so_sdt}</td>
        <td className="num">{m.converted}</td>
        <td className="num">{pct(m.rate)}</td>
        <td className="num">{m.chot_moi_luc}</td>
        <td className="num"><b>{tyLe(m.ty_le_chot_overview)}</b></td>
        <td className="num">{m.new}</td>
        <td className="num">{m.returning}</td>
        <td className="num">{vnd(m.revenue)}</td>
      </tr>)}</tbody>
    </table></div>

    <h2>3. Kênh × tháng lead</h2>
    <div className="wrap"><table>
      <thead><tr>
        <th>Kênh</th><th>Tháng lead</th>
        <th>Nguồn mẫu số</th>
        <th className="num">Mẫu số</th>
        <th className="num">SĐT đếm được</th>
        <th className="num">Lệch</th>
        <th className="num">Chốt trong kỳ</th>
        <th className="num">Tỷ lệ bảng chéo</th>
        <th className="num">Tỷ lệ {rep.quy_tac_ty_le_chot || "đã ký"}</th>
        <th className="num">DT lũy kế</th>
      </tr></thead>
      <tbody>{(rep.by_channel_month || []).map((a: any, i: number) => <tr key={i}>
        <td>{a.channel}</td><td>{a.lead_month}</td>
        <td className="muted">{NGUON[a.nguon_mau_so] || a.nguon_mau_so}</td>
        <td className="num">{a.leads}</td>
        <td className="num">{a.so_sdt}</td>
        <td className="num"><Lech v={a.lech_khai_bao} /></td>
        <td className="num">{a.converted}</td>
        <td className="num">{pct(a.rate)}</td>
        <td className="num"><b>{tyLe(a.ty_le_chot_overview)}</b></td>
        <td className="num">{vnd(a.revenue)}</td>
      </tr>)}</tbody>
    </table></div>

    <h2>Chi tiết số điện thoại đã chốt ({(rep.detail || []).length})</h2>
    <div className="wrap"><table>
      <thead><tr>
        <th>Kênh</th><th>Tháng lead</th><th>SĐT</th><th>Khách</th><th>Tour</th><th>Khởi hành</th>
        <th>Phân loại</th><th className="num">Lần đi</th><th className="num">Khách</th>
        <th className="num">DT lũy kế</th><th className="num">DT booking này</th><th>Sale</th>
      </tr></thead>
      <tbody>{(rep.detail || []).map((d: any, i: number) => <tr key={i}>
        <td>{d.channel}</td><td>{d.lead_month}</td><td>{d.phone}</td><td>{d.name}</td>
        <td>{d.tour_code}<div className="muted">{d.tour}</div></td>
        <td>{fmtD(d.start_date)}</td>
        <td><Tag cls={d.kind === "Khách mới" ? "ok" : "navy"}>{d.kind}</Tag></td>
        <td className="num">{d.trips}</td><td className="num">{d.pax}</td>
        <td className="num">{vnd(d.revenue)}</td>
        <td className="num">{vnd(d.doanh_thu_booking_chot)}</td>
        <td>{d.sales}</td>
      </tr>)}</tbody>
    </table></div>
  </>);
}
