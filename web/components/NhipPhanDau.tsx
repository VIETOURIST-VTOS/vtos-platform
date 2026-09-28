"use client";
/** BIỂU ĐỒ PHẤN ĐẤU CỦA NHÂN VIÊN KINH DOANH — TC-91, Chủ tịch chốt 28/9/2026.
 *
 *  "để cho nv thấy được động lực phấn đấu hằng ngày theo biểu đồ doanh thu của mình"
 *  và "chia ra nhiều mức, không nên giới hạn".
 *
 *  BA THỨ TRÊN MỘT HÌNH, CÙNG MỘT TRỤC (đồng):
 *    · lũy kế thực hiện       – mình đang ở đâu
 *    · nhịp cần đi            – đến hôm nay lẽ ra phải ở đâu; đây là thứ làm cho nó HẰNG NGÀY.
 *                               Không có nó, "đã bán 180 triệu" đọc ngày 5 và ngày 25 giống hệt.
 *    · nấc kế tiếp            – vạch ngang ngay phía trước, kèm còn thiếu bao nhiêu
 *
 *  KHÔNG VẼ TAY. Gọi `BieuDoDuong` của bộ dùng chung, nơi đã giữ năm luật: rỗng khác không, dưới
 *  hai điểm thì không vẽ, trục từ 0, MỘT trục tung, nối thẳng không làm mượt.
 *
 *  KHÔNG TÍNH MỘT CON SỐ NÀO. Mọi phép tính — lũy kế, nhịp, xếp nấc, bình quân ba tháng — nằm ở
 *  `doanh_thu_kd.nhip_cua_nguoi` trên máy chủ, đúng ranh giới 09/9. Tệp này chỉ vẽ.
 *
 *  ĐÍCH KHÔNG PHẢI TRẦN. Thang hiện đủ nấc, đích chỉ được tô đậm một dòng. Người vượt đích vẫn
 *  còn nấc phía trước — đó là chủ ý của Chủ tịch khi bảo "không nên giới hạn".
 */
import { BieuDoDuong, Duong, gonSo } from "@/components/BieuDo";
import { vnd } from "@/lib/api";

type Nac = {
  bac: string; pct_moc: number; nguong: number; he_so: number;
  y_nghia: string; hoa_hong_uoc: number; la_dich: boolean; con_thieu?: number;
};

export type Nhip = {
  ky: string; mang: string; thuoc_do: string;
  dich: number | null; so_ngay: number; ngay_thu: number;
  luy_ke: number; luy_ke_du_kien: number | null;
  dat_pct: number | null; nhip_hom_nay: number | null; truoc_sau_nhip: number | null;
  thang: Nac[]; bac_dang_o: Nac | null; bac_ke_tiep: Nac | null;
  do_bang: number; co_so_xep_bac: string;
  binh_quan_3_thang: { gia_tri: number; so_ky: number; cac_ky: { ky: string; loi_nhuan: number }[] } | null;
  diem: { ngay: string; luy_ke: number; luy_ke_du_kien: number | null; nhip: number | null }[];
};

export default function NhipPhanDau({ d }: { d: Nhip | null }) {
  if (!d) return null;
  const doan = d.mang === "doan";
  const dv = doan ? "lợi nhuận" : "doanh thu";

  const ds: Duong[] = [
    { ten: `Lũy kế ${dv}`, lop: "d1",
      diem: d.diem.map((p) => ({ nhan: p.ngay.slice(8), gt: p.luy_ke })) },
    { ten: "Nhịp cần đi", lop: "d2",
      diem: d.diem.map((p) => ({ nhan: p.ngay.slice(8), gt: p.nhip })) },
  ];
  // Đoàn: lớp DỰ KIẾN vẽ riêng, không cộng vào lớp chắc. Lợi nhuận chỉ chắc sau quyết toán; gộp
  // hai lớp là tạo một con số đẹp mà không ai kiểm được.
  if (doan) {
    ds.push({ ten: "Dự kiến theo dự toán (chưa quyết toán)", lop: "d3",
              diem: d.diem.map((p) => ({ nhan: p.ngay.slice(8), gt: p.luy_ke_du_kien })) });
  }

  const ke = d.bac_ke_tiep;
  const truoc_sau = d.truoc_sau_nhip;

  return (<>
    <BieuDoDuong
      ten={`Nhịp phấn đấu của tôi – ${d.ky}`}
      phu={doan
        ? "Lợi nhuận đoàn theo ngày tour kết thúc. Xếp bậc thì tính trên BÌNH QUÂN BA THÁNG (Điều 5), xem ô bên dưới."
        : "Doanh thu tính chỉ tiêu, theo ngày tour kết thúc — cùng cơ sở với bảng chấm chỉ tiêu."}
      ds={ds}
      nhan={d.diem.map((p) => p.ngay.slice(8))}
      dinh_dang="tien"
      moc={ke ? { gt: ke.nguong, nhan: `${ke.bac} · ${gonSo(ke.nguong)}` } : null}
      chan={<ChanNhip d={d} truoc_sau={truoc_sau} />}
    />
    {doan && d.binh_quan_3_thang && <BinhQuanBaThang bq={d.binh_quan_3_thang} />}
    <ThangNac d={d} />
  </>);
}

