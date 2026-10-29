"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KS-10 (Chủ tịch duyệt 29/10/2026) — ĐƠN PHÒNG QUA OTA, đi theo đúng sáu bước Agoda Demand API.
 *  Màn của ĐIỀU HÀNH, không phải của khách: bảng đơn chưa có cột nào ghi người đặt, nên mở cho
 *  khách lúc này là để ai biết thẻ tham chiếu cũng đọc được đơn người khác.
 *
 *  Chưa có đường nối sang Agoda (địa chỉ Demand API nằm sau đăng nhập đối tác). Nên mỗi con số của
 *  nguồn vào bằng đúng một trong hai cửa: môi trường «Thử» máy sinh mã giả để chạy hết sáu bước;
 *  môi trường «Chạy thật» Điều hành DÁN sáu con số từ Agoda sang. Màn không tự nghĩ ra số nào — máy
 *  chủ cũng không. Và không có ô nào nhận số thẻ: Agoda tính tiền thẳng cho khách. */
const MT_TAG: Record<string, string> = { tat: "", thu: "warn", that: "ok" };
const TT_TAG: Record<string, string> = { moi: "", da_hoi_gia: "", cho_tra_cuu: "red", da_dat: "ok", da_huy: "warn", that_bai: "red" };
// Sáu ô mà NGUỒN trả về. Chữ tiếng Việt lấy từ máy chủ (tham_so.so_cua_nguon) — không chép tay,
// vì chép tay thì ngày máy chủ đổi tên ô, màn hình lệch mà không ai biết.
const VD: Record<string, string> = {
  ma_tim: "633141408144250000", ma_khoi: "aBc_123-xyz=", ma_khach_san: "7001",
  ma_phong: "9001", ma_goi_gia: "11001", gia_gom_thue: "2400000",
};

// KS-12 · ba cổng ngoài gửi được yêu cầu. Chép đúng ba giá trị của `TaiKhoanNgoai.loai`.
const CONG_TEN: Record<string, string> = {
  khach_hang: "Khách hàng", doi_tac: "Đối tác", co_dong: "Cổ đông",
};

/** KS-12 — Điều hành ĐỌC ĐƯỢC yêu cầu khách gửi, rồi chạy bước 1 trên CHÍNH đơn ấy.
 *  KS-11 đã mở cửa cho khách và đã có cửa máy chủ `/{id}/hoi-gia-yeu-cau`, nhưng màn này chưa
 *  gọi và chưa bày nội dung khách khai — nên đơn khách gửi lên nằm trong danh sách mà người
 *  trực không biết khách muốn đi đâu, cũng không có số để gọi lại. Vòng này nối nốt chỗ ấy.
 *
 *  KHÔNG dựng đơn mới: dựng đơn mới thì khách theo dõi một đơn, Điều hành chạy một đơn khác,
 *  và hai cái ấy không bao giờ gặp nhau. */
