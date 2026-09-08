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
  ["gaps", "Chênh lệch cần xử lý"], ["tracuu", "Tra cứu quyền"], ["audit", "Nhật ký quyền"],
];
/* Vì sao có tab này (P10, 08/9/2026): quyền trong VTOS đến từ bốn nguồn không nguồn nào nhìn thấy ba
   nguồn kia. Muốn biết một nhân viên vào được những đâu thì hôm nay phải đọc mã – mà đọc mã thì trong
   kỳ rà quyền hằng tháng sẽ không ai đọc, và không rà thì quyền chỉ nở ra chứ không co lại.
   Mỗi dòng dưới đây vì thế bắt buộc kèm cột "Vì sao": danh sách quyền không có lý do thì người rà chỉ
   gật hoặc lắc được, không sửa được. */
const NGUON_TEN: Record<string, string> = {
  ma_tran_menu: "Ma trận quyền", danh_sach_hep_khai_tay: "Danh sách hẹp khai tay",
  ngoai_le_theo_nguoi: "Ngoại lệ theo người", moi_nguoi: "Ai cũng có",
  khong_duoc_an: "Không được ẩn", api_chung: "API chung", theo_man_hinh: "Theo màn hình",
  khai_tay_con_lai: "Khai tay còn lại", vai_tro_nen: "Vai trò nền", khong_ro: "KHÔNG RÕ",
};
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
  const [tcUid, setTcUid] = useState<number | null>(null);
  const [tc, setTc] = useState<any>(null);
  const [tcVai, setTcVai] = useState("");
  const [suy, setSuy] = useState<any>(null);
  const [dangSuy, setDangSuy] = useState(false);
  const [mkRobot, setMkRobot] = useState<any>(null);   // mật khẩu robot – chỉ hiện MỘT lần
  const [tcRole, setTcRole] = useState<any>(null);

  const loadAcc = useCallback(() => { api("/access/accounts").then(setAcc).catch((e) => toast(errMsg(e), true)); }, [toast]);
  const loadGaps = useCallback(() => { api("/access/gaps").then(setGaps).catch(() => {}); }, []);
  useEffect(() => { loadAcc(); loadGaps(); api("/access/grants").then(setGrants).catch(() => {}); }, [loadAcc, loadGaps]);
  useEffect(() => {
    if (tab === "matrix" && !mt) api("/access/matrix").then(setMt).catch((e) => toast(errMsg(e), true));
    if (tab === "audit") api("/access/audit").then(setLog).catch(() => {});
    if (tab === "gaps" && !suy) api("/access/phap-nhan/suy-tu-ho-so").then(setSuy).catch(() => {});
  }, [tab, mt, suy, toast]);
  useEffect(() => {
    if (tcUid == null) { setTc(null); return; }
    setTc(null); api(`/access/tra-cuu/${tcUid}`).then(setTc).catch((e) => toast(errMsg(e), true));
  }, [tcUid, toast]);
  useEffect(() => {
    if (!tcVai) { setTcRole(null); return; }
    setTcRole(null); api(`/access/tra-cuu-vai-tro/${tcVai}`).then(setTcRole).catch((e) => toast(errMsg(e), true));
  }, [tcVai, toast]);

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
          <td style={{ whiteSpace: "nowrap" }}>
            <button className="act grey" style={{ margin: 0, marginRight: 4 }}
              onClick={() => { setTcUid(r.id); setTab("tracuu"); }}>Xem quyền</button>
            {canWrite && <button className="act" style={{ margin: 0 }}
              onClick={() => send(`/users/${r.id}`, { active: !r.active }, "PUT")}>{r.active ? "Khóa" : "Mở lại"}</button>}
          </td>
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
      {/* Gán pháp nhân hàng loạt: người quản trị đã quyết ở hồ sơ nhân sự rồi, việc còn lại chỉ là chép
          sang tài khoản. Bắt ngồi gán tay hơn trăm lần là cách chắc chắn để việc này không bao giờ xong,
          và một hàng rào chưa bật thì bằng không có hàng rào.
          XEM TRƯỚC rồi mới ghi: ghi hàng trăm dòng mà không ai nhìn trước là lúc sai không ai biết sai
          ở đâu. Bảng dưới nói rõ cả phần KHÔNG suy được và lý do, chứ không chỉ khoe phần làm được. */}
      {suy && (suy.dem.suy_duoc > 0 || suy.dem.khong_suy_duoc > 0 || suy.dem.lech_voi_ho_so > 0) && <div style={{ marginBottom: 18 }}>
        <h3>Gán pháp nhân cho tài khoản, suy từ hồ sơ nhân sự</h3>
        <p className="muted">Pháp nhân của tài khoản quyết định người đó nhìn thấy dữ liệu của công ty nào.
          Suy theo <b>phòng ban của hồ sơ nhân sự đang làm việc</b>, và không ghi đè giá trị đã gán tay.</p>
        {suy.quy_tac && <p><Tag cls="ok">Quy tắc</Tag> {suy.quy_tac.cau}</p>}
        <div className="row" style={{ gap: 8, flexWrap: "wrap", alignItems: "center", margin: "8px 0" }}>
          <Tag cls="ok">{suy.dem.suy_duoc} suy được</Tag>
          <Tag cls="warn">{suy.dem.khong_suy_duoc} phải gán tay</Tag>
          {suy.dem.lech_voi_ho_so > 0 && <Tag cls="warn">{suy.dem.lech_voi_ho_so} lệch với hồ sơ</Tag>}
          <span className="muted">{suy.dem.da_co} tài khoản đã có</span>
          {canWrite && suy.dem.suy_duoc > 0 && <button className="act" style={{ margin: 0 }} disabled={dangSuy}
            onClick={async () => {
              if (!confirm(`Gán pháp nhân cho ${suy.dem.suy_duoc} tài khoản theo bảng dưới?`)) return;
              setDangSuy(true);
              try {
                const r = await api<any>("/access/phap-nhan/suy-tu-ho-so", { method: "POST", json: {} });
                toast(r.message); setSuy(null); loadAcc(); loadGaps();
              } catch (e) { toast(errMsg(e), true); } finally { setDangSuy(false); }
            }}>{dangSuy ? "Đang ghi…" : `Gán cho ${suy.dem.suy_duoc} tài khoản`}</button>}
        </div>

        {suy.suy_duoc.length > 0 && <div className="scroll"><table><thead><tr>
          <th>Mã NV</th><th>Họ tên</th><th>Vai trò</th><th>Phòng</th><th>Sẽ gán</th><th>Ghi chú</th>
        </tr></thead><tbody>{suy.suy_duoc.map((x: any) => <tr key={x.user_id}>
          <td>{x.staff_code || "—"}</td><td>{x.full_name}</td><td>{x.role_name}</td>
          <td>{x.phong || "—"}</td><td><b>{x.company}</b></td>
          <td className="muted">{x.ly_do_quy_tac
            ? <><Tag cls="warn">hồ sơ ghi {x.ho_so_company}</Tag> {x.ly_do_quy_tac}</>
            : (x.noi_bang === "user_id" ? "hồ sơ đã nối" : "nối bằng mã nhân viên")}</td>
        </tr>)}</tbody></table></div>}
        {suy.suy_duoc.some((x: any) => x.ly_do_quy_tac) && <p className="muted">
          Dòng có dấu <b>hồ sơ ghi …</b> là chỗ hồ sơ nhân sự ghi khác quy tắc. Quy tắc thắng ở bảng này,
          nhưng nên báo HCNS sửa lại hồ sơ — vì hồ sơ mới là nơi con số ấy được dùng để chia bút toán lương.
        </p>}

        {suy.lech_voi_ho_so.length > 0 && <>
          <h4 style={{ marginTop: 14 }}>Tài khoản và hồ sơ đang nói khác nhau ({suy.lech_voi_ho_so.length})</h4>
          <p className="muted">Không tự sửa: gán tay là quyết định của con người, suy tự động chỉ là phỏng
            theo dữ liệu. Người quản trị xem rồi quyết bên nào đúng.</p>
          <div className="scroll"><table><thead><tr>
            <th>Họ tên</th><th>Tài khoản đang là</th><th>Hồ sơ nói là</th>
          </tr></thead><tbody>{suy.lech_voi_ho_so.map((x: any) => <tr key={x.user_id}>
            <td>{x.full_name}</td><td>{x.company}</td><td>{x.ho_so_company}</td>
          </tr>)}</tbody></table></div>
        </>}

        {suy.khong_suy_duoc.length > 0 && <>
          <h4 style={{ marginTop: 14 }}>Không suy được, phải gán tay ({suy.khong_suy_duoc.length})</h4>
          <div className="scroll"><table><thead><tr>
            <th>Mã NV</th><th>Họ tên</th><th>Vai trò</th><th>Vì sao không suy được</th>
          </tr></thead><tbody>{suy.khong_suy_duoc.map((x: any) => <tr key={x.user_id}>
            <td>{x.staff_code || "—"}</td><td>{x.full_name}</td><td>{x.role_name}</td>
            <td className="muted">{x.ly_do}</td>
          </tr>)}</tbody></table></div>
        </>}
      </div>}

      {/* Tài khoản cho ba vai trò máy. Chưa có tài khoản riêng thì robot vẫn chạy dưới tên một con
          người, và nhật ký không phân biệt được ai làm gì – đúng vấn đề mà vai trò máy sinh ra để giải.
          Mật khẩu ngẫu nhiên và hiện ĐÚNG MỘT LẦN: không lưu ở dạng đọc được, mất thì đặt lại. */}
      {acc && <div style={{ marginBottom: 18 }}>
        <h3>Tài khoản cho robot</h3>
        <p className="muted">Mỗi vai trò máy MỘT tài khoản. Hai tài khoản cùng một vai trò thì không truy
          được lần chạy nào của bên nào. Mật khẩu sinh ngẫu nhiên và chỉ hiện một lần ngay sau khi tạo.</p>
        <div className="scroll"><table><thead><tr>
          <th>Vai trò máy</th><th>Tài khoản</th><th></th></tr></thead><tbody>
          {Object.entries(acc.roles || {}).filter(([k]: any) => k.startsWith("robot_")).map(([k, v]: any) => {
            const co = (acc.rows || []).find((r: any) => r.role === k && r.active);
            return <tr key={k}>
              <td>{v}</td>
              <td>{co ? co.username : <Tag cls="warn">chưa có</Tag>}</td>
              <td>{!co && canWrite && <button className="act" style={{ margin: 0 }} onClick={async () => {
                if (!confirm(`Tạo tài khoản đăng nhập cho ${v}? Mật khẩu chỉ hiện một lần.`)) return;
                try {
                  const r = await api<any>("/access/accounts/robot", { method: "POST", json: { role: k } });
                  setMkRobot(r); loadAcc(); loadGaps();
                } catch (e) { toast(errMsg(e), true); }
              }}>Tạo tài khoản</button>}</td>
            </tr>;
          })}
        </tbody></table></div>
        {mkRobot && <div className="panel" style={{ marginTop: 10 }}>
          <p><Tag cls="ok">Đã tạo</Tag> {mkRobot.message}</p>
          <p>Tài khoản: <b>{mkRobot.username}</b></p>
          <p>Mật khẩu: <code style={{ fontSize: 16, userSelect: "all" }}>{mkRobot.mat_khau}</code></p>
          <p className="muted">{mkRobot.luu_y}</p>
          <button className="act grey" style={{ margin: 0 }} onClick={() => setMkRobot(null)}>
            Đã chép xong, ẩn đi</button>
        </div>}
      </div>}

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

    {tab === "tracuu" && <>
      <p className="muted">Chọn một người: hiện đủ ba lớp quyền – màn hình họ thấy, nhóm dữ liệu họ chạm được,
        và năng lực cấp riêng. Cột <b>Vì sao</b> chỉ thẳng vào dòng cho phép, để người rà sửa được chứ không
        chỉ gật hoặc lắc. Màn hình này chỉ ĐỌC, không cấp và không thu quyền của ai.</p>

      <div className="row" style={{ gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
        <select value={tcUid ?? ""} onChange={(e) => { setTcUid(e.target.value ? Number(e.target.value) : null); setTcVai(""); }}
          style={{ minWidth: 280 }}>
          <option value="">— chọn một người —</option>
          {(acc?.rows || []).filter((r: any) => r.active).map((r: any) =>
            <option key={r.id} value={r.id}>{r.full_name} · {r.role_name}{r.staff_code ? ` · ${r.staff_code}` : ""}</option>)}
        </select>
        <span className="muted">hoặc theo vai trò:</span>
        <select value={tcVai} onChange={(e) => { setTcVai(e.target.value); setTcUid(null); }} style={{ minWidth: 200 }}>
          <option value="">— chọn một vai trò —</option>
          {Object.entries(acc?.roles || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {tc && <>
        <div className="row" style={{ gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
          <h3 style={{ margin: 0 }}>{tc.tai_khoan.full_name}</h3>
          <Tag cls="ok">{tc.tai_khoan.role_name}</Tag>
          {!tc.tai_khoan.active && <Tag cls="warn">đã khóa</Tag>}
          {tc.tai_khoan.ngoai_bien_che && <Tag cls="warn">ngoài biên chế</Tag>}
          <span className="muted">{tc.tai_khoan.department || "—"} · {tc.tai_khoan.username}</span>
        </div>
        <p className="muted" style={{ marginTop: 4 }}>{tc.pham_vi_phap_nhan?.cau_hien_thi}</p>
        {tc.canh_bao?.map((c: string, i: number) => <p key={i}><Tag cls="warn">Lưu ý</Tag> {c}</p>)}

        <h4 style={{ marginTop: 16 }}>Màn hình thấy được ({tc.dem.man_hinh})</h4>
        <div className="scroll"><table><thead><tr>
          <th>Màn hình</th><th>Nguồn</th><th>Vì sao</th><th>Dòng cho phép</th></tr></thead>
          <tbody>{tc.man_hinh.map((x: any) => <tr key={x.path}>
            <td>{x.path}</td>
            <td>{x.nguon === "khong_ro" ? <Tag cls="warn">{NGUON_TEN[x.nguon]}</Tag> : NGUON_TEN[x.nguon] || x.nguon}</td>
            <td>{x.cau}</td>
            <td className="muted" style={{ fontFamily: "monospace", fontSize: 12 }}>{x.dong || "—"}</td>
          </tr>)}</tbody></table></div>

        <h4 style={{ marginTop: 16 }}>Nhóm dữ liệu chạm được ({tc.dem.api})</h4>
        <div className="scroll"><table><thead><tr>
          <th>Nhóm</th><th>Nguồn</th><th>Vì sao</th></tr></thead>
          <tbody>{tc.api.map((x: any) => <tr key={x.nhom}>
            <td style={{ fontFamily: "monospace", fontSize: 12 }}>{x.nhom}</td>
            <td>{["khong_ro", "khai_tay_con_lai"].includes(x.nguon)
              ? <Tag cls="warn">{NGUON_TEN[x.nguon]}</Tag> : NGUON_TEN[x.nguon] || x.nguon}</td>
            <td>{x.cau}</td>
          </tr>)}</tbody></table></div>

        <h4 style={{ marginTop: 16 }}>Năng lực cấp riêng ({tc.dem.nang_luc})</h4>
        {tc.nang_luc.length === 0 ? <p className="muted">Không có năng lực nào cấp lẻ cho người này.</p> :
          <div className="scroll"><table><thead><tr>
            <th>Năng lực</th><th>Nguồn</th><th>Vì sao</th></tr></thead>
            <tbody>{tc.nang_luc.map((x: any) => <tr key={x.ma}>
              <td>{x.ten}</td><td>{NGUON_TEN[x.nguon] || x.nguon}</td><td>{x.cau}</td>
            </tr>)}</tbody></table></div>}

        {tc.man_hinh_bi_an?.length > 0 && <>
          <h4 style={{ marginTop: 16 }}>Màn hình KHÔNG thấy ({tc.man_hinh_bi_an.length})</h4>
          <p className="muted" style={{ fontFamily: "monospace", fontSize: 12 }}>{tc.man_hinh_bi_an.join(" · ")}</p>
        </>}
      </>}

      {tcRole && <>
        <div className="row" style={{ gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
          <h3 style={{ margin: 0 }}>{tcRole.vai_tro_ten}</h3>
          <Tag cls={tcRole.so_nguoi ? "ok" : "warn"}>{tcRole.so_nguoi} người</Tag>
        </div>
        <p className="muted">Siết hay nới vai trò này là siết hay nới đúng {tcRole.so_nguoi} người:{" "}
          {tcRole.nguoi.map((x: any) => x.full_name).join(" · ") || "chưa có ai"}</p>
        {tcRole.canh_bao?.map((c: string, i: number) => <p key={i}><Tag cls="warn">Lưu ý</Tag> {c}</p>)}
        <h4 style={{ marginTop: 12 }}>Màn hình ({tcRole.dem.man_hinh}) · Nhóm dữ liệu ({tcRole.dem.api})</h4>
        <div className="scroll"><table><thead><tr>
          <th>Màn hình</th><th>Vì sao</th></tr></thead>
          <tbody>{tcRole.man_hinh.map((x: any) => <tr key={x.path}>
            <td>{x.path}</td><td>{x.cau}</td></tr>)}</tbody></table></div>
      </>}
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
