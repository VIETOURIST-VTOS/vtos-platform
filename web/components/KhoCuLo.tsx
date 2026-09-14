"use client";
/** KHO QUYẾT TOÁN CŨ T1–T6/2026 — bảng điều khiển nạp và GỠ CẢ LÔ.
 *
 * VÌ SAO CÓ Ô NÀY, VÀ VÌ SAO NÓ ĐẶT Ở ĐÂY
 *
 * Chủ tịch giao nạp kho cũ để hệ thống chạy trên số thật nửa năm, nạp thử tháng 1 trước. Nạp thử
 * mà không gỡ lại được thì không phải "thử" — nó một chiều, và người ta hoặc không dám bấm, hoặc
 * bấm rồi phải dọn tay mấy trăm dòng.
 *
 * Hai cửa NẠP nằm ở /tep (khung ba cửa chung: tải tệp → soát → ghi). Nút GỠ đặt ở đây, ngay đầu
 * danh sách tour, vì đây là chỗ người ta NHÌN THẤY hậu quả của việc nạp: mấy trăm dòng chuyến mới.
 *
 * BA ĐIỀU Ô NÀY TỰ BUỘC MÌNH
 *
 * 1. MẶC ĐỊNH ĐÓNG. Đây không phải việc hằng ngày; mở sẵn thì nó chỉ tổ chiếm chỗ và tập cho người
 *    ta quen mắt với một cái nút xoá hàng loạt.
 * 2. KHÔNG HIỆN NÚT GỠ KHI CHƯA CÓ GÌ ĐỂ GỠ. Một nút bấm vào không làm gì là nút dạy người ta bấm
 *    mà không đọc.
 * 3. XEM TRƯỚC RỒI MỚI CHO BẤM. Con số hiện ra là con số máy chủ vừa đếm, không phải con số đoán —
 *    và nút gỡ chỉ sống sau khi đã xem.
 */
import { useState } from "react";
import { api, getUser } from "@/lib/api";
import { errMsg } from "@/components/ui";

type Xem = {
  nguon: string;
  dong_quyet_toan: Record<string, number>;
  tong_dong: number;
  chuyen_cua_lo: number;
  xoa_duoc: { id: number; ma: string; ten: string; ngay_di: string }[];
  giu_lai: { id: number; ma: string; ten: string; con_treo: Record<string, number> }[];
  ghi_chu: string;
};

const DUOC_XEM = ["chutich", "tgd", "cntt", "tp_dh"];

