// 3D port scene behind the hero, after the v0 "3D Cargo Warehouse" template (Rachata Suksereekul):
// a quay with two wireframe terminals, cranes and container stacks, and tankers from the research
// snapshot on the water. Clicking a tanker searches it. Purely decorative when WebGL is missing.
import * as THREE from "./vendor/three.module.min.js";

const NAVY = 0x00467f;
const BLUE = 0x0072ce;
const RED = 0xe60012;
const AMBER = 0xf59e0b;

/** Tankers named in the research snapshot; the tag is what the dossier shows first. */
export const SHIPS = [
  { name: "TASSOS", imo: "9408695", tag: "Listed by US, EU and UK", tone: "hit", x: -6, z: 15, heading: 0.25, sail: false },
  { name: "MERU", imo: "9187227", tag: "Flag changed since listing", tone: "change", x: 9, z: 22, heading: -0.35, sail: true },
  { name: "OCEAN 28", imo: "1021570", tag: "Listed by US", tone: "hit", x: 30, z: 30, heading: 0.1, sail: false },
  { name: "LADY JASMINE", imo: "1031537", tag: "Listed by EU", tone: "hit", x: 22, z: 13, heading: -0.15, sail: false },
];

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGL2RenderingContext && c.getContext("webgl2"));
  } catch {
    return false;
  }
}

const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0.05, ...extra });

function box(w, h, d, material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  m.position.set(x, y, z);
  return m;
}

function wireBox(w, h, d, color, x, y, z) {
  const g = new THREE.BoxGeometry(w, h, d);
  const lines = new THREE.LineSegments(new THREE.EdgesGeometry(g), new THREE.LineBasicMaterial({ color }));
  lines.position.set(x, y, z);
  return lines;
}

/** A terminal shed like the template's warehouses: glass walls, navy roof frame, racks inside. */
function terminal(w, d, x, z) {
  const g = new THREE.Group();
  const h = 4.2;
  g.add(box(w, 0.15, d, mat(0xf3f4f6), 0, 0.08, 0));
  const glass = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color: 0xe8f4fc, transparent: true, opacity: 0.18, depthWrite: false }));
  glass.position.y = h / 2;
  g.add(glass);
  g.add(wireBox(w, h, d, 0x9ca3af, 0, h / 2, 0));
  const roof = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(w, 0.01, d)), new THREE.LineBasicMaterial({ color: NAVY }));
  roof.position.y = h;
  g.add(roof);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) g.add(box(0.18, h, 0.18, mat(NAVY), (sx * w) / 2, h / 2, (sz * d) / 2));
  // wall grid, as in the template
  const grid = new THREE.LineBasicMaterial({ color: 0xc7ccd4 });
  const pts = [];
  for (let i = -w / 2; i <= w / 2 + 0.01; i += 1.4) pts.push(i, 0, d / 2, i, h, d / 2, i, 0, -d / 2, i, h, -d / 2);
  for (let k = 0.9; k < h; k += 0.9) pts.push(-w / 2, k, d / 2, w / 2, k, d / 2, -w / 2, k, -d / 2, w / 2, k, -d / 2);
  const gg = new THREE.BufferGeometry();
  gg.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  g.add(new THREE.LineSegments(gg, grid));
  // dock doors facing the quay
  for (const dx of [-w / 4, w / 4]) {
    g.add(box(2.2, 0.2, 0.2, mat(NAVY), dx, 3, d / 2));
    g.add(box(0.15, 3, 0.15, mat(NAVY), dx - 1.1, 1.5, d / 2));
    g.add(box(0.15, 3, 0.15, mat(NAVY), dx + 1.1, 1.5, d / 2));
    g.add(box(2.6, 0.04, 0.35, mat(0xfacc15), dx, 0.05, d / 2 + 0.4));
  }
  // racks with cargo
  const rackMat = mat(BLUE);
  const cargo = [mat(0xd6a15c), mat(0xc58b47), mat(0xe2b77a)];
  for (let rx = -w / 2 + 2.2; rx < w / 2 - 1.5; rx += 3.2) {
    for (let rz = -d / 2 + 2; rz < d / 2 - 2.5; rz += 3.4) {
      for (const px of [-0.9, 0.9]) for (const pz of [-0.4, 0.4]) g.add(box(0.07, 2.6, 0.07, rackMat, rx + px, 1.3, rz + pz));
      for (let lvl = 0; lvl < 3; lvl++) {
        g.add(box(1.9, 0.05, 0.9, rackMat, rx, 0.3 + lvl * 0.85, rz));
        if ((rx * 7 + rz * 3 + lvl) % 3 > 0.6) g.add(box(0.7, 0.45, 0.6, cargo[lvl % 3], rx - 0.4 + (lvl % 2) * 0.7, 0.55 + lvl * 0.85, rz));
      }
    }
  }
  g.position.set(x, 0, z);
  return g;
}

