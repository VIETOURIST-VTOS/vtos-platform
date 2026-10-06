"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Báo cáo tự động – hiện thẳng trên màn hình, không gửi mail hay Zalo (quyết định 09/9/2026).
 *
 *  Màn hình vẽ BẢNG CHỈ TIÊU do máy chủ tính, không tự tính lại con số nào. Hai chỗ cùng tính một
 *  con số thì sớm muộn lệch nhau, và người dùng sẽ tin chỗ dễ hơn.
 *
 *  Mỗi chỉ tiêu hiện kèm CÁCH TÍNH và NGUỒN. Đây không phải trang trí: câu hỏi đầu tiên của một
 *  trưởng phòng khi thấy con số lạ luôn là "cái này tính thế nào" – không trả lời được thì người ta
 *  thôi không dùng con số, và một chỉ tiêu không ai dùng thì bằng không có.
 *
 *  RỖNG KHÔNG PHẢI 0. Chỉ tiêu chưa có số hiện chữ "chưa có số" màu nhạt và KHÔNG tô cảnh báo:
 *  một phòng chưa nhập liệu không phải một phòng đang có vấn đề. */

const so = (v: any, dv: string) => {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v.toLocaleString("vi-VN") + (dv ? " " + dv : "");
  return String(v) + (dv ? " " + dv : "");
};

