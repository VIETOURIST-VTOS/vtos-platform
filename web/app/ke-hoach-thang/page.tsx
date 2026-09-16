"use client";
/** CỬA NHẬP KẾ HOẠCH THÁNG — màn hình anh Tuấn duyệt mở ngày 15/9/2026.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  ĐÂY LÀ MỘT CỬA NHẬP, KHÔNG PHẢI MỘT BÁO CÁO
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ranh giới 09/9/2026: phần mềm viết cấu trúc và phép tính, số liệu do người của bộ phận tự nhập.
 *  Suốt bốn vòng, thẻ "Doanh thu tháng" trên màn hình Chủ tịch in một câu thú nhận — "chưa có kế
 *  hoạch tháng để so sánh (Kế toán)" — vì không có bảng nào chứa chỉ tiêu và không có cửa nào để
 *  nhập nó. Màn hình này là cửa ấy.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ô TRỐNG LÀ Ô TRỐNG, KHÔNG PHẢI SỐ KHÔNG — VÀ ĐÓ LÀ VIỆC CỦA CẢ Ô NHẬP LẪN Ô HIỂN THỊ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ô nhập để rỗng thì gửi lên `null`, và máy chủ XOÁ dòng. Gửi 0 là nói "chỉ tiêu tháng này bằng
 *  không đồng" — một câu hoàn toàn khác, và là câu mà cột "Hợp nhất" sẽ cộng vào như một con số
 *  thật. Vì vậy ở đây không có chỗ nào viết `|| 0` hay `?? 0` trên giá trị kế hoạch.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  LƯU THEO TỪNG THÁNG, KHÔNG PHẢI MỘT NÚT LƯU CHO CẢ BẢNG
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Một nút lưu cho cả năm thì lý do sửa cũng phải là MỘT lý do cho cả năm — mà lý do sửa tháng 3
 *  không đời nào giống lý do sửa tháng 9. Lưu theo tháng giữ mỗi lý do đi đúng với tháng của nó, và
 *  đó chính là thứ người đọc nhật ký sáu tháng sau cần.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  MÀN HÌNH NÀY KHÔNG ĐỌC DOANH THU THỰC HIỆN
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Chỗ so kế hoạch với thực hiện là màn hình 01. Kéo con số thực hiện về đây để "tiện đối chiếu"
 *  nghĩa là dựng phép so thứ hai cho cùng một câu hỏi, và hai phép so thì sớm muộn ra hai kết quả.
 *  Một con số — một chỗ — một hình, đúng luật vòng TC-40.
 */
