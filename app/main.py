from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.auth import create_user, get_user_by_username
from app.avatars import ensure_uploads_dir
from app.room_images import ensure_room_uploads_dir
from app.booking_codes import backfill_booking_codes
from app.booking_utils import expire_finished_bookings
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_migrate import apply_pending_migrations
from app.dependencies import equipment_to_str
from app.schedule import DEFAULT_HOURS, ROOM_HOURS
from app.models import Room, UserRole
from app.routers import admin, auth, bookings, profile, rooms
from app.schemas import HealthResponse

SAMPLE_ROOMS = [
    {
        "name": "Переговорная А-101",
        "capacity": 32,
        "description": (
            "Переговорная А-101 — конференц-зал на 32 места в корпусе «Альфа» НТУ «Сириус» на Олимпийском проспекте, 4.1. "
            "Просторное помещение с П-образной рассадкой, панорамным остеклением и брендированием «Университет Сириус». "
            "Оборудование: ТВ-панели для видеоконференций, микрофоны, маркерные доски и система видеосвязи. "
            "Подходит для рабочих встреч, защит проектов, презентаций и гибридных созвонов с партнёрами. "
            "Доступна беспроводная сеть Wi-Fi, розетки у каждого места."
        ),
        "image_url": "/ui/images/room-1.png",
        "equipment": ["проектор", "доска", "конференц-связь", "Wi-Fi"],
    },
    {
        "name": "Аудитория Б-205",
        "capacity": 30,
        "description": (
            "Аудитория Б-205 — лекционный зал на 30 мест с амфитеатричной рассадкой в образовательном комплексе «Сириус». "
            "Площадь зала около 58 м², естественное освещение через панорамные окна с видом на кампус. "
            "Оборудование: проектор Full HD, акустическая система Behringer, радиомикрофон Arthur Forty и веб-камера 4K. "
            "Используется для лекций, семинаров, мастер-классов, открытых презентаций и научных докладов. "
            "Помещение адаптировано для маломобильных групп населения."
        ),
        "image_url": "/ui/images/room-2.png",
        "equipment": ["проектор", "микрофон", "колонки"],
    },
    {
        "name": "Коворкинг С-12",
        "capacity": 9,
        "description": (
            "Коворкинг С-12 — открытое пространство общественно-досугового центра Президентского лицея «Сириус». "
            "Зал на 9 рабочих мест с мягкой мебелью, высокими столами и зонами для групповых обсуждений. "
            "Здесь проходят хакатоны, проектные сессии, подготовка к олимпиадам и неформальные встречи студентов. "
            "Доступны маркерная стена для схем, быстрый Wi-Fi и розетки у каждого места. "
            "Пространство входит в новый образовательный комплекс, спроектированный бюро ATRIUM."
        ),
        "image_url": "/ui/images/room-3.png",
        "equipment": ["доска", "Wi-Fi", "розетки"],
    },
    {
        "name": "Актовый зал «Центральный»",
        "capacity": 200,
        "description": (
            "Актовый зал «Центральный» — крупнейший конференц-зал образовательного комплекса «Сириус» на 200 мест. "
            "Отдельный вход с бульвара, сцена, профессиональный свет, звуковое оборудование и проекционный комплекс. "
            "Зал спроектирован бюро ATRIUM для научных конференций, торжественных мероприятий и открытых лекций. "
            "Используется на Конгрессе молодых учёных, днях открытых дверей и выпускных церемониях. "
            "Бронирование — минимум за 3 дня, требуется согласование с администрацией кампуса."
        ),
        "image_url": "/ui/images/room-8.png",
        "equipment": ["проектор", "микрофон", "свет", "сцена"],
    },
    {
        "name": "Учебный класс К-18",
        "capacity": 24,
        "description": (
            "Учебный класс К-18 — трансформируемая аудитория на 24 места с мобильными перегородками. "
            "Пространство можно перестроить под урок, семинар, мини-лекцию или групповую проектную работу. "
            "Оборудование: проектор, интерактивная доска, акустическая система и столы-трансформеры Summa GA. "
            "Класс входит в новый образовательный комплекс на Нагорном тупике, спроектированный бюро ATRIUM. "
            "Ориентация здания оптимизирована под естественную инсоляцию южного побережья."
        ),
        "image_url": "/ui/images/room-9.png",
        "equipment": ["проектор", "доска", "колонки"],
    },
]


def seed_data(db: Session) -> None:
    if not get_user_by_username(db, "admin"):
        create_user(db, "admin", "admin123", UserRole.admin)
    if not get_user_by_username(db, "student"):
        create_user(db, "student", "student123", UserRole.user)

    if db.query(Room).count() > 0:
        return

    for item in SAMPLE_ROOMS:
        hours = ROOM_HOURS.get(item["name"], DEFAULT_HOURS)
        db.add(
            Room(
                name=item["name"],
                capacity=item["capacity"],
                description=item["description"],
                equipment=equipment_to_str(item["equipment"]),
                image_url=item["image_url"],
                open_time=hours["open"],
                close_time=hours["close"],
            )
        )
    db.commit()


def backfill_room_hours(db: Session) -> None:
    changed = False
    for room in db.query(Room).all():
        hours = ROOM_HOURS.get(room.name)
        if not hours:
            continue
        if room.open_time == "08:00" and room.close_time == "22:00":
            room.open_time = hours["open"]
            room.close_time = hours["close"]
            changed = True
    if changed:
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_pending_migrations(engine)
    ensure_uploads_dir()
    ensure_room_uploads_dir()
    db = SessionLocal()
    try:
        seed_data(db)
        backfill_room_hours(db)
        expire_finished_bookings(db)
        backfill_booking_codes(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    description="REST API для бронирования переговорных и учебных пространств Университета «Сириус»",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(profile.router)
app.include_router(admin.router)


@app.get("/api/health", response_model=HealthResponse, tags=["Система"])
def health():
    return HealthResponse(status="ok", service=settings.app_name)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/")


static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="static")
