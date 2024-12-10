from typing import Optional
from pydantic import BaseModel
from datetime import date
from backend.db.models.product import Product


class ProductSchema(BaseModel):
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