function BaoCao() {
  const { toast } = useShell();
  const [meta, setMeta] = useState<any>(null);
  const [pv, setPv] = useState("");
  const [kind, setKind] = useState("ngay");
  const [d, setD] = useState<any>(null);
  const [moTat, setMoTat] = useState<Record<string, boolean>>({});
  // "" = đang xem số HIỆN TẠI; khác rỗng = đang xem một BẢN CHỤP của kỳ đã qua.
  const [kyChup, setKyChup] = useState("");
  const [dsChup, setDsChup] = useState<any[]>([]);

  useEffect(() => {
    api<any>("/bao-cao/pham-vi").then((m) => {
      setMeta(m);
      // Phạm vi lấy từ đường dẫn trước, rồi mới tới mặc định. Mục 4.1 của cây phân hệ Điều hành
      // trỏ vào /bao-cao?pham_vi=dieu_hanh; trước 05/10/2026 dòng này luôn kéo về pham_vi[0] =
      // Toàn công ty, nên người Điều hành bấm "Tổng quan điều hành" lại mở ra báo cáo của cả
      // công ty rồi phải tự đổi ô. Phạm vi lạ trong đường dẫn thì bỏ qua, về mặc định – không
      // để màn hình trống vì một chữ gõ sai.
      if (m.pham_vi.length) {
        const q = new URLSearchParams(window.location.search).get("pham_vi") || "";
        setPv(m.pham_vi.some((x: any) => x.ma === q) ? q : m.pham_vi[0].ma);
      }
    }).catch((e) => toast(errMsg(e), true));
  }, [toast]);

  const load = useCallback(async () => {
    if (!pv) return;
    try {
      // Xem bản chụp thì ĐỌC bản chụp, không tính lại. Tính lại là cách người ta hỏi "cuối tháng
      // trước thế nào" và nhận về số của hôm nay mà không hề biết.
      setD(kyChup
        ? await api(`/bao-cao/ban-luu/${kind}/${encodeURIComponent(kyChup)}?pham_vi=${pv}`)
        : await api(`/bao-cao?pham_vi=${pv}&kind=${kind}`));
    } catch (e) { toast(errMsg(e), true); }
  }, [pv, kind, kyChup, toast]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!pv) return;
    api<any>(`/bao-cao/ban-luu?pham_vi=${pv}&kind=${kind}`)
      .then((r) => setDsChup(r.rows || [])).catch(() => setDsChup([]));
  }, [pv, kind]);

  if (!meta) return <p className="muted">Đang tải…</p>;
  if (!meta.pham_vi.length) return (<>
    <h1>Báo cáo tự động</h1>
    <p className="muted">Chưa có báo cáo nào dành cho vai trò của anh/chị. Báo cáo phòng hiện cho
      trưởng phòng và giám đốc phòng đó; báo cáo toàn công ty cho Chủ tịch, Tổng giám đốc và Ban
      Kiểm soát.</p>
  </>);

  return (<>
    <h1>Báo cáo tự động</h1>
    <p className="muted">Mặc định số liệu tính <b>tại thời điểm mở màn hình</b>. Ô <b>Thời điểm</b>
      cho phép mở lại <b>bản chụp</b> của một kỳ đã qua — số của kỳ ấy không tính lại được, nên bản
      chụp là cách duy nhất trả lời “cuối kỳ trước thế nào”. Mỗi dòng đi kèm cách tính và nguồn dữ
      liệu — bấm vào dòng để xem.</p>
    {meta.mo_rong_theo_nguoi && <div className="gate">
      Phạm vi của anh/chị đang <b>rộng hơn chức danh</b>: một ngoại lệ có thời hạn đã được cấp riêng
      cho tài khoản này, nên anh/chị xem được báo cáo của mọi phòng. Ngoại lệ có ngày hết hạn —
      xem ở màn hình Ngoại lệ cần xử lý.
    </div>}

    <div className="panel">
      <div className="grid2">
        <label>Phạm vi
          <select value={pv} onChange={(e) => { setPv(e.target.value); setD(null); }}>
            {meta.pham_vi.map((p: any) => <option key={p.ma} value={p.ma}>{p.ten}</option>)}
          </select></label>
        <label>Kỳ
          <select value={kind} onChange={(e) => { setKind(e.target.value); setKyChup(""); setD(null); }}>
            {meta.ky.map((k: any) => <option key={k.ma} value={k.ma}>{k.ten}</option>)}
          </select></label>
        <label>Thời điểm
          <select value={kyChup} onChange={(e) => { setKyChup(e.target.value); setD(null); }}>
            <option value="">Bây giờ (tính tại chỗ)</option>
            {dsChup.map((r: any) => <option key={r.ky} value={r.ky}>
              Bản chụp kỳ {r.ky} ({r.tu} → {r.den})</option>)}
          </select></label>
      </div>
      {!dsChup.length && <p className="muted">Chưa có bản chụp nào cho phạm vi và kỳ này. Bản chụp
        do lịch tự động lưu lại mỗi kỳ — xem lịch ở màn hình Lịch tự động hóa.</p>}
    </div>

    {!d ? <p className="muted">Đang tính…</p> : <>
      {d.ban_chup && <div className="gate">
        Đang xem <b>bản chụp</b> của kỳ {d.ky}, do <b>{d.tao_boi}</b> lưu lúc {String(d.tao_luc).replace("T", " ").slice(0, 16)}.
        Đây là số <b>tại thời điểm chụp</b>, không phải số hiện tại — dữ liệu từ đó tới nay đã có thể
        đổi. Chọn “Bây giờ” ở ô Thời điểm để xem số hiện tại.
      </div>}
      <div className="kpis">
        <div className="kpi"><b style={{ color: d.so_viec_do ? "var(--red)" : undefined }}>{d.so_viec_do}</b>
          <span>việc phải xử lý</span></div>
        <div className="kpi"><b>{d.so_can_ra_soat}</b><span>cần rà soát</span></div>
        <div className="kpi"><b className="muted">{d.so_chua_co_so}</b><span>chỉ tiêu chưa có số</span></div>
        <div className="kpi"><b>{d.ky}</b><span>kỳ {d.kind_ten} · {d.tu} → {d.den}</span></div>
      </div>

      <div className="panel wrap">
        <h2>{d.pham_vi_ten} – báo cáo {d.kind_ten}</h2>
        <table>
          <thead><tr><th>Chỉ tiêu</th><th style={{ textAlign: "right" }}>Giá trị</th>
            <th>Mức</th><th>Cần làm</th></tr></thead>
          <tbody>{d.chi_tieu.map((x: any) => {
            const mo = !!moTat[x.ma];
            const v = so(x.gia_tri, x.don_vi);
            return (<>
              <tr key={x.ma} style={{ cursor: "pointer" }}
                  onClick={() => setMoTat((m) => ({ ...m, [x.ma]: !m[x.ma] }))}>
                <td><b>{x.ten}</b></td>
                <td style={{ textAlign: "right" }}>
                  {v === null ? <span className="muted">chưa có số</span> : <b>{v}</b>}</td>
                <td>{x.muc === "do" ? <Tag cls="red">phải xử lý</Tag>
                  : x.muc === "vang" ? <Tag cls="warn">cần rà</Tag>
                  : v === null ? <span className="muted">—</span> : <Tag cls="ok">ổn</Tag>}</td>
                <td className="muted">{x.viec}</td>
              </tr>
              {mo && <tr key={x.ma + "-ct"}><td colSpan={4} style={{ background: "var(--panel2, #f8fafc)" }}>
                <div style={{ padding: "6px 4px" }}>
                  <div><b>Cách tính:</b> {x.cong_thuc}</div>
                  <div className="muted"><b>Nguồn dữ liệu:</b> {x.nguon}</div>
                  {x.chi_tiet?.length ? <div style={{ marginTop: 6 }}>
                    <b>Chi tiết:</b>
                    <ul style={{ margin: "4px 0 0 18px" }}>
                      {x.chi_tiet.map((c: any, i: number) => <li key={i}>{String(c)}</li>)}
                    </ul></div> : null}
                </div>
              </td></tr>}
            </>);
          })}</tbody>
        </table>
      </div>

      <p className="muted">Ô để trống nghĩa là <b>chưa có số</b> — không phải bằng 0. Một phòng chưa
        nhập liệu và một phòng không có việc gì xảy ra là hai chuyện khác nhau, nên màn hình không
        tô cảnh báo vào ô rỗng.</p>
    </>}
  </>);
}

export default function Page() { return <Shell><BaoCao /></Shell>; }
