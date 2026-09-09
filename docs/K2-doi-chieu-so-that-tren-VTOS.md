# K2 – đối chiếu bằng SỐ THẬT trên VTOS, không bằng dữ liệu ví dụ

Ngày 09/9/2026.

## Vì sao cần cái này

115 tệp phép thử của VTOS chạy trên **dữ liệu ví dụ** do chính phép thử dựng ra. Xanh hết chỉ chứng
minh mã không vỡ trên những tình huống mà người viết phép thử **nghĩ ra được**. Đợt K2 sửa 275 chỗ đọc
+ 142 chỗ đọc qua khoá + 12 câu SQL trên khắp sổ kế toán, đội xe, tài sản, công nợ – đủ rộng để một
lỗi nhỏ vẫn lọt qua toàn bộ phép thử mà làm sai một con số trên báo cáo thật.

Nên trước khi triển khai, chụp lại **số thật đang chạy** làm mốc; sau khi triển khai, chụp lại lần nữa
và so. Bất kỳ chênh lệch nào cũng là một câu hỏi phải trả lời được, không phải chuyện "chắc do làm tròn".

## Cách chụp

Chạy trong **trang VTOS đã đăng nhập** (F12 → Console). Mã gọi API bằng phiên đăng nhập sẵn có của
người đang mở máy; **không** chép mã thông báo (token) ra ngoài trình duyệt.

```js
const H = { Authorization: "Bearer " + localStorage.getItem("vtos_token") };
const A = "since=2026-01-01&upto=2026-12-31";
const duong = [
  ["can_doi_tai_khoan", "/api/v1/books/can-doi-tai-khoan?" + A + "&non_zero=false"],
  ["nhat_ky_chung",     "/api/v1/books/nhat-ky-chung?" + A + "&limit=5000"],
  ["so_quy",            "/api/v1/books/so-quy?" + A + "&limit=5000"],
  ["so_tien_gui",       "/api/v1/books/so-tien-gui?" + A + "&limit=5000"],
  ["nhat_ky_tien_thu",  "/api/v1/books/nhat-ky-tien?" + A + "&direction=thu&limit=5000"],
  ["nhat_ky_tien_chi",  "/api/v1/books/nhat-ky-tien?" + A + "&direction=chi&limit=5000"],
  ["cong_no_131",       "/api/v1/books/cong-no-tong-hop?account=131&" + A],
  ["cong_no_331",       "/api/v1/books/cong-no-tong-hop?account=331&" + A],
  ["so_cai_111",        "/api/v1/books/so-cai?account=111&" + A + "&limit=5000"],
  ["so_cai_112",        "/api/v1/books/so-cai?account=112&" + A + "&limit=5000"],
  ["so_cai_131",        "/api/v1/books/so-cai?account=131&" + A + "&limit=5000"],
  ["so_cai_331",        "/api/v1/books/so-cai?account=331&" + A + "&limit=5000"],
  ["tours",             "/api/v1/tours?limit=2000"],
  ["dashboard",         "/api/v1/dashboard"],
];

// Thu gọn mỗi phản hồi thành một "dấu vân tay": mọi số trong cây JSON được cộng dồn theo TÊN KHOÁ.
// Ô rỗng đếm riêng – đó chính là thứ K2 đang mở đường cho, nên phải nhìn thấy nó tăng.
function vet(x, ra, duong) {
  if (x === null || x === undefined) { ra.__rong = (ra.__rong || 0) + 1; return; }
  if (typeof x === "number") { ra[duong] = Math.round(((ra[duong] || 0) + x) * 100) / 100; return; }
  if (Array.isArray(x)) { ra.__dong = (ra.__dong || 0) + x.length; for (const p of x) vet(p, ra, duong); return; }
  if (typeof x === "object") for (const [k, v] of Object.entries(x)) vet(v, ra, duong ? duong + "." + k : k);
}

window.__snap = { xong: 0, tong: duong.length, ra: {} };
(async () => {
  for (const [ten, u] of duong) {
    try { const r = await fetch(u, { headers: H }); window.__snap.ra[ten] = { http: r.status, j: await r.json() }; }
    catch (e) { window.__snap.ra[ten] = { loi: String(e) }; }
    window.__snap.xong++;
  }
  const vt = {};
  for (const [ten, v] of Object.entries(window.__snap.ra)) { const ra = {}; if (v.j) vet(v.j, ra, ""); vt[ten] = ra; }
  window.__vantay = vt;
  localStorage.setItem("k2_moc_truoc", JSON.stringify({ luc: new Date().toISOString(), van_tay: vt }));
  console.log("xong", Object.keys(vt).length, "phân hệ");
})();
```

