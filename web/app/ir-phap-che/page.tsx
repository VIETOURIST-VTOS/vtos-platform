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

export default function IrPhapCheScreen() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [tab, setTab] = useState<"cong_bo" | "van_ban">("cong_bo");
  const [meta, setMeta] = useState<any>({ loai_van_ban: {}, trang_thai_van_ban: {}, chu_ky_cong_bo: {}, ghi_duoc: [] });
  const [bdk, setBdk] = useState<any>(null);
  const [nv, setNv] = useState<any>(null);
  const [vb, setVb] = useState<any>(null);
  const [pb, setPb] = useState<any>(null);
  const [fVb, setFVb] = useState<any>({ ...VB_RONG });
  const [fNv, setFNv] = useState<any>({ ...NV_RONG });
  const [fBg, setFBg] = useState<any>({ ...BG_RONG });
  const [noiCb, setNoiCb] = useState<Record<number, string>>({});
  const ghiDuoc = (meta.ghi_duoc || []).includes(role);

  const load = useCallback(async () => {
    try {
      if (!Object.keys(meta.loai_van_ban).length) setMeta(await api("/ir-phap-che/meta"));
      if (tab === "cong_bo") { setBdk(await api("/ir-phap-che/bang-dieu-khien")); setNv(await api("/ir-phap-che/nghia-vu")); }
      if (tab === "van_ban") setVb(await api("/ir-phap-che/van-ban"));
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
  </>);
}
