"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Phòng Hướng dẫn – màn hình của người điều phối, khi toàn bộ HDV là cộng tác viên.
 *
 *  Chữ dùng ở đây là "chào chuyến", không phải "phân công". Không phải chuyện chữ nghĩa: luật xét NỘI
 *  DUNG quan hệ chứ không xét tên hợp đồng, và màn hình này cùng dữ liệu của nó chính là nơi lưu bằng
 *  chứng về nội dung đó. Hạn 24 giờ vẫn còn, nhưng là hạn hiệu lực của LỜI CHÀO – quá hạn thì chuyến
 *  chào người khác, không phải hướng dẫn viên vi phạm. */
const TABS: [string, string][] = [["viec", "Việc cần làm"], ["hdv", "Đội ngũ HDV"], ["chao", "Chào chuyến"]];

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
  const canDieuPhoi = ["tp_hd", "tp_dh", "nv_dh", "hcns", "cntt"].includes(user?.role || "");

  const load = useCallback(async () => {
    try {
      setTq(await api("/huong-dan/tong-quan"));
      setHdv(await api("/huong-dan/hdv"));
      setCan(await api("/huong-dan/chuyen-can-hdv"));
      setChao(await api("/huong-dan/chao-chuyen"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const chaoChuyen = async () => {
    setLuu(true);
    try {
      const d = await api<any>("/huong-dan/chao-chuyen", { method: "POST", json: {
        tour_id: Number(form.tour_id), guide_id: Number(form.guide_id), days: Number(form.days) || 1,
        rate_per_day: Number(form.rate_per_day) || 0, holiday: !!form.holiday } });
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
  </>);
}

export default function Page() { return <Shell><HuongDan /></Shell>; }
