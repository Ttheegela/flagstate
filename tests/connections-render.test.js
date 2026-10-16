import { test } from "node:test";
import assert from "node:assert/strict";
import { connectionsQuery, sentence, layoutGraph, renderConnections, renderConnectionsLoading } from "../app/connections.js";

const tassos = {
  sanctions: {
    available: true, matched: true, others: 0, linksMore: 0,
    focus: { name: "TASSOS", schema: "Vessel", imo: "9408695", authorities: ["US", "UK"] },
    links: [{
      name: "Zulu Ships Management", schema: "Organization", role: "Property in the interest of", direction: "out", authorities: ["US", "UK"],
      groups: [
        { schema: "Vessel", items: ["TAGOR", "NEMRUT", "MANASLU"].map((n) => ({ name: n, schema: "Vessel", role: "Property in the interest of", direction: "in", authorities: ["US", "UK"] })), more: 7 },
        { schema: "Person", items: [{ name: "Hossein Shamkhani", schema: "Person", role: "Providing support to", direction: "out", authorities: ["US"] }], more: 0 },
      ],
    }],
  },
  lobbying: { available: true, matched: false, checked_no_filings: true },
  attribution: "Sanctions links: official sanctions lists compiled by OpenSanctions (CC BY-NC 4.0).",
};

const ns2 = {
  sanctions: { available: true, matched: false },
  lobbying: {
    available: true, matched: true, client: "Nord Stream 2 AG", as_of: "2026-10-14", checked_no_filings: false,
    firms: [{ name: "Capitol Counsel LLC", filings: 12, fees_usd: 1230000, sub_fees_usd: null, subcontract: false, years: [2017, 2022], url: "https://lda.gov/filings/public/filing/u1/print/" }],
    lobbyists: [{ name: "Jane Example", firm: "Capitol Counsel LLC", former_posts: ["Legislative Assistant, Sen. Smith"], former_bodies: ["US Senate"] },
                { name: "John Sample", firm: "Capitol Counsel LLC", former_posts: [], former_bodies: [] }],
    lobbyists_more: 3, revolving_door: [{ body: "US Senate", count: 1 }],
    bodies: [{ name: "US Senate", filings: 9 }],
    bills: [{ label: "S.722", title: "S.722 Countering Iran's Destabilizing Activities Act (2017)", filings: 5 }],
    parents: [{ name: "Gazprom", note: "50% of NS2 operating budget", ownership_pct: "50", url: "https://lda.gov/y" }],
    bridges: [{ from: "Gazprom", relation: "owns", to: "Gazprom Neft", grade: "documented", date: "2014-09-12", source_url: "https://home.treasury.gov/news/press-releases/jl2629" }],
  },
  attribution: "Lobbying: US Lobbying Disclosure Act filings (lda.gov).",
};

test("query string per entry", () => {
  assert.equal(connectionsQuery({ imo: "9408695", name: "TASSOS" }), "imo=9408695");
  assert.equal(connectionsQuery({ imo: null, name: "Nord Stream 2 AG" }), "name=Nord%20Stream%202%20AG");
});

test("sentences read in the list's direction", () => {
  assert.equal(sentence("TASSOS", tassos.sanctions.links[0]), "TASSOS property in the interest of Zulu Ships Management");
  assert.equal(sentence("Zulu Ships Management", { name: "TAGOR", role: "Property in the interest of", direction: "in" }), "TAGOR property in the interest of Zulu Ships Management");
});

test("layout: focus plus at most 8 sanctions boxes, collapsed groups, lobbying firms", () => {
  const many = { ...tassos, sanctions: { ...tassos.sanctions, links: Array.from({ length: 12 }, (_, i) => ({ ...tassos.sanctions.links[0], name: `Company ${i}` })) } };
  const g = layoutGraph(many);
  assert.ok(g.boxes.filter((b) => !b.focus && b.kind !== "firm").length <= 8);
  assert.ok(g.boxes.some((b) => b.focus && b.label === "TASSOS"));
  const one = layoutGraph(tassos);
  assert.ok(one.boxes.some((b) => b.label.includes("TAGOR") && b.kind === "group" && b.title.includes("+7")));
  const firms = layoutGraph({ ...ns2, sanctions: { available: true, matched: true, others: 0, linksMore: 0, focus: { name: "Nord Stream 2 AG", schema: "Company", imo: "", authorities: [] }, links: [] } });
  assert.ok(firms.boxes.some((b) => b.kind === "firm" && b.label === "Capitol Counsel LLC"));
});

