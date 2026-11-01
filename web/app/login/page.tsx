"use client";
import { useState, useEffect, useCallback } from "react";
import { login, getUser, clearSession } from "@/lib/api";
import { THANH_TREN, TRANG_MO_DAU, KHUNG_HO_TRO, CAU_CHUYEN } from "@/components/cong/manh";
import { ThuVien } from "@/components/cong/co-dong/CoDong";
import { goiCong as goi, luuPhienCong, laTenMienCong, VTOS_GOC, dauMay, luuDauMay, xoaDauMay } from "@/lib/cong";

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

/* DK-3 · MÀN ĐĂNG NHẬP MỚI — Chủ tịch chốt 01/11/2026, sáu điều.

   Điều 5: KHÔNG có cửa đăng nhập bằng mã một lần. Màn này không còn nút «Nhận mã xác thực» để
   vào thẳng. Mã một lần chỉ xuất hiện ở ba chỗ, và ở cả ba nó là LỚP THỨ HAI chứ không bao giờ
   là lớp duy nhất: bước cuối khi TẠO tài khoản, bước xác minh MÁY LẠ (sau khi mật khẩu đã đúng),
   và bước ĐẶT LẠI mật khẩu.

   Điều 6: mật khẩu từ 5 ký tự, không bắt viết hoa. Bù lại, vào từ máy lạ thì phải gõ thêm mã;
   máy đã quen thì vào thẳng, nhớ 90 ngày. Dấu nhớ máy cất ở `vtd_cong_may:<cổng>` — mỗi cổng một
   dấu riêng, vì mỗi cổng là một tài khoản riêng.

   TÀI KHOẢN CŨ chưa có mật khẩu (tạo trước DK-1, hồi cổng còn đăng nhập bằng mã) vẫn đăng nhập
   được — qua «Quên mật khẩu» để đặt mật khẩu lần đầu. Màn này NÓI RA điều đó, vì không nói thì
   khách cũ gõ mãi không vào và không hiểu vì sao. */
type Buoc = "vao" | "may" | "quen1" | "quen2" | "tao1" | "tao2" | "tao3" | "tao4";

function DongHoMa({ con }: { con: number }) {
  if (con <= 0) return <b>Mã đã hết hạn.</b>;
  return <>Còn <b>{Math.floor(con / 60)}:{String(con % 60).padStart(2, "0")}</b>.</>;
}

function ChonKenh({ k, chon, dat }: { k: any; chon: "zalo" | "email"; dat: (c: "zalo" | "email") => void }) {
  return (<fieldset className="kenh-otp"><legend>Nhận mã qua</legend>
    {(["zalo", "email"] as const).map((c) => <label key={c} className={k[c] && !k[c].ok ? "tat" : ""} title={k[c]?.ly_do || ""}>
      <input type="radio" name="kenh" checked={chon === c} disabled={!!k[c] && !k[c].ok} onChange={() => dat(c)} />
      {c === "zalo" ? "Zalo" : "Email"} <small>{k[c] && !k[c].ok ? "chưa mở" : c === "zalo" ? "tới số điện thoại" : "tới hộp thư"}</small></label>)}
  </fieldset>);
}

