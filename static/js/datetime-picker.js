const DATETIME_OPTIONS = {
  enableTime: true,
  time_24hr: true,
  minuteIncrement: 15,
  dateFormat: "d.m.Y H:i",
  altInput: true,
  altFormat: "j F Y, H:i",
  locale: "ru",
  minDate: "today",
  disableMobile: true,
};

const DURATION_STEP = 30;
const DURATION_MIN = 30;
const DURATION_DEFAULT_MAX = 8 * 60;
const WHEEL_THRESHOLD = 40;

const durationByStartId = new Map();
const roomHoursByStartId = new Map();
const wheelAccumByStartId = new Map();

function formatLocalISO(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}

function parseLocalDateTime(value) {
  const raw = String(value);
  if (raw.includes("T") && !raw.endsWith("Z") && !raw.includes("+")) {
    return new Date(raw);
  }
  return new Date(raw);
}

function formatDurationLabel(minutes) {
  if (minutes < 60) return `${minutes} мин`;

  const wholeHours = Math.floor(minutes / 60);
  const remainder = minutes % 60;

  const hourWord = (n) => {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return "час";
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "часа";
    return "часов";
  };

  if (remainder === 0) {
    return `${wholeHours} ${hourWord(wholeHours)}`;
  }
  if (remainder === 30) {
    if (wholeHours === 0) return "30 мин";
    if (wholeHours === 1) return "1,5 часа";
    return `${wholeHours},5 часа`;
  }
  return `${minutes} мин`;
}

function getDurationRoot(startId) {
  const input = document.getElementById(startId);
  return (
    input?.closest("form")?.querySelector(".time-quick") ||
    input?.closest(".stack")?.querySelector(".time-quick")
  );
}

function updateDurationLabel(startId, minutes) {
  const label = getDurationRoot(startId)?.querySelector("[data-duration-label]");
  if (label) {
    label.textContent = `Выбрано: ${formatDurationLabel(minutes)}`;
  }
}

function getMaxDurationMinutes(startId) {
  const hours = roomHoursByStartId.get(startId);
  if (!hours) return DURATION_DEFAULT_MAX;

  const [openH, openM] = hours.openTime.split(":").map(Number);
  const [closeH, closeM] = hours.closeTime.split(":").map(Number);
  const openMinutes = openH * 60 + openM;
  const closeMinutes = closeH * 60 + closeM;
  return Math.max(DURATION_MIN, closeMinutes - openMinutes);
}

function adjustStartForDuration(startId, minutes) {
  const hours = roomHoursByStartId.get(startId);
  const el = document.getElementById(startId);
  const fp = el?._flatpickr;
  if (!hours || !fp?.selectedDates?.[0]) return minutes;

  const [openH, openM] = hours.openTime.split(":").map(Number);
  const [closeH, closeM] = hours.closeTime.split(":").map(Number);
  const openMinutes = openH * 60 + openM;
  const closeMinutes = closeH * 60 + closeM;

  const start = new Date(fp.selectedDates[0]);
  const startMinutes = start.getHours() * 60 + start.getMinutes();
  const endMinutes = startMinutes + minutes;

  if (endMinutes <= closeMinutes) return minutes;

  let newStartMinutes = closeMinutes - minutes;
  if (newStartMinutes < openMinutes) {
    newStartMinutes = openMinutes;
    minutes = closeMinutes - openMinutes;
  }

  start.setHours(Math.floor(newStartMinutes / 60), newStartMinutes % 60, 0, 0);
  fp.setDate(start, true);
  return minutes;
}

function getDurationMinutes(startId) {
  return durationByStartId.get(startId) ?? 60;
}

function adjustDurationMinutes(startId, delta) {
  if (!delta) return;
  setDurationMinutes(startId, getDurationMinutes(startId) + delta);
}

function updateDurationUI(startId) {
  updateDurationLabel(startId, getDurationMinutes(startId));
}

function setDurationMinutes(startId, minutes) {
  const max = getMaxDurationMinutes(startId);
  let clamped = Math.min(max, Math.max(DURATION_MIN, minutes));
  clamped = adjustStartForDuration(startId, clamped);
  durationByStartId.set(startId, clamped);
  updateDurationUI(startId);
}

function initBookingDateTime(startId) {
  const startEl = document.getElementById(startId);
  if (!startEl || typeof flatpickr === "undefined") return null;

  const startPicker = flatpickr(startEl, {
    ...DATETIME_OPTIONS,
    onChange: () => {
      setDurationMinutes(startId, getDurationMinutes(startId));
    },
  });

  const now = new Date();
  now.setMinutes(Math.ceil(now.getMinutes() / 15) * 15, 0, 0);
  startPicker.setDate(now, false);

  return startPicker;
}

