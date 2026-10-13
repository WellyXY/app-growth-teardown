// Google Ads Transparency Center — pull every creative of one advertiser with first/last shown dates.
// Paste into the browser JS tool while on any https://adstransparency.google.com/ page
// (the calls are same-origin, so the page must be on that host).
//
// Find the advertiser id first: search the brand in the UI, click the official domain under
// "Websites", open one of the listed advertisers, and copy the id from the URL (starts with "AR").
//
// Usage (one JS-tool call each):
//   1. paste this whole file once
//   2. const ads = await __gatFetch('AR07338665835327651841')                 // all regions
//      const us  = await __gatFetch('AR07338665835327651841', 'US')           // one region
//   3. JSON.stringify(__gatMonthly(ads, '2025-11', '2026-09'))                // active / new per month
//   4. JSON.stringify(await __gatByRegion('AR07...', ['US','IN','PH','BR','MX','ID','VN']))
//   5. Open a creative to check it is an app-install ad:
//      https://adstransparency.google.com/advertiser/<AR id>/creative/<CR id>?region=anywhere
//
// Format codes: 1 = text, 2 = image, 3 = video. Counts are creatives, not spend.

window.__GAT_GEO = {
  US: 2840, CA: 2124, GB: 2826, AU: 2036, DE: 2276, FR: 2250, ES: 2724, IT: 2380, NL: 2528,
  IN: 2356, PK: 2586, BD: 2050, PH: 2608, ID: 2360, VN: 2704, TH: 2764, MY: 2458, SG: 2702,
  JP: 2392, KR: 2410, TW: 2158, BR: 2076, MX: 2484, AR: 2032, CO: 2170, CL: 2152, PE: 2604,
  TR: 2792, SA: 2682, AE: 2784, EG: 2818, NG: 2566, ZA: 2710, KE: 2404,
};

window.__gatFetch = async (advertiserId, region = null, maxPages = 15) => {
  const out = [];
  let token = null;
  for (let page = 0; page < maxPages; page++) {
    const q = { 2: 100, 3: { 12: { 1: '', 2: true }, 13: { 1: [advertiserId] } }, 7: { 1: 1, 2: 0, 3: 2344 } };
    if (region) q[3][8] = [window.__GAT_GEO[region] || region];
    if (token) q[4] = token;
    const r = await fetch('/anji/_/rpc/SearchService/SearchCreatives?authuser=0', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: 'f.req=' + encodeURIComponent(JSON.stringify(q)),
    });
    const j = await r.json();
    for (const c of j['1'] || []) {
      out.push({ id: c['2'], format: c['4'], first: +c['6']['1'], last: +c['7']['1'] });
    }
    token = j['2'];
    if (!token) break;
  }
  return out;
};

window.__gatMonths = (from, to) => {
  const months = [];
  let [y, m] = from.split('-').map(Number);
  const [ty, tm] = to.split('-').map(Number);
  while (y < ty || (y === ty && m <= tm)) {
    months.push(`${y}-${String(m).padStart(2, '0')}`);
    m++;
    if (m > 12) { m = 1; y++; }
  }
  return months;
};

window.__gatMonthly = (ads, from, to) => {
  const fmt = { 1: 'text', 2: 'image', 3: 'video' };
  const rows = {};
  for (const mo of window.__gatMonths(from, to)) {
    const [y, m] = mo.split('-').map(Number);
    const s = Date.UTC(y, m - 1, 1) / 1000;
    const e = Date.UTC(y, m, 1) / 1000;
    const active = ads.filter((a) => a.first < e && a.last >= s);
    const row = { active: active.length, new: ads.filter((a) => a.first >= s && a.first < e).length };
    for (const a of active) row[fmt[a.format] || 'other'] = (row[fmt[a.format] || 'other'] || 0) + 1;
    rows[mo] = row;
  }
  const firsts = ads.map((a) => a.first).sort((a, b) => a - b);
  return {
    totalCreatives: ads.length,
    firstShown: firsts.length ? new Date(firsts[0] * 1000).toISOString().slice(0, 10) : null,
    months: rows,
  };
};

window.__gatByRegion = async (advertiserId, regions, from = null, to = null) => {
  const res = {};
  for (const r of regions) {
    const ads = await window.__gatFetch(advertiserId, r);
    const firsts = ads.map((a) => a.first).sort((a, b) => a - b);
    res[r] = {
      creatives: ads.length,
      firstShown: firsts.length ? new Date(firsts[0] * 1000).toISOString().slice(0, 10) : null,
    };
    if (from && to) {
      const m = window.__gatMonthly(ads, from, to).months;
      res[r].activeByMonth = Object.values(m).map((x) => x.active).join(',');
    }
  }
  return res;
};

'google ads transparency helpers ready: __gatFetch / __gatMonthly / __gatByRegion';