/** Một dòng nói thẳng: đang trên hay dưới nhịp, và còn bao nhiêu nữa lên nấc. */
function ChanNhip({ d, truoc_sau }: { d: Nhip; truoc_sau: number | null }) {
  if (d.dich === null) {
    return <span className="muted">Chưa giao đích cho kỳ này — biểu đồ chỉ hiện lũy kế.</span>;
  }
  return (<>
    {truoc_sau !== null && (truoc_sau >= 0
      ? <b style={{ color: "var(--teal)" }}>Trên nhịp {vnd(truoc_sau)}</b>
      : <b style={{ color: "var(--red)" }}>Dưới nhịp {vnd(-truoc_sau)}</b>)}
    {d.bac_dang_o
      ? <> · đang ở <b>{d.bac_dang_o.bac}</b> ({d.bac_dang_o.pct_moc}% mốc)</>
      : <> · <span className="muted">chưa tới nấc đầu tiên</span></>}
    {d.bac_ke_tiep
      ? <> · còn <b>{vnd(d.bac_ke_tiep.con_thieu || 0)}</b> nữa lên <b>{d.bac_ke_tiep.bac}</b></>
      : <> · <b>đã tới nấc cao nhất</b></>}
  </>);
}

function BinhQuanBaThang({ bq }: { bq: NonNullable<Nhip["binh_quan_3_thang"]> }) {
  return (<div className="panel">
    <h2>Bình quân ba tháng – con số xếp bậc</h2>
    <p className="muted">
      Điều 5 Phòng Đoàn: một đoàn lớn mất hai ba tháng để tiếp cận, khảo sát, báo giá và ký, nhưng
      lợi nhuận chỉ ghi vào đúng tháng quyết toán. Nên bậc lương tính trên bình quân ba tháng, không
      phải tháng đơn lẻ. Đây là con số dùng để xếp bậc, khác với lũy kế tháng này trên biểu đồ.
    </p>
    <div className="kpis"><div className="kpi"><b>{vnd(bq.gia_tri)}</b><span>bình quân {bq.so_ky} kỳ</span></div></div>
    <table><thead><tr><th>Kỳ</th><th className="num">Lợi nhuận quyết toán</th></tr></thead>
      <tbody>{bq.cac_ky.map((x) => <tr key={x.ky}><td>{x.ky}</td><td className="num">{vnd(x.loi_nhuan)}</td></tr>)}</tbody></table>
  </div>);
}

function ThangNac({ d }: { d: Nhip }) {
  const doan = d.mang === "doan";
  return (<div className="panel wrap">
    <h2>Thang nấc – {d.thang.length} mức</h2>
    <p className="muted">
      {doan
        ? "Phụ lục A Phòng Đoàn: các nấc này quyết định PHẦN TRĂM LƯƠNG CƠ BẢN theo bình quân ba tháng. Hoa hồng thì KHÔNG theo nấc — Điều 7 cố ý bỏ bậc nhảy, trả thẳng 10% phần lợi nhuận vượt 20 triệu."
        : "Thang hệ số f của bảng chính sách. Hoa hồng tính trên PHẦN VƯỢT MỐC, không phải trên cả doanh thu."}
      {d.dich !== null && " Dòng tô đậm là mức công ty kỳ vọng — không phải điểm dừng, phía trên vẫn còn nấc."}
    </p>
    <table>
      <thead><tr><th>Bậc</th><th className="num">% mốc</th><th className="num">Ngưỡng</th>
        <th className="num">Hệ số</th><th className="num">{doan ? "Hoa hồng tại ngưỡng" : "Hoa hồng ước"}</th></tr></thead>
      <tbody>{d.thang.map((n) => {
        const dat = d.do_bang >= n.nguong;
        return (<tr key={n.bac} style={{ fontWeight: n.la_dich ? 700 : undefined,
                                         opacity: dat ? 1 : 0.62 }}>
          <td>{n.bac}{n.la_dich && <> <small className="muted">kỳ vọng</small></>}</td>
          <td className="num">{n.pct_moc}%</td>
          <td className="num">{vnd(n.nguong)}</td>
          <td className="num">{(n.he_so * 100).toFixed(1)}%</td>
          <td className="num">{vnd(n.hoa_hong_uoc)}</td>
        </tr>);
      })}</tbody>
    </table>
  </div>);
}
