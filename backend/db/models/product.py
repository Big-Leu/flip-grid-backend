import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Date
from backend.db.base import Base
from sqlalchemy.dialects.postgresql import UUID


class Product(Base):
    __tablename__ = "products"

    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)
    manufacturing_date = Column(String, nullable=True)
    mrp = Column(String, nullable=True)
    description = Column(String, nullable=True)
    freshStatus = Column(String, nullable=True)
    confidence = Column(String, nullable=True)


class PackagedProduct(Base):
    __tablename__ = "packaged_product"
    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    sl_no = Column(Integer, nullable=False, autoincrement=True)
    mrp = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    brand = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)
    count = Column(Integer, nullable=True)
    expired = Column(Boolean, nullable=True)
    expected_life_span = Column(Integer, nullable=True)


class FreshProduce(Base):
    __tablename__ = "fresh_produce"
    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    sl_no = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.now())
    produce = Column(String, nullable=True)
    freshness = Column(Integer, nullable=True)
    expected_life_span = Column(Integer, nullable=True)