Lần chụp đầu mất khoảng một phút vì máy chủ Render gói miễn phí ngủ khi không ai dùng.

## Cách so sau khi triển khai

```js
const truoc = JSON.parse(localStorage.getItem("k2_moc_truoc")).van_tay;
// ... chạy lại đoạn chụp ở trên (nó ghi đè window.__vantay) ...
const sau = window.__vantay, lech = {};
for (const k of new Set([...Object.keys(truoc), ...Object.keys(sau)])) {
  const a = truoc[k] || {}, b = sau[k] || {};
  for (const c of new Set([...Object.keys(a), ...Object.keys(b)]))
    if (a[c] !== b[c]) (lech[k] = lech[k] || {})[c] = { truoc: a[c], sau: b[c] };
}
lech;
```

## Kỳ vọng, và vì sao

**Mọi con số tiền phải GIỮ NGUYÊN.** Bản nâng cấp K2 chỉ nới ràng buộc, không sửa một dòng dữ liệu nào;
những giá trị đang có đều khác rỗng, mà `or 0` và `coalesce(x, 0)` đặt lên một giá trị khác rỗng thì
không đổi gì cả. Một con số lệch sau khi triển khai KHÔNG phải sai số làm tròn – nó là một chỗ gia cố
đặt sai, và phải tìm ra chỗ ấy trước khi đi tiếp.

**`__rong` được phép tăng, và chỉ tăng ở dòng nhập MỚI.** Đó chính là điều K2 làm ra: từ nay ô để trống
lưu thành rỗng. Nếu `__rong` tăng ở dữ liệu CŨ thì ngược lại: có gì đó vừa xoá số, phải dừng ngay.

## Mốc chụp lúc 09/9/2026 17:50 UTC (TRƯỚC khi triển khai K2)

14 phân hệ, khoảng 34.000 dòng. Vài con số neo để đối chiếu nhanh bằng mắt:

| Phân hệ | Số neo | Giá trị |
|---|---|---|
| Cân đối tài khoản | `total.debit` | 3.794.634.251.045 |
| Nhật ký chung | `total.debit` = `total.credit` | 3.794.634.251.045 |
| Nhật ký tiền thu | `total` | 377.517.680.454 |
| Nhật ký tiền chi | `total` | 381.461.124.357 |
| Công nợ 131 | `total.credit` | 389.685.182.261 |
| Công nợ 331 | `total.credit` | 828.790.375.389 |
| Sổ tiền gửi | `total.in` / `total.out` | 332.067.158.742 / 335.109.747.733 |
| Bảng điều khiển | `kpis.phai_thu` | 11.168.129.558 |
| Bảng điều khiển | `kpis.no_vay` | 19.756.699.501 |

Bản đầy đủ nằm trong `localStorage["k2_moc_truoc"]` trên máy đã chụp.

**Một điều đọc được ngay từ mốc này:** `__rong = 0` ở cả 13 phân hệ sổ sách. Nghĩa là dữ liệu thật hiện
nay **không có ô tiền nào rỗng** – nên về nguyên tắc K2 không thể làm đổi một con số nào đang có. Rủi ro
của đợt này nằm ở dữ liệu nhập TỪ NAY TRỞ ĐI, không nằm ở sổ sách đã có. Phép so sau khi triển khai là
để kiểm chứng câu đó bằng số, chứ không phải để tin nó.
