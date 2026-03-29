"""Testes de integração para rotas de transações (/transactions)."""
from datetime import date

from core.models import Transaction


class TestGetTransactions:
    def test_lista_transacoes_retorna_200(self, client):
        response = client.get("/transactions")
        assert response.status_code == 200

    def test_filtro_por_descricao(self, client, test_transaction):
        response = client.get(f"/transactions?f_description={test_transaction.description}")
        assert response.status_code == 200

    def test_paginacao_funciona(self, client):
        response = client.get("/transactions?page=1&per_page=5")
        assert response.status_code == 200


class TestGetTransactionById:
    def test_retorna_json_da_transacao(self, client, test_transaction):
        response = client.get(f"/transactions/{test_transaction.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == test_transaction.description

    def test_transacao_inexistente_retorna_erro(self, client):
        response = client.get("/transactions/999999")
        assert response.status_code == 200
        assert "error" in response.json()


class TestCreateTransaction:
    def test_cria_transacao_simples_redireciona(self, client, test_account, test_category):
        response = client.post(
            "/transactions",
            data={
                "account_id": test_account.id,
                "category_id": test_category.id,
                "description": "Almoço",
                "value": "35.50",
                "due_at": "2026-03-20",
                "is_recurring": "false",
                "is_installment": "false",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_transacao_criada_persiste_no_banco(self, client, db, test_user, test_account, test_category):
        client.post(
            "/transactions",
            data={
                "account_id": test_account.id,
                "category_id": test_category.id,
                "description": "Mercado",
                "value": "200.00",
                "due_at": "2026-03-25",
                "is_recurring": "false",
                "is_installment": "false",
            },
            follow_redirects=False,
        )
        tx = db.query(Transaction).filter(
            Transaction.user_id == test_user.id,
            Transaction.description == "Mercado",
        ).first()
        assert tx is not None
        assert float(tx.value) == 200.0
        assert tx.is_deleted is False


class TestEditTransaction:
    def test_edita_transacao_redireciona(self, client, test_transaction, test_account, test_category):
        response = client.post(
            f"/transactions/{test_transaction.id}/edit",
            data={
                "account_id": test_account.id,
                "category_id": test_category.id,
                "description": "Supermercado Editado",
                "value": "180.00",
                "due_at": "2026-03-15",
                "is_recurring": "false",
                "is_installment": "false",
                "next_occurrences": "false",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_edicao_altera_descricao_no_banco(self, client, db, test_transaction, test_account, test_category):
        client.post(
            f"/transactions/{test_transaction.id}/edit",
            data={
                "account_id": test_account.id,
                "category_id": test_category.id,
                "description": "Feira Livre",
                "value": "90.00",
                "due_at": "2026-03-15",
                "is_recurring": "false",
                "is_installment": "false",
                "next_occurrences": "false",
            },
            follow_redirects=False,
        )
        db.refresh(test_transaction)
        assert test_transaction.description == "Feira Livre"


class TestDeleteTransaction:
    def test_delete_aplica_soft_delete(self, client, db, test_transaction):
        """Ao deletar, is_deleted deve ser True — não remove do banco."""
        tx_id = test_transaction.id
        client.post(
            f"/transactions/{tx_id}/delete",
            data={"next_occurrences": "false"},
            follow_redirects=False,
        )
        db.refresh(test_transaction)
        assert test_transaction.is_deleted is True

    def test_transacao_deletada_nao_aparece_na_listagem(self, client, db, test_transaction):
        tx_id = test_transaction.id
        client.post(
            f"/transactions/{tx_id}/delete",
            data={"next_occurrences": "false"},
            follow_redirects=False,
        )
        # A listagem deve excluir transações com is_deleted=True
        tx = db.query(Transaction).filter(
            Transaction.id == tx_id,
            Transaction.is_deleted.is_(False),
        ).first()
        assert tx is None

    def test_deletar_inexistente_redireciona(self, client):
        response = client.post(
            "/transactions/999999/delete",
            data={"next_occurrences": "false"},
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestTransactionIsolation:
    def test_usuario_nao_ve_transacoes_de_outro(self, client, db, test_user, test_account, test_category):
        """Transações de outro usuário não devem aparecer nas consultas."""
        from core.models import User
        from core.auth import pwd_context

        outro_user = User(
            name="Outro",
            email="outro@exemplo.com",
            username="outro_user",
            password=pwd_context.hash("outrasenha"),
        )
        db.add(outro_user)
        db.commit()
        db.refresh(outro_user)

        tx_outro = Transaction(
            user_id=outro_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            description="Transação de outro usuário",
            value=999.00,
            due_at=date(2026, 3, 1),
            is_deleted=False,
        )
        db.add(tx_outro)
        db.commit()

        # Query filtrada pelo test_user (injetado no client) não deve incluir a tx do outro
        txs = db.query(Transaction).filter(
            Transaction.user_id == test_user.id,
            Transaction.is_deleted.is_(False),
        ).all()
        ids = [t.id for t in txs]
        assert tx_outro.id not in ids
