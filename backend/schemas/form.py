import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from sqlalchemy import UUID

from backend.db.models.users import User

JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class bookingform(BaseModel):
    userName: str
    email: str
    mobileNumber: Optional[str] = None
    userAadhar: Optional[str] = None
    userDrivingLicense: Optional[str] = None
    date: Optional[datetime.datetime] = None
    class Config:
        from_attributes = True

    @classmethod
    def from_sqlalchemy(
        cls, model: User
    ) -> "bookingform":
        return cls.model_validate(model)

class FormInputSchema(BaseModel):
    userName: str
    lastName: str
    mobile: str
    userEmail: str

class fillslots(BaseModel):
    slots: list[int]

class UserDetailSchema(BaseModel):
    userName: Optional[str] = None
    userProfile: Optional[str] = None
    email: Optional[str] = None

    class Config:
        fromAttributes = True
        arbitrary_types_allowed=True