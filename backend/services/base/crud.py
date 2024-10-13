import datetime
import uuid
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.bases import AbstractParams
from backend.commons.responses import ServiceResponse, ServiceResponseStatus
from backend.db.models.tripcard import PlansModel, SlotsModel
from backend.db.models.users import User
from backend.logging import get_logger
from backend.schemas.form import FormInputSchema, bookingform
from backend.schemas.plans import PlansModelInputSchema, PlansModelSchema
from backend.services.commons.base import BaseService
from sqlalchemy import func

logger = get_logger(__name__)


class FormService(BaseService):
    __item_name__ = "FormService"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, processinput: FormInputSchema
    ) -> ServiceResponse:
        try:
                    # Create a SELECT statement to fetch the oauth_account by email.
                    stmt = select(User).where(User.email == processinput.userEmail)
                    result = await self.session.execute(stmt)
                    account = result.scalars().first()
                    name=processinput.userEmail+processinput.lastName
                    if account is None:
                        return self.response(ServiceResponseStatus.NOTFOUND)

                    stmt_update = (
                        update(User)
                        .where(User.email == processinput.userEmail)
                        .values(userName=name,mobileNumber=processinput.mobile)
                    )
                    await self.session.execute(stmt_update)
                    await self.session.commit()
                    return self.response(ServiceResponseStatus.CREATED)

        except SQLAlchemyError as e:
                    logger.error(f"An error occurred: {e}")
                    await self.session.rollback()
                    return self.response(ServiceResponseStatus.ERROR)

    async def createbooking(
        self, processinput: bookingform
    ) -> ServiceResponse:
        try:
                    # Create a SELECT statement to fetch the oauth_account by email.
                    stmt = select(User).where(User.email == processinput.email)
                    result = await self.session.execute(stmt)
                    account = result.scalars().first()
                     
                    if account is None:
                        return self.response(ServiceResponseStatus.NOTFOUND)

                    stmt_update = (
                        update(User)
                        .where(User.email == processinput.email)
                        .values(userName=(processinput.userName),userAadhar=processinput.userAadhar,userDrivingLicense=processinput.userDrivingLicense)
                    )
                    await self.session.execute(stmt_update)
                    await self.session.commit()
                    return self.response(ServiceResponseStatus.CREATED,
                                         result=[bookingform.from_sqlalchemy(account)])
        except SQLAlchemyError as e:
                    logger.error(f"An error occurred: {e}")
                    await self.session.rollback()
                    return self.response(ServiceResponseStatus.ERROR)

    async def getslots(
        self, date: datetime.datetime
    ) -> ServiceResponse:
        try:
                    stmt = select(SlotsModel).where(func.date(SlotsModel.time) == date)
                    result = await self.session.execute(stmt)
                    account = result.scalars().first()

                    if account is None:
                        return self.response(ServiceResponseStatus.NOTFOUND)

                    return self.response(ServiceResponseStatus.FETCHED,
                                         result=account.slots)

        except SQLAlchemyError as e:
                    logger.error(f"An error occurred: {e}")
                    await self.session.rollback()
                    return self.response(ServiceResponseStatus.ERROR)

    async def fillslots(
        self, date: datetime.datetime ,slots: list[int]
    ) -> ServiceResponse:
        try:
                    stmt = select(SlotsModel).where(func.date(SlotsModel.time) == date)
                    result = await self.session.execute(stmt)
                    account = result.scalars().first()

                    if account is None:
                        obj = SlotsModel(uuid=uuid.uuid4(),time=datetime.datetime.now(),slots=slots)
                        self.session.add(obj)
                        await self.session.commit()
                        return self.response(ServiceResponseStatus.CREATED,
                                             result=[obj])
                    updated_slots = account.slots 
                    updated_slots.extend(slots)
                    stmt_update = (
                        update(SlotsModel)
                        .where(func.date(SlotsModel.time) == date)
                        .values({"slots": updated_slots})
                    )
                    await self.session.execute(stmt_update)
                    await self.session.commit()
                    return self.response(ServiceResponseStatus.CREATED)

        except SQLAlchemyError as e:
                    logger.error(f"An error occurred: {e}")
                    await self.session.rollback()
                    return self.response(ServiceResponseStatus.ERROR)

    async def createplans(
        self, processinput: PlansModelInputSchema
    ) -> ServiceResponse:
        try:
                    # Create a SELECT statement to fetch the oauth_account by email.
                    data = processinput.model_dump()
                    data["uuid"] =uuid.uuid4()
                    plan = PlansModel(**data)
                    self.session.add(plan)
                    await self.session.commit()
                    return self.response(ServiceResponseStatus.CREATED,
                                         result=PlansModelInputSchema.from_sqlalchemy(plan))

        except SQLAlchemyError as e:
                    logger.error(f"An error occurred: {e}")
                    await self.session.rollback()
                    return self.response(ServiceResponseStatus.ERROR)

    async def list_plans(
        self,
        params: AbstractParams,
    ) -> ServiceResponse:
        try:
            # Create a SELECT statement.
            stmt = select(PlansModel)
            paginated_result = await paginate(self.session, stmt, params, unique=True)
            metadata = {
                "total": paginated_result.total,
                "page": paginated_result.page,
                "size": paginated_result.size,
                "pages": paginated_result.pages,
            }
            # self.cache_data(filters , paginated_result)

            return self.response(
                ServiceResponseStatus.FETCHED,
                result=[
                    PlansModelSchema(
                        hours=item.hours,
                        price=item.price,
                        icon=item.icon,
                        color=item.color,
                        label=item.label,
                    )
                    for item in paginated_result.items
                ],
                metadata=metadata,
            )  #: Paginate the data from DB
        except SQLAlchemyError as e:
            logger.error(f"An error occurred: {e}")
            await self.session.rollback()
            return self.response(ServiceResponseStatus.ERROR)        