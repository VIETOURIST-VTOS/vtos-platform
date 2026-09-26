"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, pct } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Bàn bán tour lẻ – Phòng Kinh doanh Lẻ. Chủ tịch quyết 25/9/2026.
 *
 *  "Tour lẻ là do Phòng Điều hành tạo lịch khởi hành, sales lẻ chỉ việc bán."
 *  "Sales lẻ chỉ nhìn thấy dự toán 3 con số như trong file quyết toán tour của Điều hành."
 *
 *  KHÔNG CÓ NÚT NÀO TRÊN BẢNG NÀY. Bán một chỗ là việc phải mở chuyến ra đọc trước; một nút "đặt"
 *  cạnh một dòng tóm tắt là lời mời đặt mà chưa xem. Cửa bán nằm ở /requests, đã có từ đầu.
 *
 *  MÀN HÌNH KHÔNG TỰ TÍNH LẠI MỘT CON SỐ NÀO. Mọi số dưới đây do máy chủ gửi xuống nguyên vẹn từ
 *  `rules.calc`. Tính lại ở đây là dựng bản sao thứ hai của cổng biên, và bản sao nào rồi cũng lệch
 *  – lần này lệch theo hướng nguy hiểm nhất: người bán đọc một con biên, người duyệt đọc con khác.
 */

const CONG: Record<string, [string, string]> = {
  dat: ["ĐẠT biên", "ok"],
  khong_dat: ["DƯỚI biên", "warn"],
  chua_du_co_so: ["chưa đủ cơ sở tính", "grey"],
};

function BanTourLe() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [locSapDi, setLocSapDi] = useState(false);
  const load = useCallback(() => api("/ban-tour-le/ban-lam-viec").then(setD).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="muted">Đang tải…</p>;
  const T = d.tong || {};
  const rows = (d.rows || []).filter((r: any) => !locSapDi || r.days_left <= 7);

  return (<>
    <h1>Bàn bán tour lẻ</h1>
    <p className="muted">Chuyến lẻ <b>đang bán</b>, sắp theo ngày khởi hành gần nhất. Lịch khởi hành do Phòng Điều hành mở;
      bảng này để người bán biết chuyến nào còn chỗ và còn lời bao nhiêu trước khi trả lời khách.</p>

    <div className="kpis">
      <div className="kpi"><b>{T.chuyen}</b><span>Chuyến đang bán</span></div>
      <div className="kpi"><b>{T.cho_con}</b><span>Chỗ còn trống</span></div>
      <div className="kpi"><b style={{ color: T.sap_khoi_hanh ? "var(--orange)" : undefined }}>{T.sap_khoi_hanh}</b><span>Khởi hành trong 7 ngày</span></div>
      <div className="kpi"><b style={{ color: T.chua_hoa_von ? "var(--red)" : undefined }}>{T.chua_hoa_von}</b><span>Chưa bán đủ số khách hòa vốn</span></div>
      <div className="kpi"><b className="muted">{T.chua_du_co_so}</b><span>Chưa có dự toán riêng</span></div>
    </div>

    {/* Lời lưu ý do MÁY CHỦ gửi xuống, không viết cứng ở đây: màn hình có thể được viết lại, còn
        câu này là một phần của con số. */}
    <div className="gate">{d.luu_y}</div>

    <p><button className={"act " + (locSapDi ? "orange" : "grey")} onClick={() => setLocSapDi(!locSapDi)}>
      {locSapDi ? "Đang lọc: khởi hành trong 7 ngày" : "Chỉ xem chuyến khởi hành trong 7 ngày"}</button></p>

    <div className="panel wrap">
      <table>
        <thead><tr>
          <th>Chuyến</th><th>Khởi hành</th><th className="num">Chỗ</th>
          <th className="num">Giá bán</th><th className="num">Chi phí cố định</th><th className="num">Chi phí/khách</th>
          <th className="num">Hòa vốn</th><th className="num">Lợi nhuận kế hoạch</th><th className="num">Tại số đang bán</th><th>Cổng biên</th>
        </tr></thead>
        <tbody>{rows.length ? rows.map((r: any) => {
          const [nhan, mau] = CONG[r.trang_thai_cong] || [r.trang_thai_cong, "grey"];
          const chuaHoaVon = r.hoa_von_khach && r.cho_da_ban < r.hoa_von_khach;
          return <tr key={r.id}>
            <td><Link href={`/tours/${r.id}`}><b>{r.code}</b></Link><div className="muted">{r.name}</div></td>
            <td>{fmtD(r.start_date)}<div className="muted">{r.days_left <= 7 ? <Tag cls="orange">còn {r.days_left} ngày</Tag> : `còn ${r.days_left} ngày`}</div></td>
            <td className="num"><b>{r.cho_da_ban}</b>/{r.cho_mo_ban}<div className="muted">còn {r.cho_con}</div></td>
            <td className="num">{vnd(r.gia_ban)}</td>
            <td className="num">{r.chi_phi_co_dinh ? vnd(r.chi_phi_co_dinh) : <span className="muted">–</span>}</td>
            <td className="num">{r.chi_phi_theo_khach ? vnd(r.chi_phi_theo_khach) : <span className="muted">–</span>}</td>
            <td className="num">{r.hoa_von_khach ?? <span className="muted">–</span>}
              {chuaHoaVon && <div><Tag cls="red">thiếu {r.con_thieu_de_hoa_von}</Tag></div>}</td>
            {/* `null` KHÁC 0: chuyến chưa có dự toán riêng thì in chữ, không in số. Thiếu giá vốn
                mà hiện "0 đ · biên 100%" là đúng cái bệnh Ý kiến thẩm định 06/9/2026 đã bắt. */}
            <td className="num">{r.loi_nhuan_ke_hoach == null ? <span className="muted">chưa tính được</span>
              : <>{vnd(r.loi_nhuan_ke_hoach)}<div className="muted">biên {pct(r.bien_ke_hoach)}</div></>}</td>
            <td className="num">{r.loi_nhuan_tai_so_dang_ban == null ? <span className="muted">–</span>
              : <b style={{ color: r.loi_nhuan_tai_so_dang_ban < 0 ? "var(--red)" : undefined }}>{vnd(r.loi_nhuan_tai_so_dang_ban)}</b>}</td>
            <td><Tag cls={mau}>{nhan}</Tag>{r.duoi_bien && <div><Tag cls="warn">đã ký dưới biên</Tag></div>}
              {r.chi_tham_chieu && <div className="muted">số chỉ để tham chiếu</div>}</td>
          </tr>;
        }) : <tr><td colSpan={10} className="muted">Không có chuyến lẻ nào đang bán.</td></tr>}</tbody>
      </table>
    </div>

    <p className="muted"><b>Lợi nhuận kế hoạch</b> tính ở số khách dự toán; <b>tại số đang bán</b> tính ở số khách đã bán
      thật hôm nay. Hai số khác nhau chừng nào chuyến chưa bán đủ — đó là khoảng cách còn phải bán, không phải lỗi bảng.</p>
  </>);
}

export default function Page() { return <Shell><BanTourLe /></Shell>; }
