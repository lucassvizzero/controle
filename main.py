import logging
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

import core.settings as settings
from core.database import Base, engine
from core.fixtures import fixtures
from routes import accounts, balance, budgets, cards, categories, index, login, register, transactions, settings as settings_route, reports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI()
app.add_middleware(SessionMiddleware, settings.SECRET_KEY)


class RedirectUnauthorizedMiddleware:
    """Pure ASGI middleware: redireciona respostas 401 para /login.

    Evita o uso de BaseHTTPMiddleware que causa deadlock com TestClient
    no Starlette 1.0.0 ao lidar com TemplateResponse (streaming body).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        messages: list = []

        async def buffering_send(message: dict) -> None:
            messages.append(message)

        await self.app(scope, receive, buffering_send)

        if messages and messages[0].get("status") == 401:
            redirect = RedirectResponse(url="/login")
            await redirect(scope, receive, send)
        else:
            for message in messages:
                await send(message)


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
app.include_router(settings_route.router)
app.include_router(reports.router)
app.include_router(balance.router)
app.include_router(index.router)
