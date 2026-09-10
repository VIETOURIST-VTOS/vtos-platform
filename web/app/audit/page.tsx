"use client";
/** Nhật ký nghiệp vụ – màn hình CHỈ XEM.
 *
 *  Không có, và không được có, một lời gọi ghi nào ở đây: mọi thao tác ghi ở màn hình khác đều để lại
 *  một dòng tại đây, nên màn hình này mà ghi được thì nhật ký thôi là nhật ký. Bộ kiểm cửa nhập
 *  (backend/tests/test_man_hinh_co_cua_nhap.py) canh đúng điều đó và sẽ đỏ nếu ai thêm nút lưu.
 *
 *  Việc lọc chạy ở MÁY CHỦ. Lọc trên vài trăm dòng đã tải về thì bản ghi của tháng trước chưa từng rời
 *  khỏi cơ sở dữ liệu, và câu hỏi thật của một cuộc kiểm toán – "ai đã sửa chứng từ này" – không trả
 *  lời được. */
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Gate, Tag, errMsg } from "@/components/ui";

const RONG = { actor: "", action: "", entity: "", tu: "", den: "", limit: "300" };

function Audit() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [f, setF] = useState<any>({ ...RONG });
  const [dang, setDang] = useState(false);
  const [mo, setMo] = useState<number | null>(null);

  const load = useCallback(() => {
    const q = new URLSearchParams(Object.entries(f).filter(([, v]) => v) as any).toString();
    setDang(true);
    api("/audit" + (q ? `?${q}` : ""))
      .then(setD)
      .catch((e) => toast(errMsg(e), true))
      .finally(() => setDang(false));
  }, [f]); // eslint-disable-line
  useEffect(load, [load]);

  const dm = d?.danh_muc || { actor: [], action: [], entity: [] };
  const rows = d?.rows || [];

  return (<>
    <h1>Nhật ký nghiệp vụ</h1>
    <p className="muted">Sổ thao tác <b>bất biến</b> do hệ thống tự ghi — mỗi lần ai đó ghi dữ liệu ở màn hình khác thì
      để lại một dòng ở đây, nối chuỗi bằng mã băm. Màn hình này <b>chỉ xem</b>, không có ô nhập nào: số liệu vào hệ
      thống ở màn hình của từng phân hệ. Cần hồ sơ giao cho kiểm toán viên thì mở
      mục <b>Hồ sơ kiểm toán</b> ở nhóm Tài chính &amp; Kế toán — đó là việc khác.</p>

    {d && <Gate ok={d.chain_ok}>Kiểm tra chuỗi mã băm (R9): <b>{d.chain_message}</b> · {d.records} bản ghi trong sổ.
      Mọi sửa đổi trực tiếp vào cơ sở dữ liệu làm chuỗi đứt và bị phát hiện tại đây.</Gate>}

    <div className="panel">
      <div className="grid">
        <label>Người thực hiện<select value={f.actor} onChange={(e) => setF({ ...f, actor: e.target.value })}>
          <option value="">— tất cả —</option>
          {dm.actor.map((x: string) => <option key={x} value={x}>{x}</option>)}</select></label>
        <label>Hành động<select value={f.action} onChange={(e) => setF({ ...f, action: e.target.value })}>
          <option value="">— tất cả —</option>
          {dm.action.map((x: string) => <option key={x} value={x}>{x}</option>)}</select></label>
        <label>Đối tượng <i className="muted">(theo tiền tố: chọn phân hệ ra cả phân hệ)</i>
          <select value={f.entity} onChange={(e) => setF({ ...f, entity: e.target.value })}>
            <option value="">— tất cả —</option>
            {dm.entity.map((x: string) => <option key={x} value={x}>{x}</option>)}</select></label>
        <label>Từ ngày<input type="date" value={f.tu} onChange={(e) => setF({ ...f, tu: e.target.value })} /></label>
        <label>Đến ngày<input type="date" value={f.den} onChange={(e) => setF({ ...f, den: e.target.value })} /></label>
        <label>Số dòng tối đa<select value={f.limit} onChange={(e) => setF({ ...f, limit: e.target.value })}>
          {["100", "300", "1000", "5000"].map((x) => <option key={x} value={x}>{x}</option>)}</select></label>
      </div>
      <button className="act grey" onClick={() => setF({ ...RONG })}>Bỏ mọi bộ lọc</button>
      <span className="muted"> {dang ? "Đang đọc sổ…" : `Đang hiện ${rows.length} dòng`}
        {rows.length >= Number(f.limit) && !dang && " — đã chạm mức tối đa, hãy thu hẹp khoảng thời gian hoặc nâng số dòng"}</span>
    </div>

    <div className="panel wrap"><table><thead><tr>
      <th>#</th><th>Lúc</th><th>Ai</th><th>Hành động</th><th>Đối tượng</th><th>Mã băm</th><th></th>
    </tr></thead><tbody>
      {rows.map((l: any) => [
        <tr key={l.id}>
          <td>{l.id}</td>
          <td>{fmtDT(l.ts)}</td>
          <td>{l.actor}<div className="muted">{l.role}</div></td>
          <td>{l.action}</td>
          <td className="mono">{l.entity}</td>
          <td className="mono">{(l.hash || "").slice(0, 12)}</td>
          <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => setMo(mo === l.id ? null : l.id)}>{mo === l.id ? "Ẩn" : "Trước / sau"}</button></td>
        </tr>,
        mo === l.id && <tr key={l.id + "d"}><td colSpan={7} style={{ background: "var(--bg2)" }}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 320px" }}>
              <b>Trước</b> {l.before ? null : <Tag cls="grey">bản ghi mới, chưa có trạng thái trước</Tag>}
              <pre className="mono" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{l.before ? JSON.stringify(l.before, null, 2) : ""}</pre>
            </div>
            <div style={{ flex: "1 1 320px" }}>
              <b>Sau</b> {l.after ? null : <Tag cls="grey">thao tác không đổi dữ liệu</Tag>}
              <pre className="mono" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{l.after ? JSON.stringify(l.after, null, 2) : ""}</pre>
            </div>
          </div>
          <p className="muted mono">Mã băm đầy đủ: {l.hash}</p>
        </td></tr>,
      ])}
    </tbody></table>
    {!dang && rows.length === 0 && <p className="muted">Không có dòng nào khớp bộ lọc.</p>}
    </div>
  </>);
}
export default function Page() { return <Shell><Audit /></Shell>; }