import { Fragment, useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { BieuDoCot, duVeCot, type Diem } from "@/components/BieuDo";

type O = {
  company_id: number; company_ma: string; company_ten: string;
  chi_tieu: string; chi_tieu_ten: string;
  gia_tri: number | null; ly_do_sua: string; nguoi_nhap: string;
  sua_luc: string | null; so_lan_sua_muon: number;
};
type Thang = { ky: string; ten: string; be_rong: "thang" | "quy" | "nam"; da_khep: boolean; o: O[] };
type DoiChieu = {
  ky: string; chi_tieu_ten: string; chi_tieu_giao: number; tong_hep: number;
  chenh: number; nhan_hep: string;
};
type Bang = {
  nam: number;
  chi_tieu: { ma: string; ten: string }[];
  phap_nhan: { id: number; ma: string; ten: string }[];
  ky: Thang[];
  doi_chieu?: DoiChieu[];
  nam_chon_duoc?: number[];
  pham_vi?: { cau_hien_thi?: string };
  dai_toi_thieu_ly_do: number;
};

const khoaO = (ky: string, cid: number, ct: string) => `${ky}|${cid}|${ct}`;
/* TC-44 · Tên kỳ do MÁY CHỦ đặt và gửi xuống (`ten`). Trước đây màn hình tự dựng "Tháng N" từ mã
   kỳ — được, khi mọi dòng đều là tháng. Nay bảng có cả dòng Năm và bốn dòng Quý, và một hàm tên
   `tenThang` dựng tên cho dòng "Năm 2027" là chỗ sai chỉ chờ ngày lộ ra. */
const tenKy = (t: { ten?: string; ky: string }) => t.ten || t.ky;

/** Chuỗi người gõ → số, hoặc `null` khi ô để trống.
 *  Trả `undefined` nghĩa là GÕ SAI (chữ, dấu lạ) — khác hẳn để trống, nên nút Lưu phải chặn chứ
 *  không được lặng lẽ hiểu thành xoá ô. */
function docSo(s: string): number | null | undefined {
  const t = (s || "").trim().replace(/[.\s,]/g, "");
  if (t === "") return null;
  if (!/^\d+$/.test(t)) return undefined;
  return Number(t);
}

function KeHoachThang() {
  const { user, toast } = useShell();
  const [nam, setNam] = useState(new Date().getFullYear());
  const [b, setB] = useState<Bang | null>(null);
  const [xh, setXh] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [nhap, setNhap] = useState<Record<string, string>>({});
  const [lyDo, setLyDo] = useState<Record<string, string>>({});
  const [dangLuu, setDangLuu] = useState("");

  // Quyền GHI khai ở MÁY CHỦ (api/v1/ke_hoach.GHI). Ở đây chỉ để vẽ nút — và nếu hai chỗ lệch nhau
  // thì máy chủ vẫn chặn. Không bao giờ ngược lại: giao diện mở mà máy chủ đóng là phiền, giao diện
  // đóng mà máy chủ mở là lỗ hổng.
  const ghiDuoc = ["chutich", "tgd", "ketoan"].includes(user?.role || "");

  const tai = useCallback(async () => {
    setLoi("");
    try {
      const [bang, theoThang] = await Promise.all([
        api<Bang>(`/ke-hoach?nam=${nam}`),
        api<any>(`/ke-hoach/theo-thang?nam=${nam}`),
      ]);
      setB(bang); setXh(theoThang); setNhap({}); setLyDo({});
    } catch (e) { setLoi(errMsg(e) || "Không tải được bảng kế hoạch"); }
  }, [nam]);
  useEffect(() => { tai(); }, [tai]);

  if (loi) return <div className="panel" style={{ borderColor: "var(--red)" }}>
    <b style={{ color: "var(--red)" }}>Không tải được bảng kế hoạch.</b>
    <div className="muted" style={{ margin: "6px 0" }}>{loi}</div>
    <button className="act" onClick={tai}>Thử lại</button>
  </div>;
  if (!b) return <p className="muted">Đang tải…</p>;

  /* Số ĐÃ LƯU hiện có dấu chấm phân nhóm; số ĐANG GÕ hiện nguyên văn người gõ.
     Lý do phải tách hai trạng thái: "4330000000" mười chữ số liền nhau thì đếm bằng mắt không ra,
     và một chỉ tiêu lệch mười lần vẫn trông y hệt. Nhưng chèn dấu chấm trong lúc người ta đang gõ
     thì con trỏ nhảy lung tung sau mỗi phím — nên chỉ định dạng khi ô đang nghỉ.
     `docSo` bỏ dấu chấm trước khi gửi, nên định dạng ở đây không đổi con số nào. */
  const giaTriHienTai = (t: Thang, cid: number, ct: string): string => {
    const k = khoaO(t.ky, cid, ct);
    if (k in nhap) return nhap[k];
    const o = t.o.find((x) => x.company_id === cid && x.chi_tieu === ct);
    // Chưa có dòng → ô nhập RỖNG. Không điền 0 vào cho "đỡ trống".
    return o && o.gia_tri !== null ? Math.round(o.gia_tri).toLocaleString("vi-VN") : "";
  };

  const thangDoi = (t: Thang): string[] =>
    Object.keys(nhap).filter((k) => k.startsWith(`${t.ky}|`));

  async function luuThang(t: Thang) {
    const khoa = thangDoi(t);
    if (khoa.length === 0) return;
    for (const k of khoa) {
      if (docSo(nhap[k]) === undefined) {
        toast("Có ô chưa phải là số. Chỉ nhập chữ số, không nhập chữ hay ký hiệu.", true);
        return;
      }
    }
    if (t.da_khep && (lyDo[t.ky] || "").trim().length < b!.dai_toi_thieu_ly_do) {
      toast(`Tháng đã khép: phải ghi lý do ít nhất ${b!.dai_toi_thieu_ly_do} ký tự.`, true);
      return;
    }
    setDangLuu(t.ky);
    try {
      // Tuần tự chứ không song song: mỗi lần gọi ghi một dòng nhật ký, và nhật ký là chuỗi băm nối
      // tiếp nhau — hai lần ghi chạy chồng nhau thì mắt xích cuối tính trên một bản chưa ổn định.
      for (const k of khoa) {
        const [ky, cid, ct] = k.split("|");
        await api("/ke-hoach", {
          method: "PUT",
          json: { ky, company_id: Number(cid), chi_tieu: ct,
                  gia_tri: docSo(nhap[k]), ly_do: lyDo[t.ky] || "" },
        });
      }
      toast(`Đã lưu kế hoạch ${tenKy(t)} · ${b!.nam}.`);
      await tai();
    } catch (e) { toast(errMsg(e), true); }
    finally { setDangLuu(""); }
  }

  /* Biểu đồ: KẾ HOẠCH DOANH THU HỢP NHẤT theo tháng. Tháng nào chưa đủ mọi pháp nhân thì là một ô
     TRỐNG đúng chỗ của nó — không phải cột cao 0. Máy chủ đã quyết "đủ hay chưa đủ" (cờ `du`), màn
     hình chỉ đọc cờ ấy. */
  const diem: Diem[] = (xh?.thang || []).map((m: any) => ({
    nhan: `T${Number(m.ky.split("-")[1])}`,
    gt: m.doanh_thu?.du ? m.doanh_thu.gia_tri : null,
  }));
  const soThieu = (xh?.thang || []).filter((m: any) => !m.doanh_thu?.du).length;

  return (<>
    <div className="mh01-dau">
      <h2>Kế hoạch tháng</h2>
      <span className="tag">Kế toán nhập · Ban lãnh đạo duyệt</span>
    </div>

    <div className="panel">
      <div className="kh-hang">
        <button className="act" onClick={() => setNam(nam - 1)}>← {nam - 1}</button>
        <b className="kh-nam">{nam}</b>
        <button className="act" onClick={() => setNam(nam + 1)}>{nam + 1} →</button>
        {b.pham_vi?.cau_hien_thi && <span className="muted kh-pv">{b.pham_vi.cau_hien_thi}</span>}
      </div>
      {!ghiDuoc && <p className="muted">
        <span className="tag">Chỉ xem</span> Vai trò của anh/chị đọc được chỉ tiêu nhưng không nhập.
        Người nhập là Kế toán; Chủ tịch và Tổng giám đốc sửa được khi Hội đồng quản trị điều chỉnh.
      </p>}
      {b.phap_nhan.length === 0 && <p className="muted">
        Chưa có pháp nhân nào đang hoạt động trong phạm vi hợp nhất. Khai ở màn hình{" "}
        Tổ chức &amp; đơn vị trước, rồi quay lại đây.
      </p>}
    </div>

    {/* ĐỐI CHIẾU BA BỀ RỘNG — HIỆN RA, KHÔNG TỰ SỬA.
        Anh Tuấn chốt 16/9/2026 rằng chỉ tiêu năm và quý do HĐQT nhập riêng, không cộng từ 12
        tháng. Hệ quả là ba chỗ nhập, và ba chỗ thì sớm muộn lệch nhau.

        Lệch KHÔNG phải lỗi: hội đồng giao 230 tỷ trong khi Kế toán phân bổ tháng cộng lại ra 226
        thì 4 tỷ ấy là dư địa cố ý. Tự cộng ngược hay tự chia đều là xoá một quyết định quản trị và
        thay bằng một phép tính.
        Nhưng lệch mà KHÔNG AI THẤY mới là chỗ hỏng — sáu tháng sau không ai nhớ 4 tỷ ấy là dư địa
        hay một ô gõ thiếu số 0. Nên dòng này đứng ngay trên bảng nhập, và nó chỉ NÓI. */}
    {(b.doi_chieu || []).length > 0 && <div className="panel kh-doi-chieu">
      <div className="mh01-dau"><h2>Chỉ tiêu giao khác tổng phân bổ</h2>
        <span className="tag">{b.doi_chieu!.length} chỗ</span></div>
      <ul className="kh-dc-ds">
        {b.doi_chieu!.map((d) => (
          <li key={d.ky + d.chi_tieu_ten}>
            <b>{d.ky}</b> · {d.chi_tieu_ten}: giao{" "}
            <b>{Math.round(d.chi_tieu_giao).toLocaleString("vi-VN")}</b>, {d.nhan_hep} cộng lại{" "}
            <b>{Math.round(d.tong_hep).toLocaleString("vi-VN")}</b> —{" "}
            <b className="v14-canh">
              {d.chenh > 0 ? "còn thiếu " : "vượt "}
              {Math.abs(Math.round(d.chenh)).toLocaleString("vi-VN")}
            </b>
          </li>
        ))}
      </ul>
      <p className="muted v14-ghi">
        Hệ thống KHÔNG tự cộng ngược hay chia đều — chênh lệch giữa chỉ tiêu Hội đồng giao và phân
        bổ của Kế toán có thể là dư địa cố ý. Dòng này chỉ nói ra để anh/chị quyết.
      </p>
    </div>}

    {/* BIỂU ĐỒ ĐẶT TRƯỚC BẢNG NHẬP: người mở màn hình này thường mở để xem "năm nay đã đặt chỉ tiêu
        tới đâu", và câu trả lời ấy là một cái nhìn chứ không phải một bảng 24 ô. */}
    {duVeCot(diem) && <div className="panel">
      <BieuDoCot ten="Kế hoạch doanh thu hợp nhất" phu={`12 tháng năm ${b.nam}`} diem={diem}
        chan={soThieu > 0
          ? `${soThieu}/12 tháng để trống vì CHƯA ĐỦ mọi pháp nhân. Thiếu một pháp nhân thì kế hoạch hợp nhất chưa tồn tại — cộng phần đã nhập lại sẽ ra một chỉ tiêu thấp hơn thật mà nhìn không khác gì một con số đầy đủ.`
          : "Cả 12 tháng đã đủ chỉ tiêu của mọi pháp nhân trong phạm vi hợp nhất."} />
    </div>}

    {/* MỘT BẢNG CHO CẢ NĂM, KHÔNG PHẢI MƯỜI HAI KHUNG GIỐNG NHAU.
        Bản đầu của màn hình này dựng mỗi tháng một khung riêng, mỗi khung có tiêu đề, bảng và nút
        Lưu của nó. Dựng ra ảnh mới thấy: mười hai khung gần như trùng khít nhau, dài hơn bốn màn
        hình, và cái người ta thật sự muốn — so tháng này với tháng kia — thì không làm được vì hai
        tháng không bao giờ nằm cùng tầm mắt. Đúng điều anh Tuấn chốt ở vòng TC-40: "những phần lặp
        lại thì bỏ".
        Nay mỗi tháng là MỘT DÒNG. Tiêu đề hai tầng vì mỗi pháp nhân có hai chỉ tiêu; gộp một tầng
        thì nhãn cột thành "Vietourist – Doanh thu" dài gấp đôi mà vẫn phải đọc từng chữ. */}
    <section className="panel">
      <div className="mh01-dau">
        <h2>Bảng chỉ tiêu {b.nam}</h2>
        <span className="tag">{b.phap_nhan.length} pháp nhân · {b.chi_tieu.length} chỉ tiêu</span>
        <span className="tag">1 năm · 4 quý · 12 tháng</span>
      </div>
      <div className="wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th rowSpan={2}>Tháng</th>
              {b.phap_nhan.map((p) => (
                <th key={p.id} colSpan={b.chi_tieu.length} className="kh-pn">
                  {p.ten} <span className="muted">{p.ma}</span>
                </th>
              ))}
              <th rowSpan={2} className="kh-sua">Sửa muộn</th>
              {ghiDuoc && <th rowSpan={2} className="kh-sua">&nbsp;</th>}
            </tr>
            <tr>
              {b.phap_nhan.map((p) => b.chi_tieu.map((c) => (
                <th key={`${p.id}-${c.ma}`} className="kh-ct">{c.ten}</th>
              )))}
            </tr>
          </thead>
          <tbody>
            {(b.ky || []).map((t) => {
              const doi = thangDoi(t);
              const canLyDo = t.da_khep && doi.length > 0;
              const soSua = Math.max(...t.o.map((x) => x.so_lan_sua_muon), 0);
              const lyDoCu = (t.o.find((x) => x.ly_do_sua) || {} as O).ly_do_sua || "";
              return (
                <Fragment key={t.ky}>
                  <tr className={[doi.length > 0 ? "kh-dang-sua" : "",
                                  t.be_rong !== "thang" ? "kh-rong-hon" : ""].join(" ").trim()
                                  || undefined}>
                    <td className="kh-thang">
                      <b>{tenKy(t)}</b>
                      {/* Ổ KHOÁ chứ không phải chữ "đã khép": mười hai dòng mà dòng nào cũng mang
                          một chữ thì chữ ấy thành nhiễu. Biểu tượng đọc được bằng cách liếc, và
                          title kèm câu đầy đủ cho người rê chuột lẫn trình đọc màn hình. */}
                      {t.da_khep && <span className="kh-khoa" title="Tháng đã khép — sửa phải kèm lý do">🔒</span>}
                    </td>
                    {b.phap_nhan.map((p) => b.chi_tieu.map((c) => (
                      <td key={`${p.id}-${c.ma}`} className="num">
                        <input className="kh-o" inputMode="numeric"
                          aria-label={`${c.ten} ${tenKy(t)} ${p.ten}`}
                          disabled={!ghiDuoc}
                          value={giaTriHienTai(t, p.id, c.ma)}
                          onChange={(e) => setNhap({ ...nhap, [khoaO(t.ky, p.id, c.ma)]: e.target.value })} />
                      </td>
                    )))}
                    <td className="kh-sua">
                      {/* Số lần sửa muộn đứng cạnh dòng chứ không nằm trong nhật ký: một dòng sửa
                          bảy lần thì con số bảy đã là câu hỏi, trước cả khi đọc từng lý do. */}
                      {soSua > 0
                        ? <span className="kh-ly" title={lyDoCu}>
                            <b className="v14-canh">{soSua}</b>{" "}
                            <span className="muted">{lyDoCu}</span></span>
                        : <span className="muted">—</span>}
                    </td>
                    {ghiDuoc && <td className="kh-sua">
                      <button className="act" disabled={doi.length === 0 || dangLuu === t.ky}
                        onClick={() => luuThang(t)}>
                        {dangLuu === t.ky ? "Đang lưu…" : "Lưu"}
                      </button>
                      {doi.length > 0 && <button className="act kh-bo" onClick={() => {
                        const con = { ...nhap }; doi.forEach((k) => delete con[k]); setNhap(con);
                      }}>Bỏ sửa</button>}
                    </td>}
                  </tr>
                  {canLyDo && <tr>
                    {/* Ô lý do chiếm trọn chiều ngang NGAY DƯỚI dòng nó thuộc về. Đặt nó ở cuối
                        bảng thì người gõ tháng 3 phải cuộn xuống cuối để giải trình cho tháng 3. */}
                    <td colSpan={2 + b.phap_nhan.length * b.chi_tieu.length + (ghiDuoc ? 1 : 0)}>
                      <div className="kh-lydo">
                        <label htmlFor={`lydo-${t.ky}`}>
                          Lý do sửa {tenKy(t)} — kỳ đã khép <span className="muted">
                            (ít nhất {b.dai_toi_thieu_ly_do} ký tự, lưu ngay trên dòng và vào nhật ký)</span>
                        </label>
                        <input id={`lydo-${t.ky}`} className="kh-lydo-o" value={lyDo[t.ky] || ""}
                          onChange={(e) => setLyDo({ ...lyDo, [t.ky]: e.target.value })}
                          placeholder="Ví dụ: Nghị quyết HĐQT ngày … điều chỉnh chỉ tiêu quý 3" />
                      </div>
                    </td>
                  </tr>}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>

    <p className="muted">
      Ô để trống nghĩa là <b>chưa có kế hoạch</b>, không phải kế hoạch bằng 0 — lưu ô trống là xoá
      chỉ tiêu ấy. Tháng nào chưa đủ mọi pháp nhân thì màn hình Chủ tịch vẫn ghi &quot;chưa có kế
      hoạch tháng&quot;, kèm tên pháp nhân còn thiếu. Số liệu nhập ở đây không tự suy ra tháng khác:
      không có tháng nào lấy tháng trước làm lối lui.
    </p>
  </>);
}

export default function Page() { return <Shell><KeHoachThang /></Shell>; }
