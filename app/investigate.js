import { escapeHtml } from "./render.js";

// Contract step names (agent/CONTRACT.md) and how we label them.
export const STEPS = [
  ["lookup", "Lookup"],
  ["recall", "Memory recall (SurrealDB)"],
  ["browse", "Live browse (Anchor)"],
  ["analyse", "Analysis (Daytona sandbox)"],
  ["remember", "Remember (SurrealDB)"],
  ["brief", "Briefing (AWS Bedrock)"],
  ["eval", "Eval (Arize)"],
];
const POWERED = "Powered by Daytona · Anchor · SurrealDB · AWS Bedrock · Arize · ElevenLabs";
const POLL_MS = 1500;
const GIVE_UP_MS = 10 * 60 * 1000;

/** Absolute http(s) URL or "" (agent data is untrusted: no javascript:, data: or relative links). */
export function httpUrl(url) {
  try {
    const u = new URL(String(url ?? ""));
    return u.protocol === "https:" || u.protocol === "http:" ? u.href : "";
  } catch {
    return "";
  }
}

/** Agent origin from <meta name="flagstate-agent">, overridden by ?agent=. */
export function agentBase(search = location.search, meta = document.querySelector('meta[name="flagstate-agent"]')?.content) {
  const raw = new URLSearchParams(search).get("agent") || meta || "";
  return httpUrl(raw).replace(/\/+$/, "");
}

function link(url, text) {
  const href = httpUrl(url);
  return href ? `<a href="${escapeHtml(href)}" rel="noopener" target="_blank">${escapeHtml(text)}</a>` : escapeHtml(text);
}

function hostOf(url) {
  try { return new URL(url).hostname; } catch { return ""; }
}

/** A claim/flag source: a link named by its host when it is a URL, else plain text. */
function sourceLink(src) {
  return httpUrl(src) ? link(src, hostOf(src)) : escapeHtml(src);
}

export function renderStartButton(query) {
  return `<div class="inv" data-inv>
    <div class="inv-head"><div><p class="label">Live investigator</p><p class="inv-lede">Run an agent that browses the web now, compares with what it saw last time and writes a sourced briefing.</p></div>
    <button class="btn btn-accent" type="button" data-investigate="${escapeHtml(query)}">Investigate live</button></div>
    <p class="tl-note">${POWERED}</p>
  </div>`;
}

const ICON = { done: "✓", ok: "✓", error: "✕", failed: "✕", skipped: "–" };

export function renderSteps(steps) {
  const byName = new Map((Array.isArray(steps) ? steps : []).filter((s) => s && s.name).map((s) => [s.name, s]));
  const known = new Set(STEPS.map(([n]) => n));
  const rows = [...STEPS, ...[...byName.keys()].filter((n) => !known.has(n)).map((n) => [n, n])].map(([name, label]) => {
    const s = byName.get(name) || {};
    const status = String(s.status || "pending");
    const icon = status === "running" ? `<span class="spin" aria-hidden="true"></span>` : escapeHtml(ICON[status] || "·");
    const ms = typeof s.ms === "number" && Number.isFinite(s.ms) ? `<span class="inv-ms">${Math.round(s.ms)} ms</span>` : "";
    const detail = s.detail ? `<span class="inv-detail">${escapeHtml(s.detail)}</span>` : "";
    return `<li class="inv-step is-${escapeHtml(status)}"><span class="inv-ico">${icon}</span><span class="inv-name">${escapeHtml(label)}<span class="visually-hidden"> ${escapeHtml(status)}</span></span>${ms}${detail}</li>`;
  }).join("");
  return `<ol class="inv-steps">${rows}</ol>`;
}

/** "Liberia seen 25 Sep 2026 · new value first seen 16 Oct 2026" from ISO timestamps. */
export function changeNote(c) {
  const day = (iso) => {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  };
  return `${c.old ?? "Old value"} seen ${day(c.old_observed_at)}${c.detected_at ? ` · new value first seen ${day(c.detected_at)}` : ""}`;
}

