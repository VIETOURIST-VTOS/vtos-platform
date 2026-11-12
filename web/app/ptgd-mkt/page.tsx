"use client";
/** MKT-12 · BÀN LÀM VIỆC PHÓ TGĐ MARKETING — `/ptgd-mkt`. Chủ tịch duyệt bản xem thử 12/11/2026.
 *
 *  ĐỢT NÀY SỬA GIAO DIỆN, KHÔNG SỬA MỘT CON SỐ NÀO. Cửa `/api/v1/marketing/ban-ptgd` giữ nguyên,
 *  ba luật nói thật vẫn nằm ở máy chủ. Bốn chỗ đổi, và một chỗ trong đó là sửa lỗi của chính đợt
 *  MKT-11 chứ không phải ý thích mới:
 *
 *  (1) THANH ĐẦU BÀN DÙNG KHUÔN CHUNG `.mh01-ban` CỦA ĐỢT VH-30, không vẽ riêng nữa. Bàn Chủ tịch
 *      và bàn Đội xe đã đội thanh ấy từ 12/11/2026; bàn này đứng ngoài thì ba bàn của cùng một hệ
 *      thống trông như ba sản phẩm.
 *
 *  (2) TRANG NÀY KHÔNG CÒN KHAI MỘT MÃ MÀU NÀO. Bản MKT-11 khai 44 mã màu cứng — nền trắng, chữ
 *      `#16233a`, viền `#e1e7ef`. Hệ thống có HAI bộ giao diện và người dùng đổi được bằng nút
 *      «Giao diện» trên thanh ngang; bộ tối đổi `--vtos-card` sang `#122C45` và `--vtos-text` sang
 *      gần trắng. Một trang khai màu cứng thì khi đổi sang bộ tối nó vẫn trắng giữa một màn tối,
 *      và chữ tối nằm trên nền tối ở những chỗ nó lỡ dùng biến. Màn `/marketing` đã viết sẵn luật
 *      này trong chú thích đầu tệp: «Màn hình này KHÔNG khai màu riêng một dòng nào». MKT-11 không
 *      giữ luật ấy; đợt này trả lại. Phép thử `test_mkt12_ban_ptgd_khuon_nha.py` canh để nó không
 *      mở lại.
 *
 *  (3) SỐ NỀN XUỐNG CUỐI VÀ NHẠT ĐI. Đây cũng là sửa lỗi của MKT-11: luật (c) của đợt MKT-1 nói ô
 *      mẫu số đứng CUỐI và mang màu khác để không ai đọc nó như một việc phải làm — mà MKT-11 lại
 *      đặt khối ấy lên đầu, trên cả việc cần xử lý. Nay thứ tự là: việc, hàng đợi, rồi số nền.
 *
 *  (4) CHỮ GIẢI THÍCH THU VỀ MỘT DÒNG. Không xoá chữ — phần dài nằm sau một dòng bấm mở. Chữ vẫn
 *      thật, chỉ không còn đè lên con số. Và mười một lối gom vào MỘT dải bốn cột thay cho bốn
 *      khung xếp dọc cuối trang.
 *
 *  KHÔNG LẤY BỐN THỨ CỦA BẢN v32 (Chủ tịch chọn 12/11/2026): biểu tượng trên mọi thẻ, hai cột
 *  cạnh nhau, nút đậm «Mở danh sách», và thẻ nhãn trạng thái. Bàn này mỗi ô một cửa chữ giống
 *  nhau, nên mắt không phải học hai kiểu nút trên cùng một màn.
 *
 *  KHÔNG BỊA MỘT CHỮ NÀO MÁY CHỦ KHÔNG GỬI. Ô `chua_co` vẽ đúng trường `chu` máy chủ gửi, không
 *  thêm thẻ nhãn tự nghĩ ra. Ranh giới 09/9/2026.
 *
 *  KHÔNG GỌI `useSearchParams`, nên không cần ranh giới `Suspense` — luật ở
 *  `backend/tests/test_web_suspense_cho_search_params.py`.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell, GROUPS } from "@/components/Shell";
import { useHomNay } from "@/components/DauManHinh01";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";

type O = {
  khoa: string; ten: string; so_luong: number | null; don_vi: string;
  muc: string; ghi_chu: string; den: string; nguon: string;
  trang_thai: string; ly_do: string; chu?: string;
};
type Ban = { ten: string; vai: string; o: O[]; luu_y: string };

/** Mười hai lối của phòng, đọc THẲNG từ bảng menu — cùng cách màn `/marketing` đang đọc. */
const LOI: [string, string][] = (() => {
  const nhom = (GROUPS as any[]).find((g) => g.key === "marketing");
  const ra: [string, string][] = [];
  for (const b of (((nhom || {}).blocks) || []) as any[]) {
    if (Array.isArray(b)) { ra.push(b as [string, string]); continue; }
    for (const m of (((b || {}).items) || []) as any[]) {
      if (Array.isArray(m)) ra.push(m as [string, string]);
    }
  }
  return ra;
})();

