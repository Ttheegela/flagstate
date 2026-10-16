import { escapeHtml } from "./render.js";
import { agentBase } from "./investigate.js";

// Matches agent/server.py: larger uploads are refused there anyway.
export const MAX_AUDIO = 25 * 1024 * 1024;
const CONFIDENCE = { imo: "IMO match", name: "Name match", possible: "Possible match" };

/** 75.4 -> "1:15", 3725 -> "1:02:05"; "" when untimed. */
export function clock(sec) {
  if (typeof sec !== "number" || !Number.isFinite(sec) || sec < 0) return "";
  const s = Math.floor(sec), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${r}` : `${m}:${r}`;
}

/** "speaker_0" -> "Speaker 1"; anything else as given; "" for none. */
export function speakerLabel(id) {
  const m = /^speaker_(\d+)$/.exec(String(id ?? ""));
  return m ? `Speaker ${Number(m[1]) + 1}` : String(id ?? "");
}

function seekButton(sec, label = clock(sec)) {
  return label ? `<button class="sc-time" type="button" data-seek="${sec}">${escapeHtml(label)}</button>` : "";
}

export function renderEntity(e, i) {
  const listed = Array.isArray(e?.listed_by) ? e.listed_by : [];
  const conf = CONFIDENCE[e?.confidence] || "Possible match";
  const meta = [e?.kind, e?.imo ? `IMO ${e.imo}` : "", e?.flag ? `flagged ${e.flag}` : ""].filter(Boolean).map(escapeHtml).join(" · ");
  const heard = Array.isArray(e?.heard_as) && e.heard_as.length
    ? `<p class="sc-heard">Heard as <b>${e.heard_as.map(escapeHtml).join("</b>, <b>")}</b>, on record as <b>${escapeHtml(e.name)}</b></p>` : "";
  const mentions = Array.isArray(e?.mentions) ? e.mentions : [];
  const times = mentions.map((m) => seekButton(m?.start)).filter(Boolean);
  const when = times.length
    ? `<p class="sc-when">Heard ${mentions.length}× · ${times.slice(0, 8).join(" ")}${times.length > 8 ? ` <span class="conn-meta">+${times.length - 8} more</span>` : ""}</p>`
    : `<p class="sc-when">Mentioned ${mentions.length}×</p>`;
  const badges = listed.length
    ? listed.map((by) => `<span class="sev sev-high">${escapeHtml(by)}</span>`).join(" ")
    : `<span class="sev sev-info">${e?.on_record === false ? "Not in our records" : "Not on the four lists"}</span>`;
  return `<li class="sc-ent${e?.confidence === "possible" ? " is-possible" : ""}" id="sc-ent-${i}" data-entity="${i}">
    <div class="sc-ent-head"><b class="sc-ent-name">${escapeHtml(e?.name)}</b><span class="sc-conf">${escapeHtml(conf)}</span></div>
    ${meta ? `<p class="conn-meta sc-meta">${meta}</p>` : ""}
    <p class="sc-badges">${badges}</p>${heard}${when}
    <button class="btn" type="button" data-scribe-search="${escapeHtml(e?.query || e?.name || "")}">Open dossier and investigate</button>
  </li>`;
}

export function renderTranscript(segments, entities = []) {
  const rows = (Array.isArray(segments) ? segments : []).map((s) => {
    const parts = (Array.isArray(s?.parts) ? s.parts : []).map((p) => {
      if (typeof p?.entity !== "number") return escapeHtml(p?.text);
      const e = entities[p.entity] || {};
      const title = `${e.name || ""}${e.listed_by?.length ? ` · listed by ${e.listed_by.join(", ")}` : ""}`;
      return `<button class="sc-hit sc-${escapeHtml(e.confidence || "possible")}${e.listed_by?.length ? " is-listed" : ""}" type="button" data-hit="${p.entity}" title="${escapeHtml(title)}">${escapeHtml(p.text)}</button>`;
    }).join("");
    const timed = Number.isFinite(s?.start);
    const end = Number.isFinite(s?.end) ? s.end : s?.start;
    return `<div class="sc-seg"${timed ? ` data-start="${s.start}" data-end="${end}"` : ""}>
      <div class="sc-who">${timed ? seekButton(s.start) : ""}${s?.speaker ? `<span class="sc-spk">${escapeHtml(speakerLabel(s.speaker))}</span>` : ""}</div>
      <p>${parts}</p></div>`;
  }).join("");
  return `<div class="block sc-transcript"><h3>Transcript</h3>${rows || `<p class="muted">No speech found.</p>`}</div>`;
}

export function renderScribe(result) {
  const entities = Array.isArray(result?.entities) ? result.entities : [];
  const segments = Array.isArray(result?.segments) ? result.segments : [];
  const speakers = new Set(segments.map((s) => s?.speaker).filter(Boolean)).size;
  const listed = entities.filter((e) => e?.listed_by?.length).length;
  const stats = [
    result?.source === "audio" ? "Transcribed by ElevenLabs Scribe" : "Pasted transcript",
    clock(result?.duration),
    speakers ? `${speakers} speaker${speakers === 1 ? "" : "s"}` : "",
    result?.language ? `language ${result.language}` : "",
    result?.keyterms ? `tuned to ${result.keyterms} names from the sanctions data` : "",
  ].filter(Boolean).map(escapeHtml).join(" · ");
  const headline = entities.length
    ? `${entities.length} on record · <b>${listed} on a sanctions list</b>`
    : "Nobody on record was mentioned";
  return `<div class="sc-result">
    <p class="label">${headline}</p><p class="tl-note">${stats}</p>
    <div class="layers sc-layers">
      ${renderTranscript(segments, entities)}
      <div class="block sc-ents"><h3>Mentioned · ${entities.length}</h3>${entities.length ? `<ul class="sc-list">${entities.map(renderEntity).join("")}</ul>` : `<p class="muted">No ship, company or person in our data was named.</p>`}</div>
    </div>
    <p class="caveat">A name heard in a recording is a possible match, not proof. IMO numbers count only when their check digit is valid; one-word names only next to words like “tanker” or “flagged”. Check the source before you publish.</p>
  </div>`;
}

export function renderScribeError(message) {
  return `<p class="layer-error">${escapeHtml(message)}</p>`;
}

export function renderScribeLoading(what) {
  return `<p class="sc-loading"><span class="spin" aria-hidden="true"></span>${escapeHtml(what)}</p>`;
}

/** The upload/paste panel: send to the agent, render the result, keep the player and transcript in step. */
export function setupScribe({ openDossier, base = agentBase() } = {}) {
  const section = document.querySelector("#scribe");
  if (!section || !base) return;
  const $ = (sel) => section.querySelector(sel);
  const out = $("#scribe-out"), audio = $("#scribe-audio"), fileInput = $("#scribe-file"), drop = $("#scribe-drop");
  let run = 0, objectUrl = "";

  async function send(request, loading) {
    const ticket = ++run;
    out.innerHTML = renderScribeLoading(loading);
    try {
      const res = await request();
      const body = await res.json().catch(() => ({}));
      if (ticket !== run) return;
      if (!res.ok) {
        const reason = res.status === 503
          ? "Transcription is unavailable on this agent (no ElevenLabs key). You can still paste a transcript."
          : body?.detail || `The agent answered ${res.status}.`;
        out.innerHTML = renderScribeError(reason);
        return;
      }
      out.innerHTML = renderScribe(body);
    } catch {
      if (ticket === run) out.innerHTML = renderScribeError(`Couldn't reach the agent at ${base}.`);
    }
  }

  function useFile(file) {
    if (!file) return;
    if (!/^(audio|video)\//.test(file.type) && file.type) return void (out.innerHTML = renderScribeError("Choose an audio or video file."));
    if (file.size > MAX_AUDIO) return void (out.innerHTML = renderScribeError("That file is over 25 MB."));
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(file);
    audio.src = objectUrl;
    audio.hidden = false;
    $("#scribe-name").textContent = file.name;
    const form = new FormData();
    form.append("file", file);
    form.append("hints", $("#scribe-hints").value);
    send(() => fetch(`${base}/scribe`, { method: "POST", body: form }), "Transcribing with ElevenLabs Scribe and checking every name…");
  }

  fileInput.addEventListener("change", () => useFile(fileInput.files[0]));
  ["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("is-over"); }));
  ["dragleave", "drop"].forEach((t) => drop.addEventListener(t, () => drop.classList.remove("is-over")));
  drop.addEventListener("drop", (e) => { e.preventDefault(); useFile(e.dataTransfer?.files?.[0]); });

  $("#scribe-text-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("#scribe-text").value;
    if (!text.trim()) return;
    audio.hidden = true;
    audio.removeAttribute("src");
    send(() => fetch(`${base}/scribe/text`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }),
      "Checking every name in the transcript…");
  });

  out.addEventListener("click", (e) => {
    const seek = e.target.closest("[data-seek]");
    if (seek && audio.src && !audio.hidden) {
      audio.currentTime = Number(seek.dataset.seek);
      audio.play().catch(() => {});
      return;
    }
    const hit = e.target.closest("[data-hit]");
    if (hit) {
      const card = out.querySelector(`#sc-ent-${hit.dataset.hit}`);
      card?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      card?.classList.remove("is-flash");
      void card?.offsetWidth; // restart the flash animation
      card?.classList.add("is-flash");
      return;
    }
    const dossier = e.target.closest("[data-scribe-search]");
    if (dossier && openDossier) openDossier(dossier.dataset.scribeSearch);
  });

  // Mark the turn being played.
  audio.addEventListener("timeupdate", () => {
    const t = audio.currentTime;
    out.querySelectorAll(".sc-seg[data-start]").forEach((seg) => {
      seg.classList.toggle("is-now", t >= Number(seg.dataset.start) && t < Number(seg.dataset.end) + 0.25);
    });
  });
  section.hidden = false;
}
