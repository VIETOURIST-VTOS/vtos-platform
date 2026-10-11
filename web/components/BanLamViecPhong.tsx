"use client";
/** BD-1 · BÀN LÀM VIỆC CỦA MỘT PHÒNG — việc cần làm, đứng TRÊN bảng chỉ tiêu (12/10/2026).
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  VÌ SAO NẰM TRÊN BẢNG CHỈ TIÊU
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  Chủ tịch chốt 12/10/2026, sau khi xem bản dựng thử: người mở máy buổi sáng là để LÀM VIỆC.
 *  Chỉ tiêu tháng xem một lần đầu ngày là đủ, nên nó lùi xuống dưới — không bỏ, chỉ đổi chỗ.
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  MÀN HÌNH KHÔNG TÍNH MỘT CON SỐ NÀO (ranh giới 09/9/2026)
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  Nó vẽ đúng thứ máy chủ gửi xuống, kể cả ô rỗng và ô hỏng. Tổng "đang chờ" do máy chủ cộng:
 *  cộng ở đây là dựng cái đầu thứ hai cho một phép cộng đã có chủ, và chỉ cần một ô chưa đọc được
 *  là hai con số lệch nhau mà không ai biết.
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  BA THỨ PHẢI GIỮ KHI AI ĐÓ DỌN MÃ
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  1. SỐ 0 VÀ LỖI LÀ HAI MÀU KHÁC NHAU. Ô `trang_thai !== "san_sang"` hiện lý do, KHÔNG hiện 0.
 *     Một ô đọc hỏng mà in "0 việc" là bảo trưởng phòng rằng hôm nay không có gì phải làm.
 *  2. MÀU KHÔNG BAO GIỜ ĐỨNG MỘT MÌNH. Mỗi vạch màu đi kèm một nhãn chữ (`nhan_muc`) — người
 *     không phân biệt được màu vẫn phải đọc được mức độ.
 *  3. KHÔNG CÓ NÚT HÀNH ĐỘNG. Mọi ô chỉ dẫn SANG màn hình nguồn. Duyệt chi hay đóng sổ ngay trên
 *     bảng tổng là việc khó lùi nhất, và quyền của nó nằm ở màn hình nguồn chứ không ở đây.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

type Dong = { chinh: string; phu: string; phai: string; phai_phu: string; kieu: string };
type O = {
  khoa: string; ten: string; so_luong: number | null; don_vi: string;
  muc: string; nhan_muc: string; ghi_chu: string; den: string; nguon: string;
  dong: Dong[]; trang_thai: string; ly_do: string;
};
export type Ban = {
  phong: string; co_ban: boolean; ten?: string; o: O[];
  tong_dang_cho: number | null; doc_luc?: string; vi_sao?: string;
};

const TAG: Record<string, "red" | "warn" | "ok"> = { do: "red", vang: "warn", xanh: "ok" };

function OViec({ o }: { o: O }) {
  const hong = o.trang_thai !== "san_sang";
  return (
    <article className={"blv-o" + (hong ? " blv-hong" : " blv-" + (o.muc || "xanh"))}>
      <div className="blv-dau">
        <div className="blv-ten">
          <b>{o.ten}</b>
          {!hong && o.nhan_muc &&
            <Tag cls={TAG[o.muc] || "ok"}>{o.nhan_muc}</Tag>}
        </div>
        {/* Rỗng KHÔNG phải 0 — xem điều 1 ở đầu tệp. */}
        {hong ? <span className="blv-so muted">—</span>
              : <b className="blv-so">{o.so_luong}</b>}
      </div>

      {hong ? (
        <p className="muted blv-ly-do">
          {o.trang_thai === "thieu_nguon"
            ? <>Chưa có nguồn cho ô này. {o.ly_do}</>
            : <>Không đọc được ô này, nên màn hình <b>không hiện con số nào</b> thay vì hiện 0.
               Lý do: {o.ly_do}</>}
        </p>
      ) : (<>
        <ul className="blv-dong">
          {o.dong.length ? o.dong.map((d, i) => (
            <li key={i}>
              <span className="blv-trai">{d.chinh}{d.phu && <small>{d.phu}</small>}</span>
              <span className={"blv-phai" + (d.kieu ? " blv-" + d.kieu : "")}>
                {d.phai}{d.phai_phu && <small>{d.phai_phu}</small>}
              </span>
            </li>
          )) : <li className="muted">Không còn hồ sơ nào trong hàng đợi này.</li>}
        </ul>
        <div className="blv-chan">
          <span className="muted">{o.ghi_chu}</span>
          {o.den && <Link className="blv-den" href={o.den}>Mở màn hình nguồn →</Link>}
        </div>
        <p className="muted blv-nguon">Nguồn: {o.nguon}</p>
      </>)}
    </article>
  );
}

export default function BanLamViecPhong({ phong }: { phong: string }) {
  const { toast } = useShell();
  const [d, setD] = useState<Ban | null>(null);
  const [xong, setXong] = useState(false);

  useEffect(() => {
    let song = true;
    api<Ban>(`/bao-cao/ban-lam-viec?phong=${encodeURIComponent(phong)}`)
      .then((r) => { if (song) { setD(r); setXong(true); } })
      // Bàn hỏng KHÔNG được chặn bảng chỉ tiêu bên dưới: trang vẫn dựng tiếp, chỉ mất phần bàn.
      .catch((e) => { if (song) { setXong(true); toast(errMsg(e), true); } });
    return () => { song = false; };
  }, [phong, toast]);

  if (!xong) return <p className="muted">Đang gom việc cần làm…</p>;
  // Phòng chưa khai bàn thì KHÔNG vẽ một cái bàn trống: bàn trống trông y hệt "hôm nay không có
  // việc gì", mà sự thật là chưa ai dựng hàng đợi cho phòng ấy.
  if (!d || !d.co_ban) return null;

  return (
    <section className="blv" aria-label="Việc cần làm của phòng">
      <div className="blv-tieu-de">
        <div>
          <h2>Việc cần làm</h2>
          <p className="muted">{d.o.length} nhóm công việc · ưu tiên xử lý quá hạn</p>
        </div>
        <span className="blv-tong">
          {d.tong_dang_cho === null
            ? <span className="muted">Chưa đủ dữ liệu để cộng tổng</span>
            : <><b>{d.tong_dang_cho}</b> đang chờ</>}
        </span>
      </div>

      <div className="blv-luoi">{d.o.map((o) => <OViec key={o.khoa} o={o} />)}</div>

      <p className="muted blv-ghi">
        Bàn này <b>chỉ đọc</b> — mọi ô dẫn sang màn hình nguồn, nơi có đủ bộ lọc và đủ quyền để
        xử lý. Các con số ở đây <b>không cộng vào</b> bảng chỉ tiêu bên dưới: hàng đợi đếm hồ sơ
        đang chờ tại thời điểm này, bảng chỉ tiêu đếm theo kỳ báo cáo.
      </p>
    </section>
  );
}
