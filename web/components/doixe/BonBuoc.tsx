"use client";
import { useCallback, useEffect, useState } from "react";
import "./BonBuoc.css";

/** KS-64 · 09/11/2026 — bộ phận dùng chung cho HAI cửa nhập bốn bước của Giám đốc đội xe,
 *  theo `02-Huong-dan-IT-Giam-doc-doi-xe-v3.3.docx` và bản demo `01-Demo-…v3.3.html`.
 *
 *  Vì sao tách ra một tệp riêng thay vì viết hai lần: hai cửa khác nhau ở bộ trường, nhưng
 *  GIỐNG NHAU ở đúng những thứ dễ làm sai — thanh bước, danh sách việc còn thiếu, màn đối
 *  chiếu trước khi gửi, tuyến duyệt chỉ-xem, và ô lưu nháp. Viết hai lần thì sáu tháng sau
 *  một bên sửa còn một bên không, và không ai biết bên nào mới đúng.
 *
 *  BA LUẬT CỦA BỘ NÀY, lấy từ chính tài liệu v3.3 và từ các bài học đã ghi trong hồ sơ KS:
 *
 *  1 · RỖNG KHÔNG PHẢI BẰNG 0. Ô chưa gõ hiện "Chưa nhập", không hiện "0 đ". Một ô trống đọc
 *      thành 0 là cách êm ái nhất để một chuyến thiếu tiền dầu trông như một chuyến lãi to.
 *
 *  2 · KHÔNG CHO ĐI TIẾP KHI CHƯA ĐỦ, VÀ NÓI RÕ THIẾU GÌ. Nút Tiếp mờ đi kèm một danh sách
 *      gạch đầu dòng gọi tên từng ô còn thiếu. Nút mờ mà không nói vì sao là bắt người dùng
 *      đi dò.
 *
 *  3 · KHÔNG HỨA ĐIỀU HỆ CHƯA LÀM. Tuyến duyệt ở bước 4 là MỘT BỨC HÌNH CHỈ XEM: VTOS hiện
 *      chưa có luồng duyệt đề nghị chi (B1 của KS-57 còn nguyên). Bước ấy nói thẳng câu đó ra
 *      chứ không vẽ bốn ô trông như đã chạy.
 */

export type TuyenMot = [string, string];

/** Thanh bốn bước. Bước đã qua bấm được để quay lại — người ta luôn muốn sửa lại ô vừa gõ,
 *  và bắt họ bấm "Quay lại" bốn lần là một cách phạt vô cớ. Bước CHƯA tới thì không bấm
 *  được: nhảy tới trước khi đủ dữ liệu chỉ để gặp một màn trống. */
export function ThanhBuoc({ ten, buoc, veBuoc }: { ten: string[]; buoc: number; veBuoc?: (i: number) => void }) {
  return <div className="bb-thanh" role="list">
    {ten.map((t, i) => {
      const cls = i < buoc ? "xong" : i === buoc ? "dang" : "";
      const bam = i < buoc && veBuoc;
      return <div key={t} role={bam ? "button" : "listitem"} tabIndex={bam ? 0 : undefined}
        className={`bb-buoc ${cls}`}
        onClick={bam ? () => veBuoc!(i) : undefined}
        onKeyDown={bam ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); veBuoc!(i); } } : undefined}
        aria-current={i === buoc ? "step" : undefined}>
        <i aria-hidden="true">{i < buoc ? "✓" : i + 1}</i>
        <span><b>Bước {i + 1}</b>{t}</span>
      </div>;
    })}
  </div>;
}

/** Danh sách việc còn thiếu của bước đang mở. Rỗng thì không vẽ gì. */
export function ConThieu({ ds }: { ds: string[] }) {
  if (!ds.length) return null;
  return <div className="bb-thieu"><b>Chưa gửi được – còn {ds.length} việc:</b>
    <ul>{ds.map((x) => <li key={x}>{x}</li>)}</ul></div>;
}

/** Một dòng của màn đối chiếu. `value` rỗng/undefined thì tự in "Chưa nhập" bằng chữ xám —
 *  đây là chỗ luật 1 được thi hành, nên nơi gọi KHÔNG phải nhớ tự làm. */
