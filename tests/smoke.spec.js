import { test, expect } from "@playwright/test";

function watchErrors(page) {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error" && !m.location().url.includes("/api/")) errors.push(m.text());
  });
  return errors;
}

async function search(page, text) {
  await page.fill("#q", text);
  await page.press("#q", "Enter");
}

test("TASSOS: dossier, three listing chips, timeline, official lists, wider link", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/");
  await search(page, "TASSOS");
  const first = page.locator(".dossier-entry").first();
  await expect(first.locator("h2")).toHaveText("TASSOS");
  await expect(first.locator('[data-walk="chips"] .chip')).toHaveCount(3);
  await expect(first.locator('[data-walk="timeline"]')).toBeVisible();
  await expect(page.locator("table.lists")).toContainText("United States");
  await expect(page.locator("table.lists")).toContainText("United Kingdom");
  await expect(page.locator("#wider")).toContainText("Search on OpenSanctions");
  await expect(page.locator("#lists-date")).toContainText(/Official lists updated|Some lists may be out of date/);
  expect(errors).toEqual([]);
});

async function timelineBoxes(page) {
  return page.locator(".dossier-entry").first().locator(".tl-ev").evaluateAll((els) => els.map((el) => {
    const what = el.querySelector(".what");
    const r = el.getBoundingClientRect();
    const t = el.parentElement.getBoundingClientRect();
    return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, trackBottom: t.bottom,
      clipped: what.scrollHeight > what.clientHeight + 1, color: getComputedStyle(what).color, weight: getComputedStyle(what).fontWeight };
  }));
}

function expectFullAndApart(boxes) {
  for (const b of boxes) {
    expect(b.clipped).toBe(false);
    expect(b.bottom).toBeLessThanOrEqual(b.trackBottom + 1);
  }
  for (let i = 1; i < boxes.length; i++) {
    const sideBySide = boxes[i].left >= boxes[i - 1].right - 1;
    const stacked = boxes[i].top >= boxes[i - 1].bottom - 1;
    expect(sideBySide || stacked).toBe(true);
  }
}

