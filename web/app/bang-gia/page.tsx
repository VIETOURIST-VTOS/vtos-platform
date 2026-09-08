"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** V6 – Giá & chính sách bán.
 *
 *  Giá không phải một con số trên sản phẩm mà là một CHÍNH SÁCH CÓ THỜI HẠN: cao điểm khác thấp
 *  điểm, và khi tranh chấp thì câu hỏi là "ngày ấy giá niêm yết bao nhiêu". Giữ theo khoảng hiệu lực
 *  trả lời được câu đó; ghi đè một con số thì không.
 *
 *  Cột "Hiệu lực đến" để TRỐNG nghĩa là CÒN hiệu lực, không phải hết hạn hôm nay.
 */
type Dong = { id: number; hang_khach: string; mo_ta: string; gia_ban: number;
              gia_von: number | null; chiet_khau_toi_da: number };
type BG = { id: number; ma: string; ten: string; mang: string; hieu_luc_tu: string;
            hieu_luc_den: string | null; trang_thai: string; con_hieu_luc: boolean;
            ghi_chu: string; dong: Dong[] };

const vnd = (n: number) => (n || 0).toLocaleString("vi-VN") + " đ";

function BangGia() {
  const { user, toast } = useShell();
  const [ds, setDs] = useState<BG[]>([]);
  const [mang, setMang] = useState("");
  const datGia = ["gd_kd", "tp_kd", "ptgd_mkt", "tgd", "chutich", "cntt"].includes(user?.role || "");

  const load = useCallback(async () => {
    try { setDs(await api<BG[]>(`/ban-hang/bang-gia${mang ? `?mang=${mang}` : ""}`)); }
    catch (e) { toast(errMsg(e), true); }
  }, [mang, toast]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="wrap">
      <h1>Giá &amp; chính sách bán</h1>
      <p className="muted">
        Mỗi bảng giá là một chính sách <b>có thời hạn</b>, không phải một con số trên sản phẩm. Giá vốn
        nằm cùng dòng với giá bán vì cổng biên cần cả hai con số ở cùng một chỗ — để hai nơi thì mỗi
        lần ghép hụt là một lần cổng mở oan.
      </p>
      {!datGia ? (
        <p className="warn">
          Vai trò của anh/chị <b>xem</b> được bảng giá nhưng không đặt được. Giá niêm yết là chính sách
          bán; từng người đặt được thì nó không còn là chính sách.
        </p>
      ) : null}

      <div className="row">
        {[["", "Tất cả"], ["kd_le", "Lẻ"], ["kd_doan", "Đoàn"]].map(([k, t]) => (
          <button key={k} className={mang === k ? "" : "ghost"} onClick={() => setMang(k)}>{t}</button>
        ))}
      </div>

      {ds.length === 0 ? <p className="muted">Chưa có bảng giá nào.</p> : ds.map((b) => (
        <div className="card" key={b.id}>
          <div className="dau">
            <div>
              <b className="mono">{b.ma}</b> · {b.ten}
              <div className="muted small">
                {b.mang === "kd_doan" ? "Đoàn" : "Lẻ"} · hiệu lực từ {b.hieu_luc_tu}
                {b.hieu_luc_den ? ` đến ${b.hieu_luc_den}` : ""}
              </div>
            </div>
            {b.con_hieu_luc ? <Tag cls="ok">còn hiệu lực</Tag> : <Tag>có hạn kết thúc</Tag>}
          </div>
          <table className="tbl">
            <thead><tr><th>Hạng khách</th><th>Diễn giải</th>
              <th style={{ textAlign: "right" }}>Giá bán</th>
              <th style={{ textAlign: "right" }}>Giá vốn</th>
              <th style={{ textAlign: "right" }}>Chiết khấu tối đa</th></tr></thead>
            <tbody>
              {b.dong.map((d) => (
                <tr key={d.id}>
                  <td>{d.hang_khach}</td><td className="muted">{d.mo_ta}</td>
                  <td style={{ textAlign: "right" }}>{vnd(d.gia_ban)}</td>
                  <td style={{ textAlign: "right" }}>
                    {d.gia_von === null ? <Tag cls="warn">chưa có</Tag> : vnd(d.gia_von)}</td>
                  <td style={{ textAlign: "right" }}>{(d.chiet_khau_toi_da * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {b.ghi_chu ? <p className="muted small">{b.ghi_chu}</p> : null}
        </div>
      ))}

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1150px; }
        .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin: 14px 0; }
        .dau { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
               margin-bottom: 8px; }
        .row { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid #f1f5f9; padding: 6px 8px; text-align: left; }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid #0f172a;
                 background: #0f172a; color: #fff; cursor: pointer; font-size: 13px; }
        button.ghost { background: #fff; color: #0f172a; border-color: #cbd5e1; }
        .muted { color: #64748b; }
        .small { font-size: 12px; }
        .warn { color: #92400e; background: #fffbeb; padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() { return <Shell><BangGia /></Shell>; }
