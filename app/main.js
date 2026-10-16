import { prepareQuery, searchResearch, searchLists, loadJson, LIST_IDS, latestOnly, listStatus } from "./search.js";
import { setupWalkthrough } from "./walkthrough.js";
import { connectionsQuery, renderConnections, renderConnectionsLoading } from "./connections.js";
import { renderStartButton, investigate, togglePlay, setupVoice } from "./investigate.js";
import {
  renderResearch, renderLists, renderWider, renderEmpty, renderHint, renderLoading, renderLayerError,
  citation, formatUpdated, medianMonths, escapeHtml, CAVEAT,
} from "./render.js";

const $ = (selector) => document.querySelector(selector);
const state = { research: null, researchFailed: false, lists: {}, listsFailed: [], shown: new Map() };
const nextTicket = latestOnly();
let dataReady = null;

async function loadResearch() {
  try {
    const doc = await loadJson("data/research-index.json");
    if (!Array.isArray(doc.entries)) throw new Error("bad research shape");
    state.research = doc.entries;
    state.researchFailed = false;
  } catch {
    state.researchFailed = true;
  }
}

async function loadLists(ids) {
  const failed = await Promise.all(ids.map(async (id) => {
    try {
      const doc = await loadJson(`data/lists/${id}.json`);
      if (!Array.isArray(doc.records)) throw new Error("bad list shape");
      state.lists[id] = doc;
      return null;
    } catch {
      return id;
    }
  }));
  state.listsFailed = failed.filter(Boolean);
}

function loadData() {
  dataReady ??= Promise.all([loadResearch(), loadLists(LIST_IDS)]);
  return dataReady;
}

async function checkWider(text, isLatest) {
  let next;
  try {
    const q = prepareQuery(text);
    if (!q.imo && q.norm.length < 2) throw new Error("too short for the API"); // the API rejects it with a 400
    const res = await fetch(`/api/search?q=${encodeURIComponent(text)}`, { signal: AbortSignal.timeout(5000) });
    const body = await res.json();
    next = body.enabled === false ? { kind: "link" } : body.error ? { kind: "error" } : { kind: "results", results: body.results || [] };
  } catch {
    next = { kind: "link" };
  }
  const slot = $("#wider");
  if (isLatest() && slot) slot.innerHTML = renderWider(next, text);
}

async function loadConnections(entry, isLatest) {
  const slot = [...document.querySelectorAll("[data-connections]")].find((el) => el.dataset.connections === entry.id);
  if (!slot) return;
  slot.innerHTML = renderConnectionsLoading();
  let data;
  try {
    const res = await fetch(`/api/connections?${connectionsQuery(entry)}`, { signal: AbortSignal.timeout(8000) });
    data = await res.json();
    if (!data || typeof data !== "object" || !("sanctions" in data)) throw new Error("bad connections answer");
  } catch {
    data = { sanctions: { available: false }, lobbying: { available: false }, attribution: "" };
  }
  if (isLatest()) slot.innerHTML = renderConnections(data);
}

export async function runSearch(raw) {
  const isLatest = nextTicket();
  const q = prepareQuery(raw);
  const out = $("#results");
  if (q.text.length < 2) {
    out.hidden = true;
    out.innerHTML = "";
    return;
  }
  out.hidden = false;
  if (!q.usable) {
    out.innerHTML = renderHint();
    return;
  }
  if (!state.research && !state.researchFailed) out.innerHTML = renderLoading();
  await loadData();
  if (!isLatest()) return;

  const research = state.research ? searchResearch(state.research, q) : [];
  const lists = searchLists(state.lists, q);
  state.shown = new Map(research.map((e) => [e.id, e]));
  out.innerHTML = [
    renderStartButton(q.text),
    state.researchFailed ? renderLayerError("research") : renderResearch(research),
    !research.length && !lists.length && !state.researchFailed && !state.listsFailed.length ? renderEmpty(q.text) : "",
    `<div class="layers">${renderLists(lists, state.listsFailed)}<div id="wider">${renderWider({ kind: "loading" }, q.text)}</div></div>`,
    `<p class="caveat">${escapeHtml(CAVEAT)}</p>`,
  ].join("");
  syncTimelineToggles(out);
  checkWider(q.text, isLatest);
  if (research[0]) loadConnections(research[0], isLatest);
}

