/* ProteinArena BCMA. Display reviewed data; never infer scientific eligibility. */
"use strict";
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { data: null, binders: [], antigens: [], ranking: "confidence", search: "", team: "all", evidence: "all", sort: "rank", page: 1, pageSize: 25, matrixPage: 1 };
const TEAM_NAMES = { bindcraft: "BindCraft", rfdiffusion: "RFdiffusion + MPNN", prompteina: "Prompteina" };
const finite = (value) => typeof value === "number" && Number.isFinite(value);
const text = (value, fallback = "Not available") => value === null || value === undefined || value === "" ? fallback : String(value);
const numeric = (value, digits = 2) => finite(value) ? value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "—";
const count = (value) => finite(value) ? value.toLocaleString("en-US", { maximumFractionDigits: 0 }) : "—";
const human = (value) => text(value).replaceAll("_", " ").replaceAll("-", " ");
const teamName = (team) => TEAM_NAMES[team] || human(team);
const node = (tag, className, content) => { const element = document.createElement(tag); if (className) element.className = className; if (content !== undefined) element.textContent = content; return element; };
const safeUrl = (value) => { try { const url = new URL(value, location.href); return ["https:", "http:"].includes(url.protocol) ? url.href : null; } catch { return null; } };
const hasFast = (binder) => finite(binder.model_score) || Object.values(binder.fast || {}).some(finite);
const label = (binder) => text(binder.label, text(binder.id, "Unnamed design"));
const shortId = (id) => { const value = text(id, ""); return value.length > 34 ? `${value.slice(0, 19)}…${value.slice(-10)}` : value; };
const prettyStatus = (value) => human(value).replace(/\baf2\b/gi, "AF2").replace(/\bfast\b/gi, "Fast");

function toast(message) {
  const element = $("#toast");
  element.textContent = message; element.hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { element.hidden = true; }, 3200);
}

async function loadData() {
  const notice = $("#data-status");
  try {
    const response = await fetch("data.json", { cache: "no-store" });
    if (!response.ok) throw new Error("dataset_unavailable");
    const data = await response.json();
    if (!data || typeof data !== "object" || !Array.isArray(data.binders)) throw new Error("invalid_dataset");
    state.data = data;
    try { const pairedResponse = await fetch("paired.json", {cache: "no-store"}); state.paired = pairedResponse.ok ? await pairedResponse.json() : null; } catch { state.paired = null; }
    state.binders = data.binders.filter((item) => item && typeof item === "object");
    state.antigens = Array.isArray(data.antigens) ? data.antigens.filter((item) => item && typeof item === "object") : [];
    state.page = 1; state.matrixPage = 1;
    notice.hidden = true;
    renderAll();
  } catch {
    notice.replaceChildren(node("span", "", "Reviewed campaign data are not available yet."));
    const retry = node("button", "", "Reload data"); retry.type = "button"; retry.addEventListener("click", loadData);
    notice.append(retry); notice.hidden = false;
    renderAll();
  }
}

function renderAll() {
  renderOverview(); renderFilters(); renderBinders(); renderAntigens(); renderMatrix(); renderMethods(); renderProvenance();
  $("#download-csv").disabled = !state.data;
  $("#download-json").disabled = !state.data;
}

