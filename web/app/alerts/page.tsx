"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

function Alerts() {
  const { user, toast } = useShell();
  const [rows, setRows] = useState<any[]>([]);
  const load = useCallback(() => api("/alerts").then(setRows), []);
  useEffect(() => { load(); }, [load]);
  const act = async (path: string) => { try { const r = await api(path, { method: "POST" }); toast(r.message); load(); } catch (x) { toast(errMsg(x), true); } };
  return (<>
    <h1>Cảnh báo robot (D-7, quá hạn quyết toán, SLA booking, Kế toán chậm, R4 cọc – deadline – bảo lưu, R9 bất thường)</h1>
    {["cntt", "tgd", "chutich"].includes(user?.role || "") && <button className="act orange" onClick={() => act("/robots/run")}>Chạy robot ngay</button>}
    {["cntt", "tgd", "chutich", "bks", "ketoan"].includes(user?.role || "") && <button className="act grey" onClick={async () => { try { const r = await api("/robot/r9", { method: "POST" }); toast(`R9: phát hiện ${r.found}, cảnh báo mới ${r.new_alerts}`); load(); } catch (x) { toast(errMsg(x), true); } }}>R9 – quét bất thường</button>}
    <div className="panel wrap"><table><thead><tr><th>Mức</th><th>Loại</th><th>Tham chiếu</th><th>Nội dung</th><th>Gửi vai trò</th><th>Lúc</th><th></th></tr></thead>
      <tbody>{rows.length ? rows.map((a) => <tr key={a.id} style={{ opacity: a.resolved ? 0.5 : 1 }}><td><Tag cls={a.level}>{a.level}</Tag></td><td>{a.kind}</td><td>{a.ref}</td><td>{a.message}</td><td className="muted">{a.to_roles}</td><td>{fmtDT(a.created_at)}</td>
        <td>{a.resolved ? "đã đóng" : <button className="act grey" style={{ margin: 0 }} onClick={() => act(`/alerts/${a.id}/resolve`)}>Đóng</button>}</td></tr>) : <tr><td colSpan={7} className="muted">Không có cảnh báo.</td></tr>}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Alerts /></Shell>; }
