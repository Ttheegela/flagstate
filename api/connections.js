// Connections for one entity: sanctions links rebuilt nightly from the official lists via
// OpenSanctions (CC BY-NC 4.0), and US lobbying from LDA filings. Exact matching only.
// Never returns an error page: a section whose data cannot load answers {available:false}.
import { createAssetLoader } from "./_asset.js";
import { normalizeName, parseImo } from "../app/normalize.js";

const RELEASE = "https://github.com/Ttheegela/flagstate/releases/download/data-latest/";
export const CONNECTIONS_URL = `${RELEASE}connections.json.gz`;
export const LOBBYING_URL = `${RELEASE}lobbying.json.gz`;
export const GROUP_CAP = 20;
export const LINK_CAP = 20;
const LOBBYIST_CAP = 50;
const EXPANDABLE = new Set(["Organization", "Company", "LegalEntity"]);
const ATTRIBUTION = "Sanctions links: official sanctions lists compiled by OpenSanctions (CC BY-NC 4.0). Lobbying: US Lobbying Disclosure Act filings (lda.gov).";

function addTo(map, key, value) {
  if (!key) return;
  if (!map.has(key)) map.set(key, new Set());
  map.get(key).add(value);
}

export function buildGraph(doc) {
  if (!Array.isArray(doc.entities) || !Array.isArray(doc.links)) throw new Error("connections asset has no entities or links");
  const byId = new Map();
  const byImo = new Map();
  const byName = new Map();
  const adj = new Map();
  for (const [id, schema, names, imo, authorities] of doc.entities) {
    byId.set(id, { id, schema, name: names[0], imo, authorities });
    addTo(byImo, imo, id);
    for (const n of names) addTo(byName, normalizeName(n), id);
  }
  for (const [s, o, kind, role, authorities] of doc.links) {
    const link = { s, o, kind, role, authorities };
    for (const id of [s, o]) {
      if (!adj.has(id)) adj.set(id, []);
      adj.get(id).push(link);
    }
  }
  return { byId, byImo, byName, adj, updatedAt: doc.updated_at };
}

export function resolve(graph, { imo, name }) {
  const pool = imo ? graph.byImo.get(imo) : graph.byName.get(normalizeName(name || ""));
  if (!pool || !pool.size) return null;
  const degree = (id) => (graph.adj.get(id) || []).length;
  const ids = [...pool].sort((a, b) => degree(b) - degree(a) || a.localeCompare(b));
  return { id: ids[0], others: ids.length - 1 };
}

function neighbour(graph, link, fromId) {
  const out = link.s === fromId;
  const other = graph.byId.get(out ? link.o : link.s);
  return { id: other.id, name: other.name, schema: other.schema, role: link.role, direction: out ? "out" : "in", authorities: link.authorities };
}

function groupsFor(graph, n, focusId) {
  if (!EXPANDABLE.has(n.schema)) return [];
  const bySchema = new Map();
  for (const link of graph.adj.get(n.id) || []) {
    const m = neighbour(graph, link, n.id);
    if (m.id === focusId) continue;
    if (!bySchema.has(m.schema)) bySchema.set(m.schema, []);
    bySchema.get(m.schema).push(m);
  }
  return [...bySchema.entries()]
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
    .map(([schema, items]) => ({
      schema,
      items: items.slice(0, GROUP_CAP).map(({ name, schema: s, role, direction, authorities }) => ({ name, schema: s, role, direction, authorities })),
      more: Math.max(0, items.length - GROUP_CAP),
    }));
}

const isCraft = (n) => n.schema === "Vessel" || n.schema === "Airplane";

export function sanctionsFor(graph, query) {
  const hit = resolve(graph, query);
  if (!hit) return { available: true, matched: false };
  const focus = graph.byId.get(hit.id);
  const direct = (graph.adj.get(hit.id) || []).map((link) => neighbour(graph, link, hit.id));
  // people and organisations before ships and aircraft, so the cap never hides who is behind a vessel (stable sort)
  const ranked = [...direct].sort((a, b) => isCraft(a) - isCraft(b));
  const links = ranked.slice(0, LINK_CAP).map((n) => ({
    name: n.name, schema: n.schema, role: n.role, direction: n.direction, authorities: n.authorities,
    groups: groupsFor(graph, n, hit.id),
  }));
  return {
    available: true, matched: true,
    focus: { name: focus.name, schema: focus.schema, imo: focus.imo, authorities: focus.authorities },
    others: hit.others, links, linksMore: Math.max(0, direct.length - LINK_CAP),
  };
}

export function buildLobby(doc) {
  if (!Array.isArray(doc.nodes) || !Array.isArray(doc.edges)) throw new Error("lobbying asset has no nodes or edges");
  const nodes = new Map(doc.nodes.map((n) => [n.id, n]));
  const byName = new Map();
  for (const n of doc.nodes) {
    if (!["company", "association", "person"].includes(n.type)) continue;
    for (const name of [n.name, ...(n.lda_names || [])]) addTo(byName, normalizeName(name), n.id);
  }
  const from = new Map();
  const to = new Map();
  for (const e of doc.edges) {
    if (!from.has(e.source)) from.set(e.source, []);
    from.get(e.source).push(e);
    if (!to.has(e.target)) to.set(e.target, []);
    to.get(e.target).push(e);
  }
  const bridges = doc.bridges || { links: [], no_lobbying_found: [] };
  return {
    nodes, byName, from, to, asOf: (doc.updated_at || "").slice(0, 10),
    bridges: bridges.links || [],
    noLobbying: new Set((bridges.no_lobbying_found || []).map(normalizeName)),
    excluded: new Set((doc.exclude_lobbyists || []).map(normalizeName)),
  };
}