function renderOverview() {
  const campaign = state.paired ? { ...state.data.campaign, updated: state.paired.updated_utc, stage: "Model evaluations in progress", description: "23 approved binders meet five BCMA states. Explore separate Fast and Boltz confidence evaluations, provisional escape signals, and the structures behind each score. Physics evaluation is still in progress." } : state.data?.campaign || {};
  const coverage = state.data?.coverage || {};
  document.title = `${text(campaign.title, "BCMA")} — ProteinArena`;
  if (campaign.description) $("#campaign-description").textContent = campaign.description;
  const updated = campaign.updated ? new Date(/^\d{4}-\d{2}-\d{2}$/.test(campaign.updated) ? `${campaign.updated}T12:00:00Z` : campaign.updated) : null;
  $("#updated-label").textContent = updated && !Number.isNaN(updated.getTime())
    ? `Updated ${updated.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "America/Los_Angeles" })}`
    : campaign.updated ? `Updated ${campaign.updated}` : "Reviewed dataset pending";
  const values = state.paired ? {generated: coverage.generated, fast: state.paired.cells.filter(c=>c.engine==='fast').length, physics: state.paired.cells.filter(c=>c.engine==='boltz').length, variants: state.paired.antigens.length} : {generated: coverage.generated, fast:null, physics:null, variants:null};
  for (const [key, value] of Object.entries(values)) {
    $(`#stat-${key}`).textContent = count(value);
    $(`#track-${key}`).textContent = count(value);
  }
  for (const key of ["fast", "physics"]) {
    const percent = finite(values.generated) && values.generated > 0 && finite(values[key]) ? Math.min(100, Math.max(0, 100 * values[key] / 125)) : 0;
    $(`#${key}-progress`).style.width = `${percent}%`;
  }
  $("#evidence-stage").textContent = state.data ? text(campaign.stage, "Evidence in progress") : "Awaiting reviewed data";
  const arms = $("#arm-coverage"); arms.replaceChildren();
  const teams = [...new Set(state.binders.map((item) => item.team).filter(Boolean))];
  if (!teams.length) { arms.append(node("p", "muted", "Team coverage will appear with the reviewed inventory.")); return; }
  for (const team of teams) {
    const members = state.binders.filter((binder) => binder.team === team);
    const scored = members.filter(hasFast).length;
    const item = node("div", "arm-item"); const row = node("div", "arm-row");
    row.append(node("i", "arm-indicator"), node("strong", "", teamName(team)), node("span", "", `${state.paired ? state.paired.members.filter(m=>m.team===team&&!m.control).length : "—"} approved / ${members.length} generated`));
    const bar = node("div", "arm-bar"); const fill = node("i");
    fill.style.width = `${members.length && state.paired ? state.paired.members.filter(m=>m.team===team&&!m.control).length / members.length * 100 : 0}%`;
    bar.append(fill); item.append(row, bar); arms.append(item);
  }
}

function renderFilters() {
  const select = $("#team-filter"); const selected = state.team;
  select.replaceChildren(new Option("All design arms", "all"));
  [...new Set(state.binders.map((binder) => binder.team).filter(Boolean))]
    .sort((a, b) => teamName(a).localeCompare(teamName(b)))
    .forEach((team) => select.add(new Option(teamName(team), team)));
  if ([...select.options].some((option) => option.value === selected)) select.value = selected;
  else state.team = "all";
}

function filteredBinders() {
  const query = state.search.trim().toLowerCase();
  const rows = state.binders.filter((binder) => {
    if (state.team !== "all" && binder.team !== state.team) return false;
    if (query && ![binder.id, binder.label, binder.team, teamName(binder.team), binder.parent, binder.native_status, binder.status].join(" ").toLowerCase().includes(query)) return false;
    if (state.evidence === "fast" && !hasFast(binder)) return false;
    if (state.evidence === "unscored" && hasFast(binder)) return false;
    if (state.evidence === "physics" && !finite(binder.physics_score)) return false;
    if (state.evidence === "combined" && !finite(binder.combined_score)) return false;
    return true;
  });
  const nullLast = (a, b, ascending = false) => {
    if (!finite(a) && !finite(b)) return 0;
    if (!finite(a)) return 1;
    if (!finite(b)) return -1;
    return ascending ? a - b : b - a;
  };
  rows.sort((a, b) => {
    let order = 0;
    if (state.sort === "rank") {
      const field = state.ranking === "confidence" ? "provisional_rank" : "combined_rank";
      order = nullLast(a[field], b[field], true);
    } else if (state.sort === "label") order = label(a).localeCompare(label(b), undefined, { numeric: true });
    else if (state.sort === "length") order = nullLast(a.length, b.length, true);
    else order = nullLast(a[`${state.sort}_score`], b[`${state.sort}_score`]);
    return order || label(a).localeCompare(label(b), undefined, { numeric: true }) || text(a.id).localeCompare(text(b.id));
  });
  return rows;
}

