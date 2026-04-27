const API = "/api";
const EMO_ICONS = { neutral: "😐", anger: "😡", disgust: "🤢", fear: "😨", happiness: "😊", sadness: "😢", surprise: "😲" };
const EMO_COLORS = { neutral: "#94a3b8", anger: "#f87171", disgust: "#a3e635", fear: "#fbbf24", happiness: "#34d399", sadness: "#7dd3fc", surprise: "#a78bfa" };
let currentSessionId = null, isAnon = false;
function getToken() { return localStorage.getItem("serenity_token") }
function getUser() { try { return JSON.parse(localStorage.getItem("serenity_user") || "{}") } catch { return {} } }
function authHeaders() { return { "Content-Type": "application/json", "Authorization": "Bearer " + getToken() } }

// Initialize UI
async function initChat() {
  try {
    console.log("Serenity: Initializing chat...");
    if (!getToken()) {
      console.warn("No token found, redirecting to login.");
      window.location.href = "/login.html";
      return;
    }

    const params = new URLSearchParams(window.location.search);
    isAnon = params.get("anon") === "true";
    const user = getUser();
    
    // Update user info
    const nameEl = document.getElementById("user-display-name");
    const avatarEl = document.getElementById("user-avatar-letter");
    const tagEl = document.getElementById("user-tag");
    
    if (nameEl) nameEl.textContent = user.username || "Friend";
    if (avatarEl) avatarEl.textContent = (user.username || "S")[0].toUpperCase();
    if (tagEl) tagEl.textContent = isAnon ? "anonymous session" : "wellness companion";

    const textarea = document.getElementById("chat-input");
    if (textarea) {
      textarea.addEventListener("input", () => {
        const sendBtn = document.getElementById("send-btn");
        if (sendBtn) sendBtn.disabled = !textarea.value.trim();
        const charCount = document.getElementById("char-count");
        if (charCount) charCount.textContent = textarea.value.length + " / 2000";
      });
    }

    await loadSessions();
    console.log("Serenity: Initialization complete.");
  } catch (e) {
    console.error("Serenity: Initialization error:", e);
  }
}

// Run init
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initChat);
} else {
  initChat();
}

function logout() {
  localStorage.removeItem("serenity_token");
  localStorage.removeItem("serenity_user");
  window.location.href = "/";
}

function toggleSidebar() {
  const sb = document.getElementById("sidebar");
  const ov = document.getElementById("sidebar-overlay");
  sb.classList.toggle("open");
  ov.classList.toggle("active");
}

function showView(name) {
  document.querySelectorAll(".view").forEach(v => { v.style.display = "none"; v.classList.remove("active") });
  const v = document.getElementById("view-" + name);
  v.style.display = "flex"; v.classList.add("active");
  document.querySelectorAll(".sidebar-link").forEach(l => l.classList.remove("active"));
  document.getElementById("nav-" + name).classList.add("active");
  if (name === "dashboard") loadDashboard("daily");
  if (name === "history") loadHistory();
}

async function loadSessions() {
  try {
    const r = await fetch(API + "/chat/sessions", { headers: authHeaders() });
    const sessions = await r.json();
    const list = document.getElementById("session-list");
    if (!list) return;
    
    if (!Array.isArray(sessions) || !sessions.length) { 
      list.innerHTML = "<div class=\"loading-placeholder\">No sessions yet</div>"; 
      return; 
    }
    
    list.innerHTML = sessions.slice(0, 15).map(s => `
      <div class="session-item" id="session-item-${s.id}" onclick="loadSession(${s.id})">
        <div class="session-info">
          <div>${(s.session_title || "Check-in").replace("Evening Check-in — ", "")}</div>
          <div class="session-item-date">${s.started_at ? new Date(s.started_at).toLocaleDateString() : ""}</div>
        </div>
        <button class="delete-session-btn" onclick="handleDeleteSession(event, ${s.id})" title="Delete session">🗑️</button>
      </div>`).join("");
  } catch (e) { console.error(e) }
}

