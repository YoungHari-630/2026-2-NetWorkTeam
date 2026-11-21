/* global cytoscape */
"use strict";

const API_BASE = "http://127.0.0.1:8000";
const SAMPLE_TOPOLOGY = {
  routers: [{ id: "A" }, { id: "B" }, { id: "C" }, { id: "D" }],
  links: [
    { id: "AB", source: "A", target: "B", cost: 1, active: true },
    { id: "AC", source: "A", target: "C", cost: 2, active: true },
    { id: "BD", source: "B", target: "D", cost: 1, active: true },
    { id: "CD", source: "C", target: "D", cost: 3, active: true },
  ],
};

const state = {
  topology: null,
  cy: null,
  selectedLinkId: null,
  route: null,
  source: "A",
  destination: "D",
  mode: "loading",
};
const $ = (id) => document.getElementById(id);

function copyTopology(topology) {
  return {
    routers: topology.routers.map((router) => ({ ...router })),
    links: topology.links.map((link) => ({ ...link })),
  };
}

async function requestJson(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  let body;
  try { body = await response.json(); } catch { body = {}; }
  if (!response.ok) {
    const error = new Error(body.detail || "API 요청에 실패했습니다 (" + response.status + ").");
    error.status = response.status;
    throw error;
  }
  return body;
}

function friendlyNetworkError(error) {
  if (error.status) return error.message;
  return "서버 연결에 실패했습니다. 백엔드 실행 여부와 CORS 설정을 확인하세요.";
}

function setConnection(mode, label, message) {
  state.mode = mode;
  $("connection-pill").dataset.state = mode;
  $("connection-label").textContent = label;
  $("api-message").textContent = message;
}

async function loadTopology() {
  try {
    state.topology = await requestJson("/api/topology");
    setConnection("connected", "백엔드 연결", "백엔드에서 현재 네트워크 상태를 불러왔습니다.");
  } catch (apiError) {
    try {
      const response = await fetch("../data/topologies/basic.json");
      if (!response.ok) throw new Error("공통 토폴로지 파일을 불러오지 못했습니다.");
      state.topology = await response.json();
      setConnection("preview", "미리보기 모드", "백엔드에 연결할 수 없어 공통 토폴로지를 표시합니다. " + friendlyNetworkError(apiError));
    } catch {
      state.topology = copyTopology(SAMPLE_TOPOLOGY);
      setConnection("preview", "미리보기 모드", "백엔드 연결 실패: " + friendlyNetworkError(apiError) + " 예시 토폴로지를 표시하고 있습니다.");
    }
  }
  render();
  $("graph-loading").hidden = true;
  await calculateRoute();
}

function positionsFor(routers) {
  const defaults = {
    A: { x: 120, y: 100 },
    B: { x: 390, y: 100 },
    C: { x: 120, y: 300 },
    D: { x: 390, y: 300 },
  };
  return Object.fromEntries(routers.map((router, index) => [
    router.id,
    defaults[router.id] || { x: 120 + (index % 2) * 270, y: 100 + Math.floor(index / 2) * 200 },
  ]));
}

function graphElements(topology) {
  const positions = positionsFor(topology.routers);
  const nodes = topology.routers.map((router) => ({
    group: "nodes",
    data: { id: router.id, label: router.id },
    position: positions[router.id],
  }));
  const edges = topology.links.map((link) => ({
    group: "edges",
    data: { id: link.id, source: link.source, target: link.target, cost: link.cost, label: String(link.cost), active: link.active },
    classes: link.active ? "" : "inactive",
  }));
  return nodes.concat(edges);
}

