/* Robot đồng bộ Vietrip → VTOS. Cách dùng: đăng nhập app.vietrip.com.vn (quyền Giám đốc/Kế toán), mở Console (F12), dán toàn bộ file,
   rồi gọi:  await vtosSync({ api: 'https://vtos-api.onrender.com', token: '<JWT VTOS của cntt/ketoan>', from: '2026-06-01', to: '2026-09-30' })
   Chạy lại bao nhiêu lần cũng được – VTOS nạp idempotent theo mã Vietrip. */
async function vtosSync(cfg) {
  const H = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + cfg.token };
  const log = (m) => console.log('[VTOS]', m);
  const push = async (entity, rows) => {
    for (let i = 0; i < rows.length; i += 400) {
      const r = await fetch(`${cfg.api}/api/v1/import/vietrip/${entity}`, { method: 'POST', headers: H, body: JSON.stringify({ rows: rows.slice(i, i + 400) }) });
      if (!r.ok) throw new Error(entity + ' ' + r.status + ' ' + (await r.text()).slice(0, 200));
      log(`${entity}: ${Math.min(i + 400, rows.length)}/${rows.length}`);
    }
  };
  const d2 = (s) => { const [y, m, d] = s.split('-'); return `${d}%2F${m}%2F${y}`; };
  // 1. Users, vehicles
  const users = await (await fetch('/api/users/all')).json(); await push('user', users.data || users);
  const veh = await (await fetch('/api/vehicles/filter?page=1&pageSize=200')).json(); await push('vehicle', veh.data || veh);
  // 2. Tours (mọi tour có ngày khởi hành từ cfg.from)
  let tours = [], page = 1;
  while (true) {
    const j = await (await fetch('/operations/OperationsTour/GetToursData', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tourType: 'All', fromDate: cfg.from, searchKeyword: '', selectedServices: [], page, pageSize: 500 }) })).json();
    tours.push(...(j.data || [])); if (!j.data || j.data.length < 500 || page >= (j.totalPages || 1)) break; page++;
  }
  tours = tours.filter(t => !cfg.to || (t.ngayKhoiHanh || '').slice(0, 10) <= cfg.to);
  await push('tour', tours);
  // 3. Bookings theo ngày đặt
  let bks = [], start = 0;
  while (true) {
    const j = await (await fetch(`/api/booking/search?draw=1&start=${start}&length=1000&showAll=true&bookingDateFrom=${d2(cfg.from)}&bookingDateTo=${d2(cfg.to)}&order[0][column]=0&order[0][dir]=asc`)).json();
    bks.push(...(j.data || [])); start += 1000; if (!j.data || j.data.length < 1000) break;
  }
  await push('booking', bks);
  // 4. Phiếu thu / phiếu chi khách đã xác nhận + chờ xác nhận
  for (const pt of ['PhieuThu', 'PhieuChi']) for (const stt of ['DaXacNhan', 'ChoXacNhan']) {
    let rows = [], s = 0;
    while (true) {
      const p = new URLSearchParams({ draw: '1', start: String(s), length: '1000', 'order[0][column]': '9', 'order[0][dir]': 'asc', paymentType: pt, status: stt, fromDate: cfg.from });
      const j = await (await fetch('/Accounting/PaymentConfirmation/GetPaymentData', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' }, body: p })).json();
      rows.push(...(j.data || []).map(x => ({ ...x, LoaiPhieu: pt }))); s += 1000; if (!j.data || j.data.length < 1000) break;
    }
    rows = rows.filter(x => (x.FstUpdate || '').slice(0, 10) <= cfg.to);
    if (rows.length) await push('receipt', rows);
  }
  // 5. Chi NCC (toàn bộ rồi lọc theo ngày)
  let sp = [], skip = 0;
  while (true) {
    const j = await (await fetch(`/accounting/supplier-payment-confirmation/GetPaymentData?skip=${skip}&take=1000&requireTotalCount=true`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })).json();
    sp.push(...(j.data || [])); skip += 1000; if (!j.data || j.data.length < 1000) break;
  }
  sp = sp.filter(x => x.FstUpdateString >= cfg.from && x.FstUpdateString <= cfg.to);
  await push('supplier_payment', sp);
  // 6. Đề xuất chi
  const pr = await (await fetch('/expense-proposals/approvals/data?start=0&length=1000&draw=1', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })).json();
  await push('proposal', pr.items || pr.data || []);
  // 7. Quyết toán chi tiết từng tour (bảng HTML) – chỉ tour đã kết thúc trong khoảng
  const done = tours.filter(t => (t.ngayKetThuc || '').slice(0, 10) <= new Date().toISOString().slice(0, 10));
  const num = (s) => Number(String(s || '').replace(/[^\d.-]/g, '')) || 0;
  let sets = [];
  for (let i = 0; i < done.length; i++) {
    const t = done[i];
    try {
      const html = await (await fetch(`/tour-settlement/spreadsheet/${t.recID}`)).text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const txt = doc.body.innerText || '';
      const tt = txt.match(/Tổng thu:\s*([\d.,]+)/), tc = txt.match(/Tổng chi:\s*([\d.,]+)/);
      const lines = [...doc.querySelectorAll('table tbody tr')].map(tr => [...tr.querySelectorAll('td')].map(td => td.innerText.trim().replace(/\n+/g, ' | ')))
        .filter(c => c.length >= 10).map(c => ({ mo_ta: c[1], loai: c[2], ncc: c[3], don_gia: num(c[4]), sl: num(c[5]), hs: num(c[6]), thuc_chi: num(c[8]), da_tt: num(c[9]), ghi_chu: c[10] || '' }));
      sets.push({ tourId: t.recID, tourcode: t.tourcode, tong_thu: tt ? num(tt[1]) : 0, tong_chi: tc ? num(tc[1]) : 0, lines });
    } catch (e) { log('lỗi quyết toán ' + t.tourcode + ': ' + e.message); }
    if (sets.length >= 100) { await push('settlement', sets); sets = []; }
    if (i % 50 === 0) log(`quyết toán ${i}/${done.length}`);
  }
  if (sets.length) await push('settlement', sets);
  // 8. Ánh xạ
  const ap = await (await fetch(`${cfg.api}/api/v1/import/vietrip/apply`, { method: 'POST', headers: H })).json();
  log('ÁNH XẠ: ' + JSON.stringify(ap.applied));
  return { users: (users.data || users).length, tours: tours.length, bookings: bks.length, supplier_payments: sp.length, settlements: done.length, applied: ap.applied };
}
