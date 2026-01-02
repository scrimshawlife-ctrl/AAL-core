const STATE = {
  scene: null,
  animation: null,
  svg: null,
  time: 0,
  zoom: 1,
  offsetX: 0,
  offsetY: 0,
  sceneIndex: null,
  selection: {
    pinned: null,
    hover: null
  },
  compare: {
    enabled: false,
    active: null,
    sync: { A: null, B: null },
    A: { scene: null, sceneIndex: null, svgRoot: null, autoViewPlan: null },
    B: { scene: null, sceneIndex: null, svgRoot: null, autoViewPlan: null }
  },
  chrono: {
    enabled: false,
    index: null,
    runs: [],
    selectedA: null,
    selectedB: null
  },
  filters: {
    query: "",
    focus: false,
    showLabels: true,
    showHeatmap: true,
    edges: { transfer: true, resonance: true, synch: true }
  },
  toggles: {
    pulse: true,
    decay: true,
    transfer: true
  }
};

async function loadJSON(path) {
  const res = await fetch(path);
  return res.json();
}

async function tryLoadJSON(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function loadSVG(path) {
  const res = await fetch(path);
  return res.text();
}

async function loadText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`fetch failed: ${path}`);
  return await res.text();
}

function initPanZoom(svgEl) {
  let dragging = false;
  let lastX = 0, lastY = 0;

  svgEl.addEventListener("mousedown", e => {
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    svgEl.style.cursor = "grabbing";
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
    svgEl.style.cursor = "grab";
  });

  window.addEventListener("mousemove", e => {
    if (!dragging) return;
    STATE.offsetX += e.clientX - lastX;
    STATE.offsetY += e.clientY - lastY;
    lastX = e.clientX;
    lastY = e.clientY;
    applyTransform(svgEl);
  });

  svgEl.addEventListener("wheel", e => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 1.1 : 0.9;
    STATE.zoom *= delta;
    STATE.zoom = Math.max(0.2, Math.min(5, STATE.zoom));
    applyTransform(svgEl);
  });
}

function applyTransform(svgEl) {
  svgEl.style.transform =
    `translate(${STATE.offsetX}px, ${STATE.offsetY}px) scale(${STATE.zoom})`;
}

function buildSceneIndexFromScene(scene) {
  const idx = { entities: {}, edges: [] };
  if (!scene || !Array.isArray(scene.entities)) {
    return idx;
  }

  for (const e of scene.entities) {
    if (!e || !e.entity_id) continue;
    idx.entities[e.entity_id] = e;
  }

  if (Array.isArray(scene.edges)) {
    idx.edges = scene.edges;
  }

  return idx;
}

function buildSceneIndex() {
  const idx = buildSceneIndexFromScene(STATE.scene);
  STATE.sceneIndex = idx;
  return idx;
}

function applyAnimationPlan(svgEl) {
  if (!STATE.animation) return;

  const tNorm = STATE.time / 1000;

  if (STATE.toggles.pulse) {
    svgEl.querySelectorAll("path").forEach((p, i) => {
      const pulse = STATE.animation.modules?.pulse?.items?.[i];
      if (!pulse) return;
      const phase = (tNorm * 10) % 1;
      const amp = pulse.strength || 0.5;
      p.style.opacity = (0.2 + amp * Math.abs(Math.sin(Math.PI * phase))).toFixed(3);
    });
  }

  if (STATE.toggles.decay) {
    svgEl.querySelectorAll("circle").forEach(c => {
      const id = c.getAttribute("data-entity");
      if (!id) return;
      const decay = STATE.animation.modules?.decay?.items?.find(d => d.target.entity_id === id);
      if (!decay) return;
      const hl = decay.halflife_seconds || 86400;
      const factor = Math.exp(-tNorm * 1000 / hl);
      c.style.opacity = Math.max(0.15, factor).toFixed(3);
    });
  }

  applyHeatmapHooks(svgEl);
}

function applyHeatmapHooks(svgEl) {
  const heat = STATE.animation?.modules?.heatmap;
  if (!heat?.enabled) return;

  const decays = STATE.animation?.modules?.decay?.items || [];
  const decayMap = {};
  for (const d of decays) {
    const mid = d?.target?.entity_id;
    if (!mid) continue;
    const hl = d.halflife_seconds || 86400;
    const tNorm = STATE.time / 1000;
    const factor = Math.exp(-tNorm * 1000 / hl);
    decayMap[mid] = Math.max(0.15, factor);
  }

  let pulseEnv = 1.0;
  if (STATE.toggles.pulse) {
    const tNorm = STATE.time / 1000;
    const phase = (tNorm * 10) % 1;
    pulseEnv = 0.35 + 0.65 * Math.abs(Math.sin(Math.PI * phase));
  }

  svgEl.querySelectorAll('rect[data-heatmap="1"]').forEach(r => {
    const motif = r.getAttribute("data-motif");
    if (!motif) return;

    const base = parseFloat(r.getAttribute("opacity") || "0.05");
    let o = base;

    if (STATE.toggles.decay && decayMap[motif] !== undefined) {
      o = o * decayMap[motif];
    }
    if (STATE.toggles.pulse) {
      o = o * pulseEnv;
    }

    o = Math.max(0.03, Math.min(0.95, o));
    r.style.opacity = o.toFixed(3);
  });
}

const DATA_ROOT = "./demo";

function escHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function ensureTooltip() {
  let tip = document.getElementById("svgTooltip");
  if (tip) return tip;

  tip = document.createElement("div");
  tip.id = "svgTooltip";
  tip.style.position = "fixed";
  tip.style.pointerEvents = "none";
  tip.style.zIndex = "10000";
  tip.style.maxWidth = "360px";
  tip.style.padding = "8px 10px";
  tip.style.background = "rgba(255,255,255,0.95)";
  tip.style.border = "1px solid rgba(0,0,0,0.25)";
  tip.style.fontFamily = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";
  tip.style.fontSize = "12px";
  tip.style.lineHeight = "1.25";
  tip.style.display = "none";

  document.body.appendChild(tip);
  return tip;
}

function moveTooltip(tip, x, y) {
  const pad = 12;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let left = x + pad;
  let top = y + pad;

  tip.style.left = "0px";
  tip.style.top = "0px";
  tip.style.display = "block";

  const rect = tip.getBoundingClientRect();
  if (left + rect.width > vw - 6) left = x - rect.width - pad;
  if (top + rect.height > vh - 6) top = y - rect.height - pad;

  tip.style.left = Math.max(6, left) + "px";
  tip.style.top = Math.max(6, top) + "px";
}

function inspectTarget(el) {
  if (!el) return null;

  const d = (k) => el.getAttribute(k);

  const entityId = d("data-entity");
  const edgeType = d("data-edge");
  const src = d("data-src");
  const tgt = d("data-tgt");
  const motif = d("data-motif");
  const domain = d("data-domain");

  let kind = "unknown";
  if (entityId) kind = "entity";
  else if (edgeType || (src && tgt)) kind = "edge";
  else if (motif && domain) kind = "heatmap_cell";

  const payload = {
    kind,
    ids: { entity_id: entityId, edge_type: edgeType, src, tgt, motif, domain },
    svg: {
      tag: el.tagName,
      id: el.id || null,
      class: el.getAttribute("class") || null
    },
    scene: null
  };

  const idx = STATE.sceneIndex || { entities: {} };
  if (kind === "entity" && entityId && idx.entities && idx.entities[entityId]) {
    payload.scene = { entity: idx.entities[entityId] };
  }

  if (kind === "heatmap_cell" && motif && idx.entities && idx.entities[motif]) {
    payload.scene = payload.scene || {};
    payload.scene.motif = idx.entities[motif];
  }

  if (kind === "edge") {
    payload.scene = payload.scene || {};
    payload.scene.edge_match = null;

    const edges = (STATE.sceneIndex && Array.isArray(STATE.sceneIndex.edges))
      ? STATE.sceneIndex.edges
      : [];
    const match = edges.find(e => {
      if (!e) return false;
      if (edgeType && e.edge_type !== edgeType) return false;
      if (src && tgt) {
        const as = e.attributes?.source_domain;
        const at = e.attributes?.target_domain;
        if (as && at) return (as === src && at === tgt);
      }
      if (e.source && e.target && src && tgt) return (e.source === src && e.target === tgt);
      return false;
    });
    if (match) payload.scene.edge_match = match;
  }

  return payload;
}

