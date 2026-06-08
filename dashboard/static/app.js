let indexData = null;
let currentChannel = null;
let currentPage = "overview";
let videoRowsCache = null;

const pages = [
  { id: "overview", label: "總覽" },
  { id: "content", label: "內容" },
  { id: "audience", label: "觀眾" },
  { id: "sentiment", label: "情緒/衝突" },
  { id: "external_events", label: "外部討論" },
  { id: "strategy", label: "策略輸出" },
];

const selectedMetrics = [
  "comments_per_1k_views",
  "high_mid_tier_commenter_share",
  "continuity_return_rate_w4",
  "one_time_tier_commenter_share",
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
  setupChartTooltip();
  $("search").addEventListener("input", renderChannelList);
  $("subscriber-filter").addEventListener("change", renderChannelList);
  $("back-to-directory").addEventListener("click", showDirectory);
  renderGlobalStats();
  renderChannelList();
  const slugFromHash = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  if (slugFromHash) {
    const match = (indexData.examples || []).find((item) => item.slug === slugFromHash);
    if (match) await loadChannel(match.slug);
  }
}

function renderGlobalStats() {
  const stats = indexData.dashboard_statistics || {};
  const totals = stats.totals || {};
  $("global-stats").innerHTML = `
    <div><span>完成案例</span><strong>${fmtNumber(indexData.n_examples)}</strong></div>
    <div><span>比較頻道</span><strong>${fmtNumber(indexData.baseline?.cohort_n_ready)}</strong></div>
    <div><span>分析影片</span><strong>${fmtNumber(totals.videos)}</strong></div>
    <div><span>主留言數</span><strong>${fmtCompact(totals.comments)}</strong></div>
  `;
}

function filteredExamples() {
  const query = $("search").value.trim().toLowerCase();
  const minSubs = Number($("subscriber-filter").value || 0);
  const rows = (indexData.examples || []).filter((item) => {
    const text = `${item.title || ""} ${item.slug || ""} ${item.archetype || ""}`.toLowerCase();
    return (!query || text.includes(query)) && Number(item.subscriber_count || 0) >= minSubs;
  });
  return orderExamples(rows);
}

function demoTargetSlug() {
  return indexData?.demo_target_slug || "dodomen-generic-demo";
}

function orderExamples(rows) {
  return rows.slice().sort((a, b) => {
    const subDiff = Number(b.subscriber_count || 0) - Number(a.subscriber_count || 0);
    if (subDiff) return subDiff;
    return String(a.title || a.slug).localeCompare(String(b.title || b.slug), "zh-Hant");
  });
}

function renderChannelList() {
  const rows = filteredExamples();
  if (!rows.length) {
    $("examples").innerHTML = `<div class="empty-state">沒有符合條件的完成案例</div>`;
    return;
  }
  $("examples").innerHTML = `
    <div class="case-table-head">
      <span>頻道</span>
      <span>等級</span>
      <span>訂閱</span>
      <span>分析影片</span>
      <span>主留言</span>
      <span>負面率</span>
    </div>
    ${rows.map(caseRow).join("")}
  `;
  $("examples").querySelectorAll(".case-row").forEach((button) => {
    button.addEventListener("click", () => loadChannel(button.dataset.slug));
  });
}

function caseRow(item) {
  const grade = channelCommunityGrade({
    negative_rate: item.negative_rate,
    reply_overview: { max_video_like_weighted_conflict_score: item.baseline_metrics?.max_video_like_weighted_conflict_score },
  });
  return `
    <button class="case-row" data-slug="${escapeHtml(item.slug)}">
      <span class="case-channel">
        <strong>${escapeHtml(item.title || item.slug)}</strong>
      </span>
      <span class="case-grade">${escapeHtml(grade.grade)}</span>
      <span>${fmtCompact(item.subscriber_count)}</span>
      <span>${fmtNumber(item.n_videos_in_scope)}</span>
      <span>${fmtCompact(item.n_comments_in_scope)}</span>
      <span>${formatValue(item.negative_rate, "rate")}</span>
    </button>
  `;
}

async function loadChannel(slug) {
  currentChannel = await fetchJson(`/api/channels/${encodeURIComponent(slug)}`);
  currentPage = "overview";
  videoRowsCache = null;
  location.hash = currentChannel.slug;
  $("directory-page").hidden = true;
  $("analysis-page").hidden = false;
  renderShell();
  await renderPage();
}

function showDirectory() {
  currentChannel = null;
  currentPage = "overview";
  videoRowsCache = null;
  history.pushState("", document.title, location.pathname);
  $("analysis-page").hidden = true;
  $("directory-page").hidden = false;
  renderChannelList();
}

function renderShell() {
  const ch = currentChannel.channel || {};
  $("channel-title").textContent = currentChannel.title || currentChannel.slug;
  $("channel-meta").textContent = [
    `${fmtCompact(ch.subscriber_count)} 訂閱`,
    `${fmtNumber(ch.n_videos_in_scope)} 支影片`,
    `${fmtCompact(ch.n_comments_in_scope)} 則主留言`,
  ]
    .filter(Boolean)
    .join(" · ");
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
  if (currentPage === "overview") await renderOverview(root);
  else if (currentPage === "content") await renderContent(root);
  else if (currentPage === "audience") await renderAudience(root);
  else if (currentPage === "sentiment") await renderSentiment(root);
  else if (currentPage === "external_events") await renderExternalEvents(root);
  else if (currentPage === "strategy") await renderStrategy(root);
}

async function renderOverview(root) {
  const ch = currentChannel.channel || {};
  const overview = currentChannel.overview || {};
  const s = currentChannel.dashboard_summary || {};
  root.innerHTML = `
    ${sectionIntro("總覽")}
    ${channelReportCard(ch, overview, s)}

    <section class="panel">
      <div class="panel-head"><div><h3>互動概況 ${infoTip("分析範圍影片的互動比率。算法：每千次觀看留言數＝總留言數 ÷ 總觀看數 ×1000；讚/觀看＝總按讚數 ÷ 總觀看數；每留言獲讚＝總留言讚數 ÷ 留言數。各條都對照 cohort（基準線＝平均、PR＝相對位置）。只反映留言/按讚行為，留言者僅是觀看者的一小部分，不能視為全體觀眾。")}</h3></div></div>
      ${overviewEngagementBars(s)}
    </section>
  `;
}

function renderBenchmark(root) {
  const metrics = currentChannel.baseline?.all_metrics || [];
  const metricMap = Object.fromEntries(metrics.map((item) => [item.metric, item]));
  const caution = currentChannel.baseline?.comparison_caution_zh || indexData.demo_focus?.comparison_caution_zh || "";
  root.innerHTML = `
    <section class="benchmark-warning">
      <div>
        <h3>比較基準範圍</h3>
        <p>${escapeHtml(caution || "目前使用完成案例建立參考分布，尚未限制為同題材頻道。")}</p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <h3>關鍵指標分布 ${infoTip("把本頻道的關鍵指標放進 48 個 benchmark 頻道的分布。算法：橫條為 cohort 的常見範圍（IQR，中間 50% 落點），中線＝cohort 平均，標記＝本頻道目前值。cohort 僅 48 個頻道故以平均為基準；百分位只代表相對位置，不代表好壞。")}</h3>
        </div>
        <small>顯示平均 / 常見範圍 / 目前頻道</small>
      </div>
      <div class="bullet-list">
        ${selectedMetrics.map((metric) => bulletMetric(metricMap[metric])).join("")}
      </div>
    </section>
  `;
}

async function renderContent(root) {
  const s = currentChannel.dashboard_summary || {};
  const videos = await getVideoRows();
  const hotspots = await fetchTableRows("sentiment_hotspots", 400);
  const negMap = Object.fromEntries((hotspots || []).map((row) => [row.video_id, Number(row.negative_rate)]));
  const extWindows = tabAvailable("external_events") ? await fetchTableRows("external_event_audience_windows", 80) : [];
  const timelineEvents = (extWindows || [])
    .map((row) => ({
      t: Date.parse(row.event_date || row.event_start || ""),
      topic: externalTopicLabel(row.event_topic || "外部討論"),
      date: compactDate(row.event_date || row.event_start),
      posts: Number(row.external_posts) || 0,
    }))
    .filter((event) => Number.isFinite(event.t));
  const themeSummary = await fetchTableRows("theme_summary", 20);
  const sentTheme = await fetchTableRows("sentiment_theme_summary", 20);
  const conflictTheme = await fetchTableRows("reply_conflict_theme_summary", 20);
  const videoThemes = await fetchTableRows("qwen_video_themes", 2000);
  const themeViews = {};
  (videoThemes || []).forEach((row) => {
    if (row.primary_theme) themeViews[row.primary_theme] = (themeViews[row.primary_theme] || 0) + (Number(row.view_count) || 0);
  });
  root.innerHTML = `
    ${sectionIntro("內容")}
    <section class="panel">
      <div class="panel-head"><div><h3>題材一覽 ${infoTip("一張表把每個題材的『互動密度、情緒、衝突』一次看完，不用跨頁。題材由 Qwen 依影片標題/描述/標籤分類。算法：留言/千觀看＝該題材所有影片的留言則數 ÷ 觀看數 ×1000（已對觀看正規化，比『留言量』更能看出哪種題材真的引發互動，不會只因為片多/觀看高就大）；正/負面率＝該題材該情緒則數÷留言則數；衝突分數＝衝突討論串數 × 回覆衝突串比例（回覆結構，與負面率不同）。游標停在數字可看原始留言/觀看。")}</h3></div></div>
      ${themeOverview(themeSummary, sentTheme, conflictTheme, themeViews)}
    </section>
    <section class="panel">
      <div class="panel-head"><div><h3>近期影片時間軸 ${infoTip("一條時間軸同時看四件事：每支影片的留言數（左軸長條，長條顏色＝該片負面率，越紅越負面）、累積觀看數（右軸折線·對數）、外部討論事件（垂直線）。算法：X 軸為影片發布日；留言數＝爬取到的該片留言數；負面率＝該片負面留言÷留言數；外部事件取自外部討論分析。累積觀看為累積值，不能解讀成流量上升或下降。")}</h3></div></div>
      ${videoTimeline(videos, negMap, timelineEvents)}
    </section>
    <section class="panel">
      <div class="panel-head"><div><h3>留言率最高的影片 ${infoTip("以每千次觀看留言數（留言數 ÷ 觀看次數 × 1000）排序，找出最能引發討論的影片。高留言率可能來自高互動或高爭議，需搭配情緒頁判讀。")}</h3></div></div>
      ${videoEngagementTable(videos)}
    </section>
    <section class="panel">
      <div class="panel-head"><div><h3>觀看數 vs 按讚數 ${infoTip("每個點是一支影片：X 軸＝累積觀看數、Y 軸＝累積按讚數（軸為對數，跨數量級才看得清）。算法／怎麼看：點落在同一條斜線上代表『讚/觀看比＝按讚數 ÷ 觀看數』相近；落在多數點上方＝該片按讚轉換特別好(同樣觀看拿到更多讚)，下方＝偏低；離群在右下＝高觀看但讚偏少。用來找按讚轉換的高/低標影片。皆為累積值，不代表流量趨勢；讚是匿名的、只反映有按讚的人。")}</h3></div></div>
      ${likesViewsPanel(videos)}
    </section>
  `;
}

async function renderAudience(root) {
  const s = currentChannel.dashboard_summary || {};
  const profiles = s.audience_segment_profiles || s.community_profiles || [];
  const communityName = {};
  profiles.forEach((profile, idx) => {
    communityName[String(profile.community)] = personaDisplayName(profile, idx);
  });
  const ctSentiment = await fetchTableRows("community_theme_sentiment", 60);
  root.innerHTML = `
    ${sectionIntro("觀眾")}
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><h3>觀眾活躍度 ${infoTip("依每位留言者的『涵蓋率』＝留言過的不重複影片數 ÷ 頻道影片數分層（跨頻道可比、對頻道大小正規化）：一次性/路過＝只留言 1 支；回訪＝≥2 支但涵蓋率<2%；常客＝涵蓋率 2–5%；核心＝涵蓋率≥5% 且至少 3 支。門檻用 48 個 benchmark 頻道分布校準（5%≈p97、2%≈p90）。各層『占比』＝該層人數 ÷ 全部留言者；『活躍 X 次/人』＝該層平均留言則數；綠條長度＝該層占全部留言者的絕對比例。僅統計有留言者、只用主留言。")}</h3></div></div>
        ${tierComparisonBars(s.commenter_tiers || [])}
      </article>
      <article class="panel">
        <div class="panel-head"><div><h3>回訪與核心觀眾 ${infoTip("兩種回訪率都在問『留言者會不會回來再留言』，差別只在時間範圍：\n• 跨影片回訪率（全期）：把『整個頻道歷史』依時間切成每 4 支影片一窗，算「某窗留言者中有多少在下一窗仍留言」，對所有窗加權平均 → 長期、整體的跨影片黏著。\n• 近期回訪率（最新窗）：同樣算法但用滾動窗、『只取最新一段』 → 反映最近的黏著趨勢，可能比全期高或低（看近期內容）。\n核心觀眾占比＝(核心+常客層人數) ÷ 全部留言者。三者一起對照 benchmark cohort，基準線顯示 cohort 平均；百分位只代表相對位置，不代表好壞。（是影片窗、不是 4 週）")}</h3></div></div>
        ${audienceBaselineBars()}
      </article>
    </section>
    <section class="panel">
      <div class="panel-head"><div><h3>觀眾類型與策略用途 ${infoTip("由「在同一支影片共同留言」建立留言者-留言者網路（邊＝共同參與影片數），再用社群偵測（Louvain/Leiden）自動分群，群數由圖結構推得而非預設。算法：觀眾集中度 HHI＝各社群占比的平方和（越接近 1 越集中於少數群）；分群清晰度 modularity＝社群內部連結相對隨機網路超出的程度（越高分群越清楚）。modularity 介於 0~1，慣例 0.3–0.7 才算有明顯結構；但『單一頻道的共同留言網路』因為觀眾天生重疊，數值普遍偏低（本 cohort 中位數約 0.22），所以這裡的高/中/低是『相對同行』而非『絕對乾淨的分割』；題材 affinity lift＝該群在某題材的留言占比 ÷ 全頻道該題材占比（>1＝該群對此題材特別投入）；社群情緒由 Qwen 對該群留言三元分類(用『則數』算、純歸屬作者群)。每張卡片＝一個社群。注意：YouTube 只給留言的讚數、不給『誰按的』，所以任何按讚加權指標反映的是廣大觀眾(可能跨群、甚至純看客)的放大，不等於該社群自己的認同。社群是共同參與結構，不是粉絲派系。")}</h3></div></div>
      ${audienceStructureCards(s.network_summary || {})}
      ${communityPersonaCards(s.community_profiles || [])}
    </section>
    <section class="panel">
      <div class="panel-head"><div><h3>同題材、不同社群：誰對哪類內容特別容易負面 ${infoTip("回答初衷『不同觀眾群在意的點是否不同』，但用『控制題材』的正確做法：不是看各群整體的面向（那會被各群看不同題材決定、是循環），而是『同一個題材內、比較不同社群的負面率』——三群可能都看某題材，但只有某群特別罵它。算法：取三群都有 ≥150 留言的題材，比各群在該題材的負面率（負面則數÷留言則數，純歸屬作者群），只列各群差距 ≥3pp（真的有差）的題材，依差距大小排序。差距小的題材代表大家反應一致、不顯示。")}</h3></div></div>
      ${communityThemeContrast(ctSentiment, communityName)}
    </section>
  `;
}

function communityThemeContrast(ctRows, communityName) {
  const MIN_N = 150;
  const MIN_SPREAD = 0.03;
  const byTheme = {};
  (ctRows || []).forEach((row) => {
    const n = Number(row.n_comments) || 0;
    if (n < MIN_N || !row.primary_theme || row.primary_theme === "other") return;
    (byTheme[row.primary_theme] ||= []).push({
      community: String(row.community),
      neg: Number(row.negative_rate) || 0,
      n,
    });
  });
  const themes = Object.entries(byTheme)
    .filter(([, arr]) => arr.length >= 2)
    .map(([theme, arr]) => {
      const sorted = arr.sort((a, b) => b.neg - a.neg);
      return { theme, arr: sorted, spread: sorted[0].neg - sorted[sorted.length - 1].neg };
    })
    .filter((item) => item.spread >= MIN_SPREAD)
    .sort((a, b) => b.spread - a.spread)
    .slice(0, 6);
  if (!themes.length) return `<div class="empty-state">各社群對相同題材的負面反應沒有明顯差異（代表大家反應一致）。</div>`;
  const maxNeg = Math.max(...themes.flatMap((item) => item.arr.map((row) => row.neg)), 0.01);
  return `<div class="ctc-list">${themes
    .map((item) => {
      const top = item.arr[0];
      return `
        <div class="ctc-row">
          <div class="ctc-head">
            <strong>${escapeHtml(themeLabel(item.theme))}</strong>
            <span>最易負面：${escapeHtml(communityName[top.community] || `社群 ${top.community}`)}（群間差距 ${(item.spread * 100).toFixed(0)}pp）</span>
          </div>
          ${item.arr
            .map(
              (row) => `
            <div class="ctc-bar-row">
              <span class="ctc-name">${escapeHtml(communityName[row.community] || `社群 ${row.community}`)}</span>
              <div class="ctc-track"><i class="${row === top ? "hi" : ""}" style="width:${Math.max(3, (row.neg / maxNeg) * 100).toFixed(0)}%"></i></div>
              <span class="ctc-val">${formatValue(row.neg, "rate")} · ${fmtCompact(row.n)}</span>
            </div>`,
            )
            .join("")}
        </div>`;
    })
    .join("")}</div>`;
}

