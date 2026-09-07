"use client";
import { useEffect, useState, useCallback } from "react";
import { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Vị trí AI & quyền hạn (đặc tả 07/9/2026, phần C).
 *
 *  Bảng này ĐIỀU KHIỂN hành vi thật: robot hộp thư đọc ô "Soạn và gửi tin cho khách" của vai trò chủ quản
 *  trước mỗi lần định gửi. Hạ ô đó xuống mức 2 là hộp thư ngừng tự gửi ngay, nội dung nằm ở nháp. */
const TABS: [string, string][] = [["bang", "Bảng quyền theo vị trí"], ["nhat_ky", "Nhật ký AI"], ["bao_cao", "Báo cáo"]];
const MAU: Record<number, string> = { 0: "", 1: "navy", 2: "navy", 3: "warn", 4: "ok" };

export default function AiRolesPage() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const canSua = ["chutich", "tgd", "cntt"].includes(role);
  const [tab, setTab] = useState("bang");
  const [b, setB] = useState<any>(null);
  const [log, setLog] = useState<any>(null);
  const [rp, setRp] = useState<any>(null);

  const load = useCallback(() => { api("/ai/positions").then(setB).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (tab === "nhat_ky") api("/ai/runs?limit=200").then(setLog).catch((e) => toast(errMsg(e), true));
    if (tab === "bao_cao") api("/ai/report?so_ngay=7").then(setRp).catch((e) => toast(errMsg(e), true));
  }, [tab, toast]);

  const datMuc = async (vai: string, tac_vu: string, muc: number, hanMucCu: any) => {
    let han_muc = hanMucCu || {};
    if (muc === 3) {
      const kg = window.prompt("Khung giờ AI được tự gửi (ví dụ 08:00-21:00):", han_muc.khung_gio || "08:00-21:00");
      if (kg === null) return;
      const sl = window.prompt("Số lượt tối đa mỗi ngày:", String(han_muc.so_luot_ngay || 30));
      if (sl === null) return;
      const nd = window.prompt("Loại nội dung được phép gửi:", han_muc.loai_noi_dung || "lịch khởi hành, giá công bố, chính sách cọc và hủy, xin tên và số điện thoại");
      if (nd === null) return;
      const hk = window.prompt("Người hậu kiểm trong 24 giờ (mã vai trò hoặc tên):", han_muc.nguoi_hau_kiem || "ptgd_mkt");
      if (hk === null) return;
      han_muc = { khung_gio: kg.trim(), so_luot_ngay: Number(sl) || 0, loai_noi_dung: nd.trim(), nguoi_hau_kiem: hk.trim() };
    } else han_muc = {};
    try {
      const r = await api<any>("/ai/positions", { method: "PUT", json: { vai_tro: vai, tac_vu, muc, han_muc } });
      toast(r.message); load();
    } catch (e) { toast(errMsg(e), true); }
  };

  const tatKhan = async (dung: boolean) => {
    let ly_do = "";
    if (dung) {
      const v = window.prompt("Lý do tạm dừng toàn bộ AI đối ngoại (bắt buộc):", "");
      if (!v || !v.trim()) { toast("Chưa ghi lý do – không tạm dừng", true); return; }
      ly_do = v.trim();
    }
    try {
      const r = await api<any>("/ai/pause", { method: "POST", json: { tam_dung: dung, ly_do } });
      toast(r.message); load();
    } catch (e) { toast(errMsg(e), true); }
  };

  const hauKiem = async (id: number, ket_luan: string) => {
    const ghi_chu = window.prompt("Ghi chú hậu kiểm (không bắt buộc):", "") || "";
    try {
      const r = await api<any>(`/ai/runs/${id}/hau-kiem`, { method: "POST", json: { ket_luan, ghi_chu } });
      toast(r.message); api("/ai/runs?limit=200").then(setLog); api("/ai/report?so_ngay=7").then(setRp);
    } catch (e) { toast(errMsg(e), true); }
  };

  return <>
    <h1>Vị trí AI & quyền hạn</h1>

    {b && <div className={"gate " + (b.tam_dung ? "fail" : b.duoc_tu_gui ? "pass" : "")} style={{ marginBottom: 12 }}>
      {b.tam_dung
        ? <><b>AI đối ngoại đang TẠM DỪNG.</b> Mọi ô mức 3 đã hạ xuống mức 2 – AI vẫn soạn nháp, không tự gửi.
            Lý do: {b.tam_dung_ly_do} · {b.tam_dung_boi} · {b.tam_dung_luc ? fmtDT(b.tam_dung_luc) : ""}</>
        : b.duoc_tu_gui
          ? <><b>AI đang được tự gửi tin cho khách.</b> Đã gửi {b.da_gui_hom_nay} lượt hôm nay.</>
          : <><b>AI không tự gửi tin lúc này</b> – {b.ly_do_khong_tu_gui}. Nội dung vẫn được soạn và để ở nháp.</>}
      {["chutich", "tgd", "cntt"].includes(role) && <div style={{ marginTop: 8 }}>
        <button className="act" style={{ margin: 0 }} onClick={() => tatKhan(!b.tam_dung)}>
          {b.tam_dung ? "Mở lại AI đối ngoại" : "Tạm dừng toàn bộ AI đối ngoại"}</button>
      </div>}
    </div>}

    <div className="row" style={{ gap: 6, flexWrap: "wrap", margin: "10px 0" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }}
        onClick={() => setTab(k)}>{l}</button>)}
    </div>

    {tab === "bang" && b && <>
      <p className="muted">Bảng này điều khiển hành vi thật: robot hộp thư đọc ô “{b.nhom_viec.tin_khach}” của
        vai trò chủ quản ({b.chu_quan_hop_thu}) trước mỗi lần định gửi. Mức 3 bắt buộc khai đủ hạn mức.</p>
      <div className="scroll"><table><thead><tr>
        <th>Vị trí</th>{b.cot.map((c: string) => <th key={c} style={{ fontSize: 11 }}>{b.nhom_viec[c]}</th>)}
      </tr></thead><tbody>{b.rows.map((r: any) => <tr key={r.vai_tro}>
        <td><b>{r.ten}</b></td>
        {b.cot.map((c: string) => { const o = r.o[c]; return <td key={c} style={{ textAlign: "center" }}>
          {canSua
            ? <select value={o.muc} onChange={(e) => datMuc(r.vai_tro, c, Number(e.target.value), o.han_muc)}>
                {[0, 1, 2, 3, 4].map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            : <Tag cls={MAU[o.muc]}>{o.muc}</Tag>}
          {o.muc === 3 && o.muc_ap_dung === 2 && <div><Tag cls="warn">đang hạ về 2</Tag></div>}
          {o.thieu_han_muc?.length > 0 && <div><Tag cls="warn">thiếu hạn mức</Tag></div>}
          {o.muc === 3 && o.han_muc?.khung_gio && <div className="muted" style={{ fontSize: 10 }}>
            {o.han_muc.khung_gio} · {o.han_muc.so_luot_ngay}/ngày</div>}
        </td>; })}
      </tr>)}</tbody></table></div>

      <h3 style={{ marginTop: 16 }}>Bốn mức</h3>
      {Object.entries(b.muc).map(([k, v]: any) => <p key={k} className="muted" style={{ margin: "2px 0" }}>
        <b>{k}</b> — {v}</p>)}
      <p className="muted" style={{ marginTop: 6 }}>Mức 4 không có nghĩa là tin tưởng AI hơn mức 3. Nó là loại khác:
        được tự động vì quy tắc kiểm chứng được, không phải vì mô hình thông minh. Việc do mô hình ngôn ngữ
        làm thì trần là mức 3.</p>

      <h3 style={{ marginTop: 16 }}>AI không được làm, ở bất kỳ mức nào</h3>
      {(b.viec_ai_khong_duoc_lam || []).map((x: string, i: number) => <p key={i} className="muted" style={{ margin: "2px 0" }}>• {x}</p>)}
    </>}

    {tab === "nhat_ky" && log && <>
      <p className="muted">Mọi lần phần mềm dùng mô hình ngôn ngữ. Tin robot tự gửi cho khách nằm ở trạng thái
        chờ hậu kiểm cho tới khi có người đọc lại.</p>
      <div className="scroll"><table><thead><tr>
        <th>Thời điểm</th><th>Việc</th><th>Mức</th><th>Đối tượng</th><th>Nguồn</th><th>Nội dung</th>
        <th>Trạng thái</th><th></th></tr></thead>
        <tbody>{log.rows.map((r: any) => <tr key={r.id}>
          <td>{fmtDT(r.ts)}</td><td>{r.tac_vu_ten}</td><td style={{ textAlign: "center" }}>{r.muc}</td>
          <td>{r.ref || "—"}</td><td>{r.nguon === "claude" ? r.mo_hinh || "claude" : "quy tắc"}</td>
          <td style={{ maxWidth: 320, fontSize: 11 }}>{(r.ket_qua || "").slice(0, 200)}</td>
          <td>{r.trang_thai === "cho_hau_kiem" ? <Tag cls="warn">{r.trang_thai_ten}</Tag>
            : r.trang_thai === "thu_hoi" ? <Tag cls="fail">{r.trang_thai_ten}</Tag> : r.trang_thai_ten}</td>
          <td>{r.trang_thai === "cho_hau_kiem" && ["chutich", "tgd", "cntt", "ptgd_mkt", "gd_kd", "tp_kd"].includes(role) &&
            <span style={{ display: "flex", gap: 4 }}>
              <button className="act" style={{ margin: 0 }} onClick={() => hauKiem(r.id, "chap_nhan")}>Đạt</button>
              <button className="act grey" style={{ margin: 0 }} onClick={() => hauKiem(r.id, "da_sua")}>Đã sửa</button>
              <button className="act grey" style={{ margin: 0 }} onClick={() => hauKiem(r.id, "thu_hoi")}>Thu hồi</button>
            </span>}</td>
        </tr>)}</tbody></table></div>
      {log.tong_hop && <p className="muted" style={{ marginTop: 8 }}>
        Tổng {log.tong_hop.tong} lần · chờ hậu kiểm {log.tong_hop.cho_hau_kiem} · lỗi gọi mô hình {log.tong_hop.loi_goi_mo_hinh}</p>}
    </>}

    {tab === "bao_cao" && rp && <>
      <h3>Bảy ngày gần nhất</h3>
      <div className="scroll"><table><tbody>
        <tr><td>AI đã làm</td><td><b>{rp.tong}</b> lần</td></tr>
        <tr><td>Đang chờ hậu kiểm</td><td><b>{rp.cho_hau_kiem}</b></td></tr>
        <tr><td>Đã hậu kiểm</td><td><b>{rp.da_hau_kiem}</b></td></tr>
        <tr><td>Bị người sửa lại hoặc thu hồi</td><td><b>{rp.bi_sua_hoac_thu_hoi}</b></td></tr>
        <tr><td>Tỷ lệ bị sửa</td><td><b>{rp.ty_le_bi_sua === null ? "chưa có số" : `${(rp.ty_le_bi_sua * 100).toFixed(1)}%`}</b></td></tr>
        <tr><td>Lỗi gọi mô hình</td><td><b>{rp.loi_goi_mo_hinh}</b></td></tr>
      </tbody></table></div>
      <p className="muted">{rp.ghi_chu_ty_le}</p>
      <h3 style={{ marginTop: 14 }}>Theo nhóm việc</h3>
      <div className="scroll"><table><tbody>{Object.entries(rp.theo_tac_vu || {}).map(([k, v]: any) =>
        <tr key={k}><td>{rp.ten_tac_vu?.[k] || k}</td><td><b>{v}</b></td></tr>)}</tbody></table></div>
      {rp.cho_hau_kiem_chi_tiet?.length > 0 && <>
        <h3 style={{ marginTop: 14 }}>Đang chờ người đọc lại</h3>
        <div className="scroll"><table><tbody>{rp.cho_hau_kiem_chi_tiet.map((r: any) =>
          <tr key={r.id}><td>{fmtDT(r.ts)}</td><td>{r.ref}</td><td style={{ fontSize: 11 }}>{r.ket_qua}</td></tr>)}</tbody></table></div>
      </>}
    </>}
  </>;
}
