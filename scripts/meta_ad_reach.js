// Meta Ad Library — read reach of the first n ads on the page, WITH the region label next to the number.
// Paste into the browser JS tool on an Ad Library results page that lists single ads ("See ad details").
// Tip: &country=GB (or an EU country) with &sort_data[mode]=total_impressions&sort_data[direction]=desc
// lists the ads Meta discloses reach for, biggest first.
//
//     __metaReach(7); // async: do not await (about 7s per ad). Poll window.__metaDone, read window.__metaRows
//
// The "Transparency by location" panel has separate European Union and United Kingdom tabs and opens on
// the EU one, whatever country you filtered by. Never label a number from the filter; use `region` here.

window.__metaReach = async (n = 7) => {
  window.__metaRows = []; window.__metaDone = false;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const clickable = (el) => {
    for (let i = 0; el && i < 6; i++, el = el.parentElement) {
      if (['button', 'tab'].includes(el.getAttribute('role')) || el.tabIndex >= 0) return el;
    }
  };
  const leaf = (root, text) => [...root.querySelectorAll('*')].find((e) => !e.children.length && e.textContent.trim() === text);
  const buttons = [...document.querySelectorAll('div[role=button]')].filter((b) => b.innerText.trim() === 'See ad details').slice(0, n);
  for (const b of buttons) {
    let card = b;
    while (!/Library ID/.test(card.innerText)) card = card.parentElement;
    const row = { id: card.innerText.match(/Library ID: (\d+)/)[1], start: card.innerText.match(/Started running on ([^\n]+)/)?.[1] };
    b.click(); await wait(2500);
    const dlg = [...document.querySelectorAll('[role=dialog]')].filter((d) => /Library ID/.test(d.innerText)).pop();
    const link = dlg && leaf(dlg, 'Transparency by location');
    if (link) {
      clickable(link)?.click(); await wait(1500);
      const m = dlg.innerText.match(/(EU|UK) ad delivery\s*Reach\s*([\d,]+)/);
      row.region = m?.[1] ?? null;
      row.reach = m ? Number(m[2].replace(/,/g, '')) : null;
    }
    window.__metaRows.push(row);
    [...(dlg?.querySelectorAll('[role=button]') ?? [])].find((x) => x.innerText.trim() === 'Close')?.click();
    await wait(1200);
  }
  window.__metaDone = true;
};