function communityThemeRisk(ctRows, affRows, communityName) {
  const aff = {};
  (affRows || []).forEach((row) => {
    aff[`${row.community}|${row.theme_label}`] = Number(row.lift);
  });
  const rows = (ctRows || [])
    .filter((row) => Number(row.n_comments) >= 200 && row.primary_theme && row.primary_theme !== "other")
    .map((row) => ({
      community: String(row.community),
      theme: row.primary_theme,
      neg: Number(row.negative_rate || 0),
      likeNeg: Number(row.like_weighted_negative_rate || 0),
      n: Number(row.n_comments) || 0,
      lift: Number(aff[`${row.community}|${row.primary_theme}`]),
    }))
    .sort((a, b) => b.neg - a.neg)
    .slice(0, 8);
  if (!rows.length) return `<div class="empty-state">資料不足以判斷社群×題材風險。</div>`;
  const max = Math.max(...rows.map((row) => row.neg), 0.01);
  return `<div class="insight-list">${rows
    .map(
      (row) => `
      <div class="insight-row">
        <div class="insight-label">
          <strong>${escapeHtml(communityName[row.community] || `社群 ${row.community}`)} · ${escapeHtml(themeLabel(row.theme))}</strong>
          <span>${fmtCompact(row.n)} 留言${Number.isFinite(row.lift) ? ` · 投入 ${row.lift.toFixed(2)}×` : ""} · 按讚加權 ${formatValue(row.likeNeg, "rate")}（放大·讚來源不明）</span>
        </div>
        <div class="risk-track"><i style="width:${Math.max(3, (row.neg / max) * 100).toFixed(0)}%"></i></div>
        <div class="insight-value">${formatValue(row.neg, "rate")}</div>
      </div>`,
    )
    .join("")}</div>`;
}

async function renderSentiment(root) {
  const s = currentChannel.dashboard_summary || {};
  const themeSentiment = await fetchTableRows("sentiment_theme_summary", 20);
  const videoSentiment = await fetchTableRows("sentiment_hotspots", 400);
  const aspectSummary = await fetchTableRows("comment_aspect_summary", 20);
  const videoAspects = await fetchTableRows("video_aspect_summary", 3000);
  const videoPosAspects = await fetchTableRows("video_positive_aspect_summary", 3000);
  const videoPosAspectMap = buildVideoAspectMap(videoPosAspects);
  const channelPosAspect = await fetchTableRows("channel_positive_aspect_summary", 20);
  const aspectLabels = Object.fromEntries(
    (aspectSummary || []).filter((row) => row.aspect).map((row) => [row.aspect, row.aspect_label_zh || row.aspect]),
  );
  const videoAspectMap = buildVideoAspectMap(videoAspects);
  const replySentiment = await fetchTableRows("reply_sentiment_summary", 12);
  const themeConflict = await fetchTableRows("reply_conflict_theme_summary", 12);
  root.innerHTML = `
    ${sectionIntro("情緒風險")}
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><h3>正面、中性、負面留言比例 ${infoTip("全頻道留言的三元情緒占比，由 Qwen 逐則分類為正/中/負。算法：各情緒占比＝該情緒則數 ÷ 全部留言則數；按讚加權版＝Σ(該情緒留言×(讚+1)) ÷ Σ(全部留言×(讚+1))，被按讚多的留言權重更高。包含回覆，反映留言者語氣，不代表所有觀看者。")}</h3></div></div>
        ${sentimentStack(s.sentiment_summary || [])}
      </article>
      <article class="panel">
        <div class="panel-head"><div><h3>相對基準 ${infoTip("把本頻道的情緒率放進 48 個 benchmark 頻道的分布。算法：百分位＝本頻道值在 cohort 由小到大的排名位置(0–100)；基準線顯示的是 cohort『平均』(因只有 48 個頻道)。百分位僅代表相對定位，不直接等於好或壞。")}</h3></div></div>
        ${sentimentBaselineBars()}
      </article>
    </section>
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><h3>整體被讚的面向 ${infoTip("ABSA 對全頻道『正面』留言抽取面向後的分佈：觀眾整體是『因為什麼』而正面（主持人、內容品質、剪輯等通用 taxonomy）。算法：各面向正面提及數 ÷ 全部正面提及；已扣除 other／unclear。為模型標註、非人工真值。")}</h3></div></div>
        ${channelAspectBars(channelPosAspect, "positive_aspect_share", aspectLabels, "pos")}
      </article>
      <article class="panel">
        <div class="panel-head"><div><h3>整體被罵的面向 ${infoTip("ABSA 對全頻道『負面』留言抽取面向後的分佈：觀眾整體是『因為什麼』而負面。算法：各面向負面提及數 ÷ 全部負面提及；已扣除 other／unclear。為模型標註、非人工真值。")}</h3></div></div>
        ${channelAspectBars(aspectSummary, "negative_aspect_share", aspectLabels, "neg")}
      </article>
    </section>
    <section class="panel sentiment-band sentiment-band-positive">
      <div class="panel-head"><div><h3>正面亮點 ${infoTip("以正面留言率排序的影片與題材。算法：正面留言率＝該片(或該主題)正面則數 ÷ 其留言則數；影片/題材情緒使用全部留言（含回覆）。")}</h3></div></div>
      <div class="sentiment-band-grid">
        <div class="sentiment-subpanel">
          <h4>高正面影片 ${infoTip("正面留言率最高的影片（正面留言數 ÷ 該片留言數），並列出該片『被稱讚的點』（ABSA 對正面留言抽取面向，占該片正面留言比例，扣除 other／unclear）。為模型標註，非人工真值。")}</h4>
          ${positiveVideoCards(videoSentiment, videoPosAspectMap, aspectLabels)}
        </div>
        <div class="sentiment-subpanel">
          <h4>高正面題材 ${infoTip("各 Qwen 主題的正面留言率排序。算法：該主題正面則數 ÷ 該主題留言則數（含回覆）；按讚加權版以(讚+1)加權。主題由 Qwen 對影片標題/描述/標籤分類。")}</h4>
          ${positiveThemeBars(themeSentiment)}
        </div>
      </div>
    </section>
    <section class="panel sentiment-band sentiment-band-negative">
      <div class="panel-head"><div><h3>負面風險 ${infoTip("以負面率與按讚加權負面率的放大程度找出風險點。算法：負面率＝負面則數÷留言則數；按讚加權負面＝Σ(負面×(讚+1))÷Σ(全部×(讚+1))，若大於負面率代表負面被按讚放大。情緒為模型標註，非人工真值。")}</h3></div></div>
      <div class="sentiment-band-grid">
        <div class="sentiment-subpanel">
          <h4>高負面影片與負面原因 ${infoTip("排序依『實質負面』＝按讚加權負面率 × 實質負面占比（ABSA 面向中扣除 other／unclear 這類雖負面但對頻道無實質影響的部分），所以排前面的是真的被罵到痛點、不是雜訊。每片並列出主要負面面向（占該片負面留言比例）。為模型標註，非人工真值。")}</h4>
          ${riskVideoCards(s.negative_hotspots || [], videoAspectMap, aspectLabels)}
        </div>
        <div class="sentiment-subpanel">
          <h4>高負面題材 ${infoTip("各 Qwen 主題的負面留言率排序。算法：該主題負面則數 ÷ 該主題留言則數（含回覆）；按讚加權版以(讚+1)加權。主題由 Qwen 對影片標題/描述/標籤分類。")}</h4>
          ${themeRiskBars(themeSentiment)}
        </div>
      </div>
    </section>
    <section class="section-intro compact">
      <h3>回覆衝突 ${infoTip("和『情緒』不同：情緒看每則留言語氣（正/負），衝突看『回覆串的對立結構』。一個 thread＝一則主留言＋它的回覆。三種型態（算法）：\n• 衝突串 conflict_thread＝有回覆，且整串或回覆區『正面率與負面率都 ≥15%』(兩派並存、極化)。\n• 圍剿 pile-on＝回覆 ≥3 則，且回覆負面率 ≥60%、正面率 <15%(一面倒圍攻母留言)。\n• 對立母串 parent-opposition＝回覆和母留言『立場相反』(母正回覆≥25%負／母負回覆≥25%正／母中性則正負都≥15%)。\n負面率低不代表沒衝突，反之亦然。情緒為模型標註，非人工判定吵架。")}</h3>
      <p class="section-why">為什麼看這個：① <b>版務</b>——高衝突影片留言區易變戰場，可考慮置頂澄清、限制回覆、加強管理；② <b>品牌風險</b>——圍剿/對立串容易被截圖、釀公關，是早期預警；③ <b>議題極化</b>——看哪些題材會讓你的觀眾分裂成兩派（而非單純不喜歡）。</p>
    </section>
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><h3>回覆與衝突基準 ${infoTip("把『回覆活躍度與衝突程度』對照 benchmark cohort。算法：回覆占比＝回覆數 ÷ 全部留言數；衝突峰值＝全頻道單支影片最高的(按讚加權)衝突分數。基準線顯示 cohort 平均、PR 為相對位置。衝突來自回覆串結構，與單純負面率是不同概念。")}</h3></div></div>
        ${replyBaselineBars(s.reply_overview || {})}
      </article>
      <article class="panel">
        <div class="panel-head"><div><h3>主留言 vs 回覆 ${infoTip("比較主留言區與回覆區的負面率，看回覆是否比主留言更對立或更負面。算法：各區負面則數 ÷ 各區留言則數。")}</h3></div></div>
        ${replySentimentBars(replySentiment)}
      </article>
    </section>
    <section class="split-layout">
      <article class="panel">
        <div class="panel-head"><div><h3>高衝突影片 ${infoTip("找出『不只是負面多，而是真的吵起來』的影片。依按讚加權衝突分數排序（衝突分數＝衝突串數 × 回覆中衝突串比例，再用回覆讚數加權）。每張卡列三種型態的串數：衝突串(兩派並存)、圍剿(3+回覆一面倒負面攻母留言)、對立母串(回覆反對母留言立場)——有數字>0 會標紅。皆為回覆串結構，不是單純負面率；情緒為模型標註。")}</h3></div></div>
        ${conflictVideoCards(s.reply_conflict_hotspots || [])}
      </article>
      <article class="panel">
        <div class="panel-head"><div><h3>高衝突題材 ${infoTip("看哪些題材『比例上』最容易引發對立討論。算法＝衝突率＝該題材的衝突討論串數 ÷ 有回覆的討論串數（不是衝突『量』，所以大題材不會只因為串多就排前面）。只取有回覆串 ≥20 的題材避免小樣本雜訊。衝突來自回覆串結構（圍剿、對立母串），與單純負面率不同。")}</h3></div></div>
        ${themeConflictBars(themeConflict)}
      </article>
    </section>
  `;
}

async function renderExternalEvents(root) {
  const hasTab = tabAvailable("external_events");
  const audienceWindows = hasTab ? await fetchTableRows("external_event_audience_windows", 80) : [];
  const diagnostics = hasTab ? await fetchTableRows("external_event_impact_diagnostics", 80) : [];
  const diagMap = Object.fromEntries((diagnostics || []).map((row) => [row.event_cluster_id, row]));
  const events = newAudienceRows(audienceWindows, diagMap);
  root.innerHTML = `
    ${sectionIntro("外部討論")}
    ${
      hasTab && events.length
        ? `
          <section class="panel">
            <div class="panel-head"><div><h3>外部討論是否帶來新觀眾 ${infoTip("關鍵不是事件後有沒有新留言者（事件後永遠有），而是事件後的新留言者占比是否『高於頻道平常水準』。每個事件把事件後 28 天窗口的新留言者占比，對照事件前 90 天的長期基準（平常平均）並做顯著性檢定。時間窗關聯非因果；新留言者≠新觀看者。")}</h3></div></div>
            ${newAudienceSummary(events)}
          </section>
          <section class="panel">
            <div class="panel-head"><div><h3>各外部事件：前後多指標是否同步變化 ${infoTip("只要事件後『有顯著偏離平常』就預設顯示：新留言者占比顯著(p<0.05，不論升降)，或留言量/負面率/衝突/外溢等 ≥1 項影響訊號。完全無顯著差距的事件才收起、可展開。排序：反應指標數多者在前，其次依新留言者占比差距。多項一起往同方向動＝該外部討論期間 YouTube 端確實有同步反應。皆為時間窗關聯、非因果。")}</h3></div></div>
            ${newAudienceEventList(events)}
          </section>
          <p class="external-caveat">時間窗關聯非因果；「新留言者」是首次在本頻道留言者，不等於新觀看者。判讀重點是事件後是否『顯著高於平常基準』，不是絕對新留言者數。注意頻道早期長期基準偏高（當時多數留言者本來就是新的），早期事件即使有外部討論，對比基準也常呈現下降；「對比事件前 28 天」可降低此成熟趨勢的影響。</p>
        `
        : `<section class="panel"><div class="empty-state">這個頻道目前沒有外部討論的新觀眾分析資料。</div></section>`
    }
  `;
}

function newAudienceRows(rows, diagMap = {}) {
  return (rows || [])
    .map((row) => {
      const diag = diagMap[row.event_cluster_id] || {};
      return {
        topic: externalTopicLabel(row.event_topic || "外部討論"),
        date: compactDate(row.event_date || row.event_start),
        sources: sourceLabelList(row.sources),
        posts: Number(row.external_posts) || 0,
        titles: String(row.top_titles || ""),
        baselineShare: Number(row.baseline_new_commenter_share),
        postShare: Number(row.post_new_commenter_share),
        deltaPp: Number(row.delta_post_vs_baseline_new_commenter_share_pp),
        pValue: Number(row.post_vs_baseline_new_commenter_share_p),
        preDeltaPp: Number(row.delta_post_vs_pre_new_commenter_share_pp),
        prePValue: Number(row.post_vs_pre_new_commenter_share_p),
        commentShare: Number(row.post_new_commenter_comment_share),
        returnRate: Number(row.post_new_commenter_next_window_return_rate),
        newCommenters: Number(row.post_new_commenters) || 0,
        volumeLift: Number(diag.comment_volume_lift_vs_baseline),
        negDeltaPp: Number(diag.delta_post_vs_baseline_negative_rate_pp),
        negP: Number(diag.post_vs_baseline_negative_rate_p),
        conflictLift: Number(diag.conflict_score_lift_vs_baseline),
        signalCount: Number(diag.diagnostic_signal_count) || 0,
        interpretation: diag.diagnostic_interpretation || "",
      };
    })
    .filter((event) => Number.isFinite(event.postShare) && Number.isFinite(event.baselineShare))
    .sort(
      (a, b) =>
        (b.signalCount || 0) - (a.signalCount || 0) ||
        (Number.isFinite(b.deltaPp) ? b.deltaPp : -Infinity) - (Number.isFinite(a.deltaPp) ? a.deltaPp : -Infinity),
    );
}

function newAudienceSummary(events) {
  const n = events.length;
  const withDelta = events.filter((event) => Number.isFinite(event.deltaPp));
  const sigUp = events.filter((event) => Number(event.deltaPp) > 0 && Number(event.pValue) < 0.05).length;
  const sigDown = events.filter((event) => Number(event.deltaPp) < 0 && Number(event.pValue) < 0.05).length;
  const avgDelta = withDelta.reduce((acc, event) => acc + event.deltaPp, 0) / Math.max(1, withDelta.length);
  let verdict;
  if (sigUp > sigDown && sigUp >= Math.max(2, n * 0.3)) {
    verdict = "整體看，外部討論較常讓新留言者占比顯著高於平常，有帶進新觀眾的傾向。";
  } else if (sigUp === 0) {
    verdict = "整體看，沒有任何事件讓新留言者占比顯著高於平常，目前看不到外部討論帶進高於平常新觀眾的證據。";
  } else {
    verdict = "整體看，只有少數事件讓新留言者占比顯著高於平常；多數變化偏向反映頻道自然成熟（早期基準偏高），而非外部討論帶客效果。";
  }
  const takeaway = `判斷外部討論是否帶來新觀眾，要看事件後新留言者占比是否『高於頻道平常水準』，而不是看絕對人數（事件後一定有新留言者）。這 ${n} 個事件中，${sigUp} 個顯著高於平常、${sigDown} 個顯著低於平常，平均與平常基準差 ${formatValue(avgDelta, "pp")}。${verdict}`;
  return `
    <div class="metric-strip">
      ${metricTile("分析的外部事件", n, "n")}
      ${metricTile("顯著高於平常", `${sigUp} / ${n}`, "text")}
      ${metricTile("顯著低於平常", `${sigDown} / ${n}`, "text")}
      ${metricTile("平均與平常基準差距", avgDelta, "pp")}
    </div>
    <p class="external-takeaway">${escapeHtml(takeaway)}</p>`;
}