function scoreCell(value, emphasis = false) {
  const cell = node("td", "numeric");
  cell.append(node(emphasis && finite(value) ? "strong" : "span", finite(value) ? emphasis ? "cyan" : "" : "missing", numeric(value)));
  if (!finite(value)) cell.title = "Not available; not scored as zero";
  return cell;
}

function binderStatus(binder) {
  if (binder.status) return prettyStatus(binder.status);
  if (finite(binder.combined_score)) return "Combined evidence available";
  if (finite(binder.physics_score)) return "Physics available";
  if (hasFast(binder)) return "Fast scored";
  return "Not screened";
}

function renderBinders() {
  const rows = filteredBinders(); const pages = Math.ceil(rows.length / state.pageSize);
  state.page = Math.max(1, Math.min(state.page, pages || 1));
  const start = (state.page - 1) * state.pageSize;
  const visible = rows.slice(start, start + state.pageSize);
  const body = $("#binder-rows"); body.replaceChildren();
  const field = state.ranking === "confidence" ? "provisional_rank" : "combined_rank";
  const combinedAvailable = state.binders.some((binder) => finite(binder.combined_score));
  $("#ranking-note p").textContent = state.ranking === "confidence"
    ? "Provisional confidence = 100 × (native ipTM + maximum-direction ipSAE) / 2. This custom summary does not establish binding or final nomination."
    : combinedAvailable
      ? "Combined ranks use the recorded confidence and physics method. Designs without the required evidence remain unranked."
      : "Combined rankings are not available yet. Physics evidence is missing; confidence remains visible and no missing value is treated as zero.";
  $("#binder-total").textContent = state.data ? `${count(state.binders.length)} retained designs` : "Inventory pending";
  for (const binder of visible) {
    const row = node("tr"); row.dataset.binderId = text(binder.id, "");
    const rank = node("td", finite(binder[field]) ? "rank has-rank" : "rank", finite(binder[field]) ? count(binder[field]) : "—");
    if (!finite(binder[field])) rank.title = "Unranked with the currently available evidence";
    const design = node("td");
    const button = node("button", "design-button", label(binder)); button.type = "button"; button.title = label(binder); button.addEventListener("click", () => showBinder(binder));
    design.append(button, node("span", "design-id", shortId(binder.id)));
    const team = node("td");
    team.append(node("span", "team-name", teamName(binder.team)), node("div", "family", text(binder.parent, "Parent not recorded")));
    const length = node("td", "numeric", finite(binder.length) ? `${count(binder.length)} aa` : "—");
    const status = node("td");
    status.append(node("span", `status-badge ${hasFast(binder) ? "scored" : "unavailable"}`, binderStatus(binder)));
    const action = node("td");
    const open = node("button", "row-open", "↗"); open.type = "button"; open.setAttribute("aria-label", `View evidence for ${label(binder)}`); open.addEventListener("click", () => showBinder(binder));
    action.append(open);
    row.append(rank, design, team, length, scoreCell(binder.model_score, state.ranking === "confidence"), scoreCell(binder.physics_score), scoreCell(binder.combined_score, state.ranking === "combined"), status, action);
    body.append(row);
  }
  const empty = $("#binder-empty"); empty.hidden = rows.length > 0;
  if (state.data && !rows.length) {
    empty.querySelector("h3").textContent = state.binders.length ? "No designs match these filters." : "No binder records are available.";
    empty.querySelector("p").textContent = state.binders.length ? "Try another search or return the filters to all evidence states." : "The reviewed inventory has no binder rows yet.";
  }
  $("#page-info").textContent = rows.length ? `${start + 1}–${Math.min(start + state.pageSize, rows.length)} of ${count(rows.length)} designs${rows.length !== state.binders.length ? ` · ${count(state.binders.length)} total` : ""}` : "No rows to display";
  $("#page-label").textContent = `${pages ? state.page : 0} / ${pages}`;
  $("#page-prev").disabled = state.page <= 1; $("#page-next").disabled = state.page >= pages;
}

function setRanking(ranking) {
  state.ranking = ranking; state.sort = "rank"; state.page = 1; $("#sort-select").value = "rank";
  $$("[data-ranking]").forEach((tab) => { const active = tab.dataset.ranking === ranking; tab.setAttribute("aria-selected", String(active)); tab.tabIndex = active ? 0 : -1; });
  $("#binder-panel").setAttribute("aria-labelledby", `${ranking}-tab`);
  renderBinders();
}

