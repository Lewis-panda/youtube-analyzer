let indexData = null;
let currentChannel = null;
let currentPage = "overview";
let videoRowsCache = null;

const pages = [
  { id: "overview", label: "決策總覽" },
  { id: "benchmark", label: "同儕比較" },
  { id: "content", label: "內容策略" },
  { id: "community", label: "社群網路" },
  { id: "risk", label: "情緒與衝突" },
  { id: "details", label: "資料鑽取" },
];

const selectedMetrics = [
  "comments_per_1k_views",
  "high_mid_tier_commenter_share",
  "continuity_return_rate_w4",
  "community_hhi",
  "negative_rate",
  "like_weighted_negative_rate",
  "reply_share_all_comments",
  "max_video_like_weighted_conflict_score",
];

const $ = (id) => document.getElementById(id);

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function init() {
  indexData = await fetchJson("/api/index");
  $("search").addEventListener("input", renderChannelList);
  $("subscriber-filter").addEventListener("change", renderChannelList);
  renderGlobalStats();
  renderRailInsights();
  renderChannelList();
  const first = indexData.examples?.[0];
  if (first) await loadChannel(first.slug);
}

function renderGlobalStats() {
  const stats = indexData.dashboard_statistics || {};
  const totals = stats.totals || {};
  $("global-stats").innerHTML = `
    <div><span>完成案例</span><strong>${fmtNumber(indexData.n_examples)}</strong></div>
    <div><span>Baseline</span><strong>${fmtNumber(indexData.baseline?.cohort_n_ready)}</strong></div>
    <div><span>分析影片</span><strong>${fmtNumber(totals.videos)}</strong></div>
    <div><span>頂層留言</span><strong>${fmtCompact(totals.comments)}</strong></div>
  `;
}

function renderRailInsights() {
  const boards = indexData.dashboard_statistics?.leaderboards || [];
  const wanted = ["comments_per_1k_views", "continuity_return_rate_w4", "like_weighted_negative_rate"];
  const picked = boards.filter((board) => wanted.includes(board.metric));
  $("rail-insights").innerHTML = picked
    .map(
      (board) => `
        <button class="rail-board" data-metric="${escapeHtml(board.metric)}">
          <span>${escapeHtml(board.title)}</span>
          <strong>${escapeHtml(board.top?.[0]?.channel || "-")}</strong>
          <em>${formatValue(board.top?.[0]?.value, board.metric)}</em>
        </button>
      `,
    )
    .join("");
}

function filteredExamples() {
  const query = $("search").value.trim().toLowerCase();
  const minSubs = Number($("subscriber-filter").value || 0);
  return (indexData.examples || []).filter((item) => {
    const text = `${item.title || ""} ${item.slug || ""} ${item.archetype || ""}`.toLowerCase();
    return (!query || text.includes(query)) && Number(item.subscriber_count || 0) >= minSubs;
  });
}

function renderChannelList() {
  const rows = filteredExamples();
  $("examples").innerHTML = rows
    .map((item) => {
      const scores = item.analysis_scores || {};
      const active = currentChannel?.slug === item.slug ? "active" : "";
      return `
        <button class="channel-row ${active}" data-slug="${escapeHtml(item.slug)}">
          <span class="channel-name">${escapeHtml(item.title || item.slug)}</span>
          <span class="channel-meta-line">
            ${fmtCompact(item.subscriber_count)} 訂閱 · ${fmtNumber(item.n_videos_in_scope)} 片 · ${escapeHtml(item.archetype || "未分型")}
          </span>
          <span class="micro-scores">
            <i style="--v:${scorePct(scores.engagement_conversion)}"></i>
            <i style="--v:${scorePct(scores.audience_stickiness)}"></i>
            <i class="risk" style="--v:${scorePct(scores.risk_pressure)}"></i>
          </span>
        </button>
      `;
    })
    .join("");
  $("examples").querySelectorAll(".channel-row").forEach((button) => {
    button.addEventListener("click", () => loadChannel(button.dataset.slug));
  });
}

