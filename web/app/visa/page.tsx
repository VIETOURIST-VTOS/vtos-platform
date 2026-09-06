"use client";
/** Điều hành ▸ Visa – tổng quan, danh sách hồ sơ và chi tiết một hồ sơ.
 *
 * Giao diện CỐ Ý không có ô "đổi giai đoạn": mỗi bước chỉ đi tiếp bằng một nút hành động, và nút đó chỉ hiện
 * khi hồ sơ đang đứng đúng ở bước ấy. Điều kiện thật nằm ở backend – đây chỉ là lớp hiển thị cho dễ làm.
 *
 * Hai quy ước hiển thị bám theo đặc tả:
 *   - Dấu ✓ CHỈ dùng cho mục tài liệu đã được chấp nhận. "Khách nói không nộp" hiện là «đang đề nghị», không phải ✓.
 *   - Cột tài liệu ghi "đã chấp nhận / bắt buộc", không phải "đã nộp / bắt buộc".
 */
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

type Cat = { stages: Record<string, string>; lifecycle: Record<string, string>; results: Record<string, string>;
  doc_status: Record<string, string>; markets: any[] };

const dt = (s: any) => (s ? new Date(s).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" }) : "—");
const d = (s: any) => (s ? new Date(s).toLocaleDateString("vi-VN") : "—");
const DOC_TAG: Record<string, string> = { ACCEPTED: "ok", WAIVED: "ok", NOT_APPLICABLE: "grey", MISSING: "red",
  NEEDS_REPLACEMENT: "red", WAIVER_REQUESTED: "warn", UPLOADED: "warn", UNDER_REVIEW: "warn" };

function Visa() {
  const { user, toast } = useShell();
  const [cat, setCat] = useState<Cat | null>(null);
  const [tong, setTong] = useState<any>(null);
  const [ds, setDs] = useState<any>(null);
  const [ct, setCt] = useState<any>(null);          // chi tiết hồ sơ đang mở
  const [loc, setLoc] = useState({ q: "", market_code: "", stage: "", lifecycle_status: "" });
  const [busy, setBusy] = useState("");
  const canWrite = !user?.read_only;

  const qs = () => Object.entries(loc).filter(([, v]) => v).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");

  const reload = async (keepId?: number) => {
    try {
      setTong(await api("/visa/tong-quan"));
      setDs(await api(`/visa/ho-so?${qs()}`));
      if (keepId) setCt(await api(`/visa/ho-so/${keepId}`));
    } catch (x) { toast(errMsg(x), true); }
  };
  useEffect(() => { api("/visa/danh-muc").then(setCat).catch((x) => toast(errMsg(x), true)); reload(); }, []); // eslint-disable-line

  const open = async (id: number) => { try { setCt(await api(`/visa/ho-so/${id}`)); } catch (x) { toast(errMsg(x), true); } };

  /** Gọi một hành động nghiệp vụ rồi tải lại – lỗi 422 của backend hiện nguyên văn cho người dùng đọc. */
  const act = async (label: string, path: string, json?: any, method = "POST") => {
    setBusy(label);
    try {
      await api(path, { method, ...(json !== undefined ? { json } : {}) });
      toast("Xong: " + label);
      await reload(ct?.case?.id);
    } catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };

  const stage = ct?.case?.current_stage;
  const at = (s: string) => stage === s && ct?.case?.lifecycle_status === "ACTIVE";

  return (<>
    <p className="muted">Hồ sơ Visa theo <b>từng đương đơn</b>: mỗi người một form, một checklist, một lịch hẹn và một kết quả –
      kể cả khi cả nhà đi chung một booking. Khách hàng, booking, tour và chứng từ thu chi vẫn lấy từ các phân hệ sẵn có
      của VTOS, phân hệ này không giữ bản sao.</p>

    {tong && <div className="panel">
      <h3>Tổng quan</h3>
      <div className="grid">
        {([["Hồ sơ cá nhân", "ho_so_ca_nhan_dang_xu_ly"], ["Hồ sơ thuộc nhóm gia đình", "ho_so_thuoc_nhom_dang_xu_ly"],
           ["Số nhóm gia đình", "so_nhom_gia_dinh"], ["Chưa phân công", "chua_phan_cong"],
           ["Chờ khách bổ sung", "cho_khach_bo_sung"], ["Chờ kiểm tra nội bộ", "cho_kiem_tra_noi_bo"],
           ["Lịch hẹn sắp tới", "lich_hen_sap_toi"], ["Lịch đã qua chưa xác nhận", "lich_da_qua_chua_xac_nhan"],
           ["Việc quá hạn", "viec_qua_han"], ["Có kết quả, chưa bàn giao", "da_co_ket_qua_chua_ban_giao"],
           ["Tạm dừng", "tam_dung"]] as [string, string][]).map(([ten, k]) =>
          <div key={k} className="panel"><div className="muted">{ten}</div><div style={{ fontSize: 24 }}><b>{tong[k]}</b></div></div>)}
      </div>
      <p className="muted">{tong.ghi_chu}</p>
    </div>}

    <div className="panel">
      <input placeholder="Tìm tên đương đơn / mã hồ sơ" value={loc.q} onChange={(e) => setLoc({ ...loc, q: e.target.value })} />{" "}
      <select value={loc.market_code} onChange={(e) => setLoc({ ...loc, market_code: e.target.value })}>
        <option value="">Mọi thị trường</option>
        {(cat?.markets || []).map((m) => <option key={m.code} value={m.code}>{m.name}</option>)}
      </select>{" "}
      <select value={loc.stage} onChange={(e) => setLoc({ ...loc, stage: e.target.value })}>
        <option value="">Mọi giai đoạn</option>
        {Object.entries(cat?.stages || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>{" "}
      <select value={loc.lifecycle_status} onChange={(e) => setLoc({ ...loc, lifecycle_status: e.target.value })}>
        <option value="">Mọi trạng thái</option>
        {Object.entries(cat?.lifecycle || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>{" "}
      <button className="act grey" disabled={!!busy} onClick={() => reload(ct?.case?.id)}>Lọc</button>
    </div>

    {ds && <div className="panel wrap">
      <h3>Hồ sơ Visa ({ds.total})</h3>
      <table><thead><tr><th>Mã</th><th>Đương đơn</th><th>Thị trường</th><th>Ngày đi</th><th>Chuyên viên</th>
        <th>Giai đoạn</th><th>Việc tiếp theo</th><th>Hạn</th><th>Tài liệu</th><th>Kết quả</th><th></th></tr></thead>
        <tbody>{ds.rows.map((r: any) => <tr key={r.id}>
          <td><b>{r.case_code}</b></td>
          <td>{r.applicant_name}{r.family_group_id ? <> <Tag cls="grey">nhóm</Tag></> : null}</td>
          <td>{r.market_code}</td><td>{d(r.departure_date)}</td><td>{r.visa_owner || <Tag cls="warn">chưa giao</Tag>}</td>
          <td>{r.stage_name}{r.lifecycle_status !== "ACTIVE" && <> <Tag cls="grey">{cat?.lifecycle[r.lifecycle_status]}</Tag></>}</td>
          <td className="muted">{r.next_task}</td>
          <td>{r.overdue ? <Tag cls="red">{dt(r.due_at)}</Tag> : dt(r.due_at)}</td>
          <td>{r.documents}</td>
          <td>{r.result_status === "GRANTED" ? <Tag cls="ok">Được cấp</Tag>
            : r.result_status === "REFUSED" ? <Tag cls="red">Từ chối</Tag> : <span className="muted">—</span>}</td>
          <td><button className="act grey" onClick={() => open(r.id)}>Mở</button></td></tr>)}</tbody></table>
      <p className="muted">Cột “Tài liệu” là <b>số mục đã được chấp nhận / số mục bắt buộc</b> – không phải số mục khách đã gửi lên.</p>
    </div>}

    {ct && <div className="panel wrap">
      <h3>{ct.case.case_code} – {ct.applicant.ten}{" "}
        <Tag cls={ct.case.lifecycle_status === "ACTIVE" ? "ok" : "grey"}>{cat?.lifecycle[ct.case.lifecycle_status]}</Tag>{" "}
        <button className="act grey" onClick={() => setCt(null)}>Đóng</button></h3>

      <p>Giai đoạn: <b>{ct.case.stage_name}</b> · Chuyên viên: {ct.case.visa_owner || "chưa giao"} · Sales: {ct.case.sales || "—"}
        {ct.quy_visa_nhan_su ? <> · <Tag cls="grey">đã nối quỹ visa Nhân sự #{ct.quy_visa_nhan_su}</Tag></> : null}</p>
      <p className="muted">Các bước của thị trường {ct.case.market_code}: {ct.quy_trinh.cac_buoc.map((s: string) =>
        s === ct.quy_trinh.hien_tai ? `【${cat?.stages[s]}】` : cat?.stages[s]).join(" → ")}</p>

      {canWrite && <div className="panel">
        <h4>Hành động của bước hiện tại</h4>
        {at("thu_thap_tai_lieu") && <button className="act" disabled={!!busy}
          onClick={() => act("gửi kiểm tra", `/visa/ho-so/${ct.case.id}/gui-kiem-tra`)}>Gửi kiểm tra</button>}
        {at("kiem_tra") && <button className="act" disabled={!!busy}
          onClick={() => act("xác nhận kiểm tra đạt", `/visa/ho-so/${ct.case.id}/kiem-tra-dat`)}>Kiểm tra đạt</button>}
        {at("khai_ho_so") && <button className="act" disabled={!!busy} onClick={() => {
          const ma = prompt("Mã tham chiếu hồ sơ do LSQ/ĐSQ cấp:"); if (!ma) return;
          act("ghi nhận đã khai hồ sơ", `/visa/ho-so/${ct.case.id}/khai-ho-so`, { reference_code: ma });
        }}>Đã khai hồ sơ chính thức</button>}
        {at("lich_hen") && <button className="act" disabled={!!busy} onClick={() => {
          const luc = prompt("Thời gian hẹn (YYYY-MM-DD HH:MM):"); if (!luc) return;
          act("ghi lịch hẹn", `/visa/ho-so/${ct.case.id}/lich-hen`,
              { starts_at: luc.replace(" ", "T"), location: prompt("Địa điểm:") || "" });
        }}>Ghi lịch hẹn</button>}
        {at("ban_giao") && <button className="act" disabled={!!busy} onClick={() => {
          if (!confirm("Xác nhận đã trả giấy tờ/kết quả cho khách?")) return;
          act("ghi bàn giao", `/visa/ho-so/${ct.case.id}/ban-giao`,
              { direction: "TRA_KHACH", item_type: "ho_chieu", to_party: ct.applicant.ten, confirmed: true });
        }}>Đã trả khách</button>}
        {at("dong_ho_so") || ct.case.result_status !== "NOT_AVAILABLE" ? <button className="act orange" disabled={!!busy}
          onClick={() => act("đóng hồ sơ", `/visa/ho-so/${ct.case.id}/dong-ho-so`)}>Đóng hồ sơ</button> : null}{" "}
        {ct.case.lifecycle_status === "ACTIVE" && <button className="act grey" disabled={!!busy} onClick={() => {
          const ly = prompt("Lý do tạm dừng:"); if (!ly) return;
          act("tạm dừng", `/visa/ho-so/${ct.case.id}/tam-dung`, { reason: ly });
        }}>Tạm dừng</button>}{" "}
        {ct.case.lifecycle_status === "ON_HOLD" && <button className="act" disabled={!!busy}
          onClick={() => act("tiếp tục", `/visa/ho-so/${ct.case.id}/tiep-tuc`)}>Bỏ tạm dừng</button>}
        <p className="muted">Không có ô đổi giai đoạn tùy ý: mỗi nút ở trên là một hành động nghiệp vụ, và backend
          vẫn kiểm điều kiện lần nữa trước khi cho qua.</p>
      </div>}

      <h4>Checklist & tài liệu</h4>
      <table><thead><tr><th>Mục</th><th>Bắt buộc</th><th>Trạng thái</th><th>Người kiểm</th><th>Ghi chú</th><th></th></tr></thead>
        <tbody>{ct.checklist.map((i: any) => <tr key={i.id}>
          <td>{i.ten}</td><td>{i.bat_buoc ? "Có" : "—"}</td>
          <td><Tag cls={DOC_TAG[i.trang_thai] || "grey"}>{i.trang_thai === "ACCEPTED" ? "✓ " : ""}{cat?.doc_status[i.trang_thai]}</Tag>
            {i.can_kiem_lai && <> <Tag cls="warn">phải kiểm lại</Tag></>}</td>
          <td>{i.nguoi_kiem}</td><td className="muted">{i.ghi_chu}</td>
          <td>{canWrite && <label className="act grey" style={{ cursor: "pointer" }}>Nộp tệp
            <input type="file" style={{ display: "none" }} onChange={async (e) => {
              const f = e.target.files?.[0]; if (!f) return;
              const fd = new FormData(); fd.append("file", f); fd.append("checklist_item_id", String(i.id));
              setBusy("nộp " + i.ten);
              try {
                await api(`/visa/ho-so/${ct.case.id}/tai-lieu`, { method: "POST", body: fd });
                toast("Đã nộp " + i.ten); await reload(ct.case.id);
              } catch (x) { toast(errMsg(x), true); }
              setBusy(""); e.target.value = "";
            }} /></label>}</td></tr>)}</tbody></table>

      <h4>Tài liệu đã nộp</h4>
      <table><thead><tr><th>Tệp</th><th>Bản</th><th>Người tải</th><th>Lúc</th><th>SHA256</th><th></th></tr></thead>
        <tbody>{ct.tai_lieu.map((t: any) => <tr key={t.id}>
          <td>{t.ten_tep}{t.da_thay_the && <> <Tag cls="grey">đã bị thay</Tag></>}</td>
          <td>v{t.version}</td><td>{t.nguoi_tai}</td><td>{dt(t.luc)}</td><td className="muted">{t.sha256}</td>
          <td>{!t.da_thay_the && canWrite && <>
            <button className="act" disabled={!!busy}
              onClick={() => act("chấp nhận tài liệu", `/visa/ho-so/${ct.case.id}/tai-lieu/${t.id}/kiem-tra`,
                                 { decision: "ACCEPTED" })}>Chấp nhận</button>{" "}
            <button className="act orange" disabled={!!busy} onClick={() => {
              const ly = prompt("Lý do yêu cầu nộp lại (khách sẽ đọc):"); if (!ly) return;
              act("yêu cầu nộp lại", `/visa/ho-so/${ct.case.id}/tai-lieu/${t.id}/kiem-tra`,
                  { decision: "NEEDS_REPLACEMENT", reason: ly });
            }}>Nộp lại</button></>}</td></tr>)}</tbody></table>

      {!!ct.ngoai_le.length && <><h4>Đề nghị miễn nộp</h4>
        <table><thead><tr><th>Lý do</th><th>Người đề nghị</th><th>Quyết định</th><th></th></tr></thead>
          <tbody>{ct.ngoai_le.map((w: any) => <tr key={w.id}>
            <td>{w.ly_do}</td><td>{w.nguoi_de_nghi}</td>
            <td>{w.quyet_dinh === "PENDING" ? <Tag cls="warn">chờ quyết định</Tag>
              : w.quyet_dinh === "APPROVED" ? <Tag cls="ok">đã duyệt – {w.nguoi_quyet}</Tag>
              : <Tag cls="red">từ chối – {w.nguoi_quyet}</Tag>}</td>
            <td>{w.quyet_dinh === "PENDING" && canWrite && <>
              <button className="act" disabled={!!busy} onClick={() => act("duyệt miễn nộp",
                `/visa/ho-so/${ct.case.id}/ngoai-le/${w.id}/quyet-dinh`, { approve: true, note: prompt("Ghi chú:") || "" })}>Duyệt</button>{" "}
              <button className="act orange" disabled={!!busy} onClick={() => {
                const ly = prompt("Lý do từ chối:"); if (!ly) return;
                act("từ chối miễn nộp", `/visa/ho-so/${ct.case.id}/ngoai-le/${w.id}/quyet-dinh`, { approve: false, note: ly });
              }}>Từ chối</button></>}</td></tr>)}</tbody></table></>}

      <h4>Lịch hẹn</h4>
      <table><thead><tr><th>Thời gian</th><th>Múi giờ</th><th>Địa điểm</th><th>Trạng thái</th><th>Ghi chú</th><th></th></tr></thead>
        <tbody>{ct.lich_hen.map((a: any) => <tr key={a.id}>
          <td>{dt(a.luc)}</td><td className="muted">{a.mui_gio}</td><td>{a.dia_diem}</td>
          <td><Tag cls={a.trang_thai === "ATTENDED" ? "ok" : a.trang_thai === "MISSED" ? "red" : "grey"}>{a.trang_thai}</Tag></td>
          <td className="muted">{a.thay_cho_id ? `thay lịch #${a.thay_cho_id}: ${a.ly_do_doi}` : ""}</td>
          <td>{a.trang_thai === "SCHEDULED" && canWrite && <>
            <button className="act" disabled={!!busy} onClick={() => act("ghi có mặt",
              `/visa/ho-so/${ct.case.id}/lich-hen/${a.id}/sinh-trac-hoc`, { attended: true })}>Đã đến / lấy vân tay</button>{" "}
            <button className="act grey" disabled={!!busy} onClick={() => {
              const luc = prompt("Lịch mới (YYYY-MM-DD HH:MM):"); if (!luc) return;
              const ly = prompt("Lý do đổi lịch (bắt buộc):"); if (!ly) return;
              act("đổi lịch", `/visa/ho-so/${ct.case.id}/lich-hen/${a.id}/doi-lich`,
                  { starts_at: luc.replace(" ", "T"), reason: ly });
            }}>Đổi lịch</button></>}</td></tr>)}</tbody></table>
      <p className="muted">Lịch cũ không bị xóa khi đổi lịch. Lịch quá giờ mà chưa cập nhật sẽ sinh việc <b>xác minh</b>,
        hệ thống không tự kết luận khách vắng mặt.</p>

      {at("theo_doi_ket_qua") && canWrite && <div className="panel">
        <h4>Ghi nhận kết quả</h4>
        <button className="act" disabled={!!busy} onClick={() => act("ghi kết quả được cấp",
          `/visa/ho-so/${ct.case.id}/ket-qua`, { outcome: "GRANTED", received_on: new Date().toISOString().slice(0, 10) })}>Được cấp</button>{" "}
        <button className="act orange" disabled={!!busy} onClick={() => {
          const ly = prompt("Lý do từ chối theo thông báo của LSQ/ĐSQ:"); if (!ly) return;
          act("ghi kết quả từ chối", `/visa/ho-so/${ct.case.id}/ket-qua`,
              { outcome: "REFUSED", received_on: new Date().toISOString().slice(0, 10), refusal_reason: ly });
        }}>Bị từ chối</button>
        <p className="muted">Kết quả này chỉ áp cho đương đơn <b>{ct.applicant.ten}</b>, không lây sang thành viên khác trong nhóm.</p>
      </div>}

      <h4>Công việc</h4>
      <table><thead><tr><th>Việc</th><th>Người nhận</th><th>Trạng thái</th><th>Hạn</th><th>Lý do chờ</th></tr></thead>
        <tbody>{ct.cong_viec.map((t: any) => <tr key={t.id}>
          <td>{t.tieu_de}</td><td>{t.nguoi_nhan || <Tag cls="warn">chưa giao</Tag>}</td>
          <td>{t.trang_thai}</td><td>{t.qua_han ? <Tag cls="red">{dt(t.han)}</Tag> : dt(t.han)}</td>
          <td className="muted">{t.ly_do_cho}</td></tr>)}</tbody></table>

      <h4>Phiên bản form khai</h4>
      <table><thead><tr><th>Bản</th><th>Trạng thái</th><th>Trường đã đổi</th><th>Người lập</th><th>Lúc</th></tr></thead>
        <tbody>{ct.form.map((f: any) => <tr key={f.id}>
          <td>v{f.version}</td>
          <td><Tag cls={f.state === "CONFIRMED" || f.state === "USED" ? "ok" : "grey"}>{f.state}</Tag></td>
          <td className="muted">{(f.truong_doi || []).join(", ")}{f.doi_thong_tin_quan_trong && <> <Tag cls="warn">phải xác nhận lại</Tag></>}</td>
          <td>{f.nguoi_lap}</td><td>{dt(f.luc)}</td></tr>)}</tbody></table>
    </div>}
  </>);
}
export default function Page() { return <Shell><Visa /></Shell>; }
