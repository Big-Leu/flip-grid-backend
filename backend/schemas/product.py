from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from backend.db.models.product import Product


class FreshProduceSchema(BaseModel):
    uuid: Optional[UUID] = None
    sl_no: Optional[int] = None
    timestamp: Optional[datetime] = None
    produce: Optional[str] = None
    freshness: Optional[int] = None
    expected_life_span: Optional[int] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(cls, model) -> "FreshProduceSchema":
        return cls.model_validate(model)


class PackagedProductSchema(BaseModel):
    uuid: Optional[UUID] = None
    mrp: Optional[str] = None
    timestamp: Optional[datetime] = None
    brand: Optional[str] = None
    expiry_date: Optional[str] = None
    count: Optional[int] = None
    expired: Optional[bool] = None
    expected_life_span: Optional[int] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(cls, model) -> "PackagedProductSchema":
        return cls.model_validate(model)


class ProductSchema(BaseModel):
    name: Optional[str] = None
    expiry_date: Optional[str] = None
    # manufacturing_date: Optional[str] = None
    mrp: Optional[str] = None
    description: Optional[str] = None
    freshStatus: Optional[str] = None
    confidence: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(cls, model: Product) -> "ProductSchema":
        return cls.model_validate(model)


class ProductSchema2(BaseModel):
    name: Optional[str] = None
    expiry_date: Optional[str] = None
    manufacturing_date: Optional[str] = None
    mrp: Optional[str] = None
    description: Optional[str] = None
    freshStatus: Optional[str] = None
    confidence: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(cls, model: Product) -> "ProductSchema":
        return cls.model_validate(model)
