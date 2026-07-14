initSiteNav();

const roomId = Number(new URLSearchParams(window.location.search).get("id"));
let lastCheck = { start: null, end: null };
let calendarYear = new Date().getFullYear();
let calendarMonth = new Date().getMonth() + 1;
let selectedCalendarDate = todayIsoDate();

if (!roomId) {
  window.location.href = "index.html";
}

initBookingDateTime("room-start");
initDurationChips("room-start");

function updateBookButton(available) {
  const bookBtn = document.getElementById("book-room-btn");
  bookBtn.classList.toggle("hidden", !available);
  if (!available) return;
  bookBtn.textContent = isAuthed() ? "Забронировать" : "Войти и забронировать";
}

let currentRoom = null;

function renderRoom(room) {
  currentRoom = room;
  document.title = `Сириус.Аренда — ${room.name}`;
  const src = `${room.image_url || `/ui/images/room-${room.id}.webp`}?v=22`;
  document.getElementById("room-detail").innerHTML = `
    <img class="room-detail-img" src="${src}" alt="${escapeHtml(room.name)}">
    <div class="room-detail-body">
      <div class="room-detail-head">
        <h1>${escapeHtml(room.name)}</h1>
        <button type="button" class="room-fav room-fav-lg${isFavorite(room.id) ? " is-active" : ""}" data-fav-id="${room.id}" aria-label="В избранное">★</button>
      </div>
      <div class="room-detail-desc-row">
        <p class="room-detail-desc">${escapeHtml(room.description || "Описание не указано")}</p>
      </div>
      <p class="tile-meta">Вместимость: ${formatPlaces(room.capacity)} · работает ${escapeHtml(room.open_time)} – ${escapeHtml(room.close_time)}</p>
      ${room.bookings_blocked ? '<p class="room-blocked-label">Бронирование закрыто администратором</p>' : ""}
      <div class="tile-tags">${renderTags(room.equipment)}</div>
    </div>
  `;

  document.querySelector(".room-fav")?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    const active = toggleFavorite(btn.dataset.favId);
    btn.classList.toggle("is-active", active);
    showToast(active ? "В избранном" : "Убрано из избранного");
  });

  applyRoomHoursToPicker("room-start", room.open_time, room.close_time);
  applyPresetBookingTime();
  applyRoomBookingState(room);
}

function applyPresetBookingTime() {
  const query = new URLSearchParams(window.location.search);
  const start = query.get("start");
  const end = query.get("end");
  if (!start || !end || !currentRoom) return;

  applyTimeSuggestion("room-start", { start, end });
  lastCheck = { start, end };
  api(`/rooms/${roomId}/availability?${new URLSearchParams({ start, end })}`)
    .then((result) => showAvailability(result.available, start, end))
    .catch(() => {});
}

function applyRoomBookingState(room) {
  const form = document.getElementById("room-check-form");
  const notice = document.getElementById("room-blocked-notice");
  const blocked = Boolean(room?.bookings_blocked);

  form?.classList.toggle("hidden", blocked);
  notice?.classList.toggle("hidden", !blocked);

  if (blocked) {
    document.getElementById("availability-result")?.classList.add("hidden");
    document.getElementById("book-room-btn")?.classList.add("hidden");
    hideSuggestions("room-suggestions");
  }
}

function showAvailability(available, start, end) {
  const box = document.getElementById("availability-result");
  if (currentRoom?.bookings_blocked) {
    box.classList.remove("hidden", "is-free");
    box.classList.add("is-busy");
    box.textContent = "Бронирование этого пространства временно закрыто";
    updateBookButton(false);
    hideSuggestions("room-suggestions");
    return;
  }

  box.classList.remove("hidden", "is-free", "is-busy");
  box.classList.add(available ? "is-free" : "is-busy");
  box.textContent = available
    ? "Свободна на выбранное время — можно бронировать"
    : "Занято на выбранное время — ниже свободные интервалы";
  updateBookButton(available);

  if (!available && start && end) {
    showBookingSuggestions("room-suggestions", roomId, start, end, {
      onTimeSlot: (slot) => {
        applyTimeSuggestion("room-start", slot);
        lastCheck = { start: slot.start, end: slot.end };
        showAvailability(true, slot.start, slot.end);
        showToast("Выбран свободный интервал");
      },
      onRoom: (room) => {
        const params = new URLSearchParams({
          id: String(room.id),
          start,
          end,
        });
        window.location.href = `room.html?${params}`;
      },
    });
  } else {
    hideSuggestions("room-suggestions");
  }
}

