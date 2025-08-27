from __future__ import annotations
from pathlib import Path
import json
from typing import Iterable
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, FAQ

DB_PATH = Path(__file__).resolve().parent / "data.db"
ENGINE = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)

SEED_FILE = Path(__file__).resolve().parent / "seed_data.json"

def init_db() -> None:
    Base.metadata.create_all(ENGINE)

def get_session() -> Iterable[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def seed_if_empty() -> None:
    """Carga seed_data.json si la tabla está vacía."""
    with SessionLocal() as session:
        count = session.execute(select(func.count(FAQ.id))).scalar_one()
        if count and count > 0:
            return
        if not SEED_FILE.exists():
            raise FileNotFoundError(f"No existe {SEED_FILE}")
        data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        rows = []
        for item in data:
            tags = item.get("tags")
            tags_json = json.dumps(tags) if tags is not None else None
            rows.append(FAQ(question=item["question"], answer=item["answer"], tags=tags_json))
        session.add_all(rows)
        session.commit()



# Esto a continuación es para por si algún día quiero pasar de SQLite a Postgres
import os
from sqlalchemy import create_engine
from pathlib import Path

DB_URL = os.getenv("DB_URL")  # ej: postgresql+psycopg://user:pass@host/db

if DB_URL:
    ENGINE = create_engine(DB_URL, pool_pre_ping=True)
else:
    DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parent / "data.db"))
    ENGINE = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})