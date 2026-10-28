"use client";
import { useState, useEffect, useCallback } from "react";
import { login, getUser, clearSession } from "@/lib/api";
import { THANH_TREN, TRANG_MO_DAU, KHUNG_HO_TRO, CAU_CHUYEN } from "@/components/cong/manh";
import { ThuVien } from "@/components/cong/co-dong/CoDong";
import { goiCong as goi, luuPhienCong, laTenMienCong, VTOS_GOC } from "@/lib/cong";

/* CG-1 · CỔNG KẾT NỐI VTD thay màn đăng nhập VTOS — Chủ tịch duyệt bản xem thử 26/10/2026, dựng từ đúng
   bộ giao diện v3.2 (logo, biểu tượng, địa cầu có máy bay bay quanh). Bốn ô:
     · Nội bộ Vietourist → tài khoản + mật khẩu VTOS như cũ, vào thẳng VTOS cùng tab.
     · Khách hàng / Đối tác / Cổ đông → mã một lần qua Zalo hoặc Email (người dùng chọn kênh).
   Phiên cổng ngoài cất ở khoá RIÊNG `vtd_cong_phien`, không bao giờ ở `vtos_token`: lib/api.ts không gửi
   nó lên cửa nội bộ nào, và máy chủ cũng không nhận nó ở cửa nội bộ (ký bằng khoá khác).

   KHÔNG in tên tài khoản và mật khẩu lên trang này — `tests/test_mat_khau_cong_khai.py` đọc thẳng tệp
   này để canh. Quên mật khẩu nội bộ thì liên hệ HCNS hoặc CNTT để đặt lại; mật khẩu đặt lại là mật
   khẩu tạm, lần đăng nhập kế tiếp buộc đổi. */

type Man = "cong" | "noi" | "kh" | "dt" | "cd";

/* CG-2 · Bốn tên miền (Chủ tịch chốt 27/10/2026): mở tên miền nào thì vào thẳng cổng ấy, không qua
   trang bốn ô. Địa chỉ khác (vtos.infinitytours.org, vercel.app, máy dựng) giữ trang bốn ô như cũ.
   `?cong=` trên đường dẫn vẫn thắng. Nút «← Bốn cổng truy cập» vẫn còn để đổi cổng. */
const CONG_THEO_TEN_MIEN: Record<string, Man> = {
  "crm.vietourist.vn": "noi", "kh.vietourist.vn": "kh", "dt.vietourist.vn": "dt", "ir.vietourist.vn": "cd",
};
const VAI: Record<Exclude<Man, "cong">, { role: string; loai: string; ten: string; h2: string; p: string }> = {
  noi: { role: "nhan-vien", loai: "", ten: "Nội bộ Vietourist", h2: "Đăng nhập VTOS", p: "Dành cho Ban lãnh đạo, quản lý và nhân viên." },
  kh: { role: "khach-hang", loai: "khach_hang", ten: "Khách hàng", h2: "Đăng nhập khách hàng", p: "Sử dụng liên hệ đã xác minh để vào không gian của bạn." },
  dt: { role: "doi-tac", loai: "doi_tac", ten: "Đối tác", h2: "Đăng nhập đối tác", p: "Liên hệ của người đại diện. Lần đầu: xác thực liên hệ rồi gửi hồ sơ để Vietourist duyệt." },
  cd: { role: "co-dong", loai: "co_dong", ten: "Cổ đông", h2: "Đăng nhập cổ đông", p: "Sử dụng liên hệ đã đăng ký trong hồ sơ cổ đông. Lần đầu: xác thực rồi gửi hồ sơ xác minh." },
};
const TU_VAI: Record<string, Man> = { "nhan-vien": "noi", "khach-hang": "kh", "doi-tac": "dt", "co-dong": "cd" };
function NoiBo() {
  const [u, setU] = useState(""); const [p, setP] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    // Vào VTOS bằng nạp lại trang, không đi bằng router: trang cổng nạp bảng kiểu riêng của v3.2,
    // nạp lại thì VTOS mở ra sạch, đúng giao diện của nó.
    try { await login(u.trim(), p); location.replace("/"); } catch (x: any) { setErr(x.message); setBusy(false); }
  }
  return (<form className="vtd-form" onSubmit={submit}>
    <h2>{VAI.noi.h2}</h2><p>{VAI.noi.p}</p>
    <label className="v3-field">Tài khoản<input value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" required /></label>
    <label className="v3-field">Mật khẩu<input type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" required /></label>
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy}>{busy ? "Đang vào…" : "Đăng nhập VTOS"}</button></div>
    <p className="vtd-form-notice">Quên mật khẩu thì liên hệ HCNS hoặc phòng CNTT để được đặt lại. Đăng nhập xong vào thẳng VTOS trong cùng tab.</p>
  </form>);
}

