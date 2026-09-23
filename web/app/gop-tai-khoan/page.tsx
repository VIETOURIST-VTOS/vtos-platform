"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Gộp tài khoản trùng – chuyển hết dữ liệu sang một tài khoản, rồi KHOÁ cái thừa.
 *
 *  BA BƯỚC, KHÔNG RÚT GỌN ĐƯỢC: chọn giữ cái nào → xem trước bao nhiêu dòng sẽ chuyển → xác nhận.
 *  Bước xem trước không bỏ được, vì gộp là việc MỘT CHIỀU: chuyển 290 booking sang nhầm người rồi
 *  thì không có nút tách ra lại.
 *
 *  Màn hình cố ý KHÔNG có nút "gộp tất cả". Mỗi cặp là một quyết định về một con người thật.
 */
function GopTaiKhoan() {
  const { user, toast } = useShell();
  const canGop = ["chutich", "tgd", "cntt"].includes(user?.role || "");
  const [d, setD] = useState<any>(null);
  const [xt, setXt] = useState<any>(null);
  const [dang, setDang] = useState<{ giu: number; bo: number } | null>(null);

  const load = useCallback(() => { api("/gop-tai-khoan/cap-trung").then(setD).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const xem = async (giu: number, bo: number) => {
    setXt(null); setDang({ giu, bo });
    try { setXt(await api(`/gop-tai-khoan/xem-truoc?giu_id=${giu}&bo_id=${bo}`)); }
    catch (x) { toast(errMsg(x), true); setDang(null); }
  };
  const gop = async () => {
    if (!dang || !xt) return;
    const ly = prompt(`Gộp ${xt.bo.ho_ten} (${xt.bo.tai_khoan}) vào ${xt.giu.ho_ten} (${xt.giu.tai_khoan}).\n` +
                      `${xt.tong_dong_se_chuyen} dòng dữ liệu sẽ chuyển. Việc này KHÔNG hoàn lại được.\n\nLý do:`);
    if (!ly) return;
    try {
      const r = await api("/gop-tai-khoan", { method: "POST", json: { ...dang, giu_id: dang.giu, bo_id: dang.bo, ly_do: ly, xac_nhan: true } });
      toast(r.message || "Đã gộp"); setXt(null); setDang(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };

  return (<>
    <h1>Tài khoản trùng</h1>
    <p className="muted">Một người có hai tài khoản thì doanh số bị xẻ đôi, và không bảng nào báo lỗi.
      Gộp là <b>chuyển hết dữ liệu sang một tài khoản rồi khoá cái thừa</b> – không xoá, để nhật ký nghiệp vụ
      còn tra ra được ai đã làm gì.</p>

    <div className="panel wrap"><h2>Những người có nhiều hơn một tài khoản</h2>
      <table><thead><tr><th>Họ tên</th><th>Tài khoản</th><th>Vai</th><th>Mã NV</th><th className="num">Dòng dữ liệu</th><th>Trạng thái</th>{canGop && <th></th>}</tr></thead>
        <tbody>{(d?.rows || []).map((n: any) => n.tai_khoan.map((t: any, i: number) => (
          <tr key={t.id}>
            {i === 0 && <td rowSpan={n.tai_khoan.length}><b>{n.ten}</b>
              <small style={{ display: "block", color: "var(--vtos-text-faint)" }}>{n.vi_sao}</small></td>}
            <td className="mono">{t.tai_khoan}{t.id === n.goi_y_giu && <> <Tag cls="ok">nên giữ</Tag></>}</td>
            <td>{t.vai}</td>
            <td className="mono">{t.ma_nv || <span className="muted">–</span>}</td>
            <td className="num">{t.so_dong}</td>
            <td>{t.dang_mo ? <Tag cls="navy">Đang mở</Tag> : <Tag cls="red">Đã khoá</Tag>}</td>
            {canGop && <td>{t.id !== n.goi_y_giu && n.goi_y_giu && t.dang_mo &&
              <button className="act" onClick={() => xem(n.goi_y_giu, t.id)}>Gộp vào {n.tai_khoan.find((x: any) => x.id === n.goi_y_giu)?.tai_khoan}</button>}</td>}
          </tr>))).flat()}
        {!(d?.rows || []).length && <tr><td colSpan={canGop ? 7 : 6}><Tag cls="ok">Không còn ai trùng tài khoản</Tag></td></tr>}
        </tbody></table>
      <p className="muted">{d?.ghi_chu}</p></div>

    {xt && <div className="panel"><h2>Xem trước – chưa ghi gì</h2>
      <p>Chuyển <b>{xt.tong_dong_se_chuyen}</b> dòng từ <b className="mono">{xt.bo.tai_khoan}</b> ({xt.bo.ho_ten})
        sang <b className="mono">{xt.giu.tai_khoan}</b> ({xt.giu.ho_ten}), rồi khoá tài khoản cũ.</p>
      {xt.canh_bao && <p><Tag cls="warn">{xt.canh_bao}</Tag></p>}
      <div className="wrap"><table><thead><tr><th>Bảng</th><th>Cột</th><th className="num">Số dòng</th></tr></thead>
        <tbody>{xt.chi_tiet.map((c: any) => <tr key={c.bang + c.cot}>
          <td className="mono">{c.bang}</td><td className="mono">{c.cot}</td><td className="num">{c.so_dong}</td></tr>)}
        {!xt.chi_tiet.length && <tr><td colSpan={3} className="muted">Tài khoản này không giữ dòng nào – gộp xong chỉ là khoá lại.</td></tr>}
        </tbody></table></div>
      <div style={{ marginTop: 12 }}>
        <button className="act orange" onClick={gop}>Xác nhận gộp</button>{" "}
        <button className="act" onClick={() => { setXt(null); setDang(null); }}>Thôi</button>
      </div>
      <p className="muted"><b>Việc này không hoàn lại được.</b> Không có nút tách ngược – muốn tách phải sửa tay từng bảng.
        Đọc kỹ bảng trên rồi hãy bấm.</p>
    </div>}
  </>);
}

export default function Page() { return <Shell><GopTaiKhoan /></Shell>; }
