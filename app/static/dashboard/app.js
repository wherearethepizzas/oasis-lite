const state = {
  leaderboard: [],
  leaderboardExpanded: false,
  selectedCampaignId: null,
};

const metricLabels = {
  impressions: "Impressions",
  clicks: "Clicks",
  streams: "Streams",
  saves: "Saves",
  skips: "Skips",
  click_through_rate: "CTR",
  stream_rate: "Stream Rate",
  save_rate: "Save Rate",
  skip_rate: "Skip Rate",
};

const trafficPresets = {
  low: 5,
  medium: 25,
  high: 100,
};

const performanceProfiles = {
  good: { skip: 0.10, click: 0.35, stream: 0.18, save: 0.08 },
  mid: { skip: 0.28, click: 0.16, stream: 0.08, save: 0.03 },
  bad: { skip: 0.65, click: 0.05, stream: 0.02, save: 0.01 },
};

const simulatorConcurrency = 5;

const elements = {
  apiStatus: document.querySelector("#api-status"),
  refreshDashboard: document.querySelector("#refresh-dashboard"),
  leaderboardMetric: document.querySelector("#leaderboard-metric"),
  leaderboardToggle: document.querySelector("#leaderboard-toggle"),
  leaderboardBody: document.querySelector("#leaderboard-body"),
  campaignForm: document.querySelector("#campaign-form"),
  campaignId: document.querySelector("#campaign-id"),
  campaignDetail: document.querySelector("#campaign-detail"),
  recommendationForm: document.querySelector("#recommendation-form"),
  recommendationUserId: document.querySelector("#recommendation-user-id"),
  recommendationLimit: document.querySelector("#recommendation-limit"),
  recommendationMode: document.querySelector("#recommendation-mode"),
  recommendationThreshold: document.querySelector("#recommendation-threshold"),
  recommendationMetrics: document.querySelector("#recommendation-metrics"),
  recommendationBody: document.querySelector("#recommendation-body"),
  simulatorForm: document.querySelector("#simulator-form"),
  simulatorTraffic: document.querySelector("#simulator-traffic"),
  simulatorPerformance: document.querySelector("#simulator-performance"),
  simulatorLimit: document.querySelector("#simulator-limit"),
  simulatorMode: document.querySelector("#simulator-mode"),
  simulatorThreshold: document.querySelector("#simulator-threshold"),
  simulatorSeed: document.querySelector("#simulator-seed"),
  simulatorRun: document.querySelector("#simulator-run"),
  simulatorProgressBar: document.querySelector("#simulator-progress-bar"),
  simulatorProgressCopy: document.querySelector("#simulator-progress-copy"),
  simulatorSummary: document.querySelector("#simulator-summary"),
};

function setText(id, value) {
  const element = document.querySelector(`#${id}`);
  if (element) {
    element.textContent = value;
  }
}

function setStatus(message, variant = "") {
  elements.apiStatus.textContent = message;
  elements.apiStatus.className = `status-pill ${variant}`.trim();
}

function formatInteger(value) {
  const numberValue = Number(value || 0);
  return new Intl.NumberFormat().format(numberValue);
}

function formatDecimal(value, digits = 3) {
  const numberValue = Number(value || 0);
  return numberValue.toFixed(digits);
}

