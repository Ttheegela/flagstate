import { test } from "node:test";
import assert from "node:assert/strict";
import { gzipSync } from "node:zlib";
import { createAssetLoader, MAX_UNZIPPED_BYTES } from "../api/_asset.js";

const serve = (bytes) => async () => new Response(bytes, { status: 200 });

test("a gzip that expands past the limit is rejected", async () => {
  const bomb = gzipSync(Buffer.alloc(MAX_UNZIPPED_BYTES + 1024 * 1024)); // ~64 KB on the wire, 65 MB inflated
  await assert.rejects(createAssetLoader("https://x/a.gz", (d) => d).load(serve(bomb)), /larger than|maxOutputLength|ERR_BUFFER_TOO_LARGE/i);
});

test("a normal asset still loads", async () => {
  const ok = gzipSync(JSON.stringify({ a: 1 }));
  assert.deepEqual(await createAssetLoader("https://x/a.gz", (d) => d).load(serve(ok)), { a: 1 });
});
