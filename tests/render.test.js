import { test } from "node:test";
import assert from "node:assert/strict";
import {
  escapeHtml, safeUrl, formatDate, formatUpdated, timelinePositions, citation,
  renderDossier, renderResearch, renderLists, recordLink, renderWider, renderEmpty, renderHint, medianMonths,
} from "../app/render.js";

const TASSOS = {
  id: "IMO9408695", kind: "Oil Tanker", name: "TASSOS", keys: ["TASSOS"], imo: "9408695", flag: "Liberia",
  manager: "Zulu Ships", country: null, role: null,
  listings: [
    { by: "United States", date: "2025-07-30", program: "Iran", ref: 1 },
    { by: "European Union", date: "2025-10-24", program: "Russia", ref: 2 },
    { by: "United Kingdom", date: "2026-02-24", program: "Russia", ref: 3 },
  ],
  events: [
    { date: "2023-02", kind: "ownership", text: "Sold by Frontline to an unlisted ship manager (Liberia)" },
    { date: "2024-09-09", kind: "management", text: "Managed by Zulu Ships" },
    { date: "2025-07-30", kind: "listing", text: "United States lists it (Iran)" },
    { date: "2025-10-24", kind: "listing", text: "European Union lists it (Russia)" },
    { date: "2026-02-24", kind: "listing", text: "United Kingdom lists it (Russia)" },
  ],
  facts: [{ text: "Listed by the United States on 30 July 2025 (Iran).", refs: [1, 2, 3] }],
  names: [{ name: "TASSOS", current: true }, { name: "Front Balder", current: false }],
  flags: ["Liberia", "Panama"],
  story: { label: "Open on the shadow-fleet map", url: "stories/shadow-fleet/network/shadow_fleet_map.html" },
  sources: [
    { n: 1, label: "US Treasury OFAC sanctions list", url: "https://sanctionslist.ofac.treas.gov/Home/SdnList" },
    { n: 2, label: "EU Official Journal (EUR-Lex)", url: "https://eur-lex.europa.eu/eli/reg/2014/833/oj" },
    { n: 3, label: "UK Sanctions List", url: "https://www.gov.uk/government/publications/the-uk-sanctions-list" },
  ],
};

test("escapeHtml and safeUrl neutralise hostile data", () => {
  assert.equal(escapeHtml(`<script>"x"&'y'</script>`), "&lt;script&gt;&quot;x&quot;&amp;&#39;y&#39;&lt;/script&gt;");
  assert.equal(safeUrl("javascript:alert(1)"), "#");
  assert.equal(safeUrl("data:text/html,hi"), "#");
  assert.equal(safeUrl("https://www.gov.uk/x"), "https://www.gov.uk/x");
  assert.equal(safeUrl("stories/shadow-fleet/FINDINGS.md"), "stories/shadow-fleet/FINDINGS.md");
});

test("dossier escapes names and drops javascript links", () => {
  const evil = { ...TASSOS, name: `<img src=x onerror=alert(1)>`, sources: [{ n: 1, label: "<b>x</b>", url: "javascript:alert(1)" }] };
  const html = renderDossier(evil);
  assert.ok(!html.includes("<img"));
  assert.ok(!html.includes("javascript:"));
  assert.ok(html.includes("&lt;img"));
});

test("formatDate and formatUpdated", () => {
  assert.equal(formatDate("2025-07-30"), "30 Jul 2025");
  assert.equal(formatDate("2025-07-30", true), "30 July 2025");
  assert.equal(formatDate("2023-02"), "Feb 2023");
  assert.equal(formatDate("n/a"), "");
  assert.equal(formatUpdated(new Date("2026-10-13T04:00:00Z")), "13 Oct 2026, 04:00 UTC");
});

test("timelinePositions: ordered, start at 0, end at most 86, no overlaps", () => {
  const pos = timelinePositions(TASSOS.events);
  assert.equal(pos.length, 5);
  assert.equal(pos[0].pct, 0);
  assert.ok(pos.at(-1).pct <= 86);
  for (let i = 1; i < pos.length; i++) assert.ok(pos[i].pct - pos[i - 1].pct >= 13.9, `gap before ${i}`);
});

test("timeline prints every event label in full", () => {
  const long = "Owned by an unlisted United Arab Emirates ship owner c/o the Zulu Ships Management & Operation - Sole Proprietorship LLC";
  const html = renderDossier({ ...TASSOS, events: [...TASSOS.events, { date: "2024-10-10", kind: "ownership", text: long }] });
  assert.ok(html.includes(`<span class="what">${long.replace("&", "&amp;")}</span>`));
  assert.ok(!html.includes("…"));
  assert.match(html, /<button type="button" class="tl-more" aria-expanded="false" hidden>Show full text<\/button>/);
});

