"use client";
/** MKT-11 · BÀN LÀM VIỆC PHÓ TGĐ MARKETING — `/ptgd-mkt`. Chủ tịch duyệt 12/11/2026.
 *
 *  VIẾT RIÊNG, KHÔNG DÙNG CHUNG `BanMkt.tsx` NỮA — Chủ tịch chọn ngày 12/11/2026 sau khi xem bản
 *  v32. Cái giá của lựa chọn ấy đã nói rõ lúc quyết: hai bàn thành hai nguồn vẽ, và chúng sẽ lệch
 *  nhau về bố cục. Đổi lại, BA LUẬT NÓI THẬT nằm ở MÁY CHỦ chứ không ở màn hình —
 *
 *    · `trang_thai = loi`      → vẽ CHỮ "chưa đọc được", không vẽ số 0
 *    · `trang_thai = chua_co`  → vẽ `chu` ("Chưa xác định", "Chưa lập"), cũng không vẽ 0
 *    · ô mẫu số không cộng vào việc chờ
 *
 *  nên hai bàn không thể lệch nhau ở chỗ nói thật, chỉ lệch ở chỗ xếp hình.
 *
 *  KHÔNG CÓ Ô TỔNG, và đó là chủ ý. Cộng 25 lead quá hạn với 7.355 lead chưa gắn với 1 kỳ chưa
 *  chốt ra 7.381 "việc đang chờ" là một con số vô nghĩa. Tài liệu bàn giao dặn thẳng: một lead có
 *  thể thuộc nhiều nhóm nên không cộng các nhóm thành tổng người.
 *
 *  MƯỜI HAI LỐI ĐỌC THẲNG TỪ `GROUPS`, không chép tay. Mục nào chưa xếp nhóm thì rơi vào nhóm
 *  "Khác" và HIỆN RA — nên thêm một màn thứ mười ba về sau không thể rơi mất, và không cần một
 *  phép thử canh chỗ này.
 *
 *  KHÔNG GỌI `useSearchParams`, nên không cần ranh giới `Suspense` — luật ở
 *  `backend/tests/test_web_suspense_cho_search_params.py`.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell, GROUPS } from "@/components/Shell";
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

const MAU = <style>{`
body,.shell{background:#eef3f9!important}
main{max-width:1200px!important;margin:0 auto!important}
.pt-dau{display:flex;flex-wrap:wrap;gap:14px 20px;align-items:flex-start;
  justify-content:space-between;margin-bottom:26px}
.pt-eye{font-size:.71rem;font-weight:600;letter-spacing:.13em;text-transform:uppercase;
  color:#2c5fa2;margin:0 0 7px}
.pt-dau h1{font-size:1.8rem;line-height:1.18;margin:0 0 7px;color:#183c69}
.pt-sub{margin:0;color:#5d6d83;font-size:.9rem}
.pt-phai{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.pt-chidoc{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e1e7ef;
  border-radius:999px;padding:7px 14px;font-size:.8rem;font-weight:600;color:#5d6d83;min-height:40px}
.pt-muc{display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  flex-wrap:wrap;margin:0 0 13px}
.pt-muc h2{font-size:1.1rem;margin:0;color:#183c69}
.pt-muc .phu{color:#5d6d83;font-size:.82rem}
.pt-the{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(236px,1fr));margin-bottom:28px}
.pt-the>div{background:#fff;border:1px solid #eef2f7;border-radius:14px;padding:17px 19px 14px;
  box-shadow:0 1px 2px #12305410,0 3px 10px #12305414;display:flex;flex-direction:column;gap:5px;min-width:0}
.pt-nhan{color:#5d6d83;font-size:.82rem;font-weight:500}
.pt-so{font-size:2rem;line-height:1.15;color:#183c69;margin-top:4px}
.pt-so.chu{font-size:1.4rem;color:#a66a00}
.pt-so.hong{font-size:1.05rem;color:#a66a00;font-weight:700}
.pt-so.do{color:#b72f45}
.pt-cap{color:#5d6d83;font-size:.81rem;margin:0}
.pt-cua{margin-top:auto;padding-top:12px}
.pt-cua a{font-size:.84rem;font-weight:600;color:#2c5fa2;text-decoration:none}
.pt-cot{display:grid;gap:18px;grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);margin-bottom:28px}
.pt-hop{background:#fff;border:1px solid #eef2f7;border-radius:16px;padding:20px 22px;
  box-shadow:0 1px 2px #12305410,0 3px 10px #12305414}
.pt-hang{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 14px;align-items:center;
  padding:16px 0;border-top:1px solid #eef2f7}
.pt-hop .pt-hang:first-of-type{border-top:0;padding-top:4px}
.pt-hang b{font-size:1rem}
.pt-hang p{margin:3px 0 0;color:#5d6d83;font-size:.84rem;grid-column:1}
.pt-pill{grid-column:1;justify-self:start;margin-top:8px;border-radius:7px;padding:3px 10px;
  font-size:.75rem;font-weight:600;background:#fdf4e3;color:#a66a00}
.pt-pill.do{background:#fdeef1;color:#b72f45}
.pt-hang .act{grid-column:2;grid-row:1/4}
.pt-dh{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;align-items:center;
  padding:15px 0;border-top:1px solid #eef2f7;text-decoration:none;color:inherit}
.pt-hop .pt-dh:first-of-type{border-top:0;padding-top:2px}
.pt-dh b{font-size:.96rem}
.pt-dh p{margin:2px 0 0;color:#5d6d83;font-size:.82rem;grid-column:1}
.pt-dh .pt-so{grid-row:1/3;font-size:1.55rem;margin:0}
.pt-ghi{margin:16px 0 0;padding-top:14px;border-top:1px solid #eef2f7;color:#5d6d83;font-size:.8rem}
.pt-chuc{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(238px,1fr));margin-bottom:22px}
.pt-nhom{background:#fff;border:1px solid #eef2f7;border-radius:14px;overflow:hidden;
  box-shadow:0 1px 2px #12305410,0 3px 10px #12305414}
.pt-nhom .dinh{background:#f5f8fc;border-bottom:1px solid #eef2f7;padding:13px 17px;
  font-weight:600;font-size:.92rem;color:#183c69}
.pt-nhom ul{list-style:none;margin:0;padding:4px 17px 10px}
.pt-nhom li{border-top:1px solid #eef2f7}
.pt-nhom li:first-child{border-top:0}
.pt-nhom a{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 0;
  text-decoration:none;color:#16233a;font-size:.88rem;min-height:44px}
@media (max-width:900px){.pt-cot{grid-template-columns:1fr}}
@media (max-width:680px){
  .pt-dau h1{font-size:1.42rem}
  .pt-so{font-size:1.7rem}
  .pt-hang{grid-template-columns:1fr}
  .pt-hang .act{grid-column:1;grid-row:auto;justify-self:start;margin-top:10px}
}
`}</style>;

/** Vẽ con số của một ô — BA TRẠNG THÁI, và không trạng thái nào được vẽ thành số 0. */
function So({ o, do_ }: { o: O; do_?: boolean }) {
  if (o.trang_thai === "loi") return <div className="pt-so hong">chưa đọc được</div>;
  if (o.trang_thai === "chua_co") return <div className="pt-so chu">{o.chu}</div>;
  return <div className={"pt-so" + (do_ && o.so_luong ? " do" : "")}>
    {o.so_luong}{o.don_vi ? <span style={{ fontSize: ".78rem", color: "#5d6d83" }}> {o.don_vi}</span> : null}
  </div>;
}

