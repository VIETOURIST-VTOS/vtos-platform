"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Hồ sơ đội xe Vietrip – Đợt 1.
 *
 *  Nguyên tắc hiển thị của màn hình này: KHÔNG có màu xanh khi hệ thống chưa kiểm tra được. Một chiếc xe chưa
 *  nhập đăng kiểm phải hiện "Chưa đủ dữ liệu" chứ không phải một dấu tích – nếu không, người điều hành tin
 *  rằng hồ sơ đã được kiểm tra và cho xe xuất bến. */
const MUC_CLS: Record<string, string> = { OK: "ok", UNKNOWN: "warn", REVIEW: "warn", APPROVAL_REQUIRED: "warn", BLOCK: "red" };
const MUC_TEN: Record<string, string> = { OK: "Đạt", UNKNOWN: "Chưa đủ dữ liệu", REVIEW: "Cần xem lại", APPROVAL_REQUIRED: "Cần duyệt ngoại lệ", BLOCK: "Chặn" };

function DoiXe() {
  const { user, toast } = useShell();
  const [tq, setTq] = useState<any>(null);
  const [xe, setXe] = useState<any[]>([]);
  const [chon, setChon] = useState<any>(null);
  const [xm, setXm] = useState<any[]>([]);
  const canWrite = ["cntt", "hcns", "tp_dh", "nv_dh"].includes(user?.role || "");

  const load = useCallback(async () => {
    try {
      setTq(await api("/fleet/tong-quan"));
      setXe(await api("/fleet/xe?kem_kiem_tra=true"));
      setXm(await api("/fleet/xac-minh"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const mo = async (id: number) => { try { setChon(await api(`/fleet/xe/${id}`)); } catch (e) { toast(errMsg(e), true); } };

  const dongViec = async (id: number) => {
    const kl = prompt("Kết luận xác minh (bắt buộc – để lần sau còn biết việc đã xử lý thế nào):");
    if (!kl) return;
    try { await api(`/fleet/xac-minh/${id}/ket-luan`, { method: "POST", json: { status: "xong", resolution: kl } }); toast("Đã đóng việc xác minh"); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  if (!tq) return <p className="muted">Đang tải…</p>;
  return (<>
    <h1>Đội xe Vietrip – hồ sơ và điều kiện khai thác</h1>
    <p className="muted">Mã xe theo chiếc xe suốt vòng đời, không theo biển số: đổi biển hay chuyển sở hữu đều giữ nguyên lịch sử chuyến và chi phí của chính chiếc xe đó.</p>

    <div className="kpis">
      <div className="kpi"><b>{tq.tong_so_xe}</b><span>xe trong danh mục</span></div>
      <div className="kpi"><b style={{ color: "var(--ok, green)" }}>{tq.san_sang}</b><span>sẵn sàng (đủ hồ sơ, qua kiểm tra)</span></div>
      <div className="kpi"><b style={{ color: "var(--orange)" }}>{tq.chua_du_du_lieu}</b><span>chưa đủ dữ liệu để kết luận</span></div>
      <div className="kpi"><b style={{ color: tq.bi_chan ? "var(--red)" : undefined }}>{tq.bi_chan}</b><span>đang bị chặn khai thác</span></div>
      <div className="kpi"><b>{tq.viec_xac_minh_dang_mo}</b><span>việc xác minh hồ sơ còn treo</span></div>
    </div>
    <p className="muted">{tq.ghi_chu}{tq.chan_khi_thieu_giay ? " Đang BẬT chế độ chặn khi thiếu giấy tờ." : " Chế độ chặn khi thiếu giấy tờ đang TẮT – thiếu hồ sơ chỉ cảnh báo, chưa dừng lệnh điều xe."}</p>

    <div className="panel wrap"><h2>Danh sách xe ({xe.length})</h2>
      <table><thead><tr><th>Mã xe</th><th>Biển đang dùng</th><th>Quyền khai thác</th><th>Vòng đời</th><th>Pháp nhân sở hữu</th><th>Đối tác</th><th>Hợp đồng</th><th>Tài xế</th><th>Điều kiện hôm nay</th></tr></thead>
        <tbody>{xe.map((v) => <tr key={v.id} onClick={() => mo(v.id)} style={{ cursor: "pointer" }}>
          <td><b>{v.code || "—"}</b></td><td>{v.plate}</td><td>{v.op_right_ten}</td><td>{v.lifecycle_ten}</td>
          <td>{v.owner_company || <span className="muted">chưa xác định</span>}</td>
          <td>{v.partner_name || ""}</td><td>{v.contract_ref || ""}</td><td>{v.driver || <span className="muted">chưa gán</span>}</td>
          <td><Tag cls={MUC_CLS[v.san_sang?.muc] || ""}>{MUC_TEN[v.san_sang?.muc] || v.san_sang?.muc}</Tag>
            {v.san_sang?.ly_do?.length > 0 && <div className="muted">{v.san_sang.ly_do[0]}</div>}</td>
        </tr>)}</tbody></table>
    </div>

    {chon && <div className="panel"><h2>Hồ sơ xe {chon.code} · {chon.plate}</h2>
      <p className="muted">Số khung {chon.vin || "chưa nhập"} · {chon.seats} chỗ · đồng hồ {chon.odo_km ? `${chon.odo_km.toLocaleString("vi-VN")} km` : "chưa nhập"}{chon.odo_at ? ` (ghi ngày ${fmtD(chon.odo_at)})` : ""}</p>
      <div className="grid">
        <div><h3>Lịch sử biển số</h3>
          <table><tbody>{chon.lich_su_bien.map((p: any, i: number) => <tr key={i}>
            <td>{p.plate} {p.to_date === null && <Tag cls="ok">đang dùng</Tag>}</td>
            <td className="muted">{p.from_date ? fmtD(p.from_date) : "?"} → {p.to_date ? fmtD(p.to_date) : "nay"}</td>
            <td className="muted">{p.source}</td></tr>)}</tbody></table>
        </div>
        <div><h3>Giấy tờ có hạn</h3>
          {chon.giay_to.length ? <table><tbody>{chon.giay_to.map((g: any) => <tr key={g.id}>
            <td>{g.kind_ten} <span className="muted">({g.cho_ai === "xe" ? "của xe" : "của tài xế"})</span></td>
            <td>{g.number || <span className="muted">chưa có số</span>}</td>
            <td>{g.expires_on ? <>hết hạn {fmtD(g.expires_on)}</> : <Tag cls="warn">chưa có ngày hết hạn</Tag>}</td>
            <td>{g.verify === "da_xac_minh" ? <Tag cls="ok">đã đối chiếu gốc</Tag> : <Tag cls="warn">theo nguồn</Tag>}</td>
          </tr>)}</tbody></table> : <p className="muted">Chưa có giấy tờ nào trong hồ sơ – hệ thống KHÔNG kết luận xe còn hạn.</p>}
        </div>
      </div>
      {chon.san_sang?.ly_do?.length > 0 && <p><Tag cls={MUC_CLS[chon.san_sang.muc]}>{MUC_TEN[chon.san_sang.muc]}</Tag> {chon.san_sang.ly_do.join(" · ")}</p>}
      <button className="act grey" onClick={() => setChon(null)}>Đóng</button>
    </div>}

    <div className="panel wrap"><h2>Hàng đợi xác minh hồ sơ ({xm.filter((x) => x.status !== "xong" && x.status !== "khong_ap_dung").length} còn treo)</h2>
      <p className="muted">Những việc hệ thống không tự quyết được và cần người trả lời. Hệ thống nói ra chỗ nó không chắc, thay vì tự điền cho đủ form.</p>
      <table><thead><tr><th>Đối tượng</th><th>Việc cần xác minh</th><th>Nguồn</th><th>Trạng thái</th><th>Kết luận</th>{canWrite && <th></th>}</tr></thead>
        <tbody>{xm.map((x) => <tr key={x.id} style={{ opacity: x.status === "xong" ? 0.55 : 1 }}>
          <td>{x.ref}</td><td>{x.issue}</td><td className="muted">{x.source}</td>
          <td>{x.status === "xong" ? <Tag cls="ok">{x.status_ten}</Tag> : <Tag cls="warn">{x.status_ten}</Tag>}</td>
          <td className="muted">{x.resolution}{x.resolved_by ? ` — ${x.resolved_by}, ${fmtDT(x.resolved_at)}` : ""}</td>
          {canWrite && <td>{x.status !== "xong" && x.status !== "khong_ap_dung" && <button className="act teal" onClick={() => dongViec(x.id)}>Kết luận</button>}</td>}
        </tr>)}</tbody></table>
    </div>
  </>);
}

export default function Page() { return <Shell><DoiXe /></Shell>; }
