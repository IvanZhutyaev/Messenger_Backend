from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.config import settings, rate_limit_settings
from api.v1.api import api_router
from database.session import Base, engine
import models

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
@limiter.limit(rate_limit_settings.DEFAULT_LIMIT)
def root(request):
    return RedirectResponse(url="/docs")


app.include_router(api_router)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run("main:app", host=settings.API_HOST,
                port=settings.API_PORT, log_level=settings.LOG_LEVEL, reload=True)
