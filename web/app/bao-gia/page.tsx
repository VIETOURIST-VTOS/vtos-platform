"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** V6 – Báo giá. MỘT màn hình cho cả lẻ và đoàn, lọc bằng ?mang=.
 *
 *  Cổng biên đứng ở bước GỬI, không ở bước lưu nháp: nháp là chỗ để thử con số, chặn ở nháp thì sale
 *  không ước lượng được gì và cách lách rõ nhất là ghi một giá vốn bịa cho qua cổng. Cam kết với
 *  khách xảy ra lúc gửi, nên cổng đứng ở đó.
 *
 *  Màn hình cố ý hiện thẳng ba con số (bán · vốn · biên) ngay cạnh nút Gửi, kể cả khi chưa đủ cơ sở.
 *  Giấu chúng đi rồi chỉ báo lỗi lúc bấm là bắt người dùng đoán mình sai ở đâu.
 */
type Dong = { hang_khach: string; mo_ta: string; so_luong: number; don_gia: number;
              gia_von_don_vi: number | null; chiet_khau: number };
type BG = { id: number; ma: string; mang: string; khach_ten: string; khach_dien_thoai: string;
            so_khach: number; ngay_khoi_hanh: string | null; trang_thai: string; trang_thai_ten: string;
            duoi_bien: boolean; giai_trinh: string; bien_luc_gui: number | null; phien_ban: number;
            dong: Dong[]; ban_da_gui: any[]; cong_bien: any };

const vnd = (n: number) => (n || 0).toLocaleString("vi-VN") + " đ";
const pct = (n: number | null) => (n === null || n === undefined ? "–" : (n * 100).toFixed(1) + "%");

