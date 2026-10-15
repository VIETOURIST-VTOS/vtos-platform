"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Lệnh điều xe – Đợt 4.
 *
 *  Màn hình này gợi ý, không quyết. Đặc tả đặt ranh giới rõ: "Không để quyết định cho xe xuất bến phụ thuộc
 *  vào kết luận của mô hình ngôn ngữ." Nên phần lọc và xếp hạng là mã xác định, còn người chốt lệnh vẫn là
 *  người quyết — và nếu chọn khác gợi ý thì phải ghi lý do. */
function LenhDieuXe() {
  const { toast } = useShell();
  const [tu, setTu] = useState(new Date().toISOString().slice(0, 10));
  const [den, setDen] = useState(new Date().toISOString().slice(0, 10));
  const [khach, setKhach] = useState(0);
  const [km, setKm] = useState(0);
  const [gy, setGy] = useState<any>(null);
  const [dm, setDm] = useState<any>(null);           // danh mục: tên của từng mức kiểm tra
  const [ds, setDs] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  // Mẫu chốt lệnh. Trước 09/9/2026 màn hình này chỉ XEM: có bảng gợi ý, có bảng lệnh đã lập, không có
  // nút chốt. Mẫu lập lệnh duy nhất nằm ở /ops?tab=fleet – mà menu của gd_doi_xe không có /ops, trong
  // khi tham số xe_nguoi_lap_lenh lại chỉ định chính ông là người DUY NHẤT được chốt lệnh. Kết quả:
  // người được phép thì không thấy mẫu, người thấy mẫu thì không được phép.
  const [nen, setNen] = useState<any>(null);          // tour & bảng giá để lập lệnh
  const [chon, setChon] = useState<any>(null);        // phương án đang chốt
  const [tour, setTour] = useState("");
  const [rate, setRate] = useState("");
  const [lyDo, setLyDo] = useState("");
  const [hoi, setHoi] = useState<any>(null);          // máy chủ đòi lý do: giữ nhận xét của máy để người ký đọc

  // ĐỀ NGHỊ XE – mắt đầu của chuỗi Chủ tịch đặc tả 11/10/2026:
  //   Điều hành ĐỀ NGHỊ  →  Giám đốc đội xe LẬP LỆNH  →  Tài xế NHẬN
  // Đặt cùng màn hình này chứ không dựng trang thứ hai: đề nghị và lệnh là hai mặt của một việc,
  // tách ra là bắt Giám đốc đội xe mở hai trang để làm một việc.
  const [dn, setDn] = useState<any>(null);            // danh sách đề nghị + số đếm theo trạng thái
  const [dnQ, setDnQ] = useState<any>(null);           // hai câu trả lời về quyền, LẤY TỪ MÁY CHỦ
  const [dnChon, setDnChon] = useState<any>(null);     // đề nghị đang lập lệnh cho – đi kèm lệnh
  const [ho, setHo] = useState<any>(null);             // đếm lệnh lập KHÔNG qua cửa đề nghị
  // DL-1b: mắt thứ ba. Quá hạn chưa nhận và tài xế báo không nhận được gộp vào MỘT cửa —
  // với Giám đốc đội xe cả hai là một việc: "chuyến này chưa chắc có người lái".
  const [nhan, setNhan] = useState<any>(null);
  const [tourDN, setTourDN] = useState<any[]>([]);     // chuyến ĐỀ NGHỊ ĐƯỢC (đã duyệt dự toán)
  const [dnTour, setDnTour] = useState("");
  const [dnKhach, setDnKhach] = useState(0);
  const [dnKm, setDnKm] = useState(0);
  const [dnSoXe, setDnSoXe] = useState(1);
  const [dnYeuCau, setDnYeuCau] = useState("");
  const [goLyDo, setGoLyDo] = useState<any>(null);     // {id, viec:"tu_choi"|"huy"} đang đòi lý do
  const [lyDoGo, setLyDoGo] = useState("");
  /* DL-2 (13/10/2026) — SỐ KHÁCH SỐNG ĐẾN NGÀY ĐI. Chủ tịch: "số khách sẽ do nhân viên điều hành
     nhập tay và điều chỉnh đến ngày đi". Trước vòng này cửa đề nghị chỉ có tạo/từ chối/huỷ, nên
     con số Giám đốc đội xe dùng để quyết điều mấy chiếc là con số của NGÀY LẬP ĐỀ NGHỊ. */
  const [thieuGhe, setThieuGhe] = useState<any>(null);
  const [xacNhanLai, setXacNhanLai] = useState<any>(null);
  const [suaKhach, setSuaKhach] = useState<any>(null);   // {id, so_khach, so_xe_can, ly_do}
  const [lichSu, setLichSu] = useState<any[]>([]);
  const [chuoi, setChuoi] = useState<any>(null);   // DL-3: hai số đo chỗ lệnh và chuyến chưa gặp nhau

  const load = useCallback(async () => {
    try { setDs(await api("/fleet/lenh-dieu-xe")); } catch (e) { toast(errMsg(e), true); }
    // Tên của từng mức kiểm tra lấy từ máy chủ (MUC_TEN), để màn hình không gõ lại thang mức.
    try { setDm(await api("/fleet/danh-muc")); } catch { /* thiếu danh mục thì in mã mức, vẫn đúng */ }
    try { setDn(await api("/de-nghi-xe")); } catch (e) { toast(errMsg(e), true); }
    try { setDnQ(await api("/de-nghi-xe/meta")); } catch { /* thiếu meta thì ẩn nút, không đoán quyền */ }
    try { setHo(await api("/de-nghi-xe/lenh-khong-qua-de-nghi")); } catch { /* chỉ là số đo */ }
    try { setNhan(await api("/nhan-lenh/can-biet")); } catch { /* thiếu thì ẩn khối, không đoán */ }
    // DL-2 — hai số đo, cùng khuôn với `lenh-khong-qua-de-nghi`: đếm được, hiện lên, về 0 thì thôi.
    try { setThieuGhe(await api("/de-nghi-xe/thieu-ghe")); } catch { /* chỉ là số đo */ }
    try { setXacNhanLai(await api("/de-nghi-xe/can-xac-nhan-lai")); } catch { /* chỉ là số đo */ }
    // DL-3 — hai số đo chỗ chuỗi chưa liền giữa LỆNH và CHUYẾN. Cùng khuôn: đếm, không chặn.
    try { setChuoi(await api("/dispatch/chuoi-lenh-chuyen")); } catch { /* chỉ là số đo */ }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  // Nạp danh sách tour NGAY KHI MỞ TRANG, và mỗi lần đổi khoảng ngày.
  //
  // Bản đầu (09/9/2026) chỉ nạp khi bấm "Xem phương án", vì mẫu chốt lệnh dùng chung khoảng ngày với
  // bảng gợi ý. Soi trên web thật thì thấy hậu quả đúng bằng chỗ hỏng bản này sinh ra để chữa: người
  // phụ trách mở trang lên, chỉ thấy ô tìm ngày và bảng lệnh cũ, rồi kết luận màn hình này chỉ để xem.
  // Một cái cửa chỉ hiện ra sau khi người ta đoán đúng phải bấm nút nào thì cũng gần bằng không có cửa.
  const nenRef = useCallback(async (a: string, b: string) => {
    try { setNen(await api(`/fleet/de-lap-lenh?tu=${a}&den=${b}`)); }
    catch (e) { toast(errMsg(e), true); }
    // Danh sách cho mẫu đề nghị đi đường RIÊNG, vì nó phải lọc theo dự toán đã duyệt. Dùng lại
    // `nen.tour` thì mẫu bày ra chuyến chưa duyệt, người điều hành bấm gửi và nhận một câu 422.
    try { setTourDN(await api(`/de-nghi-xe/tour-cho-de-nghi?tu=${a}&den=${b}`)); }
    catch { setTourDN([]); }
  }, [toast]);
  useEffect(() => { if (tu && den && den >= tu) nenRef(tu, den); }, [tu, den, nenRef]);

  const chay = async () => {
    setBusy(true);
    try {
      setGy(await api(`/fleet/goi-y-dieu-xe?date_from=${tu}&date_to=${den}&so_khach=${khach}&km_du_kien=${km}`));
      setChon(null); setHoi(null); setLyDo("");
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  /** Chốt lệnh. Gọi thẳng fetch chứ không qua api() vì một lý do cụ thể:
   *
   *  Khi xe được chọn có điểm THẤP HƠN nhóm đề xuất, máy chủ trả 422 kèm cả nhận xét của mình –
   *  "he_thong_nhan_xet" – tức là nó chê xe này ở điểm gì. api() rút gọn lỗi còn mỗi câu message, nên
   *  người chốt lệnh sẽ chỉ đọc được "phải ghi lý do" mà không biết mình đang bác lại nhận xét nào.
   *  Một ô lý do không biết đang trả lời câu gì thì sẽ được điền cho xong, và ít lâu sau tính năng bị tắt. */
  const chot = async (p: any, lyDoGui: string) => {
    if (!tour) { toast("Chọn tour trước khi chốt lệnh", true); return; }
    setBusy(true);
    try {
      const r = await fetch("/api/v1/dispatch", { method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken() || ""}` },
        body: JSON.stringify({ tour_id: Number(tour), vehicle_id: p.vehicle_id, date_from: tu, date_to: den,
          rate_id: rate ? Number(rate) : null, so_khach: khach, km_du_kien: km,
          de_nghi_id: dnChon ? dnChon.id : null,
          ly_do_khac_goi_y: lyDoGui.trim() }) });
      const d = await r.json().catch(() => null);
      if (r.ok) {
        toast(d?.message || "Đã lập lệnh"); setHoi(null); setLyDo(""); setChon(null);
        setDnChon(null); load();
      } else if (r.status === 422 && d?.detail?.he_thong_nhan_xet !== undefined) {
        setChon(p); setHoi(d.detail);       // giữ nguyên mẫu, mở ô lý do kèm nhận xét của máy
      } else {
        toast(typeof d?.detail === "string" ? d.detail : d?.detail?.message || `Lỗi ${r.status}`, true);
      }
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  /** Điều hành gửi đề nghị. KHÔNG chọn xe ở đây – chọn xe là việc của Giám đốc đội xe. */
  const guiDeNghi = async () => {
    if (!dnTour) { toast("Chọn chuyến cần xe", true); return; }
    setBusy(true);
    try {
      const r = await api("/de-nghi-xe", { method: "POST", json: {
        tour_id: Number(dnTour), so_khach: dnKhach, km_du_kien: dnKm, so_xe_can: dnSoXe,
        yeu_cau: dnYeuCau.trim() } });
      toast(r?.message || "Đã gửi đề nghị"); setDnYeuCau(""); load();
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  /** Từ chối hoặc huỷ. Lý do BẮT BUỘC – đó chính là câu trả lời cho báo cáo đối chiếu tour/lượt xe
   *  tháng sau: vì sao chuyến này phải thuê xe ngoài. */
  const goDeNghi = async () => {
    if (!goLyDo || !lyDoGo.trim()) return;
    setBusy(true);
    try {
      const r = await api(`/de-nghi-xe/${goLyDo.id}/${goLyDo.viec === "tu_choi" ? "tu-choi" : "huy"}`,
        { method: "POST", json: { ly_do: lyDoGo.trim() } });
      toast(r?.message || "Đã ghi"); setGoLyDo(null); setLyDoGo(""); load();
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  /** Lấy một đề nghị vào mẫu lập lệnh: điền sẵn ngày, số khách, km, chuyến – rồi tính phương án.
   *  Lệnh chốt sau đó mang `de_nghi_id`, nên chuỗi ba mắt nối liền chứ không đứt ở giữa. */
  const layVaoMau = async (d: any) => {
    setDnChon(d); setTu(d.ngay_di); setDen(d.ngay_ve); setKhach(d.so_khach); setKm(d.km_du_kien);
    setTour(String(d.tour_id)); setGy(null); setChon(null); setHoi(null); setLyDo("");
    setBusy(true);
    try {
      setGy(await api(`/fleet/goi-y-dieu-xe?date_from=${d.ngay_di}&date_to=${d.ngay_ve}` +
                      `&so_khach=${d.so_khach}&km_du_kien=${d.km_du_kien}`));
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  const matTour = nen?.tour?.find((t: any) => String(t.id) === tour);
  const coQuyen = nen ? nen.toi_duoc_lap : false;

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
      setSuaKhach(null); setLichSu([]); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };

  return (<>
    <h1>Lệnh điều xe</h1>
    <p className="muted">Đây là nơi <b>lập và chốt lệnh điều xe</b>: chọn tour bên dưới, đặt khoảng ngày và số khách, xem phương án, rồi bấm <b>Chốt lệnh</b> ngay trên dòng xe đã chọn.</p>
    <p className="muted">Hệ thống <b>lọc cứng trước, xếp hạng sau</b>: xe vi phạm điều kiện không xuất hiện trong gợi ý dù điểm có cao đến đâu. Đây là gợi ý — người chốt lệnh vẫn quyết, và chọn khác gợi ý thì phải ghi lý do.</p>

    {dn && <div className="panel wrap"><h2>Đề nghị xe đang chờ lập lệnh ({dn.dem?.cho_lap_lenh || 0})</h2>
      <p className="muted">Chuỗi Chủ tịch đặc tả 11/10/2026: <b>Điều hành đề nghị</b> → <b>Giám đốc đội xe lập lệnh</b> → <b>tài xế nhận</b>. Bấm <b>Lấy vào mẫu</b> thì ngày, số khách, km và chuyến được điền sẵn xuống dưới, và lệnh chốt sau đó mang theo số đề nghị — để tháng sau còn truy được ai hỏi xe cho chuyến này.</p>
      <table><thead><tr><th>#</th><th>Chuyến</th><th>Từ → đến</th><th>Khách</th><th>Km</th><th>Xe cần</th><th>Yêu cầu</th><th>Người đề nghị</th><th>Việc</th></tr></thead>
        <tbody>{(dn.rows || []).filter((d: any) => d.trang_thai === "cho_lap_lenh").length
          ? dn.rows.filter((d: any) => d.trang_thai === "cho_lap_lenh").map((d: any) => <tr key={d.id}>
            <td>{d.id}</td><td>{d.ma_tour} · {d.ten_tour}</td>
            <td>{fmtD(d.ngay_di)} → {fmtD(d.ngay_ve)} <span className="muted">({d.so_ngay} ngày)</span></td>
            <td className="num">{d.so_khach}</td><td className="num">{d.km_du_kien || ""}</td>
            <td className="num">{d.so_xe_can}</td><td>{d.yeu_cau}</td>
            <td>{d.nguoi_de_nghi} <span className="muted">{fmtDT(d.luc)}</span></td>
            <td>
              {coQuyen && <><button className="act teal" style={{ margin: 0 }} disabled={busy}
                onClick={() => layVaoMau(d)}>Lấy vào mẫu</button>{" "}</>}
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
          </tr>) : <tr><td colSpan={9} className="muted">Không có đề nghị nào đang chờ. Điều hành gửi đề nghị ở khối dưới sau khi dự toán chuyến được duyệt.</td></tr>}</tbody></table>
      {dnChon && <p className="muted"><Tag cls="ok">đang lập lệnh</Tag> Mẫu dưới đang lập lệnh cho đề nghị <b>#{dnChon.id}</b> – chuyến {dnChon.ma_tour}, {dnChon.so_khach} khách, cần {dnChon.so_xe_can} xe.{" "}
        <button className="act grey" style={{ margin: 0 }} onClick={() => setDnChon(null)}>Bỏ liên kết</button></p>}
      {dn.dem && (dn.dem.tu_choi > 0 || dn.dem.huy > 0) &&
        <p className="muted">Đã từ chối {dn.dem.tu_choi || 0} · đã huỷ {dn.dem.huy || 0} · đã lập lệnh {dn.dem.da_lap_lenh || 0}. Lý do từ chối xem ở bảng cuối trang.</p>}
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

    {dnQ?.toi_duoc_de_nghi && <div className="panel"><h2>Điều hành đề nghị xe</h2>
      <p className="muted">Chỉ chuyến <b>đã duyệt dự toán</b> mới hiện ở đây — chi phí xe nằm trong dự toán ấy, nên không cần thêm chữ ký nào nữa (Chủ tịch quyết 11/10/2026). Đổi khoảng ngày ở khối trên thì danh sách này đổi theo.</p>
      <div className="grid">
        <div><label>Chuyến cần xe</label>
          <select value={dnTour} onChange={(e) => {
            setDnTour(e.target.value);
            const t = tourDN.find((x: any) => String(x.id) === e.target.value);
            if (t?.planned_pax) setDnKhach(t.planned_pax);   // số khách dự kiến của chuyến, sửa được
          }}>
            <option value="">– chọn chuyến –</option>
            {tourDN.map((t: any) => <option key={t.id} value={t.id}>
              {t.code} · {t.name} · {fmtD(t.start_date)}→{fmtD(t.end_date)}{t.planned_pax ? ` · ${t.planned_pax} khách` : ""}{t.da_co_de_nghi ? ` · đã có ${t.da_co_de_nghi} đề nghị` : ""}
            </option>)}
          </select></div>
        <div><label>Số khách</label><input type="number" value={dnKhach} onChange={(e) => setDnKhach(Number(e.target.value))} /></div>
        <div><label>Km dự kiến (gồm chạy rỗng)</label><input type="number" value={dnKm} onChange={(e) => setDnKm(Number(e.target.value))} /></div>
        <div><label>Số xe cần</label><input type="number" min={1} value={dnSoXe} onChange={(e) => setDnSoXe(Number(e.target.value))} /></div>
      </div>
      <div><label>Yêu cầu riêng (nếu có)</label><textarea rows={2} value={dnYeuCau} onChange={(e) => setDnYeuCau(e.target.value)}
        placeholder="Ví dụ: khách yêu cầu xe đời 2022 trở lên; cần xe có khoang hành lý rộng" /></div>
      <p className="muted">Đề nghị <b>không chọn xe</b>: chọn xe là việc của Giám đốc đội xe, vì chỉ người có xe mới biết xe nào rảnh ngày ấy.</p>
      {!tourDN.length && <p className="muted"><Tag cls="warn">chưa có chuyến</Tag> Không có chuyến nào đã duyệt dự toán trong khoảng ngày này. Đổi khoảng ngày, hoặc chờ dự toán được duyệt.</p>}
      <button className="act teal" disabled={busy || !dnTour || dnKhach <= 0} onClick={guiDeNghi}>
        {busy ? "Đang gửi…" : "Gửi đề nghị xe"}</button>
      {dnTour && dnKhach <= 0 && <p className="muted">Phải ghi số khách — bộ gợi ý điều xe lọc theo số ghế, thiếu số khách thì nó đề xuất một chiếc 29 chỗ cho đoàn 40 người.</p>}
    </div>}

    {/* DL-1b — KHỐI CHỈ HIỆN KHI CÓ VIỆC. Hết việc thì nó biến mất, không để lại một bảng rỗng
        mà người ta phải cuộn qua mỗi ngày. */}
    {nhan && (nhan.dem?.qua_han > 0 || nhan.dem?.tu_choi > 0) &&
      <div className="panel wrap"><h2>Lệnh tài xế chưa nhận ({(nhan.dem.qua_han || 0) + (nhan.dem.tu_choi || 0)})</h2>
        <p className="muted">{nhan.ghi_chu}</p>
        <table><thead><tr><th>Chuyến</th><th>Xe · tài xế</th><th>Tình hình</th></tr></thead>
          <tbody>{[...(nhan.tu_choi || []), ...(nhan.qua_han || [])].map((r: any) => <tr key={r.id}>
            <td><b>#{r.id}</b><div className="muted">đi {fmtD(r.ngay_di)}</div></td>
            <td>{r.xe}<div className="muted">{r.tai_xe}</div></td>
            <td>{r.trang_thai_nhan === "tu_choi"
              ? <><Tag cls="red">báo không nhận được</Tag><div className="muted">{r.tu_choi_nhan_ly_do}</div></>
              : <><Tag cls="warn">quá hạn, chưa bấm</Tag><div className="muted">hạn {fmtDT(r.han_nhan)}</div></>}</td>
          </tr>)}</tbody></table>
        <p className="muted">Đã nhận: {nhan.dem.da_nhan} / {nhan.dem.dang_cho} lệnh còn hiệu lực — con số này để đọc con số ở trên: 2 trên 13 là chuyện thường, 2 trên 3 là đội xe đang có vấn đề.</p>
      </div>}

    <div className="panel"><h2>Tìm phương án cho một khoảng ngày</h2>
      <div className="grid">
        <div><label>Từ ngày</label><input type="date" value={tu} onChange={(e) => setTu(e.target.value)} /></div>
        <div><label>Đến ngày</label><input type="date" value={den} onChange={(e) => setDen(e.target.value)} /></div>
        <div><label>Số khách</label><input type="number" value={khach} onChange={(e) => setKhach(Number(e.target.value))} /></div>
        <div><label>Km dự kiến (gồm chạy rỗng)</label><input type="number" value={km} onChange={(e) => setKm(Number(e.target.value))} /></div>
      </div>
      <button className="act teal" onClick={chay} disabled={busy}>{busy ? "Đang tính…" : "Xem phương án"}</button>
    </div>

    {nen && <div className="panel"><h2>Lệnh sẽ lập cho tour nào</h2>
      {!coQuyen && <p className="muted"><Tag cls="warn">chỉ xem</Tag>{" "}
        {nen.nguoi_duoc_lap_lenh.length
          ? <>Chỉ {nen.nguoi_duoc_lap_lenh.map((x: any) => `${x.full_name} (${x.username})`).join(", ")} được chốt lệnh (chỉ đạo Chủ tịch 07/9/2026). Đổi người phụ trách thì sửa tham số <b>xe_nguoi_lap_lenh</b>.</>
          : nen.ly_do_khong_gioi_han}</p>}
      <div className="grid">
        <div><label>Tour cần xe trong khoảng ngày này</label>
          <select value={tour} onChange={(e) => setTour(e.target.value)}>
            <option value="">– chọn tour –</option>
            {nen.tour.map((t: any) => <option key={t.id} value={t.id}>
              {t.code} · {t.name} · {fmtD(t.start_date)}→{fmtD(t.end_date)}{t.planned_pax ? ` · ${t.planned_pax} khách` : ""}
            </option>)}
          </select></div>
        <div><label>Tuyến trong bảng giá (để trống thì tính theo đơn giá ngày của xe)</label>
          <select value={rate} onChange={(e) => setRate(e.target.value)}>
            <option value="">– không theo bảng giá –</option>
            {nen.bang_gia.map((r: any) => <option key={r.id} value={r.id}>
              {r.route}{r.days ? ` · ${r.days} ngày` : ""} · nội bộ {r.internal_price?.toLocaleString("vi-VN")}
            </option>)}
          </select></div>
      </div>
      {!nen.tour.length && <p className="muted">Không có tour nào chạy trong khoảng ngày này. Đổi khoảng ngày ở ô trên, hoặc chờ Điều hành lập chuyến.</p>}
      {tour && !gy && <p className="muted"><Tag cls="warn">còn một bước</Tag> Đã chọn tour. Bấm <b>Xem phương án</b> ở khối trên để hệ thống lọc xe đủ điều kiện — nút Chốt lệnh nằm trên từng dòng xe được đề xuất.</p>}
      {matTour && matTour.planned_pax > 0 && khach === 0 &&
        <p className="muted"><Tag cls="warn">lưu ý</Tag> Tour này dự kiến {matTour.planned_pax} khách nhưng ô "Số khách" đang để 0 – gợi ý đang xếp hạng cho một chuyến không khách. Điền số khách rồi xem lại phương án.</p>}
      <p className="muted">{nen.ghi_chu}</p>
    </div>}

    {hoi && chon && <div className="panel"><h2>Hệ thống đánh giá xe này thấp hơn nhóm đề xuất</h2>
      <p>Xe <b>{chon.ma_xe} · {chon.xe}</b> được {hoi.diem_xe_chon} điểm, thấp nhất trong nhóm đề xuất là {hoi.diem_thap_nhat_trong_nhom_de_xuat} điểm.</p>
      {hoi.he_thong_nhan_xet?.length > 0 && <><p className="muted">Máy nhận xét về xe anh chọn:</p>
        <ul>{hoi.he_thong_nhan_xet.map((l: string, i: number) => <li key={i}>{l}</li>)}</ul></>}
      <p className="muted">Đây không phải nút chặn – anh vẫn chốt được. Nhưng lý do phải nằm lại trong hồ sơ, vì đây là dữ liệu duy nhất để mỗi quý biết thuật toán gợi ý có tốt lên không.</p>
      <div><label>Vì sao vẫn chọn xe này</label>
        <textarea rows={2} value={lyDo} onChange={(e) => setLyDo(e.target.value)}
          placeholder="Ví dụ: khách quen yêu cầu đúng xe này; xe điểm cao hơn đang chờ nghiệm thu bảo dưỡng" /></div>
      <button className="act orange" disabled={busy || !lyDo.trim()} onClick={() => chot(chon, lyDo)}>Chốt lệnh kèm lý do</button>{" "}
      <button className="act grey" onClick={() => { setHoi(null); setChon(null); setLyDo(""); }}>Bỏ, chọn xe khác</button>
    </div>}

    {gy && <>
      <div className="panel"><h2>Phương án đề xuất ({gy.phuong_an.length})</h2>
        <p className="muted">{gy.ghi_chu} <span className="muted">Bộ quy tắc {gy.rule_version}.</span></p>
        {gy.phuong_an.length ? <table><thead><tr><th>#</th><th>Xe</th><th>Chỗ</th><th>Điểm</th><th>Vì sao đề xuất</th><th>Điều kiện</th><th>Chốt</th></tr></thead>
          <tbody>{gy.phuong_an.map((p: any, i: number) => <tr key={p.vehicle_id}>
            <td><b>{i + 1}</b></td><td>{p.ma_xe} · {p.xe}</td><td className="num">{p.so_cho}</td>
            <td className="num">{p.diem}</td>
            <td>{p.ly_do.join(" · ")}</td>
            <td><Tag cls={p.muc_kiem_tra === "OK" ? "ok" : p.muc_kiem_tra === "BLOCK" ? "red" : "warn"}>
              {/* Tên mức lấy từ danh mục của máy chủ (danh-muc.muc_kiem_tra = MUC_TEN), không gõ lại
                  ba nhánh ở đây: bản cũ dồn mọi mức khác OK và UNKNOWN vào "Cần xem lại", nên một xe
                  BỊ CHẶN cũng hiện là "cần xem lại" — nhẹ hơn sự thật, đúng chỗ không được nhẹ. */}
              {dm?.muc_kiem_tra?.[p.muc_kiem_tra] || p.muc_kiem_tra}</Tag></td>
            <td>{coQuyen && <button className="act teal" style={{ margin: 0 }} disabled={busy || !tour}
              title={tour ? "" : "Chọn tour trước"} onClick={() => chot(p, "")}>Chốt lệnh</button>}</td>
          </tr>)}</tbody></table>
          : <p className="muted">Không còn xe nào hợp lệ cho khoảng ngày này.</p>}
        {gy.con_lai > 0 && <p className="muted">Còn {gy.con_lai} xe hợp lệ khác không nằm trong nhóm đề xuất.</p>}
      </div>

      {gy.bi_loai.length > 0 && <div className="panel wrap"><h2>Xe bị loại ({gy.bi_loai.length})</h2>
        <p className="muted">Loại ở bước lọc cứng — không phải điểm thấp, mà là không đủ điều kiện.</p>
        <table><thead><tr><th>Xe</th><th>Lý do loại</th></tr></thead>
          <tbody>{gy.bi_loai.map((b: any) => <tr key={b.vehicle_id}>
            <td>{b.ma_xe} · {b.xe}</td><td>{b.ly_do.map((l: string, i: number) => <div key={i}><Tag cls="red">chặn</Tag> {l}</div>)}</td>
          </tr>)}</tbody></table>
      </div>}
    </>}

    <div className="panel wrap"><h2>Lệnh đã lập ({ds.length})</h2>
      <p className="muted">Cột cuối ghi vết: lệnh theo gợi ý hay chọn khác, và lý do khi chọn khác. Đây là dữ liệu để mỗi quý đánh giá lại chất lượng thuật toán gợi ý.</p>
      {/* CHỖ HỞ CỐ Ý, ĐO ĐƯỢC: cửa lập lệnh vẫn nhận lệnh không kèm đề nghị. Bắt buộc ngay thì
          Điều hành đứng việc. Nhưng một chỗ hở không đếm được là một chỗ hở sẽ ở lại mãi — nên nó
          hiện ra ở đây, và khi con số về 0 thì siết thành bắt buộc không còn làm ai đứng việc. */}
      {ho && ho.tong_lenh > 0 && <p className="muted">
        {ho.khong_qua_de_nghi > 0
          ? <><Tag cls="warn">chuỗi chưa liền</Tag> {ho.khong_qua_de_nghi}/{ho.tong_lenh} lệnh lập <b>không qua cửa đề nghị</b>. Khi con số này về 0 và giữ 0 một thời gian thì bắt buộc đề nghị được, mà không làm ai đứng việc.</>
          : <><Tag cls="ok">chuỗi liền</Tag> Cả {ho.tong_lenh} lệnh đều đi qua cửa đề nghị xe.</>}</p>}
      {/* DL-3: hai chỗ hở giữa lệnh và chuyến. Số bên phải đo được 15/10/2026 là 756 — toàn bộ
          chuyến đang không gắn lệnh nào, vì tới hôm ấy chưa có đường nào ghi `dispatch_id`. */}
      {chuoi && <p className="muted">
        {chuoi.lenh_xong_chua_co_chuyen?.so > 0
          ? <><Tag cls="warn">lệnh xong, chưa có chuyến</Tag> {chuoi.lenh_xong_chua_co_chuyen.so}/{chuoi.lenh_xong_chua_co_chuyen.tong_lenh_hoan_thanh} lệnh đã hoàn thành mà <b>chưa sinh ra chuyến nào</b> — đóng lệnh lại một lần nữa thì máy sinh, hoặc gắn tay vào chuyến đã nạp.</>
          : <><Tag cls="ok">lệnh nào xong cũng có chuyến</Tag> </>}
        {" · "}
        {chuoi.chuyen_chua_gan_lenh?.so > 0
          ? <><Tag cls="warn">chuyến chưa gắn lệnh</Tag> {chuoi.chuyen_chua_gan_lenh.so}/{chuoi.chuyen_chua_gan_lenh.tong_chuyen} chuyến <b>không gắn lệnh nào</b> — phần lớn là sổ cũ nạp bằng tệp trước khi có mối nối này.</>
          : <><Tag cls="ok">chuyến nào cũng có lệnh</Tag></>}</p>}
      <table><thead><tr><th>#</th><th>Tour</th><th>Xe</th><th>Tài xế</th><th>Từ → đến</th><th>Giá nội bộ</th><th>Trạng thái</th><th>Tài xế nhận</th><th>Ghi vết gợi ý</th><th>Dọn</th></tr></thead>
        <tbody>{ds.length ? ds.map((d) => <tr key={d.id}>
          <td>{d.id}</td><td>{d.tour}</td><td>{d.ma_xe} · {d.xe}</td><td>{d.tai_xe}</td>
          <td>{fmtD(d.date_from)} → {fmtD(d.date_to)} <span className="muted">({d.so_ngay} ngày)</span></td>
          <td className="num">{d.internal_price?.toLocaleString("vi-VN")}</td>
          <td>{d.status === "hoan_thanh" ? <Tag cls="ok">hoàn thành</Tag> : d.status === "da_xac_nhan" ? <Tag cls="ok">đã xác nhận</Tag> : d.status === "huy" ? <Tag cls="red">hủy</Tag> : <Tag cls="warn">chờ xác nhận</Tag>}</td>
          {/* Cột này đứng CẠNH cột trạng thái, không thay nó: "đã xác nhận" là GĐ đội xe đã chốt
              lệnh — nghĩa có từ trước — còn cột này là tài xế đã nhận chưa. */}
          <td>{d.trang_thai_nhan === "da_nhan" ? <><Tag cls="ok">đã nhận</Tag> <div className="muted">{fmtDT(d.nhan_luc)}</div></>
            : d.trang_thai_nhan === "tu_choi" ? <><Tag cls="red">không nhận được</Tag> <div className="muted">{d.tu_choi_nhan_ly_do}</div></>
            : d.trang_thai_nhan === "qua_han" ? <><Tag cls="warn">quá hạn</Tag> <div className="muted">hạn {fmtDT(d.han_nhan)}</div></>
            : d.trang_thai_nhan === "chua_nhan" ? <><Tag cls="warn">chưa nhận</Tag> <div className="muted">hạn {fmtDT(d.han_nhan)}</div></>
            : <span className="muted">—</span>}</td>
          <td>{d.ly_do_khac_goi_y ? <><Tag cls="warn">chọn khác gợi ý</Tag> <div className="muted">{d.ly_do_khac_goi_y}</div></>
            : d.phuong_an_da_chon ? <Tag cls="ok">theo gợi ý</Tag> : <span className="muted">lệnh cũ, chưa có ghi vết</span>}</td>
          {/* `key` theo id lệnh là BẮT BUỘC: không có nó thì soát lệnh này rồi bấm sang lệnh khác
              sẽ thấy câu trả lời của lệnh trước — đã xảy ra thật ở cửa xoá xe ngày 14/10/2026,
              và đây là khối quyết định có làm mất hẳn một chứng từ hay không. */}
          <td><XoaLenh key={d.id} lenh={d} xong={load} /></td>
        </tr>) : <tr><td colSpan={10} className="muted">Chưa có lệnh điều xe nào.</td></tr>}</tbody></table>
    </div>
  </>);
}

/** DL-4 · Xoá một lệnh điều xe CHƯA TỪNG CHẠY (Chủ tịch chọn 14/10/2026).
 *
 *  Hai bước chứ không một: bấm SOÁT trước, máy in ra nội dung lệnh và nói vướng gì; nút xoá chỉ
 *  hiện khi máy đã trả lời là xoá được. KHÔNG dùng hộp thoại xác nhận của trình duyệt — một hộp
 *  thoại bấm quen tay thì không còn là một lần cân nhắc.
 *
 *  Máy in cả nội dung lệnh ra trước khi xoá, vì `status` không chứng minh được gì: `DL-0825` mang
 *  chữ "hoàn thành" mà không có lấy một chuyến nào. Người bấm phải nhìn tận mắt tour, xe, tài xế,
 *  ngày và giá rồi mới quyết. */
function XoaLenh({ lenh, xong }: { lenh: any; xong: () => void }) {
  const { user, toast } = useShell();
  const [s, setS] = useState<any>(null);
  const [ly, setLy] = useState("");
  const [dang, setDang] = useState(false);
  // PHẢI khớp với XOA_LENH trong backend/app/api/v1/hr.py — có phép thử canh.
  const XOA_LENH_VAI = ["cntt", "chutich"];
  const quyen = XOA_LENH_VAI.includes(user?.role || "");

  const soat = async () => {
    setDang(true);
    try { setS(await api(`/dispatch/${lenh.id}/xoa-duoc`)); }
    catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  const xoa = async () => {
    setDang(true);
    try {
      const r: any = await api(`/dispatch/${lenh.id}?ly_do=${encodeURIComponent(ly)}`, { method: "DELETE" });
      toast(r.message); setS(null); setLy(""); xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  if (!s) return <button className="act grey" style={{ margin: 0 }} disabled={dang}
    onClick={soat}>Xoá được không?</button>;
  return (<div>
    <div className={"gate " + (s.xoa_duoc ? "pass" : "fail")}>{s.noi}</div>
    {s.vuong?.length > 0 && <div className="muted">Đang vướng: {s.vuong.map((x: any) => `${x.so_dong} ${x.ten}`).join(" · ")}.</div>}
    {s.xoa_duoc && (quyen
      ? <>
        <label>Lý do xoá <span className="muted">(bắt buộc — tháng sau còn trả lời được vì sao
          chứng từ này biến mất)</span>
          <input value={ly} onChange={(e) => setLy(e.target.value)}
            placeholder="ví dụ: lệnh dữ liệu mẫu, chưa từng chạy" /></label>
        <button className="act orange" style={{ margin: "8px 0 0" }}
          disabled={dang || !ly.trim()} onClick={xoa}>Xoá lệnh #{lenh.id}</button>
      </>
      : <p className="muted">Xoá được, nhưng chỉ <b>CNTT</b> hoặc <b>Chủ tịch</b> bấm được nút xoá.</p>)}
    <p><button className="act grey" style={{ margin: "8px 0 0" }}
      onClick={() => { setS(null); setLy(""); }}>Thôi</button></p>
  </div>);
}

export default function Page() { return <Shell><LenhDieuXe /></Shell>; }