async function loadChannel(slug) {
  currentChannel = await fetchJson(`/api/channels/${encodeURIComponent(slug)}`);
  currentPage = "overview";
  videoRowsCache = null;
  renderChannelList();
  renderShell();
  await renderPage();
}

function renderShell() {
  const ch = currentChannel.channel || {};
  const archetype = currentChannel.analysis?.archetype || {};
  $("channel-eyebrow").textContent = archetype.label_zh || "頻道分析";
  $("channel-title").textContent = currentChannel.title || currentChannel.slug;
  $("channel-meta").textContent = [
    ch.custom_url || currentChannel.channel_id,
    `${fmtCompact(ch.subscriber_count)} 訂閱`,
    `${fmtNumber(ch.n_videos_in_scope)} 支影片`,
    `${fmtCompact(ch.n_comments_in_scope)} 則留言`,
  ]
    .filter(Boolean)
    .join(" · ");
  $("channel-window").textContent = `${compactDate(ch.date_min)} 至 ${compactDate(ch.date_max)}`;
  $("view-tabs").innerHTML = pages
    .map(
      (page) => `
        <button class="${page.id === currentPage ? "active" : ""}" data-page="${page.id}">
          ${escapeHtml(page.label)}
        </button>
      `,
    )
    .join("");
  $("view-tabs").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", async () => {
      currentPage = button.dataset.page;
      renderShell();
      await renderPage();
    });
  });
}

async function renderPage() {
  const root = $("page-content");
  root.innerHTML = "";
  if (currentPage === "overview") renderOverview(root);
  else if (currentPage === "benchmark") renderBenchmark(root);
  else if (currentPage === "content") await renderContent(root);
  else if (currentPage === "community") renderCommunity(root);
  else if (currentPage === "risk") renderRisk(root);
  else if (currentPage === "details") await renderDetails(root);
}

function renderOverview(root) {
  const analysis = currentChannel.analysis || {};
  const archetype = analysis.archetype || {};
  root.innerHTML = `
    <section class="hero-grid">
      <article class="archetype-panel">
        <div class="compact-heading">
          <span>頻道型態</span>
          ${infoTip([archetype.summary_zh, analysis.method_notes_zh?.[0]].filter(Boolean).join("\n\n"))}
        </div>
        <h3>${escapeHtml(archetype.label_zh || "-")}</h3>
        <div class="archetype-scoreline">${scoreline(analysis.indices || [])}</div>
      </article>
      <article class="map-panel">
        <div class="panel-head">
          <div>
            <span class="kicker">Cohort Map</span>
            <h3>互動與風險位置</h3>
          </div>
          <small>48 頻道 benchmark</small>
        </div>
        ${scatterPlot("engagement_vs_risk")}
      </article>
    </section>

    <section class="score-strip">
      ${(analysis.indices || []).map(indexTile).join("")}
    </section>

    <section class="split-layout">
      <article class="panel">
        <div class="panel-head">
          <div>
            <span class="kicker">Decision Queue</span>
            <h3>先看這幾件事</h3>
          </div>
        </div>
        <div class="decision-list">${(analysis.decision_queue || []).map(decisionRow).join("")}</div>
      </article>
      <article class="panel">
        <div class="panel-head">
          <div>
            <span class="kicker">Signals</span>
            <h3>主要訊號</h3>
          </div>
        </div>
        <div class="story-grid">${(analysis.story_cards || []).slice(0, 5).map(storyCard).join("")}</div>
      </article>
    </section>
  `;
}