function formatRate(value) {
  return `${formatDecimal(Number(value || 0) * 100, 1)}%`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

async function postJson(path, payload) {
  return fetchJson(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function fetchText(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.text();
}

function aggregateCampaigns(campaigns) {
  return campaigns.reduce(
    (totals, campaign) => {
      totals.impressions += Number(campaign.impressions || 0);
      totals.clicks += Number(campaign.clicks || 0);
      totals.streams += Number(campaign.streams || 0);
      totals.saves += Number(campaign.saves || 0);
      totals.skips += Number(campaign.skips || 0);
      return totals;
    },
    { impressions: 0, clicks: 0, streams: 0, saves: 0, skips: 0 },
  );
}

function updateKpis(campaigns, activeCampaignCount) {
  const totals = aggregateCampaigns(campaigns);
  const denominator = totals.impressions || 0;
  setText("kpi-active-campaigns", formatInteger(activeCampaignCount));
  setText("kpi-impressions", formatInteger(totals.impressions));
  setText("kpi-ctr", denominator ? formatRate(totals.clicks / denominator) : "0.0%");
  setText("kpi-stream-rate", denominator ? formatRate(totals.streams / denominator) : "0.0%");
  setText("kpi-save-rate", denominator ? formatRate(totals.saves / denominator) : "0.0%");
}

function renderLeaderboard(campaigns) {
  if (!campaigns.length) {
    elements.leaderboardBody.innerHTML = '<tr><td colspan="7" class="empty-cell">No campaign metrics found</td></tr>';
    elements.leaderboardToggle.hidden = true;
    return;
  }

  const visibleCampaigns = state.leaderboardExpanded ? campaigns : campaigns.slice(0, 5);
  elements.leaderboardToggle.hidden = campaigns.length <= 5;
  elements.leaderboardToggle.textContent = state.leaderboardExpanded ? "Show top 5" : `Show all ${campaigns.length}`;
  elements.leaderboardToggle.setAttribute("aria-expanded", String(state.leaderboardExpanded));

  elements.leaderboardBody.innerHTML = visibleCampaigns
    .map((campaign) => {
      const selected = campaign.campaign_id === state.selectedCampaignId ? "selected" : "";
      return `
        <tr class="${selected}" data-campaign-id="${campaign.campaign_id}">
          <td>#${campaign.campaign_id}</td>
          <td>${formatInteger(campaign.impressions)}</td>
          <td>${formatInteger(campaign.clicks)}</td>
          <td>${formatInteger(campaign.streams)}</td>
          <td>${formatInteger(campaign.saves)}</td>
          <td>${formatRate(campaign.click_through_rate)}</td>
          <td>${formatRate(campaign.stream_rate)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderCampaignDetail(metrics) {
  const stats = [
    ["Impressions", formatInteger(metrics.impressions)],
    ["Clicks", formatInteger(metrics.clicks)],
    ["Streams", formatInteger(metrics.streams)],
    ["Saves", formatInteger(metrics.saves)],
    ["Skips", formatInteger(metrics.skips)],
    ["CTR", formatRate(metrics.click_through_rate)],
    ["Stream Rate", formatRate(metrics.stream_rate)],
    ["Save Rate", formatRate(metrics.save_rate)],
    ["Skip Rate", formatRate(metrics.skip_rate)],
  ];
  elements.campaignDetail.innerHTML = stats
    .map(([label, value]) => `
      <div class="detail-stat">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `)
    .join("");
}

function renderCampaignError(message) {
  elements.campaignDetail.innerHTML = `<div class="error-state">${escapeHtml(message)}</div>`;
}

async function loadCampaignDetail(campaignId) {
  state.selectedCampaignId = Number(campaignId);
  elements.campaignId.value = campaignId;
  renderLeaderboard(state.leaderboard);
  elements.campaignDetail.innerHTML = '<div class="empty-state">Loading campaign metrics</div>';
  try {
    const metrics = await fetchJson(`/campaigns/${encodeURIComponent(campaignId)}/metrics`);
    renderCampaignDetail(metrics);
  } catch (error) {
    renderCampaignError(error.message);
  }
}

async function loadActiveCampaignCount() {
  const activeCampaigns = await fetchJson("/campaigns/active");
  return Array.isArray(activeCampaigns) ? activeCampaigns.length : 0;
}

async function loadLeaderboard() {
  const metric = elements.leaderboardMetric.value;
  const campaigns = await fetchJson(`/campaigns/leaderboard?metric=${encodeURIComponent(metric)}`);
  state.leaderboard = Array.isArray(campaigns) ? campaigns : [];
  renderLeaderboard(state.leaderboard);
  if (state.leaderboard.length && !state.selectedCampaignId) {
    await loadCampaignDetail(state.leaderboard[0].campaign_id);
  }
  return state.leaderboard;
}

function parsePrometheusMetrics(text) {
  const parsed = {};
  for (const line of text.split("\n")) {
    if (!line || line.startsWith("#")) {
      continue;
    }
    const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^}]*\})?\s+(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)$/i);
    if (!match) {
      continue;
    }
    const [, name, value] = match;
    if (parsed[name] === undefined) {
      parsed[name] = Number(value);
    }
  }
  return parsed;
}

async function loadPrometheusMetrics() {
  const text = await fetchText("/metrics");
  const metrics = parsePrometheusMetrics(text);
  const latencyCount = metrics.recommendation_latency_seconds_count || 0;
  const latencySum = metrics.recommendation_latency_seconds_sum || 0;
  const averageLatency = latencyCount ? latencySum / latencyCount : 0;

  setText("runtime-requests", formatInteger(metrics.recommendation_requests_total));
  setText("runtime-latency", `${formatDecimal(averageLatency, 3)}s`);
  setText("runtime-served", formatInteger(metrics.promoted_tracks_served_total));
  setText("runtime-events", formatInteger(metrics.promotion_events_total));

  if (metrics.active_campaigns_total !== undefined) {
    setText("kpi-active-campaigns", formatInteger(metrics.active_campaigns_total));
  }
}

function renderRecommendationMetrics(metrics) {
  if (!metrics) {
    elements.recommendationMetrics.innerHTML = '<div class="empty-state">No evaluation metrics returned</div>';
    return;
  }

  const stats = [
    ["Recommended", formatInteger(metrics.recommended_count)],
    ["Relevant Items", formatInteger(metrics.relevant_items_count)],
    ["Relevant Hits", formatInteger(metrics.relevant_recommended_count)],
    ["Precision@K", formatDecimal(metrics.precision_at_k)],
    ["Recall@K", formatDecimal(metrics.recall_at_k)],
    ["NDCG@K", formatDecimal(metrics.ndcg_at_k)],
    ["MAP@K", formatDecimal(metrics.map_at_k)],
  ];
  elements.recommendationMetrics.innerHTML = stats
    .map(([label, value]) => `
      <div class="eval-stat">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `)
    .join("");
}

function renderRecommendations(recommendations) {
  if (!recommendations.length) {
    elements.recommendationBody.innerHTML = '<tr><td colspan="7" class="empty-cell">No promoted tracks returned</td></tr>';
    return;
  }

  elements.recommendationBody.innerHTML = recommendations
    .map((track) => `
      <tr>
        <td>${track.rank_position}</td>
        <td>${escapeHtml(track.track_name)}<br><span class="metric-subtext">${escapeHtml(track.track_id)}</span></td>
        <td>${escapeHtml(track.artist_name)}</td>
        <td>${escapeHtml(track.genre || "Unknown")}</td>
        <td>${escapeHtml(track.objective)}</td>
        <td>${formatDecimal(track.final_score)}</td>
        <td>${formatDecimal(track.relevance_score)}</td>
      </tr>
    `)
    .join("");
}

function createSeededRandom(seed) {
  let value = Number(seed);
  if (!Number.isFinite(value)) {
    value = 42;
  }
  value = Math.trunc(value) || 42;
  return function random() {
    value |= 0;
    value = (value + 0x6d2b79f5) | 0;
    let mixed = Math.imul(value ^ (value >>> 15), 1 | value);
    mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), 61 | mixed);
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
  };
}

function clampInteger(value, fallback, min, max) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.min(Math.max(parsed, min), max);
}

function createSimulationSummary(requestsAttempted) {
  return {
    requestsAttempted,
    requestsCompleted: 0,
    impressions: 0,
    clicks: 0,
    streams: 0,
    saves: 0,
    skips: 0,
    failures: 0,
    campaigns: new Set(),
    startedAt: performance.now(),
    elapsedSeconds: 0,
  };
}

function setSimulationProgress(completed, total, message) {
  const percent = total ? Math.round((completed / total) * 100) : 0;
  elements.simulatorProgressBar.style.width = `${percent}%`;
  elements.simulatorProgressCopy.textContent = message;
}

function renderSimulationSummary(summary) {
  const stats = [
    ["Requests", `${formatInteger(summary.requestsCompleted)} / ${formatInteger(summary.requestsAttempted)}`],
    ["Impressions", formatInteger(summary.impressions)],
    ["Clicks", formatInteger(summary.clicks)],
    ["Streams", formatInteger(summary.streams)],
    ["Saves", formatInteger(summary.saves)],
    ["Skips", formatInteger(summary.skips)],
    ["Campaigns", formatInteger(summary.campaigns.size)],
    ["Failures", formatInteger(summary.failures)],
    ["Elapsed", `${formatDecimal(summary.elapsedSeconds, 1)}s`],
  ];
  elements.simulatorSummary.innerHTML = stats
    .map(([label, value]) => `
      <div class="sim-stat">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `)
    .join("");
}

function renderSimulationError(message) {
  elements.simulatorSummary.innerHTML = `<div class="error-state">${escapeHtml(message)}</div>`;
}

async function fetchRecommendationReadyUsers() {
  const users = await fetchJson("/users/recommendation-ready?limit=500");
  return Array.isArray(users) ? users.filter((user) => user.user_id) : [];
}

async function postSimulatedEvent(summary, impressionId, eventType) {
  await postJson("/promotion-events", {
    impression_id: impressionId,
    event_type: eventType,
  });
  if (eventType === "click") {
    summary.clicks += 1;
  } else if (eventType === "stream") {
    summary.streams += 1;
  } else if (eventType === "save") {
    summary.saves += 1;
  } else if (eventType === "skip") {
    summary.skips += 1;
  }
}

async function simulateRecommendationRequest(job, config, summary) {
  const params = new URLSearchParams({
    limit: String(config.limit),
    relevance_mode: config.relevanceMode,
    threshold: String(config.threshold),
  });
  const payload = await fetchJson(`/recommendations/promoted/${encodeURIComponent(job.userId)}?${params.toString()}`);
  const recommendations = payload.recommendations || [];
  const random = createSeededRandom(job.seed);

  for (const recommendation of recommendations) {
    if (!recommendation.impression_id) {
      summary.failures += 1;
      continue;
    }
    summary.impressions += 1;
    summary.campaigns.add(recommendation.campaign_id);

    if (random() < config.profile.skip) {
      await postSimulatedEvent(summary, recommendation.impression_id, "skip");
      continue;
    }
    if (random() < config.profile.click) {
      await postSimulatedEvent(summary, recommendation.impression_id, "click");
    }
    if (random() < config.profile.stream) {
      await postSimulatedEvent(summary, recommendation.impression_id, "stream");
    }
    if (random() < config.profile.save) {
      await postSimulatedEvent(summary, recommendation.impression_id, "save");
    }
  }
}

async function runTrafficSimulation() {
  const traffic = elements.simulatorTraffic.value;
  const performance = elements.simulatorPerformance.value;
  const requestCount = trafficPresets[traffic] || trafficPresets.low;
  const seed = clampInteger(elements.simulatorSeed.value, 42, -2147483648, 2147483647);
  const config = {
    limit: clampInteger(elements.simulatorLimit.value, 10, 1, 50),
    relevanceMode: elements.simulatorMode.value,
    threshold: clampInteger(elements.simulatorThreshold.value, 1, 1, 1000000),
    profile: performanceProfiles[performance] || performanceProfiles.mid,
  };
  const summary = createSimulationSummary(requestCount);

  elements.simulatorRun.disabled = true;
  setStatus("Simulating");
  setSimulationProgress(0, requestCount, `Preparing ${traffic} traffic simulation`);
  renderSimulationSummary(summary);

  try {
    const users = await fetchRecommendationReadyUsers();
    if (!users.length) {
      throw new Error("No recommendation-ready users found");
    }

    const random = createSeededRandom(seed);
    const jobs = Array.from({ length: requestCount }, (_, index) => {
      const user = users[Math.floor(random() * users.length)];
      return {
        userId: user.user_id,
        seed: seed + index * 9973 + 17,
      };
    });

    let nextJobIndex = 0;
    async function worker() {
      while (nextJobIndex < jobs.length) {
        const currentIndex = nextJobIndex;
        nextJobIndex += 1;
        try {
          await simulateRecommendationRequest(jobs[currentIndex], config, summary);
        } catch {
          summary.failures += 1;
        } finally {
          summary.requestsCompleted += 1;
          summary.elapsedSeconds = (performanceNow() - summary.startedAt) / 1000;
          setSimulationProgress(
            summary.requestsCompleted,
            requestCount,
            `${summary.requestsCompleted} of ${requestCount} recommendation requests complete`,
          );
          renderSimulationSummary(summary);
        }
      }
    }

    await Promise.all(Array.from({ length: Math.min(simulatorConcurrency, jobs.length) }, worker));
    summary.elapsedSeconds = (performanceNow() - summary.startedAt) / 1000;
    renderSimulationSummary(summary);
    setSimulationProgress(requestCount, requestCount, "Simulation complete");
    await refreshDashboard();
    setStatus("Live", "ok");
  } catch (error) {
    setStatus("Error", "error");
    renderSimulationError(error.message);
    setSimulationProgress(summary.requestsCompleted, requestCount, "Simulation failed");
  } finally {
    elements.simulatorRun.disabled = false;
  }
}

function performanceNow() {
  return window.performance ? window.performance.now() : Date.now();
}

function renderRecommendationError(message) {
  elements.recommendationMetrics.innerHTML = `<div class="error-state">${escapeHtml(message)}</div>`;
  elements.recommendationBody.innerHTML = '<tr><td colspan="7" class="empty-cell">Recommendation request failed</td></tr>';
}

async function runRecommendations() {
  const userId = elements.recommendationUserId.value.trim();
  const limit = elements.recommendationLimit.value || "10";
  const mode = elements.recommendationMode.value;
  const threshold = elements.recommendationThreshold.value || "1";

  if (!userId) {
    elements.recommendationUserId.focus();
    return;
  }

  const params = new URLSearchParams({
    limit,
    relevance_mode: mode,
    threshold,
  });
  elements.recommendationMetrics.innerHTML = '<div class="empty-state">Loading promoted ranking</div>';
  elements.recommendationBody.innerHTML = '<tr><td colspan="7" class="empty-cell">Loading recommendations</td></tr>';

  try {
    const payload = await fetchJson(`/recommendations/promoted/${encodeURIComponent(userId)}?${params.toString()}`);
    renderRecommendationMetrics(payload.metrics);
    renderRecommendations(payload.recommendations || []);
    await loadPrometheusMetrics();
  } catch (error) {
    renderRecommendationError(error.message);
  }
}

async function refreshDashboard() {
  elements.refreshDashboard.disabled = true;
  setStatus("Loading");
  try {
    const [campaigns, activeCampaignCount] = await Promise.all([
      loadLeaderboard(),
      loadActiveCampaignCount(),
      loadPrometheusMetrics().catch(() => null),
    ]).then(([leaderboard, activeCount]) => [leaderboard, activeCount]);
    updateKpis(campaigns, activeCampaignCount);
    setStatus("Live", "ok");
  } catch (error) {
    setStatus("Error", "error");
    elements.leaderboardBody.innerHTML = `<tr><td colspan="7" class="empty-cell">${escapeHtml(error.message)}</td></tr>`;
  } finally {
    elements.refreshDashboard.disabled = false;
  }
}

elements.refreshDashboard.addEventListener("click", refreshDashboard);
elements.leaderboardMetric.addEventListener("change", refreshDashboard);
elements.leaderboardToggle.addEventListener("click", () => {
  state.leaderboardExpanded = !state.leaderboardExpanded;
  renderLeaderboard(state.leaderboard);
});
elements.leaderboardBody.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-campaign-id]");
  if (row) {
    loadCampaignDetail(row.dataset.campaignId);
  }
});
elements.campaignForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (elements.campaignId.value) {
    loadCampaignDetail(elements.campaignId.value);
  }
});
elements.recommendationForm.addEventListener("submit", (event) => {
  event.preventDefault();
  runRecommendations();
});
elements.simulatorForm.addEventListener("submit", (event) => {
  event.preventDefault();
  runTrafficSimulation();
});

refreshDashboard();
