"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

/** Báo chí, KOL & sự kiện – mục 2.2.2.
 *
 *  BA THẺ, HAI SỔ. Thẻ "Báo chí" và thẻ "Sự kiện" đọc CÙNG một sổ (`mkt_pr_hoat_dong`), khác nhau
 *  đúng một bộ lọc loại – anh Tuấn chốt 24/9/2026. Dựng bảng riêng cho sự kiện là hai nơi cùng
 *  đếm "tháng này làm bao nhiêu việc truyền thông", và ngày một nơi lệch thì hai báo cáo ra hai
 *  con số mà không ai biết bên nào đúng.
 *
 *  NÚT PHÁT KHÔNG PHẢI MỘT MỨC QUYỀN. Nó chỉ hiện cho P.TGĐ Marketing, vì người phát ngôn của
 *  công ty là một VỊ TRÍ có tên – không phải người có quyền cao nhất. Chủ tịch mở được màn hình
 *  này nhưng KHÔNG thấy nút ấy, và đó là chủ ý, không phải sót.
 *
 *  TIỀN Ở THẺ KOL LÀ TIỀN THOẢ THUẬN. Cột "Phiếu chi" nối sang tiền thật; hai số lệch nhau thì in
 *  phần chênh ra chứ không san bằng. Xem ghi chú đầu services/kol.py.
 */

const THE: [string, string][] = [
  ["baochi", "Báo chí & phát ngôn"], ["sukien", "Sự kiện"], ["kol", "KOL / KOC"]];

/** DÒNG VÍ DỤ — chỉ hiện khi bảng còn TRỐNG, và KHÔNG có trong cơ sở dữ liệu.
 *
 *  Anh Tuấn chốt 24/9/2026: cần số nháp cho nhân viên thấy format phải điền. Hai cách, và đây là
 *  cách đã chọn.
 *
 *  CÁCH KIA LÀ NẠP VÀI DÒNG THẬT VÀO SỔ, và nó hỏng theo một kiểu chỉ lộ ra sau vài tháng: dòng
 *  nháp nạp vào rồi thì KHÔNG có cột nào đánh dấu nó là nháp. Ba tháng sau không ai phân biệt
 *  được nó với dòng thật, bảng hiệu quả kênh cộng cả nó vào, và người đọc báo cáo không có cách
 *  nào biết. Đúng thứ ranh giới 09/9/2026 cấm: phần mềm không tự bịa số liệu.
 *
 *  Ở đây dòng ví dụ sống TRONG MÃ MÀN HÌNH, không đi qua máy chủ, không vào bảng nào. Nó biến mất
 *  ngay khi có dòng thật đầu tiên, nên không bao giờ nằm lẫn. Và nó có nhãn trên từng dòng chứ
 *  không chỉ một câu ở đầu bảng — người cuộn tới giữa bảng vẫn phải đọc được là mình đang xem gì.
 */
const VI_DU_PR: any[] = [
  { ma: "PR-2026-09-0001", loai: "bai_bao", tieu_de: "Vietourist mở tuyến charter Phú Quốc – Đài Bắc",
    noi_dang: "Báo Thanh Niên, chuyên mục Du lịch", trang_thai: "da_phat", ghi_nhan_luc: "18/09/2026 09:20" },
  { ma: "PR-2026-09-0002", loai: "thong_cao", tieu_de: "Thông cáo kết quả kinh doanh quý III",
    noi_dang: "Website công ty + 4 đầu báo", trang_thai: "cho_phat", ghi_nhan_luc: "22/09/2026 14:05" },
];
const VI_DU_SU_KIEN: any[] = [
  { ma: "PR-2026-09-0003", loai: "su_kien", tieu_de: "Hội chợ ITE HCMC 2026 – gian hàng B12",
    noi_dang: "SECC Quận 7, 04–06/09", trang_thai: "da_phat", ghi_nhan_luc: "01/09/2026 08:00" },
];
const VI_DU_KOL: any[] = [
  { ma: "KOL-0001", ho_ten: "Nguyễn Thị Lan Anh", biet_danh: "Lan Anh Travel", kenh_ten: "TikTok",
    luong_theo_doi: 320000, theo_doi_do_ngay: "2026-09-20", gia_tham_khao: 15000000,
    so_lan: 3, da_dang: 2, tong_chi_thoa_thuan: 35000000, so_lan_chua_co_gia: 1,
    trang_thai_ten: "Đang hợp tác" },
  { ma: "KOL-0002", ho_ten: "Trần Minh Quân", biet_danh: "Quân Đi Đâu", kenh_ten: "YouTube",
    luong_theo_doi: null, theo_doi_do_ngay: "", gia_tham_khao: null,
    so_lan: 0, da_dang: 0, tong_chi_thoa_thuan: 0, so_lan_chua_co_gia: 0,
    trang_thai_ten: "Tạm dừng" },
];

