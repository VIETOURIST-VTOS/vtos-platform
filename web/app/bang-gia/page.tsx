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
  // Biểu ĐẶT GIÁ NIÊM YẾT. Trước 09/9 màn hình này chỉ liệt kê – POST /ban-hang/bang-gia đã có mà
  // không màn hình nào gọi, đúng cùng một chỗ hở với cửa nhập tay một dòng. Bộ kiểm cửa nhập của làn
  // Kiểm soát bắt được, và bắt đúng: một bảng giá không nhập được ở đâu thì phòng Kinh doanh vẫn
  // phải giữ giá trong một tệp Excel riêng, tức là hệ thống không phải nơi giữ giá.
  const RONG_DONG = { hang_khach: "nguoi_lon", mo_ta: "", gia_ban: 0, gia_von: null as number | null,
                      chiet_khau_toi_da: 0 };
  const [bieu, setBieu] = useState<any>(null);
  const [dang, setDang] = useState(false);

  const moBieu = () => setBieu({ ten: "", mang: mang || "kd_le", hieu_luc_tu: "", hieu_luc_den: "",
                                 ghi_chu: "", dong: [{ ...RONG_DONG }] });

  const luu = async () => {
    if (!bieu.ten.trim() || !bieu.hieu_luc_tu) { toast("Thiếu tên bảng giá hoặc ngày hiệu lực từ", true); return; }
    setDang(true);
    try {
      const r = await api<any>("/ban-hang/bang-gia", { method: "POST", json: {
        ten: bieu.ten.trim(), mang: bieu.mang, hieu_luc_tu: bieu.hieu_luc_tu,
        // Để TRỐNG nghĩa là CÒN hiệu lực. Gửi ngày hôm nay cho "gọn" là tự tắt bảng giá sau một đêm.
        hieu_luc_den: bieu.hieu_luc_den || null, ghi_chu: bieu.ghi_chu,
        dong: bieu.dong.filter((d: any) => d.mo_ta || d.gia_ban).map((d: any) => ({
          hang_khach: d.hang_khach, mo_ta: d.mo_ta,
          gia_ban: Number(d.gia_ban) || 0,
          // Giá vốn để trống giữ nguyên là RỖNG suốt đường đi – thiếu giá vốn không phải giá vốn 0.
          gia_von: d.gia_von === null || d.gia_von === "" ? null : Number(d.gia_von),
          chiet_khau_toi_da: Number(d.chiet_khau_toi_da) || 0 })) } });
      toast(r.message || "Đã đặt bảng giá"); setBieu(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

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

      {datGia ? (
        <div className="row">
          <button onClick={moBieu}>Đặt bảng giá mới</button>
          {bieu ? <button className="ghost" onClick={() => setBieu(null)}>Đóng biểu</button> : null}
        </div>
      ) : null}

      {bieu ? (
        <div className="card">
          <h3>Đặt một bảng giá</h3>
          <p className="muted small">
            Bảng giá mới KHÔNG xoá bảng cũ. Muốn đổi giá thì đặt bảng mới với ngày hiệu lực sau, và
            đặt hạn kết thúc cho bảng cũ — có thế thì câu hỏi “ngày ấy giá niêm yết bao nhiêu” mới
            còn trả lời được.
          </p>
          <div className="luoi">
            <label>Tên bảng giá <span className="do">*</span>
              <input value={bieu.ten} placeholder="Giá hè 2026 – tuyến miền Trung"
                     onChange={(e) => setBieu({ ...bieu, ten: e.target.value })} /></label>
            <label>Mảng
              <select value={bieu.mang} onChange={(e) => setBieu({ ...bieu, mang: e.target.value })}>
                <option value="kd_le">Lẻ</option><option value="kd_doan">Đoàn (MICE)</option>
              </select></label>
            <label>Hiệu lực từ <span className="do">*</span>
              <input type="date" value={bieu.hieu_luc_tu}
                     onChange={(e) => setBieu({ ...bieu, hieu_luc_tu: e.target.value })} /></label>
            <label>Hiệu lực đến (để trống = còn hiệu lực)
              <input type="date" value={bieu.hieu_luc_den}
                     onChange={(e) => setBieu({ ...bieu, hieu_luc_den: e.target.value })} /></label>
          </div>

          <b>Dòng giá</b>
          <table className="tbl">
            <thead><tr><th>Hạng khách</th><th>Diễn giải</th>
              <th style={{ width: 140 }}>Giá bán</th><th style={{ width: 140 }}>Giá vốn</th>
              <th style={{ width: 110 }}>Chiết khấu tối đa</th><th></th></tr></thead>
            <tbody>{bieu.dong.map((d: any, i: number) => {
              const dat = (k: string, v: any) => setBieu({ ...bieu,
                dong: bieu.dong.map((x: any, j: number) => j === i ? { ...x, [k]: v } : x) });
              return (<tr key={i}>
                <td><select value={d.hang_khach} onChange={(e) => dat("hang_khach", e.target.value)}>
                  {["nguoi_lon", "tre_em", "em_be", "phu_thu_phong_don"].map((h) =>
                    <option key={h} value={h}>{h}</option>)}
                </select></td>
                <td><input value={d.mo_ta} onChange={(e) => dat("mo_ta", e.target.value)} /></td>
                <td><input type="number" value={d.gia_ban}
                           onChange={(e) => dat("gia_ban", e.target.value)} /></td>
                <td><input type="number" placeholder="chưa có"
                           value={d.gia_von === null ? "" : d.gia_von}
                           onChange={(e) => dat("gia_von", e.target.value === "" ? null : e.target.value)} /></td>
                <td><input type="number" value={d.chiet_khau_toi_da}
                           onChange={(e) => dat("chiet_khau_toi_da", e.target.value)} /></td>
                <td><button className="ghost" onClick={() => setBieu({ ...bieu,
                      dong: bieu.dong.length > 1
                        ? bieu.dong.filter((_: any, j: number) => j !== i) : bieu.dong })}>Xóa</button></td>
              </tr>);
            })}</tbody>
          </table>
          <div className="row">
            <button className="ghost"
                    onClick={() => setBieu({ ...bieu, dong: [...bieu.dong, { ...RONG_DONG }] })}>Thêm dòng</button>
            <span className="muted small">Ô giá vốn để trống nghĩa là <b>chưa có giá vốn</b> — không
              phải bằng 0. Báo giá lấy dòng từ đây sẽ chép nguyên cái trống ấy sang.</span>
          </div>
          <div className="row">
            <button disabled={dang} onClick={luu}>{dang ? "Đang lưu…" : "Đặt bảng giá"}</button>
          </div>
        </div>
      ) : null}

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
        .card { border: 1px solid var(--vtos-line); border-radius: 10px; padding: 14px; margin: 14px 0; }
        .dau { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
               margin-bottom: 8px; }
        .row { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid var(--vtos-line); padding: 6px 8px; text-align: left; }
        .luoi { display: grid; gap: 0 14px; grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); }
        label { display: block; font-size: 12px; color: var(--vtos-text-mute); margin-top: 8px; }
        input, select { width: 100%; padding: 5px 7px; border: 1px solid var(--vtos-line); border-radius: 6px;
                        font-size: 13px; color: var(--vtos-text); background: var(--vtos-card); }
        .do { color: var(--vtos-danger); }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid var(--vtos-sky);
                 background: var(--vtos-sky); color: var(--vtos-text-on-navy); cursor: pointer; font-size: 13px; }
        button.ghost { background: var(--vtos-card); color: var(--vtos-text); border-color: var(--vtos-line); }
        .muted { color: var(--vtos-text-mute); }
        .small { font-size: 12px; }
        .warn { color: var(--vtos-warning); background: var(--vtos-warning-bg); padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() { return <Shell><BangGia /></Shell>; }