function createGraph() {
  if (typeof cytoscape !== "function") {
    $("graph-loading").textContent = "그래프 라이브러리를 불러오지 못했습니다. 인터넷 연결을 확인해 주세요.";
    $("graph-loading").hidden = false;
    setConnection("error", "그래프 오류", "Cytoscape.js CDN에 연결할 수 없습니다.");
    return;
  }
  state.cy = cytoscape({
    container: $("cy"),
    elements: graphElements(state.topology),
    layout: { name: "preset", fit: true, padding: 54 },
    minZoom: 0.65,
    maxZoom: 2.1,
    style: [
      { selector: "node", style: {
        label: "data(label)", width: 58, height: 58, "background-color": "#1d3a40",
        "border-width": 2, "border-color": "#65d5bc", color: "#e8f4f2",
        "font-size": 18, "font-family": "DM Mono, Consolas, monospace", "font-weight": 500,
        "text-valign": "center", "text-halign": "center", "overlay-opacity": 0,
        "shadow-blur": 20, "shadow-color": "#35bfa27a", "shadow-opacity": 0.36,
      } },
      { selector: "edge", style: {
        width: 2, "line-color": "#71868d", "curve-style": "bezier", label: "data(label)",
        color: "#d5e2e4", "font-size": 12, "font-family": "DM Mono, Consolas, monospace",
        "font-weight": 500, "text-background-color": "#17232b", "text-background-opacity": 1,
        "text-background-padding": 5, "text-border-color": "#40545d", "text-border-width": 1,
        "text-border-opacity": 1, "overlay-opacity": 0, "target-arrow-shape": "none",
      } },
      { selector: "edge.inactive", style: { "line-color": "#68747b", "line-style": "dashed", color: "#8b989e", opacity: 0.7 } },
      { selector: "edge.selected-link", style: { "line-color": "#ffbf75", width: 3, "z-index": 5, color: "#ffcf99" } },
      { selector: "edge.route", style: {
        "line-color": "#6ce0c1", width: 5, "z-index": 10, color: "#b6ffeb",
        "shadow-blur": 14, "shadow-color": "#6ce0c1", "shadow-opacity": 0.55,
      } },
      { selector: "node.route-node", style: {
        "border-color": "#9affdf", "border-width": 3, "shadow-color": "#6ce0c1",
        "shadow-opacity": 0.7, "shadow-blur": 26,
      } },
    ],
  });
  state.cy.on("tap", "edge", (event) => selectLink(event.target.id()));
}

function renderGraph() {
  if (!state.cy) { createGraph(); return; }
  state.cy.elements().remove();
  state.cy.add(graphElements(state.topology));
  state.cy.layout({ name: "preset", fit: false, padding: 54 }).run();
  state.cy.fit(undefined, 54);
  if (state.selectedLinkId && state.cy.getElementById(state.selectedLinkId).length) {
    state.cy.getElementById(state.selectedLinkId).addClass("selected-link");
  } else {
    state.selectedLinkId = null;
  }
  applyRouteHighlight();
}

function fillRouterSelects() {
  const sourceSelect = $("source-select");
  const destinationSelect = $("destination-select");
  const currentSource = sourceSelect.value || state.source;
  const currentDestination = destinationSelect.value || state.destination;
  [sourceSelect, destinationSelect].forEach((select) => {
    select.replaceChildren(...state.topology.routers.map((router) => {
      const option = document.createElement("option");
      option.value = router.id;
      option.textContent = "Router " + router.id;
      return option;
    }));
  });
  sourceSelect.value = state.topology.routers.some((router) => router.id === currentSource) ? currentSource : (state.topology.routers[0]?.id || "");
  destinationSelect.value = state.topology.routers.some((router) => router.id === currentDestination) ? currentDestination : (state.topology.routers.at(-1)?.id || "");
  state.source = sourceSelect.value;
  state.destination = destinationSelect.value;
}

function renderCounts() {
  const active = state.topology.links.filter((link) => link.active).length;
  const total = state.topology.links.length;
  $("router-count").textContent = state.topology.routers.length;
  $("active-link-count").textContent = active + " / " + total;
  $("summary-active").textContent = active;
  $("summary-failed").textContent = total - active;
}

