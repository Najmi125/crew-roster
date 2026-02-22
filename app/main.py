<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Crew Scheduling System - Preview</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: sans-serif; background: #f0f2f6; display: flex; min-height: 100vh; }

  /* Sidebar */
  .sidebar {
    width: 220px;
    background: #ffffff;
    border-right: 1px solid #dee2e6;
    padding: 1rem;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .sidebar img {
    width: 100%;
    border-radius: 6px;
    margin-bottom: 0.5rem;
  }
  .sidebar-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 0.3rem;
  }
  .sidebar hr { border: none; border-top: 1px solid #dee2e6; margin: 0.5rem 0; }
  .sidebar-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
  }
  .date-input {
    width: 100%;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 0.8rem;
    margin-bottom: 0.4rem;
    color: #333;
  }
  .nav-links { margin-top: 0.5rem; }
  .nav-link {
    display: block;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 0.85rem;
    color: #333;
    text-decoration: none;
    margin-bottom: 2px;
  }
  .nav-link.active { background: #e8eaf6; color: #1a1a2e; font-weight: 600; }
  .nav-link:hover { background: #f0f0f0; }

  /* Main content */
  .main {
    flex: 1;
    padding: 1.5rem;
    overflow-x: auto;
    background: #f0f2f6;
  }

  .occ-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #000000;
    text-transform: uppercase;
    line-height: 1;
    margin-bottom: 2px;
  }
  .occ-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem;
    color: #888;
    letter-spacing: 0.2em;
    margin-bottom: 1rem;
  }
  .live-badge {
    display: inline-block;
    background: #efffef;
    color: #006600;
    border: 1px solid #006600;
    border-radius: 3px;
    padding: 2px 10px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem;
    margin-bottom: 1rem;
  }

  /* Metrics */
  .metric-bar {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  .metric-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-top: 3px solid #1a1a2e;
    border-radius: 4px;
    padding: 0.6rem 1.2rem;
    flex: 1;
  }
  .metric-label {
    font-size: 0.6rem;
    color: #888;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-family: 'Share Tech Mono', monospace;
  }
  .metric-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #1a1a2e;
    line-height: 1.1;
  }

  /* Grid */
  .grid-wrapper {
    overflow-x: auto;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    background: #fff;
  }
  .roster-grid {
    border-collapse: collapse;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.58rem;
    width: 100%;
  }
  .roster-grid th {
    background: #1a1a2e;
    color: #fff;
    padding: 6px 4px;
    text-align: center;
    border: 1px solid #2d2d4e;
    font-size: 0.55rem;
    white-space: nowrap;
  }
  .roster-grid th.flight-col {
    background: #0f0f1a;
    color: #aaaacc;
    text-align: left;
    padding-left: 8px;
    min-width: 75px;
  }
  .roster-grid td {
    padding: 3px 4px;
    border: 1px solid #eeeeee;
    text-align: center;
    vertical-align: top;
    min-width: 68px;
    background: #fff;
  }
  .roster-grid td.flight-id {
    background: #f0f0f5;
    color: #1a1a2e;
    font-weight: bold;
    text-align: left;
    padding-left: 8px;
    border-right: 2px solid #ccccdd;
    white-space: nowrap;
    font-size: 0.62rem;
  }
  .roster-grid tr:hover td { background: #f0f4ff; }
  .roster-grid tr:hover td.flight-id { background: #e0e4f5; }
  .crew-cell { display: flex; flex-direction: column; gap: 1px; }
  .crew-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 82px; display: block; }
  .lcc { color: #b35900; font-weight: bold; }
  .cc  { color: #006633; font-weight: bold; }
  .empty-cell { color: #ccc; }
  .override { color: #cc0000 !important; }

  .legend {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    color: #888;
    margin-top: 0.5rem;
  }
</style>
</head>
<body>

<!-- Sidebar -->
<div class="sidebar">
  <img src="https://raw.githubusercontent.com/Najmi125/crew-roster/main/assets/cc.jpg" alt="Crew">
  <div class="sidebar-title">✈️ Crew Roster</div>
  <hr>
  <div class="nav-links">
    <a class="nav-link active" href="#">🏠 streamlit app</a>
    <a class="nav-link" href="#">📋 Roster</a>
    <a class="nav-link" href="#">✏️ Override</a>
  </div>
  <hr>
  <div class="sidebar-label">📅 Date Range</div>
  <input class="date-input" type="date" value="2026-02-22">
  <input class="date-input" type="date" value="2026-03-23">
</div>

<!-- Main -->
<div class="main">
  <div class="occ-title">AI Generated Crew Scheduling System</div>
  <div class="occ-sub">30 days rolling rosster </div>
  <span class="live-badge">● LIVE — Operational Roster</span>

  <!-- Metrics -->
  <div class="metric-bar">
    <div class="metric-card">
      <div class="metric-label">👨‍✈️ Active Crew</div>
      <div class="metric-value">75</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">✈️ Flights Scheduled</div>
      <div class="metric-value">360</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">📋 Assignments</div>
      <div class="metric-value">1440</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">⚠️ Violations</div>
      <div class="metric-value">0</div>
    </div>
  </div>

  <!-- Roster Grid -->
  <div class="grid-wrapper">
    <table class="roster-grid">
      <thead>
        <tr>
          <th class="flight-col">FLIGHT</th>
          <th>22<br>SUN</th><th>23<br>MON</th><th>24<br>TUE</th><th>25<br>WED</th><th>26<br>THU</th>
          <th>27<br>FRI</th><th>28<br>SAT</th><th>01<br>SUN</th><th>02<br>MON</th><th>03<br>TUE</th>
          <th>04<br>WED</th><th>05<br>THU</th><th>06<br>FRI</th><th>07<br>SAT</th><th>08<br>SUN</th>
          <th>09<br>MON</th><th>10<br>TUE</th><th>11<br>WED</th><th>12<br>THU</th><th>13<br>FRI</th>
          <th>14<br>SAT</th><th>15<br>SUN</th><th>16<br>MON</th><th>17<br>TUE</th><th>18<br>WED</th>
          <th>19<br>THU</th><th>20<br>FRI</th><th>21<br>SAT</th><th>22<br>SUN</th><th>23<br>MON</th>
        </tr>
      </thead>
      <tbody id="grid-body"></tbody>
    </table>
  </div>

  <div class="legend">
    <span style="color:#b35900">■</span> LCC &nbsp;&nbsp;
    <span style="color:#006633">■</span> CC &nbsp;&nbsp;
    <span style="color:#cc0000">■</span> Manual Override
  </div>
</div>

<script>
  // Sample flights and crew data
  const flights = ['PK301','PK302','PK303','PK304','PK305','PK306','PK307','PK308',
                   'PK309','PK310','PK311','PK312','PK401','PK402','PK403','PK404',
                   'PK501','PK502','PK503','PK504'];

  const lccNames = ['A.Khan','M.Ali','S.Ahmed','F.Hassan','R.Malik',
                    'A.Zafar','N.Siddiq','K.Baig','Z.Qureshi','T.Raja'];
  const ccNames  = ['S.Noor','H.Fatima','R.Aslam','M.Bibi','L.Chaud',
                    'P.Mirza','D.Sheikh','Y.Ansari','B.Javed','C.Iqbal'];

  const tbody = document.getElementById('grid-body');
  const days = 30;

  flights.forEach(flight => {
    const tr = document.createElement('tr');
    let html = `<td class="flight-id">${flight}</td>`;
    for (let d = 0; d < days; d++) {
      // Simulate: most days have crew, some are empty
      const hasData = Math.random() > 0.08;
      if (!hasData) {
        html += `<td><span class="empty-cell">—</span></td>`;
      } else {
        const lcc = lccNames[Math.floor(Math.random() * lccNames.length)];
        const cc1 = ccNames[Math.floor(Math.random() * ccNames.length)];
        const cc2 = ccNames[Math.floor(Math.random() * ccNames.length)];
        const isOverride = Math.random() > 0.92;
        html += `<td><div class="crew-cell">
          <span class="crew-name lcc ${isOverride ? 'override' : ''}" title="${lcc} (LCC)">${lcc}</span>
          <span class="crew-name cc" title="${cc1} (CC)">${cc1}</span>
          <span class="crew-name cc" title="${cc2} (CC)">${cc2}</span>
        </div></td>`;
      }
    }
    tr.innerHTML = html;
    tbody.appendChild(tr);
  });
</script>
</body>
</html>