function YeuCauKhach({ d, ds, goi }: { d: any; ds: any; goi: (duong: string, json: any) => Promise<any> }) {
  const ota = (ds?.ota || [])[0];
  const mt = ota?.moi_truong || "tat";
  const that = mt === "that";
  const [f, setF] = useState<any>({
    ma_tim: "", ma_khoi: "", ma_khach_san: "", ma_phong: "", ma_goi_gia: "", gia_gom_thue: "",
    kieu_thanh_toan: "", the_chao: "", phu_thu: "", nuoc_khach: "VN", ngon_ngu: "vi-vn", tien_te: "VND",
  });
  const [ban, setBan] = useState(false);
  if (!d.la_yeu_cau_khach) return null;
  const nhan = async () => {
    setBan(true);
    const g: any = { ...f, ota_id: ota?.id };
    for (const k of Object.keys(ds?.so_cua_nguon || {})) if (g[k] === "") g[k] = null;
    await goi("hoi-gia-yeu-cau", g);
    setBan(false);
  };

  return (<div className="panel" style={{ margin: 0 }}>
    <b>Khách gửi yêu cầu</b>{" "}
    <Tag cls="warn">{CONG_TEN[d.cong] || d.cong || "cổng ngoài"}</Tag>{" "}
    <span className="muted mono">{(d.gui_luc || "").replace("T", " ").slice(0, 16)}</span>
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 8, marginTop: 6 }}>
      <div><div className="muted">Nơi đến</div><b>{d.noi_den || "—"}</b></div>
      <div><div className="muted">Ngày ở</div><b>{d.ngay_nhan || "—"} → {d.ngay_tra || "—"}</b></div>
      <div><div className="muted">Số khách</div><b>{d.so_phong} phòng · {d.nguoi_lon} người lớn{d.tre_em ? ` · ${d.tre_em} trẻ em` : ""}</b></div>
      <div><div className="muted">Người nhận phòng</div><b>{d.nguoi_nhan_phong || "—"}</b></div>
      <div><div className="muted">Liên hệ để báo giá</div><b className="mono">{d.lien_he || "—"}</b></div>
    </div>
    {d.yeu_cau_them && <div style={{ marginTop: 6 }}>
      <div className="muted">Yêu cầu thêm</div>{d.yeu_cau_them}</div>}

    {d.trang_thai === "moi" ? <div style={{ marginTop: 10 }}>
      <b>Nhận yêu cầu này và hỏi giá</b>{" "}<Tag cls={MT_TAG[mt] || ""}>{ota?.moi_truong_ten || mt}</Tag>
      <div className="muted">Bước 1 chạy trên CHÍNH đơn này, không dựng đơn mới — để khách và Điều hành cùng theo dõi một đơn.</div>
      {that && <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 8, marginTop: 6 }}>
        {Object.entries(ds?.so_cua_nguon || {}).map(([k, ten]) => <label key={k} style={{ display: "grid", gap: 4 }}>
          <span className="muted">{ten as string}</span>
          <input className="mono" value={f[k]} placeholder={VD[k] || ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>)}
      </div>}
      <div style={{ marginTop: 8 }}>
        <button className="act teal" style={{ margin: 0 }} disabled={ban || !ota || mt === "tat"} onClick={nhan}>Nhận và hỏi giá</button>{" "}
        <span className="muted">{mt === "tat"
          ? "Môi trường nguồn đang Tắt — bật Thử hoặc Chạy thật ở màn Khách sạn OTA trước."
          : "Xong bước này, khách thấy «Vietourist đang tra giá» trên cổng của họ."}</span>
      </div>
    </div> : <div className="muted" style={{ marginTop: 8 }}>Đã qua bước hỏi giá — xem sáu bước bên dưới.</div>}
  </div>);
}

