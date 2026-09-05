/* Robot đồng bộ Vietrip → VTOS. Cách dùng: đăng nhập app.vietrip.com.vn (quyền Giám đốc/Kế toán), mở Console (F12), dán toàn bộ file,
   rồi gọi:  await vtosSync({ api: 'https://vtos-api.onrender.com', token: '<JWT VTOS của cntt/ketoan>', from: '2026-06-01', to: '2026-09-30' })
   Chạy lại bao nhiêu lần cũng được – VTOS nạp idempotent theo mã Vietrip.
   Ghi chú kỹ thuật (đo thực tế 9/2026):
   - GetPaymentData (phiếu thu/chi khách) chỉ có fromDate, không có toDate; tham số start bị máy chủ giới hạn (~≤1100) nhưng length không giới hạn
     → lấy 1 lần với length lớn rồi lọc theo ngày ở client.
   - Bảng quyết toán (/tour-settlement/spreadsheet/{id}) tải ~10 giây/tour → quét song song 6 luồng.
   - Tour khởi hành sau `to` vẫn được nạp để booking/phiếu thu đặt trong kỳ có tour tham chiếu. */
window.vtosSync = async function vtosSync(cfg) {
  const H = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + cfg.token };
  const log = (m) => console.log('[VTOS]', m);
  const sleep = (ms) => new Promise(z => setTimeout(z, ms));
  const push = async (entity, rows) => {
    for (let i = 0; i < rows.length; i += 400) {
      let r = null;
      for (let k = 0; k < 4; k++) {
        try { r = await fetch(`${cfg.api}/api/v1/import/vietrip/${entity}`, { method: 'POST', headers: H, body: JSON.stringify({ rows: rows.slice(i, i + 400) }) }); if (r.ok) break; } catch (e) { r = null; }
        await sleep(5000);
      }
      if (!r || !r.ok) throw new Error(entity + ' lỗi sau 4 lần: ' + (r ? r.status + ' ' + (await r.text()).slice(0, 200) : 'fetch'));
      log(`${entity}: ${Math.min(i + 400, rows.length)}/${rows.length}`);
    }
  };
  const d2 = (s) => { const [y, m, d] = s.split('-'); return `${d}%2F${m}%2F${y}`; };
  // 1. Users, vehicles
  const users = await (await fetch('/api/users/all')).json(); await push('user', users.data || users);
  const veh = await (await fetch('/api/vehicles/filter?page=1&pageSize=200')).json(); await push('vehicle', veh.data || veh);
  // 2. Tours: mọi tour có ngày khởi hành từ cfg.from (kể cả sau cfg.to – để booking trong kỳ có tour tham chiếu)
  let tours = [], page = 1;
  while (true) {
    const j = await (await fetch('/operations/OperationsTour/GetToursData', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tourType: 'All', fromDate: cfg.from, searchKeyword: '', selectedServices: [], page, pageSize: 500 }) })).json();
    tours.push(...(j.data || [])); if (!j.data || j.data.length < 500 || page >= (j.totalPages || 1)) break; page++;
  }
  await push('tour', tours);
  const inRange = tours.filter(t => !cfg.to || (t.ngayKhoiHanh || '').slice(0, 10) <= cfg.to);
  // 3. Bookings theo ngày đặt
  let bks = [], start = 0;
  while (true) {
    const j = await (await fetch(`/api/booking/search?draw=1&start=${start}&length=1000&showAll=true&bookingDateFrom=${d2(cfg.from)}&bookingDateTo=${d2(cfg.to)}&order[0][column]=0&order[0][dir]=asc`)).json();
    bks.push(...(j.data || [])); start += 1000; if (!j.data || j.data.length < 1000) break;
  }
  await push('booking', bks);
  // 4. Phiếu thu / phiếu chi khách (đã xác nhận + chờ xác nhận) – 1 lần/loại với length lớn (start bị giới hạn phía máy chủ)
  let nrec = 0;
  for (const pt of ['PhieuThu', 'PhieuChi']) for (const stt of ['DaXacNhan', 'ChoXacNhan']) {
    const p = new URLSearchParams({ draw: '1', start: '0', length: '20000', 'order[0][column]': '9', 'order[0][dir]': 'desc', paymentType: pt, status: stt, fromDate: cfg.from });
    let j = null;
    for (let k = 0; k < 4; k++) {
      try { j = await (await fetch('/Accounting/PaymentConfirmation/GetPaymentData', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' }, body: p })).json(); } catch (e) { j = null; }
      if (j && j.data && j.data.length >= (j.recordsFiltered || 0)) break; await sleep(4000);
    }
    const rows = ((j && j.data) || []).map(x => ({ ...x, LoaiPhieu: pt })).filter(x => (x.FstUpdate || '').slice(0, 10) <= cfg.to);
    log(`${pt}/${stt}: ${rows.length}/${j ? j.recordsFiltered : '?'}`); nrec += rows.length;
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
  // 7. Quyết toán chi tiết từng tour đã kết thúc (bảng HTML) – quét song song
  const today = new Date().toISOString().slice(0, 10);
  const done = inRange.filter(t => (t.ngayKetThuc || '').slice(0, 10) <= today);
  const num = (s) => Number(String(s || '').replace(/[^\d.-]/g, '')) || 0;
  let idx = 0, sets = [], nset = 0;
  const flush = async () => { const b = sets; sets = []; if (b.length) { await push('settlement', b); nset += b.length; } };
  const worker = async () => {
    while (idx < done.length) {
      const t = done[idx++];
      try {
        const html = await (await fetch(`/tour-settlement/spreadsheet/${t.recID}`)).text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const txt = doc.body.textContent || '';
        const tt = txt.match(/Tổng thu:\s*([\d.,]+)/), tc = txt.match(/Tổng chi:\s*([\d.,]+)/);
        const lines = [...doc.querySelectorAll('table tbody tr')].map(tr => [...tr.querySelectorAll('td')].map(td => (td.textContent || '').trim().replace(/\s*\n+\s*/g, ' | ')))
          .filter(c => c.length >= 10).map(c => ({ mo_ta: c[1], loai: c[2], ncc: c[3], don_gia: num(c[4]), sl: num(c[5]), hs: num(c[6]), thuc_chi: num(c[8]), da_tt: num(c[9]), ghi_chu: c[10] || '' }));
        sets.push({ tourId: t.recID, tourcode: t.tourcode, tong_thu: tt ? num(tt[1]) : 0, tong_chi: tc ? num(tc[1]) : 0, lines });
      } catch (e) { log('lỗi quyết toán ' + t.tourcode + ': ' + e.message); }
      if (sets.length >= 50) await flush();
      if (idx % 50 === 0) log(`quyết toán ${idx}/${done.length}`);
    }
  };
  await Promise.all(Array.from({ length: cfg.parallel || 6 }, worker));
  await flush();
  // 8. Ánh xạ theo lô tới khi hết
  let ap = null, total = {}, guard = 0;
  do {
    let r = null;
    try { r = await fetch(`${cfg.api}/api/v1/import/vietrip/apply`, { method: 'POST', headers: H }); } catch (e) { }
    if (!r || !r.ok) { log('apply ' + (r ? r.status : 'lỗi mạng') + ', thử lại'); await sleep(5000); if (++guard > 300) break; continue; }
    ap = await r.json();
    for (const [k, v] of Object.entries(ap.applied)) total[k] = (total[k] || 0) + (typeof v === 'number' && !['remaining', 'blocked'].includes(k) ? v : 0);
    log(`ánh xạ lô ${++guard}: còn ${ap.applied.remaining}, chờ tour/booking: ${ap.applied.blocked}`);
  } while ((!ap || ap.applied.remaining > 0) && guard < 300);
  log('ÁNH XẠ XONG: ' + JSON.stringify(total));
  return { users: (users.data || users).length, vehicles: (veh.data || veh).length, tours: tours.length, bookings: bks.length, receipts: nrec, supplier_payments: sp.length, proposals: (pr.items || pr.data || []).length, settlements: nset, applied: total, blocked: ap ? ap.applied.blocked : null };
};