/** Khung bao quanh bảng đang ở chế độ ví dụ. Nhãn đặt CẢ TRÊN lẫn TRÊN TỪNG DÒNG. */
function BangTrong({ so_cot, chu }: { so_cot: number; chu: string }) {
  return (<tr><td colSpan={so_cot} className="muted" style={{ paddingTop: 10 }}>
    <b>Bảng còn trống.</b> {chu} Mấy dòng dưới là <b>ví dụ</b> để anh chị thấy cần điền gì —
    chúng <b>không nằm trong sổ</b> và sẽ biến mất ngay khi có dòng thật đầu tiên.
  </td></tr>);
}

/** RỖNG hiện chữ, KHÔNG hiện 0 – "chưa ai gõ" khác hẳn "đo được và bằng không". */
function So({ x }: { x: number | null | undefined }) {
  if (x === null || x === undefined) return <span className="muted">chưa có</span>;
  return <>{x.toLocaleString("vi-VN")}</>;
}

function Tien({ x }: { x: number | null | undefined }) {
  if (x === null || x === undefined) return <span className="muted">–</span>;
  return <>{vnd(x)}</>;
}

function BaoChiKol() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [the, setThe] = useState("baochi");
  const [dm, setDm] = useState<any>(null);
  const [pr, setPr] = useState<any>(null);
  const [ds, setDs] = useState<any>(null);
  const [mo, setMo] = useState<any>(null);          // KOL đang mở chi tiết
  const [fPr, setFPr] = useState<any>({ loai: "bai_bao", tieu_de: "", tom_tat: "", noi_dang: "", link: "", campaign_id: "", la_khung_hoang: false, muc_do: "", ghi_chu: "" });
  const [fKol, setFKol] = useState<any>({ ho_ten: "", kenh: "facebook", link_kenh: "", biet_danh: "", luong_theo_doi: "", gia_tham_khao: "", nguoi_lien_he: "", dien_thoai: "", email: "", ghi_chu: "" });
  const [fHt, setFHt] = useState<any>({ ky: "", noi_dung: "", loai: "bai_dang", campaign_id: "", chi_phi: "", link_bai: "", trang_thai: "du_kien", ghi_chu: "" });

  const ghiDuoc = ["nv_mkt", "ptgd_mkt", "chutich", "tgd", "cntt"].includes(role);
  const phatDuoc = role === "ptgd_mkt";

  const load = useCallback(() => {
    if (!dm) api("/bao-chi-kol/danh-muc").then(setDm).catch((e) => toast(errMsg(e), true));
    if (the === "baochi" || the === "sukien") {
      const q = the === "sukien" ? "?loai=su_kien" : "";
      api(`/marketing/pr${q}`).then(setPr).catch((e) => toast(errMsg(e), true));
    }
    if (the === "kol") api("/bao-chi-kol/kol").then(setDs).catch((e) => toast(errMsg(e), true));
  }, [the, dm]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);

  const post = async (p: string, json?: any, method = "POST") => {
    try { const r = await api(p, { method, json }); toast(r.message || "Xong"); load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };

  const moKol = async (id: number) => {
    try { setMo(await api(`/bao-chi-kol/kol/${id}`)); setFHt({ ...fHt, ky: "" }); }
    catch (x) { toast(errMsg(x), true); }
  };

  const themKol = async () => {
    const d: any = { ...fKol };
    d.luong_theo_doi = d.luong_theo_doi ? Number(d.luong_theo_doi) : null;
    d.gia_tham_khao = d.gia_tham_khao ? Number(d.gia_tham_khao) : null;
    try {
      const r = await api("/bao-chi-kol/kol", { method: "POST", json: d });
      toast(r.message); setFKol({ ...fKol, ho_ten: "", link_kenh: "", biet_danh: "", luong_theo_doi: "", ghi_chu: "" }); load();
    } catch (x: any) {
      // 409 = trùng TÊN. Không phải lỗi – hỏi lại rồi gửi cờ bỏ qua. Trùng ĐƯỜNG DẪN KÊNH thì
      // chặn cứng ở máy chủ và không có đường đi tiếp, vì đó chắc chắn là bản khai lặp.
      const t = x?.body?.detail;
      if (x?.status === 409 && t?.trung_ten) {
        const ten = t.trung_ten.map((z: any) => `${z.ho_ten} · ${z.kenh}`).join("; ");
        if (await xacNhan(`${t.message}\n\nĐã có: ${ten}`)) {
          await post("/bao-chi-kol/kol", { ...d, bo_qua_canh_bao_trung_ten: true });
        }
      } else toast(errMsg(x), true);
    }
  };

  return (<>{hop}
    <h1>Báo chí, KOL &amp; sự kiện</h1>
    <p className="muted">Sổ hoạt động truyền thông và danh bạ người hợp tác nội dung. <b>Báo chí</b> và
      <b> Sự kiện</b> là cùng một sổ, khác nhau bộ lọc loại – một nơi đếm, một con số.
      Nút <b>Phát</b> chỉ Phó TGĐ Marketing bấm: phát ngôn ra ngoài là một vị trí có tên, không phải
      một mức quyền.</p>

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {THE.map(([k, l]) => <button key={k} className={"act " + (the === k ? "" : "grey")}
        style={{ margin: 0 }} onClick={() => { setThe(k); setMo(null); }}>{l}</button>)}
    </div>

    {/* ───────────── BÁO CHÍ & SỰ KIỆN ───────────── */}
    {(the === "baochi" || the === "sukien") && <>
      {ghiDuoc && <div className="panel"><h2>Ghi một việc vào sổ</h2>
        <div className="grid">
          <label>Loại<select value={fPr.loai} onChange={(e) => setFPr({ ...fPr, loai: e.target.value })}>
            {Object.entries(dm?.pr?.loai || {}).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select></label>
          <label>Tiêu đề<input value={fPr.tieu_de} onChange={(e) => setFPr({ ...fPr, tieu_de: e.target.value })} /></label>
          <label>Đăng ở đâu<input value={fPr.noi_dang} onChange={(e) => setFPr({ ...fPr, noi_dang: e.target.value })} placeholder="báo nào, trang nào, địa điểm" /></label>
          <label>Đường dẫn<input value={fPr.link} onChange={(e) => setFPr({ ...fPr, link: e.target.value })} /></label>
          <label>Chiến dịch<select value={fPr.campaign_id} onChange={(e) => setFPr({ ...fPr, campaign_id: e.target.value })}>
            <option value="">– chưa gắn –</option>
            {(dm?.chien_dich || []).map((c: any) => <option key={c.id} value={c.id}>{c.ma} · {c.ten}</option>)}</select></label>
          <label>Tóm tắt<input value={fPr.tom_tat} onChange={(e) => setFPr({ ...fPr, tom_tat: e.target.value })} /></label>
          <label><input type="checkbox" checked={fPr.la_khung_hoang} onChange={(e) => setFPr({ ...fPr, la_khung_hoang: e.target.checked })} /> Đây là khủng hoảng truyền thông
            <span className="muted">Đánh dấu là <b>bấm đồng hồ</b>: mốc hai giờ chạy từ lúc dòng này vào sổ, theo đồng hồ thật – không trừ ngày nghỉ, không quy ra giờ hành chính.</span></label>
          {fPr.la_khung_hoang && <label>Mức độ<select value={fPr.muc_do} onChange={(e) => setFPr({ ...fPr, muc_do: e.target.value })}>
            <option value="">– chọn –</option>
            {Object.entries(dm?.pr?.muc_do || {}).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select></label>}
        </div>
        <button className="act" disabled={!fPr.tieu_de} onClick={() => post("/bao-chi-kol/pr", {
          ...fPr, campaign_id: fPr.campaign_id ? Number(fPr.campaign_id) : null,
        }).then((r) => r && setFPr({ ...fPr, tieu_de: "", tom_tat: "", noi_dang: "", link: "", la_khung_hoang: false, muc_do: "" }))}>Ghi vào sổ (nháp)</button>
        <p className="muted">Ghi vào sổ luôn ở trạng thái <b>Nháp</b>. Đưa nội dung ra ngoài là việc của
          nút Phát, và nút ấy đứng tên người phát ngôn.</p>
      </div>}

      {pr && <>
        <div className="panel"><h2>{the === "sukien" ? "Sự kiện" : "Hoạt động truyền thông"}</h2>
          <p>Tổng <b>{pr.dem.tong}</b> · đã phát <b>{pr.dem.da_phat}</b> · chờ phát <b>{pr.dem.cho_phat}</b>
            {!!pr.dem.khung_hoang && <> · khủng hoảng <b>{pr.dem.khung_hoang}</b></>}
            {!!pr.dem.qua_han && <> · <Tag cls="red">{pr.dem.qua_han} vụ quá hạn trả lời</Tag></>}</p>
          <p className="muted">Ô <b>quá hạn</b> đếm trên <b>cả sổ</b>, không đếm trên bảng đang lọc: câu
            hỏi ở đây là “công ty đang nợ mấy câu trả lời”, không phải “trang này có mấy dòng đỏ”.
            Hạn khủng hoảng hiện đặt <b>{pr.han_khung_hoang_gio} giờ</b>.</p>
        </div>

        <div className="panel wrap">
          <table><thead><tr>
            <th>Mã</th><th>Loại</th><th>Tiêu đề</th><th>Nơi đăng</th>
            <th>Trạng thái</th><th>Ghi nhận</th><th></th>
          </tr></thead>
            <tbody>{(pr.rows || []).map((r: any) => <tr key={r.id}>
              <td className="mono">{r.ma}</td>
              <td>{pr.loai?.[r.loai] || r.loai}</td>
              <td>{r.tieu_de}{r.la_khung_hoang && <> <Tag cls="red">khủng hoảng</Tag></>}
                {r.qua_han && <> <Tag cls="red">quá hạn</Tag></>}</td>
              <td>{r.noi_dang || <span className="muted">–</span>}</td>
              <td>{pr.trang_thai_ds?.[r.trang_thai] || r.trang_thai}</td>
              <td>{r.ghi_nhan_luc}</td>
              <td>
                {phatDuoc && r.trang_thai !== "da_phat" &&
                  <button className="act" onClick={() => post(`/marketing/pr/${r.id}/phat`)}>Phát</button>}
                {r.la_khung_hoang && !r.da_phan_hoi &&
                  <button className="act grey" onClick={() => post(`/marketing/pr/${r.id}/phan-hoi`)}>Đã trả lời bằng đường khác</button>}
              </td></tr>)}
              {!(pr.rows || []).length && <>
                <BangTrong so_cot={7} chu={the === "sukien"
                  ? "Sự kiện ghi chung sổ với báo chí, chọn loại “Sự kiện” ở khung trên."
                  : "Dùng khung “Ghi một việc vào sổ” ở trên để thêm dòng đầu tiên."} />
                {(the === "sukien" ? VI_DU_SU_KIEN : VI_DU_PR).map((r) => <tr key={r.ma} className="vidu">
                  <td className="mono muted">{r.ma}</td>
                  <td className="muted">{pr.loai?.[r.loai] || r.loai}</td>
                  <td className="muted"><i>{r.tieu_de}</i> <Tag cls="grey">ví dụ</Tag></td>
                  <td className="muted">{r.noi_dang}</td>
                  <td className="muted">{pr.trang_thai_ds?.[r.trang_thai] || r.trang_thai}</td>
                  <td className="muted">{r.ghi_nhan_luc}</td>
                  <td></td></tr>)}
              </>}
            </tbody></table>
        </div>
      </>}
    </>}

    {/* ───────────── KOL / KOC ───────────── */}
    {the === "kol" && <>
      {ghiDuoc && <div className="panel"><h2>Thêm KOL / KOC</h2>
        <div className="grid">
          <label>Họ tên<input value={fKol.ho_ten} onChange={(e) => setFKol({ ...fKol, ho_ten: e.target.value })} /></label>
          <label>Tên kênh hay dùng<input value={fKol.biet_danh} onChange={(e) => setFKol({ ...fKol, biet_danh: e.target.value })} /></label>
          <label>Kênh<select value={fKol.kenh} onChange={(e) => setFKol({ ...fKol, kenh: e.target.value })}>
            {Object.entries(dm?.kol_kenh || {}).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select></label>
          <label>Đường dẫn kênh<input value={fKol.link_kenh} onChange={(e) => setFKol({ ...fKol, link_kenh: e.target.value })} />
            <span className="muted">Bắt buộc. Một dòng trong sổ này là <b>một kênh</b>, không phải một người – người có TikTok và YouTube thì khai hai dòng, vì giá và khán giả khác nhau.</span></label>
          <label>Lượng theo dõi<input type="number" value={fKol.luong_theo_doi} onChange={(e) => setFKol({ ...fKol, luong_theo_doi: e.target.value })} /></label>
          <label>Giá tham khảo một bài (đ)<input type="number" value={fKol.gia_tham_khao} onChange={(e) => setFKol({ ...fKol, gia_tham_khao: e.target.value })} /></label>
          <label>Người liên hệ<input value={fKol.nguoi_lien_he} onChange={(e) => setFKol({ ...fKol, nguoi_lien_he: e.target.value })} /></label>
          <label>Điện thoại<input value={fKol.dien_thoai} onChange={(e) => setFKol({ ...fKol, dien_thoai: e.target.value })} /></label>
          <label>Ghi chú<input value={fKol.ghi_chu} onChange={(e) => setFKol({ ...fKol, ghi_chu: e.target.value })} /></label>
        </div>
        <button className="act" disabled={!fKol.ho_ten || !fKol.link_kenh} onClick={themKol}>Thêm vào danh bạ</button>
      </div>}

      {ds && <div className="panel wrap"><h2>Danh bạ ({ds.tong})</h2>
        <table><thead><tr>
          <th>Mã</th><th>Họ tên</th><th>Kênh</th><th className="num">Theo dõi</th>
          <th className="num">Giá tham khảo</th><th className="num">Số lần</th>
          <th className="num">Đã chi (thoả thuận)</th><th>Trạng thái</th>
        </tr></thead>
          <tbody>{(ds.rows || []).map((r: any) => <tr key={r.id}>
            <td className="mono"><a href="#" onClick={(e) => { e.preventDefault(); moKol(r.id); }}>{r.ma}</a></td>
            <td>{r.ho_ten}{r.biet_danh && <span className="muted"> · {r.biet_danh}</span>}</td>
            <td>{r.kenh_ten}</td>
            <td className="num"><So x={r.luong_theo_doi} />
              {r.theo_doi_do_ngay && <span className="muted"> (đo {r.theo_doi_do_ngay})</span>}</td>
            <td className="num"><Tien x={r.gia_tham_khao} /></td>
            <td className="num">{r.so_lan}{r.da_dang ? ` (${r.da_dang} đã đăng)` : ""}</td>
            <td className="num">{vnd(r.tong_chi_thoa_thuan)}
              {!!r.so_lan_chua_co_gia && <span className="muted"> (+{r.so_lan_chua_co_gia} chưa có giá)</span>}</td>
            <td>{r.trang_thai_ten}</td></tr>)}
            {!(ds.rows || []).length && <>
              <BangTrong so_cot={8} chu="Dùng khung “Thêm KOL / KOC” ở trên để thêm người đầu tiên." />
              {VI_DU_KOL.map((r) => <tr key={r.ma} className="vidu">
                <td className="mono muted">{r.ma}</td>
                <td className="muted"><i>{r.ho_ten}</i> <span className="muted">· {r.biet_danh}</span> <Tag cls="grey">ví dụ</Tag></td>
                <td className="muted">{r.kenh_ten}</td>
                <td className="num muted"><So x={r.luong_theo_doi} />
                  {r.theo_doi_do_ngay && <span className="muted"> (đo {r.theo_doi_do_ngay})</span>}</td>
                <td className="num muted"><Tien x={r.gia_tham_khao} /></td>
                <td className="num muted">{r.so_lan}{r.da_dang ? ` (${r.da_dang} đã đăng)` : ""}</td>
                <td className="num muted">{vnd(r.tong_chi_thoa_thuan)}
                  {!!r.so_lan_chua_co_gia && <span className="muted"> (+{r.so_lan_chua_co_gia} chưa có giá)</span>}</td>
                <td className="muted">{r.trang_thai_ten}</td></tr>)}
            </>}
          </tbody></table>
        <p className="muted">Cột <b>Đã chi (thoả thuận)</b> là số Marketing thoả thuận với KOL, <b>không</b> phải
          tiền đã ra khỏi tài khoản. Lần hợp tác đã huỷ không được cộng vào. Tiền thật đi đường đề
          nghị chi – mở một người ra để xem từng lần và phần chênh giữa hai số.</p>
      </div>}

      {mo && <div className="panel"><h2>{mo.kol.ho_ten} · {mo.kol.ma}</h2>
        <p className="muted">{mo.kol.kenh_ten} · <a href={mo.kol.link_kenh} target="_blank" rel="noreferrer">{mo.kol.link_kenh}</a>
          {mo.kol.nguoi_lien_he && <> · liên hệ {mo.kol.nguoi_lien_he} {mo.kol.dien_thoai}</>}</p>
        <p>Tổng thoả thuận <b>{vnd(mo.tong_thoa_thuan)}</b> đ
          {!!mo.so_lan_chua_lap_phieu_chi && <> · <Tag cls="warn">{mo.so_lan_chua_lap_phieu_chi} lần chưa lập phiếu chi</Tag></>}
          {!!mo.so_lan_chua_co_gia && <> · <Tag cls="warn">{mo.so_lan_chua_co_gia} lần chưa có giá</Tag></>}</p>

        <div className="wrap"><table><thead><tr>
          <th>Kỳ</th><th>Loại</th><th>Nội dung</th><th>Chiến dịch</th>
          <th className="num">Thoả thuận</th><th>Phiếu chi</th><th className="num">Chênh</th>
          <th className="num">Lượt xem</th><th className="num">Lead khai</th><th>Trạng thái</th>
        </tr></thead>
          <tbody>{(mo.hop_tac || []).map((h: any) => <tr key={h.id}>
            <td className="mono">{h.ky}</td>
            <td>{h.loai_ten}</td>
            <td>{h.link_bai ? <a href={h.link_bai} target="_blank" rel="noreferrer">{h.noi_dung}</a> : h.noi_dung}</td>
            <td className="mono">{h.chien_dich_ma || <span className="muted">chưa gắn</span>}</td>
            <td className="num"><Tien x={h.chi_phi_thoa_thuan} /></td>
            <td className="mono">{h.phieu_chi_ma || <span className="muted">chưa lập</span>}</td>
            <td className="num">{h.lech_tien === null || h.lech_tien === undefined
              ? <span className="muted">–</span>
              : (h.lech_tien === 0 ? <Tag cls="ok">khớp</Tag> : <b>{h.lech_tien > 0 ? "+" : ""}{vnd(h.lech_tien)}</b>)}</td>
            <td className="num"><So x={h.luot_xem} /></td>
            <td className="num"><So x={h.so_lead_khai} /></td>
            <td>{h.trang_thai_ten}{h.ly_do_huy && <span className="muted"> · {h.ly_do_huy}</span>}</td></tr>)}
            {!(mo.hop_tac || []).length && <tr><td colSpan={10} className="muted">Chưa có lần hợp tác nào.</td></tr>}
          </tbody></table></div>
        <p className="muted">{mo.ghi_chu}</p>

        {ghiDuoc && <div style={{ marginTop: 12 }}><h3>Ghi một lần hợp tác</h3>
          <div className="grid">
            <label>Kỳ (YYYY-MM)<input value={fHt.ky} onChange={(e) => setFHt({ ...fHt, ky: e.target.value })} placeholder="2026-09" /></label>
            <label>Loại<select value={fHt.loai} onChange={(e) => setFHt({ ...fHt, loai: e.target.value })}>
              {Object.entries(dm?.hop_tac_loai || {}).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select></label>
            <label>Nội dung<input value={fHt.noi_dung} onChange={(e) => setFHt({ ...fHt, noi_dung: e.target.value })} /></label>
            <label>Chiến dịch<select value={fHt.campaign_id} onChange={(e) => setFHt({ ...fHt, campaign_id: e.target.value })}>
              <option value="">– chưa gắn –</option>
              {(dm?.chien_dich || []).map((c: any) => <option key={c.id} value={c.id}>{c.ma} · {c.ten}</option>)}</select></label>
            <label>Chi phí thoả thuận (đ)<input type="number" value={fHt.chi_phi} onChange={(e) => setFHt({ ...fHt, chi_phi: e.target.value })} />
              <span className="muted">Đây là số thoả thuận. Tiền thật vẫn phải lập <b>đề nghị chi</b> ở màn hình Đề nghị chi, và gắn chiến dịch ở đó.
                <b> Để trống</b> nghĩa là chưa thoả thuận giá; gõ <b>0</b> nghĩa là không mất tiền (đổi hàng, quà tặng) — hai việc khác nhau.</span></label>
            <label>Đường dẫn bài<input value={fHt.link_bai} onChange={(e) => setFHt({ ...fHt, link_bai: e.target.value })} /></label>
            <label>Trạng thái<select value={fHt.trang_thai} onChange={(e) => setFHt({ ...fHt, trang_thai: e.target.value })}>
              {Object.entries(dm?.hop_tac_trang_thai || {}).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select></label>
          </div>
          <button className="act" disabled={!fHt.ky || !fHt.noi_dung} onClick={() => post(`/bao-chi-kol/kol/${mo.kol.id}/hop-tac`, {
            ...fHt, campaign_id: fHt.campaign_id ? Number(fHt.campaign_id) : null,
            chi_phi: fHt.chi_phi === "" ? null : Number(fHt.chi_phi),
          }).then((r) => { if (r) { setFHt({ ...fHt, noi_dung: "", chi_phi: "", link_bai: "" }); moKol(mo.kol.id); } })}>Ghi lần hợp tác</button>
        </div>}
      </div>}
    </>}
  </>);
}

export default function Page() { return <Shell><BaoChiKol /></Shell>; }
