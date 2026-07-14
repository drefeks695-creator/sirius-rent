const CAL_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const CAL_MONTHS = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];

function normalizeIsoDate(value) {
  return String(value).slice(0, 10);
}

function formatScheduleTime(value) {
  const raw = String(value);
  const local = raw.includes("T") && !raw.endsWith("Z") && !raw.includes("+")
    ? new Date(raw)
    : new Date(raw);
  return local.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function todayIsoDate() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function formatRuDate(isoDate) {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

function calendarStatusLabel(status) {
  return (
    {
      free: "Свободно",
      partial: "Частично занято",
      busy: "Занято",
      closed: "Прошло",
    }[status] || status
  );
}

function formatBookingsCount(count) {
  const n = Number(count);
  if (!n) return "";
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n} бронь`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${n} брони`;
  return `${n} бронь`;
}

function renderCalendarLegend() {
  return `<div class="cal-legend">
    <span class="cal-legend-item"><i class="cal-status-dot cal-dot-free"></i> Свободно</span>
    <span class="cal-legend-item"><i class="cal-status-dot cal-dot-partial"></i> Частично</span>
    <span class="cal-legend-item"><i class="cal-status-dot cal-dot-busy"></i> Занято</span>
    <span class="cal-legend-item"><i class="cal-status-dot cal-dot-closed"></i> Прошло</span>
  </div>`;
}

function parseTimeToMinutes(value) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function formatHourLabel(totalMinutes) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function getTimelineLabelStep(totalMinutes) {
  const hours = totalMinutes / 60;
  if (hours <= 6) return 60;
  if (hours <= 14) return 120;
  return 180;
}

function renderTimelineBar(slots, openTime, closeTime) {
  if (!slots.length) {
    return `<p class="empty">В этот день пространство не работает</p>`;
  }

  const openMin = parseTimeToMinutes(openTime);
  const closeMin = parseTimeToMinutes(closeTime);
  const totalMin = Math.max(closeMin - openMin, 1);
  const labelStep = getTimelineLabelStep(totalMin);

  const segments = slots
    .map(
      (slot) =>
        `<span class="schedule-seg schedule-seg-${slot.status}" title="${formatScheduleTime(slot.start)} – ${formatScheduleTime(slot.end)}"></span>`
    )
    .join("");

  const gridLines = [];
  const labels = [];

  for (let mark = openMin; mark <= closeMin; mark += 60) {
    const pct = ((mark - openMin) / totalMin) * 100;
    gridLines.push(`<span class="schedule-grid-line" style="left:${pct}%"></span>`);

    const showLabel =
      mark === openMin || mark === closeMin || (mark - openMin) % labelStep === 0;
    if (!showLabel) continue;

    const posClass =
      mark === openMin ? "is-start" : mark === closeMin ? "is-end" : "";
    labels.push(
      `<span class="schedule-axis-label ${posClass}" style="left:${pct}%">${formatHourLabel(mark)}</span>`
    );
  }

  return `<div class="schedule-timeline">
    <div class="schedule-bar-track">
      <div class="schedule-grid" aria-hidden="true">${gridLines.join("")}</div>
      <div class="schedule-bar" role="img" aria-label="Занятость с ${openTime} до ${closeTime}">${segments}</div>
    </div>
    <div class="schedule-axis">${labels.join("")}</div>
  </div>`;
}

function renderBusyBookings(bookings, roomName) {
  if (!bookings.length) {
    return '<p class="schedule-free-note">На этот день бронирований нет — в рабочие часы всё свободно</p>';
  }

  return `<ul class="schedule-bookings tiles compact">${bookings
    .map((booking) => renderBookingCard(booking, roomName))
    .join("")}</ul>`;
}

function renderMonthCalendar(year, month, days, selectedDate) {
  const firstWeekday = (new Date(year, month - 1, 1).getDay() + 6) % 7;
  const today = todayIsoDate();
  const dayMap = Object.fromEntries(
    days.map((day) => [normalizeIsoDate(day.date), day])
  );

  let cells = "";
  for (let i = 0; i < firstWeekday; i += 1) {
    cells += '<span class="cal-cell cal-cell-empty"></span>';
  }

  for (let dayNum = 1; dayNum <= days.length; dayNum += 1) {
    const iso = `${year}-${String(month).padStart(2, "0")}-${String(dayNum).padStart(2, "0")}`;
    const info = dayMap[iso] || { status: "free", bookings_count: 0 };
    const classes = [
      "cal-cell",
      "cal-cell-day",
      `cal-cell-${info.status}`,
      iso === selectedDate ? "cal-cell-selected" : "",
      iso === today ? "cal-cell-today" : "",
    ]
      .filter(Boolean)
      .join(" ");

    const mark = info.bookings_count
      ? `<span class="cal-bookings-badge" title="${formatBookingsCount(info.bookings_count)}">${info.bookings_count}</span>`
      : "";

    cells += `<button type="button" class="${classes}" data-date="${iso}" aria-label="${dayNum} — ${calendarStatusLabel(info.status)}${info.bookings_count ? `, ${formatBookingsCount(info.bookings_count)}` : ""}" title="${calendarStatusLabel(info.status)}${info.bookings_count ? ` · ${formatBookingsCount(info.bookings_count)}` : ""}">
      <span class="cal-day-num">${dayNum}</span>
      <span class="cal-day-footer">
        <i class="cal-status-dot cal-dot-${info.status}" aria-hidden="true"></i>
        ${mark}
      </span>
    </button>`;
  }

  const weekdays = CAL_WEEKDAYS.map((name) => `<span class="cal-weekday">${name}</span>`).join("");

  return `<div class="cal-weekdays" aria-hidden="true">${weekdays}</div><div class="cal-grid" role="grid" aria-label="Календарь месяца">${cells}</div>`;
}