function newAudienceEventList(events) {
  // Show by default any event with a *significant* difference from baseline: either
  // the new-commenter share is significant (p<0.05, any direction) or >=1 impact
  // signal fired. Only events with no significant difference at all are collapsed.
  const isSignificant = (event) =>
    Number(event.signalCount) >= 1 || (Number.isFinite(event.pValue) && event.pValue < 0.05);
  const reacted = events.filter(isSignificant);
  const quiet = events.filter((event) => !isSignificant(event));
  const list = (arr) => `<div class="na-event-list">${arr.map(naEventCard).join("")}</div>`;
  return `
    ${
      reacted.length
        ? list(reacted)
        : `<div class="empty-state">這些外部事件後，留言量／負面率／衝突／新觀眾占比都沒有明顯偏離平常。</div>`
    }
    ${
      quiet.length
        ? `<details class="na-quiet"><summary>展開 ${quiet.length} 個與平常無明顯差距的事件</summary>${list(quiet)}</details>`
        : ""
    }
  `;
}

function naEventCard(event) {
  const sig = Number.isFinite(event.pValue) && event.pValue < 0.05;
  const preSig = Number.isFinite(event.prePValue) && event.prePValue < 0.05;
  const extras = [
    Number.isFinite(event.preDeltaPp)
      ? `對比事件前28天 ${formatValue(event.preDeltaPp, "pp")}${preSig ? "（顯著）" : ""}`
      : "",
    Number.isFinite(event.commentShare) ? `新留言者貢獻留言 ${formatValue(event.commentShare, "rate")}` : "",
    Number.isFinite(event.returnRate) ? `新觀眾回訪率 ${formatValue(event.returnRate, "rate")}` : "",
  ].filter(Boolean);
  return `
    <article class="na-event">
      <div class="na-event-head">
        <div class="na-event-title">
          <strong>${escapeHtml(event.topic)}</strong>
          ${event.signalCount ? `<span class="na-signal-badge">${event.signalCount} 項指標反應</span>` : ""}
          ${naDeltaBadge(event.deltaPp, sig)}
        </div>
        <span>${escapeHtml(event.date)} · ${escapeHtml(event.sources || "-")} · ${
          event.titles
            ? `<span class="na-titles" data-chart-tooltip="${tooltipAttr(
                event.titles
                  .split("||")
                  .map((title) => "• " + title.trim())
                  .filter((title) => title.length > 2)
                  .join("\n"),
              )}">${fmtCompact(event.posts)} 篇貼文 ▸</span>`
            : `${fmtCompact(event.posts)} 篇貼文`
        }</span>
      </div>
      ${naCompareBlock(event.baselineShare, event.postShare)}
      ${naSyncBlock(event)}
      ${extras.length ? `<div class="na-extra">${extras.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
    </article>`;
}

function naSyncBlock(event) {
  const items = [];
  if (Number.isFinite(event.volumeLift)) items.push(naSyncMetric("留言量", event.volumeLift, "lift", false));
  if (Number.isFinite(event.negDeltaPp)) {
    items.push(naSyncMetric("負面率", event.negDeltaPp, "pp", true, Number.isFinite(event.negP) && event.negP < 0.05));
  }
  if (Number.isFinite(event.conflictLift)) items.push(naSyncMetric("回覆衝突", event.conflictLift, "lift", true));
  if (Number.isFinite(event.deltaPp)) items.push(naSyncMetric("新留言者占比", event.deltaPp, "pp", false));
  if (!items.length) return "";
  return `<div class="na-sync"><span class="na-sync-label">事件前後變化</span><div class="na-sync-metrics">${items.join("")}</div></div>`;
}

function naSyncMetric(label, value, kind, riskOnUp, sig) {
  const isLift = kind === "lift";
  const up = isLift ? value > 1.15 : value > 2;
  const down = isLift ? value < 0.85 : value < -2;
  const arrow = up ? "▲" : down ? "▼" : "—";
  const text = isLift ? `${value.toFixed(2)}×` : formatValue(value, "pp");
  let cls = "flat";
  if (up || down) cls = riskOnUp ? (up ? "risk" : "calm") : up ? "up" : "down";
  return `<span class="na-sync-metric ${cls}">${escapeHtml(label)} ${arrow} ${escapeHtml(text)}${sig ? " 顯著" : ""}</span>`;
}

function naDeltaBadge(deltaPp, sig) {
  if (!Number.isFinite(Number(deltaPp))) return "";
  const value = Number(deltaPp);
  const cls = !sig ? "flat" : value > 0 ? "up" : value < 0 ? "down" : "flat";
  const arrow = value > 0 ? "▲" : value < 0 ? "▼" : "—";
  const word = value > 0 ? "高於平常" : value < 0 ? "低於平常" : "持平";
  return `<span class="na-delta ${cls}">${arrow} ${escapeHtml(word)} ${formatValue(Math.abs(value), "pp")}${sig ? " · 顯著" : " · 不顯著"}</span>`;
}

function naCompareBlock(baselineShare, postShare) {
  const rows = [
    { label: "平常基準", value: baselineShare, tone: "muted" },
    { label: "事件後", value: postShare, tone: "" },
  ];
  return `<div class="na-compare">${rows
    .map((row) => {
      if (!Number.isFinite(Number(row.value))) return "";
      const width = Math.max(2, Math.min(100, Number(row.value) * 100));
      return `
        <div class="na-cmp-row">
          <span>${row.label}</span>
          <div class="na-bar"><i class="${row.tone}" style="width:${width.toFixed(1)}%"></i></div>
          <strong>${formatValue(row.value, "rate")}</strong>
        </div>`;
    })
    .join("")}</div>`;
}

async function renderStrategy(root) {
  const brief = currentChannel.analysis?.strategy_brief;
  root.innerHTML = `
    ${sectionIntro("策略輸出")}
    ${aiHealthCheckSection(currentChannel.analysis)}
    ${
      brief?.items?.length
        ? strategyBriefSection(brief)
        : `<section class="panel">
            <div class="panel-head"><div><h3>策略決策清單 ${infoTip("由各分析模組（主題、社群、情緒、衝突、外部討論、基準）彙整的可執行建議，每項對應具體數據或表格，仍需人工判斷與驗證。")}</h3></div></div>
            <div class="decision-list">${(currentChannel.analysis?.decision_queue || []).map(decisionRow).join("") || `<div class="empty-state">沒有策略清單資料</div>`}</div>
          </section>`
    }
  `;
}

function aiHealthCheckSection(analysis) {
  const arche = analysis?.archetype;
  const indices = analysis?.indices || [];
  if (!arche && !indices.length) return "";
  return `
    <section class="panel">
      <div class="panel-head"><div><h3>AI 社群健檢 ${infoTip("由分析指標自動彙整的整體判讀（規則式，非逐字 LLM）。算法：archetype 依 6 大指數的高低組合分類；每個指數＝其組成指標的 benchmark 百分位平均(0–100)，risk 類已把負面/衝突 component 反向後再合成。僅相對 48 個 cohort 頻道，不是絕對好壞。游標停在每條看該指數要回答的問題與判讀。")}</h3></div></div>
      ${
        arche
          ? `<div class="health-archetype"><strong>${escapeHtml(arche.label_zh)}</strong><p>${escapeHtml(arche.summary_zh)}</p></div>`
          : ""
      }
      <div class="health-index-list">${indices.map(healthIndexRow).join("")}</div>
    </section>`;
}

function healthIndexRow(idx) {
  const score = Number(idx.score) || 0;
  const risk = idx.polarity === "risk_high";
  const high = score >= 66.7;
  const low = score < 33.3;
  let tone = "mid";
  if (idx.polarity === "mixed_high") tone = "mid";
  else if (risk) tone = high ? "risk" : low ? "good" : "mid";
  else tone = high ? "good" : low ? "warn" : "mid";
  const tip = `${idx.question_zh || ""}\n\n${idx.interpretation_zh || ""}`;
  return `
    <div class="health-index ${tone}" data-chart-tooltip="${tooltipAttr(tip)}">
      <div class="health-index-top">
        <strong>${escapeHtml(idx.label)}</strong>
        <span>${escapeHtml(idx.band || "")} · ${Math.round(score)}/100</span>
      </div>
      <div class="health-bar"><i style="width:${Math.max(2, Math.min(100, score)).toFixed(0)}%"></i></div>
      <p>${escapeHtml(idx.interpretation_zh || "")}</p>
    </div>`;
}

function strategyBriefSection(brief) {
  const items = brief?.items || [];
  if (!items.length) return "";
  return `
    <section class="panel">
      <div class="panel-head"><div><h3>策略總結 ${infoTip(brief.method_note_zh || "每條建議都對應分析產物的具體數據與來源表格；百分位僅代表相對位置，模型標註非人工真值。")}</h3></div></div>
      ${brief.headline_zh ? `<p class="strategy-headline">${escapeHtml(brief.headline_zh)}</p>` : ""}
      ${brief.method_note_zh ? `<p class="strategy-method-note">${escapeHtml(brief.method_note_zh)}</p>` : ""}
    </section>
    <section class="panel">
      <div class="panel-head"><div><h3>逐項策略建議（附數據與來源） ${infoTip("每條建議分為：結論、依據（指數/百分位等具體數據）、資料來源（哪張表或模組）、下一步（可執行）、限制。依據都引用自既有分析產物，非另行推測。")}</h3></div></div>
      <div class="strategy-brief-list">${items.map(strategyBriefCard).join("")}</div>
    </section>`;
}

function strategyBriefCard(item) {
  return `
    <article class="strategy-card ${escapeHtml(item.kind || "context")}">
      <div class="strategy-card-head">
        <span class="strategy-kind">${escapeHtml(kindLabel(item.kind))}</span>
        ${item.module_zh ? `<span class="strategy-module">${escapeHtml(item.module_zh)}</span>` : ""}
      </div>
      <strong class="strategy-title">${escapeHtml(item.title_zh || "")}</strong>
      ${strategyField("依據", item.basis_zh)}
      ${strategyField("資料來源", item.source_zh)}
      ${strategyField("下一步", item.action_zh)}
      ${strategyField("限制", item.caveat_zh)}
    </article>`;
}

function strategyField(label, value) {
  if (!value) return "";
  return `
    <div class="strategy-field">
      <span>${escapeHtml(label)}</span>
      <p>${escapeHtml(value)}</p>
    </div>`;
}

function frameworkCard(kicker, title, metric, question) {
  return `
    <article class="framework-card">
      <span>${escapeHtml(kicker)}</span>
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(metric)}</p>
      <em>${escapeHtml(question)}</em>
    </article>
  `;
}

function sectionIntro(kicker) {
  return `
    <section class="section-intro compact">
      <h3>${escapeHtml(kicker)}</h3>
    </section>
  `;
}

function metricTile(label, value, key) {
  return `
    <article class="metric-tile">
      <span>${escapeHtml(label)}</span>
      <strong>${formatValue(value, key)}</strong>
    </article>
  `;
}

function channelReportCard(channel, overview, summary) {
  const grade = channelCommunityGrade(summary);
  return `
    <section class="channel-report-card">
      <div class="profile-block">
        <div class="avatar-mark">${escapeHtml(initials(currentChannel?.title || currentChannel?.slug || "YT"))}</div>
        <div>
          <span class="report-kicker">YouTube 頻道</span>
          <h3>${escapeHtml(currentChannel?.title || currentChannel?.slug || "-")}</h3>
        </div>
      </div>
      <div class="grade-block">
        <span>社群等級</span>
        <strong>${escapeHtml(grade.grade)}</strong>
        <em>${escapeHtml(grade.label)}</em>
      </div>
      <div class="report-stat-grid">
        ${reportStat("訂閱", channel.subscriber_count ?? overview.subscriber_count, "n")}
        ${reportStat("總觀看", channel.view_count_api ?? overview.channel_view_count_api, "n")}
        ${reportStat("總影片", channel.video_count_api ?? overview.channel_video_count_api, "n")}
        ${reportStat("分析留言", channel.n_comments_in_scope ?? overview.n_comments_in_scope, "n")}
      </div>
    </section>
  `;
}

function reportStat(label, value, key) {
  return `
    <div class="report-stat">
      <span>${escapeHtml(label)}</span>
      <strong>${formatValue(value, key)}</strong>
    </div>
  `;
}

function channelCommunityGrade(summary) {
  const negative = Number(summary.negative_rate);
  const conflict = Number(summary.reply_overview?.max_video_like_weighted_conflict_score);
  let penalty = 0;
  if (Number.isFinite(negative)) penalty += negative * 100;
  if (Number.isFinite(conflict)) penalty += Math.min(30, conflict);
  if (penalty < 9) return { grade: "A", label: "低風險 / 穩定" };
  if (penalty < 16) return { grade: "B", label: "可控 / 需觀察" };
  if (penalty < 25) return { grade: "C", label: "壓力偏高" };
  return { grade: "D", label: "高風險" };
}

function initials(value) {
  const text = String(value || "").trim();
  if (!text) return "YT";
  const letters = Array.from(text.replace(/[^\p{L}\p{N}]/gu, "")).slice(0, 2).join("");
  return letters || "YT";
}

function overviewSnapshotRow(channel, overview) {
  return {
    custom_url: channel.custom_url || channel.channel_id || overview.channel_id,
    country: channel.country || "-",
    crawl_time: channel.crawl_time || "-",
    date_min: channel.date_min || overview.date_min,
    date_max: channel.date_max || overview.date_max,
  };
}

function overviewMetricRows(channel, overview, summary) {
  return [
    ["訂閱數", channel.subscriber_count ?? overview.subscriber_count, "YouTube 頻道公開資料"],
    ["頻道總觀看", channel.view_count_api ?? overview.channel_view_count_api, "YouTube 頻道公開資料"],
    ["頻道總影片", channel.video_count_api ?? overview.channel_video_count_api, "YouTube 頻道公開資料"],
    ["分析範圍影片", channel.n_videos_in_scope ?? overview.n_videos_in_scope, "本次分析資料"],
    ["分析範圍觀看", channel.total_views_in_scope ?? overview.total_views_in_scope, "本次分析資料"],
    ["主留言數（不含回覆）", channel.n_comments_in_scope ?? overview.n_comments_in_scope, "本次分析資料"],
    ["主留言者數（不重複）", channel.n_commenters_in_scope ?? overview.n_commenters_in_scope, "本次分析資料"],
    ["YouTube 顯示留言數", overview.total_video_comment_count_api, "YouTube 影片公開資料"],
    ["負面留言率", formatValue(summary.negative_rate, "rate"), "模型情緒標註"],
    ["正面留言率", formatValue(summary.positive_rate, "rate"), "模型情緒標註"],
    ["按讚加權負面", formatValue(summary.like_weighted_negative_rate, "rate"), "留言按讚 + 模型情緒標註"],
    ["回覆占比", formatValue(summary.reply_overview?.reply_share_all_comments, "rate"), "留言回覆串"],
  ].map(([metric, value, source]) => ({
    metric,
    value: typeof value === "number" ? formatValue(value, "n") : value,
    source,
  }));
}

function overviewEngagementRows(summary) {
  return [
    ["負面留言率", formatValue(summary.negative_rate, "rate"), "模型情緒標註"],
    ["正面留言率", formatValue(summary.positive_rate, "rate"), "模型情緒標註"],
    ["按讚加權負面", formatValue(summary.like_weighted_negative_rate, "rate"), "留言按讚 + 模型情緒標註"],
    ["回覆占比", formatValue(summary.reply_overview?.reply_share_all_comments, "rate"), "留言回覆串"],
  ].map(([metric, value, source]) => ({ metric, value, source }));
}