test("TASSOS panel: graph, list with searchable names, more count, no-lobbying note", () => {
  const html = renderConnections(tassos);
  assert.match(html, /class="conn-graph"/);
  assert.match(html, /data-search="Zulu Ships Management"/);
  assert.match(html, /data-search="TAGOR"/);
  assert.match(html, /\+7 more/);
  assert.match(html, /US, UK/);
  assert.match(html, /No US lobbying filings found \(checked nightly\)/);
  assert.match(html, /not proof of no influence/);
});

test("Nord Stream 2 panel: firms, lobbyists with former posts, revolving door, bodies, bills, parents, bridges", () => {
  const html = renderConnections(ns2);
  assert.match(html, /Lobbying in Washington/);
  assert.match(html, /Capitol Counsel LLC/);
  assert.match(html, /12 filings/);
  assert.match(html, /\$1\.23M/);
  assert.match(html, /self-reported/);
  assert.match(html, /Jane Example/);
  assert.match(html, /Legislative Assistant, Sen\. Smith/);
  assert.match(html, /1 lobbyist previously served at the US Senate/);
  assert.match(html, /\+3 more lobbyists in the filings\./);
  assert.match(html, /S\.722/);
  assert.match(html, /Gazprom/);
  assert.match(html, /home\.treasury\.gov/);
  assert.match(html, /No recorded connections on the sanctions lists/);
});

test("unavailable sections offer retry; untracked lobbying shows a coverage note", () => {
  const html = renderConnections({ sanctions: { available: false }, lobbying: { available: true, matched: false, checked_no_filings: false }, attribution: "" });
  assert.match(html, /Connections are unavailable right now/);
  assert.match(html, /data-retry="connections"/);
  assert.match(html, /Lobbying is tracked for a list of companies/);
  assert.match(html, /this one is not on it\. No filing found is not proof of no influence\./);
  assert.match(renderConnectionsLoading(), /Loading connections/);
});

test("hostile names are escaped everywhere, long names truncated in boxes", () => {
  const evil = `<img src=x onerror=alert(1)>"'${"x".repeat(80)}`;
  const data = JSON.parse(JSON.stringify(tassos));
  data.sanctions.focus.name = evil;
  data.sanctions.links[0].name = evil;
  const html = renderConnections(data);
  assert.ok(!html.includes("<img"));
  assert.ok(!/data-search="[^"]*"[^ >]*"/.test(html));
  const g = layoutGraph(data);
  assert.ok(g.boxes.every((b) => b.label.length <= 26));
});

const grp = (n) => ({ schema: "Vessel", items: Array.from({ length: n }, (_, i) => ({ name: `V${n}-${i}`, schema: "Vessel", role: "Property in the interest of", direction: "in", authorities: ["US"] })), more: 0 });
const link = (name, groups) => ({ name, schema: "Organization", role: "Property in the interest of", direction: "out", authorities: ["US"], groups });

test("at most 8 sanctions boxes even when rows run out of room", () => {
  const data = { ...tassos, sanctions: { ...tassos.sanctions, links: [link("A", [grp(1), grp(1)]), link("B", [grp(1), grp(1)]), link("C", []), link("D", [grp(1), grp(1)])] } };
  const g = layoutGraph(data);
  assert.ok(g.boxes.filter((b) => !b.focus && b.kind !== "firm").length <= 8);
});

test("edge labels are placed at distinct positions above their target boxes", () => {
  const firm = (i) => ({ name: `Firm ${i}`, filings: 1, fees_usd: 0, sub_fees_usd: null, subcontract: false, years: [2020, 2020], url: "https://lda.gov/x" });
  const g = layoutGraph({ ...ns2, sanctions: { available: true, matched: false }, lobbying: { ...ns2.lobbying, firms: [1, 2, 3, 4].map(firm) } });
  assert.equal(g.lines.length, 4);
  assert.equal(new Set(g.lines.map((ln) => `${ln.lx},${ln.ly}`)).size, 4);
  for (const ln of g.lines) assert.ok(ln.label.length <= 30);
  for (const b of g.boxes) assert.ok(b.y >= 0);
  assert.ok(g.height >= Math.max(...g.boxes.map((b) => b.y + b.h)));
});