function renderInspectionHtml(p) {
  if (!p) return "<div style='opacity:0.75'>(no selection)</div>";

  const ids = p.ids || {};
  const lines = [];

  lines.push(`<div><b>kind:</b> ${escHtml(p.kind)}</div>`);

  if (ids.entity_id) lines.push(`<div><b>entity:</b> ${escHtml(ids.entity_id)}</div>`);
  if (ids.edge_type) lines.push(`<div><b>edge_type:</b> ${escHtml(ids.edge_type)}</div>`);
  if (ids.src || ids.tgt) lines.push(`<div><b>src→tgt:</b> ${escHtml(ids.src || "")} → ${escHtml(ids.tgt || "")}</div>`);
  if (ids.motif || ids.domain) lines.push(`<div><b>cell:</b> motif ${escHtml(ids.motif || "")} × domain ${escHtml(ids.domain || "")}</div>`);

  const entity = p.scene?.entity || p.scene?.motif;
  if (entity && entity.attributes) {
    lines.push(`<div style="margin-top:6px;"><b>attributes</b></div>`);
    const keys = Object.keys(entity.attributes).sort().slice(0, 16);
    for (const k of keys) {
      lines.push(`<div style="opacity:0.85;">${escHtml(k)}: <span style="opacity:0.75;">${escHtml(JSON.stringify(entity.attributes[k]))}</span></div>`);
    }
  }

  const edge = p.scene?.edge_match;
  if (edge) {
    lines.push(`<div style="margin-top:6px;"><b>edge_match</b></div>`);
    lines.push(`<div style="opacity:0.85;">type: ${escHtml(edge.edge_type || "")} weight: ${escHtml(edge.weight ?? "")}</div>`);
    const attrs = edge.attributes || {};
    const keys = Object.keys(attrs).sort().slice(0, 10);
    for (const k of keys) {
      lines.push(`<div style="opacity:0.8;">${escHtml(k)}: <span style="opacity:0.7;">${escHtml(JSON.stringify(attrs[k]))}</span></div>`);
    }
  }

  return lines.join("");
}

function updateInspectorSelectionSection() {
  const content = document.getElementById("selection-details");
  if (!content) return;

  const pinned = STATE.selection?.pinned;
  content.innerHTML = `
    <div style="margin-top:10px; border-top:1px solid rgba(0,0,0,0.15); padding-top:8px;">
      <div style="font-weight:700;">Selection</div>
      <div style="margin-top:6px;">${renderInspectionHtml(pinned)}</div>
      <div style="margin-top:6px; opacity:0.7;">(click any marked element to pin • Esc clears)</div>
    </div>
  `;
}

function ensureBaseOpacity(el) {
  if (!el || el.dataset == null) return;
  if (el.dataset.baseOpacity !== undefined) return;

  const attr = el.getAttribute("opacity");
  const styleOpacity = el.style && el.style.opacity ? el.style.opacity : null;
  const base = (styleOpacity != null && styleOpacity !== "") ? parseFloat(styleOpacity)
    : (attr != null && attr !== "") ? parseFloat(attr)
      : 1.0;

  const value = Number.isFinite(base) ? base : 1.0;
  el.dataset.baseOpacity = String(value);
}

function elementKeyString(el) {
  const keys = [
    "data-entity", "data-edge", "data-motif", "data-domain", "data-src", "data-tgt"
  ];
  const parts = [];
  for (const k of keys) {
    const v = el.getAttribute(k);
    if (v) parts.push(v);
  }
  return parts.join(" ").toLowerCase();
}

function queryMatches(el, q) {
  if (!q) return true;
  return elementKeyString(el).includes(q);
}

function applySearchAndFilters(svgRoot) {
  if (!svgRoot) return;

  const q = (STATE.filters.query || "").trim().toLowerCase();
  const focus = !!STATE.filters.focus;
  const showLabels = !!STATE.filters.showLabels;
  const showHeatmap = !!STATE.filters.showHeatmap;
  const edgeEnabled = STATE.filters.edges || {};

  const inspectables = svgRoot.querySelectorAll(
    '[data-entity],[data-edge],[data-motif],[data-domain],[data-src],[data-tgt],text,rect[data-heatmap="1"]'
  );

  let total = 0;
  let matched = 0;
  let dimmed = 0;
  let hidden = 0;

  inspectables.forEach(el => {
    total += 1;
    ensureBaseOpacity(el);

    if (el.tagName.toLowerCase() === "text") {
      el.style.display = showLabels ? "block" : "none";
      if (!showLabels) hidden += 1;
      return;
    }

    const isHeat = el.tagName.toLowerCase() === "rect" && el.getAttribute("data-heatmap") === "1";
    if (isHeat && !showHeatmap) {
      el.style.display = "none";
      hidden += 1;
      return;
    } else if (isHeat) {
      el.style.display = "block";
    }

    const edgeType = el.getAttribute("data-edge");
    if (edgeType && edgeEnabled[edgeType] === false) {
      el.style.display = "none";
      hidden += 1;
      return;
    } else if (edgeType) {
      el.style.display = "block";
    }

    const ok = queryMatches(el, q);
    if (ok) matched += 1;

    const base = parseFloat(el.dataset.baseOpacity || "1.0");
    const baseO = Number.isFinite(base) ? base : 1.0;

    if (!q) {
      el.style.opacity = String(baseO);
      el.style.filter = "";
      el.style.outline = "";
      return;
    }

    if (ok) {
      el.style.opacity = String(Math.max(0.15, Math.min(1.0, baseO)));
      el.style.filter = "drop-shadow(0px 0px 1px rgba(0,0,0,0.45))";
      el.style.outline = "1px solid rgba(0,0,0,0.25)";
    } else {
      el.style.filter = "";
      el.style.outline = "";
      if (focus) {
        el.style.opacity = String(Math.max(0.02, baseO * 0.15));
        dimmed += 1;
      } else {
        el.style.opacity = String(baseO);
      }
    }
  });

  const stats = document.getElementById("filterStats");
  if (stats) {
    stats.textContent = `elements: ${total} • matched: ${matched} • dimmed: ${dimmed} • hidden: ${hidden}`;
  }
}

function applySearchAndFiltersAll() {
  if (STATE.compare?.enabled) {
    if (STATE.compare.A.svgRoot) applySearchAndFilters(STATE.compare.A.svgRoot);
    if (STATE.compare.B.svgRoot) applySearchAndFilters(STATE.compare.B.svgRoot);
    return;
  }
  if (STATE.svg) applySearchAndFilters(STATE.svg);
}