function HoiGia({ ds, xong }: { ds: any; xong: (d: any) => void }) {
  const { toast } = useShell();
  const ota = (ds?.ota || [])[0];
  const mt = ota?.moi_truong || "tat";
  const that = mt === "that";
  const [f, setF] = useState<any>({
    ota_id: ota?.id || 0, ngay_nhan: "", ngay_tra: "", so_phong: 1, nguoi_lon: 2, tre_em: 0,
    nuoc_khach: "VN", ngon_ngu: "vi-vn", tien_te: "VND", ghi_chu: "",
    ma_tim: "", ma_khoi: "", ma_khach_san: "", ma_phong: "", ma_goi_gia: "", gia_gom_thue: "",
    kieu_thanh_toan: "", the_chao: "", phu_thu: "",
  });
  const [ban, setBan] = useState(false);
  const gui = async () => {
    setBan(true);
    const d: any = { ...f, ota_id: ota?.id };
    for (const k of Object.keys(ds?.so_cua_nguon || {})) if (d[k] === "") d[k] = null;
    try { const r = await api<any>("/don-khach-san-ota/hoi-gia", { method: "POST", json: d }); toast(r.message); xong(r); }
    catch (e) { toast(errMsg(e), true); } finally { setBan(false); }
  };
  const o = (k: string, nhan: string, kieu = "text") => <label style={{ display: "grid", gap: 4 }}>
    <span className="muted">{nhan}</span>
    <input type={kieu} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;

  return (<div className="panel">
    <b>Bước 1 · Hỏi giá <span className="muted">(Search)</span></b>{" "}
    <Tag cls={MT_TAG[mt] || ""}>{ota?.moi_truong_ten || mt}</Tag>
    <p className="muted">{that
      ? "Chạy thật: mở Agoda, tra phòng, rồi dán sáu con số của nguồn vào bên dưới. Thiếu ô nào máy gọi đúng tên ô ấy và dừng. Đơn này VÀO báo cáo tiền."
      : mt === "thu"
        ? "Thử: máy tự sinh mã giả để chạy hết sáu bước mà không cần Agoda. Đơn dựng ở đây KHÔNG BAO GIỜ vào báo cáo tiền."
        : "Môi trường nguồn đang Tắt — bật Thử hoặc Chạy thật ở màn Khách sạn OTA trước khi dựng đơn."}</p>
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 8 }}>
      {o("ngay_nhan", "Ngày nhận", "date")}
      {o("ngay_tra", "Ngày trả", "date")}
      {o("so_phong", "Số phòng", "number")}
      {o("nguoi_lon", "Người lớn", "number")}
      {o("tre_em", "Trẻ em", "number")}
      {o("nuoc_khach", "Nước khách")}
      {o("tien_te", "Tiền tệ")}
      {o("ngon_ngu", "Ngôn ngữ")}
    </div>
    {that && <div style={{ background: "var(--panel2)", borderRadius: 8, padding: "10px 12px", marginTop: 8 }}>
      <b>Sáu con số dán từ Agoda</b>
      <div className="muted">Máy không bịa một con số nào. Giá lấy ở <span className="mono">rate.inclusive</span> — tài liệu cấm dùng <span className="mono">totalPayment</span>.</div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 8, marginTop: 6 }}>
        {Object.entries(ds?.so_cua_nguon || {}).map(([k, ten]) => <label key={k} style={{ display: "grid", gap: 4 }}>
          <span className="muted">{ten as string}</span>
          <input className="mono" value={f[k]} placeholder={VD[k] || ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>)}
      </div>
    </div>}
    <div style={{ marginTop: 8 }}>
      <button className="act teal" style={{ margin: 0 }} disabled={ban || !ota || mt === "tat"} onClick={gui}>Dựng đơn và hỏi giá</button>{" "}
      <span className="muted">Máy cấp một thẻ tham chiếu cho đơn — đó là cách duy nhất tra lại một lần gọi quá hạn.</span>
    </div>
  </div>);
}

