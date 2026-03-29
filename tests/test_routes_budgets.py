"""Testes de integração para rotas de orçamentos (/budgets)."""
from core.models import Budget


class TestGetBudgets:
    def test_lista_orcamentos_retorna_200(self, client):
        response = client.get("/budgets")
        assert response.status_code == 200

    def test_filtro_por_mes(self, client):
        response = client.get("/budgets?f_month=2026-03")
        assert response.status_code == 200

    def test_filtro_por_categoria(self, client, test_category):
        response = client.get(f"/budgets?f_category_id={test_category.id}")
        assert response.status_code == 200


class TestGetBudgetById:
    def test_retorna_json_do_orcamento(self, client, db, test_user, test_category):
        budget = Budget(
            user_id=test_user.id,
            category_id=test_category.id,
            limit_value=500.00,
            month="2026-03-01",
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        response = client.get(f"/budgets/{budget.id}")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert float(data["limit_value"]) == 500.0

    def test_orcamento_inexistente_retorna_404(self, client):
        response = client.get("/budgets/999999")
        assert response.status_code == 404


class TestCreateBudget:
    def test_cria_orcamento_redireciona(self, client, test_category):
        response = client.post(
            "/budgets",
            data={
                "category_id": test_category.id,
                "limit_value": "300.00",
                "month": "2026-04",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/budgets"

    def test_orcamento_criado_persiste_no_banco(self, client, db, test_user, test_category):
        client.post(
            "/budgets",
            data={
                "category_id": test_category.id,
                "limit_value": "750.00",
                "month": "2026-05",
            },
            follow_redirects=False,
        )
        budget = db.query(Budget).filter(
            Budget.user_id == test_user.id,
            Budget.category_id == test_category.id,
        ).order_by(Budget.id.desc()).first()
        assert budget is not None
        assert float(budget.limit_value) == 750.0

    def test_mes_invalido_redireciona_sem_criar(self, client, test_category):
        response = client.post(
            "/budgets",
            data={
                "category_id": test_category.id,
                "limit_value": "100.00",
                "month": "mes-invalido",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestEditBudget:
    def test_edita_orcamento_redireciona(self, client, db, test_user, test_category):
        budget = Budget(
            user_id=test_user.id,
            category_id=test_category.id,
            limit_value=200.00,
            month="2026-03-01",
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        response = client.post(
            f"/budgets/{budget.id}/edit",
            data={
                "category_id": test_category.id,
                "limit_value": "400.00",
                "month": "2026-03",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_edicao_altera_limite_no_banco(self, client, db, test_user, test_category):
        budget = Budget(
            user_id=test_user.id,
            category_id=test_category.id,
            limit_value=100.00,
            month="2026-06-01",
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        client.post(
            f"/budgets/{budget.id}/edit",
            data={
                "category_id": test_category.id,
                "limit_value": "999.99",
                "month": "2026-06",
            },
            follow_redirects=False,
        )
        db.refresh(budget)
        assert float(budget.limit_value) == 999.99


class TestDeleteBudget:
    def test_deleta_orcamento_redireciona(self, client, db, test_user, test_category):
        budget = Budget(
            user_id=test_user.id,
            category_id=test_category.id,
            limit_value=50.00,
            month="2026-07-01",
        )
        db.add(budget)
        db.commit()
        budget_id = budget.id

        response = client.post(f"/budgets/{budget_id}/delete", follow_redirects=False)
        assert response.status_code == 303

    def test_orcamento_removido_do_banco(self, client, db, test_user, test_category):
        budget = Budget(
            user_id=test_user.id,
            category_id=test_category.id,
            limit_value=50.00,
            month="2026-08-01",
        )
        db.add(budget)
        db.commit()
        budget_id = budget.id

        client.post(f"/budgets/{budget_id}/delete", follow_redirects=False)
        result = db.query(Budget).filter(Budget.id == budget_id).first()
        assert result is None

    def test_deletar_inexistente_nao_falha(self, client):
        response = client.post("/budgets/999999/delete", follow_redirects=False)
        assert response.status_code == 303
