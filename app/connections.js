// Connections panel: who the sanctions lists link to an entity, and US lobbying around it.
// Pure functions returning HTML strings; every value from data is escaped.
import { escapeHtml, safeUrl, joinAnd } from "./render.js";

const MAX_SANCTION_BOXES = 8;
const MAX_FIRM_BOXES = 4;
const MAX_DIRECT_BOXES = 4;
const BOX = { w: 190, h: 52, gapY: 16 };
const COLS = [20, 290, 560];
const LABEL_MAX = 26;
const EDGE_MAX = 30;
const PLURAL = { Vessel: "ships", Person: "people", Company: "companies", Organization: "organisations", LegalEntity: "entities", Airplane: "aircraft" };
const SINGULAR = { Vessel: "ship", Person: "person", Company: "company", Organization: "organisation", LegalEntity: "entity", Airplane: "aircraft" };
const NO_PROOF = "No filing found is not proof of no influence.";

export function connectionsQuery(entry) {
  return entry.imo ? `imo=${entry.imo}` : `name=${encodeURIComponent(entry.name)}`;
}

export function sentence(focusName, link) {
  const r = link.role;
  const role = /^.[a-z]/.test(r) ? r.charAt(0).toLowerCase() + r.slice(1) : r;
  return link.direction === "out" ? `${focusName} ${role} ${link.name}` : `${link.name} ${role} ${focusName}`;
}

