"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, pct } from "@/lib/api";
import { errMsg } from "@/components/ui";
import ChiPhiKyPanel from "@/components/doixe/ChiPhiKyPanel";
import MucLucPhanHe from "@/components/MucLucPhanHe";

/** Bàn làm việc Giám đốc đội xe — màn `/xe`.
 *
 *  Anh Tuấn chốt 08/11/2026: màn RIÊNG của đội xe, không cột dọc bên trái, không phân hệ phòng
 *  khác. Shell vẫn bọc (canh đăng nhập, mật khẩu tạm, toast) nhưng ẩn thanh dọc — xem cờ
 *  `khongThanhBen` thêm cùng bản này.
 *
 *  MỘT CỬA cho cả màn: GET /fleet/ban-lam-viec?ky= trả đủ bốn vùng. Bốn cửa thì bốn lần chờ, và
 *  bốn cơ hội để hai vùng trên cùng một màn nói hai con số khác nhau.
 *
 *  Ô KỲ CHỈ CÓ HAI MŨI TÊN, KHÔNG CÓ CHỖ GÕ. Lỗi thật trên màn Lãi lỗ: gõ «102026» thì ô hiện
 *  October 2026 nhưng thân trang vẽ kỳ 2026-01 với số gộp lạ (796.985.460 đ, 226 ngày khai thác).
 *  Gốc là component gọi API ở trạng thái tháng gõ dở. Ở đây kỳ là một giá trị YYYY-MM đổi bằng số
 *  tháng, không bao giờ đi qua trạng thái gõ dở.
 *
 *  CHƯA NHẬP ≠ BẰNG 0 — khoản thiếu đeo nhãn vàng, không bao giờ hiện 0. Luật này đã cứu tháng 10
 *  khỏi đọc sai 84,5 tr (KS-36) và 77 tr lương (KS-41). */

const MAU: Record<string, { cham: string; chu: string }> = {
  do:    { cham: "#be2f2f", chu: "#be2f2f" },
  cam:   { cham: "#a66a00", chu: "#a66a00" },
  vang:  { cham: "#c9a227", chu: "#6b5415" },
  trang: { cham: "#fff",    chu: "#5b6b82" },
};

/** Đổi kỳ bằng SỐ THÁNG — không đi qua chuỗi gõ dở. */
function doiKy(ky: string, buoc: number) {
  let [n, t] = ky.split("-").map(Number);
  t += buoc;
  while (t > 12) { t -= 12; n += 1; }
  while (t < 1) { t += 12; n -= 1; }
  return `${String(n).padStart(4, "0")}-${String(t).padStart(2, "0")}`;
}
const kyDoc = (ky: string) => ky.split("-").reverse().join(" / ");

/** Nhãn dùng chung cho mọi chỗ có thể thiếu số. */
const ChuaNhap = () => (
  <span className="tag" style={{ background: "#fdf6e7", color: "#a66a00", fontWeight: 700 }}>
    CHƯA NHẬP
  </span>
);

/** Ngăn kéo: xử lý tại chỗ, đóng lại là bàn tự đọc lại số. */
const NGAN_KEO: Record<string, { ten: string; toi: string; nhan: string }> = {
  "quyet-toan": { ten: "Quyết toán chuyến", toi: "/doi-xe", nhan: "Mở bảng quyết toán" },
  "chi-phi-ky": { ten: "Nhập chi phí kỳ", toi: "/lai-lo-doi-xe", nhan: "Mở sổ chi phí kỳ" },
  "ho-so-xe":   { ten: "Hồ sơ xe", toi: "/doi-xe", nhan: "Mở hồ sơ xe" },
  "bao-duong":  { ten: "Bảo dưỡng", toi: "/doi-xe", nhan: "Mở tab bảo dưỡng" },
  "de-xuat":    { ten: "Đề xuất chờ duyệt", toi: "/requests", nhan: "Mở màn đề xuất" },
};