function overviewEngagementBars(summary) {
  const rows = [
    { label: "留言 / 千次觀看", metric: "comments_per_1k_views", key: "comments_per_1k_views", tone: "good" },
    { label: "正面留言率", metric: "positive_rate", key: "positive_rate", tone: "good", value: summary.positive_rate },
    { label: "負面留言率", metric: "negative_rate", key: "negative_rate", tone: "risk", value: summary.negative_rate },
    {
      label: "按讚加權負面",
      metric: "like_weighted_negative_rate",
      key: "like_weighted_negative_rate",
      tone: "risk",
      value: summary.like_weighted_negative_rate,
    },
    {
      label: "回覆占比",
      metric: "reply_share_all_comments",
      key: "reply_share_all_comments",
      tone: "watch",
      value: summary.reply_overview?.reply_share_all_comments,
    },
  ];
  return `<div class="comparison-bars">${rows.map(comparisonMetricBar).join("")}</div>`;
}

function valuePercentile(dist, x) {
  // Estimate where x falls (0-100) via piecewise-linear interpolation of the
  // cohort distribution breakpoints. Used to place the cohort-mean marker on a
  // percentile-scaled bar so the marker and the displayed mean agree.
  const xv = Number(x);
  if (!Number.isFinite(xv)) return null;
  const pts = [
    [0, dist.min],
    [10, dist.p10],
    [25, dist.p25],
    [50, dist.median],
    [75, dist.p75],
    [90, dist.p90],
    [100, dist.max],
  ].filter(([, v]) => Number.isFinite(Number(v)));
  if (pts.length < 2) return null;
  if (xv <= Number(pts[0][1])) return pts[0][0];
  for (let i = 1; i < pts.length; i += 1) {
    const [p0, v0] = pts[i - 1];
    const [p1, v1] = pts[i];
    if (xv <= Number(v1)) {
      const span = Number(v1) - Number(v0);
      const frac = span > 0 ? (xv - Number(v0)) / span : 0;
      return p0 + frac * (p1 - p0);
    }
  }
  return 100;
}

function comparisonMetricBar(row) {
  const metric = baselineMetric(row.metric);
  const value = row.value ?? metric?.value;
  const dist = metric?.distribution || {};
  const mean = dist.mean;
  const percentile = Number(metric?.percentile);
  const hasPercentile = Number.isFinite(percentile);
  const max = comparisonScaleMax(value, mean, dist.p75, dist.max);
  const valuePct = hasPercentile ? Math.max(0, Math.min(100, percentile)) : pos(value, 0, max);
  const meanPct = hasPercentile
    ? Math.max(0, Math.min(100, valuePercentile(dist, mean) ?? 50))
    : pos(mean, 0, max);
  return `
    <div class="comparison-row ${escapeHtml(row.tone || "neutral")}">
      <div class="comparison-label">
        <strong>${escapeHtml(row.label)}</strong>
        <span>基準平均 ${formatValue(mean, row.key)}</span>
      </div>
      <div class="comparison-track ${hasPercentile ? "percentile-track" : ""}">
        ${hasPercentile ? `<i class="iqr"></i><i class="marker" style="left:${valuePct}%"></i>` : `<i class="value" style="width:${valuePct}%"></i>`}
        <i class="median" style="left:${meanPct}%"></i>
      </div>
      <div class="comparison-value">
        <strong>${formatValue(value, row.key)}</strong>
        ${hasPercentile ? `<span>百分位 ${fmtScore(percentile)}</span>` : ""}
      </div>
    </div>
  `;
}

function baselineMetric(name) {
  return (currentChannel.baseline?.all_metrics || []).find((item) => item.metric === name);
}

