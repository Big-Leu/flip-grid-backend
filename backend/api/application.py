from importlib import metadata
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import UJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination

from backend.api.lifetime import register_shutdown_event, register_startup_event
from backend.api.modules.router import api_router
from backend.settings import settings

APP_ROOT = Path(__file__).parent.parent


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """
    app = FastAPI(
        title="FlipGrid",
        version=metadata.version("backend"),
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        default_response_class=UJSONResponse,
    )
    # SECRET_KEY = "your_secret_key"
    # SessionMiddleware(
    #     app,
    #     secret_key=settings.JWT_SECRET,
    # )

    origins = settings.CORS_ORGIN
    print("Setting CORS origin to: ", origins)
    add_pagination(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # CORSMiddleware(   # TODO: Secure CORS settings
    #     app,
    #     allow_origins=["*" , "localhost:3000", "localhost:8000"],
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"]
    # )

    # app.add_middleware(
    #     AuthenticationMiddleware,
    #     backend=JWTAuth(),
    # )

    # Adds startup and shutdown events.
    register_startup_event(app)
    register_shutdown_event(app)
    # Main router for the API.
    app.include_router(router=api_router, prefix="/api/v1")
    # Adds static directory.
    # This directory is used to access swagger files.
    app.mount(
        "/static",
        StaticFiles(directory=APP_ROOT / "static"),
        name="static",
    )
    # bp_unit_service = Business_units(get_db_session())
    # loop = asyncio.get_event_loop()
    # task = loop.create_task(bp_unit_service.create())
    # loop.run_until_complete(task)
    return app
