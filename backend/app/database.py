from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool
from .config import settings

class Base(DeclarativeBase):
    pass

def create_engine_for_url(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    poolclass = NullPool if not database_url.startswith("sqlite") else None
    kwargs = {"connect_args": connect_args, "pool_pre_ping": True}
    if poolclass is not None:
        kwargs["poolclass"] = poolclass
    return create_engine(database_url, **kwargs)

engine = create_engine_for_url(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def initialize_database() -> None:
    global engine, SessionLocal
    database_url = settings.database_url
    probe_engine = create_engine_for_url(database_url)
    try:
        with probe_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        probe_engine.dispose()
        if database_url.startswith("sqlite"):
            raise
        fallback_url = "sqlite:///./taketwo.db"
        print(f"Database connection failed for {database_url}: {exc}. Falling back to SQLite at {fallback_url}")
        engine = create_engine_for_url(fallback_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    else:
        engine = probe_engine
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    from . import models
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if not inspector.has_table("accounts"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("accounts")}
    with engine.begin() as connection:
        if "photo_url" not in existing_columns:
            connection.execute(text("ALTER TABLE accounts ADD COLUMN photo_url VARCHAR"))
        if "phone" not in existing_columns:
            connection.execute(text("ALTER TABLE accounts ADD COLUMN phone VARCHAR(40) NOT NULL DEFAULT ''"))
        if "role" not in existing_columns:
            connection.execute(text("ALTER TABLE accounts ADD COLUMN role VARCHAR(100) NOT NULL DEFAULT 'Staff'"))
        if "branch" not in existing_columns:
            connection.execute(text("ALTER TABLE accounts ADD COLUMN branch VARCHAR(120) NOT NULL DEFAULT 'Main Branch'"))
        if not str(engine.url).startswith("sqlite"):
            try:
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_email ON accounts (email)"))
            except Exception:
                pass

    # Add missing columns to dropoff_requests table if they don't exist
    if inspector.has_table("dropoff_requests"):
        dropoff_columns = {column["name"] for column in inspector.get_columns("dropoff_requests")}
        with engine.begin() as connection:
            if "price_list" not in dropoff_columns:
                connection.execute(text("ALTER TABLE dropoff_requests ADD COLUMN price_list VARCHAR(255)"))
            if "discounts" not in dropoff_columns:
                connection.execute(text("ALTER TABLE dropoff_requests ADD COLUMN discounts VARCHAR(255)"))
            if "number_of_pairs" not in dropoff_columns:
                connection.execute(text("ALTER TABLE dropoff_requests ADD COLUMN number_of_pairs INTEGER"))
            if "bin" not in dropoff_columns:
                connection.execute(text("ALTER TABLE dropoff_requests ADD COLUMN bin VARCHAR(20)"))
            if "sponsored" not in dropoff_columns:
                connection.execute(text("ALTER TABLE dropoff_requests ADD COLUMN sponsored BOOLEAN NOT NULL DEFAULT FALSE"))

initialize_database()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()