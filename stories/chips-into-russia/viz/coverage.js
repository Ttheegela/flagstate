import { svg, h, load } from "./chips.js";

const LABEL = { row: "Reported a chip row to Russia", none: "Reported trade, no chip row to Russia", absent: "Did not report this year" };

try {
  const [C, W] = await Promise.all([load("coverage"), fetch("world-110m.json").then((r) => { if (!r.ok) throw new Error("world-110m.json"); return r.json(); })]);
  const years = C.years.map(String);
  const box = document.getElementById("map");
  const s = svg(box, "svg", { viewBox: `0 0 ${W.width} ${W.height}`, role: "img", "aria-labelledby": "maptitle" });
  const pat = svg(svg(s, "defs"), "pattern", { id: "hatch", width: 4, height: 4, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
  svg(pat, "rect", { width: 4, height: 4, fill: "var(--viz-stage)" });
  svg(pat, "line", { x1: 0, y1: 0, x2: 0, y2: 4, stroke: "var(--color-neutral)", "stroke-width": 1 });
  const shapes = [
    ...W.countries.map((c) => ({ c, el: svg(s, "path", { d: c.d }) })),
    ...W.dots.map((c) => ({ c, el: svg(s, "circle", { cx: c.xy[0], cy: c.xy[1], r: 3.2 }) })),
  ];

  const yearBox = document.getElementById("years");
  const buttons = years.map((y) => {
    const b = h("button", { class: "btn", type: "button", "aria-pressed": "false" }, y);
    b.addEventListener("click", () => show(y));
    yearBox.append(b);
    return b;
  });

  function show(y) {
    const Y = C.by_year[y], row = new Set(Y.row), none = new Set(Y.none);
    const state = (id) => id === "RUS" ? "rus" : row.has(id) ? "row" : none.has(id) ? "none" : "absent";
    for (const { c, el } of shapes) {
      const st = state(c.id);
      el.setAttribute("class", st);
      const name = (c.id && C.names[c.id]) || c.name;
      el.dataset.tip = st === "rus" ? `Russia, ${y}\nthe destination; ${+y <= 2021 ? "reported its own trade" : "has not reported its own trade since 2021"}` : `${name}, ${y}\n${LABEL[st]}`;
    }
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.textContent === y)));
    const absent = Object.keys(C.names).filter((i) => i !== "RUS" && !row.has(i) && !none.has(i)).length;
    document.getElementById("legend").replaceChildren(
      h("li", {}, h("span", { class: "sw hkcn" }), LABEL.row, " ", h("b", {}, String(Y.row.length))),
      h("li", {}, h("span", { class: "sw none" }), LABEL.none, " ", h("b", {}, String(Y.none.length))),
      h("li", {}, h("span", { class: "sw absent" }), `${LABEL.absent}, of the ${Object.keys(C.names).length - 1} that reported at least once`, " ", h("b", {}, String(absent))));
    document.getElementById("maptitle").textContent = `Chip export rows to Russia, ${y}`;
    document.querySelector('[data-k="year"]').textContent = y;
    document.getElementById("names").replaceChildren(...Y.row.map((i) => h("li", {}, C.names[i] || i)));
  }

  const first = C.by_year[years[0]], i23 = years.indexOf("2023") >= 0 ? "2023" : years.at(-1);
  document.querySelector('[data-k="drop"]').textContent =
    `${first.row.length} countries reported a chip row to Russia in ${years[0]}; ${C.by_year[i23].row.length} did in ${i23} and ${C.by_year[years.at(-1)].row.length} so far in ${years.at(-1)}.`;
  document.getElementById("stamp").textContent = `Data retrieved ${C.retrieved}.`;
  show(i23);
} catch (e) {
  const err = document.getElementById("err"); err.classList.add("on"); err.textContent += ` (${e.message})`;
}
