"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHomNay } from "@/components/DauManHinh01";
import NutLich90 from "@/components/NutLich90";

/** BÀN LÀM VIỆC CỦA PHÓ TỔNG GIÁM ĐỐC TOUR ĐOÀN — 24/9/2026.
 *
 *  Theo Điều 4 Văn bản đính chính, mọi dự toán tour ĐOÀN về tay vị trí này. Quyền ấy chạy trong mã
 *  đã lâu mà chưa có màn hình nào dựng quanh nó: người ký phải tự lọc bằng mắt trong danh sách tour
 *  chung. Một cổng chặn mà người giữ cổng phải tự đi tìm việc là một cổng sẽ được ký muộn — và ký
 *  muộn một dự toán thì chuyến vẫn chạy, chỉ là chạy trước khi có ai duyệt.
 *
 *  ── MÀN HÌNH KHÔNG KÝ HỘ, VÀ KHÔNG KÝ HÀNG LOẠT ─────────────────────────────────────────────
 *  Mỗi dòng có đường dẫn sang đúng chuyến để ký ở cửa cũ (`/tours`), với đúng hàng rào cũ. Dựng
 *  nút ký ở đây là tạo bản sao thứ hai của luật ký, và bản sao nào rồi cũng lệch. Ký hàng loạt thì
 *  còn tệ hơn: duyệt dự toán là việc phải đọc, không phải việc phải bấm.
 *
 *  ── KHỐI "DƯỚI BIÊN" CỐ Ý KHÔNG CÓ ĐƯỜNG KÝ ────────────────────────────────────────────────
 *  Chuyến dưới ngưỡng biên phải đủ chữ ký Chủ tịch VÀ Tổng giám đốc. Vẽ nút ở đó là vẽ một nút bấm
 *  vào sẽ nhận 403; giấu hẳn khối ấy đi thì người phụ trách mảng đoàn không biết chuyến của mình
 *  đang nằm chờ ai. Nên: hiện ra, đếm riêng, không nút.
 *
 *  ── MÀN HÌNH KHÔNG TỰ TÍNH MỘT CON SỐ NÀO ──────────────────────────────────────────────────
 *  Kể cả biên lợi nhuận. Máy chủ đã tính bằng đúng `rules.calc` mà cổng biên dùng; tính lại ở đây
 *  là dựng công thức biên thứ hai, và ngày hai bên lệch nhau thì con số nằm cạnh nút duyệt là con
 *  số sai.
 */

const pct = (v: any) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);

/** Rỗng KHÁC không: chuyến chưa ai nhập số thì để gạch, không hiện 0. */
const so = (v: any) => (v === null || v === undefined
  ? <span className="muted" title="Chưa có số – khác với bằng 0">—</span>
  : <>{vnd(v)}</>);

