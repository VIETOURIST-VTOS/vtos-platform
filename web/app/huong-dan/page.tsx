"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD, fmtDT, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Phòng Hướng dẫn – màn hình của người điều phối, khi toàn bộ HDV là cộng tác viên.
 *
 *  Chữ dùng ở đây là "chào chuyến", không phải "phân công". Không phải chuyện chữ nghĩa: luật xét NỘI
 *  DUNG quan hệ chứ không xét tên hợp đồng, và màn hình này cùng dữ liệu của nó chính là nơi lưu bằng
 *  chứng về nội dung đó. Hạn 24 giờ vẫn còn, nhưng là hạn hiệu lực của LỜI CHÀO – quá hạn thì chuyến
 *  chào người khác, không phải hướng dẫn viên vi phạm. */
const TABS: [string, string][] = [["viec", "Việc cần làm"], ["hdv", "Đội ngũ HDV"], ["chao", "Chào chuyến"],
  ["yeucau", "Yêu cầu HDV"], ["baocao", "Báo cáo sau tour"], ["tien", "Tiền HDV"], ["dexuat", "Đề xuất"]];

function HuongDan() {
  const { user, toast } = useShell();
  const [tab, setTab] = useState("viec");
  const [tq, setTq] = useState<any>(null);
  const [hdv, setHdv] = useState<any>(null);
  const [can, setCan] = useState<any[]>([]);
  const [chao, setChao] = useState<any[]>([]);
  const [tepHdv, setTepHdv] = useState("");
  const [form, setForm] = useState<any>(null);        // lời chào đang soạn
  const [hs, setHs] = useState<any>(null);            // hồ sơ hành nghề đang sửa
  const [luu, setLuu] = useState(false);
  // Bốn khối của Đợt 1–4 phòng HDV. Mỗi khối tải riêng và CHỊU ĐƯỢC LỖI: một cửa chưa mở quyền thì
  // khối ấy trống, không làm trắng cả màn hình.
  const [yc, setYc] = useState<any[]>([]);
  const [thieu, setThieu] = useState<any>(null);
  const [fYc, setFYc] = useState<any>(null);
  const [tien, setTien] = useState<any>(null);
  const [aiXem, setAiXem] = useState<string>("");
  const [dx, setDx] = useState<any[]>([]);
  const [fDx, setFDx] = useState<any>(null);
  const canDieuPhoi = ["tp_hd", "tp_dh", "nv_dh", "hcns", "cntt"].includes(user?.role || "");
  // Chỉ Chủ tịch / TGĐ thấy nút công bố chính sách duyệt. Ẩn nút KHÔNG phải là hàng rào — hàng rào
  // thật nằm ở require_roles của cửa; ẩn ở đây chỉ để người khác không bấm rồi nhận 403.
  const canCongBo = ["chutich", "tgd"].includes(user?.role || "");

  const load = useCallback(async () => {
    try {
      setTq(await api("/huong-dan/tong-quan"));
      setHdv(await api("/huong-dan/hdv"));
      setCan(await api("/huong-dan/chuyen-can-hdv"));
      setChao(await api("/huong-dan/chao-chuyen"));
      // Bốn cửa mới: lỗi của cửa nào thì chỉ khối ấy trống.
      api<any[]>("/guide-assignments/yeu-cau").then(setYc).catch(() => setYc([]));
      api<any>("/guide-assignments/yeu-cau/thieu").then(setThieu).catch(() => setThieu(null));
      api<any[]>("/guide-assignments/de-xuat").then(setDx).catch(() => setDx([]));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const chaoChuyen = async () => {
    setLuu(true);
    try {
      const d = await api<any>("/huong-dan/chao-chuyen", { method: "POST", json: {
        tour_id: Number(form.tour_id), guide_id: Number(form.guide_id), days: Number(form.days) || 1,
        rate_per_day: soTien(form.rate_per_day), holiday: !!form.holiday } });
      toast(d.message); setForm(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const luuHoSo = async () => {
    setLuu(true);
    try {
      const body: any = { the_so: hs.the_so || "", the_loai: hs.the_loai || "",
        the_het_han: hs.the_het_han || null, hoi_vien: !!hs.hoi_vien,
        hop_dong_cong_tac: !!hs.hop_dong_cong_tac, dien_thoai: hs.dien_thoai || "",
        tuyen_phu_trach: hs.tuyen_phu_trach || "",
        han_muc_tam_ung: Number(hs.han_muc_tam_ung) || 0 };
      const d = hs.id
        ? await api<any>(`/huong-dan/hdv/${hs.id}`, { method: "PUT", json: body })
        : await api<any>("/huong-dan/hdv", { method: "POST",
            json: { ...body, ho_ten: hs.ho_ten, ma_nv: hs.ma_nv || "" } });
      toast(d.message); setHs(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const lapYeuCau = async () => {
    setLuu(true);
    try {
      const r = await api<any>("/guide-assignments/yeu-cau", { method: "POST", json: {
        tour_id: Number(fYc.tour_id), so_hdv: Number(fYc.so_hdv) || 1,
        // Giờ để trống thì gửi null, KHÔNG gửi chuỗi rỗng: lúc Điều hành gửi yêu cầu nhiều khi chưa
        // chốt giờ đón với khách, và "chưa chốt" phải đi tới máy chủ đúng là chưa chốt.
        bat_dau: fYc.bat_dau || null, ket_thuc: fYc.ket_thuc || null,
        ngoai_ngu: fYc.ngoai_ngu || "", nang_luc: fYc.nang_luc || "",
        diem_hen: fYc.diem_hen || "", ghi_chu: fYc.ghi_chu || "" } });
      toast(r.message); setFYc(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const huyYeuCau = async (y: any) => {
    const ly_do = window.prompt("Huỷ yêu cầu này vì lý do gì?", "");
    if (ly_do === null) return;
    try { const r = await api<any>(`/guide-assignments/yeu-cau/${y.id}/huy`,
            { method: "POST", json: { phien_ban: y.phien_ban, ly_do } });
          toast(r.message); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const kiemBaoCao = async (aid: number, pb: number | null, xac_nhan: boolean) => {
    let y_kien = "";
    if (!xac_nhan) {
      const v = window.prompt("Trả lại báo cáo — thiếu gì?\n\nBắt buộc ghi: không ghi thì người nộp phải đoán.", "");
      if (v === null) return;
      y_kien = v;
    }
    try { const r = await api<any>(`/guide-assignments/${aid}/bao-cao/kiem`,
            { method: "POST", json: { phien_ban: pb, xac_nhan, y_kien } });
          toast(r.message); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const xemTien = async (guide_id: number) => {
    try { setTien(await api<any>(`/guide-assignments/tam-ung/so-theo-nguoi?guide_id=${guide_id}`)); }
    catch (e) { toast(errMsg(e), true); }
  };

  const congBoMotCap = async () => {
    if (!window.confirm("Công bố: mọi đề xuất phòng HDV chỉ qua MỘT cấp — Chủ tịch hoặc TGĐ ký là "
      + "xong, ở mọi mức tiền. Chữ ký sẽ ghi tên anh/chị. Loại đã có đường đi thì giữ nguyên.")) return;
    try { const r = await api<any>("/guide-assignments/de-xuat/cau-hinh/khai-mot-cap",
            { method: "POST", json: {} });
          toast(r.message); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const lapDeXuat = async () => {
    setLuu(true);
    try {
      const r = await api<any>("/guide-assignments/de-xuat", { method: "POST", json: {
        loai: fDx.loai, ly_do: fDx.ly_do || "", noi_dung: fDx.noi_dung || "",
        can_cu_tinh: fDx.can_cu_tinh || "",
        // Số tiền để trống = đề xuất không mang tiền (xin bổ sung nhân sự). Trống khác 0.
        so_tien: String(fDx.so_tien || "").trim() === "" ? null : soTien(fDx.so_tien) } });
      toast(r.message); setFDx(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const trinhDeXuat = async (d: any) => {
    try { const r = await api<any>(`/guide-assignments/de-xuat/${d.id}/trinh`,
            { method: "POST", json: { phien_ban: d.phien_ban } });
          toast(r.message); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const dongLoiChao = async (id: number) => {
    const ly_do = window.prompt("Đóng lời chào này vì lý do gì?\n\n" +
      "Ghi nhận là LỜI CHÀO HẾT HIỆU LỰC, không phải hướng dẫn viên vi phạm.", "quá hạn trả lời");
    if (ly_do === null) return;
    try { const d = await api<any>(`/huong-dan/chao-chuyen/${id}/dong`, { method: "POST", json: { ly_do } });
          toast(d.message); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  if (!tq) return <p className="muted">Đang tải…</p>;
  return (<>
    <h1>Phòng Hướng dẫn</h1>
    <p className="muted">Toàn bộ hướng dẫn viên là <b>cộng tác viên</b>. Vì vậy màn hình này <b>chào chuyến</b> chứ
      không phân công: công ty chào tuyến, ngày và đơn giá; hướng dẫn viên nhận hoặc từ chối. Hạn 24 giờ là
      hạn hiệu lực của lời chào — quá hạn thì chuyến chào người khác, không ghi nhận ai vi phạm.</p>

    <div className="kpis">
      <div className="kpi"><b>{tq.hdv_dang_cong_tac}</b><span>HDV đang cộng tác</span></div>
      <div className="kpi"><b style={{ color: tq.du_dieu_kien < tq.hdv_dang_cong_tac ? "var(--red)" : undefined }}>
        {tq.du_dieu_kien}</b><span>đủ điều kiện hành nghề (cổng 13)</span></div>
      <div className="kpi"><b>{tq.the_sap_het_han}</b><span>thẻ hết hạn trong 60 ngày</span></div>
      <div className="kpi"><b style={{ color: tq.chuyen_chua_co_hdv ? "var(--red)" : undefined }}>
        {tq.chuyen_chua_co_hdv}</b><span>chuyến 30 ngày tới chưa có HDV</span></div>
      <div className="kpi"><b>{tq.cho_nhan_chuyen}</b><span>lời chào đang chờ trả lời</span></div>
      <div className="kpi"><b>{tq.tre_bao_cao}</b><span>trễ báo cáo tour quá 3 ngày</span></div>
    </div>

    <div style={{ display: "flex", gap: 8, margin: "10px 0", flexWrap: "wrap" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }}
                                    onClick={() => setTab(k)}>{l}</button>)}
    </div>

    {hs && <div className="panel">
      <h2>{hs.id ? `Hồ sơ hành nghề – ${hs.ho_ten}` : "Thêm hướng dẫn viên cộng tác"}</h2>
      <p className="muted">Ba điều kiện của Điều 58 Luật Du lịch: thẻ hướng dẫn viên còn hạn, hội viên
        tổ chức xã hội – nghề nghiệp, và hợp đồng cộng tác đã ký. Thiếu một điều là chuyến dẫn đó vi
        phạm, và người bị xử phạt gồm cả doanh nghiệp — nên cổng 13 chặn theo dữ liệu ở đây.</p>
      <div className="grid2">
        {!hs.id && <label>Họ và tên
          <input value={hs.ho_ten} onChange={(e) => setHs({ ...hs, ho_ten: e.target.value })} /></label>}
        {!hs.id && <label>Mã nhân viên <span className="muted">(để trống thì hệ thống tự cấp)</span>
          <input value={hs.ma_nv} onChange={(e) => setHs({ ...hs, ma_nv: e.target.value })} /></label>}
        <label>Số thẻ hướng dẫn viên
          <input value={hs.the_so} placeholder="VD: HDV-NĐ-2023-0451"
                 onChange={(e) => setHs({ ...hs, the_so: e.target.value })} /></label>
        <label>Loại thẻ
          <select value={hs.the_loai} onChange={(e) => setHs({ ...hs, the_loai: e.target.value })}>
            <option value="">— chưa ghi —</option>
            <option value="noi_dia">Nội địa</option><option value="quoc_te">Quốc tế</option>
          </select></label>
        <label>Ngày hết hạn thẻ
          <input type="date" value={hs.the_het_han}
                 onChange={(e) => setHs({ ...hs, the_het_han: e.target.value })} /></label>
        <label>Điện thoại
          <input value={hs.dien_thoai} onChange={(e) => setHs({ ...hs, dien_thoai: e.target.value })} /></label>
        <label>Tuyến phụ trách
          <input value={hs.tuyen_phu_trach} placeholder="VD: Miền Trung, Tây Nguyên"
                 onChange={(e) => setHs({ ...hs, tuyen_phu_trach: e.target.value })} /></label>
        <label>Hạn mức tạm ứng
          <input type="number" step={100000} value={hs.han_muc_tam_ung}
                 onChange={(e) => setHs({ ...hs, han_muc_tam_ung: e.target.value })} /></label>
      </div>
      <label style={{ display: "block", marginTop: 6 }}>
        <input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={!!hs.hoi_vien}
               onChange={(e) => setHs({ ...hs, hoi_vien: e.target.checked })} />
        Là hội viên tổ chức xã hội – nghề nghiệp về hướng dẫn du lịch
      </label>
      <label style={{ display: "block" }}>
        <input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={!!hs.hop_dong_cong_tac}
               onChange={(e) => setHs({ ...hs, hop_dong_cong_tac: e.target.checked })} />
        Đã ký hợp đồng cộng tác với công ty
      </label>
      <p className="muted">Biểu mẫu này chỉ sửa hồ sơ hành nghề — không có ô lương, không đổi được
        phòng ban hay loại hợp đồng. Ảnh thẻ và bản hợp đồng đính kèm ở nút <b>Tệp</b> của từng người.</p>
      <button className="act teal" disabled={luu || (!hs.id && !hs.ho_ten.trim())}
              onClick={luuHoSo}>{luu ? "Đang lưu…" : "Lưu hồ sơ"}</button>{" "}
      <button className="act grey" onClick={() => setHs(null)}>Đóng</button>
    </div>}

    {form && <div className="panel">
      <h2>Chào chuyến {form.tour_code}</h2>
      <p className="muted">Chào tuyến, số ngày và đơn giá cho một hướng dẫn viên. Người nhận có quyền
        từ chối mà không kèm hệ quả gì — đây là lời chào dịch vụ, không phải lệnh giao việc.</p>
      <div className="grid2">
        <label>Hướng dẫn viên
          <select value={form.guide_id} onChange={(e) => setForm({ ...form, guide_id: e.target.value })}>
            <option value="">— chọn người —</option>
            {(hdv?.rows || []).filter((h: any) => h.du_dieu_kien && h.dang_lam)
              .map((h: any) => <option key={h.id} value={h.id}>{h.code} · {h.full_name}</option>)}
          </select></label>
        <label>Số ngày
          <input type="number" min={1} value={form.days}
                 onChange={(e) => setForm({ ...form, days: e.target.value })} /></label>
        <label>Đơn giá / ngày
          <input type="number" step={10000} value={form.rate_per_day}
                 onChange={(e) => setForm({ ...form, rate_per_day: e.target.value })} /></label>
        <label>Lễ Tết (×2)
          <select value={form.holiday ? "1" : "0"}
                  onChange={(e) => setForm({ ...form, holiday: e.target.value === "1" })}>
            <option value="0">Không</option><option value="1">Có – nhân đôi thù lao</option>
          </select></label>
      </div>
      <p className="muted">Chỉ hiện những người đủ ba điều kiện hành nghề — cổng 13 sẽ chặn lần nữa ở
        máy chủ, nên danh sách này là để đỡ mất công, không phải là chốt chặn duy nhất.</p>
      <button className="act teal" disabled={luu || !form.guide_id || !form.rate_per_day}
              onClick={chaoChuyen}>{luu ? "Đang gửi…" : "Gửi lời chào"}</button>{" "}
      <button className="act grey" onClick={() => setForm(null)}>Đóng</button>
    </div>}

    {tab === "viec" && <div className="panel wrap">
      <h2>Chuyến sắp khởi hành chưa có hướng dẫn viên</h2>
      <p className="muted">Xếp theo ngày gần nhất. Không hiện danh sách khách — chọn người cần biết tuyến,
        ngày và quy mô, không cần biết ai đi chuyến đó.</p>
      <table><thead><tr><th>Mã tour</th><th>Tuyến</th><th>Khởi hành</th><th>Số ngày</th>
        <th>Khách dự kiến</th><th>Còn lại</th>{canDieuPhoi && <th></th>}</tr></thead>
        <tbody>{can.length ? can.map((c) => <tr key={c.tour_id}>
          <td><b>{c.code}</b></td><td>{c.name}</td><td>{fmtD(c.start_date)}</td>
          <td className="num">{c.so_ngay}</td><td className="num muted">{c.so_khach_du_kien || "—"}</td>
          <td>{c.con_lai_ngay <= 3 ? <Tag cls="red">{c.con_lai_ngay} ngày</Tag>
            : <span className="muted">{c.con_lai_ngay} ngày</span>}</td>
          {canDieuPhoi && <td><button className="act teal" style={{ margin: 0 }}
            onClick={() => setForm({ tour_id: c.tour_id, tour_code: c.code, guide_id: "",
                                     days: c.so_ngay, rate_per_day: "", holiday: false })}>Chào chuyến</button></td>}
        </tr>) : <tr><td colSpan={canDieuPhoi ? 7 : 6} className="muted">Mọi chuyến trong 30 ngày tới đều đã có người nhận.</td></tr>}</tbody></table>
    </div>}

    {tab === "hdv" && hdv && <>
      <div className="panel wrap">
        <h2>Đội ngũ hướng dẫn viên</h2>
        <p className="muted">{hdv.ghi_chu} Ba điều kiện hiện thành ba cột riêng, không gộp thành một chữ
          &quot;đạt&quot; — người điều phối phải biết thiếu cái gì để đi đòi cái đó.</p>
        {canDieuPhoi && <p><button className="act" onClick={() => setHs({
          id: 0, ho_ten: "", ma_nv: "", the_so: "", the_loai: "noi_dia", the_het_han: "",
          hoi_vien: false, hop_dong_cong_tac: false, dien_thoai: "", tuyen_phu_trach: "",
          han_muc_tam_ung: "" })}>+ Thêm hướng dẫn viên</button></p>}
        {hdv.du_dieu_kien === 0 && hdv.tong > 0 && <p className="muted">
          <Tag cls="red">chưa ai đủ điều kiện</Tag> Chưa hồ sơ nào có số thẻ trong hệ thống, nên cổng 13
          đang chặn mọi lời chào chuyến. Bấm <b>Sửa hồ sơ</b> ở từng dòng để nhập thẻ, hoặc tải cả danh
          sách lên ở màn hình Nạp dữ liệu (bộ nạp &quot;Hướng dẫn viên cộng tác&quot;).</p>}
        <table><thead><tr><th>Mã</th><th>Họ tên</th><th>Thẻ HDV</th><th>Hạn thẻ</th><th>Hội viên</th>
          <th>Hợp đồng cộng tác</th><th>Hạn mức ứng</th><th>Hành nghề</th><th></th></tr></thead>
          <tbody>{hdv.rows.map((h: any) => <tr key={h.id} style={{ opacity: h.dang_lam ? 1 : 0.55 }}>
            <td className="mono">{h.code}</td><td><b>{h.full_name}</b><div className="muted">{h.phone}</div></td>
            <td className="mono">{h.the_so || <Tag cls="red">chưa có</Tag>}
              <div className="muted">{h.the_loai === "quoc_te" ? "Quốc tế" : h.the_loai === "noi_dia" ? "Nội địa" : ""}</div></td>
            <td>{fmtD(h.the_het_han)}{h.sap_het_han && <div><Tag cls="warn">còn {h.con_lai_ngay} ngày</Tag></div>}</td>
            <td>{h.hoi_vien ? <Tag cls="ok">có</Tag> : <Tag cls="red">chưa</Tag>}</td>
            <td>{h.hop_dong_cong_tac ? <Tag cls="ok">đã ký</Tag> : <Tag cls="red">chưa ký</Tag>}</td>
            <td className="num muted">{h.han_muc_tam_ung ? vnd(h.han_muc_tam_ung) : "—"}</td>
            <td>{h.du_dieu_kien ? <Tag cls="ok">đủ điều kiện</Tag> : <Tag cls="red">{h.vi_sao}</Tag>}</td>
            <td style={{ whiteSpace: "nowrap" }}>
              {canDieuPhoi && <button className="act teal" style={{ margin: 0 }} onClick={() => setHs({
                id: h.id, ho_ten: h.full_name, the_so: h.the_so || "", the_loai: h.the_loai || "",
                the_het_han: h.the_het_han ? String(h.the_het_han).slice(0, 10) : "",
                hoi_vien: h.hoi_vien, hop_dong_cong_tac: h.hop_dong_cong_tac,
                dien_thoai: h.phone || "", tuyen_phu_trach: "",
                han_muc_tam_ung: h.han_muc_tam_ung || "" })}>Sửa hồ sơ</button>}{" "}
              <button className="act grey" style={{ margin: 0 }} onClick={() => setTepHdv(h.code)}>Tệp</button></td>
          </tr>)}</tbody></table>
      </div>
      {tepHdv && <DinhKem doiTuong="nhan_su" doiTuongId={tepHdv} loai="hop_dong"
        tieuDe={`Hồ sơ hành nghề – ${tepHdv}`}
        goi={"Thẻ hướng dẫn viên (hai mặt), hợp đồng cộng tác và phụ lục đơn giá, thẻ hội viên tổ chức " +
             "xã hội – nghề nghiệp, chứng nhận bảo hiểm tai nạn. Đây là bộ hồ sơ trả lời cơ quan quản lý " +
             "khi bị hỏi về một chuyến dẫn cụ thể."} />}
    </>}

    {tab === "chao" && <div className="panel wrap">
      <h2>Chào chuyến và tình trạng nhận</h2>
      <p className="muted">Cột &quot;quá hạn&quot; nghĩa là lời chào hết hiệu lực và chuyến nên chào người
        khác — không phải hướng dẫn viên vi phạm. Khác biệt đó là khác biệt giữa quan hệ dịch vụ và quan
        hệ lao động, nên nó nằm trong dữ liệu chứ không chỉ nằm trong lời nói.</p>
      <table><thead><tr><th>Tour</th><th>HDV</th><th>Khởi hành</th><th>Ngày</th><th>Đơn giá</th>
        <th>Thù lao</th><th>Tình trạng</th><th>Sau tour</th></tr></thead>
        <tbody>{chao.length ? chao.map((c) => <tr key={c.id}>
          <td><b>{c.tour_code}</b><div className="muted">{c.tour_name}</div></td>
          <td>{c.hdv}</td><td>{fmtD(c.khoi_hanh)}</td><td className="num">{c.so_ngay}</td>
          <td className="num muted">{vnd(c.don_gia)}{c.le_tet && <div><Tag cls="warn">lễ Tết ×2</Tag></div>}</td>
          <td className="num"><b>{vnd(c.thu_lao)}</b></td>
          <td>{c.trang_thai === "da_xac_nhan" ? <Tag cls="ok">đã nhận</Tag>
            : c.trang_thai === "huy" ? <Tag cls="muted">đã hủy</Tag>
              : c.loi_chao_qua_han ? <Tag cls="warn">lời chào quá hạn – chào người khác</Tag>
                : <Tag>đang chờ trả lời</Tag>}
            <div className="muted">{fmtDT(c.chao_luc)}</div></td>
          <td>{c.da_bao_cao ? <Tag cls="ok">đã báo cáo</Tag> : c.tre_bao_cao ? <Tag cls="red">trễ báo cáo</Tag> : <span className="muted">—</span>}
            {!c.da_hoan_ung && <div><Tag cls="warn">chưa hoàn ứng</Tag></div>}
            {c.treo_chao_moi && <div className="muted">đang treo chào chuyến mới</div>}
            {c.ly_do && <div className="muted">{c.ly_do}</div>}
            {canDieuPhoi && c.loi_chao_qua_han &&
              <div><button className="act grey" style={{ margin: "4px 0 0" }}
                           onClick={() => dongLoiChao(c.id)}>Đóng lời chào</button></div>}</td>
        </tr>) : <tr><td colSpan={8} className="muted">Chưa có lời chào nào.</td></tr>}</tbody></table>
      {!canDieuPhoi && <p className="muted">Anh/chị đang xem ở chế độ chỉ đọc.</p>}
    </div>}

    {/* ───── YÊU CẦU HDV (Đợt 1) ─────
        Chỗ chứa cái CHƯA xếp được người. Trước đợt này không có bảng nào giữ một chuyến thiếu HDV,
        nên câu "tuần sau bao nhiêu chuyến chưa có người" không hỏi được. */}
    {tab === "yeucau" && <div className="panel">
      <h2>Yêu cầu hướng dẫn viên</h2>
      <p className="muted">Điều hành <b>đặt hàng</b> ở đây; phòng Hướng dẫn <b>chọn người</b>.
        Một yêu cầu xin 2 người mà mới xếp 1 thì vẫn <b>còn thiếu 1</b> — không phải đã đủ.</p>

      {thieu && <div className="kpis" style={{ marginBottom: 10 }}>
        <div className="kpi"><b style={{ color: thieu.yeu_cau_con_thieu_nguoi.length ? "var(--red)" : undefined }}>
          {thieu.yeu_cau_con_thieu_nguoi.length}</b><span>yêu cầu còn thiếu người</span></div>
        <div className="kpi"><b>{thieu.yeu_cau_chua_co_gio.length}</b><span>yêu cầu chưa có giờ</span></div>
        <div className="kpi"><b>{thieu.phan_cong_chua_co_gio.length}</b><span>phân công chưa có giờ</span></div>
      </div>}
      {thieu && thieu.phan_cong_chua_co_gio.length > 0 &&
        <p className="muted">Phân công chưa có giờ thì <b>không kiểm được trùng lịch</b> — đó là việc còn
          thiếu, không phải đã kiểm và không trùng.</p>}

      {canDieuPhoi && (fYc
        ? <div className="grid2" style={{ marginBottom: 12 }}>
            <label>Mã chuyến (số)<input value={fYc.tour_id || ""}
              onChange={(e) => setFYc({ ...fYc, tour_id: e.target.value })} /></label>
            <label>Cần mấy hướng dẫn viên<input value={fYc.so_hdv || "1"} inputMode="numeric"
              onChange={(e) => setFYc({ ...fYc, so_hdv: e.target.value })} /></label>
            <label>Bắt đầu cần người <span className="muted">(tính cả chuẩn bị, di chuyển)</span>
              <input type="datetime-local" value={fYc.bat_dau || ""}
                     onChange={(e) => setFYc({ ...fYc, bat_dau: e.target.value })} /></label>
            <label>Kết thúc<input type="datetime-local" value={fYc.ket_thuc || ""}
                     onChange={(e) => setFYc({ ...fYc, ket_thuc: e.target.value })} /></label>
            <label>Ngoại ngữ<input value={fYc.ngoai_ngu || ""}
                     onChange={(e) => setFYc({ ...fYc, ngoai_ngu: e.target.value })} /></label>
            <label>Điểm hẹn<input value={fYc.diem_hen || ""}
                     onChange={(e) => setFYc({ ...fYc, diem_hen: e.target.value })} /></label>
            <div style={{ gridColumn: "1 / -1" }}>
              <button className="act teal" disabled={luu} onClick={lapYeuCau}>Gửi yêu cầu</button>{" "}
              <button className="act grey" onClick={() => setFYc(null)}>Thôi</button>
            </div>
          </div>
        : <button className="act teal" onClick={() => setFYc({ so_hdv: "1" })}>Gửi yêu cầu HDV</button>)}

      <div className="wrap"><table style={{ marginTop: 12 }}>
        <thead><tr><th>Chuyến</th><th className="num">Xin</th><th className="num">Còn thiếu</th>
          <th>Khoảng cần người</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{yc.length ? yc.map((y: any) => <tr key={y.id}>
          <td><b>{y.tour_code}</b><div className="muted">{y.tour_name}</div></td>
          <td className="num">{y.so_hdv}</td>
          <td className="num">{y.con_thieu > 0 ? <b style={{ color: "var(--red)" }}>{y.con_thieu}</b> : 0}</td>
          <td>{y.thieu_gio ? <Tag cls="warn">chưa có giờ</Tag>
             : <>{fmtDT(y.bat_dau)} → {fmtDT(y.ket_thuc)}</>}</td>
          <td><Tag cls={y.trang_thai === "da_du" ? "ok" : y.trang_thai === "huy" ? "" : "warn"}>{y.trang_thai_ten}</Tag></td>
          <td>{canDieuPhoi && y.trang_thai !== "huy" &&
            <button className="act grey" style={{ margin: 0 }} onClick={() => huyYeuCau(y)}>Huỷ</button>}</td>
        </tr>) : <tr><td colSpan={6} className="muted">Chưa có yêu cầu nào.</td></tr>}</tbody></table></div>
    </div>}

    {/* ───── BÁO CÁO SAU TOUR (Đợt 2) ───── */}
    {tab === "baocao" && <div className="panel wrap">
      <h2>Báo cáo sau tour — chờ kiểm</h2>
      <p className="muted">Hạn nộp <b>3 ngày</b> kể từ ngày tour kết thúc. <b>Gửi chưa bằng xong</b>:
        chỉ bản đã xác nhận mới gỡ treo chào chuyến và treo thù lao. Trả lại thì <b>bắt buộc ghi lý do</b>.</p>
      <table><thead><tr><th>Chuyến</th><th>HDV</th><th>Bản</th><th>Hạn</th><th></th></tr></thead>
        <tbody>{chao.filter((c: any) => c.trang_thai === "da_xac_nhan").map((c: any) => <tr key={c.id}>
          <td><b>{c.tour_code}</b></td><td>{c.hdv}</td>
          <td>{c.da_bao_cao ? <Tag cls="ok">đã xác nhận</Tag> : <Tag cls="warn">chưa xong</Tag>}</td>
          <td>{c.tre_bao_cao ? <Tag cls="red">trễ quá 3 ngày</Tag> : <span className="muted">—</span>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{!c.da_bao_cao && canDieuPhoi && <>
            <button className="act teal" style={{ margin: 0 }}
                    onClick={() => kiemBaoCao(c.id, null, true)}>Xác nhận</button>{" "}
            <button className="act grey" style={{ margin: 0 }}
                    onClick={() => kiemBaoCao(c.id, null, false)}>Trả lại</button></>}</td>
        </tr>)}</tbody></table>
      <p className="muted">Bấm <b>Xác nhận</b> chỉ ăn khi hướng dẫn viên đã <b>gửi</b> một bản — chưa gửi
        thì máy chủ từ chối, vì không có gì để kiểm.</p>
    </div>}

    {/* ───── TIỀN HDV (Đợt 3) ───── */}
    {tab === "tien" && <div className="panel">
      <h2>Tiền của hướng dẫn viên</h2>
      <p className="muted">Số dư tách theo <b>từng túi</b>: chủ tiền × loại tiền. Không gộp — 5 triệu đồng
        của công ty và 300 đô của đối tác cộng lại thành một con số không ai trả được. Tiền <b>thu hộ khách</b>
        là túi riêng, không bù trừ sang tiền công ty.</p>
      <div className="wrap" style={{ marginBottom: 10 }}>
        <label>Xem sổ của hướng dẫn viên (mã số)<br />
          <input value={aiXem} inputMode="numeric" onChange={(e) => setAiXem(e.target.value)} />{" "}
          <button className="act" onClick={() => xemTien(Number(aiXem))}>Xem</button></label>
      </div>
      {tien && <>
        <h3>{tien.hdv}</h3>
        <table><thead><tr><th>Chủ tiền</th><th>Loại tiền</th><th className="num">Đã nhận</th>
          <th className="num">Chi hộ duyệt</th><th className="num">Đã nộp lại</th><th className="num">Số dư</th><th></th></tr></thead>
          <tbody>{tien.cac_tui.map((t: any, i: number) => <tr key={i}>
            <td>{t.chu_tien}</td><td>{t.loai_tien}</td><td className="num">{vnd(t.da_nhan)}</td>
            <td className="num">{vnd(t.chi_ho_duyet)}</td><td className="num">{vnd(t.da_nop_lai)}</td>
            <td className="num"><b>{vnd(t.so_du)}</b></td>
            <td>{t.khong_bu_tru ? <Tag>không bù trừ</Tag>
               : t.cong_ty_no_lai ? <Tag cls="warn">công ty nợ lại</Tag> : null}</td></tr>)}</tbody></table>
        <p className="muted">Số dư âm = <b>công ty nợ lại</b> hướng dẫn viên. Kế toán xem xét trả;
          hệ thống không tự trả.</p></>}
    </div>}

    {/* ───── ĐỀ XUẤT (Đợt 4) ───── */}
    {tab === "dexuat" && <div className="panel">
      <h2>Đề xuất của phòng</h2>
      <p className="muted">Đường duyệt <b>không do màn hình đặt</b>: máy chủ tra bảng cấu hình đã ký rồi
        lập đủ các bước ngay lúc trình. <b>Chưa khai cấu hình thì bị chặn trình</b> — hệ thống không tự
        chọn cấp duyệt, vì đường nó tự chọn sẽ thành tiền lệ mà không ai ký.</p>

      {canCongBo && <p style={{ marginTop: 0 }}>
        <button className="act teal" style={{ margin: 0 }} onClick={congBoMotCap}>
          Công bố: một cấp — Chủ tịch hoặc TGĐ, mọi mức tiền</button>
        <span className="muted" style={{ marginLeft: 8 }}>
          Áp quyết định 06/10/2026 cho cả sáu loại hồ sơ, một khoảng từ 0 không trần.
          Chữ ký ghi tên người bấm. <b>Không đè</b> loại đã có đường đi.</span></p>}

      {canDieuPhoi && (fDx
        ? <div className="grid2" style={{ marginBottom: 12 }}>
            <label>Loại hồ sơ
              <select value={fDx.loai} onChange={(e) => setFDx({ ...fDx, loai: e.target.value })}>
                <option value="thue_ctv">Thuê HDV / cộng tác viên</option>
                <option value="thu_lao">Thù lao, phụ cấp, công tác phí</option>
                <option value="tam_ung">Tạm ứng / hoàn ứng</option>
                <option value="phat_sinh_tour">Phát sinh trong tour</option>
                <option value="dao_tao">Đào tạo, bổ sung nhân sự</option>
                <option value="doi_soat_ky">Đối soát thù lao kỳ</option>
              </select></label>
            <label>Số tiền <span className="muted">(để trống nếu hồ sơ không mang tiền)</span>
              <input value={fDx.so_tien || ""} inputMode="numeric"
                     onChange={(e) => setFDx({ ...fDx, so_tien: e.target.value })} /></label>
            <label style={{ gridColumn: "1 / -1" }}>Lý do <span className="muted">(bắt buộc)</span>
              <textarea value={fDx.ly_do || ""} onChange={(e) => setFDx({ ...fDx, ly_do: e.target.value })} /></label>
            <label style={{ gridColumn: "1 / -1" }}>Căn cứ tính
              <textarea value={fDx.can_cu_tinh || ""} onChange={(e) => setFDx({ ...fDx, can_cu_tinh: e.target.value })} /></label>
            <div style={{ gridColumn: "1 / -1" }}>
              <button className="act teal" disabled={luu} onClick={lapDeXuat}>Lưu nháp</button>{" "}
              <button className="act grey" onClick={() => setFDx(null)}>Thôi</button>
            </div>
          </div>
        : <button className="act teal" onClick={() => setFDx({ loai: "thu_lao" })}>Lập đề xuất</button>)}

      <div className="wrap"><table style={{ marginTop: 12 }}>
        <thead><tr><th>Mã</th><th>Loại</th><th className="num">Số tiền</th><th>Đường đi</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{dx.length ? dx.map((d: any) => <tr key={d.id}>
          <td><b>{d.ma}</b></td><td>{d.loai_ten}</td>
          <td className="num">{d.so_tien === null ? <span className="muted">—</span> : vnd(d.so_tien)}</td>
          <td>{d.duong_di.length
            ? d.duong_di.map((b: any) => <span key={b.thu_tu}>
                {b.thu_tu > 1 && " → "}
                <span style={{ fontWeight: b.thu_tu === d.cap_dang_cho ? 700 : 400,
                               color: b.trang_thai === "dong_y" ? "var(--teal)"
                                    : b.trang_thai === "tu_choi" ? "var(--red)" : undefined }}
                      title={b.vai_tro_ten}>{(b.cac_vai || [b.vai_tro]).join(" hoặc ")}</span>
              </span>)
            : <span className="muted">chưa trình</span>}</td>
          <td><Tag cls={d.trang_thai === "da_duyet" ? "ok" : d.trang_thai === "tu_choi" ? "red" : "warn"}>
            {d.trang_thai_ten}</Tag></td>
          <td>{canDieuPhoi && ["nhap", "can_bo_sung"].includes(d.trang_thai) &&
            <button className="act teal" style={{ margin: 0 }} onClick={() => trinhDeXuat(d)}>Trình</button>}</td>
        </tr>) : <tr><td colSpan={6} className="muted">Chưa có đề xuất nào.</td></tr>}</tbody></table></div>
    </div>}
  </>);
}

export default function Page() { return <Shell><HuongDan /></Shell>; }