function renderBenchmark(root) {
  const metrics = currentChannel.baseline?.all_metrics || [];
  const metricMap = Object.fromEntries(metrics.map((item) => [item.metric, item]));
  const maps = currentChannel.analysis?.benchmark_maps || {};
  root.innerHTML = `
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head">
          <div>
            <span class="kicker">Position</span>
            <h3>同儕位置圖</h3>
          </div>
        </div>
        ${scatterPlot("engagement_vs_risk")}
        ${scatterPlot("stickiness_vs_concentration")}
        <div class="compact-note">
          <span>象限判讀</span>
          ${infoTip(Object.values(maps.engagement_vs_risk?.quadrant_hints_zh || {}).join("\n"))}
        </div>
      </article>
      <article class="panel">
        <div class="panel-head">
          <div>
            <span class="kicker">Distribution</span>
            <h3>關鍵指標分布</h3>
          </div>
          <small>顯示 median / IQR / 目前頻道</small>
        </div>
        <div class="bullet-list">
          ${selectedMetrics.map((metric) => bulletMetric(metricMap[metric])).join("")}
        </div>
      </article>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <span class="kicker">Leaderboards</span>
          <h3>Benchmark 參照頻道</h3>
        </div>
      </div>
      <div class="leaderboard-grid">
        ${(indexData.dashboard_statistics?.leaderboards || []).slice(0, 8).map(leaderboard).join("")}
      </div>
    </section>
  `;
}

async function renderContent(root) {
  const s = currentChannel.dashboard_summary || {};
  const videos = await getVideoRows();
  root.innerHTML = `
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head">
          <div>
            <span class="kicker">Theme Mix</span>
            <h3>題材組合</h3>
          </div>
        </div>
        ${themeMix(s.top_themes || [])}
      </article>
      <article class="panel">
        <div class="panel-head">
          <div>
            <span class="kicker">Timeline</span>
            <h3>影片留言時間線</h3>
          </div>
        </div>
        ${videoTimeline(videos)}
      </article>
    </section>
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Clusters</span><h3>共享觀眾影片群</h3></div></div>
        ${clusterList(s.video_clusters || [])}
      </article>
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Top Videos</span><h3>高留言影片</h3></div></div>
        ${tableFromRows(sortRows(videos, "observed_comments").slice(0, 10), ["title", "published_at", "view_count", "observed_comments", "observed_commenters"])}
      </article>
    </section>
  `;
}

function renderCommunity(root) {
  const s = currentChannel.dashboard_summary || {};
  const lens = lensById("audience");
  root.innerHTML = `
    <section class="score-strip">${(lens?.indices || []).map(indexTile).join("")}</section>
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Commenter Tiers</span><h3>留言者層級</h3></div></div>
        ${tierBars(s.commenter_tiers || [])}
      </article>
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Network</span><h3>留言者網路摘要</h3></div></div>
        ${keyValueGrid(s.network_summary || {})}
      </article>
    </section>
    <section class="panel">
      <div class="panel-head"><div><span class="kicker">Communities</span><h3>主要留言者社群</h3></div></div>
      ${communityBars(s.community_summary || [])}
    </section>
  `;
}

function renderRisk(root) {
  const s = currentChannel.dashboard_summary || {};
  const lens = lensById("risk");
  root.innerHTML = `
    <section class="score-strip">${(lens?.indices || []).map(indexTile).join("")}</section>
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Sentiment</span><h3>留言情緒結構</h3></div></div>
        ${sentimentStack(s.sentiment_summary || [])}
      </article>
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Reply Conflict</span><h3>回覆區風險摘要</h3></div></div>
        ${keyValueGrid(s.reply_overview || {})}
      </article>
    </section>
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Hotspots</span><h3>負面熱點影片</h3></div></div>
        ${tableFromRows(s.negative_hotspots || [], ["title", "negative_rate", "like_weighted_negative_rate", "primary_theme"])}
      </article>
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Conflict</span><h3>回覆衝突最高影片</h3></div></div>
        ${tableFromRows(s.reply_conflict_hotspots || [], ["title", "conflict_score", "reply_count_weighted_conflict_score", "like_weighted_conflict_score", "primary_theme"])}
      </article>
    </section>
  `;
}

async function renderDetails(root) {
  const report = await safeFetchReport();
  root.innerHTML = `
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Cold Report</span><h3>統計報告摘要</h3></div></div>
        <pre class="report-box">${escapeHtml(report || "目前沒有 report_zh.md。")}</pre>
      </article>
      <article class="panel">
        <div class="panel-head"><div><span class="kicker">Artifacts</span><h3>可鑽取資料表</h3></div></div>
        ${artifactList()}
      </article>
    </section>
  `;
}