async function loadDayDetail(isoDate) {
  selectedCalendarDate = isoDate;
  document.getElementById("room-day-title").textContent = formatRuDate(isoDate);
  document.querySelector(".cal-day-hint")?.classList.add("hidden");

  const timeline = document.getElementById("room-day-timeline");
  const bookingsEl = document.getElementById("room-day-bookings");

  timeline.innerHTML = '<p class="empty">Загрузка...</p>';
  bookingsEl.innerHTML = "";

  try {
    const schedule = await api(`/rooms/${roomId}/schedule?date=${isoDate}`);
    timeline.innerHTML = renderTimelineBar(
      schedule.slots,
      schedule.open_time,
      schedule.close_time
    );
    bookingsEl.innerHTML = renderBusyBookings(schedule.bookings, schedule.room_name);
  } catch (err) {
    timeline.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function focusCalendarOnDate(isoDate) {
  selectedCalendarDate = isoDate;
  const parts = isoDate.split("-").map(Number);
  calendarYear = parts[0];
  calendarMonth = parts[1];
}

async function loadMonthCalendar() {
  const grid = document.getElementById("room-calendar-grid");
  grid.innerHTML = '<p class="empty">Загружаем календарь...</p>';

  try {
    const monthData = await api(
      `/rooms/${roomId}/schedule/month?year=${calendarYear}&month=${calendarMonth}`
    );
    document.getElementById("room-hours").textContent =
      `Часы работы: ${monthData.open_time} – ${monthData.close_time}`;
    document.getElementById("cal-month-label").textContent =
      `${CAL_MONTHS[calendarMonth - 1]} ${calendarYear}`;
    document.getElementById("room-calendar-legend").innerHTML = renderCalendarLegend();
    grid.innerHTML = renderMonthCalendar(
      calendarYear,
      calendarMonth,
      monthData.days,
      selectedCalendarDate
    );

    if (!monthData.days.some((day) => normalizeIsoDate(day.date) === selectedCalendarDate)) {
      const today = todayIsoDate();
      selectedCalendarDate = monthData.days.some((day) => normalizeIsoDate(day.date) === today)
        ? today
        : normalizeIsoDate(monthData.days[0].date);
    }
    await loadDayDetail(selectedCalendarDate);
  } catch (err) {
    grid.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function shiftCalendarMonth(delta) {
  calendarMonth += delta;
  if (calendarMonth > 12) {
    calendarMonth = 1;
    calendarYear += 1;
  } else if (calendarMonth < 1) {
    calendarMonth = 12;
    calendarYear -= 1;
  }
  loadMonthCalendar();
}

async function loadRoom() {
  try {
    const room = await api(`/rooms/${roomId}`);
    renderRoom(room);
  } catch (err) {
    document.getElementById("room-detail").innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

async function loadCurrentUser() {
  try {
    const profile = await fetchProfile();
    showBookingContactPanel(profile);
    return profile;
  } catch {
    return null;
  }
}

document.getElementById("room-check-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("room-message");
  msg.textContent = "";

  try {
    const { start_time: start, end_time: end } = getBookingRange("room-start");
    if (!currentRoom) {
      throw new Error("Дождитесь загрузки пространства");
    }
    assertBookingWithinRoomHours(currentRoom.open_time, currentRoom.close_time, start, end);

    lastCheck = { start, end };
    const result = await api(
      `/rooms/${roomId}/availability?${new URLSearchParams({ start, end })}`
    );
    showAvailability(result.available, start, end);
  } catch (err) {
    document.getElementById("availability-result").classList.add("hidden");
    document.getElementById("book-room-btn").classList.add("hidden");
    hideSuggestions("room-suggestions");
    setStatus(msg, err.message, false);
  }
});

document.getElementById("book-room-btn").addEventListener("click", async () => {
  const msg = document.getElementById("room-message");
  const btn = document.getElementById("book-room-btn");

  if (!lastCheck.start || !lastCheck.end) return;

  if (!isAuthed()) {
    redirectToLogin();
    return;
  }

  try {
    await ensureBookingProfile();
  } catch (err) {
    setStatus(msg, err.message, false);
    return;
  }

  try {
    assertBookingWithinRoomHours(
      currentRoom.open_time,
      currentRoom.close_time,
      lastCheck.start,
      lastCheck.end
    );
  } catch (err) {
    setStatus(msg, err.message, false);
    return;
  }

  try {
    btn.disabled = true;
    btn.textContent = "Бронируем…";

    const booking = await api("/bookings", {
      method: "POST",
      body: JSON.stringify({
        room_id: roomId,
        start_time: lastCheck.start,
        end_time: lastCheck.end,
        ...getBookingContactPayload(),
      }),
    });
    cachedProfile = await fetchProfile(true);

    setStatus(msg, `Комната успешно забронирована · ${booking.code}`);
    showToast(`Забронировано! ${booking.code}`);
    spawnConfetti();
    initBookingBadge();
    focusCalendarOnDate(lastCheck.start.slice(0, 10));
    await loadMonthCalendar();
    hideSuggestions("room-suggestions");
    document.getElementById("availability-result").classList.remove("hidden", "is-free");
    document.getElementById("availability-result").textContent =
      `Забронировано · ${booking.code} · ${formatBookingRange(lastCheck.start, lastCheck.end)}`;
    document.getElementById("availability-result").classList.add("is-busy");
    btn.classList.add("hidden");
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "Забронировать";
    setStatus(msg, err.message, false);
    if (isBookingConflictError(err.message) && lastCheck.start && lastCheck.end) {
      showBookingSuggestions("room-suggestions", roomId, lastCheck.start, lastCheck.end, {
        onTimeSlot: (slot) => {
          applyTimeSuggestion("room-start", slot);
          lastCheck = { start: slot.start, end: slot.end };
          showAvailability(true, slot.start, slot.end);
          showToast("Выбран свободный интервал");
        },
        onRoom: (room) => {
          const params = new URLSearchParams({
            id: String(room.id),
            start: lastCheck.start,
            end: lastCheck.end,
          });
          window.location.href = `room.html?${params}`;
        },
      });
    }
  }
});

loadRoom();
loadMonthCalendar();
loadCurrentUser();

document.getElementById("cal-prev").addEventListener("click", () => shiftCalendarMonth(-1));
document.getElementById("cal-next").addEventListener("click", () => shiftCalendarMonth(1));

document.getElementById("room-calendar-grid").addEventListener("click", (e) => {
  const cell = e.target.closest(".cal-cell-day");
  if (!cell) return;
  document.querySelectorAll(".cal-cell-day").forEach((btn) => {
    btn.classList.toggle("cal-cell-selected", btn.dataset.date === cell.dataset.date);
  });
  loadDayDetail(cell.dataset.date);
});
