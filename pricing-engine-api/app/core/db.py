import uuid
from datetime import datetime, date
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Boolean,
    Integer,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,
    BigInteger,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

from app.core.config import DATABASE_URL

# SQLAlchemy 2.0 Engine and SessionLocal
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Commodity(Base):
    __tablename__ = "commodity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)  # 'leafy', 'fruit_veg', 'root', 'grain'
    unit = Column(String(20), nullable=False, default="kg")
    shelf_life_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    mandi_prices = relationship("MandiPrice", back_populates="commodity", cascade="all, delete-orphan")
    demand_signals = relationship("DemandSignal", back_populates="commodity", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Commodity(name='{self.name}', category='{self.category}')>"


class Mandi(Base):
    __tablename__ = "mandi"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True)
    latitude = Column(Numeric(10, 6), nullable=False)
    longitude = Column(Numeric(10, 6), nullable=False)
    agmarknet_code = Column(String(100), unique=True, nullable=True, index=True)

    # Relationships
    mandi_prices = relationship("MandiPrice", back_populates="mandi", cascade="all, delete-orphan")
    weather_observations = relationship("WeatherObservation", back_populates="mandi", cascade="all, delete-orphan")
    demand_signals = relationship("DemandSignal", back_populates="mandi", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Mandi(name='{self.name}', state='{self.state}', code='{self.agmarknet_code}')>"


class MandiPrice(Base):
    __tablename__ = "mandi_price"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mandi_id = Column(UUID(as_uuid=True), ForeignKey("mandi.id", ondelete="CASCADE"), nullable=False)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey("commodity.id", ondelete="CASCADE"), nullable=False)
    price_date = Column(Date, nullable=False, index=True)
    min_price = Column(Numeric(10, 2), nullable=True)  # ₹/kg (converted from AGMARKNET ₹/quintal at ingestion)
    max_price = Column(Numeric(10, 2), nullable=True)  # ₹/kg (converted from AGMARKNET ₹/quintal at ingestion)
    modal_price = Column(Numeric(10, 2), nullable=False)  # ₹/kg (converted from AGMARKNET ₹/quintal at ingestion)
    arrival_qty = Column(Numeric(12, 2), nullable=True)  # quintals (optional)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_flagged_outlier = Column(Boolean, nullable=False, default=False)
    is_derived_modal = Column(Boolean, nullable=False, default=False)
    source = Column(String(50), nullable=False, default="live")  # 'live', 'demo_fixture'

    # Relationships
    mandi = relationship("Mandi", back_populates="mandi_prices")
    commodity = relationship("Commodity", back_populates="mandi_prices")

    __table_args__ = (
        UniqueConstraint("mandi_id", "commodity_id", "price_date", name="uq_mandi_commodity_date"),
        Index("idx_mandi_commodity_date", "commodity_id", "mandi_id", "price_date"),
    )

    def __repr__(self):
        return f"<MandiPrice(mandi_id='{self.mandi_id}', commodity_id='{self.commodity_id}', date='{self.price_date}', modal='{self.modal_price}')>"


class WeatherObservation(Base):
    __tablename__ = "weather_observation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mandi_id = Column(UUID(as_uuid=True), ForeignKey("mandi.id", ondelete="CASCADE"), nullable=False)
    obs_date = Column(Date, nullable=False, index=True)
    rainfall_mm = Column(Numeric(10, 2), nullable=True, default=0.0)
    temp_max_c = Column(Numeric(5, 2), nullable=True)
    source = Column(String(50), nullable=False, default="demo_fixture")

    # Relationships
    mandi = relationship("Mandi", back_populates="weather_observations")

    __table_args__ = (
        UniqueConstraint("mandi_id", "obs_date", name="uq_mandi_obs_date"),
    )

    def __repr__(self):
        return f"<WeatherObservation(mandi_id='{self.mandi_id}', date='{self.obs_date}', rain='{self.rainfall_mm}mm')>"


class DemandSignal(Base):
    __tablename__ = "demand_signal"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey("commodity.id", ondelete="CASCADE"), nullable=False)
    region_id = Column(UUID(as_uuid=True), ForeignKey("mandi.id", ondelete="CASCADE"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    order_count = Column(Integer, nullable=False, default=0)
    requested_qty_kg = Column(Numeric(12, 2), nullable=False, default=0.0)
    unique_buyers = Column(Integer, nullable=False, default=0)

    # Relationships
    commodity = relationship("Commodity", back_populates="demand_signals")
    mandi = relationship("Mandi", back_populates="demand_signals")

    def __repr__(self):
        return f"<DemandSignal(commodity_id='{self.commodity_id}', region_id='{self.region_id}', orders={self.order_count})>"


class PredictionLog(Base):
    __tablename__ = "prediction_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_json = Column(JSON, nullable=False)
    response_json = Column(JSON, nullable=False)
    model_version_id = Column(UUID(as_uuid=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<PredictionLog(id='{self.id}', latency_ms={self.latency_ms})>"


def get_db_session() -> Session:
    """Create and return a new database session."""
    return SessionLocal()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for transactional DB session handling."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
