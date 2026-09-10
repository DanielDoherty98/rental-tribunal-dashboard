/* UK Rental Tribunal Decisions - dashboard
   Every chart is built from the same filtered array (VIEW), so adding a new one
   is a copy of the pattern inside renderCharts().

   V5.2: rows flagged `needs_review` are hidden by default so a suspect parse
   never silently skews the medians. Untick the filter to inspect them. */

let RAW = [], VIEW = [], PAGE = 0, SORT = {k:'decision_date', dir:-1};
const PER = 50, CHARTS = {};
let MAP = null, LAYER = null;

const $ = s => document.querySelector(s);
const num = v => (v === null || v === undefined || isNaN(v)) ? null : +v;
const gbp = v => v === null ? '' : '£' + (+v).toLocaleString('en-GB',
  {minimumFractionDigits:0, maximumFractionDigits:0});
const pct = v => v === null ? '' : (+v).toFixed(1) + '%';

const median = a => {
  const x = a.filter(v => v !== null && !isNaN(v)).sort((p,q) => p-q);
  if (!x.length) return null;
  const m = Math.floor(x.length/2);
  return x.length % 2 ? x[m] : (x[m-1] + x[m]) / 2;
};

/* ---------------------------------------------------------------- load */
fetch('data/decisions.json?v=' + Date.now())
  .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
  .then(d => {
    RAW = d.rows || [];
    const flagged = RAW.filter(r => r.needs_review === 'Yes').length;
    $('#generated').textContent =
      `${(d.count||0).toLocaleString('en-GB')} decisions · v${d.model_version||''} · ` +
      `refreshed ${String(d.generated_at).slice(0,10)}` +
      (flagged ? ` · ${flagged} need review` : '');
    $('#convMethod').textContent = d.conversion_method || '';
    buildFilters();
    apply();
  })
  .catch(e => {
    $('#generated').textContent = 'Could not load data/decisions.json';
    console.error(e);
  });

/* ---------------------------------------------------------------- filters */
function options(sel, values){
  const el = $(sel);
  [...new Set(values.filter(Boolean))].sort().forEach(v => {
    const o = document.createElement('option'); o.value = v; o.textContent = v; el.append(o);
  });
}
function buildFilters(){
  options('#fCity', RAW.map(r => r.city));
  options('#fRegion', RAW.map(r => r.region));
  options('#fOutcome', RAW.map(r => r.outcome_category));
  options('#fRra', RAW.map(r => r.rra_status));
  options('#fYear', RAW.map(r => r.decision_year && String(r.decision_year)));
  options('#fConf', RAW.map(r => r.parse_confidence));
  ['#fSearch','#fCity','#fRegion','#fOutcome','#fRra','#fYear','#fConf',
   '#fDetermined','#fClean']
    .forEach(s => $(s).addEventListener('input', () => { PAGE = 0; apply(); }));
  $('#resetBtn').onclick = () => {
    ['#fCity','#fRegion','#fOutcome','#fRra','#fYear','#fConf'].forEach(s => $(s).value = '');
    $('#fSearch').value = ''; $('#fDetermined').checked = false;
    $('#fClean').checked = true; PAGE = 0; apply();
  };
  $('#prev').onclick = () => { if (PAGE > 0) { PAGE--; renderTable(); } };
  $('#next').onclick = () => { if ((PAGE+1)*PER < VIEW.length) { PAGE++; renderTable(); } };
  $('#exportBtn').onclick = exportCsv;
  document.querySelectorAll('#tbl th[data-k]').forEach(th => th.onclick = () => {
    const k = th.dataset.k;
    SORT = {k, dir: SORT.k === k ? -SORT.dir : 1};
    renderTable();
  });
}

