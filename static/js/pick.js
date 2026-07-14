initSiteNav();

const COLLECTIONS = {
  popular: {
    title: "Самые популярные",
    subtitle: "Чаще всего бронируют",
    badge: "Популярное",
    hint: "Для первой брони",
    names: [
      "Переговорная А-101",
      "Аудитория Б-205",
      "Коворкинг С-12",
      "Учебный класс К-18",
      "Актовый зал «Центральный»",
    ],
  },
  meeting: {
    title: "Для встреч и созвонов",
    subtitle: "Переговорные с проектором, Wi-Fi и видеосвязью",
    badge: "Для встреч",
    hint: "Встречи и созвоны",
    names: ["Переговорная А-101", "Коворкинг С-12", "Учебный класс К-18"],
  },
  study: {
    title: "Для учёбы и семинаров",
    subtitle: "Аудитории и классы с доской, проектором и хорошей акустикой",
    badge: "Для учёбы",
    hint: "Лекции и семинары",
    names: ["Аудитория Б-205", "Учебный класс К-18", "Коворкинг С-12"],
  },
  event: {
    title: "Для больших мероприятий",
    subtitle: "Просторные залы со сценой, светом и профессиональным звуком",
    badge: "Для событий",
    hint: "Конференции и мероприятия",
    names: ["Актовый зал «Центральный»", "Аудитория Б-205", "Переговорная А-101"],
  },
};

const POPULARITY = {
  "Переговорная А-101": 100,
  "Аудитория Б-205": 96,
  "Коворкинг С-12": 92,
  "Учебный класс К-18": 90,
  "Актовый зал «Центральный»": 88,
};

let allRooms = [];
let activeCollection = "popular";

function roomImage(room) {
  const src = `${room.image_url || `/ui/images/room-${room.id}.webp`}?v=22`;
  return `<img class="room-card-img" src="${src}" alt="${escapeHtml(room.name)}" loading="lazy">`;
}

function favoriteButton(roomId) {
  const active = isFavorite(roomId) ? " is-active" : "";
  return `<button type="button" class="room-fav${active}" data-fav-id="${roomId}" aria-label="В избранное">★</button>`;
}

function pickRoomsForCollection(key) {
  const collection = COLLECTIONS[key];
  const byName = new Map(allRooms.map((room) => [room.name, room]));

  const ordered = collection.names
    .map((name) => byName.get(name))
    .filter((room) => room && !room.bookings_blocked);

  const extras = allRooms
    .filter((room) => !room.bookings_blocked && !ordered.some((item) => item.id === room.id))
    .sort((a, b) => (POPULARITY[b.name] || 0) - (POPULARITY[a.name] || 0));

  return [...ordered, ...extras].slice(0, 5);
}

function renderPickRow(room, collection, index) {
  const blocked = room.bookings_blocked
    ? '<span class="room-blocked-badge">Бронь закрыта</span>'
    : "";

  return `<li style="animation-delay:${index * 0.05}s">
    <a class="pick-row-card" href="room.html?id=${room.id}">
      <div class="pick-row-media">
        ${roomImage(room)}
        ${favoriteButton(room.id)}
        <span class="pick-row-badge">${escapeHtml(collection.badge)}</span>
      </div>
      <div class="pick-row-body">
        <p class="pick-row-kicker">${escapeHtml(collection.hint)}</p>
        <h3>${escapeHtml(room.name)}</h3>
        <p class="pick-row-desc">${escapeHtml(room.description || "Современное пространство кампуса «Сириус» для учёбы, встреч и проектов.")}</p>
        <div class="pick-row-meta">
          <span>${formatPlaces(room.capacity)}</span>
          <span>${room.open_time} – ${room.close_time}</span>
        </div>
        ${blocked}
        <div class="tile-tags">${renderTags(room.equipment)}</div>
        <span class="pick-row-cta">Подробнее →</span>
      </div>
    </a>
  </li>`;
}

function renderCollection(key) {
  const collection = COLLECTIONS[key];
  const rooms = pickRoomsForCollection(key);
  const listEl = document.getElementById("pick-results");

  document.getElementById("pick-collection-title").textContent = collection.title;
  document.getElementById("pick-collection-subtitle").textContent = collection.subtitle;

  if (!rooms.length) {
    listEl.innerHTML = '<li class="empty">Сейчас нет доступных пространств в этой подборке</li>';
    return;
  }

  listEl.innerHTML = rooms.map((room, index) => renderPickRow(room, collection, index)).join("");
}

function setActiveCollection(key) {
  activeCollection = key;
  document.querySelectorAll(".pick-tab").forEach((tab) => {
    const active = tab.dataset.collection === key;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", active ? "true" : "false");
  });
  renderCollection(key);
}

async function loadRooms() {
  try {
    allRooms = await fetchRooms();
    renderCollection(activeCollection);
  } catch (err) {
    document.getElementById("pick-results").innerHTML = `<li class="error">${escapeHtml(err.message)}</li>`;
  }
}

document.querySelectorAll(".pick-tab").forEach((tab) => {
  tab.addEventListener("click", () => setActiveCollection(tab.dataset.collection));
});

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".room-fav");
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();
  const active = toggleFavorite(btn.dataset.favId);
  btn.classList.toggle("is-active", active);
  showToast(active ? "Добавлено в избранное" : "Убрано из избранного");
});

loadRooms();
