export const CAVEAT = "A name match is a possible match, not proof. Ships and companies share names; check the numbered source before you publish. This site describes documented conduct and makes no legal findings.";
export const LIST_LABELS = { us: "United States", uk: "United Kingdom", eu: "European Union", un: "United Nations" };
export const LIST_PAGES = {
  us: "https://www.trade.gov/consolidated-screening-list",
  uk: "https://www.gov.uk/government/publications/the-uk-sanctions-list",
  eu: "https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions",
  un: "https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list",
};
const GOVERNMENTS = new Set(Object.values(LIST_LABELS));
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** Whole months from the nightly summary.json, or null when it is missing or malformed. */
export function medianMonths(doc) {
  const m = doc?.median_months;
  return typeof m === "number" && Number.isFinite(m) && m > 0 ? Math.round(m) : null;
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function safeUrl(url) {
  try {
    const parsed = new URL(url, "https://flagstate.invalid/");
    if (parsed.protocol === "https:" || parsed.protocol === "http:") return url;
  } catch { /* fall through */ }
  return "#";
}

export function joinAnd(items) {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

export function formatDate(iso, long = false) {
  const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(iso || "");
  if (!m) return "";
  const month = MONTHS[Number(m[2]) - 1];
  if (!month) return "";
  const name = long ? month : month.slice(0, 3);
  return m[3] ? `${Number(m[3])} ${name} ${m[1]}` : `${name} ${m[1]}`;
}

export function formatUpdated(date) {
  const iso = date.toISOString();
  return `${formatDate(iso.slice(0, 10))}, ${iso.slice(11, 16)} UTC`;
}

const MAX_PCT = 86;
const MIN_GAP = 14;

export function timelinePositions(events) {
  const dated = events
    .map((e) => ({ ...e, t: Date.parse(e.date.length === 7 ? `${e.date}-01` : e.date) }))
    .filter((e) => !Number.isNaN(e.t))
    .sort((a, b) => a.t - b.t);
  if (!dated.length) return [];
  const min = dated[0].t;
  const span = dated.at(-1).t - min || 1;
  const gap = dated.length > 1 ? Math.min(MIN_GAP, MAX_PCT / (dated.length - 1)) : 0;
  const pos = dated.map((e) => ((e.t - min) / span) * MAX_PCT);
  // Push labels apart going forward, then pull them back under MAX_PCT going backward.
  for (let i = 1; i < pos.length; i++) pos[i] = Math.max(pos[i], pos[i - 1] + gap);
  pos[pos.length - 1] = Math.min(pos.at(-1), MAX_PCT);
  for (let i = pos.length - 2; i >= 0; i--) pos[i] = Math.min(pos[i], pos[i + 1] - gap);
  return dated.map((e, i) => ({ ...e, pct: pos[i] }));
}

function listingPhrase(l) {
  return (GOVERNMENTS.has(l.by) ? `the ${l.by}` : l.by) + (l.date ? ` on ${formatDate(l.date, true)}` : "") + (l.program ? ` (${l.program})` : "");
}

export function citation(entry, pageUrl, today = new Date()) {
  const head = entry.imo ? `${entry.name} (IMO ${entry.imo})` : entry.name;
  const listed = entry.listings.length ? `listed by ${joinAnd(entry.listings.map(listingPhrase))}` : "not listed by a government in our research";
  const urls = entry.sources.map((s) => new URL(s.url, pageUrl).href).join(" ; ");
  return `${head}: ${listed}. Sources: ${urls}. Via Flagstate, ${pageUrl}, accessed ${formatDate(today.toISOString().slice(0, 10), true)}.`;
}

function hostOf(url) {
  try { return new URL(url).hostname; } catch { return "Flagstate research"; }
}

export function renderDossier(e) {
  const sid = e.id.replace(/[^A-Za-z0-9_-]/g, "_");
  const sub = [e.kind, e.imo && `IMO ${e.imo}`, e.flag && `Flag ${e.flag}`, e.manager && `Manager ${e.manager}`, !e.imo && e.country, !e.imo && e.role]
    .filter(Boolean).join(" · ");
  const chips = e.listings.map((l) => `<div class="chip"><b>${escapeHtml(l.by)}</b><span>${escapeHtml([formatDate(l.date), l.program].filter(Boolean).join(" · ").toUpperCase())}</span></div>`).join("");
  const verdict = chips
    ? `<div class="verdicts" data-walk="chips" aria-label="Listed by">${chips}</div>`
    : `<p class="d-unlisted">Not listed by a government in our research.</p>`;

  const tl = timelinePositions(e.events);
  const timeline = tl.length > 1 ? `
    <div class="timeline" data-walk="timeline" role="img" aria-label="${escapeHtml("Timeline: " + tl.map((x) => `${formatDate(x.date)}, ${x.text}`).join("; "))}">
      <div class="tl-track"><div class="tl-line"></div>${tl.map((x) => `
        <div class="tl-ev${x.kind === "listing" ? " hit" : ""}" style="left:${x.pct.toFixed(1)}%"><span class="when">${escapeHtml(formatDate(x.date).toUpperCase())}</span><span class="dot"></span><span class="what">${escapeHtml(x.text)}</span></div>`).join("")}
      </div>
      <button type="button" class="tl-more" aria-expanded="false" hidden>Show full text</button>
      <p class="tl-note">Spacing is approximate. Red marks a government listing.</p>
    </div>` : "";

  const sup = (refs) => refs.map((n) => `<sup><a href="#src-${sid}-${Number(n)}">${Number(n)}</a></sup>`).join("");
  const facts = e.facts.map((f) => `<p>${escapeHtml(f.text)}${sup(f.refs)}</p>`).join("");

  const nameTag = (n) => (n.current ? "CURRENT" : e.imo ? "FORMER" : "ALSO KNOWN AS");
  const names = e.names.length > 1 ? `
    <div class="block" data-walk="names">
      <h3>${e.imo ? `${e.names.length} names, one hull` : "Other names"}</h3>
      <ul class="names">${e.names.map((n) => `<li${n.current ? ' class="now"' : ""}>${escapeHtml(n.name)} <span>${nameTag(n)}</span></li>`).join("")}</ul>
      ${e.flags.length ? `<p class="tl-note">Flags flown: ${escapeHtml(joinAnd(e.flags))}.</p>` : ""}
    </div>` : "";

  const sources = `
    <div class="block" data-walk="sources">
      <h3>Sources</h3>
      <ol class="src">${e.sources.map((s) => `<li value="${Number(s.n)}" id="src-${sid}-${Number(s.n)}">${escapeHtml(s.label)}. <a href="${escapeHtml(safeUrl(s.url))}" rel="noopener">${escapeHtml(hostOf(s.url))}</a></li>`).join("")}</ol>
    </div>`;

  return `
  <article class="dossier-entry" id="entry-${sid}">
    <div class="d-head">
      <div><h2>${escapeHtml(e.name)}</h2><p class="d-sub">${escapeHtml(sub.toUpperCase())}</p></div>
      ${verdict}
    </div>
    ${timeline}
    <div class="cols">
      <div>
        <div class="block reported"><h3>What the records show</h3>${facts}</div>
        <div class="d-actions">
          <a class="btn" href="${escapeHtml(safeUrl(e.story.url))}">${escapeHtml(e.story.label)}</a>
          <button class="btn" type="button" data-cite="${escapeHtml(e.id)}">Copy citation</button>
        </div>
      </div>
      <div>${names}${sources}</div>
    </div>
    <div class="connections" data-connections="${escapeHtml(e.id)}"></div>
  </article>`;
}

export function renderResearch(entries) {
  if (!entries.length) return "";
  const [first, ...rest] = entries;
  const more = rest.map((e) => `
    <details class="more"><summary><span class="more-name">${escapeHtml(e.name)}</span><span class="more-kind">${escapeHtml(e.kind)}</span>${e.listings.map((l) => `<span class="mini-chip">${escapeHtml(l.by)}</span>`).join("")}</summary>${renderDossier(e)}</details>`).join("");
  return `<p class="label">In our research · ${entries.length} ${entries.length === 1 ? "match" : "matches"}</p>${renderDossier(first)}${rest.length ? `<div class="more-list"><h3 class="more-head">Other matches in our research</h3>${more}</div>` : ""}`;
}

/** The most specific official page for a list hit: OFAC and UK entries by id, the EU act that listed it, else the list home. */
export function recordLink(h) {
  if (h.url) return { url: h.url, text: "Legal act" };
  if (h.list === "us" && /^\d+$/.test(h.ref || "")) return { url: `https://sanctionssearch.ofac.treas.gov/Details.aspx?id=${h.ref}`, text: "Record" };
  if (h.list === "uk" && /^[A-Z]{3}\d{4}$/.test(h.ref || "")) return { url: `https://search-uk-sanctions-list.service.gov.uk/?searchValue=${h.ref}`, text: "Record" };
  return { url: LIST_PAGES[h.list], text: "List home" };
}

export function renderLists(hits, failedIds = []) {
  const rows = hits.map((h) => {
    const link = recordLink(h);
    return `<tr><td>${escapeHtml(LIST_LABELS[h.list])}</td><td>${escapeHtml(h.name)}</td><td>${escapeHtml(h.program)}</td><td class="mono">${escapeHtml(h.date || "—")}</td><td><a href="${escapeHtml(safeUrl(link.url))}" rel="noopener">${link.text}</a></td></tr>`;
  }).join("");
  const table = hits.length
    ? `<table class="lists"><thead><tr><th scope="col">List</th><th scope="col">Listed as</th><th scope="col">Program</th><th scope="col">Date</th><th scope="col"><span class="visually-hidden">Link</span></th></tr></thead><tbody>${rows}</tbody></table>`
    : `<p class="muted">No match on the official lists${failedIds.length ? " that loaded" : ""}.</p>`;
  const failed = failedIds.length
    ? `<p class="layer-error">Couldn't load the ${escapeHtml(joinAnd(failedIds.map((id) => LIST_LABELS[id])))} list${failedIds.length > 1 ? "s" : ""}. <button class="btn" type="button" data-retry="lists">Retry</button></p>`
    : "";
  return `<div class="block"><h3>On official sanctions lists · ${hits.length} ${hits.length === 1 ? "record" : "records"}</h3>${table}${failed}</div>`;
}

export function renderWider(state, query) {
  const link = `<a class="btn" href="https://www.opensanctions.org/search/?q=${encodeURIComponent(query)}" rel="noopener">Search on OpenSanctions</a>`;
  let body;
  if (state.kind === "loading") {
    body = `<p>Checking OpenSanctions…</p>`;
  } else if (state.kind === "results" && state.results.length) {
    body = `<ul class="wider-list">${state.results.map((r) => `<li><a href="${escapeHtml(safeUrl(r.url))}" rel="noopener">${escapeHtml(r.name)}</a> <span>${escapeHtml([r.schema, (r.datasets || []).join(", ")].filter(Boolean).join(" · "))}</span></li>`).join("")}</ul><p class="tl-note">Results from OpenSanctions, CC BY-NC 4.0.</p>${link}`;
  } else if (state.kind === "results") {
    body = `<p>No OpenSanctions match.</p>${link}`;
  } else {
    body = `<p>Sanctions lists from 95 sources worldwide, compiled by OpenSanctions.${state.kind === "error" ? " The live check is unavailable right now." : ""}</p>${link}`;
  }
  return `<div class="block wider"><h3>Wider check</h3>${body}</div>`;
}

export function renderEmpty(query) {
  return `<div class="state"><strong>Not found in our research or on the official lists</strong>Nothing matched “${escapeHtml(query)}”. Check the spelling, try a former name, or search by the seven-digit IMO number.</div>`;
}

export function renderHint() {
  return `<div class="state"><strong>Type the name in Latin letters, or use the IMO number</strong>Names written only in other scripts, or only a company ending like “LLC”, can't be matched.</div>`;
}

export function renderLoading() {
  return `<div class="state"><strong>Loading the lists…</strong>The first search downloads our research and the four official lists. Later searches are instant.</div>`;
}

export function renderLayerError(layer) {
  return `<div class="state"><strong>Couldn't load our ${escapeHtml(layer)}</strong>The official lists below still work. <button class="btn" type="button" data-retry="${escapeHtml(layer)}">Retry</button></div>`;
}
