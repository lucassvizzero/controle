"""Testes de integração para rotas de relatórios (/reports)."""
from datetime import date, datetime

from core.models import Account, Budget, Category, Transaction
from core.schemas import BankName, CategoryType


def _make_paid_tx(db, user_id, account_id, category_id, value, paid_at):
    tx = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        description="Teste",
        value=value,
        due_at=paid_at.date() if isinstance(paid_at, datetime) else paid_at,
        paid_at=paid_at,
        is_deleted=False,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


class TestReportsPage:
    def test_pagina_retorna_200(self, client):
        response = client.get("/reports")
        assert response.status_code == 200

    def test_filtro_por_ano(self, client):
        response = client.get("/reports?year=2026")
        assert response.status_code == 200


class TestDataAnnual:
    def test_retorna_estrutura_correta(self, client):
        response = client.get("/reports/data/annual?year=2026")
        assert response.status_code == 200
        data = response.json()
        assert "months" in data
        assert "entrou" in data
        assert "saiu" in data
        assert "investiu" in data
        assert "sobrou" in data
        assert len(data["months"]) == 12
        assert len(data["entrou"]) == 12

    def test_agrega_transacoes_pagas(self, client, db, test_user, test_account, test_category):
        cat_income = Category(
            user_id=test_user.id, name="Salário",
            type=CategoryType.income, icon="", color="#00ff00",
        )
        db.add(cat_income)
        db.commit()
        db.refresh(cat_income)

        # Período de março com start=20,end=19 = 20/fev → 19/mar
        _make_paid_tx(db, test_user.id, test_account.id, cat_income.id,
                      1000.0, datetime(2026, 3, 10))
        _make_paid_tx(db, test_user.id, test_account.id, test_category.id,
                      400.0, datetime(2026, 3, 10))

        response = client.get("/reports/data/annual?year=2026")
        data = response.json()
        assert data["entrou"][2] >= 1000.0   # março = índice 2
        assert data["saiu"][2] >= 400.0

    def test_nao_inclui_pendentes(self, client, db, test_user, test_account, test_category):
        tx = Transaction(
            user_id=test_user.id, account_id=test_account.id,
            category_id=test_category.id, description="Pendente",
            value=999.0, due_at=date(2026, 4, 10),
            paid_at=None, is_deleted=False,
        )
        db.add(tx)
        db.commit()

        response = client.get("/reports/data/annual?year=2026")
        data = response.json()
        assert data["saiu"][3] < 999.0  # abril = índice 3


class TestDataCategories:
    def test_retorna_expense_e_income(self, client):
        response = client.get("/reports/data/categories?year=2026")
        assert response.status_code == 200
        data = response.json()
        assert "expense" in data
        assert "income" in data

    def test_agrupa_por_categoria_raiz(self, client, db, test_user, test_account, test_category):
        sub = Category(
            user_id=test_user.id, name="Restaurante",
            type=CategoryType.expense, icon="", color="#ff0000",
            parent_id=test_category.id,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        _make_paid_tx(db, test_user.id, test_account.id, sub.id, 200.0, datetime(2026, 3, 10))

        response = client.get("/reports/data/categories?year=2026&month=3")
        data = response.json()
        names = [e["name"] for e in data["expense"]]
        assert test_category.name in names

    def test_isolamento_por_usuario(self, client, db, test_user, test_account, test_category):
        from core.auth import pwd_context
        from core.models import User

        outro = User(name="Outro", email="rpt_outro@ex.com", username="rpt_outro",
                     password=pwd_context.hash("x"))
        db.add(outro)
        db.commit()
        db.refresh(outro)

        acc2 = Account(user_id=outro.id, name="Conta2", bank=BankName.nubank, is_active=True)
        cat2 = Category(user_id=outro.id, name="CatOutro", type=CategoryType.expense, icon="", color="#000")
        db.add_all([acc2, cat2])
        db.commit()
        db.refresh(acc2); db.refresh(cat2)

        _make_paid_tx(db, outro.id, acc2.id, cat2.id, 9999.0, datetime(2026, 3, 5))

        response = client.get("/reports/data/categories?year=2026&month=3")
        data = response.json()
        names = [e["name"] for e in data["expense"]]
        assert "CatOutro" not in names


class TestDataAccounts:
    def test_retorna_lista(self, client):
        response = client.get("/reports/data/accounts?year=2026")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_agrega_por_conta(self, client, db, test_user, test_account, test_category):
        cat_income = Category(
            user_id=test_user.id, name="Entrada",
            type=CategoryType.income, icon="", color="#0f0",
        )
        db.add(cat_income)
        db.commit()
        db.refresh(cat_income)

        _make_paid_tx(db, test_user.id, test_account.id, cat_income.id, 2000.0, datetime(2026, 5, 1))
        _make_paid_tx(db, test_user.id, test_account.id, test_category.id, 500.0, datetime(2026, 5, 10))

        response = client.get("/reports/data/accounts?year=2026&month=5")
        data = response.json()
        acc = next((a for a in data if a["name"] == test_account.name), None)
        assert acc is not None
        assert acc["income"] >= 2000.0
        assert acc["expense"] >= 500.0


class TestDataBudgets:
    def test_retorna_lista(self, client):
        response = client.get("/reports/data/budgets?year=2026&month=3")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_calcula_percentual(self, client, db, test_user, test_account, test_category):
        budget = Budget(
            user_id=test_user.id, category_id=test_category.id,
            limit_value=1000.0, month=date(2026, 6, 1),
        )
        db.add(budget)
        db.commit()

        _make_paid_tx(db, test_user.id, test_account.id, test_category.id, 600.0, datetime(2026, 6, 15))

        response = client.get("/reports/data/budgets?year=2026&month=6")
        data = response.json()
        item = next((b for b in data if b["name"] == test_category.name), None)
        assert item is not None
        assert item["limit"] == 1000.0
        assert item["spent"] >= 600.0
        assert item["percent"] >= 60.0
