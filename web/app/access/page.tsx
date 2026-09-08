"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Tài khoản & phân quyền (đặc tả 07/9/2026, phần B).
 *
 *  Màn hình này CÔNG BỐ ma trận quyền chứ không sửa nó: ma trận nằm trong mã nguồn, có phép thử tự động
 *  canh và có lịch sử thay đổi trong git. Thứ sửa được ở đây chỉ có ba – ai ở vai trò nào, tài khoản mở
 *  hay khóa, và pháp nhân chủ quản. */
const TABS: [string, string][] = [
  ["accounts", "Tài khoản"], ["matrix", "Ma trận quyền"],
  ["gaps", "Chênh lệch cần xử lý"], ["audit", "Nhật ký quyền"],
];
const GAP_TEN: Record<string, string> = {
  nhan_su_chua_co_tai_khoan: "Nhân sự đang làm việc chưa có tài khoản",
  tai_khoan_bo_quen: "Tài khoản hoạt động nhưng không có hồ sơ (hoặc hồ sơ đã nghỉ)",
  con_mat_khau_tam: "Còn mật khẩu tạm, chưa đổi",
  bo_hoang: "Chưa đăng nhập bao giờ, hoặc bỏ hoang",
  chua_gan_phap_nhan: "Chưa gán pháp nhân chủ quản",
  ho_so_trung: "Hồ sơ trùng: cùng tên, cùng phòng, hai mã",
  ngoai_le_vo_han: "Ngoại lệ quyền KHÔNG THỜI HẠN – rà lại mỗi kỳ",
};
const ACT_TEN: Record<string, string> = {
  sua_tai_khoan: "Sửa tài khoản", dat_lai_mat_khau: "Đặt lại mật khẩu", doi_mat_khau: "Đổi mật khẩu",
  cap_ngoai_le_quyen: "Cấp ngoại lệ quyền", thu_hoi_ngoai_le_quyen: "Thu hồi ngoại lệ", hau_kiem_ai: "Hậu kiểm AI",
  dang_nhap: "Đăng nhập", xuat_ma_tran_quyen: "Xuất ma trận",
};

