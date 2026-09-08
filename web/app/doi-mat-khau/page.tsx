"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import { api, getUser, setSession, getToken } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** Đổi mật khẩu. Bắt buộc với tài khoản còn mật khẩu TẠM do HCNS/CNTT đặt (chỉ đạo 07/9/2026):
 *  mật khẩu mặc định là mã nhân viên, mà mã nhân viên nằm công khai trên bảng lương và danh bạ –
 *  ai biết mã là đăng nhập được người khác, và mọi thao tác sau đó mang tên người bị mượn. */
function DoiMatKhau() {
  const { user, toast } = useShell();
  const router = useRouter();
  const buoc = !!user?.must_change_password;
  const [cu, setCu] = useState("");
  const [moi, setMoi] = useState("");
  const [lai, setLai] = useState("");
  const [dangGui, setDangGui] = useState(false);

  const luu = async () => {
    if (moi !== lai) { toast("Hai ô mật khẩu mới không giống nhau", true); return; }
    if (moi.length < 6) { toast("Mật khẩu mới phải từ 6 ký tự", true); return; }
    setDangGui(true);
    try {
      await api("/auth/password", { method: "POST", json: { old_password: cu, new_password: moi } });
      // làm mới phiên: máy chủ đã gỡ cờ buộc đổi, giao diện phải biết để mở lại menu
      const me = await api<any>("/auth/me");
      const tok = getToken(); if (tok) setSession(tok, me);
      toast("Đã đổi mật khẩu");
      router.replace("/");
      router.refresh();
    } catch (e) { toast(errMsg(e), true); } finally { setDangGui(false); }
  };

  return <>
    <h1>Đổi mật khẩu</h1>
    {buoc && <div className="gate fail" style={{ marginBottom: 12 }}>
      <b>Tài khoản đang dùng mật khẩu tạm.</b> Mật khẩu này do HCNS hoặc CNTT đặt và bằng mã nhân viên của anh/chị –
      người khác biết mã là đăng nhập được. Đổi mật khẩu rồi mới vào được các màn hình khác.
    </div>}
    <div className="card" style={{ maxWidth: 460 }}>
      <label>Mật khẩu hiện tại<input type="password" value={cu} onChange={(e) => setCu(e.target.value)} autoComplete="current-password" /></label>
      <label>Mật khẩu mới (từ 6 ký tự)<input type="password" value={moi} onChange={(e) => setMoi(e.target.value)} autoComplete="new-password" /></label>
      <label>Nhập lại mật khẩu mới<input type="password" value={lai} onChange={(e) => setLai(e.target.value)} autoComplete="new-password" /></label>
      <button className="act" disabled={dangGui || !cu || !moi} onClick={luu}>{dangGui ? "Đang lưu…" : "Đổi mật khẩu"}</button>
      <p className="muted" style={{ marginTop: 10 }}>Không đặt mật khẩu bằng mã nhân viên: mã đó có trên bảng lương và danh bạ nội bộ.</p>
    </div>
  </>;
}

// Bọc trong Shell: không bọc thì trang chạy NGOÀI khung – mất thanh điều hướng, và tệ hơn là
// useShell() trả user rỗng nên mọi nút theo vai trò lặng lẽ biến mất mà không báo lỗi gì.
export default function Page() { return <Shell><DoiMatKhau /></Shell>; }
