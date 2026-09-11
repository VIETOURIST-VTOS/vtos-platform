"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import DinhKem from "@/components/DinhKem";

const ST: Record<string, [string, string]> = {
  da_khop: ["Đã khớp", "ok"], cho_ke_toan: ["Chờ Kế toán", "warn"], chua_khop: ["Chưa khớp", ""], bo_qua: ["Bỏ qua", ""],
  tu_dong: ["Robot tự động", "warn"], ke_toan_xac_nhan: ["KT xác nhận", "ok"], huy: ["Hủy", "red"],
};
const S = (s: string) => <Tag cls={ST[s]?.[1] || ""}>{ST[s]?.[0] || s}</Tag>;

function Collections() {
  const { user, toast } = useShell();
  const isKT = ["ketoan", "cntt"].includes(user?.role || "");
  const [sum, setSum] = useState<any>(null);
  const [txns, setTxns] = useState<any[]>([]);
  const [rcs, setRcs] = useState<any[]>([]);
  const [filter, setFilter] = useState("cho_ke_toan");
  const [assign, setAssign] = useState<Record<number, { booking_id: string; note: string }>>({});
  // Phiếu thu đang mở phần chứng từ đính kèm. Mở TỪNG phiếu chứ không hiện ô đính kèm ở mọi dòng:
  // bảng phiếu thu có thể dài hàng trăm dòng, dựng ngần ấy ô tải tệp làm màn hình nặng mà chín mươi
  // phần trăm trong số đó không ai mở.
  const [tepPT, setTepPT] = useState<number | null>(null);
  // VPM-5 – phân bổ một khoản tiền cho nhiều booking. Mở TỪNG giao dịch: bảng phân bổ là việc của
  // một khoản cụ thể, dựng sẵn cho mọi dòng chỉ làm màn hình nặng.
  const [pbMo, setPbMo] = useState<number | null>(null);
  const [pbBang, setPbBang] = useState<any>(null);
  const [pbDong, setPbDong] = useState<{ booking_id: string; so_tien: string; ghi_chu: string }[]>([]);
  const moPhanBo = async (tid: number) => {
    if (pbMo === tid) { setPbMo(null); setPbBang(null); return; }
    setPbMo(tid); setPbBang(null);
    try {
      const b = await api(`/bank-transactions/${tid}/phan-bo`);
      setPbBang(b);
      setPbDong([{ booking_id: "", so_tien: String(Math.round(b.chua_phan_bo || 0)), ghi_chu: "" }]);
    } catch (x) { toast(errMsg(x), true); }
  };
  const luuPhanBo = async (tid: number) => {
    const dong = pbDong.filter((d) => d.booking_id && Number(d.so_tien) > 0)
      .map((d) => ({ booking_id: Number(d.booking_id), so_tien: Number(d.so_tien), ghi_chu: d.ghi_chu }));
    if (!dong.length) { toast("Chưa có dòng nào để phân bổ", true); return; }
    try {
      const r = await api(`/bank-transactions/${tid}/phan-bo`, { method: "POST", json: { dong } });
      toast(r.message);
      // Cảnh báo thu dư hiện RIÊNG, không trộn vào câu báo thành công: người dùng cần thấy rằng việc
      // đã xong VÀ có một điều đáng để mắt – hai chuyện khác nhau.
      (r.canh_bao || []).forEach((c: string) => toast(c, true));
      const b = await api(`/bank-transactions/${tid}/phan-bo`);
      setPbBang(b); setPbDong([{ booking_id: "", so_tien: String(Math.round(b.chua_phan_bo || 0)), ghi_chu: "" }]);
      load();
    } catch (x) { toast(errMsg(x), true); }
  };
  const huyDong = async (tid: number, pid: number) => {
    const ly = prompt("Lý do huỷ dòng phân bổ này? (bắt buộc – dòng huỷ vẫn nằm lại trong sổ)");
    if (!ly) return;
    try {
      const r = await api(`/bank-transactions/phan-bo/${pid}/huy`, { method: "POST", json: { ly_do: ly } });
      toast(r.message);
      setPbBang(await api(`/bank-transactions/${tid}/phan-bo`)); load();
    } catch (x) { toast(errMsg(x), true); }
  };
  const [cash, setCash] = useState({ booking_id: "", amount: "", payer: "", note: "" });
  const [sp, setSp] = useState<any>(null);
  const [pull, setPull] = useState({ from_date: new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10), to_date: new Date().toISOString().slice(0, 10) });
  const [pulling, setPulling] = useState(false);
  const loadSp = useCallback(() => { if (["ketoan", "cntt", "tgd", "chutich", "bks"].includes(user?.role || "")) api("/sepay/status").then(setSp).catch(() => setSp(null)); }, [user]);
  useEffect(() => { loadSp(); }, [loadSp]);
  const load = useCallback(() => Promise.all([api("/collections/summary").then(setSum), api(`/bank-transactions${filter ? `?status=${filter}` : ""}`).then(setTxns), api("/receipts").then(setRcs)]), [filter]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); } catch (x) { toast(errMsg(x), true); } };
  const dueRows = (sum?.bookings || []).filter((b: any) => b.due > 0);
  return (<>
    <h1>Thu tiền – robot R1 (SePay) &amp; phiếu thu</h1>
    <p className="muted">Robot chỉ tự sinh phiếu thu khi khớp <b>tuyệt đối</b> mã booking + số tiền còn phải thu. Mọi trường hợp khác treo chờ Kế toán quyết định. Giao dịch ngân hàng là bản ghi bất biến.</p>
    <div className="kpis">
      <div className="kpi"><b>{sum ? vnd(dueRows.reduce((a: number, b: any) => a + b.due, 0)) : "…"}</b><span>Còn phải thu (đ)</span></div>
      <div className="kpi"><b>{dueRows.length}</b><span>Booking chưa thu đủ</span></div>
      <div className="kpi"><b style={{ color: sum?.pending_txns ? "var(--orange)" : undefined }}>{sum?.pending_txns ?? "…"}</b><span>Giao dịch chờ Kế toán</span></div>
      <div className="kpi"><b>{sum?.pending_receipts ?? "…"}</b><span>Phiếu thu robot chờ xác nhận</span></div>
    </div>

    {sp && <><h2>Kết nối SePay</h2>
      <div className="panel"><div className="grid">
        <div><b>Webhook (SePay đẩy về)</b><div>{sp.webhook_key_set ? <Tag cls="ok">Đã đặt khóa</Tag> : <Tag cls="red">Chưa đặt SEPAY_WEBHOOK_KEY</Tag>}</div><div className="muted">URL: https://vtos-api.onrender.com{sp.webhook_url} · Xác thực: Api Key</div></div>
        <div><b>User API (VTOS kéo về)</b><div>{sp.api_token_set ? (sp.error ? <Tag cls="red">Lỗi: {sp.error}</Tag> : <Tag cls="ok">Đã kết nối</Tag>) : <Tag cls="warn">Chưa đặt SEPAY_API_TOKEN</Tag>}</div>
          <div className="muted">{sp.accounts?.length ? sp.accounts.map((a: any) => `${a.bank} ${a.account_number} (${a.holder})`).join(" · ") : "my.sepay.vn → Cấu hình → API Access → tạo token → Render → Environment"}</div></div>
        <div><b>Giao dịch đã nhận</b><div>{sp.transactions}</div><div className="muted">{sp.last_transaction ? `Gần nhất ${fmtDT(sp.last_transaction.date)} · ${vnd(sp.last_transaction.amount)} · ${sp.last_transaction.content}` : "Chưa có giao dịch"}</div></div>
      </div>
      {isKT && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
        <label>Từ <input type="date" value={pull.from_date} onChange={(e) => setPull({ ...pull, from_date: e.target.value })} /></label>
        <label>Đến <input type="date" value={pull.to_date} onChange={(e) => setPull({ ...pull, to_date: e.target.value })} /></label>
        <button className="act" style={{ margin: 0 }} disabled={pulling || !sp.api_token_set} onClick={async () => { setPulling(true); try { const r = await api("/sepay/pull", { method: "POST", json: pull }); toast(r.message); load(); loadSp(); } catch (x) { toast(errMsg(x), true); } setPulling(false); }}>{pulling ? "Đang kéo…" : "Kéo giao dịch từ SePay"}</button>
        <button className="act grey" style={{ margin: 0 }} onClick={() => post("/bank-transactions/rematch")}>Xét lại giao dịch chờ</button>
        <span className="muted">Kéo lại lịch sử khi mới kết nối hoặc webhook lỗi – không nhân bản giao dịch. Robot khớp theo mã booking VTOS hoặc mã tour Vietrip + đúng số tiền còn phải thu.</span></div>}
      </div></>}

    <h2>Giao dịch ngân hàng (SePay)</h2>
    <div>{[["cho_ke_toan", "Chờ Kế toán"], ["da_khop", "Đã khớp"], ["bo_qua", "Bỏ qua"], ["", "Tất cả"]].map(([v, l]) => <button key={v} className={"act " + (filter === v ? "" : "grey")} onClick={() => setFilter(v)}>{l}</button>)}</div>
    <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Ngân hàng</th><th>Loại</th><th>Số tiền</th><th>Nội dung CK</th><th>Kết quả robot</th><th>Ghi chú</th>{isKT && <th>Kế toán xử lý</th>}</tr></thead>
      <tbody>{txns.length ? txns.map((t) => <tr key={t.id}><td>{fmtDT(t.transaction_date)}</td><td>{t.gateway}</td><td>{t.transfer_type === "in" ? "Vào" : "Ra"}</td><td style={{ textAlign: "right" }}>{vnd(t.amount)}
          {/* RỖNG = chưa ai chia khoản này; 0 = đã chia hết. Hai chuyện khác nhau nên hiện khác nhau. */}
          {t.chua_phan_bo !== null && t.chua_phan_bo !== undefined && (t.chua_phan_bo > 0
            ? <div style={{ color: "var(--orange)", fontSize: 12 }}>còn {vnd(t.chua_phan_bo)} chưa phân bổ</div>
            : <div className="muted" style={{ fontSize: 12 }}>đã phân bổ hết ({t.so_dong_phan_bo} booking)</div>)}</td><td>{t.content}</td><td>{S(t.match_status)}{t.booking_code && <> <b>{t.booking_code}</b></>}</td><td className="muted">{t.match_note}</td>
        {isKT && <td>{t.match_status === "cho_ke_toan" && <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          <select value={assign[t.id]?.booking_id ?? (t.booking_id || "")} onChange={(e) => setAssign({ ...assign, [t.id]: { booking_id: e.target.value, note: assign[t.id]?.note || "" } })}>
            <option value="">– chọn booking –</option>{(sum?.bookings || []).map((b: any) => <option key={b.booking_id} value={b.booking_id}>{b.code} · {b.customer_name} · còn {vnd(b.due)}</option>)}</select>
          <input placeholder="Ghi chú (cọc đợt 1…)" value={assign[t.id]?.note || ""} onChange={(e) => setAssign({ ...assign, [t.id]: { booking_id: assign[t.id]?.booking_id ?? (t.booking_id || ""), note: e.target.value } })} />
          <button className="act teal" style={{ margin: 0 }} disabled={!(assign[t.id]?.booking_id ?? t.booking_id)} onClick={() => post(`/bank-transactions/${t.id}/assign`, { booking_id: Number(assign[t.id]?.booking_id ?? t.booking_id), note: assign[t.id]?.note || "" })}>Gán &amp; lập phiếu thu</button>
          <button className="act grey" style={{ margin: 0 }} onClick={() => { const n = prompt("Lý do bỏ qua giao dịch này?"); if (n !== null) post(`/bank-transactions/${t.id}/ignore`, { note: n }); }}>Bỏ qua</button>
        </div>}
        {t.transfer_type === "in" && <button className="act grey" style={{ margin: 0, fontSize: 12 }}
          onClick={() => moPhanBo(t.id)}>{pbMo === t.id ? "Ẩn phân bổ" : "Chia cho nhiều booking"}</button>}</td>}</tr>)
        : <tr><td colSpan={8} className="muted">Không có giao dịch.</td></tr>}</tbody></table></div>

    {pbMo !== null && <div className="panel">
      <h2>Phân bổ khoản tiền cho nhiều booking</h2>
      {!pbBang ? <p className="muted">Đang tải…</p> : <>
        <p className="muted">Một khoản khách chuyển có thể trả cho nhiều tour. Số dư <b>chưa phân bổ</b> hiện
          ngay đây — không phải tự trừ nhẩm. Dòng đã huỷ vẫn giữ lại kèm lý do: đó là dấu vết của một
          lần hiểu sai, và là thứ người tra cứu về sau cần thấy.</p>
        <div className="kpis">
          <div className="kpi"><b>{vnd(pbBang.so_tien)}</b><span>Số tiền giao dịch</span></div>
          <div className="kpi"><b>{vnd(pbBang.da_phan_bo)}</b><span>Đã phân bổ</span></div>
          <div className="kpi"><b style={{ color: pbBang.chua_phan_bo > 0 ? "var(--orange)" : undefined }}>{vnd(pbBang.chua_phan_bo)}</b><span>Chưa phân bổ</span></div>
        </div>
        <table><thead><tr><th>Booking</th><th>Khách</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Phiếu thu</th><th>Ghi chú</th><th>Bởi</th><th></th></tr></thead>
          <tbody>{pbBang.dong.length ? pbBang.dong.map((d: any) => <tr key={d.id} style={d.huy ? { opacity: 0.55 } : undefined}>
            <td><b>{d.booking_code}</b>{d.huy && <> <Tag cls="red">đã huỷ</Tag></>}</td>
            <td>{d.khach}<div className="muted">{d.tour_code}</div></td>
            <td style={{ textAlign: "right", textDecoration: d.huy ? "line-through" : undefined }}>{vnd(d.so_tien)}</td>
            <td>{d.phieu_thu}</td>
            <td className="muted">{d.huy ? `Huỷ: ${d.huy_ly_do}` : d.ghi_chu}</td>
            <td className="muted">{d.huy ? d.huy_boi : d.boi}</td>
            <td>{isKT && !d.huy && <button className="act grey" style={{ margin: 0, fontSize: 12 }}
                  onClick={() => huyDong(pbMo, d.id)}>Huỷ dòng</button>}</td></tr>)
            : <tr><td colSpan={7} className="muted">Chưa phân bổ dòng nào.</td></tr>}</tbody></table>

        {isKT && pbBang.chua_phan_bo > 0 && <>
          <h3>Thêm dòng phân bổ</h3>
          {pbDong.map((d, i) => <div key={i} style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 4 }}>
            <select value={d.booking_id} onChange={(e) => { const x = [...pbDong]; x[i] = { ...d, booking_id: e.target.value }; setPbDong(x); }}>
              <option value="">– chọn booking –</option>
              {(sum?.bookings || []).map((b: any) => <option key={b.booking_id} value={b.booking_id}>{b.code} · {b.customer_name} · còn {vnd(b.due)}</option>)}</select>
            <input type="number" placeholder="Số tiền" value={d.so_tien}
              onChange={(e) => { const x = [...pbDong]; x[i] = { ...d, so_tien: e.target.value }; setPbDong(x); }} />
            <input placeholder="Ghi chú (cọc đợt 1…)" value={d.ghi_chu}
              onChange={(e) => { const x = [...pbDong]; x[i] = { ...d, ghi_chu: e.target.value }; setPbDong(x); }} />
            {pbDong.length > 1 && <button className="act grey" style={{ margin: 0 }}
              onClick={() => setPbDong(pbDong.filter((_, j) => j !== i))}>Bỏ dòng</button>}
          </div>)}
          <button className="act grey" style={{ margin: 0 }}
            onClick={() => setPbDong([...pbDong, { booking_id: "", so_tien: "", ghi_chu: "" }])}>+ Thêm dòng</button>
          <button className="act teal" style={{ margin: 0, marginLeft: 6 }} onClick={() => luuPhanBo(pbMo)}>Lưu phân bổ</button>
          <p className="muted">Tổng các dòng không được vượt số dư chưa phân bổ. Nếu có một dòng sai thì
            <b> không dòng nào được ghi</b> — để không bao giờ có tình trạng tiền vào sổ một nửa.</p>
        </>}
      </>}
    </div>}

    <h2>Phiếu thu (mẫu 01-TT)</h2>
    <div className="panel wrap"><table><thead><tr><th>Số PT</th><th>Booking</th><th>Tour</th><th>Người nộp</th><th>Số tiền</th><th>Hình thức</th><th>Trạng thái</th><th>Lập bởi</th><th>Lúc</th>{isKT && <th></th>}<th></th></tr></thead>
      <tbody>{rcs.length ? rcs.map((r) => [<tr key={r.id}><td><b>{r.code}</b></td><td>{r.booking_code}<div className="muted">{r.customer_name}</div></td><td>{r.tour_code}</td><td>{r.payer}</td><td style={{ textAlign: "right" }}>{vnd(r.amount)}</td><td>{r.method === "tien_mat" ? "Tiền mặt" : "Chuyển khoản"}</td><td>{S(r.status)}</td><td className="muted">{r.created_by}{r.confirmed_by && ` → ${r.confirmed_by}`}</td><td>{fmtDT(r.created_at)}</td>
        {isKT && <td>{r.status === "tu_dong" && user?.role === "ketoan" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/receipts/${r.id}/confirm`)}>Xác nhận</button>}</td>}
        <td><button className="act grey" style={{ margin: 0, fontSize: 12 }}
              onClick={() => setTepPT(tepPT === r.id ? null : r.id)}>{tepPT === r.id ? "Ẩn" : "Chứng từ"}</button></td></tr>,
        tepPT === r.id && <tr key={r.id + "t"}><td colSpan={isKT ? 11 : 10} style={{ background: "var(--bg2)" }}>
          {/* Ủy nhiệm chi, biên lai, ảnh chuyển khoản khách gửi. Đối soát thu tiền dựa vào SePay; khoản
              nào SePay không khớp thì chứng từ gốc ở đây là thứ duy nhất xử được.
              Phiếu đã xác nhận thì CHỈ XEM: số đã vào sổ thì bộ chứng từ của nó không đổi nữa. */}
          <DinhKem doiTuong="phieu_thu" doiTuongId={r.id} loai="chung_tu"
                   tieuDe={`Chứng từ của phiếu thu ${r.code}`}
                   chiXem={r.status === "da_xac_nhan"} />
        </td></tr>]) : <tr><td colSpan={10} className="muted">Chưa có phiếu thu.</td></tr>}</tbody></table></div>

    {user?.role === "ketoan" && <><h2>Lập phiếu thu tiền mặt</h2>
      <div className="panel"><div className="grid">
        <label>Booking<select value={cash.booking_id} onChange={(e) => setCash({ ...cash, booking_id: e.target.value })}><option value="">– chọn –</option>{dueRows.map((b: any) => <option key={b.booking_id} value={b.booking_id}>{b.code} · {b.customer_name} · còn {vnd(b.due)}</option>)}</select></label>
        <label>Số tiền (đ)<input type="number" value={cash.amount} onChange={(e) => setCash({ ...cash, amount: e.target.value })} /></label>
        <label>Người nộp<input value={cash.payer} onChange={(e) => setCash({ ...cash, payer: e.target.value })} /></label>
        <label>Ghi chú<input value={cash.note} onChange={(e) => setCash({ ...cash, note: e.target.value })} /></label>
      </div><button className="act" disabled={!cash.booking_id || !cash.amount} onClick={() => post("/receipts/cash", { booking_id: Number(cash.booking_id), amount: Number(cash.amount), payer: cash.payer, note: cash.note }).then(() => setCash({ booking_id: "", amount: "", payer: "", note: "" }))}>Lập phiếu thu</button></div></>}

    <h2>Công nợ phải thu theo booking</h2>
    <div className="panel wrap"><table><thead><tr><th>Booking</th><th>Tour</th><th>Khách</th><th>Phải thu</th><th>Đã thu</th><th>Còn lại</th></tr></thead>
      <tbody>{(sum?.bookings || []).map((b: any) => <tr key={b.booking_id} style={{ opacity: b.due > 0 ? 1 : 0.55 }}><td><b>{b.code}</b></td><td>{b.tour_code}</td><td>{b.customer_name}</td><td style={{ textAlign: "right" }}>{vnd(b.total)}</td><td style={{ textAlign: "right" }}>{vnd(b.paid)}</td><td style={{ textAlign: "right" }}>{b.due > 0 ? <Tag cls="warn">{vnd(b.due)}</Tag> : <Tag cls="ok">Đủ</Tag>}</td></tr>)}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Collections /></Shell>; }
