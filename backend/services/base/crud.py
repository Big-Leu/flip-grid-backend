import datetime
import uuid
from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.bases import AbstractParams
from backend.commons.responses import ServiceResponse, ServiceResponseStatus
from backend.db.models.product import Product
from backend.db.models.users import User
from backend.logging import get_logger
from backend.schemas.form import FormInputSchema, bookingform
from backend.schemas.product import ProductSchema
from backend.services.commons.base import BaseService
from sqlalchemy import func

logger = get_logger(__name__)


class FormService(BaseService):
    __item_name__ = "FormService"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def createProductListing(self, Product1: ProductSchema) -> ServiceResponse:
        try:
            data = Product1.model_dump()
            data["uuid"] = uuid.uuid4()
            plan = Product(**data)
            self.session.add(plan)  # No await needed
            await self.session.commit()
            return self.response(ServiceResponseStatus.CREATED, result=ProductSchema.from_sqlalchemy(plan))
        except SQLAlchemyError as e:
            logger.error(f"An error occurred: {e}")
            await self.session.rollback()
            return self.response(ServiceResponseStatus.ERROR, message=str(e)) 

 