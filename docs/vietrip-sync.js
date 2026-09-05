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
  // 2b. Sản phẩm tour (tour cha): danh sách /Product/Search + chi tiết /product/edit/{id} (song song 6 luồng)
  if (cfg.products !== false) {
    const ph = await (await fetch('/Product/Search?search=&page=1&pageSize=1000')).text();
    const pd = new DOMParser().parseFromString(ph, 'text/html');
    const plist = [...pd.querySelectorAll('tbody tr')].map(tr => { const c = [...tr.querySelectorAll('td')].map(td => td.textContent.trim().replace(/\s+/g, ' ')); const a = tr.querySelector('a[href*="/product/edit/"]'); return { id: a ? Number(a.getAttribute('href').split('/').pop()) : 0, code: c[0], services: c[2], status: c[6] }; }).filter(x => x.id);
    let pi = 0, prods = [];
    const pworker = async () => { while (pi < plist.length) { const it = plist[pi++]; try {
      const h = await (await fetch('/product/edit/' + it.id)).text(); const d = new DOMParser().parseFromString(h, 'text/html'); const f = {};
      for (const e of d.querySelectorAll('input[name],select[name],textarea[name]')) { const n = e.name; if (n in f) continue; if (e.type === 'checkbox') f[n] = e.checked; else if (e.tagName === 'SELECT') f[n] = (e.querySelector('option[selected]') || e.selectedOptions[0] || {}).textContent?.trim() || ''; else f[n] = e.value; }
      const lines = [...d.querySelectorAll('table tbody tr')].map(tr => [...tr.querySelectorAll('td')]).filter(tds => tds.some(td => td.querySelector('select[name=costLoaiDichVu], input[name=costMoTa]'))).map(tds => { const g = (sel) => { const e = tds.map(td => td.querySelector(sel)).find(Boolean); return e ? (e.tagName === 'SELECT' ? (e.selectedOptions[0]?.textContent || '').trim() : e.value) : ''; }; return { loai: g('select[name=costLoaiDichVu]'), ncc: g('input[name=costNCC],select[name=costNCC]'), kind: g('input[name=costLoaiTinhChi1]:checked') || (tds.map(td => td.querySelector('input[name=costLoaiTinhChi1]:checked')).find(Boolean)?.value || 'Fixed'), mo_ta: g('input[name=costMoTa]'), don_gia: g('input[name=costDonGiaBan3]'), sl: g('input[name=costSoLuong]'), so_tien: g('input[name=costSoTien3]') }; }).filter(l => l.mo_ta || l.don_gia);
      const priceEl = d.querySelector('[name=PriceInfo]'); const tmp = document.createElement('div'); tmp.innerHTML = priceEl ? priceEl.value : ''; const priceText = (tmp.innerText || tmp.textContent || '').replace(/\n{3,}/g, '\n\n').trim().slice(0, 20000);
      const nvdhOpt = d.querySelector('select[name=NVDH] option[selected]');
      prods.push({ id: it.id, services: it.services, status: it.status, ProductCode: f.ProductCode, ProductName: f.ProductName, DeparturePoint: f.DeparturePoint, TourType: f.TourType, Region: f.Region, Country: f.Country, SalePoint: f.SalePoint, Transportation: f.Transportation, VehicleType: f.VehicleType, TourLength: f.TourLength, Duration: f.Duration, ReferencePrice: f.ReferencePrice, DepositPercentage: f.DepositPercentage, DaysToCloseTour: f.DaysToCloseTour, RequiresConfirmation: f.RequiresConfirmation,
        Flight: f.Flight, Land: f.Land, LSQFee: f.LSQFee, Insurance: f.Insurance, Gift: f.Gift, TLFee: f.TLFee, GroupMeeting: f.GroupMeeting, Operating: f.Operating, Translation: f.Translation, TicketCommission: f.TicketCommission, CKFee: f.CKFee, OtherCost: f.OtherCost, cost_lines: lines, PriceInfoText: priceText, NVDH_name: nvdhOpt ? nvdhOpt.textContent.trim() : '' });
    } catch (e) { log('lỗi sản phẩm ' + it.code + ': ' + e.message); } } };
    await Promise.all(Array.from({ length: 6 }, pworker));
    await push('product', prods); log('sản phẩm: ' + prods.length + '/' + plist.length);
  }
  // 3. Bookings theo ngày đặt
  let bks = [], start = 0;
  while (true) {
    const j = await (await fetch(`/api/booking/search?draw=1&start=${start}&length=1000&showAll=true&bookingDateFrom=${d2(cfg.from)}&bookingDateTo=${d2(cfg.to)}&order[0][column]=0&order[0][dir]=asc`)).json();
    bks.push(...(j.data || [])); start += 1000; if (!j.data || j.data.length < 1000) break;
  }
  await push('booking', bks);
  // 4. Phiếu thu / phiếu chi khách: danh sách (máy chủ chỉ trả được ~3.000 dòng mới nhất: start ≤ ~1.100, length ≤ ~2.000)
  let nrec = 0; const seenRec = new Set();
  const getPay = async (pt, stt, st, len) => { const p = new URLSearchParams({ draw: '1', start: String(st), length: String(len), 'order[0][column]': '9', 'order[0][dir]': 'desc', paymentType: pt, status: stt, fromDate: cfg.from });
    for (let k = 0; k < 3; k++) { try { const j = await (await fetch('/Accounting/PaymentConfirmation/GetPaymentData', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' }, body: p })).json(); if (j && j.data) return j; } catch (e) { } await sleep(4000); } return null; };
  for (const pt of ['PhieuThu', 'PhieuChi']) for (const stt of ['DaXacNhan', 'ChoXacNhan']) {
    let rows = [];
    for (const [st, len] of [[0, 1200], [1100, 2000]]) { const j = await getPay(pt, stt, st, len); if (!j) continue; for (const x of j.data) { if (!seenRec.has(String(x.RecID))) { seenRec.add(String(x.RecID)); rows.push({ ...x, LoaiPhieu: pt }); } } if (rows.length >= (j.recordsFiltered || 0)) break; }
    rows = rows.filter(x => (x.FstUpdate || '').slice(0, 10) <= cfg.to); nrec += rows.length; log(`${pt}/${stt}: ${rows.length}`);
    if (rows.length) await push('receipt', rows);
  }
  // 4b. Bổ sung phiếu thu theo từng booking trong kỳ (API /api/bookings/{id}/payments) – bù phần danh sách không trả được
  if (cfg.scanBookings !== false) {
    let bi = 0, rows = [];
    const bworker = async () => { while (bi < bks.length) { const b = bks[bi++]; let j = null; for (let k = 0; k < 2; k++) { try { j = await (await fetch('/api/bookings/' + b.recID + '/payments')).json(); if (j && j.data) break; } catch (e) { } await sleep(1500); }
      if (!j || !j.data) continue; for (const pm of j.data) { if (seenRec.has(String(pm.id))) continue; seenRec.add(String(pm.id)); rows.push({ RecID: String(pm.id), Tourcode: b.tourcode, TenNguoiBook: b.tenNguoiBook, BookingID: String(b.recID), SoTien: pm.soTien, NguoiThanhToan: pm.nguoiThanhToan, HinhThuc: pm.hinhThuc, TaiKhoanCongTy: pm.taiKhoanCongTy, GhiChu: pm.ghiChu || '', FstUser: '', FstUpdate: pm.fstUpdate, Status: pm.status, LoaiPhieu: (pm.soTien || 0) < 0 ? 'PhieuChi' : 'PhieuThu' }); }
      if (bi % 250 === 0) log('quét phiếu thu theo booking ' + bi + '/' + bks.length + ' → ' + rows.length); } };
    await Promise.all(Array.from({ length: 6 }, bworker));
    rows = rows.filter(x => (x.FstUpdate || '').slice(0, 10) <= cfg.to); nrec += rows.length;
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
        // quy trình & lịch sử (bước hiện tại + các mốc: tiêu đề / người / thời gian / ghi chú)
        const stepEl = [...doc.querySelectorAll('h5,h6,strong,b,div')].find(e => /^Bước\s*\d/.test((e.textContent || '').trim()));
        const hist = []; const hb = [...doc.querySelectorAll('h3,h4,h5')].find(e => /Lịch sử hoạt động/.test(e.textContent || ''));
        if (hb) { let box = hb.parentElement; for (let k = 0; k < 4 && box && box.children.length < 3; k++) box = box.parentElement;
          const items = box ? [...box.querySelectorAll('.timeline-item, .d-flex, li')].filter(it => /\d{2}\/\d{2}\/\d{4}/.test(it.textContent || '')) : [];
          for (const it of items.slice(0, 60)) { const tx = (it.innerText || it.textContent || '').split('\n').map(x => x.trim()).filter(Boolean); if (tx.length < 2) continue;
            const m = tx.find(x => /^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}/.test(x)) || ''; const mm = m.match(/(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})\s*-\s*(.*)$/);
            const rec = { title: tx[0].slice(0, 200), at: mm ? `${mm[3]}-${mm[2]}-${mm[1]}T${mm[4]}:${mm[5]}:00` : '', actor: mm ? mm[6].trim() : '', note: tx.filter(x => x !== tx[0] && x !== m).join(' ').slice(0, 1000) };
            if (!hist.some(h => h.title === rec.title && h.at === rec.at)) hist.push(rec); } }
        sets.push({ tourId: t.recID, tourcode: t.tourcode, tong_thu: tt ? num(tt[1]) : 0, tong_chi: tc ? num(tc[1]) : 0, lines, step: stepEl ? stepEl.textContent.trim().slice(0, 80) : '', history: hist });
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
  return { users: (users.data || users).length, vehicles: (veh.data || veh).length, tours: tours.length, products: cfg.products === false ? 0 : undefined, bookings: bks.length, receipts: nrec, supplier_payments: sp.length, proposals: (pr.items || pr.data || []).length, settlements: nset, applied: total, blocked: ap ? ap.applied.blocked : null };
};
