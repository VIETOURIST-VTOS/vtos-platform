"use client";
/** KHỐI "TỒN ĐỌNG" – màn hình 01, theo bản vẽ V1.2 (13/9/2026).
 *
 *  BẢN VẼ GHI "Tồn đọng theo bộ phận". Ở đây gom theo LOẠI CẢNH BÁO, không phải theo bộ phận, và
 *  nói thẳng điều đó ra trên màn hình. Lý do: máy chủ trả về mỗi cảnh báo một `kind` (mã loại) và
 *  một `message`, KHÔNG trả về bộ phận phụ trách. Muốn ra "theo bộ phận" thì phải có một bảng khai
 *  loại-cảnh-báo → bộ-phận, và bảng ấy là một tuyên bố nghiệp vụ, không phải thứ màn hình được
 *  đoán: đoán sai một dòng là đẩy việc sang nhầm phòng, mà không ai biết vì nhìn vẫn hợp lý. Nên
 *  màn hình gom theo đúng cái máy chủ có, và ghi rõ phần còn thiếu là bảng khai kia.
 *
 *  VÌ SAO PHẢI GOM: bảng cũ đổ thẳng danh sách phẳng – trên bản chạy thật là sáu mươi dòng gần
 *  giống hệt nhau ("… thiếu báo cáo ngày 2 ngày liên tiếp"), cuộn hết màn hình mà không cho biết
 *  tồn đọng đang nằm ở đâu. Gom lại thì đọc một cái là thấy: loại nào bao nhiêu, nặng nhất là loại
 *  nào. Danh sách chi tiết vẫn còn nguyên, nằm trong phần bung ra.
 *
 *  RANH GIỚI 09/9 GIỮ NGUYÊN: khối này KHÔNG tự tính thêm con số nghiệp vụ nào. Nó chỉ đếm lại
 *  đúng những dòng máy chủ đã gửi, và mọi con số nó không có nguồn thì để trống kèm chỗ xem tiếp.
 */
import Link from "next/link";
import { useState } from "react";
import { Tag } from "@/components/ui";

export type CanhBao = { id?: any; kind?: string; level?: string; message?: string };

/** Xếp hạng mức nặng để chọn mức đại diện cho cả nhóm. Tên mức do máy chủ đặt; mức lạ coi như nhẹ
 *  nhất chứ không bỏ dòng đi – bỏ dòng là giấu việc. */
const NANG: Record<string, number> = { red: 3, danger: 3, warn: 2, warning: 2, ok: 1, info: 1 };
const nang = (m?: string) => NANG[String(m || "").toLowerCase()] ?? 0;

export type Nhom = { kind: string; so: number; muc: string; vi_du: string };

/** Gom theo `kind`, đếm, rồi xếp nhiều trước. Cùng số lượng thì loại nặng hơn đứng trước – đọc từ
 *  trên xuống là đọc theo thứ tự đáng lo dần. */
export function gomTheoLoai(ds: CanhBao[]): Nhom[] {
  const b = new Map<string, Nhom>();
  for (const a of ds || []) {
    const kind = a.kind || "(không rõ loại)";
    const cu = b.get(kind);
    if (!cu) b.set(kind, { kind, so: 1, muc: a.level || "", vi_du: a.message || "" });
    else {
      cu.so += 1;
      if (nang(a.level) > nang(cu.muc)) { cu.muc = a.level || ""; cu.vi_du = a.message || ""; }
    }
  }
  return [...b.values()].sort((x, y) => y.so - x.so || nang(y.muc) - nang(x.muc));
}

export default function KhoiTonDong({ ds, tong }: { ds: CanhBao[]; tong?: number | null }) {
  const [bung, setBung] = useState(false);
  const co = ds || [];
  const nhom = gomTheoLoai(co);
  /* `tong` là số tồn đọng THẬT của máy chủ; `co.length` chỉ là số dòng gửi kèm trang này. Hai con
     số khác nhau thì phải nói ra, chứ không lấy cái nào thay cái nào. */
  const cat = typeof tong === "number" && tong > co.length;

  return (
    <div className="panel" id="ton-dong">
      <div className="mh01-dau">
        {/* TÊN KHỐI GIỮ NGUYÊN CỦA VTOS (anh Tuấn chốt 13/9/2026). Bản vẽ V1.4 đề nghị đổi thành
            "Rủi ro & việc cần theo dõi"; anh Tuấn giữ "Tồn đọng cần xử lý" cho khớp tên thẻ chỉ
            tiêu ở trên – hai chỗ nói về cùng một thứ thì phải gọi cùng một tên. */}
        <h2>Tồn đọng cần xử lý</h2>
        {typeof tong === "number"
          ? <span className="tag">{tong} cảnh báo đang mở</span>
          : <span className="tag">Chưa có tổng số</span>}
      </div>

      {co.length === 0
        ? <p className="muted">Không có cảnh báo nào đang mở.</p>
        : <>
            <table className="td-bang">
              <thead>
                <tr><th>Việc cần theo dõi</th><th className="td-so">Số việc</th><th>Mức nặng nhất</th></tr>
              </thead>
              <tbody>
                {nhom.map((n) => (
                  <tr key={n.kind}>
                    <td>
                      {/* MÃ MÁY GIỮ NGUYÊN (anh Tuấn chốt 13/9/2026). Bản vẽ V1.4 đề nghị đổi mã
                          thành câu tiếng Việt; anh Tuấn giữ mã của VTOS vì mã là thứ tra được
                          ngược về robot đã phát ra nó, còn câu dịch thì mỗi người nhớ một kiểu.
                          Câu ví dụ ngay dưới đã đủ cho người đọc hiểu loại này là gì. */}
                      <b>{n.kind}</b>
                      <div className="muted td-vd">{n.vi_du}</div>
                    </td>
                    <td className="td-so">{n.so}</td>
                    <td>{n.muc ? <Tag cls={n.muc}>{n.muc}</Tag> : <span className="muted">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {cat && (
              <p className="muted">
                Bảng trên gom <b>{co.length}</b> cảnh báo mới nhất mà máy chủ gửi kèm màn hình này,
                trong tổng số <b>{tong}</b> đang mở. Muốn xem đủ thì mở{" "}
                <Link href="/alerts">trang Cảnh báo →</Link>
              </p>
            )}

            <p className="muted">
              Gom theo <b>loại cảnh báo</b>, chưa gom được theo bộ phận: máy chủ chưa khai bộ phận
              phụ trách cho từng loại. Đây là phần còn thiếu – <b>Công nghệ thông tin</b> khai bảng
              loại&nbsp;→&nbsp;bộ phận thì khối này chuyển sang gom theo bộ phận đúng như bản vẽ.
            </p>

            <button className="act grey" onClick={() => setBung(!bung)} aria-expanded={bung}>
              {bung ? "Thu gọn danh sách" : `Xem từng dòng (${co.length})`}
            </button>
            {bung && (
              <table className="td-bang td-chi-tiet">
                <tbody>
                  {co.map((a, i) => (
                    <tr key={a.id ?? i}>
                      <td>{a.level ? <Tag cls={a.level}>{a.kind}</Tag> : <b>{a.kind}</b>}</td>
                      <td>{a.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>}
    </div>
  );
}