function renderSelectedLink() {
  const link = state.topology.links.find((item) => item.id === state.selectedLinkId);
  const button = $("toggle-link-button");
  if (!link) {
    $("selected-link-name").textContent = "링크를 선택하세요";
    $("selected-link-state").textContent = "—";
    $("selected-link-state").removeAttribute("data-active");
    $("toggle-button-icon").textContent = "⊘";
    $("toggle-button-label").textContent = "링크를 먼저 선택하세요";
    button.disabled = true;
    return;
  }
  $("selected-link-name").textContent = link.source + " — " + link.target + " · 비용 " + link.cost;
  $("selected-link-state").textContent = link.active ? "활성" : "장애";
  $("selected-link-state").dataset.active = String(link.active);
  $("toggle-button-icon").textContent = link.active ? "⊘" : "↻";
  $("toggle-button-label").textContent = link.active ? "선택한 링크 장애 처리" : "선택한 링크 복구";
  button.disabled = false;
}

function render() {
  fillRouterSelects();
  renderCounts();
  renderGraph();
  renderSelectedLink();
  renderRoute();
}

function selectLink(linkId) {
  if (state.cy && state.selectedLinkId) state.cy.getElementById(state.selectedLinkId).removeClass("selected-link");
  state.selectedLinkId = linkId;
  if (state.cy) state.cy.getElementById(linkId).addClass("selected-link");
  renderSelectedLink();
  const link = state.topology.links.find((item) => item.id === linkId);
  $("control-note").textContent = link
    ? link.id + " 링크의 현재 상태를 확인했습니다. 버튼으로 장애 또는 복구를 적용하세요."
    : "링크를 선택한 뒤 장애 또는 복구를 적용할 수 있습니다.";
}

function routeEdgeIds(path) {
  if (!Array.isArray(path) || path.length < 2) return [];
  return path.slice(0, -1).map((from, index) => {
    const to = path[index + 1];
    const link = state.topology.links.find((item) =>
      (item.source === from && item.target === to) || (item.source === to && item.target === from),
    );
    return link?.id;
  }).filter(Boolean);
}

function applyRouteHighlight() {
  if (!state.cy) return;
  state.cy.edges().removeClass("route");
  state.cy.nodes().removeClass("route-node");
  if (!state.route?.reachable || !Array.isArray(state.route.path)) return;
  routeEdgeIds(state.route.path).forEach((id) => {
    const edge = state.cy.getElementById(id);
    if (edge.length && edge.data("active")) edge.addClass("route");
  });
  state.route.path.forEach((routerId) => {
    const node = state.cy.getElementById(routerId);
    if (node.length) node.addClass("route-node");
  });
}

function setResultBadge(label, mode) {
  const badge = $("result-badge");
  badge.textContent = label;
  badge.dataset.state = mode;
}

function renderRoute() {
  $("result-source").textContent = state.source || "—";
  $("result-destination").textContent = state.destination || "—";
  const route = state.route;
  if (!route) {
    $("result-cost").textContent = "—";
    $("result-path").textContent = "계산 버튼을 눌러 경로를 확인하세요.";
    setResultBadge("대기 중", "");
    $("result-note").textContent = "경로 계산 결과는 백엔드 API를 기준으로 표시합니다.";
    applyRouteHighlight();
    return;
  }
  if (!route.reachable) {
    $("result-cost").textContent = "—";
    $("result-path").textContent = "경로에 도달할 수 없습니다.";
    setResultBadge("경로 없음", "error");
    $("result-note").textContent = route.note || "활성 링크만으로 출발지에서 목적지까지 연결되지 않습니다.";
    applyRouteHighlight();
    return;
  }
  $("result-cost").textContent = route.total_cost ?? "—";
  $("result-path").replaceChildren();
  route.path.forEach((routerId, index) => {
    if (index) $("result-path").append(document.createTextNode("  →  "));
    const node = document.createElement("span");
    node.className = "path-node";
    node.textContent = routerId;
    $("result-path").append(node);
  });
  setResultBadge(route.preview ? "예시 미리보기" : "계산 완료", route.preview ? "preview" : "success");
  $("result-note").textContent = route.note || "백엔드에서 반환한 최단 경로입니다.";
  applyRouteHighlight();
}

