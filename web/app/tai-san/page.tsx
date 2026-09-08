"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Tài sản cố định & chi phí trả trước — V5 của lệnh 08/9/2026.
 *
 *  Backend viết xong từ trước (12 endpoint, khấu hao đường thẳng, xuất Excel) nhưng dữ liệu thật đang
 *  RỖNG: 0 tài sản, 0 công cụ. Trong khi khấu hao là khoản chênh lớn nhất giữa lãi theo đoàn và lãi
 *  trên sổ — 3,46 tỷ trong sáu tháng đầu 2026 không ai theo dõi được trong VTOS.
 *
 *  Màn hình cố ý KHÔNG tự ghi sổ: xem khấu hao kỳ trước, đối chiếu, rồi mới bấm ghi. Một bút toán khấu
 *  hao ghi nhầm kỳ phải đảo bằng tay ở cả hai kỳ. */
const TABS: [string, string][] = [["ts", "Tài sản cố định"], ["kh", "Khấu hao kỳ"],
                                  ["tt", "Chi phí trả trước"], ["pb", "Phân bổ kỳ"]];

function TaiSan() {
  const { user, toast } = useShell();
  const [tab, setTab] = useState("ts");
  const [ky, setKy] = useState(new Date().toISOString().slice(0, 7));
  const [meta, setMeta] = useState<any>(null);
  const [ts, setTs] = useState<any[]>([]);
  const [tt, setTt] = useState<any[]>([]);
  const [kh, setKh] = useState<any>(null);
  const [pb, setPb] = useState<any>(null);
  const [f, setF] = useState<any>(null);
  const [tep, setTep] = useState<any>(null);
  const [luu, setLuu] = useState(false);
  const canGhi = (user?.role || "") === "ketoan" || (user?.role || "") === "cntt";

  const load = useCallback(async () => {
    try {
      setTs(await api("/fixed-assets"));
      setTt(await api("/prepaid"));
      setKh(await api(`/fixed-assets/depreciation?period=${ky}`));
      setPb(await api(`/prepaid/allocation?period=${ky}`));
    } catch (e) { toast(errMsg(e), true); }
  }, [ky, toast]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { api("/assets/meta").then(setMeta).catch(() => {}); }, []);

  const ghi = async () => {
    setLuu(true);
    try {
      const la = f.loai === "ts";
      const body: any = { code: f.code, name: f.name, kind: f.kind, department: f.department || "",
        start_date: f.start_date, quantity: Number(f.quantity) || 1, note: f.note || "" };
      if (la) Object.assign(body, { purchase_date: f.purchase_date || null, cost: Number(f.cost) || 0,
        depr_months: Number(f.depr_months) || 0, salvage: Number(f.salvage) || 0 });
      else Object.assign(body, { amount: Number(f.cost) || 0, months: Number(f.depr_months) || 1 });
      await api(la ? "/fixed-assets" : "/prepaid", { method: "POST", json: body });
      toast("Đã ghi. Nhớ đính kèm hóa đơn và biên bản bàn giao."); setF(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const ghiSo = async (loai: "kh" | "pb") => {
    const url = loai === "kh" ? `/fixed-assets/depreciation/${ky}/post` : `/prepaid/allocation/${ky}/post`;
    const ten = loai === "kh" ? "khấu hao" : "phân bổ chi phí trả trước";
    if (!window.confirm(`Ghi sổ ${ten} kỳ ${ky}?\n\nĐối chiếu bảng bên dưới trước khi bấm — bút toán ` +
                        "ghi nhầm kỳ phải đảo bằng tay ở cả hai kỳ.")) return;
    try { const r = await api<any>(url, { method: "POST" }); toast(r.message || "Đã ghi sổ."); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const tai = (loai: "kh" | "pb") => {
    const url = loai === "kh" ? `/api/v1/fixed-assets/depreciation.xlsx?period=${ky}`
                              : `/api/v1/prepaid/allocation.xlsx?period=${ky}`;
    fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` } })
      .then((r) => r.blob()).then((b) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b); a.download = `${loai}_${ky}.xlsx`; a.click();
      }).catch(() => toast("Không tải được tệp", true));
  };

  const bang = (rows: any[], tienTen: string, thangTen: string, loai: "ts" | "tt") => (
    <div className="panel wrap">
      <h2>{loai === "ts" ? "Tài sản cố định & công cụ dụng cụ" : "Chi phí trả trước"}</h2>
      {canGhi && !f && <button className="act" onClick={() => setF({ loai, code: "", name: "",
        kind: Object.keys((loai === "ts" ? meta?.asset_kinds : meta?.prepaid_kinds) || {})[0] || "",
        department: "", purchase_date: "", start_date: "", cost: "", depr_months: "", salvage: "",
        quantity: 1, note: "" })}>+ Thêm</button>}
      <table><thead><tr><th>Mã</th><th>Tên</th><th>Nhóm</th><th>Bộ phận</th><th>Bắt đầu</th>
        <th className="num">{tienTen}</th><th className="num">{thangTen}</th>
        <th className="num">Mỗi kỳ</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{rows.length ? rows.map((a: any) => <tr key={a.id}>
          <td className="mono">{a.code}</td><td><b>{a.name}</b></td>
          <td className="muted">{a.kind_name}</td><td className="muted">{a.department}</td>
          <td>{fmtD(a.start_date)}</td>
          <td className="num">{vnd(a.cost ?? a.amount)}</td>
          <td className="num muted">{a.depr_months ?? a.months}</td>
          <td className="num">{vnd(a.monthly)}</td>
          <td><Tag cls={a.status === "dang_dung" || a.status === "dang_pb" ? "ok" : ""}>{a.status_name}</Tag></td>
          <td><button className="act grey" style={{ margin: 0 }}
                      onClick={() => setTep({ ma: a.code, ten: a.name })}>Hồ sơ</button></td>
        </tr>) : <tr><td colSpan={10} className="muted">Chưa có bản ghi nào — {loai === "ts"
          ? "khấu hao kỳ sẽ ra 0 cho tới khi nhập danh sách tài sản." : "chưa có gì để phân bổ."}</td></tr>}</tbody></table>
    </div>);

  const bangKy = (d: any, loai: "kh" | "pb", ten: string) => (
    <div className="panel wrap">
      <h2>{ten} kỳ {ky}</h2>
      {!d ? <p className="muted">Đang tải…</p> : <>
        <div className="kpis">
          <div className="kpi"><b>{(d.rows || []).length}</b><span>dòng</span></div>
          <div className="kpi"><b>{vnd(d.total ?? d.tong ?? 0)}</b><span>tổng {ten.toLowerCase()}</span></div>
          <div className="kpi"><b>{d.posted || d.da_ghi_so ? "đã ghi sổ" : "chưa ghi sổ"}</b><span>trạng thái kỳ</span></div>
        </div>
        <table><thead><tr><th>Mã</th><th>Tên</th><th className="num">Nguyên giá</th>
          <th className="num">Số kỳ này</th><th className="num">Lũy kế</th><th className="num">Còn lại</th></tr></thead>
          <tbody>{(d.rows || []).length ? d.rows.map((r: any, i: number) => <tr key={r.id || i}>
            <td className="mono">{r.code}</td><td>{r.name}</td>
            <td className="num muted">{vnd(r.cost ?? r.amount ?? 0)}</td>
            <td className="num"><b>{vnd(r.amount_this ?? r.monthly ?? r.so_ky_nay ?? 0)}</b></td>
            <td className="num muted">{vnd(r.accumulated ?? r.luy_ke ?? 0)}</td>
            <td className="num muted">{vnd(r.remaining ?? r.con_lai ?? 0)}</td>
          </tr>) : <tr><td colSpan={6} className="muted">Kỳ này không có dòng nào.</td></tr>}</tbody></table>
        <div style={{ marginTop: 10 }}>
          <button className="act grey" onClick={() => tai(loai)}>Tải Excel</button>{" "}
          {canGhi && (d.rows || []).length > 0 &&
            <button className="act teal" onClick={() => ghiSo(loai)}>Ghi sổ kỳ {ky}</button>}
        </div>
        <p className="muted">Xem và đối chiếu trước, ghi sổ sau. Màn hình không tự ghi — một bút toán
          khấu hao vào nhầm kỳ phải đảo bằng tay ở cả hai kỳ.</p>
      </>}
    </div>);

  return (<>
    <h1>Tài sản &amp; mua sắm</h1>
    <p className="muted">Khấu hao là khoản chênh lớn nhất giữa lãi theo đoàn và lãi trên sổ —
      <b> 3,46 tỷ trong sáu tháng đầu 2026</b>. Chừng nào danh sách tài sản còn rỗng thì khấu hao kỳ ra
      0, và lãi trên báo cáo quản trị cao hơn lãi thật đúng bằng khoản đó.</p>

    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", margin: "8px 0" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")}
        style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Kỳ
        <input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
    </div>

    {f && <div className="panel">
      <h2>{f.loai === "ts" ? "Thêm tài sản cố định / công cụ" : "Thêm chi phí trả trước"}</h2>
      <div className="grid2">
        <label>Mã <input value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} /></label>
        <label>Tên <input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
        <label>Nhóm
          <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
            {Object.entries((f.loai === "ts" ? meta?.asset_kinds : meta?.prepaid_kinds) || {})
              .map(([k, v]: any) => <option key={k} value={k}>{v?.ten || k}</option>)}
          </select></label>
        <label>Bộ phận sử dụng
          <input value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })} /></label>
        {f.loai === "ts" && <label>Ngày mua
          <input type="date" value={f.purchase_date}
                 onChange={(e) => setF({ ...f, purchase_date: e.target.value })} /></label>}
        <label>Bắt đầu tính {f.loai === "ts" ? "khấu hao" : "phân bổ"}
          <input type="date" value={f.start_date}
                 onChange={(e) => setF({ ...f, start_date: e.target.value })} /></label>
        <label>{f.loai === "ts" ? "Nguyên giá" : "Số tiền"}
          <input type="number" step={100000} value={f.cost}
                 onChange={(e) => setF({ ...f, cost: e.target.value })} /></label>
        <label>Số kỳ {f.loai === "ts" ? "khấu hao (tháng)" : "phân bổ"}
          <input type="number" value={f.depr_months}
                 onChange={(e) => setF({ ...f, depr_months: e.target.value })} /></label>
      </div>
      <button className="act teal" disabled={luu || !f.code || !f.name || !f.start_date}
              onClick={ghi}>{luu ? "Đang ghi…" : "Ghi"}</button>{" "}
      <button className="act grey" onClick={() => setF(null)}>Đóng</button>
    </div>}

    {tab === "ts" && bang(ts, "Nguyên giá", "Số tháng KH", "ts")}
    {tab === "tt" && bang(tt, "Số tiền", "Số kỳ PB", "tt")}
    {tab === "kh" && bangKy(kh, "kh", "Khấu hao")}
    {tab === "pb" && bangKy(pb, "pb", "Phân bổ chi phí trả trước")}

    {tep && <DinhKem doiTuong="hoa_don" doiTuongId={tep.ma} loai="chung_tu"
      tieuDe={`Hồ sơ tài sản – ${tep.ten} (${tep.ma})`}
      goi={"Hóa đơn mua, biên bản bàn giao, giấy tờ đăng ký. Hồ sơ tài sản là thứ kiểm toán hỏi khi " +
           "đối chiếu nguyên giá và ngày bắt đầu khấu hao."} />}
  </>);
}

export default function Page() { return <Shell><TaiSan /></Shell>; }