function MotDon({ id, ds, xong }: { id: number; ds: any; xong: (d: any) => void }) {
  const { toast } = useShell();
  const [ct, setCt] = useState<any>(null);
  const [huy, setHuy] = useState<any>(null);
  const tai = useCallback(() => { api<any>(`/don-khach-san-ota/${id}`).then(setCt).catch((e) => toast(errMsg(e), true)); }, [id, toast]);
  useEffect(() => { tai(); }, [tai]);
  const goi = async (duong: string, json: any, lai = true) => {
    try {
      const r = await api<any>(`/don-khach-san-ota/${id}/${duong}`, { method: "POST", json });
      toast(r.message || "Xong");
      if (duong === "xem-huy") setHuy(r);
      if (lai) { tai(); api<any>("/don-khach-san-ota").then(xong).catch(() => null); }
      return r;
    } catch (e) { toast(errMsg(e), true); return null; }
  };
  if (!ct) return <div className="muted">Đang tải…</div>;
  const d = ct.don;
  const dong = d.trang_thai === "da_huy" || d.trang_thai === "that_bai";

  return (<div style={{ background: "var(--panel2)", borderRadius: 8, padding: "10px 12px", display: "grid", gap: 10 }}>
    <YeuCauKhach d={d} ds={ds} goi={goi} />
    <div>
      <b>Sáu bước của đơn này</b>
      <div className="muted">Số đối chiếu: <span className="mono">{d.so_doi_chieu || "—"}</span> · {d.kieu_thanh_toan || "chưa rõ kiểu thanh toán"} · vào báo cáo tiền: {d.vao_bao_cao_tien ? "Có" : "Không"}</div>
    </div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      <button className="act grey" style={{ margin: 0 }} disabled={dong} onClick={() => goi("soat-truoc", {
        ngay_nhan: d.ngay_nhan, ngay_tra: d.ngay_tra, tien_te: d.tien_te })}>2 · Soát trước</button>
      <button className="act teal" style={{ margin: 0 }} disabled={dong || d.trang_thai === "cho_tra_cuu"} onClick={() => goi("dat", { qua_han: false })}>3 · Đặt</button>
      <button className="act orange" style={{ margin: 0 }} disabled={dong} onClick={() => goi("dat", { qua_han: true })}>3 · Ghi quá hạn</button>
      <button className="act grey" style={{ margin: 0 }} onClick={() => goi("trang-thai", { trang_thai_nguon: "" })}>4 · Tra đơn</button>
      <button className="act grey" style={{ margin: 0 }} disabled={dong} onClick={() => goi("xem-huy", {})}>5 · Xem huỷ</button>
    </div>
    {d.trang_thai === "cho_tra_cuu" && <div style={{ color: "var(--red)" }}>
      Đơn đang chờ tra cứu. Tài liệu Agoda cấm gửi lại ngay — phải tra Booking List bằng thẻ tham chiếu{" "}
      <span className="mono">{d.the_tham_chieu}</span> rồi ghi trạng thái nguồn ở bước 4. Bấm đặt lại cho chắc nghĩa là khách bị tính tiền hai lần.
    </div>}

    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 8 }}>
      <label style={{ display: "grid", gap: 4 }}><span className="muted">Trạng thái bên nguồn (chép từ Agoda)</span>
        <select defaultValue="" onChange={(e) => e.target.value && goi("trang-thai", { trang_thai_nguon: e.target.value })}>
          <option value="">— chọn —</option>
          {(ct.trang_thai_nguon || []).map((t: string) => <option key={t} value={t}>{t}</option>)}
        </select></label>
      <label style={{ display: "grid", gap: 4 }}><span className="muted">Số xác nhận khách sạn</span>
        <input className="mono" defaultValue={d.so_doi_chieu || ""} onBlur={(e) => goi("trang-thai", { so_xac_nhan_ks: e.target.value })} /></label>
    </div>

    {huy && <div className="panel" style={{ margin: 0 }}>
      <b>Bước 5–6 · Huỷ</b>
      {huy.thieu?.length ? <div style={{ color: "var(--red)" }}>Chưa huỷ được: {huy.thieu.join("; ")}</div>
        : <>
          <div className="muted">Ba con số phải khớp y nguyên bản xem trước. Lệch một cái là lỗi 914 — máy chặn trước khi gửi.</div>
          <label style={{ display: "grid", gap: 4, maxWidth: 420, marginTop: 6 }}><span className="muted">Lý do huỷ — bảng mã của nguồn</span>
            <select defaultValue="0" id="ks10-ly-do">
              {Object.entries(huy.ly_do_huy || {}).map(([k, v]) => <option key={k} value={k}>{k} · {v as string}</option>)}
            </select></label>
          <div className="muted" style={{ marginTop: 6 }}>Trong vòng 1 ngày trước ngày nhận thì huỷ qua API không còn được — phải có người báo nguồn.</div>
        </>}
    </div>}

    <div className="wrap">
      <b>Nhật ký từng bước</b>
      <div className="muted">Một dòng cho mỗi lần gọi, kể cả lần quá hạn. Không có sổ này thì câu «Agoda đã nhận đơn chưa» không có chỗ nào trả lời.</div>
      <table><thead><tr><th>Lúc</th><th>Bước</th><th>Mã</th><th>Tóm tắt</th><th>Bởi</th></tr></thead>
        <tbody>{ct.nhat_ky?.length ? ct.nhat_ky.map((n: any, i: number) => <tr key={i}>
          <td className="mono">{(n.luc || "").replace("T", " ").slice(0, 16)}</td>
          <td>{n.buoc_ten}</td>
          <td className="mono">{n.qua_han ? <Tag cls="red">quá hạn</Tag> : n.ma_tra_ve}</td>
          <td className="muted">{n.tom_tat}</td>
          <td className="muted">{n.boi || "—"}</td></tr>)
          : <tr><td colSpan={5} className="muted">Chưa có bước nào.</td></tr>}</tbody></table>
    </div>
  </div>);
}

