"use client";
/** BẢNG CHỈ TIÊU CỦA MỘT PHÒNG — một thành phần, hai cửa vào (11/10/2026).
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  VÌ SAO TÁCH RA KHỎI /bao-cao
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *
 *  Chủ tịch chốt 11/10/2026: bấm vào một phân hệ trên menu dọc thì phải thấy MÀN HÌNH CHÍNH của
 *  giám đốc / trưởng phòng ấy, chứ không phải mục lục chức năng. Thứ đã có sẵn và đúng nghĩa
 *  "màn hình chính" là bảng chỉ tiêu tự động của phòng — nó vốn nằm ở `/bao-cao`.
 *
 *  Nên hai cửa cùng dẫn tới MỘT bảng: `/bao-cao` (chọn phòng bằng ô) và `/phan-he/<khoa>` (phòng
 *  do cánh cửa quyết định). Chép bảng ra làm hai bản là dựng cái đầu thứ hai cho một luật đã có
 *  chủ: sớm muộn hai bản lệch nhau, và người dùng sẽ tin bản nào dễ đọc hơn chứ không phải bản
 *  nào đúng. Nên bảng nằm đây, đúng một bản.
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  PHÂN QUYỀN KHÔNG VIẾT LẠI MỘT DÒNG NÀO
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *
 *  Ai xem được phòng nào là câu hỏi của MÁY CHỦ, trả lời ở `bao_cao_phong.PHONG`. Giao diện không
 *  giữ bản sao của bảng vai trò ấy: nó hỏi `/bao-cao/pham-vi` và dùng đúng danh sách máy chủ trả
 *  về. Nhờ vậy mở thêm một cửa vào KHÔNG nới một quyền nào, và ngày nào máy chủ siết lại thì cả
 *  hai cửa siết theo trong cùng một nhịp.
 *
 *  RANH GIỚI 09/9/2026 vẫn nguyên: thành phần này KHÔNG tự tính một con số nào. Nó vẽ đúng bảng
 *  máy chủ gửi xuống, kể cả ô rỗng — và mỗi chỉ tiêu đều có cửa nhập của bộ phận đứng sau. Hai chỗ
 *  cùng tính một con số thì sớm muộn lệch nhau, và người dùng sẽ tin chỗ dễ đọc hơn chứ không phải
 *  chỗ đúng.
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  HAI LÝ DO CHÉP NGUYÊN TỪ BẢN CŨ Ở /bao-cao — ĐỪNG BỎ KHI DỌN MÃ
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *
 *  MỖI CHỈ TIÊU HIỆN KÈM CÁCH TÍNH VÀ NGUỒN. Đây không phải trang trí: câu hỏi đầu tiên của một
 *  trưởng phòng khi thấy con số lạ luôn là "cái này tính thế nào" — không trả lời được thì người
 *  ta thôi không dùng con số, và một chỉ tiêu không ai dùng thì bằng không có.
 *
 *  RỖNG KHÔNG PHẢI 0. Chỉ tiêu chưa có số hiện chữ "chưa có số" màu nhạt và KHÔNG tô cảnh báo:
 *  một phòng chưa nhập liệu không phải một phòng đang có vấn đề.
 */
