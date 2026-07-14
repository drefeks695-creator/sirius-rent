const AVATARS = [
  "/ui/avatars/1.svg",
  "/ui/avatars/2.svg",
  "/ui/avatars/3.svg",
  "/ui/avatars/4.svg",
  "/ui/avatars/5.svg",
  "/ui/avatars/6.svg",
];

requireAuth();
initSiteNav();

let selectedAvatar = AVATARS[0];
let profileLoaded = false;
let usernameDirty = false;
let saving = false;

const profileForm = document.getElementById("profile-form");
const usernameInput = document.getElementById("profile-username");
const saveBtn = profileForm.querySelector('button[type="submit"]');
const avatarUploadInput = document.getElementById("avatar-upload");

function isCustomAvatar(url) {
  return Boolean(url && url.includes("/uploads/avatars/"));
}

function avatarSrc(url) {
  if (!url) return AVATARS[0];
  return isCustomAvatar(url) ? `${url}?v=${Date.now()}` : url;
}

function setAvatar(url) {
  selectedAvatar = url;
  document.getElementById("profile-avatar").src = avatarSrc(url);
  const navAvatar = document.getElementById("nav-avatar");
  if (navAvatar) navAvatar.src = avatarSrc(url);
  document.querySelectorAll(".avatar-option").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.avatar === url);
  });
}

function renderCustomAvatarOption(profile) {
  const container = document.getElementById("avatar-custom");
  if (!profile.custom_avatar_url) {
    container.innerHTML = "";
    return;
  }

  const url = profile.custom_avatar_url;
  container.innerHTML = `<div class="avatar-custom-item">
    <button type="button" class="avatar-option avatar-option-custom" data-avatar="${escapeHtml(url)}">
      <img src="${escapeHtml(avatarSrc(url))}" alt="Ваше фото">
    </button>
    <button type="button" class="btn btn-soft btn-sm avatar-delete-btn" id="avatar-delete-btn">Удалить фото</button>
  </div>`;
}

function applyProfile(profile) {
  document.getElementById("profile-title").textContent = profile.username;
  if (!usernameDirty) {
    usernameInput.value = profile.username;
  }
  document.getElementById("profile-full-name").value = profile.full_name || "";
  document.getElementById("profile-phone").value = profile.phone || "";
  document.getElementById("profile-email").value = profile.email || "";
  document.getElementById("profile-role").textContent =
    profile.role === "admin" ? "Администратор" : "Пользователь";
  renderCustomAvatarOption(profile);
  setAvatar(profile.avatar_url || AVATARS[0]);
  renderBookings(profile.bookings);
}

function setFormReady(ready) {
  profileLoaded = ready;
  saveBtn.disabled = !ready || saving;
  avatarUploadInput.disabled = !ready || saving;
  const deleteBtn = document.getElementById("avatar-delete-btn");
  if (deleteBtn) deleteBtn.disabled = !ready || saving;
  document.querySelectorAll(".avatar-option").forEach((btn) => {
    btn.disabled = !ready || saving;
  });
}

function renderAvatarPicker() {
  document.getElementById("avatar-options").innerHTML = AVATARS.map(
    (url) =>
      `<button type="button" class="avatar-option" data-avatar="${url}">
        <img src="${url}" alt="">
      </button>`
  ).join("");

  document.getElementById("avatar-options").addEventListener("click", (e) => {
    const btn = e.target.closest(".avatar-option");
    if (!btn || !profileLoaded || saving) return;
    setAvatar(btn.dataset.avatar);
  });

  document.getElementById("avatar-custom").addEventListener("click", (e) => {
    if (e.target.closest("#avatar-delete-btn")) {
      deleteCustomAvatar();
      return;
    }

    const btn = e.target.closest(".avatar-option");
    if (!btn || !profileLoaded || saving) return;
    setAvatar(btn.dataset.avatar);
  });
}

async function deleteCustomAvatar() {
  if (!profileLoaded || saving) return;
  if (!confirm("Удалить загруженное фото?")) return;

  const msg = document.getElementById("profile-message");
  const deleteBtn = document.getElementById("avatar-delete-btn");

  try {
    saving = true;
    setFormReady(false);
    if (deleteBtn) deleteBtn.textContent = "Удаление...";

    const profile = await api("/profile/me/avatar", { method: "DELETE" });
    applyProfile(profile);
    setStatus(msg, "Своё фото удалено");
    showToast("Фото удалено");
  } catch (err) {
    setStatus(msg, err.message, false);
  } finally {
    saving = false;
    if (deleteBtn) deleteBtn.textContent = "Удалить фото";
    setFormReady(true);
  }
}

