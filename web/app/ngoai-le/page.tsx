"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Ngoại lệ cần xử lý (Kiểm soát & Chính sách).
 *
 *  Khác "Cảnh báo nghiệp vụ": cảnh báo nói tình trạng đang xấu và tự tắt khi hết xấu. Ngoại lệ nói đã có
 *  người cho qua một quy tắc, và nó không tự tắt – chỉ đóng khi trả lời được ba câu: ai quyết, vì sao,
 *  và sau đó đã làm gì.
 *
 *  Con số dẫn đầu màn hình là "KHÔNG AI KÝ" chứ không phải tổng số ngoại lệ. Ngoại lệ có chữ ký là ngoại
 *  lệ lành mạnh – cần rà, không cần hoảng. Ngoại lệ mà hệ thống cho qua không ai ký mới là thứ đến lúc
 *  có chuyện sẽ không có ai trả lời được. */

type Row = {
  ma: string; loai: string; loai_ten: string; nhom: string; nhom_ten: string; quy_tac: string;
  muc: string; muc_ten: string; luc: string | null; so_ngay_ton: number | null;
  doi_tuong: string; tom_tat: string; nguoi_quyet: string; ly_do: string; duong_dan: string;
  thieu_chu_ky: boolean; trang_thai: string; trang_thai_ten: string;
  nguoi_nhan: string; giai_trinh: string; da_lam: string; nguoi_chiu_trach_nhiem: string;
  dong_boi: string; dong_luc: string | null;
};

