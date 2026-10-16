// Searches a nightly compact OpenSanctions index (CC BY-NC 4.0) held in memory.
// Never returns an error page: on any failure the page falls back to an outbound link.
import { prepareQuery, scoreName, LIMIT } from "../app/search.js";
import { normalizeName } from "../app/normalize.js";
import { createAssetLoader } from "./_asset.js";

export const INDEX_URL = "https://github.com/Ttheegela/flagstate/releases/download/data-latest/opensanctions.json.gz";
const index = createAssetLoader(INDEX_URL, (doc) => {
  if (!Array.isArray(doc.entities)) throw new Error("index has no entities");
  return doc.entities.map(([id, schema, imo, by, names]) => ({ id, schema, imo, by, names, keys: names.map(normalizeName) }));
});

export function resetIndexCache() {
  index.reset();
}

function json(body, { status = 200, cache = false } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": cache ? "public, s-maxage=21600" : "no-store" },
  });
}

export function loadIndex(fetchFn = fetch, now = Date.now()) {
  return index.load(fetchFn, now);
}

export function searchIndex(entities, raw) {
  const q = prepareQuery(raw);
  if (!q.usable) return [];
  const scored = [];
  for (const e of entities) {
    const s = q.imo ? (e.imo === q.imo ? 3 : 0) : Math.max(0, ...e.keys.map((k) => scoreName(q, k)));
    if (s) scored.push({ s, e });
  }
  scored.sort((a, b) => b.s - a.s || a.e.names[0].length - b.e.names[0].length);
  return scored.slice(0, LIMIT).map(({ e }) => ({
    name: e.names[0],
    schema: e.schema,
    datasets: e.by ? e.by.split(", ") : [],
    url: `https://www.opensanctions.org/entities/${encodeURIComponent(e.id)}/`,
  }));
}

export async function GET(request) {
  const q = (new URL(request.url).searchParams.get("q") || "").trim();
  if (normalizeName(q).length < 2 || q.length > 200) return json({ error: "bad query" }, { status: 400 });
  let entities;
  try {
    entities = await loadIndex();
  } catch {
    return json({ enabled: false });
  }
  return json({ enabled: true, results: searchIndex(entities, q) }, { cache: true });
}