function showBinder(binder) {
  const content = $("#detail-content"); content.replaceChildren();
  const title = node("h2", "detail-title", label(binder)); title.id = "detail-title";
  content.append(title, node("p", "detail-id", text(binder.id)), node("span", "status-badge", binderStatus(binder)));
  const metadata = node("dl", "detail-meta");
  for (const [key, value] of [["Design arm", teamName(binder.team)], ["Length", finite(binder.length) ? `${binder.length} amino acids` : "Not recorded"], ["Parent family", text(binder.parent)], ["Native status", prettyStatus(binder.native_status)], ["Provisional rank", finite(binder.provisional_rank) ? `#${count(binder.provisional_rank)}` : "Unranked"], ["Combined rank", finite(binder.combined_rank) ? `#${count(binder.combined_rank)}` : "Unranked"]]) {
    const entry = node("div"); entry.append(node("dt", "", key), node("dd", "", value)); metadata.append(entry);
  }
  content.append(metadata);
  const scores = node("div", "detail-score-grid");
  for (const [name, value] of [["Confidence / 100", binder.model_score], ["Physics / 100", binder.physics_score], ["Combined / 100", binder.combined_score]]) {
    const entry = node("div"); entry.append(node("span", "", name), node("strong", "", numeric(value))); scores.append(entry);
  }
  content.append(scores);
  const section = node("section", "detail-section"); section.append(node("h3", "", "Fast confidence breakdown"));
  for (const [name, key] of [["Native ipTM", "iptm"], ["Native pTM", "ptm"], ["Minimum-direction ipSAE", "ipsae_min"], ["Maximum-direction ipSAE", "ipsae_max"]]) {
    const row = node("div", "detail-row"); row.append(node("span", "", name), node("strong", "", numeric(binder.fast?.[key], 3))); section.append(row);
  }
  content.append(section);
  if ("interface_dg_reu" in binder) {
    const physics = node("section", "detail-section"); physics.append(node("h3", "", "Interface physics"));
    const row = node("div", "detail-row"); row.append(node("span", "", "Interface ΔG (REU)"), node("strong", "", numeric(binder.interface_dg_reu)));
    physics.append(row); content.append(physics);
  }
  if (binder.physics && typeof binder.physics === "object") {
    const physics = node("section", "detail-section"); physics.append(node("h3", "", "Recorded physics components"));
    for (const [key, value] of Object.entries(binder.physics)) {
      if (value !== null && typeof value === "object") continue;
      const row = node("div", "detail-row"); row.append(node("span", "", human(key)), node("strong", "", finite(value) ? numeric(value) : text(value, "—"))); physics.append(row);
    }
    content.append(physics);
  }
  content.append(node("p", "detail-note", "Native acceptance, screening completion, and final nomination are distinct decisions. Provisional confidence combines native ipTM and maximum-direction ipSAE; it is not a binding probability. A dash means evidence is unavailable, not that the value is zero."));
  const dialog = $("#binder-dialog");
  if (!dialog.open) dialog.showModal();
  $("#close-detail").focus();
}