function comparisonScaleMax(...values) {
  const nums = values.map(Number).filter((n) => Number.isFinite(n) && n > 0);
  if (!nums.length) return 1;
  const max = Math.max(...nums);
  return max * 1.15;
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
      <span>${kindLabel(card.kind)} ${infoTip(localizeDisplayText(`${card.body_zh || ""}\n\n${card.next_step_zh || ""}`))}</span>
      <h4>${escapeHtml(card.title_zh || "")}</h4>
      <small>${escapeHtml(localizeDisplayText(card.evidence_zh || ""))}</small>
    </article>
  `;
}

function decisionRow(row) {
  return `
    <div class="decision-row ${escapeHtml(row.kind || "context")}">
      <span>${fmtNumber(row.rank)}</span>
      <div>
        <strong>${escapeHtml(row.title_zh || "")} ${infoTip(localizeDisplayText(`${row.why_zh || ""}\n\n下一步：${row.next_step_zh || ""}`))}</strong>
      </div>
      <em>${escapeHtml(localizeDisplayText(row.evidence_zh || ""))}</em>
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
  const median = pos(dist.mean, min, max);
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
        <span>百分位 ${fmtScore(metric.percentile)}</span>
      </div>
    </div>
  `;
}

function themeOverview(themeRows, sentRows, conflictRows, themeViews = {}) {
  const sent = Object.fromEntries((sentRows || []).map((row) => [row.primary_theme, row]));
  const conf = Object.fromEntries((conflictRows || []).map((row) => [row.primary_theme, row]));
  const ratioOf = (row) => {
    const views = Number(themeViews[row.primary_theme]) || 0;
    return views > 0 ? (Number(row.n_comments) || 0) / views * 1000 : null;
  };
  const rows = (themeRows || []).filter((row) => row.primary_theme).slice(0, 10);
  if (!rows.length) return `<div class="empty-state">沒有主題資料</div>`;
  const maxR = Math.max(...rows.map((row) => ratioOf(row) || 0), 0.01);
  return `
    <div class="theme-table">
      <div class="theme-table-head">
        <span>題材</span><span>影片</span><span>留言/千觀看</span><span>正面率</span><span>負面率</span><span>衝突分數</span>
      </div>
      ${rows
        .map((row) => {
          const sv = sent[row.primary_theme] || {};
          const cv = conf[row.primary_theme] || {};
          const ratio = ratioOf(row);
          const w = ratio != null ? Math.max(3, (ratio / maxR) * 100) : 0;
          const views = Number(themeViews[row.primary_theme]) || 0;
          return `
            <div class="theme-table-row">
              <span class="theme-name" title="${escapeHtml(themeLabel(row.primary_theme))}">${escapeHtml(themeLabel(row.primary_theme))}</span>
              <span>${fmtCompact(row.n_videos)}</span>
              <span class="theme-vol" title="${fmtCompact(row.n_comments)} 留言 ÷ ${fmtCompact(views)} 觀看"><i style="width:${w.toFixed(0)}%"></i><b>${ratio != null ? ratio.toFixed(1) : "-"}</b></span>
              <span class="pos">${formatValue(sv.positive_rate, "rate")}</span>
              <span class="neg">${formatValue(sv.negative_rate, "rate")}</span>
              <span>${cv.conflict_score != null ? formatValue(cv.conflict_score, "") : "-"}</span>
            </div>`;
        })
        .join("")}
    </div>`;
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

function videoTimeline(rows, negMap = {}, events = []) {
  const sample = (rows || [])
    .map((row) => ({
      t: Date.parse(row.published_at || row.published_month || ""),
      comments: Number(row.observed_comments || row.comment_count || 0),
      views: Number(row.view_count || 0),
      neg: Number(negMap[row.video_id]),
      title: row.title || "未命名影片",
      published_at: row.published_at,
    }))
    .filter((row) => Number.isFinite(row.t))
    .sort((a, b) => a.t - b.t)
    .slice(-60);
  if (!sample.length) return `<div class="empty-state">沒有影片資料</div>`;
  const width = 1120;
  const height = 360;
  const margin = { left: 64, right: 74, top: 34, bottom: 50 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const tMin = sample[0].t;
  const tMax = Math.max(sample[sample.length - 1].t, tMin + 1);
  const x = (t) => margin.left + ((t - tMin) / (tMax - tMin)) * plotW;
  const maxC = Math.max(...sample.map((row) => row.comments), 1);
  const yC = (c) => margin.top + plotH - (Math.max(0, c) / maxC) * plotH;
  const logs = sample.map((row) => Math.log10(Math.max(1, row.views)));
  const maxLogV = Math.max(...logs, 1);
  const minLogV = Math.min(Math.min(...logs), maxLogV - 0.5);
  const yV = (v) =>
    margin.top + plotH - ((Math.log10(Math.max(1, v)) - minLogV) / Math.max(0.001, maxLogV - minLogV)) * plotH;
  const barW = Math.max(2, Math.min(18, (plotW / sample.length) * 0.62));
  const negTone = (neg) => (!Number.isFinite(neg) ? "" : neg >= 0.15 ? " neg-high" : neg >= 0.08 ? " neg-mid" : "");
  const bars = sample
    .map((row) => {
      const bx = x(row.t) - barW / 2;
      const by = yC(row.comments);
      const negTxt = Number.isFinite(row.neg) ? ` · 負面率 ${formatValue(row.neg, "rate")}` : "";
      const tip = `${row.title} · ${compactDate(row.published_at)} · 留言 ${fmtNumber(row.comments)} · 觀看 ${fmtNumber(row.views)}${negTxt}`;
      return `<rect class="vt-bar${negTone(row.neg)}" x="${bx.toFixed(1)}" y="${by.toFixed(1)}" width="${barW.toFixed(1)}" height="${(margin.top + plotH - by).toFixed(1)}" data-chart-tooltip="${tooltipAttr(tip)}"></rect>`;
    })
    .join("");
  const eventMarks = (events || [])
    .filter((event) => Number.isFinite(event.t) && event.t >= tMin && event.t <= tMax)
    .map((event) => {
      const cx = x(event.t);
      const tip = `外部事件 · ${event.date} · ${event.topic}${event.posts ? ` · ${fmtCompact(event.posts)} 篇貼文` : ""}`;
      return `<line class="vt-event" x1="${cx.toFixed(1)}" x2="${cx.toFixed(1)}" y1="${margin.top}" y2="${margin.top + plotH}"></line><polygon class="vt-event-mark" points="${cx.toFixed(1)},${margin.top} ${(cx - 4).toFixed(1)},${margin.top - 6} ${(cx + 4).toFixed(1)},${margin.top - 6}"></polygon><rect class="vt-event-hit" x="${(cx - 5).toFixed(1)}" y="${margin.top - 8}" width="10" height="${plotH + 8}" data-chart-tooltip="${tooltipAttr(tip)}"></rect>`;
    })
    .join("");
  const linePts = sample.map((row) => `${x(row.t).toFixed(1)},${yV(row.views).toFixed(1)}`).join(" ");
  const dots = sample
    .map(
      (row) =>
        `<circle class="vt-view-dot" cx="${x(row.t).toFixed(1)}" cy="${yV(row.views).toFixed(1)}" r="2.4" data-chart-tooltip="${tooltipAttr(`${row.title} · 觀看 ${fmtNumber(row.views)}`)}"></circle>`,
    )
    .join("");
  const cTicks = linearAxisTicks(maxC, 4);
  const vTicks = logAxisTicks(minLogV, maxLogV);
  const xTicks = timeAxisTicks(tMin, tMax, 5);
  return `
    <div class="external-chart-wrap">
      <svg class="external-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="近期影片留言量與觀看數">
        <text class="chart-title" x="${margin.left}" y="18">近期影片時間軸：留言量 × 觀看數 × 負面率 × 外部事件</text>
        <rect class="chart-bg" x="${margin.left}" y="${margin.top}" width="${plotW}" height="${plotH}"></rect>
        ${eventMarks}
        ${cTicks
          .map(
            (c) =>
              `<g class="chart-grid"><line x1="${margin.left}" x2="${margin.left + plotW}" y1="${yC(c).toFixed(1)}" y2="${yC(c).toFixed(1)}"></line><text x="${margin.left - 8}" y="${(yC(c) + 4).toFixed(1)}" text-anchor="end">${escapeHtml(fmtCompact(c))}</text></g>`,
          )
          .join("")}
        ${vTicks
          .map((lg) => {
            const yy = margin.top + plotH - ((lg - minLogV) / Math.max(0.001, maxLogV - minLogV)) * plotH;
            return `<text class="vt-right-tick" x="${margin.left + plotW + 8}" y="${(yy + 4).toFixed(1)}">${escapeHtml(fmtCompact(Math.pow(10, lg)))}</text>`;
          })
          .join("")}
        ${xTicks
          .map(
            (t) =>
              `<g class="chart-x-tick"><line x1="${x(t).toFixed(1)}" x2="${x(t).toFixed(1)}" y1="${margin.top + plotH}" y2="${margin.top + plotH + 6}"></line><text x="${x(t).toFixed(1)}" y="${margin.top + plotH + 24}" text-anchor="middle">${escapeHtml(formatYearMonth(t))}</text></g>`,
          )
          .join("")}
        <text class="chart-axis-label" x="16" y="${margin.top + 10}" transform="rotate(-90 16 ${margin.top + 10})">留言數（左軸）</text>
        <text class="chart-axis-label" x="${width - 12}" y="${margin.top + 10}" transform="rotate(-90 ${width - 12} ${margin.top + 10})" text-anchor="end">觀看數（右軸·對數）</text>
        <text class="chart-axis-label" x="${margin.left + plotW / 2}" y="${height - 10}" text-anchor="middle">影片發布時間</text>
        ${bars}
        <polyline class="vt-view-line" points="${linePts}" fill="none"></polyline>
        ${dots}
      </svg>
      <div class="external-chart-legend">
        <span><i class="vt-lg-bar"></i>留言數（左軸）</span>
        <span><i class="vt-lg-negmid"></i>負面率 8–15%</span>
        <span><i class="vt-lg-neghigh"></i>負面率 ≥15%</span>
        <span><i class="event watch"></i>觀看數（右軸·對數）</span>
        <span><i class="vt-lg-event"></i>外部事件</span>
      </div>
    </div>`;
}

function linearAxisTicks(max, count) {
  const step = niceStep(max / Math.max(1, count));
  const ticks = [];
  for (let v = 0; v <= max + 1e-9; v += step) ticks.push(v);
  return ticks;
}

function niceStep(raw) {
  const power = Math.pow(10, Math.floor(Math.log10(Math.max(raw, 1e-9))));
  const n = raw / power;
  const nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return nice * power;
}

function logAxisTicks(minLog, maxLog) {
  const ticks = [];
  for (let p = Math.ceil(minLog); p <= Math.floor(maxLog); p += 1) ticks.push(p);
  if (!ticks.length) ticks.push(Math.round((minLog + maxLog) / 2));
  return ticks.slice(-5);
}

function timeAxisTicks(tMin, tMax, count) {
  const ticks = [];
  const n = Math.max(2, count);
  for (let i = 0; i < n; i += 1) ticks.push(tMin + ((tMax - tMin) * i) / (n - 1));
  return ticks;
}

function formatYearMonth(time) {
  const d = new Date(time);
  if (!Number.isFinite(d.getTime())) return "-";
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function videoEngagementTable(rows) {
  const scored = rows
    .map((row) => {
      const comments = Number(row.observed_comments || row.comment_count || 0);
      const views = Number(row.view_count || 0);
      return {
        ...row,
        observed_comments: comments,
        comments_per_1k_views: views > 0 ? (comments / views) * 1000 : null,
      };
    })
    .filter((row) => Number.isFinite(Number(row.comments_per_1k_views)))
    .sort((a, b) => Number(b.comments_per_1k_views || 0) - Number(a.comments_per_1k_views || 0))
    .slice(0, 12);
  if (!scored.length) return `<div class="empty-state">沒有影片留言率資料</div>`;
  const max = Math.max(...scored.map((row) => Number(row.comments_per_1k_views || 0)), 1);
  return `
    <div class="video-engagement-table">
      <div class="video-engagement-head">
        <span>影片</span>
        <span>發布</span>
        <span>觀看</span>
        <span>留言</span>
        <span>留言 / 千次觀看</span>
      </div>
      ${scored
        .map((row) => {
          const width = Math.max(3, (Number(row.comments_per_1k_views || 0) / max) * 100);
          return `
            <div class="video-engagement-row">
              <div class="video-title-cell" title="${escapeHtml(row.title || "")}">${escapeHtml(row.title || "-")}</div>
              <div>${compactDate(row.published_at)}</div>
              <div>${fmtCompact(row.view_count)}</div>
              <div>${fmtCompact(row.observed_comments)}</div>
              <div class="rate-cell">
                <span>${formatValue(row.comments_per_1k_views, "comments_per_1k_views")}</span>
                <i><b style="width:${width}%"></b></i>
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function likesViewsPanel(rows) {
  const points = normalizeLikesViewsRows(rows);
  if (points.length < 6) return `<div class="empty-state">影片觀看數與按讚數資料不足。</div>`;
  const model = fitLogLogRegression(points);
  const outliers = likesViewsOutliers(points, model);
  return `
    <div class="likes-view-layout">
      <div>
        ${likesViewsScatter(points, model, outliers)}
      </div>
      <aside class="likes-view-summary">
        <div class="model-stat-grid">
          <div><span>影片數</span><strong>${fmtNumber(points.length)}</strong></div>
          <div><span>R²</span><strong>${model.r2.toFixed(2)}</strong></div>
          <div><span>斜率</span><strong>${model.slope.toFixed(2)}</strong></div>
          <div><span>判讀</span><strong>${escapeHtml(likesViewsModelLabel(model))}</strong></div>
        </div>
        <div class="compact-card-list">
          ${outliers.slice(0, 5).map(likesViewOutlierCard).join("")}
        </div>
      </aside>
    </div>`;
}

function normalizeLikesViewsRows(rows) {
  return (rows || [])
    .map((row) => {
      const views = Number(row.view_count || 0);
      const likes = Number(row.like_count || 0);
      return {
        ...row,
        views,
        likes,
        logViews: Math.log10(views + 1),
        logLikes: Math.log10(likes + 1),
        likeRate: views > 0 ? likes / views : null,
      };
    })
    .filter((row) => row.views > 0 && row.likes > 0 && Number.isFinite(row.logViews) && Number.isFinite(row.logLikes));
}

function fitLogLogRegression(points) {
  const n = points.length || 1;
  const meanX = points.reduce((sum, row) => sum + row.logViews, 0) / n;
  const meanY = points.reduce((sum, row) => sum + row.logLikes, 0) / n;
  const sxx = points.reduce((sum, row) => sum + Math.pow(row.logViews - meanX, 2), 0);
  const sxy = points.reduce((sum, row) => sum + (row.logViews - meanX) * (row.logLikes - meanY), 0);
  const slope = sxx > 0 ? sxy / sxx : 1;
  const intercept = meanY - slope * meanX;
  const withResiduals = points.map((row) => {
    const predictedLogLikes = intercept + slope * row.logViews;
    const residual = row.logLikes - predictedLogLikes;
    const expectedLikes = Math.max(0, Math.pow(10, predictedLogLikes) - 1);
    return {
      ...row,
      predictedLogLikes,
      residual,
      expectedLikes,
      likeLiftVsExpected: expectedLikes > 0 ? row.likes / expectedLikes : null,
    };
  });
  const sse = withResiduals.reduce((sum, row) => sum + Math.pow(row.residual, 2), 0);
  const sst = points.reduce((sum, row) => sum + Math.pow(row.logLikes - meanY, 2), 0);
  const residualStd = Math.sqrt(sse / Math.max(1, n - 2)) || 1;
  withResiduals.forEach((row) => {
    row.residualZ = row.residual / residualStd;
  });
  return {
    intercept,
    slope,
    r2: sst > 0 ? Math.max(0, Math.min(1, 1 - sse / sst)) : 0,
    residualStd,
    points: withResiduals,
  };
}

function likesViewsOutliers(points, model) {
  const views = points.map((row) => row.views).sort((a, b) => a - b);
  const minStableViews = Math.max(1000, quantile(views, 0.1));
  return model.points
    .filter((row) => row.views >= minStableViews && Number.isFinite(row.residualZ))
    .sort((a, b) => b.residualZ - a.residualZ)
    .slice(0, 8);
}

function likesViewsScatter(points, model, outliers) {
  const enriched = model.points;
  const outlierIds = new Set(outliers.slice(0, 8).map((row) => row.video_id || row.title));
  const width = 820;
  const height = 460;
  const margin = { left: 78, right: 28, top: 24, bottom: 56 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const xMin = Math.min(...enriched.map((row) => row.logViews)) - 0.05;
  const xMax = Math.max(...enriched.map((row) => row.logViews)) + 0.05;
  const yMin = Math.min(...enriched.map((row) => row.logLikes)) - 0.08;
  const yMax = Math.max(...enriched.map((row) => row.logLikes)) + 0.08;
  const x = (value) => margin.left + ((value - xMin) / Math.max(0.001, xMax - xMin)) * plotW;
  const y = (value) => margin.top + ((yMax - value) / Math.max(0.001, yMax - yMin)) * plotH;
  const xTicks = logTicksFromRange(xMin, xMax);
  const yTicks = logTicksFromRange(yMin, yMax);
  const trendStartY = model.intercept + model.slope * xMin;
  const trendEndY = model.intercept + model.slope * xMax;
  const circles = enriched
    .map((row) => {
      const key = row.video_id || row.title;
      const cls = outlierIds.has(key) ? "is-outlier" : row.residualZ < -1.5 ? "is-low" : "";
      return `
        <circle class="likes-view-point ${cls}" data-chart-tooltip="${tooltipAttr(likesViewTooltip(row))}"
          cx="${x(row.logViews).toFixed(1)}" cy="${y(row.logLikes).toFixed(1)}" r="${outlierIds.has(key) ? 5.4 : 3.6}"></circle>`;
    })
    .join("");
  return `
    <div class="likes-view-chart-wrap">
      <svg class="likes-view-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="觀看數與按讚數散點圖">
        <rect class="chart-bg" x="${margin.left}" y="${margin.top}" width="${plotW}" height="${plotH}"></rect>
        ${xTicks.map((tick) => `
          <g class="chart-x-tick">
            <line x1="${x(Math.log10(tick + 1)).toFixed(1)}" x2="${x(Math.log10(tick + 1)).toFixed(1)}" y1="${margin.top + plotH}" y2="${margin.top + plotH + 6}"></line>
            <text x="${x(Math.log10(tick + 1)).toFixed(1)}" y="${margin.top + plotH + 25}">${escapeHtml(fmtCompact(tick))}</text>
          </g>`).join("")}
        ${yTicks.map((tick) => `
          <g class="chart-grid">
            <line x1="${margin.left}" x2="${margin.left + plotW}" y1="${y(Math.log10(tick + 1)).toFixed(1)}" y2="${y(Math.log10(tick + 1)).toFixed(1)}"></line>
            <text x="${margin.left - 10}" y="${(y(Math.log10(tick + 1)) + 4).toFixed(1)}">${escapeHtml(fmtCompact(tick))}</text>
          </g>`).join("")}
        <line class="likes-view-trend" x1="${x(xMin).toFixed(1)}" y1="${y(trendStartY).toFixed(1)}" x2="${x(xMax).toFixed(1)}" y2="${y(trendEndY).toFixed(1)}"></line>
        ${circles}
        <text class="chart-axis-label" x="18" y="${margin.top + 12}" transform="rotate(-90 18 ${margin.top + 12})">按讚數（對數刻度）</text>
        <text class="chart-axis-label" x="${margin.left + plotW}" y="${height - 12}" text-anchor="end">觀看數（對數刻度）</text>
      </svg>
      <div class="external-chart-legend">
        <span><i class="video"></i>一般影片</span>
        <span><i class="event high"></i>超預期按讚</span>
        <span><i class="event cool"></i>低於趨勢</span>
      </div>
    </div>`;
}

function likesViewOutlierCard(row) {
  return `
    <article class="compact-card likes-outlier-card">
      <div>
        <strong title="${escapeHtml(row.title || "")}">${escapeHtml(row.title || "-")}</strong>
        <span>${compactDate(row.published_at)} · 預期按讚倍率 ${formatValue(row.likeLiftVsExpected, "lift")} · 殘差 ${fmtScore(row.residualZ)}</span>
      </div>
      <div class="dual-metric">
        <span>觀看 ${formatValue(row.views, "n")}</span>
        <span>按讚 ${formatValue(row.likes, "n")}</span>
        <span>按讚率 ${formatValue(row.likeRate, "rate")}</span>
        <span>預期按讚 ${formatValue(row.expectedLikes, "n")}</span>
      </div>
    </article>`;
}

function likesViewTooltip(row) {
  return [
    row.title || "-",
    compactDate(row.published_at),
    `觀看數：${fmtNumber(row.views)}`,
    `按讚數：${fmtNumber(row.likes)}`,
    `按讚率：${formatValue(row.likeRate, "rate")}`,
    `趨勢預期按讚：${fmtNumber(row.expectedLikes)}`,
    `預期倍率：${formatValue(row.likeLiftVsExpected, "lift")}`,
    `殘差標準分數：${fmtScore(row.residualZ)}`,
  ].join("\n");
}

function likesViewsModelLabel(model) {
  if (model.r2 < 0.55) return "關係分散";
  if (Math.abs(model.slope - 1) <= 0.15) return "接近等比例";
  if (model.slope > 1) return "高觀看更容易累積讚";
  return "低觀看影片讚率較突出";
}

function logTicksFromRange(minLog, maxLog) {
  const ticks = [];
  const start = Math.max(0, Math.floor(minLog));
  const end = Math.ceil(maxLog);
  for (let p = start; p <= end; p += 1) {
    const value = Math.pow(10, p);
    if (value >= 10) ticks.push(value);
  }
  return ticks.slice(-6);
}

function quantile(values, q) {
  if (!values.length) return 0;
  const pos = (values.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  if (lo === hi) return values[lo];
  return values[lo] + (values[hi] - values[lo]) * (pos - lo);
}

function audienceBaselineBars() {
  const rows = [
    { label: "核心觀眾占比", metric: "high_mid_tier_commenter_share", key: "share", tone: "good" },
    { label: "核心觀眾留言貢獻", metric: "high_mid_tier_comment_share", key: "share", tone: "watch" },
    { label: "跨影片回訪率（全期）", metric: "continuity_return_rate_w4", key: "rate", tone: "good" },
    { label: "近期回訪率（最新窗）", metric: "rolling_return_rate_latest", key: "rate", tone: "good" },
  ];
  return `<div class="comparison-bars">${rows.map(comparisonMetricBar).join("")}</div>`;
}

function sentimentBaselineBars() {
  const rows = [
    { label: "正面留言率", metric: "positive_rate", key: "rate", tone: "good" },
    { label: "負面留言率", metric: "negative_rate", key: "rate", tone: "risk" },
    { label: "按讚加權負面", metric: "like_weighted_negative_rate", key: "rate", tone: "risk" },
    { label: "單片最高負面", metric: "max_video_like_weighted_negative_rate", key: "rate", tone: "risk" },
  ];
  return `<div class="comparison-bars">${rows.map(comparisonMetricBar).join("")}</div>`;
}

function replyBaselineBars(replyOverview) {
  const rows = [
    {
      label: "回覆占比",
      metric: "reply_share_all_comments",
      key: "rate",
      tone: "watch",
      value: replyOverview.reply_share_all_comments,
    },
    { label: "影片衝突峰值", metric: "max_video_reply_count_weighted_conflict_score", key: "score", tone: "risk" },
    { label: "按讚加權衝突", metric: "max_video_like_weighted_conflict_score", key: "score", tone: "risk" },
    { label: "題材衝突峰值", metric: "max_theme_reply_count_weighted_conflict_score", key: "score", tone: "risk" },
  ];
  return `<div class="comparison-bars">${rows.map(comparisonMetricBar).join("")}</div>`;
}

function themeRiskBars(rows) {
  const usable = withMinSample(
    (rows || []).filter((row) => row.primary_theme || row.theme_label),
    MIN_THEME_COMMENTS,
  )
    .map((row) => ({
      theme: row.primary_theme || row.theme_label,
      n_comments: row.n_comments,
      negative_rate: row.negative_rate,
      like_weighted_negative_rate: row.like_weighted_negative_rate,
      positive_rate: row.positive_rate,
    }))
    .sort((a, b) => Number(b.like_weighted_negative_rate || b.negative_rate || 0) - Number(a.like_weighted_negative_rate || a.negative_rate || 0))
    .slice(0, 8);
  if (!usable.length) return `<div class="empty-state">沒有題材情緒資料</div>`;
  const max = Math.max(...usable.map((row) => Number(row.like_weighted_negative_rate || row.negative_rate || 0)), 0.01);
  return `<div class="insight-list">${usable
    .map((row) => {
      const risk = Number(row.like_weighted_negative_rate || row.negative_rate || 0);
      return `
        <div class="insight-row">
          <div class="insight-label">
            <strong>${escapeHtml(themeLabel(row.theme))}</strong>
            <span>${fmtCompact(row.n_comments)} 留言 · 正面 ${formatValue(row.positive_rate, "rate")}</span>
          </div>
          <div class="risk-track"><i style="width:${Math.max(3, (risk / max) * 100)}%"></i></div>
          <div class="insight-value">${formatValue(risk, "rate")}</div>
        </div>`;
    })
    .join("")}</div>`;
}

function videoPositiveReasons(videoId, aspectMap, aspectLabels) {
  const reasons = (aspectMap[videoId] || []).filter((item) => item.aspect && !NON_IMPACT_ASPECTS.has(item.aspect)).slice(0, 3);
  if (!reasons.length) return "";
  return `
    <div class="video-aspect-block pos">
      <span class="video-aspect-label">被稱讚的點</span>
      <div class="video-aspects">
        ${reasons
          .map(
            (item) =>
              `<span class="video-aspect pos"><b>${escapeHtml(aspectLabels[item.aspect] || item.aspect)}</b> ${formatValue(item.share, "rate")}</span>`,
          )
          .join("")}
      </div>
    </div>`;
}

function positiveVideoCards(rows, aspectMap = {}, aspectLabels = {}) {
  const usable = withMinSample(
    (rows || []).map((row) => ({ ...row, n_comments_num: Number(row.n_comments || 0) })),
    MIN_VIDEO_COMMENTS,
  )
    .sort((a, b) => Number(b.like_weighted_positive_rate || b.positive_rate || 0) - Number(a.like_weighted_positive_rate || a.positive_rate || 0))
    .slice(0, 6);
  if (!usable.length) return `<div class="empty-state">沒有高正面影片資料</div>`;
  return `<div class="compact-card-list">${usable
    .map((row) => `
      <article class="compact-card positive-card">
        <div>
          <strong title="${escapeHtml(row.title || "")}">${escapeHtml(row.title || "-")}</strong>
          <span>${compactDate(row.published_at)} · ${escapeHtml(themeLabel(row.primary_theme))} · ${fmtCompact(row.n_comments)} 留言</span>
        </div>
        <div class="dual-metric sentiment-card-metrics">
          ${metricPill("正面", row.positive_rate, "rate")}
          ${metricPill("按讚加權正面", row.like_weighted_positive_rate, "rate", "正面留言被『讚數』加權後的比例：被越多人按讚的正面留言權重越高，比單純算則數更能反映多數人也認同的正面。算法 ≈ Σ(正面留言×讚) ÷ Σ(全部留言×讚)。")}
          ${metricPill("負面", row.negative_rate, "rate")}
          ${metricPill("回覆占比", row.reply_share, "rate")}
        </div>
        ${videoPositiveReasons(row.video_id, aspectMap, aspectLabels)}
      </article>`)
    .join("")}</div>`;
}

const MIN_THEME_COMMENTS = 30;
const MIN_VIDEO_COMMENTS = 50;

function withMinSample(rows, min) {
  // Drop low-sample rows so a theme/video with a handful of comments cannot top a
  // rate ranking (e.g. 1 comment = 100% positive). Fall back to all rows when the
  // filter would leave nothing (small channels), so panels never go empty.
  const ok = (rows || []).filter((row) => Number(row.n_comments ?? row.n_comments_num ?? 0) >= min);
  return ok.length ? ok : rows || [];
}

function channelAspectBars(rows, shareKey, labels = {}, tone = "") {
  const usable = (rows || [])
    .filter((row) => row.aspect && !NON_IMPACT_ASPECTS.has(row.aspect))
    .map((row) => ({ aspect: row.aspect, share: Number(row[shareKey]) || 0 }))
    .filter((row) => row.share > 0)
    .sort((a, b) => b.share - a.share)
    .slice(0, 6);
  if (!usable.length) return `<div class="empty-state">沒有面向資料</div>`;
  const max = Math.max(...usable.map((row) => row.share), 0.01);
  const pos = tone === "pos";
  return `<div class="insight-list">${usable
    .map(
      (row) => `
      <div class="insight-row${pos ? " positive" : ""}">
        <div class="insight-label"><strong>${escapeHtml(labels[row.aspect] || row.aspect)}</strong></div>
        <div class="${pos ? "positive-track" : "risk-track"}"><i style="width:${Math.max(3, (row.share / max) * 100).toFixed(0)}%"></i></div>
        <div class="insight-value">${formatValue(row.share, "rate")}</div>
      </div>`,
    )
    .join("")}</div>`;
}

function positiveThemeBars(rows) {
  const usable = withMinSample(
    (rows || []).filter((row) => row.primary_theme || row.theme_label),
    MIN_THEME_COMMENTS,
  )
    .sort((a, b) => Number(b.like_weighted_positive_rate || b.positive_rate || 0) - Number(a.like_weighted_positive_rate || a.positive_rate || 0))
    .slice(0, 8);
  if (!usable.length) return `<div class="empty-state">沒有題材正面資料</div>`;
  const max = Math.max(...usable.map((row) => Number(row.like_weighted_positive_rate || row.positive_rate || 0)), 0.01);
  return `<div class="insight-list">${usable
    .map((row) => {
      const score = Number(row.like_weighted_positive_rate || row.positive_rate || 0);
      return `
        <div class="insight-row positive">
          <div class="insight-label">
            <strong>${escapeHtml(themeLabel(row.primary_theme || row.theme_label))}</strong>
            <span>${fmtCompact(row.n_comments)} 留言 · 負面 ${formatValue(row.negative_rate, "rate")}</span>
          </div>
          <div class="positive-track"><i style="width:${Math.max(3, (score / max) * 100)}%"></i></div>
          <div class="insight-value">${formatValue(score, "rate")}</div>
        </div>`;
    })
    .join("")}</div>`;
}

function buildVideoAspectMap(rows) {
  const map = {};
  (rows || []).forEach((row) => {
    const videoId = row.video_id;
    if (!videoId) return;
    (map[videoId] ||= []).push({
      aspect: row.aspect,
      count: Number(row.count) || 0,
      share: Number(row.aspect_share) || 0,
    });
  });
  Object.values(map).forEach((list) => list.sort((a, b) => b.count - a.count));
  return map;
}

// Aspects that are negative but not actionable / no real channel impact.
const NON_IMPACT_ASPECTS = new Set(["other", "unclear"]);

function videoImpactfulNegativeShare(videoId, aspectMap) {
  const list = aspectMap[videoId] || [];
  const total = list.reduce((acc, item) => acc + (Number(item.count) || 0), 0);
  if (!total) return null;
  const impactful = list
    .filter((item) => item.aspect && !NON_IMPACT_ASPECTS.has(item.aspect))
    .reduce((acc, item) => acc + (Number(item.count) || 0), 0);
  return impactful / total;
}

function videoAspectReasons(videoId, aspectMap, aspectLabels) {
  const reasons = (aspectMap[videoId] || []).filter((item) => item.aspect && !NON_IMPACT_ASPECTS.has(item.aspect)).slice(0, 3);
  if (!reasons.length) return "";
  return `
    <div class="video-aspect-block">
      <span class="video-aspect-label">主要負面原因</span>
      <div class="video-aspects">
        ${reasons
          .map(
            (item) =>
              `<span class="video-aspect"><b>${escapeHtml(aspectLabels[item.aspect] || item.aspect)}</b> ${formatValue(item.share, "rate")}</span>`,
          )
          .join("")}
      </div>
    </div>`;
}

function riskVideoCards(rows, aspectMap = {}, aspectLabels = {}) {
  const usable = withMinSample(rows || [], MIN_VIDEO_COMMENTS)
    .map((row) => {
      const rawNeg = Number(row.like_weighted_negative_rate || row.negative_rate || 0);
      const impactShare = videoImpactfulNegativeShare(row.video_id, aspectMap);
      // When ABSA aspects exist, weight negativity by the share that is actionable
      // (drop other/unclear that are negative but don't really hurt the channel),
      // so the ranking reflects real impact, not noise.
      return { ...row, _score: impactShare === null ? rawNeg : rawNeg * impactShare, _impactShare: impactShare };
    })
    .sort((a, b) => b._score - a._score)
    .slice(0, 6);
  if (!usable.length) return `<div class="empty-state">沒有高負面影片資料</div>`;
  return `<div class="compact-card-list">${usable
    .map((row) => `
      <article class="compact-card risk-card">
        <div>
          <strong title="${escapeHtml(row.title || "")}">${escapeHtml(row.title || "-")}</strong>
          <span>${compactDate(row.published_at)} · ${escapeHtml(themeLabel(row.primary_theme))}</span>
        </div>
        <div class="dual-metric sentiment-card-metrics">
          ${metricPill("負面", row.negative_rate, "rate")}
          ${metricPill("按讚加權負面", row.like_weighted_negative_rate, "rate", "負面留言被『讚數』加權後的比例：被越多人按讚的負面留言權重越高，反映多數人也有同感的負面。算法 ≈ Σ(負面留言×讚) ÷ Σ(全部留言×讚)。")}
          ${row._impactShare === null ? "" : metricPill("實質負面占比", row._impactShare, "rate", "該片負面留言中屬於『可行動面向』的比例：ABSA 把每則負面留言分到面向（步調剪輯／業配／真實性…），扣掉 other／unclear 這類雖負面但對頻道無實質影響的部分。本卡排名用的『實質負面』＝按讚加權負面率 × 此占比，避免被無意義負面灌水。")}
        </div>
        ${videoAspectReasons(row.video_id, aspectMap, aspectLabels)}
      </article>`)
    .join("")}</div>`;
}

function metricPill(label, value, key, tip) {
  const tipAttr = tip ? ` data-chart-tooltip="${tooltipAttr(tip)}"` : "";
  return `<span class="metric-pill"${tipAttr}><b>${escapeHtml(label)}</b><em>${escapeHtml(formatValue(value, key))}</em></span>`;
}

function conflictVideoCards(rows) {
  const usable = (rows || [])
    .slice()
    .sort((a, b) => Number(b.like_weighted_conflict_score || b.reply_count_weighted_conflict_score || 0) - Number(a.like_weighted_conflict_score || a.reply_count_weighted_conflict_score || 0))
    .slice(0, 6);
  if (!usable.length) return `<div class="empty-state">沒有高衝突影片資料</div>`;
  return `<div class="compact-card-list">${usable
    .map((row) => `
      <article class="compact-card risk-card">
        <div>
          <strong title="${escapeHtml(row.title || "")}">${escapeHtml(row.title || "-")}</strong>
          <span>${compactDate(row.published_at)} · ${escapeHtml(themeLabel(row.primary_theme))}</span>
        </div>
        <div class="dual-metric conflict-breakdown">
          <span title="整串正負面都很高（極化，兩派並存）">衝突串 ${fmtCompact(row.n_conflict_threads)}</span>
          <span class="${Number(row.n_pile_on_threads) > 0 ? "hot" : ""}" title="3+ 回覆幾乎全負面（圍剿母留言）">圍剿 ${fmtCompact(row.n_pile_on_threads)}</span>
          <span class="${Number(row.n_parent_opposition_threads) > 0 ? "hot" : ""}" title="回覆與母留言立場相反（反對原留言者）">對立母串 ${fmtCompact(row.n_parent_opposition_threads)}</span>
        </div>
      </article>`)
    .join("")}</div>`;
}

function themeConflictBars(rows) {
  // Rank by conflict *rate* (share of replied threads that are conflict threads),
  // not raw conflict volume; require enough replied threads so the rate isn't noisy.
  const withReplies = (rows || []).filter((row) => row.primary_theme && Number(row.n_threads_with_replies) >= 20);
  const pool = withReplies.length ? withReplies : (rows || []).filter((row) => row.primary_theme);
  const usable = pool
    .map((row) => ({ ...row, _rate: Number(row.conflict_thread_rate_replied || 0) }))
    .sort((a, b) => b._rate - a._rate)
    .slice(0, 8);
  if (!usable.length) return `<div class="empty-state">沒有題材衝突資料</div>`;
  const max = Math.max(...usable.map((row) => row._rate), 0.01);
  return `<div class="insight-list">${usable
    .map(
      (row) => `
        <div class="insight-row">
          <div class="insight-label">
            <strong>${escapeHtml(themeLabel(row.primary_theme))}</strong>
            <span>${fmtCompact(row.n_threads_with_replies)} 有回覆串 · ${fmtCompact(row.n_conflict_threads)} 衝突串</span>
          </div>
          <div class="risk-track"><i style="width:${Math.max(3, (row._rate / max) * 100)}%"></i></div>
          <div class="insight-value">${formatValue(row._rate, "rate")}</div>
        </div>`,
    )
    .join("")}</div>`;
}

function replySentimentBars(rows) {
  const usable = (rows || []).filter((row) => row.n_comments || row.negative_rate !== undefined);
  if (!usable.length) return `<div class="empty-state">沒有回覆情緒資料</div>`;
  return `<div class="insight-list">${usable
    .map((row) => {
      const label = String(row.is_top_level_label || row.is_top_level || "").includes("reply") || row.is_top_level === "0" ? "回覆" : "主留言";
      return `
        <div class="insight-row">
          <div class="insight-label">
            <strong>${label}</strong>
            <span>${fmtCompact(row.n_comments)} 留言 · 正面 ${formatValue(row.positive_rate, "rate")}</span>
          </div>
          <div class="risk-track"><i style="width:${Math.max(3, Number(row.like_weighted_negative_rate || row.negative_rate || 0) * 100)}%"></i></div>
          <div class="insight-value">${formatValue(row.like_weighted_negative_rate || row.negative_rate, "rate")}</div>
        </div>`;
    })
    .join("")}</div>`;
}

function videoClusterCards(rows) {
  const usable = (rows || []).slice(0, 5);
  if (!usable.length) return `<div class="empty-state">沒有內容系列資料</div>`;
  return `<div class="cluster-card-list">${usable
    .map((row, idx) => {
      const size = row.size || row;
      const metadata = row.metadata || row;
      const topic = row.topic_from_title_description_tags || {};
      const topThemes = topic.top_themes || parseLabelCountText(row.top_theme_labels);
      const topVideos = topic.top_videos || labelCountObjects(row.top_videos);
      return `
        <article class="cluster-card">
          <div class="cluster-card-head">
            <strong>${escapeHtml(videoClusterLabel(row.video_cluster, idx, row))}</strong>
            <span>${fmtNumber(size.n_videos)} 支影片 · ${fmtCompact(metadata.total_observed_comments)} 留言</span>
          </div>
          <div class="pill-row">${topThemes.slice(0, 4).map((item) => `<span>${escapeHtml(themeLabel(item.label || item.theme))}</span>`).join("")}</div>
          <p>${topVideos.slice(0, 2).map((item) => item.label).filter(Boolean).join(" / ")}</p>
        </article>`;
    })
    .join("")}</div>`;
}

function affinityBars(rows) {
  const usable = (rows || [])
    .filter((row) => row.theme_label || row.primary_theme)
    .sort((a, b) => Number(b.lift || 0) - Number(a.lift || 0))
    .slice(0, 8);
  if (!usable.length) return `<div class="empty-state">沒有系列題材集中度資料</div>`;
  const max = Math.max(...usable.map((row) => Number(row.lift || 0)), 1);
  return `<div class="insight-list">${usable
    .map((row) => `
      <div class="insight-row">
        <div class="insight-label">
          <strong>${escapeHtml(videoClusterLabel(row.video_cluster))} · ${escapeHtml(themeLabel(row.theme_label || row.primary_theme))}</strong>
          <span>系列占比 ${formatValue(row.cluster_share, "share")} · 全頻道 ${formatValue(row.overall_share, "share")}</span>
        </div>
        <div class="comparison-track"><i class="value" style="width:${Math.max(3, (Number(row.lift || 0) / max) * 100)}%"></i></div>
        <div class="insight-value">${formatValue(row.lift, "lift")}</div>
      </div>`)
    .join("")}</div>`;
}

function opportunityCards(rows) {
  const usable = (rows || []).slice(0, 6);
  if (!usable.length) return `<div class="empty-state">沒有跨題材企劃資料</div>`;
  return `<div class="compact-card-list">${usable
    .map((row) => `
      <article class="compact-card opportunity-card">
        <div>
          <strong>${escapeHtml(opportunityTitle(row))}</strong>
          <span>${escapeHtml(opportunityTypeLabel(row.opportunity_type))} · 分數 ${formatValue(row.opportunity_score, "score")}</span>
        </div>
        <p>${escapeHtml(opportunityDescription(row))}</p>
      </article>`)
    .join("")}</div>`;
}

function opportunityTitle(row) {
  const sourceTheme = themeLabel(row.source_primary_theme);
  const targetTheme = themeLabel(row.target_primary_theme);
  const source = conciseTitle(row.source_title, 14);
  if (sourceTheme && targetTheme && sourceTheme !== targetTheme) {
    return `${sourceTheme} × ${targetTheme}｜${source || "企劃橋接"}`;
  }
  return `${sourceTheme || targetTheme || "相似觀眾"}｜${source || opportunityTypeLabel(row.opportunity_type)}`;
}

function opportunityDescription(row) {
  const source = conciseTitle(row.source_title, 34);
  const target = conciseTitle(row.target_title, 34);
  if (source && target) return `可把「${source}」的觀眾導向「${target}」`;
  return `${themeLabel(row.source_primary_theme)} → ${themeLabel(row.target_primary_theme)}`;
}

function conciseTitle(value, limit = 24) {
  const text = String(value || "")
    .replace(/｜?The DoDo Men.*$/i, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) return "";
  return Array.from(text).slice(0, limit).join("") + (Array.from(text).length > limit ? "…" : "");
}

function sourceLabelList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => ({ ptt: "PTT", dcard: "Dcard" }[item.toLowerCase()] || item))
    .join(" / ");
}

function externalTopicLabel(value) {
  const map = {
    recommendation_or_general_mentions: "一般提及 / 推薦",
    mixed_external_discussion: "外部混合討論",
    controversy_or_criticism: "外部爭議 / 批評",
    controversy_or_apology: "爭議 / 道歉聲明",
    political_or_social_controversy: "政治 / 社會爭議",
    content_quality_criticism: "內容品質批評",
    content_authenticity_question: "內容真實性質疑",
    authenticity_or_fabrication: "真實性 / 造假質疑",
    staff_or_host_change: "主持人 / 團隊變動",
    survey_or_spam: "問卷 / 灌水",
    general: "一般討論",
    politics_or_culture: "政治 / 文化價值討論",
  };
  return map[value] || String(value || "外部討論").replaceAll("_", " ");
}

function parseLabelCountText(value) {
  return String(value || "")
    .split(";")
    .map((part) => {
      const m = part.trim().match(/^(.*)\s+\(([-\d.]+)\)$/);
      return m ? { label: m[1], count: Number(m[2]) } : { label: part.trim(), count: null };
    })
    .filter((item) => item.label);
}

function labelCountObjects(value) {
  if (Array.isArray(value)) return value;
  return parseLabelCountText(value);
}

function clusterList(rows) {
  if (!rows.length) return `<div class="empty-state">沒有內容系列資料</div>`;
  return `<div class="cluster-list">${rows
    .slice(0, 5)
    .map((row, idx) => {
      const titles = topVideoTitles(row.top_videos);
      return `
      <div class="cluster-row">
        <strong>${escapeHtml(videoClusterLabel(row.video_cluster, idx, row))}</strong>
        <span>${fmtNumber(row.n_videos)} 支影片 · ${fmtCompact(row.total_views)} 觀看 · ${fmtCompact(row.total_observed_comments)} 留言 · ${fmtCompact(row.unique_commenters)} 留言者</span>
        <p>代表影片：${escapeHtml(titles.length ? titles.join("、") : "沒有代表影片資料")}</p>
      </div>`;
    })
    .join("")}</div>`;
}

function topVideoTitles(value, limit = 3) {
  return String(value || "")
    .split(";")
    .map((item) => item.trim().replace(/\s*\([^()]*\)\s*$/, ""))
    .filter(Boolean)
    .slice(0, limit);
}

function tierBars(rows) {
  if (!rows.length) return `<div class="empty-state">沒有觀眾活躍度資料</div>`;
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

function tierComparisonBars(rows) {
  if (!rows.length) return `<div class="empty-state">沒有觀眾活躍度資料</div>`;
  return `<div class="tier-comparison-list">${rows
    .map((row) => {
      const tier = row.activity_tier;
      const metric = baselineMetric(`${tier}_tier_commenter_share`);
      // pct_commenters is always a percent (0-100); convert to fraction directly
      // so sub-1% tiers (e.g. a 0.88% core) are not misread as the fraction 0.88.
      const pct = Number(row.pct_commenters);
      const value = Number.isFinite(pct) ? pct / 100 : null;
      const mean = metric?.distribution?.mean;
      const max = comparisonScaleMax(value, mean, metric?.distribution?.p75, metric?.distribution?.max);
      return `
        <div class="tier-comparison-row">
          <div class="tier-comparison-label">
            <strong>${escapeHtml(tierLabel(tier))}</strong>
            <span>${fmtNumber(row.n_commenters)} 人 · 平均 ${formatValue(row.avg_videos, "avg_videos")} 支影片</span>
          </div>
          <div class="comparison-track">
            <i class="value" style="width:${pos(value, 0, max)}%"></i>
            <i class="median" style="left:${pos(mean, 0, max)}%"></i>
          </div>
          <div class="comparison-value">
            <strong>${formatValue(value, "share")}</strong>
            <span>基準平均 ${formatValue(mean, "share")}</span>
          </div>
        </div>`;
    })
    .join("")}</div>`;
}

function audienceRepeatSummary(network, communities) {
  const repeatCommenters = Number(network.n_nodes || 0);
  const groupCount = Number(network.n_communities || communities.length || 0);
  const largestShare = Number(communities[0]?.pct_nodes || 0);
  const top3Share = communities
    .slice(0, 3)
    .reduce((sum, row) => sum + Number(row.pct_nodes || 0), 0);
  return `
    <div class="metric-strip audience-summary">
      ${metricTile("跨影片回來留言者", repeatCommenters, "n")}
      ${metricTile("可辨識內容偏好群", groupCount, "n")}
      ${metricTile("最大偏好群占比", largestShare, "pct")}
      ${metricTile("前三偏好群占比", top3Share, "pct")}
    </div>
  `;
}

function videoPortfolioSummary(network, clusters) {
  const analyzedVideos = Number(network.n_nodes || 0) || clusters.reduce((sum, row) => sum + Number(row.n_videos || 0), 0);
  const seriesCount = Number(network.n_video_clusters || clusters.length || 0);
  const totalVideos = clusters.reduce((sum, row) => sum + Number(row.n_videos || 0), 0) || analyzedVideos;
  const largestSeriesVideos = clusters.length ? Math.max(...clusters.map((row) => Number(row.n_videos || 0))) : 0;
  const largestSeriesShare = totalVideos ? (largestSeriesVideos / totalVideos) * 100 : 0;
  const totalComments = clusters.reduce((sum, row) => sum + Number(row.total_observed_comments || 0), 0);
  const top3CommentShare = totalComments
    ? (clusters.slice(0, 3).reduce((sum, row) => sum + Number(row.total_observed_comments || 0), 0) / totalComments) * 100
    : 0;
  return `
    <div class="metric-strip video-summary">
      ${metricTile("納入分析影片", analyzedVideos, "n")}
      ${metricTile("內容系列數", seriesCount, "n")}
      ${metricTile("最大系列影片占比", largestSeriesShare, "pct")}
      ${metricTile("前三系列留言占比", top3CommentShare, "pct")}
    </div>
  `;
}

function audienceStructureCards(network) {
  const cards = [];
  const hhi = Number(network.community_concentration_hhi);
  if (Number.isFinite(hhi)) {
    const pr = Number(baselineMetric("community_hhi")?.percentile);
    const band = prBand(pr, ["偏低", "中等", "偏高"]);
    const text = {
      偏高: "你的活躍留言者主要集中在少數幾個共同留言群。建議優先理解主力觀眾群偏好的內容與敏感主題。",
      中等: "活躍留言者分布在數個共同留言群，集中度中等；可同時經營主力群與次要群。",
      偏低: "活躍留言者分散在較多群、沒有明顯主導群，社群相對分散。",
    }[band];
    cards.push(
      structureCard(
        "觀眾集中度",
        band,
        `HHI ${hhi.toFixed(2)}`,
        pr,
        text,
        band === "偏高" ? "warn" : "",
        "觀眾集中度＝community HHI＝各社群占比的平方和（Σ share²）。算法：把每個社群占活躍留言者的比例平方後加總，越接近 1＝越集中在少數大群、越接近 0＝越分散在多群。對照 cohort 百分位定偏高/中等/偏低。",
      ),
    );
  }
  const mod = Number(network.modularity);
  if (Number.isFinite(mod)) {
    const pr = Number(baselineMetric("commenter_network_modularity")?.percentile);
    const band = prBand(pr, ["低", "中", "高"]);
    const text = {
      高: "相對多數頻道，你的留言者分得比較開（PR 高）；但因為大家都看同一頻道、觀眾天生重疊，社群比較像『軟性偏好傾向』而非壁壘分明的派系，別把群當成互不相干的鐵票。",
      中: "留言者的分群結構中等清楚，群與群之間仍有不少交集。",
      低: "留言者之間交集很多、分群界線不明顯，比較難切出清楚的觀眾群。",
    }[band];
    cards.push(
      structureCard(
        "分群清晰度",
        band,
        `modularity ${mod.toFixed(2)} · ${fmtNumber(network.n_communities)} 群`,
        pr,
        text,
        "",
        "分群清晰度＝modularity（Q）。算法：把『留言者-留言者』網路（邊＝兩人在同一支影片共同留言、權重＝共享影片數）用 Louvain 自動分群，Q＝Σ各群（實際落在群內的邊比例 − 隨機重連、但保留每人連結度數時的期望比例）。比的是隨機重連的圖、不是 random walk。Q 介於 0~1，慣例 0.3–0.7 才算有明顯結構；單一頻道的觀眾天生重疊，本 cohort 中位數僅約 0.22，所以這裡的高/中/低是『相對同行』，不是絕對乾淨的分割。",
        "⚠ 這是「軟性偏好傾向」，不是硬性分群：成員大量重疊（同一人會看多種題材、跨群留言），別把每個群當成互不相干的鐵票或派系。",
      ),
    );
  }
  if (!cards.length) return "";
  return `<div class="structure-card-grid">${cards.join("")}</div>`;
}

function prBand(pr, labels) {
  if (!Number.isFinite(pr)) return labels[1];
  if (pr >= 66.7) return labels[2];
  if (pr >= 33.3) return labels[1];
  return labels[0];
}

function structureCard(title, band, valueText, pr, text, tone = "", tip = "", note = "") {
  return `
    <article class="structure-card ${tone}">
      <div class="structure-card-head">
        <strong>${escapeHtml(title)}${tip ? " " + infoTip(tip) : ""}</strong>
        <span class="structure-band">${escapeHtml(band)}</span>
      </div>
      <div class="structure-card-meta">${escapeHtml(valueText)}${Number.isFinite(pr) ? ` · PR ${Math.round(pr)}` : ""}</div>
      <p>${escapeHtml(text)}</p>
      ${note ? `<p class="structure-note">${escapeHtml(note)}</p>` : ""}
    </article>`;
}

function personaAspectChart(label, items, aspectLabels = {}) {
  const rows = (items || []).filter((item) => item.aspect && !NON_IMPACT_ASPECTS.has(item.aspect)).slice(0, 4);
  if (!rows.length) return "";
  const max = Math.max(...rows.map((row) => row.share || 0), 0.01);
  return `
    <div class="persona-chart">
      <span class="persona-chart-label">${escapeHtml(label)}</span>
      <div class="persona-chart-rows">
        ${rows
          .map(
            (row) => `
          <div class="persona-chart-row">
            <span class="persona-chart-name" title="${escapeHtml(aspectLabels[row.aspect] || row.aspect)}">${escapeHtml(aspectLabels[row.aspect] || row.aspect)}</span>
            <div class="persona-bar"><i class="neg" style="width:${Math.max(3, (row.share / max) * 100).toFixed(0)}%"></i></div>
            <span class="persona-chart-val">${formatValue(row.share, "rate")}</span>
          </div>`,
          )
          .join("")}
      </div>
    </div>`;
}

function communityPersonaCards(rows, channelThemeNeg = {}, communityAspectMap = {}, aspectLabels = {}) {
  const fallbackRows = currentChannel.dashboard_summary?.audience_segment_profiles || [];
  const usable = (rows?.length ? rows : fallbackRows).filter(
    (row) =>
      row.persona_name ||
      row.segment_name ||
      row.segment_label ||
      row.top_preferred_themes ||
      row.preferred_video_themes ||
      row.preferred_themes ||
      row.distinctive_keywords ||
      row.common_keywords,
  );
  if (!usable.length) {
    return `<div class="empty-state">重跑新版分析後，這裡會顯示觀眾類型、關鍵字、代表留言與商業建議。</div>`;
  }
  const shown = usable.slice(0, 6);
  const pctOf = (row) =>
    Number(row.pct_active_commenters ?? row.group_size?.pct_active_commenters ?? row.segment_share) || 0;
  const usedNames = new Map();
  return `<div class="persona-grid">${shown
    .map((row, idx) => {
      const name = uniquePersonaDisplayName(personaDisplayName(row, idx), row, idx, usedNames);
      const pctActive = row.pct_active_commenters ?? row.group_size?.pct_active_commenters ?? row.segment_share;
      const nCommenters = row.group_size?.n_commenters ?? row.n_commenters;
      const avgComments = row.avg_comments_per_commenter ?? row.activity?.avg_comments_per_commenter;
      const nVideosTouched = row.activity?.n_videos_touched;
      const nComments = row.activity?.n_comments;
      // Absolute group share (% of active commenters), so the bar length = the
      // actual percentage — a 44.7% group fills ~44.7%, not "full because it is the biggest".
      const barWidth = Math.max(2, Math.min(100, pctOf(row)));
      const details = [
        personaThemeChart("特別活躍題材（lift＞1＝相對全頻道更投入）", row.over_indexed_themes, {
          valueKey: "lift",
          format: (it) => `${(Number(it.lift) || 0).toFixed(2)}×`,
        }),
        personaVideoList("代表影片", row.preferred_videos),
        personaKeywordChips(row.common_keywords),
        personaLine("策略用途", personaBusinessAdvice(row)),
        personaQuote(representativeText(row.representative_comments)),
      ].join("");
      return `
        <article class="persona-card">
          <div class="persona-head">
            <strong>${escapeHtml(name)}</strong>
            <span>${formatValue(pctActive, "pct_active_commenters")} 活躍留言者</span>
          </div>
          <div class="persona-size">
            <div class="persona-size-head">
              <span>群體大小</span>
              <strong>${formatValue(pctActive, "pct_active_commenters")}${nCommenters ? ` · ${fmtCompact(nCommenters)} 人` : ""}</strong>
            </div>
            <div class="persona-bar"><i style="width:${barWidth.toFixed(1)}%"></i></div>
            <div class="persona-stat-line">${Number.isFinite(Number(nVideosTouched)) ? `觸及 ${fmtCompact(nVideosTouched)} 支影片 · ` : ""}留言 ${fmtCompact(nComments)} · 活躍 ${formatValue(avgComments, "avg_comments_per_commenter")} 次/人</div>
          </div>
          ${personaSentimentBar(row.main_sentiment)}
          ${personaSensitivityLine(row)}
          ${personaLine("偏好題材", row.top_preferred_themes || row.preferred_video_themes || labelCountList(row.preferred_themes))}
          ${
            details.trim()
              ? `<details class="persona-more"><summary>展開觀眾輪廓與策略</summary><div class="persona-more-body">${details}</div></details>`
              : ""
          }
        </article>`;
    })
    .join("")}</div>`;
}

function personaSensitivityLine(row) {
  const top = (row.over_indexed_themes || [])[0];
  const parts = [];
  if (top && top.theme) {
    parts.push(`<span class="sens-pos">特別投入：${escapeHtml(themeLabel(top.theme))} ${(Number(top.lift) || 0).toFixed(2)}×</span>`);
  }
  if (!parts.length) return "";
  return `<div class="persona-sensitivity">${parts.join("")}</div>`;
}

function personaVideoList(label, videos) {
  const items = (videos || []).slice(0, 3).filter((v) => v && (v.label || v.title));
  if (!items.length) return "";
  return `
    <div class="persona-chart">
      <span class="persona-chart-label">${escapeHtml(label)}</span>
      <div class="persona-video-list">
        ${items
          .map(
            (v) =>
              `<span title="${escapeHtml(v.label || v.title)}">${escapeHtml(v.label || v.title)}${Number.isFinite(Number(v.count)) ? ` · ${fmtCompact(v.count)} 留言` : ""}</span>`,
          )
          .join("")}
      </div>
    </div>`;
}

function personaSentimentBar(ms) {
  if (!ms) return "";
  const pos = Number(ms.positive_rate) || 0;
  const neu = Number(ms.neutral_rate) || 0;
  const neg = Number(ms.negative_rate) || 0;
  const total = pos + neu + neg;
  if (total <= 0) return "";
  const pct = (value) => ((value / total) * 100).toFixed(1);
  return `
    <div class="persona-chart">
      <span class="persona-chart-label">社群情緒</span>
      <div class="persona-sentbar">
        <i class="positive" style="width:${pct(pos)}%"></i>
        <i class="neutral" style="width:${pct(neu)}%"></i>
        <i class="negative" style="width:${pct(neg)}%"></i>
      </div>
      <div class="persona-sent-legend">
        <span><i class="positive"></i>正 ${formatValue(pos, "rate")}</span>
        <span><i class="neutral"></i>中 ${formatValue(neu, "rate")}</span>
        <span><i class="negative"></i>負 ${formatValue(neg, "rate")}</span>
      </div>
    </div>`;
}

function personaThemeChart(label, rows, opts = {}) {
  const items = (rows || [])
    .slice(0, opts.limit || 5)
    .map((item) => ({
      name: themeLabel(item.label || item.theme || item.name || ""),
      value: Number(opts.valueKey ? item[opts.valueKey] : item.count) || 0,
      display: opts.format ? opts.format(item) : fmtCompact(item.count),
      tone: opts.tone || "",
    }))
    .filter((it) => it.name && it.value > 0);
  if (!items.length) return "";
  const max = Math.max(...items.map((it) => it.value));
  return `
    <div class="persona-chart">
      <span class="persona-chart-label">${escapeHtml(label)}</span>
      <div class="persona-chart-rows">
        ${items
          .map(
            (it) => `
          <div class="persona-chart-row">
            <span class="persona-chart-name" title="${escapeHtml(it.name)}">${escapeHtml(it.name)}</span>
            <div class="persona-bar"><i class="${it.tone}" style="width:${Math.max(3, (it.value / max) * 100).toFixed(1)}%"></i></div>
            <span class="persona-chart-val">${escapeHtml(it.display)}</span>
          </div>`,
          )
          .join("")}
      </div>
    </div>`;
}

function personaKeywordChips(value) {
  const values = Array.isArray(value?.values) ? value.values : Array.isArray(value) ? value : [];
  const chips = values.filter(Boolean).slice(0, 10);
  if (!chips.length) return "";
  const note = value?.limitation_zh ? `<em class="persona-chart-note">${escapeHtml(value.limitation_zh)}</em>` : "";
  return `
    <div class="persona-chart">
      <span class="persona-chart-label">常見關鍵字</span>
      <div class="persona-chips">${chips.map((v) => `<span>${escapeHtml(String(v))}</span>`).join("")}</div>
      ${note}
    </div>`;
}

function uniquePersonaDisplayName(baseName, row, idx, usedNames) {
  const base = baseName || `觀眾類型 ${idx + 1}`;
  const count = usedNames.get(base) || 0;
  usedNames.set(base, count + 1);
  if (count === 0) return base;
  const themes = personaThemeKeys(row);
  const phrase = themes.slice(0, 2).map(themeLabel).filter(Boolean).join(" × ");
  const specific = phrase ? `${phrase}型觀眾` : `觀眾類型 ${idx + 1}`;
  if (!usedNames.has(specific)) {
    usedNames.set(specific, 1);
    return specific;
  }
  return `${specific} ${count + 1}`;
}

function personaDisplayName(row, idx) {
  const themes = personaThemeKeys(row);
  if (themes.some((theme) => ["survival_outdoor", "physical_challenge"].includes(theme))) return "挑戰冒險型觀眾";
  if (themes.some((theme) => ["education_advice", "workplace_tech_career"].includes(theme))) return "知識職涯型觀眾";
  if (themes.some((theme) => ["guest_relationship", "travel_exploration"].includes(theme))) return "旅遊來賓型觀眾";
  if (themes.some((theme) => ["business_brand", "product_review"].includes(theme))) return "品牌合作敏感型觀眾";
  if (themes.includes("controversy_response")) return "爭議議題型觀眾";
  if (themes.includes("personal_team_life")) return "團隊日常型觀眾";
  const raw = row.persona_name || row.segment_name || "";
  return raw && !/^Audience segment/i.test(raw) ? raw : `觀眾類型 ${idx + 1}`;
}

function personaThemeKeys(row) {
  const focused = [];
  if (Array.isArray(row.over_indexed_themes) && row.over_indexed_themes.length) {
    row.over_indexed_themes.slice(0, 3).forEach((item) => {
      const value = item?.theme || item?.label || item?.name;
      if (value) focused.push(String(value));
    });
    return Array.from(new Set(focused.filter((value) => value.includes("_"))));
  }
  const values = [];
  const collect = (items, key = "theme") => {
    if (!Array.isArray(items)) return;
    items.slice(0, 3).forEach((item) => {
      const value = item?.[key] || item?.label || item?.theme || item?.name;
      if (value) values.push(String(value));
    });
  };
  collect(row.preferred_themes);
  collect(row.top_preferred_themes);
  collect(row.preferred_video_themes);
  return Array.from(new Set(values.filter((value) => value.includes("_"))));
}

function overIndexedThemeText(value, limit = 3) {
  if (!Array.isArray(value) || !value.length) return "";
  return value
    .slice(0, limit)
    .map((item) => `${themeLabel(item.theme)} ${formatValue(item.lift, "lift")}`)
    .join("、");
}

function personaBusinessAdvice(row) {
  const themes = personaThemeKeys(row);
  const negatives = Array.isArray(row.negative_sources) ? row.negative_sources.slice(0, 2).map((item) => themeLabel(item.theme)).filter(Boolean) : [];
  const caution = negatives.length ? `需注意${negatives.join("、")}相關負面來源。` : "需持續追蹤負面來源是否集中在特定題材。";
  if (themes.some((theme) => ["survival_outdoor", "physical_challenge"].includes(theme))) {
    return `適合挑戰任務、戶外系列、體能或企劃型合作；重點是保留過程證據與剪輯節奏，避免真實性被質疑。${caution}`;
  }
  if (themes.some((theme) => ["education_advice", "workplace_tech_career"].includes(theme))) {
    return `適合做經驗拆解、職涯故事、工具或課程型內容；合作訊息要有清楚資訊量，避免被看成空泛宣傳。${caution}`;
  }
  if (themes.some((theme) => ["guest_relationship", "travel_exploration"].includes(theme))) {
    return `適合目的地合作、文化體驗、來賓互動與系列旅行企劃；商業訊息應和體驗自然結合。${caution}`;
  }
  if (themes.some((theme) => ["business_brand", "product_review"].includes(theme))) {
    return `適合品牌教育、產品比較與轉換型內容；必須明確標示合作關係並提供可驗證資訊。${caution}`;
  }
  if (themes.includes("controversy_response")) {
    return `適合用於議題回應、澄清與價值觀溝通；內容需要先處理事實脈絡，再談立場。${caution}`;
  }
  return `適合延伸既有高互動題材，先用小型系列測試，再觀察留言率、回訪率與負面來源。${caution}`;
}

function personaLine(label, value) {
  if (!value) return "";
  return `
    <div class="persona-line">
      <span>${escapeHtml(label)}</span>
      <p>${escapeHtml(formatPersonaText(value))}</p>
    </div>`;
}

function personaQuote(value) {
  if (!value) return "";
  return `
    <div class="persona-line">
      <span>代表留言</span>
      <blockquote>${escapeHtml(formatPersonaText(value))}</blockquote>
    </div>`;
}

function formatPersonaText(value) {
  return localizeDisplayText(String(value || "").replaceAll("; ", "、").replaceAll(" of active commenters", " 活躍留言者"));
}

function localizeDisplayText(value) {
  let text = String(value || "");
  Object.entries(themeMap()).forEach(([key, label]) => {
    const pattern = new RegExp(`(^|[^A-Za-z0-9_])${escapeRegExp(key)}(?=$|[^A-Za-z0-9_])`, "g");
    text = text.replace(pattern, (_, prefix) => `${prefix}${label}`);
  });
  return text
    .replace(/\bPR\s*([0-9.]+)/g, "百分位 $1")
    .replace(/\bbenchmark\b/gi, "比較基準")
    .replace(/\bbaseline\b/gi, "基準")
    .replace(/\bABSA\b/g, "面向分析")
    .replace(/\bAI\b/g, "模型");
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function labelCountList(value, limit = 5) {
  if (Array.isArray(value)) {
    return value
      .slice(0, limit)
      .map((item) => {
        const raw = item.label || item.theme || item.name || "";
        return raw.includes("_") ? themeLabel(raw) : raw;
      })
      .filter(Boolean)
      .join("、");
  }
  return value || "";
}

function valueList(value, limit = 8) {
  if (Array.isArray(value)) return value.slice(0, limit).join("、");
  if (value?.values) return value.values.slice(0, limit).join("、");
  return value || "";
}

function negativeSourceText(value, limit = 3) {
  if (Array.isArray(value)) {
    return value
      .slice(0, limit)
      .map((item) => {
        const theme = themeLabel(item.theme || item.label || "");
        const neg = formatValue(item.negative_rate, "rate");
        const likeNeg = formatValue(item.like_weighted_negative_rate, "rate");
        return `${theme}：負面 ${neg}，按讚加權負面 ${likeNeg}`;
      })
      .filter(Boolean)
      .join("；");
  }
  return value || "";
}

function representativeText(value) {
  if (Array.isArray(value)) return value.slice(0, 2).join(" / ");
  if (value?.values?.length) return value.values.slice(0, 2).join(" / ");
  if (value?.status === "missing_current_artifact") return "";
  return value || "";
}

function communityBars(rows) {
  if (!rows.length) return `<div class="empty-state">沒有內容偏好群資料</div>`;
  return `<div class="community-grid">${rows
    .slice(0, 8)
    .map((row, idx) => {
      const pct = Number(row.pct_nodes || 0);
      return `
      <div class="community-cell">
        <strong>內容偏好群 ${idx + 1}</strong>
        <span>${fmtNumber(row.n_nodes)} 位跨影片留言者</span>
        <div class="community-bar"><i style="width:${Math.max(4, Math.min(100, pct))}%"></i></div>
        <em>占 ${formatValue(pct, "pct_nodes")}</em>
      </div>`;
    })
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

async function tableFromArtifactOrSummary(tableName, columns) {
  const summary = currentChannel.dashboard_summary || {};
  const summaryMap = {
    sentiment_theme_summary: summary.top_themes,
    community_sentiment_summary: summary.community_summary,
    reply_conflict_video_summary: summary.reply_conflict_hotspots,
    video_cluster_summary: summary.video_clusters,
  };
  if (summaryMap[tableName]?.length) {
    return tableFromRows(summaryMap[tableName], columns);
  }
  const artifact = (currentChannel.artifacts?.tables || []).find((table) => table.name === tableName);
  if (!artifact) {
    return `<div class="empty-state">目前沒有 ${escapeHtml(tableName)} 資料</div>`;
  }
  try {
    const data = await fetchJson(`/api/table/${encodeURIComponent(currentChannel.slug)}/${encodeURIComponent(tableName)}?limit=12`);
    if (data.rows?.length) {
      return tableFromRows(data.rows, columns);
    }
  } catch {
    // Fall through to the artifact hint below.
  }
  return `
    <div class="artifact-hint">
      <strong>${escapeHtml(tableName)}</strong>
      <span>這張完整資料表目前不在本機輕量版資料夾裡；補回完整分析輸出後，這裡會直接顯示表格。</span>
    </div>
  `;
}

function tabAvailable(tabId) {
  const tabs = currentChannel.tabs || [];
  const match = tabs.find((tab) => tab.id === tabId);
  return Boolean(match?.available);
}

async function getVideoRows() {
  if (videoRowsCache) return videoRowsCache;
  try {
    const data = await fetchJson(`/api/table/${encodeURIComponent(currentChannel.slug)}/video_metrics?limit=800`);
    videoRowsCache = data.rows || [];
  } catch {
    videoRowsCache = [];
  }
  return videoRowsCache;
}

async function fetchTableRows(tableName, limit = 12) {
  try {
    const data = await fetchJson(`/api/table/${encodeURIComponent(currentChannel.slug)}/${encodeURIComponent(tableName)}?limit=${limit}`);
    return data.rows || [];
  } catch {
    return [];
  }
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
  const labels = {
    top_level_comments: "主留言數（不含回覆）",
    top_level_commenters: "主留言者數（不重複）",
  };
  return labels[metric] || indexData.dashboard_statistics?.metric_labels?.[metric] || metric;
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
  if (key === "video_cluster") return videoClusterLabel(value);
  if (key === "opportunity_type") return opportunityTypeLabel(value);
  if (String(key).includes("theme")) return themeLabel(value);
  const n = Number(value);
  if (key === "pp") return Number.isFinite(n) ? `${n.toFixed(1)} 個百分點` : String(value);
  if (key === "lift") return Number.isFinite(n) ? `${n.toFixed(2)} 倍` : String(value);
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

function setupChartTooltip() {
  if (document.querySelector(".chart-tooltip")) return;
  const tip = document.createElement("div");
  tip.className = "chart-tooltip";
  tip.hidden = true;
  document.body.appendChild(tip);
  let active = null;

  const tooltipTarget = (node) => {
    if (!(node instanceof Element)) return null;
    return node.closest("[data-chart-tooltip]");
  };

  const move = (event) => {
    const pad = 14;
    const maxX = window.innerWidth - tip.offsetWidth - 12;
    const maxY = window.innerHeight - tip.offsetHeight - 12;
    tip.style.left = `${Math.max(12, Math.min(maxX, event.clientX + pad))}px`;
    tip.style.top = `${Math.max(12, Math.min(maxY, event.clientY + pad))}px`;
  };

  document.addEventListener("pointerover", (event) => {
    const target = tooltipTarget(event.target);
    if (!target) return;
    active = target;
    tip.innerHTML = escapeHtml(target.dataset.chartTooltip || "").replaceAll("\n", "<br>");
    tip.hidden = false;
    move(event);
  });
  document.addEventListener("pointermove", (event) => {
    if (!active) return;
    move(event);
  });
  document.addEventListener("pointerout", (event) => {
    if (!active) return;
    const next = tooltipTarget(event.relatedTarget);
    if (next === active) return;
    active = null;
    tip.hidden = true;
  });
}

function tooltipAttr(value) {
  return escapeHtml(value).replaceAll("\n", "&#10;");
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
    subscriber_count: "訂閱數",
    channel_view_count_api: "頻道總觀看",
    channel_video_count_api: "頻道總影片",
    total_views_in_scope: "分析範圍觀看",
    total_video_comment_count_api: "YouTube 顯示留言數",
    custom_url: "頻道",
    country: "地區",
    crawl_time: "資料擷取時間",
    date_min: "分析起始",
    date_max: "分析結束",
    like_count: "按讚",
    negative_rate: "負面率",
    like_weighted_negative_rate: "按讚加權負面",
    primary_theme: "主題",
    conflict_score: "衝突分數",
    reply_count_weighted_conflict_score: "回覆量加權",
    like_weighted_conflict_score: "按讚加權",
    metric: "指標",
    value: "數值",
    source: "資料來源",
    community: "內容偏好群",
    theme_label: "題材",
    community_share: "偏好群內占比",
    video_cluster: "內容系列",
    cluster_share: "系列內占比",
    overall_share: "全頻道占比",
    lift: "高於平均倍數",
    opportunity_type: "機會類型",
    opportunity_score: "機會分數",
    source_primary_theme: "來源題材",
    target_primary_theme: "目標題材",
    source_title: "來源影片",
    target_title: "目標影片",
    persona_name: "觀眾類型",
    persona_summary: "類型摘要",
    pct_active_commenters: "群體大小",
    avg_comments_per_commenter: "平均留言次數",
    top_preferred_themes: "偏好題材",
    top_comment_videos: "偏好影片",
    distinctive_keywords: "常見關鍵字",
    sentiment_profile: "主要情緒",
    negative_drivers: "負面來源",
    representative_comments: "代表留言",
    business_recommendation: "商業建議",
    n_comments: "留言數",
    positive_rate: "正面率",
  };
  return map[key] || String(key || "").replaceAll("_", " ");
}

function videoClusterLabel(value, fallbackIndex = null, row = null) {
  const clusters = currentChannel?.dashboard_summary?.video_clusters || [];
  const displayIndex = clusters.findIndex((row) => String(row.video_cluster) === String(value));
  const profile = row || (displayIndex >= 0 ? clusters[displayIndex] : null);
  const name = profile ? videoClusterName(profile) : "";
  if (name) return name;
  if (displayIndex >= 0) return `未命名內容系列 ${displayIndex + 1}`;
  if (Number.isInteger(fallbackIndex) && fallbackIndex >= 0) return `未命名內容系列 ${fallbackIndex + 1}`;
  const n = Number(value);
  if (Number.isInteger(n) && n >= 0) return `未命名內容系列 ${n + 1}`;
  return String(value || "未分組");
}

function videoClusterName(row) {
  const themes = clusterThemeKeys(row);
  const themePhrase = clusterThemePhrase(themes);
  const period = clusterPeriodLabel(row);
  if (period && themePhrase) return `${period}：${themePhrase}`;
  return themePhrase;
}

function clusterThemeKeys(row, limit = 5) {
  const topicThemes = row.topic_from_title_description_tags?.top_themes || [];
  const raw = topicThemes.length ? topicThemes : parseLabelCountText(row.top_theme_labels || row.top_primary_themes || "");
  return raw
    .map((item) => String(item.theme || item.label || item.name || "").trim())
    .filter(Boolean)
    .slice(0, limit);
}

function clusterThemePhrase(themes) {
  const keys = new Set(themes);
  const primary = themes[0];
  const secondary = themes[1];
  const tertiary = themes[2];
  if (primary === "travel_exploration" && secondary === "personal_team_life" && tertiary === "guest_relationship") return "跨國旅遊與來賓互動";
  if (primary === "travel_exploration" && secondary === "personal_team_life") {
    if (keys.has("workplace_tech_career") || keys.has("education_advice")) return "旅行、團隊日常與職涯經驗";
    return "旅行與團隊日常";
  }
  if (primary === "travel_exploration" && (secondary === "physical_challenge" || keys.has("survival_outdoor"))) return "旅行挑戰與來賓互動";
  if (keys.has("guest_relationship") && keys.has("travel_exploration")) return "跨國旅遊與來賓互動";
  if (keys.has("survival_outdoor") || keys.has("physical_challenge")) return "挑戰任務與體能企劃";
  if ((keys.has("workplace_tech_career") || keys.has("education_advice")) && keys.has("travel_exploration")) return "旅行與職涯經驗";
  if (keys.has("workplace_tech_career") || keys.has("education_advice")) return "職涯科技與經驗分享";
  if (keys.has("personal_team_life") && keys.has("travel_exploration")) return "旅行與團隊日常";
  if (keys.has("business_brand") || keys.has("product_review")) return "品牌合作與產品體驗";
  if (keys.has("controversy_response")) return "爭議回應與議題內容";
  const labels = themes.slice(0, 2).map(themeLabel).filter(Boolean);
  return labels.length ? labels.join(" × ") : "";
}

function clusterPeriodLabel(row) {
  const start = row.date_min || row.size?.date_min || row.metadata?.date_min;
  const end = row.date_max || row.size?.date_max || row.metadata?.date_max;
  if (!start || !end) return "";
  const startYear = Number(String(start || "").slice(0, 4));
  const endYear = Number(String(end || "").slice(0, 4));
  if (!Number.isFinite(startYear) || !Number.isFinite(endYear) || startYear <= 0 || endYear <= 0) return "";
  return startYear === endYear ? `${startYear}` : `${startYear}-${endYear}`;
}

function opportunityTypeLabel(value) {
  const map = {
    latent_cross_cluster_bridge: "潛在跨系列橋接",
    cross_cluster_theme_bridge: "跨系列題材橋接",
    same_cluster_cross_theme_extension: "同系列跨題材延伸",
    within_cluster_theme_blend: "同系列跨題材延伸",
    same_theme_cross_cluster_bridge: "同題材跨系列延伸",
    same_cluster_same_theme_link: "同系列同題材推薦",
    underconnected_similar_audience: "相似觀眾導流",
  };
  return map[value] || String(value || "企劃機會").replaceAll("_", " ");
}

function themeLabel(value) {
  const map = themeMap();
  return map[value] || String(value || "未標註");
}

function themeMap() {
  return {
    controversy_response: "爭議回應",
    personal_team_life: "個人/團隊生活",
    travel_exploration: "旅遊探索",
    food_culture: "飲食文化",
    business_brand: "商業/品牌",
    education_advice: "教育/建議",
    automotive_luxury: "車與生活風格",
    city_lifestyle: "城市生活",
    event_announcement: "活動公告",
    guest_relationship: "來賓互動",
    physical_challenge: "體能挑戰",
    product_review: "產品評測",
    survival_outdoor: "戶外求生",
    workplace_tech_career: "職涯/科技",
    other: "其他",
  };
}

function tierLabel(value) {
  return {
    core: "核心觀眾",
    regular: "常客",
    returning: "回訪",
    one_time: "一次性/路過",
    high: "高頻核心",
    mid: "中頻觀眾",
    low: "低頻/一次性",
  }[value] || value;
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
  // Use the global cursor-following tooltip (setupChartTooltip), which clamps to
  // the viewport, so tooltips near the left/right edge never get cut off.
  return `<span class="info-tip" tabindex="0" data-chart-tooltip="${tooltipAttr(body)}" aria-label="${escapeHtml(body)}">?</span>`;
}

function scoreline(indices) {
  return indices
    .slice(0, 6)
    .map((item) => `<span>${escapeHtml(item.short_label || item.label)} <strong>${fmtScore(item.score)}</strong></span>`)
    .join("");
}

init().catch((err) => {
  document.body.innerHTML = `<main class="fatal"><h1>分析頁載入失敗</h1><pre>${escapeHtml(err.stack || err.message || err)}</pre></main>`;
});