import { Fragment, useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

export type MetaPhamVi = { pham_vi: { ma: string; ten: string }[]; ky: { ma: string; ten: string }[];
                           mo_rong_theo_nguoi?: boolean };

/** Hỏi máy chủ người đang đăng nhập được xem những phạm vi nào.
 *
 *  Tách thành hook vì HAI nơi cần câu trả lời ấy cho hai việc khác nhau: `/bao-cao` cần nó để đổ
 *  ô chọn phòng, còn `/phan-he/<khoa>` cần nó để QUYẾT ĐỊNH vẽ bảng hay rơi về mục lục. Trang
 *  phân hệ hỏi một lần rồi truyền xuống bảng, nên mở một phân hệ vẫn chỉ tốn đúng một lượt hỏi.
 */
/** R5-2 · 13/11/2026: `boQua` — vai không có màn /bao-cao (nhân viên, trưởng nhóm KD mở /fit) thì
 *  không gọi: gọi là nhận 403 rồi hiện báo lỗi vô ích. `undefined` = chưa biết vai, chờ. */
export function usePhamViBaoCao(boQua: boolean | undefined = false) {
  const { toast } = useShell();
  const [meta, setMeta] = useState<MetaPhamVi | null>(null);
  const [xong, setXong] = useState(false);
  useEffect(() => {
    if (boQua === undefined) return;
    if (boQua) { setXong(true); return; }
    let song = true;
    api<MetaPhamVi>("/bao-cao/pham-vi")
      .then((m) => { if (song) { setMeta(m); setXong(true); } })
      .catch((e) => { if (song) { setXong(true); toast(errMsg(e), true); } });
    return () => { song = false; };
  }, [toast, boQua]);
  return { meta, xong };
}

const so = (v: any, dv: string) => {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v.toLocaleString("vi-VN") + (dv ? " " + dv : "");
  return String(v) + (dv ? " " + dv : "");
};

export default function BangChiTieuPhong(
  { meta, phamViCoDinh }: { meta: MetaPhamVi; phamViCoDinh?: string },
) {
  const { toast } = useShell();
  // Phạm vi CỐ ĐỊNH thì ô chọn phòng biến mất: ở trang phân hệ, phòng đã do cánh cửa quyết định,
  // để lại ô chọn là mời người ta đổi sang phòng khác ngay trong màn hình của phòng này.
  const [pv, setPv] = useState(phamViCoDinh || "");
  const [kind, setKind] = useState("ngay");
  const [d, setD] = useState<any>(null);
  const [moTat, setMoTat] = useState<Record<string, boolean>>({});
  // "" = đang xem số HIỆN TẠI; khác rỗng = đang xem một BẢN CHỤP của kỳ đã qua.
  const [kyChup, setKyChup] = useState("");
  const [dsChup, setDsChup] = useState<any[]>([]);

  useEffect(() => {
    if (phamViCoDinh) { setPv(phamViCoDinh); return; }
    if (!meta.pham_vi.length) return;
    // Phạm vi lấy từ đường dẫn trước, rồi mới tới mặc định. Mục 4.1 của cây phân hệ Điều hành
    // trỏ vào /bao-cao?pham_vi=dieu_hanh; trước 05/10/2026 dòng này luôn kéo về pham_vi[0] =
    // Toàn công ty, nên người Điều hành bấm "Tổng quan điều hành" lại mở ra báo cáo của cả
    // công ty rồi phải tự đổi ô. Phạm vi lạ trong đường dẫn thì bỏ qua, về mặc định – không
    // để màn hình trống vì một chữ gõ sai.
    const q = new URLSearchParams(window.location.search).get("pham_vi") || "";
    setPv(meta.pham_vi.some((x) => x.ma === q) ? q : meta.pham_vi[0].ma);
  }, [meta, phamViCoDinh]);

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

  return (<>
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
        {!phamViCoDinh && <label>Phạm vi
          <select value={pv} onChange={(e) => { setPv(e.target.value); setD(null); }}>
            {meta.pham_vi.map((p) => <option key={p.ma} value={p.ma}>{p.ten}</option>)}
          </select></label>}
        <label>Kỳ
          <select value={kind} onChange={(e) => { setKind(e.target.value); setKyChup(""); setD(null); }}>
            {meta.ky.map((k) => <option key={k.ma} value={k.ma}>{k.ten}</option>)}
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
          {/* Fragment CÓ KHOÁ, không phải `<>` như bản cũ: mỗi chỉ tiêu sinh ra HAI hàng (hàng số
              và hàng cách tính), nên gốc của mỗi vòng lặp là một Fragment. `<>` không nhận khoá
              được, nên React mất mốc nhận dạng hàng; đổi kỳ hay đổi phòng là danh sách dựng lại
              từ đầu và ô đang mở nhảy sang chỉ tiêu khác. Sửa luôn khi dời mã sang đây. */}
          <tbody>{d.chi_tieu.map((x: any) => {
            const mo = !!moTat[x.ma];
            const v = so(x.gia_tri, x.don_vi);
            return (<Fragment key={x.ma}>
              <tr style={{ cursor: "pointer" }}
                  onClick={() => setMoTat((m) => ({ ...m, [x.ma]: !m[x.ma] }))}>
                <td><b>{x.ten}</b></td>
                <td style={{ textAlign: "right" }}>
                  {v === null ? <span className="muted">chưa có số</span> : <b>{v}</b>}</td>
                <td>{x.muc === "do" ? <Tag cls="red">phải xử lý</Tag>
                  : x.muc === "vang" ? <Tag cls="warn">cần rà</Tag>
                  : v === null ? <span className="muted">—</span> : <Tag cls="ok">ổn</Tag>}</td>
                <td className="muted">{x.viec}</td>
              </tr>
              {mo && <tr><td colSpan={4} style={{ background: "var(--panel2, #f8fafc)" }}>
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
            </Fragment>);
          })}</tbody>
        </table>
      </div>

      <p className="muted">Ô để trống nghĩa là <b>chưa có số</b> — không phải bằng 0. Một phòng chưa
        nhập liệu và một phòng không có việc gì xảy ra là hai chuyện khác nhau, nên màn hình không
        tô cảnh báo vào ô rỗng.</p>
    </>}
  </>);
}
