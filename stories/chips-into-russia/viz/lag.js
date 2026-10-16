import { h, day, load } from "./chips.js";

const INVASION = "2022-02-24";
const COUNTRY = { AE: "UAE", AM: "Armenia", CN: "China", CY: "Cyprus", FR: "France", HK: "Hong Kong", HU: "Hungary",
  IN: "India", KG: "Kyrgyzstan", RU: "Russia", TH: "Thailand", TR: "Turkey", TW: "Taiwan" };
const where = (f) => f.countries.map((c) => COUNTRY[c] || c).join(", ");

function setNum(key, months, n, note) {
  const el = document.querySelector(`[data-k="${key}"]`);
  el.replaceChildren(String(Math.round(months)), " ", h("small", {}, "months"));
  const p = document.querySelector(`[data-k="${key}-note"]`);
  p.textContent = `${note} Median ${months} months, n = ${n}.`;
}

try {
  const L = await load("listing_lag");
  const S = L.summary, R = L.releases;
  setNum("median", S.curated_new.median_months, S.curated_new.n, "Median time from founding to US Treasury listing, for the chip suppliers below that were set up after the invasion.");
  setNum("wide", S.wider_base.median_months, S.wider_base.n, "The same measure for every company on the US Russia sanctions programme founded after the invasion and based outside Russia and Belarus.");

  const fresh = L.firms.filter((f) => f.founded && f.founded >= INVASION);
  const nodate = L.firms.filter((f) => !f.founded);
  const older = L.firms.filter((f) => f.founded && f.founded < INVASION);
  document.querySelector('[data-k="lanes-sub"]').textContent =
    `${fresh.length} firms, ordered by founding date. Half were listed within ${S.curated_new.median_months} months; the middle half took ${S.curated_new.p25_months} to ${S.curated_new.p75_months} months.`;
  document.querySelector('[data-k="older-sub"]').textContent =
    `${L.firms.length} firms in all: ${fresh.length} founded after the invasion, ${older.length} founded before it (left out of the median) and ${nodate.length} with no founding date.`;

  // time scale: whole years around the dates on show
  const dates = [...fresh, ...nodate].flatMap((f) => [f.founded, f.listed, f.bis && f.bis.date]).filter(Boolean).sort();
  const y0 = +dates[0].slice(0, 4), y1 = +dates.at(-1).slice(0, 4) + 1;
  const t0 = Date.UTC(y0, 0, 1), t1 = Date.UTC(y1, 0, 1);
  const pos = (iso) => (((Date.parse(iso) - t0) / (t1 - t0)) * 100).toFixed(2) + "%";

  const axis = document.getElementById("axis");
  for (let y = y0; y <= y1; y++) axis.append(h("span", { class: "tick", style: `left:${pos(`${y}-01-01`)}` }, String(y)));
  axis.append(h("span", { class: "inv", style: `left:${pos(INVASION)}` }), h("span", { class: "tick inv-l", style: `left:${pos(INVASION)}` }, "invasion"));

  const link = (f) => R[f.release].url;
  function lane(f) {
    const track = h("div", { class: "track" }, h("span", { class: "inv", style: `left:${pos(INVASION)}` }));
    if (f.founded) {
      track.append(h("span", { class: "span", style: `left:${pos(f.founded)};width:calc(${pos(f.listed)} - ${pos(f.founded)})` }),
        h("span", { class: "dot f", style: `left:${pos(f.founded)}`, tabindex: 0, "data-tip": `${f.name}\nfounded ${day(f.founded)} (US Treasury entry)` }));
    }
    if (f.bis) track.append(h("span", { class: "dot b", style: `left:${pos(f.bis.date)}`, tabindex: 0,
      "data-tip": `${f.name}\nEntity List ${day(f.bis.date)}${f.bis.federal_register ? ` (${f.bis.federal_register})` : ""}` }));
    track.append(h("span", { class: "dot l", style: `left:${pos(f.listed)}`, tabindex: 0,
      "data-tip": `${f.name}\nlisted by the US Treasury ${day(f.listed)}${f.months != null ? `\n${f.months} months after founding` : ""}` }));
    // months label above the middle of the line; "listed" just left of a lone listing mark
    const mid = f.founded ? (Date.parse(f.founded) + Date.parse(f.listed)) / 2 : null;
    track.append(f.founded
      ? h("span", { class: "mo", style: `left:${(((mid - t0) / (t1 - t0)) * 100).toFixed(2)}%` }, `${f.months} mo`)
      : h("span", { class: "mo left", style: `left:${pos(f.listed)}` }, "listed"));
    return h("li", { class: "lane" },
      h("div", { class: "who" }, h("a", { href: link(f), title: `US Treasury press release ${f.release}` }, f.name),
        h("span", {}, `${where(f)} · OFAC ${f.ofac_id}${f.on_current_list ? "" : " · no longer on the list"}`)),
      track);
  }
  document.getElementById("lanes").replaceChildren(...fresh.map(lane));
  document.getElementById("nodate").replaceChildren(...nodate.map(lane));

  const a = (href, text) => h("a", { href }, text);
  const head = h("tr", {}, ...["Firm", "Where", "Founded", "Entity List", "US Treasury listing", "Months", "Named for", "Sources"].map((t) => h("th", {}, t)));
  const rows = L.firms.map((f) => {
    const r = R[f.release];
    const src = h("td", {}, a(r.url, f.release), " · ", a(r.ofac_action_url, "OFAC action"),
      ...(r.federal_register ? [" · ", a(r.federal_register.url, r.federal_register.cite)] : []));
    return h("tr", {}, h("td", {}, f.name), h("td", {}, where(f)), h("td", {}, f.founded || "none given"),
      h("td", {}, f.bis ? `${f.bis.date}${f.bis.federal_register ? ` (${f.bis.federal_register})` : ""}` : ""),
      h("td", {}, f.listed), h("td", {}, f.months != null ? String(f.months) : ""), h("td", { style: "text-align:left" }, f.reason), src);
  });
  document.getElementById("tbl").replaceChildren(h("table", { class: "data" }, h("thead", {}, head), h("tbody", {}, ...rows)));

  const srcs = document.getElementById("sources");
  for (const [id, r] of Object.entries(R)) {
    srcs.append(h("li", {}, a(r.url, `US Treasury press release ${id}`), `, ${day(r.date)}: "${r.title}". `,
      a(r.ofac_action_url, "OFAC recent action"), ...(r.federal_register ? [". Federal Register ", a(r.federal_register.url, r.federal_register.cite)] : []), "."));
  }
  document.getElementById("stamp").textContent = `OFAC list of ${L.ofac_date_of_issue}, retrieved ${L.retrieved}. ${L.definition}.`;
} catch (e) {
  const err = document.getElementById("err"); err.classList.add("on"); err.textContent += ` (${e.message})`;
}
