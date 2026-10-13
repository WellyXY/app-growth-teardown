// TikTok profile / hashtag collector — paste into the browser JS tool.
//
// Works on:  https://www.tiktok.com/@<handle>   and   https://www.tiktok.com/tag/<hashtag>
// Before running: set the viewport to at least 1280x900 (the video grid does not render in short
// windows). On a profile, click the "Oldest" sort first if you want the full history.
//
// Usage (one JS-tool call each; every call must finish within ~45s):
//   1. paste this whole file once                      -> defines helpers
//   2. await __ttCollect(18)                            -> scroll+collect; repeat until the count stops growing
//   3. JSON.stringify(__ttSummary())                    -> monthly stats, concentration, top videos
//   4. JSON.stringify(__ttAccounts())                   -> (hashtag pages) who is posting
//
// Video IDs encode the post time: unix_seconds = id >> 32.
// Views come from the grid badge (e.g. "13.6M"); likes/comments/saves/shares require opening each
// video page (the four numbers under the video, in that order).

window.__tt = window.__tt || new Map();

window.__ttParse = (v) => {
  const m = String(v || '').match(/([\d.]+)\s*([KMB]?)/i);
  if (!m) return 0;
  const mult = { K: 1e3, M: 1e6, B: 1e9 }[m[2].toUpperCase()] || 1;
  return Math.round(parseFloat(m[1]) * mult);
};

window.__ttGrab = () => {
  document.querySelectorAll('a[href*="/video/"]').forEach((a) => {
    const m = a.getAttribute('href').match(/@([^/]+)\/video\/(\d+)/);
    if (!m || window.__tt.has(m[2])) return;
    const ts = Number(BigInt(m[2]) >> 32n);
    window.__tt.set(m[2], {
      id: m[2],
      user: m[1],
      date: new Date(ts * 1000).toISOString().slice(0, 10),
      views: window.__ttParse((a.querySelector('strong') || {}).textContent),
      caption: ((a.querySelector('img') || {}).alt || '').slice(0, 140),
    });
  });
  return window.__tt.size;
};

window.__ttCollect = async (rounds = 18, pauseMs = 1800) => {
  for (let i = 0; i < rounds; i++) {
    window.__ttGrab();
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise((r) => setTimeout(r, pauseMs));
  }
  return window.__ttGrab();
};

window.__ttSummary = (topN = 15, user = null) => {
  const all = [...window.__tt.values()].filter((v) => !user || v.user === user);
  const total = all.reduce((s, v) => s + v.views, 0);
  const sorted = [...all].sort((a, b) => b.views - a.views);
  const topShare = (n) => (total ? +(sorted.slice(0, n).reduce((s, v) => s + v.views, 0) / total).toFixed(3) : 0);
  const byMonth = {};
  for (const v of all) {
    const k = v.date.slice(0, 7);
    const b = (byMonth[k] = byMonth[k] || { posts: 0, views: 0, list: [], top: '' });
    b.posts++;
    b.views += v.views;
    b.list.push(v.views);
    if (!b.topViews || v.views > b.topViews) { b.topViews = v.views; b.top = v.caption.slice(0, 60); }
  }
  for (const b of Object.values(byMonth)) {
    b.list.sort((x, y) => x - y);
    b.median = b.list[Math.floor(b.list.length / 2)] || 0;
    delete b.list;
  }
  const dates = all.map((v) => v.date).sort();
  return {
    videos: all.length,
    firstPost: dates[0],
    lastPost: dates.at(-1),
    totalViews: total,
    top10Share: topShare(10),
    under5k: all.filter((v) => v.views < 5000).length,
    byMonth: Object.fromEntries(Object.entries(byMonth).sort()),
    top: sorted.slice(0, topN).map((v) => ({ id: v.id, date: v.date, views: v.views, caption: v.caption })),
  };
};

window.__ttAccounts = () => {
  const acc = {};
  for (const v of window.__tt.values()) {
    const a = (acc[v.user] = acc[v.user] || { videos: 0, first: v.date, last: v.date });
    a.videos++;
    if (v.date < a.first) a.first = v.date;
    if (v.date > a.last) a.last = v.date;
  }
  return Object.entries(acc).sort((a, b) => b[1].videos - a[1].videos).map(([user, a]) => ({ user, ...a }));
};

'tiktok helpers ready: await __ttCollect(18) -> __ttSummary() / __ttAccounts()';