function indexTile(item) {
  if (!item) return "";
  const score = Number(item.score || 0);
  const tone = item.polarity === "risk_high" ? "risk" : item.polarity === "benefit_high" ? "good" : "watch";
  return `
    <article class="score-card ${tone}">
      <div class="score-main">
        <span>${escapeHtml(item.short_label || item.label)} ${infoTip(`${item.question_zh || ""}\n\n${item.interpretation_zh || ""}`)}</span>
        <strong>${fmtScore(score)}</strong>
      </div>
      <div class="score-bar"><i style="width:${scorePct(score)}%"></i></div>
      <small>${escapeHtml(item.band || "")}</small>
    </article>
  `;
}

function storyCard(card) {
  return `
    <article class="story-card ${escapeHtml(card.kind || "context")}">
      <span>${kindLabel(card.kind)} ${infoTip(`${card.body_zh || ""}\n\n${card.next_step_zh || ""}`)}</span>
      <h4>${escapeHtml(card.title_zh || "")}</h4>
      <small>${escapeHtml(card.evidence_zh || "")}</small>
    </article>
  `;
}

function decisionRow(row) {
  return `
    <div class="decision-row ${escapeHtml(row.kind || "context")}">
      <span>${fmtNumber(row.rank)}</span>
      <div>
        <strong>${escapeHtml(row.title_zh || "")} ${infoTip(`${row.why_zh || ""}\n\n下一步：${row.next_step_zh || ""}`)}</strong>
      </div>
      <em>${escapeHtml(row.evidence_zh || "")}</em>
    </div>
  `;
}

function scatterPlot(mapId) {
  const mapMeta = indexData.dashboard_statistics?.cohort_position_maps?.maps?.find((item) => item.id === mapId);
  const points = indexData.dashboard_statistics?.cohort_position_maps?.points || [];
  const channelScores = currentChannel.analysis?.archetype?.scores || {};
  const xKey = mapMeta?.x || "engagement_conversion";
  const yKey = mapMeta?.y || "risk_pressure";
  const selected = {
    x: Number(channelScores[xKey] || 0),
    y: Number(channelScores[yKey] || 0),
  };
  const dots = points
    .filter((point) => Number.isFinite(Number(point.scores?.[xKey])) && Number.isFinite(Number(point.scores?.[yKey])))
    .map((point) => {
      const x = scalePlot(point.scores[xKey]);
      const y = 100 - scalePlot(point.scores[yKey]);
      const active = point.slug === currentChannel.slug ? " selected" : "";
      return `<circle class="dot${active}" cx="${x}" cy="${y}" r="${active ? 4.8 : 2.8}"><title>${escapeHtml(point.channel)} · ${fmtScore(point.scores[xKey])}, ${fmtScore(point.scores[yKey])}</title></circle>`;
    })
    .join("");
  const sx = scalePlot(selected.x);
  const sy = 100 - scalePlot(selected.y);
  return `
    <div class="scatter-wrap">
      <svg viewBox="0 0 100 100" role="img" aria-label="${escapeHtml(mapMeta?.title_zh || "benchmark map")}">
        <rect x="0" y="0" width="100" height="100" class="plot-bg"></rect>
        <line x1="50" y1="0" x2="50" y2="100" class="plot-axis"></line>
        <line x1="0" y1="50" x2="100" y2="50" class="plot-axis"></line>
        ${dots}
        <circle class="selected-dot" cx="${sx}" cy="${sy}" r="6"></circle>
      </svg>
      <div class="axis-label x">${escapeHtml(mapMeta?.x_label_zh || "")}</div>
      <div class="axis-label y">${escapeHtml(mapMeta?.y_label_zh || "")}</div>
    </div>
  `;
}

