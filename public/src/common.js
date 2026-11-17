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
  if (!response.ok) {
    afterAction(parts[0], options); // refused actions leave an error notification too (US-14)
    throw new Error(data.message || data.detail || "Request failed");
  }
  if (parts[0] === "login") sessionStorage.setItem("udbs_token", data.token);
  afterAction(parts[0], options);
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
  showRole(d.user);
  startNotifications(d.user);
  return d.user;
}
async function logout() {
  try {
    await libraryRequest("logout", { method: "POST" });
  } catch (e) {
    console.warn(e.message);
  }
  sessionStorage.removeItem("udbs_token");
  sessionStorage.removeItem("udbs_user");
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

// ---------------------------------------------------------------------------------------------
// Role distinction (Sprint 4): a Student or Faculty chip in the navigation bar
// ---------------------------------------------------------------------------------------------
function showRole(user) {
  if (!user) return;
  sessionStorage.setItem("udbs_user", JSON.stringify(user));
  const links = document.querySelector(".nav-links");
  if (!links || links.querySelector(".role-chip")) return;
  const chip = document.createElement("span");
  chip.className = "role-chip" + (user.is_staff ? " faculty" : "");
  chip.textContent = user.role_label || (user.is_staff ? "Faculty" : "Student");
  chip.title = user.is_staff
    ? "Faculty privileges: " + (user.perks || []).join(", ")
    : "Student account";
  const logoutBtn = links.querySelector("#logout-button");
  links.insertBefore(chip, logoutBtn);
}

// ---------------------------------------------------------------------------------------------
// Notifications (US-14 / FR-23)
// New notifications pop up on the page you're on, fade away after a few seconds,
// and stay saved on the Notifications page.
// ---------------------------------------------------------------------------------------------
const TOAST_SECONDS = 6;
const NOTE_ACTIONS = ["borrow", "return", "renew", "hold", "holds"];
let noteUser = null;
let noteTimer = null;
let noteBusy = false;
let noteAgain = false; // an action happened while a check was running, so check once more right after

function lastSeenKey() {
  return "udbs_last_note_" + (noteUser ? noteUser.user_id : "x");
}

// After borrow, return, renew or a hold action, check right away so the pop-up shows on this page
function afterAction(action, options) {
  if ((options.method || "GET") !== "POST") return;
  if (NOTE_ACTIONS.includes(action.split("/")[0])) setTimeout(checkNotifications, 150);
}

function startNotifications(user) {
  if (noteTimer || !user) return;
  noteUser = user;
  checkNotifications();
  // reminders (hold ready, window closing, loan due soon) can happen while you're on any page
  noteTimer = setInterval(() => { if (!document.hidden) checkNotifications(); }, 20000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) checkNotifications(); });
}

async function checkNotifications() {
  if (!sessionStorage.getItem("udbs_token")) return;
  if (noteBusy) { noteAgain = true; return; }
  noteBusy = true;
  try {
    const data = await libraryRequest("notifications/summary");
    setBadge(data.unread);
    let seen = Number(localStorage.getItem(lastSeenKey()));
    if (!localStorage.getItem(lastSeenKey())) seen = data.latest_id; // first visit: don't replay old ones
    const fresh = data.newest.filter((n) => n.notification_id > seen).reverse();
    localStorage.setItem(lastSeenKey(), String(Math.max(seen, data.latest_id)));
    if (fresh.length) {
      document.dispatchEvent(new CustomEvent("udbs:notifications", { detail: fresh }));
      if (!document.body.classList.contains("notifications-page")) fresh.slice(-3).forEach(showToast);
    }
  } catch (e) {
    console.warn("Notifications unavailable:", e.message);
  } finally {
    noteBusy = false;
    if (noteAgain) { noteAgain = false; checkNotifications(); }
  }
}

function setBadge(count) {
  document.querySelectorAll(".nav-badge").forEach((badge) => {
    badge.textContent = count > 99 ? "99+" : String(count);
    badge.hidden = !count;
    badge.setAttribute("aria-label", count + " unread notifications");
  });
}

function toastArea() {
  let area = document.querySelector("#toast-area");
  if (!area) {
    area = document.createElement("div");
    area.id = "toast-area";
    area.setAttribute("aria-live", "polite");
    area.setAttribute("role", "status");
    document.body.appendChild(area);
  }
  return area;
}

function noteKindClass(type) {
  if (["ERROR", "LOAN_LIMIT", "HOLD_LIMIT", "HOLD_EXPIRED"].includes(type)) return "bad";
  if (["HOLD_READY", "HOLD_WINDOW_CLOSING", "LOAN_DUE_SOON"].includes(type)) return "action";
  return "good";
}

function showToast(note) {
  const toast = document.createElement("div");
  toast.className = "udbs-toast " + noteKindClass(note.type);
  toast.innerHTML = `<div class="toast-text">
      <strong>${safeText(note.title)}</strong>
      <span>${safeText(note.message)}</span>
      <a href="notifications.html">See all notifications</a>
    </div>
    <button type="button" class="toast-close" aria-label="Dismiss">&times;</button>
    <span class="toast-timer" style="animation-duration:${TOAST_SECONDS}s"></span>`;
  let left = TOAST_SECONDS * 1000;
  let started = Date.now();
  let timer = setTimeout(close, left);
  function close() {
    clearTimeout(timer);
    toast.classList.add("leaving");
    setTimeout(() => toast.remove(), 300);
  }
  // hovering keeps it on screen so it can be read
  toast.addEventListener("mouseenter", () => {
    clearTimeout(timer);
    left -= Date.now() - started;
    toast.classList.add("paused");
  });
  toast.addEventListener("mouseleave", () => {
    started = Date.now();
    timer = setTimeout(close, Math.max(1200, left));
    toast.classList.remove("paused");
  });
  toast.querySelector(".toast-close").onclick = close;
  toastArea().appendChild(toast);
}
