from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from api.v1.api import api_router
from database.session import Base, engine
import models

app = FastAPI()

# CORS для WebSocket и фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return RedirectResponse(url="/docs")


app.include_router(api_router)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run("main:app", host=settings.API_HOST,
                port=settings.API_PORT, log_level=settings.LOG_LEVEL, reload=True)
