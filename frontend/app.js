/* global cytoscape */
"use strict";

const I18N = {
  ko: {
    title: "라우팅 경로 시뮬레이터", brand: "라우팅 경로 시뮬레이터",
    eyebrow: "OSPF 네트워크 실습", heading: "최단 경로를 확인해 보세요",
    description: "출발지와 도착지를 고르고 경로를 계산하세요. 선을 선택하면 링크 장애와 복구도 시험할 수 있습니다.",
    topology: "기본 네트워크", routerCountChip: "라우터 4개", graphTitle: "네트워크 연결",
    graphHelp: "숫자는 각 링크의 비용입니다. 비용이 낮을수록 우선 경로가 됩니다.",
    fit: "맞춤", graphAria: "라우터와 링크를 표시한 네트워크 그래프",
    loadingGraph: "네트워크를 불러오는 중입니다.", legendAria: "그래프 범례",
    legendConnected: "연결됨", legendFailed: "장애", legendRoute: "계산된 경로",
    routerMetric: "라우터", linksMetric: "사용 가능한 링크", selectLinkHint: "링크 선을 눌러 선택하세요.",
    routeTitle: "경로 계산", routeHelp: "경로는 서버에서 계산합니다.",
    sourceLabel: "출발지", destinationLabel: "도착지", calculateButton: "최단 경로 계산",
    resultTitle: "계산 결과", costLabel: "총 비용", pathLabel: "최단 경로",
    initialPath: "계산 버튼을 누르면 경로가 여기에 표시됩니다.",
    initialResultNote: "예시 경로와 서버 계산 결과를 구분해 표시합니다.",
    linkControlTitle: "링크 장애 및 복구", linkControlHelp: "그래프에서 선을 선택한 다음 상태를 바꾸세요.",
    resetButton: "처음 상태로", selectedLinkLabel: "선택한 링크", noLinkSelected: "선택된 링크 없음",
    noLinkButton: "링크를 선택하세요", controlHint: "장애가 난 링크는 회색 점선으로 표시됩니다.",
    tableTitle: "라우팅 표", tableHelp: "라우터별 다음 경로와 비용을 표시할 영역입니다.",
    comingSoon: "추가 예정", tableIcon: "표", tablePlaceholder: "라우팅 표는 다음 단계에서 연결합니다.",
    statusTitle: "네트워크 상태", activeLinks: "활성 링크", failedLinks: "장애 링크",
    footerTitle: "OSPF 기반 라우팅 재수렴 시뮬레이터", footerSubtitle: "실습용 가상 네트워크",
    loadingStatus: "서버 확인 중", loadingMessage: "네트워크 상태를 불러오는 중입니다.",
    connectedStatus: "서버 연결됨", topologyLoaded: "서버에서 네트워크 상태를 불러왔습니다.",
    previewStatus: "예시 모드", topologyFromJson: "서버에 연결할 수 없어 공통 예시 네트워크를 표시합니다. {detail}",
    topologySample: "서버와 예시 파일을 불러오지 못해 기본 네트워크를 표시합니다. {detail}",
    screenErrorStatus: "화면 오류", screenError: "화면을 표시하지 못했습니다. 그래프 파일과 연결 상태를 확인하세요. {detail}",
    graphErrorStatus: "그래프 오류", graphLibraryError: "그래프 라이브러리를 불러오지 못했습니다. 인터넷 연결을 확인하세요.",
    routerOption: "라우터 {id}", active: "활성", failed: "장애",
    selectedLinkValue: "{source} — {target} · 비용 {cost}",
    failSelectedLink: "선택한 링크 장애 처리", restoreSelectedLink: "선택한 링크 복구",
    selectedLinkInstruction: "{link} 링크를 선택했습니다. 아래 버튼으로 상태를 바꿀 수 있습니다.",
    noLinkInstruction: "링크를 선택한 뒤 장애 또는 복구를 적용할 수 있습니다.",
    idle: "대기 중", waitingPath: "계산 버튼을 누르면 경로가 여기에 표시됩니다.",
    noRoute: "경로에 도달할 수 없습니다.", noRouteNote: "활성 링크만으로 출발지에서 도착지까지 연결되지 않습니다.",
    apiErrorBadge: "요청 오류", routeCalculationError: "경로 계산에 실패했습니다. {detail}",
    previewBadge: "예시 경로", routeCalculatedBadge: "계산 완료",
    backendRouteNote: "서버에서 계산한 경로입니다.",
    previewRouteNote: "예시 경로입니다. 실제 서버 계산 결과와 다를 수 있습니다.",
    calculating: "계산 중", routeApiBadge: "API 준비 중",
    routeApiUnavailable: "경로 계산 API가 아직 준비되지 않았습니다.",
    networkError: "서버 연결에 실패했습니다. 서버 실행 여부와 CORS 설정을 확인하세요.",
    httpStatusError: "서버 요청 오류 ({status})",
    linkUpdatedStatus: "링크 변경 완료", linkUpdatedMessage: "{link} 링크 상태를 서버에 반영했습니다.",
    linkUpdatedNote: "{link} 링크 상태가 서버에 반영되었습니다. 새 경로를 계산해 보세요.",
    localPreviewStatus: "예시 모드", localLinkMessage: "서버에 연결되지 않아 이 브라우저에서만 변경했습니다. 서버에는 저장되지 않았습니다.",
    localLinkNote: "예시 변경입니다. 실제 장애 상태는 서버에 반영되지 않았습니다.",
    linkUpdateError: "{link} 링크 상태를 바꾸지 못했습니다. {detail}",
    resetSuccess: "초기화 완료", resetSuccessMessage: "기본 네트워크로 초기화했습니다.",
    resetError: "초기화에 실패했습니다. {detail}",
    localResetMessage: "서버에 연결되지 않아 브라우저의 예시 네트워크로 초기화했습니다.",
    resetDone: "기본 네트워크로 초기화했습니다."
  },
  en: {
    title: "Routing Path Simulator", brand: "Routing Path Simulator",
    eyebrow: "OSPF NETWORK LAB", heading: "Find the shortest path",
    description: "Choose a source and destination, then calculate the route. Select a link to try a failure or recovery.",
    topology: "Sample network", routerCountChip: "4 routers", graphTitle: "Network connections",
    graphHelp: "Numbers show link costs. Lower cost links are preferred.",
    fit: "Fit view", graphAria: "Network graph showing routers and links",
    loadingGraph: "Loading network…", legendAria: "Graph legend",
    legendConnected: "Active", legendFailed: "Failed", legendRoute: "Calculated route",
    routerMetric: "Routers", linksMetric: "Active links", selectLinkHint: "Select a link on the graph.",
    routeTitle: "Calculate a route", routeHelp: "The server calculates the route.",
    sourceLabel: "Source", destinationLabel: "Destination", calculateButton: "Calculate shortest path",
    resultTitle: "Result", costLabel: "Total cost", pathLabel: "Shortest path",
    initialPath: "Press the button to see the route here.",
    initialResultNote: "Example paths are labelled separately from server results.",
    linkControlTitle: "Link failure and recovery", linkControlHelp: "Select a line on the graph, then change its state.",
    resetButton: "Reset", selectedLinkLabel: "Selected link", noLinkSelected: "No link selected",
    noLinkButton: "Select a link first", controlHint: "Failed links appear as gray dashed lines.",
    tableTitle: "Routing table", tableHelp: "Next hop and cost for each router will appear here.",
    comingSoon: "Coming soon", tableIcon: "Table", tablePlaceholder: "The routing table will be added in a later step.",
    statusTitle: "Network status", activeLinks: "Active links", failedLinks: "Failed links",
    footerTitle: "OSPF Route Reconvergence Simulator", footerSubtitle: "Virtual network for learning",
    loadingStatus: "Checking server", loadingMessage: "Loading network status…",
    connectedStatus: "Server connected", topologyLoaded: "Network status loaded from the server.",
    previewStatus: "Example mode", topologyFromJson: "Could not connect to the server. Showing the shared sample network. {detail}",
    topologySample: "Could not load the server or sample file. Showing the built-in sample network. {detail}",
    screenErrorStatus: "Display error", screenError: "Could not display the graph. Check the graph file and connection. {detail}",
    graphErrorStatus: "Graph error", graphLibraryError: "Could not load the graph library. Check your internet connection.",
    routerOption: "Router {id}", active: "Active", failed: "Failed",
    selectedLinkValue: "{source} — {target} · Cost {cost}",
    failSelectedLink: "Fail selected link", restoreSelectedLink: "Restore selected link",
    selectedLinkInstruction: "Selected link {link}. Use the button below to change its state.",
    noLinkInstruction: "Select a link, then choose failure or recovery.",
    idle: "Ready", waitingPath: "Press the button to see the route here.",
    noRoute: "Destination is unreachable.", noRouteNote: "No active links connect the source to the destination.",
    apiErrorBadge: "Request error", routeCalculationError: "Could not calculate the route. {detail}",
    previewBadge: "Example route", routeCalculatedBadge: "Calculated",
    backendRouteNote: "Route calculated by the server.",
    previewRouteNote: "This is an example route and may differ from the server result.",
    calculating: "Calculating", routeApiBadge: "API unavailable",
    routeApiUnavailable: "The route calculation API is not available yet.",
    networkError: "Could not connect to the server. Check that it is running and CORS is configured.",
    httpStatusError: "Server request failed ({status})",
    linkUpdatedStatus: "Link updated", linkUpdatedMessage: "Link {link} was updated on the server.",
    linkUpdatedNote: "Link {link} was updated on the server. Calculate the route again.",
    localPreviewStatus: "Example mode", localLinkMessage: "Server unavailable. This change is only shown in this browser and is not saved.",
    localLinkNote: "This is a local preview. The server's network state did not change.",
    linkUpdateError: "Could not update link {link}. {detail}",
    resetSuccess: "Reset complete", resetSuccessMessage: "The sample network has been restored.",
    resetError: "Could not reset the network. {detail}",
    localResetMessage: "Server unavailable. Restored the sample network in this browser.",
    resetDone: "The sample network has been restored."
  }
};

