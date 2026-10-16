import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { gzipSync } from "node:zlib";
import { createAssetLoader } from "../api/_asset.js";
import {
  GET, buildGraph, buildLobby, resolve, sanctionsFor, lobbyingFor, resetConnectionsCache,
  CONNECTIONS_URL, LOBBYING_URL, GROUP_CAP,
} from "../api/connections.js";

const T = "NK-k837moN9ssPZedvkRUrexG";
const ships = Array.from({ length: 25 }, (_, i) => [`S${i}`, "Vessel", [`SHIP ${i}`], "", ["US"]]);
const graphDoc = {
  updated_at: "2026-10-14T04:00:00Z",
  entities: [
    [T, "Vessel", ["TASSOS", "Tassos"], "9408695", ["US", "UK"]],
    ["Z", "Organization", ["Zulu Ships Management"], "", ["US", "UK"]],
    ["H", "Person", ["Hossein Shamkhani"], "", ["US"]],
    ["R", "Person", ["Relative Of Hossein"], "", ["US"]],
    ["SOV1", "Company", ["SOVCOMFLOT"], "", ["US"]],
    ["SOV2", "Company", ["SOVCOMFLOT"], "", ["UK"]],
    ...ships,
  ],
  links: [
    [T, "Z", "Ownership", "Property in the interest of", ["US", "UK"]],
    ...ships.map(([id]) => [id, "Z", "Ownership", "Property in the interest of", ["US"]]),
    ["Z", "H", "UnknownLink", "Providing support to", ["US"]],
    ["H", "R", "Family", "Family member of", ["US"]],
    ["SOV2", "Z", "UnknownLink", "Linked to", ["UK"]],
  ],
};
const lobbyDoc = {
  updated_at: "2026-10-14T04:00:00Z",
  filings_kept: 3, filings_scanned: 3, exclude_lobbyists: ["Hidden Person"],
  nodes: [
    { id: "co:nord-stream-2", type: "company", name: "Nord Stream 2 AG", lda_names: ["NORD STREAM 2 AG"] },
    { id: "lf:capitol-counsel", type: "lobbyfirm", name: "Capitol Counsel LLC" },
    { id: "p:jane-example", type: "person", name: "Jane Example", covered_positions: ["Legislative Assistant, Sen. Smith"] },
    { id: "p:hidden-person", type: "person", name: "Hidden Person" },
    { id: "gov:us-senate", type: "government", name: "US Senate" },
    { id: "bill:s722", type: "bill", name: "S.722", title: "S.722 Countering Iran's Destabilizing Activities Act (2017)" },
    { id: "co:gazprom", type: "company", name: "Gazprom" },
  ],
  edges: [
    { source: "co:nord-stream-2", target: "lf:capitol-counsel", type: "hired", n_filings: 12, amount: 1230000, years: [2017, 2022], source_url: "https://lda.gov/filings/public/filing/u1/print/" },
    { source: "p:jane-example", target: "lf:capitol-counsel", type: "lobbyist_at", n_filings: 4, years: [2017, 2018], source_url: "https://lda.gov/x" },
    { source: "p:jane-example", target: "co:nord-stream-2", type: "lobbied_for", n_filings: 4, years: [2017, 2018], source_url: "https://lda.gov/x" },
    { source: "p:hidden-person", target: "co:nord-stream-2", type: "lobbied_for", n_filings: 1, years: [2018, 2018], source_url: "https://lda.gov/x" },
    { source: "p:jane-example", target: "gov:us-senate", type: "formerly_served_in", n_filings: 4, years: [2017, 2018], source_url: "https://lda.gov/x" },
    { source: "lf:capitol-counsel", target: "gov:us-senate", type: "lobbied", client: "co:nord-stream-2", n_filings: 9, years: [2017, 2022], source_url: "https://lda.gov/x" },
    { source: "lf:capitol-counsel", target: "bill:s722", type: "lobbied_on", client: "co:nord-stream-2", n_filings: 5, years: [2017, 2018], source_url: "https://lda.gov/x" },
    { source: "co:gazprom", target: "co:nord-stream-2", type: "foreign_entity_of", n_filings: 3, texts: ["50% of NS2 operating budget"], ownership_pct: "50", years: [2017, 2019], source_url: "https://lda.gov/y" },
  ],
  bridges: {
    links: [{ from: "Gazprom", relation: "owns", to: "Gazprom Neft", grade: "documented", date: "2014-09-12", source_url: "https://home.treasury.gov/news/press-releases/jl2629" }],
    no_lobbying_found: ["Sovcomflot", "Zulu Ships Management"],
  },
};

