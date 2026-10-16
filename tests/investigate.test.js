import { test } from "node:test";
import assert from "node:assert/strict";
import { httpUrl, agentBase, renderStartButton, renderSteps, renderChanges, renderFlags, evalLine, renderBriefing, renderJob } from "../app/investigate.js";

const DONE = {
  status: "done",
  steps: [
    { name: "lookup", status: "done", detail: "3 list hits", ms: 41 },
    { name: "browse", status: "done", ms: 18234.6 },
    { name: "eval", status: "done", ms: 900 },
  ],
  result: {
    live: { facts: { flag: "Cameroon" }, sources: ["https://www.marinetraffic.com/x"], live_view_url: "https://live.anchorbrowser.io/s/1" },
    changes: [{ field: "flag", old: "Panama", new: "Cameroon", old_observed_at: "2026-10-01" }],
    flags: [{ flag: "Flag hop", severity: "high", evidence: "Panama to Cameroon", source: "https://www.marinetraffic.com/x" }],
    briefing: { text: "TASSOS changed flag.", claims: [
      { text: "Flag is Cameroon", source: "https://www.marinetraffic.com/x" },
      { text: "Listed by the UK", source: "javascript:alert(1)" },
    ] },
    eval: { name: "sourced", score: 0.5, label: "partial", explanation: "One claim lacks a URL." },
    trace_url: "https://app.arize.com/trace/1",
    sandbox: { ran_in: "daytona", sandbox_id: "sb-123" },
  },
};

test("httpUrl only allows absolute http(s)", () => {
  assert.equal(httpUrl("https://a.example/x"), "https://a.example/x");
  assert.equal(httpUrl("javascript:alert(1)"), "");
  assert.equal(httpUrl("data:text/html,hi"), "");
  assert.equal(httpUrl("/relative"), "");
  assert.equal(httpUrl(undefined), "");
});

test("agentBase: meta by default, ?agent= wins, bad values ignored", () => {
  assert.equal(agentBase("", "http://localhost:8787"), "http://localhost:8787");
  assert.equal(agentBase("?agent=https://8787-abc.proxy.daytona.works/", "http://localhost:8787"), "https://8787-abc.proxy.daytona.works");
  assert.equal(agentBase("?agent=javascript:alert(1)", ""), "");
});

test("start button carries the escaped query", () => {
  const html = renderStartButton(`<b>"x"</b>`);
  assert.ok(html.includes("Investigate live"));
  assert.ok(html.includes('data-investigate="&lt;b&gt;&quot;x&quot;&lt;/b&gt;"'));
  assert.ok(html.includes("Powered by Daytona"));
});

test("steps: all seven in contract order, status icons, ms, unknown steps appended", () => {
  const html = renderSteps([{ name: "browse", status: "running" }, { name: "lookup", status: "done", ms: 41.4 }, { name: "extra<x>", status: "error" }]);
  const order = ["Lookup", "Memory recall", "Live browse", "Analysis", "Remember", "Briefing", "Eval", "extra&lt;x&gt;"].map((s) => html.indexOf(s));
  assert.ok(order.every((i, n) => i > -1 && (n === 0 || i > order[n - 1])), "order");
  assert.ok(html.includes('class="spin"'));
  assert.ok(html.includes("41 ms"));
  assert.ok(html.includes("✕"));
  assert.ok(!html.includes("<x>"));
  assert.equal(renderSteps(undefined).match(/<li /g).length, 7);
});

test("changes and flags render, escape, and handle empty or missing", () => {
  assert.ok(renderChanges(DONE.result.changes).includes('<s class="inv-old">Panama</s>') && renderChanges(DONE.result.changes).includes('<b class="inv-new">Cameroon</b>'));
  assert.ok(renderChanges([]).includes("No changes"));
  assert.equal(renderChanges(undefined), "");
  const flags = renderFlags([{ flag: "<img src=x>", severity: "HIGH", source: "javascript:alert(1)" }]);
  assert.ok(flags.includes("sev-high"));
  assert.ok(!flags.includes("<img"));
  assert.ok(!flags.includes('href="javascript'));
  assert.equal(renderFlags(null), "");
});

test("briefing: only http(s) sources become links; eval counts sourced claims", () => {
  const html = renderBriefing(DONE.result.briefing, DONE.result.eval, "http://localhost:8787/jobs/j1/audio");
  assert.ok(html.includes('href="https://www.marinetraffic.com/x"'));
  assert.ok(!html.includes('href="javascript'));
  assert.ok(html.includes("Play briefing"));
  assert.ok(html.includes('<audio preload="none" src="http://localhost:8787/jobs/j1/audio">'));
  assert.equal(evalLine(DONE.result.briefing, DONE.result.eval), "1/2 claims sourced · partial · score 0.50");
  assert.equal(evalLine({ claims: [{ source: "https://a.b/" }] }, undefined), "1/1 claims sourced");
  assert.equal(renderBriefing(undefined), "");
});

test("job: running shows steps and live link, done shows results, error offers retry", () => {
  const running = renderJob({ status: "running", steps: [{ name: "browse", status: "running" }], result: { live: { live_view_url: "https://live.anchorbrowser.io/s/1" } } });
  assert.ok(running.includes("Watch the browser live"));
  assert.ok(!running.includes("Briefing</h3>"));
  const done = renderJob(DONE, { query: "TASSOS", audioSrc: "http://x/jobs/1/audio" });
  for (const s of ["What changed since last check", "Risk flags · 1", "TASSOS changed flag.", "sb-123", "Trace (Arize)"]) assert.ok(done.includes(s), s);
  const failed = renderJob({ status: "error", error: "<boom>" }, { query: "TASSOS" });
  assert.ok(failed.includes("&lt;boom&gt;"));
  assert.ok(failed.includes('data-investigate="TASSOS"'));
  assert.ok(renderJob({ status: "done" }).includes("Investigation done"), "result missing entirely");
  assert.ok(!renderJob({ status: "running", result: { live: { live_view_url: "javascript:alert(1)" } } }).includes("Watch the browser"));
});

test("change note shows readable dates", async () => {
  const { changeNote } = await import("../app/investigate.js");
  assert.equal(changeNote({ old: "Liberia", old_observed_at: "2026-09-25T00:00:00+00:00", detected_at: "2026-10-16T16:54:40+00:00" }),
    "Liberia seen 25 Sept 2026 · new value first seen 16 Oct 2026".replace("Sept", new Date("2026-09-25").toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" })));
});