function BaoGia() {
  const { user, toast } = useShell();
  const [mang, setMang] = useState("kd_le");
  const [ds, setDs] = useState<BG[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [dang, setDang] = useState(false);
  const soan = ["nv_kd", "tn_kd", "tp_kd", "gd_kd", "ptgd_mkt", "tgd", "chutich", "cntt"]
    .includes(user?.role || "");

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("mang");
    if (q) setMang(q);
    api("/ban-hang/meta").then(setMeta).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    try { setDs(await api<BG[]>(`/ban-hang/bao-gia?mang=${mang}`)); }
    catch (e) { toast(errMsg(e), true); }
  }, [mang, toast]);
  useEffect(() => { load(); }, [load]);

  const gui = async (b: BG) => {
    const c = b.cong_bien;
    let giai_trinh = "";
    if (!c.du_co_so || !c.dat) {
      const nhac = c.du_co_so
        ? `Biên ${pct(c.bien)} dưới ngưỡng ${pct(c.nguong)}.`
        : `Chưa đủ cơ sở tính biên: ${c.dong_thieu_gia_von.length} dòng chưa có giá vốn.`;
      const ly_do = prompt(`${nhac}\n\nGửi vẫn được, nhưng phải giải trình (ít nhất ` +
                           `${meta?.dai_giai_trinh || 30} ký tự):\nvì sao chấp nhận · khoản nào làm ` +
                           `mỏng biên · bù bằng gì`);
      if (!ly_do || !ly_do.trim()) return;
      giai_trinh = ly_do.trim();
    }
    setDang(true);
    try {
      // Một lần bấm nút = một khóa. Bấm lại vì mạng chập không được thành hai cam kết với khách.
      const khoa = `bg-${b.id}-${b.phien_ban}-${Date.now()}`;
      const r = await api<any>(`/ban-hang/bao-gia/${b.id}/gui`,
                               { method: "POST", json: { giai_trinh }, headers: { "X-Khoa-Ghi": khoa } });
      toast(r.message || "Đã gửi khách");
      await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const hanh = async (b: BG, duong: string, xong: string) => {
    setDang(true);
    try { const r = await api<any>(`/ban-hang/bao-gia/${b.id}/${duong}`, { method: "POST", json: {} });
          toast(r.message || xong); await load(); }
    catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  return (
    <div className="wrap">
      <h1>Báo giá {mang === "kd_doan" ? "đoàn" : "lẻ"}</h1>
      <p className="muted">
        Cổng biên đứng ở bước <b>gửi khách</b>, vì cam kết xảy ra ở đó chứ không phải lúc lập dự toán.
        Thiếu giá vốn <b>không phải</b> giá vốn bằng 0 — không có giá vốn thì cổng không thể ĐẠT.
      </p>

      <div className="row">
        {[["kd_le", "Lẻ"], ["kd_doan", "Đoàn (MICE)"]].map(([k, t]) => (
          <button key={k} className={mang === k ? "" : "ghost"} onClick={() => setMang(k)}>{t}</button>
        ))}
        {meta ? <span className="muted small">Ngưỡng biên hiện hành: <b>{pct(meta.nguong_bien)}</b></span> : null}
      </div>

      <div className="card">
        <h3>{ds.length} báo giá</h3>
        {ds.length === 0 ? <p className="muted">Chưa có báo giá nào ở mảng này.</p> : (
          <table className="tbl">
            <thead><tr><th>Mã</th><th>Khách</th><th>Khách/số</th><th>Khởi hành</th>
              <th style={{ textAlign: "right" }}>Tổng bán</th><th>Biên</th><th>Trạng thái</th><th></th></tr></thead>
            <tbody>
              {ds.map((b) => {
                const c = b.cong_bien;
                return (
                  <>
                    <tr key={b.id}>
                      <td className="mono"><a onClick={() => setMo(mo === b.id ? null : b.id)}>{b.ma}</a></td>
                      <td><b>{b.khach_ten}</b><div className="muted small">{b.khach_dien_thoai}</div></td>
                      <td>{b.so_khach}</td>
                      <td>{b.ngay_khoi_hanh || "–"}</td>
                      <td style={{ textAlign: "right" }}>{vnd(c.tong_ban)}</td>
                      <td>
                        {!c.du_co_so ? <Tag cls="warn">chưa đủ cơ sở</Tag>
                          : c.dat ? <Tag cls="ok">{pct(c.bien)}</Tag>
                          : <Tag cls="red">{pct(c.bien)}</Tag>}
                        {b.duoi_bien ? <div className="muted small">đã gửi dưới biên</div> : null}
                      </td>
                      <td>{b.trang_thai_ten}</td>
                      <td className="nut">
                        {soan && ["nhap", "da_gui"].includes(b.trang_thai) &&
                          <button className="ghost" disabled={dang} onClick={() => gui(b)}>Gửi khách</button>}
                        {soan && b.trang_thai === "da_gui" &&
                          <button className="ghost" disabled={dang}
                                  onClick={() => hanh(b, "khach-chot", "Khách đã chốt")}>Khách chốt</button>}
                      </td>
                    </tr>
                    {mo === b.id ? (
                      <tr key={`${b.id}-chi-tiet`}><td colSpan={8} className="chitiet">
                        <b>Dòng báo giá</b>
                        <table className="tbl">
                          <thead><tr><th>Hạng khách</th><th>Diễn giải</th><th>SL</th>
                            <th style={{ textAlign: "right" }}>Đơn giá</th>
                            <th style={{ textAlign: "right" }}>Giá vốn</th></tr></thead>
                          <tbody>{b.dong.map((d, i) => (
                            <tr key={i}><td>{d.hang_khach}</td><td>{d.mo_ta}</td><td>{d.so_luong}</td>
                              <td style={{ textAlign: "right" }}>{vnd(d.don_gia)}</td>
                              <td style={{ textAlign: "right" }}>
                                {d.gia_von_don_vi === null
                                  ? <Tag cls="warn">chưa có</Tag> : vnd(d.gia_von_don_vi)}</td></tr>))}
                          </tbody>
                        </table>
                        {b.giai_trinh ? <p className="warn"><b>Giải trình khi gửi dưới biên:</b> {b.giai_trinh}</p> : null}
                        <b>Các bản đã gửi khách</b>
                        {b.ban_da_gui.length === 0 ? <p className="muted">Chưa gửi lần nào.</p> : (
                          <table className="tbl">
                            <thead><tr><th>Lần</th><th>Lúc</th><th>Người gửi</th>
                              <th style={{ textAlign: "right" }}>Tổng bán</th><th>Biên</th></tr></thead>
                            <tbody>{b.ban_da_gui.map((v: any) => (
                              <tr key={v.id}><td>{v.lan}</td><td>{v.gui_luc}</td><td>{v.gui_boi}</td>
                                <td style={{ textAlign: "right" }}>{vnd(v.tong_ban)}</td>
                                <td>{v.du_co_so ? pct(v.bien) : "chưa đủ cơ sở"}</td></tr>))}
                            </tbody>
                          </table>
                        )}
                        <p className="muted small">
                          Bản đã gửi là bản <b>đóng băng</b> — sửa báo giá không làm nó đổi theo, vì câu
                          hỏi lúc tranh chấp là “hôm ấy ta hứa với khách bao nhiêu”.
                        </p>
                      </td></tr>
                    ) : null}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1250px; }
        .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin: 14px 0; }
        .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 12px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid #f1f5f9; padding: 6px 8px; text-align: left;
                           vertical-align: top; }
        .chitiet { background: #f8fafc; }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        .mono a { cursor: pointer; text-decoration: underline; }
        .nut { white-space: nowrap; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid #0f172a;
                 background: #0f172a; color: #fff; cursor: pointer; margin-right: 6px; font-size: 13px; }
        button.ghost { background: #fff; color: #0f172a; border-color: #cbd5e1; }
        button:disabled { opacity: .5; cursor: default; }
        .muted { color: #64748b; }
        .small { font-size: 12px; }
        .warn { color: #92400e; background: #fffbeb; padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() { return <Shell><BaoGia /></Shell>; }
