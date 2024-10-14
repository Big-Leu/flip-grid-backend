from sqlalchemy import Column, Integer, String, Date
from backend.db.base import Base
from sqlalchemy.dialects.postgresql import UUID

class Product(Base):
    __tablename__ = 'products'
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)
    manufacturing_date = Column(String, nullable=True)
    mrp = Column(String, nullable=True)
    description = Column(String, nullable=True)

