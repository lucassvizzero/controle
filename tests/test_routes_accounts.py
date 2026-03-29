"""Testes de integração para rotas de contas (/accounts)."""
import pytest

from core.models import Account
from core.schemas import BankName


class TestGetAccounts:
    def test_lista_contas_retorna_200(self, client):
        response = client.get("/accounts")
        assert response.status_code == 200

    def test_lista_contas_com_filtro_nome(self, client, test_account):
        response = client.get(f"/accounts?f_name={test_account.name}")
        assert response.status_code == 200

    def test_lista_contas_com_filtro_banco(self, client, test_account):
        response = client.get(f"/accounts?f_bank={test_account.bank.value}")
        assert response.status_code == 200

    def test_paginacao_valida(self, client):
        response = client.get("/accounts?page=1&per_page=5")
        assert response.status_code == 200


class TestGetAccountById:
    def test_retorna_json_da_conta(self, client, test_account):
        response = client.get(f"/accounts/{test_account.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_account.name

    def test_conta_inexistente_retorna_404(self, client):
        response = client.get("/accounts/999999")
        assert response.status_code == 404


class TestCreateAccount:
    def test_cria_conta_redireciona(self, client):
        response = client.post(
            "/accounts",
            data={"name": "Conta Nova", "bank": BankName.nubank.value, "is_active": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/accounts"

    def test_conta_criada_persiste_no_banco(self, client, db, test_user):
        client.post(
            "/accounts",
            data={"name": "Poupança", "bank": BankName.santander.value, "is_active": "true"},
            follow_redirects=False,
        )
        conta = db.query(Account).filter(
            Account.user_id == test_user.id, Account.name == "Poupança"
        ).first()
        assert conta is not None
        assert conta.bank == BankName.santander


class TestEditAccount:
    def test_edita_conta_redireciona(self, client, test_account):
        response = client.post(
            f"/accounts/{test_account.id}/edit",
            data={"name": "Nome Editado", "bank": BankName.c6bank.value, "is_active": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_edicao_altera_dados_no_banco(self, client, db, test_account):
        client.post(
            f"/accounts/{test_account.id}/edit",
            data={"name": "Conta Atualizada", "bank": BankName.c6bank.value, "is_active": "false"},
            follow_redirects=False,
        )
        db.refresh(test_account)
        assert test_account.name == "Conta Atualizada"
        assert test_account.bank == BankName.c6bank

    def test_edicao_conta_inexistente_redireciona(self, client):
        response = client.post(
            "/accounts/999999/edit",
            data={"name": "X", "bank": BankName.nubank.value, "is_active": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestDeleteAccount:
    def test_deleta_conta_redireciona(self, client, test_account):
        response = client.post(
            f"/accounts/{test_account.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/accounts"

    def test_conta_removida_do_banco(self, client, db, test_account):
        account_id = test_account.id
        client.post(f"/accounts/{account_id}/delete", follow_redirects=False)
        conta = db.query(Account).filter(Account.id == account_id).first()
        assert conta is None

    def test_deletar_inexistente_nao_falha(self, client):
        response = client.post("/accounts/999999/delete", follow_redirects=False)
        assert response.status_code == 303
