initSiteNav();

let currentAdminId = null;

function roleLabel(role) {
  return role === "admin" ? "Администратор" : "Пользователь";
}

function avatarOptions(selected) {
  return [1, 2, 3, 4, 5, 6]
    .map((n) => {
      const url = `/ui/avatars/${n}.svg`;
      const active = selected === url ? " selected" : "";
      return `<option value="${url}"${active}>Аватар ${n}</option>`;
    })
    .join("");
}

function renderUserEditForm(user) {
  return `<form class="admin-user-form stack" data-user-id="${user.id}">
    <label>
      <span>Ник</span>
      <input type="text" name="username" required minlength="2" maxlength="100" value="${escapeHtml(user.username)}">
    </label>
    <label>
      <span>Роль</span>
      <select name="role">
        <option value="user"${user.role === "user" ? " selected" : ""}>Пользователь</option>
        <option value="admin"${user.role === "admin" ? " selected" : ""}>Администратор</option>
      </select>
    </label>
    <label>
      <span>ФИО</span>
      <input type="text" name="full_name" maxlength="200" value="${escapeHtml(user.full_name || "")}" placeholder="Фамилия Имя">
    </label>
    <label>
      <span>Телефон</span>
      <input type="tel" name="phone" maxlength="30" value="${escapeHtml(user.phone || "")}" placeholder="+7 (999) 123-45-67">
    </label>
    <label>
      <span>Почта</span>
      <input type="email" name="email" maxlength="200" value="${escapeHtml(user.email || "")}" placeholder="mail@example.com">
    </label>
    <label>
      <span>Аватар</span>
      <select name="avatar_url">${avatarOptions(user.avatar_url)}</select>
    </label>
    <label>
      <span>Новый пароль</span>
      <input type="password" name="password" minlength="8" maxlength="100" placeholder="Оставьте пустым, если не менять">
    </label>
    <div class="admin-item-actions">
      <button type="submit" class="btn btn-main btn-sm">Сохранить</button>
      <button type="button" class="btn btn-soft btn-sm admin-cancel-edit">Отмена</button>
    </div>
    <p class="admin-user-msg status" aria-live="polite"></p>
  </form>`;
}

function renderAdminUser(user) {
  const isSelf = user.id === currentAdminId;
  return `<li class="admin-item admin-user-item" data-user-id="${user.id}">
    <div class="admin-item-main">
      <div class="admin-user-head">
        <img class="admin-user-avatar" src="${escapeHtml(user.avatar_url || "/ui/avatars/1.svg")}" alt="">
        <div>
          <strong>${escapeHtml(user.username)}${isSelf ? " (вы)" : ""}</strong>
          <span class="tile-meta">${roleLabel(user.role)}</span>
        </div>
      </div>
      <span class="tile-meta">${escapeHtml(user.full_name || "ФИО не указано")} · ${escapeHtml(user.phone || "телефон не указан")} · ${escapeHtml(user.email || "почта не указана")}</span>
    </div>
    <div class="admin-item-actions">
      <button type="button" class="btn btn-soft btn-sm admin-edit-user">Изменить</button>
      <button type="button" class="btn btn-soft btn-sm admin-delete-user"${isSelf ? " disabled title=\"Нельзя удалить свой аккаунт\"" : ""}>Удалить</button>
    </div>
    <div class="admin-user-edit hidden"></div>
  </li>`;
}