function readSavedLanguage() {
  try { return window.localStorage.getItem("route-lab-language") === "en" ? "en" : "ko"; }
  catch { return "ko"; }
}

const state = {
  language: readSavedLanguage(),
  topology: null,
  cy: null,
  selectedLinkId: null,
  route: null,
  source: "A",
  destination: "D",
  mode: "loading",
  connection: { mode: "loading", labelKey: "loadingStatus", messageKey: "loadingMessage", params: {} },
  controlNote: { key: "controlHint", params: {} },
};
const $ = (id) => document.getElementById(id);

function t(key, params = {}) {
  let value = (I18N[state.language] || I18N.ko)[key] || key;
  Object.entries(params).forEach(([name, replacement]) => {
    value = value.replaceAll("{" + name + "}", String(replacement));
  });
  return value;
}

function applyLanguage() {
  document.documentElement.lang = state.language;
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAria));
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.setAttribute("title", t(element.dataset.i18nTitle));
  });
  const button = $("language-toggle");
  button.textContent = state.language === "ko" ? "English" : "한국어";
  button.setAttribute("aria-label", state.language === "ko" ? "Switch to English" : "Switch to Korean");
  renderConnection();
  renderControlNote();
  if (state.topology) {
    fillRouterSelects();
    renderSelectedLink();
    renderRoute();
  }
}

