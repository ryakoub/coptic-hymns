// Shared by the pages that mirror the app (home, library, season, hymn): the catalog the app reads
// (catalog/v1/index.json), the header and footer, season colors, and the church calendar.
const CC = (() => {
  // The App Store or public TestFlight link, once there is one; until then the pages say "coming soon".
  const GET_APP = null;

  let catalogPromise;
  function catalog() {
    catalogPromise ??= fetch("/catalog/v1/index.json").then(r => r.json()).then(c => {
      c.textById = new Map(c.texts.map(t => [t.id, t]));
      c.recordingById = new Map(c.recordings.map(r => [r.id, r]));
      c.serviceById = new Map(c.services.map(s => [s.id, s]));
      return c;
    });
    return catalogPromise;
  }

  const esc = s => String(s ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);

  // The app's rules: the English title first, then the Coptic, then the Arabic.
  const primary = t => t?.english || t?.coptic || t?.arabic || "";

  const entryCount = col => col.sections.reduce((n, s) => n + s.entries.length, 0);
  const entryRecording = e => typeof e === "string" ? e : e.recording;
  const entryText = (c, e) => (typeof e === "object" && e.text) || c.recordingById.get(entryRecording(e))?.text;

  const sectionTitles = (c, s) => s.titles || c.serviceById.get(s.service)?.titles || {};

  // A section's list as the app shows it: hymns in order, with a sub-folder where its first hymn comes.
  function sectionItems(s) {
    if (!s.groups?.length) return s.entries.map(e => ({ hymn: e }));
    const folderOf = new Map();
    for (const g of s.groups) for (const r of g.recordings) if (!folderOf.has(r)) folderOf.set(r, g);
    const shown = new Set(), out = [];
    for (const e of s.entries) {
      const g = folderOf.get(entryRecording(e));
      if (g) { if (!shown.has(g.id)) { shown.add(g.id); out.push({ folder: g }); } }
      else out.push({ hymn: e });
    }
    return out;
  }

  function syncBadge(r) {
    const t = r.timing || {};
    if (t.of > 0 && t.words === t.of) return '<span class="badge-sync words">Word by word</span>';
    if (t.words > 0) return '<span class="badge-sync some">Some words</span>';
    if (t.lines > 0) return '<span class="badge-sync">Line by line</span>';
    return "";
  }

  const duration = s => s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}` : "";

  // ── Colors of the church year, for the season cards ──
  const COVERS = {
    "annual": ["#0e6f8f", "#044a7a"],
    "kiahk": ["#1f3c88", "#5b8def"],
    "jonahs-fast": ["#2c5364", "#0f2027"],
    "great-lent": ["#4a2c6d", "#7b4fa0"],
    "holy-week": ["#2b2b2b", "#5a1f1f"],
    "bright-saturday": ["#7a5c1e", "#c9a24a"],
    "apostles-fast": ["#3d5a3c", "#7aa36f"],
    "common-hymns": ["#0a8197", "#044a7a"],
    "nayrouz": ["#9c2a1f", "#e0603a"],
    "feast-of-the-cross": ["#8a1c1c", "#c94a3a"],
    "nativity": ["#b8860b", "#f4b400"],
    "circumcision": ["#a37a1c", "#d9b45a"],
    "theophany": ["#0b5c8a", "#4fb6d6"],
    "wedding-at-cana": ["#7a2e4f", "#c46a8e"],
    "presentation": ["#6d5a2c", "#c9a24a"],
    "lazarus-saturday": ["#4b4b6d", "#8a8ab0"],
    "palm-sunday": ["#2e6b2e", "#7fb36a"],
    "resurrection": ["#c99a1c", "#f7d774"],
    "ascension": ["#1d5f9c", "#86c1ec"],
    "pentecost": ["#a3201c", "#f06a3a"],
  };
  const GROUP_COVERS = { occasions: ["#7a2e4f", "#c46a8e"], fasts: ["#3b3561", "#6b5f9e"], feasts: ["#a37a1c", "#f4b400"], programs: ["#044a7a", "#f4b400"] };
  function cover(col, groupId) {
    const [a, b] = COVERS[col.id] || GROUP_COVERS[groupId] || ["#0e6f8f", "#0a8197"];
    return `background: linear-gradient(135deg, ${a}, ${b});`;
  }

  // ── The church year (as the app's ChurchCalendar) ──
  const DAY = 864e5;
  const dayNumber = d => Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY) + 2440588;
  const fromDayNumber = n => { const u = new Date((n - 2440588) * DAY); return new Date(u.getUTCFullYear(), u.getUTCMonth(), u.getUTCDate()); };
  const copticDay = (y, m, d) => 1824665 + 365 * y + Math.floor(y / 4) + 30 * m + d - 31;
  function copticYear(n) {
    let y = Math.floor((n - 1825030) / 365.25) + 1;
    while (copticDay(y + 1, 1, 1) <= n) y++;
    while (copticDay(y, 1, 1) > n) y--;
    return y;
  }
  // The Feast of the Resurrection: the Julian Easter, 13 days later in the Gregorian calendar (1900–2099).
  function resurrection(year) {
    const a = year % 4, b = year % 7, c = year % 19;
    const d = (19 * c + 15) % 30, e = (2 * a + 4 * b - d + 34) % 7;
    const month = Math.floor((d + e + 114) / 31), day = (d + e + 114) % 31 + 1;
    return dayNumber(new Date(year, month - 1, day)) + 13;
  }
  function point(p, g, c) {
    if (p.easter != null) return resurrection(g) + p.easter;
    if (p.coptic?.length === 2) return copticDay(c, p.coptic[0], p.coptic[1]);
    return null;
  }
  // A rule's spans (first and last day numbers) starting last year, this year and next year.
  function spans(rule, n) {
    const g = fromDayNumber(n).getFullYear(), c = copticYear(n), out = [];
    for (let k = -1; k <= 1; k++) {
      const start = point(rule.from, g + k, c + k);
      if (start == null) continue;
      const ends = [-1, 0, 1, 2].map(j => point(rule.to, g + k + j, c + k + j)).filter(e => e != null && e >= start);
      if (ends.length) out.push([start, Math.min(...ends)]);
    }
    return out;
  }
  const today = () => dayNumber(new Date());
  const isCurrent = (col, n = today()) => !!col.dates && spans(col.dates, n).some(([a, b]) => a <= n && n <= b);
  // This year's span, or the next one when this year's is over.
  function nextSpan(col, n = today()) {
    if (!col.dates) return null;
    const all = [...spans(col.dates, n), ...spans(col.dates, n + 365)].filter(([, b]) => b >= n).sort((x, y) => x[0] - y[0]);
    return all[0] || null;
  }
  function spanText(col) {
    const s = nextSpan(col);
    if (!s) return "";
    const f = d => fromDayNumber(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const year = fromDayNumber(s[1]).getFullYear();
    return s[0] === s[1] ? `${f(s[0])}, ${year}` : `${f(s[0])} – ${f(s[1])}, ${year}`;
  }

  // ── Header and footer ──
  function header(active) {
    const link = (href, label, key, extra = "") =>
      `<a href="${href}" class="${extra}"${active === key ? ' aria-current="page"' : ""}>${label}</a>`;
    document.body.insertAdjacentHTML("afterbegin", `
<header class="site-header"><div class="wrap">
  <a class="brand" href="/"><img src="/brand/logo-en.svg" alt="" width="36" height="36">Coptic Chanter</a>
  <nav class="site-nav">
    ${link("/library.html", "Library", "library", "menu-library")}
    ${link("/#features", "Features", "features")}
    ${link("/support.html", "Support", "support")}
    <a class="pill" href="${GET_APP || "/#get"}">Get the app</a>
  </nav>
</div></header>`);
  }

  function footer() {
    document.body.insertAdjacentHTML("beforeend", `
<footer class="site-footer"><div class="wrap">
  <div class="cols">
    <div class="about">
      <a class="brand" href="/"><img src="/brand/logo-en.svg" alt="" width="36" height="36">Coptic Chanter</a>
      <p>The hymns of the Coptic Orthodox Church, with their words lighting up as the cantor sings. Free, with no ads and no tracking.</p>
    </div>
    <div><h4>Explore</h4><ul>
      <li><a href="/library.html">Library</a></li>
      <li><a href="/#features">Features</a></li>
      <li><a href="/#get">Get the app</a></li>
      <li><a href="/groups.html?curriculum=mahragan-keraza-2026">Mahragan 2026 levels</a></li>
    </ul></div>
    <div><h4>Help</h4><ul>
      <li><a href="/support.html">Support</a></li>
      <li><a href="mailto:support@copticchanter.com">support@copticchanter.com</a></li>
      <li><a href="/privacy.html">Privacy</a></li>
    </ul></div>
  </div>
  <div class="closing"><div class="coptic">ϩⲱⲥ ⲉ̀ⲣⲟϥ</div>Praise Him · © ${new Date().getFullYear()} Coptic Chanter</div>
</div></footer>`);
  }

  // A season's card, as on the library and home pages.
  let cardIndex = 0;
  function card(c, col, groupId) {
    const n = entryCount(col);
    return `<a class="card" style="--delay: ${(cardIndex++ % 12) * 0.25}s" href="/season.html?id=${encodeURIComponent(col.id)}">
  <div class="cover" style="${cover(col, groupId)}">
    ${isCurrent(col) ? '<span class="now">Now</span>' : ""}
    <span class="glyph" lang="ar">${esc(col.titles.arabic || "")}</span><span class="glyph en">${esc(primary(col.titles))}</span>
  </div>
  <div class="meta"><strong>${esc(primary(col.titles))}</strong>
    <span class="n">${n} hymn${n === 1 ? "" : "s"}${col.dates ? " · " + esc(spanText(col)) : ""}</span></div>
</a>`;
  }

  return { GET_APP, catalog, esc, primary, entryCount, entryRecording, entryText, sectionTitles, sectionItems,
           syncBadge, duration, cover, isCurrent, nextSpan, spanText, header, footer, card };
})();
