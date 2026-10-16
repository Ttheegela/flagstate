import { svg, h, usd, eur, load, onResize } from "./chips.js";

const GROUPS = [
  { id: "other", label: "Every other reporting country", color: "var(--viz-other)" },
  { id: "hk-china", label: "Hong Kong and mainland China", color: "var(--viz-hkcn)" },
  { id: "transit", label: "Kazakhstan, Kyrgyzstan, Armenia, Turkey, UAE", color: "var(--viz-transit)" },
];
const COLOR = { "hk-china": "var(--viz-hkcn)", transit: "var(--viz-transit)", other: "var(--viz-other)" };
const EU_NAMES = { RU: "Russia", TR: "Turkey", KZ: "Kazakhstan", KG: "Kyrgyzstan", AM: "Armenia", AE: "UAE" };
const SHORT = { HKG: "Hong Kong", KOR: "South Korea", ARE: "UAE", TUR: "Turkey", USA: "United States" };
const nm = (s) => SHORT[s.iso3] || s.name;
const axisUsd = (v) => v >= 1e9 ? `$${+(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${+(v / 1e6).toFixed(1)}M` : `$${v}`;

function niceMax(v) {
  const p = 10 ** Math.floor(Math.log10(v)), n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
}

function groupTotals(R) {
  return R.years.map((_, i) => {
    const t = { "hk-china": 0, transit: 0 };
    for (const s of R.senders) if (s.group !== "other") t[s.group] += s.usd[i] || 0;
    t.other = R.all_reporters_usd[i] - t["hk-china"] - t.transit;
    return t;
  });
}

function drawStack(R, C) {
  const box = document.getElementById("stack"); box.replaceChildren();
  const W = box.clientWidth, H = 240, ml = 52, mr = 8, top = 16, B = top + H;
  const tot = groupTotals(R);
  const vmax = niceMax(Math.max(...R.all_reporters_usd, ...R.russia_imports_usd.filter(Boolean)));
  const s = svg(box, "svg", { width: W, height: B + 40, role: "img",
    "aria-label": `Chip exports to Russia reported by all countries, ${R.years[0]} to ${R.years.at(-1)}, by group of senders` });
  const y = (v) => B - (v / vmax) * H;
  for (let k = 0; k <= 4; k++) {
    const v = (vmax / 4) * k;
    svg(s, "line", { class: "grid", x1: ml, x2: W - mr, y1: y(v), y2: y(v) });
    svg(s, "text", { x: ml - 6, y: y(v) + 4, "text-anchor": "end" }, axisUsd(v));
  }
  const band = (W - ml - mr) / R.years.length, bw = Math.min(56, band * 0.62);
  R.years.forEach((yr, i) => {
    const cx = ml + band * (i + 0.5), x = cx - bw / 2;
    let base = 0;
    for (const g of GROUPS) {
      const v = tot[i][g.id];
      if (v > 0) {
        const full = (v / vmax) * H, gap = full >= 4 ? 2 : 0, hgt = Math.max(1, full - gap);
        svg(s, "rect", { x, y: y(base) - hgt, width: bw, height: hgt, rx: gap ? 2 : 0, fill: g.color, tabindex: 0,
          "data-tip": `${g.label}, ${yr}\n${usd(v)} declared chip exports to Russia\n${Math.round((v / R.all_reporters_usd[i]) * 100)}% of all reported` });
      }
      base += v;
    }
    const ru = R.russia_imports_usd[i];
    if (ru) {
      svg(s, "line", { x1: cx - band * 0.45, x2: cx + band * 0.45, y1: y(ru), y2: y(ru), stroke: "var(--viz-ref)", "stroke-width": 2, "stroke-dasharray": "5 3" });
      svg(s, "rect", { x: cx - band * 0.45, y: y(ru) - 6, width: band * 0.9, height: 12, fill: "transparent", tabindex: 0,
        "data-tip": `Russia's own reported imports, ${yr}\n${usd(ru)} of chips from all countries` });
    }
    const narrow = band < 60;
    svg(s, "text", { x: cx, y: Math.min(y(R.all_reporters_usd[i]), ru ? y(ru) : B) - 6, "text-anchor": "middle", class: "lab", style: narrow ? "font-size:10px" : null }, usd(R.all_reporters_usd[i]));
    svg(s, "text", { x: cx, y: B + 16, "text-anchor": "middle" }, yr);
    const n = C.by_year[yr] ? C.by_year[yr].row.length + C.by_year[yr].none.length : null;
    if (n != null) svg(s, "text", { x: cx, y: B + 31, "text-anchor": "middle", fill: "var(--color-neutral)", style: "font-size:10px" }, narrow ? String(n) : `${n} reporting`);
  });
  svg(s, "line", { class: "base", x1: ml, x2: W - mr, y1: B, y2: B });
}

