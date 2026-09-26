"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

/** TRANG CÔNG KHAI — khách tự chấm điểm sau tour. KHÔNG cần đăng nhập.
 *
 *  Đề xuất tự động hoá CSKH 25/9/2026, bước 2. Khách mở trang này từ đường dẫn trong tin Zalo.
 *
 *  ── BA ĐIỀU CỦA TRANG NÀY, KHÁC MỌI TRANG KHÁC TRONG VTOS ──────────────────────────────────
 *  1. KHÔNG dùng `Shell` — Shell đòi đăng nhập và vẽ cả thanh điều hướng nội bộ. Khách không có
 *     tài khoản, và cũng không nên nhìn thấy sơ đồ phân hệ của công ty.
 *  2. KHÔNG dùng hàm `api` của kho — hàm ấy gắn thẻ đăng nhập và tự đẩy sang /login khi 401.
 *     Trang này gọi `fetch` thẳng.
 *  3. KHÔNG lưu gì vào trình duyệt. Một mã chấm xong là xong; giữ lại chỉ tạo thêm một chỗ rò.
 *
 *  ── VÌ SAO MỖI MỤC CÓ NÚT "BỎ QUA" ─────────────────────────────────────────────────────────
 *  Vì chuyến đi bộ không có tài xế, và ép khách chấm một người không tồn tại thì con số ấy hạ
 *  điểm trung bình của một người thật. Bỏ qua = RỖNG, không phải 0 — máy chủ cũng hiểu như vậy.
 */

type Muc = { doi_tuong: string; id: number | null; ten: string };
type Phieu = {
  ten_khach: string; tour_ten: string; ngay_di: string | null; ngay_ve: string | null;
  muc: Muc[]; doi_tuong_ten: Record<string, string>;
};

const fmt = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");

function Sao({ diem, doi }: { diem: number | null; doi: (v: number | null) => void }) {
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" onClick={() => doi(n)} aria-label={`${n} sao`}
          style={{
            width: 42, height: 42, fontSize: 22, lineHeight: 1, cursor: "pointer",
            borderRadius: 8, border: "1px solid var(--line, #cbd5e1)",
            background: diem && n <= diem ? "#f6c945" : "transparent",
            color: diem && n <= diem ? "#3a2c00" : "inherit",
          }}>★</button>
      ))}
      <button type="button" onClick={() => doi(null)}
        style={{ padding: "8px 12px", borderRadius: 8, cursor: "pointer",
                 border: "1px solid var(--line, #cbd5e1)", background: "transparent",
                 opacity: diem === null ? 1 : 0.55 }}>
        Không có / bỏ qua
      </button>
    </div>
  );
}

