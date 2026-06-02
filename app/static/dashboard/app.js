const state = {
  leaderboard: [],
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

const elements = {
  apiStatus: document.querySelector("#api-status"),
  refreshDashboard: document.querySelector("#refresh-dashboard"),
  leaderboardMetric: document.querySelector("#leaderboard-metric"),
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

async function fetchJson(path) {
  const response = await fetch(path);
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
    return;
  }

  elements.leaderboardBody.innerHTML = campaigns
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

refreshDashboard();
