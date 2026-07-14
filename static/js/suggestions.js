async function fetchBookingSuggestions(roomId, start, end) {
  const params = new URLSearchParams({ start, end });
  return api(`/rooms/${roomId}/suggestions?${params}`);
}

function hideSuggestions(containerId) {
  const box = document.getElementById(containerId);
  if (!box) return;
  box.classList.add("hidden");
  box.innerHTML = "";
}

function formatFreeInterval(start, end) {
  const startDate = parseLocalDateTime(start);
  const endDate = parseLocalDateTime(end);
  const startTime = startDate.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const endTime = endDate.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `с ${startTime} до ${endTime}`;
}

function renderSuggestions(containerId, data, handlers = {}) {
  const box = document.getElementById(containerId);
  if (!box) return;

  const timeSlots = data.time_slots || [];
  const rooms = data.rooms || [];

  if (!timeSlots.length && !rooms.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }

  const timeButtons = timeSlots
    .map(
      (slot, index) =>
        `<button type="button" class="chip suggestion-chip suggestion-time" data-index="${index}">
          ${formatFreeInterval(slot.start, slot.end)}
        </button>`
    )
    .join("");

  const selectedRange = data.start && data.end ? formatBookingRange(data.start, data.end) : "";
  const roomButtons = rooms
    .map(
      (room) =>
        `<button type="button" class="chip suggestion-chip suggestion-room" data-room-id="${room.id}">
          ${escapeHtml(room.name)}
        </button>`
    )
    .join("");

  box.innerHTML = `<div class="suggestions-box">
    ${
      timeSlots.length
        ? `<div class="suggestions-group">
            <p class="suggestions-title">Свободное время:</p>
            <div class="suggestion-chips">${timeButtons}</div>
          </div>`
        : ""
    }
    ${
      rooms.length
        ? `<div class="suggestions-group">
            <p class="suggestions-title">Свободные аудитории${selectedRange ? ` · ${escapeHtml(selectedRange)}` : ""}:</p>
            <div class="suggestion-chips">${roomButtons}</div>
          </div>`
        : ""
    }
  </div>`;

  box.classList.remove("hidden");
  box._suggestionData = data;

  box.querySelectorAll(".suggestion-time").forEach((btn) => {
    btn.addEventListener("click", () => {
      const slot = timeSlots[Number(btn.dataset.index)];
      handlers.onTimeSlot?.(slot);
    });
  });

  box.querySelectorAll(".suggestion-room").forEach((btn) => {
    btn.addEventListener("click", () => {
      const room = rooms.find((item) => item.id === Number(btn.dataset.roomId));
      handlers.onRoom?.(room);
    });
  });
}

async function showBookingSuggestions(containerId, roomId, start, end, handlers = {}) {
  try {
    const data = await fetchBookingSuggestions(roomId, start, end);
    renderSuggestions(containerId, data, handlers);
  } catch {
    hideSuggestions(containerId);
  }
}

function isBookingConflictError(message) {
  return /занят/i.test(message || "");
}