function bulletMetric(metric) {
  if (!metric) return "";
  const dist = metric.distribution || {};
  const min = Number(dist.min);
  const max = Number(dist.max);
  const p25 = pos(dist.p25, min, max);
  const p75 = pos(dist.p75, min, max);
  const median = pos(dist.median, min, max);
  const value = pos(metric.value, min, max);
  return `
    <div class="bullet-row">
      <div class="bullet-label">
        <strong>${escapeHtml(metric.label || metricLabel(metric.metric))} ${infoTip(`${metric.comparison?.summary_zh || ""}\n\n${metric.interpretation_hint_zh || ""}\n\n${metric.statistical_caution_zh || ""}`)}</strong>
        <span>${escapeHtml(metric.percentile_band || "")}</span>
      </div>
      <div class="bullet">
        <i class="iqr" style="left:${p25}%;width:${Math.max(2, p75 - p25)}%"></i>
        <i class="median" style="left:${median}%"></i>
        <i class="value" style="left:${value}%"></i>
      </div>
      <div class="bullet-value">
        <strong>${formatValue(metric.value, metric.metric)}</strong>
        <span>PR ${fmtScore(metric.percentile)}</span>
      </div>
    </div>
  `;
}

function themeMix(rows) {
  if (!rows.length) return `<div class="empty-state">沒有主題資料</div>`;
  const total = rows.reduce((sum, row) => sum + Number(row.n_comments || 0), 0) || 1;
  return `<div class="theme-mix">${rows
    .slice(0, 8)
    .map((row) => {
      const width = Math.max(4, (Number(row.n_comments || 0) / total) * 100);
      return `
        <div class="theme-row">
          <div><strong>${escapeHtml(themeLabel(row.primary_theme))}</strong><span>${fmtCompact(row.n_comments)} 留言 · ${fmtNumber(row.n_videos)} 片</span></div>
          <div class="theme-bar"><i style="width:${width}%"></i></div>
        </div>
      `;
    })
    .join("")}</div>`;
}

function videoTimeline(rows) {
  if (!rows.length) return `<div class="empty-state">沒有影片資料</div>`;
  const sample = rows.slice().sort((a, b) => String(a.published_at).localeCompare(String(b.published_at))).slice(-90);
  const max = Math.max(...sample.map((row) => Number(row.observed_comments || row.comment_count || 0)), 1);
  return `<div class="timeline">${sample
    .map((row) => {
      const h = Math.max(8, (Number(row.observed_comments || row.comment_count || 0) / max) * 100);
      return `<i style="height:${h}%" title="${escapeHtml(row.title)} · ${fmtNumber(row.observed_comments || row.comment_count)} 留言"></i>`;
    })
    .join("")}</div>`;
}

function clusterList(rows) {
  if (!rows.length) return `<div class="empty-state">沒有影片分群資料</div>`;
  return `<div class="cluster-list">${rows
    .slice(0, 5)
    .map(
      (row) => `
      <div class="cluster-row">
        <strong>Cluster ${escapeHtml(row.video_cluster)} ${infoTip(row.top_theme_labels || "")}</strong>
        <span>${fmtNumber(row.n_videos)} 片 · ${fmtCompact(row.unique_commenters)} 留言者 · ${fmtCompact(row.total_views)} views</span>
      </div>`,
    )
    .join("")}</div>`;
}

function tierBars(rows) {
  if (!rows.length) return `<div class="empty-state">沒有留言者層級資料</div>`;
  return `<div class="tier-list">${rows
    .map((row) => {
      const pct = Number(row.pct_commenters || 0);
      return `
        <div class="tier-row">
          <strong>${escapeHtml(tierLabel(row.activity_tier))}</strong>
          <div class="tier-bar"><i style="width:${Math.max(2, Math.min(100, pct))}%"></i></div>
          <span>${fmtNumber(row.n_commenters)} 人 · ${formatValue(row.pct_commenters, "pct")}</span>
        </div>`;
    })
    .join("")}</div>`;
}