test("numbers from data are escaped and singular filings read correctly", () => {
  const hostile = JSON.parse(JSON.stringify(ns2));
  hostile.lobbying.bodies[0].filings = "<i>x";
  hostile.lobbying.firms[0].filings = 1;
  hostile.lobbying.bills[0].filings = 1;
  const html = renderConnections(hostile);
  assert.ok(!html.includes("<i>x"));
  assert.match(html, /1 filing · /);
  assert.ok(!/1 filings/.test(html));
  assert.match(renderConnections(hostile), /HIRED/);
});

test("matched client with no filings still shows parents and bridges", () => {
  const html = renderConnections({ sanctions: { available: true, matched: false }, lobbying: { ...ns2.lobbying, checked_no_filings: true, firms: [], lobbyists: [], bodies: [], bills: [] }, attribution: "" });
  assert.match(html, /No US lobbying filings found for Nord Stream 2 AG/);
  assert.match(html, /Gazprom/);
  assert.match(html, /home\.treasury\.gov/);
});

test("sentence keeps acronym roles and lower-cases ordinary ones", () => {
  assert.equal(sentence("X", { name: "Y", role: "OFAC designated", direction: "out" }), "X OFAC designated Y");
  assert.equal(sentence("X", { name: "Y", role: "Property in the interest of", direction: "out" }), "X property in the interest of Y");
});

test("edges carry direction: arrowhead points at the object of the sentence", () => {
  const dirs = layoutGraph(tassos).lines.map((l) => l.dir);
  assert.deepEqual(dirs, ["out", "in", "out"]); // focus -> Zulu; ships -> Zulu; Zulu -> person
  const mixedGroup = JSON.parse(JSON.stringify(tassos));
  mixedGroup.sanctions.links[0].groups[0].items[1].direction = "out";
  assert.equal(layoutGraph(mixedGroup).lines[1].dir, null);
  assert.ok(!/data-dir="" marker/.test(renderConnections(mixedGroup)));
  const inOnly = JSON.parse(JSON.stringify(tassos));
  inOnly.sanctions.links[0].direction = "in";
  inOnly.sanctions.links[0].groups.pop();
  const g = layoutGraph(inOnly);
  assert.deepEqual(g.lines.map((l) => l.dir), ["in", "in"]);
  const svg = renderConnections(inOnly);
  assert.match(svg, /<path class="conn-edge" data-dir="in" marker-start="url\(#conn-arrow\)"/);
  assert.ok(!/data-dir="in" marker-end/.test(svg));
  assert.match(renderConnections(tassos), /data-dir="out" marker-end="url\(#conn-arrow\)"/);
  assert.match(renderConnections(tassos), /<marker id="conn-arrow"/);
  const firm = layoutGraph(ns2).lines;
  assert.equal(firm[0].dir, "out");
});

test("group role printed only when every item shares it; singular labels; chip titles", () => {
  const mixed = JSON.parse(JSON.stringify(tassos));
  mixed.sanctions.links[0].groups[0].items[1].role = "Owned by";
  const html = renderConnections(mixed);
  assert.match(html, /10 SHIPS LINKED TO ZULU SHIPS MANAGEMENT<\/span>/);
  assert.match(html, /1 PERSON LINKED TO ZULU SHIPS MANAGEMENT · PROVIDING SUPPORT TO<\/span>/);
  assert.match(html, /title="Providing support to · US"/);
  const same = JSON.parse(JSON.stringify(tassos));
  same.sanctions.links[0].groups.pop();
  assert.match(renderConnections(same), /10 SHIPS LINKED TO ZULU SHIPS MANAGEMENT · PROPERTY IN THE INTEREST OF/);
  const one = JSON.parse(JSON.stringify(same));
  one.sanctions.links[0].groups[0] = { ...one.sanctions.links[0].groups[0], items: [one.sanctions.links[0].groups[0].items[0]], more: 0 };
  assert.match(renderConnections(one), /1 SHIP LINKED TO/);
  assert.ok(layoutGraph(one).lines.some((l) => l.label === "1 SHIP"));
});
