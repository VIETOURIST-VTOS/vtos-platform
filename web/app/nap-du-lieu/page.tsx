"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Nạp dữ liệu vào VTOS – một cửa cho người nhập tay, cho tệp tải lên, và cho tác vụ AI.
 *
 *  Màn hình cố ý bắt đi hai bước: KIỂM TRA rồi mới NẠP. Bấm một nút rồi 500 dòng rác nằm trong sổ là
 *  chuyện của vài giây; dọn nó là chuyện của vài ngày. */
const PHONG: Record<string, string> = { dieu_hanh: "Điều hành", doi_xe: "Đội xe", hcns: "Hành chính & Nhân sự",
  kd_le: "Kinh doanh", ketoan: "Kế toán", visa: "Ban Visa", marketing: "Marketing", ban_tgd: "Ban TGĐ" };

function theoPhong(ds: any[]) {
  const g: Record<string, any[]> = {};
  ds.forEach((b) => { (g[b.phong_ban || "khac"] ||= []).push(b); });
  return g;
}

function NapDuLieu() {
  const { user, toast } = useShell();
  const [bo, setBo] = useState<any>(null);
  const [loai, setLoai] = useState("");
  const [rows, setRows] = useState<any[]>([]);
  const [tenTep, setTenTep] = useState("");
  const [kt, setKt] = useState<any>(null);
  const [ls, setLs] = useState<any[]>([]);
  const [boQua, setBoQua] = useState(false);
  const [dang, setDang] = useState(false);
  // Quyền nạp đọc theo TỪNG BỘ NẠP do máy chủ công bố, không chép lại danh sách vai trò ở đây: chép là
  // sớm muộn hai bên lệch nhau, và bên lỏng hơn luôn là bên người dùng nhìn thấy.
  const chon0 = bo?.bo_nap?.find((b: any) => b.ma === loai);
  const canNap = !!chon0?.vai_tro?.includes(user?.role || "");

  const load = useCallback(async () => {
    try { const d = await api<any>("/nap-du-lieu/bo-nap"); setBo(d); if (!loai) setLoai(d.bo_nap[0]?.ma || "");
          setLs(await api("/nap-du-lieu/lich-su")); }
    catch (e) { toast(errMsg(e), true); }
  }, [toast, loai]);
  useEffect(() => { load(); }, [load]);

  const chon = chon0;

  const taiMau = () => {
    const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
    fetch(`/api/v1/nap-du-lieu/mau/${loai}`, { headers: h }).then((r) => r.text()).then((t) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob(["﻿" + t], { type: "text/csv;charset=utf-8" }));
      a.download = `mau_${loai}.csv`; a.click();
    }).catch(() => toast("Không tải được tệp mẫu", true));
  };

  const kiemTraTep = async (f: File) => {
    setDang(true); setKt(null);
    try {
      const fd = new FormData(); fd.append("loai", loai); fd.append("tep", f);
      const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
      const r = await fetch("/api/v1/nap-du-lieu/kiem-tra-tep", { method: "POST", headers: h, body: fd });
      const d = await r.json();
      if (!r.ok) throw { status: r.status, message: d?.detail || "Không đọc được tệp" };
      setKt(d); setRows(d.rows || []); setTenTep(d.ten_tep || f.name);
      toast(`Đã đọc ${d.so_dong} dòng – xem kết quả kiểm tra bên dưới`);
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  const nap = async () => {
    setDang(true);
    try {
      const d = await api<any>("/nap-du-lieu/nap", { method: "POST", json: {
        loai, rows, bo_qua_dong_loi: boQua, ten_tep: tenTep, nguon: "nguoi_nhap" } });
      setKt(d); toast(d.message);
      if (d.da_nap > 0) { setRows([]); setTenTep(""); }
      setLs(await api("/nap-du-lieu/lich-su"));
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  if (!bo) return <p className="muted">Đang tải…</p>;
  return (<>
    <h1>Nạp dữ liệu vào VTOS</h1>
    <p className="muted">Người nhập, tệp tải lên và tác vụ AI đi qua <b>cùng một cửa</b>: cùng bộ kiểm tra,
      cùng khóa chống trùng, cùng nhật ký. Nếu mỗi đường một kiểu kiểm tra thì cái chặt nhất trở nên vô
      nghĩa — người ta chỉ cần đi đường lỏng nhất.</p>

    <div className="panel">
      <h2>1. Chọn loại dữ liệu</h2>
      <label>Loại
        <select value={loai} onChange={(e) => { setLoai(e.target.value); setKt(null); setRows([]); }}>
          {Object.entries(theoPhong(bo.bo_nap)).map(([pb, ds]: any) =>
            <optgroup key={pb} label={PHONG[pb] || pb}>
              {ds.map((b: any) => <option key={b.ma} value={b.ma}>{b.ten}</option>)}
            </optgroup>)}
        </select></label>
      {chon && <>
        <p className="muted">{chon.mo_ta}</p>
        <p className="muted">Khóa chống trùng: <b>{chon.khoa_chong_trung}</b></p>
        {!canNap && <p className="muted"><Tag cls="warn">chỉ xem</Tag> Loại dữ liệu này thuộc {PHONG[chon.phong_ban] || "phòng khác"}.
          Anh/chị xem được cấu trúc và kiểm tra thử, nhưng người nạp phải là người của phòng đó — để nhật ký
          ghi đúng tên người chịu trách nhiệm về số liệu.</p>}
        <div className="wrap"><table>
          <thead><tr><th>Cột trong tệp</th><th>Bắt buộc</th><th>Ví dụ</th><th>Ghi chú</th></tr></thead>
          <tbody>{chon.cot.map((c: any) => <tr key={c.key}>
            <td>{c.ten}</td>
            <td>{c.bat_buoc ? <Tag cls="red">bắt buộc</Tag> : <span className="muted">không</span>}</td>
            <td className="muted">{c.vi_du}</td><td className="muted">{c.ghi_chu}</td>
          </tr>)}</tbody></table></div>
        <button className="act grey" style={{ marginTop: 8 }} onClick={taiMau}>Tải tệp mẫu (.csv)</button>
      </>}
    </div>

    <div className="panel">
      <h2>2. Tải tệp lên và kiểm tra</h2>
      <p className="muted">Bước này <b>chưa ghi gì</b> vào hệ thống. Nhận tệp .csv hoặc .xlsx, hàng đầu là
        tên cột — tên cột viết hoa hay thường đều được.</p>
      <input type="file" accept=".csv,.xlsx,.xlsm" disabled={dang}
             onChange={(e) => { const f = e.target.files?.[0]; if (f) kiemTraTep(f); }} />
      {tenTep && <p className="muted">Tệp: <b>{tenTep}</b> · {rows.length} dòng</p>}
    </div>

    {kt && <div className="panel">
      <h2>3. Kết quả kiểm tra</h2>
      <div className="kpis">
        <div className="kpi"><b>{kt.so_dong}</b><span>dòng trong tệp</span></div>
        <div className="kpi"><b style={{ color: "var(--ok, green)" }}>{kt.hop_le}</b><span>hợp lệ, sẽ nạp</span></div>
        <div className="kpi"><b className="muted">{kt.da_co}</b><span>đã có trong hệ thống — bỏ qua</span></div>
        <div className="kpi"><b style={{ color: kt.dong_loi ? "var(--red)" : undefined }}>{kt.dong_loi}</b><span>dòng lỗi</span></div>
      </div>
      {kt.cot_khong_dung?.length > 0 && <p className="muted">Cột không dùng đến:
        <b> {kt.cot_khong_dung.join(", ")}</b> — kiểm tra lại xem có nạp nhầm tệp không.</p>}
      <div className="wrap"><table>
        <thead><tr><th>Dòng</th><th>Nội dung</th><th>Kết quả</th></tr></thead>
        <tbody>{kt.dong.slice(0, 200).map((d: any) => <tr key={d.dong}>
          <td className="muted">{d.dong}</td>
          <td>{d.tom_tat}</td>
          <td>{d.loi.length ? d.loi.map((l: string, i: number) => <div key={i}><Tag cls="red">{l}</Tag></div>)
            : d.da_co ? <Tag cls="warn">đã có ({d.da_co})</Tag> : <Tag cls="ok">hợp lệ</Tag>}
            {d.canh_bao?.map((c: string, i: number) => <div key={i} className="muted">{c}</div>)}</td>
        </tr>)}</tbody></table></div>
      {kt.da_nap === undefined && canNap && <div style={{ marginTop: 10 }}>
        {kt.dong_loi > 0 && <label style={{ display: "block" }}>
          <input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={boQua}
                 onChange={(e) => setBoQua(e.target.checked)} />
          Bỏ qua {kt.dong_loi} dòng lỗi và chỉ nạp phần hợp lệ
        </label>}
        <button className="act teal" disabled={dang || (kt.dong_loi > 0 && !boQua) || kt.hop_le === 0}
                onClick={nap}>{dang ? "Đang nạp…" : `Nạp ${kt.hop_le} dòng vào hệ thống`}</button>
        {kt.dong_loi > 0 && !boQua && <p className="muted">Còn dòng lỗi nên nút nạp đang khóa. Sửa tệp rồi
          kiểm tra lại, hoặc tích ô trên để nạp phần hợp lệ — bỏ qua dòng lỗi là một quyết định, không phải
          một mặc định.</p>}
      </div>}
      {kt.da_nap !== undefined && <p><b>{kt.message}</b></p>}
    </div>}

    <div className="panel wrap">
      <h2>Nhật ký nạp</h2>
      <p className="muted">Để trả lời được câu &quot;con số này ở đâu ra&quot; vào đúng lúc khó nhất.</p>
      <table><thead><tr><th>Lúc</th><th>Loại</th><th>Tệp</th><th>Nguồn</th><th>Dòng</th><th>Đã nạp</th>
        <th>Đã có</th><th>Lỗi</th><th>Người nạp</th><th>Mã băm</th></tr></thead>
        <tbody>{ls.length ? ls.map((r) => <tr key={r.id}>
          <td className="muted">{fmtDT(r.luc)}</td><td>{r.ten_bo_nap}</td>
          <td className="muted">{r.ten_tep || "—"}</td>
          <td>{r.nguon === "ai" ? <Tag cls="warn">AI: {r.tac_nhan}</Tag> : <span className="muted">{r.nguon_ten}</span>}</td>
          <td className="num">{r.so_dong}</td><td className="num">{r.da_nap}</td>
          <td className="num muted">{r.bo_qua_da_co}</td>
          <td className="num">{r.dong_loi}{r.bo_qua_dong_loi ? " (bỏ qua)" : ""}</td>
          <td className="muted">{r.boi}</td><td className="muted">{r.hash}</td>
        </tr>) : <tr><td colSpan={10} className="muted">Chưa có lần nạp nào.</td></tr>}</tbody></table>
    </div>
  </>);
}

export default function Page() { return <Shell><NapDuLieu /></Shell>; }