function crane(x, z) {
  const g = new THREE.Group();
  const m = mat(NAVY);
  for (const sx of [-1.2, 1.2]) for (const sz of [-1, 1]) g.add(box(0.25, 7, 0.25, m, sx, 3.5, sz));
  g.add(box(2.8, 0.35, 0.35, m, 0, 7, -1));
  g.add(box(2.8, 0.35, 0.35, m, 0, 7, 1));
  g.add(box(0.5, 0.4, 13, m, 0, 7.4, 3.5)); // boom out over the water
  g.add(box(1.2, 0.8, 1.2, mat(0xfacc15), 0, 6.6, 1.5));
  g.add(box(0.05, 2.5, 0.05, mat(0x334155), 0, 5.6, 7));
  g.position.set(x, 0, z);
  return g;
}

function containerStack(x, z, cols, rows, tiers) {
  const g = new THREE.Group();
  const palette = [NAVY, BLUE, 0x94a3b8, AMBER, 0xcbd5e1, RED];
  const geo = new THREE.BoxGeometry(2.4, 1, 1);
  let i = 0;
  for (let c = 0; c < cols; c++) for (let r = 0; r < rows; r++) {
    const t = 1 + ((c * 3 + r * 5) % tiers);
    for (let k = 0; k < t; k++) {
      const m = new THREE.Mesh(geo, mat(palette[(i++ * 7 + k) % palette.length]));
      m.position.set(x + c * 2.6, 0.5 + k * 1.02, z + r * 1.1);
      g.add(m);
    }
  }
  return g;
}

function tree(x, z, s = 1) {
  const g = new THREE.Group();
  g.add(box(0.25 * s, 2.4 * s, 0.25 * s, mat(0xd6c7b8), 0, 1.2 * s, 0));
  const pink = mat(0xf7c6d4, { roughness: 1 });
  for (const [dx, dy, dz, r] of [[0, 2.8, 0, 1.1], [0.8, 2.5, 0.2, 0.8], [-0.8, 2.6, -0.1, 0.85], [0.2, 3.4, -0.3, 0.75]]) {
    const b = new THREE.Mesh(new THREE.SphereGeometry(r * s, 14, 10), pink);
    b.position.set(dx * s, dy * s, dz * s);
    g.add(b);
  }
  g.position.set(x, 0, z);
  return g;
}

/** A tanker: pointed hull, deck piping, white bridge aft, funnel. Hull stripe carries the status. */
function tanker(ship) {
  const g = new THREE.Group();
  const L = 14, W = 2.6;
  const shape = new THREE.Shape();
  shape.moveTo(-L / 2, -W / 2);
  shape.lineTo(L / 2 - 2.2, -W / 2);
  shape.quadraticCurveTo(L / 2, 0, L / 2 - 2.2, W / 2);
  shape.lineTo(-L / 2, W / 2);
  shape.closePath();
  const hullGeo = new THREE.ExtrudeGeometry(shape, { depth: 1.4, bevelEnabled: false });
  hullGeo.rotateX(-Math.PI / 2);
  const tone = ship.tone === "change" ? AMBER : RED;
  const hull = new THREE.Mesh(hullGeo, mat(0x1f2937));
  hull.position.y = -0.6;
  g.add(hull);
  const stripeGeo = new THREE.ExtrudeGeometry(shape, { depth: 0.3, bevelEnabled: false });
  stripeGeo.rotateX(-Math.PI / 2);
  const stripe = new THREE.Mesh(stripeGeo, mat(tone));
  stripe.scale.set(1.004, 1, 1.02);
  stripe.position.y = -0.75;
  g.add(stripe);
  const deckGeo = new THREE.ShapeGeometry(shape);
  deckGeo.rotateX(-Math.PI / 2);
  const deck = new THREE.Mesh(deckGeo, mat(0x9f3a2c));
  deck.position.y = 0.81;
  g.add(deck);
  g.add(box(L * 0.62, 0.18, 0.25, mat(0xe5e7eb), 0.6, 0.95, 0));
  for (let i = -2; i <= 3; i++) g.add(box(0.12, 0.35, 1.6, mat(0xe5e7eb), i * 1.4, 1.0, 0));
  g.add(box(2.2, 1.8, 2.3, mat(0xffffff), -L / 2 + 1.4, 1.7, 0));
  g.add(box(1.4, 0.7, 2.6, mat(0xffffff), -L / 2 + 1.6, 2.95, 0));
  g.add(box(0.9, 0.15, 2.0, mat(0x0f172a), -L / 2 + 2.25, 3.0, 0));
  g.add(box(0.7, 1.3, 0.8, mat(tone), -L / 2 + 0.6, 3.3, 0));
  g.rotation.y = ship.heading;
  g.position.set(ship.x, 0, ship.z);
  g.userData.ship = ship;
  g.traverse((o) => { o.userData.ship = ship; });
  return g;
}

