import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { normalizeName, parseImo } from "../app/normalize.js";

const cases = JSON.parse(readFileSync(new URL("../scripts/normalize_cases.json", import.meta.url), "utf8"));

test("normalizeName matches the shared cases", () => {
  for (const c of cases.names) assert.equal(normalizeName(c.in), c.out, `input: ${JSON.stringify(c.in)}`);
});

test("parseImo matches the shared cases", () => {
  for (const c of cases.imos) assert.equal(parseImo(c.in), c.out, `input: ${JSON.stringify(c.in)}`);
});
