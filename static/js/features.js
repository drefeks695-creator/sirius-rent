const FAVORITES_KEY = "sirius_favorites";
const THEME_KEY = "sirius_theme";

const SIRIUS_TIPS = [
  "Актовый зал лучше бронировать заранее",
  "★ — добавить зал в избранное",
  "Фильтр по оборудованию — чипы под поиском",
  "Свободные слоты видно в календаре на странице зала",
  "Отменить бронь можно в профиле",
  "Коворкинг С-12 — всего 9 мест",
  "Перед бронью заполните профиль",
];

function getFavorites() {
  try {
    const data = JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]");
    return Array.isArray(data) ? data.map(Number) : [];
  } catch {
    return [];
  }
}

function isFavorite(roomId) {
  return getFavorites().includes(Number(roomId));
}

function toggleFavorite(roomId) {
  const id = Number(roomId);
  const favorites = getFavorites();
  const next = favorites.includes(id)
    ? favorites.filter((item) => item !== id)
    : [...favorites, id];
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
  return next.includes(id);
}

function getTimeGreeting() {
  const hour = new Date().getHours();
  if (hour < 6) return "Доброй ночи";
  if (hour < 12) return "Доброе утро";
  if (hour < 18) return "Добрый день";
  return "Добрый вечер";
}

function randomTip() {
  return SIRIUS_TIPS[Math.floor(Math.random() * SIRIUS_TIPS.length)];
}

function ensureToastHost() {
  let host = document.getElementById("toast-host");
  if (!host) {
    host = document.createElement("div");
    host.id = "toast-host";
    host.className = "toast-host";
    host.setAttribute("aria-live", "polite");
    document.body.appendChild(host);
  }
  return host;
}

function showToast(message, ok = true) {
  const host = ensureToastHost();
  const toast = document.createElement("div");
  toast.className = `toast ${ok ? "toast-ok" : "toast-err"}`;
  toast.textContent = message;
  host.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

function spawnConfetti(count = 28) {
  const colors = ["#c45c3a", "#2a7a8c", "#f4b942", "#5c6b4a", "#fffaf3"];
  for (let i = 0; i < count; i += 1) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = `${Math.random() * 100}vw`;
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = `${Math.random() * 0.35}s`;
    piece.style.transform = `rotate(${Math.random() * 360}deg)`;
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 1800);
  }
}

function applyTheme(theme) {
  document.body.classList.toggle("theme-night", theme === "night");
  localStorage.setItem(THEME_KEY, theme);
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.setAttribute("aria-pressed", theme === "night" ? "true" : "false");
    btn.title = theme === "night" ? "Светлая тема" : "Контрастная тема";
  });
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  applyTheme(saved === "night" ? "night" : "day");
}

function initThemeToggle() {
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    if (btn.dataset.bound) return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", () => {
      const next = document.body.classList.contains("theme-night") ? "day" : "night";
      applyTheme(next);
      showToast(next === "night" ? "Контрастная тема включена" : "Светлая тема");
    });
  });

  if (!document.querySelector("[data-theme-toggle]")) {
    const nav = document.querySelector(".nav-links");
    if (!nav || nav.querySelector("[data-theme-toggle]")) return;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-soft btn-sm btn-icon";
    btn.dataset.themeToggle = "1";
    nav.insertBefore(btn, nav.querySelector(".nav-profile"));
    initThemeToggle();
    return;
  }

  applyTheme(localStorage.getItem(THEME_KEY) === "night" ? "night" : "day");
}

function initHomeHeader() {
  const menuBtn = document.getElementById("home-menu-btn");
  const mobileNav = document.getElementById("home-mobile-nav");
  const searchBtn = document.getElementById("home-search-btn");
  const searchInput = document.getElementById("filter-search");

  if (menuBtn && mobileNav && !menuBtn.dataset.bound) {
    menuBtn.dataset.bound = "1";
    menuBtn.addEventListener("click", () => {
      const open = mobileNav.classList.toggle("hidden");
      menuBtn.setAttribute("aria-expanded", open ? "false" : "true");
    });
  }

  if (searchBtn && searchInput && !searchBtn.dataset.bound) {
    searchBtn.dataset.bound = "1";
    searchBtn.addEventListener("click", () => {
      document.getElementById("spaces")?.scrollIntoView({ behavior: "smooth", block: "start" });
      searchInput.focus();
    });
  }
}

async function initBookingBadge() {
  const profileLink = document.querySelector(".nav-profile");
  if (!profileLink || !getToken()) return;

  try {
    const profile = await api("/profile/me");
    const count = profile.bookings?.length || 0;
    let badge = profileLink.querySelector(".nav-badge");
    if (!count) {
      badge?.remove();
      return;
    }
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "nav-badge";
      profileLink.appendChild(badge);
    }
    badge.textContent = String(count);
  } catch {
    /* ignore */
  }
}

async function initAdminNav() {
  if (!isAuthed()) {
    document.querySelectorAll(".nav-admin-only").forEach((el) => el.classList.add("hidden"));
    return;
  }
  const profile = await fetchProfile();
  const isAdmin = profile?.role === "admin";
  document.querySelectorAll(".nav-admin-only").forEach((el) => {
    el.classList.toggle("hidden", !isAdmin);
  });
}

function initAppShell() {
  initSiteNav();
  initTheme();
  initThemeToggle();
  initHomeHeader();
  initAdminNav();
  initBookingBadge();
}

function debounce(fn, ms = 280) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
