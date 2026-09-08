"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** V6 – Hợp đồng khách: mắt xích giữa báo giá đã chốt và booking.
 *
 *  Số hợp đồng và ngày ký là thứ kiểm toán hỏi đầu tiên khi đối chiếu doanh thu, và trước V6 hệ thống
 *  không có chỗ nào giữ chúng.
 *
 *  Giá trị hợp đồng lấy từ BẢN BÁO GIÁ ĐÃ GỬI, không lấy từ bản đang soạn: khách chốt con số hôm ấy.
 */
type HD = { id: number; so_hop_dong: string; bao_gia_id: number | null; booking_id: number | null;
            khach_ten: string; khach_dai_dien: string; khach_ma_so_thue: string;
            ngay_ky: string | null; gia_tri: number; dat_coc: number;
            han_thanh_toan: string | null; trang_thai: string };

const vnd = (n: number) => (n || 0).toLocaleString("vi-VN") + " đ";
const pct = (n: number | null) => (n === null || n === undefined ? "–" : (n * 100).toFixed(1) + "%");

function HopDong() {
  const { toast } = useShell();
  const [ds, setDs] = useState<HD[]>([]);
  const [chuoi, setChuoi] = useState<Record<number, any>>({});

  const load = useCallback(async () => {
    try { setDs(await api<HD[]>("/ban-hang/hop-dong")); }
    catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const xemChuoi = async (id: number) => {
    if (chuoi[id]) { setChuoi({ ...chuoi, [id]: null }); return; }
    try { setChuoi({ ...chuoi, [id]: await api<any>(`/ban-hang/hop-dong/${id}/chuoi`) }); }
    catch (e) { toast(errMsg(e), true); }
  };

  return (
    <div className="wrap">
      <h1>Hợp đồng khách</h1>
      <p className="muted">
        Mắt xích giữa báo giá đã chốt và booking. Giá trị hợp đồng lấy từ <b>bản báo giá đã gửi</b>,
        không lấy từ bản đang soạn — khách chốt con số hôm ấy, và chênh lệch chỉ lộ ra lúc đối chiếu
        doanh thu vài tháng sau.
      </p>

      <div className="card">
        <h3>{ds.length} hợp đồng</h3>
        {ds.length === 0 ? <p className="muted">Chưa có hợp đồng nào.</p> : (
          <table className="tbl">
            <thead><tr><th>Số HĐ</th><th>Khách</th><th>MST</th><th>Ngày ký</th>
              <th style={{ textAlign: "right" }}>Giá trị</th>
              <th style={{ textAlign: "right" }}>Đặt cọc</th><th>Booking</th><th>Trạng thái</th><th></th></tr></thead>
            <tbody>
              {ds.map((h) => (
                <>
                  <tr key={h.id}>
                    <td className="mono">{h.so_hop_dong}</td>
                    <td><b>{h.khach_ten}</b>
                      {h.khach_dai_dien ? <div className="muted small">đại diện: {h.khach_dai_dien}</div> : null}</td>
                    <td className="mono">{h.khach_ma_so_thue || "–"}</td>
                    <td>{h.ngay_ky || <Tag cls="warn">chưa ký</Tag>}</td>
                    <td style={{ textAlign: "right" }}>{vnd(h.gia_tri)}</td>
                    <td style={{ textAlign: "right" }}>{vnd(h.dat_coc)}</td>
                    <td>{h.booking_id ? `#${h.booking_id}` : <Tag cls="warn">chưa nối</Tag>}</td>
                    <td>{h.trang_thai}</td>
                    <td><button className="ghost" onClick={() => xemChuoi(h.id)}>Trọn đường</button></td>
                  </tr>
                  {chuoi[h.id] ? (
                    <tr key={`${h.id}-chuoi`}><td colSpan={9} className="chitiet">
                      <div className="buoc">
                        {[["Bảng giá", chuoi[h.id].bang_gia && `${chuoi[h.id].bang_gia.ma} · ${chuoi[h.id].bang_gia.ten}`],
                          ["Báo giá", chuoi[h.id].bao_gia && `${chuoi[h.id].bao_gia.ma} · ${chuoi[h.id].bao_gia.trang_thai}`],
                          ["Bản đã gửi", chuoi[h.id].ban_da_gui &&
                            `lần ${chuoi[h.id].ban_da_gui.lan} · ${vnd(chuoi[h.id].ban_da_gui.tong_ban)} · biên ` +
                            (chuoi[h.id].ban_da_gui.du_co_so ? pct(chuoi[h.id].ban_da_gui.bien) : "chưa đủ cơ sở")],
                          ["Hợp đồng", `${h.so_hop_dong} · ${vnd(h.gia_tri)}`],
                          ["Booking", h.booking_id ? `#${h.booking_id}` : null],
                        ].map(([ten, gt]: any) => (
                          <div className={`o ${gt ? "co" : "thieu"}`} key={ten}>
                            <div className="ten">{ten}</div>
                            <div className="gt">{gt || "chưa có"}</div>
                          </div>
                        ))}
                      </div>
                      {chuoi[h.id].bao_gia?.duoi_bien ? (
                        <p className="warn">Báo giá này đã gửi khách <b>dưới ngưỡng biên</b> (biên lúc gửi{" "}
                          {pct(chuoi[h.id].bao_gia.bien_luc_gui)}) — có giải trình kèm theo ở màn hình Báo giá.</p>
                      ) : null}
                      {!chuoi[h.id].day_du ? (
                        <p className="warn">Chuỗi còn <b>đứt</b> — ô nào ghi “chưa có” là mắt xích còn thiếu.</p>
                      ) : null}
                    </td></tr>
                  ) : null}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1250px; }
        .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin: 14px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid #f1f5f9; padding: 6px 8px; text-align: left;
                           vertical-align: top; }
        .chitiet { background: #f8fafc; }
        .buoc { display: flex; gap: 10px; flex-wrap: wrap; margin: 6px 0 10px; }
        .o { border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; min-width: 150px; }
        .o.thieu { border-style: dashed; color: #92400e; background: #fffbeb; }
        .o .ten { font-size: 12px; color: #64748b; }
        .o .gt { font-weight: 600; font-size: 13px; }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid #cbd5e1;
                 background: #fff; color: #0f172a; cursor: pointer; font-size: 13px; }
        .muted { color: #64748b; }
        .small { font-size: 12px; }
        .warn { color: #92400e; background: #fffbeb; padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() { return <Shell><HopDong /></Shell>; }
