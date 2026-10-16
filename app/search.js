import { normalizeName, parseImo } from "./normalize.js";

export const LIST_IDS = ["us", "uk", "eu", "un"];
export const LIMIT = 10;
const STALE_MS = 3 * 24 * 60 * 60 * 1000;

export async function loadJson(url, fetchFn = fetch) {
  const res = await fetchFn(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

export function prepareQuery(raw) {
  const text = (raw || "").trim();
  const imo = parseImo(text);
  const norm = imo ? "" : normalizeName(text);
  return { text, imo, norm, tokens: norm ? norm.split(" ") : [], usable: Boolean(imo || norm) };
}

// 3 exact, 2 every query word present, 1 at least 60% of words; the last word may be a prefix (typing).
export function scoreName(q, norm) {
  if (!norm || !q.tokens.length) return 0;
  if (norm === q.norm) return 3;
  const words = norm.split(" ");
  const last = q.tokens.length - 1;
  let hit = 0;
  q.tokens.forEach((t, i) => {
    if (words.includes(t) || (i === last && t.length >= 3 && words.some((w) => w.startsWith(t)))) hit++;
  });
  if (hit === q.tokens.length) return 2;
  return hit / q.tokens.length >= 0.6 ? 1 : 0;
}

export function searchResearch(entries, q) {
  if (!q.usable) return [];
  const scored = [];
  for (const e of entries) {
    const s = q.imo ? (e.imo === q.imo ? 3 : 0) : Math.max(0, ...e.keys.map((k) => scoreName(q, k)));
    if (s) scored.push({ s, e });
  }
  scored.sort((a, b) => b.s - a.s || a.e.name.length - b.e.name.length || a.e.name.localeCompare(b.e.name));
  return scored.slice(0, LIMIT).map((x) => x.e);
}

export function searchLists(docs, q) {
  if (!q.usable) return [];
  const scored = [];
  for (const [list, doc] of Object.entries(docs)) {
    for (const r of doc.records) {
      const s = q.imo ? (r[5] === q.imo ? 3 : 0) : scoreName(q, r[1]);
      if (s) scored.push({ s, list, r });
    }
  }
  scored.sort((a, b) => b.s - a.s || a.r[0].length - b.r[0].length);
  const seen = new Set();
  const out = [];
  for (const { list, r } of scored) {
    const key = r[4] ? `${list}:${r[4]}` : `${list}:name:${r[1]}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ list, name: r[0], program: r[2], date: r[3], ref: r[4], imo: r[5], url: r[6] });
    if (out.length === LIMIT) break;
  }
  return out;
}

// Each call hands out a ticket; only the newest ticket reports true.
export function latestOnly() {
  let current = 0;
  return () => {
    const id = ++current;
    return () => id === current;
  };
}

export function listStatus(meta, now = new Date()) {
  const lists = Object.values(meta?.lists || {});
  if (!lists.length) return { newest: null, stale: true, details: [] };
  const times = lists.map((l) => new Date(l.updated_at).getTime()).filter(Number.isFinite);
  const newest = times.length ? new Date(Math.max(...times)) : null;
  const stale = lists.some((l) => {
    const t = new Date(l.updated_at).getTime();
    return !Number.isFinite(t) || l.status !== "fresh" || now - t > STALE_MS;
  });
  const details = lists.map((l) => `${l.label}: ${l.updated_at ? l.updated_at.slice(0, 10) : "never"}${l.status !== "fresh" ? " (kept previous copy)" : ""}`);
  return { newest, stale, details };
}