export function renderChanges(changes) {
  if (!Array.isArray(changes)) return "";
  const rows = changes.map((c) => `<li class="inv-change"><span class="conn-rel">${escapeHtml(c?.field)}</span><s class="inv-old">${escapeHtml(c?.old ?? "—")}</s> <span class="inv-arrow" aria-label="changed to">→</span> <b class="inv-new">${escapeHtml(c?.new ?? "—")}</b>${c?.old_observed_at ? ` <span class="conn-meta">${escapeHtml(changeNote(c))}</span>` : ""}</li>`).join("");
  return `<div class="block inv-changes"><h3>What changed since last check</h3>${rows ? `<ul class="conn-list">${rows}</ul>` : `<p class="muted">No changes since the last check.</p>`}</div>`;
}

export function renderFlags(flags) {
  if (!Array.isArray(flags)) return "";
  const rows = flags.map((f) => {
    const sev = String(f?.severity || "info").toLowerCase();
    const cls = ["high", "medium", "low"].includes(sev) ? sev : "info";
    return `<li><span class="sev sev-${cls}">${escapeHtml(sev.toUpperCase())}</span> <b>${escapeHtml(f?.flag)}</b>${f?.evidence ? `<span class="inv-detail">${escapeHtml(f.evidence)}</span>` : ""}${f?.source ? `<span class="conn-meta">${sourceLink(f.source)}</span>` : ""}</li>`;
  }).join("");
  return `<div class="block inv-flags"><h3>Risk flags · ${flags.length}</h3>${rows ? `<ul class="conn-list">${rows}</ul>` : `<p class="muted">No risk flags raised.</p>`}</div>`;
}

/** "12/12 claims sourced" from the briefing, plus the Arize eval label and score when present. */
export function evalLine(briefing, ev) {
  const claims = Array.isArray(briefing?.claims) ? briefing.claims : [];
  const parts = [];
  if (claims.length) parts.push(`${claims.filter((c) => httpUrl(c?.source)).length}/${claims.length} claims sourced`);
  if (ev?.label) parts.push(String(ev.label));
  if (typeof ev?.score === "number" && Number.isFinite(ev.score)) parts.push(`score ${ev.score.toFixed(2)}`);
  return parts.join(" · ");
}

export function renderBriefing(briefing, ev, audioSrc) {
  if (!briefing?.text && !Array.isArray(briefing?.claims)) return "";
  const claims = Array.isArray(briefing.claims) ? briefing.claims : [];
  const play = audioSrc ? `<button class="btn" type="button" data-play>Play briefing</button><audio preload="none" src="${escapeHtml(audioSrc)}"></audio>` : "";
  const line = evalLine(briefing, ev);
  return `<div class="block reported inv-brief"><h3>Briefing</h3>
    ${briefing.text ? `<p>${escapeHtml(briefing.text)}</p>` : ""}
    ${claims.length ? `<ol class="src">${claims.map((c) => `<li>${escapeHtml(c?.text)}${c?.source ? ` · ${sourceLink(c.source)}` : " · <span class=\"is-stale\">no source</span>"}</li>`).join("")}</ol>` : ""}
    <div class="d-actions">${play}${line ? `<span class="inv-eval">Eval (Arize): ${escapeHtml(line)}</span>` : ""}</div>
    ${ev?.explanation ? `<div class="tl-note">${escapeHtml(ev.explanation)}</div>` : ""}
  </div>`;
}