function setLanguage(language) {
  state.language = language === "en" ? "en" : "ko";
  try { window.localStorage.setItem("route-lab-language", state.language); } catch {}
  applyLanguage();
}

const SAMPLE_TOPOLOGY = {
  routers: [{ id: "A" }, { id: "B" }, { id: "C" }, { id: "D" }],
  links: [
    { id: "AB", source: "A", target: "B", cost: 1, active: true },
    { id: "AC", source: "A", target: "C", cost: 2, active: true },
    { id: "BD", source: "B", target: "D", cost: 1, active: true },
    { id: "CD", source: "C", target: "D", cost: 3, active: true },
  ],
};

function copyTopology(topology) {
  return {
    routers: topology.routers.map((router) => ({ ...router })),
    links: topology.links.map((link) => ({ ...link })),
  };
}

async function requestJson(path, options = {}) {
  return NetworkApi.request(path, options, () => t("networkError"));
}

function friendlyNetworkError(error) {
  if (error.status === 501) return t("routeApiUnavailable");
  if (error.status) return t("httpStatusError", { status: error.status });
  return t("networkError");
}

function setConnection(mode, labelKey, messageKey, params = {}) {
  state.mode = mode;
  state.connection = { mode, labelKey, messageKey, params };
  renderConnection();
  renderControlNote();
}

function renderConnection() {
  if (!state.connection) return;
  $("connection-pill").dataset.state = state.connection.mode;
  $("connection-label").textContent = t(state.connection.labelKey);
  $("api-message").textContent = t(state.connection.messageKey, state.connection.params);
}

