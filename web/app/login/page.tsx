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
{/* KHÔNG in tên tài khoản và mật khẩu lên trang này.
            Đến 14/9/2026 chỗ này còn liệt kê mười hai tài khoản mẫu — trong đó có cả tài khoản
            quản trị cao nhất — dùng chung MỘT mật khẩu, và in luôn mật khẩu ấy ra, trên một trang
            ai trên internet cũng mở được. Khi hệ chỉ có dữ liệu chạy thử thì chưa mất gì; từ lúc
            nhận số thật (doanh thu, giá vốn, danh sách khách, doanh số từng người) thì một dòng chữ
            ở đây là một cánh cửa mở. Mật khẩu tạm đưa cho người dùng bằng đường riêng, không dán
            lên cửa — và `tests/test_mat_khau_cong_khai.py` đọc thẳng tệp này để canh. */}
        <p className="muted">
          Quên mật khẩu thì liên hệ HCNS hoặc phòng CNTT để được đặt lại. Mật khẩu đặt lại là mật
          khẩu <b>tạm</b> – lần đăng nhập kế tiếp hệ thống buộc đổi trước khi vào được màn hình nào.
        </p>
      </div>
    </main>
  );
}
