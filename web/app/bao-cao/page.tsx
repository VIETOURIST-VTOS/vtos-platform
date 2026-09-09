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

  useEffect(() => {
    api<any>("/bao-cao/pham-vi").then((m) => {
      setMeta(m);
      if (m.pham_vi.length) setPv(m.pham_vi[0].ma);
    }).catch((e) => toast(errMsg(e), true));
  }, [toast]);

  const load = useCallback(async () => {
    if (!pv) return;
    try { setD(await api(`/bao-cao?pham_vi=${pv}&kind=${kind}`)); }
    catch (e) { toast(errMsg(e), true); }
  }, [pv, kind, toast]);
  useEffect(() => { load(); }, [load]);

  if (!meta) return <p className="muted">Đang tải…</p>;
  if (!meta.pham_vi.length) return (<>
    <h1>Báo cáo tự động</h1>
    <p className="muted">Chưa có báo cáo nào dành cho vai trò của anh/chị. Báo cáo phòng hiện cho
      trưởng phòng và giám đốc phòng đó; báo cáo toàn công ty cho Chủ tịch, Tổng giám đốc và Ban
      Kiểm soát.</p>
  </>);

  return (<>
    <h1>Báo cáo tự động</h1>
    <p className="muted">Số liệu tính <b>tại thời điểm mở màn hình</b>, không phải bản chốt hôm qua.
      Mỗi dòng đi kèm cách tính và nguồn dữ liệu — bấm vào dòng để xem.</p>
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
          <select value={kind} onChange={(e) => { setKind(e.target.value); setD(null); }}>
            {meta.ky.map((k: any) => <option key={k.ma} value={k.ma}>{k.ten}</option>)}
          </select></label>
      </div>
    </div>

    {!d ? <p className="muted">Đang tính…</p> : <>
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