function apply(){
  const q = $('#fSearch').value.toLowerCase().trim();
  const f = {city:$('#fCity').value, region:$('#fRegion').value,
             outcome_category:$('#fOutcome').value, rra_status:$('#fRra').value,
             parse_confidence:$('#fConf').value};
  const yr = $('#fYear').value;
  const detOnly = $('#fDetermined').checked;
  const cleanOnly = $('#fClean').checked;

  VIEW = RAW.filter(r => {
    for (const k in f) if (f[k] && r[k] !== f[k]) return false;
    if (yr && String(r.decision_year) !== yr) return false;
    if (detOnly && num(r.determined_rent_monthly) === null) return false;
    if (cleanOnly && r.needs_review === 'Yes') return false;
    if (q){
      const hay = [r.property, r.landlord_representative, r.case_reference, r.postcode]
        .join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  renderTable();
  try { renderKpis(); } catch (e) { console.error(e); }
  try { renderCharts(); } catch (e) { console.error(e); }
  try { renderMap(); } catch (e) { console.error(e); }
}

/* ---------------------------------------------------------------- KPIs */
function renderKpis(){
  const det = VIEW.map(r => num(r.determined_rent_monthly)).filter(v => v !== null);
  const cards = [
    ['Decisions', VIEW.length.toLocaleString('en-GB')],
    ['With a determined rent', det.length.toLocaleString('en-GB')],
    ['Median original', gbp(median(VIEW.map(r => num(r.original_rent_monthly))))],
    ['Median sought', gbp(median(VIEW.map(r => num(r.rent_sought_monthly))))],
    ['Median determined', gbp(median(det))],
    ['Median uplift sought', pct(median(VIEW.map(r => num(r.uplift_sought_pct))))],
    ['Median uplift determined', pct(median(VIEW.map(r => num(r.uplift_determined_pct))))],
    ['Determined vs ask', pct(median(VIEW.map(r => num(r.determined_vs_sought_pct))))],
  ];
  $('#kpis').innerHTML = cards.map(([l,v]) =>
    `<div class="kpi"><div class="v">${v || '–'}</div><div class="l">${l}</div></div>`).join('');
}

/* ---------------------------------------------------------------- charts */
const PALETTE = ['#1d4ed8','#0f766e','#b45309','#7c3aed','#be123c','#0891b2'];

function draw(id, cfg){
  if (CHARTS[id]) CHARTS[id].destroy();
  CHARTS[id] = new Chart($('#' + id), cfg);
}
const baseOpts = {responsive:true, maintainAspectRatio:false,
  plugins:{legend:{labels:{boxWidth:12, font:{size:11}}}},
  scales:{x:{ticks:{font:{size:10}}}, y:{ticks:{font:{size:10}}}}};

function groupBy(rows, key){
  const m = new Map();
  rows.forEach(r => { const k = r[key]; if (!k) return;
    if (!m.has(k)) m.set(k, []); m.get(k).push(r); });
  return m;
}

function renderCharts(){
  const byMonth = [...groupBy(VIEW, 'decision_month')].sort((a,b) => a[0] < b[0] ? -1 : 1);
  draw('chTime', {type:'line', data:{labels:byMonth.map(m => m[0]), datasets:[
      {label:'Decisions', data:byMonth.map(m => m[1].length), borderColor:PALETTE[0],
       backgroundColor:'rgba(29,78,216,.12)', fill:true, tension:.3, pointRadius:0, yAxisID:'y'},
      {label:'Median determined pcm', data:byMonth.map(m =>
         median(m[1].map(r => num(r.determined_rent_monthly)))),
       borderColor:PALETTE[1], tension:.3, pointRadius:0, yAxisID:'y1'}]},
    options:{...baseOpts, scales:{...baseOpts.scales,
      y:{position:'left', title:{display:true, text:'Decisions'}},
      y1:{position:'right', grid:{drawOnChartArea:false}, title:{display:true, text:'£ pcm'}}}}});

  const byOut = [...groupBy(VIEW, 'outcome_category')].sort((a,b) => b[1].length - a[1].length);
  draw('chOutcome', {type:'doughnut',
    data:{labels:byOut.map(o => o[0]), datasets:[{data:byOut.map(o => o[1].length),
      backgroundColor:PALETTE}]},
    options:{responsive:true, maintainAspectRatio:false,
      plugins:{legend:{position:'right', labels:{boxWidth:12, font:{size:11}}}}}});

  const cities = [...groupBy(VIEW, 'city')].sort((a,b) => b[1].length - a[1].length).slice(0,15);
  draw('chCity', {type:'bar', data:{labels:cities.map(c => c[0]), datasets:[
      {label:'Original', data:cities.map(c => median(c[1].map(r => num(r.original_rent_monthly)))), backgroundColor:PALETTE[2]},
      {label:'Sought', data:cities.map(c => median(c[1].map(r => num(r.rent_sought_monthly)))), backgroundColor:PALETTE[0]},
      {label:'Determined', data:cities.map(c => median(c[1].map(r => num(r.determined_rent_monthly)))), backgroundColor:PALETTE[1]}]},
    options:baseOpts});

  draw('chUplift', {type:'bar', data:{labels:cities.map(c => c[0]), datasets:[
      {label:'Uplift sought %', data:cities.map(c => median(c[1].map(r => num(r.uplift_sought_pct)))), backgroundColor:PALETTE[0]},
      {label:'Uplift determined %', data:cities.map(c => median(c[1].map(r => num(r.uplift_determined_pct)))), backgroundColor:PALETTE[1]}]},
    options:baseOpts});

  const vals = VIEW.map(r => num(r.determined_rent_monthly)).filter(v => v !== null);
  const bins = new Map(), size = 200;
  const max = vals.length ? Math.min(Math.max(...vals), 4000) : 200;
  vals.forEach(v => { const b = Math.min(Math.floor(v/size)*size, max);
    bins.set(b, (bins.get(b)||0)+1); });
  const keys = [...bins.keys()].sort((a,b) => a-b);
  draw('chDist', {type:'bar',
    data:{labels:keys.map(k => `${gbp(k)}–${gbp(k+size)}`),
      datasets:[{label:'Decisions', data:keys.map(k => bins.get(k)), backgroundColor:PALETTE[3]}]},
    options:baseOpts});

  const rra = ['Pre-RRA','Post-RRA'].map(s => VIEW.filter(r => r.rra_status === s));
  draw('chRra', {type:'bar', data:{labels:['Pre-RRA','Post-RRA'], datasets:[
      {label:'Median uplift sought %', data:rra.map(g => median(g.map(r => num(r.uplift_sought_pct)))), backgroundColor:PALETTE[0]},
      {label:'Median uplift determined %', data:rra.map(g => median(g.map(r => num(r.uplift_determined_pct)))), backgroundColor:PALETTE[1]},
      {label:'Median determined vs ask %', data:rra.map(g => median(g.map(r => num(r.determined_vs_sought_pct)))), backgroundColor:PALETTE[4]}]},
    options:baseOpts});
}

/* ---------------------------------------------------------------- map */
function renderMap(){
  if (!MAP){
    MAP = L.map('map').setView([53.2, -1.6], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {attribution:'&copy; OpenStreetMap contributors', maxZoom:12}).addTo(MAP);
  }
  if (LAYER) MAP.removeLayer(LAYER);
  LAYER = L.layerGroup().addTo(MAP);

  const groups = [...groupBy(VIEW.filter(r => r.lat && r.lon), 'city')];
  if (!groups.length) return;
  const meds = groups.map(g => median(g[1].map(r => num(r.determined_rent_monthly))) || 0);
  const lo = Math.min(...meds.filter(Boolean), 400), hi = Math.max(...meds, 1200);

  groups.forEach(([city, rows]) => {
    const med = median(rows.map(r => num(r.determined_rent_monthly)));
    const t = med ? Math.max(0, Math.min(1, (med - lo) / (hi - lo || 1))) : 0;
    const colour = `hsl(${200 - 200*t}, 72%, ${med ? 45 : 70}%)`;
    L.circleMarker([rows[0].lat, rows[0].lon], {
      radius: Math.max(6, Math.min(30, Math.sqrt(rows.length) * 3.2)),
      color:'#fff', weight:1.5, fillColor:colour, fillOpacity:.78
    }).bindPopup(
      `<strong>${city}</strong><br>${rows.length} decisions` +
      `<br>Median determined: ${med ? gbp(med) : 'n/a'}` +
      `<br>Median sought: ${gbp(median(rows.map(r => num(r.rent_sought_monthly))))}`
    ).addTo(LAYER);
  });
}

/* ---------------------------------------------------------------- table */
function renderTable(){
  const dir = SORT.dir, k = SORT.k;
  const sorted = [...VIEW].sort((a,b) => {
    const x = a[k], y = b[k];
    if (x === null || x === undefined || x === '') return 1;
    if (y === null || y === undefined || y === '') return -1;
    return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * dir;
  });
  const page = sorted.slice(PAGE*PER, PAGE*PER + PER);

  $('#tbl tbody').innerHTML = page.map((r,i) => {
    const flag = r.needs_review === 'Yes'
      ? `<span class="flagmark" title="${r.rent_sanity_flag || 'low confidence'}">&#9888;</span>` : '';
    return `<tr class="${r.needs_review === 'Yes' ? 'review' : ''}">
    <td>${r.case_reference || ''}${flag}</td>
    <td class="prop">${r.property || ''}</td>
    <td>${r.city || ''}</td>
    <td>${r.postcode || ''}</td>
    <td>${r.landlord_representative || ''}</td>
    <td>${r.original_rent_period || ''}</td>
    <td class="num">${gbp(num(r.original_rent_monthly))}</td>
    <td class="num">${gbp(num(r.rent_sought_monthly))}</td>
    <td class="num">${pct(num(r.uplift_sought_pct))}</td>
    <td class="num">${gbp(num(r.tenant_proposed_rent_monthly))}</td>
    <td class="num">${gbp(num(r.landlord_proposed_rent_monthly))}</td>
    <td class="num"><strong>${gbp(num(r.determined_rent_monthly))}</strong></td>
    <td class="num">${pct(num(r.uplift_determined_pct))}</td>
    <td><span class="tag ${r.outcome_category === 'Determined' ? 'det' : 'no'}">${r.outcome_category || ''}</span></td>
    <td><span class="tag ${r.rra_status === 'Pre-RRA' ? 'pre' : ''}">${r.rra_status || ''}</span></td>
    <td>${r.decision_date || ''}</td>
    <td><button class="btn ghost" data-i="${PAGE*PER + i}">View</button></td></tr>`;
  }).join('');

  $('#tbl tbody').querySelectorAll('button[data-i]').forEach(b =>
    b.onclick = () => showDetail(sorted[+b.dataset.i]));
  $('#tableCount').textContent = `${VIEW.length.toLocaleString('en-GB')} rows`;
  $('#pageInfo').textContent = `Page ${PAGE+1} of ${Math.max(1, Math.ceil(VIEW.length/PER))}`;
}

function showDetail(r){
  const warn = r.needs_review === 'Yes'
    ? `<p style="background:#fff4e5;padding:8px 10px;border-radius:6px;font-size:13px">
         <strong>Needs review:</strong> ${r.rent_sanity_flag || 'low parse confidence'}</p>` : '';
  $('#detailBody').innerHTML = `
    <h3>${r.property || 'Property not captured'}</h3>
    <p class="sub">${r.case_reference || ''} · ${r.city || ''} ${r.postcode || ''}</p>
    ${warn}
    <dl>
      <dt>Landlord / representative</dt><dd>${r.landlord_representative || '–'} (${r.landlord_is_organisation || '–'})</dd>
      <dt>Original rent basis</dt><dd>${r.original_rent_period || '–'}</dd>
      <dt>Original → sought</dt><dd>${gbp(num(r.original_rent_monthly))} → ${gbp(num(r.rent_sought_monthly))} (${pct(num(r.uplift_sought_pct))})</dd>
      <dt>Tenant proposed</dt><dd>${gbp(num(r.tenant_proposed_rent_monthly)) || '–'}</dd>
      <dt>Determined</dt><dd>${gbp(num(r.determined_rent_monthly)) || '–'} (${pct(num(r.uplift_determined_pct))})</dd>
      <dt>Tenant's evidence</dt><dd>${r.tenant_evidence || '–'}</dd>
      <dt>Landlord's evidence</dt><dd>${r.landlord_evidence || '–'}</dd>
      <dt>Tribunal reasoning</dt><dd>${r.tribunal_reasoning || '–'}</dd>
      <dt>Application date</dt><dd>${r.application_date || '–'}</dd>
      <dt>Decision date</dt><dd>${r.decision_date || '–'}</dd>
      <dt>RRA status</dt><dd>${r.rra_status || '–'} · tribunal may exceed landlord's ask: <strong>${r.tribunal_can_exceed_landlord_proposal || '–'}</strong></dd>
      <dt>Parse confidence</dt><dd>${r.parse_confidence || '–'}</dd>
      <dt>Source</dt><dd><a href="${r.decision_url}" target="_blank" rel="noopener">View on GOV.UK</a></dd>
    </dl>`;
  $('#detail').showModal();
}

/* ---------------------------------------------------------------- export */
function exportCsv(){
  if (!VIEW.length) return;
  const cols = Object.keys(VIEW[0]);
  const esc = v => `"${String(v ?? '').replace(/"/g,'""')}"`;
  const csv = [cols.join(','), ...VIEW.map(r => cols.map(c => esc(r[c])).join(','))].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['\ufeff' + csv], {type:'text/csv;charset=utf-8'}));
  a.download = 'rental_tribunal_filtered.csv';
  a.click();
}
