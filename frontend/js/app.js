const API = ""; // same origin when served by FastAPI
let currentUser = null;
let lastBlocks = [];

// Always available so login works even if API is slow/down
const FALLBACK_USERS = [
  { id: 1, name: "Section Controller", role: "Section Controller", department: "Control Office", initials: "SC", zone: "Northern Railway" },
  { id: 2, name: "SSE (P.Way)", role: "SSE (P.Way)", department: "Engineering", initials: "PW", zone: "Northern Railway" },
  { id: 3, name: "SSE (Signal)", role: "SSE (Signal)", department: "S&T", initials: "ST", zone: "Northern Railway" },
  { id: 4, name: "SSE (TRD)", role: "SSE (TRD)", department: "Traction", initials: "TR", zone: "Northern Railway" },
  { id: 5, name: "Sr. DEN", role: "Sr. DEN", department: "Divisional", initials: "DN", zone: "Delhi Division" },
];
let USERS_CACHE = FALLBACK_USERS;

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 3000);
}

function renderRoleList(users) {
  USERS_CACHE = users && users.length ? users : FALLBACK_USERS;
  const list = document.getElementById("role-list");
  if (!list) return;
  list.innerHTML = USERS_CACHE.map((u) => `
    <button type="button" data-user-id="${u.id}"
      class="role-btn w-full flex items-center gap-4 p-3.5 rounded-xl border border-slate-200 hover:border-sky-400 hover:bg-sky-50 text-left transition">
      <div class="w-11 h-11 rounded-full bg-rail-600 text-white flex items-center justify-center font-semibold shrink-0">${u.initials}</div>
      <div class="min-w-0">
        <div class="font-semibold text-sm text-slate-800">${u.role}</div>
        <div class="text-xs text-slate-500">${u.department || ""} · ${u.zone || ""}</div>
      </div>
      <i class="fas fa-chevron-right text-slate-300 ml-auto"></i>
    </button>`).join("");

  list.querySelectorAll(".role-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.getAttribute("data-user-id"), 10);
      const u = USERS_CACHE.find((x) => x.id === id) || FALLBACK_USERS.find((x) => x.id === id);
      if (u) login(u);
    });
  });
}

async function loadUsers() {
  // Always show designation-only roles first
  renderRoleList(FALLBACK_USERS);
  try {
    const users = await api("/api/users");
    if (users && users.length) {
      // Force display = designation only (ignore any personal names in DB)
      const cleaned = users.map((u) => ({
        id: u.id,
        role: u.role,
        name: u.role,
        department: u.department,
        initials: u.initials || (u.role || "?").slice(0, 2).toUpperCase(),
        zone: u.zone,
      }));
      renderRoleList(cleaned);
    }
  } catch (e) {
    console.warn("API users failed, using fallback roles", e);
  }
}

function login(u) {
  currentUser = u;
  document.getElementById("login-screen").classList.add("hidden");
  const app = document.getElementById("app");
  app.classList.remove("hidden");
  app.classList.add("flex");
  document.getElementById("u-av").textContent = u.initials;
  document.getElementById("u-name").textContent = u.role || u.name;
  document.getElementById("u-role").textContent = u.department || u.zone || "";
  showView("dashboard");
  toast("Logged in as " + (u.role || u.name));
}

function logout() {
  currentUser = null;
  document.getElementById("app").classList.add("hidden");
  document.getElementById("app").classList.remove("flex");
  document.getElementById("login-screen").classList.remove("hidden");
}

document.querySelectorAll(".sidebar-link").forEach((btn) => {
  btn.addEventListener("click", () => showView(btn.dataset.view, btn));
});