export default function Page() {
  const { ma } = useParams<{ ma: string }>();
  const [p, setP] = useState<Phieu | null>(null);
  const [loi, setLoi] = useState("");
  const [diem, setDiem] = useState<Record<string, number | null>>({});
  const [nx, setNx] = useState<Record<string, string>>({});
  const [tiep, setTiep] = useState("");
  const [dongY, setDongY] = useState("");
  const [gopY, setGopY] = useState("");
  const [xong, setXong] = useState("");
  const [dangGui, setDangGui] = useState(false);

  const khoa = (m: Muc) => `${m.doi_tuong}:${m.id ?? ""}`;

  const tai = useCallback(async () => {
    try {
      const r = await fetch(`/api/v1/khao-sat/${encodeURIComponent(String(ma))}`);
      const d = await r.json();
      if (!r.ok) { setLoi(d?.detail?.message || "Liên kết không đúng hoặc đã hết hiệu lực."); return; }
      setP(d);
    } catch { setLoi("Không kết nối được. Xin anh/chị thử lại sau ít phút."); }
  }, [ma]);
  useEffect(() => { tai(); }, [tai]);

  const gui = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!p) return;
    // Gửi lên ĐÚNG những mục khách đã chạm tới. Mục không chạm thì không gửi — để máy chủ giữ
    // nguyên nghĩa "khách chưa trả lời mục này", khác hẳn với "khách chấm 0".
    const ds = p.muc
      .filter((m) => khoa(m) in diem || (nx[khoa(m)] || "").trim())
      .map((m) => ({
        doi_tuong: m.doi_tuong, doi_tuong_id: m.id, doi_tuong_ten: m.ten,
        diem: diem[khoa(m)] ?? null, nhan_xet: nx[khoa(m)] || "",
      }));
    if (!ds.length) { setLoi("Xin anh/chị chấm ít nhất một mục."); return; }
    if (!tiep || !dongY) { setLoi("Xin anh/chị trả lời giúp hai câu cuối."); return; }
    setDangGui(true); setLoi("");
    try {
      const r = await fetch(`/api/v1/khao-sat/${encodeURIComponent(String(ma))}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ diem: ds, nhu_cau_tiep: tiep, dong_y_dung_danh_gia: dongY, gop_y: gopY }),
      });
      const d = await r.json();
      if (!r.ok) { setLoi(d?.detail?.message || "Không gửi được."); return; }
      setXong(d.loi_cam_on || "Cảm ơn anh/chị.");
    } catch { setLoi("Không kết nối được. Xin anh/chị thử lại sau ít phút."); }
    finally { setDangGui(false); }
  };

  if (xong) return (
    <main style={{ maxWidth: 640, margin: "40px auto", padding: "0 16px" }}>
      <div className="panel"><h1>Cảm ơn anh/chị</h1><p>{xong}</p>
        <p className="muted">Vietourist Holdings</p></div>
    </main>);

  if (!p) return (
    <main style={{ maxWidth: 640, margin: "40px auto", padding: "0 16px" }}>
      <div className="panel">{loi ? <><h1>Không mở được</h1><p>{loi}</p>
        <p className="muted">Anh/chị có thể gọi tổng đài để gửi đánh giá giúp.</p></>
        : <p className="muted">Đang mở…</p>}</div>
    </main>);

  return (
    <main style={{ maxWidth: 640, margin: "24px auto", padding: "0 16px" }}>
      <div className="panel">
        <h1>Cảm ơn anh/chị đã đi cùng Vietourist</h1>
        <p><b>{p.tour_ten}</b><br />
          <span className="muted">{fmt(p.ngay_di)}{p.ngay_ve ? ` – ${fmt(p.ngay_ve)}` : ""}</span></p>
        <p>Xin anh/chị {p.ten_khach ? <b>{p.ten_khach}</b> : null} dành hai phút chấm điểm giúp chúng tôi.
          Mục nào không có trong chuyến thì bấm <b>Không có / bỏ qua</b>.</p>

        <form onSubmit={gui}>
          {p.muc.map((m) => {
            const k = khoa(m);
            return (
              <div key={k} style={{ margin: "18px 0", paddingTop: 12, borderTop: "1px solid var(--line, #e2e8f0)" }}>
                <label style={{ fontWeight: 600 }}>
                  {p.doi_tuong_ten[m.doi_tuong] || m.doi_tuong}{m.ten && m.doi_tuong !== "tour" ? ` · ${m.ten}` : ""}
                </label>
                <Sao diem={k in diem ? diem[k] : null} doi={(v) => setDiem({ ...diem, [k]: v })} />
                <input placeholder="Anh/chị muốn nói thêm điều gì? (không bắt buộc)"
                  value={nx[k] || ""} onChange={(e) => setNx({ ...nx, [k]: e.target.value })}
                  style={{ marginTop: 8 }} />
              </div>
            );
          })}

          <div style={{ marginTop: 18, paddingTop: 12, borderTop: "1px solid var(--line, #e2e8f0)" }}>
            <label style={{ fontWeight: 600 }}>Anh/chị có dự định đi tour tiếp không?</label>
            <select value={tiep} onChange={(e) => setTiep(e.target.value)}>
              <option value="">— xin chọn —</option>
              <option value="co">Có, tôi muốn được tư vấn</option>
              <option value="khong">Chưa, cảm ơn</option>
            </select>
          </div>

          {/* Câu xin phép, HỎI THẬT chứ không mặc định. Ô này có trên phiếu từ Đợt 4 với đúng lý
              do: chưa đồng ý thì tuyệt đối không đưa lời khách lên kênh truyền thông. */}
          <div style={{ marginTop: 14 }}>
            <label style={{ fontWeight: 600 }}>Công ty có được dùng lời nhận xét của anh/chị trên trang giới thiệu không?</label>
            <select value={dongY} onChange={(e) => setDongY(e.target.value)}>
              <option value="">— xin chọn —</option>
              <option value="co">Được</option>
              <option value="khong">Không, xin giữ riêng</option>
            </select>
          </div>

          <label style={{ marginTop: 14, display: "block", fontWeight: 600 }}>Góp ý chung cho cả chuyến</label>
          <textarea value={gopY} onChange={(e) => setGopY(e.target.value)} rows={3}
            placeholder="Điều gì làm anh/chị hài lòng, điều gì cần sửa?" />

          {loi && <div className="gate fail" style={{ marginTop: 12 }}>{loi}</div>}
          <button className="act teal" type="submit" disabled={dangGui} style={{ marginTop: 14 }}>
            {dangGui ? "Đang gửi…" : "Gửi đánh giá"}
          </button>
          <p className="muted" style={{ marginTop: 10 }}>Đường dẫn này chỉ gửi được một lần.</p>
        </form>
      </div>
    </main>
  );
}