function setControlNote(key, params = {}) {
  state.controlNote = { key, params };
  renderControlNote();
}

function renderControlNote() {
  if (!state.controlNote) return;
  $("control-note").textContent = t(state.controlNote.key, state.controlNote.params);
}
async function loadTopology() {
  try {
    state.topology = await requestJson("/api/topology");
    setConnection("connected", "connectedStatus", "topologyLoaded");
  } catch (apiError) {
    try {
      const response = await fetch("../data/topologies/basic.json");
      if (!response.ok) throw new Error("sample file unavailable");
      state.topology = await response.json();
      setConnection("preview", "previewStatus", "topologyFromJson", { detail: friendlyNetworkError(apiError) });
    } catch {
      state.topology = copyTopology(SAMPLE_TOPOLOGY);
      setConnection("preview", "previewStatus", "topologySample", { detail: friendlyNetworkError(apiError) });
    }
  }
  try {
    render();
    $("graph-loading").hidden = true;
    await calculateRoute();
  } catch (error) {
    const overlay = $("graph-loading");
    overlay.textContent = t("screenError", { detail: error.message });
    overlay.hidden = false;
    setConnection("error", "screenErrorStatus", "screenError", { detail: error.message });
  }
}

function positionsFor(routers) {
  const defaults = {
    A: { x: 120, y: 100 }, B: { x: 390, y: 100 },
    C: { x: 120, y: 300 }, D: { x: 390, y: 300 },
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
    $("graph-loading").textContent = t("graphLibraryError");
    $("graph-loading").hidden = false;
    setConnection("error", "graphErrorStatus", "graphLibraryError");
    throw new Error(t("graphLibraryError"));
  }
  state.cy = cytoscape({
    container: $("cy"),
    elements: graphElements(state.topology),
    layout: { name: "preset", fit: true, padding: 54 },
    minZoom: 0.65,
    maxZoom: 2.1,
    style: [
      { selector: "node", style: {
        label: "data(label)", width: 58, height: 58, "background-color": "#e8f2ee",
        "border-width": 2, "border-color": "#177a5b", color: "#263530",
        "font-size": 16, "font-family": "Malgun Gothic, 맑은 고딕, sans-serif", "font-weight": 500,
        "text-valign": "center", "text-halign": "center", "overlay-opacity": 0,
        "shadow-blur": 3, "shadow-color": "#177a5b", "shadow-opacity": 0.12,
      } },
      { selector: "edge", style: {
        width: 2, "line-color": "#788981", "curve-style": "bezier", label: "data(label)",
        color: "#263530", "font-size": 12, "font-family": "Malgun Gothic, 맑은 고딕, sans-serif",
        "font-weight": 500, "text-background-color": "#ffffff", "text-background-opacity": 1,
        "text-background-padding": 5, "text-border-color": "#dce5e1", "text-border-width": 1,
        "text-border-opacity": 1, "overlay-opacity": 0, "target-arrow-shape": "none",
      } },
      { selector: "edge.inactive", style: { "line-color": "#a4ada9", "line-style": "dashed", color: "#69746f", opacity: 0.7 } },
      { selector: "edge.selected-link", style: { "line-color": "#d78424", width: 3, "z-index": 5, color: "#7a4a14" } },
      { selector: "edge.route", style: {
        "line-color": "#177a5b", width: 5, "z-index": 10, color: "#174b39",
        "text-background-color": "#e8f4ed", "text-border-color": "#177a5b",
        "shadow-blur": 3, "shadow-color": "#177a5b", "shadow-opacity": 0.2,
      } },
      { selector: "node.route-node", style: {
        "border-color": "#0f654b", "border-width": 3, "shadow-color": "#177a5b",
        "shadow-opacity": 0.18, "shadow-blur": 4,
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
      option.textContent = t("routerOption", { id: router.id });
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
    $("selected-link-name").textContent = t("noLinkSelected");
    $("selected-link-state").textContent = "—";
    $("selected-link-state").removeAttribute("data-active");
    $("toggle-button-label").textContent = t("noLinkButton");
    button.disabled = true;
    return;
  }
  $("selected-link-name").textContent = t("selectedLinkValue", { source: link.source, target: link.target, cost: link.cost });
  $("selected-link-state").textContent = link.active ? t("active") : t("failed");
  $("selected-link-state").dataset.active = String(link.active);
  $("toggle-button-label").textContent = link.active ? t("failSelectedLink") : t("restoreSelectedLink");
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
  $("control-note").textContent = state.selectedLinkId
    ? t("selectedLinkInstruction", { link: linkId })
    : t("noLinkInstruction");
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

function setResultBadge(key, mode) {
  const badge = $("result-badge");
  badge.textContent = t(key);
  badge.dataset.state = mode;
}

function renderRoute() {
  $("result-source").textContent = state.source || "—";
  $("result-destination").textContent = state.destination || "—";
  const route = state.route;
  if (!route) {
    $("result-cost").textContent = "—";
    $("result-path").textContent = t("initialPath");
    setResultBadge("idle", "");
    $("result-note").textContent = t("initialResultNote");
    applyRouteHighlight();
    return;
  }
  if (route.error) {
    $("result-cost").textContent = "—";
    $("result-path").textContent = t("apiErrorBadge");
    setResultBadge("apiErrorBadge", "error");
    $("result-note").textContent = t("routeCalculationError", { detail: route.errorDetail });
    applyRouteHighlight();
    return;
  }
  if (!route.reachable) {
    $("result-cost").textContent = "—";
    $("result-path").textContent = t("noRoute");
    setResultBadge("noRoute", "error");
    $("result-note").textContent = t(route.noteKey || "noRouteNote");
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
  setResultBadge(route.preview ? "previewBadge" : "routeCalculatedBadge", route.preview ? "preview" : "success");
  $("result-note").textContent = t(route.noteKey || "backendRouteNote");
  applyRouteHighlight();
}

function demoRoute() {
  const activeIds = new Set(state.topology.links.filter((link) => link.active).map((link) => link.id));
  if (state.source === "A" && state.destination === "D" && activeIds.has("AB") && activeIds.has("BD")) {
    return { source: "A", destination: "D", path: ["A", "B", "D"], total_cost: 2, reachable: true, preview: true, noteKey: "previewRouteNote" };
  }
  return null;
}

async function calculateRoute() {
  state.source = $("source-select").value;
  state.destination = $("destination-select").value;
  state.route = null;
  $("calculate-button").disabled = true;
  $("result-path").textContent = t("calculating");
  setResultBadge("calculating", "");
  renderRoute();
  try {
    const route = await requestJson("/api/route", {
      method: "POST",
      body: JSON.stringify({ source: state.source, destination: state.destination }),
    });
    state.route = { ...route, preview: false, noteKey: route.reachable ? "backendRouteNote" : "noRouteNote" };
  } catch (error) {
    const preview = demoRoute();
    if (preview && (error.status === 501 || !error.status)) {
      state.route = preview;
    } else {
      state.route = { error: true, errorDetail: friendlyNetworkError(error) };
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
    setConnection("connected", "connectedStatus", "linkUpdatedMessage", { link: link.id });
    setControlNote("linkUpdatedNote", { link: link.id });
  } catch (error) {
    if (error.status) {
      setConnection("error", "apiErrorStatus", "linkUpdateError", { link: link.id, detail: friendlyNetworkError(error) });
      $("toggle-link-button").disabled = false;
      return;
    }
    link.active = !link.active;
    setConnection("preview", "localPreviewStatus", "localLinkMessage");
    setControlNote("localLinkNote");
  }
  state.route = null;
  render();
}

async function resetTopology() {
  $("reset-button").disabled = true;
  try {
    state.topology = await requestJson("/api/reset", { method: "POST" });
    setConnection("connected", "resetSuccess", "resetSuccessMessage");
  } catch (error) {
    if (error.status) {
      setConnection("error", "apiErrorStatus", "resetError", { detail: friendlyNetworkError(error) });
      $("reset-button").disabled = false;
      return;
    }
    state.topology = copyTopology(SAMPLE_TOPOLOGY);
    setConnection("preview", "localPreviewStatus", "localResetMessage");
  }
  state.selectedLinkId = null;
  state.route = null;
  $("reset-button").disabled = false;
  setControlNote("resetDone");
  render();
}

function bindEvents() {
  $("language-toggle").addEventListener("click", () => setLanguage(state.language === "ko" ? "en" : "ko"));
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
applyLanguage();
loadTopology();
