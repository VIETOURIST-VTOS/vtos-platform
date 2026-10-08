"use client";
import { useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** IR – Pháp chế (Đợt D1, 08/10/2026).
 *
 *  Hai việc trên một màn hình: VĂN BẢN CÓ PHIÊN BẢN và NGHĨA VỤ CÔNG BỐ THÔNG TIN.
 *
 *  Không có ô nào cho người gõ TRẠNG THÁI công bố. Người ghi thời điểm, nơi công bố và văn bản đã
 *  công bố; trạng thái (quá hạn / đúng hạn / trễ) do máy chủ tính bằng quy tắc xác định. Một ô
 *  "đã công bố" gõ được là một lời khai, mà lời khai thì không cần tới phần mềm nào.
 *
 *  Mỗi con số trên màn hình này đều có một cửa nhập cho người dùng — ranh giới 09/9/2026. Hệ thống
 *  không nạp sẵn nghĩa vụ công bố nào: danh mục và thời hạn là quy định pháp luật, và điền chúng
 *  từ trí nhớ của phần mềm thì một hạn sai hiện ra như một lần chậm công bố, không như một lỗi. */

const MAU_TT: Record<string, string> = {
  qua_han: "red", cong_bo_tre: "red", sap_den_han: "warn", chua_ro_han: "warn",
  chua_den_han: "navy", da_cong_bo: "ok",
};
const THU_TU = ["qua_han", "chua_ro_han", "sap_den_han", "cong_bo_tre", "chua_den_han", "da_cong_bo"];
const VB_RONG = { loai: "quy_dinh", so_hieu: "", tieu_de: "", tom_tat: "", nguoi_ky: "", ngay_ky: "" };
const NV_RONG = { ma: "", ten: "", can_cu: "", chu_ky: "su_kien", han_sau_ngay: "", mo_ta_han: "" };
const BG_RONG = { nghia_vu_id: "", ky: "", moc_phat_sinh: "", han_chot: "", ghi_chu: "" };
/* D2_BAN_LAM_VIEC — bàn làm việc Pháp chế. Mỗi bảng mới đều có cửa nhập trên màn hình này:
   không có cửa thì đó là việc còn thiếu, không phải việc để máy nhập hộ (ranh giới 09/9/2026). */
const YC_RONG = { loai: "ra_soat_hop_dong", tieu_de: "", noi_dung: "", phong_gui: "", nguoi_gui: "", muc_do: "thuong", han_mong_muon: "" };
const CK_RONG = { mo_ta: "", nguoi_ky: "", chuc_danh: "", ngay_ky: "", loai_chu_ky: "tuoi", can_cu_tham_quyen: "", ghi_chu: "" };
const RS_RONG = { so_hop_dong: "", doi_tac: "", loai_hop_dong: "", gia_tri: "", ket_luan: "dat", dieu_kien: "", nguoi_ra_soat: "" };
const MAU_YC: Record<string, string> = { moi: "warn", dang_xu_ly: "navy", cho_bo_sung: "warn", xong: "ok", tu_choi: "grey" };
/* D3_NHA_DAU_TU — danh bạ, sổ tiếp xúc, sổ cấp quyền xem hồ sơ.
   Màn hình này KHÔNG có ô nào cho số cổ phần sở hữu: sở hữu là dữ liệu của sổ cổ đông, chép tay
   vào đây là tạo ra con số thứ hai — và hai con số về cùng một thứ thì sớm muộn sẽ lệch. */
const LH_RONG = { ten: "", to_chuc: "", chuc_danh: "", loai: "quy", email: "", dien_thoai: "", can_cu_thu_thap: "", ghi_chu: "" };
const TX_RONG = { lien_he_id: "", ngay: "", hinh_thuc: "gap", noi_dung_tom_tat: "", co_thong_tin_chua_cong_bo: false, thong_tin_da_tiet_lo: "" };
const QH_RONG = { ho_so: "", nguoi_duoc_cap: "", to_chuc: "", ly_do: "", ho_so_chua_cong_bo: true, cam_ket_bao_mat: false, can_cu_cam_ket: "", tu_ngay: "", den_ngay: "" };
const MAU_Q: Record<string, string> = { dang_hieu_luc: "ok", khong_co_han: "red", het_han: "grey", da_thu_hoi: "navy" };

export default function IrPhapCheScreen() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [tab, setTab] = useState<"cong_bo" | "van_ban" | "viec" | "chu_ky" | "ndt">("cong_bo");
  const [meta, setMeta] = useState<any>({ loai_van_ban: {}, trang_thai_van_ban: {}, chu_ky_cong_bo: {}, ghi_duoc: [] });
  const [bdk, setBdk] = useState<any>(null);
  const [nv, setNv] = useState<any>(null);
  const [vb, setVb] = useState<any>(null);
  const [pb, setPb] = useState<any>(null);
  const [fVb, setFVb] = useState<any>({ ...VB_RONG });
  const [fNv, setFNv] = useState<any>({ ...NV_RONG });
  const [fBg, setFBg] = useState<any>({ ...BG_RONG });
  const [noiCb, setNoiCb] = useState<Record<number, string>>({});
  const [mv, setMv] = useState<any>({});
  const [viec, setViec] = useState<any>(null);
  const [ck, setCk] = useState<any>(null);
  const [fYc, setFYc] = useState<any>({ ...YC_RONG });
  const [fCk, setFCk] = useState<any>({ ...CK_RONG });
  const [fRs, setFRs] = useState<any>({ ...RS_RONG });
  const [moRs, setMoRs] = useState<number | null>(null);
  const [ketQua, setKetQua] = useState<Record<number, string>>({});
  const [xn, setXn] = useState<any>(null);
  const [fXn, setFXn] = useState<any>({ chi_muc: "", chu_so_lieu: "" });
  const [ndt, setNdt] = useState<any>(null);
  const [mn, setMn] = useState<any>({});
  const [fLh, setFLh] = useState<any>({ ...LH_RONG });
  const [fTx, setFTx] = useState<any>({ ...TX_RONG });
  const [fQh, setFQh] = useState<any>({ ...QH_RONG });
  const [noiCb2, setNoiCb2] = useState<Record<number, string>>({});
  const ghiDuoc = (meta.ghi_duoc || []).includes(role);

  const load = useCallback(async () => {
    try {
      if (!Object.keys(meta.loai_van_ban).length) setMeta(await api("/ir-phap-che/meta"));
      if (tab === "cong_bo") { setBdk(await api("/ir-phap-che/bang-dieu-khien")); setNv(await api("/ir-phap-che/nghia-vu")); }
      if (tab === "van_ban") setVb(await api("/ir-phap-che/van-ban"));
      if (!Object.keys(mv).length) setMv(await api("/ir-phap-che/meta-viec"));
      if (tab === "viec") setViec(await api("/ir-phap-che/yeu-cau"));
      if (tab === "chu_ky") setCk(await api("/ir-phap-che/chu-ky"));
      if (tab === "ndt") { setNdt(await api("/ir-phap-che/nha-dau-tu")); if (!Object.keys(mn).length) setMn(await api("/ir-phap-che/meta-ndt")); }
    } catch (x) { toast(errMsg(x), true); }
  }, [tab]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);

  const goi = async (path: string, json: any, method = "POST") => {
    try { const r = await api(path, { method, json }); toast(r.message || "Xong"); await load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const moPhienBan = async (gocId: number) => {
    try { setPb(await api(`/ir-phap-che/van-ban/${gocId}/phien-ban`)); }
    catch (x) { toast(errMsg(x), true); }
  };

  return (<>
    <h1>IR – Pháp chế</h1>
    <p className="muted">Hai việc: <b>văn bản có phiên bản</b> và <b>nghĩa vụ công bố thông tin</b>. VTD niêm yết UPCoM
      nên công bố là nghĩa vụ có chế tài, không phải việc nội bộ. Trạng thái công bố do quy tắc xác định tính ra
      từ hạn chốt và thời điểm đã công bố — <b>không có ô nào để gõ “đã công bố”</b>.</p>

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button className={"act " + (tab === "cong_bo" ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab("cong_bo")}>Công bố thông tin</button>
      <button className={"act " + (tab === "van_ban" ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab("van_ban")}>Văn bản</button>
      <button className={"act " + (tab === "viec" ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab("viec")}>Việc Pháp chế</button>
      <button className={"act " + (tab === "chu_ky" ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab("chu_ky")}>Sổ chữ ký</button>
      <button className={"act " + (tab === "ndt" ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab("ndt")}>Nhà đầu tư</button>
    </div>

    {tab === "cong_bo" && bdk && <>
      <div className="kpis">
        {THU_TU.map((k) => <div className="kpi" key={k}>
          <b>{bdk.theo_trang_thai[k]?.so ?? 0}</b><span>{bdk.theo_trang_thai[k]?.ten}</span></div>)}
      </div>
      <p className="muted">{bdk.ghi_chu}</p>
      {THU_TU.filter((k) => (bdk.theo_trang_thai[k]?.rows || []).length).map((k) => (
        <div className="panel wrap" key={k}><h2><Tag cls={MAU_TT[k]}>{bdk.theo_trang_thai[k].ten}</Tag> {bdk.theo_trang_thai[k].so}</h2>
          <table><thead><tr><th>Nghĩa vụ</th><th>Kỳ</th><th>Mốc phát sinh</th><th>Hạn chốt</th><th>Đã công bố</th><th>Nơi công bố</th><th></th></tr></thead>
            <tbody>{bdk.theo_trang_thai[k].rows.map((r: any) => <tr key={r.id}>
              <td><span className="mono">{r.nghia_vu_ma}</span> {r.nghia_vu_ten}</td>
              <td>{r.ky}</td>
              <td>{r.moc_phat_sinh ? fmtD(r.moc_phat_sinh) : ""}</td>
              {/* RỖNG ≠ "còn nhiều thời gian": chưa biết hạn là một việc phải xử lý. */}
              <td>{r.han_chot ? fmtD(r.han_chot) : <Tag cls="warn">chưa xác định</Tag>}</td>
              <td>{r.da_cong_bo_luc ? fmtDT(r.da_cong_bo_luc) : ""}</td>
              <td className="muted">{r.noi_cong_bo}</td>
              <td>{!r.da_cong_bo_luc && ghiDuoc && <>
                <input placeholder="Nơi công bố (HNX, UBCKNN, website…)" style={{ width: 230 }}
                  value={noiCb[r.id] || ""} onChange={(e) => setNoiCb({ ...noiCb, [r.id]: e.target.value })} />
                <button className="act teal" onClick={() => goi(`/ir-phap-che/ban-ghi/${r.id}/da-cong-bo`, { noi_cong_bo: noiCb[r.id] || "" })}>Ghi đã công bố</button>
                <button className="act grey" onClick={async () => { try { setXn(await api(`/ir-phap-che/ban-ghi/${r.id}/xac-nhan`)); setFXn({ chi_muc: "", chu_so_lieu: "", ban_ghi_id: r.id }); } catch (x) { toast(errMsg(x), true); } }}>Xác nhận chủ số liệu</button>
              </>}</td></tr>)}</tbody></table></div>))}

      <div className="panel wrap"><h2>Nghĩa vụ đã khai · {nv?.so ?? 0}</h2>
        <p className="muted">{nv?.ghi_chu}</p>
        {!(nv?.rows || []).length ? <p className="muted">Chưa khai nghĩa vụ nào.</p> :
          <table><thead><tr><th>Mã</th><th>Tên</th><th>Chu kỳ</th><th>Hạn</th><th>Căn cứ</th><th>Người khai</th></tr></thead>
            <tbody>{nv.rows.map((n: any) => <tr key={n.id}>
              <td className="mono">{n.ma}</td><td>{n.ten}</td>
              <td>{meta.chu_ky_cong_bo?.[n.chu_ky] || n.chu_ky}</td>
              <td>{n.han_sau_ngay !== null && n.han_sau_ngay !== undefined ? `${n.han_sau_ngay} ngày từ mốc` : (n.mo_ta_han || <Tag cls="warn">chưa khai</Tag>)}</td>
              <td className="muted" style={{ maxWidth: 360 }}>{n.can_cu}</td>
              <td className="muted">{n.khai_boi}</td></tr>)}</tbody></table>}

        {ghiDuoc && <div style={{ marginTop: 12 }}><h2>Khai một nghĩa vụ</h2>
          <p className="muted"><b>Căn cứ là bắt buộc.</b> Một nghĩa vụ không ai nhớ vì sao có là nghĩa vụ sẽ bị bỏ khi bận.
            Hạn tính bằng số ngày thì điền ô “Hạn sau … ngày”; hạn kiểu khác (“trong 24 giờ”, một mốc cố định trong năm)
            thì để trống ô ấy và mô tả bằng lời — <b>để trống không phải là 0 ngày</b>.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input placeholder="Mã" value={fNv.ma} onChange={(e) => setFNv({ ...fNv, ma: e.target.value })} />
            <input placeholder="Tên nghĩa vụ" style={{ width: 280 }} value={fNv.ten} onChange={(e) => setFNv({ ...fNv, ten: e.target.value })} />
            <select value={fNv.chu_ky} onChange={(e) => setFNv({ ...fNv, chu_ky: e.target.value })}>
              {Object.entries(meta.chu_ky_cong_bo || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="Hạn sau … ngày" style={{ width: 130 }} value={fNv.han_sau_ngay} onChange={(e) => setFNv({ ...fNv, han_sau_ngay: e.target.value })} />
            <input placeholder="Mô tả hạn (nếu không tính bằng ngày)" style={{ width: 280 }} value={fNv.mo_ta_han} onChange={(e) => setFNv({ ...fNv, mo_ta_han: e.target.value })} />
            <input placeholder="Căn cứ – điều khoản nào (bắt buộc)" style={{ width: 360 }} value={fNv.can_cu} onChange={(e) => setFNv({ ...fNv, can_cu: e.target.value })} />
            <button className="act orange" onClick={() => goi("/ir-phap-che/nghia-vu", {
              ...fNv, han_sau_ngay: fNv.han_sau_ngay === "" ? null : Number(fNv.han_sau_ngay),
            }).then((r) => { if (r) setFNv({ ...NV_RONG }); })}>Khai nghĩa vụ</button>
          </div>

          <h2 style={{ marginTop: 16 }}>Mở một lần phải công bố</h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select value={fBg.nghia_vu_id} onChange={(e) => setFBg({ ...fBg, nghia_vu_id: e.target.value })}>
              <option value="">— chọn nghĩa vụ —</option>
              {(nv?.rows || []).map((n: any) => <option key={n.id} value={n.id}>{n.ma} · {n.ten}</option>)}
            </select>
            <input placeholder="Kỳ (2026-Q3, 2026, mã sự kiện…)" value={fBg.ky} onChange={(e) => setFBg({ ...fBg, ky: e.target.value })} />
            <label>Mốc phát sinh <input type="date" value={fBg.moc_phat_sinh} onChange={(e) => setFBg({ ...fBg, moc_phat_sinh: e.target.value })} /></label>
            <label>Hạn chốt <input type="date" value={fBg.han_chot} onChange={(e) => setFBg({ ...fBg, han_chot: e.target.value })} /></label>
            <button className="act orange" onClick={() => goi("/ir-phap-che/ban-ghi", {
              nghia_vu_id: Number(fBg.nghia_vu_id), ky: fBg.ky,
              moc_phat_sinh: fBg.moc_phat_sinh || null, han_chot: fBg.han_chot || null,
              ghi_chu: fBg.ghi_chu,
            }).then((r) => { if (r) setFBg({ ...BG_RONG }); })}>Mở bản ghi</button>
          </div>
          <p className="muted">Bỏ trống hạn chốt thì hệ thống suy từ mốc phát sinh — <b>chỉ khi</b> nghĩa vụ có khai hạn bằng
            số ngày. Không khai thì bản ghi mở ra với trạng thái “chưa xác định được hạn”, và đó là một việc phải xử lý
            chứ không phải một việc để yên tâm.</p>
        </div>}
        {!ghiDuoc && <p className="muted">Vai trò của bạn chỉ ĐỌC màn hình này.</p>}
      </div>
    </>}

    {tab === "van_ban" && vb && <>
      <p className="muted">Sửa một văn bản <b>đã có hiệu lực</b> không ghi đè: nó sinh một phiên bản mới và đóng dấu
        bản cũ. Một quy chế sửa ba lần trong năm mà chỉ lưu bản mới nhất thì không giải trình được một quyết định
        đã ra theo bản cũ.</p>
      <div className="panel wrap"><h2>Văn bản · {vb.so} phiên bản</h2>
        {!vb.rows.length ? <p className="muted">Chưa có văn bản nào.</p> :
          <table><thead><tr><th>Loại</th><th>Số hiệu</th><th>Tiêu đề</th><th className="num">P/bản</th><th>Trạng thái</th><th>Hiệu lực</th><th>Người ký</th><th></th></tr></thead>
            <tbody>{vb.rows.map((v: any) => <tr key={v.id}>
              <td>{meta.loai_van_ban?.[v.loai] || v.loai}</td>
              <td className="mono">{v.so_hieu}</td><td>{v.tieu_de}</td>
              <td className="num">{v.phien_ban}</td>
              <td><Tag cls={v.trang_thai === "hieu_luc" ? "ok" : v.trang_thai === "nhap" ? "warn" : "navy"}>
                {meta.trang_thai_van_ban?.[v.trang_thai] || v.trang_thai}</Tag></td>
              <td>{v.hieu_luc_tu ? fmtD(v.hieu_luc_tu) : ""}{v.hieu_luc_den ? ` → ${fmtD(v.hieu_luc_den)}` : ""}</td>
              <td className="muted">{v.nguoi_ky}</td>
              <td><button className="act grey" onClick={() => moPhienBan(v.goc_id)}>Các phiên bản</button>
                {ghiDuoc && v.trang_thai !== "hieu_luc" && !v.bi_thay_boi &&
                  <button className="act teal" onClick={() => goi(`/ir-phap-che/van-ban/${v.id}/ban-hanh`, {})}>Ban hành</button>}</td></tr>)}</tbody></table>}
      </div>

      {ghiDuoc && <div className="panel wrap"><h2>Thêm văn bản</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select value={fVb.loai} onChange={(e) => setFVb({ ...fVb, loai: e.target.value })}>
            {Object.entries(meta.loai_van_ban || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input placeholder="Số hiệu" value={fVb.so_hieu} onChange={(e) => setFVb({ ...fVb, so_hieu: e.target.value })} />
          <input placeholder="Tiêu đề" style={{ width: 340 }} value={fVb.tieu_de} onChange={(e) => setFVb({ ...fVb, tieu_de: e.target.value })} />
          <input placeholder="Người ký" value={fVb.nguoi_ky} onChange={(e) => setFVb({ ...fVb, nguoi_ky: e.target.value })} />
          <label>Ngày ký <input type="date" value={fVb.ngay_ky} onChange={(e) => setFVb({ ...fVb, ngay_ky: e.target.value })} /></label>
          <input placeholder="Tóm tắt" style={{ width: 340 }} value={fVb.tom_tat} onChange={(e) => setFVb({ ...fVb, tom_tat: e.target.value })} />
          <button className="act orange" onClick={() => goi("/ir-phap-che/van-ban", {
            ...fVb, ngay_ky: fVb.ngay_ky || null,
          }).then((r) => { if (r) setFVb({ ...VB_RONG }); })}>Tạo bản nháp</button>
        </div>
        <p className="muted">Bản nháp sửa tại chỗ. Bấm <b>Ban hành</b> thì bản ấy có hiệu lực và phiên bản trước nó
          bị đóng ngay trong cùng một lượt — không có khoảnh khắc hai bản cùng hiệu lực.</p>
      </div>}

      {pb && <div className="panel wrap"><h2>Lịch sử phiên bản · {pb.so_phien_ban} bản</h2>
        <table><thead><tr><th className="num">P/bản</th><th>Trạng thái</th><th>Hiệu lực</th><th>Lý do sửa</th><th>Bị thay bởi</th><th>Bởi</th></tr></thead>
          <tbody>{pb.rows.map((v: any) => <tr key={v.id}>
            <td className="num">{v.phien_ban}</td>
            <td><Tag cls={v.trang_thai === "hieu_luc" ? "ok" : "navy"}>{meta.trang_thai_van_ban?.[v.trang_thai] || v.trang_thai}</Tag></td>
            <td>{v.hieu_luc_tu ? fmtD(v.hieu_luc_tu) : ""}{v.hieu_luc_den ? ` → ${fmtD(v.hieu_luc_den)}` : ""}</td>
            <td className="muted">{v.ly_do_sua}</td>
            <td className="muted">{v.bi_thay_boi ? `#${v.bi_thay_boi}` : ""}</td>
            <td className="muted">{v.boi}</td></tr>)}</tbody></table>
        <button className="act grey" onClick={() => setPb(null)}>Đóng</button></div>}
    </>}

    {xn && <div className="panel wrap"><h2>Xác nhận chủ số liệu · {xn.so}</h2>
      <p className="muted">Một con số ra khỏi công ty trước khi người chịu trách nhiệm về nó xác nhận là một
        con số không ai đứng tên. Đã hỏi mà chưa trả lời — hoặc đã bị từ chối — thì cửa “ghi đã công bố” không mở.</p>
      {!xn.cong_bo_duoc && <p><Tag cls="red">Chưa công bố được</Tag> {xn.vi_sao_chua}</p>}
      {!!xn.rows.length && <table><thead><tr><th>Chỉ mục</th><th>Chủ số liệu</th><th>Trạng thái</th><th>Ý kiến</th><th></th></tr></thead>
        <tbody>{xn.rows.map((x: any) => <tr key={x.id}>
          <td>{x.chi_muc}</td><td>{x.chu_so_lieu}</td>
          <td><Tag cls={x.trang_thai === "xac_nhan" ? "ok" : x.trang_thai === "tu_choi" ? "red" : "warn"}>{x.trang_thai_ten}</Tag></td>
          <td className="muted">{x.y_kien}</td>
          <td>{x.trang_thai === "cho" && ghiDuoc && <>
            <button className="act teal" onClick={() => goi(`/ir-phap-che/xac-nhan/${x.id}/tra-loi`, { dong_y: true }).then(async () => setXn(await api(`/ir-phap-che/ban-ghi/${x.ban_ghi_id}/xac-nhan`)))}>Xác nhận</button>
            <button className="act grey" onClick={() => { const y = prompt("Lý do từ chối xác nhận:") || ""; if (y.trim()) goi(`/ir-phap-che/xac-nhan/${x.id}/tra-loi`, { dong_y: false, y_kien: y }).then(async () => setXn(await api(`/ir-phap-che/ban-ghi/${x.ban_ghi_id}/xac-nhan`))); }}>Từ chối</button>
          </>}</td></tr>)}</tbody></table>}
      {ghiDuoc && <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
        <input placeholder="Chỉ mục (Doanh thu quý 3…)" style={{ width: 240 }} value={fXn.chi_muc} onChange={(e) => setFXn({ ...fXn, chi_muc: e.target.value })} />
        <input placeholder="Chủ số liệu (phòng / người)" style={{ width: 220 }} value={fXn.chu_so_lieu} onChange={(e) => setFXn({ ...fXn, chu_so_lieu: e.target.value })} />
        <button className="act orange" onClick={() => goi(`/ir-phap-che/ban-ghi/${fXn.ban_ghi_id}/xac-nhan`, { chi_muc: fXn.chi_muc, chu_so_lieu: fXn.chu_so_lieu })
          .then(async (r) => { if (r) { setFXn({ ...fXn, chi_muc: "", chu_so_lieu: "" }); setXn(await api(`/ir-phap-che/ban-ghi/${fXn.ban_ghi_id}/xac-nhan`)); } })}>Hỏi xác nhận</button>
      </div>}
      <button className="act grey" onClick={() => setXn(null)}>Đóng</button></div>}

    {tab === "viec" && viec && <>
      <div className="kpis">
        <div className="kpi"><b>{viec.so_dang_chay}</b><span>Đang chạy</span></div>
        <div className="kpi"><b>{viec.so_ton}</b><span>Treo ≥ {viec.ngay_coi_la_ton} ngày</span></div>
        <div className="kpi"><b>{viec.so_gap_dang_chay}</b><span>Gấp, chưa đóng</span></div>
        <div className="kpi"><b>{viec.so_tat_ca}</b><span>Tất cả</span></div>
      </div>
      <p className="muted">{viec.ghi_chu}</p>
      {mv.con_thieu && <p className="muted"><b>Còn thiếu:</b> {mv.con_thieu}</p>}
      <div className="panel wrap"><h2>Việc gửi Pháp chế</h2>
        {!viec.rows.length ? <p className="muted">Chưa có việc nào.</p> :
          <table><thead><tr><th>#</th><th>Loại</th><th>Tiêu đề</th><th>Bên gửi</th><th>Mức</th><th className="num">Treo</th><th>Trạng thái</th><th>Người nhận</th><th></th></tr></thead>
            <tbody>{viec.rows.map((y: any) => <tr key={y.id}>
              <td className="mono">{y.id}</td><td>{y.loai_ten}</td><td>{y.tieu_de}</td>
              <td className="muted">{y.phong_gui}{y.nguoi_gui ? ` · ${y.nguoi_gui}` : ""}</td>
              <td>{y.muc_do === "gap" ? <Tag cls="red">Gấp</Tag> : <span className="muted">Thường</span>}</td>
              <td className="num">{y.so_ngay_treo === null ? "" : y.so_ngay_treo}</td>
              <td><Tag cls={MAU_YC[y.trang_thai] || "navy"}>{y.trang_thai_ten}</Tag></td>
              <td className="muted">{y.nguoi_nhan}</td>
              <td>{ghiDuoc && <>
                {y.trang_thai === "moi" && <button className="act teal" onClick={() => goi(`/ir-phap-che/yeu-cau/${y.id}/nhan`, {})}>Nhận việc</button>}
                {y.trang_thai !== "xong" && y.trang_thai !== "tu_choi" && <>
                  <input placeholder="Kết quả trả lời (bắt buộc)" style={{ width: 230 }} value={ketQua[y.id] || ""} onChange={(e) => setKetQua({ ...ketQua, [y.id]: e.target.value })} />
                  <button className="act orange" onClick={() => goi(`/ir-phap-che/yeu-cau/${y.id}/dong`, { trang_thai: "xong", ket_qua: ketQua[y.id] || "" })}>Đóng việc</button>
                </>}
                {y.loai === "ra_soat_hop_dong" && <button className="act grey" onClick={() => { setMoRs(y.id); setFRs({ ...RS_RONG }); }}>Rà soát</button>}
              </>}</td></tr>)}</tbody></table>}
      </div>

      {ghiDuoc && <div className="panel wrap"><h2>Mở một việc</h2>
        <p className="muted">Pháp chế ghi lại việc của phòng nào, ai hỏi. <b>Chưa có cửa cho phòng ban tự gửi</b> —
          mở cửa ấy là nới quyền trên nhóm API này cho mọi vai, phải có người ký.</p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select value={fYc.loai} onChange={(e) => setFYc({ ...fYc, loai: e.target.value })}>
            {Object.entries(mv.loai_yeu_cau || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input placeholder="Tiêu đề" style={{ width: 320 }} value={fYc.tieu_de} onChange={(e) => setFYc({ ...fYc, tieu_de: e.target.value })} />
          <input placeholder="Phòng gửi" value={fYc.phong_gui} onChange={(e) => setFYc({ ...fYc, phong_gui: e.target.value })} />
          <input placeholder="Người gửi" value={fYc.nguoi_gui} onChange={(e) => setFYc({ ...fYc, nguoi_gui: e.target.value })} />
          <select value={fYc.muc_do} onChange={(e) => setFYc({ ...fYc, muc_do: e.target.value })}>
            {Object.entries(mv.muc_do || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select>
          <label>Hạn mong muốn <input type="date" value={fYc.han_mong_muon} onChange={(e) => setFYc({ ...fYc, han_mong_muon: e.target.value })} /></label>
          <input placeholder="Nội dung" style={{ width: 360 }} value={fYc.noi_dung} onChange={(e) => setFYc({ ...fYc, noi_dung: e.target.value })} />
          <button className="act orange" onClick={() => goi("/ir-phap-che/yeu-cau", { ...fYc, han_mong_muon: fYc.han_mong_muon || null }).then((r) => { if (r) setFYc({ ...YC_RONG }); })}>Mở việc</button>
        </div>
        <p className="muted">Hạn mong muốn của bên gửi <b>không phải</b> hạn pháp lý — hạn pháp lý nằm ở sổ nghĩa vụ công bố, có căn cứ điều khoản đi kèm.</p>
      </div>}

      {moRs !== null && ghiDuoc && <div className="panel wrap"><h2>Rà soát hợp đồng · việc #{moRs}</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input placeholder="Số hợp đồng" value={fRs.so_hop_dong} onChange={(e) => setFRs({ ...fRs, so_hop_dong: e.target.value })} />
          <input placeholder="Đối tác" style={{ width: 240 }} value={fRs.doi_tac} onChange={(e) => setFRs({ ...fRs, doi_tac: e.target.value })} />
          <input placeholder="Loại hợp đồng" value={fRs.loai_hop_dong} onChange={(e) => setFRs({ ...fRs, loai_hop_dong: e.target.value })} />
          <input placeholder="Giá trị (để trống nếu chưa biết)" style={{ width: 200 }} value={fRs.gia_tri} onChange={(e) => setFRs({ ...fRs, gia_tri: e.target.value })} />
          <select value={fRs.ket_luan} onChange={(e) => setFRs({ ...fRs, ket_luan: e.target.value })}>
            {Object.entries(mv.ket_luan_ra_soat || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input placeholder="Điều kiện (bắt buộc nếu đạt có điều kiện)" style={{ width: 360 }} value={fRs.dieu_kien} onChange={(e) => setFRs({ ...fRs, dieu_kien: e.target.value })} />
          <input placeholder="Người rà soát" value={fRs.nguoi_ra_soat} onChange={(e) => setFRs({ ...fRs, nguoi_ra_soat: e.target.value })} />
          <button className="act orange" onClick={() => goi(`/ir-phap-che/yeu-cau/${moRs}/ra-soat`, {
            ...fRs, gia_tri: fRs.gia_tri === "" ? null : Number(fRs.gia_tri),
          }, "PUT")}>Lưu rà soát</button>
          <button className="act grey" onClick={() => setMoRs(null)}>Đóng</button>
        </div>
        <p className="muted"><b>Giá trị để trống là “chưa biết”, không phải 0.</b> Và kết luận “đạt có điều kiện”
          bắt buộc ghi điều kiện — không viết ra thì lần đọc lại chỉ còn thấy chữ “đạt”.</p>
      </div>}
    </>}

    {tab === "chu_ky" && ck && <>
      <p className="muted">Sổ chữ ký trả lời một câu: <b>ai ký cái gì, ngày nào, theo thẩm quyền nào</b>. Căn cứ thẩm
        quyền là bắt buộc — đó là câu hỏi đầu tiên của mọi lần soát lại một chữ ký.</p>
      <div className="panel wrap"><h2>Sổ chữ ký · {ck.so}</h2>
        {!ck.rows.length ? <p className="muted">Sổ còn rỗng.</p> :
          <table><thead><tr><th>Ngày ký</th><th>Người ký</th><th>Chức danh</th><th>Đã ký</th><th>Loại</th><th>Căn cứ thẩm quyền</th></tr></thead>
            <tbody>{ck.rows.map((b: any) => <tr key={b.id}>
              <td>{fmtD(b.ngay_ky)}</td><td>{b.nguoi_ky}</td><td className="muted">{b.chuc_danh}</td>
              <td>{b.mo_ta || (b.van_ban_id ? `Văn bản #${b.van_ban_id}` : "")}</td>
              <td>{b.loai_chu_ky_ten}</td>
              <td className="muted" style={{ maxWidth: 380 }}>{b.can_cu_tham_quyen}</td></tr>)}</tbody></table>}
      </div>
      {ghiDuoc && <div className="panel wrap"><h2>Ghi một chữ ký</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input placeholder="Đã ký cái gì" style={{ width: 300 }} value={fCk.mo_ta} onChange={(e) => setFCk({ ...fCk, mo_ta: e.target.value })} />
          <input placeholder="Người ký" value={fCk.nguoi_ky} onChange={(e) => setFCk({ ...fCk, nguoi_ky: e.target.value })} />
          <input placeholder="Chức danh" value={fCk.chuc_danh} onChange={(e) => setFCk({ ...fCk, chuc_danh: e.target.value })} />
          <label>Ngày ký <input type="date" value={fCk.ngay_ky} onChange={(e) => setFCk({ ...fCk, ngay_ky: e.target.value })} /></label>
          <select value={fCk.loai_chu_ky} onChange={(e) => setFCk({ ...fCk, loai_chu_ky: e.target.value })}>
            {Object.entries(mv.loai_chu_ky || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input placeholder="Căn cứ thẩm quyền (bắt buộc)" style={{ width: 380 }} value={fCk.can_cu_tham_quyen} onChange={(e) => setFCk({ ...fCk, can_cu_tham_quyen: e.target.value })} />
          <button className="act orange" onClick={() => goi("/ir-phap-che/chu-ky", { ...fCk, ngay_ky: fCk.ngay_ky || null }).then((r) => { if (r) setFCk({ ...CK_RONG }); })}>Ghi sổ</button>
        </div>
      </div>}
    </>}

    {tab === "ndt" && ndt && <>
      <div className="kpis">
        <div className="kpi"><b>{ndt.lien_he.so}</b><span>Đầu mối</span></div>
        <div className="kpi"><b>{ndt.tiep_xuc.so}</b><span>Lần tiếp xúc</span></div>
        <div className="kpi"><b>{ndt.tiep_xuc.so_chua_xu_ly_tiet_lo}</b><span>Tiết lộ chưa công bố</span></div>
        <div className="kpi"><b>{ndt.quyen.so_khong_co_han}</b><span>Quyền KHÔNG hạn</span></div>
        <div className="kpi"><b>{ndt.quyen.so_sap_het_han}</b><span>Sắp hết hạn</span></div>
      </div>
      <p className="muted">{ndt.ghi_chu}</p>
      {ndt.lien_he.da_che && <p className="muted">Vai của bạn thấy <b>đã tiếp xúc với ai</b>, không thấy email và
        số điện thoại đầy đủ. Đây là thu hẹp có chủ ý, không phải lỗi hiển thị.</p>}

      <div className="panel wrap"><h2>Sổ tiếp xúc · {ndt.tiep_xuc.so}</h2>
        <p className="muted">Nói một thông tin chưa công bố cho một nhà đầu tư trước những người khác là
          <b> tiết lộ chọn lọc</b>. Hệ thống không ngăn được việc ấy, nhưng nó bắt ghi lại và bắt nối tới
          bản công bố đã đưa thông tin ấy ra công chúng.</p>
        {!ndt.tiep_xuc.rows.length ? <p className="muted">Chưa ghi lần tiếp xúc nào.</p> :
          <table><thead><tr><th>Ngày</th><th>Đầu mối</th><th>Hình thức</th><th>Tóm tắt</th><th>Chưa công bố</th><th></th></tr></thead>
            <tbody>{ndt.tiep_xuc.rows.map((t: any) => <tr key={t.id}>
              <td>{fmtD(t.ngay)}</td>
              <td>{t.lien_he_ten}<span className="muted">{t.lien_he_to_chuc ? ` · ${t.lien_he_to_chuc}` : ""}</span></td>
              <td>{t.hinh_thuc_ten}</td>
              <td className="muted" style={{ maxWidth: 320 }}>{t.noi_dung_tom_tat}</td>
              <td>{t.co_thong_tin_chua_cong_bo
                ? (t.chua_xu_ly_tiet_lo ? <Tag cls="red">Chưa nối bản công bố</Tag> : <Tag cls="ok">Đã công bố · #{t.ban_ghi_cong_bo_id}</Tag>)
                : <span className="muted">Không</span>}</td>
              <td>{t.chua_xu_ly_tiet_lo && ghiDuoc && <>
                <input placeholder="ID bản ghi công bố" style={{ width: 150 }} value={noiCb2[t.id] || ""} onChange={(e) => setNoiCb2({ ...noiCb2, [t.id]: e.target.value })} />
                <button className="act teal" onClick={() => goi(`/ir-phap-che/tiep-xuc/${t.id}/noi-cong-bo`, { ban_ghi_cong_bo_id: Number(noiCb2[t.id] || 0) })}>Nối</button>
              </>}</td></tr>)}</tbody></table>}
        {ghiDuoc && <div style={{ marginTop: 10 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <select value={fTx.lien_he_id} onChange={(e) => setFTx({ ...fTx, lien_he_id: e.target.value })}>
              <option value="">— chọn đầu mối —</option>
              {ndt.lien_he.rows.map((l: any) => <option key={l.id} value={l.id}>{l.ten}{l.to_chuc ? ` · ${l.to_chuc}` : ""}</option>)}
            </select>
            <label>Ngày <input type="date" value={fTx.ngay} onChange={(e) => setFTx({ ...fTx, ngay: e.target.value })} /></label>
            <select value={fTx.hinh_thuc} onChange={(e) => setFTx({ ...fTx, hinh_thuc: e.target.value })}>
              {Object.entries(mn.hinh_thuc_tiep_xuc || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="Tóm tắt nội dung" style={{ width: 300 }} value={fTx.noi_dung_tom_tat} onChange={(e) => setFTx({ ...fTx, noi_dung_tom_tat: e.target.value })} />
            <label><input type="checkbox" checked={fTx.co_thong_tin_chua_cong_bo} onChange={(e) => setFTx({ ...fTx, co_thong_tin_chua_cong_bo: e.target.checked })} /> Có nói thông tin chưa công bố</label>
            {fTx.co_thong_tin_chua_cong_bo && <input placeholder="Đã nói gì (bắt buộc)" style={{ width: 300 }} value={fTx.thong_tin_da_tiet_lo} onChange={(e) => setFTx({ ...fTx, thong_tin_da_tiet_lo: e.target.value })} />}
            <button className="act orange" onClick={() => goi("/ir-phap-che/tiep-xuc", { ...fTx, lien_he_id: Number(fTx.lien_he_id), ngay: fTx.ngay || null }).then((r) => { if (r) setFTx({ ...TX_RONG }); })}>Ghi tiếp xúc</button>
          </div>
        </div>}
      </div>

      <div className="panel wrap"><h2>Quyền xem hồ sơ · {ndt.quyen.so}</h2>
        <p className="muted">Quyền xem hồ sơ chưa công bố mà <b>không có ngày hết hạn</b> là quyền sẽ còn sống
          sau khi lý do cấp nó đã chết. Nó có trạng thái riêng, không trộn vào “đang hiệu lực”.</p>
        {!ndt.quyen.rows.length ? <p className="muted">Chưa cấp quyền nào.</p> :
          <table><thead><tr><th>Hồ sơ</th><th>Người được cấp</th><th>Lý do</th><th>Từ</th><th>Đến</th><th>Trạng thái</th><th>Cam kết</th><th></th></tr></thead>
            <tbody>{ndt.quyen.rows.map((q: any) => <tr key={q.id}>
              <td>{q.ho_so}</td>
              <td>{q.nguoi_duoc_cap}<span className="muted">{q.to_chuc ? ` · ${q.to_chuc}` : ""}</span></td>
              <td className="muted" style={{ maxWidth: 240 }}>{q.ly_do}</td>
              <td>{fmtD(q.tu_ngay)}</td>
              <td>{q.den_ngay ? fmtD(q.den_ngay) : <Tag cls="red">không hạn</Tag>}</td>
              <td><Tag cls={MAU_Q[q.trang_thai] || "navy"}>{q.trang_thai_ten}</Tag>
                {q.sap_het_han && <span className="muted"> còn {q.con_lai_ngay} ngày</span>}</td>
              <td className="muted" style={{ maxWidth: 220 }}>{q.cam_ket_bao_mat ? q.can_cu_cam_ket : (q.ho_so_chua_cong_bo ? "—" : "hồ sơ đã công bố")}</td>
              <td>{!q.thu_hoi_luc && ghiDuoc && <button className="act grey" onClick={() => goi(`/ir-phap-che/quyen-ho-so/${q.id}/thu-hoi`, {})}>Thu hồi</button>}</td></tr>)}</tbody></table>}
        {ghiDuoc && <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input placeholder="Hồ sơ" style={{ width: 240 }} value={fQh.ho_so} onChange={(e) => setFQh({ ...fQh, ho_so: e.target.value })} />
          <input placeholder="Người được cấp" value={fQh.nguoi_duoc_cap} onChange={(e) => setFQh({ ...fQh, nguoi_duoc_cap: e.target.value })} />
          <input placeholder="Tổ chức" value={fQh.to_chuc} onChange={(e) => setFQh({ ...fQh, to_chuc: e.target.value })} />
          <input placeholder="Lý do (bắt buộc)" style={{ width: 260 }} value={fQh.ly_do} onChange={(e) => setFQh({ ...fQh, ly_do: e.target.value })} />
          <label><input type="checkbox" checked={fQh.ho_so_chua_cong_bo} onChange={(e) => setFQh({ ...fQh, ho_so_chua_cong_bo: e.target.checked })} /> Hồ sơ chưa công bố</label>
          {fQh.ho_so_chua_cong_bo && <>
            <label><input type="checkbox" checked={fQh.cam_ket_bao_mat} onChange={(e) => setFQh({ ...fQh, cam_ket_bao_mat: e.target.checked })} /> Có cam kết bảo mật</label>
            <input placeholder="Căn cứ cam kết (NDA số mấy, ký ngày nào)" style={{ width: 300 }} value={fQh.can_cu_cam_ket} onChange={(e) => setFQh({ ...fQh, can_cu_cam_ket: e.target.value })} />
          </>}
          <label>Từ <input type="date" value={fQh.tu_ngay} onChange={(e) => setFQh({ ...fQh, tu_ngay: e.target.value })} /></label>
          <label>Đến <input type="date" value={fQh.den_ngay} onChange={(e) => setFQh({ ...fQh, den_ngay: e.target.value })} /></label>
          <button className="act orange" onClick={() => goi("/ir-phap-che/quyen-ho-so", { ...fQh, tu_ngay: fQh.tu_ngay || null, den_ngay: fQh.den_ngay || null }).then((r) => { if (r) setFQh({ ...QH_RONG }); })}>Cấp quyền</button>
        </div>}
      </div>

      <div className="panel wrap"><h2>Danh bạ · {ndt.lien_he.so}</h2>
        {!ndt.lien_he.rows.length ? <p className="muted">Danh bạ còn rỗng.</p> :
          <table><thead><tr><th>Tên</th><th>Tổ chức</th><th>Loại</th><th>Email</th><th>Điện thoại</th><th>Căn cứ thu thập</th></tr></thead>
            <tbody>{ndt.lien_he.rows.map((l: any) => <tr key={l.id}>
              <td>{l.ten}</td><td>{l.to_chuc}</td><td>{l.loai_ten}</td>
              <td className="mono">{l.email}</td><td className="mono">{l.dien_thoai}</td>
              <td className="muted" style={{ maxWidth: 300 }}>{l.can_cu_thu_thap}</td></tr>)}</tbody></table>}
        {ghiDuoc && <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input placeholder="Tên" value={fLh.ten} onChange={(e) => setFLh({ ...fLh, ten: e.target.value })} />
          <input placeholder="Tổ chức" style={{ width: 220 }} value={fLh.to_chuc} onChange={(e) => setFLh({ ...fLh, to_chuc: e.target.value })} />
          <input placeholder="Chức danh" value={fLh.chuc_danh} onChange={(e) => setFLh({ ...fLh, chuc_danh: e.target.value })} />
          <select value={fLh.loai} onChange={(e) => setFLh({ ...fLh, loai: e.target.value })}>
            {Object.entries(mn.loai_lien_he || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input placeholder="Email" value={fLh.email} onChange={(e) => setFLh({ ...fLh, email: e.target.value })} />
          <input placeholder="Điện thoại" value={fLh.dien_thoai} onChange={(e) => setFLh({ ...fLh, dien_thoai: e.target.value })} />
          <input placeholder="Căn cứ thu thập (bắt buộc nếu có email/điện thoại)" style={{ width: 360 }} value={fLh.can_cu_thu_thap} onChange={(e) => setFLh({ ...fLh, can_cu_thu_thap: e.target.value })} />
          <button className="act orange" onClick={() => goi("/ir-phap-che/lien-he", fLh).then((r) => { if (r) setFLh({ ...LH_RONG }); })}>Thêm đầu mối</button>
        </div>}
        <p className="muted">Email và điện thoại là <b>dữ liệu cá nhân</b> (Nghị định 13/2023): lưu thì phải ghi được
          nó từ đâu mà có. Một danh bạ không giải trình được nguồn là loại rủi ro chỉ hiện ra khi có người hỏi.</p>
      </div>
    </>}
  </>);
}