function getDateTimeISO(inputId) {
  const el = document.getElementById(inputId);
  const date = el?._flatpickr?.selectedDates?.[0];
  if (!date) {
    throw new Error("Выберите дату и время");
  }
  return formatLocalISO(date);
}

function getSelectedDurationMinutes(startId) {
  return getDurationMinutes(startId);
}

function getBookingRange(startId) {
  const el = document.getElementById(startId);
  const startDate = el?._flatpickr?.selectedDates?.[0];
  if (!startDate) {
    throw new Error("Выберите дату и время");
  }

  const start_time = formatLocalISO(startDate);
  const endDate = new Date(startDate.getTime() + getSelectedDurationMinutes(startId) * 60 * 1000);
  const end_time = formatLocalISO(endDate);

  return { start_time, end_time };
}

function assertBookingWithinRoomHours(openTime, closeTime, startIso, endIso) {
  const startDate = parseLocalDateTime(startIso);
  const endDate = parseLocalDateTime(endIso);
  const [openH, openM] = openTime.split(":").map(Number);
  const [closeH, closeM] = closeTime.split(":").map(Number);
  const open = new Date(startDate);
  open.setHours(openH, openM, 0, 0);
  const close = new Date(startDate);
  close.setHours(closeH, closeM, 0, 0);

  const sameDay =
    startDate.getFullYear() === endDate.getFullYear() &&
    startDate.getMonth() === endDate.getMonth() &&
    startDate.getDate() === endDate.getDate();

  if (!sameDay || startDate < open || endDate > close) {
    throw new Error(`Бронирование доступно с ${openTime} до ${closeTime}`);
  }
}

function applyRoomHoursToPicker(startId, openTime, closeTime) {
  const el = document.getElementById(startId);
  const fp = el?._flatpickr;
  if (!fp) return;

  roomHoursByStartId.set(startId, { openTime, closeTime });
  fp.set("minTime", openTime);
  fp.set("maxTime", closeTime);
  ensureBookingWithinRoomHours(startId, openTime, closeTime);
  setDurationMinutes(startId, getDurationMinutes(startId));
}

function ensureBookingWithinRoomHours(startId, openTime, closeTime) {
  const el = document.getElementById(startId);
  const fp = el?._flatpickr;
  if (!fp?.selectedDates?.[0]) return;

  const [openH, openM] = openTime.split(":").map(Number);
  const [closeH, closeM] = closeTime.split(":").map(Number);
  const openMinutes = openH * 60 + openM;
  const closeMinutes = closeH * 60 + closeM;

  const date = new Date(fp.selectedDates[0]);
  const minutes = date.getHours() * 60 + date.getMinutes();

  if (minutes >= closeMinutes) {
    date.setDate(date.getDate() + 1);
    date.setHours(openH, openM, 0, 0);
    fp.setDate(date, false);
    return;
  }

  if (minutes < openMinutes) {
    date.setHours(openH, openM, 0, 0);
    fp.setDate(date, false);
  }
}

function handleDurationWheel(startId, event) {
  event.preventDefault();
  event.stopPropagation();

  let accum = (wheelAccumByStartId.get(startId) || 0) + event.deltaY;
  while (Math.abs(accum) >= WHEEL_THRESHOLD) {
    const step = accum < 0 ? DURATION_STEP : -DURATION_STEP;
    accum += accum < 0 ? WHEEL_THRESHOLD : -WHEEL_THRESHOLD;
    adjustDurationMinutes(startId, step);
  }
  wheelAccumByStartId.set(startId, accum);
}

function initDurationChips(startId) {
  const rootEl = getDurationRoot(startId);
  if (!rootEl) return;

  durationByStartId.set(startId, 60);
  wheelAccumByStartId.set(startId, 0);
  updateDurationUI(startId);

  rootEl.addEventListener("click", (event) => {
    const stepBtn = event.target.closest("[data-step]");
    if (!stepBtn) return;
    event.preventDefault();
    adjustDurationMinutes(startId, Number(stepBtn.dataset.step));
  });

  rootEl.addEventListener("wheel", (event) => handleDurationWheel(startId, event), {
    passive: false,
    capture: true,
  });

  if (!rootEl.dataset.wheelHint) {
    rootEl.dataset.wheelHint = "1";
    rootEl.title = "Прокрутите колёсико мыши, чтобы увеличить или уменьшить длительность";
  }
}

function setBookingDateTime(startId, isoStart) {
  const el = document.getElementById(startId);
  const date = parseLocalDateTime(isoStart);
  if (!el?._flatpickr || !date) return;
  el._flatpickr.setDate(date, true);
}

function applyTimeSuggestion(startId, slot) {
  setBookingDateTime(startId, slot.start);
  const minutes = Math.round(
    (parseLocalDateTime(slot.end) - parseLocalDateTime(slot.start)) / 60000
  );
  setDurationMinutes(startId, minutes);
}