function duoi(o: O) { return o.trang_thai === "loi" ? o.ly_do : o.ghi_chu; }

function BanPtgd() {
  const { toast } = useShell();
  const [d, setD] = useState<Ban | null>(null);
  const [dang, setDang] = useState(true);

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

  const theoDoi = nhieu(["sdt_phat_sinh", "chien_dich_dang_chay", "ty_le_chot", "ngan_sach_ky"]);
  const viec = nhieu(["lead_qua_han_phong", "lead_chua_gan", "ky_chua_chot"]);
  const hangDoi = nhieu(["noi_dung_cho_duyet", "chien_dich_cho_duyet", "pr_qua_han"]);

  const daXep = new Set(NHOM.flatMap(([, ms]) => ms).concat(AN));
  const khac = LOI.filter(([ten]) => !daXep.has(ten));

  return (<>
    <div className="pt-dau">
      <div>
        <p className="pt-eye">Vietourist · Marketing</p>
        <h1>{d.ten}</h1>
        <p className="pt-sub">Phòng Marketing · Theo dõi kết quả và điều phối công việc</p>
      </div>
      <div className="pt-phai">
        <span className="pt-chidoc">◉ Chỉ đọc</span>
        <button type="button" className="act grey" onClick={doc}>Đọc lại số</button>
      </div>
    </div>

    <div className="pt-muc"><h2>Kết quả theo dõi</h2></div>
    <div className="pt-the">
      {theoDoi.map((o) => <div key={o.khoa}>
        <span className="pt-nhan">{o.ten}</span>
        <So o={o} />
        <p className="pt-cap">{duoi(o)}</p>
        {o.den && <span className="pt-cua"><Link href={o.den}>Mở chỗ làm việc này →</Link></span>}
      </div>)}
    </div>

    <div className="pt-cot">
      <section className="pt-hop">
        <div className="pt-muc"><h2>Việc cần xử lý</h2><span className="phu">Ưu tiên tồn đọng</span></div>
        {viec.map((o) => <div className="pt-hang" key={o.khoa}>
          <b>{o.trang_thai === "san_sang" ? o.so_luong + " " : ""}{o.ten}</b>
          <p>{duoi(o)}</p>
          {o.muc && <span className={"pt-pill" + (o.muc === "do" ? " do" : "")}>
            {o.muc === "do" ? "Quá hạn" : "Cần bổ sung"}</span>}
          {o.den && <Link className="act" href={o.den}>Mở chỗ làm việc này →</Link>}
        </div>)}
      </section>

      <section className="pt-hop">
        <div className="pt-muc"><h2>Hàng đợi theo dõi</h2></div>
        {hangDoi.map((o) => <Link className="pt-dh" key={o.khoa} href={o.den || "#"}>
          <b>{o.ten}</b>
          <So o={o} do_ />
          <p>{duoi(o)}</p>
        </Link>)}
        <p className="pt-ghi">{d.luu_y}</p>
      </section>
    </div>

    <div className="pt-muc"><h2>Chức năng điều hành</h2>
      <Link href="/marketing?tab=muc-luc">Mục lục đầy đủ →</Link></div>
    <div className="pt-chuc">
      {NHOM.map(([ten, ms]) => {
        const muc = LOI.filter(([t]) => ms.includes(t));
        if (!muc.length) return null;
        return <div className="pt-nhom" key={ten}>
          <div className="dinh">{ten}</div>
          <ul>{muc.map(([t, u]) => <li key={u + t}><Link href={u}>{t}<span>›</span></Link></li>)}</ul>
        </div>;
      })}
      {/* Mục chưa xếp nhóm KHÔNG được rơi mất: nó hiện ra ở đây để có người xếp. */}
      {khac.length > 0 && <div className="pt-nhom">
        <div className="dinh">Khác — chưa xếp nhóm</div>
        <ul>{khac.map(([t, u]) => <li key={u + t}><Link href={u}>{t}<span>›</span></Link></li>)}</ul>
      </div>}
    </div>
  </>);
}

export default function Page() {
  return <Shell>{MAU}<BanPtgd /></Shell>;
}
