requireAuth();
initSiteNav();

initBookingDateTime("booking-start");
initDurationChips("booking-start");

const roomsById = {};

async function loadRoomOptions() {
  const select = document.getElementById("booking-room");
  try {
    const rooms = await fetchRooms();
    if (!rooms.length) {
      select.innerHTML = '<option value="">Нет доступных комнат</option>';
      select.disabled = true;
      return;
    }
    select.disabled = false;
    select.innerHTML = rooms
      .map((room) => {
        roomsById[room.id] = room;
        return `<option value="${room.id}">${escapeHtml(room.name)}</option>`;
      })
      .join("");
    updateBookingRoomHours();
  } catch {
    select.innerHTML = '<option value="">Ошибка загрузки</option>';
    select.disabled = true;
  }
}

function updateBookingRoomHours() {
  const room = roomsById[Number(document.getElementById("booking-room").value)];
  if (!room) return;
  applyRoomHoursToPicker("booking-start", room.open_time, room.close_time);
}

document.getElementById("booking-room")?.addEventListener("change", updateBookingRoomHours);

async function showConflictSuggestions(start_time, end_time) {
  const roomId = Number(document.getElementById("booking-room").value);
  await showBookingSuggestions("booking-suggestions", roomId, start_time, end_time, {
    onTimeSlot: (slot) => {
      applyTimeSuggestion("booking-start", slot);
      hideSuggestions("booking-suggestions");
      showToast("Выбран свободный интервал");
    },
    onRoom: (room) => {
      document.getElementById("booking-room").value = String(room.id);
      updateBookingRoomHours();
      hideSuggestions("booking-suggestions");
      showToast(`Можно забронировать: ${room.name}`);
    },
  });
}

document.getElementById("booking-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("booking-message");
  hideSuggestions("booking-suggestions");

  try {
    await ensureBookingProfile();
    const { start_time, end_time } = getBookingRange("booking-start");
    const room = roomsById[Number(document.getElementById("booking-room").value)];
    if (!room) {
      throw new Error("Выберите пространство");
    }
    assertBookingWithinRoomHours(room.open_time, room.close_time, start_time, end_time);

    const booking = await api("/bookings", {
      method: "POST",
      body: JSON.stringify({
        room_id: Number(document.getElementById("booking-room").value),
        start_time,
        end_time,
        ...getBookingContactPayload(),
      }),
    });
    cachedProfile = await fetchProfile(true);
    setStatus(msg, `Готово — комната забронирована · ${booking.code}`);
    showToast(`Бронирование создано! ${booking.code}`);
    spawnConfetti();
    initBookingBadge();
  } catch (err) {
    setStatus(msg, err.message, false);
    if (isBookingConflictError(err.message)) {
      const { start_time, end_time } = getBookingRange("booking-start");
      await showConflictSuggestions(start_time, end_time);
    }
  }
});

loadRoomOptions();
fetchProfile().then(showBookingContactPanel);
