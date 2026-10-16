import { test } from "node:test";
import assert from "node:assert/strict";
import { STEPS, availableSteps, nextAvailable } from "../app/walkthrough.js";

test("five steps in page order", () => {
  assert.deepEqual(STEPS.map((s) => s.target), ["#q", '[data-walk="chips"]', '[data-walk="timeline"]', '[data-walk="names"]', '[data-walk="sources"]']);
});

test("steps whose target is missing are skipped", () => {
  const present = new Set(["#q", '[data-walk="sources"]']);
  const doc = { querySelector: (sel) => (present.has(sel) ? {} : null) };
  assert.deepEqual(availableSteps(STEPS, doc).map((s) => s.target), ["#q", '[data-walk="sources"]']);
});

const docWith = (...selectors) => {
  const present = new Set(selectors);
  return { querySelector: (sel) => (present.has(sel) ? {} : null) };
};

test("nextAvailable returns from when its target exists", () => {
  const doc = docWith(...STEPS.map((s) => s.target));
  assert.equal(nextAvailable(STEPS, doc, 2, 1), 2);
});

test("nextAvailable skips forward past missing targets", () => {
  const doc = docWith("#q", '[data-walk="sources"]');
  assert.equal(nextAvailable(STEPS, doc, 1, 1), 4);
});

test("nextAvailable skips backward past missing targets", () => {
  const doc = docWith("#q");
  assert.equal(nextAvailable(STEPS, doc, 3, -1), 0);
});

test("nextAvailable returns -1 when nothing is present in that direction", () => {
  const doc = docWith("#q");
  assert.equal(nextAvailable(STEPS, doc, 1, 1), -1);
});