function initSearchAndFilterControls(svgRoot) {
  const q = document.getElementById("filterQuery");
  const focus = document.getElementById("focusMode");
  const labels = document.getElementById("showLabels");
  const heat = document.getElementById("showHeatmap");
  const edgeChecks = document.querySelectorAll(".edgeFilter");

  const saved = localStorage.getItem("aal_filter_state");
  if (saved) {
    try {
      STATE.filters = { ...STATE.filters, ...JSON.parse(saved) };
    } catch {
      // ignore corrupted state
    }
  }

  if (q) q.value = STATE.filters.query || "";
  if (focus) focus.checked = !!STATE.filters.focus;
  if (labels) labels.checked = !!STATE.filters.showLabels;
  if (heat) heat.checked = !!STATE.filters.showHeatmap;

  edgeChecks.forEach(ch => {
    const t = ch.getAttribute("data-edge-type");
    if (!t) return;
    ch.checked = STATE.filters.edges?.[t] !== false;
  });

  const persist = () => {
    localStorage.setItem("aal_filter_state", JSON.stringify(STATE.filters));
  };

  const apply = () => {
    persist();
    applySearchAndFiltersAll();
  };

  if (q) q.addEventListener("input", (e) => {
    STATE.filters.query = e.target.value || "";
    apply();
  });

  if (focus) focus.addEventListener("change", (e) => {
    STATE.filters.focus = !!e.target.checked;
    apply();
  });

  if (labels) labels.addEventListener("change", (e) => {
    STATE.filters.showLabels = !!e.target.checked;
    apply();
  });

  if (heat) heat.addEventListener("change", (e) => {
    STATE.filters.showHeatmap = !!e.target.checked;
    apply();
  });

  edgeChecks.forEach(ch => {
    ch.addEventListener("change", (e) => {
      const t = e.target.getAttribute("data-edge-type");
      if (!t) return;
      STATE.filters.edges[t] = !!e.target.checked;
      apply();
    });
  });

  apply();
}

function getTopLevelGroups(svgRoot) {
  if (!svgRoot) return [];
  const kids = Array.from(svgRoot.children || []);
  const groups = kids.filter(n => n.tagName && n.tagName.toLowerCase() === "g" && n.id);

  if (groups.length) return groups;

  const fallback = Array.from(svgRoot.querySelectorAll(":scope > g[id], :scope > g > g[id]"));
  const seen = new Set();
  const out = [];
  for (const g of fallback) {
    if (!g.id || seen.has(g.id)) continue;
    seen.add(g.id);
    out.push(g);
  }
  return out;
}