/** Bốn nhóm chức năng. Tên mục viết ĐÚNG như bảng menu — đổi tên mục là việc của một đợt khác. */
const NHOM: [string, string[]][] = [
  ["Khách hàng & doanh thu", ["Chuyển đổi & phối hợp Sales", "Đóng góp doanh thu"]],
  ["Chiến dịch & ngân sách", ["Kế hoạch & ngân sách", "Chiến dịch", "Đối soát dữ liệu"]],
  ["Nội dung & truyền thông",
   ["Nội dung & thương hiệu", "Báo chí, KOL & sự kiện", "Khủng hoảng & phản ứng nhanh"]],
  ["Chăm sóc & phối hợp", ["Chăm sóc sau bán", "Phản hồi & khiếu nại", "Bàn nhân viên Marketing"]],
];
/** Đang đứng trên chính nó, nên không vẽ lối quay về chính mình. */
const AN = ["Bàn Phó TGĐ Marketing"];

/* KHÔNG MỘT MÃ MÀU NÀO DƯỚI ĐÂY. Mọi màu lấy từ biến của `tokens.css`, nên bộ giao diện tối đổi
   theo mà không phải sửa tệp này. Xem điểm (2) ở đầu tệp.
   Lưu ý khi sửa: KHÔNG được có dấu nháy ngược nào bên trong khối này — nó cắt đôi chuỗi mẫu và
   trang nổ lúc dựng. Đã vấp hai lần, đợt MKT-6 và MKT-7. */
const MAU = <style>{`
.pt-chidoc{font-size:calc(12/14*1rem);font-weight:700;color:var(--vtos-text-on-navy);
  background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);
  border-radius:999px;padding:5px 11px;white-space:nowrap}
.pt-nut{font-size:calc(12.5/14*1rem);font-weight:600;color:var(--vtos-navy);
  background:var(--vtos-text-on-navy);border:0;border-radius:8px;padding:6px 12px;
  cursor:pointer;font-family:inherit}
.pt-muc{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 9px}
.pt-muc h2{margin:0;font-size:calc(15/14*1rem);font-weight:700;color:var(--vtos-navy)}
.pt-luoi{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(248px,1fr));
  margin-bottom:22px}
.pt-dv{font-family:inherit;font-size:calc(12.5/14*1rem);font-weight:500;
  color:var(--vtos-text-mute);margin-left:5px;letter-spacing:0}
.pt-chu{font-family:inherit;font-size:calc(19/14*1rem);font-weight:700;color:var(--vtos-warning)}
.the-ct.pt-do{border-left:3px solid var(--vtos-danger)}
.the-ct.pt-do .the-so{color:var(--vtos-danger)}
.the-ct.pt-vang{border-left:3px solid var(--vtos-warning)}
.the-ct.pt-vang .the-so{color:var(--vtos-warning)}
.pt-nen .the-ct{background:var(--vtos-surface)}
.pt-vs{margin-top:6px}
.pt-vs summary{font-size:calc(12/14*1rem);color:var(--vtos-text-mute);cursor:pointer;
  list-style:none;font-weight:600;display:inline-block;
  border-bottom:1px dotted var(--vtos-text-mute)}
.pt-vs summary::-webkit-details-marker{display:none}
.pt-vs p{margin:6px 0 0;font-size:calc(12/14*1rem);color:var(--vtos-text-mute);line-height:1.6}
.pt-loi{background:var(--vtos-card);border:1px solid var(--vtos-line);
  border-radius:var(--vtos-radius-md);padding:13px 15px;display:grid;gap:12px 22px;
  grid-template-columns:repeat(auto-fit,minmax(215px,1fr))}
.pt-loi-nhom>div:first-child{font-size:calc(11/14*1rem);font-weight:700;letter-spacing:.07em;
  text-transform:uppercase;color:var(--vtos-text-mute);margin-bottom:5px}
.pt-loi-nhom a{display:block;font-size:calc(13/14*1rem);color:var(--vtos-text);
  text-decoration:none;padding:3px 0;border-bottom:1px solid var(--vtos-line)}
.pt-loi-nhom a:last-child{border-bottom:0}
.pt-loi-nhom a:hover{color:var(--vtos-navy)}
`}</style>;

/** Vẽ con số của một ô — BA TRẠNG THÁI, và không trạng thái nào được vẽ thành số 0.
 *  Một ô đọc hỏng mà hiện "0 việc" là nói với người ngồi bàn rằng hôm nay không có gì phải làm. */
function So({ o }: { o: O }) {
  if (o.trang_thai === "loi") return <div className="the-so pt-chu">chưa đọc được</div>;
  if (o.trang_thai === "chua_co") return <div className="the-so pt-chu">{o.chu}</div>;
  return <div className="the-so">
    {o.so_luong}{o.don_vi ? <span className="pt-dv">{o.don_vi}</span> : null}
  </div>;
}

