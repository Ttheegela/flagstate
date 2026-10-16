import { test } from "node:test";
import assert from "node:assert/strict";
import { clock, speakerLabel, renderEntity, renderTranscript, renderScribe, renderScribeError } from "../app/scribe.js";

const TASSOS = {
  id: "IMO9408695", name: "TASSOS", kind: "Oil Tanker", imo: "9408695", flag: "Liberia", on_record: true,
  listed_by: ["European Union", "United Kingdom", "United States"], confidence: "imo", query: "9408695",
  heard_as: ["Front Balder"], mentions: [{ start: 1.0, segment: 0 }, { start: 63.2, segment: 1 }],
};
const UNKNOWN = { id: "IMO1234567", name: "IMO 1234567", imo: "1234567", on_record: false, listed_by: [], confidence: "imo", query: "1234567", heard_as: [], mentions: [{ start: null, segment: 0 }] };
const RESULT = {
  source: "audio", language: "eng", duration: 75.4, keyterms: 250, model: "scribe_v2",
  entities: [TASSOS, UNKNOWN],
  segments: [
    { speaker: "speaker_0", start: 0, end: 1.4, parts: [{ text: "The tanker " }, { text: "Tassos", entity: 0 }, { text: "?" }] },
    { speaker: "speaker_1", start: 2, end: 3.4, parts: [{ text: "Yes, IMO " }, { text: "1234567", entity: 1 }] },
  ],
};

test("clock formats seconds and ignores junk", () => {
  assert.equal(clock(0), "0:00");
  assert.equal(clock(75.4), "1:15");
  assert.equal(clock(3725), "1:02:05");
  assert.equal(clock(null), "");
  assert.equal(clock(-1), "");
  assert.equal(clock("12"), "");
});

test("speakerLabel numbers speakers from 1", () => {
  assert.equal(speakerLabel("speaker_0"), "Speaker 1");
  assert.equal(speakerLabel("speaker_11"), "Speaker 12");
  assert.equal(speakerLabel(null), "");
});

test("entity card shows lists, alias and seekable mentions", () => {
  const html = renderEntity(TASSOS, 0);
  assert.match(html, /id="sc-ent-0"/);
  assert.match(html, /United Kingdom/);
  assert.match(html, /Heard as <b>Front Balder<\/b>, on record as <b>TASSOS<\/b>/);
  assert.match(html, /data-seek="63.2">1:03</);
  assert.match(html, /data-scribe-search="9408695"/);
  assert.match(renderEntity(UNKNOWN, 1), /Not in our records/);
  assert.match(renderEntity({ ...TASSOS, confidence: "possible" }, 2), /is-possible/);
});

test("transcript marks mentions and escapes everything from the agent", () => {
  const html = renderTranscript([{ speaker: "<b>", start: 1, end: '"><script>', parts: [{ text: "<img src=x>" }, { text: "Tassos", entity: 0 }] }], [TASSOS]);
  assert.ok(!html.includes("<img") && !html.includes("<script") && !html.includes("<b>"));
  assert.match(html, /data-end="1"/); // a non-numeric end falls back to the start
  assert.match(html, /class="sc-hit sc-imo is-listed" type="button" data-hit="0"/);
  assert.match(html, /listed by European Union/);
});

test("untimed transcript has no seek buttons", () => {
  const html = renderTranscript([{ speaker: null, start: null, end: null, parts: [{ text: "Pasted." }] }]);
  assert.ok(!html.includes("data-seek") && !html.includes("data-start"));
});

test("result header counts listed entities and the Scribe run", () => {
  const html = renderScribe(RESULT);
  assert.match(html, /2 on record · <b>1 on a sanctions list<\/b>/);
  assert.match(html, /Transcribed by ElevenLabs Scribe · 1:15 · 2 speakers · language eng · tuned to 250 names/);
  assert.match(html, /possible match, not proof/);
  assert.match(renderScribe({ source: "text", entities: [], segments: [] }), /Nobody on record was mentioned/);
});

test("error text is escaped", () => {
  assert.equal(renderScribeError("<x>"), '<p class="layer-error">&lt;x&gt;</p>');
});
