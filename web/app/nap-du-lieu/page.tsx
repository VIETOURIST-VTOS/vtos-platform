"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Nạp dữ liệu vào VTOS – một cửa cho người nhập tay, cho tệp tải lên, và cho tác vụ AI.
 *
 *  Màn hình cố ý bắt đi hai bước: KIỂM TRA rồi mới NẠP. Bấm một nút rồi 500 dòng rác nằm trong sổ là
 *  chuyện của vài giây; dọn nó là chuyện của vài ngày. */
const PHONG: Record<string, string> = { dieu_hanh: "Điều hành", doi_xe: "Đội xe", hcns: "Hành chính & Nhân sự",
  kd_le: "Kinh doanh", ketoan: "Kế toán", visa: "Ban Visa", marketing: "Marketing", ban_tgd: "Ban TGĐ" };

function theoPhong(ds: any[]) {
  const g: Record<string, any[]> = {};
  ds.forEach((b) => { (g[b.phong_ban || "khac"] ||= []).push(b); });
  return g;
}

function NapDuLieu() {
  const { user, toast } = useShell();
  const [bo, setBo] = useState<any>(null);
  const [loai, setLoai] = useState("");
  const [rows, setRows] = useState<any[]>([]);
  const [tenTep, setTenTep] = useState("");
  const [kt, setKt] = useState<any>(null);
  const [ls, setLs] = useState<any[]>([]);
  const [boQua, setBoQua] = useState(false);
  const [dang, setDang] = useState(false);
  // Biểu nhập tay một dòng. Máy chủ đã có POST /nap-du-lieu/nhap-mot-dong từ đầu, nhưng đến 09/9/2026
  // không màn hình nào gọi nó – nên 26 bộ nạp chỉ có MỘT cửa duy nhất là tải tệp. Muốn ghi một lần đăng
  // kiểm, một lần bảo dưỡng, một hóa đơn đầu vào, một kỳ bảo hiểm thì phải dựng một tệp Excel. Thực tế
  // thì người ta không dựng, và ô ấy nằm trống – rồi con số cuối kỳ thiếu mà không ai biết thiếu ở đâu.
  const [oNhap, setONhap] = useState<Record<string, string>>({});
  const [ktDong, setKtDong] = useState<any>(null);
  // CẢ LÔ NHIỀU TỆP. Kho quyết toán cũ là việc theo lô từ bản chất: tháng 1/2026 có 81 tệp, mỗi tệp
  // một chuyến, và T1–T6 có 604 tệp. Ô chọn tệp ở mục 3 nhận đúng MỘT tệp, nên nạp tháng 1 là 81
  // lượt chọn tệp cho cửa "Tạo chuyến" rồi 81 lượt nữa cho cửa "Kho quyết toán cũ" – 162 lượt, và
  // cả nửa năm là hơn 1.200 lượt. Không ai làm nổi, nên thực tế là không ai nạp.
  const [lo, setLo] = useState<any[]>([]);
  const [dangLo, setDangLo] = useState("");
  // Quyền nạp đọc theo TỪNG BỘ NẠP do máy chủ công bố, không chép lại danh sách vai trò ở đây: chép là
  // sớm muộn hai bên lệch nhau, và bên lỏng hơn luôn là bên người dùng nhìn thấy.
  const chon0 = bo?.bo_nap?.find((b: any) => b.ma === loai);
  const canNap = !!chon0?.vai_tro?.includes(user?.role || "");

  const load = useCallback(async () => {
    try { const d = await api<any>("/nap-du-lieu/bo-nap"); setBo(d); if (!loai) setLoai(d.bo_nap[0]?.ma || "");
          setLs(await api("/nap-du-lieu/lich-su")); }
    catch (e) { toast(errMsg(e), true); }
  }, [toast, loai]);
  useEffect(() => { load(); }, [load]);

  const chon = chon0;

  /** Tải MẪU RIÊNG của bộ nạp – tệp .xlsx do chính VTOS sinh ra.
   *
   * KHÔNG dùng chung với taiMau() ở dưới: hàm ấy đọc phản hồi bằng .text(), đúng cho CSV nhưng làm
   * HỎNG tệp .xlsx – xlsx là tệp nén nhị phân, đọc thành chuỗi rồi gói lại là một tệp Excel mở
   * không lên. Hỏng kiểu ấy không có thông báo nào: người dùng tải về, bấm mở, Excel báo tệp lỗi,
   * và họ nghĩ hệ thống hỏng chứ không nghĩ cái nút hỏng.
   *
   * Cũng vì vậy nút "Tải tệp mẫu (.csv)" chung KHÔNG hiện cho bộ nạp có mẫu riêng: bộ nạp mẫu quyết
   * toán nhận tệp mười sheet, còn CSV phẳng tải về điền xong nạp lên là bị từ chối ngay dòng đầu. */
  const taiMauRieng = async (m: { ten: string; duong_dan: string }) => {
    try {
      const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
      const r = await fetch(m.duong_dan, { headers: h });
      if (!r.ok) throw { status: r.status, message: `Không tải được ${m.ten}` };
      const blob = await r.blob();
      const cd = r.headers.get("content-disposition") || "";
      const ten = /filename="?([^"]+)"?/.exec(cd)?.[1] || `${m.ten}.xlsx`;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = ten; a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) { toast(errMsg(e), true); }
  };

  const taiMau = () => {
    const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
    fetch(`/api/v1/nap-du-lieu/mau/${loai}`, { headers: h }).then((r) => r.text()).then((t) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob(["﻿" + t], { type: "text/csv;charset=utf-8" }));
      a.download = `mau_${loai}.csv`; a.click();
    }).catch(() => toast("Không tải được tệp mẫu", true));
  };

  const kiemTraTep = async (f: File) => {
    setDang(true); setKt(null);
    try {
      const fd = new FormData(); fd.append("loai", loai); fd.append("tep", f);
      const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
      const r = await fetch("/api/v1/nap-du-lieu/kiem-tra-tep", { method: "POST", headers: h, body: fd });
      const d = await r.json();
      if (!r.ok) throw { status: r.status, message: d?.detail || "Không đọc được tệp" };
      setKt(d); setRows(d.rows || []); setTenTep(d.ten_tep || f.name);
      toast(`Đã đọc ${d.so_dong} dòng – xem kết quả kiểm tra bên dưới`);
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  /** MỘT TỆP SẼ GHI ĐƯỢC BAO NHIÊU DÒNG, VÀ CÓ ĐƯỢC GHI KHÔNG.
   *
   * `hop_le` là phần SẠCH – ghi ngay, không cần hỏi ai. `da_co` là phần CÓ CẢNH BÁO: bộ nạp chỉ
   * ghi khi người duyệt bấm rõ (`bo_qua_dong_loi`).
   *
   * Bản trước đòi `hop_le > 0` mới cho nạp, và cửa "Kho quyết toán CŨ" chết đứng ở đấy. Đo trên hệ
   * thống thật ngày 16/9/2026 với 81 tệp tháng 1: **0 hợp lệ · 70 cần xác nhận · 11 bị chặn**. Con
   * số 0 không phải hỏng – bản đối chiếu H1 chưa có cửa tải nên MỌI tệp đều mang cảnh báo "không có
   * số thứ hai để soát", và đó là hàng rào cố ý. Nhưng bộ nạp CÓ đường qua hàng rào ấy, còn màn
   * hình thì không mở đường ra – nên cửa vĩnh viễn hiện "Nạp 0 tệp".
   *
   * Tệp bị CHẶN thì không lối nào ghi được, kể cả khi bấm xác nhận. Đó mới là hàng rào cứng. */
  const soSeNap = (x: any) => (x.hop_le || 0) + (boQua ? (x.da_co || 0) : 0);
  const seNap = (x: any) => soSeNap(x) > 0 && (x.dong_loi === 0 || boQua);

  /** Đọc thử CẢ LÔ. Từng tệp đi qua ĐÚNG cửa `kiem-tra-tep` của mục 3 – cùng bộ kiểm, cùng khóa
   *  chống trùng. Bước này vẫn CHƯA GHI GÌ, y như nạp một tệp. */
  const kiemTraCaLo = async (fs: File[]) => {
    setDang(true); setLo([]); setKt(null);
    const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
    const ds: any[] = [];
    for (let i = 0; i < fs.length; i++) {
      const f = fs[i];
      setDangLo(`Đang đọc ${i + 1}/${fs.length}: ${f.name}`);
      try {
        const fd = new FormData(); fd.append("loai", loai); fd.append("tep", f);
        const r = await fetch("/api/v1/nap-du-lieu/kiem-tra-tep", { method: "POST", headers: h, body: fd });
        const d = await r.json();
        if (!r.ok) throw new Error(d?.detail || "Không đọc được tệp");
        // ten_tep giữ theo TỪNG TỆP, không gộp. Xem giải thích ở napCaLo().
        //
        // CỬA SOÁT TRẢ VỀ HAI HÌNH DẠNG KHÁC NHAU, VÀ BẢN ĐẦU CHỈ ĐỌC MỘT.
        //
        // Bộ nạp thường đi qua `_kiem_tra_tung_dong` và trả khoá `hop_le` (số dòng sạch, sẽ nạp).
        // Bộ nạp THEO LÔ – gồm đúng hai cửa kho quyết toán cũ mà màn hình này sinh ra để phục vụ –
        // đi qua `kiem_lo` và trả khoá `da_nap`. Nó KHÔNG có `hop_le`.
        //
        // Bản đầu chỉ đọc `d.hop_le`, nên với hai cửa kho cũ nó luôn ra `undefined`. Hậu quả đo
        // được khi chạy thật trên vtos.infinitytours.org ngày 16/9/2026: chọn cả 81 tệp thì bảng
        // hiện đủ 81 dòng "sẵn sàng", nhưng ô đếm ghi "0 dòng hợp lệ" và nút ghi "Nạp 0 TỆP vào
        // hệ thống". Cửa mở ra mà không nạp được gì – hỏng đúng ở chỗ nó sinh ra để làm.
        //
        // Đọc cả hai khoá. `??` chứ không phải `||`: số 0 là một câu trả lời thật (không có dòng
        // nào nạp được), không được rơi sang khoá kia.
        const hop_le = d.hop_le ?? d.da_nap ?? 0;
        ds.push({ ten_tep: d.ten_tep || f.name, so_dong: d.so_dong, hop_le,
                  da_co: d.da_co, dong_loi: d.dong_loi, rows: d.rows || [], trang_thai: "da_doc" });
      } catch (e: any) {
        ds.push({ ten_tep: f.name, so_dong: 0, hop_le: 0, da_co: 0, dong_loi: 0,
                  rows: [], trang_thai: "khong_doc_duoc", loi: e?.message || String(e) });
      }
      setLo([...ds]);
    }
    setDangLo(""); setDang(false);
    const hong = ds.filter((x) => x.trang_thai === "khong_doc_duoc").length;
    toast(hong ? `Đọc xong ${fs.length} tệp – ${hong} tệp không đọc được` : `Đọc xong ${fs.length} tệp`, !!hong);
  };

  /** Nạp cả lô: MỖI TỆP MỘT LẦN GỌI, mang ĐÚNG TÊN TỆP CỦA NÓ.
   *
   *  ĐO TRƯỚC KHI TIN. Bản nháp đầu của chỗ này ghi rằng gộp dòng nhiều tệp làm một lần nạp sẽ cắt
   *  mất cầu nối tệp↔chuyến sang bản đối chiếu H1. Chạy thử thì KHÔNG PHẢI: mỗi dòng mang sẵn
   *  `ten_tep` của chính nó, và `nap_lo` ghi sổ `kho_cu_tep_chuyen` bằng tên trong DÒNG chứ không
   *  bằng tham số của lần gọi – nên gộp lô, cầu nối vẫn đúng từng tệp. Đừng suy lại kết luận cũ ấy.
   *
   *  Vẫn gọi theo từng tệp, nhưng vì ba lý do khác và nhỏ hơn:
   *
   *    1. NHẬT KÝ NẠP. `intake_runs` ghi một dòng cho mỗi lần gọi, kèm tên tệp và mã băm nội dung.
   *       Gộp 81 tệp là một dòng nhật ký mang một cái tên bịa cho dữ liệu của 81 tệp – câu "con số
   *       này ở đâu ra" hết trả lời được, mà đó là lý do cả màn hình Nhật ký nạp tồn tại.
   *    2. CÔ LẬP LỖI. Ô "bỏ qua dòng lỗi" là một quyết định cho MỘT tệp. Gộp lô thì một tệp hỏng
   *       kéo theo quyết định ấy áp lên cả 81 tệp.
   *    3. DỪNG GIỮA CHỪNG. Mất mạng ở tệp thứ 57 mà gộp lô thì không biết gì đã vào, gì chưa. */
  const napCaLo = async () => {
    const can = lo.filter((x) => x.trang_thai === "da_doc" && seNap(x));
    if (!can.length) return;
    if (!confirm(`Nạp ${can.length} tệp vào hệ thống?\n\n`
      + `Tổng ${can.reduce((s, x) => s + soSeNap(x), 0)} dòng sẽ ghi.\n`
      + `Mỗi tệp vào nhật ký thành một dòng riêng mang đúng tên tệp của nó.`)) return;
    setDang(true);
    const ds = [...lo];
    for (let i = 0; i < can.length; i++) {
      const t = can[i];
      const vt = ds.indexOf(t);
      setDangLo(`Đang nạp ${i + 1}/${can.length}: ${t.ten_tep}`);
      try {
        const d = await api<any>("/nap-du-lieu/nap", { method: "POST", json: {
          loai, rows: t.rows, bo_qua_dong_loi: boQua,
          ten_tep: t.ten_tep,          // TÊN CỦA CHÍNH TỆP NÀY – không phải tên chung của lô
          nguon: "nguoi_nhap" } });
        ds[vt] = { ...t, trang_thai: "da_nap", da_nap: d.da_nap, message: d.message };
      } catch (e) {
        ds[vt] = { ...t, trang_thai: "nap_hong", loi: errMsg(e) };
      }
      setLo([...ds]);
    }
    setDangLo(""); setDang(false);
    setLs(await api("/nap-du-lieu/lich-su"));
    const hong = ds.filter((x) => x.trang_thai === "nap_hong").length;
    toast(hong ? `Xong – ${hong} tệp nạp hỏng, xem bảng` : `Đã nạp xong ${can.length} tệp`, !!hong);
  };

  const nap = async () => {
    setDang(true);
    try {
      const d = await api<any>("/nap-du-lieu/nap", { method: "POST", json: {
        loai, rows, bo_qua_dong_loi: boQua, ten_tep: tenTep, nguon: "nguoi_nhap" } });
      setKt(d); toast(d.message);
      if (d.da_nap > 0) { setRows([]); setTenTep(""); }
      setLs(await api("/nap-du-lieu/lich-su"));
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  /** Ghi một dòng. Đi qua ĐÚNG bộ kiểm của cửa tải tệp – máy chủ dùng chung một hàm cho cả hai cửa,
   *  nên không có đường nào nhập tay mà lỏng hơn nhập tệp. */
  const ghiMotDong = async () => {
    setDang(true); setKtDong(null);
    try {
      const row: Record<string, any> = {};
      (chon?.cot || []).forEach((c: any) => { const v = (oNhap[c.key] ?? "").trim(); if (v !== "") row[c.key] = v; });
      const d = await api<any>("/nap-du-lieu/nhap-mot-dong", { method: "POST", json: { loai, row, cua: "nhap_tay" } });
      setKtDong(d);
      if (d.da_ghi) {
        toast(d.ket_qua ? `Đã ghi: ${d.ket_qua}` : d.message);
        // Giữ lại các ô NGÀY, xóa phần còn lại. Người nhập mười phiếu dầu của cùng một ngày không phải gõ
        // lại ngày mười lần; còn giữ cả số tiền thì dòng sau lặng lẽ mang số của dòng trước.
        const giu: Record<string, string> = {};
        (chon?.cot || []).forEach((c: any) => { if (c.kieu === "ngay" && oNhap[c.key]) giu[c.key] = oNhap[c.key]; });
        setONhap(giu);
        setLs(await api("/nap-du-lieu/lich-su"));
      }
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  const thieuBatBuoc = (chon?.cot || []).filter((c: any) => c.bat_buoc && !(oNhap[c.key] || "").trim());

  if (!bo) return <p className="muted">Đang tải…</p>;
  return (<>
    <h1>Nạp dữ liệu vào VTOS</h1>
    <p className="muted">Gõ tay từng dòng, tải tệp nhiều dòng và tác vụ AI đọc ảnh đi qua <b>cùng một cửa</b>: cùng bộ kiểm tra,
      cùng khóa chống trùng, cùng nhật ký. Nếu mỗi đường một kiểu kiểm tra thì cái chặt nhất trở nên vô
      nghĩa — người ta chỉ cần đi đường lỏng nhất.</p>

    <div className="panel">
      <h2>1. Chọn loại dữ liệu</h2>
      <label>Loại
        <select value={loai} onChange={(e) => { setLoai(e.target.value); setKt(null); setRows([]); }}>
          {Object.entries(theoPhong(bo.bo_nap)).map(([pb, ds]: any) =>
            <optgroup key={pb} label={PHONG[pb] || pb}>
              {ds.map((b: any) => <option key={b.ma} value={b.ma}>{b.ten}</option>)}
            </optgroup>)}
        </select></label>
      {chon && <>
        <p className="muted">{chon.mo_ta}</p>
        <p className="muted">Khóa chống trùng: <b>{chon.khoa_chong_trung}</b></p>
        {!canNap && <p className="muted"><Tag cls="warn">chỉ xem</Tag> Loại dữ liệu này thuộc {PHONG[chon.phong_ban] || "phòng khác"}.
          Anh/chị xem được cấu trúc và kiểm tra thử, nhưng người nạp phải là người của phòng đó — để nhật ký
          ghi đúng tên người chịu trách nhiệm về số liệu.</p>}
        <div className="wrap"><table>
          <thead><tr><th>Cột trong tệp</th><th>Bắt buộc</th><th>Ví dụ</th><th>Ghi chú</th></tr></thead>
          <tbody>{chon.cot.map((c: any) => <tr key={c.key}>
            <td>{c.ten}</td>
            <td>{c.bat_buoc ? <Tag cls="red">bắt buộc</Tag> : <span className="muted">không</span>}</td>
            <td className="muted">{c.vi_du}</td><td className="muted">{c.ghi_chu}</td>
          </tr>)}</tbody></table></div>
        {chon.mau_rieng?.length > 0 ? <div style={{ marginTop: 8 }}>
          <p className="muted" style={{ marginBottom: 4 }}>
            Bộ nạp này nhận <b>tệp Excel nhiều sheet do chính VTOS phát ra</b>, không nhận CSV phẳng.
            Mẫu được <b>sinh ra lúc bấm</b> nên danh mục khoản mục trong mẫu luôn khớp danh mục hệ
            thống – tải về, điền vào ô nền vàng, rồi tải lên ở bước dưới.
          </p>
          {chon.mau_rieng.map((m: any) => (
            <button key={m.duong_dan} type="button" className="act grey"
                    style={{ marginRight: 6 }} onClick={() => taiMauRieng(m)}>
              Tải {m.ten}
            </button>
          ))}
        </div> : <button className="act grey" style={{ marginTop: 8 }} onClick={taiMau}>Tải tệp mẫu (.csv)</button>}
      </>}
    </div>

    {chon && <div className="panel">
      <h2>2. Nhập tay một dòng</h2>
      <p className="muted">Dùng khi chỉ có <b>một bản ghi</b>: một lần đăng kiểm, một phiếu bảo dưỡng, một
        hóa đơn đầu vào. Bắt dựng tệp Excel cho một dòng là cách chắc chắn nhất để dòng ấy không bao giờ
        được nhập. Ô nhập đi qua <b>cùng bộ kiểm</b> với cửa tải tệp – không có đường nào nhập tay mà lỏng hơn.</p>
      {!canNap
        ? <p className="muted"><Tag cls="warn">chỉ xem</Tag> Loại dữ liệu này thuộc {PHONG[chon.phong_ban] || "phòng khác"} – người nhập phải là người của phòng đó.</p>
        : <>
        <div className="grid">
          {chon.cot.map((c: any) => <div key={c.key}>
            <label>{c.ten}{c.bat_buoc && <span style={{ color: "var(--red)" }}> *</span>}</label>
            {c.chon
              ? <select value={oNhap[c.key] || ""} onChange={(e) => setONhap({ ...oNhap, [c.key]: e.target.value })}>
                  <option value="">– chọn –</option>
                  {Object.entries(c.chon).map(([ma, ten]: any) => <option key={ma} value={ma}>{ten}</option>)}
                </select>
              : <input type={c.kieu === "ngay" ? "date" : c.kieu === "so" ? "number" : "text"}
                       value={oNhap[c.key] || ""} placeholder={c.kieu === "ngay" ? "" : c.vi_du}
                       min={c.min} max={c.max}
                       onChange={(e) => setONhap({ ...oNhap, [c.key]: e.target.value })} />}
            {c.ghi_chu && <div className="muted" style={{ fontSize: 12 }}>{c.ghi_chu}</div>}
          </div>)}
        </div>
        <button className="act teal" disabled={dang || thieuBatBuoc.length > 0} onClick={ghiMotDong}>
          {dang ? "Đang ghi…" : "Kiểm và ghi một dòng"}</button>{" "}
        <button className="act grey" disabled={dang} onClick={() => { setONhap({}); setKtDong(null); }}>Xóa biểu</button>
        {thieuBatBuoc.length > 0 && <p className="muted">Còn thiếu ô bắt buộc: <b>{thieuBatBuoc.map((c: any) => c.ten).join(", ")}</b></p>}
        <p className="muted">Ghi xong, biểu giữ lại các ô NGÀY và xóa phần còn lại – để nhập dòng tiếp theo
          không phải gõ lại ngày, mà cũng không mang nhầm số tiền của dòng trước.</p>
        {ktDong && <div style={{ marginTop: 8 }}>
          {ktDong.da_ghi
            ? <p><Tag cls="ok">đã ghi</Tag> {ktDong.ket_qua || ktDong.message}</p>
            : <p><Tag cls={ktDong.da_co ? "warn" : "red"}>chưa ghi</Tag> {ktDong.message}</p>}
          {ktDong.loi?.map((l: string, i: number) => <div key={i}><Tag cls="red">{l}</Tag></div>)}
          {ktDong.canh_bao?.map((c: string, i: number) => <div key={i} className="muted">{c}</div>)}
        </div>}
      </>}
    </div>}

    <div className="panel">
      <h2>3. Tải nhiều dòng bằng tệp</h2>
      <p className="muted">Bước này <b>chưa ghi gì</b> vào hệ thống. Nhận tệp .csv hoặc .xlsx, hàng đầu là
        tên cột — tên cột viết hoa hay thường đều được.</p>
      <input type="file" accept=".csv,.xlsx,.xlsm" disabled={dang}
             onChange={(e) => { const f = e.target.files?.[0]; if (f) kiemTraTep(f); }} />
      {tenTep && <p className="muted">Tệp: <b>{tenTep}</b> · {rows.length} dòng</p>}
    </div>

    <div className="panel">
      <h2>3b. Tải CẢ LÔ nhiều tệp một lượt</h2>
      <p className="muted">Chọn nhiều tệp cùng lúc (giữ <b>Ctrl</b> hoặc bấm <b>Ctrl+A</b> trong hộp thoại).
        Máy đọc từng tệp qua <b>đúng bộ kiểm của mục 3</b> – không nới một chốt nào – rồi hiện bảng dưới đây.
        Bước này <b>chưa ghi gì</b>.</p>
      <p className="muted">Mỗi tệp vào nhật ký thành <b>một dòng riêng mang đúng tên tệp của nó</b> — để
        sau này còn trả lời được &quot;con số này ở đâu ra&quot;. Một tệp hỏng cũng chỉ dừng ở tệp ấy,
        không kéo theo cả lô.</p>
      <input type="file" accept=".csv,.xlsx,.xlsm" multiple disabled={dang}
             onChange={(e) => { const fs = Array.from(e.target.files || []); if (fs.length) kiemTraCaLo(fs); }} />
      {dangLo && <p className="muted">{dangLo}</p>}
    </div>

    {lo.length > 0 && <div className="panel wrap">
      <h2>3c. Kết quả cả lô — {lo.length} tệp</h2>
      <div className="kpis">
        <div className="kpi"><b>{lo.length}</b><span>tệp</span></div>
        <div className="kpi"><b style={{ color: "var(--ok, green)" }}>{lo.reduce((s, x) => s + (x.hop_le || 0), 0)}</b>
          <span>dòng hợp lệ</span></div>
        <div className="kpi"><b className="muted">{lo.reduce((s, x) => s + (x.da_co || 0), 0)}</b>
          <span>đã có — bỏ qua</span></div>
        <div className="kpi"><b style={{ color: lo.some((x) => x.dong_loi) ? "var(--red)" : undefined }}>
          {lo.reduce((s, x) => s + (x.dong_loi || 0), 0)}</b><span>dòng lỗi</span></div>
        <div className="kpi"><b style={{ color: lo.some((x) => x.trang_thai === "khong_doc_duoc") ? "var(--red)" : undefined }}>
          {lo.filter((x) => x.trang_thai === "khong_doc_duoc").length}</b><span>tệp không đọc được</span></div>
      </div>
      <table><thead><tr><th>Tệp</th><th className="num">Dòng</th><th className="num">Hợp lệ</th>
        <th className="num">Đã có</th><th className="num">Lỗi</th><th>Trạng thái</th></tr></thead>
        <tbody>{lo.map((x, i) => <tr key={i}>
          <td>{x.ten_tep}</td>
          <td className="num">{x.so_dong}</td>
          <td className="num">{x.hop_le}</td>
          <td className="num muted">{x.da_co}</td>
          <td className="num">{x.dong_loi || 0}</td>
          <td>{x.trang_thai === "khong_doc_duoc" ? <Tag cls="red">không đọc được: {x.loi}</Tag>
            : x.trang_thai === "nap_hong" ? <Tag cls="red">nạp hỏng: {x.loi}</Tag>
            : x.trang_thai === "da_nap" ? <Tag cls="ok">đã nạp {x.da_nap}</Tag>
            : x.dong_loi > 0 ? <Tag cls="warn">còn dòng lỗi</Tag>
            /* "Sẵn sàng" TỪNG CHỈ NGHĨA LÀ "không có dòng lỗi" – và đó là một lời nói dối.
             * Tệp có hop_le=0, da_co=1, dong_loi=0 hiện "sẵn sàng" trong khi nút nạp không hề
             * đếm nó: cả 81 tệp tháng 1 nằm đúng vào ô ấy, bảng nói sẵn sàng còn nút nói
             * "Nạp 0 tệp". Nhãn phải nói đúng thứ nút sẽ làm. */
            : (x.hop_le || 0) === 0 && (x.da_co || 0) > 0
              ? <Tag cls="warn">chờ xác nhận{boQua ? " — sẽ nạp" : " — nút chưa đếm"}</Tag>
            : (x.hop_le || 0) === 0 ? <Tag cls="warn">không có dòng nào để nạp</Tag>
            : <Tag cls="ok">sẵn sàng</Tag>}</td>
        </tr>)}</tbody></table>

      {canNap && lo.some((x) => x.trang_thai === "da_doc") && <div style={{ marginTop: 10 }}>
        {lo.some((x) => x.dong_loi > 0 || x.da_co > 0) && <label style={{ display: "block" }}>
          <input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={boQua}
                 onChange={(e) => setBoQua(e.target.checked)} />
          Nạp cả phần CÓ CẢNH BÁO, và bỏ qua dòng lỗi
        </label>}
        {lo.some((x) => x.da_co > 0) && !boQua && <p className="muted">
          <b>{lo.reduce((s, x) => s + (x.da_co || 0), 0)}</b> dòng đang mang cảnh báo nên chưa được
          nạp. Tích ô trên là bấm rõ &quot;tôi đã xem và vẫn nạp&quot; — đó là một quyết định, không
          phải một mặc định. Tệp bị <b>chặn</b> thì tích ô này cũng không nạp được.</p>}
        <button className="act teal" disabled={dang} onClick={napCaLo}>
          {dang ? (dangLo || "Đang nạp…")
                : `Nạp ${lo.filter((x) => x.trang_thai === "da_doc" && seNap(x)).length} tệp vào hệ thống`}
        </button>
        {lo.some((x) => x.dong_loi > 0) && !boQua && <p className="muted">Những tệp còn dòng lỗi đang bị bỏ
          ra ngoài. Sửa tệp rồi đọc lại, hoặc tích ô trên — bỏ qua dòng lỗi là một quyết định, không phải
          một mặc định.</p>}
      </div>}
    </div>}

    {kt && <div className="panel">
      <h2>4. Kết quả kiểm tra tệp</h2>
      <div className="kpis">
        <div className="kpi"><b>{kt.so_dong}</b><span>dòng trong tệp</span></div>
        {/* Bộ nạp theo lô trả `da_nap` chứ không trả `hop_le` – xem soSeNap() ở trên. */}
        <div className="kpi"><b style={{ color: "var(--ok, green)" }}>{kt.hop_le ?? kt.da_nap ?? 0}</b><span>hợp lệ, sẽ nạp</span></div>
        <div className="kpi"><b className="muted">{kt.da_co}</b><span>đã có trong hệ thống — bỏ qua</span></div>
        <div className="kpi"><b style={{ color: kt.dong_loi ? "var(--red)" : undefined }}>{kt.dong_loi}</b><span>dòng lỗi</span></div>
      </div>
      {kt.cot_khong_dung?.length > 0 && <p className="muted">Cột không dùng đến:
        <b> {kt.cot_khong_dung.join(", ")}</b> — kiểm tra lại xem có nạp nhầm tệp không.</p>}
      {/* HAI HÌNH DẠNG KẾT QUẢ, VÀ BẢNG NÀY TỪNG CHỈ BIẾT MỘT.
        *
        * Bộ nạp thường trả `dong` – một dòng cho mỗi DÒNG trong tệp. Bộ nạp THEO LÔ trả `chi_tiet`
        * – một dòng cho mỗi TỆP, và KHÔNG có `dong`.
        *
        * Bản trước gọi thẳng `kt.dong.slice(...)`. Với sáu bộ nạp theo lô thì `kt.dong` là undefined
        * và cả trang NỔ: "TypeError: Cannot read properties of undefined (reading 'slice')" –
        * màn hình trắng, người dùng mất luôn kết quả vừa đọc. Bắt được trên chính bản chạy thật
        * ngày 16/9/2026 khi tải một tệp kho quyết toán cũ qua mục 3. */}
      {kt.chi_tiet ? <div className="wrap"><table>
        <thead><tr><th>Tệp</th><th>Chuyến</th><th>Kết quả</th></tr></thead>
        <tbody>{kt.chi_tiet.slice(0, 200).map((x: any, i: number) => <tr key={i}>
          <td>{x.ten_tep}</td>
          <td className="muted">{x.ma_tour || "—"}</td>
          <td>{(x.chan || []).map((l: string, j: number) => <div key={j}><Tag cls="red">{l}</Tag></div>)}
            {x.ro === "khong_thay_chuyen" && <Tag cls="red">không tìm thấy chuyến trong VTOS</Tag>}
            {x.ro === "nap_duoc" && <Tag cls="ok">sạch</Tag>}
            {(x.can_xac_nhan || []).map((c: string, j: number) =>
              <div key={j} className="muted">{c}</div>)}
            {(x.doc_thieu || []).map((c: string, j: number) =>
              <div key={j} className="muted">{c}</div>)}</td>
        </tr>)}</tbody></table></div>
      : <div className="wrap"><table>
        <thead><tr><th>Dòng</th><th>Nội dung</th><th>Kết quả</th></tr></thead>
        <tbody>{(kt.dong || []).slice(0, 200).map((d: any) => <tr key={d.dong}>
          <td className="muted">{d.dong}</td>
          <td>{d.tom_tat}</td>
          <td>{d.loi.length ? d.loi.map((l: string, i: number) => <div key={i}><Tag cls="red">{l}</Tag></div>)
            : d.da_co ? <Tag cls="warn">đã có ({d.da_co})</Tag> : <Tag cls="ok">hợp lệ</Tag>}
            {d.canh_bao?.map((c: string, i: number) => <div key={i} className="muted">{c}</div>)}</td>
        </tr>)}</tbody></table></div>}
      {kt.da_nap === undefined && canNap && <div style={{ marginTop: 10 }}>
        {kt.dong_loi > 0 && <label style={{ display: "block" }}>
          <input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={boQua}
                 onChange={(e) => setBoQua(e.target.checked)} />
          Bỏ qua {kt.dong_loi} dòng lỗi và chỉ nạp phần hợp lệ
        </label>}
        <button className="act teal" disabled={dang || (kt.dong_loi > 0 && !boQua) || kt.hop_le === 0}
                onClick={nap}>{dang ? "Đang nạp…" : `Nạp ${kt.hop_le} dòng vào hệ thống`}</button>
        {kt.dong_loi > 0 && !boQua && <p className="muted">Còn dòng lỗi nên nút nạp đang khóa. Sửa tệp rồi
          kiểm tra lại, hoặc tích ô trên để nạp phần hợp lệ — bỏ qua dòng lỗi là một quyết định, không phải
          một mặc định.</p>}
      </div>}
      {/* Bộ nạp theo lô đi qua mục 3 chỉ XEM TRƯỚC, không có nút nạp ở đây (nút nạp nằm ở mục 3c).
        * Trước đây chỗ này in `kt.message` – với bản xem trước thì message rỗng, nên người dùng thấy
        * một khoảng trắng và không hiểu vì sao không có nút nạp. Nói thẳng ra. */}
      {kt.da_nap !== undefined && <p>{kt.message ? <b>{kt.message}</b> : <>
        <b>{kt.ghi_chu || "Đây là bước XEM TRƯỚC – chưa ghi gì vào hệ thống."}</b><br />
        <span className="muted">Loại dữ liệu này nạp theo LÔ. Muốn nạp thật thì kéo chính tệp này
          (một tệp cũng được) vào <b>mục 3b</b> ở trên, xem bảng ở mục 3c rồi bấm nút nạp ở đó.</span>
      </>}</p>}
    </div>}

    <div className="panel wrap">
      <h2>Nhật ký nạp</h2>
      <p className="muted">Để trả lời được câu &quot;con số này ở đâu ra&quot; vào đúng lúc khó nhất.</p>
      <table><thead><tr><th>Lúc</th><th>Loại</th><th>Tệp</th><th>Nguồn</th><th>Dòng</th><th>Đã nạp</th>
        <th>Đã có</th><th>Lỗi</th><th>Người nạp</th><th>Mã băm</th></tr></thead>
        <tbody>{ls.length ? ls.map((r) => <tr key={r.id}>
          <td className="muted">{fmtDT(r.luc)}</td><td>{r.ten_bo_nap}</td>
          <td className="muted">{r.ten_tep || "—"}</td>
          <td>{r.nguon === "ai" ? <Tag cls="warn">AI: {r.tac_nhan}</Tag> : <span className="muted">{r.nguon_ten}</span>}</td>
          <td className="num">{r.so_dong}</td><td className="num">{r.da_nap}</td>
          <td className="num muted">{r.bo_qua_da_co}</td>
          <td className="num">{r.dong_loi}{r.bo_qua_dong_loi ? " (bỏ qua)" : ""}</td>
          <td className="muted">{r.boi}</td><td className="muted">{r.hash}</td>
        </tr>) : <tr><td colSpan={10} className="muted">Chưa có lần nạp nào.</td></tr>}</tbody></table>
    </div>
  </>);
}

export default function Page() { return <Shell><NapDuLieu /></Shell>; }