async function newSession() {
  try {
    const r = await fetch(API + "/chat/session/start", { method: "POST", headers: authHeaders() });
    const s = await r.json();
    currentSessionId = s.id;
    showView("chat");
    document.getElementById("messages-area").innerHTML = "<div class=\"welcome-state\" id=\"welcome-state\"><div class=\"welcome-icon\">✨</div><h2 class=\"welcome-title\">A new check-in</h2><p class=\"welcome-subtitle\">Serenity is ready to listen.</p><button class=\"btn btn-primary btn-large\" onclick=\"beginCheckin()\">Begin ✨</button></div>";
    document.getElementById("topbar-session-name").textContent = s.session_title.replace("Evening Check-in — ", "");
    loadSessions();
  } catch (e) { console.error(e) }
}

async function beginCheckin() {
  const area = document.getElementById("messages-area");
  area.innerHTML = "";
  showTyping(true);
  if (!currentSessionId) {
    try {
      const r = await fetch(API + "/chat/session/start", { method: "POST", headers: authHeaders() });
      const s = await r.json();
      currentSessionId = s.id;
      document.getElementById("topbar-session-name").textContent = s.session_title.replace("Evening Check-in — ", "");
    } catch (e) { console.error(e) }
  }
  try {
    const r = await fetch(API + "/chat/opening/" + currentSessionId, { headers: authHeaders() });
    const d = await r.json();
    showTyping(false);
    appendMessage("assistant", d.message, new Date().toISOString());
    enableInput(true);
    loadSessions();
  } catch (e) { showTyping(false); appendMessage("assistant", "Good evening! I'\''m Serenity. How are you feeling tonight? ??", new Date().toISOString()); enableInput(true) }
}
async function sendMessage() {
  const inp = document.getElementById("chat-input");
  const text = inp.value.trim();
  if (!text || !currentSessionId) return;
  inp.value = ""; inp.style.height = "auto";
  document.getElementById("send-btn").disabled = true;
  document.getElementById("char-count").textContent = "0 / 2000";
  appendMessage("user", text, new Date().toISOString());
  showTyping(true);
  try {
    const r = await fetch(API + "/chat/message", {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ content: text, session_id: currentSessionId })
    });
    const d = await r.json();
    showTyping(false);
    appendMessage("assistant", d.message, new Date().toISOString());
    updateEmotionDisplay(d.emotion_scores, d.dominant_emotion);
    if (d.wellness_tip) showWellnessTip(d.wellness_tip);
    if (d.crisis_alert) document.getElementById("crisis-modal").style.display = "flex";
  } catch (e) { showTyping(false); appendMessage("assistant", "I'm here with you. Please try again in a moment. ??", new Date().toISOString()) }
}

function appendMessage(role, content, timestamp) {
  const area = document.getElementById("messages-area");
  const ws = document.getElementById("welcome-state");
  if (ws) ws.remove();
  const el = document.createElement("div");
  el.className = "msg " + role;
  const avatar = role === "assistant" ? "" : "";
  const time = new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const html = content.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  el.innerHTML = `<div class="msg-avatar">${avatar}</div><div><div class="msg-bubble">${html}</div><div class="msg-time">${time}</div></div>`;
  area.appendChild(el);
  area.scrollTo({ top: area.scrollHeight, behavior: "smooth" });
}

function showTyping(show) { document.getElementById("typing-indicator").style.display = show ? "flex" : "none" }
function enableInput(on) { document.getElementById("input-area").style.opacity = on ? "1" : "0.5"; document.getElementById("chat-input").disabled = !on }

