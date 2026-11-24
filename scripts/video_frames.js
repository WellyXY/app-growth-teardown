// Look at what a video ad actually shows and says, without downloading it.
// Paste the whole file into the browser JS tool, run ONE helper, wait ~10s, then take a screenshot.
// Set the tab to about 1400x1000 first and reset it afterwards.
//
// Meta Ad Library (video has a normal src; works with 12 copies of the same file):
//     __metaSheet('1234567890')          // library id that is visible on the page
// TikTok video page (blob: source, so frames are drawn to canvas one by one, ~20s):
//     __tiktokSheet()                    // async: do not await it, screenshot later
//     await __tiktokInfo()               // stats, isAd, and the spoken words from the subtitle track
// YouTube watch page (any of them; loads the storyboard of each id you pass):
//     await __ytSheet('VIDEOIDxxxx')
//     __ytCaptions('VIDEOIDxxxx')        // async: plays muted at 1.5x; read window.__ytText when window.__ytDone
//
// Call __clearSheet() to remove the overlay. Never click through a CAPTCHA; a TikTok login prompt can be skipped.

window.__clearSheet = () => document.getElementById('__sheet')?.remove();
window.__panel = () => {
  __clearSheet();
  const o = document.createElement('div');
  o.id = '__sheet';
  o.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:#222;display:grid;gap:4px;' +
    'grid-template-columns:repeat(6,1fr);align-content:start;padding:4px';
  return o;
};

window.__metaSheet = (libraryId, n = 12) => {
  let p = [...document.querySelectorAll('span,div')].find((e) => !e.children.length && e.textContent.includes(libraryId));
  while (p && !p.querySelector('video')) p = p.parentElement;
  const src = p?.querySelector('video')?.src;
  if (!src) return 'no video found for ' + libraryId + ' (scroll it into the page first)';
  const o = __panel();
  for (let i = 0; i < n; i++) {
    const v = document.createElement('video');
    v.muted = true; v.preload = 'auto'; v.src = src;
    v.style.cssText = 'width:100%;height:480px;object-fit:contain;background:#000';
    v.addEventListener('loadedmetadata', () => { v.currentTime = v.duration * (i / n) + 0.3; });
    o.appendChild(v);
  }
  document.body.appendChild(o);
  return 'frames every ' + (p.querySelector('video').duration / n).toFixed(1) + 's';
};

window.__tiktokSheet = async (n = 12) => {
  const v = document.querySelector('video');
  v.muted = true;
  const o = __panel();
  for (let i = 0; i < n; i++) {
    v.currentTime = v.duration * (i / n) + 0.4;
    await new Promise((r) => {
      const t = setTimeout(r, 2500);
      v.addEventListener('seeked', () => { clearTimeout(t); setTimeout(r, 250); }, { once: true });
    });
    const c = document.createElement('canvas');
    c.width = 270; c.height = 480; c.style.width = '100%';
    c.getContext('2d').drawImage(v, 0, 0, 270, 480);
    o.appendChild(c);
  }
  document.body.appendChild(o);
};

window.__tiktokInfo = async () => {
  const st = JSON.parse(document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__')?.textContent || '{}');
  const it = st.__DEFAULT_SCOPE__?.['webapp.video-detail']?.itemInfo?.itemStruct;
  const url = it?.video?.subtitleInfos?.[0]?.Url;
  const vtt = url ? await fetch(url).then((r) => r.text()).catch(() => '') : '';
  return JSON.stringify({
    stats: it?.stats, isAd: it?.isAd, seconds: it?.video?.duration, caption: it?.desc,
    spoken: vtt.replace(/WEBVTT|[\d:.]+ --> [\d:.]+/g, '').replace(/\s+/g, ' ').slice(0, 1800),
  });
};

window.__ytSheet = async (id, cells = 18) => {
  const h = await fetch('/watch?v=' + id).then((r) => r.text());
  const m = h.match(/"playerStoryboardSpecRenderer":\{"spec":"(.*?)"/);
  if (!m) return 'no storyboard';
  const parts = JSON.parse('"' + m[1] + '"').split('|');
  const f = parts[parts.length - 1].split('#');
  const [w, hgt, total, cols, rows] = f.slice(0, 5).map(Number);
  const o = __panel();
  o.style.display = 'flex'; o.style.flexWrap = 'wrap';
  const step = Math.ceil(total / cells);
  const scale = w > hgt ? 0.8 : 1.4;
  for (let i = 0; i < total; i += step) {
    const k = i % (cols * rows);
    const url = parts[0].replace('$L', parts.length - 2)
      .replace('$N', f[6].replace('$M', Math.floor(i / (cols * rows)))) + '&sigh=' + f[7];
    const box = document.createElement('div');
    box.style.cssText = `width:${w * scale}px;height:${hgt * scale}px;overflow:hidden`;
    const d = document.createElement('div');
    d.style.cssText = `width:${w}px;height:${hgt}px;transform:scale(${scale});transform-origin:0 0;` +
      `background:url("${url}") -${(k % cols) * w}px -${Math.floor(k / cols) * hgt}px`;
    box.appendChild(d); o.appendChild(box);
  }
  document.body.appendChild(o);
  return total + ' storyboard frames, showing every ' + step;
};

window.__ytCaptions = async (id, maxSeconds = 90) => {
  window.__ytDone = false; window.__ytText = '';
  const p = document.querySelector('#movie_player');
  p.mute(); p.loadVideoById(id);
  await new Promise((r) => setTimeout(r, 3000));
  p.loadModule('captions'); p.setOption('captions', 'track', { languageCode: 'en' });
  p.setPlaybackRate(1.5); p.seekTo(0);
  let words = [];
  const t0 = Date.now();
  while (Date.now() - t0 < maxSeconds * 1000 && p.getPlayerState() !== 0) {
    await new Promise((r) => setTimeout(r, 250));
    const w = [...document.querySelectorAll('.ytp-caption-segment')].map((x) => x.textContent).join(' ').split(' ').filter(Boolean);
    let same = Math.min(w.length, words.length);
    while (same > 0 && words.slice(-same).join(' ') !== w.slice(0, same).join(' ')) same--;
    words = words.concat(w.slice(same));
    window.__ytText = words.join(' ');
  }
  window.__ytDone = true;
};
