import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

startup_error = None
try:
    from app.main import app as fastapi_app
    app = fastapi_app
except Exception as e:
    startup_error = e
    app = FastAPI()

    @app.get("/__startup_error")
    def _startup_error():
        return JSONResponse(
            status_code=500,
            content={"error": "Startup failure", "detail": str(startup_error)},
        )
