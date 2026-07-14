initSiteNav();

let allRooms = [];
let favoritesOnly = false;
let selectedEquipment = "";

function roomImage(room) {
  const src = `${room.image_url || `/ui/images/room-${room.id}.webp`}?v=22`;
  return `<img class="room-card-img" src="${src}" alt="${escapeHtml(room.name)}" loading="lazy">`;
}

function favoriteButton(roomId) {
  const active = isFavorite(roomId) ? " is-active" : "";
  return `<button type="button" class="room-fav${active}" data-fav-id="${roomId}" aria-label="В избранное">★</button>`;
}

function matchesFilters(room) {
  const search = document.getElementById("filter-search").value.trim().toLowerCase();
  const capacityMin = Number(document.getElementById("filter-capacity").value);
  const capacityMax = Number(document.getElementById("filter-capacity-max").value);
  const equipment = selectedEquipment.toLowerCase();

  if (favoritesOnly && !isFavorite(room.id)) return false;
  if (capacityMin && capacityMax && capacityMin > capacityMax) return false;
  if (capacityMin && room.capacity < capacityMin) return false;
  if (capacityMax && room.capacity > capacityMax) return false;

  if (equipment) {
    const hasEquipment = room.equipment.some((item) => item.toLowerCase().includes(equipment));
    if (!hasEquipment) return false;
  }

  if (search) {
    const haystack = `${room.name} ${room.equipment.join(" ")}`.toLowerCase();
    if (!haystack.includes(search)) return false;
  }

  return true;
}

function renderRooms(rooms) {
  const list = document.getElementById("rooms-list");

  if (!rooms.length) {
    list.innerHTML = '<li class="empty">Ничего не нашли — попробуйте другой фильтр</li>';
    return;
  }

  list.innerHTML = rooms
    .map(
      (room, i) =>
        `<li style="animation-delay:${i * 0.05}s">
          <a class="room-card" href="room.html?id=${room.id}">
            <div class="room-card-media">
              ${roomImage(room)}
              ${favoriteButton(room.id)}
            </div>
            <div class="room-card-body">
              <strong>${escapeHtml(room.name)}</strong>
              ${room.bookings_blocked ? '<span class="room-blocked-badge">Бронь закрыта</span>' : ""}
              <span class="tile-meta">Вместимость: ${formatPlaces(room.capacity)}</span>
              <div class="tile-tags">${renderTags(room.equipment)}</div>
            </div>
          </a>
        </li>`
    )
    .join("");
}

function applyFilters() {
  renderRooms(allRooms.filter(matchesFilters));
}

async function loadRooms() {
  const list = document.getElementById("rooms-list");
  list.innerHTML = '<li class="empty">Загружаем пространства...</li>';

  try {
    allRooms = await fetchRooms();
    applyFilters();
  } catch (err) {
    list.innerHTML = `<li class="error">${escapeHtml(err.message)}</li>`;
  }
}

async function loadGreeting() {
  const greetingEl = document.getElementById("rooms-greeting");
  const tipEl = document.getElementById("rooms-tip");
  tipEl.textContent = randomTip();

  try {
    const profile = await api("/profile/me");
    greetingEl.textContent = `${getTimeGreeting()}, ${profile.username}!`;
  } catch {
    greetingEl.textContent = isAuthed()
      ? `${getTimeGreeting()}!`
      : `${getTimeGreeting()}! Смотрите пространства без входа`;
  }
}

document.getElementById("rooms-list").addEventListener("click", (e) => {
  const btn = e.target.closest(".room-fav");
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();
  const active = toggleFavorite(btn.dataset.favId);
  btn.classList.toggle("is-active", active);
  showToast(active ? "Добавлено в избранное" : "Убрано из избранного");
  if (favoritesOnly) applyFilters();
});

document.getElementById("filter-search").addEventListener("input", debounce(applyFilters));
document.getElementById("filter-capacity").addEventListener("input", debounce(applyFilters));
document.getElementById("filter-capacity-max").addEventListener("input", debounce(applyFilters));

document.querySelectorAll(".filter-chip[data-equipment]").forEach((chip) => {
  chip.addEventListener("click", () => {
    const value = chip.dataset.equipment;
    selectedEquipment = selectedEquipment === value ? "" : value;
    document.querySelectorAll(".filter-chip[data-equipment]").forEach((c) => {
      c.classList.toggle("active", c.dataset.equipment === selectedEquipment);
    });
    applyFilters();
  });
});

document.getElementById("favorites-only-btn").addEventListener("click", () => {
  favoritesOnly = !favoritesOnly;
  document.getElementById("favorites-only-btn").classList.toggle("active", favoritesOnly);
  applyFilters();
});

loadGreeting();
loadRooms();
