"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Gate } from "@/components/ui";

function Audit() {
  const [d, setD] = useState<any>(null);
  useEffect(() => { api("/audit").then(setD); }, []);
  return (<>
    <h1>Nhật ký bất biến</h1>
    {d && <Gate ok={d.chain_ok}>Kiểm tra chuỗi hash (R9): <b>{d.chain_message}</b> · {d.records} bản ghi. Mọi sửa đổi trực tiếp vào CSDL làm chuỗi đứt và bị phát hiện tại đây.</Gate>}
    <div className="panel wrap"><table><thead><tr><th>#</th><th>Lúc</th><th>Ai</th><th>Hành động</th><th>Đối tượng</th><th>Sau</th><th>Hash</th></tr></thead>
      <tbody>{(d?.rows || []).map((l: any) => <tr key={l.id}><td>{l.id}</td><td>{fmtDT(l.ts)}</td><td>{l.actor} ({l.role})</td><td>{l.action}</td><td>{l.entity}</td><td className="muted mono">{JSON.stringify(l.after || "")}</td><td className="mono">{l.hash.slice(0, 12)}</td></tr>)}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Audit /></Shell>; }