function renderAntigens() {
  const cards = $("#antigen-cards"); const rows = $("#antigen-rows"); cards.replaceChildren(); rows.replaceChildren();
  $("#antigen-empty").hidden = state.antigens.length > 0;
  const competitive = state.antigens.filter((antigen) => !isReference(antigen));
  const scored = competitive.filter((antigen) => finite(antigen.escape_score)).length;
  $("#red-coverage-label").textContent = scored ? `${scored} challenges with recorded escape scores` : "Escape evidence not established";
  $("#antigen-count").textContent = state.antigens.length ? `${state.antigens.length} antigen states` : "No evaluated panel";
  const ordered = [...state.antigens].sort((a, b) => {
    const referenceOrder = Number(isReference(a)) - Number(isReference(b));
    if (referenceOrder) return referenceOrder;
    const ar = finite(a.escape_rank) ? a.escape_rank : Infinity;
    const br = finite(b.escape_rank) ? b.escape_rank : Infinity;
    return ar === br ? 0 : ar - br;
  });
  for (const antigen of ordered) {
    const reference = isReference(antigen);
    const card = node("article", `antigen-card ${reference ? "wt" : ""}`);
    const top = node("div", "card-label"); top.append(node("span", "", text(antigen.label, text(antigen.id))), node("span", "card-role", reference ? referenceRole(antigen) : "Challenge"));
    card.append(top, node("h3", "", numeric(antigen.escape_score)), node("p", "", reference ? `${referenceRole(antigen)} · not a competitive escape rank` : "Recorded escape score"));
    const bottom = node("div", "card-footer");
    bottom.append(node("span", "", finite(antigen.evaluable_count) ? `${count(antigen.evaluable_count)} evaluable pairs` : "Matched pairs unavailable"), node("span", "", prettyStatus(antigen.status)));
    card.append(bottom); cards.append(card);
    const row = node("tr"); const name = node("td"); name.append(node("strong", "", text(antigen.label, text(antigen.id))));
    const mutation = node("td"); mutation.append(node("span", "", text(antigen.mutation, referenceRole(antigen))), node("div", "family", human(antigen.role)));
    const supported = node("td", "numeric", count(antigen.escape_count));
    const pairs = node("td", "numeric", finite(antigen.evaluable_count) ? `${count(antigen.evaluable_count)}${finite(antigen.panel_size) ? ` / ${count(antigen.panel_size)}` : ""}` : "—");
    const status = node("td"); status.append(node("span", "status-badge", prettyStatus(antigen.status)));
    const rank = node("td", "rank", !reference && finite(antigen.escape_rank) ? count(antigen.escape_rank) : "—");
    rank.title = reference ? "Reference states are not competitively ranked" : "Rank requires complete matched evidence";
    row.append(rank, name, mutation, scoreCell(antigen.escape_score), supported, pairs, status); rows.append(row);
  }
}

function isReference(antigen) {
  const role = text(antigen.role, "").toLowerCase();
  return /control|reference|baseline/.test(role) || [antigen.id, antigen.label].some((value) => String(value).toUpperCase() === "WT");
}
function referenceRole(antigen) {
  return [antigen.id, antigen.label].some((value) => String(value).toUpperCase() === "WT") || /baseline/.test(text(antigen.role, "")) ? "WT baseline" : /control|reference/.test(text(antigen.role, "")) ? "Variant control" : "Challenge";
}