test("citation text", () => {
  assert.equal(
    citation(TASSOS, "https://flagstate.vercel.app/", new Date("2026-10-13T10:00:00Z")),
    "TASSOS (IMO 9408695): listed by the United States on 30 July 2025 (Iran), the European Union on 24 October 2025 (Russia) and the United Kingdom on 24 February 2026 (Russia). " +
    "Sources: https://sanctionslist.ofac.treas.gov/Home/SdnList ; https://eur-lex.europa.eu/eli/reg/2014/833/oj ; https://www.gov.uk/government/publications/the-uk-sanctions-list. " +
    "Via Flagstate, https://flagstate.vercel.app/, accessed 13 October 2026.",
  );
});

test("dossier has the hooks the walkthrough and copy button use", () => {
  const html = renderDossier(TASSOS);
  for (const hook of ['data-walk="chips"', 'data-walk="timeline"', 'data-walk="names"', 'data-walk="sources"', 'data-cite="IMO9408695"']) {
    assert.ok(html.includes(hook), hook);
  }
  assert.equal((html.match(/class="chip"/g) || []).length, 3);
});

test("research: first in full, others collapsed", () => {
  const html = renderResearch([TASSOS, { ...TASSOS, id: "IMO1", name: "TASSOS STAR" }]);
  assert.match(html, /In our research · 2 matches/);
  assert.equal((html.match(/<details class="more">/g) || []).length, 1);
});

test("list hits link to the official entry where one exists", () => {
  assert.deepEqual(recordLink({ list: "us", ref: "54815" }), { url: "https://sanctionssearch.ofac.treas.gov/Details.aspx?id=54815", text: "Record" });
  assert.deepEqual(recordLink({ list: "uk", ref: "RUS3483" }), { url: "https://search-uk-sanctions-list.service.gov.uk/?searchValue=RUS3483", text: "Record" });
  assert.equal(recordLink({ list: "eu", ref: "1", url: "https://eur-lex.europa.eu/x" }).text, "Legal act");
  assert.deepEqual(recordLink({ list: "us", ref: "1d0250ee07264881a780d52291d13f77" }), { url: "https://www.trade.gov/consolidated-screening-list", text: "List home" });
  assert.equal(recordLink({ list: "un", ref: "CDe.001" }).text, "List home");
});

test("lists table, failures and empty states", () => {
  const hit = { list: "uk", name: "TASSOS", program: "Russia", date: "2026-02-24", ref: "RUS3483", imo: "9408695", url: "" };
  const html = renderLists([hit], ["eu"]);
  assert.match(html, /United Kingdom/);
  assert.match(html, /Couldn't load the European Union list/);
  assert.match(html, /data-retry="lists"/);
  assert.match(renderLists([], []), /No match on the official lists/);
  assert.match(renderEmpty("Qzxv"), /Not found in our research or on the official lists/);
  assert.match(renderHint(), /Latin letters/);
});

test("wider check states", () => {
  assert.match(renderWider({ kind: "link" }, "TASSOS"), /opensanctions\.org\/search\/\?q=TASSOS/);
  assert.match(renderWider({ kind: "error" }, "TASSOS"), /unavailable right now/);
  const results = renderWider({ kind: "results", results: [{ name: "<x>", schema: "Vessel", datasets: ["us_ofac_sdn"], url: "https://www.opensanctions.org/entities/abc/" }] }, "TASSOS");
  assert.match(results, /&lt;x&gt;/);
  assert.match(results, /CC BY-NC 4.0/);
});

test("wider check shows every listing authority", () => {
  const html = renderWider({ kind: "results", results: [{ name: "TASSOS", schema: "Vessel", datasets: ["Canada", "EU", "UK", "Switzerland", "US"], url: "https://www.opensanctions.org/entities/NK-k837moN9ssPZedvkRUrexG/" }] }, "TASSOS");
  assert.match(html, /Vessel · Canada, EU, UK, Switzerland, US/);
});

test("medianMonths rounds to whole months and rejects bad input", () => {
  assert.equal(medianMonths({ median_months: 20.3, n: 25 }), 20);
  assert.equal(medianMonths({ median_months: 20.6 }), 21);
  for (const bad of [null, {}, { median_months: "20" }, { median_months: NaN }, { median_months: 0 }]) assert.equal(medianMonths(bad), null);
});