function NgoaiLePage() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const laLanhDao = ["chutich", "tgd"].includes(role);
  const ghiDuoc = !user?.read_only && ["chutich", "tgd", "ketoan", "cntt", "tp_dh", "ptgd_doan", "ptgd_mkt"].includes(role);

  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [nhom, setNhom] = useState("");
  const [tt, setTt] = useState("mo");        // mo = chưa đóng (mặc định), "" = tất cả
  const [chiThieu, setChiThieu] = useState(false);
  const [soNgay, setSoNgay] = useState(180);
  const [mo, setMo] = useState<string | null>(null);   // dòng đang mở form
  const [form, setForm] = useState<{ giai_trinh: string; da_lam: string; nguoi: string }>({ giai_trinh: "", da_lam: "", nguoi: "" });

  const load = useCallback(() => {
    const q = new URLSearchParams({ so_ngay: String(soNgay) });
    if (chiThieu) q.set("chi_thieu_chu_ky", "true");
    api(`/ngoai-le?${q}`).then((x) => { setD(x); setLoi(""); }).catch((e) => setLoi(errMsg(e)));
  }, [soNgay, chiThieu]);
  useEffect(load, [load]);

  const rows: Row[] = useMemo(() => {
    const all: Row[] = d?.rows || [];
    return all.filter((r) =>
      (!nhom || r.nhom === nhom) &&
      (tt === "" || (tt === "mo" ? r.trang_thai !== "dong" : r.trang_thai === tt)));
  }, [d, nhom, tt]);

  const th = d?.tong_hop;

  const goi = async (path: string, json: any) => {
    try {
      const r = await api<any>(`/ngoai-le/${path}`, { method: "POST", json });
      toast(r.message || "Đã ghi"); setMo(null); setForm({ giai_trinh: "", da_lam: "", nguoi: "" }); load();
    } catch (e) { toast(errMsg(e), true); }
  };

  const moForm = (r: Row) => {
    setMo(mo === r.ma ? null : r.ma);
    setForm({ giai_trinh: r.giai_trinh || "", da_lam: r.da_lam || "", nguoi: r.nguoi_chiu_trach_nhiem || "" });
  };

  return (
    <main>
      <h1>Ngoại lệ cần xử lý</h1>
      <p className="muted" style={{ marginTop: -6 }}>
        Mỗi dòng dưới đây là một lần quy tắc bị bẻ. Khác cảnh báo nghiệp vụ ở chỗ nó không tự tắt: chỉ đóng
        được khi có giải trình vì sao đã phải bẻ, và đã làm gì để không tái diễn.
      </p>

      {loi && <div className="gate fail">{loi}</div>}

      {th && (
        <div className="kpis" style={{ marginBottom: 14 }}>
          <div className="kpi" style={{ borderColor: th.khong_ai_ky ? "var(--red)" : undefined }}>
            <b style={{ color: th.khong_ai_ky ? "var(--red)" : undefined }}>{th.khong_ai_ky}</b>
            <span>KHÔNG AI KÝ – hệ thống cho qua mà không ghi lại người nào</span>
          </div>
          <div className="kpi"><b>{th.nghiem_trong_chua_dong}</b><span>Nghiêm trọng, chưa đóng</span></div>
          <div className="kpi"><b>{th.chua_dong}</b><span>Đang mở</span></div>
          <div className="kpi"><b>{th.ton_qua_30_ngay}</b><span>Tồn quá 30 ngày</span></div>
        </div>
      )}

      <div className="panel">
        <div className="grid">
          <div>
            <label>Nhóm</label>
            <select value={nhom} onChange={(e) => setNhom(e.target.value)}>
              <option value="">Tất cả nhóm{th ? ` (${th.chua_dong} đang mở)` : ""}</option>
              {Object.entries(d?.nhom || {}).map(([k, v]) => (
                <option key={k} value={k}>{v as string}{th ? ` (${th.theo_nhom?.[k] ?? 0})` : ""}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Trạng thái</label>
            <select value={tt} onChange={(e) => setTt(e.target.value)}>
              <option value="mo">Đang mở (chưa đóng)</option>
              <option value="chua">Chưa xử lý</option>
              <option value="dang">Đang xử lý</option>
              <option value="dong">Đã đóng</option>
              <option value="">Tất cả</option>
            </select>
          </div>
          <div>
            <label>Cửa sổ dò</label>
            <select value={soNgay} onChange={(e) => setSoNgay(Number(e.target.value))}>
              <option value={30}>30 ngày</option><option value={90}>90 ngày</option>
              <option value={180}>180 ngày</option><option value={365}>1 năm</option>
              <option value={1095}>3 năm</option>
            </select>
          </div>
          <div>
            <label style={{ marginTop: 26 }}>
              <input type="checkbox" style={{ width: "auto", marginRight: 6 }}
                     checked={chiThieu} onChange={(e) => setChiThieu(e.target.checked)} />
              Chỉ hiện loại KHÔNG AI KÝ
            </label>
          </div>
        </div>
      </div>

      {!d && !loi && <div className="panel muted">Đang dò…</div>}
      {d?.tong_hop?.bi_cat && Object.keys(d.tong_hop.bi_cat).length > 0 && (
        <div className="gate">
          Có loại ngoại lệ quá nhiều dòng nên màn hình chỉ hiện {d.cat_moi_loai} dòng đầu mỗi loại – con số
          thống kê phía trên vẫn đếm đủ:{" "}
          {Object.entries(d.tong_hop.bi_cat).map(([k, n]) => `${d.loai?.[k]?.ten || k}: còn ${n} mục nữa`).join(" · ")}
        </div>
      )}

      {d && rows.length === 0 && (
        <div className="gate pass">Không có ngoại lệ nào khớp bộ lọc. Đây là kết quả tốt – nhưng hãy đọc kèm
          cửa sổ dò: bộ lọc đang chỉ nhìn {soNgay} ngày gần nhất.</div>
      )}

      {rows.map((r) => (
        <div key={r.ma} className="panel"
             style={{ borderLeft: `4px solid ${r.thieu_chu_ky ? "var(--red)" : r.muc === "do" ? "var(--orange)" : "var(--line)"}` }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <Tag cls={r.muc === "do" ? "red" : "warn"}>{r.muc_ten}</Tag>
            <Tag>{r.nhom_ten}</Tag>
            <b>{r.loai_ten}</b>
            <Tag cls={r.trang_thai === "dong" ? "ok" : r.trang_thai === "dang" ? "navy" : ""}>{r.trang_thai_ten}</Tag>
            {r.thieu_chu_ky && <Tag cls="red">KHÔNG AI KÝ</Tag>}
            <span className="muted" style={{ marginLeft: "auto" }}>
              {fmtDT(r.luc)}{r.so_ngay_ton != null && r.trang_thai !== "dong" ? ` · tồn ${r.so_ngay_ton} ngày` : ""}
            </span>
          </div>

          <div style={{ marginTop: 6 }}>{r.tom_tat}</div>
          <div className="muted" style={{ marginTop: 4 }}>
            Quy tắc bị bẻ: {r.quy_tac}
            {r.duong_dan && <> · <a href={r.duong_dan}>{r.doi_tuong}</a></>}
          </div>

          <div className="grid" style={{ marginTop: 8 }}>
            <div>
              <h3>Người quyết</h3>
              {r.nguoi_quyet
                ? <div>{r.nguoi_quyet}</div>
                : <div style={{ color: "var(--red)", fontWeight: 600 }}>Không có – hệ thống cho qua, không ai ký</div>}
            </div>
            <div>
              <h3>Lý do đã ghi lúc đó</h3>
              <div>{r.ly_do || <span className="muted">— không ghi —</span>}</div>
            </div>
          </div>

          {(r.giai_trinh || r.da_lam || r.nguoi_chiu_trach_nhiem) && (
            <div className="grid" style={{ marginTop: 4 }}>
              {r.nguoi_chiu_trach_nhiem && <div><h3>Người chịu trách nhiệm</h3><div>{r.nguoi_chiu_trach_nhiem}</div></div>}
              {r.giai_trinh && <div><h3>Giải trình</h3><div style={{ whiteSpace: "pre-wrap" }}>{r.giai_trinh}</div></div>}
              {r.da_lam && <div><h3>Đã làm để không tái diễn</h3><div style={{ whiteSpace: "pre-wrap" }}>{r.da_lam}</div></div>}
            </div>
          )}
          {r.trang_thai === "dong" && (
            <div className="muted" style={{ marginTop: 6 }}>Đóng bởi {r.dong_boi} lúc {fmtDT(r.dong_luc)}</div>
          )}

          {ghiDuoc && (
            <div style={{ marginTop: 8 }}>
              {r.trang_thai === "chua" &&
                <button className="act" onClick={() => goi("nhan", { ma: r.ma })}>Nhận xử lý</button>}
              {r.trang_thai !== "dong" &&
                <button className="act grey" onClick={() => moForm(r)}>{mo === r.ma ? "Thu gọn" : "Ghi giải trình"}</button>}
              {r.trang_thai === "dong" && laLanhDao &&
                <button className="act orange" onClick={() => {
                  const ly = window.prompt("Mở lại ngoại lệ này vì lý do gì?") || "";
                  if (ly.trim()) goi("mo-lai", { ma: r.ma, ly_do: ly });
                }}>Mở lại</button>}
              {r.nguoi_nhan && r.trang_thai !== "dong" &&
                <span className="muted" style={{ marginLeft: 8 }}>đang do {r.nguoi_nhan} xử lý</span>}
            </div>
          )}

          {mo === r.ma && ghiDuoc && (
            <div style={{ marginTop: 8, borderTop: "1px solid var(--line)", paddingTop: 8 }}>
              {r.thieu_chu_ky && (
                <>
                  <label>Người chịu trách nhiệm (bắt buộc với ngoại lệ không ai ký)</label>
                  <input value={form.nguoi} onChange={(e) => setForm({ ...form, nguoi: e.target.value })}
                         placeholder="Họ tên người chịu trách nhiệm về ngoại lệ này" />
                </>
              )}
              <label>Giải trình – vì sao lúc đó phải bẻ quy tắc (tối thiểu 20 ký tự)</label>
              <textarea value={form.giai_trinh} onChange={(e) => setForm({ ...form, giai_trinh: e.target.value })} />
              <label>Đã làm gì để không tái diễn</label>
              <textarea value={form.da_lam} onChange={(e) => setForm({ ...form, da_lam: e.target.value })} />
              <button className="act" onClick={() => goi("ghi", {
                ma: r.ma, giai_trinh: form.giai_trinh, da_lam: form.da_lam, nguoi_chiu_trach_nhiem: form.nguoi,
              })}>Lưu</button>
              {laLanhDao && (
                <button className="act teal" onClick={async () => {
                  await goi("ghi", { ma: r.ma, giai_trinh: form.giai_trinh, da_lam: form.da_lam, nguoi_chiu_trach_nhiem: form.nguoi });
                  await goi("dong", { ma: r.ma });
                }}>Lưu và đóng</button>
              )}
              {!laLanhDao && <span className="muted" style={{ marginLeft: 8 }}>Đóng ngoại lệ là quyền của Chủ tịch và Tổng giám đốc.</span>}
            </div>
          )}
        </div>
      ))}
    </main>
  );
}

// Bọc trong Shell: không bọc thì trang chạy NGOÀI khung – mất thanh điều hướng, và tệ hơn là
// useShell() trả user rỗng nên mọi nút theo vai trò lặng lẽ biến mất mà không báo lỗi gì.
export default function Page() { return <Shell><NgoaiLePage /></Shell>; }