export function renderJob(job, { query = "", audioSrc = "" } = {}) {
  const status = String(job?.status || "running");
  const r = job?.result && typeof job.result === "object" ? job.result : {};
  const live = httpUrl(r.live?.live_view_url || (Array.isArray(job?.steps) ? job.steps.find((s) => s?.live_view_url)?.live_view_url : ""));
  const meta = [
    r.sandbox?.sandbox_id ? `Analysis ran in Daytona sandbox ${escapeHtml(r.sandbox.sandbox_id)}` : "",
    r.trace_url ? link(r.trace_url, "Trace (Arize)") : "",
  ].filter(Boolean).join(" · ");
  const head = status === "done" ? "Investigation done" : status === "error" ? "Investigation failed" : "Investigating…";
  const error = status === "error" ? `<p class="layer-error">${escapeHtml(job?.error || r.error || "The agent hit an error.")} <button class="btn" type="button" data-investigate="${escapeHtml(query)}">Try again</button></p>` : "";
  const body = status === "done"
    ? `<div class="layers inv-result"><div>${renderBriefing(r.briefing, r.eval, audioSrc)}</div><div>${renderChanges(r.changes)}${renderFlags(r.flags)}</div></div>`
    : "";
  return `<div class="inv-head"><div><p class="label">Live investigator · ${escapeHtml(head)}</p>
    ${live ? `<p class="inv-lede"><a class="btn" href="${escapeHtml(live)}" rel="noopener" target="_blank"><span class="live-dot" aria-hidden="true"></span>Watch the browser live</a></p>` : ""}</div></div>
    ${renderSteps(job?.steps)}${error}${body}
    ${meta ? `<p class="tl-note">${meta}</p>` : ""}
    <p class="tl-note">${POWERED}</p>`;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** POST /investigate, then poll /jobs/{id} into the slot until done, error, or the slot leaves the page. */
export async function investigate(slot, query, base = agentBase()) {
  const run = String(Math.random());
  slot.dataset.run = run;
  const current = () => slot.isConnected && slot.dataset.run === run;
  const show = (job, opts) => { if (current()) slot.innerHTML = renderJob(job, { query, ...opts }); };
  show({ status: "running", steps: [] });
  let id;
  try {
    if (!base) throw new Error("No agent configured.");
    const res = await fetch(`${base}/investigate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
    id = (await res.json())?.job_id;
    if (!res.ok || !id) throw new Error(`The agent answered ${res.status}.`);
  } catch (e) {
    return show({ status: "error", error: `Couldn't reach the agent at ${base || "(none)"}. ${e.message}` });
  }
  const jobUrl = `${base}/jobs/${encodeURIComponent(id)}`;
  const started = Date.now();
  let misses = 0;
  while (current()) {
    try {
      const job = await (await fetch(jobUrl)).json();
      misses = 0;
      show(job, { audioSrc: `${jobUrl}/audio` });
      if (job?.status === "done" || job?.status === "error") return;
    } catch {
      if (++misses >= 5) return show({ status: "error", error: "Lost contact with the agent." });
    }
    if (Date.now() - started > GIVE_UP_MS) return show({ status: "error", error: "The agent took too long." });
    await sleep(POLL_MS);
  }
}

export function togglePlay(button) {
  const audio = button.parentElement.querySelector("audio");
  if (!audio) return;
  if (audio.paused) {
    audio.play().catch(() => { button.textContent = "Audio unavailable"; });
    button.textContent = "Pause briefing";
    audio.onended = () => { button.textContent = "Play briefing"; };
  } else {
    audio.pause();
    button.textContent = "Play briefing";
  }
}

/** Show the ElevenLabs voice agent only when <meta name="flagstate-voice-agent"> has an id. */
export function setupVoice() {
  const id = document.querySelector('meta[name="flagstate-voice-agent"]')?.content.trim();
  const section = document.querySelector("#voice");
  if (!id || !section) return;
  const widget = document.createElement("elevenlabs-convai");
  widget.setAttribute("agent-id", id);
  widget.setAttribute("action-text", "Ask Flagstate by voice");
  widget.setAttribute("start-call-text", "Start a call");
  // The voice agent's webhook tools call https://{agent_host}/tools/*, so hand it the agent's host.
  try {
    widget.setAttribute("dynamic-variables", JSON.stringify({ agent_host: new URL(agentBase()).host }));
  } catch { /* no usable agent URL: the voice agent will say its tools are unavailable */ }
  section.querySelector("#voice-slot").append(widget);
  const script = document.createElement("script");
  script.src = "https://unpkg.com/@elevenlabs/convai-widget-embed@0.18.3/dist/index.js";
  script.async = true;
  document.body.append(script);
  section.hidden = false;
}
