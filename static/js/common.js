const API = getApiBase();
const TOKEN_KEY = "sirius_token";

function getApiBase() {
  const { protocol, hostname, pathname, port } = window.location;

  if (protocol === "file:") {
    return "http://127.0.0.1:8000";
  }

  if (pathname.startsWith("/ui/") || pathname === "/ui") {
    return "";
  }

  const apiPort = localStorage.getItem("sirius_api_port") || "8000";
  if (port && port !== apiPort) {
    return `${protocol}//${hostname}:${apiPort}`;
  }

  return "";
}

function formatApiError(status, message) {
  if (status === 404 && message === "Not Found") {
    return "API не найден. Запустите сервер и откройте сайт по адресу http://127.0.0.1:8000/ui/";
  }
  if (status === 401 && message === "Not authenticated") {
    return "Сессия истекла. Войдите снова";
  }
  return message;
}

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatPlaces(count) {
  const n = Math.abs(Number(count));
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} место`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${count} места`;
  return `${count} мест`;
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function setStatus(el, text, ok = true) {
  if (!el) return;
  el.textContent = text;
  el.className = ok ? "status success" : "status error";
}

function renderTags(items) {
  if (!items.length) return '<span class="tag">без оборудования</span>';
  return items.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("");
}

function parseLocalDateTime(value) {
  const raw = String(value);
  if (raw.includes("T") && !raw.endsWith("Z") && !raw.includes("+")) {
    return new Date(raw);
  }
  return new Date(raw);
}

function formatBookingRange(start, end) {
  const startDate = parseLocalDateTime(start);
  const endDate = parseLocalDateTime(end);
  const sameDay =
    startDate.getFullYear() === endDate.getFullYear() &&
    startDate.getMonth() === endDate.getMonth() &&
    startDate.getDate() === endDate.getDate();

  const dateLabel = startDate.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
  });
  const startTime = startDate.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const endTime = endDate.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (sameDay) {
    return `${dateLabel}, ${startTime} — ${endTime}`;
  }

  const endDateLabel = endDate.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
  });
  return `${dateLabel}, ${startTime} — ${endDateLabel}, ${endTime}`;
}

function formatBookingCode(code) {
  return code ? `<span class="booking-code">${escapeHtml(code)}</span>` : "";
}

function formatBookingLine(code, start, end) {
  return `${formatBookingCode(code)} ${formatBookingRange(start, end)}`.trim();
}

function formatBookingStatus(status) {
  return (
    {
      active: "Активно",
      cancelled: "Отменено",
      completed: "Завершено",
    }[status] || status
  );
}

function renderBookingInfo(booking, roomName) {
  const userName = booking.user_name || "—";
  const status = booking.status || "active";
  return `<div class="tile-info">
    <strong>${escapeHtml(roomName)}</strong>
    <span class="tile-meta">${formatBookingLine(booking.code, booking.start_time, booking.end_time)}</span>
    <span class="booking-card-meta">
      <span class="booking-card-user">${escapeHtml(userName)}</span>
      <span class="booking-status booking-status-${escapeHtml(status)}">${escapeHtml(formatBookingStatus(status))}</span>
    </span>
  </div>`;
}

function renderBookingCard(booking, roomName) {
  return `<li class="booking-card">${renderBookingInfo(booking, roomName)}</li>`;
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers });
  } catch {
    throw new Error("Не удалось подключиться к серверу. Запустите start.bat и откройте http://127.0.0.1:8000/ui/");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = "Ошибка запроса";
    if (typeof data.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail.map((item) => item.msg || item).join(", ");
    }
    throw new Error(formatApiError(response.status, message));
  }
  return data;
}

async function login(username, password) {
  const form = new FormData();
  form.append("username", username);
  form.append("password", password);
  const data = await api("/auth/login", { method: "POST", body: form });
  setToken(data.access_token);
}