function Ngoai({ man }: { man: Exclude<Man, "cong" | "noi"> }) {
  const v = VAI[man];
  const [buoc, setBuoc] = useState<Buoc>("vao");
  const [kenh, setKenh] = useState<any>(null);
  const [chon, setChon] = useState<"zalo" | "email">("zalo");
  const [lh, setLh] = useState(""); const [mk, setMk] = useState(""); const [hien, setHien] = useState(false);
  const [ma, setMa] = useState(""); const [gui, setGui] = useState<any>(null); const [con, setCon] = useState(0);
  const [don, setDon] = useState<any>(null);            // đơn đăng ký tạm (bốn bước)
  const [hoTen, setHoTen] = useState(""); const [dt, setDt] = useState(""); const [em, setEm] = useState("");
  const [dongY, setDongY] = useState(false); const [quangCao, setQuangCao] = useState(false);
  const [nhoMay, setNhoMay] = useState(true); const [tenMay, setTenMay] = useState("");
  const [err, setErr] = useState(""); const [tin, setTin] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { goi("/kenh").then((k) => { setKenh(k); if (!k.zalo.ok && k.email.ok) setChon("email"); }).catch(() => setKenh({})); }, []);
  useEffect(() => { if (!gui) return; const t = setInterval(() => setCon((c) => Math.max(0, c - 1)), 1000); return () => clearInterval(t); }, [gui]);
  const k = kenh || {};
  const sang = (b: Buoc) => { setBuoc(b); setErr(""); setTin(""); setMa(""); window.scrollTo(0, 0); };
  const xong = (r: any) => { luuPhienCong(r.phien); location.replace(veSauDangNhap()); };
  const chay = async (f: () => Promise<void>) => {
    setBusy(true); setErr("");
    try { await f(); } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };

  // ── vào: liên hệ + MẬT KHẨU. Không có nút nào gửi mã để vào thẳng. ──────────────────────────
  const vao = () => chay(async () => {
    const r = await goi("/dang-nhap", { loai: v.loai, lien_he: lh, mat_khau: mk, dau_nho: dauMay(v.loai), kenh: chon });
    if (r.xong) { xong(r); return; }
    setGui(r); setCon(r.het_han_giay || 600); sang("may");       // máy lạ: còn một lớp nữa
  });
  const xacMinhMay = () => chay(async () => {
    const r = await goi("/dang-nhap/xac-minh", { khoa: gui.khoa, ma, nho_may: nhoMay, ten_may: tenMay });
    if (nhoMay && r.dau_nho) luuDauMay(v.loai, r.dau_nho);
    xong(r);
  });

  // ── quên mật khẩu: câu trả lời KHÔNG đổi dù liên hệ có tài khoản hay không ──────────────────
  const quenGui = () => chay(async () => {
    const r = await goi("/quen-mat-khau/ma", { loai: v.loai, lien_he: lh, kenh: chon });
    setGui(r); setCon(r.het_han_giay || 600); sang("quen2"); setTin(r.message);
  });
  const quenDat = () => chay(async () => {
    await goi("/quen-mat-khau/dat-lai", { khoa: gui.khoa, ma, mat_khau: mk });
    xoaDauMay(v.loai);                                            // đổi mật khẩu là quên sạch máy
    setGui(null); setMk(""); sang("vao");
    setTin("Đã đặt mật khẩu mới. Mọi phiên và mọi máy đã nhớ đều bị đăng xuất — đăng nhập lại bằng mật khẩu vừa đặt.");
  });

  // ── tạo tài khoản: BỐN BƯỚC, mã ở bước CUỐI ────────────────────────────────────────────────
  const tao1 = () => chay(async () => { setDon(await goi("/dang-ky/lien-he", { loai: v.loai, ho_ten: hoTen, dien_thoai: dt, email: em })); sang("tao2"); });
  const tao2 = () => chay(async () => { await goi("/dang-ky/mat-khau", { khoa: don.khoa, mat_khau: mk }); sang("tao3"); });
  const tao3 = () => chay(async () => { await goi("/dang-ky/dieu-khoan", { khoa: don.khoa, dong_y_dieu_khoan: dongY, nhan_tin_quang_cao: quangCao }); sang("tao4"); });
  const taoGuiMa = () => chay(async () => { const r = await goi("/dang-ky/ma", { khoa: don.khoa, kenh: chon }); setGui(r); setCon(r.het_han_giay || 600); setMa(""); });
  const taoXong = () => chay(async () => { xong(await goi("/dang-ky/xong", { khoa: don.khoa, ma })); });

  const oMa = (<label className="v3-field">Mã xác thực
    <input value={ma} onChange={(e) => setMa(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric"
      autoComplete="one-time-code" placeholder="••••••" required autoFocus /></label>);
  const oMatKhau = (nhan: string) => (<label className="v3-field">{nhan}
    <span style={{ position: "relative", display: "block" }}>
      <input type={hien ? "text" : "password"} value={mk} onChange={(e) => setMk(e.target.value)}
        autoComplete={buoc === "vao" ? "current-password" : "new-password"} required />
      <button type="button" className="v3-button v3-secondary cursor-interaction" style={{ position: "absolute", right: 4, top: 4, padding: "2px 10px" }}
        onClick={() => setHien(!hien)}>{hien ? "Ẩn" : "Hiện"}</button></span></label>);

  // ══ 1 · ĐĂNG NHẬP ═══════════════════════════════════════════════════════════════════════════
  if (buoc === "vao") return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); vao(); }}>
    <h2>{v.h2}</h2><p>{v.p}</p>
    <label className="v3-field">Số điện thoại hoặc email
      <input value={lh} onChange={(e) => setLh(e.target.value)} inputMode="email" autoComplete="username"
        placeholder="0912 345 678 hoặc ten@email.com" required /></label>
    {oMatKhau("Mật khẩu")}
    <div style={{ textAlign: "right", marginTop: -6 }}>
      <button type="button" className="vtd-text-button cursor-interaction" onClick={() => sang("quen1")}>Quên mật khẩu?</button></div>
    {tin && <p className="vtd-form-notice">{tin}</p>}
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy || !lh.trim() || !mk}>{busy ? "Đang vào…" : "Đăng nhập"}</button></div>
    <p className="vtd-form-notice"><b>Chỉ một cửa vào: mật khẩu.</b> Mã một lần không bao giờ thay được mật khẩu — nó chỉ là lớp thứ hai khi bạn vào từ máy lạ.</p>
    <p className="vtd-form-notice">Tài khoản cũ chưa có mật khẩu? Trước đây cổng đăng nhập bằng mã một lần. Bấm <b>Quên mật khẩu</b> để đặt mật khẩu lần đầu cho tài khoản ấy.</p>
    <div className="v4-actions"><button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => sang("tao1")}>Chưa có tài khoản · Tạo tài khoản</button></div>
  </form>);

  // ══ 2 · MÁY LẠ — mật khẩu đã đúng, còn một lớp nữa ══════════════════════════════════════════
  if (buoc === "may") return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); xacMinhMay(); }}>
    <h2>Mật khẩu đúng rồi. Chưa nhận ra máy này.</h2>
    <p>{gui?.message} <DongHoMa con={con} /></p>
    {oMa}
    <label className="cong-dong-y"><input type="checkbox" checked={nhoMay} onChange={(e) => setNhoMay(e.target.checked)} />
      <span>Nhớ máy này <b>90 ngày</b> — lần sau chỉ cần mật khẩu. Đừng chọn nếu đây là máy tiệm net hay máy mượn.</span></label>
    {nhoMay && <label className="v3-field">Đặt tên cho máy này <span style={{ fontWeight: 400 }}>· không bắt buộc</span>
      <input value={tenMay} onChange={(e) => setTenMay(e.target.value.slice(0, 80))} placeholder="Điện thoại của tôi" /></label>}
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions">
      <button className="v3-button v3-primary cursor-interaction" disabled={busy || ma.length !== 6 || con <= 0}>{busy ? "Đang xác minh…" : "Xác minh và vào"}</button>
      <button type="button" className="v3-button v3-secondary cursor-interaction" disabled={busy} onClick={vao}>Gửi lại mã</button></div>
    <p className="vtd-form-notice">Không phải bạn đang đăng nhập? Có người đã biết mật khẩu của bạn — <button type="button" className="vtd-text-button cursor-interaction" onClick={() => sang("quen1")}>đổi mật khẩu ngay</button>. Đổi xong mọi máy đã nhớ đều bị quên.</p>
    <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => { setGui(null); sang("vao"); }}>Quay lại</button>
  </form>);

  // ══ 3 · QUÊN MẬT KHẨU ═══════════════════════════════════════════════════════════════════════
  if (buoc === "quen1") return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); quenGui(); }}>
    <h2>Đặt lại mật khẩu</h2><p>Vietourist không có tên đăng nhập riêng, nên không có gì để quên ngoài mật khẩu.</p>
    <ChonKenh k={k} chon={chon} dat={setChon} />
    <label className="v3-field">{chon === "zalo" ? "Số điện thoại" : "Email"}
      <input value={lh} onChange={(e) => setLh(e.target.value)} inputMode={chon === "zalo" ? "tel" : "email"} autoComplete="username" required /></label>
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy || !lh.trim()}>{busy ? "Đang gửi…" : "Gửi mã đặt lại"}</button></div>
    <p className="vtd-form-notice">Máy luôn trả lời một câu duy nhất, dù liên hệ này có tài khoản hay không — nói ra là biến màn này thành máy dò xem ai là khách của Vietourist.</p>
    <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => sang("vao")}>Tôi nhớ ra rồi · quay lại</button>
  </form>);

  if (buoc === "quen2") return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); quenDat(); }}>
    <h2>Mã và mật khẩu mới</h2>
    <p>{tin} <DongHoMa con={con} /></p>
    {oMa}
    {oMatKhau("Mật khẩu mới")}
    <p className="vtd-form-notice">Từ <b>5 ký tự</b>. Không bắt viết hoa, không bắt trộn số hay ký hiệu. Chỉ không được trùng danh sách mật khẩu đã bị lộ.</p>
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions">
      <button className="v3-button v3-primary cursor-interaction" disabled={busy || ma.length !== 6 || !mk || con <= 0}>{busy ? "Đang đặt…" : "Đặt mật khẩu mới"}</button>
      <button type="button" className="v3-button v3-secondary cursor-interaction" disabled={busy} onClick={quenGui}>Gửi lại mã</button></div>
    <p className="vtd-form-notice">Đặt xong, <b>mọi phiên đang mở ở máy khác đều bị đăng xuất</b> và <b>mọi máy đã nhớ đều bị quên</b>.</p>
  </form>);

  // ══ 4 · TẠO TÀI KHOẢN — bốn bước, mã ở bước CUỐI ════════════════════════════════════════════
  const buocSo = buoc === "tao1" ? 1 : buoc === "tao2" ? 2 : buoc === "tao3" ? 3 : 4;
  const thanhBuoc = (<ol className="v3-steps">{["Liên hệ", "Mật khẩu", "Điều khoản", "Mã xác thực"].map((t, i) =>
    <li key={t} className={i + 1 < buocSo ? "done" : i + 1 === buocSo ? "active" : ""}><span>{i + 1 < buocSo ? "✓" : i + 1}</span><div>{t}</div></li>)}</ol>);

  if (buoc === "tao1") return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); tao1(); }}>
    <h2>Tạo tài khoản {v.ten}</h2>{thanhBuoc}
    <p>Số điện thoại hoặc email này sẽ là tên đăng nhập của bạn. Chưa gửi mã ở bước này.</p>
    <label className="v3-field">Họ và tên<input value={hoTen} onChange={(e) => setHoTen(e.target.value)} autoComplete="name" required /></label>
    <label className="v3-field">Số điện thoại<input value={dt} onChange={(e) => setDt(e.target.value)} inputMode="tel" autoComplete="tel" placeholder="0912 345 678" /></label>
    <label className="v3-field">Email <span style={{ fontWeight: 400 }}>· không bắt buộc</span>
      <input value={em} onChange={(e) => setEm(e.target.value)} inputMode="email" autoComplete="email" placeholder="ten@email.com" /></label>
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy || !hoTen.trim() || (!dt.trim() && !em.trim())}>{busy ? "Đang lưu…" : "Tiếp tục"}</button></div>
    <p className="vtd-form-notice">Máy chưa trả lời số này đã có tài khoản hay chưa. Nói ra là để người lạ dò được ai là khách của Vietourist; nếu số đã có, bước 4 sẽ nhắn cho chủ số, không nhắn cho người đang gõ.</p>
    <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => sang("vao")}>Đã có tài khoản · Đăng nhập</button>
  </form>);

  if (buoc === "tao2") return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); tao2(); }}>
    <h2>Đặt mật khẩu</h2>{thanhBuoc}
    <p>Một câu bạn nhớ được dễ hơn một mớ ký hiệu — và khó đoán hơn nhiều.</p>
    {oMatKhau("Mật khẩu")}
    <p className="vtd-form-notice">Từ <b>5 ký tự</b>, tối đa 64. Dấu cách và chữ có dấu đều dùng được. <b>Không bắt viết hoa</b>, không bắt trộn số hay ký hiệu — bắt trộn chỉ làm người ta viết ra giấy.</p>
    <p className="vtd-form-notice">Đặt dưới 15 ký tự vẫn được. Nhưng khi đăng nhập từ <b>máy lạ</b>, Vietourist sẽ hỏi thêm một mã. Máy bạn hay dùng thì vào thẳng.</p>
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy || !mk}>{busy ? "Đang lưu…" : "Tiếp tục"}</button></div>
    <p className="vtd-form-notice">Vietourist <b>không bao giờ</b> bắt bạn đổi mật khẩu định kỳ, và không hỏi câu hỏi bí mật.</p>
  </form>);

  if (buoc === "tao3") return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); tao3(); }}>
    <h2>Điều khoản dịch vụ</h2>{thanhBuoc}
    <label className="cong-dong-y"><input type="checkbox" checked={dongY} onChange={(e) => setDongY(e.target.checked)} />
      <span>Tôi đồng ý điều khoản dịch vụ và chính sách bảo vệ dữ liệu cá nhân của Vietourist.</span></label>
    <label className="cong-dong-y"><input type="checkbox" checked={quangCao} onChange={(e) => setQuangCao(e.target.checked)} />
      <span>Nhận tin ưu đãi từ Vietourist. <b>Không bắt buộc</b> — bỏ trống vẫn tạo được tài khoản.</span></label>
    {err && <div className="cong-loi">{err}</div>}
    <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy || !dongY}>{busy ? "Đang lưu…" : "Tiếp tục"}</button></div>
    <p className="vtd-form-notice">Ô nhận tin ưu đãi mặc định TẮT và không bao giờ tự bật.</p>
  </form>);

  return (<form className="vtd-form" onSubmit={(e) => { e.preventDefault(); if (gui) { taoXong(); } else { taoGuiMa(); } }}>
    <h2>Mã xác thực</h2>{thanhBuoc}
    <p><b>Đây là bước cuối — và là bước tạo ra tài khoản thật.</b> Ba bước trước chưa dựng tài khoản nào; tất cả đang nằm trong một đơn đăng ký tạm, hết hạn sau 24 giờ.</p>
    {!gui ? (<>
      <ChonKenh k={k} chon={chon} dat={setChon} />
      {k[chon] && !k[chon].ok && <div className="cong-loi">Kênh {k[chon].ten} chưa mở: {k[chon].ly_do}.</div>}
      {err && <div className="cong-loi">{err}</div>}
      <div className="v4-actions"><button className="v3-button v3-primary cursor-interaction" disabled={busy || (!!k[chon] && !k[chon].ok)}>{busy ? "Đang gửi…" : "Gửi mã xác thực"}</button></div>
    </>) : (<>
      <p>{gui.message} <DongHoMa con={con} /></p>
      {oMa}
      {err && <div className="cong-loi">{err}</div>}
      <div className="v4-actions">
        <button className="v3-button v3-primary cursor-interaction" disabled={busy || ma.length !== 6 || con <= 0}>{busy ? "Đang tạo…" : "Xác thực và tạo tài khoản"}</button>
        <button type="button" className="v3-button v3-secondary cursor-interaction" disabled={busy} onClick={taoGuiMa}>Gửi lại mã</button></div>
    </>)}
    <p className="vtd-form-notice">Vietourist không bao giờ hỏi mã này qua điện thoại. Sai 5 lần thì phải gửi lại mã mới.</p>
    {man !== "kh" && <p className="vtd-form-notice">Tạo xong, {man === "dt" ? "đối tác" : "cổ đông"} còn một bước nữa: khai hồ sơ để Vietourist duyệt. Vào xem được ngay, chưa giao dịch được.</p>}
  </form>);
}

