function svg(body, fill) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${fill || "none"}" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

const ICONS = {
  anchor: svg('<circle cx="12" cy="5" r="2"/><path d="M12 7v13M5 13H2a10 10 0 0 0 20 0h-3"/>'),
  map: svg('<path d="M9 18l-6 3V6l6-3 6 3 6-3v15l-6 3-6-3z"/><path d="M9 3v15M15 6v15"/>'),
  chart: svg('<path d="M4 19V5M4 19h16"/><path d="M8 16v-5M12 16V8M16 16v-3"/>'),
  flask: svg('<path d="M9 3h6M10 3v6L5 20a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2L14 9V3"/>'),
  check: svg('<path d="M20 6L9 17l-5-5"/>'),
  user: svg('<circle cx="12" cy="8" r="3"/><path d="M5 19a7 7 0 0 1 14 0"/>'),
  cog: svg('<circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
  pin: svg('<path d="M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11z"/><circle cx="12" cy="10" r="2"/>'),
  target: svg('<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>'),
  refresh: svg('<path d="M21 12a9 9 0 1 1-2.6-6.3"/><path d="M21 3v6h-6"/>'),
  ship: svg('<path d="M3 17l2 3h14l2-3M4 17l8-8 8 8"/><path d="M12 9V3"/>'),
  clock: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>'),
  moon: svg('<path d="M21 14.5A8.5 8.5 0 1 1 9.5 3 7 7 0 0 0 21 14.5z"/>'),
  cloud: svg('<path d="M7 18h10a4 4 0 0 0 .4-8 6 6 0 0 0-11.6 2A3.5 3.5 0 0 0 7 18z"/>'),
  warning: svg('<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v4M12 17h.01"/>'),
  play: svg('<path d="M8 5l12 7-12 7V5z"/>'),
  globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'),
  search: svg('<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>'),
  expand: svg('<path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/>'),
  camera: svg('<path d="M4 7h3l2-2h6l2 2h3v12H4V7z"/><circle cx="12" cy="13" r="3"/>'),
  fuel: svg('<path d="M4 20V6a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v14"/><path d="M4 20h11M15 8h3l2 2v6a2 2 0 0 1-2 2h-3"/>'),
  money: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5c.6-.8 1.5-1 2.5-1s2 .4 2.5 1.2-.2 1.8-2.5 2.3-3.1 1-2.5 2.2.9 1.3 2.5 1.3 2-.3 2.5-1"/>'),
  leaf: svg('<path d="M5 19C5 11 11 5 20 4c0 9-6 15-15 15z"/><path d="M8 16c2-2 5-5 8-8"/>'),
  download: svg('<path d="M12 4v10M8 10l4 4 4-4M5 20h14"/>'),
  document: svg('<path d="M6 3h8l5 5v13H6V3z"/><path d="M14 3v5h5M8 13h8M8 17h6"/>'),
  ruler: svg('<path d="M4 20L20 4"/><path d="M8 16l2 2M11 13l2 2M14 10l2 2"/>'),
  scale: svg('<path d="M12 3v18M8 21h8M12 6l-7 8h5M12 6l7 8h-5"/>'),
  wave: svg('<path d="M2 15c2-3 4-3 6 0s4 3 6 0 4-3 6 0M2 9c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/>'),
  info: svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 8h.01"/>'),
  bolt: svg('<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>'),
  "chevron-down": svg('<path d="M6 9l6 6 6-6"/>'),
  "chevron-up": svg('<path d="M6 15l6-6 6 6"/>'),
  "arrow-left": svg('<path d="M19 12H5M12 5l-7 7 7 7"/>'),
  dot: svg('<circle cx="12" cy="12" r="5" fill="currentColor" stroke="none"/>'),
  x: svg('<path d="M6 6l12 12M18 6L6 18"/>'),
  shield: svg('<path d="M12 3l8 4v6c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V7l8-4z"/>'),
};

function icon(name) {
  const body = ICONS[name] || ICONS.dot;
  return `<span class="svg-icon" aria-hidden="true">${body}</span>`;
}

function hydrateIcons(root) {
  (root || document).querySelectorAll("[data-icon]").forEach((el) => {
    const name = el.getAttribute("data-icon");
    if (!ICONS[name] || el.dataset.hydrated === name) return;
    el.classList.add("svg-icon");
    el.setAttribute("aria-hidden", "true");
    el.innerHTML = ICONS[name];
    el.dataset.hydrated = name;
  });
}

document.addEventListener("DOMContentLoaded", () => hydrateIcons());