function updateEmotionDisplay(scores, dominant) {
  document.body.className = `page-chat theme-${dominant}`;
  // -- emotion strip (below messages) ----------------------------------------
  const strip = document.getElementById("emotion-strip");
  strip.style.display = "flex";
  document.getElementById("current-emotion-icon").textContent = EMO_ICONS[dominant] || "";
  document.getElementById("current-emotion-label").textContent = dominant.charAt(0).toUpperCase() + dominant.slice(1);
  const bars = document.getElementById("emotion-bars");
  bars.innerHTML = Object.entries(scores).map(([k, v]) => `<div class="emotion-bar" title="${k}: ${(v * 100).toFixed(0)}%" style="height:${Math.max(3, Math.round(v * 20))}px;background:${EMO_COLORS[k] || "#94a3b8"};width:6px;border-radius:3px"></div>`).join("");
  // -- topbar emotion pill ---------------------------------------------------
  const pill = document.getElementById("topbar-emotion-pill");
  pill.setAttribute("data-emo", dominant);
  document.getElementById("pill-emo-icon").textContent = EMO_ICONS[dominant] || "";
  document.getElementById("pill-emo-label").textContent = dominant.charAt(0).toUpperCase() + dominant.slice(1);
  pill.style.display = "flex";
}
function toggleEmotionStrip() {
  const strip = document.getElementById("emotion-strip");
  strip.style.display = strip.style.display === "none" ? "flex" : "none";
}

function showWellnessTip(tip) {
  const bar = document.getElementById("wellness-tip-bar");
  document.getElementById("wellness-tip-text").textContent = tip;
  bar.style.display = "flex";
}
function dismissTip() { document.getElementById("wellness-tip-bar").style.display = "none" }
function closeCrisisModal() { document.getElementById("crisis-modal").style.display = "none" }

async function endSession() {
  if (!currentSessionId) return;
  try {
    await fetch(API + "/chat/session/" + currentSessionId + "/end", { method: "POST", headers: authHeaders() });
    currentSessionId = null;
    loadSessions();
    document.getElementById("messages-area").innerHTML = `<div class="welcome-state"><div class="welcome-icon">✨</div><h2 class="welcome-title">Session complete 🌙</h2><p class="welcome-subtitle">Well done for checking in. Rest well.</p><button class="btn btn-primary" onclick="newSession()">Start a new check-in</button></div>`;
    document.getElementById("emotion-strip").style.display = "none";
    document.getElementById("wellness-tip-bar").style.display = "none";
  } catch (e) { console.error(e) }
}

async function loadSession(id) {
  currentSessionId = id;
  showView("chat");
  const area = document.getElementById("messages-area");
  area.innerHTML = "<div class=\"loading-state\"><div class=\"loading-spinner\"></div></div>";
  try {
    const r = await fetch(API + "/chat/session/" + id, { headers: authHeaders() });
    const s = await r.json();
    area.innerHTML = "";
    document.getElementById("topbar-session-name").textContent = s.session_title.replace("Evening Check-in — ", "");
    s.messages.forEach(m => appendMessage(m.role, m.content, m.timestamp));
    enableInput(true);
  } catch (e) { area.innerHTML = "<div class=\"loading-state\">Could not load session.</div>" }
}

function handleInputKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage() }
}
function autoResize(ta) { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 140) + "px" }
let currentDashTab = "daily";
function switchDashboard(tab) {
  currentDashTab = tab;
  document.querySelectorAll(".dash-tab").forEach(t => t.classList.remove("active"));
  document.getElementById("dtab-" + tab).classList.add("active");
  document.getElementById("dashboard-daily").style.display = tab === "daily" ? "flex" : "none";
  document.getElementById("dashboard-weekly").style.display = tab === "weekly" ? "flex" : "none";
  loadDashboard(tab);
}