function showView(name, btn) {
  document.querySelectorAll("[id^='view-']").forEach((el) => el.classList.add("hidden"));
  const v = document.getElementById("view-" + name);
  if (v) v.classList.remove("hidden");
  document.querySelectorAll(".sidebar-link").forEach((b) => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  else {
    const b = document.querySelector(`.sidebar-link[data-view="${name}"]`);
    if (b) b.classList.add("active");
  }
  const titles = {
    dashboard: "Dashboard",
    tasks: "AI Task Priority",
    schedule: "Train Schedule (Delhi–Ghaziabad)",
    optimizer: "AI Block Optimizer",
    approval: "Officer Approval",
    resources: "Resources & Personnel",
    whatif: "What-If Simulator",
  };
  document.getElementById("page-title").textContent = titles[name] || name;
  if (name === "dashboard") renderDashboard();
  if (name === "tasks") renderTasks();
  if (name === "schedule") renderSchedule();
  if (name === "optimizer") renderOptimizer();
  if (name === "approval") renderApproval();
  if (name === "resources") renderResources();
  if (name === "whatif") renderWhatIf();
}

async function renderDashboard() {
  const el = document.getElementById("view-dashboard");
  el.innerHTML = `<p class="text-slate-500">Loading…</p>`;
  try {
    const [tasks, blocks] = await Promise.all([api("/api/tasks"), api("/api/blocks")]);
    lastBlocks = blocks;
    const critical = tasks.filter((t) => t.priority === "Critical").length;
    const proposed = blocks.filter((b) => b.status === "proposed").length;
    const approved = blocks.filter((b) => b.status === "approved").length;
    el.innerHTML = `
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white rounded-xl border p-5"><div class="text-sm text-slate-500">Pending Tasks</div><div class="text-3xl font-bold">${tasks.length}</div><div class="text-xs text-amber-600">${critical} Critical</div></div>
        <div class="bg-white rounded-xl border p-5"><div class="text-sm text-slate-500">Proposed Blocks</div><div class="text-3xl font-bold text-rail-600">${proposed}</div></div>
        <div class="bg-white rounded-xl border p-5"><div class="text-sm text-slate-500">Approved</div><div class="text-3xl font-bold text-emerald-600">${approved}</div></div>
        <div class="bg-white rounded-xl border p-5"><div class="text-sm text-slate-500">Section</div><div class="text-xl font-bold">Delhi–Ghaziabad</div><div class="text-xs text-slate-500">NR · ~20.5 km</div></div>
      </div>
      <div class="bg-white rounded-xl border p-5 mt-4">
        <h3 class="font-semibold mb-3">How AI works on this section</h3>
        <ol class="text-sm text-slate-600 space-y-1 list-decimal list-inside">
          <li>Reads <strong>train schedule</strong> for Delhi–Ghaziabad and finds free gaps</li>
          <li>Ranks maintenance tasks by <strong>AI priority score</strong></li>
          <li>Checks <strong>workers, crane, tower wagon</strong> availability</li>
          <li>Assigns <strong>roles</strong> and sends plan for <strong>officer approval</strong></li>
          <li>What-If: delay / weather impact on availability</li>
        </ol>
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="text-red-600">Backend not running. Start with: <code class="bg-slate-100 px-1">uvicorn main:app --reload</code><br>${e.message}</div>`;
  }
}

async function renderTasks() {
  const el = document.getElementById("view-tasks");
  const tasks = await api("/api/tasks");
  el.innerHTML = `
    <div class="bg-white rounded-xl border overflow-hidden">
      <div class="p-4 border-b font-semibold">AI-Prioritized Tasks (Delhi–Ghaziabad)</div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-left text-slate-500 border-b"><tr>
            <th class="p-3">Code</th><th class="p-3">Description</th><th class="p-3">Dept</th>
            <th class="p-3">AI Score</th><th class="p-3">Priority</th><th class="p-3">Hours</th>
            <th class="p-3">Crane</th><th class="p-3">Tower</th>
          </tr></thead>
          <tbody>
            ${tasks
              .map(
                (t) => `<tr class="border-b hover:bg-slate-50">
              <td class="p-3 font-mono text-xs">${t.task_code}</td>
              <td class="p-3">${t.description}</td>
              <td class="p-3">${t.department}</td>
              <td class="p-3 font-bold">${t.ai_score}</td>
              <td class="p-3"><span class="text-xs px-2 py-0.5 rounded ${
                t.priority === "Critical"
                  ? "bg-red-100 text-red-700"
                  : t.priority === "High"
                  ? "bg-orange-100 text-orange-700"
                  : "bg-slate-100"
              }">${t.priority}</span></td>
              <td class="p-3">${t.est_hours}h</td>
              <td class="p-3">${t.requires_crane ? "Yes" : "—"}</td>
              <td class="p-3">${t.requires_tower_wagon ? "Yes" : "—"}</td>
            </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>`;
}

async function renderSchedule() {
  const el = document.getElementById("view-schedule");
  el.innerHTML = `
    <div class="flex gap-2 mb-4 flex-wrap">
      ${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        .map(
          (d) =>
            `<button onclick="loadDaySchedule('${d}')" class="px-3 py-1.5 rounded-lg border text-sm day-btn" data-day="${d}">${d}</button>`
        )
        .join("")}
    </div>
    <div id="sched-table" class="bg-white rounded-xl border p-4">Select a day</div>
    <div id="gaps-box" class="mt-4"></div>`;
  loadDaySchedule("Mon");
}

async function loadDaySchedule(day) {
  document.querySelectorAll(".day-btn").forEach((b) => {
    b.classList.toggle("bg-rail-600", b.dataset.day === day);
    b.classList.toggle("text-white", b.dataset.day === day);
  });
  const [trains, gaps] = await Promise.all([
    api("/api/schedule?day=" + day),
    api("/api/gaps?day=" + day),
  ]);
  document.getElementById("sched-table").innerHTML = `
    <h3 class="font-semibold mb-2">Trains · ${day}</h3>
    <table class="w-full text-sm">
      <thead class="text-slate-500 text-left"><tr><th class="py-1">Train</th><th>Name</th><th>Dir</th><th>Dep</th><th>Arr</th><th>Type</th></tr></thead>
      <tbody>${trains
        .map(
          (t) =>
            `<tr class="border-t"><td class="py-1 font-mono">${t.train_no}</td><td>${t.train_name}</td><td>${t.direction}</td><td>${t.departure_time}</td><td>${t.arrival_time}</td><td>${t.train_type}</td></tr>`
        )
        .join("")}</tbody>
    </table>`;
  document.getElementById("gaps-box").innerHTML = `
    <div class="bg-white rounded-xl border p-4">
      <h3 class="font-semibold mb-2">AI-found free block windows · ${day}</h3>
      <div class="space-y-2">
        ${gaps
          .map(
            (g) =>
              `<div class="flex justify-between items-center p-3 bg-emerald-50 rounded-lg border border-emerald-100">
            <div><span class="font-semibold">${g.start} – ${g.end}</span> <span class="text-sm text-slate-500">(${g.duration_hours}h)</span>
            <div class="text-xs text-slate-500">${g.reason}</div></div>
            <div class="text-sm font-bold text-emerald-700">Suitability ${g.suitability}</div>
          </div>`
          )
          .join("") || "<p class='text-slate-500'>No gap ≥ 90 min</p>"}
      </div>
    </div>`;
}

async function runOptimize() {
  toast("Running AI optimizer…");
  const data = await api("/api/optimize", { method: "POST" });
  lastBlocks = data.blocks;
  toast(`AI generated ${data.count} block proposals`);
  showView("optimizer");
}

async function renderOptimizer() {
  const el = document.getElementById("view-optimizer");
  el.innerHTML = `<p class="text-slate-500 mb-3">Click <strong>Run AI Optimizer</strong> to generate blocks from train gaps + priority + resources.</p><div id="opt-list"></div>`;
  let blocks = lastBlocks;
  if (!blocks.length) {
    try {
      blocks = await api("/api/blocks");
      lastBlocks = blocks;
    } catch (_) {}
  }
  const list = document.getElementById("opt-list");
  if (!blocks.length) {
    list.innerHTML = `<button onclick="runOptimize()" class="bg-rail-600 text-white px-4 py-2 rounded-lg">Run AI Optimizer</button>`;
    return;
  }
  list.innerHTML = blocks
    .map((b) => {
      const res = b.resource_check || {
        summary: b.resource_status,
        notes: b.resource_notes,
        details: [],
      };
      const tasks = b.tasks || [];
      const roles = b.role_assignments || [];
      return `
      <div class="bg-white rounded-xl border p-5 mb-4 ${
        res.summary === "SHORTAGE" || b.resource_status === "SHORTAGE" ? "ring-2 ring-amber-300" : ""
      }">
        <div class="flex justify-between gap-4 flex-wrap">
          <div>
            <div class="font-bold text-rail-700">${b.block_code || b.block_code}</div>
            <div class="text-sm">${b.day || b.day_of_week} · ${b.start_time} – ${b.end_time} (${b.duration_hours}h)</div>
            <div class="text-xs text-slate-500">${b.gap_reason || "From train schedule gaps"}</div>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold text-rail-600">${b.ai_score || "—"}</div>
            <div class="text-xs">AI Score</div>
            <div class="mt-1 text-xs font-semibold ${
              (res.summary || b.resource_status) === "READY" ? "text-emerald-600" : "text-amber-600"
            }">${res.summary || b.resource_status || ""}</div>
          </div>
        </div>
        <div class="mt-3 text-sm"><strong>Tasks:</strong>
          <ul class="list-disc list-inside text-slate-600">${tasks
            .map((t) => `<li>${t.task_code}: ${t.description} (${t.department})</li>`)
            .join("")}</ul>
        </div>
        ${
          roles.length
            ? `<div class="mt-2 text-sm"><strong>AI role assignment:</strong>
          <ul class="list-disc list-inside text-slate-600">${roles
            .map((r) => `<li>${r.task_code}: ${(r.roles || []).join(", ")}</li>`)
            .join("")}</ul></div>`
            : ""
        }
        <div class="mt-2 text-xs text-slate-500">${res.notes || b.resource_notes || ""}</div>
        ${
          (res.details || []).length
            ? `<div class="mt-2 grid grid-cols-2 gap-2 text-xs">${res.details
                .map(
                  (d) =>
                    `<div class="p-2 rounded ${
                      d.status === "Available" ? "bg-emerald-50" : "bg-amber-50"
                    }">${d.item}: ${d.available}/${d.required} — <strong>${d.status}</strong></div>`
                )
                .join("")}</div>`
            : ""
        }
      </div>`;
    })
    .join("");
}

