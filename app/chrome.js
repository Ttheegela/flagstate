// Header clock, list status pill and the 3D port scene. Kept apart from main.js so a WebGL
// failure never touches search.
import { mountPortScene } from "./scene.js";

const pad = (n) => String(n).padStart(2, "0");

function tickClock() {
  const day = document.querySelector("#clock-day");
  const time = document.querySelector("#clock-time");
  if (!day || !time) return;
  const draw = () => {
    const now = new Date();
    day.textContent = now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
    time.textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  };
  draw();
  setInterval(draw, 1000);
}

/** Mirrors #lists-date (filled by main.js) into the header status pill. */
function mirrorListStatus() {
  const source = document.querySelector("#lists-date");
  const pill = document.querySelector("#live-status");
  if (!source || !pill) return;
  const sync = () => {
    const text = source.textContent;
    const state = /out of date/.test(text) ? "stale" : /unavailable/.test(text) ? "unknown" : /updated/.test(text) ? "ok" : "checking";
    pill.dataset.state = state;
    pill.querySelector("span:last-child").textContent =
      { ok: "Lists current", stale: "Lists may be stale", unknown: "Status unavailable", checking: "Checking…" }[state];
  };
  new MutationObserver(sync).observe(source, { childList: true, subtree: true, characterData: true });
  sync();
}

function mountScene() {
  const host = document.querySelector("#port-scene");
  if (!host) return;
  const stop = mountPortScene(host, {
    labels: host.querySelector(".ship-tags"),
    onPick(ship) {
      const input = document.querySelector("#q");
      input.value = ship.name;
      document.querySelector("#search-form").requestSubmit();
      setTimeout(() => document.querySelector("#results")?.scrollIntoView({ behavior: "smooth", block: "start" }), 250);
    },
  });
  host.classList.toggle("is-static", !stop);
}

tickClock();
mirrorListStatus();
mountScene();
