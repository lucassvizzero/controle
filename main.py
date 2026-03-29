import logging
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

import core.settings as settings
from core.database import Base, engine
from core.fixtures import fixtures
from routes import accounts, budgets, cards, categories, index, login, register, transactions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI()
app.add_middleware(SessionMiddleware, settings.SECRET_KEY)


class RedirectUnauthorizedMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        if response.status_code == 401:
            return RedirectResponse(url="/login")

        return response


app.add_middleware(RedirectUnauthorizedMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS — allow_credentials não pode ser usado com allow_origins=["*"].
# Como este é um app server-side (sem frontend separado), credenciais não são necessárias via CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    fixtures()


# Registrar rotas
app.include_router(register.router)
app.include_router(login.router)
app.include_router(accounts.router)
app.include_router(cards.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(transactions.router)
app.include_router(index.router)
