// Shared helpers for the chips-into-Russia pages: SVG building, a hover tooltip, number formats.
const NS = "http://www.w3.org/2000/svg";

export function svg(parent, tag, attrs = {}, text) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}

export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  for (const kid of kids) if (kid != null) e.append(kid);
  return e;
}

export const usd = (v) => v == null ? "not reported"
  : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B`
  : v >= 1e6 ? `$${(v / 1e6).toFixed(v >= 1e8 ? 0 : 1)}M`
  : v >= 1e3 ? `$${Math.round(v / 1e3)}K` : `$${Math.round(v)}`;
export const eur = (v) => v == null ? "no data" : usd(v).replace("$", "€");

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const day = (iso) => { const [y, m, d] = iso.split("-"); return `${+d} ${MONTHS[m - 1]} ${y}`; };

export async function load(name) {
  const r = await fetch(`../data/${name}.json`);
  if (!r.ok) throw new Error(`${name}.json: HTTP ${r.status}`);
  return r.json();
}

// One tooltip for the page. Marks carry data-tip (HTML-free text, lines split by \n).
const tip = h("div", { class: "tip", role: "tooltip" });
document.body.append(tip);
function show(target, x, y) {
  const [head, ...rest] = target.dataset.tip.split("\n");
  tip.replaceChildren(h("b", {}, head), ...rest.flatMap((l, i) => i ? [h("br"), l] : [l]));
  tip.classList.add("on");
  const w = tip.offsetWidth, hgt = tip.offsetHeight;
  tip.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, x + 12)) + "px";
  tip.style.top = Math.max(8, y - hgt - 12) + "px";
}
document.addEventListener("pointermove", (e) => {
  const t = e.target.closest?.("[data-tip]");
  if (t) show(t, e.clientX, e.clientY); else tip.classList.remove("on");
});
document.addEventListener("focusin", (e) => {
  const t = e.target.closest?.("[data-tip]");
  if (!t) return tip.classList.remove("on");
  const r = t.getBoundingClientRect();
  show(t, r.left + r.width / 2, r.top);
});
document.addEventListener("focusout", () => tip.classList.remove("on"));

export function onResize(fn) {
  let t, w = window.innerWidth;
  window.addEventListener("resize", () => {
    if (window.innerWidth === w) return;
    w = window.innerWidth; clearTimeout(t); t = setTimeout(fn, 120);
  });
}