const realFetch = globalThis.fetch;
let calls;
function serve({ graph = graphDoc, lobby = lobbyDoc, failGraph = false, failLobby = false } = {}) {
  globalThis.fetch = async (url) => {
    calls.push(url);
    if (url === CONNECTIONS_URL) return failGraph ? new Response("no", { status: 404 }) : new Response(gzipSync(JSON.stringify(graph)));
    if (url === LOBBYING_URL) return failLobby ? new Response("no", { status: 404 }) : new Response(gzipSync(JSON.stringify(lobby)));
    throw new Error("unexpected " + url);
  };
}
const get = (qs) => GET(new Request(`https://flagstate.test/api/connections?${qs}`));

beforeEach(() => { calls = []; resetConnectionsCache(); });
afterEach(() => { globalThis.fetch = realFetch; });

test("asset loader: shared fetch, refresh, stale on failure with backoff", async () => {
  let n = 0;
  const ok = async () => { n++; return new Response(gzipSync('{"v":1}')); };
  const bad = async () => { n++; return new Response("x", { status: 500 }); };
  const loader = createAssetLoader("https://x/a.gz", (doc) => doc.v);
  assert.deepEqual(await Promise.all([loader.load(ok, 0), loader.load(ok, 0)]), [1, 1]);
  assert.equal(n, 1);
  assert.equal(await loader.load(bad, 13 * 3600e3), 1);
  assert.equal(n, 2);
  assert.equal(await loader.load(bad, 13 * 3600e3 + 60e3), 1);
  assert.equal(n, 2);
  loader.reset();
  await assert.rejects(loader.load(bad, 0));
});

test("bad queries are rejected without loading data", async () => {
  serve();
  for (const qs of ["", "name=", "name=a", "name=%20A.%20", "imo=123", "name=" + "x".repeat(201)]) assert.equal((await get(qs)).status, 400);
  assert.equal(calls.length, 0);
});

test("TASSOS by IMO: Zulu with its other ships capped, and the person it supports", async () => {
  const s = sanctionsFor(buildGraph(graphDoc), { imo: "9408695" });
  assert.equal(s.matched, true);
  assert.deepEqual(s.focus, { name: "TASSOS", schema: "Vessel", imo: "9408695", authorities: ["US", "UK"] });
  const [zulu] = s.links;
  assert.equal(zulu.name, "Zulu Ships Management");
  assert.equal(zulu.direction, "out");
  assert.equal(zulu.role, "Property in the interest of");
  const vessels = zulu.groups.find((g) => g.schema === "Vessel");
  assert.equal(vessels.items.length, GROUP_CAP);
  assert.equal(vessels.more, 5);
  assert.ok(vessels.items.every((i) => i.name !== "TASSOS" && i.direction === "in"));
  const people = zulu.groups.find((g) => g.schema === "Person");
  assert.deepEqual(people.items.map((i) => [i.name, i.direction, i.role]), [["Hossein Shamkhani", "out", "Providing support to"]]);
});

test("no expansion from a person", () => {
  const s = sanctionsFor(buildGraph(graphDoc), { name: "Zulu Ships Management" });
  const hossein = s.links.find((l) => l.name === "Hossein Shamkhani");
  assert.deepEqual(hossein.groups, []);
});

test("shared names pick the best-linked entry and report the others", () => {
  const g = buildGraph(graphDoc);
  assert.deepEqual(resolve(g, { name: "sovcomflot" }), { id: "SOV2", others: 1 });
  assert.deepEqual(resolve(g, { name: "Nobody At All" }), null);
});

test("unknown names are matched: false, never fuzzy", () => {
  assert.deepEqual(sanctionsFor(buildGraph(graphDoc), { name: "TASSO" }), { available: true, matched: false });
});

