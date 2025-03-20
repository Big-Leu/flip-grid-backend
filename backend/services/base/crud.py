import datetime
import uuid
from fastapi import Depends
from sqlalchemy import literal, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.bases import AbstractParams
from backend.commons.responses import ServiceResponse, ServiceResponseStatus
from backend.db.models.product import FreshProduce, PackagedProduct, Product
from backend.db.models.users import User
from backend.logging import get_logger
from backend.schemas.form import FormInputSchema, bookingform
from backend.schemas.product import (
    FreshProduceSchema,
    PackagedProductSchema,
    ProductSchema,
)
from backend.services.commons.base import BaseService
from sqlalchemy import func

logger = get_logger(__name__)

counter1 = 0
counter2 = 0


class FormService(BaseService):
    __item_name__ = "FormService"

    def get_product_type(self, item):
        brand = getattr(item, "brand", None)
        if brand:
            return "PACKAGED PRODUCT"
        else:
            return "FRUITS AND VEGETABLES"

    def get_mrp(self, item):
        mrp = getattr(item, "mrp", None)
        if mrp:
            return mrp
        else:
            return "VARIES"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def createProductListing(
        self, Product1: PackagedProductSchema
    ) -> ServiceResponse:
        try:
            data = Product1.model_dump()
            result = await self.session.execute(select(func.max(PackagedProduct.sl_no)))
            counter1 = result.scalar()
            data["sl_no"] = counter1 + 1
            plan = PackagedProduct(**data)
            self.session.add(plan)  # No await needed
            await self.session.commit()
            return self.response(
                ServiceResponseStatus.CREATED,
                result=ProductSchema.from_sqlalchemy(plan),
            )
        except SQLAlchemyError as e:
            logger.error(f"An error occurred: {e}")
            await self.session.rollback()
            return self.response(ServiceResponseStatus.ERROR, message=str(e))

    async def createProductListingFresh(
        self, Product1: FreshProduceSchema
    ) -> ServiceResponse:
        try:
            Product1.produce = (
                Product1.produce.replace("fresh", "")
                .replace("partiallyfresh", "")
                .replace("rotten", "")
            )
            Product1.uuid = uuid.uuid4()
            result = await self.session.execute(select(func.max(FreshProduce.sl_no)))
            counter2 = result.scalar()
            if counter2 is None:
                counter2 = 0
            Product1.sl_no = counter2 + 1
            data = Product1.model_dump()
            plan = FreshProduce(**data)
            self.session.add(plan)
            await self.session.commit()
            return self.response(
                ServiceResponseStatus.CREATED,
                result=ProductSchema.from_sqlalchemy(plan),
            )
        except SQLAlchemyError as e:
            logger.error(f"An error occurred: {e}")
            await self.session.rollback()
            return self.response(ServiceResponseStatus.ERROR, message=str(e))

    async def list_items(self, params: AbstractParams):
        try:
            # Select the necessary columns, ensuring both queries return the same number of columns
            packaged_product_query = select(
                PackagedProduct.uuid,
                PackagedProduct.brand,
                PackagedProduct.expiry_date,
                PackagedProduct.mrp,
                PackagedProduct.timestamp,
                literal(None).label(
                    "expected_life_span"
                ),  # Placeholder for FreshProduce field
                literal(None).label("produce"),  # Placeholder for FreshProduce field
            ).order_by(PackagedProduct.timestamp)

            fresh_produce_query = select(
                FreshProduce.uuid,
                literal(None).label("brand"),  # Placeholder for PackagedProduct field
                literal(None).label(
                    "expiry_date"
                ),  # Placeholder for PackagedProduct field
                literal(None).label("mrp"),  # Placeholder for PackagedProduct field
                FreshProduce.timestamp,
                FreshProduce.expected_life_span,
                FreshProduce.produce,
            ).order_by(FreshProduce.timestamp)

            # Combine queries with UNION ALL
            stmt = packaged_product_query.union_all(fresh_produce_query)

            # Paginate the results
            paginated_result = await paginate(self.session, stmt, params, unique=True)

            # Metadata for response
            metadata = {
                "total": paginated_result.total,
                "page": paginated_result.page,
                "size": paginated_result.size,
                "pages": paginated_result.pages,
            }

            # Format the results
            return self.response(
                ServiceResponseStatus.FETCHED,
                result=[
                    ProductSchema(
                        name=getattr(item, "brand", None)
                        or getattr(item, "produce", None),
                        expiry_date=getattr(item, "expiry_date", None)
                        or str(getattr(item, "expected_life_span", None)),
                        mrp=self.get_mrp(item),
                        description=self.get_product_type(item),
                    )
                    for item in paginated_result.items
                ],
                metadata=metadata,
            )
        except SQLAlchemyError as e:
            logger.error(f"An error occurred: {e}")
            await self.session.rollback()
            return self.response(ServiceResponseStatus.ERROR)
