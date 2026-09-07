from fastapi import FastAPI

import app.db.base_models  # noqa: F401
from app.routers import user

app = FastAPI()

app.include_router(user.router)
