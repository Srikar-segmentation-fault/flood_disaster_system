#!/usr/bin/env python3
"""
SPA merger: transforms index.html into a single-page app.
- Replaces old topbar with a unified navbar (Globe / Overview / Flood / Storm)
- Wraps #main + #bb in #globe-view (hidden/shown via JS, never destroyed)
- Adds #dashboard-view with React dashboard components
- Adds SPA routing logic
"""
import re, os

SRC = 'index.html'

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

# ──────────────────────────────────────────────────────────────────────────────
# 1. ADD CDN scripts before </head>
# ──────────────────────────────────────────────────────────────────────────────
cdn = (
  '  <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>\n'
  '  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>\n'
  '  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>\n'
  '  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>\n'
)
html = html.replace('</head>', cdn + '</head>', 1)

# ──────────────────────────────────────────────────────────────────────────────
# 2. ADD new CSS before closing </style>
# ──────────────────────────────────────────────────────────────────────────────
new_css = r"""
/* ── SPA: view containers ── */
#globe-view{flex:1;display:flex;flex-direction:column;overflow:hidden;}
#dashboard-view{flex:1;display:none;overflow:auto;background:var(--bg-base);position:relative;}
#dashboard-view.spa-active{display:flex;flex-direction:column;}
/* ── SPA: unified nav tabs ── */
.nb-sep{width:1px;height:20px;background:var(--border);flex-shrink:0;margin:0 6px;}
.nb-tabs{display:flex;gap:3px;align-items:center;}
.nb-tab{display:flex;align-items:center;gap:5px;background:transparent;border:1px solid transparent;border-radius:7px;padding:5px 12px;font-size:11px;font-weight:600;color:var(--text-muted);cursor:pointer;transition:all 0.2s;white-space:nowrap;user-select:none;}
.nb-tab:hover{background:rgba(99,179,237,0.08);border-color:var(--border);color:var(--text-primary);}
.nb-tab.spa-active{background:rgba(59,130,246,0.15);border-color:rgba(59,130,246,0.5);color:#60a5fa;}
.nb-tab.flood:hover{color:#38bdf8;}.nb-tab.flood.spa-active{background:rgba(56,189,248,0.12);border-color:rgba(56,189,248,0.45);color:#38bdf8;}
.nb-tab.storm:hover{color:#c084fc;}.nb-tab.storm.spa-active{background:rgba(168,85,247,0.12);border-color:rgba(168,85,247,0.45);color:#c084fc;}
.nb-tab.overview:hover{color:#60a5fa;}
/* Globe-only buttons collapse when on dashboard */
.globe-only{transition:opacity 0.18s,max-width 0.18s,padding 0.18s;}
body.dash-mode .globe-only{opacity:0;pointer-events:none;max-width:0;padding-left:0;padding-right:0;border:none;overflow:hidden;}
/* Dashboard component styles (scoped to #dashboard-view) */
#dashboard-view .dv-page{flex:1;padding:28px 28px 40px;max-width:1600px;margin:0 auto;width:100%;}
#dashboard-view .page-header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:28px;}
#dashboard-view .page-badge{display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;padding:4px 10px;border-radius:20px;margin-bottom:8px;}
#dashboard-view .page-badge.flood{background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.3);color:#38bdf8;}
#dashboard-view .page-badge.storm{background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.3);color:#c084fc;}
#dashboard-view .page-badge.overview{background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);color:#60a5fa;}
#dashboard-view .page-title{font-size:26px;font-weight:800;letter-spacing:-0.5px;line-height:1.2;}
#dashboard-view .hl-flood{color:#38bdf8;}#dashboard-view .hl-storm{color:#c084fc;}#dashboard-view .hl-default{color:#60a5fa;}
#dashboard-view .page-subtitle{font-size:13px;color:var(--text-secondary);margin-top:5px;}
#dashboard-view .page-header-actions{display:flex;gap:8px;align-items:center;padding-top:4px;}
#dashboard-view .action-btn{display:flex;align-items:center;gap:6px;padding:8px 14px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid var(--border);background:rgba(255,255,255,0.03);color:var(--text-secondary);transition:all 0.2s;}
#dashboard-view .action-btn:hover{border-color:var(--border-glow);color:var(--text-primary);background:rgba(255,255,255,0.06);}
#dashboard-view .action-btn.primary{background:rgba(59,130,246,0.15);border-color:rgba(59,130,246,0.4);color:#60a5fa;}
#dashboard-view .stat-row{display:grid;gap:16px;margin-bottom:24px;}
#dashboard-view .stat-row.cols-4{grid-template-columns:repeat(4,1fr);}
#dashboard-view .stat-row.cols-5{grid-template-columns:repeat(5,1fr);}
#dashboard-view .stat-card{background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;position:relative;overflow:hidden;transition:border-color 0.2s,transform 0.2s;}
#dashboard-view .stat-card:hover{border-color:var(--border-glow);transform:translateY(-2px);}
#dashboard-view .stat-card::after{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:14px 14px 0 0;}
#dashboard-view .stat-card.blue::after{background:linear-gradient(90deg,#3b82f6,#06b6d4);}
#dashboard-view .stat-card.cyan::after{background:linear-gradient(90deg,#06b6d4,#14b8a6);}
#dashboard-view .stat-card.violet::after{background:linear-gradient(90deg,#8b5cf6,#a855f7);}
#dashboard-view .stat-card.orange::after{background:linear-gradient(90deg,#f97316,#ef4444);}
#dashboard-view .stat-card.green::after{background:linear-gradient(90deg,#22c55e,#14b8a6);}
#dashboard-view .stat-card.red::after{background:linear-gradient(90deg,#ef4444,#f97316);}
#dashboard-view .stat-card.yellow::after{background:linear-gradient(90deg,#eab308,#f97316);}
#dashboard-view .stat-label{font-size:10px;font-weight:600;letter-spacing:0.9px;text-transform:uppercase;color:var(--text-muted);margin-bottom:8px;}
#dashboard-view .stat-value{font-size:28px;font-weight:800;font-family:var(--mono);letter-spacing:-1px;line-height:1;}
#dashboard-view .stat-sub{font-size:11px;color:var(--text-secondary);margin-top:5px;display:flex;align-items:center;gap:5px;}
#dashboard-view .stat-trend{font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px;font-family:var(--mono);}
#dashboard-view .stat-trend.up{background:rgba(239,68,68,0.12);color:#f87171;border:1px solid rgba(239,68,68,0.2);}
#dashboard-view .stat-trend.down{background:rgba(34,197,94,0.12);color:#4ade80;border:1px solid rgba(34,197,94,0.2);}
#dashboard-view .stat-trend.neutral{background:rgba(234,179,8,0.12);color:#fde047;border:1px solid rgba(234,179,8,0.2);}
#dashboard-view .stat-icon{position:absolute;top:14px;right:16px;font-size:22px;opacity:0.25;}
#dashboard-view .chart-grid{display:grid;gap:20px;margin-bottom:24px;}
#dashboard-view .chart-grid.cols-2{grid-template-columns:1fr 1fr;}
#dashboard-view .chart-grid.cols-2-1{grid-template-columns:2fr 1fr;}
#dashboard-view .chart-card{background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:20px;display:flex;flex-direction:column;transition:border-color 0.2s;}
#dashboard-view .chart-card:hover{border-color:var(--border-glow);}
#dashboard-view .chart-header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px;}
#dashboard-view .chart-title{font-size:13px;font-weight:700;color:var(--text-primary);}
#dashboard-view .chart-subtitle{font-size:11px;color:var(--text-muted);margin-top:3px;}
#dashboard-view .chart-pill{font-size:10px;font-weight:600;padding:3px 9px;border-radius:12px;font-family:var(--mono);}
#dashboard-view .chart-pill.flood{background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.25);color:#38bdf8;}
#dashboard-view .chart-pill.storm{background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.25);color:#c084fc;}
#dashboard-view .chart-pill.green{background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.25);color:#4ade80;}
#dashboard-view .chart-pill.orange{background:rgba(249,115,22,0.1);border:1px solid rgba(249,115,22,0.25);color:#fb923c;}
#dashboard-view .chart-pill.red{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25);color:#f87171;}
#dashboard-view .chart-body{flex:1;position:relative;min-height:220px;}
#dashboard-view .chart-body canvas{width:100%!important;}
#dashboard-view .legend-row{display:flex;gap:14px;flex-wrap:wrap;margin-top:12px;}
#dashboard-view .legend-item{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text-secondary);}
#dashboard-view .legend-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
#dashboard-view .event-table-card{background:var(--bg-card);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:24px;}
#dashboard-view .event-table-header{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
#dashboard-view .event-table-header h3{font-size:13px;font-weight:700;}
#dashboard-view .event-table-sub{font-size:11px;color:var(--text-muted);margin-top:2px;}
#dashboard-view table.dash-table{width:100%;border-collapse:collapse;}
#dashboard-view table.dash-table thead th{padding:10px 16px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);background:rgba(255,255,255,0.02);text-align:left;border-bottom:1px solid var(--border);}
#dashboard-view table.dash-table tbody tr{border-bottom:1px solid rgba(99,179,237,0.06);transition:background 0.15s;}
#dashboard-view table.dash-table tbody tr:hover{background:rgba(99,179,237,0.03);}
#dashboard-view table.dash-table tbody tr:last-child{border-bottom:none;}
#dashboard-view table.dash-table tbody td{padding:10px 16px;font-size:11px;color:var(--text-secondary);vertical-align:middle;}
#dashboard-view .td-name{font-weight:600;color:var(--text-primary)!important;}
#dashboard-view .risk-badge{font-size:9px;font-weight:700;padding:3px 8px;border-radius:10px;font-family:var(--mono);text-transform:uppercase;letter-spacing:0.5px;display:inline-block;}
#dashboard-view .risk-badge.low{background:rgba(34,197,94,0.12);color:#4ade80;border:1px solid rgba(34,197,94,0.2);}
#dashboard-view .risk-badge.moderate{background:rgba(234,179,8,0.12);color:#fde047;border:1px solid rgba(234,179,8,0.2);}
#dashboard-view .risk-badge.high{background:rgba(249,115,22,0.12);color:#fb923c;border:1px solid rgba(249,115,22,0.2);}
#dashboard-view .risk-badge.critical{background:rgba(239,68,68,0.12);color:#f87171;border:1px solid rgba(239,68,68,0.2);}
#dashboard-view .risk-badge.extreme{background:rgba(168,85,247,0.12);color:#c084fc;border:1px solid rgba(168,85,247,0.2);}
#dashboard-view .mini-bar{height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;min-width:80px;}
#dashboard-view .mini-bar-fill{height:100%;border-radius:3px;}
#dashboard-view .feature-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
#dashboard-view .feature-name{font-size:11px;color:var(--text-secondary);width:160px;flex-shrink:0;}
#dashboard-view .feature-bar-bg{flex:1;height:8px;background:rgba(255,255,255,0.05);border-radius:4px;overflow:hidden;}
#dashboard-view .feature-bar-fill{height:100%;border-radius:4px;}
#dashboard-view .feature-pct{font-size:10px;font-family:var(--mono);color:var(--text-muted);width:38px;text-align:right;flex-shrink:0;}
#dashboard-view .alert-feed{display:flex;flex-direction:column;gap:8px;}
#dashboard-view .alert-item{background:var(--bg-card2);border:1px solid var(--border);border-radius:10px;padding:12px 14px;display:flex;align-items:flex-start;gap:10px;}
#dashboard-view .alert-icon{font-size:18px;flex-shrink:0;margin-top:1px;}
#dashboard-view .alert-body{flex:1;}
#dashboard-view .alert-title{font-size:12px;font-weight:600;margin-bottom:2px;}
#dashboard-view .alert-desc{font-size:11px;color:var(--text-secondary);line-height:1.45;}
#dashboard-view .alert-meta{font-size:10px;color:var(--text-muted);margin-top:4px;font-family:var(--mono);}
@media(max-width:1200px){
  #dashboard-view .stat-row.cols-4,#dashboard-view .stat-row.cols-5{grid-template-columns:repeat(2,1fr);}
  #dashboard-view .chart-grid.cols-2,#dashboard-view .chart-grid.cols-2-1{grid-template-columns:1fr;}
}
"""
html = html.replace('</style>', new_css + '\n</style>', 1)