export default function KhoCuLo({ onXong }: { onXong?: () => void }) {
  const user = getUser();
  const [mo, setMo] = useState(false);
  const [xem, setXem] = useState<Xem | null>(null);
  const [dangChay, setDangChay] = useState(false);
  const [tin, setTin] = useState("");
  const [loi, setLoi] = useState("");

  // Vai trò do MÁY CHỦ quyết định (require_roles ở /kho-cu/*). Ô này chỉ giấu cho đỡ rối mắt —
  // giấu nút không phải là phân quyền, và nếu chỉ giấu thì ai gọi thẳng API vẫn gỡ được.
  if (!user || !DUOC_XEM.includes(user.role)) return null;

  async function nhinTruoc() {
    setDangChay(true); setLoi(""); setTin("");
    try { setXem(await api<Xem>("/quyet-toan-lop3/kho-cu/xem-go")); }
    catch (e) { setLoi(errMsg(e)); }
    finally { setDangChay(false); }
  }

  async function go() {
    if (!xem) return;
    const n = xem.xoa_duoc.length;
    if (!confirm(
      `GỠ CẢ LÔ kho quyết toán cũ T1–T6/2026?\n\n` +
      `• Gỡ ${xem.tong_dong} dòng quyết toán mang nhãn "${xem.nguon}"\n` +
      `• Xoá ${n} chuyến do lô này tạo ra\n` +
      `• Giữ lại ${xem.giu_lai.length} chuyến đã có người gắn việc lên\n\n` +
      `Dòng của Vietrip và dòng người nhập tay KHÔNG bị đụng tới.\n` +
      `Việc này ghi vào nhật ký mang tên ${user!.username}.`
    )) return;
    setDangChay(true); setLoi(""); setTin("");
    try {
      const r = await api<any>("/quyet-toan-lop3/kho-cu/go", { method: "POST", json: { xac_nhan: true } });
      setTin(r.message); setXem(null); onXong?.();
    } catch (e) { setLoi(errMsg(e)); }
    finally { setDangChay(false); }
  }

  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: "3px solid #b45309" }}>
      <button className="link" onClick={() => setMo(!mo)} style={{ fontWeight: 600 }}>
        {mo ? "▾" : "▸"} Kho quyết toán cũ T1–T6/2026 — nạp và gỡ cả lô
      </button>

      {mo && (
        <div style={{ marginTop: 10 }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Kho 604 tệp Excel Điều hành lập trước khi có mẫu chuẩn. <b>Nạp</b> làm ở màn hình{" "}
            <a href="/tep">Tải tệp</a>, hai bước theo đúng thứ tự:{" "}
            <b>1) Tạo chuyến còn thiếu</b> → <b>2) Kho quyết toán CŨ</b>. Bỏ bước 1 thì bước 2 bị
            chặn, vì dòng quyết toán không có chuyến để treo vào.
          </p>
          <p className="muted">
            Mọi dòng do hai cửa ấy ghi đều mang nhãn nguồn <code>kho_cu_h1_2026</code>. Nút gỡ dưới
            đây gỡ <b>đúng phần mang nhãn ấy</b> — dòng của Vietrip và dòng người nhập tay không bị
            đụng tới, kể cả khi nằm trên cùng một chuyến.
          </p>

          <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: "wrap" }}>
            <a className="btn" href="/tep">Mở màn hình nạp</a>
            <button disabled={dangChay} onClick={nhinTruoc}>
              {dangChay ? "Đang đếm…" : "Xem trước phần sẽ gỡ"}
            </button>
          </div>

          {loi && <p className="err" style={{ marginTop: 8 }}>{loi}</p>}
          {tin && <p className="ok" style={{ marginTop: 8 }}>{tin}</p>}

          {xem && (
            <div style={{ marginTop: 12 }}>
              <p className="muted">{xem.ghi_chu}</p>
              <table className="tbl" style={{ maxWidth: 520 }}>
                <tbody>
                  {Object.entries(xem.dong_quyet_toan).map(([k, v]) => (
                    <tr key={k}><td>{k}</td><td style={{ textAlign: "right" }}>{v}</td></tr>
                  ))}
                  <tr><td><b>Chuyến sẽ xoá</b></td>
                      <td style={{ textAlign: "right" }}><b>{xem.xoa_duoc.length}</b></td></tr>
                  <tr><td>Chuyến giữ lại (đã có người gắn việc)</td>
                      <td style={{ textAlign: "right" }}>{xem.giu_lai.length}</td></tr>
                </tbody>
              </table>

              {xem.giu_lai.length > 0 && (
                <details style={{ marginTop: 8 }}>
                  <summary className="muted">
                    {xem.giu_lai.length} chuyến được GIỮ LẠI — bấm xem vì sao
                  </summary>
                  <ul className="muted" style={{ marginTop: 6 }}>
                    {xem.giu_lai.slice(0, 30).map((g) => (
                      <li key={g.id}>
                        <b>{g.ma}</b> — còn treo:{" "}
                        {Object.entries(g.con_treo).map(([b, n]) => `${b} (${n})`).join(", ")}
                      </li>
                    ))}
                    {xem.giu_lai.length > 30 && <li>… và {xem.giu_lai.length - 30} chuyến nữa</li>}
                  </ul>
                </details>
              )}

              {/* Không hiện nút gỡ khi không có gì để gỡ — một nút bấm vào không làm gì là nút dạy
                  người ta bấm mà không đọc. */}
              {(xem.tong_dong > 0 || xem.xoa_duoc.length > 0) ? (
                <button className="danger" disabled={dangChay} onClick={go}
                        style={{ marginTop: 10 }}>
                  {dangChay ? "Đang gỡ…" : `Gỡ cả lô (${xem.xoa_duoc.length} chuyến, ${xem.tong_dong} dòng)`}
                </button>
              ) : (
                <p className="muted" style={{ marginTop: 10 }}>
                  Không có gì để gỡ — chưa nạp lô nào, hoặc đã gỡ rồi.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