function duoi(o: O) { return o.trang_thai === "loi" ? o.ly_do : o.ghi_chu; }

/** Một ô. `vs` là phần giải thích dài — xem điểm (4) ở đầu tệp: thu về một dòng bấm mở, không xoá. */
function TheO({ o, mau, vs }: { o: O; mau?: string; vs?: [string, string] }) {
  return (
    <div className={"the-ct" + (mau ? " pt-" + mau : "")}>
      <div className="the-nhan">{o.ten}</div>
      <So o={o} />
      {duoi(o) && <div className="the-duoi">{duoi(o)}</div>}
      {vs && <details className="pt-vs"><summary>{vs[0]}</summary><p>{vs[1]}</p></details>}
      {o.den && <Link className="the-cua" href={o.den}>Mở chỗ làm việc này →</Link>}
    </div>
  );
}

function BanPtgd() {
  const { toast } = useShell();
  const [d, setD] = useState<Ban | null>(null);
  const [dang, setDang] = useState(true);
  const homNay = useHomNay();

  const doc = useCallback(async () => {
    setDang(true);
    try { setD(await api("/marketing/ban-ptgd")); }
    catch (e) { toast(errMsg(e), true); }
    finally { setDang(false); }
  }, [toast]);
  useEffect(() => { doc(); }, [doc]);

  if (dang && !d) return <p className="muted">Đang đọc số…</p>;
  if (!d) return <p className="muted">Chưa đọc được bàn làm việc. Thử tải lại trang.</p>;

  const lay = (k: string) => d.o.find((x) => x.khoa === k);
  const nhieu = (ks: string[]) => ks.map(lay).filter(Boolean) as O[];

  const viec = nhieu(["lead_qua_han_phong", "lead_chua_gan", "ky_chua_chot"]);
  const hangDoi = nhieu(["noi_dung_cho_duyet", "chien_dich_cho_duyet", "pr_qua_han"]);
  const nen = nhieu(["sdt_phat_sinh", "chien_dich_dang_chay", "ty_le_chot", "ngan_sach_ky"]);

  const MUC: Record<string, string> = { do: "do", vang: "vang" };
  const daXep = new Set(NHOM.flatMap(([, ms]) => ms).concat(AN));
  const khac = LOI.filter(([ten]) => !daXep.has(ten));

  return (<>
    {/* (1) Thanh đầu bàn — khuôn chung `.mh01-ban` của đợt VH-30. */}
    <div className="mh01-ban">
      <h1 className="mh01-ban-ten">{d.ten}</h1>
      <div className="mh01-ban-cum">
        <span className="pt-chidoc">Chỉ đọc</span>
        <div className="mh01-ban-ngay"><span>Hôm nay</span>{homNay || "…"}</div>
        <button type="button" className="pt-nut" onClick={doc}>Đọc lại số</button>
      </div>
    </div>

    <div className="pt-muc"><h2>Việc cần xử lý</h2>
      <span className="muted">Ưu tiên tồn đọng</span></div>
    <div className="pt-luoi">
      {viec.map((o) => <TheO key={o.khoa} o={o} mau={MUC[o.muc]} />)}
    </div>

    <div className="pt-muc"><h2>Hàng đợi theo dõi</h2></div>
    <div className="pt-luoi">
      {hangDoi.map((o) => <TheO key={o.khoa} o={o} mau={MUC[o.muc]} />)}
    </div>

    {/* (3) Số nền đứng CUỐI và mang nền khác — luật (c) của đợt MKT-1. */}
    <div className="pt-muc"><h2>Số nền của kỳ</h2>
      <span className="muted">Để đọc việc ở trên, không phải việc phải làm</span></div>
    <div className="pt-luoi pt-nen">
      {nen.map((o) => <TheO key={o.khoa} o={o} />)}
    </div>

    {/* (4) Mười một lối gom vào MỘT dải. */}
    <div className="pt-muc"><h2>Lối điều hành</h2>
      <Link href="/marketing?tab=muc-luc">Mục lục đầy đủ →</Link></div>
    <div className="pt-loi">
      {NHOM.map(([ten, ms]) => {
        const muc = LOI.filter(([t]) => ms.includes(t));
        if (!muc.length) return null;
        return <div className="pt-loi-nhom" key={ten}>
          <div>{ten}</div>
          {muc.map(([t, u]) => <Link key={u + t} href={u}>{t}</Link>)}
        </div>;
      })}
      {/* Mục chưa xếp nhóm KHÔNG được rơi mất: nó hiện ra ở đây để có người xếp. */}
      {khac.length > 0 && <div className="pt-loi-nhom">
        <div>Khác — chưa xếp nhóm</div>
        {khac.map(([t, u]) => <Link key={u + t} href={u}>{t}</Link>)}
      </div>}
    </div>

    <p className="muted" style={{ marginTop: 16 }}>{d.luu_y}</p>
  </>);
}

export default function Page() {
  return <Shell>{MAU}<BanPtgd /></Shell>;
}