function kyMacDinh() {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, "0")}`;
}

/** Còn mấy ngày tới lúc khởi hành. Âm nghĩa là chuyến ĐÃ khởi hành mà dự toán vẫn chưa ai duyệt –
 *  đó là tình trạng nặng nhất trên màn hình này, nên nó được nói thẳng chứ không in "-3 ngày". */
function ConLai({ n }: { n: number | null }) {
  if (n === null || n === undefined) return <span className="muted">—</span>;
  if (n < 0) return <Tag cls="red">đã khởi hành {-n} ngày mà chưa duyệt</Tag>;
  if (n <= 7) return <Tag cls="red">còn {n} ngày</Tag>;
  if (n <= 14) return <Tag cls="warn">còn {n} ngày</Tag>;
  return <span className="muted">còn {n} ngày</span>;
}

function O({ nhan, so: n, phu, manh }: { nhan: string; so: number; phu?: string; manh?: boolean }) {
  return (
    // R5-25: thẻ vạch navy; ô «mạnh» (việc của tôi / quá hạn) có việc thì vạch hồng logo.
    <div className="panel" style={{ marginBottom: 0, borderTop: `3px solid var(--${manh && Number(n) > 0 ? "vtos-logo-hong" : "vtos-sky"})` }}>
      <div className="muted" style={{ fontSize: "calc(11/14*1rem)", textTransform: "uppercase", letterSpacing: ".04em", fontWeight: 600 }}>{nhan}</div>
      <div style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.2 }}>{n}</div>
      {phu ? <div className="muted" style={{ fontSize: "calc(12/14*1rem)" }}>{phu}</div> : null}
    </div>
  );
}

function BanLamViec() {
  const { toast } = useShell();
  const homNay = useHomNay();
  const [ky, setKy] = useState(kyMacDinh());
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(true);

  const nap = useCallback(async () => {
    setDang(true);
    try { setD(await api(`/ptgd-doan/ban-lam-viec?ky=${ky}`)); }
    catch (e) { toast(errMsg(e), true); setD(null); }
    finally { setDang(false); }
  }, [ky, toast]);
  useEffect(() => { nap(); }, [nap]);

  if (dang && !d) return <div className="panel"><p className="muted">Đang tải…</p></div>;
  if (!d) return <div className="panel"><p className="muted">Không đọc được dữ liệu.</p></div>;

  const dem = d.dem || {};
  const qh = d.qua_han_quyet_toan || {};
  const ll = d.lai_lo || {};

  return (<div className="ban-navy">
    {/* R5-25 (Chủ tịch duyệt bản xem trước 14/11/2026): thanh đầu navy sáng có vạch ba màu như mọi bàn; đầu bảng
        navy trên nền trắng sáng (`.ban-navy th`, globals.css). */}
    <div className="mh01-ban">
      <h1 className="mh01-ban-ten">Bàn làm việc Phó TGĐ Đoàn</h1>
      <div className="mh01-ban-cum">
        <div className="mh01-ban-ngay"><span>Hôm nay</span>{homNay || "…"}</div>
        <NutLich90 />
      </div>
    </div>
    <h2 style={{ margin: "0 0 10px" }}>Việc chờ tôi</h2>

    <div className="panel">
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Kỳ lãi lỗ<br /><input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
        <span className="muted">Hàng đợi ký và sổ quá hạn KHÔNG theo kỳ – chúng là việc của hôm nay.</span>
      </div>
    </div>

    <div className="row" style={{ gap: 14, flexWrap: "wrap", alignItems: "stretch", marginBottom: 14 }}>
      <div style={{ flex: "1 1 240px" }}>
        <O nhan="Dự toán đoàn chờ tôi duyệt" so={dem.cho_toi_duyet ?? 0} manh
           phu={`${dem.cho_toi_duyet_khoi_hanh_duoi_7_ngay ?? 0} chuyến khởi hành trong 7 ngày · ${dem.cho_toi_duyet_du_truong ?? 0} hồ sơ đủ trường`} />
      </div>
      <div style={{ flex: "1 1 240px" }}>
        <O nhan="Đoàn quá hạn chưa đóng sổ" so={dem.qua_han_chua_dong_so ?? 0} manh
           phu={`đã đóng muộn: ${dem.dong_so_muon ?? 0} chuyến`} />
      </div>
      <div style={{ flex: "1 1 240px" }}>
        <O nhan="Dưới biên – chờ hai chữ ký" so={dem.duoi_bien_hai_chu_ky ?? 0}
           phu="Chủ tịch + Tổng giám đốc, không phải tôi" />
      </div>
    </div>

    {/* ── HÀNG ĐỢI KÝ ─────────────────────────────────────────────────────────────────────── */}
    <div className="panel wrap">
      <h2>Dự toán đoàn chờ tôi duyệt</h2>
      <p className="muted">Điều 4 Văn bản đính chính: tour <b>đoàn</b> do Phó TGĐ tour đoàn duyệt, tour lẻ
        do Tổng giám đốc. Trưởng phòng Điều hành đã xác nhận trước khi dòng này tới đây.</p>
      <table className="bang-doc">
        <thead><tr><th>Mã chuyến</th><th>Khởi hành</th><th className="num">Doanh thu dự kiến</th>
          <th className="num">Giá vốn dự kiến</th><th className="num">Biên kế hoạch</th>
          <th>Trường còn thiếu</th><th></th></tr></thead>
        <tbody>
          {(d.cho_toi_duyet || []).map((r: any) => (
            <tr key={r.tour_id}>
              <td data-nhan="Mã chuyến"><span className="mono">{r.ma}</span><br /><span className="muted">{r.ten}</span></td>
              <td data-nhan="Khởi hành">{r.khoi_hanh}<br /><ConLai n={r.con_bao_nhieu_ngay} /></td>
              <td className="num" data-nhan="Doanh thu dự kiến">{so(r.doanh_thu_du_kien)}</td>
              <td className="num" data-nhan="Giá vốn dự kiến">{so(r.gia_von_du_kien)}</td>
              <td className="num" data-nhan="Biên kế hoạch">
                <b>{pct(r.bien_ke_hoach)}</b><br /><span className="muted">ngưỡng {pct(r.nguong_bien)}</span></td>
              <td data-nhan="Trường còn thiếu">
                {r.thieu.length === 0
                  ? <Tag cls="ok">đủ trường</Tag>
                  : <b className="so-do">{r.thieu.join(" · ")}</b>}
              </td>
              <td><Link className="act" href={`/tours?q=${encodeURIComponent(r.ma)}`}>Mở chuyến để duyệt</Link></td>
            </tr>
          ))}
          {!(d.cho_toi_duyet || []).length &&
            <tr><td colSpan={7} className="muted">Không có dự toán đoàn nào đang chờ chữ ký của bạn.</td></tr>}
        </tbody>
      </table>
    </div>

    {/* ── DƯỚI BIÊN: HIỆN RA, KHÔNG NÚT ───────────────────────────────────────────────────── */}
    {!!(d.duoi_bien_hai_chu_ky || []).length && (
      <div className="panel wrap" style={{ borderLeft: "4px solid var(--ink2)" }}>
        <h2>Đoàn dưới biên – đã chuyển lên hai chữ ký</h2>
        <p className="muted">Chuyến dưới ngưỡng biên <b>không</b> do tôi ký: phải đủ chữ ký Chủ tịch và Tổng
          giám đốc. Hiện ở đây để biết chúng đang nằm ở đâu, <b>không phải để bấm</b>.</p>
        <table className="bang-doc">
          <thead><tr><th>Mã chuyến</th><th className="num">Biên kế hoạch</th><th>Giải trình 4 mục</th>
            <th>Chữ ký còn thiếu</th></tr></thead>
          <tbody>
            {d.duoi_bien_hai_chu_ky.map((r: any) => (
              <tr key={r.tour_id}>
                <td data-nhan="Mã chuyến"><span className="mono">{r.ma}</span><br /><span className="muted">{r.ten}</span></td>
                <td className="num" data-nhan="Biên kế hoạch"><b className="so-do">{pct(r.bien_ke_hoach)}</b></td>
                <td data-nhan="Giải trình 4 mục">
                  {r.thieu.some((x: string) => x.includes("giải trình"))
                    ? <b className="so-do">chưa đủ – chưa trình được</b>
                    : <span className="muted">đã viết</span>}
                </td>
                <td data-nhan="Chữ ký còn thiếu">
                  {r.chu_ky_con_thieu.length
                    ? <Tag cls="warn">còn chờ {r.chu_ky_con_thieu.join(" và ")}</Tag>
                    : <Tag cls="ok">đủ hai chữ ký</Tag>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}

    {/* ── QUÁ HẠN QUYẾT TOÁN ──────────────────────────────────────────────────────────────── */}
    <div className="panel wrap" style={{ borderLeft: "4px solid var(--orange)" }}>
      <h2>Đoàn quá hạn quyết toán</h2>
      <p className="muted">Hạn chốt sổ tour đoàn: <b>{qh.han_theo_tham_so_ngay} ngày</b> kể từ ngày kết thúc
        (tham số <span className="mono">han_qt_doan</span>). Quá hạn thì chuyến <b>mất thưởng</b> kể cả khi lãi.</p>
      <table className="bang-doc">
        <thead><tr><th>Mã chuyến</th><th>Kết thúc</th><th>Hạn chốt sổ</th><th className="num">Quá hạn</th></tr></thead>
        <tbody>
          {(qh.chua_dong_so || []).map((r: any) => (
            <tr key={r.tour_id}>
              <td data-nhan="Mã chuyến"><span className="mono">{r.ma}</span><br /><span className="muted">{r.ten}</span></td>
              <td data-nhan="Kết thúc">{r.ket_thuc}</td>
              <td data-nhan="Hạn chốt sổ">{r.han_chot_so}</td>
              <td className="num" data-nhan="Quá hạn"><Tag cls="red">{r.qua_han_ngay} ngày</Tag></td>
            </tr>
          ))}
          {!(qh.chua_dong_so || []).length &&
            <tr><td colSpan={4} className="muted">Không có đoàn nào quá hạn mà chưa đóng sổ.</td></tr>}
        </tbody>
      </table>
      {/* Đếm riêng, không cộng chung: chỉ đếm chuyến chưa đóng thì mỗi lần ai đó đóng muộn, con số
          tự đẹp lên – thước đo tự lành, và cái nó đo được thì biến mất. */}
      <p className="muted" style={{ marginTop: 10 }}>
        Trong kỳ còn <b>{(qh.dong_muon || []).length}</b> chuyến đã đóng sổ <b>muộn hơn hạn</b>. Chúng không
        nằm trong bảng trên vì đã đóng, nhưng vẫn được đếm – nếu bỏ đi thì mỗi lần có người đóng muộn, con
        số quá hạn lại tự đẹp lên.
      </p>
    </div>

    {/* ── LÃI LỖ: HAI BIÊN CẠNH NHAU ──────────────────────────────────────────────────────── */}
    <div className="panel wrap">
      <h2>Lãi lỗ đoàn đã quyết toán – kỳ {ll.ky}</h2>
      <p className="muted">Chỉ tính chuyến đã đóng sổ. Cột <b>lệch biên</b> so biên thực tế với biên kế hoạch
        lúc duyệt – đó là chỗ đo lại chính chữ ký của tôi. Xếp <b>xấu nhất lên đầu</b>, không phải to nhất lên đầu.</p>
      <table className="bang-doc">
        <thead><tr><th>Mã chuyến</th><th className="num">Doanh thu</th><th className="num">Giá vốn</th>
          <th className="num">Biên kế hoạch</th><th className="num">Biên thực tế</th><th className="num">Lệch</th></tr></thead>
        <tbody>
          {(ll.rows || []).map((r: any) => (
            <tr key={r.tour_id}>
              <td data-nhan="Mã chuyến"><span className="mono">{r.ma}</span><br /><span className="muted">{r.ten}</span></td>
              <td className="num" data-nhan="Doanh thu">{so(r.doanh_thu)}</td>
              <td className="num" data-nhan="Giá vốn">{so(r.gia_von)}</td>
              <td className="num" data-nhan="Biên kế hoạch">{pct(r.bien_ke_hoach)}</td>
              <td className="num" data-nhan="Biên thực tế"><b>{pct(r.bien_thuc_te)}</b></td>
              <td className="num" data-nhan="Lệch">
                {r.lech_bien < 0 ? <b className="so-do">{pct(r.lech_bien)}</b> : <span className="so-xanh-la">+{pct(r.lech_bien)}</span>}
              </td>
            </tr>
          ))}
          {!(ll.rows || []).length &&
            <tr><td colSpan={6} className="muted">Kỳ này chưa có đoàn nào đóng sổ.</td></tr>}
        </tbody>
      </table>
      {!!(ll.rows || []).length && (
        <p className="muted" style={{ marginTop: 10 }}>
          {ll.so_chuyen} chuyến · doanh thu {vnd(ll.tong_doanh_thu)} · giá vốn {vnd(ll.tong_gia_von)} ·
          biên bình quân <b>{pct(ll.bien_binh_quan)}</b>
        </p>
      )}
    </div>
  </div>);
}

export default function Page() { return <Shell><BanLamViec /></Shell>; }
