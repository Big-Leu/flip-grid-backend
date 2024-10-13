import datetime
from typing import Any, ClassVar, Dict, Generator, List, Optional, Type, Union
from sqlalchemy.exc import SQLAlchemyError
from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import DateTime, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import class_mapper
from backend.logging import get_logger
from backend.commons.responses import ServiceResponse, ServiceResponseStatus
from backend.db.base import Base
from backend.db.models.users import User
from backend.schemas.form import UserDetailSchema
logger = get_logger(__name__)

class BaseService:
    __item_name__ = "BaseSerivce"

    def __init__(self, session: AsyncSession):
        self.session = session

    def serialize(model_instance) -> Dict[str, Any]:
        columns = [c.key for c in class_mapper(model_instance.__class__).columns]
        return {c: getattr(model_instance, c) for c in columns}

    def response(
        self,
        status: ServiceResponseStatus,
        message: str = "",
        result: Any = [],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ServiceResponse:
        if metadata is None:
            metadata = {}
        return ServiceResponse(
            status, message, self.__item_name__, result, metadata=metadata
        )
    async def user_list(self, user1: str) -> ServiceResponse:
        try:
            # Adjust the query to select both bp_unit_name and bp_unit_id
            query = select(User.userName, User.email, User.id)
            result = await self.session.execute(query)       
            names = [
                {
                    "userData" : await self.get_user_details(getattr(row, "id", None))
                }
                for row in result.all()
                if getattr(row, "id", None) != user1
            ]
    
            return BaseService.response(ServiceResponseStatus.FETCHED, result=names)
        except SQLAlchemyError as e:
            logger.error(f"An error occurred: {e}")
            return BaseService.response(ServiceResponseStatus.ERROR)
    async def get_user_details(self, reviewer_uuid: Union[None, str]
                               ) -> Union[None, UserDetailSchema]:
        if reviewer_uuid is None:
            return None
        user_profile = await self.get_user_profile_by_uuid(reviewer_uuid)
        if user_profile is not None:
            return UserDetailSchema(
                id=user_profile.id,
                userName=user_profile.userName,
                userProfile=user_profile.userProfile,
                email=user_profile.email,
            )
        return None
    async def get_user_profile_by_uuid(self, uuid: str) -> Union[None, User]:
        query = select(User).filter_by(id=uuid)
        result = await self.session.execute(query)
        user = result.scalars().first()
        if user is not None:
            return user
        else:
            return None


def generate_field_annotations(
    modelF: Type[Base], rangelist: Optional[List[str]] = None
) -> Generator[Any, Any, Any]:
    for name, column in modelF.__table__.columns.items():
        col_type = type(column.type)
        if issubclass(col_type, String):
            if rangelist and name in rangelist:
                yield name + "__in", Optional[List[str]], []
            else:
                yield name + "__ilike", Optional[str], None
        elif issubclass(col_type, DateTime):
            yield name + "__gte", Optional[datetime.datetime], None
            yield name + "__lte", Optional[datetime.datetime], None
        elif issubclass(col_type, UUID):
            yield name + "__in", Optional[List[Any]], []
        else:
            yield name, col_type, None
    yield "order_by", Optional[List[str]], []


def create_filter_class(
    modelF: Type[Base],
    rangelist: Optional[List[str]] = None,
    base_filter: Type[Filter] = Filter,
) -> type[Filter]:
    # Function to generate field annotations based on column type

    # Generate field annotations dynamically
    fields = {}
    for name, typ, default in generate_field_annotations(modelF, rangelist):
        fields[name] = (typ, default)

    class Constants(base_filter.Constants):  # type: ignore
        model: ClassVar[Type[Base]] = modelF

    # Create the new filter class dynamically
    filter_class_name = f"{modelF.__name__}Filter"
    new_filter_class = type(
        filter_class_name,
        (base_filter,),
        {
            "__module__": base_filter.__module__,
            "__annotations__": {name: typ for name, (typ, _) in fields.items()},
            **{name: default for name, (_, default) in fields.items()},
        },
    )
    new_filter_class.Constants = Constants  # type: ignore
    new_filter_class.__annotations__["Constants"] = ClassVar[Type[Constants]]
    return new_filter_class

async def user_list(self, user1: str) -> ServiceResponse:
        try:
            # Adjust the query to select both bp_unit_name and bp_unit_id
            query = select(User.userName, User.email, User.id)
            result = await self.session.execute(query)       
            names = [
                {
                    "userData" : await self.get_user_details(getattr(row, "id", None))
                }
                for row in result.all()
                if getattr(row, "id", None) != user1
            ]
    
            return BaseService.response(ServiceResponseStatus.FETCHED, result=names)
        except SQLAlchemyError as e:
            logger.error(f"An error occurred: {e}")
            return BaseService.response(ServiceResponseStatus.ERROR)
