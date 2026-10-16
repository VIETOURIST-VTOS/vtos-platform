"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ThanhViec, { baoDaDoi, useDaDoi, type Viec } from "@/components/ThanhViec";

/** ĐỀ NGHỊ XE ĐANG CHỜ — tách khỏi /lenh-dieu-xe ngày 17/10/2026 (khối 1–5 của màn cũ, cùng hộp
 *  ghi lý do từ chối / huỷ).
 *
 *  Mắt đầu của chuỗi Chủ tịch đặc tả 11/10/2026:
 *    Điều hành ĐỀ NGHỊ  →  Giám đốc đội xe LẬP LỆNH  →  Tài xế NHẬN
 *
 *  Trước 17/10 đề nghị và lệnh nằm chung một trang, với lý do «tách ra là bắt Giám đốc đội xe mở hai
 *  trang để làm một việc». Lý do ấy vẫn được giữ bằng cách khác: «Lấy vào mẫu» mở thẳng màn lập lệnh
 *  ở tab mới, đã điền sẵn đề nghị — một cú bấm, không phải chép tay số khách sang trang thứ hai. */

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/lenh-dieu-xe">Lệnh điều xe</a> · Đề nghị xe</>;

function DeNghi() {
  const { toast } = useShell();
  const [busy, setBusy] = useState(false);
  const [dn, setDn] = useState<any>(null);            // danh sách đề nghị + số đếm theo trạng thái
  const [dnQ, setDnQ] = useState<any>(null);           // hai câu trả lời về quyền, LẤY TỪ MÁY CHỦ
  const [coQuyen, setCoQuyen] = useState(false);       // được lập lệnh không — máy chủ trả lời (toi_duoc_lap)
  const [goLyDo, setGoLyDo] = useState<any>(null);     // {id, viec:"tu_choi"|"huy"} đang đòi lý do
  const [lyDoGo, setLyDoGo] = useState("");
  /* DL-2 (13/10/2026) — SỐ KHÁCH SỐNG ĐẾN NGÀY ĐI. Chủ tịch: "số khách sẽ do nhân viên điều hành
     nhập tay và điều chỉnh đến ngày đi". */
  const [thieuGhe, setThieuGhe] = useState<any>(null);
  const [xacNhanLai, setXacNhanLai] = useState<any>(null);
  const [suaKhach, setSuaKhach] = useState<any>(null);   // {id, so_khach, so_xe_can, ly_do}
  const [lichSu, setLichSu] = useState<any[]>([]);
  const daDoi = useDaDoi();

  const load = useCallback(async () => {
    try { setDn(await api("/de-nghi-xe")); } catch (e) { toast(errMsg(e), true); }
    try { setDnQ(await api("/de-nghi-xe/meta")); } catch { /* thiếu meta thì ẩn nút, không đoán quyền */ }
    // Nút «Lấy vào mẫu» chỉ hiện cho người được lập lệnh. Câu ấy máy chủ trả trong `de-lap-lenh`
    // (tham số xe_nguoi_lap_lenh) — hỏi lại đúng chỗ ấy, không gõ lại tên người ở đây.
    const hn = new Date().toISOString().slice(0, 10);
    try { const r: any = await api(`/fleet/de-lap-lenh?tu=${hn}&den=${hn}`); setCoQuyen(!!r?.toi_duoc_lap); }
    catch { setCoQuyen(false); }
    // DL-2 — hai số đo, cùng khuôn với `lenh-khong-qua-de-nghi`: đếm được, hiện lên, về 0 thì thôi.
    try { setThieuGhe(await api("/de-nghi-xe/thieu-ghe")); } catch { /* chỉ là số đo */ }
    try { setXacNhanLai(await api("/de-nghi-xe/can-xac-nhan-lai")); } catch { /* chỉ là số đo */ }
  }, [toast]);
  useEffect(() => { load(); }, [load]);
  const napLai = async () => { await load(); daDoi.xong(); };

  /** Từ chối hoặc huỷ. Lý do BẮT BUỘC – đó chính là câu trả lời cho báo cáo đối chiếu tour/lượt xe
   *  tháng sau: vì sao chuyến này phải thuê xe ngoài. */
  const goDeNghi = async () => {
    if (!goLyDo || !lyDoGo.trim()) return;
    setBusy(true);
    try {
      const r = await api(`/de-nghi-xe/${goLyDo.id}/${goLyDo.viec === "tu_choi" ? "tu-choi" : "huy"}`,
        { method: "POST", json: { ly_do: lyDoGo.trim() } });
      toast(r?.message || "Đã ghi");
      baoDaDoi(`đề nghị #${goLyDo.id} vừa ${goLyDo.viec === "tu_choi" ? "bị từ chối" : "bị huỷ"}`);
      setGoLyDo(null); setLyDoGo(""); load();
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  const moSuaKhach = async (d: any) => {
    setSuaKhach({ id: d.id, so_khach: String(d.so_khach ?? ""), so_xe_can: String(d.so_xe_can ?? ""), ly_do: "" });
    try { const r: any = await api(`/de-nghi-xe/${d.id}/lich-su-so-khach`); setLichSu(r.rows || []); }
    catch { setLichSu([]); }
  };
  const luuSoKhach = async () => {
    if (!suaKhach) return;
    setBusy(true);
    try {
      const r: any = await api(`/de-nghi-xe/${suaKhach.id}/so-khach`, { method: "PUT", json: {
        so_khach: Number(suaKhach.so_khach), so_xe_can: Number(suaKhach.so_xe_can),
        ly_do: suaKhach.ly_do } });
      // Lời của máy chủ, in nguyên: nó đã nói đủ chỗ hay thiếu mấy chỗ. Gõ lại ở đây là dựng chỗ
      // cho hai câu khác nhau về cùng một con số.
      toast(r.message, !!(r.canh_bao_ghe && !r.canh_bao_ghe.du_cho));
      baoDaDoi(`số khách của đề nghị #${suaKhach.id} vừa đổi`);
      setSuaKhach(null); setLichSu([]); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };

  const viec: Viec[] = [
    { nhan: "‹ Lệnh đã lập", href: "/lenh-dieu-xe", len: true },
    ...(dnQ?.toi_duoc_de_nghi ? [{ nhan: "Điều hành đề nghị xe", href: "/lenh-dieu-xe/de-nghi/moi", chinh: true }] : []),
  ];
  const cho = (dn?.rows || []).filter((d: any) => d.trang_thai === "cho_lap_lenh");

  return (<>
    <h1>Đề nghị xe</h1>
    <ThanhViec viec={viec} duong={DUONG} daDoi={{ ...daDoi, napLai }} />

    {dn && <div className="panel wrap"><h2>Đề nghị xe đang chờ lập lệnh ({dn.dem?.cho_lap_lenh || 0})</h2>
      <p className="muted">Chuỗi Chủ tịch đặc tả 11/10/2026: <b>Điều hành đề nghị</b> → <b>Giám đốc đội xe lập lệnh</b> → <b>tài xế nhận</b>. Bấm <b>Lấy vào mẫu</b> thì màn lập lệnh mở ở tab mới với ngày, số khách, km và chuyến đã điền sẵn, và lệnh chốt sau đó mang theo số đề nghị — để tháng sau còn truy được ai hỏi xe cho chuyến này.</p>
      <table><thead><tr><th>#</th><th>Chuyến</th><th>Từ → đến</th><th>Khách</th><th>Km</th><th>Xe cần</th><th>Yêu cầu</th><th>Người đề nghị</th><th>Việc</th></tr></thead>
        <tbody>{cho.length
          ? cho.map((d: any) => <tr key={d.id}>
            <td>{d.id}</td><td>{d.ma_tour} · {d.ten_tour}</td>
            <td>{fmtD(d.ngay_di)} → {fmtD(d.ngay_ve)} <span className="muted">({d.so_ngay} ngày)</span></td>
            <td className="num">{d.so_khach}</td><td className="num">{d.km_du_kien || ""}</td>
            <td className="num">{d.so_xe_can}</td><td>{d.yeu_cau}</td>
            <td>{d.nguoi_de_nghi} <span className="muted">{fmtDT(d.luc)}</span></td>
            <td>
              {coQuyen && <><a className="act teal" style={{ margin: 0 }} target="_blank" rel="noopener"
                href={`/lenh-dieu-xe/lap-lenh?de_nghi=${d.id}`} title="Mở màn lập lệnh trong tab mới">Lấy vào mẫu ↗</a>{" "}</>}
              {/* Hiện nút nào do MÁY CHỦ trả lời (meta.toi_duoc_*), không gõ lại danh sách vai ở đây:
                  gõ lại thì ngày nào bảng vai đổi, người ĐƯỢC phép lại không thấy nút — và cái không
                  thấy thì không ai báo lỗi. */}
              {dnQ?.toi_duoc_tu_choi && <><button className="act orange" style={{ margin: 0 }} disabled={busy}
                onClick={() => { setGoLyDo({ id: d.id, viec: "tu_choi" }); setLyDoGo(""); }}>Không còn xe</button>{" "}</>}
              {dnQ?.toi_duoc_de_nghi && <><button className="act grey" style={{ margin: 0 }} disabled={busy}
                onClick={() => { setGoLyDo({ id: d.id, viec: "huy" }); setLyDoGo(""); }}>Huỷ đề nghị</button>{" "}</>}
              {/* DL-2 — sửa được đến HẾT ngày đi, kể cả sau khi đã lập lệnh. Khoá lại sau khi lập
                  lệnh là đẩy Điều hành về đúng hai lối cũ: huỷ cả đề nghị, hoặc im lặng. */}
              {dnQ?.toi_duoc_de_nghi && <button className="act" style={{ margin: 0 }} disabled={busy}
                onClick={() => moSuaKhach(d)}>Sửa số khách</button>}
            </td>
          </tr>) : <tr><td colSpan={9} className="muted">Không có đề nghị nào đang chờ. Điều hành gửi đề nghị bằng nút <b>Điều hành đề nghị xe</b> trên thanh việc, sau khi dự toán chuyến được duyệt.</td></tr>}</tbody></table>
      {dn.dem && (dn.dem.tu_choi > 0 || dn.dem.huy > 0) &&
        <p className="muted">Đã từ chối {dn.dem.tu_choi || 0} · đã huỷ {dn.dem.huy || 0} · đã lập lệnh {dn.dem.da_lap_lenh || 0}.</p>}
    </div>}

    {goLyDo && <div className="panel"><h2>{goLyDo.viec === "tu_choi" ? "Vì sao đội xe không nhận đề nghị này" : "Vì sao huỷ đề nghị này"}</h2>
      <p className="muted">{goLyDo.viec === "tu_choi"
        ? <>Lý do này là câu trả lời cho báo cáo đối chiếu tour/lượt xe tháng sau: <b>vì sao chuyến ấy phải thuê xe ngoài</b>. Không ghi lý do thì tháng sau không ai trả lời được.</>
        : <>Khách huỷ, dời ngày, hay ghép chuyến — ghi lại để Điều hành không gửi lại đề nghị đã bỏ.</>}</p>
      <div><label>Lý do</label><textarea rows={2} value={lyDoGo} onChange={(e) => setLyDoGo(e.target.value)}
        placeholder={goLyDo.viec === "tu_choi" ? "Ví dụ: cả 11 xe nhà đều có lệnh trong khoảng ngày đó" : "Ví dụ: khách dời sang tuần sau"} /></div>
      <button className="act orange" disabled={busy || !lyDoGo.trim()} onClick={goDeNghi}>
        {goLyDo.viec === "tu_choi" ? "Ghi từ chối" : "Ghi huỷ"}</button>{" "}
      <button className="act grey" onClick={() => { setGoLyDo(null); setLyDoGo(""); }}>Bỏ</button>
    </div>}

    {/* ── DL-2 · Ô SỬA SỐ KHÁCH, và số cũ không mất ───────────────────────────────────────── */}
    {suaKhach && <div className="panel"><h2>Sửa số khách · đề nghị #{suaKhach.id}</h2>
      <p className="muted">Số khách <b>sống đến ngày đi</b> — Chủ tịch chốt 13/10/2026. Sửa xong máy
        soát lại ngay với tổng ghế của các xe <b>đã điều</b>. <b>Máy không tự thêm xe</b>: thêm xe là
        việc của Giám đốc đội xe, máy chỉ không để chuyện thiếu chỗ đi qua im lặng.</p>
      <div className="grid2">
        <label>Số khách<input type="number" value={suaKhach.so_khach}
          onChange={(e) => setSuaKhach({ ...suaKhach, so_khach: e.target.value })} /></label>
        <label>Số xe cần<input type="number" value={suaKhach.so_xe_can}
          onChange={(e) => setSuaKhach({ ...suaKhach, so_xe_can: e.target.value })} /></label>
        <label>Lý do đổi<input value={suaKhach.ly_do} placeholder="khách báo thêm / huỷ bớt / ghép đoàn"
          onChange={(e) => setSuaKhach({ ...suaKhach, ly_do: e.target.value })} /></label>
        <div />
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
        <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={luuSoKhach}>Lưu số khách</button>
        <button className="act grey" style={{ margin: 0 }} disabled={busy}
          onClick={() => { setSuaKhach(null); setLichSu([]); }}>Thôi</button>
      </div>
      {lichSu.length > 0 && <>
        <h3>Số cũ không mất</h3>
        <p className="muted">Khi một đoàn thiếu chỗ ở bãi xe, câu hỏi đầu tiên là <i>lúc lập lệnh thì
          đề nghị ghi bao nhiêu khách</i>. Ghi đè thì câu ấy không có câu trả lời.</p>
        <table><thead><tr><th>Lúc</th><th>Ai sửa</th><th className="num">Khách</th>
          <th className="num">Xe cần</th><th>Lý do</th></tr></thead>
          <tbody>{lichSu.map((x: any, i: number) => <tr key={i}>
            <td>{fmtDT(x.luc)}</td><td>{x.boi}</td>
            <td className="num">{x.so_khach_cu} → <b>{x.so_khach_moi}</b></td>
            <td className="num">{x.so_xe_can_cu} → {x.so_xe_can_moi}</td>
            <td className="muted">{x.ly_do}</td></tr>)}</tbody></table>
      </>}
    </div>}

    {/* ── DL-2 · ĐOÀN THIẾU CHỖ ───────────────────────────────────────────────────────────── */}
    {thieuGhe && thieuGhe.so > 0 && <div className="panel wrap" style={{ borderColor: "var(--red)" }}>
      <h2>Đoàn thiếu chỗ <Tag cls="red">{thieuGhe.so}</Tag></h2>
      <p className="muted">Số khách đã vượt tổng ghế của các xe đã điều. Chỉ đếm đề nghị <b>đã có
        lệnh</b> — chưa có lệnh thì chưa tới lượt soát.</p>
      <table><thead><tr><th>Ngày đi</th><th>Chuyến</th><th className="num">Khách</th>
        <th className="num">Ghế đã điều</th><th>Xe</th><th></th></tr></thead>
        <tbody>{thieuGhe.rows.map((r: any) => <tr key={r.de_nghi}>
          <td>{fmtD(r.ngay_di)}</td><td>{r.tour} · {r.ten_tour}</td>
          <td className="num">{r.so_khach}</td><td className="num">{r.tong_ghe}</td>
          <td className="muted">{r.xe.map((x: any) => `${x.bien_so} (${x.so_cho})`).join(" · ")}</td>
          <td><Tag cls="red">thiếu {r.thieu_ghe}</Tag></td></tr>)}</tbody></table>
    </div>}

    {/* ── DL-2 · CẦN XÁC NHẬN LẠI ─────────────────────────────────────────────────────────── */}
    {xacNhanLai && xacNhanLai.so > 0 && <div className="panel wrap">
      <h2>Cần xác nhận lại số khách <Tag cls="warn">{xacNhanLai.so}</Tag></h2>
      <p className="muted">Khởi hành trong <b>{xacNhanLai.gio} giờ</b> mà số khách <b>chưa ai đụng
        vào</b> kể từ lúc lập đề nghị. Không phải sai — máy không biết đúng hay sai. Chỉ là chưa ai
        xác nhận lại, trong khi con số này còn đổi đến ngày đi.</p>
      <table><thead><tr><th>Ngày đi</th><th>Chuyến</th><th className="num">Khách</th>
        <th className="num">Xe cần</th><th>Khai lúc</th><th>Người đề nghị</th></tr></thead>
        <tbody>{xacNhanLai.rows.map((r: any) => <tr key={r.de_nghi}>
          <td>{fmtD(r.ngay_di)}</td><td>{r.tour} · {r.ten_tour}</td>
          <td className="num">{r.so_khach}</td><td className="num">{r.so_xe_can}</td>
          <td className="muted">{fmtDT(r.lap_luc)}</td><td>{r.nguoi_de_nghi}</td></tr>)}</tbody></table>
    </div>}
  </>);
}

export default function Page() { return <Shell><DeNghi /></Shell>; }