function road(x, z, len, along, width = 3.2) {
  const g = new THREE.Group();
  const r = new THREE.Mesh(new THREE.PlaneGeometry(along === "x" ? len : width, along === "x" ? width : len), mat(0xbfc4cc, { roughness: 1 }));
  r.rotation.x = -Math.PI / 2;
  r.position.set(x, 0.02, z);
  g.add(r);
  const dash = mat(0xffffff);
  for (let i = -len / 2 + 1; i < len / 2; i += 3) {
    const d = new THREE.Mesh(new THREE.PlaneGeometry(along === "x" ? 1.2 : 0.15, along === "x" ? 0.15 : 1.2), dash);
    d.rotation.x = -Math.PI / 2;
    d.position.set(along === "x" ? x + i : x, 0.03, along === "x" ? z : z + i);
    g.add(d);
  }
  return g;
}

function buildWorld(scene) {
  scene.add(new THREE.HemisphereLight(0xffffff, 0xdbe4ee, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.4);
  sun.position.set(-20, 40, 25);
  scene.add(sun);

  const land = new THREE.Mesh(new THREE.PlaneGeometry(240, 120), mat(0xeceef1, { roughness: 1 }));
  land.rotation.x = -Math.PI / 2;
  land.position.z = -60 + 4;
  scene.add(land);
  const grid = new THREE.GridHelper(240, 60, 0xd9dde3, 0xd9dde3);
  grid.position.set(0, 0.01, -56);
  grid.scale.z = 0.5;
  scene.add(grid);

  const sea = new THREE.Mesh(new THREE.PlaneGeometry(240, 120), new THREE.MeshStandardMaterial({ color: 0xbcd8ee, roughness: 0.35, metalness: 0.1 }));
  sea.rotation.x = -Math.PI / 2;
  sea.position.set(0, -0.35, 64);
  scene.add(sea);
  const quay = box(240, 0.6, 0.8, mat(NAVY), 0, -0.05, 4.2);
  scene.add(quay);
  const quayLine = box(240, 0.05, 0.3, mat(0xfacc15), 0, 0.27, 3.4);
  scene.add(quayLine);

  scene.add(terminal(17, 11, -14, -6));
  scene.add(terminal(13, 9, 12, -12));
  for (const cx of [-24, -3, 6, 25]) scene.add(crane(cx, 1.5));
  scene.add(containerStack(-2, -4, 3, 4, 3));
  scene.add(containerStack(24, -6, 4, 3, 3));
  scene.add(road(0, -21, 200, "x"));
  scene.add(road(-1, -8, 26, "z"));
  scene.add(road(30, -12, 18, "z"));
  for (const [x, z, s] of [[-40, -32, 1.2], [-30, -36, 1], [-18, -34, 1.1], [-4, -37, 1], [9, -33, 1.2], [20, -38, 1], [33, -32, 1.1], [44, -36, 1.3], [-48, -24, 1]]) scene.add(tree(x, z, s));
  // soft hills on the horizon, as in the template
  const hillMat = new THREE.MeshStandardMaterial({ color: 0xdfe8e1, roughness: 1 });
  for (const [x, z, r, sy] of [[60, -70, 34, 0.45], [-70, -80, 40, 0.35], [10, -95, 45, 0.3]]) {
    const h = new THREE.Mesh(new THREE.SphereGeometry(r, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), hillMat);
    h.scale.y = sy;
    h.position.set(x, 0, z);
    scene.add(h);
  }
}

/** Starts the scene in `host`; returns a stop function, or null when WebGL is unavailable. */
export function mountPortScene(host, { onPick = () => {}, labels } = {}) {
  if (!host || !webglAvailable()) return null;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  } catch {
    return null;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.prepend(renderer.domElement);
  renderer.domElement.setAttribute("aria-hidden", "true");

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xf4f7fb, 70, 160);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.5, 400);
  buildWorld(scene);

  const ships = SHIPS.map((s) => {
    const t = tanker(s);
    scene.add(t);
    return t;
  });

  const tags = new Map();
  if (labels) {
    for (const s of SHIPS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `ship-tag ship-tag--${s.tone}`;
      b.innerHTML = `<b>${s.name}</b><span>IMO ${s.imo} · ${s.tag}</span>`;
      b.addEventListener("click", () => onPick(s));
      labels.append(b);
      tags.set(s, b);
    }
  }

  // Orbit: drag rotates, ctrl/⌘ + wheel or pinch zooms, so plain scrolling still scrolls the page.
  const target = new THREE.Vector3(2, 0, 9);
  const orbit = { az: -0.5, pol: 0.92, dist: 92, auto: !reduce };
  const clampOrbit = () => {
    orbit.pol = Math.min(1.25, Math.max(0.45, orbit.pol));
    orbit.dist = Math.min(110, Math.max(28, orbit.dist));
  };
  const place = () => {
    camera.position.set(
      target.x + orbit.dist * Math.sin(orbit.pol) * Math.sin(orbit.az),
      target.y + orbit.dist * Math.cos(orbit.pol),
      target.z + orbit.dist * Math.sin(orbit.pol) * Math.cos(orbit.az),
    );
    camera.lookAt(target);
  };

  const el = renderer.domElement;
  let drag = null;
  el.addEventListener("pointerdown", (e) => {
    drag = { x: e.clientX, y: e.clientY, moved: 0 };
    el.setPointerCapture(e.pointerId);
    orbit.auto = false;
  });
  el.addEventListener("pointermove", (e) => {
    if (!drag) return hover(e);
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    drag.x = e.clientX;
    drag.y = e.clientY;
    orbit.az -= dx * 0.006;
    orbit.pol -= dy * 0.005;
    clampOrbit();
  });
  el.addEventListener("pointerup", (e) => {
    if (drag && drag.moved < 6) {
      const ship = pick(e);
      if (ship) onPick(ship);
    }
    drag = null;
  });
  el.addEventListener("wheel", (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    orbit.dist *= 1 + e.deltaY * 0.002;
    orbit.auto = false;
    clampOrbit();
  }, { passive: false });

  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  function pick(e) {
    const r = el.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(ships, true)[0];
    return hit?.object.userData.ship || null;
  }
  function hover(e) {
    const ship = pick(e);
    el.style.cursor = ship ? "pointer" : "grab";
    for (const [s, b] of tags) b.classList.toggle("is-hot", s === ship);
  }

  const size = () => {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // keep the quay in frame on narrow screens; on wide ones, centre the port right of the hero card
    camera.fov = w < 700 ? 52 : 38;
    if (w >= 1024) camera.setViewOffset(w, h, -w * 0.2, 0, w, h);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  };
  const ro = new ResizeObserver(size);
  ro.observe(host);
  size();

  let visible = true;
  const io = new IntersectionObserver(([en]) => { visible = en.isIntersecting; if (visible) loop(); });
  io.observe(host);

  const v = new THREE.Vector3();
  const clock = new THREE.Clock();
  let frame = 0;
  let stopped = false;
  function loop() {
    cancelAnimationFrame(frame);
    if (stopped || !visible || document.hidden) return;
    frame = requestAnimationFrame(loop);
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;
    if (orbit.auto) orbit.az += dt * 0.04;
    if (!reduce) {
      for (const g of ships) {
        const s = g.userData.ship;
        g.position.y = Math.sin(t * 1.1 + s.x) * 0.08;
        g.rotation.z = Math.sin(t * 0.8 + s.z) * 0.015;
        if (s.sail) {
          g.position.x = s.x + Math.sin(t * 0.05) * 14;
          g.rotation.y = s.heading + (Math.cos(t * 0.05) > 0 ? 0 : Math.PI);
        }
      }
    }
    place();
    renderer.render(scene, camera);
    if (tags.size) {
      const w = el.clientWidth, h = el.clientHeight;
      for (const [s, b] of tags) {
        const g = ships[SHIPS.indexOf(s)];
        v.set(g.position.x, 4.6, g.position.z).project(camera);
        const off = v.z > 1 || v.x < -1.1 || v.x > 1.1 || v.y < -1.1 || v.y > 1.1;
        b.hidden = off;
        if (off) continue;
        // keep the tag inside the scene so it never widens the page
        const half = b.offsetWidth / 2 + 4;
        const x = Math.min(w - half, Math.max(half, ((v.x + 1) / 2) * w));
        b.style.transform = `translate(${x}px, ${((1 - v.y) / 2) * h}px) translate(-50%, -100%)`;
      }
    }
  }
  const onVis = () => loop();
  document.addEventListener("visibilitychange", onVis);
  place();
  loop();

  return () => {
    stopped = true;
    cancelAnimationFrame(frame);
    ro.disconnect();
    io.disconnect();
    document.removeEventListener("visibilitychange", onVis);
    renderer.dispose();
  };
}
