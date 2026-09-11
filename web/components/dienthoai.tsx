"use client";
import { useEffect, useState } from "react";

/** TC-4 · UI-03 — bộ phận dùng chung cho BẢN ĐIỆN THOẠI.
 *
 *  Lệnh giao đòi bốn điều ở bản điện thoại: MỘT ô chọn mốc · thẻ gập được · bốn ô cảnh báo xếp 2×2 ·
 *  KHÔNG cuộn ngang. Bốn điều ấy không phải bốn chỗ sửa CSS — chúng là bốn thói quen phải áp cho mọi
 *  màn hình, nên viết thành bộ phận dùng chung ở đây thay vì sửa từng trang.
 *
 *  VÌ SAO KHÔNG CUỘN NGANG LÀ ĐIỀU KHÓ NHẤT TRONG BỐN ĐIỀU
 *  --------------------------------------------------------
 *  Cách chữa quen tay là bọc bảng trong một ô cuộn ngang (`.wrap` của hệ thống này đang làm vậy).
 *  Trên điện thoại nó hỏng theo kiểu im lặng: người dùng thấy ba cột đầu, không thấy có cột thứ tư,
 *  và đọc một bảng tiền bị cắt mất cột mà tưởng là đã đọc hết. Không ai báo lỗi, vì không ai biết
 *  mình đang thiếu gì.
 *
 *  `BangDoc` chữa bằng cách đổi HÌNH chứ không đổi độ rộng: trên màn rộng nó là bảng thật, dưới
 *  640px mỗi dòng thành một thẻ, mỗi ô mang theo NHÃN CỘT của chính nó. Nhãn lấy từ `data-nhan`, do
 *  bộ phận này tự gắn — không để người viết trang tự gắn, vì chỗ nào quên là chỗ ấy hiện một con số
 *  không có tên.
 *
 *  Đổi hình bằng CSS, không bằng JavaScript đo bề rộng màn hình: đo bằng JavaScript thì lần vẽ đầu
 *  ở máy chủ luôn đoán sai, và người dùng thấy bảng nhảy một cái khi trang tải xong.
 */

/* ============================================================================ thẻ gập được */

const KHOA_THE = "vtos_the_gap";

/** Thẻ gập được. `ma` là khóa nhớ trạng thái; `moSan` là trạng thái lần đầu.
 *
 *  Nhớ theo NGƯỜI DÙNG, như thanh dọc: hai người dùng chung một máy thì người sau không thừa hưởng
 *  các thẻ người trước đã gập. Không có `nguoi` thì không nhớ gì cả — thà quên còn hơn nhớ nhầm
 *  sang tài khoản khác.
 *
 *  Phần thân vẫn nằm trong cây khi gập (dùng `hidden`), không bị gỡ bỏ: gỡ đi thì mỗi lần mở lại
 *  phải tải lại dữ liệu, và trên mạng điện thoại người dùng phải chờ thêm một lần nữa cho thứ họ
 *  vừa nhìn thấy cách đó ba giây.
 */
export function The({ ma, tieuDe, phu, moSan = true, nguoi, children }: {
  ma: string; tieuDe: React.ReactNode; phu?: React.ReactNode; moSan?: boolean;
  nguoi?: string; children: React.ReactNode;
}) {
  const [mo, setMo] = useState(moSan);
  const khoa = nguoi ? `${KHOA_THE}_${nguoi}_${ma}` : "";

  useEffect(() => {
    if (!khoa) return;
    try {
      const v = localStorage.getItem(khoa);
      if (v === "1" || v === "0") setMo(v === "1");
    } catch { /* máy chặn localStorage thì dùng mặc định – không phải lỗi */ }
  }, [khoa]);

  function doi() {
    const moi = !mo;
    setMo(moi);
    if (khoa) { try { localStorage.setItem(khoa, moi ? "1" : "0"); } catch { /* bỏ qua */ } }
  }

  return (
    <section className="panel the">
      <button type="button" className="the-dau" onClick={doi} aria-expanded={mo}
        title={mo ? "Gập thẻ này" : "Mở thẻ này"}>
        <span className="the-mui" aria-hidden="true">{mo ? "▾" : "▸"}</span>
        <h2>{tieuDe}</h2>
        {phu ? <span className="the-phu">{phu}</span> : null}
      </button>
      <div className="the-than" hidden={!mo}>{children}</div>
    </section>
  );
}

/* ============================================================================ bốn ô cảnh báo 2×2 */

export type O = { nhan: string; so: React.ReactNode; muc?: "" | "ok" | "warn" | "red"; href?: string; chuThich?: string };

