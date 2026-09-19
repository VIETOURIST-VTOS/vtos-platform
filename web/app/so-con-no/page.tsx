"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** SỔ CHUYẾN CÒN NỢ — TC-71 · anh Tuấn 18/9/2026.
 *
 *  "em dựng luôn và viết code thuật toán để kéo số liệu về màn hình CT, TGĐ và toàn bộ các phòng
 *   ban liên quan"
 *
 *  Màn hình trả lời đúng một câu: TIỀN ĐÃ VỀ MÀ CHƯA VÀO SỔ ĐANG NẰM Ở ĐÂU.
 *
 *  Đo trên sổ thật 18/9/2026: 670 chuyến đã chạy xong, doanh thu thật 24,38 tỷ nằm trong máy, mà
 *  không hiện ở đâu trên màn hình chủ tịch vì chưa ai bấm đóng sổ. TC-71 kéo nó vào con số gộp;
 *  màn hình này là chỗ bấm vào để biết CHUYẾN NÀO, chứ không phải chỉ biết "còn 24 tỷ".
 *
 *  ── MÀN HÌNH CHỈ ĐỌC ──────────────────────────────────────────────────────────────────────────
 *  Không đóng sổ hộ ai. Anh Tuấn chọn đúng phương án này khi em hỏi ("Danh sách + đường dẫn sang
 *  chuyến"): đóng sổ là việc khó lùi, làm hàng loạt từ một màn hình tổng thì một cú bấm nhầm đi xa
 *  hơn nhiều so với cái lợi về tốc độ. Mỗi dòng có đường dẫn sang đúng chuyến để người có quyền tự
 *  làm ở cửa của họ.
 *
 *  ── MÀN HÌNH KHÔNG TỰ CỘNG MỘT CON SỐ NÀO ────────────────────────────────────────────────────
 *  Mọi con số lấy từ /api/v1/so-con-no. Cùng lý do đã ghi ở màn hình Lãi lỗ tour: bốn công
 *  thức lãi lỗ song song trong kho này sinh ra chính vì mỗi màn hình từng tự cộng một kiểu.
 *
 *  ── RỖNG KHÁC KHÔNG ──────────────────────────────────────────────────────────────────────────
 *  Chuyến chưa ai nhập số thì cột tiền để "—", không hiện 0. Hiện 0 ở đây là nói chuyến ấy chạy
 *  không thu được đồng nào, mà sự thật là chưa ai điền.
 */

const so = (v: any) => (v === null || v === undefined
  ? <span className="muted" title="Chưa có số – khác với bằng 0">—</span>
  : <>{vnd(v)}</>);

/** Bao lâu là "quá hạn" do máy chủ quyết (`ngay_qua_han`), màn hình chỉ vẽ lại. Gõ cứng 30 ở đây
 *  là dựng con số thứ hai cho cùng một luật, và ngày máy chủ đổi thì màn hình nói sai. */
function TreNgay({ n, qua }: { n: number; qua: boolean }) {
  if (!qua) return <span className="muted">{n} ngày</span>;
  return <b className="red">{n} ngày</b>;
}

function SoConNo() {
  const { toast } = useShell();
  const [tu, setTu] = useState("");
  const [den, setDen] = useState("");
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(true);

  const nap = useCallback(async () => {
    setDang(true);
    try {
      const q = new URLSearchParams();
      if (tu) q.set("tu", tu);
      if (den) q.set("den", den);
      setD(await api(`/so-con-no${q.toString() ? `?${q}` : ""}`));
    } catch (e) {
      toast(errMsg(e), true);
    } finally {
      setDang(false);
    }
  }, [tu, den, toast]);

  useEffect(() => { void nap(); }, [nap]);

  const rows: any[] = d?.rows || [];
  const thang: any[] = d?.theo_thang || [];
  const dinh = thang.reduce((a, t) => Math.max(a, Number(t.tien || 0)), 0);

  return (
    <>
      <section className="panel">
        <div className="mh01-dau">
          <h2>Sổ chuyến còn nợ</h2>
          <p className="muted v14-ghi">
            Chuyến đã khởi hành mà <b>chưa đóng sổ</b>. Doanh thu của chúng đã nằm trong con số
            doanh thu vận hành trên màn hình điều hành, nhưng <b>chưa vào sổ kế toán</b> — đó là
            chỗ chênh giữa VTOS và báo cáo tài chính.
            {d?.toan_cong_ty === false && <> Đang xem phần của đơn vị bạn.</>}
          </p>
        </div>

        {/* Ba con số đứng đầu: tổng nợ, phần quá hạn, và ai đi làm. Không có con số nào ở đây do
            màn hình tự cộng — xem chú thích đầu tệp. */}
        <div className="kpis">
          <div className="kpi">
            <b>{dang ? "…" : (d?.tong ?? 0)}</b><span>chuyến chưa đóng sổ</span>
          </div>
          <div className="kpi">
            <b>{dang ? "…" : so(d?.tien)}</b><span>doanh thu chưa vào sổ</span>
          </div>
          <div className="kpi">
            <b className={Number(d?.qua_han || 0) > 0 ? "red" : ""}>{dang ? "…" : (d?.qua_han ?? 0)}</b>
            <span>quá {d?.ngay_qua_han ?? 30} ngày</span>
          </div>
        </div>

        <p className="muted v14-ghi">
          <b>{d?.ai_dong_so || "Điều hành"}</b> đóng sổ ở từng chuyến. Màn hình này chỉ liệt kê,
          không đóng sổ hộ — đóng sổ là việc khó lùi nên phải bấm ở đúng chuyến, nơi nhìn thấy đủ
          dòng quyết toán.
        </p>
      </section>

      <section className="panel">
        <div className="mh01-dau"><h3>Đọng theo tháng khởi hành</h3></div>
        {thang.length === 0 && !dang && <p className="muted">Không còn chuyến nào nợ sổ.</p>}
        {/* MỘT TRỤC TUNG: mọi thanh chia cho cùng một đỉnh `dinh`, không mỗi thanh một thang đo. */}
        <div className="sn-cot">
          {thang.map((t) => (
            <div key={t.ky} className="sn-dong">
              <span className="sn-ky">{t.ky}</span>
              <span className="sn-thanh" aria-hidden="true">
                <i style={{ width: `${dinh > 0 ? (Number(t.tien) / dinh) * 100 : 0}%` }} />
              </span>
              <span className="sn-so">{vnd(t.tien)}</span>
              <span className="sn-dem muted">{t.chuyen} chuyến</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="mh01-dau">
          <h3>Từng chuyến</h3>
          <div className="sn-loc">
            <label>Từ tháng <input type="month" value={tu} onChange={(e) => setTu(e.target.value)} /></label>
            <label>Đến tháng <input type="month" value={den} onChange={(e) => setDen(e.target.value)} /></label>
          </div>
        </div>

        {/* Bảng rộng cuộn NGANG TRONG VÙNG BẢNG, không đẩy cả trang trượt — luật giao diện TC-67. */}
        <div className="wrap bd-nhanx">
          <table>
            <thead>
              <tr>
                <th>Mã chuyến</th><th>Khởi hành</th><th>Trạng thái</th>
                <th className="num">Doanh thu</th><th className="num">Giá vốn</th>
                <th className="num">Đã chạy</th><th></th>
              </tr>
            </thead>
            <tbody>
              {dang && <tr><td colSpan={7} className="muted">Đang tải…</td></tr>}
              {!dang && rows.length === 0 && (
                <tr><td colSpan={7} className="muted">Không còn chuyến nào nợ sổ.</td></tr>
              )}
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link href={r.duong_dan}>{r.ma}</Link>
                    {r.gan_mac_dinh && (
                      <> <Tag cls="warn">quy về Vietourist theo mặc định</Tag></>
                    )}
                  </td>
                  <td>{fmtD(r.khoi_hanh)}</td>
                  <td>
                    {r.chua_co_so
                      ? <Tag cls="muted">Chưa có số</Tag>
                      : <Tag cls="">{r.trang_thai === "ket_thuc" ? "Đã về" : "Đã duyệt"}</Tag>}
                  </td>
                  <td className="num">{so(r.doanh_thu)}</td>
                  <td className="num">{so(r.gia_von)}</td>
                  <td className="num"><TreNgay n={r.so_ngay_tre} qua={r.qua_han} /></td>
                  <td className="num"><Link className="the-cua" href={r.duong_dan}>Mở chuyến →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* CẮT THÌ ĐƯỢC, IM LẶNG THÌ KHÔNG — bài học KS-5. Người đọc phải biết mình đang nhìn một
            phần, nếu không họ ra quyết định trên phần bị cắt mà tưởng là toàn bộ. */}
        {d?.cham_tran && (
          <p className="muted v14-ghi">
            Đang hiện <b>{rows.length}</b> chuyến mới nhất trong tổng số <b>{d.tong}</b>. Thu hẹp
            bằng khoảng tháng ở trên để thấy phần còn lại.
          </p>
        )}
      </section>
    </>
  );
}

export default function Page() {
  return <Shell><SoConNo /></Shell>;
}
