"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, getUser, vnd } from "@/lib/api";
import { errMsg } from "@/components/ui";
import ThanhViec, { baoDaDoi } from "@/components/ThanhViec";

/** GHI GIÁ DẦU MỘT NGÀY — màn TOÀN MÀN (luật 2 anh Tuấn chốt 16/10/2026).
 *
 *  MỘT DÒNG CHO MỘT NGÀY CÓ GIÁ MỚI. Màn này vì thế hiện dòng gần nhất ngay cạnh ô nhập: người ghi
 *  thấy giá đang áp dụng là bao nhiêu từ ngày nào, nên biết mình đang ghi một lần điều chỉnh mới
 *  hay đang ghi trùng.
 *
 *  KHÔNG TỰ ĐIỀN GIÁ GẦN NHẤT vào ô. Gợi ý một con số vào ô nhập là cách chắc chắn để một ngày nào
 *  đó có người bấm Lưu mà không đọc — và một giá dầu sai thì mọi số lít của kỳ ấy sai theo, trông
 *  vẫn hợp lý. Giá cũ chỉ ĐỨNG CẠNH để đối chiếu, không nhảy vào ô.
 *
 *  NGUỒN ĐỂ TRUY VỀ SAU. "Petrolimex", "hoá đơn trạm", "hợp đồng" — ba tháng sau có người hỏi con
 *  số này lấy ở đâu thì câu trả lời nằm ngay trên dòng, không phải đi tìm người đã ghi.
 */

const GHI_GIA_DAU = ["cntt", "ketoan", "gd_doi_xe"];

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/doi-xe/gia-dau">Giá dầu</a> · Ghi giá</>;

const homNay = () => new Date().toISOString().slice(0, 10);

function GhiGiaDau() {
  const { toast } = useShell();
  const vai = getUser()?.role || "";
  const duocGhi = GHI_GIA_DAU.includes(vai);

  const [loaiDs, setLoaiDs] = useState<any[]>([]);
  const [ganNhat, setGanNhat] = useState<any>(null);
  const [ngay, setNgay] = useState(homNay);
  const [loai, setLoai] = useState("do");
  const [gia, setGia] = useState("");
  const [nguon, setNguon] = useState("Petrolimex");
  const [dangLuu, setDangLuu] = useState(false);

  const nap = useCallback(async () => {
    try {
      const a = await api<any>("/fleet/gia-dau");
      setLoaiDs(a?.loai || []);
      const rows: any[] = a?.rows || [];
      setGanNhat(rows.length ? rows[0] : null);
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { nap(); }, [nap]);

  const giaDa = Number(String(gia).replace(/[^\d]/g, "")) || 0;
  const thieu = !ngay || !loai || giaDa <= 0;
  const cungNgay = !!(ganNhat && ganNhat.ngay === ngay && ganNhat.loai === loai);

  const luu = async () => {
    if (thieu || dangLuu) return;
    setDangLuu(true);
    try {
      await api("/fleet/gia-dau", {
        method: "POST",
        json: { ngay, loai, gia_lit: giaDa, nguon: nguon.trim() },
      });
      baoDaDoi("vừa ghi một giá dầu");
      toast("Đã ghi giá dầu ngày " + ngay);
      window.location.href = "/doi-xe/gia-dau";
    } catch (e) { toast(errMsg(e), true); setDangLuu(false); }
  };

  const viec = [
    {
      nhan: dangLuu ? "Đang lưu…" : "Lưu giá dầu",
      href: "#",
      chinh: true,
      len: true,
      tat: !duocGhi
        ? "Cửa ghi giá dầu mở cho kế toán, Giám đốc đội xe và CNTT."
        : thieu ? "Còn thiếu ngày, loại hoặc giá một lít." : "",
    },
    { nhan: "‹ Lên một cấp", href: "/doi-xe/gia-dau", len: true },
  ];

  return (<>
    <ThanhViec toanMan duong={DUONG} viec={viec} />
    <h1>Ghi giá dầu một ngày</h1>

    {!duocGhi && <p className="panel">
      Vai <b>{getUser()?.role_name || vai}</b> không ghi được giá dầu. Cửa <span className="mono">POST
      /fleet/gia-dau</span> mở cho kế toán, Giám đốc đội xe và CNTT. Anh/chị vẫn xem được{" "}
      <a href="/doi-xe/gia-dau">sổ giá dầu</a>.
    </p>}

    {duocGhi && <form onSubmit={(e) => { e.preventDefault(); luu(); }}>
      {ganNhat && <p className="panel">
        Dòng gần nhất: <b>{(ganNhat.loai_ten || ganNhat.loai)}</b> · <b>{vnd(ganNhat.gia_lit)} đ/lít</b>{" "}
        áp dụng từ <b>{fmtD(ganNhat.ngay)}</b>
        {ganNhat.nguon ? <> · nguồn {ganNhat.nguon}</> : null}.{" "}
        <span className="muted">Giá này giữ nguyên đến ngày có dòng kế tiếp — nên chỉ ghi khi giá
          thật sự đã đổi.</span>
      </p>}

      <div className="panel">
        <div className="grid2">
          <div>
            <label htmlFor="d-ngay">Ngày áp dụng *</label>
            <input id="d-ngay" type="date" value={ngay} onChange={(e) => setNgay(e.target.value)} />
            {cungNgay && <p className="muted"><b>Đã có dòng cho đúng ngày và loại này.</b> Ghi thêm
              là có hai giá cho một ngày — kiểm lại trước khi lưu.</p>}
          </div>

          <div>
            <label htmlFor="d-loai">Loại *</label>
            <select id="d-loai" value={loai} onChange={(e) => setLoai(e.target.value)}>
              {loaiDs.length
                ? loaiDs.map((l: any) => <option key={l.ma} value={l.ma}>{l.ten}</option>)
                : <option value="do">Dầu DO</option>}
            </select>
          </div>

          <div>
            <label htmlFor="d-gia">Giá một lít (đ) *</label>
            <input id="d-gia" type="text" inputMode="numeric" value={gia}
              onChange={(e) => setGia(e.target.value)} placeholder="19850" />
            {giaDa > 0 && <p className="muted">{giaDa.toLocaleString("vi-VN")} đ/lít</p>}
          </div>

          <div>
            <label htmlFor="d-nguon">Nguồn</label>
            <input id="d-nguon" type="text" maxLength={120} value={nguon}
              onChange={(e) => setNguon(e.target.value)} placeholder="Petrolimex / hoá đơn trạm / hợp đồng" />
            <p className="muted">Để ba tháng sau truy được con số lấy ở đâu.</p>
          </div>
        </div>
        <p className="muted">Người ghi và lúc ghi do máy chủ tự lưu — màn này không hỏi.</p>
      </div>

      <button className="act" type="submit" disabled={thieu || dangLuu}>
        {dangLuu ? "Đang lưu…" : "Lưu giá dầu"}
      </button>
    </form>}
  </>);
}

export default function Page() { return <Shell><GhiGiaDau /></Shell>; }