/** Bốn ô cảnh báo, xếp 2×2 trên điện thoại và một hàng trên màn rộng.
 *
 *  ĐÚNG BỐN Ô. Không phải một con số tùy ý: 2×2 chỉ là 2×2 khi có bốn. Năm ô thì hàng dưới lẻ một
 *  ô và mắt đọc thành "ô thứ năm quan trọng hơn"; ba ô thì để trống một góc. Nhận nhiều hơn bốn thì
 *  cắt, và nói ra là đã cắt — chứ không lặng lẽ bỏ mất một cảnh báo.
 */
export function BonO({ o }: { o: O[] }) {
  const bon = o.slice(0, 4);
  const thua = o.length - bon.length;
  return (
    <>
      <div className="bon-o">
        {bon.map((x, i) => {
          const trong = (
            <>
              <b>{x.so}</b>
              <span>{x.nhan}</span>
            </>
          );
          return x.href
            ? <a key={i} className={"o-cb " + (x.muc || "")} href={x.href} title={x.chuThich || x.nhan}>{trong}</a>
            : <div key={i} className={"o-cb " + (x.muc || "")} title={x.chuThich || x.nhan}>{trong}</div>;
        })}
      </div>
      {thua > 0 && <p className="muted">Còn {thua} nhóm cảnh báo nữa không nằm trong bốn ô này.</p>}
    </>
  );
}

/* ============================================================================ một ô chọn mốc */

export type Moc = { ma: string; ten: string };

/** MỘT ô chọn mốc cho bản điện thoại.
 *
 *  Bảng dòng tiền có bốn mốc. Trên màn rộng bốn mốc là bốn cột. Trên điện thoại bốn cột số tiền
 *  không vừa bề ngang, và ép chúng vừa thì hoặc chữ nhỏ đến mức đọc sai chữ số, hoặc phải cuộn
 *  ngang — tức là quay lại đúng cái hỏng im lặng ở đầu tệp này.
 *
 *  Nên: một mốc mỗi lần, người dùng tự chọn. Mốc đang chọn phải ĐỌC ĐƯỢC THÀNH CHỮ ngay cạnh bảng,
 *  không chỉ là một nút đang sáng — người ta cuộn xuống giữa bảng thì nút đã trôi khỏi màn hình, và
 *  một cột tiền không có tên là một cột tiền đọc sai.
 */
export function ChonMoc({ moc, dang, doi, nhan = "Mốc" }: {
  moc: Moc[]; dang: string; doi: (ma: string) => void; nhan?: string;
}) {
  const ten = moc.find((m) => m.ma === dang)?.ten || dang;
  return (
    <div className="chon-moc">
      <label htmlFor="chon-moc-o">{nhan}</label>
      <select id="chon-moc-o" value={dang} onChange={(e) => doi(e.target.value)}>
        {moc.map((m) => <option key={m.ma} value={m.ma}>{m.ten}</option>)}
      </select>
      <p className="muted moc-dang">Đang xem mốc <b>{ten}</b>.</p>
    </div>
  );
}

/* ============================================================================ bảng không cuộn ngang */

export type Cot = { ma: string; ten: string; so?: boolean };

/** Bảng đọc-được-trên-điện-thoại. Màn rộng: bảng thật. Dưới 640px: mỗi dòng một thẻ, mỗi ô có nhãn.
 *
 *  `khoa` là tên trường dùng làm khóa React. `dong` là dữ liệu thô; `ve` (không bắt buộc) đổi một ô
 *  thành nội dung hiển thị. Không có `ve` thì lấy thẳng giá trị.
 *
 *  Không nhận `children` tự do: nhận children thì người viết trang lại dựng `<tr><td>` bằng tay và
 *  quên `data-nhan`, và cái quên ấy chỉ hiện ra trên điện thoại — nơi gần như không ai thử.
 */
export function BangDoc<T extends Record<string, any>>({ cot, dong, khoa, ve, trong = "Không có dòng nào." }: {
  cot: Cot[]; dong: T[]; khoa: (d: T, i: number) => string | number;
  ve?: (d: T, c: Cot) => React.ReactNode; trong?: string;
}) {
  if (!dong.length) return <p className="muted">{trong}</p>;
  return (
    <table className="bang-doc">
      <thead><tr>{cot.map((c) => <th key={c.ma} className={c.so ? "num" : ""}>{c.ten}</th>)}</tr></thead>
      <tbody>
        {dong.map((d, i) => (
          <tr key={khoa(d, i)}>
            {cot.map((c) => (
              // data-nhan là chỗ nhãn cột đi theo ô xuống bản điện thoại. Gắn ở đây, không để trang
              // tự gắn: chỗ nào quên là chỗ ấy hiện một con số không có tên.
              <td key={c.ma} data-nhan={c.ten} className={c.so ? "num" : ""}>
                {ve ? ve(d, c) : d[c.ma]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