async function register(username, password) {
  await api("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  await login(username, password);
}

function requireAuth() {
  if (!getToken()) {
    redirectToLogin();
  }
}

function isAuthed() {
  return Boolean(getToken());
}

function getLoginNextUrl() {
  const file = window.location.pathname.split("/").pop() || "index.html";
  const search = window.location.search || "";
  if (!file || file === "login.html") return "index.html";
  return `${file}${search}`;
}

function redirectToLogin() {
  const next = encodeURIComponent(getLoginNextUrl());
  window.location.href = `login.html?next=${next}`;
}

function getPostLoginRedirect() {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  if (!next || next.includes("login.html")) return "index.html";
  return next;
}

function hasBookingProfile(profile) {
  if (!profile) return false;
  if (profile.booking_profile_complete) return true;
  return (
    Boolean(profile.full_name?.trim()) &&
    Boolean(profile.phone?.trim()) &&
    Boolean(profile.email?.trim())
  );
}

let cachedProfile = null;

async function fetchProfile(force = false) {
  if (!isAuthed()) {
    cachedProfile = null;
    return null;
  }
  if (!force && cachedProfile) return cachedProfile;
  try {
    cachedProfile = await api("/profile/me");
    return cachedProfile;
  } catch {
    cachedProfile = null;
    return null;
  }
}

function showBookingContactPanel(profile) {
  const panel = document.getElementById("booking-contact");
  if (!panel) return;

  if (!isAuthed() || hasBookingProfile(profile)) {
    panel.classList.add("hidden");
    panel.querySelectorAll("input").forEach((input) => input.removeAttribute("required"));
    return;
  }

  panel.classList.remove("hidden");
  const fullNameEl = document.getElementById("contact-full-name");
  const phoneEl = document.getElementById("contact-phone");
  const emailEl = document.getElementById("contact-email");
  if (fullNameEl) {
    fullNameEl.value = profile?.full_name || "";
    fullNameEl.required = true;
  }
  if (phoneEl) {
    phoneEl.value = profile?.phone || "";
    phoneEl.required = true;
  }
  if (emailEl) {
    emailEl.value = profile?.email || "";
    emailEl.required = true;
  }
}

function getBookingContactPayload() {
  const fullName = document.getElementById("contact-full-name")?.value.trim() || "";
  const phone = document.getElementById("contact-phone")?.value.trim() || "";
  const email = document.getElementById("contact-email")?.value.trim() || "";
  if (!fullName && !phone && !email) return {};
  return { full_name: fullName, phone, email };
}

async function ensureBookingProfile() {
  if (!isAuthed()) {
    redirectToLogin();
    return false;
  }

  const profile = await fetchProfile();
  if (hasBookingProfile(profile)) return true;

  const contact = getBookingContactPayload();
  if (!contact.full_name || !contact.phone || !contact.email) {
    showBookingContactPanel(profile);
    throw new Error("Заполните ФИО, телефон и почту");
  }

  return true;
}

function initSiteNav() {
  const loginLink = document.getElementById("login-link");
  const profileLink = document.querySelector(".nav-profile");
  const logoutBtn = document.getElementById("logout-btn");
  const authed = isAuthed();

  loginLink?.classList.toggle("hidden", authed);
  profileLink?.classList.toggle("hidden", !authed);
  logoutBtn?.classList.toggle("hidden", !authed);
  document.querySelectorAll(".nav-auth-only").forEach((el) => {
    el.classList.toggle("hidden", !authed);
  });

  if (logoutBtn && !logoutBtn.dataset.bound) {
    logoutBtn.dataset.bound = "1";
    logoutBtn.addEventListener("click", () => {
      clearToken();
      cachedProfile = null;
      window.location.href = "index.html";
    });
  }

  if (authed && profileLink) {
    fetchProfile().then((profile) => {
      const img = profileLink.querySelector(".nav-profile-img");
      if (img && profile?.avatar_url) img.src = profile.avatar_url;
    });
  }
}

function redirectIfAuthed(target = "index.html") {
  if (getToken()) {
    window.location.href = target;
  }
}

function initLogout() {
  initSiteNav();
}

function initProfileNav() {
  initSiteNav();
}

async function fetchRooms(params = {}) {
  const search = new URLSearchParams();
  if (params.capacity) search.set("capacity", params.capacity);
  if (params.equipment) search.set("equipment", params.equipment);
  const query = search.toString();
  return api(`/rooms${query ? `?${query}` : ""}`);
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".site-nav") || document.querySelector(".home-header")) initAppShell();
  });
}