/** Offer "Show full text" only where a collapsed timeline actually cuts a label (never on the stacked phone layout). */
function syncTimelineToggles(root) {
  root.querySelectorAll(".timeline").forEach((tl) => {
    const button = tl.querySelector(".tl-more");
    if (!button || tl.classList.contains("tl-open")) return;
    button.hidden = ![...tl.querySelectorAll(".what")].some((w) => w.scrollHeight > w.clientHeight + 1);
  });
}

async function showListDate() {
  const slot = $("#lists-date");
  try {
    const status = listStatus(await loadJson("data/lists/meta.json"));
    if (status.stale) {
      slot.innerHTML = `<span class="live-dot" aria-hidden="true"></span><span class="is-stale">Some lists may be out of date</span>`;
      slot.title = status.details.join("\n");
    } else {
      slot.innerHTML = `<span class="live-dot" aria-hidden="true"></span>Official lists updated ${escapeHtml(formatUpdated(status.newest))}`;
    }
  } catch {
    slot.textContent = "List update time unavailable";
  }
}

async function showChipsMonths() {
  try {
    const months = medianMonths(await loadJson("stories/chips-into-russia/data/summary.json"));
    if (months) $("#chips-months").textContent = months;
  } catch {} // keep the static number in index.html
}

async function copyCitation(button) {
  const entry = state.shown.get(button.dataset.cite);
  if (!entry) return;
  const label = button.textContent;
  try {
    await navigator.clipboard.writeText(citation(entry, location.href.split("#")[0]));
    button.textContent = "Copied";
  } catch {
    button.textContent = "Copy failed";
  }
  setTimeout(() => { button.textContent = label; }, 2000);
}

function wire() {
  const input = $("#q");
  let timer;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => runSearch(input.value), 200);
  });
  $("#search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    clearTimeout(timer);
    runSearch(input.value);
  });
  document.querySelectorAll("[data-example]").forEach((link) => link.addEventListener("click", (event) => {
    event.preventDefault();
    input.value = link.dataset.example;
    runSearch(input.value);
  }));
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && document.activeElement !== input) {
      event.preventDefault();
      input.focus();
    }
  });
  $("#results").addEventListener("click", async (event) => {
    const named = event.target.closest("[data-search]");
    if (named) {
      input.value = named.dataset.search;
      runSearch(input.value);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const more = event.target.closest(".tl-more");
    if (more) {
      const open = more.closest(".timeline").classList.toggle("tl-open");
      more.setAttribute("aria-expanded", String(open));
      more.textContent = open ? "Show less" : "Show full text";
      return;
    }
    const cite = event.target.closest("[data-cite]");
    if (cite) return copyCitation(cite);
    const inv = event.target.closest("[data-investigate]");
    if (inv) return investigate(inv.closest("[data-inv]"), inv.dataset.investigate);
    const play = event.target.closest("[data-play]");
    if (play) return togglePlay(play);
    const retry = event.target.closest("[data-retry]");
    if (!retry) return;
    if (retry.dataset.retry === "connections") {
      const id = retry.closest("[data-connections]")?.dataset.connections;
      const entry = id && state.shown.get(id);
      if (entry) loadConnections(entry, () => true);
      return;
    }
    if (retry.dataset.retry === "research") await loadResearch();
    else await loadLists(state.listsFailed.length ? state.listsFailed : LIST_IDS);
    runSearch(input.value);
  });
  window.addEventListener("resize", () => syncTimelineToggles($("#results")));
  $("#results").addEventListener("toggle", (event) => {
    const details = event.target;
    if (details instanceof HTMLDetailsElement && details.open) syncTimelineToggles(details);
    if (!(details instanceof HTMLDetailsElement) || !details.open) return;
    const id = details.querySelector("[data-connections]")?.dataset.connections;
    const entry = id && state.shown.get(id);
    if (entry && !details.querySelector(".conn")) loadConnections(entry, () => true);
  }, true);
  showListDate();
  showChipsMonths();
  setupVoice();
}

wire();
setupWalkthrough({ runSearch });