async function loadDashboard(tab) {
  const container = document.getElementById(tab === "daily" ? "daily-content" : "weekly-content");
  container.innerHTML = "<div class=\"loading-state\"><div class=\"loading-spinner\"></div><p>Loading...</p></div>";
  try {
    const r = await fetch(API + "/dashboard/" + tab, { headers: authHeaders() });
    if (!r.ok) throw new Error("Failed");
    const d = await r.json();
    tab === "daily" ? renderDaily(d, container) : renderWeekly(d, container);
  } catch (e) { container.innerHTML = "<div class=\"loading-state\">Could not load dashboard. Start a check-in first!</div>" }
}


// ─── Chart.js colour helpers ──────────────────────────────────────────────────
const EMO_COLORS_RGBA = {
  neutral: 'rgba(148,163,184,0.85)', anger: 'rgba(248,113,113,0.85)',
  disgust: 'rgba(163,230,53,0.85)', fear: 'rgba(251,191,36,0.85)',
  happiness: 'rgba(52,211,153,0.85)', sadness: 'rgba(125,211,252,0.85)',
  surprise: 'rgba(167,139,250,0.85)'
};
const EMO_COLORS_SOLID = {
  neutral: '#94a3b8', anger: '#f87171', disgust: '#a3e635',
  fear: '#fbbf24', happiness: '#34d399', sadness: '#7dd3fc', surprise: '#a78bfa'
};
let _chartInstances = {};
function _destroyChart(id) { if (_chartInstances[id]) { _chartInstances[id].destroy(); delete _chartInstances[id]; } }

// ─── Daily Dashboard Render ───────────────────────────────────────────────────

// --- Upgraded Charts & Suggestions ---
const SUGGESTIONS = {
  neutral: [
    "⚪ A balanced day! Try a 'micro-adventure'—take a different route home to keep your brain curious.",
    "⚪ Mindful observation: Spend 5 minutes watching the clouds or trees without your phone.",
    "⚪ Prepare for tomorrow by writing your top 3 'priority intentions' tonight."
  ],
  anger: [
    "🔴 Progressive Muscle Relaxation: Tense your muscles for 5s, then release. Start from your toes.",
    "🔴 Physical release: If you can, go for a quick jog or do 20 jumping jacks to process the adrenaline.",
    "🔴 Journaling: Write exactly what you're angry about on paper, then safely shred it."
  ],
  disgust: [
    "🟢 Environmental shift: Clean one small area of your desk or room to regain a sense of order.",
    "🟢 Sensory grounding: Scented candles or essential oils can help shift your sensory state.",
    "🟢 Perspective check: Is this feeling about a person, or just a specific action they took?"
  ],
  fear: [
    "🟡 Box Breathing: Inhale 4s, hold 4s, exhale 4s, hold 4s. Repeat 5 times.",
    "🟡 Grounding 5-4-3-2-1: Identify 5 things you see, 4 you touch, 3 you hear, 2 you smell, 1 you taste.",
    "🟡 Safe Space visualization: Close your eyes and imagine a place where you feel completely secure."
  ],
  happiness: [
    "💚 Savoring: Take 2 minutes to replay the best moment of today in your mind.",
    "💚 Gratitude share: Tell someone (or write down) why you're thankful for them today.",
    "💚 Anchor this feeling: Find a small object to hold and associate this joy with it for later."
  ],
  sadness: [
    "🔵 Self-compassion: Wrap yourself in a warm blanket and have a hot cup of tea.",
    "🔵 Social connection: Reach out to one trusted friend, even just a 'thinking of you' text.",
    "🔵 Low-stakes movement: A slow, 10-minute walk outside can help shift stagnant energy."
  ],
  surprise: [
    "🟣 Integration: Reflect on what exactly was unexpected. Was it a challenge or an opportunity?",
    "🟣 Curiosity: Ask yourself, 'What can I learn from this new information?'",
    "🟣 Presence: Practice a 1-minute meditation to bring your focus back to the 'now'."
  ]
};


// --- Happiness vs Sadness Dashboard Logic ---

