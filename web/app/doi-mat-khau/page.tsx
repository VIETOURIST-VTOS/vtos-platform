"use client";
import { useCallback, useEffect, useState } from "react";
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

  // ── Nối Zalo (19/9/2026) ──
  // Cảnh báo khủng hoảng phải tới được NGƯỜI, không chỉ tới màn hình. Hàm gửi tin OA cần một UID
  // Zalo, mà VTOS không có chỗ nào giữ UID. Chiều nối cố ý NGƯỢC với trực giác: người tự xin một
  // mã ở đây rồi tự nhắn mã ấy vào OA công ty — Zalo nói cho máy chủ biết UID, không ai phải gõ
  // nó, nên không tồn tại đường nào để nối nhầm UID người này vào tài khoản người kia.
  const [zl, setZl] = useState<any>({ da_noi: false, duoi_uid: "" });
  const [zlMa, setZlMa] = useState<any>(null);
  const napZl = useCallback(async () => {
    try { setZl(await api<any>("/zalo/trang-thai-noi")); } catch { /* chưa nối thì thôi */ }
  }, []);
  useEffect(() => { napZl(); }, [napZl]);
  const xinMa = async () => {
    try { setZlMa(await api<any>("/zalo/ma-noi", { method: "POST" })); }
    catch (e) { toast(errMsg(e), true); }
  };
  const goNoi = async () => {
    try { toast((await api<any>("/zalo/noi", { method: "DELETE" })).message); setZlMa(null); await napZl(); }
    catch (e) { toast(errMsg(e), true); }
  };

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

    <h2 style={{ marginTop: 22 }}>Nhận cảnh báo qua Zalo</h2>
    <div className="card" style={{ maxWidth: 460 }}>
      {zl.da_noi
        ? <>
            <p>Tài khoản này <b>đã nối</b> với một Zalo (…{zl.duoi_uid}). Cảnh báo của hệ thống sẽ
              gửi về máy đó.</p>
            <p className="muted">Đổi máy hoặc mất máy thì gỡ nối ngay: máy cũ vẫn nhận cảnh báo của
              công ty cho tới khi được gỡ.</p>
            <button className="act grey" onClick={goNoi}>Gỡ nối Zalo</button>
          </>
        : <>
            <p>Chưa nối. Cảnh báo khủng hoảng sẽ <b>không</b> gửi tới Zalo của anh/chị.</p>
            <button className="act" onClick={xinMa}>Lấy mã nối</button>
          </>}
      {zlMa && <div style={{ marginTop: 12 }}>
        <p>Mở Zalo → vào OA <b>Công ty cổ phần Vietourist Holdings</b> → nhắn đúng mã này:</p>
        <p className="mono" style={{ fontSize: "1.6rem", letterSpacing: "0.18em" }}>{zlMa.ma}</p>
        <p className="muted">Mã sống {zlMa.song_phut} phút (đến {zlMa.het_han}), dùng một lần.
          Nhắn xong Zalo sẽ trả lời xác nhận. Không đưa mã này cho ai — người cầm mã sẽ nhận cảnh
          báo thay anh/chị.</p>
        <button className="act grey" onClick={() => { setZlMa(null); napZl(); }}>Tôi đã nhắn xong</button>
      </div>}
    </div>
  </>;
}

// Bọc trong Shell: không bọc thì trang chạy NGOÀI khung – mất thanh điều hướng, và tệ hơn là
// useShell() trả user rỗng nên mọi nút theo vai trò lặng lẽ biến mất mà không báo lỗi gì.
export default function Page() { return <Shell><DoiMatKhau /></Shell>; }