function matrixRows() {
  const declared = state.data?.wt_matrix;
  if (declared && Array.isArray(declared.rows)) return declared.rows;
  return state.binders.map((binder) => ({ binder_id: binder.id, label: label(binder), cells: {} }));
}
function renderMatrix() {
  const declared = state.data?.wt_matrix;
  const columns = Array.isArray(declared?.columns) ? declared.columns : state.antigens.map((antigen) => ({ id: antigen.id, label: antigen.label }));
  const rows = matrixRows(); const pages = Math.ceil(rows.length / 10);
  state.matrixPage = Math.max(1, Math.min(state.matrixPage, pages || 1));
  const head = $("#matrix-head"), body = $("#matrix-body"); head.replaceChildren(); body.replaceChildren();
  $("#matrix-empty").hidden = rows.length > 0 && columns.length > 0;
  const heading = node("tr"); const first = node("th", "", "Binder design"); first.scope = "col"; heading.append(first);
  columns.forEach((column) => { const cell = node("th", "", text(column.label, text(column.id))); cell.scope = "col"; heading.append(cell); });
  if (columns.length) head.append(heading);
  if (columns.length) for (const row of rows.slice((state.matrixPage - 1) * 10, state.matrixPage * 10)) {
    const tr = node("tr"); const first = node("th", "matrix-binder", text(row.label, shortId(row.binder_id))); first.scope = "row"; first.title = text(row.binder_id, ""); tr.append(first);
    for (const column of columns) {
      const entry = row.cells?.[column.id]; const td = node("td");
      const available = entry && typeof entry === "object" && !["missing", "not_evaluated", "pending", "unavailable"].includes(entry.status);
      const recorded = available && (finite(entry.escape_score) || finite(entry.variant_score) || finite(entry.score) || ["evaluated", "recorded", "complete", "reference"].includes(entry.status));
      const escape = recorded && entry.escape === true;
      const type = !recorded ? "missing" : escape ? "escape" : entry.status === "reference" ? "reference" : "recorded";
      const value = !recorded ? "Not evaluated" : finite(entry.escape_score) ? numeric(entry.escape_score) : finite(entry.variant_score) ? numeric(entry.variant_score) : finite(entry.score) ? numeric(entry.score) : escape ? "Modeled escape" : human(entry.status);
      const cell = node("span", `matrix-cell ${type}`, value);
      cell.setAttribute("aria-label", `${text(row.label, shortId(row.binder_id))}, ${text(column.label, text(column.id))}: ${value}`);
      if (recorded) cell.title = `Status: ${human(entry.status)}${finite(entry.wt_score) ? `; WT score: ${numeric(entry.wt_score)}` : ""}${finite(entry.variant_score) ? `; variant score: ${numeric(entry.variant_score)}` : ""}${escape ? "; modeled escape" : ""}`;
      td.append(cell); tr.append(td);
    }
    body.append(tr);
  }
  const start = (state.matrixPage - 1) * 10;
  $("#matrix-page-info").textContent = rows.length && columns.length ? `${start + 1}–${Math.min(start + 10, rows.length)} of ${count(rows.length)} binders · missing cells are not zero` : "No matched matrix available";
  $("#matrix-page-label").textContent = `${pages && columns.length ? state.matrixPage : 0} / ${columns.length ? pages : 0}`;
  $("#matrix-prev").disabled = state.matrixPage <= 1 || !columns.length;
  $("#matrix-next").disabled = state.matrixPage >= pages || !columns.length;
  if (declared?.description) $("#matrix-description").textContent = declared.description;
}

const defaultMethods = [
  { title: "Confidence is provisional", formula: "C = 100 × (native ipTM + maximum-direction ipSAE) / 2", description: "This custom campaign summary uses the higher of the two directional ipSAE values. Native Fast ipTM and pTM remain separately visible. Confidence does not establish binding or final nomination." },
  { title: "Physics stays separate", formula: "P = 100 × (WT reference energies worse + 0.5 × equal) / N", description: "The final evaluation protocol uses one pinned Boltz prediction and one Rosetta beta_nov16 evaluation per pair. Physics uses the same frozen WT reference for every variant. A physics score appears only after the required reviewed output exists." },
  { title: "Combined evidence needs both parts", formula: "B = (C + P) / 2", description: "Combined ranks are shown only when both required components are available. Provisional confidence remains a separate view. Missing values are never replaced by zero; the campaign supplies the reviewed scores and tied ranks." },
  { title: "Modeled escape needs matched evidence", description: "The custom, uncalibrated escape rule requires complete WT-supported, intact-variant comparisons for the same frozen binder panel. A modeled escape is not experimental evidence. WT and P33S have distinct reference roles; panel membership or missing comparisons do not establish escape." }
];

function methodEntries(methods) {
  if (Array.isArray(methods)) return methods.map((item, index) => typeof item === "string" ? { title: `Method ${index + 1}`, description: item } : item).filter(Boolean);
  if (!methods || typeof methods !== "object" || !Object.keys(methods).length) return defaultMethods;
  if (Array.isArray(methods.sections)) return methods.sections;
  if (methods.confidence_formula) return [
    { title: "Provisional confidence", formula: methods.confidence_formula, description: methods.current_rank, notes: [methods.maximum_ipsae, methods.af2_diagnostics].filter(Boolean) },
    { title: "A frozen physics reference", formula: methods.physics_formula, description: methods.physics_reference, notes: [methods.final_rank].filter(Boolean) },
    { title: "The combined Blue score", formula: methods.combined_formula, description: methods.missing_and_ties, notes: [methods.uncalibrated_policy].filter(Boolean) },
    { title: "Modeled escapes", formula: methods.red_formula, description: methods.escape_rule, notes: [methods.escape_eligibility, methods.escape_controls].filter(Boolean) },
    { title: "Interpretation & limits", description: methods.limitations, notes: [methods.reproducibility].filter(Boolean) }
  ];
  return Object.entries(methods).filter(([key]) => !["notes", "version", "score_scale"].includes(key)).map(([key, value]) => {
    if (typeof value === "string") return { title: human(key), description: value };
    if (value && typeof value === "object" && !Array.isArray(value)) return { ...value, title: value.title || human(key) };
    if (Array.isArray(value)) return { title: human(key), notes: value };
    return { title: human(key), description: text(value) };
  });
}

