"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
// 5.9.3 Cap phat tai san · 09/10/2026 (Chu tich chot 08/10 "cap phat tai san do HCNS lam").
// So nay KHONG phai so tai san thu hai: nguyen gia va khau hao van o the TSCD ngay tren. No tra
// loi dung MOT cau — mon nao dang o tay ai — va do la cau HCNS phai hoi moi lan co nguoi nghi viec.
import { CapPhatTaiSan } from "@/components/DeNghiMuaCapPhat";
import { useHoi } from "@/components/HopHoi";

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
  const { xacNhan, nhap, hop } = useHoi();
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
      // ĐỢT TSCD-1 — `asset_account` CHỈ của tài sản cố định, nằm trong nhánh `if (la)`: chi phí
      // trả trước có đường của nó (`242` → 2421/2422, Đợt TKC-5 suy theo số kỳ).
      if (la) Object.assign(body, { purchase_date: f.purchase_date || null, cost: soTien(f.cost),
        asset_account: f.asset_account || "",
        depr_months: Number(f.depr_months) || 0, salvage: soTien(f.salvage) });
      else Object.assign(body, { amount: soTien(f.cost), months: Number(f.depr_months) || 1,
        // ĐỢT CPTT-1 — hai ô này CHỈ của chi phí trả trước, nên nằm trong nhánh `else` chứ không
        // rải chung: tài sản cố định có đường khấu hao riêng với TK của riêng nó.
        expense_account: f.expense_account || "", project_code: f.project_code || "" });
      await api(la ? "/fixed-assets" : "/prepaid", { method: "POST", json: body });
      toast("Đã ghi. Nhớ đính kèm hóa đơn và biên bản bàn giao."); setF(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const ghiSo = async (loai: "kh" | "pb") => {
    const url = loai === "kh" ? `/fixed-assets/depreciation/${ky}/post` : `/prepaid/allocation/${ky}/post`;
    const ten = loai === "kh" ? "khấu hao" : "phân bổ chi phí trả trước";
    if (!await xacNhan(`Ghi sổ ${ten} kỳ ${ky}?\n\nĐối chiếu bảng bên dưới trước khi bấm — bút toán ` +
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
        asset_account: "", expense_account: "", project_code: "", quantity: 1, note: "" })}>+ Thêm</button>}
      {loai === "tt" && rows.some((a: any) => a.expense_account === CANH_BAO_TK_CU) &&
        <p className="muted small">
          <Tag cls="warn">{rows.filter((a: any) => a.expense_account === CANH_BAO_TK_CU).length} khoản đang phân bổ vào {CANH_BAO_TK_CU}</Tag>{" "}
          Những khoản này nhập trước khi màn hình có ô chọn, hoặc nạp từ Excel — đường nạp hàng
          loạt chưa có cột TK chi phí (đợt riêng). Sửa là việc của Kế toán, máy không tự đổi.
        </p>}
      <table><thead><tr><th>Mã</th><th>Tên</th><th>Nhóm</th><th>Bộ phận</th>
        {loai === "tt" && <><th>TK chi phí</th><th>Công trình</th></>}<th>Bắt đầu</th>
        <th className="num">{tienTen}</th><th className="num">{thangTen}</th>
        <th className="num">Mỗi kỳ</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{rows.length ? rows.map((a: any) => <tr key={a.id}>
          <td className="mono">{a.code}</td><td><b>{a.name}</b></td>
          <td className="muted">{a.kind_name}</td><td className="muted">{a.department}</td>
          {loai === "tt" && <>
            <td className="mono">{a.expense_account === CANH_BAO_TK_CU
              ? <Tag cls="warn">{a.expense_account}</Tag> : a.expense_account}</td>
            <td className="mono muted">{a.project_code || "—"}</td></>}
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

  return (<>{hop}
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

    {f && (() => { const loaiTs = f.loai === "ts" ? (meta?.asset_kinds || {})[f.kind] : null; return (
      <div className="panel">
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
        {/* ĐỢT TSCD-1 08/11/2026 — Ô TK NGUYÊN GIÁ.
            Đo trên hệ thống thật 08/11/2026: `ASSET_KINDS` mời chọn BỐN loại mà chỉ MỘT lưu được.
            `211` là tài khoản CHA (2111 nhà cửa / 2112 máy móc / 2113 phương tiện); ba loại còn
            lại trả 422 vì danh mục chưa có `2143` / `212` / `217`. Form phải biết điều đó TRƯỚC
            khi người dùng bấm Lưu, và phải nói ra ĐÚNG số hiệu cần mở — ẩn loại ấy đi thì không
            ai biết vì sao thiếu, và sẽ không ai mở hai tài khoản kia. */}
        {f.loai === "ts" && (loaiTs?.dung_duoc === false
          ? <label>TK nguyên giá
              <div><Tag cls="red">chưa dùng được</Tag>{" "}
                <span className="muted">Danh mục tài khoản chưa có <b>{(loaiTs.thieu || []).join(" và ")}</b> —
                mở ở màn Danh mục tài khoản rồi quay lại, hoặc chọn loại tài sản khác.</span></div></label>
          : (loaiTs?.tk_nguyen_gia_chon || []).length > 1
            ? <label>TK nguyên giá
                <select value={f.asset_account}
                        onChange={(e) => setF({ ...f, asset_account: e.target.value })}>
                  <option value="">— chọn tài khoản —</option>
                  {(loaiTs?.tk_nguyen_gia_chon || []).map((t: any) =>
                    <option key={t.ma} value={t.ma}>{t.ma} — {t.ten}</option>)}
                </select></label>
            : <label>TK nguyên giá
                <input readOnly value={(loaiTs?.tk_nguyen_gia_chon || []).map((t: any) =>
                  t.ma + " — " + t.ten).join("") || ""} /></label>)}
        {f.loai === "tt" && <label>TK chi phí nhận phân bổ
          <select value={f.expense_account}
                  onChange={(e) => setF({ ...f, expense_account: e.target.value })}>
            <option value="">— chọn tài khoản —</option>
            {(meta?.tk_chi_phi || []).map((t: any) =>
              <option key={t.ma} value={t.ma}>{t.ma} — {t.ten}</option>)}
          </select></label>}
        {f.loai === "tt" && <label>Mã công trình (tour)
          <input value={f.project_code} placeholder="để trống nếu không thuộc chuyến nào"
                 onChange={(e) => setF({ ...f, project_code: e.target.value })} /></label>}
        <label>Số kỳ {f.loai === "ts" ? "khấu hao (tháng)" : "phân bổ"}
          <input type="number" value={f.depr_months}
                 onChange={(e) => setF({ ...f, depr_months: e.target.value })} /></label>
      </div>
      <button className="act teal"
              disabled={luu || !f.code || !f.name || !f.start_date
                        || (f.loai === "ts" && (loaiTs?.dung_duoc === false
                            || ((loaiTs?.tk_nguyen_gia_chon || []).length > 1 && !f.asset_account)))}
              onClick={ghi}>{luu ? "Đang ghi…" : "Ghi"}</button>{" "}
      <button className="act grey" onClick={() => setF(null)}>Đóng</button>
      </div>); })()}

    {tab === "ts" && bang(ts, "Nguyên giá", "Số tháng KH", "ts")}
    {tab === "tt" && bang(tt, "Số tiền", "Số kỳ PB", "tt")}
    {tab === "kh" && bangKy(kh, "kh", "Khấu hao")}
    {tab === "pb" && bangKy(pb, "pb", "Phân bổ chi phí trả trước")}

    {tep && <DinhKem doiTuong="hoa_don" doiTuongId={tep.ma} loai="chung_tu"
      tieuDe={`Hồ sơ tài sản – ${tep.ten} (${tep.ma})`}
      goi={"Hóa đơn mua, biên bản bàn giao, giấy tờ đăng ký. Hồ sơ tài sản là thứ kiểm toán hỏi khi " +
           "đối chiếu nguyên giá và ngày bắt đầu khấu hao."} />}
    <div className="panel"><CapPhatTaiSan /></div>
  </>);
}

// ĐỢT CPTT-1 07/11/2026 — TK mặc định CŨ của chi phí trả trước. Trước đợt này màn hình
// không có ô chọn nên mọi khoản rơi vào đây, và đường nạp Excel vẫn còn rơi vào đây
// (đợt riêng). Hiện ra để Kế toán sửa, KHÔNG tự đổi — đổi hộ là đoán thay người.
const CANH_BAO_TK_CU = "6423";

export default function Page() { return <Shell><TaiSan /></Shell>; }
