"""SQLAlchemy models. SQLite by default; PostgreSQL via DATABASE_URL env.
Set e.g. DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/drishti"""
import os, json, datetime
from sqlalchemy import create_engine, String, Integer, Float, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./drishti.db")
engine = create_engine(DATABASE_URL, echo=False, future=True,
                       connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)

class Base(DeclarativeBase): pass

class DataImport(Base):
    __tablename__ = "data_imports"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String)                 # real | demo
    provenance: Mapped[str] = mapped_column(Text)             # JSON
    quality: Mapped[str] = mapped_column(Text)                # JSON
    mapping: Mapped[str] = mapped_column(Text)                # JSON
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class Work(Base):
    __tablename__ = "works"
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[str] = mapped_column(String, index=True)
    work_id: Mapped[str] = mapped_column(String, index=True)
    record: Mapped[str] = mapped_column(Text)                 # full canonical record JSON

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[str] = mapped_column(String, index=True)
    mode: Mapped[str] = mapped_column(String)
    results: Mapped[str] = mapped_column(Text)               # engine output JSON
    model_runs: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(String, index=True)
    import_id: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[str] = mapped_column(String, default="local")
    role: Mapped[str] = mapped_column(String, default="District Authority")
    signals_snapshot: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class AppState(Base):
    __tablename__ = "app_state"
    k: Mapped[str] = mapped_column(String, primary_key=True)
    v: Mapped[str] = mapped_column(String)

def init_db(): Base.metadata.create_all(engine)
def get_state(s, k, default=None):
    row = s.get(AppState, k); return row.v if row else default
def set_state(s, k, v):
    row = s.get(AppState, k)
    if row: row.v = v
    else: s.add(AppState(k=k, v=v))