const firmEdge = (e) => e.type === "hired" || e.type === "lobbied_in_house";

export function lobbyingFor(lob, ...names) {
  const keys = names.filter(Boolean).map(normalizeName).filter(Boolean);
  const hiredCount = (id) => (lob.from.get(id) || []).filter(firmEdge).length;
  // lobbyists are people, not clients: skip excluded names and people who never hired a firm
  const ids = new Set(keys.flatMap((k) => [...(lob.byName.get(k) || [])]).filter((id) => {
    const n = lob.nodes.get(id);
    return !lob.excluded.has(normalizeName(n.name)) && !(n.type === "person" && hiredCount(id) === 0);
  }));
  const clientId = [...ids].sort((a, b) => hiredCount(b) - hiredCount(a) || a.localeCompare(b))[0];
  const checked = keys.some((k) => lob.noLobbying.has(k));
  if (!clientId) return { available: true, matched: false, checked_no_filings: checked };
  const node = (id) => lob.nodes.get(id) || { name: id };
  const out = lob.from.get(clientId) || [];
  const inc = lob.to.get(clientId) || [];
  const firms = out.filter(firmEdge).sort((a, b) => b.n_filings - a.n_filings).map((e) => ({
    name: e.target === clientId ? `${node(clientId).name} (in-house)` : node(e.target).name,
    filings: e.n_filings, fees_usd: e.amount ?? null, sub_fees_usd: e.sub_amount ?? null,
    subcontract: Boolean(e.subcontract), years: e.years || [], url: e.source_url,
  }));
  const firmIds = new Set(out.filter(firmEdge).map((e) => e.target));
  const allLobbyists = inc
    .filter((e) => e.type === "lobbied_for")
    .map((e) => node(e.source))
    .filter((p) => !lob.excluded.has(normalizeName(p.name)))
    .map((p) => {
      const pOut = lob.from.get(p.id) || [];
      const firm = pOut.find((e) => e.type === "lobbyist_at" && firmIds.has(e.target));
      return {
        name: p.name,
        firm: firm ? node(firm.target).name : "",
        former_posts: p.covered_positions || [],
        former_bodies: pOut.filter((e) => e.type === "formerly_served_in").map((e) => node(e.target).name),
      };
    });
  const lobbyists = allLobbyists.slice(0, LOBBYIST_CAP);
  // counted over every lobbyist, not just the ones shown
  const doors = new Map();
  for (const p of allLobbyists) for (const body of new Set(p.former_bodies)) doors.set(body, (doors.get(body) || 0) + 1);
  const revolving_door = [...doors].map(([body, count]) => ({ body, count })).sort((a, b) => b.count - a.count || a.body.localeCompare(b.body));
  const scoped = (type) => [...firmIds].flatMap((f) => (lob.from.get(f) || []).filter((e) => e.type === type && e.client === clientId));
  const bodies = scoped("lobbied").map((e) => ({ name: node(e.target).name, filings: e.n_filings })).sort((a, b) => b.filings - a.filings);
  const bills = scoped("lobbied_on").map((e) => ({ label: node(e.target).name, title: node(e.target).title || "", filings: e.n_filings })).sort((a, b) => b.filings - a.filings);
  const parentEdges = inc.filter((e) => e.type === "foreign_entity_of");
  const parents = parentEdges.map((e) => ({
    name: node(e.source).name, note: (e.texts || [])[0] || "", ownership_pct: e.ownership_pct || "", url: e.source_url,
  }));
  // a bridge matches the client or any of its foreign parents (e.g. Gazprom owns Gazprom Neft, for Nord Stream 2)
  const clientKeys = new Set([normalizeName(node(clientId).name), ...keys, ...parentEdges.map((e) => normalizeName(node(e.source).name))]);
  const bridges = lob.bridges
    .filter((b) => clientKeys.has(normalizeName(b.from)) || clientKeys.has(normalizeName(b.to)))
    .map(({ from, relation, to, grade, date, source_url }) => ({ from, relation, to, grade, date, source_url }));
  return {
    available: true, matched: true, client: node(clientId).name, as_of: lob.asOf,
    checked_no_filings: firms.length === 0,
    firms, lobbyists, lobbyists_more: allLobbyists.length - lobbyists.length, revolving_door, bodies, bills, parents, bridges,
  };
}

const graphAsset = createAssetLoader(CONNECTIONS_URL, buildGraph);
const lobbyAsset = createAssetLoader(LOBBYING_URL, buildLobby);

export function resetConnectionsCache() {
  graphAsset.reset();
  lobbyAsset.reset();
}

function json(body, { status = 200, cache = false } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": cache ? "public, s-maxage=21600" : "no-store" },
  });
}

export async function GET(request) {
  const params = new URL(request.url).searchParams;
  const rawImo = (params.get("imo") || "").trim();
  const imo = rawImo ? parseImo(rawImo) : null;
  const name = (params.get("name") || "").trim();
  if ((rawImo && !imo) || (!imo && normalizeName(name).length < 2) || name.length > 200) return json({ error: "bad query" }, { status: 400 });
  const [graph, lobby] = await Promise.allSettled([graphAsset.load(), lobbyAsset.load()]);
  const safe = (settled, fn) => {
    if (settled.status !== "fulfilled") return { available: false };
    try { return fn(settled.value); } catch (err) { console.error("connections: section failed", err); return { available: false }; }
  };
  const sanctions = safe(graph, (g) => sanctionsFor(g, { imo, name }));
  const lobbying = safe(lobby, (l) => lobbyingFor(l, name, sanctions.focus?.name));
  const complete = sanctions.available && lobbying.available;
  return json({ query: imo || name, sanctions, lobbying, attribution: ATTRIBUTION }, { cache: complete });
}