function loadLayerState() {
  try {
    const raw = localStorage.getItem("aal_layer_state");
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveLayerState(state) {
  try {
    localStorage.setItem("aal_layer_state", JSON.stringify(state));
  } catch {
    // ignore storage errors
  }
}

function applyLayerState(svgRoot, state) {
  const groups = getTopLevelGroups(svgRoot);
  for (const g of groups) {
    const on = (state[g.id] !== false);
    g.style.display = on ? "block" : "none";
  }
}

function applyLayerStateAll(state) {
  if (STATE.compare?.enabled) {
    if (STATE.compare.A.svgRoot) applyLayerState(STATE.compare.A.svgRoot, state);
    if (STATE.compare.B.svgRoot) applyLayerState(STATE.compare.B.svgRoot, state);
    return;
  }
  if (STATE.svg) applyLayerState(STATE.svg, state);
}

function buildLayerControls(svgRoot) {
  const host = document.getElementById("layerControls");
  if (!host || !svgRoot) return;

  const groups = getTopLevelGroups(svgRoot);
  const state = loadLayerState();

  host.innerHTML = "";
  if (!groups.length) {
    host.innerHTML = `<div style="opacity:0.75;">(no layers found)</div>`;
    return;
  }

  const wrap = document.createElement("div");
  wrap.style.display = "flex";
  wrap.style.flexDirection = "column";
  wrap.style.gap = "6px";

  for (const g of groups) {
    const id = g.id;
    const row = document.createElement("label");
    row.style.display = "flex";
    row.style.gap = "8px";
    row.style.alignItems = "center";
    row.style.cursor = "pointer";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = (state[id] !== false);

    cb.addEventListener("change", () => {
      state[id] = cb.checked;
      saveLayerState(state);
      applyLayerStateAll(state);
      applySearchAndFiltersAll();
    });

    const txt = document.createElement("span");
    txt.textContent = id;

    row.appendChild(cb);
    row.appendChild(txt);
    wrap.appendChild(row);
  }

  host.appendChild(wrap);

  const btnAll = document.getElementById("layersAll");
  const btnNone = document.getElementById("layersNone");
  const btnInvert = document.getElementById("layersInvert");

  const setAll = (val) => {
    for (const g of groups) state[g.id] = val;
    saveLayerState(state);
    buildLayerControls(svgRoot);
    applyLayerStateAll(state);
    applySearchAndFiltersAll();
  };

  if (btnAll) btnAll.onclick = () => setAll(true);
  if (btnNone) btnNone.onclick = () => setAll(false);

  if (btnInvert) btnInvert.onclick = () => {
    for (const g of groups) state[g.id] = !(state[g.id] !== false);
    saveLayerState(state);
    buildLayerControls(svgRoot);
    applyLayerStateAll(state);
    applySearchAndFiltersAll();
  };

  applyLayerStateAll(state);
}

function currentViewState() {
  const layers = loadLayerState();
  const filters = STATE.filters || {};
  const sel = STATE.selection || { pinned: null };
  const toggleInspector = document.getElementById("toggleInspector");

  return {
    schema: "ViewState.v0",
    version: "0.1.0",
    filters: filters,
    layers: layers,
    selection: { pinned: sel.pinned || null },
    inspector: { show: toggleInspector ? !!toggleInspector.checked : true }
  };
}

async function copyText(txt) {
  try {
    await navigator.clipboard.writeText(txt);
    return true;
  } catch {
    return false;
  }
}

function setViewStateStatus(msg) {
  const s = document.getElementById("viewStateStatus");
  if (s) s.textContent = msg;
}

function applyViewState(svgRoot, vs) {
  if (!vs || vs.schema !== "ViewState.v0") {
    throw new Error("Invalid schema (expected ViewState.v0).");
  }

  const toggleInspector = document.getElementById("toggleInspector");
  if (toggleInspector && vs.inspector && typeof vs.inspector.show === "boolean") {
    toggleInspector.checked = vs.inspector.show;
    toggleInspector.dispatchEvent(new Event("change"));
  }

  if (vs.filters) {
    STATE.filters = { ...STATE.filters, ...vs.filters };
    localStorage.setItem("aal_filter_state", JSON.stringify(STATE.filters));

    const q = document.getElementById("filterQuery");
    const focus = document.getElementById("focusMode");
    const labels = document.getElementById("showLabels");
    const heat = document.getElementById("showHeatmap");
    if (q) q.value = STATE.filters.query || "";
    if (focus) focus.checked = !!STATE.filters.focus;
    if (labels) labels.checked = !!STATE.filters.showLabels;
    if (heat) heat.checked = !!STATE.filters.showHeatmap;

    const edgeChecks = document.querySelectorAll(".edgeFilter");
    edgeChecks.forEach(ch => {
      const t = ch.getAttribute("data-edge-type");
      if (!t) return;
      ch.checked = STATE.filters.edges?.[t] !== false;
    });
  }

  if (vs.layers) {
    saveLayerState(vs.layers);
    buildLayerControls(svgRoot);
    applyLayerStateAll(vs.layers);
  } else {
    buildLayerControls(svgRoot);
  }

  STATE.selection = STATE.selection || {};
  STATE.selection.pinned = vs.selection?.pinned || null;

  const tip = ensureTooltip();
  if (STATE.selection.pinned) {
    tip.innerHTML = renderInspectionHtml(STATE.selection.pinned);
    tip.style.display = "block";
    tip.style.left = "12px";
    tip.style.top = "12px";
  } else {
    tip.style.display = "none";
  }

  applySearchAndFiltersAll();
  updateInspectorSelectionSection();
}

function initViewStateControls(svgRoot) {
  const exportBtn = document.getElementById("exportViewState");
  const copyBtn = document.getElementById("copyViewState");
  const importBtn = document.getElementById("importViewState");
  const box = document.getElementById("viewStateBox");
  const fileInput = document.getElementById("viewStateFile");

  if (!exportBtn || !copyBtn || !importBtn || !box) return;

  exportBtn.onclick = async () => {
    const vs = currentViewState();
    const txt = JSON.stringify(vs, null, 2);
    box.value = txt;

    const blob = new Blob([txt], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `viewstate.${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    setViewStateStatus("exported to textarea + downloaded json");
  };

  copyBtn.onclick = async () => {
    const vs = currentViewState();
    const txt = JSON.stringify(vs, null, 2);
    box.value = txt;
    const ok = await copyText(txt);
    setViewStateStatus(ok ? "copied ViewState to clipboard" : "clipboard copy failed");
  };

  importBtn.onclick = () => {
    const txt = box.value || "";
    if (txt.trim()) {
      try {
        const vs = JSON.parse(txt);
        applyViewState(svgRoot, vs);
        setViewStateStatus("imported ViewState");
      } catch (e) {
        setViewStateStatus("import failed: " + (e && e.message ? e.message : String(e)));
      }
      return;
    }
    if (fileInput) fileInput.click();
  };

  if (fileInput) {
    fileInput.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      try {
        const txt = await file.text();
        box.value = txt;
        const vs = JSON.parse(txt);
        applyViewState(svgRoot, vs);
        setViewStateStatus("imported ViewState from file");
      } catch (err) {
        setViewStateStatus("import failed: " + (err && err.message ? err.message : String(err)));
      } finally {
        fileInput.value = "";
      }
    });
  }
}

function b64urlDecode(s) {
  let str = s.replaceAll("-", "+").replaceAll("_", "/");
  while (str.length % 4) str += "=";
  return atob(str);
}

async function tryLoadViewStateFromQuery(svgRoot) {
  const params = new URLSearchParams(location.search);
  const st = params.get("state");
  if (!st) return false;
  try {
    const json = b64urlDecode(st);
    const vs = JSON.parse(json);
    applyViewState(svgRoot, vs);
    setViewStateStatus("loaded ViewState from URL");
    return true;
  } catch (e) {
    setViewStateStatus("failed to load state from URL: " + (e?.message || String(e)));
    return false;
  }
}

function setCompareEnabled(on) {
  STATE.compare.enabled = !!on;
  const singleWrap = document.getElementById("singleWrap");
  const compareWrap = document.getElementById("compareWrap");
  if (singleWrap) singleWrap.style.display = on ? "none" : "block";
  if (compareWrap) compareWrap.style.display = on ? "flex" : "none";
}

function setActivePanel(panelKey) {
  STATE.compare.active = panelKey;
}

function attachSvgInspectionHandlersForPanel(svgRoot, panelKey) {
  if (!svgRoot) return;
  const tip = ensureTooltip();

  function findInspectableTarget(evt) {
    let el = evt.target;
    while (el && el !== svgRoot) {
      if (
        el.hasAttribute("data-entity") ||
        el.hasAttribute("data-edge") ||
        el.hasAttribute("data-motif") ||
        el.hasAttribute("data-domain") ||
        el.hasAttribute("data-src") ||
        el.hasAttribute("data-tgt")
      ) {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  function inspectTargetPanel(el) {
    const savedSceneIndex = STATE.sceneIndex;
    STATE.sceneIndex = STATE.compare[panelKey].sceneIndex || { entities: {}, edges: [] };
    const p = inspectTarget(el);
    STATE.sceneIndex = savedSceneIndex;
    p.panel = panelKey;
    return p;
  }

  svgRoot.addEventListener("mousemove", (evt) => {
    if (STATE.selection?.pinned) return;
    const tgt = findInspectableTarget(evt);
    if (!tgt) {
      tip.style.display = "none";
      return;
    }
    const p = inspectTargetPanel(tgt);
    tip.innerHTML = renderInspectionHtml(p);
    moveTooltip(tip, evt.clientX, evt.clientY);
  });

  svgRoot.addEventListener("mouseleave", () => {
    if (STATE.selection?.pinned) return;
    tip.style.display = "none";
  });

  svgRoot.addEventListener("click", (evt) => {
    const tgt = findInspectableTarget(evt);
    if (!tgt) return;

    setActivePanel(panelKey);
    const p = inspectTargetPanel(tgt);
    STATE.selection.pinned = p;
    if (STATE.compare?.enabled) {
      syncSelectionAcrossPanels(p);
    }

    tip.innerHTML = renderInspectionHtml(p);
    moveTooltip(tip, evt.clientX, evt.clientY);
    tip.style.display = "block";

    updateInspectorSelectionSection();

    const q = document.getElementById("filterQuery");
    if (q) {
      const ids = p.ids || {};
      const token = ids.entity_id || ids.motif || ids.domain || ids.src || ids.tgt || "";
      if (token) {
        q.value = token;
        STATE.filters.query = token;
        const focus = document.getElementById("focusMode");
        if (focus && !focus.checked) {
          focus.checked = true;
          STATE.filters.focus = true;
        }
        applySearchAndFiltersAll();
      }
    }

    const tbox = document.getElementById("trendTarget");
    if (tbox) {
      const ids = p.ids || {};
      const token = ids.entity_id || ids.motif || ids.domain || "";
      if (token) tbox.value = token;
    }
  });
}

async function loadPanel(panelKey, svgUrl, sceneUrl, autoUrl) {
  const panel = STATE.compare[panelKey];
  panel.scene = sceneUrl ? await loadJSON(sceneUrl) : null;
  panel.autoViewPlan = autoUrl ? await tryLoadJSON(autoUrl) : null;
  panel.sceneIndex = buildSceneIndexFromScene(panel.scene);

  const svgText = svgUrl ? await loadText(svgUrl) : "<svg></svg>";
  return { svgText };
}

function wireCompareToggle() {
  const t = document.getElementById("compareToggle");
  if (!t) return;
  t.addEventListener("change", () => {
    const on = !!t.checked;
    setCompareEnabled(on);
    renderDiffPanel();
  });
}

async function initCompareFromQuery() {
  const params = new URLSearchParams(location.search);
  const enabled = params.get("compare") === "1";
  const toggle = document.getElementById("compareToggle");
  if (toggle) toggle.checked = enabled;
  setCompareEnabled(enabled);

  if (!enabled) return false;

  const svgA = params.get("svgA");
  const sceneA = params.get("sceneA");
  const autoA = params.get("autoA");
  const svgB = params.get("svgB");
  const sceneB = params.get("sceneB");
  const autoB = params.get("autoB");

  const a = await loadPanel("A", svgA, sceneA, autoA);
  const b = await loadPanel("B", svgB, sceneB, autoB);

  document.getElementById("svgContainerA").innerHTML = a.svgText;
  document.getElementById("svgContainerB").innerHTML = b.svgText;

  const svgElA = document.querySelector("#svgContainerA svg");
  const svgElB = document.querySelector("#svgContainerB svg");

  STATE.compare.A.svgRoot = svgElA;
  STATE.compare.B.svgRoot = svgElB;

  attachSvgInspectionHandlersForPanel(svgElA, "A");
  attachSvgInspectionHandlersForPanel(svgElB, "B");

  initSearchAndFilterControls(svgElA);
  buildLayerControls(svgElA);

  const layerState = loadLayerState();
  applyLayerStateAll(layerState);
  applySearchAndFiltersAll();

  renderDiffPanel();
  renderSelectionCompare();
  return true;
}

async function loadRunIndex(url) {
  const idx = await loadJSON(url);
  if (!idx || idx.schema !== "RunIndex.v0" || !Array.isArray(idx.runs)) {
    throw new Error("Invalid RunIndex (expected schema RunIndex.v0).");
  }

  const runs = idx.runs.slice().sort((a, b) => {
    const ia = String(a.id || "");
    const ib = String(b.id || "");
    if (ia < ib) return -1;
    if (ia > ib) return 1;
    return 0;
  });

  STATE.chrono.index = idx;
  STATE.chrono.runs = runs;
  return runs;
}

function runOptionLabel(r) {
  const id = String(r.id || "");
  const label = r.label ? String(r.label) : "";
  return label ? `${label} — ${id}` : id;
}

function populateRunSelects() {
  const selA = document.getElementById("runSelectA");
  const selB = document.getElementById("runSelectB");
  if (!selA || !selB) return;

  const runs = STATE.chrono.runs || [];
  selA.innerHTML = "";
  selB.innerHTML = "";

  for (const r of runs) {
    const optA = document.createElement("option");
    optA.value = r.id;
    optA.textContent = runOptionLabel(r);
    selA.appendChild(optA);

    const optB = document.createElement("option");
    optB.value = r.id;
    optB.textContent = runOptionLabel(r);
    selB.appendChild(optB);
  }

  if (runs.length >= 2) {
    STATE.chrono.selectedA = STATE.chrono.selectedA || runs[runs.length - 2].id;
    STATE.chrono.selectedB = STATE.chrono.selectedB || runs[runs.length - 1].id;
  } else if (runs.length === 1) {
    STATE.chrono.selectedA = runs[0].id;
    STATE.chrono.selectedB = runs[0].id;
  }

  selA.value = STATE.chrono.selectedA || "";
  selB.value = STATE.chrono.selectedB || "";
}

function findRunById(id) {
  const runs = STATE.chrono.runs || [];
  return runs.find(r => String(r.id) === String(id)) || null;
}

async function loadCompareFromRuns() {
  const a = findRunById(STATE.chrono.selectedA);
  const b = findRunById(STATE.chrono.selectedB);
  if (!a || !b) throw new Error("Selected runs not found in index.");

  STATE.compare.enabled = true;
  setCompareEnabled(true);

  const A = await loadPanel("A", a.svg, a.scene, a.auto);
  const B = await loadPanel("B", b.svg, b.scene, b.auto);

  const ca = document.getElementById("svgContainerA");
  const cb = document.getElementById("svgContainerB");
  if (!ca || !cb) throw new Error("Compare containers missing.");

  ca.innerHTML = A.svgText;
  cb.innerHTML = B.svgText;

  const svgElA = document.querySelector("#svgContainerA svg");
  const svgElB = document.querySelector("#svgContainerB svg");

  STATE.compare.A.svgRoot = svgElA;
  STATE.compare.B.svgRoot = svgElB;

  attachSvgInspectionHandlersForPanel(svgElA, "A");
  attachSvgInspectionHandlersForPanel(svgElB, "B");

  initSearchAndFilterControls(svgElA);
  buildLayerControls(svgElA);

  const layerState = loadLayerState();
  applyLayerStateAll(layerState);
  applySearchAndFiltersAll();

  renderDiffPanel();
  renderSelectionCompare();

  STATE.autoViewPlan = STATE.compare.A.autoViewPlan || null;
  renderAutoLensInspector();
  updateInspectorSelectionSection();
}

function setChronoEnabled(on) {
  STATE.chrono.enabled = !!on;
  if (STATE.chrono.enabled) {
    setCompareEnabled(true);
    STATE.compare.enabled = true;
  }

  const bar = document.getElementById("chronoBar");
  if (bar) bar.style.opacity = STATE.chrono.enabled ? "1.0" : "0.85";
}

function wireChronoscopeControls() {
  const toggle = document.getElementById("chronoToggle");
  const urlBox = document.getElementById("runIndexUrl");
  const loadBtn = document.getElementById("loadRunIndex");
  const selA = document.getElementById("runSelectA");
  const selB = document.getElementById("runSelectB");
  const swap = document.getElementById("swapRuns");

  if (toggle) {
    toggle.addEventListener("change", async () => {
      setChronoEnabled(!!toggle.checked);

      if (STATE.chrono.enabled && STATE.chrono.runs.length >= 1) {
        try {
          await loadCompareFromRuns();
        } catch (e) {
          setViewStateStatus("chronoscope load failed: " + (e?.message || String(e)));
        }
      }
    });
  }

  if (loadBtn && urlBox) {
    loadBtn.onclick = async () => {
      try {
        const url = (urlBox.value || "").trim();
        if (!url) {
          setViewStateStatus("enter RunIndex URL");
          return;
        }

        const runs = await loadRunIndex(url);
        populateRunSelects();
        setViewStateStatus(`loaded RunIndex: ${runs.length} runs`);

        if (toggle && !toggle.checked) {
          toggle.checked = true;
          setChronoEnabled(true);
        }

        await loadCompareFromRuns();
      } catch (e) {
        setViewStateStatus("RunIndex load failed: " + (e?.message || String(e)));
      }
    };
  }

  if (selA) {
    selA.addEventListener("change", async () => {
      STATE.chrono.selectedA = selA.value;
      if (!STATE.chrono.enabled) return;
      try {
        await loadCompareFromRuns();
      } catch (e) {
        setViewStateStatus("reload failed: " + (e?.message || String(e)));
      }
    });
  }

  if (selB) {
    selB.addEventListener("change", async () => {
      STATE.chrono.selectedB = selB.value;
      if (!STATE.chrono.enabled) return;
      try {
        await loadCompareFromRuns();
      } catch (e) {
        setViewStateStatus("reload failed: " + (e?.message || String(e)));
      }
    });
  }

  if (swap) {
    swap.onclick = async () => {
      const a = STATE.chrono.selectedA;
      STATE.chrono.selectedA = STATE.chrono.selectedB;
      STATE.chrono.selectedB = a;

      if (selA) selA.value = STATE.chrono.selectedA;
      if (selB) selB.value = STATE.chrono.selectedB;

      if (!STATE.chrono.enabled) return;
      try {
        await loadCompareFromRuns();
      } catch (e) {
        setViewStateStatus("swap reload failed: " + (e?.message || String(e)));
      }
    };
  }
}

async function tryLoadChronoFromQuery() {
  const params = new URLSearchParams(location.search);
  if (params.get("chrono") !== "1") return false;

  const toggle = document.getElementById("chronoToggle");
  const urlBox = document.getElementById("runIndexUrl");

  const indexUrl = params.get("index");
  if (urlBox && indexUrl) urlBox.value = indexUrl;

  if (indexUrl) {
    const runs = await loadRunIndex(indexUrl);
    populateRunSelects();

    const a = params.get("a");
    const b = params.get("b");
    if (a) STATE.chrono.selectedA = a;
    if (b) STATE.chrono.selectedB = b;

    populateRunSelects();

    if (toggle) toggle.checked = true;
    setChronoEnabled(true);

    await loadCompareFromRuns();
    setViewStateStatus(`chronoscope loaded from URL (${runs.length} runs)`);
    return true;
  }

  return false;
}

function countsByType(scene) {
  const ent = {};
  const ed = {};
  if (scene?.entities) {
    for (const e of scene.entities) {
      ent[e.entity_type] = (ent[e.entity_type] || 0) + 1;
    }
  }
  if (scene?.edges) {
    for (const x of scene.edges) {
      ed[x.edge_type] = (ed[x.edge_type] || 0) + 1;
    }
  }
  return { ent, ed };
}

function setOfIds(scene, entityType) {
  const s = new Set();
  if (!scene?.entities) return s;
  for (const e of scene.entities) {
    if (e.entity_type === entityType) s.add(e.entity_id);
  }
  return s;
}

function motifSalienceMap(scene) {
  const m = new Map();
  if (!scene?.entities) return m;
  for (const e of scene.entities) {
    if (e.entity_type !== "motif") continue;
    const sal = Number(e.attributes?.salience);
    if (Number.isFinite(sal)) m.set(e.entity_id, sal);
  }
  return m;
}

function transferPairWeights(scene) {
  const m = new Map();
  if (!scene?.edges) return m;
  for (const ed of scene.edges) {
    if (ed.edge_type !== "transfer") continue;
    const s = ed.attributes?.source_domain;
    const t = ed.attributes?.target_domain;
    if (!s || !t) continue;
    const key = `${s}→${t}`;
    const w = Number(ed.weight);
    m.set(key, (m.get(key) || 0) + (Number.isFinite(w) ? w : 0));
  }
  return m;
}

function topDeltas(mapA, mapB, cap = 25) {
  const keys = new Set([...mapA.keys(), ...mapB.keys()]);
  const out = [];
  for (const k of keys) {
    const a = mapA.get(k) || 0;
    const b = mapB.get(k) || 0;
    const d = b - a;
    if (d !== 0) out.push({ k, a, b, d });
  }
  out.sort((x, y) => Math.abs(y.d) - Math.abs(x.d) || (x.k < y.k ? -1 : 1));
  return out.slice(0, cap);
}

function renderDiffPanel() {
  const host = document.getElementById("diffPanel");
  if (!host) return;

  if (!STATE.compare.enabled) {
    host.textContent = "(Compare Mode off)";
    return;
  }

  const A = STATE.compare.A.scene;
  const B = STATE.compare.B.scene;
  if (!A || !B) {
    host.textContent = "Compare Mode enabled but sceneA/sceneB not loaded.\nProvide ?compare=1&sceneA=...&sceneB=... (and svgA/svgB).";
    return;
  }

  const cA = countsByType(A);
  const cB = countsByType(B);

  function fmtCountsDelta(aObj, bObj) {
    const keys = Array.from(new Set([...Object.keys(aObj), ...Object.keys(bObj)])).sort();
    return keys.map(k => {
      const a = aObj[k] || 0;
      const b = bObj[k] || 0;
      const d = b - a;
      const sign = d > 0 ? "+" : "";
      return `${k}: ${a} → ${b} (${sign}${d})`;
    }).join("\n");
  }

  const motifsA = setOfIds(A, "motif");
  const motifsB = setOfIds(B, "motif");
  const newMotifs = Array.from([...motifsB].filter(x => !motifsA.has(x))).sort().slice(0, 20);
  const goneMotifs = Array.from([...motifsA].filter(x => !motifsB.has(x))).sort().slice(0, 20);

  const domA = setOfIds(A, "domain");
  const domB = setOfIds(B, "domain");
  const newDom = Array.from([...domB].filter(x => !domA.has(x))).sort().slice(0, 20);
  const goneDom = Array.from([...domA].filter(x => !domB.has(x))).sort().slice(0, 20);

  const salA = motifSalienceMap(A);
  const salB = motifSalienceMap(B);
  const salD = topDeltas(salA, salB, 25);

  const trA = transferPairWeights(A);
  const trB = transferPairWeights(B);
  const trD = topDeltas(trA, trB, 25);

  const lines = [];
  lines.push("ENTITY COUNTS Δ (A → B)");
  lines.push(fmtCountsDelta(cA.ent, cB.ent));
  lines.push("");
  lines.push("EDGE COUNTS Δ (A → B)");
  lines.push(fmtCountsDelta(cA.ed, cB.ed));
  lines.push("");
  lines.push("NEW MOTIFS (B not in A): " + (newMotifs.length ? newMotifs.join(", ") : "(none)"));
  lines.push("REMOVED MOTIFS (A not in B): " + (goneMotifs.length ? goneMotifs.join(", ") : "(none)"));
  lines.push("NEW DOMAINS: " + (newDom.length ? newDom.join(", ") : "(none)"));
  lines.push("REMOVED DOMAINS: " + (goneDom.length ? goneDom.join(", ") : "(none)"));
  lines.push("");

  lines.push("TOP MOTIF SALIENCE CHANGES (B - A)");
  if (!salD.length) lines.push("(no numeric salience deltas)");
  else {
    for (const r of salD) {
      const sign = r.d > 0 ? "+" : "";
      lines.push(`${r.k}: ${r.a.toFixed(3)} → ${r.b.toFixed(3)} (${sign}${r.d.toFixed(3)})`);
    }
  }
  lines.push("");

  lines.push("TOP TRANSFER PAIR WEIGHT CHANGES (B - A)");
  if (!trD.length) lines.push("(no transfer deltas)");
  else {
    for (const r of trD) {
      const sign = r.d > 0 ? "+" : "";
      lines.push(`${r.k}: ${r.a.toFixed(3)} → ${r.b.toFixed(3)} (${sign}${r.d.toFixed(3)})`);
    }
  }

  host.textContent = lines.join("\n");
}

function getPanelSceneIndex(panelKey) {
  return STATE.compare?.[panelKey]?.sceneIndex || { entities: {}, edges: [] };
}

function getPanelScene(panelKey) {
  return STATE.compare?.[panelKey]?.scene || null;
}

function findEntityById(panelKey, entityId) {
  const idx = getPanelSceneIndex(panelKey);
  return (idx.entities && entityId && idx.entities[entityId]) ? idx.entities[entityId] : null;
}

function findTransferWeight(panelKey, src, tgt) {
  const scene = getPanelScene(panelKey);
  if (!scene?.edges) return null;
  let sum = 0;
  let found = false;
  for (const ed of scene.edges) {
    if (ed.edge_type !== "transfer") continue;
    const s = ed.attributes?.source_domain;
    const t = ed.attributes?.target_domain;
    if (s === src && t === tgt) {
      const w = Number(ed.weight);
      sum += (Number.isFinite(w) ? w : 0);
      found = true;
    }
  }
  return found ? sum : null;
}

function diffAttributes(attrsA, attrsB, cap = 24) {
  const a = attrsA || {};
  const b = attrsB || {};
  const keys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).sort();
  const out = [];
  for (const k of keys) {
    const va = a[k];
    const vb = b[k];
    const ja = JSON.stringify(va);
    const jb = JSON.stringify(vb);
    if (ja !== jb) out.push({ k, a: ja, b: jb });
  }
  out.sort((x, y) => x.k < y.k ? -1 : x.k > y.k ? 1 : 0);
  return out.slice(0, cap);
}

function renderSelectionCompare() {
  const host = document.getElementById("selectionCompare");
  if (!host) return;

  if (!STATE.compare?.enabled) {
    host.textContent = "(Compare Mode off)";
    return;
  }

  const A = STATE.compare.sync.A;
  const B = STATE.compare.sync.B;

  if (!A && !B) {
    host.textContent = "(no pinned selection)";
    return;
  }

  const left = A || { panel: "A", kind: "none", ids: {} };
  const right = B || { panel: "B", kind: "none", ids: {} };

  const lines = [];
  lines.push(`A: ${left.kind || "none"} ${JSON.stringify(left.ids || {})}`);
  lines.push(`B: ${right.kind || "none"} ${JSON.stringify(right.ids || {})}`);
  lines.push("");

  const entA = left.scene?.entity || left.scene?.motif || null;
  const entB = right.scene?.entity || right.scene?.motif || null;

  if (entA && entB) {
    lines.push("ENTITY ATTRIBUTES Δ");
    const diffs = diffAttributes(entA.attributes || {}, entB.attributes || {}, 32);
    if (!diffs.length) {
      lines.push("(no attribute deltas)");
    } else {
      for (const d of diffs) {
        lines.push(`${d.k}: A=${d.a}  |  B=${d.b}`);
      }
    }
    lines.push("");
  } else if (entA && !entB) {
    lines.push("Entity present on A but missing on B.");
    lines.push("");
  } else if (!entA && entB) {
    lines.push("Entity present on B but missing on A.");
    lines.push("");
  }

  const idsA = left.ids || {};
  const idsB = right.ids || {};

  const isTransfer = (idsA.edge_type === "transfer" || (idsA.src && idsA.tgt)) ||
    (idsB.edge_type === "transfer" || (idsB.src && idsB.tgt));

  if (isTransfer) {
    const src = idsA.src || idsB.src;
    const tgt = idsA.tgt || idsB.tgt;
    const wA = findTransferWeight("A", src, tgt);
    const wB = findTransferWeight("B", src, tgt);
    lines.push("TRANSFER WEIGHT Δ");
    lines.push(`${src}→${tgt}: A=${wA === null ? "missing" : wA.toFixed(3)}  |  B=${wB === null ? "missing" : wB.toFixed(3)}`);
  }

  host.textContent = lines.join("\n");
}

function syncSelectionAcrossPanels(pinned) {
  if (!STATE.compare?.enabled) return;

  const panel = pinned?.panel;
  if (panel !== "A" && panel !== "B") return;

  const other = (panel === "A") ? "B" : "A";
  const ids = pinned?.ids || {};

  let otherPinned = null;

  if (ids.entity_id) {
    const ent = findEntityById(other, ids.entity_id);
    if (ent) {
      otherPinned = {
        panel: other,
        kind: "entity",
        ids: { entity_id: ids.entity_id },
        scene: { entity: ent }
      };
    }
  }

  if (!otherPinned && ids.motif && ids.domain) {
    const motif = findEntityById(other, ids.motif);
    if (motif) {
      otherPinned = {
        panel: other,
        kind: "heatmap_cell",
        ids: { motif: ids.motif, domain: ids.domain },
        scene: { motif: motif }
      };
    }
  }

  if (!otherPinned && (ids.edge_type === "transfer" || (ids.src && ids.tgt))) {
    const w = findTransferWeight(other, ids.src, ids.tgt);
    if (w !== null) {
      otherPinned = {
        panel: other,
        kind: "edge",
        ids: { edge_type: "transfer", src: ids.src, tgt: ids.tgt },
        scene: { edge_match: { edge_type: "transfer", weight: w, attributes: { source_domain: ids.src, target_domain: ids.tgt } } }
      };
    }
  }

  if (panel === "A") {
    STATE.compare.sync.A = pinned;
    STATE.compare.sync.B = otherPinned;
  } else {
    STATE.compare.sync.B = pinned;
    STATE.compare.sync.A = otherPinned;
  }

  renderSelectionCompare();
}

function setTrendStatus(msg) {
  const s = document.getElementById("trendStatus");
  if (s) s.textContent = msg;
}

function isDomainId(id) {
  return typeof id === "string" && id.startsWith("d.");
}

function isMotifId(id) {
  return typeof id === "string" && id.startsWith("m.");
}

async function loadSceneForRun(run) {
  return await loadJSON(run.scene);
}

function motifSalienceFromScene(scene, motifId) {
  if (!scene?.entities) return null;
  const e = scene.entities.find(x => x.entity_id === motifId);
  if (!e) return null;
  const v = Number(e.attributes?.salience);
  return Number.isFinite(v) ? v : null;
}

function motifTopNeighborsFromScene(scene, motifId, cap = 12) {
  if (!scene?.edges) return new Set();

  const agg = new Map();
  for (const ed of scene.edges) {
    const t = ed.edge_type;
    if (t !== "resonance" && t !== "synch") continue;
    if (ed.source !== motifId && ed.target !== motifId) continue;
    const nb = (ed.source === motifId) ? ed.target : ed.source;
    if (!nb) continue;
    const w = Number(ed.weight);
    agg.set(nb, (agg.get(nb) || 0) + (Number.isFinite(w) ? w : 0));
  }

  const rows = Array.from(agg.entries()).map(([k, w]) => ({ k, w }));
  rows.sort((a, b) => (b.w - a.w) || (a.k < b.k ? -1 : 1));
  return new Set(rows.slice(0, cap).map(r => r.k));
}

function jaccard(aSet, bSet) {
  const a = aSet || new Set();
  const b = bSet || new Set();
  if (a.size === 0 && b.size === 0) return 1.0;

  let inter = 0;
  for (const x of a) if (b.has(x)) inter += 1;
  const uni = a.size + b.size - inter;
  return uni === 0 ? 1.0 : (inter / uni);
}

function domainTransferFlows(scene, domainId) {
  let inbound = 0;
  let outbound = 0;
  let saw = false;
  if (!scene?.edges) return { inbound: null, outbound: null, net: null };

  for (const ed of scene.edges) {
    if (ed.edge_type !== "transfer") continue;
    const s = ed.attributes?.source_domain;
    const t = ed.attributes?.target_domain;
    if (!s || !t) continue;

    const w = Number(ed.weight);
    const ww = Number.isFinite(w) ? w : 0;

    if (t === domainId) {
      inbound += ww;
      saw = true;
    }
    if (s === domainId) {
      outbound += ww;
      saw = true;
    }
  }

  if (!saw) return { inbound: null, outbound: null, net: null };
  return { inbound, outbound, net: outbound - inbound };
}

async function computeTrends(targetId) {
  const runs = (STATE.chrono?.runs || []).slice();
  if (!runs.length) throw new Error("No runs loaded. Load RunIndex.v0 first (Chronoscope).");

  const points = [];

  if (isMotifId(targetId)) {
    let prevNbrs = null;

    for (const r of runs) {
      const scene = await loadSceneForRun(r);
      const sal = motifSalienceFromScene(scene, targetId);
      const nbrs = motifTopNeighborsFromScene(scene, targetId, 12);
      const jac = prevNbrs ? jaccard(prevNbrs, nbrs) : null;
      prevNbrs = nbrs;

      points.push({
        run_id: r.id,
        label: r.label || null,
        salience: sal,
        neighbor_jaccard_prev: jac,
        neighbor_count: nbrs.size
      });
    }

    return { schema: "TrendPack.v0", version: "0.1.0", kind: "motif", target: targetId, points };
  }

  if (isDomainId(targetId)) {
    for (const r of runs) {
      const scene = await loadSceneForRun(r);
      const f = domainTransferFlows(scene, targetId);
      points.push({
        run_id: r.id,
        label: r.label || null,
        inbound: f.inbound,
        outbound: f.outbound,
        net: f.net
      });
    }
    return { schema: "TrendPack.v0", version: "0.1.0", kind: "domain", target: targetId, points };
  }

  throw new Error("Target must look like m.* (motif) or d.* (domain).");
}

function renderTrendsText(tr) {
  const lines = [];
  lines.push(tr.schema || "TrendPack.v0");
  lines.push(`kind: ${tr.kind}`);
  lines.push(`target: ${tr.target}`);
  lines.push("");

  if (tr.kind === "motif") {
    lines.push("run_id | salience | nbr_count | jaccard(prev)");
    lines.push("---------------------------------------------");
    for (const p of tr.points) {
      const sal = (p.salience === null) ? "n/a" : p.salience.toFixed(3);
      const jac = (p.neighbor_jaccard_prev === null) ? "n/a" : p.neighbor_jaccard_prev.toFixed(3);
      lines.push(`${p.run_id} | ${sal} | ${p.neighbor_count} | ${jac}`);
    }

    const salVals = tr.points.map(p => p.salience).filter(v => v !== null);
    if (salVals.length >= 2) {
      const first = salVals[0];
      const last = salVals[salVals.length - 1];
      const d = last - first;
      const sign = d > 0 ? "+" : "";
      lines.push("");
      lines.push(`salience_delta(first→last): ${first.toFixed(3)} → ${last.toFixed(3)} (${sign}${d.toFixed(3)})`);
    }

    return lines.join("\n");
  }

  if (tr.kind === "domain") {
    lines.push("run_id | inbound | outbound | net(out-in)");
    lines.push("----------------------------------------");
    for (const p of tr.points) {
      const ib = (p.inbound === null) ? "n/a" : p.inbound.toFixed(3);
      const ob = (p.outbound === null) ? "n/a" : p.outbound.toFixed(3);
      const net = (p.net === null) ? "n/a" : p.net.toFixed(3);
      lines.push(`${p.run_id} | ${ib} | ${ob} | ${net}`);
    }
    return lines.join("\n");
  }

  return JSON.stringify(tr, null, 2);
}

function initTrendControls() {
  const box = document.getElementById("trendTarget");
  const runBtn = document.getElementById("runTrends");
  const copyBtn = document.getElementById("copyTrends");
  const out = document.getElementById("trendOut");
  if (!box || !runBtn || !copyBtn || !out) return;

  runBtn.onclick = async () => {
    const target = (box.value || "").trim();
    if (!target) {
      setTrendStatus("enter a target id");
      return;
    }

    setTrendStatus("running…");
    try {
      const tr = await computeTrends(target);
      const txt = renderTrendsText(tr);
      out.textContent = txt;
      setTrendStatus("done");
      STATE.lastTrends = tr;
    } catch (e) {
      setTrendStatus("failed: " + (e?.message || String(e)));
    }
  };

  copyBtn.onclick = async () => {
    const txt = out.textContent || "";
    if (!txt) {
      setTrendStatus("nothing to copy");
      return;
    }
    const ok = await copyText(txt);
    setTrendStatus(ok ? "copied trends" : "copy failed");
  };
}

function attachSvgInspectionHandlers(svgRoot) {
  if (!svgRoot) return;
  const tip = ensureTooltip();

  function findInspectableTarget(evt) {
    let el = evt.target;
    while (el && el !== svgRoot) {
      if (
        el.hasAttribute("data-entity") ||
        el.hasAttribute("data-edge") ||
        el.hasAttribute("data-motif") ||
        el.hasAttribute("data-domain") ||
        el.hasAttribute("data-src") ||
        el.hasAttribute("data-tgt")
      ) {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  svgRoot.addEventListener("mousemove", (evt) => {
    if (STATE.selection?.pinned) return;
    const tgt = findInspectableTarget(evt);
    if (!tgt) {
      tip.style.display = "none";
      STATE.selection.hover = null;
      return;
    }

    const p = inspectTarget(tgt);
    STATE.selection.hover = p;
    tip.innerHTML = renderInspectionHtml(p);
    moveTooltip(tip, evt.clientX, evt.clientY);
  });

  svgRoot.addEventListener("mouseleave", () => {
    if (STATE.selection?.pinned) return;
    tip.style.display = "none";
    STATE.selection.hover = null;
  });

  svgRoot.addEventListener("click", (evt) => {
    const tgt = findInspectableTarget(evt);
    if (!tgt) return;

    const p = inspectTarget(tgt);
    STATE.selection.pinned = p;

    tip.innerHTML = renderInspectionHtml(p);
    moveTooltip(tip, evt.clientX, evt.clientY);
    tip.style.display = "block";

    updateInspectorSelectionSection();

    const q = document.getElementById("filterQuery");
    if (q) {
      const ids = p.ids || {};
      const token = ids.entity_id || ids.motif || ids.domain || ids.src || ids.tgt || "";
      if (token) {
        q.value = token;
        STATE.filters.query = token;
        const focus = document.getElementById("focusMode");
        if (focus && !focus.checked) {
          focus.checked = true;
          STATE.filters.focus = true;
        }
        applySearchAndFiltersAll();
      }
    }
  });

  window.addEventListener("keydown", (evt) => {
    if (evt.key === "Escape") {
      STATE.selection.pinned = null;
      const tip2 = document.getElementById("svgTooltip");
      if (tip2) tip2.style.display = "none";
      updateInspectorSelectionSection();
    }
  });
}

async function boot() {
  wireCompareToggle();
  wireChronoscopeControls();
  initTrendControls();
  const chronoLoaded = await tryLoadChronoFromQuery();
  if (chronoLoaded) {
    initViewStateControls(STATE.compare.A.svgRoot);
    await tryLoadViewStateFromQuery(STATE.compare.A.svgRoot);
    renderDiffPanel();
    renderSelectionCompare();
    return;
  }

  const compareLoaded = await initCompareFromQuery();
  if (compareLoaded) {
    initViewStateControls(STATE.compare.A.svgRoot);
    await tryLoadViewStateFromQuery(STATE.compare.A.svgRoot);
    renderDiffPanel();
    renderSelectionCompare();
    return;
  }

  STATE.scene = await loadJSON(`${DATA_ROOT}/scene_ir.json`);
  STATE.animation = await loadJSON(`${DATA_ROOT}/animation_plan.json`);
  const svgText = await loadSVG(`${DATA_ROOT}/render.svg`);

  document.getElementById("scene-id").textContent =
    STATE.scene.scene_id || "";

  const viewport = document.getElementById("svgContainer");
  viewport.innerHTML = svgText;
  const svgEl = viewport.querySelector("svg");
  STATE.svg = svgEl;

  buildSceneIndex();

  // annotate entities for inspection
  svgEl.querySelectorAll("circle").forEach(c => {
    const label = c.nextElementSibling;
    if (label && label.tagName === "text") {
      c.setAttribute("data-entity", label.textContent.trim());
    }
  });

  initPanZoom(svgEl);
  attachSvgInspectionHandlers(svgEl);
  initSearchAndFilterControls(svgEl);
  buildLayerControls(svgEl);
  applySearchAndFiltersAll();
  updateInspectorSelectionSection();
  initViewStateControls(svgEl);
  await tryLoadViewStateFromQuery(svgEl);
  renderDiffPanel();
  renderSelectionCompare();

  const slider = document.getElementById("time-slider");
  slider.addEventListener("input", e => {
    STATE.time = parseInt(e.target.value, 10);
    applyAnimationPlan(svgEl);
  });

  document.getElementById("toggle-pulse").onchange = e => {
    STATE.toggles.pulse = e.target.checked;
  };
  document.getElementById("toggle-decay").onchange = e => {
    STATE.toggles.decay = e.target.checked;
  };
  document.getElementById("toggle-transfer").onchange = e => {
    STATE.toggles.transfer = e.target.checked;
    svgEl.querySelectorAll("#sankey_transfer").forEach(g => {
      g.style.display = e.target.checked ? "block" : "none";
    });
  };

  applyTransform(svgEl);
}

boot();