function clip(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

const plural = (n, schema) => (n === 1 ? SINGULAR[schema] : PLURAL[schema]) || schema;
const filingsText = (n) => `${n} ${n === 1 ? "filing" : "filings"}`;
const fmtMoney = (usd) => (usd >= 1e6 ? `$${(usd / 1e6).toFixed(2)}M` : usd >= 1e3 ? `$${Math.round(usd / 1e3)}K` : `$${usd}`);
const years = (y) => (y && y.length ? (y[0] === y[1] ? `${y[0]}` : `${y[0]}–${y[1]}`) : "");
const auth = (a) => (a && a.length ? a.join(", ") : "");

// One direction for a whole group, or null when its items disagree.
const groupDir = (g) => (g.items.length && g.items.every((x) => x.direction === g.items[0].direction) ? g.items[0].direction : null);
// The role only when every item shares it (and its direction); mixed groups print none.
const sharedRole = (g) => (g.items.length && g.items.every((x) => x.role === g.items[0].role && x.direction === g.items[0].direction) ? g.items[0].role : "");

export function layoutGraph(data) {
  const s = data.sanctions || {};
  const l = data.lobbying || {};
  const focusName = s.matched ? s.focus.name : l.matched ? l.client : "";
  const boxes = [];
  const lines = [];
  let used = 0;
  let row = 0;
  const y = (r) => 20 + r * (BOX.h + BOX.gapY);
  const add = (box) => { boxes.push(box); return box; };
  const right = (b) => ({ x: b.x + b.w, y: b.y + b.h / 2 });
  const left = (b) => ({ x: b.x, y: b.y + b.h / 2 });
  // Label sits just above the target box, start-anchored at its left edge, so labels never stack.
  const link = (a, b, label, dir) => {
    const p = right(a);
    const q = left(b);
    lines.push({ x1: p.x, y1: p.y, x2: q.x, y2: q.y, label: clip(label, EDGE_MAX), dir, lx: b.x, ly: b.y - 4 });
  };
  const rows = [];
  if (s.matched) {
    for (const n of s.links.slice(0, MAX_DIRECT_BOXES)) {
      if (used + 1 > MAX_SANCTION_BOXES) break;
      const shown = Math.max(0, Math.min(n.groups.length, 2, MAX_SANCTION_BOXES - used - 1));
      rows.push({ n, groups: n.groups.slice(0, shown), at: row });
      used += 1 + shown;
      row += Math.max(1, shown);
    }
  }
  const firms = l.matched ? l.firms.slice(0, MAX_FIRM_BOXES) : [];
  const firmStart = row;
  row += firms.length;
  const total = Math.max(1, row);
  const focus = add({ x: COLS[0], y: y((total - 1) / 2), w: BOX.w - 40, h: BOX.h, kind: "focus", label: clip(focusName, LABEL_MAX), title: focusName, focus: true, schema: s.matched ? s.focus.schema : "Company" });
  for (const { n, groups, at } of rows) {
    const nb = add({ x: COLS[1], y: y(at + (Math.max(1, groups.length) - 1) / 2), w: BOX.w, h: BOX.h, kind: "link", label: clip(n.name, LABEL_MAX), title: n.name, focus: false, schema: n.schema });
    link(focus, nb, `${n.role} · ${auth(n.authorities)}`.toUpperCase(), n.direction === "in" ? "in" : "out");
    groups.forEach((g, i) => {
      const names = g.items.slice(0, 2).map((x) => x.name).join(" · ");
      const count = g.items.length + g.more;
      const gb = add({ x: COLS[2], y: y(at + i), w: BOX.w, h: BOX.h, kind: "group", label: clip(names, LABEL_MAX), title: `${count} ${plural(count, g.schema)}: ${g.items.map((x) => x.name).join(", ")}${g.more > 0 ? ` +${g.more}` : ""}`, focus: false, schema: g.schema, count });
      link(nb, gb, `${count} ${plural(count, g.schema)}`.toUpperCase(), groupDir(g));
    });
  }
  firms.forEach((f, i) => {
    const fb = add({ x: COLS[1], y: y(firmStart + i), w: BOX.w, h: BOX.h, kind: "firm", label: clip(f.name, LABEL_MAX), title: f.name, focus: false, schema: "Lobbying firm" });
    link(focus, fb, `HIRED · ${filingsText(f.filings).toUpperCase()}`, "out");
  });
  const width = COLS[2] + BOX.w + 20;
  const height = y(total) + 4;
  return { width, height, boxes, lines };
}

function renderSvg(data) {
  const g = layoutGraph(data);
  if (g.boxes.length < 2) return "";
  const summary = g.lines.map((ln) => ln.label).join("; ");
  const lines = g.lines.map((ln) => {
    const mx = (ln.x1 + ln.x2) / 2;
    const arrow = ln.dir === "in" ? ' marker-start="url(#conn-arrow)"' : ln.dir === "out" ? ' marker-end="url(#conn-arrow)"' : "";
    return `<path class="conn-edge" data-dir="${ln.dir || ""}"${arrow} d="M${ln.x1} ${ln.y1} C ${mx} ${ln.y1}, ${mx} ${ln.y2}, ${ln.x2} ${ln.y2}"/>` +
      `<text class="conn-edge-label" x="${ln.lx}" y="${ln.ly}" text-anchor="start">${escapeHtml(ln.label)}</text>`;
  }).join("");
  const boxes = g.boxes.map((b) => {
    const kind = b.kind === "group" ? `${b.count} ${plural(b.count, b.schema)}` : b.schema;
    return `<g class="conn-node${b.focus ? " is-focus" : ""}${b.kind === "firm" ? " is-firm" : ""}"><title>${escapeHtml(b.title)}</title>` +
      `<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="4"/>` +
      `<text class="conn-kind" x="${b.x + 12}" y="${b.y + 20}">${escapeHtml(String(kind).toUpperCase())}</text>` +
      `<text class="conn-label" x="${b.x + 12}" y="${b.y + 39}">${escapeHtml(b.label)}</text></g>`;
  }).join("");
  return `<svg class="conn-graph" viewBox="0 0 ${g.width} ${g.height}" width="100%" role="img" aria-label="${escapeHtml(summary)}"><defs><marker id="conn-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="conn-arrow" d="M0 0 L10 5 L0 10 z"/></marker></defs>${lines}${boxes}</svg>`;
}

const searchButton = (name, title) => `<button class="conn-name" type="button"${title ? ` title="${escapeHtml(title)}"` : ""} data-search="${escapeHtml(name)}">${escapeHtml(name)}</button>`;

function renderSanctions(s) {
  if (!s || s.available === false) {
    return `<div class="conn-block"><h3>Connections on the sanctions lists</h3><p class="conn-empty">Connections are unavailable right now. <button class="btn" type="button" data-retry="connections">Retry</button></p></div>`;
  }
  if (!s.matched || !s.links.length) {
    return `<div class="conn-block"><h3>Connections on the sanctions lists</h3><p class="conn-empty">No recorded connections on the sanctions lists.</p></div>`;
  }
  const focus = s.focus.name;
  const items = s.links.map((n) => {
    const groups = n.groups.map((g) => {
      const count = g.items.length + g.more;
      const role = sharedRole(g);
      const label = `${count} ${plural(count, g.schema)} linked to ${n.name}`;
      return `<div class="conn-group"><span class="conn-rel">${escapeHtml(label.toUpperCase())}${role ? ` · ${escapeHtml(role.toUpperCase())}` : ""}</span>` +
        `<div class="conn-chips">${g.items.map((x) => searchButton(x.name, `${x.role} · ${auth(x.authorities)}`)).join("")}${g.more ? `<span class="conn-more">+${escapeHtml(String(g.more))} more</span>` : ""}</div></div>`;
    }).join("");
    return `<li><span class="conn-rel">${escapeHtml(sentence(focus, n).toUpperCase())} · ${escapeHtml(auth(n.authorities))}</span>${searchButton(n.name)}${groups}</li>`;
  }).join("");
  const more = s.linksMore ? `<p class="conn-note">+${escapeHtml(String(s.linksMore))} more direct links on the lists.</p>` : "";
  const others = s.others ? `<p class="conn-note">${escapeHtml(String(s.others))} other list ${s.others === 1 ? "entry shares" : "entries share"} this name; showing the one with the most links.</p>` : "";
  return `<div class="conn-block"><h3>Connections on the sanctions lists</h3><p class="conn-lede">Who governments say is linked to ${escapeHtml(focus)}. Select a name to search it.</p><ul class="conn-list">${items}</ul>${more}${others}</div>`;
}

const section = (title, body) => (body ? `<h4>${title}</h4><ul class="conn-list">${body}</ul>` : "");

function renderLobbying(l) {
  const head = `<h3>Lobbying in Washington</h3>`;
  if (!l || l.available === false) {
    return `<div class="conn-block">${head}<p class="conn-empty">Lobbying data is unavailable right now. <button class="btn" type="button" data-retry="connections">Retry</button></p></div>`;
  }
  if (!l.matched) {
    const msg = l.checked_no_filings
      ? `No US lobbying filings found (checked nightly). ${NO_PROOF}`
      : `Lobbying is tracked for a list of companies named in sanctions research; this one is not on it. ${NO_PROOF}`;
    return `<div class="conn-block">${head}<p class="conn-empty">${escapeHtml(msg)}</p></div>`;
  }
  const parents = l.parents.map((p) => `<li>${escapeHtml(p.name)}${p.ownership_pct ? ` · ${escapeHtml(p.ownership_pct)}%` : ""}${p.note ? ` <span class="conn-meta">${escapeHtml(p.note)}</span>` : ""} <a href="${escapeHtml(safeUrl(p.url))}" rel="noopener">filing</a></li>`).join("");
  const bridges = l.bridges.map((b) => `<li>${escapeHtml(`${b.from} ${b.relation} ${b.to}`)} <span class="conn-meta">${escapeHtml(b.grade === "lead" ? "lead (our inference)" : b.grade)}${b.date ? ` · ${escapeHtml(b.date)}` : ""}</span>${b.source_url ? ` <a href="${escapeHtml(safeUrl(b.source_url))}" rel="noopener">source</a>` : ""}</li>`).join("");
  const tail = section("Foreign parent named on filings", parents) + section("Hand-checked links", bridges);
  if (l.checked_no_filings) {
    return `<div class="conn-block">${head}<p class="conn-empty">${escapeHtml(`No US lobbying filings found for ${l.client} (checked nightly). ${NO_PROOF}`)}</p>${tail}</div>`;
  }
  const firms = l.firms.map((f) => {
    const money = f.fees_usd ? ` · ${fmtMoney(f.fees_usd)}` : f.sub_fees_usd ? ` · ${fmtMoney(f.sub_fees_usd)} as subcontractor` : "";
    return `<li><a href="${escapeHtml(safeUrl(f.url))}" rel="noopener">${escapeHtml(f.name)}</a><span class="conn-meta">${escapeHtml(filingsText(f.filings))} · ${escapeHtml(years(f.years))}${escapeHtml(money)}</span></li>`;
  }).join("");
  const byFirm = new Map();
  for (const p of l.lobbyists) {
    const key = p.firm || "Other";
    if (!byFirm.has(key)) byFirm.set(key, []);
    byFirm.get(key).push(p);
  }
  const lobbyists = [...byFirm.entries()].map(([firm, people]) =>
    `<li><span class="conn-rel">${escapeHtml(firm.toUpperCase())}</span>${people.map((p) =>
      `<span class="conn-person">${escapeHtml(p.name)}${p.former_posts.length ? ` <span class="conn-meta">formerly ${escapeHtml(joinAnd(p.former_posts))}</span>` : ""}</span>`).join("")}</li>`).join("");
  const door = (l.revolving_door || []).map((d) => `<li>${escapeHtml(`${d.count} ${d.count === 1 ? "lobbyist" : "lobbyists"} previously served at the ${d.body}`)}</li>`).join("");
  const moreLobbyists = l.lobbyists_more > 0 ? `<p class="conn-note">+${escapeHtml(String(l.lobbyists_more))} more lobbyists in the filings.</p>` : "";
  const bodies = l.bodies.map((b) => `${escapeHtml(b.name)} (${escapeHtml(String(b.filings))})`).join(", ");
  const bills = l.bills.map((b) => `<li><b>${escapeHtml(b.label)}</b>${b.title ? ` <span class="conn-meta">${escapeHtml(b.title)}</span>` : ""} · ${escapeHtml(filingsText(b.filings))}</li>`).join("");
  return `<div class="conn-block">${head}<p class="conn-lede">${escapeHtml(`US lobbying filed for ${l.client}, as disclosed up to ${l.as_of}. Fees are self-reported and rounded.`)}</p>` +
    section("Firms hired", firms) +
    section("Revolving door", door) +
    section("Lobbyists (named in their own filings)", lobbyists) + moreLobbyists +
    (bodies ? `<h4>Lobbied</h4><p>${bodies}</p>` : "") +
    section("Bills and orders", bills) +
    tail +
    `</div>`;
}

export function renderConnections(data) {
  const svg = renderSvg(data);
  const note = `A listed link is a government finding; check the source before you publish. Lobbying is legal; filings describe disclosed activity. ${data.attribution || ""}`;
  return `<section class="conn" aria-label="Connections">${svg}${renderSanctions(data.sanctions)}${renderLobbying(data.lobbying)}<p class="conn-note">${escapeHtml(note)}</p></section>`;
}

export function renderConnectionsLoading() {
  return `<section class="conn"><p class="conn-empty">Loading connections…</p></section>`;
}