function Ngoai({ man }: { man: Exclude<Man, "cong" | "noi"> }) {
  const v = VAI[man];
  const [kenh, setKenh] = useState<any>(null);
  const [chon, setChon] = useState<"zalo" | "email">("zalo");
  const [lh, setLh] = useState(""); const [ma, setMa] = useState("");
  const [gui, setGui] = useState<any>(null);
  const [dongY, setDongY] = useState(false); const [canDongY, setCanDongY] = useState(false);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [con, setCon] = useState(0);
  useEffect(() => { goi("/kenh").then((k) => { setKenh(k); if (!k.zalo.ok && k.email.ok) setChon("email"); }).catch(() => setKenh({})); }, []);
  useEffect(() => { if (!gui) return; const t = setInterval(() => setCon((c) => Math.max(0, c - 1)), 1000); return () => clearInterval(t); }, [gui]);
  const guiMa = async () => {
    setBusy(true); setErr("");
    try { const r = await goi("/ma", { loai: v.loai, lien_he: lh, kenh: chon }); setGui(r); setCon(r.het_han_giay); setMa(""); setCanDongY(false); }
    catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  const xacThuc = async () => {
    setBusy(true); setErr("");
    try {
      const r = await goi("/xac-thuc", { khoa: gui.khoa, ma, dong_y_dieu_khoan: dongY });
      luuPhienCong(r.phien);
      location.replace("/cong");
    } catch (x: any) {
      if (x.ma === "can_dong_y") setCanDongY(true);
      if (x.ma === "ma_het") setGui(null);
      setErr(x.message); setBusy(false);
    }
  };
  const k = kenh || {};
  if (!gui) return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); guiMa(); }}>
    <h2>{v.h2}</h2><p>{v.p}</p>
    <fieldset className="kenh-otp"><legend>Nhận mã qua</legend>
      {(["zalo", "email"] as const).map((c) => <label key={c} className={k[c] && !k[c].ok ? "tat" : ""} title={k[c]?.ly_do || ""}>
        <input type="radio" name="kenh" checked={chon === c} disabled={!!k[c] && !k[c].ok} onChange={() => setChon(c)} />
        {c === "zalo" ? "Zalo" : "Email"} <small>{k[c] && !k[c].ok ? "chưa mở" : c === "zalo" ? "tới số điện thoại" : "tới hộp thư"}</small></label>)}
    </fieldset>
    {k[chon] && !k[chon].ok && <div className="cong-loi">Kênh {k[chon].ten} chưa mở: {k[chon].ly_do}.</div>}
    <label className="v3-field">{chon === "zalo" ? "Số điện thoại" : "Email"}
      <input value={lh} onChange={(e) => setLh(e.target.value)} inputMode={chon === "zalo" ? "tel" : "email"} autoComplete={chon === "zalo" ? "tel" : "email"}
        placeholder={chon === "zalo" ? "0912 345 678" : "ten@email.com"} required /></label>
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy || !lh.trim() || (!!k[chon] && !k[chon].ok)}>{busy ? "Đang gửi…" : "Nhận mã xác thực"}</button></div>
    <p className="vtd-form-notice">Mã 6 số, dùng một lần, hết hạn sau 5 phút. Lần đầu dùng liên hệ này thì hệ thống tạo tài khoản sau khi bạn đồng ý điều khoản dịch vụ{man !== "kh" ? "; đối tác và cổ đông gửi hồ sơ để Vietourist duyệt" : ""}.</p>
    {man === "cd" && <p className="vtd-form-notice"><a href="/login?cong=cd&xem=ir">Xem tài liệu công bố thông tin — không cần đăng nhập</a></p>}
  </form>);
  return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); xacThuc(); }}>
    <h2>Xác thực liên hệ</h2>
    <ol className="v3-steps"><li className="done"><span>✓</span><div>Thông tin</div></li><li className="active"><span>2</span><div>Xác thực</div></li><li className=""><span>3</span><div>Truy cập</div></li></ol>
    <p>{gui.message} {con > 0 ? <>Còn <b>{Math.floor(con / 60)}:{String(con % 60).padStart(2, "0")}</b>.</> : <b>Mã đã hết hạn.</b>}</p>
    <label className="v3-field">Mã xác thực<input value={ma} onChange={(e) => setMa(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" placeholder="••••••" required autoFocus /></label>
    {canDongY && <label className="cong-dong-y"><input type="checkbox" checked={dongY} onChange={(e) => setDongY(e.target.checked)} />
      <span>Tôi đồng ý điều khoản dịch vụ và chính sách bảo vệ dữ liệu cá nhân của Vietourist. (Không bao gồm nhận tin quảng cáo.)</span></label>}
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions">
      <button className="v3-button v3-primary cursor-interaction" disabled={busy || ma.length !== 6 || con <= 0 || (canDongY && !dongY)}>{busy ? "Đang xác thực…" : "Xác thực"}</button>
      <button type="button" className="v3-button v3-secondary cursor-interaction" disabled={busy} onClick={guiMa}>Gửi lại mã</button></div>
    <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => { setGui(null); setErr(""); }}>Đổi liên hệ / đổi kênh</button>
    <p className="vtd-form-notice">Vietourist không bao giờ hỏi mã này qua điện thoại. Sai 5 lần thì phải gửi lại mã mới.</p>
  </form>);
}

