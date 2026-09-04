"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { login, getUser } from "@/lib/api";

export default function Login() {
  const [u, setU] = useState("dh.lan"); const [p, setP] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const router = useRouter();
  useEffect(() => { if (getUser()) router.replace("/"); }, [router]);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    try { await login(u.trim(), p); router.replace("/"); } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  }
  return (
    <main style={{ maxWidth: 420, margin: "40px auto" }}>
      <div className="panel">
        <h1>Đăng nhập VTOS</h1>
        <form onSubmit={submit}>
          <label>Tài khoản</label><input value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" />
          <label>Mật khẩu</label><input type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" />
          {err && <div className="gate fail">{err}</div>}
          <button className="act teal" disabled={busy} style={{ marginTop: 12 }}>{busy ? "Đang vào…" : "Vào hệ thống"}</button>
        </form>
        <p className="muted">Bản chạy thử: các tài khoản mẫu (chutich, tgd, ptgd.doan, tp.dieuhanh, dh.lan, dh.minh, kd.hoa, kd.tuan, ketoan, hcns, cntt, bks) dùng mật khẩu <b>123456</b>. Đổi trước khi chạy thật.</p>
      </div>
    </main>
  );
}
