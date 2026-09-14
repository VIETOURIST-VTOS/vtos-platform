"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, Gate, errMsg } from "@/components/ui";

const CH: Record<string, string> = { facebook: "Facebook", zalo: "Zalo OA", web: "Web", vchat: "VCHAT" };
const ST: Record<string, [string, string]> = { cho_sale: ["Chờ sale", "warn"], mo: ["Đang mở", "ok"], ai_da_tra_loi: ["AI đã trả lời", "navy"], dong: ["Đã đóng", ""] };

function Inbox() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [st, setSt] = useState<any>({}); const [rows, setRows] = useState<any[]>([]); const [cur, setCur] = useState<any>(null);
  const [filter, setFilter] = useState(""); const [channel, setChannel] = useState(""); const [mine, setMine] = useState(false);
  const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const [tick, setTick] = useState(0);
  const bottom = useRef<HTMLDivElement>(null);
  const load = useCallback(() => { api("/inbox/status").then(setSt).catch(() => {}); api(`/inbox?status=${filter}&channel=${channel}&mine=${mine}`).then(setRows).catch((e) => toast(errMsg(e), true)); }, [filter, channel, mine, toast]);
  const open = useCallback((id: number) => api(`/inbox/${id}`).then((c) => { setCur(c); setTimeout(() => bottom.current?.scrollIntoView(), 50); }).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load, tick]);
  useEffect(() => { const t = setInterval(() => { setTick((x) => x + 1); if (cur) open(cur.id); }, 20000); return () => clearInterval(t); }, [cur, open]);
  const send = async () => { if (!cur || !text.trim()) return; setBusy(true); try { const r = await api(`/inbox/${cur.id}/reply`, { method: "POST", json: { text } }); toast(r.message, r.msg.status !== "da_gui"); setText(""); open(cur.id); load(); } catch (e) { toast(errMsg(e), true); } setBusy(false); };
  const draft = async () => { if (!cur) return; setBusy(true); try { const r = await api(`/inbox/${cur.id}/ai-draft`, { method: "POST" }); setText(r.text); toast(r.source === "claude" ? "AI đã soạn (Claude)" : "Soạn theo mẫu – chưa có khóa Claude"); } catch (e) { toast(errMsg(e), true); } setBusy(false); };
  const assign = async (json: any) => { if (!cur) return; try { await api(`/inbox/${cur.id}/assign`, { method: "POST", json }); open(cur.id); load(); } catch (e) { toast(errMsg(e), true); } };
  const canCfg = ["cntt", "ptgd_mkt", "gd_kd", "tgd"].includes(role);
  return (<>
    <h1>Hộp thư đa kênh – Page công ty, Zalo OA, web</h1>
    <div className="kpis">
      <div className="kpi"><b style={{ color: st.overdue ? "var(--red)" : undefined }}>{st.overdue ?? 0}</b><span>Khách đang chờ trả lời</span></div>
      <div className="kpi"><b>{st.sla_minutes ?? "–"}′</b><span>SLA sale trả lời ({st.working_hours ? "giờ làm việc" : "ngoài giờ"})</span></div>
      <div className="kpi"><b>{st.counts?.ai_da_tra_loi || 0}</b><span>AI đã trả lời thay</span></div>
      <div className="kpi"><b>{st.facebook ? "✓" : "✗"} / {st.zalo ? "✓" : "✗"} / {st.ai ? "✓" : "✗"}</b><span>Facebook / Zalo / Claude AI</span></div>
    </div>
    {!st.facebook && <Gate ok={false}>Chưa nối Page: CNTT dán FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID, FB_APP_SECRET vào Render; trên Meta for Developers → Messenger → Webhooks đặt Callback URL <code>https://vtos-api.onrender.com{st.fb_webhook_url || "/api/v1/facebook/webhook"}</code>, Verify token = FB_VERIFY_TOKEN, đăng ký sự kiện messages, messaging_postbacks.</Gate>}
    {!st.ai && <Gate ok={false}>Chưa có ANTHROPIC_API_KEY trên Render – AI trả lời thay bằng câu mẫu (vẫn xin tên/SĐT và báo tư vấn viên); có khóa thì AI tư vấn theo tour, giá, chỗ còn trong VTOS.</Gate>}
    <div className="grid" style={{ gridTemplateColumns: "minmax(280px, 1fr) 2fr" }}>
      <div className="panel">
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">Tất cả</option><option value="cho_sale">Chờ sale</option><option value="ai_da_tra_loi">AI đã trả lời</option><option value="mo">Đang mở</option><option value="dong">Đã đóng</option></select>
          <select value={channel} onChange={(e) => setChannel(e.target.value)}><option value="">Mọi kênh</option>{Object.entries(CH).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          <label style={{ margin: 0 }}><input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} /> của tôi</label>
          {canCfg && <button className="act grey" style={{ margin: 0, padding: "2px 8px" }} onClick={async () => { try { const r = await api("/inbox/check", { method: "POST" }); toast(`R12: AI trả lời ${r.ai_replied}, cảnh báo ${r.new_alerts}`); load(); } catch (e) { toast(errMsg(e), true); } }}>Chạy R12</button>}
        </div>
        <div style={{ maxHeight: 600, overflowY: "auto", marginTop: 8 }}>
          {rows.length ? rows.map((c) => { const [l, cls] = ST[c.status] || [c.status, ""]; return <div key={c.id} onClick={() => open(c.id)} style={{ padding: 8, borderBottom: "1px solid rgba(128,128,128,.2)", cursor: "pointer", background: cur?.id === c.id ? "rgba(255,255,255,.06)" : undefined, borderLeft: c.overdue ? "3px solid var(--red)" : c.unanswered ? "3px solid var(--vtos-warning)" : "3px solid transparent" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}><b>{c.customer_name || c.external_id}</b><span className="muted">{CH[c.channel] || c.channel}</span></div>
            <div className="muted" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.last_sender === "khach" ? "Khách: " : c.last_sender === "ai" ? "AI: " : "Sale: "}{c.last_text}</div>
            <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}><Tag cls={cls}>{l}</Tag>{c.overdue && <Tag cls="red">quá SLA</Tag>}{c.unanswered && c.sla_due_at && !c.overdue && <span className="muted">hạn {fmtDT(c.sla_due_at).slice(-5)}</span>}<span className="muted">{c.sales_name}</span>{c.ai_off && <Tag>AI tắt</Tag>}</div>
          </div>; }) : <p className="muted">Chưa có hội thoại. Khi Page nhận tin, hội thoại sẽ hiện ở đây.</p>}
        </div>
      </div>
      <div className="panel">
        {cur ? <>
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
            <h2 style={{ margin: 0 }}>{cur.customer_name || cur.external_id} <Tag>{CH[cur.channel] || cur.channel}</Tag> {cur.phone && <span className="muted">{cur.phone}</span>}</h2>
            <div style={{ display: "flex", gap: 6 }}>
              {!cur.sales_id && <button className="act grey" style={{ margin: 0, padding: "2px 8px" }} onClick={() => assign({ sales_id: user?.id })}>Nhận xử lý</button>}
              <button className="act grey" style={{ margin: 0, padding: "2px 8px" }} onClick={() => assign({ ai_off: !cur.ai_off })}>{cur.ai_off ? "Bật AI" : "Tắt AI"}</button>
              <button className="act grey" style={{ margin: 0, padding: "2px 8px" }} onClick={() => assign({ status: cur.status === "dong" ? "mo" : "dong" })}>{cur.status === "dong" ? "Mở lại" : "Đóng"}</button>
            </div>
          </div>
          <p className="muted">Sale: {cur.sales_name || "chưa phân"} · lead #{cur.lead_id} · AI đã trả lời {cur.ai_replies} lần {cur.summary && `· ${cur.summary}`}</p>
          <div style={{ maxHeight: 460, overflowY: "auto", padding: 6, background: "rgba(0,0,0,.15)", borderRadius: 8 }}>
            {cur.messages.map((m: any) => <div key={m.id} style={{ display: "flex", justifyContent: m.direction === "in" ? "flex-start" : "flex-end", marginBottom: 8 }}>
              <div style={{ maxWidth: "78%", padding: "6px 10px", borderRadius: 10, background: m.direction === "in" ? "rgba(255,255,255,.08)" : m.sender === "ai" ? "rgba(90,120,255,.25)" : "rgba(0,160,120,.25)" }}>
                <div className="muted" style={{ fontSize: 11 }}>{m.direction === "in" ? (m.sender_name || "Khách") : (m.sender === "ai" ? "🤖 Trợ lý AI" : m.sender_name)} · {fmtDT(m.at)} {m.status === "loi" && <Tag cls="red">chưa gửi được</Tag>}</div>
                <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
                {m.ai_review?.score !== undefined && <div className="muted" style={{ fontSize: 11 }}>AI chấm {m.ai_review.score}/10{m.ai_review.flags?.length ? " – " + m.ai_review.flags.join("; ") : ""}</div>}
              </div></div>)}
            <div ref={bottom} />
          </div>
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Trả lời khách… (Ctrl+Enter để gửi)" onKeyDown={(e) => { if (e.ctrlKey && e.key === "Enter") send(); }} style={{ marginTop: 8 }} />
          <button className="act teal" onClick={send} disabled={busy}>Gửi</button> <button className="act grey" onClick={draft} disabled={busy}>AI gợi ý trả lời</button>
        </> : <p className="muted">Chọn hội thoại bên trái. Khách nhắn mà sale không trả lời trong {st.sla_minutes ?? 5} phút → trợ lý AI trả lời thay (theo tour, giá, chỗ còn trong VTOS; không tự giảm giá) và báo sale/TP.</p>}
      </div>
    </div>
  </>);
}

export default function Page() { return <Shell><Inbox /></Shell>; }