async function renderApproval() {
  const el = document.getElementById("view-approval");
  const blocks = await api("/api/blocks");
  lastBlocks = blocks;
  el.innerHTML = `
    <p class="text-sm text-slate-500 mb-4">Officer reviews AI proposals. Approve / Reject with comment.</p>
    <div class="space-y-4">
      ${blocks
        .map(
          (b) => `
        <div class="bg-white rounded-xl border p-5">
          <div class="flex justify-between flex-wrap gap-2">
            <div>
              <div class="font-bold">${b.block_code}</div>
              <div class="text-sm">${b.day_of_week} ${b.start_time}–${b.end_time}</div>
              <div class="text-xs mt-1">Status: <span class="font-semibold">${b.status}</span> · Resources: ${b.resource_status}</div>
            </div>
            <div class="flex gap-2 items-start">
              <button onclick="doApprove('${b.block_code}','approved')" class="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm">Approve</button>
              <button onclick="doApprove('${b.block_code}','rejected')" class="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm">Reject</button>
            </div>
          </div>
          <ul class="mt-2 text-sm text-slate-600 list-disc list-inside">${(b.tasks || [])
            .map((t) => `<li>${t.task_code} – ${t.description}</li>`)
            .join("")}</ul>
          <input id="cmt-${b.block_code}" class="mt-2 w-full border rounded-lg px-3 py-1.5 text-sm" placeholder="Officer comment (optional)" />
        </div>`
        )
        .join("") || "<p>No blocks yet. Run AI Optimizer first.</p>"}
    </div>`;
}