/* KS-16q: /login?ve=/hotel/12 — chỉ nhận đường dẫn trang riêng cùng tên miền (không mở chuyển hướng ra ngoài). Ghi vào
   sessionStorage vì màn đăng nhập tự đổi địa chỉ khi chọn loại tài khoản. */
const VE_HOP_LE = /^\/(kham-pha\/)?(hotel|restaurant|tours)(\/\d+)?(\?[^#]*)?$/;
function veSauDangNhap(): string {
  try { const v = sessionStorage.getItem("vtd_ve") || ""; sessionStorage.removeItem("vtd_ve"); if (VE_HOP_LE.test(v)) return v; } catch { /* bỏ qua */ }
  return "/cong";
}

export default function Login() {
  const [man, setMan] = useState<Man>("cong");
  const [hoTro, setHoTro] = useState(false);
  const [xemIr, setXemIr] = useState(false);   // CD-1 · màn A18: thư viện IR công khai, không cần đăng nhập
  useEffect(() => {
    // CG-3: trên kh./dt./ir. bỏ qua và xóa phiên VTOS — tên miền cổng ngoài không mở VTOS.
    if (laTenMienCong()) clearSession();
    else if (getUser()) { location.replace("/"); return; }
    try { const ve = new URLSearchParams(location.search).get("ve") || ""; if (VE_HOP_LE.test(ve)) sessionStorage.setItem("vtd_ve", ve); } catch { /* bỏ qua */ }
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
