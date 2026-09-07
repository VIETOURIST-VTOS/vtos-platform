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
  const [tab, setTab] = useState<"xe" | "chuyen" | "giaodich" | "quyettoan" | "congno">("xe");
  const [chuyen, setChuyen] = useState<any[]>([]);
  const [gd, setGd] = useState<any>(null);
  const [chuXe, setChuXe] = useState<any[]>([]);
  const [qt, setQt] = useState<any[]>([]);
  const [dm3, setDm3] = useState<any>(null);
  const [cn, setCn] = useState<any>(null);
  const [soChuXe, setSoChuXe] = useState<any>(null);
  const canWrite = ["cntt", "hcns", "tp_dh", "nv_dh"].includes(user?.role || "");
  // Người được nhập và sửa số liệu đội xe: điều hành, kế toán, và lãnh đạo.
  // "gd_doi_xe" là chính người sẽ nhập số liệu đội xe hằng ngày – thiếu vai trò này thì nút nhập không hiện
  // ra với đúng người mà form được làm cho, dù máy chủ đã cho phép.
  const canNhap = ["cntt", "hcns", "tp_dh", "nv_dh", "ketoan", "chutich", "tgd", "gd_doi_xe"].includes(user?.role || "");
  const [form, setForm] = useState<any>(null);      // form nhật trình chuyến (thêm / sửa)
  const [formDX, setFormDX] = useState<any>(null);  // form đề xuất chi
  const [dangLuu, setDangLuu] = useState(false);

  const load = useCallback(async () => {
    try {
      setTq(await api("/fleet/tong-quan"));
      setXe(await api("/fleet/xe?kem_kiem_tra=true"));
      setXm(await api("/fleet/xac-minh"));
      setChuyen(await api("/fleet/chuyen"));
      setGd(await api("/fleet/giao-dich"));
      setChuXe(await api("/fleet/chu-xe"));
      setQt(await api("/fleet/quyet-toan"));
      setDm3(await api("/fleet/danh-muc-dot3"));
      setCn(await api("/fleet/cong-no"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const mo = async (id: number) => { try { setChon(await api(`/fleet/xe/${id}`)); } catch (e) { toast(errMsg(e), true); } };

  const luuChuyen = async () => {
    if (!form.vehicle_id) return toast("Chọn xe trước đã", true);
    if (!form.ngay_di || !form.ngay_ve) return toast("Nhập ngày đi và ngày về", true);
    setDangLuu(true);
    try {
      if (form.id) {
        await api(`/fleet/chuyen/${form.id}`, { method: "PUT", json: {
          ten_tour: form.ten_tour, ngay_di: form.ngay_di, ngay_ve: form.ngay_ve,
          km_dau: form.km_dau, km_cuoi: form.km_cuoi, doanh_thu: form.doanh_thu, note: form.note } });
        toast("Đã cập nhật phiếu chuyến");
      } else {
        const r = await api<any>("/fleet/chuyen", { method: "POST", json: {
          vehicle_id: form.vehicle_id, ten_tour: form.ten_tour, ngay_di: form.ngay_di, ngay_ve: form.ngay_ve,
          km_dau: form.km_dau, km_cuoi: form.km_cuoi, doanh_thu: form.doanh_thu, note: form.note } });
        // Bốn khoản chi phí ghi thành bốn dòng riêng: mỗi dòng phải trả lời được loại gì, ai chịu, chứng từ đâu.
        for (const k of ["dau", "cau_duong", "cong_tac_phi", "giu_xe"]) {
          const tien = Number(form[k] || 0);
          if (tien > 0) await api(`/fleet/chuyen/${r.id}/chi-phi`, { method: "POST", json: {
            kind: k, amount: tien, lit: k === "dau" ? Number(form.lit || 0) : 0, chung_tu: form.chung_tu || "" } });
        }
        toast("Đã ghi phiếu chi phí xe");
      }
      setForm(null); load();
    } catch (e) { toast(errMsg(e), true); } finally { setDangLuu(false); }
  };

  const moLai = async (id: number) => {
    const ly = prompt("Lý do mở lại phiếu đã xác nhận (bắt buộc – để sau này còn biết vì sao số đổi):");
    if (!ly) return;
    try { await api(`/fleet/chuyen/${id}/mo-lai`, { method: "POST", json: { ly_do: ly } });
          toast("Đã mở lại – sửa xong nhớ xác nhận lại"); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const luuDeXuat = async () => {
    setDangLuu(true);
    try {
      const r = await api<any>("/fleet/de-xuat-chi", { method: "POST", json: formDX });
      toast(r.message); setFormDX(null); load();
    } catch (e) { toast(errMsg(e), true); } finally { setDangLuu(false); }
  };

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

    <div style={{ display: "flex", gap: 8, margin: "10px 0" }}>
      {([["xe", "Hồ sơ xe"], ["chuyen", `Nhật trình chuyến (${chuyen.length})`], ["giaodich", `Đối soát nguồn ngoài (${gd?.rows?.length || 0})`], ["quyettoan", `Chủ xe & quyết toán (${chuXe.length})`], ["congno", "Công nợ đội xe"]] as const)
        .map(([k, ten]) => <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} onClick={() => setTab(k as any)}>{ten}</button>)}
    </div>

    {tab === "chuyen" && <>
      {form && <div className="panel">
        <h2>{form.id ? `Sửa phiếu chuyến #${form.id}` : "Phiếu chi phí xe – nhập mới"}</h2>
        <p className="muted">Đúng bộ trường của phiếu trên Vietrip. Ô để trống nghĩa là <b>chưa có số</b>, không phải bằng 0 –
          hệ thống không tự điền 0 và không tính ra quãng đường âm.</p>
        <div className="grid2">
          <label>Xe
            <select value={form.vehicle_id || ""} onChange={(e) => setForm({ ...form, vehicle_id: Number(e.target.value) })} disabled={!!form.id}>
              <option value="">— chọn xe —</option>
              {xe.map((v: any) => <option key={v.id} value={v.id}>{v.plate}{v.code ? ` · ${v.code}` : ""}</option>)}
            </select></label>
          <label>Tour / khách hàng
            <input value={form.ten_tour || ""} onChange={(e) => setForm({ ...form, ten_tour: e.target.value })} placeholder="Đà Lạt (lẻ)" /></label>
          <label>Ngày đi<input type="date" value={form.ngay_di || ""} onChange={(e) => setForm({ ...form, ngay_di: e.target.value })} /></label>
          <label>Ngày về<input type="date" value={form.ngay_ve || ""} onChange={(e) => setForm({ ...form, ngay_ve: e.target.value })} /></label>
          <label>Km đầu<input type="number" value={form.km_dau ?? ""} onChange={(e) => setForm({ ...form, km_dau: e.target.value === "" ? null : Number(e.target.value) })} /></label>
          <label>Km cuối<input type="number" value={form.km_cuoi ?? ""} onChange={(e) => setForm({ ...form, km_cuoi: e.target.value === "" ? null : Number(e.target.value) })} /></label>
          <label>Doanh thu (đ)<input type="number" value={form.doanh_thu ?? ""} onChange={(e) => setForm({ ...form, doanh_thu: e.target.value === "" ? null : Number(e.target.value) })} /></label>
          <label>Ghi chú<input value={form.note || ""} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
        </div>
        {!form.id && <>
          <h3>Chi phí chuyến</h3>
          <p className="muted">Bốn khoản này Vietourist tạm ứng theo quy tắc chốt 07/9/2026. Để trống khoản nào thì không ghi dòng đó.</p>
          <div className="grid2">
            <label>Tiền dầu (đ)<input type="number" value={form.dau ?? ""} onChange={(e) => setForm({ ...form, dau: Number(e.target.value) })} /></label>
            <label>Số lít<input type="number" step="0.001" value={form.lit ?? ""} onChange={(e) => setForm({ ...form, lit: Number(e.target.value) })} /></label>
            <label>Phí cầu đường (đ)<input type="number" value={form.cau_duong ?? ""} onChange={(e) => setForm({ ...form, cau_duong: Number(e.target.value) })} /></label>
            <label>Công tác phí tài xế (đ)<input type="number" value={form.cong_tac_phi ?? ""} onChange={(e) => setForm({ ...form, cong_tac_phi: Number(e.target.value) })} /></label>
            <label>Phí gửi xe (đ)<input type="number" value={form.giu_xe ?? ""} onChange={(e) => setForm({ ...form, giu_xe: Number(e.target.value) })} /></label>
            <label>Số chứng từ<input value={form.chung_tu || ""} onChange={(e) => setForm({ ...form, chung_tu: e.target.value })} /></label>
          </div>
        </>}
        <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
          <button className="act teal" disabled={dangLuu} onClick={luuChuyen}>{dangLuu ? "Đang lưu…" : "Lưu phiếu"}</button>
          <button className="act grey" onClick={() => setForm(null)}>Đóng</button>
        </div>
      </div>}

      {chuyen.some((t: any) => t.nguon === "bao_cao_vietrip") && <div className="panel" style={{ borderColor: "var(--orange)" }}>
        <b>Dữ liệu đối chiếu – CHƯA CHÍNH THỨC.</b>
        <p className="muted">{chuyen.filter((t: any) => t.nguon === "bao_cao_vietrip").length} phiếu trong danh sách dưới
          đây nạp từ báo cáo quyết toán xe của Vietrip để đối chiếu và chạy thử. Số liệu chính thức là phiếu do
          người phụ trách nhập và xác nhận trên VTOS. Đừng lấy các con số này để báo cáo hay quyết toán khi
          chưa được rà lại.</p>
      </div>}
      <div className="panel wrap"><h2>Nhật trình chuyến</h2>
      <p className="muted">Km để trống nghĩa là <b>chưa đo</b>, không phải bằng 0. Cột &quot;Vietourist tạm ứng&quot; và &quot;Chủ xe chịu&quot; tách theo quy tắc chốt 07/9/2026: Vietourist tạm ứng nhiên liệu, cầu đường, công tác phí, bãi xe.</p>
      {canNhap && !form && <button className="act teal" style={{ marginBottom: 10 }}
        onClick={() => setForm({ ngay_di: "", ngay_ve: "" })}>+ Nhập phiếu chi phí xe</button>}
      <table><thead><tr><th>Phiếu</th><th>Xe</th><th>Tour</th><th>Đi → về</th><th>Km chạy</th><th>Doanh thu</th><th>VTS tạm ứng</th><th>Chủ xe chịu</th><th>Cờ</th>{canNhap && <th></th>}</tr></thead>
        <tbody>{chuyen.length ? chuyen.map((t) => <tr key={t.id}>
          <td className="muted">{t.ma_phieu || `#${t.id}`}
            {t.nguon === "bao_cao_vietrip" && <div><Tag cls="warn">dữ liệu thử</Tag></div>}</td>
          <td>{t.xe}</td><td>{t.ten_tour || <span className="muted">—</span>}</td>
          <td>{fmtD(t.ngay_di)} → {fmtD(t.ngay_ve)} <span className="muted">({t.so_ngay} ngày)</span></td>
          <td className="num">{t.km_chay === null ? <span className="muted">chưa đo</span> : t.km_chay.toLocaleString("vi-VN")}</td>
          <td className="num">{t.doanh_thu ? t.doanh_thu.toLocaleString("vi-VN") : ""}</td>
          <td className="num">{t.tong_chi_vietourist.toLocaleString("vi-VN")}</td>
          <td className="num">{t.tong_chi_chu_xe.toLocaleString("vi-VN")}</td>
          <td><Tag cls={t.co === "xanh" ? "ok" : t.co === "do" ? "red" : "warn"}>{t.co === "xanh" ? "Xanh" : t.co === "do" ? "Đỏ" : "Vàng"}</Tag>
            {t.co_ly_do && <div className="muted">{t.co_ly_do}</div>}
            {t.note && <div className="muted">{t.note}</div>}</td>
          {canNhap && <td>{t.status === "da_xac_nhan"
            ? <button className="act grey" onClick={() => moLai(t.id)}>Mở lại để sửa</button>
            : <button className="act grey" onClick={() => setForm({
                id: t.id, vehicle_id: t.vehicle_id, ten_tour: t.ten_tour,
                ngay_di: (t.ngay_di || "").slice(0, 10), ngay_ve: (t.ngay_ve || "").slice(0, 10),
                km_dau: t.km_dau, km_cuoi: t.km_cuoi, doanh_thu: t.doanh_thu, note: t.note })}>Sửa</button>}</td>}
        </tr>) : <tr><td colSpan={canNhap ? 10 : 9} className="muted">Chưa có chuyến nào được ghi nhật trình.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "giaodich" && formDX && <div className="panel">
      <h2>Lập đề xuất chi</h2>
      <p className="muted">Cùng bộ trường với phiếu đề xuất chi trên Vietrip. Bắt buộc chọn <b>nhóm</b>: &quot;nạp thẻ dầu&quot;
        và &quot;sửa xe&quot; nhìn giống nhau lúc lập phiếu, nhưng một cái là nạp quỹ còn một cái là chi phí — không phân loại
        ngay thì cuối tháng phải đọc lại từng phiếu để đoán.</p>
      <div className="grid2">
        <label>Ngày đề xuất<input type="date" value={formDX.ngay || ""} onChange={(e) => setFormDX({ ...formDX, ngay: e.target.value })} /></label>
        <label>Số tiền (đ)<input type="number" value={formDX.so_tien ?? ""} onChange={(e) => setFormDX({ ...formDX, so_tien: Number(e.target.value) })} /></label>
        <label>Xe (để trống = đề xuất chung)
          <select value={formDX.bien_so || ""} onChange={(e) => setFormDX({ ...formDX, bien_so: e.target.value })}>
            <option value="">— đề xuất chung, không thuộc xe nào —</option>
            {xe.map((v: any) => <option key={v.id} value={v.plate}>{v.plate}</option>)}
          </select></label>
        <label>Nhóm khoản chi
          <select value={formDX.nhom || ""} onChange={(e) => {
            const n = e.target.value;
            setFormDX({ ...formDX, nhom: n, khong_phai_chi_phi: n.startsWith("Nạp quỹ") || n.startsWith("Điều chuyển") });
          }}>
            <option value="">— chọn nhóm —</option>
            <option>Chi phí riêng của xe</option>
            <option>Chi phí chung phân bổ</option>
            <option>Sửa chữa – bảo dưỡng</option>
            <option>Tài xế (công tác phí, lương)</option>
            <option>Quyết toán chủ xe / đối tác</option>
            <option>Nạp quỹ / tạm ứng (không phải chi phí)</option>
            <option>Điều chuyển tiền nội bộ (không phải chi phí)</option>
          </select></label>
        <label>Số chứng từ<input value={formDX.chung_tu || ""} onChange={(e) => setFormDX({ ...formDX, chung_tu: e.target.value })} placeholder="HĐ 0000xxxx" /></label>
        <label>Người / đơn vị thụ hưởng<input value={formDX.nguoi_thu_huong || ""} onChange={(e) => setFormDX({ ...formDX, nguoi_thu_huong: e.target.value })} /></label>
        <label>Số tài khoản<input value={formDX.so_tai_khoan || ""} onChange={(e) => setFormDX({ ...formDX, so_tai_khoan: e.target.value })} /></label>
        <label>Ngân hàng<input value={formDX.ngan_hang || ""} onChange={(e) => setFormDX({ ...formDX, ngan_hang: e.target.value })} /></label>
      </div>
      <label style={{ display: "block", marginTop: 8 }}>Nội dung đề xuất
        <textarea rows={4} value={formDX.noi_dung || ""} onChange={(e) => setFormDX({ ...formDX, noi_dung: e.target.value })} /></label>
      {formDX.khong_phai_chi_phi && <p className="muted">Khoản này được đánh dấu <b>không phải chi phí kỳ này</b> nên
        sẽ không cộng vào tổng chi phí đội xe — tiền dầu thật nằm ở phiếu chi phí của từng chuyến.</p>}
      <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
        <button className="act teal" disabled={dangLuu} onClick={luuDeXuat}>{dangLuu ? "Đang lưu…" : "Lập đề xuất"}</button>
        <button className="act grey" onClick={() => setFormDX(null)}>Đóng</button>
      </div>
    </div>}

    {tab === "giaodich" && gd?.rows?.some((r: any) => r.source === "de_xuat_vietrip") && <div className="panel" style={{ borderColor: "var(--orange)" }}>
      <b>Dữ liệu đối chiếu – CHƯA CHÍNH THỨC.</b>
      <p className="muted">Các dòng nguồn &quot;Đề xuất chi trên phần mềm Vietrip&quot; là bản trích để đối chiếu và
        chạy thử, không phải sổ chi phí đã duyệt của VTOS.</p>
    </div>}

    {tab === "giaodich" && gd && <div className="panel wrap"><h2>Đối soát dữ liệu nguồn ngoài</h2>
      {canNhap && !formDX && <button className="act teal" style={{ marginBottom: 10 }}
        onClick={() => setFormDX({ ngay: new Date().toISOString().slice(0, 10) })}>+ Lập đề xuất chi</button>}
      <div className="kpis">
        <div className="kpi"><b>{Number(gd.tong_chi_phi || 0).toLocaleString("vi-VN")}</b><span>chi phí (đã loại bản ghi lặp)</span></div>
        <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(gd.tong_chua_quy_ve_xe || 0).toLocaleString("vi-VN")}</b><span>chưa quy được về xe nào</span></div>
        <div className="kpi"><b className="muted">{Number(gd.tong_dieu_chuyen || 0).toLocaleString("vi-VN")}</b><span>điều chuyển tiền nội bộ – KHÔNG phải chi phí</span></div>
      </div>
      <p className="muted">{gd.ghi_chu} Biển số được tra về xe theo <b>thời điểm giao dịch</b>, không theo biển hiện tại — xe đổi biển giữa kỳ vẫn gộp đúng về một chiếc.</p>
      {gd.theo_nhom?.length > 1 && <table><thead><tr><th>Nhóm khoản</th><th>Số khoản</th><th>Số tiền</th></tr></thead>
        <tbody>{gd.theo_nhom.map((n: any) => <tr key={n.nhom}>
          <td>{n.nhom}</td><td>{n.so_khoan}</td><td className="num">{Number(n.so_tien).toLocaleString("vi-VN")}</td>
        </tr>)}</tbody></table>}
      <table><thead><tr><th>Nguồn</th><th>Mã giao dịch</th><th>Thời điểm</th><th>Biển / thẻ</th><th>Xe</th><th>Nhóm</th><th>Số tiền</th><th>Trạng thái</th></tr></thead>
        <tbody>{gd.rows.length ? gd.rows.map((r: any) => <tr key={r.id}>
          <td>{r.source_ten || (r.source === "epass" ? "ePass/VETC" : "Thẻ dầu")}</td><td>{r.ma_gd}</td><td>{fmtDT(r.thoi_diem)}</td>
          <td>{r.bien_so || (r.the_4so ? `••••${r.the_4so}` : "")}</td>
          <td>{r.xe || (r.khong_phai_chi_phi ? <span className="muted">không thuộc xe nào</span> : <Tag cls="red">chưa tra được xe</Tag>)}</td>
          <td className="muted">{r.nhom || ""}</td>
          <td className="num">{r.so_tien.toLocaleString("vi-VN")}</td>
          <td><Tag cls={r.co === "do" ? "red" : "warn"}>{r.khop === "da_khop" ? "Đã khớp chuyến" : "Chưa khớp chuyến"}</Tag>
            {r.ghi_chu && <div className="muted">{r.ghi_chu}</div>}</td>
        </tr>) : <tr><td colSpan={8} className="muted">Chưa nhập sao kê thẻ dầu, báo cáo ePass hay đề xuất chi Vietrip nào.</td></tr>}</tbody></table>
    </div>}

    {tab === "quyettoan" && <>
      {dm3 && <div className="panel"><h2>Người được tạo và chốt lệnh điều xe</h2>
        {dm3.nguoi_lap_lenh?.length
          ? <p>{dm3.nguoi_lap_lenh.map((x: any) => <Tag key={x.username} cls="ok">{x.full_name} ({x.username})</Tag>)} <span className="muted">— chỉ đạo 07/9/2026. Thay người phụ trách thì sửa tham số chính sách <code>xe_nguoi_lap_lenh</code>, không phải sửa phần mềm.</span></p>
          : <p><Tag cls="warn">Chưa áp dụng</Tag> <span className="muted">{dm3.nguoi_lap_lenh_ghi_chu}</span></p>}
      </div>}

      <div className="panel wrap"><h2>Chủ xe hợp tác ({chuXe.length})</h2>
        <table><thead><tr><th>Chủ xe</th><th>Pháp nhân đối ứng</th><th>Xe</th><th>Công nợ còn lại</th><th>Định danh</th></tr></thead>
          <tbody>{chuXe.length ? chuXe.map((p) => <tr key={p.id}>
            <td><b>{p.ho_ten}</b>{p.phone && <div className="muted">{p.phone}</div>}</td>
            <td>{p.company || <span className="muted">chưa xác định</span>}</td>
            <td>{p.xe.join(", ") || <span className="muted">chưa gán xe</span>}</td>
            <td className="num">{p.cong_no_con_lai.toLocaleString("vi-VN")}</td>
            <td>{p.xac_minh === "da_xac_minh" ? <Tag cls="ok">đã đối chiếu</Tag> : <Tag cls="warn">theo nguồn</Tag>}</td>
          </tr>) : <tr><td colSpan={5} className="muted">Chưa có chủ xe hợp tác nào trong hệ thống.</td></tr>}</tbody></table>
      </div>

      <div className="panel wrap"><h2>Quyết toán chủ xe theo kỳ ({qt.length})</h2>
        <p className="muted">Kỳ là tháng dương lịch, chuyến gán theo ngày khởi hành. <b>Số âm ghi thành phải thu và chuyển kỳ sau, không tạo phiếu chi âm.</b> Đóng kỳ rồi thì khóa — sửa phải ghi bút toán điều chỉnh ở kỳ sau.</p>
        <table><thead><tr><th>Kỳ</th><th>Chủ xe</th><th>Doanh thu</th><th>Đối tác chịu</th><th>Điều chỉnh</th><th>Trước cấn trừ</th><th>Cấn trừ</th><th>Phải trả</th><th>Chuyển kỳ sau</th><th>Trạng thái</th></tr></thead>
          <tbody>{qt.length ? qt.map((s) => <tr key={s.id}>
            <td>{s.ky}</td><td>{s.chu_xe}</td>
            <td className="num">{s.doanh_thu.toLocaleString("vi-VN")}</td>
            <td className="num">{s.doi_tac_chiu.toLocaleString("vi-VN")}</td>
            <td className="num">{s.dieu_chinh.toLocaleString("vi-VN")}</td>
            <td className="num">{s.truoc_can_tru.toLocaleString("vi-VN")}</td>
            <td className="num">{s.can_tru.toLocaleString("vi-VN")}</td>
            <td className="num"><b>{s.sau_can_tru.toLocaleString("vi-VN")}</b></td>
            <td className="num">{s.chuyen_ky_sau ? <Tag cls="warn">{s.chuyen_ky_sau.toLocaleString("vi-VN")}</Tag> : ""}</td>
            <td>{s.status === "dong_ky" ? <Tag cls="ok">{s.status_ten}</Tag> : <Tag cls="warn">{s.status_ten}</Tag>}</td>
          </tr>) : <tr><td colSpan={10} className="muted">Chưa dựng kỳ quyết toán nào.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "congno" && cn && <>
      <div className="panel">
        <h2>Công nợ đội xe</h2>
        <p className="muted">Bốn khoản dưới đây với bốn đối tượng khác nhau nên để riêng, KHÔNG cộng thành một
          con số &quot;công nợ đội xe&quot;. Tính đến {fmtDT(cn.tinh_den)}.</p>
        <div className="kpis">
          <div className="kpi"><b>{Number(cn.voi_chu_xe.cong_ty_phai_tra).toLocaleString("vi-VN")}</b>
            <span>công ty phải trả chủ xe (kỳ đã chốt, đã trừ phần đã chi)</span></div>
          <div className="kpi"><b>{Number(cn.voi_chu_xe.chu_xe_phai_tra_cong_ty).toLocaleString("vi-VN")}</b>
            <span>chủ xe phải trả công ty (chuyển kỳ sau + nợ theo lịch)</span></div>
          <div className="kpi"><b>{Number(cn.ban_xe.con_phai_thu).toLocaleString("vi-VN")}</b>
            <span>còn phải thu của người mua xe</span></div>
          <div className="kpi"><b>{Number(cn.vay_the_chap_xe.du_no_theo_khe_uoc).toLocaleString("vi-VN")}</b>
            <span>dư nợ ngân hàng có thế chấp xe (cộng theo khế ước)</span></div>
        </div>
        <div className="kpis">
          <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(cn.voi_chu_xe.dang_tinh_chua_chot).toLocaleString("vi-VN")}</b>
            <span>đang tính, chưa chốt với đối tác – chưa phải công nợ</span></div>
          <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(cn.voi_chu_xe.chi_ho_chua_vao_ky).toLocaleString("vi-VN")}</b>
            <span>công ty đã chi hộ nhưng tháng đó chưa dựng bảng quyết toán</span></div>
          <div className="kpi"><b style={{ color: cn.voi_chu_xe.so_chu_xe_chua_co_bang ? "var(--orange)" : undefined }}>{cn.voi_chu_xe.so_chu_xe_chua_co_bang}</b>
            <span>chủ xe chưa có bảng quyết toán nào (chưa biết, không phải bằng 0)</span></div>
        </div>
        <ul className="muted" style={{ marginTop: 8 }}>{cn.giai_thich.map((g: string, i: number) => <li key={i}>{g}</li>)}</ul>
      </div>

      <div className="panel wrap">
        <h2>Theo chủ xe hợp tác</h2>
        <table><thead><tr><th>Chủ xe</th><th>Xe</th><th>Công ty phải trả</th><th>Đang tính, chưa chốt</th>
          <th>Chủ xe phải trả công ty</th><th>Chi hộ chưa vào kỳ</th><th>Tình trạng</th><th></th></tr></thead>
          <tbody>{cn.voi_chu_xe.chi_tiet.length ? cn.voi_chu_xe.chi_tiet.map((c: any) => <tr key={c.partner_id}>
            <td>{c.ho_ten}</td>
            <td className="muted">{c.xe.map((x: any) => x.plate).join(", ") || "—"}</td>
            <td>{Number(c.cong_ty_phai_tra).toLocaleString("vi-VN")}</td>
            <td className="muted">{Number(c.dang_tinh_chua_chot).toLocaleString("vi-VN")}</td>
            <td>{Number(c.chu_xe_phai_tra_cong_ty).toLocaleString("vi-VN")}</td>
            <td className={c.tong_chi_ho_chua_vao_ky ? "" : "muted"}>{Number(c.tong_chi_ho_chua_vao_ky).toLocaleString("vi-VN")}</td>
            <td>{c.tinh_trang === "chua_co_bang_quyet_toan"
              ? <Tag cls="warn">Chưa có bảng quyết toán</Tag> : <Tag cls="ok">Có dữ liệu</Tag>}</td>
            <td><button className="act grey" onClick={async () => {
              try { setSoChuXe(await api(`/fleet/cong-no/chu-xe/${c.partner_id}`)); } catch (e) { toast(errMsg(e), true); }
            }}>Sổ chi tiết</button></td>
          </tr>) : <tr><td colSpan={8} className="muted">Chưa có chủ xe hợp tác nào.</td></tr>}</tbody></table>
      </div>

      {soChuXe && <div className="panel wrap">
        <h2>Sổ chi tiết – {soChuXe.ho_ten}</h2>
        {soChuXe.ghi_chu && <p className="muted">{soChuXe.ghi_chu}</p>}
        <h3>Từng kỳ quyết toán</h3>
        <table><thead><tr><th>Kỳ</th><th>Trạng thái</th><th>Doanh thu</th><th>Đối tác chịu</th><th>Cấn trừ</th>
          <th>Phải trả theo bảng</th><th>Đã trả</th><th>Còn phải trả</th><th>Chuyển kỳ sau</th></tr></thead>
          <tbody>{soChuXe.cac_ky.length ? soChuXe.cac_ky.map((k: any) => <tr key={k.settlement_id}>
            <td>{k.ky}</td>
            <td>{k.da_chot ? <Tag cls="ok">Đã chốt</Tag> : <Tag cls="warn">Đang tính</Tag>}</td>
            <td>{Number(k.doanh_thu).toLocaleString("vi-VN")}</td>
            <td>{Number(k.doi_tac_chiu).toLocaleString("vi-VN")}</td>
            <td>{Number(k.can_tru).toLocaleString("vi-VN")}</td>
            <td>{Number(k.phai_tra_theo_bang).toLocaleString("vi-VN")}</td>
            <td>{Number(k.da_tra).toLocaleString("vi-VN")}</td>
            <td><b>{k.da_chot ? Number(k.con_phai_tra).toLocaleString("vi-VN") : "—"}</b></td>
            <td className="muted">{Number(k.chuyen_ky_sau).toLocaleString("vi-VN")}</td>
          </tr>) : <tr><td colSpan={9} className="muted">Chưa dựng kỳ nào cho chủ xe này.</td></tr>}</tbody></table>

        {soChuXe.lich_can_tru.length > 0 && <><h3>Lịch cấn trừ (nợ mua xe)</h3>
          <table><thead><tr><th>Lịch</th><th>Trạng thái</th><th>Gốc</th><th>Đã cấn trừ</th><th>Còn lại</th></tr></thead>
            <tbody>{soChuXe.lich_can_tru.map((l: any) => <tr key={l.plan_id}>
              <td>{l.ten}</td><td>{l.status}</td>
              <td>{Number(l.principal).toLocaleString("vi-VN")}</td>
              <td>{Number(l.da_can_tru).toLocaleString("vi-VN")}</td>
              <td><b>{Number(l.con_lai).toLocaleString("vi-VN")}</b></td>
            </tr>)}</tbody></table></>}

        {soChuXe.chi_ho_chua_vao_ky.length > 0 && <><h3>Khoản đã chi hộ chưa vào kỳ quyết toán nào</h3>
          <p className="muted">Tiền công ty đã bỏ ra nhưng tháng đó chưa ai dựng bảng – trên giấy tờ chưa ai nợ khoản này.</p>
          <table><thead><tr><th>Tháng</th><th>Số tiền</th></tr></thead>
            <tbody>{soChuXe.chi_ho_chua_vao_ky.map((x: any) => <tr key={x.ky}>
              <td>{x.ky}</td><td>{Number(x.so_tien).toLocaleString("vi-VN")}</td></tr>)}</tbody></table></>}

        <h3>Đã trả / đã thu</h3>
        <table><thead><tr><th>Ngày</th><th>Hướng</th><th>Số tiền</th><th>Kỳ</th><th>Chứng từ</th><th>Người ghi</th></tr></thead>
          <tbody>{soChuXe.thanh_toan?.length ? soChuXe.thanh_toan.map((t: any) => <tr key={t.id}>
            <td>{fmtD(t.ngay)}</td><td>{t.huong_ten}</td>
            <td>{Number(t.so_tien).toLocaleString("vi-VN")}</td>
            <td className="muted">{t.settlement_id || "—"}</td>
            <td className="muted">{t.chung_tu || "—"}</td><td className="muted">{t.boi}</td>
          </tr>) : <tr><td colSpan={6} className="muted">Chưa ghi nhận lần trả/thu nào. Đóng kỳ KHÔNG có nghĩa là tiền đã đi.</td></tr>}</tbody></table>
      </div>}

      <div className="panel wrap">
        <h2>Còn phải thu của người mua xe</h2>
        <table><thead><tr><th>Xe</th><th>Giá bán</th><th>Đã thu</th><th>Còn phải thu</th><th>Bàn giao</th>
          <th>Giải chấp</th><th>Sang tên</th><th>Cảnh báo</th></tr></thead>
          <tbody>{cn.ban_xe.chi_tiet.length ? cn.ban_xe.chi_tiet.map((b: any) => <tr key={b.sale_case_id}>
            <td>{b.xe}</td>
            <td>{Number(b.gia_ban).toLocaleString("vi-VN")}</td>
            <td>{Number(b.da_thu).toLocaleString("vi-VN")}</td>
            <td><b>{Number(b.con_phai_thu).toLocaleString("vi-VN")}</b></td>
            <td>{b.da_ban_giao ? "Rồi" : "Chưa"}</td>
            <td>{b.da_giai_chap ? "Rồi" : "Chưa"}</td>
            <td>{b.da_sang_ten ? "Rồi" : "Chưa"}</td>
            <td>{b.canh_bao ? <Tag cls="red">{b.canh_bao}</Tag> : ""}</td>
          </tr>) : <tr><td colSpan={8} className="muted">Không có hồ sơ bán xe nào còn phải thu.</td></tr>}</tbody></table>
      </div>

      <div className="panel wrap">
        <h2>Dư nợ ngân hàng có thế chấp xe</h2>
        <p className="muted">Cộng theo KHẾ ƯỚC. Ngân hàng nhận cả gói nhiều xe cho một khoản vay, nên chia dư nợ
          về từng xe rồi cộng lại sẽ ra một con số không có thật.</p>
        <table><thead><tr><th>Khế ước</th><th>Ngân hàng</th><th>Pháp nhân</th><th>Dư nợ</th><th>Lãi suất</th>
          <th>Đáo hạn</th><th>Xe đang thế chấp</th></tr></thead>
          <tbody>{cn.vay_the_chap_xe.chi_tiet.length ? cn.vay_the_chap_xe.chi_tiet.map((k: any) => <tr key={k.contract_id}>
            <td>{k.code}</td><td>{k.ngan_hang}</td><td className="muted">{k.phap_nhan}</td>
            <td><b>{Number(k.du_no).toLocaleString("vi-VN")}</b></td>
            <td className="muted">{k.lai_suat}%</td>
            <td className="muted">{k.dao_han ? fmtD(k.dao_han) : "Hồ sơ không ghi"}</td>
            <td className="muted">{k.xe.map((x: any) => x.plate).join(", ")}</td>
          </tr>) : <tr><td colSpan={7} className="muted">Không có khế ước nào đang thế chấp xe.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "xe" && <div className="panel wrap"><h2>Danh sách xe ({xe.length})</h2>
      <table><thead><tr><th>Mã xe</th><th>Biển đang dùng</th><th>Quyền khai thác</th><th>Vòng đời</th><th>Pháp nhân sở hữu</th><th>Đối tác</th><th>Hợp đồng</th><th>Tài xế</th><th>Điều kiện hôm nay</th></tr></thead>
        <tbody>{xe.map((v) => <tr key={v.id} onClick={() => mo(v.id)} style={{ cursor: "pointer" }}>
          <td><b>{v.code || "—"}</b></td><td>{v.plate}</td><td>{v.op_right_ten}</td><td>{v.lifecycle_ten}</td>
          <td>{v.owner_company || <span className="muted">chưa xác định</span>}</td>
          <td>{v.partner_name || ""}</td><td>{v.contract_ref || ""}</td><td>{v.driver || <span className="muted">chưa gán</span>}</td>
          <td><Tag cls={MUC_CLS[v.san_sang?.muc] || ""}>{MUC_TEN[v.san_sang?.muc] || v.san_sang?.muc}</Tag>
            {v.san_sang?.ly_do?.length > 0 && <div className="muted">{v.san_sang.ly_do[0]}</div>}</td>
        </tr>)}</tbody></table>
    </div>}

    {tab === "xe" && chon && <div className="panel"><h2>Hồ sơ xe {chon.code} · {chon.plate}</h2>
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

    {tab === "xe" && <div className="panel wrap"><h2>Hàng đợi xác minh hồ sơ ({xm.filter((x) => x.status !== "xong" && x.status !== "khong_ap_dung").length} còn treo)</h2>
      <p className="muted">Những việc hệ thống không tự quyết được và cần người trả lời. Hệ thống nói ra chỗ nó không chắc, thay vì tự điền cho đủ form.</p>
      <table><thead><tr><th>Đối tượng</th><th>Việc cần xác minh</th><th>Nguồn</th><th>Trạng thái</th><th>Kết luận</th>{canWrite && <th></th>}</tr></thead>
        <tbody>{xm.map((x) => <tr key={x.id} style={{ opacity: x.status === "xong" ? 0.55 : 1 }}>
          <td>{x.ref}</td><td>{x.issue}</td><td className="muted">{x.source}</td>
          <td>{x.status === "xong" ? <Tag cls="ok">{x.status_ten}</Tag> : <Tag cls="warn">{x.status_ten}</Tag>}</td>
          <td className="muted">{x.resolution}{x.resolved_by ? ` — ${x.resolved_by}, ${fmtDT(x.resolved_at)}` : ""}</td>
          {canWrite && <td>{x.status !== "xong" && x.status !== "khong_ap_dung" && <button className="act teal" onClick={() => dongViec(x.id)}>Kết luận</button>}</td>}
        </tr>)}</tbody></table>
    </div>}
  </>);
}

export default function Page() { return <Shell><DoiXe /></Shell>; }
