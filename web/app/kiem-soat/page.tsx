"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

/** Kiểm soát – bàn làm việc của robot giữ vị trí Kiểm soát (chỉ đạo 07/9/2026).
 *
 *  Bốn việc: kiểm tra, thử, giám sát, báo cáo mọi phòng ban về Chủ tịch.
 *
 *  Hai điều màn hình phải nói thẳng, không được làm mềm đi:
 *   - Robot KHÔNG sửa được số của phòng ban nó giám sát. Nó mở việc ra được, đóng lại là quyền của người.
 *   - Điểm do máy chấm là ĐỀ XUẤT tới khi Chủ tịch hậu kiểm; phòng chưa đủ số liệu thì ghi "chưa đủ cơ
 *     sở", không chấm 0 – chưa có số liệu và làm kém là hai chuyện khác nhau. */
const TABS: [string, string][] = [
  ["phat_hien", "Việc phát hiện"], ["bao_cao", "Báo cáo gửi Chủ tịch"], ["diem", "Chấm điểm phòng ban"],
];

function KiemSoatPage() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const laLanhDao = ["chutich", "tgd"].includes(user?.role || "");
  const chayDuoc = ["chutich", "tgd", "bks", "cntt"].includes(user?.role || "");
  const [tab, setTab] = useState("phat_hien");
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [dangChay, setDangChay] = useState("");

  const load = useCallback(() => {
    api("/kiem-soat").then((x) => { setD(x); setLoi(""); }).catch((e) => setLoi(errMsg(e)));
  }, []);
  useEffect(load, [load]);

  const goi = async (path: string, json?: any) => {
    setDangChay(path);
    try {
      const r = await api<any>(`/kiem-soat/${path}`, { method: "POST", json });
      toast(r.message || r.ghi_chu || "Xong"); load();
    } catch (e) { toast(errMsg(e), true); } finally { setDangChay(""); }
  };

  const th = d?.tong_hop;
  const conSong = (d?.phat_hien || []).filter((p: any) => p.con);
  const daHet = (d?.phat_hien || []).filter((p: any) => !p.con);

  return (
    <main>{hop}
      <h1>Kiểm soát</h1>
      <p className="muted" style={{ marginTop: -6 }}>
        Vị trí Kiểm soát do robot giữ: kiểm tra, thử, giám sát và báo cáo mọi phòng ban về Chủ tịch.
        Robot đọc được toàn hệ thống nhưng <b>không sửa được số của phòng ban nào</b> – nó mở việc ra
        được, đóng lại là quyền của người. Không có báo cáo định kỳ: chỉ báo khi có việc nghiêm trọng.
      </p>

      {loi && <div className="gate fail">{loi}</div>}

      {/* TUỔI CỦA TẤM ẢNH. Ngày 30/9/2026 bàn này vẽ số liệu chốt 10/9 mà không có một chữ nào nói ra
          điều đó: một việc đã hết từ 19 ngày trước vẫn treo đỏ "nghiêm trọng · đã báo Chủ tịch". Một
          bàn giám sát đứng hình còn nguy hơn bàn trống, vì người đọc tin rằng mình đang nhìn hôm nay. */}
      {d && d.ban_cu && (
        <div className="gate fail" style={{ marginBottom: 12 }}>
          <b>Bàn giám sát đang là ảnh cũ.</b>{" "}
          {d.ban_cu_ly_do}
          {d.quet_lan_cuoi
            ? ` Lần quét gần nhất: ${new Date(d.quet_lan_cuoi).toLocaleString("vi-VN")}.`
            : ""}{" "}
          Số dưới đây là tình trạng của lần quét ấy, không phải của hôm nay.
        </div>
      )}
      {d && !d.ban_cu && d.quet_lan_cuoi && (
        <p className="muted" style={{ marginTop: -2 }}>
          Vòng quét gần nhất: <b>{new Date(d.quet_lan_cuoi).toLocaleString("vi-VN")}</b>
          {" "}({d.quet_cach_day_gio} giờ trước) · lịch tự động 20:30 mỗi ngày.
        </p>
      )}

      {th && (
        <div className="kpis" style={{ marginBottom: 12 }}>
          <div className="kpi" style={{ borderColor: th.con_do ? "var(--red)" : undefined }}>
            <b style={{ color: th.con_do ? "var(--red)" : undefined }}>{th.con_do}</b>
            <span>Việc nghiêm trọng còn tồn</span></div>
          <div className="kpi"><b>{th.con_vang}</b><span>Cần rà soát</span></div>
          <div className="kpi"><b>{th.bao_cao_chua_xem}</b><span>Báo cáo Chủ tịch chưa xem</span></div>
          <div className="kpi"><b>{th.diem_cho_hau_kiem}</b><span>Điểm chờ hậu kiểm</span></div>
        </div>
      )}

      {chayDuoc && (
        <div className="panel">
          <button className="act" disabled={!!dangChay} onClick={() => goi("quet")}>
            {dangChay === "quet" ? "Đang quét…" : "Chạy một vòng quét"}
          </button>
          <button className="act grey" disabled={!!dangChay} onClick={() => goi("cham-diem")}>
            {dangChay === "cham-diem" ? "Đang chấm…" : "Chấm điểm phòng ban kỳ này"}
          </button>
          <div className="muted" style={{ marginTop: 6 }}>
            Vòng quét kiểm: mạch nâng cấp cơ sở dữ liệu · màn hình ẩn khỏi menu mà API còn mở · vai trò
            không mở được màn hình nào · ngoại lệ nghiêm trọng tồn quá 14 ngày · nội dung AI chưa hậu kiểm.
          </div>
        </div>
      )}

      <nav className="tabs" style={{ position: "static", marginBottom: 12 }}>
        {TABS.map(([k, t]) => (
          <a key={k} className={tab === k ? "on" : ""} href="#" onClick={(e) => { e.preventDefault(); setTab(k); }}>{t}</a>
        ))}
      </nav>

      {!d && !loi && <div className="panel muted">Đang tải…</div>}

      {tab === "phat_hien" && d && (
        <>
          {conSong.length === 0 && <div className="gate pass">Vòng quét gần nhất không thấy việc nào còn tồn.</div>}
          {conSong.map((p: any) => (
            <div key={p.id} className="panel"
                 style={{ borderLeft: `4px solid ${p.muc === "do" ? "var(--red)" : "var(--orange)"}` }}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <Tag cls={p.muc === "do" ? "red" : "warn"}>{p.muc_ten}</Tag>
                <b>{p.loai_ten}</b>
                {p.phong_ban && <Tag>{p.phong_ban}</Tag>}
                {p.da_bao_cao && <Tag cls="navy">đã báo cáo Chủ tịch</Tag>}
                <span className="muted" style={{ marginLeft: "auto" }}>
                  thấy lần đầu {fmtDT(p.lan_dau)}{p.so_lan > 1 ? ` · lặp ${p.so_lan} lần` : ""}
                </span>
              </div>
              <div style={{ marginTop: 6 }}>{p.tom_tat}</div>
              {p.chi_tiet && Object.keys(p.chi_tiet).length > 0 && (
                <pre className="mono" style={{ marginTop: 6, whiteSpace: "pre-wrap", color: "var(--ink2)" }}>
                  {JSON.stringify(p.chi_tiet, null, 1)}
                </pre>
              )}
              <div className="muted" style={{ marginTop: 4 }}>
                Việc này cũng hiện ở màn hình <a href="/ngoai-le">Ngoại lệ cần xử lý</a> để phòng ban giải trình.
              </div>
            </div>
          ))}
          {daHet.length > 0 && (
            <div className="panel">
              <h3>Đã hết ({daHet.length})</h3>
              {daHet.map((p: any) => (
                <div key={p.id} className="muted" style={{ padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                  {p.loai_ten} – {p.tom_tat} <i>(lần cuối thấy {fmtDT(p.lan_cuoi)})</i>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "bao_cao" && d && (
        <>
          {(d.bao_cao || []).length === 0 &&
            <div className="gate pass">Chưa có báo cáo nào – nghĩa là chưa có việc nghiêm trọng nào phát sinh.</div>}
          {(d.bao_cao || []).map((b: any) => (
            <div key={b.id} className="panel" style={{ borderLeft: `4px solid ${b.da_xem ? "var(--line)" : "var(--red)"}` }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <Tag cls={b.da_xem ? "ok" : "red"}>{b.da_xem ? `Chủ tịch đã xem (${b.xem_boi})` : "Chưa xem"}</Tag>
                <b>{b.ly_do}</b>
                <span className="muted" style={{ marginLeft: "auto" }}>{fmtDT(b.luc)}</span>
              </div>
              <pre style={{ whiteSpace: "pre-wrap", marginTop: 8, fontFamily: "inherit" }}>{b.noi_dung}</pre>
              {!b.da_xem && laLanhDao &&
                <button className="act teal" onClick={() => goi("da-xem", { bao_cao_id: b.id })}>Đã xem</button>}
            </div>
          ))}
        </>
      )}

      {tab === "diem" && d && (
        <div className="panel">
          <div className="gate">
            Điểm do máy chấm là <b>đề xuất</b>, có hiệu lực sau khi Chủ tịch hậu kiểm. Phòng chưa đủ số
            liệu ghi “chưa đủ cơ sở” chứ không chấm 0 – chưa có số liệu và làm kém là hai chuyện khác nhau.
          </div>
          <div className="wrap">
            <table>
              <thead><tr>
                <th>Kỳ</th><th>Phòng ban</th><th className="num">Điểm</th><th>Căn cứ</th>
                <th>Trạng thái</th><th></th>
              </tr></thead>
              <tbody>
                {(d.diem || []).map((r: any) => (
                  <tr key={r.id}>
                    <td>{r.ky}</td>
                    <td><b>{r.phong_ban}</b></td>
                    <td className="num">{r.du_co_so ? r.diem : <span className="muted">chưa đủ cơ sở</span>}</td>
                    <td style={{ maxWidth: 380 }}>{r.nhan_xet}</td>
                    <td><Tag cls={r.trang_thai === "chap_nhan" ? "ok" : r.trang_thai === "bac" ? "red" : "warn"}>
                      {r.trang_thai === "chap_nhan" ? "Chủ tịch chấp nhận"
                        : r.trang_thai === "bac" ? "Chủ tịch bác" : "Chờ hậu kiểm"}</Tag>
                      {r.hau_kiem_ghi_chu && <div className="muted">{r.hau_kiem_ghi_chu}</div>}</td>
                    <td>{laLanhDao && r.trang_thai === "cho_hau_kiem" && (
                      <>
                        <button className="act teal" onClick={() => goi("hau-kiem-diem", { diem_id: r.id, chap_nhan: true })}>Chấp nhận</button>
                        <button className="act red" onClick={async () => {
                          const g = await nhap("Bác điểm này vì lý do gì?") || "";
                          if (g.trim()) goi("hau-kiem-diem", { diem_id: r.id, chap_nhan: false, ghi_chu: g });
                        }}>Bác</button>
                      </>)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(d.diem || []).length === 0 && <div className="muted">Chưa chấm kỳ nào.</div>}
        </div>
      )}
    </main>
  );
}

// Bọc trong Shell: không bọc thì trang chạy NGOÀI khung – mất thanh điều hướng, và tệ hơn là
// useShell() trả user rỗng nên mọi nút theo vai trò lặng lẽ biến mất mà không báo lỗi gì.
export default function Page() { return <Shell><KiemSoatPage /></Shell>; }
