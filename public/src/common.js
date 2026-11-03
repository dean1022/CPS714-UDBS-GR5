// Browser-only UI logic. All business rules and database operations happen on Render (Python).
const API_URL = "https://cps714-udbs-gr5.onrender.com";
const libraryUrl = API_URL.replace(/\/$/, "") + "/api";
async function libraryRequest(action, options = {}) {
  const parts = action.split("&");
  const search = new URLSearchParams(parts.slice(1).join("&"));
  let endpoint =
    parts[0] === "session"
      ? "/session"
      : parts[0] === "books"
        ? "/books?" + search
        : parts[0] === "book"
          ? "/book/" + encodeURIComponent(search.get("id"))
          : "/" + parts[0];
  let token = sessionStorage.getItem("udbs_token");
  let headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = "Bearer " + token;
  let response;
  try {
    response = await fetch(libraryUrl + endpoint, {
      ...options,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new Error(
      "Cannot connect to the Python backend on Render. Check API_URL and CORS.",
    );
  }
  const ct = response.headers.get("content-type") || "";
  let data = ct.includes("application/json") ? await response.json() : {};
  if (response.status === 401 && parts[0] !== "login") {
    sessionStorage.removeItem("udbs_token");
    location.replace("index.html?expired=1");
    throw new Error("Please sign in again.");
  }
  if (!response.ok)
    throw new Error(data.message || data.detail || "Request failed");
  if (parts[0] === "login") sessionStorage.setItem("udbs_token", data.token);
  return data;
}
function showPageError(err) {
  let node = document.querySelector("#page-message");
  if (node) {
    node.textContent = err.message || "Request failed";
    node.classList.add("error");
  }
}
async function checkLogin() {
  const d = await libraryRequest("session");
  const b = document.querySelector("#logout-button");
  if (b) b.hidden = false;
  return d.user;
}
async function logout() {
  try {
    await libraryRequest("logout", { method: "POST" });
  } catch (e) {
    console.warn(e.message);
  }
  sessionStorage.removeItem("udbs_token");
  location.replace("index.html?logout=1");
}
function safeText(s) {
  let e = document.createElement("span");
  e.textContent = s ?? "";
  return e.innerHTML;
}
const logoutButton = document.querySelector("#logout-button");
if (logoutButton) logoutButton.addEventListener("click", logout);

// Shows a normal (not error) message at the top of the page
function showPageMessage(text) {
  let node = document.querySelector("#page-message");
  if (node) {
    node.textContent = text;
    node.classList.remove("error");
  }
}

// The backend saves times in UTC without a timezone, e.g. "2026-11-02 21:30"
function utcMillis(value) {
  const raw = String(value || "").trim().replace(" ", "T");
  if (!raw) return NaN;
  return new Date(/[zZ]$|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : raw + "Z").getTime();
}

// Shows a saved time in Toronto time, e.g. "Nov 2, 2026, 4:30 p.m. EST"
function torontoTime(value) {
  const timestamp = utcMillis(value);
  if (!Number.isFinite(timestamp)) return "Unavailable";
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto", month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit", hour12: true, timeZoneName: "short",
  }).format(new Date(timestamp));
}

// Time left until a saved time, e.g. "2 days 5 hours 12 minutes"
function timeLeftUntil(value) {
  const end = utcMillis(value);
  const left = Number.isFinite(end) ? Math.max(0, end - Date.now()) : 0;
  const days = Math.floor(left / 86400000);
  const hours = Math.floor((left % 86400000) / 3600000);
  const minutes = Math.floor((left % 3600000) / 60000);
  const word = (n, unit) => `${n} ${unit}${n === 1 ? "" : "s"}`;
  return `${word(days, "day")} ${word(hours, "hour")} ${word(minutes, "minute")}`;
}