test("TASSOS timeline at 1280px: compact by default, toggle shows every label in full", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await search(page, "TASSOS");
  const tl = page.locator(".dossier-entry").first().locator(".timeline");
  const more = tl.locator(".tl-more");
  await expect(more).toBeVisible();
  await expect(more).toHaveAttribute("aria-expanded", "false");
  let boxes = await timelineBoxes(page);
  expect(boxes.some((b) => b.clipped)).toBe(true);
  for (const b of boxes) expect([b.color, b.weight]).toEqual([boxes[0].color, boxes[0].weight]);

  await more.focus();
  await page.keyboard.press("Enter");
  await expect(more).toHaveAttribute("aria-expanded", "true");
  await expect(more).toHaveText("Show less");
  await expect(tl.locator(".what", { hasText: "John Fredriksen) to an unlisted ship manager (Liberia)" })).toBeVisible();
  expectFullAndApart(await timelineBoxes(page));

  await more.click();
  await expect(more).toHaveAttribute("aria-expanded", "false");
  await expect(more).toHaveText("Show full text");
  boxes = await timelineBoxes(page);
  expect(boxes.some((b) => b.clipped)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("TASSOS timeline at 375px: stacked, full text, same colour, no toggle", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/");
  await search(page, "TASSOS");
  const tl = page.locator(".dossier-entry").first().locator(".timeline");
  await expect(tl.locator(".tl-ev").first()).toBeVisible();
  await expect(tl.locator(".tl-more")).toBeHidden();
  const boxes = await timelineBoxes(page);
  expectFullAndApart(boxes);
  for (const b of boxes) expect([b.color, b.weight]).toEqual([boxes[0].color, boxes[0].weight]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("Investigate live button appears; voice section shows the ElevenLabs widget", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/");
  await search(page, "TASSOS");
  await expect(page.locator("[data-investigate]")).toHaveText("Investigate live");
  await expect(page.locator("#voice")).toBeVisible();
  await expect(page.locator("#voice elevenlabs-convai")).toHaveAttribute("agent-id", /^agent_/);
  expect(errors).toEqual([]);
});

test("IMO number finds the same ship", async ({ page }) => {
  await page.goto("/");
  await search(page, "IMO 9408695");
  await expect(page.locator(".dossier-entry h2").first()).toHaveText("TASSOS");
});

test("made-up name shows the empty state; non-Latin shows the hint", async ({ page }) => {
  await page.goto("/");
  await search(page, "Qzxv Nonexistent Shipping 4242");
  await expect(page.locator(".state")).toContainText("Not found in our research or on the official lists");
  await search(page, "Совкомфлот");
  await expect(page.locator(".state")).toContainText("Latin letters");
});

test("research file failing still leaves the official lists working", async ({ page }) => {
  await page.route("**/data/research-index.json", (route) => route.abort());
  await page.goto("/");
  await search(page, "TASSOS");
  await expect(page.locator(".state")).toContainText("Couldn't load our research");
  await expect(page.locator("table.lists")).toContainText("United Kingdom");
});

test("walkthrough runs start to finish", async ({ page }) => {
  await page.goto("/");
  await page.click("#start-walk");
  await expect(page.locator("#walk")).toBeVisible();
  await expect(page.locator("#walk-step")).toHaveText("Walkthrough · 1 of 5");
  for (let i = 0; i < 4; i++) await page.click("#walk-next");
  await expect(page.locator("#walk-next")).toHaveText("Finish");
  await page.click("#walk-next");
  await expect(page.locator("#walk")).toBeHidden();
});

test("no sideways scroll or clipped content on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await search(page, "TASSOS");
  await expect(page.locator(".dossier-entry").first()).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  // overflow-x: clip hides overflow instead of scrolling, so also check nothing is cut off.
  const clipped = await page.evaluate(() => [...document.querySelectorAll("body *")]
    .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1)
    .map((el) => `${el.tagName}.${el.className}`));
  expect(clipped).toEqual([]);
});

test("every story page loads", async ({ request }) => {
  for (const path of [
    "/stories/how-sanctions-work/index.html",
    "/stories/shadow-fleet/network/shadow_fleet_map.html",
    "/stories/chips-into-russia/viz/index.html",
    "/stories/chips-into-russia/viz/coverage.html",
    "/stories/chips-into-russia/viz/listing_lag.html",
    "/stories/chips-into-russia/viz/river.html",
    "/stories/who-lobbies/influence-network/index.html",
    "/stories/who-lobbies/clean-names-graph/index.html",
    "/stories/about-the-data.html",
  ]) {
    expect((await request.get(path)).status(), path).toBe(200);
  }
});

test("a failed list never produces a false 'Not found'", async ({ page }) => {
  await page.route("**/data/lists/us.json", (r) => r.abort());
  await page.goto("/");
  await search(page, "Qzxv Nonexistent Shipping 4242");
  await expect(page.locator("#results")).toContainText("Couldn't load the United States list");
  await expect(page.locator(".state", { hasText: "Not found in our research or on the official lists" })).toHaveCount(0);
});

test("a wrong-shape research file fails alone", async ({ page }) => {
  await page.route("**/data/research-index.json", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: '{"oops":1}' }));
  await page.goto("/");
  await search(page, "TASSOS");
  await expect(page.locator("#results")).toContainText("Couldn't load our research");
  await expect(page.locator("table.lists")).toContainText("United Kingdom");
});

