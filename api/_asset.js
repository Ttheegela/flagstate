// Shared loader for gzipped JSON assets on the data-latest release: one fetch at a time,
// cached for 12 hours, a failed refresh keeps serving the last good copy and retries after 10 minutes.
import { gunzipSync } from "node:zlib";

const REFRESH_MS = 12 * 60 * 60 * 1000;
const RETRY_MS = 10 * 60 * 1000;
const LOAD_TIMEOUT_MS = 4000;
export const MAX_UNZIPPED_BYTES = 64 * 1024 * 1024;

export function createAssetLoader(url, transform) {
  let cached = null; // { loadedAt, value }
  let pending = null;

  async function fetchAsset(fetchFn, now) {
    const res = await fetchFn(url, { signal: AbortSignal.timeout(LOAD_TIMEOUT_MS) });
    if (!res.ok) throw new Error(`asset HTTP ${res.status}`);
    const doc = JSON.parse(gunzipSync(Buffer.from(await res.arrayBuffer()), { maxOutputLength: MAX_UNZIPPED_BYTES }).toString("utf8"));
    const value = transform(doc);
    cached = { loadedAt: now, value };
    return value;
  }

  async function load(fetchFn = fetch, now = Date.now()) {
    if (cached && now - cached.loadedAt < REFRESH_MS) return cached.value;
    // fetchAsset is async, so even a synchronously-throwing fetchFn becomes a rejection and pending is cleared
    if (!pending) pending = fetchAsset(fetchFn, now).finally(() => { pending = null; });
    try {
      return await pending;
    } catch (err) {
      if (cached) {
        cached.loadedAt = now - REFRESH_MS + RETRY_MS;
        return cached.value;
      }
      throw err;
    }
  }

  return { load, reset() { cached = null; pending = null; } };
}