function renderDaily(d, el) {
  console.log('Rendering Daily Dashboard:', d);
  const emo = d.dominant_emotion;
  const icon = EMO_ICONS[emo] || '😐';
  const accent = EMO_COLORS_SOLID[emo] || '#94a3b8';

  el.innerHTML = `
    <div class="stat-grid" style="margin-bottom:12px">
      <div class="stat-card" style="border-left:4px solid ${accent}">
        <div class="stat-value">${icon}</div>
        <div class="stat-label">Current Mood</div>
        <div style="font-weight:700;color:${accent};text-transform:uppercase;margin-top:4px">${emo}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${d.total_messages}</div>
        <div class="stat-label">Chat Turns</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="text-transform:capitalize">${d.mood_trend}</div>
        <div class="stat-label">Mood Trend</div>
      </div>
    </div>

    <!-- Happiness vs Sadness Main Chart -->
    <div class="emotion-chart" style="padding:24px;margin-bottom:20px">
      <div class="chart-title">📈 Happiness vs Sadness Tracker (Turn-by-Turn)</div>
      <canvas id="chart-daily-timeline" height="200"></canvas>
    </div>

    <!-- Session Summaries & Suggestions -->
    <div class="insights-container" style="margin-bottom:20px">
      <div class="chart-title">💡 Tonight's Reflections & Suggestions</div>
      <div class="insights-grid" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:20px">
        ${d.sessions.map(s => {
          const suggestions = SUGGESTIONS[s.dominant_emotion] || SUGGESTIONS['neutral'];
          return `
            <div class="stat-card" style="text-align:left; border-top: 4px solid ${EMO_COLORS_SOLID[s.dominant_emotion]}">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
                <span style="font-weight:700; font-size:0.85rem; text-transform:uppercase; color:${EMO_COLORS_SOLID[s.dominant_emotion]}">${s.title.split(' — ')[0]}</span>
                <span>${EMO_ICONS[s.dominant_emotion]}</span>
              </div>
              <p style="font-size:0.88rem; color:var(--text-muted); line-height:1.6; font-style:italic; margin-bottom:16px">
                "${s.summary || 'No summary available yet. Continue your check-in to see insights.'}"
              </p>
              <div class="suggestion-list">
                ${suggestions.slice(0, 2).map(tip => `
                  <div style="font-size:0.82rem; padding:8px 0; border-top:1px solid rgba(255,255,255,0.05); color:var(--text)">
                    ${tip}
                  </div>
                `).join('')}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div class="emotion-chart" style="padding:20px">
        <div class="chart-title">🕸️ Full Emotion Profile</div>
        <canvas id="chart-daily-radar" height="240"></canvas>
      </div>
      <div class="emotion-chart" style="padding:20px">
        <div class="chart-title">🍩 Breakdown</div>
        <canvas id="chart-daily-donut" height="240"></canvas>
      </div>
    </div>
  `;

  const labels = Object.keys(d.emotion_breakdown);
  const values = Object.values(d.emotion_breakdown).map(v => +(v * 100).toFixed(1));

  _destroyChart('radar');
  _chartInstances['radar'] = new Chart(document.getElementById('chart-daily-radar'), {
    type: 'radar',
    data: {
      labels: labels.map(l => l.toUpperCase()),
      datasets: [{
        data: values,
        backgroundColor: 'rgba(124,106,247,0.2)',
        borderColor: '#7c6af7',
        borderWidth: 2,
        pointBackgroundColor: labels.map(k => EMO_COLORS_SOLID[k]),
        fill: true
      }]
    },
    options: { scales: { r: { beginAtZero: true, max: 100, ticks: { display: false } } }, plugins: { legend: { display: false } } }
  });

  _destroyChart('donut');
  _chartInstances['donut'] = new Chart(document.getElementById('chart-daily-donut'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: labels.map(k => EMO_COLORS_RGBA[k]), borderColor: labels.map(k => EMO_COLORS_SOLID[k]) }]
    },
    options: { plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 10 } } } }
  });

  _renderDailyTimeline();
}

async function _renderDailyTimeline() {
  try {
    const r = await fetch(API + '/dashboard/timeline', { headers: authHeaders() });
    if (!r.ok) return;
    const data = await r.json();
    if (!data || data.length < 2) return;

    const tLabels = data.map((_, i) => `Turn ${i + 1}`);

    const datasets = [
      {
        label: 'Happiness 💚',
        data: data.map(l => +((l.happiness_score || l.Happiness_score || 0) * 100).toFixed(1)),
        borderColor: '#34d399', backgroundColor: 'rgba(52, 211, 153, 0.1)',
        fill: true, tension: 0.4, borderWidth: 3, pointRadius: 4
      },
      {
        label: 'Sadness 💙',
        data: data.map(l => +((l.sadness_score || l.Sadness_score || 0) * 100).toFixed(1)),
        borderColor: '#7dd3fc', backgroundColor: 'rgba(125, 211, 252, 0.1)',
        fill: true, tension: 0.4, borderWidth: 3, pointRadius: 4
      }
    ];

    _destroyChart('timeline');
    _chartInstances['timeline'] = new Chart(
      document.getElementById('chart-daily-timeline'),
      {
        type: 'line', data: { labels: tLabels, datasets },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: '#64748b' }, grid: { display: false } },
            y: { beginAtZero: true, max: 100, ticks: { color: '#64748b', callback: v => v + '%' }, grid: { color: 'rgba(255,255,255,0.04)' } }
          },
          plugins: {
            legend: { position: 'top', labels: { color: '#94a3b8', font: { size: 11, weight: '600' }, usePointStyle: true } },
            tooltip: { mode: 'index', intersect: false, backgroundColor: 'rgba(15, 23, 42, 0.9)', padding: 12 }
          }
        }
      }
    );
  } catch (e) { console.warn('Timeline load failed', e); }
}

function renderWeekly(d, el) {
  console.log('Rendering Weekly Dashboard:', d);
  const emo = d.overall_dominant_emotion;
  const accent = EMO_COLORS_SOLID[emo] || '#94a3b8';

  el.innerHTML = `
    <div class="stat-grid" style="margin-bottom:20px">
      <div class="stat-card" style="border-left:4px solid ${accent}">
        <div class="stat-value">${EMO_ICONS[emo] || '😐'}</div>
        <div class="stat-label">Weekly Mood</div>
        <div style="font-weight:700;color:${accent};text-transform:uppercase;margin-top:4px">${emo}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${d.total_sessions}</div>
        <div class="stat-label">Total Sessions</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${d.mood_trend}</div>
        <div class="stat-label">Weekly Trend</div>
      </div>
    </div>

    <!-- Weekly Happiness vs Sadness Line Graph -->
    <div class="emotion-chart" style="padding:24px;margin-bottom:20px">
      <div class="chart-title">📊 Weekly Happiness vs Sadness Trend (By Day)</div>
      <canvas id="chart-weekly-timeline" height="220"></canvas>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div class="emotion-chart" style="padding:20px"><canvas id="chart-weekly-radar" height="240"></canvas></div>
      <div class="emotion-chart" style="padding:20px"><canvas id="chart-weekly-donut" height="240"></canvas></div>
    </div>
  `;

  if (d.daily_summaries && d.daily_summaries.length) {
    const dayLabels = d.daily_summaries.map(s => new Date(s.date + 'T12:00:00').toLocaleDateString([], { weekday: 'short' }));

    _destroyChart('wtimeline');
    _chartInstances['wtimeline'] = new Chart(document.getElementById('chart-weekly-timeline'), {
      type: 'line',
      data: {
        labels: dayLabels,
        datasets: [
          {
            label: 'Happiness',
            data: d.daily_summaries.map(s => +((s.emotion_breakdown.happiness || s.emotion_breakdown.Happiness || 0) * 100).toFixed(1)),
            borderColor: '#34d399', backgroundColor: 'rgba(52, 211, 153, 0.1)',
            fill: true, tension: 0.4, borderWidth: 3
          },
          {
            label: 'Sadness',
            data: d.daily_summaries.map(s => +((s.emotion_breakdown.sadness || s.emotion_breakdown.Sadness || 0) * 100).toFixed(1)),
            borderColor: '#7dd3fc', backgroundColor: 'rgba(125, 211, 252, 0.1)',
            fill: true, tension: 0.4, borderWidth: 3
          }
        ]
      },
      options: {
        scales: {
          x: { ticks: { color: '#94a3b8' } },
          y: { beginAtZero: true, max: 100, ticks: { color: '#94a3b8', callback: v => v + '%' } }
        },
        plugins: { legend: { labels: { color: '#94a3b8' } } }
      }
    });
  }

  const labels = Object.keys(d.emotion_averages);
  const values = Object.values(d.emotion_averages).map(v => +(v * 100).toFixed(1));

  _destroyChart('wradar');
  _chartInstances['wradar'] = new Chart(document.getElementById('chart-weekly-radar'), {
    type: 'radar',
    data: { labels: labels.map(l => l.toUpperCase()), datasets: [{ data: values, backgroundColor: 'rgba(124,106,247,0.2)', borderColor: '#7c6af7', fill: true }] },
    options: { scales: { r: { beginAtZero: true, max: 100, ticks: { display: false } } }, plugins: { legend: { display: false } } }
  });

  _destroyChart('wdonut');
  _chartInstances['wdonut'] = new Chart(document.getElementById('chart-weekly-donut'), {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: labels.map(k => EMO_COLORS_RGBA[k]) }] },
    options: { plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } } }
  });
}


async function handleDeleteSession(event, id) {
  if (event) event.stopPropagation();
  if (!confirm("Are you sure you want to delete this conversation? This cannot be undone.")) return;

  try {
    const r = await fetch(API + '/chat/session/' + id, { method: 'DELETE', headers: authHeaders() });
    if (!r.ok) throw new Error('Failed to delete');

    if (currentSessionId == id) {
      currentSessionId = null;
      document.getElementById('messages-area').innerHTML = '<div class="welcome-state" id="welcome-state"><h2>Session Deleted</h2><p>Please select another session or start a new check-in.</p></div>';
      document.getElementById("topbar-session-name").textContent = "Check-in";
    }
    
    // Optimistic UI update: remove from sidebar immediately
    const item = document.getElementById(`session-item-${id}`);
    if (item) item.remove();
    
    // Also remove from History view if it's open
    loadHistory(); 
    loadSessions();
  } catch (e) { console.error(e); alert("Failed to delete session."); }
}

async function loadHistory() {
  const container = document.getElementById("history-content");
  container.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Loading history...</p></div>';
  try {
    const r = await fetch(API + "/chat/sessions", { headers: authHeaders() });
    const sessions = await r.json();
    if (!sessions.length) {
      container.innerHTML = '<div class="loading-state">No history yet. Start your first check-in!</div>';
      return;
    }
    container.innerHTML = `
      <div class="history-list">
        ${sessions.map(s => `
          <div class="history-item glass" onclick="loadSession(${s.id})">
            <div class="history-item-main">
              <div class="history-item-title">${s.session_title}</div>
              <div class="history-item-date">${new Date(s.started_at).toLocaleString()}</div>
              ${s.summary ? `<div class="history-item-summary">${s.summary}</div>` : ''}
            </div>
            <button class="btn btn-ghost btn-sm" onclick="handleDeleteSession(event, ${s.id})">🗑️ Delete</button>
          </div>
        `).join('')}
      </div>
    `;
  } catch (e) {
    container.innerHTML = '<div class="loading-state">Could not load history.</div>';
  }
}