function AccessPage() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const canWrite = ["cntt", "hcns", "chutich", "tgd"].includes(role);
  const laLanhDao = ["chutich", "tgd"].includes(role);
  const [tab, setTab] = useState("accounts");
  const [acc, setAcc] = useState<any>(null);
  const [mt, setMt] = useState<any>(null);
  const [gaps, setGaps] = useState<any>(null);
  const [log, setLog] = useState<any>(null);
  const [q, setQ] = useState("");
  const [loc, setLoc] = useState("");          // bộ lọc nhanh
  const [grants, setGrants] = useState<any>(null);

  const loadAcc = useCallback(() => { api("/access/accounts").then(setAcc).catch((e) => toast(errMsg(e), true)); }, [toast]);
  const loadGaps = useCallback(() => { api("/access/gaps").then(setGaps).catch(() => {}); }, []);
  useEffect(() => { loadAcc(); loadGaps(); api("/access/grants").then(setGrants).catch(() => {}); }, [loadAcc, loadGaps]);
  useEffect(() => {
    if (tab === "matrix" && !mt) api("/access/matrix").then(setMt).catch((e) => toast(errMsg(e), true));
    if (tab === "audit") api("/access/audit").then(setLog).catch(() => {});
  }, [tab, mt, toast]);

  const send = async (path: string, json: any, method = "POST") => {
    try {
      const r = await api<any>(path, { method, json });
      toast(r.message || "Đã cập nhật"); loadAcc(); loadGaps();
    } catch (e) { toast(errMsg(e), true); }
  };

  const doiVaiTro = (r: any, moi: string) => {
    if (moi === r.role) return;
    const nhay = (acc?.vai_tro_nhay_cam || []).includes(moi);
    const ly_do = window.prompt(
      `Đổi vai trò ${r.full_name} thành ${acc.roles[moi]}.` +
      (nhay ? "\n\nĐây là vai trò nhìn được toàn bộ tiền và sổ sách – chỉ Chủ tịch hoặc TGĐ đổi được." : "") +
      "\n\nLý do (bắt buộc):", "");
    if (!ly_do || !ly_do.trim()) { toast("Chưa ghi lý do – không đổi", true); return; }
    send(`/access/role-change/${r.id}`, { role: moi, reason: ly_do.trim() });
  };

  const taoTaiKhoan = async () => {
    const ho_ten = window.prompt("Họ tên đầy đủ:", ""); if (!ho_ten?.trim()) return;
    const ma_nv = window.prompt("Mã nhân viên (cũng là mật khẩu tạm):", ""); if (!ma_nv?.trim()) return;
    const role = window.prompt("Mã vai trò (ví dụ ketoan, nv_kd, hcns):", "ketoan"); if (!role?.trim()) return;
    const department = window.prompt("Phòng (ví dụ ketoan, kd_le, dieu_hanh):", "ketoan") || "";
    const ngoai = window.confirm("Người này NGOÀI biên chế (thuê ngoài, không có trong bảng lương)?\n\nOK = ngoài biên chế · Cancel = trong biên chế");
    try {
      const r = await api<any>("/access/accounts", { method: "POST", json: {
        ho_ten: ho_ten.trim(), ma_nv: ma_nv.trim(), role: role.trim(),
        department: department.trim(), ngoai_bien_che: ngoai } });
      toast(r.message); loadAcc(); loadGaps();
    } catch (e) { toast(errMsg(e), true); }
  };

  const taiExcel = async () => {
    try {
      const res = await fetch("/api/v1/access/matrix.xlsx", { headers: { Authorization: `Bearer ${getToken() || ""}` } });
      if (!res.ok) throw new Error(`Máy chủ trả ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `MA_TRAN_PHAN_QUYEN_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(a.href);
      toast("Đã tải bản Excel để ký rà quyền");
    } catch (e: any) { toast(e?.message || "Không tải được", true); }
  };

  const rows = (acc?.rows || []).filter((r: any) => {
    const k = q.trim().toLowerCase();
    if (k && ![r.full_name, r.username, r.staff_code, r.role_name].join(" ").toLowerCase().includes(k)) return false;
    if (loc === "khoa") return !r.active;
    if (loc === "mat_khau_tam") return r.must_change_password;
    if (loc === "chua_dang_nhap") return r.chua_dang_nhap;
    if (loc === "chua_phap_nhan") return !r.company_id;
    if (loc === "ngoai_bien_che") return r.ngoai_bien_che;
    return r.active;
  });

  return <>
    <h1>Tài khoản & phân quyền</h1>
    <p className="muted">Ma trận quyền nằm trong mã nguồn và có phép thử tự động canh; màn hình này công bố lại,
      không sửa. Sửa được ở đây: vai trò, khóa/mở, pháp nhân chủ quản và ngoại lệ có thời hạn.</p>

    <div className="row" style={{ gap: 6, flexWrap: "wrap", margin: "10px 0" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }}
        onClick={() => setTab(k)}>{l}{k === "gaps" && gaps?.tong ? ` (${gaps.tong})` : ""}</button>)}
    </div>

    {tab === "accounts" && acc && <>
      <div className="row" style={{ gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <input placeholder="Tìm tên, tài khoản, mã NV…" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 220 }} />
        <select value={loc} onChange={(e) => setLoc(e.target.value)}>
          <option value="">Đang hoạt động</option>
          <option value="khoa">Đang khóa</option>
          <option value="mat_khau_tam">Còn mật khẩu tạm</option>
          <option value="chua_dang_nhap">Chưa đăng nhập bao giờ</option>
          <option value="chua_phap_nhan">Chưa gán pháp nhân</option>
          <option value="ngoai_bien_che">Ngoài biên chế</option>
        </select>
        <span className="muted">{rows.length} tài khoản</span>
        {canWrite && <button className="act" style={{ margin: 0 }} onClick={taoTaiKhoan}>+ Tạo tài khoản</button>}
      </div>
      <div className="scroll"><table><thead><tr>
        <th>Mã NV</th><th>Họ tên</th><th>Tài khoản</th><th>Vai trò</th><th>Phòng</th><th>Pháp nhân</th>
        <th>Trạng thái</th><th>Đăng nhập lần cuối</th><th>Mật khẩu</th><th>Hồ sơ</th><th></th></tr></thead>
        <tbody>{rows.map((r: any) => <tr key={r.id}>
          <td>{r.staff_code || "—"}</td>
          <td>{r.full_name}{r.ngoai_bien_che && <> <Tag cls="warn">ngoài biên chế</Tag></>}</td>
          <td>{r.username}</td>
          <td>{canWrite ? <select value={r.role} onChange={(e) => doiVaiTro(r, e.target.value)} style={{ minWidth: 150 }}>
            {Object.entries(acc.roles).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select> : r.role_name}</td>
          <td>{r.department || "—"}</td>
          <td>{canWrite ? <select value={r.company_id || ""} onChange={(e) => send(`/access/users/${r.id}/company`, { company_id: e.target.value ? Number(e.target.value) : null }, "PUT")}>
            <option value="">— chưa xác định —</option>
            {(acc.companies || []).map((c: any) => <option key={c.id} value={c.id}>{c.code}</option>)}
          </select> : (r.company || "—")}</td>
          <td>{r.active ? <Tag cls="ok">hoạt động</Tag> : <Tag cls="warn">đã khóa</Tag>}</td>
          <td>{r.last_login ? fmtDT(r.last_login) : <Tag cls="warn">chưa bao giờ</Tag>}</td>
          <td>{r.must_change_password ? <Tag cls="warn">tạm – phải đổi</Tag> : "đã đổi"}</td>
          <td>{r.ho_so || <Tag cls="warn">không có</Tag>}</td>
          <td>{canWrite && <button className="act" style={{ margin: 0 }}
            onClick={() => send(`/users/${r.id}`, { active: !r.active }, "PUT")}>{r.active ? "Khóa" : "Mở lại"}</button>}</td>
        </tr>)}</tbody></table></div>

      {grants?.rows?.length > 0 && <>
        <h3 style={{ marginTop: 18 }}>Ngoại lệ quyền có thời hạn</h3>
        <p className="muted">Quyền cấp cho MỘT người, không cho cả vai trò. Hết hạn là tự mất hiệu lực, không chờ ai nhớ thu.</p>
        <div className="scroll"><table><thead><tr>
          <th>Người</th><th>Quyền</th><th>Từ</th><th>Đến</th><th>Lý do</th><th>Người duyệt</th><th>Hiệu lực</th><th></th></tr></thead>
          <tbody>{grants.rows.map((g: any) => <tr key={g.id}>
            <td>{g.ho_ten || g.username}</td><td>{g.ten_quyen}</td><td>{g.from_date}</td>
            <td>{g.vo_han ? <Tag cls="warn">không thời hạn</Tag> : g.to_date}</td>
            <td>{g.reason}</td><td>{g.approved_by || "—"}</td>
            <td>{g.hieu_luc ? <Tag cls="ok">còn hiệu lực</Tag> : <Tag cls="warn">hết / đã thu</Tag>}</td>
            <td>{laLanhDao && g.hieu_luc && <button className="act" style={{ margin: 0 }}
              onClick={() => send(`/access/grants/${g.id}`, undefined, "DELETE").then(() => api("/access/grants").then(setGrants))}>Thu hồi</button>}</td>
          </tr>)}</tbody></table></div>
      </>}
    </>}

    {tab === "matrix" && mt && <>
      <div className="row" style={{ gap: 8, marginBottom: 8 }}>
        <button className="act" style={{ margin: 0 }} onClick={taiExcel}>Xuất Excel để TGĐ ký rà quyền</button>
        <span className="muted">{mt.tong} màn hình × {mt.rows.length} vai trò</span>
      </div>
      {mt.ghi_chu.map((g: string, i: number) => <p key={i} className="muted" style={{ margin: "2px 0" }}>• {g}</p>)}
      <div className="scroll" style={{ marginTop: 10 }}><table><thead><tr>
        <th style={{ minWidth: 150 }}>Vai trò</th><th>Số MH</th><th>Tab nhân sự</th>
        {mt.man_hinh.map((p: string) => <th key={p} style={{ fontSize: 11, whiteSpace: "nowrap" }}>{p}</th>)}
      </tr></thead><tbody>{mt.rows.map((r: any) => <tr key={r.vai_tro}>
        <td><b>{r.ten}</b>{r.toan_quyen && <> <Tag cls="ok">toàn quyền</Tag></>}{r.chi_doc && <> <Tag cls="navy">chỉ đọc</Tag></>}
          {r.danh_sach_cho_phep && <> <Tag cls="warn">danh sách cho phép</Tag></>}</td>
        <td style={{ textAlign: "center" }}>{r.so_mo}/{mt.tong}</td>
        <td style={{ fontSize: 11 }}>{r.tab_nhan_su.map((t: string) => mt.hr_tabs[t]).join(", ") || "—"}</td>
        {mt.man_hinh.map((p: string) => <td key={p} style={{ textAlign: "center" }}>{r.man_hinh[p] ? "✓" : ""}</td>)}
      </tr>)}</tbody></table></div>
    </>}

    {tab === "gaps" && gaps && <>
      {gaps.tong === 0 && <p>Không có chênh lệch nào.</p>}
      {Object.entries(gaps.danh_sach).map(([k, v]: any) => v.length > 0 && <div key={k} style={{ marginBottom: 16 }}>
        <h3>{GAP_TEN[k] || k} <Tag cls="warn">{v.length}</Tag></h3>
        <div className="scroll"><table><tbody>{v.map((x: any, i: number) => <tr key={i}>
          <td>{x.code || x.staff_code || x.ma?.join(", ") || "—"}</td>
          <td>{x.full_name}</td>
          <td>{x.role_name || x.department || ""}</td>
          <td className="muted">{x.ly_do || (x.so_luong ? `${x.so_luong} hồ sơ trùng` : "")}</td>
          <td>{canWrite && x.id && k === "chua_gan_phap_nhan" &&
            <span className="muted">gán ở thẻ Tài khoản</span>}</td>
        </tr>)}</tbody></table></div>
      </div>)}
    </>}

    {tab === "audit" && log && <>
      <p className="muted">Thao tác về quyền. Dòng đăng nhập được lọc bỏ để việc cấp và thu quyền không bị trôi mất.</p>
      <div className="scroll"><table><thead><tr>
        <th>Thời điểm</th><th>Người thực hiện</th><th>Việc</th><th>Đối tượng</th><th>Trước → sau</th></tr></thead>
        <tbody>{log.rows.map((r: any) => <tr key={r.id}>
          <td>{fmtDT(r.ts)}</td>
          <td>{r.actor} <span className="muted">({r.role_name})</span></td>
          <td>{ACT_TEN[r.action] || r.action}</td>
          <td>{r.entity}</td>
          <td style={{ fontSize: 11 }} className="muted">
            {r.before ? JSON.stringify(r.before) : "—"} → {r.after ? JSON.stringify(r.after) : "—"}</td>
        </tr>)}</tbody></table></div>
    </>}
  </>;
}

// Bọc trong Shell: không bọc thì trang chạy NGOÀI khung – mất thanh điều hướng, và tệ hơn là
// useShell() trả user rỗng nên mọi nút theo vai trò lặng lẽ biến mất mà không báo lỗi gì.
export default function Page() { return <Shell><AccessPage /></Shell>; }