async function doApprove(code, decision) {
  const comment = document.getElementById("cmt-" + code)?.value || "";
  await api("/api/approve", {
    method: "POST",
    body: JSON.stringify({
      block_code: code,
      officer_id: currentUser?.id || 1,
      decision,
      comment,
    }),
  });
  toast(`${code} ${decision}`);
  renderApproval();
}

async function renderResources() {
  const el = document.getElementById("view-resources");
  el.innerHTML = `
    <div class="flex gap-2 mb-4 flex-wrap">${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
      .map((d) => `<button onclick="loadRes('${d}')" class="px-3 py-1.5 border rounded-lg text-sm res-day" data-day="${d}">${d}</button>`)
      .join("")}</div>
    <div id="res-list" class="bg-white rounded-xl border p-4">Select day</div>`;
  loadRes("Mon");
}

async function loadRes(day) {
  document.querySelectorAll(".res-day").forEach((b) => {
    b.classList.toggle("bg-rail-600", b.dataset.day === day);
    b.classList.toggle("text-white", b.dataset.day === day);
  });
  const rows = await api("/api/resources?day=" + day);
  document.getElementById("res-list").innerHTML = `
    <h3 class="font-semibold mb-3">Availability · ${day}</h3>
    <table class="w-full text-sm">
      <thead class="text-left text-slate-500"><tr><th class="py-1">Resource</th><th>Type</th><th>Dept</th><th>Available</th></tr></thead>
      <tbody>${rows
        .map(
          (r) =>
            `<tr class="border-t"><td class="py-1">${r.name}</td><td>${r.resource_type}</td><td>${r.department}</td><td class="font-semibold">${r.available_count}</td></tr>`
        )
        .join("")}</tbody>
    </table>
    <p class="text-xs text-slate-500 mt-3">Crane available Tue/Thu/Sat only in this demo data. Tower wagon unavailable on Wed.</p>`;
}