function renderMethods() {
  const cards = $("#method-cards"); cards.replaceChildren();
  const entries = methodEntries(state.data?.methods);
  entries.forEach((method, index) => {
    const card = node("article", "method-card");
    card.append(node("span", "method-number", String(index + 1).padStart(2, "0")), node("h3", "", text(method.title, `Method ${index + 1}`)));
    if (method.formula || method.equation) card.append(node("code", "method-formula", text(method.formula || method.equation)));
    const description = method.description || method.explanation || method.definition || method.text;
    if (description) card.append(node("p", "", typeof description === "string" ? description : JSON.stringify(description)));
    const notes = Array.isArray(method.notes) ? method.notes : Array.isArray(method.requirements) ? method.requirements : null;
    if (notes?.length) { const list = node("ul", "method-notes"); notes.forEach((note) => list.append(node("li", "", typeof note === "string" ? note : JSON.stringify(note)))); card.append(list); }
    if (!description && !method.formula && !method.equation && !notes) {
      const values = Object.entries(method).filter(([key]) => key !== "title").map(([key, value]) => `${human(key)}: ${typeof value === "object" ? JSON.stringify(value) : value}`);
      card.append(node("p", "", values.join(" · ")));
    }
    cards.append(card);
  });
  if (Array.isArray(state.data?.methods?.notes)) {
    const note = node("article", "method-card"); note.append(node("span", "method-number", "NOTES"), node("h3", "", "Interpretation and limitations"));
    const list = node("ul", "method-notes"); state.data.methods.notes.forEach((item) => list.append(node("li", "", text(item)))); note.append(list); cards.append(note);
  }
}

function renderProvenance() {
  const container = $("#provenance-list"); container.replaceChildren();
  $("#dataset-id").textContent = text(state.data?.campaign?.id, "Dataset pending");
  const provenance = state.data?.provenance;
  const entries = Array.isArray(provenance) ? provenance : provenance && typeof provenance === "object" ? Object.entries(provenance).map(([key, value]) => ({ label: human(key), value })) : [];
  const sources = Array.isArray(state.data?.sources) ? state.data.sources : [];
  if (sources.length) {
    const sourcesBlock = node("div", "source-citations"); sourcesBlock.append(node("strong", "", "Method sources"));
    for (const item of sources) {
      if (!item?.url || !safeUrl(item.url)) continue;
      const link = node("a", "", `${text(item.title, "Source")} ↗`); link.href = safeUrl(item.url); link.target = "_blank"; link.rel = "noopener noreferrer"; sourcesBlock.append(link);
    }
    container.append(sourcesBlock);
  }
  if (!entries.length) { container.append(node("p", "muted", "Reviewed source metadata will appear here.")); return; }
  let expanded = null;
  if (entries.length > 6) {
    expanded = node("details", "provenance-disclosure");
    expanded.append(node("summary", "", `View all ${count(entries.length)} source records`));
  }
  for (const [index, item] of entries.entries()) {
    const row = node("div", "provenance-item");
    if (typeof item === "string") { row.append(node("strong", "", `Source ${index + 1}`), node("span", "", item)); container.append(row); continue; }
    row.append(node("strong", "", text(item.label || item.title || item.name || item.source_id || item.type, `Source ${index + 1}`)));
    const value = node("span");
    if (item.sha256 || item.hash) value.append(node("code", "", text(item.sha256 || item.hash)));
    else if (item.value !== undefined) value.textContent = typeof item.value === "object" ? JSON.stringify(item.value) : text(item.value);
    else value.textContent = text(item.description || item.status || item.job_id || item.id || item.date, "Recorded source");
    if (item.url && safeUrl(item.url)) { const link = node("a", "", " View source ↗"); link.href = safeUrl(item.url); link.target = "_blank"; link.rel = "noopener noreferrer"; value.append(link); }
    row.append(value);
    if (index < 6 || !expanded) container.append(row); else expanded.append(row);
  }
  if (expanded) container.append(expanded);
}

