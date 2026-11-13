"use client";
/** TÀI KHOẢN CHƯA TỪNG ĐĂNG NHẬP — mật khẩu còn nguyên như lúc gieo.
 *
 * VÌ SAO CÓ Ô NÀY
 *
 * Đến 14/9/2026 trang đăng nhập của bản chạy trên internet công cộng còn liệt kê mười hai tài khoản
 * mẫu — trong đó có cả tài khoản quản trị cao nhất — dùng chung MỘT mật khẩu, và in luôn mật khẩu ấy
 * ra. Dòng chữ đó đã bỏ. Nhưng bỏ dòng chữ không đổi được mật khẩu của ai.
 *
 * Bộ máy buộc đổi mật khẩu thì đã có sẵn và chạy đúng. Cái thiếu là KHÔNG AI BẬT CỜ. Ô này là cái
 * nút ấy — theo đúng ranh giới Chủ tịch chốt 09/9: có việc thì phải có cửa cho người bấm.
 *
 * NÓ CHỈ LO NỬA BÀI TOÁN, VÀ ĐÓ LÀ CỐ Ý
 *
 * Người CÓ dùng tài khoản thì chính cửa đăng nhập bắt: lúc ấy máy cầm sẵn mật khẩu họ vừa gõ nên chỉ
 * cần so chuỗi, không tốn gì, và bật cờ ngay tại chỗ. Ô này lo nửa còn lại — những tài khoản chưa ai
 * động vào từ lúc gieo, nên cửa đăng nhập không với tới.
 *
 * BẢN ĐẦU CỦA Ô NÀY ĐI QUÉT VÀ ĐÃ LÀM TREO MÀN HÌNH: nó băm lại từng tài khoản một để đoán ai còn
 * dùng chuỗi đã công bố. bcrypt chậm là cố ý; 116 tài khoản thật là hơn hai phút, mỗi lần mở màn
 * hình. Giờ ô này không băm một lần nào.
 *
 * NÓ KHÔNG ĐẶT MẬT KHẨU CHO AI. Chỉ bật cờ để chính chủ tài khoản tự đổi ở lần đăng nhập đầu tiên.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

type Soat = {
  tong_tai_khoan: number;
  dang_buoc_doi: number;
  chua_tung_dang_nhap: number;
  danh_sach: { username: string; ho_ten: string; role: string }[];
  ghi_chu: string;
};

export default function MatKhauCongKhai({ canWrite }: { canWrite?: boolean }) {
  const { xacNhan, nhap, hop } = useHoi();
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
    if (!await xacNhan(
      `Buộc ${s.chua_tung_dang_nhap} tài khoản chưa từng đăng nhập phải đổi mật khẩu ở lần đăng nhập đầu tiên?\n\n` +
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
  if (s.chua_tung_dang_nhap === 0) {
    return (
      <div className="card" style={{ marginBottom: 12 }}>
        <b>Mật khẩu ban đầu:</b>{" "}
        <span className="ok">
          mọi tài khoản đang hoạt động đều đã từng đăng nhập — không còn tài khoản nào nằm nguyên với
          mật khẩu lúc gieo.
        </span>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: "3px solid var(--vtos-danger)" }}>{hop}
      <b style={{ color: "var(--vtos-danger)" }}>
        {s.chua_tung_dang_nhap} tài khoản chưa từng đăng nhập — mật khẩu còn nguyên như lúc gieo
      </b>
      <p className="muted" style={{ marginTop: 6 }}>
        Trang đăng nhập từng in tên tài khoản và mật khẩu dùng chung, trên địa chỉ ai trên internet
        cũng mở được. Dòng chữ ấy đã bỏ, nhưng <b>mật khẩu thì vẫn nguyên</b> với những tài khoản
        chưa ai động vào. Bấm nút dưới đây là buộc họ đổi ở lần đăng nhập đầu tiên — không ai bị
        khoá, và không mật khẩu nào bị đặt hộ.
      </p>
      <p className="muted" style={{ marginTop: 6 }}>
        Những tài khoản <b>đã từng đăng nhập</b> không cần nút này: ai còn dùng mật khẩu đã công bố
        thì máy nhận ra ngay ở lần đăng nhập kế tiếp của chính họ và bật cờ tại chỗ.
      </p>

      <table className="tbl" style={{ maxWidth: 560, marginBottom: 10 }}>
        <tbody>
          <tr><td>Tổng tài khoản đang hoạt động</td>
              <td style={{ textAlign: "right" }}>{s.tong_tai_khoan}</td></tr>
          <tr><td><b>Chưa từng đăng nhập</b></td>
              <td style={{ textAlign: "right" }}><b>{s.chua_tung_dang_nhap}</b></td></tr>
          <tr><td>Đang bị buộc đổi mật khẩu</td>
              <td style={{ textAlign: "right" }}>{s.dang_buoc_doi}</td></tr>
        </tbody>
      </table>

      <details style={{ marginBottom: 10 }}>
        <summary className="muted">Xem danh sách</summary>
        <ul className="muted" style={{ marginTop: 6 }}>
          {s.danh_sach.map((x) => (
            <li key={x.username}><b>{x.username}</b> — {x.ho_ten} ({x.role})</li>
          ))}
        </ul>
      </details>

      {loi && <p className="err">{loi}</p>}
      {tin && <p className="ok">{tin}</p>}

      {canWrite && (
        <button className="danger" disabled={chay} onClick={batCo}>
          {chay ? "Đang bật…" : `Buộc ${s.chua_tung_dang_nhap} tài khoản đổi mật khẩu`}
        </button>
      )}
    </div>
  );
}
