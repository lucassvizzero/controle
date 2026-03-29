"""Configuração compartilhada dos testes.

Para rodar localmente:
    DATABASE_URL=postgresql://admin:secret@localhost:5432/finance_test pytest

Dentro do container (recomendado):
    docker exec finance_api python -m pytest
"""
import os

# Define DATABASE_URL de teste ANTES de qualquer import do projeto.
# Usa uma variável de ambiente se definida, senão aponta para o PostgreSQL de teste local.
_default_test_url = "postgresql://admin:secret@localhost:5432/finance_test"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _default_test_url)

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Garante que o working directory seja a raiz do projeto
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import pwd_context
from core.database import Base, get_db
from core.models import Account, Budget, Card, Category, Transaction, User
from core.schemas import BankName, BrandName, CategoryType

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Cria as tabelas uma vez para toda a sessão de testes."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(create_tables):
    """Sessão isolada por teste: rollback no teardown."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_user(db) -> User:
    user = User(
        name="Usuário Teste",
        email="teste@exemplo.com",
        username="usuario_teste",
        password=pwd_context.hash("senha123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_account(db, test_user) -> Account:
    account = Account(
        user_id=test_user.id,
        name="Conta Teste",
        bank=BankName.nubank,
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture(scope="function")
def test_category(db, test_user) -> Category:
    category = Category(
        user_id=test_user.id,
        name="Alimentação",
        type=CategoryType.expense,
        icon="fas fa-utensils",
        color="#ff0000",
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture(scope="function")
def test_card(db, test_user, test_account) -> Card:
    card = Card(
        user_id=test_user.id,
        account_id=test_account.id,
        name="Cartão Teste",
        brand=BrandName.visa,
        due_day=10,
        close_day=3,
        is_active=True,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@pytest.fixture(scope="function")
def test_transaction(db, test_user, test_account, test_category) -> Transaction:
    transaction = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=test_category.id,
        description="Supermercado",
        value=150.00,
        due_at=date(2026, 3, 15),
        is_deleted=False,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@pytest.fixture(scope="function")
def client(db, test_user):
    """TestClient com banco de teste e usuário autenticado injetados.

    Não usa context manager para evitar que startup_event dispare
    `fixtures()` contra o banco de produção.
    As tabelas já foram criadas pelo fixture `create_tables`.
    """
    from fastapi import Request as FastAPIRequest
    from main import app
    from routes.auth import get_current_user

    def override_get_db():
        yield db

    def override_get_current_user(request: FastAPIRequest):
        # TemplateContext lê request.state.user — precisa ser setado aqui
        request.state.user = test_user
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Sem context manager → startup_event não é executado
    c = TestClient(app, raise_server_exceptions=True)
    yield c

    app.dependency_overrides.clear()