function communityBars(rows) {
  if (!rows.length) return `<div class="empty-state">沒有社群資料</div>`;
  return `<div class="community-grid">${rows
    .slice(0, 8)
    .map(
      (row) => `
      <div class="community-cell">
        <strong>社群 ${escapeHtml(row.community)}</strong>
        <span>${fmtNumber(row.n_nodes)} 人</span>
        <div class="community-bar"><i style="width:${Math.max(4, Math.min(100, Number(row.pct_nodes || 0)))}%"></i></div>
        <em>${formatValue(row.pct_nodes, "pct_nodes")}</em>
      </div>`,
    )
    .join("")}</div>`;
}

function sentimentStack(rows) {
  if (!rows.length) return `<div class="empty-state">沒有情緒資料</div>`;
  const order = ["positive", "neutral", "negative"];
  const byLabel = Object.fromEntries(rows.map((row) => [row.sentiment_label, row]));
  return `
    <div class="sentiment-stack">
      ${order
        .map((label) => {
          const row = byLabel[label] || {};
          const pct = Number(row.pct_comments || 0) * 100;
          return `<i class="${label}" style="width:${pct}%"><span>${sentimentLabel(label)} ${pct.toFixed(1)}%</span></i>`;
        })
        .join("")}
    </div>
    <div class="sentiment-detail">${order
      .map((label) => {
        const row = byLabel[label] || {};
        return `<div><strong>${sentimentLabel(label)}</strong><span>${fmtCompact(row.n_comments)} 留言 · 按讚加權 ${formatValue(row.like_weighted_share, "rate")}</span></div>`;
      })
      .join("")}</div>
  `;
}

function keyValueGrid(obj) {
  const keys = Object.keys(obj || {}).filter((key) => obj[key] !== null && obj[key] !== undefined).slice(0, 10);
  if (!keys.length) return `<div class="empty-state">沒有摘要資料</div>`;
  return `<div class="kv-grid">${keys
    .map((key) => `<div><span>${escapeHtml(readableKey(key))}</span><strong>${escapeHtml(formatValue(obj[key], key))}</strong></div>`)
    .join("")}</div>`;
}

function leaderboard(board) {
  return `
    <div class="leaderboard">
      <h4>${escapeHtml(board.title || board.label)}</h4>
      ${(board.top || [])
        .slice(0, 4)
        .map(
          (row, idx) => `
          <div>
            <span>${idx + 1}</span>
            <strong>${escapeHtml(row.channel)}</strong>
            <em>${formatValue(row.value, board.metric)}</em>
          </div>`,
        )
        .join("")}
    </div>`;
}

function artifactList() {
  const tables = currentChannel.artifacts?.tables || [];
  return `<div class="artifact-list">${tables
    .filter((table) => !["qwen_comment_sentiment", "commenter_activity", "actor_communities"].includes(table.name))
    .slice(0, 18)
    .map((table) => `<div><strong>${escapeHtml(table.name)}</strong><span>${fmtCompact(table.bytes)} bytes</span></div>`)
    .join("")}</div>`;
}

async function getVideoRows() {
  if (videoRowsCache) return videoRowsCache;
  try {
    const data = await fetchJson(`/api/table/${encodeURIComponent(currentChannel.slug)}/video_metrics?limit=220`);
    videoRowsCache = data.rows || [];
  } catch {
    videoRowsCache = [];
  }
  return videoRowsCache;
}

async function safeFetchReport() {
  try {
    const data = await fetchJson(`/api/report/${encodeURIComponent(currentChannel.slug)}?lang=zh`);
    return data.text || "";
  } catch {
    return "";
  }
}

function tableFromRows(rows, columns) {
  if (!rows?.length) return `<div class="empty-state">沒有資料</div>`;
  return `<div class="table-wrap"><table><thead><tr>${columns
    .map((col) => `<th>${escapeHtml(readableKey(col))}</th>`)
    .join("")}</tr></thead><tbody>${rows
    .slice(0, 12)
    .map((row) => `<tr>${columns.map((col) => `<td>${escapeHtml(formatValue(row[col], col))}</td>`).join("")}</tr>`)
    .join("")}</tbody></table></div>`;
}