function renderFavorites(rooms) {
  const list = document.getElementById("favorites-list");
  const ids = getFavorites();
  const favRooms = rooms.filter((r) => ids.includes(r.id));

  if (!favRooms.length) {
    list.innerHTML =
      '<li class="empty">Пока пусто — жмите ★ на карточке пространства</li>';
    return;
  }

  list.innerHTML = favRooms
    .map(
      (room) =>
        `<li>
          <a class="tile-row tile-link" href="room.html?id=${room.id}">
            <div class="tile-info">
              <strong>${escapeHtml(room.name)}</strong>
              <span class="tile-meta">Вместимость: ${formatPlaces(room.capacity)}</span>
            </div>
            <span class="fav-arrow">→</span>
          </a>
        </li>`
    )
    .join("");
}

async function loadFavorites() {
  try {
    const rooms = await fetchRooms();
    renderFavorites(rooms);
  } catch {
    document.getElementById("favorites-list").innerHTML =
      '<li class="empty">Не удалось загрузить избранное</li>';
  }
}

function renderBookings(bookings) {
  const list = document.getElementById("bookings-list");
  if (!Array.isArray(bookings) || !bookings.length) {
    list.innerHTML = '<li class="empty">У вас пока нет активных бронирований</li>';
    return;
  }

  list.innerHTML = bookings
    .map(
      (b) =>
        `<li class="booking-card" data-booking-id="${b.id}">
          <div class="tile-row">
            ${renderBookingInfo(b, b.room_name)}
            <button type="button" class="btn btn-soft btn-sm btn-cancel-booking" data-id="${b.id}">
              Отменить
            </button>
          </div>
        </li>`
    )
    .join("");
}

async function loadProfile() {
  const profile = await api("/profile/me");
  usernameDirty = false;
  applyProfile(profile);
  setFormReady(true);
  return profile;
}

usernameInput.addEventListener("input", () => {
  usernameDirty = true;
});

avatarUploadInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || !profileLoaded || saving) return;

  const msg = document.getElementById("profile-message");
  const formData = new FormData();
  formData.append("file", file);

  try {
    saving = true;
    setFormReady(false);
    saveBtn.textContent = "Загрузка...";

    const profile = await api("/profile/me/avatar", {
      method: "POST",
      body: formData,
    });

    applyProfile(profile);
    setStatus(msg, "Своё фото загружено");
    showToast("Аватар обновлён");
  } catch (err) {
    setStatus(msg, err.message, false);
  } finally {
    saving = false;
    saveBtn.textContent = "Сохранить";
    setFormReady(true);
    e.target.value = "";
  }
});

profileForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!profileLoaded || saving) return;

  const msg = document.getElementById("profile-message");
  const username = usernameInput.value.trim();
  const full_name = document.getElementById("profile-full-name").value.trim();
  const phone = document.getElementById("profile-phone").value.trim();
  const email = document.getElementById("profile-email").value.trim();

  if (username.length < 2) {
    setStatus(msg, "Ник должен быть не короче 2 символов", false);
    return;
  }

  try {
    saving = true;
    saveBtn.disabled = true;
    saveBtn.textContent = "Сохранение...";

    const payload = { username, avatar_url: selectedAvatar };
    if (full_name) payload.full_name = full_name;
    if (phone) payload.phone = phone;
    if (email) payload.email = email;

    const profile = await api("/profile/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });

    if (profile.access_token) {
      setToken(profile.access_token);
    }

    usernameDirty = false;
    applyProfile(profile);
    setStatus(msg, "Профиль сохранён");
    showToast("Профиль сохранён");
  } catch (err) {
    setStatus(msg, err.message, false);
  } finally {
    saving = false;
    saveBtn.textContent = "Сохранить";
    setFormReady(true);
  }
});

document.getElementById("bookings-list").addEventListener("click", async (e) => {
  const btn = e.target.closest(".btn-cancel-booking");
  if (!btn) return;

  const msg = document.getElementById("profile-message");
  try {
    btn.disabled = true;
    await api(`/bookings/${btn.dataset.id}`, { method: "DELETE" });
    await loadProfile();
    setStatus(msg, "Бронирование отменено");
    showToast("Бронь отменена");
    initBookingBadge();
  } catch (err) {
    btn.disabled = false;
    setStatus(msg, err.message, false);
  }
});

setFormReady(false);
renderAvatarPicker();
loadFavorites();
loadProfile().catch((err) => {
  profileLoaded = true;
  setFormReady(true);
  renderBookings([]);
  document.getElementById("profile-message").textContent = err.message;
  document.getElementById("profile-message").className = "status error";
});