function selectFields(object, fields) {
  const out = {};
  for (const field of fields) if (Object.prototype.hasOwnProperty.call(object, field)) out[field] = object[field];
  return out;
}
function publicExport() {
  // data.json is the reviewed, allowlist-sanitized public snapshot. Preserve its
  // complete methods, raw scalar evidence, build identity and provenance.
  return state.data;
}
function download(content, type, filename) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a"); link.href = url; link.download = filename; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast(`${filename} prepared.`);
}
function downloadCSV() {
  const columns = ["id", "label", "team", "parent", "length", "native_status", "iptm", "ptm", "ipsae_min", "ipsae_max", "model_score", "physics_score", "combined_score", "provisional_rank", "combined_rank", "status"];
  const csvValue = (value) => {
    let string = value === null || value === undefined ? "" : String(value);
    if (typeof value === "string" && /^[=+\-@\t\r]/.test(string)) string = `'${string}`;
    return `"${string.replaceAll('"', '""')}"`;
  };
  const records = filteredBinders().map((binder) => columns.map((key) => csvValue(key in (binder.fast || {}) ? binder.fast[key] : binder[key])).join(","));
  download([columns.join(","), ...records].join("\r\n") + "\r\n", "text/csv;charset=utf-8", "bcma-binders-filtered.csv");
}

$("#binder-search").addEventListener("input", (event) => { state.search = event.target.value; state.page = 1; renderBinders(); });
$("#team-filter").addEventListener("change", (event) => { state.team = event.target.value; state.page = 1; renderBinders(); });
$("#evidence-filter").addEventListener("change", (event) => { state.evidence = event.target.value; state.page = 1; renderBinders(); });
$("#sort-select").addEventListener("change", (event) => { state.sort = event.target.value; state.page = 1; renderBinders(); });
$("#page-size").addEventListener("change", (event) => { state.pageSize = Number(event.target.value); state.page = 1; renderBinders(); });
$("#page-prev").addEventListener("click", () => { state.page--; renderBinders(); });
$("#page-next").addEventListener("click", () => { state.page++; renderBinders(); });
$("#matrix-prev").addEventListener("click", () => { state.matrixPage--; renderMatrix(); });
$("#matrix-next").addEventListener("click", () => { state.matrixPage++; renderMatrix(); });
$$("[data-sort]").forEach((button) => button.addEventListener("click", () => { state.sort = button.dataset.sort; state.page = 1; $("#sort-select").value = state.sort; renderBinders(); }));
$$("[data-ranking]").forEach((tab) => {
  tab.addEventListener("click", () => setRanking(tab.dataset.ranking));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const ranking = event.key === "Home" ? "confidence" : event.key === "End" ? "combined" : state.ranking === "confidence" ? "combined" : "confidence";
    setRanking(ranking); $(`#${ranking}-tab`).focus();
  });
});
$("#close-detail").addEventListener("click", () => $("#binder-dialog").close());
$("#binder-dialog").addEventListener("click", (event) => {
  const bounds = event.currentTarget.getBoundingClientRect();
  if (event.target === event.currentTarget && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) event.currentTarget.close();
});
$("#download-csv").addEventListener("click", downloadCSV);
$("#download-json").addEventListener("click", () => download(JSON.stringify(publicExport(), null, 2) + "\n", "application/json", "bcma-campaign-reviewed.json"));
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    const entry = entries.filter((item) => item.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
    if (!entry) return;
    $$(".main-nav a").forEach((link) => { if (link.hash === `#${entry.target.id}`) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current"); });
  }, { rootMargin: "-15% 0px -60% 0px", threshold: 0 });
  ["overview", "arena", "blue", "red", "methods"].forEach((id) => observer.observe(document.getElementById(id)));
}
loadData();