function parseEquipment(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

const roomImageInput = document.getElementById("room-image");
const roomImageName = document.getElementById("room-image-name");
const roomImagePreview = document.getElementById("room-image-preview");
const roomImagePreviewImg = document.getElementById("room-image-preview-img");
let roomImagePreviewUrl = null;

function setRoomImageName(file) {
  if (!file) {
    roomImageName.textContent = "Файл не выбран";
    roomImageName.classList.remove("is-selected");
    return;
  }
  roomImageName.textContent = file.name;
  roomImageName.classList.add("is-selected");
}

function clearRoomImagePreview() {
  if (roomImagePreviewUrl) {
    URL.revokeObjectURL(roomImagePreviewUrl);
    roomImagePreviewUrl = null;
  }
  roomImageInput.value = "";
  setRoomImageName(null);
  roomImagePreviewImg.removeAttribute("src");
  roomImagePreview.classList.add("hidden");
  roomImagePreview.setAttribute("aria-hidden", "true");
}

roomImageInput.addEventListener("change", () => {
  if (roomImagePreviewUrl) {
    URL.revokeObjectURL(roomImagePreviewUrl);
    roomImagePreviewUrl = null;
  }

  const file = roomImageInput.files?.[0];
  if (!file) {
    setRoomImageName(null);
    roomImagePreviewImg.removeAttribute("src");
    roomImagePreview.classList.add("hidden");
    roomImagePreview.setAttribute("aria-hidden", "true");
    return;
  }

  setRoomImageName(file);
  roomImagePreviewUrl = URL.createObjectURL(file);
  roomImagePreviewImg.src = roomImagePreviewUrl;
  roomImagePreview.classList.remove("hidden");
  roomImagePreview.setAttribute("aria-hidden", "false");
});

document.getElementById("room-image-clear").addEventListener("click", clearRoomImagePreview);

async function uploadRoomImage(roomId, file) {
  const formData = new FormData();
  formData.append("file", file);
  return api(`/rooms/${roomId}/image`, {
    method: "POST",
    body: formData,
  });
}

function renderAdminRoom(room) {
  const blocked = room.bookings_blocked;
  return `<li class="admin-item" data-room-id="${room.id}">
    <div class="admin-item-main">
      <strong>${escapeHtml(room.name)}</strong>
      <span class="tile-meta">Вместимость: ${formatPlaces(room.capacity)} · ${escapeHtml(room.equipment.join(", ") || "без оборудования")}</span>
      ${blocked ? '<span class="admin-badge admin-badge-blocked">Бронирование закрыто</span>' : ""}
    </div>
    <div class="admin-item-actions">
      <button type="button" class="btn btn-soft btn-sm admin-toggle-block" data-blocked="${blocked ? "1" : "0"}">
        ${blocked ? "Открыть бронь" : "Закрыть бронь"}
      </button>
      <a href="room.html?id=${room.id}" class="btn btn-soft btn-sm">Открыть</a>
      <button type="button" class="btn btn-soft btn-sm admin-delete-room">Удалить</button>
    </div>
  </li>`;
}

function bookingStatusLabel(status) {
  if (status === "active") return "Активно";
  if (status === "completed") return "Завершено";
  if (status === "cancelled") return "Отменено";
  return status;
}

function renderReportBookingRow(booking) {
  return `<tr>
    <td>${escapeHtml(booking.code || "—")}</td>
    <td>${escapeHtml(booking.user_name)}</td>
    <td>${formatBookingLine("", booking.start_time, booking.end_time).replace(/^ · /, "")}</td>
    <td><span class="admin-report-status admin-report-status-${booking.status}">${bookingStatusLabel(booking.status)}</span></td>
  </tr>`;
}

function renderReportBookingsTable(items, emptyText) {
  if (!items.length) {
    return `<p class="admin-report-empty">${emptyText}</p>`;
  }
  return `<div class="admin-report-table-wrap">
    <table class="admin-report-table">
      <thead>
        <tr>
          <th>Код</th>
          <th>Пользователь</th>
          <th>Время</th>
          <th>Статус</th>
        </tr>
      </thead>
      <tbody>${items.map(renderReportBookingRow).join("")}</tbody>
    </table>
  </div>`;
}

function renderAdminReportRoom(room) {
  const bookedCount = room.booked.length;
  return `<article class="admin-report-room" data-room-id="${room.room_id}">
    <div class="admin-report-room-head">
      <div>
        <h3>${escapeHtml(room.room_name)}</h3>
        <p class="tile-meta">Вместимость: ${formatPlaces(room.capacity)}</p>
      </div>
      <div class="admin-report-stats">
        <span class="admin-report-stat">Забронировано: <strong>${bookedCount}</strong></span>
        <span class="admin-report-stat">Отменено: <strong>${room.cancelled_count}</strong></span>
        <span class="admin-report-stat">Активно: <strong>${room.active_count}</strong></span>
        <span class="admin-report-stat">Завершено: <strong>${room.completed_count}</strong></span>
      </div>
    </div>
    <div class="admin-report-columns">
      <div class="admin-report-column">
        <h4>Бронирования</h4>
        ${renderReportBookingsTable(room.booked, "Бронирований пока нет")}
      </div>
      <div class="admin-report-column">
        <h4>Отмены</h4>
        ${renderReportBookingsTable(room.cancelled, "Отмен не было")}
      </div>
    </div>
  </article>`;
}

async function loadAdminReport() {
  const roomsEl = document.getElementById("admin-report-rooms");
  const generatedEl = document.getElementById("admin-report-generated");

  try {
    const report = await api("/admin/reports/rooms");
    const generated = new Date(report.generated_at);
    generatedEl.textContent = `Обновлено ${generated.toLocaleString("ru-RU")}`;

    if (!report.rooms.length) {
      roomsEl.innerHTML = '<p class="empty">Пространств для отчёта пока нет</p>';
      return;
    }

    roomsEl.innerHTML = report.rooms.map(renderAdminReportRoom).join("");
  } catch (err) {
    roomsEl.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function renderAdminBooking(booking) {
  return `<li class="admin-item" data-booking-id="${booking.id}">
    <div class="admin-item-main">
      <strong>${escapeHtml(booking.room_name)}</strong>
      <span class="tile-meta">${formatBookingLine(booking.code, booking.start_time, booking.end_time)}</span>
      <span class="tile-meta">Пользователь: ${escapeHtml(booking.user_name)}</span>
    </div>
    <div class="admin-item-actions">
      <button type="button" class="btn btn-soft btn-sm admin-cancel-booking">Отменить</button>
    </div>
  </li>`;
}

async function ensureAdmin() {
  requireAuth();
  const profile = await fetchProfile();
  if (profile?.role !== "admin") {
    window.location.href = "index.html";
    return false;
  }
  currentAdminId = profile.id;
  return true;
}

let adminUsersCache = [];

async function loadAdminRooms() {
  const list = document.getElementById("admin-rooms-list");
  const countEl = document.getElementById("admin-rooms-count");

  try {
    const rooms = await fetchRooms();
    countEl.textContent = rooms.length ? `${rooms.length} шт.` : "";
    if (!rooms.length) {
      list.innerHTML = '<li class="empty">Пространств пока нет</li>';
      return;
    }
    list.innerHTML = rooms.map(renderAdminRoom).join("");
  } catch (err) {
    list.innerHTML = `<li class="error">${escapeHtml(err.message)}</li>`;
  }
}

async function loadAdminUsers() {
  const list = document.getElementById("admin-users-list");
  const countEl = document.getElementById("admin-users-count");

  try {
    adminUsersCache = await api("/admin/users");
    countEl.textContent = adminUsersCache.length ? `${adminUsersCache.length} шт.` : "";
    if (!adminUsersCache.length) {
      list.innerHTML = '<li class="empty">Пользователей нет</li>';
      return;
    }
    list.innerHTML = adminUsersCache.map(renderAdminUser).join("");
  } catch (err) {
    list.innerHTML = `<li class="error">${escapeHtml(err.message)}</li>`;
  }
}

async function loadAdminBookings() {
  const list = document.getElementById("admin-bookings-list");
  const countEl = document.getElementById("admin-bookings-count");

  try {
    const bookings = await api("/admin/bookings");
    countEl.textContent = bookings.length ? `${bookings.length} шт.` : "";
    if (!bookings.length) {
      list.innerHTML = '<li class="empty">Активных бронирований нет</li>';
      return;
    }
    list.innerHTML = bookings.map(renderAdminBooking).join("");
  } catch (err) {
    list.innerHTML = `<li class="error">${escapeHtml(err.message)}</li>`;
  }
}

async function reloadAdmin() {
  await Promise.all([loadAdminReport(), loadAdminRooms(), loadAdminUsers(), loadAdminBookings()]);
}

document.getElementById("admin-room-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("admin-room-msg");

  try {
    const payload = {
      name: document.getElementById("room-name").value.trim(),
      capacity: Number(document.getElementById("room-capacity").value),
      description: document.getElementById("room-description").value.trim(),
      equipment: parseEquipment(document.getElementById("room-equipment").value),
    };
    const room = await api("/rooms", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    const imageFile = roomImageInput.files?.[0];
    if (imageFile) {
      await uploadRoomImage(room.id, imageFile);
    }

    e.target.reset();
    clearRoomImagePreview();
    setStatus(msg, "Пространство добавлено", true);
    showToast("Пространство добавлено");
    await loadAdminRooms();
  } catch (err) {
    setStatus(msg, err.message, false);
  }
});

document.getElementById("admin-rooms-list").addEventListener("click", async (e) => {
  const item = e.target.closest(".admin-item");
  if (!item) return;
  const roomId = Number(item.dataset.roomId);

  if (e.target.closest(".admin-toggle-block")) {
    const btn = e.target.closest(".admin-toggle-block");
    const blocked = btn.dataset.blocked === "1";
    try {
      await api(`/rooms/${roomId}`, {
        method: "PUT",
        body: JSON.stringify({ bookings_blocked: !blocked }),
      });
      showToast(blocked ? "Бронирование открыто" : "Бронирование закрыто");
      await loadAdminRooms();
    } catch (err) {
      showToast(err.message);
    }
    return;
  }

  if (e.target.closest(".admin-delete-room")) {
    if (!window.confirm("Удалить пространство и все связанные брони?")) return;
    try {
      await api(`/rooms/${roomId}`, { method: "DELETE" });
      showToast("Пространство удалено");
      await reloadAdmin();
    } catch (err) {
      showToast(err.message);
    }
  }
});

document.getElementById("admin-users-list").addEventListener("click", async (e) => {
  const item = e.target.closest(".admin-user-item");
  if (!item) return;
  const userId = Number(item.dataset.userId);
  const user = adminUsersCache.find((entry) => entry.id === userId);
  if (!user) return;

  if (e.target.closest(".admin-edit-user")) {
    const editBox = item.querySelector(".admin-user-edit");
    editBox.classList.remove("hidden");
    editBox.innerHTML = renderUserEditForm(user);
    return;
  }

  if (e.target.closest(".admin-cancel-edit")) {
    const editBox = item.querySelector(".admin-user-edit");
    editBox.classList.add("hidden");
    editBox.innerHTML = "";
    return;
  }

  if (e.target.closest(".admin-delete-user")) {
    if (userId === currentAdminId) return;
    if (!window.confirm(`Удалить аккаунт «${user.username}» и все его брони?`)) return;
    try {
      await api(`/admin/users/${userId}`, { method: "DELETE" });
      showToast("Пользователь удалён");
      await Promise.all([loadAdminUsers(), loadAdminBookings()]);
    } catch (err) {
      showToast(err.message);
    }
  }
});

document.getElementById("admin-users-list").addEventListener("submit", async (e) => {
  const form = e.target.closest(".admin-user-form");
  if (!form) return;
  e.preventDefault();

  const userId = Number(form.dataset.userId);
  const msg = form.querySelector(".admin-user-msg");
  const payload = {
    username: form.username.value.trim(),
    role: form.role.value,
    full_name: form.full_name.value.trim(),
    phone: form.phone.value.trim(),
    email: form.email.value.trim(),
    avatar_url: form.avatar_url.value,
  };
  if (form.password.value) {
    payload.password = form.password.value;
  }

  try {
    await api(`/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    showToast("Данные пользователя сохранены");
    await loadAdminUsers();
  } catch (err) {
    setStatus(msg, err.message, false);
  }
});

document.getElementById("admin-bookings-list").addEventListener("click", async (e) => {
  const item = e.target.closest(".admin-item");
  if (!item || !e.target.closest(".admin-cancel-booking")) return;

  const bookingId = Number(item.dataset.bookingId);
  if (!window.confirm("Отменить это бронирование?")) return;

  try {
    await api(`/bookings/${bookingId}`, { method: "DELETE" });
    showToast("Бронирование отменено");
    await Promise.all([loadAdminBookings(), loadAdminReport()]);
  } catch (err) {
    showToast(err.message);
  }
});

(async () => {
  if (!(await ensureAdmin())) return;
  await reloadAdmin();
})();