export default function Login() {
  const [man, setMan] = useState<Man>("cong");
  const [hoTro, setHoTro] = useState(false);
  const [xemIr, setXemIr] = useState(false);   // CD-1 · màn A18: thư viện IR công khai, không cần đăng nhập
  useEffect(() => {
    // CG-3: trên kh./dt./ir. bỏ qua và xóa phiên VTOS — tên miền cổng ngoài không mở VTOS.
    if (laTenMienCong()) clearSession();
    else if (getUser()) { location.replace("/"); return; }
    setXemIr(new URLSearchParams(location.search).get("xem") === "ir");
    const q = new URLSearchParams(location.search).get("cong") as Man | null;
    if (q === "noi" && laTenMienCong()) { location.replace(`${VTOS_GOC}/login`); return; }
    if (q && (q === "cong" || q in VAI)) setMan(q);
    else { const m = CONG_THEO_TEN_MIEN[location.hostname.toLowerCase()]; if (m) setMan(m); }
  }, []);
  const di = useCallback((m: Man) => {
    if (m === "noi" && laTenMienCong()) { location.href = `${VTOS_GOC}/login`; return; }   // CG-3: nội bộ chỉ ở crm.
    setMan(m); setHoTro(false); setXemIr(false); try { history.replaceState(null, "", m === "cong" ? "/login" : `/login?cong=${m}`); } catch { /* bỏ qua */ } window.scrollTo(0, 0); }, []);
  // Bấm vào mảnh tĩnh (thẻ vai, logo, nút Hỗ trợ): bắt bằng một chỗ, đọc data-* có sẵn trong bản v3.2.
  const bam = (e: React.MouseEvent) => {
    const nutBay = (e.target as HTMLElement).closest("[data-hero-motion]") as HTMLElement | null;
    if (nutBay) {   // v3.4: dừng / tiếp tục máy bay bay quanh Trái Đất
      e.preventDefault();
      const vung = nutBay.closest(".v5-earth-area"); const dung = !vung?.classList.contains("is-paused");
      vung?.classList.toggle("is-paused", dung);
      nutBay.setAttribute("aria-pressed", String(dung));
      nutBay.setAttribute("aria-label", dung ? "Tiếp tục hiệu ứng máy bay" : "Dừng hiệu ứng máy bay");
      const chu = nutBay.querySelector("span"); if (chu) chu.textContent = dung ? "Tiếp tục hiệu ứng" : "Dừng hiệu ứng";
      return;
    }
    const el = (e.target as HTMLElement).closest("[data-go-role],[data-action]") as HTMLElement | null;
    if (!el) return;
    e.preventDefault();
    if (el.dataset.action === "support") setHoTro(true);
    else if (el.dataset.action === "close-support") setHoTro(false);
    else if (el.dataset.goRole !== undefined) di(el.dataset.goRole ? TU_VAI[el.dataset.goRole] || "cong" : "cong");
  };
  const vai = man === "cong" ? null : VAI[man];
  const goc = man === "cong" ? KHUNG_HO_TRO : THANH_TREN;   // trang mở đầu v3.4 không có thanh trên riêng
  const thanh = hoTro ? goc.replace(' hidden=""', "") : goc;
  return (<>
    <link rel="stylesheet" href="/cong/vtd.css?v=39" />
    <div style={{ background: "#081826", minHeight: "100vh" }}>
      <div id="vtd-access" data-mode="inline" data-page={man === "cong" ? "home" : "login"} data-role={vai?.role || "khach-hang"} data-preview="off" data-vtos-screen="off" data-vtos-menu="closed">
        <div id="vtd-screen" onClick={bam}>
          <div style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: thanh }} />
          {man === "cong" ? <div style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: TRANG_MO_DAU }} />
            : <div data-role={vai!.role}><div className="v4-auth">
              <nav className="vtd-breadcrumb"><button type="button" className="v3-button v3-secondary cursor-interaction" data-go-role="">← Bốn cổng truy cập</button><span>{vai!.ten}</span></nav>
              {xemIr && man === "cd" ? <section className="v3-app" data-portal="co-dong"><main className="v3-main" style={{ maxWidth: 920, margin: "0 auto" }}>
                <div className="v3-page-head"><div><div className="v3-eyebrow">VTD • Quan hệ nhà đầu tư · công khai</div><h1>Công bố thông tin</h1></div>
                  <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => di("cd")}><span>Cổ đông đăng nhập</span></button></div>
                <ThuVien coPhien={false} /></main></section>
              : <main className="vtd-login">
                <div style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: CAU_CHUYEN[vai!.role] }} />
                {man === "noi" ? <NoiBo /> : <Ngoai key={man} man={man} />}
              </main>}</div></div>}
        </div>
      </div>
    </div>
  </>);
}
