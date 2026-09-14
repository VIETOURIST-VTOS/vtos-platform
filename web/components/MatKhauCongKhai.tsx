"use client";
/** MẬT KHẨU ĐÃ CÔNG KHAI — soát và buộc đổi.
 *
 * VÌ SAO CÓ Ô NÀY
 *
 * Đến 14/9/2026 trang đăng nhập của bản chạy trên internet công cộng còn liệt kê mười hai tài khoản
 * mẫu — trong đó có cả tài khoản quản trị cao nhất — dùng chung MỘT mật khẩu, và in luôn mật khẩu ấy
 * ra. Dòng chữ đó đã bỏ. Nhưng bỏ dòng chữ không đổi được mật khẩu của ai: những tài khoản ấy vẫn
 * đang dùng đúng chuỗi đã bị công bố.
 *
 * Bộ máy buộc đổi mật khẩu thì đã có sẵn và chạy đúng. Cái thiếu là KHÔNG AI BẬT CỜ. Ô này là cái
 * nút ấy — theo đúng ranh giới Chủ tịch chốt 09/9: có việc thì phải có cửa cho người bấm.
 *
 * NÓ KHÔNG ĐẶT MẬT KHẨU CHO AI. Chỉ hai việc: đếm xem còn ai dùng chuỗi đã công bố (so bản băm,
 * không đọc được mật khẩu của ai), và bật cờ để chính chủ tài khoản tự đổi ở lần đăng nhập kế tiếp.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";

type Soat = {
  tong_tai_khoan: number;
  con_mat_khau_cong_khai: number;
  da_buoc_doi: number;
  chua_buoc_doi: number;
  danh_sach: { username: string; ho_ten: string; role: string; da_buoc_doi: boolean }[];
  ghi_chu: string;
};

export default function MatKhauCongKhai({ canWrite }: { canWrite?: boolean }) {
  const [s, setS] = useState<Soat | null>(null);
  const [chay, setChay] = useState(false);
  const [loi, setLoi] = useState("");
  const [tin, setTin] = useState("");

  useEffect(() => { tai(); }, []);

  async function tai() {
    setLoi("");
    try { setS(await api<Soat>("/access/mat-khau/soat-cong-khai")); }
    catch (e) { setLoi(errMsg(e)); }
  }

  async function batCo() {
    if (!s) return;
    if (!confirm(
      `Buộc ${s.chua_buoc_doi} tài khoản đổi mật khẩu ở lần đăng nhập kế tiếp?\n\n` +
      `• Không tài khoản nào bị khoá\n` +
      `• Không mật khẩu nào bị đặt hộ — mỗi người tự đặt mật khẩu mới\n` +
      `• Cho tới khi đổi, họ chỉ vào được đúng màn hình đổi mật khẩu\n\n` +
      `Việc này ghi vào nhật ký kèm danh sách tài khoản.`
    )) return;
    setChay(true); setLoi(""); setTin("");
    try {
      const r = await api<any>("/access/mat-khau/buoc-doi",
        { method: "POST", json: { xac_nhan: true } });
      setTin(r.message); await tai();
    } catch (e) { setLoi(errMsg(e)); }
    finally { setChay(false); }
  }

  if (!s) return loi ? <p className="err">{loi}</p> : null;

  // Không còn ai thì nói một câu ngắn rồi thôi — ô này không phải thứ cần chiếm chỗ hằng ngày.
  if (s.con_mat_khau_cong_khai === 0) {
    return (
      <div className="card" style={{ marginBottom: 12 }}>
        <b>Mật khẩu công khai:</b>{" "}
        <span className="ok">không còn tài khoản nào dùng mật khẩu đã từng in trên trang đăng nhập.</span>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: "3px solid #b91c1c" }}>
      <b style={{ color: "#b91c1c" }}>
        {s.con_mat_khau_cong_khai} tài khoản còn dùng mật khẩu đã in công khai
      </b>
      <p className="muted" style={{ marginTop: 6 }}>
        Trang đăng nhập từng in tên tài khoản và mật khẩu dùng chung, trên địa chỉ ai trên internet
        cũng mở được. Dòng chữ ấy đã bỏ, nhưng <b>mật khẩu thì vẫn nguyên</b> cho tới khi từng người
        tự đổi. Bấm nút dưới đây là buộc họ đổi ở lần đăng nhập kế tiếp — không ai bị khoá, và không
        mật khẩu nào bị đặt hộ.
      </p>

      <table className="tbl" style={{ maxWidth: 560, marginBottom: 10 }}>
        <tbody>
          <tr><td>Tổng tài khoản đang hoạt động</td>
              <td style={{ textAlign: "right" }}>{s.tong_tai_khoan}</td></tr>
          <tr><td><b>Còn mật khẩu đã công khai</b></td>
              <td style={{ textAlign: "right" }}><b>{s.con_mat_khau_cong_khai}</b></td></tr>
          <tr><td>Trong đó đã bị buộc đổi</td>
              <td style={{ textAlign: "right" }}>{s.da_buoc_doi}</td></tr>
          <tr><td>Chưa bị buộc đổi</td>
              <td style={{ textAlign: "right" }}>{s.chua_buoc_doi}</td></tr>
        </tbody>
      </table>

      <details style={{ marginBottom: 10 }}>
        <summary className="muted">Xem danh sách</summary>
        <ul className="muted" style={{ marginTop: 6 }}>
          {s.danh_sach.map((x) => (
            <li key={x.username}>
              <b>{x.username}</b> — {x.ho_ten} ({x.role}){x.da_buoc_doi ? " · đã buộc đổi" : ""}
            </li>
          ))}
        </ul>
      </details>

      {loi && <p className="err">{loi}</p>}
      {tin && <p className="ok">{tin}</p>}

      {canWrite && s.chua_buoc_doi > 0 && (
        <button className="danger" disabled={chay} onClick={batCo}>
          {chay ? "Đang bật…" : `Buộc ${s.chua_buoc_doi} tài khoản đổi mật khẩu`}
        </button>
      )}
    </div>
  );
}