export function Cap({ nhan, value }: { nhan: string; value?: string | number | null }) {
  const trong = value === null || value === undefined || value === "";
  return <div className={`bb-cap ${trong ? "trong" : ""}`}>
    <span>{nhan}</span><strong>{trong ? "Chưa nhập" : value}</strong></div>;
}

export const KhoiXem = ({ children }: { children: React.ReactNode }) => <div className="bb-xem">{children}</div>;

/** Tuyến xử lý — CHỈ XEM. Xem luật 3 ở đầu tệp. */
export function TuyenDuyet({ tuyen, ghi }: { tuyen: TuyenMot[]; ghi: string }) {
  return <>
    <ol className="bb-tuyen">
      {tuyen.map(([ai, viec], i) => <li key={ai} className={i === 0 ? "day" : ""}>
        <i aria-hidden="true">{i === 0 ? "1" : i + 1}</i>
        <div><strong>{ai}</strong><small>{viec}</small></div>
        <em>{i === 0 ? "Đang lập" : "Bước sau · chỉ xem"}</em>
      </li>)}
    </ol>
    <p className="muted" style={{ marginTop: 10 }}>{ghi}</p>
  </>;
}

/** Ô xác nhận trước khi gửi. Bắt buộc, và câu chữ nói rõ người bấm đang xác nhận ĐIỀU GÌ —
 *  "Tôi đồng ý" không xác nhận gì cả. */
export function OXacNhan({ cho, doi, chu }: { cho: boolean; doi: (v: boolean) => void; chu: string }) {
  return <label className="bb-ok"><input type="checkbox" checked={cho} onChange={(e) => doi(e.target.checked)} />
    <span>{chu}</span></label>;
}

/** Nháp. LƯU TRONG MÁY NÀY, không lưu trên máy chủ — và câu đó phải hiện ra bằng chữ ở nơi
 *  gọi (cả hai cửa đều in). v3.3 §5 đòi nháp nhiều bước có phiên bản ở MÁY CHỦ; đó là B4 của
 *  KS-57, chưa làm. Cái ở đây chỉ cứu người gõ khỏi mất công khi đóng tab hay bấm nhầm, và
 *  nó không được phép tự nhận là nhiều hơn thế.
 *
 *  Bọc try/catch vì cửa sổ ẩn danh, trình duyệt chặn site data, hay dung lượng đầy đều làm
 *  localStorage NÉM LỖI — và mất nháp thì đáng tiếc, chứ sập cả biểu mẫu thì mất luôn phiếu. */
export function useNhap<T>(khoa: string, rong: () => T) {
  const [data, setData] = useState<T>(rong);
  const [daDoc, setDaDoc] = useState(false);
  const [coNhapCu, setCoNhapCu] = useState(false);

  useEffect(() => {
    try {
      const v = window.localStorage.getItem(khoa);
      if (v) { setData({ ...rong(), ...JSON.parse(v) }); setCoNhapCu(true); }
    } catch { /* không đọc được nháp thì mở biểu mẫu trắng, không chặn người gõ */ }
    setDaDoc(true);
  }, [khoa]);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!daDoc) return;   // đừng ghi đè nháp cũ bằng biểu mẫu trắng ở lần dựng đầu
    try { window.localStorage.setItem(khoa, JSON.stringify(data)); } catch { /* đầy hoặc bị chặn */ }
  }, [khoa, data, daDoc]);

  const xoaNhap = useCallback(() => {
    try { window.localStorage.removeItem(khoa); } catch { /* không xoá được thì thôi */ }
    setCoNhapCu(false); setData(rong());
  }, [khoa]);   // eslint-disable-line react-hooks/exhaustive-deps

  return { data, setData, xoaNhap, coNhapCu, daDoc };
}

/** Tiền để đọc. `null`/`undefined`/rỗng -> undefined để `Cap` in "Chưa nhập" (luật 1). */
export const tien = (v: any): string | undefined => {
  if (v === null || v === undefined || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString("vi-VN") + " đ" : undefined;
};
export const soDoc = (v: any): string | undefined => {
  if (v === null || v === undefined || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString("vi-VN") : undefined;
};