function Trang() {
  const { toast } = useShell();
  const [ds, setDs] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const load = useCallback(() => { api<any>("/don-khach-san-ota").then(setDs).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);

  return (<>
    <h1>Đơn phòng OTA</h1>
    <p className="muted">Đặt phòng đi theo đúng sáu bước của Agoda Demand API. Vietourist KHÔNG thu tiền khách — Agoda tính tiền thẳng cho khách (Fulfill Assisted), nên màn này không có ô nào nhận số thẻ. Đơn ở môi trường Thử và đơn Agoda đánh dấu BookingTest không bao giờ vào báo cáo tiền. Đơn có dấu «Khách gửi» là yêu cầu từ cổng khách: mở ra để đọc nơi đến, liên hệ và yêu cầu thêm, rồi bấm «Nhận và hỏi giá» — bước 1 chạy trên chính đơn ấy.</p>

    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))" }}>
      {Object.entries(ds?.buoc || {}).map(([k, v], i) => <div className="panel" key={k}>
        <b>{i + 1} · {ds?.buoc_vi?.[k] || k}</b><div className="muted mono">{v as string}</div></div>)}
    </div>

    <HoiGia ds={ds} xong={(r) => setDs(r)} />

    <div className="panel wrap"><b>Đơn đang có</b>
      <table><thead><tr><th>Thẻ tham chiếu</th><th>Môi trường</th><th>Trạng thái bên mình</th><th>Trạng thái bên nguồn</th><th>Số đối chiếu</th><th>Nhận – Trả</th><th>Giá gồm thuế</th><th>Báo cáo tiền</th><th></th></tr></thead>
        <tbody>{ds?.don?.length ? ds.don.map((d: any) => <>
          <tr key={d.id}>
            <td style={{ overflowWrap: "anywhere" }}>
              <span className="mono">{d.the_tham_chieu}</span>
              {d.la_yeu_cau_khach && <div style={{ marginTop: 4 }}>
                <Tag cls="warn">Khách gửi</Tag>{" "}
                <span className="muted">{d.noi_den || "—"}</span></div>}</td>
            <td><Tag cls={MT_TAG[d.moi_truong] || ""}>{d.moi_truong}</Tag></td>
            <td><Tag cls={TT_TAG[d.trang_thai] || ""}>{d.trang_thai_ten}</Tag></td>
            <td className="mono muted">{d.trang_thai_nguon || "—"}</td>
            <td className="mono">{d.so_doi_chieu || "—"}</td>
            <td className="muted">{d.ngay_nhan || "—"} → {d.ngay_tra || "—"}</td>
            <td className="mono">{(d.gia_gom_thue || 0).toLocaleString("vi-VN")}</td>
            <td>{d.vao_bao_cao_tien ? <Tag cls="ok">Có</Tag> : <Tag cls="">Không</Tag>}</td>
            <td><button className="act grey" style={{ margin: 0 }} onClick={() => setMo(mo === d.id ? null : d.id)}>{mo === d.id ? "Đóng" : "Mở"}</button></td></tr>
          {mo === d.id && <tr key={String(d.id) + "ct"}><td colSpan={9}><MotDon id={d.id} ds={ds} xong={(r) => setDs(r)} /></td></tr>}
        </>) : <tr><td colSpan={9} className="muted">Chưa có đơn nào.</td></tr>}</tbody></table>
    </div>
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