function lensById(id) {
  return (currentChannel.analysis?.lenses || []).find((lens) => lens.id === id);
}

function metricLabel(metric) {
  return indexData.dashboard_statistics?.metric_labels?.[metric] || metric;
}

function sortRows(rows, key) {
  return rows.slice().sort((a, b) => Number(b[key] || 0) - Number(a[key] || 0));
}

function scalePlot(value) {
  return Math.max(5, Math.min(95, Number(value || 0)));
}

function scorePct(value) {
  return Math.max(0, Math.min(100, Number(value || 0)));
}

function pos(value, min, max) {
  const v = Number(value);
  if (!Number.isFinite(v) || !Number.isFinite(min) || !Number.isFinite(max) || max <= min) return 50;
  return Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
}

function fmtNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return new Intl.NumberFormat("zh-Hant").format(Math.round(n));
}

function fmtCompact(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return new Intl.NumberFormat("zh-Hant", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

function fmtScore(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(1);
}

function fmtPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  const pct = Math.abs(n) <= 1 ? n * 100 : n;
  return `${pct.toFixed(1)}%`;
}

function formatValue(value, key = "") {
  if (value === null || value === undefined || value === "") return "-";
  if (String(key).includes("published")) return compactDate(value);
  const n = Number(value);
  if (isRateLike(key)) return fmtPct(value);
  if (!Number.isFinite(n)) return String(value);
  if (Math.abs(n) >= 1000) return fmtCompact(n);
  if (Number.isInteger(n)) return fmtNumber(n);
  return n.toFixed(2);
}

function isRateLike(key) {
  return ["rate", "share", "density", "modularity", "pct"].some((part) => String(key).includes(part));
}

function compactDate(value) {
  if (!value) return "-";
  return String(value).slice(0, 10);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function readableKey(key) {
  const map = {
    title: "影片標題",
    published_at: "發布日",
    view_count: "觀看",
    comment_count: "留言",
    observed_comments: "觀測留言",
    observed_commenters: "留言者",
    negative_rate: "負面率",
    like_weighted_negative_rate: "按讚加權負面",
    primary_theme: "主題",
    conflict_score: "衝突分數",
    reply_count_weighted_conflict_score: "回覆量加權",
    like_weighted_conflict_score: "按讚加權",
  };
  return map[key] || String(key || "").replaceAll("_", " ");
}

function themeLabel(value) {
  const map = {
    controversy_response: "爭議回應",
    personal_team_life: "個人/團隊生活",
    travel_exploration: "旅遊探索",
    food_culture: "飲食文化",
    business_brand: "商業/品牌",
    education_advice: "教育/建議",
    automotive_luxury: "車與生活風格",
    other: "其他",
  };
  return map[value] || String(value || "未標註");
}

function tierLabel(value) {
  return { high: "高頻核心", mid: "中頻觀眾", low: "低頻/一次性" }[value] || value;
}

function sentimentLabel(value) {
  return { positive: "正面", neutral: "中性", negative: "負面" }[value] || value;
}

function kindLabel(value) {
  return { risk: "風險", opportunity: "機會", watch: "觀察", context: "脈絡" }[value] || "訊號";
}

function infoTip(text) {
  const body = String(text || "").trim();
  if (!body) return "";
  return `<span class="info-tip" tabindex="0" aria-label="${escapeHtml(body)}">?<span class="tip-box">${escapeHtml(body).replaceAll("\n", "<br>")}</span></span>`;
}

function scoreline(indices) {
  return indices
    .slice(0, 6)
    .map((item) => `<span>${escapeHtml(item.short_label || item.label)} <strong>${fmtScore(item.score)}</strong></span>`)
    .join("");
}

init().catch((err) => {
  document.body.innerHTML = `<main class="fatal"><h1>Dashboard failed</h1><pre>${escapeHtml(err.stack || err.message || err)}</pre></main>`;
});