function BanLamViecXe() {
  const { toast } = useShell();
  const [ky, setKy] = useState(() => new Date().toISOString().slice(0, 7));
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(true);
  const [keo, setKeo] = useState<string | null>(null);

  const doc = useCallback(async (k: string) => {
    setDang(true);
    try { setD(await api(`/fleet/ban-lam-viec?ky=${k}`)); }
    catch (e) { toast(errMsg(e), true); }
    finally { setDang(false); }
  }, [toast]);

  useEffect(() => { doc(ky); }, [ky, doc]);
  useEffect(() => {
    if (!keo) return;
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setKeo(null); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [keo]);

  const hd = d?.hang_doi, sk = d?.so_ky, xe = d?.xe_hom_nay, db = d?.dien_bien;
  const k = keo ? NGAN_KEO[keo] : null;

  return (<>
    {/* THANH CHỨC NĂNG — toàn bộ là việc của đội xe. Thay cho thanh dọc đã ẩn: giám đốc
        vẫn đi được tới các màn của chính phân hệ mình, nhưng không thấy phân hệ phòng khác. */}
    <nav aria-label="Màn hình đội xe"
         style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 14,
                  borderBottom: "1px solid #dce3ec" }}>
      <span style={{ padding: "8px 12px", fontWeight: 700,
                     borderBottom: "3px solid #1d5bbf" }}>Bàn làm việc</span>
      <Link href="/doi-xe" style={{ padding: "8px 12px" }}>Hồ sơ xe</Link>
      <Link href="/doi-xe/xe-hom-nay" style={{ padding: "8px 12px" }}>Xe hôm nay</Link>
      <Link href="/doi-xe/gia-dau" style={{ padding: "8px 12px" }}>Giá dầu &amp; định mức</Link>
      <Link href="/hieu-qua-doi-xe" style={{ padding: "8px 12px" }}>Hiệu quả khai thác</Link>
      <Link href="/lai-lo-doi-xe" style={{ padding: "8px 12px" }}>Lãi lỗ đội xe</Link>
      {/* Lối ra. Màn này ẩn thanh dọc, nên nếu đây không có thì người dùng chỉ còn nút
          Back của trình duyệt — trên máy bảng thì nhiều người không tìm ra nó. */}
      <Link href="/" style={{ padding: "8px 12px", marginLeft: "auto" }}>Trang tổng CRM →</Link>
    </nav>

    {/* thanh trên — CHỈ đội xe */}
    <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-end",
                  justifyContent: "space-between", marginBottom: 18 }}>
      <div>
        <h1 style={{ margin: "0 0 4px" }}>Bàn làm việc Giám đốc đội xe</h1>
        <p className="muted" style={{ margin: 0 }}>
          Công ty TNHH Vận tải Vietrip · chỉ dữ liệu đội xe
        </p>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="muted">Kỳ</span>
        <button type="button" aria-label="Kỳ trước" onClick={() => setKy(doiKy(ky, -1))}>‹</button>
        <strong style={{ minWidth: 92, textAlign: "center" }}>{kyDoc(ky)}</strong>
        <button type="button" aria-label="Kỳ sau" onClick={() => setKy(doiKy(ky, 1))}>›</button>
      </div>
    </div>

    {dang && !d && <p className="muted">Đang đọc số…</p>}

    {/* ① HÀNG ĐỢI — đứng trên cùng, trên cả con số doanh thu.
        Doanh thu là thứ giám đốc XEM; hàng đợi là thứ giám đốc LÀM. */}
    {hd && <section style={{ marginBottom: 18 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "baseline",
                    justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Hàng đợi việc của tôi</h2>
        <span className="muted">
          {hd.so_viec_cua_toi} việc · <strong style={{ color: "#be2f2f" }}>{hd.so_do} đỏ</strong>
          {hd.so_cho_nguoi_khac > 0 && ` · ${hd.so_cho_nguoi_khac} đang chờ người khác`}
        </span>
      </div>

      {hd.viec.length === 0
        ? <p className="muted">Không có việc nào đang mở. Đây là số thật, không phải thiếu nguồn.</p>
        : hd.viec.map((v: any) => (
          <div key={v.ma} style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center",
                                   padding: "12px 0", borderBottom: "1px solid #e6eaf0" }}>
            <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: "50%",
              flex: "0 0 10px", background: (MAU[v.muc] || MAU.vang).cham,
              border: v.muc === "trang" ? "2px solid #afbcce" : undefined }} />
            <span style={{ flex: "999 1 320px", minWidth: 0 }}>
              <strong style={{ display: "block" }}>{v.tieu_de}</strong>
              <span className="muted">{v.mo_ta}</span>
            </span>
            {/* Quyền ẩn NÚT, không ẩn VIỆC: giám đốc vẫn thấy tiền đang treo kể cả khi chưa
                được bấm. Giấu việc đi thì tiền treo biến mất khỏi tầm mắt người duy nhất
                quan tâm đến nó. */}
            {v.bam_duoc && v.ngan_keo
              ? <button type="button" onClick={() => setKeo(v.ngan_keo)}>{v.nhan_nut}</button>
              : <span className="muted"><strong>{v.nhan_nut}</strong></span>}
          </div>))}

      {hd.bo_do_hong?.length > 0 && <p style={{ color: "#a66a00" }}>
        {hd.bo_do_hong.length} bộ dò lỗi ({hd.bo_do_hong.join(", ")}) — hàng đợi đang thiếu dòng,
        báo CNTT.
      </p>}
    </section>}

    {/* ② + ③ */}
    {sk && xe && <div style={{ display: "flex", flexWrap: "wrap", gap: 18, marginBottom: 18 }}>
      <section style={{ flex: "999 1 520px", minWidth: 0 }}>
        <h2 style={{ marginTop: 0 }}>Số đội xe kỳ {kyDoc(sk.ky)}</h2>
        <table><tbody>
          <tr><td>Doanh thu</td><td style={{ textAlign: "right" }}><strong>{vnd(sk.doanh_thu)}</strong></td></tr>
          <tr><td className="muted">− Chi phí của xe (gồm chi phí chuyến)</td>
              <td style={{ textAlign: "right" }} className="muted">{vnd(sk.chi_phi_xe)}</td></tr>
          <tr><td className="muted">− Chi phí của đội (bãi xe, điện nước, BHXH…)</td>
              <td style={{ textAlign: "right" }} className="muted">{vnd(sk.chi_phi_cua_doi)}</td></tr>
          <tr><td><strong>LỢI NHUẬN ĐỘI XE</strong></td>
              <td style={{ textAlign: "right" }}>
                <strong>{vnd(sk.loi_nhuan)}</strong> <span className="muted">({pct(sk.bien_loi_nhuan)})</span>
              </td></tr>
        </tbody></table>

        {/* CHƯA NHẬP ≠ BẰNG 0 — nêu TÊN nhóm thiếu, không hiện 0. */}
        {sk.chua_nhap?.length > 0 && <p style={{ marginTop: 10 }}>
          <ChuaNhap />{" "}
          <span className="muted">
            {sk.chua_nhap.map((n: any) => n.ten).join(" · ")} — kỳ này chưa có số, nên lợi nhuận ở
            trên đang cao hơn thực tế. Đó là THIẾU SỐ, không phải bằng 0.
          </span>
        </p>}

        <p className="muted" style={{ marginBottom: 0 }}>
          {sk.so_xe_co_chay}/{sk.tong_xe} xe có chạy trong kỳ
        </p>
      </section>

      <section style={{ flex: "400 1 320px", minWidth: 0 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "baseline",
                      justifyContent: "space-between" }}>
          <h2 style={{ marginTop: 0 }}>Xe hôm nay</h2>
          <span className="muted">{xe.doc_luc ? `đọc lúc ${xe.doc_luc}` : "chưa đọc được"}</span>
        </div>
        <p>
          <strong>{xe.dang_di ?? "—"}</strong> đang đi ·{" "}
          <strong>{xe.o_bai ?? "—"}</strong> ở bãi ·{" "}
          <strong>{xe.khong_khop ?? "—"}</strong> không khớp
        </p>
        {/* Không bao giờ im lặng hiện 0: nói rõ nguồn và tuổi số. */}
        {xe.canh_bao && <p style={{ color: "#a66a00" }}>{xe.canh_bao}</p>}
        {xe.danh_sach?.map((x: any) => (
          <div key={x.bien || x.xe} style={{ borderTop: "1px solid #e6eaf0", padding: "8px 0" }}>
            <strong>{x.bien || x.xe}</strong>{x.tai_xe ? ` · ${x.tai_xe}` : ""}
            {x.tour && <div className="muted">{x.tour}</div>}
          </div>))}
      </section>
    </div>}

    {/* ④ DIỄN BIẾN — kỳ chưa có số thì nói «chưa đủ dữ liệu», KHÔNG vẽ cột bằng 0. */}
    {db && <section>
      <h2>Diễn biến lợi nhuận đội xe</h2>
      {/* Câu lưu ý đi KÈM bảng, đặt NGAY TRÊN nó. Ai đọc cái dốc cũng phải đọc luôn lý do
          cái dốc có thể không thật: kỳ thiếu lương, thiếu bảo dưỡng thì biên luôn cao hơn
          kỳ đã nhập đủ. Đo 09/11/2026: kỳ 07 biên 46,2% với 0 dòng chi phí kỳ, kỳ 10 biên
          15,1% với 23 dòng. */}
      {db.luu_y && <p style={{ color: "#a66a00" }}><strong>Lưu ý:</strong> {db.luu_y}</p>}
      {db.du_ve
        ? <table><thead><tr><th>Kỳ</th><th style={{ textAlign: "right" }}>Lợi nhuận</th>
            <th style={{ textAlign: "right" }}>Biên</th><th>Chi phí kỳ</th></tr></thead>
            <tbody>{db.diem.map((p: any) => (
              <tr key={p.ky}>
                <td>{kyDoc(p.ky)}</td>
                <td style={{ textAlign: "right" }}>
                  {p.co_so ? vnd(p.loi_nhuan) : <span className="muted">chưa đủ dữ liệu</span>}</td>
                <td style={{ textAlign: "right" }}>
                  {p.co_so ? pct(p.bien) : <span className="muted">—</span>}</td>
                <td>{!p.co_so ? <span className="muted">—</span>
                   : p.du_chi_phi_ky
                     ? <span className="muted">{vnd(p.chi_phi_ky)} đ · {p.so_nhom_chi_phi_ky} nhóm</span>
                     : <span className="tag" style={{ background: "#fdf6e7", color: "#a66a00",
                                                      fontWeight: 700 }}
                             title={`Biên kỳ này đang đọc cao hơn thực tế — ${p.vi_sao_chua_du}`}>
                         SỐ CHƯA ĐỦ · {p.vi_sao_chua_du}
                       </span>}</td>
              </tr>))}</tbody></table>
        : <p className="muted">{db.vi_sao}</p>}
    </section>}

    {/* ⑤ CHỨC NĂNG ĐỘI XE — mục lục 4.9, trước nằm ở một TRANG RIÊNG (/phan-he/dhxe).
        Anh Tuấn 09/11/2026: "2 màn hình này là 1". Gắn lại CHÍNH mục lục ấy chứ không
        chép danh sách màn hình ra đây — chép là để hai danh sách trôi khỏi nhau, rồi một
        hôm màn mới chỉ hiện ở một chỗ. `khongChip` bỏ dãy chip phân hệ phòng khác: đó là
        thứ duy nhất trong mục lục không phải việc của đội xe.
        Mục lục này KHÔNG gọi máy chủ và không hiện một con số nghiệp vụ nào (ranh giới
        09/9/2026) — nó chỉ đọc cấu trúc từ lib/cay_phan_he.ts. */}
    <section style={{ marginTop: 26, borderTop: "1px solid #e6eaf0", paddingTop: 18 }}>
      <MucLucPhanHe khoa="dhxe" khongChip />
    </section>

    {/* NGĂN KÉO */}
    {k && <>
      <div onClick={() => setKeo(null)}
           style={{ position: "fixed", inset: 0, background: "rgba(14,42,82,.42)", zIndex: 40 }} />
      <aside role="dialog" aria-modal="true" aria-label={k.ten}
             style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "min(720px, 94vw)",
                      background: "#fff", zIndex: 41, overflowY: "auto", padding: 22,
                      boxShadow: "-12px 0 28px rgba(14,42,82,.22)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                      gap: 12, marginBottom: 14 }}>
          <div>
            <h2 style={{ margin: 0 }}>{k.ten}</h2>
            <p className="muted" style={{ margin: 0 }}>Kỳ {kyDoc(ky)}</p>
          </div>
          <button type="button" aria-label="Đóng ngăn kéo" onClick={() => setKeo(null)}>✕</button>
        </div>
        {/* BƯỚC 1/2: ngăn kéo hiện việc và đưa thẳng tới cửa nhập đang chạy. Bước 2 nhúng chính
            form ấy vào đây để giám đốc không rời trang — làm sau khi bàn này chạy thật vài ngày,
            để biết ngăn kéo nào thực sự được mở. */}
        {hd?.viec.filter((v: any) => v.ngan_keo === keo).map((v: any) => (
          <p key={v.ma}><strong>{v.tieu_de}</strong><br /><span className="muted">{v.mo_ta}</span></p>
        ))}
        {/* BƯỚC 2 của ngăn kéo: nhóm nào đã có form thì làm NGAY TẠI ĐÂY, không rời trang.
            Nhóm chưa có thì vẫn dẫn sang màn cũ — dẫn sang còn hơn không đi được. */}
        {keo === "chi-phi-ky"
          ? <ChiPhiKyPanel ky={ky} onDoiSo={() => doc(ky)} />
          : <p><Link href={k.toi}>{k.nhan} →</Link></p>}
        <p className="muted">Đóng ngăn kéo thì bàn tự đọc lại số.</p>
        <button type="button" onClick={() => { setKeo(null); doc(ky); }}>Xong — đọc lại số</button>
      </aside>
    </>}
  </>);
}

export default function Page() {
  return <Shell khongThanhBen><BanLamViecXe /></Shell>;
}
