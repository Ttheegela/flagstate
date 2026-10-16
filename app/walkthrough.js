export const STEPS = [
  { target: "#q", text: "We searched TASSOS, an oil tanker's current name. Its IMO number, 9408695, works too, and never changes when the name does." },
  { target: '[data-walk="chips"]', text: "Three governments listed TASSOS within seven months, under two different programs: first Iran, then Russia." },
  { target: '[data-walk="timeline"]', text: "The timeline shows the pattern: sold out of a mainstream fleet, handed to a new manager, then listed by the first government 29 months after the sale." },
  { target: '[data-walk="names"]', text: "Five names, one hull. Search any of them and you land here." },
  { target: '[data-walk="sources"]', text: "Every sentence carries a number, and the number is the source. Open it before you quote." },
];

export function availableSteps(steps, doc) {
  return steps.filter((s) => doc.querySelector(s.target));
}

export function nextAvailable(steps, doc, from, direction) {
  for (let i = from; i >= 0 && i < steps.length; i += direction) {
    if (doc.querySelector(steps[i].target)) return i;
  }
  return -1;
}

export function setupWalkthrough({ runSearch, doc = document }) {
  const card = doc.querySelector("#walk");
  const label = doc.querySelector("#walk-step");
  const bar = doc.querySelector("#walk-bar");
  const text = doc.querySelector("#walk-text");
  const back = doc.querySelector("#walk-back");
  const next = doc.querySelector("#walk-next");
  let steps = [];
  let index = 0;

  const clear = () => doc.querySelectorAll(".spot").forEach((el) => el.classList.remove("spot"));
  const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function show(i, direction = 1) {
    clear();
    const found = nextAvailable(steps, doc, i, direction);
    if (found === -1) return leave();
    index = found;
    const step = steps[index];
    const target = doc.querySelector(step.target);
    target.classList.add("spot");
    target.scrollIntoView({ block: "center", behavior: reduced() ? "auto" : "smooth" });
    text.classList.add("is-swapping");
    setTimeout(() => {
      text.textContent = step.text;
      text.classList.remove("is-swapping");
    }, 120);
    label.textContent = `Walkthrough · ${index + 1} of ${steps.length}`;
    bar.innerHTML = steps.map((_, k) => `<i${k <= index ? ' class="on"' : ""}></i>`).join("");
    back.disabled = index === 0;
    next.textContent = index === steps.length - 1 ? "Finish" : "Next";
  }

  let opener = null;

  function leave() {
    clear();
    card.hidden = true;
    opener?.focus();
  }

  async function start(event) {
    event?.preventDefault();
    opener = event?.currentTarget ?? null;
    const input = doc.querySelector("#q");
    input.value = "TASSOS";
    await runSearch("TASSOS");
    steps = availableSteps(STEPS, doc);
    if (!steps.length) return;
    card.hidden = false;
    show(0);
    next.focus();
  }

  doc.querySelector("#start-walk").addEventListener("click", start);
  doc.querySelector("#nav-walk").addEventListener("click", start);
  next.addEventListener("click", () => (index === steps.length - 1 ? leave() : show(index + 1, 1)));
  back.addEventListener("click", () => index > 0 && show(index - 1, -1));
  doc.querySelector("#walk-exit").addEventListener("click", leave);
  doc.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !card.hidden) leave();
  });
}