function demoRoute() {
  const activeIds = new Set(state.topology.links.filter((link) => link.active).map((link) => link.id));
  if (state.source === "A" && state.destination === "D" && activeIds.has("AB") && activeIds.has("BD")) {
    return {
      source: "A", destination: "D", path: ["A", "B", "D"], total_cost: 2, reachable: true, preview: true,
      note: "백엔드 경로 API가 아직 준비되지 않아 기본 예시 경로를 표시합니다. 실제 계산 결과가 아닙니다.",
    };
  }
  return null;
}

async function calculateRoute() {
  state.source = $("source-select").value;
  state.destination = $("destination-select").value;
  state.route = null;
  $("calculate-button").disabled = true;
  $("result-path").textContent = "경로를 계산하고 있어요…";
  setResultBadge("계산 중", "");
  renderRoute();
  try {
    const route = await requestJson("/api/route", {
      method: "POST",
      body: JSON.stringify({ source: state.source, destination: state.destination }),
    });
    state.route = { ...route, preview: false };
    state.route.note = route.reachable ? "백엔드에서 반환한 최단 경로입니다." : "활성 링크만으로 목적지에 도달할 수 없습니다.";
  } catch (error) {
    const preview = demoRoute();
    if (preview && (error.status === 501 || !error.status)) {
      state.route = preview;
    } else {
      state.route = { reachable: false, path: [], total_cost: null, note: "경로 API 오류: " + friendlyNetworkError(error) };
      if (error.status === 501) setResultBadge("API 준비 중", "error");
    }
  } finally {
    $("calculate-button").disabled = false;
    renderRoute();
  }
}

async function toggleSelectedLink() {
  const link = state.topology.links.find((item) => item.id === state.selectedLinkId);
  if (!link) return;
  $("toggle-link-button").disabled = true;
  try {
    const updated = await requestJson("/api/links/toggle", {
      method: "POST",
      body: JSON.stringify({ link_id: link.id }),
    });
    state.topology = updated;
    setConnection("connected", "백엔드 연결", link.id + " 링크 상태를 백엔드에서 변경했습니다.");
    $("control-note").textContent = link.id + " 링크 상태가 백엔드에 반영되었습니다. 새 경로를 계산해 보세요.";
  } catch (error) {
    if (error.status) {
      setConnection("error", "API 오류", link.id + " 링크를 변경하지 못했습니다: " + friendlyNetworkError(error));
      $("toggle-link-button").disabled = false;
      return;
    }
    link.active = !link.active;
    setConnection("preview", "미리보기 모드", "서버에 연결되지 않아 링크 상태를 브라우저에서만 바꿨습니다. 백엔드에는 저장되지 않습니다.");
    $("control-note").textContent = "로컬 미리보기 변경입니다. 실제 장애 상태는 백엔드에 반영되지 않았습니다.";
  }
  state.route = null;
  render();
}

async function resetTopology() {
  $("reset-button").disabled = true;
  try {
    state.topology = await requestJson("/api/reset", { method: "POST" });
    setConnection("connected", "백엔드 연결", "기본 토폴로지로 초기화했습니다.");
  } catch (error) {
    if (error.status) {
      setConnection("error", "API 오류", "초기화에 실패했습니다: " + friendlyNetworkError(error));
      $("reset-button").disabled = false;
      return;
    }
    state.topology = copyTopology(SAMPLE_TOPOLOGY);
    setConnection("preview", "미리보기 모드", "서버에 연결되지 않아 브라우저의 예시 토폴로지로 초기화했습니다.");
  }
  state.selectedLinkId = null;
  state.route = null;
  $("reset-button").disabled = false;
  $("control-note").textContent = "기본 토폴로지로 초기화되었습니다.";
  render();
}

function bindEvents() {
  $("calculate-button").addEventListener("click", calculateRoute);
  $("toggle-link-button").addEventListener("click", toggleSelectedLink);
  $("reset-button").addEventListener("click", resetTopology);
  $("source-select").addEventListener("change", () => {
    state.source = $("source-select").value;
    state.route = null;
    renderRoute();
  });
  $("destination-select").addEventListener("change", () => {
    state.destination = $("destination-select").value;
    state.route = null;
    renderRoute();
  });
  $("fit-button").addEventListener("click", () => state.cy?.fit(undefined, 54));
}

bindEvents();
loadTopology();