test("lobbying view for Nord Stream 2", () => {
  const l = lobbyingFor(buildLobby(lobbyDoc), "Nord Stream 2 AG");
  assert.equal(l.matched, true);
  assert.equal(l.client, "Nord Stream 2 AG");
  assert.deepEqual(l.firms, [{ name: "Capitol Counsel LLC", filings: 12, fees_usd: 1230000, sub_fees_usd: null, subcontract: false, years: [2017, 2022], url: "https://lda.gov/filings/public/filing/u1/print/" }]);
  assert.deepEqual(l.lobbyists, [{ name: "Jane Example", firm: "Capitol Counsel LLC", former_posts: ["Legislative Assistant, Sen. Smith"], former_bodies: ["US Senate"] }]);
  assert.deepEqual(l.revolving_door, [{ body: "US Senate", count: 1 }]);
  assert.equal(l.lobbyists_more, 0);
  assert.deepEqual(l.bodies, [{ name: "US Senate", filings: 9 }]);
  assert.deepEqual(l.bills.map((b) => b.label), ["S.722"]);
  assert.deepEqual(l.parents, [{ name: "Gazprom", note: "50% of NS2 operating budget", ownership_pct: "50", url: "https://lda.gov/y" }]);
  assert.equal(l.bridges.length, 1);
  assert.equal(l.checked_no_filings, false);
});

test("lobbying: checked-no-filings list and untracked names", () => {
  const lob = buildLobby(lobbyDoc);
  assert.deepEqual(lobbyingFor(lob, "SOVCOMFLOT"), { available: true, matched: false, checked_no_filings: true });
  assert.deepEqual(lobbyingFor(lob, "Acme Widgets"), { available: true, matched: false, checked_no_filings: false });
});

test("GET: each asset fails alone, and a full answer is cached", async () => {
  serve({ failLobby: true });
  let res = await get("imo=9408695");
  let body = await res.json();
  assert.equal(body.sanctions.matched, true);
  assert.deepEqual(body.lobbying, { available: false });
  assert.equal(res.headers.get("cache-control"), "no-store");
  resetConnectionsCache();
  serve({ failGraph: true });
  body = await (await get("name=Nord%20Stream%202%20AG")).json();
  assert.deepEqual(body.sanctions, { available: false });
  assert.equal(body.lobbying.client, "Nord Stream 2 AG");
  resetConnectionsCache();
  serve();
  res = await get("imo=9408695");
  assert.equal(res.headers.get("cache-control"), "public, s-maxage=21600");
  body = await res.json();
  assert.match(body.attribution, /OpenSanctions/);
});

test("lobbyists and excluded names are never lobbying clients", () => {
  const lob = buildLobby(lobbyDoc);
  for (const n of ["Jane Example", "Hidden Person"]) assert.deepEqual(lobbyingFor(lob, n), { available: true, matched: false, checked_no_filings: false });
});

test("the link cap keeps people and companies ahead of ships", () => {
  const many = Array.from({ length: 25 }, (_, i) => [`V${i}`, "Vessel", [`V ${i}`], "", ["US"]]);
  const doc = {
    updated_at: "x",
    entities: [["F", "Vessel", ["FOCUS"], "9408695", ["US"]], ...many, ["P", "Person", ["Late Person"], "", ["US"]]],
    links: [...many.map(([id]) => ["F", id, "Ownership", "Owner of", ["US"]]), ["F", "P", "UnknownLink", "Run by", ["US"]]],
  };
  const s = sanctionsFor(buildGraph(doc), { imo: "9408695" });
  assert.equal(s.links.length, 20);
  assert.equal(s.links[0].name, "Late Person");
  assert.equal(s.linksMore, 6);
});

test("GET: a throw while reading a loaded asset degrades that section only", async () => {
  serve({ graph: { ...graphDoc, links: [...graphDoc.links, [T, "MISSING", "Ownership", "Owner of", ["US"]]] } });
  const res = await get("imo=9408695");
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.deepEqual(body.sanctions, { available: false });
  assert.equal(res.headers.get("cache-control"), "no-store");
});
