from typing import Dict, Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, Literal["OK"]]:
    return JSONResponse({"status": "OK"}, status_code=200)
