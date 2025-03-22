from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

import core.settings as settings
from core.database import Base, engine
from core.fixtures import fixtures
from routes import accounts, budgets, cards, categories, index, login, register, transactions

app = FastAPI()
app.add_middleware(SessionMiddleware, settings.SECRET_KEY)


class RedirectUnauthorizedMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Se o status for 401, redireciona para /login
        if response.status_code == 401:
            return RedirectResponse(url="/login")

        return response


# Adiciona o middleware na aplicação
app.add_middleware(RedirectUnauthorizedMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# @app.on_event("startup")
# def startup_event():
#     Base.metadata.drop_all(bind=engine)
#     inspector = inspect(engine)
#     for table in Base.metadata.tables.keys():
#         if not inspector.has_table(table):
#             print(f"Criando tabela: {table}")
#             Base.metadata.create_all(bind=engine)

#     fixtures()


# Registrar rotas
app.include_router(register.router)
app.include_router(login.router)
app.include_router(accounts.router)
app.include_router(cards.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(transactions.router)
app.include_router(index.router)