# ──────────────────────────────────────────────────────────────────────────────
# 3. REPLACE TOPBAR HTML
# ──────────────────────────────────────────────────────────────────────────────
# We match the start and end markers precisely
old_topbar_start = '<!-- TOP BAR -->'
old_topbar_end = '</div>\n\n<!-- MAIN -->'

# Find bounds
i_start = html.index(old_topbar_start)
i_end   = html.index(old_topbar_end) + len(old_topbar_end)

new_topbar_block = """<!-- TOP BAR — Unified SPA Navbar -->
<div id="topbar">
  <svg class="logo-icon" viewBox="0 0 28 28" fill="none">
    <circle cx="14" cy="14" r="13" stroke="#3b82f6" stroke-width="1.5"/>
    <path d="M5 19 C7 15,9 21,11 17 C13 13,15 20,17 16 C19 12,21 18,23 18" stroke="#06b6d4" stroke-width="2" stroke-linecap="round" fill="none"/>
    <circle cx="14" cy="9" r="3" fill="#3b82f6" opacity="0.75"/>
    <path d="M14 12 L14 17" stroke="#3b82f6" stroke-width="1.5" stroke-linecap="round"/>
  </svg>
  <span class="topbar-title">FloodSense AI</span>
  <div class="nb-sep"></div>
  <div class="nb-tabs" id="nb-tabs">
    <div class="nb-tab spa-active" data-page="globe"    onclick="spaNavigate('globe')">&#127760; Globe</div>
    <div class="nb-tab overview"  data-page="overview" onclick="spaNavigate('overview')">&#127757; Overview</div>
    <div class="nb-tab flood"     data-page="flood"     onclick="spaNavigate('flood')">&#127754; Flood</div>
    <div class="nb-tab storm"     data-page="storm"     onclick="spaNavigate('storm')">&#127744; Storm</div>
  </div>
  <div class="spacer"></div>
  <div class="topbar-btn globe-only" id="btn-replay" onclick="openEventsModal()">&#128260; Replay</div>
  <div class="topbar-btn globe-only" id="btn-farm" onclick="toggleFarmMode()">&#127806; Farm Mode</div>
  <div class="status-pill"><div class="sdot"></div>Prediction Engine Online</div>
  <div id="clock">--:--:--</div>
</div>

<!-- MAIN -->"""

html = html[:i_start] + new_topbar_block + html[i_end:]

