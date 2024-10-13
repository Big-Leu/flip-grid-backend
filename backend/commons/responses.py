import json
import typing
from enum import Enum
from typing import Any, List

from fastapi.responses import JSONResponse as FASTAPI_JSONResponse
from starlette.background import BackgroundTask

from backend.logging import get_logger

logger = get_logger(__name__)


class ServiceResponseStatus(Enum):
    FETCHED = "FETCHED"
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    EXISTS = "EXISTS"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    ERROR = "ERROR"
    NOTFOUND = "NOTFOUND"


class JSONResponse(FASTAPI_JSONResponse):
    media_type = "application/json"

    def __init__(
        self,
        content: typing.Any,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(content, status_code, headers, media_type, background)

    def json(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


class ServiceResponse:
    def __init__(
        self,
        status: ServiceResponseStatus,
        message: str,
        request_item: str = "",
        result: List[Any] = [],
        metadata: dict[str, Any] = {},
        **kwargs: dict[str, Any],
    ) -> None:
        if status not in ServiceResponseStatus:
            logger.error(f"Invalid status: {status}")
            raise ValueError(f"Invalid status: {status}")

        if message == "" or message is None:
            match status:
                case ServiceResponseStatus.FETCHED:
                    message = f"{request_item} Fetched successfully"
                case ServiceResponseStatus.CREATED:
                    message = f"{request_item} Created successfully"
                case ServiceResponseStatus.UPDATED:
                    message = f"{request_item} Updated successfully"
                case ServiceResponseStatus.DELETED:
                    message = f"{request_item} Deleted successfully"
                case ServiceResponseStatus.BAD_REQUEST:
                    message = f"Bad request for {request_item}"
                case ServiceResponseStatus.UNAUTHORIZED:
                    message = f"Unauthorized access for {request_item}"
                case ServiceResponseStatus.FORBIDDEN:
                    message = f"Forbidden access for {request_item}"
                case ServiceResponseStatus.ERROR:
                    message = f"An error occurred while processing {request_item}"
                case ServiceResponseStatus.EXISTS:
                    message = f"duplicate key found {request_item}"

        if not isinstance(result, list):  # to make sure result is a list
            result = [result]

        self.message = message.lower()
        self.status = status
        self.result = result
        self.result_length = len(result)
        self.metadata = metadata

    def json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "result": self.result,
            "result_length": self.result_length,
            "metadata": self.metadata,
        }

    def get_api_response(self) -> JSONResponse:
        match self.status:
            case ServiceResponseStatus.FETCHED:
                return OKAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.CREATED:
                return CreatedAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.UPDATED:
                return OKAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.DELETED:
                return OKAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.BAD_REQUEST:
                return BadRequestAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.UNAUTHORIZED:
                return UnauthorizedAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.FORBIDDEN:
                return ForbiddenAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.ERROR:
                return ErrorServiceResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.EXISTS:
                return ExistsAPIResponse(self.json(), **self.kwargs)
            case ServiceResponseStatus.NOTFOUND:
                return OKAPIResponse(self.json(), **self.kwargs)
            case _:
                return OKAPIResponse(self.json(), **self.kwargs)


class ErrorServiceResponse(ServiceResponse):
    def __init__(self, message: str) -> None:
        super().__init__(ServiceResponseStatus.ERROR, message)


class APIResponse:
    def __init__(self, status_code: int, message: str, result: List = []) -> None:
        self.status_code = status_code
        self.message = message
        self.result = result

    def json(self) -> dict:
        return {
            "status_code": self.status_code,
            "message": self.message,
            "result": self.result,
        }


class ExistsAPIResponse(APIResponse):
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(409, message, **kwargs)


class CreatedAPIResponse(APIResponse):
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(201, message, **kwargs)


class OKAPIResponse(APIResponse):
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(200, message, **kwargs)


class BadRequestAPIResponse(APIResponse):
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(400, message, **kwargs)


class UnauthorizedAPIResponse(APIResponse):
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(401, message, **kwargs)


class ForbiddenAPIResponse(APIResponse):
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(403, message, **kwargs)