const CONNECTIONS = {
  TASSOS: {
    sanctions: { available: true, matched: true, others: 0, linksMore: 0,
      focus: { name: "TASSOS", schema: "Vessel", imo: "9408695", authorities: ["US", "UK"] },
      links: [{ name: "Zulu Ships Management", schema: "Organization", role: "Property in the interest of", direction: "out", authorities: ["US", "UK"],
        groups: [{ schema: "Vessel", items: ["TAGOR", "NEMRUT", "MANASLU", "BRIONT"].map((n) => ({ name: n, schema: "Vessel", role: "Property in the interest of", direction: "in", authorities: ["US", "UK"] })), more: 6 }] }] },
    lobbying: { available: true, matched: false, checked_no_filings: false },
    attribution: "Sanctions links: official sanctions lists compiled by OpenSanctions (CC BY-NC 4.0).",
  },
  NS2: {
    sanctions: { available: true, matched: false },
    lobbying: { available: true, matched: true, client: "Nord Stream 2 AG", as_of: "2026-10-14", checked_no_filings: false,
      firms: [{ name: "Capitol Counsel LLC", filings: 12, fees_usd: 1230000, sub_fees_usd: null, subcontract: false, years: [2017, 2022], url: "https://lda.gov/filings/public/filing/u1/print/" }],
      lobbyists: [], lobbyists_more: 0, revolving_door: [], bodies: [{ name: "US Senate", filings: 9 }], bills: [], parents: [], bridges: [] },
    attribution: "Lobbying: US Lobbying Disclosure Act filings (lda.gov).",
  },
  SOV: {
    sanctions: { available: true, matched: true, others: 2, linksMore: 0, focus: { name: "SOVCOMFLOT", schema: "Company", imo: "", authorities: ["US"] },
      links: [{ name: "Government of Russia", schema: "Organization", role: "Owned by", direction: "out", authorities: ["US"], groups: [] }] },
    lobbying: { available: true, matched: false, checked_no_filings: true },
    attribution: "",
  },
};

async function stubConnections(page) {
  await page.route("**/api/connections**", (route) => {
    const url = new URL(route.request().url());
    const key = url.searchParams.get("imo") === "9408695" ? "TASSOS" : /nord stream/i.test(url.searchParams.get("name") || "") ? "NS2" : "SOV";
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(CONNECTIONS[key]) });
  });
}

test("connections: TASSOS shows Zulu and its ships, names are searchable", async ({ page }) => {
  await stubConnections(page);
  await page.goto("/");
  await search(page, "TASSOS");
  const panel = page.locator(".dossier-entry").first().locator(".conn");
  await expect(panel).toContainText("Zulu Ships Management");
  await expect(panel).toContainText("+6 more");
  await expect(panel.locator(".conn-graph")).toBeVisible();
  await panel.locator('[data-search="TAGOR"]').click();
  await expect(page.locator("#q")).toHaveValue("TAGOR");
});

test("connections: Nord Stream 2 shows its lobbying firm", async ({ page }) => {
  await stubConnections(page);
  await page.goto("/");
  await search(page, "Nord Stream 2 AG");
  const panel = page.locator(".dossier-entry").first().locator(".conn");
  await expect(panel).toContainText("Lobbying in Washington");
  await expect(panel).toContainText("Capitol Counsel LLC");
});

test("connections: Sovcomflot says no lobbying found; phone hides the graph without clipping", async ({ page }) => {
  await stubConnections(page);
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await search(page, "Sovcomflot");
  const panel = page.locator(".dossier-entry").first().locator(".conn");
  await expect(panel).toContainText("No US lobbying filings found (checked nightly)");
  await expect(panel.locator(".conn-graph")).toBeHidden();
  const clipped = await page.evaluate(() => [...document.querySelectorAll("body *")]
    .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1).map((el) => `${el.tagName}.${el.className}`));
  expect(clipped).toEqual([]);
});

test("home chips card reads the median from data, keeps 20 when the file is missing", async ({ page }) => {
  await page.route("**/chips-into-russia/data/summary.json", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: '{"median_months":22.4,"n":30}' }));
  await page.goto("/");
  await expect(page.locator("#chips-months")).toHaveText("22");
  await page.unroute("**/chips-into-russia/data/summary.json");
  await page.route("**/chips-into-russia/data/summary.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/");
  await expect(page.locator("#lists-date")).toContainText(/Official lists|out of date|unavailable/);
  await expect(page.locator("#chips-months")).toHaveText("20");
});

test("chip dossiers: RM Design links the time-to-list page, ELEM GROUP does not", async ({ page }) => {
  await page.goto("/");
  await search(page, "RM Design and Development");
  await expect(page.locator('.dossier-entry a[href$="viz/listing_lag.html"]').first()).toBeVisible();
  await search(page, "ELEM GROUP");
  const elem = page.locator(".dossier-entry", { hasText: "ELEM GROUP" }).first();
  await expect(elem.locator('a[href$="viz/index.html"]')).toBeVisible();
  await expect(elem.locator('a[href$="listing_lag.html"]')).toHaveCount(0);
});