function mini(parent, title, values, years, vmax, color, fmt, unitNote) {
  const card = h("div", { class: "mult" });
  const peak = Math.max(...values.map((v) => v || 0)), pi = values.indexOf(peak);
  card.append(h("h4", {}, title, h("span", {}, peak ? `peak ${fmt(peak)} (${years[pi]})` : "no chip rows")));
  parent.append(card);
  const W = 190, H = 64, top = 8, B = top + H, band = W / years.length, bw = band * 0.66;
  const s = svg(card, "svg", { viewBox: `0 0 ${W} ${B + 16}`, width: "100%", role: "img", "aria-label": `${title}: ${unitNote}` });
  svg(s, "line", { class: "base", x1: 0, x2: W, y1: B, y2: B });
  values.forEach((v, i) => {
    const x = band * i + (band - bw) / 2;
    if (v == null) {
      svg(s, "text", { x: x + bw / 2, y: B - 3, "text-anchor": "middle", fill: "var(--color-neutral)", style: "font-size:9px" }, "n/r");
      svg(s, "rect", { x, y: top, width: bw, height: H, fill: "transparent", tabindex: 0, "data-tip": `${title}, ${years[i]}\ndid not report` });
      return;
    }
    const hgt = v > 0 ? Math.max(1.5, (v / vmax) * H) : 0;
    if (hgt) svg(s, "rect", { x, y: B - hgt, width: bw, height: hgt, rx: 1.5, fill: color });
    svg(s, "rect", { x, y: top, width: bw, height: H, fill: "transparent", tabindex: 0,
      "data-tip": `${title}, ${years[i]}\n${v > 0 ? fmt(v) : "no chip row (reported trade, none in chips to Russia)"}` });
  });
  [0, years.length - 1].forEach((i) => svg(s, "text", { x: band * i + band / 2, y: B + 13, "text-anchor": "middle", style: "font-size:10px" }, years[i]));
}

function draw(R, C) {
  drawStack(R, C);
  const big = document.getElementById("big"), small = document.getElementById("small"), eu = document.getElementById("eu");
  big.replaceChildren(); small.replaceChildren(); eu.replaceChildren();
  const bigS = R.senders.filter((s) => s.group !== "transit"), smallS = R.senders.filter((s) => s.group === "transit");
  const max = (list) => niceMax(Math.max(...list.flatMap((s) => s.usd.map((v) => v || 0))));
  const bm = max(bigS), sm = max(smallS);
  for (const s of bigS) mini(big, nm(s), s.usd, R.years, bm, COLOR[s.group], usd, "declared chip exports to Russia, US dollars");
  for (const s of smallS) mini(small, nm(s), s.usd, R.years, sm, COLOR[s.group], usd, "declared chip exports to Russia, US dollars");
  for (const code of Object.keys(EU_NAMES)) {
    const vals = R.eu27_exports_eur[code];
    if (!vals) continue;
    const vm = niceMax(Math.max(...vals.map((v) => v || 0)) || 1);
    mini(eu, `EU27 to ${EU_NAMES[code] || code}`, vals, R.years, vm, code === "RU" ? "var(--viz-other)" : "var(--viz-transit)", eur, "EU27 chip exports, euros");
  }
}

function table(R) {
  const head = h("tr", {}, h("th", {}, "Reporter (USD)"), ...R.years.map((y) => h("th", {}, String(y))));
  const rows = R.senders.map((s) => h("tr", {}, h("td", {}, nm(s)), ...s.usd.map((v) => h("td", {}, v == null ? "n/r" : usd(v)))));
  rows.push(h("tr", {}, h("td", {}, "All reporters"), ...R.all_reporters_usd.map((v) => h("td", {}, usd(v)))));
  rows.push(h("tr", {}, h("td", {}, "Russia's own imports"), ...R.russia_imports_usd.map((v) => h("td", {}, v == null ? "n/r" : usd(v)))));
  document.getElementById("tbl").replaceChildren(h("table", { class: "data" }, h("thead", {}, head), h("tbody", {}, ...rows)));
}

try {
  const [R, C] = await Promise.all([load("routes"), load("coverage")]);
  const i23 = R.years.indexOf(2023);
  if (i23 >= 0) {
    const hk = R.senders.filter((s) => s.group === "hk-china").reduce((a, s) => a + (s.usd[i23] || 0), 0);
    document.querySelector('[data-k="share"]').textContent = `${Math.round((hk / R.all_reporters_usd[i23]) * 100)}%`;
  }
  draw(R, C); table(R);
  document.getElementById("stamp").textContent = `Data retrieved ${R.retrieved}. Years ${R.years[0]} to ${R.years.at(-1)}.`;
  onResize(() => draw(R, C));
} catch (e) {
  const err = document.getElementById("err"); err.classList.add("on"); err.textContent += ` (${e.message})`;
}
