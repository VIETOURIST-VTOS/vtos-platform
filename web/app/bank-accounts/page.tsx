"use client";
/** Tài khoản ngân hàng: nạp Sổ tiền gửi MISA, xem trước rồi mới gán dòng sổ 112 về đúng tiểu khoản từng ngân hàng.
 *
 * Ba bước cố ý tách rời để không ai lỡ tay đổi sổ:
 *   1. Nạp Sổ tiền gửi – chỉ dựng bản đồ chứng từ → ngân hàng, KHÔNG đụng vào sổ.
 *   2. Xem trước      – hiện rõ mỗi ngân hàng nhận bao nhiêu dòng, còn bao nhiêu dòng chưa nhận diện được.
 *   3. Ghi vào sổ     – có hộp xác nhận, và chỉ hiện sau khi đã xem trước.
 */
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const H1 = { from: "2026-01-01", to: "2026-06-30" };

function BankAccounts() {
  const { user, toast } = useShell();
  const [rows, setRows] = useState<any[]>([]);
  const [map, setMap] = useState<any>(null);
  const [bal, setBal] = useState<any>(null);
  const [preview, setPreview] = useState<any>(null);
  const [applied, setApplied] = useState<any>(null);
  const [range, setRange] = useState(H1);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState("");
  const canWrite = ["ketoan", "chutich"].includes(user?.role || "");

  const reload = async () => {
    try {
      setRows((await api("/bank-accounts")).rows || []);
      setMap(await api("/bank-accounts/ban-do"));
      setBal(await api(`/bank-accounts/so-du?since=${range.from}&upto=${range.to}`));
    } catch (x) { toast(errMsg(x), true); }
  };
  useEffect(() => { reload(); }, []);           // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (label: string, fn: () => Promise<any>, after?: (r: any) => void) => {
    setBusy(label);
    try { const r = await fn(); after?.(r); toast("Xong: " + label); await reload(); }
    catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };

  const upload = () => {
    if (!file) { toast("Chọn tệp Sổ tiền gửi ngân hàng xuất từ MISA trước", true); return; }
    const fd = new FormData(); fd.append("file", file);
    run("nạp Sổ tiền gửi", () => api("/bank-accounts/nap-so-tien-gui", { method: "POST", body: fd }),
        () => setPreview(null));
  };

  const doPreview = () => run("xem trước",
    () => api(`/bank-accounts/phan-loai/xem-truoc?since=${range.from}&upto=${range.to}`), setPreview);

  const doApply = () => {
    const n = preview?.matched || 0;
    if (!confirm(`Ghi vào sổ: đổi mã tài khoản của ${n.toLocaleString("vi")} dòng từ 1121/1122 sang tiểu khoản từng ngân hàng.\n\n` +
      `Không đổi số tiền, ngày, số chứng từ. Hệ thống tự kiểm chứng số dư TK 112 trước và sau phải y nguyên – lệch một đồng là hoàn tác toàn bộ.\n\n` +
      `Có nhật ký kiểm toán và có thể huỷ gán từng ngân hàng. Tiếp tục?`)) return;
    run("ghi vào sổ", () => api(`/bank-accounts/phan-loai/thuc-hien?since=${range.from}&upto=${range.to}`, { method: "POST" }),
        (r) => { setApplied(r); setPreview(null); });
  };

  const pct = (a: number, b: number) => (b ? Math.round((1000 * a) / b) / 10 : 0);

  return (<>
    <p className="muted">MISA theo dõi tiền gửi theo <b>từng tài khoản ngân hàng</b>; sổ nạp sang VTOS lại ghi cột đối tượng trên TK 112
      là người nộp/nhận tiền nên không tách được. Nạp báo cáo <b>“Sổ tiền gửi ngân hàng”</b> của MISA (in theo từng tài khoản ngân hàng)
      để hệ thống biết chính xác chứng từ nào thuộc ngân hàng nào – không phải đoán theo số chứng từ.</p>

    <div className="panel">
      <label>Kỳ: từ <input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>{" "}
      <label>đến <input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label>{" "}
      <button className="act grey" disabled={!!busy} onClick={reload}>Tải lại</button>
    </div>

    <div className="grid">
      <div className="panel">
        <h3>1. Nạp Sổ tiền gửi ngân hàng (MISA)</h3>
        <p className="muted">Excel (.xlsx) hoặc CSV. Bước này chỉ dựng bản đồ chứng từ → ngân hàng và tự mở tài khoản ngân hàng
          còn thiếu kèm tiểu khoản 112. <b>Không đụng vào sổ.</b> Nạp lại cùng ngân hàng thì thay thế bản đồ cũ.</p>
        <input type="file" accept=".xlsx,.csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        {canWrite && <button className="act" disabled={!!busy} onClick={upload}>Nạp</button>}
        {map && <p className="muted">Bản đồ hiện có: <b>{(map.map_rows || 0).toLocaleString("vi")}</b> dòng ·{" "}
          {(map.docs_single_bank || 0).toLocaleString("vi")} chứng từ chỉ thuộc một ngân hàng</p>}
      </div>

      <div className="panel">
        <h3>2. Xem trước</h3>
        <p className="muted">Hiện rõ mỗi ngân hàng sẽ nhận bao nhiêu dòng và còn bao nhiêu dòng chưa nhận diện được.
          Dòng không có trong Sổ tiền gửi sẽ <b>giữ nguyên</b> ở tài khoản cha chứ không gán bừa.</p>
        <button className="act grey" disabled={!!busy} onClick={doPreview}>Xem trước</button>
        {preview && <p>Quét <b>{preview.scanned.toLocaleString("vi")}</b> dòng · gán được{" "}
          <b>{preview.matched.toLocaleString("vi")}</b> ({pct(preview.matched, preview.scanned)}%) · chưa nhận diện{" "}
          <b>{preview.unmatched.toLocaleString("vi")}</b>{" "}
          {preview.co_ban_do_misa ? <Tag cls="ok">có bản đồ MISA</Tag> : <Tag cls="warn">chưa nạp Sổ tiền gửi – đang phải suy đoán</Tag>}</p>}
      </div>

      <div className="panel">
        <h3>3. Ghi vào sổ</h3>
        <p className="muted">Chỉ đổi mã tài khoản trong cây 112, không đổi số tiền/ngày/chứng từ. Hệ thống tự kiểm chứng
          số dư TK 112 trước và sau phải y nguyên, lệch một đồng là hoàn tác toàn bộ.</p>
        {canWrite
          ? <button className="act orange" disabled={!!busy || !preview || !preview.matched} onClick={doApply}>Ghi vào sổ</button>
          : <span className="muted">Chỉ Kế toán / Chủ tịch mới ghi được.</span>}
        {!preview && <p className="muted">Phải chạy “Xem trước” trước đã.</p>}
        {applied && <p><Tag cls="ok">Đã ghi {applied.changed?.toLocaleString("vi")} dòng</Tag>{" "}
          số dư 112 trước {vnd(applied.balance_before)} → sau {vnd(applied.balance_after)}</p>}
      </div>
    </div>

    {preview && <div className="panel wrap">
      <h3>Kết quả xem trước theo ngân hàng</h3>
      <table><thead><tr><th>Mã / số tài khoản</th><th>Ngân hàng</th><th>Tiểu khoản 112</th><th className="r">Số dòng</th><th>Chứng từ mẫu</th></tr></thead>
        <tbody>{preview.by_bank.map((b: any) => <tr key={b.code}>
          <td><b>{b.code}</b></td><td>{b.bank}</td><td>{b.account_code}</td>
          <td className="r">{b.lines.toLocaleString("vi")}</td>
          <td className="muted">{(b.samples || []).map((s: any) => s.entry_code).join(", ")}</td></tr>)}</tbody></table>
      {!!preview.unmatched && <>
        <h4>Chưa nhận diện được ngân hàng ({preview.unmatched.toLocaleString("vi")} dòng)</h4>
        <p className="muted">Thường là chứng từ không có trong file Sổ tiền gửi đã nạp: ngoài khoảng ngày của file,
          hoặc bút toán do VTOS tự sinh chứ không phải từ MISA. Các dòng này giữ nguyên ở tài khoản cha.</p>
        <table><thead><tr><th>Tiền tố số chứng từ</th><th className="r">Số dòng</th></tr></thead>
          <tbody>{(preview.unmatched_prefixes || []).map((p: any) => <tr key={p.prefix}><td>{p.prefix}</td><td className="r">{p.lines.toLocaleString("vi")}</td></tr>)}</tbody></table>
      </>}
    </div>}

    {bal && <div className="panel wrap">
      <h3>Số dư từng ngân hàng ({range.from} → {range.to})</h3>
      <table><thead><tr><th>Mã</th><th>Ngân hàng</th><th>Tiểu khoản</th><th className="r">Dư đầu</th><th className="r">Phát sinh Nợ</th><th className="r">Phát sinh Có</th><th className="r">Dư cuối</th></tr></thead>
        <tbody>
          {bal.rows.map((r: any) => <tr key={r.code}><td><b>{r.code}</b></td><td>{r.bank_name}</td><td>{r.account_code}</td>
            <td className="r">{vnd(r.opening)}</td><td className="r">{vnd(r.debit)}</td><td className="r">{vnd(r.credit)}</td><td className="r"><b>{vnd(r.closing)}</b></td></tr>)}
          <tr><td colSpan={3}><i>Chưa nhận diện ngân hàng (còn ở {(bal.unassigned.accounts || []).join(", ")})</i></td>
            <td className="r">{vnd(bal.unassigned.opening)}</td><td className="r">{vnd(bal.unassigned.debit)}</td>
            <td className="r">{vnd(bal.unassigned.credit)}</td><td className="r">{vnd(bal.unassigned.closing)}</td></tr>
          <tr><td colSpan={6}><b>TỔNG – phải bằng số dư TK 112</b></td><td className="r"><b>{vnd(bal.total_closing)}</b></td></tr>
        </tbody></table>
      {Math.abs((bal.total_closing || 0) - (bal.check_112 || 0)) >= 1
        ? <p><Tag cls="red">Lệch so với TK 112: {vnd((bal.total_closing || 0) - (bal.check_112 || 0))}</Tag></p>
        : <p><Tag cls="ok">Khớp đúng số dư TK 112: {vnd(bal.check_112)}</Tag></p>}
    </div>}

    {!!rows.length && <div className="panel wrap">
      <h3>Danh mục tài khoản ngân hàng ({rows.length})</h3>
      <table><thead><tr><th>Mã</th><th>Ngân hàng</th><th>Số tài khoản</th><th>Loại tiền</th><th>Tiểu khoản 112</th><th>Trạng thái</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.code}><td><b>{r.code}</b></td><td>{r.bank_name}</td><td>{r.account_number}</td>
          <td>{r.currency}</td><td>{r.account_code}</td>
          <td>{r.active ? <Tag cls="ok">Đang dùng</Tag> : <Tag cls="grey">Ngừng</Tag>}</td></tr>)}</tbody></table>
    </div>}
  </>);
}
export default function Page() { return <Shell><BankAccounts /></Shell>; }
