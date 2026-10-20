"use client";
import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, fmtD, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** PC-1 · Gửi yêu cầu Pháp chế — Chủ tịch duyệt bản xem thử 19/10/2026.
 *
 *  Trưởng phòng trở lên (cộng HCNS, CNTT) tự gửi, thay vì nhờ Pháp chế ghi hộ. Phòng gửi và người gửi
 *  MÁY CHỦ lấy từ tài khoản — màn hình chỉ hiện ra cho người dùng xem, không gửi lên. Bảng dưới chỉ có
 *  yêu cầu của chính người đang đăng nhập: cửa đọc lọc ở máy chủ, không lọc ở đây.
 */
const RONG = { loai: "y_kien_phap_ly", tieu_de: "", noi_dung: "", muc_do: "thuong", han_mong_muon: "" };
const MAU: Record<string, string> = { moi: "navy", dang_xu_ly: "teal", cho_bo_sung: "warn", xong: "ok", tu_choi: "red" };

async function moTep(id: number) {
  const r = await fetch(`/api/v1/gui-phap-che/${id}/tep`, { headers: { Authorization: `Bearer ${getToken() || ""}` } });
  if (!r.ok) return;
  window.open(URL.createObjectURL(await r.blob()), "_blank");
}

function GuiPhapChe() {
  const [d, setD] = useState<any>(null);
  const [f, setF] = useState<any>(RONG);
  const [tep, setTep] = useState<File | null>(null);
  const [bs, setBs] = useState<Record<number, string>>({});
  const [tb, setTb] = useState<{ text: string; err?: boolean } | null>(null);
  const [dang, setDang] = useState(false);

  const tai = useCallback(() => {
    api("/gui-phap-che").then(setD).catch((e) => setTb({ text: errMsg(e), err: true }));
  }, []);
  useEffect(() => { tai(); }, [tai]);

  const gui = async (e: React.FormEvent) => {
    e.preventDefault();
    setDang(true); setTb(null);
    try {
      const r = await api<any>("/gui-phap-che", { method: "POST", json: { ...f, han_mong_muon: f.han_mong_muon || null } });
      if (tep) {
        const fd = new FormData(); fd.append("tep", tep);
        await api(`/gui-phap-che/${r.yeu_cau.id}/tep`, { method: "POST", body: fd });
      }
      setTb({ text: r.message }); setF(RONG); setTep(null); tai();
    } catch (ex) { setTb({ text: errMsg(ex), err: true }); }
    setDang(false);
  };

  const boSung = async (id: number) => {
    try {
      const r = await api<any>(`/gui-phap-che/${id}/bo-sung`, { method: "POST", json: { noi_dung_bo_sung: bs[id] || "" } });
      setTb({ text: r.message }); setBs({ ...bs, [id]: "" }); tai();
    } catch (ex) { setTb({ text: errMsg(ex), err: true }); }
  };

  if (!d) return <><h1>Gửi yêu cầu Pháp chế</h1>{tb && <p className={tb.err ? "red" : "muted"}>{tb.text}</p>}</>;
  return (<>
    <h1>Gửi yêu cầu Pháp chế</h1>
    <p className="muted">Gửi thẳng tới Pháp chế: rà soát hợp đồng, xin ý kiến pháp lý, soạn thảo văn bản, tranh chấp.
      Pháp chế nhận được chuông ngay khi bạn gửi.</p>
    {tb && <p className={tb.err ? "red" : "muted"}>{tb.text}</p>}
    <form className="panel" onSubmit={gui} style={{ display: "grid", gap: 10 }}>
      <div className="grid">
        <div><label htmlFor="pc-loai">Loại yêu cầu</label>
          <select id="pc-loai" value={f.loai} onChange={(e) => setF({ ...f, loai: e.target.value })}>
            {Object.entries(d.loai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></div>
        <div><label htmlFor="pc-muc">Mức độ</label>
          <select id="pc-muc" value={f.muc_do} onChange={(e) => setF({ ...f, muc_do: e.target.value })}>
            {Object.entries(d.muc_do).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></div>
        <div><label htmlFor="pc-han">Hạn mong muốn</label>
          <input id="pc-han" type="date" value={f.han_mong_muon} onChange={(e) => setF({ ...f, han_mong_muon: e.target.value })} /></div>
      </div>
      <div><label htmlFor="pc-td">Tiêu đề</label>
        <input id="pc-td" required style={{ width: "100%" }} value={f.tieu_de} onChange={(e) => setF({ ...f, tieu_de: e.target.value })} /></div>
      <div><label htmlFor="pc-nd">Nội dung</label>
        <textarea id="pc-nd" rows={4} style={{ width: "100%" }} value={f.noi_dung} onChange={(e) => setF({ ...f, noi_dung: e.target.value })} /></div>
      <div><label htmlFor="pc-tep">Tệp đính kèm (hợp đồng, công văn)</label>
        <input id="pc-tep" type="file" onChange={(e) => setTep(e.target.files?.[0] || null)} /></div>
      <p className="muted">Phòng gửi: <b>{d.phong_gui}</b> · Người gửi: <b>{d.nguoi_gui}</b> (lấy từ tài khoản)</p>
      <button className="act teal" disabled={dang}>{dang ? "Đang gửi…" : "Gửi Pháp chế"}</button>
    </form>

    <div className="panel wrap"><h2>Yêu cầu bạn đã gửi</h2>
      {!d.rows.length ? <p className="muted">Bạn chưa gửi yêu cầu nào.</p> :
        <table><thead><tr><th>#</th><th>Ngày gửi</th><th>Tiêu đề</th><th>Trạng thái</th><th>Kết quả / Pháp chế cần bổ sung</th><th></th></tr></thead>
          <tbody>{d.rows.map((y: any) => <tr key={y.id}>
            <td className="mono">{y.id}</td><td>{fmtD(y.luc)}</td>
            <td>{y.tieu_de}{y.muc_do === "gap" && <> <Tag cls="red">Gấp</Tag></>}</td>
            <td><Tag cls={MAU[y.trang_thai] || "navy"}>{y.trang_thai_ten}</Tag></td>
            <td>{y.ket_qua || <span className="muted">—</span>}
              {y.co_the_bo_sung && <div style={{ marginTop: 6 }}>
                <input aria-label="Nội dung bổ sung" placeholder="Nội dung bổ sung" style={{ width: 240 }}
                  value={bs[y.id] || ""} onChange={(e) => setBs({ ...bs, [y.id]: e.target.value })} />
                <button className="act" style={{ marginLeft: 6 }} onClick={() => boSung(y.id)}>Gửi bổ sung</button></div>}</td>
            <td>{y.attachment_id && <button className="act grey" onClick={() => moTep(y.id)}>Tệp</button>}</td>
          </tr>)}</tbody></table>}
    </div>
  </>);
}

export default function Page() { return <Shell><GuiPhapChe /></Shell>; }