async function renderWhatIf() {
  const el = document.getElementById("view-whatif");
  const blocks = await api("/api/blocks");
  lastBlocks = blocks;
  const opts = blocks.map((b) => `<option value="${b.block_code}">${b.block_code} (${b.day_of_week})</option>`).join("");
  el.innerHTML = `
    <div class="grid md:grid-cols-2 gap-6">
      <div class="bg-white rounded-xl border p-5">
        <h3 class="font-semibold mb-3">Delay impact</h3>
        <label class="text-sm">Block</label>
        <select id="wi-block" class="w-full border rounded-lg px-3 py-2 mb-3 text-sm">${opts || "<option>No blocks</option>"}</select>
        <label class="text-sm">Delay (hours)</label>
        <input id="wi-delay" type="number" value="3" min="0.5" step="0.5" class="w-full border rounded-lg px-3 py-2 mb-3 text-sm" />
        <button onclick="runDelay()" class="w-full bg-rail-600 text-white py-2 rounded-lg text-sm font-semibold">Simulate Delay</button>
      </div>
      <div class="bg-white rounded-xl border p-5">
        <h3 class="font-semibold mb-3">Weather impact</h3>
        <label class="text-sm">Block</label>
        <select id="wi-block2" class="w-full border rounded-lg px-3 py-2 mb-3 text-sm">${opts || "<option>No blocks</option>"}</select>
        <label class="text-sm">Weather</label>
        <select id="wi-weather" class="w-full border rounded-lg px-3 py-2 mb-3 text-sm">
          <option value="rain">Rain</option>
          <option value="heavy_rain">Heavy rain</option>
          <option value="fog">Fog</option>
          <option value="heat">Extreme heat</option>
          <option value="storm">Storm</option>
        </select>
        <button onclick="runWeather()" class="w-full bg-rail-600 text-white py-2 rounded-lg text-sm font-semibold">Simulate Weather</button>
      </div>
    </div>
    <div id="wi-result" class="mt-6 bg-slate-50 rounded-xl border p-5 text-sm text-slate-600">Run a simulation to see AI impact analysis.</div>`;
}

async function runDelay() {
  const block_code = document.getElementById("wi-block").value;
  const delay_hours = parseFloat(document.getElementById("wi-delay").value);
  const r = await api("/api/whatif/delay", {
    method: "POST",
    body: JSON.stringify({ block_code, delay_hours }),
  });
  document.getElementById("wi-result").innerHTML = `
    <h4 class="font-bold text-amber-700 mb-2">Delay scenario · ${r.block_code}</h4>
    <p>Window: ${r.original_window} · Delay: ${r.delay_hours}h</p>
    <p class="mt-2">Projected availability: <strong class="text-amber-600">${r.projected_availability}%</strong> (drop ${r.availability_drop}%)</p>
    <ul class="list-disc list-inside mt-2">${(r.effects || []).map((e) => `<li>${e}</li>`).join("")}</ul>
    <p class="mt-2 text-rail-700"><strong>AI suggestion:</strong> ${r.ai_suggestion}</p>`;
}

async function runWeather() {
  const block_code = document.getElementById("wi-block2").value;
  const weather = document.getElementById("wi-weather").value;
  const r = await api("/api/whatif/weather", {
    method: "POST",
    body: JSON.stringify({ block_code, weather }),
  });
  document.getElementById("wi-result").innerHTML = `
    <h4 class="font-bold mb-2">Weather · ${r.weather} · Risk: ${r.risk_level}</h4>
    <p>${r.message}</p>
    <p class="mt-2"><strong>Recommended:</strong> ${r.recommended}</p>
    <ul class="list-disc list-inside mt-2">${(r.ai_actions || []).map((e) => `<li>${e}</li>`).join("")}</ul>`;
}

// Show roles immediately; API enriches if backend is up
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => loadUsers());
} else {
  loadUsers();
}
