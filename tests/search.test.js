import { test } from "node:test";
import assert from "node:assert/strict";
import { prepareQuery, scoreName, searchResearch, searchLists, latestOnly, listStatus, loadJson, LIMIT } from "../app/search.js";

const entry = (id, name, keys, imo = null) => ({ id, name, keys, imo, listings: [] });
const ENTRIES = [
  entry("IMO9408695", "TASSOS", ["TASSOS", "FRONT BALDER", "SEASALVIA"], "9408695"),
  entry("co:sovcomflot", "SOVCOMFLOT", ["SOVCOMFLOT"]),
  entry("co:sterling", "SOVCOMFLOT/STERLING SHIP MANAGEMENT", ["SOVCOMFLOT STERLING SHIP MANAGEMENT"]),
  entry("IMO1", "TASSOS STAR", ["TASSOS STAR"], "1111111"),
];

test("prepareQuery: names, IMO shapes and unusable input", () => {
  assert.deepEqual(prepareQuery("  Sovcomflot PJSC "), { text: "Sovcomflot PJSC", imo: null, norm: "SOVCOMFLOT", tokens: ["SOVCOMFLOT"], usable: true });
  for (const raw of ["9408695", "IMO 9408695", "imo9408695", " 9408695 "]) assert.equal(prepareQuery(raw).imo, "9408695");
  for (const raw of ["Совкомфлот", "LLC", "...", ""]) assert.equal(prepareQuery(raw).usable, false);
});

test("scoreName: exact 3, all words 2, most words 1, last word may be a prefix", () => {
  const q = prepareQuery("Sovcomflot");
  assert.equal(scoreName(q, "SOVCOMFLOT"), 3);
  assert.equal(scoreName(q, "SOVCOMFLOT STERLING SHIP MANAGEMENT"), 2);
  assert.equal(scoreName(prepareQuery("Sovcomflot Sterling Holdings"), "SOVCOMFLOT STERLING SHIP MANAGEMENT"), 1);
  assert.equal(scoreName(prepareQuery("Sovcomfl"), "SOVCOMFLOT"), 2);
  assert.equal(scoreName(prepareQuery("Tanker"), "SOVCOMFLOT"), 0);
});

test("searchResearch: exact first, former names match, IMO is exact", () => {
  assert.deepEqual(searchResearch(ENTRIES, prepareQuery("Sovcomflot")).map((e) => e.id), ["co:sovcomflot", "co:sterling"]);
  assert.deepEqual(searchResearch(ENTRIES, prepareQuery("front balder")).map((e) => e.id), ["IMO9408695"]);
  assert.deepEqual(searchResearch(ENTRIES, prepareQuery("TASSOS")).map((e) => e.id), ["IMO9408695", "IMO1"]);
  assert.deepEqual(searchResearch(ENTRIES, prepareQuery("IMO 9408695")).map((e) => e.id), ["IMO9408695"]);
  assert.deepEqual(searchResearch(ENTRIES, prepareQuery("LLC")), []);
});

test("searchResearch and searchLists cap common words at LIMIT, best first", () => {
  const many = Array.from({ length: 500 }, (_, i) => entry(`e${i}`, `ALPHA SHIPPING ${i}`, [`ALPHA SHIPPING ${i}`]));
  many.push(entry("exact", "SHIPPING", ["SHIPPING"]));
  const hits = searchResearch(many, prepareQuery("shipping"));
  assert.equal(hits.length, LIMIT);
  assert.equal(hits[0].id, "exact");

  const records = Array.from({ length: 500 }, (_, i) => [`Beta Trading ${i}`, `BETA TRADING ${i}`, "Iran", "", `r${i}`, "", ""]);
  assert.equal(searchLists({ us: { records } }, prepareQuery("trading")).length, LIMIT);
});

test("searchLists: one row per listed entity, IMO matches, fields mapped", () => {
  const docs = {
    us: { records: [["TASSOS", "TASSOS", "Iran", "", "54815", "9408695", ""]] },
    uk: { records: [
      ["TASSOS", "TASSOS", "Russia", "2026-02-24", "RUS3483", "9408695", ""],
      ["Tassos", "TASSOS", "Russia", "2026-02-24", "RUS3483", "9408695", ""],
    ] },
  };
  const hits = searchLists(docs, prepareQuery("tassos"));
  assert.deepEqual(hits.map((h) => h.list).sort(), ["uk", "us"]);
  assert.deepEqual(searchLists(docs, prepareQuery("9408695")).length, 2);
  const refless = { uk: { records: [["TASSOS ONE", "TASSOS ONE", "Iran", "", "", "", ""], ["TASSOS TWO", "TASSOS TWO", "Iran", "", "", "", ""]] } };
  assert.deepEqual(searchLists(refless, prepareQuery("tassos")).map((h) => h.name).sort(), ["TASSOS ONE", "TASSOS TWO"]);
  assert.deepEqual(hits.find((h) => h.list === "uk"), { list: "uk", name: "TASSOS", program: "Russia", date: "2026-02-24", ref: "RUS3483", imo: "9408695", url: "" });
});

test("latestOnly: an older ticket stops being latest", () => {
  const next = latestOnly();
  const first = next();
  const second = next();
  assert.equal(first(), false);
  assert.equal(second(), true);
});

test("listStatus: newest time, stale when old or kept-previous", () => {
  const now = new Date("2026-10-13T12:00:00Z");
  const fresh = { label: "United States", status: "fresh", updated_at: "2026-10-13T04:00:00Z" };
  assert.equal(listStatus({ lists: { us: fresh } }, now).stale, false);
  assert.equal(listStatus({ lists: { us: fresh } }, now).newest.toISOString(), "2026-10-13T04:00:00.000Z");
  assert.equal(listStatus({ lists: { us: { ...fresh, updated_at: "2026-10-09T04:00:00Z" } } }, now).stale, true);
  const kept = listStatus({ lists: { us: fresh, uk: { label: "United Kingdom", status: "kept-previous", updated_at: "2026-10-12T04:00:00Z" } } }, now);
  assert.equal(kept.stale, true);
  assert.match(kept.details.join("\n"), /United Kingdom: 2026-10-12 \(kept previous copy\)/);
  assert.deepEqual(listStatus(null, now), { newest: null, stale: true, details: [] });
  const bad = listStatus({ lists: { us: { label: "United States", status: "fresh", updated_at: "not a date" } } }, now);
  assert.equal(bad.stale, true);
  assert.equal(bad.newest, null);
});

test("loadJson throws on HTTP errors", async () => {
  const fake = async () => ({ ok: false, status: 404, json: async () => ({}) });
  await assert.rejects(loadJson("data/x.json", fake), /404/);
});
