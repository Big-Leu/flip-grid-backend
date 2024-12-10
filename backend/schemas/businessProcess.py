"""
This file contains the schemas for
the business process model. This will be used in
REST API to validate the input and output data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from backend.db.models.businessProcess import BusinessProcessModel

JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class ProcessCreateInputSchema(BaseModel):

    processName: str
    processData: str
    processDescription: str
    bpUnitName: str


class UserDetailSchema(BaseModel):
    userName: Optional[str] = None
    userProfile: Optional[str] = None
    email: Optional[str] = None

    class Config:
        fromAttributes = True
        arbitrary_types_allowed = True


class ProcessUpdateInputSchema(BaseModel):
    processData: str

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


# class ProcessCreateInputSchema(BaseModel):
#     processName: str
#     processData: JSON = {}
#     processAttributes: JSON = {}
#     owner: str


class ProcessDeleteInputSchema(BaseModel):
    uuid: UUID


class ProcessReadInputSchema(BaseModel):
    uuid: UUID


class ProcessCreateOutputSchema(BaseModel):
    uuid: UUID
    processName: str
    processData: str
    processDescription: str
    ownerId: UUID
    createdDate: datetime = Field(defaultFactory=datetime.utcnow)
    updatedDate: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(
        cls, model: BusinessProcessModel
    ) -> "ProcessCreateOutputSchema":
        return cls.model_validate(model)


class ProcessReadOutputSchema(BaseModel):
    uuid: UUID
    processName: str
    processData: str
    processDescription: str
    ownerId: UUID
    updatedDate: Optional[datetime] = None
    approvalStatus: str
    attestationDate: Optional[datetime] = None
    reviewer: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(cls, model: BusinessProcessModel) -> "ProcessReadOutputSchema":
        return cls.model_validate(model)


# userProfile=item.relatedModel.userProfile,


class ProcessCreateListSchema(BaseModel):
    uuid: UUID
    processName: str
    updatedDate: datetime
    owner: Optional[UserDetailSchema] = None
    approvalStatus: str
    reviewer: Optional[UserDetailSchema] = None
    bpUnitName: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(cls, model: BusinessProcessModel) -> "ProcessCreateListSchema":
        return cls.model_validate(model)