# ──────────────────────────────────────────────────────────────────────────────
# 4. WRAP #main and #bb in #globe-view, add #dashboard-view after
# ──────────────────────────────────────────────────────────────────────────────
html = html.replace('\n<!-- MAIN -->\n<div id="main">', '\n<!-- MAIN -->\n<div id="globe-view">\n<div id="main">', 1)

# Close #globe-view after #bb closes, before the HISTORICAL EVENTS MODAL
bb_close_marker = '</div>\n\n<!-- HISTORICAL EVENTS MODAL -->'
globe_inject = (
    '</div>\n'                          # closes #bb
    '</div><!-- /#globe-view -->\n\n'
    '<div id="dashboard-view"><div id="react-root"></div></div>\n\n'
    '<!-- HISTORICAL EVENTS MODAL -->'
)
html = html.replace(bb_close_marker, globe_inject, 1)

# ──────────────────────────────────────────────────────────────────────────────
# 5. ADD SPA ROUTER + REACT APP before </body>
# ──────────────────────────────────────────────────────────────────────────────
spa_and_react = r"""
<script>
/* ── SPA ROUTER ─────────────────────────────────────────────── */
function spaNavigate(page) {
  const globeView = document.getElementById('globe-view');
  const dashView  = document.getElementById('dashboard-view');

  if (page === 'globe') {
    globeView.style.display = 'flex';
    dashView.classList.remove('spa-active');
    document.body.classList.remove('dash-mode');
  } else {
    globeView.style.display = 'none';
    dashView.classList.add('spa-active');
    document.body.classList.add('dash-mode');
    if (window.__setDashPage) window.__setDashPage(page);
  }

  document.querySelectorAll('#nb-tabs .nb-tab').forEach(t => {
    t.classList.toggle('spa-active', t.dataset.page === page);
  });
}
</script>

<script type="text/babel">
/* ── REACT DASHBOARD (SPA version — no navbar, driven by spaNavigate) ─────── */
const{useState,useEffect,useRef}=React;
const MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const YEARS=[2018,2019,2020,2021,2022,2023,2024,2025];

const floodData={
  monthlyRainfall:[45,62,88,110,178,312,428,390,265,140,72,38],
  monthlyFloodRisk:[12,18,24,32,52,74,89,83,61,38,20,10],
  yearlyEvents:[14,19,22,18,28,35,41,52],
  yearlyAffected:[120,185,210,165,290,385,470,580],
  regionRisk:[
    {name:'Krishna Delta',risk:87,affected:12400,state:'Andhra Pradesh',level:'critical'},
    {name:'Brahmaputra Floodplain',risk:82,affected:28600,state:'Assam',level:'critical'},
    {name:'Bihar Plains',risk:76,affected:19200,state:'Bihar',level:'high'},
    {name:'Godavari Basin',risk:71,affected:9800,state:'Telangana',level:'high'},
    {name:'Mahanadi Delta',risk:68,affected:14300,state:'Odisha',level:'high'},
    {name:'Ganga Belt',risk:62,affected:31000,state:'Uttar Pradesh',level:'moderate'},
    {name:'Cauvery Delta',risk:48,affected:6700,state:'Tamil Nadu',level:'moderate'},
    {name:'Narmada Basin',risk:39,affected:4200,state:'Madhya Pradesh',level:'low'},
  ],
  shapFeatures:[
    {name:'Rainfall (72h cumulative)',val:0.42,color:'rgba(56,189,248,0.8)'},
    {name:'Soil Moisture Index',val:0.23,color:'rgba(20,184,166,0.8)'},
    {name:'River Gauge Level',val:0.18,color:'rgba(59,130,246,0.8)'},
    {name:'Topographic Slope',val:0.10,color:'rgba(99,102,241,0.8)'},
    {name:'Upstream Dam Level',val:0.07,color:'rgba(168,85,247,0.8)'},
  ],
  gaugeReadings:Array.from({length:30},(_,i)=>({
    krishna:parseFloat((8.2+Math.sin(i/4)*2.1+(i>18&&i<26?3.5:0)+Math.random()*0.4).toFixed(2)),
    brahmaputra:parseFloat((12.4+Math.sin(i/5)*3.5+(i>12&&i<20?4.2:0)+Math.random()*0.5).toFixed(2)),
  })),
  forecast48h:Array.from({length:49},(_,i)=>({
    risk:parseFloat(Math.min(100,45+Math.sin(i/8)*20+(i>20&&i<36?25:0)+Math.random()*8).toFixed(1)),
    lower:parseFloat(Math.max(0,35+Math.sin(i/8)*15+(i>20&&i<36?18:0)).toFixed(1)),
    upper:parseFloat(Math.min(100,55+Math.sin(i/8)*25+(i>20&&i<36?32:0)+Math.random()*10).toFixed(1)),
  })),
};

const stormData={
  monthlyFreq:[0.2,0.1,0.2,0.5,1.2,0.6,0.4,0.3,0.8,2.1,2.8,1.1],
  yearlyIntensity:YEARS.map(()=>({
    cat1:Math.floor(2+Math.random()*3),cat2:Math.floor(1+Math.random()*3),
    cat3:Math.floor(Math.random()*2),cat4:Math.floor(Math.random()*2),cat5:Math.floor(Math.random()*1.2)
  })),
  historicStorms:[
    {name:'Cyclone Amphan',year:2020,maxWind:185,pressure:920,deaths:128,damage:13200,cat:'Super Cyclone',landfall:'West Bengal'},
    {name:'Cyclone Biparjoy',year:2023,maxWind:150,pressure:944,deaths:14,damage:3600,cat:'Extremely Severe',landfall:'Gujarat'},
    {name:'Cyclone Mocha',year:2023,maxWind:195,pressure:924,deaths:463,damage:8100,cat:'Super Cyclone',landfall:'Myanmar/Bangladesh'},
    {name:'Cyclone Fani',year:2019,maxWind:180,pressure:932,deaths:89,damage:8100,cat:'Extremely Severe',landfall:'Odisha'},
    {name:'Cyclone Tauktae',year:2021,maxWind:165,pressure:940,deaths:198,damage:6900,cat:'Extremely Severe',landfall:'Gujarat'},
    {name:'Cyclone Gaja',year:2018,maxWind:120,pressure:976,deaths:63,damage:2800,cat:'Very Severe',landfall:'Tamil Nadu'},
  ],
  activeTrack:Array.from({length:72},(_,i)=>({
    hour:-72+i,
    windSpeed:parseFloat(Math.max(20,60+(i<36?i*3.2:(72-i)*2.8)+Math.sin(i/6)*12+Math.random()*8).toFixed(1)),
    pressure:parseFloat(Math.max(880,1010-(i<36?i*3.2:(72-i)*2.6)-Math.sin(i/6)*8-Math.random()*6).toFixed(0)),
  })),
  shapFeatures:[
    {name:'Wind Speed (10m)',val:0.50,color:'rgba(168,85,247,0.8)'},
    {name:'Pressure Gradient',val:0.30,color:'rgba(192,132,252,0.8)'},
    {name:'Sea Surface Temp',val:0.20,color:'rgba(99,179,237,0.8)'},
    {name:'Humidity (850 hPa)',val:0.14,color:'rgba(56,189,248,0.8)'},
    {name:'Distance to Coast',val:0.09,color:'rgba(59,130,246,0.8)'},
  ],
  regionRisk:[
    {name:'Bay of Bengal (North)',risk:82,level:'critical'},
    {name:'Arabian Sea (East)',risk:61,level:'high'},
    {name:'Bay of Bengal (South)',risk:58,level:'high'},
    {name:'Arabian Sea (West)',risk:42,level:'moderate'},
    {name:'Bay of Bengal (Central)',risk:38,level:'moderate'},
  ],
  forecastTrack:Array.from({length:13},(_,i)=>({t:i*6,wind:parseFloat(Math.max(60,120+i*5.5-Math.max(0,(i-8)*12)).toFixed(0))})),
};

const cDef={
  plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(8,12,24,0.97)',borderColor:'rgba(99,179,237,0.35)',borderWidth:1,titleColor:'#e8f0fe',bodyColor:'#8ba3c7',padding:10,cornerRadius:8}},
  scales:{x:{grid:{color:'rgba(99,179,237,0.06)',drawBorder:false},ticks:{color:'#4a6080',font:{family:'JetBrains Mono',size:10}}},y:{grid:{color:'rgba(99,179,237,0.06)',drawBorder:false},ticks:{color:'#4a6080',font:{family:'JetBrains Mono',size:10}}}},
  animation:{duration:700},responsive:true,maintainAspectRatio:false,
};

function StatCard({label,value,sub,trend,trendType='neutral',icon,colorClass='blue'}){
  return React.createElement('div',{className:`stat-card ${colorClass}`},
    icon&&React.createElement('div',{className:'stat-icon'},icon),
    React.createElement('div',{className:'stat-label'},label),
    React.createElement('div',{className:'stat-value'},value),
    React.createElement('div',{className:'stat-sub'},sub,trend&&React.createElement('span',{className:`stat-trend ${trendType}`},trend))
  );
}
function RiskBadge({level}){return React.createElement('span',{className:`risk-badge ${level}`},level);}
function MiniBar({value,color}){
  return React.createElement('div',{className:'mini-bar'},React.createElement('div',{className:'mini-bar-fill',style:{width:`${value}%`,background:color}}));
}
function SHAP({features}){
  return React.createElement('div',null,features.map((f,i)=>
    React.createElement('div',{key:i,className:'feature-row'},
      React.createElement('div',{className:'feature-name'},f.name),
      React.createElement('div',{className:'feature-bar-bg'},React.createElement('div',{className:'feature-bar-fill',style:{width:`${f.val*100}%`,background:f.color}})),
      React.createElement('div',{className:'feature-pct'},`${(f.val*100).toFixed(0)}%`)
    )
  ));
}
function useChart(ref,configFn,deps){
  const chart=useRef(null);
  useEffect(()=>{
    if(chart.current){chart.current.destroy();chart.current=null;}
    if(ref.current){const cfg=configFn();if(cfg)chart.current=new Chart(ref.current,cfg);}
    return()=>{if(chart.current){chart.current.destroy();chart.current=null;}};
  },deps||[]);
}

function FloodDashboard(){
  const r1=useRef(),r2=useRef(),r3=useRef(),r4=useRef(),r5=useRef(),r6=useRef();
  useChart(r1,()=>({type:'bar',data:{labels:MONTHS,datasets:[{label:'Rainfall mm',data:floodData.monthlyRainfall,backgroundColor:MONTHS.map((_,i)=>i>=5&&i<=8?'rgba(56,189,248,0.75)':'rgba(56,189,248,0.25)'),borderColor:'rgba(56,189,248,0.9)',borderWidth:1,borderRadius:4}]},options:{...cDef,scales:{...cDef.scales,y:{...cDef.scales.y,title:{display:true,text:'mm',color:'#4a6080',font:{size:10}}}}}}));
  useChart(r2,()=>({type:'line',data:{labels:MONTHS,datasets:[{label:'Flood Risk %',data:floodData.monthlyFloodRisk,borderColor:'#06b6d4',backgroundColor:'rgba(6,182,212,0.08)',fill:true,tension:0.4,pointBackgroundColor:'#06b6d4',pointRadius:4,borderWidth:2}]},options:{...cDef,scales:{...cDef.scales,y:{...cDef.scales.y,min:0,max:100}}}}));
  useChart(r3,()=>({type:'bar',data:{labels:YEARS,datasets:[{type:'bar',label:'Flood Events',data:floodData.yearlyEvents,backgroundColor:'rgba(56,189,248,0.4)',borderColor:'rgba(56,189,248,0.8)',borderWidth:1,borderRadius:4,yAxisID:'y'},{type:'line',label:'Affected (K)',data:floodData.yearlyAffected,borderColor:'#ef4444',fill:false,tension:0.4,pointBackgroundColor:'#ef4444',pointRadius:4,borderWidth:2,yAxisID:'y1'}]},options:{...cDef,plugins:{...cDef.plugins,legend:{display:true,position:'top',labels:{color:'#8ba3c7',font:{size:10},boxWidth:12,padding:12}}},scales:{x:cDef.scales.x,y:{...cDef.scales.y,position:'left',title:{display:true,text:'Events',color:'#4a6080',font:{size:10}}},y1:{...cDef.scales.y,position:'right',grid:{drawOnChartArea:false},title:{display:true,text:'Affected (K)',color:'#4a6080',font:{size:10}}}}}}));
  useChart(r4,()=>({type:'line',data:{labels:Array.from({length:30},(_,i)=>`D-${30-i}`),datasets:[{label:'Krishna (m)',data:floodData.gaugeReadings.map(r=>r.krishna),borderColor:'#38bdf8',fill:false,tension:0.35,pointRadius:0,borderWidth:2},{label:'Brahmaputra (m)',data:floodData.gaugeReadings.map(r=>r.brahmaputra),borderColor:'#8b5cf6',fill:false,tension:0.35,pointRadius:0,borderWidth:2},{label:'Danger (12m)',data:Array(30).fill(12),borderColor:'rgba(239,68,68,0.55)',borderDash:[5,3],pointRadius:0,fill:false,borderWidth:1.5},{label:'Warning (9m)',data:Array(30).fill(9),borderColor:'rgba(234,179,8,0.45)',borderDash:[5,3],pointRadius:0,fill:false,borderWidth:1.5}]},options:{...cDef,plugins:{...cDef.plugins,legend:{display:true,position:'top',labels:{color:'#8ba3c7',font:{size:10},boxWidth:12,padding:10}}},scales:{x:{...cDef.scales.x,ticks:{...cDef.scales.x.ticks,maxTicksLimit:8}},y:{...cDef.scales.y,title:{display:true,text:'Water Level (m)',color:'#4a6080',font:{size:10}}}}}}));
  useChart(r5,()=>({type:'line',data:{labels:Array.from({length:49},(_,i)=>`T+${i}h`),datasets:[{label:'Upper',data:floodData.forecast48h.map(r=>r.upper),borderColor:'transparent',backgroundColor:'rgba(239,68,68,0.07)',fill:'+1',tension:0.4,pointRadius:0},{label:'Flood Risk %',data:floodData.forecast48h.map(r=>r.risk),borderColor:'#38bdf8',fill:false,tension:0.4,pointRadius:0,borderWidth:2.5},{label:'Lower',data:floodData.forecast48h.map(r=>r.lower),borderColor:'transparent',fill:false,tension:0.4,pointRadius:0}]},options:{...cDef,scales:{x:{...cDef.scales.x,ticks:{...cDef.scales.x.ticks,maxTicksLimit:10}},y:{...cDef.scales.y,min:0,max:100,title:{display:true,text:'Risk %',color:'#4a6080',font:{size:10}}}}}}));
  const sorted=[...floodData.regionRisk].sort((a,b)=>b.risk-a.risk);
  useChart(r6,()=>({type:'bar',data:{labels:sorted.map(r=>r.name),datasets:[{label:'Risk Score',data:sorted.map(r=>r.risk),backgroundColor:sorted.map(r=>r.risk>80?'rgba(168,85,247,0.6)':r.risk>70?'rgba(239,68,68,0.55)':r.risk>55?'rgba(249,115,22,0.55)':r.risk>40?'rgba(234,179,8,0.5)':'rgba(34,197,94,0.5)'),borderColor:sorted.map(r=>r.risk>80?'#a855f7':r.risk>70?'#ef4444':r.risk>55?'#f97316':r.risk>40?'#eab308':'#22c55e'),borderWidth:1,borderRadius:4}]},options:{...cDef,indexAxis:'y',scales:{x:{...cDef.scales.x,min:0,max:100},y:{...cDef.scales.y,ticks:{...cDef.scales.y.ticks,font:{family:'Inter',size:10}}}}}}));

  return React.createElement('div',{className:'dv-page'},
    React.createElement('div',{className:'page-header'},
      React.createElement('div',null,
        React.createElement('div',{className:'page-badge flood'},'Flood Intelligence Dashboard'),
        React.createElement('div',{className:'page-title'},'Historical ',React.createElement('span',{className:'hl-flood'},'Flood Analysis')),
        React.createElement('div',{className:'page-subtitle'},'Compound LSTM · SHAP Explainability · River Gauge Networks · 48h Forecast')
      ),
      React.createElement('div',{className:'page-header-actions'},
        React.createElement('button',{className:'action-btn'},'Export CSV'),
        React.createElement('button',{className:'action-btn primary'},'Run LSTM Forecast')
      )
    ),
    React.createElement('div',{className:'stat-row cols-4'},
      React.createElement(StatCard,{label:'People at Risk',value:'1.82M',sub:'In High/Critical zones',trend:'\u2191 +12%',trendType:'up',icon:'\ud83d\udc65',colorClass:'red'}),
      React.createElement(StatCard,{label:'Active Flood Zones',value:'8',sub:'Monitored districts',trend:'\u25b2 +3 zones',trendType:'up',icon:'\ud83c\udf0a',colorClass:'blue'}),
      React.createElement(StatCard,{label:'Advance Warning',value:'34h',sub:'vs. 6-8h traditional',trend:'Best-in-class',trendType:'down',icon:'\u26a1',colorClass:'cyan'}),
      React.createElement(StatCard,{label:'Model Accuracy',value:'86%',sub:'Compound v3 \u00b7 LSTM+SHAP',trend:'\u2191 +14% vs v1',trendType:'down',icon:'\ud83e\udd16',colorClass:'violet'})
    ),
    React.createElement('div',{className:'chart-grid cols-2'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Monthly Rainfall Distribution'),React.createElement('div',{className:'chart-subtitle'},'Average precipitation (mm)')),React.createElement('span',{className:'chart-pill flood'},'2018-2025 avg')),
        React.createElement('div',{className:'chart-body',style:{height:'220px'}},React.createElement('canvas',{ref:r1})),
        React.createElement('div',{className:'legend-row'},React.createElement('div',{className:'legend-item'},React.createElement('div',{className:'legend-dot',style:{background:'rgba(56,189,248,0.9)'}}),React.createElement('span',null,'Peak Monsoon (Jun-Sep)')))
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Monthly Flood Risk Index'),React.createElement('div',{className:'chart-subtitle'},'Compound model risk score (0-100%)')),React.createElement('span',{className:'chart-pill red'},'Critical >70%')),
        React.createElement('div',{className:'chart-body',style:{height:'220px'}},React.createElement('canvas',{ref:r2}))
      )
    ),
    React.createElement('div',{className:'chart-grid cols-2'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'LSTM 48h Flood Risk Forecast'),React.createElement('div',{className:'chart-subtitle'},'With confidence band')),React.createElement('span',{className:'chart-pill flood'},'LIVE')),
        React.createElement('div',{className:'chart-body',style:{height:'230px'}},React.createElement('canvas',{ref:r5}))
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'River Gauge Levels (Last 30 Days)'),React.createElement('div',{className:'chart-subtitle'},'Krishna & Brahmaputra \u2014 meters ASL')),React.createElement('span',{className:'chart-pill orange'},'Live Gauges')),
        React.createElement('div',{className:'chart-body',style:{height:'230px'}},React.createElement('canvas',{ref:r4}))
      )
    ),
    React.createElement('div',{className:'chart-grid cols-2-1'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Year-on-Year Flood Events & Impact'),React.createElement('div',{className:'chart-subtitle'},'Annual events vs population affected')),React.createElement('span',{className:'chart-pill red'},'Worsening trend')),
        React.createElement('div',{className:'chart-body',style:{height:'230px'}},React.createElement('canvas',{ref:r3}))
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'SHAP Feature Attribution'),React.createElement('div',{className:'chart-subtitle'},'Top drivers of flood risk score')),React.createElement('span',{className:'chart-pill green'},'v3 Model')),
        React.createElement('div',{className:'chart-body',style:{height:'230px',display:'flex',flexDirection:'column',justifyContent:'center'}},React.createElement(SHAP,{features:floodData.shapFeatures}))
      )
    ),
    React.createElement('div',{className:'chart-card',style:{marginBottom:'24px'}},
      React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Regional Flood Risk Score \u2014 India'),React.createElement('div',{className:'chart-subtitle'},'8 monitored river basins')),React.createElement('span',{className:'chart-pill flood'},'8 Zones')),
      React.createElement('div',{className:'chart-body',style:{height:'260px'}},React.createElement('canvas',{ref:r6}))
    ),
    React.createElement('div',{className:'event-table-card'},
      React.createElement('div',{className:'event-table-header'},React.createElement('div',null,React.createElement('h3',null,'Flood Zone Monitoring Table'),React.createElement('div',{className:'event-table-sub'},'Real-time compound risk scores per monitored district')),React.createElement('span',{className:'chart-pill flood'},'Updated 1 min ago')),
      React.createElement('table',{className:'dash-table'},
        React.createElement('thead',null,React.createElement('tr',null,React.createElement('th',null,'Zone / Basin'),React.createElement('th',null,'State'),React.createElement('th',null,'Risk Score'),React.createElement('th',null,'Risk Level'),React.createElement('th',null,'People at Risk'),React.createElement('th',null,'Risk Bar'))),
        React.createElement('tbody',null,floodData.regionRisk.map((r,i)=>
          React.createElement('tr',{key:i},
            React.createElement('td',{className:'td-name'},'\ud83c\udf0a '+r.name),React.createElement('td',null,r.state),
            React.createElement('td',null,React.createElement('span',{style:{fontFamily:'var(--mono)',fontWeight:700,color:r.risk>80?'#c084fc':r.risk>70?'#f87171':r.risk>55?'#fb923c':r.risk>40?'#fde047':'#4ade80'}},r.risk+'%')),
            React.createElement('td',null,React.createElement(RiskBadge,{level:r.level})),
            React.createElement('td',{style:{fontFamily:'var(--mono)'}},r.affected.toLocaleString()),
            React.createElement('td',null,React.createElement(MiniBar,{value:r.risk,color:r.risk>80?'#a855f7':r.risk>70?'#ef4444':r.risk>55?'#f97316':r.risk>40?'#eab308':'#22c55e'}))
          )
        ))
      )
    )
  );
}

function StormDashboard(){
  const r1=useRef(),r2=useRef(),r3=useRef(),r4=useRef(),r5=useRef(),r6=useRef();
  useChart(r1,()=>({type:'bar',data:{labels:MONTHS,datasets:[{label:'Avg Cyclones/Month',data:stormData.monthlyFreq,backgroundColor:MONTHS.map((_,i)=>(i>=9&&i<=11)||i===4?'rgba(168,85,247,0.7)':'rgba(168,85,247,0.25)'),borderColor:'rgba(168,85,247,0.9)',borderWidth:1,borderRadius:4}]},options:{...cDef}}));
  useChart(r2,()=>({type:'bar',data:{labels:YEARS,datasets:[{label:'Cat 1',data:stormData.yearlyIntensity.map(y=>y.cat1),backgroundColor:'rgba(56,189,248,0.6)',stack:'s'},{label:'Cat 2',data:stormData.yearlyIntensity.map(y=>y.cat2),backgroundColor:'rgba(20,184,166,0.6)',stack:'s'},{label:'Cat 3',data:stormData.yearlyIntensity.map(y=>y.cat3),backgroundColor:'rgba(234,179,8,0.6)',stack:'s'},{label:'Cat 4',data:stormData.yearlyIntensity.map(y=>y.cat4),backgroundColor:'rgba(249,115,22,0.7)',stack:'s'},{label:'Cat 5',data:stormData.yearlyIntensity.map(y=>y.cat5),backgroundColor:'rgba(239,68,68,0.75)',stack:'s'}]},options:{...cDef,plugins:{...cDef.plugins,legend:{display:true,position:'top',labels:{color:'#8ba3c7',font:{size:10},boxWidth:10,padding:10}}},scales:{x:cDef.scales.x,y:{...cDef.scales.y,stacked:true}}}}));
  useChart(r3,()=>({type:'line',data:{labels:stormData.activeTrack.map(r=>r.hour+'h'),datasets:[{label:'Wind Speed (km/h)',data:stormData.activeTrack.map(r=>r.windSpeed),borderColor:'#c084fc',backgroundColor:'rgba(192,132,252,0.07)',fill:true,tension:0.4,pointRadius:0,borderWidth:2.5}]},options:{...cDef,scales:{x:{...cDef.scales.x,ticks:{...cDef.scales.x.ticks,maxTicksLimit:12}},y:{...cDef.scales.y,title:{display:true,text:'Wind Speed (km/h)',color:'#4a6080',font:{size:10}}}}}}));
  useChart(r4,()=>({type:'line',data:{labels:stormData.activeTrack.map(r=>r.hour+'h'),datasets:[{label:'Central Pressure (hPa)',data:stormData.activeTrack.map(r=>r.pressure),borderColor:'#38bdf8',backgroundColor:'rgba(56,189,248,0.06)',fill:true,tension:0.4,pointRadius:0,borderWidth:2}]},options:{...cDef,scales:{x:{...cDef.scales.x,ticks:{...cDef.scales.x.ticks,maxTicksLimit:12}},y:{...cDef.scales.y,reverse:true,title:{display:true,text:'Pressure (hPa)',color:'#4a6080',font:{size:10}}}}}}));
  useChart(r5,()=>({type:'bar',data:{labels:stormData.regionRisk.map(r=>r.name),datasets:[{label:'Storm Risk Score',data:stormData.regionRisk.map(r=>r.risk),backgroundColor:stormData.regionRisk.map(r=>r.risk>75?'rgba(239,68,68,0.55)':r.risk>55?'rgba(249,115,22,0.5)':'rgba(234,179,8,0.45)'),borderColor:stormData.regionRisk.map(r=>r.risk>75?'#ef4444':r.risk>55?'#f97316':'#eab308'),borderWidth:1,borderRadius:4}]},options:{...cDef,indexAxis:'y',scales:{x:{...cDef.scales.x,min:0,max:100},y:{...cDef.scales.y,ticks:{...cDef.scales.y.ticks,font:{family:'Inter',size:10}}}}}}));
  useChart(r6,()=>({type:'bar',data:{labels:stormData.forecastTrack.map(r=>'T+'+r.t+'h'),datasets:[{label:'Forecast Wind (km/h)',data:stormData.forecastTrack.map(r=>r.wind),backgroundColor:stormData.forecastTrack.map(r=>r.wind>=165?'rgba(239,68,68,0.75)':r.wind>=120?'rgba(249,115,22,0.65)':r.wind>=90?'rgba(234,179,8,0.6)':'rgba(168,85,247,0.45)'),borderColor:stormData.forecastTrack.map(r=>r.wind>=165?'#ef4444':r.wind>=120?'#f97316':r.wind>=90?'#eab308':'#a855f7'),borderWidth:1,borderRadius:4}]},options:{...cDef,scales:{x:cDef.scales.x,y:{...cDef.scales.y,title:{display:true,text:'Wind Speed (km/h)',color:'#4a6080',font:{size:10}}}}}}));

  return React.createElement('div',{className:'dv-page'},
    React.createElement('div',{className:'page-header'},
      React.createElement('div',null,
        React.createElement('div',{className:'page-badge storm'},'Storm Intelligence Dashboard'),
        React.createElement('div',{className:'page-title'},'Cyclone & ',React.createElement('span',{className:'hl-storm'},'Storm Analysis')),
        React.createElement('div',{className:'page-subtitle'},'XGBoost Classifier \u00b7 LSTM Track Prediction \u00b7 SHAP Attribution \u00b7 Bay of Bengal & Arabian Sea')
      ),
      React.createElement('div',{className:'page-header-actions'},
        React.createElement('button',{className:'action-btn'},'Export Track Data'),
        React.createElement('button',{className:'action-btn primary'},'Active Storm: BIPARJOY-2')
      )
    ),
    React.createElement('div',{className:'stat-row cols-5'},
      React.createElement(StatCard,{label:'Active Cyclones',value:'2',sub:'Bay of Bengal + Arabian Sea',trend:'\u2b06 +1 this week',trendType:'up',icon:'\ud83c\udf00',colorClass:'violet'}),
      React.createElement(StatCard,{label:'Peak Wind Speed',value:'185',sub:'km/h \u00b7 Super Cyclone class',trend:'Cat 5 equivalent',trendType:'up',icon:'\ud83d\udca8',colorClass:'red'}),
      React.createElement(StatCard,{label:'Min Pressure',value:'920',sub:'hPa \u00b7 Storm center',trend:'Deepening',trendType:'up',icon:'\ud83d\udcc9',colorClass:'blue'}),
      React.createElement(StatCard,{label:'Time to Landfall',value:'18h',sub:'XGBoost LSTM estimate',trend:'High confidence',trendType:'neutral',icon:'\u23f1',colorClass:'orange'}),
      React.createElement(StatCard,{label:'Storm Risk Score',value:'74%',sub:'XGBoost model v1.0',trend:'Extremely Severe',trendType:'up',icon:'\u26a0\ufe0f',colorClass:'yellow'})
    ),
    React.createElement('div',{className:'chart-grid cols-2'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Storm Wind Speed \u2014 72h Track History'),React.createElement('div',{className:'chart-subtitle'},'Observed max sustained wind (km/h)')),React.createElement('span',{className:'chart-pill storm'},'XGBoost v1')),
        React.createElement('div',{className:'chart-body',style:{height:'230px'}},React.createElement('canvas',{ref:r3}))
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Central Pressure \u2014 72h History'),React.createElement('div',{className:'chart-subtitle'},'hPa \u00b7 Lower = stronger storm (inverted axis)')),React.createElement('span',{className:'chart-pill flood'},'LSTM Model')),
        React.createElement('div',{className:'chart-body',style:{height:'230px'}},React.createElement('canvas',{ref:r4}))
      )
    ),
    React.createElement('div',{className:'chart-grid cols-2'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Monthly Cyclone Frequency (Climatology)'),React.createElement('div',{className:'chart-subtitle'},'Average storms per month \u2014 Indian Ocean')),React.createElement('span',{className:'chart-pill storm'},'1990-2025')),
        React.createElement('div',{className:'chart-body',style:{height:'220px'}},React.createElement('canvas',{ref:r1}))
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Yearly Storm Intensity Distribution'),React.createElement('div',{className:'chart-subtitle'},'Stacked by IMD cyclone category')),React.createElement('span',{className:'chart-pill red'},'Intensifying')),
        React.createElement('div',{className:'chart-body',style:{height:'220px'}},React.createElement('canvas',{ref:r2}))
      )
    ),
    React.createElement('div',{className:'chart-grid cols-2-1'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'72h Forecast Wind Speed (Next Landfall)'),React.createElement('div',{className:'chart-subtitle'},'LSTM track prediction \u00b7 6-hourly steps')),React.createElement('span',{className:'chart-pill storm'},'T+0 to T+72h')),
        React.createElement('div',{className:'chart-body',style:{height:'230px'}},React.createElement('canvas',{ref:r6}))
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'SHAP Storm Feature Attribution'),React.createElement('div',{className:'chart-subtitle'},'XGBoost top risk drivers')),React.createElement('span',{className:'chart-pill green'},'v1.0 Model')),
        React.createElement('div',{className:'chart-body',style:{height:'230px',display:'flex',flexDirection:'column',justifyContent:'center'}},React.createElement(SHAP,{features:stormData.shapFeatures}))
      )
    ),
    React.createElement('div',{className:'chart-card',style:{marginBottom:'24px'}},
      React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Storm Risk by Ocean Basin / Region'),React.createElement('div',{className:'chart-subtitle'},'XGBoost compound risk score')),React.createElement('span',{className:'chart-pill storm'},'5 Regions')),
      React.createElement('div',{className:'chart-body',style:{height:'180px'}},React.createElement('canvas',{ref:r5}))
    ),
    React.createElement('div',{className:'event-table-card'},
      React.createElement('div',{className:'event-table-header'},React.createElement('div',null,React.createElement('h3',null,'Notable Cyclone Events \u2014 Historical Record'),React.createElement('div',{className:'event-table-sub'},'FloodSense AI retroactive predictions vs actual impact')),React.createElement('span',{className:'chart-pill storm'},'2018-2025')),
      React.createElement('table',{className:'dash-table'},
        React.createElement('thead',null,React.createElement('tr',null,React.createElement('th',null,'Storm Name'),React.createElement('th',null,'Year'),React.createElement('th',null,'Max Wind'),React.createElement('th',null,'Min Pressure'),React.createElement('th',null,'Category'),React.createElement('th',null,'Landfall'),React.createElement('th',null,'Damage (Cr Rs)'),React.createElement('th',null,'Deaths'))),
        React.createElement('tbody',null,stormData.historicStorms.map((s,i)=>
          React.createElement('tr',{key:i},
            React.createElement('td',{className:'td-name'},'\ud83c\udf00 '+s.name),
            React.createElement('td',{style:{fontFamily:'var(--mono)'}},s.year),
            React.createElement('td',{style:{fontFamily:'var(--mono)',color:'#c084fc',fontWeight:600}},s.maxWind+' km/h'),
            React.createElement('td',{style:{fontFamily:'var(--mono)',color:'#38bdf8'}},s.pressure+' hPa'),
            React.createElement('td',{style:{fontSize:'10px',color:'var(--text-secondary)'}},s.cat),
            React.createElement('td',null,s.landfall),
            React.createElement('td',{style:{fontFamily:'var(--mono)',color:'#fb923c'}},'Rs '+s.damage.toLocaleString()),
            React.createElement('td',{style:{fontFamily:'var(--mono)',color:'#f87171'}},s.deaths)
          )
        ))
      )
    )
  );
}

function OverviewDashboard(){
  const r1=useRef(),r2=useRef();
  useChart(r1,()=>({type:'doughnut',data:{labels:['Flood (Critical)','Storm (Extreme)','Earthquake','Wildfire','Drought'],datasets:[{data:[35,28,18,12,7],backgroundColor:['rgba(56,189,248,0.7)','rgba(168,85,247,0.7)','rgba(192,132,252,0.65)','rgba(249,115,22,0.65)','rgba(234,179,8,0.6)'],borderColor:['#38bdf8','#a855f7','#c084fc','#f97316','#eab308'],borderWidth:1.5,hoverOffset:6}]},options:{responsive:true,maintainAspectRatio:false,cutout:'62%',plugins:{legend:{position:'bottom',labels:{color:'#8ba3c7',font:{family:'Inter',size:10},boxWidth:10,padding:14}},tooltip:cDef.plugins.tooltip},animation:{duration:800}}}));
  useChart(r2,()=>({type:'radar',data:{labels:['Flood Risk','Storm Track','Earthquake','Wildfire','Drought','Advance Warning'],datasets:[{label:'FloodSense AI v3',data:[86,74,68,55,60,90],borderColor:'#38bdf8',backgroundColor:'rgba(56,189,248,0.12)',borderWidth:2,pointBackgroundColor:'#38bdf8',pointRadius:4},{label:'Traditional NWP',data:[52,58,71,48,55,40],borderColor:'rgba(139,92,246,0.6)',backgroundColor:'rgba(139,92,246,0.07)',borderWidth:1.5,borderDash:[4,3],pointBackgroundColor:'#8b5cf6',pointRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'top',labels:{color:'#8ba3c7',font:{size:10},boxWidth:10,padding:12}},tooltip:cDef.plugins.tooltip},scales:{r:{min:0,max:100,grid:{color:'rgba(99,179,237,0.08)'},angleLines:{color:'rgba(99,179,237,0.08)'},ticks:{color:'#4a6080',font:{family:'JetBrains Mono',size:9},stepSize:25,backdropColor:'transparent'},pointLabels:{color:'#8ba3c7',font:{family:'Inter',size:10}}}},animation:{duration:800}}}));

  const alerts=[
    {icon:'\ud83c\udf0a',title:'Critical Flood Alert \u2014 Krishna Delta',desc:'Risk score 87% \u00b7 LSTM forecast: peak in 18h \u00b7 12,400 people in immediate zone.',meta:'2 min ago \u00b7 Andhra Pradesh',level:'critical'},
    {icon:'\ud83c\udf00',title:'Cyclone BIPARJOY-2 Intensifying',desc:'Max wind 150 km/h, deepening. Landfall estimate: Gujarat coast T+18h.',meta:'8 min ago \u00b7 Arabian Sea',level:'extreme'},
    {icon:'\u26a1',title:'Flash Flood Warning \u2014 Brahmaputra',desc:'Gauge level 14.2m (danger: 12m). Upstream dam release imminent.',meta:'15 min ago \u00b7 Assam',level:'high'},
    {icon:'\u2600\ufe0f',title:'Drought Stress Alert \u2014 Vidarbha',desc:'Soil moisture index below 18%. Crop stress risk elevated for 4.2L farmers.',meta:'32 min ago \u00b7 Maharashtra',level:'moderate'},
  ];

  return React.createElement('div',{className:'dv-page'},
    React.createElement('div',{className:'page-header'},
      React.createElement('div',null,
        React.createElement('div',{className:'page-badge overview'},'FloodSense AI \u2014 Command Overview'),
        React.createElement('div',{className:'page-title'},'Multi-Hazard ',React.createElement('span',{className:'hl-default'},'Risk Overview')),
        React.createElement('div',{className:'page-subtitle'},'Global compound risk status \u00b7 All monitored hazards \u00b7 Real-time prediction engine')
      ),
      React.createElement('div',{className:'page-header-actions'},
        React.createElement('button',{className:'action-btn primary'},'Send SMS Alerts')
      )
    ),
    React.createElement('div',{className:'stat-row cols-4'},
      React.createElement(StatCard,{label:'Global Compound Risk',value:'MODERATE',sub:'45% \u00b7 Stable trend',trend:'Stable',trendType:'neutral',icon:'\ud83c\udf0d',colorClass:'blue'}),
      React.createElement(StatCard,{label:'Active Risk Zones',value:'45',sub:'Across 8 global regions',trend:'\u2191 +3 this week',trendType:'up',icon:'\ud83d\udccd',colorClass:'orange'}),
      React.createElement(StatCard,{label:'Farmers Protected',value:'1.2M',sub:'Via SMS gateway',trend:'ROI 40,000x',trendType:'down',icon:'\ud83c\udf3e',colorClass:'green'}),
      React.createElement(StatCard,{label:'ML Model Uptime',value:'99.7%',sub:'Compound v3 + LSTM',trend:'All systems nominal',trendType:'down',icon:'\u2699\ufe0f',colorClass:'cyan'})
    ),
    React.createElement('div',{className:'chart-grid cols-2'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Global Hazard Activity Breakdown'),React.createElement('div',{className:'chart-subtitle'},'Current share of active risk alerts by category')),React.createElement('span',{className:'chart-pill flood'},'Live')),
        React.createElement('div',{className:'chart-body',style:{height:'260px'}},React.createElement('canvas',{ref:r1}))
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'System Capability Comparison'),React.createElement('div',{className:'chart-subtitle'},'FloodSense AI v3 vs Traditional NWP/IMD systems')),React.createElement('span',{className:'chart-pill green'},'v3 Model')),
        React.createElement('div',{className:'chart-body',style:{height:'260px'}},React.createElement('canvas',{ref:r2}))
      )
    ),
    React.createElement('div',{className:'chart-card',style:{marginBottom:'24px'}},
      React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'Active Alert Feed'),React.createElement('div',{className:'chart-subtitle'},'Real-time compound risk alerts \u2014 sorted by priority')),React.createElement('span',{className:'chart-pill red'},alerts.length+' Active')),
      React.createElement('div',{className:'alert-feed'},alerts.map((a,i)=>
        React.createElement('div',{key:i,className:'alert-item'},
          React.createElement('div',{className:'alert-icon'},a.icon),
          React.createElement('div',{className:'alert-body'},React.createElement('div',{className:'alert-title'},a.title),React.createElement('div',{className:'alert-desc'},a.desc),React.createElement('div',{className:'alert-meta'},a.meta)),
          React.createElement(RiskBadge,{level:a.level})
        )
      ))
    ),
    React.createElement('div',{className:'chart-grid cols-2'},
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'ML Model Summary'))),
        React.createElement('table',{className:'dash-table'},
          React.createElement('thead',null,React.createElement('tr',null,React.createElement('th',null,'Model'),React.createElement('th',null,'Version'),React.createElement('th',null,'Accuracy'),React.createElement('th',null,'Notes'))),
          React.createElement('tbody',null,
            React.createElement('tr',null,React.createElement('td',{className:'td-name'},'Compound Flood'),React.createElement('td',{style:{fontFamily:'var(--mono)'}},'v3.0'),React.createElement('td',{style:{color:'#4ade80',fontFamily:'var(--mono)',fontWeight:700}},'86%'),React.createElement('td',{style:{fontSize:'10px'}},'LSTM + SHAP + Meta-Ensemble')),
            React.createElement('tr',null,React.createElement('td',{className:'td-name'},'Storm XGBoost'),React.createElement('td',{style:{fontFamily:'var(--mono)'}},'v1.0'),React.createElement('td',{style:{color:'#38bdf8',fontFamily:'var(--mono)',fontWeight:700}},'74%'),React.createElement('td',{style:{fontSize:'10px'}},'XGBoost + LSTM Track Pred')),
            React.createElement('tr',null,React.createElement('td',{className:'td-name'},'LSTM Forecast'),React.createElement('td',{style:{fontFamily:'var(--mono)'}},'v2.1'),React.createElement('td',{style:{color:'#c084fc',fontFamily:'var(--mono)',fontWeight:700}},'91%'),React.createElement('td',{style:{fontSize:'10px'}},'48h flood · 72h storm')),
            React.createElement('tr',null,React.createElement('td',{className:'td-name'},'SHAP Explainer'),React.createElement('td',{style:{fontFamily:'var(--mono)'}},'v1.4'),React.createElement('td',{style:{color:'#fb923c',fontFamily:'var(--mono)',fontWeight:700}},'-'),React.createElement('td',{style:{fontSize:'10px'}},'TreeExplainer · Real-time'))
          )
        )
      ),
      React.createElement('div',{className:'chart-card'},
        React.createElement('div',{className:'chart-header'},React.createElement('div',null,React.createElement('div',{className:'chart-title'},'API Endpoint Status'))),
        React.createElement('div',{style:{display:'flex',flexDirection:'column',gap:'8px'}},
          ['/health','/predict/flood','/predict/storm','/earthquakes (USGS)','/farmers','/send-alert (Twilio)'].map((ep,i)=>
            React.createElement('div',{key:i,style:{display:'flex',alignItems:'center',justifyContent:'space-between',background:'var(--bg-card2)',border:'1px solid var(--border)',borderRadius:'8px',padding:'8px 12px'}},
              React.createElement('span',{style:{fontFamily:'var(--mono)',fontSize:'11px',color:i<5?'#22c55e':'#eab308'}},ep),
              React.createElement('span',{style:{fontSize:'11px',color:i<5?'#22c55e':'#eab308'}},'● '+(i<5?'Online':'Standby'))
            )
          )
        )
      )
    )
  );
}

function DashApp(){
  const [page, setPage] = useState('overview');
  // Expose setter to SPA router
  useEffect(() => { window.__setDashPage = setPage; return () => { delete window.__setDashPage; }; }, []);
  return React.createElement(React.Fragment, null,
    page === 'overview' && React.createElement(OverviewDashboard, null),
    page === 'flood'    && React.createElement(FloodDashboard, null),
    page === 'storm'    && React.createElement(StormDashboard, null),
  );
}

ReactDOM.createRoot(document.getElementById('react-root')).render(React.createElement(DashApp, null));
</script>
"""

html = html.replace('</body>', spa_and_react + '\n</body>', 1)

with open(SRC, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done. Written {len(html):,} bytes to {SRC}")
